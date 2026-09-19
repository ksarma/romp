// Where the guide says the literal-tag rule stops: a tag markdown reads as an HTML block (docs/guide.md, the paragraph on a
// file's own HTML; plans/file-review.md, decision 52). The rule of decision 52 converts an inline start tag with no end tag in
// its block to its own characters (md-literal-tags.ts, literalizeUnclosedTags), and the guide first stated it without a
// limit: a placeholder typed as `<table>` "is shown as the characters typed", named for a paragraph and a list item among
// the blocks. marked's block html rule (CommonMark's HTML-block conditions 1, 6 and 7) lexes a tag FIRST on its line, a
// list marker or a `>` before it allowed, as a block `html` token when its name is on the rule's list (`table`, `div`, `p`,
// `pre` and the rest; `span`, `b` and an invented name are not), and any tag alone on a line where a paragraph would begin
// likewise; a block html token owns no inline run, so literalizeUnclosedTags leaves it as lexed, the raw tag reaches the
// browser, and the anchor map refuses the block as an HTML block, so a comment on it goes through the Raw view. The slice's
// review found the guide overstating the rule for that placement (round 2); the guide now says where the rule stops, and,
// since the whole review's first round, which tags take the rest of the file with them when they stay HTML: `<title>`,
// `<script>`, `<style>` and `<iframe>` written with the slash (the rule leaves the self-closing syntax HTML) or first on the
// line, while `<textarea>` so placed shows the rest as characters (the file's text first on its line, the viewer's HTML
// mid-sentence). This module holds each clause of the account to the
// installed marked (vscode-extension/node_modules, the copy the viewer bundles), by lexing synthetic documents, and to the two
// code paths the account rests on. The lexer legs skip where marked is not installed, which is every CI run of tools/*.test.mjs
// (the shell job runs no npm ci); ui/webview/guide-own-html-block-tag.test.ts runs the same legs through the viewer's own
// configuration under the extension job's npm test, so CI holds them there. The sentences are pinned flattened, so a rewrap
// survives. Synthetic text only. Run: node --test tools/guide-own-html-block-tag.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const MARKED = path.join(REPO, 'vscode-extension', 'node_modules', 'marked', 'lib', 'marked.esm.js');
const SKIP = fs.existsSync(MARKED)
  ? false
  : 'marked is not installed under vscode-extension/node_modules (run `npm ci` in vscode-extension); the lexer legs did not run';
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');
const flat = (s) => s.replace(/\s+/g, ' ').trim();
/** A TypeScript module with its `//` lines and `/* *\/` blocks removed, so a pin reads the code and not its comments. */
const codeOnly = (ts) => ts.replace(/\/\*[\s\S]*?\*\//g, '').split('\n').filter((l) => !l.trimStart().startsWith('//')).join('\n');

// ── the guide's account, sentence by sentence ────────────────────────

const RULE = 'A tag opened in a line of prose and not closed in the same paragraph, heading, list item or table cell (a placeholder typed mid-sentence as `<table>`, say) is shown as the characters typed, not read as HTML, and can be commented on like any passage; a tag closed in the same block, a tag that never takes an end tag such as `<br>` or `<img>`, and a tag written with a slash before its `>` (`<x/>`) are HTML as before.';
const BLOCK = 'A tag the viewer reads as an HTML block rather than as prose is HTML as before too: a tag first on its line, after a list marker or a `>` included, whose name is on CommonMark\'s HTML-block list (`<table>`, `<div>`, `<p>` and `<pre>` are on it; `<span>`, `<b>` and an invented name are not), or a tag alone on a line where a paragraph would begin.';
const PLACEHOLDER = 'The same placeholder typed first on its line is therefore read as HTML: the browser shows no `<table>`, and a comment on the passage goes through the Raw view.';
const CHAT = 'A chat message is not read this way.';
const LOSS = 'A `<title>`, `<script>`, `<style>` or `<iframe>` that stays HTML takes everything after it out of the Rendered view, up to an end tag of its name, or the end of the file when there is none: a browser reads `<title/>` as `<title>`, so the tag written with the slash mid-sentence does this, and so does the tag first on its line; a `<textarea>` in either place shows that stretch as unformatted characters instead: after the tag first on its line the file\'s own text, and after the tag written with the slash mid-sentence the HTML the viewer built from the rest of its paragraph and the blocks after it, tags such as `</p>` and `<h2>` among the characters.';

function ownHtmlParagraph() {
  const guide = read('docs', 'guide.md');
  const at = guide.indexOf("**A file's own HTML.**");
  assert.ok(at >= 0, 'the guide has the paragraph');
  const end = guide.indexOf('\n\n', at);
  return flat(end < 0 ? guide.slice(at) : guide.slice(at, end));
}

test('the guide states the rule for a tag in prose, then where it stops (an HTML block), then what the placeholder does first on its line, then which tags take the rest of the file when they stay HTML, in that order and once', () => {
  const para = ownHtmlParagraph();
  assert.ok(para.includes(RULE + ' ' + BLOCK + ' ' + PLACEHOLDER + ' ' + CHAT + ' ' + LOSS), 'the five sentences stand together in order');
  assert.equal(para.split('is shown as the characters typed').length - 1, 1, 'the rule is stated once');
  assert.equal(para.split('as an HTML block').length - 1, 1, 'the block limit is stated once');
  assert.equal(para.split('takes everything after it out of the Rendered view').length - 1, 1, 'the loss is stated once');
  assert.ok(para.includes(CHAT + ' ' + LOSS + ' Inside an inline `svg` or `math`'), 'the svg and math qualification follows the loss sentence');
  assert.ok(!para.includes('—'), 'no em dash');
});

// ── the lexer: which placements are a block, which are prose ─────────

const lex = async (src) => {
  const { Lexer } = await import(pathToFileURL(MARKED).href);
  return Lexer.lex(src);
};
const types = (tokens) => tokens.map((t) => t.type);
const inlineHtml = (block) => (block.tokens ?? []).filter((t) => t.type === 'html').map((t) => t.raw);

test('a placeholder typed mid-sentence is an inline html token of its paragraph, the rule\'s input', { skip: SKIP }, async () => {
  const tokens = await lex('See (<table>__widths.csv) here.\n');
  assert.deepEqual(types(tokens), ['paragraph']);
  assert.deepEqual(inlineHtml(tokens[0]), ['<table>'], 'the `<table>` is an inline token inside the paragraph, which literalizeUnclosedTags reads');
});

test('the same placeholder first on its line is a block html token wherever the line stands: the document\'s start, indented up to three spaces, a paragraph\'s second line, a list item, a quote', { skip: SKIP }, async () => {
  const first = await lex('<table>__widths.csv) is the file.\n\n## Next\n\nAfter.\n');
  assert.equal(first[0].type, 'html', 'at the document\'s start');
  assert.ok(first[0].raw.startsWith('<table>'));
  assert.deepEqual(types(first).filter((t) => t !== 'space'), ['html', 'heading', 'paragraph'], 'the blocks after it are their own tokens; the browser, not the lexer, parses them into the table');
  const indented = await lex('   <table>x) is the file.\n');
  assert.equal(indented[0].type, 'html', 'indented three spaces');
  const second = await lex('Intro text\n<table>x) is the file.\n');
  assert.deepEqual(types(second), ['paragraph', 'html'], 'a paragraph\'s second line: the html block interrupts the paragraph');
  const item = await lex('- <table>x) item\n- second\n');
  assert.equal(item[0].type, 'list');
  assert.equal(item[0].items[0].tokens[0].type, 'html', 'after a list marker');
  const quote = await lex('> <table>x) quoted\n');
  assert.equal(quote[0].type, 'blockquote');
  assert.equal(quote[0].tokens[0].type, 'html', 'after a `>`');
});

test('the names: `<table>`, `<div>`, `<p>` and `<pre>` first on a line open a block; `<span>`, `<b>` and an invented name first on a line are prose with an inline tag', { skip: SKIP }, async () => {
  for (const name of ['table', 'div', 'p', 'pre']) {
    const tokens = await lex(`<${name}>x rest\n`);
    assert.equal(tokens[0].type, 'html', `<${name}> first on its line is a block`);
  }
  for (const name of ['span', 'b', 'cell']) {
    const tokens = await lex(`<${name}>x rest\n`);
    assert.deepEqual(types(tokens), ['paragraph'], `<${name}> first on its line is prose`);
    assert.deepEqual(inlineHtml(tokens[0]), [`<${name}>`], `with the tag an inline token, the rule's input`);
  }
});

test('a tag alone on a line where a paragraph would begin is a block; alone on a line inside a paragraph it is prose', { skip: SKIP }, async () => {
  assert.equal((await lex('<b>\nrest\n'))[0].type, 'html', 'at the document\'s start');
  const after = await lex('Intro\n\n<b>\nrest\n');
  assert.deepEqual(types(after).filter((t) => t !== 'space'), ['paragraph', 'html'], 'after a blank line');
  const inside = await lex('Intro\n<b>\nrest\n');
  assert.deepEqual(types(inside), ['paragraph'], 'inside a paragraph the line is prose (the block rule\'s seventh condition cannot interrupt a paragraph)');
  assert.deepEqual(inlineHtml(inside[0]), ['<b>']);
});

test('a tag that opens a heading or a table cell is not first on its line: an inline token, the rule\'s input', { skip: SKIP }, async () => {
  const heading = await lex('# <table>x heading\n');
  assert.equal(heading[0].type, 'heading');
  assert.deepEqual(inlineHtml(heading[0]), ['<table>']);
  const table = await lex('| a | b |\n|---|---|\n| <table>x | y |\n');
  assert.equal(table[0].type, 'table');
  assert.deepEqual(table[0].rows[0][0].tokens.filter((t) => t.type === 'html').map((t) => t.raw), ['<table>']);
});

test('the names the guide says take the rest of the file when they stay HTML: first on its line each is a block html token (`<title>` and `<iframe>` to the next blank line; `<script>`, `<style>` and `<textarea>` to the document\'s end); written with the slash mid-sentence each is an inline html token, which the rule leaves HTML (isSelfClosingTag, whose flag reading md-literal-tags-tag-syntax.test.ts pins by execution; ui/webview/guide-own-html-block-tag.test.ts runs the rule over these five)', { skip: SKIP }, async () => {
  const doc = (name) => `Intro T0.\n\n<${name}> note T1\n\n## After heading\n\nPara after.\n`;
  for (const name of ['title', 'iframe']) {
    const tokens = await lex(doc(name));
    assert.deepEqual(types(tokens).filter((t) => t !== 'space'), ['paragraph', 'html', 'heading', 'paragraph'], `<${name}> first on its line is a block that ends at the blank line`);
    assert.equal(tokens.find((t) => t.type === 'html').raw, `<${name}> note T1\n\n`);
  }
  for (const name of ['script', 'style', 'textarea']) {
    const tokens = await lex(doc(name));
    assert.deepEqual(types(tokens).filter((t) => t !== 'space'), ['paragraph', 'html'], `<${name}> first on its line is a block that runs to the document's end`);
    assert.equal(tokens.find((t) => t.type === 'html').raw, `<${name}> note T1\n\n## After heading\n\nPara after.\n`);
  }
  for (const name of ['title', 'script', 'style', 'iframe', 'textarea']) {
    const tokens = await lex(`Intro <${name}/> tail T1.\n`);
    assert.deepEqual(types(tokens), ['paragraph'], `<${name}/> mid-sentence is prose`);
    assert.deepEqual(inlineHtml(tokens[0]), [`<${name}/>`], `with the slashed tag an inline html token`);
  }
});

// ── the two code paths the account rests on ──────────────────────────

test('literalizeUnclosedTags reads inline runs and children only, so a block html token, which has neither, is left as lexed', () => {
  const code = codeOnly(read('ui', 'webview', 'md-literal-tags.ts'));
  const fn = code.slice(code.indexOf('export function literalizeUnclosedTags('), code.indexOf('function literalizeRun('));
  assert.ok(fn.includes('case "paragraph": case "heading": case "text": case "footnoteDef": {'), 'the blocks whose inline run it reads');
  assert.ok(fn.includes('case "table": {'), 'and a table\'s cells');
  assert.ok(fn.includes('const kids = (t as { tokens?: Token[] }).tokens;'), 'every other token: its children, if any');
  assert.ok(!fn.includes('"html"'), 'no case reads a block html token');
});

test('the anchor map refuses a block html token as an HTML block, so a comment on the passage goes through the Raw view', () => {
  const map = codeOnly(read('ui', 'webview', 'anchor-map.ts'));
  assert.ok(map.includes('case "html": throw new Refusal("an HTML block");'), 'the text walk\'s refusal');
});
