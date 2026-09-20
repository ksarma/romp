// The print flow's machine and its wait (file-print.ts; the print follow-on to plans/markdown-viewer.md's Slice 3, item 12),
// executed under node with no DOM: `step` over every phase and event (the disabled phase the driver starts in, P7, and the
// stalled phase the deadline's ask stands in, among them), the words, the chord, and settlePictures over fake pictures and a
// fake clock (the deadline is the one timer in the module, and it is injected; Keep waiting's wait sets none). The DOM driver, the button,
// the line and window.print run over the real viewer in file-print-browser.test.ts. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import * as ts from "typescript";   // the census blanks file-view.ts's comments with the compiler's own read of them (the round-5 fix; writer-census.ts is the precedent, a runtime require of the test bundle)
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

test("the words: one picture and many, for the armed line, the wait, the open-ended wait and the ask; the four buttons' words; the ask's line and the open-ended wait's line each end with the button's own sentence, what Print anyway does (FAILS BEFORE: neither line said, and the press dropped the pictures still loading with nothing said), a sentence that takes no count and names no picture, since a picture the count covers can land while the line stands and then prints (FAILS BEFORE: the sentence read \"prints without them\", them being the counted pictures)", () => {
  assert.equal(armedWords(1), "1 picture from another host is not loaded.");
  assert.equal(armedWords(2), "2 pictures from other hosts are not loaded.");
  assert.equal(preparingWords(1), "Preparing 1 picture…");
  assert.equal(preparingWords(3), "Preparing 3 pictures…");
  assert.equal(anywayWords(), "Print anyway leaves out any picture still loading.");
  assert.equal(anywayWords.length, 0, "the sentence takes no count: it is the same words beside every count, true of whichever pictures are still loading at the press (the round-5 review's ui-1)");
  assert.equal(waitingWords(1), "Waiting for 1 picture… Print anyway leaves out any picture still loading.");
  assert.equal(waitingWords(3), "Waiting for 3 pictures… Print anyway leaves out any picture still loading.");
  assert.equal(stalledWords(1), "1 picture has not loaded. Print anyway leaves out any picture still loading.");
  assert.equal(stalledWords(3), "3 pictures have not loaded. Print anyway leaves out any picture still loading.");
  for (const n of [1, 2, 7]) for (const [site, words] of [["the ask", stalledWords(n)], ["the open-ended wait", waitingWords(n)]] as Array<[string, string]>) assert.ok(words.endsWith(" " + anywayWords()), site + " over " + n + ": the line ends with the button's own sentence");
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

test("offPaper below the figure's root reads the display the browser COMPUTES, the root the author's declaration: a group hidden by a sheet rule on its class (no attribute, no style) takes the image inside it off the paper, so the figure is not printable (FAILS BEFORE: the author's declaration read empty and the figure counted, its host named and fetched); the same group with a computed display of inline leaves it on the paper; and the root's own computed display none, the gate's sheet on every gated figure, is not read (the author road), so a plain figure stays printable (the round-4 review's extra8-3, 2026-09-20)", () => {
  const computed = new Map<object, string>();
  const doc = { defaultView: { getComputedStyle: (el: unknown) => ({ visibility: "visible", opacity: "1", display: computed.get(el as object) || "inline" }) }, createElement: () => ({ style: { display: "" } }) };
  const svgEl = (localName: string, parentElement: FigureNode | null, descendants: FigureNode[] = []): FigureNode =>
    hideEdges({ localName, namespaceURI: SVG_NS, parentElement, hasAttribute: () => false, getAttribute: () => null, ownerDocument: doc,
      querySelectorAll: (sel: string) => ({ forEach: (cb: (el: FigureNode) => void) => { assert.equal(sel, PAINTS_SEL); descendants.filter((d) => d.localName === "image").forEach(cb); } }) });
  const build = (): { root: FigureNode; group: FigureNode } => {
    const root = svgEl("svg", null, []);
    const group = svgEl("g", root);
    const image = svgEl("image", group);
    (root as unknown as { querySelectorAll: unknown }).querySelectorAll = (sel: string) => ({ forEach: (cb: (el: FigureNode) => void) => { assert.equal(sel, PAINTS_SEL); [image].forEach(cb); } });
    return { root, group };
  };
  const around = (figure: FigureNode): PrintableNode & { firstElementChild: FigureNode | null } => hideEdges({ localName: "span", parentElement: null, hasAttribute: () => false, checkVisibility: () => true, getClientRects: () => ({ length: 1 }), firstElementChild: figure });
  const hiddenGroup = build();
  computed.set(hiddenGroup.root as object, "none");    // the gate's sheet on the root
  computed.set(hiddenGroup.group as object, "none");   // a sheet rule on the group's class
  assert.equal(figurePrintable(around(hiddenGroup.root)), false, "FAILS BEFORE: the group's computed display none is read below the root, so the image inside it is off the paper and the figure paints nothing");
  assert.equal(figureHidden(hiddenGroup.root), false, "the root itself reads the author's declaration, not the sheet's none: the figure is not hidden as a whole");
  const plain = build();
  computed.set(plain.root as object, "none");
  assert.equal(figurePrintable(around(plain.root)), true, "the root's computed none (the gate's sheet) is not read, and the group computes inline: the figure is printable");
  assert.equal(figureHidden(plain.root), false);
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
// root the viewer gains would lock Print silently unless something reads the viewer. This census does, and its DEFAULT
// REFUSES (the round-5 review, 2026-09-20): it passes a closed set of sanctioned forms, each read by hand and listed, and
// fails every other form with its line, so a spelling nobody here thought of reds and is looked at rather than passing. It
// reads file-view.ts with its comments blanked by the compiler (every comment range the TypeScript parser reports, wherever
// it stands: a doc comment, a `//` at the start of a line or after a `;`, a trailing one) and reads it twice.
// FIRST, EVERY `body` token outside a string, template or regular-expression literal. A token a member access follows
// (`body.<member>`, `body?.<member>`, `body[...]` or `body?.[...]`, across any whitespace and a non-null `!`; `document.body`
// and any other receiver's `.body` are not the token) is classed by what follows the member: a CALL of a seating method (`(`
// or `?.(`) has its seated arguments resolved down to the root element's `el("<tag>", "<class>")` (SEATING: replaceChildren,
// prepend and append seat every argument; appendChild and insertBefore their first, insertBefore's second being the
// reference child; insertAdjacentElement its second, the first being the position); a call of a method the census lists as
// seating nothing passes (NON_SEATING_CALLS); an ASSIGNMENT (`=` and the compound forms) to a listed scalar passes
// (NON_SEATING_ASSIGNS: scrollTop, scrollLeft, tabIndex); a FURTHER ACCESS (`.`, `?.`, `[`) on a listed scalar or on
// classList, style or dataset passes (FURTHER_MEMBERS); a bare READ of a listed scalar, or of a non-seating method as a value
// (`typeof body.getClientRects`), passes (READ_MEMBERS), and a bare read of a node member (NODE_MEMBERS) passes in one place
// alone, directly inside the argument list of a `body` call the census read (the reference child of
// `body.insertBefore(x, body.firstChild)`), not inside a nested call's list or a callback's braces within it (the round-5
// review's tests-1: the exemption applied anywhere inside the arguments, so a listener's callback read a node and seated it);
// and every other member access on `body` FAILS the census with its line: a computed name (`body["append"]`), a call it
// does not list (`closest`, `getRootNode`), an assignment it does not list (innerHTML, outerHTML, textContent and
// insertAdjacentHTML seat what no resolver can read), a further access on a member that hands out a child node (firstChild,
// children and their kin), on a seating method (`body.append.call`, `.bind`, `.apply`) or on any member not listed, and a
// bare read of any member not listed (a seating method handed out, `const seat = body.append`, seats later where no census
// can follow). A token NO member access follows is classed by its context: a declaration, a parameter, a declared type or
// a property key (`const body =`, `(body: HTMLElement)`, `body: string;`, `body: foldBody(d)`) and a comparison operand
// (`activeElement === body`) pass; the viewer's action-context accessor (`body: () => body`, the one hand-out to the Comments
// panel, read by hand) passes at ONE SITE, inside the object literal declared `const ctx: FileViewActionCtx =`, the census
// holds the source to declaring that literal, and the spelling anywhere else fails (the round-5 review's extra8-2: keyed on
// its spelling, it passed anywhere); an argument, or a property of an argument, passes when the callee is one BODY_HANDED_TO
// lists (each read by hand for what it does with the body; a callee whose own parameter is named `body` has its member
// accesses read by this census like the viewer's own, and the census holds its declaration to that name); and EVERY OTHER
// `body` TOKEN FAILS the census with its line: an alias (`const b = body`), a return, an arrow's value, an array element, a
// ternary or logical operand, a parenthesised or cast receiver (`(body).append`, `(body as HTMLElement).append`), an
// argument to a callee the census does not list (`Element.prototype.append.call(body, x)`, a helper of its own).
// SECOND, EVERY MEMBER CALL in the file on ANY receiver, by the compiler's tree (seatSites), classed by the member's NAME
// (the round-6 review's census-1, 2026-09-20: the form axis is an allowlist too). A call of a method that seats a node
// (SEAT_CALLS: the six the body's read resolves; replaceWith, after, before, replaceChild and insertAdjacentHTML; a range's
// insertNode and surroundContents; setHTMLUnsafe; moveBefore; write and writeln) and an assignment to innerHTML or
// outerHTML (SEAT_ASSIGNS) are SEATS; a call, apply or bind, a mount or render, and any method of Object, Reflect or
// Function (SITE_CALLS, SITE_RECEIVERS) are calls read BY THEIR SITE; a method by a name NON_SEATING_METHODS lists, each
// read by hand as seating nothing, passes; and a method by ANY OTHER NAME fails the census with its line. A seat whose
// receiver is the sanctioned `body` token (the identifier, a non-null `!` allowed) was the first read's; EVERY OTHER SEAT
// and every site-read call passes only as a SITE the census lists, read by hand (SEATS_READ_BY_HAND: the enclosing
// function's name, the receiver's spelling and the form, with what the receiver is and so why its seat lands no child in
// the body, and, for a receiver that is a bare name, the DECLARATION it is bound to by the language's scopes; the round-6
// review's census-2: an entry is held to ONE binding, so a second declaration of a listed name inside the entry's
// function, a block's `const main = md.parentElement!` or a callback's `(main) =>`, fails with its line rather than
// passing under the entry's claim), and FAILS the census with its line otherwise, whatever produced the receiver:
// `body.querySelector(...)!.parentElement!.append(x)`, a stored query result (`const md2 = body.querySelector(...);
// md2!.append(x)`), `md.parentElement!.append(x)`, a parent held in a variable, `body.closest(...)!.append(x)`,
// `body.getRootNode().appendChild(x)`, a node read inside a listener and seated, `(body).append(x)`, an alias's seat, a
// range's `insertNode`, `setHTMLUnsafe`, `moveBefore`, `Object.assign(md, { innerHTML })`, `Reflect.set(md, "innerHTML",
// ...)`. A seating or site-read method READ WITHOUT BEING CALLED fails with its line (`md.append.call(md, x)`,
// `Element.prototype.append.call(md.parentElement, x)`, `Reflect.apply(md.append, ...)`, a bound seat, `const f =
// md.append`, `md["append"]`: it runs later where the census cannot read its receiver); a call through a computed name
// (`x["append"](...)`, `x[m](...)`) fails wherever it stands, since the census cannot read what it calls; a call whose
// callee is neither a name nor a member (`(md.append)(x)`, a call's value called) fails; and a member read by a computed
// name and STORED or handed on (`const f = md[m]`) passes only as a site INDEX_READS_BY_HAND lists (its function and
// receiver, with what the receiver is), where one only compared, tested or read further (`rows[i].id`) is an index read
// and passes. A listed site the source no longer has fails too (a stale entry is removed, never kept). The resolved set
// is then held equal to the flow's three lists (READY_ROOTS, NOT_READY_ROOTS, LINE_ROOTS) and bodyReady is executed over
// each root as its list says. Each seated expression resolves as before: a builder call (`mdBlock(...)`) to the `el(...)`
// assigned to the variable the builder's last `return` names; a bare variable to the expression assigned to it last before
// the site; a ternary to both its branches; an `el("<tag>", "<class>")` to itself; anything else fails with the expression.
// The round-3 review (2026-09-20): before this the sites were found by a closed list of three method names
// (replaceChildren, prepend, appendChild) and its unknown passed, so a root seated by body.append or body.insertBefore was
// invisible to it and the guarantee the lists state was false. The round-4 review (2026-09-20): the collect pattern read
// `body.<member>` alone, so `body?.append(x)` and `body["append"](x)` were outside it, `body.append?.(x)` was a further
// access refused for NODE_MEMBERS alone, and `body.append.call(body, x)` and a bare `body.append` passed. The round-5 fix
// (2026-09-20): the census read member accesses on the `body` token alone, so a parenthesised or cast receiver
// (`(body).append(x)`) and the body under another name (`const b = body; b.append(x)`, the body as an argument) seated
// with no refusal and no root; and its comment strip blanked a `//` only after a space or a tab, so a seat quoted in a
// comment at the start of a line counted as a seat and a real seat moved into one kept the census green. The round-5
// review (2026-09-20): the census refused a closed list of dangerous forms (six child-level method names, read anywhere)
// and passed every other seat unread, so six spellings seated with no refusal and no root (a seat through
// `body.querySelector(...)!.parentElement`, a node read inside any body call's arguments, a listener's callback included,
// then seated, `md.parentElement!.append(x)`, the accessor by its spelling, a stored query result); the default now
// refuses, every seat in the file is read against the table, and the mutant case below plants every one of those forms and
// reads the census red with the planted line. The round-6 review (2026-09-20): the inversion landed on the receiver axis
// alone, and the second read still knew a closed list of eleven seating names and two assignments and passed every other
// form on a receiver other than the body, so a seating method reached through call, bind or apply, through Reflect.apply or
// as a bound function, a range's insertNode, setHTMLUnsafe and moveBefore seated with no refusal and no root, an entry
// keyed on a receiver's spelling covered a second binding of the same name, and a spread into a body seat threw with no
// line; the form axis now passes a listed name and refuses every other with its line, each entry names its binding, the
// resolver's failure is a refusal with the line, and the mutant case plants each of those forms. What this census cannot
// see is what a LISTED callee does with the body it is handed, what a LISTED site's receiver is, and what a LISTED method
// does by its name: each is read by hand when it is listed, never derived, and a new callee, a new site or a new method
// name fails the census until it is read and listed.
/** file-view.ts with its comments blanked: every comment range the TypeScript parser reports (leading and trailing trivia of
 *  every token, a doc comment, a `//` at the start of a line or after a `;`, a `//` after a space or a tab, a block comment
 *  anywhere), each replaced by spaces of its own length with its newlines kept, so an index still maps to its line and no
 *  prose is read as code (the collect pattern reads across whitespace, and a doc-comment's "the body. The …" would
 *  otherwise read as a member access; the round-4 review, 2026-09-20). String, template and regular-expression literals are
 *  kept as they are (the census resolves `el("div", "fileview-md")` through its strings) and the census skips a token
 *  inside one; a comment opener inside a literal opens nothing, since the parser reads the literal (the round-5 fix,
 *  2026-09-20: before this a pattern blanked a block comment and a `//` after a space or a tab, so a `//` line starting at
 *  column 0 was read as code, 415 such lines in file-view.ts at the round-5 verifiers' read). The test runs in vscode-extension, and reads the tree as real-viewer-leg.ts does. */
const blank = (m: string): string => m.replace(/[^\n]/g, " ");
/** The comment ranges and the literal ranges of `src`, as the compiler parses them. */
function textRanges(src: string): { comments: Array<[number, number]>; literals: Array<[number, number]> } {
  const sf = ts.createSourceFile("file-view.ts", src, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
  const comments: Array<[number, number]> = [], literals: Array<[number, number]> = [];
  const seen = new Set<number>();
  const visit = (n: ts.Node): void => {
    if (n.kind >= ts.SyntaxKind.FirstJSDocNode && n.kind <= ts.SyntaxKind.LastJSDocNode) return;   // a doc comment's own tree: its range is already a comment range
    for (const r of [...(ts.getLeadingCommentRanges(src, n.getFullStart()) || []), ...(ts.getTrailingCommentRanges(src, n.getEnd()) || [])]) if (!seen.has(r.pos)) { seen.add(r.pos); comments.push([r.pos, r.end]); }
    if (ts.isStringLiteral(n) || ts.isNoSubstitutionTemplateLiteral(n) || ts.isTemplateHead(n) || ts.isTemplateMiddle(n) || ts.isTemplateTail(n) || ts.isRegularExpressionLiteral(n)) literals.push([n.getStart(sf), n.getEnd()]);
    for (const c of n.getChildren(sf)) visit(c);
  };
  visit(sf);
  const byStart = (a: [number, number], b: [number, number]): number => a[0] - b[0];
  return { comments: comments.sort(byStart), literals: literals.sort(byStart) };
}
const stripComments = (src: string): string => {
  const out: string[] = [];
  let last = 0;
  for (const [a, b] of textRanges(src).comments) { if (a < last) continue; out.push(src.slice(last, a), blank(src.slice(a, b))); last = b; }
  out.push(src.slice(last));
  return out.join("");
};
const VIEWER_RAW = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "file-view.ts"), "utf8");
const VIEWER_SRC = stripComments(VIEWER_RAW);
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
/** The scalars of the body the viewer reads: geometry, the scroll offsets, the tab order. */
const SCALARS = ["clientWidth", "clientHeight", "clientTop", "clientLeft", "scrollHeight", "scrollWidth", "offsetWidth", "offsetHeight", "offsetTop", "offsetLeft", "isConnected", ...NON_SEATING_ASSIGNS];
/** The members a bare read passes for: a scalar, and a non-seating method read as a value (`typeof body.getClientRects`). A
 *  bare read of a node member (NODE_MEMBERS) passes inside the argument list of a `body` call the census read (the reference
 *  child of `body.insertBefore(x, body.firstChild)`) and is refused anywhere else, since a node stored under another name
 *  (`const first = body.firstChild;`) could seat in the body where the census cannot follow. A bare read of any other member
 *  is refused: a seating method handed out (`const seat = body.append;`) seats later where the census cannot follow, and a
 *  member the census has not seen is read by hand and listed here, never passed (the round-4 review, 2026-09-20: before this
 *  every bare read passed). */
const READ_MEMBERS = [...SCALARS, ...NON_SEATING_CALLS];
/** The members a further access (`.`, `?.`, `[`) passes for: a scalar's own methods, and the three objects of the body that
 *  seat nothing (classList, style, dataset; `body.classList.add(...)` is the plain `.` tail the round-4 review kept passing).
 *  A further access on a member that hands out a node (NODE_MEMBERS, its own message), on a seating method (`.call`, `.bind`,
 *  `.apply`, a computed `["call"]`: the seat runs where the census cannot read its arguments) or on any other member is
 *  refused. */
const FURTHER_MEMBERS = [...SCALARS, "classList", "style", "dataset"];
/** The callees file-view.ts hands the body to bare, as an argument (`foldKeeper(body)`) or as a property of one
 *  (`installFilePrint({ body, ... })`), each READ BY HAND for what it does with the body it is handed (the round-5 fix,
 *  2026-09-20; the reason is the read). One whose own parameter is named `body` (`own`) has its member accesses read by
 *  this census like the viewer's own, and the census holds file-view.ts to declaring that parameter under that name, so a
 *  rename fails the census until the callee is read again. A callee not listed fails the census with its line: it is read
 *  by hand and listed, never passed. The census cannot derive what a listed callee does; that is the hand read's claim. */
const BODY_HANDED_TO: Array<{ callee: string; own?: true; why: string }> = [
  { callee: "foldKeeper", own: true, why: "notes and restores the folds' open state" },
  { callee: "armFigureLabels", own: true, why: "labels the gated figures inside the body" },
  { callee: "openFoldOrdinals", own: true, why: "reads which folds are open" },
  { callee: "textSize.bindWheel", own: true, why: "binds the wheel to the text size" },
  { callee: "watchBodyWidth", own: true, why: "observes the body's width (ro.observe(body) is its own use, below)" },
  { callee: "gateKeys", own: true, why: "the keyboard over a gated placeholder" },
  { callee: "scrollToFragment", why: "file-view.ts: scrolls the body to a fragment's target; reads and scrolls" },
  { callee: "sectionHidden", why: "file-view.ts: asks whether a fragment's section is hidden; reads" },
  { callee: "ringOf", why: "file-view.ts: reads whether the focus ring shows" },
  { callee: "keepPoint", why: "file-view.ts: keeps a selection point across a paint; reads" },
  { callee: "pointBack", why: "file-view.ts: finds a kept point again; reads" },
  { callee: "readPlace", why: "reader-place.ts: reads the reader's place" },
  { callee: "seatPlaceOutcome", why: "reader-place.ts: scrolls to a kept place; reads and scrolls" },
  { callee: "gateOf", why: "figure-gate.ts: finds the placeholder an event target is in; reads" },
  { callee: "delegate", why: "actions.ts: installs one click listener" },
  { callee: "ro.observe", why: "a ResizeObserver's observe" },
  { callee: "main.appendChild", why: "seats the body in its parent, not a child in the body" },
  { callee: "box.appendChild", why: "seats the body in its parent, not a child in the body" },
  { callee: "installFilePrint", why: "file-print.ts: reads the body's children and pictures, observes it; seats nothing" },
];
/** The census over `src`: the roots seated, each with the lines that seat it, and every use the census refuses, each with its
 *  line and why. Every `body` token outside a literal (the token pattern: `body` with no identifier character or `.` before
 *  it and none after) is read. One a member access follows (an optional non-null `!`, then `.`, `?.`, `[` or `?.[`, then
 *  the member name) is classed by what follows the member (the tail pattern: a call `(` or `?.(`, an assignment `=` or a
 *  compound one, a further access `.`, `?.` or `[`, or nothing, a bare read). The `?.(` alternative stands before the
 *  general `\??\.` one, so an optional call is a call and not a further access; the call and assignment branches stand
 *  before the bare-read refusal, so a direct call still parses (the round-4 review's two ordering warnings). A token no
 *  member access follows is classed by its context (bareContext), and one the census cannot class is refused with its
 *  line. */
function census(src: string, table: SeatRead[] = SEATS_READ_BY_HAND, indexTable: IndexRead[] = INDEX_READS_BY_HAND): { seated: Map<string, number[]>; refused: string[] } {
  const lineAt = (i: number): number => src.slice(0, i).split("\n").length;
  const seated = new Map<string, number[]>();
  const refused: string[] = [];
  if (!src.includes(ACTION_CTX_DECL + " {")) refused.push("the census passes the action-context accessor `body: () => body` inside the object literal declared `" + ACTION_CTX_DECL + " {`, and the source declares no such literal: read the hand-out by hand again");
  const argLists: Array<[number, number]> = [];   // the argument list of every `body` call read so far, as [open, close]: a bare node read inside one is a call's argument
  const { literals } = textRanges(src);
  const inLiteral = (i: number): boolean => literals.some(([a, b]) => i >= a && i < b);
  const tokens = [...src.matchAll(/(?<![\w$.])body(?![\w$])/g)].map((m) => m.index!).filter((i) => !inLiteral(i));
  const { openerAt, parentOf } = bracketMap(src, literals, tokens);
  for (const own of BODY_HANDED_TO) {
    if (!own.own) continue;
    const last = own.callee.split(".").pop()!;
    if (!new RegExp("(?:function " + last + "\\(|const " + last + " = \\()body(?:: |\\))").test(src)) refused.push("BODY_HANDED_TO lists " + own.callee + " as reading the body under its own parameter named body, and the source declares no such parameter: read it by hand again");
  }
  for (const at of tokens) {
    const line = lineAt(at);
    const access = /^\s*!?\s*(\?\.\s*\[|\[|\?\.|\.)\s*(\w+)?/.exec(src.slice(at + 4));
    if (!access) {
      const why = bareContext(src, at, openerAt, parentOf);
      if (why) refused.push("line " + line + ": " + why);
      continue;
    }
    const sep = access[1], member = access[2], after = at + 4 + access[0].length;
    if (sep === "[" || sep.startsWith("?.") && sep.endsWith("[")) { refused.push("line " + line + ": body" + sep.replace(/\s+/g, "") + "...] reaches a member by a computed name the census cannot read"); continue; }
    if (!member) { refused.push("line " + line + ": body" + sep + " is followed by no member name the census can read"); continue; }
    const tail = /^\s*!?\s*(\?\.\(|\(|(?:[-+*/%&|^]|\*\*|<<|>>>?|\?\?|\|\||&&)?=(?!=)|\??\.|\[|)/.exec(src.slice(after))![1];   // what follows the member (a non-null `!` skipped): a call (`?.(` read before the general `?.`), an assignment (plain or compound, not a comparison), a further access, or nothing, a read
    const use = "body" + sep + member;
    if (tail === "(" || tail === "?.(") {
      const open = src.indexOf("(", after);
      const inner = balancedAt(src, open);
      argLists.push([open, open + inner.length + 1]);
      const seats = SEATING[member];
      if (seats) {
        const args = inner.replace(/\s+/g, " ").trim();
        for (const arg of seats(args ? splitTop(args, ",") : [])) {
          let roots: string[];
          try { roots = rootsOf(src, arg, at); } catch (e) { refused.push("line " + line + ": " + use + "(...) seats `" + arg + "`, an expression the census cannot resolve to a root (" + (e as Error).message + "): a spread, a call it does not know, a variable assigned where it cannot read"); continue; }   // the round-6 review's census-4: before this the resolver threw, naming the expression and not its line
          for (const root of roots) seated.set(root, [...(seated.get(root) || []), line]);
        }
      } else if (!NON_SEATING_CALLS.includes(member)) refused.push("line " + line + ": " + use + "(...) is a call the census does not know");
    } else if (tail.endsWith("=")) {
      if (!NON_SEATING_ASSIGNS.includes(member)) refused.push("line " + line + ": " + use + " " + tail + " ... is an assignment the census does not know (innerHTML and its kin seat what no resolver reads)");
    } else if (tail === "." || tail === "?." || tail === "[") {
      if (NODE_MEMBERS.includes(member)) refused.push("line " + line + ": " + use + " hands out a node and a further access on it could seat where the census cannot follow");
      else if (SEATING[member]) refused.push("line " + line + ": " + use + tail + "... reaches the seating method through a further access (call, bind, apply, a computed name), which seats where the census cannot read the arguments");
      else if (!FURTHER_MEMBERS.includes(member)) refused.push("line " + line + ": " + use + tail + "... is a further access on a member the census does not know");
    } else if (NODE_MEMBERS.includes(member)) {
      // the innermost bracket open around the token must be the body call's own argument list: a read inside a nested call's
      // list or a callback's braces within it is stored or handed on where the census cannot follow (the round-5 review's tests-1)
      if (!argLists.some(([open, close]) => at > open && at < close && openerAt.get(at) === open)) refused.push("line " + line + ": " + use + " is read bare outside a body call's arguments (or inside a nested call's or a callback's within them), and a node stored under another name could seat in the body where the census cannot follow");
    } else if (!READ_MEMBERS.includes(member)) refused.push("line " + line + ": " + use + " is read bare, and a member the census does not know as a scalar or a non-seating method, handed out, could seat where the census cannot follow");
  }
  // the second read: every seat and every member call in the file, on any receiver; the sanctioned `body` token's were
  // read above; a seat or a site-read call passes only as a site the table lists, held to one binding per entry, a method
  // passes only by a name read by hand, a stored index read only as a site listed, and everything else fails with its line
  const second = seatSites(src);
  const used = new Set<SeatRead>();
  const bindings = new Map<SeatRead, Map<number, number>>();   // per entry, the binding positions its sites resolve to, each with a line
  for (const s of second.sites) {
    if (s.body) continue;
    const entry = table.find((e) => e.in === s.fn && e.on === s.on && e.via === s.via);
    if (!entry) {
      if (SEAT_CALLS.includes(s.via) || s.via.endsWith(" =")) refused.push("line " + s.line + ": " + s.text + " seats on `" + s.on + "` in " + s.fn + ", a receiver the census has not read by hand: read the site for what " + s.on + " is (the body under another name, or a node whose seat lands as a child of the body, seats a root the lists must know) and list it in SEATS_READ_BY_HAND, or seat the body by its name");
      else refused.push("line " + s.line + ": " + s.text + " calls " + s.via + " on `" + s.on + "` in " + s.fn + ", a call the census reads by its site (a call, apply or bind, a mount or render, a reflection global's method) and has not read by hand: read it for what it runs and list it in SEATS_READ_BY_HAND");
      continue;
    }
    used.add(entry);
    if (s.decl === undefined) continue;   // a member chain (`document.body`) has no binding; its spelling is the read
    if (s.decl !== entry.decl) refused.push("line " + s.line + ": " + s.text + " seats on `" + s.on + "` in " + s.fn + ", bound to `" + s.decl + "`, where SEATS_READ_BY_HAND read `" + (entry.decl ?? "no binding") + "`: the receiver is not the one read by hand");
    const seen = bindings.get(entry) ?? new Map<number, number>(); seen.set(s.bindingAt!, s.line); bindings.set(entry, seen);
  }
  for (const [e, seen] of bindings) if (seen.size > 1) refused.push("SEATS_READ_BY_HAND's entry `" + e.on + "." + e.via.replace(" =", " = ...") + "` in " + e.in + " covers seats on " + seen.size + " bindings of " + e.on + " (lines " + [...seen.values()].join(", ") + "): one entry reads one receiver");
  for (const c of second.computed) refused.push("line " + c.line + ": " + c.text + " calls through a computed name the census cannot read, and a seating method called that way seats where the census cannot follow");
  for (const u of second.unknown) refused.push("line " + u.line + ": " + u.text + " calls " + u.name + " on `" + u.on + "`, a method the census does not list as seating or as seating nothing: read it by hand and list it (SEAT_CALLS, SITE_CALLS or NON_SEATING_METHODS)");
  for (const h of second.handedOut) refused.push("line " + h.line + ": " + h.text + " reads the method " + h.name + " without calling it (a bare read, a call, bind or apply on it, an argument), and it runs later where the census cannot read its receiver");
  for (const o of second.oddCallee) refused.push("line " + o.line + ": " + o.text + " calls neither a name nor a member (a parenthesised expression, a call's value, an arrow), which the census cannot read");
  for (const i of second.indexReads) if (!indexTable.some((e) => e.in === i.fn && e.on === i.on)) refused.push("line " + i.line + ": " + i.text + " reads a member of `" + i.on + "` by a computed name and stores or hands it on, in " + i.fn + ": read the site for what " + i.on + " is and list it in INDEX_READS_BY_HAND, or read the member by its name");
  for (const e of table) if (!used.has(e)) refused.push("SEATS_READ_BY_HAND lists `" + e.on + "." + e.via.replace(" =", " = ...") + "` in " + e.in + ", and the source has no such seat: the entry is stale, remove it or read the site again");
  for (const e of indexTable) if (!second.indexReads.some((i) => i.fn === e.in && i.on === e.on)) refused.push("INDEX_READS_BY_HAND lists `" + e.on + "` in " + e.in + ", and the source has no such stored index read: the entry is stale, remove it or read the site again");
  return { seated, refused };
}
/** The seating forms the census reads on ANY receiver, by the compiler's tree (seatSites): a call of a method that seats a node
 *  (SEAT_CALLS: the six SEATING resolves on the body; replaceWith, after, before, replaceChild and insertAdjacentHTML, which
 *  seat through the receiver's parent or replace the receiver's children; insertNode and surroundContents, which seat at a
 *  range; setHTMLUnsafe, which parses HTML in place; moveBefore, which moves a node in; write and writeln, which write the
 *  document) and an assignment (plain or compound) to a member that parses HTML into element children (SEAT_ASSIGNS:
 *  innerHTML and outerHTML, the two such properties an element has). textContent is not a seat: it makes a text node and
 *  no element child. */
const SEAT_CALLS = [...Object.keys(SEATING), "replaceWith", "after", "before", "replaceChild", "insertAdjacentHTML", "insertNode", "surroundContents", "setHTMLUnsafe", "moveBefore", "write", "writeln"];
const SEAT_ASSIGNS = ["innerHTML", "outerHTML"];
/** The calls the census reads BY THEIR SITE like a seat, through SEATS_READ_BY_HAND (the round-6 review's census-1,
 *  2026-09-20): a method named call, apply or bind runs a method where the census cannot read its receiver or its
 *  arguments (Function.prototype's and Reflect.apply), one named mount or render seats inside the element it is handed (the
 *  editor chunk's mount, the PDF chunk's render), and any method of the reflection globals (SITE_RECEIVERS: Object.assign
 *  can set innerHTML, Reflect.set and Reflect.get reach any member by a string, Function.prototype's methods run any
 *  function) can seat where no name says so. Each live site is read by hand for what it calls and listed; one not listed
 *  fails the census with its line. */
const SITE_CALLS = ["call", "apply", "bind", "mount", "render"];
const SITE_RECEIVERS = ["Object", "Reflect", "Function"];
/** Every other method name file-view.ts calls, on any receiver, each read by hand as seating no element (the round-6
 *  review's census-1, 2026-09-20: before this the second read knew a closed list of seating names and passed every other
 *  method unread, so a seat by a name it did not list, a range's insertNode or an element's moveBefore, passed). A method the
 *  file calls by a name not here fails the census with its line until it is read and listed, whatever its receiver; what a
 *  listed method does is the hand read's claim, by name: the DOM's reads, attribute writes, removals, events, focus,
 *  geometry, scrolling, classes and styles, a range's bounds and a tree walker's steps (a range's insertNode and
 *  surroundContents are seats, SEAT_CALLS); the language's strings, arrays, maps, sets, promises, numbers and JSON; the
 *  browser's fetch and its bodies, storage, the clipboard, windows and blobs; and the viewer's own objects (the text-size
 *  control, the folds, the edit hooks, the tracked edit, the gate clock, the hold, the action seam, the highlighter, marked,
 *  the PDF and editor handles), whose seats, where they have any, are calls in this file that this census reads or stand in a
 *  module handed nothing of the body. The body token's own calls are the first read's (NON_SEATING_CALLS, a shorter list). */
const NON_SEATING_METHODS = [
  // the DOM
  ...NON_SEATING_CALLS, "setAttribute", "getAttribute", "hasAttribute", "removeAttribute", "getAttributeNS", "removeAttributeNS", "remove", "closest", "matches", "getElementById", "createElement", "scrollIntoView", "stopPropagation", "preventDefault", "click", "hasFocus", "toggle", "setProperty", "createRange", "setStart", "setEnd", "createTreeWalker", "nextNode", "getSelection", "setBaseAndExtent", "observe", "disconnect",
  // the language
  "push", "pop", "shift", "slice", "map", "filter", "forEach", "some", "every", "find", "join", "from", "includes", "indexOf", "lastIndexOf", "startsWith", "split", "replace", "trim", "toLowerCase", "toUpperCase", "toString", "repeat", "match", "test", "exec", "get", "set", "has", "add", "then", "catch", "finally", "all", "resolve", "reject", "max", "min", "floor", "abs", "sign", "isInteger", "now", "parse", "stringify",
  // the browser: fetch and its bodies, storage, the clipboard, windows, blobs, messages
  "text", "json", "blob", "arrayBuffer", "getItem", "setItem", "removeItem", "writeText", "abort", "open", "confirm", "postMessage", "createObjectURL", "revokeObjectURL",
  // the viewer's own objects and the modules it calls
  "mode", "onClose", "failed", "saved", "close", "dispose", "destroy", "value", "begin", "save", "routesSave", "suggestions", "decisions", "learnAll", "stamp", "timed", "defer", "held", "ask", "note", "restore", "sync", "bindWheel", "scrollToOffset", "highlight", "getLanguage", "registerLanguage", "lexer", "parser", "walkTokens",
];
/** One seat in the viewer's source: its line, the nearest named function around it (`fn`: a declaration's, a variable's or a
 *  property's arrow or function expression, a method; `<module>` at the top level), the receiver as spelled with a non-null
 *  `!` dropped and its whitespace collapsed to single spaces (`on`), the form (`via`: the method's name, or `<member> =` for
 *  an assignment), the call or assignment's text, whether the receiver is the sanctioned `body` token (the identifier alone;
 *  `(body)` and a cast are not it), and, for a receiver that is a bare identifier, its BINDING (the round-6 review's
 *  census-2, 2026-09-20): the declaration the name resolves to by the language's scopes (`decl`: the declaration as
 *  written, `const main = el("div", "fileview-main")`, a loop's `const a of fileViewActions`; "a parameter of <function>",
 *  or of "the callback handed to <call>" for an unnamed callback's, since what fills it is that call's; "a global" for a
 *  name the file never declares) and where it stands (`bindingAt`), so
 *  the table's entry, keyed on the receiver's spelling, is held to ONE binding and a second declaration of the same name
 *  inside the entry's function (a block's `const main = md.parentElement!`, a callback's `(main) =>`) is refused rather
 *  than read under the entry's claim. */
type SeatSite = { line: number; fn: string; on: string; via: string; text: string; body: boolean; decl?: string; bindingAt?: number };
/** A use of a member the census reads only by its site or refuses: its line and text. */
type Use = { line: number; text: string };
/** Every seat in `src` on any receiver, and every other form the second read classes (the round-6 review's census-1: the
 *  form axis is an allowlist too). Every CALL of a member (`x.m(...)`, `x?.m(...)`, `x["m"](...)`) is classed by the member's
 *  NAME: a seating name (SEAT_CALLS) or a site-read one (SITE_CALLS, or any method of a SITE_RECEIVERS global) is a site,
 *  passed only through the table; a name NON_SEATING_METHODS lists passes; any other name is `unknown` and refused. A
 *  seating or site-read name READ WITHOUT BEING CALLED (`md.append.call(...)`, `Reflect.apply(md.append, ...)`, `const f =
 *  md.append`, `Element.prototype.append`) is `handedOut` and refused: the method runs later where the census cannot read
 *  its receiver. A call through a computed name (`x[m](...)`) is `computed` and refused; a call whose callee is neither a
 *  name nor a member (a parenthesised expression, a call's value, an arrow) is `oddCallee` and refused. A member read by a
 *  computed name and NOT called (`x[k]`) is an index read: it passes where its value is only compared, tested or read
 *  further (an operand, a condition, a `.member` on it, which this read classes in turn), and where it is stored or handed
 *  on (a declaration, an assignment, an argument, a return, an array or object literal, a branch's value) it is an
 *  `indexRead` passed only as a site INDEX_READS_BY_HAND lists, since `const f = md[m]; f(x)` seats where no name says so.
 *  The tree is the compiler's, so a receiver of any shape (a query result, a parentElement chain, a variable, a call's
 *  value) is one text the table can hold or refuse. */
function seatSites(src: string): { sites: SeatSite[]; computed: Use[]; unknown: Array<Use & { name: string; on: string }>; handedOut: Array<Use & { name: string }>; oddCallee: Use[]; indexReads: Array<Use & { fn: string; on: string }> } {
  const sf = ts.createSourceFile("file-view.ts", src, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
  const lineOf = (n: ts.Node): number => sf.getLineAndCharacterOfPosition(n.getStart(sf)).line + 1;
  const flat = (s: string): string => s.replace(/\s+/g, " ");
  const nameOfFn = (f: ts.Node): string | null => {
    if (ts.isFunctionDeclaration(f) && f.name) return f.name.text;
    if ((ts.isArrowFunction(f) || ts.isFunctionExpression(f)) && (ts.isVariableDeclaration(f.parent) || ts.isPropertyAssignment(f.parent)) && ts.isIdentifier(f.parent.name)) return f.parent.name.text;
    if (ts.isMethodDeclaration(f) && ts.isIdentifier(f.name)) return f.name.text;
    return null;
  };
  const fnOf = (n: ts.Node): string => {
    for (let p: ts.Node | undefined = n.parent; p; p = p.parent) { const name = nameOfFn(p); if (name) return name; }
    return "<module>";
  };
  const text = (n: ts.Node): string => flat(n.getText(sf)).slice(0, 100);
  const strip = (e: ts.Expression): ts.Expression => { let r = e; while (ts.isNonNullExpression(r)) r = r.expression; return r; };
  const isBodyToken = (e: ts.Expression): boolean => { const r = strip(e); return ts.isIdentifier(r) && r.text === "body"; };
  /** The member name an access spells: `x.m` and `x["m"]` name m; `x[k]` names nothing. */
  const memberName = (e: ts.Expression): string | null => ts.isPropertyAccessExpression(e) ? e.name.text : ts.isElementAccessExpression(e) && ts.isStringLiteral(e.argumentExpression) ? e.argumentExpression.text : null;
  const memberObject = (e: ts.Expression): ts.Expression => (e as ts.PropertyAccessExpression | ts.ElementAccessExpression).expression;
  const isSite = (name: string, obj: ts.Expression): boolean => SEAT_CALLS.includes(name) || SITE_CALLS.includes(name) || (ts.isIdentifier(strip(obj)) && SITE_RECEIVERS.includes((strip(obj) as ts.Identifier).text));
  /** A member access the FIRST read owns: `body.<seating method>` (its further access and its bare read are refused there). */
  const ownedByFirstRead = (e: ts.Expression): boolean => { const name = memberName(e); return name !== null && SEAT_CALLS.includes(name) && isBodyToken(memberObject(e)); };
  // the binding of an identifier: the innermost enclosing scope that declares the name (a block, a function's parameters, a
  // for or catch clause, the module), by the language's rule; `var` is read as block-scoped (file-view.ts declares none)
  const isScope = (n: ts.Node): boolean => ts.isSourceFile(n) || ts.isBlock(n) || ts.isFunctionLike(n) || ts.isForStatement(n) || ts.isForInStatement(n) || ts.isForOfStatement(n) || ts.isCatchClause(n) || ts.isCaseBlock(n);
  const declares = (n: ts.Node, name: string): boolean => (ts.isVariableDeclaration(n) || ts.isParameter(n) || ts.isBindingElement(n) || ts.isFunctionDeclaration(n) || ts.isClassDeclaration(n) || ts.isImportSpecifier(n) || ts.isImportClause(n)) && !!n.name && ts.isIdentifier(n.name) && n.name.text === name;
  const ownDecls = (scope: ts.Node, name: string): ts.Node[] => {   // the declarations of `name` this scope owns: a nested scope's are its own, but a nested function's or class's NAME is declared here
    const out: ts.Node[] = [];
    const visit = (n: ts.Node): void => { if (declares(n, name)) out.push(n); if (n !== scope && isScope(n)) return; ts.forEachChild(n, visit); };
    visit(scope);
    return out;
  };
  const describe = (d: ts.Node): string => {
    if (ts.isParameter(d)) {
      const f = d.parent, name = nameOfFn(f);
      if (name) return "a parameter of " + name;
      const handedTo = ts.isCallExpression(f.parent) ? flat(f.parent.expression.getText(sf)).slice(0, 80) : null;   // an unnamed callback: the call it is handed to says what fills the parameter
      return handedTo ? "a parameter of the callback handed to " + handedTo : "a parameter of an unnamed function at line " + lineOf(f);
    }
    if (ts.isVariableDeclaration(d)) {
      const list = d.parent as ts.VariableDeclarationList, kind = list.flags & ts.NodeFlags.Const ? "const" : list.flags & ts.NodeFlags.Let ? "let" : "var";
      const loop = ts.isForOfStatement(list.parent) ? " of " + flat(list.parent.expression.getText(sf)).slice(0, 80) : ts.isForInStatement(list.parent) ? " in " + flat(list.parent.expression.getText(sf)).slice(0, 80) : "";
      return kind + " " + flat(d.name.getText(sf)) + (d.initializer ? " = " + flat(d.initializer.getText(sf)).slice(0, 80) : loop);
    }
    if (ts.isBindingElement(d)) { let p: ts.Node = d; while (p && !ts.isVariableDeclaration(p) && !ts.isParameter(p)) p = p.parent; return "a destructured binding of " + (p ? describe(p) : "an unknown declaration"); }
    if (ts.isFunctionDeclaration(d)) return "function " + d.name!.text;
    if (ts.isImportSpecifier(d) || ts.isImportClause(d)) return "an import";
    return "a " + ts.SyntaxKind[d.kind];
  };
  const bindingOf = (id: ts.Identifier): { decl: string; bindingAt: number } => {
    for (let s: ts.Node | undefined = id.parent; s; s = s.parent) {
      if (!isScope(s)) continue;
      const ds = ownDecls(s, id.text);
      if (ds.length === 1) return { decl: describe(ds[0]), bindingAt: ds[0].getStart(sf) };
      if (ds.length > 1) return { decl: "declared " + ds.length + " times in one scope (lines " + ds.map(lineOf).join(", ") + ")", bindingAt: ds[0].getStart(sf) };
    }
    return { decl: "a global", bindingAt: -1 };
  };
  const sites: SeatSite[] = [], computed: Use[] = [], unknown: Array<Use & { name: string; on: string }> = [], handedOut: Array<Use & { name: string }> = [], oddCallee: Use[] = [], indexReads: Array<Use & { fn: string; on: string }> = [];
  const site = (n: ts.Node, recv: ts.Expression, via: string): void => {
    const r = strip(recv);
    const s: SeatSite = { line: lineOf(n), fn: fnOf(n), on: flat(r.getText(sf)), via, text: text(n), body: ts.isIdentifier(r) && r.text === "body" };
    if (ts.isIdentifier(r) && !s.body) Object.assign(s, bindingOf(r));
    sites.push(s);
  };
  const isCallee = (n: ts.Node): boolean => ts.isCallExpression(n.parent) && n.parent.expression === n;
  /** The node whose value an expression's value is: a cast, a non-null `!` or parentheses around it read through. */
  const effectiveParent = (n: ts.Node): ts.Node => { let p = n.parent; while (ts.isAsExpression(p) || ts.isNonNullExpression(p) || ts.isParenthesizedExpression(p) || ts.isSatisfiesExpression(p)) p = p.parent; return p; };
  const onlyRead = (n: ts.Node): boolean => {   // the value is compared, tested or read further, never stored or handed on
    const p = effectiveParent(n);
    if (ts.isPropertyAccessExpression(p) || ts.isElementAccessExpression(p) && p.argumentExpression === n || ts.isPrefixUnaryExpression(p) || ts.isPostfixUnaryExpression(p) || ts.isTypeOfExpression(p) || ts.isTemplateSpan(p) || ts.isExpressionStatement(p) || ts.isIfStatement(p) || ts.isWhileStatement(p) || ts.isDoStatement(p) || ts.isDeleteExpression(p) || ts.isVoidExpression(p)) return true;
    if (ts.isBinaryExpression(p)) return !(p.operatorToken.kind >= ts.SyntaxKind.FirstAssignment && p.operatorToken.kind <= ts.SyntaxKind.LastAssignment) || p.left === n;
    if (ts.isConditionalExpression(p)) return p.condition === n;
    if (ts.isForStatement(p)) return p.condition === n || p.incrementor === n;
    return false;
  };
  const visit = (n: ts.Node): void => {
    if (ts.isCallExpression(n)) {
      const c = n.expression;
      const name = memberName(c);
      if (ts.isPropertyAccessExpression(c) || ts.isElementAccessExpression(c) && name !== null) {
        const obj = memberObject(c);
        if (ts.isElementAccessExpression(c)) computed.push({ line: lineOf(n), text: text(n) });
        else if (isSite(name!, obj)) { if (!(SITE_CALLS.includes(name!) && ownedByFirstRead(obj))) site(n, obj, name!); }   // `body.append.call(...)` is the first read's refusal
        else if (!NON_SEATING_METHODS.includes(name!) && !isBodyToken(obj)) unknown.push({ line: lineOf(n), text: text(n), name: name!, on: flat(strip(obj).getText(sf)) });
      } else if (ts.isElementAccessExpression(c)) computed.push({ line: lineOf(n), text: text(n) });
      else if (!ts.isIdentifier(c) && c.kind !== ts.SyntaxKind.SuperKeyword && c.kind !== ts.SyntaxKind.ImportKeyword) oddCallee.push({ line: lineOf(n), text: text(n) });
    } else if (ts.isBinaryExpression(n) && n.operatorToken.kind >= ts.SyntaxKind.FirstAssignment && n.operatorToken.kind <= ts.SyntaxKind.LastAssignment && (ts.isPropertyAccessExpression(n.left) || ts.isElementAccessExpression(n.left)) && memberName(n.left) !== null && SEAT_ASSIGNS.includes(memberName(n.left)!)) site(n, memberObject(n.left), memberName(n.left) + " =");
    if ((ts.isPropertyAccessExpression(n) || ts.isElementAccessExpression(n)) && !isCallee(n)) {
      const name = memberName(n);
      if (name !== null) { if ((SEAT_CALLS.includes(name) || SITE_CALLS.includes(name)) && !ownedByFirstRead(n) && !isBodyToken(memberObject(n))) handedOut.push({ line: lineOf(n), text: text(effectiveParent(n)), name }); }
      else if (ts.isElementAccessExpression(n) && !ts.isNumericLiteral(n.argumentExpression) && !onlyRead(n)) indexReads.push({ line: lineOf(n), text: text(effectiveParent(n)), fn: fnOf(n), on: flat(strip(n.expression).getText(sf)) });
    }
    ts.forEachChild(n, visit);
  };
  visit(sf);
  return { sites, computed, unknown, handedOut, oddCallee, indexReads };
}
/** A seat in file-view.ts on a receiver other than the `body` token, READ BY HAND and listed by its site: the nearest named
 *  function around it (`in`), the receiver's spelling (`on`) and the form (`via`), with what the receiver is (`is`), which is
 *  the hand read's claim: that a seat on it lands no child in the body. A seat the table does not list fails the census with
 *  its line, whatever produced the receiver, and an entry the source has no seat for fails it too, so the table is the live
 *  set of sites and nothing more (the round-5 review, 2026-09-20: before this the census refused a closed list of dangerous
 *  forms and passed every other seat unread). A body root's own children (a hint inside the failure pane, the glyph inside
 *  a loader) are seats inside the root, not beside it, and are listed as such. */
type SeatRead = { in: string; on: string; via: string; is: string; decl?: string };
const SEATS_READ_BY_HAND: SeatRead[] = [
  // the zoom control (textSizeControl builds it; the bar seats its span through textSize.wrap, an argument the body's read never sees)
  { in: "textSizeControl", on: "trigger", via: "innerHTML =", is: "the zoom button, built here by el(); its glyph goes inside it", decl: "const trigger = el(\"button\", \"fileview-btn fileview-icon fileview-zoom-btn\") as HTMLButtonElemen" },
  { in: "textSizeControl", on: "menu", via: "appendChild", is: "the zoom flyout, built here by el(); its step buttons go inside it", decl: "const menu = el(\"div\", \"fileview-zoom-menu\")" },
  { in: "textSizeControl", on: "wrap", via: "appendChild", is: "the control's own span, built here by el() and seated in the bar's actions by the viewers (viewGroup, acts); the button and the flyout go inside it", decl: "const wrap = el(\"span\", \"fileview-zoom\")" },
  // the URL viewer's loader (a body root: body.appendChild(loaderEl()) is resolved by the body's read through the builder's return)
  { in: "loaderEl", on: "load", via: "innerHTML =", is: "the loader this builder returns, div.fileview-load; its glyph goes inside it", decl: "const load = el(\"div\", \"fileview-load\")" },
  // the GitHub-link action (githubLinkAction.mount, whose apply hook fills the span; the viewer seats the span in the bar's file group)
  { in: "apply", on: "unit", via: "replaceChildren", is: "the action's own span (div.fileview-gh), built in its mount and returned to the viewer, which seats it in the bar; the link goes inside it", decl: "const unit = el(\"span\", \"fileview-gh\")" },
  // the local viewer's card (openFileView): the bar, its groups and buttons, the card, its wrapper, and the page's body they land in
  { in: "openFileView", on: "bar", via: "appendChild", is: "the title bar, a child of the card beside main; the back button, the name, the session tag and the actions go in it", decl: "const bar = el(\"div\", \"fileview-bar\")" },
  { in: "openFileView", on: "name", via: "appendChild", is: "the file name in the bar; its directory and base spans go in it", decl: "const name = el(\"div\", \"fileview-name\")" },
  { in: "openFileView", on: "sess", via: "replaceChildren", is: "the session tag in the bar (sess = el(\"span\", \"fileview-sess\")); the host and name nodes go in it", decl: "let sess = null" },
  { in: "openFileView", on: "seg", via: "appendChild", is: "the Rendered|Raw pair in the view group; its two buttons go in it", decl: "const seg = el(\"span\", \"fileview-seg\")" },
  { in: "openFileView", on: "viewGroup", via: "appendChild", is: "the view group of the actions row; the pair, the outline button, the zoom control and the source button go in it", decl: "const viewGroup = el(\"span\", \"fileview-group fileview-group-view\")" },
  { in: "openFileView", on: "editBtn", via: "innerHTML =", is: "the Edit button in the file group; its glyph goes inside it", decl: "const editBtn = el(\"button\", \"fileview-btn\") as HTMLButtonElement" },
  { in: "openFileView", on: "fileGroup", via: "appendChild", is: "the file group of the actions row; the edit, save and cancel buttons, an action's mount, download, Print and copy go in it", decl: "const fileGroup = el(\"span\", \"fileview-group fileview-group-file\")" },
  { in: "openFileView", on: "load", via: "innerHTML =", is: "the open's loader (a body root: body.appendChild(load) is resolved by the body's read); its glyph goes inside it", decl: "const load = el(\"div\", \"fileview-load\")" },
  { in: "openFileView", on: "main", via: "appendChild", is: "the card's main column, the body's PARENT: the body itself is seated in it (main.appendChild(body)), so this seat is the body's, not a child in it", decl: "const main = el(\"div\", \"fileview-main\")" },
  { in: "aside", on: "main", via: "appendChild", is: "the same column, through the seam's aside hook: an action's aside is seated beside the body, in main, not in the body", decl: "const main = el(\"div\", \"fileview-main\")" },
  { in: "openFileView", on: "dl", via: "innerHTML =", is: "the Download button in the file group; its glyph goes inside it", decl: "const dl = el(\"button\", \"fileview-btn\") as HTMLButtonElement" },
  { in: "openFileView", on: "copy", via: "innerHTML =", is: "the Copy button in the file group; its glyph goes inside it", decl: "const copy = el(\"button\", \"fileview-btn fileview-icon\") as HTMLButtonElement" },
  { in: "copySay", on: "copy", via: "innerHTML =", is: "the same Copy button; the acknowledgement swaps its glyph", decl: "const copy = el(\"button\", \"fileview-btn fileview-icon\") as HTMLButtonElement" },
  { in: "openFileView", on: "acts", via: "appendChild", is: "the actions row in the bar; the two groups and the close button go in it", decl: "const acts = el(\"div\", \"fileview-acts\")" },
  { in: "openFileView", on: "box", via: "appendChild", is: "the card (div.fileview); the bar and main go in it", decl: "const box = el(\"div\", \"fileview\")" },
  { in: "openFileView", on: "wrap", via: "appendChild", is: "the overlay wrapper; the card goes in it", decl: "const wrap = el(\"div\")" },
  { in: "openFileView", on: "document.body", via: "appendChild", is: "the page's body, not the viewer's; the overlay wrapper goes in it" },
  { in: "openOutline", on: "pop", via: "appendChild", is: "the headings popover, built here by el(); its rows go in it", decl: "const pop = el(\"div\", \"fileview-outline\")" },
  { in: "openOutline", on: "box", via: "appendChild", is: "the card; the popover goes in it, beside the bar and main", decl: "const box = el(\"div\", \"fileview\")" },
  { in: "noteBar", on: "box", via: "insertBefore", is: "the card; a notice bar (div.fileview-err) goes in it above main, outside the body (a body root of the same class is seated by the body's own replaceChildren, read separately)", decl: "const box = el(\"div\", \"fileview\")" },
  { in: "showSaveError", on: "bar2", via: "appendChild", is: "noteBar's notice bar in the card; its retry button goes in it", decl: "const bar2 = noteBar(err)" },
  { in: "raiseDiskBar", on: "bar2", via: "appendChild", is: "noteBar's notice bar in the card; its reload button goes in it", decl: "const bar2 = noteBar(words)" },
  // failure panes (each a body root: body.replaceChildren(why) is resolved by the body's read); their hint and offer go inside them
  { in: "imgFailed", on: "why", via: "appendChild", is: "the picture failure pane (div.fileview-err), a body root; its hint and offer go inside it", decl: "const why = el(\"div\", \"fileview-err\")" },
  { in: "fetchFile", on: "why", via: "appendChild", is: "the fetch failure pane (div.fileview-err), a body root; its hint and offer go inside it", decl: "const why = el(\"div\", \"fileview-err\")" },
  { in: "fail", on: "why", via: "appendChild", is: "the URL viewer's failure pane (div.fileview-err), a body root; its hint and link go inside it", decl: "const why = el(\"div\", \"fileview-err\")" },
  // the page's head: the editor and PDF chunks load as script tags
  { in: "editorChunk", on: "document.head", via: "appendChild", is: "the page's head; the editor chunk's script tag goes in it" },
  { in: "pdfChunkLoad", on: "document.head", via: "appendChild", is: "the page's head; the PDF chunk's script tag goes in it" },
  // the PDF pages flow (showPdfPages and its fallback): the kept frame's column, a fresh column, the pages loader
  { in: "showPdfPages", on: "col", via: "prepend", is: "the kept frame's parent (col = kept ? kept.parentElement : null; shownFrame finds the frame the body holds, and pdfBlock seats its frame inside its div.fileview-pdffall column and nowhere else), so the column, a body root; the pages loader goes inside it", decl: "const col = kept ? kept.parentElement : null" },
  { in: "fallback", on: "col", via: "prepend", is: "the same column; the notice goes inside it", decl: "const col = kept ? kept.parentElement : null" },
  { in: "fallback", on: "fall", via: "prepend", is: "a fresh pdfBlock column (a body root: body.replaceChildren(fall) is resolved by the body's read); the notice goes inside it", decl: "const fall = pdfBlock(url, path)" },
  { in: "showPdfPages", on: "wait", via: "innerHTML =", is: "the pages loader (div.fileview-load: a body root through body.replaceChildren(wait, host), or inside the column through col.prepend(wait)); its glyph goes inside it", decl: "const wait = el(\"div\", \"fileview-load\")" },
  { in: "enterEdit", on: "wait", via: "innerHTML =", is: "the chunk loader (div.fileview-load, a body root: body.replaceChildren(wait) is resolved by the body's read); its glyph goes inside it", decl: "const wait = el(\"div\", \"fileview-load\")" },
  // the URL viewer's card (openUrlView): the bar, its actions, the card (the body's parent there), its wrapper, the page's body
  { in: "openUrlView", on: "name", via: "appendChild", is: "the file name in the URL viewer's bar; its directory and base spans go in it", decl: "const name = el(\"div\", \"fileview-name\")" },
  { in: "openUrlView", on: "acts", via: "appendChild", is: "the URL viewer's actions row in the bar; its buttons, the zoom control, the link and the close button go in it", decl: "const acts = el(\"div\", \"fileview-acts\")" },
  { in: "openUrlView", on: "acts", via: "insertBefore", is: "the same actions row; the Print button goes in it before Copy", decl: "const acts = el(\"div\", \"fileview-acts\")" },
  { in: "openUrlView", on: "bar", via: "appendChild", is: "the URL viewer's title bar, a child of the card beside the body; the name and the actions go in it", decl: "const bar = el(\"div\", \"fileview-bar\")" },
  { in: "openUrlView", on: "box", via: "appendChild", is: "the URL viewer's card (div.fileview), the body's PARENT there: the bar and the body itself are seated in it (box.appendChild(body)), so this seat is the body's, not a child in it", decl: "const box = el(\"div\", \"fileview\")" },
  { in: "openUrlView", on: "wrap", via: "appendChild", is: "the overlay wrapper; the card goes in it", decl: "const wrap = el(\"div\")" },
  { in: "openUrlView", on: "document.body", via: "appendChild", is: "the page's body, not the viewer's; the overlay wrapper goes in it" },
  { in: "startDownload", on: "document.body", via: "appendChild", is: "the page's body; a temporary anchor for the download click goes in it and is removed" },
  // the builders of the body's roots seat INSIDE the root they return (each root is resolved by the body's read where the viewer seats it)
  { in: "codeBlock", on: "code", via: "innerHTML =", is: "the code element inside the code root's pre; the highlighted HTML goes in it", decl: "const code = el(\"code\", \"hljs\")" },
  { in: "codeBlock", on: "pre", via: "appendChild", is: "the pre inside the code root; the code element goes in it", decl: "const pre = el(\"pre\", \"fileview-pre\")" },
  { in: "codeBlock", on: "wrap", via: "appendChild", is: "the code root itself (div.fileview-code), which this builder returns; the gutter and the pre go inside it", decl: "const wrap = el(\"div\", \"fileview-code\")" },
  { in: "mdBlock", on: "box", via: "replaceChildren", is: "the markdown root itself (div.fileview-md), which this builder returns; the sanitized document goes inside it", decl: "const box = el(\"div\", \"fileview-md\")" },
  { in: "mdBlock", on: "codeEl", via: "innerHTML =", is: "a code element of the sanitized document inside the markdown root; the highlighted HTML goes in it", decl: "const codeEl = node as HTMLElement" },
  { in: "imgBlock", on: "box", via: "appendChild", is: "the picture root itself (div.fileview-imgbox), which this builder returns; the img goes inside it", decl: "const box = el(\"div\", \"fileview-imgbox\")" },
  { in: "pdfBlock", on: "col", via: "appendChild", is: "the PDF column itself (div.fileview-pdffall), which this builder returns; the frame goes inside it", decl: "const col = el(\"div\", \"fileview-pdffall\")" },
  // the figure labels (armFigureLabels's onError): a label beside a failed figure's anchor
  { in: "onError", on: "parent", via: "insertBefore", is: "the parent of a failed figure's anchor (parent = anchor.parentNode): figureOf takes an img inside .fileview-md alone and figureAnchor climbs wrappers around that img, so the parent is inside the markdown root or is the root itself, never the body; the label goes beside the anchor", decl: "const parent = anchor.parentNode" },
  // the calls the census reads by their site (SITE_CALLS, SITE_RECEIVERS; the round-6 review's census-1): reflection and module hand-offs, each read by hand for what it calls
  { in: "<module>", on: "Object", via: "entries", is: "Object.entries over the highlighter's language table at module load, a literal record of grammars; each is registered with hljs; no element is touched", decl: "a global" },
  { in: "fetchFile", on: "Object", via: "assign", is: "Object.assign onto a fresh Error, setting its status for the failure road; the target is the Error, never an element", decl: "a global" },
  { in: "mdBlock", on: "base", via: "call", is: "marked's default walkTokens, called with marked as this over each token (base = marked.defaults.walkTokens): it walks the token tree and seats nothing", decl: "const base = marked.defaults.walkTokens" },
  { in: "initFileView", on: "h", via: "apply", is: "the git-link hooks' apply, told the URL and the reason the kernel answered (h = gitHooks); an object's method, not Function.prototype.apply", decl: "const h = gitHooks" },
  { in: "openFileView", on: "a", via: "mount", is: "a registered action's mount (the GitHub link, the Comments panel), which returns the element the viewer then seats in the file group (fileGroup.appendChild, listed above); the mount seats nothing itself", decl: "const a of fileViewActions" },
  { in: "enterEdit", on: "ed", via: "mount", is: "the editor chunk's mount into host, the div.fileview-cm root (a body root: body.replaceChildren(host) is resolved by the body's read); the CodeMirror editor goes inside that root, not beside it", decl: "a parameter of the callback handed to editorChunk().then" },
  { in: "showPdfPages", on: "pdf", via: "render", is: "the PDF chunk's render into host, the div.fileview-pdfhost root (a body root: body.replaceChildren(wait, host) is resolved by the body's read); the page canvases go inside that root", decl: "a destructured binding of a parameter of the callback handed to Promise.all([pdfChunkLoad(), blob.arrayBuffer()]).then" },
];
/** A member of a receiver read by a COMPUTED name and stored or handed on (`const at = rows[cur]`), READ BY HAND and listed by
 *  its site: the nearest named function (`in`) and the receiver's spelling (`on`), with what the receiver is (`is`), the
 *  hand read's claim that the value is no seating method of an element (the round-6 review's census-1, 2026-09-20: a
 *  computed member read is the one form that reaches a method without spelling its name, `const f = md[m]; f(x)`). A stored
 *  index read the table does not list fails the census with its line, and an entry the source has no such read for fails
 *  it too. An index read whose value is only compared, tested or read further is not stored and is not listed. */
type IndexRead = { in: string; on: string; is: string };
const INDEX_READS_BY_HAND: IndexRead[] = [
  { in: "stepTextSize", on: "TEXT_SIZES", is: "the text-size steps, a readonly array of numbers; the one at the clamped index is returned as the next size" },
  { in: "setCur", on: "rows", is: "the outline popover's rows, an array of the row elements openOutline built; the one at the index has its class and id read (no seat: classList.add and setAttribute)" },
  { in: "restore", on: "nowKeys", is: "the folds' keys, an array of strings, one per fold now in the body; the one at the index is looked up in a map" },
  { in: "boundarySide", on: "node.childNodes", is: "a selection boundary's neighbours, the child nodes at and before the offset, read for whether each is a text leaf (leafIsText) and never seated" },
];
/** For every `body` token of `tokens`, the index of the innermost bracket (`(`, `[`, `{`) open around it, or -1, and for
 *  every bracket the index of the one open around it: one pass over `src` with the literal ranges skipped. */
function bracketMap(src: string, literals: Array<[number, number]>, tokens: number[]): { openerAt: Map<number, number>; parentOf: Map<number, number> } {
  const openerAt = new Map<number, number>(), parentOf = new Map<number, number>();
  const stack: number[] = [];
  let lit = 0, tok = 0;
  for (let i = 0; i < src.length; i++) {
    while (lit < literals.length && literals[lit][1] <= i) lit++;
    if (lit < literals.length && i >= literals[lit][0]) { i = literals[lit][1] - 1; continue; }
    while (tok < tokens.length && tokens[tok] < i) tok++;
    if (tok < tokens.length && tokens[tok] === i) openerAt.set(i, stack.length ? stack[stack.length - 1] : -1);
    const c = src[i];
    if (c === "(" || c === "[" || c === "{") { parentOf.set(i, stack.length ? stack[stack.length - 1] : -1); stack.push(i); }
    else if (c === ")" || c === "]" || c === "}") stack.pop();
  }
  return { openerAt, parentOf };
}
const HANDED_OUT = "body is written bare where the census cannot class it";
/** The declaration that opens the one object literal the action-context accessor passes in (file-view.ts's viewer seam). */
const ACTION_CTX_DECL = "const ctx: FileViewActionCtx =";
/** Why the bare `body` token at `at` (one no member access follows) is refused, or null when its context passes: a
 *  declaration, a parameter, a declared type or a property key; a comparison operand; the action-context accessor
 *  `body: () => body`; an argument, or a property of an argument, to a callee BODY_HANDED_TO lists. Every other context is
 *  refused with what it is: a callee not listed by its name, and the rest (an alias, a return, an arrow's value, an array
 *  element, a ternary or logical operand, a parenthesised or cast receiver) as handed out. */
function bareContext(src: string, at: number, openerAt: Map<number, number>, parentOf: Map<number, number>): string | null {
  const before = src.slice(0, at), rest = src.slice(at + 4);
  const pre = /(===|!==|==|!=|=>|\?\?|\|\||&&|\b(?:const|let|var|return|typeof|await|yield|throw|case|in|of|instanceof|new|void|delete)|[^\s])\s*$/.exec(before)?.[1] ?? "";
  const post = /^\s*(?:!(?!=))?\s*(===|!==|==|!=|=>|\?\?|\|\||&&|\(\)\s*:|\bas\b|[^\s])/.exec(rest)?.[1] ?? "";
  const lineStart = /(?:^|\n)[ \t]*$/.test(before);
  const snippet = (): string => ": " + src.slice(before.lastIndexOf("\n") + 1, at + 4 + rest.indexOf("\n")).trim().slice(0, 100);
  if (post === ":" && (lineStart || ["{", ",", ";", "(", "const", "let", "var"].includes(pre))) return null;   // a declaration's or a parameter's type, a property key
  if (["const", "let", "var"].includes(pre)) return null;   // the declaration
  if (/^\(\)\s*:$/.test(post)) return null;   // a method signature in a type
  const compare = ["===", "!==", "==", "!="];
  if (compare.includes(pre) || compare.includes(post)) return null;   // an identity comparison hands nothing out
  const open = openerAt.get(at) ?? -1;
  if (pre === "=>") {   // the action-context accessor alone, and at its one site: inside the object literal the ctx declaration opens (the round-5 review's extra8-2: keyed on its spelling, it passed anywhere)
    if (!/body\s*:\s*\(\)\s*=>\s*$/.test(before)) return HANDED_OUT + " (an arrow's value)" + snippet();
    return open >= 0 && src[open] === "{" && new RegExp(ACTION_CTX_DECL.replace(/[()]/g, "\\$&") + "\\s*$").test(src.slice(0, open)) ? null : "body: () => body is written outside the object literal declared `" + ACTION_CTX_DECL + "`, the one action-context accessor the census passes (the Comments panel's hand-out, read by hand): a second accessor is read by hand and this check widened, never passed" + snippet();
  }
  if (post === "as") return HANDED_OUT + " (a cast receiver)" + snippet();
  if (open >= 0 && src[open] === "(") {
    const close = open + balancedAt(src, open).length + 1;
    if (/^\s*(?::[^=;]*?)?=>/.test(src.slice(close + 1)) || /\bfunction\b(?:\s+[\w$]+)?\s*$/.test(src.slice(0, open))) return null;   // a parameter
    const callee = /([\w$]+(?:\s*(?:\?\.|!\.|\.)\s*[\w$]+)*)\s*!?\s*$/.exec(src.slice(0, open))?.[1]?.replace(/\s+|!/g, "");
    if (!callee || /^(?:if|for|while|switch|return|typeof|await|void|delete|new|else|do|case|throw|yield|catch|with|in|of)$/.test(callee)) return HANDED_OUT + " (a parenthesised receiver or operand)" + snippet();
    return BODY_HANDED_TO.some((h) => h.callee === callee) ? null : "body is handed to " + callee + "(...), a callee the census does not list: read it by hand for a seat in the body and list it in BODY_HANDED_TO, or seat the body here by its name" + snippet();
  }
  if (open >= 0 && src[open] === "{" && ["{", ","].includes(pre) && [",", "}"].includes(post)) {   // a shorthand property of an object literal
    const outer = parentOf.get(open) ?? -1;
    if (outer >= 0 && src[outer] === "(") {
      const callee = /([\w$]+(?:\s*(?:\?\.|!\.|\.)\s*[\w$]+)*)\s*!?\s*$/.exec(src.slice(0, outer))?.[1]?.replace(/\s+|!/g, "");
      if (callee && BODY_HANDED_TO.some((h) => h.callee === callee)) return null;
      return "body is handed to " + (callee || "a parenthesised expression") + "(...) as a property of its argument, a callee the census does not list: read it by hand for a seat in the body and list it in BODY_HANDED_TO" + snippet();
    }
    return HANDED_OUT + " (a property of an object literal handed nowhere the census can name)" + snippet();
  }
  return HANDED_OUT + " (" + (open >= 0 && src[open] === "[" ? "an array element" : pre === "=" ? "an alias" : pre === "return" ? "a return" : pre === "?" || pre === ":" ? "a ternary operand" : ["??", "||", "&&"].includes(pre) || ["??", "||", "&&"].includes(post) ? "a logical operand" : "after `" + pre + "`") + ")" + snippet();
}

test("the census of the body's roots, its default refusing: every `body` token in file-view.ts outside a literal is one the census classes (a member access by what follows the member: a seating call, resolved; a call, an assignment, a further access or a bare read the census lists as seating nothing; a bare token by its context: a declaration, a parameter, a property key, a comparison, the action-context accessor at its one declared site, an argument to a callee read by hand and listed) and every seat in the file on any other receiver (a seating call, an innerHTML or outerHTML assignment) and every call it reads by its site (call, apply, bind, mount, render, a reflection global's method) is a site read by hand and listed in SEATS_READ_BY_HAND with the receiver's binding, one binding per entry, every other method call is by a name listed as seating nothing, no seating method is read without being called, a member stored under a computed name is a site listed in INDEX_READS_BY_HAND, the file calls nothing through a computed name and nothing but a name or a member, and every listed site is live, else the census FAILS with the line; every element the viewer seats resolves to a root the flow lists (READY_ROOTS, NOT_READY_ROOTS or LINE_ROOTS), every listed root is seated, no root is in two lists, bodyReady answers over each root as its list says, an unlisted child is NOT in (the safe side, so a root the viewer gains fails here until it is listed), and under the PDF kind the loader alone of the wait roots reads as content", (t) => {
  const { seated, refused } = census(VIEWER_SRC);
  assert.deepEqual(refused, [], "every use of the body is one the census knows how to read: a use it does not is read by hand and the census taught it, never skipped");
  const roots = [...seated.keys()].sort();
  t.diagnostic("census: " + roots.map((r) => r + " (line " + seated.get(r)!.join(", ") + ")").join("; "));
  const second = seatSites(VIEWER_SRC);
  t.diagnostic("second read: " + second.sites.length + " seats and site-read calls (" + second.sites.filter((s) => s.body).length + " on the body token, " + second.sites.filter((s) => !s.body).length + " on other receivers, " + SEATS_READ_BY_HAND.length + " distinct sites listed), " + second.indexReads.length + " stored index reads (" + INDEX_READS_BY_HAND.length + " distinct sites listed), " + NON_SEATING_METHODS.length + " method names listed as seating nothing");
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

test("the census refuses its unknown and derives its population, executed over mutants of file-view.ts's source: a root seated by body.append or body.insertBefore is resolved and fails the lists (FAILS BEFORE: the three-name list never saw either, so the census passed over both), a seat through an innerHTML assignment, a call the census does not know, a further access on a child node and a child-level replaceWith each fail with their line, and a read or a scroll assignment passes; the round-4 review's forms each red with the planted line (FAILS BEFORE: body?.append(x) and body[\"append\"](x) were outside the collect pattern, body.append?.(x) was a further access refused for node members alone, body.append.call(body, x), .bind and .apply and a bare body.append passed); the round-5 fix's forms each red with the planted line (FAILS BEFORE: (body).append(x), (body as HTMLElement).append(x), an alias const b = body, [body].forEach(...), Element.prototype.append.call(body, x) and a helper handed the body passed with no refusal and no root; a seat quoted in a column-0 // comment or after ;// counted as a seat, and a listed root's seat moved into one kept the census green); a seat written across a newline is read, a comment's prose is not, a declaration, a comparison and a listed callee's argument pass, and body.classList.add(...) still passes; the round-5 review's forms each red with the planted line (FAILS BEFORE: the census refused six child-level method names and passed every other seat unread, so a seat through body.querySelector(...)!.parentElement, a stored query result, md.parentElement!.append(x), a parent held in a variable, body.closest(...) and body.getRootNode(), a node read inside a listener's callback or a nested call within a body call's arguments and then seated, and the accessor body: () => body written anywhere but its declared site all passed with no refusal and no root); a seat on a receiver the table does not list, a computed-name call, a live site whose entry is removed, a stale entry and the ctx declaration renamed each red; the round-6 review's forms each red with the planted line (FAILS BEFORE: the second read knew a closed list of seating names and passed every other form on a receiver other than the body, so a seating method reached through call, bind or apply on md or md.parentElement, Reflect.apply(md.append, ...), a bound seat, a Range's insertNode, setHTMLUnsafe, moveBefore, a method by a name the census does not list, a bare read of md.append or md[\"append\"], a member read by a computed name and stored, a parenthesised callee, Object.assign(md, { innerHTML }) and Reflect.set(md, \"innerHTML\", ...) all passed with no refusal and no root; a block's const main = md.parentElement! and a callback's parameter named main seated under the entry for openFileView's main, while a second seat on the listed binding passes; a spread into body.append threw with no line), and a receiver with a cast inside is spelled with its spaces", () => {
  const at = (src: string, needle: string): number => { const i = src.indexOf(needle); assert.ok(i >= 0, needle + " is in the source"); return i; };
  const seat = (call: string): string => { const i = at(VIEWER_SRC, "\n  body.appendChild(load);\n"); return VIEWER_SRC.slice(0, i) + "\n  " + call + VIEWER_SRC.slice(i); };   // a line inside the local viewer's open, before its loader is seated
  const plantedLine = VIEWER_SRC.slice(0, at(VIEWER_SRC, "\n  body.appendChild(load);\n")).split("\n").length + 1;   // the line the planted call lands on
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
  assert.equal(unknownCall.refused.length, 1, "a call the census does not know is refused (once: the seat read's receiver is the body token, which the token read owns)"); assert.match(unknownCall.refused[0], /^line \d+: body\.replaceChild\(\.\.\.\) is a call the census does not know/);
  const chained = census(seat('body.firstElementChild!.replaceWith(el("div", "fileview-mutant"));'));
  assert.equal(chained.refused.length, 2, "a further access on a child node is refused, and so is the replaceWith it reaches, a seat on a receiver the table does not list"); assert.match(chained.refused[0], /^line \d+: body\.firstElementChild hands out a node/); assert.match(chained.refused[1], /^line \d+: body\.firstElementChild!\.replaceWith\(el\("div", "fileview-mutant"\)\) seats on `body\.firstElementChild` in openFileView, a receiver the census has not read by hand/);
  const reads = census(seat('if (body.scrollTop > 0 && body.clientWidth === 0 && typeof body.getClientRects === "function") body.scrollTop = 0;'));
  assert.deepEqual(reads.refused, [], "reads and a scroll assignment seat nothing and pass");
  assert.deepEqual([...reads.seated.keys()].sort(), [...before.seated.keys()].sort(), "...and seat no root");
  const unresolvable = census(seat('body.appendChild(someRoot);'));
  assert.equal(unresolvable.refused.length, 1, "an argument the census cannot resolve is refused with its line: " + JSON.stringify(unresolvable.refused)); assert.match(unresolvable.refused[0], /^line \d+: body\.appendChild\(\.\.\.\) seats `someRoot`, an expression the census cannot resolve to a root \(the variable someRoot is assigned before the site/);
  // the round-4 review's forms (correctness-2, regression-1), each red with the planted line: two resolve to a root the lists
  // do not name (the seat is read, so the lists comparison reds with the line), three are refused with the line
  const seatsMutant = (src: string, form: string): void => {
    const r = census(src);
    assert.deepEqual(r.refused, [], form + ": a seating call, read as one (no refusal)");
    assert.deepEqual([...r.seated.keys()].filter((k) => !before.seated.has(k)), ["div.fileview-mutant"], "FAILS BEFORE: " + form + " was outside the census; now its root is resolved and fails the lists");
    assert.deepEqual(r.seated.get("div.fileview-mutant"), [plantedLine], form + ": with the planted line");
  };
  seatsMutant(seat('body?.append(el("div", "fileview-mutant"));'), "body?.append(x)");
  seatsMutant(seat('body.append?.(el("div", "fileview-mutant"));'), "body.append?.(x)");
  seatsMutant(seat('body\n    .append(el("div", "fileview-mutant"));'), "a seat written across a newline");
  const refusedMutant = (src: string, form: string, want: RegExp, count = 1): void => {   // count: a form that hands the body to its own seating method (`body.append.call(body, x)`) is refused twice, once per token, each with the line
    const r = census(src);
    assert.equal(r.refused.length, count, form + ": " + count + " refusal(s): " + JSON.stringify(r.refused));
    for (const one of r.refused) assert.ok(one.startsWith("line " + plantedLine + ": "), form + ": with the planted line: " + one);
    assert.match(r.refused[0], want, form);
    assert.deepEqual([...r.seated.keys()].sort(), [...before.seated.keys()].sort(), form + ": and no root seated");
  };
  refusedMutant(seat('body["append"](el("div", "fileview-mutant"));'), 'body["append"](x)', /body\[\.\.\.\] reaches a member by a computed name/, 2);   // and the seat read refuses the computed call itself
  refusedMutant(seat('body?.["append"](el("div", "fileview-mutant"));'), 'body?.["append"](x)', /body\?\.\[\.\.\.\] reaches a member by a computed name/, 2);
  refusedMutant(seat('body.append.call(body, el("div", "fileview-mutant"));'), "body.append.call(body, x)", /body\.append\.\.\.\. reaches the seating method through a further access/, 2);
  refusedMutant(seat('body.append.bind(body)(el("div", "fileview-mutant"));'), "body.append.bind(body)(x)", /body\.append\.\.\.\. reaches the seating method through a further access/, 3);   // both tokens, and the second read's: a call's value called (round 6)
  refusedMutant(seat('body.append.apply(body, [el("div", "fileview-mutant")]);'), "body.append.apply(body, [x])", /body\.append\.\.\.\. reaches the seating method through a further access/, 2);
  refusedMutant(seat('body.append["call"](body, el("div", "fileview-mutant"));'), 'body.append["call"](body, x)', /body\.append\[\.\.\. reaches the seating method through a further access/, 3);   // both tokens, and the seat read's computed call
  refusedMutant(seat('const seatLater = body.append;'), "a bare read of body.append", /body\.append is read bare/);
  refusedMutant(seat('const seatLater = body.insertAdjacentHTML;'), "a bare read of body.insertAdjacentHTML", /body\.insertAdjacentHTML is read bare/);
  refusedMutant(seat('const first = body.firstChild;'), "a bare read of body.firstChild stored under another name", /body\.firstChild is read bare outside a body call's arguments/);
  refusedMutant(seat('body.innerHTML += "<div class=\\"fileview-mutant\\"></div>";'), "a compound assignment to innerHTML", /body\.innerHTML \+= \.\.\. is an assignment the census does not know/);
  refusedMutant(seat('body.shadowRoot!.append(el("div", "fileview-mutant"));'), "a further access on a member the census does not know", /body\.shadowRoot\.\.\.\. is a further access on a member the census does not know/, 2);   // and the seat on `body.shadowRoot`, a receiver the table does not list
  // the round-5 fix's forms (the round-4 review's verifiers: a parenthesised or cast receiver passed the census green with no
  // root; the body under another name was a disclosed blind spot), each refused with the planted line and no root seated
  refusedMutant(seat('(body).append(el("div", "fileview-mutant"));'), "(body).append(x)", /body is written bare where the census cannot class it \(a parenthesised receiver or operand\)/, 2);   // the token, and the seat on `(body)`, not the sanctioned token
  refusedMutant(seat('(body as HTMLElement).append(el("div", "fileview-mutant"));'), "(body as HTMLElement).append(x)", /body is written bare where the census cannot class it \(a cast receiver\)/, 2);
  refusedMutant(seat('const seatLater = body;'), "an alias, const b = body", /body is written bare where the census cannot class it \(an alias\)/);
  refusedMutant(seat('[body].forEach((b) => b.prepend(el("div", "fileview-mutant")));'), "[body].forEach(b => b.prepend(x))", /body is written bare where the census cannot class it \(an array element\)/, 2);   // and b.prepend, a seat on a receiver the table does not list
  refusedMutant(seat('Element.prototype.append.call(body, el("div", "fileview-mutant"));'), "Element.prototype.append.call(body, x)", /body is handed to Element\.prototype\.append\.call\(\.\.\.\), a callee the census does not list/, 3);   // the token, and the second read's two: a call read by its site and not listed, and append read without being called (round 6)
  refusedMutant(seat('seatInto(body, el("div", "fileview-mutant"));'), "a helper handed the body", /body is handed to seatInto\(\.\.\.\), a callee the census does not list/);
  refusedMutant(seat('seatInto({ body, root: el("div", "fileview-mutant") });'), "a helper handed the body as a property", /body is handed to seatInto\(\.\.\.\) as a property of its argument, a callee the census does not list/);
  refusedMutant(seat('const target = wrap ? body : main;'), "a ternary operand", /body is written bare where the census cannot class it \(a ternary operand\)/);
  refusedMutant(seat('const target = held ?? body;'), "a logical operand", /body is written bare where the census cannot class it \(a logical operand\)/);
  refusedMutant(seat('const target = () => body;'), "an arrow's value outside the accessor", /body is written bare where the census cannot class it \(an arrow's value\)/);
  // the round-5 review's six escapes (2026-09-20), each red with the planted line under the inverted default: a seat on any
  // receiver but the sanctioned `body` token is refused unless its site is in the table, whatever produced the receiver
  const SEAT_UNREAD = /seats on `([^`]+)` in openFileView, a receiver the census has not read by hand/;
  refusedMutant(seat('body.querySelector("x")!.parentElement!.append(el("div", "fileview-mutant"));'), "a seat through body.querySelector(...)!.parentElement", SEAT_UNREAD);
  refusedMutant(seat('const md2 = body.querySelector("x"); md2!.append(el("div", "fileview-mutant"));'), "a seat through a stored query result", SEAT_UNREAD);
  refusedMutant(seat('md.parentElement!.append(el("div", "fileview-mutant"));'), "md.parentElement!.append(x)", SEAT_UNREAD);
  refusedMutant(seat('const p = body.firstChild!.parentElement; p.append(el("div", "fileview-mutant"));'), "a parent held in a variable", /body\.firstChild hands out a node/, 2);   // the further access, and the seat on p
  refusedMutant(seat('body.closest(".fileview-body")!.append(el("div", "fileview-mutant"));'), 'body.closest(...)!.append(x)', /body\.closest\(\.\.\.\) is a call the census does not know/, 2);
  refusedMutant(seat('body.getRootNode().appendChild(el("div", "fileview-mutant"));'), "body.getRootNode().appendChild(x)", /body\.getRootNode\(\.\.\.\) is a call the census does not know/, 2);
  refusedMutant(seat('body.addEventListener("keydown", () => { const c = body.firstChild; c!.append(el("div", "fileview-mutant")); });'), "a node read inside a listener's callback, then seated", /body\.firstChild is read bare outside a body call's arguments \(or inside a nested call's or a callback's within them\)/, 2);   // the read, and the seat on c
  refusedMutant(seat('if (body.contains(pick(body.firstChild))) return;'), "a node read inside a nested call within a body call's arguments", /body\.firstChild is read bare outside a body call's arguments \(or inside a nested call's or a callback's within them\)/);
  const nested = census(seat('body.insertBefore(el("div", "fileview-mutant"), pick(body.firstChild));'));
  assert.equal(nested.refused.length, 1, "the reference child read inside a nested call is refused: " + JSON.stringify(nested.refused)); assert.match(nested.refused[0], /^line \d+: body\.firstChild is read bare outside a body call's arguments \(or inside a nested call's/);
  assert.deepEqual(nested.seated.get("div.fileview-mutant"), [plantedLine], "...and the seat itself is still resolved");
  for (const [form, planted] of [["md[\"append\"](x)", 'md["append"](el("div", "fileview-mutant"));'], ["md[m](x)", 'md[m](el("div", "fileview-mutant"));']] as const) refusedMutant(seat(planted), form + ", a call through a computed name", /calls through a computed name the census cannot read/);
  for (const [form, planted] of [["md.replaceWith(x)", 'md.replaceWith(el("div", "fileview-mutant"));'], ["md.after(x)", 'md.after(el("div", "fileview-mutant"));'], ["md.insertAdjacentHTML(...)", 'md.insertAdjacentHTML("afterend", "<div class=\\"fileview-mutant\\"></div>");'], ["md.outerHTML = ...", 'md.outerHTML = "<div class=\\"fileview-mutant\\"></div>";'], ["md.innerHTML += ...", 'md.innerHTML += "<div class=\\"fileview-mutant\\"></div>";']] as const) refusedMutant(seat(planted), form + " on a receiver the table does not list", SEAT_UNREAD);
  // the round-6 review's census-1 (2026-09-20): the FORM axis refuses its unknown too. Before this the second read knew a closed
  // list of seating names and passed every other method call, a seating method read without being called, and a member
  // read by a computed name, so each of these seated with no refusal and no root
  const SITE_UNREAD = /calls (?:call|apply|bind|assign|set|insertNode) on `[^`]+` in openFileView, a call the census reads by its site/;
  const HANDED_METHOD = /reads the method append without calling it/;
  refusedMutant(seat('Reflect.apply(md.append, md, [el("div", "fileview-mutant")]);'), "Reflect.apply(md.append, md, [x])", SITE_UNREAD, 2);   // the reflection global's call by its site, and append read without being called
  refusedMutant(seat('Reflect.apply(Element.prototype.append, md.parentElement, [el("div", "fileview-mutant")]);'), "Reflect.apply(Element.prototype.append, md.parentElement, [x])", SITE_UNREAD, 2);
  refusedMutant(seat('md.append.call(md, el("div", "fileview-mutant"));'), "md.append.call(md, x)", SITE_UNREAD, 2);
  refusedMutant(seat('md.parentElement!.append.call(md.parentElement, el("div", "fileview-mutant"));'), "md.parentElement!.append.call(md.parentElement, x)", SITE_UNREAD, 2);
  refusedMutant(seat('Element.prototype.append.call(md.parentElement, el("div", "fileview-mutant"));'), "Element.prototype.append.call(md.parentElement, x)", SITE_UNREAD, 2);
  refusedMutant(seat('const seatMd = md.parentElement!.append.bind(md.parentElement); seatMd(el("div", "fileview-mutant"));'), "a bound seat, const f = md.parentElement!.append.bind(md.parentElement); f(x)", SITE_UNREAD, 2);
  refusedMutant(seat('const rg = document.createRange(); rg.selectNodeContents(md.parentElement!); rg.insertNode(el("div", "fileview-mutant"));'), "a Range's insertNode over md.parentElement", /rg\.insertNode\(el\("div", "fileview-mutant"\)\) seats on `rg` in openFileView, a receiver the census has not read by hand/, 2);   // the seat by insertNode on a receiver the table does not list, and selectNodeContents, a method it does not list
  refusedMutant(seat('(md.parentElement as any).setHTMLUnsafe("<div class=\\"fileview-mutant\\"></div>");'), "(md.parentElement as any).setHTMLUnsafe(...)", /seats on `\(md\.parentElement as any\)` in openFileView, a receiver the census has not read by hand/);
  refusedMutant(seat('(md.parentElement as any).moveBefore(el("div", "fileview-mutant"), null);'), "(md.parentElement as any).moveBefore(x, null)", SEAT_UNREAD);
  refusedMutant(seat('md.parentElement!.seatAnywhere(el("div", "fileview-mutant"));'), "a method the census does not list, by any name", /calls seatAnywhere on `md\.parentElement`, a method the census does not list as seating or as seating nothing: read it by hand and list it/);
  refusedMutant(seat('const seatLater2 = md.append;'), "a bare read of md.append", HANDED_METHOD);
  refusedMutant(seat('const seatLater3 = md["append"];'), 'a bare read of md["append"]', HANDED_METHOD);
  refusedMutant(seat('const seatLater4 = md[m];'), "a member read by a computed name and stored, const f = md[m]", /seatLater4 = md\[m\] reads a member of `md` by a computed name and stores or hands it on, in openFileView: read the site for what md is and list it in INDEX_READS_BY_HAND/);
  refusedMutant(seat('(md.append)(el("div", "fileview-mutant"));'), "(md.append)(x), a parenthesised callee", HANDED_METHOD, 2);   // append read without being called (its call is the parenthesised expression's), and the callee the census cannot read
  refusedMutant(seat('Object.assign(md, { innerHTML: "<div class=\\"fileview-mutant\\"></div>" });'), "Object.assign(md, { innerHTML })", SITE_UNREAD);
  refusedMutant(seat('Reflect.set(md, "innerHTML", "<div class=\\"fileview-mutant\\"></div>");'), 'Reflect.set(md, "innerHTML", ...)', SITE_UNREAD);
  refusedMutant(seat('(md as any).up.append(el("div", "fileview-mutant"));'), "a cast inside the receiver", /seats on `\(md as any\)\.up` in openFileView/);   // the round-6 review's census-5: the receiver is spelled with its spaces, so the line can be read
  // the round-6 review's census-2 (2026-09-20): an entry is keyed on the receiver's spelling and held to ONE binding, so a
  // second declaration of a listed name inside the entry's function is refused rather than read under the entry's claim
  const rebound = (src: string, form: string, decl: RegExp): void => {
    const r = census(src);
    assert.equal(r.refused.length, 2, form + ": the seat's binding and the entry's two bindings: " + JSON.stringify(r.refused));
    assert.ok(r.refused[0].startsWith("line " + plantedLine + ": "), form + ": with the planted line: " + r.refused[0]);
    assert.match(r.refused[0], decl, form); assert.match(r.refused[0], /where SEATS_READ_BY_HAND read `const main = el\("div", "fileview-main"\)`: the receiver is not the one read by hand/, form);
    assert.match(r.refused[1], /^SEATS_READ_BY_HAND's entry `main\.appendChild` in openFileView covers seats on 2 bindings of main \(lines \d+, \d+\): one entry reads one receiver$/, form);
    assert.deepEqual([...r.seated.keys()].sort(), [...before.seated.keys()].sort(), form + ": and no root seated");
  };
  rebound(seat('{ const main = md.parentElement!; main.appendChild(el("div", "fileview-mutant")); }'), "a block's const main = md.parentElement!", /seats on `main` in openFileView, bound to `const main = md\.parentElement!`/);
  rebound(seat('[md.parentElement!].forEach((main) => main.appendChild(el("div", "fileview-mutant")));'), "a callback's parameter named main", /seats on `main` in openFileView, bound to `a parameter of the callback handed to \[md\.parentElement!\]\.forEach`/);
  const sameBinding = census(seat('main.appendChild(el("div", "fileview-mutant"));'));
  assert.deepEqual(sameBinding.refused, [], "a second seat on the listed binding of main passes: the entry's claim (the body's parent, so a seat in it lands beside the body) is about the binding, and covers every seat on it");
  // the round-6 review's census-4 (2026-09-20): an argument the resolver cannot read is refused with its line (before this rootsOf threw, naming the expression and not the line)
  refusedMutant(seat('body.append(...[el("div", "fileview-mutant")]);'), "a spread into body.append", /body\.append\(\.\.\.\) seats `\.\.\.\[el\("div", "fileview-mutant"\)\]`, an expression the census cannot resolve to a root \(a seated expression the census cannot resolve/);
  refusedMutant(seat('const kids = [el("div", "fileview-mutant")]; body.append(...kids);'), "a spread of a variable into body.append", /body\.append\(\.\.\.\) seats `\.\.\.kids`, an expression the census cannot resolve to a root/);
  // the action-context accessor passes at its one site alone (the round-5 review's extra8-2): the spelling anywhere else is refused
  const ACCESSOR_ELSEWHERE = /body: \(\) => body is written outside the object literal declared `const ctx: FileViewActionCtx =`/;
  refusedMutant(seat('const other = { body: () => body };'), "the accessor in a second object literal", ACCESSOR_ELSEWHERE);
  refusedMutant(seat('const acc = () => ({ body: () => body });'), "the accessor in a function's returned literal", ACCESSOR_ELSEWHERE);
  refusedMutant(seat('let held = { path, body: () => body, open: true };'), "the accessor in a variable's literal", ACCESSOR_ELSEWHERE);
  refusedMutant(seat('const ctx2: FileViewActionCtx = { path, body: () => body };'), "the accessor under a renamed ctx const", ACCESSOR_ELSEWHERE);
  refusedMutant(seat('installFilePrint({ card: box, bar, body: () => body, typing: typingHere, onClose: (cb) => { closeHooks.push(cb); } });'), "the accessor moved into a callee's argument", ACCESSOR_ELSEWHERE);
  assert.ok(VIEWER_SRC.includes("\n  const ctx: FileViewActionCtx = {\n"), "the sanctioned site is declared as the census expects");
  const ctxRenamed = census(VIEWER_SRC.replace("\n  const ctx: FileViewActionCtx = {\n", "\n  const actions: FileViewActionCtx = {\n"));
  assert.deepEqual(ctxRenamed.refused.filter((r) => !ACCESSOR_ELSEWHERE.test(r)), ["the census passes the action-context accessor `body: () => body` inside the object literal declared `const ctx: FileViewActionCtx = {`, and the source declares no such literal: read the hand-out by hand again"], "the ctx declaration renamed: the census holds the source to it");
  assert.equal(ctxRenamed.refused.filter((r) => ACCESSOR_ELSEWHERE.test(r)).length, 1, "...and the live accessor is refused with its line, since its literal is no longer the declared one");
  // the table is read, not decorative: a live site whose entry is removed reds with its line, and an entry with no site reds
  const dropped = SEATS_READ_BY_HAND.find((e) => e.in === "mdBlock" && e.on === "box" && e.via === "replaceChildren")!;
  const withoutEntry = census(VIEWER_SRC, SEATS_READ_BY_HAND.filter((e) => e !== dropped));
  assert.equal(withoutEntry.refused.length, 1, "the markdown root's own seat, unlisted, is refused: " + JSON.stringify(withoutEntry.refused));
  assert.match(withoutEntry.refused[0], /^line \d+: box\.replaceChildren\(\.\.\.Array\.from\(sanitizeMd\(dirty, mintHeadingIds\)\.childNodes\)\) seats on `box` in mdBlock, a receiver the census has not read by hand/);
  const stale = census(VIEWER_SRC, [...SEATS_READ_BY_HAND, { in: "openFileView", on: "gone", via: "append", is: "an entry the source has no seat for" }]);
  assert.deepEqual(stale.refused, ["SEATS_READ_BY_HAND lists `gone.append` in openFileView, and the source has no such seat: the entry is stale, remove it or read the site again"], "a stale entry is refused, so the table holds the live sites and nothing more");
  const moved = census(VIEWER_SRC, SEATS_READ_BY_HAND.map((e) => (e === dropped ? { ...e, in: "renderBody" } : e)));
  assert.equal(moved.refused.length, 2, "an entry keyed to another function matches nothing: the live site reds and the entry is stale: " + JSON.stringify(moved.refused));
  // the seats the table holds are the file's: every non-body seat matched an entry (no refusal above), and the population is stated
  const live = seatSites(VIEWER_SRC);
  assert.equal(live.computed.length, 0, "file-view.ts calls nothing through a computed name");
  assert.ok(live.sites.filter((s) => s.body).length >= 10 && live.sites.filter((s) => !s.body).length > live.sites.filter((s) => s.body).length, "the seat read finds the file's seats, on the body token and on the rest (the counts are the commit's, derived by this read, not kept here)");
  assert.equal(new Set(live.sites.filter((s) => !s.body).map((s) => s.fn + "|" + s.on + "|" + s.via)).size, SEATS_READ_BY_HAND.length, "one entry per distinct site (function, receiver, form): the table has no duplicate and no site is covered twice");
  assert.deepEqual({ unknown: live.unknown, handedOut: live.handedOut, oddCallee: live.oddCallee }, { unknown: [], handedOut: [], oddCallee: [] }, "every method file-view.ts calls is by a name the census lists, no seating method is read without being called, and every callee is a name or a member (the round-6 review's census-1)");
  assert.equal(new Set(live.indexReads.map((i) => i.fn + "|" + i.on)).size, INDEX_READS_BY_HAND.length, "one entry per stored index read (function, receiver): the index table has no duplicate and no site is covered twice");
  for (const e of SEATS_READ_BY_HAND) { const s = live.sites.find((x) => x.fn === e.in && x.on === e.on && x.via === e.via)!; assert.equal(e.decl, s.decl, "the entry for " + e.in + "/" + e.on + "/" + e.via + " names the binding its sites resolve to (a member chain names none)"); }
  // a listed callee whose parameter the census reads under the body's name: renamed, the census fails until it is read again
  const renamed = census(VIEWER_SRC.replace("\nfunction foldKeeper(body: HTMLElement)", "\nfunction foldKeeper(root: HTMLElement)"));
  assert.deepEqual(renamed.refused.filter((r) => r.startsWith("BODY_HANDED_TO lists foldKeeper")), ["BODY_HANDED_TO lists foldKeeper as reading the body under its own parameter named body, and the source declares no such parameter: read it by hand again"], "the own-parameter claim is held to the source");
  // what still passes: a plain `.` tail on classList, style and dataset, a scalar's own method, a non-seating method read as a value; a bare
  // token as a declaration, a parameter, a property key, a comparison, an argument to a listed callee and as a property of one
  const passes = census(seat('body.classList.add("fileview-mutant"); body.style.height = "0"; body.dataset.probe = "1"; body.scrollTop.toString(); if (typeof body.getClientRects === "function") body.scrollTop += 0;'));
  assert.deepEqual(passes.refused, [], "body.classList.add(...), body.style, body.dataset, a scalar's method, a typeof read of a non-seating method and a compound scroll assignment pass");
  assert.deepEqual([...passes.seated.keys()].sort(), [...before.seated.keys()].sort(), "...and seat no root");
  const bare = census(seat('if (document.activeElement === body || body !== null) foldKeeper(body); const keep = (body: HTMLElement): void => { readPlace(body, ""); }; installFilePrint({ card: box, bar, body, typing: typingHere, onClose: (cb) => { closeHooks.push(cb); } }); const fold = { key: "k", body: "text", open: true };'));
  assert.deepEqual(bare.refused, [], "a comparison, a listed callee's argument, a parameter, a property key and a listed callee's shorthand property pass");
  assert.deepEqual([...bare.seated.keys()].sort(), [...before.seated.keys()].sort(), "...and seat no root");
  // a comment's prose is blanked before the read, wherever the comment stands, so "the body. The next…" is no member access and a seat quoted in a comment is no seat
  const prose = census(stripComments(seat('/** the body. The next paint seats it. */')));
  assert.deepEqual(prose.refused, [], "a block comment's prose is not read (the collect pattern reads across whitespace, so unblanked it would read `body. The` as a member)");
  assert.equal(census(seat('/** the body. The next paint seats it. */')).refused.length, 1, "...where the raw source would have been refused for it: the blanking is load-bearing");
  const seatCol0 = (text: string): string => { const i = at(VIEWER_SRC, "\n  body.appendChild(load);\n"); return VIEWER_SRC.slice(0, i) + "\n" + text + VIEWER_SRC.slice(i); };   // the same line, written from column 0 (seat indents by two spaces, and a space before `//` is what the old strip keyed on)
  for (const [form, planted] of [["a column-0 // comment", seatCol0('//body.append(el("div", "fileview-mutant"));')], ["a // comment after a ;", seat('load.tabIndex = 0;// body.append(el("div", "fileview-mutant"));')], ["an indented // comment", seat('// body.append(el("div", "fileview-mutant"));')], ["a block comment", seat('/* body.append(el("div", "fileview-mutant")); */')]]) {
    const quoted = census(stripComments(planted));
    assert.deepEqual(quoted.refused, [], form + ": no refusal");
    assert.deepEqual([...quoted.seated.keys()].sort(), [...before.seated.keys()].sort(), "FAILS BEFORE for the first two: a seat quoted in " + form + " is not a seat");
  }
  assert.deepEqual([...census(seatCol0('//body.append(el("div", "fileview-mutant"));')).seated.keys()].filter((k) => !before.seated.has(k)), ["div.fileview-mutant"], "...where the unblanked source counts the quoted seat: the compiler's strip is load-bearing");
  const cmLine = "\n      body.replaceChildren(host);";
  assert.equal(VIEWER_RAW.split(cmLine).length, 2, "the CodeMirror host's seat is written once in file-view.ts, on a line of its own");
  const phantom = census(stripComments(VIEWER_RAW.replace(cmLine, "\n//body.replaceChildren(host);")));
  assert.equal(phantom.seated.has("div.fileview-cm"), false, "FAILS BEFORE: a listed root's seat moved into a column-0 comment is gone from the derived set, so the lists comparison reds (before this the comment was read as code and the census stayed green over a seat that no longer ran)");
  assert.equal(before.seated.has("div.fileview-cm"), true, "...and the real seat is derived");
  assert.deepEqual(census(stripComments(seat('const kind = "image/*"; body.scrollTop = 0;   // image/* files\n  const mark = "/* not a comment */";'))).refused, [], "a comment opener inside a string or inside a line comment opens no block: the code after it is still read");
  assert.deepEqual([...census(stripComments(seat('const kind = "image/*";   // image/* files\n  body.append(el("div", "fileview-mutant"));'))).seated.keys()].filter((k) => !before.seated.has(k)), ["div.fileview-mutant"], "...and a seat after such a line is still found (before the fix the blanking ran to the next star-slash and dropped three spans of the viewer)");
  assert.deepEqual(census(seat('const label = "the body. The next paint seats it: body.append(x)"; const re = /body\\.append\\(/;')).refused, [], "a body token inside a string or a regular-expression literal is text, not code");
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
