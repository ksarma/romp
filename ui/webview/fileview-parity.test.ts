// The file VIEWER mounts in both documents (file-view.ts is one shared module), but the chat page
// loads styles.css alone and the feed page feed.css alone — so its dress is declared in BOTH sheets
// (the .romp-acted / filebrowse precedent). The copies had already drifted once (feed.css lacked the
// a.fileview-btn anchor rules, so the GitHub link rendered hrefless-underlined there, 2026-08-26).
// This pins the shared chrome byte-equal so it cannot drift again. Rules that are deliberately
// pane-specific (wrap mode, the pane's own load cue `.fileview-load {`) are not pinned. The md body's
// own rule IS (since Slice 1 of plans/markdown-viewer.md): its `contain: layout` is what keeps a note's
// fixed-positioned element inside the note, and it has to hold in both documents.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const read = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const CHAT = read("styles.css");
const FEED = read("feed.css");

const RULES = [
  "#romp-fileview {", ".fileview {", "body.fileview-open {", ".fileview-bar {", ".fileview-name {",
  ".fileview-dir {", ".fileview-base {", ".fileview-sess {", ".fileview-sess .host-prefix {", ".fileview-acts {",
  ".fileview-bar .fileview-name {", ".fileview-bar .fileview-acts {",   // the bar's own wrap (scoped: the browser's row and the pane's Recent rows wear the classes too)
  ".fileview-btn {", ".fileview-btn:hover {",
  "a.fileview-btn {", ".fileview-gh {", ".fileview-gh-why {", ".fileview-gh-dots {",
  '.fileview-btn:disabled, .fileview-btn[aria-disabled="true"] {', '.fileview-btn:disabled:hover, .fileview-btn[aria-disabled="true"]:hover {',
  '.fileview-btn:disabled:active, .fileview-btn[aria-disabled="true"]:active {', ".fileview-size-reset {", ".fileview-size-reset.fileview-size-default {",
  "a.fileview-gh-note {", ".fileview-body {", ".fileview-md {",
  ".fileview > .fileview-err {",   // the notice bar above the body row (Slice 2 of plans/markdown-viewer.md)
  // the width caps on a note's pictures and on the media it draws itself (svg, canvas, video): under the md box's
  // contain: layout an uncapped one is clipped and unreachable, so the cap has to hold on both pages
  ".fileview-md img {", ":where(.fileview-md) svg, :where(.fileview-md) canvas, :where(.fileview-md) video {",
  ':where(.fileview-md :is(img, svg, canvas, video)[width]:not([width$="%"])) {',   // the ratio-keeping half, pixel-sized media only (a sized <img> since Slice 2 of plans/markdown-viewer.md)
  // the document type scale (Slice 3 of plans/markdown-viewer.md): the headings, the list gutter and the task item, kbd, the
  // fences' rows and Copy button, the table's fill, striping, alignment and pane-wide break-out
  ".fileview-md h1, .fileview-md h2, .fileview-md h3, .fileview-md h4, .fileview-md h5, .fileview-md h6 {", ".fileview-md h1 {", ".fileview-md h2 {", ".fileview-md h3 {",
  ".fileview-md h4 {", ".fileview-md h5, .fileview-md h6 {", ".fileview-md h1, .fileview-md h2 {",
  ".fileview-md ul, .fileview-md ol {", ".fileview-md li.task-list-item {", ".fileview-md li.task-list-item input {",
  '.fileview-md li.task-list-item > input[type="checkbox"], .fileview-md li.task-list-item > p:first-child > input[type="checkbox"] {',
  ".fileview-md kbd {", ".fileview-md pre code {", ".fileview-md pre code .cl {", ".fileview-md pre code .cl::before {", ".fileview-md pre code .ct {",
  ".fileview-md pre.has-copy {", ".fileview-md .code-copy {", ".fileview-md pre.has-copy:hover .code-copy, .fileview-md .code-copy:focus-visible {",
  ".fileview-md .code-copy:hover {", ".fileview-md .code-copy.copied {",
  ".fileview-md table {", ".fileview-md > table {", ".fileview-md th, .fileview-md td {", ".fileview-md th {", ".fileview-md tbody tr:nth-child(even) {",
  '.fileview-md th[align="center"], .fileview-md td[align="center"] {', '.fileview-md th[align="right"], .fileview-md td[align="right"] {', '.fileview-md th[align="left"], .fileview-md td[align="left"] {',
  ".md code.md-math-src, .fileview-md code.md-math-src {",   // the math fill's source fallback, dressed as unrendered source (math.ts MATH_SOURCE_CLASS)
  ".fileview-cm {", ".fileview-cm .cm-editor {", ".fileview-editor {",
  ".fileview-dir-link {", ".fileview-dir-link:hover {",
  // links inside a shown file (file-view-links.ts): the light dress on a URL anchor and a path link, and the Markdown link that names a file
  ".fileview-body .file-uri-link, .fileview-body .fv-url {", ".fileview-body .file-uri-link:hover, .fileview-body .fv-url:hover {",
  ".fileview-md a.file-uri-link {", ".fileview-md a.file-uri-link:hover {", ".fileview-md a.fv-dead {",
  ".fileview-imgbox {", ".fileview-img {", ".fileview-frame {",
  // the PDF pages (Slice 4): the chunk's host, root, page and canvas, and the frame fallback's column
  ".fileview-pdfhost {", ".fileview-pdf {", ".fileview-pdf-page {", ".fileview-pdf-canvas {", ".fileview-pdffall {", ".fileview-pdffall .fileview-frame {",
  // …and the dress on the white page sheet (the failure notice, the per-page wait cue): each sheet's cascade and ratios are
  // measured by styles-pdf-page-err / feed-pdf-page-err and styles-pdf-page-load / feed-pdf-page-load; the bytes are held here too
  ".fileview-pdf-page .fileview-err {", ".fileview-pdf-page .fileview-load {", ".fileview-pdf-page .fileview-dot {",
  // the comments panel's aside and its chrome (plans/file-review.md Slice 1): the whole block is also
  // pinned byte-equal end to end by file-comments.test.ts; these heads keep it in the same list
  ".fileview-main {", ".fileview-aside {", ".fileview-fc {", ".fileview-fc[hidden] {", ".fc-panel {", ".fc-card {",
  ".fc-chip {", ".fc-input {", ".fc-hl {", ".fc-presel {", ".fc-float {",
  // the editor's marks over pending changes (Slice 5; track-decorations.ts CLS): the chat and feed pages both host the editor
  ".tc-diff-ins {", ".tc-diff-del {", ".tc-diff-sub {", ".tc-diff-del.tc-diff-sub {", ".tc-diff-del-block {", ".tc-diff-del-line {", ".tc-diff-hover {",
  // the embed token a struck block row still holds (track-decorations.ts, departure 4) and its tag; the pixel legs are
  // styles-kept-embed.test.ts and feed-css-kept-embed.test.ts
  ".tc-diff-del-kept-embed {", ".tc-diff-del-kept-embed::after {",
];

function ruleOf(css: string, head: string): string {
  const at = css.indexOf(head);
  assert.ok(at >= 0, head + " present");
  return css.slice(at, css.indexOf("}", at) + 1);
}

test("the viewer's shared chrome exists in BOTH sheets, byte-equal", () => {
  for (const head of RULES) {
    assert.equal(ruleOf(CHAT, head), ruleOf(FEED, head), head + " mirrors exactly");
  }
});
