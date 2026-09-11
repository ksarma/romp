// Decisions 49 and 50 (plans/file-review.md), the host paragraph's lock-and-clock sentence, the refusal
// codes list, the Vendoring paragraph's eighth-patch sentence, the Tests bullet and the ADR's lock bullet,
// held to the source and the tree: the constants the records quote are store-io's, the message they quote
// is the one the CLIs print and the host wraps, the verbs they list are the ones under the lock, the panel
// treats `busy` as the records say, the patch and its README row exist and say "not yet", and every test
// module the records name is in the tree. A record that names a bound the code no longer keeps, or a module
// that is not there, costs the next reader the search it was meant to save. Synthetic: only the repo's text.
// Run: node --test tools/file-review-plan-sidecar.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');
const exists = (...parts) => fs.existsSync(path.join(REPO, ...parts));

const plan = read('plans', 'file-review.md');
const adr = read('docs', 'adr', '0002-file-comments-in-the-track-changents-sidecar.md');
const host = read('tools', 'file-comments-host.mjs');
const storeIo = read('vendor', 'track-changents', 'store-io.mjs');
const panel = read('ui', 'webview', 'file-comments.ts');
const viewer = read('ui', 'webview', 'file-view.ts');
const readme = read('vendor', 'track-changents', 'README.md');
const { STORE_LOCK_WAIT_MS, STORE_LOCK_STALE_MS, withStoreLock, StoreLockError } = await import(path.join(REPO, 'vendor', 'track-changents', 'store-io.mjs'));

function between(doc, from, to) {
  const a = doc.indexOf(from);
  assert.ok(a >= 0, `${JSON.stringify(from)} not found`);
  const b = doc.indexOf(to, a + from.length);
  assert.ok(b > a, `${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return doc.slice(a, b).replace(/\s+/g, ' ');
}
const d49 = between(plan, '49. **One writer per sidecar at a time**', '50. **');
const d50 = between(plan, '50. **The clock a reply carries is taken before the read**', '\n## Open questions');
const hostPara = between(plan, '**The host script** (`tools/file-comments-host.mjs`', '**`fileCommentsSend`**');
const wire = between(plan, '## Kernel: two ops and a host script', '**The host script**');
const vendoring = between(plan, '### Vendoring', '### The comments log');
const risks = between(plan, '\n## Risks', '\n## Tests');
const security = between(plan, '\n## Security posture', '\n## Doctrines');
const tests = between(plan, '\n## Tests', '\n## Docs');
const testsBullet = between(plan, '- The sidecar lock and the clocks (2026-09-11, decisions 49 and 50)', '\n## Docs');
// one function's source: its `function name(` line to the next column-0 `}`
function fn(src, name) {
  let i = src.indexOf(`\nfunction ${name}(`);
  if (i < 0) i = src.indexOf(`\nexport function ${name}(`);
  assert.ok(i >= 0, `${name} is defined`);
  return src.slice(i, src.indexOf('\n}\n', i) + 3);
}

test('the two decisions date themselves, paraphrase the owner\'s yes, quote no one, and carry no em dash', () => {
  for (const [name, d] of [['49', d49], ['50', d50]]) {
    assert.ok(d.includes('(2026-09-11)'), `decision ${name} is dated`);
    assert.ok(/the user said yes/i.test(d), `decision ${name} paraphrases the yes`);
    assert.ok(!/"[^"]*\b(I|my|me)\b[^"]*"/.test(d), `decision ${name} quotes no utterance of the user's`);
    assert.ok(!/—/.test(d), `decision ${name} has no em dash`);
  }
  assert.ok(!/—/.test(testsBullet), 'nor the Tests bullet');
  assert.ok(!/—/.test(between(adr, '- Since 2026-09-11 one transient file', '- A romp-only field')), 'nor the ADR bullet');
});

test('decision 49 records the measurement and the fix, and its bounds are store-io\'s', () => {
  assert.ok(d49.includes('one write in five at a stagger of 4 to 20 ms'), 'the window measured');
  assert.ok(d49.includes('A stat before the rename narrows the window without closing it'));
  assert.ok(d49.includes('a lock in the host alone leaves the CLIs overwriting'));
  assert.ok(d49.includes('`withStoreLock(storePath, fn)`'));
  assert.equal(typeof withStoreLock, 'function');
  assert.equal(typeof StoreLockError, 'function');
  assert.ok(d49.includes('retries for up to 2 s'));
  assert.equal(STORE_LOCK_WAIT_MS, 2000, 'the wait the record quotes');
  assert.ok(d49.includes('older than 15 s'));
  assert.equal(STORE_LOCK_STALE_MS, 15000, 'the stale bound the record quotes');
  assert.ok(d49.includes('(the kernel kills a host at 10 s)'));
  assert.match(read('kernel', 'kernel.py'), /^_FILE_COMMENTS_TIMEOUT = 10\b/m, 'the kernel\'s deadline the bound is set against');
  assert.ok(d49.includes('holding `pid ts`'));
  assert.match(fn(storeIo, 'withStoreLock'), /fs\.writeFileSync\(fd, `\$\{process\.pid\} \$\{Date\.now\(\)\}\\n`\)/, 'the stamp is pid then ts');
  // 'ax+' since review round 2 (2026-09-11): still O_EXCL; O_APPEND so a maker's `made-dir` line put on the lock between
  // its create and its stamp keeps its place, and readable so the holder reads the line back through its own descriptor
  assert.match(fn(storeIo, 'withStoreLock'), /fs\.openSync\(lockPath, 'ax\+'\)/, 'O_EXCL');
  assert.match(fn(storeIo, 'withStoreLock'), /sleepMs\(2 \+ Math\.floor\(Math\.random\(\) \* 4\)\)/, '2 to 5 ms');
  assert.ok(d49.includes('unlinks it in `finally`'));
  // the release since review round 1 (2026-09-11): `finally` unlinks through unlinkOwn, which removes the entry at
  // the name only while it is still this holder's own inode, so a writer broken as stale never removes a breaker's lock
  assert.match(fn(storeIo, 'withStoreLock'), /\} finally \{\n    const held = unlinkOwn\(lockPath, mine\);/, 'the release is in finally');
  assert.match(fn(storeIo, 'withStoreLock'), /mine = fs\.fstatSync\(fd, \{ bigint: true \}\);/, 'the holder\'s identity is the open fd\'s inode');
  assert.match(fn(storeIo, 'unlinkOwn'), /if \(!cur \|\| cur\.st\.ino !== mine\.ino \|\| cur\.st\.dev !== mine\.dev\) return null;\n  try \{ fs\.unlinkSync\(p\); \}/, 'unlinkOwn unlinks, and only its own inode');
});

test('decision 49 names the CLIs\' message and behaviour, and the CLIs keep them', () => {
  assert.ok(d49.includes('print `another editor is writing this file; retry` and exit 1 with nothing written'));
  assert.ok(storeIo.includes("'another editor is writing this file; retry'"), 'the line is StoreLockError\'s');
  for (const cli of ['track-edit', 'track-comment', 'track-reply']) {
    const src = read('vendor', 'track-changents', 'cli', `${cli}.mjs`);
    assert.ok(/withStoreLock, StoreLockError,?\n?\s*\} from '\.\.\/store-io\.mjs'/.test(src) || /isNonTextPath, withStoreLock, StoreLockError,/.test(src), `${cli} imports the lock`);
    assert.ok(src.includes('withStoreLock(storePath, () =>'), `${cli} takes it`);
    assert.ok(src.includes('if (e instanceof StoreLockError) fail(e.message);'), `${cli} prints the one line on a held lock`);
    assert.ok(src.includes('class CliFailure extends Error {}') && src.includes('throw new CliFailure(msg);'), `${cli}'s fail() throws`);
    assert.ok(src.includes('if (!(e instanceof CliFailure)) throw e;') && src.includes('process.exit(1);'), `${cli}'s entry point prints and exits 1`);
  }
  assert.ok(d49.includes('`track-edit` from the file read through the file write and the edit turn it adds to the comment it answers'));
  const edit = read('vendor', 'track-changents', 'cli', 'track-edit.mjs');
  const locked = edit.slice(edit.indexOf('\nfunction editUnderLock('));
  for (const step of ['fs.readFileSync(abs)', 'recordAgentEdit(vaultRoot, abs, text', 'fs.writeFileSync(abs, res.text', 'addThreadEditTurn(vaultRoot, abs, args.thread']) {
    assert.ok(locked.includes(step), `track-edit's locked region holds ${step}`);
  }
});

test('decision 49 names the patch as not yet offered, and the patch and its README row say so', () => {
  assert.ok(d49.includes('vendor patch 0008, written as offerable to the engine\'s author and held back from the offer'));
  assert.ok(d49.includes('standing word of 2026-09-11 to open nothing new upstream'));
  const patches = fs.readdirSync(path.join(REPO, 'vendor', 'track-changents', 'patches')).filter((f) => f.startsWith('0008-'));
  assert.equal(patches.length, 1, 'one patch 0008');
  const header = read('vendor', 'track-changents', 'patches', patches[0]).split('\ndiff --git ')[0];
  assert.match(header, /^# Offered back: no \(not yet:/m, 'the header\'s not-yet');
  assert.match(header, /^# Files: store-io\.mjs, cli\/track-comment\.mjs, cli\/track-edit\.mjs, cli\/track-reply\.mjs$/m);
  const row = readme.split('\n').find((l) => l.startsWith(`| \`${patches[0]}\``));
  assert.ok(row, 'the README lists the patch');
  assert.match(row, /^\| `0008-[a-z0-9-]+\.patch` \| not yet \(/, 'the row says not yet');
  assert.ok(vendoring.includes('An eighth patch (2026-09-11) adds the per-sidecar lock to `store-io.mjs`'), 'the Vendoring paragraph');
  assert.ok(vendoring.includes('held back from the offer under the standing word of that day to open nothing new upstream'));
});

test('decision 49 lists the verbs under the lock and what set-tracked locks, and the host agrees', () => {
  assert.ok(d49.includes('the sidecar\'s for `comment`, `reply`, `resolve`, `retarget`, `accept`, `reject` and `save`; `config.json`\'s own for `set-tracked`'));
  assert.ok(host.includes('function underStoreLock(ctx, lockedPath, fn)'));
  assert.match(fn(host, 'withSidecar'), /return reply\(ctx, paths \? underStoreLock\(ctx, paths\.storePath, write\) : write\(\)\);/, 'comment, reply, resolve and retarget through withSidecar');
  assert.match(fn(host, 'decideUnderLock'), /paths \? underStoreLock\(ctx, paths\.storePath, run\) : run\(\)/, 'the decisions');
  for (const verb of ['doAccept', 'doReject', 'doSave']) assert.ok(fn(host, verb).includes('decideUnderLock(ctx,'), `${verb} decides under the lock`);
  assert.match(fn(host, 'doSetTracked'), /paths \? underStoreLock\(ctx, paths\.configPath, toggle\) : toggle\(\)/, 'set-tracked locks config.json');
  assert.ok(d49.includes('A loose file takes it after its landmark and checks its `""` fence again under it'));
  assert.match(fn(host, 'withSidecar'), /root = createLandmark\(ctx\);[\s\S]*underStoreLock\(ctx, paths\.storePath, \(\) => \{\n\s*requireFence\(ctx, 'storeMtimeNs', statNs\(paths\.storePath\), 'store-moved'/);
  assert.match(fn(host, 'doSetTracked'), /root = createLandmark\(ctx\);[\s\S]*underStoreLock\(ctx, paths\.configPath, \(\) => \{\n\s*requireFence\(ctx, 'configMtimeNs', statNs\(paths\.configPath\), 'config-moved'/);
  assert.ok(d49.includes('every reply is built after the release from a store read back under the lock'));
  assert.ok(!fn(host, 'decideUnderLock').includes('reply(ctx') || /const \[state, extra, opts\] = paths \? underStoreLock[\s\S]*\n  return reply\(ctx, state, extra, opts\);/.test(fn(host, 'decideUnderLock')), 'the reply after the release');
});

test('decision 49 says what refuses and how the panel takes it; the host and the panel agree', () => {
  assert.ok(d49.includes('A lock still held after the wait refuses `busy` with nothing changed'));
  assert.match(fn(host, 'underStoreLock'), /if \(e\.held\) throw new Refusal\('busy', `another editor is writing \$\{ctx\.shown\}; retry`\);/);
  assert.ok(d49.includes('the panel handles `busy` as it handles a moved fence (`MOVED`)'));
  assert.match(panel, /const MOVED = new Set\(\["store-moved", "file-moved", "config-moved", "busy"\]\);/);
  assert.match(panel, /if \(attempt === 0 && \(e\.code === "store-moved" \|\| e\.code === "config-moved" \|\| e\.code === "busy"\)\)/, 'the save\'s retry too');
  assert.match(viewer, /code === "store-moved" \|\| code === "file-moved" \|\| code === "config-moved" \|\| code === "busy"\);/, 'and the viewer\'s Reload offer');
  assert.ok(wire.includes('A moved fence refuses, as does `busy` (another writer held the host\'s lock past its wait, decision 49)'));
  assert.ok(wire.includes('`busy` (the lock on the sidecar, or on `config.json` for `set-tracked`, still held by another writer after the host\'s two-second wait; the client handles it as a moved fence, decision 49)'), 'the codes list');
  // the lock sentence, scoped to the eight verbs that rewrite a store since review round 1 (2026-09-11);
  // tools/file-review-plan-lock-verbs.test.mjs holds the same sentence to the host's verb table
  assert.ok(hostPara.includes('Every verb that rewrites the sidecar or `config.json` (`comment`, `reply`, `resolve`, `retarget`, `accept`, `reject` and `save` the sidecar; `set-tracked` the config) holds store-io\'s lock on the file it rewrites, from its fence stat through its last rename or prune'));
  assert.equal(hostPara.includes('Every verb that writes holds'), false, 'the over-claim is gone (`log-edit` and `log-send` append the comments log under no lock)');
  assert.ok(hostPara.includes('refuses `busy` when the lock is still held after two seconds'));
  assert.ok(hostPara.includes('every clock a reply carries (`storeMtimeNs`, `configMtimeNs`) is taken before the bytes it describes are read, never at reply time (decisions 49 and 50)'));
  assert.ok(risks.includes('one lock per sidecar, shared with the CLIs, that serializes the writers (decision 49)'));
  assert.ok(security.includes('for the length of one write, the lock beside the sidecar or the config (`<name>.lock`, decision 49), created with O_EXCL'));
});

test('decision 50 records the blind poll and the clock taken first, and the host keeps it', () => {
  assert.ok(d50.includes('blind to a write 11 times in 147 rounds'));
  assert.ok(d50.includes('a write landing between the two gave the panel the writer\'s clock over the earlier bytes'));
  assert.ok(d50.includes('`loadOrRefuse` and `loadFile` stat the sidecar first'));
  assert.match(fn(host, 'loadOrRefuse'), /^\nfunction loadOrRefuse\(ctx, paths, text\) \{\n  ctx\.storeClock = statNs\(paths\.storePath\);/);
  assert.match(fn(host, 'loadFile'), /if \(paths\) ctx\.storeClock = statNs\(paths\.storePath\);/);
  assert.ok(d50.includes('`configStatus` stats `config.json` first'));
  assert.match(fn(host, 'configStatus'), /^\nfunction configStatus\(ctx, paths\) \{\n  ctx\.configClock = statNs\(paths\.configPath\);/);
  assert.ok(d50.includes('a prune sets the sidecar\'s clock to null as of the prune'));
  assert.match(fn(host, 'afterDecision'), /ctx\.storeClock = null;/);
  assert.ok(d50.includes('`set-tracked` stamps the config\'s with its own write, under its lock'));
  assert.match(fn(host, 'doSetTracked'), /writeConfigAtomic\(root, entry, on\);\n\s*ctx\.configClock = statNs\(paths\.configPath\);/);
  assert.ok(d50.includes('The reply carries those clocks (`clockOf`) and stats nothing under `.trackchanges/`'));
  assert.equal(/statNs\(/.test(fn(host, 'reply')), false);
  assert.ok(d50.includes('a verb that reaches the reply without a clock is a program error, never a stat at reply time'));
  assert.match(fn(host, 'clockOf'), /throw new Error\(/);
  assert.ok(d50.includes('never newer than the bytes it was given'));
});

test('the Tests bullet and the two decisions name modules that are in the tree, and the ADR names the lock', () => {
  for (const m of ['tools/file-comments-host-store-lock.test.mjs', 'tools/file-comments-host-race.test.mjs', 'tools/file-comments-host-clocks.test.mjs',
    'tools/vendor-patches.test.mjs', 'ui/webview/file-comments-changes-review2.test.ts', 'tools/file-review-plan-sidecar.test.mjs']) {
    assert.ok(testsBullet.includes(`\`${m}\``), `the Tests bullet names ${m}`);
    assert.ok(exists(...m.split('/')), `${m} is in the tree`);
  }
  for (const m of ['tools/file-comments-host-store-lock.test.mjs', 'tools/file-comments-host-race.test.mjs', 'tools/vendor-patches.test.mjs',
    'ui/webview/file-comments-changes-review2.test.ts', 'tools/file-review-plan-sidecar.test.mjs']) assert.ok(d49.includes(`\`${m}\``), `decision 49 names ${m}`);
  assert.ok(d50.includes('`tools/file-comments-host-clocks.test.mjs`'));
  assert.ok(read('ui', 'webview', 'file-comments-changes-review2.test.ts').includes('Accept refused busy'), 'the panel case the records name');
  assert.ok(read('tools', 'vendor-patches.test.mjs').includes("test('P8 "), 'the P8 cases the records name');
  // the seam the race test uses: one read in the host, none in the kernel
  assert.equal((host.match(/process\.env\.FILE_COMMENTS_TEST_PAUSE_MS/g) || []).length, 1);
  assert.equal(read('kernel', 'kernel.py').includes('FILE_COMMENTS_TEST_PAUSE_MS'), false);
  assert.ok(d49.includes('`FILE_COMMENTS_TEST_PAUSE_MS`') && testsBullet.includes('`FILE_COMMENTS_TEST_PAUSE_MS`'));
  const bullet = between(adr, '- Since 2026-09-11 one transient file', '- A romp-only field');
  assert.ok(bullet.includes('`<name>.lock`'));
  assert.ok(bullet.includes('vendor patch 0008; decision 49 in `plans/file-review.md`'));
  assert.ok(bullet.includes('older than fifteen seconds'));
  assert.ok(tests.includes('The sidecar lock and the clocks'), 'the bullet is under Tests');
});
