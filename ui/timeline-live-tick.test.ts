// The live tick as a transform write (2026-09-06). While the timeline follows the live edge, a rAF loop
// (_tickLive) advanced the clock by wiping and rebuilding the whole svg every time the edge moved 0.15 px:
// about 30 ms a draw, twice a second at a one-hour window and up to sixteen times a second at ten minutes
// (the pane's largest cost while visible, and invisible to every handler bracket). draw() now puts every
// time-positioned element in one plot group, and the tick writes one translate on that group plus a width on
// each element whose right edge rides the live now (an open bar, an open awaiting or compacting span, an
// open judging run); a full draw() stays only for what a translate cannot express. Headless, on the DOM shim
// timeline-render.test.ts uses: the shim counts element creation, so a rebuild is observable.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as path from "node:path";
import { createRequire } from "node:module";

function makeNode(tag: string): any {
  const n: any = {
    tag, _attrs: {}, children: [] as any[], style: {}, dataset: {}, textContent: "", parentNode: null,
    classList: { _s: new Set<string>(), add(...a: string[]) { a.forEach((c) => this._s.add(c)); },
      remove(...a: string[]) { a.forEach((c) => this._s.delete(c)); },
      toggle(c: string, f?: boolean) { f ? this._s.add(c) : this._s.delete(c); }, contains(c: string) { return this._s.has(c); } },
    setAttribute(k: string, v: any) { this._attrs[k] = v; }, getAttribute(k: string) { return this._attrs[k]; },
    setAttributeNS(_n: any, k: string, v: any) { this._attrs[k] = v; }, removeAttribute(k: string) { delete this._attrs[k]; },
    appendChild(c: any) { c.parentNode = n; this.children.push(c); return c; },
    insertBefore(c: any, ref: any) { c.parentNode = n; const i = this.children.indexOf(ref); i < 0 ? this.children.push(c) : this.children.splice(i, 0, c); return c; },
    removeChild(c: any) { const i = this.children.indexOf(c); if (i >= 0) { this.children.splice(i, 1); c.parentNode = null; } return c; },
    get firstChild() { return this.children[0] || null; },
    addEventListener() {}, removeEventListener() {}, querySelector() { return null; }, querySelectorAll() { return []; },
    getBoundingClientRect() { return { width: 1400, height: 420, left: 0, top: 0, right: 1400, bottom: 420 }; },
    closest() { return null; }, focus() {},
    createEl(t: string, o: any) { const e = makeNode(t); if (o && o.cls) e.classList.add(o.cls); if (o && o.text) e.textContent = o.text; this.appendChild(e); return e; },
    createDiv(o: any) { return this.createEl("div", o); }, createSpan(o: any) { return this.createEl("span", o); },
  };
  return n;
}
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

test("a move under LIVE_MIN_PX writes nothing; the translate is measured from the build, not the last tick", () => {
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
  advance(panel, 3);
  const before = created;
  panel._tickLive();
  assert.ok(created > before, "the tick fell back to a full draw");
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
