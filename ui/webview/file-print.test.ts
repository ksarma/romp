// The print flow's machine and its wait (file-print.ts; the print follow-on to plans/markdown-viewer.md's Slice 3, item 12),
// executed under node with no DOM: `step` over every phase and event (the disabled phase the driver starts in, P7, and the
// stalled phase the deadline's ask stands in, among them), the words, the chord, and settlePictures over fake pictures and a
// fake clock (the deadline is the one timer in the module, and it is injected; Keep waiting's wait sets none). The DOM driver, the button,
// the line and window.print run over the real viewer in file-print-browser.test.ts. Synthetic values only.
// The print record's pins that need the TypeScript compiler stand at the end of this module (the record test,
// tools/markdown-viewer-plan-print-record.test.mjs, runs in CI's shell job with no node_modules and holds the same sentences by text).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import * as crypto from "node:crypto";   // the census holds a text over 300 characters by its sha256 beside its first 80 characters (the round-8 ruling)
import * as ts from "typescript";   // the census blanks file-view.ts's comments with the compiler's own read of them (the round-5 fix; writer-census.ts is the precedent, a runtime require of the test bundle)
import { hideEdges } from "../test-dom-shim";   // every stand-in below that carries a tree edge (parentElement, children, childNodes, firstElementChild) hides it, the shared module's rule (ui/test-dom-shim.test.ts's ratchet)
import { step, RESTING, DISABLED, armedWords, preparingWords, waitingWords, stalledWords, anywayWords, ANYWAY_TITLE, isPrintChord, isPrintKeys, settlePictures, collectPictures, bodyReady, rootKind, PRINT_SETTLE_MS, setPrintSettleMs, printSettleMs,
  WITH_WORDS, WITHOUT_WORDS, ANYWAY_WORDS, KEEP_WORDS, TAB_WORDS, NO_TAB_WORDS, pdfFrameWindow, READY_ROOTS, NOT_READY_ROOTS, LINE_ROOTS, PDF_LOADER_ROOT, printable, figurePrintable, figureHidden, rendered, SVG_NS, PAINTS_SEL, REFERENCE_DEPTH,
  type PrintState, type Picture, type Timers, type BodyLike, type PrintableNode, type FigureNode } from "./file-print";
import { ANYWAY_SENTENCE } from "./file-print-fixtures";   // the sentence's one test-side home, fixed: a compare against it does not move with the product (the round-7 review's cluster A)

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
  assert.ok(!/\b(it|its|them|they|their|these|those|this|that)\b/i.test(anywayWords()) && !/\d/.test(anywayWords()), "the sentence names no counted picture: no pronoun standing for the pictures the count covers and no digit (the round-6 review's ui-1, as its refuters corrected it); this pin NARROWS the class of a wording that turns false when a counted picture lands, and does not close it (a count-free wording that is false for another reason passes here): " + anywayWords());
  assert.equal(anywayWords(), ANYWAY_SENTENCE, "the product's sentence is the fixed test-side copy (file-print-fixtures.ts), the one home a compare cannot move with the product; the driver leg's case (15b) holds the rendered line to the same constant (the round-7 review's cluster A)");
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

test("collectPictures reads the container walk for an svg image as well as the browser's answer (the round-7 fixes, 2026-09-20: Firefox and WebKit report a client rect for an image inside a container that never renders its content, so the browser's answer alone collected it there and Chromium alone skipped it): an image whose SVG ancestors include defs, symbol, clipPath or metadata is not collected and not probed even where the browser reports it rendered, and one under a mask, a pattern or a marker that no printable element references by url(#id) is not either (the stand-ins here carry no id; the referenced container, collected through its referrer, is the figure leg's reference case); one under g, a, switch or a nested svg is; a stand-in whose parents carry no namespace is decided by the browser's answer and the walk alone", () => {
  const probed: string[] = [];
  const probe = (url: string): Picture => { probed.push(url); return new FakePic(); };
  const svgNode = (localName: string, parentElement: PrintableNode | null = null): PrintableNode & { namespaceURI: string } => hideEdges({ localName, parentElement, hasAttribute: () => false, namespaceURI: SVG_NS });   // built as `node` builds an ancestor (a spread of one would drop the edges hideEdges hides)
  const svgRoot = svgNode("svg", node("div"));
  const rendersTo = (container: string, href: string): FakeEl => elm({ href }, false, undefined, svgNode(container, svgRoot), "image", { cv: true, rects: 1 });   // Firefox's and WebKit's reading: a rect and visible
  const never = ["defs", "symbol", "clipPath", "mask", "pattern", "marker", "metadata"].map((c) => rendersTo(c, c + ".svg"));
  const renders = ["g", "a", "switch", "svg"].map((c) => rendersTo(c, c + ".svg"));
  const deep = elm({ href: "deep.svg" }, false, undefined, svgNode("g", svgNode("defs", svgRoot)), "image", { cv: true, rects: 1 });   // a rendering group inside a container that never renders
  const bare = elm({ href: "bare.svg" }, false, undefined, node("defs", [], node("svg")), "image", { cv: true, rects: 1 });   // a stand-in with no namespace: the walk reads SVG containers alone
  const pics = collectPictures(fakeBody({ img: [], "video[poster]": [], image: [...never, ...renders, deep, bare] }), "http://notes-api.test/files", probe);
  assert.deepEqual(probed, ["http://notes-api.test/g.svg", "http://notes-api.test/a.svg", "http://notes-api.test/switch.svg", "http://notes-api.test/svg.svg", "http://notes-api.test/bare.svg"], "the images under a rendering container alone, and the namespace-less stand-in");
  assert.equal(pics.length, 5);
});

// the author's closing pass over round 8 (2026-09-21): the reference walk's shapes the figure leg does not measure, over stand-ins.
// The leg's reference case holds the direct reference (a referrer in rendering content naming a container inside <defs>) and
// the pattern inherited through href to the ink per engine; the nested, the capped and the cyclic shapes are the rule's own
// statement, executed here: a reference from inside another container's content is followed to REFERENCE_DEPTH references,
// a chain past the cap is not collected, and a cycle ends at the cap and collects nothing (the verifiers' r8v-A-E-1 and
// r8v-A-E-2: the inheriting pattern painted in every engine and was collected in none, and the recursive clause was executed
// by no test)
test("svgReachesPaper over stand-ins: an image inside a pattern a printable rect fills is collected; one inside a pattern that an empty second pattern inherits through href, the rect filling the second, is collected (the alias walk, paintingIds; a mask has no href); a reference from inside a mask's content is followed, so a pattern referenced by a rect inside a mask that a printable rect references is collected at two references, and at four; a chain of five references is past the cap and not collected; a cycle of references between a pattern and a mask, referenced by nothing in rendering content, ends at the cap and collects nothing; and a fallback after the url() is not read", () => {
  const probed: string[] = [];
  const probe = (url: string): Picture => { probed.push(url); return new FakePic(); };
  type SvgStandIn = PrintableNode & { namespaceURI: string; getAttribute(name: string): string | null };
  const svgEl = (localName: string, attrs: Record<string, string>, parentElement: PrintableNode | null): SvgStandIn => hideEdges({ localName, parentElement, namespaceURI: SVG_NS, hasAttribute: (k) => k in attrs, getAttribute: (k) => (k in attrs ? attrs[k] : null), checkVisibility: () => true, getClientRects: () => ({ length: 1 }) });
  const root = svgEl("svg", {}, node("div"));
  const patterns: SvgStandIn[] = [], referrers: SvgStandIn[] = [], images: FakeEl[] = [];
  /** A pattern of id `id` under the root holding an image of `href`. */
  const pattern = (id: string, href: string): SvgStandIn => { const p = svgEl("pattern", { id }, root); patterns.push(p); images.push(elm({ href }, false, undefined, p, "image", { cv: true, rects: 0 })); return p; };
  /** A mask of id `id` under the root, empty until a referrer is placed in it. */
  const mask = (id: string): SvgStandIn => svgEl("mask", { id }, root);
  /** A rect carrying `attrs` under `parent` (the root, in rendering content, or a container). */
  const rect = (attrs: Record<string, string>, parent: SvgStandIn = root): SvgStandIn => { const r = svgEl("rect", attrs, parent); referrers.push(r); return r; };
  // direct: a printable rect fills the pattern
  pattern("p1", "direct.svg"); rect({ fill: "url(#p1)" });
  // inherited: an empty pattern q2 inherits p2's content through href, and the rect fills q2
  pattern("p2", "inherited.svg"); const q2 = svgEl("pattern", { id: "q2", href: "#p2" }, root); patterns.push(q2); rect({ fill: "url(#q2)" });
  // a mask has no href: a mask "inheriting" a pattern through href is no alias, so its referrer reaches nothing
  pattern("p2b", "mask-href.svg"); const m2b = svgEl("mask", { id: "m2b", href: "#p2b" }, root); patterns.push(m2b); rect({ fill: "url(#m2b)" });
  // nested, two references: a rect inside mask m3 fills p3, and a printable rect is masked by m3
  pattern("p3", "nested-2.svg"); const m3 = mask("m3"); rect({ fill: "url(#p3)" }, m3); rect({ mask: "url(#m3)" });
  // nested, four references (the cap): p4 <- rect in m4a <- rect in m4b <- rect in m4c <- printable rect
  pattern("p4", "nested-4.svg"); const m4a = mask("m4a"), m4b = mask("m4b"), m4c = mask("m4c"); rect({ fill: "url(#p4)" }, m4a); rect({ mask: "url(#m4a)" }, m4b); rect({ mask: "url(#m4b)" }, m4c); rect({ mask: "url(#m4c)" });
  // five references: one past the cap
  pattern("p5", "nested-5.svg"); const m5a = mask("m5a"), m5b = mask("m5b"), m5c = mask("m5c"), m5d = mask("m5d"); rect({ fill: "url(#p5)" }, m5a); rect({ mask: "url(#m5a)" }, m5b); rect({ mask: "url(#m5b)" }, m5c); rect({ mask: "url(#m5c)" }, m5d); rect({ mask: "url(#m5d)" });
  // a cycle: p6's content is masked by m6, m6's content fills p6, and nothing in rendering content names either
  const p6 = pattern("p6", "cycle.svg"); const m6 = mask("m6"); rect({ mask: "url(#m6)" }, p6); rect({ fill: "url(#p6)" }, m6);
  // a fallback after the url(): not read
  pattern("p7", "fallback.svg"); rect({ fill: "url(#p7) red" });
  const body = { querySelectorAll: (sel: string) => (sel === "image" ? images : sel === "pattern" ? patterns : sel === "img" || sel === "video[poster]" ? [] : referrers) as unknown as NodeListOf<Element> } as unknown as ParentNode;
  const pics = collectPictures(body, "http://notes-api.test/files", probe);
  assert.deepEqual(probed, ["http://notes-api.test/direct.svg", "http://notes-api.test/inherited.svg", "http://notes-api.test/nested-2.svg", "http://notes-api.test/nested-4.svg"], "collected: the direct reference, the pattern inherited through href, and the nested references within the cap; not collected: the mask named by href (no alias), the chain past the cap, the cycle and the fallback spelling");
  assert.equal(pics.length, 4);
  assert.equal(REFERENCE_DEPTH, 4, "the cap the chain of five is past and the chain of four is within");
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
// SECOND, EVERY MEMBER CALL AND EVERY MEMBER WRITE in the file on ANY receiver, by the compiler's tree (seatSites), each
// axis the read stands on an allowlist with its default refusing (the branch's verification pass finding census-1, 2026-09-20, and
// the round-6 review's clusters A to C, 2026-09-20: inverting a default is not one edit, every axis the guard reads on is
// inverted with it, or the closed list moves to the axis left alone). THE CALL AXIS: a call of a method that seats a node
// (SEAT_CALLS: the six the body's read resolves; replaceWith, after, before, replaceChild and insertAdjacentHTML; a range's
// insertNode and surroundContents; setHTMLUnsafe; moveBefore; write and writeln) and an assignment to innerHTML or
// outerHTML (SEAT_ASSIGNS) are SEATS; a call, apply or bind, a mount or render, any method of Object, Reflect or Function
// (SITE_CALLS, SITE_RECEIVERS) and an add on a receiver that is neither a DOMTokenList nor a Set are calls read BY THEIR
// SITE; a method by a name NON_SEATING_METHODS lists, each read by hand as seating nothing, passes; and a method by ANY
// OTHER NAME fails the census with its line. THE ASSIGNMENT AXIS (the round-6 review's cluster B: before this the second read
// knew innerHTML and outerHTML and passed every other write on any receiver unread, so `md.innerText = ...`, a
// computed-name write `md[k] = html` and `document.body = ...` were neither a seat nor a refusal): every assignment, plain
// or compound, a `++` or `--`, each target of an array or object pattern and a for-of or for-in head, on any receiver but
// the `body` token (the first read's), is classed by the member's NAME: a seat (SEAT_ASSIGNS, a site the table must list),
// a name NON_SEATING_WRITES lists, each read by hand as seating no element (an on<event> handler among them, whose value
// must be a function: a string there runs as code), or a refusal with its line, a computed name (`md[k] = ...`, `md["inner"
// + "HTML"] = ...`) refused wherever it stands. THE RECEIVER AXIS: a seat whose receiver is the sanctioned `body` token (the
// identifier, a non-null `!` allowed) was the first read's; EVERY OTHER SEAT and every site-read call passes only as a SITE
// the census lists, read by hand (SEATS_READ_BY_HAND), KEYED ON THE SEAT (the round-6 review's cluster A: keyed on the
// enclosing function, the receiver's spelling and the form alone, one entry admitted every seat sharing that triple, so a
// second call on a listed receiver seated an unlisted root in the viewer's body under an entry hand-read at another seat,
// and the entry for a `let` receiver pinned its declaration and nothing about what it held at the seat): an entry is ONE
// seating call or assignment, its enclosing function's name, the receiver's spelling, the form, WHAT IT SEATS (the seated
// arguments as spelled, or the value assigned; for a site-read call every argument, since where it seats into is among
// them), and, for a receiver that is a bare name, the DECLARATION it is bound to, with what the receiver is and so why its
// seat lands no child in the body; two seats at one site are two entries, since one entry is one seat SPELLING, and a seat
// spelled byte for byte alike in two branches of one function declares `times` and is read at each; an entry two seats match
// fails unless it says so; a
// second declaration of a listed name inside the entry's function (a block's `const main = md.parentElement!`, a
// callback's `(main) =>`) fails with its line rather than passing under the entry's claim (the branch's verification pass
// finding census-2); each seated argument that is a bare name is held to ITS declaration too (`seatedBy`; the verifiers'
// census-2 of the round-7 build, 2026-09-20: the seated name was matched by its spelling alone, so a block's `const body =
// el("div", "fileview-mutant")` seated through the listed `main.appendChild(body)` wore the entry), a declaration named
// `body` passes only as the viewer's own `el("div", "fileview-body")` or as the parameter of a callee BODY_HANDED_TO lists as
// reading the body under its own parameter, and a listed name declared twice in the entry's function fails at every seat,
// hand-off or URL write it stands at, whatever the second declaration spells (a shadow wearing the listed declaration's exact
// text passed the text compare); THE RECEIVER'S HOLD IS BY BINDING, NOT NAME (the maintainer's round-8 question, 2026-09-21,
// after PR 850's census read a synthetic local named `p` as a kernel path, a silent false match; answered by executing 23
// plants at the round-7 head, 13 refused with the planted line and 10 passed as expected, the 13 loud ones kept as this
// module's binding case beside two of the passing ones and the residue plant named below): an entry is addressed by the tuple (the enclosing function's NAME, the receiver's spelling, the form, the
// seated arguments), and the receiver is then resolved to its DECLARATION by the language's scopes (bindingOf: the innermost
// scope declaring the name, a block, a function's parameters, a for or catch clause, the module), never by its name, and
// held to the entry by that declaration's text (`decl`) and the per-function declaration count (shadowOf), so a same-named
// local in another function is another entry's `in` and an unlisted seat there, never read under the listed function's
// entry, with or without `times`; a listed name declared twice in the entry's function, in a block, an unnamed callback or a
// callback's parameter, is refused at every seat of the name whatever `times` says and whatever the second declaration
// spells; two functions' entries with their declarations swapped are refused at both seats naming both declarations; and a
// string, a comment or a property key (`q.p`) is no declaration. Two things stay keyed on TEXT, each reached only through
// the author's own hand (a `times` written over same-named functions, or a declaration spelled exactly as the listed one
// whose meaning changed underneath it): the `in` is the nearest named function's bare name, which two distinct function
// nodes can share (`apply` is such a name in file-view.ts, textSizeControl's inner arrow and githubLinkAction's method), so
// their same-spelled seats collapse to one key that reds the count unless the entry says `times`, and with `times` reads N
// seats across the same-named functions held to equal declaration text rather than to one node; and the hold is on the
// declaration's TEXT, so a same-spelled declaration whose `el` is rebound in the function, or a same-spelled declaration
// added inside the nested named function an entry names while the enclosing function keeps the listed one (the binding moves
// inward, the reported declaration text does not, and nothing refuses), passes under the listed text: the plants k4 and k4'
// below pass, k4'' with another text inside refuses naming both. The text held is the WHOLE of it (the initializer, a loop's
// head, an unnamed callback's call, and the argument axis's hand-off and callee texts; a text over 300 characters is held as
// its first 80 characters beside the sha256 of the whole flattened text, the text as the census reads it with comments blanked
// and whitespace collapsed to single spaces, so the digest is recomputed from that text and not from the file's raw bytes;
// openFileView's `ctx` initializer the one such text in the tables today, both held by the mutants case, which recomputes the
// digest from the flattened initializer and counts the hashed fields across the three tables), since a third road, the hold on
// the initializer's first 80 characters, let two initializers alike to there pass under one listed text; the maintainer's
// round-8 ruling of 2026-09-21 closed it, and the plants m1 to m7 below execute, at every held text, the refusal under a text
// cut at 80 and the pass under each whole text (the initializer m1 and m1', the hash form m2 and m2', a loop's head m3, an
// unnamed callback's call m4, a hand-off's argument m5 and m5b and callee m6, a hashed argument m7); and a receiver bound
// by `let` or `var`, or a parameter written to, is REASSIGNABLE and its seat fails
// unless the entry pins what the binding HOLDS (`holds`: the one expression every write to it in the file assigns), since
// its declaration says nothing about what it holds at the seat (the round-6 review's correctness-5; the viewer's session
// tag moved from a `let` onto a const for it). Object, Reflect and Function are read BY THEIR BINDING (globalOf: the bare
// global, an alias `const R = Reflect`, `globalThis.Reflect`) and pass in ONE position alone, the receiver of a member
// call, which is then a site the table must list; every other read of one (the alias declaration itself, a stored method
// `const s = Reflect.set`, an argument, an array element, a return) fails with its line (the round-6 review's cluster C:
// before this the global was known by its receiver's spelling, so `const R = Reflect; R.set(md, "innerHTML", x)` and
// `window.Reflect.set(...)` passed with no site and no refusal, while the header claimed every such read failed). And the
// census FAILS with its line otherwise, whatever produced the receiver: `body.querySelector(...)!.parentElement!.append(x)`,
// a stored query result (`const md2 = body.querySelector(...); md2!.append(x)`), `md.parentElement!.append(x)`, a parent
// held in a variable, `body.closest(...)!.append(x)`, `body.getRootNode().appendChild(x)`, a node read inside a listener
// and seated, `(body).append(x)`, an alias's seat, a range's `insertNode`, `setHTMLUnsafe`, `moveBefore`,
// `Object.assign(md, { innerHTML })`, `Reflect.set(md, "innerHTML", ...)`, a second `main.appendChild(x)` beside the
// listed one. A seating or site-read method READ WITHOUT BEING CALLED fails with its line (`md.append.call(md, x)`,
// `Element.prototype.append.call(md.parentElement, x)`, `Reflect.apply(md.append, ...)`, a bound seat, `const f =
// md.append`, `md["append"]`, a destructuring `const { append: f } = md`: it runs later where the census cannot read its
// receiver); a call through a computed name (`x["append"](...)`, `x[m](...)`) fails wherever it stands, since the census
// cannot read what it calls; a call whose callee is neither a name nor a member (`(md.append)(x)`, a call's value called)
// fails; and a member read by a computed name and STORED or handed on (`const f = md[m]`) passes only as a site
// INDEX_READS_BY_HAND lists (its function and receiver, with what the receiver is), where one only compared, tested or
// read further (`rows[i].id`) is an index read and passes. THE ARGUMENT AXIS (the round-6 review's item 7, 2026-09-20; its
// first run at the round-7 head, with the tables empty, is recorded in the plan's P7): a node of the tree (a NODE_MEMBERS
// chain, an index into one, or a name bound to either) handed to ANY callee, and an element the census can see by its
// shape (`el(...)`, a createElement, querySelector, closest, getElementById or cloneNode result, a local builder's result,
// a parameter typed as an element or a node, or a name bound to any of these) handed to a callee THIS FILE DOES NOT
// DECLARE (an import or a global; a member call is the call axis's, passed by its name or listed with its arguments as a
// site), each read where it stands bare and inside an object literal, an array literal, a spread or a concise arrow's
// value, passes only as a site ARGS_READ_BY_HAND lists (the function, the callee, the argument as spelled with its path
// into the literal, a bare name's declaration, a reassignable one held to what it holds; one entry per hand-off, `times`
// for one spelled alike in two branches), each read by hand for what the callee does with the node (the verifiers'
// records-1 and census-3 of the round-7 build, 2026-09-20: before this the axis knew NODE_MEMBERS chains handed bare, so
// an imported helper handed the card, the bar or the markdown root, and a node inside an object literal, were read on no
// axis while the promise named every axis); and AN ARGUMENT THE CENSUS CANNOT NAME BY SHAPE handed to a callee this file
// does not declare is refused by the compiler's TYPE when that type can hold a node (a member assignable to Node or that
// Node is assignable to, or any or unknown, which the compiler cannot vouch for) unless ARGS_READ_BY_HAND lists it marked
// `unnamed`, the mark held to the road that reads it, so the two populations never blur (the round-8 fixes, the round-7
// review's tests-2 and regression-1, 2026-09-21: the shape rule enumerated on the unsafe side and PASSED what it could
// not name, and the merge deleted the entry reading the sanitized body handed to gateRemoteFigures rather than repointing
// it, so two live hand-offs were read on no axis; a function expression, a string literal and a chain on the `body` token
// are not asked, the last being the first read's); a bare eval, setTimeout, setInterval or Function (by binding) with a first
// argument that is not a function, `new Function` and `import(...)` are string roads and fail; and a destructuring by a
// computed key fails. THE URL AXIS (the URL roads; its name until the round-8 fixes was the one the assignment roads' code
// also used, and the round-7 review's extra5-1 found two of the axes under one name, so that name is retired from this module's
// vocabulary and each axis is named for what it classifies, 2026-09-21; the verifiers' census-1 and census-4 of the round-7 build, 2026-09-20:
// before this the axis read the assignment spelling alone, so `a.setAttribute("href", x)`, `location.replace(x)` under
// String.prototype.replace's listing and `window.open(x)` under the browser's `open` passed): a URL written from a value
// that is not a literal, or from a javascript: literal, passes only as a site URL_WRITES_READ_BY_HAND lists (the function,
// the target, the value as spelled and a bare name's declaration; one entry per write), each read by hand for whether the
// value can carry a remote URL, whether that road reaches the network and when, and what gates it, where a URL is written
// by an assignment to a member the assignment axis's hand read flags as a URL (NON_SEATING_WRITES' `url`: href, src) or to
// a member of `location`, by setAttribute or setAttributeNS under any name but an `aria-*` or `data-*` one (neither fetched
// nor navigated by) or one NON_URL_ATTRS lists as carrying no URL, by a CSS property written through an element's `style`
// (an assignment through `style`, or `style.setProperty`, its value read like setAttribute's) under any name but one
// NON_URL_STYLE_PROPS lists by hand as taking no url() value (a computed property name refused whatever the value; the
// round-8 fixes, the round-7 review's correctness-2, 2026-09-21: before this a write through `style` passed on the
// assignment axis by the rule and `setProperty` by its listing, so `el.style.backgroundImage = "url(" + x + ")"`,
// `el.style.cssText = ...` and `el.style.setProperty("background-image", ...)` reached the network with no hand read while
// `el.setAttribute("style", ...)` was refused), by a method of `location` (assign, replace or reload, its own navigations;
// every other method on a receiver whose chain names `location` is the call axis's and a seat there is refused as a seat:
// the round-8 fixes, the round-7 review's correctness-1, before which an else-if chain let the URL arm, keyed on the
// receiver alone, swallow `append`, `setHTMLUnsafe` and every other method there, a literal first argument recording nothing)
// or by `window.open` (the global's `open` by binding), each call's first argument the value; and a setAttribute or
// setAttributeNS whose NAME is not a string literal (a constant resolved through its declaration counts as one) or names an
// on<event> handler passes only as a site ATTR_NAMES_READ_BY_HAND lists. A listed site the source no longer has fails too (a
// stale entry is removed, never kept). The resolved set is then held equal to the flow's three lists (READY_ROOTS, NOT_READY_ROOTS, LINE_ROOTS) and
// bodyReady is executed over each root as its list says. Each seated expression resolves as before: a builder call
// (`mdBlock(...)`) to the `el(...)` EVERY return of the builder names, each return read from the compiler's tree (a nested
// function's excluded), a return of anything but a bare name refused, and the roots united; a bare variable to the ONE
// expression assigned to it in its declaring block, its initializer or its one assignment, a name assigned an element more
// than once there refused, a null or undefined write not counted (the round-8 fixes, the round-7 review's extra9-1, 2026-09-21: before this the builder's LAST line-anchored
// `return <name>;` alone was read, so a root seated through an early return, a guarded one-liner among them, was neither
// derived nor refused, and a bare name resolved to the last textual assignment before the site, so a branch's assignment
// was passed over); a ternary to both its branches; an `el("<tag>", "<class>")` to itself; anything else fails with the
// expression.
// WHERE THIS MODULE LIVES (the maintainer's round-8 ruling on cluster C, 2026-09-21): the census builds a TypeScript PROGRAM
// over the viewer (ts.createProgram, programOver) and runs under npm test in vscode-extension, where node_modules stands, so it
// is permanently a vscode-extension-leg module; no part of it moves under tools/. The record module there
// (tools/markdown-viewer-plan-print-record.test.mjs) runs in CI's shell job with NO node_modules and reaches no compiler, and
// its isolation guard (tools/markdown-viewer-plan-print-record-isolation.test.mjs, a child run from a mirror without
// node_modules) refuses any road to one, so the two modules' claims are one split, this module executing what needs the
// compiler and that one holding the same sentences by text, never a contradiction.
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
const VIEWER_PATH = path.resolve(process.cwd(), "..", "ui", "webview", "file-view.ts");
const VIEWER_RAW = fs.readFileSync(VIEWER_PATH, "utf8");
const VIEWER_SRC = stripComments(VIEWER_RAW);
/** A TypeScript PROGRAM over `src` standing as file-view.ts (the round-8 fixes, the round-7 review's tests-2 and regression-1,
 *  2026-09-21: the argument axis names an element by its shape and passed what it could not name, so the compiler's TYPE is
 *  the namer of last resort now, seatSites.unnamedShape). The host serves `src` for file-view.ts's own path and the disk for
 *  every other file, so a mutant of the viewer type-checks against the real modules it imports; the options are
 *  vscode-extension's (strict, the DOM lib, `paths` into its node_modules for marked's types). ONE program per distinct
 *  source text (the maintainer's round-8 ruling on cluster C: the mutant case calls the census over the live source many
 *  times and over each mutant once, and a program per call took the case from 116 s to 288 s in the probe), the parsed
 *  files other than file-view.ts cached across programs and the last program handed to the next as its predecessor. This
 *  module reaches the compiler under npm test with node_modules present: see the census header's rider on where it lives. */
const PROGRAM_OPTIONS: ts.CompilerOptions = { target: ts.ScriptTarget.ES2021, lib: ["lib.es2021.d.ts", "lib.dom.d.ts", "lib.dom.iterable.d.ts"], strict: true, module: ts.ModuleKind.CommonJS, moduleResolution: ts.ModuleResolutionKind.Node10, esModuleInterop: true, skipLibCheck: true, noEmit: true, types: [], baseUrl: process.cwd(), paths: { "*": ["node_modules/*"] } };
const programFiles = new Map<string, ts.SourceFile>();
let lastProgram: { src: string; program: ts.Program } | null = null;
function programOver(src: string): ts.Program {
  if (lastProgram !== null && lastProgram.src === src) return lastProgram.program;
  const host = ts.createCompilerHost(PROGRAM_OPTIONS, true);
  const fromDisk = host.getSourceFile;
  host.getSourceFile = (fileName, languageVersion, onError, shouldCreateNewSourceFile) => {
    if (path.resolve(fileName) === VIEWER_PATH) return ts.createSourceFile(fileName, src, languageVersion, true, ts.ScriptKind.TS);
    const hit = programFiles.get(fileName);
    if (hit) return hit;
    const read = fromDisk.call(host, fileName, languageVersion, onError, shouldCreateNewSourceFile);
    if (read) programFiles.set(fileName, read);
    return read;
  };
  const program = ts.createProgram([VIEWER_PATH], PROGRAM_OPTIONS, host, lastProgram?.program);
  lastProgram = { src, program };
  return program;
}
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
    // every return of the builder, read from the compiler's tree (the round-8 fixes, the round-7 review's extra9-1: a
    // line-anchored regex read the LAST `return <name>;` alone, so a root returned early, `if (x) return early;` among them,
    // was neither derived nor refused); a return inside a nested function is that function's; a return of anything but a
    // bare name is refused, which the census turns into a refusal with the seat's line
    const sf = programOver(src).getSourceFile(VIEWER_PATH)!;
    const fn = sf.statements.find((s): s is ts.FunctionDeclaration => ts.isFunctionDeclaration(s) && s.name !== undefined && s.name.text === call[1]);
    assert.ok(fn !== undefined && fn.body !== undefined, "the builder " + call[1] + " is a top-level function of file-view.ts");
    const returns: ts.ReturnStatement[] = [];
    const walk = (n: ts.Node): void => { if (ts.isFunctionLike(n)) return; if (ts.isReturnStatement(n)) returns.push(n); ts.forEachChild(n, walk); };
    ts.forEachChild(fn.body, walk);
    assert.ok(returns.length >= 1, "the builder " + call[1] + " returns a value");
    const roots = new Set<string>();
    for (const r of returns) {
      assert.ok(r.expression !== undefined && ts.isIdentifier(r.expression), "the builder " + call[1] + " returns a bare name at every return, and line " + (sf.getLineAndCharacterOfPosition(r.getStart(sf)).line + 1) + " returns `" + (r.expression ? r.expression.getText(sf).replace(/\s+/g, " ") : "") + "`, which the census cannot resolve: a builder's root is read from the name each return hands back");
      for (const root of rootsOf(src, r.expression.text, r.getStart(sf))) roots.add(root);
    }
    return [...roots];
  }
  const name = /^(\w+)$/.exec(e);
  if (name) {
    // the ONE expression the name is bound to in its declaring block (the round-8 fixes, extra9-1: before this the last textual
    // assignment before the site was taken, so a branch's assignment was passed over): the declaration the compiler resolves the
    // name to from the site, its initializer and every assignment to that binding inside the block that declares it, nested
    // functions included; a nullish write (`null`, `undefined`) assigns no element and is not counted (the viewer's fallback
    // textarea is null-initialised, assigned its element once and nulled on exit); more than one element write is refused,
    // since the census cannot say which the seat sees; none is refused as before
    const program = programOver(src), sf = program.getSourceFile(VIEWER_PATH)!, checker = program.getTypeChecker();
    let at: ts.Node = sf;
    for (;;) { const child = ts.forEachChild(at, (c) => (c.getFullStart() <= before && before < c.getEnd() ? c : undefined)); if (!child) break; at = child; }
    const sym = checker.resolveName(name[1], at, ts.SymbolFlags.Variable, false);
    const decl = sym?.declarations?.find((d): d is ts.VariableDeclaration => ts.isVariableDeclaration(d));
    assert.ok(decl !== undefined, "the variable " + name[1] + " is assigned before the site at " + before);
    let block: ts.Node = decl.parent;
    while (!ts.isBlock(block) && !ts.isSourceFile(block) && !ts.isFunctionLike(block)) block = block.parent;
    const peelCast = (x: ts.Expression): ts.Expression => { let r = x; while (ts.isAsExpression(r) || ts.isParenthesizedExpression(r) || ts.isNonNullExpression(r) || ts.isSatisfiesExpression(r)) r = r.expression; return r; };
    const writes: Array<{ text: string; at: number; line: number }> = [];
    if (decl.initializer) writes.push({ text: peelCast(decl.initializer).getText(sf).replace(/\s+/g, " "), at: decl.initializer.getStart(sf), line: sf.getLineAndCharacterOfPosition(decl.getStart(sf)).line + 1 });
    const collect = (n: ts.Node): void => {
      if (ts.isBinaryExpression(n) && n.operatorToken.kind === ts.SyntaxKind.EqualsToken) { const l = peelCast(n.left); if (ts.isIdentifier(l) && checker.getSymbolAtLocation(l) === sym) writes.push({ text: peelCast(n.right).getText(sf).replace(/\s+/g, " "), at: n.right.getStart(sf), line: sf.getLineAndCharacterOfPosition(n.getStart(sf)).line + 1 }); }
      ts.forEachChild(n, collect);
    };
    collect(block);
    const elementWrites = writes.filter((w) => w.text !== "null" && w.text !== "undefined");
    assert.ok(elementWrites.length >= 1, "the variable " + name[1] + " is assigned before the site at " + before);
    assert.ok(elementWrites.length === 1, "the variable " + name[1] + " is assigned " + elementWrites.length + " times in the block that declares it (lines " + elementWrites.map((w) => w.line).join(", ") + "; a null or undefined write is not counted), so it resolves to no one expression at the seat: a bare seated name assigned more than once where it is declared is refused (seat each branch's own element, or bind the name once)");
    return rootsOf(src, elementWrites[0].text, elementWrites[0].at);
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
function census(src: string, table: SeatRead[] = SEATS_READ_BY_HAND, indexTable: IndexRead[] = INDEX_READS_BY_HAND, argTable: ArgRead[] = ARGS_READ_BY_HAND, urlTable: UrlWriteRead[] = URL_WRITES_READ_BY_HAND, attrTable: AttrNameRead[] = ATTR_NAMES_READ_BY_HAND): { seated: Map<string, number[]>; refused: string[] } {
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
          try { roots = rootsOf(src, arg, at); } catch (e) { refused.push("line " + line + ": " + use + "(...) seats `" + arg + "`, an expression the census cannot resolve to a root (" + (e as Error).message + "): a spread, a call it does not know, a variable assigned where it cannot read"); continue; }   // the branch's verification pass finding census-4: before this the resolver threw, naming the expression and not its line
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
  // the second read: every seat, every member call and every member write in the file, on any receiver; the sanctioned
  // `body` token's were read above; a seat or a site-read call passes only as the ONE seat an entry of the table reads (the
  // round-6 review's cluster A: keyed on the seat, held to one binding, a reassignable binding held to what it holds), a
  // method passes only by a name read by hand, a write only by a name read by hand (cluster B), a reflection global only
  // as a listed call's receiver (cluster C), a stored index read only as a site listed, and everything else fails with its line
  const second = seatSites(src);
  const form = (via: string): string => via.replace(/ (\S*=)$/, " $1 ...");
  const used = new Map<SeatRead, number[]>();   // per entry, the lines of the seats it matched: one entry is one seat
  const writesText = (b: Partial<Binding>): string => (b.writes ?? []).map((w) => "`" + w.text + "` at line " + w.line).join(", ") || "none";
  /** Why a bare name's binding cannot be read under an entry's claim, or null: a let or a var pins its declaration and not what
   *  it holds at the site, so it passes only when the entry's `holds` is what every write to it assigns (the initializer and
   *  each assignment); a parameter written to is reassignable the same way and has no expression to hold it to; a const
   *  written again (the compiler refuses it too) is refused. */
  const reassignable = (b: Partial<Binding>, holds: string | undefined, what: string): string | null => {
    if (b.kind === undefined || b.kind === "other") return null;   // a member chain or a global: no binding to read
    const writes = b.writes ?? [];
    if (b.kind === "const" || b.kind === "function" || b.kind === "import" || b.kind === "class") return writes.length > 1 ? what + " is bound by `" + b.decl + "` and written again (" + writesText(b) + "): the binding is not the one read by hand" : null;
    if (b.kind === "parameter") return writes.length ? what + " is bound by `" + b.decl + "`, a parameter written to (" + writesText(b) + "), a reassignable binding whose declaration says nothing about what it holds at the site" : null;
    if (holds === undefined) return what + " is bound by `" + b.decl + "`, a reassignable binding (" + b.kind + "; the writes: " + writesText(b) + ") whose declaration says nothing about what it holds at the site: list `holds` with the one expression every write assigns, or bind it by const";
    if (!writes.length || writes.some((w) => w.text !== holds)) return what + " is bound by `" + b.decl + "`, and the entry's `holds` (`" + holds + "`) is not what every write to it assigns (" + writesText(b) + "): the binding is not the one read by hand";
    return null;
  };
  for (const s of second.sites) {
    if (s.body) continue;
    const entry = table.find((e) => e.in === s.fn && e.on === s.on && e.via === s.via && e.seats === s.seats);
    if (!entry) {
      const near = table.filter((e) => e.in === s.fn && e.on === s.on && e.via === s.via);
      const wearing = near.length ? " (the table's " + (near.length === 1 ? "entry" : near.length + " entries") + " for `" + s.on + "." + form(s.via) + "` in " + s.fn + " seat" + (near.length === 1 ? "s" : "") + " " + near.map((e) => "`" + e.seats + "`").join(", ") + ", not this: a second seat at a listed site is a second entry, read by hand)" : "";
      if (SEAT_CALLS.includes(s.via) || s.assign) refused.push("line " + s.line + ": " + s.text + " seats `" + s.seats + "` on `" + s.on + "` by " + s.via + " in " + s.fn + ", a seat the census has not read by hand" + wearing + ": read the site for what " + s.on + " is (the body under another name, or a node whose seat lands as a child of the body, seats a root the lists must know) and what it seats, and list the seat in SEATS_READ_BY_HAND, or seat the body by its name");
      else refused.push("line " + s.line + ": " + s.text + " calls " + s.via + " on `" + s.on + "` into `" + s.seats + "` in " + s.fn + ", a call the census reads by its site (a call, apply or bind, a mount or render, a reflection global's method by its binding, an add on a receiver that is neither a class list nor a Set) and has not read by hand" + wearing + ": read it for what it runs and list the call in SEATS_READ_BY_HAND");
      continue;
    }
    used.set(entry, [...(used.get(entry) ?? []), s.line]);
    if (s.seatedBy !== entry.seatedBy) { refused.push("line " + s.line + ": " + s.text + " seats `" + s.seats + "` bound by `" + (s.seatedBy ?? "no bare name") + "`, where SEATS_READ_BY_HAND read `" + (entry.seatedBy ?? "no bare name") + "`: what is seated is not the binding read by hand (the entry names each seated bare name's declaration in `seatedBy`)"); continue; }
    if (s.decl !== undefined && s.decl !== entry.decl) { refused.push("line " + s.line + ": " + s.text + " seats on `" + s.on + "` in " + s.fn + ", bound to `" + s.decl + "`, where SEATS_READ_BY_HAND read `" + (entry.decl ?? "no binding") + "`: the receiver is not the one read by hand"); continue; }
    if (s.shadowed) { refused.push("line " + s.line + ": " + s.text + " in " + s.fn + ": " + s.shadowed); continue; }   // the declarations' text agreed: a same-spelled second declaration is what the compare cannot see
    if (s.decl === undefined) continue;   // a member chain (`document.body`) has no binding; its spelling is the read
    const why = reassignable(s, entry.holds, "`" + s.on + "`");
    if (why) refused.push("line " + s.line + ": " + s.text + " seats on " + why);
  }
  for (const d of second.bodyDecls) refused.push("line " + d.line + ": " + d.text + " " + d.why);
  for (const [e, lines] of used) if (lines.length !== (e.times ?? 1)) refused.push("SEATS_READ_BY_HAND's entry `" + e.on + "." + form(e.via) + "` seating `" + e.seats + "` in " + e.in + " matches " + lines.length + " seats (lines " + lines.join(", ") + ") where it reads " + (e.times ?? 1) + ": one entry is one seat, read by hand where it stands; a seat spelled alike in two branches says `times` and is read at each");
  for (const c of second.computed) refused.push("line " + c.line + ": " + c.text + " calls through a computed name the census cannot read, and a seating method called that way seats where the census cannot follow");
  for (const u of second.unknown) refused.push("line " + u.line + ": " + u.text + " calls " + u.name + " on `" + u.on + "`, a method the census does not list as seating or as seating nothing: read it by hand and list it (SEAT_CALLS, SITE_CALLS or NON_SEATING_METHODS)");
  for (const h of second.handedOut) refused.push("line " + h.line + ": " + h.text + " reads the method " + h.name + " without calling it (a bare read, a call, bind or apply on it, an argument, a destructuring), and it runs later where the census cannot read its receiver");
  for (const o of second.oddCallee) refused.push("line " + o.line + ": " + o.text + " calls neither a name nor a member (a parenthesised expression, a call's value, an arrow), which the census cannot read");
  for (const i of second.indexReads) if (!indexTable.some((e) => e.in === i.fn && e.on === i.on)) refused.push("line " + i.line + ": " + i.text + " reads a member of `" + i.on + "` by a computed name and stores or hands it on, in " + i.fn + ": read the site for what " + i.on + " is and list it in INDEX_READS_BY_HAND, or read the member by its name");
  for (const e of table) if (!used.has(e)) refused.push("SEATS_READ_BY_HAND lists `" + e.on + "." + form(e.via) + "` seating `" + e.seats + "` in " + e.in + ", and the source has no such seat: the entry is stale, remove it or read the site again");
  for (const e of indexTable) if (!second.indexReads.some((i) => i.fn === e.in && i.on === e.on)) refused.push("INDEX_READS_BY_HAND lists `" + e.on + "` in " + e.in + ", and the source has no such stored index read: the entry is stale, remove it or read the site again");
  // the assignment axis (the round-6 review's cluster B): every member write on a receiver other than the body token passes by a
  // name read by hand (NON_SEATING_WRITES), a seat through the table above, a computed name never; a handler member holds a
  // function; a listed name the file no longer writes is stale
  for (const w of second.computedWrites) refused.push("line " + w.line + ": " + w.text + " writes a member of `" + w.on + "` by a computed name " + w.name + " in " + w.fn + ", which the census cannot read (innerHTML by any other spelling seats where no name says so): write the member by its name");
  for (const w of second.writes) if (w.through === undefined && !NON_SEATING_WRITES.some((e) => e.name === w.name)) refused.push("line " + w.line + ": " + w.text + " writes " + w.name + " on `" + w.on + "` in " + w.fn + ", a member the census does not list as a seat (SEAT_ASSIGNS) or as seating nothing (NON_SEATING_WRITES): read the member by hand for what its setter does and list its name, never pass it unread");
  for (const w of second.handlerStrings) refused.push("line " + w.line + ": " + w.text + " writes " + w.name + " on `" + w.on + "` in " + w.fn + " from a value that is not a function: a handler member holding a string runs it as code, a string road the census cannot read");
  for (const o of second.oddTargets) refused.push("line " + o.line + ": " + o.text + " writes to a target the census cannot read as a name or a member");
  for (const d of second.destructured) refused.push("line " + d.line + ": " + d.text + " destructures a member by a computed key, which the census cannot read (a seating method taken out that way runs where no name says so)");
  for (const e of NON_SEATING_WRITES) if (!second.writes.some((w) => w.through === undefined && w.name === e.name)) refused.push("NON_SEATING_WRITES lists " + e.name + ", and the source writes no such member on a receiver other than the body token: the entry is stale, remove it or read the write again");
  // the receiver axis (the round-6 review's cluster C): a reflection global passes as a listed call's receiver alone
  for (const r of second.reflectionReads) refused.push("line " + r.line + ": " + r.text + " reads " + r.name + (r.as === r.name ? "" : " (as `" + r.as + "`)") + " other than as the receiver of a member call: a reflection global stored, aliased, handed on or returned reaches any member by a string where the census cannot read the call");
  // the argument axis (the round-6 review's item 7): a node of the tree handed to ANY callee passes only as the site the table
  // lists (function, callee, the argument as spelled, a bare name's binding, a reassignable one held to what it holds); a
  // string road runs code the census cannot read; a URL member written from a value that is not a literal, or from a
  // javascript: literal, passes only as the site the table lists (function, target, the value as spelled, a bare name's
  // binding); an attribute set under a name the census cannot read as a literal, or naming a handler, passes only as a site
  // listed; a listed site the source no longer has fails too
  const argKey = (h: { fn: string; to: string; arg: string }, e: ArgRead): boolean => e.in === h.fn && e.to === h.to && e.arg === h.arg;
  for (const h of second.handedNodes) {
    const e = argTable.find((x) => argKey(h, x));
    if (!e) { refused.push("line " + h.line + ": " + h.text + " hands `" + h.arg + "`, a node of the tree read through " + h.member + (h.decl ? " (bound by `" + h.decl + "`)" : "") + ", to " + h.to + "(...) in " + h.fn + ", a callee the census has not read by hand for what it does with a node it is handed (it could seat the node in the body, or seat into it, where the census cannot follow): read it and list the site in ARGS_READ_BY_HAND, or read the node inside a call the census reads"); continue; }
    if (h.decl !== e.decl) { refused.push("line " + h.line + ": " + h.text + " hands `" + h.arg + "` bound to `" + (h.decl ?? "no binding") + "`, where ARGS_READ_BY_HAND read `" + (e.decl ?? "no binding") + "`: the argument is not the one read by hand"); continue; }
    if (h.shadowed) { refused.push("line " + h.line + ": " + h.text + " in " + h.fn + ": " + h.shadowed); continue; }
    const why = reassignable(h, e.holds, "`" + h.arg + "`");
    if (why) refused.push("line " + h.line + ": " + h.text + " hands " + why);
  }
  for (const e of argTable) { const n = [...second.handedNodes, ...second.elementsHanded].filter((h) => argKey(h, e)).length; if (n === 0) refused.push("ARGS_READ_BY_HAND lists `" + e.arg + "` handed to " + e.to + " in " + e.in + ", and the source has no such hand-off: the entry is stale, remove it or read the site again"); else if (n !== (e.times ?? 1)) refused.push("ARGS_READ_BY_HAND's entry `" + e.arg + "` handed to " + e.to + " in " + e.in + " matches " + n + " hand-offs where it reads " + (e.times ?? 1) + ": one entry is one hand-off, read where it stands; one spelled alike in two branches says `times` and is read at each"); }
  for (const r of second.stringRoads) refused.push("line " + r.line + ": " + r.text + " calls " + r.callee + " with a first argument that is not a function: a string road (eval, a timer's string, Function, import) runs code the census cannot read, and the kernel's page sends no script-src to stop it");
  const urlKey = (u: { fn: string; on: string; value: string }, e: UrlWriteRead): boolean => e.in === u.fn && e.on === u.on && e.value === u.value;
  for (const u of second.urlWrites) {
    const e = urlTable.find((x) => urlKey(u, x));
    if (!e) { refused.push("line " + u.line + ": " + u.text + " writes " + u.on + " from `" + u.value + "` in " + u.fn + ", a URL write (a member the assignment axis's hand read flags as a URL, a member of location, an attribute set under a name that is not aria-* or data-* and not listed as carrying no URL, a CSS property through style or style.setProperty not listed as taking no url(), a method of location, or window.open) from a value that is not a literal, or from a javascript: literal, and a javascript: URL runs code the census cannot read: read the site for what the value can be, whether it can carry a remote URL and what gates that road, and list it in URL_WRITES_READ_BY_HAND"); continue; }
    if (u.decl !== e.decl) { refused.push("line " + u.line + ": " + u.text + " writes from `" + u.value + "` bound to `" + (u.decl ?? "no binding") + "`, where URL_WRITES_READ_BY_HAND read `" + (e.decl ?? "no binding") + "`: the value is not the one read by hand"); continue; }
    if (u.shadowed) { refused.push("line " + u.line + ": " + u.text + " in " + u.fn + ": " + u.shadowed); continue; }
    const why = reassignable(u, e.holds, "`" + u.value + "`");
    if (why) refused.push("line " + u.line + ": " + u.text + " writes from " + why);
  }
  for (const e of urlTable) { const n = second.urlWrites.filter((u) => urlKey(u, e)).length; if (n === 0) refused.push("URL_WRITES_READ_BY_HAND lists `" + e.on + "` written from `" + e.value + "` in " + e.in + ", and the source has no such write: the entry is stale, remove it or read the site again"); else if (n !== (e.times ?? 1)) refused.push("URL_WRITES_READ_BY_HAND's entry `" + e.on + "` written from `" + e.value + "` in " + e.in + " matches " + n + " writes where it reads " + (e.times ?? 1) + ": one entry is one write, read where it stands; one spelled alike in two branches says `times` and is read at each"); }
  const attrKey = (a: { fn: string; on: string; name: string }, e: AttrNameRead): boolean => e.in === a.fn && e.on === a.on && e.name === a.name;
  for (const a of second.attrNames) if (!attrTable.some((e) => attrKey(a, e))) refused.push("line " + a.line + ": " + a.text + " sets an attribute on `" + a.on + "` in " + a.fn + " under a name (`" + a.name + "`) the census cannot read as a literal, or one naming an on<event> handler: a handler attribute holds a string that runs as code, a string road the census cannot read; read the site for what the name can be and list it in ATTR_NAMES_READ_BY_HAND, or name the attribute by a literal");
  for (const e of attrTable) if (!second.attrNames.some((a) => attrKey(a, e))) refused.push("ATTR_NAMES_READ_BY_HAND lists `" + e.name + "` set on `" + e.on + "` in " + e.in + ", and the source has no such write: the entry is stale, remove it or read the site again");
  for (const e of NON_URL_ATTRS) if (!second.attrWrites.some((a) => a.name === e.name)) refused.push("NON_URL_ATTRS lists " + e.name + ", and the source sets no such attribute from a value that is not a literal: the entry is stale, remove it or read the write again");
  for (const e of NON_URL_STYLE_PROPS) if (!second.styleWrites.some((w) => w.name === e.name)) refused.push("NON_URL_STYLE_PROPS lists " + e.name + ", and the source writes no such CSS property through style from a value that is not a literal: the entry is stale, remove it or read the write again");
  // an element the census can see by its shape, handed to a callee the file does not declare: read by hand and listed in
  // ARGS_READ_BY_HAND like a node of the tree (the verifiers' records-1 of the round-7 build)
  for (const h of second.elementsHanded) {
    const e = argTable.find((x) => argKey(h, x));
    if (!e) { refused.push("line " + h.line + ": " + h.text + " hands `" + h.arg + "`, " + h.member + (h.decl ? " (bound by `" + h.decl + "`)" : "") + ", to " + h.to + "(...) in " + h.fn + ", a callee this file does not declare and the census has not read by hand for what it does with an element it is handed (it could seat the element in the body, or seat into it, where the census cannot follow): read it and list the site in ARGS_READ_BY_HAND" + (h.unnamed ? ", marked `unnamed` (the shape rule cannot name it; the compiler's type is what refuses it)" : "")); continue; }
    if (h.decl !== e.decl) { refused.push("line " + h.line + ": " + h.text + " hands `" + h.arg + "` bound to `" + (h.decl ?? "no binding") + "`, where ARGS_READ_BY_HAND read `" + (e.decl ?? "no binding") + "`: the argument is not the one read by hand"); continue; }
    if (h.shadowed) { refused.push("line " + h.line + ": " + h.text + " in " + h.fn + ": " + h.shadowed); continue; }
    if (!!h.unnamed !== !!e.unnamed) { refused.push("line " + h.line + ": " + h.text + " hands `" + h.arg + "`, " + h.member + ", where ARGS_READ_BY_HAND's entry " + (e.unnamed ? "is marked `unnamed` and the census now names the shape" : "is not marked `unnamed` and the census cannot name the shape") + ": the two populations must not blur, so the mark follows the road that reads the hand-off"); continue; }
    const why = reassignable(h, e.holds, "`" + h.arg + "`");
    if (why) refused.push("line " + h.line + ": " + h.text + " hands " + why);
  }
  return { seated, refused };
}
/** The seating forms the census reads on ANY receiver, by the compiler's tree (seatSites): a call of a method that seats a node
 *  (SEAT_CALLS: the six SEATING resolves on the body; replaceWith, after, before, replaceChild and insertAdjacentHTML, which
 *  seat through the receiver's parent or replace the receiver's children; insertNode and surroundContents, which seat at a
 *  range; setHTMLUnsafe, which parses HTML in place; moveBefore, which moves a node in; write and writeln, which write the
 *  document) and an assignment (plain or compound) to innerHTML or outerHTML (SEAT_ASSIGNS), which parse HTML into element
 *  children. Every other member write is the assignment axis's (NON_SEATING_WRITES: passed by a name read by hand, refused
 *  otherwise; the round-6 review's cluster B, 2026-09-20: before this the two names stood as a closed list and the write
 *  axis knew no other member, so innerText and outerText, whose setters make element children too, and a computed-name
 *  write passed unread). */
const SEAT_CALLS = [...Object.keys(SEATING), "replaceWith", "after", "before", "replaceChild", "insertAdjacentHTML", "insertNode", "surroundContents", "setHTMLUnsafe", "moveBefore", "write", "writeln"];
const SEAT_ASSIGNS = ["innerHTML", "outerHTML"];
/** Which of a seating call's arguments each SEAT_CALLS name seats, the part of the call an entry of SEATS_READ_BY_HAND is
 *  keyed on (the round-6 review's cluster A): SEATING's six as the body's read has them; replaceWith, after, before, write
 *  and writeln every argument; replaceChild, insertNode, surroundContents, setHTMLUnsafe and moveBefore their first;
 *  insertAdjacentHTML its second (the first is the position). */
const SEATED_ARGS: Record<string, (args: string[]) => string[]> = {
  ...SEATING, replaceWith: (a) => a, after: (a) => a, before: (a) => a, write: (a) => a, writeln: (a) => a,
  replaceChild: (a) => a.slice(0, 1), insertNode: (a) => a.slice(0, 1), surroundContents: (a) => a.slice(0, 1), setHTMLUnsafe: (a) => a.slice(0, 1), moveBefore: (a) => a.slice(0, 1), insertAdjacentHTML: (a) => a.slice(1, 2),
};
/** The calls the census reads BY THEIR SITE like a seat, through SEATS_READ_BY_HAND (the branch's verification pass finding census-1,
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
 *  module handed nothing of the body. `add` passes by this name on a DOMTokenList (`classList`, `relList`, `part`) or a Set
 *  ALONE (seatSites.addSeatsNothing reads the receiver): an HTMLSelectElement's add and an HTMLOptionsCollection's add seat
 *  an option, so `add` on any other receiver is a call read by its site, listed in SEATS_READ_BY_HAND or refused (the
 *  round-6 review's extra6-4, 2026-09-20: the name stood here as seating nothing for every receiver, with no probe; the
 *  mutant case plants a select's add and reads the census red). THIS LIST SPEAKS OF THE CALL AXIS'S QUESTION ALONE, WHETHER A CALL SEATS, AND EXEMPTS
 *  NO VALUE READ (the maintainer's round-8 ruling on the round-7 review's correctness-2, 2026-09-21): a listed name says the
 *  call seats nothing, and what its arguments carry is read on the axis that reads values regardless of the listing. So `setProperty`
 *  stands here as seating nothing, and its VALUE is read on the URL axis by seatSites' style road like setAttribute's (a
 *  CSS property through `style.setProperty` is a URL write unless NON_URL_STYLE_PROPS lists the property); `setAttribute`
 *  stands here and its name and value are read on the URL axis; `assign` and `reload` are NOT here, and `replace` and
 *  `open` are (the string's replace, the browser's and the viewer's open), because the URL axis owns the (location,
 *  navigation-method) PAIRS and the global `open`, not the names: a call of `assign`, `replace` or `reload` on a receiver
 *  whose chain names `location`, and of `open` on the global (window, globalThis, self, or the bare name), is a navigation
 *  read as a URL write through URL_WRITES_READ_BY_HAND, and the call axis does not read those three pairs (listing `assign`
 *  or `reload` here instead would pass `x.assign(y)` on every receiver, the unsafe side; the verifiers' census-4 of the
 *  round-7 build, 2026-09-20: `location.replace(x)` passed under the string method's listing and `window.open(href, ...)`
 *  under the browser's). Every other method on a location-named receiver is this list's like any other receiver's (the
 *  round-8 fixes, the round-7 review's correctness-1). The body token's own calls are the first read's (NON_SEATING_CALLS,
 *  a shorter list). */
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
/** Every member file-view.ts WRITES (plain or compound) on a receiver other than the `body` token and other than a seat
 *  (SEAT_ASSIGNS), by the member's name, each read by hand as seating no element (the round-6 review's cluster B,
 *  2026-09-20: the assignment axis inverted like the call axis; the refuters' measure at the round-6 head was 47 distinct names
 *  over 225 writes, the census test's diagnostic prints the count derived at every run). A write by a name not here fails
 *  the census with its line until it is read and listed, whatever its receiver, and a listed name the file no longer writes
 *  fails as stale; a computed name is never listed. What a listed setter does is the hand read's claim, by name: text and
 *  attribute setters of the DOM, the fields of the viewer's own records (the format preference, the fetch verdict, the disk
 *  bar's state, the save hooks, a srcset candidate), and three handler members (onclick, onload, onerror) whose value the
 *  census holds to a function (a string there is a string road). The two URL members among them (href, src) are also the
 *  URL axis's read (URL_WRITES_READ_BY_HAND): the write seats nothing, what the value can be is read there. A write
 *  THROUGH an element's `style` (a CSS property) or `dataset` (a data attribute) passes ON THIS AXIS by that rule and not
 *  by its name (MemberWrite's `through`): neither object can hold an element child, whatever the property (the body's first
 *  read passes a further access on the same two, FURTHER_MEMBERS). The rule says nothing about the URL axis: a write through
 *  `style` from a value that is not a literal, or from a literal spelling `url(` or `javascript:`, is a URL write there
 *  unless NON_URL_STYLE_PROPS lists the property as taking no url() (the round-8 fixes, the round-7 review's correctness-2).
 *  The `body` token's own writes are the first read's (NON_SEATING_ASSIGNS, a shorter list that refuses textContent on the
 *  body). */
const NON_SEATING_WRITES: Array<{ name: string; why: string; url?: true }> = [
  // the DOM's text and attribute reflectors: none makes an element child
  { name: "textContent", why: "sets the element's text: one text node replaces its children, no element is made (on a body root it empties the root and seats nothing)" },
  { name: "title", why: "the tooltip text" },
  { name: "type", why: "a button's type attribute" },
  { name: "hidden", why: "the hidden attribute, a toggle" },
  { name: "disabled", why: "a button's disabled state" },
  { name: "id", why: "an element's id (the outline's rows, the overlay wrapper)" },
  { name: "tabIndex", why: "the tab order (the outline popover; the body's is the first read's)" },
  { name: "className", why: "the class list as one string (the `el` builder)" },
  { name: "value", why: "a textarea's text" },
  { name: "spellcheck", why: "a textarea's spellcheck attribute" },
  { name: "wrap", why: "a textarea's wrap attribute" },
  { name: "alt", why: "an img's alternative text" },
  { name: "download", why: "an anchor's download hint" },
  { name: "target", why: "an anchor's target window name" },
  { name: "rel", why: "an anchor's link relation" },
  { name: "href", url: true, why: "an anchor's URL: the write seats nothing; what the value can be is the URL axis's read (URL_WRITES_READ_BY_HAND)" },
  { name: "src", url: true, why: "a script's or a frame's or an img's URL: the write seats nothing; what the value can be is the URL axis's read (URL_WRITES_READ_BY_HAND)" },
  { name: "scrollTop", why: "a scroll offset (the outline popover's; the body's is the first read's)" },
  // handler members: the value is held to a function by the census (a string there is a string road)
  { name: "onclick", why: "the overlay wrapper's click handler, a function" },
  { name: "onload", why: "a chunk script tag's load handler, a function" },
  { name: "onerror", why: "a chunk script tag's error handler, a function" },
  // the viewer's own records (plain objects, not elements)
  { name: "md", why: "the format preference record's markdown mode (fmt)" },
  { name: "logWarning", why: "the save hooks' warning text from the kernel's reply (hooks, h)" },
  { name: "held", why: "the disk bar's record: whether it held the keyboard (diskBar, d)" },
  { name: "ring", why: "the disk bar's record: whether with the focus ring" },
  { name: "asked", why: "the disk bar's record: the fetch sequence its reload asked" },
  { name: "url", why: "a parsed srcset candidate's URL (c), a record parseSrcset built" },
  { name: "isText", why: "the fetch verdict record (v): a header's reading" },
  { name: "mtimeNs", why: "the fetch verdict record: the mtime header" },
  { name: "isImage", why: "the fetch verdict record: a content-type reading" },
  { name: "isPdf", why: "the fetch verdict record: a content-type reading" },
  { name: "isSvgImage", why: "the fetch verdict record: a content-type reading" },
  { name: "notUtf8", why: "the fetch verdict record: the UTF-8 header's reading" },
  { name: "bytes", why: "the fetch verdict record: the content length" },
];
/** One seat or site-read call in the viewer's source: its line, the nearest named function around it (`fn`: a declaration's,
 *  a variable's or a property's arrow or function expression, a method; `<module>` at the top level), the receiver as
 *  spelled with its OUTERMOST non-null `!` chain dropped and its whitespace collapsed to single spaces (`on`; an inner `!`
 *  and a cast stay in the spelling, so `(md as any).up!.append(x)` seats on `(md as any).up` and `a!.b.append(x)` on
 *  `a!.b`; the round-6 review's item 8), the form (`via`: the method's name, or `<member> <operator>` for an assignment,
 *  `innerHTML =` and `innerHTML +=` being two forms), WHAT THE SEAT SEATS (`seats`, the round-6 review's cluster A,
 *  2026-09-20: before this a site was its function, receiver and form, and one entry admitted every seat sharing that
 *  triple, so a second call on a listed receiver seated an unlisted root under an entry hand-read at another seat; now
 *  the seated arguments as spelled, joined by a comma and a space: for a seating call the arguments the form seats
 *  (SEATED_ARGS), for an assignment the value, and for a site-read call every argument, an object literal among them
 *  spelled by its property names (`{text, ext, onChange}`, a spread by its expression; the verifiers' census-3 of the
 *  round-7 build: `{...}` let a property added to a listed call pass as the same seat), an array literal or a function
 *  abbreviated to `[...]` or `() => ...`, since the claim there is about where the call seats into, an argument spelled
 *  by a name or a member), the binding of each seated argument that is a bare name (`seatedBy`, seatedBy: `name = decl`,
 *  a reassignable one with its writes, joined by "; "; the verifiers' census-2 of the round-7 build), why the receiver's
 *  or a seated name's binding cannot be held to one declaration (`shadowed`, shadowOf: the entry's function declares the
 *  name more than once), whether the form is an assignment (`assign`), the
 *  call or assignment's text, whether the receiver is the sanctioned `body` token (the identifier alone; `(body)` and a
 *  cast are not it), and, for a receiver that is a bare identifier, its BINDING (the branch's verification pass finding
 *  census-2, 2026-09-20): the declaration the name resolves to by the language's scopes (`decl`: the declaration as
 *  written, `const main = el("div", "fileview-main")`, a loop's `const a of fileViewActions`; "a parameter of <function>",
 *  or of "the callback handed to <call>" for an unnamed callback's, since what fills it is that call's; "a global" for a
 *  name the file never declares), where it stands (`bindingAt`), its KIND (`kind`: const, let, var, a parameter, a
 *  function, an import, a class) and every WRITE to it in the file (`writes`: the declaration's initializer, then each
 *  assignment, `++` or `--`, destructuring target or loop head that names it, each with its line; the round-6 review's
 *  correctness-5), so the table's entry, keyed on the seat, is held to ONE binding, a second declaration of the same name
 *  inside the entry's function (a block's `const main = md.parentElement!`, a callback's `(main) =>`) is refused rather
 *  than read under the entry's claim, and a REASSIGNABLE binding (a let or a var, a parameter written to) is refused
 *  unless the entry pins what it holds (SeatRead's `holds`, held to every write). */
type BindingKind = "const" | "let" | "var" | "parameter" | "function" | "import" | "class" | "other";
type Write = { text: string; line: number };
type Binding = { decl: string; bindingAt: number; kind: BindingKind; writes: Write[] };
type SeatSite = { line: number; fn: string; on: string; via: string; seats: string; assign: boolean; text: string; whole: string; body: boolean; seatedBy?: string; shadowed?: string } & Partial<Binding>;   // `text` is the call's text cut at 100 for messages; `whole` the flattened call text uncut, what a compare reads
/** A use of a member the census reads only by its site or refuses: its line and text. */
type Use = { line: number; text: string };
/** A member written on a receiver other than the `body` token: its function, receiver and the member's name; `through` names
 *  the object it is written through when that object is an element's `style` (a CSS property) or `dataset` (a data
 *  attribute), neither of which can hold an element child, so such a write passes by the rule and not by its name. */
type MemberWrite = Use & { fn: string; on: string; name: string; through?: "style" | "dataset" };
/** What the second read finds in file-view.ts, each list a class the census passes through a table, passes by a name, or refuses. */
type SecondRead = {
  sites: SeatSite[]; computed: Use[]; unknown: Array<Use & { name: string; on: string }>; handedOut: Array<Use & { name: string }>; oddCallee: Use[]; indexReads: Array<Use & { fn: string; on: string }>;
  handedNodes: HandedNode[]; stringRoads: Array<Use & { callee: string }>; urlWrites: UrlWrite[];
  writes: MemberWrite[]; computedWrites: MemberWrite[]; handlerStrings: MemberWrite[]; oddTargets: Use[]; bodyWrites: number;
  reflectionReads: Array<Use & { name: string; as: string }>; attrNames: MemberWrite[]; destructured: Use[];
  attrWrites: MemberWrite[]; bodyDecls: Array<Use & { why: string }>; elementsHanded: HandedNode[]; styleWrites: MemberWrite[];
};
/** Every seat in `src` on any receiver, and every other form the second read classes, each axis an allowlist with its default
 *  refusing (the branch's verification pass finding census-1; the round-6 review's clusters A to C). THE CALL AXIS: every
 *  CALL of a member (`x.m(...)`, `x?.m(...)`, `x["m"](...)`) is classed by the member's NAME: a seating name (SEAT_CALLS) or
 *  a site-read one (SITE_CALLS, any method of a SITE_RECEIVERS global by its binding, an `add` on a receiver that is neither
 *  a DOMTokenList nor a Set) is a site, passed only through the table; a name NON_SEATING_METHODS lists passes; any other
 *  name is `unknown` and refused. A seating or site-read name READ WITHOUT BEING CALLED (`md.append.call(...)`,
 *  `Reflect.apply(md.append, ...)`, `const f = md.append`, `Element.prototype.append`, a destructuring `const { append: f }
 *  = md` or `({ append: f } = md)`) is `handedOut` and refused: the method runs later where the census cannot read its
 *  receiver. A call through a computed name (`x[m](...)`) is `computed` and refused; a call whose callee is neither a name
 *  nor a member (a parenthesised expression, a call's value, an arrow) is `oddCallee` and refused. A member read by a
 *  computed name and NOT called (`x[k]`) is an index read: it passes where its value is only compared, tested or read
 *  further (an operand, a condition, a `.member` on it, which this read classes in turn), and where it is stored or handed
 *  on (a declaration, an assignment, an argument, a return, an array or object literal, a branch's value) it is an
 *  `indexRead` passed only as a site INDEX_READS_BY_HAND lists, since `const f = md[m]; f(x)` seats where no name says so.
 *  THE ASSIGNMENT AXIS (the round-6 review's cluster B: before this the second read knew innerHTML and outerHTML and passed every
 *  other write unread): every assignment, plain or compound, a `++` or `--`, each leaf target of an array or object pattern
 *  and a for-of or for-in head, whose target is a member of a receiver other than the `body` token (the first read's,
 *  counted in `bodyWrites`), is classed by the member's NAME: a seat (SEAT_ASSIGNS) is a site passed only through the
 *  table; a name NON_SEATING_WRITES lists is a `write` the census passes by that name; a computed name (`md[k] = ...`,
 *  `md["inner" + "HTML"] = ...`, `md[\`inner${k}\`] = ...`) is a `computedWrite` and refused wherever it stands; a member
 *  named `on<event>` written from a value that is not a function or null is a `handlerString` and refused (a string there
 *  runs as code); a target the census cannot read is `oddTargets` and refused; and a write by any other name is passed to
 *  the census, which refuses it unless the name is listed. A destructuring whose key is a seating or site-read name is
 *  `handedOut`; one whose key is computed is `destructured` and refused. THE RECEIVER AXIS (the round-6 review's cluster
 *  C: before this a reflection global was recognised by its receiver's bare spelling, so `const R = Reflect; R.set(...)`
 *  and `window.Reflect.set(...)` passed with no site and no refusal): every read of Object, Reflect or Function BY ITS
 *  BINDING (globalOf: the bare global, an alias through its declaration, a member of globalThis, window or self) other
 *  than as the receiver of a member call is a `reflectionRead` and refused: the alias declaration itself, a stored
 *  method (`const s = Reflect.set`), an argument, an array element, a return; as a call's receiver the call is a site the
 *  table must list. THE ARGUMENT AXIS (the round-6 review's item 7; the verifiers' records-1 and census-3 of the round-7
 *  build): a node of the tree handed to any callee is a `handedNode` (nodeHanded), and an element the census can see by
 *  its shape (elementShape) handed to a bare callee this file does not declare (foreignCallee) is an `elementHanded`, and
 *  so is one the census cannot name by shape whose type the compiler reads as able to hold a node (unnamedShape, marked
 *  `unnamed`; the round-8 fixes), each read bare and inside an object literal, an array literal, a spread or a concise
 *  arrow's value (handedIn), passed only as a site ARGS_READ_BY_HAND lists; a bare eval, setTimeout, setInterval or Function by its binding with a first argument
 *  that is not a function, `new Function`, and `import(...)` are `stringRoads` and refused. THE URL AXIS (the URL roads;
 *  the verifiers' census-1 and census-4 of the round-7 build): an assignment to a member NON_SEATING_WRITES flags as a URL
 *  or to a member of `location`, a setAttribute or setAttributeNS under a name that is neither `aria-*` nor `data-*` nor
 *  listed in NON_URL_ATTRS, a CSS property written through an element's `style` (an assignment through `style`, or
 *  `style.setProperty`) under a name NON_URL_STYLE_PROPS does not list (a literal spelling `url(` counts as a URL there; a
 *  computed property name is recorded whatever the value), a method of `location` that is one of its own navigations
 *  (assign, replace, reload) and `window.open`, each from a value (the call's first argument) that is not a literal or is a
 *  javascript: literal, is a `urlWrite` passed only as a site URL_WRITES_READ_BY_HAND lists. A member call is read in TWO
 *  PASSES (the round-8 fixes, the round-7 review's correctness-1, 2026-09-21: before this an else-if chain let the URL arm,
 *  keyed on the receiver's chain naming `location`, preempt the call axis and the seat table, so `append`, `setHTMLUnsafe` and every
 *  other method on such a receiver was classed on no axis and a literal first argument recorded nothing): the shape first
 *  (does the receiver's chain name `location`, is the method one of its navigations, is the callee the global `open`), then
 *  each axis on its own, the URL axis recording the navigations and the call axis every member call by its name except
 *  the three (location, navigation-method) pairs, a keyed exclusion on the PAIR and never on the receiver; the assignment
 *  spellings reach the URL axis inside classWrite, on the peeled target, before the identifier and body-token returns, so a
 *  parenthesised, array, object, for-of or for-in target is a `urlWrite` like a plain one (the round-7 review's extra8-1:
 *  the push stood in the plain-assignment arm on the raw left side); an
 *  `aria-*` or `data-*` attribute set from a non-literal is an `attrWrite`, classed and passed; a setAttribute or
 *  setAttributeNS whose name is not a string literal (a constant resolved through its declaration counts as one) or names
 *  an `on<event>` handler is an `attrName` passed only as a site ATTR_NAMES_READ_BY_HAND lists. A declaration named `body`
 *  other than the viewer's own, or a parameter of the name in a function BODY_HANDED_TO does not list as its own, is a
 *  `bodyDecl` and refused. The tree is the compiler's, so a receiver of any shape (a query result, a parentElement chain,
 *  a variable, a call's value) is one text the table can hold or refuse. */
function seatSites(src: string): SecondRead {
  const program = programOver(src);
  const sf = program.getSourceFile(VIEWER_PATH)!;
  assert.ok(sf !== undefined && sf.text === src, "the program's file-view.ts is the source handed in");
  const checker = program.getTypeChecker();
  const lineOf = (n: ts.Node): number => sf.getLineAndCharacterOfPosition(n.getStart(sf)).line + 1;
  const flat = (s: string): string => s.replace(/\s+/g, " ");
  /** A text an entry is HELD to (a declaration's initializer, a loop's head, an unnamed callback's call, a hand-off's argument or
   *  callee): the whole of it, so two texts that differ anywhere are two texts (the maintainer's round-8 ruling of 2026-09-21:
   *  the hold was the first 80 characters, and two initializers alike to there passed under one listed text); a text over 300
   *  characters is held as its first 80 characters beside the sha256 of the whole FLATTENED text, the text as the census reads
   *  it (comments blanked by the compiler, whitespace collapsed to single spaces), so a reader sees where it starts, the compare
   *  still reads all of it, and the digest is recomputed from that text and not from the file's raw bytes. The site texts in
   *  refusal messages (`text`) stay cut at 100 characters, being messages; the one compare over two live sites, the P7 case's
   *  byte-identical read of an entry's two seats or hand-offs, reads `whole`, the flattened call text uncut (the fold's
   *  verifiers' records-2: before this it read `text`, a hold on a 100-character prefix). */
  const held = (s: string): string => s.length > 300 ? s.slice(0, 80) + " ... sha256:" + crypto.createHash("sha256").update(s).digest("hex") : s;
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
  const isSite = (name: string, obj: ts.Expression): boolean => SEAT_CALLS.includes(name) || SITE_CALLS.includes(name) || SITE_RECEIVERS.includes(globalOf(obj) ?? "");   // a reflection global BY ITS BINDING: `Reflect`, an alias `const R = Reflect`, `globalThis.Reflect` (the round-6 review's item 7)
  /** A member access the FIRST read owns: `body.<seating method>` (its further access and its bare read are refused there). */
  const ownedByFirstRead = (e: ts.Expression): boolean => { const name = memberName(e); return name !== null && SEAT_CALLS.includes(name) && isBodyToken(memberObject(e)); };
  // the binding of an identifier: the innermost enclosing scope that declares the name (a block, a function's parameters, a
  // for or catch clause, the module), by the language's rule; `var` is read as block-scoped (file-view.ts declares none)
  const isScope = (n: ts.Node): boolean => ts.isSourceFile(n) || ts.isBlock(n) || ts.isFunctionLike(n) || ts.isForStatement(n) || ts.isForInStatement(n) || ts.isForOfStatement(n) || ts.isCatchClause(n) || ts.isCaseBlock(n);
  const declares = (n: ts.Node, name: string): boolean => (ts.isVariableDeclaration(n) || ts.isParameter(n) || ts.isBindingElement(n) || ts.isFunctionDeclaration(n) || ts.isClassDeclaration(n) || ts.isImportSpecifier(n) || ts.isImportClause(n)) && !!n.name && ts.isIdentifier(n.name) && n.name.text === name;
  // the declarations each scope owns, by name, read once (a nested scope's are its own, but a nested function's or class's
  // NAME is declared in the scope around it): the binding read runs for every identifier in the file, so the map is built
  // in one pass rather than walking the scope for each
  const declsIn = new Map<ts.Node, Map<string, ts.Node[]>>();
  const index = (n: ts.Node): void => {
    if ((ts.isVariableDeclaration(n) || ts.isParameter(n) || ts.isBindingElement(n) || ts.isFunctionDeclaration(n) || ts.isClassDeclaration(n) || ts.isImportSpecifier(n) || ts.isImportClause(n)) && n.name && ts.isIdentifier(n.name)) {
      let s: ts.Node = n.parent; while (!isScope(s)) s = s.parent;
      const names = declsIn.get(s) ?? new Map<string, ts.Node[]>(); declsIn.set(s, names);
      names.set(n.name.text, [...(names.get(n.name.text) ?? []), n]);
    }
    ts.forEachChild(n, index);
  };
  index(sf);
  const ownDecls = (scope: ts.Node, name: string): ts.Node[] => declsIn.get(scope)?.get(name) ?? [];
  const describe = (d: ts.Node): string => {
    if (ts.isParameter(d)) {
      const f = d.parent, name = nameOfFn(f);
      if (name) return "a parameter of " + name;
      const handedTo = ts.isCallExpression(f.parent) ? held(flat(f.parent.expression.getText(sf))) : null;   // an unnamed callback: the call it is handed to says what fills the parameter
      return handedTo ? "a parameter of the callback handed to " + handedTo : "a parameter of an unnamed function at line " + lineOf(f);
    }
    if (ts.isVariableDeclaration(d)) {
      const list = d.parent as ts.VariableDeclarationList, kind = list.flags & ts.NodeFlags.Const ? "const" : list.flags & ts.NodeFlags.Let ? "let" : "var";
      const loop = ts.isForOfStatement(list.parent) ? " of " + held(flat(list.parent.expression.getText(sf))) : ts.isForInStatement(list.parent) ? " in " + held(flat(list.parent.expression.getText(sf))) : "";
      return kind + " " + flat(d.name.getText(sf)) + (d.initializer ? " = " + held(flat(d.initializer.getText(sf))) : loop);
    }
    if (ts.isBindingElement(d)) { let p: ts.Node = d; while (p && !ts.isVariableDeclaration(p) && !ts.isParameter(p)) p = p.parent; return "a destructured binding of " + (p ? describe(p) : "an unknown declaration"); }
    if (ts.isFunctionDeclaration(d)) return "function " + d.name!.text;
    if (ts.isImportSpecifier(d) || ts.isImportClause(d)) return "an import";
    return "a " + ts.SyntaxKind[d.kind];
  };
  /** The kind of a declaration, for whether the name it binds can be written again: a const cannot; a let, a var and a
   *  parameter can (a destructured binding takes its declaration's kind). */
  const kindOf = (d: ts.Node): BindingKind => {
    if (ts.isParameter(d)) return "parameter";
    if (ts.isVariableDeclaration(d)) { const f = (d.parent as ts.VariableDeclarationList).flags; return f & ts.NodeFlags.Const ? "const" : f & ts.NodeFlags.Let ? "let" : "var"; }
    if (ts.isBindingElement(d)) { let p: ts.Node = d; while (p && !ts.isVariableDeclaration(p) && !ts.isParameter(p)) p = p.parent; return p ? kindOf(p) : "other"; }
    if (ts.isFunctionDeclaration(d)) return "function";
    if (ts.isImportSpecifier(d) || ts.isImportClause(d)) return "import";
    if (ts.isClassDeclaration(d)) return "class";
    return "other";
  };
  /** The declaration an identifier resolves to by the language's scopes: `undefined` for a name the file never declares (a
   *  global), null for one declared more than once in one scope (the census cannot say which). */
  const declNodeOf = (id: ts.Identifier): ts.Node | null | undefined => {
    for (let s: ts.Node | undefined = id.parent; s; s = s.parent) {
      if (!isScope(s)) continue;
      const ds = ownDecls(s, id.text);
      if (ds.length === 1) return ds[0];
      if (ds.length > 1) return null;
    }
    return undefined;
  };
  /** An expression with its parentheses, casts and non-null `!` read through. */
  const peel = (e: ts.Expression): ts.Expression => { let r = e; while (ts.isParenthesizedExpression(r) || ts.isAsExpression(r) || ts.isNonNullExpression(r) || ts.isSatisfiesExpression(r) || ts.isTypeAssertionExpression(r)) r = r.expression; return r; };
  const isAssignOp = (k: ts.SyntaxKind): boolean => k >= ts.SyntaxKind.FirstAssignment && k <= ts.SyntaxKind.LastAssignment;
  const isIncDec = (n: ts.Node): n is ts.PrefixUnaryExpression | ts.PostfixUnaryExpression => (ts.isPrefixUnaryExpression(n) || ts.isPostfixUnaryExpression(n)) && (n.operator === ts.SyntaxKind.PlusPlusToken || n.operator === ts.SyntaxKind.MinusMinusToken);
  /** The leaf targets a write's left side names, each with the key it is read under when the side is an object pattern: the
   *  target itself, or every leaf of an array or object pattern (a default's left, a spread's expression, a property's value). */
  const targetsOf = (t: ts.Expression): Array<{ target: ts.Expression; key?: ts.PropertyName }> => {
    const r = peel(t);
    if (ts.isArrayLiteralExpression(r)) return r.elements.flatMap((e) => ts.isOmittedExpression(e) ? [] : ts.isSpreadElement(e) ? targetsOf(e.expression) : ts.isBinaryExpression(e) && e.operatorToken.kind === ts.SyntaxKind.EqualsToken ? targetsOf(e.left) : targetsOf(e));
    if (ts.isObjectLiteralExpression(r)) return r.properties.flatMap((p): Array<{ target: ts.Expression; key?: ts.PropertyName }> => ts.isPropertyAssignment(p) ? (ts.isBinaryExpression(p.initializer) && p.initializer.operatorToken.kind === ts.SyntaxKind.EqualsToken ? targetsOf(p.initializer.left) : targetsOf(p.initializer)).map((x) => ({ target: x.target, key: x.key ?? p.name })) : ts.isShorthandPropertyAssignment(p) ? [{ target: p.name, key: p.name }] : ts.isSpreadAssignment(p) ? targetsOf(p.expression) : [{ target: r }]);
    return [{ target: r }];
  };
  // the writes to every binding in the file, by its declaration (the round-6 review's correctness-5): a pass before the
  // read, so a binding's `writes` is complete wherever its seat stands
  const writesTo = new Map<ts.Node, Write[]>();
  const noteWrite = (id: ts.Identifier, w: Write): void => { const d = declNodeOf(id); if (d) writesTo.set(d, [...(writesTo.get(d) ?? []), w]); };
  const prepass = (n: ts.Node): void => {
    if (ts.isBinaryExpression(n) && isAssignOp(n.operatorToken.kind)) {
      const plain = n.operatorToken.kind === ts.SyntaxKind.EqualsToken;
      for (const { target } of targetsOf(n.left)) if (ts.isIdentifier(target)) noteWrite(target, { text: plain && peel(n.left) === target ? flat(n.right.getText(sf)) : flat(n.getText(sf)), line: lineOf(n) });
    } else if (isIncDec(n)) { const o = peel(n.operand); if (ts.isIdentifier(o)) noteWrite(o, { text: flat(n.getText(sf)), line: lineOf(n) }); }
    else if ((ts.isForOfStatement(n) || ts.isForInStatement(n)) && !ts.isVariableDeclarationList(n.initializer)) for (const { target } of targetsOf(n.initializer)) if (ts.isIdentifier(target)) noteWrite(target, { text: "each of " + flat(n.expression.getText(sf)), line: lineOf(n) });
    ts.forEachChild(n, prepass);
  };
  prepass(sf);
  const bindingOf = (id: ts.Identifier): Binding => {
    for (let s: ts.Node | undefined = id.parent; s; s = s.parent) {
      if (!isScope(s)) continue;
      const ds = ownDecls(s, id.text);
      if (ds.length === 1) { const d = ds[0]; const init = ts.isVariableDeclaration(d) && d.initializer ? [{ text: flat(d.initializer.getText(sf)), line: lineOf(d) }] : []; return { decl: describe(d), bindingAt: d.getStart(sf), kind: kindOf(d), writes: [...init, ...(writesTo.get(d) ?? [])] }; }
      if (ds.length > 1) return { decl: "declared " + ds.length + " times in one scope (lines " + ds.map(lineOf).join(", ") + ")", bindingAt: ds[0].getStart(sf), kind: "other", writes: [] };
    }
    return { decl: "a global", bindingAt: -1, kind: "other", writes: [] };
  };
  /** The initializer a name is bound to by its `const` or `let` declaration, or null (a parameter, a global, a loop's binding). */
  const initOf = (e: ts.Expression): ts.Expression | null => { const r = peel(e); if (!ts.isIdentifier(r)) return null; const d = declNodeOf(r); return d && ts.isVariableDeclaration(d) && d.initializer ? d.initializer : null; };
  const GLOBAL_OBJECTS = ["globalThis", "window", "self"];
  /** The global a receiver or callee resolves to BY ITS BINDING (the round-6 review's item 7: before this a reflection
   *  global was read by its identifier's text, so `const R = Reflect; R.set(...)` and `globalThis.Reflect.set(...)` passed):
   *  the name itself when the file never declares it, an alias through its declaration's initializer, a member of the
   *  global object (`globalThis.Reflect`); null for a name the file declares or a shape the census cannot follow. */
  const globalOf = (e: ts.Expression, depth = 0): string | null => {
    const r = peel(e);
    if (depth > 8) return null;
    if (ts.isIdentifier(r)) { const d = declNodeOf(r); if (d === undefined) return r.text; return d && ts.isVariableDeclaration(d) && d.initializer ? globalOf(d.initializer, depth + 1) : null; }
    if (ts.isPropertyAccessExpression(r)) { const g = globalOf(r.expression, depth + 1); return g !== null && GLOBAL_OBJECTS.includes(g) ? r.name.text : null; }
    return null;
  };
  /** The bare callees that run a string as code unless their first argument is a function (a string road: eval, a timer's
   *  string, the Function constructor; `import(...)` never takes a function, so every dynamic import is refused). */
  const STRING_ROAD_CALLEES = ["eval", "setTimeout", "setInterval", "Function"];
  /** Whether an argument is a function: an arrow or function expression, or a name bound to a function declaration or to a
   *  declaration whose initializer is one. */
  const isFunction = (a: ts.Expression | undefined): boolean => {
    if (!a) return false;
    const r = peel(a);
    if (ts.isArrowFunction(r) || ts.isFunctionExpression(r)) return true;
    if (!ts.isIdentifier(r)) return false;
    const d = declNodeOf(r);
    if (d && ts.isFunctionDeclaration(d)) return true;
    const i = initOf(r);
    return i !== null && (ts.isArrowFunction(peel(i)) || ts.isFunctionExpression(peel(i)));
  };
  const isNullish = (a: ts.Expression): boolean => { const r = peel(a); return r.kind === ts.SyntaxKind.NullKeyword || (ts.isIdentifier(r) && r.text === "undefined"); };
  /** The members a URL is written to, and whether an assignment's target reaches `location` (the global, or a member so named). */
  const URL_MEMBERS = NON_SEATING_WRITES.filter((e) => e.url).map((e) => e.name);   // the members whose hand read says the value is a URL (the assignment axis lists every written name; the URL axis reads the flagged ones)
  const touchesLocation = (e: ts.Expression): boolean => {
    let r = peel(e);
    for (;;) {
      if (ts.isIdentifier(r)) return r.text === "location" && declNodeOf(r) === undefined;
      if (ts.isPropertyAccessExpression(r)) { if (r.name.text === "location") return true; r = peel(r.expression); continue; }
      if (ts.isElementAccessExpression(r)) { r = peel(r.expression); continue; }
      return false;
    }
  };
  const isUrlTarget = (left: ts.Expression): boolean => { const name = ts.isPropertyAccessExpression(left) || ts.isElementAccessExpression(left) ? memberName(left) : null; return (name !== null && URL_MEMBERS.includes(name)) || touchesLocation(left); };
  const literalText = (right: ts.Expression): string | null => { const r = peel(right); return ts.isStringLiteral(r) || ts.isNoSubstitutionTemplateLiteral(r) ? r.text : null; };
  /** `add` seats nothing on a DOMTokenList (`x.classList`, `relList`, `part`) or a Set (`new Set(...)`, `new WeakSet(...)`, a
   *  name bound to one by its declaration); on any other receiver (an HTMLSelectElement's add and an HTMLOptionsCollection's
   *  add seat an option) it is a call read by its site (the round-6 review's item 7 and extra6-4: `add` stood in
   *  NON_SEATING_METHODS for every receiver). */
  const TOKEN_LISTS = ["classList", "relList", "part"];
  const isSetLike = (e: ts.Expression, depth = 0): boolean => {
    const r = peel(e);
    if (ts.isNewExpression(r)) return ts.isIdentifier(r.expression) && ["Set", "WeakSet"].includes(r.expression.text) && globalOf(r.expression) === r.expression.text;
    const i = initOf(r);
    return i !== null && depth < 8 && isSetLike(i, depth + 1);
  };
  const addSeatsNothing = (obj: ts.Expression): boolean => { const r = peel(obj); return (ts.isPropertyAccessExpression(r) && TOKEN_LISTS.includes(r.name.text)) || isSetLike(r); };
  /** The node of the tree an argument hands out (the round-6 review's item 7, the argument axis: before this no argument to
   *  a callee other than the `body` token was read, so `addCopyBtn(load.parentElement!, "")` seated a body root with no
   *  refusal): a NODE_MEMBERS chain (`x.parentElement`), an index into one (`x.children[0]`), or a name bound to either by
   *  its declaration's initializer (with the name's binding, kind and writes), each with parentheses, casts and `!` read
   *  through. A chain whose object is the `body` token is the first read's (a bare read of `body.firstChild` is classed
   *  there) and is not counted twice. Null for every other argument. */
  const nodeHanded = (a: ts.Expression, depth = 0): ({ member: string } & Partial<Binding>) | null => {
    const r = peel(a);
    if (ts.isPropertyAccessExpression(r) && NODE_MEMBERS.includes(r.name.text)) return isBodyToken(peel(r.expression)) ? null : { member: r.name.text };
    if (ts.isElementAccessExpression(r)) { const o = peel(r.expression); return ts.isPropertyAccessExpression(o) && NODE_MEMBERS.includes(o.name.text) && !isBodyToken(peel(o.expression)) ? { member: o.name.text } : null; }
    if (ts.isIdentifier(r) && depth < 8) { const d = declNodeOf(r); if (d && ts.isVariableDeclaration(d) && d.initializer) { const h = nodeHanded(d.initializer, depth + 1); return h ? { member: h.member, ...bindingOf(r), ...(shadowOf(r) ? { shadowed: shadowOf(r)! } : {}) } : null; } }
    return null;
  };
  const sites: SeatSite[] = [], computed: Use[] = [], unknown: Array<Use & { name: string; on: string }> = [], handedOut: Array<Use & { name: string }> = [], oddCallee: Use[] = [], indexReads: Array<Use & { fn: string; on: string }> = [];
  const handedNodes: HandedNode[] = [], stringRoads: Array<Use & { callee: string }> = [], urlWrites: UrlWrite[] = [];
  const writes: MemberWrite[] = [], computedWrites: MemberWrite[] = [], handlerStrings: MemberWrite[] = [], oddTargets: Use[] = [], reflectionReads: Array<Use & { name: string; as: string }> = [], attrNames: MemberWrite[] = [], destructured: Use[] = [];
  const attrWrites: MemberWrite[] = [], bodyDecls: Array<Use & { why: string }> = [], elementsHanded: HandedNode[] = [], styleWrites: MemberWrite[] = [];   // styleWrites: the writes through style from a non-literal the URL axis passes by NON_URL_STYLE_PROPS, classed and never silent
  /** One URL write recorded on the URL axis: its target as spelled (`on`), the value as spelled and, for a bare name, the
   *  value's binding and shadow. Every road of the axis (an assignment, setAttribute, the style road, a navigation) records
   *  through this one function, so a value read is never a road's own. */
  const urlWriteAt = (n: ts.Node, on: string, value: string, valueNode?: ts.Expression): void => {
    const u: UrlWrite = { line: lineOf(n), text: text(n), fn: fnOf(n), on, value };
    if (valueNode) { const pv = peel(valueNode); if (ts.isIdentifier(pv)) { Object.assign(u, bindingOf(pv)); const sh = shadowOf(pv); if (sh) u.shadowed = sh; } }
    urlWrites.push(u);
  };
  /** A call of one of `location`'s own navigation methods (LOCATION_NAV: assign, replace, reload) or of `window.open` (or the
   *  bare global `open`): a navigation to its first argument, read as a URL write whose target is the call (`location.replace`,
   *  `window.open`) and whose value is that argument; a string literal there that is not a javascript: URL passes, as an
   *  assignment's does. Any other method on a location-named receiver is the call axis's (the round-8 fixes). */
  const urlCall = (n: ts.CallExpression, target: string): void => {
    const v = n.arguments[0];
    const lit = v ? literalText(v) : null;
    if (v && lit !== null && !/^\s*javascript:/i.test(lit)) return;
    urlWriteAt(n, target, v ? flat(v.getText(sf)) : "", v);
  };
  /** The methods of `location` that navigate: the three the URL axis owns on a receiver whose chain names `location`. */
  const LOCATION_NAV = ["assign", "replace", "reload"];
  /** A CSS property name as `style.<name>` spells it, from setProperty's kebab-case argument (`background-image` to
   *  `backgroundImage`; a custom property `--x` keeps its dashes, so it never matches a listed name and is read). */
  const camelProp = (name: string): string => name.startsWith("--") ? name : name.replace(/-([a-z])/g, (_, ch: string) => ch.toUpperCase());
  /** Whether a call's callee is a BARE name this file does not declare: an import (`addCopyBtn`, `installFilePrint`) or a
   *  global (`Array.from` is a member; a bare `structuredClone`). A local function's seats are read in this file; a member
   *  call is the call axis's (its name passes only as NON_SEATING_METHODS lists it, whatever it is handed, or as a site the
   *  table lists with its arguments). */
  const foreignCallee = (n: ts.CallExpression | ts.NewExpression): boolean => {
    const c = peel(n.expression);
    if (!ts.isIdentifier(c)) return false;   // a member call is the call axis's: its name passes only as NON_SEATING_METHODS lists it, or as a site the table lists
    const d = declNodeOf(c);
    return d === undefined || (!!d && (ts.isImportSpecifier(d) || ts.isImportClause(d)));
  };
  /** The methods whose value is an element or a node the census can see by the call's spelling. */
  const ELEMENT_MAKERS = ["createElement", "createElementNS", "querySelector", "closest", "getElementById", "cloneNode", "importNode", "createTextNode", "createDocumentFragment"];
  /** The element an expression is, by its shape (the verifiers' records-1 of the round-7 build: a root gained through an imported
   *  helper handed an el()-built const or a query result was read on no axis, while the argument axis knew NODE_MEMBERS chains
   *  alone): `el(...)`, a call of an ELEMENT_MAKERS method, a call of a local builder any of whose returns names an el()-built
   *  variable (every return read, as rootsOf reads them since the round-8 fixes), a name bound to any of these by its declaration, a parameter typed as an element or a node, each
   *  through parentheses, casts and `!`; null for anything else. */
  const elementShape = (a: ts.Expression, depth = 0): string | null => {
    const r = peel(a);
    if (depth > 8) return null;
    if (ts.isCallExpression(r)) {
      const c = r.expression;
      if (ts.isIdentifier(c)) {
        if (c.text === "el") return "el(...)";
        const d = declNodeOf(c);
        if (d && ts.isFunctionDeclaration(d) && d.body) {   // every return of the builder, a nested function's excluded, the shapes united (the round-8 fixes, extra9-1: the last top-level return alone was read)
          const rets: ts.ReturnStatement[] = [];
          const walk = (x: ts.Node): void => { if (ts.isFunctionLike(x)) return; if (ts.isReturnStatement(x)) rets.push(x); ts.forEachChild(x, walk); };
          ts.forEachChild(d.body, walk);
          const shapes = [...new Set(rets.map((r) => (r.expression && ts.isIdentifier(r.expression) ? elementShape(r.expression, depth + 1) : null)).filter((x): x is string => x !== null))];
          if (shapes.length) return "a call of the builder " + c.text + ", which returns " + shapes.join(" or ");
        }
        return null;
      }
      const name = memberName(c);
      return name !== null && ELEMENT_MAKERS.includes(name) ? "a " + name + "(...) result" : null;
    }
    if (ts.isIdentifier(r)) {
      const d = declNodeOf(r);
      if (d && ts.isVariableDeclaration(d) && d.initializer) { const shape = elementShape(d.initializer, depth + 1); return shape ? shape + " bound to `" + r.text + "`" : null; }
      if (d && ts.isParameter(d) && d.type && /\b(?:HTML\w*Element|SVG\w*Element|Element|Node|ParentNode|ChildNode)\b/.test(d.type.getText(sf))) return "a parameter typed " + flat(d.type.getText(sf)) + " bound to `" + r.text + "`";
      return null;
    }
    return null;
  };
  /** The compiler's answer for an argument elementShape cannot name (the round-8 fixes, the round-7 review's tests-2 and
   *  regression-1, 2026-09-21: the shape rule enumerated on the UNSAFE side, an element it could not name PASSED, and the
   *  merge moved the sanitized body handed to the imported gateRemoteFigures into that gap after the entry that read it was
   *  deleted rather than repointed; the refuters found addCopyBtn(host, ...), a conditional, and wrapCodeLines(codeEl), a cast
   *  of an untyped callback parameter, in the same gap, which no syntactic rule reaches). The road asks what the value CAN BE
   *  rather than how it was spelled: the argument's type, as the compiler reads it, with every non-nullish member tested for
   *  being assignable to `Node`, for `Node` being assignable to it (EventTarget, ParentNode, object, `{}`) or for being `any`
   *  or `unknown` (a type the compiler cannot vouch for is the safe side). A function expression and a string literal are
   *  never a node and are not asked; a property or element access on the `body` token is the first read's and yields, as
   *  nodeHanded does (a read there would red one signal twice). Null when the type can hold no node; else the text the
   *  hand-off is refused with until ARGS_READ_BY_HAND lists it, marked `unnamed`. */
  let nodeType: ts.Type | null = null;
  const canHoldNode = (t: ts.Type): boolean => {
    if (nodeType === null) { const sym = checker.resolveName("Node", undefined, ts.SymbolFlags.Type, false); assert.ok(sym !== undefined, "the DOM lib's Node is in the program"); nodeType = checker.getDeclaredTypeOfSymbol(sym); }
    const node = nodeType;
    return (t.isUnion() ? t.types : [t]).some((m) => {
      if (m.flags & (ts.TypeFlags.Null | ts.TypeFlags.Undefined | ts.TypeFlags.Void | ts.TypeFlags.Never)) return false;
      if (m.flags & (ts.TypeFlags.Any | ts.TypeFlags.Unknown)) return true;
      return checker.isTypeAssignableTo(m, node) || checker.isTypeAssignableTo(node, m);
    });
  };
  const unnamedShape = (a: ts.Expression): string | null => {
    const r = peel(a);
    if (ts.isArrowFunction(r) || ts.isFunctionExpression(r) || ts.isStringLiteral(r) || ts.isNoSubstitutionTemplateLiteral(r)) return null;
    if ((ts.isPropertyAccessExpression(r) || ts.isElementAccessExpression(r)) && isBodyToken(peel(r.expression))) return null;
    const t = checker.getTypeAtLocation(a);
    return canHoldNode(t) ? "an argument the census cannot name by shape, typed `" + checker.typeToString(t) + "` by the compiler, a type that can hold a node" : null;
  };
  /** One argument of a call, or a node inside it (the verifiers' census-3 of the round-7 build: the argument axis read direct
   *  arguments alone, so a node handed inside an object literal passed): an object literal's property values, an array
   *  literal's elements, a spread's expression and a concise arrow's value are read in turn, each spelled with its path
   *  (`{ hostParent: host.parentElement }`); a node of the tree (nodeHanded) is a handedNode; an element the census can see by
   *  shape (elementShape) handed to a callee the file does not declare is an elementHanded. Not read: a node returned from a
   *  block-bodied callback, or built inside one. */
  const handedIn = (n: ts.CallExpression | ts.NewExpression, a: ts.Expression, spell: (inner: string) => string, foreign: boolean): void => {
    if (ts.isSpreadElement(a)) { handedIn(n, a.expression, (s) => spell("..." + s), foreign); return; }
    const r = peel(a);
    if (ts.isObjectLiteralExpression(r)) { for (const p of r.properties) { if (ts.isPropertyAssignment(p)) handedIn(n, p.initializer, (s) => spell("{ " + flat(p.name.getText(sf)) + ": " + s + " }"), foreign); else if (ts.isShorthandPropertyAssignment(p)) handedIn(n, p.name, (s) => spell("{ " + s + " }"), foreign); else if (ts.isSpreadAssignment(p)) handedIn(n, p.expression, (s) => spell("{ ..." + s + " }"), foreign); } return; }
    if (ts.isArrayLiteralExpression(r)) { for (const e of r.elements) if (!ts.isOmittedExpression(e)) handedIn(n, e, (s) => spell("[ " + s + " ]"), foreign); return; }
    if (ts.isArrowFunction(r) && !ts.isBlock(r.body)) { handedIn(n, r.body, (s) => spell("() => " + s), foreign); return; }
    const h = nodeHanded(a);
    if (h) { handedNodes.push({ line: lineOf(n), text: text(n), whole: flat(n.getText(sf)), fn: fnOf(n), to: calleeText(n), arg: spell(held(flat(a.getText(sf)))), ...h }); return; }
    if (!foreign) return;
    const named = elementShape(a);
    const unnamed = named === null ? unnamedShape(a) : null;   // the shape first; the compiler's type for what the shape cannot name (the round-8 fixes)
    const shape = named ?? unnamed;
    if (shape !== null) { const e = peel(a); if (ts.isIdentifier(e) && isBodyToken(e)) return; const b = ts.isIdentifier(e) ? { ...bindingOf(e), ...(shadowOf(e) ? { shadowed: shadowOf(e)! } : {}) } : {}; elementsHanded.push({ line: lineOf(n), text: text(n), whole: flat(n.getText(sf)), fn: fnOf(n), to: calleeText(n), arg: spell(held(flat(a.getText(sf)))), member: shape, ...(unnamed !== null ? { unnamed: true as const } : {}), ...b }); }
  };
  let bodyWrites = 0;
  /** An argument as the seat key spells it: an object literal, an array literal or a function abbreviated, the rest as written. */
  const abbreviate = (a: ts.Expression): string => { const r = peel(a); return ts.isObjectLiteralExpression(r) ? "{" + r.properties.map((p) => ts.isSpreadAssignment(p) ? "..." + flat(p.expression.getText(sf)) : p.name ? flat(p.name.getText(sf)) : "?").join(", ") + "}" : ts.isArrayLiteralExpression(r) ? "[...]" : ts.isArrowFunction(r) || ts.isFunctionExpression(r) ? "() => ..." : flat(a.getText(sf)); };
  /** The nearest named function around `n` (the one fnOf names), or the file. */
  const fnNodeOf = (n: ts.Node): ts.Node => { for (let p: ts.Node | undefined = n.parent; p; p = p.parent) if (nameOfFn(p)) return p; return sf; };
  /** Every declaration of `name` inside `fn` (a block's, a loop's, a callback's parameter), not descending into a nested
   *  named function, which is another entry's `in`. */
  const declsInFn = (fn: ts.Node, name: string): ts.Node[] => {
    const out: ts.Node[] = [];
    const walk = (x: ts.Node): void => { if (x !== fn && nameOfFn(x)) return; if (declares(x, name)) out.push(x); ts.forEachChild(x, walk); };
    walk(fn);
    return out;
  };
  /** Why a bare name at a seat cannot be held to one binding by its declaration's text, or null: the entry's function declares
   *  the name more than once (a block's `const wrap = el("div")` beside the listed one, spelled alike), or declares it once while
   *  the name at the seat is bound outside the function (a shadow elsewhere in the function). The census refuses the seat
   *  rather than pin the binding by its line (the verifiers' finding census-2 of the round-7 build: a shadow wearing the listed
   *  declaration's exact spelling passed on the text compare). */
  const shadowOf = (id: ts.Identifier): string | null => {
    const fn = fnNodeOf(id), inside = declsInFn(fn, id.text), d = declNodeOf(id);
    const expected = d && inside.includes(d) ? 1 : 0;
    if (inside.length === expected) return null;
    return "`" + id.text + "` is declared " + inside.length + " times in " + (fn === sf ? "the module" : nameOfFn(fn)) + " (lines " + inside.map(lineOf).join(", ") + ")" + (expected === 0 && d ? " while the name here is bound outside it" : "") + ": a second declaration of a listed name in the entry's function is refused, whatever it spells";
  };
  /** The binding of each seated argument that is a bare name (the branch's verification pass finding census-2, and the
   *  verifiers' census-2 of the round-7 build: the receiver was held to its declaration while the SEATED name was matched by
   *  its spelling alone, so `{ const body = el("div", "x"); main.appendChild(body); }` wore the listed seat): `name = decl`,
   *  a spread's name with its dots, a reassignable one with every write to it, joined by "; "; undefined when no seated
   *  argument is a bare name, the `body` token among them (the viewer's own declaration, so a block's `const body` seated at
   *  the listed site is another binding). */
  const seatedBy = (args: ts.Expression[]): string | undefined => {
    const parts: string[] = [];
    for (const a of args) {
      const spread = ts.isSpreadElement(a), e = peel(spread ? (a as ts.SpreadElement).expression : a);
      if (!ts.isIdentifier(e)) continue;   // the `body` token too: the entry pins that what is seated IS the viewer's body (a block's `const body` is another binding)
      const b = bindingOf(e);
      parts.push((spread ? "..." : "") + e.text + " = " + b.decl + (b.kind === "const" || b.kind === "function" || b.kind === "import" || b.kind === "class" || b.kind === "other" ? "" : "; writes: " + ((b.writes ?? []).map((w) => "`" + w.text + "` at line " + w.line).join(", ") || "none")));
    }
    return parts.length ? parts.join("; ") : undefined;
  };
  const site = (n: ts.Node, recv: ts.Expression, via: string, seats: string, assign = false, seatedArgs: ts.Expression[] = []): void => {
    const r = strip(recv);
    const s: SeatSite = { line: lineOf(n), fn: fnOf(n), on: flat(r.getText(sf)), via, seats, assign, text: text(n), whole: flat(n.getText(sf)), body: ts.isIdentifier(r) && r.text === "body" };
    if (ts.isIdentifier(r) && !s.body) { Object.assign(s, bindingOf(r)); const sh = shadowOf(r); if (sh) s.shadowed = sh; }
    const by = seatedBy(seatedArgs);
    if (by !== undefined) s.seatedBy = by;
    for (const a of seatedArgs) { const e = peel(ts.isSpreadElement(a) ? (a as ts.SpreadElement).expression : a); if (ts.isIdentifier(e) && !isBodyToken(e)) { const sh = shadowOf(e); if (sh) s.shadowed = (s.shadowed ? s.shadowed + "; " : "") + sh; } }
    sites.push(s);
  };
  const isCallee = (n: ts.Node): boolean => ts.isCallExpression(n.parent) && n.parent.expression === n;
  /** The node whose value an expression's value is: a cast, a non-null `!` or parentheses around it read through. */
  const effectiveParent = (n: ts.Node): ts.Node => { let p = n.parent; while (ts.isAsExpression(p) || ts.isNonNullExpression(p) || ts.isParenthesizedExpression(p) || ts.isSatisfiesExpression(p)) p = p.parent; return p; };
  /** Whether `n` stands as the receiver of a member call (`n.m(...)`, through parentheses or a cast), the one position a
   *  reflection global passes in. */
  const receiverOfMemberCall = (n: ts.Node): boolean => { let c: ts.Node = n, p = n.parent; while (ts.isParenthesizedExpression(p) || ts.isAsExpression(p) || ts.isNonNullExpression(p) || ts.isSatisfiesExpression(p)) { c = p; p = p.parent; } return ts.isPropertyAccessExpression(p) && p.expression === c && isCallee(p); };
  /** Whether an identifier is a READ of a value: not a member's name, not a declaration's name, not a property key, not a
   *  label, and not inside a type (a type reference `Function`, a `typeof X` type query). */
  const isReference = (id: ts.Identifier): boolean => {
    const p = id.parent;
    if (ts.isPropertyAccessExpression(p) && p.name === id) return false;
    if ((ts.isVariableDeclaration(p) || ts.isParameter(p) || ts.isBindingElement(p) || ts.isFunctionDeclaration(p) || ts.isClassDeclaration(p) || ts.isImportSpecifier(p) || ts.isImportClause(p) || ts.isPropertyAssignment(p) || ts.isPropertySignature(p) || ts.isMethodDeclaration(p) || ts.isMethodSignature(p) || ts.isPropertyDeclaration(p) || ts.isEnumMember(p) || ts.isTypeAliasDeclaration(p) || ts.isInterfaceDeclaration(p) || ts.isGetAccessor(p) || ts.isSetAccessor(p)) && p.name === id) return false;
    if (ts.isBindingElement(p) && p.propertyName === id) return false;
    if (ts.isLabeledStatement(p) || ts.isBreakOrContinueStatement(p) || ts.isQualifiedName(p) || ts.isExportSpecifier(p)) return false;
    for (let a: ts.Node | undefined = p, i = 0; a && i < 3; a = a.parent, i++) if (ts.isTypeNode(a)) return false;
    return true;
  };
  const onlyRead = (n: ts.Node): boolean => {   // the value is compared, tested or read further, never stored or handed on
    const p = effectiveParent(n);
    if (ts.isPropertyAccessExpression(p) || ts.isElementAccessExpression(p) && p.argumentExpression === n || ts.isPrefixUnaryExpression(p) || ts.isPostfixUnaryExpression(p) || ts.isTypeOfExpression(p) || ts.isTemplateSpan(p) || ts.isExpressionStatement(p) || ts.isIfStatement(p) || ts.isWhileStatement(p) || ts.isDoStatement(p) || ts.isDeleteExpression(p) || ts.isVoidExpression(p)) return true;
    if (ts.isBinaryExpression(p)) return !isAssignOp(p.operatorToken.kind) || p.left === n;   // an assignment's left side is a WRITE, classed by the assignment axis (classWrite), not a stored read
    if (ts.isConditionalExpression(p)) return p.condition === n;
    if (ts.isForStatement(p)) return p.condition === n || p.incrementor === n;
    return false;
  };
  const calleeText = (n: ts.CallExpression | ts.NewExpression): string => (ts.isNewExpression(n) ? "new " : "") + (n.expression.kind === ts.SyntaxKind.ImportKeyword ? "import" : held(flat(strip(n.expression).getText(sf))));
  /** A property key a destructuring reads a value under: a seating or site-read name is a hand-out, a computed key is refused. */
  const keyRead = (key: ts.PropertyName, at: ts.Node): void => {
    if (ts.isComputedPropertyName(key)) destructured.push({ line: lineOf(at), text: text(at) });
    else if ((ts.isIdentifier(key) || ts.isStringLiteral(key)) && (SEAT_CALLS.includes(key.text) || SITE_CALLS.includes(key.text))) handedOut.push({ line: lineOf(at), text: text(at), name: key.text });
  };
  /** One write target, classed by the assignment axis and, first, by the URL axis: a binding's write was the pre-pass's; a
   *  member of the `body` token is the first read's; a computed name is refused; a SEAT_ASSIGNS name is a site (the value is
   *  what it seats); any other member name is a write the census holds to NON_SEATING_WRITES, an `on<event>` one to a
   *  function value as well. THE URL AXIS reads the PEELED target here, before the identifier and body-token returns (the
   *  round-8 fixes, the round-7 review's extra8-1, 2026-09-21: the push stood in visit's plain-assignment arm on the raw
   *  left side, so a URL member written through a parenthesised, array, object, for-of or for-in target was a write and no
   *  URL write, where the same targets with innerHTML were seats): a member NON_SEATING_WRITES flags as a URL, or a target
   *  whose chain names `location`, written from a value that is not a literal or is a javascript: literal, is a URL write; an
   *  arm with no value node (a pattern's leaf, a loop's head, a `++`) is recorded unconditionally, there being no literal to
   *  read; `on` is the peeled target's text (byte-identical to the raw left side's for every live entry). The style road (the
   *  round-7 review's correctness-2) follows the write's own record: a write through `style` under a property
   *  NON_URL_STYLE_PROPS does not list, from a value that is not a literal or a literal spelling `url(` or `javascript:`, is a
   *  URL write on `<recv>.style.<prop>`; a computed property name is the computed-write refusal above. */
  const classWrite = (n: ts.Node, target: ts.Expression, value: string, op: string, valueNode?: ts.Expression): void => {
    const t = peel(target);
    const urlMember = isUrlTarget(t);
    const lit = valueNode ? literalText(valueNode) : null;
    if (urlMember && (lit === null || /^\s*javascript:/i.test(lit))) urlWriteAt(n, flat(strip(t).getText(sf)), value, valueNode);
    if (ts.isIdentifier(t)) return;
    if (!ts.isPropertyAccessExpression(t) && !ts.isElementAccessExpression(t)) { oddTargets.push({ line: lineOf(n), text: text(n) }); return; }
    const obj = memberObject(t), name = memberName(t);
    if (isBodyToken(obj)) { bodyWrites++; return; }
    const on = flat(strip(obj).getText(sf));
    if (name === null) { computedWrites.push({ line: lineOf(n), text: text(n), fn: fnOf(n), on, name: "[" + flat((t as ts.ElementAccessExpression).argumentExpression.getText(sf)) + "]" }); return; }
    if (SEAT_ASSIGNS.includes(name)) { site(n, obj, name + " " + op, value, true); return; }
    const o = peel(obj);
    const through = ts.isPropertyAccessExpression(o) && (o.name.text === "style" || o.name.text === "dataset") ? o.name.text : undefined;
    writes.push(through ? { line: lineOf(n), text: text(n), fn: fnOf(n), on, name, through } : { line: lineOf(n), text: text(n), fn: fnOf(n), on, name });
    if (!urlMember && through === "style" && (lit === null || /url\(|javascript:/i.test(lit))) { if (NON_URL_STYLE_PROPS.some((p) => p.name === name)) styleWrites.push({ line: lineOf(n), text: text(n), fn: fnOf(n), on, name, through }); else urlWriteAt(n, on + "." + name, value, valueNode); }
    if (/^on[a-z]+$/.test(name) && !(valueNode && (isFunction(valueNode) || isNullish(valueNode)))) handlerStrings.push({ line: lineOf(n), text: text(n), fn: fnOf(n), on, name });
  };
  const visit = (n: ts.Node): void => {
    if (ts.isCallExpression(n)) {
      const c = n.expression;
      const name = memberName(c);
      if (ts.isPropertyAccessExpression(c) || ts.isElementAccessExpression(c) && name !== null) {
        const obj = memberObject(c);
        const recv = flat(strip(obj).getText(sf));
        if (ts.isElementAccessExpression(c)) computed.push({ line: lineOf(n), text: text(n) });
        else {
          // TWO PASSES over a member call (the round-8 fixes, the round-7 review's correctness-1, 2026-09-21: an else-if chain
          // stood here whose URL arm, keyed on the receiver's chain naming `location`, preempted the seat and call arms, so
          // `nav.location.append(x)` was refused as a URL write and `nav.location.setHTMLUnsafe("<b>")` recorded nothing).
          // The first pass reads the call's SHAPE: does the receiver's chain name `location`, is the method one of location's
          // own navigations, is the callee the global `open`. The second applies each axis on its own.
          const onLocation = touchesLocation(obj), navigation = LOCATION_NAV.includes(name!), globalOpen = name === "open" && GLOBAL_OBJECTS.includes(globalOf(obj) ?? "");
          // THE URL AXIS: a navigation is a URL write from its first argument (the verifiers' census-4 of the round-7 build:
          // `location.replace(x)` passed under String.prototype.replace's listing, `window.open(href, ...)` under the browser's `open`)
          if ((onLocation && navigation) || globalOpen) urlCall(n, recv + "." + name);
          // THE CALL AXIS: every member call by its name, except the three (location, navigation-method) PAIRS, which seat
          // nothing and are the URL axis's alone; the exclusion is keyed on the pair, never on the receiver, so a seat name or an
          // unlisted name on a location-named receiver is read here like any other receiver's, and `x.assign(y)` on any other
          // receiver is an unlisted method
          if (!(onLocation && navigation)) {
            if (isSite(name!, obj)) { if (!(SITE_CALLS.includes(name!) && ownedByFirstRead(obj))) { const seated = SEAT_CALLS.includes(name!) ? SEATED_ARGS[name!](n.arguments.map((_, i) => String(i))).map((i) => n.arguments[Number(i)]) : [...n.arguments]; site(n, obj, name!, SEAT_CALLS.includes(name!) ? seated.map((a) => flat(a.getText(sf))).join(", ") : n.arguments.map(abbreviate).join(", "), false, seated); } }   // `body.append.call(...)` is the first read's refusal
            else if (name === "add" && !isBodyToken(obj) && !addSeatsNothing(obj)) site(n, obj, "add", n.arguments.map(abbreviate).join(", "), false, [...n.arguments]);   // add on a receiver that is neither a class list nor a Set: a site
            else if (!NON_SEATING_METHODS.includes(name!) && !isBodyToken(obj)) unknown.push({ line: lineOf(n), text: text(n), name: name!, on: recv });
          }
        }
        if (name === "setProperty" && !isBodyToken(obj)) {   // THE URL AXIS's style road through setProperty (the round-8 fixes, the round-7 review's correctness-2): the call passes on the call axis by its listing, which says nothing about the value; the property name a literal (a constant resolved through its declaration counts) is read against NON_URL_STYLE_PROPS in its `style.<name>` spelling, a computed name is recorded whatever the value, and the value is read like setAttribute's (a non-literal, or a literal spelling url( or javascript:, is a URL write on `<recv>.setProperty("<prop>")`)
          const a = n.arguments[0], v = n.arguments[1];
          const init = a ? initOf(a) : null;
          const lit = a ? literalText(a) ?? (init !== null ? literalText(init) : null) : null;
          const vlit = v ? literalText(v) : null;
          if (v && (lit === null || vlit === null || /url\(|javascript:/i.test(vlit))) { if (lit !== null && NON_URL_STYLE_PROPS.some((p) => p.name === camelProp(lit))) styleWrites.push({ line: lineOf(n), text: text(n), fn: fnOf(n), on: recv, name: camelProp(lit), through: "style" }); else urlWriteAt(n, recv + ".setProperty(" + (lit !== null ? JSON.stringify(lit) : flat(a.getText(sf))) + ")", flat(v.getText(sf)), v); }
        }
        if ((name === "setAttribute" || name === "setAttributeNS") && !isBodyToken(obj)) {   // the attribute's name: a literal (a constant resolved through its declaration counts) not naming a handler passes; the rest is a site read by hand
          const ai = name === "setAttributeNS" ? 1 : 0, a = n.arguments[ai], v = n.arguments[ai + 1];
          const init = a ? initOf(a) : null;
          const lit = a ? literalText(a) ?? (init !== null ? literalText(init) : null) : null;
          const on = recv;
          if (lit === null || /^on/i.test(lit)) attrNames.push({ line: lineOf(n), text: text(n), fn: fnOf(n), on, name: a ? flat(a.getText(sf)) : "" });
          // the attribute's VALUE (the verifiers' census-1 of the round-7 build: the URL axis read the assignment spelling alone, so
          // `a.setAttribute("href", path)` passed): a value that is not a literal, or a javascript: literal, under a name the census
          // cannot read as a literal or one it does not know as carrying no URL, is a URL write read by hand; a handler name is the
          // attribute rule's above; an aria-* or data-* name, or one NON_URL_ATTRS lists, carries no URL and passes, classed
          const vlit = v ? literalText(v) : null;
          if (v && !(lit !== null && /^on/i.test(lit)) && (vlit === null || /^\s*javascript:/i.test(vlit))) {
            if (lit !== null && (/^(?:aria|data)-/.test(lit) || NON_URL_ATTRS.some((e) => e.name === lit))) attrWrites.push({ line: lineOf(n), text: text(n), fn: fnOf(n), on, name: lit });
            else urlWriteAt(n, on + "." + name + "(" + (lit !== null ? JSON.stringify(lit) : flat(a.getText(sf))) + ")", flat(v.getText(sf)), v);
          }
        }
      } else if (ts.isElementAccessExpression(c)) computed.push({ line: lineOf(n), text: text(n) });
      else if (ts.isIdentifier(c)) { const g = globalOf(c); if (g !== null && STRING_ROAD_CALLEES.includes(g) && !isFunction(n.arguments[0])) stringRoads.push({ line: lineOf(n), text: text(n), callee: c.text + (g === c.text ? "" : " (bound to " + g + ")") }); else if (g === "open") urlCall(n, c.text); }
      else if (c.kind === ts.SyntaxKind.ImportKeyword) stringRoads.push({ line: lineOf(n), text: text(n), callee: "import" });
      else if (c.kind !== ts.SyntaxKind.SuperKeyword) oddCallee.push({ line: lineOf(n), text: text(n) });
    } else if (ts.isNewExpression(n)) {
      if (globalOf(n.expression) === "Function") stringRoads.push({ line: lineOf(n), text: text(n), callee: calleeText(n) });
    } else if (ts.isBinaryExpression(n) && isAssignOp(n.operatorToken.kind)) {
      const op = n.operatorToken.getText(sf), left = peel(n.left), value = flat(n.right.getText(sf));
      if (ts.isArrayLiteralExpression(left) || ts.isObjectLiteralExpression(left)) for (const { target, key } of targetsOf(left)) { if (key) keyRead(key, n); classWrite(n, target, "a value destructured from `" + value + "`", op); }
      else classWrite(n, left, value, op, n.right);   // the URL axis reads the target inside classWrite, with every other arm's (the round-8 fixes)
    } else if (isIncDec(n)) classWrite(n, n.operand, "", n.operator === ts.SyntaxKind.PlusPlusToken ? "++" : "--");
    else if ((ts.isForOfStatement(n) || ts.isForInStatement(n)) && !ts.isVariableDeclarationList(n.initializer)) for (const { target, key } of targetsOf(n.initializer)) { if (key) keyRead(key, n); classWrite(n, target, "each of `" + flat(n.expression.getText(sf)) + "`", "of"); }
    if (ts.isBindingElement(n) && ts.isObjectBindingPattern(n.parent)) keyRead(n.propertyName ?? (n.name as ts.PropertyName), n.parent);
    if (ts.isCallExpression(n) || ts.isNewExpression(n)) { const foreign = foreignCallee(n); for (const a of n.arguments ?? []) handedIn(n, a, (x) => x, foreign); }
    if ((ts.isVariableDeclaration(n) || ts.isParameter(n)) && ts.isIdentifier(n.name) && n.name.text === "body" && !ts.isFunctionTypeNode(n.parent) && !ts.isMethodSignature(n.parent)) {   // a declaration of the sanctioned name: the viewer's own alone
      if (ts.isVariableDeclaration(n)) { if (!n.initializer || flat(n.initializer.getText(sf)) !== BODY_DECL_INIT) bodyDecls.push({ line: lineOf(n), text: text(n.parent.parent), why: "declares `body` as " + (n.initializer ? "`" + flat(n.initializer.getText(sf)).slice(0, 80) + "`" : "nothing") + ", not the viewer's own `" + BODY_DECL_INIT + "`: a second binding of the sanctioned name wears the first read's every pass (a declaration, a listed callee's argument) and the second read's seat key" }); }
      else { const f = nameOfFn(n.parent); if (!f || !BODY_HANDED_TO.some((h) => h.own && h.callee.split(".").pop() === f)) bodyDecls.push({ line: lineOf(n), text: text(n), why: "declares a parameter named `body` in " + (f ?? "an unnamed function") + ", which BODY_HANDED_TO does not list as reading the body under its own parameter: the census reads that function's member accesses as the viewer's, so the name passes only where the hand read says the parameter IS the body" }); }
    }
    if ((ts.isIdentifier(n) && isReference(n)) || ts.isPropertyAccessExpression(n)) { const g = globalOf(n); if (g !== null && SITE_RECEIVERS.includes(g) && !receiverOfMemberCall(n)) reflectionReads.push({ line: lineOf(n), text: text(effectiveParent(n)), name: g, as: flat(n.getText(sf)) }); }
    if ((ts.isPropertyAccessExpression(n) || ts.isElementAccessExpression(n)) && !isCallee(n)) {
      const name = memberName(n);
      if (name !== null) { if ((SEAT_CALLS.includes(name) || SITE_CALLS.includes(name)) && !ownedByFirstRead(n) && !isBodyToken(memberObject(n))) handedOut.push({ line: lineOf(n), text: text(effectiveParent(n)), name }); }
      else if (ts.isElementAccessExpression(n) && !ts.isNumericLiteral(n.argumentExpression) && !onlyRead(n)) indexReads.push({ line: lineOf(n), text: text(effectiveParent(n)), fn: fnOf(n), on: flat(strip(n.expression).getText(sf)) });
    }
    ts.forEachChild(n, visit);
  };
  visit(sf);
  return { sites, computed, unknown, handedOut, oddCallee, indexReads, handedNodes, stringRoads, urlWrites, writes, computedWrites, handlerStrings, oddTargets, bodyWrites, reflectionReads, attrNames, destructured, attrWrites, bodyDecls, elementsHanded, styleWrites };
}
/** A seat in file-view.ts on a receiver other than the `body` token, READ BY HAND and listed as ONE seat (the round-6 review's
 *  cluster A, 2026-09-20): the nearest named function around it (`in`), the receiver's spelling (`on`), the form (`via`) and
 *  WHAT IT SEATS (`seats`: the seated arguments as spelled, the value assigned, or a site-read call's arguments, as
 *  SeatSite says), with what the receiver is (`is`), which is the hand read's claim: that this seat lands no child in the
 *  body; for a receiver that is a bare name, the declaration it is bound to (`decl`), and for one bound by `let` or `var`
 *  the one expression every write to it assigns (`holds`), without which the seat is refused as reassignable; and, for the
 *  one case of a seat spelled byte for byte alike more than once in one function (codeBlock's two branches), how many
 *  times (`times`, each read; one otherwise); and the declaration of each seated argument that is a bare name (`seatedBy`,
 *  as SeatSite spells it; the verifiers' census-2 of the round-7 build, 2026-09-20: without it a second binding wearing the
 *  seated name passed on the receiver's read alone). A seat the
 *  table does not list fails the census with its line, whatever produced the receiver and however close a listed entry
 *  stands (a second seat at a listed site is a second entry, read where it stands: one entry is one seat SPELLING, and a seat
 *  spelled byte for byte alike in two branches of one function declares `times` and is read at each), an entry the source has
 *  no seat for fails it too, and an entry two seats match fails unless it says `times`, so the table is the live set of seats
 *  and nothing more (the round-5
 *  review, 2026-09-20: before this the census refused a closed list of dangerous forms and passed every other seat unread;
 *  the round-6 review: keyed on the function, receiver and form, one entry covered every seat on its binding). A body
 *  root's own children (a hint inside the failure pane, the glyph inside a loader) are seats inside the root, not beside
 *  it, and are listed as such. */
type SeatRead = { in: string; on: string; via: string; seats: string; is: string; decl?: string; holds?: string; times?: number; seatedBy?: string };
const SEATS_READ_BY_HAND: SeatRead[] = [
  { in: "<module>", on: "Object", via: "entries", seats: "{bash, sh, shell, python, py, javascript, js, typescript, ts, json, xml, html, css, markdown, md, diff, yaml, yml}", is: "Object.entries over the highlighter's language table at module load, a literal record of grammars; each is registered with hljs; no element is touched", decl: "a global" },
  { in: "textSizeControl", on: "trigger", via: "innerHTML =", seats: "ICON_ZOOM", is: "the zoom button, built here by el(); its glyph (ICON_ZOOM, a constant SVG string from icons.ts) goes inside it", decl: "const trigger = el(\"button\", \"fileview-btn fileview-icon fileview-zoom-btn\") as HTMLButtonElement" },
  { in: "textSizeControl", on: "menu", via: "appendChild", seats: "b", seatedBy: "b = const b of buttons", is: "the zoom flyout, built here by el(); a step button (b, built in the loop over the steps) goes inside it", decl: "const menu = el(\"div\", \"fileview-zoom-menu\")" },
  { in: "textSizeControl", on: "wrap", via: "appendChild", seats: "trigger", seatedBy: "trigger = const trigger = el(\"button\", \"fileview-btn fileview-icon fileview-zoom-btn\") as HTMLButtonElement", is: "the control's own span, built here by el() and seated in the bar's actions by the viewers (viewGroup, acts); the zoom button goes inside it", decl: "const wrap = el(\"span\", \"fileview-zoom\")" },
  { in: "textSizeControl", on: "wrap", via: "appendChild", seats: "menu", seatedBy: "menu = const menu = el(\"div\", \"fileview-zoom-menu\")", is: "the same span; the flyout goes inside it", decl: "const wrap = el(\"span\", \"fileview-zoom\")" },
  { in: "loaderEl", on: "load", via: "innerHTML =", seats: "'<img src=\"/media/romp-swirl-glyph.svg\" alt=\"\"><span>romp</span>' + '<i class=\"fileview-dot\"></i><i class=\"fileview-dot\"></i><i class=\"fileview-dot\"></i>'", is: "the loader this builder returns, div.fileview-load; its glyph markup (a literal string: the swirl img, the word, three dots) goes inside it", decl: "const load = el(\"div\", \"fileview-load\")" },
  { in: "apply", on: "unit", via: "replaceChildren", seats: "", is: "the action's own span (div.fileview-gh), built in its mount and returned to the viewer, which seats it in the bar; emptied when the kernel answers with no URL", decl: "const unit = el(\"span\", \"fileview-gh\")" },
  { in: "apply", on: "unit", via: "replaceChildren", seats: "a", seatedBy: "a = const a = el(\"a\", \"fileview-btn\") as HTMLAnchorElement", is: "the same span; the GitHub link anchor (a, built here by el()) goes inside it", decl: "const unit = el(\"span\", \"fileview-gh\")" },
  { in: "openFileView", on: "bar", via: "appendChild", seats: "back", seatedBy: "back = const back = el(\"button\", \"fileview-btn fileview-back\") as HTMLButtonElement", is: "the title bar, a child of the card beside main; the back button goes in it", decl: "const bar = el(\"div\", \"fileview-bar\")" },
  { in: "openFileView", on: "name", via: "appendChild", seats: "dir", seatedBy: "dir = const dir = el(\"span\", \"fileview-dir\")", is: "the file name in the bar; its directory span goes in it", decl: "const name = el(\"div\", \"fileview-name\")" },
  { in: "openFileView", on: "name", via: "appendChild", seats: "base", seatedBy: "base = const base = el(\"span\", \"fileview-base\")", is: "the same name; its base-name span goes in it", decl: "const name = el(\"div\", \"fileview-name\")" },
  { in: "openFileView", on: "sess", via: "replaceChildren", seats: "...hostNameNodes(owner.name, sid)", is: "the session tag in the bar, a const built by el() when the file was opened from a session (the round-6 review's correctness-5: it was a let assigned inside the branch, whose declaration said nothing about what it held here); the host and name nodes go in it", decl: "const sess = owner ? el(\"span\", \"fileview-sess\") : null" },
  { in: "openFileView", on: "seg", via: "appendChild", seats: "b", seatedBy: "b = const b = el(\"button\", \"fileview-btn\") as HTMLButtonElement", is: "the Rendered|Raw pair in the view group; a format button (b, built in the loop) goes in it", decl: "const seg = el(\"span\", \"fileview-seg\")" },
  { in: "openFileView", on: "viewGroup", via: "appendChild", seats: "seg", seatedBy: "seg = const seg = el(\"span\", \"fileview-seg\")", is: "the view group of the actions row; the format pair goes in it", decl: "const viewGroup = el(\"span\", \"fileview-group fileview-group-view\")" },
  { in: "openFileView", on: "viewGroup", via: "appendChild", seats: "outlineBtn", seatedBy: "outlineBtn = const outlineBtn = el(\"button\", \"fileview-btn fileview-outline-btn\") as HTMLButtonElement", is: "the same group; the outline button goes in it", decl: "const viewGroup = el(\"span\", \"fileview-group fileview-group-view\")" },
  { in: "openOutline", on: "pop", via: "appendChild", seats: "r", seatedBy: "r = const r = el(\"div\", \"fileview-outline-row\")", is: "the headings popover, built here by el(); a row (r, built in the loop over the headings) goes in it", decl: "const pop = el(\"div\", \"fileview-outline\")" },
  { in: "openOutline", on: "box", via: "appendChild", seats: "pop", seatedBy: "pop = const pop = el(\"div\", \"fileview-outline\")", is: "the card; the popover goes in it, beside the bar and main", decl: "const box = el(\"div\", \"fileview\")" },
  { in: "openFileView", on: "viewGroup", via: "appendChild", seats: "textSize.wrap", is: "the same group; the zoom control's span goes in it", decl: "const viewGroup = el(\"span\", \"fileview-group fileview-group-view\")" },
  { in: "openFileView", on: "viewGroup", via: "appendChild", seats: "srcBtn", seatedBy: "srcBtn = const srcBtn = el(\"button\", \"fileview-btn\") as HTMLButtonElement", is: "the same group; the source button goes in it", decl: "const viewGroup = el(\"span\", \"fileview-group fileview-group-view\")" },
  { in: "openFileView", on: "editBtn", via: "innerHTML =", seats: "ICON_EDIT", is: "the Edit button in the file group; its glyph (ICON_EDIT, a constant SVG string) goes inside it", decl: "const editBtn = el(\"button\", \"fileview-btn\") as HTMLButtonElement" },
  { in: "openFileView", on: "fileGroup", via: "appendChild", seats: "editBtn", seatedBy: "editBtn = const editBtn = el(\"button\", \"fileview-btn\") as HTMLButtonElement", is: "the file group of the actions row; the Edit button goes in it", decl: "const fileGroup = el(\"span\", \"fileview-group fileview-group-file\")" },
  { in: "openFileView", on: "fileGroup", via: "appendChild", seats: "saveBtn", seatedBy: "saveBtn = const saveBtn = el(\"button\", \"fileview-btn\") as HTMLButtonElement", is: "the same group; the Save button goes in it", decl: "const fileGroup = el(\"span\", \"fileview-group fileview-group-file\")" },
  { in: "openFileView", on: "fileGroup", via: "appendChild", seats: "cancelBtn", seatedBy: "cancelBtn = const cancelBtn = el(\"button\", \"fileview-btn\") as HTMLButtonElement", is: "the same group; the Cancel button goes in it", decl: "const fileGroup = el(\"span\", \"fileview-group fileview-group-file\")" },
  { in: "openFileView", on: "load", via: "innerHTML =", seats: "'<img src=\"/media/romp-swirl-glyph.svg\" alt=\"\"><span>romp</span>' + '<i class=\"fileview-dot\"></i><i class=\"fileview-dot\"></i><i class=\"fileview-dot\"></i>'", is: "the open's loader (a body root: body.appendChild(load) is resolved by the body's read); its glyph markup (a literal string) goes inside it", decl: "const load = el(\"div\", \"fileview-load\")" },
  { in: "openFileView", on: "main", via: "appendChild", seats: "body", seatedBy: "body = const body = el(\"div\", \"fileview-body\")", is: "the card's main column, the body's PARENT: the body itself is seated in it, so this seat is the body's, not a child in it", decl: "const main = el(\"div\", \"fileview-main\")" },
  { in: "aside", on: "main", via: "appendChild", seats: "node", seatedBy: "node = a parameter of aside; writes: none", is: "the same column, through the seam's aside hook: an action's aside (node, the element the action hands the hook) is seated beside the body, in main, not in the body", decl: "const main = el(\"div\", \"fileview-main\")" },
  { in: "openFileView", on: "a", via: "mount", seats: "ctx", seatedBy: "ctx = const ctx = { path, sid: sid || null, todoId: opts?.todoId ?? null, body: () => body, mode:  ... sha256:306d4d2acecf796e87372abbe8fcb5ee7eb39d67c4a9618585138f108505d0c9", is: "a registered action's mount (the GitHub link, the Comments panel), handed the action context and returning the element the viewer then seats in the file group (fileGroup.appendChild(n), listed here); the mount seats nothing itself", decl: "const a of fileViewActions" },
  { in: "openFileView", on: "fileGroup", via: "appendChild", seats: "n", seatedBy: "n = const n = a.mount(ctx)", is: "the same group; a registered action's mount result (n, the element a.mount(ctx) returned: the GitHub link's span, the Comments panel's button) goes in it", decl: "const fileGroup = el(\"span\", \"fileview-group fileview-group-file\")" },
  { in: "openFileView", on: "dl", via: "innerHTML =", seats: "ICON_DOWNLOAD", is: "the Download button in the file group; its glyph (ICON_DOWNLOAD, a constant SVG string) goes inside it", decl: "const dl = el(\"button\", \"fileview-btn\") as HTMLButtonElement" },
  { in: "openFileView", on: "fileGroup", via: "appendChild", seats: "dl", seatedBy: "dl = const dl = el(\"button\", \"fileview-btn\") as HTMLButtonElement", is: "the same group; the Download button goes in it", decl: "const fileGroup = el(\"span\", \"fileview-group fileview-group-file\")" },
  { in: "openFileView", on: "fileGroup", via: "appendChild", seats: "print.button", is: "the same group; the Print button (installFilePrint's) goes in it", decl: "const fileGroup = el(\"span\", \"fileview-group fileview-group-file\")" },
  { in: "openFileView", on: "copy", via: "innerHTML =", seats: "ICON_COPY", is: "the Copy button in the file group; its glyph (ICON_COPY, a constant SVG string) goes inside it", decl: "const copy = el(\"button\", \"fileview-btn fileview-icon\") as HTMLButtonElement" },
  { in: "copySay", on: "copy", via: "innerHTML =", seats: "icon", is: "the same Copy button; the acknowledgement swaps its glyph (icon, one of the constant SVG strings copySay is handed)", decl: "const copy = el(\"button\", \"fileview-btn fileview-icon\") as HTMLButtonElement" },
  { in: "openFileView", on: "fileGroup", via: "appendChild", seats: "copy", seatedBy: "copy = const copy = el(\"button\", \"fileview-btn fileview-icon\") as HTMLButtonElement", is: "the same group; the Copy button goes in it", decl: "const fileGroup = el(\"span\", \"fileview-group fileview-group-file\")" },
  { in: "openFileView", on: "acts", via: "appendChild", seats: "viewGroup", seatedBy: "viewGroup = const viewGroup = el(\"span\", \"fileview-group fileview-group-view\")", is: "the actions row in the bar; the view group goes in it", decl: "const acts = el(\"div\", \"fileview-acts\")" },
  { in: "openFileView", on: "acts", via: "appendChild", seats: "fileGroup", seatedBy: "fileGroup = const fileGroup = el(\"span\", \"fileview-group fileview-group-file\")", is: "the same row; the file group goes in it", decl: "const acts = el(\"div\", \"fileview-acts\")" },
  { in: "openFileView", on: "acts", via: "appendChild", seats: "close", seatedBy: "close = const close = el(\"button\", \"fileview-btn fileview-close\") as HTMLButtonElement", is: "the same row; the close button goes in it", decl: "const acts = el(\"div\", \"fileview-acts\")" },
  { in: "openFileView", on: "bar", via: "appendChild", seats: "name", seatedBy: "name = const name = el(\"div\", \"fileview-name\")", is: "the same bar; the file name goes in it", decl: "const bar = el(\"div\", \"fileview-bar\")" },
  { in: "openFileView", on: "bar", via: "appendChild", seats: "sess", seatedBy: "sess = const sess = owner ? el(\"span\", \"fileview-sess\") : null", is: "the same bar; the session tag goes in it (when the file was opened from a session)", decl: "const bar = el(\"div\", \"fileview-bar\")" },
  { in: "openFileView", on: "bar", via: "appendChild", seats: "acts", seatedBy: "acts = const acts = el(\"div\", \"fileview-acts\")", is: "the same bar; the actions row goes in it", decl: "const bar = el(\"div\", \"fileview-bar\")" },
  { in: "openFileView", on: "box", via: "appendChild", seats: "bar", seatedBy: "bar = const bar = el(\"div\", \"fileview-bar\")", is: "the card (div.fileview); the bar goes in it", decl: "const box = el(\"div\", \"fileview\")" },
  { in: "openFileView", on: "box", via: "appendChild", seats: "main", seatedBy: "main = const main = el(\"div\", \"fileview-main\")", is: "the same card; main goes in it", decl: "const box = el(\"div\", \"fileview\")" },
  { in: "openFileView", on: "wrap", via: "appendChild", seats: "box", seatedBy: "box = const box = el(\"div\", \"fileview\")", is: "the overlay wrapper; the card goes in it", decl: "const wrap = el(\"div\")" },
  { in: "openFileView", on: "document.body", via: "appendChild", seats: "wrap", seatedBy: "wrap = const wrap = el(\"div\")", is: "the page's body, not the viewer's; the overlay wrapper goes in it" },
  { in: "noteBar", on: "box", via: "insertBefore", seats: "bar2", seatedBy: "bar2 = const bar2 = el(\"div\", \"fileview-err\")", is: "the card; a notice bar (bar2, div.fileview-err built here) goes in it above main, outside the body (a body root of the same class is seated by the body's own replaceChildren, read separately)", decl: "const box = el(\"div\", \"fileview\")" },
  { in: "imgFailed", on: "why", via: "appendChild", seats: "hint", seatedBy: "hint = const hint = el(\"div\", \"fileview-err-hint\")", is: "the picture failure pane (div.fileview-err), a body root; its hint goes inside it", decl: "const why = el(\"div\", \"fileview-err\")" },
  { in: "imgFailed", on: "why", via: "appendChild", seats: "offer", seatedBy: "offer = const offer = el(\"button\", \"fileview-btn fileview-err-dl\") as HTMLButtonElement", is: "the same pane; its download offer goes inside it", decl: "const why = el(\"div\", \"fileview-err\")" },
  { in: "editorChunk", on: "document.head", via: "appendChild", seats: "sc", seatedBy: "sc = const sc = document.createElement(\"script\")", is: "the page's head; the editor chunk's script tag goes in it" },
  { in: "pdfChunkLoad", on: "document.head", via: "appendChild", seats: "sc", seatedBy: "sc = const sc = document.createElement(\"script\")", is: "the page's head; the PDF chunk's script tag goes in it" },
  { in: "fallback", on: "col", via: "prepend", seats: "note", seatedBy: "note = const note = el(\"div\", \"fileview-err\")", is: "the kept frame's parent (col = kept ? kept.parentElement : null; shownFrame finds the frame the body holds, and pdfBlock seats its frame inside its div.fileview-pdffall column and nowhere else), so the column, a body root; the notice goes inside it", decl: "const col = kept ? kept.parentElement : null" },
  { in: "fallback", on: "fall", via: "prepend", seats: "note", seatedBy: "note = const note = el(\"div\", \"fileview-err\")", is: "a fresh pdfBlock column (a body root: body.replaceChildren(fall) is resolved by the body's read); the notice goes inside it", decl: "const fall = pdfBlock(url, path)" },
  { in: "showPdfPages", on: "wait", via: "innerHTML =", seats: "'<img src=\"/media/romp-swirl-glyph.svg\" alt=\"\"><span>romp</span>' + '<i class=\"fileview-dot\"></i><i class=\"fileview-dot\"></i><i class=\"fileview-dot\"></i>'", is: "the pages loader (div.fileview-load: a body root through body.replaceChildren(wait, host), or inside the column through col.prepend(wait)); its glyph markup (a literal string) goes inside it", decl: "const wait = el(\"div\", \"fileview-load\")" },
  { in: "showPdfPages", on: "col", via: "prepend", seats: "wait", seatedBy: "wait = const wait = el(\"div\", \"fileview-load\")", is: "the kept frame's parent, the same column as fallback's; the pages loader goes inside it", decl: "const col = kept ? kept.parentElement : null" },
  { in: "showPdfPages", on: "pdf", via: "render", seats: "bytes, host, {maxBytes, signal, onPage, onPageError}", seatedBy: "bytes = a destructured binding of a parameter of the callback handed to Promise.all([pdfChunkLoad(), blob.arrayBuffer()]).then; writes: none; host = const host = el(\"div\", \"fileview-pdfhost\")", is: "the PDF chunk's render, handed the bytes, the host (div.fileview-pdfhost, a body root: body.replaceChildren(wait, host) is resolved by the body's read) and its options; the page canvases go inside that root", decl: "a destructured binding of a parameter of the callback handed to Promise.all([pdfChunkLoad(), blob.arrayBuffer()]).then" },
  { in: "enterEdit", on: "wait", via: "innerHTML =", seats: "'<img src=\"/media/romp-swirl-glyph.svg\" alt=\"\"><span>romp</span>' + '<i class=\"fileview-dot\"></i><i class=\"fileview-dot\"></i><i class=\"fileview-dot\"></i>'", is: "the chunk loader (div.fileview-load, a body root: body.replaceChildren(wait) is resolved by the body's read); its glyph markup (a literal string) goes inside it", decl: "const wait = el(\"div\", \"fileview-load\")" },
  { in: "enterEdit", on: "ed", via: "mount", seats: "host, {text, ext, onChange, onSave, ...(pending ? { track: { suggestions: pending.records, authorColor: pending.authorColor, onDecisions: () => { dirty = cm!.value() !== norm(text!) || decided(); } } } : {})}", seatedBy: "host = const host = el(\"div\", \"fileview-cm\")", is: "the editor chunk's mount into host, the div.fileview-cm root (a body root: body.replaceChildren(host) is resolved by the body's read), with its options; the CodeMirror editor goes inside that root, not beside it", decl: "a parameter of the callback handed to editorChunk().then" },
  { in: "showSaveError", on: "bar2", via: "appendChild", seats: "re", seatedBy: "re = const re = el(\"button\", \"fileview-btn fileview-err-dl\") as HTMLButtonElement", is: "noteBar's notice bar in the card; its retry button goes in it", decl: "const bar2 = noteBar(err)" },
  { in: "raiseDiskBar", on: "bar2", via: "appendChild", seats: "re", seatedBy: "re = const re = el(\"button\", \"fileview-btn fileview-err-act\") as HTMLButtonElement", is: "noteBar's notice bar in the card; its reload button goes in it", decl: "const bar2 = noteBar(words)" },
  { in: "fetchFile", on: "Object", via: "assign", seats: "new Error(t || (\"HTTP \" + r.status)), {status}", is: "Object.assign onto a fresh Error, setting its status for the failure road; the target is the Error, never an element", decl: "a global" },
  { in: "fetchFile", on: "why", via: "appendChild", seats: "hint", seatedBy: "hint = const hint = el(\"div\", \"fileview-err-hint\")", is: "the fetch failure pane (div.fileview-err), a body root; its hint goes inside it", decl: "const why = el(\"div\", \"fileview-err\")" },
  { in: "fetchFile", on: "why", via: "appendChild", seats: "offer", seatedBy: "offer = const offer = el(\"button\", \"fileview-btn fileview-err-dl\") as HTMLButtonElement", is: "the same pane; its download offer goes inside it", decl: "const why = el(\"div\", \"fileview-err\")" },
  { in: "openUrlView", on: "name", via: "appendChild", seats: "dir", seatedBy: "dir = const dir = el(\"span\", \"fileview-dir\")", is: "the file name in the URL viewer's bar; its directory span goes in it", decl: "const name = el(\"div\", \"fileview-name\")" },
  { in: "openUrlView", on: "name", via: "appendChild", seats: "base", seatedBy: "base = const base = el(\"span\", \"fileview-base\")", is: "the same name; its base-name span goes in it", decl: "const name = el(\"div\", \"fileview-name\")" },
  { in: "openUrlView", on: "acts", via: "appendChild", seats: "b", seatedBy: "b = const b = el(\"button\", \"fileview-btn\") as HTMLButtonElement", is: "the URL viewer's actions row in the bar; a format button (b, built in the loop) goes in it", decl: "const acts = el(\"div\", \"fileview-acts\")" },
  { in: "openUrlView", on: "acts", via: "appendChild", seats: "textSize.wrap", is: "the same row; the zoom control's span goes in it", decl: "const acts = el(\"div\", \"fileview-acts\")" },
  { in: "openUrlView", on: "acts", via: "appendChild", seats: "linkOut()", is: "the same row; the link out to the URL goes in it", decl: "const acts = el(\"div\", \"fileview-acts\")" },
  { in: "openUrlView", on: "acts", via: "appendChild", seats: "copy", seatedBy: "copy = const copy = el(\"button\", \"fileview-btn\") as HTMLButtonElement", is: "the same row; the Copy button goes in it", decl: "const acts = el(\"div\", \"fileview-acts\")" },
  { in: "openUrlView", on: "acts", via: "appendChild", seats: "close", seatedBy: "close = const close = el(\"button\", \"fileview-btn fileview-close\") as HTMLButtonElement", is: "the same row; the close button goes in it", decl: "const acts = el(\"div\", \"fileview-acts\")" },
  { in: "openUrlView", on: "bar", via: "appendChild", seats: "name", seatedBy: "name = const name = el(\"div\", \"fileview-name\")", is: "the URL viewer's title bar, a child of the card beside the body; the name goes in it", decl: "const bar = el(\"div\", \"fileview-bar\")" },
  { in: "openUrlView", on: "bar", via: "appendChild", seats: "acts", seatedBy: "acts = const acts = el(\"div\", \"fileview-acts\")", is: "the same bar; the actions row goes in it", decl: "const bar = el(\"div\", \"fileview-bar\")" },
  { in: "openUrlView", on: "acts", via: "insertBefore", seats: "print.button", is: "the same row; the Print button goes in it before Copy", decl: "const acts = el(\"div\", \"fileview-acts\")" },
  { in: "openUrlView", on: "box", via: "appendChild", seats: "bar", seatedBy: "bar = const bar = el(\"div\", \"fileview-bar\")", is: "the URL viewer's card (div.fileview), the body's PARENT there; the bar goes in it", decl: "const box = el(\"div\", \"fileview\")" },
  { in: "openUrlView", on: "box", via: "appendChild", seats: "body", seatedBy: "body = const body = el(\"div\", \"fileview-body\")", is: "the same card: the body itself is seated in it, so this seat is the body's, not a child in it", decl: "const box = el(\"div\", \"fileview\")" },
  { in: "openUrlView", on: "wrap", via: "appendChild", seats: "box", seatedBy: "box = const box = el(\"div\", \"fileview\")", is: "the overlay wrapper; the card goes in it", decl: "const wrap = el(\"div\")" },
  { in: "openUrlView", on: "document.body", via: "appendChild", seats: "wrap", seatedBy: "wrap = const wrap = el(\"div\")", is: "the page's body, not the viewer's; the overlay wrapper goes in it" },
  { in: "fail", on: "why", via: "appendChild", seats: "hint", seatedBy: "hint = const hint = el(\"div\", \"fileview-err-hint\")", is: "the URL viewer's failure pane (div.fileview-err), a body root; its hint goes inside it", decl: "const why = el(\"div\", \"fileview-err\")" },
  { in: "fail", on: "why", via: "appendChild", seats: "linkOut()", is: "the same pane; the link out to the URL (linkOut() builds an anchor) goes inside it", decl: "const why = el(\"div\", \"fileview-err\")" },
  { in: "startDownload", on: "document.body", via: "appendChild", seats: "a", seatedBy: "a = const a = document.createElement(\"a\")", is: "the page's body; a temporary anchor for the download click goes in it and is removed" },
  { in: "codeBlock", on: "code", via: "innerHTML =", seats: "wrapNumberedHtml(hl !== null ? hl : escapeHtml(text))", is: "the code element inside the code root's pre (the numbered branch); the highlighted or escaped HTML, wrapped in numbered rows, goes in it", decl: "const code = el(\"code\", \"hljs\")" },
  { in: "codeBlock", on: "pre", via: "appendChild", seats: "code", seatedBy: "code = const code = el(\"code\", \"hljs\")", is: "the pre inside the code root; the code element goes in it (written alike in the numbered and the plain branch, each read)", times: 2, decl: "const pre = el(\"pre\", \"fileview-pre\")" },
  { in: "codeBlock", on: "wrap", via: "appendChild", seats: "pre", seatedBy: "pre = const pre = el(\"pre\", \"fileview-pre\")", is: "the code root itself (div.fileview-code), which this builder returns; the pre goes inside it (written alike in the numbered and the plain branch, each read)", times: 2, decl: "const wrap = el(\"div\", \"fileview-code\")" },
  { in: "codeBlock", on: "code", via: "innerHTML =", seats: "hl", is: "the same code element (the plain branch, when the highlighter answered); the highlighted HTML goes in it", decl: "const code = el(\"code\", \"hljs\")" },
  { in: "codeBlock", on: "wrap", via: "appendChild", seats: "gutter", seatedBy: "gutter = const gutter = el(\"div\", \"fileview-gutter\")", is: "the same code root; the line-number gutter goes inside it (the plain branch)", decl: "const wrap = el(\"div\", \"fileview-code\")" },
  { in: "mdBlock", on: "base", via: "call", seats: "marked, t", seatedBy: "marked = an import; t = a parameter of the callback handed to viewerHtml; writes: none", is: "marked's default walkTokens, called with marked as this over each token (base = marked.defaults.walkTokens): it walks the token tree and seats nothing", decl: "const base = marked.defaults.walkTokens" },
  { in: "mdBlock", on: "box", via: "replaceChildren", seats: "...Array.from(clean.childNodes)", is: "the markdown root itself (div.fileview-md), which this builder returns; the sanitized body's nodes (`clean`, the sanitizer's own document's body, over which the fence pass and the figure chain ran before this adoption, the gate before adoption of 2026-09-20) go inside it", decl: "const box = el(\"div\", \"fileview-md\")" },
  { in: "mdBlock", on: "codeEl", via: "innerHTML =", seats: "hljs.highlight(raw, { language: lang }).value", is: "a code element of the sanitized document inside the markdown root; the highlighted HTML goes in it", decl: "const codeEl = node as HTMLElement" },
  { in: "onError", on: "parent", via: "insertBefore", seats: "label", seatedBy: "label = const label = el(\"span\", FIGERR_CLASS)", is: "the parent of a failed figure's anchor (parent = anchor.parentNode): figureOf takes an img inside .fileview-md alone and figureAnchor climbs wrappers around that img, so the parent is inside the markdown root or is the root itself, never the body; the label goes beside the anchor (the reference child, anchor.nextSibling, is the argument axis's read)", decl: "const parent = anchor.parentNode" },
  { in: "imgBlock", on: "box", via: "appendChild", seats: "img", seatedBy: "img = const img = el(\"img\", \"fileview-img\") as HTMLImageElement", is: "the picture root itself (div.fileview-imgbox), which this builder returns; the img goes inside it", decl: "const box = el(\"div\", \"fileview-imgbox\")" },
  { in: "pdfBlock", on: "col", via: "appendChild", seats: "frame", seatedBy: "frame = const frame = el(\"iframe\", \"fileview-frame\") as HTMLIFrameElement", is: "the PDF column itself (div.fileview-pdffall), which this builder returns; the frame goes inside it", decl: "const col = el(\"div\", \"fileview-pdffall\")" },
  { in: "initFileView", on: "gh", via: "apply", seats: "String(m.url || \"\"), String(m.reason || \"\")", is: "the git-link hooks' apply, told the URL and the reason the kernel answered (gh = gitHooks, its own name since the census holds a receiver to one declaration per function: `h` is the edit hooks' in the branches below); an object's method, not Function.prototype.apply", decl: "const gh = gitHooks" },
];
/** The one initializer a declaration named `body` may carry in file-view.ts, the viewer's own body element (both viewers build
 *  it so); a declaration of the name with any other initializer, or a parameter of the name in a function BODY_HANDED_TO does
 *  not list as reading the body under its own parameter, fails the census with its line (the verifiers' census-2 of the round-7
 *  build, 2026-09-20: the first read passed every declaration and every parameter of the name, so a block's `const body =
 *  el("div", "fileview-mutant")` seated through the listed `main.appendChild(body)` wore the entry). */
const BODY_DECL_INIT = 'el("div", "fileview-body")';
/** An attribute name file-view.ts sets from a value that is not a literal, read by hand as carrying no URL: the browser fetches
 *  nothing and navigates nowhere by it. An `aria-*` or `data-*` name passes by that rule without an entry (assistive
 *  technology reads the first; the second is inert to the browser); every other name set from a non-literal value is the URL
 *  axis's (URL_WRITES_READ_BY_HAND) unless listed here, and a listed name the file no longer sets from a non-literal fails as
 *  stale. Empty at this head: the viewer's non-literal attribute values go to aria-*, data-*, srcset, href and the figure
 *  reference's own name, and the last three are URL writes. */
const NON_URL_ATTRS: Array<{ name: string; why: string }> = [];
/** The CSS properties file-view.ts writes through an element's `style` (an assignment, or `style.setProperty`) from a value
 *  that is not a literal and that the URL axis passes WITHOUT a hand read of the value, each listed here because the
 *  property accepts no url() value, so whatever the value is it cannot name a resource (the round-8 fixes, the round-7
 *  review's correctness-2 as its refuters corrected it, 2026-09-21: an allowlist of the url()-capable names would enumerate
 *  on the unsafe side, maskImage, borderImageSource, cursor, content and their kin missed; this list is the other side, a
 *  property not here is READ, its write a URL write until URL_WRITES_READ_BY_HAND lists it). A property that accepts url()
 *  stays out: `background` (the shorthand takes an image) is written from the session colour record at one live site and
 *  is read by hand there, never listed here. A stale name here (one the file no longer writes from a non-literal) is
 *  refused, so the list is the live set. */
const NON_URL_STYLE_PROPS: Array<{ name: string; why: string }> = [
  { name: "top", why: "an inset: a <length-percentage> or auto (CSS Positioned Layout 3); url() is not a value of it" },
  { name: "right", why: "an inset, as top" },
  { name: "left", why: "an inset, as top" },
  { name: "maxWidth", why: "a sizing limit: a <length-percentage>, none or a sizing keyword (CSS Sizing 3); url() is not a value of it" },
  { name: "maxHeight", why: "a sizing limit, as maxWidth" },
  { name: "aspectRatio", why: "a <ratio> or auto (CSS Sizing 4); url() is not a value of it" },
  { name: "color", why: "a <color> (CSS Color 4): no image, so url() is not a value of it" },
];
/** A member of a receiver read by a COMPUTED name and stored or handed on (`const at = rows[cur]`), READ BY HAND and listed by
 *  its site: the nearest named function (`in`) and the receiver's spelling (`on`), with what the receiver is (`is`), the
 *  hand read's claim that the value is no seating method of an element (the branch's verification pass finding census-1, 2026-09-20: a
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
/** A node of the tree handed to a callee (seatSites.nodeHanded): its line and text, the nearest named function (`fn`), the
 *  callee as spelled (`to`), the argument as spelled (`arg`), the NODE_MEMBERS member it reads through, and, for a name,
 *  its binding (the declaration, its kind and every write to it). */
type HandedNode = Use & { fn: string; to: string; arg: string; member: string; whole: string; shadowed?: string; unnamed?: true } & Partial<Binding>;   // `whole`: the flattened call text uncut, beside the message's `text` cut at 100; `unnamed`: an element the census could not name by shape, typed by the compiler (the round-8 fixes)
/** A URL member written from a value that is not a literal (seatSites): its line and text, the function, the target as
 *  spelled (`on`), the value as spelled (`value`) and, for a bare name, its binding. */
type UrlWrite = Use & { fn: string; on: string; value: string; shadowed?: string } & Partial<Binding>;
/** A node of the tree handed to a callee in file-view.ts, or an element the census can see by its shape handed to a callee
 *  the file does not declare, READ BY HAND and listed by its site: the nearest named function (`in`), the callee (`to`) and
 *  the argument as spelled (`arg`, with its path into a literal: `{ card: box }`), with a bare name's declaration (`decl`)
 *  and, for one bound by `let`, the one expression every write to it assigns (`holds`), how many hand-offs spelled alike the
 *  function has (`times`, one otherwise), and what the callee does with the node (`is`), which is the hand read's claim:
 *  that it seats nothing in the body through it. The round-6 review's item 7 (2026-09-20): the argument axis, whose first
 *  run is the census (the plan's P7 records the count); a hand-off the table does not list fails with its line, one bound
 *  elsewhere than the entry says fails, an entry two hand-offs match fails unless it says `times`, and an entry the source
 *  has no hand-off for fails too. `unnamed` marks an entry for a hand-off the shape rule cannot name, which the compiler's
 *  type refuses (the round-8 fixes): the census holds the mark to the road, so an entry marked for a hand-off the shape
 *  names, or unmarked for one it cannot, is refused. */
type ArgRead = { in: string; to: string; arg: string; is: string; decl?: string; holds?: string; times?: number; unnamed?: true };
const ARGS_READ_BY_HAND: ArgRead[] = [
  // Array.from over a node list: the language's copy into an array, whose elements are then only read (a tag name, a text, a style property set); the array seats nothing and is handed to no seat
  { in: "stamp", to: "Array.from", arg: "md.children", is: "the markdown root's element children copied into an array so the top-level tables among them get the body's width as a CSS variable (style.setProperty); read and styled, never seated (watchBodyWidth's stamp)" },
  { in: "headingWords", to: "Array.from", arg: "n.childNodes", is: "a heading's child nodes copied into an array and mapped to their words for the Outline's row text (headingWords recurses over each and returns a string); read, never seated" },
  { in: "foldKey", to: "Array.from", arg: "d.children", is: "a details element's element children copied into an array to find its summary's text for the fold's key; read, never seated" },
  { in: "foldBody", to: "Array.from", arg: "d.childNodes", is: "a details element's child nodes copied into an array to join their text but the summary's, the fold's body text; read, never seated" },
  { in: "mdBlock", to: "Array.from", arg: "clean.childNodes", is: "the sanitized body's child nodes (`clean`, bound by `const clean = sanitizeMd(dirty, mintHeadingIds)`, the sanitizer's own document's body) copied into an array and spread into box.replaceChildren, the markdown root's own seat (listed in SEATS_READ_BY_HAND as what that seat seats); Array.from itself seats nothing" },
  // figureAnchor's climb: p is the anchor's parent at every step, read by two predicates
  { in: "figureAnchor", to: "oneImg", arg: "p", decl: "let p = a.parentElement", holds: "a.parentElement", is: "the current anchor's parent element (p, a let the loop's head and its update both assign a.parentElement, and nothing else writes: `holds` pins it), asked whether it holds exactly one img (a querySelectorAll count); oneImg reads and seats nothing" },
  { in: "figureAnchor", to: "linkAround", arg: "p", decl: "let p = a.parentElement", holds: "a.parentElement", is: "the same parent element, asked whether it is a link holding the anchor alone (localName, children, textContent read); linkAround reads and seats nothing" },
  // a seat's reference child: the node before which the seat lands, read for its position
  { in: "onError", to: "parent.insertBefore", arg: "anchor.nextSibling", is: "the reference child of the label's seat (parent.insertBefore(label, anchor.nextSibling), the seat listed in SEATS_READ_BY_HAND): insertBefore reads its second argument for where to put the first and seats nothing through it" },
  // a selection boundary's neighbour, read for whether it is a text leaf
  { in: "boundarySide", to: "leafIsText", arg: "after", decl: "const after = node.childNodes[offset]", is: "the child node at a selection boundary's offset (a const), asked whether its first leaf is text (leafIsText walks down through firstChild and reads nodeType); it reads and seats nothing" },
  // an element the census can see by its shape (el(), a query result, a parameter typed as an element), handed to a callee this
  // file does not declare (an import): each callee read in its own module for what it does with the element (the verifiers'
  // records-1 of the round-7 build, 2026-09-20: before this the argument axis knew NODE_MEMBERS chains alone, so an imported
  // helper handed the card, the bar or the markdown root was read on no axis while the promise said every axis was)
  { in: "openFileView", to: "flash", arg: "outlineBtn", decl: "const outlineBtn = el(\"button\", \"fileview-btn fileview-outline-btn\") as HTMLButtonElement", is: "actions.ts flash: toggles the class romp-acted on the element it is handed (remove, a reflow read, add, a timed remove); the Outline button's press pulse; seats nothing" },
  { in: "openFileView", to: "pressHold", arg: "box", decl: "const box = el(\"div\", \"fileview\")", is: "actions.ts pressHold: installs a pointerdown listener on the surface (the card) and release listeners on the window, and parks a run handed to its defer until the release; seats nothing (the runs it defers are the viewer's own paints, read in this file)" },
  { in: "openFileView", to: "pressHold", arg: "main", decl: "const main = el(\"div\", \"fileview-main\")", is: "the same helper over main (the reload under a press); seats nothing" },
  { in: "openFileView", to: "selectionOpenIn", arg: "box", decl: "const box = el(\"div\", \"fileview\")", is: "path-links.ts selectionOpenIn: reads window.getSelection() and asks box.contains(anchorNode); a boolean, seats nothing" },
  { in: "openFileView", to: "installFilePrint", arg: "{ card: box }", decl: "const box = el(\"div\", \"fileview\")", is: "file-print.ts installFilePrint: the card is where the print line is seated (host.card.insertBefore(row, host.bar.nextSibling): after the bar, beside main, never in the body) and where its click, keydown and toggle listeners go; the body it is handed under the `body` key is the first read's (BODY_HANDED_TO), read by bodyReady and observed, never seated into; the button it builds is returned and seated by this file (fileGroup.appendChild(print.button), listed)" },
  { in: "openFileView", to: "installFilePrint", arg: "{ bar }", decl: "const bar = el(\"div\", \"fileview-bar\")", is: "the same call: the bar is read for where the print line goes (its nextSibling) and never written" },
  { in: "openUrlView", to: "installFilePrint", arg: "{ card: box }", decl: "const box = el(\"div\", \"fileview\")", is: "the URL viewer's install of the same flow: the print line is seated in the card after the bar (host.card.insertBefore(row, host.bar.nextSibling)); the body is read, never seated into; the button is returned and seated by this file (acts.insertBefore(print.button, copy), listed)" },
  { in: "openUrlView", to: "installFilePrint", arg: "{ bar }", decl: "const bar = el(\"div\", \"fileview-bar\")", is: "the same call: the bar is read for where the line goes and never written" },
  { in: "scrollToOffset", to: "rawRowForOffset", arg: "code", decl: "const code = body.querySelector(\"code.hljs\")", is: "anchor-map.ts rawRowForOffset: indexes the code element's rows against the source (rawIndex) and returns the row whose span holds the offset; the caller scrolls that row into view; reads, seats nothing" },
  { in: "revealRemembered", to: "renderedBlockElements", arg: "md", decl: "const md = body.querySelector(\".fileview-md\")", is: "anchor-map.ts renderedBlockElements: the elements a source block renders as, from the rendered index over the markdown root; the caller reveals each (revealFragmentTarget opens the folds around it); reads, seats nothing" },
  { in: "scrollToSourceOffset", to: "renderedBlockElements", arg: "md", decl: "const md = body.querySelector(\".fileview-md\")", times: 2, is: "the same helper, called twice in the scroll (the block's elements and, when it has none, the next block's); reads, seats nothing" },
  { in: "codeBlock", to: "linkifyFileText", arg: "code", decl: "const code = el(\"code\", \"hljs\")", times: 2, is: "file-view-links.ts linkifyFileText: marks the URLs and path tokens in the element's text nodes as anchors and path links, INSIDE the code element it is handed (url-links.ts linkifyUrls and path-links.ts linkifyPathTokens split text nodes and wrap the token); the code element is inside the code root this builder returns, so every seat it makes is inside that root and none lands as a child of the body (written alike in the numbered and the plain branch, each read)" },
  { in: "mdBlock", to: "linkifyFileText", arg: "box", decl: "const box = el(\"div\", \"fileview-md\")", is: "the same helper over the markdown root (a URL document, or a caller with no location): its seats are inside the root this builder returns, none beside it" },
  { in: "mdBlock", to: "linkMarkdownAnchors", arg: "box", decl: "const box = el(\"div\", \"fileview-md\")", is: "file-view-links.ts linkMarkdownAnchors: walks every `a` inside the markdown root and writes its attributes (class, title, data-path, data-line, data-frag, target, rel; href removed off a path link and a dead link); it dresses the anchor it finds and makes no element, so it seats nothing anywhere" },
  { in: "rewriteFigureSrcs", to: "figureRefs", arg: "root", decl: "a parameter of rewriteFigureSrcs", is: "figure-gate.ts figureRefs: querySelectorAll over the media elements under the root and a read of each fetching attribute (FETCH_ATTRS); returns the references; seats nothing" },
  { in: "resolveFigureRefs", to: "figureRefs", arg: "root", decl: "a parameter of resolveFigureRefs", is: "the same read over a URL document's root; seats nothing" },
  { in: "failedSource", to: "pictureDest", arg: "img", decl: "a parameter of failedSource", times: 2, is: "file-comments.ts pictureDest: reads the picture's data-fv-src, else its src, and returns the string; seats nothing (called in two branches of the label's source read, each read)" },
  // an argument the census cannot name by shape, handed to a callee this file does not declare, whose TYPE the compiler reads as
  // able to hold a node (the round-8 fixes, the round-7 review's tests-2 and regression-1, 2026-09-21: the shape rule passed
  // what it could not name, and the merge deleted the entry that read the sanitized body handed to gateRemoteFigures rather
  // than repointing it, so two live hand-offs were read on no axis). Each is marked `unnamed`, the mark the census holds to
  // the road that refuses it (the shape rule names none of these), and each is read in the callee's own module for what it
  // does with what it is handed. The two `times` entries here are the same argument handed to the same callee by two calls
  // that differ after the argument (the second argument), not byte-identical calls; the P7 case says so.
  { in: "mdBlock", to: "gateRemoteFigures", arg: "clean", decl: "const clean = sanitizeMd(dirty, mintHeadingIds)", times: 2, unnamed: true, is: "figure-gate.ts gateRemoteFigures: wraps each media root inside the sanitized body (`clean`, the sanitizer's own document's body, HTMLElement by md-sanitize.ts's signature) whose sources name a host outside the allowed set in a placeholder span (gate: the figure's fetch attributes moved onto data-fv-gated-* names, the wrapper put where the figure stood, inside the body), and installs once a settings listener that re-judges the document's placeholders; every seat it makes is inside the body, whose child nodes the markdown root then adopts (box.replaceChildren, the seat listed in SEATS_READ_BY_HAND); called in the URL kind's branch with the document's own host and in the file kind's, each read. The entry the round-7 merge deleted (its `box` repointed to `clean`), restored" },
  { in: "mdBlock", to: "addCopyBtn", arg: "host", decl: "const host = pre && pre.tagName === \"PRE\" ? pre : null", times: 2, unnamed: true, is: "code-block.ts addCopyBtn: appends a Copy button INTO the pre it is handed, a fence inside the sanitized body (`host` is the code element's parent when that parent is a pre, else null and the call is skipped), so the one seat it makes is inside the fence; called in the math-source branch and after the highlight, each read (the refuters' conditional, which no shape rule names)" },
  { in: "mdBlock", to: "wrapCodeLines", arg: "codeEl", decl: "const codeEl = node as HTMLElement", unnamed: true, is: "code-block.ts wrapCodeLines: rewrites the code element's innerHTML into one span per line and sets a style property on it; every seat is inside the code element it is handed, a fence inside the sanitized body (the refuters' cast of an untyped callback parameter)" },
  { in: "mdBlock", to: "linkHref", arg: "link", decl: "const link = node as HTMLElement | SVGElement", unnamed: true, is: "md-links.ts linkHref: reads the element's href, else its xlink:href, and returns the string; seats nothing (the URL kind's link pass; the local was `a` and is `link` since the round-8 fixes, so the census's shadow rule admits one entry per name in mdBlock)" },
  { in: "mdBlock", to: "linkHref", arg: "anchor", decl: "const anchor = node as HTMLElement | SVGElement", unnamed: true, is: "the same read in the new-tab stamping pass over every link element; seats nothing (the local was `a` and is `anchor` since the round-8 fixes, for the same reason)" },
  { in: "underEye", to: "getComputedStyle", arg: "h", decl: "a parameter of the callback handed to heads.forEach", unnamed: true, is: "the browser's getComputedStyle over a heading element, read for its scroll margin; a read of the element, no seat" },
  { in: "revealRemembered", to: "revealFragmentTarget", arg: "e", decl: "const e of renderedBlockElements(md, shownText, b)", unnamed: true, is: "md-sanitize.ts revealFragmentTarget: walks the element's ancestors, removes hidden=until-found and opens a closed details; attribute writes on elements already in the tree, no element made, no seat" },
  { in: "scrollToSourceOffset", to: "revealFragmentTarget", arg: "target", decl: "let target", holds: "renderedBlockElements(md, src, k)[0]", unnamed: true, is: "the same helper over the offset's block element (`target`, a let the two search loops assign the same expression, and nothing else writes: `holds` pins it); attribute writes on the tree, no seat" },
  { in: "scrollToFragment", to: "fragmentTarget", arg: "box.querySelector(\".fileview-md\") || box", unnamed: true, is: "file-view-links.ts fragmentTarget: userContentTarget and a querySelector by id over the root it is handed (the markdown root, else the card); returns the element found, seats nothing (the refuters' bare `||`, which no shape rule names)" },
  { in: "scrollToFragment", to: "revealFragmentTarget", arg: "target", decl: "const target = fragmentTarget(box.querySelector(\".fileview-md\") || box, frag)", unnamed: true, is: "the same reveal over the fragment's target; attribute writes on the tree, no seat" },
  { in: "sectionHidden", to: "fragmentTarget", arg: "root", decl: "const root = box.querySelector(\".fileview-md\") || box", unnamed: true, is: "the same lookup over the markdown root, else the card; returns, seats nothing" },
  { in: "openFileView", to: "gateOf", arg: "t", decl: "const t = ev.target as Element | null", unnamed: true, is: "figure-gate.ts gateOf: the click target's closest placeholder when it is inside the body it is handed beside, else null; a read, no seat (the SVG source toggle's callback parameter was `t` and is `txt` since the round-8 fixes, so this name is declared once in openFileView and the shadow rule admits the entry)" },
  { in: "openFileView", to: "panelMark", arg: "t", decl: "const t = ev.target as Element | null", unnamed: true, is: "file-comments.ts panelMark: walks the target's ancestors against the panel's mark set and answers whether the click was on the panel's own mark; a read, no seat" },
  { in: "gateKeys", to: "gateOf", arg: "ev.target", unnamed: true, is: "gateOf over a keydown's target (EventTarget | null to the compiler), the same read as the click's; no seat" },
  { in: "loadGate", to: "loadGatedHost", arg: "document", decl: "a global", unnamed: true, is: "figure-gate.ts loadGatedHost: adds the host to the page's loaded set and re-judges every placeholder of the document it is handed (regateFigures), putting each restored figure's media element back where its placeholder stands, inside the markdown root; no seat beside the body's roots" },
  // String() over a value the compiler cannot type (a caught error is unknown or any; the host's message fields are any): the
  // language's conversion to a string, which reads and seats nothing; each listed because the compiler cannot vouch for the value
  { in: "fellMessage", to: "String", arg: "err", decl: "a parameter of fellMessage", unnamed: true, is: "a render failure's value (unknown) made a string for the failure line's text; String reads and seats nothing" },
  { in: "undoneLanded", to: "String", arg: "(r as { id?: unknown }).id", unnamed: true, is: "an undo record's id made a string for a Set of ids; no seat" },
  { in: "showPdfPages", to: "String", arg: "err && (err as Error).message || err", unnamed: true, is: "the pages attempt's caught error made a string for the fallback's message; no seat" },
  { in: "enterEdit", to: "String", arg: "err && (err as Error).message || err", unnamed: true, is: "the editor chunk's caught error made a string for the failure text; no seat" },
  { in: "doSave", to: "String", arg: "e && e.error || \"the save failed\"", unnamed: true, is: "a save reply's error text made a string (`{}` to the compiler, the type a caught value narrows to here); no seat" },
  { in: "doSave", to: "String", arg: "e.code", unnamed: true, is: "the save reply's code made a string; no seat" },
  { in: "fetchFile", to: "String", arg: "err && err.message || err", unnamed: true, is: "the fetch's caught error made a string for the failure pane's text; no seat" },
  { in: "openUrlView", to: "String", arg: "err && (err as Error).message || err", unnamed: true, is: "the URL viewer's caught error made a string for its failure text; no seat" },
  { in: "initFileView", to: "String", arg: "m.url || \"\"", unnamed: true, is: "the kernel's fileGitLink reply's url field (any: the listener's message record) made a string and handed to the GitHub link's apply (its URL write is listed in URL_WRITES_READ_BY_HAND); no seat" },
  { in: "initFileView", to: "String", arg: "m.reason || \"\"", unnamed: true, is: "the same reply's reason field made a string; no seat" },
  { in: "initFileView", to: "String", arg: "m.mtimeNs || \"\"", unnamed: true, is: "the fileSaved reply's mtime field made a string for the save hooks; no seat" },
  { in: "initFileView", to: "String", arg: "m.error || \"the save failed\"", unnamed: true, is: "the fileSaveFailed reply's error field made a string for the failure text; no seat" },
  { in: "initFileView", to: "String", arg: "m.text || \"the session's host is not answering \u2014 the save was not sent\"", unnamed: true, is: "a federation warn's text field made a string for the failure text (the source spells a dash character in the fallback; the entry spells it as an escape); no seat" },
];
/** A URL written from a value that is not a literal in file-view.ts (an assignment to a member flagged `url` in
 *  NON_SEATING_WRITES or to a member of `location`; a setAttribute or setAttributeNS under a name that is neither `aria-*`
 *  nor `data-*` nor listed in NON_URL_ATTRS, spelled `el.setAttribute("href")` or `el.setAttribute(ref.attr)`; a method
 *  of `location`; `window.open`), READ BY HAND and listed by its site: the nearest named function (`in`), the target as
 *  spelled (`on`), the value as spelled (`value`), a bare name's declaration (`decl`) and how many writes spelled alike the
 *  function has (`times`, one otherwise), with the hand read's claim (`is`), which answers three questions for the round-6
 *  review's lens on URL writes: whether the value can carry a REMOTE URL (an object URL or a same-origin route is a
 *  different answer from a value that can name another host), whether that road reaches the NETWORK and when (at the
 *  write, at an insertion, at the person's click) and what GATES it, and how each was established (the declaration, the
 *  callers, the code read). Never a javascript: URL: a javascript: literal is refused whatever the table says, and a
 *  javascript: value at run time is what the gate named here excludes. */
type UrlWriteRead = { in: string; on: string; value: string; is: string; decl?: string; holds?: string; times?: number };
const URL_WRITES_READ_BY_HAND: UrlWriteRead[] = [
  { in: "apply", on: "a.href", value: "url", decl: "a parameter of apply", is: "the GitHub link's URL, the kernel's answer to the viewer's fileGitLink ask (initFileView's message handler calls h.apply(String(m.url || \"\"), String(m.reason || \"\")), the one caller; read by the parameter's declaration and that call): it CAN carry a remote URL, the repository host the kernel derives from the file's git remote. The network is reached by no fetch at the write; the anchor navigates only on the person's click, in a new tab (target _blank, rel noopener). The gate is the kernel's answer, built server-side from the repository's remote and never from page input, plus the click" },
  { in: "editorChunk", on: "sc.src", value: "self.replace(/\\/(render|feed|files)\\.js/, \"/editor-chunk.js\")", is: "the editor chunk's URL, the page's own bundle URL with the file name swapped: `self` is the src of the page's script tag whose URL matches the bundle names (Array.from(document.querySelectorAll(\"script[src]\")) mapped to src, the first matching /\\/(render|feed|files)\\.js/; read by the declaration two lines above). It carries the ORIGIN THAT SERVED THE PAGE'S BUNDLE and no other host: the value is derived from that tag, not from the file or the person. The network IS reached, a script fetch at document.head.appendChild(sc); the gate is the bundle tag the kernel's page (or the VS Code webview) wrote, the same origin the running code came from" },
  { in: "pdfChunkLoad", on: "sc.src", value: "self.replace(/\\/(render|feed|files)\\.js/, \"/pdf-chunk.js\")", is: "the PDF chunk's URL, derived exactly as the editor chunk's from the page's own bundle tag (the same querySelectorAll over script[src] filtered to the bundle names, read by the declaration above it): the bundle's origin and no other host. The network IS reached, a script fetch at document.head.appendChild(sc), after the engine check; the gate is the bundle tag the page was served with" },
  { in: "aimFrame", on: "(frame as HTMLIFrameElement).src", value: "objUrl + \"#page=\" + pdfPage", is: "an object URL with a page fragment: `objUrl` is the open's object URL (let objUrl: string | null = null, written at one site from URL.createObjectURL(t) over the fetched bytes and read null-checked here; every write read by grep of `objUrl =`), so the value is a blob: URL of the page's own origin plus `#page=N` with N a number. No network: a blob URL resolves in the browser to bytes already fetched; the frame navigates its PDF viewer to the fragment. The gate is URL.createObjectURL, which mints only blob: URLs" },
  { in: "linkOut", on: "a.href", value: "href", decl: "a parameter of openUrlView", is: "the URL viewer's own document URL, openUrlView's parameter (never written inside it): the chat's anchor delegate opens this viewer only for a same-origin markdown URL (render.ts routes into openUrlView under isMarkdownUrl(href, location.origin)), and the probe seams hand it a same-origin test URL, so at this head the value names the page's origin; the comment above the site says so too. It COULD carry a remote URL if a caller passed one, so the road is read: the network is reached on the person's click alone, a navigation in a new tab (target _blank, rel noopener, dataset.newTab so the delegate lets the tab open); the gate is the caller's isMarkdownUrl test against the page's origin, plus the click" },
  { in: "startDownload", on: "a.href", value: "url", decl: "a parameter of startDownload", is: "the kernel's download route: every caller hands `dlUrl`, fileUrl(path, sid) + \"&download=1\" (three call sites, read by grep of startDownload(), each with dlUrl), a same-origin path the kernel answers with Content-Disposition: attachment. The network IS reached at the press, since the code clicks the anchor itself (a.click()), a same-origin cookie-authed request the browser's downloader owns; the gate is fileUrl, which builds the route from the file's path against the page's origin, never from page input" },
  { in: "imgBlock", on: "img.src", value: "objUrl", decl: "a parameter of imgBlock", is: "an object URL over the fetched bytes: the one caller hands the open's objUrl (imgBlock(objUrl, path, imgFailed) in renderBody, with objUrl minted by URL.createObjectURL(t); read by the parameter's declaration and grep of imgBlock(). No network: a blob: URL resolves in the browser to bytes already fetched. The gate is URL.createObjectURL" },
  // the style road (the round-8 fixes, the round-7 review's correctness-2, 2026-09-21): a CSS property written through `style`
  // from a non-literal under a name NON_URL_STYLE_PROPS does not list, each read for what the value can be
  { in: "stamp", on: "(n as HTMLElement).style.setProperty(\"--fv-body-w\")", value: "width + \"px\"", is: "the body's measured width as a CSS custom property on each top-level table (watchBodyWidth's stamp: `width` is the ResizeObserver entry's contentRect width, a number the browser measured, plus the unit), consumed by the stylesheet's `var(--fv-body-w)` in a width rule alone (styles.css); a number with a unit names no resource and the property that reads it takes no url(). No network: nothing fetches a length. The gate is the type: a measured number, never a string from the document or the person" },
  { in: "openOutline", on: "r.style.setProperty(\"--fv-ol-depth\")", value: "String(Number(h.tagName[1]) - shallowest)", is: "a heading's depth as a CSS custom property on its outline row (the heading's tag digit, h1 to h6, less the shallowest depth in the outline, a small integer made a string), consumed by the stylesheet's `var(--fv-ol-depth)` in an indent rule alone; an integer names no resource. No network. The gate is the derivation: Number() of a tag name's digit, never document text" },
  { in: "openFileView", on: "sess.style.background", value: "owner.color.bg", is: "the session tag's background colour, the owning session's colour record (FileViewIdentity's `color`, resolved from the sid through identityOf, which files.ts and feed.ts register from the kernel's session list; hostStub gives none), a colour string the kernel mints from its palette, never the document's or the person's. `background` is the shorthand and ACCEPTS a url() image, so this write is read here by hand and the property is kept OUT of NON_URL_STYLE_PROPS: a reader must not tidy it onto that list. No network at this head: the value is a colour. The gate is the record's source, the kernel's palette" },
  { in: "pdfBlock", on: "frame.src", value: "objUrl", decl: "a parameter of pdfBlock", is: "an object URL over the fetched bytes: the callers hand the open's objUrl (pdfBlock(objUrl, path) in renderBody; pdfBlock(url, path) in showPdfPages's fallback with `const url = objUrl` read null-checked above it), objUrl minted by URL.createObjectURL(t); read by the parameter's declaration and grep of pdfBlock(). No network: the frame's PDF viewer reads the blob the browser holds. The gate is URL.createObjectURL" },
  // the setAttribute spelling and window.open (the verifiers' census-1 and census-4 of the round-7 build, 2026-09-20: the URL
  // axis read the assignment spelling alone, so eight setAttribute writes from author-controlled values and the tab opener stood
  // outside the network lens). The value of each is the DOCUMENT's (a link or a figure source the author wrote), so each can
  // carry a remote host; what gates the road is the sanitizer's URI rule before the write, the figure gate after it, and the
  // person's click
  { in: "openUrlTab", on: "window.open", value: "href", decl: "a parameter of openUrlTab", is: "the href of a URL anchor inside the body (openLink, the one caller: openUrlTab(x.getAttribute(\"href\") || \"\") for an anchor wearing URL_LINK_CLASS, the document's own web links as file-view-links.ts stamped them): it CAN carry a remote host, the author's. The network is reached by a navigation in a NEW TAB on the person's MODIFIED click alone (own = wantsOwnTab: Ctrl, Cmd or the middle button; a plain click is the browser's own open of the anchor, target _blank and rel noopener stamped on it), and only where canPreview() (the web dashboard; the VS Code webview posts openLink to the host instead). The gate is the sanitizer's URI rule on the href before the stamp (DOMPurify's allowed-URI test over every href, so a javascript: value never reaches the anchor), the modified click and canPreview; established by reading openLink and the two stamps" },
  { in: "mdBlock", on: "a.setAttribute(\"href\")", value: "xl", decl: "const xl = a.getAttributeNS(XLINK_NS, \"href\")", is: "an SVG anchor's xlink:href moved to a plain href, after the sanitize and the adoption (box.replaceChildren(...Array.from(clean.childNodes)) above this loop): the author's value, so it CAN carry a remote host. The network is reached on a click alone (an anchor navigates when clicked; for a file document linkMarkdownAnchors then stamps a web link target _blank and takes the href off a path link, and a URL document's links are stamped _blank below), never at the write. The gate is DOMPurify's allowed-URI test over xlink:href (dompurify's _isValidAttribute reads every attribute's value against IS_ALLOWED_URI, so a javascript: value is gone before this loop) plus the click; established by the sanitize call above and the sanitizer's source" },
  { in: "mdBlock", on: "link.setAttribute(\"href\")", value: "resolveDocRelative(href, doc.href)", is: "a URL document's relative link made absolute against the document's own URL (doc.href, the page's origin by the caller's isMarkdownUrl test, render.ts): a relative reference resolves to the document's host; a protocol-relative `//host/path` takes the document's scheme with the AUTHOR's host, so the value CAN name another host; an absolute reference, a `#fragment` and an empty value return early above (the scheme test) and are not written here. The network is reached on a click alone: the chat page's anchor delegate opens a same-origin .md in this viewer and every other link in a new tab (target _blank, rel noopener stamped on every link element below). The gate is the sanitizer's URI rule before the loop (a javascript: scheme never reaches this branch, and DOMPurify dropped it anyway), the click and the delegate; established by reading the loop's early return, md-links.ts resolveDocRelative and render.ts's delegate" },
  { in: "rewriteFigureSrcs", on: "el.setAttribute(\"srcset\")", value: "serializeSrcset(cands)", is: "a file document's figure srcset with each relative candidate re-pointed at the kernel's /file route (fileUrl over the file's directory, the page's origin) and every absolute, protocol-relative, data: or empty candidate left AS WRITTEN (path() returns null for those): the serialized value CAN carry a remote host, the author's. The network is reached when the picture lays out, for the page's origin at once; for a host outside the gear's list the figure gate runs after this rewrite (mdBlock: rewriteFigureSrcs, then gateRemoteFigures) and moves the attribute into the placeholder, so the fetch waits for the person's click on the placeholder or Print with them. The gate is fileUrl for the relative candidates and figure-gate's allowed-host list plus the click or the print for the rest; established by reading path(), mdBlock's order and gateRemoteFigures" },
  { in: "rewriteFigureSrcs", on: "el.setAttribute(\"href\")", value: "p === null ? ref.value : p", is: "an svg image's xlink:href folded into href in a file document: the /file route when the value was relative (p), else the value as written (an absolute, protocol-relative, data: or empty href), so it CAN carry a remote host. The network is reached when the image renders, for the page's origin at once; a host outside the list is gated by gateRemoteFigures after this rewrite (figureRefs reads href on an svg image) until the click or the print. The gate is fileUrl, DOMPurify's URI rule before the rewrite (a javascript: value is gone), and the figure gate plus the click or the print; established by reading path(), mdBlock's order and figure-gate's FETCH_ATTRS" },
  { in: "rewriteFigureSrcs", on: "el.setAttribute(ref.attr)", value: "p", decl: "const p = path(ref.value)", is: "the figure reference's attribute (src or poster here: srcset, xlink:href and a null p returned above) written from the /file route path() built with fileUrl over the file's directory and the session: the page's origin and no other host (a value with a scheme, a `//` or nothing returns null and never reaches this line). The network is reached when the element lays out, a same-origin request the kernel answers from the session's disk, never gated since the page's own origin is never a gated host. The gate is fileUrl; established by reading path() and the continue above" },
  { in: "resolveFigureRefs", on: "el.setAttribute(\"srcset\")", value: "serializeSrcset(cands)", is: "a URL document's figure srcset with each candidate resolved against the document's URL (resolveDocRelative over base = doc.href): a relative candidate resolves to the document's host (the page's origin by the caller's isMarkdownUrl test), an absolute one stays as written and a protocol-relative one takes the document's scheme with the author's host, so the value CAN carry a remote host. The network is reached at layout; gateRemoteFigures(box, document.baseURI, [own]) runs after this resolve (mdBlock) and gates every host but the document's own and the gear's list behind the click or Print with them. The gate is the figure gate plus the click or the print; established by reading resolveDocRelative and mdBlock's order" },
  { in: "resolveFigureRefs", on: "el.setAttribute(\"href\")", value: "abs", decl: "const abs = resolveDocRelative(ref.value, base)", is: "an svg image's xlink:href folded into href in a URL document, resolved against the document's URL: the document's host for a relative value, the author's host for an absolute or protocol-relative one, so it CAN carry a remote host. The network is reached when the image renders, gated by gateRemoteFigures after this resolve for every host but the document's own and the gear's list. The gate is DOMPurify's URI rule before (a javascript: value is gone), the figure gate and the click or the print; established as the srcset entry above" },
  { in: "resolveFigureRefs", on: "el.setAttribute(ref.attr)", value: "abs", decl: "const abs = resolveDocRelative(ref.value, base)", is: "the figure reference's attribute (src or poster here: srcset and xlink:href are handled above) resolved against the document's URL and written back under its own name when it changed: the document's host for a relative value, the author's host for an absolute or protocol-relative one, so it CAN carry a remote host. The network is reached at layout, gated by gateRemoteFigures after this resolve for every host but the document's own and the gear's list. The gate is the figure gate plus the click or the print; established as the srcset entry above" },
];
/** An attribute set under a name the census cannot read as a string literal (or one naming an on<event> handler) in
 *  file-view.ts, READ BY HAND and listed by its site: the nearest named function (`in`), the receiver as spelled (`on`) and
 *  the name's spelling (`name`), with what the name can be (`is`), the hand read's claim: never a handler attribute (a
 *  string that runs as code). A literal name, or a constant resolved through its declaration to one, not starting with
 *  `on` passes without an entry; a site the table does not list fails with its line; a stale entry fails. */
type AttrNameRead = { in: string; on: string; name: string; is: string };
const ATTR_NAMES_READ_BY_HAND: AttrNameRead[] = [
  { in: "rewriteFigureSrcs", on: "el", name: "ref.attr", is: "the figure reference's attribute name, one of the names figure-gate.ts's figureRefs enumerates from its closed FETCH_ATTRS table over the media elements it walks (src, srcset, poster, href and xlink:href; the srcset and xlink:href branches are handled above this line), never an on* name: the set is the gate's own, not the document's" },
  { in: "resolveFigureRefs", on: "el", name: "ref.attr", is: "the same figure reference's attribute name from figureRefs, the URL document's resolver writing the resolved URL back under the name it was read from" },
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
  if (refused.length) t.diagnostic("census refused " + refused.length + ":\n" + refused.join("\n"));
  assert.deepEqual(refused, [], "every use of the body is one the census knows how to read: a use it does not is read by hand and the census taught it, never skipped");
  const roots = [...seated.keys()].sort();
  t.diagnostic("census: " + roots.map((r) => r + " (line " + seated.get(r)!.join(", ") + ")").join("; "));
  const second = seatSites(VIEWER_SRC);
  t.diagnostic("second read: " + second.sites.length + " seats and site-read calls (" + second.sites.filter((s) => s.body).length + " on the body token, " + second.sites.filter((s) => !s.body).length + " on other receivers, " + SEATS_READ_BY_HAND.length + " entries listed over " + SEATS_READ_BY_HAND.reduce((n, e) => n + (e.times ?? 1), 0) + " seats, one entry per seat spelling, `times` for a repeat), " + second.indexReads.length + " stored index reads (" + INDEX_READS_BY_HAND.length + " distinct sites listed), " + NON_SEATING_METHODS.length + " method names listed as seating nothing; member writes on receivers other than the body token: " + (second.writes.length + second.sites.filter((s) => !s.body && s.assign).length) + " over " + new Set([...second.writes.map((w) => w.name), ...second.sites.filter((s) => !s.body && s.assign).map((s) => s.via.split(" ")[0])]).size + " distinct names (" + second.sites.filter((s) => !s.body && s.assign).length + " seats, " + second.writes.filter((w) => w.through === undefined).length + " by " + NON_SEATING_WRITES.length + " names listed as seating nothing, " + second.writes.filter((w) => w.through !== undefined).length + " through style or dataset by the rule), the body token's " + second.bodyWrites + "; " + second.handedNodes.length + " nodes handed to callees and " + second.elementsHanded.length + " elements handed to callees the file does not declare, " + second.elementsHanded.filter((h) => h.unnamed).length + " of them named by the compiler's type alone (" + ARGS_READ_BY_HAND.length + " entries listed over " + ARGS_READ_BY_HAND.reduce((n, e) => n + (e.times ?? 1), 0) + " hand-offs, " + ARGS_READ_BY_HAND.filter((e) => e.unnamed).length + " of the entries marked `unnamed`), " + second.urlWrites.length + " URL writes (" + URL_WRITES_READ_BY_HAND.length + " entries listed over " + URL_WRITES_READ_BY_HAND.reduce((n, e) => n + (e.times ?? 1), 0) + " writes), " + second.styleWrites.length + " CSS properties written through style from a non-literal under a name listed as taking no url() (" + NON_URL_STYLE_PROPS.length + " names listed), " + second.attrNames.length + " attribute names read by hand (" + ATTR_NAMES_READ_BY_HAND.length + " listed), " + second.attrWrites.length + " attributes set from a non-literal under an aria-* or data-* name (" + NON_URL_ATTRS.length + " names listed as carrying no URL)");
  t.diagnostic("live seats on receivers other than the body token: " + JSON.stringify(second.sites.filter((s) => !s.body).map((s) => ({ in: s.fn, on: s.on, via: s.via, seats: s.seats, decl: s.decl, kind: s.kind, writes: s.writes, line: s.line }))));
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
  assert.equal(bodyReady(bodyOf("div.fileview-unlisted")), false, "FAILS BEFORE: a child none of the lists names is not in; this census is what turns a new root into a red test rather than a dead button, on the call, assignment, receiver, argument and URL axes since the round-7 fixes (a method call's name; a member assignment's name; a seat's receiver and each seated name by their bindings; a node of the tree handed to any callee, and an element the census can see by shape handed to a callee the file does not declare; a URL written from a non-literal by an assignment, setAttribute, a CSS property through style or style.setProperty, a method of location or window.open, or an attribute set under a non-literal name)");
  for (const c of READY_ROOTS) assert.equal(bodyReady(bodyOf(c, "div.fileview-unlisted")), false, "an unlisted child beside " + c + ": not in");
  for (const r of NOT_READY_ROOTS) assert.equal(bodyReady(bodyOf(r), "pdf"), r === PDF_LOADER_ROOT, r + " alone under the PDF kind: " + (r === PDF_LOADER_ROOT ? "in (the pages attempt's loader; the PDF road reads nothing from the body)" : "not in"));
  assert.ok(NOT_READY_ROOTS.includes(PDF_LOADER_ROOT), "the PDF kind's exception is one of the wait roots");
  for (const r of LINE_ROOTS) assert.equal(bodyReady(bodyOf(r), "pdf"), false, r + " alone under the PDF kind: not in");
});

test("the census refuses its unknown and derives its population, executed over mutants of file-view.ts's source: a root seated by body.append or body.insertBefore is resolved and fails the lists (FAILS BEFORE: the three-name list never saw either, so the census passed over both), a seat through an innerHTML assignment, a call the census does not know, a further access on a child node and a child-level replaceWith each fail with their line, and a read or a scroll assignment passes; the round-4 review's forms each red with the planted line (FAILS BEFORE: body?.append(x) and body[\"append\"](x) were outside the collect pattern, body.append?.(x) was a further access refused for node members alone, body.append.call(body, x), .bind and .apply and a bare body.append passed); the round-5 fix's forms each red with the planted line (FAILS BEFORE: (body).append(x), (body as HTMLElement).append(x), an alias const b = body, [body].forEach(...), Element.prototype.append.call(body, x) and a helper handed the body passed with no refusal and no root; a seat quoted in a column-0 // comment or after ;// counted as a seat, and a listed root's seat moved into one kept the census green); a seat written across a newline is read, a comment's prose is not, a declaration, a comparison and a listed callee's argument pass, and body.classList.add(...) still passes; the round-5 review's forms each red with the planted line (FAILS BEFORE: the census refused six child-level method names and passed every other seat unread, so a seat through body.querySelector(...)!.parentElement, a stored query result, md.parentElement!.append(x), a parent held in a variable, body.closest(...) and body.getRootNode(), a node read inside a listener's callback or a nested call within a body call's arguments and then seated, and the accessor body: () => body written anywhere but its declared site all passed with no refusal and no root); a seat on a receiver the table does not list, a computed-name call, a live site whose entry is removed, a stale entry and the ctx declaration renamed each red; the branch's verification pass's forms each red with the planted line (FAILS BEFORE: the second read knew a closed list of seating names and passed every other form on a receiver other than the body, so a seating method reached through call, bind or apply on md or md.parentElement, Reflect.apply(md.append, ...), a bound seat, a Range's insertNode, setHTMLUnsafe, moveBefore, a method by a name the census does not list, a bare read of md.append or md[\"append\"], a member read by a computed name and stored, a parenthesised callee, Object.assign(md, { innerHTML }) and Reflect.set(md, \"innerHTML\", ...) all passed with no refusal and no root; a block's const main = md.parentElement! and a callback's parameter named main seated under the entry for openFileView's main; a spread into body.append threw with no line), and a receiver with a cast inside is spelled with its spaces; the round-6 review's forms (2026-09-20) each red with the planted line: cluster A (FAILS BEFORE: a second seat on the listed binding of main seating an unlisted root, a second ed.mount into another host and a second URL write at a listed target passed under the entry hand-read at another seat, and the viewer's `let sess = null` passed under an entry pinning that declaration; a let is refused unless `holds` names what every write assigns, a parameter written to is refused, and an entry two seats match is refused unless it says `times`), cluster B (FAILS BEFORE: a computed-name write `md[k] = html` plain and compound, `md[\"inner\" + \"HTML\"]`, a template-literal index, innerText and outerText on md, on a child and in a callback, `document.body = md`, a destructuring or for-of head with innerHTML as a target, a parenthesised target, a destructured append, a handler member or attribute holding a string were neither a seat nor a refusal; textContent passes as a listed write), cluster C (FAILS BEFORE: `const R = Reflect; R.set(...)`, `window.Reflect.set(...)`, `globalThis.Object.assign(...)`, a stored `Reflect.set` and Reflect as an array element passed with no site and no refusal), item 7's string roads, the argument axis and URL writes, and extra6-4's select.add", () => {
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
  assert.equal(chained.refused.length, 2, "a further access on a child node is refused, and so is the replaceWith it reaches, a seat on a receiver the table does not list"); assert.match(chained.refused[0], /^line \d+: body\.firstElementChild hands out a node/); assert.match(chained.refused[1], /^line \d+: body\.firstElementChild!\.replaceWith\(el\("div", "fileview-mutant"\)\) seats `el\("div", "fileview-mutant"\)` on `body\.firstElementChild` by replaceWith in openFileView, a seat the census has not read by hand/);
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
  const refusedMutant = (src: string, form: string, want: RegExp, count = 1): string[] => {   // count: a form that hands the body to its own seating method (`body.append.call(body, x)`) is refused twice, once per token, each with the line
    const r = census(src);
    assert.equal(r.refused.length, count, form + ": " + count + " refusal(s): " + JSON.stringify(r.refused));
    for (const one of r.refused) assert.ok(one.startsWith("line " + plantedLine + ": "), form + ": with the planted line: " + one);
    assert.match(r.refused[0], want, form);
    assert.deepEqual([...r.seated.keys()].sort(), [...before.seated.keys()].sort(), form + ": and no root seated");
    return r.refused;
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
  refusedMutant(seat('[body].forEach((bx) => bx.prepend(el("div", "fileview-mutant")));'), "[body].forEach(bx => bx.prepend(x))", /body is written bare where the census cannot class it \(an array element\)/, 2);   // and bx.prepend, a seat on a receiver the table does not list (not `b`: a second declaration of that listed name in openFileView is its own refusal, below)
  refusedMutant(seat('Element.prototype.append.call(body, el("div", "fileview-mutant"));'), "Element.prototype.append.call(body, x)", /body is handed to Element\.prototype\.append\.call\(\.\.\.\), a callee the census does not list/, 3);   // the token, and the second read's two: a call read by its site and not listed, and append read without being called (round 6)
  refusedMutant(seat('seatInto(body, el("div", "fileview-mutant"));'), "a helper handed the body", /body is handed to seatInto\(\.\.\.\), a callee the census does not list/, 2);   // and the el() it is handed beside the body, an element handed to a callee the file does not declare (the author's closing pass over the round-7 build)
  refusedMutant(seat('seatInto({ body, root: el("div", "fileview-mutant") });'), "a helper handed the body as a property", /body is handed to seatInto\(\.\.\.\) as a property of its argument, a callee the census does not list/, 2);   // as above, the el() inside the literal
  refusedMutant(seat('const target = wrap ? body : main;'), "a ternary operand", /body is written bare where the census cannot class it \(a ternary operand\)/);
  refusedMutant(seat('const target = held ?? body;'), "a logical operand", /body is written bare where the census cannot class it \(a logical operand\)/);
  refusedMutant(seat('const target = () => body;'), "an arrow's value outside the accessor", /body is written bare where the census cannot class it \(an arrow's value\)/);
  // the round-5 review's six escapes (2026-09-20), each red with the planted line under the inverted default: a seat on any
  // receiver but the sanctioned `body` token is refused unless its site is in the table, whatever produced the receiver
  const SEAT_UNREAD = /seats `[^`]*` on `([^`]+)` by [^,]+ in openFileView, a seat the census has not read by hand/;
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
  // the branch's verification pass finding census-1 (2026-09-20): the CALL axis refuses its unknown too. Before this the second read knew a closed
  // list of seating names and passed every other method call, a seating method read without being called, and a member
  // read by a computed name, so each of these seated with no refusal and no root
  const SITE_UNREAD = /calls (?:call|apply|bind|assign|set|insertNode|add|mount) on `[^`]+` into `[^`]*` in openFileView, a call the census reads by its site/;
  const HANDED_METHOD = /reads the method append without calling it/;
  refusedMutant(seat('Reflect.apply(md.append, md, [el("div", "fileview-mutant")]);'), "Reflect.apply(md.append, md, [x])", SITE_UNREAD, 2);   // the reflection global's call by its site, and append read without being called
  refusedMutant(seat('Reflect.apply(Element.prototype.append, md.parentElement, [el("div", "fileview-mutant")]);'), "Reflect.apply(Element.prototype.append, md.parentElement, [x])", SITE_UNREAD, 3);   // the site, append read without being called, and md.parentElement handed to a callee (the argument axis, round 7)
  refusedMutant(seat('md.append.call(md, el("div", "fileview-mutant"));'), "md.append.call(md, x)", SITE_UNREAD, 2);
  refusedMutant(seat('md.parentElement!.append.call(md.parentElement, el("div", "fileview-mutant"));'), "md.parentElement!.append.call(md.parentElement, x)", SITE_UNREAD, 3);   // the site, append read without being called, and md.parentElement handed to the call (the argument axis, round 7)
  refusedMutant(seat('Element.prototype.append.call(md.parentElement, el("div", "fileview-mutant"));'), "Element.prototype.append.call(md.parentElement, x)", SITE_UNREAD, 3);   // as above
  refusedMutant(seat('const seatMd = md.parentElement!.append.bind(md.parentElement); seatMd(el("div", "fileview-mutant"));'), "a bound seat, const f = md.parentElement!.append.bind(md.parentElement); f(x)", SITE_UNREAD, 3);   // as above
  refusedMutant(seat('const rg = document.createRange(); rg.selectNodeContents(md.parentElement!); rg.insertNode(el("div", "fileview-mutant"));'), "a Range's insertNode over md.parentElement", /rg\.insertNode\(el\("div", "fileview-mutant"\)\) seats `el\("div", "fileview-mutant"\)` on `rg` by insertNode in openFileView, a seat the census has not read by hand/, 3);   // the seat by insertNode on a receiver the table does not list, selectNodeContents, a method it does not list, and md.parentElement handed to it (the argument axis, round 7)
  refusedMutant(seat('(md.parentElement as any).setHTMLUnsafe("<div class=\\"fileview-mutant\\"></div>");'), "(md.parentElement as any).setHTMLUnsafe(...)", /seats `"<div class=\\"fileview-mutant\\"><\/div>"` on `\(md\.parentElement as any\)` by setHTMLUnsafe in openFileView, a seat the census has not read by hand/);
  refusedMutant(seat('(md.parentElement as any).moveBefore(el("div", "fileview-mutant"), null);'), "(md.parentElement as any).moveBefore(x, null)", SEAT_UNREAD);
  refusedMutant(seat('md.parentElement!.seatAnywhere(el("div", "fileview-mutant"));'), "a method the census does not list, by any name", /calls seatAnywhere on `md\.parentElement`, a method the census does not list as seating or as seating nothing: read it by hand and list it/);
  refusedMutant(seat('const seatLater2 = md.append;'), "a bare read of md.append", HANDED_METHOD);
  refusedMutant(seat('const seatLater3 = md["append"];'), 'a bare read of md["append"]', HANDED_METHOD);
  refusedMutant(seat('const seatLater4 = md[m];'), "a member read by a computed name and stored, const f = md[m]", /seatLater4 = md\[m\] reads a member of `md` by a computed name and stores or hands it on, in openFileView: read the site for what md is and list it in INDEX_READS_BY_HAND/);
  refusedMutant(seat('(md.append)(el("div", "fileview-mutant"));'), "(md.append)(x), a parenthesised callee", HANDED_METHOD, 2);   // append read without being called (its call is the parenthesised expression's), and the callee the census cannot read
  refusedMutant(seat('Object.assign(md, { innerHTML: "<div class=\\"fileview-mutant\\"></div>" });'), "Object.assign(md, { innerHTML })", SITE_UNREAD);
  refusedMutant(seat('Reflect.set(md, "innerHTML", "<div class=\\"fileview-mutant\\"></div>");'), 'Reflect.set(md, "innerHTML", ...)', SITE_UNREAD);
  refusedMutant(seat('(md as any).up.append(el("div", "fileview-mutant"));'), "a cast inside the receiver", /seats `el\("div", "fileview-mutant"\)` on `\(md as any\)\.up` by append in openFileView/);   // the branch's verification pass finding census-5: the receiver is spelled with its spaces, so the line can be read
  // the branch's verification pass finding census-2 (2026-09-20): an entry is held to ONE binding, so a second declaration of a listed
  // name inside the entry's function is refused rather than read under the entry's claim (the seat spelled as the entry's,
  // `main.appendChild(body)`, so the binding rule is what reds, not the seat key)
  /** The refusals a second declaration of `main` inside openFileView draws on the LIVE seats and hand-offs of that name (the
   *  author's closing pass over the round-7 build, the verifiers' census-2: a listed name declared twice in the entry's
   *  function is refused at every seat it stands at, whatever the second declaration spells), set apart from the planted
   *  line's own. */
  const MAIN_SHADOW = /^line \d+: .* in openFileView: `main` is declared 2 times in openFileView \(lines \d+, \d+\)/;
  const splitShadows = (refused: string[], form: string): string[] => {
    const shadows = refused.filter((x) => MAIN_SHADOW.test(x));
    assert.deepEqual(shadows.map((x) => / (\S+\(.*?\)|[\w.]+\([^)]*\)) in openFileView:/.exec(x)?.[1] ?? x).sort(), ["box.appendChild(main)", "main.appendChild(body)", "pressHold(main)"], form + ": the live seats and hand-offs of `main` are refused under the second declaration: " + JSON.stringify(shadows));
    return refused.filter((x) => !MAIN_SHADOW.test(x));
  };
  const rebound = (src: string, form: string, decl: RegExp): void => {
    const r = census(src);
    const own = splitShadows(r.refused, form);
    assert.equal(own.length, 2, form + ": the seat's binding and the entry's two seats: " + JSON.stringify(own));
    assert.ok(own[0].startsWith("line " + plantedLine + ": "), form + ": with the planted line: " + own[0]);
    assert.match(own[0], decl, form); assert.match(own[0], /where SEATS_READ_BY_HAND read `const main = el\("div", "fileview-main"\)`: the receiver is not the one read by hand/, form);
    assert.match(own[1], /^SEATS_READ_BY_HAND's entry `main\.appendChild` seating `body` in openFileView matches 2 seats \(lines \d+, \d+\) where it reads 1: one entry is one seat/, form);
    assert.deepEqual([...r.seated.keys()].sort(), [...before.seated.keys()].sort(), form + ": and no root seated");
  };
  rebound(seat('{ const main = md.parentElement!; main.appendChild(body); }'), "a block's const main = md.parentElement!", /seats on `main` in openFileView, bound to `const main = md\.parentElement!`/);
  rebound(seat('[md.parentElement!].forEach((main) => main.appendChild(body));'), "a callback's parameter named main", /seats on `main` in openFileView, bound to `a parameter of the callback handed to \[md\.parentElement!\]\.forEach`/);
  // the round-6 review's cluster A (extra5-1, correctness-1, correctness-5; 2026-09-20): the table is keyed on the SEAT. Before
  // this an entry was (function, receiver, form) and admitted every seat sharing the triple, so a second seat on the listed
  // binding of main, seating an unlisted root in the viewer's own body, passed under the entry hand-read for main.appendChild(body)
  // (this probe asserted that pass); a second mount at a listed mount site seated anywhere; and the entry for the `let` session
  // tag pinned its declaration and nothing about what it held at the seat
  const WEARING = /seats `el\("div", "fileview-mutant"\)` on `main` by appendChild in openFileView, a seat the census has not read by hand \(the table's entry for `main\.appendChild` in openFileView seats `body`, not this: a second seat at a listed site is a second entry, read by hand\)/;
  refusedMutant(seat('main.appendChild(el("div", "fileview-mutant"));'), "FAILS BEFORE: a second seat on the listed binding of main, seating an unlisted root", WEARING);
  { const r = census(seat('{ const main = md.parentElement!; main.appendChild(el("div", "fileview-mutant")); }')); const own = splitShadows(r.refused, "a block's const main seating an unlisted root"); assert.equal(own.length, 1, "a block's const main seating an unlisted root: the seat key reds before the binding rule is reached: " + JSON.stringify(own)); assert.ok(own[0].startsWith("line " + plantedLine + ": ")); assert.match(own[0], WEARING); }
  const plantAfter = (needle: string, code: string): { src: string; line: number } => { const i = at(VIEWER_SRC, needle) + needle.length; return { src: VIEWER_SRC.slice(0, i) + "      " + code + "\n" + VIEWER_SRC.slice(i), line: VIEWER_SRC.slice(0, i).split("\n").length }; };   // a line planted right after a given line of the viewer, where `seat` cannot reach (another function's scope)
  const refusedAt = (planted: { src: string; line: number }, form: string, want: RegExp, count = 1): string[] => {
    const r = census(planted.src);
    assert.equal(r.refused.length, count, form + ": " + count + " refusal(s): " + JSON.stringify(r.refused));
    for (const one of r.refused) assert.ok(one.startsWith("line " + planted.line + ": "), form + ": with the planted line " + planted.line + ": " + one);
    assert.match(r.refused[0], want, form);
    return r.refused;
  };
  const secondMount = plantAfter('\n      const host = el("div", "fileview-cm");\n', "ed.mount(wait, {});");
  refusedAt(secondMount, "FAILS BEFORE: a second ed.mount beside the listed one, into another host", /ed\.mount\(wait, \{\}\) calls mount on `ed` into `wait, \{\}` in enterEdit, a call the census reads by its site \([^)]*\) and has not read by hand \(the table's entry for `ed\.mount` in enterEdit seats `host, \{text, ext, onChange, onSave, /);   // an object literal in a seats key is spelled by its property names (the author's closing pass over the round-7 build, the verifiers' census-3)
  const secondUrl = plantAfter("\n  img.src = objUrl;\n", "img.src = path;");
  refusedAt(secondUrl, "a second URL write at a listed target, from another value", /img\.src = path writes img\.src from `path` in imgBlock, a URL write/);
  // correctness-5: a receiver bound by `let` is reassignable, and its declaration says nothing about what it holds at the seat;
  // the entry for it is refused unless it pins what every write assigns (`holds`), and the viewer's session tag moved onto a const
  const LET_SEAT = { in: "openFileView", on: "sess2", via: "replaceChildren", seats: 'el("span", "fileview-mutant")', is: "a probe's entry for a let-bound receiver", decl: 'let sess2 = el("div", "fileview-mutant")' };
  const reassigned = seat('let sess2: HTMLElement | null = el("div", "fileview-mutant"); sess2 = md.parentElement!; sess2.replaceChildren(el("span", "fileview-mutant"));');
  const letNoHolds = census(reassigned, [...SEATS_READ_BY_HAND, LET_SEAT]);
  assert.equal(letNoHolds.refused.length, 1, "a let receiver with an entry pinning its declaration: " + JSON.stringify(letNoHolds.refused));
  assert.match(letNoHolds.refused[0], new RegExp("^line " + plantedLine + ": sess2\\.replaceChildren\\(el\\(\"span\", \"fileview-mutant\"\\)\\) seats on `sess2` is bound by `let sess2 = el\\(\"div\", \"fileview-mutant\"\\)`, a reassignable binding \\(let; the writes: `el\\(\"div\", \"fileview-mutant\"\\)` at line " + plantedLine + ", `md\\.parentElement!` at line " + plantedLine + "\\) whose declaration says nothing about what it holds at the site: list `holds`"), "FAILS BEFORE: the entry pinned `let sess = null` and the seat passed whatever sess held");
  const letWrongHolds = census(reassigned, [...SEATS_READ_BY_HAND, { ...LET_SEAT, holds: 'el("div", "fileview-mutant")' }]);
  assert.equal(letWrongHolds.refused.length, 1); assert.match(letWrongHolds.refused[0], /and the entry's `holds` \(`el\("div", "fileview-mutant"\)`\) is not what every write to it assigns \(`el\("div", "fileview-mutant"\)` at line \d+, `md\.parentElement!` at line \d+\)/, "a `holds` one write disagrees with is refused: the reassignment between the declaration and the seat is what it names");
  const letHeld = census(seat('let sess2: HTMLElement | null = el("div", "fileview-mutant"); sess2.replaceChildren(el("span", "fileview-mutant"));'), [...SEATS_READ_BY_HAND, { ...LET_SEAT, holds: 'el("div", "fileview-mutant")' }]);
  assert.deepEqual(letHeld.refused, [], "a let every write to which assigns what `holds` names passes: the entry pins what the binding holds, not its declaration alone");
  const paramWritten = census(seat('[md].forEach((par) => { par = md.parentElement!; par.append(el("div", "fileview-mutant")); });'), [...SEATS_READ_BY_HAND, { in: "openFileView", on: "par", via: "append", seats: 'el("div", "fileview-mutant")', is: "a probe's entry for a parameter written to", decl: "a parameter of the callback handed to [md].forEach" }]);
  assert.equal(paramWritten.refused.length, 1); assert.match(paramWritten.refused[0], new RegExp("^line " + plantedLine + ": par\\.append\\(el\\(\"div\", \"fileview-mutant\"\\)\\) seats on `par` is bound by `a parameter of the callback handed to \\[md\\]\\.forEach`, a parameter written to \\(`md\\.parentElement!` at line " + plantedLine + "\\), a reassignable binding"), "a parameter written to before its seat is refused under an entry pinning the parameter");
  const SESS_CONST = '\n  const sess: HTMLElement | null = owner ? el("span", "fileview-sess") : null;\n  if (owner && sess) {\n    sess.replaceChildren(...hostNameNodes(owner.name, sid));';
  assert.ok(VIEWER_SRC.includes(SESS_CONST), "the session tag is a const built by el() in the branch that shows it");
  const sessEntry = SEATS_READ_BY_HAND.find((e) => e.on === "sess")!;
  const sessLet = census(VIEWER_SRC.replace(SESS_CONST, '\n  let sess: HTMLElement | null = null;\n  if (owner) {\n    sess = el("span", "fileview-sess");\n    sess.replaceChildren(...hostNameNodes(owner.name, sid));'), SEATS_READ_BY_HAND.map((e) => (e === sessEntry ? { ...e, decl: "let sess = null" } : e)));
  assert.equal(sessLet.refused.length, 2, "FAILS BEFORE: the viewer's `let sess = null`, assigned in the branch, under an entry pinning that declaration: " + JSON.stringify(sessLet.refused));
  assert.match(sessLet.refused[0], /sess\.replaceChildren\(\.\.\.hostNameNodes\(owner\.name, sid\)\) seats on `sess` is bound by `let sess = null`, a reassignable binding \(let; the writes: `null` at line \d+, `el\("span", "fileview-sess"\)` at line \d+\)/, "...is refused as reassignable, naming both writes");
  assert.match(sessLet.refused[1], /bar\.appendChild\(sess\) seats `sess` bound by `sess = let sess = null; writes: `null` at line \d+, `el\("span", "fileview-sess"\)` at line \d+`, where SEATS_READ_BY_HAND read `sess = const sess = owner \? el\("span", "fileview-sess"\) : null`/, "...and the tag's own seat in the bar is refused too: the seated name's binding is not the entry's (the author's closing pass over the round-7 build, the verifiers' census-2)");
  const timesDropped = SEATS_READ_BY_HAND.find((e) => e.in === "codeBlock" && e.on === "pre")!;
  const untimed = census(VIEWER_SRC, SEATS_READ_BY_HAND.map((e) => (e === timesDropped ? { ...e, times: undefined } : e)));
  assert.deepEqual(untimed.refused.map((r) => r.replace(/lines \d+, \d+/, "lines N, M")), ["SEATS_READ_BY_HAND's entry `pre.appendChild` seating `code` in codeBlock matches 2 seats (lines N, M) where it reads 1: one entry is one seat, read by hand where it stands; a seat spelled alike in two branches says `times` and is read at each"], "an entry two seats match is refused unless it says so: one entry is one seat");
  // the round-6 review's cluster B (correctness-2, extra5-2, extra6-1, extra6-2; 2026-09-20): the assignment axis inverted. Before
  // this the second read knew innerHTML and outerHTML by name and passed every other member write unread, so each of these
  // was neither a seat nor a refusal; now a write passes by a listed name alone (NON_SEATING_WRITES), a computed name never
  const MUTANT_HTML = '"<div class=\\"fileview-mutant\\"></div>"';
  const COMPUTED_WRITE = /writes a member of `(?:md|\(md as any\))` by a computed name \[[^\]]+\] in openFileView, which the census cannot read/;
  refusedMutant(seat('md[k] = ' + MUTANT_HTML + ';'), "md[k] = html, a computed-name write", COMPUTED_WRITE);
  refusedMutant(seat('md[k] += ' + MUTANT_HTML + ';'), "md[k] += html, a compound computed-name write", COMPUTED_WRITE);
  refusedMutant(seat('(md as any)["inner" + "HTML"] = ' + MUTANT_HTML + ';'), '(md as any)["inner" + "HTML"] = html', COMPUTED_WRITE);
  refusedMutant(seat('(md as any)[`inner${"HTML"}`] = ' + MUTANT_HTML + ';'), "a template-literal index write", COMPUTED_WRITE);
  refusedMutant(seat('md["innerHTML"] = ' + MUTANT_HTML + ';'), 'md["innerHTML"] = html, a seat by a string index', SEAT_UNREAD);
  const UNLISTED_WRITE = (name: string, on: string): RegExp => new RegExp("writes " + name + " on `" + on.replace(/[()[\].]/g, "\\$&") + "` in openFileView, a member the census does not list as a seat \\(SEAT_ASSIGNS\\) or as seating nothing \\(NON_SEATING_WRITES\\)");
  refusedMutant(seat('md.innerText = "a\\nb";'), "md.innerText = ... (its setter makes a br child)", UNLISTED_WRITE("innerText", "md"));
  refusedMutant(seat('md.outerText = "x";'), "md.outerText = ...", UNLISTED_WRITE("outerText", "md"));
  refusedMutant(seat('(md.children[0] as HTMLElement).innerText = "a\\nb";'), "innerText on a child", UNLISTED_WRITE("innerText", "(md.children[0] as HTMLElement)"));
  refusedMutant(seat('[md].forEach((x) => { x.outerText = "a"; });'), "outerText in a callback", UNLISTED_WRITE("outerText", "x"));
  refusedMutant(seat('(md as any).seatCount++;'), "a ++ on a member by an unlisted name", UNLISTED_WRITE("seatCount", "(md as any)"));
  refusedMutant(seat('document.body = md;'), "document.body = md", /writes body on `document` in openFileView, a member the census does not list/);
  refusedMutant(seat('document.body.innerHTML = ' + MUTANT_HTML + ';'), "document.body.innerHTML = html, a seat on the page's body", /seats `"<div class=\\"fileview-mutant\\"><\/div>"` on `document\.body` by innerHTML = in openFileView, a seat the census has not read by hand/);
  refusedMutant(seat('[md.innerHTML] = [' + MUTANT_HTML + '];'), "an array pattern with innerHTML as a target", /seats `a value destructured from `\[[^`]*\]`` on `md` by innerHTML = in openFileView/);
  refusedMutant(seat('({ h: md.innerHTML } = { h: ' + MUTANT_HTML + ' });'), "an object pattern with innerHTML as a target", /seats `a value destructured from `\{[^`]*\}`` on `md` by innerHTML = in openFileView/);
  refusedMutant(seat('for (md.innerHTML of [' + MUTANT_HTML + ']) { break; }'), "a for-of head with innerHTML as its target", /seats `each of `\[[^`]*\]`` on `md` by innerHTML of in openFileView/);
  refusedMutant(seat('(md.innerHTML) = ' + MUTANT_HTML + ';'), "a parenthesised target", /seats `"<div class=\\"fileview-mutant\\"><\/div>"` on `md` by innerHTML = in openFileView/);
  // the round-8 fixes (the round-7 review's extra8-1, 2026-09-21): the URL push stood in visit's plain-assignment arm on the raw
  // left side, so a URL member written through a parenthesised, array, object, for-of or for-in target was a write and no URL
  // write (FAILS BEFORE: each of e8-a to e8-j and e8-n below passed with no refusal), where the innerHTML twins above were
  // seats; the push is classWrite's now, on the peeled target, and every arm reaches it
  const esc = (x: string): string => x.replace(/[()[\].*+?^$|{}\\]/g, "\\$&");
  const A4 = 'const a4 = el("a") as HTMLAnchorElement; ';
  const HREF_URL = (value: string): RegExp => new RegExp("writes a4\\.href from `" + esc(value) + "` in openFileView, a URL write");
  refusedMutant(seat(A4 + '({ href: a4.href } = { href: path });'), "FAILS BEFORE (e8-a): an object pattern with href as a target", HREF_URL("a value destructured from `{ href: path }`"));
  refusedMutant(seat(A4 + '[a4.href] = [path];'), "FAILS BEFORE (e8-b): an array pattern with href as a target", HREF_URL("a value destructured from `[path]`"));
  refusedMutant(seat(A4 + '(a4.href) = path;'), "FAILS BEFORE (e8-c): a parenthesised href target", HREF_URL("path"));
  refusedMutant(seat(A4 + 'for (a4.href of [path]) {}'), "FAILS BEFORE (e8-d): a for-of head with href as its target", HREF_URL("each of `[path]`"));
  refusedMutant(seat(A4 + 'for (a4.href in { x: 1 }) {}'), "FAILS BEFORE (e8-e): a for-in head with href as its target", HREF_URL("each of `{ x: 1 }`"));
  refusedMutant(seat(A4 + '(a4.href) += path;'), "FAILS BEFORE (e8-f): a compound assignment to a parenthesised href target", HREF_URL("path"));
  refusedMutant(seat(A4 + '[[a4.href]] = [[path]];'), "FAILS BEFORE (e8-g): a nested array pattern", HREF_URL("a value destructured from `[[path]]`"));
  refusedMutant(seat(A4 + '({ h: { href: a4.href } } = { h: { href: path } });'), "FAILS BEFORE (e8-h): a nested object pattern", HREF_URL("a value destructured from `{ h: { href: path } }`"));
  refusedMutant(seat(A4 + 'for ({ href: a4.href } of [{ href: path }]) {}'), "FAILS BEFORE (e8-n): a for-of object head", HREF_URL("each of `[{ href: path }]`"));
  refusedMutant(seat('[location.href] = [path];'), "FAILS BEFORE (e8-i): location.href as an array pattern's target", /writes location\.href from `a value destructured from `\[path\]`` in openFileView, a URL write/);
  refusedMutant(seat('({ href: location.href } = { href: path });'), "FAILS BEFORE (e8-j): location.href as an object pattern's target", /writes location\.href from `a value destructured from `\{ href: path \}`` in openFileView, a URL write/);
  assert.deepEqual(census(seat(A4 + 'a4.href = path;')).refused.length, 1, "the plain spelling, the control: one refusal, as before the fix");
  refusedMutant(seat('const { append: seatFn } = md; [el("div", "fileview-mutant")].forEach(seatFn, md);'), "a destructured seating method with an iterator thisArg", HANDED_METHOD);
  refusedMutant(seat('const { ["append"]: seatFn2 } = md; seatFn2.call(md, el("div", "fileview-mutant"));'), "a destructuring by a computed key, then call", /calls call on `seatFn2` into `md, el\("div", "fileview-mutant"\)` in openFileView, a call the census reads by its site/, 2);   // the call read by its site on `seatFn2`, and the destructuring, below
  assert.match(census(seat('const { ["append"]: seatFn2 } = md; seatFn2.call(md, el("div", "fileview-mutant"));')).refused[1], /^line \d+: \{ \["append"\]: seatFn2 \} destructures a member by a computed key, which the census cannot read/, "...the destructuring by a computed key, refused on its own");
  refusedMutant(seat('md.onclick = "md.append(el(\'div\', \'fileview-mutant\'))";'), "a handler member holding a string", /writes onclick on `md` in openFileView from a value that is not a function: a handler member holding a string runs it as code/);
  refusedMutant(seat('md.setAttribute("onclick", "this.append(el(\'div\', \'fileview-mutant\'))");'), "a handler attribute", /sets an attribute on `md` in openFileView under a name \(`"onclick"`\) the census cannot read as a literal, or one naming an on<event> handler/);
  refusedMutant(seat('md.setAttribute(attrName, "x");'), "an attribute under a name that is not a literal", /sets an attribute on `md` in openFileView under a name \(`attrName`\)/);
  const classedWrite = seat('md.textContent = "x"; md.onclick = () => {}; md.setAttribute(FV_SRCSET, "x"); md.setAttribute("data-fv-probe", "x"); md.scrollTop++; md.style.height = "0"; md.dataset.probe = "1";');
  assert.deepEqual(census(classedWrite).refused, [], "textContent, a handler holding a function, an attribute named by a constant or a literal, a ++ on a listed name, a style property and a data attribute pass");
  assert.deepEqual(seatSites(classedWrite).writes.filter((w) => w.line === plantedLine).map((w) => w.name + (w.through ? " through " + w.through : "")), ["textContent", "onclick", "scrollTop", "height through style", "probe through dataset"], "...and each passing write is CLASSED (never silent): the assignment axis records it, by a name NON_SEATING_WRITES lists or by the style or dataset rule");
  refusedMutant(seat('(md as any).style = "color: red";'), "the style attribute written as one string (the name `style` on md, not a property through it)", UNLISTED_WRITE("style", "(md as any)"));
  // the round-8 fixes (the round-7 review's correctness-2, 2026-09-21): a CSS URL written through `style` reached the network with
  // no hand read (FAILS BEFORE: c2-a, c2-b, c2-e and c2-g below passed, recorded as writes through style; c2-c and c2-h passed,
  // recorded nowhere, setProperty being listed), while the same road spelled setAttribute("style", ...) was refused. The style
  // road is the URL axis's now, inverted as the refuters asked: a write through style from a non-literal, or from a literal
  // spelling url( or javascript:, is a URL write unless NON_URL_STYLE_PROPS lists the property by hand, and a computed property
  // name through setProperty is recorded whatever the value
  const STYLE_URL = (on: string, value: string): RegExp => new RegExp("writes " + esc(on) + " from `" + esc(value) + "` in openFileView, a URL write");
  refusedMutant(seat('md.style.backgroundImage = "url(" + path + ")";'), "FAILS BEFORE (c2-a): style.backgroundImage from a non-literal", STYLE_URL("md.style.backgroundImage", '"url(" + path + ")"'));
  refusedMutant(seat('md.style.cssText = "background:url(" + path + ")";'), "FAILS BEFORE (c2-b): style.cssText from a non-literal", STYLE_URL("md.style.cssText", '"background:url(" + path + ")"'));
  refusedMutant(seat('md.style.setProperty("background-image", "url(" + path + ")");'), "FAILS BEFORE (c2-c): style.setProperty from a non-literal (the call passes on the call axis by its listing; the value is read here)", STYLE_URL('md.style.setProperty("background-image")', '"url(" + path + ")"'));
  refusedMutant(seat('md.style["backgroundImage"] = path;'), "FAILS BEFORE (c2-e): the element-access spelling through style", STYLE_URL("md.style.backgroundImage", "path"));
  refusedMutant(seat('md.style.backgroundImage = "url(https://example.invalid/x.png)";'), "FAILS BEFORE (c2-g): a literal url() through style", STYLE_URL("md.style.backgroundImage", '"url(https://example.invalid/x.png)"'));
  refusedMutant(seat('md.style.setProperty("--fv-probe", path);'), "FAILS BEFORE (c2-h): a custom property from a non-literal through setProperty", STYLE_URL('md.style.setProperty("--fv-probe")', "path"));
  refusedMutant(seat('md.style.setProperty(propName, "red");'), "a computed property name through setProperty is recorded whatever the value", STYLE_URL("md.style.setProperty(propName)", '"red"'));
  const styleClassed = seat('md.style.top = x + "px"; md.style.color = owner ? "red" : "blue"; md.style.setProperty("color", path); md.style.display = "none";');
  assert.deepEqual(census(styleClassed).refused, [], "a listed no-URL property (top, color) written from a non-literal, the same property through setProperty, and a literal that spells no url() pass");
  const classedStyle = seatSites(styleClassed);
  assert.deepEqual(classedStyle.writes.filter((w) => w.line === plantedLine).map((w) => w.name + " through " + w.through), ["top through style", "color through style", "display through style"], "...and each passing assignment is CLASSED on the assignment axis (never silent): the write through style, by the rule");
  assert.deepEqual(classedStyle.styleWrites.filter((w) => w.line === plantedLine).map((w) => w.on + " " + w.name), ["md.style top", "md.style color", "md.style color"], "...and each non-literal write a listed property passes is CLASSED on the URL axis as a style write the list excused, the setProperty one among them");
  assert.deepEqual(classedStyle.urlWrites.filter((u) => u.line === plantedLine), [], "...and none is a URL write");
  const staleStyle = census(VIEWER_SRC, undefined, undefined, undefined, undefined, undefined);
  assert.deepEqual(staleStyle.refused, [], "the pristine viewer under the live no-URL list: every listed property is written from a non-literal somewhere in the file");
  const staleWrite = census(VIEWER_SRC, undefined, undefined, undefined, undefined, undefined);
  assert.deepEqual(staleWrite.refused, [], "the pristine viewer under the live tables");
  // the round-6 review's cluster C (correctness-3, extra6-3; 2026-09-20): a reflection global is read by its binding and
  // passes as a member call's receiver alone. Before this `isSite` knew the receiver's bare spelling, so each of these
  // passed with no site and no refusal while the header said a site-read method read without being called failed
  const REFLECTION = /reads (?:Reflect|Object|Function)(?: \(as `[^`]+`\))? other than as the receiver of a member call: a reflection global stored, aliased, handed on or returned reaches any member by a string/;
  const aliased = refusedMutant(seat('const R = Reflect; R.set(md, "innerHTML", ' + MUTANT_HTML + ');'), "const R = Reflect; R.set(md, ...)", /calls set on `R` into `md, "innerHTML", "<div class=\\"fileview-mutant\\"><\/div>"` in openFileView, a call the census reads by its site/, 2);   // R.set is a site read by its binding and not listed, and the alias declaration reads Reflect
  assert.match(aliased[1], REFLECTION, "...the alias declaration `const R = Reflect` is a read of Reflect other than as a call's receiver");
  refusedMutant(seat('window.Reflect.set(md, "innerHTML", ' + MUTANT_HTML + ');'), "window.Reflect.set(md, ...)", /calls set on `window\.Reflect` into `md, "innerHTML", "<div class=\\"fileview-mutant\\"><\/div>"` in openFileView, a call the census reads by its site/);
  refusedMutant(seat('globalThis.Object.assign(md, { innerHTML: ' + MUTANT_HTML + ' });'), "globalThis.Object.assign(md, { innerHTML })", /calls assign on `globalThis\.Object` into `md, \{innerHTML\}` in openFileView, a call the census reads by its site/);
  refusedMutant(seat('const s = Reflect.set; s(md, "innerHTML", ' + MUTANT_HTML + ');'), "const s = Reflect.set; s(md, ...)", REFLECTION);
  refusedMutant(seat('[Reflect].forEach((R2) => R2.set(md, "innerHTML", ' + MUTANT_HTML + '));'), "[Reflect].forEach(...)", REFLECTION);
  refusedMutant(seat('const seatWith = (r: typeof Reflect) => r.set(md, "innerHTML", ' + MUTANT_HTML + '); seatWith(Reflect);'), "Reflect handed as an argument", REFLECTION);
  // the round-6 review's item 7 (2026-09-20), the forms its rule refuses (the argument axis, the string roads, the URL writes;
  // the analyst's and the refuters' forms at the round-6 pre-answers), each red with the planted line
  refusedMutant(seat('addCopyBtn(load.parentElement!, "");'), "a body root's parent handed to a helper (the argument axis)", /hands `load\.parentElement!`, a node of the tree read through parentElement, to addCopyBtn\(\.\.\.\) in openFileView, a callee the census has not read by hand/);
  refusedMutant(seat('const pe = load.parentElement!; wrapCodeLines(pe);'), "a node held in a const, then handed", /hands `pe`, a node of the tree read through parentElement \(bound by `const pe = load\.parentElement!`\), to wrapCodeLines\(\.\.\.\) in openFileView/);
  const STRING_ROAD = /with a first argument that is not a function: a string road \(eval, a timer's string, Function, import\) runs code the census cannot read/;
  refusedMutant(seat('eval("md.append(el(\'div\', \'fileview-mutant\'))");'), "eval(string)", STRING_ROAD);
  refusedMutant(seat('const ev = eval; ev("md.append(el(\'div\', \'fileview-mutant\'))");'), "eval by an alias", STRING_ROAD);
  refusedMutant(seat('setTimeout("md.append(el(\'div\', \'fileview-mutant\'))", 0);'), "setTimeout(string)", STRING_ROAD);
  refusedMutant(seat('setInterval("md.append(el(\'div\', \'fileview-mutant\'))", 1);'), "setInterval(string)", STRING_ROAD);
  refusedMutant(seat('void import("data:text/javascript,md.append(el(\'div\', \'fileview-mutant\'))");'), "a dynamic import", STRING_ROAD);
  refusedMutant(seat('const F = new Function("m", "m.append(document.createElement(\'div\'))"); F(md);'), "new Function(...)", REFLECTION, 2);   // Function read other than as a call's receiver, and the string road
  refusedMutant(seat('location.href = "javascript:md.append(el(\'div\', \'fileview-mutant\'))";'), "location.href = a javascript: literal", /writes location\.href from `"javascript:[^`]*"` in openFileView, a URL write/);
  refusedMutant(seat('const a2 = el("a") as HTMLAnchorElement; a2.href = "javascript:void md.append(el(\'div\', \'fileview-mutant\'))"; a2.click();'), "an anchor's href = a javascript: literal, then click", /writes a2\.href from `"javascript:[^`]*"` in openFileView, a URL write/);
  refusedMutant(seat('const u = mediaUrlLive; const a3 = el("a") as HTMLAnchorElement; a3.href = u!;'), "an anchor's href from a value that is not a literal", /writes a3\.href from `u!` in openFileView, a URL write/);
  // extra6-4: `add` seats an option on a select or an options collection, so it is a site read by hand there, while a class
  // list's and a Set's add pass by the name (NON_SEATING_METHODS); the item-7 commit gave the rule, this is its red-before
  refusedMutant(seat('const sel = el("select") as HTMLSelectElement; sel.add(el("option") as HTMLOptionElement);'), "FAILS BEFORE: a select's add", /calls add on `sel` into `el\("option"\) as HTMLOptionElement` in openFileView, a call the census reads by its site/);
  refusedMutant(seat('const sel2 = el("select") as HTMLSelectElement; sel2.options.add(el("option") as HTMLOptionElement);'), "FAILS BEFORE: an options collection's add", /calls add on `sel2\.options` into `el\("option"\) as HTMLOptionElement` in openFileView, a call the census reads by its site/);
  assert.deepEqual(census(seat('const seen = new Set<string>(); seen.add("x"); md.classList.add("fileview-mutant");')).refused, [], "a Set's add and a class list's add pass by the name");
  // the author's closing pass over the round-7 build (the verifiers' findings, 2026-09-20). census-1: the URL axis read the
  // assignment spelling alone, so a URL member written through setAttribute passed (FAILS BEFORE: each of the four below green)
  const URL_ATTR = (name: string, value: string): RegExp => new RegExp("writes bar\\.setAttribute\\(" + name.replace(/[()[\].]/g, "\\$&") + "\\) from `" + value.replace(/[()[\].]/g, "\\$&") + "` in openFileView, a URL write \\(a member the assignment axis's hand read flags as a URL, a member of location, an attribute set under a name that is not aria-\\* or data-\\* and not listed as carrying no URL, a CSS property through style or style\\.setProperty not listed as taking no url\\(\\), a method of location, or window\\.open\\)");
  refusedMutant(seat('bar.setAttribute("href", path);'), 'FAILS BEFORE: bar.setAttribute("href", path)', URL_ATTR('"href"', "path"));
  refusedMutant(seat('bar.setAttribute("href", "javascript:alert(1)");'), 'FAILS BEFORE: bar.setAttribute("href", "javascript:...")', URL_ATTR('"href"', '"javascript:alert(1)"'));
  refusedMutant(seat('bar.setAttribute("srcdoc", path);'), 'FAILS BEFORE: bar.setAttribute("srcdoc", path)', URL_ATTR('"srcdoc"', "path"));
  refusedMutant(seat('bar.setAttribute("src", path);'), 'FAILS BEFORE: bar.setAttribute("src", path)', URL_ATTR('"src"', "path"));
  assert.match(refusedMutant(seat('bar.setAttributeNS(null, "href", path);'), 'bar.setAttributeNS(null, "href", path)', /calls setAttributeNS on `bar`, a method the census does not list/, 2)[1], /writes bar\.setAttributeNS\("href"\) from `path` in openFileView, a URL write/, "the namespaced spelling is a URL write too (and its name is unlisted, since the viewer never calls it: the call axis's own refusal comes first)");
  refusedMutant(seat('bar.setAttribute("role", path);'), 'an attribute under a name that is neither aria-* nor data-* nor listed as carrying no URL, from a non-literal: refused until read (the inverted default on the URL axis\'s attribute road)', URL_ATTR('"role"', "path"));
  const attrClassed = seat('bar.setAttribute("aria-label", path); bar.setAttribute("data-fv-probe", path); bar.setAttribute("href", "/files"); bar.setAttribute("open", "");');
  assert.deepEqual(census(attrClassed).refused, [], "an aria-* or data-* attribute set from a non-literal passes by the rule, and a URL attribute set from a literal that is not javascript: passes");
  assert.deepEqual(seatSites(attrClassed).attrWrites.filter((a) => a.line === plantedLine).map((a) => a.name), ["aria-label", "data-fv-probe"], "...and each passing non-literal attribute write is CLASSED, never silent");
  // census-4: a method of `location` passed under String.prototype.replace's listing, and window.open under the browser's `open`
  refusedMutant(seat('location.replace(path);'), "FAILS BEFORE: location.replace(path)", /writes location\.replace from `path` in openFileView, a URL write/);
  refusedMutant(seat('window.location.assign(path);'), "window.location.assign(path)", /writes window\.location\.assign from `path` in openFileView, a URL write/);
  refusedMutant(seat('location.reload();'), "location.reload(), no argument: a navigation the census cannot read the target of, refused until listed", /writes location\.reload from `` in openFileView, a URL write/);
  refusedMutant(seat('window.open(path);'), "FAILS BEFORE: window.open(path)", /writes window\.open from `path` in openFileView, a URL write/);
  refusedMutant(seat('globalThis.open("javascript:alert(1)");'), 'globalThis.open("javascript:...")', /writes globalThis\.open from `"javascript:alert\(1\)"` in openFileView, a URL write/);
  assert.deepEqual(census(seat('location.assign("/files"); window.open("/files", "_blank");')).refused, [], "a literal that is not javascript: passes at both, as an assignment's literal does");
  // the round-8 fixes (the round-7 review's correctness-1, 2026-09-21): the URL arm preempted the seat and call axes on a receiver
  // whose chain names `location`, and a literal first argument recorded nothing (FAILS BEFORE: c1-a and c1-f below were refused
  // as URL writes, on the URL axis with a URL write's message; c1-b, c1-d, c1-g and c1-j passed silent). The chain is two passes now,
  // the shape and then each axis, and the call axis's exclusion is keyed on the (location, navigation-method) pair alone
  const LOC_SEAT = /seats `[^`]*` on `(?:nav\.location|\(window\.location as any\)|\(document\.location as any\))` by (?:append|setHTMLUnsafe) in openFileView, a seat the census has not read by hand/;
  const NAV = 'const nav = { location: md }; ';
  refusedMutant(seat(NAV + 'nav.location.append(el("div", "fileview-mutant"));'), "FAILS BEFORE (c1-a): append of an element on a location-named receiver, refused as a URL write", LOC_SEAT);
  refusedMutant(seat(NAV + 'nav.location.append("fileview-mutant text");'), "FAILS BEFORE (c1-b): append of a literal on a location-named receiver, silent", LOC_SEAT);
  refusedMutant(seat(NAV + 'nav.location.setHTMLUnsafe(\'<div class="fileview-mutant"></div>\');'), "FAILS BEFORE (c1-d): setHTMLUnsafe of a literal on a location-named receiver, silent", LOC_SEAT);
  refusedMutant(seat('(window.location as any).append(el("div", "fileview-mutant"));'), "FAILS BEFORE (c1-f): append on window.location, refused as a URL write", LOC_SEAT);
  refusedMutant(seat('(document.location as any)!.setHTMLUnsafe(\'<div class="fileview-mutant"></div>\');'), "FAILS BEFORE (c1-g): setHTMLUnsafe on document.location, silent", LOC_SEAT);
  refusedMutant(seat(NAV + 'nav.location.foo("x");'), "FAILS BEFORE (c1-j): an unlisted method on a location-named receiver with a literal argument, silent", /calls foo on `nav\.location`, a method the census does not list as seating or as seating nothing/);
  refusedMutant(seat(NAV + 'nav.location.assign(path);'), "the navigation pair on a location-named receiver is the URL axis's alone, one refusal (the call axis does not read the pair)", /writes nav\.location\.assign from `path` in openFileView, a URL write/);
  refusedMutant(seat('md.assign(path);'), "`assign` on any other receiver is an unlisted method: the exclusion is keyed on the pair, never on the name", /calls assign on `md`, a method the census does not list as seating or as seating nothing/);
  // census-3: the argument axis read direct arguments alone, so a node handed inside an object literal, an array literal or a
  // concise arrow passed, and an object literal in a seats key was `{...}`, so a property added to a listed call was no new seat
  refusedMutant(seat('wrapCodeLines({ up: main.parentElement } as any);'), "FAILS BEFORE: a node inside an object literal handed to a callee", /hands `\{ up: main\.parentElement \}`, a node of the tree read through parentElement, to wrapCodeLines\(\.\.\.\) in openFileView, a callee the census has not read by hand/);
  refusedMutant(seat('wrapCodeLines([main.parentElement] as any);'), "a node inside an array literal", /hands `\[ main\.parentElement \]`, a node of the tree read through parentElement, to wrapCodeLines/);
  refusedMutant(seat('wrapCodeLines((() => main.parentElement) as any);'), "a node as a concise arrow's value", /hands `\(\) => main\.parentElement`, a node of the tree read through parentElement, to wrapCodeLines/);
  refusedMutant(seat('wrapCodeLines({ deep: { up: [main.parentElement] } } as any);'), "a node nested two literals deep", /hands `\{ deep: \{ up: \[ main\.parentElement \] \} \}`, a node of the tree/);
  const MOUNT_LINE = "ed.mount(host, {\n        text: norm(text!), ext:";
  assert.equal(VIEWER_SRC.split(MOUNT_LINE).length, 2, "the editor mount is written once");
  const mountProp = census(VIEWER_SRC.replace(MOUNT_LINE, "ed.mount(host, { hostParent: host.parentElement,\n        text: norm(text!), ext:"));
  assert.equal(mountProp.refused.length, 3, "FAILS BEFORE: a property added to a listed site-read call's object literal: a new seats key, a handed node inside the literal, and the entry gone stale: " + JSON.stringify(mountProp.refused));
  assert.match(mountProp.refused[0], /calls mount on `ed` into `host, \{hostParent, text, ext, onChange, onSave, /, "the seats key spells the literal's property names, so the added property is a new seat");
  assert.match(mountProp.refused[1], /^SEATS_READ_BY_HAND lists `ed\.mount` seating `host, \{text, ext, onChange, onSave, .* in enterEdit, and the source has no such seat: the entry is stale/, "...the entry for the old key is stale");
  assert.match(mountProp.refused[2], /hands `\{ hostParent: host\.parentElement \}`, a node of the tree read through parentElement, to ed\.mount/, "...and the node inside the literal is a hand-off read on its own");
  // census-2: the receiver was held to its declaration while the SEATED name was matched by its spelling alone, and a shadow
  // wearing the listed declaration's exact spelling passed the text compare
  const SEAT_BODY = "\n  main.appendChild(body);\n";
  assert.equal(VIEWER_SRC.split(SEAT_BODY).length, 2, "the body's seat in main is written once");
  const shadowBody = census(VIEWER_SRC.replace(SEAT_BODY, '\n  { const body = el("div", "fileview-mutant"); main.appendChild(body); }\n'));
  assert.equal(shadowBody.refused.length, 2, "FAILS BEFORE: a block's `const body = el(...)` seated through the listed main.appendChild(body): " + JSON.stringify(shadowBody.refused));
  assert.match(shadowBody.refused[0], /main\.appendChild\(body\) seats `body` bound by `body = const body = el\("div", "fileview-mutant"\)`, where SEATS_READ_BY_HAND read `body = const body = el\("div", "fileview-body"\)`: what is seated is not the binding read by hand/, "the seated name's binding is not the entry's: the entry pins the viewer's own body");
  assert.match(shadowBody.refused[1], /const body = el\("div", "fileview-mutant"\); declares `body` as `el\("div", "fileview-mutant"\)`, not the viewer's own `el\("div", "fileview-body"\)`/, "...and the declaration itself is refused: the sanctioned name is declared by the viewer alone");
  refusedMutant(seat('const keep = (body: HTMLElement): void => { readPlace(body, ""); };'), "a parameter named body in a function BODY_HANDED_TO does not list as reading the body under its own parameter", /declares a parameter named `body` in keep, which BODY_HANDED_TO does not list as reading the body under its own parameter/);
  const SEAT_BOX = "\n  box.appendChild(bar); box.appendChild(main);\n  wrap.appendChild(box);\n";
  assert.equal(VIEWER_SRC.split(SEAT_BOX).length, 2, "the card's seat in the wrapper is written once in the local viewer");
  const shadowWrap = census(VIEWER_SRC.replace(SEAT_BOX, '\n  box.appendChild(bar); box.appendChild(main);\n  { const wrap = el("div"); wrap.appendChild(box); }\n'));
  assert.equal(shadowWrap.refused.length, 2, "FAILS BEFORE: the listed seat replaced by one on a block's `const wrap = el(\"div\")`, spelled exactly as the listed declaration: the seat, and the wrapper's own seat in the page's body, which seats the name: " + JSON.stringify(shadowWrap.refused));
  assert.match(shadowWrap.refused[0], /wrap\.appendChild\(box\) in openFileView: `wrap` is declared 2 times in openFileView \(lines \d+, \d+\): a second declaration of a listed name in the entry's function is refused, whatever it spells/, "a second declaration of a listed receiver name in the entry's function is refused, so the text compare is never the last word");
  assert.match(shadowWrap.refused[1], /document\.body\.appendChild\(wrap\) in openFileView: `wrap` is declared 2 times in openFileView/, "...and so is every seat of the name in that function");
  const shadowSeated = census(seat('{ const outlineBtn = el("button", "fileview-mutant"); viewGroup.appendChild(outlineBtn); }'));
  assert.equal(shadowSeated.refused.length, 4, "a second declaration of a listed SEATED name, spelled otherwise: the live seat and the live hand-off of the name under the second declaration, the planted seat's binding, and the entry's two seats: " + JSON.stringify(shadowSeated.refused));
  assert.match(shadowSeated.refused[0], /^line \d+: viewGroup\.appendChild\(outlineBtn\) in openFileView: `outlineBtn` is declared 2 times in openFileView \(lines \d+, \d+\)/, "the live seat of the name is refused under the second declaration");
  assert.match(shadowSeated.refused[1], new RegExp("^line " + plantedLine + ": viewGroup\\.appendChild\\(outlineBtn\\) seats `outlineBtn` bound by `outlineBtn = const outlineBtn = el\\(\"button\", \"fileview-mutant\"\\)`, where SEATS_READ_BY_HAND read `outlineBtn = const outlineBtn = el\\(\"button\", \"fileview-btn fileview-outline-btn\"\\) as HTMLButtonElement`"), "the planted seat's seated binding is not the entry's");
  assert.match(shadowSeated.refused[2], /^SEATS_READ_BY_HAND's entry `viewGroup\.appendChild` seating `outlineBtn` in openFileView matches 2 seats/, "the entry's two seats");
  assert.match(shadowSeated.refused[3], /^line \d+: flash\(outlineBtn\) in openFileView: `outlineBtn` is declared 2 times in openFileView/, "and the live hand-off of the name to an imported helper is refused under it too");
  // records-1: an element the census can see by its shape, handed to a callee this file does not declare, was read on no axis
  const ELEMENT_HANDED = /to addCopyBtn\(\.\.\.\) in openFileView, a callee this file does not declare and the census has not read by hand for what it does with an element it is handed/;
  refusedMutant(seat('addCopyBtn(main, "");'), "FAILS BEFORE: an el()-built const handed to an imported helper", /hands `main`, el\(\.\.\.\) bound to `main` \(bound by `const main = el\("div", "fileview-main"\)`\), to addCopyBtn/);
  refusedMutant(seat('const wrap2 = document.querySelector(".fileview-body") as HTMLElement; addCopyBtn(wrap2, "");'), "FAILS BEFORE: a query result handed to an imported helper", /hands `wrap2`, a querySelector\(\.\.\.\) result bound to `wrap2`/);
  refusedMutant(seat('addCopyBtn(loaderEl(), "");'), "a local builder's result handed to an imported helper", /hands `loaderEl\(\)`, a call of the builder loaderEl, which returns el\(\.\.\.\) bound to `load`, to addCopyBtn/);
  refusedMutant(seat('[main].forEach((m: HTMLElement) => addCopyBtn(m, ""));'), "a parameter typed as an element handed to an imported helper", /hands `m`, a parameter typed HTMLElement bound to `m`/);
  refusedMutant(seat('addCopyBtn(document.createElement("div"), "");'), "a createElement result handed to an imported helper", /hands `document\.createElement\("div"\)`, a createElement\(\.\.\.\) result, to addCopyBtn/);
  refusedMutant(seat('addCopyBtn({ box } as any, "");'), "an element inside an object literal handed to an imported helper", /hands `\{ box \}`, el\(\.\.\.\) bound to `box`/);
  assert.match(census(seat('addCopyBtn(main, "");')).refused[0], ELEMENT_HANDED, "...the refusal names the callee as one the file does not declare");
  const secondFlash = census(seat('flash(outlineBtn);'));
  assert.deepEqual(secondFlash.refused, ["ARGS_READ_BY_HAND's entry `outlineBtn` handed to flash in openFileView matches 2 hand-offs where it reads 1: one entry is one hand-off, read where it stands; one spelled alike in two branches says `times` and is read at each"], "a second hand-off of a listed element to a listed callee is a second entry: the argument table is one entry per site, as the seat table is");
  assert.deepEqual(census(seat('noteBar("x"); const nb = noteBar("y"); copySay(ICON_CHECK, "x"); imgFailed(main);')).refused, [], "an element handed to a LOCAL function passes: its seats are read in this file (imgFailed's are listed)");
  // the argument and URL tables are keyed on the seat too and held live: a stale entry, and a hand-off bound elsewhere than the entry says
  const staleArg = census(VIEWER_SRC, undefined, undefined, [...ARGS_READ_BY_HAND, { in: "openFileView", to: "gone", arg: "x.parentElement", is: "an entry the source has no hand-off for" }]);
  assert.deepEqual(staleArg.refused, ["ARGS_READ_BY_HAND lists `x.parentElement` handed to gone in openFileView, and the source has no such hand-off: the entry is stale, remove it or read the site again"]);
  const staleUrl = census(VIEWER_SRC, undefined, undefined, undefined, [...URL_WRITES_READ_BY_HAND, { in: "openFileView", on: "a.href", value: "gone", is: "an entry the source has no write for" }]);
  assert.deepEqual(staleUrl.refused, ["URL_WRITES_READ_BY_HAND lists `a.href` written from `gone` in openFileView, and the source has no such write: the entry is stale, remove it or read the site again"]);
  const staleAttr = census(VIEWER_SRC, undefined, undefined, undefined, undefined, [...ATTR_NAMES_READ_BY_HAND, { in: "openFileView", on: "md", name: "gone", is: "an entry the source has no write for" }]);
  assert.deepEqual(staleAttr.refused, ["ATTR_NAMES_READ_BY_HAND lists `gone` set on `md` in openFileView, and the source has no such write: the entry is stale, remove it or read the site again"]);
  const PCLIMB = "; p = a.parentElement) a = p;";
  assert.equal(VIEWER_SRC.split(PCLIMB).length, 2, "figureAnchor's climb writes p once in its update");
  const pRebound = census(VIEWER_SRC.replace(PCLIMB, "; p = a.parentNode as Element) a = p;"));
  assert.equal(pRebound.refused.length, 2, "the let p handed to oneImg and linkAround, written from another expression than `holds` names: " + JSON.stringify(pRebound.refused));
  for (const one of pRebound.refused) assert.match(one, /hands `p` is bound by `let p = a\.parentElement`, and the entry's `holds` \(`a\.parentElement`\) is not what every write to it assigns \(`a\.parentElement` at line \d+, `a\.parentNode as Element` at line \d+\)/);
  // the branch's verification pass finding census-4 (2026-09-20): an argument the resolver cannot read is refused with its line (before this rootsOf threw, naming the expression and not the line)
  refusedMutant(seat('body.append(...[el("div", "fileview-mutant")]);'), "a spread into body.append", /body\.append\(\.\.\.\) seats `\.\.\.\[el\("div", "fileview-mutant"\)\]`, an expression the census cannot resolve to a root \(a seated expression the census cannot resolve/);
  refusedMutant(seat('const kids = [el("div", "fileview-mutant")]; body.append(...kids);'), "a spread of a variable into body.append", /body\.append\(\.\.\.\) seats `\.\.\.kids`, an expression the census cannot resolve to a root/);
  // the round-8 fixes (the round-7 review's extra9-1, 2026-09-21): the resolver took the LAST return of a builder and the last
  // textual assignment of a bare name (FAILS BEFORE: the early return below left div.fileview-mutant out of every root list with
  // no refusal, and the branch-assigned name resolved to its last assignment); every return is read from the tree and united, and
  // a name assigned more than once in its declaring block is refused
  const CODE_WRAP = '\n  const wrap = el("div", "fileview-code");\n';
  assert.equal(VIEWER_SRC.split(CODE_WRAP).length, 2, "codeBlock declares its wrap once, at the top of the builder");
  const earlyReturn = census(VIEWER_SRC.replace(CODE_WRAP, CODE_WRAP + '  const early = el("div", "fileview-mutant"); if (text.length > 1e9) return early;\n'));
  assert.deepEqual(earlyReturn.refused, [], "a guarded one-line early return in the codeBlock builder: no refusal");
  assert.deepEqual([...earlyReturn.seated.keys()].filter((k) => !before.seated.has(k)), ["div.fileview-mutant"], "FAILS BEFORE: the root the early return hands back is derived beside the last return's, so the lists comparison reds (before this only the last `return wrap;` was read)");
  const nonName = census(VIEWER_SRC.replace(CODE_WRAP, CODE_WRAP + '  if (text.length > 1e9) return el("div", "fileview-mutant");\n'));
  assert.ok(nonName.refused.length >= 1 && nonName.refused.every((r) => /^line \d+: body\.replaceChildren\(\.\.\.\) seats `[^`]*codeBlock\([^`]*`, an expression the census cannot resolve to a root \(the builder codeBlock returns a bare name at every return, and line \d+ returns `el\("div", "fileview-mutant"\)`, which the census cannot resolve/.test(r)), "a builder returning anything but a bare name is refused at each seat of the builder (bare or in a ternary's branch), with the return's line: " + JSON.stringify(nonName.refused));
  assert.equal(nonName.refused.length, seatSites(VIEWER_SRC).sites.filter((x) => x.body && x.via === "replaceChildren" && x.whole.includes("codeBlock(")).length, "...once per body seat that resolves through the builder, derived from the second read's seats (bare or in a ternary's branch)");
  refusedMutant(seat('let root2 = el("div", "fileview-md"); if (owner) root2 = el("div", "fileview-mutant"); body.append(root2);'), "FAILS BEFORE: a bare seated name assigned in a branch after its declaration", /body\.append\(\.\.\.\) seats `root2`, an expression the census cannot resolve to a root \(the variable root2 is assigned 2 times in the block that declares it \(lines \d+, \d+; a null or undefined write is not counted\), so it resolves to no one expression at the seat/);
  const nulled = census(seat('let root4: HTMLElement | null = null; if (owner) root4 = el("div", "fileview-mutant"); if (root4) body.append(root4); root4 = null;'));
  assert.deepEqual(nulled.refused, [], "a null-initialised name assigned its element once and nulled after (the viewer's fallback textarea's shape) resolves: the nullish writes assign no element and are not counted");
  assert.deepEqual([...nulled.seated.keys()].filter((k) => !before.seated.has(k)), ["div.fileview-mutant"], "...to the one element write's root");
  const declaredOnce = census(seat('const root3 = el("div", "fileview-mutant"); body.append(root3);'));
  assert.deepEqual(declaredOnce.refused, [], "a name bound once resolves through its initializer");
  assert.deepEqual([...declaredOnce.seated.keys()].filter((k) => !before.seated.has(k)), ["div.fileview-mutant"], "...to its root");
  // the action-context accessor passes at its one site alone (the round-5 review's extra8-2): the spelling anywhere else is refused
  const ACCESSOR_ELSEWHERE = /body: \(\) => body is written outside the object literal declared `const ctx: FileViewActionCtx =`/;
  refusedMutant(seat('const other = { body: () => body };'), "the accessor in a second object literal", ACCESSOR_ELSEWHERE);
  refusedMutant(seat('const acc = () => ({ body: () => body });'), "the accessor in a function's returned literal", ACCESSOR_ELSEWHERE);
  refusedMutant(seat('let held = { path, body: () => body, open: true };'), "the accessor in a variable's literal", ACCESSOR_ELSEWHERE);
  refusedMutant(seat('const ctx2: FileViewActionCtx = { path, body: () => body };'), "the accessor under a renamed ctx const", ACCESSOR_ELSEWHERE);
  refusedMutant(seat('installFilePrint({ card: null, bar: null, body: () => body, typing: typingHere, onClose: (cb) => { closeHooks.push(cb); } });'), "the accessor moved into a callee's argument", ACCESSOR_ELSEWHERE);   // nulls for the card and the bar: the listed elements handed a second time would be their own refusals (the argument table is one entry per hand-off)
  assert.ok(VIEWER_SRC.includes("\n  const ctx: FileViewActionCtx = {\n"), "the sanctioned site is declared as the census expects");
  const ctxRenamed = census(VIEWER_SRC.replace("\n  const ctx: FileViewActionCtx = {\n", "\n  const actions: FileViewActionCtx = {\n"));
  const ctxEntry = SEATS_READ_BY_HAND.find((e) => e.in === "openFileView" && e.on === "a" && e.via === "mount" && e.seats === "ctx")!;   // the mount's entry, its `seatedBy` the one home of the ctx declaration's held text (the round-8 fold: the initializer is over 300 characters, so the text is held as its first 80 characters beside the sha256 of the whole)
  assert.match(ctxEntry.seatedBy!, /^ctx = const ctx = .{80} \.\.\. sha256:[0-9a-f]{64}$/, "the ctx entry's `seatedBy` holds the hashed form, the one live text over 300 characters");
  // the header's two clauses on the hash form, held by execution (the author's closing pass over round 8, the fold's verifiers'
  // mechanism-2 and records-3): the digest is of the FLATTENED initializer, comments blanked and whitespace collapsed as the
  // census reads it, recomputed here from that text and matched to the table's field; and the ctx initializer is the ONE hashed
  // text across the three tables, by a count of every string field carrying the hash form
  const sfCtx = ts.createSourceFile("file-view.ts", VIEWER_SRC, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
  const ctxInits: string[] = [];
  const findCtx = (n: ts.Node): void => { if (ts.isVariableDeclaration(n) && ts.isIdentifier(n.name) && n.name.text === "ctx" && n.initializer && n.type && n.type.getText(sfCtx) === "FileViewActionCtx") ctxInits.push(n.initializer.getText(sfCtx).replace(/\s+/g, " ")); ts.forEachChild(n, findCtx); };
  findCtx(sfCtx);
  assert.equal(ctxInits.length, 1, "file-view.ts declares one `ctx: FileViewActionCtx`");
  assert.ok(ctxInits[0].length > 300, "its initializer, flattened, is over 300 characters, the hash line (" + ctxInits[0].length + ")");
  assert.equal(ctxEntry.seatedBy, "ctx = const ctx = " + ctxInits[0].slice(0, 80) + " ... sha256:" + crypto.createHash("sha256").update(ctxInits[0]).digest("hex"), "the table's hashed form is the first 80 characters and the sha256 of the flattened initializer (comments blanked, whitespace collapsed to single spaces), the text the header names, so a reader recomputes the digest from it");
  const hashedFields = [...SEATS_READ_BY_HAND, ...ARGS_READ_BY_HAND, ...URL_WRITES_READ_BY_HAND].flatMap((e) => Object.entries(e).filter(([, v]) => typeof v === "string" && / \.\.\. sha256:[0-9a-f]{64}/.test(v)).map(([k, v]) => k + " = " + v));
  assert.deepEqual(hashedFields, ["seatedBy = " + ctxEntry.seatedBy], "one hashed text across the three tables, the ctx entry's `seatedBy`: the header's clause that openFileView's `ctx` initializer is the one such text in the tables today");
  assert.deepEqual(ctxRenamed.refused.filter((r) => !ACCESSOR_ELSEWHERE.test(r)).map((r) => r.replace(/^line \d+: /, "")), ["the census passes the action-context accessor `body: () => body` inside the object literal declared `const ctx: FileViewActionCtx = {`, and the source declares no such literal: read the hand-out by hand again", "a.mount(ctx) seats `ctx` bound by `ctx = a global`, where SEATS_READ_BY_HAND read `" + ctxEntry.seatedBy + "`: what is seated is not the binding read by hand (the entry names each seated bare name's declaration in `seatedBy`)"], "the ctx declaration renamed: the census holds the source to it, and the mount seated `ctx` is bound to no declaration now (the seated name's binding, the author's closing pass over the round-7 build)");
  assert.equal(ctxRenamed.refused.filter((r) => ACCESSOR_ELSEWHERE.test(r)).length, 1, "...and the live accessor is refused with its line, since its literal is no longer the declared one");
  // the table is read, not decorative: a live site whose entry is removed reds with its line, and an entry with no site reds
  const dropped = SEATS_READ_BY_HAND.find((e) => e.in === "mdBlock" && e.on === "box" && e.via === "replaceChildren" && e.seats.startsWith("...Array.from("))!;
  const withoutEntry = census(VIEWER_SRC, SEATS_READ_BY_HAND.filter((e) => e !== dropped));
  assert.equal(withoutEntry.refused.length, 1, "the markdown root's own seat, unlisted, is refused: " + JSON.stringify(withoutEntry.refused));
  assert.match(withoutEntry.refused[0], /^line \d+: box\.replaceChildren\(\.\.\.Array\.from\(clean\.childNodes\)\) seats `\.\.\.Array\.from\(clean\.childNodes\)` on `box` by replaceChildren in mdBlock, a seat the census has not read by hand/);
  const stale = census(VIEWER_SRC, [...SEATS_READ_BY_HAND, { in: "openFileView", on: "gone", via: "append", seats: "x", is: "an entry the source has no seat for" }]);
  assert.deepEqual(stale.refused, ["SEATS_READ_BY_HAND lists `gone.append` seating `x` in openFileView, and the source has no such seat: the entry is stale, remove it or read the site again"], "a stale entry is refused, so the table holds the live sites and nothing more");
  for (const [key, want] of [[(e: SeatRead) => e.in === "openFileView" && e.on === "main" && e.via === "appendChild", /^line \d+: main\.appendChild\(body\) seats `body` on `main` by appendChild in openFileView, a seat the census has not read by hand/], [(e: SeatRead) => e.in === "imgFailed" && e.on === "why" && e.seats === "hint", /^line \d+: why\.appendChild\(hint\) seats `hint` on `why` by appendChild in imgFailed, a seat the census has not read by hand \(the table's entry for `why\.appendChild` in imgFailed seats `offer`, not this/]] as const) {
    const gone = SEATS_READ_BY_HAND.find(key)!;
    const r = census(VIEWER_SRC, SEATS_READ_BY_HAND.filter((e) => e !== gone));
    assert.equal(r.refused.length, 1, "the live seat of a removed entry reds, and nothing else: " + JSON.stringify(r.refused)); assert.match(r.refused[0], want);
  }
  const moved = census(VIEWER_SRC, SEATS_READ_BY_HAND.map((e) => (e === dropped ? { ...e, in: "renderBody" } : e)));
  assert.equal(moved.refused.length, 2, "an entry keyed to another function matches nothing: the live site reds and the entry is stale: " + JSON.stringify(moved.refused));
  // the seats the table holds are the file's: every non-body seat matched an entry (no refusal above), and the population is stated
  const live = seatSites(VIEWER_SRC);
  assert.equal(live.computed.length, 0, "file-view.ts calls nothing through a computed name");
  assert.ok(live.sites.filter((s) => s.body).length >= 10 && live.sites.filter((s) => !s.body).length > live.sites.filter((s) => s.body).length, "the seat read finds the file's seats, on the body token and on the rest (the counts are the commit's, derived by this read, not kept here)");
  const seatKeys = live.sites.filter((s) => !s.body).map((s) => s.fn + "|" + s.on + "|" + s.via + "|" + s.seats);
  assert.equal(new Set(seatKeys).size, SEATS_READ_BY_HAND.length, "one entry per distinct seat (function, receiver, form, what is seated): the table has no duplicate and no seat is covered twice (the round-6 review's cluster A)");
  assert.equal(SEATS_READ_BY_HAND.reduce((n, e) => n + (e.times ?? 1), 0), seatKeys.length, "...and the entries' `times` sum to the live seats, so every seat spelled alike is counted");
  // the triple count is held EQUAL to P7's own number for it, read from the sentence (the round-7 review's extra6-4: an inequality
  // here let the sentence's "rise of 30, which is what the triple hid" go false by one the first time a seat lands at a new
  // triple; the maintainer's OPEN-5 ruling: the number stays derived and read from P7, and a parse that finds no number FAILS here)
  const tripleCells = [...sectionPart("P7. **", "**Derivations and their unknown cases.**").matchAll(/the triple key gives (\d+) at the round-6 file and (\d+) at the round-7 file/g)];
  assert.equal(tripleCells.length, 1, "P7 states the triple key's two cells once, in the sentence's form (a sentence the pattern does not find is a loud failure here, never a default and never a compare against undefined)");
  const triplesLive = new Set(live.sites.filter((s) => !s.body).map((s) => s.fn + "|" + s.on + "|" + s.via)).size;
  assert.equal(triplesLive, Number(tripleCells[0][2]), "P7's own number: the distinct (function, receiver, form) triples of the live seats equal the triple key's count at the round-7 file that P7 carries, " + tripleCells[0][2] + ", against which the seat-keyed table's rise of " + (SEATS_READ_BY_HAND.length - Number(tripleCells[0][2])) + " is measured; a seat at a new triple moves this number and the sentence with it, so P7 is re-derived rather than a reader editing the cell (the round-7 review's extra6-4)");
  assert.ok(SEATS_READ_BY_HAND.length > triplesLive, "...and the seat key is finer than the triple the round-6 review refused: more entries than distinct triples");
  assert.deepEqual({ unknown: live.unknown, handedOut: live.handedOut, oddCallee: live.oddCallee }, { unknown: [], handedOut: [], oddCallee: [] }, "every method file-view.ts calls is by a name the census lists, no seating method is read without being called, and every callee is a name or a member (the branch's verification pass finding census-1)");
  assert.equal(new Set(live.indexReads.map((i) => i.fn + "|" + i.on)).size, INDEX_READS_BY_HAND.length, "one entry per stored index read (function, receiver): the index table has no duplicate and no site is covered twice");
  for (const e of SEATS_READ_BY_HAND) { const s = live.sites.find((x) => x.fn === e.in && x.on === e.on && x.via === e.via && x.seats === e.seats)!; assert.equal(e.decl, s.decl, "the entry for " + e.in + "/" + e.on + "/" + e.via + " names the binding its seat resolves to (a member chain names none)"); }
  // a listed callee whose parameter the census reads under the body's name: renamed, the census fails until it is read again
  const renamed = census(VIEWER_SRC.replace("\nfunction foldKeeper(body: HTMLElement)", "\nfunction foldKeeper(root: HTMLElement)"));
  assert.deepEqual(renamed.refused.filter((r) => r.startsWith("BODY_HANDED_TO lists foldKeeper")), ["BODY_HANDED_TO lists foldKeeper as reading the body under its own parameter named body, and the source declares no such parameter: read it by hand again"], "the own-parameter claim is held to the source");
  // what still passes: a plain `.` tail on classList, style and dataset, a scalar's own method, a non-seating method read as a value; a bare
  // token as a declaration, a parameter, a property key, a comparison, an argument to a listed callee and as a property of one
  const passes = census(seat('body.classList.add("fileview-mutant"); body.style.height = "0"; body.dataset.probe = "1"; body.scrollTop.toString(); if (typeof body.getClientRects === "function") body.scrollTop += 0;'));
  assert.deepEqual(passes.refused, [], "body.classList.add(...), body.style, body.dataset, a scalar's method, a typeof read of a non-seating method and a compound scroll assignment pass");
  assert.deepEqual([...passes.seated.keys()].sort(), [...before.seated.keys()].sort(), "...and seat no root");
  const bare = census(seat('if (document.activeElement === body || body !== null) foldKeeper(body); readPlace(body, ""); seatPlaceOutcome({ body, place: null } as any); const fold = { key: "k", body: "text", open: true };'));
  assert.deepEqual(bare.refused, [], "a comparison, a listed callee's argument, a property key and a listed callee's shorthand property pass (a parameter named body passes in a listed own callee alone, and a second installFilePrint is a second hand-off of the card and the bar: the author's closing pass over the round-7 build)");
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

// the maintainer's round-8 question (2026-09-21): is the seat table keyed on a receiver's NAME rather than its binding? PR 850's
// census read a synthetic local named `p` as a kernel path, a silent false match. Answered by execution (the round-8 probe: 23
// plants at the round-7 head, 13 refused with the planted line, 10 passed as expected): the entry is addressed by (function
// name, receiver spelling, form, seated arguments) and the receiver is then resolved to its DECLARATION by the language's
// scopes and held to the entry by the declaration's text and a per-function declaration count, so every name collision the
// probe planted refused loud. The plants below keep all 13 of those failures loud, with two of the probe's passing plants
// (b1', c2') and the k4 family, the inward-move road the header states; the m1 to m7 plants execute the round-8 ruling's
// fix, the whole text held at every held text (the 80-character road, closed): the initializer (m1, m1'), the hash form (m2,
// m2'), a loop's head (m3), an unnamed callback's call (m4), a hand-off's argument (m5 an element by shape, m5b a node of the tree) and callee (m6), a hashed argument (m7).
test("the seat table's receiver hold is by binding, not name, executed over functions planted at the end of file-view.ts: a listed name declared in two blocks of the entry's function is refused at both seats, whatever each declaration spells and with its own entry per block; a callback parameter of the name is refused at every seat of the name in the function; a same-named local in ANOTHER function is an unlisted seat there, never read under the listed function's entry, with or without `times`; two functions' entries with their declarations swapped are refused at both seats naming both declarations; one entry over two function nodes sharing a name reds the count; the probe's six other loud plants refuse as it recorded (two blocks spelled alike under `times`, a second block that never seats, a nested named arrow's own declaration unlisted and then wearing the outer text, an unnamed callback's declaration, a nested named function's parameter, a property key); the text hold's stated residue passes (a same-text declaration added inside the nested named function an entry names); two declarations alike through the initializer's 80th character and differing after are refused under one listed text and pass under each whole text, and a text over 300 characters is held by its hash (the maintainer's round-8 ruling of 2026-09-21), the same at every text the census holds an entry to (a loop's head, an unnamed callback's call, a hand-off's argument and callee, a hashed argument); and the header names the shared name the live tables use", () => {
  const plant = (code: string): string => VIEWER_SRC + "\n" + code + "\n";
  const lineIn = (src: string, needle: string): number => { const i = src.indexOf(needle); assert.ok(i >= 0 && src.indexOf(needle, i + 1) < 0, needle + " is planted once"); return src.slice(0, i).split("\n").length; };
  assert.deepEqual(census(VIEWER_SRC).refused, [], "the unplanted file passes, so every refusal below is the plant's");
  const P = (fn: string, decl: string, seats: string, times?: number): SeatRead => ({ in: fn, on: "p", via: "appendChild", seats, is: "a probe's entry for a planted receiver named p", decl, ...(times === undefined ? {} : { times }) });
  const D1 = 'const p = el("div", "fileview-probe-1")', D2 = 'const p = el("div", "fileview-probe-2")', S1 = 'el("span", "fileview-probe-1")', S2 = 'el("span", "fileview-probe-2")';
  // a1: one function, `p` declared in two blocks with different initializers, an entry per block carrying its own declaration
  const a1 = plant('function probeA(): void {\n  { ' + D1 + '; p.appendChild(' + S1 + '); }\n  { ' + D2 + '; p.appendChild(' + S2 + '); }\n}');
  const a1Lines = [lineIn(a1, "{ " + D1), lineIn(a1, "{ " + D2)];
  const ra = census(a1, [...SEATS_READ_BY_HAND, P("probeA", D1, S1), P("probeA", D2, S2)]).refused;
  assert.equal(ra.length, 2, "a1: both seats refused, nothing else: " + JSON.stringify(ra));
  for (const [k, l] of a1Lines.entries()) assert.equal(ra[k], "line " + l + ": p.appendChild(" + (k ? S2 : S1) + ") in probeA: `p` is declared 2 times in probeA (lines " + a1Lines.join(", ") + "): a second declaration of a listed name in the entry's function is refused, whatever it spells", "a1: the seat at line " + l);
  // c1: the second declaration is an unnamed callback's parameter; both entries listed, the inner one as the callback's parameter
  const c1 = plant('function probeC(): void {\n  ' + D1 + '; p.appendChild(' + S1 + ');\n  [p].forEach((p) => { p.appendChild(' + S2 + '); });\n}');
  const c1Lines = [lineIn(c1, D1 + "; p.appendChild"), lineIn(c1, "[p].forEach")];
  const rc = census(c1, [...SEATS_READ_BY_HAND, P("probeC", D1, S1), P("probeC", "a parameter of the callback handed to [p].forEach", S2)]).refused;
  assert.equal(rc.length, 2, "c1: both seats refused, nothing else: " + JSON.stringify(rc));
  for (const [k, l] of c1Lines.entries()) assert.equal(rc[k], "line " + l + ": p.appendChild(" + (k ? S2 : S1) + ") in probeC: `p` is declared 2 times in probeC (lines " + c1Lines.join(", ") + "): a second declaration of a listed name in the entry's function is refused, whatever it spells", "c1: the seat at line " + l);
  // g1, g2: another function declares `p` with the same text and seats the same thing; only probeG1 is listed. The PR-850 shape:
  // the same-named local is never read under probeG1's entry, and a `times: 2` on that entry does not admit it either
  const body1 = "{ " + D1 + "; p.appendChild(" + S1 + "); }";
  const g = plant("function probeG1(): void " + body1 + "\nfunction probeG2(): void " + body1);
  const g2Line = lineIn(g, "function probeG2"), g1Line = lineIn(g, "function probeG1");
  const UNLISTED_G2 = "line " + g2Line + ": p.appendChild(" + S1 + ") seats `" + S1 + "` on `p` by appendChild in probeG2, a seat the census has not read by hand: read the site for what p is (the body under another name, or a node whose seat lands as a child of the body, seats a root the lists must know) and what it seats, and list the seat in SEATS_READ_BY_HAND with the receiver's declaration";
  const rg1 = census(g, [...SEATS_READ_BY_HAND, P("probeG1", D1, S1)]).refused;
  assert.equal(rg1.length, 1, "g1: the other function's seat is unlisted, and probeG1's passes: " + JSON.stringify(rg1));
  assert.ok(rg1[0].startsWith(UNLISTED_G2.slice(0, UNLISTED_G2.indexOf(": read the site"))), "g1: refused as probeG2's unlisted seat: " + rg1[0]);
  const rg2 = census(g, [...SEATS_READ_BY_HAND, P("probeG1", D1, S1, 2)]).refused;
  assert.equal(rg2.length, 2, "g2: `times: 2` on probeG1's entry admits nothing in probeG2: " + JSON.stringify(rg2));
  assert.ok(rg2[0].startsWith(UNLISTED_G2.slice(0, UNLISTED_G2.indexOf(": read the site"))), "g2: probeG2's seat stays unlisted: " + rg2[0]);
  assert.equal(rg2[1], "SEATS_READ_BY_HAND's entry `p.appendChild` seating `" + S1 + "` in probeG1 matches 1 seats (lines " + g1Line + ") where it reads 2: one entry is one seat, read by hand where it stands; a seat spelled alike in two branches says `times` and is read at each", "g2: and probeG1's entry reds its count");
  // f2: two functions each declaring `p` with its own initializer, the two entries carrying each other's declaration
  const f = plant("function probeF1(): void { " + D1 + "; p.appendChild(" + S1 + "); }\nfunction probeF2(): void { " + D2 + "; p.appendChild(" + S1 + "); }");
  const rf = census(f, [...SEATS_READ_BY_HAND, P("probeF1", D2, S1), P("probeF2", D1, S1)]).refused;
  assert.deepEqual(rf, [
    "line " + lineIn(f, "function probeF1") + ": p.appendChild(" + S1 + ") seats on `p` in probeF1, bound to `" + D1 + "`, where SEATS_READ_BY_HAND read `" + D2 + "`: the receiver is not the one read by hand",
    "line " + lineIn(f, "function probeF2") + ": p.appendChild(" + S1 + ") seats on `p` in probeF2, bound to `" + D2 + "`, where SEATS_READ_BY_HAND read `" + D1 + "`: the receiver is not the one read by hand",
  ], "f2: both seats refused, each naming the declaration it resolved to and the one read by hand");
  // h1: two nested arrows both named `inner`, in two functions, same declaration text and seat; one entry `in: "inner"`. The
  // `in` is a bare function name two nodes can share, so the seats collapse to one key, and the count reds it
  const innerFn = "const inner = () => { " + D1 + "; p.appendChild(" + S1 + "); }; inner();";
  const h = plant("function probeH1(): void { " + innerFn + " }\nfunction probeH2(): void { " + innerFn + " }");
  const rh = census(h, [...SEATS_READ_BY_HAND, P("inner", D1, S1)]).refused;
  assert.deepEqual(rh, ["SEATS_READ_BY_HAND's entry `p.appendChild` seating `" + S1 + "` in inner matches 2 seats (lines " + lineIn(h, "function probeH1") + ", " + lineIn(h, "function probeH2") + ") where it reads 1: one entry is one seat, read by hand where it stands; a seat spelled alike in two branches says `times` and is read at each"], "h1: one entry over two function nodes named alike reds the count");
  // a2: the two blocks spelled alike, declaration and seat, one entry `times: 2`: `times` admits no second declaration
  const a2 = plant('function probeA2(): void {\n  { ' + D1 + '; p.appendChild(' + S1 + '); }\n  { ' + D1 + '; p.appendChild(' + S1 + '); }\n}');
  const a2Lines = [lineIn(a2, "function probeA2") + 1, lineIn(a2, "function probeA2") + 2];
  assert.deepEqual(census(a2, [...SEATS_READ_BY_HAND, P("probeA2", D1, S1, 2)]).refused, a2Lines.map((l) => "line " + l + ": p.appendChild(" + S1 + ") in probeA2: `p` is declared 2 times in probeA2 (lines " + a2Lines.join(", ") + "): a second declaration of a listed name in the entry's function is refused, whatever it spells"), "a2: both seats refused under the declaration count, `times` admitting neither");
  // a3: the second block declares `p` and never seats it; the first block's entry alone is listed, and its seat is refused
  const a3 = plant('function probeA3(): void {\n  { ' + D1 + '; p.appendChild(' + S1 + '); }\n  { ' + D2 + '; }\n}');
  const a3Line = lineIn(a3, "function probeA3") + 1;
  assert.deepEqual(census(a3, [...SEATS_READ_BY_HAND, P("probeA3", D1, S1)]).refused, ["line " + a3Line + ": p.appendChild(" + S1 + ") in probeA3: `p` is declared 2 times in probeA3 (lines " + a3Line + ", " + (a3Line + 1) + "): a second declaration of a listed name in the entry's function is refused, whatever it spells"], "a3: a second declaration that never seats still refuses the listed seat");
  // b1: `p` declared again, with another initializer, in a nested NAMED arrow `inner` that seats it. The nested function is
  // another entry's `in`: its seat is unlisted under the outer entry (b1), passes listed with its own declaration (b1'), and
  // listed with the OUTER declaration's text is refused naming both (b1'')
  const b1 = plant('function probeB1(): void {\n  ' + D1 + '; p.appendChild(' + S1 + ');\n  const inner = () => { ' + D2 + '; p.appendChild(' + S2 + '); }; inner();\n}');
  const b1Line = lineIn(b1, "function probeB1") + 2;
  const rb1 = census(b1, [...SEATS_READ_BY_HAND, P("probeB1", D1, S1)]).refused;
  assert.equal(rb1.length, 1, "b1: the nested function's seat alone is refused: " + JSON.stringify(rb1));
  assert.ok(rb1[0].startsWith("line " + b1Line + ": p.appendChild(" + S2 + ") seats `" + S2 + "` on `p` by appendChild in inner, a seat the census has not read by hand"), "b1: refused as inner's unlisted seat: " + rb1[0]);
  assert.deepEqual(census(b1, [...SEATS_READ_BY_HAND, P("probeB1", D1, S1), P("inner", D2, S2)]).refused, [], "b1': listed under inner with inner's declaration, both seats pass");
  assert.deepEqual(census(b1, [...SEATS_READ_BY_HAND, P("probeB1", D1, S1), P("inner", D1, S2)]).refused, ["line " + b1Line + ": p.appendChild(" + S2 + ") seats on `p` in inner, bound to `" + D2 + "`, where SEATS_READ_BY_HAND read `" + D1 + "`: the receiver is not the one read by hand"], "b1'': inner's entry wearing the outer declaration's text is refused, naming the declaration the seat resolved to");
  // b2: the second declaration is inside an UNNAMED callback, both entries listed: the callback is the function's own, so the
  // name is declared twice in probeB2 and both seats are refused
  const b2 = plant('function probeB2(): void {\n  ' + D1 + '; p.appendChild(' + S1 + ');\n  [1].forEach(() => { ' + D2 + '; p.appendChild(' + S2 + '); });\n}');
  const b2Lines = [lineIn(b2, "function probeB2") + 1, lineIn(b2, "function probeB2") + 2];
  assert.deepEqual(census(b2, [...SEATS_READ_BY_HAND, P("probeB2", D1, S1), P("probeB2", D2, S2)]).refused, b2Lines.map((l, k) => "line " + l + ": p.appendChild(" + (k ? S2 : S1) + ") in probeB2: `p` is declared 2 times in probeB2 (lines " + b2Lines.join(", ") + "): a second declaration of a listed name in the entry's function is refused, whatever it spells"), "b2: both seats refused under the declaration count, the unnamed callback's declaration counted in probeB2");
  // c2: a nested NAMED function's parameter named `p`: its seat is unlisted under the outer entry (c2) and passes listed as the
  // parameter of innerC (c2')
  const c2 = plant('function probeC2(): void {\n  ' + D1 + '; p.appendChild(' + S1 + ');\n  const innerC = (p: HTMLElement): void => { p.appendChild(' + S2 + '); }; innerC(p);\n}');
  const rc2 = census(c2, [...SEATS_READ_BY_HAND, P("probeC2", D1, S1)]).refused;
  assert.equal(rc2.length, 1, "c2: innerC's seat alone is refused: " + JSON.stringify(rc2));
  assert.ok(rc2[0].startsWith("line " + (lineIn(c2, "function probeC2") + 2) + ": p.appendChild(" + S2 + ") seats `" + S2 + "` on `p` by appendChild in innerC, a seat the census has not read by hand"), "c2: refused as innerC's unlisted seat: " + rc2[0]);
  assert.deepEqual(census(c2, [...SEATS_READ_BY_HAND, P("probeC2", D1, S1), P("innerC", "a parameter of innerC", S2)]).refused, [], "c2': listed as innerC's parameter, both seats pass");
  // e1: a property key named `p` (`const q = { p: el(...) }`) is no declaration of `p`: the bare seat passes, and `q.p`'s seat
  // is refused as its own unlisted seat on the member chain
  const e1 = plant('function probeE(): void {\n  ' + D1 + '; p.appendChild(' + S1 + ');\n  const q = { p: el("div", "fileview-probe-2") }; q.p.appendChild(' + S2 + ');\n}');
  const re1 = census(e1, [...SEATS_READ_BY_HAND, P("probeE", D1, S1)]).refused;
  assert.equal(re1.length, 1, "e1: the `q.p` seat alone is refused: " + JSON.stringify(re1));
  assert.ok(re1[0].startsWith("line " + (lineIn(e1, "function probeE") + 2) + ": q.p.appendChild(" + S2 + ") seats `" + S2 + "` on `q.p` by appendChild in probeE, a seat the census has not read by hand"), "e1: refused as the member chain's unlisted seat, the bare `p` seat passing: " + re1[0]);
  // the text hold's inward-move road, stated in the header (the round-8 verifier's k4 family): an entry naming a nested named arrow
  // whose `p` is the ENCLOSING function's declaration passes (k4) and stays green when the arrow gains a same-text declaration
  // of its own (k4'), the binding moving inward under the same reported text; another text inside is refused naming both (k4'')
  const k4 = (inner: string): string => plant('function probeK4(): void {\n  ' + D1 + ';\n  const inner4 = () => { ' + inner + 'p.appendChild(' + S1 + '); }; inner4();\n}');
  assert.deepEqual(census(k4(""), [...SEATS_READ_BY_HAND, P("inner4", D1, S1)]).refused, [], "k4: the enclosing function's declaration read through the nested named arrow passes");
  assert.deepEqual(census(k4(D1 + "; "), [...SEATS_READ_BY_HAND, P("inner4", D1, S1)]).refused, [], "k4': a same-text declaration added inside inner4 passes under the listed text, the residue the header states");
  assert.deepEqual(census(k4(D2 + "; "), [...SEATS_READ_BY_HAND, P("inner4", D1, S1)]).refused, ["line " + (lineIn(k4(D2 + "; "), "function probeK4") + 2) + ": p.appendChild(" + S1 + ") seats on `p` in inner4, bound to `" + D2 + "`, where SEATS_READ_BY_HAND read `" + D1 + "`: the receiver is not the one read by hand"], "k4'': another text inside inner4 is refused naming both declarations");
  // the 80-character road, closed (the maintainer's round-8 ruling of 2026-09-21): two declarations alike through the initializer's
  // 80th character and differing after, listed under one text cut at 80 (what the hold read before the ruling), are refused at
  // both seats naming each whole declaration (m1); listed under their whole texts they pass (m1'); a text over 300 characters is
  // held as its first 80 characters beside the sha256 of the whole, so two such declarations alike through the 80th are two
  // holds, the sibling refused naming both hashed forms, and each passes under its own (m2)
  const cut = (decl: string, n: number): string => decl.slice(0, "const p = ".length + n);
  const L1 = 'const p = el("div", "fileview-probe-' + "x".repeat(60) + '-1")', L2 = 'const p = el("div", "fileview-probe-' + "x".repeat(60) + '-2")';
  const T = cut(L1, 80);
  assert.ok(L1 !== L2 && cut(L2, 80) === T && L1.length - "const p = ".length <= 300, "L1 and L2 are alike through the initializer's 80th character, differ after, and stay under the hash line");
  const m1 = plant('function probeL1(): void {\n  ' + L1 + '; p.appendChild(' + S1 + ');\n}\nfunction probeL2(): void {\n  ' + L2 + '; p.appendChild(' + S2 + ');\n}');
  assert.deepEqual(census(m1, [...SEATS_READ_BY_HAND, P("probeL1", T, S1), P("probeL2", T, S2)]).refused, [
    "line " + (lineIn(m1, "function probeL1") + 1) + ": p.appendChild(" + S1 + ") seats on `p` in probeL1, bound to `" + L1 + "`, where SEATS_READ_BY_HAND read `" + T + "`: the receiver is not the one read by hand",
    "line " + (lineIn(m1, "function probeL2") + 1) + ": p.appendChild(" + S2 + ") seats on `p` in probeL2, bound to `" + L2 + "`, where SEATS_READ_BY_HAND read `" + T + "`: the receiver is not the one read by hand",
  ], "m1: two declarations alike through the 80th character, listed under the text cut there, are refused at both seats naming each whole declaration");
  assert.deepEqual(census(m1, [...SEATS_READ_BY_HAND, P("probeL1", L1, S1), P("probeL2", L2, S2)]).refused, [], "m1': listed under their whole texts, both seats pass");
  const H1 = 'const p = el("div", "fileview-probe-' + "x".repeat(300) + '-1")', H2 = 'const p = el("div", "fileview-probe-' + "x".repeat(300) + '-2")';
  const hashed = (decl: string): string => cut(decl, 80) + " ... sha256:" + crypto.createHash("sha256").update(decl.slice("const p = ".length)).digest("hex");
  assert.ok(cut(H1, 80) === cut(H2, 80) && hashed(H1) !== hashed(H2) && /^const p = .{80} \.\.\. sha256:[0-9a-f]{64}$/.test(hashed(H1)), "H1 and H2 are alike through the 80th character and their hashed forms differ in the hash alone");
  const m2 = plant('function probeH1(): void {\n  ' + H1 + '; p.appendChild(' + S1 + ');\n}\nfunction probeH2(): void {\n  ' + H2 + '; p.appendChild(' + S2 + ');\n}');
  assert.deepEqual(census(m2, [...SEATS_READ_BY_HAND, P("probeH1", hashed(H1), S1), P("probeH2", hashed(H1), S2)]).refused, ["line " + (lineIn(m2, "function probeH2") + 1) + ": p.appendChild(" + S2 + ") seats on `p` in probeH2, bound to `" + hashed(H2) + "`, where SEATS_READ_BY_HAND read `" + hashed(H1) + "`: the receiver is not the one read by hand"], "m2: over 300 characters, the sibling listed under the other's hashed form is refused naming both hashed forms");
  assert.deepEqual(census(m2, [...SEATS_READ_BY_HAND, P("probeH1", hashed(H1), S1), P("probeH2", hashed(H2), S2)]).refused, [], "m2': each listed under its own hashed form, both seats pass");
  // the other five held texts (the author's closing pass over round 8, the fold's verifiers' mechanism-1 and records-1: the
  // fix reached all six sites and the plants above executed the initializer's alone, so cutting the other five back stayed
  // green). Each plant below is two texts alike through the 80th character and differing after: listed under the text cut at
  // 80, refused naming each whole text; listed under each whole text, passing.
  const cut80 = (s: string): string => s.slice(0, 80);
  const alike = (a: string, b: string): boolean => a !== b && a.length > 80 && cut80(a) === cut80(b);
  const NOT_READ = (fn: string, S: string, whole: string, listed: string): string => "p.appendChild(" + S + ") seats on `p` in " + fn + ", bound to `" + whole + "`, where SEATS_READ_BY_HAND read `" + listed + "`: the receiver is not the one read by hand";
  // m3: a loop's head, for-of and for-in
  const O1 = '[el("div", "fileview-probe-' + "x".repeat(60) + '-1")]', O2 = '[el("div", "fileview-probe-' + "x".repeat(60) + '-2")]';
  const I1 = '{ "fileview-probe-' + "x".repeat(70) + '-1": 0 }', I2 = '{ "fileview-probe-' + "x".repeat(70) + '-2": 0 }';
  assert.ok(alike(O1, O2) && alike(I1, I2), "the for-of heads and the for-in heads are alike through the 80th character and differ after");
  const m3 = plant('function probeO1(): void {\n  for (const p of ' + O1 + ') p.appendChild(' + S1 + ');\n}\nfunction probeO2(): void {\n  for (const p of ' + O2 + ') p.appendChild(' + S2 + ');\n}\nfunction probeI1(): void {\n  for (const p in ' + I1 + ') p.appendChild(' + S1 + ');\n}\nfunction probeI2(): void {\n  for (const p in ' + I2 + ') p.appendChild(' + S2 + ');\n}');
  const m3Line = (fn: string): number => lineIn(m3, "function " + fn) + 1;
  assert.deepEqual(census(m3, [...SEATS_READ_BY_HAND, P("probeO1", "const p of " + cut80(O1), S1), P("probeO2", "const p of " + cut80(O1), S2), P("probeI1", "const p in " + cut80(I1), S1), P("probeI2", "const p in " + cut80(I1), S2)]).refused, [
    "line " + m3Line("probeO1") + ": " + NOT_READ("probeO1", S1, "const p of " + O1, "const p of " + cut80(O1)),
    "line " + m3Line("probeO2") + ": " + NOT_READ("probeO2", S2, "const p of " + O2, "const p of " + cut80(O1)),
    "line " + m3Line("probeI1") + ": " + NOT_READ("probeI1", S1, "const p in " + I1, "const p in " + cut80(I1)),
    "line " + m3Line("probeI2") + ": " + NOT_READ("probeI2", S2, "const p in " + I2, "const p in " + cut80(I1)),
  ], "m3: loop heads alike through the 80th character, listed under the head cut there, are refused at all four seats naming each whole head");
  assert.deepEqual(census(m3, [...SEATS_READ_BY_HAND, P("probeO1", "const p of " + O1, S1), P("probeO2", "const p of " + O2, S2), P("probeI1", "const p in " + I1, S1), P("probeI2", "const p in " + I2, S2)]).refused, [], "m3': listed under their whole heads, all four seats pass");
  // m4: an unnamed callback's call, the text its parameter is described by
  const C1 = '[el("div", "fileview-probe-' + "x".repeat(60) + '-1")].forEach', C2 = '[el("div", "fileview-probe-' + "x".repeat(60) + '-2")].forEach';
  assert.ok(alike(C1, C2), "the two calls are alike through the 80th character and differ after");
  const m4 = plant('function probeU1(): void {\n  ' + C1 + '((p) => { p.appendChild(' + S1 + '); });\n}\nfunction probeU2(): void {\n  ' + C2 + '((p) => { p.appendChild(' + S2 + '); });\n}');
  const cb = (call: string): string => "a parameter of the callback handed to " + call;
  assert.deepEqual(census(m4, [...SEATS_READ_BY_HAND, P("probeU1", cb(cut80(C1)), S1), P("probeU2", cb(cut80(C1)), S2)]).refused, [
    "line " + (lineIn(m4, "function probeU1") + 1) + ": " + NOT_READ("probeU1", S1, cb(C1), cb(cut80(C1))),
    "line " + (lineIn(m4, "function probeU2") + 1) + ": " + NOT_READ("probeU2", S2, cb(C2), cb(cut80(C1))),
  ], "m4: two unnamed callbacks' parameters, the calls alike through the 80th character, listed under the call cut there, are refused at both seats naming each whole call");
  assert.deepEqual(census(m4, [...SEATS_READ_BY_HAND, P("probeU1", cb(C1), S1), P("probeU2", cb(C2), S2)]).refused, [], "m4': listed under the whole calls, both seats pass");
  // m5: a hand-off's argument (the argument axis's `arg`), an element by shape handed to an import (flash), twice in one function
  const A = (fn: string, to: string, arg: string, times?: number): ArgRead => ({ in: fn, to, arg, is: "a probe's entry for a planted hand-off", ...(times === undefined ? {} : { times }) });
  const UNLISTED_HANDOFF = (line: number, call: string, arg: string, to: string, fn: string): string => "line " + line + ": " + call.slice(0, 100) + " hands `" + arg + "`, el(...), to " + to + "(...) in " + fn + ", a callee this file does not declare and the census has not read by hand for what it does with an element it is handed (it could seat the element in the body, or seat into it, where the census cannot follow): read it and list the site in ARGS_READ_BY_HAND";
  const STALE_HANDOFF = (arg: string, to: string, fn: string): string => "ARGS_READ_BY_HAND lists `" + arg + "` handed to " + to + " in " + fn + ", and the source has no such hand-off: the entry is stale, remove it or read the site again";
  const E1 = 'el("div", "fileview-probe-' + "x".repeat(70) + '-1")', E2 = 'el("div", "fileview-probe-' + "x".repeat(70) + '-2")';
  assert.ok(alike(E1, E2) && E1.length <= 300, "the two arguments are alike through the 80th character, differ after, and stay under the hash line");
  const m5 = plant('function probeM5(): void {\n  flash(' + E1 + ');\n  flash(' + E2 + ');\n}');
  const m5Line = lineIn(m5, "function probeM5");
  assert.deepEqual(census(m5, SEATS_READ_BY_HAND, INDEX_READS_BY_HAND, [...ARGS_READ_BY_HAND, A("probeM5", "flash", cut80(E1), 2)]).refused, [
    STALE_HANDOFF(cut80(E1), "flash", "probeM5"),
    UNLISTED_HANDOFF(m5Line + 1, "flash(" + E1 + ")", E1, "flash", "probeM5"),
    UNLISTED_HANDOFF(m5Line + 2, "flash(" + E2 + ")", E2, "flash", "probeM5"),
  ], "m5: two hand-offs alike through the argument's 80th character, listed as one entry under the argument cut there with `times: 2`, are three refusals: the cut entry stale, and each hand-off unlisted naming its whole argument");
  assert.deepEqual(census(m5, SEATS_READ_BY_HAND, INDEX_READS_BY_HAND, [...ARGS_READ_BY_HAND, A("probeM5", "flash", E1), A("probeM5", "flash", E2)]).refused, [], "m5': listed under each whole argument, both hand-offs pass");
  // m5b: the same over the argument axis's other push, a node of the tree (a NODE_MEMBERS chain) handed to a callee
  const N1 = E1 + ".parentElement", N2 = E2 + ".parentElement";
  const UNLISTED_NODE = (line: number, call: string, arg: string, to: string, fn: string): string => "line " + line + ": " + call.slice(0, 100) + " hands `" + arg + "`, a node of the tree read through parentElement, to " + to + "(...) in " + fn + ", a callee the census has not read by hand for what it does with a node it is handed (it could seat the node in the body, or seat into it, where the census cannot follow): read it and list the site in ARGS_READ_BY_HAND, or read the node inside a call the census reads";
  const m5b = plant('function probeN5(): void {\n  flash(' + N1 + ');\n  flash(' + N2 + ');\n}');
  const m5bLine = lineIn(m5b, "function probeN5");
  assert.deepEqual(census(m5b, SEATS_READ_BY_HAND, INDEX_READS_BY_HAND, [...ARGS_READ_BY_HAND, A("probeN5", "flash", cut80(N1), 2)]).refused, [
    UNLISTED_NODE(m5bLine + 1, "flash(" + N1 + ")", N1, "flash", "probeN5"),
    UNLISTED_NODE(m5bLine + 2, "flash(" + N2 + ")", N2, "flash", "probeN5"),
    STALE_HANDOFF(cut80(N1), "flash", "probeN5"),
  ], "m5b: two nodes of the tree handed under one entry cut at the argument's 80th character are three refusals: each hand-off unlisted naming its whole argument, and the cut entry stale");
  assert.deepEqual(census(m5b, SEATS_READ_BY_HAND, INDEX_READS_BY_HAND, [...ARGS_READ_BY_HAND, A("probeN5", "flash", N1), A("probeN5", "flash", N2)]).refused, [], "m5b': listed under each whole argument, both pass");
  // m6: a hand-off's callee (`to`), two bare names this file does not declare, alike through the 80th character
  const K1 = "probeCallee" + "x".repeat(70) + "1", K2 = "probeCallee" + "x".repeat(70) + "2";
  assert.ok(alike(K1, K2), "the two callees are alike through the 80th character and differ after");
  const m6 = plant('function probeM6(): void {\n  ' + K1 + '(' + S1 + ');\n  ' + K2 + '(' + S1 + ');\n}');
  const m6Line = lineIn(m6, "function probeM6");
  assert.deepEqual(census(m6, SEATS_READ_BY_HAND, INDEX_READS_BY_HAND, [...ARGS_READ_BY_HAND, A("probeM6", cut80(K1), S1, 2)]).refused, [
    STALE_HANDOFF(S1, cut80(K1), "probeM6"),
    UNLISTED_HANDOFF(m6Line + 1, K1 + "(" + S1 + ")", S1, K1, "probeM6"),
    UNLISTED_HANDOFF(m6Line + 2, K2 + "(" + S1 + ")", S1, K2, "probeM6"),
  ], "m6: two callees alike through the 80th character handed the same element, listed as one entry under the callee cut there, are three refusals: the cut entry stale, and each hand-off unlisted naming its whole callee");
  assert.deepEqual(census(m6, SEATS_READ_BY_HAND, INDEX_READS_BY_HAND, [...ARGS_READ_BY_HAND, A("probeM6", K1, S1), A("probeM6", K2, S1)]).refused, [], "m6': listed under each whole callee, both hand-offs pass");
  // m7: an argument over 300 characters, held as its first 80 characters beside the sha256 of the whole
  const G1 = 'el("div", "fileview-probe-' + "x".repeat(300) + '-1")', G2 = 'el("div", "fileview-probe-' + "x".repeat(300) + '-2")';
  const hashedArg = (a: string): string => cut80(a) + " ... sha256:" + crypto.createHash("sha256").update(a).digest("hex");
  assert.ok(alike(G1, G2) && G1.length > 300 && hashedArg(G1) !== hashedArg(G2), "the two arguments are over 300 characters, alike through the 80th, and their hashed forms differ in the hash alone");
  const m7 = plant('function probeM7(): void {\n  flash(' + G1 + ');\n}');
  assert.deepEqual(census(m7, SEATS_READ_BY_HAND, INDEX_READS_BY_HAND, [...ARGS_READ_BY_HAND, A("probeM7", "flash", hashedArg(G1))]).refused, [], "m7: an argument over 300 characters passes under its own hashed form");
  assert.deepEqual(census(m7, SEATS_READ_BY_HAND, INDEX_READS_BY_HAND, [...ARGS_READ_BY_HAND, A("probeM7", "flash", hashedArg(G2))]).refused, [
    STALE_HANDOFF(hashedArg(G2), "flash", "probeM7"),
    UNLISTED_HANDOFF(lineIn(m7, "function probeM7") + 1, "flash(" + G1 + ")", hashedArg(G1), "flash", "probeM7"),
  ], "m7': listed under the sibling's hashed form, it is refused naming both hashed forms (the sibling's entry stale, its own hand-off unlisted)");
  // the live file: the names the three tables use that more than one function node bears, and the header's example among them
  const sf = ts.createSourceFile("file-view.ts", VIEWER_SRC, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
  const nodesNamed = new Map<string, number>();
  const nameOf = (f: ts.Node): string | null => ts.isFunctionDeclaration(f) && f.name ? f.name.text : (ts.isArrowFunction(f) || ts.isFunctionExpression(f)) && (ts.isVariableDeclaration(f.parent) || ts.isPropertyAssignment(f.parent)) && ts.isIdentifier(f.parent.name) ? f.parent.name.text : ts.isMethodDeclaration(f) && ts.isIdentifier(f.name) ? f.name.text : null;
  const walk = (n: ts.Node): void => { const name = nameOf(n); if (name) nodesNamed.set(name, (nodesNamed.get(name) ?? 0) + 1); ts.forEachChild(n, walk); };
  walk(sf);
  const used = new Set([...SEATS_READ_BY_HAND, ...ARGS_READ_BY_HAND, ...URL_WRITES_READ_BY_HAND].map((e) => e.in));
  const shared = [...nodesNamed].filter(([name, n]) => n > 1 && used.has(name)).map(([name]) => name).sort();
  assert.ok(shared.includes("apply"), "`apply` names more than one function node in file-view.ts and the tables use it (the shared names today: " + JSON.stringify(shared) + ")");
  const whole = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "file-print.test.ts"), "utf8");
  const [h0, h1] = [whole.indexOf("// bodyReady classes a child it has never seen as UNKNOWN"), whole.indexOf("/** file-view.ts with its comments blanked")];   // the header block alone, as the record test reads it: a pin over the whole module is satisfied by its own literals (the round-8 fold's mutation found the old read so)
  assert.ok(h0 >= 0 && h1 > h0, "the census header block is found between its two markers");
  const header = whole.slice(h0, h1).replace(/\n\/\/ /g, " ");
  assert.ok(header.includes("THE RECEIVER'S HOLD IS BY BINDING, NOT NAME") && header.includes("`apply` is such a name in file-view.ts, textSizeControl's inner arrow and githubLinkAction's method") && header.includes("the plants k4 and k4' below pass, k4'' with another text inside refuses naming both") && header.includes("a text over 300 characters is held as its first 80 characters beside the sha256 of the whole flattened text, the text as the census reads it with comments blanked and whitespace collapsed to single spaces") && header.includes("openFileView's `ctx` initializer the one such text in the tables today") && header.includes("the plants m1 to m7 below execute, at every held text, the refusal under a text cut at 80 and the pass under each whole text"), "the census header states the binding hold, its two text-keyed residues with the k4 plants by id, the hash form over the flattened text, and the closed 80-character road with its plants at every held text");
  const P7 = sectionPart("P7. **", "**Derivations and their unknown cases.**");
  assert.ok(P7.includes("the receiver's hold is by binding, not name (the maintainer's round-8 question, 2026-09-21") && P7.includes("two things stay keyed on text and are stated in the census header, the entry's `in`, a bare function name two function nodes can share") && P7.includes("the census module's plants k4 and k4' pass, k4'' refuses") && P7.includes("holds the whole text (one over 300 characters as its first 80 characters beside the sha256 of the whole flattened text, comments blanked and whitespace collapsed as the census reads it), the plants m1 to m7 executing it at every held text"), "P7 states the answer, the two roads with the k4 plants by id, and the closed 80-character road with its fix at every held text");
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

// ── the print record's pins that need the compiler ────────────────────────────────────────────────────────────────────────
// tools/markdown-viewer-plan-print-record.test.mjs holds the plan's print follow-on (plans/markdown-viewer.md, "## Follow-on:
// Print (2026-09-19)") to the tree. It runs in CI's shell job (`node --test tools/*.test.mjs` from the repo root) with no
// node_modules, so it reaches no compiler: a `require("typescript")` there failed the job at load (2026-09-21). The three
// derivations that need one run here, under npm test, and the record test holds the same sentences by text, each of its
// messages naming this module as where the equality is checked by execution: P7's table sizes against the tables this module
// runs (and the record test's text count of their array literals against the same tables), the figure leg's table built from
// `shapes()` for the shape count, the two-URL count and the per-engine list, and the post-filter-index census by syntax over
// the print test modules. The plan is read from the repo root the way file-view.ts is above.

const REPO_ROOT = path.resolve(process.cwd(), "..");
const readRepo = (...parts: string[]): string => fs.readFileSync(path.join(REPO_ROOT, ...parts), "utf8");
/** The print follow-on section of `plan`, from its head to the next `## ` heading or the plan's end (the round-6 review's
 *  cluster F, which the round-7 review's extra5-2 found undone here: the slice ran to the plan's end, and every consumer
 *  below ends at an in-section mark, so nothing shipped reached the tail, but a section appended after this one would have
 *  been in the text every mark was sought in), its hard wraps collapsed so a pin survives a rewrap. */
function printSectionOf(plan: string): string {
  const head = "## Follow-on: Print (2026-09-19)";
  const at = plan.indexOf("\n" + head + "\n");
  assert.ok(at >= 0, "the follow-on section is in the plan");
  const next = plan.indexOf("\n## ", at + 1);
  return plan.slice(at, next >= 0 ? next : plan.length).replace(/\s+/g, " ");
}
/** The plan's section, read on first use so a missing section fails the pin that needs it and not the module's load. */
let printSectionText: string | null = null;
function printSection(): string {
  if (printSectionText === null) printSectionText = printSectionOf(readRepo("plans", "markdown-viewer.md"));
  return printSectionText;
}
test("the plan section this module reads ends at the next `## ` heading (the round-6 review's cluster F; the round-7 review's extra5-2): a decoy section appended after the Print head is outside the text every mark below is sought in, which reads the same with and without it (FAILS BEFORE: the slice ran to the plan's end and held the decoy)", () => {
  const plan = readRepo("plans", "markdown-viewer.md");
  const decoy = "\n## Decoy follow-on (this case's own synthetic section)\n\nA decoy sentence after the next heading: this text names a retired name for an axis, and 7 gated shapes stand here.\n";
  assert.equal(printSectionOf(plan + decoy), printSectionOf(plan), "the section is the same text with a section appended after it");
  assert.ok(!printSectionOf(plan + decoy).includes("decoy sentence after the next heading"), "the decoy is outside it");
  assert.ok((plan + decoy).replace(/\s+/g, " ").includes("decoy sentence after the next heading"), "...where an unbounded read holds it: the bound is load-bearing");
});
/** `text` from `start` up to the `end` that follows it; a missing mark fails, which is the failure wanted. */
function sectionBetween(text: string, start: string, end: string): string {
  const a = text.indexOf(start);
  assert.ok(a >= 0, JSON.stringify(start) + " is in the text");
  const b = text.indexOf(end, a + start.length);
  assert.ok(b > a, JSON.stringify(end) + " follows it");
  return text.slice(a, b);
}
const sectionPart = (from: string, to: string): string => sectionBetween(printSection(), from, to);
const COUNT_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve"];
const ORDINAL_WORDS = ["", "first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth", "eleventh", "twelfth"];
const tableTimes = (rows: ReadonlyArray<{ times?: number }>): number => rows.reduce((n, e) => n + (e.times ?? 1), 0);

test("P7's derived numbers are the tables this module runs: the seat-keyed table's entries, seats, entries reading two seats and the rise over the round-7 triple count, the PR's own seats and entries over the merge-base cell, the argument axis's sites, hand-offs, entries reading two hand-offs and URL writes, and the setAttribute writes the URL table lists, each read from the sentence in plans/markdown-viewer.md and held to the table by execution; and the record test's text count over this file's array literals, which is what CI's shell job holds the sentences by, counts the same tables", () => {
  const P7 = sectionPart("P7. **", "**Derivations and their unknown cases.**");
  const entries = SEATS_READ_BY_HAND.length, seats = tableTimes(SEATS_READ_BY_HAND);
  const live = seatSites(VIEWER_SRC);
  // the triple-key cells and the merge-base cell are the round-7 pre-answers' run, literals the sentence carries once; the rise
  // and the PR's own contribution are computed from those cells and the live table, so no cell is carried here a second time
  const triples = [...P7.matchAll(/the triple key gives (\d+) at the round-6 file and (\d+) at the round-7 file/g)];
  assert.equal(triples.length, 1, "the triple-key cells stand in P7 once");
  const tripleAtRound7 = Number(triples[0][2]);
  assert.equal(triples[0][1], triples[0][2], "the two triple cells are equal, so the rise across the change of key is the key's alone, as the sentence says (" + triples[0][1] + " at the round-6 file, " + triples[0][2] + " at the round-7 file)");
  const seatSentence = [...P7.matchAll(/the seat key gives (\d+) entries over (\d+) seats at both, (\w+) entries standing for two byte-identical seats each \(((?:[^()]|\([^()]*\))*)\), each read at both seats, which is why the seats exceed the entries by (\w+), so the rise of (\d+) entries is what the triple hid and the site population, (\d+), moves in neither file's cell/g)];
  assert.equal(seatSentence.length, 1, "the seat-keyed table's size stands in P7 once");
  const twice = SEATS_READ_BY_HAND.filter((e) => e.times !== undefined);
  assert.ok(twice.length > 0 && twice.every((e) => e.times === 2), "every entry with a `times` reads two seats (" + JSON.stringify(twice.map((e) => e.times)) + "), the sentence's two byte-identical seats each");
  const [, sEntries, sSeats, sTwice, sNamed, sExcess, sRise, sPopulation] = seatSentence[0];
  assert.deepEqual([sEntries, sSeats, sTwice, sExcess, sRise, sPopulation], [String(entries), String(seats), COUNT_WORDS[twice.length], COUNT_WORDS[seats - entries], String(entries - tripleAtRound7), String(seats)], "P7's entries, seats, entries reading two seats, the seats' excess over the entries (why 92 exceeds 90: the `times` entries, each read at two seats), rise and site population are the table's (" + entries + " over " + seats + ", " + twice.length + " reading two, an excess of " + (seats - entries) + ", a rise of " + (entries - tripleAtRound7) + " over the round-7 triple count)");
  assert.equal(live.sites.filter((x) => !x.body).length, seats, "the site population the sentence names is the live non-body seats, which the entries' `times` sum to");
  for (const e of twice) {
    assert.ok(sNamed.includes(e.in + "'s") && sNamed.includes("`" + e.on + "." + e.via + "(" + e.seats + ")`"), "the sentence names the entry reading two seats, " + e.in + "'s `" + e.on + "." + e.via + "(" + e.seats + ")`: " + sNamed);
    const texts = live.sites.filter((x) => !x.body && x.fn === e.in && x.on === e.on && x.via === e.via && x.seats === e.seats).map((x) => x.whole);   // the whole flattened call text, never the message's 100-character cut (the fold's verifiers' records-2)
    assert.equal(texts.length, 2, "the entry reads two live seats: " + JSON.stringify(texts)); assert.equal(new Set(texts).size, 1, "and the two are byte-identical calls, whole: " + JSON.stringify(texts));
  }
  const base = [...P7.matchAll(/gives (\d+) non-body sites, (\d+) triples and (\d+) seat-key entries under the same walk/g)];
  assert.equal(base.length, 1, "the merge-base cell stands in P7 once");
  const delta = [...P7.matchAll(/so this PR's own contribution is (\w+) seats \(the two `print\.button` seats\), one triple \([^)]*\) and (\w+) seat-key entries/g)];
  assert.equal(delta.length, 1, "the PR's own contribution stands in P7 once");
  assert.deepEqual(delta[0].slice(1), [COUNT_WORDS[seats - Number(base[0][1])], COUNT_WORDS[entries - Number(base[0][3])]], "the PR's own seats and entries are the live table's over the merge-base cell (" + (seats - Number(base[0][1])) + " seats, " + (entries - Number(base[0][3])) + " entries)");
  assert.equal(tripleAtRound7 - Number(base[0][2]), 1, "one triple over the merge-base cell, as the sentence says");
  const printSeats = SEATS_READ_BY_HAND.filter((e) => e.seats === "print.button");
  assert.deepEqual(printSeats.map((e) => e.in + " " + e.on + "." + e.via).sort(), ["openFileView fileGroup.appendChild", "openUrlView acts.insertBefore"], "the two print.button seats are the table's, openUrlView's acts.insertBefore the triple the sentence names as new");
  assert.equal(printSeats.length, seats - Number(base[0][1]), "the PR's own seats over the merge-base cell are the print.button seats");
  assert.ok(P7.includes("the census module holds it to the table it runs and prints the same two in its `second read:` diagnostic"), "P7 says this module holds the sentence to the table it runs");
  const args = ARGS_READ_BY_HAND.length, argSeats = tableTimes(ARGS_READ_BY_HAND), urls = URL_WRITES_READ_BY_HAND.length, urlSeats = tableTimes(URL_WRITES_READ_BY_HAND);
  const sizes = [...P7.matchAll(/(\d+) argument sites over (\d+) hand-offs, (\w+) entries standing for two hand-offs each, (\w+) of them byte-identical calls \(([^)]*)\) and (\w+) the same argument handed to the same callee by two calls that differ after it \(([^)]*)\), (\d+) of the entries marked `unnamed` for the (\d+) hand-offs the census cannot name by shape and the compiler types as able to hold a node, and (\d+) URL writes today/g)];
  assert.equal(sizes.length, 1, "today's table sizes stand in P7 once, in the sentence's form (a sentence the pattern does not find is a loud failure here, never a default)");
  const argTwice = ARGS_READ_BY_HAND.filter((e) => e.times !== undefined);
  assert.ok(argTwice.length > 0 && argTwice.every((e) => e.times === 2), "every argument entry with a `times` reads two hand-offs (" + JSON.stringify(argTwice.map((e) => e.times)) + ")");
  const unnamedEntries = ARGS_READ_BY_HAND.filter((e) => e.unnamed), unnamedHanded = live.elementsHanded.filter((h) => h.unnamed);
  assert.deepEqual([sizes[0][1], sizes[0][2], sizes[0][3], sizes[0][8], sizes[0][9], sizes[0][10]], [String(args), String(argSeats), COUNT_WORDS[argTwice.length], String(unnamedEntries.length), String(unnamedHanded.length), String(urls)], "P7's argument sites, hand-offs, entries reading two hand-offs, entries marked `unnamed`, hand-offs the compiler's type refuses and URL writes are the tables' and the run's (" + args + " over " + argSeats + ", " + argTwice.length + " reading two, " + unnamedEntries.length + " marked over " + unnamedHanded.length + ", " + urls + ")");
  assert.equal(tableTimes(unnamedEntries), unnamedHanded.length, "the marked entries' `times` sum to the hand-offs the compiler's type refuses");
  // the entries reading two hand-offs, in two groups by execution (the round-8 fixes): the calls byte-identical whole, and the same
  // argument handed to the same callee by two calls that differ after it (the record test holds the two lists as one sequence in
  // table order and cannot make the split, which is this run's)
  const identical: ArgRead[] = [], differing: ArgRead[] = [];
  for (const e of argTwice) {
    const texts = [...live.handedNodes, ...live.elementsHanded].filter((h) => h.fn === e.in && h.to === e.to && h.arg === e.arg).map((h) => h.whole);   // the whole call text, as above
    assert.equal(texts.length, 2, "the entry reads two live hand-offs: " + JSON.stringify(texts));
    (new Set(texts).size === 1 ? identical : differing).push(e);
  }
  const names = (es: ArgRead[]): string => es.map((e) => e.in + "'s two `" + e.to + "`").join(", ");
  assert.deepEqual([sizes[0][4], sizes[0][5], sizes[0][6], sizes[0][7]], [COUNT_WORDS[identical.length], names(identical), COUNT_WORDS[differing.length], names(differing)], "the sentence counts and names the byte-identical pairs and the differing pairs, each group in table order (" + identical.length + " and " + differing.length + ")");
  assert.equal(urlSeats, urls, "no URL write is spelled alike twice at this head (the sentence carries one number for the URL writes; a `times` on an entry would make it two)");
  assert.ok(P7.includes("the census module holds to the tables it runs and prints in its `second read:` diagnostic"), "P7 says this module holds the sentence to the tables it runs");
  const setAttr = URL_WRITES_READ_BY_HAND.filter((e) => /\.setAttribute(?:NS)?\(/.test(e.on)).length;
  const setAttrSentence = [...P7.matchAll(/(\w+) `setAttribute` writes/g)];
  assert.equal(setAttrSentence.length, 1, "the setAttribute count stands in P7 once");
  assert.ok(setAttr > 0 && setAttr < COUNT_WORDS.length, "the URL table lists setAttribute writes (" + setAttr + ")");
  assert.equal(setAttrSentence[0][1], COUNT_WORDS[setAttr], "P7's count of the setAttribute writes the closing pass listed is the URL table's (" + setAttr + ")");
  // the record test counts each table's array literal by text (an entry opens a line as `  { in: "`, a `times` adds to the
  // seats and counts as an entry reading two); that read is what the shell job holds the sentences by, and it is held here to
  // the tables it counts. The count is TWO-SIDED and must stay so (the maintainer's round-8 ruling, 2026-09-21): the sentence is
  // held to the table this module runs above and to the text count in the record test, and the text count is held EQUAL to
  // the run table here, so each side is read by the other; a single-sided count (the text count alone holding the sentence,
  // with nothing holding it to the run table) would let the form keying pass silently, since an entry spelled so the text
  // pattern misses it, or a `times` the run table reads and the pattern does not, would drop from the text count and from the
  // sentence together and nothing would read the run table.
  const self = readRepo("ui", "webview", "file-print.test.ts");
  const literal = (start: string): string => sectionBetween(self, start, "\n];");
  const textCount = (src: string): { entries: number; seats: number; twice: number } => {
    const n = [...src.matchAll(/^  \{ in: "/gm)].length, times = [...src.matchAll(/, times: (\d+)[,} ]/g)].map((m) => Number(m[1]));
    return { entries: n, seats: n + times.reduce((sum, t) => sum + t - 1, 0), twice: times.filter((t) => t === 2).length };
  };
  assert.deepEqual(textCount(literal("const SEATS_READ_BY_HAND: SeatRead[] = [")), { entries, seats, twice: twice.length }, "the text count of the seat table's literal is the table run here (an entry not opening its line as the pattern expects would be missed by the text and is caught here)");
  assert.deepEqual(textCount(literal("const ARGS_READ_BY_HAND: ArgRead[] = [")), { entries: args, seats: argSeats, twice: argTwice.length }, "the text count of the argument table's literal is the table run here");
  const urlLiteral = literal("const URL_WRITES_READ_BY_HAND: UrlWriteRead[] = [");
  assert.deepEqual(textCount(urlLiteral), { entries: urls, seats: urlSeats, twice: 0 }, "the text count of the URL table's literal is the table run here");
  assert.equal([...urlLiteral.matchAll(/^  \{ in: "[^"]*", on: "[^"]*\.setAttribute(?:NS)?\(/gm)].length, setAttr, "the text count of the URL table's setAttribute entries is the table's");
});

// the round-8 fixes (the round-7 review's cluster C, tests-2 and regression-1, 2026-09-21): the argument axis's pass road refused
// nothing it could not name, and the merge deleted the entry reading the sanitized body handed to gateRemoteFigures. The
// population that road passed is derived here and held to the marked entries by set and by count, the deletion is executed as
// the mutant it was, and the four shapes the refuters said no syntactic rule reaches (a conditional, a cast of an untyped
// callback parameter, a bare `||`, a property access) are held live: dropping each entry reds its own hand-offs
test("the argument axis refuses what elementShape cannot name (the round-8 fixes on the round-7 review's cluster C): the hand-offs the compiler's type refuses over the live viewer are exactly the entries marked `unnamed`, by key set and by count, the count P7 carries is the run's, the mark follows the road (an entry marked for a hand-off the shape names, or unmarked for one it cannot, is refused), the entry fef739ca7 deleted is restored and its deletion reds the two gateRemoteFigures lines and nothing else (FAILS BEFORE: the two hand-offs were read on no axis), the sanitized body handed to a third imported callee under a cast is refused with the compiler's type (FAILS BEFORE: passed, the diagnostic unchanged), each of the four shapes no syntactic rule reaches is held by its entry, a chain on the body token yields to the first read, and a program is built once per source", () => {
  const live = seatSites(VIEWER_SRC);
  assert.deepEqual(census(VIEWER_SRC).refused, [], "the live viewer passes under the table, so every refusal below is the plant's or the dropped entry's");
  const unnamed = live.elementsHanded.filter((h) => h.unnamed), marked = ARGS_READ_BY_HAND.filter((e) => e.unnamed);
  const key = (x: { fn?: string; in?: string; to: string; arg: string }): string => (x.fn ?? x.in) + " | " + x.to + " | " + x.arg;
  assert.ok(unnamed.length > 0 && marked.length > 0, "the population exists at this head (" + unnamed.length + " hand-offs, " + marked.length + " entries)");
  assert.deepEqual([...new Set(unnamed.map(key))].sort(), marked.map(key).sort(), "the hand-offs the compiler's type refuses are the marked entries, as a set of (function, callee, argument) keys: an entry deleted or a hand-off gained reds by set difference, not by count alone");
  assert.equal(marked.length, new Set(marked.map(key)).size, "one marked entry per key");
  assert.equal(tableTimes(marked), unnamed.length, "...and their `times` sum to the hand-offs");
  assert.ok(unnamed.every((h) => /^an argument the census cannot name by shape, typed `[^`]+` by the compiler, a type that can hold a node$/.test(h.member)), "each refusal names the compiler's type: " + JSON.stringify(unnamed.map((h) => h.member)));
  assert.ok(live.elementsHanded.every((h) => h.unnamed || !h.member.startsWith("an argument the census cannot name")), "an unmarked hand-off is one the shape rule named");
  const P7 = sectionPart("P7. **", "**Derivations and their unknown cases.**");
  const stated = [...P7.matchAll(/(\d+) of the entries marked `unnamed` for the (\d+) hand-offs the census cannot name by shape/g)];
  assert.equal(stated.length, 1, "P7 states the unnamed population once (a sentence the pattern does not find is a loud failure, never a default)");
  assert.deepEqual([stated[0][1], stated[0][2]], [String(marked.length), String(unnamed.length)], "P7's two numbers are this run's (" + marked.length + " entries over " + unnamed.length + " hand-offs)");
  // the mark follows the road: an entry marked for a hand-off the shape rule names, and one unmarked for a hand-off it cannot, are refused
  const flashEntry = ARGS_READ_BY_HAND.find((e) => e.in === "openFileView" && e.to === "flash")!, gateEntry = ARGS_READ_BY_HAND.find((e) => e.in === "mdBlock" && e.to === "gateRemoteFigures")!;
  const misMarked = census(VIEWER_SRC, undefined, undefined, ARGS_READ_BY_HAND.map((e) => (e === flashEntry ? { ...e, unnamed: true as const } : e)));
  assert.equal(misMarked.refused.length, 1, "an entry marked `unnamed` for a hand-off the shape rule names: " + JSON.stringify(misMarked.refused)); assert.match(misMarked.refused[0], /^line \d+: flash\(outlineBtn\) hands `outlineBtn`, el\(\.\.\.\) bound to `outlineBtn`, where ARGS_READ_BY_HAND's entry is marked `unnamed` and the census now names the shape: the two populations must not blur/);
  const unMarked = census(VIEWER_SRC, undefined, undefined, ARGS_READ_BY_HAND.map((e) => (e === gateEntry ? { ...e, unnamed: undefined } : e)));
  assert.equal(unMarked.refused.length, 2, "an entry not marked for the two hand-offs the shape rule cannot name: " + JSON.stringify(unMarked.refused)); for (const r of unMarked.refused) assert.match(r, /gateRemoteFigures\(clean, [^)]*\) hands `clean`, an argument the census cannot name by shape, typed `HTMLElement` by the compiler, a type that can hold a node, where ARGS_READ_BY_HAND's entry is not marked `unnamed` and the census cannot name the shape/);
  // the deletion fef739ca7 made, executed as a mutant: the entry dropped reds the two lines that hand the sanitized body to
  // gateRemoteFigures and nothing else (FAILS BEFORE: both passed, and the census stayed green over two hand-offs read on no axis)
  const gateLines = VIEWER_SRC.split("\n").flatMap((l, i) => (l.includes("gateRemoteFigures(clean") ? [String(i + 1)] : []));
  assert.equal(gateLines.length, 2, "the viewer hands `clean` to gateRemoteFigures twice: lines " + gateLines.join(", "));
  const deleted = census(VIEWER_SRC, undefined, undefined, ARGS_READ_BY_HAND.filter((e) => e !== gateEntry));
  assert.deepEqual(deleted.refused.map((r) => /^line (\d+):/.exec(r)![1]), gateLines, "FAILS BEFORE: the entry deleted reds the two hand-offs by line, and nothing else: " + JSON.stringify(deleted.refused));
  for (const r of deleted.refused) assert.match(r, /hands `clean`, an argument the census cannot name by shape, typed `HTMLElement` by the compiler, a type that can hold a node \(bound by `const clean = sanitizeMd\(dirty, mintHeadingIds\)`\), to gateRemoteFigures\(\.\.\.\) in mdBlock, a callee this file does not declare and the census has not read by hand for what it does with an element it is handed .* marked `unnamed`/);
  // the plant: the sanitized body handed to a third imported callee under a cast, a spelling the seam test's exact-call pin does
  // not read (FAILS BEFORE: 0 refusals, the diagnostic unchanged)
  const after = "\n    gateRemoteFigures(clean, document.baseURI);\n";
  assert.equal(VIEWER_SRC.split(after).length, 2, "the file kind's gate call is written once");
  const plantAt = VIEWER_SRC.indexOf(after) + after.length;
  const planted = VIEWER_SRC.slice(0, plantAt) + '    addCopyBtn(clean as HTMLElement, "");\n' + VIEWER_SRC.slice(plantAt);
  const plantLine = VIEWER_SRC.slice(0, plantAt).split("\n").length;
  const plant = census(planted);
  assert.equal(plant.refused.length, 1, "FAILS BEFORE: the sanitized body under a cast handed to addCopyBtn: " + JSON.stringify(plant.refused));
  assert.match(plant.refused[0], new RegExp("^line " + plantLine + ": addCopyBtn\\(clean as HTMLElement, \"\"\\) hands `clean as HTMLElement`, an argument the census cannot name by shape, typed `HTMLElement` by the compiler, a type that can hold a node \\(bound by `const clean = sanitizeMd\\(dirty, mintHeadingIds\\)`\\), to addCopyBtn\\(\\.\\.\\.\\) in mdBlock"));
  const aliased = census(VIEWER_SRC.slice(0, plantAt) + '    const c2 = clean; addCopyBtn(c2, "");\n' + VIEWER_SRC.slice(plantAt));
  assert.equal(aliased.refused.length, 1, "...and through an alias, which the seam test's pin does not read either: " + JSON.stringify(aliased.refused)); assert.match(aliased.refused[0], /hands `c2`, an argument the census cannot name by shape, typed `HTMLElement` by the compiler, a type that can hold a node \(bound by `const c2 = clean`\), to addCopyBtn/);
  // the four shapes the refuters said no syntactic rule reaches, each a live hand-off held by its entry: dropping the entry reds its line(s) alone
  for (const [inFn, to, arg, what] of [["mdBlock", "addCopyBtn", "host", "a conditional"], ["mdBlock", "wrapCodeLines", "codeEl", "a cast of an untyped callback parameter"], ["scrollToFragment", "fragmentTarget", 'box.querySelector(".fileview-md") || box', "a bare `||`"], ["gateKeys", "gateOf", "ev.target", "a property access"]] as const) {
    const e = ARGS_READ_BY_HAND.find((x) => x.in === inFn && x.to === to && x.arg === arg)!;
    assert.ok(e !== undefined && e.unnamed, what + " is listed and marked: " + inFn + "/" + to + "/" + arg);
    const r = census(VIEWER_SRC, undefined, undefined, ARGS_READ_BY_HAND.filter((x) => x !== e));
    assert.equal(r.refused.length, e.times ?? 1, what + ": the entry dropped reds its hand-off(s) and nothing else: " + JSON.stringify(r.refused));
    for (const one of r.refused) assert.match(one, new RegExp("^line \\d+: .* to " + to + "\\(\\.\\.\\.\\) in " + inFn + ", a callee this file does not declare"));
  }
  // a chain on the body token yields to the first read (the round-8 build's run 4: without the yield, `pick(body.firstChild)` red twice)
  assert.ok(!live.elementsHanded.some((h) => /^body\./.test(h.arg)), "no hand-off of a chain on the body token is on this axis");
  // the program is built once per source text: two reads of one source share it, a second source gets its own
  assert.strictEqual(programOver(VIEWER_SRC), programOver(VIEWER_SRC), "one program for one source text");
  assert.notStrictEqual(programOver(planted), programOver(VIEWER_SRC), "another source, another program (the last one handed on as the predecessor)");
});

/** A row of the figure leg's table as `shapes()` builds it: the fields the record's pins read (the leg's own `Shape` type
 *  has more; a per-engine column is an object keyed by engine). */
type FigureRow = { name: string; html: (url: string, url2: string) => string; hidden?: boolean | Record<string, boolean>; paints: boolean | Record<string, boolean>; fetches?: unknown; twinReads?: Record<string, boolean | undefined>; flowReads?: { in: Record<string, boolean | undefined>; why: string } };
/** The figure leg's table, BUILT: `shapes()` and the helpers it reads (`svgOf`, `image`, `HIDE_RULE`), cut from the leg's
 *  source, transpiled with the compiler and run, so a count here is of the rows the leg builds (rows come from loops, so a
 *  `name:` grep undercounts them). A cut that misses either mark fails, which is the failure wanted. */
function figureRows(): FigureRow[] {
  const src = readRepo("ui", "webview", "file-print-figure-browser.test.ts");
  const start = src.indexOf("const svgOf = ");
  const fnAt = src.indexOf("function shapes(): Shape[] {", start);
  const end = src.indexOf("\n}\n", fnAt);
  assert.ok(start >= 0 && fnAt > start && end > fnAt, "the leg declares svgOf, then shapes()");
  const js = ts.transpileModule(src.slice(start, end + 2) + "\nreturn shapes();", { compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.None } }).outputText;
  const rows = new Function(js)() as FigureRow[];
  assert.ok(Array.isArray(rows) && rows.length > 0 && rows.every((r) => typeof r.name === "string" && typeof r.html === "function"), "the built table: rows with a name and an html builder");
  return rows;
}
/** The figure leg's per-engine rows, derived from the table it builds: every row whose ink (`paints`), root answer
 *  (`hidden`), twin oracle reading (`twinReads`) or flow answer (`flowReads`) is recorded per engine, each as the words the
 *  Tests list carries for it, the row's name and the engines named (the round-6 review's cluster E, 2026-09-20: the roster
 *  bullet stated single answers for rows the leg holds per engine, and a literal-sentence pin held the stale sentence; the
 *  bullet now carries this list and the pin below derives it, so a row the leg gains with a per-engine column reds until the
 *  bullet names it). */
const ENGINE_NAMES: Record<string, string> = { chromium: "Chromium", firefox: "Firefox", webkit: "WebKit" };
const ENGINE_ORDER = ["chromium", "firefox", "webkit"];
const engineList = (engines: string[]): string => engines.length <= 1 ? engines.map((e) => ENGINE_NAMES[e]).join("") : engines.slice(0, -1).map((e) => ENGINE_NAMES[e]).join(", ") + " and " + ENGINE_NAMES[engines[engines.length - 1]];
function divergenceNotes(rows: FigureRow[]): string[] {
  const out: string[] = [];
  for (const r of rows) {
    const parts: string[] = [];
    const paints = r.paints, hidden = r.hidden, twin = r.twinReads, flow = r.flowReads;
    if (typeof paints === "object") parts.push("ink in " + engineList(ENGINE_ORDER.filter((e) => paints[e])) + ", none in " + engineList(ENGINE_ORDER.filter((e) => !paints[e])));
    if (typeof hidden === "object") parts.push("the root read hidden in " + engineList(ENGINE_ORDER.filter((e) => hidden[e])) + " alone");
    if (twin !== undefined) {
      const on = ENGINE_ORDER.filter((e) => twin[e] === true), off = ENGINE_ORDER.filter((e) => twin[e] === false);
      if (on.length) parts.push("the twin oracle reads a box in " + engineList(on));
      if (off.length) parts.push("the twin oracle reads none in " + engineList(off));
    }
    if (flow !== undefined) {
      const on = ENGINE_ORDER.filter((e) => flow.in[e] === true), off = ENGINE_ORDER.filter((e) => flow.in[e] === false);
      if (on.length) parts.push("the flow counts it in " + engineList(on));
      if (off.length) parts.push("the flow reads it off in " + engineList(off));
    }
    if (parts.length) out.push("`" + r.name + "` (" + parts.join("; ") + ")");
  }
  return out;
}

test("the figure leg's table, built from the leg's own source: the shape count P2 and the Tests list state is the number of rows `shapes()` builds, the two-URL count is the rows whose html takes the second URL, and the Tests list's figure-leg entry names every row the leg holds per engine, per engine, from the built table (the record test holds these sentences by text and cannot build the table: it runs with no node_modules)", () => {
  const rows = figureRows();
  const P2 = sectionPart("P2. **", "P3. **"), TESTS = sectionPart("**Tests.**", "**Open points for the owner.**");
  const p2 = P2.match(/file-print-figure-browser\.test\.ts, in Chromium, Firefox and WebKit since the round-5 review: every one of (\d+) gated shapes built twice on one page, (\d+) at the round-3 review and (\w+) more since the round-4 review/);
  assert.ok(p2 !== null && Number(p2[1]) === rows.length, "P2's sentence around the shape count carries the number of rows the leg builds (" + rows.length + ")");
  const tests = TESTS.match(/every one of (\d+) gated shapes built twice on one page \((\d+) at the round-3 review, (\w+) added since the round-4 review, below\)/);
  assert.ok(tests !== null && Number(tests[1]) === rows.length, "the Tests list's sentence around the shape count carries the number of rows the leg builds (" + rows.length + ")");
  // the two-URL qualifier (the round-5 review's regression-5 and extra6-4): the rows whose html takes the second URL
  const twoUrl = rows.filter((r) => r.html("URL", "URL2").includes("URL2"));
  assert.ok(twoUrl.length >= 2 && twoUrl.length < COUNT_WORDS.length, "two-URL rows exist and their count has a word: " + twoUrl.length);
  assert.ok(twoUrl.every((r) => r.fetches !== undefined), "every two-URL row carries a measured `fetches` column");
  assert.ok(TESTS.includes("over " + COUNT_WORDS[twoUrl.length] + " added shapes with two URLs on two hosts, and a " + ORDINAL_WORDS[twoUrl.length + 1] + " for the display read below the root"), "the Tests list counts the two-URL shapes as the leg builds them (" + twoUrl.length + ") and the one-URL addition as the next");
  // the per-engine list (the round-6 review's cluster E, regression-1 and extra7-1)
  const bullet = sectionBetween(TESTS, "- ui/webview/file-print-figure-browser.test.ts, headless Chromium, Firefox and WebKit", "- ui/webview/file-view-print-takings-browser.test.ts");
  const notes = divergenceNotes(rows);
  const perEngine = rows.filter((r) => typeof r.paints === "object" || typeof r.hidden === "object" || r.twinReads !== undefined || r.flowReads !== undefined);
  assert.equal(notes.length, perEngine.length, "one note per row with a per-engine column (paints or hidden per engine, twinReads, flowReads)");
  assert.ok(notes.length >= 3 && notes.length < rows.length, "the population at this head: " + notes.length + " of " + rows.length + " rows hold a per-engine column");
  const list = "The rows the leg holds per engine, each held to its record and named here from the leg's built table (file-print.test.ts derives this list from `shapes()` under npm test, so a row the leg gains with a per-engine column reds until it is named): " + notes.join("; ") + ".";
  assert.ok(bullet.includes(list), "the figure-leg entry names every per-engine row per engine, in the leg's order: the population derived is the rows with per-engine paints or hidden, twinReads or flowReads, read in the entry's slice of the Tests list (its head to the takings leg's entry). Expected in the entry: " + list);
});

/** The array methods whose callback takes the element's index (the index is the third parameter of reduce and reduceRight,
 *  the second of the rest). */
const INDEXED_ITERATORS = ["map", "forEach", "flatMap", "filter", "some", "every", "find", "findIndex", "findLast", "findLastIndex", "reduce", "reduceRight"];
/** Every chain in `src` that indexes a filter's result by its POST-FILTER index, by its syntax, so `i` counts the rows the
 *  filter KEPT and no longer names the row of any table the callback indexes. The shape space read (the round-6 review's
 *  tests-4, 2026-09-20: before this the census matched one shape, a `.map` with an indexed callback directly on a `.filter`
 *  call): a call of any INDEXED_ITERATORS method whose callback declares the index parameter, on a receiver that is a
 *  `.filter(...)` call or an identifier a variable declaration anywhere in the module binds to one (a `!` or parentheses
 *  between them unwrapped), and `Array.from(<filter result>, (row, i) => ...)`. NOT read, so a chain written these ways
 *  passes unseen: a filter result handed to a function as an argument and indexed inside it, returned from a function,
 *  reassigned after its declaration, reached through a property or an element access, or spread into another array; a
 *  binding is matched by NAME across the module, not by scope, so a name bound to a filter in one function marks that
 *  name everywhere. Each as `line: text`. */
function postFilterIndexChains(name: string, src: string): string[] {
  const sf = ts.createSourceFile(name, src, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
  const out: string[] = [];
  const unwrap = (n: ts.Node): ts.Node => { while (ts.isNonNullExpression(n) || ts.isParenthesizedExpression(n) || ts.isAsExpression(n) || ts.isTypeAssertionExpression(n)) n = n.expression; return n; };
  const isFilterCall = (n: ts.Node): boolean => ts.isCallExpression(n) && ts.isPropertyAccessExpression(n.expression) && n.expression.name.text === "filter";
  const filterBound = new Set<string>();
  const collect = (n: ts.Node): void => { if (ts.isVariableDeclaration(n) && ts.isIdentifier(n.name) && n.initializer !== undefined && isFilterCall(unwrap(n.initializer))) filterBound.add(n.name.text); ts.forEachChild(n, collect); };
  collect(sf);
  const fromFilter = (n: ts.Node): boolean => { const r = unwrap(n); return isFilterCall(r) || (ts.isIdentifier(r) && filterBound.has(r.text)); };
  const indexed = (fn: ts.Expression | undefined, min: number): boolean => fn !== undefined && (ts.isArrowFunction(fn) || ts.isFunctionExpression(fn)) && fn.parameters.length >= min;
  const at = (n: ts.Node): string => (sf.getLineAndCharacterOfPosition(n.getStart(sf)).line + 1) + ": " + n.getText(sf);
  const walk = (n: ts.Node): void => {
    if (ts.isCallExpression(n) && ts.isPropertyAccessExpression(n.expression)) {
      const method = n.expression.name.text, recv = n.expression.expression;
      if (INDEXED_ITERATORS.includes(method) && fromFilter(recv) && indexed(n.arguments[0], /^reduce/.test(method) ? 3 : 2)) out.push(at(n));
      else if (method === "from" && ts.isIdentifier(recv) && recv.text === "Array" && n.arguments.length >= 2 && fromFilter(n.arguments[0]) && indexed(n.arguments[1], 2)) out.push(at(n));
    }
    ts.forEachChild(n, walk);
  };
  walk(sf);
  return out;
}
/** The print follow-on's test modules under ui/webview: the `ls ui/webview/file-print*.test.ts` listing the Tests paragraph
 *  names, the gate's node module, the takings leg and the legs' shared harness. Read from the directory, so a module added
 *  under the pattern joins the census on its own (the record test lists them the same way for its text census). */
const printTestModules = (): string[] => [...fs.readdirSync(path.join(REPO_ROOT, "ui", "webview")).filter((f) => /^file-print.*\.test\.ts$/.test(f)), "figure-gate.test.ts", "file-view-print-takings-browser.test.ts", "real-viewer-leg.ts"].sort();
/** The chains sanctioned by hand, each the executed record of the defect inside the node case that holds the helper
 *  replacing it, keyed by module and by the chain's exact text (a line number would move). The record test carries the same
 *  two texts and holds this literal to its list. */
type PostFilterRecord = { file: string; text: string; why: string };
const POST_FILTER_INDEX_RECORDS: PostFilterRecord[] = [
  { file: "file-print-figure-browser.test.ts", text: "rows.filter((r, i) => r.twinPaints !== expected[i]).map((r, i) => r.name + \": the browser paints the twin \" + r.twinPaints + \", the leg expected \" + expected[i])", why: "paperMismatches' fails-before record (the round-4 review's correctness-4)" },
  { file: "file-print-figure-browser.test.ts", text: "restored.filter(holds).map((_, i) => names[i])", why: "namesWhere's fails-before record (the round-5 review's correctness-3)" },
];

test("the post-filter index (the round-4 review's correctness-4, tests-7 and regression-3; the round-5 review's correctness-3, tests-2, regression-2 and extra7-1, one defect filed seven times; the round-6 review's tests-4: the shape space widened from one form): a census over the print test modules by syntax finds every chain that indexes a filter's result by the post-filter index in the forms its docstring names, passes the two fails-before records by their exact text and refuses any other with its module and line, saying what it does not read (run here, where the compiler is; the record test holds the records by text)", () => {
  const modules = printTestModules();
  assert.ok(modules.length >= 9 && modules.includes("file-print-figure-browser.test.ts") && modules.includes("file-print.test.ts"), "the listing is the follow-on's, this module in it: " + modules.join(", "));
  const refused: string[] = [], found: PostFilterRecord[] = [];
  for (const file of printTestModules()) {
    for (const chain of postFilterIndexChains(file, readRepo("ui", "webview", file))) {
      const text = chain.slice(chain.indexOf(": ") + 2);
      const record = POST_FILTER_INDEX_RECORDS.find((r) => r.file === file && r.text === text);
      if (record) found.push(record); else refused.push(file + ":" + chain);
    }
  }
  assert.deepEqual(refused, [], "a post-filter-index chain the census has not read by hand: a message built from it names a row other than the one that failed (namesWhere or paperMismatches carry the row with its name). Read: an indexed callback of " + INDEXED_ITERATORS.join(", ") + " or Array.from on a filter call or a name a declaration binds to one, through !, parentheses and casts. Not read: a filter result handed as an argument, returned, reassigned, reached through a property or an element access, or spread");
  assert.deepEqual(found.map((r) => r.text).sort(), POST_FILTER_INDEX_RECORDS.map((r) => r.text).sort(), "each sanctioned record stands once, none stale");
  assert.equal(found.length, 2, "the population of the class at the round-6 head: the two records, no live chain");
  // the census's own shape space is executed over a synthetic module: each named form is found, each unread form is not
  const synthetic = [
    "const kept = rows.filter((r) => r.ok);", "kept.map((r, i) => i);", "kept!.forEach((r, i) => i);", "(kept as T[]).some((r, i) => i > 0);",
    "rows.filter((r) => r.ok).reduce((a, r, i) => a + i, 0);", "Array.from(rows.filter((r) => r.ok), (r, i) => i);",
    "kept.map((r) => r.name);", "take(rows.filter((r) => r.ok)).map((r, i) => i);", "[...kept].map((r, i) => i);", "o.kept.map((r, i) => i);",
  ].join("\n");
  assert.deepEqual(postFilterIndexChains("synthetic.ts", synthetic).map((c) => c.slice(0, c.indexOf(":"))), ["2", "3", "4", "5", "6"], "the five named forms are found by their lines; the one-parameter callback, the argument road, the spread and the property road are not, as the docstring says");
});
