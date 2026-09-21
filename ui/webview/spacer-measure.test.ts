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
import { spacerRow, unitChanges } from "./scroll-write";
import { meanRowHeight, perTurnEstimate, rowsFor } from "./turn-estimate";
import type { DisplayItem } from "./compact";
import { hideEdges } from "../test-dom-shim";
import * as ts from "typescript";

const requireCjs = createRequire(__filename);
const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");

/** The source with its comments removed and nothing else: the comment ranges are the compiler's own (every token's leading and trailing
 *  trivia over the parsed file), so a `//` or a `/*` inside a string, a template or a regular expression is text, never a comment. The
 *  regex stripper this replaces (review round 3) cut a line at the `//` of a quoted URL, which hid an alias written after it on the same
 *  line from the bare-reference census below, opened a block comment at a quoted glob (`"image/*"`) and swallowed the code to the next
 *  `*\/`, and cut `u.replace(/^file:\/\//, "")` at the regular expression's slashes. The writer census (writer-census.ts) reads render.ts
 *  the same way for the same reason. */
function codeOf(src: string): string {
  const sf = ts.createSourceFile("render.ts", src, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
  const cut: Array<[number, number]> = [];
  const walk = (n: ts.Node): void => {
    for (const r of ts.getLeadingCommentRanges(src, n.getFullStart()) ?? []) cut.push([r.pos, r.end]);
    for (const r of ts.getTrailingCommentRanges(src, n.getEnd()) ?? []) cut.push([r.pos, r.end]);
    for (const c of n.getChildren(sf)) walk(c);
  };
  walk(sf);
  cut.sort((a, b) => a[0] - b[0]);
  let out = "", at = 0;
  for (const [p, e] of cut) { if (p < at) continue; out += src.slice(at, p); at = e; }
  return out + src.slice(at);
}

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
type Writes = Array<{ top: number; writer: string; stick: boolean }>;
type World = {
  reads: Reads; diag: Diag; rafs: Array<() => void>; views: Map<string, any>; activeId: string | null; writes: Writes; content: { scrollTop: number; ch: number }; paints: number;
  sizeSpacers: (v: any) => void; measureUnits: (v: any) => void; applyMeasure: (v: any) => boolean; redrawGapUnits: (v: any) => void; takeMeasureAtBottom: (v: any) => void; forgetAverage: (v: any) => void;
  setActive: (id: string | null) => void;   // the lifted span's own activeId (a tab switch between a queued spacer row and its frame)
  gapUnitsOf: (items: DisplayItem[], per: number | undefined) => Map<number, number> | undefined; entryBoxHeight: (e: any) => number;
};
/** The scroller: 9,114 px tall in a 902 px viewport; `scrollTop` starts at the bottom unless a world says otherwise. Every layout read counts.
 *  `paints` counts the appendActive paints the frame-end take asks for (scheduleAppendActive). */
function lift(activeId: string | null, scrollTop = 9114 - 902): World {
  const js = liftBetween("function gapUnitsOf(", "function unitAtScroll(");
  const reads: Reads = { offsetHeight: 0, scrollHeight: 0, clientHeight: 0 };
  const diag: Diag = []; const rafs: Array<() => void> = []; const views = new Map<string, any>(); const writes: Writes = [];
  const content = { scrollTop, ch: 902, get scrollHeight() { reads.scrollHeight++; return 9114; }, get clientHeight() { reads.clientHeight++; return this.ch; } };
  const world: any = { reads, diag, rafs, views, activeId, writes, content, paints: 0 };
  const hooks = { FakeEl, views, activeId, document: { getElementById: (id: string) => (id === "content" ? content : null) },
                  raf: (cb: () => void) => { rafs.push(cb); return rafs.length; }, diag: (kind: string, data: any) => diag.push({ kind, data }),
                  spacerRow, gapHeight, rowsFor, meanRowHeight, perTurnEstimate,
                  atBottom: (c: any) => c.scrollHeight - c.scrollTop - c.clientHeight <= 2,
                  writeScroll: (c: any, top: number, writer: string, stick = false) => { writes.push({ top, writer, stick }); c.scrollTop = Math.min(top, c.scrollHeight - c.clientHeight); },
                  scheduleAppendActive: () => { world.paints++; } };
  const prelude = `
    const H = HOOKS;
    const HTMLElement = H.FakeEl;
    const el = (tag, cls) => new H.FakeEl(tag, cls || "");
    const views = H.views; let activeId = H.activeId; const document = H.document;
    const setActive = (id) => { activeId = id; };
    const requestAnimationFrame = H.raf; const scrollDiagRow = H.diag; const spacerRow = H.spacerRow; const gapHeight = H.gapHeight;
    const rowsFor = H.rowsFor, meanRowHeight = H.meanRowHeight, perTurnEstimate = H.perTurnEstimate;
    const atBottom = H.atBottom, writeScroll = H.writeScroll, scheduleAppendActive = H.scheduleAppendActive;
  `;
  const api = new Function("HOOKS", prelude + js + "\nreturn { sizeSpacers, measureUnits, applyMeasure, redrawGapUnits, gapUnitsOf, entryBoxHeight, takeMeasureAtBottom, forgetAverage, setActive };")(hooks);
  return Object.assign(world, api) as World;
}
/** The unit observer's callback, lifted from ensureView (the `const view3 = v;` span) over a world's measure and take: a fake
 *  ResizeObserver hands the callback back, and `deliver` runs it with entries shaped as the browser's (border box + contentRect). */
function liftObserver(w: World, v: any, id: string) {
  const js = liftBetween("      const view3 = v;", "      const view2 = v;");
  let cb: ((entries: any[]) => void) | null = null;
  const hooks = { v, id, w, unitChanges, ResizeObserver: class { constructor(f: (entries: any[]) => void) { cb = f; } observe() {} unobserve() {} disconnect() {} } };
  const prelude = `
    const H = HOOKS;
    const v = H.v, id = H.id, activeId = H.w.activeId, document = { getElementById: (x) => (x === "content" ? H.w.content : null) };
    const ResizeObserver = H.ResizeObserver, unitChanges = H.unitChanges, entryBoxHeight = H.w.entryBoxHeight;
    const measureUnits = H.w.measureUnits, takeMeasureAtBottom = H.w.takeMeasureAtBottom;
    const atBottom = (c) => c.scrollHeight - c.scrollTop - c.clientHeight <= 2;
    const scrollDiagRow = (kind, data) => H.w.diag.push({ kind, data }); const unitChangeRow = (...a) => ({ row: a });
  `;
  new Function("HOOKS", prelude + js)(hooks);
  assert.ok(cb, "the unit observer was constructed");
  const deliver = (rows: FakeEl[], h: (r: FakeEl) => number) => cb!(rows.map((r) => ({ target: r, borderBoxSize: [{ blockSize: h(r), inlineSize: 400 }], contentRect: { height: h(r) } })));
  return { deliver, heights: v.uh as WeakMap<object, number> };
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
  assert.equal(v.pxPerTurn, 100, "the median of 100 and 120: the lower of the two (a height a turn has)");
  assert.equal(v.gapUnits.get(0), 200 * 100, "the head gap at the measured figure");
  assert.equal(v.gapUnits.get(items.length - 1), 10 * 100, "the mid-transcript gap too");
  assert.equal(g.style.height, 10 * 100 + "px", "the rendered gap element follows without a rebuild");
  assert.equal(topPx(v), Math.round(200 * 100 + 100 * v.avgTurnH), "the spacer: the gap plus the hidden run units at the average");
});

test("a later build re-measures (not once): the figure follows the window's complete turns; a window with fewer than two keeps the last figure", () => {
  const w = lift(null);
  const two = (a: number, b: number): Array<[string, number]> => [["turn turn-user", 30], ["turn turn-assistant", a - 30], ["turn turn-user", 30], ["turn turn-assistant", b - 30], ["turn turn-user", 30], ["turn turn-assistant", 500]];
  const first = viewOver(w, 200, 1 + 100 + 6, 101, (u) => two(100, 120)[u - 101]);
  buildOne(w, first.v, first.items); observe(w, first.v, first.rows); paintTwo(w, first.v);
  assert.equal(first.v.pxPerTurn, 100);
  const avgFirst = first.v.avgTurnH;
  assert.ok(avgFirst! > 0, "the average was taken on the first build");
  // the same view, re-windowed over taller turns (a browse, a fill): build, observe, paint
  const v = first.v;
  while (v.el.children.length > 1) v.el.removeChild(v.el.lastChild!);
  const rows2: FakeEl[] = [];
  two(200, 220).forEach(([cls, h], i) => { const n = new FakeEl("div", cls, h, w.reads); n.dataset.unit = String(101 + i); v.el.appendChild(n); rows2.push(n); });
  buildOne(w, v, first.items); observe(w, v, rows2); paintTwo(w, v);
  assert.equal(v.pxPerTurn, 200, "re-measured on the later build");
  assert.equal(v.gapUnits.get(0), 200 * 200);
  assert.equal(v.avgTurnH, avgFirst, "the average is taken once per view: the taller rows did not move it");
  // …and a window with one complete turn leaves the figure where it was
  while (v.el.children.length > 1) v.el.removeChild(v.el.lastChild!);
  const rows3: FakeEl[] = [];
  ([["turn turn-user", 30], ["turn turn-assistant", 70], ["turn turn-user", 30], ["turn turn-assistant", 900]] as Array<[string, number]>).forEach(([cls, h], i) => { const n = new FakeEl("div", cls, h, w.reads); n.dataset.unit = String(101 + i); v.el.appendChild(n); rows3.push(n); });
  buildOne(w, v, first.items); observe(w, v, rows3); paintTwo(w, v);
  assert.equal(v.pxPerTurn, 200, "one complete turn: the figure stands");
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
  const topOne = topPx(v);
  assert.deepEqual(w.reads, { offsetHeight: 0, scrollHeight: 0, clientHeight: 0 }, "build one's spacer write read nothing");
  assert.equal(w.diag.length, 0, "the spacer row is not filed inside the paint");
  assert.equal(w.rafs.length, 1, "…it waits for the next animation frame");
  observe(w, v, rows); paintTwo(w, v);
  const topTwo = topPx(v);
  assert.deepEqual(w.reads, { offsetHeight: 0, scrollHeight: 0, clientHeight: 0 }, "the measure read the observer's map, the paint wrote the spacers: still nothing");
  assert.ok(v.pxPerTurn! > 0 && v.avgTurnH! > 0, "…and the figures were taken from the map: " + v.pxPerTurn + " / " + v.avgTurnH);
  const before = w.diag.length;
  w.rafs.shift()!();
  assert.equal(w.diag.length, before + 2, "the two writes' rows, filed together");
  assert.deepEqual(w.reads, { offsetHeight: 0, scrollHeight: 1, clientHeight: 1 }, "the scroller was read once, in the frame, for both rows");
  assert.deepEqual(w.diag.map((d) => [d.kind, d.data.sid, d.data.sh, d.data.ch]), [["spacer", "A", 9114, 902], ["spacer", "A", 9114, 902]]);
  // each row carries its own before/after, in that order (the tuple queueSpacerRow pushes and the frame drains): the T262j diagnosis reads
  // which way the head spacer moved, so an inverted pair would read backwards (review round 0: the old assertion here compared a value with itself)
  assert.deepEqual(w.diag[0].data.top, [0, topOne], "build one's row: from nothing to the first spacer");
  assert.deepEqual(w.diag[1].data.top, [topOne, topTwo], "the paint's row: from the first spacer to the measured one");
  assert.deepEqual(w.diag[0].data.bot, [0, 0], "no bottom spacer in this window");
  assert.equal(w.diag[1].data.dTop, topTwo - topOne, "the delta follows the pair's order");
  assert.ok(topOne !== topTwo, "the second write moved the spacer again (the measured figures)");
});

test("a spacer row whose view was switched away before the frame carries no geometry and says so: the scroller is the active view's alone, and it is not read when no queued row is that view's (review round 1b)", () => {
  const w = lift("A");
  const { v, items } = viewOver(w, 200, 301, 221, () => ["turn turn-assistant", 90]);
  w.views.set("A", v);
  buildOne(w, v, items);                       // A is active: its spacer write queues a row for the next frame
  assert.equal(w.diag.length, 0); assert.equal(w.rafs.length, 1);
  w.setActive("B");   // the reader switched tabs before the frame ran
  w.rafs.shift()!();
  assert.deepEqual(w.reads, { offsetHeight: 0, scrollHeight: 0, clientHeight: 0 }, "no queued row is the active view's: the scroller is not read at all");
  assert.deepEqual(w.diag.map((d) => [d.kind, d.data.sid, d.data.sh, d.data.ch, d.data.view]), [["spacer", "A", null, null, "inactive"]], "A's row: no geometry and the marker, never B's 9114 / 902");
  // the marker is spread only when set: the shown view's row carries none (scroll-movers.test.ts and scroll-journal-audit.test.ts read that shape)
  assert.ok(!("view" in spacerRow("A", 1, 2, 0, 0, 9114, 902)), "no marker on the active view's row");
  assert.deepEqual(spacerRow("A", 1, 2, 0, 0, null, null, "inactive"), { sid: "A", top: [1, 2], bot: [0, 0], dTop: 1, dBot: 0, sh: null, ch: null, view: "inactive" });
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

// ── the follow-mode take at frame end ────────────────────────────────────────────────────────────

test("a follow-mode reader at the bottom is given the figures on the next paint: the frame-end take asks for it and writes nothing itself; anyone else's figures wait for the tail paint", () => {
  const two: Array<[string, number]> = [["turn turn-user", 30], ["turn turn-assistant", 70], ["turn turn-user", 30], ["turn turn-assistant", 90], ["turn turn-user", 30], ["turn turn-assistant", 500]];
  // the active, shown, follow-mode view with the reader at the bottom: the observer's delivery parks the figures and asks for the paint
  const w = lift("A");
  const world = viewOver(w, 200, 1 + 100 + 6, 101, (u) => two[u - 101]);
  w.views.set("A", world.v); world.v.shown = true; world.v.stick = true;
  buildOne(w, world.v, world.items); observe(w, world.v, world.rows);
  assert.ok(world.v.measured, "the figures are parked by the measure");
  const topBefore = topPx(world.v);
  w.takeMeasureAtBottom(world.v);
  assert.equal(w.paints, 1, "one paint asked for (scheduleAppendActive)");
  assert.ok(world.v.measured, "…the figures still parked for it");
  assert.equal(world.v.pxPerTurn, undefined); assert.equal(topPx(world.v), topBefore, "no spacer written inside the observer's callback (a write there re-sizes the view under its own observer: the ResizeObserver loop error)");
  assert.deepEqual(w.writes, [], "…and no scroll written");
  // the paint (appendActive's sync, the one that passes atBottom) takes them; its own follow writes the bottom (append-stick, scroll-keep.ts followTail)
  paintTwo(w, world.v);
  assert.equal(world.v.measured, undefined, "taken by the paint");
  assert.equal(world.v.pxPerTurn, 100); assert.equal(world.v.gapUnits.get(0), 200 * 100, "the gap units follow");
  assert.notEqual(topPx(world.v), topBefore, "the spacer moved in the paint");
  w.takeMeasureAtBottom(world.v);
  assert.equal(w.paints, 1, "nothing parked: no paint asked for");
  // the same reader scrolled up: no paint asked for, the figures wait for the tail paint (appendActive restores their anchor there)
  const up = lift("A", 1000);
  const w2 = viewOver(up, 200, 1 + 100 + 6, 101, (u) => two[u - 101]);
  up.views.set("A", w2.v); w2.v.shown = true; w2.v.stick = false;
  buildOne(up, w2.v, w2.items); observe(up, w2.v, w2.rows); up.takeMeasureAtBottom(w2.v);
  assert.ok(w2.v.measured, "parked"); assert.equal(w2.v.pxPerTurn, undefined); assert.deepEqual(up.writes, []); assert.equal(up.paints, 0);
  // follow mode recorded but the reader not at the bottom (a stale flag): nothing either
  const stale = lift("A", 1000);
  const w3 = viewOver(stale, 200, 1 + 100 + 6, 101, (u) => two[u - 101]);
  stale.views.set("A", w3.v); w3.v.shown = true; w3.v.stick = true;
  buildOne(stale, w3.v, w3.items); observe(stale, w3.v, w3.rows); stale.takeMeasureAtBottom(w3.v);
  assert.ok(w3.v.measured, "the recorded follow mode alone does not move a reader who is not at the bottom"); assert.deepEqual(stale.writes, []); assert.equal(stale.paints, 0);
  // an inactive or hidden view: nothing
  const other = lift("B");
  const w4 = viewOver(other, 200, 1 + 100 + 6, 101, (u) => two[u - 101]);
  other.views.set("A", w4.v); w4.v.shown = true; w4.v.stick = true;
  buildOne(other, w4.v, w4.items); observe(other, w4.v, w4.rows); other.takeMeasureAtBottom(w4.v);
  assert.ok(w4.v.measured); assert.deepEqual(other.writes, []); assert.equal(other.paints, 0);
  // a scroller with no box (the pane hidden: 0 - 0 - 0 reads as the bottom) is asked for nothing (review round 0, high)
  const hidden = lift("A", 0);
  const w5 = viewOver(hidden, 200, 1 + 100 + 6, 101, (u) => two[u - 101]);
  hidden.views.set("A", w5.v); w5.v.shown = true; w5.v.stick = true;
  buildOne(hidden, w5.v, w5.items); observe(hidden, w5.v, w5.rows);
  hidden.content.ch = 0; Object.defineProperty(hidden.content, "scrollHeight", { get() { return 0; } }); hidden.content.scrollTop = 0;
  hidden.takeMeasureAtBottom(w5.v);
  assert.ok(w5.v.measured, "parked"); assert.equal(hidden.paints, 0, "an emptied scroller reads as the bottom and asks for nothing");
});

// ── the unit observer's callback: a view with no width is the hidden case (review round 0, high) ─

test("an observer delivery with the view at width 0 (an ancestor hid it) forgets the baselines and measures nothing: no 0 enters the heights map, nothing is parked, no paint is asked for; the re-show measures", () => {
  const two: Array<[string, number]> = [["turn turn-user", 30], ["turn turn-assistant", 70], ["turn turn-user", 30], ["turn turn-assistant", 90], ["turn turn-user", 30], ["turn turn-assistant", 500]];
  const w = lift("A");
  const { v, items, rows } = viewOver(w, 200, 1 + 100 + 6, 101, (u) => two[u - 101]);
  w.views.set("A", v); v.shown = true; v.stick = true; (v.el as any).clientWidth = 800;
  buildOne(w, v, items);
  const { deliver, heights } = liftObserver(w, v, "A");
  // the first delivery at a real width: baselines, the measure, the paint asked for
  deliver(rows, (r) => r.realH);
  assert.equal(heights.get(rows[1]), 70, "the border boxes are the baselines");
  assert.deepEqual(v.measured, { avg: (30 + 70 + 30 + 90 + 30 + 500) / 6, per: 100 }, "the window measured");
  assert.equal(w.paints, 1, "a bottom reader's paint asked for");
  paintTwo(w, v);
  assert.equal(v.pxPerTurn, 100); const gapAfter = v.gapUnits.get(0), topAfter = topPx(v);
  // the ancestor hides the pane: every unit arrives at 0 with the view at width 0, its own display still ""
  (v.el as any).clientWidth = 0; v.measureDue = true;
  deliver(rows, () => 0);
  assert.equal(heights.get(rows[1]), undefined, "the baselines are forgotten, as on the view's own hide");
  assert.equal(v.measured, undefined, "nothing parked"); assert.equal(v.pxPerTurn, 100, "the figure stands"); assert.equal(v.gapUnits.get(0), gapAfter); assert.equal(topPx(v), topAfter);
  assert.equal(w.paints, 1, "no paint asked for");
  assert.equal(v.measureDue, true, "the measure still owed: the re-show pays it");
  // the re-show at the same width: real sizes again, baselines recorded, the owed measure runs off them (nothing changed: no new figure parked)
  (v.el as any).clientWidth = 800;
  deliver(rows, (r) => r.realH);
  assert.equal(heights.get(rows[1]), 70, "fresh baselines");
  assert.equal(v.measureDue, false, "measured on the re-show"); assert.equal(v.measured, undefined, "the same figures: nothing new parked");
  // …and what the zeros would have done, read as heights: the estimator refuses them (turn-estimate.test.ts), the map never holds them
  assert.equal(perTurnEstimate(rowsFor(rows, (r) => r.className, () => false, () => 0)), null, "the estimator hands out no 0");
});

test("a delivery on a view whose only child is the empty transcript's placeholder, or the deferred build's loading hint under a spacer, survives: the callback returns, measures nothing and files no unitchange row (the maintainer's round 3 ruling A: the unit-aware tail scan left tail at -1 and the pane's unitOf threw on children[-1] inside the observer's callback)", () => {
  // the two views the pane shows with no unit-carrying child: syncViewInner's tx-empty placeholder for a zero-event session (its swirl
  // removes itself on error, a height change), and showActive's tx-loading hint, the only child of a non-empty session's view for the frame
  // its heavy build is deferred to. The mutation observer hands every added element to this observer, so the first observation of either
  // is a baseline and a later height change an entry; the callback is the lifted one (the 13441 closure's dataset reach-in included)
  for (const [label, kids] of [["the placeholder", [["tx-empty", 120]]], ["the loading hint under a spacer", [["tx-spacer tx-spacer-top", 10], ["tx-loading", 40]]]] as Array<[string, Array<[string, number]>]>) {
    const w = lift("A");
    const host = new FakeEl("div"); (host as any).clientWidth = 800;
    const rows = kids.map(([cls, h]) => host.appendChild(new FakeEl("div", cls, h, w.reads)));
    const v: any = { el: host, uh: new WeakMap<object, number>(), stick: true, shown: true, winStart: 0, winEnd: 0, unitTotal: 0 };
    w.views.set("A", v);
    const { deliver, heights } = liftObserver(w, v, "A");
    deliver(rows, (r) => r.realH);   // the first observation: the baselines
    const last = rows[rows.length - 1];
    assert.doesNotThrow(() => deliver([last], () => last.realH - 24), label + ": the callback survives a height change of the unit-less child (at the head: TypeError, reading dataset of undefined)");
    assert.equal(heights.get(last), last.realH - 24, label + ": the baseline moved on");
    assert.deepEqual(w.diag.filter((d) => d.kind === "unitchange"), [], label + ": no unitchange row (the parent's behaviour: the view's own change is the rail's tailchange row, which names it, tail-change-row.test.ts)");
    assert.equal(v.measured, undefined, label + ": nothing measured, there being no unit rows"); assert.equal(w.paints, 0, label + ": no paint asked for");
  }
});

// ── the resets that clear the average (review round 0, low) ──────────────────────────────────────

test("forgetAverage drops a parked average with the figure, so a reset's build measures the new rows instead of taking the old rows' average", () => {
  const w = lift(null);
  // build one over dense rows; the observer parks the average; nothing takes it (the reader landed off the bottom, the session is idle)
  const dense = viewOver(w, 200, 1 + 100 + 4, 101, () => ["turn turn-assistant", 400]);
  buildOne(w, dense.v, dense.items); observe(w, dense.v, dense.rows);
  assert.equal(dense.v.measured?.avg, 400, "parked over the old rows, untaken");
  // the reset (the compact toggle, a re-collapse, the older-history re-anchor): the figure AND the parked one go
  w.forgetAverage(dense.v);
  assert.equal(dense.v.avgTurnH, undefined); assert.equal(dense.v.measured, undefined);
  // the rebuild over the new mode's rows: build (takes nothing), observe (measures the new rows), paint (takes the new average)
  const v = dense.v;
  while (v.el.children.length > 1) v.el.removeChild(v.el.lastChild!);
  const rows2: FakeEl[] = [];
  for (let i = 0; i < 4; i++) { const n = new FakeEl("div", "turn turn-assistant", 40, w.reads); n.dataset.unit = String(101 + i); v.el.appendChild(n); rows2.push(n); }
  buildOne(w, v, dense.items);
  assert.equal(v.avgTurnH, undefined, "the build took no parked figure");
  observe(w, v, rows2); paintTwo(w, v);
  assert.equal(v.avgTurnH, 40, "the new rows' average");
  // the counter-example the reset used to produce: clearing the figure alone leaves the parked one for the build to take
  const w2 = lift(null);
  const d2 = viewOver(w2, 200, 1 + 100 + 4, 101, () => ["turn turn-assistant", 400]);
  buildOne(w2, d2.v, d2.items); observe(w2, d2.v, d2.rows);
  d2.v.avgTurnH = undefined;   // the bare reset
  buildOne(w2, d2.v, d2.items);
  assert.equal(d2.v.avgTurnH, 400, "the old rows' average, taken by the build, would stand for the view's life");
  assert.equal(w.reads.offsetHeight, 0, "no layout read anywhere in this");
});

// ── the measure's population is the units (review round 1) ───────────────────────────────────────

test("a hover's rail band among the view's children is not a row: the rows' average is over the children that carry a unit alone", () => {
  // drawRailBand appends the band to the thread with a class and no data-unit; the unit observer observes every added element, so the
  // band has a height in v.uh, and measureUnits' population was every child of the thread, band included (review round 1, with the trim)
  const w = lift(null);
  const heights = [40, 90, 90, 30, 90, 90];
  const { v, items, rows } = viewOver(w, 200, 1 + 100 + heights.length, 101, (u) => [u === 101 || u === 104 ? "turn turn-user" : "turn turn-assistant", heights[u - 101]]);
  const band = new FakeEl("div", "rail-band rail-band-local", 4, w.reads);
  v.el.appendChild(band);
  buildOne(w, v, items);
  assert.ok(rows.length > 0, "the population is derived from the fixture's rows and must not be empty");
  const expected = rows.reduce((a, r) => a + r.realH, 0) / rows.length;
  assert.ok(expected > 0);
  v.uh.set(band, band.realH);   // the observer reported the band too (it observes every added element)
  observe(w, v, rows);
  assert.equal(v.measured?.avg, expected, "the mean over the unit rows: " + expected + " (the band's 4 px would pull it to " + (expected * rows.length + 4) / (rows.length + 1) + ")");
  assert.equal(v.measured?.per, undefined, "one complete turn in this window: no per-turn figure (the band is no turn row either)");
});

// ── source pins on what the harness does not lift ────────────────────────────────────────────────

test("render.ts: the render task's spacer code holds no layout read; the unit observer records border-box heights and measures in both of its branches", () => {
  const code = codeOf;   // the code alone (the compiler's comment ranges): the comments name the reads that are gone
  // the stripper's own pin (review round 3): a `//` in a quoted URL leaves the alias after it standing for the census, a quoted glob opens
  // no block comment, a regular expression's slashes are not a comment, and the comments themselves go
  assert.equal(code('const u = "http://h"; const rwi = renderWindowItems; // c\nz("image/*"); y(); /* c */ q(/^file:\\/\\//, ""); // d\n'),
    'const u = "http://h"; const rwi = renderWindowItems; \nz("image/*"); y();  q(/^file:\\/\\//, ""); \n', "the stripper keeps string, template and regular-expression literals whole and drops comments alone");
  const span = RENDER.slice(RENDER.indexOf("function gapUnitsOf("), RENDER.indexOf("function unitAtScroll("));
  const inFrame = span.slice(span.indexOf("function queueSpacerRow("), span.indexOf("// The window's two figures"));
  const paintSide = code(span.replace(inFrame, ""));
  assert.ok(paintSide.includes("function sizeSpacers(v") && paintSide.includes("function measureUnits(v") && paintSide.includes("function applyMeasure(v"), "the span holds the paint-side functions");
  assert.doesNotMatch(paintSide, /offsetHeight|scrollHeight|clientHeight|getBoundingClientRect|offsetTop/, "sizeSpacers, the trim, the eviction, the measure and the apply read no layout property");
  // the frame's read is per row, not per batch (review round 1b): once, only when a queued row is the shown view's, and a row of a view switched
  // away since it was queued is filed with no geometry and the inactive marker, never another view's figures
  assert.match(inFrame, /requestAnimationFrame\(\(\) => \{[\s\S]*?const live = activeId;\s*\n\s*let sh: number \| null = null, ch: number \| null = null;\s*\n\s*if \(live && content && rows\.some\(\(\[rsid\]\) => rsid === live\)\) \{ sh = content\.scrollHeight; ch = content\.clientHeight; \}/, "the diag row's scroller read rides a frame, once, for the active view's rows alone");
  assert.match(inFrame, /rsid === live \? spacerRow\(rsid, a, b, c, d, sh, ch\) : spacerRow\(rsid, a, b, c, d, null, null, "inactive"\)/, "a switched-away view's row: no geometry, marked");
  assert.doesNotMatch(inFrame, /const sh = content \? content\.scrollHeight : 0/, "the batch read is gone");
  const uo = RENDER.slice(RENDER.indexOf("v.uo = new ResizeObserver((entries) => {"), RENDER.indexOf("v.mo = new MutationObserver("));
  assert.match(uo, /unitHeights\.set\(e\.target, entryBoxHeight\(e\)\); view3\.measureDue = true; measureUnits\(view3\); takeMeasureAtBottom\(view3\); return; \}/, "a reflow records border boxes, re-measures and asks for a bottom reader's paint");
  assert.match(uo, /height: entryBoxHeight\(e\) \}\)\), view3\.el\.children, unitHeights, unitOf\);\s*\n\s*measureUnits\(view3\); takeMeasureAtBottom\(view3\);/, "…and so does every delivery");
  assert.match(uo, /if \(view3\.el\.style\.display === "none" \|\| w === 0\) \{ for \(const e of entries\) unitHeights\.delete\(e\.target\); return; \}/, "a view with no width is the hidden case: no zero enters the map");
  // the frame-end take decides and asks for the paint; it writes nothing inside the observer's callback (a spacer written there re-sizes the
  // view element under v.ro, delivered earlier in the same frame: the ResizeObserver loop error, the tab-row sentinel's precedent)
  const take = inFrame.slice(inFrame.indexOf("function takeMeasureAtBottom(v: View): void {"));
  assert.match(take, /if \(!content \|\| content\.clientHeight <= 0 \|\| !atBottom\(content\)\) return;\s*\n\s*scheduleAppendActive\(\);\s*\n\}/, "the take: a scroller with a box, at the bottom, then the paint asked for");
  assert.doesNotMatch(code(take), /writeScroll|sizeSpacers|redrawGapUnits|applyMeasure|style\./, "…and no write of its own");
  assert.doesNotMatch(RENDER, /"spacer-follow"/, "the writer is gone with it (landing-settle.ts's census)");
  assert.doesNotMatch(code(uo), /writeScroll|style\.height|sizeSpacers|redrawGapUnits/, "nothing in the unit observer's callback writes the DOM");
  // the parked figures reach the DOM under one rule (review round 1b): a figure is taken ONLY by a paint that anchors the reader, and EVERY
  // anchoring paint takes one. The takers: syncViewInner under the `anchored` flag (appendActive's follow or the anchor its restore holds,
  // `stick || !!anchor`; the toggle's keep when it captured a row, `!!anchor`), a window build under the same flag from its caller (a deep
  // link's or a moment's land, the re-window, a fill with a row or a point to put back), landActive on every road but the nothing-armed
  // re-show (land-saved, the raw write; an ARMED land that misses takes and puts the saved place's row back, anchor-restore, and writes
  // raw only when that restore finds no row to put back: review round 2, the third such road named in round 3, executed in
  // land-active-keep.test.ts), and keepPlaceAcrossWindow over its restore. A switch's, a landing's or a hidden prebuild's sync passes no flag and applies
  // nothing (a 55 px move of a bottom reader in the landing lab), a fill that can only restore its raw top passes false, and a paint whose
  // only restore is a raw scrollTop (appendActive with no capturable row, the toggle for a bottom or row-less reader) passes false too.
  assert.match(RENDER, /function syncViewInner\(id: string, atBottom\?: boolean, anchored: boolean = atBottom !== undefined\): View \{/, "the flag defaults to 'atBottom was passed'");
  assert.match(RENDER, /if \(anchored && applyMeasure\(v\)\) \{ redrawGapUnits\(v\); sizeSpacers\(v\); \}/, "syncViewInner takes the figures inside an anchoring paint alone");
  assert.match(RENDER, /function renderWindowItems\([^\n]*anchored = false\): void \{\n(?:\s*\/\/[^\n]*\n)*\s*if \(anchored\) applyMeasure\(v\);/, "a window build takes them only when its caller anchors");
  const land = RENDER.slice(RENDER.indexOf("function landActive(content: HTMLElement | null, v: View): void {"), RENDER.indexOf("\n}\n", RENDER.indexOf("function landActive(content: HTMLElement | null, v: View): void {")));
  assert.match(land, /const saved = !pendingAnchor && pendingAnchorT == null && !\(seek && seek\.sid === activeId\) && v\.shown && !v\.stick && takeReloadScroll\(pendingReloadScroll, activeId\) == null;\s*\n\s*const held = !saved && v\.shown && !v\.stick \? captureScrollAnchor\(content, v, v\.scrollTop\) : null;[^\n]*\n\s*if \(!saved && applyMeasure\(v\)\) redrawGapUnits\(v\);\s*\n\s*sizeSpacers\(v\);/,
    "landActive takes on every road but the nothing-armed re-show, BEFORE its landing attempt (the gate reads what is armed, not the outcome), captures the row at the saved place first, and sizes the spacers after the take; an armed land that misses puts that row back (the fallback below, executed in land-active-keep.test.ts)");
  assert.match(land, /else if \(!\(held && restoreScrollAnchor\(content, v, held\)\)\) writeScroll\(content, v\.scrollTop, "land-saved"\);/, "the saved-place fallback restores the captured row; the raw write stands whenever that restore finds no row to put back: nothing armed (nothing taken), no row at the saved place, or the captured row gone with the attempt's window build (land-active-keep.test.ts executes the three)");
  assert.equal((land.match(/applyMeasure\(v\)/g) || []).length, 1, "one take in the land");
  const keep = RENDER.slice(RENDER.indexOf("function keepPlaceAcrossWindow("), RENDER.indexOf("\n}\n", RENDER.indexOf("function keepPlaceAcrossWindow(")));
  assert.match(keep, /const under = captureScrollAnchor\(content, v\);\s*\n\s*if \(applyMeasure\(v\)\) \{ redrawGapUnits\(v\); sizeSpacers\(v\); \}\s*\n\s*if \(restoreScrollAnchor\(content, v, keep\)\) return true;/,
    "keepPlaceAcrossWindow captures the row under the viewport top, then takes over its restore, spacers and gap units first (the take stays above the restores, which read the re-sized layout; land-active-keep.test.ts executes the roads and the double miss)");
  assert.match(keep, /if \(!landed && under\) restoreScrollAnchor\(content, v, under\);/, "the double miss puts the captured row back over the take instead of writing nothing (review round 2)");
  const calls = (RENDER.match(/(?<![\w.])applyMeasure\(v\)/g) || []).length;
  assert.equal(calls, 4, "four takers: syncViewInner, the window build, landActive and keepPlaceAcrossWindow (" + calls + "); the frame-end take asks for the first");
  // the census of callers, derived from the tree and keyed on the CALLER, not on a spelling (review round 2): every window build outside
  // the definition names whether its caller anchors (a seventh argument that is the flag it was handed, true, or the fill's own predicate)
  // and sits in one of the functions the multiset names (a multiset, so an eighth build hard-coded inside syncViewInner reds too); every
  // syncView call either passes its keep's own predicate (appendActive's `stick || !!anchor`, the toggle's `!!anchor`, the fill's
  // `keepVisible || pointBefore != null`) or is one of the non-anchoring callers named here, which take nothing; and neither name is
  // handed on as a bare reference (a value passed on could reach a caller neither census reads). appendActive has no harness of its
  // own, so its line is pinned here as well; scroll-to-anchor-roads.test.ts and land-active-keep.test.ts execute the roads behind the
  // flagged builds and the land.
  assert.match(RENDER, /const anchor = !stick && v \? captureScrollAnchor\(content, v\) : null;\n(?:\s*\/\/[^\n]*\n)*\s*syncView\(activeId, stick, stick \|\| !!anchor\);/, "appendActive's sync is flagged by its follow or the anchor it captured, never by atBottom alone");
  const lines = RENDER.split("\n").map((l, i) => [i + 1, l] as const);
  const fnOf = (line: number) => { for (let i = line - 1; i >= 0; i--) { const m = /^function (\w+)\(/.exec(RENDER.split("\n")[i]); if (m) return m[1]; } return ""; };
  const builds = RENDER.match(/(?<![\w.])renderWindowItems\(v, s, items, [^\n]*?\);/g) || [];
  assert.equal(builds.length, (RENDER.match(/(?<![\w.])renderWindowItems\(/g) || []).length - 1, "every call site has the (v, s, items, …) shape (the definition excluded)");
  assert.ok(builds.length >= 7, "the census is not empty: " + builds.length);
  for (const b of builds) assert.match(b, /, (?:anchored|true|keepVisible \|\| pointBefore != null)\);$/, "a build names whether its caller anchors: " + b);
  const buildLines = lines.filter(([, l]) => /(?<![\w.])renderWindowItems\(v, s, items, /.test(l));
  assert.equal(buildLines.length, builds.length, "one build call per line");
  assert.deepEqual(buildLines.map(([n]) => fnOf(n)).sort(), ["fillInPlace", "fillInPlace", "landNearestMoment", "scrollToAnchor", "syncViewInner", "syncViewInner", "virtualizeToViewport"].sort(),
    "the window builds by caller, a multiset: the fill's two (the land and its re-window), the moment's, the deep link's, the seam's first build and rebuild, the re-window's; a build added anywhere, syncViewInner included, changes it");
  const bare = (name: string) => (code(RENDER).match(new RegExp("(?<![\\w.$])" + name + "(?![\\w$(])", "g")) || []).length;
  assert.equal(bare("renderWindowItems"), 0, "renderWindowItems is never handed on as a bare reference (every use is a call the census reads)");
  assert.equal(bare("syncView"), 0, "syncView is never handed on as a bare reference either");
  const syncs = lines.filter(([, l]) => /(?<![\w.])syncView\(/.test(l) && !/function syncView\(/.test(l));
  assert.ok(syncs.length >= 7, "the syncView census is not empty: " + syncs.length);
  const flagless = syncs.filter(([, l]) => !/syncView\(\w+, stick, stick \|\| !!anchor\)/.test(l) && !/syncView\(\w+, undefined, !!anchor\)/.test(l) && !/syncView\(\w+, undefined, keepVisible \|\| pointBefore != null\)/.test(l));
  assert.deepEqual(flagless.map(([n]) => fnOf(n)).sort(), ["reviveFailedLocal", "runPrebuild", "showActive", "showActive"].sort(),
    "the flagless syncView callers are the non-anchoring ones: the placeholder re-render, the hidden prebuild and the switch's two builds (landActive and keepPlaceAcrossWindow land them)");
  assert.deepEqual(syncs.filter((x) => !flagless.includes(x)).map(([n]) => fnOf(n)).sort(), ["appendActive", "fillInPlace", "toggleToolGroup"].sort(),
    "…and three pass their keep's own predicate: appendActive (its follow or its anchor), the toggle (its anchor) and the fill's no-unit fallback (a row or a point in hand), by caller");
  assert.equal(syncs.length - flagless.length, 3, "three flagged syncs");
  // every reset that clears the average clears the parked figures with it (forgetAverage), and none clears the figure bare
  assert.match(RENDER, /function forgetAverage\(v: View\): void \{\s*\n\s*v\.avgTurnH = undefined; v\.measured = undefined;\s*\n\}/);
  assert.equal((RENDER.match(/\bavgTurnH = undefined/g) || []).length, 1, "the one bare clear is the helper's");
  assert.equal((RENDER.match(/(?<![\w.])forgetAverage\(v\);/g) || []).length, 4, "four resets: the compact toggle's rerender, the prebuild's and the switch's re-collapse, the older-history re-anchor");
  assert.match(RENDER, /import \{ rowsFor, meanRowHeight, perTurnEstimate \} from "\.\/turn-estimate";/);
  assert.match(RENDER, /interface View \{[^\n]*measured\?: \{ avg\?: number; per\?: number \};/, "the parked figures live on the view");
});
