// The anchors follow-on's review (2026-09-07) changed what the host does with a stored position and
// with a tie the request's offset cannot settle, and the plan's governing sections lagged behind it:
// the contract, the host paragraph, the commenting section and the follow-on note still said the
// position was refreshed only for an anchor that locates uniquely and a tie was refused only when no
// offset was sent, while the host moved a tied position through the recorded changes (movedCopy),
// refused a sent offset that sits on no tied copy (anchor-moved, surfaced as anchor-ambiguous),
// refreshed at two sites under a scan budget, and the model named a recurring passage's copy by its
// surroundings in `desc` (review finding, round 2). A test written from the plan asserted the
// opposite of the host, and the plan's pin (tools/file-review-plan.test.mjs) held the stale
// sentences, so neither side caught the drift. The plan now states each of those, and this module
// keeps it in step with the host and the model: every sentence the plan gained is checked against
// the source it describes, the refusal against the exported locateExact on the repo's fixture, and
// the test modules and e2e cases the note names against the files that exist. The second review
// (2026-09-08) then bounded the refresh's classification scan under the same budget (a comment past
// it keeps its position, counted as `unscanned`) and mapped the comment verb's offset into the text
// the host read (`browserHint`, one character on a BOM file); the pins here read the host as it stands
// after that review, not as it stood between the two (a pin written against the earlier host went red
// the moment the second review landed, so each source pin below sits beside the behavior it names).
// Synthetic: the repo's own text, no session data.
// Run: node --test tools/file-review-plan-anchors.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { locateExact, REFRESH_SCAN_BUDGET } from './file-comments-host.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');
const exists = (...parts) => fs.existsSync(path.join(REPO, ...parts));

const plan = read('plans', 'file-review.md');
const host = read('tools', 'file-comments-host.mjs');
const panel = read('ui', 'webview', 'file-comments.ts');
const model = read('ui', 'webview', 'file-comments-model.ts');
const e2e = read('tests', 'test_file_comments_e2e.py');

// The text between two headings, hard wraps collapsed so an assertion survives a rewrap.
function section(from, to) {
  const a = plan.indexOf(from);
  assert.ok(a >= 0, `heading ${JSON.stringify(from)} not found in the plan`);
  const b = plan.indexOf(to, a + from.length);
  assert.ok(b > a, `heading ${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return plan.slice(a, b).replace(/\s+/g, ' ');
}
const contract = section('## The contract: the track-changents sidecar', '## Kernel: two ops and a host script');
const op = section('## Kernel: two ops and a host script', '### The message to the session');
const ux = section('### Commenting from either view, and in every format', '### The viewer seam');
const note = section('### Slice 2: the session', '### Slice 3: region comments on images');
const tests = section('## Tests', '## Docs');

// A function's source, from its `function name(` to the first line that is a lone closing brace.
function fn(src, name) {
  const a = src.indexOf(`function ${name}(`);
  assert.ok(a >= 0, `${name} is defined`);
  const b = src.indexOf('\n}\n', a);
  assert.ok(b > a, `${name} closes`);
  return src.slice(a, b);
}
// Each needle occurs in `src`, and in this order.
function inOrder(src, needles, what) {
  let at = -1;
  for (const n of needles) {
    const i = src.indexOf(n, at + 1);
    assert.ok(i > at, `${what}: ${JSON.stringify(n)} follows the previous step`);
    at = i;
  }
}

// ── the contract: the refresh by where the whole anchor sits ────────

test('the contract states the refresh by where the whole anchor sits, and refreshAnchorAts takes the three cases in that order', () => {
  assert.ok(contract.includes('the host script refreshes it on every sidecar write it makes, against the text the sidecar is saved for, by where the whole anchor sits in that text'));
  assert.ok(contract.includes('at one place, the position becomes that place'));
  assert.ok(contract.includes("at several (the copies tie), the position stands where it still names a copy and otherwise moves only to the one copy the sidecar's recorded changes can have carried it to, never to the nearest, and only while the file is as the sidecar's last writer left it"));
  assert.ok(contract.includes("nowhere, the engine's scoring places it, under a scan budget per write past which the remaining such comments keep the position they have"));
  assert.ok(contract.includes('A comment without an anchor never carries it'));
  const refresh = fn(host, 'refreshAnchorAts');
  inOrder(refresh, [
    'const budget = { left: REFRESH_SCAN_BUDGET, skipped: 0, unscanned: 0 };',
    'if (!affordableScan(budget, text, c.anchor)) { budget.unscanned++; continue; }',
    'if (hits.length === 1) { c.anchorAt = hits[0]; continue; }',
    'if (hits.length > 1) {',
    'hits.includes(at)',
    'store[TEXT_AS_WRITTEN] !== true) continue;',
    'const moved = movedCopy(hits, at, bounds);',
    'if (moved !== null) c.anchorAt = moved;',
    'if (!affordable(budget, text, c.anchor)) continue;',
    'const loc = locateExact(text, c.anchor, undefined);',
    'if (!loc.error) c.anchorAt = loc.from;',
  ], 'the refresh');
  assert.ok(/const budget = \{[^}]*\};/.test(refresh) && !/budget = /.test(refresh.replace(/const budget = \{[^}]*\};/, '')), 'the budget is per write: one object, made once per call');
  // both ways a comment keeps its position past the budget are counted, and stderr says how many of each
  // (the second review, 2026-09-08: the classification scan, one whole-text pass per distinct anchor, is
  // budgeted too, not only the engine's scoring for a passage that sits nowhere in whole)
  assert.ok(refresh.includes('if (budget.skipped) {') && refresh.includes('if (budget.unscanned) {'), 'the skipped and the unscanned are reported apart');
  assert.equal((refresh.match(/process\.stderr\.write\(/g) || []).length, 2, 'one stderr line each');
  const scan = fn(host, 'affordableScan');
  assert.ok(scan.includes('if (budget.left <= 0) return false;') && scan.includes('budget.left -= text.length;'), 'a classification scan costs one pass over the text against the same budget');
  const place = fn(host, 'affordable');
  assert.ok(place.includes('if (budget.left <= 0) { budget.skipped++; return false; }') && place.includes('if (cost > budget.left) { budget.skipped++; return false; }'), "the engine's scoring is what counts as skipped");
  assert.ok(Number.isInteger(REFRESH_SCAN_BUDGET) && REFRESH_SCAN_BUDGET > 0, 'the budget is exported');
  // never to the nearest copy: movedCopy answers the one copy the bounds vouch for, and null for none or several
  const moved = fn(host, 'movedCopy');
  assert.ok(moved.includes('if (d < lo || d > hi) continue;') && moved.includes('if (found !== null) return null;'));
});

// ── the refusal: an offset the text moved from under ────────────────

test('the host paragraph and the commenting section state the refusal of an offset that sits on no tied copy, and the host refuses it on the fixture', () => {
  assert.ok(op.includes("`anchor-ambiguous` when two candidates tie and the request's offset cannot settle it: no offset was sent, or the offset sent sits on none of the tied copies in the text the host read, because the text moved after the selection"));
  assert.ok(op.includes('that offset is refused, with a message that says the text moved, rather than placed on the nearest copy'));
  assert.ok(ux.includes('two candidates tie and the offset cannot settle it: none was sent, or the one sent sits on no tied copy because the text moved after the selection, and the note is then refused rather than placed on the nearest copy'));
  assert.ok(ux.includes('The typed note is never discarded by a refusal'));
  // the host: the creation path asks for an exact hit, with the request's offset mapped into the text the
  // host read (the second review, 2026-09-08: the browser measures against the fetch's BOM-stripped text,
  // the host keeps the BOM, so on a BOM file the correct selection was refused as moved), and maps
  // anchor-moved to the anchor-ambiguous refusal
  assert.ok(/locateExact\(text, anchor, browserHint\(text, args\.hintOffset\), \{ exact: true \}\)/.test(host), 'buildComment locates exactly, on the mapped offset');
  const hint = fn(host, 'browserHint');
  assert.ok(hint.includes("if (typeof hintOffset !== 'number' || !Number.isFinite(hintOffset)) return hintOffset;"), 'no offset passes through untouched');
  assert.ok(hint.includes('return text.charCodeAt(0) === 0xFEFF ? hintOffset + 1 : hintOffset;'), 'a BOM file adds the one character the fetch stripped');
  assert.equal((host.match(/browserHint\(/g) || []).length, 2, "the definition and the comment verb's call: a stored anchorAt never goes through it");
  assert.ok(/if \(built\.error === 'anchor-moved'\) \{\s*\n\s*throw new Refusal\('anchor-ambiguous', /.test(host), 'anchor-moved surfaces as anchor-ambiguous');
  assert.ok(host.includes('the text moved after it was selected'), 'and the message says the text moved');
  // behavior, on the fixture whose "Ship it." recurs with the same 24 characters either side
  const text = read('tests', 'fixtures', 'file_comments', 'report.md');
  const a = text.indexOf('Ship it.'), b = text.indexOf('Ship it.', a + 1);
  assert.ok(b > a && text.indexOf('Ship it.', b + 1) === -1, 'the fixture: two copies');
  const at24 = { quote: 'Ship it.', prefix: text.slice(b - 24, b), suffix: text.slice(b + 8, b + 32) };
  assert.deepEqual(at24, { quote: 'Ship it.', prefix: text.slice(a - 24, a), suffix: text.slice(a + 8, a + 32) }, 'the fixture: the copies tie at 24');
  assert.deepEqual(locateExact(text, at24, undefined, { exact: true }), { error: 'anchor-ambiguous' }, 'no offset sent');
  assert.deepEqual(locateExact(text, at24, b, { exact: true }), { from: b, to: b + 8 }, 'an offset on a copy settles it');
  assert.deepEqual(locateExact(text, at24, b + 3, { exact: true }), { error: 'anchor-moved' }, 'an offset on no copy is refused, not placed on the nearest');
  assert.deepEqual(locateExact(text, at24, b + 3), { from: b, to: b + 8 }, 'a stored position keeps nearest-wins');
  // the same selection on a BOM-prefixed file: the browser's offset (b, in the stripped text) sits on no
  // copy of this text, whose copies sit one later; mapped by the BOM it settles the tie
  const bom = '\uFEFF' + text;
  assert.deepEqual(locateExact(bom, at24, b, { exact: true }), { error: 'anchor-moved' }, 'unmapped, the correct selection is refused as moved: the bug browserHint fixes');
  assert.deepEqual(locateExact(bom, at24, b + 1, { exact: true }), { from: b + 1, to: b + 9 }, 'mapped, it settles the tie');
});

// ── the two refresh sites ───────────────────────────────────────────

test('the host paragraph names both refresh sites and the measure they serve, and the host refreshes at exactly those two', () => {
  assert.ok(op.includes('Every sidecar write the host makes refreshes `anchorAt`, in `stageSidecar`, the one function every sidecar write goes through, and once more before the reply is measured, so the bytes the refresh adds count against `too-large`'));
  assert.ok(op.includes("a stored comment's anchor is located with its `anchorAt` as the hint"));
  assert.ok(/function stageSidecar\(root, storePath, store, text\) \{\s*\n\s*refreshAnchorAts\(store, text\);/.test(host), 'first thing in stageSidecar');
  assert.ok(/function checkReplyFits\(ctx, state, extra, pending, what\) \{\s*\n\s*refreshAnchorAts\(state\.store, state\.text\);/.test(host), 'first thing in checkReplyFits');
  const calls = host.match(/^\s*refreshAnchorAts\(/gm) || [];
  assert.equal(calls.length, 2, 'two call sites, no more');
  assert.ok(note.includes('first thing in `stageSidecar`, the one function every sidecar write goes through, and again in `checkReplyFits` before the reply is measured'));
});

// ── the desc sentence: a recurring passage named by its surroundings ─

test('the desc sentence states the widened form, and the model builds it from the anchor the host stored', () => {
  assert.ok(op.includes("`desc` is the first 40 characters of the passage for an anchored comment, and when the host widened the anchor's context past 24 characters because the passage recurs, also the copy by its whole surroundings"));
  assert.ok(op.includes('`, the one after "…" and before "…"`'));
  assert.ok(op.includes("a side the file's bound left empty is not named"));
  assert.ok(op.includes('the text a session can pass to `track-edit --old`, which refuses text that is not unique, to reach that copy'));
  assert.ok(op.includes('a side wider than 120 characters (five widening steps) is not printed, and the desc says instead that the passage appears more than once with the same text around each copy'));
  assert.ok(model.includes('export const ANCHOR_CTX = 24;'));
  assert.ok(model.includes('export const DESC_CTX_MAX = ANCHOR_CTX * 5;'), 'the bound is five steps, 120 characters');
  assert.ok(model.includes('export const RECURS_CLAUSE = ", which appears more than once with the same text around each copy";'), 'the clause the plan paraphrases');
  const widened = fn(model, 'anchorWidened');
  assert.ok(widened.includes('a.prefix.length > ANCHOR_CTX') && widened.includes('a.suffix.length > ANCHOR_CTX'), 'widened means past the default on either side');
  const desc = fn(model, 'passageDesc');
  inOrder(desc, [
    `const head = 'on "' + a.quote.slice(0, 40) + '"';`,
    'if (!anchorWidened(a)) return head;',
    'if (prefix.length > DESC_CTX_MAX || suffix.length > DESC_CTX_MAX) return head + RECURS_CLAUSE;',
    'sides.push("after " + JSON.stringify(prefix));',
    'sides.push("before " + JSON.stringify(suffix));',
    'return head + ", the one " + sides.join(" and ");',
  ], 'passageDesc');
  assert.ok(/if \(prefix\) sides\.push/.test(desc) && /if \(suffix\) sides\.push/.test(desc), 'an empty side is not named');
  assert.ok(read('ui', 'webview', 'file-comments-model-recurring.test.ts').includes('passageDesc('), 'the model test exercises it');
  assert.ok(note.includes('The sent message names a recurring passage by its widened surroundings (`passageDesc`, up to 120 characters a side; past that it says only that the passage recurs with the same text around each copy)'));
});

// ── the follow-on note: what was built, and the tests that pin it ───

test('the follow-on note states the exact and bounded refresh, the refusal, and the composer follow, and names functions and tests that exist', () => {
  assert.ok(note.includes('The anchors follow-on (2026-09-07): the user asked that a passage comment anchor reliably to text that recurs'));
  assert.ok(note.includes('The refresh is exact and bounded (the review, 2026-09-07)'));
  assert.ok(note.includes('moves only to the one copy the recorded changes (the pending ops, the ops the write settles, the edits the write applies, summed as bounds on the shift) can have carried it to (`movedCopy`), never to the nearest copy'));
  assert.ok(note.includes("only while the sidecar's fingerprint says no unrecorded edit touched the file"));
  assert.ok(note.includes('one that sits nowhere in whole is placed by the engine\'s scoring under `REFRESH_SCAN_BUDGET`, past which the rest keep their position and stderr says how many'));
  assert.ok(note.includes('The refusal remains for a tie the request cannot settle: no offset sent, or an offset that sits on none of the tied copies in the text the host read because the text moved after the selection (`locateExact` with `exact`, refused `anchor-ambiguous`'));
  assert.ok(note.includes('with no offset sent when the copies now tie, so the host refuses instead of guessing (`followPassage`)'));
  // every function the note names is defined where the note puts it
  for (const name of ['refreshAnchorAts', 'stageSidecar', 'checkReplyFits', 'movedCopy', 'locateExact']) assert.ok(host.includes(`function ${name}(`), `${name} in the host`);
  assert.ok(host.includes('export const REFRESH_SCAN_BUDGET'));
  assert.ok(panel.includes('export function followPassage('), 'followPassage in the panel');
  assert.ok(model.includes('export function passageDesc('), 'passageDesc in the model');
  // the composer sends no offset for a tie it cannot settle
  assert.ok(/state: "tied"/.test(panel) && panel.includes('tied?: boolean'), 'the composer follows into a tied state');
  // the tests the note names exist, and the e2e module holds exactly the two cases
  assert.ok(note.includes('Tests: the host modules `tools/file-comments-host-anchors.test.mjs` and `-anchors-exact`, two e2e cases'));
  assert.ok(note.includes('`ui/webview/file-comments-anchors.test.ts`, `-follow` and `-model-recurring`, and this plan\'s pins in `tools/file-review-plan.test.mjs`, `-acceptance` and `-anchors`'));
  for (const f of [
    ['tools', 'file-comments-host-anchors.test.mjs'], ['tools', 'file-comments-host-anchors-exact.test.mjs'],
    ['ui', 'webview', 'file-comments-anchors.test.ts'], ['ui', 'webview', 'file-comments-follow.test.ts'], ['ui', 'webview', 'file-comments-model-recurring.test.ts'],
    ['tools', 'file-review-plan.test.mjs'], ['tools', 'file-review-plan-acceptance.test.mjs'], ['tools', 'file-review-plan-anchors.test.mjs'],
  ]) assert.ok(exists(...f), `${f.join('/')} exists`);
  const cases = e2e.match(/^def test_\w*(identical_lines|tied_past_the_cap)\w*\(/gm) || [];
  assert.equal(cases.length, 2, 'two e2e cases on a tied passage');
  // the Tests section names the exact module and this pin
  assert.ok(tests.includes('(`tools/file-comments-host-anchors.test.mjs` and `-anchors-exact`)'));
  assert.ok(tests.includes('a tied position follows its copy through a tracked insertion above, its reject, an accept and the person\'s own save, and keeps its position after an edit nobody recorded, after changes above that span a copy, and when the comment has no position'));
  assert.ok(tests.includes('`tools/file-review-plan-anchors.test.mjs` pins what the contract, the host paragraph, the commenting section and the follow-on note state after the follow-on\'s review'));
});

// ── the pre-review rules are gone from the plan ─────────────────────

test('the plan no longer states the pre-review rules anywhere', () => {
  for (const stale of [
    'whose anchor still locates uniquely',
    'whose anchor locates uniquely',
    'carries no offset to settle it',
    'two candidates tie and no offset was sent',
    'in the one sidecar-writing function',
    'one e2e case',
    'settle: no offset sent. Tests',
  ]) assert.ok(!plan.replace(/\s+/g, ' ').includes(stale), `the plan still says ${JSON.stringify(stale)}`);
});
