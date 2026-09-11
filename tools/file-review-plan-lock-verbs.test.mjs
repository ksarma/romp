// The host paragraph of plans/file-review.md claims store-io's lock for the verbs that REWRITE a
// store (the sidecar or config.json), the eight decision 49 names, and says the two verbs that only
// append to the comments log hold none. This holds that claim to the host's verb table: the eight
// route through withSidecar, decideUnderLock or doSetTracked (the only functions that call
// underStoreLock); status, log-edit and log-send call none of them; the log is opened for append and
// written an entry at a time, never renamed over, so it has no load-to-rename for a lock to serialize;
// and nothing vendored names the log, so the host script is its one writer. Before the sidecar
// slice's review (2026-09-11) the sentence said every verb that writes holds the lock, which the two
// log verbs never did.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');

const plan = read('plans', 'file-review.md');
const host = read('tools', 'file-comments-host.mjs');

function between(doc, from, to) {
  const a = doc.indexOf(from);
  assert.ok(a >= 0, `found: ${from}`);
  const b = doc.indexOf(to, a + from.length);
  assert.ok(b > a, `found after it: ${to}`);
  return doc.slice(a, b).replace(/\s+/g, ' ');
}
const hostPara = between(plan, '**The host script** (`tools/file-comments-host.mjs`', '**`fileCommentsSend`**');
const d49 = between(plan, '49. **One writer per sidecar at a time**', '50. **');
const testsBullet = between(plan, '- The sidecar lock and the clocks (2026-09-11, decisions 49 and 50)', '\n## Docs');

// one function's source: its `function name(` line to the next column-0 `}`
function fn(src, name) {
  let i = src.indexOf(`\nfunction ${name}(`);
  if (i < 0) i = src.indexOf(`\nexport function ${name}(`);
  assert.ok(i >= 0, `${name} is defined`);
  return src.slice(i, src.indexOf('\n}\n', i) + 3);
}
const LOCKERS = ['withSidecar', 'decideUnderLock', 'doSetTracked'];
const holdsLock = (src) => LOCKERS.some((n) => src.includes(`${n}(`)) || src.includes('underStoreLock(');

// the verb table: `verb: handler` or `'verb': (ctx) => handler(ctx, ...)`
const table = between(host, '\nconst HANDLERS = {', '\n};');
function handlerOf(verb) {
  const m = new RegExp(`(?:^|[ {])'?${verb}'?: (?:\\(ctx\\) => )?(do[A-Za-z]+)`).exec(table);
  assert.ok(m, `the verb table names ${verb}`);
  return m[1];
}

const SIDECAR_VERBS = ['comment', 'reply', 'resolve', 'retarget', 'accept', 'reject', 'save'];
const CONFIG_VERB = 'set-tracked';
const APPEND_ONLY = ['log-edit', 'log-send'];

test('the host paragraph scopes the lock to the verbs that rewrite a store, the eight decision 49 names', () => {
  assert.ok(hostPara.includes('Every verb that rewrites the sidecar or `config.json` (`comment`, `reply`, `resolve`, `retarget`, `accept`, `reject` and `save` the sidecar; `set-tracked` the config) holds store-io\'s lock on the file it rewrites, from its fence stat through its last rename or prune'));
  assert.equal(hostPara.includes('Every verb that writes holds'), false, 'the over-claim is gone');
  assert.ok(d49.includes('the sidecar\'s for `comment`, `reply`, `resolve`, `retarget`, `accept`, `reject` and `save`; `config.json`\'s own for `set-tracked`'), 'the same eight in decision 49');
  assert.ok(hostPara.includes('`log-edit` and `log-send`, which only append to the comments log, hold none, since the log is appended an entry at a time by the host script alone and never rewritten'));
  assert.ok(testsBullet.includes('`tools/file-review-plan-lock-verbs.test.mjs`'), 'the Tests bullet names this module');
  assert.ok(testsBullet.includes('the eight verbs route through the lock, `status`, `log-edit` and `log-send` take none, the log is appended an entry at a time and never rewritten, and nothing vendored names it'));
});

test('the eight verbs route through the lock and the others do not', () => {
  for (const verb of SIDECAR_VERBS) {
    const src = fn(host, handlerOf(verb));
    assert.ok(holdsLock(src), `${verb} holds the lock`);
    assert.equal(src.includes('paths.configPath, '), false, `${verb} locks the sidecar, not config.json`);
  }
  const toggle = fn(host, handlerOf(CONFIG_VERB));
  assert.ok(toggle.includes('underStoreLock(ctx, paths.configPath,'), 'set-tracked locks config.json');
  for (const verb of ['status', ...APPEND_ONLY]) {
    assert.equal(holdsLock(fn(host, handlerOf(verb))), false, `${verb} takes no lock`);
  }
  // no other function reaches the lock: every call site sits inside one of the three
  const sites = [...host.matchAll(/(?<!function )underStoreLock\(ctx,/g)].map((m) => m.index);
  assert.ok(sites.length >= 3, 'the lock is called');
  for (const i of sites) {
    const owner = LOCKERS.find((n) => {
      const start = host.indexOf(`\nfunction ${n}(`);
      return start >= 0 && i >= start && i < start + fn(host, n).length;
    });
    assert.ok(owner, `the underStoreLock call at offset ${i} is inside withSidecar, decideUnderLock or doSetTracked`);
  }
  // the verb table carries exactly the eleven verbs this test sorts, so a new verb lands here first
  const named = [...table.matchAll(/(?:^|[ {])'?([a-z-]+)'?: /g)].map((m) => m[1]).sort();
  assert.deepEqual(named, ['accept', 'accept-all', 'comment', 'log-edit', 'log-send', 'reject', 'reject-all', 'reply', 'resolve', 'retarget', 'save', 'set-tracked', 'status']);
});

test('the log verbs append an entry at a time, and the host script is the log\'s one writer', () => {
  for (const verb of APPEND_ONLY) {
    const src = fn(host, handlerOf(verb));
    assert.ok(src.includes('appendLog(paths.logPath,'), `${verb} appends`);
    assert.equal(/writeFileAtomic|writeStore|renameSync/.test(src), false, `${verb} rewrites nothing`);
  }
  assert.match(fn(host, 'openLog'), /c\.O_WRONLY \| c\.O_APPEND \| c\.O_CREAT/, 'the log is opened for append');
  const append = fn(host, 'appendLog');
  assert.ok(append.includes('openLog(logPath, true)'));
  assert.equal(/rename|writeFile|truncate|ftruncate/.test(append), false, 'appendLog only writes at the end');
  // the suffix the host names the log by appears nowhere in the vendored engine or CLIs
  const suffix = /export const LOG_SUFFIX = '([^']+)';/.exec(host);
  assert.ok(suffix, 'LOG_SUFFIX is defined');
  const vendored = path.join(REPO, 'vendor', 'track-changents');
  const walk = (dir) => fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const p = path.join(dir, e.name);
    return e.isDirectory() ? walk(p) : /\.(m?js)$/.test(e.name) ? [p] : [];
  });
  for (const file of walk(vendored)) {
    assert.equal(fs.readFileSync(file, 'utf8').includes(suffix[1]), false, `${path.relative(REPO, file)} never names the comments log`);
  }
});
