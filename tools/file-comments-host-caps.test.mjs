// The byte caps tools/file-comments-host.mjs mirrors from the kernel (plans/file-review.md, Slices
// 3 and 4): FILE_HASH_CAP is the kernel's _MEDIA_MAX_BYTES, the cap of GET /file on every image and
// PDF, and TEXT_MAX_BYTES is its _TEXT_MAX_BYTES. The regions test pins FILE_HASH_CAP to a literal;
// this one reads both constants out of kernel.py, so the two sides cannot drift apart unnoticed. They
// did once: Slice 4 renamed the kernel's cap from _PREVIEW_MAX_BYTES (50,000,000) to _MEDIA_MAX_BYTES
// (50 MiB, so its 413 reads "50.0 MB") while the host kept 50,000,000, and a media file in the
// 2.4 MB between was served, shown and region-commentable, yet every status/comment reply on it
// carried fileHash null — so each region read "unknown" and regenerating the file never read stale.
// Hermetic, as the other host tests are: the synthetic `notes-api` world under a scratch directory,
// the script driven as the kernel drives it. The boundary files are SPARSE (a truncate, no bytes
// written), so a 50 MiB probe costs no disk.
// Run: node --test tools/file-comments-host-caps.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

import { FILE_HASH_CAP, TEXT_MAX_BYTES, hashRegular } from './file-comments-host.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST = path.join(REPO, 'tools', 'file-comments-host.mjs');
const KERNEL = fs.readFileSync(path.join(REPO, 'kernel', 'kernel.py'), 'utf8');

// A module-level `NAME = <int product>` in kernel.py, evaluated: the caps are written as products of
// integer literals (`50 * 1024 * 1024`, or a bare `50_000_000`) and nothing else, so anything that
// does not parse as one is a test failure, not a guess.
function kernelBytes(name) {
  const m = new RegExp(`^${name} = ([0-9_]+(?:\\s*\\*\\s*[0-9_]+)*)\\s*(?:#|$)`, 'm').exec(KERNEL);
  assert.ok(m, `kernel.py defines ${name} as a product of integer literals at column 0`);
  return m[1].split('*').map((t) => Number(t.trim().replace(/_/g, ''))).reduce((a, b) => a * b, 1);
}

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-fc-host-caps-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

// <scratch>/wN/home/notes-api/.git   the landmark that makes notes-api a project
// <scratch>/wN/home/notes-api/docs   where the probe files live
let worlds = 0;
function world() {
  const home = path.join(SCRATCH, `w${++worlds}`, 'home');
  const root = path.join(home, 'notes-api');
  const docs = path.join(root, 'docs');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  fs.mkdirSync(docs, { recursive: true });
  return { home, root, docs };
}

// The kernel's call under the DEFAULT caps: the overrides are cleared from the inherited environment,
// so what this test measures is the constant the script ships with.
function status(w, file) {
  const env = { ...process.env, FILE_COMMENTS_HOME: w.home };
  delete env.TRACKCHANGES_ROOT;
  delete env.FILE_COMMENTS_HASH_CAP;
  delete env.FILE_COMMENTS_EMBEDDED_HASH_CAP;
  delete env.ROMP_SID;
  delete env.ROMP_SESSION_NAME;
  const req = { verb: 'status', path: file, args: {} };
  const r = spawnSync(process.execPath, [HOST], { input: JSON.stringify(req), encoding: 'utf8', env });
  assert.equal(r.status, 0, `exit ${r.status}: ${r.stderr}`);
  let json = null;
  try { json = JSON.parse(r.stdout); } catch { json = null; }
  assert.ok(json && json.ok === true, `expected ok:true, got ${r.stdout}`);
  assert.equal(json.verb, 'status');
  return json;
}

// A sparse file of exactly `size` zero bytes: created empty and truncated UP, so no byte is written.
function sparse(p, size) {
  fs.writeFileSync(p, '');
  fs.truncateSync(p, size);
  assert.equal(fs.statSync(p).size, size);
}

// The sha256 of `size` zero bytes, in chunks, so a 50 MiB expectation costs no 50 MiB buffer.
function sha256Zeros(size) {
  const h = createHash('sha256');
  const chunk = Buffer.alloc(1024 * 1024);
  for (let left = size; left > 0; left -= chunk.length) h.update(chunk.subarray(0, Math.min(left, chunk.length)));
  return h.digest('hex');
}

test('FILE_HASH_CAP is the kernel\'s _MEDIA_MAX_BYTES, byte for byte: every media file GET /file serves, this script hashes', () => {
  assert.equal(FILE_HASH_CAP, kernelBytes('_MEDIA_MAX_BYTES'));
  // The kernel's number is a power-of-two 50 MiB so its 413 reads "50.0 MB" (tests/test_file_view.py);
  // the 50,000,000 the host carried through Slice 3 would leave a 2.4 MB window of served files unhashed.
  assert.equal(FILE_HASH_CAP, 50 * 1024 * 1024);
  assert.ok(FILE_HASH_CAP > 50_000_000, 'the old literal is inside the cap, not the cap');
  // The stale comment named a constant the kernel no longer has; the mirror names the one it does.
  assert.equal(/_PREVIEW_MAX_BYTES/.test(KERNEL), false, 'kernel.py has no _PREVIEW_MAX_BYTES any more');
  const host = fs.readFileSync(HOST, 'utf8');
  assert.equal(/_PREVIEW_MAX_BYTES/.test(host), false, 'the host script names no constant the kernel lacks');
  assert.match(host, /_MEDIA_MAX_BYTES/, 'the host script names the kernel constant it mirrors');
});

test('TEXT_MAX_BYTES is the kernel\'s _TEXT_MAX_BYTES, byte for byte', () => {
  assert.equal(TEXT_MAX_BYTES, kernelBytes('_TEXT_MAX_BYTES'));
});

test('under the default cap, a media file of exactly the kernel\'s cap hashes and one byte over is null: the viewer\'s "unknown" region is unreachable for a file the kernel serves', () => {
  const w = world();
  const png = path.join(w.docs, 'big.png');
  // Exactly the cap: the kernel serves it (its check is strictly over), so the host must hash it.
  sparse(png, FILE_HASH_CAP);
  assert.equal(status(w, png).fileHash, sha256Zeros(FILE_HASH_CAP));
  // The old host literal, now inside the cap: the file the finding's window is about hashes too.
  sparse(png, 50_000_001);
  assert.equal(status(w, png).fileHash, sha256Zeros(50_000_001));
  // One byte over the kernel's cap: GET /file 413s it, and the host answers "unknown" — null, no read.
  sparse(png, FILE_HASH_CAP + 1);
  assert.equal(status(w, png).fileHash, null);
  // The same boundary at the function the verb calls, with the cap passed as the verb passes it.
  assert.deepEqual(hashRegular(png, FILE_HASH_CAP), { hash: null, size: FILE_HASH_CAP + 1 });
  assert.equal(hashRegular(png, null).hash, sha256Zeros(FILE_HASH_CAP + 1), 'a comment stamps the full hash uncapped');
});
