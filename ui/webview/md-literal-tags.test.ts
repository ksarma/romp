// The rule for an inline start tag with no end tag in its block (md-literal-tags.ts; plans/file-review.md, decision 52), at the
// token level: which tokens the walk converts and which it leaves, over marked's lexer under the one configuration
// (md-config.ts), and what the converted token renders as through marked's own parser (the installed marked 12's text renderer
// writes a text token's text as is, so the text must be escaped as its inline text tokenizer escapes text; a `Tokens.Text` in
// that version has no `escaped` field). The rendered HTML of every shape the rule leaves alone is byte for byte marked.parse's,
// so the viewer's output for those notes is what it was. The source pins at the end hold the one rule to its two callers: the
// viewer's parse (file-view.ts mdBlock) and the map's lex (anchor-map.ts placeTokens) both import and call the function, and
// md-config.ts and the chat's md() (render.ts) do not, so the chat renders as before. The map's side over a rendered DOM is
// anchor-map-literal-tags.test.ts; the real pane in Chromium is anchor-map-literal-tags-browser.test.ts. Synthetic text only.
import { test } from "node:test";
import assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { marked, type Token, type Tokens } from "marked";
import { applyMdConfig } from "./md-config";
import { literalizeUnclosedTags, escapeInlineText, VOID_ELEMENTS } from "./md-literal-tags";
import { viewerHtml } from "./file-view";   // the viewer's parse (mdBlock's recipe): the lexer, the rule, the per-call walk, the parser
import { headingSlug } from "./md-links";

applyMdConfig();
const UI = path.resolve(process.cwd(), "..", "ui", "webview");
const read = (f: string): string => fs.readFileSync(path.join(UI, f), "utf8");

/** The lexed tree with the rule applied. */
function lexed(src: string): Token[] { const tokens = marked.lexer(src); literalizeUnclosedTags(tokens); return tokens; }
/** The inline tokens of the first block of `src` (a paragraph's, a heading's), flattened in document order. */
function inlineOf(src: string, at = 0): Token[] {
  const t = lexed(src)[at] as { tokens?: Token[] };
  const out: Token[] = [];
  const walk = (list: Token[]) => { for (const x of list) { out.push(x); const kids = (x as { tokens?: Token[] }).tokens; if (kids) walk(kids); } };
  walk(t.tokens || []);
  return out;
}
/** `type:raw` of every tag among the inline tokens of block `at`: the html tokens, and the text tokens the rule made of tags. */
const tags = (src: string, at = 0): string[] => inlineOf(src, at).filter((t) => (t.type === "html" || t.type === "text") && /^<[!?\/a-zA-Z]/.test(t.raw) && t.raw.endsWith(">")).map((t) => t.type + ":" + t.raw);
/** Whether the first block's inline run holds a `text` token whose raw is `raw` and whose text is `text`. */
function converted(src: string, raw: string, at = 0): Tokens.Text | undefined {
  return inlineOf(src, at).find((t) => t.type === "text" && t.raw === raw) as Tokens.Text | undefined;
}

test("an inline start tag with no end tag in its block becomes a text token in place: raw kept, text the raw escaped, marked's own fields gone, and the parser renders the tag's characters as text where marked.parse passed the tag through (before: the paragraph held an `html` token predicting no text, and the browser opened a table inside it)", () => {
  const SRC = "Intro (<table>__widths.csv) mid.\n\n## Second heading\n\nPara.\n\n| a | b |\n|---|---|\n| c | d |\n";
  const t = converted(SRC, "<table>");
  assert.ok(t, "the `<table>` token is text now");
  assert.equal(t!.text, "&lt;table&gt;");
  assert.deepEqual(Object.keys(t!).sort(), ["raw", "text", "type"], "an html token's pre, block, inLink and inRawBlock are gone");
  assert.equal(inlineOf(SRC).filter((x) => x.type === "html").length, 0, "no html token left in the run");
  assert.equal(viewerHtml(SRC).split("\n")[0], "<p>Intro (&lt;table&gt;__widths.csv) mid.</p>", "the parser writes the escaped text");
  assert.equal((marked.parse(SRC) as string).split("\n")[0], "<p>Intro (<table>__widths.csv) mid.</p>", "marked.parse alone passes the tag through (the chat's rendering, and the viewer's before)");
  assert.ok(viewerHtml(SRC).includes("<h2>Second heading</h2>") && viewerHtml(SRC).includes("<table>\n<thead>"), "the later blocks render as they did");
});

test("the raw-text and RCDATA elements the parser reads to their end tag (`<title>`, `<script>`, `<style>`, `<textarea>`, `<xmp>`, `<iframe>`, `<plaintext>`, `<template>`) left open in a paragraph are text too, and closed within the block they stay HTML", () => {
  for (const name of ["title", "script", "style", "textarea", "xmp", "iframe", "plaintext", "template"]) {
    const src = `Lead <${name}> rest of the line.\n\n## After\n\nPara.\n`;
    assert.ok(converted(src, `<${name}>`), `<${name}> left open: text`);
    assert.equal(viewerHtml(src).split("\n")[0], `<p>Lead &lt;${name}&gt; rest of the line.</p>`, `<${name}>: the line renders whole`);
    const closed = `Lead <${name}>inside</${name}> tail.\n`;
    assert.deepEqual(tags(closed), [`html:<${name}>`, `html:</${name}>`], `<${name}> closed: HTML on both ends`);
    assert.equal(viewerHtml(closed), marked.parse(closed), `<${name}> closed: marked.parse's output`);
  }
});

test("a start tag closed within its block stays HTML, with marked.parse's output byte for byte: `<b>x</b>`, `<span class=\"a\">y</span>`, `<kbd>Ctrl</kbd>`, a closer in upper case, a closer inside emphasis, an opener inside a link's label closed after it", () => {
  for (const src of ["Press <b>x</b> now.\n", "See <span class=\"a\">y</span> here.\n", "Hold <kbd>Ctrl</kbd> down.\n", "Case <B>x</b> mixed.\n", "Emph <b>x *y</b>* z.\n", "Link [<b>x](http://a.test) y</b> z.\n", "Nested <b><i>x</i></b> y.\n", "Interleaved <b><i>x</b></i> y.\n"]) {
    assert.equal(inlineOf(src).filter((t) => t.type === "text" && t.raw.startsWith("<")).length, 0, src.trim() + ": nothing converted");
    assert.equal(viewerHtml(src), marked.parse(src), src.trim() + ": marked.parse's output");
  }
  assert.deepEqual(tags("Emph <b>x *y</b>* z.\n"), ["html:<b>", "html:</b>"], "the closer inside the emphasis counts (the run is flattened)");
});

test("void elements and the self-closing syntax stay HTML, in the output and in the tokens (`<br>`, `<img src>`, `<x/>`, `<wbr>`, `<input>`, `<hr>` inline, `<area>`, `<col>`, `<embed>`, `<source>`, `<track>`, `<x />`); the void list is HTML's fourteen", () => {
  const VOID_SRC = "a<br>b <img src=\"a.png\"> c <x/> d <wbr> e <input type=\"checkbox\"> f <hr> g <area> h <col> i <embed> j <source> k <track> l <x /> m <base> n <link> o <meta> p <param> q.\n";
  assert.equal(inlineOf(VOID_SRC).filter((t) => t.type === "text" && t.raw.startsWith("<")).length, 0, "nothing converted");
  assert.equal(viewerHtml(VOID_SRC), marked.parse(VOID_SRC), "marked.parse's output");
  assert.deepEqual(Array.from(VOID_ELEMENTS).sort(), ["AREA", "BASE", "BR", "COL", "EMBED", "HR", "IMG", "INPUT", "LINK", "META", "PARAM", "SOURCE", "TRACK", "WBR"]);
});

test("an unclosed formatting tag renders as text: `<b>rest of line`, `<i>`, `<a href=...>`; nothing after it is an element's, and a later block's end tag does not close it (the block is the token that owns the run)", () => {
  assert.equal(viewerHtml("Start <b>rest of line.\n").split("\n")[0], "<p>Start &lt;b&gt;rest of line.</p>");
  assert.equal(viewerHtml("Start <i>rest.\n").split("\n")[0], "<p>Start &lt;i&gt;rest.</p>");
  assert.equal(viewerHtml("Start <a href=\"http://a.test\">rest.\n").split("\n")[0], "<p>Start &lt;a href=&quot;http://a.test&quot;&gt;rest.</p>");
  const LATER = "Start <b>rest.\n\nAnd </b> the end.\n";
  assert.ok(converted(LATER, "<b>"), "the opener: text");
  assert.deepEqual(tags(LATER, 2), ["html:</b>"], "the later block's end tag: an html token still (a stray, blockEnds' to read)");
  assert.equal(viewerHtml(LATER), "<p>Start &lt;b&gt;rest.</p>\n<p>And </b> the end.</p>\n");
});

test("matching is by name, innermost first: `<b>x<b>y</b>` keeps the inner pair as HTML and makes the first `<b>` text; `<B>x</b>` is closed; `<b>x *y</b>*` is closed; `<b><i>x</b>` closes the b and leaves the i text; a comment between counts for nothing", () => {
  assert.deepEqual(tags("A <b>x<b>y</b> z.\n"), ["text:<b>", "html:<b>", "html:</b>"]);
  assert.equal(viewerHtml("A <b>x<b>y</b> z.\n").split("\n")[0], "<p>A &lt;b&gt;x<b>y</b> z.</p>");
  assert.deepEqual(tags("A <B>x</b> z.\n"), ["html:<B>", "html:</b>"]);
  assert.deepEqual(tags("A <b><i>x</b> z.\n"), ["html:<b>", "text:<i>", "html:</b>"]);
  assert.deepEqual(tags("A <b>x<!-- c --><b>y</b> z.\n"), ["text:<b>", "html:<!-- c -->", "html:<b>", "html:</b>"]);
});

test("the rule in a heading, a tight list item, a loose list item, a table cell, a quote's paragraph and a footnote definition, each block its own run: the cell's closer does not serve the paragraph's opener", () => {
  assert.equal(viewerHtml("## Head <table> tail\n").split("\n")[0], "<h2>Head &lt;table&gt; tail</h2>");
  assert.equal(viewerHtml("- item <b>x\n- plain\n"), "<ul>\n<li>item &lt;b&gt;x</li>\n<li>plain</li>\n</ul>\n");
  assert.equal(viewerHtml("- item <b>x\n\n- plain\n"), "<ul>\n<li><p>item &lt;b&gt;x</p>\n</li>\n<li><p>plain</p>\n</li>\n</ul>\n");
  assert.ok(viewerHtml("| <span> x | y |\n|---|---|\n| a | <i>b |\n").includes("<th>&lt;span&gt; x</th>") && viewerHtml("| <span> x | y |\n|---|---|\n| a | <i>b |\n").includes("<td>&lt;i&gt;b</td>"), "the header's cell and a body cell");
  assert.equal(viewerHtml("> quote <i> more\n"), "<blockquote>\n<p>quote &lt;i&gt; more</p>\n</blockquote>\n");
  assert.ok(viewerHtml("[^1]: note <b>x\n\nSee[^1].\n").includes("note &lt;b&gt;x"), "a footnote definition's run");
  assert.ok(viewerHtml("> [!note] T\n> body <b>x\n").includes("body &lt;b&gt;x"), "a callout's body");
  const CELL = "Open <b>x here.\n\n| a | b |\n|---|---|\n| c</b> | d |\n";
  assert.ok(converted(CELL, "<b>"), "the paragraph's opener: text, whatever a later cell holds");
  assert.ok(viewerHtml(CELL).includes("<td>c</b></td>"), "the cell's stray closer stays HTML");
});

test("a heading holding a converted tag renders the tag's characters in its text, so the id the viewer mints from the rendered text (file-view.ts mintHeadingIds: headingSlug over the sanitized heading's textContent) slugs them too: `## Results <b>` renders `<h2>Results &lt;b&gt;</h2>` and slugs `results-b`, where `## Results` slugs `results`, the slug GitHub gives the heading with the tag read as HTML; decision 52 of plans/file-review.md records the divergence as left (the review's consolidation pass), so a change that hides the tag's characters from the slug retires that record and this pin", () => {
  assert.equal(viewerHtml("## Results <b>\n"), "<h2>Results &lt;b&gt;</h2>\n", "the heading's text carries the tag");
  const shown = "Results <b>";   // the h2's textContent once the browser decodes the escape
  assert.equal(headingSlug(shown), "results-b");
  assert.equal(headingSlug("Results"), "results", "the slug of the heading without the tag, GitHub's for it with the tag");
  assert.notEqual(headingSlug(shown), headingSlug("Results"), "the recorded divergence");
  const VIEW = read("file-view.ts");
  assert.match(VIEW, /function mintHeadingIds\(root: ParentNode\): void \{\n {2}const heads = Array\.from\(root\.querySelectorAll\("h1, h2, h3, h4, h5, h6"\)\) as HTMLElement\[\];\n {2}const slugs = uniqueSlugs\(heads\.map\(\(h\) => headingSlug\(h\.textContent \|\| ""\)\)\);/, "the minting reads the heading's textContent and nothing else, so the record describes this code");
  assert.ok(VIEW.includes("recorded as left in decision 52") && VIEW.includes("`## Results <b>` mints md-results-b"), "file-view.ts says so where it mints the ids and where it calls the slug GitHub's");
});

test("a comment, a stray end tag, a declaration, a processing instruction and a CDATA section are untouched, with marked.parse's output byte for byte", () => {
  for (const src of ["a <!-- x --> b\n", "a </div> b\n", "a <!DOCTYPE x> b\n", "a <?php echo 1; ?> b\n", "a <![CDATA[ x ]]> b\n", "**Bold** </div>\n"]) {
    assert.equal(inlineOf(src).filter((t) => t.type === "text" && t.raw.startsWith("<") && t.raw.length > 1).length, 0, src.trim() + ": nothing converted");
    assert.equal(viewerHtml(src), marked.parse(src), src.trim() + ": marked.parse's output");
  }
});

test("the converted text is escaped as marked's inline text tokenizer escapes text (the installed marked 12: `<`, `>`, `\"`, `'` always, `&` unless it begins a character reference), so the reader sees the tag as written; the walk is idempotent", () => {
  const tag = "<a href=\"x&amp;y\" title='t'>";
  const t = converted("Open " + tag + " rest.\n", tag);
  assert.ok(t);
  // marked's own escape of the same characters: the text token after an escaped `<`
  const own = marked.lexer("Open \\" + tag + " rest.\n")[0] as Tokens.Paragraph;
  const after = own.tokens.find((x) => x.type === "text" && x.raw.startsWith("a href")) as Tokens.Text;
  assert.equal(t!.text, "&lt;" + after.text.slice(0, -" rest.".length), "the same escape marked applies to text: the quotes, the `>`, the reference kept");
  assert.equal(escapeInlineText("<a title=\"a & b\">"), "&lt;a title=&quot;a &amp; b&quot;&gt;", "an `&` that begins no reference is escaped");
  const tokens = marked.lexer("Open <b>x <b>y</b> z.\n");
  literalizeUnclosedTags(tokens);
  const once = JSON.stringify(tokens);
  literalizeUnclosedTags(tokens);
  assert.equal(JSON.stringify(tokens), once, "a second pass changes nothing");
});

test("source: one rule, two callers. file-view.ts viewerHtml, mdBlock's parse, runs the lexer, the rule, the caller's walk and the parser at the function's own level, over a copy of the singleton's defaults as marked.parse copies them, and mdBlock hands it the walkTokens it ran inside marked.parse, unchanged and in the same order; anchor-map.ts placeTokens runs the rule on the line after Lexer.lex; md-config.ts registers nothing for it and the chat's md() (render.ts) still parses with marked.parse; the module imports marked's types alone", () => {
  const VIEW = read("file-view.ts"), MAP = read("anchor-map.ts"), CONFIG = read("md-config.ts"), RENDER = read("render.ts"), MOD = read("md-literal-tags.ts"), CHAT = read("chat-md.ts");
  assert.match(VIEW, /^import \{ literalizeUnclosedTags \} from "\.\/md-literal-tags";/m, "the viewer imports the rule");
  const recipe = VIEW.split("export function viewerHtml(text: string, walk?: (token: Token) => void): string {")[1].split("\n}\n")[0];
  assert.match(recipe, /^\n {2}const opts = \{ \.\.\.marked\.defaults \};\n {2}const tokens = marked\.lexer\(text, opts\);\n {2}literalizeUnclosedTags\(tokens\);\n {2}if \(walk\) marked\.walkTokens\(tokens, walk\);\n {2}return marked\.parser\(tokens, opts\);$/,
    "the lexer, the rule, the caller's walk, the parser, each at the function's own level, and nothing else");
  const mdFn = VIEW.split("function mdBlock(text: string, doc?: MdDocLoc): HTMLElement {")[1].split("\n}\n")[0];
  assert.match(mdFn, /\n {2}const base = marked\.defaults\.walkTokens;\n(?: {2}\/\/[^\n]*\n)* {2}const dirty = viewerHtml\(text, \(t\) => \{\n {4}if \(t\.type === "code"\) \{ const c = t as Tokens\.Code; fences\.push\(\{ text: c\.text, indented: c\.codeBlockStyle === "indented" \}\); \}\n {4}if \(doc && doc\.kind === "file"\) viewerWalkTokens\(t\);\n {4}if \(base\) void base\.call\(marked, t\);\n {2}\}\);\n/,
    "mdBlock's parse is the recipe's, the walk it ran before (its three steps in order) handed over");
  assert.equal((mdFn.match(/marked\.parse\(/g) || []).length, 0, "mdBlock no longer calls marked.parse (the tokens are in hand between the recipe's lexer and its parser)");
  assert.equal((mdFn.match(/marked\.(lexer|parser)\(|literalizeUnclosedTags\(/g) || []).length, 0, "and holds no step of its own: the recipe does");
  assert.match(MAP, /^import \{ literalizeUnclosedTags, VOID_ELEMENTS \} from "\.\/md-literal-tags";/m, "the map imports the rule and the void list");
  assert.match(MAP, /\n {2}try \{ tokens = Lexer\.lex\(N\); literalizeUnclosedTags\(tokens\); \} catch \(e\) \{ lexError = /, "the rule right after the lex, before anything reads the tokens");
  assert.match(MAP, /^const VOID_TAGS = VOID_ELEMENTS;/m, "one void list, the module's");
  assert.equal((MAP.match(/literalizeUnclosedTags\(/g) || []).length, 1, "one call in the map");
  assert.ok(!CONFIG.includes("md-literal-tags") && !CONFIG.includes("literalize"), "md-config.ts registers nothing for the rule: the singleton's grammar is the chat's too");
  assert.ok(!RENDER.includes("md-literal-tags") && !CHAT.includes("md-literal-tags"), "the chat's modules never import the rule");
  assert.match(RENDER, /\nfunction md\(src: string, repo: string \| null = prRepoFor\(\)\): string \{\n(?:[^\n]*\n){0,12}?[^\n]*const dirty = marked\.parse\(src\) as string;\n/, "md() still parses with marked.parse");
  assert.deepEqual(MOD.match(/^import .*$/gm), ['import type { Token, Tokens } from "marked";'], "the module imports marked's types alone: no marked.use, no renderer hook, nothing on the singleton");
});
