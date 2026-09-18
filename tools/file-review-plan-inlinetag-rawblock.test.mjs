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
// blocks' text tokens. Synthetic text only. Run: node --test tools/file-review-plan-inlinetag-rawblock.test.mjs
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
