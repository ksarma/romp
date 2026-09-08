// The hidden-pane hold, at the paint gate. A pane the shell has hidden (display:none on its iframe: the Outline
// and Waiting panes by default, the timeline band when toggled off, every pane but the current tab on the phone)
// used to receive every merged frame and render a board nobody could see; about 58% of the handler time in the
// live minute rows went there. The fork's first answer (2026-09-06) held the merged FRAME in federation.ts
// (setPaneOn / installPaneHold / paneHidden, keyed on the shell's panes message) and re-emitted the newest once
// on show. Upstream #1016 solved the same problem the other way round, and the 2026-09-08 fold took its shape
// (romp-upstream's steer 2): every pane APPLIES every frame the moment it arrives (state, badges, follow-move
// bookkeeping), and only the PAINT is owed while nobody can see it, settled ONCE, synchronously, on the event
// that shows the pane (paint-gate.ts: the tab's visibilitychange, or the IntersectionObserver over the pane's
// list for a display:none iframe). Facts these tests pin, each the successor of one the federation hold pinned:
//   - frames after the first are held while the pane is hidden, and the newest paints once on show; the first
//     content always paints through (the pane loader retires on it);
//   - hidden is the OBSERVER's word, not the shell's and not the zero-viewport probe: a pane hidden after a first
//     show keeps its iframe size (innerWidth stays 1200) and a same-size re-show fires no resize, so the observer
//     over the list, which reports display:none as not intersecting and fires on the way back, is the release
//     the probe never had;
//   - a standalone page (no iframe) is never held while its tab is visible; its tab's hiding holds it, the case
//     the framed probe never covered (the user 2026-09-07, whose dashboard froze on the return to its tab);
//   - federation itself holds nothing: every merged frame reaches the pane, a delta applied while hidden keeps
//     the pane's state current and asks for no full frame, and the timeline's lanes and bars arrive in wire order;
//   - the chat is never held (render.ts has no gate); the feed pane's PAINT is gated like the Outline's, its
//     payload never;
//   - the gate PUBLISHES its word for the kernel's pane shim (window.__rompPaneHidden, paint-gate.ts
//     publishPaneHidden; the round-2 ruling of the 2026-09-08 fold): the shim's stale-banner gate had only the
//     zero-viewport probe, which misses a pane hidden after a first show, so every pane that gates publishes
//     document.hidden OR the observer's word on the gate's own events, and the shim says hidden when EITHER its
//     probe or the word says so (round 3: Firefox zeroes a hidden iframe's viewport and does not run its observer,
//     Chromium keeps the size and runs it; the union is right in both, a word-first read is not);
//   - nothing is published before the observer's first word (round 3): a return's visibilitychange must not say
//     visible for a display:none pane one rendering step before the observer's first entry, so the word starts
//     null and the probe decides until it speaks. The chat page (render.ts, no paint gate) publishes the same
//     word through chat-visibility.ts (chat-visibility.test.ts runs it, in Chromium too).
// The federation half runs against a bare FederationManager over a window stand-in (as the other executed
// federation tests do); the pane half runs the gate's pure decision through a harness of fleet.ts's render()
// and releasePaint() lines, which outline-visibility.test.ts and feed-hidden-paint.test.ts pin at source; the
// timeline's bars half runs the panel method itself.
import { test } from "node:test";
import assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { FederationManager } from "./federation";
import { paintHeld, paintReleased, publishPaneHidden, type PaneHiddenHost } from "./paint-gate";

const SID = "11111111-2222-3333-4444-555555555555";
const ROOT = path.resolve(process.cwd(), "..");
const read = (...p: string[]) => fs.readFileSync(path.join(ROOT, ...p), "utf8");
const FED = read("ui", "webview", "federation.ts");
const FLEET = read("ui", "webview", "fleet.ts");
const FEED = read("ui", "webview", "feed.ts");
const RENDER = read("ui", "webview", "render.ts");
const WAITING = read("ui", "webview", "waiting.ts");
const PERF = read("ui", "webview", "perf-telemetry.ts");
const GATE = read("ui", "webview", "paint-gate.ts");
const TL = read("ui", "romp-timeline-view.js");
const KERNEL = read("kernel", "kernel.py");

type Win = any;
/** A window stand-in: dispatchEvent collects what federation emits; `parent` makes it framed or not. */
function makeWindow(opts: { framed: boolean; innerWidth: number; innerHeight: number }): { win: Win; emitted: any[]; sent: any[] } {
  const emitted: any[] = [], sent: any[] = [];
  const win: Win = {
    dispatchEvent: (ev: any) => { if (ev && ev.data) emitted.push(ev.data); },
    addEventListener: () => {},
    innerWidth: opts.innerWidth, innerHeight: opts.innerHeight,
    __rompLocalSend: (m: any) => sent.push(m),
  };
  win.parent = opts.framed ? {} : win;
  return { win, emitted, sent };
}

function withWindow(w: Win, fn: () => void): void {
  const g: any = globalThis;
  const hadWindow = "window" in g, prevWindow = g.window;
  const hadLS = "localStorage" in g, prevLS = g.localStorage;
  const store = new Map<string, string>();
  g.window = w;
  g.localStorage = { getItem: (k: string) => store.get(k) ?? null, setItem: (k: string, v: string) => { store.set(k, v); } };
  try { fn(); } finally {
    if (hadWindow) g.window = prevWindow; else delete g.window;
    if (hadLS) g.localStorage = prevLS; else delete g.localStorage;
  }
}

const feed = (ids: string[], now: number) => ({ type: "feed", now, asks: ids.map((id) => ({ itemId: id, sid: SID })), sessions: [], order: [], working: [], awaiting: [], ledgers: [] });
const lanes = (state: string, now: number) => ({ type: "data", data: { now, sessions: [{ id: SID, name: "web", color: "#888", live: true, state }], turns: {}, judging: [], messages: [] } });
const bars = (n: number, now: number) => ({ type: "bars", now, turns: { [SID]: Array.from({ length: n }, (_, i) => ({ id: "t" + i, start: now - 60 * (i + 1), end: now - 60 * i })) }, judging: [], messages: [] });
const askIds = (f: any) => (f.asks || []).map((a: any) => a.itemId);

/** A pane's gate: fleet.ts's render() and releasePaint() line for line over the pure decision (the source pins
 *  at the end hold fleet.ts and feed.ts to these lines). `visible` is the observer's last word, null until it
 *  speaks (`let paneVisible: boolean | null = null;`); `hidden` is document.hidden; `painted` the list's child count;
 *  `host` the window stand-in the shim's word is published on (releasePaint's first line and the hidden arm of visibilitychange). */
function paneHarness() {
  const st = { hidden: false, visible: null as boolean | null, painted: 0, dirty: false, frames: 0, paints: 0, lastPainted: null as any, host: {} as PaneHiddenHost };
  let model: any = null;
  function render() {
    if (paintHeld(st.hidden, st.visible, st.painted > 0)) { st.dirty = true; return; }
    st.paints++; st.painted = model ? model.asks.length : 0; st.lastPainted = model;
  }
  function releasePaint() {
    publishPaneHidden(st.hidden, st.visible, st.host);
    if (!paintReleased(st.dirty, st.hidden, st.visible)) return;
    st.dirty = false;
    render();
  }
  return {
    st,
    /** the frame handler: the payload applied, then the gated render */
    frame(m: any) { model = m; st.frames++; render(); },
    /** the IntersectionObserver's callback over the list */
    observer(intersecting: boolean) { st.visible = intersecting; releasePaint(); },
    /** the tab's visibilitychange */
    tab(state: "hidden" | "visible") { st.hidden = state === "hidden"; if (!st.hidden) releasePaint(); if (st.hidden) publishPaneHidden(true, st.visible, st.host); },
  };
}

test("Outline: frames after the first are held while the pane is hidden, and the newest paints once on show", () => {
  const p = paneHarness();
  p.observer(false);                                   // the list is display:none: the observer's first word
  p.frame(feed(["a1"], 1000));
  assert.equal(p.st.paints, 1, "the first content paints through while hidden (the pane loader retires on it)");
  p.frame(feed(["a1", "a2"], 1001));
  p.frame(feed(["a1", "a2", "a3"], 1002));
  assert.equal(p.st.paints, 1, "later frames are held while hidden");
  assert.equal(p.st.frames, 3, "...and every one of them was applied");
  p.observer(true);                                    // shown
  assert.equal(p.st.paints, 2, "the show paints exactly once");
  assert.deepEqual(askIds(p.st.lastPainted), ["a1", "a2", "a3"], "the paint is of the NEWEST state, not the frames in between");
  p.observer(true);
  assert.equal(p.st.paints, 2, "a shown pane with nothing owed paints nothing on a repeated word");
  p.frame(feed(["a4"], 1003));
  assert.equal(p.st.paints, 3, "a shown pane's frames paint at once");
});

test("hide after show: the iframe keeps its size and no resize comes; the observer's word hides the pane, and its next word releases the owed paint", () => {
  // steer 2: the shell's panes message and the zero-viewport probe (the federation hold's two measures) are gone;
  // the observer over the list reports display:none as not intersecting and fires again on the way back (and its
  // word is what the shim now reads for this case: the test after the boot default below)
  const p = paneHarness();
  p.frame(feed(["a1"], 1000));
  p.frame(feed(["a1", "a2"], 1001));
  assert.equal(p.st.paints, 2, "shown: every frame paints");
  p.observer(false);                                   // the shell hides the pane; innerWidth would still read 1200
  p.frame(feed(["a1", "a2", "a3"], 1002));
  assert.equal(p.st.paints, 2, "held after the hide");
  p.tab("hidden"); p.tab("visible");                   // the tab blinks while the pane is still display:none
  assert.equal(p.st.paints, 2, "the tab's return is not a show for a pane the observer cannot see");
  p.observer(true);                                    // the same-size re-show: the observer's callback is the only event
  assert.equal(p.st.paints, 3, "the observer's word is the show event");
  assert.deepEqual(askIds(p.st.lastPainted), ["a1", "a2", "a3"]);
});

test("boot default: a pane hidden since load paints its first content through, then holds until the observer reports it on screen", () => {
  // steer 2: no zero-viewport probe; the observer's word is null until it speaks (`let paneVisible: boolean | null =
  // null;`, which the gate reads as on screen) and the first content is never withheld (paint-gate.ts), so the
  // loader retires on it whatever the visibility
  const p = paneHarness();
  p.frame(feed(["a1"], 1000));
  assert.equal(p.st.paints, 1, "the first content paints before the observer's first callback");
  p.observer(false);                                   // the observer's first measure: display:none
  p.frame(feed(["a1", "a2"], 1001));
  assert.equal(p.st.paints, 1, "held");
  p.observer(true);                                    // the first show
  assert.equal(p.st.paints, 2, "the first show paints once");
  assert.deepEqual(askIds(p.st.lastPainted), ["a1", "a2"]);
  p.observer(true);
  assert.equal(p.st.paints, 2, "a further callback with nothing owed paints nothing");
});

test("the shim's word: unset until the gate's first event, then the observer's word OR the tab's, so a pane hidden AFTER a first show reads hidden", () => {
  // The kernel's pane shim gates its stale banner on paneHidden() (a hidden pane never raises it, the 2026-08-15 phone
  // fix). Its own measure, the zero-viewport probe, is right for a pane hidden since load and wrong for one the shell
  // hides after the user has looked at it (the iframe keeps its size: innerWidth stays 1200), the phone shell's every
  // tab switch. The gate sees that case, so it publishes; the shim reads the flag when it is a boolean, the probe
  // otherwise. Every publish is on a gate event (the observer's callback, visibilitychange, the release): no timer.
  const p = paneHarness();
  assert.equal(typeof p.st.host.__rompPaneHidden, "undefined", "boot: nothing published before the first event, so the shim's probe decides (right for a pane hidden since load)");
  p.frame(feed(["a1"], 1000));
  assert.equal(typeof p.st.host.__rompPaneHidden, "undefined", "a frame is not a gate event: the first paint publishes nothing");
  p.observer(true);                                    // the observer's first word: on screen
  assert.equal(p.st.host.__rompPaneHidden, false, "shown");
  p.observer(false);                                   // the shell hides the pane after the show; innerWidth would still read 1200
  assert.equal(p.st.host.__rompPaneHidden, true, "hidden after a first show: the case the probe misses, read hidden");
  p.tab("hidden"); p.tab("visible");                   // the tab blinks while the pane is still display:none
  assert.equal(p.st.host.__rompPaneHidden, true, "the tab's return is not a show for a pane the observer cannot see");
  p.observer(true);
  assert.equal(p.st.host.__rompPaneHidden, false, "the re-show publishes on the observer's callback");
  p.tab("hidden");
  assert.equal(p.st.host.__rompPaneHidden, true, "the tab hidden with the pane on screen: hidden (a banner nobody can see is not raised; the return re-raises if still stale)");
  p.tab("visible");
  assert.equal(p.st.host.__rompPaneHidden, false, "the tab's return publishes on visibilitychange");
  assert.equal(typeof p.st.host.__rompPaneHidden, "boolean", "a boolean, the type the shim tests for");
});

test("before the observer's first word a visibilitychange publishes nothing, on either arm; after it, both arms publish (round 3)", () => {
  // A page loaded in a background tab gets no IntersectionObserver callback until the tab's first rendering step
  // after its return. The return's visibilitychange therefore ran with the observer's word still at its `true`
  // default and published false for a pane that was display:none, one rendering step before the observer's first
  // entry said otherwise; the shim preferred that boolean over its probe, which read innerWidth 0 and was right.
  // The word starts null now and nothing is published until the observer has spoken: the probe decides at boot.
  const p = paneHarness();
  p.frame(feed(["a1"], 1000));
  p.tab("visible");
  assert.equal(typeof p.st.host.__rompPaneHidden, "undefined", "the return before the observer's first entry publishes nothing");
  p.tab("hidden");
  assert.equal(typeof p.st.host.__rompPaneHidden, "undefined", "nor does the hidden arm");
  p.tab("visible");
  assert.equal(p.st.paints, 1, "the paint side is as before: the first content painted through and nothing is owed");
  p.observer(false);                                   // the observer's first entry: display:none
  assert.equal(p.st.host.__rompPaneHidden, true, "the first entry publishes");
  p.tab("hidden"); assert.equal(p.st.host.__rompPaneHidden, true);
  p.tab("visible"); assert.equal(p.st.host.__rompPaneHidden, true, "both arms publish now, and the return of a display:none pane still reads hidden");
  p.observer(true); assert.equal(p.st.host.__rompPaneHidden, false);
  p.tab("hidden"); assert.equal(p.st.host.__rompPaneHidden, true, "the hidden arm");
  p.tab("visible"); assert.equal(p.st.host.__rompPaneHidden, false, "the visible arm");
  // the pure publisher: null is "not yet", never a verdict
  const w: PaneHiddenHost = {};
  assert.equal(publishPaneHidden(false, null, w), null);
  assert.equal(publishPaneHidden(true, null, w), null);
  assert.equal(typeof w.__rompPaneHidden, "undefined");
  // a page with no IntersectionObserver never publishes: the probe stands, as before the publisher existed
  const bare = paneHarness();
  bare.frame(feed(["a1"], 1000)); bare.tab("hidden"); bare.tab("visible");
  assert.equal(typeof bare.st.host.__rompPaneHidden, "undefined", "no observer, no word");
  assert.equal(bare.st.paints, 1, "...and its paint is gated by the tab alone, as before");
});

test("a standalone page (no iframe) is never held while its tab is visible; its tab's own hiding holds it", () => {
  // steer 2: the federation hold exempted an unframed page outright (its probe read the iframe's viewport); the
  // paint gate reads the tab too, the case that froze the user's dashboard on the return to its tab (2026-09-07)
  const p = paneHarness();                             // no observer callback ever says otherwise: the list is on screen
  p.frame(feed(["a1"], 1000));
  p.frame(feed(["a1", "a2"], 1001));
  assert.equal(p.st.paints, 2, "every frame paints");
  p.tab("hidden");
  p.frame(feed(["a1", "a2", "a3"], 1002));
  p.frame(feed(["a4"], 1003));
  assert.equal(p.st.paints, 2, "the hidden tab holds the paint");
  assert.equal(p.st.frames, 4, "...not the payload");
  p.tab("visible");
  assert.equal(p.st.paints, 3, "the return paints once");
  assert.deepEqual(askIds(p.st.lastPainted), ["a4"]);
  assert.equal(paintHeld(false, true, true), false, "the pure decision: on screen in a visible tab, nothing holds");
  assert.equal(paintHeld(true, true, true), true, "...a hidden tab holds, framed or not");
});

test("federation holds nothing: a feed delta applied while the pane is hidden keeps its state current, asks for no full frame, and every merged frame reaches the pane", () => {
  // steer 2: the hold moved from the merged frame to the pane's paint; federation.ts carries no hidden-pane state
  const { win, emitted, sent } = makeWindow({ framed: true, innerWidth: 1200, innerHeight: 800 });
  withWindow(win, () => {
    const fm = new FederationManager(); fm.app = "fleet";
    fm.inbound("", feed(["a1"], 1000));
    fm.inbound("", { type: "feedDelta", now: 1010, buildId: 2, asks: [{ itemId: "a2", sid: SID }] });
    fm.inbound("", { type: "feedDelta", now: 1020, buildId: 3, asks: [{ itemId: "a3", sid: SID }], removeAsks: ["a1"] });
    assert.equal(emitted.length, 3, "each frame is emitted as it arrives; the pane's gate decides what is painted");
    assert.equal(sent.filter((m) => m && m.type === "needFullFeed").length, 0, "the deltas applied onto the held base; nothing asked for a full frame");
    assert.deepEqual(askIds(emitted[2]), ["a2", "a3"], "the newest merge carries both deltas' effect");
    assert.equal(emitted[2].now, 1020);
  });
  for (const gone of ["HoldSlot", "setPaneOn", "installPaneHold", "holdWhileHidden", "flushOwed", "__rompPaneHidden"]) {
    assert.ok(!FED.includes(gone), "federation.ts no longer carries the frame hold: " + gone);
  }
  assert.match(FLEET, /import \{ paintHeld, paintReleased \} from "\.\/paint-gate";/, "the Outline holds at its paint");
  assert.match(FEED, /import \{ paintHeld, paintReleased \} from "\.\/paint-gate";/, "so does the feed");
});

test("the timeline's lanes and bars reach the pane in wire order, unheld; the pane applies both while hidden and paints one catch-up on show", () => {
  const { win, emitted } = makeWindow({ framed: true, innerWidth: 1200, innerHeight: 800 });
  withWindow(win, () => {
    const fm = new FederationManager(); fm.app = "timeline";
    fm.inbound("", lanes("idle", 1000)); fm.inbound("", bars(1, 1000));
    fm.inbound("", lanes("working", 1005)); fm.inbound("", bars(2, 1005));
    assert.deepEqual(emitted.map((m) => m.type), ["data", "bars", "data", "bars"], "every frame, lanes then bars, as the kernel sent them");
    assert.equal(emitted[2].data.sessions[0].state, "working");
    assert.equal(emitted[3].turns[SID].length, 2);
  });
  // The pane's half, executed on the method itself: applyBars() merges the bars into the live data whatever the
  // visibility and holds only the draw; _releasePaintHold paints the catch-up once. ui/timeline-hidden-hold.test.ts
  // drives the whole panel (the skeleton path, the observer, the live tick, a bars frame parked ahead of its lanes).
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const { TimelinePanel } = require(path.join(ROOT, "ui", "romp-timeline-view.js"));
  const v: any = Object.create(TimelinePanel.prototype);
  let hidden = true, draws = 0;
  Object.assign(v, {
    data: { now: 1000, sessions: [{ id: SID, live: true }], turns: {} }, _barsSeen: new Set(), _pendingBars: null,
    tip: null, _pointerHeld: false, _dirtyWhileTip: false, fitted: true, _newestNow: null,
    _hiddenForPaint: () => hidden, draw: () => { draws++; }, _startLiveTick: () => {}, _anchorNow: () => {},
  });
  v.applyBars(bars(1, 1001));
  v.applyBars(bars(2, 1002));
  assert.equal(draws, 0, "hidden: no draw for either frame");
  assert.equal(v._dirtyWhileTip, true, "...the paint is owed on the hold path the tooltip and click holds use");
  assert.equal(v.data.turns[SID].length, 2, "...and the newest bars are the live data");
  assert.equal(v.data.now, 1002, "...with the newest clock");
  assert.equal(v._barsLoaded, true, "...and the loader latch flipped (a return must not show the loader)");
  hidden = false; v._releasePaintHold();
  assert.equal(draws, 1, "the show paints once");
  assert.equal(v._dirtyWhileTip, false);
  v._releasePaintHold();
  assert.equal(draws, 1, "nothing owed: nothing painted");
});

test("the chat is never held; the feed pane holds its PAINT like the Outline and applies its payload whatever the visibility", () => {
  // steer 2 changed the feed's half: the federation hold exempted the feed pane's frames, #1016 gates its paint
  // (feed-hidden-paint.test.ts runs that gate) while applyFeedPayload never looks at the visibility
  assert.ok(!RENDER.includes("paintHeld(") && !RENDER.includes("paintReleased(") && !/from "\.\/paint-gate"/.test(RENDER),
    "render.ts (the chat) has no paint gate: every frame paints (its shim word comes through chat-visibility.ts: the publisher pins below)");
  assert.equal(FEED.split("paintHeld(").length - 1, 1, "the feed gates once, in render()");
  assert.equal(FLEET.split("paintHeld(").length - 1, 1, "so does the Outline");
  const apply = /^function applyFeedPayload\([\s\S]*?\n\}/m.exec(FEED)![0];
  assert.doesNotMatch(apply, /document\.hidden|paintDirty|feedIntersecting|paintHeld/, "the payload path never looks at the gate");
  // federation hands the chat and the feed every frame, as it hands every pane
  for (const app of ["chat", "feed"]) {
    const { win, emitted } = makeWindow({ framed: true, innerWidth: 1200, innerHeight: 800 });
    withWindow(win, () => {
      const fm = new FederationManager(); fm.app = app;
      fm.inbound("", feed(["a1"], 1000));
      fm.inbound("", feed(["a1", "a2"], 1001));
      fm.inbound("", feed(["a1", "a2", "a3"], 1002));
      assert.equal(emitted.length, 3, app + ": every feed frame emits");
    });
  }
});

test("source pins: the release events are the observer's callback and visibilitychange, never a resize; the telemetry's hidden_pane is the viewport probe again", () => {
  for (const [name, src, sites] of [["fleet.ts", FLEET, 2], ["feed.ts", FEED, 3]] as const) {
    assert.match(src, /new IntersectionObserver\(\(entries\) => \{\n\s*\w+ = entries\.some\(\(e\) => e\.isIntersecting\);\n\s*releasePaint\(\);\n\s*\}\)\.observe\(list\);/, name + ": the observer over the list releases");
    assert.match(src, /document\.addEventListener\("visibilitychange", \(\) => \{ if \(!document\.hidden\) releasePaint\(\); \}\);/, name + ": the tab's return releases");
    assert.equal(src.split("releasePaint();").length - 1, sites, name + ": the release call sites");
    assert.ok(!/addEventListener\("resize"[^\n]*releasePaint/.test(src), name + ": a resize releases nothing (a same-size re-show fires none)");
  }
  // feed.ts's third site: a bell jump settles the owed paint on the shell's word (feed-hidden-paint.test.ts pins the line)
  assert.match(FEED, /if \(paintDirty\) \{ feedIntersecting = true; releasePaint\(\); \}/);
  // perf-telemetry's hidden_pane row is the shim's union: the zero-viewport probe OR the pane's published word
  // (round 3; steer 2 had left it on the probe alone, which under-reports a pane hidden after a first show in
  // Chromium). perf-telemetry.test.ts executes the read.
  assert.match(PERF, /hiddenPane: \(\) => \{ try \{ return \(w\.parent !== w && \(w\.innerWidth === 0 \|\| w\.innerHeight === 0\)\) \|\| w\.__rompPaneHidden === true; \} catch \(e\) \{ return false; \} \},/);
});

test("the Waiting pane (fork-only, hidden by default on desktop) gates its paint like the Outline: the payload applied, the rebuild owed until shown", () => {
  // The federation hold covered every pane but the chat and the feed, the Waiting pane included; #1016 gates the
  // feed, the Outline and the timeline, and the fold's steer 2 dropped the hold without a gate here, so render()
  // in waiting.ts rebuilds the rows on every feed frame while the pane is display:none. A lost hunk, not a
  // superseded one: CODE REQUEST uihold -> coordinator (waiting.ts is not this fixer's file); red until it lands.
  assert.match(WAITING, /import \{ paintHeld, paintReleased \} from "\.\/paint-gate";/);
  assert.match(WAITING, /function render\(\): void \{[\s\S]*?if \(paintHeld\(document\.hidden, \w+, list\.childElementCount > 0\)\) \{ \w+ = true; return; \}/);
  assert.equal(WAITING.split("paintHeld(").length - 1, 1, "one gate, in render()");
  assert.match(WAITING, /new IntersectionObserver\(\(entries\) => \{\n\s*\w+ = entries\.some\(\(e\) => e\.isIntersecting\);\n\s*releasePaint\(\);\n\s*\}\)\.observe\(list\);/);
  assert.match(WAITING, /document\.addEventListener\("visibilitychange", \(\) => \{ if \(!document\.hidden\) releasePaint\(\); \}\);/);
  const apply = /^function applyFrame\([\s\S]*?\n\}/m.exec(WAITING)![0];
  assert.doesNotMatch(apply, /document\.hidden|paintHeld|paintReleased/, "the payload is applied whatever the visibility");
});

test("source pins: every pane that gates publishes the shim's word from the gate's own events, through paint-gate.ts; the flag name lives in one place", () => {
  for (const [name, src, vis] of [["fleet.ts", FLEET, "paneVisible"], ["feed.ts", FEED, "feedIntersecting"], ["waiting.ts", WAITING, "paneVisible"]] as const) {
    assert.match(src, /import \{ publishPaneHidden \} from "\.\/paint-gate";/, name + ": the publisher, on its own import line (the paintHeld/paintReleased line is upstream's text, pinned by its tests)");
    const rel = /^function releasePaint\(\): void \{([\s\S]*?)\n\}/m.exec(src)![1];
    assert.match(rel, new RegExp("^\\n\\s*publishPaneHidden\\(document\\.hidden, " + vis + "\\);[^\\n]*\\n\\s*if \\(!paintReleased\\("), name + ": the release publishes FIRST, before the owed-paint decision, so the observer's callback and the tab's return both publish");
    assert.match(src, new RegExp('document\\.addEventListener\\("visibilitychange", \\(\\) => \\{ if \\(document\\.hidden\\) publishPaneHidden\\(true, ' + vis + '\\); \\}\\);'), name + ": the hidden arm publishes too (the pinned visible arm releases, and so publishes)");
    assert.equal(src.split("publishPaneHidden(").length - 1, 2, name + ": two publish sites, the release and the hidden arm; the observer's callback and the revealCard settle go through the release");
    assert.ok(!/set(Interval|Timeout)\([^\n]*publishPaneHidden/.test(src), name + ": never on a timer");
    assert.ok(!src.includes("__rompPaneHidden"), name + ": the flag's name is paint-gate.ts's, not the pane's");
    assert.match(src, new RegExp("^let " + vis + ": boolean \\| null = null;", "m"), name + ": the observer's word starts null (round 3), so nothing is published before it speaks");
  }
  assert.match(GATE, /export function publishPaneHidden\(docHidden: boolean, intersecting: boolean \| null, w: PaneHiddenHost = globalThis as PaneHiddenHost\): boolean \| null \{\s*\n\s*if \(intersecting === null\) return null;[^\n]*\n\s*const hidden = docHidden \|\| !intersecting;\s*\n\s*w\.__rompPaneHidden = hidden;/,
    "the word is the union of both measures, written on the page's window as a boolean, and only once the observer has spoken");
  assert.equal(GATE.split("__rompPaneHidden").length - 1, 3, "the name: the interface, the write, the comment's mention of the shim's read");
  assert.ok(!FED.includes("__rompPaneHidden"), "federation.ts publishes nothing (steer 2): the gate does");
  // the chat page (round 3): no gate, the same word, from chat-visibility.ts, installed once on the page's body
  const CHATVIS = read("ui", "webview", "chat-visibility.ts");
  assert.match(RENDER, /^import \{ watchChatVisibility, browserChatVisibilityDeps \} from "\.\/chat-visibility";/m, "render.ts imports the chat's publisher");
  assert.match(RENDER, /^watchChatVisibility\(document\.body, browserChatVisibilityDeps\(\)\);/m, "installed at top level, over the page's body (the element the shell's display:none takes the box from)");
  assert.equal(RENDER.split("watchChatVisibility(").length - 1, 1, "once");
  assert.ok(!RENDER.includes("__rompPaneHidden") && !CHATVIS.includes("__rompPaneHidden"), "the flag's name stays paint-gate.ts's");
  assert.match(CHATVIS, /import \{ publishPaneHidden, type PaneHiddenHost \} from "\.\/paint-gate";/, "through the shared publisher");
  assert.ok(!/set(Interval|Timeout)/.test(CHATVIS), "never on a timer");
  assert.ok(!CHATVIS.includes('"panes"') && !CHATVIS.includes("romp:") && !CHATVIS.includes("panesOn"), "from the frame's own visibility, never the shell's panes message");
  assert.match(KERNEL, /_shim\("chat", v, caps=READY_GATE_CAP\)/, "the chat page carries the shim that reads the word");
});

test("both ends: the kernel's pane shim says hidden when its zero-viewport probe OR the published word says so (round 2's read, made the union in round 3)", () => {
  // tests/test_kernel_disconnect_banner.py pins the shim's text; this cross-pin holds the two halves together: a
  // publisher nobody reads, or a read nobody publishes, fails here whichever side changes. The union, not the word
  // first: Firefox zeroes a display:none iframe's viewport and does not run its IntersectionObserver, so there the
  // word goes stale while the probe is right; Chromium is the reverse (chat-visibility.test.ts measures both).
  const shim = /function paneHidden\(\)\{[^\n]*/.exec(KERNEL)?.[0] ?? "";
  assert.ok(shim, "kernel.py has the shim's paneHidden");
  assert.match(shim, /\(window\.parent!==window&&\(window\.innerWidth===0\|\|window\.innerHeight===0\)\)\|\|window\.__rompPaneHidden===true/, "the probe OR a published word of true");
  assert.doesNotMatch(shim, /typeof window\.__rompPaneHidden==="boolean"\)return/, "never the word first");
  assert.match(KERNEL, /function raiseStale\(why\)\{if\(paneHidden\(\)\)\{staleDiag\("stale-suppressed-hidden",why\);return;\}/, "the gate is at raise time, as before");
});

test("the timeline pane publishes the word too, from its own hold's events, and not before its observer has spoken", () => {
  // The timeline's paint hold (upstream #1016) is its own: _releasePaintHold on visibilitychange and the observer's
  // intersecting entries, keyed on _hiddenForPaint. Its shim has the same probe and the same blind spot, so the same
  // union (document hidden OR the observer's last word) is published from the constructor's two handlers, and (round
  // 3) skipped while _paneIntersecting is still null, the same rule as the panes': the probe decides at boot.
  const ctor = TL.slice(TL.indexOf("this._onVis = "), TL.indexOf("// controls row BELOW the time axis"));
  assert.ok(ctor.length > 0, "the constructor's hold wiring");
  assert.match(TL, /this\._paneIntersecting = null;/, "the observer's word starts null");
  assert.match(ctor, /this\._onVis = \(\) => \{[^\n]*_publishPaneHidden\(\)/, "visibilitychange publishes, then releases");
  assert.match(ctor, /new IntersectionObserver\(\(entries\) => \{[\s\S]*?_publishPaneHidden\(\)[\s\S]*?\}\);/, "the observer's callback publishes its word, intersecting or not, before the release");
  assert.match(TL, /window\.__rompPaneHidden = /, "written on the page's window, the name the shim reads");
  assert.match(TL, /_publishPaneHidden\(\) \{\n\s*if \(typeof window === 'undefined'\) return;\n\s*if \(this\._paneIntersecting === null\) return;/, "one method, the union of both measures, silent until the observer speaks");
  // executed on the method itself, over a window stand-in
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const { TimelinePanel } = require(path.join(ROOT, "ui", "romp-timeline-view.js"));
  const v: any = Object.create(TimelinePanel.prototype);
  v._paneIntersecting = null;
  const { win } = makeWindow({ framed: true, innerWidth: 1200, innerHeight: 800 });
  withWindow(win, () => {
    v._publishPaneHidden();
    assert.equal(typeof win.__rompPaneHidden, "undefined", "a visibilitychange before the observer's first entry publishes nothing");
    v._paneIntersecting = false; v._publishPaneHidden();
    assert.equal(win.__rompPaneHidden, true, "the first entry publishes: display:none after a show");
    v._paneIntersecting = true; v._publishPaneHidden();
    assert.equal(win.__rompPaneHidden, false, "shown");
  });
});
