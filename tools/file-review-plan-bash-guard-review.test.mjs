// Decision 47's cost sentence and its test inventory (plans/file-review.md) held to the hook and to the tree.
//
// The review's second round (2026-09-10) found two records of the Bash-side guard stale. The decision said
// "about 60 ms per Bash call" with no condition, while the hook's verdict (trackedIn in
// hooks/romp-track-bash-guard.mjs) pays store-io's link closure, a listing of every .md under the project root
// and a read of every tracked note, for every write target inside a tracking project that the tracked list does
// not name: the common write in a project that tracks anything, and a cost that grows with the project's
// markdown count (measured at 80 to 100 ms on a 3000-note tree and 130 to 170 ms on a 12000-note one, against
// 55 to 65 ms for the no-walk path). And the decision, the Tests bullet and hooks/README.md named
// tools/romp-track-bash-guard.test.mjs alone for the grammar, while the first round's module,
// tools/romp-track-bash-guard-shapes.test.mjs, which holds the subshell-cd, heredoc, bash -lc, [[ ]], prefix,
// keyword-open, NUL-byte, walk-cap and one-closure pins, was named nowhere; the existing pin
// (tools/file-review-plan-bash-guard.test.mjs) checks that the modules the plan names exist, never that the
// tree's modules are named, so the omission failed nothing. This module holds the cost sentence to the code it
// describes (the closure's place in the verdict's order, the empty-list return before it, the once-per-call Map
// the targets share) and to the hook's behavior on a scratch project (a read, an explicit hit and an empty list
// walk nothing; a write the list does not name walks the root once, however many targets); the shapes module to
// the pins the plan credits it with; and the inventory to the tree: every romp-track-bash-guard*.test.mjs under
// tools/ is named in decision 47 and in the Tests bullet, and every file-review-plan-bash-guard*.test.mjs in the
// bullet, so a later round's module fails here by name. Synthetic: a project under os.tmpdir() with invented
// paths, and the repo's own text.
// Run: node --test tools/file-review-plan-bash-guard-review.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { evaluate } from '../hooks/romp-track-bash-guard.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');

const plan = read('plans', 'file-review.md');
const hook = read('hooks', 'romp-track-bash-guard.mjs');
const storeIo = read('vendor', 'track-changents', 'store-io.mjs');
const vendoredGuard = read('vendor', 'track-changents', 'hooks', 'track-guard.mjs');

const SHAPES = 'tools/romp-track-bash-guard-shapes.test.mjs';
const SELF = 'tools/file-review-plan-bash-guard-review.test.mjs';

// A span of a document, hard wraps collapsed so an assertion survives a rewrap.
function between(doc, from, to) {
  const a = doc.indexOf(from);
  assert.ok(a >= 0, `${JSON.stringify(from)} not found`);
  const b = doc.indexOf(to, a + from.length);
  assert.ok(b > a, `${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return doc.slice(a, b).replace(/\s+/g, ' ');
}
const d47 = between(plan, '47. **A guard on the Bash tool too**', '48. **');
// The Tests section's bullet for the guard: from its lead to the next bullet (a line opening with "- ";
// a bullet's continuation lines are indented) or the section's end.
const bulletAt = plan.indexOf('\n- The Bash-side guard (2026-09-10, decision 47):');
assert.ok(bulletAt >= 0, 'the Tests section carries the guard\'s bullet');
const sectionEnd = plan.indexOf('\n## Docs', bulletAt);
assert.ok(sectionEnd > bulletAt, 'the Docs section follows the Tests section');
let bulletEnd = plan.indexOf('\n- ', bulletAt + 1);
if (bulletEnd === -1 || bulletEnd > sectionEnd) bulletEnd = sectionEnd;
const bullet = plan.slice(bulletAt, bulletEnd).replace(/\s+/g, ' ');
// The test modules a span names in backticks, as repo-relative paths.
const testFiles = (text) => [...text.matchAll(/`((?:tools|tests|ui\/webview)\/[\w.-]+)`/g)].map((m) => m[1]);

// ── the cost sentence ───────────────────────────────────────────────────────────────────────────────────────────

test('decision 47 states the cost with its condition: 60 ms without the closure, one walk per call for a write the list does not name, growing with the markdown count', () => {
  assert.ok(!d47.includes('(decision 24). About 60 ms per Bash call.'), 'the unconditional figure is gone');
  assert.ok(d47.includes('Cost: about 60 ms per Bash call when no target needs the link closure'));
  assert.ok(d47.includes('a write to a file inside a tracking project that the list does not name'));
  assert.ok(d47.includes('adds one walk of the project\'s markdown tree per call, store-io\'s `trackedClosure`'));
  assert.ok(d47.includes('a listing of every .md under the root and a read of every tracked note'));
  assert.ok(d47.includes('the same walk the vendored guard pays on every such Write'));
  assert.ok(d47.includes('built once and shared by all the command\'s targets, so a directory copy pays it once'));
  assert.ok(d47.includes('growing with the project\'s markdown count and well under the installer\'s 10 s timeout'));
  assert.ok(!/\u2014/.test(d47), 'no em dash');
});

test('the hook agrees: the closure comes after the veto and the explicit list, never with an empty list, once per call and shared by every target', () => {
  const trackedIn = hook.slice(hook.indexOf('function trackedIn(root, file, closures)'), hook.indexOf('export function isGuardedPath'));
  assert.ok(trackedIn.length > 0, 'trackedIn precedes isGuardedPath');
  const veto = trackedIn.indexOf('if (engine.isTracked(untrackedPaths(root), rel)) return false;');
  const explicit = trackedIn.indexOf('if (engine.isTracked(list, rel)) return true;');
  const empty = trackedIn.indexOf('if (!list.length) return false;');
  const memo = trackedIn.indexOf('let closure = closures.get(root);');
  const walk = trackedIn.indexOf('if (!closure) { closure = trackedClosure(root); closures.set(root, closure); }');
  assert.ok(veto >= 0 && explicit > veto && empty > explicit && memo > empty && walk > memo, 'the veto, the explicit list, the empty list, the memo, then the walk');
  const evaluateSrc = hook.slice(hook.indexOf('export function evaluate(raw)'), hook.indexOf('const invokedDirectly'));
  assert.ok(evaluateSrc.includes('const closures = new Map();'), 'one Map per call');
  assert.ok(evaluateSrc.includes('if (!isGuardedPath(t.path, closures)) continue;'), 'handed to every target');
  assert.ok(hook.includes('ONE walk of the project\'s markdown tree per call'), 'the hook\'s header states the same cost');
  // the walk is what the plan says it is: store-io lists every .md under the root and reads every tracked note
  const closure = storeIo.slice(storeIo.indexOf('export function trackedClosure(vaultRoot)'), storeIo.indexOf('export function isTrackedFile'));
  assert.ok(closure.includes('const index = buildLinkIndex(vaultRoot);'), 'the closure builds the link index');
  assert.ok(storeIo.includes('const rels = walkVaultMd(vaultRoot);'), 'the index lists every .md under the root');
  assert.ok(closure.includes("try { text = fs.readFileSync(path.join(vaultRoot, rel), 'utf8'); } catch { continue; }"), 'and every tracked note is read');
  // and the vendored guard pays it on every Write to such a file: isTrackedFile falls to the closure in the same order
  const isTracked = storeIo.slice(storeIo.indexOf('export function isTrackedFile(vaultRoot, file)'), storeIo.indexOf('export function writeTrackedPaths'));
  assert.ok(isTracked.includes('if (!list.length) return false;') && isTracked.includes('return trackedClosure(vaultRoot).has(rel);'));
  assert.ok(vendoredGuard.includes('tracked = isTrackedFile(root, file);'), 'the vendored guard asks store-io');
});

test('on a scratch project the condition holds: a read, an explicit hit and an empty list walk nothing; a write the list does not name walks the root once, however many targets', () => {
  const proj = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'romp-plan-bash-guard-cost-')));
  const saved = process.env.TRACKCHANGES_ROOT;
  delete process.env.TRACKCHANGES_ROOT;
  try {
    for (const d of ['.trackchanges', 'docs', 'base']) fs.mkdirSync(path.join(proj, d));
    const config = (tracked) => fs.writeFileSync(path.join(proj, '.trackchanges', 'config.json'), JSON.stringify({ v: 2, tracked }));
    config(['docs/report.md']);
    fs.writeFileSync(path.join(proj, 'docs', 'report.md'), 'The api session cut tail latency by 40%.\n');
    fs.writeFileSync(path.join(proj, 'base', 'report.md'), 'an older copy\n');
    fs.writeFileSync(path.join(proj, 'base', 'notes.md'), 'a note in the source folder\n');
    const payload = (command) => JSON.stringify({ tool_name: 'Bash', tool_input: { command }, cwd: proj });
    // the walk is the closure's readdir of the project root; count those
    const walks = (fn) => {
      const real = fs.readdirSync;
      let n = 0;
      fs.readdirSync = function (p, ...rest) {
        if (path.resolve(String(p)) === proj) n++;
        return real.call(this, p, ...rest);
      };
      try { fn(); } finally { fs.readdirSync = real; }
      return n;
    };
    let reason;
    assert.equal(walks(() => { reason = evaluate(payload('ls -la')); }), 0, 'a read names no target');
    assert.equal(reason, null);
    assert.equal(walks(() => { reason = evaluate(payload('cat docs/report.md | grep latency')); }), 0, 'a read of the tracked file');
    assert.equal(reason, null);
    assert.equal(walks(() => { reason = evaluate(payload('cp base/report.md docs/report.md')); }), 0, 'an explicit hit on the list needs no closure');
    assert.ok(reason && reason.includes(path.join(proj, 'docs', 'report.md')), 'and is refused');
    assert.equal(walks(() => { reason = evaluate(payload('echo x > other.md')); }), 1, 'a write the list does not name pays one walk');
    assert.equal(reason, null);
    assert.equal(walks(() => { reason = evaluate(payload('echo a > o1.md; echo b > o2.md; echo c > o3.md; cp -r base docs/new')); }), 1, 'one walk shared by every target, a directory copy among them');
    assert.equal(reason, null);
    config([]);
    assert.equal(walks(() => { reason = evaluate(payload('echo x > other.md')); }), 0, 'an empty list walks nothing');
    assert.equal(reason, null);
  } finally {
    if (saved === undefined) delete process.env.TRACKCHANGES_ROOT; else process.env.TRACKCHANGES_ROOT = saved;
    try { fs.rmSync(proj, { recursive: true, force: true }); } catch { /* ignore */ }
  }
});

// ── the shapes module, named and credited ───────────────────────────────────────────────────────────────────────

test('decision 47 and the Tests bullet name the shapes module, credit it to the review\'s first round, and it holds the pins they credit it with', () => {
  assert.ok(fs.existsSync(path.join(REPO, SHAPES)), `${SHAPES} exists`);
  assert.ok(d47.includes('`' + SHAPES + '`, from the review\'s first round (2026-09-10), the shapes that round found misread'), 'decision 47 names and credits it');
  assert.ok(bullet.includes('from the review\'s first round (2026-09-10), `' + SHAPES + '` pins the shapes the round found misread'), 'the Tests bullet names and credits it');
  const shapes = read(...SHAPES.split('/'));
  for (const title of [
    "test('a cd inside ( ... ) moves nothing after the ): the untracked write after it is allowed, the tracked one refused'",
    "test('a cd inside an if, loop or case body leaves the cwd unknown once the body closes: the body may not run'",
    "test('a python or node heredoc script followed by &&, |, ; or & on the opener line is read'",
    "test('a heredoc piped into python or node is its stdin too; a heredoc redirected into a file is the redirect\\'s write, not a script'",
    "test('a shell reading its script from a heredoc is read like sh -c: bash <<EOF, bash -s <<EOF, bash - <<EOF, sh <<EOF'",
    "test('a -c in an option cluster is a -c: bash -lc, sh -ec, bash -xc; a variable script there is opaque'",
    "test('python or node with options and a heredoc on stdin is read: -u, -B, -I, -X utf8, --input-type=module, --no-warnings'",
    "test('a prefix with options still leads to the command: sudo -u, sudo -n, env -u, timeout -s, exec -a, time -p, command -p'",
    "test('pushd moves the cwd like cd; popd leaves it unknown'",
    "test('[[ a > b ]] and (( a > b )) compare and write nothing; [ a > b ] and test a > b redirect, as in the shell'",
    "test('a function definition is not a run: a cd in its body moves nothing after it; a write in it is still a target'",
    "test('Path(x).open with a write mode, open with keyword arguments in any order, io.open, and fs.openSync with a write flag are writes'",
    "test('node inline scripts in each spelling: -e, --eval, -p, --print'",
    "test('the refusal speaks of a change, the person\\'s word, never a suggestion'",
    "test('a tracked file that is binary under a text-looking name passes: the NUL-byte rule'",
    "test('a directory source is walked to 500 files and no further'",
    "test('a directory copy to an untracked destination walks the project once, not once per landing file'",
    "test('the per-call closure agrees with store-io\\'s isTrackedFile on every kind of path'",
    "test('the hook process rules the same way on a subshell cd, a chained heredoc and a heredoc-fed shell'",
  ]) assert.ok(shapes.includes(title), `the shapes module holds ${title}`);
  assert.ok(shapes.includes("'five literal targets, one walk'"), 'the one-closure pin covers the five redirect targets the bullet names');
  assert.ok(shapes.includes("assert.equal(t.length, 500, 'the cap');"), 'the walk cap the bullet names is 500');
});

// ── the inventory, held to the tree ─────────────────────────────────────────────────────────────────────────────

test('every romp-track-bash-guard module under tools/ is named in decision 47 and in the Tests bullet, and every file-review-plan-bash-guard module in the bullet: a later round\'s module fails here by name', () => {
  const inD47 = new Set(testFiles(d47)), inBullet = new Set(testFiles(bullet));
  const driven = fs.readdirSync(path.join(REPO, 'tools')).filter((f) => /^romp-track-bash-guard[\w-]*\.test\.mjs$/.test(f)).map((f) => 'tools/' + f).sort();
  assert.ok(driven.length >= 2, 'the scan reaches the family: ' + driven.join(', '));
  for (const f of driven) {
    assert.ok(inD47.has(f), `${f} is in the tree but decision 47 names it nowhere`);
    assert.ok(inBullet.has(f), `${f} is in the tree but the Tests bullet names it nowhere`);
  }
  const pins = fs.readdirSync(path.join(REPO, 'tools')).filter((f) => /^file-review-plan-bash-guard[\w-]*\.test\.mjs$/.test(f)).map((f) => 'tools/' + f).sort();
  assert.ok(pins.length >= 2, 'the plan pins are in the tree: ' + pins.join(', '));
  for (const f of pins) assert.ok(inBullet.has(f), `${f} is in the tree but the Tests bullet names it nowhere`);
  assert.ok(inD47.has(SELF) && inBullet.has(SELF), 'this pin is named in both places');
  for (const f of new Set([...inD47, ...inBullet])) assert.ok(fs.existsSync(path.join(REPO, f)), `${f} is named but not in the tree`);
  assert.ok(bullet.includes('every `romp-track-bash-guard…` module under `tools/` is named in decision 47 and in this bullet, and every `file-review-plan-bash-guard…` module in this bullet'), 'the bullet says this pin holds the inventory to the tree');
});
