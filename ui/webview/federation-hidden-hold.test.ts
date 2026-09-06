// The hidden-pane hold (2026-09-06): a pane the shell has hidden (display:none on its iframe — the Outline
// and Waiting panes by default, the timeline band when toggled off, every pane but the current tab on the
// phone) used to receive every merged frame and render a board nobody could see; about 58% of the handler
// time in the live minute rows went there. federation.ts now holds the emit for such a pane after its first
// frame, keeps the per-host state current underneath, and emits the newest merge ONCE on show. Facts these
// tests pin, all measured in Chromium 151 on 2026-09-06 and written into the hold's design:
//   - hidden is the SHELL's word ({romp:'panes', on}), because the zero-viewport probe holds only for a pane
//     hidden since load — once shown and hidden again the iframe keeps its size (innerWidth stays 1200) and a
//     same-size re-show fires NO resize, so a probe-and-resize design saves nothing after a first show and
//     misses every same-size re-show;
//   - the first frame of each slot goes through while hidden (the timeline's ready post, the panes' loaders);
//   - the chat and the feed pane are never held; the timeline's owed lanes and bars emit as lanes, then bars.
// The manager is constructed bare against a window stand-in, as the other executed federation tests do.
import { test } from "node:test";
import assert from "node:assert/strict";
import { FederationManager } from "./federation";

const SID = "11111111-2222-3333-4444-555555555555";

type Win = any;
/** A window stand-in: dispatchEvent collects what federation emits; addEventListener records the hold's
 *  listeners so a test can fire the shell's panes message and a resize; `parent` makes it framed or not. */
function makeWindow(opts: { framed: boolean; innerWidth: number; innerHeight: number }): { win: Win; emitted: any[]; sent: any[]; fire: (type: string, ev?: any) => void } {
  const emitted: any[] = [], sent: any[] = [];
  const listeners: Record<string, Array<(ev: any) => void>> = {};
  const win: Win = {
    dispatchEvent: (ev: any) => { if (ev && ev.data) emitted.push(ev.data); },
    addEventListener: (t: string, f: (ev: any) => void) => { (listeners[t] ||= []).push(f); },
    innerWidth: opts.innerWidth, innerHeight: opts.innerHeight,
    __rompLocalSend: (m: any) => sent.push(m),
  };
  win.parent = opts.framed ? {} : win;
  return { win, emitted, sent, fire: (t, ev) => { for (const f of listeners[t] || []) f(ev ?? {}); } };
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

test("Outline: frames after the first are held while the shell says hidden, and the newest emits once on show", () => {
  const { win, emitted } = makeWindow({ framed: true, innerWidth: 1200, innerHeight: 800 });
  withWindow(win, () => {
    const fm = new FederationManager(); fm.app = "fleet";
    fm.setPaneOn(false);
    fm.inbound("", feed(["a1"], 1000));
    assert.equal(emitted.length, 1, "the first frame of the slot goes through while hidden (loaders and the ready post resolve on it)");
    fm.inbound("", feed(["a1", "a2"], 1001));
    fm.inbound("", feed(["a1", "a2", "a3"], 1002));
    assert.equal(emitted.length, 1, "later frames are held while hidden");
    fm.setPaneOn(true);
    assert.equal(emitted.length, 2, "the show emits exactly once");
    assert.deepEqual(askIds(emitted[1]), ["a1", "a2", "a3"], "the show emits the NEWEST held state, not the frames in between");
    fm.setPaneOn(true);
    assert.equal(emitted.length, 2, "a shown pane with nothing owed emits nothing on a repeated word");
    fm.inbound("", feed(["a4"], 1003));
    assert.equal(emitted.length, 3, "a shown pane's frames emit at once");
  });
});

test("hide after show: the viewport keeps its size and no resize comes, and the owed frame still emits on the shell's word", () => {
  const { win, emitted, fire } = makeWindow({ framed: true, innerWidth: 1200, innerHeight: 800 });
  withWindow(win, () => {
    const fm = new FederationManager(); fm.app = "waiting";
    fm.installPaneHold(win);
    fire("message", { data: { romp: "panes", on: { waiting: true, chat: true } } });
    fm.inbound("", feed(["a1"], 1000));
    fm.inbound("", feed(["a1", "a2"], 1001));
    assert.equal(emitted.length, 2, "shown: every frame emits");
    fire("message", { data: { romp: "panes", on: { waiting: false, chat: true } } });   // the shell hides the pane
    assert.equal(fm.paneHidden(), true, "hidden is the shell's word: innerWidth is still 1200 (the iframe keeps its size)");
    assert.equal(win.innerWidth, 1200);
    fm.inbound("", feed(["a1", "a2", "a3"], 1002));
    assert.equal(emitted.length, 2, "held after the hide");
    fire("resize");                                          // a resize while still hidden (a same-size re-show fires none at all)
    assert.equal(emitted.length, 2, "a resize is not a show while the shell says hidden");
    fire("message", { data: { romp: "panes", on: { waiting: true, chat: true } } });   // the same-size re-show: the panes message is the only event
    assert.equal(emitted.length, 3, "the panes message is the show event");
    assert.deepEqual(askIds(emitted[2]), ["a1", "a2", "a3"]);
    assert.equal(typeof win.__rompPaneHidden, "function", "the answer is published for perf-telemetry's hidden_pane and the shim");
    assert.equal(win.__rompPaneHidden(), false);
  });
});

test("boot default: a framed pane with a zero viewport is hidden until the first-show resize or the shell's word", () => {
  const { win, emitted, fire } = makeWindow({ framed: true, innerWidth: 0, innerHeight: 0 });
  withWindow(win, () => {
    const fm = new FederationManager(); fm.app = "fleet";
    fm.installPaneHold(win);
    assert.equal(fm.paneHidden(), true, "no word from the shell yet: the zero viewport is the boot-time default");
    fm.inbound("", feed(["a1"], 1000));
    fm.inbound("", feed(["a1", "a2"], 1001));
    assert.equal(emitted.length, 1, "the first passes, the second is held");
    win.innerWidth = 1200; win.innerHeight = 800;
    fire("resize");                                          // the 0 → size resize a FIRST show fires
    assert.equal(emitted.length, 2, "the first-show resize is a show event under a shell that never posts the panes message");
    assert.deepEqual(askIds(emitted[1]), ["a1", "a2"]);
    fire("resize");
    assert.equal(emitted.length, 2, "a further resize with nothing owed emits nothing");
  });
});

test("an unframed page (a standalone kernel page) is never hidden by the probe", () => {
  const { win, emitted } = makeWindow({ framed: false, innerWidth: 0, innerHeight: 0 });
  withWindow(win, () => {
    const fm = new FederationManager(); fm.app = "fleet";
    assert.equal(fm.paneHidden(), false);
    fm.inbound("", feed(["a1"], 1000));
    fm.inbound("", feed(["a1", "a2"], 1001));
    assert.equal(emitted.length, 2);
  });
});

test("a feed delta applied while hidden keeps the held state current: no needFullFeed, and the show emits its result", () => {
  const { win, emitted, sent } = makeWindow({ framed: true, innerWidth: 1200, innerHeight: 800 });
  withWindow(win, () => {
    const fm = new FederationManager(); fm.app = "fleet";
    fm.inbound("", feed(["a1"], 1000));
    fm.setPaneOn(false);
    fm.inbound("", { type: "feedDelta", now: 1010, buildId: 2, asks: [{ itemId: "a2", sid: SID }] });
    fm.inbound("", { type: "feedDelta", now: 1020, buildId: 3, asks: [{ itemId: "a3", sid: SID }], removeAsks: ["a1"] });
    assert.equal(emitted.length, 1, "held");
    assert.equal(sent.filter((m) => m && m.type === "needFullFeed").length, 0, "the deltas applied onto the held base; nothing asked for a full frame");
    fm.setPaneOn(true);
    assert.equal(emitted.length, 2);
    assert.deepEqual(askIds(emitted[1]), ["a2", "a3"], "the show carries both deltas' effect");
    assert.equal(emitted[1].now, 1020);
  });
});

test("the timeline holds its lanes and bars while hidden and emits them on show as lanes, then bars", () => {
  const { win, emitted } = makeWindow({ framed: true, innerWidth: 1200, innerHeight: 800 });
  withWindow(win, () => {
    const fm = new FederationManager(); fm.app = "timeline";
    fm.setPaneOn(false);
    fm.inbound("", lanes("idle", 1000));
    fm.inbound("", bars(1, 1000));
    assert.deepEqual(emitted.map((m) => m.type), ["data", "bars"], "the first frame of each slot goes through while hidden");
    fm.inbound("", lanes("working", 1005));
    fm.inbound("", bars(2, 1005));
    fm.inbound("", lanes("working", 1010));
    fm.inbound("", bars(3, 1010));
    assert.equal(emitted.length, 2, "held");
    fm.setPaneOn(true);
    assert.deepEqual(emitted.slice(2).map((m) => m.type), ["data", "bars"], "one lanes emit, then one bars emit");
    assert.equal(emitted[2].data.sessions[0].state, "working");
    assert.equal(emitted[2].data.now, 1010, "the newest skeleton");
    assert.equal(emitted[3].turns[SID].length, 3, "the newest bars");
    fm.setPaneOn(false);
    fm.inbound("", bars(4, 1015));     // only the bars slot is owed this time
    fm.setPaneOn(true);
    assert.deepEqual(emitted.slice(4).map((m) => m.type), ["bars"], "an unowed slot is not re-emitted on show");
  });
});

test("the chat and the feed pane are never held, even when the shell says hidden", () => {
  for (const app of ["chat", "feed"]) {
    const { win, emitted } = makeWindow({ framed: true, innerWidth: 1200, innerHeight: 800 });
    withWindow(win, () => {
      const fm = new FederationManager(); fm.app = app;
      fm.setPaneOn(false);
      assert.equal(fm.paneHidden(), true, app + ": the hidden state is still reported truthfully (telemetry reads it)");
      fm.inbound("", feed(["a1"], 1000));
      fm.inbound("", feed(["a1", "a2"], 1001));
      fm.inbound("", feed(["a1", "a2", "a3"], 1002));
      assert.equal(emitted.length, 3, app + ": every feed frame emits");
    });
  }
});
