// The Tests bullet under "The sidecar lock and the clocks" and decision 49 in plans/file-review.md, held to
// the modules the slice's review added in its third round and to store-io's pid rule, by name and whatever a
// module cites (the review's fourth round, 2026-09-11):
//   * the records pin (tools/file-review-plan-sidecar-records.test.mjs) sweeps the test modules whose text
//     cites decision 49 or 50 and names the plan. The third round's commit added three modules for store-io's
//     lock (tools/store-io-lock-inode-reuse, -folder-name and -pid-namespace) that the sweep reached and the
//     bullet did not name, so that pin was red at the commit; and two the sweep cannot reach, the vendored
//     README's row module (tools/README-track-changents-patch-0008-row, which cites the decision and not the
//     plan) and the busy retry's fence module (ui/webview/file-comments-busy-retry-fence, which cites the lock
//     and no decision). Held here by name: every test module named for store-io's lock
//     (`tools/store-io-lock-*.test.mjs`) or for a row of the vendored README's patch table
//     (`tools/README-track-changents-patch-*.test.mjs`), and the fence module, is in the tree and named in the
//     Tests bullet and in decision 49; and what the bullet says of each of the five is read from that module's
//     cases, so a case renamed or removed fails here and not silently in the record.
//   * the same round made a pid judgeable by a reader in the namespace that stamped it only (a writer outside
//     the initial pid namespace names its own on the stamp's second line), and the records had said "a dead
//     writer's lock is broken" with no condition. Held here: decision 49 and the Risks bullet state the rule,
//     and store-io's source keeps it (ownPidNamespace on /proc/self/ns/pid, the `ns <inode>` line lockStamp
//     writes from a child namespace, lockIsStale judging the pid only under the reader's own namespace and a
//     stamp by its distance from now either way), so a change to the rule fails here and the record is
//     rewritten with it.
// Synthetic: only the repo's text.
// Run: node --test tools/file-review-plan-sidecar-lock-modules.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const SELF = 'tools/file-review-plan-sidecar-lock-modules.test.mjs';
const FENCE = 'ui/webview/file-comments-busy-retry-fence.test.ts';
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');
// A module's source with its escaped apostrophes unescaped: a single-quoted test name holds \' where the record holds '.
const src = (...parts) => read(...parts).replace(/\\'/g, "'");
const exists = (m) => fs.existsSync(path.join(REPO, ...m.split('/')));

const plan = read('plans', 'file-review.md');
const storeIo = read('vendor', 'track-changents', 'store-io.mjs');
const host = read('tools', 'file-comments-host.mjs');

function between(doc, from, to) {
  const a = doc.indexOf(from);
  assert.ok(a >= 0, `${JSON.stringify(from)} not found`);
  const b = doc.indexOf(to, a + from.length);
  assert.ok(b > a, `${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return doc.slice(a, b).replace(/\s+/g, ' ');
}
const d49 = between(plan, '49. **One writer per sidecar at a time**', '50. **');
const testsBullet = between(plan, '- The sidecar lock and the clocks (2026-09-11, decisions 49 and 50)', '\n## Docs');
const risks = between(plan, '\n## Risks', '\n## Tests');
// one function's source: its `function name(` line to the next column-0 `}`
function fn(src, name) {
  let i = src.indexOf(`\nfunction ${name}(`);
  if (i < 0) i = src.indexOf(`\nexport function ${name}(`);
  assert.ok(i >= 0, `${name} is defined`);
  return src.slice(i, src.indexOf('\n}\n', i) + 3);
}
// What the Tests bullet says of a module: the one parenthetical after its name (no parenthesis inside it).
function about(m) {
  const re = new RegExp('`' + m.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '` \\(([^()]*)\\)');
  const hit = re.exec(testsBullet);
  assert.ok(hit, `the Tests bullet describes ${m} in a parenthetical after its name`);
  return hit[1];
}

// The families held by name, whatever a module cites.
const families = () => fs.readdirSync(path.join(REPO, 'tools'))
  .filter((f) => /^(?:store-io-lock-.*|README-track-changents-patch-.*)\.test\.mjs$/.test(f))
  .map((f) => `tools/${f}`);
const THIRD_ROUND = ['tools/store-io-lock-inode-reuse.test.mjs', 'tools/store-io-lock-folder-name.test.mjs',
  'tools/store-io-lock-pid-namespace.test.mjs', 'tools/README-track-changents-patch-0008-row.test.mjs', FENCE];

test('every module named for store-io\'s lock or for a README patch row, and the fence module, is in the tree and named in the Tests bullet and in decision 49', () => {
  const modules = [...families(), FENCE];
  for (const m of THIRD_ROUND) assert.ok(modules.includes(m), `the families reach ${m}: ${modules.join(', ')}`);
  for (const m of modules) {
    assert.ok(exists(m), `${m} is in the tree`);
    assert.ok(testsBullet.includes(`\`${m}\``), `the Tests bullet names ${m}`);
    assert.ok(d49.includes(`\`${m}\``), `decision 49 names ${m}`);
  }
  // the premise: the records pin's sweep admits a module by a citation of the decision and the plan's name, and two of
  // the five carry no such pair, so the sweep cannot reach them and the bullet says it names them by hand
  const CITES = /\bdecisions? (?:49|50)\b/;
  const row = read('tools', 'README-track-changents-patch-0008-row.test.mjs');
  assert.ok(CITES.test(row) && !row.includes('file-review.md'), 'the row module cites the decision and not the plan');
  assert.ok(!CITES.test(read('ui', 'webview', 'file-comments-busy-retry-fence.test.ts')), 'the fence module cites no decision');
  assert.ok(testsBullet.includes('two more the scan cannot reach, one citing the decision without the plan\'s name and one citing the lock and no decision'), 'the bullet says why the two evaded the sweep');
  assert.ok(testsBullet.includes(`\`${SELF}\` holds those five by name, whatever they cite`), 'and names this pin as the one that holds them');
  assert.ok(d49.includes(`\`${SELF}\` the third round's five modules`), 'decision 49 names this pin too');
});

test('what the bullet says of each third-round module is read from that module\'s cases, and the code keeps the behaviour', () => {
  const inode = src('tools', 'store-io-lock-inode-reuse.test.mjs');
  let said = about('tools/store-io-lock-inode-reuse.test.mjs');
  assert.ok(said.includes('kept open from the judgment through its unlink') && said.includes('entering beside it'));
  assert.ok(inode.includes('the judged inode was still open, so the fresh lock could not take its number'), 'the in-process case');
  assert.ok(inode.includes('waits for that waiter\'s write instead of removing its lock and entering beside it'), 'the real-process case');
  assert.match(fn(storeIo, 'breakStaleLock'), /const held = unlinkJudged\(lockPath, entry\.st\);/, 'the lock is unlinked as the inode judged');
  assert.match(fn(storeIo, 'breakStaleLock'), /try \{ held = unlinkJudged\(claim, other\.st\); \} finally \{ closeEntry\(other\); \}/, 'and the dead claim, its descriptor open until then');
  assert.ok(d49.includes('The entry judged stale, lock or claim, stays open from the judgment through its unlink'));

  const folder = src('tools', 'store-io-lock-folder-name.test.mjs');
  said = about('tools/store-io-lock-folder-name.test.mjs');
  for (const s of ['a link to nothing left alone with nothing created', 'a regular file refused with the OS error', 'a link to a directory followed', 'exiting 1 in well under the wait']) assert.ok(said.includes(s), `the bullet says: ${s}`);
  assert.ok(folder.includes('a link to nothing at .trackchanges refuses at once, held false, naming the link'), 'the link case');
  assert.ok(folder.includes('a regular file at .trackchanges refuses at once too, held false, with the OS error; a link to a directory is followed'), 'the file and the followed link');
  assert.ok(folder.includes('prints that line, exits 1 at once and writes nothing'), 'the real CLI');
  assert.match(fn(storeIo, 'withStoreLock'), /const bad = notADirectory\(dir\);\n\s*if \(bad\) throw new StoreLockError\(lockPath, false, bad\);/, 'store-io refuses a non-directory at the folder\'s name at once');
  assert.match(fn(host, 'checkTrackDir'), /if \(dst && !dst\.isDirectory\(\)\) \{\n\s*throw new Refusal\('unreadable'/, 'the host refuses it before it locks, as decision 49 says');
  assert.ok(d49.includes('An entry at the folder\'s name that is not a directory') && d49.includes('as `unreadable` before it locks (`checkTrackDir`)'));

  const pidns = src('tools', 'store-io-lock-pid-namespace.test.mjs');
  said = about('tools/store-io-lock-pid-namespace.test.mjs');
  for (const s of ['waits the bound out and refuses as held', 'a stamp past the bound is still broken', 'in the initial namespace a dead pid\'s lock is broken at once', 'stamps `pid ts` and then `ns <inode>`', 'a free number outside', 'read from the stamping namespace is broken at once', 'skipped where it cannot']) assert.ok(said.includes(s), `the bullet says: ${s}`);
  assert.ok(pidns.includes('an initial-namespace writer\'s lock stamped with a dead pid and a fresh ts is left alone: the writer waits the bound out and refuses as held'), 'the child-namespace wait');
  assert.ok(pidns.includes('stamps "pid ts" and then "ns <inode>"; one in the initial namespace stamps "pid ts" alone'), 'the second line');
  assert.ok(pidns.includes('a child-namespace writer\'s live lock whose pid is a free number here is left alone by a writer in the initial namespace'), 'the host\'s direction');
  assert.ok(pidns.includes('the pid is judged in the namespace that stamped it: read from that namespace a dead pid\'s lock is broken at once; read from a third namespace it is waited out'), 'the stamping namespace');
  assert.ok(pidns.includes('a stamp past the stale bound is still broken, whatever its pid'), 'the age rule there');
  assert.ok(pidns.includes('in the initial pid namespace the dead pid\'s lock is broken at once'), 'the initial namespace');
  assert.ok(pidns.includes('a real child pid namespace: track-comment against a lock a live process outside holds') && pidns.includes('t.skip(`no unprivileged child pid namespace here'), 'the real namespace, skipped where none can be made');

  const row = read('tools', 'README-track-changents-patch-0008-row.test.mjs');
  said = about('tools/README-track-changents-patch-0008-row.test.mjs');
  for (const s of ['no third', 'store-io\'s make and remove sites', 'one set of names']) assert.ok(said.includes(s), `the bullet says: ${s}`);
  assert.ok(row.includes("test('the row names both names the lock leaves, as store-io defines them, and no third'"), 'the names case');
  assert.ok(row.includes("test('the row names the handover line as store-io writes it, whose file it lands in, and the folder it hands over'"), 'the folder case');
  assert.ok(row.includes("test('the row, the patch header and the ADR bullet list one set of names and the one line'"), 'the three records');
  assert.ok(row.includes("read('vendor', 'track-changents', 'README.md')") && row.includes("constant('STORE_LOCK_SUFFIX')"), 'read from the README and store-io\'s constants');

  const clock = src('tools', 'store-io-lock-clock.test.mjs');
  assert.ok(d49.includes('`tools/store-io-lock-clock.test.mjs` drives that: a lock stamped `1 <an hour ahead>` is broken at once'));
  assert.ok(clock.includes('a lock stamped "1 <an hour ahead>" is broken at once, pid 1 alive to every reader or not'), 'the hour-ahead case');
  assert.ok(clock.includes('stamped five seconds ahead it is a live writer\'s and waited out'), 'the five-seconds case');
  assert.ok(clock.includes('a stampless lock whose mtime is an hour ahead is broken at once'), 'the stampless case');
  assert.ok(clock.includes('a dead breaker\'s claim stamped an hour ahead beside a dead lock is removed and the break proceeds'), 'the claim');
  assert.ok(clock.includes('lands its comment and exits 0 in well under the wait, the lock gone'), 'the real CLI');

  const fence = read('ui', 'webview', 'file-comments-busy-retry-fence.test.ts');
  said = about(FENCE);
  for (const s of ['the same fence', '`store-moved`', 'the contrast', '`MOVED`', '`saveThroughComments`']) assert.ok(said.includes(s), `the bullet says: ${s}`);
  assert.ok(fence.includes('retries once with the SAME fence'), 'the same-fence case');
  assert.ok(fence.includes('the contrast: a holder that finished in the gap before the re-read'), 'the contrast');
  assert.ok(fence.includes("the panel's comments at MOVED and on saveThroughComments say"), 'the source comments');
  assert.ok(d49.includes('`busy` arrives while the other writer still holds the lock'));
});

test('decision 49 and the Risks bullet state the pid rule as store-io keeps it: judged by a reader in the stamping namespace only, named on the stamp\'s second line, and a stamp judged by its distance from now either way', () => {
  assert.ok(d49.includes('a pid is judged only by a reader in the pid namespace that stamped it'));
  assert.ok(d49.includes('names its own on a second stamp line, `ns <inode>`'));
  assert.ok(d49.includes('named by the line\'s absence'));
  assert.ok(d49.includes('any other lock is judged by its stamp\'s age alone'));
  assert.ok(d49.includes('A stamp more than 15 s from the reader\'s clock in either direction is a dead writer\'s'));
  assert.ok(d49.includes('the lock serializes the writers of one machine'));
  assert.ok(risks.includes('Residual (decision 49): a lock names its writer\'s pid namespace only when that is not the initial one'));
  assert.ok(testsBullet.includes('a pid judged only by a reader in the namespace that stamped it, named on the stamp\'s second line from any but the initial one'));
  // the code
  assert.match(storeIo, /^const PROC_PID_INIT_INO = 0xEFFFFFFC;$/m, 'the initial namespace\'s inode');
  assert.ok(fn(storeIo, 'ownPidNamespace').includes("fs.readlinkSync('/proc/self/ns/pid')"), 'the reader\'s own namespace is read from /proc');
  assert.ok(fn(storeIo, 'ownPidNamespace').includes('ownNs = m ? Number(m[1]) : PROC_PID_INIT_INO;'), 'no /proc: the initial namespace');
  assert.ok(storeIo.includes("const STORE_LOCK_NS_RE = /^ns (\\d+)$/m;"), 'the second line\'s shape');
  assert.ok(fn(storeIo, 'lockStamp').includes("return `${process.pid} ${Date.now()}\\n${ns === PROC_PID_INIT_INO ? '' : `ns ${ns}\\n`}`;"), 'the stamp: pid ts, and the line from a child namespace only');
  assert.equal((storeIo.match(/fs\.writeFileSync\((?:fd|cfd), lockStamp\(\)\);/g) || []).length, 2, 'the lock and the claim are stamped by lockStamp');
  const stale = fn(storeIo, 'lockIsStale');
  assert.match(stale, /const ns = STORE_LOCK_NS_RE\.exec\(entry\.raw\);/, 'the lock\'s namespace line is read');
  assert.match(stale, /if \((?:writerNs|\(ns \? Number\(ns\[1\]\) : PROC_PID_INIT_INO\)) === ownPidNamespace\(\) && !pidAlive\(Number\(m\[1\]\)\)\) return true;/, 'the pid is judged only under the reader\'s own namespace');
  assert.ok(stale.includes('return Math.abs(now - Number(m[2])) > staleMs;'), 'the stamp is judged by its distance from now, behind or ahead');
  assert.ok(!/—/.test(risks.slice(risks.indexOf('Residual (decision 49)'), risks.indexOf('The Obsidian'))), 'no em dash in the residual');
});
