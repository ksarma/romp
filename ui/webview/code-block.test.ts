// The shared code-block module (code-block.ts; Slice 3 of plans/markdown-viewer.md, 2026-09-08): the chat's per-line
// rows and Copy button, now the viewer's too. The chat's highlight() (render.ts) and the viewer's mdBlock (file-view.ts)
// import the same two functions; file-view.ts cannot import render.ts (render.ts imports it, and the Files and feed
// bundles must not carry the chat), so the module is their meeting point. Executed: the pure walk (wrapLinesHtml)
// over plain and highlighted lines, a span straddling a newline, a trailing newline. Pinned: the two callers' shapes
// (the raw text captured before the rewrite, every fence wrapped and given Copy, the math fallback's exemption), the
// bundle boundary (file-view.ts, files.ts and feed.ts import nothing from render.ts), the sheets' scoped copies
// byte-equal in styles.css and feed.css with the counter reset on `.fileview-md pre code`, decision 5's six grammars
// registered on the core by viewer-grammars.ts (executed, in node) and reached through file-view.ts, and the chat's
// auto-detection kept to its ten (highlight-cache.ts AUTO_LANGUAGES, executed).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import hljs from "highlight.js/lib/core";
import { wrapLinesHtml } from "./code-block";
import { AUTO_LANGUAGES, highlightHtml, newHighlightCache } from "./highlight-cache";
import { VIEWER_GRAMMARS } from "./viewer-grammars";

const UI = path.resolve(process.cwd(), "..", "ui", "webview");
const read = (f: string) => fs.readFileSync(path.join(UI, f), "utf8");
const BLOCK = read("code-block.ts");
const RENDER = read("render.ts");
const VIEW = read("file-view.ts");
const CHAT = read("styles.css");
const FEED = read("feed.css");

// ── the walk, executed ─────────────────────────────────────────────────────────────────────────────

test("wrapLinesHtml: one row per line, the newlines dropped, a trailing newline not a row", () => {
  assert.equal(wrapLinesHtml("a\nb\n"), '<span class="cl"><span class="ct">a</span></span><span class="cl"><span class="ct">b</span></span>');
  assert.equal(wrapLinesHtml("a\n\nb"), '<span class="cl"><span class="ct">a</span></span><span class="cl"><span class="ct"></span></span><span class="cl"><span class="ct">b</span></span>', "a blank line is an empty row");
  assert.equal(wrapLinesHtml("only"), '<span class="cl"><span class="ct">only</span></span>');
  assert.equal(wrapLinesHtml(""), '<span class="cl"><span class="ct"></span></span>', "an empty block is one empty row (a single empty line is not a trailing newline)");
  assert.equal(wrapLinesHtml("a\nb").indexOf("\n"), -1, "no newline survives: a reader of the lines puts it back between rows (anchor-map.ts codeRuns)");
});

test("wrapLinesHtml: a highlighter span that straddles a newline is closed on its line and re-opened on the next", () => {
  const html = '<span class="hljs-string">"one\ntwo"</span> x';
  const out = wrapLinesHtml(html);
  assert.equal(out, '<span class="cl"><span class="ct"><span class="hljs-string">"one</span></span></span><span class="cl"><span class="ct"><span class="hljs-string">two"</span> x</span></span>');
  // nested: two open spans across the break, both re-opened in order
  const nested = wrapLinesHtml('<span class="a"><span class="b">1\n2</span>3</span>');
  assert.equal(nested, '<span class="cl"><span class="ct"><span class="a"><span class="b">1</span></span></span></span><span class="cl"><span class="ct"><span class="a"><span class="b">2</span>3</span></span></span>');
});

// ── the callers ────────────────────────────────────────────────────────────────────────────────────

test("render.ts and file-view.ts import the two functions from the module; render.ts keeps no copy; the viewer never imports the chat", () => {
  assert.match(RENDER, /^import \{ wrapCodeLines, addCopyBtn \} from "\.\/code-block";/m);
  assert.match(VIEW, /^import \{ wrapCodeLines, addCopyBtn \} from "\.\/code-block";/m);
  assert.doesNotMatch(RENDER, /^(export )?function (wrapCodeLines|addCopyBtn|copyText|fallbackCopy)\(/m, "the definitions moved");
  assert.match(BLOCK, /^export function wrapLinesHtml\(html: string\): string/m);
  assert.match(BLOCK, /^export function wrapCodeLines\(code: HTMLElement\): void/m);
  assert.match(BLOCK, /^export function addCopyBtn\(pre: HTMLElement, raw: string\): void/m);
  assert.match(BLOCK, /^export function copyText\(text: string\): Promise<boolean>/m);
  assert.doesNotMatch(BLOCK, /from "\.\/render"|from "\.\/file-view"/, "the module imports neither caller");
  for (const f of ["file-view.ts", "files.ts", "feed.ts", "code-block.ts", "viewer-grammars.ts", "anchor-map.ts", "reader-place.ts"]) {
    assert.doesNotMatch(read(f), /from "\.\/render"/, f + " imports nothing from the chat (the Files and feed bundles must not carry it)");
  }
});

test("mdBlock: the raw text is captured before the highlight rewrite, a named registered language is highlighted (never guessed), then EVERY fence is wrapped and given Copy; the math fallback keeps Copy alone", () => {
  const fn = VIEW.split("function mdBlock(")[1].split("export function rewriteFigureSrcs")[0];
  const pass = fn.slice(fn.indexOf('box.querySelectorAll("pre code").forEach'), fn.indexOf("linkifyFileText(box, doc.path)"));
  assert.match(pass, /const raw = codeEl\.textContent \|\| "";/);
  assert.ok(pass.indexOf("const raw = codeEl.textContent") < pass.indexOf("codeEl.innerHTML = hljs.highlight(raw"), "raw first, then the rewrite highlights that same string");
  assert.match(pass, /if \(codeEl\.classList\.contains\("md-math-src"\)\) \{ if \(host\) addCopyBtn\(host, raw\); return; \}/, "the math fallback: Copy, no highlight, no rows (the chat's highlight() does the same; render-math.test.ts)");
  assert.match(pass, /if \(lang && hljs\.getLanguage\(lang\)\) \{/, "highlight only a named, registered language");
  assert.doesNotMatch(VIEW, /hljs\.highlightAuto\(/, "no guessing in the viewer");
  assert.match(pass, /\}\s*\n\s*wrapCodeLines\(codeEl\);\s*\n\s*if \(host\) addCopyBtn\(host, toCopy\);/, "the wrap and the Copy button sit OUTSIDE the language branch: an unregistered or unnamed fence gets them too");
  // what Copy copies is the fence's text as the NOTE holds it (fence-source.ts): the raw text is marked's, its leading tabs
  // already four spaces each (the Slice 3 review: a Makefile recipe pasted back with spaces); the queue is keyed by the raw
  // text and consumed in document order, and a fence the module did not find in the note falls back to the raw text
  assert.match(pass, /const queued = copySources\.get\(raw\);\n\s*const toCopy = \(queued && queued\.length \? queued\.shift\(\) : null\) \?\? raw;/, "Copy's text comes off the source queue, the raw text when the fence was not found");
  assert.match(fn, /const copySources = fenceCopyQueue\(text, fences\);/, "the queue is built from the note and the code tokens the parse collected");
  assert.match(fn, /if \(t\.type === "code"\) \{ const c = t as Tokens\.Code; fences\.push\(\{ text: c\.text, indented: c\.codeBlockStyle === "indented" \}\); \}/, "the parse's walkTokens collects every code token, for every document kind");
  assert.match(VIEW, /^import \{ fenceCopyQueue, type Fence \} from "\.\/fence-source";/m);
  assert.ok(pass.indexOf("wrapCodeLines(codeEl)") > pass.indexOf("codeEl.classList.add(\"hljs\")"), "the rows are cut after the highlight, as in the chat");
  // the counter reset is the sheets' `.fileview-md pre code`, not `code.hljs`: a plain fence carries no hljs class
  assert.ok(!/wrapCodeLines\(codeEl\);[\s\S]{0,80}classList\.add\("hljs"\)/.test(pass), "no hljs class is added to a plain fence for the counter's sake (the sheet resets on pre code)");
});

test("a wrapped fence's rows are lines to the viewer's link pass: `.cl` is a line unit beside the Raw view's `.fv-cl`", () => {
  // the pass joins the text nodes under the nearest unit; with the newlines gone from a wrapped fence the pre alone read
  // as one line, and a path ending one line ran into the path beginning the next (file-view-links-browser.test.ts holds
  // the fence's three paths as links)
  assert.match(read("file-view-links.ts"), /^export const LINE_UNITS = "\.fv-cl, \.cl, p, li, /m);
});

test("the chat's highlight() is unchanged in shape: raw first, the cache, the rows when lineNos, Copy on the <pre>", () => {
  const hl = RENDER.slice(RENDER.indexOf("function highlight(container: HTMLElement"), RENDER.indexOf("function dot("));
  assert.match(hl, /const raw = code\.textContent \|\| "";/);
  assert.match(hl, /code\.innerHTML = highlightHtml\(hljs, lang, raw\);/);
  assert.match(hl, /if \(lineNos\) wrapCodeLines\(code\);/);
  assert.match(hl, /if \(pre && pre\.tagName === "PRE"\) addCopyBtn\(pre as HTMLElement, raw\);/);
});

// ── the sheets ─────────────────────────────────────────────────────────────────────────────────────

const ruleOf = (css: string, head: string): string => { const at = css.indexOf(head); assert.ok(at >= 0, head + " present"); return css.slice(at, css.indexOf("}", at) + 1); };
const decls = (rule: string): string[] => rule.slice(rule.indexOf("{") + 1, -1).split(";").map((d) => d.trim()).filter(Boolean);

test("both sheets: the viewer's fences carry scoped copies of the chat's row and Copy rules, byte-equal, the counter reset and tab-size on `.fileview-md pre code`", () => {
  const HEADS = [".fileview-md pre code .cl {", ".fileview-md pre code .cl::before {", ".fileview-md pre code .ct {", ".fileview-md pre.has-copy {", ".fileview-md .code-copy {",
    ".fileview-md pre.has-copy:hover .code-copy, .fileview-md .code-copy:focus-visible {", ".fileview-md .code-copy:hover {", ".fileview-md .code-copy.copied {"];
  for (const head of HEADS) assert.equal(ruleOf(CHAT, head), ruleOf(FEED, head), head + " mirrors exactly");
  for (const [name, css] of [["styles.css", CHAT], ["feed.css", FEED]] as const) {
    const code = decls(ruleOf(css, ".fileview-md pre code {"));
    assert.ok(code.includes("counter-reset: ln"), name + ": the line counter resets on every fence, hljs class or not");
    assert.ok(code.includes("tab-size: 4"), name + ": tabs as the Raw view shows them");
    assert.ok(decls(ruleOf(css, ".fileview-pre {")).includes("tab-size: 4"), name + ": ...which is 4 (editor-lazy.test.ts pins the editor's)");
    // the copies are the chat's rules with the viewer's scope in front, declaration for declaration
    assert.deepEqual(decls(ruleOf(css, ".fileview-md pre code .cl {")), decls(ruleOf(CHAT, "\npre code .cl {")), name + ": .cl is the chat's");
    assert.deepEqual(decls(ruleOf(css, ".fileview-md pre code .cl::before {")), decls(ruleOf(CHAT, "\npre code .cl::before {")), name + ": the gutter is the chat's");
    assert.deepEqual(decls(ruleOf(css, ".fileview-md pre code .ct {")), decls(ruleOf(CHAT, "\npre code .ct {")), name + ": .ct is the chat's");
    const copy = decls(ruleOf(css, ".fileview-md .code-copy {"));
    const chatCopy = decls(ruleOf(CHAT, "\n.code-copy {"));
    assert.deepEqual(copy.filter((d) => !d.startsWith("background")), chatCopy.filter((d) => !d.startsWith("background")), name + ": the Copy button is the chat's, but for the tint's fallback");
    assert.ok(copy.includes("background: var(--code-bg, rgba(217, 119, 87, 0.10))"), name + ": the code tint carries the chat's literal as its fallback (feed.css defines no --code-bg in :root)");
    assert.match(css, /@media \(hover: none\) \{ \.fileview-md \.code-copy \{ opacity: 0\.8; \} \}/, name + ": touch keeps the button visible");
  }
  // every var() the feed's copies use resolves on the feed page (feed-css-vars.test.ts holds the whole sheet; this names the block)
  const defined = new Set([...FEED.matchAll(/(--[a-zA-Z0-9-]+)\s*:/g)].map((m) => m[1]));
  const block = FEED.slice(FEED.indexOf(".fileview-md pre code .cl {"), FEED.indexOf("@media (hover: none) { .fileview-md .code-copy"));
  for (const m of block.matchAll(/var\(\s*(--[a-zA-Z0-9-]+)\s*\)/g)) assert.ok(defined.has(m[1]), "feed.css defines " + m[1] + " (a fallback-less var in the fence block)");
});

// ── the grammars ───────────────────────────────────────────────────────────────────────────────────

test("viewer-grammars.ts registers decision 5's six grammars, with their aliases, on the bundle's one hljs core; file-view.ts imports it and the chat auto-detects among its ten only", () => {
  assert.deepEqual(Object.keys(VIEWER_GRAMMARS).sort(), ["c", "go", "golang", "h", "ini", "java", "rs", "rust", "sql", "toml"].sort());
  for (const name of ["rust", "rs", "go", "golang", "c", "h", "java", "sql", "toml", "ini"]) assert.ok(hljs.getLanguage(name), name + " is registered once the module is imported");
  assert.equal(hljs.getLanguage("toml")!.name, "TOML, also INI", "toml is hljs's ini grammar (no toml module in hljs 11; registerLanguage builds a grammar per name, so the two are equal by name, not identity)");
  assert.equal(hljs.getLanguage("ini")!.name, hljs.getLanguage("toml")!.name);
  assert.equal(hljs.highlight("fn main() {}", { language: "rust" }).value.includes("hljs-keyword"), true, "the rust grammar tokenizes");
  assert.equal(hljs.highlight("[section]\nkey = 1", { language: "toml" }).value.includes("hljs-"), true, "the toml alias tokenizes");
  assert.match(VIEW, /^import "\.\/viewer-grammars";/m, "the viewer reaches the six (files.ts and feed.ts import file-view.ts; the chat bundle does too)");
  assert.doesNotMatch(RENDER, /viewer-grammars/, "render.ts imports the module through file-view.ts, not on its own");
  // the chat's ten, by the grammar imports in render.ts, are the auto-detection subset
  const ten = [...RENDER.matchAll(/^import \w+ from "highlight\.js\/lib\/languages\/(\w+)";/gm)].map((m) => m[1]).sort();
  assert.equal(ten.length, 10, "render.ts imports ten grammars: " + ten.join(","));
  assert.deepEqual([...AUTO_LANGUAGES].sort(), ten, "AUTO_LANGUAGES is exactly the chat's ten");
  assert.deepEqual([...VIEW.matchAll(/^import \w+ from "highlight\.js\/lib\/languages\/(\w+)";/gm)].map((m) => m[1]).sort(), ten, "file-view.ts registers the same ten itself; the six live in viewer-grammars.ts");
});

test("highlightHtml passes the ten-name subset to highlightAuto for an unlabeled fence, and names the grammar for a labeled one", () => {
  const seen: unknown[] = [];
  const hl = {
    getLanguage: (n: string) => (n === "python" ? {} : undefined),
    highlight: (raw: string, o: { language: string }) => { seen.push(["named", o.language]); return { value: "<n>" + raw + "</n>" }; },
    highlightAuto: (raw: string, subset?: readonly string[]) => { seen.push(["auto", subset]); return { value: "<a>" + raw + "</a>" }; },
  };
  const c = newHighlightCache();
  assert.equal(highlightHtml(hl, "python", "x = 1", c), "<n>x = 1</n>");
  assert.equal(highlightHtml(hl, undefined, "x = 1", c), "<a>x = 1</a>");
  assert.equal(highlightHtml(hl, "rust", "x = 1", c), "<a>x = 1</a>", "a language this fake does not know reads as unlabeled: the cache's key for it is the unlabeled one, so this is the entry above, a hit (in the chat bundle rust IS known, through file-view.ts)");
  assert.deepEqual(seen, [["named", "python"], ["auto", AUTO_LANGUAGES]], "one auto-detection, with the subset");
  assert.equal(seen[1][1], AUTO_LANGUAGES, "the very list, not a copy");
  assert.equal(highlightHtml(hl, undefined, "y = 2", c), "<a>y = 2</a>");
  assert.equal(seen.length, 3); assert.equal(seen[2][1], AUTO_LANGUAGES, "every auto-detection carries it");
});
