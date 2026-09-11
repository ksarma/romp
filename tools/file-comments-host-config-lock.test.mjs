// set-tracked writes the root's tracking list, `.trackchanges/config.json`, which every file under
// the root shares, so it takes config.json's lock rather than the sidecar's (plans/file-review.md,
// decision 49; underStoreLock in the host). The kernel runs every host verb on its own thread, so
// two toggles from two dashboards, on the same file or on two files under one root, both load the
// list and rename over it; before the lock the second rename dropped the first's entry. Against the
// real host, with the lock held by the test as a toggle holds it (an O_EXCL create of
// `config.json.lock` holding "pid ts"):
//   * a toggle waits for the release; the holder's write moved the "" fence, so it refuses
//     config-moved and the panel's one retry lands both entries, the reply's configMtimeNs the
//     disk's; a release with nothing written lets the toggle land after the wait;
//   * a lock held past store-io's wait refuses `busy`, nothing written and the holder's lock left
//     alone, with a line that names what the held lock guards: the tracking list of the root, since
//     the holder may be a toggle on a sibling file, and "writing <this file>" would be false;
//   * the config's lock and the sidecar's are independent: a comment on the same file lands at once
//     while config.json.lock is held;
//   * two toggles on two files under one root at once, in a loop: never both ok with an entry
//     missing (the lost update), and both entries on disk after the panel's retry.
// Same hermetic harness as file-comments-host-store-lock.test.mjs (the synthetic notes-api world
// under a scratch directory, FILE_COMMENTS_HOME for "~"); synthetic text only.
// Run: node --test tools/file-comments-host-config-lock.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

import { configPathFor, storePathFor, readConfig, STORE_LOCK_WAIT_MS } from '../vendor/track-changents/store-io.mjs';
import { statNs } from './file-comments-host.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST = path.join(REPO, 'tools', 'file-comments-host.mjs');
const FIX = path.join(REPO, 'tests', 'fixtures', 'file_comments');
const HOLD_MS = 300;

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-fc-host-config-lock-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

// <scratch>/wN/home/notes-api/.git/ the landmark; docs/report.md and docs/other.md two files under it
let worlds = 0;
function world() {
  const home = path.join(SCRATCH, `w${++worlds}`, 'home');
  const root = path.join(home, 'notes-api');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  fs.mkdirSync(path.join(root, 'docs'));
  fs.copyFileSync(path.join(FIX, 'report.md'), path.join(root, 'docs', 'report.md'));
  fs.copyFileSync(path.join(FIX, 'report.md'), path.join(root, 'docs', 'other.md'));
  const configPath = configPathFor(root);
  return {
    home, root, configPath,
    lockPath: `${configPath}.lock`,
    report: path.join(root, 'docs', 'report.md'),
    other: path.join(root, 'docs', 'other.md'),
  };
}

function env(w) {
  const e = { ...process.env, FILE_COMMENTS_HOME: w.home };
  delete e.TRACKCHANGES_ROOT;
  delete e.ROMP_SID;
  delete e.ROMP_SESSION_NAME;
  return e;
}

// The kernel's call of the host: the request on stdin, one JSON object back; `endedAt` is
// Date.now() at exit, for the "waited" assertions.
function host(w, req) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [HOST], { env: env(w) });
    let stdout = '';
    let stderr = '';
    child.stdout.setEncoding('utf8'); child.stdout.on('data', (c) => { stdout += c; });
    child.stderr.setEncoding('utf8'); child.stderr.on('data', (c) => { stderr += c; });
    child.on('error', reject);
    child.on('close', (code) => {
      let json = null;
      try { json = JSON.parse(stdout); } catch { json = null; }
      resolve({ code, stdout, stderr, json, endedAt: Date.now() });
    });
    child.stdin.end(JSON.stringify(req));
  });
}
function hostSync(w, req) {
  const r = spawnSync(process.execPath, [HOST], { input: JSON.stringify(req), encoding: 'utf8', env: env(w) });
  assert.equal(r.status, 0, `exit ${r.status}: ${r.stderr}`);
  let json = null;
  try { json = JSON.parse(r.stdout); } catch { json = null; }
  assert.ok(json, r.stdout);
  return json;
}
function status(w, file) {
  const j = hostSync(w, { verb: 'status', path: file, args: {} });
  assert.equal(j.ok, true, j.error);
  return j;
}
const toggleOn = (file, fence) => ({ verb: 'set-tracked', path: file, args: { on: true, scope: 'file' }, fence: { configMtimeNs: fence == null ? '' : fence } });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// A toggle mid-write: config.json's lock taken as withStoreLock takes it. `save(list)` lands a
// tracking list and releases, and says when it did; `release()` releases with nothing written.
function holdConfig(w) {
  fs.mkdirSync(path.dirname(w.configPath), { recursive: true });
  fs.writeFileSync(w.lockPath, `${process.pid} ${Date.now()}\n`, { flag: 'wx' });
  return {
    save(list) {
      fs.writeFileSync(w.configPath, JSON.stringify({ v: 2, tracked: list }, null, 2) + '\n');
      const savedAt = Date.now();
      fs.unlinkSync(w.lockPath);
      return savedAt;
    },
    release() { try { fs.unlinkSync(w.lockPath); } catch { /* ignore */ } return Date.now(); },
  };
}

// ── the toggle waits ────────────────────────────────────────────────

test('set-tracked waits for a held config.json lock: the list the holder saves 300 ms later moves the fence, the toggle refuses config-moved, and the retry lands both entries', async () => {
  const w = world();
  const holder = holdConfig(w);
  let savedAt = 0;
  let r;
  try {
    const pending = host(w, toggleOn(w.report));
    await sleep(HOLD_MS);
    savedAt = holder.save(['docs/other.md']);
    r = await pending;
  } finally {
    holder.release();
  }
  assert.equal(r.code, 0, r.stderr);
  assert.ok(r.json, r.stdout);
  assert.ok(r.endedAt >= savedAt, `the toggle answered ${savedAt - r.endedAt} ms BEFORE the lock holder saved`);
  assert.equal(r.json.ok, false, r.stdout);
  assert.equal(r.json.code, 'config-moved', r.json.error);
  assert.match(r.json.error, /appeared on disk since you opened the file/);
  assert.deepEqual(readConfig(w.root), { v: 2, tracked: ['docs/other.md'] }, 'the holder\'s list stands, untouched');
  // the panel re-reads and retries once (MOVED)
  const st = status(w, w.report);
  assert.equal(st.configMtimeNs, statNs(w.configPath), 'the fresh fence');
  const retry = hostSync(w, toggleOn(w.report, st.configMtimeNs));
  assert.equal(retry.ok, true, retry.error);
  assert.deepEqual(readConfig(w.root), { v: 2, tracked: ['docs/other.md', 'docs/report.md'] }, 'both toggles survive');
  assert.deepEqual(retry.trackedBy, { kind: 'file', entry: 'docs/report.md' });
  assert.equal(retry.configMtimeNs, statNs(w.configPath), 'the reply\'s clock is the write\'s own');
  assert.equal(fs.existsSync(w.lockPath), false, 'the lock is released');
});

test('set-tracked waits for a held config.json lock and lands once it is released with nothing written', async () => {
  const w = world();
  const holder = holdConfig(w);
  let releasedAt = 0;
  let r;
  try {
    const pending = host(w, toggleOn(w.report));
    await sleep(HOLD_MS);
    releasedAt = holder.release();
    r = await pending;
  } finally {
    holder.release();
  }
  assert.equal(r.code, 0, r.stderr);
  assert.ok(r.json && r.json.ok === true, r.stdout + r.stderr);
  assert.ok(r.endedAt >= releasedAt, `the toggle answered ${releasedAt - r.endedAt} ms BEFORE the release`);
  assert.deepEqual(readConfig(w.root), { v: 2, tracked: ['docs/report.md'] });
  assert.equal(r.json.configMtimeNs, statNs(w.configPath));
  assert.equal(fs.existsSync(w.lockPath), false);
});

// ── the refusal, and the two locks apart ────────────────────────────

test('a config.json lock held past the wait: set-tracked refuses busy naming the root\'s tracking list, writes nothing and leaves the lock; a comment on the same file lands at once under the sidecar\'s own lock', async () => {
  const w = world();
  const holder = holdConfig(w);
  const startedAt = Date.now();
  let t;
  let c;
  try {
    [t, c] = await Promise.all([
      host(w, toggleOn(w.report)),
      host(w, { verb: 'comment', path: w.report, args: { note: 'Whole-file note.' }, fence: { storeMtimeNs: '' } }),
    ]);
    assert.equal(t.code, 0, t.stderr);
    assert.ok(t.endedAt - startedAt >= STORE_LOCK_WAIT_MS, 'the toggle waited out the bound before giving up');
    // Not "writing ~/notes-api/docs/report.md": nobody is; the holder of config.json's lock may be
    // a toggle on any file under the root.
    assert.deepEqual(t.json, { ok: false, code: 'busy', error: 'another editor is changing which files under ~/notes-api are tracked; retry' });
    assert.equal(fs.existsSync(w.configPath), false, 'nothing was written');
    assert.ok(fs.existsSync(w.lockPath), 'a live holder\'s lock is never removed');
    assert.equal(c.code, 0, c.stderr);
    assert.ok(c.json && c.json.ok === true, c.stdout + c.stderr);
    assert.ok(c.endedAt - startedAt < STORE_LOCK_WAIT_MS, `the comment waited on the config's lock (${c.endedAt - startedAt} ms)`);
  } finally {
    holder.release();
  }
  const disk = JSON.parse(fs.readFileSync(storePathFor(w.root, w.report), 'utf8'));
  assert.deepEqual(disk.comments.map((x) => x.body), ['Whole-file note.'], 'the comment landed under the sidecar\'s lock');
  assert.equal(c.json.trackedBy, null, 'no tracking list was written');
});

test('a sidecar lock held past the wait still names the file: the comment refuses busy about the file, and a toggle on it lands under the config\'s lock', async () => {
  const w = world();
  const storePath = storePathFor(w.root, w.report);
  fs.mkdirSync(path.dirname(storePath), { recursive: true });
  fs.writeFileSync(`${storePath}.lock`, `${process.pid} ${Date.now()}\n`, { flag: 'wx' });
  try {
    const [c, t] = await Promise.all([
      host(w, { verb: 'comment', path: w.report, args: { note: 'Whole-file note.' }, fence: { storeMtimeNs: '' } }),
      host(w, toggleOn(w.report)),
    ]);
    assert.deepEqual(c.json, { ok: false, code: 'busy', error: 'another editor is writing ~/notes-api/docs/report.md; retry' });
    assert.ok(t.json && t.json.ok === true, t.stdout + t.stderr);
    assert.deepEqual(readConfig(w.root), { v: 2, tracked: ['docs/report.md'] });
    assert.equal(fs.existsSync(storePath), false);
  } finally {
    fs.unlinkSync(`${storePath}.lock`);
  }
});

// ── two toggles at once ─────────────────────────────────────────────

test('two host processes toggle two files under one root at once, in a loop: never both ok with an entry missing, and both entries are on disk after the retry', async () => {
  const ROUNDS = 8;
  const outcomes = new Set();
  for (let round = 0; round < ROUNDS; round++) {
    const w = world();
    const files = [w.report, w.other];
    const replies = await Promise.all(files.map((f) => host(w, toggleOn(f))));
    for (const r of replies) {
      assert.equal(r.code, 0, `round ${round}: exit ${r.code}: ${r.stderr}`);
      assert.ok(r.json, `round ${round}: ${r.stdout}`);
      if (r.json.ok) { outcomes.add('ok'); continue; }
      outcomes.add(r.json.code);
      assert.ok(r.json.code === 'config-moved' || r.json.code === 'busy', `round ${round}: refused ${r.json.code}: ${r.json.error}`);
    }
    const cfg = readConfig(w.root);
    if (replies.every((r) => r.json.ok)) {
      assert.deepEqual(cfg.tracked.slice().sort(), ['docs/other.md', 'docs/report.md'], `round ${round}: both answered ok and the list lost an entry (the lost update)`);
    }
    for (let i = 0; i < files.length; i++) {
      if (replies[i].json.ok) continue;
      const st = status(w, files[i]);
      const again = hostSync(w, toggleOn(files[i], st.configMtimeNs));
      assert.equal(again.ok, true, `round ${round}: the retry: ${again.error}`);
    }
    assert.deepEqual(readConfig(w.root).tracked.slice().sort(), ['docs/other.md', 'docs/report.md'], `round ${round}: both entries are on disk`);
    assert.equal(fs.existsSync(w.lockPath), false, `round ${round}: the lock is released`);
  }
  assert.ok(outcomes.has('ok'), `outcomes seen: ${[...outcomes].join(', ')}`);
});
