"use client";

import { useEffect, useMemo, useState, type CSSProperties } from "react";
import rawData from "./v0-data.json";

type Airport = {
  code: string;
  city: string;
  region: string;
  name: string;
  flights: number;
  delayRate: number;
  cancelRate: number;
  avgDelay: number;
  p90Delay: number;
  propagationRate: number;
  recoveryRate: number;
  chainLinks: number;
  pressureScore: number;
};

type Airline = {
  code: string;
  name: string;
  flights: number;
  delayRate: number;
  cancelRate: number;
  avgDelay: number;
  propagationRate: number;
  recoveryRate: number;
  chainLinks: number;
};

type DailyPoint = {
  date: string;
  day: number;
  flights: number;
  delayRate: number;
  cancelRate: number;
  avgDelay: number;
  propagationRate: number;
};

type StoryLeg = {
  flight: string;
  origin: string;
  dest: string;
  scheduled: string;
  depDelay: number | null;
  arrDelay: number;
  turn?: number;
  status: "propagated" | "recovered" | "delayed" | "on-time";
};

type Story = {
  id: string;
  type: string;
  title: string;
  summary: string;
  tail: string;
  date: string;
  edges: number;
  propagated: number;
  recovered: number;
  legs: StoryLeg[];
};

type SiteData = {
  meta: {
    period: string;
    records: number;
    airports: number;
    airlines: number;
    tails: number;
    chainLinks: number;
    source: string;
    coverage: string;
  };
  national: {
    delayRate: number;
    cancelRate: number;
    propagationRate: number;
    recoveryRate: number;
    peakDay: string;
  };
  daily: DailyPoint[];
  airports: Airport[];
  airlines: Airline[];
  stories: Story[];
};

type AirportSortKey =
  | "pressureScore"
  | "delayRate"
  | "propagationRate"
  | "flights"
  | "cancelRate";

type Language = "zh" | "en";

const data = rawData as SiteData;

const sortOptions: Array<{ key: AirportSortKey; zh: string; en: string }> = [
  { key: "pressureScore", zh: "压力指数", en: "Pressure" },
  { key: "delayRate", zh: "起飞延误", en: "Departure delay" },
  { key: "propagationRate", zh: "延误传播", en: "Propagation" },
  { key: "flights", zh: "航班量", en: "Volume" },
  { key: "cancelRate", zh: "取消率", en: "Cancellation" },
];

const storyLabels: Record<Language, Record<string, string>> = {
  zh: {
    cascade: "延误级联",
    recovery: "延误恢复",
    "tight-turn": "紧周转",
    mixed: "传播与恢复",
  },
  en: {
    cascade: "Cascade",
    recovery: "Recovery",
    "tight-turn": "Tight turn",
    mixed: "Mixed",
  },
};

const statusLabels: Record<Language, Record<StoryLeg["status"], string>> = {
  zh: {
    propagated: "已传播",
    recovered: "已恢复",
    delayed: "延误",
    "on-time": "准点",
  },
  en: {
    propagated: "propagated",
    recovered: "recovered",
    delayed: "delayed",
    "on-time": "on time",
  },
};

const ui = {
  zh: {
    skip: "跳至分析内容",
    home: "Airports Under Stress 首页",
    navLabel: "主要导航",
    airports: "机场",
    carriers: "航司",
    rotations: "轮转故事",
    method: "方法",
    period: "2026 年 5 月",
    eyebrow: "美国航空网络 / 事后分析",
    heroDeckBefore: "一架飞机晚到之后，延误会继续传递，还是被下一段航班吸收？我们用真实机尾号重建",
    heroDeckAfter: "条轮转关系，观察美国航空网络的压力与恢复。",
    explore: "探索航空网络",
    boundary: "查看研究边界",
    pulseAria: "2026 年 5 月每日起飞延误率",
    pulseKicker: "网络脉冲",
    pulseTitle: "每日起飞压力",
    peak: "峰值",
    month: "全月",
    delayedLegend: "延误 ≥ 15 分钟",
    peakDay: "单日峰值",
    reportedFlights: "611,735 条航班记录",
    nationalSummary: "全美航空网络摘要",
    metricDelay: "起飞延误 15 分钟及以上",
    metricPropagation: "上游延误继续传播",
    metricRecovery: "上游延误被后续航段吸收",
    metricTails: "观测到的独立飞机数量",
    airportSection: "01 / 机场压力榜",
    airportTitle: "哪些机场感受到了更大压力？",
    airportIntro: "只比较月出发量至少 1,000 班、有效轮转链至少 500 条的机场。压力指数由延误率、取消率和传播率的样本内百分位构成。",
    sortAria: "机场排序方式",
    rankBy: "排序依据",
    rankedAirports: "机场排名",
    rankAirport: "排名 / 机场",
    relativeSignal: "相对信号",
    delay: "起飞延误",
    propagation: "传播率",
    selectedAirport: "当前机场",
    flights: "航班量",
    avgDepartureDelay: "平均起飞延误",
    percentile90: "第 90 百分位延误",
    cancellation: "取消率",
    afterInboundDelay: "发生进港延误后",
    links: "条轮转链",
    splitAria: "延误传播率与恢复率",
    propagated: "继续传播",
    recovered: "被吸收",
    pressureNote: "压力指数只反映符合条件机场之间的相对位置，不是安全评级，也不代表因果关系。",
    carrierSection: "02 / 航司对比",
    carrierTitle: "规模不等于韧性。",
    carrierIntro: "每家航司面对不同的航线结构和运营约束。这里展示描述性差异，不把排名解释成运营能力的因果结论。",
    flightUnit: "班航班",
    carrierDelay: "延误",
    carrierPropagate: "传播",
    carrierRecover: "恢复",
    rotationSection: "03 / 飞机轮转故事",
    rotationTitle: "跟踪飞机，而不只是航班。",
    rotationIntro: "每个故事都来自同一机尾号的连续真实航段。状态用 15 分钟阈值描述传播或恢复，时间统一显示为 UTC。",
    storyAria: "选择一个飞机轮转故事",
    tail: "机尾号",
    date: "日期",
    chain: "轮转链",
    legs: "个航段",
    departure: "起飞",
    arrival: "到达",
    turn: "分钟周转",
    nextLeg: "下一航段",
    methodSection: "04 / 方法与边界",
    methodTitleFirst: "证据在前。",
    methodTitleSecond: "结论在后。",
    methodOneTitle: "统一到 UTC 时间线",
    methodOne: "所有本地 HHMM 时间先结合机场时区转成 UTC；1,167 条记录若按本地时钟排序会得到不同顺序。",
    methodTwoTitle: "确保物理连续性",
    methodTwo: "只连接机尾号相同、上一站终点等于下一站起点、且周转时间物理可行的航段。79 条负周转候选已排除。",
    methodThreeTitle: "不做因果断言",
    methodThree: "“传播”表示相邻两段都超过 15 分钟，并不单独证明前一段造成后一段；天气和机场拥堵将在后续版本控制。",
    integrity: "数据完整性",
    tailCoverage: "已执行航班的机尾号覆盖率",
    clockAgreement: "计划时刻一致率",
    airportContinuity: "机场衔接连续率",
    duplicateKeys: "候选主键重复数",
    footerTagline: "延误传播与航空网络韧性实验室。",
    sourceFirst: "数据来源：美国交通部交通统计局",
    sourceSecond: "承运人航班准点表现数据。",
    officialData: "查看官方数据",
    edition: "V0 / 描述性产品",
  },
  en: {
    skip: "Skip to analysis",
    home: "Airports Under Stress home",
    navLabel: "Primary navigation",
    airports: "Airports",
    carriers: "Carriers",
    rotations: "Rotations",
    method: "Method",
    period: "May 2026",
    eyebrow: "U.S. aviation network / retrospective",
    heroDeckBefore: "When an aircraft arrives late, does the delay keep moving or get absorbed by the next flight? We reconstructed",
    heroDeckAfter: "real aircraft rotations to examine pressure and recovery across the U.S. aviation network.",
    explore: "Explore the network",
    boundary: "Read the research boundary",
    pulseAria: "Daily departure delay rate in May 2026",
    pulseKicker: "Network pulse",
    pulseTitle: "Daily departure pressure",
    peak: "Peak",
    month: "Month",
    delayedLegend: "Delayed ≥ 15 min",
    peakDay: "Peak day",
    reportedFlights: "611,735 reported flights",
    nationalSummary: "National summary",
    metricDelay: "departures delayed 15+ min",
    metricPropagation: "upstream delays propagated",
    metricRecovery: "upstream delays absorbed",
    metricTails: "unique aircraft observed",
    airportSection: "01 / Airport pressure board",
    airportTitle: "Where the network felt tight.",
    airportIntro: "We compare airports with at least 1,000 monthly departures and 500 valid rotation links. The pressure score combines within-sample percentiles for delay, cancellation and propagation rates.",
    sortAria: "Sort airports",
    rankBy: "Rank by",
    rankedAirports: "Ranked airports",
    rankAirport: "Rank / airport",
    relativeSignal: "relative signal",
    delay: "delay",
    propagation: "propagation",
    selectedAirport: "Selected airport",
    flights: "Flights",
    avgDepartureDelay: "Avg. dep delay",
    percentile90: "90th percentile",
    cancellation: "Cancellation",
    afterInboundDelay: "After an inbound delay",
    links: "links",
    splitAria: "Propagation versus recovery rate",
    propagated: "propagated",
    recovered: "recovered",
    pressureNote: "Pressure score is relative within eligible airports; it is not a safety rating or causal claim.",
    carrierSection: "02 / Carrier comparison",
    carrierTitle: "Scale is not resilience.",
    carrierIntro: "Each carrier faces a different route structure and operating constraints. These are descriptive differences, not causal rankings of operating ability.",
    flightUnit: "flights",
    carrierDelay: "delay",
    carrierPropagate: "propagate",
    carrierRecover: "recover",
    rotationSection: "03 / Aircraft rotation stories",
    rotationTitle: "Follow the aircraft, not just the flight.",
    rotationIntro: "Each story follows consecutive real legs flown by one tail number. A 15-minute threshold describes propagation or recovery, and all times are UTC.",
    storyAria: "Choose aircraft rotation story",
    tail: "Tail",
    date: "Date",
    chain: "Chain",
    legs: "legs",
    departure: "DEP",
    arrival: "ARR",
    turn: "m turn",
    nextLeg: "next leg",
    methodSection: "04 / Method & boundary",
    methodTitleFirst: "Evidence first.",
    methodTitleSecond: "Claims second.",
    methodOneTitle: "One UTC timeline",
    methodOne: "All local HHMM times are converted to UTC using airport time zones; 1,167 records would sort differently on local clocks.",
    methodTwoTitle: "Physical continuity",
    methodTwo: "We only connect legs with the same tail, a matching arrival and next departure airport, and a physically feasible turn. 79 negative-turn candidates were excluded.",
    methodThreeTitle: "Not a causal claim",
    methodThree: "Propagation means two adjacent legs both exceed 15 minutes. It does not prove the earlier leg caused the later delay; weather and airport congestion are reserved for later versions.",
    integrity: "Data integrity",
    tailCoverage: "operated-flight tail coverage",
    clockAgreement: "scheduled-clock agreement",
    airportContinuity: "airport continuity",
    duplicateKeys: "candidate-key duplicates",
    footerTagline: "Delay propagation & network resilience lab.",
    sourceFirst: "Source: U.S. DOT Bureau of Transportation Statistics,",
    sourceSecond: "Reporting Carrier On-Time Performance.",
    officialData: "Official data",
    edition: "V0 / Descriptive product",
  },
} as const;

function percent(value: number, digits = 1) {
  return `${(value * 100).toFixed(digits)}%`;
}

function delayLabel(value: number | null, language: Language) {
  if (value === null) return "—";
  if (value === 0) return language === "zh" ? "准点" : "on time";
  return language === "zh"
    ? `${value > 0 ? "+" : ""}${Math.round(value)} 分钟`
    : `${value > 0 ? "+" : ""}${Math.round(value)}m`;
}

function barStyle(value: number, max: number): CSSProperties {
  return { "--value": `${Math.max(4, (value / max) * 100)}%` } as CSSProperties;
}

export default function Dashboard() {
  const [language, setLanguage] = useState<Language>("zh");
  const [airportSort, setAirportSort] = useState<AirportSortKey>("pressureScore");
  const [selectedAirportCode, setSelectedAirportCode] = useState(data.airports[0].code);
  const [activeStoryId, setActiveStoryId] = useState(data.stories[0].id);

  const sortedAirports = useMemo(
    () => [...data.airports].sort((a, b) => b[airportSort] - a[airportSort]).slice(0, 12),
    [airportSort],
  );
  const selectedAirport =
    data.airports.find((airport) => airport.code === selectedAirportCode) ?? sortedAirports[0];
  const activeStory =
    data.stories.find((story) => story.id === activeStoryId) ?? data.stories[0];
  const dailyMax = Math.max(...data.daily.map((point) => point.delayRate));
  const peakPoint = data.daily.find((point) => point.date === data.national.peakDay) ?? data.daily[0];
  const airlineDelayMax = Math.max(...data.airlines.map((airline) => airline.delayRate));
  const text = ui[language];
  const integer = (value: number) =>
    new Intl.NumberFormat(language === "zh" ? "zh-CN" : "en-US").format(value);
  const storyTitle = (story: Story) => {
    if (language === "en") return story.title;
    return {
      cascade: "延误沿轮转链持续传递",
      recovery: "计划缓冲切断了传播链",
      "tight-turn": "紧周转没有留下余量",
      mixed: "先传播，然后恢复",
    }[story.type] ?? story.title;
  };
  const storySummary = (story: Story) => {
    if (language === "en") return story.summary;
    if (story.type === "cascade") return `${story.propagated} 个后续航段的起飞延误超过了 15 分钟。`;
    if (story.type === "recovery") return `${story.recovered} 次晚到在下一次起飞前被吸收。`;
    if (story.type === "tight-turn") {
      const tightestTurn = Math.min(...story.legs.map((leg) => leg.turn ?? Infinity));
      return `这条轮转链最短的计划周转时间只有 ${tightestTurn} 分钟。`;
    }
    return "同一架飞机的轮转说明，网络压力并不是单向级联：延误可以传播，也可能在后续航段恢复。";
  };

  useEffect(() => {
    document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
  }, [language]);

  return (
    <main id="top">
      <a className="skip-link" href="#pressure-board">
        {text.skip}
      </a>

      <header className="site-header">
        <a className="wordmark" href="#top" aria-label={text.home}>
          <span className="wordmark-signal" aria-hidden="true" />
          <span>AUS / LAB</span>
        </a>
        <nav aria-label={text.navLabel}>
          <a href="#pressure-board">{text.airports}</a>
          <a href="#carriers">{text.carriers}</a>
          <a href="#rotations">{text.rotations}</a>
          <a href="#method">{text.method}</a>
        </nav>
        <div className="header-tools">
          <div className="language-toggle" role="group" aria-label="Language / 语言">
            <button
              type="button"
              className={language === "zh" ? "active" : ""}
              aria-pressed={language === "zh"}
              onClick={() => setLanguage("zh")}
            >
              中文
            </button>
            <button
              type="button"
              className={language === "en" ? "active" : ""}
              aria-pressed={language === "en"}
              onClick={() => setLanguage("en")}
            >
              EN
            </button>
          </div>
          <div className="edition-badge">
            <span>V0</span>
            <span>{text.period}</span>
          </div>
        </div>
      </header>

      <section className="hero section-shell" aria-labelledby="hero-title">
        <div className="hero-copy">
          <div className="eyebrow">
            <span className="live-dot" />
            {text.eyebrow}
          </div>
          <h1 id="hero-title">
            <span>Airports</span>
            <span className="outlined">Under Stress</span>
          </h1>
          <p className="hero-deck">
            {text.heroDeckBefore} <strong>549,388</strong> {text.heroDeckAfter}
          </p>
          <div className="hero-actions">
            <a className="primary-action" href="#pressure-board">
              {text.explore} <span aria-hidden="true">↘</span>
            </a>
            <a className="text-action" href="#method">
              {text.boundary}
            </a>
          </div>
        </div>

        <div className="pulse-panel" aria-label={text.pulseAria}>
          <div className="panel-topline">
            <div>
              <span className="panel-kicker">{text.pulseKicker}</span>
              <h2>{text.pulseTitle}</h2>
            </div>
            <div className="peak-readout">
              <span>{text.peak} / {language === "zh" ? `5 月 ${peakPoint.day} 日` : `May ${peakPoint.day}`}</span>
              <strong>{percent(peakPoint.delayRate)}</strong>
            </div>
          </div>
          <div className="pulse-chart">
            <div className="pulse-baseline" aria-hidden="true">
              <span>{text.month} {percent(data.national.delayRate)}</span>
            </div>
            {data.daily.map((point) => (
              <div
                className={`pulse-column ${point.date === data.national.peakDay ? "is-peak" : ""}`}
                key={point.date}
                title={language === "zh"
                  ? `5 月 ${point.day} 日：${percent(point.delayRate)} 航班延误`
                  : `May ${point.day}: ${percent(point.delayRate)} delayed`}
              >
                <div
                  className="pulse-fill"
                  style={{ height: `${Math.max(8, (point.delayRate / dailyMax) * 100)}%` }}
                />
                <span>{point.day % 5 === 0 || point.day === 1 ? point.day : ""}</span>
              </div>
            ))}
          </div>
          <div className="pulse-legend">
            <span>
              <i className="legend-mark legend-delay" /> {text.delayedLegend}
            </span>
            <span>
              <i className="legend-mark legend-peak" /> {text.peakDay}
            </span>
            <span>{text.reportedFlights}</span>
          </div>
        </div>
      </section>

      <section className="metric-ribbon section-shell" aria-label={text.nationalSummary}>
        <article>
          <span className="metric-index">01</span>
          <strong>{percent(data.national.delayRate)}</strong>
          <p>{text.metricDelay}</p>
        </article>
        <article>
          <span className="metric-index">02</span>
          <strong>{percent(data.national.propagationRate)}</strong>
          <p>{text.metricPropagation}</p>
        </article>
        <article>
          <span className="metric-index">03</span>
          <strong>{percent(data.national.recoveryRate)}</strong>
          <p>{text.metricRecovery}</p>
        </article>
        <article>
          <span className="metric-index">04</span>
          <strong>{integer(data.meta.tails)}</strong>
          <p>{text.metricTails}</p>
        </article>
      </section>

      <section className="analysis-section section-shell" id="pressure-board">
        <div className="section-heading">
          <div>
            <span className="section-number">{text.airportSection}</span>
            <h2>{text.airportTitle}</h2>
          </div>
          <p>{text.airportIntro}</p>
        </div>

        <div className="sort-rail" aria-label={text.sortAria}>
          <span>{text.rankBy}</span>
          <div>
            {sortOptions.map((option) => (
              <button
                type="button"
                key={option.key}
                className={airportSort === option.key ? "active" : ""}
                aria-pressed={airportSort === option.key}
                onClick={() => setAirportSort(option.key)}
              >
                {option[language]}
              </button>
            ))}
          </div>
        </div>

        <div className="airport-layout">
          <div className="airport-table" role="list" aria-label={text.rankedAirports}>
            <div className="airport-table-head" aria-hidden="true">
              <span>{text.rankAirport}</span>
              <span>{text.relativeSignal}</span>
              <span>{text.delay}</span>
              <span>{text.propagation}</span>
            </div>
            {sortedAirports.map((airport, index) => {
              const sortValue =
                airportSort === "flights"
                  ? airport.flights
                  : airportSort === "pressureScore"
                    ? airport.pressureScore
                    : airport[airportSort];
              const maxValue =
                airportSort === "flights"
                  ? sortedAirports[0].flights
                  : airportSort === "pressureScore"
                    ? 100
                    : Math.max(...sortedAirports.map((row) => row[airportSort]));
              return (
                <button
                  type="button"
                  role="listitem"
                  className={`airport-row ${selectedAirport.code === airport.code ? "selected" : ""}`}
                  key={airport.code}
                  onClick={() => setSelectedAirportCode(airport.code)}
                  aria-label={language === "zh"
                    ? `${airport.code}，${airport.city}：${percent(airport.delayRate)} 航班延误`
                    : `${airport.code}, ${airport.city}: ${percent(airport.delayRate)} delayed`}
                >
                  <span className="airport-identity">
                    <i>{String(index + 1).padStart(2, "0")}</i>
                    <strong>{airport.code}</strong>
                    <small>{airport.city}</small>
                  </span>
                  <span className="signal-track" style={barStyle(Number(sortValue), Number(maxValue))}>
                    <i />
                  </span>
                  <span className="row-value">{percent(airport.delayRate)}</span>
                  <span className="row-value">{percent(airport.propagationRate)}</span>
                </button>
              );
            })}
          </div>

          <aside className="airport-focus" aria-live="polite">
            <div className="focus-header">
              <div>
                <span>{text.selectedAirport}</span>
                <h3>{selectedAirport.code}</h3>
              </div>
              <strong>{selectedAirport.pressureScore.toFixed(1)}</strong>
            </div>
            <p className="airport-name">{selectedAirport.name}</p>
            <p className="airport-location">
              {selectedAirport.city}, {selectedAirport.region}
            </p>
            <div className="focus-grid">
              <div>
                <span>{text.flights}</span>
                <strong>{integer(selectedAirport.flights)}</strong>
              </div>
              <div>
                <span>{text.avgDepartureDelay}</span>
                <strong>{selectedAirport.avgDelay.toFixed(1)}{language === "zh" ? " 分钟" : "m"}</strong>
              </div>
              <div>
                <span>{text.percentile90}</span>
                <strong>{selectedAirport.p90Delay.toFixed(0)}{language === "zh" ? " 分钟" : "m"}</strong>
              </div>
              <div>
                <span>{text.cancellation}</span>
                <strong>{percent(selectedAirport.cancelRate)}</strong>
              </div>
            </div>
            <div className="absorption-block">
              <div className="absorption-label">
                <span>{text.afterInboundDelay}</span>
                <span>{integer(selectedAirport.chainLinks)} {text.links}</span>
              </div>
              <div className="split-meter" aria-label={text.splitAria}>
                <span style={{ width: percent(selectedAirport.propagationRate, 2) }} />
                <i style={{ width: percent(selectedAirport.recoveryRate, 2) }} />
              </div>
              <div className="split-values">
                <span>
                  <strong>{percent(selectedAirport.propagationRate)}</strong> {text.propagated}
                </span>
                <span>
                  <strong>{percent(selectedAirport.recoveryRate)}</strong> {text.recovered}
                </span>
              </div>
            </div>
            <p className="focus-note">{text.pressureNote}</p>
          </aside>
        </div>
      </section>

      <section className="analysis-section carrier-section section-shell" id="carriers">
        <div className="section-heading compact-heading">
          <div>
            <span className="section-number">{text.carrierSection}</span>
            <h2>{text.carrierTitle}</h2>
          </div>
          <p>{text.carrierIntro}</p>
        </div>
        <div className="carrier-grid">
          {data.airlines.map((airline, index) => (
            <article className="carrier-card" key={airline.code}>
              <div className="carrier-topline">
                <span>{String(index + 1).padStart(2, "0")}</span>
                <span>{integer(airline.flights)} {text.flightUnit}</span>
              </div>
              <div className="carrier-name">
                <strong>{airline.code}</strong>
                <h3>{airline.name}</h3>
              </div>
              <div className="carrier-bar">
                <span style={{ width: percent(airline.delayRate / airlineDelayMax, 2) }} />
              </div>
              <div className="carrier-stats">
                <span>
                  <strong>{percent(airline.delayRate)}</strong>
                  {text.carrierDelay}
                </span>
                <span>
                  <strong>{percent(airline.propagationRate)}</strong>
                  {text.carrierPropagate}
                </span>
                <span>
                  <strong>{percent(airline.recoveryRate)}</strong>
                  {text.carrierRecover}
                </span>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="analysis-section rotation-section section-shell" id="rotations">
        <div className="section-heading rotation-heading">
          <div>
            <span className="section-number">{text.rotationSection}</span>
            <h2>{text.rotationTitle}</h2>
          </div>
          <p>{text.rotationIntro}</p>
        </div>

        <div className="story-switcher" aria-label={text.storyAria}>
          {data.stories.map((story, index) => (
            <button
              type="button"
              key={story.id}
              className={story.id === activeStory.id ? "active" : ""}
              aria-pressed={story.id === activeStory.id}
              onClick={() => setActiveStoryId(story.id)}
            >
              <span>{String(index + 1).padStart(2, "0")}</span>
              <strong>{storyLabels[language][story.type]}</strong>
              <small>{story.tail}</small>
            </button>
          ))}
        </div>

        <div className="story-stage" aria-live="polite">
          <div className="story-intro">
            <span className={`story-type type-${activeStory.type}`}>
              {storyLabels[language][activeStory.type]}
            </span>
            <h3>{storyTitle(activeStory)}</h3>
            <p>{storySummary(activeStory)}</p>
            <dl>
              <div>
                <dt>{text.tail}</dt>
                <dd>{activeStory.tail}</dd>
              </div>
              <div>
                <dt>{text.date}</dt>
                <dd>{activeStory.date}</dd>
              </div>
              <div>
                <dt>{text.chain}</dt>
                <dd>{activeStory.legs.length} {text.legs}</dd>
              </div>
            </dl>
          </div>

          <div className="rotation-track">
            {activeStory.legs.map((leg, index) => (
              <article className={`rotation-leg status-${leg.status}`} key={`${leg.flight}-${index}`}>
                <div className="leg-sequence">
                  <span>{String(index + 1).padStart(2, "0")}</span>
                  <i />
                </div>
                <div className="leg-card">
                  <div className="leg-topline">
                    <span>{leg.flight}</span>
                    <span>{leg.scheduled}</span>
                  </div>
                  <div className="leg-route">
                    <strong>{leg.origin}</strong>
                    <span aria-hidden="true">→</span>
                    <strong>{leg.dest}</strong>
                  </div>
                  <div className="leg-delays">
                    <span>
                      {text.departure} <strong>{delayLabel(leg.depDelay, language)}</strong>
                    </span>
                    <span>
                      {text.arrival} <strong>{delayLabel(leg.arrDelay, language)}</strong>
                    </span>
                  </div>
                  <span className="leg-status">{statusLabels[language][leg.status]}</span>
                </div>
                {index < activeStory.legs.length - 1 && (
                  <div className="turn-label">
                    {activeStory.legs[index + 1].turn
                      ? `${activeStory.legs[index + 1].turn}${text.turn}`
                      : text.nextLeg}
                  </div>
                )}
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="method-section section-shell" id="method">
        <div className="method-title">
          <span className="section-number">{text.methodSection}</span>
          <h2>{text.methodTitleFirst}<br />{text.methodTitleSecond}</h2>
        </div>
        <div className="method-grid">
          <article>
            <span>01</span>
            <h3>{text.methodOneTitle}</h3>
            <p>{text.methodOne}</p>
          </article>
          <article>
            <span>02</span>
            <h3>{text.methodTwoTitle}</h3>
            <p>{text.methodTwo}</p>
          </article>
          <article>
            <span>03</span>
            <h3>{text.methodThreeTitle}</h3>
            <p>{text.methodThree}</p>
          </article>
        </div>
        <div className="integrity-strip">
          <span>{text.integrity}</span>
          <div>
            <strong>100.0000%</strong>
            <small>{text.tailCoverage}</small>
          </div>
          <div>
            <strong>99.9982%</strong>
            <small>{text.clockAgreement}</small>
          </div>
          <div>
            <strong>98.78%</strong>
            <small>{text.airportContinuity}</small>
          </div>
          <div>
            <strong>0</strong>
            <small>{text.duplicateKeys}</small>
          </div>
        </div>
      </section>

      <footer className="site-footer section-shell">
        <div>
          <span className="wordmark-signal" aria-hidden="true" />
          <strong>Airports Under Stress</strong>
          <p>{text.footerTagline}</p>
        </div>
        <div className="footer-meta">
          <p>
            {text.sourceFirst}<br />{text.sourceSecond}
          </p>
          <a
            href="https://www.transtats.bts.gov/TableInfo.asp?QO_fu146_anzr=b0-gvzr&gnoyr_VQ=FGJ"
            target="_blank"
            rel="noreferrer"
          >
            {text.officialData} ↗
          </a>
        </div>
        <div className="footer-edition">
          <span>{text.edition}</span>
          <span>2026</span>
        </div>
      </footer>
    </main>
  );
}
