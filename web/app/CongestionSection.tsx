"use client";

import { useState } from "react";
import AirportExplorer, { type V3BData } from "./AirportExplorer";
import v3bData from "./v3-b-data.json";
import { AIRPORT_ZH } from "./airport-names-zh";

type Language = "zh" | "en";

export type V3AData = {
  version: string;
  defaultWindowMinutes: number;
  windows: string[];
  scope: { mechanismAirports: number; eventCount: number };
  plannedMovements: Record<string, { median: number; p90: number }>;
  groups: Record<string, { low: GroupMetric; middle: GroupMetric; high: GroupMetric }>;
  highMinusLow: Record<string, { percentagePoints: number; computedFrom: string }>;
  windowSensitivity: Record<string, {
    spearmanVs60m: number;
    quartileAgreementVs60m: number;
    highMinusLowPropagationRate: number;
  }>;
  concentration: { maxHighAirportShare: number; maxHighDayShare: number };
  airportGate: {
    passed: boolean;
    minHighN: number;
    minLowN: number;
    threshold: number;
    minHighAirport: string;
  };
  gateDecision: string;
  interpretationBoundary: string;
};

type GroupMetric = { n: number; propagationRate: number };

type Props = { language: Language; data: V3AData; airportCityEn: Record<string, string> };

function pct(value: number, digits = 2) {
  return `${(value * 100).toFixed(digits)}%`;
}
function int(value: number) {
  return new Intl.NumberFormat("en-US").format(value);
}

export default function CongestionSection({ language, data, airportCityEn }: Props) {
  const [activeWindow, setActiveWindow] = useState<string>(String(data.defaultWindowMinutes));

  const labels = language === "zh"
    ? {
        section: "06 / 计划拥挤",
        title: "航班排得越密，延误越容易继续吗？",
        conclusion: `在 ${activeWindow} 分钟统计范围下，排班最松的一组里已经晚点的飞机“继续晚点”的比例为 ${pct(data.groups[activeWindow].low.propagationRate)}；排班最密的一组为 ${pct(data.groups[activeWindow].high.propagationRate)}，两组相差约 ${Math.round(data.highMinusLow[activeWindow].percentagePoints)} 个百分点。`,
        lowCard: "排班较松",
        highCard: "排班较密",
        diffCard: "两组相差",
        cardSub: "继续晚点比例",
        diffHelp: "排班更密的一组里，已经晚点的飞机继续晚点的比例高出这么多。",
        boundary: "这里只看到“排班更密”和“晚点继续”经常一起出现，不能证明排班密造成了延误。天气、空管、跑道容量等共同冲击也可能同时存在。",
        toggleAria: "计划拥挤统计范围",
        windowHelp: "30 / 60 / 90 分钟是围绕同一计划起飞时刻的三种统计范围：30 = 前 15 + 后 15，60 = 前 30 + 后 30，90 = 前 45 + 后 45。它们衡量时刻表排得多密，不衡量延误持续了多久。默认 60 为主口径，30/90 用来检查换一把尺子后主要方向是否仍在。",
        withinAirport: "排班松紧是在每个机场内部比较：一个时刻只和这个机场自己的通常水平相比，不把大型枢纽和小机场直接比航班数量。",
        barsNote: "条越长，说明这一组里已经晚点的飞机越常继续晚点。我们比较的是“排班最松”和“排班最密”两组，不是某一天实时堵不堵。",
        detailsSummary: "查看研究细节",
        detail1Title: "这是怎么算的",
        lowGroup: "低组（排班较松）",
        midGroup: "中间组（中间 50%）",
        highGroup: "高组（排班较密）",
        eventsUnit: "次航班衔接",
        rateLabel: "继续晚点",
        detail1Movements: (median: number, p90: number) => `该统计范围计划总架次：中位数 ${int(median)}，第 90 百分位 ${int(p90)}。`,
        detail1Note: "“计划拥挤”来自时刻表原本排得多密，不是当天实时堵塞，也不是机场安全或能力排名。",
        detail1Percentile: "在每个机场内部，按相对百分位把衔接分为约 25% 低、50% 中、25% 高。由于并列值，实际样本不会严格等于 25/50/25。低/中/高描述的是“某机场的某个时刻或航班衔接”，不是机场的永久类别。",
        detail2Title: "换一种统计范围，结果还稳不稳",
        detail2Primary: "60 分钟是主口径；这里不另算自相关指标，只展示它自身的低/中/高组对比。",
        detail2Sensitivity: (spearman: number, quartile: string) => `与 60 分钟主口径相比，${activeWindow} 分钟的排序相关性（Spearman）为 ${spearman.toFixed(3)}，四分位一致率为 ${quartile}。`,
        detail2Note30: "30 分钟口径下四分位一致率约 51%，只作敏感性参考，不可当作稳定的机场排序。",
        detail3Title: "为什么不做机场排名",
        detail3Coverage: `本次覆盖 ${data.scope.mechanismAirports} 个机场，全国低/中/高组样本充足（各数万次航班衔接）。`,
        detail3PerAirport: `逐机场比较要求高、低组都至少 ${data.airportGate.threshold} 次；目前未完全通过，因此本版不做 ${data.scope.mechanismAirports} 机场全量排名或搜索。`,
        detail3Oma: `样本最少的是 ${data.airportGate.minHighAirport}：高拥挤组 ${data.airportGate.minHighN} 次，低于每机场 ${data.airportGate.threshold} 次门槛，故 Gate 为 ${data.gateDecision}。`,
        detail3Note: "未展示的机场不代表更差；样本不足的机场也不显示为 0%。",
      }
    : {
        section: "06 / Scheduled congestion",
        title: "Does a tighter schedule keep delay moving?",
        conclusion: `At the ${activeWindow}-minute range, among the loosest-scheduled group the share of already-late aircraft that stayed late is ${pct(data.groups[activeWindow].low.propagationRate)}; for the tightest-scheduled group it is ${pct(data.groups[activeWindow].high.propagationRate)} — a gap of about ${Math.round(data.highMinusLow[activeWindow].percentagePoints)} percentage points.`,
        lowCard: "Loosest schedule",
        highCard: "Tightest schedule",
        diffCard: "Gap between groups",
        cardSub: "stayed late",
        diffHelp: "The tighter-scheduled group shows this much higher a share of continued delay.",
        boundary: "We only see that tighter scheduling and continued delay often appear together — this does not prove that tight scheduling caused the delay. Shared shocks such as weather, air-traffic control, or runway capacity may also be at play.",
        toggleAria: "Scheduled-congestion statistic range",
        windowHelp: "These 30 / 60 / 90 minute buttons are three total statistic ranges around the same scheduled departure: 30 = 15 before + 15 after, 60 = 30 before + 30 after, 90 = 45 before + 45 after. They measure how tightly the timetable is packed, not how long a delay lasted. 60 minutes is the primary range; 30/90 check whether the main direction still holds under a different ruler.",
        withinAirport: "Tightness is compared within each airport: a given moment is measured only against that airport's own usual level, not by comparing a large hub directly to a small airport by flight count.",
        barsNote: "A longer bar means aircraft in that group more often stayed late. We compare the loosest- and tightest-scheduled groups, not whether a given day was congested in real time.",
        detailsSummary: "View research details",
        detail1Title: "How this is computed",
        lowGroup: "Low group (loosest)",
        midGroup: "Middle group (middle 50%)",
        highGroup: "High group (tightest)",
        eventsUnit: "flight handoffs",
        rateLabel: "stayed late",
        detail1Movements: (median: number, p90: number) => `Planned total movements in this range: median ${int(median)}, 90th percentile ${int(p90)}.`,
        detail1Note: "Scheduled congestion comes from how tightly the timetable is packed, not that day's live congestion, and not a safety or capacity ranking.",
        detail1Percentile: "Within each airport, handoffs are split by relative percentile into roughly 25% low, 50% middle, 25% high. Ties mean the actual split is not exactly 25/50/25. Low/middle/high describe a moment or handoff at an airport, not a permanent airport category.",
        detail2Title: "Does it hold under a different range?",
        detail2Primary: "60 minutes is the primary range; we do not compute a separate autocorrelation metric, only its own low/middle/high contrast.",
        detail2Sensitivity: (spearman: number, quartile: string) => `Against the 60-minute primary range, the ${activeWindow}-minute rank correlation (Spearman) is ${spearman.toFixed(3)} and quartile agreement is ${quartile}.`,
        detail2Note30: "At the 30-minute range, quartile agreement is only about 51%, so it is a sensitivity check, not a stable airport ranking.",
        detail3Title: "Why we don't rank airports",
        detail3Coverage: `This covers ${data.scope.mechanismAirports} airports with adequate national low/middle/high samples (tens of thousands of flight handoffs each).`,
        detail3PerAirport: `A per-airport comparison requires at least ${data.airportGate.threshold} handoffs in both the high and low groups; this is not yet met everywhere, so this version has no full ${data.scope.mechanismAirports}-airport ranking or search.`,
        detail3Oma: `The smallest sample is ${data.airportGate.minHighAirport}: its high-congestion group has ${data.airportGate.minHighN} handoffs, below the per-airport ${data.airportGate.threshold}-handoff threshold, so the gate is ${data.gateDecision}.`,
        detail3Note: "Airports not shown are not implied to perform worse; under-sampled airports are not shown as 0%.",
      };

  const group = data.groups[activeWindow];
  const diff = data.highMinusLow[activeWindow].percentagePoints;
  const movements = data.plannedMovements[activeWindow];
  const isPrimary = activeWindow === "60";
  const sensitivity = isPrimary ? null : data.windowSensitivity[activeWindow];

  const lowPct = pct(group.low.propagationRate);
  const midPct = pct(group.middle.propagationRate);
  const highPct = pct(group.high.propagationRate);
  const diffRounded = Math.round(diff);
  const diffDisplay = language === "zh" ? `约 ${diffRounded}` : `about ${diffRounded}`;
  const diffUnit = language === "zh" ? "个百分点" : "pp";
  const showNote30 = activeWindow === "30";

  return (
    <section id="congestion" className="analysis-section congestion-section section-shell">
      <div className="section-heading">
        <div>
          <span className="section-number">{labels.section}</span>
          <h2>{labels.title}</h2>
        </div>
      </div>

      {/* 一眼层：默认可见 */}
      <p className="congestion-conclusion">{labels.conclusion}</p>

      <div className="congestion-grid">
        <div>
          <small>{labels.lowCard}</small>
          <strong>{lowPct}</strong>
          <span>{labels.cardSub}</span>
        </div>
        <div>
          <small>{labels.highCard}</small>
          <strong>{highPct}</strong>
          <span>{labels.cardSub}</span>
        </div>
        <div className="is-highlight">
          <small>{labels.diffCard}</small>
          <strong>{diffDisplay} <em>{diffUnit}</em></strong>
          <span>{labels.diffHelp}</span>
        </div>
      </div>

      <p className="congestion-boundary">{labels.boundary}</p>

      {/* 理解层：默认可见 */}
      <div className="congestion-toolbar">
        <div className="congestion-window-toggle" role="radiogroup" aria-label={labels.toggleAria}>
          {data.windows.map((value) => (
            <button
              type="button"
              key={value}
              role="radio"
              aria-checked={activeWindow === value}
              className={activeWindow === value ? "is-active" : ""}
              onClick={() => setActiveWindow(value)}
            >
              {value} min
            </button>
          ))}
        </div>
        <p className="congestion-window-help">{labels.windowHelp}</p>
      </div>

      <div className="congestion-bars" aria-hidden="true">
        <div className="congestion-bar-row is-low">
          <span>{labels.lowCard}</span>
          <span className="congestion-bar-track"><i style={{ width: `${Math.max(2, group.low.propagationRate * 100)}%` }} /></span>
          <strong>{lowPct}</strong>
        </div>
        <div className="congestion-bar-row">
          <span>{labels.highCard}</span>
          <span className="congestion-bar-track"><i style={{ width: `${Math.max(2, group.high.propagationRate * 100)}%` }} /></span>
          <strong>{highPct}</strong>
        </div>
      </div>
      <p className="congestion-bars-note">{labels.barsNote}</p>
      <p className="congestion-within-note">{labels.withinAirport}</p>

      {/* V3-B 机场层探索器：放在全国结论/理解层之后、研究细节之前 */}
      <AirportExplorer language={language} data={v3bData as unknown as V3BData} airportZh={AIRPORT_ZH} airportCityEn={airportCityEn} />

      {/* 研究细节：默认收起 */}
      <details className="congestion-details">
        <summary>{labels.detailsSummary}</summary>
        <div className="congestion-detail-inner">
          <div className="congestion-detail-group">
            <h3>{labels.detail1Title}</h3>
            <ul className="congestion-detail-list">
              <li>{labels.lowGroup}：{int(group.low.n)} {labels.eventsUnit}，{labels.rateLabel} {lowPct}</li>
              <li>{labels.midGroup}：{int(group.middle.n)} {labels.eventsUnit}，{labels.rateLabel} {midPct}</li>
              <li>{labels.highGroup}：{int(group.high.n)} {labels.eventsUnit}，{labels.rateLabel} {highPct}</li>
            </ul>
            <p>{labels.detail1Movements(movements.median, movements.p90)}</p>
            <p>{labels.detail1Note}</p>
            <p>{labels.detail1Percentile}</p>
          </div>

          <div className="congestion-detail-group">
            <h3>{labels.detail2Title}</h3>
            {isPrimary ? (
              <p>{labels.detail2Primary}</p>
            ) : (
              <div>
                <p>{labels.detail2Sensitivity(sensitivity.spearmanVs60m, pct(sensitivity.quartileAgreementVs60m, 1))}</p>
                {showNote30 && <p>{labels.detail2Note30}</p>}
              </div>
            )}
          </div>

          <div className="congestion-detail-group">
            <h3>{labels.detail3Title}</h3>
            <ul className="congestion-detail-list">
              <li>{labels.detail3Coverage}</li>
              <li>{labels.detail3PerAirport}</li>
              <li>{labels.detail3Oma}</li>
              <li>{labels.detail3Note}</li>
            </ul>
          </div>
        </div>
      </details>
    </section>
  );
}
