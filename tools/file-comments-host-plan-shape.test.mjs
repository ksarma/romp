// The contract's own shape for a region on an embedded figure, read by tools/file-comments-host.mjs
// (plans/file-review.md, "The contract" and Slice 3's acceptance): the embed line's anchor plus
// `target {kind, region, hash}` with NO `src`. The panel always writes `src` (the embed's
// destination as written, which the anchor's quote does not always carry), but a writer following
// the plan leaves the src-less shape, and before this module the host skipped it: no hash on any
// reply, so the panel read "unknown" forever and a regenerated figure never flipped it to stale;
// and the panel's Re-place, which names no src for it, crashed the host as a caller bug. Pinned
// here instead:
//   * every reply on a text file names such a comment's figure from its anchored passage, located
//     now, when that passage embeds exactly one figure: the store the reply carries gets the src
//     (`derivedSrcs` says which, per comment id; the disk is never rewritten by a read) and
//     `embeddedHashes` hashes it, so a regenerated figure reads stale by hash;
//   * a re-place naming no src on it lands: the passage's figure is taken and the written target
//     carries its src and the current hash (a comment WITH a stored src keeps needing the request
//     to name it, as file-comments-host-regions.test.mjs pins: the panel holds that src);
//   * a passage that cannot tell its figure — two figures, none, the passage edited away — is
//     named per comment id in `derivedSrcReasons`, hashed under nothing, and a re-place naming no
//     src on it refuses with the same reason (`no-figure`, or the anchor's code), never a crash;
//   * a reference-style embed's figure is told through its definition; a media file's reply has
//     none of this; a panel-written comment is carried exactly as the disk holds it.
// Same hermetic harness as file-comments-host-targets.test.mjs: the synthetic `notes-api` world
// under a scratch directory, tiny PNGs generated at run time, the script driven as the kernel drives
// it. Run: node --test tools/file-comments-host-plan-shape.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

import { tinyPng, sha256 } from '../tests/fixtures/file_comments/tiny-png.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST = path.join(REPO, 'tools', 'file-comments-host.mjs');
const VENDOR = path.join(REPO, 'vendor', 'track-changents');
const FIX = path.join(REPO, 'tests', 'fixtures', 'file_comments');
const engine = createRequire(import.meta.url)(path.join(VENDOR, 'engine.js'));

const LATENCY = tinyPng(10, 20, 30);
const LATENCY_AGAIN = tinyPng(11, 22, 33);   // the figure regenerated: other bytes, same name
const ERRORS = tinyPng(200, 30, 30);
const CHART = tinyPng(0, 120, 60);

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-fc-host-plan-shape-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

// <scratch>/wN/home/                  FILE_COMMENTS_HOME: "~" in every text the script prints
//   notes-api/.git/                   the landmark that makes notes-api a project
//   notes-api/docs/figures.md         the fixture with embedded figures
//   notes-api/docs/figs/latency.png   embedded twice
//   notes-api/docs/figs/errors.png    embedded once
//   notes-api/docs/chart.png          a standalone image
let worlds = 0;
function world() {
  const home = path.join(SCRATCH, `w${++worlds}`, 'home');
  const root = path.join(home, 'notes-api');
  const docs = path.join(root, 'docs');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  fs.mkdirSync(path.join(docs, 'figs'), { recursive: true });
  fs.copyFileSync(path.join(FIX, 'figures.md'), path.join(docs, 'figures.md'));
  fs.writeFileSync(path.join(docs, 'figs', 'latency.png'), LATENCY);
  fs.writeFileSync(path.join(docs, 'figs', 'errors.png'), ERRORS);
  fs.writeFileSync(path.join(docs, 'chart.png'), CHART);
  return {
    home, root, docs,
    figures: path.join(docs, 'figures.md'),
    figText: fs.readFileSync(path.join(FIX, 'figures.md'), 'utf8'),
    latency: path.join(docs, 'figs', 'latency.png'),
    errors: path.join(docs, 'figs', 'errors.png'),
    chart: path.join(docs, 'chart.png'),
  };
}

function env(w) {
  const e = { ...process.env, FILE_COMMENTS_HOME: w.home };
  delete e.TRACKCHANGES_ROOT;
  delete e.FILE_COMMENTS_HASH_CAP;
  delete e.FILE_COMMENTS_EMBEDDED_HASH_CAP;
  delete e.ROMP_SID;
  delete e.ROMP_SESSION_NAME;
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
  return Object.assign(r.json, { stderr: r.stderr });
}
function refused(w, req, code) {
  const r = host(w, req);
  assert.equal(r.code, 0, `a refusal exits 0; got ${r.code}: ${r.stderr}`);
  assert.ok(r.json && r.json.ok === false, `expected ok:false, got ${r.stdout}`);
  assert.equal(r.json.code, code, r.json.error);
  return r.json;
}
function crashed(w, req, re) {
  const r = host(w, req);
  assert.equal(r.code, 2, `a BadRequest exits 2; got ${r.code} with stdout ${r.stdout}`);
  assert.match(r.stderr, re);
  return r;
}
function status(w, file) { return ok(w, { verb: 'status', path: file, args: {} }); }
function fenceFor(st) { return { storeMtimeNs: st.storeMtimeNs == null ? '' : st.storeMtimeNs }; }
function readSidecar(sp) { return JSON.parse(fs.readFileSync(sp, 'utf8')); }
function writeSidecar(sp, obj) { fs.writeFileSync(sp, JSON.stringify(obj, null, 2) + '\n'); }
function anchorAt(text, quote, nth) {
  let i = -1;
  for (let k = 0; k <= (nth || 0); k++) i = text.indexOf(quote, i + 1);
  assert.ok(i >= 0, `fixture lacks occurrence ${nth} of ${JSON.stringify(quote)}`);
  return { anchor: engine.makeAnchor(text, i, i + quote.length), hintOffset: i };
}
const LATENCY_EMBED = '![p95 latency](figs/latency.png)';
const ERRORS_EMBED = '![error rate](figs/errors.png)';
const REGION = { x: 0.12, y: 0.4, w: 0.35, h: 0.2 };
const REGION2 = { x: 0.5, y: 0.5, w: 0.25, h: 0.1 };
// The panel's request: a region on `file` anchored at the nth occurrence of `quote`, naming its src.
function panelComment(file, text, quote, nth, st, src, note) {
  const { anchor, hintOffset } = anchorAt(text, quote, nth);
  return { verb: 'comment', path: file, fence: fenceFor(st), args: { anchor, hintOffset, note: note || 'On the figure.', target: { kind: 'image', region: REGION, src } } };
}
// The re-place the panel sends for a card whose target carries no src: a target with no src.
function replaceNoSrc(file, st, id, region) {
  return { verb: 'retarget', path: file, fence: fenceFor(st), args: { commentId: id, target: { kind: 'image', region: region || REGION2 } } };
}
// A sidecar rewritten into the contract's shape: the named comments lose their `src`, as another
// writer following the plan leaves them (the panel itself always writes one).
function stripSrc(sp, ids) {
  const disk = readSidecar(sp);
  for (const c of disk.comments) if (!ids || ids.includes(c.id)) delete c.target.src;
  writeSidecar(sp, disk);
  return disk;
}
const reasonLines = (stderr) => stderr.split('\n').filter((l) => l.startsWith('file-comments-host:'));

// ── the figure is told from the embed line, and a regenerated figure reads stale ──────

test('a comment in the contract\'s shape (anchor + {kind, region, hash}, no src) is not "unknown": status tells its figure from the embed line, carries the src in its store and hashes it, without rewriting the disk; a regenerated figure then reads stale by hash', () => {
  const w = world();
  let st = status(w, w.figures);
  const written = ok(w, panelComment(w.figures, w.figText, LATENCY_EMBED, 0, st, 'figs/latency.png'));
  const sp = written.storePath;
  const id = written.store.comments[0].id;
  const disk = stripSrc(sp);
  assert.deepEqual(Object.keys(disk.comments[0].target), ['kind', 'region', 'hash'], 'the contract\'s shape, as the plan spells it');
  const bytes = fs.readFileSync(sp);

  st = status(w, w.figures);
  assert.deepEqual(st.store.comments[0].target, { kind: 'image', region: REGION, hash: sha256(LATENCY), src: 'figs/latency.png' },
    'the reply\'s store carries the src the passage tells, after the stored keys');
  assert.deepEqual(st.store.comments[0].anchor, disk.comments[0].anchor);
  assert.deepEqual(st.derivedSrcs, { [id]: 'figs/latency.png' }, 'the reply says which src is the passage\'s telling, not the disk\'s');
  assert.deepEqual(st.derivedSrcReasons, {});
  assert.deepEqual(st.embeddedHashes, { 'figs/latency.png': sha256(LATENCY) }, 'hashed under the src, so the panel\'s stale check finds it');
  assert.deepEqual(st.embeddedHashReasons, {});
  assert.deepEqual(reasonLines(st.stderr), [], 'nothing to explain');
  assert.deepEqual(fs.readFileSync(sp), bytes, 'a read never rewrites the sidecar');

  // Slice 3's acceptance: the figure regenerated flips the comment to stale by hash.
  fs.writeFileSync(w.latency, LATENCY_AGAIN);
  st = status(w, w.figures);
  assert.equal(st.embeddedHashes['figs/latency.png'], sha256(LATENCY_AGAIN));
  assert.notEqual(st.embeddedHashes['figs/latency.png'], st.store.comments[0].target.hash, 'current hash ≠ stored hash: stale');
  assert.deepEqual(fs.readFileSync(sp), bytes);
});

// ── the panel's re-place lands ──────────────────────────────────────

test('a re-place naming no src — the panel\'s, on a card in the contract\'s shape — lands: the passage\'s figure is taken and the target is written with its src and the current hash; on a comment with a stored src a request must still name it, and another src is still a caller bug', () => {
  const w = world();
  let st = status(w, w.figures);
  let r = ok(w, panelComment(w.figures, w.figText, LATENCY_EMBED, 0, st, 'figs/latency.png'));
  const sp = r.storePath;
  const first = r.store.comments[0];
  st = status(w, w.figures);
  r = ok(w, panelComment(w.figures, w.figText, ERRORS_EMBED, 0, st, 'figs/errors.png', 'On the errors chart.'));
  const second = r.store.comments[1];
  stripSrc(sp, [first.id]);
  fs.writeFileSync(w.latency, LATENCY_AGAIN);   // stale now; the re-place makes it current

  st = status(w, w.figures);
  assert.deepEqual(st.derivedSrcs, { [first.id]: 'figs/latency.png' });
  r = ok(w, replaceNoSrc(w.figures, st, first.id, REGION2));
  const expected = { kind: 'image', region: REGION2, hash: sha256(LATENCY_AGAIN), src: 'figs/latency.png' };
  assert.deepEqual(r.store.comments[0].target, expected, 'written in the contract\'s key order, src last, hash of the bytes as they are now');
  assert.deepEqual(readSidecar(sp).comments[0].target, expected, 'and that is what the disk holds');
  assert.deepEqual(r.store.comments[0].anchor, first.anchor, 'the anchor stays');
  assert.equal(r.store.comments[0].body, first.body);
  assert.deepEqual(r.derivedSrcs, {}, 'nothing left to tell: the src is stored');
  assert.deepEqual(r.embeddedHashes, { 'figs/latency.png': sha256(LATENCY_AGAIN), 'figs/errors.png': sha256(ERRORS) });

  // A comment with a stored src keeps needing the request to name it (the regions test's pin): the
  // panel holds that src, so a request without one is a caller bug, as before this module.
  st = status(w, w.figures);
  const bytes = fs.readFileSync(sp);
  crashed(w, replaceNoSrc(w.figures, st, second.id, REGION2), /needs target\.src/);
  assert.deepEqual(readSidecar(sp).comments[0].target, expected, 'the re-placed comment above, now with a stored src, is held to the same rule');
  crashed(w, replaceNoSrc(w.figures, st, first.id, REGION), /needs target\.src/);
  // A request naming ANOTHER src is a caller bug, as before.
  crashed(w, { verb: 'retarget', path: w.figures, fence: fenceFor(st), args: { commentId: second.id, target: { kind: 'image', region: REGION, src: 'figs/latency.png' } } },
    /retarget keeps the figure: comment \S+ is on figs\/errors\.png, and target\.src names figs\/latency\.png/);
  assert.deepEqual(fs.readFileSync(sp), bytes);
});

// ── a passage that cannot tell its figure is named, not left unknown ─

test('a passage that cannot tell its figure — two figures on it, none, or the passage edited away — is named per comment in derivedSrcReasons and hashed under nothing; a re-place naming no src refuses with that reason, and one naming the figure lands', () => {
  const w = world();
  const md = path.join(w.docs, 'two.md');
  let text = '# Two\n\nBoth charts: ![a](figs/latency.png) ![b](figs/errors.png)\n\nText only line.\n\n![c](figs/errors.png)\n';
  fs.writeFileSync(md, text);
  let st = status(w, md);
  // The whole line with both figures, anchored as one passage; the panel names one of them.
  let r = ok(w, panelComment(md, text, 'Both charts: ![a](figs/latency.png) ![b](figs/errors.png)', 0, st, 'figs/latency.png'));
  const sp = r.storePath;
  const both = r.store.comments[0].id;
  st = status(w, md);
  r = ok(w, panelComment(md, text, '![c](figs/errors.png)', 0, st, 'figs/errors.png', 'On c.'));
  const gone = r.store.comments[1].id;
  // Rewritten into the contract's shape, plus a third comment another writer left on a passage with
  // no figure at all (the panel refuses to create one: figure-mismatch).
  const disk = stripSrc(sp);
  const { anchor } = anchorAt(text, 'Text only line.', 0);
  const none = 'plan-none';
  disk.comments.push({ id: none, author: 'you', ts: Date.now(), anchor, body: 'On nothing.', replies: [], resolved: false, target: { kind: 'image', region: REGION, hash: sha256(ERRORS) } });
  writeSidecar(sp, disk);
  // The passage of the second comment edited under it: the quote changes, its surroundings stay, so
  // the engine relocates it by context and locateExact refuses the relocation as anchor-not-found.
  text = text.replace('![c](figs/errors.png)', '![c](figs/errors-v2.png)');
  fs.writeFileSync(md, text);
  const bytes = fs.readFileSync(sp);

  st = status(w, md);
  assert.equal(st.store.comments.length, 3);
  assert.deepEqual(st.derivedSrcs, {});
  assert.deepEqual(Object.keys(st.derivedSrcReasons).sort(), [both, gone, none].sort());
  assert.match(st.derivedSrcReasons[both], /^the passage of comment \S+ in ~\/notes-api\/docs\/two\.md embeds figs\/latency\.png, figs\/errors\.png, so which figure it is on cannot be told$/);
  assert.match(st.derivedSrcReasons[gone], /^the passage of comment \S+ could not be placed in ~\/notes-api\/docs\/two\.md \(anchor-not-found\), so which figure it is on cannot be told$/);
  assert.match(st.derivedSrcReasons[none], /^the passage of comment plan-none in ~\/notes-api\/docs\/two\.md embeds no figure, so which figure it is on cannot be told$/);
  assert.deepEqual(st.embeddedHashes, {}, 'nothing named, nothing hashed');
  assert.deepEqual(st.embeddedHashReasons, {});
  for (const c of st.store.comments) assert.equal('src' in c.target, false, 'a passage that cannot tell leaves the target as stored');
  assert.deepEqual(reasonLines(st.stderr).sort(), Object.values(st.derivedSrcReasons).map((x) => `file-comments-host: ${x}`).sort(), 'each reason on stderr too');
  assert.deepEqual(fs.readFileSync(sp), bytes);

  // A re-place naming no src refuses with the reason — a refusal, never a crash — and writes nothing.
  let ref = refused(w, replaceNoSrc(md, st, both), 'no-figure');
  assert.match(ref.error, /embeds figs\/latency\.png, figs\/errors\.png, so which figure it is on cannot be told; a re-place needs the figure named in the comment's target \(src\); nothing was changed$/);
  ref = refused(w, replaceNoSrc(md, st, gone), 'anchor-not-found');
  assert.match(ref.error, /could not be placed .*\(anchor-not-found\)/);
  ref = refused(w, replaceNoSrc(md, st, none), 'no-figure');
  assert.match(ref.error, /embeds no figure/);
  assert.deepEqual(fs.readFileSync(sp), bytes, 'byte-identical after the refusals');
  // A re-place that names one of the passage's figures lands, as a caller supplying src always could.
  r = ok(w, { verb: 'retarget', path: md, fence: fenceFor(st), args: { commentId: both, target: { kind: 'image', region: REGION2, src: 'figs/errors.png' } } });
  assert.deepEqual(r.store.comments[0].target, { kind: 'image', region: REGION2, hash: sha256(ERRORS), src: 'figs/errors.png' });
  assert.deepEqual(Object.keys(r.derivedSrcReasons).sort(), [gone, none].sort());
});

// ── the definition's destination, a media file, and the panel's own shape ────────────

test('a reference-style embed\'s figure is told through its definition, which the anchor\'s quote does not carry; a media file\'s reply has no derived fields; a panel-written comment is carried exactly as the disk holds it', () => {
  const w = world();
  const md = path.join(w.docs, 'forms.md');
  const text = '# Forms\n\nErrors by reference: ![error rate][errs]\n\n![p95 latency](figs/latency.png)\n\n[errs]: figs/errors.png\n';
  fs.writeFileSync(md, text);
  let st = status(w, md);
  let r = ok(w, panelComment(md, text, '![error rate][errs]', 0, st, 'figs/errors.png'));
  const sp = r.storePath;
  const byRef = r.store.comments[0].id;
  st = status(w, md);
  r = ok(w, panelComment(md, text, '![p95 latency](figs/latency.png)', 0, st, 'figs/latency.png', 'Panel-written.'));
  stripSrc(sp, [byRef]);
  const disk = readSidecar(sp);

  st = status(w, md);
  assert.deepEqual(st.derivedSrcs, { [byRef]: 'figs/errors.png' }, 'the definition\'s destination, not the label');
  assert.deepEqual(st.derivedSrcReasons, {});
  assert.equal(st.store.comments[0].target.src, 'figs/errors.png');
  assert.deepEqual(st.store.comments[1], disk.comments[1], 'the panel\'s own shape goes as the disk holds it');
  assert.deepEqual(st.embeddedHashes, { 'figs/errors.png': sha256(ERRORS), 'figs/latency.png': sha256(LATENCY) });

  // A standalone image: no anchor, nothing told by a passage; the reply has fileHash and none of this.
  const media = status(w, w.chart);
  assert.equal(media.fileHash, sha256(CHART));
  assert.equal('derivedSrcs' in media, false);
  assert.equal('derivedSrcReasons' in media, false);
  assert.equal('embeddedHashes' in media, false);
});
