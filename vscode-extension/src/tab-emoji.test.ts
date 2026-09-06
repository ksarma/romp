// The tab's emoji label (the user 2026-09-06): one glyph before the session name, set from the tab menu
// (Emoji… → a one-field dialog → the setSessionEmoji WS op), by the session itself (the postal set_emoji
// tool) or by `romp emoji` — one kernel validator and one store behind all three doors. Source pins on
// render.ts (no jsdom for the chat render — the tab-menu-flags idiom); the pure sync lives in tab-meta.ts
// and runs for real in ui/webview/tab-meta.test.ts; the kernel side in tests/test_session_emoji.py.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { INTENT_OPS } from "./pipe-intent";

const SRC = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
const CSS = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "styles.css"), "utf8");

test("the strip renders the emoji BEFORE the name on real and placeholder tabs, aria-hidden (the name is the label)", () => {
  assert.match(SRC, /function tabEmojiNode\(emoji: string \| undefined\): HTMLElement \| null \{\n  if \(!emoji\) return null;\n  const e = el\("span", "tab-emoji"\);\n  e\.textContent = emoji;\n  e\.setAttribute\("aria-hidden", "true"\);/);
  // a real tab: the glyph is appended right before the label, from the session's field or the pushed meta
  assert.match(SRC, /const emojiEl = tabEmojiNode\(s\.emoji \?\? tabMeta\.get\(id\)\?\.emoji\);[^\n]*\n\s*if \(emojiEl\) tab\.appendChild\(emojiEl\);\n\s*tab\.appendChild\(label\);/);
  // a placeholder tab (tabs-first): the same, from the pushed meta alone
  assert.match(SRC, /const phEmoji = tabEmojiNode\(meta\?\.emoji\);\n\s*if \(phEmoji\) tab\.appendChild\(phEmoji\);\n\s*const label = el\("span", "tab-label"\);/);
  assert.match(CSS, /\.tab-emoji \{ flex: 0 0 auto; line-height: 1; \}/);
});

test("the session and the tab meta carry the field; a frame without it (an older kernel) keeps the last value", () => {
  assert.match(SRC, /interface Session \{ id: string; name: string; color: Color \| null; emoji\?: string;/);
  assert.match(SRC, /const tabMeta = new Map<string, \{ name: string; color: Color \| null; emoji\?: string \}>\(\);/);
  assert.match(SRC, /emoji: \("emoji" in msg\) \? String\(msg\.emoji \|\| ""\) : \(prev \? prev\.emoji : undefined\)/);
  assert.match(SRC, /emoji: typeof t\.emoji === "string" \? t\.emoji : undefined/);
});

test("the tab menu's Emoji… row sits with Rename, wears the current emoji as its icon, and opens the dialog", () => {
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
  assert.match(CSS, /\.ctx-item-toggle \.ctx-icon\.glyph \{ width: 14px; line-height: 14px; justify-content: center; \}/);
});

test("the dialog: Set posts the typed value, Clear posts \"\", an empty Set is refused locally, and closing is the acknowledgement", () => {
  assert.match(SRC, /function showEmojiPrompt\(sid: string\): void \{/);
  assert.match(SRC, /const submit = \(value: string\) => \{ closeEmojiPrompt\(\); setSessionEmoji\(sid, value\); \};/);
  assert.match(SRC, /if \(!v\) \{ input\.classList\.add\("bad"\); input\.focus\(\); return; \}/);
  assert.match(SRC, /clear\.addEventListener\("click", \(\) => submit\(""\)\);/);
  assert.match(SRC, /clear\.disabled = !cur;/);
  assert.match(SRC, /input\.value = cur;/);   // prefilled with the current emoji
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
