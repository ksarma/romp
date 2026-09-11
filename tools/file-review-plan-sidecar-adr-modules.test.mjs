// The Tests bullet under "The sidecar lock and the clocks" and decision 49 in plans/file-review.md, held on
// two gaps the slice's review found in its third round (2026-09-11):
//   * the records' inventory pin (tools/file-review-plan-sidecar-records.test.mjs) sweeps the test modules
//     whose text cites decision 49 or 50 of the plan. The second round's module for the ADR's lock bullet,
//     tools/0002-file-comments-in-the-track-changents-sidecar-lock-names.test.mjs, cites the ADR and not the
//     decision, so it landed in the commit that built the sweep with the plan naming it nowhere. Held here
//     by name, whatever a module cites: every test module under tools/ named for an ADR
//     (`<NNNN>-<adr slug>-<what>.test.mjs`, the ADR in docs/adr/) is named in the Tests bullet and in decision
//     49, and what the bullet says of the lock-names module is read from that module and from store-io.
//   * the second round's prose recorded the track-comment race as run on "one note" with its replies posted
//     to "one thread", two words CONTEXT.md's File comment entry sets aside (a note goes with one send, a
//     thread is a forked side session anchored to the chat) and that the plan binds itself against
//     (its terminology paragraph; decision 17). Held here: neither record uses either word outside a code
//     span, and the race is recorded on a file, its replies on a comment.
// Synthetic: only the repo's text.
// Run: node --test tools/file-review-plan-sidecar-adr-modules.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const SELF = 'tools/file-review-plan-sidecar-adr-modules.test.mjs';
const RECORDS_PIN = 'tools/file-review-plan-sidecar-records.test.mjs';
const LOCK_NAMES = 'tools/0002-file-comments-in-the-track-changents-sidecar-lock-names.test.mjs';
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');

const plan = read('plans', 'file-review.md');
const context = read('CONTEXT.md');
const storeIo = read('vendor', 'track-changents', 'store-io.mjs');

function between(doc, from, to) {
  const a = doc.indexOf(from);
  assert.ok(a >= 0, `${JSON.stringify(from)} not found`);
  const b = doc.indexOf(to, a + from.length);
  assert.ok(b > a, `${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return doc.slice(a, b).replace(/\s+/g, ' ');
}
const d49 = between(plan, '49. **One writer per sidecar at a time**', '50. **');
const testsBullet = between(plan, '- The sidecar lock and the clocks (2026-09-11, decisions 49 and 50)', '\n## Docs');
// A record's prose: its text with the code spans taken out, so a flag or a path is not read as a word.
const prose = (s) => s.replace(/`[^`]*`/g, '');

// One constant's value as store-io defines it, so a rename there fails here and not silently.
function constant(name) {
  const m = new RegExp(`^const ${name} = '([^']+)';`, 'm').exec(storeIo);
  assert.ok(m, `store-io defines ${name}`);
  return m[1];
}

// The test modules under tools/ named for an ADR: `<NNNN>-<slug>-<what>.test.mjs` where docs/adr/<NNNN>-<slug>.md
// is in the tree. A number with no ADR behind it is a failure, not a module passed over.
function adrNamedModules() {
  const adrs = fs.readdirSync(path.join(REPO, 'docs', 'adr')).map((f) => /^(\d{4})-(.+)\.md$/.exec(f)).filter(Boolean)
    .map((m) => ({ number: m[1], slug: m[2] }));
  return fs.readdirSync(path.join(REPO, 'tools')).map((f) => /^(\d{4})-(.+)\.test\.mjs$/.exec(f)).filter(Boolean)
    .map((m) => {
      const adr = adrs.find((a) => a.number === m[1]);
      assert.ok(adr, `tools/${m[0]} is numbered like an ADR and docs/adr/ has no ${m[1]}-*.md`);
      assert.ok(m[2].startsWith(`${adr.slug}-`), `tools/${m[0]} is named for ADR ${adr.number} but not by its slug (${adr.slug})`);
      return `tools/${m[0]}`;
    });
}

test('every test module named for an ADR is named in the Tests bullet and in decision 49 by its name, whatever it cites', () => {
  const modules = adrNamedModules();
  assert.ok(modules.includes(LOCK_NAMES), `the lock-names module is among them: ${modules.join(', ')}`);
  for (const m of modules) {
    assert.ok(fs.existsSync(path.join(REPO, m)), `${m} is in the tree`);
    assert.ok(testsBullet.includes(`\`${m}\``), `the Tests bullet names ${m}`);
    assert.ok(d49.includes(`\`${m}\``), `decision 49 names ${m}`);
  }
  // the premise: the records pin's sweep admits a module by what it cites, which is what left the ADR's module out
  const recordsPin = read(...RECORDS_PIN.split('/'));
  assert.ok(recordsPin.includes('const CITES = /\\bdecisions? (?:49|50)\\b/;'), 'the records pin sweeps by a citation of decision 49 or 50');
  assert.ok(recordsPin.includes("t.includes('file-review.md')"), 'and by the plan\'s name');
  assert.ok(testsBullet.includes('That scan goes by citation, and the ADR\'s module cites the ADR and not the decision'), 'the bullet says so');
  assert.ok(testsBullet.includes(`\`${SELF}\` holds every module named for an ADR`), 'and names this pin as the one that holds them by name');
  assert.ok(d49.includes(`\`${SELF}\` the ADR-named modules to the Tests bullet and to this record by name`), 'decision 49 names this pin too');
});

test('what the bullet and decision 49 say of the lock-names module is read from that module and from store-io', () => {
  const module = read(...LOCK_NAMES.split('/'));
  const LOCK = constant('STORE_LOCK_SUFFIX');
  const BREAK = constant('STORE_LOCK_BREAK_SUFFIX');
  const HANDOVER = constant('STORE_LOCK_HANDOVER');
  // the bullet names the ADR, the two names and the line as store-io defines them
  const about = between(testsBullet, `\`${LOCK_NAMES}\``, `\`${RECORDS_PIN}\``);
  assert.ok(about.includes('`docs/adr/0002`'), 'the bullet names the ADR the module is for');
  assert.ok(module.includes("read('docs', 'adr', '0002-file-comments-in-the-track-changents-sidecar.md')"), 'the module reads that ADR');
  for (const n of [`\`<name>${LOCK}\``, `\`<name>${LOCK}${BREAK}\``, `\`${HANDOVER}\``]) assert.ok(about.includes(n), `the bullet names ${n}`);
  for (const c of ['STORE_LOCK_SUFFIX', 'STORE_LOCK_BREAK_SUFFIX', 'STORE_LOCK_HANDOVER']) assert.ok(module.includes(`constant('${c}')`), `the module reads ${c} from store-io`);
  assert.ok(about.includes('held to the constants `store-io.mjs` defines'));
  // the four cases the bullet describes are the module's four tests
  assert.ok(module.includes("test('the bullet names the two names the lock leaves, as store-io defines them, and no third"), 'the names');
  assert.ok(module.includes("test('the bullet names the handover line as store-io writes it, and says whose file it lands in'"), 'the line');
  assert.ok(about.includes('the lock run in a scratch root'));
  assert.ok(module.includes("test('a live claim beside a dead lock governs the waiter, under the second name; a dead claim goes with the break, and the write sees the lock alone'"), 'the claim');
  assert.ok(about.includes('a live claim beside a dead lock governs the waiter and a dead claim goes with the break, the write seeing the lock alone'));
  assert.ok(module.includes("test('the maker of the folder writes the line into a real holder\\'s lock at release, and that holder removes the folder at its own'"), 'the handover');
  assert.ok(about.includes('the maker of the folder writes the line into a real holder\'s lock, which that holder honors at its own release'));
  // the round the bullet credits is the module's own header (its comment lines, read as one line)
  const header = module.split('\n').filter((l) => l.startsWith('//')).map((l) => l.replace(/^\/\/ ?/, '')).join(' ');
  assert.ok(about.includes('the second round\'s module for the ADR\'s lock bullet'));
  assert.ok(header.includes('Review round 2 (2026-09-11): round 1 added the claim and the handover line and the bullet still said one file.'), header);
  assert.ok(about.includes('which the first round had left naming one file'));
  // decision 49 credits the ADR's bullet to it beside the enumeration claim the two share
  assert.ok(d49.includes(`The two names and that line are everything the lock leaves under \`.trackchanges/\` (\`tools/store-io-lock.test.mjs\`; the ADR's lock bullet, \`docs/adr/0002\`, is held to the same names and line and to the lock run in a scratch root by \`${LOCK_NAMES}\`)`));
  const adr = read('docs', 'adr', '0002-file-comments-in-the-track-changents-sidecar.md');
  assert.ok(between(adr, '- Since 2026-09-11 one transient file', '- A romp-only field').includes('everything the lock leaves under `.trackchanges/`'), 'the ADR makes the same claim');
});

test('neither record uses the two words the glossary sets aside for a file comment outside a code span; the race is recorded on a file, its replies on a comment', () => {
  // the premise: CONTEXT.md's File comment entry lists both under Avoid, and the plan binds itself to that glossary
  const entry = /^\*\*File comment\*\*:\n([\s\S]*?)(?=\n\n)/m.exec(context);
  assert.ok(entry, 'CONTEXT.md has the File comment entry');
  const at = entry[1].indexOf('_Avoid_:');
  assert.ok(at >= 0, 'the entry has an Avoid line');
  const avoid = entry[1].slice(at + '_Avoid_:'.length).replace(/\([^)]*\)/g, '').split(',').map((w) => w.trim()).filter(Boolean);
  for (const w of ['thread', 'note']) assert.ok(avoid.includes(w), `File comment avoids "${w}" (${avoid.join(', ')})`);
  assert.ok(plan.includes('Terminology, as pinned in `CONTEXT.md`: a **file comment** is the object (never "thread", which in\nromp is a forked side session anchored to the chat)'), 'the terminology paragraph');
  assert.ok(plan.includes('17. **The object is a file comment** (2026-09-06), never a thread'), 'decision 17');
  // the records
  for (const [name, record] of [['the Tests bullet', testsBullet], ['decision 49', d49]]) {
    const text = prose(record);
    assert.doesNotMatch(text, /\bthreads?\b/i, `${name} calls a comment with its replies a comment, not by the forked side session's word`);
    assert.doesNotMatch(text, /\bnotes?\b/i, `${name} calls a file a file, not by the send's word`);
  }
  assert.ok(testsBullet.includes('`tools/track-comment-race.test.mjs` (six real `track-comment` processes on one file at one instant, the first round on a root with no `.trackchanges/` yet: every comment lands and the folder holds the sidecar alone; three comments and three replies to one earlier comment at once; the source: the save inside the lock)'));
  assert.ok(d49.includes('`tools/track-comment-race.test.mjs` six real `track-comment` processes on one file at one instant, every comment landing'));
  // and the module runs what the records say: six processes at one instant over rounds, and replies beside comments
  const race = read('tools', 'track-comment-race.test.mjs');
  assert.ok(race.includes('test(`six real track-comment processes on one'), 'the six-process case');
  assert.ok(race.includes('three comments and three replies'), 'the replies-beside-comments case');
  assert.ok(testsBullet.includes('the two words `CONTEXT.md` sets aside under File comment (the forked side session\'s and the send\'s paragraph\'s) appear in neither record'), 'the bullet states the rule without either word');
  assert.ok(d49.includes(`\`${SELF}\` the ADR-named modules to the Tests bullet and to this record by name, and both records to the glossary's words for a file and a comment`));
});
