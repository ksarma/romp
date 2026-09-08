// The plan's margin-layout note (plans/file-review.md, the Slice 2 section) carries a Built account, and the Tests
// section is the plan's record of where each mechanism is pinned. The follow-on's second review (2026-09-07) widened
// the footer's yield rule to every section but the track, in two tiers; dropped the header term from the scroll that
// shows an opened card's end; and made a save scroll to the card it landed in — and its commit, like the first
// round's, added test modules the plan did not name, while the account still described the footer as the first round
// built it (the Send section with its confirm up and the Log with its rows the only sections that yield) and the head
// and the composer as staying put (round 3). tools/file-review-plan-margin-review.test.mjs holds the first round's
// account and modules, and pins the first round's footer sentence verbatim; this module holds the second round's the
// same way: each statement the account makes is in the panel source or the sheets, the statement the round replaced
// is gone, and every module the round added is named in the note's Tests sentence and the Tests section's margin
// bullet, exists, and holds the pin the plan credits it with. Synthetic: only the repo's own text.
// Run: node --test tools/file-review-plan-margin-review-2.test.mjs
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

// The note's Built account, as the first round's module reads it: from "Built:" to the end of the Slice 2 section, its
// Tests sentence the tail.
const LABEL = 'The margin-layout follow-on (2026-09-07), panel side.';
const noteAt = slice2.indexOf(LABEL);
assert.ok(noteAt >= 0, 'the note is in the Slice 2 section');
const builtAt = slice2.indexOf(' Built: ', noteAt);
assert.ok(builtAt > noteAt, 'the note turns to what was built');
// …to the next follow-on note under Slice 2 (the todo-file follow-on's, then the filter follow-on's, in date order since main merged both branches), or the section's end
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

/** The file-comments block of a sheet, between the markers tests/test_guide_files_margin_layout.py reads. */
function fcBlock(css, name) {
  const a = css.indexOf('/* ── file comments panel (plans/file-review.md Slice 1; file-comments.ts)');
  const b = css.indexOf('/* ── end file comments panel ── */');
  assert.ok(a >= 0 && b > a, name + ': the file-comments block has both markers');
  return css.slice(a, b);
}

// ── the Built account, held to the sheets ─────────────────────────────────────────────────────────────────

test('the fixed parts are fixed in place, not in size: the "stay put" statement is gone, and both sheets let the head and the composer shrink and scroll', () => {
  assert.ok(!built.includes('The head and the composer stay put at the top'), 'the first round\'s statement, which the two tiers made incomplete, is gone');
  assert.ok(built.includes('The head and the composer sit at the top; Accept all · Reject all (moved out of the list), Send and the Log at the bottom, fixed in place while the track scrolls though not in size (the yield rule, below)'));
  for (const [name, css] of sheets) {
    assert.ok(/\.fc-margin > \.fc-sec-head, \.fc-margin > \.fc-composer \{ flex: 0 1 auto; min-height: 0; overflow: auto; padding: 10px 12px 0; \}/.test(css), name + ': the head and the composer shrink and scroll inside themselves');
    assert.ok(!/\.fc-margin > \.fc-sec-head \{ flex: 0 0 auto;/.test(css), name + ': the head is no longer fixed in size');
    assert.ok(!/\.fc-margin > \.fc-composer \{ flex: 0 0 auto;/.test(css), name + ': the composer is no longer fixed in size');
  }
});

test('the two tiers are stated with their floor and their reason, both sheets carry them, and the first round\'s keyed rule is gone', () => {
  assert.ok(built.includes('as the first review built it, a footer section that outgrows its share (the Send section with its confirm up, the Log with its rows) shrinks and scrolls inside itself'), 'the first round\'s rule stands in the account as history, not as the current rule');
  assert.ok(built.includes('The second review widened that yield to every section but the track, in two tiers, in both sheets (their file-comments blocks are held byte-equal)'));
  assert.ok(built.includes('the first rule left every other growth (the composer, the Track file/folder choice, the Reject all confirm, a refusal row under the foot, a fold row, the tooling warning) pushing Send and the Log toggle past the panel\'s bottom'), 'the reason: what the first rule did not cover');
  assert.ok(built.includes('a Tab onto one scrolled the clipped panel anyway, the head under the top edge and every card above its mark by that amount until the next pass'), 'the second reason: a focus scrolling the clipped panel');
  assert.ok(built.includes('Now the head, the composer, the Send section and the Log all shrink (`flex: 0 1 auto; min-height: 0`) and scroll inside themselves when they do'));
  assert.ok(built.includes('the sections holding what grew give first (the composer while it shows; the head, the Send section and the Log while they hold anything beyond their controls), their flex-shrink a million times the others\''));
  assert.ok(built.includes('down to a floor of one control row, or 15% of a panel too short for one (`min(15%, 2.4em)`'));
  assert.ok(built.includes('only then do the collapsed sections give, in proportion, scrolling too. The sections add up to the panel, always.'));
  for (const [name, css] of sheets) {
    assert.ok(/\.fc-margin > \.fc-sec-send, \.fc-margin > \.fc-sec-log \{ flex: 0 1 auto; min-height: 0; overflow: auto; padding: 0 12px; \}/.test(css), name + ': Send and the Log shrink and scroll inside themselves, grown or not');
    assert.ok(/\.fc-margin > \.fc-composer, \.fc-margin > \.fc-sec-head:has\(\.fc-head > :nth-child\(n\+2\):not\(\.fc-filter\)\),\s*\.fc-margin > \.fc-sec-send:has\(> :not\(\.fc-foot, \.fc-send\), \.fc-foot > :nth-child\(n\+2\), \.fc-send > :nth-child\(n\+2\):not\(\.fc-note\)\),\s*\.fc-margin > \.fc-sec-log:has\(\.fc-log > :nth-child\(n\+2\)\) \{ flex-shrink: 1000000; min-height: min\(15%, 2\.4em\); \}/.test(css), name + ': the grown tier — the composer, and each other section while it holds more than its controls — gives first, to the floor');
    assert.ok(!/\.fc-sec-send:has\(\.fc-confirm\), \.fc-margin > \.fc-sec-log:has\(\.fc-log-row\)/.test(css), name + ': the first round\'s rule keyed on the confirm and the rows is gone');
    assert.ok(/\.fc-margin > \.fc-sec-cards \{ flex: 1 1 0; min-height: 30%; position: relative; overflow: auto; scrollbar-width: none; \}/.test(css), name + ': the track keeps its basis and floor');
    assert.ok(/\.fc-panel\.fc-margin \{ overflow: hidden; padding: 0; gap: 0; \}/.test(css), name + ': the panel still clips');
  }
  // "in both sheets" is a claim about one block: the chat page loads styles.css, the feed page feed.css alone
  const [[, styles], [, feed]] = sheets;
  assert.ok(feed.includes(fcBlock(styles, 'styles.css')), 'feed.css carries styles.css\'s file-comments block byte-equal, so the account\'s "both sheets" is one rule');
});

// ── the Built account, held to the panel ──────────────────────────────────────────────────────────────────

test('the offset-free centering is stated and is the panel\'s: the scroll that shows a card\'s end is track content, with no header term', () => {
  assert.ok(built.includes('Where centering the mark would leave the card\'s end past the track\'s box (an open card, a pushed one), the body scrolls the least that shows the card\'s end, as far as keeps the mark\'s top in view'));
  assert.ok(built.includes('that scroll is track content, where the lock keeps the track\'s position the body\'s, so it carries no header term (`centerOn`)'));
  assert.ok(built.includes('an opened card that fit the track landed with its head (the fold control, the reference link) under the panel\'s header'), 'what the header term did');
  assert.ok(/private centerOn\(key: string\): boolean \{/.test(panel));
  assert.ok(/const showCard = p\.top \+ p\.height \+ CARD_GAP - track\.clientHeight;/.test(panel), 'the least scroll that shows the card\'s end, in track content');
  assert.ok(!/const showCard = p\.top \+ p\.height \+ offset - track\.clientHeight/.test(panel), 'the header term is gone');
  assert.ok(/if \(showCard > want\) want = Math\.min\(showCard, markY - CARD_GAP\);/.test(panel), 'as far as keeps the mark\'s top in view');
});

test('the save\'s scroll is stated and is the panel\'s: scrollToSaved before the composer closes, the comment read off the reply\'s store, a loose card shown by one write onto both scrollers', () => {
  assert.ok(built.includes('A comment saved while the text is scrolled scrolls to the card the save landed in, before the composer closes (`scrollToSaved`'));
  assert.ok(built.includes('the host names no id in its reply, so the new comment is read off the reply\'s store as the one the status before the write did not hold, `savedCommentId`'));
  assert.ok(built.includes('a loose card (a whole-file comment\'s, at the top of the track, where the lock keeps it out of view for a reader anywhere but the top of the text) is brought into the track\'s box by the least scroll that shows it, written onto the body and the track at once (`showLoose`, `scrollBoth`)'));
  assert.ok(built.includes('since a track-only `scrollIntoView` moved the track alone and the frame\'s `followBody` pass pulled it back to the body'), 'why scrollIntoView could not do it');
  assert.ok(built.includes('before that the composer closed and no card appeared, and the save read as having done nothing'), 'what stood before');
  assert.ok(/function savedCommentId\(had: Set<string>, r: Status, note: string\): string \| null \{/.test(panel));
  assert.ok(/private scrollToSaved\(c: Composer, had: Set<string>, r: Status, note: string\): void \{/.test(panel));
  assert.ok(/if \(r\) this\.scrollToSaved\(c, had, r, note\);[^\n]*\n\s*if \(r\) this\.closeComposer\(\);/.test(panel), 'the scroll runs before the composer closes');
  assert.ok(/private showLoose\(key: string\): boolean \{/.test(panel));
  assert.ok(/private scrollBoth\(want: number\): void \{/.test(panel));
  assert.ok(/if \(this\.margin && \(this\.centerOn\(id\) \|\| this\.showLoose\(id\)\)\) return;/.test(panel), 'scrollCard tries the mark first, then the loose group');
  assert.ok((panel.match(/this\.scrollBoth\(want\);/g) || []).length >= 2, 'centerOn and showLoose both write both scrollers through scrollBoth');
  assert.ok(!/scrollIntoView\(\{ block: "nearest" \}\);[^\n]*\n[^\n]*loose/.test(panel), 'no loose card is scrolled by scrollIntoView alone');
});

test('the account names the second review and what it changed, beside the first', () => {
  assert.ok(built.includes('The one range, the footer rows, the content observer, the placement order, the focus fixup, the escaping and the footer\'s yield rule are the follow-on\'s first review (2026-09-07)'), 'the first review\'s sentence stands');
  assert.ok(built.includes('The two tiers, the offset-free centering and the save\'s scroll are the follow-on\'s second review (2026-09-07)'));
  assert.ok(built.includes('which also found the sheets\' margin comment still attributing the level-with placement to the user and held it to this note\'s record'));
  assert.ok(built.includes('the pass without a render that un-pushes a card (the leader\'s attribute and its length leave the reused node) stood already and gained its pin in that round'));
  assert.ok(/else \{ delete node\.dataset\.pushed; node\.style\.removeProperty\("--fc-push"\); \}/.test(panel), 'the un-push, on the reused node');
  assert.ok(tests.includes('`ui/webview/styles-fc-margin-attribution.test.ts` holds each sheet\'s margin comment to the same record (the second review found the sheets still said the user had asked for what was built, 2026-09-07)'), 'the Tests section\'s attribution sentence names the sheets\' pin beside the plan\'s');
});

// ── the modules: named in the note and the Tests section, in the tree, holding the pin credited ───────────

/** Each module the second review added, the pin the plan credits it with (a test name's body), as the file spells it. */
const MODULES = [
  { file: 'ui/webview/styles-fc-margin-fit.test.ts', holds: [
    'test("styles.css: the head, the composer, the Send section and the Log all shrink and scroll inside themselves under .fc-margin"',
    'test("styles.css: the grown tier — the composer, and each other section while it holds more than its controls — gives first, down to a floor"',
    'test("styles.css: the track keeps its floor and the aside itself still clips',
    'a focus and a Tab onto Send and the Log leave the aside unscrolled and every card on its mark',
    'the collapsed controls alone outgrow the room, and still nothing leaves the aside',
  ] },
  { file: 'ui/webview/file-comments-margin-fixes.test.ts', holds: [
    'test("an opened card that fits the track is shown whole: the body scrolls the least that shows the card\'s end, and the card\'s head stays in the track\'s box',
    'test("a card taller than the track: brought in as far as its end, the clipping at its head the excess over the track\'s box alone',
    'test("a pass without a render un-pushes a card the pass no longer pushes: the leader\'s attribute and its length leave the reused node',
    'test("a whole-file comment saved with the text scrolled down: the new card — loose, at the top of the track, where the lock keeps it out of view — is brought into the track\'s box by the least scroll that shows it, written onto both scrollers at once; the composer closes after',
    'test("a reply saved on a card: the card is centered as an opened card is',
    'test("the saved comment is read off the reply\'s store: the one comment the status before the write did not hold; among several new ones (a retry after a moved fence), the one whose body is the note; none identifiable, nothing scrolls"',
    'test("at source: the scroll that shows a card\'s end is track content (no header term); the save scrolls to its card BEFORE the composer closes',
  ] },
  { file: 'ui/webview/file-comments-margin-fixes-browser.test.ts', holds: [
    'an opened card that fits the track lands whole in the track\'s box — its head under the header no more — after its head is clicked and after its reference link; a card taller than the track is clipped at its head by the excess alone',
    'a whole-file comment saved with the text scrolled far down brings its card into view (the track to the loose card at its top, the body with it); a reply saved brings the card to its mark; the composer closes after',
  ] },
  { file: 'ui/webview/styles-fc-margin-attribution.test.ts', holds: [
    'the margin layout\'s comment opens by naming the layout as the build\'s reading of the ask, not the user\'s ruling',
    'the ask in the clause carries its hedges and the centering the build did not do',
    'the clause says where the build departed from the ask, and where the plan records both',
    'the comment nowhere attributes level-with placement to the user',
  ] },
  { file: 'tools/file-review-plan-margin-review-2.test.mjs', holds: ['the second review'] },
];

test('every module the second review added is named in the note\'s Tests sentence and in the Tests section\'s margin bullet', () => {
  const inNote = new Set(testFiles(noteTests));
  const inBullet = new Set(testFiles(bullet));
  for (const m of MODULES) {
    assert.ok(inNote.has(m.file), `the note's Tests sentence names ${m.file}`);
    assert.ok(inBullet.has(m.file), `the Tests section's margin bullet names ${m.file}`);
  }
});

test('the note\'s Tests sentence and the margin bullet name the first round\'s modules still, beside the second\'s', () => {
  for (const f of ['ui/webview/file-comments-margin-review.test.ts', 'ui/webview/styles-fc-margin-footer.test.ts', 'ui/webview/feed-css-margin-leader.test.ts', 'tools/file-review-plan-margin-review.test.mjs']) {
    assert.ok(testFiles(noteTests).includes(f), `the note's Tests sentence names ${f}`);
    assert.ok(testFiles(bullet).includes(f), `the margin bullet names ${f}`);
  }
});

for (const m of MODULES) {
  test(`${m.file} holds the pins the plan credits it with`, () => {
    assert.ok(fs.existsSync(path.join(REPO, m.file)), `${m.file} exists`);
    const src = read(...m.file.split('/'));
    for (const pin of m.holds) assert.ok(src.includes(pin), `${m.file} holds ${JSON.stringify(pin)}`);
  });
}
