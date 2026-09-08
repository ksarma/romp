// The plan's margin-layout note (plans/file-review.md, the Slice 2 section) carries a Built account, and the
// Tests section is the plan's record of where each mechanism is pinned: a maintainer asking why the body has an
// inline padding-bottom, why the "… N more changes" fold stands above Send rather than in the cards track, or
// which test holds the footer's yield rule, reads the plan first. The follow-on's first review (2026-09-07)
// replaced the layout's one-range mechanism (a list sized to the body's scroll height) with a padded body and
// a range match, moved every non-card row into the footer, made the cards' DOM order the placement's, gave the
// keyboard back after a move that detaches it, escaped the id selectors, and gave the footer a floor and a
// yield rule in both sheets — and its commit said the plan's Tests section named the new modules when it named
// none; the Built account still described the range as it was before the review. This module holds the note
// and the Tests section to the tree the way tools/file-review-plan.test.mjs holds the plan's other statements:
// each mechanism the account names is in the panel source or the sheets, the pre-review statement is gone, and
// every test module the note and the Tests bullet name exists and holds the pin the plan credits it with.
// ui/webview/file-review-docs.test.ts checks only that the files the Tests section names exist; this one reads
// the note as well, and what each file holds. Synthetic: only the repo's own text.
// Run: node --test tools/file-review-plan-margin-review.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const read = (...p) => fs.readFileSync(path.join(REPO, ...p), 'utf8');
const plan = read('plans', 'file-review.md');
const panel = read('ui', 'webview', 'file-comments.ts');
const sheets = [['styles.css', read('ui', 'webview', 'styles.css')], ['feed.css', read('ui', 'webview', 'feed.css')]];

// The text between two headings, hard wraps collapsed so an assertion survives a rewrap.
function section(from, to) {
  const a = plan.indexOf(from);
  assert.ok(a >= 0, `heading ${JSON.stringify(from)} not found in the plan`);
  const b = plan.indexOf(to, a + from.length);
  assert.ok(b > a, `heading ${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return plan.slice(a, b).replace(/\s+/g, ' ');
}
const slice2 = section('### Slice 2: the session\'s changes as accept/reject cards and inline marks', '### Slice 3: region comments on images');
const tests = section('## Tests', '## Docs');
const docs = section('## Docs', '## Deliberately not in v1');

// The note's Built account: from "Built:" to the note's end; its Tests sentence is the tail.
const LABEL = 'The margin-layout follow-on (2026-09-07), panel side.';
const noteAt = slice2.indexOf(LABEL);
assert.ok(noteAt >= 0, 'the note is in the Slice 2 section');
const builtAt = slice2.indexOf(' Built: ', noteAt);
assert.ok(builtAt > noteAt, 'the note turns to what was built');
// ...to the next follow-on note under Slice 2 (the anchors follow-on's, then the todo-file's, then the filter's, in date
// order since main merged the three branches), or the section's end when none follows.
const builtEnd = (() => { const m = / The [a-z-]+ follow-on \(20\d\d-\d\d-\d\d\)/.exec(slice2.slice(builtAt)); return m ? builtAt + m.index : slice2.length; })();
const built = slice2.slice(builtAt, builtEnd);
const testsAt = built.lastIndexOf(' Tests: ');
assert.ok(testsAt > 0, 'the Built account ends with the modules that pin it');
const noteTests = built.slice(testsAt);

// The Tests section's margin bullet: from its lead to the next bullet.
const BULLET = '- `ui/webview/card-layout.test.ts`, `file-comments-margin.test.ts` and `file-comments-margin-browser.test.ts` (the margin-layout follow-on, 2026-09-07)';
const bulletAt = tests.indexOf(BULLET);
assert.ok(bulletAt >= 0, 'the Tests section has the margin bullet');
const bulletEnd = tests.indexOf(' - `', bulletAt + BULLET.length);
const bullet = tests.slice(bulletAt, bulletEnd === -1 ? undefined : bulletEnd);

/** The test files a run of prose names in backticks, as file-review-docs.test.ts reads them: a bare `*.test.ts`
 *  is a webview test, anything else a repo path. */
const testFiles = (s) => Array.from(s.matchAll(/`([^`\s]+\.(?:test\.ts|test\.mjs|py|bats))`/g), (m) => m[1])
  .map((n) => (n.includes('/') ? n : path.posix.join('ui', 'webview', n)));

// ── the Built account, held to the panel ──────────────────────────────────────────────────────────────────

test('the one range is stated as the code makes it: the body padded by the footer plus the overhang, the list sized to the range or the cards, the track alone past a non-scrolling body', () => {
  assert.ok(!built.includes('whose content is as tall as the body\'s, so the two share one range'), 'the pre-review statement of the range is gone');
  assert.ok(built.includes('pads the body\'s content at its end by the footer\'s height plus how far the last card hangs past the content\'s end (`padBody`'));
  assert.ok(/private padBody\(body: HTMLElement, px: number\): void \{/.test(panel), 'the panel has padBody');
  assert.ok(/body\.style\.paddingBottom = px \? px \+ "px" : "";/.test(panel), 'padBody writes the inline padding');
  assert.ok(/this\.padBody\(body, Math\.ceil\(footer \+ hang\)\);/.test(panel), 'the pass pads by the footer plus the overhang');
  assert.ok(built.includes('cleared by `layoutOff` when the layout ends: the fold, edit mode, the panel\'s close'));
  assert.ok(/private layoutOff\(\): void \{[^}]*this\.padBody\(this\.ctx\.body\(\), 0\);/.test(panel), 'layoutOff clears the padding');
  assert.ok(/if \(this\.margin\) this\.layoutOff\(\);[\s\S]*?this\.stopPoll\(\);\n\s*\}\n[\s\S]*?\n  dispose\(\): void \{\n(?:\s*this\.clearLanding\(\);[^\n]*\n)?\s*this\.stopPoll\(\);\n\s*if \(this\.margin\) this\.layoutOff\(\);/.test(panel), 'closePanel and dispose end the layout (since the inline-display follow-on, draftAsk stands between the two and dispose clears the Reveal landing cue first)');
  assert.ok(built.includes('makes the list as tall as puts the track\'s farthest position at the body\'s, or as the last card\'s end, whichever is more'));
  assert.ok(/list\.style\.height = Math\.max\(body\.scrollHeight - body\.clientHeight \+ track\.clientHeight, out\.bottom \+ CARD_GAP\) \+ "px";/.test(panel), 'the list is the range or the cards');
  assert.ok(!/list\.style\.height = Math\.max\(body\.scrollHeight - offset, /.test(panel), 'the pre-review sizing is gone');
  assert.ok(built.includes('there the track goes on alone as far as the last card\'s end, and a pass or a status reply leaves it there instead of pulling it back to the body (`followBody`)'));
  assert.ok(/private followBody\(\): void \{/.test(panel));
  assert.ok(/if \(track\.scrollTop > at && atEnd\(body\)\) want = Math\.min\(track\.scrollTop, Math\.max\(at, this\.cardsEnd - track\.clientHeight\)\);/.test(panel), 'past the body\'s end the track keeps its place, as far as the cards\' end');
});

test('the footer rows: every non-card row stands above Send, the foot first, and the account says which rows and why', () => {
  assert.ok(built.includes('The track holds cards alone: every row the list held stands in the footer above Send (`moveRows`), the foot with Accept all · Reject all first, then a wait\'s loader, a refusal row, the "… N more changes" and Resolved folds and the empty note, in the list\'s order.'));
  assert.ok(built.includes('A row at the top of a track locked to the body\'s scroll was out of view for a reader anywhere but the top of the text'), 'the reason, so the placement is not read as taste');
  assert.ok(/private moveRows\(kids: HTMLElement\[\]\): void \{/.test(panel));
  assert.ok(/const rows = kids\.filter\(\(k\) => !k\.classList\.contains\("fc-card"\) && !k\.classList\.contains\("fc-group"\)\);/.test(panel), 'every row that is not a card or a paragraph title');
  assert.ok(/this\.sections\.send\.insertBefore\(foot, this\.sections\.send\.firstChild\);/.test(panel), 'the foot first');
  assert.ok(/for \(const r of rows\) if \(r !== foot\) send\.insertBefore\(r, box\);/.test(panel), 'the other rows above Send, in the list\'s order');
  assert.ok(/this\.moveRows\(kids\(\)\);/.test(panel), 'called from the pass');
});

test('the content observer, the placement order, the focus fixup and the escaping are stated and in the panel', () => {
  assert.ok(built.includes('on the body\'s content\'s resize (`watchContent`'));
  assert.ok(/private watchContent\(body: HTMLElement\): void \{/.test(panel));
  assert.ok(/this\.watchContent\(body\);/.test(panel), 'the pass observes the content');
  assert.ok(built.includes('The pass also makes the cards\' DOM order the placement\'s, so the Tab order runs down the margin; `cardsInOrder`'));
  assert.ok(/private cardsInOrder\(\): HTMLElement\[\] \{/.test(panel));
  assert.ok((panel.match(/this\.cardsInOrder\(\)/g) || []).length >= 2, 'focusKey and focusNear read the placement order');
  assert.ok(/this\.moving\(order, \(\) => \{ for \(const node of order\) list\.appendChild\(node\); \}\);/.test(panel), 'the reorder runs through the focus-keeping move');
  assert.ok(built.includes('The rows\' move into the footer and the reorder both detach a focused control, and `moving` gives the keyboard back to it'));
  assert.ok(/private moving\(nodes: HTMLElement\[\], move: \(\) => void\): void \{/.test(panel));
  assert.ok(/if \(kept\) kept\.focus\(\{ preventScroll: true \}\);/.test(panel), 'the focus is given back');
  assert.ok((panel.match(/this\.moving\(/g) || []).length >= 2, 'the rows\' move and the reorder both use it');
  assert.ok(built.includes('the selectors the pass builds from a comment id are CSS-escaped (`cssId`)'));
  assert.ok(/function cssId\(s: string\): string \{/.test(panel));
  assert.ok((panel.match(/cssId\(/g) || []).length >= 4, 'ownMarks, goTo, scrollCard and focusNear escape the id');
});

test('the footer\'s floor and yield rule are stated, and both sheets carry the clip, the floor, the sticky toggle and Send and Log sections that scroll inside themselves', () => {
  assert.ok(built.includes('The footer stays inside the panel, in both sheets: the panel is `overflow: hidden`'));
  assert.ok(built.includes('the track has a basis of 0 with a floor of 30% of the panel'));
  assert.ok(built.includes('a footer section that outgrows its share (the Send section with its confirm up, the Log with its rows) shrinks and scrolls inside itself instead of pushing Send, Cancel or the Log toggle past the panel\'s edge, with the Log toggle sticky at the top of its scroller'));
  for (const [name, css] of sheets) {
    assert.ok(/\.fc-panel\.fc-margin \{ overflow: hidden; padding: 0; gap: 0; \}/.test(css), name + ': the panel never scrolls');
    assert.ok(/\.fc-margin > \.fc-sec-cards \{ flex: 1 1 0; min-height: 30%; position: relative; overflow: auto; scrollbar-width: none; \}/.test(css), name + ': the track\'s basis and floor');
    // the selector's form is the sheet's (round 1 keyed it on the confirm and the rows; a later round may key it otherwise):
    // the pin is that a grown Send or Log section scrolls inside itself
    assert.ok(/\.fc-margin > \.fc-sec-send[^{]*\{[^}]*overflow: auto;/.test(css), name + ': the Send section scrolls inside itself');
    assert.ok(/\.fc-margin > \.fc-sec-log[^{]*\{[^}]*overflow: auto;/.test(css), name + ': the Log section scrolls inside itself');
    assert.ok(/\.fc-margin \.fc-log > \.fc-sec \{ position: sticky; top: 0; background: var\(--bg\); \}/.test(css), name + ': the Log toggle is sticky');
  }
});

test('the account names the review that changed the mechanisms and what stood before it', () => {
  assert.ok(built.includes('The one range, the footer rows, the content observer, the placement order, the focus fixup, the escaping and the footer\'s yield rule are the follow-on\'s first review (2026-09-07)'));
  assert.ok(built.includes('before it the list was sized to the body\'s scroll height less the header\'s offset'));
});

// ── the modules: named in the note and the Tests section, in the tree, holding the pin credited ───────────

/** Each module the review added, the pin the plan credits it with (a test name, or a def), as the file spells it. */
const MODULES = [
  { file: 'ui/webview/file-comments-margin-review.test.ts', holds: [
    'test("the body\'s end is padded by the footer\'s height, so the two scrollers share one range',
    'test("a card hanging past the content\'s end grows the padding by its overhang',
    'test("a body that does not scroll (a short file): the track goes on alone',
    'test("the list\'s rows stand in the footer above Send — the foot first, then the rows in the list\'s order',
    'test("the cards\' DOM order is the placement\'s',
    'test("a write the other scroller clamps raises no echo',
    'test("the body\'s content is observed, not only its box',
    'test("cards the list layout held are observed when the margin layout comes on outside a render',
    'test("a comment id holding a quote: the pass builds its selectors escaped',
    'test("closing the panel takes the body\'s end padding and the margin class with it; reopening brings both back',
    'test("a standalone image: the region\'s card sits level with its rectangle',
    'test("a PDF: a region on a page with a box is placed beside its rectangle',
  ] },
  { file: 'ui/webview/file-comments-margin-review-browser.test.ts', holds: [
    'Reject all keeps the keyboard through its confirm\'s render',
    'a <details> block opened above the marks re-runs the pass',
    'the cards\' DOM order is the placement\'s, so Tabbing down the heads scrolls the text one way',
    'the list\'s rows stand in the footer',
  ] },
  { file: 'ui/webview/feed-css-margin-footers.test.ts', holds: [
    'test("feed.css: the margin layout gives the Send and Log sections an overflow of their own, inside the panel block"',
    'the Send confirm with its preview open stays inside the aside, scrolls under the wheel to Send · Cancel, and leaves the track its cards',
    'the open Log stays inside the aside, scrolls under the wheel to its oldest row, and leaves the track its cards',
  ] },
  { file: 'ui/webview/styles-fc-margin-footer.test.ts', holds: [
    'test("styles.css: the margin layout\'s track has a floor, the expanded footer sections yield and scroll, the panel never scrolls"',
    'the Send confirm with fifteen comments and the preview open scrolls within its section',
    'the Log with thirty rows scrolls within its section under a sticky toggle',
  ] },
  { file: 'ui/webview/feed-css-margin-leader.test.ts', holds: [
    'test("feed.css: a pushed card\'s leader is the sheet\'s ::before, dashed, as tall as the push',
    'test("styles.css: the chat page\'s sheet holds the same leader rule"',
    'the card the one above pushed wears a dashed leader up the gutter to its mark\'s height, inside the track; a card nothing pushed wears none',
  ] },
  { file: 'tests/test_guide_files_margin_layout.py', holds: [
    'def test_level_with_the_passage',
    'def test_scrolls_with_the_text',
    'def test_the_narrow_column_lists_the_cards',
    'def test_the_sheets_agree',
  ] },
  { file: 'ui/webview/file-comments-margin-browser.test.ts', holds: [
    'the scrollers move together over one range, the far end included',
  ] },
  { file: 'tools/file-review-plan-margin-review.test.mjs', holds: ['the Built account'] },
];

test('every module the review added is named in the note\'s Tests sentence and in the Tests section\'s margin bullet', () => {
  const inNote = new Set(testFiles(noteTests));
  const inBullet = new Set(testFiles(bullet));
  for (const m of MODULES) {
    assert.ok(inNote.has(m.file), `the note's Tests sentence names ${m.file}`);
    assert.ok(inBullet.has(m.file), `the Tests section's margin bullet names ${m.file}`);
  }
});

test('every test file the note names exists (the docs test reads the Tests section alone)', () => {
  const named = testFiles(noteTests);
  assert.ok(named.length >= 8, 'the note names its modules in backticks');
  for (const rel of named) assert.ok(fs.existsSync(path.join(REPO, rel)), `the note names ${rel}, which does not exist`);
});

for (const m of MODULES) {
  test(`${m.file} holds the pins the plan credits it with`, () => {
    assert.ok(fs.existsSync(path.join(REPO, m.file)), `${m.file} exists`);
    const src = read(...m.file.split('/'));
    for (const pin of m.holds) assert.ok(src.includes(pin), `${m.file} holds ${JSON.stringify(pin)}`);
  });
}

test('the Docs section records the guide\'s Files sentence for the margin layout, and the guide says it', () => {
  assert.ok(docs.includes('with the margin-layout follow-on (2026-09-07) it says that beside the file each card sits level with the passage it is about and scrolls with the text, and that a narrow column lists the cards (`tests/test_guide_files_margin_layout.py` holds the sentence to the panel and both sheets)'));
  const files = read('docs', 'guide.md');
  const at = files.indexOf('### Files');
  assert.ok(at >= 0, 'the guide has a Files section');
  assert.ok(files.slice(at).replace(/\s+/g, ' ').includes('where each card sits level with the passage it is about and scrolls with the text; when the column is narrow the panel drops below the file and lists the cards instead.'));
});
