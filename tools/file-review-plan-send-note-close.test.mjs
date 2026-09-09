// Decision 40's sentences on the viewer's close guard (plans/file-review.md) held to the panel's close asks and the
// viewer's close paths.
//
// The decision says the Send confirm's note is cleared only by a successful send or by Cancel, and then records a gap the
// arrivals follow-on's review found (2026-09-09): the panel's close ask (ctx.guardClose) reads the composer's typed
// comment and not the note, so a close of the viewer or a replace-open with words in the box drops them with the panel,
// silently; the fix owed is the composer's ask extended to the note. A plan that says "not yet" about a thing the code has since done
// costs the next reader the search the sentence was meant to save, so this module reads both ways: while no close ask
// reads the note, the gap's sentence must stand; the day a close ask reads it, this fails and the sentence is rewritten
// (the same shape as file-review-plan-margin-review-3's loose-band pin). The viewer's side is held too: the guard runs on
// a close and on both replace-opens, and Escape typed in the box stops there. Synthetic: only the repo's own text.
// Run: node --test tools/file-review-plan-send-note-close.test.mjs
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
const viewer = read('ui', 'webview', 'file-view.ts');

// The text between two markers, hard wraps collapsed so an assertion survives a rewrap.
function between(doc, from, to) {
  const a = doc.indexOf(from);
  assert.ok(a >= 0, `${JSON.stringify(from)} not found`);
  const b = to === null ? doc.length : doc.indexOf(to, a + from.length);
  assert.ok(b > a, `${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return doc.slice(a, b).replace(/\s+/g, ' ');
}
const decisions = between(plan, '## Decisions', '## Open questions for the user');
const d40 = between(decisions, '40. **The Send confirm\'s message preview gives way to a note box**', null);
const tests = between(plan, '\n## Tests', '\n## Docs');

// Every method the panel registers as a close ask, and its body (from the signature to the method's closing brace).
const askNames = Array.from(panel.matchAll(/ctx\.guardClose\(\(\) => this\.(\w+)\(\)\)/g), (m) => m[1]);
function bodyOf(name) {
  const sig = `\n  ${name}(): CloseAsk | null {`;
  const a = panel.indexOf(sig);
  assert.ok(a >= 0, `the panel defines ${name}(): CloseAsk | null`);
  const b = panel.indexOf('\n  }\n', a + sig.length);
  assert.ok(b > a, `${name}'s closing brace`);
  return panel.slice(a, b);
}

test('decision 40 says the note is cleared only by a send or by Cancel, and records the close guard\'s gap as owed', () => {
  assert.ok(d40.includes('its text survives every re-render while the confirm is open and is cleared only by a successful send or by Cancel.'));
  assert.ok(d40.includes('The arrivals follow-on\'s review (2026-09-09) found one gap, still owed: the viewer\'s close guard (`ctx.guardClose`) asks about the composer\'s typed comment and not about the note'));
  assert.ok(d40.includes('a close of the viewer or a replace-open (a link followed inside the file, a Files-pane row) while the box holds words drops them with the panel, and neither a dialog nor the notice bar says so'));
  assert.ok(d40.includes('Escape typed in the box stops at the box and closes nothing.'));
  assert.ok(d40.includes('The fix is the composer\'s ask extended to the note: the close guard names what it would drop, and a refused ask keeps the viewer, the panel and the words.'));
  assert.ok(d40.includes('`tools/file-review-plan-send-note-close.test.mjs` holds these sentences to the panel\'s close asks and fails once a close ask reads the note'));
  assert.ok(!/"[^"]*\b(I|my|me)\b[^"]*"/.test(d40), 'no quoted utterance of the user\'s');
});

test('the panel\'s close asks are as the sentence says: the composer\'s typed comment is asked about, the note is not (yet)', () => {
  assert.ok(askNames.length >= 1, 'the panel registers at least one close ask through ctx.guardClose');
  const bodies = askNames.map((n) => [n, bodyOf(n)]);
  assert.ok(bodies.some(([, b]) => b.includes('this.composer') && b.includes('this.input.value')), 'one ask reads the composer and its box');
  for (const [n, b] of bodies) {
    assert.ok(!/sendNote|noteBox/.test(b), `${n} now reads the Send confirm's note: decision 40's gap is closed. Rewrite its "found one gap, still owed" sentences (the close guard asks about the note too) and re-pin here.`);
  }
  // the note lives in the panel's field and its box alone: nothing else could carry it past a dispose
  assert.ok(panel.includes('sendNote = "";'), 'the note\'s field');
  assert.ok(!/(localStorage|sessionStorage)\.[a-zA-Z]+\([^)]*[nN]ote/.test(panel), 'the note is not stored outside the panel');
});

test('the viewer runs every close ask on a close and on both replace-opens, and Escape in the box stops there', () => {
  assert.ok(viewer.includes('closeGuard = () => confirmDiscard() && closeAsks.every((ask) => { const q = ask(); return q === null || askDiscard(q.question, q.kept); });'));
  const closeFn = between(viewer, 'export function closeFileView(): void {', 'export function openFileView(');
  assert.ok(closeFn.includes('if (closeGuard && !closeGuard()) return;'), 'a close asks');
  assert.ok(closeFn.includes('runCloseHooks();'), 'then the panel is disposed with the viewer');
  const openFn = between(viewer, 'export function openFileView(', 'closeGuard = null;');
  assert.ok(openFn.includes('if (document.getElementById("romp-fileview") && closeGuard && !closeGuard()) return false;'), 'a replace-open by path asks');
  const urlFn = between(viewer, 'export function openUrlView(', 'closeGuard = null;');
  assert.ok(urlFn.includes('if (document.getElementById("romp-fileview") && closeGuard && !closeGuard()) return;'), 'a replace-open by URL asks');
  assert.ok(panel.includes('ctx.onClose(() => this.dispose());'), 'the panel goes with the viewer');
  const noteKey = between(panel, 'noteKey = (e: KeyboardEvent) => {', '\n  };');
  assert.ok(noteKey.includes('if (e.key === "Escape") e.stopPropagation();'), 'Escape typed in the note box does not reach the viewer\'s close');
});

test('the Tests section names this module for decision 40\'s close-guard sentences', () => {
  assert.ok(tests.includes('`tools/file-review-plan-send-note-close.test.mjs` holds decision 40\'s sentences on the viewer\'s close guard (the composer\'s comment asked about, the note not yet) to the panel\'s close asks and the viewer\'s close and replace-open paths.'));
});
