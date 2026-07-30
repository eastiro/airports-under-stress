"use client";

import { useMemo, useState } from "react";
import { AIRPORT_ZH } from "./airport-names-zh";

type Language = "zh" | "en";

type WindowKey = "30" | "60" | "90";

type Cell = {
  n: number;
  propagated: number;
  rate: number;
  wilsonLower: number;
  wilsonUpper: number;
};

type AirportWindow = {
  low: Cell;
  high: Cell;
  gapPercentagePoints: number;
};

type AirportPayload = {
  windows: Record<WindowKey, AirportWindow>;
  direction60: "higher" | "lower" | "equal";
  directionLabel: "samePositive" | "sameNegative" | "mixed";
};

export type V3BData = {
  version: string;
  primaryWindowMinutes: number;
  windows: WindowKey[];
  airportThreshold: number;
  scope: { totalAirports: number; eligibleAirports: number; excludedAirports: number; eventCount: number };
  directionCounts60: { positive: number; negative: number; equal: number };
  samePositiveAirports: number;
  counterexamples60: string[];
  defaultAirport: string;
  excluded: Array<{ airport: string; lowN: number; highN: number; reason: string }>;
  airports: Record<string, AirportPayload>;
};

type Props = {
  language: Language;
  data: V3BData;
  airportZh: typeof AIRPORT_ZH;
  airportCityEn: Record<string, string>;
};

function pct(value: number, digits = 2) {
  return `${(value * 100).toFixed(digits)}%`;
}
function int(value: number) {
  return new Intl.NumberFormat("en-US").format(value);
}
function airportCity(
  code: string,
  language: Language,
  airportZh: typeof AIRPORT_ZH,
  airportCityEn: Record<string, string>,
) {
  if (language === "zh") return airportZh[code]?.city ?? code;
  return airportCityEn[code] ?? code;
}

export default function AirportExplorer({ language, data, airportZh, airportCityEn }: Props) {
  const [selectedCode, setSelectedCode] = useState<string>(data.defaultAirport);

  // The primary card is fixed to the 60-minute window; the 30/90 band is a
  // sensitivity check, not an active state to toggle, so there is no active window.
  const activeWindow: WindowKey = "60";
  const codes = useMemo(
    () => Object.keys(data.airports).sort((a, b) => a.localeCompare(b)),
    [data.airports],
  );
  const airport = data.airports[selectedCode] ?? data.airports[data.defaultAirport];
  const windowData = airport.windows[activeWindow];
  const lowRate = windowData.low.rate;
  const highRate = windowData.high.rate;
  const gap = windowData.gapPercentagePoints;
  const isReverse = airport.direction60 === "lower";

  const labels = language === "zh"
    ? {
        subheading: "换到一座机场，结果还一样吗？",
        transition:
          "选择一座机场，只和自己比较：54 个样本足够的机场中，52 个在排班较密时更常继续晚点；但也有反例，所以这里不做机场好坏排名，只描述这座机场和自己平时相比的结果。",
        selectLabel: "选择机场",
        selectAria: "从 54 个样本足够的机场中任选一座",
        lowCard: "排班较松时继续晚点率",
        highCard: "排班较密时继续晚点率",
        diffCard: "两组相差",
        cardSub: "已经晚点的飞机继续晚点",
        explanationPositive: (city: string, g: number) =>
          `在 ${city} 自己排班较密的时段，已经晚点的飞机继续晚点的比例比排班较松时高约 ${Math.round(g)} 个百分点。`,
        explanationReverse:
          "这个机场在本月出现了相反方向；这不代表排班更密有帮助，航线、时段、天气等构成可能同时不同。",
        windowBandTitle: "换三种统计范围，方向稳不稳",
        primaryTag: "主口径",
        checkNote: "30 / 90 是“换尺子检查”，只看同方向是否还在，不是三条同等结论。",
        samePositive: "换三种统计范围（30 / 60 / 90 分钟），方向都一样：排班较密时更常继续晚点。",
        sameNegative: "三种统计范围都显示相反方向，说明这座机场本月的构成与多数机场不同，只描述、不排名。",
        mixed: "三种统计范围方向不完全一致，说明这座机场的“排班较密更常继续晚点”并不稳定，只描述、不排名。",
        detailsSummary: "查看研究细节",
        detailTitle: "这页数字是怎么来的",
        thresholdLine: `每座机场要求排班较松、排班较密两组都至少 ${data.airportThreshold} 条；不足者不进入可选列表，也不显示为 0%。`,
        currentAirportTitle: (code: string) => `当前机场 ${code} 三档明细（30 / 60 / 90 分钟，主口径 60）`,
        windowLabel: "统计范围",
        lowGroup: "排班较松",
        highGroup: "排班较密",
        propagatedLabel: "其中继续晚点",
        rateLabel: "继续晚点率",
        wilsonLabel: "Wilson 95% 估计范围",
        omaLine: `OMA 因排班较密组仅 82 条、排班较松组 140 条，低于每机场每组 ${data.airportThreshold} 条门槛，被排除在可选列表之外。`,
        directionLine: `全国 54 个合格机场中，${data.directionCounts60.positive} 个“排班较密组继续晚点率”高于“排班较松组”，${data.directionCounts60.negative} 个相反（${data.counterexamples60.join("、")}）；这 ${data.directionCounts60.positive}/${data.scope.eligibleAirports} 只表示方向，不表示因果稳健或统计显著。`,
        samePosLine: `三档统计范围（30 / 60 / 90 分钟）方向均为正的合格机场有 ${data.samePositiveAirports} 个；这只表示方向稳定，不表示因果稳健。`,
        onlySelfLine: "每座机场只和自己的通常水平比，不把大型枢纽和小机场直接按航班量排名。",
        counterLine: "反例与 mixed 不等于结论错误：航线、时段、天气等构成可能同时不同。",
        boundaryLine: "这里只看到“排班更密”和“晚点继续”经常一起出现，不能证明排班密造成了延误。",
      }
    : {
        subheading: "Does it hold at a single airport?",
        transition:
          "Choose an airport and compare it only with itself: among the 54 airports with enough samples, 52 more often kept delay moving when tightly scheduled; there are counterexamples, so this is not an airport ranking — only this airport compared with its own usual level.",
        selectLabel: "Choose airport",
        selectAria: "Select any of the 54 airports with enough samples",
        lowCard: "Stayed-late rate, loosest schedule",
        highCard: "Stayed-late rate, tightest schedule",
        diffCard: "Gap between groups",
        cardSub: "already-late aircraft stayed late",
        explanationPositive: (city: string, g: number) =>
          `At ${city}, in its own tightest-scheduled periods, the share of already-late aircraft that stayed late is about ${Math.round(g)} percentage points higher than in its loosest-scheduled periods.`,
        explanationReverse:
          "This airport shows the opposite direction this month; that does not mean tighter scheduling helped — route, time-of-day and weather composition may all differ at once.",
        windowBandTitle: "Does the direction hold under a different range?",
        primaryTag: "primary",
        checkNote: "30 / 90 are sensitivity checks with a different ruler, not three equal conclusions.",
        samePositive: "Under all three ranges (30 / 60 / 90 minutes) the direction is the same: tighter schedule more often keeps delay moving.",
        sameNegative: "All three ranges show the opposite direction, so this airport's composition differs from most; descriptive only, not a ranking.",
        mixed: "The three ranges do not fully agree, so 'tighter schedule keeps delay moving' is not stable here; descriptive only, not a ranking.",
        detailsSummary: "View research details",
        detailTitle: "How these numbers are computed",
        thresholdLine: `Each airport needs at least ${data.airportThreshold} handoffs in both the loosest and tightest groups; those below are excluded and not shown as 0%.`,
        currentAirportTitle: (code: string) => `Current airport ${code} per-tier detail (30 / 60 / 90 minutes, primary 60)`,
        windowLabel: "Range",
        lowGroup: "Loosest schedule",
        highGroup: "Tightest schedule",
        propagatedLabel: "Stayed late",
        rateLabel: "stayed-late rate",
        wilsonLabel: "Wilson 95% interval",
        omaLine: `OMA is excluded from the selector because its tightest group has only 82 handoffs and its loosest 140, below the per-airport ${data.airportThreshold}-handoff threshold.`,
        directionLine: `Of the 54 eligible airports, ${data.directionCounts60.positive} have a higher stayed-late rate in the tightest group than the loosest, and ${data.directionCounts60.negative} are opposite (${data.counterexamples60.join(", ")}); this ${data.directionCounts60.positive}/${data.scope.eligibleAirports} is direction only, not causal robustness or significance.`,
        samePosLine: `${data.samePositiveAirports} eligible airports are positive under all three ranges (30 / 60 / 90 minutes); that shows directional stability, not causal robustness.`,
        onlySelfLine: "Each airport is compared only with its own usual level, not ranked against others by flight count.",
        counterLine: "Counterexamples and mixed directions are not errors: route, time-of-day and weather composition may all differ.",
        boundaryLine: "We only see that tighter scheduling and continued delay often appear together — this does not prove tighter scheduling caused the delay.",
      };

  const cityName = airportCity(selectedCode, language, airportZh, airportCityEn);
  const explanation = isReverse
    ? labels.explanationReverse
    : labels.explanationPositive(cityName, gap);

  const directionSentence =
    airport.directionLabel === "samePositive"
      ? labels.samePositive
      : airport.directionLabel === "sameNegative"
        ? labels.sameNegative
        : labels.mixed;

  return (
    <div id="airport-explorer" className="airport-explorer">
      <div className="section-heading">
        <div>
          <span className="section-kicker">{language === "zh" ? "机场层观察 · V3-B" : "Airport view · V3-B"}</span>
          <h3 className="airport-explorer-subtitle">{labels.subheading}</h3>
        </div>
        <p className="airport-explorer-transition">{labels.transition}</p>
      </div>

      <div className="airport-selector-rail">
        <label className="airport-selector">
          <span>{labels.selectLabel}</span>
          <select
            name="v3b-airport"
            value={selectedCode}
            onChange={(e) => setSelectedCode(e.target.value)}
            aria-label={labels.selectAria}
          >
            {codes.map((code) => (
              <option key={code} value={code}>
                {code} · {airportCity(code, language, airportZh, airportCityEn)}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="congestion-grid airport-explorer-grid">
        <div>
          <small>{labels.lowCard}</small>
          <strong>{pct(lowRate)}</strong>
          <span>{labels.cardSub}</span>
        </div>
        <div>
          <small>{labels.highCard}</small>
          <strong>{pct(highRate)}</strong>
          <span>{labels.cardSub}</span>
        </div>
        <div className="is-highlight">
          <small>{labels.diffCard}</small>
          <strong>
            {language === "zh" ? `约 ${Math.round(gap)}` : `about ${Math.round(gap)}`}{" "}
            <em>{language === "zh" ? "个百分点" : "pp"}</em>
          </strong>
          <span>{labels.cardSub}</span>
        </div>
      </div>

      <p className="airport-explorer-explanation">{explanation}</p>

      <div className="airport-explorer-band">
        <span className="airport-explorer-band-title">{labels.windowBandTitle}</span>
        <div className="airport-explorer-band-rows" role="list">
          {data.windows.map((w) => {
            const cell = airport.windows[w];
            const primary = w === "60";
            return (
              <div
                key={w}
                role="listitem"
                className={`airport-explorer-band-row${primary ? " is-primary" : ""}`}
              >
                <span className="airport-explorer-band-window">
                  {w} min{primary ? ` · ${labels.primaryTag}` : ""}
                </span>
                <span className="airport-explorer-band-track" aria-hidden="true">
                  <i style={{ width: `${Math.max(2, cell.low.rate * 100)}%` }} className="is-low" />
                  <i style={{ width: `${Math.max(2, cell.high.rate * 100)}%` }} className="is-high" />
                </span>
                <strong className="airport-explorer-band-gap">
                  {cell.gapPercentagePoints >= 0 ? "+" : ""}
                  {Math.round(cell.gapPercentagePoints)}
                  <em>{language === "zh" ? "pp" : "pp"}</em>
                </strong>
              </div>
            );
          })}
        </div>
        <p className="airport-explorer-band-note">{directionSentence} {labels.checkNote}</p>
      </div>

      <details className="clarity-details airport-explorer-details">
        <summary>{labels.detailsSummary}</summary>
        <div className="clarity-details-inner">
          <h4>{labels.detailTitle}</h4>
          <ul className="congestion-detail-list">
            <li>{labels.thresholdLine}</li>
            <li>{labels.directionLine}</li>
            <li>{labels.samePosLine}</li>
            <li>{labels.onlySelfLine}</li>
            <li>{labels.counterLine}</li>
            <li>{labels.omaLine}</li>
          </ul>

          <h4>{labels.currentAirportTitle(selectedCode)}</h4>
          <div className="airport-explorer-detail-table">
            <div className="airport-explorer-detail-head">
              <span>{labels.windowLabel}</span>
              <span>{language === "zh" ? "分组" : "Group"}</span>
              <span>n</span>
              <span>{labels.propagatedLabel}</span>
              <span>{labels.rateLabel}</span>
              <span>{labels.wilsonLabel}</span>
            </div>
            {data.windows.map((w) => {
              const cell = airport.windows[w];
              const isWindowPrimary = w === "60";
              return (
                <div className="airport-explorer-detail-window" key={w}>
                  <div className="airport-explorer-detail-row">
                    <span>{w} min{isWindowPrimary ? ` · ${labels.primaryTag}` : ""}</span>
                    <span>{labels.lowGroup}</span>
                    <span>{int(cell.low.n)}</span>
                    <span>{int(cell.low.propagated)}</span>
                    <span>{pct(cell.low.rate)}</span>
                    <span>{pct(cell.low.wilsonLower)} – {pct(cell.low.wilsonUpper)}</span>
                  </div>
                  <div className="airport-explorer-detail-row">
                    <span>{w} min{isWindowPrimary ? ` · ${labels.primaryTag}` : ""}</span>
                    <span>{labels.highGroup}</span>
                    <span>{int(cell.high.n)}</span>
                    <span>{int(cell.high.propagated)}</span>
                    <span>{pct(cell.high.rate)}</span>
                    <span>{pct(cell.high.wilsonLower)} – {pct(cell.high.wilsonUpper)}</span>
                  </div>
                </div>
              );
            })}
          </div>

          <p className="congestion-boundary">{labels.boundaryLine}</p>
        </div>
      </details>
    </div>
  );
}
