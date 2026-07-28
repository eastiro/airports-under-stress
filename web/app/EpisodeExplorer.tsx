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
    section: "06 / 连续延误案例", title: "同一架飞机，延误状态能延续多久？",
    intro: "案例跟随同一机尾号上的连续延误状态，不把整条链解释为同一原因造成。每个 episode 最长观察 18 小时，计划停场超过 180 分钟即中断；再用 15、30、60 分钟三种门槛检查结论是否稳定。",
    lab: "定义敏感性实验室", labIntro: "15 分钟是主分析基线；30 与 60 分钟检查延误门槛。180 分钟停场与 18 小时总时长是所有档位共同使用的连续运营边界。", threshold: "延误门槛",
    thresholdNames: { 15: "标准", 30: "严格", 60: "极端" },
    episodes: "全国 episodes", deep3: "深度 ≥3", maxDepth: "最大深度", airports500: "暴露 ≥500 的机场",
    baseline: "主分析基线：观察达到 15 分钟的连续晚点状态。",
    comparison30: "相较 15 分钟，episode 减少 {episodes}，深度 ≥3 减少 {deep}; 链路排序仍较稳定（Spearman 0.896，Top 20 重合 20/20）。",
    comparison60: "相较 15 分钟，episode 减少 {episodes}，深度 ≥3 减少 {deep}; Top 20 仅重合 3/20，极端门槛明显改变了观察对象。",
    play: "播放", pause: "暂停", previous: "上一个观察点", next: "下一个观察点", restart: "重新开始", step: "观察点", timeline: "观察序列", current: "当前观察", why: "为何值得看", summary: "Episode 总结",
    recoveredRule: "当前门槛下：{depth} 个仍达到门槛的传播航段 + 1 个恢复判定 = {observations} 个观察点。最后的恢复判定不计入传播深度。",
    censoredRule: "当前门槛下已观察到 {depth} 个仍达到门槛的传播航段；记录在恢复出现前中断，因此共有 {observations} 个观察点。",
    arrival: "上一航段到达延误", departure: "下一航段起飞延误", nextArrival: "下一航段到达延误", delta: "延误变化", turn: "计划 / 实际周转", time: "观察时刻", depth: "连续深度", observed: "观察点数量", maxDeparture: "最大起飞延误", amplification: "累计放大", duration: "持续时间", airports: "经过机场", outcome: "最终结局", recovered: "已恢复", censored: "观察中断", notQualified: "不构成 episode", finalRecovery: "含最终恢复观察点", boundary: "观察可能因长停场、18 小时时长上限、链断裂或样本结束而停止，不能据此判断之后是否恢复。", disclaimer: "所有时间为 UTC。这里只描述同一机尾号上的连续延误状态，不声称它们由最初一次延误造成；天气、空管与机场拥堵尚未控制。",
    noEpisodeTitle: "这条冲击在当前门槛下不会开始。", noEpisodeBody: "案例起始到达延误为 {delay} 分钟，低于 {threshold} 分钟门槛，因此不构成该定义下的 episode。原始航班记录没有消失，只是分类发生变化。",
    categories: { deepest: "最深延续", high_delay_recovered: "大延误后恢复", high_pressure_day: "高压力日", normal_day: "普通日", crosses_midnight: "跨 UTC 午夜", censored: "观察中断" },
    states: { propagated: "延误继续传递", amplified: "延误正在放大", caught_up: "延误正在追回", recovered: "起飞前恢复", recovered_en_route: "在途恢复" },
    endings: { recovered: "在下一次起飞前恢复", recovered_en_route: "该延误航段在途中恢复", scheduled_turn_break: "计划停场超过 180 分钟，连续观察在此结束", duration_limit: "达到 18 小时观察上限", airport_discontinuity: "飞机轮转链在此断开", end_of_sequence: "样本记录在此结束", initial_delay_below_threshold: "起始延误未达到当前门槛" },
  },
  en: {
    section: "06 / Continuous-delay cases", title: "How long does a late state persist on one aircraft?",
    intro: "Cases follow a continuous late state on one tail; they do not attribute the whole chain to one cause. Episodes are observed for at most 18 hours and stop at planned turns over 180 minutes, then are reclassified at 15, 30, and 60 minutes.",
    lab: "Definition sensitivity lab", labIntro: "15 minutes is the primary delay baseline; 30 and 60 test threshold sensitivity. Every view shares the 180-minute planned-turn and 18-hour continuity limits.", threshold: "Delay threshold",
    thresholdNames: { 15: "Standard", 30: "Strict", 60: "Extreme" },
    episodes: "National episodes", deep3: "Depth ≥3", maxDepth: "Maximum depth", airports500: "Airports with ≥500 exposures",
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

export default function EpisodeExplorer({ language, data }: { language: Language; data: V1BData }) {
  const t = copy[language];
  const defaultEpisode = [...data.episodes].sort((a, b) => b.depth - a.depth || a.episodeId.localeCompare(b.episodeId))[0];
  const [id, setId] = useState(defaultEpisode.episodeId);
  const [threshold, setThreshold] = useState<Threshold>(15);
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
    stepRefs.current[index]?.scrollIntoView({ inline: "center", block: "nearest", behavior: reducedMotion ? "auto" : "smooth" });
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
    else if (viewStep.stateKey === "recovered") explanation = language === "zh" ? `下一航段以 ${step.nextDepartureDelay} 分钟延误起飞，已低于 ${threshold} 分钟门槛，episode 在起飞前结束。` : `The next flight departed ${step.nextDepartureDelay} minutes late, below the ${threshold}-minute threshold, ending the episode before departure.`;
    else if (viewStep.stateKey === "recovered_en_route") explanation = language === "zh" ? `该航段起飞时仍超过 ${threshold} 分钟门槛，但到达延误降至 ${step.nextArrivalDelay} 分钟，episode 在途中恢复。` : `The flight departed above ${threshold} minutes but arrived only ${step.nextArrivalDelay} minutes late, so the episode recovered en route.`;
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
        <div className="threshold-metrics"><div><small>{t.episodes}</small><strong>{sensitivity.nEpisodes.toLocaleString(language === "zh" ? "zh-CN" : "en-US")}</strong></div><div><small>{t.deep3}</small><strong>{sensitivity.nDeep3.toLocaleString(language === "zh" ? "zh-CN" : "en-US")}</strong></div><div><small>{t.maxDepth}</small><strong>{sensitivity.maxDepth}</strong></div><div><small>{t.airports500}</small><strong>{sensitivity.nAirportsExposed500}</strong></div></div>
        <div className="threshold-volume" aria-label={`${t.episodes}: ${sensitivity.nEpisodes}`}><i style={{ width: `${(sensitivity.nEpisodes / baseline.nEpisodes) * 100}%` }} /></div>
        <p>{comparison}</p>
      </div>
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
        <div className="episode-step-metrics"><div><span>{t.arrival}</span><strong>{step.prevArrivalDelay} min</strong></div><div><span>{t.turn}</span><strong>{step.plannedTurnMinutes} / {step.actualTurnMinutes} min</strong></div><div><span>{t.departure}</span><strong>{step.nextDepartureDelay} min</strong></div><div><span>{viewStep.phase === "arrival" ? t.nextArrival : t.delta}</span><strong>{viewStep.phase === "arrival" ? `${step.nextArrivalDelay} min` : `${step.delayDelta > 0 ? "+" : ""}${step.delayDelta} min`}</strong></div></div>
        <p className="episode-time">{t.time} · {utc(step.prevActualArrivalUTC, language)} → {utc(viewStep.phase === "arrival" ? step.nextActualArrivalUTC : step.nextActualDepartureUTC, language)}</p>
      </article><aside className="episode-summary"><span>{t.summary} · {threshold} MIN</span><div className="episode-summary-grid"><div><small>{t.depth}</small><strong>{view.depth}</strong></div><div><small>{t.observed}</small><strong>{view.observationCount}</strong></div><div><small>{t.arrival}</small><strong>{episode.initialArrivalDelay} min</strong></div><div><small>{t.maxDeparture}</small><strong>{view.maxDepartureDelay} min</strong></div><div><small>{t.amplification}</small><strong>+{view.cumulativeAmplificationMinutes} min</strong></div><div><small>{t.duration}</small><strong>{durationText(view.durationMinutes, language)}</strong></div><div><small>{t.airports}</small><strong>{view.uniqueAirportsTouched}</strong></div><div><small>{t.outcome}</small><strong>{view.outcome === "censored" ? t.censored : t.recovered}</strong></div></div>
        <p>{view.outcome === "censored" ? `${t.endings[view.terminationReason as keyof typeof t.endings] ?? t.censored}。${t.boundary}` : `${t.endings[view.terminationReason as keyof typeof t.endings] ?? t.recovered}；${t.finalRecovery}。`}</p>
      </aside></div>}
    </>}
    <p className="mechanism-disclaimer">{t.disclaimer}</p>
  </section>;
}
