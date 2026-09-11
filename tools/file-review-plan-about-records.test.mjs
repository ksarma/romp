// The about follow-on (2026-09-10) took every comment out of the change card, and its records commit reworded the
// plan's focus, filter and reply-place notes to say so, but four sentences elsewhere in plans/file-review.md kept the
// hosted era in the present tense (the review of the slice, 2026-09-10): the Show more row's paragraph still had a
// hosted comment's Reply and Resolve standing above the change card's Show more, which lifted the hosted parts; the
// paragraph's Tests sentence and the Tests section's bullet still credited file-comments-focus-verify.test.ts with a
// change card's hosted comment folding with the card, the reverse of what the rewritten module asserts; and the filter
// bullet still had the saved line ending when a comment came to ride a change card. Two more records drifted the same
// day: decision 46 said "thread" for a file comment's run of replies, the word CONTEXT.md sets aside for a forked side
// session and the plan's own terminology paragraph rules out, and the about paragraph cited the decoupling assessment
// as a report under the repo's notes, a place the tree does not have. The plan's pins for those rounds hold the
// reworded sentences and the modules' titles, not the superseded sentences, so the stale ones passed 15/15. This module
// holds each of them to the source that makes it true now: the panel (no hosted comment, the change card's order), the
// focus module (its title and its assertions), the filter module (its saved-line test), the model (the rule's own
// words), the vocabulary and the tree. The consolidation of the review (2026-09-10) added the relation's own names: the
// records (the Slice 2 lead, decision 45, the Docs restatement), the panel's comments, the ADR's consequences bullet and
// the host's changeIds note said "linked", "cross-linked" or "thread" for what CONTEXT.md's About entry calls "about",
// and the filter's option titles and the decision tag on a legacy binding still spoke in the hosted era's words ("comments
// on changes", "each with the comments made on it", "the change this comment is on"); the guide and the plan's filter
// paragraph had moved on. Each is held here to the entry's Avoid list and to the words the guide uses.
// Run: node --test tools/file-review-plan-about-records.test.mjs
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
const focusModule = read('ui', 'webview', 'file-comments-focus-verify.test.ts');
const filterModule = read('ui', 'webview', 'file-comments-filter-fixes.test.ts');
const context = read('CONTEXT.md');

// The text between two markers, hard wraps collapsed so an assertion survives a rewrap.
function between(doc, from, to) {
  const a = doc.indexOf(from);
  assert.ok(a >= 0, `${JSON.stringify(from)} not found`);
  const b = doc.indexOf(to, a + from.length);
  assert.ok(b > a, `${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return doc.slice(a, b).replace(/\s+/g, ' ');
}
const focusNote = between(plan, 'The focus follow-on (2026-09-08):', 'The anchors follow-on (2026-09-07):');
const aboutNote = between(plan, 'The about follow-on (2026-09-10):', '### Slice 3: region comments on images');
const tests = between(plan, '\n## Tests', '\n## Docs');
const focusBullet = tests.slice(tests.indexOf('- The focus follow-on (2026-09-08): `card-layout.test.ts` gains the focus rule'), tests.indexOf(' - The todo-file follow-on'));
const filterBullet = tests.slice(tests.indexOf('`ui/webview/file-comments-filter-fixes.test.ts` drives the second'), tests.indexOf('`ui/webview/file-comments-filter-saved-line.test.ts`'));
const aboutBullet = tests.slice(tests.indexOf('- The about follow-on (2026-09-10, decisions 45 and 46):'));
const d46 = between(plan, '46. **Resolve answered', '\n## Open questions');

// ── the Show more row's order: the hosted order is history, the comment card's is the one order ───────────────────

test('the Show more row paragraph states the hosted order as history and the comment card\'s as the one order, as the panel has it: no hosted comment, the change card\'s text, then its row, then its buttons', () => {
  assert.ok(focusNote.includes('(until the about follow-on, 2026-09-10, a hosted comment\'s Reply and Resolve so stood above the change card\'s one Show more, which lifted the hosted parts too: the verification review, 2026-09-09, raised both orders and the choice was recorded; with every comment on its own card there is one order, the comment card\'s, which the reply-place stand-ins assert)'));
  assert.ok(!focusNote.includes('Reply and Resolve so stand above'), 'the present tense is gone');
  assert.ok(!focusNote.includes('which lifts the hosted parts'), 'and so is the lift of hosted parts');
  assert.ok(!/renderHosted|fc-hosted/.test(panel), 'the panel draws no comment inside a change card');
  const diffAt = panel.indexOf('card.appendChild(diff);');
  assert.ok(diffAt >= 0, 'renderChangeCard appends the change\'s text');
  const actsAt = panel.indexOf('card.appendChild(acts);', diffAt);
  assert.ok(actsAt > diffAt, 'and then its action row');
  const betweenThem = panel.slice(diffAt, actsAt);
  assert.ok(/^card\.appendChild\(diff\);\n\s*card\.appendChild\(this\.clipRow\(c\.key\)\);/.test(betweenThem), 'the row right after the change\'s text');
  assert.ok(!/renderCard\(|fc-replies|fc-body fc-clip"/.test(betweenThem), 'and no comment, body or run of turns drawn between the text and the buttons');
  const place = read('ui', 'webview', 'file-comments-reply-place.test.ts');
  assert.ok(place.includes('["fc-card-head", "fc-body fc-clip", "fc-replies fc-clip", "fc-clip-row", "fc-composer fc-composer-in", "fc-actions"]'), 'the reply-place stand-in asserts the comment card\'s order');
});

// ── the focus module: described as it reads, in the paragraph and in the Tests bullet ────────────────────────────

test('the paragraph and the Tests bullet describe file-comments-focus-verify.test.ts as it reads: a comment a change answered folds on its own card, the change card folds its own text alone and hosts nothing, the short change\'s card offers no toggle', () => {
  for (const [name, text] of [['the paragraph', focusNote], ['the Tests bullet', focusBullet]]) {
    assert.ok(text.includes('a comment a change answered folding on its own card'), name + ' says whose card folds');
    assert.ok(text.includes('the change card folds its own text alone and hosts nothing'), name + ' says the change card hosts nothing');
    assert.ok(text.includes('the about follow-on\'s rewrite, 2026-09-10, of the hosted'), name + ' credits the rewrite');
    assert.ok(!text.includes('a change card\'s hosted comment folding with the card'), name + ' no longer credits the module with the hosted fold in the present');
    assert.ok(!text.includes('the hosted run is the only part cut'), name + ' no longer has a hosted run');
  }
  assert.ok(focusNote.includes('on a short one, whose card offers no toggle while the comment\'s does'));
  assert.ok(focusBullet.includes('on a long change and on a short one whose card offers no toggle'));
  // the module: its title and the assertions the descriptions paraphrase
  assert.ok(focusModule.includes('test("a comment bound to a change folds on its OWN card (the about follow-on): its run of turns is marked cut and scrolled to its end, and the card\'s own Show more lifts it; the change card folds its own text alone, counts the comment in a \'1 comment\' tag and hosts nothing: on a change whose own text is long, and on a short change, whose card offers no toggle while the comment\'s card does"'), 'the module\'s title');
  assert.ok(focusModule.includes('assert.equal(w.aside().querySelectorAll(".fc-hosted").length, 0, "no comment is drawn inside a change card");'));
  assert.ok(focusModule.includes('assert.equal(f.parts, 1, "the change\'s text alone: the comment\'s body and run are on the comment\'s own card");'));
  assert.ok(focusModule.includes('assert.equal(foldOf(w, CHG2).hidden, true, "the short change\'s card still offers no toggle");'));
  assert.ok(!focusModule.includes('hosted comment folding with the card'), 'the module pins no hosted fold');
  assert.ok(!/renderHosted|fc-hosted/.test(focusModule.replace(/querySelectorAll\("\.fc-hosted"\)/g, '')), 'the module names the hosted element only to count none of it');
  // the fixture is the legacy binding, read as answered: the description says "a comment a change answered", never "bound" (CONTEXT.md, About: Avoid)
  assert.ok(focusModule.includes('assert.equal(tag.textContent, "answered by a change", "the legacy binding\'s tag");'));
  assert.ok(context.includes('_Avoid_: bound to, linked to (the old binding the session\'s edit made)'));
  for (const [name, text] of [['the paragraph', focusNote], ['the Tests bullet', focusBullet]]) assert.ok(!/\bbound to a change\b/.test(text), name + ' does not say bound to');
});

test('the plan\'s account of tools/file-review-plan-focus-verify.test.mjs says the hosted fold is held as history, and that module\'s test says so in its title', () => {
  assert.ok(focusNote.includes('the re-lay, the save\'s focus and the fold\'s parts as recorded here, the hosted fold among them as history, held to the layout'));
  assert.ok(focusBullet.includes('holds the paragraph\'s re-lay, save and fold statements (the hosted fold as history) to the layout'));
  assert.ok(!focusNote.includes('the hosted fold as recorded here held to') && !focusBullet.includes('hosted-fold statements'), 'neither place holds the hosted fold as the present');
  const pin = read('tools', 'file-review-plan-focus-verify.test.mjs');
  assert.ok(pin.includes('test(\'the parts under the fold are recorded as the pass reads them: every fc-clip under the card (the hosted comments\\\' among them until the about follow-on), lifted by the card\\\'s one Show more\''), 'the focus pin holds the hosted parts as history');
});

// ── the filter module: the saved line stands when a change answers the comment ────────────────────────────────────

test('the filter bullet describes file-comments-filter-fixes.test.ts as it reads: the saved line stands when a change comes to answer the comment and ends at the count\'s click; the ride on a change card is history', () => {
  assert.ok(filterBullet.includes('the line standing when a change comes to answer the comment and its end at the count\'s click (the about follow-on, 2026-09-10; until it the comment rode the change card and the line ended there)'));
  assert.ok(!filterBullet.includes('the line\'s end when the comment comes to ride a change card'), 'the present-tense ride is gone');
  assert.ok(filterModule.includes('test("the saved line stands when the session answers the comment with a revision: a passage comment saved under Changes, then bound to a change by the poll\'s status (suggestionId), keeps its own card, hidden like every comment under Changes, so the line stays as it was; the change card counts the comment, and the count\'s click (All, the card shown) ends the line, for good"'), 'the module\'s title');
  assert.ok(filterModule.includes('assert.equal(savedLine(aside)?.textContent, LINE, "the line stands, its words unchanged: the comment\'s card is still hidden");'));
  assert.ok(filterModule.includes('assert.ok(!savedLine(aside), "the card shown: the line is over");'));
  assert.ok(filterModule.includes('assert.equal(count!.dataset.act, "fcaboutfirst");'), 'the count\'s click is the way to the comment');
  assert.ok(panel.includes('fcaboutfirst'), 'and the panel has the action');
});

// ── decision 46: the plan's own vocabulary ────────────────────────────────────────────────────────────────────────

test('decision 46 states the rule in the plan\'s vocabulary: since the person\'s last message on the comment, as the model\'s doc comment has it; the word CONTEXT.md sets aside for a forked side session appears nowhere in it', () => {
  assert.ok(d46.includes('since the person\'s last message on the comment (a reply of kind edit counts as an answer; the person\'s own later reply does not)'));
  assert.doesNotMatch(d46, /\bthreads?\b/i, 'a file comment\'s run of replies is not called by the forked-session word (CONTEXT.md, File comment and About: Avoid)');
  assert.ok(model.includes('with a turn by another author after the person\'s last turn on the comment'), 'the model\'s doc comment says the same');
  assert.ok(model.includes('export function answeredComments(cards: Card[]): Card[] {'));
  // the plan's own terminology paragraph and decision 17 rule the word out, so the decision now agrees with them
  assert.ok(plan.includes('a **file comment** is the object (never "thread", which in\nromp is a forked side session anchored to the chat)'), 'the terminology paragraph');
  assert.ok(plan.includes('17. **The object is a file comment** (2026-09-06), never a thread'), 'decision 17');
  assert.ok(context.includes('_Avoid_: thread (a comment thread is a forked side session anchored to the chat)'), 'CONTEXT.md, File comment');
  assert.ok(/its passage or its file, and about the changes it names\), thread/.test(context.replace(/\s+/g, ' ')), 'CONTEXT.md, About');
});

// ── the about paragraph's citation: a report outside the repo, said so ────────────────────────────────────────────

test('the about paragraph cites the decoupling assessment as a report kept outside the repo, by its path, and the tree bears that out: no notes directory, no report', () => {
  assert.ok(aboutNote.includes('the decoupling assessment of 2026-09-09 (a report kept outside the repo, at ~/romp-handoffs/romp-filereview-notes/decouple-assessment-report.txt)'));
  assert.ok(!aboutNote.includes('the repo\'s notes'), 'no pointer at a place the tree does not have');
  assert.ok(!fs.existsSync(path.join(REPO, 'notes')), 'the tree has no notes directory');
  for (const dir of ['plans', 'docs']) {
    for (const f of fs.readdirSync(path.join(REPO, dir), { recursive: true })) {
      const full = path.join(REPO, dir, f);
      if (!fs.statSync(full).isFile() || !/\.(md|txt)$/.test(f)) continue;
      if (full === path.join(REPO, 'plans', 'file-review.md')) continue;
      assert.ok(!/decoupling assessment/i.test(fs.readFileSync(full, 'utf8')), `${dir}/${f}: the report is not in the tree, so no document but the plan cites it`);
    }
  }
  assert.ok(!/`~\/romp-handoffs/.test(plan), 'the path is prose, not a backticked identifier (the about pin checks backticked names against the code)');
});

// ── this module is named where the plan indexes its pins ──────────────────────────────────────────────────────────

test('the Tests section\'s about bullet names this module and says what it holds; the focus paragraph and its bullet name it too, since it cites them (the focus audit reads the headers)', () => {
  assert.ok(aboutBullet.includes('`tools/file-review-plan-about-records.test.mjs` holds the hosted-era sentences the follow-on superseded elsewhere in this document (the Show more row\'s order, the focus module\'s fold, the filter module\'s saved line) to the panel and the modules as history, decision 46 to the vocabulary, and the note\'s citation of the assessment to the tree (the report is outside it)'));
  assert.ok(focusNote.includes('From the about follow-on\'s review (2026-09-10), `tools/file-review-plan-about-records.test.mjs` holds the sentences here the follow-on superseded, the Show more row\'s order and the focus module\'s fold, to the panel and the module as history.'));
  assert.ok(focusBullet.includes('From the about follow-on\'s review (2026-09-10), `tools/file-review-plan-about-records.test.mjs` holds this paragraph\'s superseded sentences, the Show more row\'s order and the focus module\'s fold, to the panel and the module as history.'));
});

// ── the relation's names: CONTEXT.md's About entry, in the records and the code (the consolidation, 2026-09-10) ─────

const adr = read('docs', 'adr', '0002-file-comments-in-the-track-changents-sidecar.md');
const host = read('tools', 'file-comments-host.mjs');
const settings = read('ui', 'webview', 'settings.ts');
const guide = read('docs', 'guide.md').replace(/\s+/g, ' ');
const slice2Lead = between(plan, 'User-visible: change cards grouped by paragraph with Accept, Reject, Accept all, Reject all, and', 'Acceptance: accept changes the sidecar only');
const d45 = between(plan, '45. **A comment names the changes it is about by stored ids the person picks', '46. **Resolve answered');
const docsSection = between(plan, '\n## Docs', '\n## Deliberately not in v1');

test('the records and the code say each carries a tag for the other, never linked or cross-linked: the Slice 2 lead, decision 45, the Docs restatement, the about paragraph, the panel\'s comments (CONTEXT.md, About: Avoid)', () => {
  assert.ok(/linked to \(the old binding the session's edit made\)/.test(context.replace(/\s+/g, ' ')), 'the entry sets "linked" aside for the old binding');
  for (const [name, text] of [['the Slice 2 lead', slice2Lead], ['decision 45', d45], ['the Docs section', docsSection], ['the about paragraph', aboutNote]]) {
    assert.doesNotMatch(text, /\bcross-linked\b|\blinked (?:by|to)\b/i, name + ' names the relation as the entry does');
  }
  assert.ok(slice2Lead.includes('its own card in the list, the comment and the change each carrying a tag for the other; the about follow-on, 2026-09-10.'));
  assert.ok(d45.includes('the card wears "about a change" and the change card "N comments", each a tag for the other; the message says "about your change …" after the passage.'));
  assert.ok(docsSection.includes('that a comment is never shown inside a change\'s card and the comment and the change each carry a tag for the other, that a selection inside a change leaves an ordinary comment with the same box checked'), 'the Docs restatement says what the guide says');
  assert.ok(guide.includes('every comment is its own card, and the comment and the change each carry a tag for the other, **about a change** on the comment'), 'and the guide says it');
  assert.doesNotMatch(panel, /linked by tags|cross-linked/, 'the panel\'s own comments');
  assert.ok(panel.includes('no comment is drawn inside a\n//     change\'s card, and each carries a tag for the other ("about N changes" on the comment, "N comments" on the change).'), 'the header');
  assert.ok(panel.includes('a comment about a change is its own card,\n    // each carrying a tag for the other); "comments" shows the comment cards and no change card'), 'renderCards');
});

test('the format\'s key is not called a thread: the ADR\'s consequences bullet and the host\'s changeIds note say what the other editors set it for (CONTEXT.md, File comment and About: Avoid)', () => {
  const bullet = between(adr, '- Under that rule the sidecar now carries six additive fields on a comment', '- A romp-only field is read defensively');
  assert.ok(bullet.includes('romp never writes the format\'s own `suggestionId`, the key the other editors set on a comment their change answers, and reads one it finds as the change that answered the comment.'));
  assert.doesNotMatch(bullet, /\bthreads?\b/i, 'the ADR');
  const note = between(host, '// `changeIds` is the person\'s own pick of the changes a comment is ABOUT', 'function readChangeIds(args) {').replace(/ \/\/ /g, ' ');
  assert.ok(note.includes('takes its id from the first change\'s current offset (a detached change\'s last place), where the other hosts put a comment whose `suggestionId` names the change.'));
  assert.doesNotMatch(note, /\bthreads?\b/i, 'the host\'s note');
  const hostTest = read('tools', 'file-comments-host-about.test.mjs');
  assert.ok(hostTest.includes('where the other hosts put a comment whose suggestionId names the change'), 'and the host test\'s message');
  assert.doesNotMatch(hostTest, /change threads/, 'the host test');
});

test('the filter\'s option titles and the decision tag on a legacy binding speak as the guide and the plan\'s filter paragraph do: comments about changes, each counting the comments about it, the change that answered this comment; never the hosted era\'s "on"', () => {
  assert.ok(panel.includes('const commentsTitle = "Show only the comments, comments about changes among them; "'), 'the Comments option');
  assert.ok(panel.includes('const changesTitle = "Show only the changes, each counting the comments about it"'), 'the Changes option');
  assert.doesNotMatch(panel, /comments made on it|including comments on changes/, 'the hosted era\'s titles are gone');
  assert.ok(guide.includes('**Comments** lists only the comments, comments about changes among them, and hides the change marks in the file; **Changes** lists only the changes, each counting the comments about it'), 'the guide\'s words, which the titles follow');
  assert.ok(plan.replace(/\s+/g, ' ').includes('**Changes** lists the change cards alone, each counting the comments about it (before the about follow-on, each with the comments made on it drawn inside)'), 'the plan\'s filter paragraph, which records the old words as history');
  assert.ok(settings.includes('"changes" (change cards, each counting the comments about it; no comment highlights or region rectangles)'), 'the setting\'s comment');
  assert.ok(panel.includes(' : about.length ? " the change this comment is about" : " the change that answered this comment");'), 'the decision tag: about for the person\'s pick, answered for a legacy binding');
  assert.doesNotMatch(panel, /this comment is on"/, 'never "on a change"');
  assert.ok(/on a change \(a comment is on its passage or its file, and about the changes it names\)/.test(context.replace(/\s+/g, ' ')), 'the rule the words follow');
  // the stand-ins pin the same words
  const filterReview = read('ui', 'webview', 'file-comments-filter-review.test.ts');
  assert.ok(filterReview.includes('"Show only the comments, comments about changes among them; the change marks in the text are hidden with the change cards"'));
  assert.ok(filterReview.includes('"Show only the changes, each counting the comments about it; the comment highlights in the text are hidden with the comment cards"'));
  const changesReview = read('ui', 'webview', 'file-comments-changes-review2.test.ts');
  assert.ok(changesReview.includes('assert.equal(tag.title, "You accepted the change that answered this comment"'));
  assert.ok(changesReview.includes('assert.equal(tag2.title, "You rejected the change that answered this comment");'));
});

// ── the list layout's places: the guide and the plan say where the ids-only line and the Reopen all offer stand ─────

test('the guide and the plan state the list layout\'s places as the panel has them: the ids-only line by layout, the Reopen all offer under the header in the list (the consolidation, 2026-09-10)', () => {
  // the guide's vocabulary for the layouts, set by the saved line's sentence
  assert.ok(guide.includes('In the list under a narrow column, the line stands under the panel\'s header instead.'), 'the saved line\'s precedent');
  assert.ok(guide.includes('a deletion, whose text is no longer in the file, takes a comment about the change alone, laid beside its mark (in the list under a narrow column, listed like any other card).'));
  assert.ok(guide.includes('offers **Reopen all** where the sent acknowledgment stands (in the list under a narrow column, under the panel\'s header) until your next scroll, click, tap, or key.'));
  assert.ok(aboutNote.includes('or, in the list layout, where no card is laid at any point, that the comment names the change instead of a passage (the review\'s second round, 2026-09-10)'));
  assert.ok(d46.includes('puts "Reopen all" in the acknowledgment\'s position (the margin layout\'s Send section; in the list layout, whose Send section is the scroller\'s foot and left the offer off screen after the click, under the header: the review\'s second round, 2026-09-10) until the person\'s next gesture'));
  // the panel: the line by layout, the offer by layout
  assert.match(panel, /this\.margin \? "The removed text is not in the file, so the comment is laid at the change's point\."\s*: "The removed text is not in the file, so the comment names the change instead of a passage\."/);
  assert.ok(panel.includes('private reopenLineHead(): HTMLElement | null {'));
  assert.ok(panel.includes('return this.margin || this.reopenAll === null ? null : this.reopenLine(this.reopenAll.length);'), 'the head\'s offer in the list layout alone');
  assert.ok(panel.includes('if (this.reopenAll !== null && this.margin) box.appendChild(this.reopenLine(this.reopenAll.length));'), 'the Send section\'s in the margin layout alone');
  assert.ok(panel.includes('const offer = this.reopenLineHead();\n    if (offer) head.appendChild(offer);'), 'renderHead appends it');
  // the guide's pins carry the same sentences
  const guidePins = read('tests', 'test_guide_files_about.py');
  assert.ok(guidePins.includes('laid beside its mark (in the "\n              "list under a narrow column, listed like any other card).'));
  assert.ok(guidePins.includes('"(in the list under a narrow column, under the panel\'s header) until your next scroll, click, tap, or key."'));
});

test('both Tests indexes name the second round\'s modules and say what each holds, and the browser leg\'s two later cases; every module named is in the tree and the leg\'s title has the cases', () => {
  for (const [name, text] of [['the about paragraph', aboutNote], ['the Tests bullet', aboutBullet]]) {
    assert.ok(text.includes('From its second round (2026-09-10): `file-comments-about-review2.test.ts` (the stand-in with the layout switchable: the composer\'s about ids pruned as a status retires a change, a selection starting exactly at a deletion\'s point, the deletion marks a drag crosses, the kind cue\'s title by source, the ids-only line by layout), `file-comments-resolve-answered-review2.test.ts` (the Reopen all offer\'s place by layout and the keyboard after a run the confirm\'s Resolve began from the keyboard) and `file-comments-arrivals-about.test.ts` (a session\'s reply on a comment about a pending change shows on the comment\'s own card, never the change\'s).'), name);
  }
  for (const m of ['file-comments-about-review2.test.ts', 'file-comments-resolve-answered-review2.test.ts', 'file-comments-arrivals-about.test.ts']) {
    assert.ok(fs.existsSync(path.join(REPO, 'ui', 'webview', m)), m + ' is in the tree');
  }
  assert.ok(aboutNote.includes('a drag across the insertion\'s end with its highlight painting in the other view too, the deletion\'s label and the card laid level with its mark'));
  const leg = read('ui', 'webview', 'file-comments-about-browser.test.ts');
  assert.ok(leg.includes('a drag across the insertion\'s end is a passage comment over the whole selection with the option, its highlight and the one inside the mark painting in the other view too'), 'the leg\'s title has the case');
  // the modules hold what the indexes say
  const review2 = read('ui', 'webview', 'file-comments-about-review2.test.ts');
  assert.ok(review2.includes('pruneAbout') && review2.includes('STARTING exactly at a deletion\'s point') && review2.includes('The ids-only composer\'s line says what the layout does'));
  const resolve2 = read('ui', 'webview', 'file-comments-resolve-answered-review2.test.ts');
  assert.ok(resolve2.includes('In the LIST layout (the narrow pane, the panel under the text) the Reopen all offer stands under the header') && resolve2.includes('Enter on the confirm\'s Resolve'));
  const arrivals = read('ui', 'webview', 'file-comments-arrivals-about.test.ts');
  assert.ok(arrivals.includes('marks the comment\'s own card new, and never the change\'s card'));
});
