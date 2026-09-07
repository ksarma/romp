// The tab's emoji label (the user 2026-09-06): one glyph before the session name, set from the tab menu
// (Emoji… → the picker dialog → the setSessionEmoji WS op), by the session itself (the postal set_emoji
// tool) or by `romp emoji` — one kernel validator and one store behind all three doors. Source pins on
// render.ts (no jsdom for the chat render — the tab-menu-flags idiom); the pure sync lives in tab-meta.ts
// and runs for real in ui/webview/tab-meta.test.ts; the kernel side in tests/test_session_emoji.py. The
// picker itself (search, Recent row, grid, keyboard) is pinned in ui/webview/tab-emoji-picker.test.ts and
// its pure half runs in ui/webview/emoji-picker.test.ts (2026-09-07); what this file pins is the contract
// the picker inherited from the one-field dialog it replaced.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { INTENT_OPS } from "./pipe-intent";

const SRC = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
const CSS = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "styles.css"), "utf8");
const GUIDE = fs.readFileSync(path.resolve(process.cwd(), "..", "docs", "guide.md"), "utf8");

function slice(from: string, to: string): string {
  const i = SRC.indexOf(from);
  assert.ok(i > 0, `render.ts has ${JSON.stringify(from)}`);
  const j = SRC.indexOf(to, i);
  assert.ok(j > i, `render.ts has ${JSON.stringify(to)} after ${JSON.stringify(from)}`);
  return SRC.slice(i, j);
}

test("the strip renders the emoji BEFORE the name on real and placeholder tabs, exposed to assistive technology", () => {
  // The glyph is a label the user or the session placed on purpose, and the only thing besides color that
  // tells two same-named sessions on one host apart — so it is NOT aria-hidden (review, 2026-09-06): a
  // reader speaks the character's own name ahead of the session name, which is what a sighted user sees.
  const body = slice("function tabEmojiNode(", "\nfunction renderTabs()");
  assert.match(body, /if \(!emoji\) return null;\n  const e = el\("span", "tab-emoji"\);\n  e\.textContent = emoji;\n  return e;/);
  assert.doesNotMatch(body, /aria-hidden/, "the tab's glyph is part of the tab's accessible name");
  const why = slice("// The tab's emoji label (the user 2026-09-06)", "\nfunction tabEmojiNode(");
  assert.match(why, /names are not unique on a host/);            // the reason, stated where the decision is
  assert.match(why, /ARIA prohibits aria-label on a role-less div/); // the alternative weighed and passed over
  // a real tab: the glyph is appended right before the label, from the session's field or the pushed meta
  assert.match(SRC, /const emojiEl = tabEmojiNode\(s\.emoji \?\? tabMeta\.get\(id\)\?\.emoji\);[^\n]*\n\s*if \(emojiEl\) tab\.appendChild\(emojiEl\);\n\s*tab\.appendChild\(label\);/);
  // a placeholder tab (tabs-first): the same, from the pushed meta alone
  assert.match(SRC, /const phEmoji = tabEmojiNode\(meta\?\.emoji\);\n\s*if \(phEmoji\) tab\.appendChild\(phEmoji\);\n\s*const label = el\("span", "tab-label"\);/);
  assert.match(CSS, /\.tab-emoji \{ flex: 0 0 auto; line-height: 1; \}/);
  // the sheet's comment above that rule states the SAME design: after round 1 exposed the glyph it still said
  // "aria-hidden in the markup", and a maintainer reading the sheet as the design would have hidden it again
  // (review round 3, 2026-09-06)
  const cssFrom = CSS.indexOf("/* The tab's emoji label (the user 2026-09-06)");
  const cssTo = CSS.indexOf(".tab-emoji { flex: 0 0 auto;");
  assert.ok(cssFrom > 0 && cssTo > cssFrom && cssTo - cssFrom < 900, "the comment sits directly above the rule");
  const cssWhy = CSS.slice(cssFrom, cssTo);
  assert.match(cssWhy, /EXPOSED to assistive technology — not aria-hidden/);
  assert.doesNotMatch(cssWhy, /aria-hidden in the markup/);
  assert.match(cssWhy, /tab MENU's copy of the glyph is the\s+hidden one/);
});

test("the session and the tab meta carry the field; a frame without it (an older kernel) keeps the last value", () => {
  assert.match(SRC, /interface Session \{ id: string; name: string; color: Color \| null; emoji\?: string;/);
  assert.match(SRC, /const tabMeta = new Map<string, \{ name: string; color: Color \| null; emoji\?: string \}>\(\);/);
  assert.match(SRC, /emoji: \("emoji" in msg\) \? String\(msg\.emoji \|\| ""\) : \(prev \? prev\.emoji : undefined\)/);
  assert.match(SRC, /emoji: typeof t\.emoji === "string" \? t\.emoji : undefined/);
});

test("the tab menu's Emoji… row sits with Rename, wears the current emoji as its icon (hidden — the row's text is the label), and opens the dialog", () => {
  const i = SRC.indexOf('l.textContent = "Emoji…"');
  assert.ok(i > 0, "the row exists");
  const block = SRC.slice(i - 900, i + 700);
  assert.match(block, /const curEmoji = sessions\.get\(id\)\?\.emoji \|\| tabMeta\.get\(id\)\?\.emoji \|\| "";/);
  assert.match(block, /ic\.textContent = curEmoji; ic\.setAttribute\("aria-hidden", "true"\);/);
  assert.match(block, /else em\.appendChild\(ctxIcon\("smile", false\)\);/);
  assert.match(block, /ctx-item-sub/);
  assert.match(block, /dismissTabMenu\(\); showEmojiPrompt\(id\);/);
  // after Move to folder…, before the color swatches: the aesthetic section, with Rename
  const move = SRC.indexOf('l.textContent = "Move to folder…"');
  const colors = SRC.indexOf('const row = el("div", "ctx-colors");');
  assert.ok(move > 0 && colors > 0 && move < i && i < colors);
  // the glyph box sizes to its glyph up to the sibling SVG icons' 16px and CLIPS the rest horizontally: a
  // well-formed ZWJ chain the font does not join, or an RGI sequence the font predates, draws as three or four
  // glyphs, which over the fixed 14px box this was spilled into the row text on the right and the padding on
  // the left (review round 3, 2026-09-06). clip-path with vertical slack, not overflow: a glyph's ink can
  // stand taller than the 14px line and keeps its top and bottom.
  assert.match(CSS, /\.ctx-item-toggle \.ctx-icon\.glyph \{ min-width: 14px; max-width: 16px; line-height: 14px; clip-path: inset\(-50% 0\); \}/);
  const gi = CSS.indexOf(".ctx-item-toggle .ctx-icon.glyph {");
  const glyphRule = CSS.slice(gi, CSS.indexOf("}", gi));
  assert.doesNotMatch(glyphRule, /[^-]width: 14px/, "no fixed width: the box follows its glyph");
  assert.doesNotMatch(glyphRule, /overflow/, "overflow: hidden would clip a tall glyph's ink top and bottom");
  assert.doesNotMatch(glyphRule, /justify-content: center/, "centered, an overflowing run showed its middle glyph; from the start it shows the first");
});

test("the dialog: Set posts the typed value, Clear posts \"\", an empty Set is refused locally, and the pressed button acknowledges BEFORE the post", () => {
  const body = slice("function showEmojiPrompt(sid: string): void {", "\nfunction emojiLanded(");
  assert.match(body, /input\.value = cur;/);   // prefilled with the current emoji
  // the empty Set: marked, focused and SAID (the hint; the mark alone was invisible on this field, review round 1)
  assert.match(body, /if \(!v\) \{[^\n]*\n\s*input\.classList\.add\("bad"\); input\.focus\(\);\n\s*hint\.textContent = EMPTY_SET;[^\n]*\n\s*return;/);
  assert.match(body, /submit\(v, go, "Setting…"\)/);
  assert.match(body, /clear\.addEventListener\("click", \(\) => submit\("", clear, "Clearing…"\)\);/);
  // the click-safe rule: acknowledge first (label + disabled + locked input), then the round trip; the dialog
  // is NOT closed on the click any more — the kernel's answer is what changes it next
  const ack = body.indexOf("btn.textContent = busy; go.disabled = true; clear.disabled = true; input.disabled = true;");
  const post = body.indexOf("setSessionEmoji(sid, value);");
  assert.ok(ack > 0 && post > ack, "the button changes its label BEFORE the op is posted");
  assert.doesNotMatch(body.slice(body.indexOf("const submit ="), post), /closeEmojiPrompt\(\)/, "the submit no longer closes the dialog");
  assert.match(body, /if \(!p \|\| p\.pending\) return;/);   // one answer per press
  assert.match(body, /p\.pending = true; p\.asked = value;/);   // and the dialog remembers what it asked (the late-confirm close)
  assert.match(body, /30000\)/);                            // the backstop: a wait never traps
  // the dialog lives on document.body, outside #tabs — renderTabs (every kernel push) never rebuilds its
  // Set/Clear mid-click, so per-node listeners on those are click-safe (the move and fork dialogs'
  // arrangement); the footer keeps the field, then Clear, then Set (2026-09-07: the picker's footer)
  assert.match(body, /document\.body\.appendChild\(card\);/);
  assert.match(body, /foot\.appendChild\(input\); foot\.appendChild\(clear\); foot\.appendChild\(go\);/);
});

test("the disabled Clear (nothing to clear) is dressed as disabled and says why; the move dialog's Moving… gets the same dress", () => {
  const body = slice("function showEmojiPrompt(sid: string): void {", "\nfunction emojiLanded(");
  assert.match(body, /clear\.disabled = !cur;/);
  assert.match(body, /if \(!cur\) clear\.title = "nothing to clear — this session has no emoji";/);
  // .picker-action had no :disabled rule: its pointer cursor, full color and hover wash made a disabled
  // button look live (review, 2026-09-06). The .bg-stop:disabled / .apierror-retry:disabled idiom.
  assert.match(CSS, /\.picker-action:disabled \{ opacity: 0\.55; cursor: default; \}/);
  assert.match(CSS, /\.picker-action:disabled:hover \{ background: transparent; \}/);
  const rule = CSS.indexOf(".picker-action:disabled {");
  const hover = CSS.indexOf(".picker-action:hover {");
  assert.ok(hover > 0 && rule > hover, "the disabled rule follows the hover rule it overrides");
});

test("the kernel's answer drives the dialog: emojiSet for its session closes it, a warn while pending puts the reason under the input", () => {
  // the confirm handler applies the emoji to the strip, THEN closes the dialog that asked
  const handler = slice('m.type === "emojiSet" && m.id && typeof m.emoji === "string"', 'm.type === "droppedPath"');
  assert.match(handler, /else if \(!s\) renderTabs\(\);[^\n]*\n\s*emojiLanded\(String\(m\.id\), m\.emoji\);/);
  // the close decision is the pure emojiConfirmClosesDialog (tab-meta.ts; tab-meta.test.ts runs it): pending →
  // its own answer, whatever the validator trimmed; not pending but the value it asked for → the same answer
  // arriving late, after the 30 s backstop had painted "still waiting" — it used to stay open with a red hint
  // under a value the tab already wore (review round 3, 2026-09-06)
  const landed = slice("function emojiLanded(sid: string, emoji: string): void {", "\nfunction emojiRefusedLocal(");
  // 2026-09-07: the decision is still the pure function's alone; a landed emoji is filed as a recent on the way out
  assert.match(landed, /^function emojiLanded\(sid: string, emoji: string\): void \{\n  if \(!emojiConfirmClosesDialog\(emojiPrompt, sid, emoji\)\) return;\n  if \(emoji\) rememberRecentEmoji\(emoji\);\n  closeEmojiPrompt\(\);\n\}/);
  assert.match(SRC, /import \{[^}]*\bemojiConfirmClosesDialog\b[^}]*\} from "\.\/tab-meta";/);
  assert.match(SRC, /backstop\?: number; asked\?: string \} \| null = null;/);
  // the refusal: buttons back, input unlocked with the value in place, the reason where the move dialog puts its
  const refused = slice("function emojiRefusedLocal(text: string): void {", "\n// THE FORK MODAL");
  // a warn while NOT pending is not this dialog's: it returns before touching the hint, the buttons or the
  // input (the router then hands the warn to the create branch or a toast — pinned below)
  assert.match(refused, /^function emojiRefusedLocal\(text: string\): void \{\n  const p = emojiPrompt;\n  if \(!p \|\| !p\.pending\) return;/);
  assert.match(refused, /p\.pending = false;/);
  assert.match(refused, /p\.go\.disabled = false; p\.go\.textContent = "Set";/);
  assert.match(refused, /p\.clear\.disabled = !\(sessions\.get\(p\.sid\)\?\.emoji \|\| tabMeta\.get\(p\.sid\)\?\.emoji\); p\.clear\.textContent = "Clear";/);
  assert.match(refused, /p\.input\.disabled = false;/);
  assert.match(refused, /p\.hint\.textContent = text; p\.hint\.title = text; p\.hint\.className = "emoji-hint bad";/);
  assert.match(refused, /p\.input\.classList\.add\("bad"\); p\.input\.focus\(\);/);
  assert.doesNotMatch(refused, /input\.value/, "the typed value is left in place to fix");
  // the closer clears the backstop, so a cancelled dialog cannot fire a stale 'still waiting'
  assert.match(SRC, /function closeEmojiPrompt\(\): void \{\n  if \(!emojiPrompt\) return;\n  if \(emojiPrompt\.backstop !== undefined\) clearTimeout\(emojiPrompt\.backstop\);/);
  // the hint's dress: the move dialog's verdict line, dim until red
  assert.match(CSS, /\.emoji-hint \{ min-height: 1\.2em; font-family: var\(--sans\); font-size: 0\.82em; color: var\(--dim\); \}/);
  assert.match(CSS, /\.emoji-hint\.bad \{ color: #e5484d; \}/);
});

test("the warn router: a pending emoji dialog claims the warn BEFORE the create-failure branch, which used to strike the opening tab", () => {
  const warn = slice('else if (m.type === "warn" && typeof m.text === "string" && m.text) {', "const wv = activeId");
  assert.match(warn, /if \(emojiPrompt\?\.pending\) emojiRefusedLocal\(m\.text\);\n\s*else if \(provisionalId\) failProvisional\(m\.text\);\n\s*else warnToast\(m\.text\);/);
});

test("setSessionEmoji posts the op and is NOT optimistic — the strip changes on the kernel's emojiSet confirm", () => {
  const i = SRC.indexOf("function setSessionEmoji(id: string, emoji: string) {");
  assert.ok(i > 0);
  const body = SRC.slice(i, SRC.indexOf("\n}\n", i));
  assert.match(body, /postMessage\(\{ type: "setSessionEmoji", id, emoji \}\)/);
  assert.doesNotMatch(body, /renderTabs\(\)/);
  assert.doesNotMatch(body, /notePendingMeta/);
  // the confirm — the renamed shape: note the expectation, apply to session + meta, repaint
  const j = SRC.indexOf('m.type === "emojiSet" && m.id && typeof m.emoji === "string"');
  assert.ok(j > 0);
  const handler = SRC.slice(j, j + 800);
  assert.match(handler, /notePendingMeta\(pendingTabMeta, m\.id, \{ emoji: m\.emoji \}\);/);
  assert.match(handler, /if \(meta\) meta\.emoji = m\.emoji;/);
  assert.match(handler, /if \(s && \(s\.emoji \|\| ""\) !== m\.emoji\) \{ s\.emoji = m\.emoji; renderTabs\(\); \}/);
});

test("the op is user intent: the VS Code pipe holds it across a reconnect like setSessionColor", () => {
  assert.ok(INTENT_OPS.has("setSessionEmoji"));
  assert.ok(INTENT_OPS.has("setSessionColor"));
});

test("the guide says an accepted emoji is drawn with the viewer's font and can still show as a box on an older machine", () => {
  // the validator's tables are Unicode 16.0; acceptance is the kernel's, rendering is the viewing machine's
  assert.match(GUIDE, /draws the emoji with the viewing\s+machine's own emoji font, so one from the newest Unicode release, accepted by\s+Romp, can still show as an empty box on a machine whose font predates it\./);
});
