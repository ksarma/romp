// A user-todo row must say AT A GLANCE whether more sits behind it (the user 2026-09-02): the
// postal tool's optional `detail` used to hide behind the text's click with no visible tell, so a
// bare one-line ask and one with a paragraph behind it looked identical until hovered. Now a row
// WITH detail wears a small "▸ details" hint after its text (flipping to "▾ details" while the fold
// is open) and a bare row renders nothing extra. The decision is EXECUTED here through the pure
// module; the wiring into the card and the styles are source-pinned (render.ts has no jsdom
// harness — the repo convention).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { utDetailHint, utHintFor, applyUtHint, UT_HINT_CLASS } from "../../ui/webview/user-todo-hint";

const read = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const RENDER = read("render.ts");
const CSS = read("styles.css");
const TODO = RENDER.slice(RENDER.indexOf("function renderTodo"), RENDER.indexOf("function renderCompact"));

// a stand-in for the span the renderer paints (no DOM here) — the same three surfaces
function fakeNode() {
  const attrs: Record<string, string> = {};
  return { textContent: null as string | null, title: "", attrs, setAttribute(n: string, v: string) { attrs[n] = v; } };
}

test("a todo WITH detail gets the hint: caret + word, a plain-words title, the same words for aria", () => {
  const hint = utDetailHint("OAuth vs cookie — either unblocks login", false);
  assert.ok(hint, "detail present → a hint");
  assert.equal(hint.text, "▸ details");
  assert.equal(hint.title, "has details — click to read");
  const n = fakeNode();
  applyUtHint(n, hint);
  assert.equal(n.textContent, "▸ details");
  assert.equal(n.title, "has details — click to read");
  assert.equal(n.attrs["aria-label"], "has details — click to read");
  assert.equal(UT_HINT_CLASS, "ut-more");
});

test("a todo WITHOUT detail gets NO hint — nor does a blank or whitespace-only one", () => {
  assert.equal(utDetailHint(undefined, false), null);
  assert.equal(utDetailHint(null, false), null);
  assert.equal(utDetailHint("", false), null);
  assert.equal(utDetailHint("  \n\t ", false), null);
  assert.equal(utDetailHint(undefined, true), null, "the fold state cannot conjure a hint");
});

test("the hint flips with the fold — caret down + hide words while open — so the flip acknowledges the click", () => {
  assert.deepEqual(utHintFor(true), { text: "▾ details", title: "click to hide the details" });
  assert.deepEqual(utDetailHint("some context", true), utHintFor(true));
  assert.notEqual(utHintFor(true).text, utHintFor(false).text);
  assert.notEqual(utHintFor(true).title, utHintFor(false).title);
});

test("the row paints the hint INSIDE .ut-text — the existing delegated uttoggle target, no listener of its own", () => {
  // ONE decision gates the text's click affordance, the hint, and the fold body (a blank detail renders none)
  assert.match(TODO, /const hint = utDetailHint\(t\.detail, utDetailOpen\.has\(t\.id\)\);/);
  assert.match(TODO, /if \(hint\) \{\s*\n\s*txt\.classList\.add\("ut-has-detail"\);\s*\n\s*txt\.dataset\.act = "uttoggle"; txt\.dataset\.tid = t\.id;/);
  assert.match(TODO, /txt\.title = hint\.title;/, "the text (the click target) explains itself in the same words");
  assert.match(TODO, /const more = el\("span", UT_HINT_CLASS\); applyUtHint\(more, hint\); txt\.appendChild\(more\);/);
  assert.match(TODO, /if \(hint\) \{\s*\n\s*const d = el\("div", "ut-detail"/, "the fold body renders on the same gate");
  assert.doesNotMatch(TODO, /more\.addEventListener|more\.onclick/, "no per-render listener (click-safety, ui/CLAUDE.md)");
  assert.doesNotMatch(TODO, /more\.dataset\.act/, "not its own target: a click on the hint bubbles to .ut-text's data-act");
  assert.doesNotMatch(TODO, /if \(t\.detail\)/, "no second, looser has-detail gate survives");
});

test("the uttoggle handler repaints the hint in place (open ↔ closed) alongside the fold", () => {
  const handler = RENDER.slice(RENDER.indexOf("uttoggle: (elx) => {"), RENDER.indexOf("utreply: (elx) => {"));
  assert.match(handler, /det\?\.classList\.toggle\("open", open\);/);
  assert.match(handler, /const more = elx\.querySelector<HTMLElement>\("\." \+ UT_HINT_CLASS\);/);
  assert.match(handler, /if \(more\) applyUtHint\(more, utHintFor\(open\)\);/);
  assert.match(handler, /elx\.title = utHintFor\(open\)\.title;/, "the text's own title follows the state too");
});

test("the hint wears the row's chrome rung and the dim text color — the accent is not for this", () => {
  const rule = (CSS.match(/\.ut-more \{[^}]*\}/) || [""])[0];
  assert.ok(rule, ".ut-more rule exists");
  assert.match(rule, /font-size: 0\.72em;/, "the .ut-btn / .todo-head rung: row chrome matches row chrome");
  assert.match(rule, /color: var\(--dim\);/);
  assert.match(rule, /display: inline-block;/, "so the text's dotted hover underline does not run under the hint");
  assert.match(rule, /white-space: nowrap;/, "the caret and the word never split across a wrap");
  assert.doesNotMatch(rule, /#[0-9a-f]{3,8}\b|var\(--accent/i, "tokens only, and not the accent");
  assert.match(CSS, /\.ut-has-detail:hover \.ut-more \{ color: var\(--fg\); \}/, "brightens with the text on hover, like .todo-fold:hover");
});

test("the Reply modal quotes the detail beneath the ask when there is one, in the fold's own dress", () => {
  // replying to an ask with detail should not require opening the row's fold first — the whole
  // need is in view while the answer is typed; a bare ask adds nothing to the modal
  assert.match(TODO, /\(reply as any\)\._utdetail = t\.detail \|\| "";/);
  assert.match(RENDER, /function showUserTodoReply\(sid: string, todoId: string, todoText: string, todoDetail = ""\): void/);
  const modal = RENDER.slice(RENDER.indexOf("function showUserTodoReply"), RENDER.indexOf("\nfunction ", RENDER.indexOf("function showUserTodoReply") + 10));
  assert.match(modal, /const dd = todoDetail\.trim\(\) \? el\("div", "ut-detail open"\) : null;/);
  assert.match(modal, /box\.append\(h, d\); if \(dd\) box\.appendChild\(dd\); box\.append\(input, actions\);/, "between the quoted line and the answer box");
  const handler = RENDER.slice(RENDER.indexOf("utreply: (elx) => {"), RENDER.indexOf("utdismiss: (elx) => {"));
  assert.match(handler, /showUserTodoReply\(sid, tid, \(\(elx as any\)\._uttext as string\) \|\| "", \(\(elx as any\)\._utdetail as string\) \|\| ""\);/);
});
