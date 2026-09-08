// The plan's margin-layout note (plans/file-review.md, the Slice 2 section) carries a Built account, and the Tests
// section is the plan's record of where each mechanism is pinned. The follow-on's third review (2026-09-07) mirrored
// the second review's two tiers into feed.css (they had reached styles.css alone); made the pass take the body's end
// padding back where it bought no scroll range (a centered picture and a short Raw file shifted at every open and close
// of the panel); and held the panel's own section comment to the attribution record the plan and the sheets already
// kept. Its commit, like the two before it, added test modules the plan did not name, and wrote round 2 into the
// account while saying nothing of its own round. The review also confirmed the loose group's place as a finding and
// left it to the user (a pinned band for the loose cards is a new surface): the plan's Open questions carry it.
// tools/file-review-plan-margin-review.test.mjs holds the first round's account and modules, -2 the second's; this
// module holds the third's the same way: each statement the account makes is in the panel source or the sheets, the
// open question describes the code as it is, and every module the round added is named in the note's Tests sentence
// and the Tests section's margin bullet, exists, and holds the pin the plan credits it with. Synthetic: only the
// repo's own text.
// Run: node --test tools/file-review-plan-margin-review-3.test.mjs
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
const layout = read('ui', 'webview', 'card-layout.ts');
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
const open = section('## Open questions for the user', '## Upstream');

// The note's Built account, as the first round's module reads it: from "Built:" to the note's end, its Tests sentence
// the tail.
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

/** The file-comments block of a sheet, between the markers tests/test_guide_files_margin_layout.py reads. */
function fcBlock(css, name) {
  const a = css.indexOf('/* ── file comments panel (plans/file-review.md Slice 1; file-comments.ts)');
  const b = css.indexOf('/* ── end file comments panel ── */');
  assert.ok(a >= 0 && b > a, name + ': the file-comments block has both markers');
  return css.slice(a, b);
}

// ── the Built account, held to the panel ──────────────────────────────────────────────────────────────────

test('the padding take-back is stated with its reason and is the pass\'s: written, measured, cleared where the body gained no range', () => {
  assert.ok(built.includes('there the track goes on alone as far as the last card\'s end, and a pass or a status reply leaves it there instead of pulling it back to the body (`followBody`)'), 'the first round\'s sentence stands');
  assert.ok(built.includes('Such padding is taken back in the pass that wrote it: a box\'s padding comes out of its content box, and content sized to the box by a `min-height: 100%`'));
  assert.ok(built.includes('a centered picture rose by half the footer at every open of the panel and fell back at the close, on no new information about it'), 'what the padding did before: a card move on no new information, in the plan\'s own terms');
  assert.ok(built.includes('the pass writes the padding, measures, and clears it where the body\'s scroll height is still its box\'s'));
  assert.ok(built.includes('keeps it where the body did lengthen (a picture nearly the box\'s height, whose own box outgrows the padded content box'));
  assert.ok(/const scrolls = body\.scrollHeight > body\.clientHeight;/.test(panel), 'whether the body scrolls, read before the write');
  assert.ok(/const content = scrolls \? body\.scrollHeight - this\.bodyPad : null;/.test(panel), 'the content\'s height is known only while the body scrolls');
  assert.ok(/this\.padBody\(body, Math\.ceil\(footer \+ hang\)\);\s*\n\s*if \(!scrolls && body\.scrollHeight <= body\.clientHeight\) this\.padBody\(body, 0\);/.test(panel), 'written, then taken back the same pass where it bought no range');
});

// ── the third review, held to the sheets and the panel ────────────────────────────────────────────────────

test('the account names the third review and what it changed, beside the first two; the sheets are one block again and the attribution is the record\'s in all three files', () => {
  assert.ok(built.includes('The two tiers, the offset-free centering and the save\'s scroll are the follow-on\'s second review (2026-09-07)'), 'the second review\'s sentence stands');
  assert.ok(built.includes('The third review (2026-09-07) found the two tiers had reached styles.css alone, the feed page\'s sheet still carrying the first cut while the byte-equal pins stood red, and mirrored the block into feed.css'));
  assert.ok(built.includes('found the padding\'s shift of a centered picture and of a short Raw file, and made the pass take the padding back where it bought no range'));
  assert.ok(built.includes('found the panel\'s own section comment still attributing the level-with placement to the user, and held it to this note\'s record as the sheets\' had been'));
  const [[, styles], [, feed]] = sheets;
  assert.ok(feed.includes(fcBlock(styles, 'styles.css')), 'feed.css carries styles.css\'s file-comments block byte-equal');
  const OPENS = '/* the margin layout (the build\'s reading, not a ruling, of the user\'s 2026-09-07 ask after walking the loop';
  for (const [name, css] of sheets) {
    assert.ok(fcBlock(css, name).includes(OPENS), name + ': the margin comment opens as the build\'s reading');
    assert.ok(!css.includes('(the user 2026-09-07, after walking the loop'), name + ': the ruling-shaped attribution is gone');
  }
  assert.ok(panel.includes('// ── the margin layout (the build\'s reading, not a ruling, of the user\'s 2026-09-07 ask after walking the loop'), 'the panel\'s section comment opens the same way');
  assert.ok(!panel.includes('(the user 2026-09-07, after walking the loop'), 'the panel carries the ruling-shaped attribution nowhere');
});

// ── the loose group's place: an open question that describes the code as it is ────────────────────────────

test('the loose group\'s place stands under Open questions, named from the account, and describes the layout as built: loose first, from the top of the track, no band', () => {
  assert.ok(built.includes('The loose group\'s place — cards with no mark at the top of the track, out of view for a reader anywhere else — is the third review\'s one finding left to the user\'s word, under Open questions'));
  assert.ok(open.includes('The margin layout (the follow-on note under Slice 2) awaits the user\'s word: it is the build\'s reading of the ask, not a ruling, and the walk answers it'), 'the attribution test\'s sentence stands');
  assert.ok(open.includes('With it, the loose group\'s place: a card with no mark (a whole-file comment, a change the Rendered view cannot paint, a detached anchor, a region whose figure has not loaded) stands at the top of the track, which the lock keeps out of view for a reader anywhere but the top of the text'));
  assert.ok(open.includes('proposed a pinned band between the composer and the track for those cards, in the list\'s order, with its own scroll and a fold beyond a few — a new surface, so it waits for the same word rather than landing with the review\'s fixes'));
  assert.ok(open.includes('(the save\'s scroll, `showLoose`, already brings a whole-file comment\'s card into view)'));
  // the code the question describes: the pure rule puts the loose group first, from the top; the panel scrolls a saved
  // loose card into view; and no band exists — the day one does, this question is answered and belongs under Decisions
  assert.ok(/for \(const it of items\) if \(it\.desired === null\) put\(it, floor\);/.test(layout), 'card-layout.ts: the loose group first, from the top of the track');
  assert.ok(/private showLoose\(key: string\): boolean \{/.test(panel));
  assert.ok(!/sections\.loose|fc-sec-loose/.test(panel), 'the panel has no loose band: when it does, the question under Open questions is answered — move it to Decisions and re-pin');
  for (const [name, css] of sheets) assert.ok(!css.includes('fc-sec-loose'), name + ': no band rule either');
});

// ── the modules: named in the note and the Tests section, in the tree, holding the pin credited ───────────

/** Each module the third review added, the pin the plan credits it with (a test name's body), as the file spells it. */
const MODULES = [
  { file: 'ui/webview/feed-css-margin-fit.test.ts', holds: [
    'test("feed.css: the head, the composer, the Send section and the Log all shrink and scroll inside themselves under .fc-margin"',
    'test("feed.css: the grown tier — the composer, and each other section while it holds more than its controls — gives first, down to a floor"',
    'test("feed.css: the track keeps its floor and the aside itself still clips',
    'test("styles.css: the chat page\'s sheet holds the same margin rules — a fix that reaches one sheet alone fails here by name"',
    'under feed.css: a 330px panel',
    'under feed.css: a 500px panel with every row up',
    'under feed.css: a 200px panel',
  ] },
  { file: 'ui/webview/file-comments-margin-image-pad.test.ts', holds: [
    'test("a picture shorter than the box: the footer\'s padding buys the body no scroll range, so the pass takes it back, and the picture stays where the box centered it',
    'test("with no comment yet the footer holds the empty note too: the verdict is the same, the picture stays put"',
    'test("a picture nearly the box\'s height: the padding lengthens the body (the picture\'s own box outgrows the padded content box), so it stays',
    'test("a short file (the Raw view\'s box has the same min-height): the padding bought no range and is taken back; a file that scrolls keeps the footer\'s padding as before"',
    'test("at source: the pass writes the footer\'s padding, then takes it back where the body gained no range"',
  ] },
  { file: 'ui/webview/file-comments-margin-image-browser.test.ts', holds: [
    'a picture shorter than the body\'s box — opening the Comments panel leaves the picture where the box centered it (the footer\'s padding, which bought no scroll range, is taken back), with its card level with the rectangle; closing changes nothing',
    'a picture nearly the body\'s height — the footer\'s padding lengthens the body (its own box outgrows the padded content box), so it stays and the body scrolls; the close gives the picture its centered place back',
  ] },
  { file: 'ui/webview/file-comments-margin-attribution.test.ts', holds: [
    'test("the panel\'s margin-layout comment opens by naming the layout as the build\'s reading of the ask, not the user\'s ruling"',
    'test("the ask in the clause carries its hedges and the centering the build did not do"',
    'test("the clause says where the build departed from the ask, where the plan records both, and that the user\'s word is still to come"',
    'test("the comment nowhere attributes level-with placement to the user"',
    'test("the panel source carries the old clause nowhere else"',
  ] },
  { file: 'tools/file-review-plan-margin-review-3.test.mjs', holds: ['the third review'] },
  // the review's consolidation: the footer's rule moved from the foot to the Send section's edge
  { file: 'ui/webview/feed-css-margin-footer-rule.test.ts', holds: [
    'test("both sheets: the footer\'s rule stands on the Send section\'s top edge, after the shared rule it overrides; the Send box drops its own when first; the foot\'s rule is gone"',
    'the footer begins under one hairline whichever row comes first — the Send box alone, the Resolved fold, the foot — and the Send box wears its own only behind a row',
  ] },
];

test('the footer\'s rule is stated and is the sheets\': on the Send section\'s edge, the Send box\'s own dropped when first, the foot\'s gone', () => {
  assert.ok(built.includes('The footer begins under a rule whichever row comes first: the rule stands on the Send section\'s top edge in both sheets, and the Send box drops its own when nothing stands before it'));
  assert.ok(built.includes('the first review\'s rule stood on the foot alone, so a footer of rows with no pending change — a comments-only file with a resolved comment — began flush under the track\'s clipped cards and drew its one rule under the fold, above Send'), 'what stood before, so the rule is not read as taste');
  for (const [name, css] of sheets) {
    const block = fcBlock(css, name);
    assert.ok(block.includes('\n.fc-margin > .fc-sec-send { padding-top: 8px; border-top: 1px solid var(--card-border); }'), name + ': the rule on the section\'s edge');
    assert.ok(block.includes('\n.fc-margin .fc-sec-send > .fc-send:first-child { padding-top: 0; border-top: 0; }'), name + ': the Send box\'s own dropped when first');
    assert.ok(!/\.fc-sec-send > \.fc-foot \{/.test(block), name + ': the first review\'s rule on the foot is gone');
  }
  assert.ok(!panel.includes('the sheet\'s border-top stands on it'), 'the panel\'s moveRows comment no longer says the rule stands on the foot');
});

test('every module the third review added is named in the note\'s Tests sentence and in the Tests section\'s margin bullet', () => {
  const inNote = new Set(testFiles(noteTests));
  const inBullet = new Set(testFiles(bullet));
  for (const m of MODULES) {
    assert.ok(inNote.has(m.file), `the note's Tests sentence names ${m.file}`);
    assert.ok(inBullet.has(m.file), `the Tests section's margin bullet names ${m.file}`);
  }
});

test('the note\'s Tests sentence and the margin bullet name the first two rounds\' modules still, beside the third\'s', () => {
  for (const f of ['ui/webview/file-comments-margin-review.test.ts', 'ui/webview/styles-fc-margin-footer.test.ts', 'ui/webview/feed-css-margin-leader.test.ts', 'tools/file-review-plan-margin-review.test.mjs',
    'ui/webview/styles-fc-margin-fit.test.ts', 'ui/webview/file-comments-margin-fixes.test.ts', 'ui/webview/file-comments-margin-fixes-browser.test.ts', 'ui/webview/styles-fc-margin-attribution.test.ts', 'tools/file-review-plan-margin-review-2.test.mjs']) {
    assert.ok(testFiles(noteTests).includes(f), `the note's Tests sentence names ${f}`);
    assert.ok(testFiles(bullet).includes(f), `the margin bullet names ${f}`);
  }
});

test('every margin module in the tree is named by the plan: a fourth round\'s modules fail here by name, not in a later consolidation', () => {
  const named = new Set([...testFiles(noteTests), ...testFiles(bullet)]);
  const inTree = fs.readdirSync(path.join(REPO, 'ui', 'webview')).filter((f) => /margin/.test(f) && /\.test\.ts$/.test(f)).map((f) => path.posix.join('ui', 'webview', f));
  const tools = fs.readdirSync(path.join(REPO, 'tools')).filter((f) => /margin/.test(f) && /\.test\.mjs$/.test(f)).map((f) => path.posix.join('tools', f));
  for (const f of [...inTree, ...tools]) assert.ok(named.has(f), `${f} is in the tree but the plan's note and Tests bullet name it nowhere`);
});

for (const m of MODULES) {
  test(`${m.file} holds the pins the plan credits it with`, () => {
    assert.ok(fs.existsSync(path.join(REPO, m.file)), `${m.file} exists`);
    const src = read(...m.file.split('/'));
    for (const pin of m.holds) assert.ok(src.includes(pin), `${m.file} holds ${JSON.stringify(pin)}`);
  });
}
