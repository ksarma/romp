// The plan names one save gesture for the comments panel's composer, and the panel implements it.
//
// The composer follow-on (plans/file-review.md, "The composer follow-on (2026-09-07)") made every
// composer in the panel a textarea: Enter adds a line; Cmd+Enter or Ctrl+Enter, or the Save button,
// saves. That change rewrote the Slice 2 bullet and added the note, but four older sentences kept
// naming plain Enter as the save moment (the Raw acceptance criterion under "Commenting from either
// view", two sentences in the Slice 3 build note, and the Slice 3 entry under "## Tests"), so the plan
// contradicted itself about the key, and the acceptance criterion could no longer be executed as
// written (review finding, 2026-09-07). Those sentences now say "the save", which was true under the
// old key and is true under the new one. This module keeps the plan to one gesture: every bare
// "Enter" in it is a chord, "Enter adds a line", or the story's Step 6 sentence about the CHAT
// composer's quote chips (a different surface, ui/webview/feed.ts); the four sentences name the save;
// and the panel's key rule still matches, so a change to either side without the other fails here.
// Synthetic: no session data, only the repo's own text.
// Run: node --test tools/file-review-plan-save-gesture.test.mjs
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
const flat = plan.replace(/\s+/g, ' ');

// The text between two headings, hard wraps collapsed so an assertion survives a rewrap.
function section(from, to) {
  const a = plan.indexOf(from);
  assert.ok(a >= 0, `heading ${JSON.stringify(from)} not found in the plan`);
  const b = plan.indexOf(to, a + from.length);
  assert.ok(b > a, `heading ${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return plan.slice(a, b).replace(/\s+/g, ' ');
}
const surface = section('### The surface, in its Slice 2 state', '### Commenting from either view, and in every format');
const ux = section('### Commenting from either view, and in every format', '### The viewer seam');
const slice2 = section('### Slice 2: the session\'s changes as accept/reject cards and inline marks', '### Slice 3: region comments on images');
const slice3 = section('### Slice 3: region comments on images', '### Slice 4: PDFs rendered in the viewer');
const tests = section('## Tests', '## Docs');

test('every bare "Enter" in the plan is a chord, "Enter adds a line", or the chat composer\'s send', () => {
  const seen = [];
  for (const m of flat.matchAll(/\bEnter\b/g)) {
    const before = flat.slice(Math.max(0, m.index - 5), m.index);
    const after = flat.slice(m.index + 'Enter'.length, m.index + 'Enter'.length + 30);
    const chord = /(?:Cmd|Ctrl)[+-]$/.test(before);
    const newline = after.startsWith(' adds a line');
    // Step 6 of the story: the CHAT composer's quote chips, where Enter sends (ui/webview/feed.ts) — not the panel.
    const chat = after.startsWith(' sends them as one message');
    seen.push({ chord, newline, chat });
    assert.ok(chord || newline || chat, `a bare Enter names a moment the composer no longer has: ${JSON.stringify(flat.slice(Math.max(0, m.index - 60), m.index + 40))}`);
  }
  assert.ok(seen.some((s) => s.chord) && seen.some((s) => s.newline), 'the plan names the chord and the newline');
  assert.equal(seen.filter((s) => s.chat).length, 1, 'the chat composer\'s Enter is named once, in the story');
});

test('the four sentences that once said "and Enter" name the save instead', () => {
  assert.ok(!flat.includes('and Enter'), 'no "…and Enter" anchors a moment to the key');
  assert.ok(ux.includes('two lines are inserted above the passage between the selection and the save'), 'the Raw acceptance criterion');
  assert.ok(slice3.includes('a reference definition can change on disk between the drag and the save'), 'figure-mismatch, the Slice 3 build note');
  assert.ok(slice3.includes('a figure regenerated between the drag and the save was stamped with the new bytes\' hash'), 'the figure fence, the Slice 3 review note');
  assert.ok(tests.includes('regenerated between the drag and the save, nothing written and no landmark created'), 'the Slice 3 entry under Tests');
});

test('the Slice 2 bullet and the follow-on note say the one gesture, and the panel\'s key rule is that gesture', () => {
  const bullet = surface.slice(surface.indexOf('- **Comment on a selection**'), surface.indexOf('- **Send to session**'));
  assert.ok(bullet.length > 0, 'the Comment on a selection bullet is under The surface');
  assert.ok(bullet.includes('Enter adds a line; Cmd+Enter (Ctrl+Enter off a Mac) or Save saves'), 'the bullet');
  const note = slice2.slice(slice2.indexOf('The composer follow-on (2026-09-07)'));
  assert.ok(note.includes('Enter adds a line; Cmd+Enter on macOS or Ctrl+Enter elsewhere'), 'the note names the newline and both chords');
  assert.ok(note.includes('or the Save button saves'), '…and the button');
  // The panel: a plain Enter is not the composer's (the textarea's newline); Enter with either modifier saves.
  assert.ok(panel.includes('if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) return "save";'), 'composerKeyAction saves on the chord only');
  assert.ok(/export function composerKeyAction\([\s\S]*?\n\}/.test(panel), 'composerKeyAction is exported');
  const body = panel.slice(panel.indexOf('export function composerKeyAction('), panel.indexOf('\n}', panel.indexOf('export function composerKeyAction(')));
  assert.ok(!/e\.key === "Enter"\)\s*return "save"/.test(body), 'no branch saves on a bare Enter');
  assert.ok(panel.includes('" saves; Enter adds a line"'), 'the hint under the box says what the plan says');
});
