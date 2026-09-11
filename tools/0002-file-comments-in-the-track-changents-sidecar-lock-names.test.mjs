// The ADR's lock bullet (docs/adr/0002, "Since 2026-09-11 one transient file ...") enumerates what
// store-io's lock leaves under `.trackchanges/`: `<name>.lock` for the length of a write,
// `<name>.lock.break` while a break runs, and one `made-dir` line appended to another writer's
// lock or claim when the folder's removal is handed over. Held here to the code two ways: by the constants
// store-io defines (a suffix or a line the code adds that the bullet does not name, or one the bullet names
// that the code no longer defines, fails), and by the lock run in a scratch root (the claim's name governs a
// waiter, a break leaves only the lock behind for the write, and the maker's release writes the line into a
// real holder's lock, which that holder honors). Review round 2 (2026-09-11): round 1 added the claim and the
// handover line and the bullet still said one file. Synthetic paths only, under a scratch directory.
// Run: node --test tools/0002-file-comments-in-the-track-changents-sidecar-lock-names.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn, spawnSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';

import { storeLockPathFor, withStoreLock, StoreLockError } from '../vendor/track-changents/store-io.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const STORE_IO_PATH = path.join(REPO, 'vendor', 'track-changents', 'store-io.mjs');
const STORE_IO = pathToFileURL(STORE_IO_PATH).href;
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');

const adr = read('docs', 'adr', '0002-file-comments-in-the-track-changents-sidecar.md');
const storeIo = fs.readFileSync(STORE_IO_PATH, 'utf8');

function between(doc, from, to) {
  const a = doc.indexOf(from);
  assert.ok(a >= 0, `${JSON.stringify(from)} not found`);
  const b = doc.indexOf(to, a + from.length);
  assert.ok(b > a, `${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return doc.slice(a, b).replace(/\s+/g, ' ');
}
const bullet = between(adr, '- Since 2026-09-11 one transient file', '- A romp-only field');

// The names and the line as store-io defines them, read from its source so a rename there is a
// failure here and not a silently stale record.
function constant(name) {
  const m = new RegExp(`^const ${name} = '([^']+)';`, 'm').exec(storeIo);
  assert.ok(m, `store-io defines ${name}`);
  return m[1];
}
const LOCK = constant('STORE_LOCK_SUFFIX');
const BREAK = constant('STORE_LOCK_BREAK_SUFFIX');
const HANDOVER = constant('STORE_LOCK_HANDOVER');
const NAME_RE = (() => {
  const m = /^const STORE_LOCK_NAME_RE = \/(.*)\/;$/m.exec(storeIo);
  assert.ok(m, 'store-io defines STORE_LOCK_NAME_RE');
  return new RegExp(m[1]);
})();

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-adr-lock-names-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

let worlds = 0;
// A root with a landmark and, unless `fresh`, its `.trackchanges/`; the sidecar path of one note in it.
function world(fresh) {
  const root = path.join(SCRATCH, `w${++worlds}`, 'notes-api');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  const dir = path.join(root, '.trackchanges');
  if (!fresh) fs.mkdirSync(dir);
  const storePath = path.join(dir, 'docs%2Freport.md.json');
  return { root, dir, storePath, lockPath: storeLockPathFor(storePath) };
}

// The pid of a process that has exited (spawnSync returns only after it did).
function deadPid() {
  const gone = spawnSync(process.execPath, ['-e', ''], { encoding: 'utf8' });
  assert.equal(gone.status, 0);
  return gone.pid;
}

const sleepMs = (ms) => Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);

test('the bullet names the two names the lock leaves, as store-io defines them, and no third; both are outside the format', () => {
  const names = [LOCK, LOCK + BREAK];
  for (const n of names) assert.ok(bullet.includes(`\`<name>${n}\``), `the bullet names \`<name>${n}\``);
  const listed = [...bullet.matchAll(/`<name>(\.[\w.]+)`/g)].map((m) => m[1]);
  assert.deepEqual([...new Set(listed)].sort(), names.sort(), 'the bullet lists exactly the names the code leaves');
  for (const n of names) {
    assert.ok(!n.endsWith('.json'), `${n} is not read as a sidecar`);
    assert.match(`docs%2Freport.md.json${n}`, NAME_RE, `store-io counts ${n} among the names the lock leaves`);
  }
  assert.doesNotMatch('docs%2Freport.md.json', NAME_RE);
  assert.doesNotMatch('config.json', NAME_RE);
  assert.ok(bullet.includes('neither ends in `.json`'));
  assert.ok(bullet.includes('a second transient name while the break runs'), 'the claim is a second name, for the break only');
  assert.ok(bullet.includes('everything the lock leaves under `.trackchanges/`'), 'the bullet claims to be the whole enumeration');
});

test('the bullet names the handover line as store-io writes it, and says whose file it lands in', () => {
  assert.ok(bullet.includes(`\`${HANDOVER}\``), `the bullet names \`${HANDOVER}\``);
  assert.ok(bullet.includes(`appends one line, \`${HANDOVER}\`, to each of them`));
  assert.ok(bullet.includes('the one thing the lock writes into a file it did not create'));
  // the code appends exactly that line, once, through handOverDir
  assert.match(storeIo, /function handOverDir\(p\) \{[\s\S]*?fs\.writeFileSync\(fd, `\$\{STORE_LOCK_HANDOVER\}\\n`\)/);
  assert.equal((storeIo.match(/STORE_LOCK_HANDOVER\}\\n`/g) || []).length, 1, 'one append site');
});

test('a live claim beside a dead lock governs the waiter, under the second name; a dead claim goes with the break, and the write sees the lock alone', () => {
  const w = world(false);
  const claim = w.lockPath + BREAK;
  assert.equal(claim, `${w.storePath}${LOCK}${BREAK}`, 'the claim is the lock\'s name plus the break suffix');
  const gone = deadPid();
  fs.writeFileSync(w.lockPath, `${gone} ${Date.now()}\n`);
  fs.writeFileSync(claim, `${process.pid} ${Date.now()}\n`);   // a breaker mid-break
  let err = null;
  try { withStoreLock(w.storePath, () => 'ran', { waitMs: 120 }); } catch (e) { err = e; }
  assert.ok(err instanceof StoreLockError, String(err));
  assert.equal(err.held, true, 'the waiter waited out the bound behind the claim');
  assert.deepEqual(fs.readdirSync(w.dir).sort(), [path.basename(w.lockPath), path.basename(claim)].sort(), 'the dead lock and the live claim are both left');
  // the breaker died holding its claim
  fs.writeFileSync(claim, `${gone} ${Date.now()}\n`);
  let inside = null;
  withStoreLock(w.storePath, () => { inside = fs.readdirSync(w.dir); }, { waitMs: 1000 });
  assert.deepEqual(inside, [path.basename(w.lockPath)], 'for the length of the write, one file beside the sidecar: the lock');
  assert.deepEqual(fs.readdirSync(w.dir), [], 'the claim went with the break, the lock with the release');
});

// A real holder of a sibling's lock: takes it, holds until `marker` appears, reads its own lock back
// just before release (the line the maker appended lands there), and leaves. Prints one JSON line.
const HOLDER = `
import fs from 'node:fs';
const [storeIo, store, marker] = process.argv.slice(1);   // -e: no script path in argv
const { withStoreLock } = await import(storeIo);
const sleep = (ms) => Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
const out = { raw: null, dirAfter: null };
withStoreLock(store, () => {
  const until = Date.now() + 8000;
  while (!fs.existsSync(marker) && Date.now() < until) sleep(5);
  out.raw = fs.readFileSync(store + '.lock', 'utf8');
});
process.stdout.write(JSON.stringify(out) + '\\n');
`;

test('the maker of the folder writes the line into a real holder\'s lock at release, and that holder removes the folder at its own', async () => {
  const w = world(true);
  const sibling = path.join(w.dir, 'docs%2Fnotes.md.json');
  const siblingLock = storeLockPathFor(sibling);
  const marker = path.join(SCRATCH, `w${worlds}`, 'release-now');
  let child;
  let inside = null;
  const done = new Promise((resolve) => {
    let stdout = '';
    let stderr = '';
    child = spawn(process.execPath, ['--input-type=module', '-e', HOLDER, '--', STORE_IO, sibling, marker]);
    child.stdout.setEncoding('utf8'); child.stdout.on('data', (c) => { stdout += c; });
    child.stderr.setEncoding('utf8'); child.stderr.on('data', (c) => { stderr += c; });
    child.on('close', () => {
      let json = null;
      try { json = JSON.parse(stdout); } catch { json = { err: `no JSON line: ${stdout} ${stderr}` }; }
      resolve(json);
    });
  });
  // This process makes the folder (a first write in a fresh root) and, while it holds its lock, the
  // sibling's holder arrives and takes its own lock in the folder this process made.
  withStoreLock(w.storePath, () => {
    const until = Date.now() + 8000;
    while (!fs.existsSync(siblingLock) && Date.now() < until) sleepMs(5);
    assert.ok(fs.existsSync(siblingLock), 'the sibling\'s holder took its lock while this one held');
    inside = fs.readdirSync(w.dir).sort();
  });
  assert.deepEqual(inside, [path.basename(w.lockPath), path.basename(siblingLock)].sort(), 'two locks, nothing else');
  // released: the folder stays for the sibling's holder, whose lock now carries the line
  assert.ok(fs.existsSync(w.dir), 'the folder was not removed from under the sibling\'s holder');
  assert.equal(fs.existsSync(w.lockPath), false, 'this lock is gone');
  const handed = fs.readFileSync(siblingLock, 'utf8');
  assert.ok(handed.split('\n').includes(HANDOVER), `the line ${JSON.stringify(HANDOVER)} was appended to the sibling's lock: ${JSON.stringify(handed)}`);
  assert.match(handed, /^\d+ \d+\n/, 'appended after the holder\'s own stamp, not over it');
  fs.writeFileSync(marker, '');
  const out = await done;
  assert.equal(out.err, undefined, out.err);
  assert.ok(out.raw.split('\n').includes(HANDOVER), 'the holder read the line back at release');
  assert.equal(fs.existsSync(w.dir), false, 'the holder took the folder away at its own release');
  assert.ok(fs.existsSync(w.root), 'the root stays');
});
