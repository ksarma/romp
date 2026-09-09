// The seen follow-on's review (2026-09-09): the plan sentences the review found stale, held to the code.
//
// The review of the seen slice (decisions 41 to 43) found the plan saying things the slice itself had made false. The
// arrivals follow-on's paragraph still had the Send confirm's accept option "read" its arrivals count and listed the
// save's scroll among what fires the scroll event, both in the present tense, after decision 41 had moved the option to
// the seen split and decision 43 had retired the scroll; its pointer to the seen follow-on said "below" when that paragraph
// stands above. Decision 43 and the same paragraph called the "Sent to <session> at <time>" acknowledgment "the sent
// note", which CONTEXT.md's Note entry says it is not (tests/test_context_send_note.py scans the plan for the phrase, and
// went red). The Tests bullet credited file-comments-model-seen.test.ts with "resolve counts" the option lost with
// decision 42, and the margin-fixes module's account still described the save's scroll its cases now refuse. The
// contract paragraph said the host runs its self-check before every decision's write when doReject (reject and
// reject-all) had no call; the same review's host fix gave it one and moved the check onto the staged sidecar for every
// decision, and the sentence now says so. A record that contradicts the code costs the next
// reader the search it was meant to save, so this module holds each corrected sentence to the source that makes it
// true. Synthetic: only the repo's own text.
// Run: node --test tools/file-review-plan-seen-review.test.mjs
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
const model = read('ui', 'webview', 'file-comments-model.ts');
const host = read('tools', 'file-comments-host.mjs');
const context = read('CONTEXT.md');
const seenTest = read('ui', 'webview', 'file-comments-model-seen.test.ts');
const fixesTest = read('ui', 'webview', 'file-comments-margin-fixes.test.ts');

// The text between two markers, hard wraps collapsed so an assertion survives a rewrap.
function between(doc, from, to) {
  const a = doc.indexOf(from);
  assert.ok(a >= 0, `${JSON.stringify(from)} not found`);
  const b = doc.indexOf(to, a + from.length);
  assert.ok(b > a, `${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return doc.slice(a, b).replace(/\s+/g, ' ');
}
const SEEN = 'The seen follow-on (2026-09-09):';
const ARRIVALS = 'The arrivals follow-on (2026-09-09):';
const seen = between(plan, SEEN, ARRIVALS);
const arrivals = between(plan, ARRIVALS, '### Slice 3: region comments on images');
const contract = between(plan, 'The comments a decision stages equal the loaded ones apart', '**`fileCommentsSend`**, the send op:');
const margin = between(plan, '`file-comments-margin-fixes.test.ts` (over the first review\'s stand-in', '`file-comments-margin-fixes-browser.test.ts`');
const tests = between(plan, '\n## Tests', '\n## Docs');
const d43 = between(plan, '43. **A save never moves the view; a line says where the card is**', '## Open questions for the user');

test('the arrivals paragraph states the option\'s arrivals count as history, names decision 41 as what replaced it, and points at the seen follow-on above', () => {
  assert.ok(arrivals.includes('The Send confirm\'s accept option read "accept the N pending changes (M arrived since you last looked)" when arrivals included pending changes, until decision 41 (the seen follow-on above, the same day) moved it to the seen split'));
  assert.ok(arrivals.includes('says nothing of arrivals, which the line under the header counts (`acceptOptionLabel`; the seen follow-on\'s paragraph carries the words)'));
  assert.ok(!arrivals.includes('accept option reads "accept the N pending changes (M arrived'), 'the retired words are not stated as the option\'s today');
  assert.ok(arrivals.includes('both went with it (the seen follow-on above)'));
  assert.ok(!arrivals.includes('seen follow-on below'), 'the seen paragraph is above this one');
  assert.ok(plan.indexOf(SEEN) < plan.indexOf(ARRIVALS), 'and it is');
  // the model's option: the seen split's words, nothing of arrivals
  assert.ok(model.includes('export function acceptOptionLabel(seen: number, unseen: number): string {'));
  const label = model.slice(model.indexOf('export function acceptOptionLabel('), model.indexOf('\n}\n', model.indexOf('export function acceptOptionLabel(')));
  assert.ok(label.includes('" you have seen"') && label.includes('" pending)"'), 'the seen count and the unseen ones staying pending');
  assert.ok(!label.includes('arrived'), 'the option says nothing of arrivals');
  assert.ok(seen.includes('"accept the N pending changes you have seen"'), 'the seen paragraph carries the words');
});

test('the scroll event\'s sources are stated as they are: the lock\'s writes and a centering now, the save\'s scroll as history; the save\'s path scrolls nothing', () => {
  assert.ok(arrivals.includes('since the lock\'s writes and a centering fire it with no gesture behind them, as the save\'s scroll did while it stood (decision 43 retired it)'));
  assert.ok(!arrivals.includes('a centering and the save\'s scroll fire it'), 'the save\'s scroll is not listed among today\'s sources');
  assert.ok(arrivals.includes('a save, a send; never a timer'), 'the save is still a gesture');
  // the save's body, the landing and the side reading: from saveComposer to the end of cardWhere
  const start = panel.indexOf('async saveComposer(): Promise<void> {');
  const side = panel.indexOf('private cardWhere(', start);
  const save = panel.slice(start, panel.indexOf('\n  }\n', side));
  assert.ok(start >= 0 && side > start && save.includes('private landSaved('), 'the slice covers the save, the landing and the side reading');
  assert.ok(!/scrollCard|scrollBoth|scrollIntoView|centerOn|showLoose|scrollTop\s*=[^=]/.test(save), 'nothing on the save\'s path scrolls (decision 43); the side reading reads the track\'s scroll, it does not write it');
  assert.ok(/private centerOn\(key: string\): boolean \{/.test(panel) && /this\.scrollBoth\(want\);/.test(panel), 'a centering still writes the scroll, so the scroll event is still no gesture');
});

test('the line at the foot is named as CONTEXT.md names its neighbour: the acknowledgment line, never the sent note, in the arrivals paragraph and decision 43; the panel puts the saved line in that position', () => {
  assert.ok(arrivals.includes('the acknowledgment line\'s position at the panel\'s foot reads "Saved · the card is above" or "below" (`savedLine`'));
  assert.ok(d43.includes('the acknowledgment line\'s position at the panel\'s foot reads "Saved · the card is above" or "below", a button whose click scrolls the card into view'));
  const hit = /\bsent[ -]note\b/i.exec(plan);
  assert.ok(!hit, 'the plan never calls the acknowledgment a note (tests/test_context_send_note.py scans for the phrase): ' + (hit ? plan.slice(Math.max(0, hit.index - 60), hit.index + 40) : ''));
  assert.ok(context.replace(/\s+/g, ' ').includes('The panel\'s acknowledgment after a send (Sent to <session> at <time>, or Queued for <session>) is not a note either.'));
  const send = panel.slice(panel.indexOf('private renderSend('), panel.indexOf('private savedLine(): HTMLElement | null {'));
  const line = send.indexOf('const saved = this.savedLine();');
  const placed = send.indexOf('if (saved) box.appendChild(saved);', line);
  const ack = send.indexOf('if (this.sentNote) box.appendChild(el("div", "fc-note fc-sent", this.sentNote));', placed);
  assert.ok(line >= 0 && placed > line && ack > placed, 'the saved line is appended where the acknowledgment is, just before it');
  assert.ok(panel.includes('reply.queued ? "Queued for " + who : "Sent to " + who + " at " + clock(Date.now())'), 'the acknowledgment\'s words');
});

test('the Tests bullet credits the model-seen module with two counts and no resolve clause, as the module and the model have it', () => {
  const bullet = tests.slice(tests.indexOf('- The seen follow-on (2026-09-09):'), tests.indexOf('- The todo-file follow-on (2026-09-07):'));
  assert.ok(bullet.includes('the accept option\'s words with seen and unseen counts and with nothing seen, and no resolve clause, the option taking two counts since decision 42'));
  assert.ok(!bullet.includes('resolve counts'), 'no resolve count: decision 42 retired the clause');
  assert.ok(seenTest.includes('assert.equal(acceptOptionLabel.length, 2);'), 'the module pins the two counts');
  assert.ok(seenTest.includes('.includes("resolves"));'), 'and the absence of the clause');
  const label = model.slice(model.indexOf('export function acceptOptionLabel('), model.indexOf('\n}\n', model.indexOf('export function acceptOptionLabel(')));
  assert.ok(!label.includes('resolves'), 'the model has no resolve words');
  assert.ok(seen.includes('"resolves M comments" clause and the acknowledgment line\'s tail are retired'), 'the seen paragraph says so');
});

test('the contract paragraph\'s self-check claim follows the host\'s call sites: every decision\'s write only once accept, save and reject are all checked; an accept\'s and a save\'s otherwise', () => {
  // the review found the sentence saying "every decision" with doReject (reject and reject-all) calling no check. The
  // check may yet reach doReject (the contract asked for it over a decision); the plan then says every decision again,
  // and this pin refuses the one pairing that is false: the plan claiming more writes than the host checks
  const verbs = Array.from(host.matchAll(/requireCommentsUntouched\(ctx, store, loadedComments, ([^)]*)\)/g), (m) => m[1]);
  assert.ok(verbs.length >= 2, 'the host calls its self-check: ' + verbs.join(' | '));
  const checks = (verb) => verbs.some((v) => v.includes("'" + verb + "'"));
  assert.ok(checks('accept') && checks('save'), 'the accept and the save are checked');
  assert.ok(host.includes('function requireCommentsUntouched(ctx, store, loadedComments, verb) {'));
  const every = checks('accept') && checks('save') && checks('reject');
  const claim = 'the host checks that on the staged sidecar, before every decision\'s rename lands it (`requireCommentsUntouched`)';
  assert.equal(contract.includes(claim), every,
    every ? 'the host checks a reject\'s write too: the plan says every decision\'s' : 'a reject\'s write is not checked (doReject): the plan names the accept and the save');
  if (every) {
    const fn = host.slice(host.indexOf('function requireCommentsUntouched('), host.indexOf('\n}\n', host.indexOf('function requireCommentsUntouched(')));
    assert.ok(fn.includes('store[STAGED]') && fn.includes('fs.readFileSync(at'), 'the check reads the staged sidecar back, as the sentence says');
    assert.ok(host.includes('function landSidecar(') && host.includes('function stageSidecar('), 'a stage and a rename apart');
  } else {
    assert.ok(contract.includes('the host checks that before an accept\'s and a save\'s write (`requireCommentsUntouched`)'), contract);
  }
});

test('the margin-fixes module\'s account names its cases as the module has them since decision 43, in the note and the Tests section', () => {
  const cases = 'a whole-file comment saved while scrolled moving nothing, the line at the foot saying above and its click bringing the card into the track\'s box by one write onto both scrollers, the composer closing after (decision 43; before it, the save\'s own scroll), a reply\'s save scrolling nothing with the card the focus and its line\'s click centering the card, the saved comment read off the reply\'s store';
  const source = 'and at source the offset-free term and the save\'s focus and line raised before the composer\'s close, with no scroll';
  assert.ok(margin.includes(cases + ', ' + source), margin);
  assert.ok(tests.includes(cases + ' (one new comment; among several, the one whose body is the note; none identifiable, no line), ' + source));
  assert.ok(!plan.includes('the save\'s scroll before the composer\'s close'), 'no account still credits the module with the save\'s scroll');
  for (const name of [
    'test("a whole-file comment saved: the new card is loose at the top of the track, and the save moves nothing (decision 43',
    'the line at the foot says above and its click brings the card in on both scrollers',
    'test("a reply saved on a card with the text scrolled away from it: nothing scrolls (decision 43',
    'the card is the focus, level with its mark below the box, the composer closes, and the line says below — its click centers the card as an opened card is',
    'none identifiable, no line, and the composer closes all the same',
    'the save sets the focus and raises the line BEFORE the composer closes, and scrolls nothing (decision 43)',
  ]) assert.ok(fixesTest.includes(name), 'the module has the case: ' + name);
});

test('the plan names this module beside the seen follow-on\'s, in the paragraph and the Tests bullet', () => {
  const bullet = tests.slice(tests.indexOf('- The seen follow-on (2026-09-09):'), tests.indexOf('- The todo-file follow-on (2026-09-07):'));
  for (const text of [seen, bullet]) assert.ok(text.includes('`tools/file-review-plan-seen-review.test.mjs`'));
  assert.ok(fs.existsSync(path.join(REPO, 'tools', 'file-review-plan-seen-review.test.mjs')));
});
