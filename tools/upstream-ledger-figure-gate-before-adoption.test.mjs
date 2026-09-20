// The ledger entry upstream/2026-09-20-figure-gate-before-adoption.md is the queue item the owner reads before promoting the
// gate-before-adoption fix to an upstream offer, and its `where:` line is the offer's inventory. Round 1 of the branch's
// review added a second browser leg and rewrote that line without naming the leg or re-deriving its count, so the line said
// 13 files where the head's diff listed 14, and the body kept saying WebKit alone fetched a gated figure where the new leg
// had measured Firefox doing so too (found by the branch's second review round, 2026-09-20). This module holds the entry to the tree and
// to the legs: every file the branch changed is named in the where: line, by its path or its basename (the entry by the
// ledger's own phrase, "this entry among them"), and exists; the count the line states is the number of files it names;
// both browser legs and the node scene are named in the line and in the body; the body's engine statements match the legs' own headers (the
// img leg red in WebKit alone at the base, the svg leg red in Firefox and in WebKit, green in Chromium); the reach names
// Firefox beside Safari, as the chain block's comment in file-view.ts does; since the fork PR's round-2 push (the branch's fourth
// round), the rule, scoped to mdBlock, the fence scene, the Copy case and the seam test's re-parse pin are named in the line and in
// the body and stand in the files; no em dash. The file list is the branch's diff
// at its head (against its merge base with main), written down: the entry is a record of that branch, so this module reads no git. Named by its subject and
// not by the entry's date: a tools module whose name opens with four digits is read as an ADR's by
// tools/file-review-plan-sidecar-adr-modules.test.mjs, which requires a docs/adr/<NNNN>-*.md behind it (the branch's
// first full sweep, 2026-09-20, was red there on the dated name). Synthetic: the repo's own text only.
// Run: node --test tools/upstream-ledger-figure-gate-before-adoption.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');

const ENTRY = 'upstream/2026-09-20-figure-gate-before-adoption.md';
const IMG_LEG = 'ui/webview/file-view-figures-gate-adopt-browser.test.ts';
const SVG_LEG = 'ui/webview/file-view-figures-gate-adopt-svg-browser.test.ts';
/** The node scene that executes the order where the legs skip (in CI's vscode-extension job no engine is installed before the
 *  npm test step; tools/markdown-viewer-plan-gate-adopt.test.mjs reads that off the job's block). */
const NODE_SCENE = 'ui/webview/file-view-figures-gate-adopt.test.ts';
/** `git diff --name-only origin/main...HEAD` at the branch's head (the branch's own files, from its merge base with main), sorted as git
 *  prints it. Not the two-dot diff from 2d41e5c9b: the branch merged origin/main once, so that diff also counts what main brought in
 *  (22 files at the head before the node scene, where the line said 15; found and corrected by the build of the node scene, 2026-09-20). */
const FILES = [
  'plans/markdown-viewer.md',
  'tools/file-review-viewer-recipe.test.mjs',
  'tools/markdown-viewer-plan-gate-adopt.test.mjs',
  'tools/upstream-ledger-figure-gate-before-adoption.test.mjs',
  IMG_LEG,
  SVG_LEG,
  NODE_SCENE,
  'ui/webview/file-view-figures-gate-browser.test.ts',
  'ui/webview/file-view-seam.test.ts',
  'ui/webview/file-view-text-size.test.ts',
  'ui/webview/file-view.test.ts',
  'ui/webview/file-view.ts',
  'ui/webview/md-sanitize-viewer-links.test.ts',
  'ui/webview/md-url-view.test.ts',
  'ui/webview/render-sanitize.test.ts',
  ENTRY,
];

const entry = read(ENTRY);
/** The front matter's pairs (one line each, `key: value`) and the prose after the closing delimiter. */
function parse(text) {
  const lines = text.split('\n');
  assert.equal(lines[0], '---', 'the entry opens with the front matter delimiter');
  const end = lines.indexOf('---', 1);
  assert.ok(end > 1, 'the front matter closes');
  const header = {};
  for (const line of lines.slice(1, end)) {
    const m = /^([a-z]+):(.*)$/.exec(line);
    assert.ok(m, `a header line is one key: value pair, not ${JSON.stringify(line)}`);
    header[m[1]] = m[2].trim();
  }
  return { header, body: lines.slice(end + 1).join('\n') };
}
const { header, body } = parse(entry);
const where = header.where;

test('the where: line names every file the branch changed, each of which exists in the tree', () => {
  assert.ok(where && where.length > 0, 'where: is present and non-blank');
  // the entry covers itself with the ledger's own phrase, "this entry among them", as the earlier entries do
  const covered = (f) => where.includes(f) || where.includes(path.basename(f)) || (f === ENTRY && where.includes('this entry among them'));
  const unnamed = FILES.filter((f) => !covered(f));
  assert.deepEqual(unnamed, [], 'every changed file is named by its path or its basename');
  const missing = FILES.filter((f) => !fs.existsSync(path.join(REPO, f)));
  assert.deepEqual(missing, [], 'every named file exists');
  assert.equal(new Set(FILES.map((f) => path.basename(f))).size, FILES.length, 'basenames are unique, so a basename names one file');
});

test('the count the where: line states is the number of files it names, derived at the head', () => {
  const m = /(\d+) files by `git diff --name-only origin\/main\.\.\.HEAD` at the head/.exec(where);
  assert.ok(m, 'the line states its count and the command it was derived from, at the head');
  assert.equal(Number(m[1]), FILES.length, 'the stated count is the list\'s length');
  assert.ok(where.includes('this entry among them'), 'the entry counts itself');
});

test('both browser legs are named in the where: line and in the body, the svg leg as the second vector', () => {
  for (const leg of [IMG_LEG, SVG_LEG]) {
    assert.ok(where.includes(leg), `where: names ${leg} by its path`);
    assert.ok(body.includes(path.basename(leg)), `the body names ${path.basename(leg)}`);
  }
  assert.ok(where.includes('two new browser legs'), 'the line counts the legs');
  assert.ok(where.includes('three scenes'), 'the img leg is described with its three scenes');
  assert.ok(where.includes('two inline svg images, one spelt href and one xlink:href'), 'the svg leg is described by its two spellings');
});

test('the node scene is named in the where: line and in the body, is a node test (no browser in its name, no Playwright), and both legs\' skip text names it as the guard that runs where they skip', () => {
  assert.ok(where.includes(NODE_SCENE), `where: names ${NODE_SCENE} by its path`);
  assert.ok(where.includes('one node scene'), 'the line counts the scene');
  assert.ok(body.includes(path.basename(NODE_SCENE)), 'the body names the scene');
  assert.ok(body.includes('red on the base\'s order and on three other mutations in scratch copies of the head, green at the head'), 'the body records the mutation runs');
  assert.ok(!path.basename(NODE_SCENE).includes('browser'), 'a node test: no browser in its name, so npm test runs it under node');
  const scene = read(NODE_SCENE);
  assert.ok(!/(?:require\w*\(|from )["']playwright/.test(scene), 'the scene reaches no browser: no import or require of playwright (its comments may name the legs\' engines)');
  assert.ok(scene.includes('hideEdges(this)'), 'its stand-in is on the shim rule (ui/test-dom-shim.test.ts)');
  for (const leg of [IMG_LEG, SVG_LEG]) {
    const src = read(leg);
    assert.ok(src.includes('t.skip("playwright is not installed under vscode-extension; the browser legs need it (CI installs no browsers before npm test); file-view-figures-gate-adopt.test.ts, the node scene, is the guard that runs where this leg skips")'), `${leg}'s skip names the scene`);
    assert.ok(src.split('\nimport ')[0].includes('file-view-figures-gate-adopt.test.ts executes the'), `${leg}'s header names the scene`);
  }
});

test("the body's engine statements are the legs' own: the img leg red in WebKit alone at the base, the svg leg red in Firefox and WebKit, green in Chromium", () => {
  const imgHeader = read(IMG_LEG).split('\nimport ')[0];
  const svgHeader = read(SVG_LEG).split('\nimport ')[0];
  assert.ok(imgHeader.includes('Red before the fix in WebKit alone, all three scenes'), "the img leg's header: WebKit alone, three scenes");
  assert.ok(body.includes('red in WebKit at 2d41e5c9b in all three scenes, green in Chromium and Firefox there'), 'the body says so of the img leg');
  assert.ok(svgHeader.includes('red in Firefox') && svgHeader.includes('red in WebKit') && svgHeader.includes('green in Chromium'), "the svg leg's header: Firefox and WebKit red, Chromium green");
  assert.ok(body.includes('red in Firefox (both requested while the placeholders stood) and in WebKit (the xlink:href one) at 2d41e5c9b, green in Chromium there'), 'the body says so of the svg leg');
  assert.ok(body.includes('(the second leg\'s 3000-paragraph note, both spellings, 3 of 3 runs; shorter notes in some runs or none; the counts are under "Run counts, the svg vectors" in the plan section)'), 'the Firefox svg statement carries its run counts and points at the plan\'s Run counts paragraph');
  assert.ok(body.includes('Both legs green in all three engines after the fix.'), 'the body records the fixed state for both legs');
  assert.ok(!body.includes('so neither leaked'), 'the pre-round-1 sentence that Chromium and Firefox did not leak is gone');
});

test('the fork PR\'s round-2 push: the where: line and the body state the rule over mdBlock, name the fence scene and the Copy case of the img leg and the seam test\'s re-parse pin, and the leg holds those two tests', () => {
  assert.ok(where.includes('the fence pass, the one pass that re-parses markup, then resolveFigureRefs, rewriteFigureSrcs and gateRemoteFigures, all on the sanitized body'), 'where: names the fence pass first in the order');
  assert.ok(where.includes('the chain block\'s comment states the rule, every pass of mdBlock that sets, repoints, moves or creates a fetching element runs before the adoption'), 'where: states the rule with its domain, mdBlock');
  assert.ok(where.includes('a fourth scene, the fence pass\'s re-parse of raw multi-line fences holding an svg image with src or srcset, red in all three engines with the pass after the adoption; and a fifth case, the Copy button clicked for real after the move'), 'where: names the fence scene and the Copy case');
  assert.ok(where.includes('which since the fork PR\'s round-2 push reads comment-stripped code, pins the fence pass\'s place and derives and pins the post-adoption re-parse population'), 'where: names the seam test\'s round-2 pins');
  assert.ok(body.includes('the rule it keeps is that every pass of mdBlock that sets, repoints, moves or creates a fetching element runs before the adoption'), 'the body states the rule with its domain');
  assert.ok(body.includes('The fork PR\'s review (its round-2 push, the branch\'s fourth round, 2026-09-20) found and closed the one pass that creates one'), 'the body names the review series once, as the plan does');
  assert.ok(body.includes('an HTML img the chain had never judged, which fetched from the unlisted host in Chromium, Firefox and WebKit with no click, on main and at this fix as filed; the fence pass now runs before the chain, over the same inert body, so the chain judges what the re-parse creates'), 'the body records the fence hole, its engines, its standing on main and the move');
  const leg = read(IMG_LEG);
  assert.ok(leg.includes('raw multi-line fences holding an svg image with a src, a gated one with a src beside its href, and one with a srcset'), 'the img leg holds the fence scene');
  assert.ok(leg.includes('the Copy button, created in the live document and appended into the sanitizer\'s body before the adoption, answers a real click on each fence after it'), 'and the Copy case');
  assert.ok(leg.includes('await buttons.nth(k).click();'), 'the Copy case clicks through the engine');
  const view = read('ui', 'webview', 'file-view.ts');
  assert.ok(view.indexOf('clean.querySelectorAll("pre code")') > 0 && view.indexOf('clean.querySelectorAll("pre code")') < view.indexOf('resolveFigureRefs(clean, doc.href);'), 'the fence pass over the sanitized body sits before the chain in file-view.ts');
  const seam = read('ui', 'webview', 'file-view-seam.test.ts');
  assert.ok(seam.includes('test("no re-parse after the adoption:'), 'the seam test holds the re-parse population pin');
});

test('the reach names Firefox beside Safari, as the chain block\'s comment in file-view.ts does, and the title names no one engine', () => {
  const view = read('ui', 'webview', 'file-view.ts');
  assert.ok(view.includes('the dashboard, in Safari and in Firefox'), "file-view.ts's chain comment names both");
  assert.ok(body.includes('Reachable from the kernel-served dashboard, in Safari and in Firefox'), 'the body names both');
  assert.ok(body.includes('the review of this branch found it for an inline svg image in Firefox and in WebKit'), 'the body attributes the svg vector to this branch\'s review');
  assert.ok(header.title.endsWith('so no gated figure is fetched while its placeholder stands'), 'the title states the property, not one engine');
  assert.ok(!header.title.includes('WebKit'), 'the title names no engine');
});

test('the entry keeps the record rules: fix tier, a candidate, pr: blank until filed and then the fork PR number, no em dash', () => {
  assert.equal(header.tier, 'fix');
  assert.equal(header.status, 'candidate');
  assert.match(header.pr, /^(|[1-9][0-9]*)$/, 'pr: is blank until the PR exists, then its fork number (the guard rule: blank or an integer)');
  assert.ok(!entry.includes(String.fromCharCode(0x2014)), 'no em dash');
});
