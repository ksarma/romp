// The plan describes the hint under the comment box, and the panel renders what it describes.
//
// The composer follow-on (plans/file-review.md, "The composer follow-on (2026-09-07)") said the hint
// "names the platform's chord, detected once by the editor's modifier rule". The round-1 review fix
// (ui/webview/file-comments.ts, composerHint) gave the hint a second form: on a device whose primary
// pointer is coarse, a phone or a tablet, it names the Save button instead ("Enter adds a line; tap
// Save when done"), because a soft keyboard has no modifier to hold; and it reads the pointer at each
// render rather than once, because a tablet docks to a trackpad. The plan kept the one-form sentence,
// so it misdescribed the hint on the phone its own Phone bullet names (review finding, 2026-09-07).
// The plan now says both forms and the per-render read, and this module holds the two sides together:
// the touch hint the plan quotes is the panel's constant, byte for byte; the keyboard hint the plan
// quotes is what the panel's saveChord and suffix compose on macOS; and the plan's per-render
// statement matches the default argument and the call site in renderComposer, so a change to either
// side without the other fails here. tools/file-review-plan-save-gesture.test.mjs pins the gesture;
// this pins the hint. Synthetic: no session data, only the repo's own text.
// Run: node --test tools/file-review-plan-composer-hint.test.mjs
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

// The follow-on note, hard wraps collapsed so an assertion survives a rewrap.
const noteAt = plan.indexOf('The composer follow-on (2026-09-07)');
assert.ok(noteAt >= 0, 'the follow-on note is in the plan');
const noteEnd = plan.indexOf('### Slice 3: region comments on images', noteAt);
assert.ok(noteEnd > noteAt, 'the note ends at the Slice 3 heading');
const note = plan.slice(noteAt, noteEnd).replace(/\s+/g, ' ');

// The panel's pieces, from its source: the touch constant, the chord, and the keyboard suffix.
const touchHint = /export const COMPOSER_HINT_TOUCH = "([^"]+)";/.exec(panel)?.[1];
const chord = /export function saveChord\(mac: boolean\): string \{ return \(mac \? "(\w+)" : "(\w+)"\) \+ "(\+Enter)"; \}/.exec(panel);
const suffix = /return touch \? COMPOSER_HINT_TOUCH : saveChord\(mac\) \+ "([^"]+)";/.exec(panel)?.[1];

test('the touch hint the plan quotes is the panel\'s constant, and the plan says when it shows', () => {
  assert.ok(touchHint, 'COMPOSER_HINT_TOUCH is a string constant in the panel');
  assert.equal(touchHint, 'Enter adds a line; tap Save when done');
  assert.ok(note.includes(`"${touchHint}"`), `the note quotes the touch hint: ${JSON.stringify(touchHint)}`);
  assert.ok(note.includes('primary pointer is coarse'), 'the note names the condition the panel tests (isCoarsePointer: the primary pointer)');
  assert.ok(note.includes('names the button instead'), 'the note says the hint names the button there, not a chord');
  assert.ok(/a phone; a tablet with no trackpad/.test(note), 'the note names the devices that read as coarse');
  assert.ok(note.includes('any hardware keyboard, whatever the hint says'), 'the note says the chord still saves from a hardware keyboard, so the tablet-with-keyboard case is stated');
});

test('the keyboard hint the plan quotes is what the panel composes on macOS, with Ctrl elsewhere', () => {
  assert.ok(chord, 'saveChord composes the modifier and +Enter');
  assert.equal(chord[1], 'Cmd'); assert.equal(chord[2], 'Ctrl');
  assert.ok(suffix, 'composerHint appends one suffix to the chord');
  const macHint = chord[1] + chord[3] + suffix;
  assert.equal(macHint, 'Cmd+Enter saves; Enter adds a line');
  const at = note.indexOf(`"${macHint}"`);
  assert.ok(at >= 0, `the note quotes the macOS hint: ${JSON.stringify(macHint)}`);
  const after = note.slice(at + macHint.length + 2, at + macHint.length + 60);
  assert.ok(after.includes('on macOS') && after.includes(chord[2] + chord[3] + ' elsewhere'), `…and names the other platform's chord beside it: ${JSON.stringify(after)}`);
  assert.ok(note.includes('detected once by the editor\'s modifier rule'), 'the modifier is still detected once (IS_MAC, a module constant)');
  assert.match(panel, /^const IS_MAC = typeof navigator !== "undefined" && /m, 'IS_MAC is a module constant, read once');
});

test('the plan says the pointer is read at each render, and the panel reads it there', () => {
  assert.ok(note.includes('read at each render'), 'the note says the coarse-pointer read is per render');
  assert.ok(note.includes('docks to a trackpad'), 'the note gives the reason: the primary pointer changes');
  assert.match(panel, /export function composerHint\(mac: boolean, touch: boolean = isCoarsePointer\(\)\): string \{/,
    'the touch flag defaults to the device\'s answer at the call, not to a constant');
  const rc = panel.indexOf('  private renderComposer(): void {');
  assert.ok(rc >= 0, 'renderComposer is a method of the panel');
  const end = panel.indexOf('\n  }\n', rc);
  assert.ok(end > rc, 'the method closes at the class\'s indent');
  const body = panel.slice(rc, end);
  assert.ok(body.includes('composerHint(IS_MAC)'), 'renderComposer builds the hint with the default touch flag, so the device is read at each render');
  assert.ok(!panel.includes('composerHint(IS_MAC, '), 'no call site pins the touch flag to a constant');
  assert.match(panel, /import \{[^}]*\bisCoarsePointer\b[^}]*\} from "\.\/file-comments-regions";/, 'the one coarse-pointer test the panel uses');
});
