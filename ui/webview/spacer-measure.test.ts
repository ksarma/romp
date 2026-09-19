// The spacers' measurement, lifted from render.ts and executed (PR E, 2026-09-19): sizeSpacers writes the spacers from the
// view's figures and reads no layout property; measureUnits reads the unit observer's heights (v.uh) at frame end and parks
// the figures on the view; the next paint takes them (applyMeasure) and re-draws the gap units. Two defects this pins shut:
// the ORDER (build one drew the head gap at the 120 px default, the same call measured the window's whole height over its
// one user row, and build two drew the gap at that figure: 24k to 1.43M px in one second on the phone), and the FORCED
// LAYOUT (sizeSpacers read offsetHeight for every child right after the rebuild, and the scroller's scrollHeight for the
// diag row, inside the render task). A recording fake counts every layout read; the old code's count is the red before.
// The models-rev.test.ts / chat-exact-tail-exec.test.ts pattern: the span is transpiled with esbuild at run time.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { DEFAULT_TURN_PX, MAX_TURN_PX, gapHeight } from "./chat-regions";
import { spacerRow } from "./scroll-write";
import { meanRowHeight, perTurnEstimate, rowsFor } from "./turn-estimate";
import type { DisplayItem } from "./compact";
import { hideEdges } from "../test-dom-shim";

const requireCjs = createRequire(__filename);
const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");

function liftBetween(startAnchor: string, endAnchor: string): string {
  const a = RENDER.indexOf(startAnchor), b = RENDER.indexOf(endAnchor, a);
  assert.ok(a > 0 && b > a, `anchors not found: ${startAnchor.slice(0, 40)} or ${endAnchor.slice(0, 40)} moved; re-anchor`);
  return requireCjs("esbuild").transformSync(RENDER.slice(a, b), { loader: "ts" }).code;
}

/** The layout reads a paint must not make: every offsetHeight of a row, every scrollHeight / clientHeight of the scroller. */
type Reads = { offsetHeight: number; scrollHeight: number; clientHeight: number };

/** Enough of an element for the spacer code: a class list, data-*, inline style, children and the selectors it uses; offsetHeight
 *  is a RECORDING getter (the read counts, the value is the row's real height). */
class FakeEl {
  children!: FakeEl[]; parent: FakeEl | null = null; dataset: Record<string, string> = {}; style: Record<string, string> = { display: "" };
  constructor(public tag: string, public className = "", public realH = 0, private reads: Reads | null = null) {
    Object.defineProperty(this, "children", { value: [], writable: true, enumerable: false, configurable: true });
    hideEdges(this);
  }
  get offsetHeight(): number { if (this.reads) this.reads.offsetHeight++; return this.realH; }
  get classList() { const cls = this.className.split(/\s+/); return { contains: (c: string) => cls.includes(c) }; }
  get firstChild(): FakeEl | null { return this.children[0] ?? null; }
  get lastChild(): FakeEl | null { return this.children[this.children.length - 1] ?? null; }
  get nextSibling(): FakeEl | null { const p = this.parent; if (!p) return null; const i = p.children.indexOf(this); return i >= 0 ? p.children[i + 1] ?? null : null; }
  appendChild(c: FakeEl): FakeEl { c.parent?.removeChild(c); c.parent = this; this.children.push(c); return c; }
  insertBefore(c: FakeEl, ref: FakeEl | null): FakeEl { c.parent?.removeChild(c); c.parent = this; const i = ref ? this.children.indexOf(ref) : -1; if (i < 0) this.children.push(c); else this.children.splice(i, 0, c); return c; }
  removeChild(c: FakeEl): void { this.children = this.children.filter((x) => x !== c); c.parent = null; }
  private match(sel: string): FakeEl[] { const m = /^(?::scope > )?\.([\w-]+)$/.exec(sel); if (!m) throw new Error("unsupported selector " + sel); return this.children.filter((c) => c.classList.contains(m[1])); }
  querySelector(sel: string): FakeEl | null { return this.match(sel)[0] ?? null; }
  querySelectorAll(sel: string): FakeEl[] { return this.match(sel); }
}

type Diag = Array<{ kind: string; data: any }>;
type World = {
  reads: Reads; diag: Diag; rafs: Array<() => void>; views: Map<string, any>; activeId: string | null;
  sizeSpacers: (v: any) => void; measureUnits: (v: any) => void; applyMeasure: (v: any) => boolean; redrawGapUnits: (v: any) => void;
  gapUnitsOf: (items: DisplayItem[], per: number | undefined) => Map<number, number> | undefined; entryBoxHeight: (e: any) => number;
};
function lift(activeId: string | null): World {
  const js = liftBetween("function gapUnitsOf(", "function unitAtScroll(");
  const reads: Reads = { offsetHeight: 0, scrollHeight: 0, clientHeight: 0 };
  const diag: Diag = []; const rafs: Array<() => void> = []; const views = new Map<string, any>();
  const content = { get scrollHeight() { reads.scrollHeight++; return 9114; }, get clientHeight() { reads.clientHeight++; return 902; } };
  const hooks = { FakeEl, views, activeId, document: { getElementById: (id: string) => (id === "content" ? content : null) },
                  raf: (cb: () => void) => { rafs.push(cb); return rafs.length; }, diag: (kind: string, data: any) => diag.push({ kind, data }),
                  spacerRow, gapHeight, rowsFor, meanRowHeight, perTurnEstimate };
  const prelude = `
    const H = HOOKS;
    const HTMLElement = H.FakeEl;
    const el = (tag, cls) => new H.FakeEl(tag, cls || "");
    const views = H.views; const activeId = H.activeId; const document = H.document;
    const requestAnimationFrame = H.raf; const scrollDiagRow = H.diag; const spacerRow = H.spacerRow; const gapHeight = H.gapHeight;
    const rowsFor = H.rowsFor, meanRowHeight = H.meanRowHeight, perTurnEstimate = H.perTurnEstimate;
  `;
  const api = new Function("HOOKS", prelude + js + "\nreturn { sizeSpacers, measureUnits, applyMeasure, redrawGapUnits, gapUnitsOf, entryBoxHeight };")(hooks);
  return { reads, diag, rafs, views, activeId, ...api };
}

/** A view over `items` (a head gap as unit 0, then event units) rendered as the window [winStart, total): a top spacer, then one row per
 *  unit with the class and real height given by `rowOf(u)`. The observer's map (v.uh) starts EMPTY, as it is at build time. */
function viewOver(w: World, gapTurns: number, total: number, winStart: number, rowOf: (u: number) => [string, number]) {
  const items: DisplayItem[] = [{ kind: "gap", lo: 0, hi: gapTurns, before: 0 }];
  for (let u = 1; u < total; u++) items.push({ kind: "event", index: u - 1 });
  const host = new FakeEl("div");
  host.appendChild(new FakeEl("div", "tx-spacer tx-spacer-top", 0, w.reads));
  const rows: FakeEl[] = [];
  for (let u = winStart; u < total; u++) { const [cls, h] = rowOf(u); const n = new FakeEl("div", cls, h, w.reads); n.dataset.unit = String(u); host.appendChild(n); rows.push(n); }
  const v: any = { el: host, winStart, winEnd: total, spacerCount: winStart, spacerCountBot: 0, unitTotal: total, units: items, uh: new WeakMap<object, number>(), stick: true };
  return { v, items, rows, top: host.children[0] };
}
/** Build one, as renderWindowItems ends: the gap units at the current figure, then the spacers. */
const buildOne = (w: World, v: any, items: DisplayItem[]) => { w.applyMeasure(v); v.gapUnits = w.gapUnitsOf(items, v.pxPerTurn); w.sizeSpacers(v); v.measureDue = true; };
/** The observer's delivery: every row's border-box height lands in the map, then the measure. */
const observe = (w: World, v: any, rows: FakeEl[]) => { for (const r of rows) v.uh.set(r, r.realH); w.measureUnits(v); };
/** The next paint, as syncViewInner takes the figures. */
const paintTwo = (w: World, v: any) => { if (w.applyMeasure(v)) { w.redrawGapUnits(v); w.sizeSpacers(v); } };
const topPx = (v: any) => parseFloat(v.el.children[0].style.height);

// ── T3: the order ────────────────────────────────────────────────────────────────────────────────

test("the phone's window (one user row, 79 dense rows) over a 200-turn head gap: build two keeps build one's gap; the old formula drew it 60x", () => {
  const w = lift(null);
  const { v, items, rows } = viewOver(w, 200, 301, 221, (u) => (u === 221 ? ["turn turn-user", 40] : ["turn turn-assistant", 90]));
  buildOne(w, v, items);
  const gapOne = v.gapUnits.get(0), topOne = topPx(v);
  assert.equal(gapOne, 200 * DEFAULT_TURN_PX, "build one: the default per turn (24k px)");
  assert.equal(topOne, gapOne + 220 * 60, "…plus the hidden run units at the default average");
  observe(w, v, rows);
  assert.equal(v.pxPerTurn, undefined, "the figure waits for the paint");
  paintTwo(w, v);
  const gapTwo = v.gapUnits.get(0), topTwo = topPx(v);
  assert.equal(gapTwo, gapOne, "no complete turn in the window: the gap keeps the default, it is not measured off one user row");
  assert.equal(v.pxPerTurn, undefined, "…and nothing is cached");
  assert.equal(v.avgTurnH, (40 + 79 * 90) / 80, "the rows' average is taken (once per view)");
  assert.ok(topTwo / topOne < 2, "the spacer moved with the average alone: " + topOne + " -> " + topTwo);
  const oldFigure = (40 + 79 * 90) / 1;   // the whole window over its one user row
  assert.ok(gapHeight({ lo: 0, hi: 200 }, oldFigure) / gapOne >= 20, "the old figure would have drawn the gap at least 20x (the clamp's edge): " + gapHeight({ lo: 0, hi: 200 }, oldFigure));
  assert.ok(200 * oldFigure / gapOne > 55, "…and without the cap about 60x: " + (200 * oldFigure / gapOne));
});

test("a window with two complete turns measures their median; the gap units and the rendered gap element take it on the next paint", () => {
  const w = lift(null);
  // rows: a partial leading reply (500), then user 30 / reply 70, user 30 / reply 90, then the streaming turn user 30 / reply 900
  const shape: Array<[string, number]> = [["turn turn-assistant", 500], ["turn turn-user", 30], ["turn turn-assistant", 70], ["turn turn-user", 30], ["turn turn-assistant", 90], ["turn turn-user", 30], ["turn turn-assistant", 900]];
  const { v, items, rows } = viewOver(w, 200, 1 + 100 + shape.length, 101, (u) => shape[u - 101]);
  // a second gap, rendered inside the window, follows the rows (T386: a mid-transcript gap)
  const g = new FakeEl("div", "tx-gap", 0, w.reads); g.dataset.lo = "300"; g.dataset.hi = "310"; g.dataset.unit = String(items.length); v.el.appendChild(g);
  items.push({ kind: "gap", lo: 300, hi: 310, before: items.length - 1 }); v.unitTotal = items.length; v.winEnd = items.length;
  buildOne(w, v, items);
  g.style.height = gapHeight({ lo: 300, hi: 310 }, v.pxPerTurn) + "px";   // as gapElement draws it at build
  assert.equal(v.gapUnits.get(0), 200 * DEFAULT_TURN_PX); assert.equal(g.style.height, 10 * DEFAULT_TURN_PX + "px");
  observe(w, v, rows); paintTwo(w, v);
  assert.equal(v.pxPerTurn, 110, "the median of 100 and 120");
  assert.equal(v.gapUnits.get(0), 200 * 110, "the head gap at the measured figure");
  assert.equal(v.gapUnits.get(items.length - 1), 10 * 110, "the mid-transcript gap too");
  assert.equal(g.style.height, 10 * 110 + "px", "the rendered gap element follows without a rebuild");
  assert.equal(topPx(v), Math.round(200 * 110 + 100 * v.avgTurnH), "the spacer: the gap plus the hidden run units at the average");
});

test("a later build re-measures (not once): the figure follows the window's complete turns; a window with fewer than two keeps the last figure", () => {
  const w = lift(null);
  const two = (a: number, b: number): Array<[string, number]> => [["turn turn-user", 30], ["turn turn-assistant", a - 30], ["turn turn-user", 30], ["turn turn-assistant", b - 30], ["turn turn-user", 30], ["turn turn-assistant", 500]];
  const first = viewOver(w, 200, 1 + 100 + 6, 101, (u) => two(100, 120)[u - 101]);
  buildOne(w, first.v, first.items); observe(w, first.v, first.rows); paintTwo(w, first.v);
  assert.equal(first.v.pxPerTurn, 110);
  const avgFirst = first.v.avgTurnH;
  assert.ok(avgFirst! > 0, "the average was taken on the first build");
  // the same view, re-windowed over taller turns (a browse, a fill): build, observe, paint
  const v = first.v;
  while (v.el.children.length > 1) v.el.removeChild(v.el.lastChild!);
  const rows2: FakeEl[] = [];
  two(200, 220).forEach(([cls, h], i) => { const n = new FakeEl("div", cls, h, w.reads); n.dataset.unit = String(101 + i); v.el.appendChild(n); rows2.push(n); });
  buildOne(w, v, first.items); observe(w, v, rows2); paintTwo(w, v);
  assert.equal(v.pxPerTurn, 210, "re-measured on the later build");
  assert.equal(v.gapUnits.get(0), 200 * 210);
  assert.equal(v.avgTurnH, avgFirst, "the average is taken once per view: the taller rows did not move it");
  // …and a window with one complete turn leaves the figure where it was
  while (v.el.children.length > 1) v.el.removeChild(v.el.lastChild!);
  const rows3: FakeEl[] = [];
  ([["turn turn-user", 30], ["turn turn-assistant", 70], ["turn turn-user", 30], ["turn turn-assistant", 900]] as Array<[string, number]>).forEach(([cls, h], i) => { const n = new FakeEl("div", cls, h, w.reads); n.dataset.unit = String(101 + i); v.el.appendChild(n); rows3.push(n); });
  buildOne(w, v, first.items); observe(w, v, rows3);
  assert.equal(paintTwo(w, v), undefined); assert.equal(v.pxPerTurn, 210, "one complete turn: the figure stands");
  assert.equal(v.measured, undefined, "nothing waits");
});

test("the clamp is a backstop under the measured figure: turns of 5,000 px draw the gap at MAX_TURN_PX per turn", () => {
  const w = lift(null);
  const tall: Array<[string, number]> = [["turn turn-user", 200], ["turn turn-assistant", 4800], ["turn turn-user", 200], ["turn turn-assistant", 4800], ["turn turn-user", 200]];
  const { v, items, rows } = viewOver(w, 200, 1 + 100 + tall.length, 101, (u) => tall[u - 101]);
  buildOne(w, v, items); observe(w, v, rows); paintTwo(w, v);
  assert.equal(v.pxPerTurn, 5000, "the measured figure is kept as measured");
  assert.equal(v.gapUnits.get(0), 200 * MAX_TURN_PX, "…and drawn under the cap");
  assert.equal(MAX_TURN_PX, 20 * DEFAULT_TURN_PX);
});

// ── T4: no forced layout in the render task ──────────────────────────────────────────────────────

test("sizeSpacers and the measure read no layout property: zero offsetHeight, scrollHeight and clientHeight reads in the paint; the spacer row reads the scroller a frame later", () => {
  const w = lift("A");
  const { v, items, rows } = viewOver(w, 200, 301, 221, (u) => (u % 3 === 0 ? ["turn turn-user", 40] : ["turn turn-assistant", 90]));
  w.views.set("A", v);
  buildOne(w, v, items);
  assert.deepEqual(w.reads, { offsetHeight: 0, scrollHeight: 0, clientHeight: 0 }, "build one's spacer write read nothing");
  assert.equal(w.diag.length, 0, "the spacer row is not filed inside the paint");
  assert.equal(w.rafs.length, 1, "…it waits for the next animation frame");
  observe(w, v, rows); paintTwo(w, v);
  assert.deepEqual(w.reads, { offsetHeight: 0, scrollHeight: 0, clientHeight: 0 }, "the measure read the observer's map, the paint wrote the spacers: still nothing");
  assert.ok(v.pxPerTurn! > 0 && v.avgTurnH! > 0, "…and the figures were taken from the map: " + v.pxPerTurn + " / " + v.avgTurnH);
  const before = w.diag.length;
  w.rafs.shift()!();
  assert.equal(w.diag.length, before + 2, "the two writes' rows, filed together");
  assert.deepEqual(w.reads, { offsetHeight: 0, scrollHeight: 1, clientHeight: 1 }, "the scroller was read once, in the frame, for both rows");
  assert.deepEqual(w.diag.map((d) => [d.kind, d.data.sid, d.data.sh, d.data.ch]), [["spacer", "A", 9114, 902], ["spacer", "A", 9114, 902]]);
  assert.equal(w.diag[0].data.top[1], topPx(v) === w.diag[1].data.top[1] ? w.diag[0].data.top[1] : w.diag[0].data.top[1], "each row carries its own before/after");
  assert.ok(w.diag[0].data.top[1] !== w.diag[1].data.top[1], "the second write moved the spacer again (the measured figures)");
});

test("an inactive view's spacer write files no row, and a write that changes nothing files none", () => {
  const w = lift("B");   // the active view is another one
  const { v, items } = viewOver(w, 200, 301, 221, () => ["turn turn-assistant", 90]);
  buildOne(w, v, items);
  assert.equal(w.rafs.length, 0, "nothing queued for an inactive view");
  const w2 = lift("A");
  const world2 = viewOver(w2, 200, 301, 221, () => ["turn turn-assistant", 90]);
  w2.views.set("A", world2.v);
  buildOne(w2, world2.v, world2.items);
  w2.sizeSpacers(world2.v);
  assert.equal(w2.rafs.length, 1); w2.rafs[0]();
  assert.equal(w2.diag.length, 1, "the same height written twice files one row");
});

test("the observer's entry height is the border box (the height offsetHeight reports); contentRect is the fallback", () => {
  const w = lift(null);
  assert.equal(w.entryBoxHeight({ borderBoxSize: [{ blockSize: 33, inlineSize: 400 }], contentRect: { height: 19 } }), 33, "the array shape (the spec)");
  assert.equal(w.entryBoxHeight({ borderBoxSize: { blockSize: 33, inlineSize: 400 }, contentRect: { height: 19 } }), 33, "the object shape (older engines)");
  assert.equal(w.entryBoxHeight({ contentRect: { height: 19 } }), 19, "no box sizes: the content box");
  assert.equal(w.entryBoxHeight({}), 0);
});

// ── source pins on what the harness does not lift ────────────────────────────────────────────────

test("render.ts: the render task's spacer code holds no layout read; the unit observer records border-box heights and measures in both of its branches", () => {
  const code = (s: string) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/[^\n]*/g, "");   // the code alone: the comments name the reads that are gone
  const span = RENDER.slice(RENDER.indexOf("function gapUnitsOf("), RENDER.indexOf("function unitAtScroll("));
  const inFrame = span.slice(span.indexOf("function queueSpacerRow("), span.indexOf("// The window's two figures"));
  const paintSide = code(span.replace(inFrame, ""));
  assert.ok(paintSide.includes("function sizeSpacers(v") && paintSide.includes("function measureUnits(v") && paintSide.includes("function applyMeasure(v"), "the span holds the paint-side functions");
  assert.doesNotMatch(paintSide, /offsetHeight|scrollHeight|clientHeight|getBoundingClientRect|offsetTop/, "sizeSpacers, the trim, the eviction, the measure and the apply read no layout property");
  assert.match(inFrame, /requestAnimationFrame\(\(\) => \{[\s\S]*?const sh = content \? content\.scrollHeight : 0, ch = content \? content\.clientHeight : 0;/, "the diag row's scroller read rides a frame");
  const uo = RENDER.slice(RENDER.indexOf("v.uo = new ResizeObserver((entries) => {"), RENDER.indexOf("v.mo = new MutationObserver("));
  assert.match(uo, /unitHeights\.set\(e\.target, entryBoxHeight\(e\)\); view3\.measureDue = true; measureUnits\(view3\); return; \}/, "a reflow records border boxes and re-measures");
  assert.match(uo, /height: entryBoxHeight\(e\) \}\)\), view3\.el\.children, unitHeights, unitOf\);\s*\n\s*measureUnits\(view3\);/, "…and so does every delivery");
  assert.match(RENDER, /if \(applyMeasure\(v\)\) \{ redrawGapUnits\(v\); sizeSpacers\(v\); \}/, "syncViewInner takes the figures inside the paint");
  assert.match(RENDER, /function renderWindowItems\([^\n]*\n\s*applyMeasure\(v\);/, "a window build takes them first");
  assert.match(RENDER, /if \(applyMeasure\(v\)\) redrawGapUnits\(v\);\s*\/\/[^\n]*\n\s*sizeSpacers\(v\);/, "landActive takes them on show");
  assert.match(RENDER, /import \{ rowsFor, meanRowHeight, perTurnEstimate \} from "\.\/turn-estimate";/);
  assert.match(RENDER, /interface View \{[^\n]*measured\?: \{ avg\?: number; per\?: number \};/, "the parked figures live on the view");
});
