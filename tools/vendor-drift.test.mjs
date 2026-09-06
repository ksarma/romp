// The vendored track-changents copy (vendor/track-changents/) is the pinned upstream commit
// plus the patch series under vendor/track-changents/patches/, nothing else. This test holds
// that invariant without a second copy of the sources: PIN.json carries the sha256 of every
// file AS IT WAS at the pinned commit, so reverse-applying the patches onto a scratch copy of
// the vendored files must reproduce those hashes, and applying them forward again must
// reproduce the vendored files byte for byte. A hand edit to a vendored file that bypassed
// patches/ fails here, and so does a patch that no longer applies.
//
// The checkout half runs only where a track-changents checkout exists ($TRACKCHANGENTS_CHECKOUT,
// else ~/code/track-changents). It asserts two things: the checkout is AT OR PAST the pin (the
// pin is an ancestor of its HEAD), and PIN.json is HONEST, meaning each hash in it is the sha256
// of the blob the pinned commit stores at that path, read from the checkout's object store.
// Without the second check the invariant above rests on PIN.json alone: a pin minted from a
// dirty working tree, or a PIN.commit bumped without re-hashing, is self-consistent (the
// reverse-applied patches still reproduce it) while the vendored tree is no longer the pinned
// commit plus patches, and every offer back is diffed against the wrong base. The checkout half
// never compares vendored files against the checkout's WORKING TREE, which by construction
// differs from a patched copy; it reads only the pinned commit's objects.
//
// Run: node --test tools/vendor-drift.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const VENDOR = path.resolve(HERE, '..', 'vendor', 'track-changents');
const PATCH_DIR = path.join(VENDOR, 'patches');
const PIN = JSON.parse(fs.readFileSync(path.join(VENDOR, 'PIN.json'), 'utf8'));
const PATCHES = fs.readdirSync(PATCH_DIR).filter((f) => f.endsWith('.patch')).sort();
// romp's own files beside the vendored ones; everything else under VENDOR is upstream's.
// `.git` is the scratch copy's repo, never present under VENDOR itself.
const OWN = new Set(['PIN.json', 'README.md', 'patches', '.git']);

const sha256 = (buf) => createHash('sha256').update(buf).digest('hex');

function walk(root, rel = '') {
  const out = [];
  for (const name of fs.readdirSync(path.join(root, rel)).sort()) {
    if (rel === '' && OWN.has(name)) continue;
    const r = rel ? `${rel}/${name}` : name;
    if (fs.statSync(path.join(root, r)).isDirectory()) out.push(...walk(root, r));
    else out.push(r);
  }
  return out;
}

function git(args, cwd) {
  const r = spawnSync('git', args, { cwd, encoding: 'utf8' });
  assert.equal(r.status, 0, `git ${args.join(' ')} failed in ${cwd}:\n${r.stderr}`);
  return r.stdout;
}

// A scratch git repo holding a copy of the vendored files, so `git apply` checks every
// preimage exactly (outside a repo it would still work, but the repo makes -R and
// --check unambiguous and keeps the copy out of any real tree).
function scratchCopy() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-vendor-drift-'));
  git(['-c', 'init.defaultBranch=main', 'init', '-q'], dir);
  for (const rel of walk(VENDOR)) {
    fs.mkdirSync(path.dirname(path.join(dir, rel)), { recursive: true });
    fs.copyFileSync(path.join(VENDOR, rel), path.join(dir, rel));
  }
  return dir;
}

function hashesOf(root) {
  return Object.fromEntries(walk(root).map((rel) => [rel, sha256(fs.readFileSync(path.join(root, rel)))]));
}

// Where PIN.json disagrees with the commit it names: every pinned path whose hash is not the
// sha256 of the blob `commit` stores there, or which `commit` has no file at. Reads the
// checkout's OBJECTS (`git cat-file blob <commit>:<path>`), never its working tree, so a
// dirty or moved-on checkout does not change the answer; only a different pin does.
function pinDisagreements(dir, commit, files) {
  const out = [];
  for (const [rel, pinned] of Object.entries(files)) {
    const r = spawnSync('git', ['-C', dir, 'cat-file', 'blob', `${commit}:${rel}`], { maxBuffer: 64 << 20 });
    if (r.status !== 0) {
      out.push(`${rel}: the pinned commit has no such file (${r.stderr.toString().trim()})`);
      continue;
    }
    const actual = sha256(r.stdout);
    if (actual !== pinned) out.push(`${rel}: PIN.json says ${pinned.slice(0, 12)}…, the pinned commit's blob hashes to ${actual.slice(0, 12)}…`);
  }
  return out;
}

// The local track-changents checkout the checkout half reads, if there is one: skips the
// calling test when there is none, and fails it when the checkout has never fetched the
// pinned commit (neither half can judge anything without it).
function checkoutWithPin(t) {
  const dir = process.env.TRACKCHANGENTS_CHECKOUT || path.join(os.homedir(), 'code', 'track-changents');
  const shown = dir.startsWith(os.homedir()) ? `~${dir.slice(os.homedir().length)}` : dir;
  if (!fs.existsSync(path.join(dir, '.git'))) {
    t.skip(`no track-changents checkout at ${shown} (set TRACKCHANGENTS_CHECKOUT to point at one)`);
    return null;
  }
  const known = spawnSync('git', ['-C', dir, 'cat-file', '-e', `${PIN.commit}^{commit}`], { encoding: 'utf8' });
  assert.equal(known.status, 0, `the checkout at ${shown} does not have the pinned commit ${PIN.commit}; fetch it before judging drift`);
  return { dir, shown };
}

test('PIN.json names the pinned commit and every vendored file, and nothing else', () => {
  assert.match(PIN.commit, /^[0-9a-f]{40}$/, 'the pin is a full commit sha');
  assert.deepEqual(Object.keys(PIN.files).sort(), walk(VENDOR),
    'every file under vendor/track-changents (outside PIN.json, README.md, patches/) is pinned, and every pinned file exists');
  for (const [rel, h] of Object.entries(PIN.files)) assert.match(h, /^[0-9a-f]{64}$/, `${rel}: sha256 hex`);
});

test('the patch series is a numbered sequence with a header naming the reason, the files, and whether it is offered back', () => {
  assert.ok(PATCHES.length > 0, 'at least one patch');
  PATCHES.forEach((name, i) => {
    assert.match(name, /^\d{4}-[a-z0-9-]+\.patch$/, `${name}: NNNN-slug.patch`);
    assert.equal(name.slice(0, 4), String(i + 1).padStart(4, '0'), `${name}: numbered in sequence`);
    const text = fs.readFileSync(path.join(PATCH_DIR, name), 'utf8');
    const headerEnd = text.indexOf('\ndiff --git ');
    assert.ok(headerEnd > 0, `${name}: has a header before the first diff`);
    const header = text.slice(0, headerEnd);
    assert.match(header, /^# Patch \d{4} — .+/m, `${name}: title line`);
    assert.match(header, /^# Offered back: (yes|no)\b/m, `${name}: says whether it is offered back`);
    assert.match(header, /^# Reason: /m, `${name}: states its reason`);
    const filesLine = header.match(/^# Files: (.+)$/m);
    assert.ok(filesLine, `${name}: lists its files`);
    const declared = filesLine[1].split(',').map((s) => s.trim()).sort();
    const touched = [...text.matchAll(/^diff --git a\/(\S+) b\/(\S+)$/gm)].map((m) => m[2]).sort();
    assert.deepEqual(declared, touched, `${name}: the header's file list matches the diff`);
  });
});

test('the vendored README names the pin and every patch', () => {
  const readme = fs.readFileSync(path.join(VENDOR, 'README.md'), 'utf8');
  assert.ok(readme.includes(PIN.commit), 'README names the pinned commit');
  for (const name of PATCHES) assert.ok(readme.includes(name), `README lists ${name}`);
});

test('reverse-applying the patch series reproduces the pinned files, and applying it forward reproduces the vendored copy', () => {
  const dir = scratchCopy();
  try {
    for (const name of [...PATCHES].reverse()) {
      git(['apply', '-R', '--check', path.join(PATCH_DIR, name)], dir);
      git(['apply', '-R', path.join(PATCH_DIR, name)], dir);
    }
    const pristine = hashesOf(dir);
    assert.deepEqual(Object.keys(pristine).sort(), Object.keys(PIN.files).sort(),
      'after reversing the patches, the file set is exactly the pinned one');
    for (const [rel, h] of Object.entries(PIN.files)) {
      assert.equal(pristine[rel], h, `${rel}: pin-plus-patches (a change to a vendored file must go through patches/, and PIN.json must be the pristine hash)`);
    }
    for (const name of PATCHES) {
      git(['apply', '--check', path.join(PATCH_DIR, name)], dir);
      git(['apply', path.join(PATCH_DIR, name)], dir);
    }
    const rebuilt = hashesOf(dir);
    const live = hashesOf(VENDOR);
    assert.deepEqual(Object.keys(rebuilt).sort(), Object.keys(live).sort(), 'the forward series yields the vendored file set');
    for (const rel of Object.keys(live)) assert.equal(rebuilt[rel], live[rel], `${rel}: pristine plus the patch series equals the vendored file byte for byte`);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('a track-changents checkout on this machine, if any, is at or past the pin', (t) => {
  const co = checkoutWithPin(t);
  if (!co) return;
  const r = spawnSync('git', ['-C', co.dir, 'merge-base', '--is-ancestor', PIN.commit, 'HEAD'], { encoding: 'utf8' });
  assert.equal(r.status, 0, `the checkout at ${co.shown} is BEHIND the pin ${PIN.commit.slice(0, 7)}: its HEAD does not descend from it`);
});

test("PIN.json's hashes are the pinned commit's own blobs, where a checkout can show them", (t) => {
  const co = checkoutWithPin(t);
  if (!co) return;
  const bad = pinDisagreements(co.dir, PIN.commit, PIN.files);
  assert.deepEqual(bad, [], [
    `PIN.json is not an honest picture of the pinned commit ${PIN.commit.slice(0, 7)} (read from ${co.shown}).`,
    'Either PIN.commit was bumped without re-hashing, or PIN.json was minted from a working tree that was not',
    'exactly that commit; re-vendor per vendor/track-changents/README.md so the hashes are of pristine files at',
    'the pinned commit.',
    ...bad,
  ].join('\n'));
});

// The detector behind the test above, shown to read the commit rather than the working tree, on
// a synthetic repo so it runs where no track-changents checkout does (CI): a PIN.commit bumped
// without re-hashing, a pin minted from a dirty working tree, and a pinned path the commit lacks
// are each reported; an honest pin is not.
test('the pin-versus-commit check reads the pinned commit, not the working tree, so a bumped or dirty-tree pin is reported', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-vendor-drift-pin-'));
  const h = (s) => sha256(Buffer.from(s));
  const commit = (msg) => {
    git(['add', '-A'], dir);
    git(['-c', 'user.name=romp-test', '-c', 'user.email=romp-test@example.invalid', '-c', 'commit.gpgsign=false',
      'commit', '-q', '-m', msg], dir);
    return git(['rev-parse', 'HEAD'], dir).trim();
  };
  try {
    git(['-c', 'init.defaultBranch=main', 'init', '-q'], dir);
    fs.mkdirSync(path.join(dir, 'cli'));
    fs.writeFileSync(path.join(dir, 'engine.js'), 'module.exports = 1;\n');
    fs.writeFileSync(path.join(dir, 'cli', 'tool.mjs'), 'export const v = 1;\n');
    const parent = commit('first');
    fs.writeFileSync(path.join(dir, 'engine.js'), 'module.exports = 2;\n');
    const pinned = commit('second');
    // The working tree moves on without a commit; nothing below may notice.
    fs.writeFileSync(path.join(dir, 'engine.js'), 'module.exports = 3; // uncommitted\n');

    const honest = { 'engine.js': h('module.exports = 2;\n'), 'cli/tool.mjs': h('export const v = 1;\n') };
    assert.deepEqual(pinDisagreements(dir, pinned, honest), [], 'an honest pin has nothing to report, dirty working tree or not');

    // PIN.commit points at the parent while the hashes are the child's: bumped without re-hashing.
    const bumped = pinDisagreements(dir, parent, honest);
    assert.equal(bumped.length, 1, `exactly the file that changed between the commits is reported:\n${bumped.join('\n')}`);
    assert.match(bumped[0], /^engine\.js: PIN\.json says /);

    // Hashes taken from the dirty working tree instead of the commit.
    const dirty = pinDisagreements(dir, pinned, { ...honest, 'engine.js': h('module.exports = 3; // uncommitted\n') });
    assert.equal(dirty.length, 1, `the file whose pin came from the working tree is reported:\n${dirty.join('\n')}`);
    assert.match(dirty[0], /^engine\.js: PIN\.json says /);

    // A pinned path the commit does not have at all.
    const missing = pinDisagreements(dir, pinned, { ...honest, 'cli/gone.mjs': h('') });
    assert.equal(missing.length, 1);
    assert.match(missing[0], /^cli\/gone\.mjs: the pinned commit has no such file/);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});
