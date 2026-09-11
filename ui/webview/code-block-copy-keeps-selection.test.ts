// The Copy button's execCommand fallback leaves the page's selection and focus as it found them (code-block.ts fallbackCopy;
// the Slice 5 review of plans/markdown-viewer.md, round 6). The fallback runs when the async Clipboard API is missing (an
// insecure origin) or refuses: a textarea off screen takes the text, the focus and the selection, execCommand copies the
// selection, and the textarea is removed. Its focus and its select are the copy's moves, not the person's, and the removal
// left them as it found them: the document's selection collapsed outside whatever had been selected and the focus on the
// body, with no selectionchange the document hears. In the file viewer a passage stood with its Comment button beside it and
// nothing selected under the button, so a click on the button opened nothing (file-comments-copy-fallback-browser.test.ts
// shows it over the real viewer), and Space on a focused Copy button lost the keyboard's place. Now the selection's ranges
// are cloned before the textarea takes it and put back after (a clone: the Range a selection hands out is the selection's
// own and follows it), and the element that held the focus takes it back; a page with no selection keeps none, and a body
// that held the focus is left alone. Over a stand-in whose selection and focus move as a browser's do for the textarea trick:
// select() puts the textarea's range in the document's selection, the removal leaves a collapsed one elsewhere, focus() sets
// the active element. The Clipboard API is absent throughout (the fallback's own case). Synthetic values only.
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
    if (selection.ranges.some((r) => r.start[0] === c)) selection.ranges = [range(doc.body, 0, doc.body, 0)];
    if (doc.activeElement === c) doc.activeElement = doc.body;
    return c;
  }
  focus(opts?: { preventScroll?: boolean }): void { this.focusCalls.push(opts); doc.activeElement = this; }
  /** A textarea's select(): the document's selection moves to the textarea (the fallback's premise: execCommand copies the selection). */
  select(): void { selection.ranges = [range(this, 0, this, 1)]; }
}
type FakeRange = { start: [unknown, number]; end: [unknown, number]; cloneRange(): FakeRange };
const range = (sn: unknown, so: number, en: unknown, eo: number): FakeRange => ({ start: [sn, so], end: [en, eo], cloneRange() { return range(sn, so, en, eo); } });
const selection = {
  ranges: [] as FakeRange[],
  get rangeCount(): number { return selection.ranges.length; },
  getRangeAt(i: number): FakeRange { const r = selection.ranges[i]; if (!r) throw new Error("IndexSizeError"); return r; },
  removeAllRanges(): void { selection.ranges = []; },
  addRange(r: FakeRange): void { selection.ranges.push(r); },
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

const reset = (): void => { doc.body = new El("body"); doc.activeElement = doc.body; selection.ranges = []; execSeen.length = 0; execResult = true; };
/** A passage selected in a paragraph of the body, and a Copy button holding the focus (a click focuses a button; so does Tab). */
function scene(): { p: El; btn: El } {
  const p = doc.body.appendChild(new El("p")); const btn = doc.body.appendChild(new El("button"));
  selection.ranges = [range(p, 3, p, 9)];
  btn.focus(); btn.focusCalls.length = 0;
  return { p, btn };
}

test("the fallback copies from its textarea (the textarea held the focus and the selection when the command ran) and then puts the selection back, by its boundary points, and the focus back on the element that held it", async () => {
  reset();
  const { p, btn } = scene();
  const before = selection.ranges[0];
  assert.equal(await copyText("x = 1\n"), true, "copied through the fallback");
  assert.equal(execSeen.length, 1, "one command");
  assert.equal(execSeen[0].active?.tagName, "textarea", "the textarea had the focus when the command ran");
  assert.equal((execSeen[0].selectionIn as El | undefined)?.tagName, "textarea", "...and the selection (what execCommand copies)");
  assert.equal(doc.body.children.some((c) => c.tagName === "textarea"), false, "the textarea never stays in the document");
  assert.equal(selection.rangeCount, 1, "one range stands again (before: the collapsed one the removal left, outside the passage)");
  assert.deepEqual([selection.ranges[0].start, selection.ranges[0].end], [[p, 3], [p, 9]], "the passage's own boundary points: what the person had selected");
  assert.notEqual(selection.ranges[0], before, "a clone, not the object the selection handed out (a selection's own Range follows the selection)");
  assert.equal(doc.activeElement, btn, "the Copy button holds the focus again (before: the body, once the focused textarea was removed)");
  assert.deepEqual(btn.focusCalls, [{ preventScroll: true }], "focused once, without scrolling the button into view");
});

test("a refused command puts the selection and the focus back too, and the verdict is the command's", async () => {
  reset();
  const { p, btn } = scene();
  execResult = false;
  assert.equal(await copyText("y"), false, "the fallback failed, as the command said");
  assert.deepEqual([selection.ranges[0].start, selection.ranges[0].end], [[p, 3], [p, 9]]);
  assert.equal(doc.activeElement, btn);
});

test("with nothing selected the copy leaves nothing selected, and a body that held the focus is not focused again", async () => {
  reset();
  doc.body.appendChild(new El("p"));
  assert.equal(selection.rangeCount, 0); assert.equal(doc.activeElement, doc.body);
  assert.equal(await copyText("z"), true);
  assert.equal(selection.rangeCount, 0, "no range put back where none was (before: the collapsed one the removal left)");
  assert.equal(doc.activeElement, doc.body, "the body has the focus as before");
  assert.deepEqual(doc.body.focusCalls, [], "...and was not asked for it");
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
