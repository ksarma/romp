// The vendored README's row for patch 0008 (vendor/track-changents/README.md, the Patches table) is
// the fork's own index of what the patch does, and the record a reader of the vendored copy opens
// before the patch header. The sidecar slice's review (2026-09-11) found the row naming `<sidecar>.lock`
// alone after its first round added the breakers' claim (`<sidecar>.lock.break`) and its second the
// folder handover (a `made-dir` line appended to another writer's lock or claim), which the patch
// header, docs/adr/0002 and decision 49 all named. Held here to the code the way the ADR bullet is
// (tools/0002-file-comments-in-the-track-changents-sidecar-lock-names.test.mjs): the names and the
// line as store-io defines them, read from its source, must all be in the row, the row may list no
// name the code does not leave, the row's account of the folder is checked against store-io's make
// and remove sites, and the row, the patch header and the ADR bullet must list one set of names, so
// a rename in the code or a name added to one record fails here rather than going stale in the
// README. Synthetic: only the repo's own text.
// Run: node --test tools/README-track-changents-patch-0008-row.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');

const readme = read('vendor', 'track-changents', 'README.md');
const storeIo = read('vendor', 'track-changents', 'store-io.mjs');
const adr = read('docs', 'adr', '0002-file-comments-in-the-track-changents-sidecar.md');

const PATCH_DIR = path.join(REPO, 'vendor', 'track-changents', 'patches');
const patches = fs.readdirSync(PATCH_DIR).filter((f) => f.startsWith('0008-'));
assert.equal(patches.length, 1, 'one patch 0008');
const patchName = patches[0];
const header = fs.readFileSync(path.join(PATCH_DIR, patchName), 'utf8').split('\ndiff --git ')[0];

// The row is one table line: found by its first cell, and the only line that begins with it.
const rows = readme.split('\n').filter((l) => l.startsWith(`| \`${patchName}\``));
assert.equal(rows.length, 1, 'the README has one row for patch 0008');
const row = rows[0];

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
const NAMES = [LOCK, LOCK + BREAK].sort();

function between(doc, from, to) {
  const a = doc.indexOf(from);
  assert.ok(a >= 0, `${JSON.stringify(from)} not found`);
  const b = doc.indexOf(to, a + from.length);
  assert.ok(b > a, `${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return doc.slice(a, b).replace(/\s+/g, ' ');
}
const bullet = between(adr, '- Since 2026-09-11 one transient file', '- A romp-only field');

// Every `<placeholder>.suffix` name a record puts in backticks, by suffix.
const namesIn = (text, placeholder) =>
  [...new Set([...text.matchAll(new RegExp(`\`<${placeholder}>(\\.[\\w.]+)\``, 'g'))].map((m) => m[1]))].sort();

test('the row keeps its shape: one table line of three cells, whose second cell says not yet', () => {
  assert.equal(row.split('|').length, 5, 'a leading and a trailing pipe around three cells');
  assert.match(row, /^\| `0008-[a-z0-9-]+\.patch` \| not yet \(/, 'the second cell the plan test pins');
  assert.ok(row.endsWith(' |'));
});

test('the row names both names the lock leaves, as store-io defines them, and no third', () => {
  for (const n of NAMES) assert.ok(row.includes(`\`<sidecar>${n}\``), `the row names \`<sidecar>${n}\``);
  assert.deepEqual(namesIn(row, 'sidecar'), NAMES, 'the row lists exactly the names the code leaves');
  for (const n of NAMES) assert.match(`docs%2Freport.md.json${n}`, NAME_RE, `store-io counts ${n} among the names the lock leaves`);
  assert.ok(row.includes('a second transient name beside it'), 'the claim is a second name, for the break only');
  assert.ok(row.includes('the claim the breakers serialize on'), 'the row says what the second name is for');
  assert.ok(row.includes('leaves three things under `.trackchanges/`, and nothing else'), 'the row claims to be the whole inventory');
});

test('the row names the handover line as store-io writes it, whose file it lands in, and the folder it hands over', () => {
  assert.ok(row.includes(`one line, \`${HANDOVER}\`, appended to another writer's lock or claim`), `the row names \`${HANDOVER}\` and where it lands`);
  assert.ok(row.includes('the one thing the lock writes into a file it did not create'));
  assert.ok(row.includes('makes the `.trackchanges/` folder when a first write finds none'), 'the folder is made for a first write');
  assert.ok(row.includes('the maker removes it again at release when nothing else landed in it'), 'and removed by its maker');
  assert.ok(row.includes('a refused first write leaves no trace'));
  assert.ok(row.includes('appends the line to each of them instead'), 'the folder is handed to every lock or claim in it');
  assert.ok(row.includes('take the folder away at their own release, the last one out removing it'), 'the writers handed the folder remove it');
  assert.match(storeIo, /for \(const n of names\) \{\s*const on = handOverDir\(path\.join\(dir, n\)\);/, 'removeDirUnlessUsed hands the folder to each name in it');
  // the code does each: one make site that marks the maker, one guarded remove, one append of the line
  assert.match(storeIo, /fs\.mkdirSync\(dir\); ownsDir = true;/, 'the lock makes the folder and marks itself its maker');
  assert.match(storeIo, /try \{ fs\.rmdirSync\(dir\); return; \} catch \(e\) \{ if \(!e \|\| e\.code !== 'ENOTEMPTY'\) return; \}/, 'the folder is removed only while empty');
  assert.match(storeIo, /function handOverDir\(p\) \{[\s\S]*?fs\.writeFileSync\(fd, `\$\{STORE_LOCK_HANDOVER\}\\n`\)/, 'the line is appended by handOverDir');
  assert.equal((storeIo.match(/STORE_LOCK_HANDOVER\}\\n`/g) || []).length, 1, 'one append site');
});

test('the row, the patch header and the ADR bullet list one set of names and the one line', () => {
  assert.deepEqual(namesIn(header, 'sidecar'), NAMES, 'the patch header names the same two names');
  assert.ok(header.includes(`"${HANDOVER}" line`), 'the patch header names the line');
  assert.deepEqual(namesIn(bullet, 'name'), NAMES, 'the ADR bullet names the same two names');
  assert.ok(bullet.includes(`\`${HANDOVER}\``), 'the ADR bullet names the line');
  assert.ok(bullet.includes('the two names and the line are everything the lock leaves under `.trackchanges/`'));
});
