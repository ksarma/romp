// A track-edit that lands inside a reject's write (plans/file-review.md, decision 49). reject stages
// the file, lands the sidecar, appends the log entry and then renames the staged file into place.
// A session's track-edit arriving between the sidecar's rename and the file's used to read the file
// as it still was, record its op into the sidecar the reject had just landed, and write the file;
// the reject's rename then landed the reject's text over it, so the session's text was gone from
// the file while its record stood in the sidecar (detached at the next load). With the sidecar's
// lock held by the reject from its load to that last rename, and taken by track-edit around its
// own read-to-write (vendor patch 0008), the edit waits for the rename and then reads the file
// the reject left: both the reject and the session's text and record land.
// The window is opened on purpose: FILE_COMMENTS_TEST_PAUSE_MS holds the host between the file's
// stage and its rename (pauseForTest, in commitFileWrite), inert unless set, and the kernel never
// sets it; the test watches the sidecar for the reject's write and starts track-edit then.
// Same hermetic harness as file-comments-host.test.mjs; synthetic ids and text only.
// Run: node --test tools/file-comments-host-race.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

import { storePathFor, loadStore } from '../vendor/track-changents/store-io.mjs';
import { logPathFor } from './file-comments-host.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST = path.join(REPO, 'tools', 'file-comments-host.mjs');
const VENDOR = path.join(REPO, 'vendor', 'track-changents');
const FIX = path.join(REPO, 'tests', 'fixtures', 'file_comments');

const SID_API = '11111111-2222-3333-4444-555555555555';
const SID_WEB = '66666666-7777-8888-9999-000000000000';
const PAUSE_MS = 1000;

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-fc-host-race-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

let worlds = 0;
function world() {
  const home = path.join(SCRATCH, `w${++worlds}`, 'home');
  const root = path.join(home, 'notes-api');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  fs.mkdirSync(path.join(root, 'docs'));
  fs.copyFileSync(path.join(FIX, 'report.md'), path.join(root, 'docs', 'report.md'));
  return { home, root, report: path.join(root, 'docs', 'report.md'), text: fs.readFileSync(path.join(FIX, 'report.md'), 'utf8') };
}

function env(w, extra) {
  const e = { ...process.env, FILE_COMMENTS_HOME: w.home };
  delete e.TRACKCHANGES_ROOT;
  delete e.FILE_COMMENTS_TEST_PAUSE_MS;   // only the reject under test is paused, by its own `extra`
  delete e.ROMP_SID;
  delete e.ROMP_SESSION_NAME;
  return { ...e, ...(extra || {}) };
}

function run(file, args, opts) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [file, ...args], { env: opts.env });
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
    if (opts.input != null) child.stdin.end(opts.input); else child.stdin.end();
  });
}
const host = (w, req, extra) => run(HOST, [], { input: JSON.stringify(req), env: env(w, extra) });
function cliSync(w, name, session, args) {
  const r = spawnSync(process.execPath, [path.join(VENDOR, 'cli', `track-${name}.mjs`), ...args],
    { encoding: 'utf8', env: env(w, session) });
  assert.equal(r.status, 0, `track-${name} failed: ${r.stderr}`);
  return r;
}
const cli = (w, name, session, args) => run(path.join(VENDOR, 'cli', `track-${name}.mjs`), args, { env: env(w, session) });
const API = { ROMP_SESSION_NAME: 'api', ROMP_SID: SID_API };
const WEB = { ROMP_SESSION_NAME: 'web', ROMP_SID: SID_WEB };
function status(w) {
  const r = spawnSync(process.execPath, [HOST], { input: JSON.stringify({ verb: 'status', path: w.report, args: {} }), encoding: 'utf8', env: env(w) });
  assert.equal(r.status, 0, r.stderr);
  const j = JSON.parse(r.stdout);
  assert.equal(j.ok, true, j.error);
  return j;
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const readSidecar = (sp) => JSON.parse(fs.readFileSync(sp, 'utf8'));

// Wait until the sidecar on disk holds no pending change (the reject's sidecar landed) while the
// file still holds the change's text (its rename has not): the host is inside the pause.
async function untilInsidePause(storePath, file, changeText) {
  const deadline = Date.now() + 5000;
  while (Date.now() < deadline) {
    let disk = null;
    try { disk = readSidecar(storePath); } catch { /* mid-rename */ }
    if (disk && disk.suggestions.length === 0) {
      assert.ok(fs.readFileSync(file, 'utf8').includes(changeText), 'the file still holds the change: the reject is between its sidecar\'s rename and its file\'s');
      return;
    }
    await sleep(5);
  }
  assert.fail('the reject never landed its sidecar');
}

test('a track-edit arriving between a reject\'s sidecar rename and its file rename waits for the lock; the reject and the session\'s text and record both land', async () => {
  const w = world();
  // the api session's change, pending
  cliSync(w, 'edit', API, ['--file', w.report, '--old', 'cut p95 latency by 40%', '--new', 'reduced p95 latency by 35%']);
  const storePath = storePathFor(w.root, w.report);
  const st = status(w);
  assert.equal(st.hunks.length, 1);
  const changeId = st.hunks[0].id;
  const fence = { storeMtimeNs: st.storeMtimeNs, fileMtimeNs: st.fileMtimeNs };
  // the reject, held between its two renames
  const rejecting = host(w, { verb: 'reject-all', path: w.report, args: {}, fence }, { FILE_COMMENTS_TEST_PAUSE_MS: String(PAUSE_MS) });
  await untilInsidePause(storePath, w.report, 'reduced p95 latency by 35%');
  const editStarted = Date.now();
  // the web session edits another passage now
  const editing = cli(w, 'edit', WEB, ['--file', w.report, '--old', 'shipping the cache in v1.2', '--new', 'shipping the cache in v1.3']);
  const [rej, edit] = await Promise.all([rejecting, editing]);
  assert.equal(rej.code, 0, rej.stderr);
  assert.ok(rej.json && rej.json.ok === true, rej.stdout + rej.stderr);
  assert.deepEqual(rej.json.rejected, [changeId]);
  assert.equal(edit.code, 0, edit.stderr);
  assert.equal(edit.stdout, 'Tracked edit applied.\n');
  // The file: the reject restored the api session's passage, and the web session's edit is in it.
  const text = fs.readFileSync(w.report, 'utf8');
  assert.ok(text.includes('cut p95 latency by 40%'), 'the reject landed');
  assert.ok(!text.includes('reduced p95 latency by 35%'));
  assert.ok(text.includes('shipping the cache in v1.3'), 'the session\'s text landed and stayed (the reject\'s rename erased it before the lock)');
  assert.equal(text, w.text.replace('shipping the cache in v1.2', 'shipping the cache in v1.3'));
  // The edit waited for the lock the paused reject held, and not past it: the pause began at most
  // a poll before the edit started, so the edit ran at least the rest of it.
  assert.ok(edit.endedAt - editStarted >= PAUSE_MS - 50, `the edit did not wait for the reject's rename (it took ${edit.endedAt - editStarted} ms of a ${PAUSE_MS} ms pause)`);
  assert.ok(edit.endedAt - editStarted < PAUSE_MS + 2000, 'and did not wait out the lock');
  // The sidecar: the web session's record, live against the file (not detached), and no other.
  const disk = readSidecar(storePath);
  assert.equal(disk.suggestions.length, 1);
  assert.equal(disk.suggestions[0].author, 'web');
  assert.equal(disk.suggestions[0].authorId, SID_WEB);
  assert.equal(disk.suggestions[0].newText, 'shipping the cache in v1.3');
  const loaded = loadStore(storePath, text);
  assert.equal(loaded.suggestions.length, 1, 'the record places in the file as written');
  assert.deepEqual(loaded.detached, []);
  const after = status(w);
  assert.equal(after.hunks.length, 1);
  assert.equal(after.hunks[0].author, 'web');
  assert.equal(text.slice(after.hunks[0].curFrom, after.hunks[0].curTo), 'shipping the cache in v1.3');
  // The log: the reject's entry.
  assert.deepEqual(fs.readFileSync(logPathFor(storePath), 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l).kind), ['reject']);
});

test('the pause is a test seam: read from FILE_COMMENTS_TEST_PAUSE_MS alone at the file\'s rename, returning at once when it is unset, and the kernel never sets it', () => {
  const src = fs.readFileSync(HOST, 'utf8');
  const fn = (name) => {
    const i = src.indexOf(`\nfunction ${name}(`);
    assert.ok(i >= 0, name);
    const j = src.indexOf('\n}\n', i);
    return src.slice(i, j + 3);
  };
  assert.match(fn('commitFileWrite'), /pauseForTest\(\);\n  fs\.renameSync\(prepared\.tmp, prepared\.real\);/, 'the pause sits before the rename that lands the file');
  const pause = fn('pauseForTest');
  assert.match(pause, /process\.env\.FILE_COMMENTS_TEST_PAUSE_MS/);
  assert.match(pause, /if \(v == null \|\| v === ''\) return;/, 'unset: inert');
  assert.equal((src.match(/process\.env\.FILE_COMMENTS_TEST_PAUSE_MS/g) || []).length, 1, 'read in one place');
  const kernel = fs.readFileSync(path.join(REPO, 'kernel', 'kernel.py'), 'utf8');
  assert.equal(kernel.includes('FILE_COMMENTS_TEST_PAUSE_MS'), false, 'the kernel never sets it');
});
