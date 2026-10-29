"use client";

import { useEffect, useMemo, useRef, useState, type ChangeEvent } from "react";
import { AIRPORT_COORDINATES, type AirportCoordinate } from "./airport-coordinates";
import { US_BOUNDARY } from "./us-boundary";
import { AIRPORT_ZH } from "./airport-names-zh";

type Language = "zh" | "en";
type DailyPoint = {
  date: string;
  day: number;
  flights: number;
  delayRate: number;
  cancelRate: number;
  avgDelay: number;
  propagationRate: number;
};
type Airport = {
  code: string;
  name: string;
  city: string;
  region: string;
  delayRate: number;
  propagationRate: number;
  pressureScore: number;
};
type Route = { origin: string; dest: string; flights: number; delayRate: number };
type StoryLeg = { origin: string; dest: string; status: string; arrDelay: number };
type Story = { id: string; type: string; legs: StoryLeg[] };
type SiteData = {
  meta: { chainLinks: number; mapAirports: number };
  national: { delayRate: number; cancelRate: number; propagationRate: number };
  daily: DailyPoint[];
  mapAirportCodes: string[];
  airports: Airport[];
  network: { routes: Route[] };
  stories: Story[];
};

type Props = { language: Language; data: SiteData };
type Point = [number, number];

const MAP_BOUNDS = { west: -125, east: -66, south: 24, north: 50, padX: 0.05, padY: 0.07 } as const;

const MAP_ONLY_EN: Record<string, { name: string; city: string; region: string }> = {
  CRW: { name: "West Virginia International Yeager Airport", city: "Charleston", region: "West Virginia" },
  DEC: { name: "Decatur Airport", city: "Decatur", region: "Illinois" },
  DLH: { name: "Duluth International Airport", city: "Duluth", region: "Minnesota" },
  SBN: { name: "South Bend International Airport", city: "South Bend", region: "Indiana" },
};

// One equirectangular projection for the continental U.S. viewport, shared by
// the airport nodes and the boundary outline so they stay aligned.
function projectLonLat(longitude: number, latitude: number): Point {
  const xRatio = (longitude - MAP_BOUNDS.west) / (MAP_BOUNDS.east - MAP_BOUNDS.west);
  const yRatio = (MAP_BOUNDS.north - latitude) / (MAP_BOUNDS.north - MAP_BOUNDS.south);
  return [
    MAP_BOUNDS.padX + xRatio * (1 - MAP_BOUNDS.padX * 2),
    MAP_BOUNDS.padY + yRatio * (1 - MAP_BOUNDS.padY * 2),
  ];
}
function projectCoord({ latitude, longitude }: AirportCoordinate): Point {
  return projectLonLat(longitude, latitude);
}
function pct(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}
function legColor(arrDelay: number) {
  if (arrDelay >= 60) return "#ff6b5f";
  if (arrDelay >= 15) return "#ffbc52";
  return "#5fd4b4";
}
function hexWithAlpha(hex: string, alpha: number) {
  const a = Math.max(0, Math.min(255, Math.round(alpha * 255)))
    .toString(16)
    .padStart(2, "0");
  return `${hex}${a}`;
}

export default function NetworkHero({ language, data }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const frameRef = useRef<number | null>(null);
  const nodeScreenRef = useRef<{ code: string; x: number; y: number; r: number; clusterCodes?: string[] }[]>([]);
  const clusterButtonRefs = useRef(new Map<string, HTMLButtonElement>());
  const pendingClusterFocus = useRef<string | null>(null);
  const [dayIndex, setDayIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [hovered, setHovered] = useState<string | null>(null);
  const [pinned, setPinned] = useState<string | null>(null);
  const [selectedCode, setSelectedCode] = useState<string | null>(null);
  const [a11yOpen, setA11yOpen] = useState(false);
  const [metric, setMetric] = useState<"delayRate" | "cancelRate" | "propagationRate">("delayRate");

  const point = data.daily[dayIndex] ?? data.daily[0];

  const labels = language === "zh"
    ? {
        eyebrow: "美国航空网络 / 网络现场",
        title: ["压力正在", "网络中呼吸"],
        deck: "我们用真实机尾号重建",
        links: "条轮转关系，观察延误如何传递，又在哪里被吸收。",
        explore: "进入机场压力榜",
        boundary: "查看研究边界",
        signal: "代表性轮转链路",
        network: "月度航线底网",
        national: "全国每日压力",
        delay: "起飞延误",
        cancel: "取消率",
        propagation: "传播率",
        pause: "暂停日期播放",
        play: "播放日期",
        motionOff: "系统已启用减少动态效果，日期自动播放不可用",
        select: "选择 2026 年 5 月日期",
        note: "全国每日指标驱动网络强度；航线仅展示数据中真实存在的轮转航段，不是全美实时航班轨迹。",
        node: "机场节点",
        levelLow: "低",
        levelMed: "中",
        levelHigh: "高",
        levelLabel: "全国压力等级",
        trend: "31 日走势",
        metricDelay: "起飞延误率",
        metricCancel: "取消率",
        metricPropagation: "传播率",
        metricLegend: "更大的节点 / 更强的光晕 = 当前全国指标更高",
      }
    : {
        eyebrow: "U.S. aviation network / live field",
        title: ["Pressure is", "breathing"],
        deck: "We reconstructed",
        links: "real rotation links to watch where delay moves — and where it gets absorbed.",
        explore: "Open airport board",
        boundary: "Read the research boundary",
        signal: "Representative rotation links",
        network: "Monthly route base network",
        national: "National daily pressure",
        delay: "Departure delay",
        cancel: "Cancellation",
        propagation: "Propagation",
        pause: "Pause date playback",
        play: "Play dates",
        motionOff: "Reduced motion is enabled; date autoplay is unavailable",
        select: "Select a date in May 2026",
        note: "National daily metrics drive network intensity; arcs show only real rotation legs, not live tracking of every U.S. flight.",
        node: "Airport node",
        levelLow: "Low",
        levelMed: "Med",
        levelHigh: "High",
        levelLabel: "National pressure level",
        trend: "31-day trend",
        metricDelay: "Dep. delay rate",
        metricCancel: "Cancel rate",
        metricPropagation: "Propagation rate",
        metricLegend: "Larger nodes / stronger glow = higher national metric",
      };

  // Unified node set from map codes + route endpoints + story airports.
  const nodes = useMemo(() => {
    const byCode = new Map<string, { code: string; coord: Point; pressureScore: number; delayRate: number; city: string; priority: number }>();
    const allAirports = new Map(data.airports.map((a) => [a.code, a]));
    for (const code of data.mapAirportCodes) {
      const coord = AIRPORT_COORDINATES[code];
      if (!coord) continue;
      const ap = allAirports.get(code);
      byCode.set(code, {
        code,
        coord: projectCoord(coord),
        pressureScore: ap?.pressureScore ?? 0,
        delayRate: ap?.delayRate ?? 0,
        city: ap?.city ?? code,
        priority: 1000 + (ap?.pressureScore ?? 0),
      });
    }
    for (const route of data.network.routes) {
      for (const code of [route.origin, route.dest]) {
        if (byCode.has(code)) continue;
        const coord = AIRPORT_COORDINATES[code];
        if (!coord) continue;
        byCode.set(code, { code, coord: projectCoord(coord), pressureScore: 0, delayRate: 0, city: code, priority: 400 + route.flights / 100 });
      }
    }
    for (const story of data.stories) {
      for (const leg of story.legs) {
        for (const code of [leg.origin, leg.dest]) {
          if (byCode.has(code)) continue;
          const coord = AIRPORT_COORDINATES[code];
          if (!coord) continue;
          byCode.set(code, { code, coord: projectCoord(coord), pressureScore: 0, delayRate: 0, city: code, priority: 300 });
        }
      }
    }
    return Array.from(byCode.values());
  }, [data.mapAirportCodes, data.airports, data.network.routes, data.stories]);

  const baseArcs = useMemo(
    () =>
      data.network.routes.flatMap((route) => {
        const a = AIRPORT_COORDINATES[route.origin];
        const b = AIRPORT_COORDINATES[route.dest];
        return a && b ? [{ from: projectCoord(a), to: projectCoord(b), delayRate: route.delayRate }] : [];
      }),
    [data.network.routes],
  );

  const storyArcs = useMemo(
    () =>
      data.stories.flatMap((story) =>
        story.legs.flatMap((leg) => {
          const a = AIRPORT_COORDINATES[leg.origin];
          const b = AIRPORT_COORDINATES[leg.dest];
          return a && b ? [{ from: projectCoord(a), to: projectCoord(b), color: legColor(leg.arrDelay) }] : [];
        }),
      ),
    [data.stories],
  );

  const metricRate = point[metric];
  const { minRate, maxRate, levelThreshold } = useMemo(() => {
    const rates = data.daily.map((d) => d[metric]);
    const min = Math.min(...rates);
    const max = Math.max(...rates);
    const sorted = [...rates].sort((x, y) => x - y);
    const q = (p: number) => sorted[Math.min(sorted.length - 1, Math.floor(p * (sorted.length - 1)))];
    return { minRate: min, maxRate: max, levelThreshold: { low: q(0.34), high: q(0.67) } };
  }, [data.daily, metric]);

  const intensity = useMemo(() => {
    if (maxRate <= minRate) return 0.5;
    return (metricRate - minRate) / (maxRate - minRate);
  }, [metricRate, minRate, maxRate]);

  const levelLabel =
    intensity >= (levelThreshold.high - minRate) / (maxRate - minRate || 1)
      ? labels.levelHigh
      : intensity >= (levelThreshold.low - minRate) / (maxRate - minRate || 1)
        ? labels.levelMed
        : labels.levelLow;

  const metricLabel = metric === "delayRate" ? labels.metricDelay : metric === "cancelRate" ? labels.metricCancel : labels.metricPropagation;

  useEffect(() => {
    stateRef.current.dayIndex = dayIndex;
    stateRef.current.playing = playing;
  }, [dayIndex, playing]);
  const stateRef = useRef({ dayIndex: 0, playing: false, reduced: false });
  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => {
      stateRef.current.reduced = media.matches;
      setReducedMotion(media.matches);
      if (media.matches) setPlaying(false);
    };
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  useEffect(() => {
    if (!playing || reducedMotion) return;
    const timer = window.setInterval(
      () => setDayIndex((current) => (current + 1) % data.daily.length),
      1800,
    );
    return () => window.clearInterval(timer);
  }, [playing, reducedMotion, data.daily.length]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const context = canvas.getContext("2d");
    if (!context) return;
    let visible = document.visibilityState !== "hidden";

    const draw = (time: number) => {
      if (!visible) {
        frameRef.current = null;
        return;
      }
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const width = Math.max(1, rect.width);
      const height = Math.max(1, rect.height);
      if (canvas.width !== Math.floor(width * dpr) || canvas.height !== Math.floor(height * dpr)) {
        canvas.width = Math.floor(width * dpr);
        canvas.height = Math.floor(height * dpr);
      }
      context.setTransform(dpr, 0, 0, dpr, 0, 0);
      context.clearRect(0, 0, width, height);
      context.fillStyle = "#071113";
      context.fillRect(0, 0, width, height);

      // Background energy scales with the selected day's pressure.
      const glow = context.createRadialGradient(
        width * 0.5,
        height * 0.42,
        0,
        width * 0.5,
        height * 0.42,
        Math.max(width, height) * 0.7,
      );
      glow.addColorStop(0, hexWithAlpha("#5fd4b4", 0.05 + intensity * 0.1));
      glow.addColorStop(1, "rgba(7,17,19,0)");
      context.fillStyle = glow;
      context.fillRect(0, 0, width, height);

      const map = (p: Point) => [p[0] * width, p[1] * height] as const;

      // Continental U.S. boundary outline, same projection as nodes.
      context.strokeStyle = "rgba(95,212,180,0.22)";
      context.lineWidth = 1;
      for (const ring of US_BOUNDARY) {
        context.beginPath();
        ring.forEach(([lon, lat], i) => {
          const [x, y] = map(projectLonLat(lon, lat));
          if (i === 0) context.moveTo(x, y);
          else context.lineTo(x, y);
        });
        context.closePath();
        context.stroke();
      }

      // Base monthly route network (low brightness).
      const baseAlpha = 0.1 + intensity * 0.12;
      for (const arc of baseArcs) {
        const [x1, y1] = map(arc.from);
        const [x2, y2] = map(arc.to);
        const cx = (x1 + x2) / 2;
        const cy = Math.min(y1, y2) - Math.max(18, Math.abs(x2 - x1) * 0.18);
        context.strokeStyle = hexWithAlpha("#5fd4b4", baseAlpha);
        context.lineWidth = 1;
        context.beginPath();
        context.moveTo(x1, y1);
        context.quadraticCurveTo(cx, cy, x2, y2);
        context.stroke();
        const progress = stateRef.current.reduced ? 0.5 : (time / 3200) % 1;
        const inv = 1 - progress;
        const px = inv * inv * x1 + 2 * inv * progress * cx + progress * progress * x2;
        const py = inv * inv * y1 + 2 * inv * progress * cy + progress * progress * y2;
        context.fillStyle = hexWithAlpha("#5fd4b4", 0.5 + intensity * 0.3);
        context.beginPath();
        context.arc(px, py, 1.4, 0, Math.PI * 2);
        context.fill();
      }

      // Story highlight layer (colored, brighter).
      for (const arc of storyArcs) {
        const [x1, y1] = map(arc.from);
        const [x2, y2] = map(arc.to);
        const cx = (x1 + x2) / 2 - (y2 - y1) * 0.12;
        const cy = (y1 + y2) / 2 + (x2 - x1) * 0.12;
        context.strokeStyle = hexWithAlpha(arc.color, 0.55 + intensity * 0.3);
        context.lineWidth = 1.8;
        context.beginPath();
        context.moveTo(x1, y1);
        context.quadraticCurveTo(cx, cy, x2, y2);
        context.stroke();
        const progress = stateRef.current.reduced ? 0.46 : ((time / 1700) % 1);
        const inv = 1 - progress;
        const px = inv * inv * x1 + 2 * inv * progress * cx + progress * progress * x2;
        const py = inv * inv * y1 + 2 * inv * progress * cy + progress * progress * y2;
        context.fillStyle = arc.color;
        context.shadowColor = arc.color;
        context.shadowBlur = stateRef.current.reduced ? 0 : 8;
        context.beginPath();
        context.arc(px, py, 2.4, 0, Math.PI * 2);
        context.fill();
        context.shadowBlur = 0;
      }

      // Nodes: screen projection → cluster → draw.
      const isMobile = window.innerWidth < 600;
      const maxLabels = isMobile ? 6 : 12;
      const labelGap = 22;
      const clusterDist = 20;

      interface ScreenNode { code: string; x: number; y: number; r: number; priority: number; city: string; delayRate: number; pressureScore: number; }
      const screenNodes: ScreenNode[] = nodes
        .map((node) => {
          const [x, y] = map(node.coord);
          const pulse = stateRef.current.reduced
            ? 1
            : 1 + Math.sin(time / 600 + node.priority) * (0.06 + node.pressureScore / 1400) * (0.6 + intensity * 0.6);
          const radius = (2.6 + node.pressureScore / 32) * (0.85 + intensity * 0.3) * pulse;
          return { code: node.code, x, y, r: radius, priority: node.priority, city: node.city, delayRate: node.delayRate, pressureScore: node.pressureScore };
        })
        .sort((a, b) => b.priority - a.priority);

      interface ClusterEnt { codes: string[]; x: number; y: number; r: number; priority: number; delayRate: number; pressureScore: number; }
      const clusters: ClusterEnt[] = [];
      for (const sn of screenNodes) {
        let merged = false;
        for (const c of clusters) {
          if (Math.hypot(c.x - sn.x, c.y - sn.y) < clusterDist) {
            c.codes.push(sn.code);
            const members = c.codes.map((code) => screenNodes.find((n) => n.code === code)!).filter(Boolean);
            c.x = members.reduce((s, m) => s + m.x, 0) / members.length;
            c.y = members.reduce((s, m) => s + m.y, 0) / members.length;
            c.priority = Math.max(c.priority, sn.priority);
            c.delayRate = members.reduce((s, m) => s + m.delayRate, 0) / members.length;
            c.pressureScore = members.reduce((s, m) => s + m.pressureScore, 0) / members.length;
            c.r = Math.max(4.2, 3.4 + Math.sqrt(members.length) * 1.7);
            merged = true;
            break;
          }
        }
        if (!merged) {
          clusters.push({ codes: [sn.code], x: sn.x, y: sn.y, r: sn.r, priority: sn.priority, delayRate: sn.delayRate, pressureScore: sn.pressureScore });
        }
      }

      const haloAlpha = 0.18 + intensity * 0.5;
      const placed: { code: string; x: number; y: number }[] = [];
      nodeScreenRef.current = [];

      for (const cl of clusters) {
        const isMulti = cl.codes.length > 1;
        const pulse = stateRef.current.reduced
          ? 1
          : 1 + Math.sin(time / 600 + cl.priority) * (0.04 + cl.pressureScore / 1800) * (0.6 + intensity * 0.6);
        const drawR = cl.r * (0.85 + intensity * 0.3) * pulse;
        const color = cl.pressureScore > 70 ? "#ffbc52" : "#5fd4b4";

        // Halo stroke — uses haloAlpha (previously unused, now fixes low/high pressure visibility).
        context.strokeStyle = hexWithAlpha(color, haloAlpha);
        context.lineWidth = isMulti ? 1.4 : 1;
        context.beginPath();
        context.arc(cl.x, cl.y, drawR * (isMulti ? 2.1 : 2.6), 0, Math.PI * 2);
        if (isMulti) context.setLineDash([3, 3]);
        context.stroke();
        context.setLineDash([]);

        // Fill
        context.fillStyle = isMulti ? hexWithAlpha(color, 0.65 + intensity * 0.2) : color;
        context.beginPath();
        context.arc(cl.x, cl.y, drawR, 0, Math.PI * 2);
        context.fill();

        const hitCode = isMulti ? cl.codes.join(",") : cl.codes[0];
        nodeScreenRef.current.push({ code: hitCode, x: cl.x, y: cl.y, r: drawR * (isMulti ? 2.3 : 3.0), clusterCodes: isMulti ? cl.codes : undefined });

        if (isMulti) {
          // Cluster label: airport count
          context.fillStyle = "#ffbc52";
          context.font = "700 9px ui-monospace, monospace";
          context.textAlign = "center";
          context.fillText(String(cl.codes.length), cl.x, cl.y - drawR - 7);
        } else {
          // Solo node label
          if (placed.length < maxLabels) {
            const tooClose = placed.some((p) => Math.hypot(p.x - cl.x, p.y - cl.y) < labelGap);
            if (!tooClose) {
              placed.push({ code: cl.codes[0], x: cl.x, y: cl.y });
              context.fillStyle = cl.codes[0] === hovered ? "#5fd4b4" : "rgba(237,245,241,0.82)";
              context.font = "700 10px ui-monospace, monospace";
              context.textAlign = "center";
              context.fillText(cl.codes[0], cl.x, cl.y - drawR - 5);
            }
          }
        }
      }

      frameRef.current = window.requestAnimationFrame(draw);
    };

    const resizeObserver = new ResizeObserver(() => {
      if (visible && frameRef.current === null) frameRef.current = window.requestAnimationFrame(draw);
    });
    const onVisibility = () => {
      visible = document.visibilityState !== "hidden";
      if (visible && frameRef.current === null) frameRef.current = window.requestAnimationFrame(draw);
    };
    resizeObserver.observe(canvas);
    document.addEventListener("visibilitychange", onVisibility);
    frameRef.current = window.requestAnimationFrame(draw);
    return () => {
      resizeObserver.disconnect();
      document.removeEventListener("visibilitychange", onVisibility);
      if (frameRef.current !== null) window.cancelAnimationFrame(frameRef.current);
    };
  }, [baseArcs, storyArcs, nodes, data.daily, hovered, intensity, minRate, maxRate]);

  const handleDate = (event: ChangeEvent<HTMLInputElement>) => setDayIndex(Number(event.target.value));
  const togglePlaying = () => {
    if (!reducedMotion) setPlaying((value) => !value);
  };
  const onCanvasMove = (event: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const mx = event.clientX - rect.left;
    const my = event.clientY - rect.top;
    const hit = nodeScreenRef.current.find((n) => Math.hypot(n.x - mx, n.y - my) < (n.r || 6));
    setHovered(hit ? hit.code : null);
  };

  const onCanvasClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const mx = event.clientX - rect.left;
    const my = event.clientY - rect.top;
    const hit = nodeScreenRef.current.find((n) => Math.hypot(n.x - mx, n.y - my) < (n.r || 6));
    if (hit) {
      setPinned((prev) => prev === hit.code ? null : hit.code);
      setSelectedCode(null);
    } else {
      setPinned(null);
      setSelectedCode(null);
    }
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") { setPinned(null); setSelectedCode(null); } };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const onA11yClick = (code: string) => {
    const entry = nodeScreenRef.current.find((e) => e.code === code || e.clusterCodes?.includes(code));
    const pinCode = entry?.code ?? code;
    setPinned(pinCode);
    if (entry?.clusterCodes && entry.clusterCodes.length > 1) {
      pendingClusterFocus.current = code;
      setSelectedCode(code);
      setA11yOpen(false);
    } else {
      setSelectedCode(null);
    }
  };

  // Cluster codes are comma-joined (e.g. "JFK,LGA,EWR"); solo node codes match the data.
  const isPinnedCluster = pinned && pinned.includes(",");
  const hoveredNode = hovered && !hovered.includes(",") ? nodes.find((n) => n.code === hovered) : undefined;
  const pinnedNode = pinned && !isPinnedCluster ? nodes.find((n) => n.code === pinned) : undefined;
  const clusterHovered = hovered && hovered.includes(",") ? hovered.split(",") : undefined;
  const pinnedCluster = isPinnedCluster ? pinned.split(",") : undefined;
  const showTooltip = Boolean((pinnedNode || hoveredNode) && !isPinnedCluster && !pinnedCluster);
  const effectiveCluster = pinnedCluster || clusterHovered;
  const selectedAirportMeta = selectedCode ? data.airports.find((a) => a.code === selectedCode) : undefined;

  useEffect(() => {
    const code = pendingClusterFocus.current;
    if (!code || !pinnedCluster) return;
    const frame = window.requestAnimationFrame(() => {
      clusterButtonRefs.current.get(code)?.focus();
      pendingClusterFocus.current = null;
    });
    return () => window.cancelAnimationFrame(frame);
  }, [pinnedCluster, selectedCode]);

  return (
    <section className="network-hero section-shell" aria-labelledby="network-hero-title">
      <div className="network-copy">
        <div className="eyebrow">
          <span className="live-dot" />
          {labels.eyebrow}
        </div>
        <h1 id="network-hero-title">
          {labels.title.map((line) => (
            <span key={line}>{line}</span>
          ))}
        </h1>
        <p className="hero-deck">
          {labels.deck}{" "}
          <strong>
            {data.meta.chainLinks.toLocaleString(language === "zh" ? "zh-CN" : "en-US")}
          </strong>{" "}
          {labels.links}
        </p>
        <div className="hero-actions">
          <a className="primary-action" href="#pressure-board">
            {labels.explore} <span aria-hidden="true">↘</span>
          </a>
          <a className="text-action" href="#method">
            {labels.boundary}
          </a>
        </div>
        <p className="network-note">{labels.note}</p>
      </div>

      <div className="network-visual" aria-label={labels.national}>
        <canvas
          ref={canvasRef}
          aria-hidden="true"
          onMouseMove={onCanvasMove}
          onMouseLeave={() => { if (!pinned) setHovered(null); }}
          onClick={onCanvasClick}
        />
        <div className="network-a11y">
          <button
            type="button"
            className="network-a11y-toggle"
            onClick={() => setA11yOpen((v) => !v)}
            aria-expanded={a11yOpen}
          >
            {a11yOpen ? (language === "zh" ? "收起机场列表" : "Hide airport list") : (language === "zh" ? "选择机场 (键盘浏览)" : "Select airport (keyboard)" )}
          </button>
          {a11yOpen && (
            <div className="network-a11y-list" role="group" aria-label={language === "zh" ? "地图机场" : "Map airports"}>
              {data.mapAirportCodes.map((code) => (
                <button
                  key={code}
                  type="button"
                  aria-pressed={Boolean(pinned?.includes(code))}
                  onClick={() => onA11yClick(code)}
                  className={pinned?.includes(code) ? "active" : ""}
                >
                  {code}
                </button>
              ))}
            </div>
          )}
        </div>
        <span className="network-map-label network-map-label-west">WEST</span>
        <span className="network-map-label network-map-label-east">EAST</span>
        <div className="network-legend">
          <span>
            <i className="legend-line legend-line-base" /> {labels.network}
          </span>
          <span>
            <i className="legend-line legend-line-delay" /> {labels.signal}
          </span>
          <span>
            <i className="legend-node" /> {labels.node}
          </span>
        </div>
        {showTooltip && (() => {
          const n = pinnedNode || hoveredNode!;
          const sample = data.airports.find((airport) => airport.code === n.code);
          const english = sample ?? MAP_ONLY_EN[n.code];
          const chinese = AIRPORT_ZH[n.code];
          return (
          <div
            className="network-tooltip"
            style={{
              left: `${Math.min(82, Math.max(8, n.coord[0] * 100))}%`,
              top: `${Math.min(86, Math.max(8, n.coord[1] * 100))}%`,
            }}
          >
            <strong>{n.code}</strong>
            <span>{language === "zh" ? (chinese?.name ?? n.code) : (english?.name ?? n.code)}</span>
            <small>
              {language === "zh"
                ? [chinese?.city, chinese?.region].filter(Boolean).join("，")
                : [english?.city ?? n.city, english?.region].filter(Boolean).join(", ")}
            </small>
            <small>
              {n.pressureScore > 0
                ? `${labels.delay} ${pct(n.delayRate)} · ${labels.levelLabel} ${n.pressureScore.toFixed(0)}`
                : (language === "zh" ? "地图航线节点，未进入 97 机场样本" : "Map node — not in the 97-airport sample")}
            </small>
          </div>
        ); })()}
        {effectiveCluster && effectiveCluster.length > 1 && (
          <div className={`network-cluster-hud${pinnedCluster ? " is-pinned" : ""}`} role="dialog" aria-label={language === "zh" ? "聚合机场" : "Airport cluster"}>
            <div className="cluster-head">
              <strong>{effectiveCluster.length} {language === "zh" ? "机场" : "airports"}</strong>
              {pinnedCluster && (
                <button type="button" className="cluster-close" onClick={() => { setPinned(null); setSelectedCode(null); }} aria-label={language === "zh" ? "关闭" : "Close"}>✕</button>
              )}
            </div>
            <div className="cluster-list">
              {effectiveCluster.map((code) => (
                <button
                  key={code}
                  type="button"
                  ref={(element) => {
                    if (element) clusterButtonRefs.current.set(code, element);
                    else clusterButtonRefs.current.delete(code);
                  }}
                  className={selectedCode === code ? "active" : ""}
                  onClick={(e) => { e.stopPropagation(); setSelectedCode((prev) => prev === code ? null : code); }}
                >
                  {code}
                </button>
              ))}
            </div>
            {selectedCode && (
              <div className="cluster-detail">
                <strong>{selectedCode}</strong>
                {language === "zh" ? (
                  <>
                    <span>{AIRPORT_ZH[selectedCode]?.name ?? selectedCode}</span>
                    {selectedAirportMeta?.name && selectedAirportMeta.name !== selectedCode && <small className="cluster-en-name">{selectedAirportMeta.name}</small>}
                    <small>{AIRPORT_ZH[selectedCode]?.city ?? ""}{AIRPORT_ZH[selectedCode]?.region ? `，${AIRPORT_ZH[selectedCode].region}` : ""}</small>
                  </>
                ) : (
                  <>
                    <span>{selectedAirportMeta?.name ?? MAP_ONLY_EN[selectedCode]?.name ?? selectedCode}</span>
                    {(selectedAirportMeta?.city ?? MAP_ONLY_EN[selectedCode]?.city) ? (
                      <small>
                        {selectedAirportMeta?.city ?? MAP_ONLY_EN[selectedCode]?.city}
                        {(selectedAirportMeta?.region ?? MAP_ONLY_EN[selectedCode]?.region) ? `, ${selectedAirportMeta?.region ?? MAP_ONLY_EN[selectedCode]?.region}` : ""}
                      </small>
                    ) : null}
                  </>
                )}
                {selectedAirportMeta?.pressureScore && selectedAirportMeta.pressureScore > 0 ? (
                  <small>{language === "zh" ? "延误率" : "delay"} {pct(selectedAirportMeta.delayRate)} · {labels.levelLabel} {selectedAirportMeta.pressureScore.toFixed(0)}</small>
                ) : (
                  <small className="cluster-out-of-sample">{language === "zh" ? "地图航线节点，未进入 97 机场压力榜样本" : "Map route node — not in the 97-airport pressure sample"}</small>
                )}
              </div>
            )}
          </div>
        )}
        <div className="network-hud">
          <span>{metricLabel}</span>
          <strong>{pct(metricRate)}</strong>
          <small>
            {labels.levelLabel}：{levelLabel}
          </small>
          <small>
            {metricLabel} · {point.day}/31
          </small>
        </div>
      </div>

      <div className="network-controls" aria-label={language === "zh" ? "日期播放控制" : "Date playback controls"}>
        <button
          type="button"
          className="network-play"
          onClick={togglePlaying}
          disabled={reducedMotion}
          aria-label={reducedMotion ? labels.motionOff : playing ? labels.pause : labels.play}
          aria-pressed={playing}
        >
          {playing ? "Ⅱ" : "▶"}
        </button>
        <div className="network-date">
          <span>
            {language === "zh" ? `5 月 ${point.day} 日` : `May ${point.day}, 2026`}
          </span>
          <strong>{pct(metricRate)}</strong>
        </div>
        <label className="network-slider">
          <span className="sr-only">{labels.select}</span>
          <input
            type="range"
            min="0"
            max={data.daily.length - 1}
            value={dayIndex}
            onChange={handleDate}
            aria-valuetext={
              language === "zh"
                ? `5 月 ${point.day} 日，${metricLabel} ${pct(metricRate)}`
                : `May ${point.day}, ${metricLabel} ${pct(metricRate)}`
            }
          />
        </label>
        <div className="network-metrics">
          <span>
            <strong>{pct(point.cancelRate)}</strong>
            {labels.cancel}
          </span>
          <span>
            <strong>{pct(point.propagationRate)}</strong>
            {labels.propagation}
          </span>
        </div>
        <div className="network-metric-selector" role="radiogroup" aria-label={language === "zh" ? "选择全国指标" : "Select national metric"}>
          {(["delayRate", "cancelRate", "propagationRate"] as const).map((m) => {
            const selected = metric === m;
            const lbl = m === "delayRate" ? labels.metricDelay : m === "cancelRate" ? labels.metricCancel : labels.metricPropagation;
            return (
              <button
                key={m}
                type="button"
                role="radio"
                aria-checked={selected}
                className={selected ? "active" : ""}
                onClick={() => setMetric(m)}
              >
                {lbl}
              </button>
            );
          })}
        </div>
        <div className="network-metric-legend">
          {labels.metricLegend}
        </div>
        <div className="network-trend" aria-label={metricLabel + " " + labels.trend}>
          <span className="network-trend-label">{metricLabel} · {labels.trend}</span>
          <svg viewBox="0 0 310 40" preserveAspectRatio="none" role="img" aria-label={metricLabel + " " + labels.trend}>
            {data.daily.map((d, i) => {
              const h = 4 + (maxRate > minRate ? (d[metric] - minRate) / (maxRate - minRate) : 0.5) * 30;
              const x = (i / (data.daily.length - 1)) * 306 + 2;
              const active = i === dayIndex;
              return (
                <rect
                  key={d.day}
                  x={x - 2.4}
                  y={36 - h}
                  width={4.8}
                  height={h}
                  fill={active ? "#ffbc52" : "#5fd4b4"}
                  opacity={active ? 1 : 0.55}
                />
              );
            })}
          </svg>
        </div>
      </div>
    </section>
  );
}
