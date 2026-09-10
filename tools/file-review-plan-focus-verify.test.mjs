// The focus follow-on's verification review (2026-09-09) changed the layout rule and added two behavior modules, and its
// commit recorded neither in the plan's focus paragraph (plans/file-review.md, under the margin-layout note in the Slice 2
// section) nor in the Tests section's focus bullet, while it did record the centering fix and its pin in both places. The
// rule: a card laid below the focus stands above nothing, so the cards above are laid again without it until a pass
// moves no card past the start (card-layout.ts; card-layout-spill.test.ts). The modules: card-layout-spill.test.ts and
// file-comments-focus-verify.test.ts (the save's focus, the hosted comment's fold, a status's re-render). The plan's own
// pin (tools/file-review-plan-focus.test.mjs) holds a hand-written list of the modules the plan names, so an unnamed
// module passes it. This module holds the round's statements — the re-lay, the save's setter on scrollCard's path, the
// hosted parts under the fold — to the layout, the panel and the modules the plan credits, and scans the tree for every
// focus module, so a later round's module fails here by name, the way tools/file-review-plan-margin-review-3.test.mjs
// does for the margin family. Synthetic: only the repo's own text.
// Run: node --test tools/file-review-plan-focus-verify.test.mjs
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

// The text between two markers, hard wraps collapsed so an assertion survives a rewrap.
function between(doc, from, to) {
  const a = doc.indexOf(from);
  assert.ok(a >= 0, `${JSON.stringify(from)} not found`);
  const b = doc.indexOf(to, a + from.length);
  assert.ok(b > a, `${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return doc.slice(a, b).replace(/\s+/g, ' ');
}
const note = between(plan, 'The focus follow-on (2026-09-08):', 'The anchors follow-on (2026-09-07):');
const tests = between(plan, '## Tests', '## Docs');
const BULLET = '- The focus follow-on (2026-09-08): `card-layout.test.ts` gains the focus rule';
const bulletAt = tests.indexOf(BULLET);
assert.ok(bulletAt >= 0, 'the Tests section has the focus bullet');
const bullet = tests.slice(bulletAt, tests.indexOf(' - The todo-file follow-on', bulletAt));
const open = between(plan, '## Open questions for the user', '## Upstream');
/** The layout module's leading comment, its line markers dropped and its wraps collapsed. */
const layoutComment = layout.split('\n').filter((l) => l.startsWith('//')).map((l) => l.replace(/^\/\/ ?/, '')).join(' ').replace(/\s+/g, ' ');

/** The test files a run of prose names in backticks: a bare `*.test.ts` is a webview test, anything else a repo path. */
const testFiles = (s) => Array.from(s.matchAll(/`([^`\s]+\.(?:test\.ts|test\.mjs|py|bats))`/g), (m) => m[1])
  .map((n) => (n.includes('/') ? n : path.posix.join('ui', 'webview', n)));

// ── the re-lay ─────────────────────────────────────────────────────────────────────────────────────────────────────

test('the paragraph records the re-lay as the layout does: a card laid below the focus stands above nothing, the cards above laid again without it until a pass moves no card past the start', () => {
  assert.ok(note.includes('A card laid below the focus stands above nothing, so the cards above are laid again without it — the push-down rule, then the chain — until a pass moves no card past the start'));
  assert.ok(note.includes('a card the spilled card alone had pushed under its mark sits at its mark again, and a card under a spilled whole-file card takes the start the group gave up (the verification review, 2026-09-09'));
  assert.ok(note.includes('laid once, the card between a spilled tall card and the focus kept the push the tall card had given it in the push-down layout'), 'the record says what the rule fixed');
  // the layout: the spilled set, the passes over it, a spilled card skipped by the chain, the loop's end when no card was added
  assert.ok(layout.includes('const spilled = new Set<LayoutItem>();'), 'the set of cards laid below the focus');
  assert.ok(layout.includes('for (let grew = true; grew;) {'), 'the passes');
  assert.ok(layout.includes('for (const it of loose) if (!spilled.has(it)) { tops.set(it, floor); floor += it.height + gap; }'), 'the push-down rule without the spilled loose cards');
  assert.ok(layout.includes('for (const it of above) if (!spilled.has(it)) { const top = Math.max(it.desired as number, floor); tops.set(it, top); floor = top + it.height + gap; }'), 'and without the spilled marked cards');
  assert.ok(layout.includes('if (spilled.has(it)) continue;'), 'the chain skips a card a pass before laid below');
  assert.ok(layout.includes('grew = spilled.size > known;'), 'a pass that sent no card below is the last');
  assert.ok(layoutComment.includes('A card laid below the focus stands above nothing, so the cards above are laid again without it — the push-down rule, then the chain — until a pass moves no card past the start'), 'the module comment records the same rule');
  assert.ok(layoutComment.includes('(the verification round, 2026-09-09: laid once, the card between a spilled tall card and the focus kept the push the tall card had given it'));
});

test('the chain\'s clause is stated for the re-lay: a card the chain never reaches stays where the push-down rule laid it, not "where it was"', () => {
  assert.ok(note.includes('so a card the chain never reaches stays where the push-down rule laid it'), 'the clause names the pass\'s own push-down layout, which the re-lay changes');
  assert.ok(!note.includes('a card the focused card never met stays where it was'), 'the pre-re-lay phrasing is gone: laid again, a card can stand elsewhere than it did');
  assert.ok(note.includes('The cards below the focus follow the push-down rule from the end of the last card so displaced, as ever from a card\'s end. Without a focus the rule is unchanged'), 'the account of the cards below the focus reads on after the re-lay');
  assert.ok(layout.includes('const top = Math.min(tops.get(it) as number, ceiling - it.height);'), 'a card above the focus keeps its push-down top where the chain asks for no more');
});

// ── the save's focus ───────────────────────────────────────────────────────────────────────────────────────────────

test('the save\'s setter is recorded on scrollCard\'s path as the verification review had it; since decision 43 landSaved sets the focus itself, with no gesture before it, and scrollCard keeps its setter for the saved line\'s click', () => {
  assert.ok(note.includes('the save\'s is the one on `scrollCard`\'s path — `scrollToSaved` reaches it with no gesture before it, so a reply saved on an open card that is not the focus, pushed under a tall change card whose mark was clicked after the card opened, lands level with its mark and not where the push-down rule left it, a viewport below: the verification review, 2026-09-09'));
  assert.ok(note.includes('the card a save landed in'), 'the save stands among the focus setters the paragraph lists');
  assert.ok(/private landSaved\(c: Composer, had: Set<string>, r: Status, note: string\): boolean \{\n\s*const saved = [^\n]*\n\s*if \(saved === null\) return false;\n\s*const key = this\.cardKey\(saved\);\n\s*if \(this\.margin\) this\.focusOn\(key\);/.test(panel), 'landSaved makes the card the focus with no gesture of its own before it (the scroll it once made through scrollCard went with decision 43)');
  assert.ok(/scrollCard\(id: string\): void \{\n\s*if \(this\.margin && this\.revealMarks\(id\)\) this\.placeCards\(false\);[^\n]*\n\s*if \(this\.margin && this\.focusOn\(id\) && \(this\.centerOn\(id\) \|\| this\.showLoose\(id\)\)\) return;/.test(panel), 'scrollCard sets the focus first, after the one statement before it: the reveal of a mark inside a closed <details> (Slice 4 of plans/markdown-viewer.md), which is a DOM change and no gesture');
  assert.ok(panel.includes('save itself scrolled here (before decision 43) it was the one caller with no setter before it'), 'the panel\'s docstring says why the setter is here');
});

// ── the hosted comment's fold ──────────────────────────────────────────────────────────────────────────────────────

test('the parts under the fold are recorded as the pass reads them: every fc-clip under the card (the hosted comments\' among them until the about follow-on), lifted by the card\'s one Show more', () => {
  assert.ok(note.includes('the parts are every `fc-clip` under the card (until the about follow-on, 2026-09-10, a change card\'s hosted comments\' body and run of turns among them, so the card\'s one Show more lifted them with the change\'s text: the verification review, 2026-09-09'));
  assert.ok(note.includes('a pass reading the card\'s own children alone left a hosted run capped with no fade and, where the change\'s own text was short, no Show more at all'));
  assert.ok(note.includes('no comment is drawn inside a change card now'));
  assert.ok(panel.includes('for (const part of Array.from(card.querySelectorAll(".fc-clip")) as HTMLElement[]) {   // every part under the card'), 'clipCards reads the parts under the card, and says so');
  assert.ok(panel.includes('The parts are every `.fc-clip` UNDER the card, not the card\'s own children alone'), 'its docstring records the choice');
  assert.ok(!/renderHosted|fc-hosted/.test(panel), 'no hosted comment is rendered on a change card (the about follow-on)');
  for (const [name, css] of [['styles.css', read('ui', 'webview', 'styles.css')], ['feed.css', read('ui', 'webview', 'feed.css')]]) {
    assert.ok(css.includes('.fc-margin .fc-card:not(.fc-more) .fc-clip { max-height: 8lh; overflow: hidden; }'), name + ': one cap rule for every fc-clip under a card, hosted or the card\'s own');
  }
});

// ── the Open question ──────────────────────────────────────────────────────────────────────────────────────────────

test('the Open question on the loose group says what the re-lay does to the card under a spilled whole-file card', () => {
  assert.ok(open.includes('the follow-on\'s review put every card at or below the start, and the verification review, 2026-09-09, lays the cards a spilled card had pushed again without it, so the first passage\'s card takes the start a spilled whole-file card gave up'));
  const spill = read('ui', 'webview', 'card-layout-spill.test.ts');
  assert.ok(spill.includes('test("the loose group\'s spill: the first paragraph\'s card takes the start a spilled whole-file card gave up"'), 'the spill module pins that scene');
});

// ── the round's modules, named in both places and holding what the plan credits them with ─────────────────────────

const ROUND = [
  { file: 'ui/webview/card-layout-spill.test.ts', holds: [
    'test("the card between a spilled tall card and the focus is laid from its own mark, not from the push the spilled card gave it"',
    'test("two cards between the spilled card and the focus: the first at its mark, the second pushed only by the first"',
    'test("a card above the spilled one still pushes the card between: the push that stands is the one a card above it makes"',
    'test("the loose group\'s spill: the first paragraph\'s card takes the start a spilled whole-file card gave up"',
    'test("over a grid of fixtures: every pushed card sits a gap under the card placed above it — no leader claims a push no card makes — and the reach rule\'s invariants hold"',
  ] },
  { file: 'ui/webview/file-comments-focus-verify.test.ts', holds: [
    'test("a reply saved on an open card that is NOT the focus makes that card the focus: level with its mark, the tall change card above moved up',
    'test("a comment bound to a change folds on its OWN card (the about follow-on): its run of turns is marked cut and scrolled to its end, and the card\'s own Show more lifts it;',
    'test("the fold\'s choice survives a re-render a STATUS drives:',
    'test("vocabulary: this module\'s own prose says file comment and run of turns;',
  ] },
  { file: 'tools/file-review-plan-focus-centering.test.mjs', holds: [
    'test(\'the paragraph states the fallback\\\'s trigger as centerOn tests it:',
  ] },
  { file: 'tools/file-review-plan-focus-verify.test.mjs', holds: [
    'test(\'the paragraph records the re-lay as the layout does:',
  ] },
  // the round's second pass (the plan's paragraph credits it after the first round's modules, "from its second round")
  { file: 'ui/webview/file-comments-focus-verify-2.test.ts', holds: [
    'test("a head click on a loose card the reach rule laid below the focused card opens it where it stands: the focus stays on the card the person was reviewing',
    'test("Show more on a loose card laid below the focused card shows its text whole where it stands: the card wears fc-more and grows in place, the focus and the scroll stay',
    'test("a whole-file comment saved while a card is the focus: the new card joins the loose group\'s end below the focused card, the focus and the tall card\'s lift are kept',
    'test("the focus clears with the panel\'s close: a reopen lays the cards by the push-down rule',
    'test("the toggle is remembered for as long as the columns stay narrow: a repaint and a status while the list layout holds leave the keyboard on the card\'s head',
    'test("a busy Reject is remembered across a repaint during its round trip:',
  ] },
];

test('the paragraph\'s Tests sentence and the Tests section\'s bullet name every module the verification review added', () => {
  const inNote = new Set(testFiles(note)), inBullet = new Set(testFiles(bullet));
  for (const m of ROUND) {
    assert.ok(inNote.has(m.file), `the paragraph names ${m.file}`);
    assert.ok(inBullet.has(m.file), `the Tests bullet names ${m.file}`);
    assert.ok(fs.existsSync(path.join(REPO, m.file)), `${m.file} exists`);
  }
  const at = note.indexOf('from the verification review (2026-09-09), ');
  assert.ok(at >= 0, 'the paragraph credits the round');
  for (const m of ROUND) assert.ok(note.indexOf('`' + m.file.replace(/^ui\/webview\//, '') + '`', at) > at, `${m.file} is credited to the round, not to an earlier one`);
});

for (const m of ROUND) {
  test(`${m.file} holds the pins the plan credits it with`, () => {
    const src = read(...m.file.split('/'));
    for (const pin of m.holds) assert.ok(src.includes(pin), `${m.file} holds ${JSON.stringify(pin)}`);
  });
}

// ── the second round's statements: the loose focus, the keyboard's memory, the Show more row's place ───────────────

test('a loose focus is recorded as the pass has it: a focus with no mark leaves the pass\'s focus as it was (laidOn), cleared with the layout', () => {
  assert.ok(note.includes('A focus written on a LOOSE card — a whole-file comment\'s card opened by its head or its Show more, the card a whole-file comment\'s save landed in — leaves the pass\'s focus as it was: the pass keeps the card it laid the cards on last (`laidOn`)'));
  assert.ok(note.includes('a gesture on such a card moves nothing, as a head click on a loose card never did, and `layoutOff` clears the memory with the focus'));
  assert.ok(panel.includes('if (fit && fit.desired === null) this.focusCard = this.laidOn !== null && nodes.has(this.laidOn) ? this.laidOn : null;'), 'the pass falls back to the focus it laid the cards on last');
  assert.ok(panel.includes('this.laidOn = this.focusCard;'), 'and remembers the one it lays them on now');
  assert.ok(/this\.focusCard = null;[^\n]*\n\s*this\.laidOn = null;/.test(panel), 'layoutOff clears both');
  assert.ok(layout.includes('A focus with no mark, or one\n// not among the items, changes nothing.'), 'the rule takes a focus with no mark as none, as the paragraph says');
});

test('the keyboard\'s memory is recorded as refocus has it: re-armed for a control of the list while the keyboard stays where the panel put it, the composer\'s controls keeping the one render', () => {
  assert.ok(note.includes('The memory holds for as long as the control is in the list and the keyboard stays where the panel put it, however many renders pass — a repaint, a status — and a busy Accept or Reject is remembered the same way'));
  assert.ok(note.includes('the composer\'s controls keep the one render, since a save closes the box in the render after its Save comes back'));
  assert.ok(panel.includes('if (wf && document.activeElement === n && !this.composerBox.contains(wf)) this.wanted = { key: want!, at: n! };'), 'refocus re-arms the memory at the place the keyboard now holds, for a control outside the composer');
  assert.ok(panel.includes('The composer\'s controls keep the one render'), 'its docstring says why the composer is left out');
});

test('the Show more row\'s place is recorded as the renderers and placeComposer have it: at the card\'s foot above the action row, a reply\'s box between the row and the buttons', () => {
  assert.ok(note.includes('The row stands at the card\'s foot above the action row — on a comment\'s card under the run of turns, on a change card after its old and new text, above Accept and Reject — and a reply\'s box opened on the card stands between the row and the buttons (`placeComposer` puts it before `.fc-actions`)'));
  assert.ok(/card\.appendChild\(this\.clipRow\(c\.id\)\);[^\n]*\n\s*card\.appendChild\(acts\);/.test(panel), 'renderCard: the row, then the action row');
  assert.ok(/card\.appendChild\(diff\);\n\s*card\.appendChild\(this\.clipRow\(c\.key\)\);/.test(panel), 'renderChangeCard: the change\'s text, then the row');
  assert.ok(panel.includes('before(host, (Array.from(host.childNodes) as HTMLElement[]).find((n) => n.nodeType === 1 && n.classList.contains("fc-actions")) || null);'), 'placeComposer: the box before the action row, so after the row');
  const place = read('ui', 'webview', 'file-comments-reply-place.test.ts');
  assert.ok(place.includes('["fc-card-head", "fc-body fc-clip", "fc-replies fc-clip", "fc-clip-row", "fc-composer fc-composer-in", "fc-actions"]'), 'the reply-place stand-in asserts the order');
});

// ── the tree: every focus module named, so a round's module fails here by name ──────────────────────────────────────

test('every focus module in the tree is named by the paragraph and by the bullet: a later round\'s module fails here by name, not in a later consolidation', () => {
  const inNote = new Set(testFiles(note)), inBullet = new Set(testFiles(bullet));
  const web = fs.readdirSync(path.join(REPO, 'ui', 'webview')).filter((f) => /^(card-layout|file-comments-focus)[\w-]*\.test\.ts$/.test(f)).map((f) => path.posix.join('ui', 'webview', f));
  const tools = fs.readdirSync(path.join(REPO, 'tools')).filter((f) => /^file-review-plan-focus[\w-]*\.test\.mjs$/.test(f)).map((f) => path.posix.join('tools', f));
  const py = fs.readdirSync(path.join(REPO, 'tests')).filter((f) => /^test_guide_files_focus[\w-]*\.py$/.test(f)).map((f) => path.posix.join('tests', f));
  const all = [...web, ...tools, ...py];
  assert.ok(all.length >= 12, 'the scan reaches the family: ' + all.length);
  for (const f of all) {
    assert.ok(inNote.has(f), `${f} is in the tree but the paragraph's Tests sentence names it nowhere`);
    assert.ok(inBullet.has(f), `${f} is in the tree but the Tests section's focus bullet names it nowhere`);
  }
});
