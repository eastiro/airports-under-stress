"use client";

import { useEffect, useRef, useState } from "react";
import type { Language } from "./dashboard";
import { AIRLINE_ZH, AIRPORT_ZH } from "./airport-names-zh";

type Threshold = 15 | 30 | 60;
type Airport = { code: string; cityEn: string; cityZh?: string };
type Flight = { carrierCode: string; carrierNameEn: string; flightNumber: string | null };
type Step = {
  stepIndex: number; stepType: string; stateKey: string;
  prevAirport: Airport; turnAirport: Airport; nextAirport: Airport | null;
  previousFlight: Flight | null; nextFlight: Flight | null;
  prevArrivalDelay: number; nextDepartureDelay: number; nextArrivalDelay: number;
  delayDelta: number; plannedTurnMinutes: number; actualTurnMinutes: number;
  prevActualArrivalUTC: string; nextActualDepartureUTC: string; nextActualArrivalUTC: string;
};
type ThresholdStep = {
  sourceStepIndex: number; phase: "departure" | "arrival"; stateKey: string; depthAfterStep: number;
};
type ThresholdView = {
  threshold: Threshold; qualifies: boolean; depth: number; observationCount: number;
  maxDepartureDelay: number | null; cumulativeAmplificationMinutes: number; durationMinutes: number;
  uniqueAirportsTouched: number; outcome: "recovered" | "censored" | "not_qualified";
  terminationReason: string; endUTC: string; steps: ThresholdStep[];
};
type Episode = {
  episodeId: string; selectionCategory: string; selectionReasonKey?: string;
  tailNumber: string; depth: number; outcome: "recovered" | "censored";
  initialArrivalDelay: number; airportsTouched: string[]; steps: Step[];
  thresholdViews: Record<string, ThresholdView>;
};
type SensitivityRow = {
  threshold: Threshold; nEpisodes: number; nDeep2: number; nDeep3: number;
  maxDepth: number; nAirportsExposed500: number;
};
export type V1BData = {
  thresholdMinutes: number; availableThresholds: Threshold[];
  sourceSummary: { nEpisodes: number }; thresholdSensitivity: SensitivityRow[];
  episodeContinuity: { maxScheduledTurnMinutes: number; maxDurationHours: number };
  thresholdStability: { "15vs30Spearman": number; "15vs30Top20Overlap": number; "15vs60Spearman": number | null; "15vs60Top20Overlap": number };
  episodes: Episode[];
};

const copy = {
  zh: {
    section: "07 / 连续延误案例", title: "同一架飞机，延误状态能延续多久？",
    intro: "案例跟随同一架飞机的一串连续航班，看晚点是继续、加重，还是被追回。单个案例最多跟踪 18 小时；如果两班之间计划停场超过 180 分钟，就不再把它们算作同一段连续运行。",
    lab: "换一种晚点标准，结论会变吗？", labIntro: "主页面把晚 15 分钟算作晚点；切换到 30 或 60 分钟，可以检查只有更严重的晚点是否仍会连续出现。这三个按钮改变的是“多晚才算晚点”，不是观察时长。", threshold: "多晚才算晚点",
    thresholdNames: { 15: "标准", 30: "严格", 60: "极端" },
    episodes: "全国连续延误段", deep3: "至少连续 3 次", maxDepth: "最长连续晚点次数", airports500: "晚到衔接 ≥500 次的机场", detailsSummary: "查看研究细节", weatherDetails: "查看这一步的天气",
    baseline: "主分析基线：观察达到 15 分钟的连续晚点状态。",
    comparison30: "相较 15 分钟标准，连续延误段减少 {episodes}，至少连续 3 次的情况减少 {deep}；最常传播的航线排序仍较稳定。",
    comparison60: "相较 15 分钟标准，连续延误段减少 {episodes}，至少连续 3 次的情况减少 {deep}；只有最严重的晚点被保留下来，观察对象明显改变。",
    play: "播放", pause: "暂停", previous: "上一步", next: "下一步", restart: "重新开始", step: "步骤", timeline: "延误变化过程", current: "当前这一步", why: "为何值得看", summary: "整段旅程总结",
    recoveredRule: "按当前晚点标准，这架飞机连续 {depth} 次仍然晚点，第 {observations} 步终于恢复。最后这次恢复只用于说明结局，不计入连续晚点次数。",
    censoredRule: "按当前晚点标准，已经连续观察到 {depth} 次晚点；随后观察因边界停止，尚不知道后来是否恢复。页面共有 {observations} 个步骤。",
    arrival: "上一班到达晚了", departure: "下一班起飞晚了", nextArrival: "下一班到达晚了", delta: "延误增加 / 减少", turn: "计划 / 实际停场", time: "这一段发生在", depth: "连续晚点次数", observed: "页面展示步骤", maxDeparture: "最严重起飞延误", amplification: "相比开始最多增加", duration: "跟踪时长", airports: "经过机场", outcome: "记录结束时", recovered: "延误已追回", censored: "未观察到最终结果", notQualified: "不属于连续延误段", finalRecovery: "含最后一次恢复判断", boundary: "观察可能因为计划停场超过 180 分钟、达到 18 小时上限、航班衔接断开或样本结束而停止；这不代表飞机后来没有恢复。", disclaimer: "所有时间为 UTC。这里只描述同一架飞机上的连续晚点现象，不声称最初一次延误造成了后面全部晚点。",
    noEpisodeTitle: "按当前标准，这里还不能算连续延误的开始。", noEpisodeBody: "第一班到达只晚了 {delay} 分钟，没有达到“晚 {threshold} 分钟才算晚点”的标准。航班记录仍然存在，只是不进入这组连续延误案例。",
    categories: { deepest: "最深延续", high_delay_recovered: "大延误后恢复", high_pressure_day: "高压力日", normal_day: "普通日", crosses_midnight: "跨 UTC 午夜", censored: "观察中断" },
    states: { propagated: "延误继续传递", amplified: "延误正在放大", caught_up: "延误正在追回", recovered: "起飞前恢复", recovered_en_route: "在途恢复" },
    endings: { recovered: "在下一次起飞前恢复", recovered_en_route: "该延误航段在途中恢复", scheduled_turn_break: "计划停场超过 180 分钟，连续观察在此结束", duration_limit: "达到 18 小时观察上限", airport_discontinuity: "飞机轮转链在此断开", end_of_sequence: "样本记录在此结束", initial_delay_below_threshold: "起始延误未达到当前门槛" },
  },
  en: {
    section: "07 / Continuous-delay cases", title: "How long does a late state persist on one aircraft?",
    intro: "Cases follow a continuous late state on one tail; they do not attribute the whole chain to one cause. Episodes are observed for at most 18 hours and stop at planned turns over 180 minutes, then are reclassified at 15, 30, and 60 minutes.",
    lab: "Definition sensitivity lab", labIntro: "15 minutes is the primary delay baseline; 30 and 60 test threshold sensitivity. Every view shares the 180-minute planned-turn and 18-hour continuity limits.", threshold: "Delay threshold",
    thresholdNames: { 15: "Standard", 30: "Strict", 60: "Extreme" },
    episodes: "National episodes", deep3: "Depth ≥3", maxDepth: "Maximum depth", airports500: "Airports with ≥500 exposures", detailsSummary: "View research details", weatherDetails: "Weather at this step",
    baseline: "Primary baseline: observes continuous late states reaching 15 minutes.",
    comparison30: "Versus 15 minutes, episodes fall {episodes} and depth ≥3 falls {deep}; link ranks remain fairly stable (Spearman 0.896, Top 20 overlap 20/20).",
    comparison60: "Versus 15 minutes, episodes fall {episodes} and depth ≥3 falls {deep}; Top 20 overlap drops to 3/20, so the extreme threshold changes what is observed.",
    play: "Play", pause: "Pause", previous: "Previous observation", next: "Next observation", restart: "Restart", step: "Observation", timeline: "Observation sequence", current: "Current observation", why: "Why this case", summary: "Episode summary",
    recoveredRule: "At this threshold: {depth} above-threshold propagated legs + 1 recovery decision = {observations} observations. The terminal recovery does not add to propagation depth.",
    censoredRule: "At this threshold, {depth} above-threshold propagated legs are observed; the record ends before recovery, for {observations} observations in total.",
    arrival: "Previous arrival delay", departure: "Next departure delay", nextArrival: "Next arrival delay", delta: "Delay change", turn: "Scheduled / actual turn", time: "Observed UTC", depth: "Continuity depth", observed: "Observations", maxDeparture: "Maximum departure delay", amplification: "Cumulative amplification", duration: "Episode duration", airports: "Airports touched", outcome: "Outcome", recovered: "Recovered", censored: "Observation interrupted", notQualified: "Not an episode", finalRecovery: "includes the terminal recovery observation", boundary: "Observation may stop at a long planned turn, the 18-hour ceiling, a chain break, or the sample boundary; this is not evidence that it never recovered.", disclaimer: "All times are UTC. This is a continuous late state on one tail, not proof that one initial delay caused the whole chain; weather, ATC, and congestion are not controlled.",
    noEpisodeTitle: "This disruption does not start under the active threshold.", noEpisodeBody: "The case begins with an arrival delay of {delay} minutes, below the {threshold}-minute threshold. The flight records still exist; only their classification changes.",
    categories: { deepest: "Deepest persistence", high_delay_recovered: "High delay, then recovery", high_pressure_day: "High-pressure day", normal_day: "Typical day", crosses_midnight: "Crosses UTC midnight", censored: "Observation interrupted" },
    states: { propagated: "Delay continues", amplified: "Delay is amplifying", caught_up: "Delay is being recovered", recovered: "Recovered before departure", recovered_en_route: "Recovered en route" },
    endings: { recovered: "Recovered before the next departure", recovered_en_route: "The delayed flight recovered en route", scheduled_turn_break: "The planned ground stop exceeds 180 minutes", duration_limit: "The 18-hour observation ceiling is reached", airport_discontinuity: "The aircraft rotation chain breaks here", end_of_sequence: "The observed sample ends here", initial_delay_below_threshold: "Initial delay does not reach this threshold" },
  },
};

function utc(value: string, language: Language) {
  return new Intl.DateTimeFormat(language === "zh" ? "zh-CN" : "en-US", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "UTC" }).format(new Date(value)).replace(",", "") + " UTC";
}
function city(airport: Airport | null, language: Language) {
  if (!airport) return "—";
  return language === "zh" ? (airport.cityZh ?? AIRPORT_ZH[airport.code]?.city ?? airport.cityEn) : airport.cityEn;
}
function airportLabel(airport: Airport | null, language: Language) {
  if (!airport) return "—";
  const cityName = city(airport, language);
  return cityName === airport.code ? airport.code : `${airport.code} ${cityName}`;
}
function flightLabel(flight: Flight | null) { return flight ? `${flight.carrierCode}${flight.flightNumber ?? ""}` : "—"; }
function airlineName(flight: Flight | null, language: Language) {
  if (!flight) return "";
  return language === "zh" ? (AIRLINE_ZH[flight.carrierCode] ?? flight.carrierNameEn) : flight.carrierNameEn;
}
function pctDrop(current: number, baseline: number, language: Language) {
  return new Intl.NumberFormat(language === "zh" ? "zh-CN" : "en-US", { style: "percent", maximumFractionDigits: 1 }).format((baseline - current) / baseline);
}
function fill(template: string, values: Record<string, string | number>) {
  return Object.entries(values).reduce((text, [key, value]) => text.replace(`{${key}}`, String(value)), template);
}
function durationText(minutes: number, language: Language) {
  if (minutes < 120) return `${minutes} min`;
  const hours = new Intl.NumberFormat(language === "zh" ? "zh-CN" : "en-US", { maximumFractionDigits: 1 }).format(minutes / 60);
  return `${hours} h (${minutes} min)`;
}

const WEATHER_FLAG_ZH: Record<string, string> = {
  low_visibility: "低能见度", low_ceiling: "低云底", strong_wind: "强风",
  precipitation: "降水", thunderstorm: "雷暴", fog: "雾 / 轻雾",
};
function weatherFlag(flag: string, language: Language) {
  return language === "zh" ? (WEATHER_FLAG_ZH[flag] ?? flag) : flag.replaceAll("_", " ");
}
function weatherMissing(reason: string | undefined, language: Language) {
  const zh: Record<string, string> = {
    unmapped_station: "机场无可用气象站映射",
    missing_event_time: "事件时刻缺失",
    no_complete_report_within_tolerance: "容差内没有完整 METAR/SPECI",
  };
  const en: Record<string, string> = {
    unmapped_station: "no mapped weather station",
    missing_event_time: "event time is missing",
    no_complete_report_within_tolerance: "no complete METAR/SPECI within tolerance",
  };
  return (language === "zh" ? zh : en)[reason ?? ""] ?? (language === "zh" ? "天气不可用" : "weather unavailable");
}
function weatherNumber(value: number | null | undefined, unit: string) {
  return value === null || value === undefined ? "—" : `${new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 }).format(value)} ${unit}`;
}

type EpisodeWeatherData = { episodeWeather?: Array<{ episodeId: string; steps: Array<{ stepIndex: number; weatherAtScheduledDeparture: Record<string, WeatherNote>; weatherAtActualArrival: Record<string, WeatherNote> }> }> };
type WeatherNote = {
  available: boolean; airport?: string; eventUTC?: string; observedUTC?: string;
  ageMinutes?: number; adverse?: boolean; flags?: string[]; reason?: string;
  reportType?: string; statusKey?: string;
  values?: { visibilityKm: number | null; ceilingFt: number | null; windSpeedMps: number | null; windGustMps: number | null };
};

export default function EpisodeExplorer({ language, data, weather }: { language: Language; data: V1BData; weather?: EpisodeWeatherData }) {
  const t = copy[language];
  const defaultEpisode = [...data.episodes].sort((a, b) => b.depth - a.depth || a.episodeId.localeCompare(b.episodeId))[0];
  const [id, setId] = useState(defaultEpisode.episodeId);
  const [threshold, setThreshold] = useState<Threshold>(15);
  const [weatherTolerance, setWeatherTolerance] = useState<60 | 90>(90);
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const stepRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const sectionRef = useRef<HTMLElement | null>(null);
  const episode = data.episodes.find(item => item.episodeId === id) ?? defaultEpisode;
  const view = episode.thresholdViews[String(threshold)];
  const viewStep = view.steps[index];
  const step = viewStep ? episode.steps.find(item => item.stepIndex === viewStep.sourceStepIndex) ?? null : null;
  const stepWeather = weather?.episodeWeather?.find(item => item.episodeId === episode.episodeId)?.steps.find(item => item.stepIndex === (step?.stepIndex ?? -1));
  const weatherNote = stepWeather ? (viewStep?.phase === "arrival" ? stepWeather.weatherAtActualArrival[String(weatherTolerance)] : stepWeather.weatherAtScheduledDeparture[String(weatherTolerance)]) : null;
  const sensitivity = data.thresholdSensitivity.find(item => item.threshold === threshold) ?? data.thresholdSensitivity[0];
  const baseline = data.thresholdSensitivity.find(item => item.threshold === 15) ?? data.thresholdSensitivity[0];
  const stop = () => { if (timer.current) clearInterval(timer.current); timer.current = null; setPlaying(false); };
  const setStep = (next: number) => { stop(); setIndex(Math.max(0, Math.min(view.steps.length - 1, next))); };

  useEffect(() => () => { if (timer.current) clearInterval(timer.current); }, []);
  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReducedMotion(query.matches);
    update(); query.addEventListener("change", update); return () => query.removeEventListener("change", update);
  }, []);
  useEffect(() => {
    // Scroll the tape itself, never the page: scrollIntoView here used to drag the
    // whole window ~9,000px down as soon as the section mounted.
    const node = stepRefs.current[index];
    const rail = node?.closest(".episode-tape") as HTMLElement | null;
    if (!node || !rail) return;
    const nodeRect = node.getBoundingClientRect();
    const railRect = rail.getBoundingClientRect();
    const delta = nodeRect.left - railRect.left - (railRect.width - nodeRect.width) / 2;
    rail.scrollTo({ left: rail.scrollLeft + delta, behavior: reducedMotion ? "auto" : "smooth" });
  }, [id, index, reducedMotion, threshold]);
  useEffect(() => {
    const element = sectionRef.current;
    if (!element || !("IntersectionObserver" in window)) return;
    const observer = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting && timer.current) stop();
    }, { threshold: 0.08 });
    observer.observe(element); return () => observer.disconnect();
  }, []);
  useEffect(() => {
    if (!playing || reducedMotion || !view.qualifies) return;
    timer.current = setInterval(() => setIndex(current => {
      if (current >= view.steps.length - 1) { if (timer.current) clearInterval(timer.current); timer.current = null; setPlaying(false); return current; }
      return current + 1;
    }), 2000);
    return () => { if (timer.current) clearInterval(timer.current); };
  }, [playing, reducedMotion, view.qualifies, view.steps.length]);

  const selectEpisode = (nextId: string) => { stop(); setId(nextId); setIndex(0); };
  const selectThreshold = (next: Threshold) => { stop(); setThreshold(next); setIndex(0); };
  const comparison = threshold === 15 ? t.baseline : fill(threshold === 30 ? t.comparison30 : t.comparison60, {
    episodes: pctDrop(sensitivity.nEpisodes, baseline.nEpisodes, language),
    deep: pctDrop(sensitivity.nDeep3, baseline.nDeep3, language),
  });

  let state = "";
  let explanation = "";
  if (step && viewStep) {
    state = t.states[viewStep.stateKey as keyof typeof t.states] ?? t.states.propagated;
    if (viewStep.stateKey === "amplified") explanation = language === "zh" ? `上一航段晚到 ${step.prevArrivalDelay} 分钟；下一航段以 ${step.nextDepartureDelay} 分钟延误起飞，观察到延误增加 ${step.delayDelta} 分钟。` : `The prior flight arrived ${step.prevArrivalDelay} minutes late; the next departed ${step.nextDepartureDelay} minutes late, an observed increase of ${step.delayDelta} minutes.`;
    else if (viewStep.stateKey === "caught_up") explanation = language === "zh" ? `下一航段仍超过 ${threshold} 分钟门槛，但从 ${step.prevArrivalDelay} 分钟回落到 ${step.nextDepartureDelay} 分钟，延误正在被追回。` : `The next flight remains above ${threshold} minutes but falls from ${step.prevArrivalDelay} to ${step.nextDepartureDelay} minutes, so delay is being recovered.`;
    else if (viewStep.stateKey === "recovered") explanation = language === "zh" ? `下一班只晚 ${step.nextDepartureDelay} 分钟起飞，已经低于 ${threshold} 分钟标准，因此在起飞前记为恢复。` : `The next flight departed ${step.nextDepartureDelay} minutes late, below the ${threshold}-minute threshold, ending the episode before departure.`;
    else if (viewStep.stateKey === "recovered_en_route") explanation = language === "zh" ? `这班飞机起飞时仍超过 ${threshold} 分钟标准，但到达时只晚 ${step.nextArrivalDelay} 分钟，因此记为途中追回。` : `The flight departed above ${threshold} minutes but arrived only ${step.nextArrivalDelay} minutes late, so the episode recovered en route.`;
    else explanation = language === "zh" ? `下一航段以 ${step.nextDepartureDelay} 分钟延误起飞，仍高于 ${threshold} 分钟门槛。` : `The next flight departed ${step.nextDepartureDelay} minutes late, remaining above the ${threshold}-minute threshold.`;
  }

  return <section ref={sectionRef} id="episodes" className="analysis-section episode-explorer section-shell">
    <div className="section-heading"><div><span className="section-number">{t.section}</span><h2>{t.title}</h2></div><p>{t.intro}</p></div>

    <div className="threshold-lab">
      <div className="threshold-lab-copy"><span>{t.lab}</span><strong>{t.threshold}</strong><p>{t.labIntro}</p>
        <div className="threshold-toggle" role="radiogroup" aria-label={t.threshold}>
          {data.availableThresholds.map(value => <button key={value} type="button" role="radio" aria-checked={threshold === value} className={threshold === value ? "is-active" : ""} onClick={() => selectThreshold(value)}><b>{value}</b><small>{t.thresholdNames[value]}</small></button>)}
        </div>
      </div>
      <div className="threshold-national">
        <div className="threshold-metrics"><div><small>{t.episodes}</small><strong>{sensitivity.nEpisodes.toLocaleString(language === "zh" ? "zh-CN" : "en-US")}</strong></div><div><small>{t.deep3}</small><strong>{sensitivity.nDeep3.toLocaleString(language === "zh" ? "zh-CN" : "en-US")}</strong></div><div><small>{t.maxDepth}</small><strong>{sensitivity.maxDepth}</strong></div></div>
        <div className="threshold-volume" aria-label={`${t.episodes}: ${sensitivity.nEpisodes}`}><i style={{ width: `${(sensitivity.nEpisodes / baseline.nEpisodes) * 100}%` }} /></div>
        <p>{comparison}</p>
      </div>
      <details className="clarity-details episode-details">
        <summary>{t.detailsSummary}</summary>
        <div className="clarity-details-inner">
          <div className="threshold-metrics threshold-metrics-extra"><div><small>{t.airports500}</small><strong>{sensitivity.nAirportsExposed500}</strong></div></div>
        </div>
      </details>
    </div>

    <div className="episode-selector" role="list" aria-label={t.why}>
      {data.episodes.map(item => { const itemView = item.thresholdViews[String(threshold)]; return <button type="button" className={`episode-card ${item.episodeId === id ? "is-active" : ""} ${!itemView.qualifies ? "is-unqualified" : ""}`} aria-pressed={item.episodeId === id} onClick={() => selectEpisode(item.episodeId)} key={item.episodeId}>
        <span>{t.categories[item.selectionCategory as keyof typeof t.categories]}</span><strong>{item.airportsTouched.slice(0, 3).join(" → ")}</strong><small>{item.tailNumber} · {itemView.qualifies ? `${t.depth} ${itemView.depth} · ${itemView.outcome === "censored" ? t.censored : t.recovered}` : t.notQualified}</small>
      </button>; })}
    </div>
    <p className="episode-why"><strong>{t.why}：</strong>{t.categories[episode.selectionCategory as keyof typeof t.categories]} · {threshold} min</p>
    {view.qualifies && <p className="episode-count-rule">{fill(view.outcome === "recovered" ? t.recoveredRule : t.censoredRule, { depth: view.depth, observations: view.observationCount })}</p>}
    {view.outcome === "censored" && <p className="episode-censor-note"><strong>{t.censored}：</strong>{t.boundary}</p>}

    {!view.qualifies ? <div className="episode-unqualified"><span>{threshold} MIN</span><div><h3>{t.noEpisodeTitle}</h3><p>{fill(t.noEpisodeBody, { delay: episode.initialArrivalDelay, threshold })}</p></div></div> : <>
      <div className="episode-controls">
        <button type="button" onClick={() => setStep(index - 1)} disabled={!index}>{t.previous}</button>
        <button type="button" aria-label={playing ? t.pause : t.play} disabled={reducedMotion} onClick={() => setPlaying(value => !value)}>{playing ? t.pause : t.play}</button>
        <button type="button" onClick={() => setStep(index + 1)} disabled={index === view.steps.length - 1}>{t.next}</button>
        <button type="button" onClick={() => setStep(0)}>{t.restart}</button>
        <strong>{t.step} {index + 1} / {view.steps.length}</strong>
      </div>
      <div className="episode-tape" aria-label={t.timeline}>
        {view.steps.map((item, itemIndex) => <button type="button" key={`${item.sourceStepIndex}-${item.phase}`} ref={node => { stepRefs.current[itemIndex] = node; }} aria-current={itemIndex === index ? "step" : undefined} aria-label={`${t.step} ${itemIndex + 1}: ${t.states[item.stateKey as keyof typeof t.states] ?? item.stateKey}`} className={`episode-node state-${item.stateKey} ${itemIndex < index ? "is-complete" : ""} ${itemIndex === index ? "is-current" : ""}`} onClick={() => setStep(itemIndex)}>
          <span>{itemIndex + 1}</span><small>{t.states[item.stateKey as keyof typeof t.states] ?? item.stateKey}</small>
        </button>)}
      </div>
      {step && viewStep && <div className="episode-stage"><article className="episode-detail"><span>{t.current} · {state}</span><h3>{viewStep.phase === "arrival" ? <>{airportLabel(step.turnAirport, language)} <i>→</i> {airportLabel(step.nextAirport, language)}</> : <>{airportLabel(step.prevAirport, language)} <i>→</i> {airportLabel(step.turnAirport, language)} {step.nextAirport && <><i>→</i> {airportLabel(step.nextAirport, language)}</>}</>}</h3>
        <div className="episode-flight-line"><b>{flightLabel(viewStep.phase === "arrival" ? step.nextFlight : step.previousFlight)}</b><span>{airlineName(viewStep.phase === "arrival" ? step.nextFlight : step.previousFlight, language)}</span>{viewStep.phase !== "arrival" && step.nextFlight && <><i>→</i><b>{flightLabel(step.nextFlight)}</b><span>{airlineName(step.nextFlight, language)}</span></>}</div>
        <p className="episode-explanation">{explanation}</p>
        <details className="episode-weather-note clarity-details">
          <summary>{t.weatherDetails}</summary>
          <div className="clarity-details-inner">
          <div className="episode-weather-head">
            <div><span>{language === "zh" ? "当前观察点天气" : "Weather at this observation"}</span><small>{viewStep.phase === "arrival" ? (language === "zh" ? "实际到达前报告" : "report before actual arrival") : (language === "zh" ? "计划起飞前报告" : "report before scheduled departure")}</small></div>
            <div className="episode-weather-tolerance" role="radiogroup" aria-label={language === "zh" ? "案例天气报告匹配范围" : "Case weather-report matching window"}>
              {([60, 90] as const).map(value => <button type="button" role="radio" aria-checked={weatherTolerance === value} className={weatherTolerance === value ? "is-active" : ""} key={value} onClick={() => setWeatherTolerance(value)}>{value} min</button>)}
            </div>
          </div>
          <p className="episode-weather-help">{language === "zh" ? "60 / 90 分钟表示：只从当前航班事件发生前这段时间内，寻找最近的天气报告；它不代表观察这场延误 60 或 90 分钟。" : "60 / 90 minutes limits the search to reports issued within that period before this flight event; it is not the length of delay observation."}</p>
          {weatherNote?.available ? <div className="episode-weather-body">
            <div className={`episode-weather-status ${weatherNote.adverse ? "is-adverse" : "is-clear"}`}><strong>{weatherNote.adverse ? (language === "zh" ? "触发恶劣天气条件" : "Candidate adverse") : (language === "zh" ? "未触发恶劣天气条件" : "Non-adverse")}</strong><span>{weatherNote.airport} · {weatherNote.reportType === "METAR_OR_SPECI" ? "METAR/SPECI" : weatherNote.reportType} · {language === "zh" ? `报告早于事件 ${weatherNote.ageMinutes} 分钟` : `${weatherNote.ageMinutes} min before event`}</span></div>
            <div className="episode-weather-values"><span>{language === "zh" ? "能见度" : "Visibility"}<b>{weatherNumber(weatherNote.values?.visibilityKm, "km")}</b></span><span>{language === "zh" ? "云底" : "Ceiling"}<b>{weatherNumber(weatherNote.values?.ceilingFt, "ft")}</b></span><span>{language === "zh" ? "风速" : "Wind"}<b>{weatherNumber(weatherNote.values?.windSpeedMps, "m/s")}</b></span><span>{language === "zh" ? "阵风" : "Gust"}<b>{weatherNumber(weatherNote.values?.windGustMps, "m/s")}</b></span></div>
            <p>{language === "zh" ? "报告 UTC" : "Report UTC"}: {weatherNote.observedUTC} {weatherNote.flags?.length ? ` · ${weatherNote.flags.map(flag => weatherFlag(flag, language)).join(" / ")}` : ` · ${language === "zh" ? "未触发候选天气标签" : "no candidate-weather flag"}`}</p>
          </div> : <div className="episode-weather-unavailable"><strong>unavailable</strong><span>{weatherMissing(weatherNote?.reason, language)} · {weatherTolerance} min</span></div>}
          </div>
        </details>
        <div className="episode-step-metrics"><div><span>{t.arrival}</span><strong>{step.prevArrivalDelay} min</strong></div><div><span>{t.turn}</span><strong>{step.plannedTurnMinutes} / {step.actualTurnMinutes} min</strong></div><div><span>{t.departure}</span><strong>{step.nextDepartureDelay} min</strong></div><div><span>{viewStep.phase === "arrival" ? t.nextArrival : t.delta}</span><strong>{viewStep.phase === "arrival" ? `${step.nextArrivalDelay} min` : `${step.delayDelta > 0 ? "+" : ""}${step.delayDelta} min`}</strong></div></div>
        <p className="episode-time">{t.time} · {utc(step.prevActualArrivalUTC, language)} → {utc(viewStep.phase === "arrival" ? step.nextActualArrivalUTC : step.nextActualDepartureUTC, language)}</p>
      </article><aside className="episode-summary"><span>{t.summary} · {threshold} MIN</span><div className="episode-summary-grid"><div><small>{t.depth}</small><strong>{view.depth}</strong></div><div><small>{t.observed}</small><strong>{view.observationCount}</strong></div><div><small>{t.arrival}</small><strong>{episode.initialArrivalDelay} min</strong></div><div><small>{t.maxDeparture}</small><strong>{view.maxDepartureDelay} min</strong></div><div><small>{t.amplification}</small><strong>+{view.cumulativeAmplificationMinutes} min</strong></div><div><small>{t.duration}</small><strong>{durationText(view.durationMinutes, language)}</strong></div><div><small>{t.airports}</small><strong>{view.uniqueAirportsTouched}</strong></div><div><small>{t.outcome}</small><strong>{view.outcome === "censored" ? t.censored : t.recovered}</strong></div></div>
        <p>{view.outcome === "censored" ? `${t.endings[view.terminationReason as keyof typeof t.endings] ?? t.censored}。${t.boundary}` : `${t.endings[view.terminationReason as keyof typeof t.endings] ?? t.recovered}；${t.finalRecovery}。`}</p>
      </aside></div>}
    </>}
    <p className="mechanism-disclaimer">{t.disclaimer}</p>
  </section>;
}
