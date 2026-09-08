// The plan's filter follow-on note records the review's fixes, and the UX paragraph states the counts
// as the panel renders them; the panel, the model and the guide do what both say.
//
// The filter follow-on's review round (2026-09-07) changed six panel behaviors — the Changes option's
// detached clause, a line for a comment saved while Changes is chosen, the option titles while the
// editor is up, the head rows that stand above the filter's row, the reply's place for a comment bound
// to a change under Comments, and the tag and cue titles for a detached change — and the note under
// Slice 2 (plans/file-review.md, "The filter follow-on (2026-09-07)") said none of them, while the UX
// paragraph ("The surface, in its Slice 2 state") said every option carries its count, though All
// carries none (review finding, 2026-09-07). The other pins (tools/file-review-plan.test.mjs,
// tools/file-review-plan-kind-cue.test.mjs, tests/test_guide_files_filter.py) hold only statements the
// note made before, so nothing held the plan to the new behaviors or caught the count. The plan now
// says all of it, and this module holds each statement to its source: the panel's option labels and
// titles, the model's label and counts, the panel's saved-line state and its ends, the filter block's
// editing branch, the `underToggles` insertion, `replyAway`'s Comments read, the tag and cue titles, and
// the guide's counts sentence — and the suites the note names exist and drive what it says. Synthetic:
// only the repo's own text.
// Run: node --test tools/file-review-plan-filter-review.test.mjs
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

// A span of the plan, hard wraps collapsed so an assertion survives a rewrap.
function section(from, to) {
  const a = plan.indexOf(from);
  assert.ok(a >= 0, `heading ${JSON.stringify(from)} not found in the plan`);
  const b = plan.indexOf(to, a + from.length);
  assert.ok(b > a, `heading ${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return plan.slice(a, b).replace(/\s+/g, ' ');
}
// The follow-on note: from its lead to the blank line (the Tests bullet later opens with the same words;
// the first hit is the note under Slice 2).
const noteAt = plan.indexOf('The filter follow-on (2026-09-07):');
assert.ok(noteAt >= 0, 'the follow-on note is in the plan');
const note = plan.slice(noteAt, plan.indexOf('\n\n', noteAt)).replace(/\s+/g, ' ');
const surface = section('### The surface, in its Slice 2 state', '### Commenting from either view, and in every format');
const tests = section('## Tests', '## Docs');
// The panel's filter block: from the offer to the row that answers a toggle.
const filterBlock = panel.slice(panel.indexOf('if (filterOffered(s)) {'), panel.indexOf('const underToggles ='));
assert.ok(filterBlock.length > 0, 'the filter block is found');

test('the UX paragraph says Comments and Changes carry their counts and All none; the panel labels them so, and the guide says the same', () => {
  assert.ok(surface.includes('narrows the list and the marks to one kind, Comments and Changes carrying their counts and All none, and is kept the same way'));
  assert.ok(!surface.includes('each option carrying its count'), 'the sentence that gave All a count is gone');
  assert.ok(filterBlock.includes('["all", "All", "Show every comment and change"],'), 'All: a bare label, no count');
  assert.ok(filterBlock.includes('["comments", "Comments " + n.comments, commentsTitle],'), 'Comments carries its count');
  assert.ok(filterBlock.includes('["changes", "Changes " + n.changes, changesTitle],'), 'Changes carries its count');
  assert.ok(guide.replace(/\s+/g, ' ').includes('Comments and Changes show their counts.'), 'the guide names the two that carry one');
  assert.ok(note.includes('agree; All carries no count.'), 'the note says it too');
});

test('the note says the Changes option carries the label\'s detached count and its title names the group; the panel and the model do', () => {
  assert.ok(note.includes('A detached change is neither an open comment nor a pending change, so the Changes option carries the label\'s detached count after its own, "Changes 0 · 1 detached", and its title says the detached changes are listed in a group of their own'));
  assert.ok(note.includes('a file holding detached changes alone does not read as one with nothing to show (the review, 2026-09-07)'));
  assert.ok(filterBlock.includes('const d = s && s.store ? detachedChanges(s.store).length : 0;'), 'the header counts the detached changes apart');
  assert.ok(filterBlock.includes('const b = btn(key === "changes" && d ? label + " · " + d + " detached" : label, "fcfilter", "fileview-btn fc-toggle");'), 'the clause follows the count on Changes alone');
  assert.ok(filterBlock.includes('" listed too, in a group of " + (d === 1 ? "its" : "their") + " own"'), 'the title names the group');
  // the label's own clause, and the counts that leave detached changes out
  assert.ok(model.includes('+ (d ? " · " + plural(d, "detached change", "detached changes") : "");'), 'actionLabel carries the detached clause');
  assert.ok(/export function cardCounts\(s: Status \| null\): \{ comments: number; changes: number \} \{\n[^\n]*\n\s+return \{ comments: s\.store\.comments\.filter\(\(c\) => !c\.resolved\)\.length, changes: \(s\.hunks \|\| \[\]\)\.length \};/.test(model), 'cardCounts: open comments and pending hunks, nothing detached');
  assert.ok(/a detached change is neither pending\s*\*?\s*nor counted here/.test(model), 'and says so');
});

test('the note says a comment saved under Changes gets a dismissable line at the top of the list with the ends it names; the panel keeps that state', () => {
  assert.ok(note.includes('the panel keeps the saved comment\'s id (`hiddenSaved`) and renders a dismissable line at the top of the list saying the comment is saved and that All or Comments shows it (`hiddenSavedRow`)'));
  assert.ok(note.includes('the line ends once the card shows, the comment is gone from the file, the ✕ is clicked, or the panel closes, a later return to Changes does not bring it back, and the kept choice is unchanged'));
  assert.ok(note.includes('a comment made from a change card\'s Reply rides that card under Changes and gets no line'));
  assert.ok(/^\s+hiddenSaved: string \| null = null;/m.test(panel), 'the kept id');
  assert.ok(panel.includes('const hid = r !== null && c.kind !== "reply" && this.noteHiddenSave(before, note);'), 'a save, not a reply, may raise the line');
  assert.ok(panel.includes('if (!mine || mine.hunk !== null || this.activeFilter() !== "changes") return false;'), 'only a comment on no change, under Changes');
  assert.ok(panel.includes('"Your comment is saved; its card" + (mark ? " and " + mark + " are" : " is")'), 'the line says the comment is saved');
  assert.ok(panel.includes('" hidden while Changes is chosen above (All or Comments shows " + (mark ? "them" : "it") + ")."'), 'and names the options that show it');
  assert.ok(panel.includes('const x = btn("✕", "fchiddenx", "fileview-btn fc-x");'), 'dismissable');
  assert.ok(panel.includes('fchiddenx: () => { this.hiddenSaved = null; this.render(); },'), 'the ✕ ends it');
  assert.ok(panel.includes('if (!card || filter !== "changes" || card.hunk !== null) { this.hiddenSaved = null; return null; }'), 'the card showing, or gone, ends it for good');
  // the close ends it: the assignment stands in the panel's close, between the landing clear and the poll stop
  assert.ok(/this\.clearLanding\(\);[^\n]*\n\s+this\.hiddenSaved = null;[^\n]*\n\s+this\.stopPoll\(\);/.test(panel), 'closing the panel ends it');
  // at the top of the list: the row is appended before the empty states and the cards
  const list = panel.slice(panel.indexOf('private renderCards('), panel.indexOf('private renderCard('));
  const at = list.indexOf('const saved = this.hiddenSavedRow(filter);');
  assert.ok(at >= 0 && list.indexOf('if (saved) list.appendChild(saved);') > at, 'the line is appended');
  assert.ok(at < list.indexOf('if (!cards.length && !view.cards.length && filter === "changes") {'), 'before the Changes empty state');
  assert.ok(at < list.indexOf('if (view.cards.length) {'), 'before the change cards');
  assert.ok(at < list.indexOf('const open = cards.filter((c) => !c.resolved)'), 'before the comment cards');
  assert.ok(!panel.includes('saveSettings({ commentsFilter: "all" })'), 'the kept choice is not changed for it');
});

test('the note says the filter row stays while the editor is up and its titles say the editor keeps the marks; the panel\'s filter block branches on editing', () => {
  assert.ok(note.includes('While the Slice 5 editor is up the filter row is offered all the same (Show changes inline is not: the editor draws every change itself), and the option titles say the editor keeps every change marked in its text rather than that the marks are hidden'));
  assert.ok(panel.includes('if (s && (s.hunks || []).length && !this.ctx.editing()) {'), 'Show changes inline is withheld while editing');
  assert.ok(panel.includes('if (filterOffered(s)) {'), 'the filter is offered on the cards alone');
  assert.ok(filterBlock.includes('const editing = this.ctx.editing();'), 'the block reads the editor state');
  assert.ok(filterBlock.includes('(editing ? "the editor keeps every change marked in its text" : "the change marks in the text are hidden with the change cards")'), 'Comments: the editor keeps its marks');
  assert.ok(filterBlock.includes('+ (editing ? "" : "; the comment highlights in the text are hidden with the comment cards")'), 'Changes: no claim of hidden highlights the editor never paints');
});

test('the note says the Track scope choice, the Stop confirm and the track slot\'s rows stand above the filter\'s row; the panel inserts them there', () => {
  assert.ok(note.includes('The rows answering a click on the toggles\' row, the Track scope choice, the folder Stop confirm and the track slot\'s loader and refusal, are inserted above the filter\'s row, directly under the toggles (`underToggles`), and the filter\'s row is under the toggles again once the question is answered; the other head rows keep their place below it'));
  assert.ok(panel.includes('let filterRow: HTMLElement | null = null;'), 'the filter row is kept for the insertion');
  assert.ok(filterBlock.includes('filterRow = seg;'));
  assert.ok(panel.includes('const underToggles = (n: HTMLElement): void => { head.insertBefore(n, filterRow); };'), 'insertBefore the filter row (appended when there is none)');
  assert.ok(panel.includes('underToggles(pick);'), 'the Track scope choice');
  assert.ok(panel.includes('underToggles(stop);'), 'the folder Stop confirm');
  assert.ok(panel.includes('if (n.nodeType === 1 && (n as HTMLElement).dataset.slot === "track") underToggles(n as HTMLElement);'), 'the track slot\'s loader and refusal');
  // the other head rows are appended, never inserted above the filter's row (whether or not the track slot's share their line)
  assert.ok(/for \(const n of \[[^\]]*this\.errRow\("head"\), this\.errRow\("poll"\), this\.errRow\("edit"\)\]\) if \(n\) head\.appendChild\(n\);/.test(panel), 'the other head rows are appended below');
  assert.ok(!/underToggles\(this\.errRow\("(head|poll|edit|save)"\)/.test(panel), 'and none of them goes above the filter');
});

test('the note says under Comments a bound comment is read as one on no change for the reply\'s place, the tag title says pending or detached, and a detached change\'s cue offers no decision; the panel does each', () => {
  assert.ok(note.includes('Under Comments a comment bound to a change is read as one on no change when the reply\'s box is placed (`replyAway`), so a resolved bound comment\'s line names the Resolved fold, where its card is, and Cancel focuses that fold; Comments never names a "… N more changes" row it does not render'));
  assert.ok(panel.includes('const card = this.activeFilter() === "comments" ? { ...found, hunk: null } : found;'), 'replyAway reads the bound comment as one on none under Comments');
  assert.ok(panel.includes('if (card.resolved && card.hunk === null) return { gone: false, back: "fcresolved",'), 'so the Resolved fold is the row that hides it');
  assert.ok(note.includes('The "on a change" tag\'s title says the change is pending only when it is among the status\'s hunks and says detached otherwise, naming the Detached changes group, and a detached change card\'s kind cue offers no accept or reject'));
  assert.ok(panel.includes('const pending = !!this.status && (this.status.hunks || []).some((h) => h.id === c.hunk!.id);'), 'pending is read from the status\'s hunks');
  assert.ok(panel.includes('t.title = pending ? "This comment is on a pending change; All or Changes above shows the change\'s card"'), 'the pending title');
  assert.ok(panel.includes(': "This comment is on a detached change, whose text the file no longer holds; All or Changes above shows the change\'s card, under Detached changes";'), 'the detached title names the group');
  assert.ok(panel.includes('kind.title = c.detached ? "A change the session made to the file, whose text the file no longer holds; nothing here accepts or rejects it" : "A change the session made to the file, for you to accept or reject";'), 'the cue offers no decision on a detached change');
});

test('the note and the Tests bullet name the review suite and this pin, both exist, and the suite drives what the note says', () => {
  for (const rel of ['ui/webview/file-comments-filter-review.test.ts', 'tools/file-review-plan-filter-review.test.mjs']) {
    assert.ok(note.includes('`' + rel + '`'), 'the note names ' + rel);
    assert.ok(tests.includes('`' + rel + '`'), 'the Tests bullet names ' + rel);
    assert.ok(fs.existsSync(path.join(REPO, rel)), rel + ' exists');
  }
  assert.ok(tests.includes('drives the review\'s six fixes over the same stand-in'));
  const suite = read('ui', 'webview', 'file-comments-filter-review.test.ts');
  for (const phrase of ['Changes 0 · 1 detached', 'saved under Changes', 'while the editor is up the filter row is offered', 'above the filter\'s', 'DETACHED change wears the \'on a change\' tag', 'not a \'… N more changes\' row Comments never renders']) {
    assert.ok(suite.includes(phrase), 'the review suite drives: ' + phrase);
  }
});
