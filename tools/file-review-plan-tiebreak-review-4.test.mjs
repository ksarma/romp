// The recurring-passage tie-break, the record's account of the review's third and fourth rounds (2026-09-11;
// plans/file-review.md decision 51, the contract, the host paragraph, the painting paragraph, the anchors follow-on note
// and the Tests section). The third round changed the host's rules and the panel's words (the ordinal yields to a stored
// heading path that names other copies and not its own; a position the quote sits at names the passage; the reply's map
// drops a verdict the recorded changes carry elsewhere; creation writes no copy fields past the cap; front matter closes
// on --- alone; the words for the editor and for a view with no picture), and its commit recorded only the second round's
// items, so the plan stated a rule the code no longer took: the ordinal's copy confirmed whenever the count of copies was
// unchanged. The fourth round asked for one side of the quote's context beside it before a position names the passage,
// charged the walk over the recorded changes to the budget, and gave a phone's pictured region card words without the
// Re-place it lacks. This module holds the record's account of all that to the code: the plan's sentences to the host
// (locateStored's position rule and the yield, placedFor's recorded window, carriedTo's budgeted walk, buildComment's cap,
// the front-matter reader), to the panel (copyUnsureWords and its words) and to the tree (the rounds' modules), and
// drives the yield and the position rule on synthetic markdown, so the sentences stay true of the code and not only
// present in the plan. Synthetic: the repo's own text and an invented report, no session data.
// Run: node --test tools/file-review-plan-tiebreak-review-4.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { sectionAt, locateStored, fullMatches } from './file-comments-host.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');
const exists = (...parts) => fs.existsSync(path.join(REPO, ...parts));

const plan = read('plans', 'file-review.md');
const host = read('tools', 'file-comments-host.mjs');
const panel = read('ui', 'webview', 'file-comments.ts');

// The text between two headings, hard wraps collapsed so an assertion survives a rewrap.
function section(from, to) {
  const a = plan.indexOf(from);
  assert.ok(a >= 0, `heading ${JSON.stringify(from)} not found in the plan`);
  const b = plan.indexOf(to, a + from.length);
  assert.ok(b > a, `heading ${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return plan.slice(a, b).replace(/\s+/g, ' ');
}
const contract = section('## The contract: the track-changents sidecar', '## Kernel: two ops and a host script');
const op = section('## Kernel: two ops and a host script', '## UX');
const ux = section('### Commenting from either view, and in every format', '### The viewer seam');
const note = section('### Slice 2: the session', '### Slice 3: region comments on images');
const tests = section('## Tests', '## Docs');
const decisions = section('## Decisions (the user, 2026-09-05 and 2026-09-06)', '## Open questions for the user');
const decision51 = decisions.slice(decisions.indexOf('51. **'));
const open = plan.slice(plan.indexOf('## Open questions for the user')).replace(/\s+/g, ' ');

// A function's source, from its `function name(` to the first line that is a lone closing brace.
function fn(src, name) {
  const a = src.indexOf(`function ${name}(`);
  assert.ok(a >= 0, `${name} is defined`);
  const b = src.indexOf('\n}\n', a);
  assert.ok(b > a, `${name} closes`);
  return src.slice(a, b);
}
function inOrder(src, needles, what) {
  let from = 0;
  for (const n of needles) {
    const i = src.indexOf(n, from);
    assert.ok(i >= 0, `${what}: ${JSON.stringify(n)} follows the previous step`);
    from = i + n.length;
  }
}
// A string constant's value as the panel writes it: one literal, or a literal joined to a named tail.
function constant(src, name) {
  const m = src.match(new RegExp(`const ${name} = "((?:[^"\\\\]|\\\\.)*)"(?: \\+ ([A-Z_]+))?;`));
  assert.ok(m, `${name} is one string literal, or one joined to a named tail`);
  return m[2] ? m[1] + constant(src, m[2]) : m[1];
}

const ROUND_MODULES = ['tools/file-comments-host-tiebreak-review-3.test.mjs', 'ui/webview/file-comments-host-tiebreak-review-3-panel.test.ts', 'ui/webview/file-comments-tiebreak-shown.test.ts', 'ui/webview/file-comments-tiebreak-touch.test.ts', 'tools/file-review-plan-tiebreak-review-4.test.mjs'];

// ── the record ──────────────────────────────────────────────────────

test('decision 51 states the first rule with its yield, the position the quote names and the rounds\' account, and the open questions carry the user\'s word on the departure from the contract', () => {
  assert.ok(decision51.includes("host must choose among several copies and the position names none, not even by the quote with one side of its context whole beside it (`locateStored`, which every reader of a stored anchor in the host goes through, and the `placed` map every reply carries for the panel), the rules run in order: the count of copies unchanged since the fields were written, the ordinal's copy, confirmed, unless the stored heading path names other copies and not the ordinal's, when the two fields disagree and the tie is a guess (the review's third round, 2026-09-11, said below); else, the count changed, exactly one copy under the stored heading path, that copy, confirmed; else the copy nearest the position, a guess, as before."));
  assert.ok(!decision51.includes("the ordinal's copy, confirmed; else exactly one copy under the stored heading path"), 'the unconditional first rule, false of the code since the third round, is gone');
  assert.ok(decision51.includes("The review's third round (2026-09-11) qualified the first rule, the position's, and the reply's map."));
  assert.ok(decision51.includes("where it names other copies and not the ordinal's, the two fields disagree, neither confirms, and the tie is a guess: an unchanged count does not say that no copy was added or removed"));
  assert.ok(decision51.includes("so a tie the two fields read two ways is left to the person, and the section rule runs once the count has changed."));
  assert.ok(decision51.includes("The contract the user said yes to confirmed the ordinal's copy whenever the count was unchanged, with no such condition; the code and this record hold the qualified rule, and the user's word on it is open (Open questions)."));
  assert.ok(decision51.includes("A position the quote sits at with ONE side of its context whole beside it, the other side edited (the state the refresh leaves when a recorded change edited the chosen copy's context and not its text, and the state a raw edit of the surroundings alone leaves), names the passage before any rule runs (`quoteSitsAt`), the copies whole elsewhere being the other copies"));
  assert.ok(decision51.includes("The third round took the quote alone; the review's fourth round (2026-09-11) asks for the one side, since a bare occurrence of the quoted words (a passing mention, a table cell, one character of a run) is what a stale position lands on by a coincidence of distance"));
  assert.ok(decision51.includes("The reply carries no verdict for such a comment, and the panel paints by its own engine, which scores a whole copy over an edited one: with three or more copies the nearest whole copy as a guess with its cue, the cue from before the tie-break; with exactly two, the one still whole, plainly, the paint of the anchors follow-on, on the copy the person did not comment, since the map's contract (a tie the position names no copy of) does not carry a position verdict today"));
  assert.ok(decision51.includes("the reply's map forwards a tie's verdict only where the recorded changes carry the stored position to that very copy (a tracked insertion above moved every copy alike) or to no one place, and drops one they carry elsewhere (`placedFor`, `carriedTo`)"));
  assert.ok(decision51.includes('After a raw write the changes vouch for nothing and every verdict is forwarded, as before.'));
  assert.ok(decision51.includes("The walk over the copies the recorded changes can have carried a position to (`reachable`, for the refresh and for `carriedTo`) reads the changes off one sorted index, a compare per change to build it and a compare per copy inside the changes' window, charged to the budget; a walk that does not fit is nothing known, the refresh keeping the position and counting the comment among the unscanned, the map forwarding the verdict"));
  assert.ok(decision51.includes('creation writes no copy fields for a passage whole at more places than the refresh enumerates (`REFRESH_COPIES_MAX`), as the stamping pass already refused to'));
  assert.ok(decision51.includes('the front-matter reader closes a block on `---` alone, as the viewer\'s test does (a block closed only by YAML\'s `...` is body, and a heading in it is the passage\'s path'));
  assert.ok(decision51.includes('(`copiesUnder`, `nearestOf`)'));
  assert.ok(decision51.includes('leave edit mode, then reveal it and save again from the right copy (`UNSURE_IN_EDITOR`, `PASSAGE_CONFIRM_AFTER_EDIT`; a region\'s, leave edit mode, then draw a new region in the view that shows the image, `REGION_CONFIRM_AFTER_EDIT`), a passage\'s save line standing under them as in the read view, and offer no Reveal'));
  assert.ok(decision51.includes('a region whose picture the view does not show (Raw) is told which view has it (`REGION_CONFIRM_UNSEEN`)'));
  assert.ok(decision51.includes('ends with the pictured view\'s words less the sentence about Re-place (`REGION_CONFIRM_TOUCH`; the sweep after the round, the same day)'));
  assert.ok(open.includes("The tie-break's first rule as the review's third round qualified it (decision 51: the ordinal's copy is confirmed unless the stored heading path names other copies and not the ordinal's, when the tie is a guess) departs from the contract the user said yes to, which confirmed the ordinal's copy whenever the count of copies was unchanged; it awaits the user's word, and the code and the record hold the qualified rule meanwhile."));
});

test('the contract, the host paragraph, the painting paragraph and the note state the same rules, and the unconditional wording is gone from each', () => {
  assert.ok(contract.includes("the ordinal's copy while the count of copies is unchanged, unless the stored heading path names other copies and not the ordinal's, when the two fields disagree and the tie is a guess (the same round; decision 51 says why); else, the count changed, the one copy under the stored heading path; confirmed either way; else the nearest copy to the position, a guess."));
  assert.ok(contract.includes('Every reply carries the verdicts (`placed`, per comment id), except that while every change to the text is on record a verdict the recorded changes carry to another place is left to the next write\'s refresh (the same round), and the panel paints a confirmed copy plainly.'));
  assert.ok(contract.includes('at creation (none for a passage whole at more places than the refresh enumerates, where no count is known; the review\'s third round, 2026-09-11)'));
  assert.ok(contract.includes("not even by the quote with one side of its context whole beside it (such a position, the other side edited, names the passage, and the copies whole elsewhere are the other copies; the same round, and the review's fourth, which asks for the one side: a bare occurrence of the quoted words is a stale position like any other)"));
  assert.ok(!contract.includes('else the one copy under the stored heading path, confirmed either way'), 'the contract no longer confirms the ordinal against a disagreeing heading path');
  assert.ok(op.includes('the position first, where the whole anchor still sits at it, and where the quote sits at it with one side of its context whole beside it while the whole anchor sits elsewhere (`quoteSitsAt`: the passage whose surroundings on the other side were edited'));
  assert.ok(op.includes('so the panel paints by its own engine, the nearest whole copy as a guess with its cue, or, with exactly two copies, the one still whole, plainly, as since the anchors follow-on; the review\'s third round, 2026-09-11, which took the quote alone, and its fourth, which asks for the one side'));
  assert.ok(op.includes('`ordinal` while `copies` equals the count of matches now, unless the stored `section` names other matches and not the ordinal\'s, when the two fields disagree and neither confirms (the same round); else, the count changed, the one match under the stored `section`; both confirmed; else the match nearest the position, a guess, and a tie with no position refuses `anchor-ambiguous` as before; an anchor whole nowhere is the engine\'s.'));
  assert.ok(op.includes('The reply\'s map (`placedFor`) carries the verdict of every such tie, except that while every change to the text is on record (the text as the sidecar\'s last writer left it) a verdict the recorded changes carry to another copy, or to the quote\'s own occurrence, is dropped for the next write\'s refresh to settle (`carriedTo`;'));
  assert.ok(op.includes("the walk over the copies the recorded changes can have carried a position to (`reachable`, the refresh's and the map's) reads the changes off one sorted index and is charged to the same budget, and a comment whose walk does not fit is one the changes say nothing about, its position kept and counted by the refresh, its verdict forwarded by the map"));
  assert.ok(op.includes('Creation stamps them alone where the whole anchor is at no more places than the refresh enumerates (`REFRESH_COPIES_MAX`): past that no count is known and none is written, as the stamping pass already refused to'));
  assert.ok(!op.includes('the count of matches now, else the one match under the stored `section`, both confirmed'), 'the host paragraph no longer states the first cut\'s order');
  assert.ok(ux.includes("a copy the host confirmed from the fields stored with the comment (the ordinal's copy while the count of copies is unchanged, unless the stored heading path names other copies and not that one; else, the count changed, the one copy under the stored heading path; decision 51 has the rules) is the painter's hint in place of the stale position (`placedAt`)"));
  assert.ok(ux.includes('a guessed verdict, or none (a tie whose verdict the recorded changes carry elsewhere has none until the next write settles it, and a position the quote sits at with one side of its context whole beside it has none, the panel painting that comment by its own engine as before the tie-break; the review\'s third round, 2026-09-11, and its fourth), paints as before'));
  assert.ok(ux.includes('Those are the words of a view that paints the copy: with the editor up (Slice 5) no highlight of ours is painted and the card offers neither Reveal nor the composer, so a guessed card\'s words say only that the copy is a guess and name the way there first, leave edit mode, then reveal it and save again from the right copy (`UNSURE_IN_EDITOR`, `PASSAGE_CONFIRM_AFTER_EDIT`;'));
  assert.ok(ux.includes('a region whose picture the view does not show (Raw) is told which view has it (`REGION_CONFIRM_UNSEEN`); and a pictured region\'s card on a coarse pointer, which offers no Re-place, ends with the pictured view\'s words less the sentence about Re-place (`REGION_CONFIRM_TOUCH`).'));
  assert.ok(!ux.includes('(the ordinal while the count of copies is unchanged, else the one copy under the stored heading path)'), 'the painting paragraph no longer abbreviates the rules to the first cut\'s');
  assert.ok(note.includes("the ordinal's copy while the count of copies is unchanged, confirmed, unless the stored heading path names other copies and not the ordinal's, when the two fields disagree and the tie is a guess (the review's third round, 2026-09-11); else, the count changed, the one copy under the stored heading path, confirmed; else the nearest, a guess, whose words on the card end with \"Reveal it and save again from the right copy to confirm.\" and whose card offers that Reveal (the review's first round, 2026-09-11)."));
  assert.ok(note.includes("Both are the read view's card: with the editor up the words say only that the copy is a guess and name the way there first, leave edit mode, then reveal it and save again from the right copy (a region's: then draw a new region in the view that shows the image), and the card offers no Reveal; in Raw a region's words name the view that shows its picture, and on a coarse pointer they leave out the sentence about the Re-place the card lacks (the review's third round, 2026-09-11, and the sweep after it)."));
  assert.ok(note.includes("A position the quote sits at with one side of its context whole beside it, the other side edited, names the passage before any rule runs, and the copies whole elsewhere are the other copies, never placed on (the same round, whose test took the quote alone, and the review's fourth, which asks for the one side;"));
  assert.ok(!note.includes('copy while the count of copies is unchanged, else the one copy under the stored heading path, confirmed;'), 'the note no longer states the unconditional rule');
});

// ── the host ────────────────────────────────────────────────────────

test('locateStored takes the rules as the record states them: the quote with one side of its context at the position before any rule, the ordinal confirmed unless the stored heading path names other copies and not its own, the section rule once the count changed, the nearest off the enumerated copies', () => {
  const locate = fn(host, 'locateStored');
  inOrder(locate, [
    "if (at !== undefined && sitsAt(text, anchor, at)) return span(at, true, 'position');",
    'const { hits, more, cut } = fullMatches(text, anchor, REFRESH_COPIES_MAX, budget);',
    "if (at !== undefined && quoteSitsAt(text, anchor, at)) return span(at, true, 'position');",
    "if (hits.length === 1 && !more) return span(hits[0], true, 'whole');",
    'const o = ordinalOf(c);',
    'const s = sectionOf(c);',
    'const under = s !== null && markdown ? copiesUnder(text, anchor, hits, markdown, s, budget) : [];',
    'if (o && o.copies === hits.length) {',
    'const pick = hits[o.ordinal - 1];',
    "if (!under.length || sectionAt(text, pick, markdown) === s) return span(pick, true, 'ordinal');",
    '} else if (under.length === 1) {',
    "return span(under[0], true, 'section');",
    "if (at === undefined) return { error: 'anchor-ambiguous' };",
    "if (!more) return span(nearestOf(hits, at), false, 'nearest');",
  ], 'locateStored');
  const sits = fn(host, 'quoteSitsAt');
  inOrder(sits, [
    'if (!Number.isInteger(at) || at < 0 || at > text.length || !text.startsWith(anchor.quote, at)) return false;',
    'return (prefix.length > 0 && at >= prefix.length && text.startsWith(prefix, at - prefix.length))',
    '|| (suffix.length > 0 && text.startsWith(suffix, at + anchor.quote.length));',
  ], 'quoteSitsAt');
  // behaviour, on synthetic markdown: one paragraph three times, each under its own heading
  const Q = 'The passage recurs here.';
  const sec = (h) => `## ${h}\n\nLorem ipsum body.\n\n${Q}\n\n`;
  const anchor = { quote: Q, prefix: 'body.\n\n', suffix: '\n\n' };
  const hitsOf = (t) => fullMatches(t, anchor, 100).hits;
  const span = (from, confirmed, by) => ({ from, to: from + Q.length, confirmed, by });
  const TIED = '# Report\n\n' + sec('First pass') + sec('Second pass') + sec('Third pass');
  const H = hitsOf(TIED);
  assert.deepEqual(H.map((h) => sectionAt(TIED, h, true)), ['Report > First pass', 'Report > Second pass', 'Report > Third pass'], 'the fixture: three copies, one under each heading');
  const stored = { anchor, anchorAt: H[1], ordinal: 2, copies: 3, section: 'Report > Second pass' };
  assert.deepEqual(locateStored(TIED, stored, true), span(H[1], true, 'position'), 'the text as saved: the position names the copy');
  // one copy deleted and another pasted under a new heading: the count stays 3 and the ordinal's copy is under Third pass
  const SWAPPED = '# Report\n\nA short line.\n\n' + sec('Second pass') + sec('Third pass') + sec('Fourth pass');
  const HS = hitsOf(SWAPPED);
  assert.deepEqual(HS.map((h) => sectionAt(SWAPPED, h, true)), ['Report > Second pass', 'Report > Third pass', 'Report > Fourth pass']);
  assert.equal(sectionAt(SWAPPED, HS[1], true), 'Report > Third pass', 'the fixture: the ordinal\'s copy is under another heading than the stored path');
  assert.deepEqual(locateStored(SWAPPED, stored, true), span(HS[1], false, 'nearest'), 'the count unchanged but the stored path names another copy and not the ordinal\'s: a guess, not the ordinal\'s copy and not the one copy under the stored path');
  assert.deepEqual(locateStored(SWAPPED, { ...stored, section: 'Report > Old name' }, true), span(HS[1], true, 'ordinal'), 'the stored path names no copy (a heading renamed): the ordinal\'s copy, confirmed');
  assert.deepEqual(locateStored(SWAPPED, stored, false), span(HS[1], true, 'ordinal'), 'a non-markdown file, every path empty: the ordinal\'s copy, confirmed');
  assert.deepEqual(locateStored(SWAPPED, { anchor, ordinal: 2, copies: 3, section: 'Report > Second pass' }, true), { error: 'anchor-ambiguous' }, 'the fields disagree and there is no position: refused, as a hintless tie always was');
  // the stored path names the ordinal's copy among others: the ordinal stands
  const TWO_UNDER = '# Report\n\n' + sec('Second pass') + `Lorem ipsum body.\n\n${Q}\n\n` + sec('Third pass');
  const HT = hitsOf(TWO_UNDER);
  assert.deepEqual(HT.map((h) => sectionAt(TWO_UNDER, h, true)), ['Report > Second pass', 'Report > Second pass', 'Report > Third pass']);
  assert.deepEqual(locateStored(TWO_UNDER, { ...stored, anchorAt: 1 }, true), span(HT[1], true, 'ordinal'), 'the stored path names the ordinal\'s copy, among others: confirmed by ordinal');
  // the count changed: the section rule
  const DELETED = '# Report\n\n' + sec('Second pass') + sec('Third pass');
  const HD = hitsOf(DELETED);
  assert.deepEqual(locateStored(DELETED, { ...stored, anchorAt: 1 }, true), span(HD[0], true, 'section'), 'the count changed and one copy under the stored path: that copy, confirmed');
  assert.deepEqual(locateStored(DELETED, { anchor, ordinal: 2, copies: 3, section: 'Report > Second pass' }, true), span(HD[0], true, 'section'), 'the same with no position: the fields answer before the refusal');
  const TWICE = '# Report\n\n' + sec('Second pass') + `Lorem ipsum body.\n\n${Q}\n\n` + sec('Fourth pass') + sec('Fifth pass');
  assert.deepEqual(locateStored(TWICE, { ...stored, anchorAt: 1 }, true), span(hitsOf(TWICE)[0], false, 'nearest'), 'the count changed and two copies under the stored path: the nearest, a guess');
  // the quote at the position with one side of its context: the prefix of the chosen copy edited raw, the suffix whole
  const EDITED = TIED.slice(0, H[1] - 7) + 'text.\n\n' + TIED.slice(H[1]);
  assert.equal(hitsOf(EDITED).length, 2, 'the fixture: the whole anchor now sits at the other two copies');
  assert.ok(EDITED.startsWith(Q, H[1]) && EDITED.startsWith('\n\n', H[1] + Q.length), 'the fixture: the quote and its suffix still sit at the stored position');
  assert.deepEqual(locateStored(EDITED, stored, true), span(H[1], true, 'position'), 'the quote with one side of its context at the position names the passage; the copies whole elsewhere are the other copies, and neither rule places the comment on one');
  // a bare occurrence of the quoted words at the position, neither side beside it: a stale position, and the rules run
  const MENTION = '# Report\n\n' + sec('First pass') + `## Second pass\n\nSee: ${Q} as noted.\n\n` + sec('Third pass');
  const bareAt = MENTION.indexOf('See: ') + 5;
  assert.ok(MENTION.startsWith(Q, bareAt) && !MENTION.startsWith('body.\n\n', bareAt - 7) && !MENTION.startsWith('\n\n', bareAt + Q.length), 'the fixture: the quoted words alone at the position');
  const HM = hitsOf(MENTION);
  assert.equal(HM.length, 2);
  const bare = locateStored(MENTION, { ...stored, anchorAt: bareAt }, true);
  assert.deepEqual(bare, span(bareAt < (HM[0] + HM[1]) / 2 ? HM[0] : HM[1], false, 'nearest'), 'the count changed and no copy under the stored path: the nearest whole copy, a guess, not the mention (the fourth round)');
});

test('the reply\'s map drops a verdict the recorded changes carry elsewhere while every change is on record, through a walk charged to the budget; creation writes no copy fields past the cap; the front-matter reader closes on --- alone', () => {
  const placed = fn(host, 'placedFor');
  inOrder(placed, [
    'const recorded = store[TEXT_AS_WRITTEN] === true;',
    'const loc = locateStored(text, c, markdown, refreshBudget);',
    "if (!loc || loc.error || loc.by === 'position' || loc.by === 'whole' || loc.by === 'engine') continue;",
    'if (recorded) {',
    'const carried = carriedTo(text, c, bounds, refreshBudget);',
    'if (carried !== null && carried !== loc.from) continue;',
    'out[String(c.id)] = { at: loc.from, confirmed: loc.confirmed, by: loc.by };',
  ], 'placedFor');
  const carried = fn(host, 'carriedTo');
  inOrder(carried, [
    'if (at === undefined) return null;',
    'const whole = movedCopy(hits, at, bounds, undefined, budget);',
    'if (whole === undefined) return null;',
    'if (whole !== null) return whole;',
    'const moved = movedCopy(hits, at, bounds, q.positions, budget);',
    'return moved === undefined ? null : moved;',
  ], 'carriedTo');
  const reach = fn(host, 'reachable');
  assert.ok(reach.includes('const ix = boundsIndex(bounds, budget);') && reach.includes('if (budget) {') && reach.includes('budget.left -= to - from;'), 'the walk reads the changes off one index and is charged to the budget');
  const refresh = fn(host, 'refreshAnchorAts');
  assert.ok(refresh.includes('if (whole === undefined) { budget.unscanned++; continue; }') && refresh.includes('if (moved === undefined) { budget.unscanned++; continue; }'), 'a walk that does not fit leaves the refresh\'s position where it is, counted among the unscanned');
  const build = fn(host, 'buildComment');
  assert.ok(build.includes('const counted = stored.unique || !fullMatches(text, stored.anchor, REFRESH_COPIES_MAX).more;'), 'a count is known only when the whole-copy scan was not cut at the cap');
  assert.ok(build.includes('if (counted) stampCopy(copy, text, loc.from, stored.unique ? [loc.from] : fullMatches(text, stored.anchor, REFRESH_COPIES_MAX).hits, !!(opts && opts.markdown));'), 'and the fields are written only then');
  const front = fn(host, 'frontMatterLines');
  assert.ok(front.includes('if (/^---[ \\t]*$/.test(lines[i])) { close = i; break; }'), 'a block closes on a --- line');
  assert.ok(!front.includes('\\.\\.\\.') && !front.includes("'...'"), 'and never on YAML\'s document-end marker, which closes none in the viewer');
  // behaviour: a block closed only by ... is body, and the heading in it is the passage's path; a block closed by --- is skipped
  const DOTS = '---\ntitle: Notes\n...\n\n## Inside\n\nBody line.\n';
  assert.equal(sectionAt(DOTS, DOTS.indexOf('Body line.'), true), 'Inside');
  const DASHES = '---\ntitle: Notes\n---\n\n## After\n\nBody line.\n';
  assert.equal(sectionAt(DASHES, DASHES.indexOf('Body line.'), true), 'After');
});

// ── the panel ───────────────────────────────────────────────────────

test('the panel words the recourse for what the render shows: the editor names the way there and offers no Reveal, a view with no picture names the view that has it, a coarse pointer leaves out the Re-place the card lacks', () => {
  const words = fn(panel, 'copyUnsureWords');
  inOrder(words, [
    'if (c.shown.editing) return UNSURE_IN_EDITOR + (c.target ? REGION_CONFIRM_AFTER_EDIT : PASSAGE_CONFIRM_AFTER_EDIT);',
    'if (c.target && !c.shown.pictured) return state + ", not a confirmed one. " + REGION_CONFIRM_UNSEEN;',
    'if (c.target && !c.shown.draws) return state + ", not a confirmed one. " + REGION_CONFIRM_TOUCH;',
    'if (c.target) return state + ", not a confirmed one. " + REGION_CONFIRM;',
    'return state + ", not a confirmed one. Reveal it and save again from the right copy to confirm.";',
  ], 'copyUnsureWords');
  const inEditor = constant(panel, 'UNSURE_IN_EDITOR');
  assert.ok(inEditor.endsWith('the copy this comment is on can only be guessed. '), 'the editor states the guess and names no paint');
  assert.ok(!/highlight|position|place where/.test(inEditor), 'no hint is named: the editor shows no highlight of ours');
  assert.equal(constant(panel, 'PASSAGE_CONFIRM_AFTER_EDIT'), 'To confirm the copy, leave edit mode, then reveal it and save again from the right copy.');
  const regionAfterEdit = constant(panel, 'REGION_CONFIRM_AFTER_EDIT');
  assert.ok(regionAfterEdit.startsWith('To confirm the copy, leave edit mode, then draw a new region on the figure you mean in the view that shows the image'), 'a region\'s: leave edit mode, then draw in the view that shows the image');
  const unseen = constant(panel, 'REGION_CONFIRM_UNSEEN');
  assert.ok(unseen.startsWith('To confirm the copy, draw a new region on the figure you mean in the view that shows the image'), 'a view with no picture names the view that has it');
  assert.ok(!/\bRe-place\b/.test(unseen) && !/\bRe-place\b/.test(regionAfterEdit), 'neither names the Re-place those cards lack');
  const touch = constant(panel, 'REGION_CONFIRM_TOUCH');
  const pictured = constant(panel, 'REGION_CONFIRM');
  assert.ok(!/\bRe-place\b/.test(touch), 'a coarse pointer\'s words name no Re-place');
  assert.ok(pictured.includes('Re-place redraws the rectangle on the figure shown and does not move the comment to another figure. '), 'the pictured view\'s words, on a pointer that draws, say what Re-place does');
  assert.equal(touch, pictured.replace('Re-place redraws the rectangle on the figure shown and does not move the comment to another figure. ', ''), 'the coarse pointer\'s words are the pictured view\'s less that sentence, and nothing else changed');
  // the render stamps the editor, the picture and the pointer on the card its words read, and offers Reveal outside the editor alone
  assert.ok(panel.includes('const c: WordedCard = { ...given, shown: { editing, pictured: !!picture, draws: this.drawsRegions() } };'), 'what this render shows rides on the card');
  const reveal = panel.indexOf('const rv = btn("Reveal", "fcreveal"); rv.dataset.id = c.id;');
  assert.ok(reveal >= 0, 'a comment card\'s Reveal');
  const gate = panel.lastIndexOf('if (!editing) {', reveal);
  assert.ok(gate >= 0 && reveal - gate < 400, 'offered only outside the editor');
  assert.ok(panel.includes('if (this.unsureCopies.has(c.id) && !c.target) card.appendChild(el("div", "fc-note", SAVE_FROM_COPY_NOTE));'), 'a passage\'s save line stands under the words in either state, a line that names no control');
});

// ── the tree ────────────────────────────────────────────────────────

test('the rounds\' modules exist, and the note, the Tests section and decision 51 name them; the Tests section says what each drives; no em dash in the new sentences', () => {
  for (const m of ROUND_MODULES) {
    assert.ok(exists(...m.split('/')), `${m} exists`);
    assert.ok(note.includes('`' + m + '`'), `the note names ${m}`);
    assert.ok(tests.includes('`' + m + '`'), `the Tests section names ${m}`);
    assert.ok(decision51.includes('`' + m + '`'), `decision 51 names ${m}`);
  }
  assert.ok(tests.includes("From that third round (2026-09-11), `tools/file-comments-host-tiebreak-review-3.test.mjs` drives the real host as a child process, or its exported readers, over the round's findings on the host: a comment the refresh carried to the quote's own occurrence, one side of its context still beside it, answers the position and the reply carries no verdict for it (`locateStored`, `quoteSitsAt`, `placedFor`)"));
  assert.ok(tests.includes('the ordinal yields to a stored heading path that names other copies and not its own, while a heading renamed or deleted above the copies leaves it confirmed; creation writes no copy fields for a passage whole at more places than `REFRESH_COPIES_MAX`, and a later write adds none; a front-matter block closes on `---` alone'));
  assert.ok(tests.includes("`ui/webview/file-comments-host-tiebreak-review-3-panel.test.ts` drives the panel's half of that state, over the tie-break stand-in and over the real host's reply: with no entry the panel paints the nearest whole copy in the dashed cue with the stored position's words and nothing at the quote"));
  assert.ok(tests.includes('`ui/webview/file-comments-tiebreak-shown.test.ts` drives the words for what the render shows, over the recourse module\'s stand-in with a viewer that flips into edit mode as `enterEdit` does: with the editor up a guessed passage card names the way there (leave edit mode, then reveal it and save again) and offers no Reveal'));
  assert.ok(tests.includes('`ui/webview/file-comments-tiebreak-touch.test.ts` drives the same region on a coarse pointer with the picture in view: the words leave out the sentence about the Re-place the card lacks and end with what drawing takes'));
  assert.ok(tests.includes("`tools/file-review-plan-tiebreak-review-4.test.mjs` holds the record's account of the third round (decision 51, the contract, the host and painting paragraphs, the note) to the host"));
  assert.ok(tests.includes("The third round wrote it for the second's account; its own account is held below."), 'the review-3 pin\'s place in the rounds is said');
  for (const [name, text] of [['decision 51', decision51], ['the contract\'s tie-break sentences', contract.slice(contract.indexOf('Three more romp-only fields'), contract.indexOf('A file created through'))], ['the host paragraph\'s tie-break sentences', op.slice(op.indexOf('goes through `locateStored`'), op.indexOf('Reject writes the sidecar first'))], ['the painting paragraph\'s tie-break sentences', ux.slice(ux.indexOf('Since the tie-break (2026-09-11'), ux.indexOf('The stored position is an offset'))], ['the note\'s tie-break sentences', note.slice(note.indexOf('The tie-break (2026-09-11, decision 51) closes'), note.indexOf('The todo-file follow-on'))], ['the open question', open.slice(0, open.indexOf('The margin layout'))]]) {
    assert.ok(text.length > 0, `${name} found`);
    assert.ok(!text.includes('\u2014'), `${name} has no em dash`);
  }
});
