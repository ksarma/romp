// Disk-state pins for tools/file-comments-host.mjs (the Slice 1 review round 2 fixes): a refused
// `set-tracked` or `comment` on a loose file creates no `.trackchanges/` landmark (decision 37 ties
// the landmark to the first comment or tracking toggle, and a refused one is neither), and
// `set-tracked` replaces config.json by temp-and-rename with the bytes the vendored writer produces,
// never truncating it in place. Same hermetic harness as file-comments-host.test.mjs: the synthetic
// `notes-api` world under a scratch directory, the script driven as the kernel drives it.
// Run: node --test tools/file-comments-host-disk.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

import { storePathFor, readConfig, writeTrackedPaths, setTracked } from '../vendor/track-changents/store-io.mjs';
import { logPathFor } from './file-comments-host.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST = path.join(REPO, 'tools', 'file-comments-host.mjs');
const VENDOR = path.join(REPO, 'vendor', 'track-changents');
const FIX = path.join(REPO, 'tests', 'fixtures', 'file_comments');
const engine = createRequire(import.meta.url)(path.join(VENDOR, 'engine.js'));

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-fc-host-disk-')); });
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
    text: fs.readFileSync(path.join(FIX, 'report.md'), 'utf8'),
  };
}

function env(w) {
  const e = { ...process.env, FILE_COMMENTS_HOME: w.home };
  delete e.TRACKCHANGES_ROOT;
  delete e.ROMP_SID;
  delete e.ROMP_SESSION_NAME;
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
function status(w, file) { return ok(w, { verb: 'status', path: file, args: {} }); }
function configFenceFor(st) { return { configMtimeNs: st.configMtimeNs == null ? '' : st.configMtimeNs }; }
function fileBytes(p) { try { return fs.readFileSync(p); } catch { return null; } }
function inodeOf(p) { return fs.statSync(p, { bigint: true }).ino; }
function anchorAt(text, quote, nth) {
  let i = -1;
  for (let k = 0; k <= (nth || 0); k++) i = text.indexOf(quote, i + 1);
  assert.ok(i >= 0, `fixture lacks occurrence ${nth} of ${JSON.stringify(quote)}`);
  return { anchor: engine.makeAnchor(text, i, i + quote.length), hintOffset: i };
}
// The loose file's directory as the world made it: the file alone, no landmark.
function assertUntouched(w) {
  assert.equal(fs.existsSync(path.join(w.looseDir, '.trackchanges')), false, 'a refused verb created a landmark');
  assert.deepEqual(fs.readdirSync(w.looseDir), ['report.md']);
  assert.equal(status(w, w.loose).root, null, 'status still answers root:null after the refusal');
}

// ── a refused verb creates no landmark ──────────────────────────────

test('set-tracked folder on a loose file refuses folder-is-root, names its own folder, and creates no landmark', () => {
  const w = world();
  const r = refused(w, { verb: 'set-tracked', path: w.loose, args: { on: true, scope: 'folder' }, fence: { configMtimeNs: '' } }, 'folder-is-root');
  assert.ok(r.error.includes('~/loose/report.md'), r.error);
  assert.ok(r.error.includes('~/loose'), r.error);
  assert.match(r.error, /track the file itself/);
  assertUntouched(w);
  // The refusal on a loose file says why there is no folder: no project above it, so its own
  // folder would be the root. The rooted text (a file at an existing project's root) stays as it was.
  assert.match(r.error, /no project above it/);
  const rooted = refused(w, { verb: 'set-tracked', path: w.index, args: { on: true, scope: 'folder' }, fence: { configMtimeNs: '' } }, 'folder-is-root');
  assert.match(rooted.error, /sits at its project's root/);
  assert.equal(fs.existsSync(path.join(w.root, '.trackchanges')), false);
  // The first toggle that is not refused creates the landmark, as before.
  const on = ok(w, { verb: 'set-tracked', path: w.loose, args: { on: true, scope: 'file' }, fence: { configMtimeNs: '' } });
  assert.equal(on.root, w.looseDir);
  assert.deepEqual(readConfig(w.looseDir), { v: 2, tracked: ['report.md'] });
});

test('a refused comment on a loose file creates no landmark: anchor-not-found, anchor-ambiguous, and a malformed anchor', () => {
  const w = world();
  const missing = { quote: 'cut p99 latency', prefix: '', suffix: '' };
  const r1 = refused(w, { verb: 'comment', path: w.loose, args: { anchor: missing, note: 'x' }, fence: { storeMtimeNs: '' } }, 'anchor-not-found');
  assert.ok(r1.error.includes('~/loose/report.md'), r1.error);
  assertUntouched(w);
  // The passage edited away between the selection and Enter, its surroundings intact.
  const gone = anchorAt(w.text, 'cut p95 latency by 40%', 0);
  fs.writeFileSync(w.loose, w.text.replace('cut p95 latency by 40%', 'cut p95 latency by 35%'));
  refused(w, { verb: 'comment', path: w.loose, args: { anchor: gone.anchor, note: 'x', hintOffset: gone.hintOffset }, fence: { storeMtimeNs: '' } }, 'anchor-not-found');
  assertUntouched(w);
  fs.writeFileSync(w.loose, w.text);
  const twice = anchorAt(w.text, 'Ship it.', 1);
  refused(w, { verb: 'comment', path: w.loose, args: { anchor: twice.anchor, note: 'x', hintOffset: twice.hintOffset }, fence: { storeMtimeNs: '' } }, 'anchor-ambiguous');
  assertUntouched(w);
  // A caller bug (a malformed anchor, an empty note) crashes before the landmark too.
  const bad = host(w, { verb: 'comment', path: w.loose, args: { anchor: { quote: 7 }, note: 'x' }, fence: { storeMtimeNs: '' } });
  assert.notEqual(bad.code, 0);
  assert.match(bad.stderr, /anchor\.quote/);
  assertUntouched(w);
  const empty = host(w, { verb: 'comment', path: w.loose, args: { note: '  ' }, fence: { storeMtimeNs: '' } });
  assert.notEqual(empty.code, 0);
  assertUntouched(w);
  // The first comment that is not refused creates the landmark and the sidecar, as before.
  const good = anchorAt(w.text, 'cut p95 latency by 40%', 0);
  const c = ok(w, { verb: 'comment', path: w.loose, args: { anchor: good.anchor, note: 'Which window?', hintOffset: good.hintOffset }, fence: { storeMtimeNs: '' } });
  assert.equal(c.root, w.looseDir);
  assert.equal(c.storePath, storePathFor(w.looseDir, w.loose));
  assert.equal(c.store.comments.length, 1);
});

test('a refused comment under an existing root leaves .trackchanges/ exactly as it was', () => {
  const w = world();
  writeTrackedPaths(w.root, ['index.md']);
  const before = fs.readdirSync(path.join(w.root, '.trackchanges')).sort();
  const twice = anchorAt(w.text, 'Ship it.', 1);
  refused(w, { verb: 'comment', path: w.report, args: { anchor: twice.anchor, note: 'x', hintOffset: twice.hintOffset }, fence: { storeMtimeNs: '' } }, 'anchor-ambiguous');
  assert.deepEqual(fs.readdirSync(path.join(w.root, '.trackchanges')).sort(), before);
  assert.equal(fs.existsSync(storePathFor(w.root, w.report)), false);
});

// ── config.json is replaced, never truncated in place ───────────────

// A twin root with the same config, written through the vendored setTracked: the bytes the
// Obsidian and VS Code hosts would leave. The host's write must equal them exactly.
function vendoredBytes(w, cfgBytes, rel, on) {
  const twin = path.join(w.home, 'twin');
  fs.mkdirSync(path.join(twin, '.trackchanges'), { recursive: true });
  if (cfgBytes) fs.writeFileSync(path.join(twin, '.trackchanges', 'config.json'), cfgBytes);
  setTracked(twin, rel, on);
  const out = fs.readFileSync(path.join(twin, '.trackchanges', 'config.json'));
  fs.rmSync(twin, { recursive: true, force: true });
  return out;
}

test('set-tracked replaces config.json through a rename, keeps every other entry and the vetoes, and writes the vendored bytes', () => {
  const w = world();
  fs.mkdirSync(path.dirname(w.cfg), { recursive: true });
  // Two entries that neither cover docs/report.md nor link to it, so `off` leaves it untracked.
  fs.writeFileSync(w.cfg, JSON.stringify({ v: 2, tracked: ['docs/a.md', 'notes/b.md'], untracked: ['docs/private/'] }, null, 2) + '\n');
  const cfg0 = fileBytes(w.cfg);
  const ino0 = inodeOf(w.cfg);
  const st = status(w, w.report);
  const on = ok(w, { verb: 'set-tracked', path: w.report, args: { on: true, scope: 'file' }, fence: configFenceFor(st) });
  assert.deepEqual(on.trackedBy, { kind: 'file', entry: 'docs/report.md' });
  assert.deepEqual(readConfig(w.root), { v: 2, tracked: ['docs/a.md', 'notes/b.md', 'docs/report.md'], untracked: ['docs/private/'] });
  // A new inode: the file was renamed into place, not opened and truncated. An in-place rewrite
  // keeps the inode and leaves a half-written config when the process dies between the two.
  const ino1 = inodeOf(w.cfg);
  assert.notEqual(ino1, ino0, 'config.json was rewritten in place');
  assert.deepEqual(fileBytes(w.cfg), vendoredBytes(w, cfg0, 'docs/report.md', true));
  assert.equal(on.configMtimeNs, fs.statSync(w.cfg, { bigint: true }).mtimeNs.toString(), 'the reply fences on the file now in place');
  // No temp file left beside it; nothing but the config and the toggle's log line.
  const lp = logPathFor(storePathFor(w.root, w.report));
  assert.deepEqual(fs.readdirSync(path.dirname(w.cfg)).sort(), ['config.json', path.basename(lp)].sort());
  // Off: the same discipline, and the same bytes.
  const cfg1 = fileBytes(w.cfg);
  const off = ok(w, { verb: 'set-tracked', path: w.report, args: { on: false }, fence: configFenceFor(on) });
  assert.equal(off.trackedBy, null);
  assert.notEqual(inodeOf(w.cfg), ino1);
  assert.deepEqual(fileBytes(w.cfg), vendoredBytes(w, cfg1, 'docs/report.md', false));
  assert.deepEqual(readConfig(w.root), { v: 2, tracked: ['docs/a.md', 'notes/b.md'], untracked: ['docs/private/'] });
  assert.deepEqual(fs.readdirSync(path.dirname(w.cfg)).sort(), ['config.json', path.basename(lp)].sort());
  // A folder entry and a duplicate toggle go through the same writer: still the vendored bytes.
  const cfg2 = fileBytes(w.cfg);
  const folder = ok(w, { verb: 'set-tracked', path: w.report, args: { on: true, scope: 'folder' }, fence: configFenceFor(off) });
  assert.deepEqual(fileBytes(w.cfg), vendoredBytes(w, cfg2, 'docs/', true));
  const cfg3 = fileBytes(w.cfg);
  ok(w, { verb: 'set-tracked', path: w.report, args: { on: true, scope: 'folder' }, fence: configFenceFor(folder) });
  assert.deepEqual(fileBytes(w.cfg), vendoredBytes(w, cfg3, 'docs/', true));
  assert.deepEqual(readConfig(w.root).tracked, ['docs/a.md', 'notes/b.md', 'docs/']);
});

test('the first toggle under a root with no config.json, and on a loose file, writes the vendored bytes', () => {
  const w = world();
  ok(w, { verb: 'set-tracked', path: w.report, args: { on: true, scope: 'file' }, fence: { configMtimeNs: '' } });
  assert.deepEqual(fileBytes(w.cfg), vendoredBytes(w, null, 'docs/report.md', true));
  ok(w, { verb: 'set-tracked', path: w.loose, args: { on: true, scope: 'file' }, fence: { configMtimeNs: '' } });
  assert.deepEqual(fileBytes(path.join(w.looseDir, '.trackchanges', 'config.json')), vendoredBytes(w, null, 'report.md', true));
  // The vendored CLI reads what the host wrote.
  const r = spawnSync(process.execPath, [path.join(VENDOR, 'cli', 'track-config.mjs'), '--file', w.loose], { encoding: 'utf8', env: env(w) });
  assert.equal(r.stdout.trim(), 'on');
});
