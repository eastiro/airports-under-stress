"use client";

import { useEffect, useMemo, useState, Fragment, type CSSProperties } from "react";
import rawData from "./v0-data.json";
import v1aData from "./v1-a-data.json";
import v1bData from "./v1-b-data.json";
import v2aData from "./v2-a-data.json";
import v2bData from "./v2-b-data.json";
import v3aData from "./v3-a-data.json";
import NetworkHero from "./NetworkHero";
import MechanismSection, { type V1AData as MechanismData, type V2BData } from "./MechanismSection";
import EpisodeExplorer, { type V1BData } from "./EpisodeExplorer";
import CongestionSection, { type V3AData } from "./CongestionSection";
import { AIRPORT_ZH, AIRLINE_ZH } from "./airport-names-zh";

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
  rankPressure: number;
  rankDelay: number;
  rankCancel: number;
  rankPropagation: number;
  rankFlights: number;
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
  status: "late" | "on-time";
  depDelay: number;
  arrDelay: number;
  scheduledDepUTC: string;
  actualDepUTC: string;
  scheduledArrUTC: string;
  actualArrUTC: string;
};

type StoryConnector = {
  hub: string;
  planGap: number;
  actualTurn: number;
  prevArrDelay: number;
  nextDepDelay: number;
  delayDelta: number;
  relation: "propagated" | "caught_up" | "recovered_full" | "delayed" | "on-time";
};

type Story = {
  id: string;
  type: string;
  title: string;
  titleZh: string;
  summary: string;
  summaryZh: string;
  tail: string;
  date: string;
  edges: number;
  legCount: number;
  propagated: number;
  recovered: number;
  maxDelay: number;
  legs: StoryLeg[];
  connectors: StoryConnector[];
};

type SiteData = {
  meta: {
    period: string;
    records: number;
    rawAirports: number;
    eligibleAirports: number;
    mapAirports: number;
    rankedAirportsShown: number;
    rawAirlines: number;
    comparableAirlines: number;
    tails: number;
    chainLinks: number;
    source: string;
    coverage: string;
    airlineThreshold: string;
  };
  national: {
    delayRate: number;
    cancelRate: number;
    propagationRate: number;
    recoveryRate: number;
    peakDay: string;
  };
  daily: DailyPoint[];
  mapAirportCodes: string[];
  network: {
    routes: { origin: string; dest: string; flights: number; delayRate: number }[];
  };
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
export const AIRPORT_CITY_EN: Record<string, string> = Object.fromEntries(
  data.airports.map((airport) => [airport.code, airport.city]),
);

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

const statusLabels: Record<Language, Record<string, string>> = {
  zh: {
    late: "晚点",
    "on-time": "准点",
  },
  en: {
    late: "late",
    "on-time": "on time",
  },
};

const relationLabels: Record<Language, Record<string, string>> = {
  zh: {
    propagated: "延误延续",
    caught_up: "略有追回",
    recovered_full: "恢复准点",
    delayed: "延误加重",
    "on-time": "全程准点",
  },
  en: {
    propagated: "continued",
    caught_up: "eased",
    recovered_full: "recovered",
    delayed: "worsened",
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
    metricDelay: "起飞晚点 15 分钟以上",
    metricPropagation: "晚点继续传到下一班",
    metricRecovery: "晚点被下一班追回",
    metricTails: "研究覆盖",
    metricTailsSub: "架有机尾号的飞机",
    airportSection: "01 / 机场压力榜",
    airportTitle: "哪些机场感受到了更大压力？",
    airportIntro: "这张榜单比较哪些机场在这批数据里同时出现更多晚点、取消，以及晚点继续往下传。分数越高，表示相对压力越集中——只比机场之间的相对位置，不是安全评分。榜单展示前 12 名，下方可选择全部 97 个合格机场中的任意一个。",
    airportDetailsSummary: "查看研究细节",
    airportScopeDetails: "97 个机场纳入比较：月出发量至少 1,000 班、有效轮转链至少 500 条。压力指数由延误率、取消率和传播率的样本内百分位合成（满分 100）。榜单按单个机场计算，不合并纽约、芝加哥、休斯顿等都会区的多个机场。",
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
    carrierIntro: "比较大型报告航司在这批数据里的不同表现——只描述差异，不评哪家运营能力更高。",
    carrierDetailsSummary: "查看研究细节",
    carrierScopeDetails: "共 12 家航司纳入比较，均为月计划航班至少 10,000 班的报告航司。这些差异是描述性的，不把排名解释成运营能力的因果结论。",
    flightUnit: "班航班",
    carrierDelay: "起飞晚点",
    carrierPropagate: "晚点继续",
    carrierRecover: "晚点追回",
    rotationSection: "03 / 飞机轮转故事",
    rotationTitle: "跟踪飞机，而不只是航班。",
    rotationIntro: "每个故事都来自同一架飞机的连续真实航段，看晚点如何一段段传下去、又在哪里被追回。",
    rotationDetailsSummary: "查看研究细节",
    rotationScopeDetails: "这些衔接用 15 分钟统一门槛区分传播或恢复，时间统一按 UTC 显示；只描述相邻两段都晚点的连续性，不构成因果。",
    storyAria: "选择一个飞机轮转故事",
    tail: "机尾号",
    date: "日期",
    chain: "轮转链",
    legs: "个航段",
    departure: "起飞",
    arrival: "到达",
    turn: "分钟周转",
    nextLeg: "下一航段",
    planned: "计划",
    depDelay: "起飞延误",
    arrDelay: "到达延误",
    planTurn: "计划过站",
    actualTurn: "实际过站",
    improve: "追回",
    worsen: "加重",
    maxDelay: "最大延误",
    guideTitle: "怎么读这张图",
    guideActual: "实心 = 实际起飞 / 到达时刻",
    guidePlanned: "浅色 = 计划时刻",
    guideTurn: "过站时间 = 飞机实际停场分钟（不是计划）",
    guideThreshold: "15 分钟是描述传播 / 恢复的统一门槛",
    guideCausal: "衔接关系只描述相邻两段都晚点的连续性，不构成因果",
    methodSection: "08 / 方法与边界",
    methodTitleFirst: "证据在前。",
    methodTitleSecond: "结论在后。",
    methodOneTitle: "统一到 UTC 时间线",
    methodOne: "所有本地 HHMM 时间先结合机场时区转成 UTC；1,167 条记录若按本地时钟排序会得到不同顺序。",
    methodTwoTitle: "确保物理连续性",
    methodTwo: "只连接机尾号相同、上一站终点等于下一站起点、且周转时间物理可行的航段。79 条负周转候选已排除。",
    methodThreeTitle: "不做因果断言",
    methodThree: "“传播”表示相邻两段都超过 15 分钟，并不单独证明前一段造成后一段。后续章节已分别做了天气与计划拥挤的描述性比较，但那仍然不是因果控制或因果证明。",
    integrity: "数据完整性",
    integrityNote: "这些完整性数字说明数据处理可靠，不代表研究结论就是因果。",
    tailCoverage: "已执行航班的机尾号覆盖率",
    clockAgreement: "计划时刻一致率",
    airportContinuity: "机场衔接连续率",
    duplicateKeys: "候选主键重复数",
    footerTagline: "延误传播与航空网络韧性实验室。",
    sourceFirst: "数据来源：美国交通部交通统计局",
    sourceSecond: "承运人航班准点表现数据。",
    officialData: "查看官方数据",
    edition: "V3 / 描述性研究产品",
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
    metricPropagation: "delay kept moving to the next flight",
    metricRecovery: "delay recovered by the next flight",
    metricTails: "Research coverage",
    metricTailsSub: "aircraft with tail numbers",
    airportSection: "01 / Airport pressure board",
    airportTitle: "Where the network felt tight.",
    airportIntro: "This board compares which airports in this dataset show more delay, cancellation, and delay moving onward at the same time. A higher score means more concentrated relative pressure — it ranks airports only against each other, not a safety rating. It shows the top 12, and you can pick any of the 97 eligible airports below.",
    airportDetailsSummary: "View research details",
    airportScopeDetails: "97 airports are compared: at least 1,000 monthly departures and 500 valid rotation links each. The pressure score combines within-sample percentiles for delay, cancellation and propagation rates (out of 100). Airports are ranked individually; metro-area airports (NYC, Chicago, Houston, etc.) are not merged.",
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
    carrierIntro: "We compare how large reporting carriers performed differently in this dataset — descriptive only, not a ranking of operating ability.",
    carrierDetailsSummary: "View research details",
    carrierScopeDetails: "12 carriers are compared, each with at least 10,000 scheduled monthly flights. These are descriptive differences, not causal rankings of operating ability.",
    flightUnit: "flights",
    carrierDelay: "departure delay",
    carrierPropagate: "delay continued",
    carrierRecover: "delay recovered",
    rotationSection: "03 / Aircraft rotation stories",
    rotationTitle: "Follow the aircraft, not just the flight.",
    rotationIntro: "Each story follows consecutive real legs flown by one aircraft, showing how delay travels leg to leg and where it gets recovered.",
    rotationDetailsSummary: "View research details",
    rotationScopeDetails: "Propagation and recovery are separated by a shared 15-minute threshold, and all times are UTC. The links only describe two adjacent late legs; they are not causal.",
    storyAria: "Choose aircraft rotation story",
    tail: "Tail",
    date: "Date",
    chain: "Chain",
    legs: "legs",
    departure: "DEP",
    arrival: "ARR",
    turn: "m turn",
    nextLeg: "next leg",
    planned: "sched",
    depDelay: "dep delay",
    arrDelay: "arr delay",
    planTurn: "plan turn",
    actualTurn: "actual turn",
    improve: "recovered",
    worsen: "worse",
    maxDelay: "max delay",
    guideTitle: "How to read this",
    guideActual: "solid = actual departure / arrival",
    guidePlanned: "muted = scheduled time",
    guideTurn: "turn time = actual minutes on the ground, not the plan",
    guideThreshold: "15 min is the shared threshold for propagation / recovery",
    guideCausal: "link labels describe continuity of two late legs, not causation",
    methodSection: "08 / Method & boundary",
    methodTitleFirst: "Evidence first.",
    methodTitleSecond: "Claims second.",
    methodOneTitle: "One UTC timeline",
    methodOne: "All local HHMM times are converted to UTC using airport time zones; 1,167 records would sort differently on local clocks.",
    methodTwoTitle: "Physical continuity",
    methodTwo: "We only connect legs with the same tail, a matching arrival and next departure airport, and a physically feasible turn. 79 negative-turn candidates were excluded.",
    methodThreeTitle: "Not a causal claim",
    methodThree: "Propagation means two adjacent legs both exceed 15 minutes. It does not prove the earlier leg caused the later delay. Later chapters do compare weather and scheduled congestion descriptively, but that is still not causal control or proof.",
    integrity: "Data integrity",
    integrityNote: "These integrity numbers show the data was processed reliably; they do not mean the conclusions are causal.",
    tailCoverage: "operated-flight tail coverage",
    clockAgreement: "scheduled-clock agreement",
    airportContinuity: "airport continuity",
    duplicateKeys: "candidate-key duplicates",
    footerTagline: "Delay propagation & network resilience lab.",
    sourceFirst: "Source: U.S. DOT Bureau of Transportation Statistics,",
    sourceSecond: "Reporting Carrier On-Time Performance.",
    officialData: "Official data",
    edition: "V3 / Descriptive research product",
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

function formatSortValue(key: AirportSortKey, value: number, language: Language) {
  if (key === "flights") return new Intl.NumberFormat(language === "zh" ? "zh-CN" : "en-US").format(value) + (language === "zh" ? " 班" : "");
  if (key === "pressureScore") return `${value.toFixed(1)} / 100`;
  return percent(value);
}
function rankKey(sort: AirportSortKey): keyof Airport {
  const map: Record<AirportSortKey, keyof Airport> = {
    pressureScore: "rankPressure",
    delayRate: "rankDelay",
    cancelRate: "rankCancel",
    propagationRate: "rankPropagation",
    flights: "rankFlights",
  };
  return map[sort];
}
function sortLabel(key: AirportSortKey, language: Language) {
  return sortOptions.find((o) => o.key === key)?.[language] ?? key;
}
export default function Dashboard() {
  const [language, setLanguage] = useState<Language>("zh");
  const [airportSort, setAirportSort] = useState<AirportSortKey>("pressureScore");
  const [selectedAirportCode, setSelectedAirportCode] = useState(data.airports[0].code);
  const [activeStoryId, setActiveStoryId] = useState(data.stories[0].id);
  // Shared pointer target between the map and the pressure board.
  const [linkedAirport, setLinkedAirport] = useState<string | null>(null);

  const sortedAirports = useMemo(
    () => [...data.airports].sort((a, b) => b[airportSort] - a[airportSort]).slice(0, 12),
    [airportSort],
  );
  const cityOf = (code: string) => language === "zh" ? (AIRPORT_ZH[code]?.city ?? AIRPORT_CITY_EN[code] ?? code) : (AIRPORT_CITY_EN[code] ?? code);
  const selectedAirport =
    data.airports.find((airport) => airport.code === selectedAirportCode) ?? sortedAirports[0];
  const activeStory =
    data.stories.find((story) => story.id === activeStoryId) ?? data.stories[0];
  const text = ui[language];
  const integer = (value: number) =>
    new Intl.NumberFormat(language === "zh" ? "zh-CN" : "en-US").format(value);
  const storyTitle = (story: Story) => (language === "zh" ? story.titleZh : story.title);
  const storySummary = (story: Story) => (language === "zh" ? story.summaryZh : story.summary);

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
          <a href="#mechanism">{language === "zh" ? "传播机制" : "Mechanism"}</a>
          <a href="#congestion">{language === "zh" ? "计划拥挤" : "Congestion"}</a>
          <a href="#episodes">{language === "zh" ? "连续延误案例" : "Episodes"}</a>
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
            <span>V3</span>
            <span>{text.period}</span>
          </div>
        </div>
      </header>

      <NetworkHero
        language={language}
        data={data}
        linkedAirport={linkedAirport}
        onLinkAirport={setLinkedAirport}
      />

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
        <article className="is-secondary">
          <span className="metric-index">04</span>
          <strong>{integer(data.meta.tails)}</strong>
          <p>{text.metricTails}</p>
          <small>{text.metricTailsSub}</small>
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

        <div className="airport-selector-rail">
          <label className="airport-selector">
            <span>{language === "zh" ? "查看其他机场" : "Find another airport"}</span>
            <select
              value={selectedAirportCode}
              onChange={(e) => setSelectedAirportCode(e.target.value)}
              aria-label={language === "zh" ? "选择 97 个合格机场中的任意一个" : "Select any of the 97 eligible airports"}
            >
              {[...data.airports]
                .sort((a, b) => a[airportSort] < b[airportSort] ? 1 : -1)
                .map((airport) => (
                  <option key={airport.code} value={airport.code}>
                    {airport.code} · {cityOf(airport.code)} — {formatSortValue(airportSort, airport[airportSort] as number, language)}
                  </option>
                ))}
            </select>
          </label>
        </div>

        <div className="airport-layout">
          <div className="airport-table" role="list" aria-label={text.rankedAirports}>
            <div className="airport-table-head" aria-hidden="true">
              <span>{text.rankAirport}</span>
              <span>{text.relativeSignal}</span>
              <span>{sortOptions.find((o) => o.key === airportSort)?.[language] ?? ""}</span>
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
                  className={`airport-row ${selectedAirport.code === airport.code ? "selected" : ""}${linkedAirport === airport.code ? " is-linked" : ""}`}
                  key={airport.code}
                  onClick={() => setSelectedAirportCode(airport.code)}
                  onMouseEnter={() => setLinkedAirport(airport.code)}
                  onMouseLeave={() => setLinkedAirport((prev) => (prev === airport.code ? null : prev))}
                  onFocus={() => setLinkedAirport(airport.code)}
                  onBlur={() => setLinkedAirport((prev) => (prev === airport.code ? null : prev))}
                  aria-label={language === "zh"
                    ? `${airport.code}，${airport.city}：${formatSortValue(airportSort, sortValue as number, language)}`
                    : `${airport.code}, ${airport.city}: ${formatSortValue(airportSort, sortValue as number, language)}`}
                >
                  <span className="airport-identity">
                    <i>{String(index + 1).padStart(2, "0")}</i>
                    <strong>{airport.code}</strong>
                    <small>{language === "zh" ? (AIRPORT_ZH[airport.code]?.city ?? airport.city) : airport.city}</small>
                  </span>
                  <span className="signal-track" style={barStyle(Number(sortValue), Number(maxValue))}>
                    <i />
                  </span>
                    <span className="row-value">{formatSortValue(airportSort, sortValue as number, language)}</span>
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
              <div className="focus-score">
                <strong>{formatSortValue(airportSort, selectedAirport[airportSort] as number, language)}</strong>
                <small>
                  {language === "zh"
                    ? `按${sortLabel(airportSort, "zh")}排序，第 ${selectedAirport[rankKey(airportSort)]} 名 / 97`
                    : `#${selectedAirport[rankKey(airportSort)]} of 97 (by ${sortLabel(airportSort, "en")})`}
                </small>
              </div>
            </div>
            <p className="airport-name">
              {language === "zh" ? (AIRPORT_ZH[selectedAirport.code]?.name ?? selectedAirport.name) : selectedAirport.name}
              {language === "zh" && <small>{selectedAirport.name}</small>}
            </p>
            <p className="airport-location">
              {language === "zh"
                ? (AIRPORT_ZH[selectedAirport.code]?.city ?? selectedAirport.city)
                : selectedAirport.city}
              {language === "zh"
                ? `，${AIRPORT_ZH[selectedAirport.code]?.region ?? selectedAirport.region}`
                : `, ${selectedAirport.region}`}
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
          </aside>
        </div>

        <details className="clarity-details airport-details">
          <summary>{text.airportDetailsSummary}</summary>
          <div className="clarity-details-inner">
            <p>{text.airportScopeDetails}</p>
            <p>{text.pressureNote}</p>
          </div>
        </details>
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
                <h3>{language === "zh" ? (AIRLINE_ZH[airline.code] ?? airline.name) : airline.name}</h3>
                {language === "zh" && <small>{airline.name} · {airline.code}</small>}
              </div>
              <div className="carrier-stats">
                <span className="carrier-stat" data-tone="delay">
                  <em>{text.carrierDelay}</em>
                  <strong>{percent(airline.delayRate)}</strong>
                  <span className="carrier-meter">
                    <i style={{ width: percent(airline.delayRate, 1) }} />
                  </span>
                </span>
                <span className="carrier-stat" data-tone="propagate">
                  <em>{text.carrierPropagate}</em>
                  <strong>{percent(airline.propagationRate)}</strong>
                  <span className="carrier-meter">
                    <i style={{ width: percent(airline.propagationRate, 1) }} />
                  </span>
                </span>
                <span className="carrier-stat" data-tone="recover">
                  <em>{text.carrierRecover}</em>
                  <strong>{percent(airline.recoveryRate)}</strong>
                  <span className="carrier-meter">
                    <i style={{ width: percent(airline.recoveryRate, 1) }} />
                  </span>
                </span>
              </div>
            </article>
          ))}
        </div>

        <details className="clarity-details carrier-details">
          <summary>{text.carrierDetailsSummary}</summary>
          <div className="clarity-details-inner">
            <p>{text.carrierScopeDetails}</p>
          </div>
        </details>
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
              <div>
                <dt>{text.maxDelay}</dt>
                <dd>{delayLabel(activeStory.maxDelay, language)}</dd>
              </div>
            </dl>
          </div>

          <div className="rotation-panel">
            <div className="rotation-track">
              {activeStory.legs.map((leg, index) => (
                <Fragment key={`${leg.flight}-${index}`}>
                  <article className={`rotation-leg status-${leg.status}`}>
                    <div className="leg-sequence">
                      <span>{String(index + 1).padStart(2, "0")}</span>
                      <i />
                    </div>
                    <div className="leg-card">
                      <div className="leg-topline">
                        <span>{leg.flight}</span>
                        <span className="leg-status">{statusLabels[language][leg.status]}</span>
                      </div>
                      <div className="leg-route" aria-label={`${leg.origin} ${cityOf(leg.origin)} → ${leg.dest} ${cityOf(leg.dest)}`}>
                        <strong>{leg.origin}<small>{cityOf(leg.origin)}</small></strong>
                        <span aria-hidden="true">→</span>
                        <strong>{leg.dest}<small>{cityOf(leg.dest)}</small></strong>
                      </div>
                      <div className="leg-times">
                        <div className="leg-time">
                          <span className="leg-time-label">{text.departure}</span>
                          <b>{leg.actualDepUTC}</b>
                          <small>{text.planned} {leg.scheduledDepUTC}</small>
                        </div>
                        <div className="leg-time">
                          <span className="leg-time-label">{text.arrival}</span>
                          <b>{leg.actualArrUTC}</b>
                          <small>{text.planned} {leg.scheduledArrUTC}</small>
                        </div>
                      </div>
                      <div className="leg-delays">
                        <span>
                          {text.depDelay} <strong className={leg.depDelay >= 15 ? "is-bad" : "is-ok"}>{delayLabel(leg.depDelay, language)}</strong>
                        </span>
                        <span>
                          {text.arrDelay} <strong className={leg.arrDelay >= 15 ? "is-bad" : "is-ok"}>{delayLabel(leg.arrDelay, language)}</strong>
                        </span>
                      </div>
                    </div>
                  </article>

                  {index < activeStory.connectors.length && (
                    <article
                      className={`rotation-connector rel-${activeStory.connectors[index].relation}`}
                      aria-label={`${activeStory.connectors[index].hub} ${cityOf(activeStory.connectors[index].hub)} · ${relationLabels[language][activeStory.connectors[index].relation]}`}
                    >
                      <span className="connector-hub">{activeStory.connectors[index].hub}<small>{cityOf(activeStory.connectors[index].hub)}</small></span>
                      <span className="connector-relation">{relationLabels[language][activeStory.connectors[index].relation]}</span>
                      <span className="connector-turn">{text.planTurn} <b>{Math.round(activeStory.connectors[index].planGap)}′</b></span>
                      <span className="connector-turn">{text.actualTurn} <b>{Math.round(activeStory.connectors[index].actualTurn)}′</b></span>
                      <span className={`connector-delta ${activeStory.connectors[index].delayDelta <= 0 ? "is-good" : "is-bad"}`}>
                        {activeStory.connectors[index].delayDelta <= 0 ? text.improve : text.worsen} {Math.abs(Math.round(activeStory.connectors[index].delayDelta))}′
                      </span>
                    </article>
                  )}
                </Fragment>
              ))}
            </div>

            <div className="rotation-guide" aria-label={text.guideTitle}>
              <strong>{text.guideTitle}</strong>
              <ul>
                <li><i className="guide-chip guide-actual" aria-hidden="true" /> {text.guideActual}</li>
                <li><i className="guide-chip guide-planned" aria-hidden="true" /> {text.guidePlanned}</li>
                <li><i className="guide-chip guide-turn" aria-hidden="true" /> {text.guideTurn}</li>
              </ul>
            </div>

            <details className="clarity-details rotation-details">
              <summary>{text.rotationDetailsSummary}</summary>
              <div className="clarity-details-inner">
                <p>{text.rotationScopeDetails}</p>
              </div>
            </details>
          </div>
        </div>
      </section>

      <MechanismSection language={language} data={v1aData as MechanismData} airportCitiesEn={AIRPORT_CITY_EN} weather={v2aData} adjustedWeather={v2bData as V2BData} />
      <CongestionSection language={language} data={v3aData as unknown as V3AData} airportCityEn={AIRPORT_CITY_EN} />
      <EpisodeExplorer language={language} data={v1bData as V1BData} weather={v2aData} />

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
        <p className="integrity-note">{text.integrityNote}</p>
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
