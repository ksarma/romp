// Decision 40's sentences on the viewer's close guard (plans/file-review.md) held to the panel's close asks and the
// viewer's close paths.
//
// The decision says the Send confirm's note is cleared only by a successful send or by Cancel, and then records the gap
// the arrivals follow-on's review found (2026-09-09) and its consolidation closed: the panel's close ask (ctx.guardClose)
// read the composer's typed comment and not the note, so a close of the viewer or a replace-open with words in the box
// dropped them with the panel, silently. Now a second ask beside the composer's reads the note as the kernel does
// (trimNote) and names what it would drop. This module holds the record to the code both ways: the two asks exist, each
// reads its own field, the note's words are the decision's, and the viewer runs every ask on a close and on both
// replace-opens; Escape typed in the box stops there. A plan that said "not yet" about a thing the code had since done
// would cost the next reader the search the sentence was meant to save, so the "owed" wording is pinned absent too.
// Synthetic: only the repo's own text. Run: node --test tools/file-review-plan-send-note-close.test.mjs
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

test('decision 40 says the note is cleared only by a send or by Cancel, records the close guard\'s gap as closed by a second ask, and no longer calls it owed', () => {
  assert.ok(d40.includes('its text survives every re-render while the confirm is open and is cleared only by a successful send or by Cancel.'));
  assert.ok(d40.includes('The arrivals follow-on\'s review (2026-09-09) found one gap: the viewer\'s close guard (`ctx.guardClose`) asked about the composer\'s typed comment and not about the note'));
  assert.ok(d40.includes('a close of the viewer or a replace-open (a link followed inside the file, a Files-pane row) while the box held words dropped them with the panel, and neither a dialog nor the notice bar said so'));
  assert.ok(d40.includes('The review\'s consolidation closed it with a second ask beside the composer\'s (`noteAsk`): words in the box, as the kernel reads them (`trimNote`), make a close ask naming what it would drop, put by the viewer the way it puts the editor\'s own, and a refused ask keeps the viewer, the panel and the words'));
  assert.ok(d40.includes('Cancel and a send that went leave no ask, a send out or refused keeps it, and Escape typed in the box stops at the box and closes nothing.'));
  assert.ok(d40.includes('`tools/file-review-plan-send-note-close.test.mjs` holds these sentences to the panel\'s two close asks and the viewer\'s close paths; `file-comments-send-note.test.ts` drives the ask.'));
  assert.ok(!/still owed|not yet/.test(d40), 'the gap is closed: the record says so, not "owed"');
  assert.ok(!/"[^"]*\b(I|my|me)\b[^"]*"/.test(d40), 'no quoted utterance of the user\'s');
});

test('the panel\'s close asks are as the sentence says: one reads the composer\'s typed comment, one the Send confirm\'s note as the kernel reads it, each naming its own thing', () => {
  assert.deepEqual(askNames, ['draftAsk', 'noteAsk'], 'two asks, the composer\'s then the note\'s');
  const draft = bodyOf('draftAsk'), note = bodyOf('noteAsk');
  assert.ok(draft.includes('this.composer') && draft.includes('this.input.value'), 'the composer\'s ask reads the composer and its box');
  assert.ok(!/sendNote|noteBox/.test(draft), 'and not the note: each ask names one thing');
  assert.ok(note.includes('if (!trimNote(this.sendNote)) return null;'), 'the note\'s ask reads the note as the kernel does: words its strip would take to nothing are not asked about');
  assert.ok(!/this\.composer|this\.input/.test(note), 'and not the composer');
  assert.ok(note.includes('return { question: "Discard the unsent note on " + name + "?", kept: "This file stays open: the note typed under Send on " + name + " is not sent. Send it, or Cancel it, then try again." };'), 'the ask names what it would drop and how to keep it, in the editor\'s ask\'s shape');
  // the note lives in the panel's field and its box alone: nothing else could carry it past a dispose
  assert.ok(panel.includes('sendNote = "";'), 'the note\'s field');
  assert.ok(!/(localStorage|sessionStorage)\.[a-zA-Z]+\([^)]*[nN]ote/.test(panel), 'the note is not stored outside the panel');
  // Cancel and a send that went clear the field the ask reads, so neither leaves an ask
  assert.ok(panel.includes('fcsendcancel: () => { this.sendConfirm = false; this.sendNote = ""; this.noteBox.value = ""; this.render(); },'), 'Cancel clears the words');
  assert.ok(panel.includes('this.sendNote = ""; this.noteBox.value = "";     // sent: the words went with the message; a refusal (the catch) keeps them'), 'a send that went clears them; a refusal keeps them');
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

test('the Tests section names this module for decision 40\'s close-guard sentences, with both asks', () => {
  assert.ok(tests.includes('`tools/file-review-plan-send-note-close.test.mjs` holds decision 40\'s sentences on the viewer\'s close guard (the composer\'s comment and the Send box\'s note each asked about) to the panel\'s close asks and the viewer\'s close and replace-open paths.'));
});
