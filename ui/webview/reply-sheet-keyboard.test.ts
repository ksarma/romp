// The todo Reply sheet on a phone with the keyboard up (the user 2026-09-19, screenshot): a todo's long detail filled
// the sheet and the answer box was ONE squeezed line above Cancel and Send. Two hand-maintained builders emit it,
// ui/webview/waiting.ts showReply (the Waiting pane) and ui/webview/render.ts showUserTodoReply (the chat), and what
// they SHARE is what the CSS keys on: the overlay #ut-reply-prompt (.picker-overlay.confirm-overlay) > the box
// .picker-box.confirm-box, a column flex box capped at the window, and inside it, in this order, .confirm-title, the
// quoted line .confirm-detail.ut-reply-quote, .ut-detail.open, textarea.ut-reply-input and .confirm-actions. The two
// trees are NOT the same (the maintainer's round 1 ruling): the pane appends the file and link chips as flex children
// of the box between the quoted line and the detail (.wt-file, .wt-link; waiting-pane.css says why), the chat puts
// them inside the quoted line (.ut-file, .ut-link; styles.css's #ut-reply-prompt .ut-link rule says why), so the two
// columns have different headroom under the same rules, and every browser leg measures both with the chips present
// (waiting-reply-sheet-browser.test.ts, render-reply-sheet-browser.test.ts; tests/test_reply_sheet_served.py reads
// both real trees in CI). The skeleton pin below keeps the shared part shared and the divergence exactly the chips.
// Every child is a shrinkable flex item; a wrapped text block's automatic minimum (min-height: auto) refuses to shrink
// and the textarea's (overflow auto) resolves to zero, so the box took the whole deficit and the cap clipped rather
// than scrolled.
//
// The fix rides the picker's existing fold and touches no shared rule (.confirm-box and .picker-box serve seven
// dialogs). Five CSS rules scoped to this dialog: the answer box never shrinks and holds three rows (min-height in
// lh); the detail is the part that gives way, capped and scrolling within itself (overflow-y: auto makes it a scroll
// container, whose automatic flex minimum is zero; #pinned-notes is the precedent) down to a floor of two of its lines
// (the picker's list keeps one row under the fold for the same reason: a region that gives way never gives way to
// nothing); a short window pins the sheet to the top under the picker's 12px frame; the box scrolls at every height, the
// backstop for a window the floors alone overflow; and there the actions row is kept in view at the box's bottom, so Send
// stays inside the clip, while grow keeps the answer box clear of that row (the maintainer's round 2 ruling, B-i). In each builder one closure, kbFit, toggles kb-tight
// on THIS window's own resize (the shell sizes the pane iframe to the visible height, so the keyboard opening or
// closing IS a resize here; render.ts's picker keys on the same event, at the same 480px), re-runs restCap (the
// detail's cap at rest, the maintainer's ruling at the merge with main: with the keyboard down the cap is the larger of
// 12em and 34.8% of the window's height, which restCap publishes on the overlay; with the keyboard up, read as
// the shell's kbOpen reads it on the parent window, it withdraws it and the cap is 12em) and re-runs grow, and
// close() removes the listener, which also removes itself when the overlay was replaced by a second Reply; grow lets
// the box follow the answer up to the room the box has left, never under the three-row floor, and stands down for a
// height the person dragged (file-comments.ts autosize's guard); on the resize path (kbFit's grow(true)) that height is
// the person's preference, clamped to the room and returned toward when the room comes back, never re-fit to the
// content (the author's pass after the maintainer's round 1, composition-3). The backdrop's click dismisses only when the
// whole gesture was on the backdrop, press and release both, recorded per pointer: a click whose press began inside the
// sheet (a grip pull or a text selection released past the box's edge) is not a backdrop tap (the author's pass after the
// maintainer's round 1, composition-2, and the reviewer's ruling on the selection), and neither is a click whose release
// landed inside it (a press on the backdrop released inside the sheet, the maintainer's round 2), nor a click that no
// release of its own pointer preceded (a chorded mouse) or that ends a drag out of the sheet while another pointer rests on
// the backdrop (the maintainer's focused re-check of round 2); the release is read where the pointer lifted, since a
// backdrop press gives back the implicit capture a touch pointer takes (the backdrop's six lines, the capture's release
// among them, are executed below out of each builder).
//
// Two kinds of leg, no browser (the browser legs are waiting-reply-sheet-browser.test.ts and
// render-reply-sheet-browser.test.ts). The executed legs slice the fold's lines and the grow handler out of EACH
// builder's source (the waiting-reply-focus.test.ts idiom) and run them against stand-ins: the overlay is the shared
// shim's node (ui/test-dom-shim.ts nodeFactory; its isConnected is its tree's own answer), the window a
// listener-recording EventTarget stand-in with an innerHeight and no DOM edge, the answer box and the sheet's box
// shim nodes whose geometry is the test's input. The source legs pin the five rules' declared properties (read with
// the sheet's comments stripped) and that no rule of the fix adds a font-size (ui/CLAUDE.md), and that the picker's
// own fold strings stand as picker-keyboard.test.ts pins them. Synthetic only: no fixture text.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { nodeFactory } from "../test-dom-shim";

const UI = path.resolve(process.cwd(), "..", "ui", "webview");   // npm test runs in vscode-extension
const WAITING = fs.readFileSync(path.join(UI, "waiting.ts"), "utf8");
const RENDER = fs.readFileSync(path.join(UI, "render.ts"), "utf8");
const CSS = fs.readFileSync(path.join(UI, "styles.css"), "utf8");
const BUILDERS: Array<[string, string]> = [
  ["waiting.ts showReply", WAITING.slice(WAITING.indexOf("function showReply("), WAITING.indexOf("// ── render"))],
  ["render.ts showUserTodoReply", RENDER.slice(RENDER.indexOf("function showUserTodoReply("), RENDER.indexOf("// ── COMMENT THREADS"))],
];
for (const [name, src] of BUILDERS) assert.ok(src.length > 200, name + ": the builder's slice was found");

// one line of a builder, by a regex that must hit exactly once
function line(src: string, re: RegExp, what: string, name: string): string {
  const m = src.match(re);
  assert.ok(m, what + " not found in " + name + ": re-anchor");
  return m![0];
}
const KBFIT = /^\s*const kbFit = .*$/m;
const RESTCAP = /^\s*const restCap = .*$/m;   // the detail's cap at rest: the window's height published on the overlay with the keyboard down
const CLOSE = /^\s*const close = .*$/m;
const KB_ARM = /window\.addEventListener\("resize", kbFit\);\n\s*kbFit\(\);/;
const GROW_ARM = /input\.addEventListener\("input", \(\) => grow\(\)\);/;   // the keystroke path: grow with no argument (kbFit's resize path is grow(true))
// the backdrop's click and what it reads, recorded per pointer: the pointers whose press began on the backdrop and the pending
// tap; the press listener, which clears any pending tap, notes a backdrop press (and gives back its pointer capture) and
// forgets a press inside; the release listener, which marks a tap pending when that pointer's press and release were both on
// the backdrop; the cancel listener, which forgets a cancelled pointer; and the click line
const PRESS_RECORD = /^\s*const backdropPress = new Set\(\);.*$/m;
const TAP_RECORD = /^\s*let tapPending = false;.*$/m;
const PRESS_ARM = /^\s*overlay\.addEventListener\("pointerdown", .*$/m;
const RELEASE_ARM = /^\s*overlay\.addEventListener\("pointerup", .*$/m;
const CANCEL_ARM = /^\s*overlay\.addEventListener\("pointercancel", .*$/m;
const DISMISS = /^\s*overlay\.addEventListener\("click", .*$/m;
const BACKDROP: Array<[string, RegExp]> = [["the press record", PRESS_RECORD], ["the pending tap", TAP_RECORD], ["the press listener", PRESS_ARM], ["the release listener", RELEASE_ARM], ["the cancel listener", CANCEL_ARM], ["the backdrop's click", DISMISS]];
// the six lines as one body, each by its own anchor (a missing one is a loud re-anchor failure)
const backdropLines = (src: string, name: string): string => BACKDROP.map(([what, re]) => line(src, re, what, name)).join("\n");
// the grow handler is a BLOCK (its records, its head, its statements, the `};` that closes it), sliced whole; a builder
// whose head or close moved is a loud failure here
const GROW_HEAD = "\n  const grow = (resized = false) => {\n";   // resized: kbFit's path, where a dragged height is clamped to the room
function growBlock(src: string, name: string): string {
  const head = src.indexOf("\n  let sizedTo = \"\";");   // the drag guard's record, declared right above the handler
  assert.ok(head >= 0, "the grow block's head (let sizedTo) not found in " + name + ": re-anchor");
  assert.ok(src.indexOf(GROW_HEAD, head) > head && src.indexOf(GROW_HEAD, head) < head + 400, name + ": the grow handler follows its sizedTo and pref lines");
  const end = src.indexOf("\n  };\n", head);
  assert.ok(end > head, "the grow block's close not found in " + name + ": re-anchor");
  return src.slice(head + 1, end + "\n  };".length);
}

// an EventTarget stand-in for the window: listeners by type, every removal recorded, one type fired at a time; the
// dispatch walks a COPY of the set, as the DOM does, so a listener that removes itself mid-dispatch runs to its end.
// innerHeight is the test's input. No DOM edge on it, so it is not a hideEdges caller (the ratchet's rule)
class Win {
  innerHeight = 900;
  private byType = new Map<string, Set<(...a: unknown[]) => void>>();
  removed: Array<[string, unknown]> = [];
  addEventListener(type: string, fn: (...a: unknown[]) => void): void { (this.byType.get(type) ?? this.byType.set(type, new Set()).get(type)!).add(fn); }
  removeEventListener(type: string, fn: (...a: unknown[]) => void): void { this.byType.get(type)?.delete(fn); this.removed.push([type, fn]); }
  count(type: string): number { return this.byType.get(type)?.size ?? 0; }
  fire(type: string): void { for (const fn of [...(this.byType.get(type) ?? [])]) fn(); }
}
const makeNode = nodeFactory();

// ── the fold, executed out of each builder ───────────────────────────────────────────────────────
type Fold = { kbFit: () => void; close: () => void };
// the kbFit line, the close line and the arming lines, run with the names they read handed in: the overlay (a shim
// node under a body, so isConnected is the tree's answer), the window stand-in, stand-ins for the other names the
// close line removes (onKey, onFocus) and the document it removes them from, and grow, the answer box's handler kbFit
// re-runs on the same resize (the room the box has left changes with the window), as a counter
function fold(name: string, src: string, overlay: unknown, win: Win): Fold & { doc: Win; grown: () => number; calls: string[] } {
  const doc = new Win();
  let grown = 0;
  const calls: string[] = [];   // restCap and grow, in the order kbFit calls them
  const grow = () => { grown++; calls.push("grow"); };
  const restCap = () => { calls.push("restCap"); };   // the detail's cap at rest, executed on its own below
  const body = line(src, KBFIT, "the kbFit line", name) + "\n" + line(src, CLOSE, "the close line", name) + "\n" + line(src, KB_ARM, "the arming lines", name) + "\nreturn { kbFit, close };";
  const onKey = () => { /* the modal's Escape handler, by reference only */ };
  const onFocus = () => { /* waiting.ts's focus-return listener, by reference only */ };
  const r = new Function("overlay", "window", "document", "onKey", "onFocus", "grow", "restCap", body)(overlay, win, doc, onKey, onFocus, grow, restCap) as Fold;
  return { ...r, doc, grown: () => grown, calls };
}
function world() {
  const body = makeNode("body"), overlay = makeNode("div");
  body.appendChild(overlay);
  Object.defineProperty(overlay, "isConnected", { get: () => overlay.parentNode === body, configurable: true });
  return { body, overlay, win: new Win(), tight: () => overlay.classList.contains("kb-tight") as boolean };
}

for (const [name, src] of BUILDERS) {
  test(`${name}: kb-tight follows this window's height: on under 480px at open and on every resize, off again with the room back`, () => {
    const w = world();
    w.win.innerHeight = 420;   // the keyboard already up when Reply is tapped
    const f = fold(name, src, w.overlay, w.win);
    assert.equal(w.win.count("resize"), 1, "one resize listener armed");
    assert.equal(w.tight(), true, "synced at open: a short window folds before any resize");
    assert.equal(f.grown(), 1, "the open's own kbFit() fits the answer box once: the room is read with the box in the document");
    w.win.innerHeight = 900; w.win.fire("resize");
    assert.equal(w.tight(), false, "the keyboard down (or a tall screen): the fold comes off on the same event");
    assert.equal(f.grown(), 2, "the same resize re-fits the answer box: its cap is the room, which the window's height changes");
    w.win.innerHeight = 479; w.win.fire("resize");
    assert.equal(w.tight(), true, "479px is short: the picker's threshold, shared");
    w.win.innerHeight = 480; w.win.fire("resize");
    assert.equal(w.tight(), false, "480px is not");
    assert.equal(f.grown(), 4, "one grow per resize while the modal is up");
    assert.deepEqual(f.calls, ["restCap", "grow", "restCap", "grow", "restCap", "grow", "restCap", "grow"], "each fit re-reads the keyboard for the detail's cap at rest, then grows: the room grow reads is the room under the cap restCap just set");
    assert.equal(w.win.count("resize"), 1, "the listener stays for the next resize while the modal is up");
    assert.equal(w.overlay.isConnected, true, "the fold never removes the modal");
  });

  test(`${name}: close() removes the resize listener by the reference it added, with the Escape handler; a later resize toggles nothing`, () => {
    const w = world();
    w.win.innerHeight = 420;
    const f = fold(name, src, w.overlay, w.win);
    assert.equal(w.tight(), true);
    f.close();
    assert.equal(w.overlay.isConnected, false, "the overlay left the document (the shim's remove, off its body)");
    assert.equal(w.win.count("resize"), 0, "the resize listener went with the modal");
    const resizeRemovals = w.win.removed.filter(([t]) => t === "resize");
    assert.equal(resizeRemovals.length, 1, "one removal of a resize listener");
    assert.equal(resizeRemovals[0][1] === f.kbFit, true, "removed under the reference it was added under");
    assert.deepEqual(f.doc.removed.map(([t]) => t), ["keydown"], "the Escape handler is removed in the same close");
    w.win.innerHeight = 900; w.win.fire("resize");
    assert.equal(w.tight(), true, "nothing runs after the close: the class is as the last live toggle left it");
  });

  test(`${name}: the overlay removed some other way (a second Reply replacing this one): the next resize drops the listener and toggles nothing`, () => {
    const w = world();
    w.win.innerHeight = 900;
    const f = fold(name, src, w.overlay, w.win);
    assert.equal(w.tight(), false);
    w.body.removeChild(w.overlay);   // the replacing builder's getElementById(...)?.remove(), not this modal's close()
    assert.equal(w.overlay.isConnected, false);
    w.win.innerHeight = 420; w.win.fire("resize");
    assert.equal(w.tight(), false, "a modal that is gone is not folded");
    assert.equal(f.grown(), 1, "and its answer box is not re-fitted: only the open's own fit is on record");
    assert.equal(w.win.count("resize"), 0, "the listener removed itself");
    assert.deepEqual(w.win.removed.map(([t, fn]) => [t, fn === f.kbFit]), [["resize", true]], "by its own reference");
    w.win.fire("resize");
    assert.equal(w.win.removed.length, 1, "and nothing runs on the resize after that");
    assert.deepEqual(f.doc.removed, [], "close() never ran: the Escape handler is still the document's");
  });
}

// ── the detail's cap at rest, executed out of each builder ───────────────────────────────────────
// restCap publishes THIS window's height (innerHeight) on the overlay (--ut-rest-h) with the keyboard down, which
// styles.css's max(12em, calc(0.348 * var(--ut-rest-h, 0px))) turns into the cap at rest, and removes it with the keyboard
// up, where the cap is 12em (the maintainer's ruling at the merge with main). The keyboard is the parent window's visual
// viewport more than 120px shorter than its layout viewport (kernel.py kbOpen's test, on the window that owns the screen:
// inside the shell the pane's own two heights agree whatever the keyboard does). Run against stand-ins: the overlay's
// style records every setProperty and removeProperty, the window carries an innerHeight, a visualViewport of its own
// (which restCap does not read: a pinch zoom shrinks it and must leave the cap alone) and a parent, the parent its own
// innerHeight and visualViewport
function restCapper(name: string, src: string, overlay: unknown, win: unknown): () => void {
  return new Function("overlay", "window", line(src, RESTCAP, "the restCap line", name) + "\nreturn restCap;")(overlay, win) as () => void;
}
for (const [name, src] of BUILDERS) {
  test(`${name}: restCap publishes the window's height for the detail's cap at rest and withdraws it with the keyboard up, read on the parent window as the shell's kbOpen reads it`, () => {
    const props = new Map<string, string>();
    const log: string[] = [];
    const overlay = { style: {
      setProperty: (k: string, v: string) => { props.set(k, v); log.push("set " + k + " " + v); },
      removeProperty: (k: string) => { props.delete(k); log.push("remove " + k); return ""; },
    } };
    const shell = { innerHeight: 844, visualViewport: { height: 844, scale: 1 } };
    const win: any = { innerHeight: 800, visualViewport: { height: 800, scale: 1 }, parent: shell };
    const restCap = restCapper(name, src, overlay, win);
    // the keyboard down: the shell's two heights agree, and the pane's own height is published
    restCap();
    assert.equal(props.get("--ut-rest-h"), "800px", "at rest: THIS window's height (the pane's, not the shell's), for styles.css's 34.8% term");
    // the pane's own visual viewport is not what is published: a pinch zoom that halves it leaves the published height alone
    win.visualViewport.height = 400; win.visualViewport.scale = 2;
    restCap();
    assert.equal(props.get("--ut-rest-h"), "800px", "a pinch zoom shrinks only the visual viewport: the window's height, and so the cap, stay");
    win.visualViewport.height = 800; win.visualViewport.scale = 1;
    // the keyboard up: the shell's visual viewport is 336px shorter than its layout viewport, and the pane was resized to 508
    shell.visualViewport.height = 508; win.innerHeight = 508; win.visualViewport.height = 508;
    restCap();
    assert.equal(props.has("--ut-rest-h"), false, "keyboard up: the property is withdrawn, so the term is 0px and the cap is 12em, the head's (no viewport term enters)");
    // the threshold is the shell's: more than 120px
    shell.visualViewport.height = 724;   // 844 - 120
    restCap();
    assert.equal(props.get("--ut-rest-h"), "508px", "120px shorter is not the keyboard (kbOpen's > 120)");
    shell.visualViewport.height = 723;
    restCap();
    assert.equal(props.has("--ut-rest-h"), false, "121px shorter is");
    // a pinch zoom on the shell shrinks its visual viewport by its scale: height times scale is the layout's again, not a keyboard
    shell.visualViewport.height = 422; shell.visualViewport.scale = 2;
    restCap();
    assert.equal(props.get("--ut-rest-h"), "508px", "a 2x pinch on the shell (422 x 2 = 844) is not the keyboard");
    // standalone: the parent is this window itself, and its own two heights decide
    const alone: any = { innerHeight: 900, visualViewport: { height: 900, scale: 1 } }; alone.parent = alone;
    const restCapAlone = restCapper(name, src, overlay, alone);
    restCapAlone();
    assert.equal(props.get("--ut-rest-h"), "900px", "standalone at rest");
    alone.visualViewport.height = 564;
    restCapAlone();
    assert.equal(props.has("--ut-rest-h"), false, "standalone with the keyboard up (a top-level page's visual viewport shrinks, its layout viewport does not)");
    // a cross-origin host (a VS Code webview): reading the parent throws, read as no keyboard
    const hosted: any = { innerHeight: 700, visualViewport: { height: 700, scale: 1 } };
    const denied = { get innerHeight(): number { throw new Error("SecurityError"); }, get visualViewport(): unknown { throw new Error("SecurityError"); } };
    Object.defineProperty(hosted, "parent", { get: () => denied });
    restCapper(name, src, overlay, hosted)();
    assert.equal(props.get("--ut-rest-h"), "700px", "a cross-origin parent throws: no keyboard, the cap at rest");
    // an engine with no visualViewport: no keyboard
    const bare: any = { innerHeight: 600, visualViewport: null }; bare.parent = bare;
    restCapper(name, src, overlay, bare)();
    assert.equal(props.get("--ut-rest-h"), "600px", "no visualViewport: no keyboard, this window's height");
    assert.ok(log.every((l) => /^(set --ut-rest-h \d+px|remove --ut-rest-h)$/.test(l)), "restCap writes one property and nothing else: " + JSON.stringify(log));
  });
}
// A STATED RESIDUAL of the keyboard-up ruling (the maintainer's ruling on the cap pass), pinned as it is so a change to it
// is seen: Android Chrome honours the shell's interactive-widget=resizes-content (kernel.py's viewport meta; iOS ignores
// it), so the keyboard shrinks the shell's LAYOUT viewport with its visual one, the two agree, and restCap, reading the
// shell as kbOpen does, sees no keyboard: the pane's height stays published and the at-rest term applies under the
// keyboard. The browser half is waiting-reply-sheet-browser.test.ts (the pane in a frame inside a shell page whose layout
// viewport shrinks with the keyboard: at 508 the cap is 177px and the room sets the detail)
for (const [name, src] of BUILDERS) {
  test(`${name}: under Android Chrome's resizes-content the keyboard shrinks the shell's layout viewport too, so restCap sees no keyboard and keeps the pane's height published (a stated residual)`, () => {
    const props = new Map<string, string>();
    const overlay = { style: {
      setProperty: (k: string, v: string) => { props.set(k, v); },
      removeProperty: (k: string) => { props.delete(k); return ""; },
    } };
    const shell = { innerHeight: 844, visualViewport: { height: 844, scale: 1 } };
    const win: any = { innerHeight: 844, visualViewport: { height: 844, scale: 1 }, parent: shell };
    const restCap = restCapper(name, src, overlay, win);
    restCap();
    assert.equal(props.get("--ut-rest-h"), "844px", "at rest, the keyboard down: the pane's height is published");
    // the keyboard opens under resizes-content: the shell's layout and visual viewports shrink together, and the shell sizes
    // the pane to what is left
    shell.innerHeight = 508; shell.visualViewport.height = 508; win.innerHeight = 508; win.visualViewport.height = 508;
    restCap();
    assert.equal(props.get("--ut-rest-h"), "508px", "under resizes-content the shell's two heights agree, so restCap sees no keyboard and the term stays: the cap is 34.8% of 508 (177px), not 12em. Today's behaviour, disclosed at restCap and in the ledger entry; a keyboard signal that survives resizes-content turns this red, and is a design of its own (the shell's kbOpen has the same blind spot)");
  });
}

// ── the grow handler, executed out of each builder ───────────────────────────────────────────────
// the textarea as the handler reads it: a shim node whose geometry is the test's input (offsetHeight is the border-box
// height the browser lays out for the current inline height, clientHeight the same less the border, scrollHeight the
// content's); every write to style.height is recorded, in order
function inputNode(geom: { offset: number; client: number; scroll: number }) {
  const input = makeNode("textarea");
  const writes: string[] = [];
  Object.defineProperty(input.style, "height", { get: () => writes[writes.length - 1] ?? "", set: (v: string) => { writes.push(String(v)); }, configurable: true });
  Object.defineProperty(input, "offsetHeight", { get: () => geom.offset, configurable: true });
  Object.defineProperty(input, "clientHeight", { get: () => geom.client, configurable: true });
  Object.defineProperty(input, "scrollHeight", { get: () => geom.scroll, configurable: true });
  // the writes since the last mark: the list is never cleared, because style.height READS the last write and the handler's
  // drag guard compares that read with what it wrote last (a cleared list would read as a drag)
  let mark = 0;
  return { input, writes, geom, mark: () => { mark = writes.length; }, fresh: () => writes.slice(mark) };
}
// the box (.picker-box.confirm-box) as the handler reads it: its scroll height against its client height is the content
// past the cap, the room the answer does not have; a stand-in whose two numbers are the test's input. The handler writes
// the wanted height FIRST and reads the box after it, so a stand-in that answers a fixed overflow models a box whose
// content, with the answer at that height, runs `over` past its cap
function boxNode(geom: { scroll: number; client: number }) {
  const box = makeNode("div");
  Object.defineProperty(box, "scrollHeight", { get: () => geom.scroll, configurable: true });
  Object.defineProperty(box, "clientHeight", { get: () => geom.client, configurable: true });
  return { box, geom };
}
// the actions row (.confirm-actions, kept in view at the box's bottom: styles.css #ut-reply-prompt .confirm-actions) as the
// handler reads it: a shim node whose rect is the test's input; by default the shim's flat rect, level with the answer box's,
// so the answer box is never under it and the handler leaves the box's scroll alone
function grower(name: string, src: string, input: unknown, box: unknown, win: Win, actions: unknown = makeNode("div")): () => void {
  const body = growBlock(src, name) + "\n" + line(src, GROW_ARM, "the grow arming line", name) + "\nreturn grow;";
  return new Function("input", "box", "window", "actions", body)(input, box, win, actions) as () => void;
}

for (const [name, src] of BUILDERS) {
  test(`${name}: the box grows with the answer from height auto, to the content's height plus the border; never under the three-row floor; capped at the ROOM the box has left, read from the box`, () => {
    // laid out at height auto the box is its floor: three rows of text, the padding and the 1px borders (78px of
    // border-box; 76px inside the border); the sheet's box fits its content (no overflow)
    const g = inputNode({ offset: 78, client: 76, scroll: 76 });
    const b = boxNode({ scroll: 400, client: 400 });
    const win = new Win(); win.innerHeight = 900;
    const grow = grower(name, src, g.input, b.box, win);
    assert.equal(typeof g.input._listeners.input, "function", "armed on the box's input event (the listener calls grow with no argument, the keystroke path; kbFit calls grow(true), the resize path, executed below)");
    g.input._listeners.input({ type: "input" });
    assert.deepEqual(g.fresh(), ["auto", "78px"], "measured at auto first, then the floor: an empty box is three rows");
    // a long answer: the content's scroll height plus the border a border-box height carries (the composer's growComposer
    // reads scrollHeight the same way; the border is what a bare scrollHeight would leave as a one-line scroll)
    g.mark(); g.geom.scroll = 200;
    grow();
    assert.deepEqual(g.fresh(), ["auto", "202px"], "grows to the content: 200px of content and padding plus the 2px of border; the box fit it, so the wanted height stands");
    // the cap is the room: with the answer at its content's height the box runs past its own cap, and the answer gives
    // exactly that overflow back, so Cancel and Send end at the box's bottom edge, inside its clip
    g.mark(); g.geom.scroll = 5000; b.geom.scroll = 5300; b.geom.client = 400;
    grow();
    assert.deepEqual(g.fresh(), ["auto", "5002px", (5002 - 4900) + "px"], "the wanted height written, the box's 4900px of overflow read, and the height is the wanted less the overflow: the room");
    // the room does not go under the floor: a box whose fixed rows alone overflow keeps three rows (the box itself scrolls,
    // styles.css's every-height backstop; that is the browser legs' measurement, not this harness's)
    g.mark(); b.geom.scroll = 5390;
    grow();
    assert.deepEqual(g.fresh(), ["auto", "5002px", "78px"], "5002 less 4990 is 12px, under the floor: the floor stands");
    // the window's height is not what caps the answer: the same box overflow at another window gives the same height
    g.mark(); win.innerHeight = 150;
    grow();
    assert.deepEqual(g.fresh(), ["auto", "5002px", "78px"], "a 150px window changes nothing here: the box's own overflow is the input, never window.innerHeight");
    assert.doesNotMatch(growBlock(src, name), /window\.innerHeight|innerHeight \* 0\.4/, name + ": the handler reads no share of the window");
    // the floor is read from the layout, not a constant: a larger font lays out a taller floor and the handler follows
    g.mark(); g.geom.offset = 100; g.geom.client = 98; g.geom.scroll = 98; b.geom.scroll = 400; win.innerHeight = 900;
    grow();
    assert.deepEqual(g.fresh(), ["auto", "100px"], "the floor is whatever height auto laid out");
    // a box with no layout to measure (a fake DOM, a display:none box) keeps what stood: nothing new is written past the
    // measuring auto, as file-comments.ts autosizeComposer stands down when the scroll height reads 0
    g.mark(); g.geom.offset = 0; g.geom.client = 0; g.geom.scroll = 0;
    grow();
    assert.deepEqual(g.fresh(), ["auto", "100px"], "no layout: the measuring auto, then what stood put back");
    // THE DRAG GUARD (file-comments.ts autosize's): the textarea keeps resize: vertical, and a drag writes the inline height
    // and fires no input, so the handler knows a drag as an inline height that is not what it last wrote; the next
    // keystroke writes nothing and the person's height stands until the sheet closes
    g.mark(); g.geom.offset = 78; g.geom.client = 76; g.geom.scroll = 76;
    grow();
    assert.deepEqual(g.fresh(), ["auto", "78px"], "back at the floor, on record");
    g.mark(); g.writes.push("150px");   // the drag, as the browser serializes it
    g.geom.scroll = 300;
    grow();
    assert.deepEqual(g.fresh(), ["150px"], "dragged since the last write: the handler stands down, the 150px stands (before the guard a keystroke snapped it back to the content's height)");
    grow();
    assert.deepEqual(g.fresh(), ["150px"], "and on every keystroke after");
    // dragged BEFORE the first keystroke: nothing on record yet, an inline height already there
    const g2 = inputNode({ offset: 78, client: 76, scroll: 200 }); g2.writes.push("120px");
    const grow2 = grower(name, src, g2.input, boxNode({ scroll: 400, client: 400 }).box, win);
    grow2();
    assert.deepEqual(g2.writes, ["120px"], "dragged before the first write: the handler stands down too (the case the second comparison alone cannot see)");
  });
}

// ── the dragged height as a preference, executed out of each builder ─────────────────────────────
// A height the person dragged stands against typing (F's guard, above). On the resize path, kbFit's grow(true), it is
// their PREFERENCE (the author's pass after the maintainer's round 1, composition-3): the keyboard opening clamps the box
// to min(preference, room), never under the floor, so Send stays inside the clip; the keyboard closing returns the box
// toward the preference, up to it and never past; and neither path re-fits the box to its content while a preference
// stands. Before: a box dragged to 215px at 900 kept 215px under the keyboard, the box overflowed its cap by about 130px
// and Send lay below the frame (the browser legs and tests/test_reply_sheet_served.py measure the real sheet)
for (const [name, src] of BUILDERS) {
  test(`${name}: on the resize path a dragged height is a preference clamped to the room, returned toward when the room comes back, never re-fit to the content`, () => {
    const g = inputNode({ offset: 78, client: 76, scroll: 76 });
    const b = boxNode({ scroll: 400, client: 400 });
    const win = new Win(); win.innerHeight = 900;
    const grow = grower(name, src, g.input, b.box, win) as (resized?: boolean) => void;
    grow();
    assert.deepEqual(g.fresh(), ["auto", "78px"], "an empty box at the floor, on record");
    // the drag, as the browser serializes it, then a resize with the box fitting (900): the preference stands, written as such
    g.mark(); g.writes.push("215px");
    grow(true);
    assert.deepEqual(g.fresh(), ["215px", "auto", "215px"], "the room holds the dragged height: the resize writes the preference itself");
    // the keyboard opens: with the answer at 215px the box runs 132px past its cap, and the box is clamped to the room, never
    // re-fit to the content (the content is the floor here: a re-fit would write 78px)
    g.mark(); b.geom.scroll = 532; b.geom.client = 400;
    grow(true);
    assert.deepEqual(g.fresh(), ["auto", "215px", "83px"], "clamped to the room: the preference written, the box's 132px of overflow read, and the height is the preference less the overflow (before the clamp the dragged height stood through the resize)");
    // typing under the clamp: the handler stands down (F's guard), the clamped height is not re-fit to the content
    g.mark(); g.geom.scroll = 300;
    grow();
    assert.deepEqual(g.fresh(), [], "a keystroke under the clamp writes nothing: the dragged height stands against typing, clamped or not");
    // the keyboard closes: the box returns to the preference, not stuck at the clamp
    g.mark(); b.geom.scroll = 400;
    grow(true);
    assert.deepEqual(g.fresh(), ["auto", "215px"], "the room back, the box returns to the preference (before, nothing returned it: a clamped height stood until the sheet closed)");
    // a later drag is the new preference, clamped the same way
    g.mark(); g.writes.push("180px"); b.geom.scroll = 497;
    grow(true);
    assert.deepEqual(g.fresh(), ["180px", "auto", "180px", "83px"], "a later drag replaces the preference: 180px, clamped by the 97px overflow the box then has");
    g.mark(); b.geom.scroll = 400;
    grow(true);
    assert.deepEqual(g.fresh(), ["auto", "180px"], "and the room back returns to the new preference, not the old one");
    // the clamp never goes under the floor: a box whose fixed rows alone overflow keeps three rows (the box itself scrolls)
    g.mark(); b.geom.scroll = 600;
    grow(true);
    assert.deepEqual(g.fresh(), ["auto", "180px", "78px"], "180 less 200 is under the floor: the floor stands");
    // no layout to measure: what stood is put back, the preference kept for the next resize
    g.mark(); g.geom.offset = 0; g.geom.client = 0;
    grow(true);
    assert.deepEqual(g.fresh(), ["auto", "78px"], "no layout: the measuring auto, then what stood put back");
    g.mark(); g.geom.offset = 78; g.geom.client = 76; b.geom.scroll = 400;
    grow(true);
    assert.deepEqual(g.fresh(), ["auto", "180px"], "the preference survived the no-layout call");
    // a preference under the floor is the floor
    g.mark(); g.writes.push("40px");
    grow(true);
    assert.deepEqual(g.fresh(), ["40px", "auto", "78px"], "a dragged height under the floor lays out at the floor, and the handler writes the floor");
    // without a drag the resize path is the content fit, unchanged
    const g2 = inputNode({ offset: 78, client: 76, scroll: 200 });
    const grow2 = grower(name, src, g2.input, boxNode({ scroll: 400, client: 400 }).box, win) as (resized?: boolean) => void;
    grow2(true);
    assert.deepEqual(g2.writes, ["auto", "202px"], "no drag: the resize path fits the content, as the room case above");
  });
}

// ── the answer box kept clear of the kept row, executed out of each builder ─────────────────────
// Where the floors alone overflow the box (the keyboard up with a long ask, both chips, a narrow phone), the box scrolls and
// styles.css keeps the actions row in view at its bottom (#ut-reply-prompt .confirm-actions, sticky), so Cancel and Send stay
// inside the box's clip and a finger on Send sends (the maintainer's round 2 ruling, B-i: at a6e7f1cfa Send lay past the clip
// in those states and a tap at its centre closed the sheet with the answer). The kept row paints over what the box scrolls
// under it, and the answer box must not be that: grow's last line scrolls the box to its end when the box overflows and the
// answer box's bottom lies under the row's top, where the answer box sits just above the row (without the line the row covered
// the line being typed by up to about 20px, measured by refuter 2 and the ruling). The browser legs measure the real layout
// (the typed row clear of the row, Send inside the clip and sending, in three engines); this runs the line against stand-ins
for (const [name, src] of BUILDERS) {
  test(`${name}: with the box overflowing, grow scrolls the box to its end when the answer box's bottom lies under the kept actions row, and leaves the box's scroll alone otherwise`, () => {
    const g = inputNode({ offset: 78, client: 76, scroll: 76 });
    const b = boxNode({ scroll: 400, client: 400 });
    const scrolls: number[] = [];   // every write to the box's scrollTop, in order
    Object.defineProperty(b.box, "scrollTop", { get: () => scrolls[scrolls.length - 1] ?? 0, set: (v: number) => { scrolls.push(Number(v)); }, configurable: true });
    const rect = (top: number, bottom: number) => ({ top, bottom, left: 20, right: 360, width: 340, height: bottom - top, x: 20, y: top });
    const actions = makeNode("div"); actions._rect = rect(300, 331);
    const grow = grower(name, src, g.input, b.box, new Win(), actions) as (resized?: boolean) => void;
    // the box fits its cap: nothing to keep clear, whatever the rects say
    g.input._rect = rect(240, 318);
    grow();
    assert.deepEqual(scrolls, [], "the box fits (400 of 400px): grow leaves its scroll alone, even with the answer box's rect under the row's");
    // the box overflows and the answer box ends above the row: nothing is covered, the scroll stays
    b.geom.scroll = 460; g.input._rect = rect(200, 290);
    grow();
    assert.deepEqual(scrolls, [], "overflowing, the answer box's bottom (290) above the row's top (300): the scroll stays where the person or the engine left it");
    // level with the row's top is not under it
    g.input._rect = rect(222, 300);
    grow();
    assert.deepEqual(scrolls, [], "the answer box's bottom level with the row's top is not under it");
    // the box overflows and the answer box's bottom lies under the row: scrolled to the box's end
    g.input._rect = rect(240, 318);
    grow();
    assert.deepEqual(scrolls, [460], "overflowing, the answer box's bottom (318) under the row's top (300): the box is scrolled to its end, its scroll height, where the answer box sits just above the row");
    // the resize path (kbFit's grow(true)) does the same
    grow(true);
    assert.deepEqual(scrolls, [460, 460], "and on the resize path: a keyboard opening under an answer already grown keeps the answer box clear of the row too");
    // a dragged height stands against typing: the keystroke path returns before the line, so a keystroke moves nothing
    g.writes.push("150px");
    grow();
    assert.deepEqual(scrolls, [460, 460], "a keystroke after a drag writes nothing and scrolls nothing (the drag guard returns first)");
    // on the resize path the dragged height is clamped to the room and the line runs after the clamp
    grow(true);
    assert.deepEqual(scrolls, [460, 460, 460], "the resize path clamps a dragged height to the room, then keeps the answer box clear of the row");
    // the line reads the two rects and the box's two heights, nothing of the window
    assert.match(growBlock(src, name), /\n    if \(box\.scrollHeight > box\.clientHeight && input\.getBoundingClientRect\(\)\.bottom > actions\.getBoundingClientRect\(\)\.top\) box\.scrollTop = box\.scrollHeight;\n  \};$/, name + ": the line is grow's last, after the height is settled, so the answer box's rect is the one the height laid out");
  });
}

// ── the backdrop's click, executed out of each builder ───────────────────────────────────────────
// A tap on the backdrop dismisses: the whole gesture on the backdrop, press and release both. A click whose press began
// inside the sheet does not: Chromium and WebKit dispatch a click whose press and release targets differ to their common
// ancestor, the overlay, so a grip pull released past the box's bottom edge (at 508 the box is at its cap and cannot grow
// with the answer box, so the pointer leaves it) and a text selection dragged out of the box arrived as backdrop clicks and
// closed the sheet with the answer (the author's pass after the maintainer's round 1, composition-2, then the reviewer's
// ruling on the selection: widen the predicate rather than add a case). Nor does a click whose release landed inside the
// sheet: a press on the backdrop released on the answer box or the title reached the overlay as its click in all three
// engines and closed the sheet with the answer (the maintainer's round 2, ui-1), and for a touch the release is read where
// the finger lifted only because a backdrop press gives back the implicit capture a touch pointer takes, without which the
// pointerup's target is the overlay wherever the finger lifts (measured in Chromium through CDP touch). The gesture is
// recorded per pointer (any target but the overlay itself is inside), and a tap is pending from the release that completes
// it until any new press (the maintainer's focused re-check of round 2): while it was two records shared by every pointer,
// the last press and the last release, a chorded mouse (the left button released over the sheet with a second button held,
// which is no pointerup) and a finger resting on the backdrop while a mouse or pen dragged out of the sheet closed it with the
// answer. The browser legs and tests/test_reply_sheet_served.py drive the gestures in each engine (the touch in Chromium:
// this shim cannot model an engine's capture, so it pins the call, not the routing; the chord and the resting finger in the
// browser legs). What a dismiss DOES (close with no save) is untouched: the filed discard item's. Run here against shim nodes
// with the six lines sliced out of each builder
for (const [name, src] of BUILDERS) {
  test(`${name}: the backdrop's click dismisses only when the press and the release were both on the backdrop; a backdrop press gives back its pointer capture so its release is read where it lifted`, () => {
    const overlay = makeNode("div"), input = makeNode("textarea"), detail = makeNode("div"), title = makeNode("div");
    overlay.appendChild(title); overlay.appendChild(input); overlay.appendChild(detail);
    // the overlay's pointer capture, as the test sets it: the pointers it holds, and every release the listener asks for
    const held = new Set<number>(); const released: number[] = [];
    overlay.hasPointerCapture = (id: number) => held.has(id);
    overlay.releasePointerCapture = (id: number) => { released.push(id); held.delete(id); };
    let closed = 0;
    const close = () => { closed++; };
    new Function("overlay", "input", "close", backdropLines(src, name))(overlay, input, close);
    const press = (target: unknown, pointerId = 1) => overlay._listeners.pointerdown({ type: "pointerdown", target, pointerId });
    const release = (target: unknown, pointerId = 1) => overlay._listeners.pointerup({ type: "pointerup", target, pointerId });
    const click = (target: unknown) => overlay._listeners.click({ type: "click", target });
    input.style.height = "78px";
    // a tap on the backdrop: the press, the release and the click all on the overlay
    press(overlay); release(overlay); click(overlay);
    assert.equal(closed, 1, "a tap on the backdrop dismisses: press and release both on it (the sheet's dismiss road, as before)");
    // THE REVERSE DRAG (the maintainer's round 2, ui-1): the press on the backdrop, the release on the answer box, the click at the
    // overlay (the pressed node and the common ancestor both, in all three engines)
    press(overlay); release(input); click(overlay);
    assert.equal(closed, 1, "a press on the backdrop released on the answer box is not a backdrop tap: the sheet stands (reading the press alone, it closed with the answer in Chromium, Firefox and WebKit)");
    press(overlay); release(title); click(overlay);
    assert.equal(closed, 1, "and released on the title: the sheet stands");
    // THE GUARDED DRAG: a drag of the grip released past the box's bottom edge, the press on the answer box, the inline height
    // changed under it, the release and the click at the overlay (Chromium and WebKit: the common ancestor of the press and the release)
    press(input); input.style.height = "148px"; release(overlay); click(overlay);
    assert.equal(closed, 1, "the click that ends a grip drag is not a backdrop tap: the sheet stands (before the press was read it closed with the answer in Chromium and WebKit; reading the release alone, it would again)");
    // a text selection dragged out of the box and released over the backdrop: the press inside the sheet, the height unchanged,
    // the same common-ancestor click
    press(input); release(overlay); click(overlay);
    assert.equal(closed, 1, "the click that ends a selection dragged out of the box is not a backdrop tap either: the press began inside the sheet, whether or not the height changed (the predicate the reviewer ruled; a height clause here left this road open in Chromium and WebKit)");
    // a press anywhere inside the sheet (the detail, say) released on the backdrop: the same
    press(detail); release(overlay); click(overlay);
    assert.equal(closed, 1, "any press that began inside the sheet: its click at the overlay is not a dismissal");
    // each gesture is its own: a tap on the backdrop after any of them dismisses
    press(overlay); release(overlay); click(overlay);
    assert.equal(closed, 2, "each gesture is its own: a tap on the backdrop after a drag dismisses");
    // Firefox retargets a guarded drag's click to the pressed node: not the overlay, so nothing to dismiss
    press(input); input.style.height = "200px"; release(overlay); click(input);
    assert.equal(closed, 2, "a click on the textarea is never a dismissal");
    press(overlay); release(overlay); click(overlay);
    assert.equal(closed, 3, "and the drag leaves nothing behind for the next tap on the backdrop");
    // a press inside the sheet whose release and click never came here (released over another frame): the pointer's next press
    // rewrites its record
    press(input);
    press(overlay); release(overlay); click(overlay);
    assert.equal(closed, 4, "a pointer's new press rewrites its record: a press inside the sheet without a release leaves nothing behind for the next tap");
    // nor does a reverse drag outlive the next tap
    press(overlay); release(input); click(overlay);
    press(overlay); release(overlay); click(overlay);
    assert.equal(closed, 5, "a release inside the sheet, then a tap on the backdrop: the tap dismisses");
    // THE CAPTURE (form R2 of the maintainer's round 2 ruling): a touch pointer is implicitly captured to the node it pressed, so a
    // finger pressed on the backdrop has the overlay holding its capture at the pointerdown; the listener gives it back, so the
    // engine sends the pointerup to the node under the lift (here fed as the answer box, as Chromium does once the capture is back)
    assert.deepEqual(released, [], "no press so far held a capture on the overlay: nothing was released (a mouse takes no implicit capture)");
    held.add(7);
    press(overlay, 7);
    assert.deepEqual(released, [7], "a press on the backdrop with the overlay holding its capture gives that capture back, once, by the pointer's id");
    assert.equal(held.has(7), false, "the overlay no longer holds it");
    release(input, 7); click(overlay);
    assert.equal(closed, 5, "the finger lifted inside the sheet: its pointerup's target is the answer box, so the click at the overlay is not a backdrop tap and the sheet stands with its text");
    held.add(8);
    press(overlay, 8); release(overlay, 8); click(overlay);
    assert.deepEqual(released, [7, 8], "each backdrop press gives its capture back");
    assert.equal(closed, 6, "a touch tap on the backdrop, pressed and lifted there, still dismisses");
    // a press inside the sheet keeps whatever capture the overlay holds for it: a drag that starts inside is left to the node it pressed
    held.add(9);
    press(input, 9);
    assert.deepEqual(released, [7, 8], "a press inside the sheet gives back no capture");
    assert.equal(held.has(9), true, "the capture a press inside the sheet had stays where it was");
    release(overlay, 9); click(overlay);
    assert.equal(closed, 6, "and its drag, released over the backdrop, is not a dismissal");
    // a backdrop press whose capture the overlay does not hold (a mouse, a pen) asks for no release: releasePointerCapture on a
    // pointer the element does not hold is never called
    press(overlay, 10);
    assert.deepEqual(released, [7, 8], "no capture held, nothing released");
  });
  // THE GESTURE PER POINTER (the maintainer's focused re-check of round 2, lens A's findings 1 and 2, measured there on the
  // builders before this form; the lost release below, the check of dace68d57, measured on this form with the press inside
  // not forgetting): fed on a fresh sheet, as a person meets it, so no earlier gesture's release is in play
  test(`${name}: the gesture is recorded per pointer and a new press clears a pending tap: a chorded mouse, a finger resting on the backdrop and a drag out of the sheet after a backdrop press whose release never reached the overlay are not backdrop taps`, () => {
    const overlay = makeNode("div"), input = makeNode("textarea");
    overlay.appendChild(input);
    overlay.hasPointerCapture = () => false;   // a mouse or a pen: no implicit capture
    overlay.releasePointerCapture = () => { /* never asked for here */ };
    let closed = 0;
    const close = () => { closed++; };
    new Function("overlay", "input", "close", backdropLines(src, name))(overlay, input, close);
    const press = (target: unknown, pointerId: number) => overlay._listeners.pointerdown({ type: "pointerdown", target, pointerId });
    const release = (target: unknown, pointerId: number) => overlay._listeners.pointerup({ type: "pointerup", target, pointerId });
    const cancel = (pointerId: number) => overlay._listeners.pointercancel({ type: "pointercancel", target: overlay, pointerId });
    const click = (target: unknown) => overlay._listeners.click({ type: "click", target });
    // THE CHORD: the left button pressed on the backdrop and a second button held (no pointer event: the pointer is already
    // down), the pointer moved over the answer box and the left released there, which with another button still down is a
    // pointermove, not a pointerup, in Chromium and Firefox (in WebKit, in this order, it is a pointerup inside the sheet, which
    // the release listener reads as the reverse drag's); the engine then dispatches the left's click at the overlay, the common
    // ancestor
    press(overlay, 1); click(overlay);
    assert.equal(closed, 0, "a chorded mouse released over the sheet is not a backdrop tap: no release of its pointer came before the click, so no tap is pending and the sheet stands (with one release record shared by every pointer, the click read the value it held from the sheet's open and closed the sheet with the answer in Chromium and Firefox in both orders, and in WebKit with the right button first)");
    release(input, 1);   // the second button released over the answer box: the pointer's pointerup, and no click follows it
    // THE RESTING FINGER: a mouse (or a pen) pressed in the answer box, a finger, another pointer, pressed on the backdrop and
    // held, the mouse released over the backdrop (a selection dragged out of the box), and the mouse's click at the overlay
    press(input, 1); press(overlay, 2); release(overlay, 1); click(overlay);
    assert.equal(closed, 0, "a finger resting on the backdrop does not make a mouse's drag out of the sheet a backdrop tap: that pointer's press began inside the sheet (with one press record shared by every pointer, the finger's press overwrote the mouse's and the sheet closed with the answer, in Chromium through the DevTools protocol, with a mouse and with a pen)");
    release(overlay, 2); click(overlay);
    assert.equal(closed, 1, "the resting finger lifted where it pressed, on the backdrop: its own press and release both there, so its tap dismisses, which the rule allows");
    // THE NEW PRESS CLEARS A PENDING TAP: a right click on the backdrop is a press and a release there whose click the engine
    // never dispatches (it sends contextmenu and auxclick), so its tap stays pending; the chord after it must not read it
    closed = 0;
    press(overlay, 1); release(overlay, 1);
    press(overlay, 1); click(overlay);
    assert.equal(closed, 0, "a new press clears a pending tap: the chord after a right click on the backdrop is not a backdrop tap (left pending, the right click's tap would close the sheet with the answer)");
    release(input, 1);
    // and another pointer's press does the same to a tap whose click has not come yet
    press(overlay, 3); release(overlay, 3); press(input, 1); click(overlay);
    assert.equal(closed, 0, "any new press clears it: a press inside the sheet between a tap's release and its click withdraws the tap");
    release(input, 1);
    // A LOST RELEASE (the check of dace68d57): a mouse pressed on the backdrop, moved past the frame's or the window's edge and
    // released there, so neither its pointerup nor its click reaches the overlay (logged at the root element in Chromium and
    // WebKit; in Firefox with no element target, or not at all); then the same pointer pressed in the answer box, dragged onto
    // the backdrop and released there, its click at the overlay (Chromium and WebKit, as the browser legs drive it). Only the
    // press inside the sheet forgets the stale backdrop press: with that forgetting removed from both builders every other pin
    // stayed green, and in Chromium and WebKit this gesture closed the sheet with the answer in both panes
    press(overlay, 1);   // released past the edge: no pointerup reaches the overlay
    press(input, 1); release(overlay, 1); click(overlay);
    assert.equal(closed, 0, "a press inside the sheet forgets that pointer's backdrop press: after a backdrop press whose release never reached the overlay (released past the frame's or the window's edge), a drag out of the answer box released on the backdrop is not a backdrop tap (without the forgetting, the stale press and the release on the backdrop completed a tap, and in Chromium and WebKit the sheet closed with the answer)");
    // A CANCELLED POINTER is forgotten, and clears a pending tap: in the engines a cancelled pointer (a touch that became a pan)
    // fires no pointerup and no click, so these two halves are argued, not observed, there; this is their pin
    press(overlay, 4); cancel(4); release(overlay, 4); click(overlay);
    assert.equal(closed, 0, "a cancelled pointer's backdrop press is forgotten: no release of it can complete a tap");
    press(overlay, 5); release(overlay, 5); cancel(6); click(overlay);
    assert.equal(closed, 0, "a cancel clears a pending tap");
    // a plain tap after all of them dismisses
    press(overlay, 7); release(overlay, 7); click(overlay);
    assert.equal(closed, 1, "a tap on the backdrop, pressed and released there by one pointer, dismisses after all of them");
  });
}

// ── twins ────────────────────────────────────────────────────────────────────────────────────────
test("the two builders stay twins for this fix: the same kbFit line, the same grow line, the same threshold as the picker's fold", () => {
  const [[, w], [, r]] = BUILDERS;
  assert.equal(line(w, KBFIT, "kbFit", "waiting.ts").trim(), line(r, KBFIT, "kbFit", "render.ts").trim(), "one kbFit line in both builders");
  assert.equal(line(w, RESTCAP, "restCap", "waiting.ts").trim(), line(r, RESTCAP, "restCap", "render.ts").trim(), "one restCap line in both builders (executed above)");
  assert.equal(growBlock(w, "waiting.ts"), growBlock(r, "render.ts"), "one grow block in both builders, byte for byte");
  for (const [what, re] of BACKDROP) {
    assert.equal(line(w, re, what, "waiting.ts").trim(), line(r, re, what, "render.ts").trim(), `one ${what} line in both builders (executed above)`);
  }
  for (const [name, src] of BUILDERS) {
    assert.match(line(src, KBFIT, "kbFit", name), /overlay\.classList\.toggle\("kb-tight", window\.innerHeight < 480\)/, name + ": the picker's 480px threshold (render.ts openPicker), so the two folds agree on what a short window is");
    assert.match(line(src, KBFIT, "kbFit", name), /if \(!overlay\.isConnected\) \{ window\.removeEventListener\("resize", kbFit\); return; \}/, name + ": the listener drops itself when the overlay was replaced");
    assert.match(line(src, KBFIT, "kbFit", name), /window\.innerHeight < 480\); restCap\(\); grow\(true\); \};$/, name + ": the fold re-runs restCap and then grow after its own toggle, on the resize path (grow(true): a dragged height is clamped to the room there and returned toward when the room comes back; executed above), so the room is read with the fold's cap and the detail's cap applied (one grow per resize)");
    assert.ok(src.search(RESTCAP) < src.search(KBFIT), name + ": restCap is declared before kbFit, which calls it");
    assert.ok(src.search(KBFIT) < src.indexOf(GROW_HEAD), name + ": kbFit is declared before grow and reads it only when called; the first call is kbFit() after the append, past grow's declaration");
    assert.match(line(src, CLOSE, "close", name), /window\.removeEventListener\("resize", kbFit\)/, name + ": close() removes it too");
    const armAt = src.search(KB_ARM), appendAt = src.indexOf("document.body.appendChild(overlay);");
    assert.ok(appendAt >= 0 && armAt > appendAt, name + ": armed after the overlay is in the document, so the first kbFit() reads a connected overlay");
    assert.doesNotMatch(src, /style\.height = .*\b(76|78|60)px/, name + ": no hard-coded row height; the floor is measured");
  }
});

// ── the skeleton the CSS keys on, and the one divergence ─────────────────────────────────────────
// Read from each builder's append statements (the tree is built by hand twice, so the order lives in these lines): the
// box holds the title, the quoted line, [the pane's chips], the detail, the answer box, the actions. This is a pin on
// WHERE the order is spelled; the trees themselves are measured by execution in the two browser legs (each pane's
// `kinds`) and in tests/test_reply_sheet_served.py, which reads both real trees in CI. A builder that reorders its
// column, or moves its chips to the other pane's placement, goes red here first and in the legs after.
test("the two builders share the skeleton the five rules key on, in one order, and differ exactly in where the chips go", () => {
  const [[, w], [, r]] = BUILDERS;
  assert.match(w, /\n  box\.append\(h, d\); if \(chip\) box\.appendChild\(chip\); if \(lchip\) box\.appendChild\(lchip\); if \(dd\) box\.appendChild\(dd\); box\.append\(input, actions\);\n/,
    "waiting.ts: title, quoted line, the file chip, the link chip, the detail, the answer box, the actions: the chips are flex children of the box (waiting-pane.css #ut-reply-prompt .wt-file: alone on their line, the cap is the line)");
  assert.match(r, /\n  box\.append\(h, d\); if \(dd\) box\.appendChild\(dd\); box\.append\(input, actions\);\n/,
    "render.ts: title, quoted line, the detail, the answer box, the actions: no chip is a child of the box");
  assert.match(r, /if \(todoFile\) d\.append\(" ", todoFileChip\(todoFile, sid\)\);[^\n]*\n\s*if \(todoLink\) d\.append\(" ", todoLinkChip\(todoLink\)\);/,
    "render.ts: the chips trail the quoted line INSIDE it, the file's first (styles.css #ut-reply-prompt .ut-link, .ut-file: the cap is the line)");
  assert.doesNotMatch(w, /d\.append\(" ", (fileChip|linkChip)/, "waiting.ts puts no chip inside the quoted line");
  assert.doesNotMatch(r, /box\.appendChild\((chip|lchip)\)/, "render.ts appends no chip to the box");
  for (const [name, src] of BUILDERS) {
    // the classes the rules key on, each minted once per builder, on the element the rule means
    assert.match(src, /el\("div", "picker-overlay confirm-overlay"\); overlay\.id = "ut-reply-prompt";/, name + ": the overlay id the five rules are scoped to");
    assert.match(src, /const box = el\("div", "picker-box confirm-box"\);/, name + ": the box (#ut-reply-prompt .picker-box)");
    assert.match(src, /el\("div", "ut-detail open"\)/, name + ": the detail (#ut-reply-prompt .ut-detail.open)");
    assert.match(src, /input\.className = "ut-reply-input"; input\.rows = 3;/, name + ": the answer box (#ut-reply-prompt .ut-reply-input), three rows");
    assert.match(src, /const actions = el\("div", "confirm-actions"\);/, name + ": the actions row (#ut-reply-prompt .confirm-actions, kept in view at the box's bottom)");
  }
});

// ── the sheet's rules, pinned at source ──────────────────────────────────────────────────────────
// the sheet with its comments stripped FIRST, so a declaration commented out in place is gone from what a pin reads (a
// raw-text match kept a pin green over `/* overflow-y: auto; */`, the maintainer's round 1 ruling), and a brace inside a
// comment cannot end a rule's slice early
const CSS_LIVE = CSS.replace(/\/\*[\s\S]*?\*\//g, "");
const rule = (sel: string): string => {
  const at = CSS_LIVE.indexOf("\n" + sel + " {");
  assert.ok(at >= 0, sel + " is a rule in styles.css");
  return CSS_LIVE.slice(at + 1, CSS_LIVE.indexOf("}", at) + 1);   // from the selector to its closing brace, live declarations only
};
test("rule() reads live declarations: a declaration commented out in place is not in the slice", () => {
  const stripped = "\n.x { a: 1; /* b: 2; */ c: 3; }\n".replace(/\/\*[\s\S]*?\*\//g, "");
  assert.equal(stripped, "\n.x { a: 1;  c: 3; }\n");
  assert.doesNotMatch(CSS_LIVE, /\/\*/, "no comment opener survives the strip");
  assert.ok(CSS_LIVE.length < CSS.length, "the sheet has comments, and the strip removed them");
});

test("the answer box is a fixed flex item that holds three rows: it never absorbs the box's deficit", () => {
  const r = rule("#ut-reply-prompt .ut-reply-input");
  assert.match(r, /flex: 0 0 auto;/, "no shrink: with min-height auto resolving to 0 on a textarea, flex-shrink 1 gave it the whole deficit");
  assert.match(r, /min-height: calc\(3lh \+ 16px\);/, "three rows (rows=3) plus the 7px+7px padding and the 1px+1px border (.ut-reply-input, box-sizing border-box)");
  assert.match(rule(".ut-reply-input"), /resize: vertical;/, "the person can pull the box taller, and the height they pulled STANDS: grow stands down for an inline height it did not write (the guard executed above; the browser legs drag the grip, then type, in each engine)");
  assert.match(rule(".ut-reply-input"), /box-sizing: border-box;/, "the 16px in the floor is the box's own padding and border");
  assert.match(rule(".ut-reply-input"), /padding: 7px 9px;/); assert.match(rule(".ut-reply-input"), /border: 1px solid/);
});

test("the detail is the part that gives way: it shrinks (a scroll container's flex minimum is zero) down to a floor of two lines, is capped, and scrolls within itself", () => {
  const r = rule("#ut-reply-prompt .ut-detail.open");
  assert.match(r, /flex: 1 1 auto;/);
  assert.match(r, /min-height: 32px; min-height: 2lh;/, "the FLOOR: two of the detail's own lines (2lh), the px value ahead of it so an engine without the lh unit falls to two lines at the default size, never to zero; without it the detail resolved to 0px at 390x508 with the answer grown (invisible, unscrollable), the dead end the picker's fold forbids its list with min-height: 52px (one row). The browser legs measure it: the detail's height is at least twice its computed line-height in every deficit state");
  assert.doesNotMatch(r, /min-height: 0;/, "no zero floor beside the real one: the later declaration in a block wins, and the executed legs pin the floor, not this string");
  assert.match(r, /max-height: max\(12em, calc\(0\.348 \* var\(--ut-rest-h, 0px\)\)\);/, "the cap: the larger of 12em of the detail's own font (about eight and a half of its lines at line-height 1.4) and 34.8% of the window's height, which restCap publishes only with the keyboard down (executed above); with the property absent the term is 0px and the cap is 12em, the keyboard-up cap, where the flex shrink and the two-line floor govern. This spelling is not the guarantee: the browser legs measure the cap at rest at the pane heights a phone gives (620, 633, 709 and the installed app's 732) and at 900 and 1080 (the viewport term), the 8-line detail on both sides of the stated boundary (in full from 720), at rest at 300 (12em, read from the computed max-height), and under the keyboard at 508 (12em), in three engines, and the served leg at the same rest heights, the boundary and under the keyboard in CI. A 35dvh arm stood beside 12em in round 1 as the keyboard-up cap and never bound (177.8px against 134px at 508), so it is gone");
  assert.doesNotMatch(r, /dvh/, "no viewport arm presented as the keyboard's mechanism: the keyboard case is the shrink and the floor, measured by execution");
  assert.match(r, /overflow-y: auto;/, "the rest of the detail is a scroll away, never clipped. The spelling pins of this test alone guard the declaration (this one and the sequence pin below): since overflow-x: hidden stands beside it, either half alone makes the detail a scroll container (CSS Overflow: a visible half beside a non-visible half computes to auto, measured in Chromium, Firefox and WebKit), so commenting this one out changes nothing an engine can read and no execution pin reds it; the browser legs' scrollTop pin guards the PAIR, and reds once both halves are gone");
  assert.match(r, /overscroll-behavior: contain;/, "a swipe past its end does not scroll the box or the page under it (#pinned-notes's rule)");
  assert.match(r, /overflow-y: auto; overflow-x: hidden; overflow-wrap: anywhere;/, "no sideways scroller: a scroll container's overflow-x computes to auto, and an unbreakable token made the detail scroll sideways (measured in WebKit at 390x508); overflow-wrap: anywhere breaks the token as .pn-detail and .ut-reply-quote do, overflow-x: hidden is #pinned-notes's companion (the browser legs and the served leg pin the detail's scrollWidth no wider than its offsetWidth, the border box, in three engines)");
  assert.match(rule("#pinned-notes"), /max-height: min\(11em, 30vh\); overflow-y: auto; overflow-x: hidden; overscroll-behavior: contain;/, "the precedent this follows");
  assert.match(rule(".ut-detail.open"), /^\.ut-detail\.open \{ display: block; \}$/, "the base rule stays: display block, no flex or cap of its own; the fix is scoped to this dialog");
});

test("a short window pins the sheet to the top under the picker's 12px frame, on this overlay's OWN selector; nothing hides or reorders", () => {
  const r = rule("#ut-reply-prompt.kb-tight");
  assert.match(r, /align-items: flex-start; padding: 12px 16px;/, "the picker's kb-tight frame (its rule is #picker-scoped, so this overlay needs its own)");
  assert.doesNotMatch(r, /display: none|\border\s*:/, "no kb-tight rule hides a row or reorders the column (picker-keyboard.test.ts's rule holds here too)");
  // the picker's fold rules the class shares reach this overlay through .picker-overlay: the dvh cap and the scrolling box
  assert.match(CSS, /\.picker-overlay\.kb-tight \.picker-box \{ max-height: calc\(100dvh - 24px\); overflow-y: auto; \}/, "the class-scoped rule that caps and scrolls the box once this overlay wears kb-tight");
  // …and the picker's own strings stand as picker-keyboard.test.ts pins them: this fix added a selector, it moved none
  assert.match(CSS, /#picker\.kb-tight,\s*\nbody\.picker-lifted > #picker\.kb-tight \{ align-items: flex-start; padding: 12px 16px; \}/);
  assert.match(RENDER, /const kbFit = \(\) => document\.getElementById\("picker"\)\?\.classList\.toggle\("kb-tight", window\.innerHeight < 480\)/, "the picker's own kbFit is untouched");
});

test("this dialog's box scrolls at EVERY height, on its own selector: the backstop for a window the floors alone overflow (the actions row kept in view there: the next pin)", () => {
  const r = rule("#ut-reply-prompt .picker-box");
  assert.match(r, /overflow-y: auto;/, "the shared .picker-box is overflow hidden and scrolls only under the fold (480px); above it a row laid out past the cap was clipped and not hit-testable, so a tap where Send was painted fell on the backdrop and closed the sheet with the answer (the maintainer's round 1 ruling); the box scrolls instead, at any height");
  assert.doesNotMatch(r, /max-height|height:|padding|display/, "the scroll alone: no cap of its own (an id-scoped max-height would outrank the fold's calc(100dvh - 24px) and widen this dialog's sizing)");
  assert.equal(r.replace(/\s+/g, " ").trim(), "#ut-reply-prompt .picker-box { overflow-y: auto; }", "one declaration, so the shared box rule's other declarations reach this dialog unchanged");
});

test("the actions row is kept in view at the box's bottom, on this dialog's own selector: where the floors overflow the box, Cancel and Send stay inside its clip", () => {
  const r = rule("#ut-reply-prompt .confirm-actions");
  assert.match(r, /position: sticky; bottom: 0;/, "sticky at the bottom of the box's scrollport: where the floors overflow the box and it scrolls, the row stays in view, so Send is inside the clip and a finger at its centre reaches it (at a6e7f1cfa, in the pane, Send lay partly or wholly past the clip at 390x420 and 480 with a 300-character ask and at 320 wide with the fixture, and a tap at its centre closed the sheet with the answer, in three engines; the maintainer's round 2 ruling, B-i). The browser legs and the served leg click Send's centre in those states and read one answer posted");
  assert.match(r, /background: var\(--vscode-editorWidget-background, #252526\);/, "opaque, in the box's own background, so what scrolls under the row does not show through it");
  assert.match(rule(".picker-box"), /background: var\(--vscode-editorWidget-background, #252526\);/, "the box's background, which the row repeats");
  assert.equal(r.replace(/\s+/g, " ").trim(), "#ut-reply-prompt .confirm-actions { position: sticky; bottom: 0; background: var(--vscode-editorWidget-background, #252526); }", "three declarations, so the shared .confirm-actions rule's layout reaches this dialog unchanged");
  assert.match(CSS, /\n\.confirm-actions \{ display: flex; gap: 8px; margin-top: 6px; \}\n/, ".confirm-actions is as it was: the other dialogs' rows are untouched");
});

test("the fix adds no font-size and touches no shared dialog rule", () => {
  for (const sel of ["#ut-reply-prompt .ut-reply-input", "#ut-reply-prompt .ut-detail.open", "#ut-reply-prompt.kb-tight", "#ut-reply-prompt .picker-box", "#ut-reply-prompt .confirm-actions"]) {
    assert.doesNotMatch(rule(sel), /font-size/, sel + ": no new font-size (ui/CLAUDE.md: reuse a size already on the surface)");
    assert.equal((CSS.match(new RegExp("\\n" + sel.replace(/[.#]/g, "\\$&") + " \\{", "g")) || []).length, 1, sel + " is declared once");
  }
  assert.match(CSS, /\n\.confirm-box \{ width: min\(440px, 96%\); padding: 16px 18px; gap: 10px; \}\n/, ".confirm-box is as it was: seven dialogs share it");
  assert.match(CSS, /\n\.confirm-overlay \{ display: flex; align-items: center; padding: 16px; \}\n/, ".confirm-overlay is as it was");
  const pb = rule(".picker-box");
  assert.match(pb, /max-height: calc\(100vh - 88px\);/); assert.match(pb, /display: flex; flex-direction: column;/); assert.match(pb, /overflow: hidden;/);
});
