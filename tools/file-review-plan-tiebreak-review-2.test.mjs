// The tie-break's review, second round (2026-09-11): the record behind the slice (plans/file-review.md: the host
// paragraph, the contract, the painting paragraph, the anchors follow-on note, the Tests and Docs sections, decision 51)
// lagged the first round's fixes in four places, and this module holds each corrected sentence to the code that makes
// it true.
//   * The host paragraph and the Tests section said a comment whose copy-field stamp the budget refuses is skipped
//     "with no note"; the first round had added noteUnstamped, which tells stderr how many stamps were refused, once
//     per write, after the comments without fields are stamped first. The record now says so.
//   * Decision 51 said a comment the CLI made "carries neither until the next host write stamps it". A CLI comment on a
//     recurring passage ties with no position (track-comment stores 24 characters of context and checks no
//     uniqueness), the refresh never seats a hintless tie, and the stamping pass walks the seated comments alone, so
//     no host write stamps it while the tie holds. The record now says so, and this module walks it on the real host:
//     the tied CLI comment through three host writes beside a unique-passage control that is stamped on the first,
//     then the tie dissolved by a raw write and the next write seating and stamping it.
//   * The definition of `section` omitted the heading cap (SECTION_HEADING_CAP, a first-round change) and how the
//     file's kind is judged (from its name, never the sidecar JSON's `path` field, another).
//   * The panel's first-round changes (Reveal on a guessed copy's card; a confirmed place the view's text moved past
//     said in its own words, PanelCard.confirmedAt), the guide's reworded sentence and the first round's three test
//     modules were absent from the record.
// Hermetic, the file-comments-host-tiebreak.test.mjs way: the synthetic notes-api world under a scratch directory, the
// host as a child process, the real vendored CLI where the session did something, a raw write where the person did.
// Synthetic fixtures only: the repo's own text and the tie-break tests' invented report.
// Run: node --test tools/file-review-plan-tiebreak-review-2.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

import { sectionAt, locateStored, isMarkdownPath, SECTION_HEADING_CAP, ANCHOR_CTX_CAP } from './file-comments-host.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST = path.join(REPO, 'tools', 'file-comments-host.mjs');
const VENDOR = path.join(REPO, 'vendor', 'track-changents');
const engine = createRequire(import.meta.url)(path.join(VENDOR, 'engine.js'));
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');
const exists = (...parts) => fs.existsSync(path.join(REPO, ...parts));

const plan = read('plans', 'file-review.md');
const host = read('tools', 'file-comments-host.mjs');
const panel = read('ui', 'webview', 'file-comments.ts');
const guide = read('docs', 'guide.md').replace(/\s+/g, ' ');

// The text between two headings, hard wraps collapsed so an assertion survives a rewrap.
function section(from, to) {
  const a = plan.indexOf(from);
  assert.ok(a >= 0, `heading ${JSON.stringify(from)} not found in the plan`);
  const b = plan.indexOf(to, a + from.length);
  assert.ok(b > a, `heading ${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return plan.slice(a, b).replace(/\s+/g, ' ');
}
const contract = section('## The contract: the track-changents sidecar', '## Kernel: two ops and a host script');
const op = section('## Kernel: two ops and a host script', '## UX');
const ux = section('### Commenting from either view, and in every format', '### The viewer seam');
const note = section('### Slice 2: the session', '### Slice 3: region comments on images');
const tests = section('## Tests', '## Docs');
const docs = section('## Docs', '## Deliberately not in v1');
const decisions = section('## Decisions (the user, 2026-09-05 and 2026-09-06)', '## Open questions for the user');
const decision51 = decisions.slice(decisions.indexOf('51. **'));

// A function's source, from its `function name(` to the first line that is a lone closing brace.
function fn(src, name) {
  const a = src.indexOf(`function ${name}(`);
  assert.ok(a >= 0, `${name} is defined`);
  const b = src.indexOf('\n}\n', a);
  assert.ok(b > a, `${name} closes`);
  return src.slice(a, b);
}

// ── the world (file-comments-host-tiebreak.test.mjs's) ──────────────
const SID = '11111111-2222-3333-4444-555555555555';
let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-fc-tiebreak-r2-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

const PARA = ('The quick brown fox jumps over the lazy dog. '.repeat(12)
  + 'Here is the marker phrase to comment on. '
  + 'Pack my box with five dozen liquor jugs. '.repeat(12)).trim();
const MARKER = 'the marker phrase';
assert.ok(PARA.indexOf(MARKER) > ANCHOR_CTX_CAP && PARA.length - PARA.indexOf(MARKER) - MARKER.length > ANCHOR_CTX_CAP,
  'the fixture: the phrase sits more than the cap from both ends of its paragraph');
const OPENING = '# Report\n\nA short opening line that occurs once.\n\n';
const TIED = `${OPENING}## First pass\n\n${PARA}\n\n## Second pass\n\n${PARA}\n\n## Third pass\n\n${PARA}\n`;
const ONE = `${OPENING}## First pass\n\n${PARA}\n`;
const UNIQUE = 'opening line that occurs once';

let worlds = 0;
function world() {
  const home = path.join(SCRATCH, `w${++worlds}`, 'home');
  const root = path.join(home, 'notes-api');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  fs.mkdirSync(path.join(root, 'docs'));
  fs.writeFileSync(path.join(root, 'docs', 'tied.md'), TIED);
  return { home, root, tied: path.join(root, 'docs', 'tied.md') };
}
function env(w, extra) {
  const e = { ...process.env, FILE_COMMENTS_HOME: w.home, ...(extra || {}) };
  delete e.TRACKCHANGES_ROOT;
  if (!extra || !('ROMP_SID' in extra)) { delete e.ROMP_SID; delete e.ROMP_SESSION_NAME; }
  return e;
}
function hostCall(w, req) {
  const r = spawnSync(process.execPath, [HOST], { input: JSON.stringify(req), encoding: 'utf8', env: env(w) });
  let json = null;
  try { json = JSON.parse(r.stdout); } catch { json = null; }
  return { code: r.status, stdout: r.stdout, stderr: r.stderr, json };
}
function ok(w, req) {
  const r = hostCall(w, req);
  assert.equal(r.code, 0, `exit ${r.code}: ${r.stderr}`);
  assert.ok(r.json && r.json.ok === true, `expected ok:true, got ${r.stdout}`);
  assert.equal(r.json.verb, req.verb);
  assert.ok(!r.stderr.includes('kept the copy fields'), `no stamp was refused for the budget: ${r.stderr}`);
  return r.json;
}
function cliOk(w, name, args) {
  const r = spawnSync(process.execPath, [path.join(VENDOR, 'cli', `track-${name}.mjs`), ...args],
    { encoding: 'utf8', env: env(w, { ROMP_SESSION_NAME: 'web', ROMP_SID: SID }) });
  assert.equal(r.status, 0, `track-${name} failed: ${r.stderr}`);
  return r;
}
function status(w, file) { return ok(w, { verb: 'status', path: file, args: {} }); }
function fenceFor(st) { return { storeMtimeNs: st.storeMtimeNs == null ? '' : st.storeMtimeNs }; }
function comment(w, file, args) { return ok(w, { verb: 'comment', path: file, args, fence: fenceFor(status(w, file)) }); }
function readSidecar(sp) { return JSON.parse(fs.readFileSync(sp, 'utf8')); }
const FIELDS = ['anchorAt', 'ordinal', 'copies', 'section'];
const fieldsOf = (c) => Object.keys(c).filter((k) => FIELDS.includes(k));
const copyFields = (c) => [c.ordinal, c.copies, c.section];

// ── the stamp's note ────────────────────────────────────────────────

test('the host paragraph and the Tests section say a refused stamp is told on stderr once per write, the fieldless comments stamped first, and no longer "with no note"; the host stamps in that order and notes after the loop', () => {
  assert.ok(op.includes("and past the budget the remaining comments keep their position and stderr says how many, once per write, and a comment whose stamp the budget refuses keeps the fields it has, or none, and stderr says how many of those, once per write; and a stored comment's anchor is located with its `anchorAt` as the hint. The comments without the fields are stamped before the rest, so a sidecar with more distinct anchors than one write scans gains fields where it has none before it refreshes the fields it has (`noteUnstamped` is the note; the review's first round, 2026-09-11: before it the skip was silent, and a comment past the budget never gained the fields)."));
  assert.ok(!op.includes('with no note'), 'the host paragraph no longer calls the skip silent');
  assert.ok(tests.includes("charged to the budget, and past it keeps the fields it has while stderr says how many, once per write (the stamping pass of `refreshAnchorAts`, `noteUnstamped`, `fullMatches`'s memo), and a tie with no position is settled by the fields before it is refused (`locateStored`)."));
  assert.ok(!tests.includes('with no note'), 'the Tests section no longer calls the skip silent');
  // the host: the fieldless comments first, the loop, the count of refusals, the note; none of it inside the loop
  const refresh = fn(host, 'refreshAnchorAts');
  const sortAt = refresh.indexOf('seated.sort((a, b) => Number(stampedAlready(a)) - Number(stampedAlready(b)));');
  const loopAt = refresh.indexOf('for (const c of seated) {');
  const countAt = refresh.indexOf('budget.unstamped = seated.filter((c) => stampRefused(text, c.anchor)).length;');
  const noteAt = refresh.indexOf('noteUnstamped(budget);');
  assert.ok(sortAt >= 0 && loopAt > sortAt && countAt > loopAt && noteAt > countAt, 'the comments without the fields first, the stamping loop, the count, then the note');
  const noted = fn(host, 'noteUnstamped');
  assert.ok(noted.includes('if (budget.unstamped === budget.keptUnstamped) return;'), 'once per write: the process is one verb, and the second pass tells nothing new');
  assert.ok(noted.includes("process.stderr.write(`file-comments-host: ${budget.unstamped} comment(s) kept the copy fields they had, or none: counting the copies of their passage would scan past the refresh's budget for one write\\n`);"), 'the note names the count and the reason');
});

// ── the CLI comment on a recurring passage ──────────────────────────

test('decision 51 says no host write stamps a CLI comment on a recurring passage while its tie holds, that the next write after the tie dissolves does, and that a unique one was never refused; the refresh skips a hintless tie before any seating', () => {
  assert.ok(decision51.includes('a comment the CLI made on a passage that recurs with the same 24 characters around it (the context the CLI stores) carries neither and is refused as before; no host write stamps it while the tie holds, since the refresh stamps only a comment it seats and never seats a tie with no position, and the next host write after an edit leaves its passage at one place seats and stamps it, as it stamps a CLI comment on a unique passage, which was never refused'));
  assert.ok(!decision51.includes('until the next host write stamps it'), 'the sentence that promised a stamp the tied comment never gets is gone');
  assert.ok(!decision51.includes('\u2014'), 'decision 51 has no em dash');
  const refresh = fn(host, 'refreshAnchorAts');
  const several = refresh.indexOf('if (hits.length >= 1) {');
  const skip = refresh.indexOf('if (at === undefined) continue;', several);
  const seatFrom = refresh.indexOf('seated.push(c)', several);
  assert.ok(several >= 0 && skip > several && seatFrom > skip, 'a comment with no position whose whole anchor sits at several places is skipped before any seating in that branch');
  assert.ok(refresh.indexOf('if (hits.length === 1 && at === undefined) { c.anchorAt = hits[0]; seated.push(c); continue; }') < several, 'one whole place seats a hintless comment: how the tie dissolving stamps it');
  const cli = read('vendor', 'track-changents', 'cli', 'track-comment.mjs');
  assert.ok(cli.includes('function makeAnchor(text, from, to, ctx = 24)') && cli.includes('const idx = text.indexOf(anchorQuote);'), 'the CLI: 24 characters of context, the first occurrence, no uniqueness check');
});

test('on the real host: a track-comment on the recurring passage keeps the contract\'s keys alone through a comment, a reply and a resolve, with no verdict and no note, while one on the unique line is stamped on the first write; a raw write leaving one copy has the next write seat and stamp it', () => {
  const w = world();
  cliOk(w, 'comment', ['--file', w.tied, '--anchor', MARKER, '--note', 'On the marker, says the session.']);
  cliOk(w, 'comment', ['--file', w.tied, '--anchor', UNIQUE, '--note', 'Once, says the session.']);
  let st = status(w, w.tied);
  const sp = st.storePath;
  const [tied, unique] = readSidecar(sp).comments;
  assert.deepEqual(Object.keys(tied), ['id', 'author', 'authorId', 'ts', 'anchor', 'body', 'replies', 'resolved'], 'the CLI writes the contract\'s shape alone');
  assert.deepEqual(fieldsOf(unique), []);
  assert.equal(tied.anchor.prefix.length, 24, 'the CLI\'s context');
  assert.deepEqual(locateStored(TIED, tied, true), { error: 'anchor-ambiguous' }, 'a hintless tie with no fields: refused');
  assert.deepEqual(st.placed, {}, 'no verdict for a refused comment (nor for the unique one, which the anchor alone places)');
  // three host writes: a comment on the unique line, a reply on the tied comment itself, a resolve of it
  const u = { idx: TIED.indexOf(UNIQUE) };
  u.anchor = engine.makeAnchor(TIED, u.idx, u.idx + UNIQUE.length);
  const r1 = comment(w, w.tied, { anchor: u.anchor, note: 'Once more.', hintOffset: u.idx });
  st = status(w, w.tied);
  const r2 = ok(w, { verb: 'reply', path: w.tied, args: { commentId: tied.id, note: 'A reply on the tied one.' }, fence: fenceFor(st) });
  st = status(w, w.tied);
  const r3 = ok(w, { verb: 'resolve', path: w.tied, args: { commentId: tied.id, on: true }, fence: fenceFor(st) });
  for (const [i, r] of [r1, r2, r3].entries()) {
    const after = readSidecar(r.storePath).comments;
    const t = after.find((c) => c.id === tied.id);
    assert.deepEqual(fieldsOf(t), [], `write ${i + 1}: the tied CLI comment gained no position and no copy fields`);
    assert.equal(r.placed[tied.id], undefined, `write ${i + 1}: and has no verdict, refused as before`);
    const q = after.find((c) => c.id === unique.id);
    assert.equal(q.anchorAt, u.idx, `write ${i + 1}: the unique CLI comment was seated`);
    assert.deepEqual(copyFields(q), [1, 1, 'Report'], `write ${i + 1}: and stamped`);
  }
  assert.equal(readSidecar(r3.storePath).comments.find((c) => c.id === tied.id).resolved, true, 'the resolve landed');
  // the person's raw write leaves the passage at one place: a read still rewrites nothing, the next write seats and stamps
  fs.writeFileSync(w.tied, ONE);
  st = status(w, w.tied);
  assert.deepEqual(fieldsOf(readSidecar(sp).comments.find((c) => c.id === tied.id)), [], 'a read never rewrites the sidecar');
  assert.equal(st.placed[tied.id], undefined, 'one whole place: the anchor alone places it, no verdict to carry');
  const r4 = ok(w, { verb: 'resolve', path: w.tied, args: { commentId: tied.id, on: false }, fence: fenceFor(st) });
  const seated = readSidecar(r4.storePath).comments.find((c) => c.id === tied.id);
  assert.equal(seated.anchorAt, ONE.indexOf(MARKER), 'seated at the one copy');
  assert.deepEqual(copyFields(seated), [1, 1, 'Report > First pass'], 'and stamped 1 of 1 under its heading');
  assert.deepEqual(r4.placed, {}, 'nothing tied any more');
});

// ── the heading cap and the file's kind ─────────────────────────────

test('decision 51 and the contract state the heading cap and the file\'s kind from its name; the host caps by code point at the read the stamp shares and judges the kind from the name it stamped on the store', () => {
  assert.ok(decision51.includes("Each heading's text in the path is cut at 200 characters (`SECTION_HEADING_CAP`, by code point, at the stamp and the read alike, so two headings alike for that long are one path"));
  assert.ok(decision51.includes("the headings are read as the viewer renders the file (a leading BOM, CRLF line ends, a front-matter block by the viewer's own test in `md-config.ts`), and whether the file is markdown is judged from the file's name, `.md` or `.markdown`, at every stamp and every read, never from the sidecar's own `path` field"));
  assert.ok(contract.includes("each heading's text cut at 200 characters, `SECTION_HEADING_CAP`, joined with \" > \"; empty for a file without headings or a non-markdown file, the file's kind judged from its name, `.md` or `.markdown`, never from the sidecar's own `path` field"));
  assert.equal(SECTION_HEADING_CAP, 200);
  // a heading of 211 code points, the cut inside a run of astral characters; a twin alike for the first 200
  const long = 'H'.repeat(150) + ' ' + '\u{1F600}'.repeat(60);
  const twin = 'H'.repeat(150) + ' ' + '\u{1F600}'.repeat(80);
  const capped = Array.from(long).slice(0, 200).join('');
  assert.equal(Array.from(capped).length, 200);
  assert.notEqual(long, twin);
  const text = `# ${long}\n\nUnder the long heading.\n\n## ${twin}\n\nUnder its twin.\n`;
  assert.equal(sectionAt(text, text.indexOf('Under the long'), true), capped, 'cut by code point: no split surrogate');
  assert.equal(sectionAt(text, text.indexOf('Under its twin'), true), `${capped} > ${capped}`, 'two headings alike for the cap are one path each');
  assert.equal(sectionAt(text, text.indexOf('Under the long'), false), '', 'a non-markdown file has no heading path');
  assert.ok(fn(host, 'stampCopy').includes('c.section = sectionAt(text, at, markdown);'), 'the stamp reads through the same cap');
  assert.ok(isMarkdownPath('/x/notes.md') && isMarkdownPath('/x/notes.markdown') && !isMarkdownPath('/x/notes.txt'));
  assert.ok(host.includes("const MARKDOWN_FILE = Symbol('romp.markdownFile');"), 'the judgment rides on the store under a symbol');
  assert.ok(fn(host, 'refreshAnchorAts').includes('const markdown = markdownOf(store);') && !host.includes('isMarkdownPath(store'), 'the refresh takes the stamped judgment, never the sidecar JSON\'s path');
  const heads = fn(host, 'headings');
  assert.ok(heads.includes("endsWith('\\r')") && heads.includes('0xFEFF') && heads.includes('frontMatterLines('), 'CRLF, the BOM, the front-matter block');
});

// ── the panel's first round ─────────────────────────────────────────

test('the painting paragraph, the note and decision 51 record the guessed card\'s Reveal and the confirmed place the view moved past; the panel offers that Reveal on a guessed copy alone and names the place in the words', () => {
  assert.ok(ux.includes("A passage comment's guessed copy has its card offer the Reveal those words name (the review's first round, 2026-09-11; before it the card offered Reveal only for a passage it could not paint, and named a button it did not have): it switches to Raw and scrolls to the guessed copy, and its title says that a comment saved from the copy you mean is placed on that copy and this one keeps its tag until you resolve it."));
  assert.ok(ux.includes("A confirmed place the view's text has moved past (the poll's reload paints before the fresh status lands; a refused refresh keeps the old status) paints the copy nearest that place as a guess whose words name the confirmed place (`confirmedAt`), never plainly on a copy the host did not vouch for in the text shown."));
  assert.ok(note.includes('whose words on the card end with "Reveal it and save again from the right copy to confirm." and whose card offers that Reveal (the review\'s first round, 2026-09-11).'));
  assert.ok(decision51.includes("A passage comment's guessed copy has its card offer the Reveal those words name (the review's first round: before it the card offered Reveal only for a passage it could not paint, so the words named a button the card did not have); it switches to Raw and scrolls to the guessed copy, and its title says that a comment saved from the copy you mean is placed on that copy and this one keeps its tag until you resolve it"));
  assert.ok(decision51.includes('paints the copy nearest that place as a guess whose words name the confirmed place (`confirmedAt`), never plainly on a copy the host did not vouch for in the text shown.'));
  // the panel: Reveal for an unpainted passage, else for a guessed copy, with the title the record states
  const a = panel.indexOf('if (c.anchor && loc && loc.range && !loc.painted) {');
  const b = panel.indexOf('} else if (', a);
  assert.ok(a >= 0 && b > a, 'Reveal for an unpainted passage, else...');
  const cond = panel.slice(b, panel.indexOf('{', b));
  assert.ok(cond.includes('c.anchor') && cond.includes('this.unsureCopies.has(c.id)'), '...for a guessed copy of a passage comment');
  const branch = panel.slice(b, panel.indexOf('acts.appendChild(rv);', b));
  assert.ok(branch.includes('const rv = btn("Reveal", "fcreveal"); rv.dataset.id = c.id;'), 'the same control, the same action');
  assert.ok(branch.includes('"Show this copy in the Raw view"'), 'the title names the Raw view');
  const saveWords = 'a comment saved from the copy you mean is placed on that copy, and this one keeps its tag until you resolve it';
  assert.ok(branch.includes(saveWords) || (branch.includes('SAVE_FROM_COPY') && panel.includes(`const SAVE_FROM_COPY = "${saveWords}";`)), 'the title says what the save does, as the record states it');
  assert.ok(panel.includes('type PanelCard = Card & { confirmedAt?: number };'));
  const words = fn(panel, 'copyUnsureWords');
  assert.ok(words.includes('c.confirmedAt !== undefined') && words.includes("the place where the comment's copy was last confirmed names none of the copies as the file is now, so the copy nearest that place is highlighted"), 'the words name the confirmed place');
  assert.ok(words.includes('", not a confirmed one. Reveal it and save again from the right copy to confirm."'), 'and still end by asking for the save');
});

// ── the Docs section, the guide and the modules ─────────────────────

test('the Docs section records the guide\'s tie-break sentences and the modules that hold them, and the guide carries them; the first round\'s modules the record names exist and are named in the note, the Tests section and decision 51; no em dash in the new sentences', () => {
  assert.ok(docs.includes("With the tie-break (2026-09-11), that a comment on text which occurs more than once is placed again by its own record of where it was, which copy it is and the heading above it when the file has changed around that occurrence, that when none of those can tell the copy shown is a guess and the card says so, and that saving the comment again from the right copy adds a new card on that copy with no tag while the old card keeps its tag until you resolve it"));
  assert.ok(docs.includes('`tests/test_guide_files_comments_anchors.py` holds the first two to the panel and the ADR, `tests/test_guide_files_comments_confirm.py` the last to the panel and the real host'));
  assert.ok(guide.includes("When the file has changed around that occurrence, the comment's own record of where it was, which copy it is and the heading above it places it again. When none of those can tell which copy the comment meant, its highlight is dashed and the card carries a **passage recurs** tag: the copy shown is a guess, and the card says so."));
  assert.ok(guide.includes('Saving the comment again from the right copy, as the card asks, adds a new card on that copy with no tag; the old card keeps its tag, so resolve it once the new one is saved.'));
  for (const m of ['tools/file-comments-host-tiebreak-review.test.mjs', 'ui/webview/file-comments-tiebreak-recourse.test.ts', 'tests/test_guide_files_comments_confirm.py', 'tools/file-review-plan-tiebreak-review.test.mjs', 'tools/file-review-plan-tiebreak-review-2.test.mjs']) {
    assert.ok(exists(...m.split('/')), `${m} exists`);
    for (const [name, text] of [['decision 51', decision51], ['the note', note], ['the Tests section', tests]]) assert.ok(text.includes(`\`${m}\``), `${name} names ${m}`);
  }
  const docsSentence = docs.slice(docs.indexOf('With the tie-break (2026-09-11)'), docs.indexOf('`docs/reference.md`'));
  const testsSentences = tests.slice(tests.indexOf('`tools/file-review-plan-tiebreak-review.test.mjs` holds'), tests.indexOf('`tools/file-review-plan-attribution.test.mjs`'));
  for (const [name, text] of [['decision 51', decision51], ['the Docs sentence', docsSentence], ['the Tests sentences', testsSentences]]) {
    assert.ok(text.length > 0, `${name} found`);
    assert.ok(!text.includes('\u2014'), `${name} has no em dash`);
  }
});
