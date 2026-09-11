// The CLI-vs-CLI race the sidecar lock closes (plans/file-review.md, decision 49; vendor patch 0008),
// driven with the real `track-comment`: several processes, each another session's, comment on one note
// at one instant, and every comment must land. Every writer of a sidecar loads it, changes the object
// and renames a temp over it, so two writers interleaved between load and rename each save a store
// without the other's change and the second rename erases the first's (one write in five lost at a
// 4 to 20 ms stagger: the lost-update probe of 2026-09-09). The lock cases elsewhere refuse a held
// lock, wait for one synthetic holder and break a dead one (tools/vendor-patches.test.mjs P8,
// tools/file-comments-host-store-lock.test.mjs, tools/store-io-lock.test.mjs); none ran two real CLIs
// writing one sidecar at once, so a track-comment whose save slipped past its lock (the load and the
// comment under withStoreLock, the save after the release) passed every one of them while six such
// processes on one note lost about one comment in four, to the unlocked `.tmp` collision and to the
// rename over each other's write (the review of 2026-09-11). Here the writers are the CLIs themselves,
// run as a session runs them, released together by a file they all spin on:
//   * six track-comment processes, each another session, on one note over several rounds, the first
//     round on a root with no `.trackchanges/` yet: every one exits 0 with its one line, every comment
//     is in the sidecar with its author, and the folder holds the sidecar alone (no lock, no temp, no
//     claim).
//   * the same with track-reply beside it: three comments and three replies to one earlier comment at once.
//   * a first comment on a root with no `.trackchanges/` yet whose folder another writer makes
//     between its lock create's ENOENT and its look at the folder lands: the create is tried again,
//     not refused as `cannot create <lock>: ENOENT`. The race above met this in about one run in
//     seven on the machine that first ran it (six first writers, one round): a transient of the
//     shared folder's making, judged a failure to create the lock, so a session's comment was
//     refused with a raw OS error and a host would refuse `unreadable`.
//   * the source: run() takes the lock around commentUnderLock, and the save is inside it.
// Synthetic root, note, sessions and ids only, under a scratch directory.
// Run: node --test tools/track-comment-race.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';

import { storePathFor, loadStore } from '../vendor/track-changents/store-io.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
// Real paths: a CLI runs only when process.argv[1]'s real path is its own module's.
const VENDOR = fs.realpathSync(path.resolve(HERE, '..', 'vendor', 'track-changents'));
const CLI = {
  'track-comment': path.join(VENDOR, 'cli', 'track-comment.mjs'),
  'track-reply': path.join(VENDOR, 'cli', 'track-reply.mjs'),
};
const LINE = { 'track-comment': 'Comment added.\n', 'track-reply': 'Reply posted to thread.\n' };
const STORE_IO = pathToFileURL(path.join(VENDOR, 'store-io.mjs')).href;

// Six sessions of the notes-api demo world; synthetic names and ids.
const SESSIONS = ['web', 'api', 'tests', 'docs', 'infra', 'review']
  .map((name, i) => ({ name, sid: `11111111-2222-3333-4444-55555555555${i}` }));

const ANCHORS = ['Step one', 'Step two', 'Step three', 'Step four', 'Step five', 'Step six'];
const NOTE = [
  '# Latency report',
  '',
  'Step one: warm the cache before the first request.',
  'Step two: keep cold starts on the watch list.',
  'Step three: ship the cache in v1.2.',
  'Step four: retry on timeout once.',
  'Step five: measure the p95 again after a week.',
  'Step six: close the report.',
  '',
].join('\n');

// Preloaded into each CLI process (`--import`): warms store-io, so the CLI's own import of it is a
// cache hit, reports the process ready, then spins until the round's go file exists; the CLI runs on
// its return. A gate that never opens lets the process run after five seconds.
const GATE = `
import fs from 'node:fs';
await import(process.env.TRACK_COMMENT_RACE_WARM);
fs.writeFileSync(process.env.TRACK_COMMENT_RACE_READY, '');
const go = process.env.TRACK_COMMENT_RACE_GO;
const deadline = Date.now() + 5000;
while (!fs.existsSync(go) && Date.now() < deadline) { /* spin */ }
`;

// Preloaded into one CLI process: the peer's first write, at the one instant the race reaches
// once in several runs. The CLI's first O_EXCL create of its lock fails ENOENT (no `.trackchanges/`
// yet) and, before the CLI looks at the folder, the peer's making of it lands. Everything else is
// the real fs. store-io calls fs.openSync through the module's default export, so the wrapper is
// what it calls. It arms on any exclusive create of the lock's name (flags with `x`: 'wx' as first
// built, 'ax+' since review round 2) and writes the file TRACK_COMMENT_RACE_PEER_FIRED names when it
// fires, so the case can tell it ran: armed on the literal 'wx' after the flags changed, it never
// fired and the case ran as a plain first comment (review round 4, 2026-09-11).
const PEER = `
import fs from 'node:fs';
import path from 'node:path';
const real = fs.openSync;
let armed = true;
fs.openSync = function (p, flags, ...rest) {
  if (!armed || typeof flags !== 'string' || !flags.includes('x') || typeof p !== 'string' || !p.endsWith('.json.lock')) return real.call(fs, p, flags, ...rest);
  armed = false;
  try {
    return real.call(fs, p, flags, ...rest);
  } catch (e) {
    if (e && e.code === 'ENOENT') {
      fs.mkdirSync(path.dirname(p), { recursive: true });
      fs.writeFileSync(process.env.TRACK_COMMENT_RACE_PEER_FIRED, '');
    }
    throw e;
  }
};
`;

let SCRATCH;
let GATE_URL;
let PEER_URL;
before(() => {
  SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-track-comment-race-'));
  const gate = path.join(SCRATCH, 'gate.mjs');
  fs.writeFileSync(gate, GATE);
  GATE_URL = pathToFileURL(gate).href;
  const peer = path.join(SCRATCH, 'peer.mjs');
  fs.writeFileSync(peer, PEER);
  PEER_URL = pathToFileURL(peer).href;
});
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

let worlds = 0;
// A root with a landmark and one note, no `.trackchanges/` yet; the note's sidecar path.
function world() {
  const root = path.join(SCRATCH, `w${++worlds}`, 'notes-api');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  fs.mkdirSync(path.join(root, 'docs'));
  const note = path.join(root, 'docs', 'report.md');
  fs.writeFileSync(note, NOTE);
  const storePath = storePathFor(root, note);
  return { root, note, storePath, dir: path.dirname(storePath) };
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// One CLI run as a session runs it (its name and id in the environment, no root override). With a
// gate, the process reports ready and waits at it before the CLI runs; with a preload ({ url, fired }),
// that module runs first (the peer above) and writes `fired` when it fires.
function cli(name, args, session, { gate, preload } = {}) {
  return new Promise((resolve, reject) => {
    const env = { ...process.env };
    for (const k of ['TRACKCHANGES_ROOT', 'TRACKCHANGES_SESSION', 'ROMP_SID', 'ROMP_SESSION_NAME']) delete env[k];
    env.ROMP_SESSION_NAME = session.name;
    env.ROMP_SID = session.sid;
    const nodeArgs = [];
    if (preload) { nodeArgs.push('--import', preload.url); env.TRACK_COMMENT_RACE_PEER_FIRED = preload.fired; }
    if (gate) {
      nodeArgs.push('--import', GATE_URL);
      env.TRACK_COMMENT_RACE_WARM = STORE_IO;
      env.TRACK_COMMENT_RACE_READY = path.join(gate.dir, `ready-${name}-${session.name}`);
      env.TRACK_COMMENT_RACE_GO = gate.go;
    }
    const child = spawn(process.execPath, [...nodeArgs, CLI[name], ...args], { env });
    let stdout = '';
    let stderr = '';
    child.stdout.setEncoding('utf8'); child.stdout.on('data', (c) => { stdout += c; });
    child.stderr.setEncoding('utf8'); child.stderr.on('data', (c) => { stderr += c; });
    child.on('error', reject);
    child.on('close', (status) => resolve({ name, session: session.name, args, status, stdout, stderr }));
    child.stdin.end();
  });
}

let gates = 0;
// Run every writer at once: each waits at the gate, which opens once all of them are there (or after
// five seconds, for a machine too loaded to start them in time). Returns the results and how many
// were at the gate when it opened.
async function race(writers) {
  const dir = path.join(SCRATCH, 'gates', String(++gates));
  fs.mkdirSync(dir, { recursive: true });
  const gate = { dir, go: path.join(dir, 'go') };
  const pending = writers.map((x) => cli(x.name, x.args, x.session, { gate }));
  const deadline = Date.now() + 5000;
  while (fs.readdirSync(dir).length < writers.length && Date.now() < deadline) await sleep(2);
  const ready = fs.readdirSync(dir).length;
  fs.writeFileSync(gate.go, '');
  return { results: await Promise.all(pending), ready };
}

function landed(results) {
  for (const r of results) {
    assert.equal(r.status, 0, `${r.name} (${r.session}) exited ${r.status}: ${r.stderr || r.stdout}`);
    assert.equal(r.stdout, LINE[r.name], `${r.name} (${r.session}) printed its one line`);
    assert.equal(r.stderr, '', `${r.name} (${r.session}) wrote nothing to stderr`);
  }
}

function sidecarAlone(w) {
  assert.deepEqual(fs.readdirSync(w.dir), [path.basename(w.storePath)],
    'the folder holds the sidecar alone: no lock, no temp, no claim');
}

const noteOf = (x) => x.args[x.args.indexOf('--note') + 1];

// ── the race ────────────────────────────────────────────────────────

const ROUNDS = 10;

test(`six real track-comment processes on one note at one instant, ${ROUNDS} rounds from a root with no .trackchanges/: every comment lands, none is lost, no lock or temp is left`, async (t) => {
  const w = world();
  assert.equal(fs.existsSync(w.dir), false, 'the first round makes the folder, under the race');
  let atGate = 0;
  for (let r = 0; r < ROUNDS; r++) {
    const writers = SESSIONS.map((session, i) => ({
      name: 'track-comment', session,
      args: ['--file', w.note, '--anchor', ANCHORS[i], '--note', `Round ${r}: ${session.name} on ${ANCHORS[i].toLowerCase()}.`],
    }));
    const { results, ready } = await race(writers);
    atGate += ready;
    landed(results);
    const store = loadStore(w.storePath, NOTE);
    assert.ok(store, `round ${r}: the sidecar parses`);
    assert.equal(store.comments.length, 6 * (r + 1), `round ${r}: ${6 * (r + 1) - store.comments.length} comment(s) lost`);
    for (const [i, x] of writers.entries()) {
      const c = store.comments.find((k) => k.body === noteOf(x));
      assert.ok(c, `round ${r}: the comment by ${x.session.name} is in the sidecar`);
      assert.equal(c.author, x.session.name);
      assert.equal(c.authorId, x.session.sid);
      assert.equal(c.anchor.quote, ANCHORS[i]);
    }
    sidecarAlone(w);
  }
  const ids = new Set(loadStore(w.storePath, NOTE).comments.map((c) => c.id));
  assert.equal(ids.size, 6 * ROUNDS, 'every comment has its own id');
  assert.equal(fs.readFileSync(w.note, 'utf8'), NOTE, 'the note is untouched');
  t.diagnostic(`${atGate} of ${6 * ROUNDS} writers were at the gate when it opened`);
});

test('three track-comment and three track-reply processes, each another session, on one sidecar at one instant: every comment and every reply lands', async (t) => {
  const w = world();
  const seed = await cli('track-comment', ['--file', w.note, '--anchor', 'Step one', '--note', 'Which cache?'], SESSIONS[0]);
  landed([seed]);
  // The vendored CLI takes the id of the comment a reply goes to as `--thread`; here that is the earlier comment.
  const earlier = loadStore(w.storePath, NOTE).comments[0].id;
  let atGate = 0;
  for (let r = 0; r < 6; r++) {
    const writers = [
      ...[1, 2, 3].map((i) => ({
        name: 'track-comment', session: SESSIONS[i],
        args: ['--file', w.note, '--anchor', ANCHORS[i], '--note', `Round ${r}: ${SESSIONS[i].name} on ${ANCHORS[i].toLowerCase()}.`],
      })),
      ...[4, 5, 0].map((i) => ({
        name: 'track-reply', session: SESSIONS[i],
        args: ['--file', w.note, '--thread', earlier, '--note', `Round ${r}: ${SESSIONS[i].name} answers.`],
      })),
    ];
    const { results, ready } = await race(writers);
    atGate += ready;
    landed(results);
    const store = loadStore(w.storePath, NOTE);
    assert.ok(store, `round ${r}: the sidecar parses`);
    assert.equal(store.comments.length, 1 + 3 * (r + 1), `round ${r}: ${1 + 3 * (r + 1) - store.comments.length} comment(s) lost`);
    const head = store.comments.find((c) => c.id === earlier);
    assert.ok(head, `round ${r}: the earlier comment is in the sidecar`);
    assert.equal(head.replies.length, 3 * (r + 1), `round ${r}: ${3 * (r + 1) - head.replies.length} reply(ies) lost`);
    for (const x of writers) {
      const list = x.name === 'track-comment' ? store.comments : head.replies;
      const k = list.find((e) => e.body === noteOf(x));
      assert.ok(k, `round ${r}: the ${x.name === 'track-comment' ? 'comment' : 'reply'} by ${x.session.name} is in the sidecar`);
      assert.equal(k.author, x.session.name);
      assert.equal(k.authorId, x.session.sid);
    }
    sidecarAlone(w);
  }
  t.diagnostic(`${atGate} of 36 writers were at the gate when it opened`);
});

// ── the first write ─────────────────────────────────────────────────

test('a first comment whose folder another writer makes between its lock create and its look lands: the ENOENT is tried again, not refused', async () => {
  const w = world();
  assert.equal(fs.existsSync(w.dir), false);
  const fired = path.join(SCRATCH, 'peer-fired');
  const r = await cli('track-comment', ['--file', w.note, '--anchor', 'Step two', '--note', 'Which list?'], SESSIONS[1], { preload: { url: PEER_URL, fired } });
  assert.ok(fs.existsSync(fired), 'the peer fired: the lock create met ENOENT and the folder was made before the CLI looked (armed on flags store-io no longer passes, the peer never fired and the case ran as a plain first comment; review round 4, 2026-09-11)');
  assert.equal(r.status, 0, `exited ${r.status}: ${r.stderr || r.stdout}`);
  assert.equal(r.stdout, LINE['track-comment']);
  assert.equal(r.stderr, '');
  const store = loadStore(w.storePath, NOTE);
  assert.ok(store, 'the sidecar parses');
  assert.equal(store.comments.length, 1);
  assert.equal(store.comments[0].body, 'Which list?');
  assert.equal(store.comments[0].author, 'api');
  sidecarAlone(w);
  // the preload is the peer's making of the folder alone: without it, the same first comment lands the same way
  const w2 = world();
  const plain = await cli('track-comment', ['--file', w2.note, '--anchor', 'Step two', '--note', 'Which list?'], SESSIONS[1]);
  landed([plain]);
  assert.equal(loadStore(w2.storePath, NOTE).comments.length, 1);
  sidecarAlone(w2);
});

// ── the source ──────────────────────────────────────────────────────

test('the save is inside the lock: run() takes withStoreLock around commentUnderLock, which reads the note, loads the sidecar, adds the comment and saves before it returns', () => {
  const src = fs.readFileSync(CLI['track-comment'], 'utf8');
  const runAt = src.indexOf('\nfunction run(');
  const lockedAt = src.indexOf('\nfunction commentUnderLock(');
  const tailAt = src.indexOf('\nconst invokedDirectly');
  assert.ok(runAt > 0 && lockedAt > runAt && tailAt > lockedAt, 'run(), then commentUnderLock(), then the entry point');
  const run = src.slice(runAt, lockedAt);
  const locked = src.slice(lockedAt, tailAt);
  assert.ok(run.includes('withStoreLock(storePath, () => commentUnderLock(args, abs, vaultRoot, storePath));'), 'run() takes the lock around commentUnderLock');
  assert.ok(!run.includes('saveStore(') && !run.includes('loadStore('), 'nothing is loaded or saved outside the lock');
  for (const step of ["fs.readFileSync(abs, 'utf8')", 'loadStore(storePath, text)', 'addComment(store, text, args.anchor', 'saveStore(vaultRoot, storePath, store, text)']) {
    assert.ok(locked.includes(step), `the locked region holds ${step}`);
  }
  assert.equal((src.match(/saveStore\(/g) || []).length, 1, 'one save, the locked one');
  assert.ok(src.indexOf("process.stdout.write('Comment added.\\n');") > runAt && src.indexOf("process.stdout.write('Comment added.\\n');") < lockedAt, 'the one line is printed after the release');
});
