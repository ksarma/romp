// Review pins for tools/file-comments-host.mjs (the Slice 1 file-review fixes): the `untracked` veto
// on set-tracked, the deferred file read behind `status`, a config.json that cannot be read, and the
// log verbs' refusals after an append. Same hermetic harness as file-comments-host.test.mjs: the
// synthetic `notes-api` world under a scratch directory, the script driven as the kernel drives it.
// Run: node --test tools/file-comments-host-review.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

import { storePathFor, readConfig, writeTrackedPaths } from '../vendor/track-changents/store-io.mjs';
import { statNs, logPathFor } from './file-comments-host.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST = path.join(REPO, 'tools', 'file-comments-host.mjs');
const VENDOR = path.join(REPO, 'vendor', 'track-changents');
const FIX = path.join(REPO, 'tests', 'fixtures', 'file_comments');

const SID = '11111111-2222-3333-4444-555555555555';
const NS_RE = /^\d+$/;
// One byte past V8's longest string (0x1fffffe8 characters): a file this size cannot become a
// string, so a verb that answers on it provably did not read it. Sparse, so it costs no disk.
const OVER_STRING_LIMIT = 0x20000000;

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-fc-host-review-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

let worlds = 0;
function world() {
  const home = path.join(SCRATCH, `w${++worlds}`, 'home');
  const root = path.join(home, 'notes-api');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  fs.mkdirSync(path.join(root, 'docs'));
  fs.copyFileSync(path.join(FIX, 'report.md'), path.join(root, 'docs', 'report.md'));
  fs.copyFileSync(path.join(FIX, 'index.md'), path.join(root, 'index.md'));
  const looseDir = path.join(home, 'loose');
  fs.mkdirSync(looseDir);
  fs.copyFileSync(path.join(FIX, 'report.md'), path.join(looseDir, 'report.md'));
  return {
    home, root, looseDir,
    report: path.join(root, 'docs', 'report.md'),
    index: path.join(root, 'index.md'),
    loose: path.join(looseDir, 'report.md'),
    cfg: path.join(root, '.trackchanges', 'config.json'),
  };
}

function env(w, extra) {
  const e = { ...process.env, FILE_COMMENTS_HOME: w.home, ...(extra || {}) };
  delete e.TRACKCHANGES_ROOT;
  if (!extra || !('ROMP_SID' in extra)) { delete e.ROMP_SID; delete e.ROMP_SESSION_NAME; }
  return e;
}
function host(w, req) {
  const r = spawnSync(process.execPath, [HOST], { input: JSON.stringify(req), encoding: 'utf8', env: env(w) });
  let json = null;
  try { json = JSON.parse(r.stdout); } catch { json = null; }
  return { code: r.status, stdout: r.stdout, stderr: r.stderr, json };
}
function ok(w, req) {
  const r = host(w, req);
  assert.equal(r.code, 0, `exit ${r.code}: ${r.stderr}`);
  assert.ok(r.json && r.json.ok === true, `expected ok:true, got ${r.stdout}`);
  assert.equal(r.json.verb, req.verb);
  return r.json;
}
function refused(w, req, code) {
  const r = host(w, req);
  assert.equal(r.code, 0, `a refusal exits 0; got ${r.code}: ${r.stderr}`);
  assert.ok(r.json && r.json.ok === false, `expected ok:false, got ${r.stdout}`);
  assert.equal(r.json.code, code, r.json.error);
  assert.equal(typeof r.json.error, 'string');
  return r.json;
}
function cli(w, name, args) {
  return spawnSync(process.execPath, [path.join(VENDOR, 'cli', `track-${name}.mjs`), ...args],
    { encoding: 'utf8', env: env(w, { ROMP_SESSION_NAME: 'web', ROMP_SID: SID }) });
}
function status(w, file, args) { return ok(w, { verb: 'status', path: file, args: args || {} }); }
function fenceFor(st) { return { storeMtimeNs: st.storeMtimeNs == null ? '' : st.storeMtimeNs }; }
function configFenceFor(st) { return { configMtimeNs: st.configMtimeNs == null ? '' : st.configMtimeNs }; }
function comment(w, file, st, args) { return ok(w, { verb: 'comment', path: file, args, fence: fenceFor(st) }); }
function writeConfig(w, text) {
  fs.mkdirSync(path.dirname(w.cfg), { recursive: true });
  fs.writeFileSync(w.cfg, typeof text === 'string' ? text : JSON.stringify(text) + '\n');
}
function fileBytes(p) { try { return fs.readFileSync(p); } catch { return null; } }
function readLogLines(lp) { return fs.readFileSync(lp, 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l)); }
const summary = () => ({ mtimeBeforeNs: '1', mtimeAfterNs: '2', bytesBefore: 10, bytesAfter: 12, diff: '@@ -1 +1 @@\n-a\n+b\n', truncated: false });
const sendArgs = () => ({ sid: SID, comments: [], accepted: 0, rejected: 0, queued: false, watermark: null });

// ── the untracked veto ──────────────────────────────────────────────

test('set-tracked on refuses tracked-vetoed for a file under an untracked entry, writes nothing, and names the entry to remove', () => {
  const w = world();
  writeConfig(w, { v: 2, tracked: [], untracked: ['docs/report.md'] });
  const bytes = fileBytes(w.cfg);
  const st = status(w, w.report);
  assert.equal(st.trackedBy, null);
  for (const scope of ['file', 'folder']) {
    const r = refused(w, { verb: 'set-tracked', path: w.report, args: { on: true, scope }, fence: configFenceFor(st) }, 'tracked-vetoed');
    assert.deepEqual(Object.keys(r).sort(), ['code', 'error', 'ok']);
    assert.ok(r.error.includes('~/notes-api/docs/report.md'), r.error);
    assert.ok(r.error.includes('"docs/report.md"'), r.error);
    assert.ok(r.error.includes('~/notes-api/.trackchanges/config.json'), r.error);
    assert.equal(r.error.includes(w.home), false);
  }
  assert.deepEqual(fileBytes(w.cfg), bytes, 'config.json is untouched');
  assert.deepEqual(readConfig(w.root), { v: 2, tracked: [], untracked: ['docs/report.md'] });
  assert.equal(fs.existsSync(logPathFor(storePathFor(w.root, w.report))), false, 'a refused toggle logs nothing');
  assert.equal(status(w, w.report).trackedBy, null);
  assert.equal(cli(w, 'config', ['--file', w.report]).status, 1, 'track-config still says off');
  // A folder veto covering the file refuses the same way and names the folder entry.
  writeConfig(w, { v: 2, tracked: [], untracked: ['docs/'] });
  const st2 = status(w, w.report);
  const r2 = refused(w, { verb: 'set-tracked', path: w.report, args: { on: true, scope: 'file' }, fence: configFenceFor(st2) }, 'tracked-vetoed');
  assert.ok(r2.error.includes('"docs/"'), r2.error);
  // With the veto gone the same request goes through.
  writeConfig(w, { v: 2, tracked: [] });
  const st3 = status(w, w.report);
  const r3 = ok(w, { verb: 'set-tracked', path: w.report, args: { on: true, scope: 'file' }, fence: configFenceFor(st3) });
  assert.deepEqual(r3.trackedBy, { kind: 'file', entry: 'docs/report.md' });
  assert.deepEqual(readConfig(w.root), { v: 2, tracked: ['docs/report.md'] });
  assert.equal(cli(w, 'config', ['--file', w.report]).stdout.trim(), 'on');
});

test('a veto elsewhere in the project does not refuse: the sibling under untracked stays off while the file tracks', () => {
  const w = world();
  writeConfig(w, { v: 2, tracked: [], untracked: ['docs/private/'] });
  const st = status(w, w.report);
  const r = ok(w, { verb: 'set-tracked', path: w.report, args: { on: true, scope: 'folder' }, fence: configFenceFor(st) });
  assert.deepEqual(r.trackedBy, { kind: 'folder', entry: 'docs/' });
  assert.deepEqual(readConfig(w.root), { v: 2, tracked: ['docs/'], untracked: ['docs/private/'] });
  const vetoed = path.join(w.root, 'docs', 'private', 'notes.md');
  fs.mkdirSync(path.dirname(vetoed));
  fs.writeFileSync(vetoed, '# Private\n');
  assert.equal(status(w, vetoed).trackedBy, null);
  const st2 = status(w, vetoed);
  refused(w, { verb: 'set-tracked', path: vetoed, args: { on: true, scope: 'file' }, fence: configFenceFor(st2) }, 'tracked-vetoed');
});

// ── the deferred read ───────────────────────────────────────────────

test('status, set-tracked and log-edit on a file above V8\'s string limit with no sidecar answer without reading it', () => {
  const w = world();
  const huge = path.join(w.root, 'docs', 'huge.log');
  fs.writeFileSync(huge, '');
  fs.truncateSync(huge, OVER_STRING_LIMIT);
  assert.equal(fs.statSync(huge).size, OVER_STRING_LIMIT);
  const st = status(w, huge);
  assert.equal(st.root, w.root);
  assert.equal(st.store, null);
  assert.equal(st.trackedBy, null);
  assert.match(st.fileMtimeNs, NS_RE);
  assert.equal(st.fileMtimeNs, fs.statSync(huge, { bigint: true }).mtimeNs.toString());
  assert.equal('baseline' in st, false);
  const r = ok(w, { verb: 'set-tracked', path: huge, args: { on: true, scope: 'file' }, fence: configFenceFor(st) });
  assert.deepEqual(r.trackedBy, { kind: 'file', entry: 'docs/huge.log' });
  assert.deepEqual(readConfig(w.root), { v: 2, tracked: ['docs/huge.log'] });
  const e = ok(w, { verb: 'log-edit', path: huge, args: { summary: summary() } });
  assert.equal(e.logged, true);
  assert.deepEqual(e.log.map((x) => x.kind), ['set-tracked', 'edit']);
  // The same file with no landmark above it: the null shape, still without a read.
  const looseHuge = path.join(w.looseDir, 'huge.log');
  fs.writeFileSync(looseHuge, '');
  fs.truncateSync(looseHuge, OVER_STRING_LIMIT);
  const s2 = status(w, looseHuge);
  assert.equal(s2.root, null);
  assert.equal(s2.store, null);
  assert.equal(fs.existsSync(path.join(w.looseDir, '.trackchanges')), false);
});

test('without a read, status still refuses unreadable for a missing file, a directory, and a file it may not open', () => {
  const w = world();
  const gone = refused(w, { verb: 'status', path: path.join(w.root, 'docs', 'gone.md') }, 'unreadable');
  assert.ok(/ENOENT/.test(gone.error) && gone.error.includes('~/notes-api/docs/gone.md'), gone.error);
  const dir = refused(w, { verb: 'status', path: path.join(w.root, 'docs') }, 'unreadable');
  assert.ok(dir.error.includes('~/notes-api/docs') && /not a regular file/.test(dir.error), dir.error);
  assert.equal(dir.error.includes(w.home), false);
  if (typeof process.getuid === 'function' && process.getuid() === 0) return;   // root reads anything
  const locked = path.join(w.root, 'docs', 'locked.md');
  fs.writeFileSync(locked, 'secret\n');
  fs.chmodSync(locked, 0o000);
  try {
    const r = refused(w, { verb: 'status', path: locked }, 'unreadable');
    assert.ok(/EACCES/.test(r.error) && r.error.includes('~/notes-api/docs/locked.md'), r.error);
    refused(w, { verb: 'set-tracked', path: locked, args: { on: true, scope: 'file' }, fence: { configMtimeNs: '' } }, 'unreadable');
    assert.equal(fs.existsSync(w.cfg), false, 'nothing written for a file that cannot be opened');
  } finally {
    fs.chmodSync(locked, 0o644);
  }
});

test('the read still happens when a sidecar exists: status re-places the sidecar against the current text', () => {
  const w = world();
  const st = status(w, w.report);
  const c = comment(w, w.report, st, { note: 'whole file' });
  assert.equal(c.store.comments.length, 1);
  fs.appendFileSync(w.report, '\nA new closing paragraph.\n');
  const s2 = status(w, w.report);
  assert.equal(s2.store.comments.length, 1, 'the sidecar was loaded (and rebased) against the file as it is now');
  assert.notEqual(s2.fileMtimeNs, st.fileMtimeNs);
  // Asking for the baseline reads the file even with no sidecar: the baseline is the text itself.
  const other = path.join(w.root, 'docs', 'other.md');
  fs.writeFileSync(other, 'Plain text.\n');
  assert.equal(status(w, other, { baseline: true }).baseline, 'Plain text.\n');
});

// ── a config.json that cannot be read ───────────────────────────────

const CONFLICTED = [
  '<<<<<<< HEAD',
  '{"v":2,"tracked":["docs/a.md"],"untracked":["docs/private/"]}',
  '=======',
  '{"v":2,"tracked":["docs/c.md"],"untracked":["docs/private/"]}',
  '>>>>>>> feature',
  '',
].join('\n');

test('a config.json with conflict markers refuses corrupt on every verb, names config.json, and is never rewritten', () => {
  const w = world();
  writeConfig(w, CONFLICTED);
  const bytes = fileBytes(w.cfg);
  const mt = statNs(w.cfg);
  const r = refused(w, { verb: 'status', path: w.report }, 'corrupt');
  assert.ok(r.error.includes('~/notes-api/.trackchanges/config.json'), r.error);
  assert.ok(r.error.includes('~/notes-api/docs/report.md'), r.error);
  assert.equal(r.error.includes(w.home), false);
  refused(w, { verb: 'status', path: w.index }, 'corrupt');
  // set-tracked on, with the fence the corrupt file's own mtime: refused, the file untouched.
  refused(w, { verb: 'set-tracked', path: w.report, args: { on: true, scope: 'file' }, fence: { configMtimeNs: mt } }, 'corrupt');
  refused(w, { verb: 'set-tracked', path: w.report, args: { on: true, scope: 'folder' }, fence: { configMtimeNs: mt } }, 'corrupt');
  refused(w, { verb: 'set-tracked', path: w.report, args: { on: false }, fence: { configMtimeNs: mt } }, 'corrupt');
  refused(w, { verb: 'comment', path: w.report, args: { note: 'x' }, fence: { storeMtimeNs: '' } }, 'corrupt');
  refused(w, { verb: 'reply', path: w.report, args: { commentId: '1', note: 'x' }, fence: { storeMtimeNs: '' } }, 'corrupt');
  refused(w, { verb: 'resolve', path: w.report, args: { commentId: '1', on: true }, fence: { storeMtimeNs: '' } }, 'corrupt');
  // log-edit on a file with no sidecar and no log cannot tell whether the file is tracked: refused, nothing logged.
  const le = refused(w, { verb: 'log-edit', path: w.report, args: { summary: summary() } }, 'corrupt');
  assert.equal(le.logged, false);
  assert.match(le.error, /nothing was changed$/);
  assert.deepEqual(fileBytes(w.cfg), bytes, 'the conflict markers are still there for a person to resolve');
  assert.deepEqual(fs.readdirSync(path.dirname(w.cfg)), ['config.json'], 'no sidecar, no log, no temp file');
});

test('log-edit and log-send under a corrupt config still record their entry for a file with a sidecar, and say so', () => {
  const w = world();
  const c = comment(w, w.report, status(w, w.report), { note: 'one' });
  const lp = logPathFor(c.storePath);
  writeConfig(w, CONFLICTED);
  const bytes = fileBytes(w.cfg);
  const le = refused(w, { verb: 'log-edit', path: w.report, args: { summary: summary() } }, 'corrupt');
  assert.equal(le.logged, true);
  assert.doesNotMatch(le.error, /nothing was changed/);
  assert.match(le.error, /the edit was recorded in the comments log$/);
  const ls = refused(w, { verb: 'log-send', path: w.report, args: sendArgs() }, 'corrupt');
  assert.equal(ls.logged, true);
  assert.match(ls.error, /the send was recorded in the comments log$/);
  assert.deepEqual(readLogLines(lp).map((e) => e.kind), ['edit', 'send']);
  assert.deepEqual(fileBytes(w.cfg), bytes);
});

test('an empty config.json and a non-array tracked list are corrupt; a newer version is unsupported-version; a missing list is nothing tracked', () => {
  const w = world();
  writeConfig(w, '');
  refused(w, { verb: 'status', path: w.report }, 'corrupt');
  writeConfig(w, '{"v":2,"tracked":"docs/a.md"}\n');
  refused(w, { verb: 'status', path: w.report }, 'corrupt');
  writeConfig(w, '{"v":2,"tracked":[],"untracked":"docs/private/"}\n');
  refused(w, { verb: 'status', path: w.report }, 'corrupt');
  writeConfig(w, '[]\n');
  refused(w, { verb: 'status', path: w.report }, 'corrupt');
  writeConfig(w, { v: 3, tracked: ['docs/a.md'], scopes: {} });
  const bytes = fileBytes(w.cfg);
  const r = refused(w, { verb: 'status', path: w.report }, 'unsupported-version');
  assert.ok(r.error.includes('~/notes-api/.trackchanges/config.json'), r.error);
  refused(w, { verb: 'set-tracked', path: w.report, args: { on: true, scope: 'file' }, fence: { configMtimeNs: statNs(w.cfg) } }, 'unsupported-version');
  assert.deepEqual(fileBytes(w.cfg), bytes, 'a v3 config is never downgraded to v2');
  // A readable config with no `tracked` list tracks nothing, as store-io reads it, and on writes the list.
  writeConfig(w, { v: 2 });
  const st = status(w, w.report);
  assert.equal(st.trackedBy, null);
  const on = ok(w, { verb: 'set-tracked', path: w.report, args: { on: true, scope: 'file' }, fence: configFenceFor(st) });
  assert.deepEqual(on.trackedBy, { kind: 'file', entry: 'docs/report.md' });
  assert.deepEqual(readConfig(w.root), { v: 2, tracked: ['docs/report.md'] });
});

test('an intact config keeps every entry across a toggle: the corrupt check refuses nothing that setTracked would have kept', () => {
  const w = world();
  writeTrackedPaths(w.root, ['docs/a.md']);
  writeConfig(w, { v: 2, tracked: ['docs/a.md'], untracked: ['docs/private/'] });
  const st = status(w, w.report);
  ok(w, { verb: 'set-tracked', path: w.report, args: { on: true, scope: 'file' }, fence: configFenceFor(st) });
  assert.deepEqual(readConfig(w.root), { v: 2, tracked: ['docs/a.md', 'docs/report.md'], untracked: ['docs/private/'] });
});

// ── log-send: the append and the refusal after it ───────────────────

test('log-send on a path with no landmark and no file refuses unreadable and creates nothing', () => {
  const w = world();
  const ghost = path.join(w.looseDir, 'ghost.md');
  const r = refused(w, { verb: 'log-send', path: ghost, args: sendArgs() }, 'unreadable');
  assert.equal(r.logged, false);
  assert.ok(/ENOENT/.test(r.error) && r.error.includes('~/loose/ghost.md'), r.error);
  assert.doesNotMatch(r.error, /recorded in the comments log/);
  assert.equal(fs.existsSync(path.join(w.looseDir, '.trackchanges')), false, 'no landmark beside a file that does not exist');
  assert.deepEqual(fs.readdirSync(w.looseDir), ['report.md']);
});

test('log-send on a file deleted under an existing root still records the send, and its refusal says so', () => {
  const w = world();
  const c = comment(w, w.report, status(w, w.report), { note: 'one' });
  const lp = logPathFor(c.storePath);
  fs.unlinkSync(w.report);
  const r = refused(w, { verb: 'log-send', path: w.report, args: { ...sendArgs(), comments: [{ id: c.store.comments[0].id, desc: 'on this file', body: 'one' }], watermark: c.store.comments[0].ts } }, 'unreadable');
  assert.equal(r.logged, true);
  assert.ok(/ENOENT/.test(r.error), r.error);
  assert.match(r.error, /the send was recorded in the comments log$/);
  const lines = readLogLines(lp);
  assert.equal(lines.length, 1);
  assert.equal(lines[0].kind, 'send');
  assert.equal(lines[0].watermark, c.store.comments[0].ts);
  assert.deepEqual(fs.readdirSync(path.dirname(lp)).sort(), [path.basename(c.storePath), path.basename(lp)].sort());
  // The file back in place: the send counts, so nothing is offered again.
  fs.copyFileSync(path.join(FIX, 'report.md'), w.report);
  assert.deepEqual(status(w, w.report).unsent.comments, []);
});

test('a refusal after a log append never claims nothing was changed; one before it still does', () => {
  const w = world();
  const sp = storePathFor(w.root, w.report);
  fs.mkdirSync(path.dirname(sp));
  fs.copyFileSync(path.join(FIX, 'sidecar-corrupt.txt'), sp);
  const st = refused(w, { verb: 'status', path: w.report }, 'corrupt');
  assert.match(st.error, /nothing was changed$/);
  const le = refused(w, { verb: 'log-edit', path: w.report, args: { summary: summary() } }, 'corrupt');
  assert.equal(le.logged, true);
  assert.doesNotMatch(le.error, /nothing was changed/);
  assert.match(le.error, /the edit was recorded in the comments log$/);
  const ls = refused(w, { verb: 'log-send', path: w.report, args: sendArgs() }, 'corrupt');
  assert.equal(ls.logged, true);
  assert.doesNotMatch(ls.error, /nothing was changed/);
  assert.match(ls.error, /the send was recorded in the comments log$/);
  assert.deepEqual(readLogLines(logPathFor(sp)).map((e) => e.kind), ['edit', 'send']);
  // log-edit on a file that has nothing: refused before any append, logged:false, the plain text.
  const other = path.join(w.root, 'docs', 'other.md');
  fs.writeFileSync(other, 'x\n');
  fs.copyFileSync(path.join(FIX, 'sidecar-corrupt.txt'), storePathFor(w.root, other));
  fs.unlinkSync(other);
  const r = refused(w, { verb: 'log-edit', path: other, args: { summary: summary() } }, 'unreadable');
  assert.equal(r.logged, true, 'a sidecar exists, so the edit is the log\'s business even with the file gone');
});
