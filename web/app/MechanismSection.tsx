"use client";

import { useState } from "react";
import type { Language } from "./dashboard";
import { AIRPORT_ZH } from "./airport-names-zh";

export type V1AData = {
  version: string;
  nationalSummary: {
    period: string;
    totalChainLinks: number;
    upstreamLateExposures: number;
    basePropagationRate: number;
    baseRecoveryRate: number;
    nEpisodes: number;
    nDeep2: number;
    nDeep3: number;
    maxDepth: number;
    meanDepth: number;
    episodesRecovered: number;
    episodesCensored: number;
    episodesRejectedTimelineConflict: number;
    nAirportsExposed500: number;
    nLinksQualified100: number;
  };
  recommendedThreshold: number;
  recommendedLinkThreshold: number;
  airportMechanismDimensions: AirportDim[];
  highVolumeLinks: DirectedLink[];
  highVulnerabilityLinks: DirectedLink[];
  fieldNotes: Record<string, string>;
  disclaimer: string;
};

type AirportDim = {
  code: string;
  exposureRate: number;
  persistenceRate: number;
  recoveryRate: number;
  caughtUpRate: number;
  amplificationRate: number;
  medianDelayDelta: number;
  p90DelayDelta: number;
  deepEpisodeRate2plus: number;
  deepEpisodeRate3plus: number;
  outgoingReach: number;
  nExposed: number;
  nEdges: number;
  totalEpisodes: number;
  roleLabel: string;
};

type DirectedLink = {
  turnAirport: string;
  nextDestination: string;
  nTotal: number;
  nUpstreamLate: number;
  nPropagated: number;
  nRecovered: number;
  pPropGivenLate: number;
  wilsonCI_low: number | null;
  wilsonCI_high: number | null;
  conditionalDiff: number;
};

type Props = {
  language: Language;
  data: V1AData;
  airportCitiesEn: Record<string, string>;
};

function pct(v: number, digits = 1) {
  return `${(v * 100).toFixed(digits)}%`;
}
function int(v: number) {
  return new Intl.NumberFormat("en-US").format(v);
}
export default function MechanismSection({ language, data, airportCitiesEn }: Props) {
  const [linkView, setLinkView] = useState<"volume" | "vulnerability">("volume");
  const [showAllLinks, setShowAllLinks] = useState(false);
  const [selectedAirport, setSelectedAirport] = useState<string | null>(() =>
    data.airportMechanismDimensions.reduce(
      (best, airport) => airport.nExposed > best.nExposed ? airport : best,
    ).code,
  );

  const labels = language === "zh"
    ? {
        section: "05 / 传播机制",
        title: "延误会走多远？",
        intro: "当同一架飞机上一航段晚到后，延误状态在后续轮转中持续了多深、沿哪些真实路径延续、在哪里被吸收。Episode 限制为计划停场不超过 180 分钟且总时长不超过 18 小时；以下均为描述性分析，不构成因果结论。",
        summary: "全国连续延误摘要",
        episodes: "连续状态 episode",
        deep2: "深度 ≥2",
        deep3: "深度 ≥3",
        maxDepth: "最大深度",
        recovered: "已恢复",
        censored: "观察中断",
        rejected: "时间线冲突排除",
        mechanismChart: "机场机制图",
        chartX: "上游晚到暴露率",
        chartY: "晚到后持续传播率",
        chartSize: "节点大小 = 上游暴露数",
        chartColor: "颜色 = 恢复率（绿高红低）",
        chartHintTR: "右上：经常接到晚点飞机，而且晚点更容易继续",
        chartHintBR: "右下：暴露较多，但相对更能吸收",
        chartHintTL: "左上：暴露不算最多，但一旦晚到更容易持续",
        selectAirport: "点击节点查看机场详情",
        exposure: "暴露率",
        persistence: "持续传播率",
        recovery: "恢复率",
        caughtUp: "追回率",
        amplification: "放大率",
        deepEp2: "深层 episode 率（≥2）",
        reach: "出向覆盖",
        sample: "样本量",
        role: "角色标签",
        linksTitle: "可靠传播链路",
        volumeView: "观察最多",
        vulnView: "保守传播信号最高",
        linkRoute: "周转机场 → 下一目的地",
        upstreamLate: "上游晚到暴露",
        propRate: "传播率",
        ci95: "Wilson 95% CI",
        recoveredCount: "恢复数",
        showMore: "展开全部 20 条",
        showLess: "收起至精选 8 条",
        disclaimer: "所有指标均为 BTS 2026 年 5 月数据的描述性观察。不做因果声明。天气和机场拥堵未控制。",
        insufficientSample: "样本不足",
      }
    : {
        section: "05 / Propagation mechanism",
        title: "How far does delay travel?",
        intro: "When the same aircraft arrives late, how deep does the late state persist through subsequent rotations, and where is it absorbed? Episodes require planned turns of at most 180 minutes and last no more than 18 hours. All results are descriptive, not causal.",
        summary: "National continuous-delay summary",
        episodes: "Continuous-state episodes",
        deep2: "Depth ≥2",
        deep3: "Depth ≥3",
        maxDepth: "Max depth",
        recovered: "Recovered",
        censored: "Censored",
        rejected: "Timeline conflicts excluded",
        mechanismChart: "Airport mechanism chart",
        chartX: "Upstream late exposure rate",
        chartY: "Post-exposure persistence rate",
        chartSize: "Node size = upstream exposure count",
        chartColor: "Color = recovery rate (green high, red low)",
        chartHintTR: "Top-right: frequently receives late aircraft, and delays tend to continue",
        chartHintBR: "Bottom-right: high exposure but relatively absorbing",
        chartHintTL: "Top-left: less exposed but once late, more likely to persist",
        selectAirport: "Click a node for airport detail",
        exposure: "Exposure rate",
        persistence: "Persistence rate",
        recovery: "Recovery rate",
        caughtUp: "Caught-up rate",
        amplification: "Amplification rate",
        deepEp2: "Deep episode rate (≥2)",
        reach: "Outgoing reach",
        sample: "Sample size",
        role: "Role label",
        linksTitle: "Reliable propagation links",
        volumeView: "High volume",
        vulnView: "Conservative vulnerability",
        linkRoute: "Turn airport → Next destination",
        upstreamLate: "Upstream late exposures",
        propRate: "Propagation rate",
        ci95: "Wilson 95% CI",
        recoveredCount: "Recovered",
        showMore: "Show all 20 links",
        showLess: "Collapse to 8 highlights",
        disclaimer: "All metrics are descriptive observations from BTS May 2026 data. No causal claims. Weather and airport congestion not controlled.",
        insufficientSample: "Insufficient sample",
      };

  const s = data.nationalSummary;
  const links = linkView === "volume" ? data.highVolumeLinks : data.highVulnerabilityLinks;
  const visibleLinks = showAllLinks ? links : links.slice(0, 8);
  const selected = selectedAirport ? data.airportMechanismDimensions.find(a => a.code === selectedAirport) : undefined;
  const cityOf = (code: string) => language === "zh"
    ? (AIRPORT_ZH[code]?.city ?? airportCitiesEn[code] ?? code)
    : (airportCitiesEn[code] ?? code);

  // SVG scatter: 55 eligible airports
  // X: exposureRate [0, 1], Y: persistenceRate [0, 1]
  const W = 680, H = 360, PAD = 50;
  const xs = data.airportMechanismDimensions.map(a => a.exposureRate);
  const ys = data.airportMechanismDimensions.map(a => a.persistenceRate);
  const xRawMin = Math.min(...xs), xRawMax = Math.max(...xs);
  const yRawMin = Math.min(...ys), yRawMax = Math.max(...ys);
  const xPad = Math.max((xRawMax - xRawMin) * 0.08, 0.01);
  const yPad = Math.max((yRawMax - yRawMin) * 0.08, 0.01);
  const xMin = xRawMin - xPad, xMax = xRawMax + xPad;
  const yMin = yRawMin - yPad, yMax = yRawMax + yPad;
  const xScale = (v: number) => PAD + (v - xMin) / (xMax - xMin) * (W - 2 * PAD);
  const yScale = (v: number) => H - PAD - (v - yMin) / (yMax - yMin) * (H - 2 * PAD);
  const maxExposed = Math.max(...data.airportMechanismDimensions.map(a => a.nExposed));
  const median = (values: number[]) => {
    const sorted = [...values].sort((a, b) => a - b);
    return sorted[Math.floor(sorted.length / 2)];
  };
  const medianExposure = median(xs);
  const medianPersistence = median(ys);
  const priorityLabels = new Set(
    [...data.airportMechanismDimensions]
      .sort((a, b) => b.nExposed - a.nExposed)
      .slice(0, 9)
      .map(a => a.code),
  );

  return (
    <section className="analysis-section mechanism-section section-shell" id="mechanism">
      <div className="section-heading">
        <div>
          <span className="section-number">{labels.section}</span>
          <h2>{labels.title}</h2>
        </div>
        <p>{labels.intro}</p>
      </div>

      {/* National summary */}
      <div className="mechanism-summary">
        <span className="mechanism-summary-label">{labels.summary}</span>
        <div className="mechanism-stats">
          <div><strong>{int(s.nEpisodes)}</strong><small>{labels.episodes}</small></div>
          <div><strong>{int(s.nDeep2)}</strong><small>{labels.deep2}</small></div>
          <div><strong>{int(s.nDeep3)}</strong><small>{labels.deep3}</small></div>
          <div><strong>{s.maxDepth}</strong><small>{labels.maxDepth}</small></div>
          <div><strong>{int(s.episodesRecovered)}</strong><small>{labels.recovered}</small></div>
          <div><strong>{int(s.episodesCensored)}</strong><small>{labels.censored}</small></div>
          <div><strong>{s.episodesRejectedTimelineConflict}</strong><small>{labels.rejected}</small></div>
        </div>
      </div>

      {/* Airport mechanism chart */}
      <div className="mechanism-chart-block">
        <h3>{labels.mechanismChart}</h3>
        <div className="mechanism-chart-hints">
          <span>{labels.chartHintTR}</span>
          <span>{labels.chartHintBR}</span>
          <span>{labels.chartHintTL}</span>
        </div>
        <svg className="mechanism-chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={labels.mechanismChart}>
          {/* Axes */}
          <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="rgba(102,240,210,.2)" />
          <line x1={PAD} y1={PAD} x2={PAD} y2={H - PAD} stroke="rgba(102,240,210,.2)" />
          <text x={W / 2} y={H - 12} textAnchor="middle" fill="var(--muted)" fontSize="10">{labels.chartX}</text>
          <text x={12} y={H / 2} textAnchor="middle" fill="var(--muted)" fontSize="10" transform={`rotate(-90 12 ${H / 2})`}>{labels.chartY}</text>
          {/* Median lines */}
          <line x1={xScale(medianExposure)} y1={PAD} x2={xScale(medianExposure)} y2={H - PAD} stroke="rgba(102,240,210,.12)" strokeDasharray="3 3" />
          <line x1={PAD} y1={yScale(medianPersistence)} x2={W - PAD} y2={yScale(medianPersistence)} stroke="rgba(102,240,210,.12)" strokeDasharray="3 3" />
          {/* Nodes */}
          {data.airportMechanismDimensions.map(a => {
            const cx = xScale(a.exposureRate);
            const cy = yScale(a.persistenceRate);
            const r = 4 + (a.nExposed / maxExposed) * 12;
            // Green = high recovery, red = low recovery
            const hue = a.recoveryRate * 120; // 0=red, 120=green
            const color = `hsl(${hue}, 60%, 50%)`;
            return (
              <g
                key={a.code}
                role="button"
                tabIndex={0}
                aria-label={`${a.code} ${cityOf(a.code)}，${labels.exposure} ${pct(a.exposureRate)}，${labels.persistence} ${pct(a.persistenceRate)}`}
                onClick={() => setSelectedAirport(a.code)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    setSelectedAirport(a.code);
                  }
                }}
                style={{ cursor: "pointer" }}
              >
                <circle cx={cx} cy={cy} r={r} fill={color} fillOpacity={0.35} stroke={selectedAirport === a.code ? "var(--mint)" : color} strokeWidth={selectedAirport === a.code ? 2 : 1} />
                {(priorityLabels.has(a.code) || selectedAirport === a.code) && (
                  <text x={cx} y={cy - r - 3} textAnchor="middle" fill="var(--ink)" fontSize="10" fontWeight="700">{a.code}</text>
                )}
                <title>{`${a.code} ${cityOf(a.code)}: ${labels.exposure} ${pct(a.exposureRate)}, ${labels.persistence} ${pct(a.persistenceRate)}`}</title>
              </g>
            );
          })}
        </svg>
        <div className="mechanism-chart-legend">
          <span>{labels.chartSize}</span>
          <span>{labels.chartColor}</span>
        </div>
      </div>

      {/* Selected airport detail */}
      {selected && (
        <div className="mechanism-airport-detail" role="region" aria-label={`${selected.code} ${cityOf(selected.code)}`}>
          <div className="mechanism-detail-header">
            <strong>{selected.code}</strong>
            <span>{cityOf(selected.code)}</span>
            <small>{selected.roleLabel !== "insufficient_sample" ? selected.roleLabel : labels.insufficientSample}</small>
          </div>
          <div className="mechanism-detail-grid">
            <div><span>{labels.exposure}</span><strong>{pct(selected.exposureRate)}</strong></div>
            <div><span>{labels.persistence}</span><strong>{pct(selected.persistenceRate)}</strong></div>
            <div><span>{labels.recovery}</span><strong>{pct(selected.recoveryRate)}</strong></div>
            <div><span>{labels.caughtUp}</span><strong>{pct(selected.caughtUpRate)}</strong></div>
            <div><span>{labels.amplification}</span><strong>{pct(selected.amplificationRate)}</strong></div>
            <div><span>{labels.deepEp2}</span><strong>{pct(selected.deepEpisodeRate2plus)}</strong></div>
            <div><span>{labels.reach}</span><strong>{selected.outgoingReach}</strong></div>
            <div><span>{labels.sample}</span><strong>{int(selected.nExposed)}</strong></div>
          </div>
        </div>
      )}

      {/* Directed link views */}
      <div className="mechanism-links-block">
        <h3>{labels.linksTitle}</h3>
        <div className="link-view-toggle" role="tablist">
          <button type="button" role="tab" aria-selected={linkView === "volume"} className={linkView === "volume" ? "active" : ""} onClick={() => { setLinkView("volume"); setShowAllLinks(false); }}>{labels.volumeView}</button>
          <button type="button" role="tab" aria-selected={linkView === "vulnerability"} className={linkView === "vulnerability" ? "active" : ""} onClick={() => { setLinkView("vulnerability"); setShowAllLinks(false); }}>{labels.vulnView}</button>
        </div>
        <div className="link-list" role="list">
          {visibleLinks.map((link, i) => (
            <div className="link-row" role="listitem" key={`${link.turnAirport}-${link.nextDestination}-${i}`}>
              <div className="link-route">
                <strong>{link.turnAirport}</strong>
                <small>{cityOf(link.turnAirport)}</small>
                <span aria-hidden="true">→</span>
                <strong>{link.nextDestination}</strong>
                <small>{cityOf(link.nextDestination)}</small>
              </div>
              <div className="link-stats">
                <span><strong>{int(link.nUpstreamLate)}</strong> {labels.upstreamLate}</span>
                <span><strong>{pct(link.pPropGivenLate)}</strong> {labels.propRate}</span>
                <span><strong>{link.wilsonCI_low !== null && link.wilsonCI_high !== null ? `[${pct(link.wilsonCI_low)}, ${pct(link.wilsonCI_high)}]` : "—"}</strong> {labels.ci95}</span>
                <span><strong>{int(link.nRecovered)}</strong> {labels.recoveredCount}</span>
              </div>
            </div>
          ))}
        </div>
        <button className="link-list-more" type="button" aria-expanded={showAllLinks} onClick={() => setShowAllLinks(value => !value)}>
          {showAllLinks ? labels.showLess : labels.showMore}
        </button>
      </div>

      <p className="mechanism-disclaimer">{labels.disclaimer}</p>
    </section>
  );
}
