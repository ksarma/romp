// Symbolic-link pins for tools/file-comments-host.mjs (the Slice 2 review's two findings). The plan's
// Security posture says the host writes only the sidecar, the comments log, config.json and the
// commented file; the three names under `.trackchanges/` are derived from the file's path and never
// shown, and a checked-out repository can commit anything under them (the plan leaves committing
// `.trackchanges/` to the project). Before these pins, (1) appendLog was a bare appendFileSync, so a
// link committed at the log's name carried every accept's or reject's entry — the change's own
// oldText/newText — to wherever the link pointed; and (2) reject saved the sidecar with store-io's
// saveStore on its own path, whose fixed `<sidecar>.tmp` is opened with a plain 'w', so a link
// committed under THAT name had its target truncated and replaced with the sidecar's bytes and was
// then renamed onto the sidecar's name. Now every verb refuses `unreadable` when any of the three
// names, or `.trackchanges/` itself, is a link or otherwise not a regular file — before it reads
// through them and with nothing changed — the log is opened O_NOFOLLOW under that, and every temp
// the host creates takes a random name and O_EXCL, with the sidecar landing through a staged rename.
// Same hermetic harness as file-comments-host.test.mjs: the synthetic `notes-api` world under a
// scratch directory, the script driven as the kernel drives it, changes recorded by the real
// track-edit. The link targets are files in the scratch world standing in for anything outside
// the project; nothing here reads or writes a real dotfile.
// Run: node --test tools/file-comments-host-symlinks.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

import { storePathFor, fingerprintOf } from '../vendor/track-changents/store-io.mjs';
import { appendLog, readLog, logPathFor, statNs } from './file-comments-host.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST = path.join(REPO, 'tools', 'file-comments-host.mjs');
const VENDOR = path.join(REPO, 'vendor', 'track-changents');
const FIX = path.join(REPO, 'tests', 'fixtures', 'file_comments');

const SID = '11111111-2222-3333-4444-555555555555';
const OLD = 'cut p95 latency by 40%';
// A change whose text a shell would act on if the log line reached a startup file: the finding's shape.
const NEW = 'reduced p95 latency by 40% $(touch pwned)';
const VICTIM = '# victim: a file outside the project\n';
const LINK_RE = /symbolic link/;
const NOTHING_CHANGED_RE = /; nothing was changed$/;

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-fc-host-symlinks-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

// ── the world ───────────────────────────────────────────────────────
// <scratch>/wN/home/            FILE_COMMENTS_HOME
//   victim.rc                   what a committed link points at: two levels above .trackchanges/
//   notes-api/.git/             the landmark
//   notes-api/docs/report.md    the commented file
//   loose/report.md             a file with no landmark above it
let worlds = 0;
function world() {
  const home = path.join(SCRATCH, `w${++worlds}`, 'home');
  const root = path.join(home, 'notes-api');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  fs.mkdirSync(path.join(root, 'docs'));
  fs.copyFileSync(path.join(FIX, 'report.md'), path.join(root, 'docs', 'report.md'));
  const looseDir = path.join(home, 'loose');
  fs.mkdirSync(looseDir);
  fs.copyFileSync(path.join(FIX, 'report.md'), path.join(looseDir, 'report.md'));
  const victim = path.join(home, 'victim.rc');
  fs.writeFileSync(victim, VICTIM);
  const report = path.join(root, 'docs', 'report.md');
  const storePath = storePathFor(root, report);
  return {
    home, root, looseDir, victim, report, storePath,
    trackDir: path.dirname(storePath),
    logPath: logPathFor(storePath),
    configPath: path.join(root, '.trackchanges', 'config.json'),
    loose: path.join(looseDir, 'report.md'),
    text: fs.readFileSync(path.join(FIX, 'report.md'), 'utf8'),
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
function status(w, file) { return ok(w, { verb: 'status', path: file || w.report, args: {} }); }
function fenceFor(st) { return { storeMtimeNs: st.storeMtimeNs == null ? '' : st.storeMtimeNs }; }
function fileFenceFor(st) { return { ...fenceFor(st), fileMtimeNs: st.fileMtimeNs }; }
function configFenceFor(st) { return { configMtimeNs: st.configMtimeNs == null ? '' : st.configMtimeNs }; }

// The session's tracked edit, by the real CLI, then the status the panel would hold.
function edit(w, file, oldText, newText) {
  const r = spawnSync(process.execPath, [path.join(VENDOR, 'cli', 'track-edit.mjs'), '--file', file, '--old', oldText, '--new', newText],
    { encoding: 'utf8', env: env(w, { ROMP_SESSION_NAME: 'web', ROMP_SID: SID }) });
  assert.equal(r.status, 0, `track-edit failed: ${r.stderr}`);
  return status(w, file);
}

const bytes = (p) => { try { return fs.readFileSync(p); } catch { return null; } };
const listing = (dir) => { try { return fs.readdirSync(dir).sort(); } catch { return null; } };
const logSendArgs = { sid: SID, sessionName: 'web', comments: [], accepted: 0, rejected: 0, queued: false, watermark: null };
const logEditArgs = { summary: { bytesBefore: 1, bytesAfter: 2 } };
const wholeFileComment = { note: 'Please tighten the summary.' };

// Every request the panel can issue against the commented file, with the fences `st` holds.
function everyVerb(w, st) {
  return [
    { verb: 'status', path: w.report, args: {} },
    { verb: 'comment', path: w.report, args: wholeFileComment, fence: fenceFor(st) },
    { verb: 'accept-all', path: w.report, args: {}, fence: fenceFor(st) },
    { verb: 'reject-all', path: w.report, args: {}, fence: fileFenceFor(st) },
    { verb: 'set-tracked', path: w.report, args: { on: true, scope: 'file' }, fence: configFenceFor(st) },
    { verb: 'log-edit', path: w.report, args: logEditArgs },
    { verb: 'log-send', path: w.report, args: logSendArgs },
  ];
}

// The link is as planted: still a link, to the same target, and the target's bytes are as written.
function assertLinkIntact(link, target) {
  assert.ok(fs.lstatSync(link).isSymbolicLink(), `${link} is still a symbolic link`);
  assert.equal(fs.readlinkSync(link), target, 'the link still points where it did');
  assert.equal(fs.readFileSync(path.resolve(path.dirname(link), target), 'utf8'), VICTIM, 'the link\'s target is untouched');
}

// A refusal that named the entry, tilde-collapsed, and claims nothing changed — and never that an
// entry landed (log-edit and log-send answer `logged: false`; the decisions carry no flag at all).
function assertRefusalNames(r, w, shownEntry) {
  assert.match(r.error, LINK_RE);
  assert.ok(r.error.includes(shownEntry), `${r.error} names ${shownEntry}`);
  assert.ok(r.error.includes('~/notes-api/docs/report.md'), r.error);
  assert.equal(r.error.includes(w.home), false, 'the home path is tilde-collapsed');
  assert.match(r.error, NOTHING_CHANGED_RE);
  assert.notEqual(r.logged, true, 'refused before any append, so nothing claims to be recorded');
}

// ── (1) the comments log as a link ──────────────────────────────────

test('accept, accept-all, reject and reject-all refuse unreadable through a link at the log\'s name; the decision does not land and the target gets no line', () => {
  const cases = [
    ['accept', (w, st) => ({ verb: 'accept', path: w.report, args: { ids: [st.hunks[0].id] }, fence: fenceFor(st) }), 'absolute'],
    ['accept-all', (w, st) => ({ verb: 'accept-all', path: w.report, args: {}, fence: fenceFor(st) }), 'relative'],
    ['reject', (w, st) => ({ verb: 'reject', path: w.report, args: { ids: [st.hunks[0].id] }, fence: fileFenceFor(st) }), 'absolute'],
    ['reject-all', (w, st) => ({ verb: 'reject-all', path: w.report, args: {}, fence: fileFenceFor(st) }), 'relative'],
  ];
  for (const [verb, build, kind] of cases) {
    const w = world();
    const st = edit(w, w.report, OLD, NEW);
    assert.equal(st.hunks.length, 1);
    const fileText = fs.readFileSync(w.report, 'utf8');
    const sidecarBytes = bytes(w.storePath);
    const sidecarMtime = statNs(w.storePath);
    // The shape a git checkout produces is the relative one: `../../victim.rc` from .trackchanges/.
    const target = kind === 'absolute' ? w.victim : path.join('..', '..', 'victim.rc');
    fs.symlinkSync(target, w.logPath);
    const before = listing(w.trackDir);

    const r = refused(w, build(w, st), 'unreadable');
    assertRefusalNames(r, w, '~/notes-api/.trackchanges/docs%2Freport.md.comments-log.jsonl');
    assert.match(r.error, /comments log/);
    assertLinkIntact(w.logPath, target);
    assert.equal(fs.readFileSync(w.report, 'utf8'), fileText, `${verb}: the file is untouched`);
    assert.deepEqual(bytes(w.storePath), sidecarBytes, `${verb}: the sidecar is as it was`);
    assert.equal(statNs(w.storePath), sidecarMtime, `${verb}: never written and restored`);
    assert.deepEqual(listing(w.trackDir), before, `${verb}: no staged sidecar or temp left behind`);
    assert.deepEqual(listing(path.dirname(w.report)), ['report.md'], `${verb}: no file temp left beside the file`);
    assert.equal(fs.existsSync(path.join(w.home, 'pwned')), false);

    // Recoverable: with the link gone the same request lands, and the log's first line is the entry.
    fs.unlinkSync(w.logPath);
    const st2 = status(w);
    const r2 = ok(w, build(w, st2));
    assert.deepEqual(r2[verb.startsWith('accept') ? 'accepted' : 'rejected'], [st.hunks[0].id]);
    const lines = fs.readFileSync(w.logPath, 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l));
    assert.equal(lines.length, 1);
    assert.equal(lines[0].kind, verb.startsWith('accept') ? 'accept' : 'reject');
    assert.equal(lines[0].changes[0].newText, NEW);
    assert.equal(fs.readFileSync(w.victim, 'utf8'), VICTIM, 'the former target never got the line');
  }
});

test('log-send, log-edit and set-tracked refuse unreadable through a linked log with logged:false and nothing written; comment and status refuse before reading it', () => {
  const w = world();
  const st = edit(w, w.report, OLD, NEW);
  const sidecarBytes = bytes(w.storePath);
  fs.symlinkSync(w.victim, w.logPath);
  const before = listing(w.trackDir);

  const ls = refused(w, { verb: 'log-send', path: w.report, args: logSendArgs }, 'unreadable');
  assertRefusalNames(ls, w, '~/notes-api/.trackchanges/docs%2Freport.md.comments-log.jsonl');
  assert.equal(ls.logged, false);
  assert.doesNotMatch(ls.error, /recorded in the comments log/);
  const le = refused(w, { verb: 'log-edit', path: w.report, args: logEditArgs }, 'unreadable');
  assertRefusalNames(le, w, '~/notes-api/.trackchanges/docs%2Freport.md.comments-log.jsonl');
  assert.equal(le.logged, false);
  assert.doesNotMatch(le.error, /recorded in the comments log/);
  const tr = refused(w, { verb: 'set-tracked', path: w.report, args: { on: true, scope: 'file' }, fence: configFenceFor(st) }, 'unreadable');
  assertRefusalNames(tr, w, '~/notes-api/.trackchanges/docs%2Freport.md.comments-log.jsonl');
  assert.equal(fs.existsSync(w.configPath), false, 'set-tracked wrote no config.json before the refusal');
  const c = refused(w, { verb: 'comment', path: w.report, args: wholeFileComment, fence: fenceFor(st) }, 'unreadable');
  assertRefusalNames(c, w, '~/notes-api/.trackchanges/docs%2Freport.md.comments-log.jsonl');
  assert.deepEqual(bytes(w.storePath), sidecarBytes, 'the comment was not written');
  const s = refused(w, { verb: 'status', path: w.report, args: {} }, 'unreadable');
  assertRefusalNames(s, w, '~/notes-api/.trackchanges/docs%2Freport.md.comments-log.jsonl');

  assertLinkIntact(w.logPath, w.victim);
  assert.deepEqual(listing(w.trackDir), before, 'nothing else under .trackchanges/ changed');
});

// ── (2) a link where store-io's fixed temp name would go ────────────

test('reject, reject-all and comment never write through a link at <sidecar>.tmp: the decision lands, the link and its target are untouched', () => {
  const w = world();
  edit(w, w.report, OLD, NEW);
  const st = edit(w, w.report, 'shipping the cache in v1.2', 'shipping the cache in v1.3');
  assert.equal(st.hunks.length, 2);
  const planted = `${w.storePath}.tmp`;
  fs.symlinkSync(w.victim, planted);
  const [a, b] = st.hunks;

  // comment: withSidecar's write, the same saveStore route Slice 1 used.
  const c = ok(w, { verb: 'comment', path: w.report, args: wholeFileComment, fence: fenceFor(st) });
  assert.equal(c.store.comments.length, 1);
  assertLinkIntact(planted, w.victim);
  // reject by id, then reject-all: the two callers Slice 2 added behind the Reject button.
  const r1 = ok(w, { verb: 'reject', path: w.report, args: { ids: [a.id] }, fence: fileFenceFor(c) });
  assert.deepEqual(r1.rejected, [a.id]);
  assert.ok(fs.readFileSync(w.report, 'utf8').includes(OLD), 'the first change is undone');
  assertLinkIntact(planted, w.victim);
  const r2 = ok(w, { verb: 'reject-all', path: w.report, args: {}, fence: fileFenceFor(r1) });
  assert.deepEqual(r2.rejected, [b.id]);
  assert.equal(fs.readFileSync(w.report, 'utf8'), w.text, 'the fixture is back');
  assertLinkIntact(planted, w.victim);
  // The sidecar landed as a regular file each time (the comment keeps it), described against the new text.
  assert.ok(fs.lstatSync(w.storePath).isFile(), 'the sidecar is a regular file, not the renamed link');
  const disk = JSON.parse(fs.readFileSync(w.storePath, 'utf8'));
  assert.deepEqual(disk.suggestions, []);
  assert.equal(disk.comments.length, 1);
  assert.deepEqual(disk.fingerprint, fingerprintOf(w.text));
  // Nothing of the host's own staging remains: only the sidecar, the log, and the planted link.
  assert.deepEqual(listing(w.trackDir), [path.basename(w.storePath), path.basename(planted), path.basename(w.logPath)].sort());
  assert.equal(fs.existsSync(path.join(w.home, 'pwned')), false);
});

// ── (3) the sidecar or config.json as a link ────────────────────────

test('a link at the sidecar\'s name refuses unreadable on every verb: never read through as the sidecar, never followed, replaced or removed', () => {
  const w = world();
  // The target reads as a valid v3 sidecar with a pending change: if any verb read through the
  // link, status would show the change and a decision would act on it.
  const fake = {
    v: 3, path: 'docs/report.md', fingerprint: fingerprintOf(w.text),
    suggestions: [{ id: 'planted-1', kind: 'sub', from: 0, to: 0, oldText: '', newText: '', author: 'web', ts: 1 }],
    comments: [],
  };
  fs.mkdirSync(w.trackDir);
  const target = path.join(w.home, 'planted-sidecar.json');
  fs.writeFileSync(target, JSON.stringify(fake));
  fs.symlinkSync(target, w.storePath);
  const targetBytes = bytes(target);
  const st = { storeMtimeNs: statNs(target), fileMtimeNs: statNs(w.report), configMtimeNs: null };

  for (const req of everyVerb(w, st)) {
    const r = refused(w, req, 'unreadable');
    assert.match(r.error, LINK_RE, `${req.verb}: ${r.error}`);
    assert.ok(r.error.includes('~/notes-api/.trackchanges/docs%2Freport.md.json'), `${req.verb}: ${r.error}`);
    assert.match(r.error, /the comments for/);
    assert.match(r.error, NOTHING_CHANGED_RE);
    assert.notEqual(r.logged, true, `${req.verb}: nothing claims to be recorded`);
  }
  assert.ok(fs.lstatSync(w.storePath).isSymbolicLink());
  assert.equal(fs.readlinkSync(w.storePath), target);
  assert.deepEqual(bytes(target), targetBytes, 'the target is untouched');
  assert.deepEqual(listing(w.trackDir), [path.basename(w.storePath)], 'no log, no config, no temp');
  assert.equal(fs.readFileSync(w.report, 'utf8'), w.text);
});

test('a link at config.json refuses unreadable on every verb and set-tracked writes nothing; a directory under any of the names refuses too', () => {
  const w = world();
  const st = edit(w, w.report, OLD, NEW);
  fs.symlinkSync(w.victim, w.configPath);
  const before = listing(w.trackDir);
  for (const req of everyVerb(w, st)) {
    const r = refused(w, req, 'unreadable');
    assert.match(r.error, LINK_RE, `${req.verb}: ${r.error}`);
    assert.ok(r.error.includes('~/notes-api/.trackchanges/config.json'), `${req.verb}: ${r.error}`);
    assert.match(r.error, /tracking list/);
  }
  assertLinkIntact(w.configPath, w.victim);
  assert.deepEqual(listing(w.trackDir), before);

  // Not a link but not a regular file either: a directory under the log's name.
  const w2 = world();
  const st2 = edit(w2, w2.report, OLD, NEW);
  fs.mkdirSync(w2.logPath);
  const r = refused(w2, { verb: 'accept-all', path: w2.report, args: {}, fence: fenceFor(st2) }, 'unreadable');
  assert.match(r.error, /is a directory, not a regular file/);
  assert.ok(r.error.includes('~/notes-api/.trackchanges/docs%2Freport.md.comments-log.jsonl'), r.error);
  assert.ok(fs.statSync(w2.logPath).isDirectory(), 'left in place');
  assert.deepEqual(fs.readdirSync(w2.logPath), []);
});

// ── (4) .trackchanges/ itself as a link ─────────────────────────────

test('.trackchanges/ as a link to a directory elsewhere refuses unreadable on every verb, and nothing lands in the link\'s target', () => {
  const w = world();
  const elsewhere = path.join(w.home, 'elsewhere');
  fs.mkdirSync(elsewhere);
  fs.symlinkSync(elsewhere, w.trackDir);
  const st = { storeMtimeNs: null, fileMtimeNs: statNs(w.report), configMtimeNs: null };
  for (const req of everyVerb(w, st)) {
    const r = refused(w, req, 'unreadable');
    assert.match(r.error, /comments folder/, `${req.verb}: ${r.error}`);
    assert.match(r.error, /is a symbolic link, not a directory/, `${req.verb}: ${r.error}`);
    assert.ok(r.error.includes('~/notes-api/.trackchanges'), r.error);
    assert.equal(r.error.includes(w.home), false);
    assert.match(r.error, NOTHING_CHANGED_RE);
  }
  assert.ok(fs.lstatSync(w.trackDir).isSymbolicLink(), 'the link is still there');
  assert.deepEqual(fs.readdirSync(elsewhere), [], 'the target directory received nothing');
  assert.equal(fs.readFileSync(w.report, 'utf8'), w.text);
});

test('a dangling .trackchanges link beside a loose file refuses the first comment, toggle and log-send, and is neither followed nor replaced', () => {
  const w = world();
  const mark = path.join(w.looseDir, '.trackchanges');
  const nowhere = path.join(w.home, 'nowhere');
  fs.symlinkSync(nowhere, mark);
  const st = status(w, w.loose);
  assert.equal(st.root, null, 'a link to nothing is no landmark');
  const reqs = [
    { verb: 'comment', path: w.loose, args: wholeFileComment, fence: { storeMtimeNs: '' } },
    { verb: 'set-tracked', path: w.loose, args: { on: true, scope: 'file' }, fence: { configMtimeNs: '' } },
    { verb: 'log-send', path: w.loose, args: logSendArgs },
  ];
  for (const req of reqs) {
    const r = refused(w, req, 'unreadable');
    assert.match(r.error, /comments folder/, `${req.verb}: ${r.error}`);
    assert.match(r.error, /already exists as a symbolic link to nothing/, `${req.verb}: ${r.error}`);
    assert.ok(r.error.includes('~/loose/.trackchanges'), r.error);
    assert.match(r.error, NOTHING_CHANGED_RE);
    if (req.verb === 'log-send') assert.equal(r.logged, false);
  }
  assert.ok(fs.lstatSync(mark).isSymbolicLink());
  assert.equal(fs.readlinkSync(mark), nowhere);
  assert.equal(fs.existsSync(nowhere), false, 'nothing was created where the link points');
  assert.deepEqual(listing(w.looseDir), ['.trackchanges', 'report.md']);
});

// ── the log's open, as a unit ───────────────────────────────────────

test('appendLog and readLog refuse a link, a directory and a FIFO at the log\'s path without following, writing, or blocking', (t) => {
  const dir = fs.mkdtempSync(path.join(SCRATCH, 'log-unit-'));
  const victim = path.join(dir, 'victim.rc');
  fs.writeFileSync(victim, VICTIM);
  const link = path.join(dir, 'linked.comments-log.jsonl');
  fs.symlinkSync(victim, link);
  assert.throws(() => appendLog(link, { kind: 'accept' }), LINK_RE);
  assert.throws(() => readLog(link), LINK_RE);
  assert.equal(fs.readFileSync(victim, 'utf8'), VICTIM);
  assert.ok(fs.lstatSync(link).isSymbolicLink());

  const asDir = path.join(dir, 'dir.comments-log.jsonl');
  fs.mkdirSync(asDir);
  assert.throws(() => appendLog(asDir, { kind: 'accept' }));
  assert.throws(() => readLog(asDir));
  assert.deepEqual(fs.readdirSync(asDir), []);

  // A regular file still appends and reads, and a missing one reads as empty and is created on append.
  const fresh = path.join(dir, 'fresh.comments-log.jsonl');
  assert.deepEqual(readLog(fresh), { entries: [], bad: 0 });
  appendLog(fresh, { kind: 'a' });
  appendLog(fresh, { kind: 'b' });
  assert.deepEqual(readLog(fresh).entries.map((e) => e.kind), ['a', 'b']);
  assert.ok(fs.lstatSync(fresh).isFile());

  const mkfifo = spawnSync('mkfifo', [path.join(dir, 'fifo.comments-log.jsonl')]);
  if (mkfifo.status !== 0) { t.diagnostic('mkfifo unavailable; the FIFO case is not exercised here'); return; }
  const fifo = path.join(dir, 'fifo.comments-log.jsonl');
  // No reader on the FIFO: a blocking open would hang here until killed; O_NONBLOCK returns at once.
  assert.throws(() => appendLog(fifo, { kind: 'accept' }));
  assert.throws(() => readLog(fifo), /not a regular file/);
});
