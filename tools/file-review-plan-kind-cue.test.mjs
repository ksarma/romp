// The plan's filter follow-on note describes the kind cue and the keyboard's return in literal terms,
// and the sheets and the panel do what it says.
//
// The filter follow-on (plans/file-review.md, "The filter follow-on (2026-09-07)") first said the kind
// word is rendered "in the note's dress" and that Escape or Cancel "hands the keyboard to All". Neither
// phrase named the thing it meant: the first is the `.fc-kind` rule copying `.fc-note`'s color and size,
// and "note" is a word CONTEXT.md lists under _Avoid_ for a file comment, so a reader could take it for
// the comment's own text; the second is a focus move to the All button (review finding, 2026-09-07,
// under the repo's rule that a literal phrase is used where one exists). The note now names the rule,
// the tokens and the button, and this module holds those statements to their sources: `.fc-kind` and
// `.fc-note` carry the same color and size in both sheets; the change edge reads the token the note
// names; the panel's hidden-card case sends the keyboard to the first `fcfilter` button, and the header
// offers All first; and the note's prose uses "note" only for itself, never for the rule or the
// comment. tools/file-review-plan.test.mjs pins the rest of the note. Synthetic: only the repo's own
// text.
// Run: node --test tools/file-review-plan-kind-cue.test.mjs
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
const context = read('CONTEXT.md');
const sheets = { 'styles.css': read('ui', 'webview', 'styles.css'), 'feed.css': read('ui', 'webview', 'feed.css') };

// The follow-on note, hard wraps collapsed so an assertion survives a rewrap (the Tests bullet later in
// the plan opens with the same words; the first hit is the note under Slice 2).
const noteAt = plan.indexOf('The filter follow-on (2026-09-07):');
assert.ok(noteAt >= 0, 'the follow-on note is in the plan');
const note = plan.slice(noteAt, plan.indexOf('\n\n', noteAt)).replace(/\s+/g, ' ');
// …and its prose alone: code spans (`.fc-note`, `settings.ts`) are names, not words.
const prose = note.replace(/`[^`]*`/g, '');

// A rule's declarations, by selector, from one sheet's file-comments block.
function decls(css, selector) {
  const m = new RegExp('^' + selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ' \\{ ([^}]*) \\}$', 'm').exec(css);
  assert.ok(m, selector + ' is a one-line rule in the sheet');
  return m[1].split(';').map((d) => d.trim()).filter(Boolean);
}

test('the note says the kind word is styled like .fc-note, and both sheets give .fc-kind that rule\'s color and size', () => {
  assert.ok(note.includes('styled like `.fc-note` (`--dim`, 0.86em; the `.fc-kind` rule)'), 'the note names the rule it copies and the one that copies it');
  for (const [name, css] of Object.entries(sheets)) {
    const kind = decls(css, '.fc-kind'), ref = decls(css, '.fc-note');
    for (const d of ['color: var(--dim)', 'font-size: 0.86em']) {
      assert.ok(ref.includes(d), name + ': .fc-note has ' + d);
      assert.ok(kind.includes(d), name + ': .fc-kind has ' + d);
    }
  }
});

test('the note names the edge\'s width and tokens, and the sheets\' data-cue rules read them', () => {
  assert.ok(note.includes('a 3px border in the accent for a comment (a region is one) and in `--text-muted` for a change'));
  for (const [name, css] of Object.entries(sheets)) {
    assert.ok(css.includes('.fc-card[data-cue="comment"]:not(.fc-card-detached) { border-left: 3px solid var(--accent); }'), name + ': the comment edge');
    assert.ok(css.includes('.fc-card[data-cue="change"]:not(.fc-card-detached) { border-left: 3px solid var(--text-muted); }'), name + ': the change edge');
  }
});

test('the note says Escape or Cancel moves the focus to the All button, and the panel sends it to the first filter button, which is All', () => {
  assert.ok(note.includes('Escape or Cancel moves the focus to the All button, the one that brings the card back'));
  // Escape in the box cancels; Cancel and Escape close the composer, which hands a hidden reply's keyboard to focusAway
  assert.match(panel, /if \(e\.key === "Escape"\) return "cancel";/, 'Escape is the cancel action');
  assert.match(panel, /else if \(act === "cancel"\) \{ e\.preventDefault\(\); e\.stopPropagation\(\); this\.closeComposer\(\); \}/, 'cancel closes the composer');
  assert.match(panel, /if \(was && was\.kind === "reply" && held\) this\.focusAway\(was\);/, 'closeComposer hands a hidden reply\'s keyboard to focusAway');
  // the hidden-card case names the filter row, and focusAway takes the first button carrying that action
  assert.match(panel, /if \(this\.activeFilter\(\) === "changes" && card\.hunk === null\) return \{ gone: false, back: "fcfilter", /, 'replyAway: the filter hides the card');
  assert.match(panel, /const back = this\.replyAway\(was\)\.back;\n\s+const row = back \? root\.querySelector\('\[data-act="' \+ back \+ '"\]'\) as HTMLElement \| null : null;\n\s+if \(row\) row\.focus\(\{ preventScroll: true \}\);/, 'focusAway focuses the first control with that action');
  // …and the header offers All first, so that button is All
  const order = /\["all", "All", [^\]]+\],\s*\["comments", "Comments " \+ n\.comments, [^\]]+\],\s*\["changes", "Changes " \+ n\.changes, [^\]]+\],/.exec(panel);
  assert.ok(order, 'the header offers all, comments, changes in that order');
  assert.match(panel, /const FILTERS: CommentsFilter\[\] = \["all", "comments", "changes"\];/, 'the group\'s order starts at all');
});

test('the note\'s prose says "note" only of itself: CONTEXT.md lists the word under Avoid for a file comment, and the rule is named by its selector', () => {
  const entry = /^\*\*File comment\*\*:\n([\s\S]*?)(?=\n\n)/m.exec(context);
  assert.ok(entry, 'CONTEXT.md has the File comment entry');
  // the Avoid line wraps, so it is read to the entry's end (the blank line), parentheticals dropped
  const at = entry[1].indexOf('_Avoid_:');
  assert.ok(at >= 0, 'the entry has an Avoid line');
  const avoid = entry[1].slice(at + '_Avoid_:'.length).replace(/\([^)]*\)/g, '').split(',').map((w) => w.trim()).filter(Boolean);
  assert.ok(avoid.includes('note'), 'the premise: File comment avoids "note" (' + avoid.join(', ') + ')');
  for (const m of prose.matchAll(/\b(\w+)\s+note\b/g)) assert.equal(m[1], 'this', 'the note says "' + m[0] + '": "note" is the plan\'s word for its own build and follow-on notes, and nothing else here');
  assert.doesNotMatch(prose, /\bnote's\b/, 'no "the note\'s …" in the prose');
  // the two phrases the review named, replaced by what they meant
  assert.doesNotMatch(prose, /\bdress\b|hands the keyboard/, 'the styling and the focus move are stated, not figured');
});
