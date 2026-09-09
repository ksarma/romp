// The review of the focus follow-on's merge-audit fixes (2026-09-09) changed Reveal's landing and added a module, and its
// commit recorded neither in the plan (plans/file-review.md, "The focus follow-on (2026-09-08)" under the margin-layout
// note in the Slice 2 section, and the Tests section's focus bullet). The landing: after scrollToOffset centers the Raw
// row, the revealed card is brought whole into the track's box where the switch's pass laid it on its Raw mark
// (settleRevealed: centerOn, the landing a click on the mark gives), so the body ends where centerOn puts it and not where
// the row's centering did; the module: file-comments-reveal-arms-focus.test.ts, which drives the pass revealInRaw runs
// itself, the comment's branch, the settling and Show changes inline off under plain node. The plan's tree scan
// (tools/file-review-plan-focus-verify.test.mjs) reads the names, `card-layout` and `file-comments-focus`, so a focus
// module named otherwise — this one, named for Reveal — passed it unnamed. This module holds the round's statements to the
// panel and the module, and scans the tree by what a module's header cites: every test file that names the focus
// paragraph is named by the paragraph's Tests sentence and by the bullet, whatever it is called. Synthetic: only the
// repo's own text.
// Run: node --test tools/file-review-plan-focus-audit.test.mjs
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

const PARAGRAPH = 'The focus follow-on (2026-09-08)';
const MODULE = 'ui/webview/file-comments-reveal-arms-focus.test.ts';
const MODULE_2 = 'ui/webview/file-comments-reveal-one-pass.test.ts';      // the review's second round: one pass per Reveal
const SELF = 'tools/file-review-plan-focus-audit.test.mjs';

// The text between two markers, hard wraps collapsed so an assertion survives a rewrap.
function between(doc, from, to) {
  const a = doc.indexOf(from);
  assert.ok(a >= 0, `${JSON.stringify(from)} not found`);
  const b = doc.indexOf(to, a + from.length);
  assert.ok(b > a, `${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return doc.slice(a, b).replace(/\s+/g, ' ');
}
const note = between(plan, PARAGRAPH + ':', 'The anchors follow-on (2026-09-07):');
const tests = between(plan, '## Tests', '## Docs');
const BULLET = '- The focus follow-on (2026-09-08): `card-layout.test.ts` gains the focus rule';
const bulletAt = tests.indexOf(BULLET);
assert.ok(bulletAt >= 0, 'the Tests section has the focus bullet');
const bullet = tests.slice(bulletAt, tests.indexOf(' - The todo-file follow-on', bulletAt));

/** The test files a run of prose names in backticks: a bare `*.test.ts` is a webview test, anything else a repo path. */
const testFiles = (s) => Array.from(s.matchAll(/`([^`\s]+\.(?:test\.ts|test\.mjs|py|bats))`/g), (m) => m[1])
  .map((n) => (n.includes('/') ? n : path.posix.join('ui', 'webview', n)));
/** A method's body, from its signature to the close of its indentation. */
const method = (sig) => { const at = panel.indexOf(sig); assert.ok(at >= 0, sig); return panel.slice(at, panel.indexOf('\n  }\n', at)); };

// ── the settling ───────────────────────────────────────────────────────────────────────────────────────────────────

test('the paragraph records the settling as the panel has it: after the row\'s centering, centerOn where the switch\'s pass laid the card on its Raw mark, the row\'s centering standing where it did not', () => {
  assert.ok(note.includes('The row\'s centering is then settled (`settleRevealed`; the review of the merge audit\'s fixes, 2026-09-09): where the switch\'s pass laid the card on its Raw mark, `centerOn` follows the row\'s centering with the landing a click on the mark gives — the mark centered, or the least scroll that shows the card\'s end, the fallback above'));
  assert.ok(note.includes('so the body ends where `centerOn` puts it, not where the row\'s centering did'), 'the record says the landing is centerOn\'s, not the row\'s centering');
  assert.ok(note.includes('where the pass laid the card on no mark (Show changes inline off: Raw paints none, and `landOn` cues the row) the row\'s centering stands, since `centerOn` has no mark to scroll to'));
  assert.ok(/private settleRevealed\(key: string\): void \{\n\s*if \(this\.margin && this\.laidOn === key\) this\.centerOn\(key\);\n\s*\}/.test(panel), 'settleRevealed: centerOn where the pass laid the cards on the revealed card, and only in the margin layout');
  assert.equal((panel.match(/this\.landOn\([^\n]*\);\n\s*this\.settleRevealed\(key\);/g) || []).length, 2, 'both branches of reveal() settle after the landing cue');
  assert.equal((panel.match(/this\.revealInRaw\(key\);\n\s*this\.ctx\.scrollToOffset\([^\n]*\);\n\s*this\.landOn\(/g) || []).length, 2, 'and on both the switch precedes the scroll, the scroll the cue');
  const doc = panel.slice(panel.lastIndexOf('/**', panel.indexOf('private settleRevealed(')), panel.indexOf('private settleRevealed(')).replace(/\s+\*\s+/g, ' ');
  assert.ok(doc.includes('(the review of the merge audit\'s fixes, 2026-09-09)'), 'the panel credits the round the plan credits');
  assert.ok(doc.includes('the row\'s own centering stands where the pass did not lay the card on a mark (laidOn: Show changes inline off'), 'and says where the row\'s centering stands');
  const reveal = panel.slice(panel.lastIndexOf('/**', panel.indexOf('  reveal(key: string): void {')), panel.indexOf('  reveal(key: string): void {')).replace(/\s+\*\s+/g, ' ');
  assert.ok(reveal.includes('the card is then brought whole into the track\'s box where the row\'s centering left its end past it (settleRevealed)'), 'reveal()\'s own docstring records the settling');
});

test('the two landings the record names are centerOn\'s: the mark centered, or the least scroll that shows the card\'s end, as far as keeps the mark\'s top in view', () => {
  const center = method('private centerOn(key: string): boolean {');
  assert.ok(center.includes('let want = markY - view / 2;'), 'the mark\'s top at the body\'s center');
  assert.ok(center.includes('const showCard = p.top + p.height + CARD_GAP - track.clientHeight;'), 'the least scroll that shows the card\'s end');
  assert.ok(center.includes('if (showCard > want) want = Math.min(showCard, markY - CARD_GAP);'), 'taken where the centering would leave the end past the box, capped where the mark\'s top would leave the body\'s');
  assert.ok(note.includes('the least-scroll fallback stays for a focused card taller than the track has room for below the centered mark'), 'the fallback the settling sentence points to stands above it in the paragraph');
  assert.ok(note.indexOf('the least-scroll fallback stays') < note.indexOf('The row\'s centering is then settled'), 'above it, so "the fallback above" reads on');
});

// ── the pass after the switch ──────────────────────────────────────────────────────────────────────────────────────

test('the pass after the switch is recorded on the guard revealInRaw has — where the switch ran none, read from the placement — and the row\'s centering stands where the switch\'s pass laid the card on no mark', () => {
  assert.ok(note.includes('Reveal arms the focus as well (`revealInRaw`; the merge audit, 2026-09-09): the card is made the focus before the switch to Raw, so the pass the viewer\'s `setMode` runs synchronously lays it level with its Raw mark before `scrollToOffset` centers the row'));
  assert.ok(note.includes('a pass runs after the switch where the switch ran none, and only there (a file with no Rendered view is Raw already, so the switch paints nothing; every pass ends by writing a new placement, `placed`, so the placement of before still standing after the switch says no pass ran — the review of the merge audit\'s fixes, round 2, 2026-09-09'));
  assert.ok(note.includes('the pass ran wherever the last pass had not laid the cards on the card, which with Show changes inline off, where Raw paints no mark and the switch\'s pass keeps the focus it had, was every change card\'s Reveal, the margin measured and written twice for one click'), 'the record says what the guard replaced, and what that cost');
  assert.ok(!note.includes('a pass runs after the switch where the switch painted nothing (a file with no Rendered view is Raw already). Before,'), 'the account that stopped at the paintless switch is gone');
  const rir = method('private revealInRaw(key: string): void {');
  assert.ok(/if \(this\.margin\) this\.focusCard = key;/.test(rir), 'the focus before the switch');
  assert.ok(/this\.focusCard = key;[^\n]*\n\s*const placed = this\.placed;[^\n]*\n\s*this\.ctx\.setMode\("raw"\);\n\s*if \(this\.margin && this\.placed === placed\) this\.placeCards\(false\);/.test(rir), 'the placement read before the switch, then a pass where the switch wrote no new one');
  assert.ok(!/this\.laidOn !== key/.test(rir), 'the guard on laidOn — a pass wherever the last one had not laid the cards on the card — is gone');
  assert.ok(method('placeCards(fromRender: boolean): void {').includes('this.placed = new Map(out.placed.map((p) => [p.key, p]));'), 'every pass ends by writing a new placement, which the guard reads');
  const doc = panel.slice(panel.lastIndexOf('/**', panel.indexOf('private revealInRaw(')), panel.indexOf('private revealInRaw(')).replace(/\s+\*\s+/g, ' ');
  assert.ok(doc.includes('so one runs here where the switch ran none, and only there: every pass ends by writing a new placement (placeCards: `placed`)'), 'its docstring states the guard');
  assert.ok(doc.includes('With Show changes inline off Raw paints no mark either, and the switch\'s pass falls to the focus it had'), 'and names the case that ran the margin twice');
  assert.ok(doc.includes('(the review of the audit\'s fixes, round 2, 2026-09-09)'), 'and credits the round the plan credits');
});

// ── the round's module, named in both places and holding what the record credits it with ───────────────────────────

const HOLDS = [
  'test("a file with no Rendered view (the seam\'s setMode returns without a paint, as file-view.ts\'s does off markdown): the deletion\'s card opened by its head, then the change card the focus from its mark and unfolded with Show more, the deletion\'s card pushed under it; Reveal on the deletion\'s card calls for Raw, gets no paint, and the pass revealInRaw runs itself lays the card level with its point, not pushed',
  'test("the comment\'s branch of Reveal: Rendered, a comment on an HTML comment block is loose (Reveal offered), the change card unfolded as the focus; Reveal on the comment\'s card writes the focus before the switch to Raw — the switch\'s own pass lays the card level with its Raw highlight — scrolls to the passage after the switch, over the Raw rows',
  'test("a revealed card taller than the room under the body\'s center (a short run of turns under the note): the row\'s centering alone left its end past the track\'s box; after it the body scrolls the least that shows the card\'s end',
  'test("with Show changes inline off, Reveal on the change card (offered: the view shows no mark for it) switches to Raw, where no mark is painted either: the pass keeps the focus it had (the passage\'s card, level with its highlight), the change card stays where the pass laid it, the row\'s centering stands with no settling after it, and the row wears the landing cue"',
  'test("vocabulary: this module\'s own prose says a change\'s old and new text, file comment and run of turns;',
];

test('the round\'s module is named in the paragraph\'s Tests sentence and the Tests section\'s bullet, credited to the round, exists, and holds the tests the record credits it with', () => {
  const inNote = new Set(testFiles(note)), inBullet = new Set(testFiles(bullet));
  for (const f of [MODULE, MODULE_2, SELF]) {
    assert.ok(inNote.has(f), `the paragraph names ${f}`);
    assert.ok(inBullet.has(f), `the Tests bullet names ${f}`);
    assert.ok(fs.existsSync(path.join(REPO, f)), `${f} exists`);
  }
  const at = note.indexOf('and from the review of the merge audit\'s fixes (2026-09-09), ');
  assert.ok(at >= 0, 'the paragraph credits the round');
  assert.ok(note.indexOf('`file-comments-reveal-arms-focus.test.ts`', at) > at, 'the module is credited to the round, not to the audit');
  assert.ok(bullet.includes('From the review of the merge audit\'s fixes (2026-09-09): `file-comments-reveal-arms-focus.test.ts`'), 'the bullet credits it to the round too');
  const src = read(...MODULE.split('/'));
  for (const pin of HOLDS) assert.ok(src.includes(pin), `${MODULE} holds ${JSON.stringify(pin.slice(0, 80))}`);
  assert.ok(src.includes(PARAGRAPH), 'the module\'s header cites the paragraph, so the header scan below reaches it');
  assert.ok(!/^(card-layout|file-comments-focus)[\w-]*\.test\.ts$/.test(path.posix.basename(MODULE)), 'and its name is the shape the name scan does not reach — the gap this module closes');
});

test('the round\'s second module — one pass per Reveal, the guard on the placement — is named in both places after the first, credited to the second round, exists, cites the paragraph and holds what the record credits it with', () => {
  const first = note.indexOf('`file-comments-reveal-arms-focus.test.ts`');
  const second = note.indexOf('and from its second round, `file-comments-reveal-one-pass.test.ts`', first);
  assert.ok(first >= 0 && second > first, 'the second round\'s module is credited after the first round\'s');
  assert.ok(bullet.includes('From its second round: `file-comments-reveal-one-pass.test.ts`'), 'the bullet credits it to the second round too');
  const src = read(...MODULE_2.split('/'));
  assert.ok(src.includes(PARAGRAPH), 'its header cites the paragraph');
  assert.ok(src.includes('the review of the merge audit\'s fixes, round 2, 2026-09-09'), 'and the round');
  assert.ok(src.includes('test("with Show changes inline off, from Raw: Reveal on the change card runs one pass, the switch\'s own, which finds the card loose and keeps the focus it had; no pass runs after the switch'), 'the marks off: the switch\'s pass is the only one');
  assert.ok(src.includes('test("a file with no Rendered view (the seam\'s setMode returns without a paint): the pass revealInRaw runs itself is the click\'s only pass'), 'no Rendered view: the pass revealInRaw runs is the only one');
  assert.ok(src.includes('test("the comment\'s branch, Rendered, a comment on an HTML comment block (loose in Rendered, marked in Raw): the switch\'s own pass lays the card level with its Raw highlight, and it is the click\'s only pass'), 'the comment\'s branch: the switch\'s pass is the only one');
  assert.ok(!/^(card-layout|file-comments-focus)[\w-]*\.test\.ts$/.test(path.posix.basename(MODULE_2)), 'named for Reveal too: the header scan is what reaches it');
});

// ── the tree, by the headers: every module that cites the paragraph is named, whatever it is called ────────────────

test('every test file whose text cites the focus paragraph is named by the paragraph\'s Tests sentence and by the bullet: a module named for its scene and not for the focus fails here', () => {
  const inNote = new Set(testFiles(note)), inBullet = new Set(testFiles(bullet));
  const cites = (dir, re) => fs.readdirSync(path.join(REPO, ...dir)).filter((f) => re.test(f))
    .filter((f) => read(...dir, f).includes(PARAGRAPH)).map((f) => path.posix.join(...dir, f));
  const all = [...cites(['ui', 'webview'], /\.test\.ts$/), ...cites(['tools'], /\.test\.mjs$/), ...cites(['tests'], /^test_[\w]+\.py$/)];
  assert.ok(all.includes(MODULE), 'the scan reaches the module that motivated it');
  assert.ok(all.includes(SELF), 'and this module');
  assert.ok(all.length >= 12, 'the scan reaches the family: ' + all.length);
  for (const f of all) {
    assert.ok(inNote.has(f), `${f} cites the paragraph but its Tests sentence names it nowhere`);
    assert.ok(inBullet.has(f), `${f} cites the paragraph but the Tests section's focus bullet names it nowhere`);
  }
});

test('the census claim the verify pin carries is qualified: a scan of the names, which the round\'s module passed unnamed until this one read the headers', () => {
  assert.ok(note.includes('a scan of the names, `card-layout` and `file-comments-focus`, which a focus module named otherwise passed unnamed: the module of the review of the merge audit\'s fixes, named for Reveal, until `tools/file-review-plan-focus-audit.test.mjs` below read the headers'));
  const verify = read('tools', 'file-review-plan-focus-verify.test.mjs');
  assert.ok(verify.includes('/^(card-layout|file-comments-focus)[\\w-]*\\.test\\.ts$/'), 'the verify pin\'s scan is the one the plan describes');
});
