// Behaviour tests for the patches romp applies to its vendored track-changents copy
// (vendor/track-changents/patches/, listed in vendor/track-changents/README.md). Each
// case here fails against the pristine upstream files and passes with the patch, so
// re-vendoring cannot silently drop a fix. The CLIs are run as processes, the way an
// agent runs them, against a synthetic vault under os.tmpdir().
//
// Run: node --test tools/vendor-patches.test.mjs
import { test, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const VENDOR = path.resolve(HERE, '..', 'vendor', 'track-changents');
const { storePathFor, loadStore, recordAgentEdit, storeLockPathFor, STORE_LOCK_WAIT_MS } = await import(path.join(VENDOR, 'store-io.mjs'));

const SID_API = '11111111-2222-3333-4444-555555555555';
const SID_WEB = '66666666-7777-8888-9999-000000000000';

let vault;
let note;

beforeEach(() => {
  vault = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-vendor-patches-'));
  fs.mkdirSync(path.join(vault, '.obsidian'));
  note = path.join(vault, 'report.md');
});

afterEach(() => {
  fs.rmSync(vault, { recursive: true, force: true });
});

// Run a vendored CLI as the agent would: a child node process, the session's
// identity in the environment, nothing inherited that could steer the root.
function cli(name, args, env = {}) {
  const base = { ...process.env };
  for (const k of ['TRACKCHANGES_ROOT', 'TRACKCHANGES_SESSION', 'ROMP_SID', 'ROMP_SESSION_NAME']) delete base[k];
  return spawnSync(process.execPath, [path.join(VENDOR, 'cli', `${name}.mjs`), ...args], {
    encoding: 'utf8',
    env: { ...base, ROMP_SESSION_NAME: 'web', ROMP_SID: SID_WEB, ...env },
  });
}

// A note with one pending change by the `api` session and a .superseded park
// holding comment C1, which the live sidecar lacks. This is the A1 shape: the
// review closed (store parked), a new change landed, and a reply into the old
// comment arrives late.
function seedPendingChangeAndParkedComment() {
  const text0 = 'The api session reduced p95 latency by 40%.\n';
  const from = text0.indexOf('reduced');
  const text1 = text0.replace('reduced', 'cut');
  fs.writeFileSync(note, text1);
  recordAgentEdit(vault, note, text0, { from, to: from + 'reduced'.length, insert: 'cut' }, 'api', 1000, SID_API);
  const storePath = storePathFor(vault, note);
  const live = loadStore(storePath, text1);
  assert.equal(live.suggestions.length, 1, 'seed: one pending change');
  fs.writeFileSync(`${storePath}.superseded`, JSON.stringify({
    v: 3,
    path: 'report.md',
    suggestions: [],
    comments: [{
      id: 'C1', author: 'you', ts: 900, body: 'Which latency figure is this?', replies: [], resolved: true,
      anchor: { quote: 'p95 latency', prefix: 'session cut ', suffix: ' by 40%.' },
    }],
    detached: [],
  }, null, 2));
  return { text1, storePath };
}

// ── P1: a reply into a parked comment keeps the live sidecar's changes ──

test('P1 track-reply: replying into a comment only the park holds keeps the pending change', () => {
  const { text1, storePath } = seedPendingChangeAndParkedComment();
  const r = cli('track-reply', ['--file', note, '--thread', 'C1', '--note', 'The p95 over the last week.']);
  assert.equal(r.status, 0, r.stderr);
  const store = loadStore(storePath, text1);
  assert.equal(store.suggestions.length, 1, 'the api session\'s pending change survives the reply');
  assert.equal(store.suggestions[0].author, 'api');
  const c1 = store.comments.find((c) => c.id === 'C1');
  assert.ok(c1, 'the parked comment is revived into the live store');
  assert.equal(c1.resolved, false);
  assert.equal(c1.replies.length, 1);
  assert.equal(c1.replies[0].author, 'web');
  assert.equal(c1.replies[0].authorId, SID_WEB);
  assert.equal(fs.readFileSync(note, 'utf8'), text1, 'a reply never touches the file');
});

test('P1 track-edit --thread: an edit answering a parked comment keeps its own op and the earlier one', () => {
  const { storePath } = seedPendingChangeAndParkedComment();
  const r = cli('track-edit', ['--file', note, '--old', 'p95 latency', '--new', 'tail latency', '--thread', 'C1']);
  assert.equal(r.status, 0, r.stderr);
  const text2 = fs.readFileSync(note, 'utf8');
  assert.equal(text2, 'The api session cut tail latency by 40%.\n');
  const store = loadStore(storePath, text2);
  assert.deepEqual(store.suggestions.map((s) => s.author).sort(), ['api', 'web'],
    'both the earlier change and the one just recorded are pending');
  const c1 = store.comments.find((c) => c.id === 'C1');
  assert.ok(c1, 'the parked comment is revived into the live store');
  assert.equal(c1.resolved, false);
  assert.equal(c1.replies.length, 1);
  assert.equal(c1.replies[0].kind, 'edit');
  assert.equal(c1.replies[0].oldText, 'p95 latency');
  assert.equal(c1.replies[0].newText, 'tail latency');
  const web = store.suggestions.find((s) => s.author === 'web');
  assert.equal(c1.suggestionId, web.id, 'the comment binds to the op that answered it');
});

test('P1 track-reply: with no live store the park still seeds a fresh one (unchanged path)', () => {
  const { text1, storePath } = seedPendingChangeAndParkedComment();
  fs.unlinkSync(storePath);   // the review closed: only the park remains
  const r = cli('track-reply', ['--file', note, '--thread', 'C1', '--note', 'Still here.']);
  assert.equal(r.status, 0, r.stderr);
  const store = loadStore(storePath, text1);
  assert.deepEqual(store.suggestions, []);
  assert.equal(store.comments.length, 1);
  assert.equal(store.comments[0].replies[0].body, 'Still here.');
});

test('P1 track-reply: an unknown id with no park fails and leaves the sidecar bytes alone', () => {
  const { storePath } = seedPendingChangeAndParkedComment();
  fs.unlinkSync(`${storePath}.superseded`);
  const before = fs.readFileSync(storePath);
  const r = cli('track-reply', ['--file', note, '--thread', 'NOPE', '--note', 'Anyone?']);
  assert.equal(r.status, 1);
  assert.match(r.stderr, /No thread found/);
  assert.ok(fs.readFileSync(storePath).equals(before), 'a failed reply writes nothing');
});

// ── P2: track-edit refuses a file that is not text, and writes nothing ──

function trackFile(rel) {
  const dir = path.join(vault, '.trackchanges');
  fs.mkdirSync(dir, { recursive: true });
  const cfgPath = path.join(dir, 'config.json');
  const cfg = fs.existsSync(cfgPath) ? JSON.parse(fs.readFileSync(cfgPath, 'utf8')) : { v: 2, tracked: [] };
  cfg.tracked.push(rel);
  fs.writeFileSync(cfgPath, JSON.stringify(cfg));
}

function assertRefusedUntouched(r, file, before, why) {
  assert.equal(r.status, 1, `expected a refusal, got exit ${r.status}: ${r.stdout}`);
  assert.match(r.stderr, /Refusing to edit/);
  assert.match(r.stderr, why);
  assert.match(r.stderr, /Nothing was written/);
  assert.ok(fs.readFileSync(file).equals(before), 'the file bytes are unchanged');
  assert.equal(fs.existsSync(storePathFor(vault, file)), false, 'no sidecar is created');
}

test('P2 track-edit refuses an image by name and leaves it byte for byte', () => {
  const png = path.join(vault, 'figure.png');
  const bytes = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0, 0, 0, 0x0d, 0x49, 0x48, 0x44, 0x52]);
  fs.writeFileSync(png, bytes);
  trackFile('figure.png');
  const r = cli('track-edit', ['--file', png, '--old', 'IHDR', '--new', 'IHDX']);
  assertRefusedUntouched(r, png, bytes, /\.png is not a text format/);
});

test('P2 track-edit refuses to CREATE an image or a PDF', () => {
  for (const name of ['new-figure.png', 'summary.PDF']) {
    const f = path.join(vault, name);
    const r = cli('track-edit', ['--file', f, '--old', '', '--new', 'not really an image']);
    assert.equal(r.status, 1, r.stdout);
    assert.match(r.stderr, /is not a text format/);
    assert.equal(fs.existsSync(f), false, `${name} is not created`);
  }
});

test('P2 track-edit refuses a binary under a text-looking name by its NUL bytes', () => {
  const dat = path.join(vault, 'weights.dat');
  const bytes = Buffer.from([0x68, 0x65, 0x61, 0x64, 0x00, 0x00, 0x74, 0x61, 0x69, 0x6c]);   // "head", two NULs, "tail"
  fs.writeFileSync(dat, bytes);
  trackFile('weights.dat');
  const r = cli('track-edit', ['--file', dat, '--old', 'head', '--new', 'HEAD']);
  assertRefusedUntouched(r, dat, bytes, /NUL byte/);
});

test('P2 track-edit refuses a file whose bytes are not valid UTF-8', () => {
  const txt = path.join(vault, 'legacy.txt');
  const bytes = Buffer.from([0x63, 0x61, 0x66, 0xe9, 0x0a]);   // "café" in latin-1: 0xe9 alone is not UTF-8
  fs.writeFileSync(txt, bytes);
  trackFile('legacy.txt');
  const r = cli('track-edit', ['--file', txt, '--old', 'caf', '--new', 'CAF']);
  assertRefusedUntouched(r, txt, bytes, /invalid UTF-8/);
});

test('P2 track-edit still edits text, and keeps a UTF-8 BOM and non-ASCII text intact', () => {
  const bom = path.join(vault, 'notes.md');
  fs.writeFileSync(bom, '\uFEFFThe café reopens — p95 latency fell.\n');
  trackFile('notes.md');
  const r = cli('track-edit', ['--file', bom, '--old', 'reopens', '--new', 'reopened']);
  assert.equal(r.status, 0, r.stderr);
  assert.equal(fs.readFileSync(bom, 'utf8'), '\uFEFFThe café reopened — p95 latency fell.\n');
  const store = loadStore(storePathFor(vault, bom), fs.readFileSync(bom, 'utf8'));
  assert.equal(store.suggestions.length, 1);
  assert.equal(store.suggestions[0].newText, 'reopened');
});

// ── P7: the skill forbids a Bash write to a tracked file and asks for the comments folder in the commit ──
//
// Prose, so the pin is the text (patch 0007; plans/file-review.md decisions 47 and 48). Each
// phrase is absent from the pristine skill and present with the patch.

const SKILL = fs.readFileSync(path.join(VENDOR, 'skill', 'SKILL.md'), 'utf8').replace(/\s+/g, ' ');

test('P7 the skill says a tracked file is never written through Bash either, naming the shell forms, and that every write goes through track-edit', () => {
  const section = SKILL.slice(SKILL.indexOf('## When tracking is ON'), SKILL.indexOf('## Messages from the editor'));
  assert.ok(section.includes('Nor through Bash'), 'the rule opens the section, before the CLI bullets');
  for (const form of ['`cp`', '`mv`', '`tee`', '`>`', '`>>`', 'heredoc', '`sed -i`', '`perl -i`', 'python', 'node']) {
    assert.ok(section.includes(form), `the rule names ${form}`);
  }
  assert.ok(section.includes('Every write to a tracked file goes through `track-edit`'));
});

test('P7 the skill says to check track-config\'s exit code as a step of its own, never in a compound command with the write', () => {
  const section = SKILL.slice(SKILL.indexOf('## When tracking is ON'), SKILL.indexOf('## Messages from the editor'));
  assert.ok(section.includes('as a step of its own, never in a compound command with the write'));
  // why: its exit status is 0 for ON, so `track-config ... && cp ...` copies exactly when it must not
  assert.ok(section.includes('`track-config ... && cp ...`'), 'the shape the dry run saw, with the reason');
  assert.ok(section.includes('exactly the file it must not touch'));
});

test('P7 the skill asks the agent to include the .trackchanges/ folder in a commit of its work when the project has one and does not ignore it', () => {
  const notes = SKILL.slice(SKILL.indexOf('## Notes'));
  assert.ok(notes.includes('When you commit work in a project that has a `.trackchanges/` folder and does not ignore it, include that folder in the commit'));
  assert.ok(notes.includes('it holds the user\'s comments on your files and the record of your tracked changes'));
});


// ── P8: one writer per sidecar: the CLIs take store-io's lock around their load-to-rename ──
//
// Patch 0008 adds withStoreLock to store-io.mjs and has track-edit, track-comment and track-reply
// take it; a lock held past the wait fails with one plain line and nothing written, and a failure
// inside the locked region releases the lock (fail() throws to the entry point instead of exiting
// on the spot). The waiting itself, against the host and against a mid-write holder, is driven in
// tools/file-comments-host-store-lock.test.mjs.

function cliAsync(name, args) {
  return new Promise((resolve, reject) => {
    const base = { ...process.env };
    for (const k of ['TRACKCHANGES_ROOT', 'TRACKCHANGES_SESSION', 'ROMP_SID', 'ROMP_SESSION_NAME']) delete base[k];
    const child = spawn(process.execPath, [path.join(VENDOR, 'cli', `${name}.mjs`), ...args],
      { env: { ...base, ROMP_SESSION_NAME: 'web', ROMP_SID: SID_WEB } });
    let stdout = '';
    let stderr = '';
    child.stdout.setEncoding('utf8'); child.stdout.on('data', (c) => { stdout += c; });
    child.stderr.setEncoding('utf8'); child.stderr.on('data', (c) => { stderr += c; });
    child.on('error', reject);
    child.on('close', (status) => resolve({ status, stdout, stderr }));
    child.stdin.end();
  });
}

test('P8 a lock held past the wait: track-edit, track-comment and track-reply each print one plain line, exit 1 and write nothing', async () => {
  const { text1, storePath } = seedPendingChangeAndParkedComment();
  const before = fs.readFileSync(storePath);
  const lockPath = storeLockPathFor(storePath);
  fs.writeFileSync(lockPath, `${process.pid} ${Date.now()}\n`, { flag: 'wx' });
  const t0 = Date.now();
  let results;
  try {
    results = await Promise.all([
      cliAsync('track-edit', ['--file', note, '--old', 'p95 latency', '--new', 'tail latency']),
      cliAsync('track-comment', ['--file', note, '--anchor', 'p95 latency', '--note', 'Which figure?']),
      cliAsync('track-reply', ['--file', note, '--thread', 'C1', '--note', 'The p95 over the last week.']),
    ]);
  } finally {
    fs.unlinkSync(lockPath);
  }
  assert.ok(Date.now() - t0 >= STORE_LOCK_WAIT_MS, 'each waited out the bound before giving up');
  for (const r of results) {
    assert.equal(r.status, 1, r.stdout);
    assert.equal(r.stderr, 'another editor is writing this file; retry\n');
    assert.equal(r.stdout, '');
  }
  assert.ok(fs.readFileSync(storePath).equals(before), 'the sidecar is untouched');
  assert.equal(fs.readFileSync(note, 'utf8'), text1, 'the note is untouched');
});

test('P8 a failure inside the locked region releases the lock and leaves no folder made for it', () => {
  // an existing sidecar: --old not found fails after the lock was taken
  const { storePath } = seedPendingChangeAndParkedComment();
  const r = cli('track-edit', ['--file', note, '--old', 'no such text', '--new', 'x']);
  assert.equal(r.status, 1);
  assert.match(r.stderr, /--old text not found/);
  assert.equal(fs.existsSync(storeLockPathFor(storePath)), false, 'the lock is released on the failure');
  // a fresh vault with no .trackchanges/ yet: the folder made for the lock goes with the refusal
  const fresh = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-vendor-patches-fresh-'));
  try {
    fs.mkdirSync(path.join(fresh, '.obsidian'));
    const n2 = path.join(fresh, 'note.md');
    fs.writeFileSync(n2, 'A line.\n');
    const r2 = cli('track-comment', ['--file', n2, '--anchor', 'missing span', '--note', 'Where?']);
    assert.equal(r2.status, 1);
    assert.match(r2.stderr, /Anchor text not found/);
    assert.equal(fs.existsSync(path.join(fresh, '.trackchanges')), false, 'a refused first comment leaves no .trackchanges/ behind');
    const r3 = cli('track-comment', ['--file', n2, '--anchor', 'A line', '--note', 'Where?']);
    assert.equal(r3.status, 0, r3.stderr);
    assert.ok(fs.existsSync(storePathFor(fresh, n2)), 'a landed one keeps the folder and the sidecar');
    assert.equal(fs.existsSync(storeLockPathFor(storePathFor(fresh, n2))), false);
  } finally {
    fs.rmSync(fresh, { recursive: true, force: true });
  }
});
