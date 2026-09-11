// The focus follow-on's review (2026-09-08) found the plan's margin-layout note (plans/file-review.md, the Slice 2
// section) still stating as a live rule that cards are "pushed down in order and never up" and "only ever move down
// from their marks" — the rule the focus follow-on, a paragraph below it, amends (the card the person last acted on
// holds its mark and the cards above it move up, past their own marks where they must) — with nothing in the note
// qualifying either sentence or pointing at the amendment. Every other record had been amended (card-layout.ts's module
// comment, the sheets' comments, centerOn's), so the plan was the one place the old rule stood unqualified, and it is
// the record a reader implementing or reviewing against the margin layout reads first. The review also found the Docs
// section, the plan's record of what docs/guide.md says, carrying the margin follow-on's Files sentence and its pin but
// not the focus follow-on's, so the record and the guide disagreed; and the Open question on the loose group reasoning
// from the group standing at the top of the track when a focus can move it (the review's own fix then kept every card
// at or below the track's start, and the question says so). This module holds
// the three amended passages to the code and the guide, the way tools/file-review-plan-focus.test.mjs holds the focus
// paragraph itself. Synthetic: only the repo's own text.
// Run: node --test tools/file-review-plan-focus-review.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const read = (...p) => fs.readFileSync(path.join(REPO, ...p), 'utf8');
const plan = read('plans', 'file-review.md');
const layout = read('ui', 'webview', 'card-layout.ts');
const panel = read('ui', 'webview', 'file-comments.ts');
const guide = read('docs', 'guide.md');
const sheets = [['styles.css', read('ui', 'webview', 'styles.css')], ['feed.css', read('ui', 'webview', 'feed.css')]];

// The text between two markers, hard wraps collapsed so an assertion survives a rewrap.
function between(doc, from, to) {
  const a = doc.indexOf(from);
  assert.ok(a >= 0, `${JSON.stringify(from)} not found`);
  const b = doc.indexOf(to, a + from.length);
  assert.ok(b > a, `${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return doc.slice(a, b).replace(/\s+/g, ' ');
}
const MARGIN = 'The margin-layout follow-on (2026-09-07), panel side.';
const FOCUS = 'The focus follow-on (2026-09-08):';
const slice2 = between(plan, '### Slice 2: the session\'s changes as accept/reject cards and inline marks', '### Slice 3: region comments on images');
// The margin note, from its label to the focus paragraph: the ask and the design clause up to "Built:", then the Built account.
const note = between(slice2, MARGIN, FOCUS);
const builtAt = note.indexOf(' Built: ');
assert.ok(builtAt > 0, 'the margin note turns to what was built');
const design = note.slice(0, builtAt);
const built = note.slice(builtAt);
const focus = between(slice2, FOCUS, 'The anchors follow-on (2026-09-07):');
const tests = between(plan, '## Tests', '## Docs');
const docs = between(plan, '## Docs', '## Deliberately not in v1');
const open = between(plan, '## Open questions for the user', '## Upstream');
/** The guide's Files section (a `### Files` heading), up to the next heading of any level. */
const files = (() => {
  const m = /^### Files\n([\s\S]*?)(?=^#{2,3} )/m.exec(guide);
  assert.ok(m, 'the guide has a Files section');
  return m[1].replace(/\s+/g, ' ');
})();

/** The test files a run of prose names in backticks: a bare `*.test.ts` is a webview test, anything else a repo path. */
const testFiles = (s) => Array.from(s.matchAll(/`([^`\s]+\.(?:test\.ts|test\.mjs|py|bats))`/g), (m) => m[1])
  .map((n) => (n.includes('/') ? n : path.posix.join('ui', 'webview', n)));

// ── the margin note's rule, qualified by the focus and pointing at the paragraph that amends it ───────────────────

test('the design clause keeps the first cut\'s "never up" as the record of what was described, and says the focus follow-on below amends it', () => {
  // the attribution pin (tools/file-review-plan-attribution.test.mjs) reads this clause as the record of what the build
  // described to the user on 2026-09-07; the phrase stays, and a qualifier follows it in the same breath
  const at = design.indexOf('pushed down in order and never up');
  assert.ok(at > 0, 'the design clause still records the first cut\'s rule');
  assert.ok(design.startsWith('pushed down in order and never up (as first built; the focus follow-on, 2026-09-08, below, holds the card the person last acted on at its mark and moves the cards above it up)', at),
    'the phrase is qualified where it stands, not in a later sentence a reader may not reach');
  assert.ok(design.includes('and the passage centered only on a click'), 'the clause\'s tail still reads on');
  assert.equal(design.split('never up').length - 1, 1, 'the design clause says "never up" once, and that once is qualified');
});

test('the Built account states the push-down rule as holding without a focus, names what a focus does, and points at the paragraph', () => {
  const rule = 'so cards never overlap and, without a focus, only ever move down from their marks (with one — the card the person last acted on, which holds its mark — the cards above it move up, past their own marks where they must: the focus follow-on, 2026-09-08, below)';
  assert.ok(built.includes(rule), 'the rule is stated with its condition and its amendment');
  assert.equal(built.split('only ever move down').length - 1, 1, 'the account says "only ever move down" once, qualified');
  assert.ok(!built.includes('never up'), 'the Built account does not restate the first cut\'s rule unqualified');
  assert.ok(built.includes('a pushed card draws a dashed leader up the gutter to its mark\'s height, and a card the focus moved up one down'), 'both leaders');
  assert.ok(built.includes('the placed cards begin below it (a focus can move the group up from there; the focus follow-on says how)'), 'the loose group\'s place is qualified too');
  // the paragraph the note points at stands below it, under the same slice, and says what the note now says of it
  assert.ok(slice2.indexOf(MARGIN) < slice2.indexOf(FOCUS), 'the focus paragraph is below the margin note');
  assert.ok(focus.includes('The focused card sits exactly at its mark'));
  assert.ok(focus.includes('moved UP from the focus'));
  assert.ok(focus.includes('A card the focus moved up past its own mark draws its leader down the gutter (`data-pulled`, `--fc-pull`)'));
});

test('the qualified rule is the code\'s: the focused card at its mark, the cards above moved up, the leader down in the panel and both sheets, the old rule without a focus', () => {
  assert.ok(layout.includes('put(fit, focusTop);'), 'the focused card holds its mark');
  assert.ok(layout.includes('const top = Math.min(tops.get(it) as number, ceiling - it.height);'), 'a card above the focus moves up');
  assert.ok(layout.includes('negative, how far above it the focus moved it (below)'), 'the module comment amends its own "never up" the way the note now does');
  assert.ok(layout.includes('if (f < 0) {\n    for (const it of items) if (it.desired === null) put(it, floor);\n    for (const it of marked) put(it, Math.max(it.desired as number, floor));'), 'without a focus the push-down rule stands as the note\'s "without a focus" says');
  assert.ok(panel.includes('if (pull >= 1) { node.dataset.pulled = "1"; node.style.setProperty("--fc-pull", pull + "px"); }'), 'the panel marks a card the focus moved up');
  for (const [name, css] of sheets) {
    assert.ok(css.includes('.fc-margin .fc-card[data-pulled]::after {'), name + ': the leader down');
    assert.ok(css.includes('.fc-margin .fc-card[data-pushed]::before {'), name + ': the leader up');
  }
});

// ── the Docs section's record of the guide's Files paragraph ───────────────────────────────────────────────────────

test('the Docs section records the focus follow-on\'s Files sentence and its pin, after the margin follow-on\'s', () => {
  const marginAt = docs.indexOf('with the margin-layout follow-on (2026-09-07) it says that beside the file each card sits level with the passage it is about');
  const focusAt = docs.indexOf('with the focus follow-on (2026-09-08), that the card you click sits level with its passage whatever stands above it and that a long card folds to a few lines with Show more at its foot (`tests/test_guide_files_focus.py` holds the sentence to the panel, the layout rule and the sheets)');
  assert.ok(marginAt >= 0, 'the margin follow-on\'s record stands');
  assert.ok(focusAt > marginAt, 'the focus follow-on\'s record follows it, in the same Files item');
  assert.ok(focusAt < docs.indexOf('`docs/reference.md`'), 'inside the guide\'s item, before the reference doc\'s');
});

test('the record is the guide\'s: the Files section says both clauses, and the pin the record names exists and holds them', () => {
  assert.ok(files.includes('sits level with its passage whatever stands above it'), 'the guide says the clicked card sits level whatever stands above it');
  assert.ok(files.includes('folds to a few lines with **Show more** at its foot'), 'the guide says a long card folds, with Show more');
  const pin = path.join(REPO, 'tests', 'test_guide_files_focus.py');
  assert.ok(fs.existsSync(pin), 'tests/test_guide_files_focus.py exists');
  const py = fs.readFileSync(pin, 'utf8');
  assert.ok(py.includes('def test_the_card_you_click_sits_level_whatever_stands_above_it'), 'the pin holds the first clause to the panel and the layout');
  assert.ok(py.includes('def test_a_long_card_folds_to_a_few_lines_with_show_more'), 'the pin holds the second clause to the panel and the sheets');
  assert.ok(py.includes('def test_the_sheets_agree'), 'the pin holds the sheets to each other');
});

// ── the Open question on the loose group, with what a focus does to the group ─────────────────────────────────────

test('the Open question says a focus can move the loose group, as far as the track\'s start, with the cards at its end that do not fit laid below the focus, as the layout does', () => {
  assert.ok(open.includes('The focus follow-on (2026-09-08) adds to the question: the group joins the chain of cards a focus moves up, as far as the track\'s start, and the cards at its end that do not fit above the focused card are laid below it'));
  assert.ok(open.includes('the follow-on\'s review put every card at or below the start'));
  assert.ok(open.includes('stands at the top of the track'), 'the question still states the group\'s place without a focus');
  assert.ok(layout.includes('let keep = loose.length, shift = 0;'), 'the chain runs through the loose group as one');
  assert.ok(layout.includes('if ((tops.get(loose[0]) as number) - shift >= 0) break;'), 'and never past the start');
  assert.ok(layout.includes('for (const it of loose) if (spilled.has(it)) put(it, floor);'), 'the cards at its end that do not fit go below the focus');
  assert.ok(focus.includes('No card is moved past the start (the review, 2026-09-08)'), 'the focus paragraph says the same');
  const unit = read('ui', 'webview', 'card-layout.test.ts');
  assert.ok(unit.includes('test("the focus and the loose group:'), 'the rule\'s test covers the group');
  const reach = read('ui', 'webview', 'card-layout-reach.test.ts');
  assert.ok(reach.includes('test("the loose group moves up as one, as far as the track\'s start; past that, the cards at its end go below the focus'), 'and the reach test the start');
});

// ── this module, named where the plan names its pins ─────────────────────────────────────────────────────────────

test('the focus paragraph\'s Tests sentence and the Tests section\'s focus bullet name this module', () => {
  const self = 'tools/file-review-plan-focus-review.test.mjs';
  assert.ok(testFiles(focus).includes(self), 'the paragraph names it');
  const bulletAt = tests.indexOf('- The focus follow-on (2026-09-08): `card-layout.test.ts` gains the focus rule');
  assert.ok(bulletAt >= 0, 'the Tests section has the focus bullet');
  const bullet = tests.slice(bulletAt, tests.indexOf(' - The todo-file follow-on', bulletAt));
  assert.ok(testFiles(bullet).includes(self), 'the bullet names it');
});
