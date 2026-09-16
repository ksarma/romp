// The Reply modal's window focus-return listener (ui/webview/waiting.ts showReply), pinned at source and EXECUTED. Restored at
// the 2026-09-15 upstream pull-in's fixer round 7w under R5 (never retire a test silently): fixer round 3 deleted
// ui/webview/waiting-link-focus.test.ts whole under the T404 twin (https://github.com/romp-on/romp/pull/1596, the route
// follows the OPEN Files pane), and that file's browser leg had indeed lost its premise (a relay bringing a CLOSED Files pane
// forward), but its third case was the only pin of a listener that is still live: when a link in the modal moved the keyboard
// to the Files pane and this pane regains focus (Alt+Left, a click into it), the document's focus has been reset to its body,
// BEHIND the overlay, where Tab would walk the covered rows before reaching the box; so the modal takes the focus back into
// its box. Gone with the modal: close() drops the listener, and it drops itself when the overlay was removed some other way
// (a second Reply replacing this one). Two of the three arms had no executing test anywhere: the round's mutants (close()
// without the removal; onFocus without the self-removal) stayed green under the twin's browser legs.
//
// Two legs, no browser. The source leg restores the deleted case's three pins as written. The executed leg slices the two
// arrow functions and the arming lines out of showReply's body (waiting.ts's source, the user-todo-links.test.ts idiom) and
// runs them against stand-ins: the overlay and the box are the shared shim's nodes (ui/test-dom-shim.ts nodeFactory, the
// projection rule the ratchet in ui/test-dom-shim.test.ts keeps; the overlay's isConnected is its tree's own answer), the
// window and the document a listener-recording EventTarget stand-in with no DOM edge (so no hideEdges call, which the
// ratchet's caller rule reserves for a fake with an edge): the return trip focuses the box; close() removes the very
// listener it added; a listener that finds its overlay gone removes itself and focuses nothing. The return trip in
// a real browser (Alt+Left after the Files pane took the click) is waiting-pane-browser.test.ts's Files-pane-open case, in
// Firefox and Chromium. The suite discovers this file by its name and place (vscode-extension/esbuild.js testBuild reads
// every *.test.ts under ui/webview). Synthetic only: no fixture text.
//
// A third leg (the 2026-09-15 pull-in's review, round 2, item 5) executes the modal's capture-phase Escape handler (onKey)
// against stand-ins the same way: while the viewer OR the file browser's listing is up over the pane, Escape is that surface's
// and the modal stands aside, parking one return of the keyboard into the box that runs only once BOTH ids are gone; with
// neither up, Escape is the modal's. Before the round the guard read the viewer's id alone, so a listing reached through the
// modal's own link (the viewer's directory link) had the modal's Escape close the modal, typed answer and all, with the
// listing still up. The flow in a browser is waiting-pane-browser.test.ts's modal-link case.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { nodeFactory } from "../test-dom-shim";

const UI = path.resolve(process.cwd(), "..", "ui", "webview");   // npm test runs in vscode-extension
const WAITING = fs.readFileSync(path.join(UI, "waiting.ts"), "utf8");
const MODAL = WAITING.slice(WAITING.indexOf("function showReply("), WAITING.indexOf("// ── render"));

// ── the source leg: the deleted case's pins, as written ──────────────────────────────────────────
test("the Reply modal takes the focus back into its box when the pane regains it, and the listener goes with the modal (pinned at source)", () => {
  assert.match(MODAL, /const onFocus = \(\) => \{ if \(!overlay\.isConnected\) \{ window\.removeEventListener\("focus", onFocus\); return; \} input\.focus\(\); \};/);
  assert.match(MODAL, /const close = \(\) => \{ overlay\.remove\(\); document\.removeEventListener\("keydown", onKey, true\); window\.removeEventListener\("focus", onFocus\); \};/);
  assert.match(MODAL, /window\.addEventListener\("focus", onFocus\);\n\s*input\.focus\(\);\n\}/, "armed at open, after the modal is in the document");
});

// ── the executed leg ─────────────────────────────────────────────────────────────────────────────
// the listener, the close and the arming lines, executed out of the source with the names they read handed in
type Armed = { onFocus: () => void; close: () => void };
function arm(overlay: unknown, input: unknown, win: unknown, doc: unknown, onKey: unknown): Armed {
  const line = (re: RegExp, what: string): string => { const m = MODAL.match(re); assert.ok(m, what + " not found in showReply: re-anchor"); return m![0]; };
  const onFocus = line(/^\s*const onFocus = .*$/m, "the onFocus line");
  const close = line(/^\s*const close = .*$/m, "the close line");
  const arming = line(/document\.addEventListener\("keydown", onKey, true\);\n\s*window\.addEventListener\("focus", onFocus\);\n\s*input\.focus\(\);/, "the arming lines");
  const body = onFocus + "\n" + close + "\n" + arming + "\nreturn { onFocus, close };";
  return new Function("overlay", "input", "window", "document", "onKey", body)(overlay, input, win, doc, onKey) as Armed;
}
// an EventTarget stand-in for the window and the document: remembers its listeners by type, records every removal, and can
// fire one type; dispatch walks a COPY of the set, as the DOM does, so a listener that removes itself mid-dispatch still runs
// to its end. No DOM edge on it, so it is not a hideEdges caller (the ratchet's rule for a fake with an edge)
class Target {
  private byType = new Map<string, Set<(...a: unknown[]) => void>>();
  removed: Array<[string, unknown, unknown]> = [];
  addEventListener(type: string, fn: (...a: unknown[]) => void): void { (this.byType.get(type) ?? this.byType.set(type, new Set()).get(type)!).add(fn); }
  removeEventListener(type: string, fn: (...a: unknown[]) => void, opt?: unknown): void { this.byType.get(type)?.delete(fn); this.removed.push([type, fn, opt]); }
  count(type: string): number { return this.byType.get(type)?.size ?? 0; }
  fire(type: string): void { for (const fn of [...(this.byType.get(type) ?? [])]) fn(); }
}
const makeNode = nodeFactory();
function world() {
  // the modal's overlay under a body, so isConnected is the tree's own answer (attached or not), and remove() the shim's
  const body = makeNode("body"), overlay = makeNode("div");
  body.appendChild(overlay);
  Object.defineProperty(overlay, "isConnected", { get: () => overlay.parentNode === body, configurable: true });
  const input = makeNode("textarea");
  let focused = 0;
  input.addEventListener("focus", () => { focused++; });   // the shim's focus() fires the node's own focus listener, as a browser would
  const win = new Target(), doc = new Target();
  const onKey = () => { /* the modal's Escape handler, by reference only */ };
  return { body, overlay, input, focused: () => focused, win, doc, onKey };
}

test("armed at open: the pane regaining focus puts the keyboard back into the box, and the listener stays for the next return", () => {
  const { overlay, input, focused, win, doc, onKey } = world();
  assert.equal(overlay.isConnected, true, "the overlay is in the document");
  const a = arm(overlay, input, win, doc, onKey);
  assert.equal(focused(), 1, "the open itself focuses the box");
  assert.equal(win.count("focus"), 1, "one window focus listener");
  assert.equal(doc.count("keydown"), 1, "the modal's Escape handler, armed in the same breath");
  win.fire("focus");
  assert.equal(focused(), 2, "the return trip lands in the box");
  win.fire("focus");
  assert.equal(focused(), 3, "and again: the listener stays while the modal is up");
  assert.equal(win.count("focus"), 1);
  assert.equal(overlay.isConnected, true, "the modal is untouched");
  assert.equal(typeof a.onFocus, "function"); assert.equal(typeof a.close, "function");
});

test("close() removes the window focus listener with the modal, by the reference it added, and the Escape handler with it; a later focus reaches no listener", () => {
  const { overlay, input, focused, win, doc, onKey } = world();
  const a = arm(overlay, input, win, doc, onKey);
  a.close();
  assert.equal(overlay.isConnected, false, "the overlay left the document (the shim's remove, off its body)");
  assert.equal(win.count("focus"), 0, "the focus listener went with it");
  assert.equal(win.removed.length, 1); assert.equal(win.removed[0][0], "focus"); assert.equal(win.removed[0][1] === a.onFocus, true, "removed under the reference it was added under");
  assert.deepEqual(doc.removed.map(([t, f, o]) => [t, f === onKey, o]), [["keydown", true, true]], "the Escape handler, removed with its capture flag");
  win.fire("focus");
  assert.equal(focused(), 1, "nothing focuses the box after the close: only the open's own focus is on record");
});

test("the overlay removed some other way (a second Reply replacing this one): the next focus drops the listener and focuses nothing", () => {
  const { body, overlay, input, focused, win, doc, onKey } = world();
  arm(overlay, input, win, doc, onKey);
  body.removeChild(overlay);   // the replacing showReply's getElementById(...)?.remove(), not this modal's close()
  assert.equal(overlay.isConnected, false);
  win.fire("focus");
  assert.equal(focused(), 1, "a box behind a modal that is gone gets no focus");
  assert.equal(win.count("focus"), 0, "the listener removed itself");
  assert.equal(win.removed.length, 1); assert.equal(win.removed[0][0], "focus");
  win.fire("focus");
  assert.equal(focused(), 1, "and nothing runs on the focus after that");
  assert.equal(doc.removed.length, 0, "close() never ran: the Escape handler is still the document's");
});

// ── the Escape stand-aside, executed ─────────────────────────────────────────────────────────────
// showReply's onKey (the modal's capture-phase Escape), sliced WHOLE out of the source (the multi-line arrow, head to its
// closing brace) and run against stand-ins: a document whose getElementById answers for the ids a case puts up (the viewer's
// romp-fileview, the listing's romp-filebrowse; no DOM edge on it, so no hideEdges call, as Target above), the overlay and the
// box as factory nodes (world()), a setTimeout that PARKS the tick for the case to run, and a close that counts. The rule: with
// a surface up, no stopPropagation and no close, one return parked; at the tick the box takes the keyboard only when both ids
// are gone and the modal is still in the document; with nothing up, Escape stops here and closes the modal.
type Key = (e: { key: string; stopPropagation(): void }) => void;
function onKeyOf(dom: unknown, overlay: unknown, input: unknown, timer: unknown, close: unknown): Key {
  const head = "const onKey = (e: KeyboardEvent) => {";
  const at = MODAL.indexOf(head);
  assert.ok(at >= 0, "the onKey head not found in showReply: re-anchor");
  const tail = "\n  };";
  const end = MODAL.indexOf(tail, at);
  assert.ok(end > at, "the onKey close not found in showReply: re-anchor");
  const src = MODAL.slice(at, end + tail.length).replace(head, "const onKey = (e) => {");   // the one annotation, off for plain JS
  return new Function("document", "overlay", "input", "setTimeout", "close", src + "\nreturn onKey;")(dom, overlay, input, timer, close) as Key;
}
// the document as the handler reads it: getElementById for the two overlay ids, up or not
class Doc {
  private up = new Map<string, unknown>();
  show(id: string): void { this.up.set(id, makeNode("div")); }
  hide(id: string): void { this.up.delete(id); }
  getElementById(id: string): unknown { return this.up.get(id) ?? null; }
}
function escWorld() {
  const { body, overlay, input, focused } = world();
  const dom = new Doc();
  const parked: Array<() => void> = [];
  const timer = (fn: () => void, ms: number) => { assert.equal(ms, 0, "the return is a tick later, never a wait"); parked.push(fn); };
  const tick = (): number => { const run = parked.splice(0); for (const fn of run) fn(); return run.length; };
  let closed = 0;
  const onKey = onKeyOf(dom, overlay, input, timer, () => { closed++; });
  // one press: how many times the handler stopped the key (0: it stood aside or ignored the key; 1: the modal took it)
  const press = (key = "Escape"): number => { let stopped = 0; onKey({ key, stopPropagation() { stopped++; } }); return stopped; };
  return { body, overlay, input, focused, dom, parked, tick, closed: () => closed, press };
}

test("Escape with nothing over the pane is the modal's: the key stops here and the modal closes, no return parked; another key is nobody's", () => {
  const w = escWorld();
  assert.equal(w.press("Enter"), 0, "not Escape: nothing");
  assert.equal(w.closed(), 0); assert.equal(w.parked.length, 0);
  assert.equal(w.press(), 1, "stopPropagation: the key goes no further");
  assert.equal(w.closed(), 1, "close()");
  assert.equal(w.parked.length, 0, "no return of the keyboard parked");
  assert.equal(w.focused(), 0, "the box was never focused: only the open's own focus would be (not armed here)");
});

test("Escape while the viewer is up stands aside and parks the return: the box takes the keyboard once the viewer is gone, not while it stays", () => {
  const w = escWorld();
  w.dom.show("romp-fileview");
  assert.equal(w.press(), 0, "no stopPropagation: the viewer's own handler (file-view.ts onKey, bubble phase) gets the key");
  assert.equal(w.closed(), 0, "the modal stays");
  assert.equal(w.parked.length, 1, "one return parked, a tick later");
  assert.equal(w.tick(), 1);
  assert.equal(w.focused(), 0, "the viewer still up at the tick (its dirty-edit veto kept it): the box is left alone");
  w.press(); w.dom.hide("romp-fileview"); w.tick();
  assert.equal(w.focused(), 1, "the viewer gone at the tick: the keyboard comes back into the box");
  assert.equal(w.closed(), 0, "and the modal is still up");
});

test("Escape while the LISTING is up stands aside the same way: the browser's own handler closes it, the answer stays, the box takes the keyboard once the listing is gone, and the next Escape is the modal's", () => {
  const w = escWorld();
  w.dom.show("romp-filebrowse");
  assert.equal(w.press(), 0, "no stopPropagation: the browser's handler (file-browse.ts onKey, bubble phase) gets the key");
  assert.equal(w.closed(), 0, "the modal stays with its text");
  assert.equal(w.tick(), 1, "one return parked");
  assert.equal(w.focused(), 0, "the listing still up at the tick (a row menu took the key): the box does not take the keys the listing reads");
  w.press(); w.dom.hide("romp-filebrowse"); w.tick();
  assert.equal(w.focused(), 1, "the listing gone: the keyboard comes back into the box");
  assert.equal(w.closed(), 0);
  assert.equal(w.press(), 1, "nothing up: the next Escape is the modal's");
  assert.equal(w.closed(), 1);
});

test("the viewer over the listing (a pick from it): the viewer's Escape leaves the listing up, so the box waits for BOTH to go; a modal replaced before the tick takes nothing", () => {
  const w = escWorld();
  w.dom.show("romp-filebrowse"); w.dom.show("romp-fileview");
  assert.equal(w.press(), 0, "stands aside for the topmost, the viewer");
  assert.equal(w.closed(), 0);
  w.dom.hide("romp-fileview");   // the viewer's own handler closed it; the listing is still up beneath
  w.tick();
  assert.equal(w.focused(), 0, "both ids are checked: the listing still up keeps the keyboard");
  assert.equal(w.press(), 0, "the next Escape is the listing's");
  w.dom.hide("romp-filebrowse"); w.tick();
  assert.equal(w.focused(), 1, "both gone: the box");
  assert.equal(w.closed(), 0, "the modal never closed through this");
  // a second Reply replaced this modal before the tick (its overlay removed some other way, not close()): no focus into a box
  // behind a modal that is gone
  const v = escWorld();
  v.dom.show("romp-filebrowse");
  assert.equal(v.press(), 0);
  v.dom.hide("romp-filebrowse"); v.body.removeChild(v.overlay);
  assert.equal(v.overlay.isConnected, false);
  v.tick();
  assert.equal(v.focused(), 0, "overlay.isConnected false at the tick: nothing focused");
});
