// The plan's "Both" acceptance criterion under "Commenting from either view, and in every format"
// says how a comment written from the viewer compares with the one `addComment` (the comment CLI)
// writes, and the host still does what it says (plans/file-review.md; tools/file-comments-host.mjs).
//
// The anchors follow-on (2026-09-07) added `anchorAt` to every passage comment and widened the
// stored anchor's context past the CLI's 24 characters when those tie with another copy's. The
// slice amended the contract, the host paragraph, the painting paragraph and the follow-on note,
// and reworded the host test's title to except `anchorAt`, but the criterion kept its pre-slice
// text ("apart from id and `ts`"), so the plan denied what its own pin asserted (review finding,
// 2026-09-07). The criterion now states the exception and the widening rule, and this module keeps
// three things in step: the criterion's wording, the host test that pins it (its title must make the
// same exception, or the two disagree again), and the behavior on the repo's fixture: a passage
// unique at 24 characters keeps `addComment`'s anchor, a tied one is stored wider, and the host adds
// `anchorAt` and nothing else. Synthetic: the repo's own fixture text, no session data.
// Run: node --test tools/file-review-plan-acceptance.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

import { uniqueAnchor, ANCHOR_CTX, ANCHOR_CTX_STEP } from './file-comments-host.mjs';
import { addComment } from '../vendor/track-changents/cli/track-comment.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');
const engine = createRequire(import.meta.url)(path.join(REPO, 'vendor', 'track-changents', 'engine.js'));

const plan = read('plans', 'file-review.md');
const host = read('tools', 'file-comments-host.mjs');
const hostTest = read('tools', 'file-comments-host.test.mjs');
const fixture = read('tests', 'fixtures', 'file_comments', 'report.md');

// The text between two headings, hard wraps collapsed so an assertion survives a rewrap.
function section(from, to) {
  const a = plan.indexOf(from);
  assert.ok(a >= 0, `heading ${JSON.stringify(from)} not found in the plan`);
  const b = plan.indexOf(to, a + from.length);
  assert.ok(b > a, `heading ${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return plan.slice(a, b).replace(/\s+/g, ' ');
}
const ux = section('### Commenting from either view, and in every format', '### The viewer seam');
const tests = section('## Tests', '## Docs');

// The comment addComment writes for `quote` on the fixture, at the CLI's first occurrence.
function cliComment(quote) {
  const seed = { v: 3, path: 'docs/report.md', suggestions: [], comments: [] };
  const r = addComment(seed, fixture, quote, 'A note.', 'you', 1700000000000, null);
  assert.equal(r.error, undefined);
  return seed.comments[0];
}

test('the Both criterion excepts anchorAt and states when the anchor is wider than addComment\'s; the pre-slice wording is gone', () => {
  assert.ok(ux.includes('deep-equals the one `addComment` writes for the same quote and note, apart from id, `ts`, and the romp-only `anchorAt` stored beside the anchor'));
  assert.ok(ux.includes('the anchor is the one `addComment` writes when its 24 characters of context locate the passage uniquely, and wider only when they tie with another copy\'s'));
  assert.ok(!ux.includes('apart from id and `ts`;'), 'the criterion no longer promises deep-equality with addComment\'s whole object');
  assert.ok(ux.includes("the sidecar's changes, fingerprint, and version are unchanged"), 'the sidecar clause stands');
  // the Tests section names this module, as it names every pin that exists
  assert.ok(tests.includes('`tools/file-review-plan-acceptance.test.mjs` pins the Both acceptance criterion'));
  assert.ok(fs.existsSync(path.join(HERE, 'file-review-plan-acceptance.test.mjs')));
});

test('the host test that pins the criterion makes the same exception in its title, so the plan and its pin agree', () => {
  assert.ok(hostTest.includes("test('a passage comment deep-equals addComment\\'s object for the same quote and note apart from id, ts and the romp-only anchorAt"), 'the pin\'s title excepts anchorAt');
  assert.ok(hostTest.includes("'a passage unique at 24 characters keeps track-comment\\'s context'"), 'the pin asserts the 24-character case keeps the CLI\'s anchor');
  assert.ok(hostTest.includes("'the stored anchor is wider than the 24 characters the browser sent'"), 'the pin asserts the tied case is stored wider');
});

test('on the fixture, a passage unique at 24 characters keeps addComment\'s anchor, and the host adds anchorAt beside it', () => {
  const quote = 'cut p95 latency by 40%';
  const at = fixture.indexOf(quote);
  assert.ok(at >= 0 && fixture.indexOf(quote, at + 1) === -1, 'the fixture holds the passage once');
  const want = cliComment(quote);
  const u = uniqueAnchor(fixture, at, at + quote.length);
  assert.equal(u.unique, true);
  assert.deepEqual(u.anchor, want.anchor, 'the stored anchor is the CLI\'s 24 characters of context');
  assert.equal(u.anchor.prefix.length, ANCHOR_CTX);
  assert.deepEqual(Object.keys(want), ['id', 'author', 'ts', 'anchor', 'body', 'replies', 'resolved'], 'addComment writes no anchorAt');
  // the fields the host adds, right after the anchor: the position, then the copy fields (the tie-break, 2026-09-11);
  // the object it builds otherwise takes addComment's shape
  assert.ok(/anchor: stored\.anchor,\s*\n\s*anchorAt: loc\.from,\s*\n\s*\.\.\.copy,/.test(host), 'the host stores anchorAt and the copy fields beside the anchor, and nothing else beyond addComment\'s keys');
  assert.ok(!/authorId/.test(host.slice(host.indexOf('function buildComment('), host.indexOf('\n}\n', host.indexOf('function buildComment(')))), 'no authorId, as addComment with none');
});

test('on the fixture, a passage whose 24 characters tie with another copy\'s is stored one step wider than addComment\'s anchor', () => {
  const quote = 'Ship it.';
  const first = fixture.indexOf(quote), second = fixture.indexOf(quote, first + 1);
  assert.ok(second > first, 'the fixture holds the passage twice');
  const want = cliComment(quote);
  assert.equal(want.id, `1700000000000-${first}`, 'addComment anchors the first occurrence');
  // the tie: 24 characters either side of the second copy equal the first copy's, so the CLI's anchor cannot tell them apart
  assert.deepEqual(engine.makeAnchor(fixture, second, second + quote.length), want.anchor, 'at 24 characters the copies share one anchor');
  const u = uniqueAnchor(fixture, second, second + quote.length);
  assert.equal(u.unique, true);
  assert.notDeepEqual(u.anchor, want.anchor, 'the stored anchor is wider than addComment\'s');
  assert.equal(u.anchor.prefix.length, ANCHOR_CTX + ANCHOR_CTX_STEP, 'one step wider tells the copies apart');
  assert.equal(u.anchor.quote, quote, 'the quote is unchanged; only the context widens');
  assert.equal(engine.locateAnchor(fixture, u.anchor).from, second, 'a hintless reader places it on the selected copy');
});
