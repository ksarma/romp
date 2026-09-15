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
const LINKS = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "path-links.ts"), "utf8");   // the matcher, lifted out of render.ts
const CSS = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "styles.css"), "utf8");

test("a bare file:// URL becomes a clickable .file-uri-link that opens the file in the host app", () => {
  assert.match(RENDER, /function linkifyFileUris\(root: HTMLElement, skipThumbs\?: string\[\], spacePaths\?: string\[\],\s*\n\s*pathLinks\?: Record<string, string>, pathPins\?: Record<string, string>, pathPreview\?: Record<string, string>,\s*\n\s*pathPreviewWhy\?: Record<string, string>, sid\?: string \| null, delegated = false, walkOpts\?: PathLinkOptions\): void/);   // upstream's pathPreview/pathPreviewWhy (T351), then the fork's sid, delegated and walkOpts
  assert.match(LINKS, /el\("span", "file-uri-link"\)/);   // the span is minted in path-links.ts (Slice 0 of plans/file-review.md)
  // clicking is ROUTED by openPath, never a blocked window.open(file://) — a file:// URI is absolute,
  // so it takes the shared openPathLink's no-session-id branch
  assert.match(LINKS, /function fileUriLink\(uri: string\): HTMLElement \{ return openPathLink\(uri, fileUriToPath\(uri\)\); \}/);
  assert.match(RENDER, /openPath\(open, relative \? \(sid \?\? activeId\) : null, e, linkTarget\(a\)\);/);   // with the click: a PDF's modified-click tab; and the target the link named after its path (Slice 6 of plans/markdown-viewer.md; a `#slug` is its heading arm, so no separate frag rides here)
  // the URL is turned into a real filesystem path: scheme stripped, percent-decoded (fileUriToPath, path-links.ts); only a
  // LOCAL URI (an empty authority, or localhost) is one; file://host/path names another machine and stays prose (2026-09-07)
  assert.match(LINKS, /const FILE_URI_RE = \/\^file:\\\/\\\/\(\?:localhost\)\?\(\?=\\\/\)\/i;/, "a LOCAL URI: an empty authority or localhost; file://host/x names another machine and stays prose");
  assert.match(LINKS, /let p = uri\.replace\(FILE_URI_RE, ""\);/);
  assert.match(LINKS, /decodeURIComponent\(p\)/);
});

test("linkify runs on chat message bodies (assistant reply + user bubble + nudge full text) and todo notes — never tool summaries", () => {
  assert.match(RENDER, /linkifyFileUris\(body, undefined, ev\.spacePaths, ev\.pathLinks, ev\.pathPins, ev\.pathPreview, ev\.pathPreviewWhy\)/);   // the assistant reply
  assert.match(RENDER, /linkifyFileUris\(bubble, imgPaths, ev\.spacePaths, ev\.pathLinks, ev\.pathPins, ev\.pathPreview, ev\.pathPreviewWhy\)/); // your own bubble (in-bubble images don't re-thumb)
  assert.match(RENDER, /linkifyFileUris\(full, imgPaths, ev\.spacePaths, ev\.pathLinks, ev\.pathPins, ev\.pathPreview, ev\.pathPreviewWhy\)/);   // a compact nudge's expanded full text (2026-07-17)
  // …plus a user todo's note, in the card's fold and quoted in the reply dialog, through linkTodoDetailPaths:
  // the same pass, DELEGATED, since the card rebuilds every push and its spans are not bound (user-todo-links.test.ts);
  // the two undefineds after pathPins are upstream's pathPreview and pathPreviewWhy slots (T351), which a todo's note has no verdict for
  assert.match(RENDER, /function linkTodoDetailPaths\(node: HTMLElement, sid: string \| null\): void \{\n\s*linkifyUrls\(node\);\n\s*linkifyFileUris\(node, undefined, undefined, undefined, undefined, undefined, undefined, sid, true, \{ targetSuffix: true \}\);/);   // the URL pass first (url-links.ts, 2026-09-08)
  assert.match(RENDER, /linkTodoDetailPaths\(d, renderingSid \|\| null\)/);
  assert.match(RENDER, /linkTodoDetailPaths\(dd, sid\)/);
  // exactly the definition + those four applications, so tool-use reports/summaries stay untouched
  const uses = RENDER.match(/linkifyFileUris\(/g) || [];
  assert.equal(uses.length, 5, "linkifyFileUris is defined once and applied to the three chat bodies + the todo-note wrapper");
});

test("linkify works inside INLINE backticks (agents backtick paths), skips existing links, trims trailing punctuation; a fenced block links on the kernel's verdict under the viewer's code gate (2026-09-12)", () => {
  // inline <code> is NOT skipped — a `file://…` path in backticks still linkifies; links and inline SVGs are dead text
  // (render.ts's SPACED pass still skips a fence outright: the kernel's verified spaced names are prose tokens; the token
  // walk in path-links.ts takes the fence under FENCE_WALK's gate instead, below)
  assert.match(RENDER, /closest\("a, \.file-uri-link, pre"\)/);
  assert.doesNotMatch(RENDER, /closest\("a, \.file-uri-link, code, pre"\)/);
  assert.match(LINKS, /export const DEAD_TEXT = "a, \.file-uri-link, svg";/);
  assert.match(LINKS, /const skip = opts && opts\.inPre \? DEAD_TEXT : DEAD_TEXT \+ ", pre";/, "a surface that asks for no fenced walk skips the block; never inline code");
  assert.doesNotMatch(LINKS, /"a, \.file-uri-link, code, pre"|code, pre"/);
  assert.doesNotMatch(LINKS, /DEAD_TEXT \+ ", code/);
  assert.match(LINKS, /tok = tok\.slice\(0, tok\.length - trail\[0\]\.length\)/);
  // the chat asks for the fenced walk (the user 2026-09-12: a report's path printed in a ``` block did not link): the
  // kernel's verdict or nothing inside a fence, the viewer's code-aware gate there, the fence's rows as units, and a
  // fenced hit opens the file and previews on hover like any link, and renders no figure under a code sample
  assert.match(RENDER, /^import \{ viewerPathGate \} from "\.\/file-view-links";/m);
  assert.match(RENDER, /^const FENCE_WALK: PathLinkOptions = \{\n\s*inPre: true, preVerified: true, unit: "\.cl",\n\s*accept: \(tok, ctx\) => !ctx\.inPre \|\| viewerPathGate\(tok, ctx\),/m);
  assert.match(RENDER, /for \(const \{ el: link, open, verified, inPre \} of linkifyPathTokens\(root, sid, pathLinks, walkOpts \? \{ \.\.\.FENCE_WALK, \.\.\.walkOpts \} : FENCE_WALK\)\) \{\n\s*bind\(link\);\n\s*armPreview\(link, link\.textContent \|\| "", open\);\n\s*absorbFragment\(link\);\n\s*if \(verified\) kernelVerified\.add\(open\);[^\n]*\n\s*if \(inPre\) continue;/);   // the fork's walk: the session and a todo surface's options ride beside the chat's (bind: bindPathLink, or the identity when delegated)
  assert.match(LINKS, /if \(!isUri && span\.inPre && opts && opts\.preVerified && typeof fixed !== "string"\) continue;/, "fenced: the kernel's word or nothing");
  assert.match(CSS, /^pre code \.file-uri-link \{ color: var\(--accent\); \}/m, "the link keeps the accent over the highlight's token colour");
});

test(".file-uri-link is styled as a wrapping link in the chat's one link dress (T378)", () => {
  assert.match(CSS, /\.file-uri-link \{[\s\S]*?cursor: pointer[\s\S]*?color: var\(--link\)/, "the link token, as .md a and .term-link (T378)");
  assert.match(CSS, /\.file-uri-link:hover \{ text-decoration: underline; \}/);
});
