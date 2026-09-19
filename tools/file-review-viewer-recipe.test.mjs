// The viewer's markdown parse lives in product code, and the test suites that stand a Rendered body in for the viewer's render
// through it. file-view.ts exports `viewerHtml`: marked.parse's three steps called one by one over a copy of the singleton's
// defaults (its lexer, the caller's per-call walk, its parser), with the literal-tags rule (md-literal-tags.ts
// literalizeUnclosedTags) between the lexer and the walk, and mdBlock parses through it with the walk it ran before (the code
// tokens for Copy, the file kind's link hook, the defaults' walk, in that order). Before (the review of the slice's PR, round 1,
// 2026-09-19, regression-3): thirteen test modules under ui/webview held a copy of those steps (one inside a browser probe's
// bundled source), three of them with the wikilink stamp as a walk the others lacked, and twenty-six more parsed their stand-in's
// HTML with marked.parse alone (twenty node stand-ins filled through the shim's parseHTML, one oracle and one fence walk that
// handed marked.parse a walkTokens, one browser stamp, three browser probes' pages; and three more, in two file-comments
// modules, filled a fileview-md div through the shim's innerHTML setter, a spelling that count's grep missed, converted in
// the same review's round 2), which since the rule renders
// a block holding an inline start tag with no end tag as the viewer does not (`We recommend <b>shipping the cache.` is
// `<p>We recommend <b>shipping the cache.</b></p>` and a line feed from marked.parse, `<p>We recommend &lt;b&gt;shipping the cache.</p>`
// and a line feed from the viewer), so a fixture of that shape could pass green over a DOM the viewer cannot build. This module holds the recipe to
// file-view.ts and every ui/webview test module to the recipe by grep, so a later stand-in cannot drift back: none calls
// marked's parser itself (`marked.parser(`, the tail of any copy of the steps); no module holding a node stand-in (a
// `parseHTML(` shim, or an `innerHTML` setter over it) has a `marked.parse(` line but an assert's, the output compared and not
// filled, or one of two named lines: the contrast anchor-map-cells-formulas.test.ts draws with the tree the viewer built before
// the rule, and md-config-footnote-paint.test.ts's HTML-string oracle; so a stand-in filled from marked.parse in one statement
// or two goes red; and every module that calls `viewerHtml(` imports it from file-view.ts. Source reads only, no marked (the
// CI shell job runs no npm ci), so this module runs wherever node does. Run: node --test tools/file-review-viewer-recipe.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');
const WEB = ['ui', 'webview'];
const testModules = () => fs.readdirSync(path.join(REPO, ...WEB)).filter((f) => f.endsWith('.test.ts')).sort();

const SIG = 'export function viewerHtml(text: string, walk?: (token: Token) => void): string {';
const RECIPE = [
  '  const opts = { ...marked.defaults };',
  '  const tokens = marked.lexer(text, opts);',
  '  literalizeUnclosedTags(tokens);',
  '  if (walk) marked.walkTokens(tokens, walk);',
  '  return marked.parser(tokens, opts);',
].join('\n');
const WALK = [
  '  const dirty = viewerHtml(text, (t) => {',
  '    if (t.type === "code") { const c = t as Tokens.Code; fences.push({ text: c.text, indented: c.codeBlockStyle === "indented" }); }',
  '    if (doc && doc.kind === "file") viewerWalkTokens(t);',
  '    if (base) void base.call(marked, t);',
  '  });',
].join('\n');

test('file-view.ts exports viewerHtml, the five statements in order and nothing else, and mdBlock parses through it with the walk it ran before, holding no step of its own', () => {
  const view = read(...WEB, 'file-view.ts');
  assert.ok(view.includes(SIG), 'the export');
  assert.equal(view.split(SIG)[1].split('\n}\n')[0], '\n' + RECIPE, 'the recipe body: the defaults copied, the lexer, the rule, the caller\'s walk when given, the parser');
  const mdBlock = view.split('function mdBlock(text: string, doc?: MdDocLoc): HTMLElement {')[1].split('\n}\n')[0];
  assert.ok(mdBlock.includes('\n  const base = marked.defaults.walkTokens;\n'), 'the defaults\' walk is read first');
  assert.ok(mdBlock.includes('\n' + WALK + '\n'), 'mdBlock\'s dirty HTML is the recipe\'s, its walk handed over: the fences, the file kind\'s link hook, the defaults\' walk');
  assert.ok(mdBlock.indexOf('const base = marked.defaults.walkTokens;') < mdBlock.indexOf(WALK), 'the base is read before the parse that runs it');
  for (const s of ['marked.parse(', 'marked.lexer(', 'marked.parser(', 'marked.walkTokens(', 'literalizeUnclosedTags(']) assert.ok(!mdBlock.includes(s), `mdBlock holds no ${s} of its own`);
  assert.equal((view.match(/literalizeUnclosedTags\(/g) || []).length, 1, 'one call in the viewer, the recipe\'s');
  assert.ok(view.includes('\n  box.replaceChildren(...Array.from(sanitizeMd(dirty, mintHeadingIds).childNodes));\n'), 'the sanitizer stays mdBlock\'s own step after the recipe');
  assert.ok(view.includes('import { marked, type Token, type Tokens } from "marked";'), 'the walk\'s parameter type comes from marked');
});

test('no ui/webview test module holds a copy of the recipe, none that holds a node stand-in parses with marked.parse but as an assert\'s oracle or at two named lines, and every one that calls viewerHtml imports it from file-view.ts', () => {
  // marked.parse in a module that holds a node stand-in, at the lines named here and nowhere else (an assert's own line is an
  // oracle compared, not a fill, and passes on its own): the contrast anchor-map-cells-formulas.test.ts draws with the tree the
  // viewer built before the rule, and an HTML-string oracle md-config-footnote-paint.test.ts assigns for the next line's assert
  const NAMED = {
    'anchor-map-cells-formulas.test.ts': ['  for (const n of parseHTML(doc, marked.parse(text) as string)) box.appendChild(n);'],
    'md-config-footnote-paint.test.ts': ['  const html = marked.parse(doc("x[^1]\\n\\n[^1]: **a** *b*")) as string;'],
  };
  for (const [f, lines] of Object.entries(NAMED)) for (const l of lines) assert.ok(read(...WEB, f).includes(l), `${f}: the named line is still there`);
  const parserCalls = [], bare = [], unimported = [], callers = [];
  for (const f of testModules()) {
    const src = read(...WEB, f);
    if (src.includes('marked.parser(') || src.includes('Parser.parse(')) parserCalls.push(f);
    if (/^function parseHTML\(/m.test(src) || src.includes('set innerHTML(')) {
      src.split('\n').forEach((line, i) => {
        if (!line.includes('marked.parse(') || line.trim().startsWith('//')) return;
        if (/\bassert\./.test(line)) return;
        if ((NAMED[f] || []).includes(line)) return;
        bare.push(`${f}:${i + 1}`);
      });
    }
    if (f === 'anchor-map-cells-formulas.test.ts') assert.ok(src.includes('function buildParsedAlone(text: string): FakeElement {'), `${f}: the contrast is the named builder`);
    if (/\bviewerHtml\((?!text: string, walk)/.test(src)) {   // a call, not a source pin quoting the export's signature
      callers.push(f);
      if (!/from "\.\/file-view"/.test(src)) unimported.push(f);
    }
  }
  assert.deepEqual(parserCalls, [], 'no test module calls marked\'s parser itself: the recipe is file-view.ts viewerHtml');
  assert.deepEqual(bare, [], 'no node stand-in parses with marked.parse, in one statement or two: it renders through viewerHtml');
  assert.deepEqual(unimported, [], 'every module that calls viewerHtml imports it from file-view.ts (a browser probe in its bundled source)');
  assert.ok(callers.length >= 36, 'the recipe reaches the suites: ' + callers.length);
  for (const f of ['anchor-map.test.ts', 'anchor-map-cells.test.ts', 'anchor-map-literal-tags.test.ts', 'anchor-map-boundary-points.test.ts', 'anchor-map-pairing-r6.test.ts', 'md-config-paint-trim.test.ts', 'file-view-place.test.ts', 'md-literal-tags.test.ts', 'anchor-map-html-text-browser.test.ts']) assert.ok(callers.includes(f), `${f} renders through the recipe`);
});

test('the stand-ins that stamp wikilinks hand the recipe the file kind\'s stamp as the walk, as marked.parse ran it for them before', () => {
  for (const f of ['anchor-map-wrappers.test.ts', 'anchor-map-obsidian.test.ts', 'anchor-map-fallback-markup.test.ts', 'anchor-map-pairing-r6.test.ts']) {
    const src = read(...WEB, f);
    assert.ok(src.includes('viewerHtml(text, (t) => { resolveWikilink(t); })'), `${f}: the stamp rides as the per-call walk`);
    assert.ok(!src.includes('marked.walkTokens('), `${f}: no walk of its own over the tokens`);
  }
});

test('this module carries no em dash', () => {
  assert.ok(!read('tools', 'file-review-viewer-recipe.test.mjs').includes(String.fromCharCode(0x2014)));
});
