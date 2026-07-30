import assert from "node:assert/strict";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);
  return worker.fetch(
    new Request("http://localhost/", { headers: { accept: "text/html" } }),
    { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } },
    { waitUntil() {}, passThroughOnException() {} },
  );
}

test("server-renders the Chinese-first bilingual V0 product", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);
  const html = await response.text();
  assert.match(html, /<html lang="zh-CN">/i);
  assert.match(html, /Airports Under Stress/);
  assert.match(html, /611,735/);
  assert.match(html, /机场压力榜/);
  assert.match(html, /飞机轮转故事/);
  assert.match(html, />中文<\/button>/);
  assert.match(html, />EN<\/button>/);
  assert.doesNotMatch(html, /codex-preview|Your site is taking shape|react-loading-skeleton/i);
});

test("includes metric selector with three indicators", async () => {
  const response = await render();
  const html = await response.text();
  assert.match(html, /起飞延误率/);
  assert.match(html, /取消率/);
  assert.match(html, /传播率/);
  assert.match(html, /role="radiogroup"/);
});

test("shows Chinese airport and airline names in serialized data", async () => {
  const response = await render();
  const html = await response.text();
  assert.match(html, /达拉斯/);
  assert.match(html, /休斯顿/);
  assert.match(html, /新奥尔良/);
  assert.match(html, /西南航空/);
  assert.match(html, /达美航空/);
  assert.match(html, /按压力指数排序/);
  assert.match(html, /\/ 100/);
});

test("shows pressure board scope and rank info", async () => {
  const response = await render();
  const html = await response.text();
  // Static text that DOES render server-side.
  assert.match(html, /97/);
  assert.match(html, /10,\s*000/);
  assert.match(html, /机场/);
});

test("has keyboard-accessible airport list and sample scope", async () => {
  const response = await render();
  const html = await response.text();
  assert.match(html, /按压力指数排序/);
  assert.match(html, /选择机场/);
  assert.match(html, /键盘浏览/);
  // listbox appears when toggle is clicked (client-side), SSR renders the toggle button
  assert.match(html, /network-a11y/);
});

test("V1-A mechanism section renders", async () => {
  const response = await render();
  const html = await response.text();
  assert.match(html, /传播机制/);
  assert.match(html, /mechanism-section/);
  assert.match(html, /识别出的连续延误段/);
  assert.match(html, /哪些机场更常接到晚点飞机/);
  assert.match(html, /考虑样本误差后仍较高/);
  assert.match(html, /天气不好时，延误更容易继续吗/);
  assert.match(html, /95% 估计范围/);
  assert.match(html, /核心机场 96\/97/);
  assert.match(html, /本页分析机场 55\/55/);
  assert.match(html, /低能见度/);
  assert.match(html, /低云底/);
  assert.match(html, /机场天气详情/);
  assert.match(html, /把其他可观察条件放进来后，差距还剩多少/);
  assert.match(html, /机场与时段相近/);
  assert.match(html, /运营条件也相近/);
  assert.match(html, /3\.17(?:<!-- -->|\s)*个百分点/);
  assert.match(html, /调整后的数字不一定比直接比较更小/);
  assert.match(html, /不能把差异解释成天气造成的延误/);
});

test("V1-B curated episode explorer renders without full episode payload", async () => {
  const response = await render();
  const html = await response.text();
  assert.match(html, /连续延误案例/);
  assert.match(html, /同一架飞机，延误状态能延续多久/);
  assert.match(html, /50,526/);
  assert.match(html, /180 分钟/);
  assert.match(html, /18 小时/);
  assert.match(html, /换一种晚点标准，结论会变吗/);
  assert.match(html, /30 或 60 分钟/);
  assert.match(html, /主分析基线/);
  assert.match(html, /观察中断/);
  assert.match(html, /未观察到最终结果/);
  assert.match(html, /连续晚点次数/);
  assert.match(html, /页面展示步骤/);
  assert.match(html, /延误正在放大|延误继续传递|延误正在追回/);
  assert.doesNotMatch(html, />deepest</);
  assert.doesNotMatch(html, />amplified</);
  assert.equal((html.match(/aria-pressed="(?:true|false)"/g) ?? []).length >= 14, true);
  assert.match(html, /当前观察点天气/);
  assert.match(html, /天气报告匹配范围/);
  assert.match(html, /报告 UTC|unavailable/);
  // 3 network + 2 mechanism weather + 3 delay threshold + 2 episode weather + 3 congestion-window radios.
  assert.equal((html.match(/role="radio"/g) ?? []).length, 13);
  assert.equal((html.match(/aria-checked="(?:true|false)"/g) ?? []).length, 13);
  assert.doesNotMatch(html, /ep-[A-Z0-9-]{4,}-00000\d/g);
});

test("V3-A scheduled-congestion section renders with window toggles, non-causal boundary, and updated numbering", async () => {
  const response = await render();
  const html = await response.text();
  assert.match(html, /计划拥挤/);
  assert.match(html, /congestion-section/);
  assert.match(html, /航班排得越密，延误越容易继续吗/);
  assert.match(html, /计划总架次/);
  // Three window toggles (30 / 60 / 90 min). JSX `{value} min` serializes with a
  // React comment separator (e.g. `30<!-- --> min`), so allow <!-- --> or whitespace.
  assert.match(html, /30(?:<!-- -->|\s)*min/);
  assert.match(html, /60(?:<!-- -->|\s)*min/);
  assert.match(html, /90(?:<!-- -->|\s)*min/);
  // Default 60-minute glance: meaning + values of the three core numbers.
  assert.match(html, /排班较松/);
  assert.match(html, /排班较密/);
  assert.match(html, /两组相差/);
  assert.match(html, /42\.27%/);
  assert.match(html, /66\.15%/);
  assert.match(html, /约\s*24\s*个百分点|about\s*24/);
  // Research-details disclosure exists.
  assert.match(html, /查看研究细节/);
  // Plain-language non-causal boundary preserved (no causal claim).
  assert.match(html, /不能证明排班密造成了延误/);
  assert.match(html, /同时出现/);
  // Frozen-event wording removed from rendered HTML.
  assert.doesNotMatch(html, /冻结事件|frozen events/i);
  // Audit boundary kept inside the details, not deleted: CONDITIONAL GO + OMA.
  assert.match(html, /CONDITIONAL GO/);
  assert.match(html, /OMA/);
  assert.doesNotMatch(html, /SourceRow/);
  // Episode explorer renumbered to 07, method section renumbered to 08.
  assert.match(html, /07 \/ 连续延误案例/);
  assert.match(html, /08 \/ 方法与边界/);
  // Radio count now includes the three congestion-window radios.
  assert.equal((html.match(/role="radio"/g) ?? []).length, 13);
});

test("V3-B airport scheduled-congestion explorer renders plain-language default and 54-airport selector", async () => {
  const response = await render();
  const html = await response.text();
  // New plain-language question heading inside chapter 06.
  assert.match(html, /换到一座机场，结果还一样吗|Does it hold at a single airport\?/);
  assert.match(html, /54/);
  assert.match(html, /52/);
  assert.match(html, /只和自己比较|compare it only with itself/);
  // Airport selector with the default airport present; OMA must NOT be an option.
  assert.match(html, /ATL/);
  assert.match(html, /亚特兰大|Atlanta/);
  const airportSelect = html.match(/<select[^>]*name="v3b-airport"[^>]*>[\s\S]*?<\/select>/)?.[0];
  assert.ok(airportSelect, "V3-B airport selector must render");
  assert.equal((airportSelect.match(/<option/g) ?? []).length, 54);
  assert.doesNotMatch(airportSelect, /value="OMA"/);
  // Default airport selector value is ATL.
  assert.match(airportSelect, /value="ATL"[^>]*selected/);
  // Three core numbers at the 60-minute primary window are present (ATL positive).
  assert.match(html, /排班较松时继续晚点率|Stayed-late rate, loosest schedule/);
  assert.match(html, /排班较密时继续晚点率|Stayed-late rate, tightest schedule/);
  assert.match(html, /两组相差|Gap between groups/);
  assert.match(html, /46\.48%/);
  assert.match(html, /61\.93%/);
  assert.match(html, /约(?:<!-- -->|\s)*15(?:<!-- -->|\s)*<em>个百分点|about(?:<!-- -->|\s)*15(?:<!-- -->|\s)*<em>pp/);
  // Real ATL 60-minute primary numbers (positive direction).
  assert.match(html, /46\.48%/);
  assert.match(html, /61\.93%/);
  assert.match(html, /约\s*15\s*个百分点|about\s*15/);
  // 30/60/90 band exists and 60 is tagged primary.
  assert.match(html, /30(?:<!-- -->|\s)*min/);
  assert.match(html, /60(?:<!-- -->|\s)*min/);
  assert.match(html, /90(?:<!-- -->|\s)*min/);
  assert.match(html, /主口径|primary/);
  // Same-positive direction sentence (ATL default) is rendered.
  assert.match(html, /换三种统计范围（30 \/ 60 \/ 90 分钟），方向都一样|under all three ranges \(30 \/ 60 \/ 90 minutes\) the direction is the same/);
  // Reverse explanation template exists in the bundle for JFK/ONT (not on default ATL).
  // OMA appears only inside research-details copy, never as a selectable option.
  assert.match(html, /OMA 因排班较密组仅 82 条|OMA is excluded from the selector/);
  // Research-details disclosure is present (default closed; full fields still in SSR).
  assert.match(html, /查看研究细节|View research details/);
  assert.match(html, /每座机场要求排班较松、排班较密两组都至少 100 条|Each airport needs at least 100/);
  assert.match(html, /当前机场 ATL 三档明细/);
  assert.match(html, /其中继续晚点/);
  assert.match(html, /634/);
  assert.match(html, /597/);
  // No causal / ranking vocabulary leaked into the default layer.
  assert.doesNotMatch(html, /最危险|最好|最差|most dangerous|best airport|worst airport/i);
});


test("site clarity refactor: plain-language defaults, research-details, and no outdated copy", async () => {
  const response = await render();
  const html = await response.text();

  // 首屏三个人话指标与「研究覆盖」次级样本语义
  assert.match(html, /起飞晚点 15 分钟以上/);
  assert.match(html, /晚点继续传到下一班/);
  assert.match(html, /晚点被下一班追回/);
  assert.match(html, /研究覆盖/);
  assert.match(html, /架有机尾号的飞机/);

  // 机场榜 / 航司 / 轮转 各自存在研究细节入口与内容
  assert.match(html, /查看研究细节/);
  assert.match(html, /97 个机场纳入比较/);
  assert.match(html, /共 12 家航司纳入比较/);
  assert.match(html, /这些衔接用 15 分钟统一门槛/);

  // 第 05 章默认三项核心摘要 + 天气白话结论 + 两个细节入口
  assert.match(html, /识别出的连续延误段/);
  assert.match(html, /至少连续 3 次/);
  assert.match(html, /最长连续晚点次数/);
  assert.match(html, /恶劣天气组里，下一班仍然晚点的比例更高一些/);
  assert.match(html, /出现恶劣天气条件/);
  assert.match(html, /未出现这些条件/);
  assert.match(html, /两组相差/);
  assert.match(html, /查看天气研究细节/);
  assert.match(html, /查看调整分析/);

  // 第 06 章：三把尺子的意义 + 仅与机场自己比较
  assert.match(html, /前 15 \+ 后 15/);
  assert.match(html, /前 30 \+ 后 30/);
  assert.match(html, /前 45 \+ 后 45/);
  assert.match(html, /排班松紧是在每个机场内部比较/);

  // 第 07 章：每步天气面板收起，summary 使用「查看这一步的天气」，完整字段仍在 SSR
  assert.match(html, /查看这一步的天气/);
  assert.match(html, /只从当前航班事件发生前这段时间内/);
  assert.match(html, /当前观察点天气/);
  assert.match(html, /天气报告匹配范围/);
  assert.match(html, /报告 UTC|unavailable/);

  // 第 08 章：不再出现过时文案，包含新的非因果 / 完整性说明
  assert.doesNotMatch(html, /将在后续版本控制/);
  assert.doesNotMatch(html, /reserved for later versions/i);
  assert.match(html, /后续章节已分别做了天气与计划拥挤的描述性比较/);
  assert.match(html, /这些完整性数字说明数据处理可靠/);
});
