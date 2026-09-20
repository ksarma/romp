// The print flow's machine and its wait (file-print.ts; the print follow-on to plans/markdown-viewer.md's Slice 3, item 12),
// executed under node with no DOM: `step` over every phase and event (the disabled phase the driver starts in, P7, and the
// stalled phase the deadline's ask stands in, among them), the words, the chord, and settlePictures over fake pictures and a
// fake clock (the deadline is the one timer in the module, and it is injected; Keep waiting's wait sets none). The DOM driver, the button,
// the line and window.print run over the real viewer in file-print-browser.test.ts. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { hideEdges } from "../test-dom-shim";   // every stand-in below that carries a tree edge (parentElement, children, childNodes, firstElementChild) hides it, the shared module's rule (ui/test-dom-shim.test.ts's ratchet)
import { step, RESTING, DISABLED, armedWords, preparingWords, waitingWords, stalledWords, anywayWords, ANYWAY_TITLE, isPrintChord, isPrintKeys, settlePictures, collectPictures, bodyReady, rootKind, PRINT_SETTLE_MS, setPrintSettleMs, printSettleMs,
  WITH_WORDS, WITHOUT_WORDS, ANYWAY_WORDS, KEEP_WORDS, TAB_WORDS, NO_TAB_WORDS, pdfFrameWindow, READY_ROOTS, NOT_READY_ROOTS, LINE_ROOTS, PDF_LOADER_ROOT, printable, figurePrintable, figureHidden, rendered, SVG_NS, PAINTS_SEL,
  type PrintState, type Picture, type Timers, type BodyLike, type PrintableNode, type FigureNode } from "./file-print";

// ── the machine ─────────────────────────────────────────────────────────────────────────────────────

test("a press over gated placeholders arms with their count; a second press, or Escape, disarms and nothing prints", () => {
  const armed = step(RESTING, { kind: "press", gated: 3, pending: 0 });
  assert.equal(armed.act, "arm");
  assert.equal(armed.state.phase, "armed");
  assert.equal(armed.state.gated, 3);
  const again = step(armed.state, { kind: "press", gated: 3, pending: 0 });
  assert.equal(again.act, "disarm");
  assert.equal(again.state.phase, "resting");
  const esc = step(armed.state, { kind: "escape" });
  assert.equal(esc.act, "disarm");
  assert.equal(esc.state.phase, "resting");
  assert.equal(step(RESTING, { kind: "escape" }).act, "none", "Escape at rest changes nothing (the viewer's own Escape closes the card)");
});

test("the two choices: with them activates the gates, without them skips; the driver's prepare then begins the wait or prints at once", () => {
  const armed = step(RESTING, { kind: "press", gated: 1, pending: 0 }).state;
  const w = step(armed, { kind: "choose", withGated: true });
  assert.equal(w.act, "activate");
  assert.equal(w.state.phase, "armed", "still armed until the driver reports the pictures");
  const wo = step(armed, { kind: "choose", withGated: false });
  assert.equal(wo.act, "skip");
  assert.equal(wo.state.phase, "armed");
  const waiting = step(armed, { kind: "prepare", pending: 2 });
  assert.equal(waiting.act, "wait");
  assert.equal(waiting.state.phase, "preparing");
  assert.equal(waiting.state.pending, 2);
  const now = step(armed, { kind: "prepare", pending: 0 });
  assert.equal(now.act, "print", "every picture already complete: the print runs at once");
  assert.equal(now.state.phase, "printing");
});

test("no gated placeholder: one press begins the wait when pictures are loading and prints at once when none is", () => {
  const wait = step(RESTING, { kind: "press", gated: 0, pending: 4 });
  assert.equal(wait.act, "wait");
  assert.equal(wait.state.phase, "preparing");
  assert.equal(wait.state.pending, 4);
  const now = step(RESTING, { kind: "press", gated: 0, pending: 0 });
  assert.equal(now.act, "print");
  assert.equal(now.state.phase, "printing");
});

test("ready during the wait prints; printed rests; a press, an Escape, a choice or Print anyway during the timed wait or the print changes nothing (the timed wait's line has no button; its deadline asks)", () => {   // the wait's verdict carries why (settled, or the deadline) and the count still loading: the machine reads both (the deadline's ask, below)
  const preparing: PrintState = { phase: "preparing", gated: 0, pending: 2 };
  for (const ev of [{ kind: "press", gated: 0, pending: 0 }, { kind: "escape" }, { kind: "anyway" }, { kind: "choose", withGated: true }, { kind: "prepare", pending: 1 }, { kind: "printed" }] as const) {
    const r = step(preparing, ev);
    assert.equal(r.act, "none", ev.kind + " during the wait");
    assert.equal(r.state, preparing, ev.kind + " during the wait keeps the state");
  }
  const printing = step(preparing, { kind: "ready", why: "settled", pending: 0 });
  assert.equal(printing.act, "print");
  assert.equal(printing.state.phase, "printing");
  for (const ev of [{ kind: "press", gated: 2, pending: 0 }, { kind: "escape" }, { kind: "anyway" }, { kind: "ready", why: "settled", pending: 0 }] as const) {
    assert.equal(step(printing.state, ev).act, "none", ev.kind + " during the print");
  }
  const rested = step(printing.state, { kind: "printed" });
  assert.equal(rested.act, "rest");
  assert.equal(rested.state.phase, "resting");
  assert.equal(step(RESTING, { kind: "ready", why: "settled", pending: 0 }).act, "none", "a late ready after a rest changes nothing");
  assert.equal(step(RESTING, { kind: "printed" }).act, "none");
});

test("the words: one picture and many, for the armed line, the wait, the open-ended wait and the ask; the four buttons' words; the ask's line and the open-ended wait's line each end with the button's own sentence, what Print anyway does (FAILS BEFORE: neither line said, and the press dropped the pictures still loading with nothing said)", () => {
  assert.equal(armedWords(1), "1 picture from another host is not loaded.");
  assert.equal(armedWords(2), "2 pictures from other hosts are not loaded.");
  assert.equal(preparingWords(1), "Preparing 1 picture…");
  assert.equal(preparingWords(3), "Preparing 3 pictures…");
  assert.equal(anywayWords(1), "Print anyway prints without it.");
  assert.equal(anywayWords(3), "Print anyway prints without them.");
  assert.equal(waitingWords(1), "Waiting for 1 picture… Print anyway prints without it.");
  assert.equal(waitingWords(3), "Waiting for 3 pictures… Print anyway prints without them.");
  assert.equal(stalledWords(1), "1 picture has not loaded. Print anyway prints without it.");
  assert.equal(stalledWords(3), "3 pictures have not loaded. Print anyway prints without them.");
  for (const n of [1, 2, 7]) for (const [site, words] of [["the ask", stalledWords(n)], ["the open-ended wait", waitingWords(n)]] as Array<[string, string]>) assert.ok(words.endsWith(" " + anywayWords(n)), site + " over " + n + ": the line ends with the button's own sentence");
  assert.equal(ANYWAY_TITLE, "Print now; a picture still loading is left out");
  assert.ok(!ANYWAY_TITLE.includes("as the browser has it"), "the title no longer says the picture prints as the browser has it: a still-loading picture with no declared size prints as nothing (case (15a))");
  assert.equal(WITH_WORDS, "Print with them");
  assert.equal(WITHOUT_WORDS, "Print without them");
  assert.equal(ANYWAY_WORDS, "Print anyway");
  assert.equal(KEEP_WORDS, "Keep waiting");
});

// ── the deadline's ask (the stalled phase) ──────────────────────────────────────────────────────────

test("the wait's verdict carries why and the count still loading: settled prints; the deadline with pictures still loading asks instead of printing; the deadline with nothing pending is a settle in effect and prints; Print anyway prints; Keep waiting resumes through the driver's prepare, into an open-ended wait or a print with nothing left; Escape or a second press disarms; a repaint under the ask counts again or rests over none, and never prints", () => {
  const preparing: PrintState = { phase: "preparing", gated: 0, pending: 2 };
  const settled = step(preparing, { kind: "ready", why: "settled", pending: 0 });
  assert.equal(settled.act, "print", "every picture settled: the print");
  assert.equal(settled.state.phase, "printing");
  const asked = step(preparing, { kind: "ready", why: "deadline", pending: 2 });
  assert.equal(asked.act, "stall", "FAILS BEFORE: the deadline with two still loading asks (the first build printed on the one ready event, which said nothing of the deadline)");
  assert.deepEqual(asked.state, { phase: "stalled", gated: 0, pending: 2 }, "the ask carries the count still loading");
  const none = step(preparing, { kind: "ready", why: "deadline", pending: 0 });
  assert.equal(none.act, "print", "the deadline with nothing pending is a settle in effect: it prints, as settled does");
  assert.equal(none.state.phase, "printing");
  assert.equal(step(preparing, { kind: "stalled", pending: 2 }).act, "none", "the driver's repaint count is the ask's event, not the wait's: during the wait it changes nothing (a repaint under the wait re-aims instead)");
  const anyway = step(asked.state, { kind: "anyway" });
  assert.equal(anyway.act, "print", "Print anyway prints at once");
  assert.equal(anyway.state.phase, "printing");
  const keep = step(asked.state, { kind: "keep" });
  assert.equal(keep.act, "resume", "Keep waiting: the driver aims the open-ended wait");
  assert.equal(keep.state, asked.state, "still asking until the driver reports the pictures");
  const resumed = step(asked.state, { kind: "prepare", pending: 1 });
  assert.equal(resumed.act, "wait");
  assert.deepEqual(resumed.state, { phase: "preparing", gated: 0, pending: 1, untimed: true }, "the wait again, marked open-ended");
  const landed = step(asked.state, { kind: "prepare", pending: 0 });
  assert.equal(landed.act, "print", "every picture landed while the ask stood: Keep waiting prints at once");
  for (const ev of [{ kind: "press", gated: 0, pending: 0 }, { kind: "escape" }] as const) {
    const r = step(asked.state, ev);
    assert.equal(r.act, "disarm", ev.kind + " under the ask disarms");
    assert.equal(r.state.phase, "resting");
  }
  const again = step(asked.state, { kind: "stalled", pending: 1 });
  assert.equal(again.act, "stall", "a repaint under the ask with one still loading: the ask again, the driver rewriting the count");
  assert.deepEqual(again.state, { phase: "stalled", gated: 0, pending: 1 });
  const moot = step(asked.state, { kind: "stalled", pending: 0 });
  assert.equal(moot.act, "disarm", "FAILS BEFORE: a repaint under the ask with nothing loading is no answer to the ask, so the question is moot and the flow rests (the line goes; the person may press again); before this the zero count was read as the print act and window.print ran with neither button pressed");
  assert.equal(moot.state.phase, "resting", "at rest, not printing");
  assert.equal(step(asked.state, { kind: "ready", why: "deadline", pending: 1 }).act, "none", "no wait runs under the ask, so a wait's verdict there changes nothing");
  for (const ev of [{ kind: "ready", why: "settled", pending: 0 }, { kind: "printed" }, { kind: "choose", withGated: true }, { kind: "recount", gated: 1 }, { kind: "body", in: true }] as const) {
    const r = step(asked.state, ev);
    assert.equal(r.act, "none", ev.kind + " under the ask changes nothing");
    assert.equal(r.state, asked.state);
  }
  const out = step(asked.state, { kind: "body", in: false });
  assert.equal(out.act, "disarm", "the body going out under the ask disarms"); assert.equal(out.state.phase, "disabled", "...and disables");
  assert.equal(step(step(asked.state, { kind: "anyway" }).state, { kind: "printed" }).act, "rest", "the print Print anyway began rests as any print does");
  for (const ev of [{ kind: "anyway" }, { kind: "keep" }, { kind: "stalled", pending: 1 }, { kind: "ready", why: "deadline", pending: 1 }] as const) {
    for (const [s, name] of [[RESTING, "rest"], [step(RESTING, { kind: "press", gated: 1, pending: 0 }).state, "the armed line"], [none.state, "the print"]] as const) {
      assert.equal(step(s, ev).act, "none", ev.kind + " during " + name + " changes nothing");
    }
  }
});

test("the open-ended wait: Escape cancels it and Print anyway prints at once with what has loaded (FAILS BEFORE: the event changed nothing during any wait, so the open-ended wait had no way through but the load), where the timed wait's Escape is left to the viewer and its anyway changes nothing (its line has no button); a press changes nothing in either; ready prints in both; the timed waits carry no mark", () => {
  const timed = step(RESTING, { kind: "press", gated: 0, pending: 2 }).state;
  assert.equal(timed.untimed, undefined, "the press's wait carries the deadline");
  assert.equal(step(timed, { kind: "escape" }).act, "none", "Escape during the timed wait is the viewer's (it closes the card, whose close cancels the wait)");
  const chosen = step(step(RESTING, { kind: "press", gated: 1, pending: 0 }).state, { kind: "prepare", pending: 2 }).state;
  assert.equal(chosen.untimed, undefined, "the armed line's choice begins a timed wait too");
  const open = step({ phase: "stalled", gated: 0, pending: 2 }, { kind: "prepare", pending: 2 }).state;
  assert.equal(open.untimed, true, "Keep waiting's wait is open-ended");
  const esc = step(open, { kind: "escape" });
  assert.equal(esc.act, "disarm", "Escape cancels the open-ended wait: no deadline would end it");
  assert.equal(esc.state.phase, "resting");
  const anyway = step(open, { kind: "anyway" });
  assert.equal(anyway.act, "print", "FAILS BEFORE: Print anyway on the open-ended wait's line prints at once with what has loaded (romp-manager's ruling, 2026-09-20); before this the event changed nothing during any wait, so the open-ended wait had no way through but the load");
  assert.equal(anyway.state.phase, "printing");
  assert.equal(anyway.state.untimed, undefined, "the print carries no mark");
  assert.equal(step(anyway.state, { kind: "printed" }).act, "rest", "the print Print anyway began rests as any print does");
  assert.equal(step(timed, { kind: "anyway" }).act, "none", "the timed wait's line has no Print anyway button, so the event changes nothing there: its deadline asks");
  assert.equal(step(chosen, { kind: "anyway" }).act, "none", "the armed line's choice begins a timed wait too, with no button");
  assert.equal(step(open, { kind: "press", gated: 0, pending: 0 }).act, "none", "a press during the open-ended wait changes nothing, as during the timed one");
  assert.equal(step(open, { kind: "ready", why: "settled", pending: 0 }).act, "print", "every picture settled: the print");
  assert.equal(step(open, { kind: "ready", why: "deadline", pending: 1 }).act, "stall", "a deadline verdict during the open-ended wait would ask again (none comes: the wait sets no timer)");
  assert.equal(step(open, { kind: "stalled", pending: 1 }).act, "none", "the repaint count is the ask's event: during the wait it changes nothing (a repaint under the wait re-aims instead)");
  assert.equal(step(open, { kind: "body", in: false }).act, "disarm", "the body going out cancels it, as any wait");
});

test("the chord: Ctrl+P and Cmd+P, either case of the key; not with Shift or Alt, not a repeat, not a bare P", () => {
  assert.equal(isPrintChord({ key: "p", ctrlKey: true }), true);
  assert.equal(isPrintChord({ key: "P", ctrlKey: true }), true, "Caps Lock reports P with no Shift");
  assert.equal(isPrintChord({ key: "p", metaKey: true }), true);
  assert.equal(isPrintChord({ key: "p", ctrlKey: true, shiftKey: true }), false);
  assert.equal(isPrintChord({ key: "p", ctrlKey: true, altKey: true }), false);
  assert.equal(isPrintChord({ key: "p", ctrlKey: true, repeat: true }), false);
  assert.equal(isPrintChord({ key: "p" }), false);
  assert.equal(isPrintChord({ key: "Escape", ctrlKey: true }), false);
  assert.equal(isPrintChord({}), false, "a bare fake event, as the node suites dispatch them, is no chord");
});

// ── the wait ────────────────────────────────────────────────────────────────────────────────────────

class FakePic implements Picture {
  complete: boolean;
  private ls: Record<string, Array<() => void>> = { load: [], error: [] };
  constructor(complete = false) { this.complete = complete; }
  addEventListener(type: string, cb: () => void): void { this.ls[type].push(cb); }
  removeEventListener(type: string, cb: () => void): void { this.ls[type] = this.ls[type].filter((f) => f !== cb); }
  fire(type: "load" | "error"): void { this.complete = true; for (const cb of [...this.ls[type]]) cb(); }
  listening(): number { return this.ls.load.length + this.ls.error.length; }
}
class FakeClock implements Timers {
  now = 0;
  private seq = 0;
  private due: Array<{ at: number; fn: () => void; id: number }> = [];
  setTimeout = (fn: () => void, ms: number): unknown => { const id = ++this.seq; this.due.push({ at: this.now + ms, fn, id }); return id; };
  clearTimeout = (h: unknown): void => { this.due = this.due.filter((d) => d.id !== h); };
  armed(): number { return this.due.length; }
  advance(ms: number): void {
    this.now += ms;
    const fire = this.due.filter((d) => d.at <= this.now);
    this.due = this.due.filter((d) => d.at > this.now);
    for (const d of fire) d.fn();
  }
}
const tick = (): Promise<void> => new Promise((r) => setTimeout(r, 0));

test("settlePictures: only the incomplete pictures are waited on; load or error on each settles it, the listeners come off and the timer is cleared", async () => {
  const done = new FakePic(true), a = new FakePic(), b = new FakePic();
  const clock = new FakeClock();
  const s = settlePictures([done, a, b], 8000, clock);
  assert.equal(s.pending(), 2, "the complete picture is not counted");
  assert.equal(done.listening(), 0, "nothing listens on a complete picture");
  assert.equal(a.listening(), 2); assert.equal(b.listening(), 2);
  assert.equal(clock.armed(), 1, "one deadline timer");
  let why: string | null = null;
  void s.done.then((w) => { why = w; });
  a.fire("load");
  await tick();
  assert.equal(s.pending(), 1);
  assert.equal(why, null, "one still loading: not settled");
  assert.equal(a.listening(), 0, "the settled picture's listeners came off");
  b.fire("error");
  await tick();
  assert.equal(why, "settled", "an error settles a picture as a load does: it prints as its label");
  assert.equal(s.pending(), 0);
  assert.equal(clock.armed(), 0, "the deadline timer is cleared");
  clock.advance(10000);
  assert.equal(why, "settled", "nothing fires later");
});

test("settlePictures: the deadline resolves the wait with pictures still pending, and their listeners come off", async () => {
  const a = new FakePic(), b = new FakePic();
  const clock = new FakeClock();
  const s = settlePictures([a, b], 8000, clock);
  let why: string | null = null;
  void s.done.then((w) => { why = w; });
  clock.advance(7999);
  await tick();
  assert.equal(why, null, "one millisecond short of the deadline");
  clock.advance(1);
  await tick();
  assert.equal(why, "deadline");
  assert.equal(s.pending(), 2, "both still loading: they print as the browser has them");
  assert.equal(a.listening() + b.listening(), 0, "no listener left on a picture the deadline abandoned");
  a.fire("load");
  await tick();
  assert.equal(why, "deadline", "a load after the deadline changes nothing");
});

test("settlePictures with no deadline: no timer is set, the events alone end the wait, and cancel still ends it", async () => {
  const a = new FakePic(), b = new FakePic();
  const clock = new FakeClock();
  const s = settlePictures([a, b], null, clock);
  assert.equal(s.pending(), 2);
  assert.equal(clock.armed(), 0, "no deadline timer for an open-ended wait");
  let why: string | null = null;
  void s.done.then((w) => { why = w; });
  clock.advance(60000);
  await tick();
  assert.equal(why, null, "a minute on: still waiting, since nothing but the events ends it");
  a.fire("load");
  await tick();
  assert.equal(why, null); assert.equal(s.pending(), 1);
  b.fire("error");
  await tick();
  assert.equal(why, "settled", "the last event settles it");
  assert.equal(a.listening() + b.listening(), 0);
  const c = new FakePic();
  const s2 = settlePictures([c], null, clock);
  s2.cancel();
  assert.equal(await s2.done, "cancelled");
  assert.equal(c.listening(), 0, "cancel takes the listeners off an open-ended wait too");
});

test("settlePictures: nothing pending resolves settled at once with no timer; cancel ends a wait without a verdict", async () => {
  const clock = new FakeClock();
  const s0 = settlePictures([new FakePic(true), new FakePic(true)], 8000, clock);
  assert.equal(s0.pending(), 0);
  assert.equal(clock.armed(), 0, "no timer for nothing");
  assert.equal(await s0.done, "settled");
  const a = new FakePic();
  const s1 = settlePictures([a], 8000, clock);
  let why: string | null = null;
  void s1.done.then((w) => { why = w; });
  s1.cancel();
  await tick();
  assert.equal(why, "cancelled");
  assert.equal(clock.armed(), 0, "the timer is cleared by the cancel");
  assert.equal(a.listening(), 0);
  a.fire("load");
  clock.advance(9000);
  await tick();
  assert.equal(why, "cancelled", "a load or the clock after the cancel changes nothing");
});

test("the deadline constant is 8 s and the seam moves it for a test and restores it with null", () => {
  assert.equal(PRINT_SETTLE_MS, 8000);
  assert.equal(printSettleMs(), 8000);
  setPrintSettleMs(300);
  assert.equal(printSettleMs(), 300);
  setPrintSettleMs(null);
  assert.equal(printSettleMs(), 8000);
});

// ── the pictures the wait collects ─────────────────────────────────────────────────────────────────

type FakeEl = Picture & PrintableNode & { getAttribute(name: string): string | null; loading?: string };
/** A body stand-in: querySelectorAll answers each selector the collector asks with the nodes filed under it. */
function fakeBody(filed: Record<string, FakeEl[]>): ParentNode {
  return { querySelectorAll: (sel: string) => (filed[sel] || []) as unknown as NodeListOf<Element> } as unknown as ParentNode;
}
/** An ancestor stand-in for the printable walk: its name, the attributes it carries and its parent. */
const node = (localName: string, attrs: string[] = [], parentElement: PrintableNode | null = null): PrintableNode => hideEdges({ localName, parentElement, hasAttribute: (k) => attrs.includes(k) });
/** A picture stand-in: its attributes (read by getAttribute and by the printable walk's hasAttribute), its parent for that walk (none: in the open body) and its name (an img unless said). */
const elm = (attrs: Record<string, string>, complete = false, loading?: string, parentElement: PrintableNode | null = null, localName = "img", seenBy?: { cv: boolean; rects: number }): FakeEl => hideEdges({ localName, parentElement, hasAttribute: (k) => k in attrs, complete, getAttribute: (k) => (k in attrs ? attrs[k] : null), addEventListener() {}, removeEventListener() {},
  ...(loading === undefined ? {} : { loading }), ...(seenBy === undefined ? {} : { checkVisibility: () => seenBy.cv, getClientRects: () => ({ length: seenBy.rects }) }) });   // seenBy: the browser's own answers, where the stand-in offers them

test("collectPictures: every img as itself; a poster and an svg image through a probe at the resolved URL; a gated poster or href (moved aside) and an unparseable value probe nothing", () => {
  const probed: string[] = [];
  const probe = (url: string): Picture => { probed.push(url); return new FakePic(); };
  const img1 = elm({}, true), img2 = elm({});
  const body = fakeBody({
    img: [img1, img2],
    "video[poster]": [elm({ poster: "clip-poster.png" }), elm({ poster: "https://pics.test/p.png" }), elm({ poster: "http://[bad" })],
    image: [elm({ href: "/diagrams/d.svg" }), elm({ "data-fv-gated-href": "https://remote.test/g.svg" })],
  });
  const pics = collectPictures(body, "http://notes-api.test/files", probe);
  assert.equal(pics.length, 2 + 3, "two imgs and three probes: two posters and one svg image");
  assert.equal(pics[0], img1); assert.equal(pics[1], img2);
  assert.deepEqual(probed, ["http://notes-api.test/clip-poster.png", "https://pics.test/p.png", "http://notes-api.test/diagrams/d.svg"]);
});

test("collectPictures sets a lazy img eager before the wait listens on it (FAILS BEFORE: a picture the browser had not started fetching fired neither event, and the wait ran to its deadline); an eager or unmarked img is left as it is", () => {
  const lazy = elm({}, false, "lazy"), eager = elm({}, false, "eager"), plain = elm({});
  const pics = collectPictures(fakeBody({ img: [lazy, eager, plain] }), "http://notes-api.test/files", () => new FakePic());
  assert.equal(pics.length, 3, "every img is collected, the lazy one among them");
  assert.equal(lazy.loading, "eager", "the lazy picture reads eager: its deferred fetch starts, and load or error will come");
  assert.equal(eager.loading, "eager"); assert.equal(plain.loading, undefined, "no attribute is added where none was");
});

test("collectPictures reads the printable rule the placeholders are counted by (FAILS BEFORE: every img, poster and svg image in the body was collected, so the wait counted, set eager and asked about a picture inside a closed fold or under hidden, one the print never shows): a picture under hidden, on itself or an ancestor, or inside a closed details is left out of each of the three collections and a lazy one among them is not set eager; a summary's picture and one inside an open details are collected", () => {
  const closed = node("details"), open = node("details", ["open"]), hiddenDiv = node("div", ["hidden"]);
  const summary = node("summary", [], closed);
  const inBody = elm({}), inSummary = elm({}, false, undefined, summary), inOpen = elm({}, false, undefined, open);
  const inClosed = elm({}, false, undefined, closed), inHidden = elm({}, false, "lazy", hiddenDiv), selfHidden = elm({ hidden: "until-found" });
  const probed: string[] = [];
  const probe = (url: string): Picture => { probed.push(url); return new FakePic(); };
  const pics = collectPictures(fakeBody({
    img: [inBody, inClosed, inSummary, inHidden, inOpen, selfHidden],
    "video[poster]": [elm({ poster: "open-clip.png" }, false, undefined, null, "video"), elm({ poster: "folded-clip.png" }, false, undefined, closed, "video")],
    image: [elm({ href: "open-d.svg" }, false, undefined, null, "image"), elm({ href: "hidden-d.svg" }, false, undefined, hiddenDiv, "image")],
  }), "http://notes-api.test/files", probe);
  assert.equal(pics.length, 3 + 2, "three imgs that reach the paper and two probes: the open clip's poster and the open diagram's image");
  assert.equal(pics[0], inBody); assert.equal(pics[1], inSummary); assert.equal(pics[2], inOpen);
  assert.deepEqual(probed, ["http://notes-api.test/open-clip.png", "http://notes-api.test/open-d.svg"], "no probe for the folded poster or the hidden svg image");
  assert.equal(inHidden.loading, "lazy", "a hidden lazy picture keeps its attribute: no fetch is started for a picture that is not on the paper");
});

// ── the printable rule's unknown side ──────────────────────────────────────────────────────────────
/** A node stand-in with the browser's own answers: `cv` for checkVisibility, `rects` for getClientRects's count. */
const seen = (localName: string, cv: boolean, rects: number, parentElement: PrintableNode | null = null, attrs: string[] = []): PrintableNode =>
  hideEdges({ localName, parentElement, hasAttribute: (k) => attrs.includes(k), checkVisibility: () => cv, getClientRects: () => ({ length: rects }) });

test("rendered: the browser's own answer where it can be asked (checkVisibility with visibility and opacity read, and at least one client rect), null where it cannot (a stand-in under node, an old engine); printable reads it after the walk, so a hiding the walk does not know falls to NOT printable: FAILS BEFORE, the walk alone answered printable for a placeholder inside a ruby's rp, a canvas's fallback content or a popover not shown", () => {
  assert.equal(rendered(node("span")), null, "no API: the browser cannot be asked");
  assert.equal(rendered(seen("span", true, 1)), true);
  assert.equal(rendered(seen("span", false, 0)), false, "no box: display none somewhere above (a popover not shown, a ruby's rp, a canvas's or a video's fallback content, a class the sheets hide)");
  assert.equal(rendered(seen("span", false, 1)), false, "a box the browser skips: a closed fold's content, a hidden=until-found ancestor (content-visibility hidden keeps the rects)");
  assert.equal(rendered(seen("image", true, 0)), false, "a layout object and no rect: an svg image inside defs, a symbol, a clipPath, a mask, a pattern or a marker");
  assert.equal(printable(seen("span", true, 1)), true, "in the open body, rendered: printable");
  assert.equal(printable(seen("span", false, 0)), false, "FAILS BEFORE: the walk finds no closed details and no hidden, and the browser says the element is not rendered");
  assert.equal(printable(seen("span", true, 1, node("details"))), false, "the walk's own answer stands whatever the browser says (a closed details holds it)");
  assert.equal(printable(seen("span", true, 1, null, ["hidden"])), false, "hidden on the element: the walk");
  const opts: Array<Record<string, boolean>> = [];
  const asked: PrintableNode = hideEdges({ localName: "span", parentElement: null, hasAttribute: () => false, checkVisibility: (o) => { opts.push(o || {}); return true; }, getClientRects: () => ({ length: 1 }) });
  printable(asked);
  assert.deepEqual(opts, [{ visibilityProperty: true, opacityProperty: true }], "checkVisibility is asked with visibility and opacity read (an svg's visibility=hidden or opacity=0, kept attributes, leave nothing on the paper) and content-visibility auto left alone (the sheets use none, and a picture far below the fold is on the paper)");
});

/** A figure stand-in inside a placeholder: its name, its attributes and, for an SVG element, its namespace (an HTML one has
 *  none here, as the flow reads a stand-in without one). It has no document, so no browser computes its style: the
 *  attributes alone answer, as printable's walk answers alone without rendered. */
const media = (localName: string, attrs: Record<string, string> = {}, namespaceURI?: string): FigureNode => ({ localName, namespaceURI, hasAttribute: (k) => k in attrs, getAttribute: (k) => (k in attrs ? attrs[k] : null) });
test("figureHidden under node, where no browser computes a style: hidden (any value) and popover on an HTML element leave the figure off the paper; on an SVG element neither is read, since the browser ignores them there (an <svg hidden> paints, measured in Chromium, Firefox and WebKit); a presentation attribute needs the browser's parse and reads nothing here (file-print-figure-browser.test.ts executes display, visibility and opacity over the real gate in Chromium, the spellings of zero among them); every other attribute leaves the figure on the paper", () => {
  assert.equal(figureHidden(media("img")), false, "a plain picture");
  assert.equal(figureHidden(media("img", { hidden: "" })), true, "hidden");
  assert.equal(figureHidden(media("img", { hidden: "until-found" })), true, "hidden=until-found: skipped until a find reveals it");
  assert.equal(figureHidden(media("img", { popover: "" })), true, "a popover is shown by a call alone, which a note cannot make");
  assert.equal(figureHidden(media("img", { popover: "manual" })), true);
  assert.equal(figureHidden(media("svg", { hidden: "" }, SVG_NS)), false, "hidden on an SVG element is not read: the browser paints an <svg hidden>");
  assert.equal(figureHidden(media("image", { popover: "" }, SVG_NS)), false, "popover on an SVG element: not read either");
  assert.equal(figureHidden(media("svg", { display: "none" }, SVG_NS)), false, "a presentation attribute with no browser to parse it reads nothing under node (in Chromium the figure leg reads it hidden)");
  assert.equal(figureHidden(media("svg", { visibility: "hidden" }, SVG_NS)), false, "the same for visibility");
  assert.equal(figureHidden(media("svg", { opacity: "0" }, SVG_NS)), false, "and for opacity: the computed value is the browser's, and there is none here");
  assert.equal(figureHidden(media("img", { display: "none" })), false, "display is no HTML attribute: on an img it styles nothing (the style attribute keeps colour alone), so the picture is on the paper");
  assert.equal(figureHidden(media("video", { poster: "x", width: "0" })), false, "a zero size is a degenerate picture the browser still draws: on the paper as far as the flow reads");
  assert.equal(figureHidden(media("picture", { inert: "" })), false, "inert renders");
  assert.equal(figureHidden(media("svg", { opacity: "0.5" })), false, "a faint figure is on the paper (in the browser too: the figure leg)");
});

test("figurePrintable under node: a placeholder reaches the paper when it does (printable: the walk and the browser) and a painting element of the figure it wraps shows: the root when it is an img, a video or an audio with controls, and the descendants PAINTS_SEL names through querySelectorAll (none on a stand-in without it), each read with its ancestors up to the root. FAILS BEFORE the round-2 census: an <img hidden> inside its placeholder had the placeholder counted and its figure fetched by Print with them for a print that never shows it; FAILS BEFORE the round-3 review: a <picture> whose <img> carries hidden was read at the picture alone and counted. No media child leaves the placeholder's own answer; the gated figure's own checkVisibility is not read", () => {
  // a placeholder stand-in around `figure`: hideEdges makes a node's methods non-enumerable, so a spread of one copies nothing; the fields are named
  const around = (base: PrintableNode, figure: FigureNode | null): PrintableNode & { firstElementChild: FigureNode | null } =>
    hideEdges({ localName: base.localName, parentElement: base.parentElement, hasAttribute: (k: string) => base.hasAttribute(k), checkVisibility: base.checkVisibility, getClientRects: base.getClientRects, firstElementChild: figure });
  const wrap = (cv: boolean, rects: number, figure: FigureNode | null): PrintableNode & { firstElementChild: FigureNode | null } => around(seen("span", cv, rects), figure);
  assert.equal(figurePrintable(wrap(true, 1, media("img"))), true, "the placeholder rendered and its picture plain");
  assert.equal(figurePrintable(wrap(true, 1, media("img", { hidden: "" }))), false, "FAILS BEFORE: the placeholder's label is rendered while the picture it wraps carries hidden");
  assert.equal(figurePrintable(wrap(true, 1, media("video"))), true, "a clip paints its poster or a frame, or its box");
  assert.equal(figurePrintable(wrap(true, 1, media("audio", { controls: "" }))), true, "a sound with controls paints them"); assert.equal(figurePrintable(wrap(true, 1, media("audio"))), false, "a sound without controls paints nothing: the browser's own sheet hides it (the figure leg measures it in Chromium)");
  assert.equal(figurePrintable(wrap(true, 1, media("picture"))), false, "a picture paints through its img: a stand-in with no descendants paints nothing");
  assert.equal(figurePrintable(wrap(true, 1, media("svg", {}, SVG_NS))), false, "an svg paints through its graphics elements: none on a stand-in");
  assert.equal(figurePrintable(wrap(false, 0, media("img"))), false, "the placeholder itself not rendered (a popover, a ruby's rp, a canvas's fallback content)");
  assert.equal(figurePrintable(wrap(true, 1, null)), true, "no media child (the placeholder alone): its own answer");
  assert.equal(figurePrintable(around(node("span"), media("img"))), true, "no browser to ask: the walk alone on the placeholder, the attributes on the figure");
  assert.equal(figurePrintable(around(node("span", [], node("details")), media("img"))), false, "the walk on the placeholder: a closed details");
  const sheetHidden: FigureNode & PrintableNode = hideEdges({ localName: "img", hasAttribute: () => false, getAttribute: () => null, parentElement: null, checkVisibility: () => false, getClientRects: () => ({ length: 0 }) });
  assert.equal(figurePrintable(wrap(true, 1, sheetHidden)), true, "the gated figure's own checkVisibility is not read (the sheet's display none on it would say hidden for every gated figure): its HTML attributes, the author's display and the computed visibility and opacity are, and a stand-in with no document offers none of the last three");
  // the descendants: a picture stand-in whose querySelectorAll hands PAINTS_SEL its img, the img's parent the picture
  const holding = (pic: FigureNode, img: FigureNode): FigureNode => hideEdges({ ...pic, querySelectorAll: (sel: string) => ({ forEach: (cb: (el: FigureNode) => void) => { assert.equal(sel, PAINTS_SEL, "the descendants are asked for by PAINTS_SEL"); cb(img); } }) });
  const inside = (attrs: Record<string, string>, parent: FigureNode): FigureNode => hideEdges({ ...media("img", attrs), parentElement: parent });
  const plainPic = media("picture"); const plainImg = inside({}, plainPic);
  assert.equal(figurePrintable(wrap(true, 1, holding(plainPic, plainImg))), true, "a picture with a plain img: the img paints");
  const hiddenImg = inside({ hidden: "" }, plainPic);
  assert.equal(figurePrintable(wrap(true, 1, holding(plainPic, hiddenImg))), false, "FAILS BEFORE: <picture><img hidden> was read at the picture alone and counted; the img is the element that paints, and it is hidden");
  const hiddenPic = media("picture", { hidden: "" }); const imgUnder = inside({}, hiddenPic);
  assert.equal(figurePrintable(wrap(true, 1, holding(hiddenPic, imgUnder))), false, "a plain img under a hidden picture: the ancestor takes it off the paper");
  const popPic = media("picture", { popover: "" });
  assert.equal(figurePrintable(wrap(true, 1, holding(popPic, inside({}, popPic)))), false, "a popover ancestor the same");
});

test("collectPictures reads the browser's answer through printable too: a picture with no box (a ruby's rp, a canvas's fallback content, a popover not shown) or without a rect (an svg image inside defs) is not collected, not set eager and not probed", () => {
  const probed: string[] = [];
  const probe = (url: string): Picture => { probed.push(url); return new FakePic(); };
  const shown = elm({}, false, "lazy", null, "img", { cv: true, rects: 1 });
  const unshown = elm({}, false, "lazy", null, "img", { cv: false, rects: 0 });
  const defsImage = elm({ href: "defs-d.svg" }, false, undefined, null, "image", { cv: true, rects: 0 });
  const pics = collectPictures(fakeBody({ img: [shown, unshown], "video[poster]": [], image: [defsImage, elm({ href: "open-d.svg" }, false, undefined, null, "image")] }), "http://notes-api.test/files", probe);
  assert.equal(pics.length, 2, "the shown picture and the open diagram's probe");
  assert.equal(pics[0], shown);
  assert.equal(shown.loading, "eager", "the shown lazy picture is set eager");
  assert.equal(unshown.loading, "lazy", "the unshown one keeps its attribute: no fetch is started for a picture the browser does not render");
  assert.deepEqual(probed, ["http://notes-api.test/open-d.svg"], "no probe for the image inside defs");
});

test("isPrintKeys enumerates the chord's keys and answers false for every other key or modifier set (the flow prevents no key it does not know; the browser's default stands for the rest): Ctrl or Meta with p or P, no Shift, no Alt; a repeat is the keys (isPrintChord alone refuses it)", () => {
  assert.equal(isPrintKeys({ key: "p", ctrlKey: true }), true); assert.equal(isPrintKeys({ key: "P", metaKey: true }), true);
  assert.equal(isPrintKeys({ key: "p", ctrlKey: true, repeat: true }), true, "a held chord's repeat is the keys");
  assert.equal(isPrintChord({ key: "p", ctrlKey: true, repeat: true }), false, "and not a press");
  for (const e of [{ key: "q", ctrlKey: true }, { key: "Enter", ctrlKey: true }, { key: "F12", metaKey: true }, { key: "Escape" }, { key: "p" }, { key: "p", shiftKey: true }, { key: "p", altKey: true },
    { key: "p", ctrlKey: true, shiftKey: true }, { key: "p", metaKey: true, altKey: true }, { key: "p", ctrlKey: true, metaKey: true, shiftKey: true }, { ctrlKey: true }, { key: undefined, ctrlKey: true }, { key: "pp", ctrlKey: true }, { key: "π", ctrlKey: true }, {}]) {
    assert.equal(isPrintKeys(e), false, JSON.stringify(e) + " is not the chord's keys");
    assert.equal(isPrintChord(e), false, JSON.stringify(e) + " is not the chord");
  }
});

// ── the PDF kind (P4) ───────────────────────────────────────────────────────────────────────────────

test("the PDF kind: a press at rest prints the document itself, whatever the counts; printed rests; a document's press is the flow above; the two lines' words", () => {
  const r = step(RESTING, { kind: "press", gated: 2, pending: 3, file: "pdf" });
  assert.equal(r.act, "printPdf");
  assert.equal(r.state.phase, "printing");
  assert.equal(step(r.state, { kind: "press", gated: 0, pending: 0, file: "pdf" }).act, "none", "a press during the print changes nothing");
  const rested = step(r.state, { kind: "printed" });
  assert.equal(rested.act, "rest");
  assert.equal(rested.state.phase, "resting");
  assert.equal(step(RESTING, { kind: "press", gated: 1, pending: 0, file: "document" }).act, "arm", "a document's press arms over a placeholder as before");
  assert.equal(step(RESTING, { kind: "press", gated: 0, pending: 0 }).act, "print", "a press with no kind is a document's");
  assert.equal(TAB_WORDS, "Print from the tab that opened.");
  assert.equal(NO_TAB_WORDS, "The browser did not open a tab for this PDF.");
});

type FakeWin = { print: unknown; location: { href: string }; document: { contentType: string } | null };
/** A body stand-in holding one `iframe.fileview-frame`, or none. */
const frameBody = (frame: { contentWindow: FakeWin | null; src: string } | null): ParentNode =>
  ({ querySelector: (sel: string) => (sel === "iframe.fileview-frame" ? frame : null) }) as unknown as ParentNode;
const win = (href: string, type: string | null, print: unknown = () => {}): FakeWin => ({ print, location: { href }, document: type === null ? null : { contentType: type } });
const BLOB = "blob:http://notes-api.test/11111111-2222-3333-4444-555555555555";

test("pdfFrameWindow: the frame's window when it holds the PDF and can print; null with no frame, a withheld window, a window left at about:blank, a print that is no function, or a window that throws", () => {
  const viewer = win(BLOB, "application/pdf");
  assert.equal(pdfFrameWindow(frameBody({ contentWindow: viewer, src: BLOB })), viewer, "Chromium's viewer document reports application/pdf");
  const paged = win(BLOB + "#page=3", "text/html");
  assert.equal(pdfFrameWindow(frameBody({ contentWindow: paged, src: BLOB + "#page=3" })), paged, "a window at the frame's own blob URL holds the bytes the frame was aimed at, whatever type its viewer reports; the #page fragment is set aside");
  const typeless = win(BLOB, null);
  assert.equal(pdfFrameWindow(frameBody({ contentWindow: typeless, src: BLOB })), typeless, "no document to ask: the location decides");
  assert.equal(pdfFrameWindow(frameBody(null)), null, "no frame: the Comments panel's pages are up");
  assert.equal(pdfFrameWindow(frameBody({ contentWindow: null, src: BLOB })), null, "a withheld window");
  assert.equal(pdfFrameWindow(frameBody({ contentWindow: win("about:blank", "text/html"), src: BLOB })), null, "the frame never loaded the PDF: a browser without a viewer downloaded the bytes and left the window at about:blank, whose print would print a blank page");
  assert.equal(pdfFrameWindow(frameBody({ contentWindow: win(BLOB, "application/pdf", null), src: BLOB })), null, "print is no function");
  const throwing: FakeWin = { print: () => {}, get location(): { href: string } { throw new Error("cross-origin"); }, document: null };
  assert.equal(pdfFrameWindow(frameBody({ contentWindow: throwing, src: BLOB })), null, "a window that withholds its location");
  // the unknown side: a document of a kind the flow does not know, at a URL that is not the frame's own, is not the PDF, and the
  // press falls to the /file tab (the safe side: a print of that window would print whatever it holds)
  assert.equal(pdfFrameWindow(frameBody({ contentWindow: win("http://notes-api.test/other.html", "text/html"), src: BLOB })), null, "an HTML document at another URL: not the PDF, the tab");
  assert.equal(pdfFrameWindow(frameBody({ contentWindow: win("http://notes-api.test/bytes", "application/octet-stream"), src: BLOB })), null, "a document of an unknown type at another URL: the tab");
  const elsewhere = win("http://notes-api.test/bytes", "application/pdf");
  assert.equal(pdfFrameWindow(frameBody({ contentWindow: elsewhere, src: BLOB })), elsewhere, "a PDF document at another URL is the PDF (the type decides)");
  const kinds = [["application/pdf", true], ["text/html", false], ["application/octet-stream", false], ["image/svg+xml", false], ["", false]] as Array<[string, boolean]>;
  for (const [type, holds] of kinds) assert.equal(pdfFrameWindow(frameBody({ contentWindow: win("http://notes-api.test/elsewhere", type), src: BLOB })) !== null, holds, "a document of type " + JSON.stringify(type) + " at another URL " + (holds ? "is the PDF" : "is not: the tab"));
});

// ── the body not in (P7) ────────────────────────────────────────────────────────────────────────────

/** A child stand-in for the readiness test: "name.class1.class2" (the viewer's own paints, spelled as the DOM reads them). */
const kidOf = (k: string): { localName: string; classList: { contains(name: string): boolean } } => { const [localName, ...classes] = k.split("."); return { localName, classList: { contains: (c: string) => classes.includes(c) } }; };
/** A body stand-in whose element children are `kids` (the DOM's `children`). */
const bodyOf = (...kids: string[]): BodyLike => hideEdges({ children: kids.map(kidOf) });
/** A body stand-in with `childNodes` alone, or with both lists, or with neither. */
const bodyLike = (b: BodyLike): BodyLike => hideEdges(b);

test("bodyReady reads the body's element children against three closed lists: a rendered root, code, a picture's box, a PDF frame's column (a loader inside it aside), the pages' host, the CodeMirror mount and a line over content are in; the loader, the plain fallback editor and a failure line alone are not; an empty body is not; a child none of the lists names is NOT in, whatever stands beside it (FAILS BEFORE: it read as content); for the PDF kind alone the pages attempt's loader reads as content", () => {
  assert.equal(bodyReady(bodyOf()), false, "an empty body (the URL viewer's before its loader)");
  assert.equal(bodyReady(bodyOf("div.fileview-load")), false, "the open's loader, the editor's chunk wait");
  assert.equal(bodyReady(bodyOf("div.fileview-load", "div.fileview-pdfhost")), false, "a document's body holding a loader and a host: not in (the kind unknown or a document's)");
  assert.equal(bodyReady(bodyOf("textarea.fileview-editor")), false, "the plain fallback editor: a print of it is one clipped page");
  assert.equal(bodyReady(bodyOf("div.fileview-err")), false, "a failure pane alone: the fetch's, imgFailed's, the URL viewer's");
  assert.equal(bodyReady(bodyOf("div.fileview-md")), true, "a rendered note");
  assert.equal(bodyReady(bodyOf("div.fileview-code")), true, "code or text (codeBlock's root, file-view.ts)");
  assert.equal(bodyReady(bodyOf("div.fileview-err", "div.fileview-md")), true, "a line over content: an empty file's, a render that fell (the line above the rows)");
  assert.equal(bodyReady(bodyOf("div.fileview-imgbox")), true, "a picture opened directly");
  assert.equal(bodyReady(bodyOf("div.fileview-pdffall")), true, "a PDF frame's column (the pages attempt's loader inside it is not the body's child, and the frame stands)");
  assert.equal(bodyReady(bodyOf("div.fileview-pdffall", "div.fileview-pdfhost")), true, "the pages attempt over a kept frame: the column and the host");
  assert.equal(bodyReady(bodyOf("div.fileview-pdfhost")), true, "the panel's pages once page 1 is drawn (the loader gone)");
  assert.equal(bodyReady(bodyOf("div.fileview-cm")), true, "the CodeMirror mount, which prints the whole file");
  assert.equal(bodyReady(bodyOf("div.fileview-md", "div.fileview-load")), false, "a loader anywhere among the children is the body loading, whatever else stands");
  // the unknown side: not in (the round-2 review, 2026-09-19: the first derivation read every child it had not seen as content)
  assert.equal(bodyReady(bodyOf("div.fileview-unlisted")), false, "FAILS BEFORE: a root none of the lists names is not in; the button stays dead rather than printing what stands");
  assert.equal(bodyReady(bodyOf("div.fileview-md", "div.fileview-unlisted")), false, "an unlisted child beside content: not in, since the flow cannot say what the press would print");
  assert.equal(bodyReady(bodyOf("span.fileview-md")), false, "the class alone is not the root: a span wearing the rendered root's class is unlisted");
  assert.equal(bodyReady(bodyOf("div.fileview-md.fv-wide")), true, "a root's element may carry more classes than its own");
  assert.equal(bodyReady(bodyOf("div")), false, "a bare div is unlisted");
  // the PDF kind: the PDF road reads nothing from the body, so the pages attempt's loader is content there (the press prints
  // through the frame or opens the /file tab), while the plain editor, a failure pane alone and an empty body stay not in
  assert.equal(bodyReady(bodyOf("div.fileview-load", "div.fileview-pdfhost"), "pdf"), true, "FAILS BEFORE: the Comments panel's pages attempt with no frame kept, the kind known to be a PDF: in (the press opens the tab, as it did before the derivation)");
  assert.equal(bodyReady(bodyOf("div.fileview-load"), "pdf"), true, "the loader alone under the PDF kind: in");
  assert.equal(bodyReady(bodyOf("div.fileview-pdffall"), "pdf"), true, "the frame's column: in for a PDF as for a document");
  assert.equal(bodyReady(bodyOf("div.fileview-err"), "pdf"), false, "a failure pane alone stays not in for a PDF: a reload of the PDF that failed");
  assert.equal(bodyReady(bodyOf("textarea.fileview-editor"), "pdf"), false, "the plain editor stays not in whatever the kind");
  assert.equal(bodyReady(bodyOf(), "pdf"), false, "an empty body stays not in");
  assert.equal(bodyReady(bodyOf("div.fileview-unlisted"), "pdf"), false, "an unlisted root stays not in whatever the kind");
  assert.equal(bodyReady(bodyOf("div.fileview-load", "div.fileview-pdfhost"), "document"), false, "a document's kind, spelled: the loader is a wait");
  assert.equal(PDF_LOADER_ROOT, "div.fileview-load", "the one wait root the PDF kind reads as content is the loader");
});

test("rootKind classes one child by its `<tag>.<class>` against the three lists: content, wait, line, else unknown; the tag and the class are both read", () => {
  for (const r of READY_ROOTS) assert.equal(rootKind(kidOf(r)), "content", r);
  for (const r of NOT_READY_ROOTS) assert.equal(rootKind(kidOf(r)), "wait", r);
  for (const r of LINE_ROOTS) assert.equal(rootKind(kidOf(r)), "line", r);
  assert.equal(rootKind(kidOf("div.fileview-unlisted")), "unknown");
  assert.equal(rootKind(kidOf("p.fileview-md")), "unknown", "the rendered root's class on another tag");
  assert.equal(rootKind(kidOf("div")), "unknown", "no class");
  assert.equal(rootKind({ localName: undefined as unknown as string, classList: { contains: () => true } }), "unknown", "a child with no localName (a stand-in under node) is unknown, so a stand-in body is never in by accident");
});

test("bodyReady reads the element children through `children`, else through `childNodes` filtered to elements (the DOM stand-ins of the node suites, which drive the real viewer over bodies with childNodes alone: FAILS BEFORE, Array.from(undefined) threw at every open), and a body with neither is not in", () => {
  const text = { nodeType: 3 };
  const viaNodes = bodyLike({ childNodes: [text, { nodeType: 1, ...kidOf("div.fileview-md") }, text] });
  assert.equal(bodyReady(viaNodes), true, "the rendered root among text nodes, read through childNodes");
  assert.equal(bodyReady(bodyLike({ childNodes: [text, { nodeType: 1, ...kidOf("div.fileview-load") }] })), false, "the loader through childNodes: not in");
  assert.equal(bodyReady(bodyLike({ childNodes: [text] })), false, "text alone: no element child, not in");
  assert.equal(bodyReady(bodyLike({ childNodes: [{ nodeType: 1, tagName: "DIV", classList: { contains: () => true } } as unknown as { nodeType: number }] })), false, "a stand-in element without localName is unknown: not in");
  assert.equal(bodyReady(bodyLike({})), false, "a body that reports neither children nor childNodes cannot be read: not in (the safe side; a DOM body always has both)");
  assert.equal(bodyReady(bodyLike({ children: [kidOf("div.fileview-md")], childNodes: [text] })), true, "children wins when both stand: it is the DOM's own element list");
});

// ── the census of the body's roots (P7) ────────────────────────────────────────────────────────────
// bodyReady classes a child it has never seen as UNKNOWN, and an unknown child makes the body not in whatever stands beside
// it (the safe side: a press that prints what stands is the dangerous one; the person can still close and reopen), so a
// root the viewer gains would lock Print silently unless something reads the viewer. This census does: it reads file-view.ts
// and collects EVERY member the viewer reaches on `body` (`body.<member>`, with `document.body` and any other receiver's
// `.body` aside), then classes each use by what follows the member: a CALL of a seating method has its seated arguments
// resolved down to the root element's `el("<tag>", "<class>")` (SEATING: replaceChildren, prepend and append seat every
// argument; appendChild and insertBefore their first, insertBefore's second being the reference child; insertAdjacentElement
// its second, the first being the position); a call of a method that seats nothing passes (NON_SEATING_CALLS); an
// ASSIGNMENT to a scalar passes (NON_SEATING_ASSIGNS: scrollTop, scrollLeft, tabIndex); a bare READ passes, since a read
// seats nothing; and EVERY OTHER USE FAILS the census with its line: a call it does not know, an assignment it does not
// know (innerHTML, outerHTML, textContent and insertAdjacentHTML seat what no resolver can read), and a member that reaches
// a child node (firstChild, children and their kin) followed by a further access, behind which a seat could hide. The file
// is read once more for a child-level seat anywhere (replaceWith, after, before, replaceChild, insertAdjacentElement,
// insertAdjacentHTML), which the census cannot attribute to the body and fails on sight; file-view.ts has none. The
// resolved set is then held equal to the flow's three lists (READY_ROOTS, NOT_READY_ROOTS, LINE_ROOTS) and bodyReady is
// executed over each root as its list says. Each seated expression resolves as before: a builder call (`mdBlock(...)`) to
// the `el(...)` assigned to the variable the builder's last `return` names; a bare variable to the expression assigned to it
// last before the site; a ternary to both its branches; an `el("<tag>", "<class>")` to itself; anything else fails with the
// expression. The round-3 review (2026-09-20): before this the sites were found by a closed list of three method names
// (replaceChildren, prepend, appendChild) and its unknown passed, so a root seated by body.append or body.insertBefore was
// invisible to it and the guarantee the lists state was false; the mutant case below executes both seats and an innerHTML
// assignment against the census over the same source. What this census cannot see is a seat through another name for the
// body (a helper handed the body seating under its own parameter name): file-view.ts's body is seated by the one name.
/** file-view.ts with its trailing `//` comments removed (a space or a tab before the `//`; the newlines stay, so an index
 *  still maps to its line): the test runs in vscode-extension, and reads the tree as real-viewer-leg.ts does. */
const VIEWER_SRC = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "file-view.ts"), "utf8").replace(/[ \t]\/\/[^\n]*/g, "");
/** The text between the bracket at `at` and its match, strings skipped. */
function balancedAt(src: string, at: number): string {
  let depth = 0;
  for (let i = at; i < src.length; i++) {
    const c = src[i];
    if (c === '"' || c === "'" || c === "`") { i++; while (i < src.length && src[i] !== c) { if (src[i] === "\\") i++; i++; } continue; }
    if (c === "(" || c === "[" || c === "{") depth++;
    else if (c === ")" || c === "]" || c === "}") { depth--; if (depth === 0) return src.slice(at + 1, i); }
  }
  throw new Error("unbalanced bracket at " + at);
}
/** The index of the first `sep` in `expr` outside brackets and strings, or -1. */
function indexTop(expr: string, sep: string): number {
  let depth = 0;
  for (let i = 0; i < expr.length; i++) {
    const c = expr[i];
    if (c === '"' || c === "'" || c === "`") { i++; while (i < expr.length && expr[i] !== c) { if (expr[i] === "\\") i++; i++; } continue; }
    if (c === "(" || c === "[" || c === "{") depth++;
    else if (c === ")" || c === "]" || c === "}") depth--;
    else if (depth === 0 && expr.startsWith(sep, i)) return i;
  }
  return -1;
}
/** `expr` split at each top-level `sep`. */
function splitTop(expr: string, sep: string): string[] {
  const out: string[] = [];
  let rest = expr;
  for (let at = indexTop(rest, sep); at >= 0; at = indexTop(rest, sep)) { out.push(rest.slice(0, at)); rest = rest.slice(at + sep.length); }
  out.push(rest);
  return out;
}
/** The roots (`<tag>.<class>`) the expression `expr`, written at `before` in `src`, seats. */
function rootsOf(src: string, expr: string, before: number): string[] {
  const e = expr.trim();
  const q = indexTop(e, " ? ");
  if (q >= 0) {
    const branches = e.slice(q + 3);
    const c = indexTop(branches, " : ");
    assert.ok(c >= 0, "a ternary has both branches: " + e);
    return [...rootsOf(src, branches.slice(0, c), before), ...rootsOf(src, branches.slice(c + 3), before)];
  }
  const built = /^el\("(\w+)", "([\w -]+)"\)$/.exec(e);
  if (built) return [built[1] + "." + built[2].split(" ").join(".")];
  const call = /^(\w+)\(/.exec(e);
  if (call && call[1] !== "el") {
    const head = "\nfunction " + call[1] + "(";
    const at = src.indexOf(head);
    assert.ok(at >= 0, "the builder " + call[1] + " is a top-level function of file-view.ts");
    const end = src.indexOf("\n}\n", at);
    const body = src.slice(at, end);
    const returns = [...body.matchAll(/^\s+return (\w+);$/gm)];
    assert.ok(returns.length >= 1, "the builder " + call[1] + " returns a variable");
    return rootsOf(src, returns[returns.length - 1][1], at + body.length);
  }
  const name = /^(\w+)$/.exec(e);
  if (name) {
    const assigned = [...src.slice(0, before).matchAll(new RegExp("\\b" + name[1] + " = (?!=)([^;\\n]+?)(?: as \\w+)?;", "g"))];
    assert.ok(assigned.length >= 1, "the variable " + name[1] + " is assigned before the site at " + before);
    const last = assigned[assigned.length - 1];
    return rootsOf(src, last[1], last.index!);
  }
  throw new Error("a seated expression the census cannot resolve: " + e);
}
/** The seating methods and which of a call's arguments each seats. */
const SEATING: Record<string, (args: string[]) => string[]> = {
  replaceChildren: (a) => a, prepend: (a) => a, append: (a) => a,
  appendChild: (a) => a.slice(0, 1), insertBefore: (a) => a.slice(0, 1), insertAdjacentElement: (a) => a.slice(1, 2),
};
/** The body's methods the viewer calls that seat nothing: listeners, queries, the keyboard, geometry, containment. */
const NON_SEATING_CALLS = ["addEventListener", "removeEventListener", "querySelector", "querySelectorAll", "focus", "blur", "contains", "getBoundingClientRect", "getClientRects", "scrollTo", "scrollBy", "dispatchEvent"];
/** The scalars the viewer assigns on the body: a scroll offset, the tab order. */
const NON_SEATING_ASSIGNS = ["scrollTop", "scrollLeft", "tabIndex"];
/** The members that hand out a node of the body's tree: a further access on one could seat where the census cannot follow. */
const NODE_MEMBERS = ["firstChild", "lastChild", "firstElementChild", "lastElementChild", "children", "childNodes", "parentNode", "parentElement", "nextSibling", "previousSibling", "nextElementSibling", "previousElementSibling"];
/** The census over `src`: the roots seated, each with the lines that seat it, and every use the census refuses, each with its
 *  line and why. */
function census(src: string): { seated: Map<string, number[]>; refused: string[] } {
  const lineAt = (i: number): number => src.slice(0, i).split("\n").length;
  const seated = new Map<string, number[]>();
  const refused: string[] = [];
  for (const m of src.matchAll(/(?<![\w$.])body\.(\w+)/g)) {
    const member = m[1], after = m.index! + m[0].length, line = lineAt(m.index!);
    const tail = /^\s*!?\s*(\(|=(?!=)|\??\.|\[|)/.exec(src.slice(after))![1];   // what follows the member (a non-null `!` skipped): a call, an assignment (not a comparison), a further access, or nothing, a read
    if (tail === "(") {
      const seats = SEATING[member];
      if (seats) {
        const args = balancedAt(src, src.indexOf("(", after)).replace(/\s+/g, " ").trim();
        for (const arg of seats(args ? splitTop(args, ",") : [])) for (const root of rootsOf(src, arg, m.index!)) seated.set(root, [...(seated.get(root) || []), line]);
      } else if (!NON_SEATING_CALLS.includes(member)) refused.push("line " + line + ": body." + member + "(...) is a call the census does not know");
    } else if (tail === "=") {
      if (!NON_SEATING_ASSIGNS.includes(member)) refused.push("line " + line + ": body." + member + " = ... is an assignment the census does not know (innerHTML and its kin seat what no resolver reads)");
    } else if ((tail === "." || tail === "?." || tail === "[") && NODE_MEMBERS.includes(member)) refused.push("line " + line + ": body." + member + " hands out a node and a further access on it could seat where the census cannot follow");
  }
  for (const m of src.matchAll(/\.(replaceWith|after|before|replaceChild|insertAdjacentElement|insertAdjacentHTML)\(/g)) refused.push("line " + lineAt(m.index!) + ": ." + m[1] + "(...) seats through a node the census cannot attribute to the body");
  return { seated, refused };
}

test("the census of the body's roots: every use of `body` in file-view.ts is one the census classes (a seating call, resolved; a call, an assignment or a read that seats nothing) and the file seats through no child, else the census FAILS with the line; every element the viewer seats resolves to a root the flow lists (READY_ROOTS, NOT_READY_ROOTS or LINE_ROOTS), every listed root is seated, no root is in two lists, bodyReady answers over each root as its list says, an unlisted child is NOT in (the safe side, so a root the viewer gains fails here until it is listed), and under the PDF kind the loader alone of the wait roots reads as content", (t) => {
  const { seated, refused } = census(VIEWER_SRC);
  assert.deepEqual(refused, [], "every use of the body is one the census knows how to read: a use it does not is read by hand and the census taught it, never skipped");
  const roots = [...seated.keys()].sort();
  t.diagnostic("census: " + roots.map((r) => r + " (line " + seated.get(r)!.join(", ") + ")").join("; "));
  assert.ok([...seated.values()].reduce((n, ls) => n + ls.length, 0) >= 10, "the seating sites are found in file-view.ts");
  const listed = [...READY_ROOTS, ...NOT_READY_ROOTS, ...LINE_ROOTS].sort();
  assert.deepEqual(roots, listed, "the roots the viewer seats in the body are the roots the flow lists, no more and no fewer");
  assert.equal(new Set(listed).size, listed.length, "no root is in two lists");
  for (const r of READY_ROOTS) assert.equal(bodyReady(bodyOf(r)), true, r + " alone: the body is in");
  for (const r of NOT_READY_ROOTS) {
    assert.equal(bodyReady(bodyOf(r)), false, r + " alone: not in");
    for (const c of READY_ROOTS) assert.equal(bodyReady(bodyOf(c, r)), false, r + " beside " + c + ": not in, whatever else stands");
  }
  for (const r of LINE_ROOTS) {
    assert.equal(bodyReady(bodyOf(r)), false, r + " alone: not in");
    for (const c of READY_ROOTS) assert.equal(bodyReady(bodyOf(r, c)), true, r + " over " + c + ": a line over content, in");
  }
  assert.equal(bodyReady(bodyOf("div.fileview-unlisted")), false, "FAILS BEFORE: a child none of the lists names is not in; this census is what turns a new root into a red test rather than a dead button");
  for (const c of READY_ROOTS) assert.equal(bodyReady(bodyOf(c, "div.fileview-unlisted")), false, "an unlisted child beside " + c + ": not in");
  for (const r of NOT_READY_ROOTS) assert.equal(bodyReady(bodyOf(r), "pdf"), r === PDF_LOADER_ROOT, r + " alone under the PDF kind: " + (r === PDF_LOADER_ROOT ? "in (the pages attempt's loader; the PDF road reads nothing from the body)" : "not in"));
  assert.ok(NOT_READY_ROOTS.includes(PDF_LOADER_ROOT), "the PDF kind's exception is one of the wait roots");
  for (const r of LINE_ROOTS) assert.equal(bodyReady(bodyOf(r), "pdf"), false, r + " alone under the PDF kind: not in");
});

test("the census refuses its unknown and derives its population, executed over mutants of file-view.ts's source: a root seated by body.append or body.insertBefore is resolved and fails the lists (FAILS BEFORE: the three-name list never saw either, so the census passed over both), a seat through an innerHTML assignment, a call the census does not know, a further access on a child node and a child-level replaceWith each fail with their line, and a read or a scroll assignment passes", () => {
  const at = (src: string, needle: string): number => { const i = src.indexOf(needle); assert.ok(i >= 0, needle + " is in the source"); return i; };
  const seat = (call: string): string => { const i = at(VIEWER_SRC, "\n  body.appendChild(load);\n"); return VIEWER_SRC.slice(0, i) + "\n  " + call + VIEWER_SRC.slice(i); };   // a line inside the local viewer's open, before its loader is seated
  const before = census(VIEWER_SRC);
  const appended = census(seat('body.append(el("div", "fileview-mutant"));'));
  assert.deepEqual(appended.refused, [], "body.append is a seating call the census knows");
  assert.deepEqual([...appended.seated.keys()].filter((r) => !before.seated.has(r)), ["div.fileview-mutant"], "FAILS BEFORE: the root body.append seats is resolved (the three-name list never saw an append)");
  const inserted = census(seat('body.insertBefore(el("div", "fileview-mutant"), body.firstChild);'));
  assert.deepEqual(inserted.refused, [], "insertBefore's first argument is the seat; its second, the reference child, is a bare read of firstChild and seats nothing");
  assert.deepEqual([...inserted.seated.keys()].filter((r) => !before.seated.has(r)), ["div.fileview-mutant"], "FAILS BEFORE: the root body.insertBefore seats is resolved");
  const adjacent = census(seat('body.insertAdjacentElement("afterbegin", el("div", "fileview-mutant"));'));
  assert.deepEqual([...adjacent.seated.keys()].filter((r) => !before.seated.has(r)), ["div.fileview-mutant"], "insertAdjacentElement seats its second argument");
  const html = census(seat('body.innerHTML = "<div class=\\"fileview-mutant\\"></div>";'));
  assert.equal(html.refused.length, 1, "an innerHTML assignment is refused"); assert.match(html.refused[0], /^line \d+: body\.innerHTML = \.\.\. is an assignment the census does not know/);
  const unknownCall = census(seat('body.replaceChild(el("div", "fileview-mutant"), load);'));
  assert.equal(unknownCall.refused.length, 2, "a call the census does not know is refused, and the child-level read of the file finds the same replaceChild"); assert.match(unknownCall.refused[0], /^line \d+: body\.replaceChild\(\.\.\.\) is a call the census does not know/);
  const chained = census(seat('body.firstElementChild!.replaceWith(el("div", "fileview-mutant"));'));
  assert.equal(chained.refused.length, 2, "a further access on a child node is refused, and so is the replaceWith it reaches"); assert.match(chained.refused[0], /^line \d+: body\.firstElementChild hands out a node/); assert.match(chained.refused[1], /^line \d+: \.replaceWith\(\.\.\.\) seats through a node/);
  const reads = census(seat('if (body.scrollTop > 0 && body.clientWidth === 0 && typeof body.getClientRects === "function") body.scrollTop = 0;'));
  assert.deepEqual(reads.refused, [], "reads and a scroll assignment seat nothing and pass");
  assert.deepEqual([...reads.seated.keys()].sort(), [...before.seated.keys()].sort(), "...and seat no root");
  const unresolvable = (): void => { census(seat('body.appendChild(someRoot);')); };
  assert.throws(unresolvable, /the variable someRoot is assigned before the site/, "an argument the census cannot resolve fails with the expression");
});

test("disabled until the body is in: the driver's start, where a press (the button's or the chord's), an Escape, a choice, a prepare, a ready and a printed change nothing; the body arriving rests; the body going out from rest, armed, the wait or the print disarms and disables; the body's arrival elsewhere changes nothing", () => {
  assert.equal(DISABLED.phase, "disabled");
  for (const ev of [{ kind: "press", gated: 0, pending: 0 }, { kind: "press", gated: 2, pending: 1 }, { kind: "press", gated: 0, pending: 0, file: "pdf" }, { kind: "escape" },
    { kind: "choose", withGated: true }, { kind: "prepare", pending: 1 }, { kind: "ready", why: "settled", pending: 0 }, { kind: "stalled", pending: 1 }, { kind: "anyway" }, { kind: "keep" }, { kind: "printed" }, { kind: "body", in: false }] as const) {
    const r = step(DISABLED, ev);
    assert.equal(r.act, "none", ev.kind + " while disabled changes nothing");
    assert.equal(r.state, DISABLED, ev.kind + " while disabled keeps the state");
  }
  const on = step(DISABLED, { kind: "body", in: true });
  assert.equal(on.act, "none", "the body's arrival needs no act: the driver's sync reads the phase");
  assert.equal(on.state.phase, "resting");
  assert.equal(step(on.state, { kind: "press", gated: 0, pending: 0 }).act, "print", "the first press after the body is in prints");
  const armed = step(RESTING, { kind: "press", gated: 1, pending: 0 }).state;
  const preparing: PrintState = { phase: "preparing", gated: 0, pending: 2 };
  const stalled: PrintState = { phase: "stalled", gated: 0, pending: 2 };
  const printing: PrintState = { phase: "printing", gated: 0, pending: 0 };
  for (const [s, name] of [[RESTING, "rest"], [armed, "the armed line"], [preparing, "the wait"], [stalled, "the ask"], [printing, "the print"]] as const) {
    const out = step(s, { kind: "body", in: false });
    assert.equal(out.act, "disarm", "the body going out during " + name + " disarms: the line goes and the driver cancels the wait");
    assert.equal(out.state.phase, "disabled", "...and disables");
    const stay = step(s, { kind: "body", in: true });
    assert.equal(stay.act, "none", "the body's arrival during " + name + " changes nothing");
    assert.equal(stay.state, s);
  }
  assert.equal(step(step(printing, { kind: "body", in: false }).state, { kind: "printed" }).act, "none", "a print's end after the body went out leaves the button disabled");
});
