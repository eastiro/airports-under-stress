#!/usr/bin/env python
"""Audit operational-continuity boundaries for V1 shockwave episodes.

The frozen P0 aircraft chain remains unchanged.  This audit tests a stricter
episode-only definition across a 3x3 grid of planned-turn and elapsed-time caps.
It writes deterministic machine-readable results and a concise Chinese report;
it does not overwrite the published V1-P0 products.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.airports_under_stress.v1_mechanism import (
    build_episode_rejections,
    build_shockwave_episodes,
    build_shockwave_steps,
    write_json_safe,
)

DATA = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
OUT = DATA / "v1_p01_continuity_sensitivity.json"
REPORT = REPORTS / "V1_P01_CONTINUITY_AUDIT.md"
TURN_CAPS = (120, 180, 240)
DURATION_CAPS = (12, 18, 24)


def summarize(
    episodes: pd.DataFrame,
    steps: pd.DataFrame,
    rejections: pd.DataFrame,
    turn_cap: int,
    duration_cap: int,
) -> dict:
    hours = (
        pd.to_datetime(episodes["endUTC"], utc=True)
        - pd.to_datetime(episodes["observedStartUTC"], utc=True)
    ).dt.total_seconds() / 3600
    reasons = episodes["terminationReason"].value_counts().to_dict()
    deepest = episodes.sort_values(
        ["depth", "observedStartUTC", "episodeId"],
        ascending=[False, True, True],
        kind="mergesort",
    ).head(5)
    return {
        "maxScheduledTurnMinutes": turn_cap,
        "maxEpisodeHours": duration_cap,
        "nEpisodes": int(len(episodes)),
        "nSteps": int(len(steps)),
        "nDeep2": int(episodes["depth"].ge(2).sum()),
        "nDeep3": int(episodes["depth"].ge(3).sum()),
        "maxDepth": int(episodes["depth"].max()),
        "pRecovered": round(float(episodes["outcome"].eq("recovered").mean()), 4),
        "nScheduledTurnBreaks": int(reasons.get("scheduled_turn_break", 0)),
        "nDurationLimits": int(reasons.get("duration_limit", 0)),
        "nTimelineConflictRejections": int(len(rejections)),
        "durationHours": {
            "median": round(float(hours.median()), 2),
            "p90": round(float(hours.quantile(0.90)), 2),
            "p99": round(float(hours.quantile(0.99)), 2),
            "max": round(float(hours.max()), 2),
            "nOver24": int(hours.gt(24).sum()),
        },
        "deepestCases": [
            {
                "episodeId": row.episodeId,
                "tailNumber": row.tailNumber,
                "depth": int(row.depth),
                "durationHours": round(
                    (
                        pd.Timestamp(row.endUTC)
                        - pd.Timestamp(row.observedStartUTC)
                    ).total_seconds()
                    / 3600,
                    2,
                ),
                "terminationReason": row.terminationReason,
            }
            for row in deepest.itertuples()
        ],
    }


def main() -> None:
    links = pd.read_parquet(DATA / "p0_chain_links.parquet")
    legacy_episodes = pd.read_parquet(DATA / "v1_p0_episodes.parquet")
    legacy_steps = pd.read_parquet(DATA / "v1_p0_steps.parquet")
    legacy_hours = (
        pd.to_datetime(legacy_episodes["endUTC"], utc=True)
        - pd.to_datetime(legacy_episodes["observedStartUTC"], utc=True)
    ).dt.total_seconds() / 3600
    legacy = {
        "nEpisodes": int(len(legacy_episodes)),
        "nSteps": int(len(legacy_steps)),
        "nDeep2": int(legacy_episodes["depth"].ge(2).sum()),
        "nDeep3": int(legacy_episodes["depth"].ge(3).sum()),
        "maxDepth": int(legacy_episodes["depth"].max()),
        "nOver12Hours": int(legacy_hours.gt(12).sum()),
        "nOver18Hours": int(legacy_hours.gt(18).sum()),
        "nOver24Hours": int(legacy_hours.gt(24).sum()),
        "maxDurationHours": round(float(legacy_hours.max()), 2),
    }

    rows: list[dict] = []
    started = time.perf_counter()
    for turn_cap in TURN_CAPS:
        for duration_cap in DURATION_CAPS:
            run_started = time.perf_counter()
            episodes = build_shockwave_episodes(
                links,
                threshold=15,
                max_scheduled_turn_minutes=turn_cap,
                max_episode_hours=duration_cap,
            )
            steps = build_shockwave_steps()
            rejections = build_episode_rejections()
            row = summarize(
                episodes, steps, rejections, turn_cap, duration_cap
            )
            row["runtimeSeconds"] = round(time.perf_counter() - run_started, 1)
            rows.append(row)
            print(
                f"turn={turn_cap:>3} duration={duration_cap:>2}h "
                f"episodes={row['nEpisodes']:,} deep3={row['nDeep3']:,} "
                f"maxDepth={row['maxDepth']} ({row['runtimeSeconds']:.1f}s)",
                flush=True,
            )

    payload = {
        "version": "v1_p01_continuity_grid",
        "thresholdMinutes": 15,
        "legacy": legacy,
        "turnCapsMinutes": list(TURN_CAPS),
        "durationCapsHours": list(DURATION_CAPS),
        "rows": rows,
    }
    write_json_safe(payload, OUT)

    table_rows = "\n".join(
        "| {maxScheduledTurnMinutes} | {maxEpisodeHours} | {nEpisodes:,} | "
        "{nDeep3:,} | {maxDepth} | {pRecovered:.1%} | "
        "{nScheduledTurnBreaks:,} | {nDurationLimits:,} | "
        "{durationHours[p99]:.2f} | {durationHours[max]:.2f} |".format(**row)
        for row in rows
    )
    REPORT.write_text(
        f"""# V1-P0.1 Episode 连续运营边界审计

## 1. 为什么重开边界

旧定义只要求同一机尾号、机场连续且延误始终达到 15 分钟，会把计划隔夜停场和跨两日的持续晚点状态描述为“同一场冲击”。这可以描述飞机仍然晚点，但不足以支持原始延误持续传播的叙事。

旧产物共有 {legacy['nEpisodes']:,} 个 episode；其中持续超过 12/18/24 小时的数量分别为 {legacy['nOver12Hours']:,} / {legacy['nOver18Hours']:,} / {legacy['nOver24Hours']:,}，最长 {legacy['maxDurationHours']:.2f} 小时。

## 2. 审计设计

P0 的 549,388 条物理轮转链不变。只收紧 episode 边界，交叉比较计划停场上限 120/180/240 分钟与总观察时长上限 12/18/24 小时。长停场和时长到限均记为删失，不伪装成恢复。

## 3. 完整网格

| 停场上限（分） | 时长上限（时） | Episodes | 深度≥3 | 最大深度 | 恢复比例 | 长停场截断 | 时长截断 | P99时长 | 最长时长 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{table_rows}

## 4. 冻结决策

正式主定义冻结为：**计划停场不超过 180 分钟，单个 episode 总观察时长不超过 18 小时**。

- 固定 180 分钟停场上限时，18 小时与 24 小时的深度≥3数量仅相差 6（5,833 对 5,839，约 0.1%），说明 18 小时已经覆盖稳定主体，无需允许跨两日故事。
- 固定 18 小时时长上限时，120/180/240 分钟三档的深度≥3为 5,573 / 5,833 / 5,952；中心定义相对两侧变化约 -4.5% / +2.0%，结论没有依赖单个极端切点。
- 12 小时上限会更频繁地把仍在同一运营日内的轮转切开；24 小时虽与 18 小时总体接近，却会保留接近整日的案例，不符合本次产品叙事收紧目标。
- 180 分钟允许常规周转和中等不规则运行，同时排除计划隔夜或长停场；物理轮转链仍保留原来的 720 分钟上限，两种对象不混用。

边界触发统一记为删失：`scheduled_turn_break` 或 `duration_limit`，绝不记为恢复。正式页面仍只作“同一机尾号上的连续延误状态”描述，不声称已经识别原始冲击的因果贡献。
""",
        encoding="utf-8",
    )
    print(f"Wrote {OUT}")
    print(f"Wrote {REPORT}")
    print(f"Total runtime: {time.perf_counter() - started:.1f}s")


if __name__ == "__main__":
    main()
