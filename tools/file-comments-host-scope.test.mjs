// Pins for tools/file-comments-host.mjs from the Slice 5 review, round 3 (plans/file-review.md,
// "Security posture", "Consent, trace, routing", Slice 2 and Slice 5): the scope of what the host
// writes, by name and by record.
//   * reject and reject-all keep Slice 2's scope: every tracked file that is UTF-8 text, whatever its
//     name. The viewer's text allowlist (TEXT_EXT, TEXT_NAMES — the kernel's _is_text_path) bounds
//     `save`, which writes the client's content; reject writes back only what the sidecar recorded,
//     so a session's change in a .tex or .hs file — a card the panel shows — is rejected from the
//     dashboard as it was before Slice 5, while a save of the same file refuses `not-text`.
//   * `save` takes no change record the sidecar never held: fitRecords checks each record against
//     `content` only and rebuilds it from the id, author, authorId, ts and oldText the client sent, so
//     an unrooted record would enter the sidecar as a change the session it names never made — and
//     the next save or the panel's Reject would find it pending, log a decision on it, count it to
//     the session and (for a planted deletion) INSERT its oldText into the file. Such a record refuses
//     `desync` by id and nothing is written; the records a real editor produces — the seeded ones, the
//     engine's `<id>~n` splits, a record the undo of a landed accept put back — still land.
// Same hermetic harness as file-comments-host-save-guards.test.mjs: the synthetic `notes-api` world
// under a scratch directory, the script driven as the kernel drives it, changes recorded by the REAL
// vendored track-edit, the editor's remap done with the engine's own calls.
// Run: node --test tools/file-comments-host-scope.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

import { writeTrackedPaths } from '../vendor/track-changents/store-io.mjs';
import { logPathFor, isTextPath } from './file-comments-host.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST = path.join(REPO, 'tools', 'file-comments-host.mjs');
const VENDOR = path.join(REPO, 'vendor', 'track-changents');
const FIX = path.join(REPO, 'tests', 'fixtures', 'file_comments');
const engine = createRequire(import.meta.url)(path.join(VENDOR, 'engine.js'));

const SID = '11111111-2222-3333-4444-555555555555';

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-fc-host-scope-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

let worlds = 0;
function world() {
  const home = path.join(SCRATCH, `w${++worlds}`, 'home');
  const root = path.join(home, 'notes-api');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  fs.mkdirSync(path.join(root, 'docs'));
  fs.mkdirSync(path.join(root, 'src'));
  fs.copyFileSync(path.join(FIX, 'report.md'), path.join(root, 'docs', 'report.md'));
  return { home, root, report: path.join(root, 'docs', 'report.md'), text: fs.readFileSync(path.join(FIX, 'report.md'), 'utf8') };
}

function env(w, extra) {
  const e = { ...process.env, FILE_COMMENTS_HOME: w.home, ...(extra || {}) };
  delete e.TRACKCHANGES_ROOT;
  if (!extra || !('ROMP_SID' in extra)) { delete e.ROMP_SID; delete e.ROMP_SESSION_NAME; }
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
  assert.equal(r.json.error.includes(w.home), false, `home path leaked: ${r.json.error}`);
  assert.deepEqual(Object.keys(r.json).sort(), ['code', 'error', 'ok']);
  return r.json;
}
function crashed(w, req, re) {
  const r = host(w, req);
  assert.equal(r.code, 2, `expected a BadRequest crash, got exit ${r.code}: ${r.stdout}`);
  assert.match(r.stderr, re);
  assert.equal(r.stdout, '');
}
function cliOk(w, name, args) {
  const r = spawnSync(process.execPath, [path.join(VENDOR, 'cli', `track-${name}.mjs`), ...args],
    { encoding: 'utf8', env: env(w, { ROMP_SESSION_NAME: 'web', ROMP_SID: SID }) });
  assert.equal(r.status, 0, `track-${name} failed: ${r.stderr}`);
  return r;
}
function status(w, file) { return ok(w, { verb: 'status', path: file, args: {} }); }
function fenceFor(st) { return { storeMtimeNs: st.storeMtimeNs == null ? '' : st.storeMtimeNs }; }
function fileFenceFor(st) { return { ...fenceFor(st), fileMtimeNs: st.fileMtimeNs }; }
function edit(w, file, oldText, newText) {
  cliOk(w, 'edit', ['--file', file, '--old', oldText, '--new', newText]);
  return status(w, file);
}
function recordFor(st, id) {
  const s = st.store.suggestions.find((x) => String(x.id) === String(id));
  assert.ok(s, `no record ${id}`);
  return s;
}
function saveReq(file, st, content, suggestions, accepted, rejected) {
  return { verb: 'save', path: file, args: { content, suggestions, accepted: accepted || [], rejected: rejected || [] }, fence: fileFenceFor(st) };
}
const decision = (h) => ({ id: h.id, oldText: h.oldText, newText: h.newText });
// What the editor's field does when the person types: every record mapped through the change.
function typed(text, records, from, to, insert) {
  return { content: text.slice(0, from) + insert + text.slice(to), records: engine.ingestHumanChanges(records, [{ from, to, insert }]) };
}
function readSidecar(sp) { return JSON.parse(fs.readFileSync(sp, 'utf8')); }
function fileBytes(p) { try { return fs.readFileSync(p); } catch { return null; } }
function readLogLines(lp) { return fs.readFileSync(lp, 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l)); }
function snapshot(file, storePath) {
  return { file, storePath, fileBytes: fileBytes(file), sidecar: fileBytes(storePath), log: fileBytes(logPathFor(storePath)) };
}
function untouched(before) {
  assert.deepEqual(fileBytes(before.file), before.fileBytes, 'the file is untouched');
  assert.deepEqual(fileBytes(before.storePath), before.sidecar, 'the sidecar is untouched');
  assert.deepEqual(fileBytes(logPathFor(before.storePath)), before.log, 'the log is untouched');
}
// The finding's planted record: a change by the session, in the session's name, that the session
// never made — its newText is text already in `content` (so it fits), its oldText the client's.
function planted(id, content, word, oldText) {
  const from = content.indexOf(word);
  assert.ok(from >= 0, `${word} is in the text`);
  return { id, author: 'web', authorId: SID, ts: 1700000000000, kind: 'sub', from, newText: word, oldText, anchor: null };
}

// ── reject keeps Slice 2's scope: any tracked UTF-8 file, whatever its name ─────

test('reject and reject-all put the old text back in a tracked file whose name is outside the viewer\'s text allowlist, as before Slice 5; save on the same file refuses not-text before any write', () => {
  const w = world();
  // Two names the viewer serves download-only (TEXT_EXT has neither): a LaTeX source and a Haskell
  // module. The CLIs record changes in both; the panel shows the change cards for both.
  const tex = path.join(w.root, 'docs', 'notes.tex');
  const hs = path.join(w.root, 'src', 'Main.hs');
  for (const p of [tex, hs]) assert.equal(isTextPath(p), false, `${path.basename(p)} is outside the viewer's text scope`);
  fs.writeFileSync(tex, 'Hello world.\n');
  fs.writeFileSync(hs, 'main = putStrLn "hello"\n');
  writeTrackedPaths(w.root, ['docs/notes.tex', 'src/Main.hs']);
  // reject-all on the .tex file: the session's change is reverted, the record dropped, the decision logged.
  const st = edit(w, tex, 'world', 'there');
  assert.equal(fs.readFileSync(tex, 'utf8'), 'Hello there.\n');
  assert.deepEqual(st.hunks.map((h) => [h.oldText, h.newText]), [['world', 'there']]);
  const r = ok(w, { verb: 'reject-all', path: tex, args: {}, fence: fileFenceFor(st) });
  assert.equal(fs.readFileSync(tex, 'utf8'), 'Hello world.\n', 'the old text is back');
  assert.deepEqual(r.rejected, [st.hunks[0].id]);
  assert.deepEqual(r.hunks, []);
  assert.deepEqual(r.log.map((e) => e.kind), ['reject']);
  assert.deepEqual(r.log[0].changes, [{ id: st.hunks[0].id, oldText: 'world', newText: 'there' }]);
  assert.equal(r.unsent.rejected, 1);
  assert.equal(r.logged, true);
  assert.equal(r.fileMtimeNs, fs.statSync(tex, { bigint: true }).mtimeNs.toString(), 'the reply carries the write\'s own mtime');
  // reject by id on the .hs file, with a second change left pending and remapped.
  let sh = edit(w, hs, 'hello', 'hi');
  cliOk(w, 'edit', ['--file', hs, '--old', 'main', '--new', 'main2']);
  sh = status(w, hs);
  assert.equal(fs.readFileSync(hs, 'utf8'), 'main2 = putStrLn "hi"\n');
  const hi = sh.hunks.find((h) => h.newText === 'hi');
  const main2 = sh.hunks.find((h) => h.newText === 'main2');
  assert.ok(hi && main2, 'two changes pending');
  const r2 = ok(w, { verb: 'reject', path: hs, args: { ids: [hi.id] }, fence: fileFenceFor(sh) });
  assert.equal(fs.readFileSync(hs, 'utf8'), 'main2 = putStrLn "hello"\n', 'one change reverted, the other kept');
  assert.deepEqual(r2.rejected, [hi.id]);
  assert.deepEqual(r2.hunks.map((h) => [h.id, h.newText]), [[main2.id, 'main2']]);
  assert.deepEqual(readSidecar(r2.storePath).suggestions.map((s) => s.id), [main2.id]);
  assert.deepEqual(r2.log.map((e) => e.kind), ['reject']);
  assert.equal(r2.unsent.rejected, 1);
  // save on the same file: the client's content under a name saveFile would not write it under
  // refuses, in saveFile's phrase, before any read or write. The kernel refuses the same name before
  // this script runs; the script answers the same way so the answer does not depend on the route.
  const sh2 = status(w, hs);
  const before = snapshot(hs, sh2.storePath);
  const rs = refused(w, saveReq(hs, sh2, fs.readFileSync(hs, 'utf8'), sh2.store.suggestions), 'not-text');
  assert.equal(rs.error, 'cannot save ~/notes-api/src/Main.hs: not a text file the viewer edits; nothing was changed');
  untouched(before);
  // And accept, which writes no file, never cared about the name.
  const a = ok(w, { verb: 'accept-all', path: hs, args: {}, fence: fenceFor(sh2) });
  assert.deepEqual(a.accepted, [main2.id]);
  assert.equal(fs.readFileSync(hs, 'utf8'), 'main2 = putStrLn "hello"\n');
});

test('source pin: the name allowlist gates save, not reject', () => {
  const src = fs.readFileSync(HOST, 'utf8');
  const body = (name) => {
    const m = src.match(new RegExp(`\\nfunction ${name}\\([^)]*\\) \\{\\n([\\s\\S]*?)\\n\\}\\n`));
    assert.ok(m, `${name} is defined`);
    return m[1];
  };
  assert.equal(/checkTextPath\(/.test(body('doReject')), false, 'doReject applies no name rule');
  assert.equal(/checkTextPath\(/.test(body('doSave')), true, 'doSave applies saveFile\'s name rule');
  assert.equal(/checkIsText\(/.test(body('doReject')), true, 'doReject still refuses bytes that are not UTF-8');
});

// ── save takes no record the sidecar never held ────────────────────

test('a save whose records include one the sidecar never held refuses desync by id and writes nothing: the planted change never reaches the sidecar, so no later verb can decide it', () => {
  const w = world();
  writeTrackedPaths(w.root, ['docs/report.md']);
  const st = edit(w, w.report, 'cut p95 latency by 40%', 'reduced p95 latency by 35%');
  const cur = fs.readFileSync(w.report, 'utf8');
  const X = st.hunks[0];
  const rec = recordFor(st, X.id);
  const before = snapshot(w.report, st.storePath);
  assert.equal(before.log, null, 'no comments log yet');
  // The finding's save 1: the file's own text, the real record, and a record by `web` the session
  // never made, whose oldText is the client's. Before the fix it was written into the sidecar and
  // status listed it as the session's pending change.
  const ghost = planted('ghost-1', cur, 'response cache', 'PLANTED-BY-CLIENT');
  let r = refused(w, saveReq(w.report, st, cur, [rec, ghost]), 'desync');
  assert.equal(r.error, 'change ghost-1 was never pending in ~/notes-api/docs/report.md: neither the comments file holds it nor the comments log remembers it, so the records being saved are not that file\'s; nothing was changed — reload and retry');
  untouched(before);
  // Nothing the ghost claimed is anywhere: status lists the real change alone, no log exists, and the
  // panel's Reject of the ghost (the finding's save 2, by the other door) finds nothing to decide.
  const st2 = status(w, w.report);
  assert.deepEqual(st2.hunks.map((h) => h.id), [X.id]);
  assert.deepEqual(readSidecar(st.storePath).suggestions.map((s) => s.id), [X.id]);
  assert.deepEqual(st2.unsent, { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null });
  assert.equal(fs.existsSync(logPathFor(st.storePath)), false);
  refused(w, { verb: 'reject', path: w.report, args: { ids: ['ghost-1'] }, fence: fileFenceFor(st2) }, 'no-change');
  const cur2 = cur.replace('response cache', 'PLANTED-BY-CLIENT');
  r = refused(w, saveReq(w.report, st2, cur2, [rec], [], [{ id: 'ghost-1', oldText: 'PLANTED-BY-CLIENT', newText: 'response cache' }]), 'no-change');
  assert.match(r.error, /^change ghost-1 is no longer pending/);
  untouched(before);
  assert.equal(fs.readFileSync(w.report, 'utf8').includes('PLANTED-BY-CLIENT'), false, 'the planted text never reached the file');
  // Several strangers are all named, in the request's order; the real record is not.
  const ghost2 = planted('ghost-2', cur, 'Cold starts', 'ALSO-PLANTED');
  r = refused(w, saveReq(w.report, st2, cur, [ghost2, rec, ghost]), 'desync');
  assert.match(r.error, /^changes ghost-2, ghost-1 were never pending in ~\/notes-api\/docs\/report\.md: /);
  assert.equal(r.error.includes(String(X.id)), false, 'the real record is not named');
  untouched(before);
  // A planted DELETION point is refused the same way. Written, it would be a pending deletion of text
  // that was never there, and the panel's Reject of it would insert its oldText into the file.
  const point = { id: 'd1', author: 'web', authorId: SID, ts: 1700000000000, kind: 'del', from: rec.from + 3, newText: '', oldText: 'gone', anchor: null };
  r = refused(w, saveReq(w.report, st2, cur, [rec, point]), 'desync');
  assert.match(r.error, /^change d1 was never pending/);
  untouched(before);
  // A stranger that does not even fit the text is named as the misfit it is: fitRecords rules first.
  r = refused(w, saveReq(w.report, st2, cur, [rec, { ...ghost, newText: 'not in the text' }]), 'desync');
  assert.match(r.error, /^change ghost-1 does not fit the text being saved/);
  untouched(before);
  // A malformed record beside a stranger is still the caller bug it always was (exit 2), not a refusal.
  crashed(w, saveReq(w.report, st2, cur, [rec, ghost, { author: 'web', from: 0, newText: 'L', oldText: '' }]), /needs a non-empty id/);
  untouched(before);
});

test('the records a real editor produces still land: the seeded records, the engine\'s split fragment, and a record the undo of a landed accept put back in the field', () => {
  const w = world();
  writeTrackedPaths(w.root, ['docs/report.md']);
  let st = edit(w, w.report, 'cut p95 latency by 40%', 'reduced p95 latency by 35%');
  st = ok(w, { verb: 'comment', path: w.report, args: { note: 'Overall fine.' }, fence: fenceFor(st) });   // keeps the sidecar alive past the accept below
  const cur = fs.readFileSync(w.report, 'utf8');
  const X = st.hunks[0];
  const rec = recordFor(st, X.id);
  // (a) The seeded records, remapped through typing outside the change: the same ids.
  const moved = typed(cur, st.store.suggestions, 0, 0, 'Preface.\n');
  assert.deepEqual(moved.records.map((s) => s.id), [X.id]);
  const r1 = ok(w, saveReq(w.report, st, moved.content, moved.records));
  assert.equal(fs.readFileSync(w.report, 'utf8'), moved.content);
  assert.deepEqual(r1.hunks.map((h) => h.id), [X.id]);
  assert.deepEqual(r1.log.map((e) => e.kind), ['edit']);
  // (b) Typing inside the change: the engine splits it into X and X~1, an id the sidecar never held,
  // rooted in X by the split scheme. Both fragments save as pending.
  const at = recordFor(r1, X.id).from + 'reduced '.length;
  const split = typed(moved.content, r1.store.suggestions, at, at, 'the ');
  assert.deepEqual(split.records.map((s) => [s.id, s.newText]), [[X.id, 'reduced '], [`${X.id}~1`, 'p95 latency by 35%']]);
  const r2 = ok(w, { ...saveReq(w.report, r1, split.content, split.records), fence: fileFenceFor(r1) });
  assert.equal(fs.readFileSync(w.report, 'utf8'), split.content);
  assert.deepEqual(r2.hunks.map((h) => h.id), [X.id, `${X.id}~1`]);
  assert.deepEqual(readSidecar(st.storePath).suggestions.map((s) => s.id), [X.id, `${X.id}~1`]);
  // (c) The person accepts both and saves: the sidecar drops them, the log remembers them. Then undo
  // past the landed save puts the records back in the field, and the next save carries them as
  // pending again — rooted by the log alone, since the sidecar no longer holds them.
  const frag = split.records[1];
  const r3 = ok(w, { ...saveReq(w.report, r2, split.content, [], [decision(X), { id: frag.id, oldText: frag.oldText, newText: frag.newText }], []), fence: fileFenceFor(r2) });
  assert.deepEqual(r3.store.suggestions, [], 'accepted: gone from the sidecar');
  assert.equal(r3.store.comments.length, 1, 'the comment keeps the sidecar');
  assert.deepEqual(r3.log.map((e) => e.kind), ['edit', 'edit', 'edit', 'accept']);
  assert.equal(r3.unsent.accepted, 2);
  const r4 = ok(w, { ...saveReq(w.report, r3, split.content, split.records), fence: fileFenceFor(r3) });
  assert.deepEqual(r4.hunks.map((h) => h.id), [X.id, `${X.id}~1`], 'pending again');
  assert.deepEqual(readSidecar(st.storePath).suggestions.map((s) => [s.id, s.author, s.oldText]), [[X.id, rec.author, rec.oldText], [`${X.id}~1`, rec.author, '']]);
  assert.deepEqual(r4.log.map((e) => e.kind), ['edit', 'edit', 'edit', 'accept', 'edit']);
  assert.deepEqual(readLogLines(logPathFor(st.storePath)), r4.log);
  // A stranger beside these is still refused: the roots are the sidecar's and the log's ids, nothing else.
  const before = snapshot(w.report, st.storePath);
  const rg = refused(w, { ...saveReq(w.report, r4, split.content, [...split.records, planted('ghost-9', split.content, 'Cold starts', 'PLANTED')]), fence: fileFenceFor(r4) }, 'desync');
  assert.match(rg.error, /^change ghost-9 was never pending/);
  untouched(before);
});
