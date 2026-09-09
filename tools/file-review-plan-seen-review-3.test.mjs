// The seen follow-on's third review round (2026-09-09): the plan sentences that round found stale, held to the code.
//
// The first round's fix moved the list layout's saved line under the panel's header (savedLineHead: the list under a narrow
// column scrolls the whole panel, so its Send section is below the very card the line says is below, and a line there was
// never on screen when it was wanted) and made a Tab or a modifier pressed alone no gesture (NAV_KEYS: counted as gestures
// they ended the line before the keyboard could reach it). The second round corrected the guide for the first and left the
// plan alone, and neither round recorded the second anywhere but a commit message. So the plan claimed the acknowledgment
// line's position at the panel's foot for both layouts, in the arrivals paragraph, decision 43 and the Docs sentence, and
// "a key anywhere in the body row" as a gesture without exception, and no pin held either to the code: the seen-review pin
// ties the foot sentences to renderSend alone, and tests/test_guide_files_save_line.py derives the gesture words from the
// constructor's listeners, which the key filter never touches. The same round found "the sent note's" in the arrivals Tests
// bullet, wrapped across a line so the raw-text scans (tests/test_context_send_note.py, the seen-review pin) passed over it,
// after CONTEXT.md's Note entry says the acknowledgment is not a note; and the Tests bullet naming none of the rounds' own
// modules. A record that contradicts the code costs the next reader the search it was meant to save, so this module holds
// each corrected sentence to the source that makes it true. Synthetic: only the repo's own text.
// Run: node --test tools/file-review-plan-seen-review-3.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');

const plan = read('plans', 'file-review.md');
const panel = read('ui', 'webview', 'file-comments.ts');
const guide = read('docs', 'guide.md');
const context = read('CONTEXT.md');
const review2 = read('ui', 'webview', 'file-comments-seen-review2.test.ts');

// The text between two markers with hard wraps collapsed, so an assertion survives a rewrap; the markers are matched on
// the collapsed text too, since a sentence can wrap anywhere.
const flat = (s) => s.replace(/\s+/g, ' ');
const FLAT = flat(plan);
function between(from, to) {
  const a = FLAT.indexOf(from);
  assert.ok(a >= 0, `${JSON.stringify(from)} not found`);
  const b = FLAT.indexOf(to, a + from.length);
  assert.ok(b > a, `${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return FLAT.slice(a, b);
}
// A function's body: from its signature to the first line holding only the closing brace at its indent.
function body(src, sig) {
  const a = src.indexOf(sig);
  assert.ok(a >= 0, `${JSON.stringify(sig)} not found`);
  const indent = /(\s*)$/.exec(src.slice(0, a))[1].replace(/^\n/, '');
  const b = src.indexOf('\n' + indent + '}\n', a);
  assert.ok(b > a, `no end for ${JSON.stringify(sig)}`);
  return src.slice(a, b);
}
const SEEN = 'The seen follow-on (2026-09-09):';
const ARRIVALS = 'The arrivals follow-on (2026-09-09):';
const seen = between(SEEN, ARRIVALS);
const arrivals = between(ARRIVALS, '### Slice 3: region comments on images');
const d43 = between('43. **A save never moves the view; a line says where the card is**', '## Open questions for the user');
const tests = between('## Tests', '## Docs');
const docs = between('## Docs', '## Deliberately not in v1');
const seenBullet = tests.slice(tests.indexOf('- The seen follow-on (2026-09-09):'), tests.indexOf('- The todo-file follow-on (2026-09-07):'));
const arrivalsBullet = tests.slice(tests.indexOf('- The arrivals follow-on (2026-09-09):'), tests.indexOf('- The seen follow-on (2026-09-09):'));

test('the saved line\'s place is stated by layout wherever the plan states it: the margin layout\'s foot and the list layout\'s header, in the arrivals paragraph, decision 43 and the Docs sentence', () => {
  // the arrivals paragraph: the foot for the margin layout, the header for the list, each with its function
  assert.ok(arrivals.includes('in the margin layout the acknowledgment line\'s position at the panel\'s foot reads "Saved · the card is above" or "below" (`savedLine`'));
  assert.ok(arrivals.includes('in the list layout the same button stands under the header (`savedLineHead`, appended by `renderHead`), since the list\'s Send section is the scroller\'s foot, below the very card the line says is below'));
  assert.ok(arrivals.includes('an earlier send\'s acknowledgment keeps its place at the foot there where the margin layout\'s gives way to the line'));
  // decision 43: the same two places, in the guide's words for the layouts
  assert.ok(d43.includes('in the margin layout the acknowledgment line\'s position at the panel\'s foot reads "Saved · the card is above" or "below", a button whose click scrolls the card into view, and in the list under a narrow column the same button stands under the panel\'s header'));
  // the Docs sentence: the guide's list-layout sentence and the module that holds it
  assert.ok(docs.includes('and that in the list under a narrow column the line stands under the panel\'s header instead (`tests/test_guide_files_saved_line_layout.py` holds that sentence to the panel\'s placement by layout, the sheets and the panel\'s tests of both placements)'));
  // no account of the line claims the foot without naming the layout: each text that says "foot" for the saved line says "header" for the list too
  for (const [name, text] of [['the arrivals paragraph', arrivals], ['decision 43', d43], ['the Docs sentence', docs]]) {
    assert.ok(text.includes('panel\'s foot') && (text.includes('under the panel\'s header') || text.includes('under the header')), name + ' names both places');
  }
});

test('the panel places the line as the plan says: one button, in the Send section with the margin on and under the header with it off, and the acknowledgment gives way in the margin layout alone', () => {
  assert.ok(/private savedLine\(\): HTMLElement \| null \{\n\s*return this\.margin \? this\.savedButton\(\) : null;/.test(panel), 'the margin layout\'s line');
  assert.ok(/private savedLineHead\(\): HTMLElement \| null \{\n\s*return this\.margin \? null : this\.savedButton\(\);/.test(panel), 'the list layout\'s');
  const send = body(panel, 'private renderSend(');
  const line = send.indexOf('const saved = this.savedLine();');
  const placed = send.indexOf('if (saved) box.appendChild(saved);', line);
  const ack = send.indexOf('if (this.sentNote) box.appendChild(el("div", "fc-note fc-sent", this.sentNote));', placed);
  assert.ok(line >= 0 && placed > line && ack > placed, 'the Send section appends the margin layout\'s line in the acknowledgment\'s position');
  assert.ok(/const saved = this\.savedLineHead\(\);\n\s*if \(saved\) head\.appendChild\(saved\);\n\s*return head;/.test(panel), 'the head appends the list layout\'s, last');
  assert.equal(panel.match(/this\.savedButton\(\)/g).length, 2, 'one builder, two places');
  const land = body(panel, 'private landSaved(c: Composer, had: Set<string>, r: Status, note: string): boolean {');
  // every write of the acknowledgment in the landing is under the margin's guard: the line takes its position there, and in the list the acknowledgment stays
  const writes = land.split('\n').filter((l) => /this\.sentNote\s*=/.test(l.replace(/\/\/.*$/, '')));
  assert.ok(writes.length >= 1 && writes.every((l) => l.includes('if (this.margin)')), 'the acknowledgment gives way in the margin layout, and keeps its place in the list: ' + writes.join(' | '));
  assert.ok(!body(panel, 'private landClosed(c: Composer, had: Set<string>, r: Status, note: string): void {').includes('sentNote'), 'the list layout\'s re-read after the close touches it neither');
  // the guide says the same in the reader's words, and the module the Docs sentence names is in the tree
  assert.ok(flat(guide).includes('In the list under a narrow column, the line stands under the panel\'s header instead.'));
  assert.ok(fs.existsSync(path.join(REPO, 'tests', 'test_guide_files_saved_line_layout.py')));
});

test('a Tab or a modifier pressed alone is no gesture: the arrivals paragraph names the keys NAV_KEYS holds, decision 43 names the exception, and gesture() returns on them before it marks or ends anything', () => {
  // the definition stands, and the exception follows it
  const rule = arrivals.indexOf('A gesture is a pointer press or a key anywhere in the body row, a wheel or a touch move');
  const except = arrivals.indexOf('A Tab or a modifier pressed alone (Shift, Control, Alt, AltGraph, Meta: `NAV_KEYS`) is no gesture: it moves the keyboard or begins a chord and scrolls, edits or presses nothing, and the key or the click that follows is the gesture');
  assert.ok(rule >= 0 && except > rule, 'the rule, then the exception');
  assert.ok(arrivals.includes('counted as gestures they ended the saved line before the keyboard could reach it'));
  assert.ok(d43.includes('the line ends at the person\'s next gesture (a Tab or a modifier pressed alone, the keyboard\'s way to the line, is none) or when the card comes into view, never on a timer'));
  // the keys the paragraph names are the set's, no more and no fewer
  const set = /const NAV_KEYS = new Set\(\[([^\]]*)\]\);/.exec(panel);
  assert.ok(set, 'the panel\'s NAV_KEYS');
  const inCode = set[1].match(/"([^"]+)"/g).map((k) => k.slice(1, -1)).sort();
  const named = /A Tab or a modifier pressed alone \(([^:]+): `NAV_KEYS`\)/.exec(arrivals);
  assert.ok(named, 'the paragraph names the modifiers');
  const inPlan = ['Tab', ...named[1].split(',').map((k) => k.trim())].sort();
  assert.deepEqual(inPlan, inCode, 'the plan names every key that is no gesture, and only those');
  // the gesture: the return on those keys comes before the saved line's end and before any arrival is marked seen
  const gesture = body(panel, 'gesture(ev?: Event): void {');
  const ret = gesture.indexOf('if (kb && NAV_KEYS.has(kb.key)) return;');
  assert.ok(ret >= 0, 'the early return');
  assert.ok(ret < gesture.indexOf('const over = this.savedOut !== null'), 'before the saved line is ended');
  assert.ok(ret < gesture.indexOf('this.seenKeys?.add(k);'), 'before an arrival is marked seen');
  // the keys reach the gesture through the constructor's keydown listener, the one the plan's "a key anywhere in the body row" names
  assert.ok(panel.includes('for (const ev of ["pointerdown", "keydown"]) row.addEventListener(ev, (e) => this.gesture(e), true);'));
  // the module the paragraph names drives the Tab and each modifier on both lines
  assert.ok(arrivals.includes('`file-comments-seen-review2.test.ts` drives the Tab and each modifier on both lines'));
  assert.ok(review2.includes('test("a Tab or a modifier pressed alone is no gesture: the line stands through the Tab that brings the keyboard to it'), 'the saved line');
  assert.ok(review2.includes('for (const key of ["Tab", "Shift", "Control", "Alt", "Meta", "AltGraph"]) {'), 'each key of the set, on the saved line');
  assert.ok(review2.includes('test("a Tab marks no arrival seen either'), 'the arrivals line');
});

test('the plan never calls the acknowledgment a note, across a wrap either: the arrivals Tests bullet says the acknowledgment\'s green', () => {
  assert.ok(flat(context).includes('The panel\'s acknowledgment after a send (Sent to <session> at <time>, or Queued for <session>) is not a note either.'));
  // the raw-text scans (tests/test_context_send_note.py, tools/file-review-plan-seen-review.test.mjs) miss a phrase wrapped across
  // a line; this reads the collapsed text
  const hit = /\bsent[ -]note\b/i.exec(FLAT);
  assert.ok(!hit, 'the plan calls the acknowledgment a note: ' + (hit ? FLAT.slice(Math.max(0, hit.index - 60), hit.index + 40) : ''));
  assert.ok(arrivalsBullet.includes('a whole-file comment\'s save moving nothing, the line at the foot in the acknowledgment\'s green, a real wheel ending it'));
});

test('the Tests bullet names the review rounds\' own modules, each in the tree, and the seen paragraph points at them', () => {
  const modules = [
    'file-comments-seen-fixes.test.ts', 'file-comments-seen-review2.test.ts', 'file-comments-seen-review2-browser.test.ts',
    'tests/test_guide_files_seen_definition.py', 'tests/test_guide_files_saved_line_layout.py',
    'tools/file-comments-host-untouched.test.mjs', 'tools/file-comments-host-review-seen.test.mjs',
  ];
  for (const m of modules) {
    const rel = m.includes('/') ? m : path.join('ui', 'webview', m);
    assert.ok(fs.existsSync(path.join(REPO, rel)), `${m} is in the tree`);
    assert.ok(seenBullet.includes('`' + m + '`'), `the Tests bullet names ${m}`);
    assert.ok(seen.includes('`' + m + '`'), `the seen paragraph names ${m}`);
  }
  assert.ok(seenBullet.includes('The review rounds\' own modules: `file-comments-seen-fixes.test.ts` drives the panel over the stand-in'));
});

test('the plan names this module beside the seen follow-on\'s, in the paragraph and the Tests bullet', () => {
  for (const text of [seen, seenBullet]) assert.ok(text.includes('`tools/file-review-plan-seen-review-3.test.mjs`'));
  assert.ok(fs.existsSync(path.join(REPO, 'tools', 'file-review-plan-seen-review-3.test.mjs')));
});
