// The Slice 5 build note's pointer at the paint-gap fix (2026-09-20; plans/markdown-viewer.md, the Slice 5 note's item 9). The
// note's item 9 records the Comment offer on a keyboard selection with every amendment the Slice 5 review made to it (rounds 1, 2,
// 4, 6, 7 and 8); the fix of upstream/2026-09-20-paint-gap-reoffer.md changed the same mechanism (a pass reads the selection at its
// head against the two notes the events write, and a change whose selectionchange is still to come leaves the record dropped and the
// float to that event), and the plan keeps a slice's history as written and marks a superseded sentence with a pointer in place
// ("history since ..."), the form the Slice 5 and Slice 8 notes use elsewhere (tools/markdown-viewer-plan-decision52-pointers.test.mjs).
// This module holds the pointer to the ledger entry it cites and to the identifiers it names in ui/webview/file-comments.ts, so a
// later move of either is seen here. Synthetic: the repo's own text only. Run: node --test tools/markdown-viewer-plan-paint-gap-pointer.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');
const flat = (s) => s.replace(/\s+/g, ' ');

const LEDGER = 'upstream/2026-09-20-paint-gap-reoffer.md';
const POINTER = 'the review\'s round 1; history since 2026-09-20, the paint-gap fix of ' + LEDGER + ': a pass reads the selection at its head, before its writes, against the selection the last delivered selectionchange found and the one the previous pass left, and a change of the person\'s whose event is still to come leaves the record dropped and the float to that event, the mechanics in the offeredFor, lastDelivered, passLeft, pendingChange and afterPaint docblocks of ui/webview/file-comments.ts);';

// The Slice 5 build note, hard wraps collapsed so an assertion survives a rewrap.
function slice5() {
  const plan = read('plans', 'markdown-viewer.md');
  const from = '### Slice 5: comments anchor on real notes';
  const to = '### Slice 6: reaching a section without scrolling';
  const a = plan.indexOf(from);
  assert.ok(a >= 0, `heading ${JSON.stringify(from)} not found in the plan`);
  const b = plan.indexOf(to, a + from.length);
  assert.ok(b > a, `heading ${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return flat(plan.slice(a, b));
}

test('the Slice 5 note marks item 9\'s offeredFor sentence as history since the paint-gap fix, in place, once', () => {
  const note = slice5();
  assert.ok(note.includes(POINTER), 'the pointer is missing from the Slice 5 note, or its wording moved');
  assert.equal((note.match(/history since 2026-09-20, the paint-gap fix of/g) || []).length, 1, 'one pointer, at the offeredFor parenthetical');
  // the sentence the pointer annotates is still there as written: history is marked, not rewritten
  assert.ok(note.includes('recorded by onSelection and re-read from the live selection after every paint of the panel\'s own, `afterPaint` at the end of paintAll and of repaintPresel'));
});

test('the pointer cites a ledger entry that exists and names identifiers file-comments.ts declares', () => {
  assert.ok(fs.existsSync(path.join(REPO, LEDGER)), LEDGER + ' is missing');
  const src = read('ui', 'webview', 'file-comments.ts');
  for (const id of ['offeredFor: SelectionEnds', 'lastDelivered: EndsNote', 'passLeft: EndsNote', 'pendingChange = false', 'private afterPaint(): void', 'private noteSelectionAtHead(): void']) {
    assert.ok(src.includes(id), 'file-comments.ts no longer declares ' + JSON.stringify(id));
  }
});

test('the pointer uses plain prose: no em dash', () => {
  assert.ok(!POINTER.includes(String.fromCharCode(0x2014)), 'em dash');
});
