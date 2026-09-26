// fillInPlace's roads, EXECUTED (PR E, the maintainer's round 3 rulings B and E). A gap fill re-renders the window around the reader's
// place and puts the reader back: a visible row (captured before the build) at its exact offset; with no row on screen, the point under
// the viewport top (a turn and a fraction into its gap) by its turn (yOfTurn); with neither, the raw pre-fill top. The build (or the
// no-unit fallback's sync, the same paint one road over) takes the figures the unit observer parked only when the land has a row or a
// point to put back (the flag `keepVisible || pointBefore != null`, the same predicate on both roads: the maintainer's round 2 ruling),
// and where the outcome is the raw top after all (the anchor row gone from the rebuilt window with no point to name; a point whose turn
// maps to no y, on the fill and on its re-window) the take is given back before the write (untakeMeasure; the maintainer's round 3 ruling
// B, until which the two roads were disclosed as a take followed by a raw write). Nothing executed the fill before this harness: the
// census over its flag's spelling could not see a flag that lied about the road (the maintainer's round 3 ruling E; the census now
// reads the flag's kind per caller and points here for its semantics). fillInPlace, unitOfTurn, rowOnScreen, captureScrollAnchor and
// restoreScrollAnchor are lifted from render.ts over the toggle harness's layout model; the stubbed renderWindowItems and syncView
// record the flag, model the take under it (the head spacer grows by the take's delta) and the world's DOM change; turnUnderTop and
// yOfTurn answer what the world says. Synthetic uuids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { hideEdges } from "../test-dom-shim";

const requireCjs = createRequire(__filename);
const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");

function liftBetween(startAnchor: string, endAnchor: string): string {
  const a = RENDER.indexOf(startAnchor), b = RENDER.indexOf(endAnchor, a);
  assert.ok(a > 0 && b > a, `anchors not found: ${startAnchor.slice(0, 40)} or ${endAnchor.slice(0, 40)} moved; re-anchor`);
  return requireCjs("esbuild").transformSync(RENDER.slice(a, b), { loader: "ts" }).code;
}

/** The layout model: the scroller holds one view whose children stack from offset 0, each of a known height; a row's client rect is its
 *  offset less the scroller's scrollTop (the scroller's own rect top is 0). Rows carry `turn` (a class) and data-uuid. */
type Write = { writer: string; top: number; stick: boolean; from: number | undefined };
class Content {
  scrollTop = 0; host: Host | null = null;
  constructor(public clientHeight: number) { hideEdges(this); }
  get scrollHeight(): number { return this.host ? this.host.children.reduce((a, c) => a + c.h, 0) : 0; }
  getBoundingClientRect() { return { top: 0, bottom: this.clientHeight }; }
}
class Node {
  dataset: Record<string, string> = {}; host: Host | null = null;
  constructor(public h: number, public className: string, uuid?: string) { if (uuid) this.dataset.uuid = uuid; hideEdges(this); }
  get classList() { const c = this.className.split(/\s+/); return { contains: (x: string) => c.includes(x) }; }
  getBoundingClientRect() { const top = this.host!.offsetOf(this) - this.host!.content.scrollTop; return { top, bottom: top + this.h, height: this.h }; }
}
class Host {
  children: Node[] = [];
  constructor(public content: Content) { content.host = this; hideEdges(this); }
  add(n: Node): Node { n.host = this; this.children.push(n); return n; }
  removeChild(n: Node): void { this.children = this.children.filter((c) => c !== n); }
  offsetOf(n: Node): number { let y = 0; for (const c of this.children) { if (c === n) return y; y += c.h; } throw new Error("not a child"); }
  querySelectorAll(sel: string): Node[] { assert.equal(sel, "[data-uuid]", "captureScrollAnchor's selector"); return this.children.filter((c) => c.dataset.uuid != null); }
  querySelector(sel: string): Node | null { const m = /^(?:\.turn)?\[data-uuid="([^"]*)"\]$/.exec(sel); assert.ok(m, "the fill's or restoreScrollAnchor's selector: " + sel); return this.children.find((c) => c.dataset.uuid === m![1]) ?? null; }
}

type Opts = { spacerH?: number; n?: number; rowH?: number; clientHeight?: number; scrollTop: number; bottomSpacerH?: number; parked?: boolean;
              point?: number | null; yOf?: (t: number, call: number) => number | null; unitAt?: number; eventPrefix?: string;
              onBuild?: (host: Host, call: number) => void; onSync?: (host: Host) => void };
type World = { content: Content; host: Host; v: any; spacer: Node; rows: Node[]; writes: Write[]; builds: Array<[number, number, boolean]>; syncs: Array<[boolean | undefined, boolean]>; untakes: number; takes: number; parked: boolean; fill: () => void };
const D = 300;   // the take's delta: the head spacer re-sized by the re-measured figure over the head gap's turns

/** A view with a head spacer of `spacerH`, `n` rows of `rowH` each (uuids r0..) over a session of `n` events (uuids `eventPrefix` + i,
 *  "r" by default so a row's uuid names its event; turn i for event i), in a scroller of `clientHeight`, the reader at `scrollTop`;
 *  `point` is what turnUnderTop answers (the turn under the viewport top, null when the viewport is not over a gap or a row), `yOf` what
 *  yOfTurn answers per call, `unitAt` what unitAtScroll answers; `parked`: a figure waits for a taker. The stubbed build and sync record
 *  their flag, take under it (production's gate: `if (anchored) applyMeasure(v)`, the head spacer growing by D) and run the world's DOM
 *  change (`onBuild` with the call's ordinal, `onSync`); the stubbed untake gives that take back (spacer-measure.test.ts executes the pair). */
function world(o: Opts): World {
  const spacerH = o.spacerH ?? 2000, n = o.n ?? 10, rowH = o.rowH ?? 100, clientHeight = o.clientHeight ?? 600;
  const content = new Content(clientHeight); const host = new Host(content);
  const spacer = host.add(new Node(spacerH, "tx-spacer tx-spacer-top"));
  const rows: Node[] = []; for (let i = 0; i < n; i++) rows.push(host.add(new Node(rowH, "turn", "r" + i)));
  if (o.bottomSpacerH) host.add(new Node(o.bottomSpacerH, "tx-spacer tx-spacer-bot"));
  content.scrollTop = o.scrollTop;
  const s = { id: "A", events: Array.from({ length: n }, (_, i) => ({ kind: i % 2 ? "assistant" : "user", uuid: (o.eventPrefix ?? "r") + i })), status: { state: "working" }, regions: undefined };
  const v: any = { el: host, stick: true, shown: true, winStart: 0 };
  const w: any = { content, host, v, spacer, rows, writes: [] as Write[], builds: [], syncs: [], untakes: 0, takes: 0 };
  const H: any = { content, s, v, writes: w.writes, parked: o.parked ?? true, took: false, point: o.point ?? null, unitAt: o.unitAt ?? -1, yCalls: 0,
                   take: (anchored: boolean) => { if (anchored && H.parked) { H.parked = false; spacer.h += D; H.took = true; w.takes++; } },
                   build: (ws: number, we: number, anchored: boolean) => { w.builds.push([ws, we, anchored]); H.take(anchored); o.onBuild?.(host, w.builds.length); },
                   sync: (atBottom: boolean | undefined, anchored: boolean) => { w.syncs.push([atBottom, anchored]); H.take(anchored); o.onSync?.(host); },
                   yOf: (t: number) => (o.yOf ? o.yOf(t, ++H.yCalls) : null),
                   untake: () => { w.untakes++; if (!H.took) return false; H.took = false; H.parked = true; spacer.h -= D; return true; } };
  const js = liftBetween("function fillInPlace(", "// The display unit holding an absolute turn")
           + liftBetween("function unitOfTurn(", "// Whether any turn row intersects the viewport")
           + liftBetween("function rowOnScreen(", "const pendingOlderAnchor = new Map")
           + liftBetween("function captureScrollAnchor(", "// Live tail-append to the ACTIVE view");
  const prelude = `
    const H = HOOKS;
    const document = { getElementById: (id) => (id === "content" ? H.content : null) };
    const activeId = "A"; const sessions = new Map([["A", H.s]]);
    const showActive = () => { throw new Error("fillInPlace fell through to showActive"); };
    const displayItems = (s) => s.events.map((e, i) => ({ kind: "event", index: i }));
    const itemFirstEvent = (it) => it.index;
    const turnOfEvents = (s) => s.events.map((e, i) => i);
    const turnUnderTop = () => H.point;
    const unitAtScroll = () => H.unitAt;
    const WINDOW_RADIUS = 70;
    const renderWindowItems = (v, s, items, ws, we, working, anchored) => { H.build(ws, we, anchored); };
    const syncView = (id, atBottom, anchored) => { H.sync(atBottom, anchored); };
    const yOfTurn = (v, s, items, turns, content, t) => H.yOf(t);
    const figuresBefore = (v) => ({ parked: H.parked }); const untakeMeasure = (v, fig) => H.untake();
    const writeScroll = (c, top, writer, stick = false, from) => { H.writes.push({ writer, top, stick, from }); c.scrollTop = Math.max(0, Math.min(top, c.scrollHeight - c.clientHeight)); };
    const applyCommentMarks = () => {}; const scheduleRailSticky = () => {}; const cssEscape = (x) => x;
  `;
  const fill = new Function("HOOKS", prelude + js + "\nreturn fillInPlace;")(H) as (sid: string, v: any) => void;
  w.fill = () => fill("A", v);
  Object.defineProperty(w, "parked", { get: () => H.parked });
  return w as World;
}
// the reader's place in the default world: 2350 in a 3000 px view under a 2000 px spacer, a 600 px viewport: r3 (2300..2400) is under the
// viewport top, 50 px above it

test("a row in hand that survives the rebuild: the build is flagged (a row to put back), takes, and the row goes back at its exact offset over the re-sized spacer; the take stands", () => {
  const w = world({ scrollTop: 2350 });
  w.fill();
  assert.deepEqual(w.builds, [["r".length ? 0 : 0, 10, true]], "one window build around the row's unit, flagged: the land below has a row to put back");
  assert.deepEqual(w.syncs, [], "no fallback sync: the row named its unit");
  assert.equal(w.takes, 1); assert.equal(w.spacer.h, 2000 + D, "the build took");
  assert.deepEqual(w.writes, [{ writer: "gap-fill", top: 2350 + D, stick: false, from: 2350 }], "r3 at its offset, 300 px further down the document, the pre-fill top the origin");
  assert.equal(w.rows[3].getBoundingClientRect().top, -50, "the row did not move on screen");
  assert.equal(w.untakes, 0, "nothing given back: the row anchored the reader"); assert.equal(w.v.stick, false, "a fill never follows the tail");
});

test("no row on screen, the point under the viewport top in hand: the build is flagged (a point to put back), takes, and the point goes back by its turn (yOfTurn); the take stands", () => {
  // rows 0..1000 then a 5000 px bottom spacer; the reader at 3000 sees no row; the point is turn 7 and a half, which yOfTurn maps to 500 (a row on screen after the write)
  const w = world({ spacerH: 0, scrollTop: 3000, bottomSpacerH: 5000, point: 7.5, yOf: () => 500 });
  w.fill();
  assert.deepEqual(w.builds, [[0, 10, true]], "the window around the unit holding the point's turn, flagged");
  assert.equal(w.takes, 1); assert.equal(w.spacer.h, D, "the build took");
  assert.deepEqual(w.writes, [{ writer: "gap-fill", top: 500, stick: false, from: 3000 }], "the point put back by its turn");
  assert.equal(w.untakes, 0, "the point anchored the reader");
});

test("neither a row nor a point (a jump to the head, the window rendered around unitAtScroll's estimate): the build is flagged false, takes nothing, and the raw pre-fill top stands; the untake finds nothing to give back", () => {
  const w = world({ spacerH: 0, scrollTop: 3000, bottomSpacerH: 5000, point: null, unitAt: 4 });
  w.fill();
  assert.deepEqual(w.builds, [[0, 10, false]], "the build is told it anchors nothing");
  assert.equal(w.takes, 0); assert.equal(w.spacer.h, 0, "nothing taken"); assert.equal(w.parked, true, "the figure waits for a paint that anchors");
  assert.equal(w.untakes, 1, "the raw road asks; nothing was taken");
  assert.deepEqual(w.writes, [{ writer: "gap-fill", top: 3000, stick: false, from: 3000 }], "the raw pre-fill top");
});

test("a row in hand that is GONE from the rebuilt window with no point to name (a turn anchored on a key no event carries): the build took on the intent, the restore has nothing, the take is given back and the raw pre-fill top lands in the layout it was read in (the maintainer's round 3 ruling B: until then the take stood under the raw write, disclosed)", () => {
  const w = world({ scrollTop: 2350, point: null, onBuild: (host) => { host.removeChild(w.rows[3]); host.removeChild(w.rows[4]); } });
  w.fill();
  assert.deepEqual(w.builds, [[0, 10, true]], "a row was captured, so the build was flagged: its fate is known only after the build");
  assert.equal(w.takes, 1, "the build took");
  assert.equal(w.spacer.h, 2000, "the head spacer stands where the pre-fill top was read (at the head it stood 300 px taller under the raw write)");
  assert.equal(w.untakes, 1, "the row gone and no point: the take is given back before the raw write");
  assert.equal(w.parked, true, "the figures wait for a paint that anchors");
  assert.deepEqual(w.writes, [{ writer: "gap-fill", top: 2350, stick: false, from: 2350 }], "the raw pre-fill top, exact in the layout it was read in");
});

test("a point whose turn maps to no y, on the fill and again on its re-window (no row on screen after the first write): each build takes and each take is given back before the raw write (the maintainer's round 3 ruling B: the second of the two disclosed roads, both sites)", () => {
  const w = world({ spacerH: 0, scrollTop: 3000, bottomSpacerH: 5000, point: 7.5, yOf: () => null });
  w.fill();
  assert.deepEqual(w.builds, [[0, 10, true], [0, 10, true]], "the fill's build around the point's unit, then, with no row on screen after its write, the re-window around the same unit, both flagged");
  assert.equal(w.spacer.h, 0, "the head spacer stands where the pre-fill top was read (at the head the maintainer's round 3 ruled on it stood 300 px taller: the property, asserted before the mechanism)"); assert.equal(w.parked, true);
  assert.equal(w.takes, 2, "the figures were parked again by the first untake, so the re-window took them again");
  assert.equal(w.untakes, 2, "…and gave them back again: the point mapped to no y both times");
  assert.deepEqual(w.writes, [{ writer: "gap-fill", top: 3000, stick: false, from: 3000 }, { writer: "gap-fill", top: 3000, stick: false, from: 3000 }], "the raw pre-fill top, twice, in the layout it was read in");
});

test("the re-window around the point after a fill that left no row on screen, the point mapping to a y: the second build takes nothing new (the first take stands) and the point is put back", () => {
  // the first build renders the window away from the point (every row leaves); the re-window brings them back and the point maps to 2400
  const w = world({ scrollTop: 2350, point: 3.5, yOf: () => 2400, onBuild: (host, call) => { if (call === 1) for (const r of w.rows) host.removeChild(r); else for (const r of w.rows) host.add(r); } });
  w.fill();
  assert.deepEqual(w.builds, [[0, 10, true], [0, 10, true]]);
  assert.equal(w.takes, 1, "one take: the re-window found nothing parked");
  assert.equal(w.untakes, 0, "the point anchored the reader on both writes"); assert.equal(w.spacer.h, 2000 + D, "the take stands");
  assert.deepEqual(w.writes, [{ writer: "gap-fill", top: 2400, stick: false, from: 2350 }, { writer: "gap-fill", top: 2400, stick: false, from: 2350 }], "the point by its turn, on the fill and on the re-window");
});

test("the no-unit fallback (a row in hand that names no unit: its uuid in no event and no turn on the row): the sync is flagged true, the same predicate as the build's, takes, and the row goes back over the take; with neither a row nor a point and no unit under the scroll the sync is flagged false and takes nothing", () => {
  const w = world({ scrollTop: 2350, eventPrefix: "x" });   // the rows' uuids name no event
  w.fill();
  assert.deepEqual(w.builds, [], "no unit to build around");
  assert.deepEqual(w.syncs, [[undefined, true]], "the fallback's sync, flagged: a row is in hand (the maintainer's round 2 ruling: a flagless sync here restored a row over spacers it had not re-sized)");
  assert.equal(w.takes, 1); assert.equal(w.spacer.h, 2000 + D);
  assert.deepEqual(w.writes, [{ writer: "gap-fill", top: 2350 + D, stick: false, from: 2350 }], "r3 at its offset over the re-sized spacer");
  assert.equal(w.untakes, 0);
  const w2 = world({ spacerH: 0, scrollTop: 3000, bottomSpacerH: 5000, point: null, unitAt: -1 });
  w2.fill();
  assert.deepEqual(w2.syncs, [[undefined, false]], "nothing to put back: the sync anchors nothing");
  assert.equal(w2.takes, 0); assert.equal(w2.spacer.h, 0);
  assert.deepEqual(w2.writes, [{ writer: "gap-fill", top: 3000, stick: false, from: 3000 }], "the raw pre-fill top");
});

test("render.ts: the figures are read before the build or the sync, and both raw roads give the take back before their write", () => {
  const fn = RENDER.slice(RENDER.indexOf("function fillInPlace("), RENDER.indexOf("// The display unit holding an absolute turn"));
  assert.match(fn, /const figures = figuresBefore\(v\);\s*\n\s*if \(u >= 0\) renderWindowItems\(/, "the figures read before the build");
  assert.match(fn, /if \(mapped != null\) y = mapped;\s*\n\s*else \{ untakeMeasure\(v, figures\); y = topBefore; \}/, "no row and no point: the take given back, then the raw top");
  assert.match(fn, /if \(y2 == null\) untakeMeasure\(v, figures\);[^\n]*\n\s*writeScroll\(content, y2 != null \? y2 : topBefore, "gap-fill", false, topBefore\);/, "the re-window's point mapping to no y: the take given back, then the raw top");
});
