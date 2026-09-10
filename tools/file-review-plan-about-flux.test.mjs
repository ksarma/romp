// Comment on this change is offered on a spanned change only while the view carries the change's text (spanCarried): the
// withholding the about follow-on's review added on 2026-09-10 (ui/webview/file-comments.ts, renderChangeCard and
// startChangeComment; its stand-in file-comments-about-fixes.test.ts). Until the review of the round's records, the same
// day, plans/file-review.md's about paragraph and its Slice 2 build paragraph stated the button unconditionally, so a
// reader of the plan expected a button the card does not show between a reject's reply and its reload, or between the
// poll's reload and its status. The about pin (tools/file-review-plan-about.test.mjs) checks the paragraph's backticked
// names for presence in the code, one way, so it could not hold the gate. This module holds the sentences the records
// fix added (the condition's three parts, the card in flux, the click that writes nothing, the button's return with the
// bytes beside Reveal's sibling gate, the deletion's exemption and the history) to the panel's code and to the stand-in's
// title and assertions, and the two Tests indexes to the tree and the modules' own headers. Synthetic: only the repo's
// own text. Run: node --test tools/file-review-plan-about-flux.test.mjs
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
const standIn = read('ui', 'webview', 'file-comments-about-fixes.test.ts');
// A module's header comment as one line: the slashes and the hard wraps out, so a sentence survives a rewrap.
const header = (src) => src.slice(0, src.indexOf('\nimport ')).replace(/\n\/\/\s*/g, ' ').replace(/^\/\/\s*/, '').replace(/\s+/g, ' ');

// The text between two markers, hard wraps collapsed so an assertion survives a rewrap.
function between(doc, from, to) {
  const a = doc.indexOf(from);
  assert.ok(a >= 0, `${JSON.stringify(from)} not found`);
  const b = doc.indexOf(to, a + from.length);
  assert.ok(b > a, `${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return doc.slice(a, b).replace(/\s+/g, ' ');
}
const note = between(plan, 'The about follow-on (2026-09-10):', '### Slice 3: region comments on images');
const build = between(plan, 'Since the about follow-on (2026-09-10) every comment is its own card', 'The panel re-fetches the view\'s bytes itself');
const tests = between(plan, '\n## Tests', '\n## Docs');
const aboutBullet = tests.slice(tests.indexOf('- The about follow-on (2026-09-10, decisions 45 and 46):'));
// startChangeComment's body: from its signature to the helper declared after it.
const startAt = panel.indexOf('startChangeComment(id: string): void {');
const spanCarriedAt = panel.indexOf('private spanCarried(c: ChangeCard): boolean {');
assert.ok(startAt >= 0 && spanCarriedAt > startAt, 'startChangeComment, then spanCarried');
const start = panel.slice(startAt, spanCarriedAt);

// ── the condition: three parts, as spanCarried has them ───────────────────────────────────────────────────────────

test('the about paragraph records the withholding with its condition\'s three parts, each as the panel\'s helper has it: the status\'s bytes (textCurrent), a text to cut from (indexedText), a text view', () => {
  assert.ok(note.includes('For a spanned change, an insertion or a substitution, the card offers Comment on this change only while the view carries the change\'s text (`spanCarried`: the view\'s bytes are the status\'s, whose offsets place the span (`textCurrent`); there is a text to cut it from (`indexedText`: the view\'s, or while the editor is up the file as the editor loaded it, never the buffer); and the view shows text at all, not the picture of a media file)'));
  assert.ok(panel.includes('return !!s && this.textCurrent(s) && this.indexedText() !== null && this.ctx.mode() !== "media";'), 'spanCarried: the three parts and nothing else');
  assert.ok(panel.includes('private textCurrent(s: Status): boolean {\n    const vm = this.ctx.mtimeNs();\n    return !vm || !s.fileMtimeNs || vm === s.fileMtimeNs;'), 'textCurrent: the view\'s mtime is the status\'s');
  assert.ok(panel.includes('private indexedText(): string | null {\n    return this.ctx.editing() && this.editText !== null ? this.editText : this.ctx.text();'), 'indexedText: the file as the editor loaded it while editing, else the view\'s text');
  // the sentence stands where a reader meets the button: after the Reply sentence, before the selection's option
  const reply = note.indexOf('The change card\'s Reply is Comment on this change (`fcchangecomment`, `startChangeComment`)');
  const gate = note.indexOf('For a spanned change, an insertion or a substitution, the card offers Comment on this change only while');
  const option = note.indexOf('A selection overlapping pending changes\' marks (`overlapping`:');
  assert.ok(reply >= 0 && reply < gate && gate < option, 'the button, then its gate, then the selection\'s option');
});

// ── the card in flux: Accept and Reject alone; a deletion's stands ────────────────────────────────────────────────

test('the paragraph says what the card shows in flux and that a deletion\'s button stands, as renderChangeCard\'s guard has it and the stand-in asserts', () => {
  assert.ok(note.includes('in flux, a reject\'s reply landed and its reload not, or the poll\'s reload landed and its status not, the card shows Accept and Reject alone, no Comment on this change'));
  assert.ok(note.includes('while a deletion\'s, by id, stands whatever the view shows'));
  assert.match(panel, /if \(c\.curTo === c\.curFrom \|\| this\.spanCarried\(c\)\) \{\s*const re = btn\("Comment on this change", "fcchangecomment"\); re\.dataset\.id = c\.id;/, 'the guard: a deletion (no span), or the span carried');
  assert.equal(panel.match(/btn\("Comment on this change"/g).length, 1, 'the one place the button is made');
  // the stand-in drives the paragraph's scenario: the poll's reload before its status, then the bytes, then media
  assert.ok(standIn.includes('test("Comment on this change is withheld for a substitution or an insertion while the view\'s bytes are not the status\'s, and in media mode, and stands for a deletion; it comes back with the bytes"'), 'the stand-in\'s title');
  assert.ok(standIn.includes('const offered = (): boolean[] => ["h1", "h2", "h3"].map((id) => !!act(card(aside, "chg:" + id)!, "fcchangecomment", id));'), 'compares extracted booleans, never nodes');
  assert.ok(standIn.includes('assert.deepEqual(offered(), [false, false, true], "in flux: the spanned changes offer none'), 'the substitution and the insertion offer none; the deletion\'s stands');
  assert.ok(standIn.includes('["Accept", "Reject"], "Accept and Reject stay");'), 'Accept and Reject alone');
  assert.ok(standIn.includes('assert.deepEqual(offered(), [true, true, true], "the bytes landed: offered again");'), 'it comes back with the bytes');
  assert.ok(standIn.includes('assert.deepEqual(offered(), [false, false, true], "media: no text to cut the span from; the deletion\'s by id");'), 'and media mode');
});

// ── a click that reaches startChangeComment anyway writes nothing ─────────────────────────────────────────────────

test('the paragraph says a click that reaches startChangeComment in flux writes nothing, and the method returns before it opens the card or seats a composer', () => {
  assert.ok(note.includes('a click that reaches `startChangeComment` anyway writes nothing, since the composer over the span would quote other bytes and a comment by id alone would lose the passage the change has'));
  const spanned = start.indexOf('const spanned = !c.detached && c.curTo > c.curFrom;');
  const guard = start.indexOf('if (spanned && !this.spanCarried(c)) return;');
  const open = start.indexOf('this.openCards.add(c.key);');
  const composer = start.indexOf('this.composer = {');
  assert.ok(spanned >= 0 && guard > spanned, 'spanned, then the guard');
  assert.ok(open > guard && composer > guard, 'the guard before the card opens and before any composer');
});

// ── it comes back with the bytes, as Reveal and the not-shown tag do: inFlux ───────────────────────────────────────

test('the paragraph names Reveal\'s and the not-shown tag\'s sibling gate, inFlux, which renderChangeCard derives from the same textCurrent', () => {
  assert.ok(note.includes('the button comes back with the bytes, as an unpainted change\'s Reveal and its "not shown" tag do on the same ground (`inFlux`)'));
  assert.ok(panel.includes('const inFlux = !!s && !this.textCurrent(s);'), 'inFlux: the status\'s bytes are not the view\'s');
  assert.ok(panel.includes('if (c.kind === "del" || !inFlux) acts.appendChild(rv);'), 'an unpainted insertion\'s or substitution\'s Reveal waits; a deletion\'s stays');
  assert.match(panel, /else if \(!painted && this\.inline && !editing && !inFlux && src !== null && this\.ctx\.mode\(\) !== "media"\) \{[^}]*el\("span", "fc-tag", "not shown"\)/, 'the not-shown tag waits too');
});

// ── the history, as the stand-in's header has it ──────────────────────────────────────────────────────────────────

test('the paragraph\'s history matches the stand-in\'s: before the review a spanned change in flux took the deletion\'s by-id composer and Save wrote a comment with no passage', () => {
  assert.ok(note.includes('(the review of the slice, 2026-09-10; before it a spanned change in flux took the deletion\'s by-id composer and Save wrote a comment with no passage though the change has one)'));
  const h = header(standIn);
  assert.ok(h.includes('before, the spanned change took the deletion\'s by-id composer'), 'the stand-in\'s header');
  assert.ok(h.includes('and Save wrote a comment with no passage though the change has one'));
});

// ── the Slice 2 build paragraph carries the gate with the write shape ──────────────────────────────────────────────

test('the Slice 2 build paragraph states the gate beside the write shape and points at the about paragraph', () => {
  assert.ok(build.includes('Comment on this change writes `comment {anchor, hintOffset, changeIds: [id], note}` over the change\'s span (a deletion: `{changeIds: [id], note}`; for a spanned change the card offers it only while the view carries the change\'s text, `spanCarried` in the about follow-on\'s paragraph below)'));
  assert.ok(panel.includes('if (c.about && c.about.on) args.changeIds = c.about.ids;'), 'the write shape the clause names');
});

// ── the two Tests indexes name the review's modules and this one ──────────────────────────────────────────────────

test('the paragraph\'s Tests sentence and the Tests bullet name the review\'s modules and this one, each in the tree, each described as its header reads', () => {
  const modules = ['file-comments-about-fixes.test.ts', 'file-comments-resolve-answered-fixes.test.ts', 'tools/file-comments-host-about-scale.test.mjs', 'tools/file-review-plan-about-flux.test.mjs'];
  for (const [name, text] of [['the paragraph', note], ['the Tests bullet', aboutBullet]]) {
    assert.ok(text.includes('From the about follow-on\'s review (2026-09-10):'), name + ' indexes the review');
    for (const m of modules) assert.ok(text.includes('`' + m + '`'), `${name} names ${m}`);
    assert.ok(text.includes('Comment on this change withheld in flux and in media mode and standing on a deletion'), name + ' says what the stand-in pins');
  }
  for (const m of modules) {
    const rel = m.includes('/') ? m : path.join('ui', 'webview', m);
    assert.ok(fs.existsSync(path.join(REPO, rel)), `${m} is in the tree`);
  }
  assert.ok(note.includes('`tools/file-review-plan-about-flux.test.mjs` (the withholding as recorded here and in the Slice 2 build paragraph held to the panel and the stand-in)'));
  assert.ok(aboutBullet.includes('`tools/file-review-plan-about-flux.test.mjs` holds the paragraph\'s account of Comment on this change withheld in flux and in media mode, and the Slice 2 build paragraph\'s clause, to the panel and the stand-in.'));
  // the descriptions against the modules' own headers
  assert.ok(header(standIn).includes('Comment on this change is withheld for a substitution or an insertion while the view\'s bytes are not the status\'s'));
  const resolve = header(read('ui', 'webview', 'file-comments-resolve-answered-fixes.test.ts'));
  assert.ok(resolve.includes('nor does the confirm survive the panel\'s close') && resolve.includes('The file-editing consent is asked once') && resolve.includes('A wheel while Reopen all holds the keyboard ends the offer'));
  const scale = header(read('tools', 'file-comments-host-about-scale.test.mjs'));
  assert.ok(scale.includes('a hundred thousand change-shaped ids') && scale.includes('refuses `no-change` inside the deadline'));
});
