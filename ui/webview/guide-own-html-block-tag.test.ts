// The guide's account of where the literal-tag rule stops, held to the viewer's own lexer (docs/guide.md, the paragraph on a
// file's own HTML; plans/file-review.md, decision 52). The rule (md-literal-tags.ts literalizeUnclosedTags) converts an inline
// start tag with no end tag in its block to its own characters, and the guide says where that ends: a tag first on its line, a
// list marker or a `>` before it allowed, whose name is on CommonMark's HTML-block list, or any tag alone on a line where a
// paragraph would begin, is a block `html` token, which owns no inline run, so the rule leaves it as lexed and the raw tag reaches
// the browser; a tag that opens a heading or a table cell is not first on its line and stays the rule's input. The guide also
// names the tags that take the rest of the file with them when they stay HTML (`<title>`, `<script>`, `<style>`, `<iframe>`;
// `<textarea>` shows it as characters, the file's text first on its line, the viewer's HTML mid-sentence): first on its line each
// is a block html token, and written with the slash mid-sentence each
// is an inline html token the rule leaves html (isSelfClosingTag). The lexer legs here hold those clauses through the viewer's own
// configuration (md-config.ts applyMdConfig, then mdBlock's lex and placeTokens' lex as file-review-plan-inlinetag-rawblock.test.ts
// runs them), each placement lexed both ways and the rule run over the tokens after.
// Why this module beside tools/guide-own-html-block-tag.test.mjs, which holds the same clauses to the guide's text and to marked's
// bare Lexer under vscode-extension/node_modules: that module skips its lexer legs when marked is not installed there, and CI's
// shell job, the one runner of tools/*.test.mjs, runs no npm ci, so those legs skipped in every CI run (the whole review's first
// round found it, 2026-09-19). This file is built and run by the extension job's `npm test` (esbuild.js's test build takes every
// .test.ts under ui/webview), so a marked release, or an extension of the viewer's own configuration, that moves a placement
// between block and prose goes red in CI here. The guide's sentences themselves are pinned in CI twice already (the tools
// module's first leg, which needs no marked, and tests/test_guide_files_own_html_foreign_tag.py) and not a third time here.
// Synthetic text only.
import { test } from "node:test";
import assert from "node:assert/strict";
import { marked, Lexer, type Token, type Tokens } from "marked";
import { applyMdConfig } from "./md-config";
import { literalizeUnclosedTags } from "./md-literal-tags";
import { viewerHtml } from "./file-view";   // the viewer's HTML: mdBlock's recipe (its lexer, the rule, the per-call walk, its parser), exported

applyMdConfig();

type Lex = (src: string) => Token[];
/** mdBlock's lex (file-view.ts): marked.lexer over a copy of the singleton's defaults, before the rule. */
const viewerLex: Lex = (src) => marked.lexer(src, { ...marked.defaults });
/** placeTokens' lex (anchor-map.ts): the static Lexer.lex over the module defaults, before the rule. */
const mapLex: Lex = (src) => Lexer.lex(src);
const LEXES: Array<[string, Lex]> = [["mdBlock's lex", viewerLex], ["placeTokens' lex", mapLex]];
/** The block token types, the blank-line `space` tokens left out. */
const types = (tokens: Token[]): string[] => tokens.filter((t) => t.type !== "space").map((t) => t.type);
const run = (block: Token): Token[] => (block as { tokens?: Token[] }).tokens ?? [];
/** A block's inline html tokens, by raw. */
const inlineHtml = (block: Token): string[] => run(block).filter((t) => t.type === "html").map((t) => t.raw);
/** A block's inline run as `type:raw` strings. */
const shape = (block: Token): string[] => run(block).map((t) => `${t.type}:${t.raw}`);

test("a placeholder typed mid-sentence is an inline html token of its paragraph under both lexes, the rule's input; the rule makes it a text token and the viewer writes its characters", () => {
  for (const [name, lex] of LEXES) {
    const tokens = lex("See (<table>__widths.csv) here.\n");
    assert.deepEqual(types(tokens), ["paragraph"], name);
    assert.deepEqual(inlineHtml(tokens[0]), ["<table>"], `${name}: the tag is an inline token inside the paragraph`);
    literalizeUnclosedTags(tokens);
    assert.deepEqual(shape(tokens[0]), ["text:See (", "text:<table>", "text:__widths.csv) here."], `${name}: after the rule the tag is a text token, its raw kept`);
    assert.equal((run(tokens[0])[1] as Tokens.Text).text, "&lt;table&gt;", `${name}: its text is the raw escaped`);
  }
  assert.equal(viewerHtml("See (<table>__widths.csv) here.\n"), "<p>See (&lt;table&gt;__widths.csv) here.</p>\n");
});

test("the same placeholder first on its line is a block html token under both lexes wherever the line stands (the document's start, indented up to three spaces, a paragraph's second line, a list item, a quote), which the rule leaves as lexed and the viewer writes raw", () => {
  for (const [name, lex] of LEXES) {
    const first = lex("<table>__widths.csv) is the file.\n\n## Next\n\nAfter.\n");
    assert.equal(first[0].type, "html", `${name}: at the document's start`);
    assert.ok(first[0].raw.startsWith("<table>"), name);
    assert.deepEqual(types(first), ["html", "heading", "paragraph"], `${name}: the blocks after it are their own tokens`);
    const raw = first[0].raw;
    literalizeUnclosedTags(first);
    assert.equal(`${first[0].type}:${first[0].raw}`, `html:${raw}`, `${name}: the rule leaves the block html token as lexed`);
    assert.equal(lex("   <table>x) is the file.\n")[0].type, "html", `${name}: indented three spaces`);
    assert.deepEqual(types(lex("Intro text\n<table>x) is the file.\n")), ["paragraph", "html"], `${name}: a paragraph's second line, the html block interrupting the paragraph`);
    const item = lex("- <table>x) item\n- second\n");
    assert.equal(item[0].type, "list", name);
    assert.equal((item[0] as Tokens.List).items[0].tokens[0].type, "html", `${name}: after a list marker`);
    const quote = lex("> <table>x) quoted\n");
    assert.equal(quote[0].type, "blockquote", name);
    assert.equal((quote[0] as Tokens.Blockquote).tokens[0].type, "html", `${name}: after a \`>\``);
  }
  assert.ok(viewerHtml("<table>__widths.csv) is the file.\n\n## Next\n").startsWith("<table>__widths.csv) is the file.\n"), "the viewer writes the block's raw tag");
});

test("the names: `<table>`, `<div>`, `<p>` and `<pre>` first on a line open a block under both lexes; `<span>`, `<b>` and an invented name first on a line are prose with an inline tag, which the rule converts", () => {
  for (const [name, lex] of LEXES) {
    for (const tag of ["table", "div", "p", "pre"]) assert.equal(lex(`<${tag}>x rest\n`)[0].type, "html", `${name}: <${tag}> first on its line is a block`);
    for (const tag of ["span", "b", "cell"]) {
      const tokens = lex(`<${tag}>x rest\n`);
      assert.deepEqual(types(tokens), ["paragraph"], `${name}: <${tag}> first on its line is prose`);
      assert.deepEqual(inlineHtml(tokens[0]), [`<${tag}>`], `${name}: with the tag an inline token`);
      literalizeUnclosedTags(tokens);
      assert.deepEqual(shape(tokens[0]), [`text:<${tag}>`, "text:x rest"], `${name}: which the rule converts`);
    }
  }
});

test("a tag alone on a line where a paragraph would begin is a block under both lexes; alone on a line inside a paragraph it is prose, which the rule converts", () => {
  for (const [name, lex] of LEXES) {
    assert.equal(lex("<b>\nrest\n")[0].type, "html", `${name}: at the document's start`);
    assert.deepEqual(types(lex("Intro\n\n<b>\nrest\n")), ["paragraph", "html"], `${name}: after a blank line`);
    const inside = lex("Intro\n<b>\nrest\n");
    assert.deepEqual(types(inside), ["paragraph"], `${name}: inside a paragraph the line is prose`);
    assert.deepEqual(inlineHtml(inside[0]), ["<b>"], name);
    literalizeUnclosedTags(inside);
    assert.deepEqual(shape(inside[0]), ["text:Intro\n", "text:<b>", "text:\nrest"], `${name}: which the rule converts`);
  }
});

test("a tag that opens a heading or a table cell is not first on its line: an inline token under both lexes, the rule's input, which the rule converts", () => {
  for (const [name, lex] of LEXES) {
    const heading = lex("# <table>x heading\n");
    assert.equal(heading[0].type, "heading", name);
    assert.deepEqual(inlineHtml(heading[0]), ["<table>"], name);
    literalizeUnclosedTags(heading);
    assert.deepEqual(shape(heading[0]), ["text:<table>", "text:x heading"], `${name}: the heading's tag converted`);
    const table = lex("| a | b |\n|---|---|\n| <table>x | y |\n");
    assert.equal(table[0].type, "table", name);
    const cell = (table[0] as Tokens.Table).rows[0][0];
    assert.deepEqual(cell.tokens.filter((t) => t.type === "html").map((t) => t.raw), ["<table>"], name);
    literalizeUnclosedTags(table);
    assert.deepEqual(cell.tokens.map((t) => `${t.type}:${t.raw}`), ["text:<table>", "text:x"], `${name}: the cell's tag converted`);
  }
});

test("the names the guide says take the rest of the file when they stay HTML: first on its line each is a block html token the rule leaves as lexed (`<title>` and `<iframe>` to the next blank line; `<script>`, `<style>` and `<textarea>` to the document's end), and written with the slash mid-sentence each is an inline html token the rule leaves html, where the bare spelling becomes text", () => {
  const DOC = (tag: string): string => `Intro T0.\n\n<${tag}> note T1\n\n## After heading\n\nPara after.\n`;
  for (const [name, lex] of LEXES) {
    for (const tag of ["title", "iframe"]) {
      const tokens = lex(DOC(tag));
      assert.deepEqual(types(tokens), ["paragraph", "html", "heading", "paragraph"], `${name}: <${tag}> first on its line is a block that ends at the blank line`);
      const block = tokens.find((t) => t.type === "html") as Token;
      assert.equal(block.raw, `<${tag}> note T1\n\n`, name);
      literalizeUnclosedTags(tokens);
      assert.equal(`${block.type}:${block.raw}`, `html:<${tag}> note T1\n\n`, `${name}: left as lexed`);
    }
    for (const tag of ["script", "style", "textarea"]) {
      const tokens = lex(DOC(tag));
      assert.deepEqual(types(tokens), ["paragraph", "html"], `${name}: <${tag}> first on its line is a block that runs to the document's end`);
      const block = tokens.find((t) => t.type === "html") as Token;
      assert.equal(block.raw, `<${tag}> note T1\n\n## After heading\n\nPara after.\n`, name);
      literalizeUnclosedTags(tokens);
      assert.equal(block.type, "html", `${name}: left as lexed`);
    }
    for (const tag of ["title", "script", "style", "iframe", "textarea"]) {
      const slashed = lex(`Intro <${tag}/> tail T1.\n`);
      assert.deepEqual(types(slashed), ["paragraph"], `${name}: <${tag}/> mid-sentence is prose`);
      literalizeUnclosedTags(slashed);
      assert.deepEqual(shape(slashed[0]), ["text:Intro ", `html:<${tag}/>`, "text: tail T1."], `${name}: the slashed tag stays an html token after the rule`);
      const bare = lex(`Intro <${tag}> tail T1.\n`);
      literalizeUnclosedTags(bare);
      assert.deepEqual(shape(bare[0]), ["text:Intro ", `text:<${tag}>`, "text: tail T1."], `${name}: the bare spelling becomes text`);
    }
  }
  assert.ok(viewerHtml("Intro <title/> tail T1.\n").startsWith("<p>Intro <title/> tail T1.</p>"), "the viewer writes the slashed tag raw");
  assert.ok(viewerHtml("Intro <title> tail T1.\n").startsWith("<p>Intro &lt;title&gt; tail T1.</p>"), "and the bare one as characters");
});
