// Cost pins for tools/file-comments-host.mjs imageEmbeds (plans/file-review.md, Slice 3, "Risks"):
// the reader of a markdown file's figure embeds runs over the WHOLE text on every `comment` with a
// `target.src` and on every `retarget` of a stored target that lacks one, under the kernel's
// _FILE_COMMENTS_TIMEOUT, on texts up to the viewer's 2 MB cap. The Slice 3 review found the
// reading quadratic in two places — a fence-membership scan per embed, and the one-regex `<img>`
// form that rescans from every `<img` to the next `>` — so a 2 MB file of repeated fences and
// embeds, or of `<img ` with no `>`, took the host past the deadline on every attempt: the kernel
// killed it, no sidecar was written, and no region could be placed on any figure in that file.
// This module pins:
//   * agreement — the linear walk yields exactly the embeds the one-regex reading yields, which is
//     still the panel's reading (ui/webview/file-comments.ts imageEmbeds), so the host and the
//     panel keep naming the same figures; a seeded corpus over the forms' fragments plus the edge
//     cases the `<img>` regex is particular about (a quoted value crossing `>`, a `src=` inside
//     another attribute's value, `<img` inside `<img`, no `>` at all);
//   * cost — every adversarial shape at the viewer's cap completes far under the deadline;
//   * the scenario — a region comment on the one real figure in such a file is written, on
//     `comment` and on the `retarget` path that re-reads the passage, well inside the deadline.
// Same hermetic harness as file-comments-host-targets.test.mjs: the synthetic `notes-api` world
// under a scratch directory, a tiny PNG generated at run time, the script driven as the kernel
// drives it. Run: node --test tools/file-comments-host-embeds.test.mjs
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

import { TEXT_MAX_BYTES, imageEmbeds } from './file-comments-host.mjs';
import { tinyPng, sha256 } from '../tests/fixtures/file_comments/tiny-png.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const HOST = path.join(REPO, 'tools', 'file-comments-host.mjs');
const VENDOR = path.join(REPO, 'vendor', 'track-changents');
const engine = createRequire(import.meta.url)(path.join(VENDOR, 'engine.js'));

// The kernel's deadline for one verb, read from its source so the bound below is the real one.
function kernelDeadlineMs() {
  const src = fs.readFileSync(path.join(REPO, 'kernel', 'kernel.py'), 'utf8');
  const m = /^_FILE_COMMENTS_TIMEOUT = (\d+)/m.exec(src);
  assert.ok(m, 'kernel.py defines _FILE_COMMENTS_TIMEOUT');
  return Number(m[1]) * 1000;
}

// ── the reading being matched ───────────────────────────────────────

// The one-regex reading, as the panel reads (ui/webview/file-comments.ts imageEmbeds) and as this
// host read before the review: the specification the linear walk must agree with, match for match.
const LABEL = '(?:\\\\.|[^\\[\\]\\\\])*';
const IMG_INLINE = new RegExp('!\\[(' + LABEL + ')\\]\\([ \\t]*(?:<([^<>\\n]*)>|([^\\s()]*(?:\\([^\\s()]*\\)[^\\s()]*)*))(?:[ \\t]+(?:"[^"]*"|\'[^\']*\'|\\([^()]*\\)))?[ \\t]*\\)', 'g');
const IMG_FULL_REF = new RegExp('!\\[(' + LABEL + ')\\]\\[(' + LABEL + ')\\]', 'g');
const IMG_SHORT_REF = new RegExp('!\\[(' + LABEL + ')\\](?![\\[(])', 'g');
const IMG_HTML = /<img\b[^>]*?\bsrc[ \t]*=[ \t]*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))[^>]*>/gi;
const REF_DEF = /^ {0,3}\[((?:\\.|[^\[\]\\])+)\]:[ \t]*<?([^\s>]+)>?/gm;
const normLabel = (s) => s.trim().replace(/\s+/g, ' ').toLowerCase();
function fencedRanges(text) {
  const out = [];
  let open = null;
  let at = 0;
  for (const line of text.split('\n')) {
    const m = /^ {0,3}(`{3,}|~{3,})/.exec(line);
    if (m) {
      if (!open) open = { ch: m[1][0], n: m[1].length, at };
      else if (m[1][0] === open.ch && m[1].length >= open.n && /^\s*$/.test(line.slice(m[0].length))) { out.push([open.at, at + line.length]); open = null; }
    }
    at += line.length + 1;
  }
  if (open) out.push([open.at, text.length]);
  return out;
}
function oneRegexEmbeds(text) {
  const fences = fencedRanges(text);
  const inFence = (i) => fences.some(([a, b]) => i >= a && i < b);
  const defs = new Map();
  let m;
  REF_DEF.lastIndex = 0;
  while ((m = REF_DEF.exec(text))) if (!inFence(m.index)) defs.set(normLabel(m[1]), m[2]);
  const out = [];
  const push = (start, len, dest) => {
    if (dest !== undefined && !inFence(start)) out.push({ start, end: start + len, dest });
  };
  for (const re of [IMG_INLINE, IMG_FULL_REF, IMG_SHORT_REF, IMG_HTML]) re.lastIndex = 0;
  while ((m = IMG_INLINE.exec(text))) push(m.index, m[0].length, m[2] ?? m[3] ?? '');
  while ((m = IMG_FULL_REF.exec(text))) push(m.index, m[0].length, defs.get(normLabel(m[2] || m[1])));
  while ((m = IMG_SHORT_REF.exec(text))) push(m.index, m[0].length, defs.get(normLabel(m[1])));
  while ((m = IMG_HTML.exec(text))) push(m.index, m[0].length, m[1] ?? m[2] ?? m[3] ?? '');
  out.sort((a, b) => a.start - b.start);
  return out.filter((e, i) => !i || e.start >= out[i - 1].end);
}

// ── agreement ───────────────────────────────────────────────────────

// Every way the `<img>` regex can accept or reject a tag, spelled out; the corpus below may reach
// these by chance, this list reaches them by construction.
const IMG_EDGES = [
  '<img alt="a<b" src="x.png">', '<img alt="a>b" src="x.png">', '<img src="a>b" x>', '<img src="x src=y.png>"',
  '<img <img src=a.png>', '<img src="a" src=\'b\'>', '<img src=', '<img src="', '<img src="x', '<img src="x"',
  '<img src=x', '<img src=x>', '<img>', '<imgsrc=x>', '<img-x src=y>', '<img src = "x y" >', '<IMG SRC=\'Q\'>',
  '<img src="a"\n<img src="b">', '<img data-src=x src=y>', '<img srcset=a src=b>', '<img xsrc=a>', '<img\nsrc="a"\n>',
  '<img src="\u00a0">', '<img src=\u00a0x>', '<img src=a\u2028>', '<img src=""> <img src="">', '<img src=\'\'>',
  '<img src="x"> tail <img src=', '<img src=x.png ![a](b.png)>', '![a](<img src=x>)', '<img src="](x)">',
  'a <img\tsrc\t=\t"x.png"\t> b', '<img src="a"><img src="b">', '<img src="a" ><img src="b"', '<img src=a><img',
  '<img src=a>>', '<img src=a>b>c>', '<img src=a src=b>', '<img alt=src=a.png>', '<img alt=\'src=a.png\' src=b>',
  '<img src=a>\n```\n<img src=b>\n```\n<img src=c>', '<img src="x\n```\n">\n```\n<img src=y>', '<img a> <img b> src=x>',
  '<img src="a>"><img src="b>">', '<img', '<img ', 'src=x>', '<img\u00a0src=x>', '<img src=x\u00a0>',
];
// Fragments of every form the reader knows, assembled at random under a fixed seed: the same
// corpus on every run, so a disagreement is reproducible by its index.
const FRAGMENTS = ['<img', '<IMG', ' src=', ' SRC=', '\tsrc =', ' data-src=', ' srcset=', 'src=', '"', "'", '>', '<', ' ', '\n',
  'a', 'x.png', 'alt="', '\u00a0', '=', '![', ']', '(', ')', '[', ':', '```\n', '~~~\n', '\\', '!', 'ref', ' "t"', '<b>', 'img', '-', '[]'];
function corpus(n) {
  let seed = 0x5eed;
  const rnd = (k) => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed % k; };
  const out = [];
  for (let i = 0; i < n; i++) {
    let t = '';
    for (let k = 1 + rnd(30); k > 0; k--) t += FRAGMENTS[rnd(FRAGMENTS.length)];
    out.push(t);
  }
  return out;
}

test('imageEmbeds yields the embeds of the one-regex reading, match for match: the named <img> edges and a seeded corpus over every form\'s fragments', () => {
  for (const t of IMG_EDGES) assert.deepEqual(imageEmbeds(t), oneRegexEmbeds(t), JSON.stringify(t));
  const texts = corpus(40_000);
  for (let i = 0; i < texts.length; i++) {
    const t = texts[i];
    const got = imageEmbeds(t);
    const want = oneRegexEmbeds(t);
    if (JSON.stringify(got) !== JSON.stringify(want)) assert.deepEqual(got, want, `corpus[${i}] ${JSON.stringify(t)}`);
  }
});

// ── cost ────────────────────────────────────────────────────────────

// Texts at the viewer's cap built to make each reading do its worst: the two the review measured
// past the deadline (fences × embeds, `<img ` with no `>`), and the other ways a scan could be made
// to restart — a `src=` far past every tag's `>`, quotes that close each other across `>`, a
// definition label or a title with no close, parenthesised runs, escapes in labels, a fence never
// closed, and a text that is nothing but figures.
function atCap(unit, prefix = '') {
  const n = Math.floor((TEXT_MAX_BYTES - Buffer.byteLength(prefix)) / Buffer.byteLength(unit));
  const text = prefix + unit.repeat(n);
  assert.ok(Buffer.byteLength(text) <= TEXT_MAX_BYTES, 'a text the viewer shows');
  return text;
}
const SHAPES = {
  'fences and embeds': () => atCap('```\n```\n![a](f.png)\n'),
  'img with no close': () => atCap('<img '),
  'img closed, src far behind': () => atCap('<img a>').slice(0, TEXT_MAX_BYTES - 7) + ' src=x>',
  'quotes crossing >': () => atCap('<img src="a>b'),
  'unclosed quotes': () => atCap('<img src="'),
  'definition lines': () => atCap('[x\n'),
  'unclosed title': () => atCap('![a](b "'),
  'parenthesised run': () => atCap('(c)', '![a](x'),
  'escapes in labels': () => atCap('![\\['),
  'fence never closed': () => atCap('![a](b)\n', '```\n'),
  'definitions and references': () => atCap('![r] ', '[r]: a.png\n'),
  'every form, repeated': () => atCap('<img src=x> ![a](b) ![c][r] ![r] '),
};

test('every adversarial shape at the viewer\'s 2 MB cap is read far inside the kernel\'s deadline', () => {
  // The linear reading takes well under a second on each; the bound leaves room for a loaded
  // machine and still sits at a fifth of the deadline the quadratic reading ran past.
  const bound = kernelDeadlineMs() / 5;
  for (const [name, build] of Object.entries(SHAPES)) {
    const text = build();
    const t0 = performance.now();
    const out = imageEmbeds(text);
    const ms = performance.now() - t0;
    assert.ok(Array.isArray(out), name);
    assert.ok(ms < bound, `${name}: ${ms.toFixed(0)} ms, bound ${bound} ms`);
  }
});

// ── the scenario, through the script ────────────────────────────────

let SCRATCH;
before(() => { SCRATCH = fs.mkdtempSync(path.join(os.tmpdir(), 'romp-fc-host-embeds-')); });
after(() => { try { fs.rmSync(SCRATCH, { recursive: true, force: true }); } catch { /* ignore */ } });

const REAL = tinyPng(10, 20, 30);
const REAL_EMBED = '![the real figure](figs/real.png)';
const REGION = { x: 0.12, y: 0.4, w: 0.35, h: 0.2 };
const REGION2 = { x: 0.5, y: 0.5, w: 0.25, h: 0.1 };

// <scratch>/wN/home/notes-api/.git/        the landmark that makes notes-api a project
//                    notes-api/docs/doc.md the 2 MB text: one real figure, then the adversarial tail
//                    notes-api/docs/figs/real.png
let worlds = 0;
function world(tail) {
  const home = path.join(SCRATCH, `w${++worlds}`, 'home');
  const root = path.join(home, 'notes-api');
  const docs = path.join(root, 'docs');
  fs.mkdirSync(path.join(root, '.git'), { recursive: true });
  fs.mkdirSync(path.join(docs, 'figs'), { recursive: true });
  fs.writeFileSync(path.join(docs, 'figs', 'real.png'), REAL);
  const text = atCap(tail, `# A report\n\n${REAL_EMBED}\n\n`);
  fs.writeFileSync(path.join(docs, 'doc.md'), text);
  return { home, root, doc: path.join(docs, 'doc.md'), text };
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
  const t0 = performance.now();
  const r = spawnSync(process.execPath, [HOST], { input: JSON.stringify(req), encoding: 'utf8', env: env(w), maxBuffer: 64 * 1024 * 1024 });
  const ms = performance.now() - t0;
  let json = null;
  try { json = JSON.parse(r.stdout); } catch { json = null; }
  return { code: r.status, stdout: r.stdout, stderr: r.stderr, json, ms };
}
function ok(w, req, bound) {
  const r = host(w, req);
  assert.equal(r.code, 0, `exit ${r.code}: ${r.stderr}`);
  assert.ok(r.json && r.json.ok === true, `expected ok:true, got ${r.stdout.slice(0, 400)}`);
  assert.ok(r.ms < bound, `${req.verb} took ${r.ms.toFixed(0)} ms, bound ${bound} ms`);
  return r.json;
}
function fenceFor(st) { return { storeMtimeNs: st.storeMtimeNs == null ? '' : st.storeMtimeNs }; }
function regionComment(w, st, src) {
  const i = w.text.indexOf(REAL_EMBED);
  const anchor = engine.makeAnchor(w.text, i, i + REAL_EMBED.length);
  return { verb: 'comment', path: w.doc, fence: fenceFor(st), args: { anchor, hintOffset: i, note: 'On the figure.', target: { kind: 'image', region: REGION, src } } };
}

for (const [name, tail] of [['fences and embeds', '```\n```\n![a](f.png)\n'], ['img with no close', '<img ']]) {
  test(`a region comment on the real figure in a 2 MB file of ${name} is written on comment and re-placed on retarget, each well inside the kernel's deadline`, () => {
    // Half the deadline: the quadratic reading ran past the whole of it on both shapes, on every
    // attempt; the linear one leaves the verb its usual fraction of a second.
    const bound = kernelDeadlineMs() / 2;
    const w = world(tail);
    let st = ok(w, { verb: 'status', path: w.doc, args: {} }, bound);
    assert.equal(st.store, null, 'no sidecar yet');
    let r = ok(w, regionComment(w, st, 'figs/real.png'), bound);
    const sp = r.storePath;
    assert.ok(fs.existsSync(sp), 'the sidecar was written');
    const c = r.store.comments[0];
    assert.deepEqual(c.target, { kind: 'image', region: REGION, hash: sha256(REAL), src: 'figs/real.png' });
    assert.deepEqual(r.embeddedHashes, { 'figs/real.png': sha256(REAL) });
    // The other path that reads the passage's embeds: a stored target with an anchor and no src
    // takes one from the passage on retarget.
    const disk = JSON.parse(fs.readFileSync(sp, 'utf8'));
    delete disk.comments[0].target.src;
    fs.writeFileSync(sp, JSON.stringify(disk, null, 2) + '\n');
    st = ok(w, { verb: 'status', path: w.doc, args: {} }, bound);
    r = ok(w, { verb: 'retarget', path: w.doc, fence: fenceFor(st), args: { commentId: c.id, target: { kind: 'image', region: REGION2, src: 'figs/real.png' } } }, bound);
    assert.deepEqual(r.store.comments[0].target, { kind: 'image', region: REGION2, hash: sha256(REAL), src: 'figs/real.png' });
    assert.deepEqual(r.store.comments[0].anchor, c.anchor);
  });
}
