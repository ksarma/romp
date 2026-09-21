// appendActive's keep and its roads, EXECUTED (PR E, the maintainer's round 3 ruling B). The tail paint of the active view keeps the
// reader's place: a reader at the bottom of an overflowing scroller follows the tail (append-stick, when there is something new to follow:
// scroll-keep.ts followTail), anyone else has the first visible row's offset captured before the sync and restored after it
// (anchor-restore), the raw pre-append scrollTop the fallback when no row is capturable (the viewport inside a spacer) or the captured row
// is gone after the sync (folded into a run that formed, retired by a shrink). The sync takes the figures the unit observer parked when the
// paint anchors (the flag `stick || !!anchor`: the maintainer's round 1 addendum, applied in the author's pass 1b); the one take followed
// by a raw write, the captured row gone, gives the take back before the write since this pass (untakeMeasure: the figures parked again,
// the head spacer back, so the raw top lands in the layout it was read in), a road no harness executed and the body did not disclose until
// the maintainer's round 3. appendActive, captureScrollAnchor, restoreScrollAnchor and atBottom are lifted from render.ts and run over the
// toggle harness's layout model (a head spacer, rows of known heights, a scroller with a viewport); the stubbed syncView records the flag,
// models production's gate (a take under the flag grows the head spacer by the take's delta) and the world's DOM change; followTail and
// atBottomDist are the real ones. Synthetic uuids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { atBottomDist, followTail } from "./scroll-keep";
import { hideEdges } from "../test-dom-shim";

const requireCjs = createRequire(__filename);
const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");

function liftBetween(startAnchor: string, endAnchor: string): string {
  const a = RENDER.indexOf(startAnchor), b = RENDER.indexOf(endAnchor, a);
  assert.ok(a > 0 && b > a, `anchors not found: ${startAnchor.slice(0, 40)} or ${endAnchor.slice(0, 40)} moved; re-anchor`);
  return requireCjs("esbuild").transformSync(RENDER.slice(a, b), { loader: "ts" }).code;
}

/** The layout model: the scroller holds one view whose children stack from offset 0, each of a known height; a row's client rect is its
 *  offset less the scroller's scrollTop (the scroller's own rect top is 0). */
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
  getBoundingClientRect() { const top = this.host!.offsetOf(this) - this.host!.content.scrollTop; return { top, bottom: top + this.h }; }
}
class Host {
  children: Node[] = [];
  constructor(public content: Content) { content.host = this; hideEdges(this); }
  add(n: Node): Node { n.host = this; this.children.push(n); return n; }
  removeChild(n: Node): void { this.children = this.children.filter((c) => c !== n); }
  offsetOf(n: Node): number { let y = 0; for (const c of this.children) { if (c === n) return y; y += c.h; } throw new Error("not a child"); }
  querySelectorAll(sel: string): Node[] { assert.equal(sel, "[data-uuid]", "captureScrollAnchor's selector"); return this.children.filter((c) => c.dataset.uuid != null); }
  querySelector(sel: string): Node | null { const m = /^\[data-uuid="([^"]*)"\]$/.exec(sel); assert.ok(m, "restoreScrollAnchor's selector: " + sel); return this.children.find((c) => c.dataset.uuid === m![1]) ?? null; }
}

type Opts = { spacerH?: number; n?: number; rowH?: number; clientHeight?: number; scrollTop: number; bottomSpacerH?: number; parked?: boolean };
type World = { content: Content; host: Host; v: any; spacer: Node; rows: Node[]; writes: Write[]; syncs: Array<[boolean | undefined, boolean | undefined]>; untakes: number; parked: boolean; append: () => void; onSync: (anchored: boolean) => void };
const D = 300;   // the take's delta: the head spacer re-sized by the re-measured figure over the head gap's turns

/** A view with a head spacer of `spacerH`, `n` rows of `rowH` each (uuids r0..), in a scroller of `clientHeight`, the reader at
 *  `scrollTop`; `parked`: a figure waits for a taker. The stubbed sync records the flag it is handed, takes under it (production's gate:
 *  syncViewInner's `anchored && applyMeasure`, the head spacer growing by D) and then runs `onSync`, the world's DOM change; the stubbed
 *  untake gives that take back (spacer-measure.test.ts executes the real pair). */
function world(o: Opts): World {
  const spacerH = o.spacerH ?? 2000, n = o.n ?? 10, rowH = o.rowH ?? 100, clientHeight = o.clientHeight ?? 600;
  const content = new Content(clientHeight); const host = new Host(content);
  const spacer = host.add(new Node(spacerH, "tx-spacer tx-spacer-top"));
  const rows: Node[] = []; for (let i = 0; i < n; i++) rows.push(host.add(new Node(rowH, "turn", "r" + i)));
  if (o.bottomSpacerH) host.add(new Node(o.bottomSpacerH, "tx-spacer tx-spacer-bot"));
  content.scrollTop = o.scrollTop;
  const v: any = { el: host, stick: false, shown: true };
  const w: any = { content, host, v, spacer, rows, writes: [] as Write[], syncs: [] as Array<[boolean | undefined, boolean | undefined]>, untakes: 0, onSync: () => {} };
  const H: any = { content, v, writes: w.writes, parked: o.parked ?? true, took: false, atBottomDist, followTail,
                   sync: (atBottom: boolean | undefined, anchored: boolean) => { w.syncs.push([atBottom, anchored]); if (anchored && H.parked) { H.parked = false; spacer.h += D; H.took = true; } w.onSync(anchored); },
                   untake: () => { w.untakes++; if (!H.took) return false; H.took = false; H.parked = true; spacer.h -= D; return true; } };
  const js = liftBetween("function appendActive() {", "// Row heights change when the pane is resized")
           + liftBetween("function captureScrollAnchor(", "// Live tail-append to the ACTIVE view")
           + liftBetween("function atBottom(", "function nearBottomForSend(");
  const prelude = `
    const H = HOOKS;
    const document = { getElementById: (id) => (id === "content" ? H.content : null) };
    const activeId = "A"; const views = new Map([["A", H.v]]); const skeletonTabs = { ids: new Set() };
    const showActive = () => { throw new Error("appendActive fell through to showActive: no view to append to"); };
    const syncView = (id, atBottom, anchored) => { H.sync(atBottom, anchored); };
    const figuresBefore = (v) => ({ parked: H.parked }); const untakeMeasure = (v, fig) => H.untake();
    const syncHostOfflineFoot = () => {}; const updateStatusline = () => {}; const scheduleRailSticky = () => {}; const updateJumpBtn = () => {};
    const followTail = H.followTail; const atBottomDist = H.atBottomDist;
    const writeScroll = (c, top, writer, stick = false, from) => { H.writes.push({ writer, top, stick, from }); c.scrollTop = Math.max(0, Math.min(top, c.scrollHeight - c.clientHeight)); };
    const cssEscape = (s) => s;
  `;
  w.append = new Function("HOOKS", prelude + js + "\nreturn appendActive;")(H) as () => void;
  Object.defineProperty(w, "parked", { get: () => H.parked });
  return w as World;
}

test("a reader at the bottom of an overflowing scroller: the sync is flagged by the follow, takes the parked figure, and the paint writes the grown scroller's bottom (append-stick, the pre-append top its origin); nothing is given back", () => {
  const w = world({ scrollTop: 3000 - 600 });
  w.onSync = () => { w.host.add(new Node(100, "turn", "r10")); };   // a new row at the tail
  w.append();
  assert.deepEqual(w.syncs, [[true, true]], "atBottom true, anchored by the follow");
  assert.equal(w.spacer.h, 2000 + D, "the sync took");
  assert.deepEqual(w.writes, [{ writer: "append-stick", top: 3000 + 100 + D, stick: true, from: 2400 }], "the bottom of the grown scroller (the row and the taken figure), the pre-append top its origin");
  assert.equal(w.untakes, 0, "the follow anchors: the take stands"); assert.equal(w.parked, false);
});

test("a scrolled-up reader whose captured row survives the sync: the sync is flagged by the anchor, takes, and the row goes back at its offset over the re-sized spacer (anchor-restore); the take stands", () => {
  const w = world({ scrollTop: 2350 });   // r3 under the viewport top, 50 px above it
  w.onSync = () => { w.host.add(new Node(100, "turn", "r10")); };
  w.append();
  assert.deepEqual(w.syncs, [[false, true]], "scrolled up (atBottom false), anchored by the captured row");
  assert.equal(w.spacer.h, 2000 + D, "the sync took");
  assert.deepEqual(w.writes, [{ writer: "anchor-restore", top: 2350 + D, stick: false, from: 2350 }], "r3 at its offset, 300 px further down the document");
  assert.equal(w.rows[3].getBoundingClientRect().top, -50, "the row did not move on screen");
  assert.equal(w.untakes, 0); assert.equal(w.parked, false);
});

test("a scrolled-up reader whose captured row is GONE after the sync (folded into a run that formed, retired by a shrink): the sync took on the intent, the restore misses, the take is given back and the raw pre-append top lands in the layout it was read in (the maintainer's round 3 ruling B: until then the take stood and the reader moved by its delta, on a road no harness executed)", () => {
  const w = world({ scrollTop: 2350 });
  w.onSync = () => { w.host.removeChild(w.rows[3]); w.host.removeChild(w.rows[4]); };   // r3 and r4 folded away by the paint
  w.append();
  assert.deepEqual(w.syncs, [[false, true]], "a row was captured, so the sync was flagged: the row's fate is known only after the sync");
  assert.equal(w.spacer.h, 2000, "the head spacer stands where the pre-append top was read (at the head the maintainer's round 3 ruled on it stood 300 px taller under the raw write: the property, asserted before the mechanism so the red-before is on it)");
  assert.equal(w.untakes, 1, "the restore missed: the take is given back before the raw write");
  assert.equal(w.parked, true, "the figures wait for a paint that anchors");
  assert.deepEqual(w.writes, [{ writer: "append-raw", top: 2350, stick: false, from: 2350 }], "the raw write: target and origin the pre-append top, exact in the layout it was read in");
});

test("no capturable row (the viewport inside a spacer): the sync is flagged false, nothing is taken, nothing is given back, and the raw write stands", () => {
  const w = world({ spacerH: 0, scrollTop: 3000, bottomSpacerH: 5000 });   // rows 0..1000, then a 5000 px bottom spacer; the reader at 3000 sees no row
  w.append();
  assert.deepEqual(w.syncs, [[false, false]], "no row to put back: the paint anchors nothing and takes nothing");
  assert.equal(w.spacer.h, 0, "nothing taken"); assert.equal(w.parked, true, "still parked");
  assert.equal(w.untakes, 1, "the raw road asks; nothing was taken by this paint, so nothing is given back");
  assert.deepEqual(w.writes, [{ writer: "append-raw", top: 3000, stick: false, from: 3000 }]);
});

test("a reader at the very bottom with nothing new and nothing parked (a status-only tail): the sync is flagged by the follow, takes nothing, and the follow's write is the bottom they are at (followTail: a reader at the very bottom is followed, a no-op pin); nothing is given back", () => {
  const w = world({ scrollTop: 3000 - 600, parked: false });
  w.append();
  assert.deepEqual(w.syncs, [[true, true]]);
  assert.equal(w.spacer.h, 2000, "nothing parked: nothing taken");
  assert.deepEqual(w.writes, [{ writer: "append-stick", top: 3000, stick: true, from: 2400 }], "the bottom, where they already are"); assert.equal(w.untakes, 0);
});

test("render.ts: the figures are read between the capture and the sync, and the raw road gives the take back before its write", () => {
  const fn = RENDER.slice(RENDER.indexOf("function appendActive() {"), RENDER.indexOf("// Row heights change when the pane is resized"));
  assert.match(fn, /const anchor = !stick && v \? captureScrollAnchor\(content, v\) : null;\n\s*const figures = v \? figuresBefore\(v\) : null;/, "the figures read after the capture");
  assert.ok(fn.indexOf("const figures = ") < fn.indexOf("syncView(activeId, stick, stick || !!anchor);"), "…before the sync that may take them");
  assert.match(fn, /else if \(!\(v && restoreScrollAnchor\(content, v, anchor, before\)\)\) \{ if \(v && figures\) untakeMeasure\(v, figures\); writeScroll\(content, before, "append-raw", false, before\); \}/, "the raw road: the take given back, then the write");
});
