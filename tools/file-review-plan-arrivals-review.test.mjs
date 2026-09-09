// The arrivals follow-on's review (round 1, 2026-09-09): three plan sentences held to the code and to the guide.
//
// The review found the plan's own contract for the send op behind the op: the fileCommentsSend request block listed every
// field the kernel reads except `note`, which the Send confirm's box had begun sending that day (decision 40 named it in
// prose; the block, the one shape statement a reader on another host builds from, did not). It also found the new text
// gendering the user where the base plan and the repo's CLAUDE.md say they/their, and, after the guide's save sentence
// was rewritten to name every gesture the panel counts, the plan's Docs sentence still naming scrolling alone. This
// module holds the three fixes: the block lists `note?` and the op prose states the field's trim, its two refusals and
// their order, each checked against the kernel and the panel; the arrivals paragraph, decision 40 and the Docs sentence
// carry no gendered pronoun for the user; and the Docs sentence's gestures are the guide's. Synthetic: only the repo's
// own text.
// Run: node --test tools/file-review-plan-arrivals-review.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');

const plan = read('plans', 'file-review.md');
const kernel = read('kernel', 'kernel.py');
const panel = read('ui', 'webview', 'file-comments.ts');
const model = read('ui', 'webview', 'file-comments-model.ts');
const guide = read('docs', 'guide.md');

// The text between two markers, hard wraps collapsed so an assertion survives a rewrap.
function between(doc, from, to) {
  const a = doc.indexOf(from);
  assert.ok(a >= 0, `${JSON.stringify(from)} not found`);
  const b = doc.indexOf(to, a + from.length);
  assert.ok(b > a, `${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return doc.slice(a, b).replace(/\s+/g, ' ');
}
const op = between(plan, '**`fileCommentsSend`**, the send op:', '### The message to the session');
const note = between(plan, 'The arrivals follow-on (2026-09-09):', '### Slice 3: region comments on images');
const d40 = between(plan, '40. **The Send confirm\'s message preview gives way to a note box**', '## Open questions for the user');
const docs = between(plan, '\n## Docs', '\n## Deliberately not in v1');
const tests = between(plan, '\n## Tests', '\n## Docs');

test('the fileCommentsSend request block lists `note?` beside `todoId?`, and the op prose states the field', () => {
  assert.ok(op.includes('request {type:"fileCommentsSend", reqId, sid, path, tracked, comments:[{id, desc, body}], accepted, rejected, watermark, todoId?, note?}'));
  assert.ok(op.includes('`note` (the arrivals follow-on, 2026-09-09) is the Send confirm\'s box, trimmed and left out when empty'));
  assert.ok(op.includes('the kernel refuses a `note` that is not text, trims one that is, and refuses a trimmed note longer than 4000 characters (`_SEND_NOTE_MAX`)'));
  assert.ok(op.includes('both refusals before the nothing-to-send gate (a note alone is something to send) and before the watermark is read'));
  assert.ok(op.includes('the panel refuses the same bound (`SEND_NOTE_MAX`, `file-comments-model.ts`) before any request goes'));
  assert.ok(op.includes('marker-neutralizes the path, every body and the note'));
});

test('the op prose is true of the kernel: the read, the two refusals, their order before the gate and the watermark, the neutralization', () => {
  assert.ok(kernel.includes('\n_SEND_NOTE_MAX = 4000\n'), 'the bound the prose names');
  const read_ = kernel.indexOf('note = msg.get("note")');
  const notText = kernel.indexOf('return fail("nothing was sent: the note was not text")');
  const tooLong = kernel.indexOf('if len(note) > _SEND_NOTE_MAX:');
  const gate = kernel.indexOf('if not comments and accepted + rejected == 0 and not note:');
  const watermark = kernel.indexOf('watermark, bad = _send_watermark(msg.get("watermark"))');
  for (const [name, i] of [['the read', read_], ['the not-text refusal', notText], ['the bound refusal', tooLong], ['the nothing-to-send gate', gate], ['the watermark read', watermark]]) {
    assert.ok(i >= 0, `${name} is in the kernel`);
  }
  assert.ok(read_ < notText && notText < tooLong && tooLong < gate && gate < watermark, 'read, refuse, refuse, then the gate, then the watermark: the order the prose states');
  assert.ok(kernel.includes('nt = _neutralize_romp_markers(str(note or ""))'), 'the builder neutralizes the note with the path and the bodies');
});

test('the op prose is true of the panel: the same bound, refused before any request goes', () => {
  assert.ok(model.includes('export const SEND_NOTE_MAX = 4000;'), 'the panel\'s bound is the kernel\'s');
  assert.ok(model.includes('export function noteTooLong(note: string): string | null {'));
  const send = between(panel, 'async doSend(): Promise<void> {', 'if (note) msg.note = note;');
  assert.ok(send.includes('const note = this.sendNote.trim();'), 'trimmed');
  assert.ok(send.includes('const long = noteTooLong(note); if (long) { this.errors.set("send", { text: long, reload: false }); this.render(); return; }'), 'refused over the bound before the request is built');
  assert.ok(panel.includes('if (note) msg.note = note;'), 'left out when empty');
});

test('the arrivals paragraph, decision 40 and the Docs sentence speak of the user as the base plan does: the user, they; never a gendered pronoun', () => {
  for (const [name, text] of [['the arrivals paragraph', note], ['decision 40', d40], ['the Docs section', docs]]) {
    const hit = text.match(/\b(he|his|him)\b/);
    assert.ok(!hit, `${name} genders the user: ${hit && hit[0]} in "${hit && text.slice(Math.max(0, hit.index - 60), hit.index + 40)}"`);
  }
  assert.ok(note.includes('The first report: the user sent comments, the session answered with eleven changes and seven replies while they kept commenting'));
  assert.ok(note.includes('the first they knew of them was the next Send accepting the changes by default'));
  assert.ok(note.includes('The second report: they saved a reply, scrolled on while the host answered'));
  assert.ok(d40.includes('a text box for anything they want to add takes its place'));
});

test('the Docs sentence names the gestures the guide\'s save sentence names, and the panel listens for each', () => {
  const gestures = 'unless you scrolled, clicked, tapped, or pressed a key';
  assert.ok(docs.includes('and that a save brings the new card into view ' + gestures + ' meanwhile (`tests/test_guide_files_arrivals.py` holds both sentences to the panel)'));
  const save = guide.replace(/\s+/g, ' ').match(/Saving brings the new card into view[^.]*\./);
  assert.ok(save, 'the guide\'s save sentence');
  assert.ok(save[0].includes(gestures), 'the guide names the same gestures: ' + save[0]);
  assert.ok(panel.includes('for (const ev of ["pointerdown", "keydown"]) row.addEventListener(ev, (e) => this.gesture(e), true);'), 'clicked, tapped, pressed a key');
  assert.ok(panel.includes('for (const ev of ["wheel", "touchmove"]) row.addEventListener(ev, (e) => this.gesture(e), { capture: true, passive: true });'), 'scrolled');
});

test('the Tests section names this module', () => {
  assert.ok(tests.includes('`tools/file-review-plan-arrivals-review.test.mjs` holds the review\'s three plan fixes (the request block\'s `note?` and the op prose to the kernel and the panel, the user ungendered, the Docs sentence\'s gestures to the guide)'));
});
