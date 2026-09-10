// Decision 47 (plans/file-review.md) records the dry run that found the Bash-side gap, and records it as
// "a dry run": whose it was, and what that project is, stays out of the plan. An incident from another
// project is recorded here with no project nickname or goal text (CLAUDE.md, Privacy), and every other record
// of this run in the tree (the hook's header, the guide test's docstring, the patch header, the commit
// messages) already says only that. This pins the plan to the same form, so an edit that attributes a dry run
// to a project fails here rather than in a public plan. Synthetic: only the repo's own text.
// Run: node --test tools/file-review-plan-dry-run-record.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const plan = fs.readFileSync(path.join(REPO, 'plans', 'file-review.md'), 'utf8');
const flat = plan.replace(/\s+/g, ' ');

function between(doc, from, to) {
  const a = doc.indexOf(from);
  assert.ok(a >= 0, `${JSON.stringify(from)} not found`);
  const b = doc.indexOf(to, a + from.length);
  assert.ok(b > a, `${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return doc.slice(a, b);
}
const d47 = between(flat, '47. **A guard on the Bash tool too**', '48. **');

test('decision 47 records the dry run as a dry run, dated, and attributed to no project', () => {
  assert.ok(d47.includes('A dry run (2026-09-09) saw one do exactly that'), 'the anonymous form, dated');
  assert.ok(!/\bdry run of\b/i.test(d47), 'no "dry run of <project>"');
});

test('no dry run anywhere in the plan is attributed to a project', () => {
  // "the dry run's compound command" names nobody; "the dry run of the X", "X's dry run" and "the dry run by X"
  // name whose it was, which says what that project is.
  const mentions = [...flat.matchAll(/dry[ -]run/gi)];
  assert.ok(mentions.length >= 2, 'the plan mentions the dry run at least twice (the test list and decision 47)');
  for (const m of mentions) {
    const context = flat.slice(Math.max(0, m.index - 24), m.index + m[0].length + 16);
    const after = flat.slice(m.index + m[0].length, m.index + m[0].length + 12);
    assert.ok(!/^(?:'s)? (?:of|by|from) /.test(after), `a dry run attributed to someone: ...${context}...`);
    const before = flat.slice(Math.max(0, m.index - 24), m.index);
    assert.ok(!/\w's $/.test(before), `a dry run with an owner before it: ...${context}...`);
  }
});

test('the Tests section names this pin beside the bash-guard pin', () => {
  const tests = between(flat, ' ## Tests', ' ## Docs');
  assert.ok(tests.includes('`tools/file-review-plan-dry-run-record.test.mjs`'));
  assert.ok(tests.includes('`tools/file-review-plan-bash-guard.test.mjs`'));
});
