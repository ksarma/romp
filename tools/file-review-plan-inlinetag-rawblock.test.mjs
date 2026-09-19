// The scope of marked's inline lexer state, as decision 52 of plans/file-review.md records it among the shapes it
// deliberately left (2026-09-18; the record first said "the block's remaining text", and the review of the slice
// found the scope wider). marked keeps `inRawBlock` and `inLink` on the one Lexer that lexes a document, and
// `Lexer.lex` drains every block's inline run through that instance with no reset between blocks: after an inline
// `<kbd>`, `<pre>`, `<code>` or `<script>` start tag with no end tag, the rest of that block AND every later block
// of the document is lexed unescaped until an end tag of any of those four names or the document's end, and after
// an unclosed `<a` no bare URL is autolinked in that block or any later one until an `</a>`. The viewer's mdBlock
// (file-view.ts) and the map's placeTokens (anchor-map.ts) each lex the whole document with one Lexer, so the scope
// is theirs too; the literal-tags rule runs after the lex and changes no lexer state, so this is marked's behaviour
// before and after decision 52. This module holds the record's sentence to the plan and to the installed marked
// (vscode-extension/node_modules, the copy the viewer bundles), by lexing synthetic documents and reading the later
// blocks' text tokens. The lexer legs skip where marked is not installed, and CI's shell job, the one runner of
// tools/*.test.mjs, installs nothing, so they skipped in every CI run (review find, 2026-09-18): the module of the same stem
// under ui/webview (file-review-plan-inlinetag-rawblock.test.ts) holds the same scope through both callers' lexes under the
// extension job's `npm test`, which installs, and the last test here holds that module and its runner to the tree, so the
// record's sentence has an arbiter in CI. Synthetic text only. Run: node --test tools/file-review-plan-inlinetag-rawblock.test.mjs
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
const flat = (s) => s.replace(/\s+/g, ' ');

// ── the record ──────────────────────────────────────────────────────

test('decision 52 records the scope of the unrewound lexer state as the rest of the document, not the block', () => {
  const plan = flat(fs.readFileSync(path.join(REPO, 'plans', 'file-review.md'), 'utf8'));
  const d52 = plan.slice(plan.indexOf('52. **An inline start tag with no end tag in its block'), plan.indexOf('53. **A selection across several cells'));
  assert.ok(d52.length > 0, 'decision 52 precedes decision 53');
  assert.ok(d52.includes("marked's inline lexer state is not rewound between blocks: one Lexer lexes every block's inline run in turn, so a flag one block sets stays set for the rest of the document."));
  assert.ok(d52.includes('After an unclosed `<kbd>`, `<pre>`, `<code>` or `<script>` it lexes the remaining text of that block and of every later block unescaped (`inRawBlock`), until an end tag of any of those four names (a stray `</code>` closes an open `<kbd>`) or the document\'s end'));
  assert.ok(d52.includes('After an unclosed `<a` it autolinks no bare URL in that block or any later one (`inLink`), until an `</a>`.'));
  assert.ok(d52.includes("Under the flag marked's inline tag rule still reads a tag-shaped run (`<c>`, `<c a=\"b\">`, `<y z>`, `<y then d>`) as an `html` token"), 'the tag-shaped run under the flag');
  assert.ok(d52.includes("A `<` before a letter that the tag rule does not read as a tag (`<b=c>`, `<b/x>`, `<y z t2.` with no `>` after it in its block) is unescaped text"), 'the run the tag rule rejects');
  assert.ok(!d52.includes("a later block with a `<` before a letter then loses the text"), 'the over-broad clause is gone');
  assert.ok(!d52.includes("lexes the block's remaining text"), 'the block-scoped wording is gone');
  assert.ok(!d52.includes(String.fromCharCode(0x2014)), 'no em dash');
});

// ── the installed marked ────────────────────────────────────────────

/** Each paragraph's and heading's inline run as one string: a text token's text (escaped or not, which is the point), any
 *  other token as `[type:raw]`. */
function inlineText(tokens) {
  return tokens
    .filter((t) => t.type === 'paragraph' || t.type === 'heading')
    .map((t) => t.tokens.map((x) => (x.type === 'text' ? x.text : `[${x.type}:${x.raw}]`)).join(''));
}
const LATER = 'Later a & b <y then d.\n\n# Head a & b <y\n\nClosing a & b <y then d.\n';
const ESCAPED = ['Later a &amp; b &lt;y then d.', 'Head a &amp; b &lt;y', 'Closing a &amp; b &lt;y then d.'];
const RAW = ['Later a & b <y then d.', 'Head a & b <y', 'Closing a & b <y then d.'];

test('an unclosed <kbd>, <pre>, <code> or <script> leaves every later block lexed unescaped, to the document\'s end', { skip: SKIP }, async () => {
  const { Lexer } = await import(pathToFileURL(MARKED).href);
  assert.deepEqual(inlineText(Lexer.lex('Plain a & b.\n\n' + LATER)).slice(1), ESCAPED, 'the control escapes every later block');
  for (const tag of ['kbd', 'pre', 'code', 'script']) {
    const got = inlineText(Lexer.lex(`Open <${tag}>here a & b.\n\n` + LATER));
    assert.equal(got[0], `Open [html:<${tag}>]here a & b.`, `${tag}: the rest of its own block is unescaped`);
    assert.deepEqual(got.slice(1), RAW, `${tag}: every later block, a heading among them, is unescaped`);
  }
});

test('an end tag of any of the four names clears the flag and escaping resumes; an end tag of another name does not', { skip: SKIP }, async () => {
  const { Lexer } = await import(pathToFileURL(MARKED).href);
  const cleared = inlineText(Lexer.lex('Open <kbd>here.\n\nStill raw a & b.\n\nStray </code> then a & b <y.\n\nAfter a & b <y then d.\n'));
  assert.deepEqual(cleared, ['Open [html:<kbd>]here.', 'Still raw a & b.', 'Stray [html:</code>] then a &amp; b &lt;y.', 'After a &amp; b &lt;y then d.'], 'a stray </code> closes an open <kbd>');
  const kept = inlineText(Lexer.lex('Open <kbd>here.\n\nStray </b> then a & b <y.\n'));
  assert.deepEqual(kept, ['Open [html:<kbd>]here.', 'Stray [html:</b>] then a & b <y.'], 'a </b> clears nothing');
});

test('under the flag marked\'s inline tag rule still reads a tag-shaped run as an html token (the rule\'s input, converted when its block holds no end tag); a run it does not read as a tag is unescaped text; a closed pair is html on both ends', { skip: SKIP }, async () => {
  const { Lexer } = await import(pathToFileURL(MARKED).href);
  const paras = Lexer.lex('Open <kbd>here.\n\nStill raw a & b <c> and <b=c> d and <b/x> e.\n\nPair <c>x</c> t.\n').filter((t) => t.type === 'paragraph');
  const shape = (t) => `${t.type}:${t.raw}` + (t.type === 'text' ? (t.text === t.raw ? ' (text=raw)' : ` (text=${t.text})`) : t.type === 'html' && t.inRawBlock ? ' (inRawBlock)' : '');
  assert.deepEqual(paras[1].tokens.map(shape), ['text:Still raw a & b  (text=raw)', 'html:<c> (inRawBlock)', 'text: and <b=c> d and <b/x> e. (text=raw)'], 'the tag-shaped `<c>` is an html token under the flag; `<b=c>` and `<b/x>` are unescaped text');
  assert.deepEqual(paras[2].tokens.map(shape), ['text:Pair  (text=raw)', 'html:<c> (inRawBlock)', 'text:x (text=raw)', 'html:</c> (inRawBlock)', 'text: t. (text=raw)'], 'the closed pair: html on both ends');
});

test('an unclosed <a leaves no bare URL autolinked in any later block until an </a>', { skip: SKIP }, async () => {
  const { Lexer } = await import(pathToFileURL(MARKED).href);
  const types = (src) => Lexer.lex(src).filter((t) => t.type === 'paragraph').map((t) => t.tokens.map((x) => x.type).join(','));
  assert.deepEqual(types('See https://example.test/a now.\n'), ['text,link,text'], 'the control autolinks');
  assert.deepEqual(
    types('Open <a href="x">here.\n\nSee https://example.test/a now.\n\nStray </a> here.\n\nSee https://example.test/b now.\n'),
    ['text,html,text', 'text', 'text,html,text', 'text,link,text'],
    'no link in the later block until the </a>; a link after it',
  );
});

// ── the arbiter in CI ───────────────────────────────────────────────

// The three legs above assert only where marked is installed. CI's shell job runs tools/*.test.mjs from a bare checkout, so
// they skip there, and the extension job, which runs npm ci, invokes no tools module but pdf-smoke; so the webview module of
// this stem carries the scope into that job's `npm test`. This test runs everywhere and holds the chain: the module is in the
// tree with both lexes and every case above, the test build takes every .test.ts under ui/webview, `npm test` builds and runs
// that bundle, and the extension job runs `npm test` after `npm ci`.
const TWIN = path.join(REPO, 'ui', 'webview', 'file-review-plan-inlinetag-rawblock.test.ts');

test('the webview module of this stem holds the scope to the installed marked where CI installs it: both callers\' lexes, every case above, and the extension job\'s npm test as its runner', () => {
  assert.ok(fs.existsSync(TWIN), 'ui/webview/file-review-plan-inlinetag-rawblock.test.ts is in the tree');
  const twin = fs.readFileSync(TWIN, 'utf8');
  assert.ok(twin.includes('from "marked"') && twin.includes('applyMdConfig();'), 'it lexes with the installed marked under the one configuration');
  assert.ok(twin.includes('marked.lexer(src, opts)') && twin.includes('{ ...marked.defaults }'), "mdBlock's lex: marked.lexer over a copy of the defaults");
  assert.ok(twin.includes('Lexer.lex(src)'), "placeTokens' lex: the static Lexer.lex");
  assert.ok(twin.includes('literalizeUnclosedTags(tokens)'), 'the rule runs after each lex');
  for (const s of ['["kbd", "pre", "code", "script"]', 'Stray </code>', 'Stray </b>', '<a href="x">', 'Stray </a>', 'https://example.test/b', '<c> and <b=c>', 'Pair <c>x</c>']) {
    assert.ok(twin.includes(s), `the module holds the ${s} case`);
  }
  assert.ok(!twin.includes('skip:'), 'no leg of it skips');
  const esbuild = fs.readFileSync(path.join(REPO, 'vscode-extension', 'esbuild.js'), 'utf8');
  assert.ok(esbuild.includes('["src", "../ui", "../ui/webview"]') && esbuild.includes('f.endsWith(".test.ts")'), 'the test build takes every .test.ts under ui/webview');
  const pkg = JSON.parse(fs.readFileSync(path.join(REPO, 'vscode-extension', 'package.json'), 'utf8'));
  assert.ok(/esbuild\.js --tests/.test(pkg.scripts.test) && /out-tests\/\*\*\/\*\.test\.js/.test(pkg.scripts.test), 'npm test builds and runs the bundle: ' + pkg.scripts.test);
  const ci = fs.readFileSync(path.join(REPO, '.github', 'workflows', 'ci.yml'), 'utf8');
  assert.ok(/working-directory: vscode-extension\n[\s\S]*?run: npm ci\n[\s\S]*?run: npm test\n/.test(ci), 'the extension job runs npm ci, then npm test');
});
