// The bars frame's expansion runs when the frame is first READ, not when it lands (2026-09-11). Since T278c the
// view expanded every compact wire bar and judging entry in _mergeBars, ahead of the paint hold that skips draw()
// for a hidden pane, so a dashboard tab in the background paid the whole expansion (tens of milliseconds and tens
// of thousands of allocations per full frame) for frames nobody saw, and a visible tab paid it again for every
// lane a full frame repeated unchanged. Now the wire payload is merged as received and data.turns / data.judging
// expand on their first read (_bindBars), the expansion reuses what the previous one built wherever the wire says
// the same thing (reuseLane), and the drawn SVG is the same as before. Headless over ui/test-dom-shim.ts with a
// recording document, as ui/timeline-hidden-hold.test.ts. Every value is synthetic.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as path from "node:path";
import { createRequire } from "node:module";
import { nodeFactory } from "./test-dom-shim";

const makeNode = nodeFactory({ rect: { width: 1400, height: 420, left: 0, top: 0, right: 1400, bottom: 420 } });
const docListeners: Record<string, Array<(e: any) => void>> = {};
const g: any = global;
g.document = {
  visibilityState: "visible",
  createElement(t: string) { return t === "canvas" ? { getContext() { return { font: "", measureText(s: string) { return { width: (s ? s.length : 0) * 6 }; } }; } } : makeNode(t); },
  createElementNS(_n: any, t: string) { return makeNode(t); },
  body: makeNode("body"), documentElement: makeNode("html"), head: makeNode("head"),
  getElementById() { return null; },
  addEventListener(t: string, fn: (e: any) => void) { (docListeners[t] ||= []).push(fn); },
  removeEventListener(t: string, fn: (e: any) => void) { const a = docListeners[t] || []; const i = a.indexOf(fn); if (i >= 0) a.splice(i, 1); },
};
class FakeIO {
  cb: (entries: any[], io: any) => void; targets: any[] = [];
  constructor(cb: (entries: any[], io: any) => void) { this.cb = cb; }
  observe(t: any) { this.targets.push(t); }
  disconnect() {}
}
g.IntersectionObserver = FakeIO;
// The triage judges are shown (the gear's toggle), so draw() reads the judging band: with both toggles off the
// band is never read, and under the lazy expansion never expanded either.
g.localStorage = { getItem(k: string) { return k === "romp:settings" ? JSON.stringify({ showTriageJudges: true }) : null; }, setItem() {}, removeItem() {} };
g.getComputedStyle = () => ({ backgroundColor: "rgb(30,30,30)" });
g.requestAnimationFrame = () => 1;
g.cancelAnimationFrame = () => {};
g.addEventListener = () => {}; g.removeEventListener = () => {};
g.matchMedia = () => ({ matches: false, addEventListener() {}, addListener() {} });
g.window = g;
g.innerWidth = 1400; g.innerHeight = 800;
// A fixed clock: the live edge interpolates from performance.now(), so two panels drawing the same frames at
// different instants would differ in every x position. Pinned before the module loads; it reads the global per call.
g.performance = { now: () => 5000 };

const viewPath = path.resolve(process.cwd(), "..", "ui", "romp-timeline-view.js");
const { TimelinePanel, expandBars, expandJudging } = createRequire(__filename)(viewPath);
// The view's own count of wire objects expanded; a view without it (the tree before this change) reads NaN, so
// every count assertion fails there for the reason it should while the paint pins below still run.
const _expandCounts = createRequire(__filename)(viewPath)._expandCounts || { bars: NaN, judging: NaN };

// ---- a synthetic board in the T278c wire shape: three lanes of compact bars, a compact judging band ----
const NOW = 1_781_000_000;
const SIDS = ["11111111-2222-4333-8444-000000000001", "11111111-2222-4333-8444-000000000002", "11111111-2222-4333-8444-000000000003"];
function wireBar(sid: string, n: number) {
  const start = NOW - 3000 + n * 200;
  const b: any = { id: `${sid.slice(-2)}:${n}:aa`, start, end: start + 90, p: `p-${sid.slice(-2)}-${n}`, w: `w-${sid.slice(-2)}-${n}`, r: `r-${sid.slice(-2)}-${n}`, q: `request ${n}`, c: `did step ${n}` };
  if (n % 3 === 0) b.d = [`m-${n}`, `m-${n + 1}`];
  if (n % 4 === 1) b.s = "queued";
  return b;
}
function wireLane(sid: string, count: number) { const out = []; for (let n = 0; n < count; n++) out.push(wireBar(sid, n)); return out; }
function wireJudging(sid: string, count: number) {
  const out = [];
  for (let n = 0; n < count; n++) { const t = NOW - 2500 + n * 300; out.push({ k: `${t}/closer`, t, j: "closer", t1: t + 4, x: `gloss ${n}`, ms: 1200 + n, in: 300, out: 40, s: t, r: t + 4 }); }
  return out;
}
const LANE_COUNTS = [7, 5, 9];
const JUDGING_COUNTS = [3, 2, 4];
function board() {
  const turns: any = {}, judging: any = {};
  SIDS.forEach((sid, i) => { turns[sid] = wireLane(sid, LANE_COUNTS[i]); judging[sid] = wireJudging(sid, JUDGING_COUNTS[i]); });
  return { turns, judging };
}
const TOTAL_BARS = LANE_COUNTS.reduce((a, b) => a + b, 0);
const TOTAL_JUDGING = JUDGING_COUNTS.reduce((a, b) => a + b, 0);
function sess(id: string, name: string) {
  return { id, name, color: "#7aa2f7", state: "working", live: true, model: "Opus 4.8", effort: "xhigh", context: 40, since: NOW - 60,
    awaiting: [], compacting: [], pendingMail: 0, compactions: [], faded: false, stale: false };
}
function skeleton(dNow = 0) {
  return { now: NOW + dNow, sessions: SIDS.map((s, i) => sess(s, "lane" + i)), turns: {}, judging: {}, messages: [], nudges: [], activeChat: null, focus: null, hover: null, usage: null };
}
// A full bars frame is a fresh parse on the wire: every lane array and every bar object new (JSON round trip).
function fullFrame(b = board(), dNow = 0) { return JSON.parse(JSON.stringify({ type: "bars", turns: b.turns, judging: b.judging, messages: [], nudges: [], now: NOW + dNow })); }

function mk() {
  g.document.visibilityState = "visible";   // a failed test leaves the document as it was; every panel starts on a visible tab
  const panel: any = new TimelinePanel(makeNode("div"));
  if (panel._loaderBackstop != null) { clearTimeout(panel._loaderBackstop); panel._loaderBackstop = null; }
  const c = { draws: 0 };
  const real = panel.draw.bind(panel);
  panel.draw = () => { c.draws++; real(); };
  return { panel, c };
}
function setVisibility(state: "hidden" | "visible") {
  g.document.visibilityState = state;
  for (const fn of [...(docListeners.visibilitychange || [])]) fn({ type: "visibilitychange" });
}
function done(panel: any) { g.document.removeEventListener("visibilitychange", panel._onVis); g.document.visibilityState = "visible"; }
function resetCounts() { _expandCounts.bars = 0; _expandCounts.judging = 0; }
function counts() { return { bars: _expandCounts.bars, judging: _expandCounts.judging }; }
// A reference expansion for an assertion, without it counting: the exported expanders run the same counted functions.
function ref<T>(f: () => T): T { const c = counts(); const r = f(); _expandCounts.bars = c.bars; _expandCounts.judging = c.judging; return r; }
// The drawn SVG as text: every node's tag, its attributes in name order, and its text, one line per node.
function serialize(node: any, out: string[] = [], depth = 0): string[] {
  const attrs = Object.keys(node._attrs || {}).sort().map((k) => `${k}=${node._attrs[k]}`).join(" ");
  out.push(`${"  ".repeat(depth)}${node.tag} ${attrs} ${node._text || ""}`);
  for (const ch of node.children || []) serialize(ch, out, depth + 1);
  return out;
}
function svgText(panel: any): string { return serialize(panel.svg).join("\n"); }

test("a bars frame landing on a hidden tab expands nothing; the return expands once and draws once", () => {
  const { panel, c } = mk();
  setVisibility("hidden");
  resetCounts();
  panel.update(skeleton());
  panel.applyBars(fullFrame());
  assert.equal(c.draws, 0, "held: no paint");
  assert.deepEqual(counts(), { bars: 0, judging: 0 }, "held: no bar and no judging entry expanded");
  assert.equal(panel._barsLoaded, true, "the loader latch still flips on the merge");
  assert.equal(panel.fitted, true, "the window fit still reads the frame (its starts are on the wire by name)");
  for (let i = 1; i <= 5; i++) { panel.update(skeleton(i)); panel.applyBars(fullFrame(board(), i)); }
  assert.deepEqual(counts(), { bars: 0, judging: 0 }, "five more held frames: still nothing expanded");
  setVisibility("visible");
  assert.equal(c.draws, 1, "the return paints one catch-up");
  assert.deepEqual(counts(), { bars: TOTAL_BARS, judging: TOTAL_JUDGING }, "which expands the held frame exactly once");
  assert.equal(panel.svg.children.length > 10, true, "into a populated SVG");
  assert.deepEqual(panel.data.turns, ref(() => expandBars(board().turns)), "and every reader sees the long-named bars");
  assert.deepEqual(panel.data.judging, ref(() => expandJudging(board().judging)));
  assert.deepEqual(counts(), { bars: TOTAL_BARS, judging: TOTAL_JUDGING }, "reading again expands nothing more");
  done(panel);
});

test("a reader under the hold gets the expanded shape on demand, and the hold's release does not expand it again", () => {
  const { panel, c } = mk();
  setVisibility("hidden");
  resetCounts();
  panel.update(skeleton());
  panel.applyBars(fullFrame());
  const anchor = panel.nearestTurnAnchor(SIDS[0], NOW - 3000 + 400);   // a deep-link lookup while hidden
  assert.equal(anchor && anchor.promptId, "p-01-2", "the reader sees a long-named bar");
  assert.deepEqual(counts(), { bars: TOTAL_BARS, judging: 0 }, "the read expanded the bars, and only the bars");
  setVisibility("visible");
  assert.equal(c.draws, 1);
  assert.deepEqual(counts(), { bars: TOTAL_BARS, judging: TOTAL_JUDGING }, "the draw expanded the judging band and reused the bars");
  done(panel);
});

test("a second full frame whose lanes say the same thing reuses the expansion, lane arrays and all", () => {
  const { panel } = mk();
  resetCounts();
  panel.update(skeleton());
  panel.applyBars(fullFrame());
  assert.deepEqual(counts(), { bars: TOTAL_BARS, judging: TOTAL_JUDGING }, "visible: the first frame expands on its draw");
  const lanes1 = SIDS.map((s) => panel.data.turns[s]), judging1 = panel.data.judging;
  panel.applyBars(fullFrame(board(), 1));   // a fresh parse of the same board: no array or object identity survives
  assert.deepEqual(counts(), { bars: TOTAL_BARS, judging: TOTAL_JUDGING }, "nothing is expanded again");
  SIDS.forEach((s, i) => assert.equal(panel.data.turns[s], lanes1[i], `lane ${i} keeps its expanded array`));
  assert.equal(panel.data.judging, judging1, "the judging list keeps its identity too");
  // one bar changes in one lane: that bar alone is expanded; the lane is a new array, the others are not
  const b3 = board(); b3.turns[SIDS[1]][2].c = "did step 2, then more";
  panel.applyBars(fullFrame(b3, 2));
  assert.deepEqual(counts(), { bars: TOTAL_BARS + 1, judging: TOTAL_JUDGING }, "exactly the changed bar is expanded");
  assert.notEqual(panel.data.turns[SIDS[1]], lanes1[1], "the changed lane is a new array");
  assert.equal(panel.data.turns[SIDS[1]][2].summary, "did step 2, then more", "carrying the change");
  assert.equal(panel.data.turns[SIDS[1]][1], lanes1[1][1], "and the lane's other bars are the objects already held");
  assert.equal(panel.data.turns[SIDS[0]], lanes1[0]); assert.equal(panel.data.turns[SIDS[2]], lanes1[2]);
  assert.deepEqual(panel.data.turns, ref(() => expandBars(b3.turns)), "the whole shape is what a plain expansion gives");
  // a bar appended to a lane: one expansion; a bar removed: none
  const b4 = JSON.parse(JSON.stringify(b3)); b4.turns[SIDS[2]].push(wireBar(SIDS[2], 9));
  panel.applyBars(fullFrame(b4, 3));
  assert.deepEqual(counts(), { bars: TOTAL_BARS + 2, judging: TOTAL_JUDGING });
  assert.equal(panel.data.turns[SIDS[2]].length, LANE_COUNTS[2] + 1);
  const b5 = JSON.parse(JSON.stringify(b4)); b5.turns[SIDS[0]].shift();
  panel.applyBars(fullFrame(b5, 4));
  assert.deepEqual(counts(), { bars: TOTAL_BARS + 2, judging: TOTAL_JUDGING }, "a shorter lane reuses every bar it kept, found by id");
  assert.deepEqual(panel.data.turns, ref(() => expandBars(b5.turns)));
  // a field that LEAVES a bar (a default now omitted) is a change too
  const b6 = JSON.parse(JSON.stringify(b5)); delete b6.turns[SIDS[0]][0].c;
  panel.applyBars(fullFrame(b6, 5));
  assert.deepEqual(counts(), { bars: TOTAL_BARS + 3, judging: TOTAL_JUDGING });
  assert.equal(panel.data.turns[SIDS[0]][0].summary, "", "and the reader sees the default");
  done(panel);
});

test("the judging band reuses its entries the same way: one changed entry expands one entry", () => {
  const { panel } = mk();
  panel.update(skeleton());
  panel.applyBars(fullFrame());
  resetCounts();
  const b = board(); b.judging[SIDS[2]][1].ms = 9999;
  panel.applyBars(fullFrame(b, 1));
  assert.deepEqual(counts(), { bars: 0, judging: 1 });
  assert.equal(panel.data.judging.find((e: any) => e.sid === SIDS[2] && e.ms === 9999) != null, true);
  assert.deepEqual(panel.data.judging, ref(() => expandJudging(b.judging)));
  const b2 = board(); b2.judging[SIDS[0]].push({ k: `${NOW}/closer`, t: NOW, j: "closer", u: true });
  panel.applyBars(fullFrame(b2, 2));
  assert.deepEqual(counts(), { bars: 0, judging: 3 }, "the appended entry and the reverted one expand; the rest are found by key");
  assert.deepEqual(panel.data.judging, ref(() => expandJudging(b2.judging)));
  done(panel);
});

test("a lane array the shim hands back unchanged (a delta) still expands nothing, as before", () => {
  const { panel } = mk();
  panel.update(skeleton());
  const f = fullFrame();
  panel.applyBars(f);
  resetCounts();
  const delta = { type: "bars", turns: { ...f.turns }, judging: { ...f.judging }, messages: [], nudges: [], now: NOW + 1 };   // the same lane arrays
  delta.turns[SIDS[1]] = f.turns[SIDS[1]].concat([wireBar(SIDS[1], 5)]);   // one touched lane: its kept bars are the same objects
  panel.applyBars(delta);
  assert.deepEqual(counts(), { bars: 1, judging: 0 });
  done(panel);
});

test("the drawn SVG is the same whether the frames landed on a visible tab, behind a hold, or as a repeated full frame", () => {
  const seen = mk();
  seen.panel.update(skeleton()); seen.panel.applyBars(fullFrame());
  const drawnSeen = svgText(seen.panel);
  const held = mk();
  setVisibility("hidden");
  held.panel.update(skeleton()); held.panel.applyBars(fullFrame());
  for (let i = 1; i <= 3; i++) { held.panel.update(skeleton()); held.panel.applyBars(fullFrame(board())); }
  setVisibility("visible");
  assert.equal(held.c.draws, 1);
  assert.equal(svgText(held.panel), drawnSeen, "the catch-up paints exactly what the visible tab painted");
  seen.panel.applyBars(fullFrame(board()));   // the reuse path
  assert.equal(svgText(seen.panel), drawnSeen, "a repeated frame through the reuse path paints the same SVG");
  // the golden shape of this board: one judging mark per entry (300 s apart, none merge), each at a finite x
  const rects: any[] = [];
  const walk = (n: any) => { if (n.tag === "rect" && n._attrs["data-judge"]) rects.push(n); for (const c of n.children || []) walk(c); };
  walk(seen.panel.svg);
  assert.equal(rects.length, TOTAL_JUDGING);
  const xs = rects.map((r) => Number(r._attrs.x));
  assert.equal(xs.every((x) => Number.isFinite(x)), true, "marks carry numeric x positions");
  done(seen.panel); done(held.panel);
});
