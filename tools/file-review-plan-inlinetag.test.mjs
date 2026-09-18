// The inline tag and the cells (2026-09-18; plans/file-review.md decisions 52 and 53, the Rendered paragraph and the
// painting paragraph of the UX section, the Tests bullet, the Docs sentence and the Open questions paragraph;
// plans/markdown-viewer.md's two pointer sentences; docs/guide.md). The user's note had a placeholder written as an
// inline `<table>` tag mid-paragraph, which opened an element inside the paragraph in the sanitizer's quirks-mode
// parse and made the anchor map refuse that block and every block after it; decision 52 renders an inline start tag
// with no end tag in its block as its own characters, on the viewer's parse and on the map's lex, through one shared
// function (md-literal-tags.ts). Decision 53 overturns Slice 8's one-cell refusal: a selection across several cells of
// one table anchors to its span, the pipes inside the quote. This module holds each record to the source that makes
// it true: the decisions' sentences to the module (its export, its void list), to both callers (mdBlock's three steps
// in file-view.ts, placeTokens' lex line in anchor-map.ts, one void list) and to the chat's modules that must not
// import it; the retired one-cell machinery and the anchor line in anchor-map.ts; the guide's two sentences; the
// markdown-viewer plan's pointers; the Tests bullet's modules to the tree; and the about module's DECISIONS_END.
// Synthetic: the repo's own text only. Run: node --test tools/file-review-plan-inlinetag.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');
const exists = (...parts) => fs.existsSync(path.join(REPO, ...parts));
const flat = (s) => s.replace(/\s+/g, ' ');

const plan = read('plans', 'file-review.md');
const viewerPlan = flat(read('plans', 'markdown-viewer.md'));
const guide = flat(read('docs', 'guide.md'));
const mod = read('ui', 'webview', 'md-literal-tags.ts');
const view = read('ui', 'webview', 'file-view.ts');
const map = read('ui', 'webview', 'anchor-map.ts');
const about = read('tools', 'file-review-plan-about.test.mjs');

// The text between two headings, hard wraps collapsed so an assertion survives a rewrap.
function section(from, to) {
  const a = plan.indexOf(from);
  assert.ok(a >= 0, `heading ${JSON.stringify(from)} not found in the plan`);
  const b = plan.indexOf(to, a + from.length);
  assert.ok(b > a, `heading ${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return flat(plan.slice(a, b));
}
const ux = section('### Commenting from either view, and in every format', '### The viewer seam');
const tests = section('## Tests', '## Docs');
const docs = section('## Docs', '## Deliberately not in v1');
const decisions = section('## Decisions (the user, 2026-09-05 and 2026-09-06)', '## Open questions for the user');
const open = section('## Open questions for the user', '## Upstream');
const d52 = decisions.slice(decisions.indexOf('52. **'), decisions.indexOf('53. **'));
const d53 = decisions.slice(decisions.indexOf('53. **'));

// A function's source, from its `function name(` to the first line that is a lone closing brace.
function fn(src, name) {
  const a = src.indexOf(`function ${name}(`);
  assert.ok(a >= 0, `${name} is defined`);
  const b = src.indexOf('\n}\n', a);
  assert.ok(b > a, `${name} closes`);
  return src.slice(a, b);
}
function inOrder(src, needles, what) {
  let from = 0;
  for (const n of needles) {
    const i = src.indexOf(n, from);
    assert.ok(i >= 0, `${what}: ${JSON.stringify(n)} follows the previous step`);
    from = i + n.length;
  }
}
/** The module names a record carries in backticks. */
const modulesNamed = (text) => Array.from(text.matchAll(/`([^`\s]+\.(?:test\.ts|test\.mjs|py))`/g), (m) => m[1]);
/** The Decisions list's numbers, as the about module reads them. */
const decisionNumbers = Array.from(decisions.matchAll(/(?:^| )(\d+)\. \*\*/g), (m) => Number(m[1]));

// ── the two records ─────────────────────────────────────────────────

test('decisions 52 and 53 follow 51, dated 2026-09-18, the list consecutive to 53 and the about module ending there', () => {
  assert.deepEqual(decisionNumbers, Array.from({ length: 53 }, (_, i) => i + 1), 'the list runs 1..53');
  assert.match(about, /^const DECISIONS_END = 53;$/m, 'the about module\'s pin ends at 53');
  assert.ok(d52.startsWith('52. **An inline start tag with no end tag in its block renders as literal text, and the anchor map places it** (2026-09-18).'));
  assert.ok(d53.startsWith('53. **A selection across several cells of one table anchors to its span** (2026-09-18).'));
  for (const [name, text] of [['decision 52', d52], ['decision 53', d53], ['the Open questions paragraph', open.slice(open.indexOf('Two edges of decision 53'))], ['the Docs sentence', docs.slice(docs.indexOf('With decisions 52 and 53'))]]) {
    assert.ok(!text.includes(String.fromCharCode(0x2014)), `${name} has no em dash`);
    assert.ok(!/"[^"]*\b(I|my|me)\b[^"]*"/.test(text.replace(/"This selection spans more than one cell of a table; select within one cell, or comment on it from the Raw view\."/g, '')), `${name}: no quoted utterance of the user's`);
  }
});

test('decision 52 records the report paraphrased, the rule, the one shared function with its two callers, the void list, what is deliberately left, and the tests', () => {
  assert.ok(d52.includes('The user reported that comments from the Rendered view were refused over most of one of their notes.'));
  assert.ok(d52.includes('a placeholder written mid-paragraph as a `<table>` start tag followed by a file name (the tests write it `(<table>__widths.csv)`)'));
  assert.ok(d52.includes('150 of the note\'s 189 blocks refused, identically on every main head since the map\'s first release'));
  assert.ok(d52.includes('The user took the assessment\'s first option on its recommendation: such a tag renders as its own characters, and the map predicts them.'));
  assert.ok(d52.includes('The rule: an inline `html` token that is a START tag of a non-void element, with no matching end tag later in the SAME block\'s inline tokens, becomes a `text` token in place, its raw kept and its text the raw escaped as marked\'s inline text tokenizer escapes text'));
  assert.ok(d52.includes('its `Tokens.Text` has no `escaped` field, so the text is escaped up front'));
  assert.ok(d52.includes('Matching is by element name, ASCII case-insensitive, innermost first'));
  assert.ok(d52.includes('so `<b>x<b>y</b>` keeps the inner pair as HTML and makes the first `<b>` text, `<B>x</b>` is closed and `<b>x *y</b>*` is closed through the emphasis'));
  assert.ok(d52.includes('One rule in one code path is the design point that keeps the risk low: one module, `ui/webview/md-literal-tags.ts`, exports `literalizeUnclosedTags(tokens)`, and two callers run it on their own token trees of the same source under the one configuration (md-config.ts)'));
  assert.ok(d52.includes('Nothing is registered on the singleton (no marked.use, no renderer hook; the module imports marked\'s types alone), so the chat\'s `md()` (render.ts, still marked.parse) and md-config.ts are untouched'));
  assert.ok(d52.includes('Deliberately left, recorded here: `<hr>` inline is void, stays HTML and still splits its paragraph in the parser; a start tag whose end tag stands in a LATER block renders as text now'));
  assert.ok(d52.includes('a block-level element closed within its block mid-line (`<div>x</div>`) still splits the paragraph in the parser, a known gap'));
  assert.ok(d52.includes('inside an inline `<svg>` or `<math>` the rule applies by name'), 'the foreign-content consequence is recorded');
  assert.ok(d52.includes('CONTEXT.md is unchanged, since no term was coined.'));
  const named = modulesNamed(d52);
  assert.ok(named.length >= 12, 'the record names its tests: ' + named.length);
  for (const m of named) assert.ok(exists(...m.split('/')), `${m} exists`);
  for (const m of ['ui/webview/md-literal-tags.test.ts', 'ui/webview/anchor-map-literal-tags.test.ts', 'ui/webview/anchor-map-literal-tags-browser.test.ts', 'tools/file-review-plan-inlinetag.test.mjs']) assert.ok(named.includes(m), `decision 52 names ${m}`);
});

test('decision 53 records the ruling overturned, the raw delimiters accepted, the anchor, the retired machinery, the two edges left open, the paint rule and the tests', () => {
  assert.ok(d53.includes('refused a Rendered selection whose source span covered two or more cells of one table with the sentence "This selection spans more than one cell of a table; select within one cell, or comment on it from the Raw view."'));
  assert.ok(d53.includes('the user overturned the ruling: the selection anchors instead of refusing, the raw delimiters inside the quote accepted.'));
  assert.ok(d53.includes('The anchor runs from the selection\'s first positioned character to its last, both from the pass as before, widened by a formula the selection covered whole at either end (the existing `widened`'));
  assert.ok(d53.includes('the quote is the source between, the pipes, the delimiter row and the line feeds included, the characters a Raw selection over the same text mints'));
  assert.ok(d53.includes('The one-cell machinery is gone from the map: the constant `ONE_CELL`, `cellsRule`'));
  assert.ok(d53.includes('Two edges are the build\'s reading of the contract, which said to keep whatever the formula rules still need, and not a ruling'));
  assert.ok(d53.includes('The paint rule: the rendered paint of a multi-cell anchor needs no new rule.'));
  assert.ok(d53.includes('so every covered cell gets a mark over its own text and the pipes get none'));
  assert.ok(open.includes('Two edges of decision 53 (2026-09-18) are the build\'s reading of its contract, not a ruling'), 'the Open questions paragraph carries the two edges');
  const named = modulesNamed(d53);
  assert.ok(named.length >= 7, 'the record names its tests: ' + named.length);
  for (const m of named) assert.ok(exists(...m.split('/')), `${m} exists`);
  for (const m of ['ui/webview/anchor-map-cells.test.ts', 'ui/webview/anchor-map-cells-formulas.test.ts', 'ui/webview/anchor-map-cells-browser.test.ts', 'tests/test_guide_files_cells_and_code_lines.py']) assert.ok(named.includes(m), `decision 53 names ${m}`);
});

// ── the module and its two callers ──────────────────────────────────

test('md-literal-tags.ts exports the function and the void list the record names, imports marked\'s types alone, and both file-view.ts and anchor-map.ts import and call the function; the chat\'s modules do not', () => {
  assert.ok(mod.includes('export function literalizeUnclosedTags(tokens: Token[]): void {'), 'the one exported walk');
  const voidLine = mod.match(/^export const VOID_ELEMENTS: ReadonlySet<string> = new Set\(\[(.*)\]\);$/m);
  assert.ok(voidLine, 'the void list is exported');
  const moduleVoids = Array.from(voidLine[1].matchAll(/"([A-Z]+)"/g), (m) => m[1].toLowerCase()).sort();
  const recordVoids = Array.from(d52.slice(d52.indexOf('The void list is HTML\'s fourteen')).matchAll(/`([a-z]+)`/g), (m) => m[1]).slice(0, 14).sort();
  assert.deepEqual(recordVoids, moduleVoids, 'the record lists the module\'s fourteen void elements');
  assert.equal(moduleVoids.length, 14);
  assert.deepEqual(mod.match(/^import .*$/gm), ['import type { Token, Tokens } from "marked";'], 'the module imports marked\'s types alone: nothing on the singleton');
  assert.ok(!/marked\.(use|setOptions)\(/.test(mod), 'no marked.use');
  // the viewer: mdBlock's three steps, the rule between the lexer and the walk, over a copy of the defaults
  assert.match(view, /^import \{ literalizeUnclosedTags \} from "\.\/md-literal-tags";/m, 'file-view.ts imports the rule');
  const mdBlock = view.split('function mdBlock(text: string, doc?: MdDocLoc): HTMLElement {')[1].split('\n}\n')[0];
  inOrder(mdBlock, ['const base = marked.defaults.walkTokens;', 'const opts = { ...marked.defaults };', 'const tokens = marked.lexer(text, opts);', 'literalizeUnclosedTags(tokens);', 'marked.walkTokens(tokens, (t) => {', 'if (doc && doc.kind === "file") viewerWalkTokens(t);', 'if (base) void base.call(marked, t);', 'const dirty = marked.parser(tokens, opts);', 'sanitizeMd(dirty'], 'mdBlock');
  assert.ok(!mdBlock.includes('marked.parse('), 'mdBlock no longer calls marked.parse');
  assert.equal((view.match(/literalizeUnclosedTags\(/g) || []).length, 1, 'one call in the viewer');
  // the map: the rule on the lex line, before anything reads the tree; one void list
  assert.match(map, /^import \{ literalizeUnclosedTags, VOID_ELEMENTS \} from "\.\/md-literal-tags";/m, 'anchor-map.ts imports the rule and the void list');
  const place = fn(map, 'placeTokens');
  assert.ok(place.includes('try { tokens = Lexer.lex(N); literalizeUnclosedTags(tokens); } catch (e) { lexError = String((e as Error).message || e); }'), 'the rule right after the lex');
  assert.equal((map.match(/literalizeUnclosedTags\(/g) || []).length, 1, 'one call in the map');
  assert.match(map, /^const VOID_TAGS = VOID_ELEMENTS;$/m, 'the scans read the module\'s list');
  assert.ok(!map.includes('new Set(["AREA"'), 'no second void list in the map');
  // the chat renders as before
  for (const f of ['md-config.ts', 'render.ts', 'chat-md.ts']) {
    assert.ok(!read('ui', 'webview', f).includes('md-literal-tags'), `${f} does not import the rule`);
  }
  assert.match(read('ui', 'webview', 'render.ts'), /const dirty = marked\.parse\(src\) as string;/, 'the chat\'s md() still parses with marked.parse');
});

test('anchor-map.ts holds no one-cell rule: ONE_CELL, cellsRule, coveredCells and coveredOnly are gone with the sentence, and the anchor is the widened span sliced from the source', () => {
  for (const gone of ['ONE_CELL', 'cellsRule', 'coveredCells', 'coveredOnly']) assert.ok(!map.includes(gone), `${gone} is gone from anchor-map.ts`);
  assert.ok(!map.includes('spans more than one cell'), 'no refusal names a count of cells');
  assert.ok(!map.includes('select within one cell'), 'the one-cell sentence is gone');
  const sel = map.slice(map.indexOf('export function mapRenderedSelection('));
  assert.ok(sel.includes('const FORMULA_TOUCHED = "This selection touches a formula; comment on it from the Raw view.";'), 'the formula refusal stands');
  assert.ok(sel.includes('const { start, end } = widened(nOf(idx, idx.blocks[bs].pos[ks]), nOf(idx, idx.blocks[be].pos[ke - 1]) + 1);'), 'the anchor: the first positioned character through the last, widened by a covered formula');
  assert.ok(sel.includes('return { ok: true, range: { start, end }, quote: source.slice(start, end) };'), 'the quote is that slice of the source');
  // the header comment, its `//` prefixes stripped so a sentence wrapped across comment lines reads whole
  const header = flat(map.slice(0, map.indexOf('\nimport ')).replace(/^\/\/ ?/gm, ''));
  assert.ok(header.includes('a selection across several cells of one table maps to its span'), 'the header says so');
  assert.ok(header.includes('an inline start tag with no end tag in its block is literal text on both sides'), 'and names the literal-tags rule');
});

// ── the guide, the other plan and the plan's own paragraphs ─────────

test('the guide says a selection across several cells can be commented from the Rendered view and names a formula as what cannot be mapped, and its own-HTML paragraph says an unclosed inline tag is shown as the characters typed', () => {
  assert.ok(guide.includes('A table cell, a selection across several cells of a table and a line of a code block can be commented from the Rendered view like any passage; a comment across cells quotes the pipes between them as the file holds them. When a passage cannot be mapped from the Rendered view (a formula), the panel says so, keeps your comment, and offers the Raw view with the passage selected.'));
  assert.ok(!guide.includes('(a selection across two cells of a table, a formula)'), 'the parenthetical before decision 53 is gone');
  assert.ok(!guide.includes('select within one cell'), 'the guide promises no one-cell refusal');
  // the rule's sentence as the guide states it since the second round (the placeholder typed mid-sentence), the opening of the
  // HTML-block passage that follows it, and the closing sentence; the passage's clauses are held one by one by
  // tools/guide-own-html-block-tag.test.mjs
  assert.ok(guide.includes('A tag opened in a line of prose and not closed in the same paragraph, heading, list item or table cell (a placeholder typed mid-sentence as `<table>`, say) is shown as the characters typed, not read as HTML, and can be commented on like any passage; a tag closed in the same block, and a tag that never takes an end tag such as `<br>` or `<img>`, is HTML as before. A tag the viewer reads as an HTML block rather than as prose is HTML as before too:'));
  assert.ok(guide.includes('and a comment on the passage goes through the Raw view. A chat message is not read this way.'));
  for (const name of ['br', 'img']) assert.ok(mod.includes(`"${name.toUpperCase()}"`), `the guide's examples of a tag with no end tag are in the module's void list: ${name}`);
});

test('plans/markdown-viewer.md points at both decisions without rewriting the slices\' history', () => {
  assert.ok(viewerPlan.includes('Overturned by decision 53 of plans/file-review.md (2026-09-18): a selection across several cells of one table anchors to its span, the pipes and the delimiter row inside the quote, and the one-cell sentence, `cellsRule`, `coveredCells` and `coveredOnly` are gone from the map; this item stands as the slice\'s history.'));
  assert.ok(viewerPlan.includes('built since as decision 52 of plans/file-review.md, 2026-09-18, by a rule the viewer and the map share rather than by `Block.leaves`: an inline start tag with no end tag in its block renders as its own characters on both sides, so the block maps and that fix shape is moot'));
  assert.ok(viewerPlan.includes('3. *Item 3, a selection spanning cells is refused with the reason named, the Raw view offered on the span.*'), 'the Slice 8 item keeps its title as history');
});

test('the UX section, the Tests bullet and the Docs sentence carry the two decisions, and every module the bullet names is in the tree', () => {
  assert.ok(ux.includes('Two later changes narrow that list of refusals: Slice 8 of plans/markdown-viewer.md positions a table\'s cells and a code block\'s lines as prose, so a selection inside one maps, and decision 53 (2026-09-18) lets a selection across several cells of one table anchor to its span'));
  assert.ok(ux.includes('and decision 52 (2026-09-18) renders an inline start tag with no end tag in its block as its own characters on both sides'));
  assert.ok(ux.includes('A highlight or a change mark over an anchor that spans several cells of a table is one mark per cell over the cell\'s own text, none over the pipes between them (decision 53: the exact path\'s `wrapBetween` skips the whitespace between the cells\' boxes), and one over an inline tag rendered as literal text wraps the tag\'s characters (decision 52).'));
  assert.ok(ux.includes('Since Slice 8 of plans/markdown-viewer.md and decision 53 the code and the table are no longer refusals: a code line, a cell and a selection across several cells of one table map'));
  assert.ok(map.includes('const BLOCK_BOXES'), 'the painting sentence names a mechanism the map has');
  assert.ok(map.includes('function wrapBetween('), 'and wrapBetween');
  const bullet = tests.slice(tests.indexOf('- The inline tag and the cells (2026-09-18, decisions 52 and 53):'));
  assert.ok(bullet.length > 0, 'the Tests section carries the bullet');
  const named = modulesNamed(bullet.slice(0, bullet.indexOf('## Docs') < 0 ? undefined : bullet.indexOf('## Docs')));
  assert.ok(named.length >= 8, 'the bullet names its modules: ' + named.length);
  for (const m of named) assert.ok(exists(...m.split('/')), `${m} exists`);
  assert.ok(docs.includes('With decisions 52 and 53 (2026-09-18), that a table cell, a selection across several cells of a table and a line of a code block can be commented from the Rendered view like any passage'));
  assert.ok(docs.includes('(`tools/file-review-plan-inlinetag.test.mjs` holds the sentence to the guide and the module)'));
  assert.ok(docs.includes('and that a tag first on its line, which markdown reads as an HTML block, is HTML as before, the same placeholder included (`tools/guide-own-html-block-tag.test.mjs` holds those clauses to the guide, the installed marked\'s lexer and the map)'), 'the Docs sentence carries the guide\'s HTML-block limit and names its pin module');
});
