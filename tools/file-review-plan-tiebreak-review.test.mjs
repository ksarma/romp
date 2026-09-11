// The tie-break's review (2026-09-11) found the plan behind the slice wrong in two places. The host paragraph and the
// anchors follow-on note still said a passage still at its position costs the refresh no scan, a sentence from before
// the tie-break: since it, the refresh stamps `ordinal`, `copies` and `section` on every comment whose position names
// its copy, and the stamp needs the count of the whole anchor's matches, so such a comment costs one classification
// pass per distinct anchor on every write (a fresh process each), charged to the same budget; past it the comment keeps
// the fields it has, or none, and stderr says how many were left, once per write (noteUnstamped, the review's own fix:
// before it the skip was silent). The paragraph's own stamping sentence conceded the cost two sentences on. And
// decision 51 said a tie with no position still refuses, unconditionally, where locateStored runs the ordinal rule and
// the section rule before the hintless refusal, so a comment whose position an editor dropped is confirmed from its
// fields and only a comment with neither position nor field is refused. The plan now says both; this module holds each
// corrected sentence to the source that makes it true: fullMatches's charge and memo, the stamping pass of
// refreshAnchorAts and the note told after it, and locateStored on a tied text. The review's second round found this
// module's first cut pinning the plan's word that the skip past the budget leaves no note, a sentence the first round's
// fix had made false, with a source pin over the stamping loop alone, which ends before the note is told; the pin now
// reads the note's source and the plan says what stderr says. Synthetic: the repo's own text and an invented report,
// no session data.
// Run: node --test tools/file-review-plan-tiebreak-review.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { fullMatches, locateStored, sectionAt, REFRESH_PASS_DIVISOR } from './file-comments-host.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');

const plan = read('plans', 'file-review.md');
const host = read('tools', 'file-comments-host.mjs');

// The text between two headings, hard wraps collapsed so an assertion survives a rewrap.
function section(from, to) {
  const a = plan.indexOf(from);
  assert.ok(a >= 0, `heading ${JSON.stringify(from)} not found in the plan`);
  const b = plan.indexOf(to, a + from.length);
  assert.ok(b > a, `heading ${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return plan.slice(a, b).replace(/\s+/g, ' ');
}
const op = section('## Kernel: two ops and a host script', '## UX');
const note = section('### Slice 2: the session', '### Slice 3: region comments on images');
const tests = section('## Tests', '## Docs');
const decisions = section('## Decisions (the user, 2026-09-05 and 2026-09-06)', '## Open questions for the user');
const decision51 = decisions.slice(decisions.indexOf('51. **'));

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

// ── the fixture: one paragraph three times, each under its own heading ──
const PARA = 'Alpha beta gamma. Here is the marker phrase to comment on. Delta epsilon zeta.';
const TEXT = `# Report\n\nAn opening line that occurs once.\n\n## First pass\n\n${PARA}\n\n## Second pass\n\n${PARA}\n\n## Third pass\n\n${PARA}\n`;
const ANCHOR = { quote: 'the marker phrase', prefix: 'Here is ', suffix: ' to comment on.' };
const COPIES = [];
for (let i = TEXT.indexOf(ANCHOR.quote); i !== -1; i = TEXT.indexOf(ANCHOR.quote, i + 1)) COPIES.push(i);
assert.equal(COPIES.length, 3, 'the fixture: three copies');
const span = (from, confirmed, by) => ({ from, to: from + ANCHOR.quote.length, confirmed, by });

// ── the cost of a passage still at its position ─────────────────────

test('the host paragraph and the note say a passage still at its position costs its copy fields one classification pass per distinct anchor on every write, charged to the budget, and past it keeps the fields it has while stderr says how many, once per write; the old sentences are gone', () => {
  assert.ok(op.includes('is charged at its own cost to one budget per write (`REFRESH_SCAN_BUDGET`); a passage still at its position costs no scan to place, only the one classification pass per distinct anchor that stamping its copy fields takes on every write since the tie-break (below; before it such a passage cost nothing), and past the budget the remaining comments keep their position and stderr says how many, once per write, and a comment whose stamp the budget refuses keeps the fields it has, or none, and stderr says how many of those, once per write; and a stored comment\'s anchor is located with its `anchorAt` as the hint.'));
  assert.ok(!op.includes('a passage still at its position costs no scan,'), 'the host paragraph no longer says the passage costs no scan at all');
  assert.ok(!op.includes('with no note'), 'and no longer says a refused stamp leaves no note: the host tells how many, once per write (noteUnstamped, the review\'s fix), and the record said the silence the fix ended');
  assert.ok(note.includes("every scan (the whole-anchor classification, the quote count, the engine's) is charged to that one budget per write, and a passage still at its position costs none to place, one classification pass per distinct anchor for its copy fields on every write since the tie-break (below)."));
  assert.ok(!note.includes('costs none. '), 'the note no longer stops at costs none');
  // the paragraph's stamping sentence, which the corrected sentence agrees with
  assert.ok(op.includes('The refresh stamps the three fields on every comment whose position names its copy once its pass is done (`stampCopy`), under the same budget'));
});

test('the stamping pass of refreshAnchorAts scans every seated comment through the budget, tells nothing per comment, and once done counts the stamps the budget refused and tells stderr how many, once per write; fullMatches charges one pass per distinct anchor and text and none for a repeat', () => {
  const refresh = fn(host, 'refreshAnchorAts');
  // the placing pass seats a comment still at its position without a scan...
  assert.ok(refresh.includes('if (at !== undefined && sitsAt(text, c.anchor, at)) { seated.push(c); continue; }'), 'seated without a scan to place');
  // ...and the stamping pass then scans it, one classification per anchor, charged to the same budget
  const a = refresh.indexOf('for (const c of seated) {');
  assert.ok(a >= 0, 'the stamping pass walks the seated comments');
  const loop = refresh.slice(a, refresh.indexOf('\n  }\n', a));
  inOrder(loop, [
    "if (c[ENGINE_PLACED]) { delete c[ENGINE_PLACED]; stampCopy(c, text, at, [at], markdown); continue; }",
    'if (!affordableScan(budget, text, c.anchor)) continue;',
    'const { hits, more, cut } = fullMatches(text, c.anchor, REFRESH_COPIES_MAX, budget);',
    'if (cut || more) continue;',
    'stampCopy(c, text, at, hits, markdown);',
  ], 'the stamping pass');
  assert.ok(!loop.includes('process.stderr'), 'the loop tells nothing per comment: the count is told once, after it');
  assert.ok(!loop.includes('budget.unscanned') && !loop.includes('budget.skipped'), 'and it is not counted among the positions kept');
  // ...and once the loop is done, the stamps the budget refused are counted and told, once per write. The review's fix:
  // the first cut skipped them silently, and this module's first cut pinned the plan saying so with the slice above,
  // which ends at the loop's closing brace, before the note; the pin reads past it now.
  const afterLoop = refresh.slice(a + loop.length);
  inOrder(afterLoop, [
    'budget.unstamped = seated.filter((c) => stampRefused(text, c.anchor)).length;',
    'noteUnstamped(budget);',
  ], 'after the stamping pass');
  assert.ok(refresh.includes('budget.unstamped = 0;'), 'the count is reset per pass, as the position counts are');
  const noted = fn(host, 'noteUnstamped');
  inOrder(noted, [
    'if (budget.unstamped === budget.keptUnstamped) return;',
    'budget.keptUnstamped = budget.unstamped;',
    'if (budget.unstamped) {',
    "process.stderr.write(`file-comments-host: ${budget.unstamped} comment(s) kept the copy fields they had, or none: counting the copies of their passage would scan past the refresh's budget for one write\\n`);",
  ], 'noteUnstamped: told when the count changes, so once per write (the measure\'s pass and the stage\'s pass share the budget and the memos)');
  assert.ok(host.includes('refreshBudget.keptUnstamped = 0;'), 'what stderr was last told starts at none, so the first refusal of a write is told');
  // the host suite drives the note from the real host (a near-cap file with more seated anchors than one write's budget
  // scans) and reads it off stderr by this sentence, so the two suites cannot drift apart on what the host says
  const hostSuite = read('tools', 'file-comments-host-tiebreak-review.test.mjs');
  assert.ok(hostSuite.includes("comment\\(s\\) kept the copy fields they had, or none: counting the copies of their passage would scan past the refresh's budget for one write/g"), 'the host suite reads the same sentence');
  assert.ok(hostSuite.includes('unstampedNotes(res.stderr), [left.length]'), 'and asserts it is written when the budget refuses a stamp');
  // fullMatches: the pass is charged once per distinct anchor and text; a repeat is the memo's
  const budget = { left: 48_000_000 };
  const first = fullMatches(TEXT, ANCHOR, 64, budget);
  assert.deepEqual(first.hits, COPIES, 'the three copies');
  const afterFirst = budget.left;
  assert.ok(afterFirst < 48_000_000, 'the first classification of an anchor is charged');
  fullMatches(TEXT, ANCHOR, 64, budget);
  assert.equal(budget.left, afterFirst, 'the same anchor on the same text costs nothing more (comments on the copies of one passage share the pass)');
  const other = { quote: 'opening line that occurs once', prefix: 'An ', suffix: '.' };
  fullMatches(TEXT, other, 64, budget);
  assert.ok(budget.left < afterFirst, 'a distinct anchor is charged its own pass');
  const pass = 48_000_000 - afterFirst;
  assert.ok(pass >= Math.floor(TEXT.length / REFRESH_PASS_DIVISOR), 'the charge is at least the native pass over the text');
});

// ── a tie with no position ──────────────────────────────────────────

test('decision 51 says a tie with no position refuses only when neither field tells, and names this module beside the tie-break\'s; the Tests section says what this module holds', () => {
  assert.ok(decision51.includes('a tie with no position still refuses `anchor-ambiguous` when neither field tells (the fields settle it as for any other comment, so one whose position an editor dropped is confirmed from its ordinal or its heading path, and a comment the CLI made, which carries neither until the next host write stamps it, is refused as before), and the other editors write the object back whole, so the fields survive them (docs/adr/0002: six additive fields now).'));
  assert.ok(!decision51.includes('still refuses, and'), 'the unconditional clause is gone');
  assert.ok(decision51.includes('`tools/file-review-plan-tiebreak-review.test.mjs` (the review\'s two corrections to this record: the stamp\'s pass on a passage still at its position, and the fields settling a tie with no position)'));
  assert.ok(tests.includes('`tools/file-review-plan-tiebreak-review.test.mjs` holds the tie-break review\'s two corrections to the record against the host: a passage still at its position costs its copy fields one classification pass per distinct anchor on every write, charged to the budget, and past it keeps the fields it has while stderr says how many, once per write (the stamping pass of `refreshAnchorAts`, `noteUnstamped`, `fullMatches`\'s memo), and a tie with no position is settled by the fields before it is refused (`locateStored`).'));
  assert.ok(!tests.includes('with no note'), 'the Tests section no longer says the skip leaves no note');
  assert.ok(!decision51.includes('\u2014'), 'decision 51 has no em dash');
  // the host paragraph already scoped the refusal to the fall-through; the decision now agrees with it
  assert.ok(op.includes('else the match nearest the position, a guess, and a tie with no position refuses `anchor-ambiguous` as before'));
});

test('locateStored runs the ordinal rule and the section rule before the hintless refusal, so a positionless comment is confirmed from its fields and refused only without them', () => {
  const src = fn(host, 'locateStored');
  inOrder(src, [
    "if (o && o.copies === hits.length) return span(hits[o.ordinal - 1], true, 'ordinal');",
    "if (under.length === 1) return span(under[0], true, 'section');",
    "if (at === undefined) return { error: 'anchor-ambiguous' };",
    "return span(engine.locateAnchor(text, anchor, at).from, false, 'nearest');",
  ], 'locateStored');
  // on the tied text, with no anchorAt at all
  assert.deepEqual(locateStored(TEXT, { anchor: ANCHOR, ordinal: 2, copies: 3 }, true), span(COPIES[1], true, 'ordinal'), 'the count unchanged: the ordinal\'s copy, confirmed');
  assert.equal(sectionAt(TEXT, COPIES[2], true), 'Report > Third pass', 'the fixture: the third copy\'s heading path');
  assert.deepEqual(locateStored(TEXT, { anchor: ANCHOR, ordinal: 3, copies: 2, section: 'Report > Third pass' }, true), span(COPIES[2], true, 'section'), 'the count changed: the one copy under the stored heading path, confirmed');
  assert.deepEqual(locateStored(TEXT, { anchor: ANCHOR, ordinal: 3, copies: 2 }, true), { error: 'anchor-ambiguous' }, 'the count changed and no heading path: refused');
  assert.deepEqual(locateStored(TEXT, { anchor: ANCHOR, section: 'Report > Third pass' }, false), { error: 'anchor-ambiguous' }, 'a non-markdown file: the section rule never confirms, so refused');
  assert.deepEqual(locateStored(TEXT, { anchor: ANCHOR }, true), { error: 'anchor-ambiguous' }, 'neither position nor field (a comment the CLI made): refused, as before');
});
