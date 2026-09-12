// The Copy button's execCommand fallback leaves the page's selection and focus as it found them (code-block.ts fallbackCopy;
// the Slice 5 review of plans/markdown-viewer.md, rounds 6 and 7). The fallback runs when the async Clipboard API is missing (an
// insecure origin) or refuses: a textarea off screen takes the text, the focus and the selection, execCommand copies the
// selection, and the textarea is removed. Its focus and its select are the copy's moves, not the person's, and the removal
// left them as it found them: the document's selection collapsed outside whatever had been selected and the focus on the
// body, with no selectionchange the document hears. In the file viewer a passage stood with its Comment button beside it and
// nothing selected under the button, so a click on the button opened nothing (file-comments-copy-fallback-browser.test.ts
// shows it over the real viewer), and Space on a focused Copy button lost the keyboard's place. Now the selection's two ends,
// anchor and focus, are kept before the textarea takes it and put back after with setBaseAndExtent, each where it was, and
// the element that held the focus takes it back; a page with no selection keeps none, and a body that held the focus is left
// alone. The ends and not a Range (round 7): a Range has no direction, and round 6's put-back through addRange came back FORWARD
// for a selection the person had made right to left, its anchor and focus swapped, so the next Shift+ArrowLeft shrank it from
// the other end and the viewer's panel, which knows the selection it offered Comment beside by its ends, offered again. The
// Ranges, cloned (the Range a selection hands out is the selection's own and follows it), stay the route for an engine without
// setBaseAndExtent and for a put-back the engine refuses. Over a stand-in whose selection and focus move as a browser's do for
// the textarea trick: select() puts the textarea's range in the document's selection, the removal leaves a collapsed one
// elsewhere, focus() sets the active element; the selection carries a direction bit as a browser's does (anchor and focus read
// off its range and the bit; addRange puts a range in forward, as the Selection API does, setBaseAndExtent sets both ends as
// given), and logs what was called on it. The Clipboard API is absent throughout (the fallback's own case). Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { hideEdges } from "../test-dom-shim";

// ── the stand-in: elements with a parent, focus that sets the active element, a textarea whose select takes the selection ──
class El {
  parentNode: El | null = null;
  children: El[] = [];
  value = ""; style: Record<string, string> = {};
  focusCalls: Array<{ preventScroll?: boolean } | undefined> = [];
  constructor(public tagName: string) { hideEdges(this); }
  appendChild(c: El): El { c.parentNode?.removeChild(c); c.parentNode = this; this.children.push(c); return c; }
  removeChild(c: El): El {
    const i = this.children.indexOf(c); if (i >= 0) this.children.splice(i, 1); c.parentNode = null;
    // the browser's selection once the node holding it is gone: collapsed at the nearest place it can stand, outside what was selected
    if (selection.ranges.some((r) => r.start[0] === c)) selection.put([range(doc.body, 0, doc.body, 0)], false);
    if (doc.activeElement === c) doc.activeElement = doc.body;
    return c;
  }
  focus(opts?: { preventScroll?: boolean }): void { this.focusCalls.push(opts); doc.activeElement = this; }
  /** A textarea's select(): the document's selection moves to the textarea (the fallback's premise: execCommand copies the selection). */
  select(): void { selection.moves.push("select"); selection.put([range(this, 0, this, 1)], false); }
}
type Point = [unknown, number];
type FakeRange = { start: Point; end: Point; cloneRange(): FakeRange };
const range = (sn: unknown, so: number, en: unknown, eo: number): FakeRange => ({ start: [sn, so], end: [en, eo], cloneRange() { return range(sn, so, en, eo); } });
/** The document's selection: its ranges and the browser's direction bit (backwards: the anchor is the range's end, the focus its
 *  start), the four ends read off them, and a log of what was called on it (the route a restore took). */
const selection = {
  ranges: [] as FakeRange[],
  backwards: false,
  moves: [] as string[],
  put(ranges: FakeRange[], backwards: boolean): void { selection.ranges = ranges; selection.backwards = backwards; },
  get rangeCount(): number { return selection.ranges.length; },
  get anchorNode(): unknown { const r = selection.ranges[0]; return r ? (selection.backwards ? r.end : r.start)[0] : null; },
  get anchorOffset(): number { const r = selection.ranges[0]; return r ? (selection.backwards ? r.end : r.start)[1] : 0; },
  get focusNode(): unknown { const r = selection.ranges[0]; return r ? (selection.backwards ? r.start : r.end)[0] : null; },
  get focusOffset(): number { const r = selection.ranges[0]; return r ? (selection.backwards ? r.start : r.end)[1] : 0; },
  getRangeAt(i: number): FakeRange { const r = selection.ranges[i]; if (!r) throw new Error("IndexSizeError"); return r; },
  removeAllRanges(): void { selection.moves.push("removeAllRanges"); selection.put([], false); },
  /** A Range has no direction: a selection built from one runs forward, as the Selection API's addRange has it. */
  addRange(r: FakeRange): void { selection.moves.push("addRange"); selection.ranges.push(r); selection.backwards = false; },
  /** Both ends as given: a focus before its anchor (in the one node the fixtures select in) makes a backwards selection. */
  setBaseAndExtent(an: unknown, ao: number, fn: unknown, fo: number): void {
    selection.moves.push("setBaseAndExtent");
    const back = an === fn && fo < ao;
    selection.put([back ? range(fn, fo, an, ao) : range(an, ao, fn, fo)], back);
  },
};
const execSeen: Array<{ active: El | null; selectionIn: unknown }> = [];   // what the command found: the active element and the selection's node
let execResult = true;
const doc = {
  body: new El("body"),
  activeElement: null as El | null,
  createElement: (tag: string) => new El(tag),
  execCommand: (cmd: string) => { assert.equal(cmd, "copy"); execSeen.push({ active: doc.activeElement, selectionIn: selection.ranges[0]?.start[0] }); return execResult; },
};
hideEdges(doc);
(globalThis as any).document = doc;
(globalThis as any).window = { setTimeout: (fn: () => void) => { fn(); return 1; }, getSelection: () => selection };
(globalThis as any).MutationObserver = class { observe(): void { /* inert */ } disconnect(): void { /* inert */ } };
Object.defineProperty(globalThis, "navigator", { configurable: true, get: () => ({ clipboard: undefined }) });   // no async API: the fallback runs

// eslint-disable-next-line @typescript-eslint/no-var-requires
const { copyText } = require("./code-block") as typeof import("./code-block");

const reset = (): void => { doc.body = new El("body"); doc.activeElement = doc.body; selection.put([], false); selection.moves.length = 0; execSeen.length = 0; execResult = true; };
/** A passage selected in a paragraph of the body (characters 3 to 9; `backwards` for a selection made right to left, its anchor
 *  at 9 and its focus at 3), and a Copy button holding the focus (a click focuses a button; so does Tab). */
function scene(backwards = false): { p: El; btn: El } {
  const p = doc.body.appendChild(new El("p")); const btn = doc.body.appendChild(new El("button"));
  selection.put([range(p, 3, p, 9)], backwards);
  btn.focus(); btn.focusCalls.length = 0;
  return { p, btn };
}
/** The selection's four ends, as the panel reads them (file-comments.ts endsOf). */
const ends = (): [unknown, number, unknown, number] => [selection.anchorNode, selection.anchorOffset, selection.focusNode, selection.focusOffset];

test("the fallback copies from its textarea (the textarea held the focus and the selection when the command ran) and then puts the selection back, by its ends, and the focus back on the element that held it", async () => {
  reset();
  const { p, btn } = scene();
  const before = selection.ranges[0];
  assert.deepEqual(ends(), [p, 3, p, 9], "the passage runs forward: anchor at 3, focus at 9");
  assert.equal(await copyText("x = 1\n"), true, "copied through the fallback");
  assert.equal(execSeen.length, 1, "one command");
  assert.equal(execSeen[0].active?.tagName, "textarea", "the textarea had the focus when the command ran");
  assert.equal((execSeen[0].selectionIn as El | undefined)?.tagName, "textarea", "...and the selection (what execCommand copies)");
  assert.equal(doc.body.children.some((c) => c.tagName === "textarea"), false, "the textarea never stays in the document");
  assert.equal(selection.rangeCount, 1, "one range stands again (before: the collapsed one the removal left, outside the passage)");
  assert.deepEqual([selection.ranges[0].start, selection.ranges[0].end], [[p, 3], [p, 9]], "the passage's own boundary points: what the person had selected");
  assert.deepEqual(ends(), [p, 3, p, 9], "...and its ends where they were");
  assert.notEqual(selection.ranges[0], before, "put back by its ends, not as the object the selection handed out (a selection's own Range follows the selection)");
  assert.deepEqual(selection.moves, ["select", "setBaseAndExtent"], "the textarea's select took the selection; the ends put it back");
  assert.equal(doc.activeElement, btn, "the Copy button holds the focus again (before: the body, once the focused textarea was removed)");
  assert.deepEqual(btn.focusCalls, [{ preventScroll: true }], "focused once, without scrolling the button into view");
});

test("a selection made right to left (its anchor after its focus) comes back right to left: the ends are put back, not a direction-less Range (before: forward, anchor and focus swapped)", async () => {
  reset();
  const { p, btn } = scene(true);
  assert.deepEqual(ends(), [p, 9, p, 3], "the passage runs backwards: anchor at 9, focus at 3");
  assert.equal(await copyText("x = 1\n"), true, "copied through the fallback");
  assert.equal((execSeen[0].selectionIn as El | undefined)?.tagName, "textarea", "the textarea held the selection when the command ran");
  assert.deepEqual([selection.ranges[0].start, selection.ranges[0].end], [[p, 3], [p, 9]], "the passage's boundary points");
  assert.deepEqual(ends(), [p, 9, p, 3], "the anchor at 9 and the focus at 3 still (before: 3 and 9, a Range put back through addRange, which runs forward)");
  assert.deepEqual(selection.moves, ["select", "setBaseAndExtent"], "put back by its ends");
  assert.equal(doc.activeElement, btn, "the focus back on the Copy button");
});

test("a refused command puts the selection and the focus back too, and the verdict is the command's", async () => {
  reset();
  const { p, btn } = scene(true);
  execResult = false;
  assert.equal(await copyText("y"), false, "the fallback failed, as the command said");
  assert.deepEqual([selection.ranges[0].start, selection.ranges[0].end], [[p, 3], [p, 9]]);
  assert.deepEqual(ends(), [p, 9, p, 3], "direction kept");
  assert.equal(doc.activeElement, btn);
});

test("with nothing selected the copy leaves nothing selected, and a body that held the focus is not focused again", async () => {
  reset();
  doc.body.appendChild(new El("p"));
  assert.equal(selection.rangeCount, 0); assert.equal(doc.activeElement, doc.body);
  assert.equal(await copyText("z"), true);
  assert.equal(selection.rangeCount, 0, "no range put back where none was (before: the collapsed one the removal left)");
  assert.deepEqual(selection.moves, ["select", "removeAllRanges"], "no ends to put back: the removal's collapsed range is cleared and nothing added");
  assert.equal(doc.activeElement, doc.body, "the body has the focus as before");
  assert.deepEqual(doc.body.focusCalls, [], "...and was not asked for it");
});

test("an engine without setBaseAndExtent puts the cloned Ranges back, forward, the direction a Range cannot carry", async () => {
  reset();
  const { p, btn } = scene(true);
  const had = selection.setBaseAndExtent; delete (selection as any).setBaseAndExtent;
  try {
    assert.equal(await copyText("v"), true, "copied");
    assert.deepEqual([selection.ranges[0].start, selection.ranges[0].end], [[p, 3], [p, 9]], "the passage's boundary points stand");
    assert.deepEqual(ends(), [p, 3, p, 9], "...forward: the API has no other way to put a Range back");
    assert.deepEqual(selection.moves, ["select", "removeAllRanges", "addRange"], "the Range route");
    assert.equal(doc.activeElement, btn);
  } finally { selection.setBaseAndExtent = had; }
});

test("a put-back of the ends the engine refuses falls to the cloned Ranges", async () => {
  reset();
  const { p } = scene(true);
  const had = selection.setBaseAndExtent;
  selection.setBaseAndExtent = () => { selection.moves.push("setBaseAndExtent"); throw new Error("IndexSizeError"); };
  try {
    assert.equal(await copyText("u"), true, "copied: the copy's verdict is the command's");
    assert.deepEqual([selection.ranges[0].start, selection.ranges[0].end], [[p, 3], [p, 9]], "the passage stands selected");
    assert.deepEqual(selection.moves, ["select", "setBaseAndExtent", "removeAllRanges", "addRange"], "the ends refused, the Ranges put back");
  } finally { selection.setBaseAndExtent = had; }
});

test("a document with no selection API (a stand-in, an old engine) copies as before and restores nothing", async () => {
  reset();
  const { btn } = scene();
  const w = (globalThis as any).window; const had = w.getSelection; delete w.getSelection;
  try {
    assert.equal(await copyText("w"), true, "copied");
    assert.equal(doc.activeElement, btn, "the focus is put back all the same");
  } finally { w.getSelection = had; }
});
