// The seen follow-on's second review round (2026-09-09): the plan sentences that round found stale, held to the code.
//
// The first round's fix (the seen follow-on's review) changed what the send accepts and reworded the guide, and left four
// accounts in plans/file-review.md saying what the code no longer does. The seen paragraph said the send read the split
// after its own gesture, so a card on screen at the Send press counted for that send; since the fix the send accepts the
// seen set AS THE CONFIRM SHOWED IT (confirmSeen), and the press marks a card seen for the next confirm only (sendPress).
// The Send paragraph and decision 41 defined a seen change as one whose "card or mark" was on screen, while entryShown
// reads the card's place alone and the guide had already been reworded to the card. The seen paragraph said the unseen
// pending changes ARE the arrivals line's count, while that line also counts a detached arrival the split never sees.
// And three paragraphs still named scrollToSaved in the present tense after decision 43 retired it. A record that
// contradicts the code costs the next reader the search it was meant to save, so this module holds each corrected
// sentence to the source that makes it true. Synthetic: only the repo's own text.
// Run: node --test tools/file-review-plan-seen-review-2.test.mjs
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
const guide = read('docs', 'guide.md');
const seenFixes = read('ui', 'webview', 'file-comments-seen-fixes.test.ts');
const modelSeen = read('ui', 'webview', 'file-comments-model-seen.test.ts');
const sendSeen = read('ui', 'webview', 'file-comments-send-seen.test.ts');

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
const send = between('The confirm carries up to three checkboxes', 'The sequence is fixed: the message is built');
const d41 = between('41. **The Send\'s accept takes the changes you have seen', '42. **');
const tests = between('## Tests', '## Docs');

test('the send accepts the seen set as the confirm showed it, and the press\'s own mark counts for the next confirm: the paragraph and decision 41 say so, and the panel does so', () => {
  assert.ok(seen.includes('over the seen set as the confirm SHOWED it (`confirmSeen`, written at the confirm\'s render and rewritten with the option\'s words after a gesture; `pendingSplit` reads it while a confirm is up)'));
  assert.ok(seen.includes('so what the option and the count row said when the person pressed Send is what goes'));
  assert.ok(seen.includes('for the NEXT confirm and not this send (`sendPress`'));
  assert.ok(!seen.includes('counts as seen the way any gesture counts it'), 'the pre-fix account is gone');
  assert.ok(!FLAT.includes('reads the split after the send\'s own gesture'), 'nowhere in the plan');
  assert.ok(d41.includes('The send accepts the seen set as the confirm showed it: the Send press is a gesture and marks a card on screen seen, for the next confirm and not for this send.'));
  // the panel: the split reads the confirm's set, the render writes it, the in-place update rewrites it for every gesture but the send's own
  assert.ok(body(panel, 'private pendingSplit(s: Status): { seen: Hunk[]; unseen: Hunk[] } {').includes('return partitionPending(s.hunks || [], this.confirmSeen || this.seenKeys);'));
  assert.ok(panel.includes('this.confirmSeen = this.sendConfirm && s && !this.sending ? new Set(this.seenKeys || []) : null;'), 'the render writes the confirm\'s set');
  const sync = body(panel, 'private syncAcceptOption(cb: HTMLInputElement, s: Status): void {');
  assert.ok(/if \(this\.sendPress\) return;\n\s*this\.confirmSeen = new Set\(this\.seenKeys \|\| \[\]\);/.test(sync), 'the in-place update leaves the set alone under the send\'s press, and rewrites it otherwise');
  const doSend = panel.slice(panel.indexOf('async doSend(): Promise<void> {'), panel.indexOf('private async sendOnce('));
  const press = /this\.sendPress = true;\n\s*this\.gesture\(\);[^\n]*\n\s*this\.sendPress = false;/.exec(doSend);
  assert.ok(press, 'the send\'s gesture runs under sendPress');
  assert.ok(press.index < doSend.indexOf('const acceptIds = this.sendOpts.accept ? this.pendingSplit(s).seen.map((h) => String(h.id)) : [];'), 'and the split is read after it, over the confirm\'s set');
  assert.ok(body(panel, 'gesture(ev?: Event): void {').includes('if (press) this.sendPress = true;'), 'the key that sends is the send\'s own press too');
  // the stand-in pins the case the paragraph describes
  assert.ok(seenFixes.includes('the press marks it seen, the option keeps its words through the hold, and the send accepts nothing'));
  assert.ok(seenFixes.includes('the press marks the third seen, and the send accepts the two the list named'));
});

test('a seen change is one whose CARD was on screen: the Send paragraph, decision 41 and the guide say the card alone, as entryShown reads it', () => {
  assert.ok(!FLAT.includes('card or mark'), 'the plan nowhere promises the mark path');
  assert.ok(send.includes('a change whose card was on screen at one of the person\'s gestures (the card alone, as the arrivals follow-on\'s `entryShown` reads it: a mark in the text on screen with its card out of the box marks nothing seen), or that the panel\'s first status held'));
  assert.ok(d41.includes('a change whose card was on screen at one of their gestures, or that the panel\'s first status held, the arrivals follow-on\'s rule (the card alone: a mark in the text on screen with its card out of the box marks nothing seen)'));
  assert.ok(flat(guide).includes('whose card was in view when you scrolled, clicked, tapped, or pressed a key'), 'the guide\'s definition is the same');
  const shown = body(panel, 'private entryShown(e: Entry): boolean {');
  assert.ok(shown.includes('.fc-card[data-id="'), 'entryShown looks the card up');
  assert.ok(shown.includes('this.placed.get(key)') && shown.includes('card.getBoundingClientRect()'), 'and reads its place: the placed top in the margin layout, the card\'s box in the list');
  assert.ok(!/ownMarks|fc-mark|fc-ins|fc-del|markTop|dataset\.act/.test(shown), 'no mark path');
  const gesture = body(panel, 'gesture(ev?: Event): void {');
  assert.ok(gesture.includes('if (!this.entryShown(e)) continue;') && gesture.includes('this.seenKeys?.add(k);'), 'the gesture admits an arrival to the seen set through entryShown alone');
  // the model's docstring and the two seen test modules' headers said "card or mark" after the plan and the guide had dropped it
  // (the review's consolidation, 2026-09-09): the same rule, in every account of it
  for (const [name, text] of [['file-comments-model.ts', model], ['file-comments-model-seen.test.ts', modelSeen], ['file-comments-send-seen.test.ts', sendSeen]]) {
    assert.ok(!text.includes('card or mark'), name + ' promises no mark path');
  }
  assert.ok(model.includes('a change whose card was on screen at\n *  one of the person\'s gestures (the card alone, as the panel\'s entryShown reads it'), 'partitionPending\'s docstring says the card alone');
});

test('the unseen pending changes are among the arrivals the line counts, not that count: a detached arrival is in the line\'s count and never in the split', () => {
  assert.ok(seen.includes('every unseen pending change is among the arrivals the line under the header counts (that line\'s changes count takes in a detached arrival too, which `statusEntries` files as a change with pending off and the split, over the status\'s hunks, never sees, so the two numbers agree only while no detached change has arrived)'));
  assert.ok(!FLAT.includes('are the arrivals line\'s count'), 'the equality is not claimed');
  // nor by the model's docstring or the model-seen module's title (the review's consolidation, 2026-09-09)
  assert.ok(!model.includes('the same K the arrivals line counts') && !modelSeen.includes('are the arrivals line\'s count'), 'neither the model nor its tests claim the equality');
  assert.ok(flat(model.replace(/^\s*\* ?/gm, '')).includes('so the two numbers agree only while no detached change has arrived'), 'acceptOptionLabel\'s docstring carries the caveat (the docblock\'s continuation markers stripped before the wrap is collapsed)');
  const entries = body(model, 'export function statusEntries(');
  assert.ok(entries.includes('for (const d of detachedChanges(store)) {') && entries.includes('kind: "change", author: d.author, authorId: d.authorId, subject: "chg:" + d.id, pending: false });'), 'a detached change is a change entry with pending off');
  assert.ok(body(model, 'export function arrivalWords(').includes('counts[e.kind]++;'), 'the line counts every change entry');
  const split = body(model, 'export function partitionPending(');
  assert.ok(split.includes('for (const h of hunks)') && !split.includes('detached'), 'the split reads the hunks alone');
});

test('the save\'s scroll is history wherever the plan names scrollToSaved, and the panel has no such function: landSaved sets the focus and moves nothing', () => {
  const hits = Array.from(plan.matchAll(/scrollToSaved/g), (m) => m.index);
  assert.ok(hits.length >= 3, 'the three accounts still record what stood: ' + hits.length);
  for (const at of hits) {
    const around = flat(plan.slice(Math.max(0, at - 700), at + 700));
    assert.ok(around.includes('decision 43'), 'each mention stands with decision 43\'s retirement: ' + flat(plan.slice(at - 80, at + 80)));
  }
  assert.ok(FLAT.includes('decision 43 (2026-09-09, the arrivals follow-on below) retired the scroll and `scrollToSaved` with it: `landSaved`, before the composer closes as well, makes the saved card the focus and moves nothing, and a line at the panel\'s foot says where the card is'), 'the margin-layout paragraph');
  assert.ok(FLAT.includes('since decision 43 the same day the save\'s setter is `landSaved`\'s own call to `focusOn`, with no click on the card before it to set the focus and no scroll after it, and `scrollToSaved` is gone'), 'the focus paragraph');
  assert.ok(FLAT.includes('the save\'s landing (`landSaved`) finds no card for a comment the filter hides and raises no line for it, since this row says where the comment is; and the save moves nothing, hidden card or not (decision 43'), 'the filter paragraph');
  assert.ok(!FLAT.includes('the margin\'s scroll to a saved card (`scrollToSaved`) finds no card'), 'not stated as today\'s');
  assert.ok(!panel.includes('scrollToSaved'), 'the panel has no scrollToSaved');
  const land = body(panel, 'private landSaved(c: Composer, had: Set<string>, r: Status, note: string): boolean {');
  assert.ok(land.includes('if (this.margin) this.focusOn(key);') && land.includes('const side = this.cardWhere(key);'), 'the focus, then the side');
  assert.ok(!/scrollCard|scrollBoth|scrollIntoView|centerOn|showLoose|scrollTop\s*=[^=]/.test(land), 'no scroll');
  assert.ok(body(panel, 'private cardWhere(key: string): "above" | "below" | null {').includes('if (!p) return null;'), 'a card not placed (the filter hides it) is nothing to point at: no line');
  assert.ok(panel.includes('const hid = r !== null && c.kind !== "reply" && this.noteHiddenSave(before, note);'), 'the hidden comment\'s own row is raised by the save');
});

test('the plan names this module beside the seen follow-on\'s, in the paragraph and the Tests bullet', () => {
  const bullet = tests.slice(tests.indexOf('- The seen follow-on (2026-09-09):'), tests.indexOf('- The todo-file follow-on (2026-09-07):'));
  for (const text of [seen, bullet]) assert.ok(text.includes('`tools/file-review-plan-seen-review-2.test.mjs`'));
  assert.ok(fs.existsSync(path.join(REPO, 'tools', 'file-review-plan-seen-review-2.test.mjs')));
});
