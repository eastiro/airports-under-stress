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

type WeatherMetric = { n: number; propagated: number; recovered: number; propagationRate: number | null; recoveryRate: number | null; wilson95: number[] | null };
type WeatherData = {
  defaultToleranceMinutes: number;
  tolerances: number[];
  national: Record<string, { matched: number; matchRate: number; maxWeatherAgeMinutes: number; adverse: WeatherMetric; nonAdverse: WeatherMetric; differencePercentagePoints: number }>;
  weatherCategories: Record<string, Array<WeatherMetric & { category: string }>>;
  airportComparisons: Record<string, Array<{ airport: string; adverse: WeatherMetric; nonAdverse: WeatherMetric; comparable: boolean; differencePercentagePoints: number | null; status: string }>>;
  insufficientSampleAirportsByTolerance: Record<string, string[]>;
  scope: { coreMappedAirports: number; coreTotalAirports: number; mechanismMappedAirports: number; mechanismTotalAirports: number; pbi: string };
};
type AdjustedWeatherModel = {
  nRows: number;
  nClusters: number;
  standardizedProbabilityDifferencePercentagePoints: number;
  clusterRobustCI95: number[];
};
export type V2BData = {
  version: string;
  gate1: string;
  tolerances: Record<string, {
    baseAdjustment: AdjustedWeatherModel;
    operatingConditions: AdjustedWeatherModel;
  }>;
  disclaimer: string;
};
type Props = {
  language: Language;
  data: V1AData;
  airportCitiesEn: Record<string, string>;
  weather: WeatherData;
  adjustedWeather: V2BData;
};

function pct(v: number, digits = 1) {
  return `${(v * 100).toFixed(digits)}%`;
}
function int(v: number) {
  return new Intl.NumberFormat("en-US").format(v);
}
function weatherCi(metric: WeatherMetric) {
  return metric.wilson95 ? `${pct(metric.wilson95[0])}–${pct(metric.wilson95[1])}` : "—";
}
export default function MechanismSection({ language, data, airportCitiesEn, weather, adjustedWeather }: Props) {
  const [weatherTolerance, setWeatherTolerance] = useState(90);
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
        intro: "上一班晚到后，我们继续跟踪同一架飞机：下一班是否仍晚点、这种状态连续了几次、最后有没有被追回。这里只描述现象，不判断延误是谁造成的。",
        summary: "先看全国：晚点连续了几次？",
        detailsSummary: "查看研究细节",
        detailsExtra: "连续航班要求计划停场不超过 180 分钟、整段不超过 18 小时。未观察到最终结果（观察中断）与时间线冲突排除的衔接不计入上面的主数字。",
        episodes: "识别出的连续延误段",
        deep2: "至少连续 2 次",
        deep3: "至少连续 3 次",
        maxDepth: "最长连续晚点次数",
        recovered: "后来恢复",
        censored: "未观察到最终结果",
        rejected: "时间线冲突排除",
        mechanismChart: "哪些机场更常接到晚点飞机？",
        chartX: "到达本站的飞机中，上一班晚到的比例",
        chartY: "上一班晚到后，下一班仍晚点的比例",
        chartSize: "圆点越大 = 观察到的晚到衔接次数越多",
        chartColor: "颜色 = 恢复率（绿高红低）",
        chartHintTR: "右上：经常接到晚点飞机，而且晚点更容易继续",
        chartHintBR: "右下：经常接到晚点飞机，但下一班相对更常追回",
        chartHintTL: "左上：接到晚点飞机不算多，但一旦发生就更容易继续晚点",
        selectAirport: "点击节点查看机场详情",
        exposure: "接到晚点飞机的比例",
        persistence: "晚到后仍延误起飞",
        recovery: "恢复率",
        caughtUp: "追回率",
        amplification: "放大率",
        deepEp2: "至少又连续晚点 2 次",
        reach: "连接到的下一站数量",
        sample: "晚到衔接样本",
        role: "机场表现类型",
        linksTitle: "样本较充足的延误传播航线",
        volumeView: "观察最多",
        vulnView: "考虑样本误差后仍较高",
        linkRoute: "周转机场 → 下一目的地",
        upstreamLate: "次上一班晚到的衔接",
        propRate: "传播率",
        ci95: "95% 估计范围",
        recoveredCount: "恢复数",
        showMore: "展开全部 20 条",
        showLess: "收起至精选 8 条",
        disclaimer: "本章的传播指标本身就是描述性观察，不代表因果；后面做的天气与排班比较，同样只描述差异，不等于因果控制。",
        insufficientSample: "样本不足",
        weatherTitle: "天气不好时，延误更容易继续吗？",
        weatherIntro: "恶劣天气组里，下一班仍然晚点的比例更高一些；两组相差只说明两件事同时出现，不能证明是天气造成的延误。",
        adverse: "出现恶劣天气条件", nonAdverse: "未出现这些条件", weatherRate: "下一班仍晚点", weatherN: "次衔接", weatherDiff: "两组相差",
        weatherAge: "天气报告匹配范围", weatherScope: "数据覆盖", weatherInsufficient: "恶劣天气样本不足",
        weatherAgeHelp: "60 / 90 分钟只向事件发生前找最近报告；范围越大匹配到的样本越多，也越偏离事件时刻。",
        weatherCategoryHelp: "下面每个百分比都是：触发该天气条件时，下一班仍晚点的比例；n 是符合条件的衔接次数。天气条件可能重叠。",
        weatherDiffHelp: "正数表示恶劣天气组更高，负数表示更低；1 个百分点就是 50% 与 51% 的差距。",
        weatherResearchSummary: "查看天气研究细节",
        weatherAdjustedSummary: "查看调整分析",
        weatherAdjustedOneLiner: "把机场、时段、航司等条件拉平后，两组差距仍在——但这不代表天气造成了延误。",
        adjustedTitle: "把其他可观察条件放进来后，差距还剩多少？",
        adjustedIntro: "先看两组直接相减，再逐步比较条件更相近的衔接。数字表示模型中的平均概率差，不是单个航班的预测。",
        rawComparison: "直接比较",
        baseAdjustment: "机场与时段相近",
        operatingAdjustment: "运营条件也相近",
        baseAdjustmentHelp: "考虑周转机场、计划起飞 UTC 时段和星期",
        operatingAdjustmentHelp: "再考虑航司、计划周转时间和上一航段晚到程度",
        estimateRange: "95% 估计范围",
        estimateRangeHelp: "范围越窄，说明这个平均差距估计得越稳定；它不是单个航班可能出现的范围。",
        adjustmentWhy: "调整后的数字不一定比直接比较更小：如果两组原本集中在不同机场、时段或运营条件，放到相近条件下比较后，隐藏的差距反而可能显出来。",
        adjustedBoundary: "这些结果只说明可观察条件相近时，两组仍有差异。模型没有覆盖每次天气系统、空管、跑道容量等因素，不能把差异解释成天气造成的延误。",
      }
    : {
        section: "05 / Propagation mechanism",
        title: "How far does delay travel?",
        intro: "When the same aircraft arrives late, we keep following it: does the next flight stay late, how many legs in a row, and where does it get recovered? This only describes what happened, not who caused the delay.",
        summary: "National continuous-delay summary",
        detailsSummary: "View research details",
        detailsExtra: "Episodes require planned turns of at most 180 minutes and last no more than 18 hours. Handoffs whose outcome was unobserved (censored) or excluded for timeline conflicts are not counted in the headline numbers above.",
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
        disclaimer: "The propagation metrics here are descriptive observations, not causal claims; the later weather and scheduling comparisons also describe differences but are not causal controls.",
        insufficientSample: "Insufficient sample",
        weatherTitle: "Weather stratification",
        weatherIntro: "In the adverse-weather group, a larger share of next flights stayed late. The gap only shows two things happening together; it does not prove weather caused the delay.",
        adverse: "Candidate adverse", nonAdverse: "Non-adverse", weatherRate: "Next flight still late", weatherN: "connections", weatherDiff: "Gap",
        weatherAge: "Weather-report matching window", weatherScope: "Data coverage", weatherInsufficient: "Insufficient adverse-weather sample",
        weatherAgeHelp: "60 / 90 minutes look only for the latest report issued before the event; a wider window matches more cases but sits further from the event.",
        weatherCategoryHelp: "Each percentage below is the share whose next flight was still late when that condition was present; n is the number of connections. Conditions may overlap.",
        weatherDiffHelp: "Positive means the adverse group is higher; negative means lower. One percentage point is the difference between 50% and 51%.",
        weatherResearchSummary: "View weather research details",
        weatherAdjustedSummary: "View adjustment analysis",
        weatherAdjustedOneLiner: "After leveling out airport, time, and carrier conditions, the gap remains — but this still does not mean weather caused the delay.",
        adjustedTitle: "How much remains after observable adjustment?",
        adjustedIntro: "Start with the raw group difference, then compare links under increasingly similar observed conditions. These are model-average probability differences, not flight predictions.",
        rawComparison: "Raw comparison",
        baseAdjustment: "Similar airport and time",
        operatingAdjustment: "Similar operating conditions",
        baseAdjustmentHelp: "Airport, scheduled UTC hour, and weekday",
        operatingAdjustmentHelp: "Plus carrier, scheduled turn band, and upstream-delay severity",
        estimateRange: "95% estimate range",
        estimateRangeHelp: "A narrower range means the average difference is estimated more precisely; it is not a range for individual flights.",
        adjustmentWhy: "Adjustment does not have to shrink the number: accounting for where and when the two groups occur can reveal a difference hidden in the raw comparison.",
        adjustedBoundary: "This is an adjusted descriptive association. Weather systems, air-traffic control, runway capacity, and other unobserved factors remain outside the model, so the difference is not a causal weather effect.",
      };

  const s = data.nationalSummary;
  const links = linkView === "volume" ? data.highVolumeLinks : data.highVulnerabilityLinks;
  const visibleLinks = showAllLinks ? links : links.slice(0, 8);
  const selected = selectedAirport ? data.airportMechanismDimensions.find(a => a.code === selectedAirport) : undefined;
  const nationalWeather = weather.national[String(weatherTolerance)];
  const adjustedModels = adjustedWeather.tolerances[String(weatherTolerance)];
  const airportWeatherRows = weather.airportComparisons[String(weatherTolerance)];
  const selectedWeather = airportWeatherRows.find(item => item.airport === selectedAirport);
  const weatherCategoryLabels: Record<string, string> = language === "zh" ? {
    low_visibility: "低能见度", low_ceiling: "低云底", strong_wind: "强风",
    precipitation: "降水", thunderstorm: "雷暴", fog: "雾 / 轻雾",
  } : {
    low_visibility: "Low visibility", low_ceiling: "Low ceiling", strong_wind: "Strong wind",
    precipitation: "Precipitation", thunderstorm: "Thunderstorm", fog: "Fog / mist",
  };
  const cityOf = (code: string) => language === "zh"
    ? (AIRPORT_ZH[code]?.city ?? airportCitiesEn[code] ?? code)
    : (airportCitiesEn[code] ?? code);
  const roleOf = (role: string) => language === "zh" ? ({
    absorbing: "较常追回",
    persistent: "较常延续",
    high_exposure: "较常接到晚点飞机",
    low_exposure: "较少接到晚点飞机",
  }[role] ?? role) : role;

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
          <div><strong>{int(s.nDeep3)}</strong><small>{labels.deep3}</small></div>
          <div><strong>{s.maxDepth}</strong><small>{labels.maxDepth}</small></div>
        </div>
      </div>

      <details className="clarity-details mechanism-details">
        <summary>{labels.detailsSummary}</summary>
        <div className="clarity-details-inner">
          <p>{labels.detailsExtra}</p>
          <div className="mechanism-stats mechanism-stats-extra">
            <div><strong>{int(s.nDeep2)}</strong><small>{labels.deep2}</small></div>
            <div><strong>{int(s.episodesRecovered)}</strong><small>{labels.recovered}</small></div>
            <div><strong>{int(s.episodesCensored)}</strong><small>{labels.censored}</small></div>
            <div><strong>{s.episodesRejectedTimelineConflict}</strong><small>{labels.rejected}</small></div>
          </div>
        </div>
      </details>

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
          <text x={W / 2} y={H - 12} textAnchor="middle" fill="var(--muted)" fontSize="12">{labels.chartX}</text>
          <text x={12} y={H / 2} textAnchor="middle" fill="var(--muted)" fontSize="12" transform={`rotate(-90 12 ${H / 2})`}>{labels.chartY}</text>
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
                  <text x={cx} y={cy - r - 3} textAnchor="middle" fill="var(--ink)" fontSize="12" fontWeight="700">{a.code}</text>
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
            <small>{selected.roleLabel !== "insufficient_sample" ? roleOf(selected.roleLabel) : labels.insufficientSample}</small>
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

      {/* Weather stratification */}
      <div className="weather-stratification" id="weather-stratification">
        <div className="weather-stratification-heading">
          <div><span className="section-kicker">V2-A</span><h3>{labels.weatherTitle}</h3></div>
          <p>{labels.weatherIntro}</p>
        </div>
        <p className="weather-reading-guide">{labels.weatherAgeHelp}</p>
        <div className="weather-toolbar">
          <div className="weather-tolerance-toggle" role="radiogroup" aria-label={language === "zh" ? "全国天气报告匹配范围" : labels.weatherAge}>
            {weather.tolerances.map(value => (
              <button type="button" key={value} role="radio" aria-checked={weatherTolerance === value} className={weatherTolerance === value ? "active" : ""} onClick={() => setWeatherTolerance(value)}>{value} min</button>
            ))}
          </div>
        </div>
        <div className="weather-national-grid">
          <div><small>{labels.adverse}</small><strong>{pct(nationalWeather.adverse.propagationRate ?? 0)}</strong><span>{int(nationalWeather.adverse.n)} {labels.weatherN}</span></div>
          <div><small>{labels.nonAdverse}</small><strong>{pct(nationalWeather.nonAdverse.propagationRate ?? 0)}</strong><span>{int(nationalWeather.nonAdverse.n)} {labels.weatherN}</span></div>
          <div><small>{labels.weatherDiff}</small><strong>{nationalWeather.differencePercentagePoints.toFixed(2)}{language === "zh" ? " 个百分点" : " pp"}</strong><span>{labels.weatherDiffHelp}</span></div>
        </div>
        <p className="weather-adjusted-oneliner">{labels.weatherAdjustedOneLiner}</p>

        <details className="clarity-details weather-details">
          <summary>{labels.weatherResearchSummary}</summary>
          <div className="clarity-details-inner">
            <p>{labels.weatherCategoryHelp}</p>
            <label className="weather-airport-select">
              <span>{language === "zh" ? "机场天气详情" : "Airport weather detail"}</span>
              <select value={selectedAirport ?? ""} onChange={event => setSelectedAirport(event.target.value)}>
                {airportWeatherRows.map(item => <option key={item.airport} value={item.airport}>{item.airport} · {cityOf(item.airport)}</option>)}
              </select>
            </label>
            <div className="weather-category-row">
              {weather.weatherCategories[String(weatherTolerance)].map(item => <div key={item.category}><strong>{weatherCategoryLabels[item.category]}</strong><span>{language === "zh" ? `传播率 ${pct(item.propagationRate ?? 0)} · ${int(item.n)} 次衔接` : `${pct(item.propagationRate ?? 0)} propagation · n=${int(item.n)}`}</span></div>)}
            </div>
            {selectedWeather && (
              <div className={`weather-selected-airport ${selectedWeather.comparable ? "is-comparable" : "is-insufficient"}`}>
                <div className="weather-selected-heading"><div><strong>{selectedWeather.airport}</strong><span>{cityOf(selectedWeather.airport)}</span></div><small>{selectedWeather.comparable ? (language === "zh" ? "两组都至少有 50 次衔接" : "Both strata meet n ≥ 50") : labels.weatherInsufficient}</small></div>
                <div className="weather-selected-grid">
                  <div><span>{labels.adverse}</span><strong>{selectedWeather.adverse.propagationRate === null ? "—" : pct(selectedWeather.adverse.propagationRate)}</strong><small>{language === "zh" ? `${int(selectedWeather.adverse.n)} 次衔接 · 95% 估计范围` : `n=${int(selectedWeather.adverse.n)} · Wilson 95% CI`} {weatherCi(selectedWeather.adverse)}</small></div>
                  <div><span>{labels.nonAdverse}</span><strong>{selectedWeather.nonAdverse.propagationRate === null ? "—" : pct(selectedWeather.nonAdverse.propagationRate)}</strong><small>{language === "zh" ? `${int(selectedWeather.nonAdverse.n)} 次衔接 · 95% 估计范围` : `n=${int(selectedWeather.nonAdverse.n)} · Wilson 95% CI`} {weatherCi(selectedWeather.nonAdverse)}</small></div>
                  <div><span>{labels.weatherDiff}</span><strong>{selectedWeather.differencePercentagePoints === null ? "—" : `${selectedWeather.differencePercentagePoints.toFixed(2)}${language === "zh" ? " 个百分点" : " pp"}`}</strong><small>{selectedWeather.comparable ? (language === "zh" ? "只比较两组现象，不判断原因或好坏" : "No causal or winner/loser interpretation") : (language === "zh" ? `固定门槛：每组至少 50 次；当前恶劣天气组 ${selectedWeather.adverse.n} 次` : `Fixed rule: n ≥ 50 per stratum; adverse n=${selectedWeather.adverse.n}`)}</small></div>
                </div>
              </div>
            )}
            <div className="weather-airport-browser" aria-label={language === "zh" ? "55 个机制机场天气差异" : "Weather differences for 55 mechanism airports"}>
              {airportWeatherRows.map(item => <button type="button" key={item.airport} className={selectedAirport === item.airport ? "is-selected" : ""} onClick={() => setSelectedAirport(item.airport)}><b>{item.airport}</b><span>{item.comparable ? `${item.differencePercentagePoints?.toFixed(1)}${language === "zh" ? " 个百分点" : " pp"}` : (language === "zh" ? `恶劣天气组仅 ${item.adverse.n} 次` : `insufficient · ${item.adverse.n}/50`)}</span></button>)}
            </div>
            <p className="weather-scope-note">{language === "zh" ? `数据覆盖：核心机场 ${weather.scope.coreMappedAirports}/${weather.scope.coreTotalAirports}；本页分析机场 ${weather.scope.mechanismMappedAirports}/${weather.scope.mechanismTotalAirports}。PBI 因没有可用气象站映射而未纳入。天气类别可能重叠，不能相加；结果只描述同时出现的现象。` : `${labels.weatherScope}: ${weather.scope.coreMappedAirports}/${weather.scope.coreTotalAirports} Core · ${weather.scope.mechanismMappedAirports}/${weather.scope.mechanismTotalAirports} Mechanism · PBI ${weather.scope.pbi}. Weather categories overlap and must not be added. Stratification is not causal attribution.`}</p>
            <p>{language === "zh" ? "每一组的“下一班仍晚点”比例都带有 95% 估计范围（Wilson 区间），样本越小范围越宽。" : "Each group's “next flight still late” share carries a 95% estimate range (Wilson interval); smaller samples give wider ranges."}</p>
          </div>
        </details>

        <details className="clarity-details weather-adjusted-details">
          <summary>{labels.weatherAdjustedSummary}</summary>
          <div className="clarity-details-inner">
            <div className="weather-adjusted-block">
              <div className="weather-adjusted-heading">
                <div><span className="section-kicker">V2-B</span><h4>{labels.adjustedTitle}</h4></div>
                <p>{labels.adjustedIntro}</p>
              </div>
              <div className="weather-adjusted-flow">
                <article>
                  <small>01 · {labels.rawComparison}</small>
                  <strong>{nationalWeather.differencePercentagePoints.toFixed(2)} {language === "zh" ? "个百分点" : "pp"}</strong>
                  <span>{language === "zh" ? "恶劣天气组与非恶劣天气组直接相减" : "Adverse minus non-adverse, without adjustment"}</span>
                </article>
                <i aria-hidden="true">→</i>
                <article>
                  <small>02 · {labels.baseAdjustment}</small>
                  <strong>{adjustedModels.baseAdjustment.standardizedProbabilityDifferencePercentagePoints.toFixed(2)} {language === "zh" ? "个百分点" : "pp"}</strong>
                  <span>{labels.baseAdjustmentHelp}</span>
                  <em>{labels.estimateRange} {(adjustedModels.baseAdjustment.clusterRobustCI95[0] * 100).toFixed(2)}–{(adjustedModels.baseAdjustment.clusterRobustCI95[1] * 100).toFixed(2)}</em>
                </article>
                <i aria-hidden="true">→</i>
                <article className="is-primary">
                  <small>03 · {labels.operatingAdjustment}</small>
                  <strong>{adjustedModels.operatingConditions.standardizedProbabilityDifferencePercentagePoints.toFixed(2)} {language === "zh" ? "个百分点" : "pp"}</strong>
                  <span>{labels.operatingAdjustmentHelp}</span>
                  <em>{labels.estimateRange} {(adjustedModels.operatingConditions.clusterRobustCI95[0] * 100).toFixed(2)}–{(adjustedModels.operatingConditions.clusterRobustCI95[1] * 100).toFixed(2)}</em>
                </article>
              </div>
              <p className="weather-estimate-help">{labels.estimateRangeHelp} {labels.adjustmentWhy}</p>
              <p className="weather-adjusted-boundary">{labels.adjustedBoundary}</p>
            </div>
          </div>
        </details>
      </div>

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
