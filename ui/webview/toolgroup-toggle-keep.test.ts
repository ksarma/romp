// A tool-run toggle keeps the reader's place (PR E review round 1, high). toggleToolGroup repaints the active view through a window build
// (syncView over a stale view: renderWindowItems), and a build takes the figures the unit observer parked since the last paint
// (applyMeasure), so the head spacer above the viewport can change height under the reader by the re-measured per-turn figure times the
// head gap's turns; the toggle then restored the raw pre-toggle scrollTop, moving a scrolled-up reader by that delta. The keep is
// appendActive's: a reader at the bottom keeps the raw write (a collapse makes the transcript shorter, the browser clamps them at the
// forced layout and the write claims that move with the pre-toggle top as its origin; an expand leaves the run's head where it was);
// anyone else has the first visible row's offset captured before the sync and restored after it, the raw write standing as the fallback
// when no row is capturable or the anchor row was inside the run that collapsed. The build's sync is flagged by whether a row was
// captured (review round 1b): a bottom reader's and a row-less reader's build takes no parked figure, since their raw write would move
// them by it (a figure parked while the reader was off the bottom has no paint asked for, so an idle session's first paint at the bottom
// can be the toggle); the one take followed by a raw write is the anchor row gone in the collapse, the PR's disclosed residual.
// toggleToolGroup, captureScrollAnchor, restoreScrollAnchor and atBottom are lifted from render.ts and run over a layout model: a head
// spacer, rows of known heights, a scroller with a viewport; the stubbed syncView models production's gate (renderWindowItems takes
// under the flag alone): with a figure parked, it grows the head spacer by the take's delta when, and only when, the toggle hands it
// anchored true. Synthetic uuids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { atBottomDist } from "./scroll-keep";
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
  constructor(public clientHeight: number) {}
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

type World = { content: Content; host: Host; v: any; writes: Write[]; open: Set<string>; toggle: (key: string) => void; spacer: Node; rows: Node[]; onSync: () => void; syncs: Array<[boolean | undefined, boolean | undefined]>; take: (delta?: number) => void };
/** A view with a head spacer of `spacerH`, `n` rows of `rowH` each (uuids r0..), in a scroller of `clientHeight`, the reader at
 *  `scrollTop`; `onSync` is what the stubbed window build does to the DOM (a collapse drops rows, an expand adds them), and `take` is
 *  production's gate over a parked figure: the head spacer grows by the take's delta only when the sync in progress was handed
 *  anchored true (renderWindowItems: `if (anchored) applyMeasure(v)`; syncViewInner: `if (anchored && applyMeasure(v))`). */
function world(spacerH: number, n: number, rowH: number, clientHeight: number, scrollTop: number, bottomSpacerH = 0): World {
  const content = new Content(clientHeight); const host = new Host(content);
  const spacer = host.add(new Node(spacerH, "tx-spacer tx-spacer-top"));
  const rows: Node[] = []; for (let i = 0; i < n; i++) rows.push(host.add(new Node(rowH, "turn", "r" + i)));
  if (bottomSpacerH > 0) host.add(new Node(bottomSpacerH, "tx-spacer tx-spacer-bot"));
  content.scrollTop = scrollTop;
  const writes: Write[] = []; const open = new Set<string>();
  const v: any = { el: host, stale: false };
  const syncs: Array<[boolean | undefined, boolean | undefined]> = [];   // what the toggle hands syncView: (atBottom, anchored)
  const w: any = { content, host, v, writes, open, spacer, rows, onSync: () => {}, syncs };
  const js = liftBetween("function toggleToolGroup(", "// Re-render every view from scratch") + liftBetween("function captureScrollAnchor(", "// Live tail-append to the ACTIVE view") + liftBetween("function atBottom(", "function nearBottomForSend(");
  const prelude = `
    const H = HOOKS;
    const openFolds = H.open;
    const document = { getElementById: (id) => (id === "content" ? H.content : null) };
    const activeId = "A"; const views = new Map([["A", H.v]]);
    const syncView = (id, atBottom, anchored) => { H.synced = (H.synced || 0) + 1; H.syncs.push([atBottom, anchored]); H.onSync(); };
    const writeScroll = (c, top, writer, stick = false, from) => { H.writes.push({ writer, top, stick, from }); c.scrollTop = Math.max(0, Math.min(top, c.scrollHeight - c.clientHeight)); };
    const cssEscape = (s) => s;
    const refillOpenCommentPop = () => {}; const scheduleRailSticky = () => {};
    const atBottomDist = H.atBottomDist;
  `;
  const hooks: any = { open, content, v, writes, atBottomDist, syncs, onSync: () => w.onSync() };
  w.toggle = new Function("HOOKS", prelude + js + "\nreturn toggleToolGroup;")(hooks) as (key: string) => void;
  w.take = (delta = D) => { const last = syncs[syncs.length - 1]; assert.ok(last, "take is called inside the sync"); if (last[1] === true) spacer.h += delta; };
  return w as World;
}
const D = 300;   // the take's delta: the head spacer re-sized by the re-measured figure over the head gap's turns

test("a scrolled-up reader in a session with a head gap: the toggle's build re-sizes the head spacer and the reader's row keeps its offset (the write's target moves by the spacer's delta, the pre-toggle top its origin)", () => {
  // the spacer 2000 px, ten rows of 100 px (3000 px in all), a 600 px viewport, the reader at 2350: the row under the viewport top is r3 (2300..2400), 50 px above it
  const w = world(2000, 10, 100, 600, 2350);
  w.onSync = () => w.take();
  w.toggle("tg:k");
  assert.ok(w.open.has("tg:k"), "the fold opened");
  assert.equal(w.v.stale, true, "the view was marked stale for the build");
  assert.deepEqual(w.syncs, [[undefined, true]], "the build's sync is told it anchors (no atBottom, the flag true: a row was captured): the keep below covers a figure taken there (review round 1b)");
  assert.equal(w.spacer.h, 2000 + D, "the build took the parked figure");
  assert.deepEqual(w.writes, [{ writer: "anchor-restore", top: 2350 + D, stick: false, from: 2350 }], "one write: the anchor row (r3) put back at its offset, 300 px further down the document, from the pre-toggle top");
  assert.equal(w.content.scrollTop, 2350 + D);
  assert.equal(w.rows[3].getBoundingClientRect().top, -50, "r3 is where it was on screen");
  // the toggle back: the spacer shrinks by the same delta (a figure parked again), the row stays put
  w.onSync = () => w.take(-D);
  w.toggle("tg:k");
  assert.ok(!w.open.has("tg:k"), "the fold closed");
  assert.deepEqual(w.writes.slice(-1), [{ writer: "anchor-restore", top: 2350, stick: false, from: 2350 + D }]);
  assert.equal(w.rows[3].getBoundingClientRect().top, -50);
});

test("a reader at the bottom keeps the raw write with the pre-toggle top as its origin (the collapse clamp is claimed, an expand leaves the head where it was); no anchor is captured for them, their sync is flagged false, and a parked figure is not taken (the raw write would move them by it)", () => {
  const w = world(2000, 10, 100, 600, 3000 - 600);   // at the bottom of an overflowing scroller
  w.onSync = () => { w.take(); w.host.removeChild(w.rows[9]); w.host.removeChild(w.rows[8]); };   // a collapse: two rows go, the transcript shorter
  w.toggle("tg:k");
  assert.deepEqual(w.syncs, [[undefined, false]], "no row captured, so the sync is told it does not anchor (review round 1b: a figure parked while this reader was off the bottom is asked for by no paint, and the toggle's raw write must not take it)");
  assert.equal(w.spacer.h, 2000, "the head spacer stands: nothing taken");
  assert.deepEqual(w.writes, [{ writer: "toolgroup-toggle", top: 2400, stick: false, from: 2400 }], "the raw write: target and origin the pre-toggle top (scroll-write.test.ts and the pending-bubble lab pin this shape)");
  // an expand at the bottom: rows come back, the write is the same raw one, the reader stays where they were rather than following to the bottom
  const w2 = world(2000, 10, 100, 600, 3000 - 600);
  const r4Before = w2.rows[4].getBoundingClientRect().top;
  assert.equal(r4Before, 0, "r4 sits under the viewport top before the toggle");
  w2.onSync = () => { w2.take(); w2.host.add(new Node(100, "turn tg-child", "r10")); w2.host.add(new Node(100, "turn tg-child tg-last", "r11")); };
  w2.toggle("tg:k");
  assert.deepEqual(w2.syncs, [[undefined, false]]);
  assert.equal(w2.spacer.h, 2000, "nothing taken on the expand either");
  assert.deepEqual(w2.writes, [{ writer: "toolgroup-toggle", top: 2400, stick: false, from: 2400 }]);
  assert.equal(w2.content.scrollTop, 2400, "the head of the run is where it was; its rows open under it");
  assert.equal(w2.rows[4].getBoundingClientRect().top, r4Before, "the row under the viewport top did not move (with the flag true it would sit 300 px lower)");
});

test("the anchor row was inside the run that collapsed and is gone after the build: the raw write stands as the fallback, the pre-toggle top its origin; a row was captured, so this build took (the PR's disclosed residual: the one take followed by a raw write)", () => {
  const w = world(2000, 10, 100, 600, 2350);   // r3 under the viewport top, a member row of the run
  w.onSync = () => { w.take(); w.host.removeChild(w.rows[3]); w.host.removeChild(w.rows[4]); };
  w.toggle("tg:k");
  assert.deepEqual(w.syncs, [[undefined, true]], "a row was captured before the build, so the sync was flagged (the row's fate is known only after the build)");
  assert.equal(w.spacer.h, 2000 + D, "the build took the parked figure");
  assert.deepEqual(w.writes, [{ writer: "toolgroup-toggle", top: 2350, stick: false, from: 2350 }], "no anchor to restore: the raw write, its origin the top read before the build (the reader is 300 px off where they were: the residual)");
});

test("no row capturable (the viewport inside a spacer): the sync is flagged false, nothing is taken, and the raw write stands", () => {
  const w = world(0, 10, 100, 600, 3000, 5000);   // rows 0..1000, then a 5000 px bottom spacer; the reader at 3000 sees no row
  w.onSync = () => w.take();
  w.toggle("tg:k");
  assert.deepEqual(w.syncs, [[undefined, false]], "no row to put back: the sync does not anchor (the flag is `!!anchor`, not `!stick`: this reader is off the bottom and still takes nothing)");
  assert.equal(w.spacer.h, 0, "nothing taken");
  assert.deepEqual(w.writes, [{ writer: "toolgroup-toggle", top: 3000, stick: false, from: 3000 }]);
});

test("render.ts: the toggle's keep is appendActive's: the stick check, the anchor captured before the sync only when not at the bottom, the sync flagged by that capture, the anchor restored after it, the raw write the fallback with the pre-toggle top as origin", () => {
  const t = RENDER.slice(RENDER.indexOf("function toggleToolGroup("), RENDER.indexOf("// Re-render every view from scratch"));
  assert.match(t, /const stick = !!content && content\.scrollHeight > content\.clientHeight \+ 2 && atBottom\(content\);/, "the stick check (appendActive's)");
  assert.match(t, /const anchor = content && v && !stick \? captureScrollAnchor\(content, v\) : null;/, "the anchor captured before the sync, not for a bottom reader");
  assert.ok(t.indexOf("captureScrollAnchor(") < t.indexOf("syncView(activeId, undefined, !!anchor)"), "…before the build, whose sync is flagged by whether a row was captured (review round 1b: the keep below puts the row back, so that paint may take a parked figure; a bottom or row-less reader's raw write anchors nothing and takes nothing)");
  assert.doesNotMatch(t, /syncView\(activeId, undefined, (?:true|!stick)\)/, "neither the flag true for every reader nor `!stick` (a row-less reader off the bottom would take and write raw)");
  assert.match(t, /if \(content && !\(anchor && v && restoreScrollAnchor\(content, v, anchor, top\)\)\) writeScroll\(content, top, "toolgroup-toggle", false, top\);/, "the restore after it, the raw write its fallback, `top` the origin of both");
  assert.doesNotMatch(t, /scroll preserved/, "the old comment's claim is gone");
});
