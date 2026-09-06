// The order a decision's writes land in, and what each failure or kill between them leaves behind
// (tools/file-comments-host.mjs, doAccept and doReject; plans/file-review.md, "The comments log"
// and "Consent, trace, routing"). The rule under test: a decision is recorded before it lands.
// Accept and reject each end in one rename that makes them true, and the log entry is appended
// before that rename, every other fallible step done earlier still — so a failed append refuses
// with nothing changed, and a kill after the append leaves the record. Before this order the
// append came last: a kill at the file rename left a rejected change's text in the file with no op
// and no record (indistinguishable from an accept), and a failed append after the sidecar landed
// left an accept that no record knew of, so the next send omitted it.
// Hermetic like the conformance suite: the synthetic `notes-api` world under a scratch directory,
// the host driven as the kernel drives it (a child process, one JSON request on stdin), every
// change recorded by the REAL track-edit. A kill or a failing rename is injected with a `--import`
// preload that patches fs.renameSync in the child for one destination path only.
// Run: node --test tools/file-comments-host-decisions.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';

import { storePathFor } from '../vendor/track-changents/store-io.mjs';
import { logPathFor, statNs } from './file-comments-host.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST = path.join(REPO, 'tools', 'file-comments-host.mjs');
const VENDOR = path.join(REPO, 'vendor', 'track-changents');
const FIX = path.join(REPO, 'tests', 'fixtures', 'file_comments');

const SID = '11111111-2222-3333-4444-555555555555';
const OLD = 'cut p95 latency by 40%';
const NEW = 'reduced p95 latency by 40%';
// Directory modes mean nothing to root, so the chmod-based cases skip there (as the conformance suite's do).
const notRoot = typeof process.getuid === 'function' && process.getuid() === 0 ? 'root ignores file modes' : false;

let SCRATCH;
let PRELOAD;
before(() => {
  SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-fc-host-decisions-'));
  // The fault injector: fs.renameSync patched on the module object the host and store-io share.
  // ROMP_FC_TEST_KILL_RENAME_TO — SIGKILL the child when a rename's destination is this path (the
  // kernel's deadline kill, landing exactly there); ROMP_FC_TEST_FAIL_RENAME_TO — throw EPERM
  // instead (a destination made immutable). Every other rename runs as written.
  PRELOAD = path.join(SCRATCH, 'rename-faults.mjs');
  fs.writeFileSync(PRELOAD, `
import fs from 'node:fs';
const kill = process.env.ROMP_FC_TEST_KILL_RENAME_TO || '';
const fail = process.env.ROMP_FC_TEST_FAIL_RENAME_TO || '';
const orig = fs.renameSync;
fs.renameSync = function (from, to) {
  if (kill && to === kill) process.kill(process.pid, 'SIGKILL');
  if (fail && to === fail) {
    const e = new Error(\`EPERM: operation not permitted, rename '\${from}' -> '\${to}'\`);
    e.code = 'EPERM';
    throw e;
  }
  return orig.call(fs, from, to);
};
`);
});
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

// ── the world (the conformance suite's, reduced to the commented file) ──
let worlds = 0;
function world() {
  const home = path.join(SCRATCH, `w${++worlds}`, 'home');
  const root = path.join(home, 'notes-api');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  fs.mkdirSync(path.join(root, 'docs'));
  fs.copyFileSync(path.join(FIX, 'report.md'), path.join(root, 'docs', 'report.md'));
  const report = path.join(root, 'docs', 'report.md');
  return {
    home, root, report,
    docs: path.dirname(report),
    real: fs.realpathSync(report),   // the host renames through the realpath; the faults key on it
    storePath: storePathFor(root, report),
    logPath: logPathFor(storePathFor(root, report)),
    text: fs.readFileSync(path.join(FIX, 'report.md'), 'utf8'),
  };
}

function env(w, extra) {
  const e = { ...process.env, FILE_COMMENTS_HOME: w.home, ...(extra || {}) };
  delete e.TRACKCHANGES_ROOT;
  if (!extra || !('ROMP_SID' in extra)) { delete e.ROMP_SID; delete e.ROMP_SESSION_NAME; }
  return e;
}

// The kernel's call, with an optional fault (env for the preload) — one JSON object back, or a kill.
function host(w, req, fault) {
  const argv = fault ? ['--import', pathToFileURL(PRELOAD).href, HOST] : [HOST];
  const r = spawnSync(process.execPath, argv, { input: JSON.stringify(req), encoding: 'utf8', env: env(w, fault) });
  let json = null;
  try { json = JSON.parse(r.stdout); } catch { json = null; }
  return { code: r.status, signal: r.signal, stdout: r.stdout, stderr: r.stderr, json };
}
function ok(w, req, fault) {
  const r = host(w, req, fault);
  assert.equal(r.code, 0, `exit ${r.code} (${r.signal}): ${r.stderr}`);
  assert.ok(r.json && r.json.ok === true, `expected ok:true, got ${r.stdout}`);
  return r.json;
}
function refused(w, req, code, fault) {
  const r = host(w, req, fault);
  assert.equal(r.code, 0, `a refusal exits 0; got ${r.code} (${r.signal}): ${r.stderr}`);
  assert.ok(r.json && r.json.ok === false, `expected ok:false, got ${r.stdout}`);
  assert.equal(r.json.code, code, r.json.error);
  return r.json;
}
function killed(w, req, fault) {
  const r = host(w, req, fault);
  assert.equal(r.signal, 'SIGKILL', `expected the child killed, got exit ${r.code}: ${r.stderr} ${r.stdout}`);
  assert.equal(r.stdout, '', 'a killed host answers nothing');
  return r;
}

// The session's tracked edit, by the real CLI, then the status the panel would hold.
function edit(w, oldText, newText) {
  const r = spawnSync(process.execPath, [path.join(VENDOR, 'cli', 'track-edit.mjs'), '--file', w.report, '--old', oldText, '--new', newText],
    { encoding: 'utf8', env: env(w, { ROMP_SESSION_NAME: 'web', ROMP_SID: SID }) });
  assert.equal(r.status, 0, `track-edit failed: ${r.stderr}`);
  return status(w);
}
function status(w) { return ok(w, { verb: 'status', path: w.report, args: {} }); }
function fenceFor(st) { return { storeMtimeNs: st.storeMtimeNs == null ? '' : st.storeMtimeNs }; }
function fileFenceFor(st) { return { ...fenceFor(st), fileMtimeNs: st.fileMtimeNs }; }
const rejectAllReq = (w, st) => ({ verb: 'reject-all', path: w.report, args: {}, fence: fileFenceFor(st) });
const acceptAllReq = (w, st) => ({ verb: 'accept-all', path: w.report, args: {}, fence: fenceFor(st) });

function readLogLines(lp) {
  return fs.readFileSync(lp, 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l));
}
const bytes = (p) => { try { return fs.readFileSync(p); } catch { return null; } };
const listing = (dir) => fs.readdirSync(dir).sort();
const changeOf = (h) => ({ id: h.id, oldText: h.oldText, newText: h.newText });
// A decision's log entry, as the conformance suite pins its shape: ts, kind, author, changes.
function decisionEntry(e, kind, hunks) {
  assert.deepEqual({ ...e, ts: 'T' }, { ts: 'T', kind, author: 'you', changes: hunks.map(changeOf) });
}

// ── the kill between the append and the last rename ─────────────────

test('reject appends the log entry before the file lands: killed at the file rename, the record survives beside the landed sidecar', () => {
  const w = world();
  const st = edit(w, OLD, NEW);
  const [h] = st.hunks;
  killed(w, rejectAllReq(w, st), { ROMP_FC_TEST_KILL_RENAME_TO: w.real });
  // The aftermath the order is for: the sidecar landed (no op), the file did not (its text still
  // holds the change) — and the log says a reject was asked for, with the change's texts.
  assert.equal(fs.readFileSync(w.report, 'utf8').includes(NEW), true, 'the file rename never ran');
  assert.deepEqual(JSON.parse(fs.readFileSync(w.storePath, 'utf8')).suggestions, [], 'the sidecar landed first');
  const lines = readLogLines(w.logPath);
  assert.equal(lines.length, 1);
  decisionEntry(lines[0], 'reject', [h]);
  // The next status shows the record: nothing pending, one reject to send, the entry in the Log.
  const s = status(w);
  assert.deepEqual(s.hunks, []);
  assert.equal(s.unsent.rejected, 1);
  assert.equal(s.log.length, 1);
  assert.equal(s.log[0].kind, 'reject');
});

test('accept appends the log entry before the sidecar lands: killed at the sidecar rename, the change stays pending and the record is visible', () => {
  const w = world();
  const st = edit(w, OLD, NEW);
  const [h] = st.hunks;
  const sidecarBytes = bytes(w.storePath);
  killed(w, acceptAllReq(w, st), { ROMP_FC_TEST_KILL_RENAME_TO: w.storePath });
  // Nothing landed under the sidecar's name; the staged bytes sit beside it under a non-.json name
  // the other hosts' scans skip; the log holds the asked-for decision.
  assert.deepEqual(bytes(w.storePath), sidecarBytes, 'the sidecar is as it was');
  const staged = listing(path.dirname(w.storePath)).filter((n) => n.includes('.romp-fc-'));
  assert.equal(staged.length, 1, `one staged sidecar left by the kill: ${staged}`);
  assert.equal(staged[0].endsWith('.json'), false);
  const lines = readLogLines(w.logPath);
  assert.equal(lines.length, 1);
  decisionEntry(lines[0], 'accept', [h]);
  // The next status reads through the leftover: the change is still pending and the Log says
  // accept — the person sees both, where the old order could leave a landed accept nobody recorded.
  const s = status(w);
  assert.equal(s.hunks.length, 1);
  assert.equal(s.hunks[0].id, h.id);
  assert.equal(s.unsent.accepted, 1);
  // Deciding again lands it; the log keeps the earlier entry too (it is never rewritten).
  const r = ok(w, acceptAllReq(w, s));
  assert.deepEqual(r.accepted, [h.id]);
  assert.equal(r.store, null, 'accept-all with no comments prunes the sidecar');
  assert.deepEqual(readLogLines(w.logPath).map((e) => e.kind), ['accept', 'accept']);
});

// ── a log that cannot be appended to ─────────────────────────────────

test('a reject whose log append fails puts the sidecar back, lands nothing, and refuses naming the log', { skip: notRoot }, () => {
  const w = world();
  const st = edit(w, OLD, NEW);
  const sidecarBytes = bytes(w.storePath);
  const fileText = fs.readFileSync(w.report, 'utf8');
  const docsListing = listing(w.docs);
  fs.writeFileSync(w.logPath, '');
  fs.chmodSync(w.logPath, 0o444);
  let r;
  try {
    r = refused(w, rejectAllReq(w, st), 'unreadable');
  } finally {
    fs.chmodSync(w.logPath, 0o644);
  }
  assert.match(r.error, /EACCES|EPERM/);
  assert.ok(r.error.includes('~/notes-api/.trackchanges/docs%2Freport.md.comments-log.jsonl'), r.error);
  assert.ok(r.error.includes('~/notes-api/docs/report.md'), r.error);
  assert.equal(r.error.includes(w.home), false);
  assert.match(r.error, /put back as it was and nothing was changed/);
  assert.equal('logged' in r, false, 'nothing was recorded, so the refusal carries no logged flag');
  assert.deepEqual(bytes(w.storePath), sidecarBytes, 'the prior sidecar bytes are back');
  assert.equal(fs.readFileSync(w.report, 'utf8'), fileText, 'the file is untouched');
  assert.deepEqual(listing(w.docs), docsListing, 'the staged file was discarded');
  assert.deepEqual(listing(path.dirname(w.storePath)), [path.basename(w.logPath), path.basename(w.storePath)].sort(), 'no restore temp left');
  assert.equal(fs.readFileSync(w.logPath, 'utf8'), '', 'the log is as it was');
  // The store is whole and nothing counts as decided; with the log writable again the reject lands.
  const s = status(w);
  assert.deepEqual(s.hunks, st.hunks);
  assert.equal(s.unsent.rejected, 0);
  const r2 = ok(w, rejectAllReq(w, s));
  assert.deepEqual(r2.rejected, [st.hunks[0].id]);
  assert.equal(fs.readFileSync(w.report, 'utf8'), w.text);
  assert.deepEqual(readLogLines(w.logPath).map((e) => e.kind), ['reject']);
});

test('an accept whose log append fails discards the staged sidecar and refuses with nothing changed', { skip: notRoot }, () => {
  const w = world();
  const st = edit(w, OLD, NEW);
  const sidecarBytes = bytes(w.storePath);
  fs.writeFileSync(w.logPath, '');
  fs.chmodSync(w.logPath, 0o444);
  let r;
  try {
    r = refused(w, acceptAllReq(w, st), 'unreadable');
  } finally {
    fs.chmodSync(w.logPath, 0o644);
  }
  assert.match(r.error, /EACCES|EPERM/);
  assert.ok(r.error.includes('~/notes-api/.trackchanges/docs%2Freport.md.comments-log.jsonl'), r.error);
  assert.equal(r.error.includes(w.home), false);
  assert.match(r.error, /; nothing was changed$/);
  assert.equal('logged' in r, false);
  assert.deepEqual(bytes(w.storePath), sidecarBytes, 'the sidecar is as it was: the change is still pending');
  assert.deepEqual(listing(path.dirname(w.storePath)), [path.basename(w.logPath), path.basename(w.storePath)].sort(), 'the staged sidecar was discarded');
  assert.equal(fs.readFileSync(w.logPath, 'utf8'), '');
  const s = status(w);
  assert.deepEqual(s.hunks, st.hunks);
  assert.equal(s.unsent.accepted, 0, 'no record, no count: the next send says nothing about it');
  const r2 = ok(w, acceptAllReq(w, s));
  assert.deepEqual(r2.accepted, [st.hunks[0].id]);
  assert.deepEqual(readLogLines(w.logPath).map((e) => e.kind), ['accept']);
});

// ── the last rename failing after the append ─────────────────────────

test('a reject whose file rename fails after the append puts the sidecar back and says the log already holds the decision', () => {
  const w = world();
  const st = edit(w, OLD, NEW);
  const [h] = st.hunks;
  const sidecarBytes = bytes(w.storePath);
  const fileText = fs.readFileSync(w.report, 'utf8');
  const docsListing = listing(w.docs);
  const r = refused(w, rejectAllReq(w, st), 'unreadable', { ROMP_FC_TEST_FAIL_RENAME_TO: w.real });
  assert.match(r.error, /EPERM/);
  assert.ok(r.error.includes('~/notes-api/docs/report.md'), r.error);
  assert.equal(r.error.includes(w.home), false);
  assert.match(r.error, /put back as it was, but the decision had already been recorded in the comments log/);
  assert.equal(r.logged, true, 'the refusal says the entry is there, the way log-edit and log-send do');
  assert.deepEqual(bytes(w.storePath), sidecarBytes, 'the prior sidecar bytes are back');
  assert.equal(fs.readFileSync(w.report, 'utf8'), fileText, 'the file is untouched');
  assert.deepEqual(listing(w.docs), docsListing, 'the staged file was discarded');
  const lines = readLogLines(w.logPath);
  assert.equal(lines.length, 1);
  decisionEntry(lines[0], 'reject', [h]);
  // What the refusal warned of: the change is pending again, and the log counts a reject.
  const s = status(w);
  assert.deepEqual(s.hunks, st.hunks);
  assert.equal(s.unsent.rejected, 1);
});

test('an accept whose sidecar rename fails after the append discards the stage and says the log already holds the decision', () => {
  const w = world();
  const st = edit(w, OLD, NEW);
  const [h] = st.hunks;
  const sidecarBytes = bytes(w.storePath);
  const r = refused(w, acceptAllReq(w, st), 'unreadable', { ROMP_FC_TEST_FAIL_RENAME_TO: w.storePath });
  assert.match(r.error, /EPERM/);
  assert.ok(r.error.includes('~/notes-api/.trackchanges/docs%2Freport.md.json'), r.error);
  assert.equal(r.error.includes(w.home), false);
  assert.match(r.error, /recorded in the comments log but did not land/);
  assert.equal(r.logged, true);
  assert.deepEqual(bytes(w.storePath), sidecarBytes, 'the sidecar is as it was');
  assert.deepEqual(listing(path.dirname(w.storePath)), [path.basename(w.logPath), path.basename(w.storePath)].sort(), 'the staged sidecar was discarded');
  const lines = readLogLines(w.logPath);
  assert.equal(lines.length, 1);
  decisionEntry(lines[0], 'accept', [h]);
  const s = status(w);
  assert.deepEqual(s.hunks, st.hunks);
  assert.equal(s.unsent.accepted, 1);
});

// ── the file that cannot be staged: before anything else ─────────────

test('a reject whose file cannot be staged refuses before the sidecar is touched: same bytes, same mtime, no log', { skip: notRoot }, () => {
  const w = world();
  const st = edit(w, OLD, NEW);
  const sidecarBytes = bytes(w.storePath);
  const sidecarMtime = statNs(w.storePath);
  fs.chmodSync(w.docs, 0o555);
  let r;
  try {
    r = refused(w, rejectAllReq(w, st), 'unreadable');
  } finally {
    fs.chmodSync(w.docs, 0o755);
  }
  assert.match(r.error, /EACCES|EPERM/);
  assert.match(r.error, /nothing was changed: the comments file was not touched, so there was nothing to put back/);
  assert.equal('logged' in r, false);
  assert.deepEqual(bytes(w.storePath), sidecarBytes);
  assert.equal(statNs(w.storePath), sidecarMtime, 'never written and restored: the panel\'s sidecar fence still holds');
  assert.equal(fs.existsSync(w.logPath), false);
  assert.deepEqual(listing(path.dirname(w.storePath)), [path.basename(w.storePath)]);
  // The fence the panel holds is still current, so the retry needs no reload.
  const r2 = ok(w, rejectAllReq(w, st));
  assert.deepEqual(r2.rejected, [st.hunks[0].id]);
  assert.equal(fs.readFileSync(w.report, 'utf8'), w.text);
});
