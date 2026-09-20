// landActive's take and its roads, EXECUTED (PR E review round 2, A). A land takes the figures the unit observer parked since the last
// paint (applyMeasure: the head spacer and the gap units re-sized) on every road but the nothing-armed re-show, BEFORE its landing
// attempt, because the roads that land read the target's live rect (scrollToAnchor, landOn) and a resident target rebuilds nothing, so a
// take after the attempt would re-size the spacer under a row just placed. The take is decided on what is ARMED, not on the outcome: a
// land whose anchor MISSES (nowhere in the transcript, the wrong kind, a fetch armed) took the figures and then fell through to the raw
// land-saved write of a scrollTop measured in the pre-resize layout, and the reader moved by the spacer's delta (round 1's HIGH 2 shape
// one road over; the comment in the source and the pin over it said the road could not happen). The fallback now restores the row the
// SAVED place held, captured at that place before the take (the scroller does not hold the saved place yet on a switch: the leaving
// tab's position is still under the viewport). The raw write stands whenever that restore finds no row to put back, three roads: nothing
// was armed (no take, the saved scrollTop exact); no row was capturable (the saved place inside a spacer); the captured row is gone,
// because the attempt's window build around the anchor's unit (scrollToAnchor's pointer-not-rendered and pointer-wrong-kind roads)
// replaced the rows before its re-query missed, the sub-road keepPlaceAcrossWindow's double miss has too (review round 3: the comment,
// the pin and the body had named two roads). landActive, captureScrollAnchor and restoreScrollAnchor are lifted from
// render.ts and run over a layout model (the toggle harness's: a head spacer, rows of known heights, a scroller with a viewport); the
// stubs record the take, the landing attempt and every write, and scrollToAnchor answers what the world says. keepPlaceAcrossWindow,
// the other taker pinned by source text alone until this round, is lifted the same way over both its roads (the direct restore, the
// deep-link re-land with the kept offset) and the road where both miss: it takes before the restores (restoreScrollAnchor needs the
// row's y in the re-sized layout), so on a double miss it took and wrote nothing, and the content under the viewport moved by the take's
// delta; the row under the viewport top, captured before the take, now goes back at its offset there. Synthetic uuids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { takeReloadScroll } from "./reload-restore";
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
  children: Node[] = []; style: Record<string, string> = { display: "" };
  constructor(public content: Content) { content.host = this; hideEdges(this); }
  add(n: Node): Node { n.host = this; this.children.push(n); return n; }
  offsetOf(n: Node): number { let y = 0; for (const c of this.children) { if (c === n) return y; y += c.h; } throw new Error("not a child"); }
  querySelectorAll(sel: string): Node[] { assert.equal(sel, "[data-uuid]", "captureScrollAnchor's selector"); return this.children.filter((c) => c.dataset.uuid != null); }
  querySelector(sel: string): Node | null { const m = /^\[data-uuid="([^"]*)"\]$/.exec(sel); assert.ok(m, "restoreScrollAnchor's selector: " + sel); return this.children.find((c) => c.dataset.uuid === m![1]) ?? null; }
}

type Arm = { anchor?: string; t?: number; keepY?: number; seek?: { sid: string; uuid: string; kind: string }; reload?: unknown; land?: boolean; landT?: boolean; rebuild?: (host: Host) => void };
type Opts = { spacerH?: number; n?: number; rowH?: number; clientHeight?: number; saved: number; scrollTop?: number; shown?: boolean; stick?: boolean; parked?: boolean; bottomSpacerH?: number };
type World = { content: Content; host: Host; v: any; spacer: Node; rows: Node[]; writes: Write[]; calls: any[]; rows_: any[]; toasts: string[]; land: (content: Content | null, v: any) => void };
const D = 300;   // the take's delta: the head spacer re-sized by the re-measured figure over the head gap's turns

/** A view of `n` rows of `rowH` under a head spacer of `spacerH` (uuids r0..), in a scroller of `clientHeight`; `saved` is the view's
 *  saved place (v.scrollTop, recorded when the tab was left) and `scrollTop` the scroller's position when the land runs (the saved place
 *  on a re-show; the LEAVING tab's on a switch, the default here being the saved place). `parked`: a figure waits for a taker, and the
 *  take grows the head spacer by D (the stubbed applyMeasure models what sizeSpacers draws from the taken figure). `arm` is what the
 *  land finds armed and how the stubbed landings answer (`land`: scrollToAnchor's answer, `landT`: landNearestMoment's; `rebuild` runs
 *  over the host before scrollToAnchor answers: the window rebuilt around the anchor's unit, rows leaving). */
function world(o: Opts, arm: Arm = {}): World {
  const spacerH = o.spacerH ?? 2000, n = o.n ?? 10, rowH = o.rowH ?? 100, clientHeight = o.clientHeight ?? 600;
  const content = new Content(clientHeight); const host = new Host(content);
  const spacer = host.add(new Node(spacerH, "tx-spacer tx-spacer-top"));
  const rows: Node[] = []; for (let i = 0; i < n; i++) rows.push(host.add(new Node(rowH, "turn", "r" + i)));
  if (o.bottomSpacerH) host.add(new Node(o.bottomSpacerH, "tx-spacer tx-spacer-bot"));
  content.scrollTop = o.scrollTop ?? o.saved;
  const v: any = { el: host, scrollTop: o.saved, shown: o.shown ?? true, stick: o.stick ?? false };
  const H: any = { content, v, spacer, writes: [] as Write[], calls: [] as any[], rows: [] as any[], toasts: [] as string[], deferred: [] as any[],
                   parked: o.parked ?? true, delta: D, arm, takeReloadScroll,
                   land: (uuid: string) => { if (arm.rebuild) arm.rebuild(host); return !!arm.land; }, landT: (t: number) => !!arm.landT };
  const js = liftBetween("function landActive(content: HTMLElement | null, v: View): void {", "// Scroll ANCHORING for scrolled-up re-renders")
           + liftBetween("function captureScrollAnchor(", "// Live tail-append to the ACTIVE view");
  const prelude = `
    const H = HOOKS;
    let pendingAnchor = H.arm.anchor ?? null, pendingAnchorT = H.arm.t ?? null, pendingAnchorIntent = null, pendingAnchorKind = null;
    let pendingAnchorKeepY = H.arm.keepY ?? null, pendingAnchorClick = false, pendingReloadScroll = H.arm.reload ?? null;
    let seek = H.arm.seek ?? null, landTrail = [], landSettling = null, anchorPendingOlder = false;
    const activeId = "A"; const views = new Map([["A", H.v]]); const sessions = new Map([["A", { name: "web" }]]);
    const document = { getElementById: (id) => (id === "content" ? H.content : null) };
    const vscodeApi = { postMessage: (row) => { H.rows.push(row); } };
    const whenChatVisible = (cb) => { H.deferred.push(cb); };
    const takeReloadScroll = H.takeReloadScroll;
    const applyMeasure = (v) => { H.calls.push("applyMeasure"); if (!H.parked) return false; H.parked = false; H.spacer.h += H.delta; return true; };
    const redrawGapUnits = () => { H.calls.push("redrawGapUnits"); };
    const sizeSpacers = () => { H.calls.push("sizeSpacers"); };
    const scrollToAnchor = (uuid) => { H.calls.push(["scrollToAnchor", uuid]); return H.land(uuid); };
    const landNearestMoment = (t) => { H.calls.push(["landNearestMoment", t]); return H.landT(t); };
    const revealProgressTick = () => {}; const clearSeek = () => { H.calls.push("clearSeek"); }; const showSeekNote = () => { H.calls.push("showSeekNote"); };
    const settleSample = () => {}; const landToast = (m) => { H.toasts.push(m); }; const notifyShell = () => {};
    const writeScroll = (c, top, writer, stick = false, from) => { H.writes.push({ writer, top, stick, from }); c.scrollTop = Math.max(0, Math.min(top, c.scrollHeight - c.clientHeight)); };
    const scheduleRailSticky = () => {}; const updateJumpBtn = () => {}; const cssEscape = (s) => s;
  `;
  const land = new Function("HOOKS", prelude + js + "\nreturn landActive;")(H) as (content: Content | null, v: any) => void;
  return { content, host, v, spacer, rows, writes: H.writes, calls: H.calls, rows_: H.rows, toasts: H.toasts, land };
}
const takes = (w: World) => w.calls.filter((c) => c === "applyMeasure").length;
const attemptAfterTake = (w: World) => { const t = w.calls.indexOf("applyMeasure"), a = w.calls.findIndex((c) => Array.isArray(c)); return t >= 0 && a >= 0 && t < a; };
// the reader's saved place in these worlds: 2350 in a 3000 px view under a 2000 px spacer, a 600 px viewport: the row under the
// viewport top is r3 (2300..2400), 50 px above it
const R3_OFFSET = -50;

test("the nothing-armed re-show of a scrolled-up view (land-saved): no take, the spacers sized as they were, the raw write at the saved place", () => {
  const w = world({ saved: 2350 });
  w.land(w.content, w.v);
  assert.equal(takes(w), 0, "nothing armed: the land takes nothing (a spacer written here would move the saved place)");
  assert.deepEqual(w.calls.filter((c) => typeof c === "string"), ["sizeSpacers"], "the spacers take the figures the view holds, and nothing else runs");
  assert.equal(w.spacer.h, 2000, "the parked figure stays parked for the next anchoring paint");
  assert.deepEqual(w.writes, [{ writer: "land-saved", top: 2350, stick: false, from: undefined }], "the saved scrollTop is exact in a layout nothing re-sized: the raw write");
  assert.equal(w.rows[3].getBoundingClientRect().top, R3_OFFSET, "the row the saved place held is where it was");
  assert.equal(w.v.shown, true);
});

test("an armed anchor that MISSES on a re-show: the take before the attempt, then the row the saved place held is put back at its offset over the re-sized spacer (anchor-restore), never the raw pre-resize scrollTop", () => {
  // a card's anchor nowhere in the transcript (scrollToAnchor false: pointer-not-rendered), a figure parked, the scroller at the saved place
  const w = world({ saved: 2350 }, { anchor: "11111111-2222-4333-8444-000000000001", land: false });
  w.land(w.content, w.v);
  assert.equal(takes(w), 1, "an armed land takes, whatever its outcome (the take is decided before the attempt)");
  assert.ok(attemptAfterTake(w), "…and before the landing attempt, which reads live rects");
  assert.deepEqual(w.calls.filter((c) => Array.isArray(c)), [["scrollToAnchor", "11111111-2222-4333-8444-000000000001"]], "one attempt");
  assert.equal(w.spacer.h, 2000 + D, "the head spacer grew by the taken figure's delta");
  assert.deepEqual(w.writes, [{ writer: "anchor-restore", top: 2350 + D, stick: false, from: undefined }],
    "the fallback restores the row the saved place held (r3) at its offset, 300 px further down the document; the raw land-saved write at 2350 would leave the reader 300 px above their place");
  assert.equal(w.rows[3].getBoundingClientRect().top, R3_OFFSET, "r3 is where the saved place had it (with the raw write it would sit at +250, moved by the spacer's delta)");
  assert.equal(w.rows_.length, 1, "the miss files its locate row"); assert.equal(w.rows_[0].ok, false);
  assert.deepEqual(w.toasts, ["couldn't locate this in the transcript"], "…and says so: the road stays the error road it was");
});

test("the same miss on a tab SWITCH: the scroller still holds the leaving tab's position, so the row is captured at the SAVED place, not under the viewport as it stands, and put back there", () => {
  // the leaving tab was at its top (scrollTop 0); the entering view's saved place is 2350. A capture at the scroller's own position would
  // hold r0 (the first row, 2000 px below a viewport at 0) and put the reader at r0, a place they never were
  const w = world({ saved: 2350, scrollTop: 0 }, { anchor: "11111111-2222-4333-8444-000000000001", land: false });
  w.land(w.content, w.v);
  assert.equal(takes(w), 1);
  assert.equal(w.spacer.h, 2000 + D);
  assert.deepEqual(w.writes, [{ writer: "anchor-restore", top: 2350 + D, stick: false, from: undefined }], "r3, the row at the saved place, back at its offset");
  assert.equal(w.rows[3].getBoundingClientRect().top, R3_OFFSET);
});

test("an armed miss with no row at the saved place (the saved place inside a spacer): the take, then the raw land-saved write, the one road left to it", () => {
  // rows 0..1000 then a 5000 px bottom spacer; the saved place at 3000 has no row at or below the viewport top
  const w = world({ spacerH: 0, saved: 3000, bottomSpacerH: 5000 }, { anchor: "11111111-2222-4333-8444-000000000002", land: false });
  w.land(w.content, w.v);
  assert.equal(takes(w), 1, "the take is on the arm, not the row");
  assert.deepEqual(w.writes, [{ writer: "land-saved", top: 3000, stick: false, from: undefined }], "nothing to put back: the raw write stands");
});

test("an armed miss whose attempt REBUILT the window around the anchor's unit (scrollToAnchor's pointer-not-rendered and pointer-wrong-kind roads): the captured row left with the old rows, so the restore misses and the raw land-saved write of the pre-resize scrollTop follows the take, the third of the raw write's roads; a rebuild that renders the saved place's row again under its uuid is restored", () => {
  // the build removes every child and renders the units around the anchor's: rows 20..29 stand where 0..9 stood, and r3 is gone
  const gone = (host: Host) => { host.children = [host.children[0]]; for (let i = 20; i < 30; i++) host.add(new Node(100, "turn", "r" + i)); };
  const w = world({ saved: 2350 }, { anchor: "11111111-2222-4333-8444-000000000006", land: false, rebuild: gone });
  w.land(w.content, w.v);
  assert.equal(takes(w), 1, "the take is on the arm");
  assert.ok(attemptAfterTake(w));
  assert.equal(w.spacer.h, 2000 + D, "the head spacer grew under the rebuilt rows");
  assert.deepEqual(w.writes, [{ writer: "land-saved", top: 2350, stick: false, from: undefined }],
    "no row of the captured DOM is left to put back: the raw write at the pre-resize saved place stands, and the reader is in the window built around the anchor (the residual the body names beside keepPlaceAcrossWindow's double miss after a rebuild)");
  assert.deepEqual(w.toasts, ["couldn't locate this in the transcript"], "the error road it was");
  // the same rebuild rendering the saved place's row again (a fresh node, the same uuid): the restore finds it, so the rule is the
  // restore's answer, not whether a rebuild ran
  const again = (host: Host) => { host.children = [host.children[0]]; for (let i = 0; i < 10; i++) host.add(new Node(100, "turn", "r" + i)); };
  const w2 = world({ saved: 2350 }, { anchor: "11111111-2222-4333-8444-000000000006", land: false, rebuild: again });
  w2.land(w2.content, w2.v);
  assert.equal(takes(w2), 1);
  assert.deepEqual(w2.writes, [{ writer: "anchor-restore", top: 2350 + D, stick: false, from: undefined }], "the rebuilt r3 is put back at its offset over the re-sized spacer");
  assert.equal(w2.host.children[4].getBoundingClientRect().top, R3_OFFSET, "the new r3 sits where the saved place had the old one");
});

test("the anchoring roads each take once, before the attempt, and landActive writes nothing of its own when the landing placed the reader: an anchor that hits, a moment, a seek; the reload restore and the bottom land take and write their own", () => {
  const anchor = "11111111-2222-4333-8444-000000000003";
  // an anchor that hits: scrollToAnchor placed the reader (landOn's write, inside the stub); a keep-offset re-land (pendingAnchorKeepY) the same
  for (const arm of [{ anchor, land: true }, { anchor, keepY: -50, land: true }] as Arm[]) {
    const w = world({ saved: 2350 }, arm);
    w.land(w.content, w.v);
    assert.equal(takes(w), 1, "one take: " + JSON.stringify(arm)); assert.ok(attemptAfterTake(w), "before the attempt: " + JSON.stringify(arm));
    assert.deepEqual(w.writes, [], "the landing's own write placed the reader; no fallback: " + JSON.stringify(arm));
    assert.equal(w.toasts.length, 0); assert.equal(w.rows_[0].ok, true);
  }
  // a moment (time-only navigation): no anchor, landNearestMoment lands
  const m = world({ saved: 2350 }, { t: 1700000000, landT: true });
  m.land(m.content, m.v);
  assert.equal(takes(m), 1); assert.ok(attemptAfterTake(m));
  assert.deepEqual(m.calls.filter((c) => Array.isArray(c)), [["landNearestMoment", 1700000000]], "the moment's land, no anchor attempt");
  assert.deepEqual(m.writes, []);
  // a durable seek for this tab re-arms the attempt from its uuid; a hit clears the seek
  const s = world({ saved: 2350 }, { seek: { sid: "A", uuid: "11111111-2222-4333-8444-000000000004", kind: "user" }, land: true });
  s.land(s.content, s.v);
  assert.equal(takes(s), 1); assert.ok(attemptAfterTake(s));
  assert.deepEqual(s.calls.filter((c) => Array.isArray(c)), [["scrollToAnchor", "11111111-2222-4333-8444-000000000004"]], "the seek's uuid is the attempt");
  assert.ok(s.calls.includes("clearSeek"), "the landing event ends the seek"); assert.deepEqual(s.writes, []);
  // …and a seek that misses this pass keeps searching (no toast) and puts the saved place's row back over the take
  const s2 = world({ saved: 2350 }, { seek: { sid: "A", uuid: "11111111-2222-4333-8444-000000000004", kind: "user" }, land: false });
  s2.land(s2.content, s2.v);
  assert.equal(takes(s2), 1); assert.ok(s2.calls.includes("showSeekNote")); assert.deepEqual(s2.toasts, []);
  assert.deepEqual(s2.writes, [{ writer: "anchor-restore", top: 2350 + D, stick: false, from: undefined }]);
  // the reload restore, a follow-mode reader: the bottom, after the take
  const r = world({ saved: 2350 }, { reload: { id: "A", top: 2350, stick: true, anchor: null } });
  r.land(r.content, r.v);
  assert.equal(takes(r), 1);
  assert.deepEqual(r.writes.map((x) => [x.writer, x.stick]), [["reload-restore", true]], "the follow-mode reader lands at the bottom"); assert.equal(r.v.stick, true);
  // the reload restore with an anchor row the rebuilt DOM holds: the reload's own anchor restore, after the take
  const r2 = world({ saved: 2350, scrollTop: 0 }, { reload: { id: "A", top: 2350, stick: false, anchor: { uuid: "r3", y: -50 } } });
  r2.land(r2.content, r2.v);
  assert.equal(takes(r2), 1);
  assert.deepEqual(r2.writes, [{ writer: "anchor-restore", top: 2350 + D, stick: false, from: undefined }], "the reload's anchor row at its offset over the re-sized spacer");
  // the bottom land: a view not yet shown, and a follow-mode view
  for (const o of [{ saved: 2350, shown: false }, { saved: 2350, stick: true }] as Opts[]) {
    const b = world(o);
    b.land(b.content, b.v);
    assert.equal(takes(b), 1, "the bottom land takes: " + JSON.stringify(o));
    assert.deepEqual(b.writes.map((x) => [x.writer, x.stick]), [["land-bottom", true]], "…and writes the bottom: " + JSON.stringify(o));
    assert.equal(b.v.shown, true);
  }
});

test("a hidden pane with a jump armed defers the whole land (nothing taken, nothing written) until the pane shows", () => {
  const w = world({ saved: 2350, clientHeight: 0 }, { anchor: "11111111-2222-4333-8444-000000000005", land: true });
  w.land(w.content, w.v);
  assert.equal(takes(w), 0, "no take in a zero-height view"); assert.deepEqual(w.writes, []); assert.deepEqual(w.calls, []);
});

// ── keepPlaceAcrossWindow: the take over its restores, and the double miss (review round 2, tests-4 and correctness-3) ──────────────

type KeepArm = { land?: boolean; older?: boolean; rebuild?: (host: Host) => void };
type KeepWorld = { content: Content; host: Host; spacer: Node; rows: Node[]; writes: Write[]; calls: any[]; keep: (k: { uuid: string; y: number }) => boolean; state: () => { pendingAnchor: string | null; pendingAnchorKeepY: number | null; relandAsk: boolean } };
/** The reader at `scrollTop` over the same view; `parked` a figure waiting; the stubbed scrollToAnchor answers `land`, marks an older fetch
 *  when `older`, and runs `rebuild` over the host first (the window rebuilt around the anchor's unit: rows leave). */
function keepWorld(scrollTop: number, arm: KeepArm = {}, parked = true): KeepWorld {
  const content = new Content(600); const host = new Host(content);
  const spacer = host.add(new Node(2000, "tx-spacer tx-spacer-top"));
  const rows: Node[] = []; for (let i = 0; i < 10; i++) rows.push(host.add(new Node(100, "turn", "r" + i)));
  content.scrollTop = scrollTop;
  const v: any = { el: host, scrollTop, shown: true, stick: false };
  const H: any = { content, v, spacer, writes: [] as Write[], calls: [] as any[], parked, delta: D, arm };
  const js = liftBetween("function keepPlaceAcrossWindow(", "// Scroll/anchor landing + deep-link diagnostics + restamp")
           + liftBetween("function captureScrollAnchor(", "// Live tail-append to the ACTIVE view");
  const prelude = `
    const H = HOOKS;
    let pendingAnchor = null, pendingAnchorKeepY = null, relandAsk = false, anchorPendingOlder = false;
    const applyMeasure = (v) => { H.calls.push("applyMeasure"); if (!H.parked) return false; H.parked = false; H.spacer.h += H.delta; return true; };
    const redrawGapUnits = () => { H.calls.push("redrawGapUnits"); };
    const sizeSpacers = () => { H.calls.push("sizeSpacers"); };
    const scrollToAnchor = (uuid) => { H.calls.push(["scrollToAnchor", uuid, relandAsk, pendingAnchor, pendingAnchorKeepY]); if (H.arm.rebuild) H.arm.rebuild(H.content.host); if (H.arm.older) anchorPendingOlder = true; return !!H.arm.land; };
    const writeScroll = (c, top, writer, stick = false, from) => { H.writes.push({ writer, top, stick, from }); c.scrollTop = Math.max(0, Math.min(top, c.scrollHeight - c.clientHeight)); };
    const cssEscape = (s) => s;
  `;
  const api = new Function("HOOKS", prelude + js + "\nreturn { keep: (k) => keepPlaceAcrossWindow(H.content, H.v, k), state: () => ({ pendingAnchor, pendingAnchorKeepY, relandAsk }) };")(H);
  return { content, host, spacer, rows, writes: H.writes, calls: H.calls, keep: api.keep, state: api.state };
}
const keepTakes = (w: KeepWorld) => w.calls.filter((c) => c === "applyMeasure").length;

test("keepPlaceAcrossWindow, the direct restore: the take first (spacers and gap units re-sized), then the reader's row back at its offset over them; true, one write", () => {
  const w = keepWorld(2350);   // r3 under the viewport top, 50 px above it
  assert.equal(w.keep({ uuid: "r3", y: R3_OFFSET }), true);
  assert.equal(keepTakes(w), 1, "the land of the reader's own row takes");
  assert.deepEqual(w.calls.filter((c) => typeof c === "string"), ["applyMeasure", "redrawGapUnits", "sizeSpacers"], "the take, the gap units, the spacers, before any restore");
  assert.equal(w.spacer.h, 2000 + D);
  assert.deepEqual(w.writes, [{ writer: "anchor-restore", top: 2350 + D, stick: false, from: undefined }], "r3 at its offset, 300 px further down the document");
  assert.equal(w.rows[3].getBoundingClientRect().top, R3_OFFSET, "the row did not move on screen");
  assert.deepEqual(w.calls.filter((c) => Array.isArray(c)), [], "no deep-link attempt: the row was there");
  assert.equal(w.state().pendingAnchor, null);
  // nothing parked: no re-size, the row back where it is
  const w2 = keepWorld(2350, {}, false);
  assert.equal(w2.keep({ uuid: "r3", y: R3_OFFSET }), true);
  assert.equal(keepTakes(w2), 1, "asked"); assert.equal(w2.spacer.h, 2000, "…and nothing to take");
  assert.deepEqual(w2.writes, [{ writer: "anchor-restore", top: 2350, stick: false, from: undefined }]);
});

test("keepPlaceAcrossWindow, the restore missing (the reader's row gone from the rebuilt window): the deep-link re-land with the kept offset, armed and flagged as the re-land of the reader's own row while it runs, disarmed after unless an older fetch is on the wire", () => {
  const w = keepWorld(2350, { land: true });
  assert.equal(w.keep({ uuid: "11111111-2222-4333-8444-000000000011", y: R3_OFFSET }), true);
  assert.equal(keepTakes(w), 1);
  assert.deepEqual(w.calls.filter((c) => Array.isArray(c)), [["scrollToAnchor", "11111111-2222-4333-8444-000000000011", true, "11111111-2222-4333-8444-000000000011", R3_OFFSET]],
    "the attempt runs with relandAsk raised and the anchor armed with the kept offset (the keep-offset write is scrollToAnchor's own)");
  assert.deepEqual(w.state(), { pendingAnchor: null, pendingAnchorKeepY: null, relandAsk: false }, "disarmed after the land, the flag lowered");
  assert.deepEqual(w.writes, [], "the landing wrote; nothing else does");
  // an older fetch pointed at the anchor keeps the arm for chatHead's arrival
  const w2 = keepWorld(2350, { land: false, older: true });
  assert.equal(w2.keep({ uuid: "11111111-2222-4333-8444-000000000011", y: R3_OFFSET }), false);
  assert.deepEqual(w2.state(), { pendingAnchor: "11111111-2222-4333-8444-000000000011", pendingAnchorKeepY: R3_OFFSET, relandAsk: false }, "armed for the arrival");
});

test("keepPlaceAcrossWindow, BOTH restores missing (the reader's row gone and the attempt landing nothing): the take was made, so the row that was under the viewport top goes back at its offset (measured on its own rect), never a take with no write; when the attempt's rebuild dropped that row too, nothing is written and the road is the disclosed residual", () => {
  // the reader's row is nowhere (a fetch is armed for it); before the fix the take grew the head spacer 300 px and nothing was written,
  // so the content under the viewport moved down by 300 px
  const w = keepWorld(2350, { land: false, older: true });
  assert.equal(w.keep({ uuid: "11111111-2222-4333-8444-000000000012", y: R3_OFFSET }), false);
  assert.equal(keepTakes(w), 1, "the take is made before the restores, whatever they find");
  assert.equal(w.spacer.h, 2000 + D);
  assert.deepEqual(w.writes, [{ writer: "anchor-restore", top: 2350 + D, stick: false, from: undefined }], "the row under the viewport top before the take (r3) is put back at its offset");
  assert.equal(w.rows[3].getBoundingClientRect().top, R3_OFFSET, "what the reader saw under the viewport top is still there (it sat 300 px lower with no write)");
  // the same with no fetch armed (an anchor nowhere in the transcript): the arm is dropped, the row still goes back
  const w2 = keepWorld(2350, { land: false });
  assert.equal(w2.keep({ uuid: "11111111-2222-4333-8444-000000000012", y: R3_OFFSET }), false);
  assert.deepEqual(w2.writes, [{ writer: "anchor-restore", top: 2350 + D, stick: false, from: undefined }]);
  assert.deepEqual(w2.state(), { pendingAnchor: null, pendingAnchorKeepY: null, relandAsk: false });
  // the attempt rebuilt the window around the anchor's unit (every row replaced) and its re-query missed: the captured row is gone too,
  // nothing is written, and the reader is where the rebuild left them (the residual the body names)
  const w3 = keepWorld(2350, { land: false, rebuild: (host) => { host.children = [host.children[0]]; for (let i = 20; i < 30; i++) host.add(new Node(100, "turn", "r" + i)); } });
  assert.equal(w3.keep({ uuid: "11111111-2222-4333-8444-000000000012", y: R3_OFFSET }), false);
  assert.equal(keepTakes(w3), 1); assert.deepEqual(w3.writes, [], "no row of the captured DOM is left to put back");
});
