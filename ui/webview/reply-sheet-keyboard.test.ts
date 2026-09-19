// The todo Reply sheet on a phone with the keyboard up (the user 2026-09-19, screenshot): a todo's long detail filled
// the sheet and the answer box was ONE squeezed line above Cancel and Send. The two hand-maintained twin builders,
// ui/webview/waiting.ts showReply and ui/webview/render.ts showUserTodoReply, emit the same tree: #ut-reply-prompt
// (.picker-overlay.confirm-overlay) > .picker-box.confirm-box, a column flex box capped at the window with overflow
// hidden, holding the title, the quoted line, the chips, .ut-detail.open, textarea.ut-reply-input and .confirm-actions.
// Every child is a shrinkable flex item; a wrapped text block's automatic minimum (min-height: auto) refuses to shrink
// and the textarea's (overflow auto) resolves to zero, so the box took the whole deficit and the cap clipped rather
// than scrolled.
//
// The fix rides the picker's existing fold and touches no shared rule (.confirm-box and .picker-box serve seven
// dialogs). Three CSS rules scoped to this dialog: the answer box never shrinks and holds three rows (min-height in
// lh); the detail is the part that gives way, capped and scrolling within itself, min-height: 0 being the half that
// lets it shrink at all (#pinned-notes is the precedent); a short window pins the sheet to the top under the picker's
// 12px frame. In each builder one closure, kbFit, toggles kb-tight on THIS window's own resize (the shell sizes the
// pane iframe to the visible height, so the keyboard opening or closing IS a resize here; render.ts's picker keys on
// the same event, at the same 480px), and close() removes the listener, which also removes itself when the overlay
// was replaced by a second Reply; and a grow handler lets the box follow the answer, as the composer's growComposer
// does, never under the three-row floor.
//
// Two kinds of leg, no browser (the browser legs are waiting-reply-sheet-browser.test.ts and
// render-reply-sheet-browser.test.ts). The executed legs slice the fold's lines and the grow handler out of EACH
// builder's source (the waiting-reply-focus.test.ts idiom) and run them against stand-ins: the overlay is the shared
// shim's node (ui/test-dom-shim.ts nodeFactory; its isConnected is its tree's own answer), the window a
// listener-recording EventTarget stand-in with an innerHeight and no DOM edge. The source legs pin the three rules'
// declared properties and that no rule of the fix adds a font-size (ui/CLAUDE.md), and that the picker's own fold
// strings stand as picker-keyboard.test.ts pins them. Synthetic only: no fixture text.
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
const CLOSE = /^\s*const close = .*$/m;
const KB_ARM = /window\.addEventListener\("resize", kbFit\);\n\s*kbFit\(\);/;
const GROW = /^\s*const grow = .*$/m;
const GROW_ARM = /input\.addEventListener\("input", grow\);/;

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
// node under a body, so isConnected is the tree's answer), the window stand-in, and stand-ins for the other names
// the close line removes (onKey, onFocus) and the document it removes them from
function fold(name: string, src: string, overlay: unknown, win: Win): Fold & { doc: Win } {
  const doc = new Win();
  const body = line(src, KBFIT, "the kbFit line", name) + "\n" + line(src, CLOSE, "the close line", name) + "\n" + line(src, KB_ARM, "the arming lines", name) + "\nreturn { kbFit, close };";
  const onKey = () => { /* the modal's Escape handler, by reference only */ };
  const onFocus = () => { /* waiting.ts's focus-return listener, by reference only */ };
  const r = new Function("overlay", "window", "document", "onKey", "onFocus", body)(overlay, win, doc, onKey, onFocus) as Fold;
  return { ...r, doc };
}
function world() {
  const body = makeNode("body"), overlay = makeNode("div");
  body.appendChild(overlay);
  Object.defineProperty(overlay, "isConnected", { get: () => overlay.parentNode === body, configurable: true });
  return { body, overlay, win: new Win(), tight: () => overlay.classList.contains("kb-tight") as boolean };
}

for (const [name, src] of BUILDERS) {
  test(`${name}: kb-tight follows this window's height — on under 480px at open and on every resize, off again with the room back`, () => {
    const w = world();
    w.win.innerHeight = 420;   // the keyboard already up when Reply is tapped
    fold(name, src, w.overlay, w.win);
    assert.equal(w.win.count("resize"), 1, "one resize listener armed");
    assert.equal(w.tight(), true, "synced at open: a short window folds before any resize");
    w.win.innerHeight = 900; w.win.fire("resize");
    assert.equal(w.tight(), false, "the keyboard down (or a tall screen): the fold comes off on the same event");
    w.win.innerHeight = 479; w.win.fire("resize");
    assert.equal(w.tight(), true, "479px is short: the picker's threshold, shared");
    w.win.innerHeight = 480; w.win.fire("resize");
    assert.equal(w.tight(), false, "480px is not");
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
    assert.equal(w.win.count("resize"), 0, "the listener removed itself");
    assert.deepEqual(w.win.removed.map(([t, fn]) => [t, fn === f.kbFit]), [["resize", true]], "by its own reference");
    w.win.fire("resize");
    assert.equal(w.win.removed.length, 1, "and nothing runs on the resize after that");
    assert.deepEqual(f.doc.removed, [], "close() never ran: the Escape handler is still the document's");
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
  return { input, writes, geom };
}
function grower(name: string, src: string, input: unknown, win: Win): () => void {
  const body = line(src, GROW, "the grow line", name) + "\n" + line(src, GROW_ARM, "the grow arming line", name) + "\nreturn grow;";
  return new Function("input", "window", body)(input, win) as () => void;
}

for (const [name, src] of BUILDERS) {
  test(`${name}: the box grows with the answer from height auto, to the content's height plus the border; never under the three-row floor, capped at a share of the window`, () => {
    // laid out at height auto the box is its floor: three rows of text, the padding and the 1px borders (78px of
    // border-box; 76px inside the border)
    const g = inputNode({ offset: 78, client: 76, scroll: 76 });
    const win = new Win(); win.innerHeight = 900;
    const grow = grower(name, src, g.input, win);
    assert.equal(g.input._listeners.input === grow, true, "armed on the box's input event");
    g.input._listeners.input({ type: "input" });
    assert.deepEqual(g.writes, ["auto", "78px"], "measured at auto first, then the floor: an empty box is three rows");
    // a long answer: the content's scroll height plus the border a border-box height carries (the composer's growComposer
    // reads scrollHeight the same way; the border is what a bare scrollHeight would leave as a one-line scroll)
    g.writes.length = 0; g.geom.scroll = 200;
    grow();
    assert.deepEqual(g.writes, ["auto", "202px"], "grows to the content: 200px of content and padding plus the 2px of border");
    // the cap: a share of the window, so Cancel and Send stay in the box on a phone
    g.writes.length = 0; g.geom.scroll = 5000; win.innerHeight = 508;
    grow();
    assert.deepEqual(g.writes, ["auto", Math.round(508 * 0.4) + "px"], "capped at 40% of a 508px window");
    // the floor beats the cap on a window too short for even three rows' share: never under three rows
    g.writes.length = 0; win.innerHeight = 150;
    grow();
    assert.deepEqual(g.writes, ["auto", "78px"], "a 150px window's 40% is 60px, under the floor: the floor stands");
    // the floor is read from the layout, not a constant: a larger font lays out a taller floor and the handler follows
    g.writes.length = 0; g.geom.offset = 100; g.geom.client = 98; g.geom.scroll = 98; win.innerHeight = 900;
    grow();
    assert.deepEqual(g.writes, ["auto", "100px"], "the floor is whatever height auto laid out");
  });
}

// ── twins ────────────────────────────────────────────────────────────────────────────────────────
test("the two builders stay twins for this fix: the same kbFit line, the same grow line, the same threshold as the picker's fold", () => {
  const [[, w], [, r]] = BUILDERS;
  assert.equal(line(w, KBFIT, "kbFit", "waiting.ts").trim(), line(r, KBFIT, "kbFit", "render.ts").trim(), "one kbFit line in both builders");
  assert.equal(line(w, GROW, "grow", "waiting.ts").trim(), line(r, GROW, "grow", "render.ts").trim(), "one grow line in both builders");
  for (const [name, src] of BUILDERS) {
    assert.match(line(src, KBFIT, "kbFit", name), /overlay\.classList\.toggle\("kb-tight", window\.innerHeight < 480\)/, name + ": the picker's 480px threshold (render.ts showPicker), so the two folds agree on what a short window is");
    assert.match(line(src, KBFIT, "kbFit", name), /if \(!overlay\.isConnected\) \{ window\.removeEventListener\("resize", kbFit\); return; \}/, name + ": the listener drops itself when the overlay was replaced");
    assert.match(line(src, CLOSE, "close", name), /window\.removeEventListener\("resize", kbFit\)/, name + ": close() removes it too");
    const armAt = src.search(KB_ARM), appendAt = src.indexOf("document.body.appendChild(overlay);");
    assert.ok(appendAt >= 0 && armAt > appendAt, name + ": armed after the overlay is in the document, so the first kbFit() reads a connected overlay");
    assert.doesNotMatch(src, /style\.height = .*\b(76|78|60)px/, name + ": no hard-coded row height; the floor is measured");
  }
});

// ── the sheet's rules, pinned at source ──────────────────────────────────────────────────────────
const rule = (sel: string): string => {
  const at = CSS.indexOf("\n" + sel + " {");
  assert.ok(at >= 0, sel + " is a rule in styles.css");
  return CSS.slice(at + 1, CSS.indexOf("}", at) + 1);   // from the selector to its closing brace
};

test("the answer box is a fixed flex item that holds three rows: it never absorbs the box's deficit", () => {
  const r = rule("#ut-reply-prompt .ut-reply-input");
  assert.match(r, /flex: 0 0 auto;/, "no shrink: with min-height auto resolving to 0 on a textarea, flex-shrink 1 gave it the whole deficit");
  assert.match(r, /min-height: calc\(3lh \+ 16px\);/, "three rows (rows=3) plus the 7px+7px padding and the 1px+1px border (.ut-reply-input, box-sizing border-box)");
  assert.match(rule(".ut-reply-input"), /resize: vertical;/, "the person can still pull the box taller");
  assert.match(rule(".ut-reply-input"), /box-sizing: border-box;/, "the 16px in the floor is the box's own padding and border");
  assert.match(rule(".ut-reply-input"), /padding: 7px 9px;/); assert.match(rule(".ut-reply-input"), /border: 1px solid/);
});

test("the detail is the part that gives way: it shrinks (min-height 0), is capped, and scrolls within itself", () => {
  const r = rule("#ut-reply-prompt .ut-detail.open");
  assert.match(r, /flex: 1 1 auto;/);
  assert.match(r, /min-height: 0;/, "load-bearing: a block's automatic minimum is its content, so without this it never shrinks");
  assert.match(r, /max-height: min\(12em, 35dvh\);/, "the cap: some lines of detail, never more than a third of the visible window (dvh, as the picker's fold)");
  assert.match(r, /overflow-y: auto;/, "the rest of the detail is a scroll away, never clipped (a collapsed region stays reachable)");
  assert.match(r, /overscroll-behavior: contain;/, "a swipe past its end does not scroll the box or the page under it (#pinned-notes's rule)");
  assert.match(rule("#pinned-notes"), /max-height: min\(11em, 30vh\); overflow-y: auto; overflow-x: hidden; overscroll-behavior: contain;/, "the precedent this follows");
  assert.match(rule(".ut-detail.open"), /^\.ut-detail\.open \{ display: block; \}$/, "the base rule stays: display block, no flex or cap of its own — the fix is scoped to this dialog");
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

test("the fix adds no font-size and touches no shared dialog rule", () => {
  for (const sel of ["#ut-reply-prompt .ut-reply-input", "#ut-reply-prompt .ut-detail.open", "#ut-reply-prompt.kb-tight"]) {
    assert.doesNotMatch(rule(sel), /font-size/, sel + ": no new font-size (ui/CLAUDE.md: reuse a size already on the surface)");
    assert.equal((CSS.match(new RegExp("\\n" + sel.replace(/[.#]/g, "\\$&") + " \\{", "g")) || []).length, 1, sel + " is declared once");
  }
  assert.match(CSS, /\n\.confirm-box \{ width: min\(440px, 96%\); padding: 16px 18px; gap: 10px; \}\n/, ".confirm-box is as it was: seven dialogs share it");
  assert.match(CSS, /\n\.confirm-overlay \{ display: flex; align-items: center; padding: 16px; \}\n/, ".confirm-overlay is as it was");
  const pb = rule(".picker-box");
  assert.match(pb, /max-height: calc\(100vh - 88px\);/); assert.match(pb, /display: flex; flex-direction: column;/); assert.match(pb, /overflow: hidden;/);
});
