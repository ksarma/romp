// The print flow's machine and its wait (file-print.ts; the print follow-on to plans/markdown-viewer.md's Slice 3, item 12),
// executed under node with no DOM: `step` over every phase and event (the disabled phase the driver starts in, P7, and the
// stalled phase the deadline's ask stands in, among them), the words, the chord, and settlePictures over fake pictures and a
// fake clock (the deadline is the one timer in the module, and it is injected; Keep waiting's wait sets none). The DOM driver, the button,
// the line and window.print run over the real viewer in file-print-browser.test.ts. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { step, RESTING, DISABLED, armedWords, preparingWords, stalledWords, isPrintChord, settlePictures, collectPictures, bodyReady, PRINT_SETTLE_MS, setPrintSettleMs, printSettleMs,
  WITH_WORDS, WITHOUT_WORDS, ANYWAY_WORDS, KEEP_WORDS, TAB_WORDS, NO_TAB_WORDS, pdfFrameWindow, READY_ROOTS, NOT_READY_ROOTS, LINE_ROOTS,
  type PrintState, type Picture, type Timers, type BodyLike, type PrintableNode } from "./file-print";

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

test("ready during the wait prints; printed rests; a press, an Escape or a choice during the wait or the print changes nothing", () => {   // the wait's verdict carries why (settled, or the deadline) and the count still loading: the machine reads both (the deadline's ask, below)
  const preparing: PrintState = { phase: "preparing", gated: 0, pending: 2 };
  for (const ev of [{ kind: "press", gated: 0, pending: 0 }, { kind: "escape" }, { kind: "choose", withGated: true }, { kind: "prepare", pending: 1 }, { kind: "printed" }] as const) {
    const r = step(preparing, ev);
    assert.equal(r.act, "none", ev.kind + " during the wait");
    assert.equal(r.state, preparing, ev.kind + " during the wait keeps the state");
  }
  const printing = step(preparing, { kind: "ready", why: "settled", pending: 0 });
  assert.equal(printing.act, "print");
  assert.equal(printing.state.phase, "printing");
  for (const ev of [{ kind: "press", gated: 2, pending: 0 }, { kind: "escape" }, { kind: "ready", why: "settled", pending: 0 }] as const) {
    assert.equal(step(printing.state, ev).act, "none", ev.kind + " during the print");
  }
  const rested = step(printing.state, { kind: "printed" });
  assert.equal(rested.act, "rest");
  assert.equal(rested.state.phase, "resting");
  assert.equal(step(RESTING, { kind: "ready", why: "settled", pending: 0 }).act, "none", "a late ready after a rest changes nothing");
  assert.equal(step(RESTING, { kind: "printed" }).act, "none");
});

test("the words: one picture and many, for the armed line, the wait and the ask; the four buttons' words", () => {
  assert.equal(armedWords(1), "1 picture from another host is not loaded.");
  assert.equal(armedWords(2), "2 pictures from other hosts are not loaded.");
  assert.equal(preparingWords(1), "Preparing 1 picture…");
  assert.equal(preparingWords(3), "Preparing 3 pictures…");
  assert.equal(stalledWords(1), "1 picture has not loaded.");
  assert.equal(stalledWords(3), "3 pictures have not loaded.");
  assert.equal(WITH_WORDS, "Print with them");
  assert.equal(WITHOUT_WORDS, "Print without them");
  assert.equal(ANYWAY_WORDS, "Print anyway");
  assert.equal(KEEP_WORDS, "Keep waiting");
});

// ── the deadline's ask (the stalled phase) ──────────────────────────────────────────────────────────

test("the wait's verdict carries why and the count still loading: settled prints; the deadline with pictures still loading asks instead of printing; the deadline with nothing pending is a settle in effect and prints; Print anyway prints; Keep waiting resumes through the driver's prepare, into an open-ended wait or a print with nothing left; Escape or a second press disarms; a repaint under the ask counts again or prints over none", () => {
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
  assert.equal(step(asked.state, { kind: "stalled", pending: 0 }).act, "print", "a repaint under the ask with nothing loading prints: the question is moot and the wait's condition is met");
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

test("the open-ended wait: Escape cancels it, where the timed wait's Escape is left to the viewer; a press changes nothing in either; ready prints in both; the timed waits carry no mark", () => {
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
const node = (localName: string, attrs: string[] = [], parentElement: PrintableNode | null = null): PrintableNode => ({ localName, parentElement, hasAttribute: (k) => attrs.includes(k) });
/** A picture stand-in: its attributes (read by getAttribute and by the printable walk's hasAttribute), its parent for that walk (none: in the open body) and its name (an img unless said). */
const elm = (attrs: Record<string, string>, complete = false, loading?: string, parentElement: PrintableNode | null = null, localName = "img"): FakeEl => ({ localName, parentElement, hasAttribute: (k) => k in attrs, complete, getAttribute: (k) => (k in attrs ? attrs[k] : null), addEventListener() {}, removeEventListener() {}, ...(loading === undefined ? {} : { loading }) });

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
});

// ── the body not in (P7) ────────────────────────────────────────────────────────────────────────────

/** A body stand-in whose children are `kids`, each "name.class1.class2" (the viewer's own paints, spelled as the DOM would read them). */
const bodyOf = (...kids: string[]): BodyLike => ({ children: kids.map((k) => { const [localName, ...classes] = k.split("."); return { localName, classList: { contains: (c: string) => classes.includes(c) } }; }) });

test("bodyReady reads the body's children: the loader as content, the plain fallback editor and a failure line alone are not in; a rendered root, code, a picture's box, a PDF frame's column (a loader inside it aside), the pages' host, the CodeMirror mount and a line over content are in; an empty body is not", () => {
  assert.equal(bodyReady(bodyOf()), false, "an empty body (the URL viewer's before its loader)");
  assert.equal(bodyReady(bodyOf("div.fileview-load")), false, "the open's loader, the editor's chunk wait");
  assert.equal(bodyReady(bodyOf("div.fileview-load", "div.fileview-pdfhost")), false, "the Comments panel's PDF pages before page 1 is drawn, with no frame to keep: the loader and the empty host");
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
});

// ── the census of the body's roots (P7) ────────────────────────────────────────────────────────────
// bodyReady classes a child it has never seen as content, on purpose (a false not-ready locks the button with no road out; a
// false ready is a press that prints what stands), so a root the viewer gains would be classed silently unless something
// reads the viewer. This census does: it reads file-view.ts, finds every site that seats an element in the body and resolves
// each seated expression down to the root element's `el("<tag>", "<class>")`, then holds that set equal to the flow's three
// lists (READY_ROOTS, NOT_READY_ROOTS, LINE_ROOTS) and executes bodyReady over each root as its list says. The sites, by
// hand, are the lines this command prints:
//   grep -nP '(?<!document\.)\bbody\.(replaceChildren|prepend|appendChild)\(' ui/webview/file-view.ts
// and the census resolves each argument of those calls: a builder call (`mdBlock(...)`) to the `el(...)` assigned to the
// variable the builder's last `return` names; a bare variable to the expression assigned to it last before the site; a
// ternary to both its branches; an `el("<tag>", "<class>")` to itself. An expression it cannot resolve fails the census with
// the expression, so a new shape is read by hand rather than skipped.
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
/** The roots (`<tag>.<class>`) the expression `expr`, written at `before` in file-view.ts, seats. */
function rootsOf(expr: string, before: number): string[] {
  const e = expr.trim();
  const q = indexTop(e, " ? ");
  if (q >= 0) {
    const branches = e.slice(q + 3);
    const c = indexTop(branches, " : ");
    assert.ok(c >= 0, "a ternary has both branches: " + e);
    return [...rootsOf(branches.slice(0, c), before), ...rootsOf(branches.slice(c + 3), before)];
  }
  const built = /^el\("(\w+)", "([\w -]+)"\)$/.exec(e);
  if (built) return [built[1] + "." + built[2].split(" ").join(".")];
  const call = /^(\w+)\(/.exec(e);
  if (call && call[1] !== "el") {
    const head = "\nfunction " + call[1] + "(";
    const at = VIEWER_SRC.indexOf(head);
    assert.ok(at >= 0, "the builder " + call[1] + " is a top-level function of file-view.ts");
    const end = VIEWER_SRC.indexOf("\n}\n", at);
    const body = VIEWER_SRC.slice(at, end);
    const returns = [...body.matchAll(/^\s+return (\w+);$/gm)];
    assert.ok(returns.length >= 1, "the builder " + call[1] + " returns a variable");
    return rootsOf(returns[returns.length - 1][1], at + body.length);
  }
  const name = /^(\w+)$/.exec(e);
  if (name) {
    const assigned = [...VIEWER_SRC.slice(0, before).matchAll(new RegExp("\\b" + name[1] + " = (?!=)([^;\\n]+?)(?: as \\w+)?;", "g"))];
    assert.ok(assigned.length >= 1, "the variable " + name[1] + " is assigned before the site at " + before);
    const last = assigned[assigned.length - 1];
    return rootsOf(last[1], last.index!);
  }
  throw new Error("a seated expression the census cannot resolve: " + e);
}

test("the census of the body's roots: every element file-view.ts seats in the body resolves to a root the flow lists (READY_ROOTS, NOT_READY_ROOTS or LINE_ROOTS), every listed root is seated, no root is in two lists, bodyReady answers over each root as its list says, and an unlisted child reads as content, the fallthrough the lists guard", (t) => {
  const sites = [...VIEWER_SRC.matchAll(/(?<!document\.)\bbody\.(replaceChildren|prepend|appendChild)\(/g)];
  assert.ok(sites.length >= 10, "the seating sites are found in file-view.ts: " + sites.length);
  const seated = new Map<string, number[]>();
  for (const m of sites) {
    const line = VIEWER_SRC.slice(0, m.index!).split("\n").length;
    const args = balancedAt(VIEWER_SRC, m.index! + m[0].length - 1).replace(/\s+/g, " ").trim();
    if (!args) continue;   // a clearing seats nothing: an empty body is executed above
    for (const arg of splitTop(args, ",")) for (const root of rootsOf(arg, m.index!)) seated.set(root, [...(seated.get(root) || []), line]);
  }
  const roots = [...seated.keys()].sort();
  t.diagnostic("census: " + roots.map((r) => r + " (line " + seated.get(r)!.join(", ") + ")").join("; "));
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
  assert.equal(bodyReady(bodyOf("div.fileview-unlisted")), true, "a child none of the lists names reads as content: the fallthrough this census guards");
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
