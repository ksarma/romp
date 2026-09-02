// A user todo's note links to files the way a transcript does (the user 2026-09-02): a path in the
// detail fold — or in the note quoted by the reply dialog — becomes the same .file-uri-link a chat
// body gets, and opens through openPath. Relative paths resolve against the TODO'S OWN session (the
// one that flagged the need, whose working directory the note was written from), not whichever tab
// happens to be active when the card is read. Source pins — render.ts has no jsdom harness.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");

test("the todo card linkifies the detail fold with the todo's session resolving relative paths", () => {
  const card = RENDER.slice(RENDER.indexOf('const d = el("div", "ut-detail" + (utDetailOpen.has(t.id)'),
                            RENDER.indexOf("row.appendChild(d);"));
  assert.match(card, /d\.textContent = t\.detail \|\| "";/);                           // the note stays plain text…
  assert.match(card, /linkifyFileUris\(d, undefined, undefined, undefined, undefined, renderingSid \|\| null\);/);   // …with paths linked after
  // the card is rendered per session (renderingSid is the session whose chat holds the card), and the
  // Reply/Dismiss buttons carry the same id — the note's paths resolve where the buttons act
  assert.match(RENDER, /reply\.dataset\.sid = renderingSid \|\| "";/);
});

test("the reply dialog's quoted note is linkified against the todo's session too", () => {
  const modal = RENDER.slice(RENDER.indexOf("function showUserTodoReply(sid: string, todoId: string, todoText: string, todoDetail = \"\")"),
                             RENDER.indexOf("input.className = \"ut-reply-input\""));
  assert.match(modal, /dd\.textContent = todoDetail; linkifyFileUris\(dd, undefined, undefined, undefined, undefined, sid\);/);
});

test("linkifyFileUris and openPathLink accept the session whose cwd a relative path belongs to", () => {
  // the trailing parameter is optional: every chat-body call site is unchanged and keeps the active tab
  assert.match(RENDER, /function linkifyFileUris\(root: HTMLElement, skipThumbs\?: string\[\], spacePaths\?: string\[\],\s*\n\s*pathLinks\?: Record<string, string>, pathPins\?: Record<string, string>, sid\?: string \| null\): void/);
  assert.match(RENDER, /function openPathLink\(raw: string, open: string, relative = false, sid\?: string \| null\): HTMLElement/);
  assert.match(RENDER, /openPath\(open, relative \? \(sid \?\? activeId\) : null\);/);   // named session first, active tab otherwise
  // both relative-link sites inside the linkifier thread it through (a verified space path, a bare path)
  assert.match(RENDER, /openPathLink\(tok, tok, true, sid\)/);
  assert.match(RENDER, /openPathLink\(tok, open, true, sid\)/);
  // the chat bodies still pass no sid — the active tab IS their session
  assert.match(RENDER, /linkifyFileUris\(body, undefined, ev\.spacePaths, ev\.pathLinks, ev\.pathPins\)/);
});

test("the todo's one-line text is NOT linkified — it is the fold's click target (ui/CLAUDE.md click safety)", () => {
  const row = RENDER.slice(RENDER.indexOf('const txt = el("span", "ut-text");'), RENDER.indexOf('const reply = el("button", "ut-btn ut-reply");'));
  assert.match(row, /txt\.textContent = t\.text;/);
  assert.doesNotMatch(row, /linkifyFileUris\(/);
});
