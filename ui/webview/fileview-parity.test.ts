// The file VIEWER mounts in both documents (file-view.ts is one shared module), but the chat page
// loads styles.css alone and the feed page feed.css alone — so its dress is declared in BOTH sheets
// (the .romp-acted / filebrowse precedent). The copies had already drifted once (feed.css lacked the
// a.fileview-btn anchor rules, so the GitHub link rendered hrefless-underlined there, 2026-08-26).
// This pins the shared chrome byte-equal so it cannot drift again. Rules that are deliberately
// pane-specific (wrap mode, the pane's own load cue `.fileview-load {`) are not pinned. The md body's
// own rule IS (since Slice 1 of plans/markdown-viewer.md): its `contain: layout` is what keeps a note's
// fixed-positioned element inside the note, and it has to hold in both documents.
// The reader (`rulesOf`) matches a head at a LINE START only, and pins every rule declared under it. A shorter head
// can end a longer one (`.fileview-md h5, .fileview-md h6 {` is the tail of the six-heading head), and a plain
// indexOf read the longer rule's body twice and never the h5/h6 dim rule (Slice 3 of plans/markdown-viewer.md,
// review round 3); a head declared twice (the six-heading head: its type rule and its scroll-margin rule) is held
// twice, so the second copy cannot drift either. A body runs to its first `}`, so a rule inside a nested block (an
// @media wrap) is not readable here; such a block is pinned whole by its own test.
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
  ".fileview-md kbd {", ".fileview-md pre code {", ".fileview-md pre code .cl {", ".fileview-md pre code .cl::before {", ".fileview-md pre code .ct {", ".fileview-md pre code .ct::before {",
  ".fileview-md pre.has-copy {", ".fileview-md .code-copy {", ".fileview-md pre.has-copy:hover .code-copy, .fileview-md .code-copy:focus-visible {",
  ".fileview-md .code-copy:hover {", ".fileview-md .code-copy.copied {",
  ".fileview-md table {", ".fileview-md > table {", ".fileview-md th, .fileview-md td {", ".fileview-md th {", ".fileview-md tbody tr:nth-child(even) {",
  '.fileview-md th[align="center"], .fileview-md td[align="center"] {', '.fileview-md th[align="right"], .fileview-md td[align="right"] {', '.fileview-md th[align="left"], .fileview-md td[align="left"] {',
  ".md code.md-math-src, .fileview-md code.md-math-src {",   // the math fill's source fallback, dressed as unrendered source (math.ts MATH_SOURCE_CLASS)
  // math in every bundle (Slice 4 of plans/markdown-viewer.md, decision 1): the feed sheet imports the KaTeX CSS as styles.css does, and the display box's twin
  ".katex-display {",
  // the Obsidian constructs and the figure gate (Slice 4; md-config.ts and figure-gate.ts render them, anchor-map.ts maps them)
  // (doubled `.md X, .fileview-md X`: the grammar sits on the marked singleton, so the chat's markdown bodies render the constructs too)
  ".md details.md-frontmatter, .fileview-md details.md-frontmatter {", ".md .md-frontmatter-head, .fileview-md .md-frontmatter-head {", ".md details.md-frontmatter pre, .fileview-md details.md-frontmatter pre {",
  ".md sup.md-fnref, .fileview-md sup.md-fnref {", ".md sup.md-fnref a, .fileview-md sup.md-fnref a {", ".md .md-footnote, .fileview-md .md-footnote {", ".md .md-fnback, .fileview-md .md-fnback {",
  ".md .md-callout, .fileview-md .md-callout {", ".md .md-callout-title, .fileview-md .md-callout-title {", ".md details.md-callout .md-callout-title, .fileview-md details.md-callout .md-callout-title {",
  ".md .md-callout-note, .fileview-md .md-callout-note, .md .md-callout-info, .fileview-md .md-callout-info, .md .md-callout-abstract, .fileview-md .md-callout-abstract, .md .md-callout-summary, .fileview-md .md-callout-summary, .md .md-callout-tldr, .fileview-md .md-callout-tldr, .md .md-callout-todo, .fileview-md .md-callout-todo, .md .md-callout-quote, .fileview-md .md-callout-quote, .md .md-callout-cite, .fileview-md .md-callout-cite, .md .md-callout-example, .fileview-md .md-callout-example {",
  ".md .md-callout-tip, .fileview-md .md-callout-tip, .md .md-callout-hint, .fileview-md .md-callout-hint, .md .md-callout-success, .fileview-md .md-callout-success, .md .md-callout-check, .fileview-md .md-callout-check, .md .md-callout-done, .fileview-md .md-callout-done {",
  ".md .md-callout-important, .fileview-md .md-callout-important {",
  ".md .md-callout-warning, .fileview-md .md-callout-warning, .md .md-callout-attention, .fileview-md .md-callout-attention, .md .md-callout-question, .fileview-md .md-callout-question, .md .md-callout-help, .fileview-md .md-callout-help, .md .md-callout-faq, .fileview-md .md-callout-faq {",
  ".md .md-callout-caution, .fileview-md .md-callout-caution, .md .md-callout-danger, .fileview-md .md-callout-danger, .md .md-callout-error, .fileview-md .md-callout-error, .md .md-callout-failure, .fileview-md .md-callout-failure, .md .md-callout-fail, .fileview-md .md-callout-fail, .md .md-callout-missing, .fileview-md .md-callout-missing, .md .md-callout-bug, .fileview-md .md-callout-bug {",
  ".md mark:not(.cmt-hl), .fileview-md mark {", ".md .fv-wikilink, .fileview-md .fv-wikilink {", ".fileview-md a.fv-embed {",
  ".fileview-md .fv-gate {", ".fileview-md .fv-gate:hover, .fileview-md .fv-gate:focus-visible {", ".fileview-md .fv-gate > :not([data-fv-label]) {",
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

// Every rule declared under `head` in `css`, in sheet order: each occurrence of the head at a line start, read
// through its first `}`. Line-start only, so a head that is the tail of a longer head resolves to its own rule.
function rulesOf(css: string, head: string): string[] {
  const text = "\n" + css;   // a head on the sheet's first line is found the same way as any other
  const key = "\n" + head;
  const out: string[] = [];
  for (let at = text.indexOf(key); at >= 0; at = text.indexOf(key, at + 1)) {
    out.push(text.slice(at + 1, text.indexOf("}", at) + 1));
  }
  return out;
}

test("the rule reader anchors a head at a line start and reads every rule declared under it", () => {
  // a synthetic sheet in the sheets' own shape: a two-selector head whose tail is another head, the shorter head's
  // own rule after it, and the longer head declared a second time further down
  const css = [
    "/* a comment */",
    ".fv-a, .fv-b {",
    "  color: var(--fg); }",
    ".fv-b { color: var(--dim); }",
    ".fv-a, .fv-b { margin: 0; }",
  ].join("\n");
  assert.deepEqual(rulesOf(css, ".fv-b {"), [".fv-b { color: var(--dim); }"], "the tail of a longer head resolves to its own rule");
  assert.deepEqual(rulesOf(css, ".fv-a, .fv-b {"), [".fv-a, .fv-b {\n  color: var(--fg); }", ".fv-a, .fv-b { margin: 0; }"], "a head declared twice yields both rules");
  assert.deepEqual(rulesOf(css, ".fv-c {"), [], "an absent head yields nothing");
  assert.deepEqual(rulesOf(".fv-a { top: 0; }\n.fv-a { left: 0; }", ".fv-a {"), [".fv-a { top: 0; }", ".fv-a { left: 0; }"], "a head on the first line counts");
});

test("the viewer's shared chrome exists in BOTH sheets, byte-equal", () => {
  for (const head of RULES) {
    const chat = rulesOf(CHAT, head), feed = rulesOf(FEED, head);
    assert.ok(chat.length > 0, head + " present in styles.css");
    assert.ok(feed.length > 0, head + " present in feed.css");
    assert.deepEqual(chat, feed, head + " mirrors exactly");
  }
});
