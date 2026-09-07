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
import { viewTagUnion } from "./session-views";
import { parseTabGroups, planStrip, setSectionCollapsed, homeSectionOf } from "./tab-groups";

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
// a slice INSIDE the dialog (the move and fork dialogs define a `close` of their own before it)
function dialogSlice(from: string, to: string): string {
  const i = DIALOG.indexOf(from);
  assert.ok(i > 0, `the dialog has ${JSON.stringify(from)}`);
  const j = DIALOG.indexOf(to, i);
  assert.ok(j > i, `the dialog has ${JSON.stringify(to)} after ${JSON.stringify(from)}`);
  return DIALOG.slice(i, j);
}
// the notes-api demo world (tab-groups.test.ts): qa holds tests and api, infra holds web and api
const V = {
  active: "all",
  tags: [
    { id: "g1", name: "qa", color: "#DD42FF", members: ["tests", "api"] },
    { id: "g2", name: "infra", color: "#4EC9B0", members: ["web", "api"] },
  ],
};

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
  assert.match(RENDER, /import \{ EMOJI_RECENT_KEY, gridSections, moveInGrid, parseRecentEmoji, rememberEmoji, sameEmoji \} from "\.\/emoji-picker";/);
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
  assert.match(RENDER, /window\.addEventListener\("keydown", \(e\) => \{ if \(e\.key === "Escape" && emojiPrompt\) \{ e\.stopPropagation\(\); e\.preventDefault\(\); closeEmojiPrompt\(\); \} \}, true\);/);
  assert.match(RENDER, /function showTabMenu\(e: MouseEvent, id: string\) \{\n  dismissTabMenu\(\);\n  closeEmojiPrompt\(\);/);
  // the menu's scroll and blur closers do NOT reach the picker: its grid scrolls, and its field invites a paste
  assert.doesNotMatch(RENDER, /addEventListener\("scroll", closeEmojiPrompt/);
  assert.doesNotMatch(RENDER, /addEventListener\("blur", [^\n]*closeEmojiPrompt/);
  assert.doesNotMatch(slice("function dismissTabMenu() {", "\n}"), /closeEmojiPrompt/,
                      "dismissTabMenu runs on every window scroll; hanging the picker off it would close it on its own grid scroll");
  // the picker's own Escape listener of the old dialog is gone: the window-level one closes it
  assert.doesNotMatch(DIALOG, /document\.addEventListener\("keydown"/);
});

test("the search box filters as you type (the pure filter), Down goes to the next Tab stop (the Recent row when there is one), Enter picks the first result", () => {
  assert.match(DIALOG, /search\.addEventListener\("input", paint\);/);
  assert.match(DIALOG, /sections = gridSections\(search\.value, recents\);/);
  // Down used to land on the grid's stop (the current emoji, far down the list) and skip the Recent row directly
  // beneath the box, where Tab goes (review round 1): both keys now reach the same first stop
  assert.match(DIALOG, /if \(e\.key === "ArrowDown"\) \{ e\.preventDefault\(\); focusCell\(isRecent\(0\) \? \{ section: 0, index: recentFocus \} : gridFocus\); \}/);
  assert.match(DIALOG, /const isRecent = \(s: number\) => sections\[s\]\?\.id === "recent";/);
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
  // the ring and the grid's starting stop compare U+FE0F-insensitively (sameEmoji, emoji-picker.ts, tested there):
  // the kernel stores either form unchanged, so a tab set by `romp emoji` with the bare form still finds its cell
  assert.match(DIALOG, /const isCur = sameEmoji\(emoji, cur\);[^\n]*\n\s*const b = el\("button", "emoji-cell" \+ \(isCur \? " cur" : ""\)\) as HTMLButtonElement;/);
  assert.match(DIALOG, /const k = sections\[s\]\.cells\.findIndex\(\(c\) => sameEmoji\(c\[0\], cur\)\);/);
  assert.doesNotMatch(DIALOG, /=== cur\b/, "no exact-string comparison against the current emoji");
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
  assert.match(DIALOG, /const pick = \(emoji: string\) => \{ if \(emoji\) submit\(emoji, go, "Setting…", false\); \};/);
  assert.match(DIALOG, /submit\(v, go, "Setting…", true\)/);
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
  assert.match(DIALOG, /p\.typed = fromField;/);   // noted at submit time, by the caller: the refusal must not read the field (tab-emoji.test.ts)
  assert.match(refused, /if \(p\.typed\) \{ p\.input\.classList\.add\("bad"\); p\.input\.focus\(\); \}/);
});

test("Clear: present in the footer, disabled and dressed as disabled with nothing to clear, posts \"\" (the inherited contract)", () => {
  assert.match(DIALOG, /clear\.disabled = !cur;/);
  assert.match(DIALOG, /clear\.addEventListener\("click", \(\) => submit\("", clear, "Clearing…", false\)\);/);
  assert.match(DIALOG, /foot\.appendChild\(input\); foot\.appendChild\(clear\); foot\.appendChild\(go\);/);
  assert.match(CSS, /\.picker-action:disabled \{ opacity: 0\.55; cursor: default; \}/);
});

test("the guide's emoji paragraph names the picker: search, the Recent row, the categories, or type or paste one", () => {
  assert.match(GUIDE, /choose \*\*Emoji…\*\*\s+to open a picker: search by name or keyword, reuse one from the \*\*Recent\*\* row,\s+browse the categories, or type or paste one the list does not have\./);
});

test("the reference describes the picker, not the one-field dialog: every sender, the hint ABOVE the field, the Recent row, the local empty-Set refusal", () => {
  const REF = fs.readFileSync(path.resolve(process.cwd(), "..", "docs", "reference.md"), "utf8");
  const bullet = REF.slice(REF.indexOf("- **The tab.** Right-click it and choose **Emoji…**"), REF.indexOf("- **The session itself.**"));
  assert.ok(bullet.length > 0, "the tab bullet exists and precedes the session bullet");
  const flat = bullet.replace(/\s+/g, " ");   // wrap-tolerant: the pins are phrases, not line breaks
  // what sends: a cell, Enter in the search box (the first result), Set with a typed value; the same op
  assert.ok(flat.includes("Clicking a cell, Enter in the search box (the first result) and **Set** with a typed value all send the same `setSessionEmoji` WebSocket op"), "the three senders");
  assert.match(DIALOG, /const top = sections\[0\]\?\.cells\[0\];/);   // the premise: Enter in the search box picks the first result
  assert.ok(flat.includes('`emoji: ""` clears, and **Clear** sends exactly that'), "the Clear contract");
  assert.ok(flat.includes("only the kernel judges the value"), "no client-side judgment");
  // the picker stays open; the confirm closes it and files the emoji as a recent
  assert.ok(flat.includes("The picker stays open for the answer."), "stays open");
  assert.ok(flat.includes("the picker closes, and the emoji joins the Recent row"), "the confirm closes it and files a recent");
  // the hint sits ABOVE the field (card.appendChild(hint); card.appendChild(foot)), not "under the input"
  assert.ok(flat.includes("shows in its hint line above the field, with a typed value left in the field to fix"), "the hint above the field");
  assert.doesNotMatch(flat, /under the input|The dialog's \*\*Set\*\*/, "the one-field dialog's wording is gone");
  assert.ok(flat.includes("**Set** with the field empty is refused in place, without a round trip: to clear, use **Clear**."), "the local empty-Set refusal");
});

test("Set with the field empty: the mark is VISIBLE (a rule matches the class the field wears) and the hint says why; a later submit drops both", () => {
  // the picker's field wears ctx-tag-input emoji-pick; the old dialog's .fork-name.bad rule matched nothing on
  // it, so Set with an empty field acknowledged nothing (review round 1, measured in Chromium)
  assert.match(DIALOG, /input\.type = "text"; input\.className = "ctx-tag-input emoji-pick";/);
  assert.match(CSS, /\.emoji-foot \.emoji-pick\.bad \{ border-color: #e5484d; background: rgba\(229, 72, 77, 0\.07\); \}/);
  assert.match(DIALOG, /if \(!v\) \{[^\n]*\n\s*input\.classList\.add\("bad"\); input\.focus\(\);\n\s*hint\.textContent = EMPTY_SET; hint\.title = EMPTY_SET; hint\.className = "emoji-hint bad";\n\s*return;\n\s*\}/);
  assert.match(RENDER, /const EMPTY_SET = "Pick an emoji, or type or paste one\.";/);
  // the submit resets the hint AND the field's mark, so a stale red border cannot ride through a later cell pick
  assert.match(DIALOG, /hint\.textContent = ""; hint\.title = ""; hint\.className = "emoji-hint"; input\.classList\.remove\("bad"\);/);
  assert.match(DIALOG, /input\.addEventListener\("input", \(\) => input\.classList\.remove\("bad"\)\);/);
});

test("while a pick waits, the search box locks with the field and the buttons (a keystroke repainted the grid and dropped the .busy cue); the refusal unlocks it", () => {
  assert.match(DIALOG, /go\.disabled = true; clear\.disabled = true; input\.disabled = true; search\.disabled = true;/);
  const refused = slice("function emojiRefusedLocal(text: string): void {", "\n}");
  assert.match(refused, /p\.input\.disabled = false; p\.search\.disabled = false;/);
  // the repaint the lock prevents: the search's input handler rebuilds every cell without .busy
  assert.match(DIALOG, /search\.addEventListener\("input", paint\);/);
});

test("focus never falls to <body>: a submit parks it on the card before disabling its holder, a refusal hands it back, a close returns it to the tab", () => {
  assert.match(DIALOG, /card\.tabIndex = -1;/);   // focusable by script, never a Tab stop
  const submit = dialogSlice("const submit = (value: string, btn: HTMLButtonElement, busy: string, fromField: boolean) => {", "const pick =");
  // parked BEFORE the disabling line, and only when a control about to be disabled holds it (a cell keeps its own)
  const park = submit.indexOf("if (a === search || a === input || a === go || a === clear) card.focus({ preventScroll: true });");
  const lock = submit.indexOf("go.disabled = true; clear.disabled = true; input.disabled = true; search.disabled = true;");
  assert.ok(park > 0 && lock > park, "the focus moves to the card before the control that held it is disabled");
  assert.match(submit, /const a = document\.activeElement;/);
  assert.match(CSS, /\.emoji-picker:focus \{ outline: none; \}/);   // a parking spot, not a control: no ring around the whole card
  // the refusal: the field when it held the value (the inherited rule); else the button that was pressed
  const refused = slice("function emojiRefusedLocal(text: string): void {", "\n}");
  assert.match(refused, /if \(p\.typed\) \{ p\.input\.classList\.add\("bad"\); p\.input\.focus\(\); \}\n\s*else if \(document\.activeElement === p\.card\) \(p\.asked === "" \? p\.clear : p\.go\)\.focus\(\);/);
  // the close: back to this session's tab, but only when the card held focus (a right-click reopening the menu
  // has already focused ITS tab, which may be another session's); the tab gone meanwhile: the next test
  const close = dialogSlice("const close = () => {", "\n  };");
  assert.match(close, /const held = card\.contains\(document\.activeElement\);\n\s*card\.remove\(\);\n\s*if \(!held\) return;/,
               "read before the removal (removing the focused card would already have dropped focus); nothing moves when the card did not hold it");
  assert.match(close, /const tab = bar\?\.querySelector\(`\.tab\[data-id="\$\{sid\}"\]`\) as HTMLElement \| null;\n\s*if \(tab\) \{ tab\.focus\(\); return; \}/);
  // the tab bar's own refocus addresses a tab by #tabs .tab[data-id] and falls back to the section header when
  // the active tab is folded away (tab-groups.ts): the ladder the close borrows
  assert.match(RENDER, /function focusActiveTab\(\) \{\n\s*const bar = document\.getElementById\("tabs"\);\n\s*const tab = bar\?\.querySelector\(`\.tab\[data-id="\$\{activeId\}"\]`\) as HTMLElement \| null;\n\s*if \(tab\) \{ tab\.focus\(\); return; \}/,
               "the premise: the tab bar's own refocus addresses a tab by #tabs .tab[data-id]");
});

test("a refusal marks the field only when IT sent the value: the caller says so (fromField); a pick of the current emoji's cell and Clear on an emptied field are not typed (review round 2)", () => {
  // the field is prefilled with the tab's emoji (input.value = cur), so `p.typed = value === input.value.trim()`
  // read a pick of that emoji's cell as typed, and Clear too once the field was emptied; on a refusal or the
  // 30 s backstop the field then turned red and took focus with nothing wrong in it, and the pressed control
  // never got focus back. The flag is the caller's, never inferred from the value.
  assert.match(DIALOG, /const submit = \(value: string, btn: HTMLButtonElement, busy: string, fromField: boolean\) => \{/);
  assert.match(DIALOG, /p\.pending = true; p\.asked = value;\n\s*p\.typed = fromField;/);
  assert.doesNotMatch(DIALOG, /typed = value ===|typed = [^\n]*input\.value/, "no comparison of the value with the field");
  // the three doors: the field's Enter and the Set button both run start, which says yes; a cell (the grid, the
  // Recent row, Enter in the search box) and Clear say no
  assert.match(DIALOG, /const start = \(\) => \{\n\s*const v = input\.value\.trim\(\);[^]*?submit\(v, go, "Setting…", true\);\n\s*\};/);
  assert.match(DIALOG, /input\.addEventListener\("keydown", \(e\) => \{ if \(e\.key === "Enter"\) \{ e\.preventDefault\(\); start\(\); \} \}\);/);
  assert.match(DIALOG, /go\.addEventListener\("click", start\);/);
  assert.match(DIALOG, /const pick = \(emoji: string\) => \{ if \(emoji\) submit\(emoji, go, "Setting…", false\); \};/);
  assert.match(DIALOG, /if \(top\) pick\(top\[0\]\);/);   // the search box's Enter is a pick
  assert.match(DIALOG, /clear\.addEventListener\("click", \(\) => submit\("", clear, "Clearing…", false\)\);/);
  const calls = DIALOG.match(/\bsubmit\([^)]*\)/g) || [];
  assert.equal(calls.length, 3, "three call sites: start, pick, Clear");
  assert.deepEqual(calls.filter((c) => !/, (true|false)\)$/.test(c)), [], "every call names the flag as a literal");
  // the refusal reads the flag, never the field: the field when it sent the value, else the pressed control
  const refused = slice("function emojiRefusedLocal(text: string): void {", "\n}");
  assert.match(refused, /if \(p\.typed\) \{ p\.input\.classList\.add\("bad"\); p\.input\.focus\(\); \}\n\s*else if \(document\.activeElement === p\.card\) \(p\.asked === "" \? p\.clear : p\.go\)\.focus\(\);/);
  assert.doesNotMatch(refused, /input\.value/);
});

test("a close with the tab gone from the strip (closed from another client, or re-homed into a folded section while the picker sat open) still hands focus on: the section head, else the active tab (review round 2)", () => {
  // the card lives on document.body and outlives every strip rebuild; the tab was on screen when the menu
  // opened on it, not necessarily at close time. Focusing the missing tab with `?.focus()` did nothing and
  // the removed card's focus fell to <body>, against the module's own rule.
  const close = dialogSlice("const close = () => {", "\n  };");
  assert.match(close, /const home = homeSectionOf\(lastStripItems, sid\);/, "the rendered plan's answer for THIS sid, not the active id");
  assert.match(close, /const head = home && home\.name !== null && bar\n\s*\? Array\.from\(bar\.querySelectorAll<HTMLElement>\("\.tab-group-head"\)\)\.find\(\(h\) => h\.dataset\.group === home\.name\) : undefined;/);
  assert.match(close, /if \(head\) head\.focus\(\); else focusActiveTab\(\);/, "the head, else the active tab");
  assert.doesNotMatch(close, /\?\.focus\(\)/, "no optional-chained focus that silently does nothing");
  // the same two fallbacks the tab bar uses: focusActiveTab lands on the header when the active tab is folded
  // away, and renderTabs lands on the active tab when the header a focused node sat in is gone
  assert.match(RENDER, /const home = activeId \? homeSectionOf\(lastStripItems, activeId\) : null;\n\s*if \(!home \|\| home\.name === null \|\| !bar\) return;\n\s*Array\.from\(bar\.querySelectorAll<HTMLElement>\("\.tab-group-head"\)\)\.find\(\(h\) => h\.dataset\.group === home\.name\)\?\.focus\(\);/);
  assert.match(RENDER, /if \(h && h\.tabIndex >= 0\) [^\n]*\.focus\(\); else focusActiveTab\(\);/);
  assert.match(RENDER, /head\.dataset\.group = name;[^]*?head\.tabIndex = 0;/, "a section head is focusable and carries its name in data-group");
  // executed, on the real planner: the two ways the tab leaves the strip while the card stays up
  const unions = viewTagUnion(V);
  const st = parseTabGroups(null);
  const onTab = (items: ReturnType<typeof planStrip>["items"], id: string) => items.some((i) => "id" in i && i.id === id);
  const open = planStrip(["web", "api", "tests"], unions, st, "api", false);
  assert.ok(onTab(open.items, "web"), "the tab is on the strip when the menu opens on it");
  const folded = planStrip(["web", "api", "tests"], unions, setSectionCollapsed(st, "infra", true), "api", false);
  assert.ok(!onTab(folded.items, "web"), "re-homed under a fold: no tab node to focus");
  assert.equal(homeSectionOf(folded.items, "web")?.name, "infra", "its section head is the stand-in");
  const gone = planStrip(["api", "tests"], unions, st, "api", false);
  assert.ok(!onTab(gone.items, "web"));
  assert.equal(homeSectionOf(gone.items, "web"), null, "closed from another client: no home either, so the active tab takes it");
});

test("assistive semantics: the hint is a live region; the scroll box is a listbox of one group per section whose options are the cells, named and selected", () => {
  assert.match(DIALOG, /hint\.setAttribute\("role", "status"\); hint\.setAttribute\("aria-live", "polite"\);/);
  assert.match(DIALOG, /scroll\.setAttribute\("role", "listbox"\); scroll\.setAttribute\("aria-label", "Emoji"\);/);
  assert.match(DIALOG, /h\.id = "emoji-sec-" \+ sec\.id; box\.appendChild\(h\);\n\s*box\.setAttribute\("role", "group"\); box\.setAttribute\("aria-labelledby", h\.id\);/);
  assert.match(DIALOG, /b\.setAttribute\("role", "option"\); b\.setAttribute\("aria-selected", isCur \? "true" : "false"\);/);
  assert.match(DIALOG, /b\.setAttribute\("aria-label", nm\);/);   // the cell's name, not its glyph, is what a reader speaks
  // the feed toast is the repo's precedent for role=status
  assert.match(fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "feed.ts"), "utf8"), /setAttribute\("role", "status"\)/);
});

test("the strip's mark at both ends (stripMarkAt, executed): the Recent row counts as the first category; at the end the last section is marked", () => {
  const m = RENDER.match(/function stripMarkAt\(ids: readonly string\[\], tops: readonly number\[\], scrollTop: number, clientHeight: number,\n\s*scrollHeight: number\): string \| null \{([^]*?)\n\}/);
  assert.ok(m, "the pure function exists with the pinned signature");
  const mark = new Function("ids", "tops", "scrollTop", "clientHeight", "scrollHeight", m![1]) as
    (ids: string[], tops: number[], scrollTop: number, clientHeight: number, scrollHeight: number) => string | null;
  // the reviewer's geometry: a Recent row at 0, nine categories, a 304px box over 2953px of content
  const ids = ["recent", "smileys", "people", "animals", "food", "travel", "activities", "objects", "symbols", "flags"];
  const tops = [0, 90, 400, 800, 1150, 1500, 1800, 2060, 2400, 2787];
  const H = 304, S = 2953;
  assert.equal(mark(ids, tops, 0, H, S), "smileys", "at the top with a Recent row: the first category, not nothing");
  assert.equal(mark(ids.slice(1), tops.slice(1).map((t) => t - 90), 0, H, S - 90), "smileys", "at the top without one: the first category");
  assert.equal(mark(ids, tops, 2060, H, S), "objects", "a jump lands a header at the top: that category");
  assert.equal(mark(ids, tops, 2061, H, S), "objects", "the +1 tolerance for a fractional scrollTop");
  assert.equal(mark(ids, tops, S - H, H, S), "flags", "at the end (Flags cannot reach the top: the box clamps at 2649 < 2787): the last section");
  assert.equal(mark(ids, tops, S - H - 1, H, S), "flags", "the same 1px tolerance at the end (a fractional scrollTop)");
  assert.equal(mark(ids, tops, S - H - 2, H, S), "symbols", "short of the end: the top rule");
  assert.equal(mark(ids, tops, 1500, H, S), "travel");
  assert.equal(mark(ids, tops, 1498, H, S), "food");
  // a box that does not scroll (content shorter than the box) is never "at the end": the top rule alone
  assert.equal(mark(["recent", "smileys"], [0, 90], 0, 400, 300), "smileys");
  assert.equal(mark(["results"], [0], 0, 304, 2000), "results", "a search's one section: whatever it is named (the strip is off then)");
  assert.equal(mark([], [], 0, 304, 0), null, "no sections: nothing marked");
  // wired: markCat feeds it the sections' data-sec and offsetTop and the box's three measures
  assert.match(DIALOG, /const at = stripMarkAt\(secs\.map\(\(x\) => x\.dataset\.sec \|\| ""\), secs\.map\(\(x\) => x\.offsetTop\),\n\s*scroll\.scrollTop, scroll\.clientHeight, scroll\.scrollHeight\);/);
  assert.match(DIALOG, /b\.classList\.toggle\("cur", b\.dataset\.cat === at\)/);
});

test("Set and Clear hover with the menu's own wash on both themes (the base .picker-action hover is a white wash the light card swallows)", () => {
  assert.match(CSS, /\.emoji-foot \.picker-action:hover:not\(:disabled\) \{ background: var\(--menu-hover\); \}/);
  // after the base rules, so it wins by order; :not(:disabled) leaves the disabled hover transparent
  const base = CSS.indexOf(".picker-action:hover {"), dis = CSS.indexOf(".picker-action:disabled:hover {"), ours = CSS.indexOf(".emoji-foot .picker-action:hover:not(:disabled) {");
  assert.ok(base > 0 && dis > base && ours > dis);
  assert.match(CSS, /\.emoji-cell:hover \{ background: var\(--menu-hover\); \}/);   // the cells' wash, which the buttons now share
});
