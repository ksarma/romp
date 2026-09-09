// Bare file:// URLs in a CHAT message (the user 2026-07-06): a link like
// file:///Users/me/analysis/trace.pdf pasted into a message should be clickable and open the file — marked
// doesn't autolink the file: scheme and DOMPurify strips it, so linkifyFileUris wraps them post-render into
// a clickable .file-uri-link that routes to the host opener. NOT applied to tool-use summaries. The renderer
// has no jsdom harness, so pin the wiring at source.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
const LINKS = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "path-links.ts"), "utf8");   // the matcher lives here since plans/file-review.md Slice 0
const CSS = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "styles.css"), "utf8");

test("a bare file:// URL becomes a clickable .file-uri-link that opens the file in the host app", () => {
  assert.match(RENDER, /function linkifyFileUris\(root: HTMLElement, skipThumbs\?: string\[\], spacePaths\?: string\[\],\s*\n\s*pathLinks\?: Record<string, string>, pathPins\?: Record<string, string>, sid\?: string \| null, delegated = false\): void/);
  assert.match(LINKS, /el\("span", "file-uri-link"\)/);   // the span is minted in path-links.ts (Slice 0 of plans/file-review.md)
  // clicking is ROUTED by openPath, never a blocked window.open(file://) — a file:// URI is absolute,
  // so it takes the shared openPathLink's no-session-id branch
  assert.match(LINKS, /function fileUriLink\(uri: string\): HTMLElement \{ return openPathLink\(uri, fileUriToPath\(uri\)\); \}/);
  assert.match(RENDER, /openPath\(open, relative \? \(sid \?\? activeId\) : null, e\);/);   // with the click: a PDF's modified-click tab
  // the URL is turned into a real filesystem path: scheme stripped, percent-decoded (fileUriToPath, path-links.ts); only a
  // LOCAL URI (an empty authority, or localhost) is one; file://host/path names another machine and stays prose (2026-09-07)
  assert.match(LINKS, /const FILE_URI_RE = \/\^file:\\\/\\\/\(\?:localhost\)\?\(\?=\\\/\)\/i;/);
  assert.match(LINKS, /let p = uri\.replace\(FILE_URI_RE, ""\);/);
  assert.match(LINKS, /decodeURIComponent\(p\)/);
});

test("linkify runs on chat message bodies (assistant reply + user bubble + nudge full text) and todo notes — never tool summaries", () => {
  assert.match(RENDER, /linkifyFileUris\(body, undefined, ev\.spacePaths, ev\.pathLinks, ev\.pathPins\)/);   // the assistant reply
  assert.match(RENDER, /linkifyFileUris\(bubble, imgPaths, ev\.spacePaths, ev\.pathLinks, ev\.pathPins\)/); // your own bubble (in-bubble images don't re-thumb)
  assert.match(RENDER, /linkifyFileUris\(full, imgPaths, ev\.spacePaths, ev\.pathLinks, ev\.pathPins\)/);   // a compact nudge's expanded full text (2026-07-17)
  // …plus a user todo's note, in the card's fold and quoted in the reply dialog, through linkTodoDetailPaths:
  // the same pass, DELEGATED, since the card rebuilds every push and its spans are not bound (user-todo-links.test.ts)
  assert.match(RENDER, /function linkTodoDetailPaths\(node: HTMLElement, sid: string \| null\): void \{\n\s*linkifyUrls\(node\);\n\s*linkifyFileUris\(node, undefined, undefined, undefined, undefined, sid, true\);/);   // the URL pass first (url-links.ts, 2026-09-08)
  assert.match(RENDER, /linkTodoDetailPaths\(d, renderingSid \|\| null\)/);
  assert.match(RENDER, /linkTodoDetailPaths\(dd, sid\)/);
  // exactly the definition + those four applications, so tool-use reports/summaries stay untouched
  const uses = RENDER.match(/linkifyFileUris\(/g) || [];
  assert.equal(uses.length, 5, "linkifyFileUris is defined once and applied to the three chat bodies + the todo-note wrapper");
});

test("linkify works inside INLINE backticks (agents backtick paths), skips only fenced code + existing links, trims trailing punctuation", () => {
  // inline <code> is NOT skipped — a `file://…` path in backticks still linkifies; only fenced <pre> + links are skipped
  // (the spaced pass in render.ts and the token walk in path-links.ts share the one skip list)
  assert.match(RENDER, /closest\("a, \.file-uri-link, pre"\)/);
  assert.doesNotMatch(RENDER, /closest\("a, \.file-uri-link, code, pre"\)/);
  assert.match(LINKS, /const skip = opts && opts\.inPre \? DEAD_TEXT : DEAD_TEXT \+ ", pre";/, "the chat's default skip list (a variable since the file viewer walks inside its <pre>; DEAD_TEXT is the link and the inline SVG)");
  assert.match(LINKS, /export const DEAD_TEXT = "a, \.file-uri-link, svg";/);
  assert.doesNotMatch(LINKS, /"a, \.file-uri-link, code, pre"|code, pre"/);
  assert.match(LINKS, /tok = tok\.slice\(0, tok\.length - trail\[0\]\.length\)/);
});

test(".file-uri-link is styled as a wrapping accent link", () => {
  assert.match(CSS, /\.file-uri-link \{[\s\S]*?cursor: pointer[\s\S]*?color: var\(--accent\)/);
  assert.match(CSS, /\.file-uri-link:hover \{ text-decoration: underline; \}/);
});
