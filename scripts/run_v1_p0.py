#!/usr/bin/env python
"""run_v1_p0.py — Execute the full V1-P0 data feasibility audit.

Reads frozen P0 chain links, reconstructs shockwave episodes,
builds directed link metrics, computes airport mechanism dimensions,
runs sensitivity analysis, and generates the UI data contract.

All outputs are reproducible given the same frozen inputs.
"""

import gc
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.airports_under_stress.v1_mechanism import (
    EPISODE_MAX_DURATION_HOURS,
    EPISODE_MAX_SCHEDULED_TURN_MINUTES,
    build_airport_roles,
    build_directed_links,
    build_episode_rejections,
    build_shockwave_episodes,
    build_shockwave_steps,
    build_ui_contract,
    concentration_check,
    conditional_lift_stratified,
    select_case_candidates,
    sensitivity_by_threshold,
    sha256,
    validate_episodes,
    write_json_safe,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
REPORT_DIR = ROOT / "reports"
OUT_DIR = DATA

SEED = 20260727


def main() -> None:
    t0 = time.perf_counter()
    np.random.seed(SEED)
    previous_output_hashes: dict[str, str] = {}
    previous_manifest_path = OUT_DIR / "v1_p0_manifest.json"
    if previous_manifest_path.exists():
        try:
            previous_manifest = json.loads(
                previous_manifest_path.read_text(encoding="utf-8")
            )
            previous_output_hashes = previous_manifest.get("outputHashes", {})
        except (json.JSONDecodeError, OSError):
            previous_output_hashes = {}

    # ── Phase 0: verify inputs ────────────────────────────────────
    print("=" * 60)
    print("Phase 0: Input verification")
    flights_path = DATA / "p0_flights.parquet"
    links_path = DATA / "p0_chain_links.parquet"

    assert flights_path.exists(), f"Missing: {flights_path}"
    assert links_path.exists(), f"Missing: {links_path}"

    flights = pd.read_parquet(flights_path)
    links = pd.read_parquet(links_path)

    assert len(links) == 549_388, f"Expected 549,388 chain links, got {len(links)}"

    input_hash = {
        "p0_flights": sha256(flights_path),
        "p0_chain_links": sha256(links_path),
    }
    print(f"  flights: {len(flights):,} rows, sha256={input_hash['p0_flights'][:16]}...")
    print(f"  links:   {len(links):,} rows, sha256={input_hash['p0_chain_links'][:16]}...")

    # ── Phase 1: Episode reconstruction ───────────────────────────
    print(
        "\nPhase 1: Shockwave episode reconstruction "
        f"(T=15, scheduled turn<={EPISODE_MAX_SCHEDULED_TURN_MINUTES}m, "
        f"duration<={EPISODE_MAX_DURATION_HOURS}h)"
    )
    t1 = time.perf_counter()
    episodes = build_shockwave_episodes(links, threshold=15)
    steps = build_shockwave_steps()
    rejections = build_episode_rejections()
    t1e = time.perf_counter()
    print(
        f"  {len(episodes):,} episodes, {len(steps):,} steps, "
        f"{len(rejections):,} rejected timeline conflicts  ({t1e - t1:.1f}s)"
    )

    integrity = validate_episodes(episodes, links, steps)
    print(f"  Integrity: neg_turns={integrity['negative_actual_turn_steps']}, "
          f"utc_rev={integrity['utc_reversed']}, overlaps={integrity['overlapping_episodes']}, "
          f"gaps={integrity['airport_discontinuity_count']}")
    print(f"  Outcomes: recovered={(episodes['outcome']=='recovered').sum()}, "
          f"censored={(episodes['outcome']=='censored').sum()}")
    print(
        "  Continuity boundaries: "
        f"scheduled_turn_break={(episodes['terminationReason']=='scheduled_turn_break').sum()}, "
        f"duration_limit={(episodes['terminationReason']=='duration_limit').sum()}"
    )

    episodes.to_parquet(OUT_DIR / "v1_p0_episodes.parquet", index=False)
    steps.to_parquet(OUT_DIR / "v1_p0_steps.parquet", index=False)
    rejections.to_parquet(
        OUT_DIR / "v1_p0_episode_rejections.parquet", index=False
    )

    # ── Phase 2: Directed links ───────────────────────────────────
    print("\nPhase 2: Directed link metrics")
    t2 = time.perf_counter()
    d_links = build_directed_links(links, threshold=15)
    d_links.to_parquet(OUT_DIR / "v1_p0_directed_links.parquet", index=False)

    cond_lift = conditional_lift_stratified(links, threshold=15)
    wl = cond_lift["weightedConditionalLift"]
    t2e = time.perf_counter()
    l1 = d_links[d_links["level"] == "L1_turn_dest"]
    # CI null-safe: only count non-null
    ci_eligible = l1[l1["wilsonCI_low"].notna() & l1["wilsonCI_high"].notna()]
    print(f"  L1 links (turn→dest): {len(l1):,}  ({t2e - t2:.1f}s)")
    print(f"  Weighted stratified conditional lift: {wl:.4f} "
          f"(comparable strata: {cond_lift['comparableStrata']}, "
          f"excluded: {cond_lift['excludedStrata']}, coverage: {cond_lift['coverageRate']:.2%})")
    for min_n in (50, 100, 200):
        q = l1[l1["nUpstreamLate"] >= min_n]
        q_ci = ci_eligible[ci_eligible["nUpstreamLate"] >= min_n]
        ci_width = round(float((q_ci["wilsonCI_high"] - q_ci["wilsonCI_low"]).median()), 4) if len(q_ci) > 0 else None
        print(f"    n>={min_n}: {len(q)} links, {q['turnAirport'].nunique()} airports, "
              f"median CI width {ci_width} (n>=5 for CI: {len(q_ci)})")

    # ── Phase 3: Airport roles ────────────────────────────────────
    print("\nPhase 3: Airport mechanism dimensions")
    t3 = time.perf_counter()
    airport_roles = build_airport_roles(links, episodes, threshold=15)
    airport_roles.to_parquet(OUT_DIR / "v1_p0_airport_roles.parquet", index=False)
    t3e = time.perf_counter()

    role_counts = airport_roles["roleLabel"].value_counts().to_dict()
    n_with_data = int((airport_roles["nExposed"] >= 500).sum())
    print(f"  {len(airport_roles)} airports, {n_with_data} with >=500 exposures  ({t3e - t3:.1f}s)")
    print(f"  Role distribution: {json.dumps(role_counts)}")

    # ── Phase 4: Sensitivity ──────────────────────────────────────
    print("\nPhase 4: Sensitivity analysis")
    t4 = time.perf_counter()
    sens = sensitivity_by_threshold(links)
    t4e = time.perf_counter()
    for _, row in sens.iterrows():
        print(f"  T={int(row['threshold'])}: {int(row['nEpisodes']):,} episodes, "
              f"deep2={int(row['nDeep2'])}, deep3={int(row['nDeep3'])}, "
              f"airports500={int(row['nAirportsExposed500'])}")

    # Spearman + Top 20 overlap between thresholds
    from scipy.stats import spearmanr
    l1_t15 = l1[l1["nUpstreamLate"] >= 100].copy()
    l1_t30 = build_directed_links(links, threshold=30)
    l1_t30 = l1_t30[(l1_t30["level"] == "L1_turn_dest") & (l1_t30["nUpstreamLate"] >= 100)]
    cross_spearman = {}
    top20_overlap = {}
    for label, a, b in [("15vs30", l1_t15, l1_t30), ("15vs60", l1_t15, None)]:
        if b is None:
            l1_t60 = build_directed_links(links, threshold=60)
            b = l1_t60[(l1_t60["level"] == "L1_turn_dest") & (l1_t60["nUpstreamLate"] >= 100)]
        a_top = a.nlargest(20, "nUpstreamLate")[["turnAirport", "nextDestination"]]
        b_top = b.nlargest(20, "nUpstreamLate")[["turnAirport", "nextDestination"]]
        a_keys = set(zip(a_top["turnAirport"], a_top["nextDestination"]))
        b_keys = set(zip(b_top["turnAirport"], b_top["nextDestination"]))
        overlap = len(a_keys & b_keys)
        top20_overlap[label] = {"overlap": overlap, "uniqueA": len(a_keys), "uniqueB": len(b_keys)}
        # Spearman: merge on common links
        merged = a.merge(b, on=["turnAirport", "nextDestination"], suffixes=("_15", "_30"))
        if len(merged) >= 5:
            rho, p = spearmanr(merged["pPropGivenLate_15"], merged["pPropGivenLate_30"])
            cross_spearman[label] = round(rho, 4)
        else:
            cross_spearman[label] = None
    print(f"  Top20 overlap: {json.dumps(top20_overlap)}")
    print(f"  Spearman: {json.dumps(cross_spearman)}")

    conc = concentration_check(episodes, links, d_links)
    print(f"  Concentration: {json.dumps(conc, indent=2)}")
    print(f"  ({t4e - t4:.1f}s)")

    # ── Phase 5: Cases and UI contract ────────────────────────────
    print("\nPhase 5: Case candidates and UI contract")
    t5 = time.perf_counter()
    candidates = select_case_candidates(episodes, links)

    summary = {
        "period": "May 2026",
        "totalChainLinks": int(len(links)),
        "upstreamLateExposures": int(links["PrevArrDelay"].ge(15).sum()),
        "basePropagationRate": round(float(
            links.loc[links["PrevArrDelay"] >= 15, "DepDelay"].ge(15).mean()
        ), 4),
        "baseRecoveryRate": round(float(
            links.loc[links["PrevArrDelay"] >= 15, "DepDelay"].lt(15).mean()
        ), 4),
        "nEpisodes": int(len(episodes)),
        "nDeep2": int((episodes["depth"] >= 2).sum()),
        "nDeep3": int((episodes["depth"] >= 3).sum()),
        "maxDepth": int(episodes["depth"].max()),
        "meanDepth": round(float(episodes["depth"].mean()), 2),
        "episodesRecovered": int((episodes["outcome"] == "recovered").sum()),
        "episodesCensored": int((episodes["outcome"] == "censored").sum()),
        "episodesRejectedTimelineConflict": int(len(rejections)),
        "nAirportsExposed500": int((airport_roles["nExposed"] >= 500).sum()),
        "nLinksQualified100": int((l1["nUpstreamLate"] >= 100).sum()),
        "condLiftComparableStrata": cond_lift["comparableStrata"],
        "condLiftExcludedStrata": cond_lift["excludedStrata"],
        "condLiftCoverage": cond_lift["coverageRate"],
        "thresholdsAnalyzed": [15, 30, 60],
        "thresholdSensitivity": sens.to_dict(orient="records"),
        "episodeContinuity": {
            "maxScheduledTurnMinutes": EPISODE_MAX_SCHEDULED_TURN_MINUTES,
            "maxDurationHours": EPISODE_MAX_DURATION_HOURS,
            "sensitivityAudit": "reports/V1_P01_CONTINUITY_AUDIT.md",
        },
        "inputHash": input_hash,
    }

    contract = build_ui_contract(summary, d_links, airport_roles, episodes, candidates)
    write_json_safe(summary, OUT_DIR / "v1_p0_summary.json")
    write_json_safe(contract, OUT_DIR / "v1_p0_ui_contract.json")
    t5e = time.perf_counter()

    # Runtime manifest (separate from scientific results)
    output_hashes = {}
    for name in [
        "v1_p0_episodes.parquet",
        "v1_p0_steps.parquet",
        "v1_p0_episode_rejections.parquet",
        "v1_p0_directed_links.parquet",
        "v1_p0_airport_roles.parquet",
        "v1_p0_summary.json",
        "v1_p0_ui_contract.json",
    ]:
        p = OUT_DIR / name
        if p.exists():
            output_hashes[name] = sha256(p)
    print(f"  Output hashes: {json.dumps(output_hashes, indent=2)}")
    compared_with_previous = set(previous_output_hashes) == set(output_hashes)
    hashes_match_previous = (
        compared_with_previous and previous_output_hashes == output_hashes
    )

    manifest = {
        "generated": pd.Timestamp.now(tz="UTC").isoformat(),
        "executionTimeSeconds": round(time.perf_counter() - t0, 1),
        "pythonVersion": sys.version.split()[0],
        "outputHashes": output_hashes,
        "reproducibility": {
            "comparedWithPreviousRun": compared_with_previous,
            "scientificOutputsMatchPreviousRun": hashes_match_previous,
        },
    }
    write_json_safe(manifest, OUT_DIR / "v1_p0_manifest.json")

    ui_size = (OUT_DIR / "v1_p0_ui_contract.json").stat().st_size
    print(f"  Cases: {[(k, len(v)) for k, v in candidates.items()]}")
    print(f"  UI contract: {ui_size:,} bytes  ({t5e - t5:.1f}s)")

    # ── GO / NO-GO assessment ─────────────────────────────────────
    print("\n" + "=" * 60)
    print("GO / CONDITIONAL GO / NO-GO assessment")
    print("=" * 60)

    # CI gate: n>=100 AND CI width <=0.20 AND CI non-null
    ci_qualified = ci_eligible[(ci_eligible["nUpstreamLate"] >= 100) & ((ci_eligible["wilsonCI_high"] - ci_eligible["wilsonCI_low"]) <= 0.20)]

    hard_checks = {
        "chain_links_549388": int(len(links)) == 549_388,
        "no_negative_turns": int(integrity["negative_actual_turn_steps"]) == 0,
        "no_utc_reversal": int(integrity["utc_reversed"]) == 0,
        "no_invalid_episode_times": int(integrity["invalid_episode_times"]) == 0,
        "no_overlapping_episodes_same_tail": int(integrity["overlapping_episodes"]) == 0,
        "airport_path_continuity": int(integrity["airport_path_discontinuities"]) == 0,
        "no_gaps_as_recovered": int(integrity["gaps_marked_recovered"]) == 0,
        "recovery_not_continuing_old_episodes": int(integrity.get("recovery_not_continuing", 0)) == 0,
        "continuity_boundaries_not_recovered": int(integrity["continuity_boundaries_marked_recovered"]) == 0,
        "episode_duration_within_limit": int(integrity["episode_duration_limit_violations"]) == 0,
        "step_turn_within_limit": int(integrity["scheduled_turn_limit_violations"]) == 0,
    }

    product_checks = {
        "n_episodes_gte_10000": int(len(episodes)) >= 10_000,
        "n_deep2_gte_1000": int((episodes["depth"] >= 2).sum()) >= 1_000,
        "n_deep3_gte_100": int((episodes["depth"] >= 3).sum()) >= 100,
        "airports_exposed500_gte_40": int((airport_roles["nExposed"] >= 500).sum()) >= 40,
        "links_qualified100_gte_50": int((l1["nUpstreamLate"] >= 100).sum()) >= 50,
        "links_ci020_n100_gte_30": len(ci_qualified) >= 30,
        "thresholds_analyzed": len(sens) == 3,
        "cases_each_5plus": all(len(v) >= 5 for v in candidates.values()),
    }

    all_hard = all(hard_checks.values())
    all_product = all(product_checks.values())
    product_pass_rate = sum(product_checks.values()) / len(product_checks)

    if all_hard and all_product:
        verdict = "GO"
    elif all_hard and product_pass_rate >= 0.7:
        verdict = "CONDITIONAL GO"
    else:
        verdict = "NO-GO"

    print(f"  Hard checks: {hard_checks}")
    print(f"  Product checks: {product_checks}")
    print(f"  Verdict: {verdict}")

    sensitivity_rows = "\n".join(
        "| {threshold:.0f} | {nEpisodes:.0f} | {nDeep2:.0f} | {nDeep3:.0f} | "
        "{maxDepth:.0f} | {nAirportsExposed500:.0f} |".format(**row)
        for row in sens.to_dict(orient="records")
    )
    hard_rows = "\n".join(
        f"| `{name}` | {'通过' if passed else '失败'} |"
        for name, passed in hard_checks.items()
    )
    product_rows = "\n".join(
        f"| `{name}` | {'通过' if passed else '失败'} |"
        for name, passed in product_checks.items()
    )
    report = f"""# V1-P0 传播机制与 Shockwave 数据可行性审计

**判定：{verdict}**

## 1. 执行摘要

在冻结的 549,388 条 P0 轮转链边上，发布 {len(episodes):,} 个通过完整性门槛的 episode 和 {len(steps):,} 个 step。另有 {len(rejections)} 个候选因同机尾号时间线冲突被排除并单独审计，不进入统计样本。

## 2. 数据边界

数据覆盖 2026 年 5 月 BTS 美国国内定期、不经停客运航班。所有结果均为观察性描述，不代表因果关系，也不代表全球航空网络。

## 3. Episode 定义

当上一航段到达延误达到 15 分钟时开始观察；后续起飞延误仍达到阈值则传播，起飞或到达恢复至阈值以下则恢复。正式 episode 只允许计划停场不超过 {EPISODE_MAX_SCHEDULED_TURN_MINUTES} 分钟，且总观察时长不超过 {EPISODE_MAX_DURATION_HOURS} 小时；长停场、时长到限、机场链断裂和序列末端均属于删失，不伪装成恢复。无法形成单一物理时间线的候选不发布为 episode。物理轮转链仍保留 P0 的 720 分钟上限，不与传播 episode 边界混用。

## 4. 完整性审计

| 硬门槛 | 结果 |
|---|---:|
{hard_rows}

发布产物中的同机尾号 episode 重叠数为 {integrity['overlapping_episodes']}；UTC 倒序 {integrity['utc_reversed']}；路径断裂 {integrity['airport_path_discontinuities']}；恢复后继续计数 {integrity['recovery_not_continuing']}；超过 {EPISODE_MAX_DURATION_HOURS} 小时 {integrity['episode_duration_limit_violations']}；步骤计划停场超过 {EPISODE_MAX_SCHEDULED_TURN_MINUTES} 分钟 {integrity['scheduled_turn_limit_violations']}；连续性边界误记恢复 {integrity['continuity_boundaries_marked_recovered']}。

## 5. Episode 规模与结局

- Episodes：{len(episodes):,}
- Recovered：{int(episodes['outcome'].eq('recovered').sum()):,}
- Censored：{int(episodes['outcome'].eq('censored').sum()):,}
- 深度 ≥2：{int(episodes['depth'].ge(2).sum()):,}
- 深度 ≥3：{int(episodes['depth'].ge(3).sum()):,}
- 最大深度：{int(episodes['depth'].max())}
- 时间线冲突排除：{len(rejections)}
- 计划长停场截断：{int(episodes['terminationReason'].eq('scheduled_turn_break').sum()):,}
- {EPISODE_MAX_DURATION_HOURS} 小时时长截断：{int(episodes['terminationReason'].eq('duration_limit').sum()):,}

## 6. 有向传播链路

L1 `turnAirport -> nextDestination` 共 {len(l1):,} 条；其中上游晚到暴露 ≥100 的链路 {int(l1['nUpstreamLate'].ge(100).sum()):,} 条。推荐正式展示使用 `nUpstreamLate >= 100` 并同时显示 Wilson 95% 区间。

## 7. 样本门槛与区间

CI 门槛同时要求 `nUpstreamLate >= 100` 且区间宽度 ≤0.20；符合条件的链路为 {len(ci_qualified):,} 条。小于 5 个样本的区间保留为空，不作为合格项。

## 8. 条件传播差异

仅纳入同时存在 upstream-late 与 upstream-not-late 的可比 `(turnAirport, 2-hour bin)` strata。可比 strata {cond_lift['comparableStrata']:,}，排除 {cond_lift['excludedStrata']:,}，覆盖率 {cond_lift['coverageRate']:.2%}，加权观察性差异 {cond_lift['weightedConditionalLift']:.4f}。

## 9. 机场机制维度

共计算 {len(airport_roles):,} 个机场，其中 {n_with_data} 个满足 `nExposed >= 500`。只有这些机场获得描述性 role label；其余标记为 `insufficient_sample`。V1 应优先展示连续维度，而不是把角色标签写成因果结论。

## 10. 阈值敏感性

| 阈值（分钟） | Episodes | 深度≥2 | 深度≥3 | 最大深度 | 暴露≥500机场 |
|---:|---:|---:|---:|---:|---:|
{sensitivity_rows}

15↔30 的传播率 Spearman 为 {cross_spearman['15vs30']}，Top 20 链路交集 {top20_overlap['15vs30']['overlap']}/20；15↔60 的 Spearman 为 {cross_spearman['15vs60']}，Top 20 交集 {top20_overlap['15vs60']['overlap']}/20。

独立 P0.1 连续性网格比较了计划停场 120/180/240 分钟与总时长 12/18/24 小时。18 与 24 小时在 180 分钟停场定义下的深度≥3数量仅相差约 0.1%；正式选择中心规格 180 分钟 + 18 小时，详见 `reports/V1_P01_CONTINUITY_AUDIT.md`。

## 11. 集中度

集中度严格按精确 `(turnAirport, nextDestination)` Top 20 链路计算，而不是扩展为这些机场的全部航班。完整机器可读结果由运行日志及派生表保留。

## 12. 案例候选

案例候选包含最深传播、高延误后恢复、跨 UTC 午夜、高压日、普通日和删失案例；每类数量为：{', '.join(f'{k}={len(v)}' for k, v in candidates.items())}。

## 13. UI 数据契约

`v1_p0_ui_contract.json` 不含动态时间戳，控制在 {ui_size:,} bytes。它只包含全国摘要、有限链路、机场机制维度和案例候选，不嵌入全量 episode。

## 14. 可复现性与限制

科学产物 SHA-256 写入独立 manifest；本次是否与前次相同：{hashes_match_previous}。运行时间和生成时间仅存在 manifest，不参与科学产物哈希。天气、机场拥堵及共同冲击尚未控制，所以传播率和 conditional lift 都不作因果解释。

## 15. 产品门槛与 V1 范围

| 产品门槛 | 结果 |
|---|---:|
{product_rows}

判定为 **{verdict}**。仅当全部硬门槛通过时才允许进入 V1-A / V1-B；V1-A 可实现机制总览、机场连续维度和可靠链路，V1-B 再加入 episode explorer 与阈值切换。
"""
    (REPORT_DIR / "V1_P0_MECHANISM_AUDIT.md").write_text(
        report, encoding="utf-8"
    )

    # Clean up large objects
    del flights, links
    gc.collect()

    total = time.perf_counter() - t0
    print(f"\nTotal execution: {total:.1f}s")
    print(f"Outputs written to {OUT_DIR}/v1_p0_*")


if __name__ == "__main__":
    main()
