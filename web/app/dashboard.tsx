"use client";

import { useMemo, useState, type CSSProperties } from "react";
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

const data = rawData as SiteData;

const sortOptions: Array<{ key: AirportSortKey; label: string }> = [
  { key: "pressureScore", label: "Pressure" },
  { key: "delayRate", label: "Departure delay" },
  { key: "propagationRate", label: "Propagation" },
  { key: "flights", label: "Volume" },
  { key: "cancelRate", label: "Cancellation" },
];

const storyLabels: Record<string, string> = {
  cascade: "Cascade",
  recovery: "Recovery",
  "tight-turn": "Tight turn",
  mixed: "Mixed",
};

function percent(value: number, digits = 1) {
  return `${(value * 100).toFixed(digits)}%`;
}

function integer(value: number) {
  return new Intl.NumberFormat("en-US").format(value);
}

function delayLabel(value: number | null) {
  if (value === null) return "—";
  if (value === 0) return "on time";
  return `${value > 0 ? "+" : ""}${Math.round(value)}m`;
}

function barStyle(value: number, max: number): CSSProperties {
  return { "--value": `${Math.max(4, (value / max) * 100)}%` } as CSSProperties;
}

export default function Dashboard() {
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

  return (
    <main id="top">
      <a className="skip-link" href="#pressure-board">
        Skip to analysis
      </a>

      <header className="site-header">
        <a className="wordmark" href="#top" aria-label="Airports Under Stress home">
          <span className="wordmark-signal" aria-hidden="true" />
          <span>AUS / LAB</span>
        </a>
        <nav aria-label="Primary navigation">
          <a href="#pressure-board">Airports</a>
          <a href="#carriers">Carriers</a>
          <a href="#rotations">Rotations</a>
          <a href="#method">Method</a>
        </nav>
        <div className="edition-badge">
          <span>V0</span>
          <span>{data.meta.period}</span>
        </div>
      </header>

      <section className="hero section-shell" aria-labelledby="hero-title">
        <div className="hero-copy">
          <div className="eyebrow">
            <span className="live-dot" />
            U.S. AVIATION NETWORK / RETROSPECTIVE
          </div>
          <h1 id="hero-title">
            <span>Airports</span>
            <span className="outlined">Under Stress</span>
          </h1>
          <p className="hero-deck">
            一架飞机晚到之后，延误会继续传递，还是被下一段航班吸收？我们用真实机尾号重建
            <strong> 549,388 </strong>条轮转关系，观察美国航空网络的压力与恢复。
          </p>
          <div className="hero-actions">
            <a className="primary-action" href="#pressure-board">
              Explore the network <span aria-hidden="true">↘</span>
            </a>
            <a className="text-action" href="#method">
              Read the research boundary
            </a>
          </div>
        </div>

        <div className="pulse-panel" aria-label="Daily departure delay rate in May 2026">
          <div className="panel-topline">
            <div>
              <span className="panel-kicker">NETWORK PULSE</span>
              <h2>Daily departure pressure</h2>
            </div>
            <div className="peak-readout">
              <span>Peak / May {peakPoint.day}</span>
              <strong>{percent(peakPoint.delayRate)}</strong>
            </div>
          </div>
          <div className="pulse-chart">
            <div className="pulse-baseline" aria-hidden="true">
              <span>MONTH {percent(data.national.delayRate)}</span>
            </div>
            {data.daily.map((point) => (
              <div
                className={`pulse-column ${point.date === data.national.peakDay ? "is-peak" : ""}`}
                key={point.date}
                title={`May ${point.day}: ${percent(point.delayRate)} delayed`}
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
              <i className="legend-mark legend-delay" /> Delayed ≥ 15 min
            </span>
            <span>
              <i className="legend-mark legend-peak" /> Peak day
            </span>
            <span>611,735 reported flights</span>
          </div>
        </div>
      </section>

      <section className="metric-ribbon section-shell" aria-label="National summary">
        <article>
          <span className="metric-index">01</span>
          <strong>{percent(data.national.delayRate)}</strong>
          <p>departures delayed 15+ min</p>
        </article>
        <article>
          <span className="metric-index">02</span>
          <strong>{percent(data.national.propagationRate)}</strong>
          <p>upstream delays propagated</p>
        </article>
        <article>
          <span className="metric-index">03</span>
          <strong>{percent(data.national.recoveryRate)}</strong>
          <p>upstream delays absorbed</p>
        </article>
        <article>
          <span className="metric-index">04</span>
          <strong>{integer(data.meta.tails)}</strong>
          <p>unique aircraft observed</p>
        </article>
      </section>

      <section className="analysis-section section-shell" id="pressure-board">
        <div className="section-heading">
          <div>
            <span className="section-number">01 / AIRPORT PRESSURE BOARD</span>
            <h2>Where the network felt tight.</h2>
          </div>
          <p>
            只比较月出发量至少 1,000 班、有效轮转链至少 500 条的机场。压力指数由延误率、
            取消率和传播率的样本内百分位构成。
          </p>
        </div>

        <div className="sort-rail" aria-label="Sort airports">
          <span>RANK BY</span>
          <div>
            {sortOptions.map((option) => (
              <button
                type="button"
                key={option.key}
                className={airportSort === option.key ? "active" : ""}
                aria-pressed={airportSort === option.key}
                onClick={() => setAirportSort(option.key)}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        <div className="airport-layout">
          <div className="airport-table" role="list" aria-label="Ranked airports">
            <div className="airport-table-head" aria-hidden="true">
              <span>Rank / airport</span>
              <span>relative signal</span>
              <span>delay</span>
              <span>propagation</span>
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
                  aria-label={`${airport.code}, ${airport.city}: ${percent(airport.delayRate)} delayed`}
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
                <span>SELECTED AIRPORT</span>
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
                <span>Flights</span>
                <strong>{integer(selectedAirport.flights)}</strong>
              </div>
              <div>
                <span>Avg. dep delay</span>
                <strong>{selectedAirport.avgDelay.toFixed(1)}m</strong>
              </div>
              <div>
                <span>90th percentile</span>
                <strong>{selectedAirport.p90Delay.toFixed(0)}m</strong>
              </div>
              <div>
                <span>Cancellation</span>
                <strong>{percent(selectedAirport.cancelRate)}</strong>
              </div>
            </div>
            <div className="absorption-block">
              <div className="absorption-label">
                <span>After an inbound delay</span>
                <span>{integer(selectedAirport.chainLinks)} links</span>
              </div>
              <div className="split-meter" aria-label="Propagation versus recovery rate">
                <span style={{ width: percent(selectedAirport.propagationRate, 2) }} />
                <i style={{ width: percent(selectedAirport.recoveryRate, 2) }} />
              </div>
              <div className="split-values">
                <span>
                  <strong>{percent(selectedAirport.propagationRate)}</strong> propagated
                </span>
                <span>
                  <strong>{percent(selectedAirport.recoveryRate)}</strong> recovered
                </span>
              </div>
            </div>
            <p className="focus-note">
              Pressure score is relative within eligible airports; it is not a safety rating or causal claim.
            </p>
          </aside>
        </div>
      </section>

      <section className="analysis-section carrier-section section-shell" id="carriers">
        <div className="section-heading compact-heading">
          <div>
            <span className="section-number">02 / CARRIER COMPARISON</span>
            <h2>Scale is not resilience.</h2>
          </div>
          <p>
            每家航司面临不同的航线结构和运营约束。这里展示描述性差异，不把排名解释成运营能力的因果结论。
          </p>
        </div>
        <div className="carrier-grid">
          {data.airlines.map((airline, index) => (
            <article className="carrier-card" key={airline.code}>
              <div className="carrier-topline">
                <span>{String(index + 1).padStart(2, "0")}</span>
                <span>{integer(airline.flights)} flights</span>
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
                  delay
                </span>
                <span>
                  <strong>{percent(airline.propagationRate)}</strong>
                  propagate
                </span>
                <span>
                  <strong>{percent(airline.recoveryRate)}</strong>
                  recover
                </span>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="analysis-section rotation-section section-shell" id="rotations">
        <div className="section-heading rotation-heading">
          <div>
            <span className="section-number">03 / AIRCRAFT ROTATION STORIES</span>
            <h2>Follow the aircraft, not just the flight.</h2>
          </div>
          <p>
            每个故事来自同一机尾号的连续真实航段。状态用 15 分钟阈值描述传播或恢复，时间统一显示为 UTC。
          </p>
        </div>

        <div className="story-switcher" aria-label="Choose aircraft rotation story">
          {data.stories.map((story, index) => (
            <button
              type="button"
              key={story.id}
              className={story.id === activeStory.id ? "active" : ""}
              aria-pressed={story.id === activeStory.id}
              onClick={() => setActiveStoryId(story.id)}
            >
              <span>{String(index + 1).padStart(2, "0")}</span>
              <strong>{storyLabels[story.type]}</strong>
              <small>{story.tail}</small>
            </button>
          ))}
        </div>

        <div className="story-stage" aria-live="polite">
          <div className="story-intro">
            <span className={`story-type type-${activeStory.type}`}>{storyLabels[activeStory.type]}</span>
            <h3>{activeStory.title}</h3>
            <p>{activeStory.summary}</p>
            <dl>
              <div>
                <dt>Tail</dt>
                <dd>{activeStory.tail}</dd>
              </div>
              <div>
                <dt>Date</dt>
                <dd>{activeStory.date}</dd>
              </div>
              <div>
                <dt>Chain</dt>
                <dd>{activeStory.legs.length} legs</dd>
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
                      DEP <strong>{delayLabel(leg.depDelay)}</strong>
                    </span>
                    <span>
                      ARR <strong>{delayLabel(leg.arrDelay)}</strong>
                    </span>
                  </div>
                  <span className="leg-status">{leg.status.replace("-", " ")}</span>
                </div>
                {index < activeStory.legs.length - 1 && (
                  <div className="turn-label">
                    {activeStory.legs[index + 1].turn
                      ? `${activeStory.legs[index + 1].turn}m turn`
                      : "next leg"}
                  </div>
                )}
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="method-section section-shell" id="method">
        <div className="method-title">
          <span className="section-number">04 / METHOD & BOUNDARY</span>
          <h2>Evidence first.<br />Claims second.</h2>
        </div>
        <div className="method-grid">
          <article>
            <span>01</span>
            <h3>One UTC timeline</h3>
            <p>
              所有本地 HHMM 时间先结合机场时区转成 UTC；1,167 条记录若按本地时钟排序会得到不同顺序。
            </p>
          </article>
          <article>
            <span>02</span>
            <h3>Physical continuity</h3>
            <p>
              只连接机尾号相同、上一站终点等于下一站起点、且周转时间物理可行的航段。79 条负周转候选已排除。
            </p>
          </article>
          <article>
            <span>03</span>
            <h3>Not a causal claim</h3>
            <p>
              “传播”表示相邻两段都超过 15 分钟，并不单独证明前一段造成后一段；天气和机场拥堵将在后续版本控制。
            </p>
          </article>
        </div>
        <div className="integrity-strip">
          <span>DATA INTEGRITY</span>
          <div>
            <strong>100.0000%</strong>
            <small>operated-flight tail coverage</small>
          </div>
          <div>
            <strong>99.9982%</strong>
            <small>scheduled-clock agreement</small>
          </div>
          <div>
            <strong>98.78%</strong>
            <small>airport continuity</small>
          </div>
          <div>
            <strong>0</strong>
            <small>candidate-key duplicates</small>
          </div>
        </div>
      </section>

      <footer className="site-footer section-shell">
        <div>
          <span className="wordmark-signal" aria-hidden="true" />
          <strong>Airports Under Stress</strong>
          <p>Delay propagation & network resilience lab.</p>
        </div>
        <div className="footer-meta">
          <p>
            Source: U.S. DOT Bureau of Transportation Statistics,<br />Reporting Carrier On-Time Performance.
          </p>
          <a
            href="https://www.transtats.bts.gov/TableInfo.asp?QO_fu146_anzr=b0-gvzr&gnoyr_VQ=FGJ"
            target="_blank"
            rel="noreferrer"
          >
            Official data ↗
          </a>
        </div>
        <div className="footer-edition">
          <span>V0 / DESCRIPTIVE PRODUCT</span>
          <span>2026</span>
        </div>
      </footer>
    </main>
  );
}

