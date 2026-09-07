// The tab menu's Emoji… opens a PICKER (2026-09-07), not a bare text field: search, a Recent row, the grid by
// category with a jump strip, and a footer for typing or pasting one plus Clear. Source pins against
// render.ts, styles.css and the guide (the dialog builds DOM at click time; no jsdom for the chat render, the
// tab-color-picker idiom). The pure half (filter, recents, sections, the keyboard model) runs for real in
// emoji-picker.test.ts; the curated list's shape in emoji-data.test.ts; the contract inherited from the
// one-field dialog (ack before post, the kernel's verdict drives the dialog, the warn router) stays pinned
// in vscode-extension/src/tab-emoji.test.ts.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { EMOJI_GRID_COLS } from "./emoji-picker";

const ui = (...p: string[]) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", ...p), "utf8");
const RENDER = ui("webview", "render.ts");
const CSS = ui("webview", "styles.css");
const GUIDE = fs.readFileSync(path.resolve(process.cwd(), "..", "docs", "guide.md"), "utf8");

function slice(from: string, to: string): string {
  const i = RENDER.indexOf(from);
  assert.ok(i > 0, `render.ts has ${JSON.stringify(from)}`);
  const j = RENDER.indexOf(to, i);
  assert.ok(j > i, `render.ts has ${JSON.stringify(to)} after ${JSON.stringify(from)}`);
  return RENDER.slice(i, j);
}
const DIALOG = slice("function showEmojiPrompt(sid: string): void {", "\nfunction emojiLanded(");

test("the same Emoji… row opens it, its icon still the current emoji or the smiley; the dialog is a menu-vocabulary card, not a modal", () => {
  const i = RENDER.indexOf('l.textContent = "Emoji…"');
  const row = RENDER.slice(i - 900, i + 700);
  assert.match(row, /ic\.textContent = curEmoji; ic\.setAttribute\("aria-hidden", "true"\);/);
  assert.match(row, /else em\.appendChild\(ctxIcon\("smile", false\)\);/);
  assert.match(row, /dismissTabMenu\(\); showEmojiPrompt\(id\);/);
  assert.match(DIALOG, /const card = el\("div", "ctx-menu emoji-picker"\); card\.id = "emoji-picker";/);
  assert.match(DIALOG, /card\.setAttribute\("role", "dialog"\)/);
  assert.doesNotMatch(DIALOG, /picker-overlay|confirm-overlay|confirm-box/, "no backdrop, no modal: the swatches' floating arrangement");
  // top to bottom: title, search, the category strip, the scrolling grid, the hint line, the footer
  assert.match(DIALOG, /card\.appendChild\(title\); card\.appendChild\(search\); card\.appendChild\(cats\); card\.appendChild\(scroll\);\n\s*card\.appendChild\(hint\); card\.appendChild\(foot\);/);
  assert.match(DIALOG, /for \(const c of EMOJI_CATEGORIES\)/);   // the strip: one button per curated category
  assert.match(RENDER, /import \{ EMOJI_CATEGORIES \} from "\.\/emoji-data";/);
  assert.match(RENDER, /import \{ EMOJI_RECENT_KEY, gridSections, moveInGrid, parseRecentEmoji, rememberEmoji \} from "\.\/emoji-picker";/);
});

test("anchoring and dismissal follow the color swatches: where the menu stood, clamped; closed by an outside mousedown, Escape, or a menu opening; never by scroll or blur", () => {
  // the menu records its clamped corner; the picker opens there, clamped again for its own size
  assert.match(RENDER, /let ctxMenuAt: \{ x: number; y: number \} \| null = null;/);
  assert.match(RENDER, /menu\.style\.left = mx \+ "px";\n\s*menu\.style\.top = my \+ "px";\n\s*ctxMenuAt = \{ x: mx, y: my \};/);
  assert.match(DIALOG, /const at = ctxMenuAt \|\| \{ x: \(window\.innerWidth - r\.width\) \/ 2, y: \(window\.innerHeight - r\.height\) \/ 3 \};/);
  assert.match(DIALOG, /card\.style\.left = Math\.max\(0, Math\.min\(at\.x, window\.innerWidth - r\.width - 4\)\) \+ "px";/);
  assert.match(DIALOG, /card\.style\.top = Math\.max\(0, Math\.min\(at\.y, window\.innerHeight - r\.height - 4\)\) \+ "px";/);
  // dismissal
  assert.match(RENDER, /window\.addEventListener\("mousedown", \(e\) => \{ if \(emojiPrompt && !emojiPrompt\.card\.contains\(e\.target as Node\)\) closeEmojiPrompt\(\); \}, true\);/);
  assert.match(RENDER, /window\.addEventListener\("keydown", \(e\) => \{ if \(e\.key === "Escape" && emojiPrompt\) \{ e\.stopPropagation\(\); closeEmojiPrompt\(\); \} \}, true\);/);
  assert.match(RENDER, /function showTabMenu\(e: MouseEvent, id: string\) \{\n  dismissTabMenu\(\);\n  closeEmojiPrompt\(\);/);
  // the menu's scroll and blur closers do NOT reach the picker: its grid scrolls, and its field invites a paste
  assert.doesNotMatch(RENDER, /addEventListener\("scroll", closeEmojiPrompt/);
  assert.doesNotMatch(RENDER, /addEventListener\("blur", [^\n]*closeEmojiPrompt/);
  assert.doesNotMatch(slice("function dismissTabMenu() {", "\n}"), /closeEmojiPrompt/,
                      "dismissTabMenu runs on every window scroll; hanging the picker off it would close it on its own grid scroll");
  // the picker's own Escape listener of the old dialog is gone: the window-level one closes it
  assert.doesNotMatch(DIALOG, /document\.addEventListener\("keydown"/);
});

test("the search box filters as you type (the pure filter), Down enters the grid, Enter picks the first result", () => {
  assert.match(DIALOG, /search\.addEventListener\("input", paint\);/);
  assert.match(DIALOG, /sections = gridSections\(search\.value, recents\);/);
  assert.match(DIALOG, /if \(e\.key === "ArrowDown"\) \{ e\.preventDefault\(\); focusCell\(gridFocus\); \}/);
  assert.match(DIALOG, /else if \(e\.key === "Enter" && search\.value\.trim\(\)\) \{\n\s*e\.preventDefault\(\);\n\s*const top = sections\[0\]\?\.cells\[0\];[^\n]*\n\s*if \(top\) pick\(top\[0\]\);/);
  // a fruitless search says so and points at the field, never a blank
  assert.match(DIALOG, /none\.textContent = "No match\. Type or paste one below\.";/);
  // the strip has nothing to jump to while one Results section shows
  assert.match(DIALOG, /cats\.classList\.toggle\("off", searching\);/);
  assert.match(CSS, /\.emoji-cats\.off \{ opacity: 0\.4; pointer-events: none; \}/);
  assert.match(DIALOG, /search\.placeholder = "Search";/);
});

test("the Recent row: read from localStorage under the namespaced key, written only when a pick LANDS (a clear is not a pick)", () => {
  assert.match(RENDER, /function readRecentEmoji\(\): string\[\] \{\n\s*try \{ return parseRecentEmoji\(localStorage\.getItem\(EMOJI_RECENT_KEY\)\); \} catch \{ return \[\]; \}/);
  assert.match(RENDER, /function rememberRecentEmoji\(emoji: string\): void \{\n\s*try \{ localStorage\.setItem\(EMOJI_RECENT_KEY, JSON\.stringify\(rememberEmoji\(readRecentEmoji\(\), emoji\)\)\); \} catch/);
  assert.match(DIALOG, /let recents = readRecentEmoji\(\);/);
  const landed = slice("function emojiLanded(sid: string, emoji: string): void {", "\nfunction emojiRefusedLocal(");
  assert.match(landed, /if \(!emojiConfirmClosesDialog\(emojiPrompt, sid, emoji\)\) return;\n\s*if \(emoji\) rememberRecentEmoji\(emoji\);\n\s*closeEmojiPrompt\(\);/);
  // never at pick time: a refused typed value must not become a recent
  assert.doesNotMatch(DIALOG, /rememberRecentEmoji/);
});

test("the grid: real buttons per cell, click-safe by DELEGATION to the card, the current emoji marked, category headers and a strip that jumps to them", () => {
  assert.match(DIALOG, /const b = el\("button", "emoji-cell" \+ \(emoji === cur \? " cur" : ""\)\) as HTMLButtonElement;/);
  assert.match(DIALOG, /b\.type = "button"; b\.dataset\.act = "pick"; b\.dataset\.emoji = emoji; b\.dataset\.s = String\(s\); b\.dataset\.i = String\(i\);/);
  assert.match(DIALOG, /b\.title = nm; b\.setAttribute\("aria-label", nm\); b\.textContent = emoji;/);
  // the cells are rebuilt on every search keystroke (scroll.replaceChildren), so no action hangs on a cell:
  // ONE delegate on the card, installed once per open, routes pick and cat by data-act (actions.ts)
  assert.match(DIALOG, /scroll\.replaceChildren\(frag\);/);
  assert.match(DIALOG, /delegate\(card, \{ pick: \(b\) => pick\(b\.dataset\.emoji \|\| ""\), cat: \(b\) => jumpTo\(b\.dataset\.cat \|\| ""\) \}\);/);
  assert.doesNotMatch(DIALOG, /b\.addEventListener\("click"/, "no per-cell click handler");
  assert.doesNotMatch(DIALOG, /b\.onclick/, "no per-cell click handler");
  assert.match(RENDER, /import \{ delegate \} from "\.\/actions";/);
  // headers + the strip
  assert.match(DIALOG, /const h = el\("div", "emoji-sec-h"\); h\.textContent = sec\.label;/);
  assert.match(DIALOG, /b\.type = "button"; b\.tabIndex = -1; b\.dataset\.act = "cat"; b\.dataset\.cat = c\.id;/);
  assert.match(DIALOG, /if \(sec\) scroll\.scrollTop = sec\.offsetTop;/);
  assert.match(DIALOG, /scroll\.addEventListener\("scroll", markCat\);/);   // the strip's current mark follows the scroll (an event, not a timer)
  assert.match(CSS, /\.emoji-sec-h \{ position: sticky; top: 0;/);
  assert.match(CSS, /\.emoji-scroll \{ position: relative;/);   // offsetTop of a section is relative to the scroll box
  // the column count the keyboard model moves by is the one the sheet draws
  assert.match(CSS, new RegExp("\\.emoji-grid \\{ display: grid; grid-template-columns: repeat\\(" + EMOJI_GRID_COLS + ", 1fr\\);"));
  // the current emoji and the focused cell wear the accent, never a status color
  assert.match(CSS, /\.emoji-cell\.cur \{ box-shadow: inset 0 0 0 2px var\(--accent\); \}/);
  assert.match(CSS, /\.emoji-cell:focus-visible \{ outline: none; background: var\(--menu-hover\); box-shadow: inset 0 0 0 2px var\(--accent\); \}/);
});

test("keyboard: roving tabindex (one stop for the Recent row, one for the grid), arrows through moveInGrid, Enter/Space left to the button", () => {
  assert.match(DIALOG, /let gridFocus: GridPos = \{ section: 0, index: 0 \};/);
  assert.match(DIALOG, /let recentFocus = 0;/);
  assert.match(DIALOG, /b\.tabIndex = i === f \? 0 : -1;/);
  assert.match(DIALOG, /const next = moveInGrid\(sections\.map\(\(s\) => s\.cells\.length\),\n\s*\{ section: \+\(b\.dataset\.s \|\| 0\), index: \+\(b\.dataset\.i \|\| 0\) \}, e\.key\);/);
  assert.match(DIALOG, /if \(!next\) return;[^\n]*\n\s*e\.preventDefault\(\); focusCell\(next\);/);
  // the moved-to cell joins the Tab order and the moved-from leaves it; the grid's stop starts on the current emoji
  assert.match(DIALOG, /if \(was\) was\.tabIndex = -1;/);
  assert.match(DIALOG, /b\.tabIndex = 0; b\.focus\(\{ preventScroll: true \}\);/);
  assert.match(DIALOG, /if \(k >= 0\) \{ gridFocus = \{ section: s, index: k \}; break; \}/);
  // the footer: Enter in the field sets; the field is prefilled with the current emoji
  assert.match(DIALOG, /input\.addEventListener\("keydown", \(e\) => \{ if \(e\.key === "Enter"\) \{ e\.preventDefault\(\); start\(\); \} \}\);/);
  assert.match(DIALOG, /input\.value = cur;/);
  assert.match(DIALOG, /input\.placeholder = "or type or paste one";/);
  assert.match(DIALOG, /search\.focus\(\);\n\}/, "the search box takes focus on open");
});

test("a pick and a typed value go through the SAME door (setSessionEmoji, the kernel validates); the Set button acknowledges either; the reason lands inline", () => {
  assert.match(DIALOG, /const pick = \(emoji: string\) => \{ if \(emoji\) submit\(emoji, go, "Setting…"\); \};/);
  assert.match(DIALOG, /submit\(v, go, "Setting…"\)/);
  assert.match(DIALOG, /setSessionEmoji\(sid, value\);/);
  const submits = DIALOG.match(/setSessionEmoji\(/g) || [];
  assert.equal(submits.length, 1, "one post site for cells and typed values alike");
  // no client-side judgment of the value: the kernel's validator is the one authority
  assert.doesNotMatch(DIALOG, /Segmenter|\\p\{Emoji|codePointAt/, "the dialog does not pre-judge what is an emoji");
  // the pending state: the picked cell dims, the cells lock, Set/Clear/the field lock (the inherited ack)
  assert.match(DIALOG, /card\.classList\.add\("waiting"\);/);   // not "pending": comments.test.ts bans that one-off class name in render.ts
  assert.match(DIALOG, /c\.classList\.toggle\("busy", c\.dataset\.emoji === value\)/);
  assert.match(CSS, /\.emoji-picker\.waiting \.emoji-cell, \.emoji-picker\.waiting \.emoji-cat \{ pointer-events: none; \}/);
  // the refusal restores all of it; the field is marked only when IT held the refused value
  const refused = slice("function emojiRefusedLocal(text: string): void {", "\n}");
  assert.match(refused, /p\.card\.classList\.remove\("waiting"\);/);
  assert.match(refused, /\.emoji-cell\.busy"\)\.forEach\(\(c\) => c\.classList\.remove\("busy"\)\);/);
  assert.match(refused, /p\.hint\.textContent = text; p\.hint\.title = text; p\.hint\.className = "emoji-hint bad";/);
  assert.match(DIALOG, /p\.typed = value === input\.value\.trim\(\);/);   // noted at submit time: the refusal must not read the field (tab-emoji.test.ts)
  assert.match(refused, /if \(p\.typed\) \{ p\.input\.classList\.add\("bad"\); p\.input\.focus\(\); \}/);
});

test("Clear: present in the footer, disabled and dressed as disabled with nothing to clear, posts \"\" (the inherited contract)", () => {
  assert.match(DIALOG, /clear\.disabled = !cur;/);
  assert.match(DIALOG, /clear\.addEventListener\("click", \(\) => submit\("", clear, "Clearing…"\)\);/);
  assert.match(DIALOG, /foot\.appendChild\(input\); foot\.appendChild\(clear\); foot\.appendChild\(go\);/);
  assert.match(CSS, /\.picker-action:disabled \{ opacity: 0\.55; cursor: default; \}/);
});

test("the guide's emoji paragraph names the picker: search, the Recent row, the categories, or type or paste one", () => {
  assert.match(GUIDE, /choose \*\*Emoji…\*\*\s+for a picker: search by name or keyword, take one from the \*\*Recent\*\* row, browse\s+the categories, or type or paste one the list does not have\./);
});
