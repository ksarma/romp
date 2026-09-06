#!/usr/bin/env node
// The node host script behind the Files pane's comments panel (plans/file-review.md, "The host
// script" and "The comments log"). The kernel runs it once per verb, on the machine that holds the
// file, with one JSON request on stdin and reads one JSON object from stdout:
//
//   stdin   {"verb", "path", "args": {...}, "fence": {...}|null}
//   stdout  {"ok": true, "verb", "root", "storePath", "trackedBy", "agentTooling", "fileMtimeNs",
//            "storeMtimeNs", "configMtimeNs", "store", "hunks", "unsent", "log", "logTruncated",
//            "baseline"?, "logged"?}
//        or {"ok": false, "code", "error"}          — a refusal; exit status 0
//   crash   a non-zero exit with the reason on stderr  — a malformed request or a program error
//
// Every verb is one load-mutate-write in this one process: root discovery, the sidecar path, the
// load-time rebase that re-places changes after outside edits, anchor location, the write, the
// comments-log append. The sidecar format is track-changents v3, read and written ONLY through the
// vendored store-io (never a second implementation of the format); the comments log beside it is
// romp's own, outside that contract. Four rules the file-review plan fixes and this script keeps:
//   * a corrupt or newer-version sidecar is refused, never replaced (loadStoreStatus, not loadStore
//     or ensureStore, which mint a fresh sidecar over anything they cannot read);
//   * the same for .trackchanges/config.json: a config that exists but cannot be read (conflict
//     markers, a half-written file, a newer version) refuses on every verb; it never reads as
//     "nothing tracked", and set-tracked never rewrites it from that reading (checkConfig) — nor
//     in place: it is replaced by temp-and-rename, so this script never produces the half-written
//     file it refuses (writeConfigAtomic);
//   * a refused verb changes nothing on disk. In particular the `.trackchanges/` landmark a loose
//     file gets on its first comment or tracking toggle (decision 37) is created only after every
//     check the verb can refuse on has passed (withSidecar, doSetTracked).
//   * a reply or resolve into a comment the live sidecar lacks refuses `no-comment`; this script
//     never calls reviveThreadFromSuperseded, which overwrites the live sidecar from a park.
// The file's text is read only when a verb needs it: to rebase an existing sidecar, to place an
// anchor, to stamp a fingerprint. `status` runs on every viewer open, a file the viewer refuses
// above 2 MB included, so on a file with no sidecar it stats the file and reads nothing (statFile).
//
// Vendored code: vendor/track-changents (MIT, LICENSE beside it).

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import engine from '../vendor/track-changents/engine.js';
import {
  findVaultRoot, storePathFor, relPathFor, configPathFor, trackedPaths, untrackedPaths,
  trackedClosure, isTrackedFile, loadStoreStatus, saveStore, STORE_VERSION,
} from '../vendor/track-changents/store-io.mjs';
import { addReply } from '../vendor/track-changents/cli/track-reply.mjs';

// ── constants ───────────────────────────────────────────────────────

// The kernel's _TEXT_MAX_BYTES: the cap on any text this script writes back to a file.
export const TEXT_MAX_BYTES = 2 * 1024 * 1024;
// The Log the panel shows: the newest LOG_TAIL entries of the comments log, oldest first.
export const LOG_TAIL = 200;
// Every human action and log entry is authored `you`, with no authorId (decision 6).
export const AUTHOR = 'you';
export const LOG_SUFFIX = '.comments-log.jsonl';
// config.json's format version: store-io's CONFIG_VERSION (not exported), the one shape this script
// and the vendored CLIs read and write.
const CONFIG_VERSION = 2;

// Slice 1 verbs. Slice 2 adds accept, reject, accept-all, reject-all; Slice 5 adds save. The
// verbs that write the FILE (not only the sidecar) — reject, reject-all, save — also fence on
// fileMtimeNs (requireFence with 'file-moved') and call checkTooLarge before any write; no Slice
// 1 verb does either.
const VERBS = new Set(['status', 'set-tracked', 'comment', 'reply', 'resolve', 'log-edit', 'log-send']);

// ── outcome classes ─────────────────────────────────────────────────

// A refusal: the disk state does not allow the verb. Printed as {ok:false, code, error}, exit 0.
export class Refusal extends Error {
  constructor(code, error, extra) {
    super(error);
    this.name = 'Refusal';
    this.code = code;
    this.extra = extra || null;
  }
}

// A malformed request (unknown verb, a missing argument): a caller bug, so a crash (exit 2),
// which the kernel reports as host-error with this message.
export class BadRequest extends Error {
  constructor(msg) { super(msg); this.name = 'BadRequest'; }
}

// ── small helpers ───────────────────────────────────────────────────

// FILE_COMMENTS_HOME lets tests point "home" at a scratch directory; the kernel never sets it.
export function homeDir() {
  return process.env.FILE_COMMENTS_HOME || os.homedir();
}

// Tilde-collapse one path, for every text a person reads.
export function tilde(p) {
  const home = homeDir();
  if (!home || typeof p !== 'string') return p;
  if (p === home) return '~';
  if (p.startsWith(home + path.sep)) return '~' + p.slice(home.length);
  return p;
}

// Tilde-collapse every occurrence of the home path inside a text (an OS error message).
function tildeText(s) {
  const home = homeDir();
  if (!home) return s;
  return String(s).split(home + path.sep).join('~' + path.sep);
}

// Nanosecond mtime as a decimal string, the kernel's X-Romp-Mtime-Ns; null when the path is
// absent. Only a bigint stat carries the full integer (mtimeMs is a float and loses the last
// digits, so a fence built on it would refuse every write).
export function statNs(p) {
  try {
    return fs.statSync(p, { bigint: true }).mtimeNs.toString();
  } catch (e) {
    if (e && (e.code === 'ENOENT' || e.code === 'ENOTDIR')) return null;
    throw e;
  }
}

function exists(p) {
  try { fs.statSync(p); return true; } catch { return false; }
}

// The comments log sits beside the sidecar under the same encoded name, so the two are found
// together and the other hosts' `.json`-only directory scans never read it.
export function logPathFor(storePath) {
  return storePath.replace(/\.json$/, LOG_SUFFIX);
}

function pathsFor(root, abs) {
  const storePath = storePathFor(root, abs);
  return {
    root,
    rel: relPathFor(root, abs),
    storePath,
    configPath: configPathFor(root),
    logPath: logPathFor(storePath),
  };
}

// "present" when the agent-side CLIs are linked on this machine (romp's install.sh, or
// track-changents' own): without them the session cannot answer a comment.
export function agentTooling() {
  return exists(path.join(homeDir(), '.claude', 'hooks', 'track-reply.mjs')) ? 'present' : 'absent';
}

// ── the comments log ────────────────────────────────────────────────

// Parse every line; a line that is not a JSON object is skipped and counted, never rewritten.
export function readLog(logPath) {
  let raw;
  try {
    raw = fs.readFileSync(logPath, 'utf8');
  } catch (e) {
    if (e && e.code === 'ENOENT') return { entries: [], bad: 0 };
    throw e;
  }
  const entries = [];
  let bad = 0;
  for (const line of raw.split('\n')) {
    const t = line.trim();
    if (!t) continue;
    try {
      const o = JSON.parse(t);
      if (o && typeof o === 'object' && !Array.isArray(o)) entries.push(o); else bad++;
    } catch { bad++; }
  }
  return { entries, bad };
}

// One line per entry, appended; the directory must already exist (the caller makes sure).
export function appendLog(logPath, entry) {
  fs.appendFileSync(logPath, JSON.stringify(entry) + '\n', 'utf8');
}

function logEntry(kind, fields) {
  return { ts: new Date().toISOString(), kind, author: AUTHOR, ...fields };
}

function countChanges(entry) {
  return Array.isArray(entry.changes) ? entry.changes.length : 0;
}

// What is unsent, derived from the log alone (decision 10: no browser state). The watermark is
// the largest `watermark` any send entry recorded (a later send that carried only decisions has
// none and must not un-send earlier comments); a `you` comment or reply is unsent when its ts is
// later; accepts and rejects are counted from the entries after the last send.
export function deriveUnsent(store, entries) {
  let watermark = null;
  let lastSend = -1;
  entries.forEach((e, i) => {
    if (!e || e.kind !== 'send') return;
    lastSend = i;
    if (typeof e.watermark === 'number' && (watermark == null || e.watermark > watermark)) watermark = e.watermark;
  });
  const later = (ts) => typeof ts === 'number' && (watermark == null || ts > watermark);
  const comments = [];
  const replies = [];
  for (const c of (store && store.comments) || []) {
    if (!c) continue;
    if (c.author === AUTHOR && later(c.ts)) comments.push(c.id);
    for (const r of c.replies || []) {
      if (r && r.author === AUTHOR && later(r.ts)) replies.push({ commentId: c.id, ts: r.ts });
    }
  }
  let accepted = 0;
  let rejected = 0;
  for (let i = lastSend + 1; i < entries.length; i++) {
    const e = entries[i];
    if (!e) continue;
    if (e.kind === 'accept') accepted += countChanges(e);
    else if (e.kind === 'reject') rejected += countChanges(e);
  }
  return { comments, replies, accepted, rejected, watermark };
}

// ── tracking ────────────────────────────────────────────────────────

// Mirrors the link index store-io builds privately (walkVaultMd, buildLinkIndex,
// resolveLinkTarget are not exported): every .md under the root, dot-dirs and node_modules
// skipped; a link resolves against the full relative path first, then by basename, the shortest
// path winning ties. Used only to NAME the parent note that makes a file inherit tracking; the
// tracked-or-not verdict itself always comes from store-io's isTrackedFile.
function linkIndex(root) {
  const rels = [];
  const walk = (dir) => {
    let entries;
    try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { return; }
    for (const e of entries) {
      if (e.name.startsWith('.')) continue;
      const p = path.join(dir, e.name);
      if (e.isDirectory()) { if (e.name !== 'node_modules') walk(p); } else if (e.isFile() && e.name.toLowerCase().endsWith('.md')) {
        rels.push(path.relative(root, p));
      }
    }
  };
  walk(root);
  const byLowerRel = new Map();
  const byBasename = new Map();
  for (const rel of rels) {
    byLowerRel.set(rel.toLowerCase(), rel);
    const base = path.basename(rel, path.extname(rel)).toLowerCase();
    if (!byBasename.has(base)) byBasename.set(base, []);
    byBasename.get(base).push(rel);
  }
  return { byLowerRel, byBasename };
}

function resolveLink(index, linkText) {
  const t = String(linkText || '').trim().replace(/^\.?\//, '');
  if (!t) return null;
  const lower = t.toLowerCase();
  const withMd = lower.endsWith('.md') ? lower : lower + '.md';
  if (index.byLowerRel.has(withMd)) return index.byLowerRel.get(withMd);
  const base = path.basename(lower, lower.endsWith('.md') ? '.md' : '');
  const hits = index.byBasename.get(base) || [];
  if (!hits.length) return null;
  return [...hits].sort((a, b) => (a.split('/').length - b.split('/').length) || a.localeCompare(b))[0];
}

// The tracked note whose whole-line link makes `rel` inherit tracking, or null when none can be
// named (the verdict said inherited, so one exists unless the tree changed under us).
export function inheritedParent(root, rel) {
  const closure = trackedClosure(root);
  const index = linkIndex(root);
  for (const parent of closure) {
    if (parent === rel) continue;
    let text;
    try { text = fs.readFileSync(path.join(root, parent), 'utf8'); } catch { continue; }
    for (const target of engine.childLinkLines(text)) {
      if (resolveLink(index, target) === rel) return parent;
    }
  }
  return null;
}

const normEntry = (s) => String(s).replace(/^\.?\//, '');

// Which config.json entry covers the file: `{kind: "file"|"folder"|"inherited", entry}` or null.
// A file entry wins over a folder entry; among folder entries the most specific one; `entry` is
// the string as written in config.json so `off` can remove exactly it. An `untracked` veto wins
// over everything, as it does for the guard and the CLIs.
export function trackedByFor(root, abs) {
  const rel = relPathFor(root, abs);
  if (engine.isTracked(untrackedPaths(root), rel)) return null;
  const list = trackedPaths(root);
  const p = normEntry(rel);
  let file = null;
  let folder = null;
  for (const raw of list) {
    if (typeof raw !== 'string' || !raw) continue;
    const e = normEntry(raw);
    if (e.endsWith('/')) {
      if (p.startsWith(e) && (folder == null || e.length > normEntry(folder).length)) folder = raw;
    } else if (e === p && file == null) {
      file = raw;
    }
  }
  if (file != null) return { kind: 'file', entry: file };
  if (folder != null) return { kind: 'folder', entry: folder };
  if (!list.length) return null;
  if (!isTrackedFile(root, abs)) return null;
  return { kind: 'inherited', entry: inheritedParent(root, rel) };
}

// The `untracked` entry that vetoes tracking `rel`, or null — the match engine.isTracked makes,
// kept so a refusal can name the entry to remove.
function vetoEntryFor(root, rel) {
  const p = normEntry(rel);
  for (const raw of untrackedPaths(root)) {
    if (typeof raw !== 'string' || !raw) continue;
    const e = normEntry(raw);
    if (e.endsWith('/') ? p.startsWith(e) : e === p) return raw;
  }
  return null;
}

// ── the config ──────────────────────────────────────────────────────

// config.json is read the way the sidecar is: saying WHY it cannot be. store-io's readConfig
// answers null for an unparseable file exactly as for a missing one, so through it alone a
// conflict-marked or half-written config.json reads as "nothing tracked" — and setTracked, which
// rewrites the file from that reading, would replace it with a one-entry list, dropping every
// other tracked entry and the untracked vetoes while the guard already passes raw writes. The
// sidecar's rule, refused and never replaced, holds for the config too.
//   absent       no file
//   corrupt      unparseable, not an object, or a `tracked`/`untracked` that is not an array
//   unsupported  a `v` above CONFIG_VERSION
//   unreadable   an I/O error other than ENOENT
//   ok           readable; a missing `tracked` list means nothing tracked, as store-io reads it
function configStatus(paths) {
  let raw;
  try {
    raw = fs.readFileSync(paths.configPath, 'utf8');
  } catch (e) {
    return e && e.code === 'ENOENT' ? 'absent' : 'unreadable';
  }
  let obj;
  try { obj = JSON.parse(raw); } catch { return 'corrupt'; }
  if (!obj || typeof obj !== 'object' || Array.isArray(obj)) return 'corrupt';
  if (typeof obj.v === 'number' && obj.v > CONFIG_VERSION) return 'unsupported';
  if (obj.tracked !== undefined && !Array.isArray(obj.tracked)) return 'corrupt';
  if (obj.untracked !== undefined && !Array.isArray(obj.untracked)) return 'corrupt';
  return 'ok';
}

// Every verb under a root calls this before it reads tracking through store-io or writes
// config.json, so `trackedBy` is never answered from a config that could not be read.
function refuseConfig(ctx, paths, status) {
  const cp = tilde(paths.configPath);
  switch (status) {
    case 'ok':
    case 'absent': return;
    case 'corrupt':
      throw new Refusal('corrupt', `the tracking list for ${ctx.shown} could not be read: ${cp} is not valid JSON in the expected shape; nothing was changed`);
    case 'unsupported':
      throw new Refusal('unsupported-version', `the tracking list for ${ctx.shown} (${cp}) was written by a newer version of the format than this romp reads; nothing was changed`);
    default:
      throw new Refusal('unreadable', `cannot read the tracking list for ${ctx.shown} (${cp})`);
  }
}
function checkConfig(ctx, paths) { refuseConfig(ctx, paths, configStatus(paths)); }

// ── the file ────────────────────────────────────────────────────────

// The one way this script opens the file: a non-blocking open, then fstat through the descriptor,
// and a refusal (`unreadable`) for anything but a regular file — a missing path, a directory, a
// FIFO, a device, a file this process may not open — with the OS error for the person to read.
// Both readFile and statFile go through here so the check cannot be skipped by the route a verb
// takes. A plain open() of a FIFO with no writer blocks until one arrives, which used to pin the
// host until the kernel's deadline killed it and reported a hang where a refusal was due; and a
// stat-then-open pair checks one inode and opens whatever the path names by then. O_NONBLOCK
// returns the descriptor at once, the fstat says what it is, and a regular file reads the same
// through it. Returns the open descriptor (the caller closes it) and the bigint stat.
function openRegular(ctx) {
  let fd;
  try {
    fd = fs.openSync(ctx.abs, fs.constants.O_RDONLY | (fs.constants.O_NONBLOCK || 0));
    const st = fs.fstatSync(fd, { bigint: true });
    if (!st.isFile()) throw new Error(`${ctx.abs} is not a regular file`);
    return { fd, st };
  } catch (e) {
    if (fd !== undefined) { try { fs.closeSync(fd); } catch { /* ignore */ } }
    throw new Refusal('unreadable', `cannot read ${ctx.shown}: ${tildeText(e && e.message ? e.message : String(e))}`);
  }
}

// Every file is read as UTF-8 text, images and PDFs included, exactly as the CLIs read it, so
// the fingerprint this script stamps equals theirs. The mtime comes from the same descriptor the
// text is read through, taken before the read: a file that changes between the two then carries
// the older stamp, so the next fenced write refuses and the caller reloads, rather than a newer
// stamp over text the caller never saw.
function readFile(ctx) {
  const { fd, st } = openRegular(ctx);
  let text;
  try {
    text = fs.readFileSync(fd, 'utf8');
  } catch (e) {
    throw new Refusal('unreadable', `cannot read ${ctx.shown}: ${tildeText(e && e.message ? e.message : String(e))}`);
  } finally {
    try { fs.closeSync(fd); } catch { /* ignore */ }
  }
  return { text, fileMtimeNs: st.mtimeNs.toString() };
}

// The file opened and stat'ed, not read: for the verbs that need no text when no sidecar exists
// (nothing to rebase, no fingerprint to stamp). `status` runs on every viewer open, so reading
// the whole file into a V8 string there loaded a 300 MB log for nothing and failed outright
// above V8's string limit. Refuses exactly what readFile would (both go through openRegular), so
// a caller sees no difference but the bytes not moved.
function statFile(ctx) {
  const { fd, st } = openRegular(ctx);
  try { fs.closeSync(fd); } catch { /* ignore */ }
  return { text: null, fileMtimeNs: st.mtimeNs.toString() };
}

// `too-large`: only verbs that write the file check it, before any write (the kernel's cap).
export function checkTooLarge(shown, text) {
  if (Buffer.byteLength(text, 'utf8') > TEXT_MAX_BYTES) {
    throw new Refusal('too-large', `${shown} exceeds the 2 MB text cap, so its contents cannot be written from the dashboard`);
  }
}

// Atomic write of a file's new text, for the verbs that change file bytes (reject, save): a
// temp file in the same directory whose name does not end in .json (so the other hosts' sidecar
// scans skip it), written through the realpath (never over a symlink), mode preserved, renamed
// into place. Returns the new mtime string. Nothing in Slice 1 calls it; it is the seam Slice 2's
// reject and Slice 5's save write through.
export function writeFileAtomic(absPath, text) {
  const real = fs.realpathSync(absPath);
  const st = fs.statSync(real);
  const mode = st.mode & 0o7777;
  const tmp = path.join(path.dirname(real), `.${path.basename(real)}.romp-fc-${process.pid}-${Date.now()}.tmp`);
  let fd;
  try {
    fd = fs.openSync(tmp, 'w', mode);
    fs.writeFileSync(fd, text, 'utf8');
    try { fs.fsyncSync(fd); } catch { /* fsync unsupported on some filesystems */ }
    fs.closeSync(fd);
    fd = undefined;
    fs.chmodSync(tmp, mode);
    fs.renameSync(tmp, real);
  } catch (e) {
    if (fd !== undefined) { try { fs.closeSync(fd); } catch { /* ignore */ } }
    try { fs.unlinkSync(tmp); } catch { /* ignore */ }
    throw e;
  }
  return statNs(real);
}

// ── the sidecar ─────────────────────────────────────────────────────

// Load through loadStoreStatus, the only loader that says WHY there is no store. Returns the
// normalized store (rebased against the current text), or null when absent; refuses the rest.
function loadOrRefuse(ctx, paths, text) {
  const { store, status } = loadStoreStatus(paths.storePath, text);
  const sp = tilde(paths.storePath);
  switch (status) {
    case 'ok': return store;
    case 'absent': return null;
    case 'corrupt':
      throw new Refusal('corrupt', `the comments for ${ctx.shown} could not be read: ${sp} is not valid JSON in the expected shape; nothing was changed`);
    case 'unsupported':
      throw new Refusal('unsupported-version', `the comments for ${ctx.shown} (${sp}) were written by a newer version of the format than this romp reads; nothing was changed`);
    default:
      throw new Refusal('unreadable', `cannot read the comments for ${ctx.shown} (${sp})`);
  }
}

// The file and its sidecar for the verbs that write neither: the text is read only when a sidecar
// exists to rebase against (or the caller asked for the baseline, which is the text itself when
// there is none); otherwise the file is stat'ed. `store` is null when there is no sidecar.
function loadFile(ctx, paths) {
  const read = ctx.args.baseline === true || (paths != null && exists(paths.storePath));
  const file = read ? readFile(ctx) : statFile(ctx);
  const store = read && paths ? loadOrRefuse(ctx, paths, file.text) : null;
  return { ...file, store };
}

// A refusal thrown after the comments log was appended: carry `logged`, and when the entry did
// land say so in place of "nothing was changed" — the kernel shows this text beside its warning.
function recordedDespite(e, logged, what) {
  e.extra = { ...(e.extra || {}), logged };
  if (logged) e.message = `${e.message.replace(/; nothing was changed$/, '')}; the ${what} was recorded in the comments log`;
}

// The seed track-comment writes for a file with no sidecar yet (cli/track-comment.mjs).
function seedStore(rel) {
  return { v: STORE_VERSION, path: rel, suggestions: [], comments: [] };
}

// A file with no landmark above it (.obsidian, .git, .trackchanges): the first comment or
// tracking toggle creates .trackchanges/ beside it, and that folder is its project's root from
// then on, for this script and for the CLIs alike (decision 37).
function createLandmark(ctx) {
  const dir = path.dirname(ctx.abs);
  fs.mkdirSync(path.join(dir, '.trackchanges'), { recursive: true });
  const root = findVaultRoot(ctx.abs);
  if (root !== dir) throw new Error(`created ${tilde(dir)}/.trackchanges but findVaultRoot answers ${tilde(String(root))}`);
  return root;
}

// A fence compares the caller's mtime string with the current one; "" means the file must not
// exist. Missing fences are a caller bug, never silently skipped.
function requireFence(ctx, key, actual, code, describe) {
  const v = ctx.fence[key];
  if (typeof v !== 'string') throw new BadRequest(`fence.${key} is required for ${ctx.verb}`);
  const expected = v === '' ? null : v;
  if (expected === actual) return;
  let how = 'changed on disk since you opened the file';
  if (expected == null && actual != null) how = 'appeared on disk since you opened the file';
  else if (expected != null && actual == null) how = 'disappeared from disk since you opened the file';
  throw new Refusal(code, `${describe} ${how} — reload and retry`);
}

function findComment(store, id) {
  return ((store && store.comments) || []).find((c) => c && String(c.id) === String(id)) || null;
}

function requireNote(args) {
  const note = args.note;
  if (typeof note !== 'string' || !note.trim()) throw new BadRequest('a non-empty note is required');
  return note.trim();
}

function requireCommentId(args) {
  const id = args.commentId;
  if ((typeof id !== 'string' && typeof id !== 'number') || id === '') throw new BadRequest('commentId is required');
  return id;
}

// Locate the browser's anchor in the file as it is now. The engine picks the best-scoring hit
// and breaks ties by the hint; a stored comment carries no hint, so a passage that occurs twice
// with the same 24 characters on both sides cannot be re-placed by any later reader and is
// refused `anchor-ambiguous` rather than saved on a guess. Locating with the hint pinned to the
// start and to the end of the text asks the engine for the earliest and the latest tied hit;
// when they differ, a tie exists. The located text must equal the quote: the engine's fallback
// to the surviving context is a relocation, not a match, and refuses `anchor-not-found`.
export function locateExact(text, anchor, hint) {
  const quote = anchor.quote;
  const first = engine.locateAnchor(text, anchor, 0);
  if (!first || text.slice(first.from, first.to) !== quote) return { error: 'anchor-not-found' };
  const last = engine.locateAnchor(text, anchor, text.length);
  if (!last || last.from !== first.from) return { error: 'anchor-ambiguous' };
  const loc = engine.locateAnchor(text, anchor, typeof hint === 'number' ? hint : undefined);
  if (!loc || loc.from !== first.from) return { error: 'anchor-ambiguous' };
  return { from: loc.from, to: loc.to };
}

function validateAnchor(anchor) {
  if (!anchor || typeof anchor !== 'object') throw new BadRequest('anchor must be an object {quote, prefix, suffix}');
  if (typeof anchor.quote !== 'string' || !anchor.quote) throw new BadRequest('anchor.quote must be a non-empty string');
  return {
    quote: anchor.quote,
    prefix: typeof anchor.prefix === 'string' ? anchor.prefix : '',
    suffix: typeof anchor.suffix === 'string' ? anchor.suffix : '',
  };
}

// The comment object in addComment's exact shape (cli/track-comment.mjs): id `${now}-${idx}`,
// author `you`, no authorId, ts, anchor (a passage only), body, replies [], resolved false. A
// whole-file comment has no anchor and the id `${now}-0`. `target` (a region on an image or a
// PDF page, Slices 3 and 4) passes through untouched.
export function buildComment(text, args, now) {
  const note = requireNote(args);
  let c;
  if (args.anchor == null) {
    c = { id: `${now}-0`, author: AUTHOR, ts: now, body: note, replies: [], resolved: false };
  } else {
    const anchor = validateAnchor(args.anchor);
    const loc = locateExact(text, anchor, args.hintOffset);
    if (loc.error) return { error: loc.error };
    c = {
      id: `${now}-${loc.from}`,
      author: AUTHOR,
      ts: now,
      anchor: engine.makeAnchor(text, loc.from, loc.to),
      body: note,
      replies: [],
      resolved: false,
    };
  }
  if (args.target != null) c.target = args.target;
  return { comment: c };
}

// ── the reply ───────────────────────────────────────────────────────

function reply(ctx, state, extra) {
  const { root, paths, store, text, fileMtimeNs } = state;
  let log = [];
  let logTruncated = false;
  let entries = [];
  if (paths) {
    const read = readLog(paths.logPath);
    entries = read.entries;
    if (read.bad) process.stderr.write(`file-comments-host: ${read.bad} unreadable line(s) in ${tilde(paths.logPath)} skipped\n`);
    logTruncated = entries.length > LOG_TAIL;
    log = logTruncated ? entries.slice(entries.length - LOG_TAIL) : entries;
  }
  const out = {
    ok: true,
    verb: ctx.verb,
    root,
    storePath: paths ? paths.storePath : null,
    trackedBy: root ? trackedByFor(root, ctx.abs) : null,
    agentTooling: agentTooling(),
    fileMtimeNs,
    storeMtimeNs: paths ? statNs(paths.storePath) : null,
    configMtimeNs: paths ? statNs(paths.configPath) : null,
    store,
    hunks: store ? engine.toHunks(store.suggestions) : [],
    unsent: deriveUnsent(store, entries),
    log,
    logTruncated,
  };
  if (ctx.args.baseline === true) out.baseline = engine.baselineOf(text, store ? store.suggestions : []);
  return Object.assign(out, extra || {});
}

// Re-read what was just written so the reply carries the sidecar as every later load sees it.
function reloadSaved(ctx, paths, text) {
  const store = loadOrRefuse(ctx, paths, text);
  if (!store) throw new Error(`the sidecar ${tilde(paths.storePath)} vanished after its write`);
  return store;
}

// ── verbs ───────────────────────────────────────────────────────────

function doStatus(ctx) {
  const root = findVaultRoot(ctx.abs);
  if (!root) return reply(ctx, { root: null, paths: null, ...loadFile(ctx, null) });
  const paths = pathsFor(root, ctx.abs);
  checkConfig(ctx, paths);
  return reply(ctx, { root, paths, ...loadFile(ctx, paths) });
}

// comment, reply, resolve: fence on the sidecar, load, decide, then write. `plan(store, text)`
// runs every check the verb itself can refuse on (the anchor, the comment id) and returns the
// step that changes the store; it runs BEFORE the landmark, so a refused verb leaves the disk as
// it found it. Ordered the other way, a passage comment whose passage was edited away between the
// selection and Enter left an empty `.trackchanges/` beside a loose file — a root for every later
// verb and for the CLIs — under a refusal that named no such thing. `store` is null in `plan` when
// no sidecar exists yet (a first comment); the seed is minted after the landmark, whose root
// gives the seed its relative path.
function withSidecar(ctx, create, plan) {
  const file = readFile(ctx);
  let root = findVaultRoot(ctx.abs);
  let paths = root ? pathsFor(root, ctx.abs) : null;
  requireFence(ctx, 'storeMtimeNs', paths ? statNs(paths.storePath) : null, 'store-moved',
    `the comments for ${ctx.shown}`);
  if (paths) checkConfig(ctx, paths);
  let store = null;
  if (root) store = loadOrRefuse(ctx, paths, file.text);
  if (!store && !create) {
    throw new Refusal('no-comment', `comment ${String(ctx.args.commentId)} is not among the comments for ${ctx.shown} — reload and retry`);
  }
  const apply = plan(store, file.text);
  if (!root) {
    root = createLandmark(ctx);
    paths = pathsFor(root, ctx.abs);
  }
  if (!store) store = seedStore(paths.rel);
  apply(store);
  saveStore(root, paths.storePath, store, file.text);
  return reply(ctx, { root, paths, store: reloadSaved(ctx, paths, file.text), ...file });
}

function doComment(ctx) {
  return withSidecar(ctx, true, (store, text) => {
    const built = buildComment(text, ctx.args, Date.now());
    if (built.error === 'anchor-not-found') {
      throw new Refusal('anchor-not-found', `the selected passage is no longer in ${ctx.shown} — reload and select it again`);
    }
    if (built.error === 'anchor-ambiguous') {
      throw new Refusal('anchor-ambiguous', `the selected passage occurs more than once in ${ctx.shown} with the same surroundings, so a comment on it could not be placed again later — select more of the text around it`);
    }
    return (s) => { s.comments.push(built.comment); };
  });
}

function doReply(ctx) {
  const id = requireCommentId(ctx.args);
  const note = requireNote(ctx.args);
  return withSidecar(ctx, false, (store) => {
    if (!findComment(store, id)) {
      throw new Refusal('no-comment', `comment ${String(id)} is not among the comments for ${ctx.shown} — reload and retry`);
    }
    return (s) => {
      const res = addReply(s, id, AUTHOR, note, Date.now(), null);
      if (res.error) throw new BadRequest(res.error);
    };
  });
}

function doResolve(ctx) {
  const id = requireCommentId(ctx.args);
  if (typeof ctx.args.on !== 'boolean') throw new BadRequest('resolve needs on: true|false');
  return withSidecar(ctx, false, (store) => {
    if (!findComment(store, id)) throw new Refusal('no-comment', `comment ${String(id)} is not among the comments for ${ctx.shown} — reload and retry`);
    return (s) => { findComment(s, id).resolved = ctx.args.on; };
  });
}

// The folder entry that tracks a file's directory: `<dir>/` relative to the root. A file at the
// root itself has no folder entry to write (an empty prefix matches nothing), so that refuses.
// A loose file is always that case — its project would start in its own folder (decision 37) —
// so its refusal says why, in place of a root the person never chose.
function folderEntryFor(ctx, rel, loose) {
  const dir = path.dirname(rel);
  if (!dir || dir === '.' || dir === '' || dir.startsWith('..')) {
    if (loose) {
      throw new Refusal('folder-is-root', `${ctx.shown} has no project above it, so tracking would start in its own folder ${tilde(path.dirname(ctx.abs))} and there is no folder inside that to track; track the file itself`);
    }
    throw new Refusal('folder-is-root', `${ctx.shown} sits at its project's root, so there is no folder to track; track the file itself, or open a file inside a folder`);
  }
  return dir + '/';
}

// config.json replaced, never rewritten in place. The vendored setTracked ends in a bare
// writeFileSync, which truncates the file before it writes it, so a kill (the kernel's 10 s
// timeout SIGKILLs this process) or a full disk between the two leaves a half-written config:
// this script then refuses `corrupt` on every verb while the guard reads the same file as nothing
// tracked and passes raw writes to every file the list protected. So the list is computed as
// setTracked computes it and written the way the sidecar (saveStore) and the commented file
// (writeFileAtomic) are: a temp file in the same directory, fsync, rename. The bytes equal
// writeTrackedPaths's exactly — same shape, same dedupe, the `untracked` vetoes kept — which the
// disk tests pin against the vendored writer, so the Obsidian and VS Code hosts read no difference.
// The temp name does not end in .json, so their sidecar scans skip it.
function writeConfigAtomic(root, relPath, on) {
  const list = trackedPaths(root);
  const next = on ? (list.includes(relPath) ? list : [...list, relPath]) : list.filter((p) => p !== relPath);
  const cfg = { v: CONFIG_VERSION, tracked: [...new Set(next.filter((s) => typeof s === 'string' && s))] };
  const off = untrackedPaths(root);
  if (off.length) cfg.untracked = off;
  const configPath = configPathFor(root);
  const dir = path.dirname(configPath);
  fs.mkdirSync(dir, { recursive: true });
  const tmp = path.join(dir, `.config.romp-fc-${process.pid}-${Date.now()}.tmp`);
  let fd;
  try {
    fd = fs.openSync(tmp, 'w');
    fs.writeFileSync(fd, JSON.stringify(cfg, null, 2) + '\n', 'utf8');
    try { fs.fsyncSync(fd); } catch { /* fsync unsupported on some filesystems */ }
    fs.closeSync(fd);
    fd = undefined;
    fs.renameSync(tmp, configPath);
  } catch (e) {
    if (fd !== undefined) { try { fs.closeSync(fd); } catch { /* ignore */ } }
    try { fs.unlinkSync(tmp); } catch { /* ignore */ }
    throw e;
  }
}

function doSetTracked(ctx) {
  const { on, scope } = ctx.args;
  if (typeof on !== 'boolean') throw new BadRequest('set-tracked needs on: true|false');
  if (on && scope !== 'file' && scope !== 'folder') throw new BadRequest('set-tracked needs scope: "file"|"folder"');
  let root = findVaultRoot(ctx.abs);
  let paths = root ? pathsFor(root, ctx.abs) : null;
  requireFence(ctx, 'configMtimeNs', paths ? statNs(paths.configPath) : null, 'config-moved',
    `the tracking setting for ${ctx.shown}`);
  if (paths) checkConfig(ctx, paths);
  const file = loadFile(ctx, paths);
  if (!root && !on) return reply(ctx, { root: null, paths: null, ...file });
  // With no landmark, the root the toggle would create is the file's own directory (decision
  // 37). Every check below runs against that root first — the veto (none, with no config), the
  // folder entry (always the root for a loose file) — and the landmark is created only once none
  // refused, so a refused toggle leaves the disk as it found it: no `.trackchanges/` created beside
  // the file by a click that answered folder-is-root.
  const loose = !root;
  const newRoot = root || path.dirname(ctx.abs);
  if (!paths) paths = pathsFor(newRoot, ctx.abs);
  let entry;
  let kind;
  if (on) {
    // The `untracked` veto wins over the list and over inheritance, for the guard and the CLIs as
    // for trackedByFor; an entry written under it would change nothing but the config, so refuse
    // and name the entry to remove (the config is the vault owner's, edited by hand).
    const veto = vetoEntryFor(newRoot, paths.rel);
    if (veto != null) {
      throw new Refusal('tracked-vetoed', `${ctx.shown} cannot be tracked while the untracked entry "${veto}" in ${tilde(paths.configPath)} vetoes it — remove that entry there first`);
    }
    kind = scope;
    entry = scope === 'file' ? paths.rel : folderEntryFor(ctx, paths.rel, loose);
  } else {
    const before = trackedByFor(root, ctx.abs);
    if (!before) return reply(ctx, { root, paths, ...file });
    if (before.kind === 'inherited') {
      const parent = before.entry ? tilde(path.join(root, before.entry)) : 'a tracked note';
      throw new Refusal('tracked-inherited', `${ctx.shown} is tracked because ${parent} links to it — turn tracking off there instead`);
    }
    kind = before.kind;
    entry = before.entry;
  }
  if (loose) root = createLandmark(ctx); // asserts the root it finds is newRoot, the file's directory
  writeConfigAtomic(root, entry, on);
  appendLog(paths.logPath, logEntry('set-tracked', { on, scope: kind, entry }));
  return reply(ctx, { root, paths, ...file });
}

const EDIT_SUMMARY_KEYS = ['mtimeBeforeNs', 'mtimeAfterNs', 'bytesBefore', 'bytesAfter', 'diff', 'truncated'];

// A direct edit from the viewer (decision 33), logged by the kernel's saveFile path after the
// save: only for a file that already has a sidecar, a comments log, or a tracked flag; never
// creates a sidecar, a log, or a landmark. The append comes first so the record never depends on
// the sidecar being readable — nor on the config: a sidecar or a log makes the file the log's
// business whatever config.json says, and only the tracked flag needs a readable config.
function doLogEdit(ctx) {
  const summary = ctx.args.summary;
  if (!summary || typeof summary !== 'object' || Array.isArray(summary)) throw new BadRequest('log-edit needs summary: {...}');
  const root = findVaultRoot(ctx.abs);
  const paths = root ? pathsFor(root, ctx.abs) : null;
  let logged = false;
  try {
    if (paths) {
      const cfg = configStatus(paths);
      if (exists(paths.storePath) || exists(paths.logPath) || (cfg === 'ok' && isTrackedFile(root, ctx.abs))) {
        const fields = {};
        for (const k of EDIT_SUMMARY_KEYS) if (summary[k] !== undefined) fields[k] = summary[k];
        appendLog(paths.logPath, logEntry('edit', fields));
        logged = true;
      }
      refuseConfig(ctx, paths, cfg);
    }
    return reply(ctx, { root, paths, ...loadFile(ctx, paths) }, { logged });
  } catch (e) {
    if (e instanceof Refusal) recordedDespite(e, logged, 'edit');
    throw e;
  }
}

// The send entry the kernel appends after fileCommentsSend replied sent or queued: the message
// as sent, so the log remembers what went and the unsent derivation moves its watermark. The
// append comes before the file and sidecar are read: the message has gone, and the log is the
// only state for what is unsent, so a send left unrecorded would be offered again. The one
// exception is a file that does not exist under no landmark: nothing on disk names it, so the
// entry has nothing to mark sent, and no `.trackchanges/` is created beside a ghost.
function doLogSend(ctx) {
  const a = ctx.args;
  if (typeof a.sid !== 'string' || !a.sid) throw new BadRequest('log-send needs sid');
  if (!Array.isArray(a.comments)) throw new BadRequest('log-send needs comments: [{id, desc, body}]');
  for (const c of a.comments) {
    if (!c || typeof c !== 'object' || c.id === undefined) throw new BadRequest('every log-send comment needs an id');
  }
  if (typeof a.accepted !== 'number' || typeof a.rejected !== 'number') throw new BadRequest('log-send needs accepted and rejected counts');
  if (typeof a.queued !== 'boolean') throw new BadRequest('log-send needs queued: true|false');
  if (a.watermark !== null && typeof a.watermark !== 'number') throw new BadRequest('log-send needs watermark: number|null');
  let root = findVaultRoot(ctx.abs);
  let logged = false;
  try {
    if (!root) {
      statFile(ctx);
      root = createLandmark(ctx);
    }
    const paths = pathsFor(root, ctx.abs);
    fs.mkdirSync(path.dirname(paths.logPath), { recursive: true });
    const fields = { sid: a.sid };
    if (typeof a.sessionName === 'string') fields.sessionName = a.sessionName;
    fields.comments = a.comments.map((c) => ({ id: c.id, desc: c.desc, body: c.body }));
    fields.accepted = a.accepted;
    fields.rejected = a.rejected;
    fields.queued = a.queued;
    fields.watermark = a.watermark;
    appendLog(paths.logPath, logEntry('send', fields));
    logged = true;
    checkConfig(ctx, paths);
    return reply(ctx, { root, paths, ...loadFile(ctx, paths) }, { logged });
  } catch (e) {
    if (e instanceof Refusal) recordedDespite(e, logged, 'send');
    throw e;
  }
}

const HANDLERS = {
  status: doStatus,
  'set-tracked': doSetTracked,
  comment: doComment,
  reply: doReply,
  resolve: doResolve,
  'log-edit': doLogEdit,
  'log-send': doLogSend,
};

// One request in, one result object out; throws Refusal or BadRequest (or a program error).
export function handle(req) {
  if (!req || typeof req !== 'object' || Array.isArray(req)) throw new BadRequest('the request must be a JSON object');
  const verb = req.verb;
  if (typeof verb !== 'string' || !VERBS.has(verb)) throw new BadRequest(`unknown verb ${JSON.stringify(verb)}`);
  if (typeof req.path !== 'string' || !req.path) throw new BadRequest('path is required');
  const args = req.args == null ? {} : req.args;
  if (typeof args !== 'object' || Array.isArray(args)) throw new BadRequest('args must be an object');
  const fence = req.fence == null ? {} : req.fence;
  if (typeof fence !== 'object' || Array.isArray(fence)) throw new BadRequest('fence must be an object');
  const abs = path.resolve(req.path);
  const ctx = { verb, abs, args, fence, shown: tilde(abs) };
  return HANDLERS[verb](ctx);
}

// ── entry point ─────────────────────────────────────────────────────

async function readStdin() {
  const chunks = [];
  for await (const c of process.stdin) chunks.push(c);
  return Buffer.concat(chunks).toString('utf8');
}

async function main() {
  const raw = await readStdin();
  let req;
  try {
    req = JSON.parse(raw);
  } catch (e) {
    process.stderr.write(`file-comments-host: the request on stdin is not JSON: ${e && e.message}\n`);
    process.exit(2);
  }
  let out;
  try {
    out = handle(req);
  } catch (e) {
    if (e instanceof Refusal) {
      out = { ok: false, code: e.code, error: e.message, ...(e.extra || {}) };
    } else {
      process.stderr.write(`file-comments-host: ${e && e.stack ? tildeText(e.stack) : String(e)}\n`);
      process.exit(e instanceof BadRequest ? 2 : 1);
    }
  }
  process.stdout.write(JSON.stringify(out) + '\n');
}

const invokedDirectly = (() => {
  try {
    return process.argv[1] && fs.realpathSync(process.argv[1]) === fileURLToPath(import.meta.url);
  } catch { return false; }
})();

if (invokedDirectly) main();
