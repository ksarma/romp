// The plan's focus follow-on paragraph (plans/file-review.md, under the margin-layout note in the Slice 2 section) records
// what the user hit (a tall change card above a comment pushed the comment's card a viewport below its highlight; the click
// scrolled the highlight to the body's top edge with no card beside it) and what was built (the focus the pass anchors the
// layout on, the leader down, the fold of a tall card). This module holds each statement of the paragraph to the code it
// describes — the layout rule, the panel, the sheets — and checks that every module the paragraph and the Tests section's
// bullet name exists and holds the pin the plan credits it with. Synthetic: only the repo's own text.
// Run: node --test tools/file-review-plan-focus.test.mjs
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

// The text between two markers, hard wraps collapsed so an assertion survives a rewrap.
function between(from, to) {
  const a = plan.indexOf(from);
  assert.ok(a >= 0, `${JSON.stringify(from)} not found in the plan`);
  const b = plan.indexOf(to, a + from.length);
  assert.ok(b > a, `${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return plan.slice(a, b).replace(/\s+/g, ' ');
}
const LABEL = 'The focus follow-on (2026-09-08):';
const note = between(LABEL, 'The anchors follow-on (2026-09-07):');
const tests = between('## Tests', '## Docs');
const BULLET = '- The focus follow-on (2026-09-08): `card-layout.test.ts` gains the focus rule';
const bulletAt = tests.indexOf(BULLET);
assert.ok(bulletAt >= 0, 'the Tests section has the focus bullet');
const bullet = tests.slice(bulletAt, tests.indexOf(' - The todo-file follow-on', bulletAt));

/** The test files a run of prose names in backticks: a bare `*.test.ts` is a webview test, anything else a repo path. */
const testFiles = (s) => Array.from(s.matchAll(/`([^`\s]+\.(?:test\.ts|test\.mjs|py|bats))`/g), (m) => m[1])
  .map((n) => (n.includes('/') ? n : path.posix.join('ui', 'webview', n)));

test('the paragraph stands under the margin-layout note, after its Tests sentence, and says what the user hit', () => {
  const slice2 = between('### Slice 2: the session', '### Slice 3: region comments on images');
  const marginAt = slice2.indexOf('The margin-layout follow-on (2026-09-07), panel side.');
  const focusAt = slice2.indexOf(LABEL);
  const anchorsAt = slice2.indexOf('The anchors follow-on (2026-09-07):');
  assert.ok(marginAt >= 0 && marginAt < focusAt && focusAt < anchorsAt, 'margin note, then the focus paragraph, then the anchors note');
  assert.ok(slice2.lastIndexOf(' Tests: ', focusAt) > marginAt, 'the margin note\'s Tests sentence stands before the paragraph, so the reviews\' modules still read that note\'s account');
  assert.ok(note.includes('the user clicked a comment\'s highlight and saw the highlight rise to the top edge of the body with no card beside it'));
  assert.ok(note.includes('the placement pass only ever pushed cards down, so the comment\'s card sat a full viewport below its highlight'));
});

test('the focus as stated is the code\'s: set before the render, given to the rule, the focused card at its mark, the cards above moved up by the least, the loose group joining the chain, cleared with the card, the layout and the panel', () => {
  assert.ok(note.includes('`layoutCards` takes it as its third argument'));
  assert.ok(/export function layoutCards\(items: LayoutItem\[\], gap: number = CARD_GAP, focus: string \| null = null\): Layout/.test(layout));
  assert.ok(note.includes('The focused card sits exactly at its mark (clamped to the top inset when the mark is under the header, as any first card is)'));
  assert.ok(layout.includes('const focusTop = Math.max(fit.desired as number, gap);'));
  assert.ok(note.includes('moved UP from the focus, each by the least that puts its end a gap above the card under it'));
  assert.ok(layout.includes('let ceiling = focusTop - gap;') && layout.includes('const top = Math.min(tops.get(it) as number, ceiling - it.height);') && layout.includes('ceiling = top - gap;'));
  assert.ok(note.includes('the loose group joins that chain when the moved cards reach it'));
  assert.ok(layout.includes('for (const it of [...above.slice().reverse(), ...loose.slice().reverse()])'), 'the chain runs up through the cards above and then the loose group');
  assert.ok(note.includes('Without a focus the rule is unchanged'));
  assert.ok(layout.includes('if (f < 0) {\n    for (const it of items) if (it.desired === null) put(it, floor);\n    for (const { it } of marked) put(it, Math.max(it.desired as number, floor));'), 'the old rule, verbatim, without a focus');
  assert.ok(note.includes('`focusOn`, which `goTo` and `scrollCard` call and which runs a pass when the focus changed'));
  assert.ok(/goTo\(key: string\): void \{\n\s*if \(this\.margin && this\.focusOn\(key\) && this\.centerOn\(key\)\) return;/.test(panel));
  assert.ok(/scrollCard\(id: string\): void \{\n\s*if \(this\.margin && this\.focusOn\(id\) && \(this\.centerOn\(id\) \|\| this\.showLoose\(id\)\)\) return;/.test(panel));
  assert.ok(/private focusOn\(key: string\): boolean \{[\s\S]*?if \(this\.focusCard !== key\) \{ this\.focusCard = key; this\.placeCards\(false\); \}/.test(panel));
  assert.ok(panel.includes('if (!wasOpen) this.focusCard = x.dataset.id;'), 'the head-click listener sets the focus for a card that opens');
  assert.ok(note.includes('The focus clears when the list no longer holds the card (a status, the filter, a fold), when the layout ends (`layoutOff`: the fold to the list, edit mode, the panel\'s close) and with the panel (`dispose`)'));
  assert.ok(panel.includes('if (this.focusCard !== null && !nodes.has(this.focusCard)) this.focusCard = null;'));
  assert.ok(/private layoutOff\(\): void \{[\s\S]*?this\.focusCard = null;[\s\S]*?\n  \}/.test(panel));
  assert.ok(/dispose\(\): void \{[\s\S]*?if \(this\.margin\) this\.layoutOff\(\);\n\s*this\.focusCard = null;/.test(panel));
});

test('the leader down, the centering fallback and the fold are as stated, in the panel and in both sheets', () => {
  assert.ok(note.includes('draws its leader down the gutter (`data-pulled`, `--fc-pull`)'));
  assert.ok(panel.includes('if (pull >= 1) { node.dataset.pulled = "1"; node.style.setProperty("--fc-pull", pull + "px"); }'));
  assert.ok(note.includes('the least-scroll fallback stays for a focused card taller than the track'));
  assert.ok(panel.includes('if (showCard > want) want = Math.min(showCard, markY - CARD_GAP);'), 'centerOn keeps the fallback');
  assert.ok(note.includes('the sheets cap each at eight of its lines (`8lh`)'));
  assert.ok(note.includes('(`clipCards`: `data-clipped`, read before the cards\' heights, since the fold changes them)'));
  assert.ok(/this\.moveRows\(kids\(\)\);\n\s*this\.clipCards\(kids\(\)\);/.test(panel));
  assert.ok(note.includes('Show more (`fcclip`, a `fileview-btn` through the delegate root, hidden as rendered until the pass finds a part cut)'));
  assert.ok(panel.includes('const b = btn(open ? "Show less" : "Show more", "fcclip");') && panel.includes('row.hidden = true;\n    return row;'));
  assert.ok(note.includes('keyed like the expand state (`openBodies`; the card wears `fc-more`)'));
  assert.ok(panel.includes('openBodies = new Set<string>();'));
  assert.ok(note.includes('Show more makes the card the focus and centers its mark, as opening a card does'));
  assert.ok(panel.includes('else { this.openBodies.add(key); this.focusCard = key; this.expandIntent = { key, wasOpen: false }; }'));
  assert.ok(note.includes('The list layout caps nothing'));
  for (const [name, css] of sheets) {
    assert.ok(css.includes('.fc-margin .fc-card:not(.fc-more) .fc-clip { max-height: 8lh; overflow: hidden; }'), name + ': the cap under fc-margin alone');
    assert.ok(css.includes('.fc-margin .fc-card[data-pulled]::after {'), name + ': the leader down');
  }
});

test('the modules the paragraph and the Tests bullet name exist, and hold the pins the plan credits them with', () => {
  const named = new Set([...testFiles(note), ...testFiles(bullet)]);
  for (const f of ['ui/webview/card-layout.test.ts', 'ui/webview/file-comments-focus.test.ts', 'ui/webview/file-comments-focus-browser.test.ts', 'tests/test_guide_files_focus.py', 'tools/file-review-plan-focus.test.mjs']) {
    assert.ok(named.has(f), 'the paragraph and the bullet name ' + f);
    assert.ok(fs.existsSync(path.join(REPO, f)), f + ' exists');
  }
  const unit = read('ui', 'webview', 'card-layout.test.ts');
  assert.ok(unit.includes('test("the focus: a tall card above a passage no longer pushes the passage\'s card down'));
  assert.ok(unit.includes('test("the focus and the loose group:'));
  assert.ok(unit.includes('test("the focus: no focus, a focus with no mark and an unknown focus each give the old result'));
  const driven = read('ui', 'webview', 'file-comments-focus.test.ts');
  assert.ok(driven.includes('test("a tall open change card above a comment: clicking the comment\'s highlight makes its card the focus'));
  assert.ok(driven.includes('test("the focus clears when the list no longer holds its card'));
  assert.ok(driven.includes('test("the focus clears on the fold to the list layout'));
  assert.ok(driven.includes('test("in the margin layout a long part is clipped'));
  const browser = read('ui', 'webview', 'file-comments-focus-browser.test.ts');
  assert.ok(browser.includes('for (const name of ["chromium", "firefox"])'));
  assert.ok(browser.includes('near(s.cards.c!.top, s.marks.c!.top, "the comment\'s card is level with its highlight (the defect: it sat a viewport below)");'));
  const guide = read('tests', 'test_guide_files_focus.py');
  assert.ok(guide.includes('The card you click sits level with its passage whatever stands above it'));
});
