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
  assert.match(html, /连续状态 episode/);
  assert.match(html, /机制图/);
  assert.match(html, /保守传播信号/);
});

test("V1-B curated episode explorer renders without full episode payload", async () => {
  const response = await render();
  const html = await response.text();
  assert.match(html, /连续延误案例/);
  assert.match(html, /同一架飞机，延误状态能延续多久/);
  assert.match(html, /50,526/);
  assert.match(html, /180 分钟/);
  assert.match(html, /18 小时/);
  assert.match(html, /定义敏感性实验室/);
  assert.match(html, /15、30、60 分钟/);
  assert.match(html, /主分析基线/);
  assert.match(html, /观察中断/);
  assert.match(html, /连续深度/);
  assert.match(html, /观察点数量/);
  assert.match(html, /延误正在放大|延误继续传递|延误正在追回/);
  assert.doesNotMatch(html, />deepest</);
  assert.doesNotMatch(html, />amplified</);
  assert.equal((html.match(/aria-pressed="(?:true|false)"/g) ?? []).length >= 14, true);
  // Three network metric radios + three V1-B threshold radios.
  assert.equal((html.match(/role="radio"/g) ?? []).length, 6);
  assert.equal((html.match(/aria-checked="(?:true|false)"/g) ?? []).length, 6);
  assert.doesNotMatch(html, /ep-[A-Z0-9-]{4,}-00000\d/g);
});
