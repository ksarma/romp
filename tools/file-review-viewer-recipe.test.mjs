// The viewer's markdown parse lives in product code, and the test suites that stand a Rendered body in for the viewer's render
// through it. file-view.ts exports `viewerHtml`: marked.parse's three steps called one by one over a copy of the singleton's
// defaults (its lexer, the caller's per-call walk, its parser), with the literal-tags rule (md-literal-tags.ts
// literalizeUnclosedTags) between the lexer and the walk, and mdBlock parses through it with the walk it ran before (the code
// tokens for Copy, the file kind's link hook, the defaults' walk, in that order). Before (the review of the slice's PR, round 1,
// 2026-09-19, regression-3): thirteen test modules under ui/webview held a copy of those steps (one inside a browser probe's
// bundled source), three of them with the wikilink stamp as a walk the others lacked, and twenty-six more parsed their stand-in's
// HTML with marked.parse alone (twenty node stand-ins filled through the shim's parseHTML, one oracle and one fence walk that
// handed marked.parse a walkTokens, one browser stamp, three browser probes' pages), which since the rule renders
// a block holding an inline start tag with no end tag as the viewer does not (`We recommend <b>shipping the cache.` is
// `<p>We recommend <b>shipping the cache.</b></p>` and a line feed from marked.parse, `<p>We recommend &lt;b&gt;shipping the cache.</p>`
// and a line feed from the viewer), so a fixture of that shape could pass green over a DOM the viewer cannot build. This module holds the recipe to
// file-view.ts and every ui/webview test module to the recipe by grep, so a later stand-in cannot drift back: none calls
// marked's parser itself (`marked.parser(`, the tail of any copy of the steps), none fills a node stand-in from `marked.parse(`
// through the shim's `parseHTML(` but the one contrast anchor-map-cells-formulas.test.ts draws with the tree the viewer built
// before the rule, and every module that calls `viewerHtml(` imports it from file-view.ts. Source reads only, no marked (the
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

test('no ui/webview test module holds a copy of the recipe or fills its Rendered stand-in from marked.parse alone, and every one that calls viewerHtml imports it from file-view.ts', () => {
  // the one node stand-in built from marked.parse on purpose: the tree the viewer built before the rule, drawn as the contrast
  // in one test of that suite, named here so a second one cannot land unread
  const ALONE_ON_PURPOSE = { 'anchor-map-cells-formulas.test.ts': 'function buildParsedAlone(text: string): FakeElement {' };
  const parserCalls = [], bare = [], unimported = [], callers = [];
  for (const f of testModules()) {
    const src = read(...WEB, f);
    if (src.includes('marked.parser(') || src.includes('Parser.parse(')) parserCalls.push(f);
    const fills = src.match(/parseHTML\(\w+, marked\.parse\(/g) || [];
    if (f in ALONE_ON_PURPOSE) {
      assert.equal(fills.length, 1, `${f}: the one contrast fill, no other`);
      assert.ok(src.includes(ALONE_ON_PURPOSE[f]), `${f}: the contrast is the named builder`);
    } else if (fills.length) bare.push(f);
    if (/\bviewerHtml\((?!text: string, walk)/.test(src)) {   // a call, not a source pin quoting the export's signature
      callers.push(f);
      if (!/from "\.\/file-view"/.test(src)) unimported.push(f);
    }
  }
  assert.deepEqual(parserCalls, [], 'no test module calls marked\'s parser itself: the recipe is file-view.ts viewerHtml');
  assert.deepEqual(bare, [], 'no node stand-in is filled from marked.parse alone: it renders through viewerHtml');
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
