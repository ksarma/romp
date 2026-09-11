// The sidecar slice's records in plans/file-review.md (the Tests bullet under "The sidecar lock and the
// clocks", the panel section's Errors bullet, the Security posture's lock sentence and decision 49's
// break clause), held to the tree and the source on three gaps the slice's review found (2026-09-11,
// second round):
//   * the first round's commit added six test modules and its plan edit named one of them in the Tests
//     bullet, and the plan-sidecar pin read the bullet one way only (every module named is in the tree),
//     so five modules landed unrecorded. Held both ways here: every module the bullet names is in the
//     tree, and every test module under tools/, ui/webview/ or tests/ whose text cites decision 49 or 50
//     of this plan is named in the bullet, so a later round's module cannot land unrecorded.
//   * the panel section's Errors bullet listed three Reload codes while the panel's MOVED set and the
//     viewer's Save error offer Reload on `busy` too (and the panel on `figure-changed`, since Slice 3).
//     Held to the sets the code declares, read from the source, so a code added to either set and not to
//     the bullet fails here.
//   * the Security posture and decision 49 named `<name>.lock` as the one transient name while store-io's
//     breakers serialize on a second, `<name>.lock.break`, and hand the folder's removal over by a
//     `made-dir` line. Held to store-io's constants, so a suffix or a line the code adds or renames fails
//     here, and to the host's and the CLIs' handling of a lock that cannot be taken.
// Synthetic: only the repo's text.
// Run: node --test tools/file-review-plan-sidecar-records.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const SELF = 'tools/file-review-plan-sidecar-records.test.mjs';
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');

const plan = read('plans', 'file-review.md');
const host = read('tools', 'file-comments-host.mjs');
const storeIo = read('vendor', 'track-changents', 'store-io.mjs');
const panel = read('ui', 'webview', 'file-comments.ts');
const viewer = read('ui', 'webview', 'file-view.ts');

function between(doc, from, to) {
  const a = doc.indexOf(from);
  assert.ok(a >= 0, `${JSON.stringify(from)} not found`);
  const b = doc.indexOf(to, a + from.length);
  assert.ok(b > a, `${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return doc.slice(a, b).replace(/\s+/g, ' ');
}
const d49 = between(plan, '49. **One writer per sidecar at a time**', '50. **');
const testsBullet = between(plan, '- The sidecar lock and the clocks (2026-09-11, decisions 49 and 50)', '\n## Docs');
const errorsBullet = between(plan, '- **Errors** render inside the panel as an error row', '- **Click-safety**');
const security = between(plan, '\n## Security posture', '\n## Doctrines');

// The test modules a record names in backticks, as repo-relative paths (a bare ui name is under ui/webview/).
const testFiles = (s) => Array.from(s.matchAll(/`([^`\s]+\.(?:test\.ts|test\.mjs|py|bats))`/g), (m) => m[1])
  .map((n) => (n.includes('/') ? n : path.posix.join('ui', 'webview', n)));
// A record of this plan's decision 49 or 50: the number, and the plan's name somewhere in the file, so a
// module citing another document's forty-ninth decision is not swept in.
const CITES = /\bdecisions? (?:49|50)\b/;
const citing = (dir, re) => fs.readdirSync(path.join(REPO, ...dir)).filter((f) => re.test(f))
  .filter((f) => { const t = read(...dir, f); return CITES.test(t) && t.includes('file-review.md'); })
  .map((f) => path.posix.join(...dir, f));

// One constant's value as store-io defines it, so a rename there fails here and not silently.
function constant(name) {
  const m = new RegExp(`^const ${name} = '([^']+)';`, 'm').exec(storeIo);
  assert.ok(m, `store-io defines ${name}`);
  return m[1];
}
const LOCK = constant('STORE_LOCK_SUFFIX');
const BREAK = constant('STORE_LOCK_BREAK_SUFFIX');
const HANDOVER = constant('STORE_LOCK_HANDOVER');

// The five modules the review found unrecorded; the scan below reaches each (their headers cite the decision).
const UNRECORDED = ['tools/store-io-lock.test.mjs', 'tools/file-comments-host-config-lock.test.mjs',
  'tools/file-comments-host-landmark-race.test.mjs', 'tools/file-comments-host-read-under-lock.test.mjs',
  'ui/webview/file-comments-save-busy.test.ts'];

test('every module the Tests bullet names is in the tree, and every test module citing decision 49 or 50 is named in the bullet', () => {
  const named = new Set(testFiles(testsBullet));
  assert.ok(named.size >= 15, 'the bullet names the round\'s modules: ' + named.size);
  for (const f of named) assert.ok(fs.existsSync(path.join(REPO, f)), `${f} is named but not in the tree`);
  const all = [...citing(['tools'], /\.test\.mjs$/), ...citing(['ui', 'webview'], /\.test\.ts$/), ...citing(['tests'], /^test_\w+\.py$/)];
  for (const m of UNRECORDED) assert.ok(all.includes(m), `the scan reaches ${m}`);
  assert.ok(all.includes(SELF), 'and this module');
  assert.ok(all.length >= 12, 'the scan reaches the family: ' + all.length);
  for (const f of all) assert.ok(named.has(f), `${f} cites decision 49 or 50 but the Tests bullet names it nowhere`);
  assert.ok(testsBullet.includes('so a later round\'s module cannot land unrecorded'), 'the bullet says this pin holds the inventory both ways');
  assert.ok(testsBullet.includes(`\`${SELF}\` holds this bullet's inventory to the tree both ways`));
});

test('decision 49 names the round\'s modules too, each beside the behaviour it pins', () => {
  for (const m of UNRECORDED) assert.ok(d49.includes(`\`${m}\``), `decision 49 names ${m}`);
  assert.ok(d49.includes(`\`${SELF}\``), 'and this module');
  for (const m of testFiles(d49)) assert.ok(fs.existsSync(path.join(REPO, m)), `${m} is named by decision 49 but not in the tree`);
  // the modules the round added carry what the bullet says they pin
  assert.ok(read('tools', 'store-io-lock.test.mjs').includes('never hold together, and every one of them writes'), 'the one-winner break');
  assert.ok(read('tools', 'file-comments-host-config-lock.test.mjs').includes('tracking list, writes nothing and leaves the lock'), 'the config lock\'s busy line');
  assert.ok(read('tools', 'file-comments-host-landmark-race.test.mjs').includes('never unreadable, and the retry lands both'), 'the landmark race');
  assert.ok(read('tools', 'file-comments-host-read-under-lock.test.mjs').includes('waits and is placed in the text the edit left'), 'the file read under the lock');
  assert.ok(read('ui', 'webview', 'file-comments-save-busy.test.ts').includes('a second busy on the retry is not retried'), 'the save\'s one retry');
  assert.ok(d49.includes('a held `config.json` lock refuses `busy` naming the root\'s tracked list rather than the file'));
  assert.match(host, /if \(e\.held && lockedPath === configPathFor\(root\)\) throw new Refusal\('busy', `another editor is changing which files under \$\{tilde\(root\)\} are tracked; retry`\);/, 'the host\'s line for a held config lock');
});

test('the panel section\'s Errors bullet names every code the panel and the viewer offer Reload on, and no em dash', () => {
  const moved = /const MOVED = new Set\(\[([^\]]*)\]\);/.exec(panel);
  assert.ok(moved, 'the panel declares MOVED');
  const movedCodes = Array.from(moved[1].matchAll(/"([a-z-]+)"/g), (m) => m[1]);
  const figure = /const FIGURE_CHANGED = "([a-z-]+)";/.exec(panel);
  assert.ok(figure, 'the panel declares FIGURE_CHANGED');
  assert.match(panel, /reload: MOVED\.has\(e\.code\) \|\| e\.code === FIGURE_CHANGED \}/, 'the panel\'s row offers Reload on MOVED and on the figure code');
  const arm = /showSaveError\(err, ((?:code === "[a-z-]+"(?: \|\| )?)+)\);/.exec(viewer);
  assert.ok(arm, 'the viewer\'s save-failed arm offers Reload on a list of codes');
  const viewerCodes = Array.from(arm[1].matchAll(/"([a-z-]+)"/g), (m) => m[1]);
  assert.deepEqual([...viewerCodes].sort(), [...movedCodes].sort(), 'the viewer\'s Save error and the panel\'s MOVED set are the same codes');
  assert.ok(movedCodes.includes('busy'), 'busy is among them (decision 49)');
  for (const code of [...movedCodes, figure[1]]) assert.ok(errorsBullet.includes(`\`${code}\``), `the Errors bullet names \`${code}\``);
  assert.ok(errorsBullet.includes('since the sidecar lock (2026-09-11, decision 49), `busy` offer Reload, in the panel\'s row and in the viewer\'s Save error alike'));
  assert.ok(errorsBullet.includes(`and so does \`${figure[1]}\` in the panel's row (Slice 3; never retried)`));
  assert.ok(!/—/.test(errorsBullet), 'no em dash');
});

test('the Security posture names the two names the lock leaves and the one line, as store-io defines them, and no third', () => {
  const names = [LOCK, LOCK + BREAK];
  for (const n of names) assert.ok(security.includes(`\`<name>${n}\``), `the posture names \`<name>${n}\``);
  const listed = [...new Set(Array.from(security.matchAll(/`<name>(\.[\w.]+)`/g), (m) => m[1]))].sort();
  assert.deepEqual(listed, [...names].sort(), 'the posture lists exactly the names the code leaves');
  assert.match(storeIo, /^const STORE_LOCK_NAME_RE = \/\\\.lock\(\\\.break\)\?\$\/;$/m, 'store-io counts those two names and no other as the lock\'s');
  assert.ok(security.includes(`the one \`${HANDOVER}\` line`), 'the posture names the handover line');
  assert.ok(security.includes('are everything the lock leaves under `.trackchanges/`'), 'and claims the whole enumeration');
  assert.match(storeIo, /const claim = lockPath \+ STORE_LOCK_BREAK_SUFFIX;[\s\S]*?cfd = fs\.openSync\(claim, 'ax\+'\);/, 'the claim is created with O_EXCL, as the posture says (O_APPEND and readable like the lock, review round 2)');
  assert.ok(security.includes('a link or another non-file at the lock\'s name, or at the claim\'s while a stale lock stands, refuses the write as `unreadable`, never followed and never removed'));
  assert.match(storeIo, /if \(!st\.isFile\(\)\) throw new StoreLockError\(p, false\);/, 'a non-file at either name is refused, held false');
  assert.match(host, /throw new Refusal\('unreadable', `cannot lock \$\{ctx\.shown\} for writing: \$\{errText\(e\)\}; nothing was changed`\);/, 'which the host refuses unreadable');
  assert.ok(!/—/.test(between(plan, 'for the length of one write, the lock beside the sidecar', 'The mtime fences refuse and never merge.')), 'no em dash in the lock sentences');
});

test('decision 49 records the one-winner break, the conditional release and the handover, and store-io keeps them', () => {
  assert.ok(d49.includes('The break has one winner'));
  assert.ok(d49.includes(`\`<sidecar>${LOCK}${BREAK}\`, created with O_EXCL like the lock and holding the same \`pid ts\``));
  // lockStamp() since review round 4 (2026-09-11): the claim is stamped as the lock is, `pid ts` first
  assert.match(storeIo, /function breakStaleLock\(lockPath, staleMs\) \{[\s\S]*?fs\.writeFileSync\(cfd, lockStamp\(\)\);/, 'the claim holds the stamp the lock holds');
  assert.match(storeIo, /function lockStamp\(\) \{[\s\S]*?return `\$\{process\.pid\} \$\{Date\.now\(\)\}\\n/, 'which begins pid then ts');
  assert.ok(d49.includes('unlinks it only while it is still stale'));
  // since review round 2 (2026-09-11) the unlink is unlinkJudged: the lock goes only while the entry at the name is still
  // the inode judged stale, and only while the claim at its name is still this breaker's own
  assert.match(storeIo, /const entry = inspectLock\(lockPath\);\n\s*if \(entry && lockIsStale\(entry, staleMs, Date\.now\(\)\)\) \{[\s\S]*?if \(cur && sameInode\(cur\.st, mine\)\) \{\n\s*const held = unlinkJudged\(lockPath, entry\.st\);/, 'judged again under the claim, and unlinked only as the inode judged');
  assert.ok(d49.includes('a claim whose breaker is dead or whose stamp is past the bound is removed by the lock\'s own rule'));
  assert.match(storeIo, /const other = inspectLock\(claim\);\n\s*if \(other && lockIsStale\(other, staleMs, Date\.now\(\)\)\) \{/, 'the claim judged by lockIsStale');
  assert.ok(d49.includes('The release unlinks the lock only while the entry at the name is the holder\'s own inode'));
  assert.match(storeIo, /function unlinkOwn\(p, mine\) \{[\s\S]*?if \(!cur \|\| cur\.st\.ino !== mine\.ino \|\| cur\.st\.dev !== mine\.dev\) return null;/);
  assert.ok(d49.includes('a stamp that cannot be written after the create leaves no lock and no folder behind'));
  assert.ok(d49.includes(`by a \`${HANDOVER}\` line appended to its lock or claim`));
  assert.match(storeIo, /function handOverDir\(p\) \{[\s\S]*?fs\.writeFileSync\(fd, `\$\{STORE_LOCK_HANDOVER\}\\n`\)/, 'the line handOverDir appends');
  assert.ok(d49.includes('the host refuses `unreadable` naming it, the CLIs print its line and exit 1'));
  for (const cli of ['track-edit', 'track-comment', 'track-reply']) {
    assert.ok(read('vendor', 'track-changents', 'cli', `${cli}.mjs`).includes('if (e instanceof StoreLockError) fail(e.message);'), `${cli} prints the lock error's line`);
  }
  assert.ok(storeIo.includes('exists and is not a regular file, so the file cannot be locked for writing'), 'the line a non-file at either name gets');
  assert.ok(d49.includes('The two names and that line are everything the lock leaves under `.trackchanges/`'));
  assert.ok(!/—/.test(d49), 'no em dash');
});
