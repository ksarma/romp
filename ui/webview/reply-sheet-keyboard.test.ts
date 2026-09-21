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
// dialogs). Four CSS rules scoped to this dialog: the answer box never shrinks and holds three rows (min-height in
// lh); the detail is the part that gives way, capped and scrolling within itself (overflow-y: auto makes it a scroll
// container, whose automatic flex minimum is zero; #pinned-notes is the precedent) down to a floor of two of its lines
// (the picker's list keeps one row under the fold for the same reason: a region that gives way never gives way to
// nothing); a short window pins the sheet to the top under the picker's 12px frame; and the box scrolls at every
// height, the backstop for a window the floors alone overflow. In each builder one closure, kbFit, toggles kb-tight
// on THIS window's own resize (the shell sizes the pane iframe to the visible height, so the keyboard opening or
// closing IS a resize here; render.ts's picker keys on the same event, at the same 480px) and re-runs grow, and
// close() removes the listener, which also removes itself when the overlay was replaced by a second Reply; grow lets
// the box follow the answer up to the room the box has left, never under the three-row floor, and stands down for a
// height the person dragged (file-comments.ts autosize's guard).
//
// Two kinds of leg, no browser (the browser legs are waiting-reply-sheet-browser.test.ts and
// render-reply-sheet-browser.test.ts). The executed legs slice the fold's lines and the grow handler out of EACH
// builder's source (the waiting-reply-focus.test.ts idiom) and run them against stand-ins: the overlay is the shared
// shim's node (ui/test-dom-shim.ts nodeFactory; its isConnected is its tree's own answer), the window a
// listener-recording EventTarget stand-in with an innerHeight and no DOM edge, the answer box and the sheet's box
// shim nodes whose geometry is the test's input. The source legs pin the four rules' declared properties (read with
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
const CLOSE = /^\s*const close = .*$/m;
const KB_ARM = /window\.addEventListener\("resize", kbFit\);\n\s*kbFit\(\);/;
const GROW_ARM = /input\.addEventListener\("input", grow\);/;
// the grow handler is a BLOCK (its head, its statements, the `};` that closes it), sliced whole; a builder whose head or
// close moved is a loud failure here, and the browser legs slice the same block
function growBlock(src: string, name: string): string {
  const head = src.indexOf("\n  let sizedTo = \"\";");   // the drag guard's record, declared right above the handler
  assert.ok(head >= 0, "the grow block's head (let sizedTo) not found in " + name + ": re-anchor");
  assert.ok(src.indexOf("\n  const grow = () => {\n", head) > head && src.indexOf("\n  const grow = () => {\n", head) < head + 200, name + ": the grow handler follows its sizedTo line");
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
function fold(name: string, src: string, overlay: unknown, win: Win): Fold & { doc: Win; grown: () => number } {
  const doc = new Win();
  let grown = 0;
  const grow = () => { grown++; };
  const body = line(src, KBFIT, "the kbFit line", name) + "\n" + line(src, CLOSE, "the close line", name) + "\n" + line(src, KB_ARM, "the arming lines", name) + "\nreturn { kbFit, close };";
  const onKey = () => { /* the modal's Escape handler, by reference only */ };
  const onFocus = () => { /* waiting.ts's focus-return listener, by reference only */ };
  const r = new Function("overlay", "window", "document", "onKey", "onFocus", "grow", body)(overlay, win, doc, onKey, onFocus, grow) as Fold;
  return { ...r, doc, grown: () => grown };
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
function grower(name: string, src: string, input: unknown, box: unknown, win: Win): () => void {
  const body = growBlock(src, name) + "\n" + line(src, GROW_ARM, "the grow arming line", name) + "\nreturn grow;";
  return new Function("input", "box", "window", body)(input, box, win) as () => void;
}

for (const [name, src] of BUILDERS) {
  test(`${name}: the box grows with the answer from height auto, to the content's height plus the border; never under the three-row floor; capped at the ROOM the box has left, read from the box`, () => {
    // laid out at height auto the box is its floor: three rows of text, the padding and the 1px borders (78px of
    // border-box; 76px inside the border); the sheet's box fits its content (no overflow)
    const g = inputNode({ offset: 78, client: 76, scroll: 76 });
    const b = boxNode({ scroll: 400, client: 400 });
    const win = new Win(); win.innerHeight = 900;
    const grow = grower(name, src, g.input, b.box, win);
    assert.equal(g.input._listeners.input === grow, true, "armed on the box's input event");
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
    assert.deepEqual(g.fresh(), ["auto", "100px"], "no layout: the measuring auto, then the height the handler last wrote put back");
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

// ── twins ────────────────────────────────────────────────────────────────────────────────────────
test("the two builders stay twins for this fix: the same kbFit line, the same grow line, the same threshold as the picker's fold", () => {
  const [[, w], [, r]] = BUILDERS;
  assert.equal(line(w, KBFIT, "kbFit", "waiting.ts").trim(), line(r, KBFIT, "kbFit", "render.ts").trim(), "one kbFit line in both builders");
  assert.equal(growBlock(w, "waiting.ts"), growBlock(r, "render.ts"), "one grow block in both builders, byte for byte");
  for (const [name, src] of BUILDERS) {
    assert.match(line(src, KBFIT, "kbFit", name), /overlay\.classList\.toggle\("kb-tight", window\.innerHeight < 480\)/, name + ": the picker's 480px threshold (render.ts showPicker), so the two folds agree on what a short window is");
    assert.match(line(src, KBFIT, "kbFit", name), /if \(!overlay\.isConnected\) \{ window\.removeEventListener\("resize", kbFit\); return; \}/, name + ": the listener drops itself when the overlay was replaced");
    assert.match(line(src, KBFIT, "kbFit", name), /window\.innerHeight < 480\); grow\(\); \};$/, name + ": the fold re-runs grow after its own toggle, so the room is read with the fold's cap applied (executed above: one grow per resize)");
    assert.ok(src.search(KBFIT) < src.indexOf("\n  const grow = () => {\n"), name + ": kbFit is declared before grow and reads it only when called; the first call is kbFit() after the append, past grow's declaration");
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
test("the two builders share the skeleton the four rules key on, in one order, and differ exactly in where the chips go", () => {
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
    assert.match(src, /el\("div", "picker-overlay confirm-overlay"\); overlay\.id = "ut-reply-prompt";/, name + ": the overlay id the four rules are scoped to");
    assert.match(src, /const box = el\("div", "picker-box confirm-box"\);/, name + ": the box (#ut-reply-prompt .picker-box)");
    assert.match(src, /el\("div", "ut-detail open"\)/, name + ": the detail (#ut-reply-prompt .ut-detail.open)");
    assert.match(src, /input\.className = "ut-reply-input"; input\.rows = 3;/, name + ": the answer box (#ut-reply-prompt .ut-reply-input), three rows");
    assert.match(src, /const actions = el\("div", "confirm-actions"\);/, name + ": the actions row");
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
  assert.match(r, /max-height: 12em;/, "the cap at rest: 12em of the detail's own font, about eight and a half of its lines at line-height 1.4 (the browser legs pin the height at 900px to 12 times the computed font size); with the keyboard up the flex shrink and the two-line floor govern, not this. A 35dvh arm stood beside it in round 1 as the keyboard-up cap and never bound (177.8px against 134px at 508; under about 383px the shrink is already below both), so it is gone");
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

test("this dialog's box scrolls at EVERY height, on its own selector: the backstop for a window the floors alone overflow", () => {
  const r = rule("#ut-reply-prompt .picker-box");
  assert.match(r, /overflow-y: auto;/, "the shared .picker-box is overflow hidden and scrolls only under the fold (480px); above it a row laid out past the cap was clipped and not hit-testable, so a tap where Send was painted fell on the backdrop and closed the sheet with the answer (the maintainer's round 1 ruling); the box scrolls instead, at any height");
  assert.doesNotMatch(r, /max-height|height:|padding|display/, "the scroll alone: no cap of its own (an id-scoped max-height would outrank the fold's calc(100dvh - 24px) and widen this dialog's sizing)");
  assert.equal(r.replace(/\s+/g, " ").trim(), "#ut-reply-prompt .picker-box { overflow-y: auto; }", "one declaration, so the shared box rule's other declarations reach this dialog unchanged");
});

test("the fix adds no font-size and touches no shared dialog rule", () => {
  for (const sel of ["#ut-reply-prompt .ut-reply-input", "#ut-reply-prompt .ut-detail.open", "#ut-reply-prompt.kb-tight", "#ut-reply-prompt .picker-box"]) {
    assert.doesNotMatch(rule(sel), /font-size/, sel + ": no new font-size (ui/CLAUDE.md: reuse a size already on the surface)");
    assert.equal((CSS.match(new RegExp("\\n" + sel.replace(/[.#]/g, "\\$&") + " \\{", "g")) || []).length, 1, sel + " is declared once");
  }
  assert.match(CSS, /\n\.confirm-box \{ width: min\(440px, 96%\); padding: 16px 18px; gap: 10px; \}\n/, ".confirm-box is as it was: seven dialogs share it");
  assert.match(CSS, /\n\.confirm-overlay \{ display: flex; align-items: center; padding: 16px; \}\n/, ".confirm-overlay is as it was");
  const pb = rule(".picker-box");
  assert.match(pb, /max-height: calc\(100vh - 88px\);/); assert.match(pb, /display: flex; flex-direction: column;/); assert.match(pb, /overflow: hidden;/);
});
