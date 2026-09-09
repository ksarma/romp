// Seen-slice review pin for tools/file-comments-host.mjs (plans/file-review.md, decision 42 and the
// contract paragraph): the host's own account of `suggestionId` matches its code. Decision 42 took the
// resolve pass out of accept and save — a decision never touches a comment, and requireCommentsUntouched
// refuses one that would — but two comments written before it (buildComment's header, requireDecisions'
// account of `taken`) kept describing the pass as if it still ran, and the review found them twice; no
// test read the account, only the code (file-review-plan-seen.test.mjs pins `c.resolved = true` absent).
// This module reads the source once and holds both:
//   * the code: every assignment to a comment's `resolved` in the host is the person's own `resolve`
//     verb (doResolve, `= ctx.args.on`), so no decision can flip one whatever a comment says;
//   * the account: no comment names a resolve pass, and buildComment's header says what a decision
//     does to a bound comment — leaves it as it was — and names the check that holds it.
// Run: node --test tools/file-comments-host-review-seen.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const host = fs.readFileSync(path.join(REPO, 'tools', 'file-comments-host.mjs'), 'utf8');

test('the only write to a comment\'s resolved is the person\'s own resolve verb', () => {
  const writes = [...host.matchAll(/\.resolved\s*=(?!=)/g)].map((m) => host.slice(m.index, host.indexOf('\n', m.index)));
  assert.deepEqual(writes, ['.resolved = ctx.args.on; };'], 'doResolve alone assigns resolved; a decision (accept, reject, save) never does (decision 42)');
});

test('the host\'s account names no resolve pass: the comments describe the code decision 42 left', () => {
  assert.ok(!/resolve pass/.test(host), 'the accept\'s resolve pass is gone (decision 42); no comment may describe it as running');
  assert.ok(host.includes('here the panel\'s card and\n// decidedFor read it, and a decision leaves the comment as it was, open or resolved (decision 42,'),
    'buildComment\'s header says who reads suggestionId and that a decision leaves the comment as it was');
  assert.ok(host.includes('requireCommentsUntouched now\n// refuses a decision that changes one).'), 'and names the check that holds it');
  assert.ok(host.includes('(decisionRoots, in doSave), and for nothing else: a decision touches\n// no comment (decision 42).'),
    'requireDecisions\' account of `taken`: the root check alone, no resolve pass');
});
