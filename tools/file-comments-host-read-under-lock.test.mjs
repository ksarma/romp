// The file is read under the sidecar's lock (plans/file-review.md, decision 49; withSidecar in the
// host). track-edit writes the sidecar and then the file, so between its two writes the disk holds
// a record whose text is not in the file yet; with the file read before the lock, a comment
// arriving in that window read the old text, waited for the edit's release, and then loaded the
// sidecar against text the record does not fit: an anchored comment on the edited passage refused
// `anchor-not-found` for text that IS in the file, a whole-file comment landed a sidecar stamped
// with the old text's fingerprint and a reply carrying the old file's clock, while the fence (the
// sidecar's mtime, which the panel's poll had refreshed in the window) matched and refused nothing.
// Read under the lock, the host sees the pair as the edit left it. Here the edit is the test itself,
// holding the lock as track-edit holds it (an O_EXCL create of `<sidecar>.lock` holding "pid ts"),
// recording the change through store-io's recordAgentEdit (the sidecar's rename), and writing the
// file 300 ms later, just before the release.
// Same hermetic harness as file-comments-host-store-lock.test.mjs (the synthetic notes-api world
// under a scratch directory, FILE_COMMENTS_HOME for "~"); synthetic ids and text only.
// Run: node --test tools/file-comments-host-read-under-lock.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';

import engine from '../vendor/track-changents/engine.js';
import { storePathFor, storeLockPathFor, recordAgentEdit } from '../vendor/track-changents/store-io.mjs';
import { statNs } from './file-comments-host.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST = path.join(REPO, 'tools', 'file-comments-host.mjs');
const FIX = path.join(REPO, 'tests', 'fixtures', 'file_comments');

const SID = '11111111-2222-3333-4444-555555555555';
const HOLD_MS = 300;
const OLD = 'cut p95 latency by 40%';
const NEW = 'reduced p95 latency by 35%';

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-fc-host-read-lock-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

let worlds = 0;
function world() {
  const home = path.join(SCRATCH, `w${++worlds}`, 'home');
  const root = path.join(home, 'notes-api');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  fs.mkdirSync(path.join(root, 'docs'));
  fs.copyFileSync(path.join(FIX, 'report.md'), path.join(root, 'docs', 'report.md'));
  const report = path.join(root, 'docs', 'report.md');
  return { home, root, report, text: fs.readFileSync(report, 'utf8'), storePath: storePathFor(root, report) };
}

function host(w, req) {
  return new Promise((resolve, reject) => {
    const env = { ...process.env, FILE_COMMENTS_HOME: w.home };
    delete env.TRACKCHANGES_ROOT;
    delete env.ROMP_SID;
    delete env.ROMP_SESSION_NAME;
    const child = spawn(process.execPath, [HOST], { env });
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
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const readSidecar = (sp) => JSON.parse(fs.readFileSync(sp, 'utf8'));

// track-edit's sequence, held open at the point between its two writes: the lock, the record (the
// sidecar's rename), and later the file's write and the release. Returns what a verb arriving in
// the window sees: the renamed sidecar's clock (the fence a poll in the window hands the panel) and
// the file's clock before the write.
function editHeldOpen(w) {
  const lockPath = storeLockPathFor(w.storePath);
  fs.mkdirSync(path.dirname(w.storePath), { recursive: true });
  fs.writeFileSync(lockPath, `${process.pid} ${Date.now()}\n`, { flag: 'wx' });
  const from = w.text.indexOf(OLD);
  assert.ok(from >= 0, 'the fixture holds the passage');
  const to = from + OLD.length;
  const newText = w.text.slice(0, from) + NEW + w.text.slice(to);
  recordAgentEdit(w.root, w.report, w.text, { from, to, insert: NEW }, 'api', Date.now(), SID);
  assert.equal(fs.readFileSync(w.report, 'utf8'), w.text, 'the record is on disk and the file is not yet written');
  return {
    from, newText,
    fence: { storeMtimeNs: statNs(w.storePath) },
    fileBefore: statNs(w.report),
    // the edit's second write and its release
    finish() {
      fs.writeFileSync(w.report, newText, 'utf8');
      const releasedAt = Date.now();
      fs.unlinkSync(lockPath);
      return releasedAt;
    },
    release() { try { fs.unlinkSync(lockPath); } catch { /* ignore */ } },
  };
}

test('a comment anchored on the edited passage, sent while a track-edit has renamed its sidecar and not yet written the file, waits and is placed in the text the edit left', async () => {
  const w = world();
  const edit = editHeldOpen(w);
  // the selection the person made in the panel, which shows the edit's text once its poll refreshed
  const anchor = engine.makeAnchor(edit.newText, edit.from, edit.from + NEW.length);
  let releasedAt = 0;
  let r;
  try {
    const pending = host(w, { verb: 'comment', path: w.report, args: { anchor, hintOffset: edit.from, note: 'Is 35% measured or estimated?' }, fence: edit.fence });
    await sleep(HOLD_MS);
    releasedAt = edit.finish();
    r = await pending;
  } finally {
    edit.release();
  }
  assert.equal(r.code, 0, r.stderr);
  assert.ok(r.json, r.stdout);
  assert.ok(r.endedAt >= releasedAt, `the host answered ${releasedAt - r.endedAt} ms BEFORE the edit's release`);
  assert.equal(r.json.ok, true, `${r.json.code}: ${r.json.error}`);
  const fileAfter = statNs(w.report);
  assert.notEqual(fileAfter, edit.fileBefore, 'the edit\'s write moved the file\'s clock');
  assert.equal(r.json.fileMtimeNs, fileAfter, 'the reply carries the file as the edit left it, not as it was before the lock');
  assert.equal(r.json.hunks.length, 1, 'the edit\'s change, placed');
  assert.equal(r.json.hunks[0].oldText, OLD);
  assert.equal(r.json.hunks[0].newText, NEW);
  assert.equal(r.json.store.comments.length, 1);
  assert.equal(r.json.store.comments[0].anchor.quote, NEW, 'the comment sits on the edited passage');
  const disk = readSidecar(w.storePath);
  assert.equal(disk.comments.length, 1);
  assert.equal(disk.comments[0].anchor.quote, NEW);
  assert.equal(disk.suggestions.length, 1, 'the edit\'s record stands beside the comment');
  assert.equal(disk.fingerprint.size, Buffer.byteLength(edit.newText), 'the sidecar is stamped with the text it was written against');
  assert.equal(fs.existsSync(storeLockPathFor(w.storePath)), false, 'the lock is released');
});

test('a whole-file comment sent in the same window carries the edited file\'s clock and stamps the sidecar with the edited text', async () => {
  const w = world();
  const edit = editHeldOpen(w);
  let releasedAt = 0;
  let r;
  try {
    const pending = host(w, { verb: 'comment', path: w.report, args: { note: 'Whole-file note.' }, fence: edit.fence });
    await sleep(HOLD_MS);
    releasedAt = edit.finish();
    r = await pending;
  } finally {
    edit.release();
  }
  assert.equal(r.code, 0, r.stderr);
  assert.ok(r.json && r.json.ok === true, r.stdout + r.stderr);
  assert.ok(r.endedAt >= releasedAt);
  assert.equal(r.json.fileMtimeNs, statNs(w.report), 'the file\'s clock is the edit\'s write');
  assert.equal(r.json.storeMtimeNs, statNs(w.storePath), 'the sidecar\'s clock is this write\'s own');
  assert.deepEqual(r.json.hunks.map((h) => [h.oldText, h.newText]), [[OLD, NEW]]);
  const disk = readSidecar(w.storePath);
  assert.deepEqual(disk.comments.map((c) => c.body), ['Whole-file note.']);
  assert.equal(disk.fingerprint.size, Buffer.byteLength(edit.newText), 'not the old text\'s size');
  assert.equal(fs.readFileSync(w.report, 'utf8'), edit.newText, 'the file is the edit\'s');
});
