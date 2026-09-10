// The timeline's redraw budget on a many-session dashboard (2026-09-04). Measured with a headless browser
// replaying a real seventeen-session board: the live-follow loop woke every animation frame and forced a
// layout each time (about 40% of the shared main thread on an IDLE dashboard), rebuilt the whole SVG once
// the edge had crept 0.15 px, and inside each rebuild compared every turn against every message. The chat pane's tab clicks share
// that thread, so every one of these landed on the user as click lag. Like the other timeline tests,
// the wiring is pinned at the source level, and the pure helper is run.
//
// The live tick as a transform write (2026-09-06). While the timeline follows the live edge, a rAF loop
// (_tickLive) advanced the clock by wiping and rebuilding the whole svg every time the edge moved 0.15 px:
// about 30 ms a draw, twice a second at a one-hour window and up to sixteen times a second at ten minutes
// (the pane's largest cost while visible, and invisible to every handler bracket). draw() now puts every
// time-positioned element in one plot group, and the tick writes one translate on that group plus a width on
// each element whose right edge rides the live now (an open bar, an open awaiting or compacting span, an
// open judging run); a full draw() stays only for what a translate cannot express. Headless, on the DOM shim
// timeline-render.test.ts uses: the shim counts element creation, so a rebuild is observable.
//
// Merged 2026-09-07: both mechanisms ship. With a plot handle the tick translates on every animation frame
// (TICK_MIN_PX guards the sub-pixel move); with none (a glyph rides the live edge) the rebuild is paced as
// above: a draw once the edge has moved LIVE_MIN_PX, then a sleep of _liveWaitMs(). The first group of tests
// pins the pacing at the source and runs the pure helpers; the second drives a panel on the DOM shim.

import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { nodeFactory } from "./test-dom-shim";

const SRC = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "romp-timeline-view.js"), "utf8");

test("the live tick sleeps until the edge has moved a whole pixel, instead of waking every frame", () => {
  assert.match(SRC, /const LIVE_MIN_PX = 1;/);
  assert.match(SRC, /_liveWaitMs\(\) \{[\s\S]*?const pxPerSec = g\.plotW \/ g\.winSec;/);
  assert.match(SRC, /_sleep\(ms\) \{\n\s*this\._liveTO = setTimeout\(\(\) => \{ this\._liveTO = null; this\._liveRAF = requestAnimationFrame\(\(\) => this\._tickLive\(\)\); \}, ms\);/);
  assert.match(SRC, /this\._sleep\(this\._liveWaitMs\(\)\);/);
  assert.match(SRC, /_stopLiveTick\(\) \{[\s\S]*?clearTimeout\(this\._liveTO\)/, "stopping the loop clears the sleep too");
  assert.match(SRC, /_startLiveTick\(\) \{[\s\S]*?if \(this\._liveRAF != null\) return;[\s\S]*?if \(this\._liveTO != null\) \{ clearTimeout\(this\._liveTO\); this\._liveTO = null; \}/,
    "a restart re-paces a pending sleep (a zoom or a frame changed the geometry) but never doubles an imminent look");
});

test("the live wait is bounded and scales with the zoom", () => {
  const m = /  _liveWaitMs\(\) \{([\s\S]*?)\n  \}/.exec(SRC);
  assert.ok(m, "the pacing helper exists");
  const LIVE_MIN_PX = 1;
  const fn = new Function("LIVE_MIN_PX", "return function(){" + m![1] + "}")(LIVE_MIN_PX) as () => number;
  const at = (winSec: number, plotW: number) => fn.call({ _geom: { winSec, plotW } });
  assert.equal(at(3600, 450), 2000, "a one-hour window over 450 px: capped at two seconds between looks");
  assert.equal(at(600, 900), 667, "a ten-minute window over 900 px: two thirds of a second");
  assert.equal(at(60, 1800), 100, "zoomed right in: never faster than ten looks a second");
  assert.equal(fn.call({ _geom: null }), 1000, "no geometry yet: a plain second");
});

// (A skeleton and its bars frame are two draws: update()/applyBars() draw synchronously while the pane can be
// seen, which the view's tests rely on — out of sight they hold to one catch-up, timeline-hidden-hold.test.ts.
// The kernel stops re-sending an unchanged skeleton instead — tests/test_timeline_skeleton_dedup.py — so in
// steady state only the bars frame lands, and only when it changed.)

test("the prompt-dot pass indexes processed messages by recipient instead of scanning them per turn", () => {
  assert.doesNotMatch(SRC, /data\.messages\.some\(\(mm\) => mm\.toId === s\.id && !mm\.pending/);
  assert.match(SRC, /const execByTo = new Map\(\);[\s\S]*?execByTo\.forEach\(\(a\) => a\.sort\(\(p, q\) => p - q\)\);[\s\S]*?const execNear = \(sid, t\) => sortedHasWithin\(execByTo\.get\(sid\), t, 1\);/);
  assert.match(SRC, /if \(execNear\(s\.id, startAt\(t\)\)\) return;/);
});

test("sortedHasWithin answers the ±1 s question exactly", () => {
  const m = /function sortedHasWithin\(arr, t, tol\) \{[\s\S]*?\n\}/.exec(SRC);
  assert.ok(m);
  const f = new Function(m![0] + "; return sortedHasWithin;")() as (a: number[] | undefined, t: number, tol: number) => boolean;
  assert.equal(f(undefined, 5, 1), false);
  assert.equal(f([], 5, 1), false);
  assert.equal(f([1, 4, 9], 5, 1), true, "4 is within one second of 5");
  assert.equal(f([1, 4, 9], 6.5, 1), false, "nothing within one second of 6.5");
  assert.equal(f([1, 4, 9], 10, 1), true, "the last element counts");
  assert.equal(f([1, 4, 9], 0, 1), true, "the first element counts");
  assert.equal(f([1, 4, 9], -1.5, 1), false);
  assert.equal(f([2.9], 4.0, 1), false, "1.1 apart: outside");
  assert.equal(f([3.0], 4.0, 1), true, "exactly one apart: inside, as Math.abs(a-b) <= 1 was");
  // brute-force parity with the scan it replaces
  const xs = [0.5, 1.7, 1.9, 8, 8.2, 20, 33.3].sort((a, b) => a - b);
  for (let t = -2; t < 40; t += 0.37) assert.equal(f(xs, t, 1), xs.some((v) => Math.abs(v - t) <= 1), "t=" + t);
});

test("a hidden pane stops the loop (the paint hold's release re-arms it); a held pointer yields to the release event", () => {
  const tick = /  _tickLive\(\) \{([\s\S]*?)\n  \}/.exec(SRC)![1];
  // 2026-09-07: the old 2 s sleep re-entered _isVisible()'s forced layout every wake for a pane nobody could
  // see; the loop now stops and _releasePaintHold re-arms it on visibilitychange / the pane's observer.
  assert.match(tick, /if \(!this\._isVisible\(\)\) return;/);
  assert.doesNotMatch(tick, /_sleep\(2000\)/);
  assert.match(tick, /if \(this\._pointerHeld\) \{ this\._liveResume = true; return; \}/);
  assert.match(SRC, /if \(this\._liveResume\) \{ this\._liveResume = false; this\._startLiveTick\(\); \}/, "_release restarts it");
  assert.match(SRC, /this\._liveRAF = null; this\._liveTO = null; this\._liveResume = false;/, "the constructor knows every handle");
});

test("a bars frame re-anchors the live edge, and the glide cap outlasts the kernel's 60 s repost", () => {
  const bars = /  _mergeBars\(m\) \{([\s\S]*?)\n  \}/.exec(SRC)![1];   // the state half of applyBars (2026-09-07)
  assert.match(bars, /this\._anchorNow\(this\.data\.now\);/);
  assert.match(SRC, /_anchorNow\(sample\) \{[\s\S]*?reanchorEdge\(this\._nowBaseSec, this\._nowBaseMs, tMs, sample, this\._wasLive\)/);
  const cap = Number(/const MAX_INTERP_AHEAD = (\d+);/.exec(SRC)![1]);
  assert.ok(cap >= 120, "the edge must be able to glide through a whole repost interval: got " + cap);
  // the pure functions, extracted and run: a 61 s silence neither stalls the edge nor makes it jump
  const consts = "const MAX_INTERP_AHEAD = " + cap + "; const REANCHOR_SEC = " + /const REANCHOR_SEC = ([\d.]+);/.exec(SRC)![1] + ";";
  const fi = /function interpNow\([\s\S]*?\n\}/.exec(SRC)![0];
  const fr = /function reanchorEdge\([\s\S]*?\n\}/.exec(SRC)![0];
  const { interpNow, reanchorEdge } = new Function(consts + fi + fr + "; return { interpNow, reanchorEdge };")();
  assert.equal(interpNow(1000, 0, 61000, true, cap), 1061, "still gliding after 61 s");
  assert.equal(interpNow(1000, 0, 61000, true, 30), 1030, "…where the old 30 s cap had frozen it at +30");
  const a = reanchorEdge(1000, 0, 61000, 1061, true);
  assert.equal(a.baseSec, 1061, "the repost's sample matches the displayed edge: no jump");
});

// ── the panel on the DOM shim: the translate tick (2026-09-06) ─────────────────────────────────────
const makeNode = nodeFactory({ rect: { width: 1400, height: 420, left: 0, top: 0, right: 1400, bottom: 420 } });
let created = 0;   // every element the view creates: a full draw() makes hundreds, a tick must make none
const g: any = global;
g.document = {
  createElement(t: string) { created++; return t === "canvas" ? { getContext() { return { font: "", measureText(s: string) { return { width: (s ? s.length : 0) * 6 }; } }; } } : makeNode(t); },
  createElementNS(_n: any, t: string) { created++; return makeNode(t); },
  body: makeNode("body"), documentElement: makeNode("html"), head: makeNode("head"),
  getElementById() { return null; },
  addEventListener() {}, removeEventListener() {},
  elementFromPoint() { return null; },
};
g.localStorage = { getItem() { return null; }, setItem() {}, removeItem() {} };
g.getComputedStyle = () => ({ backgroundColor: "rgb(30,30,30)" });
g.requestAnimationFrame = () => 0;
g.cancelAnimationFrame = () => {};
g.addEventListener = () => {}; g.removeEventListener = () => {};
g.matchMedia = () => ({ matches: false, addEventListener() {}, addListener() {} });
g.window = g;
g.innerWidth = 1400; g.innerHeight = 800;

const viewPath = path.resolve(process.cwd(), "..", "ui", "romp-timeline-view.js");
const { TimelinePanel } = createRequire(__filename)(viewPath);

const NOW = 1_781_000_000;
const SID1 = "11111111-2222-3333-4444-aaaaaaaaaaa1", SID2 = "11111111-2222-3333-4444-aaaaaaaaaaa2";
function turn(id: string, start: number, end: number, extra: any = {}) {
  return { id, promptId: id + "#p", workId: id + "#w", start, end, prompt: "do the thing", src: "typed", mids: [],
           pending: false, summary: "did the thing", reply: "did it", tid: "fork-" + id, uuid: "u-" + id, workUuid: "w-" + id, replyUuid: "r-" + id, ...extra };
}
function sess(id: string, name: string, state: string) {
  return { id, name, color: "#7aa2f7", state, live: true, model: "Opus 4.8", effort: "xhigh", context: 40, since: NOW - 60,
           awaiting: [], compacting: [], pendingMail: 0, compactions: [], faded: false, stale: false };
}
/** Two lanes: web has an OPEN turn (its bar ends at the live edge), api a closed one. */
function liveData(): any {
  return {
    now: NOW,
    sessions: [sess(SID1, "web", "working"), sess(SID2, "api", "idle")],
    turns: { [SID1]: [turn("a", NOW - 900, NOW - 700), turn("b", NOW - 300, NOW, { open: true })], [SID2]: [turn("c", NOW - 600, NOW - 400)] },
    messages: [], judging: [], activeChat: null, focus: null, hover: null, usage: null,
  };
}
/** A panel following the live edge, built once; `advance` moves its clock by `sec` for the next tick. */
function livePanel(data: any, winSec: number): any {
  const panel: any = new TimelinePanel(makeNode("div"));
  panel._lockNow = true; panel._pinned = true;
  panel._winSec = winSec; panel.fitted = true;
  panel.update(data);
  assert.ok(panel._liveFollowing(), "the panel follows the live edge");
  assert.ok(panel._tickPlot, "a full build leaves the tick its handle");
  return panel;
}
const advance = (panel: any, sec: number) => { panel._nowBaseMs = performance.now() - sec * 1000; };
const plotOf = (panel: any) => panel._tickPlot.g;
const widthOf = (el: any) => Number(el.getAttribute("width"));

test("a tick moves the plot group by a transform and creates no element; the open bar's width rides the edge", () => {
  const panel = livePanel(liveData(), 3600);
  const tp = panel._tickPlot, geom0 = { ...panel._geom };
  const openBar = tp.riders.find((r: any) => r.el.tag === "rect" && r.attr === "width");
  assert.ok(openBar, "the open bar registered as a live-edge rider");
  const w0 = widthOf(openBar.el);
  const closedBar = plotOf(panel).children.find((c: any) => c.tag === "rect" && c._attrs.fill === "#7aa2f7" && widthOf(c) !== w0 && !tp.riders.some((r: any) => r.el === c));
  assert.ok(closedBar, "a closed bar is in the plot group and is not a rider");
  const cw0 = widthOf(closedBar);
  advance(panel, 3);
  const before = created;
  panel._tickLive();
  assert.equal(created, before, "the tick created no element: no rebuild");
  // the build itself stood a few ms past data.now (its own interpolation), so the drift is 3 s less that
  const px = tp.applied, want = 3 / geom0.winSec * geom0.plotW;
  assert.ok(px >= 0.15 && Math.abs(px - want) < 0.01, "the edge moved about 3 s worth of pixels: " + px + " vs " + want);
  assert.equal(plotOf(panel).getAttribute("transform"), "translate(" + (-px) + " 0)", "one translate on the plot group");
  assert.equal(widthOf(openBar.el), w0 + px, "the open bar grew by the drift: its right edge stays at the live now");
  assert.equal(widthOf(closedBar), cw0, "a closed bar's geometry is untouched");
  assert.ok(Math.abs((panel._geom.t1 - geom0.t1) - px / tp.k) < 1e-6, "the window geometry the handlers read follows the move");
  assert.equal(panel._geom.plotW, geom0.plotW);
  assert.equal(panel._holdReal, panel._geom.t1);
});

test("a move under TICK_MIN_PX writes nothing; the translate is measured from the build, not the last tick", () => {
  const panel = livePanel(liveData(), 43200);   // 12 h: 0.1 s is far under a pixel
  advance(panel, 0.1);
  const before = created;
  panel._tickLive();
  assert.equal(created, before);
  assert.equal(plotOf(panel).getAttribute("transform"), undefined, "nothing to write yet");
  advance(panel, 30);   // the interpolation cap; the movement is now well past the guard
  panel._tickLive();
  const px = panel._tickPlot.applied, want = 30 / panel._geom.winSec * panel._geom.plotW;
  assert.ok(px > 0.15 && Math.abs(px - want) < 0.01, "about 30 s worth: " + px + " vs " + want);
  assert.equal(plotOf(panel).getAttribute("transform"), "translate(" + (-px) + " 0)");
});

test("a message glyph riding the live edge leaves the tick its full draw (a translate cannot express it)", () => {
  const data = liveData();
  data.messages = [{ id: "m1", fromId: SID2, toId: SID1, from: "api", to: "web", sent: NOW - 100, exec: NOW - 100, pending: true, text: "please review" }];
  const panel: any = new TimelinePanel(makeNode("div"));
  panel._lockNow = true; panel._pinned = true; panel._winSec = 3600; panel.fitted = true;
  panel.update(data);
  assert.equal(panel._tickPlot, null, "the pending message's dot lands AT the live edge, so the build hands the tick no translate handle");
  // with no handle the loop is paced as a rebuild must be (2026-09-04): under a whole pixel of movement
  // (LIVE_MIN_PX) it draws nothing and sleeps until the edge could have moved that far…
  const g0 = panel._geom, pxOf = (sec: number) => sec / g0.winSec * g0.plotW;
  advance(panel, 3);
  assert.ok(pxOf(3) < 1, "3 s at a one-hour window is under a pixel: " + pxOf(3));
  let before = created;
  try {
    panel._tickLive();
    assert.equal(created, before, "under LIVE_MIN_PX: no rebuild yet");
    assert.ok(panel._liveTO != null, "…and the next look is a sleep, not an animation frame");
    // …and once the edge has moved a whole pixel it falls back to the full draw a translate cannot replace
    advance(panel, 1.5 * g0.winSec / g0.plotW);
    before = created;
    panel._tickLive();
    assert.ok(created > before, "the tick fell back to a full draw");
    assert.equal(panel._tickPlot, null, "the rider is still at the edge: still no handle, so the loop stays paced");
    assert.ok(panel._liveTO != null, "paced again after the draw");
  } finally { panel._stopLiveTick(); }   // the sleep is a real timer on the runner; the loop is not under test past here
});

test("a drift reaching the gutter gap hands the tick back to a full draw (no frame has rebuilt since the build)", () => {
  const panel = livePanel(liveData(), 60);   // 1 min window: 3 s is tens of pixels
  const tp = panel._tickPlot;
  assert.ok(tp.maxDrift >= 2 && tp.maxDrift < 10, "the cap is the gutter gap, a few px");
  advance(panel, 3);
  const before = created;
  panel._tickLive();
  assert.ok(created > before, "the drift would have poked clamped content into the battery column: a full draw instead");
  assert.ok(panel._tickPlot, "the rebuild leaves a fresh handle");
  assert.equal(panel._tickPlot.applied, 0);
});

test("inside a collapsed trailing gap the edge does not move on screen: the tick writes nothing and redraws nothing", () => {
  // every lane quiet for longer than GAP_MIN (20 min): _buildCompressMap appends a trailing gap whose compressed
  // width is fixed, so compress(now) is constant while now advances — the old real-seconds guard redrew anyway
  const data = liveData();
  data.sessions[0].state = "idle";
  data.turns = { [SID1]: [turn("a", NOW - 5000, NOW - 4000)], [SID2]: [turn("c", NOW - 4800, NOW - 4500)] };
  const panel = livePanel(data, 7200);
  assert.equal(panel._tickPlot.trailing, true, "the build saw the trailing gap");
  advance(panel, 5);
  const before = created;
  panel._tickLive();
  assert.equal(created, before, "no rebuild");
  assert.equal(plotOf(panel).getAttribute("transform"), undefined, "no translate: compressed movement is zero");
});

test("an open awaiting span and an open judging run ride the edge too; the lane chrome stays out of the plot group", () => {
  const data = liveData();
  data.sessions[1].state = "needsInput"; data.sessions[1].since = NOW - 120;   // an open blocked stripe on api, to the live edge
  data.judging = [{ sid: SID1, judge: "closer", t: NOW - 30, t1: NOW - 30, open: true, kind: "k", text: "" }];
  const getItem = g.localStorage.getItem;
  g.localStorage.getItem = (k: string) => (k === "romp:settings" ? JSON.stringify({ showTriageJudges: true }) : null);   // the band is off by default
  const panel: any = new TimelinePanel(makeNode("div"));
  panel._lockNow = true; panel._pinned = true; panel._winSec = 3600; panel.fitted = true;
  try { panel.update(data); } finally { g.localStorage.getItem = getItem; }
  const tp = panel._tickPlot;
  assert.ok(tp, "no live-edge message: the handle exists");
  const kinds = tp.riders.map((r: any) => r.el.tag + ":" + r.attr + ":" + (r.el._attrs["data-judge"] || r.el._attrs.fill || ""));
  assert.ok(kinds.some((k: string) => k.startsWith("rect:width:url(#vault-await-hatch)")), "the awaiting stripe is a rider: " + kinds.join(", "));
  assert.ok(tp.riders.some((r: any) => r.el._attrs["data-judge"] === "closer"), "the open judging run is a rider");
  // the gutter chrome and the rows' hit rects are on the svg itself, not in the moving group
  const plotTags = new Set(plotOf(panel).children.map((c: any) => c.tag));
  const names = panel.svg.children.filter((c: any) => c.tag === "text" && (c.textContent === "web" || c.textContent === "api"));
  assert.equal(names.length, 2, "lane names are direct svg children (fixed)");
  assert.ok(!plotOf(panel).children.some((c: any) => c.tag === "text" && (c.textContent === "web" || c.textContent === "api")), "and not in the plot group");
  assert.ok(plotTags.has("rect") && plotTags.has("line"), "bars and axis gridlines are in the plot group");
  const idx = panel.svg.children.indexOf(plotOf(panel));
  const rowHit = panel.svg.children.findIndex((c: any) => c.tag === "rect" && c._attrs.fill === "transparent" && c._attrs.x === 0);
  assert.ok(rowHit >= 0 && rowHit < idx, "the plot group paints over the rows' hit rects (a bar must take the hover)");
});

test("a glyph anchored near the left edge hides once its anchor crosses it (where a full draw culls it), so no dot drifts onto the battery column", () => {
  // a 10-minute window at 1400 px: about 2 px a second, a 9 px drift cap (the battery column's gap). The closed turn
  // on api starts 0.6 s inside the left edge: its prompt dot (DOT_R 6) already overhangs the edge by about 5 px at
  // build time, and translated by the cap it would paint 3-4 px over the battery and take its /compact pointer.
  const data = liveData();
  data.turns = { [SID1]: [turn("a", NOW - 300, NOW - 100)], [SID2]: [turn("c", NOW - 599.4, NOW - 500)] };
  const panel = livePanel(data, 600);
  const tp = panel._tickPlot, g = panel._geom;
  const bat = panel.svg.children.find((c: any) => c.tag === "rect" && c._attrs.width === 48 && c._attrs.height === 14 && c._attrs.fill !== "transparent");
  assert.ok(bat, "the lanes carry a context battery, so the gap left of the plot is COLGAP");
  const batRight = bat._attrs.x + 48;
  assert.equal(tp.maxDrift, 9);
  assert.equal(tp.left, g.ml);
  const dots = plotOf(panel).children.filter((c: any) => c.tag === "circle");
  const edgeDot = dots.reduce((a: any, b: any) => (a._attrs.cx < b._attrs.cx ? a : b));
  const farDot = dots.reduce((a: any, b: any) => (a._attrs.cx > b._attrs.cx ? a : b));
  const inside = edgeDot._attrs.cx - g.ml;
  assert.ok(inside > 0 && inside < 2, "the edge dot's anchor sits about 0.6 s inside the plot: " + inside + " px");
  assert.ok(tp.edge.some((e: any) => e.el === edgeDot), "the build listed it as an edge glyph");
  assert.ok(!tp.edge.some((e: any) => e.el === farDot), "a dot well inside the window is not listed");
  const paintedLeft = (dot: any) => dot._attrs.cx - tp.applied - 6;   // the dot's left edge on screen: anchor, less the translate, less DOT_R
  // a small drift, the anchor still inside the plot: visible, and its overhang still short of the battery
  advance(panel, inside / 2 / tp.k);
  let before = created; panel._tickLive();
  assert.equal(created, before, "no rebuild");
  assert.ok(tp.applied > 0 && tp.applied < inside, "applied " + tp.applied);
  assert.equal(edgeDot.getAttribute("visibility"), undefined, "anchor inside: visible");
  assert.ok(paintedLeft(edgeDot) >= batRight, "and off the battery column");
  // just under the cap: the anchor has crossed the edge, so the dot is hidden, exactly where a full draw drops it
  advance(panel, (tp.maxDrift - 0.3) / tp.k);
  before = created; panel._tickLive();
  assert.equal(created, before, "still no rebuild: the drift is under the cap");
  assert.ok(tp.applied > tp.maxDrift - 1 && tp.applied < tp.maxDrift, "applied " + tp.applied);
  assert.equal(edgeDot.getAttribute("visibility"), "hidden", "the dot whose anchor crossed the edge is hidden (and takes no pointer)");
  assert.ok(edgeDot.getAttribute("visibility") === "hidden" || paintedLeft(edgeDot) >= batRight, "its painted left edge never reaches the battery");
  assert.equal(farDot.getAttribute("visibility"), undefined, "a dot inside the window stays");
});

test("a rider's floor applies to the grown extent: a just-opened bar grows as a full draw draws it, and a narrow judging run stays centred only until it is wider than JMARK_MINW", () => {
  const data = liveData();
  data.turns[SID1] = [turn("a", NOW - 300, NOW - 100), turn("b", NOW, NOW, { open: true })];   // opened this instant: drawn at the 2 px floor
  data.judging = [{ sid: SID1, judge: "closer", t: NOW, t1: NOW, open: true, kind: "k", text: "" }];
  const getItem = g.localStorage.getItem;
  g.localStorage.getItem = (k: string) => (k === "romp:settings" ? JSON.stringify({ showTriageJudges: true }) : null);
  const panel: any = new TimelinePanel(makeNode("div"));
  panel._lockNow = true; panel._pinned = true; panel._winSec = 600; panel.fitted = true;
  try { panel.update(data); } finally { g.localStorage.getItem = getItem; }
  const tp = panel._tickPlot;
  assert.ok(tp, "the handle exists");
  const bar = tp.riders.find((r: any) => r.el.tag === "rect" && r.attr === "width" && r.el._attrs.fill === "#7aa2f7");
  assert.ok(bar && bar.min === 2 && bar.base >= 0 && bar.base < 0.1, "the open bar's rider carries its un-clamped extent and the floor: " + JSON.stringify({ base: bar && bar.base, min: bar && bar.min }));
  assert.equal(widthOf(bar.el), 2, "drawn at the floor");
  const run = tp.riders.find((r: any) => r.el._attrs["data-judge"] === "closer");
  assert.ok(run && run.fn && run.base >= 0 && run.base < 0.1, "the open run's rider re-derives its placement from the un-centred extent");
  assert.equal(widthOf(run.el), 6, "drawn centred at JMARK_MINW");
  assert.ok(Math.abs(run.el._attrs.x - (run.x0 + (run.base - 6) / 2)) < 1e-9, "the build's centring");
  // a drift under the floor: the bar stays at 2 px (a full draw would also draw max(2, 1.2)); the run stays centred and its centre moves by half the drift
  advance(panel, 1.2 / tp.k);
  panel._tickLive();
  assert.ok(tp.applied > 1 && tp.applied < 1.3, "applied " + tp.applied);
  assert.equal(widthOf(bar.el), 2, "the floor holds: not 2 + the drift");
  assert.equal(widthOf(run.el), 6, "still narrower than JMARK_MINW: still centred");
  assert.ok(Math.abs(run.el._attrs.x - (run.x0 + (run.base + tp.applied - 6) / 2)) < 1e-9, "centred on the grown extent, as a full draw places it");
  // past the floor: the true extent, as a full draw would draw it, and the run's centring is gone
  advance(panel, 7 / tp.k);
  panel._tickLive();
  assert.ok(tp.applied > 6.5 && tp.applied < 7.1 && tp.applied < tp.maxDrift, "applied " + tp.applied);
  assert.ok(Math.abs(widthOf(bar.el) - (bar.base + tp.applied)) < 1e-9, "the un-clamped extent plus the drift: " + widthOf(bar.el));
  assert.ok(widthOf(bar.el) < 2 + tp.applied - 1.5, "not the floor plus the drift");
  assert.ok(Math.abs(run.el._attrs.x - run.x0) < 1e-9 && Math.abs(widthOf(run.el) - (run.base + tp.applied)) < 1e-9, "the run starts at its own x and spans to the edge");
  const hit = tp.riders.find((r: any) => r.el === run.el);
  assert.ok(hit, "one rider carries both the run and its hit");
});

test("the focus pulse is drawn into the live plot group, in the group's frame, so it rides the tick with its target", () => {
  const panel = livePanel(liveData(), 3600);
  const plot = plotOf(panel);
  advance(panel, 3);
  panel._tickLive();
  assert.ok(panel._tickPlot.applied > 0, "the plot is translated");
  const n0 = plot.children.length;
  panel._pulseFocus(SID2, NOW - 600, null);   // api's closed turn c: a prompt focus rings its start dot
  const ring = plot.children[plot.children.length - 1];
  assert.equal(plot.children.length, n0 + 1, "the ring went into the plot group, not onto the svg");
  assert.ok(ring.tag === "circle" && ring._attrs.stroke === "#ffd166");
  const dotC = plot.children.find((c: any) => c.tag === "circle" && c !== ring && c._attrs.fill === "#7aa2f7" && Math.abs(c._attrs.cx - ring._attrs.cx) < 1e-6);
  assert.ok(dotC, "positioned in the build's frame: it sits on the prompt dot it rings (both then move by the translate)");
  panel._pulseFocus(SID1, NOW - 900, { t: NOW - 900, end: NOW - 700 });   // a work focus outlines the bar
  const box = plot.children[plot.children.length - 1];
  assert.ok(box.tag === "rect" && box._attrs.stroke === "#ffd166" && box.parentNode === plot);
  const barA = plot.children.filter((c: any) => c.tag === "rect" && c._attrs.fill === "#7aa2f7").reduce((a: any, b: any) => (a._attrs.x < b._attrs.x ? a : b));
  assert.ok(Math.abs((box._attrs.x + 3) - barA._attrs.x) < 1e-6, "the outline hugs the bar in the group's frame");
  // with no live group (the loader wiped the svg) the pulse goes on the svg as before
  panel.drawMessage("no lanes");
  panel._pulseFocus(SID2, NOW - 600, null);
  assert.equal(panel.svg.children[panel.svg.children.length - 1].parentNode, panel.svg);
});
