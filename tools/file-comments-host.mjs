#!/usr/bin/env node
// The node host script behind the Files pane's comments panel (plans/file-review.md, "The host
// script" and "The comments log"). The kernel runs it once per verb, on the machine that holds the
// file, with one JSON request on stdin and reads one JSON object from stdout:
//
//   stdin   {"verb", "path", "args": {...}, "fence": {...}|null}
//   stdout  {"ok": true, "verb", "root", "storePath", "trackedBy", "agentTooling", "fileMtimeNs",
//            "storeMtimeNs", "configMtimeNs", "store", "hunks", "unsent", "log", "logTruncated",
//            "fileHash" + "fileHashReason" | "embeddedHashes" + "embeddedHashReasons" + "derivedSrcs" +
//            "derivedSrcReasons", "baseline"?, "logged"?, "accepted"?, "rejected"?}
//        or {"ok": false, "code", "error"}          — a refusal; exit status 0
//   crash   a non-zero exit with the reason on stderr  — a malformed request or a program error
//
// Every verb is one load-mutate-write in this one process: root discovery, the sidecar path, the
// load-time rebase that re-places changes after outside edits, anchor location, accept and reject
// through the engine, the write, the comments-log append, the prune of an emptied sidecar. The
// sidecar format is track-changents v3, read and written ONLY through the vendored store-io (never
// a second implementation of the format); the comments log beside it is romp's own, outside that
// contract. Five rules the file-review plan fixes and this script keeps:
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
//   * a decision about a change that is no longer pending (accepted already, or coalesced away by a
//     later track-edit) refuses `no-change` by id, so the caller reloads instead of deciding a
//     different change under the same name; and accept never drops a comment bound to the change
//     (`suggestionId`), it marks it resolved, so the ids in a sent message stay addressable;
//   * a region comment's stored target is `{kind, region, page?, hash, src?}` (validateTarget, then
//     stampTarget, in that key order): `page` on a PDF only, and `src` only on a figure embedded in a
//     markdown file — the embed's destination as written, which keys the reply's `embeddedHashes`
//     and which the anchor quote does not always carry (a reference-style embed's destination sits
//     in a `[ref]: dest` definition elsewhere in the file); a target with no anchor has none. The
//     `hash` is this script's sha256 of the figure's BYTES (Slice 3), never the client's value and
//     never a hash of the lossy text: for a standalone image or PDF the file's own, for a figure
//     embedded in a markdown file the bytes of the `src` the embed names, resolved
//     against the file's directory and refused unless it is a regular file inside the project root,
//     one the anchored passage embeds (`figure-mismatch`), of the kind the target claims, and no
//     larger than the viewer shows (`too-large`); the region lies inside the unit square. And when
//     the request says which bytes the person saw (`fence.figureHash`: the hash the last reply
//     carried for that figure — `fileHash` on a media file, `embeddedHashes[src]` on a text file),
//     the bytes hashed must be those, else `figure-changed` (figureFence, stampTarget): a figure
//     regenerated between the drag and Enter would otherwise be stamped with a hash the person never
//     saw, which the panel reads as current — the one write the hash exists to catch, missed at the
//     moment it is made. That fence says what the caller saw and is checked when it says anything;
//     a request without one is taken as before, since a caller has no hash for a figure no reply
//     has hashed yet (a text file's replies hash the figures its region comments already name), and
//     `retarget` is held to the same rule. Every reply carries the current hash to compare against
//     — `fileHash` on a media file, `embeddedHashes` per src on a text file — with null for
//     "unknown" (unreadable, or past the size cap), which is never the same as stale, and beside
//     every null the reason (`fileHashReason`, `embeddedHashReasons`), so the panel can say what
//     could not be checked;
//   * the contract's own shape — the embed line's anchor plus `{kind, region, hash}` with no `src`,
//     which the plan describes and another writer can leave — is read, never left "unknown": every
//     reply names the figure such a comment is on from its anchored passage, located now, when that
//     passage embeds exactly one figure (passageFigure), carries that src in the store it answers
//     (`derivedSrcs`, per comment id: a read never rewrites the sidecar, and the reply says where
//     its store differs from the disk) and hashes it under `embeddedHashes`, so the panel's stale
//     check and its re-place key on it; when the passage cannot tell (gone, ambiguous, embedding no
//     figure or several) the reason stands per comment id in `derivedSrcReasons`. A `retarget` on
//     such a comment whose request names no `src` takes the passage's figure and writes the target
//     with its src; a passage that cannot tell refuses (`no-figure`, or the anchor's own code),
//     since that is the disk's state and not a caller bug. A stored src must still be named by the
//     request, as before: the panel holds it, and a re-place keeps the figure.
// The file's text is read only when a verb needs it: to rebase an existing sidecar, to place an
// anchor, to stamp a fingerprint. `status` runs on every viewer open, a file the viewer refuses
// above 2 MB included, so on a file with no sidecar it stats the file and reads nothing (statFile).
// The verbs that change the FILE (reject, reject-all) fence on its mtime too, refuse a file that is
// not UTF-8 text (`not-text`) or would exceed the 2 MB cap (`too-large`) before any write, write the
// sidecar first and the file second, and put the prior sidecar back if the file write fails — the
// order track-edit uses, so a reader never finds a file whose changes its sidecar does not describe.
//
// Vendored code: vendor/track-changents (MIT, LICENSE beside it).

import { createHash } from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import engine from '../vendor/track-changents/engine.js';
import {
  findVaultRoot, storePathFor, relPathFor, configPathFor, trackedPaths, untrackedPaths,
  trackedClosure, isTrackedFile, loadStoreStatus, saveStore, pruneIfClean, STORE_VERSION,
} from '../vendor/track-changents/store-io.mjs';
import { addReply } from '../vendor/track-changents/cli/track-reply.mjs';
import { decodeTextOrNull } from '../vendor/track-changents/cli/track-edit.mjs';

// ── constants ───────────────────────────────────────────────────────

// The kernel's _TEXT_MAX_BYTES: the cap on any text this script writes back to a file.
export const TEXT_MAX_BYTES = 2 * 1024 * 1024;
// The Log the panel shows: the newest LOG_TAIL entries of the comments log, oldest first.
export const LOG_TAIL = 200;
// Every human action and log entry is authored `you`, with no authorId (decision 6).
export const AUTHOR = 'you';
export const LOG_SUFFIX = '.comments-log.jsonl';
// The files the viewer shows as an image or a PDF: the kernel's _PREVIEW_MIME extensions (the media
// half of GET /file), mirrored here because a region comment can exist only on a file the viewer
// renders as media. `status` on such a file answers the hash of its bytes (fileHash); on any other
// file it answers the hashes of the figures its region comments name (embeddedHashes). The regions
// test pins this set against the kernel's dict.
export const MEDIA_EXTENSIONS = new Set(['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg', 'pdf']);
// How many bytes a reply will hash: a media file up to the kernel's _PREVIEW_MAX_BYTES (the most
// the viewer shows), and one shared budget for the figures a text file's region comments name.
// Past either the hash is null. FILE_COMMENTS_HASH_CAP and FILE_COMMENTS_EMBEDDED_HASH_CAP
// override them for tests; the kernel never sets them.
export const FILE_HASH_CAP = 50_000_000;
export const EMBEDDED_HASH_CAP = 200_000_000;
// config.json's format version: store-io's CONFIG_VERSION (not exported), the one shape this script
// and the vendored CLIs read and write.
const CONFIG_VERSION = 2;

// The verbs through Slice 3 (retarget is Slice 3's re-place gesture); Slice 5 adds save. The verbs
// that write the FILE (not only the sidecar) — reject, reject-all, and later save — also fence on
// fileMtimeNs (requireFence with 'file-moved') and check the text (not-text, too-large) before any
// write; no other verb does. The verbs that stamp a figure's hash (comment with a target, retarget)
// fence on the figure's BYTES instead, through fence.figureHash when the request carries it
// (figureFence, then stampTarget with 'figure-changed'): a markdown file's mtime cannot fence a
// figure embedded in it, and a hash is checked against the very bytes stamped.
const VERBS = new Set([
  'status', 'set-tracked', 'comment', 'reply', 'resolve', 'log-edit', 'log-send',
  'accept', 'accept-all', 'reject', 'reject-all', 'retarget',
]);

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
// stamp over text the caller never saw. `isText` says whether the bytes ARE UTF-8 text (no NUL
// byte, no invalid sequence — track-edit's decodeTextOrNull, the same judgement the CLI makes):
// when they are not, `text` is the lossy decode the fingerprint needs, and the verbs that write
// the file refuse (`not-text`) rather than write that decode back over the bytes.
function readFile(ctx) {
  const { fd, st } = openRegular(ctx);
  let buf;
  try {
    buf = fs.readFileSync(fd);
  } catch (e) {
    throw new Refusal('unreadable', `cannot read ${ctx.shown}: ${tildeText(e && e.message ? e.message : String(e))}`);
  } finally {
    try { fs.closeSync(fd); } catch { /* ignore */ }
  }
  const strict = decodeTextOrNull(buf);
  return { text: strict != null ? strict : buf.toString('utf8'), isText: strict != null, fileMtimeNs: st.mtimeNs.toString() };
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

// ── regions: the bytes behind a target ──────────────────────────────

function envCap(name, dflt) {
  const v = process.env[name];
  if (v == null || v === '') return dflt;
  const n = Number(v);
  if (!Number.isFinite(n) || n < 0) throw new Error(`${name} must be a non-negative number of bytes, not ${JSON.stringify(v)}`);
  return n;
}
export function fileHashCap() { return envCap('FILE_COMMENTS_HASH_CAP', FILE_HASH_CAP); }
export function embeddedHashCap() { return envCap('FILE_COMMENTS_EMBEDDED_HASH_CAP', EMBEDDED_HASH_CAP); }

// What the viewer shows a path as, by its extension (the kernel's _PREVIEW_MIME, keyed the same
// way): 'pdf', 'image', or null for a file it renders as text or refuses. A region can be drawn
// only on the first two, and a target's `kind` must be the one the file it is about has.
export function mediaKind(p) {
  const ext = path.extname(String(p == null ? '' : p)).slice(1).toLowerCase();
  if (ext === 'pdf') return 'pdf';
  return ext !== '' && MEDIA_EXTENSIONS.has(ext) ? 'image' : null;
}
export function isMediaPath(p) { return mediaKind(p) !== null; }

// A byte count as the kernel's _human_bytes prints it (the 413's own phrasing), so a size this
// script names beside a cap reads the same as the viewer's refusal for the same file.
export function humanBytes(n) {
  for (const [unit, step] of [['GB', 1 << 30], ['MB', 1 << 20], ['KB', 1 << 10]]) {
    if (n >= step) return `${(n / step).toFixed(1)} ${unit}`;
  }
  return `${n} bytes`;
}

// An embedded figure's `src` as the viewer decodes it before loading the figure (decodeURI, so
// `p95%20latency.png` is the file with the space; a malformed escape is read as written —
// file-view.ts, rewriteFigureSrcs): the spelling every path check and the kind check use.
function decodeSrc(src) {
  try { return decodeURI(src); } catch { return src; }
}

// The sha256 hex of a regular file's BYTES, streamed through the hash in chunks and never decoded:
// the UTF-8 text every other read in this script produces is lossy for an image (every invalid
// sequence becomes U+FFFD), so a hash over it would call two different files the same. Opened as
// openRegular opens (non-blocking, fstat through the descriptor, regular files only), so a FIFO or
// a directory named as a figure fails at once instead of hanging. `cap` (bytes, or null for none)
// is checked against the size before any byte is read: over it the hash is null, "unknown", which
// the panel shows as such and never as stale. Throws on anything unreadable; the caller decides
// between a refusal (comment, retarget) and null (the hashes a reply carries).
export function hashRegular(abs, cap) {
  let fd;
  try {
    fd = fs.openSync(abs, fs.constants.O_RDONLY | (fs.constants.O_NONBLOCK || 0));
    const st = fs.fstatSync(fd);
    if (!st.isFile()) throw new Error(`${abs} is not a regular file`);
    if (cap != null && st.size > cap) return { hash: null, size: st.size };
    const h = createHash('sha256');
    const buf = Buffer.allocUnsafe(64 * 1024);
    for (;;) {
      const n = fs.readSync(fd, buf, 0, buf.length, null);
      if (n === 0) break;
      h.update(buf.subarray(0, n));
    }
    return { hash: h.digest('hex'), size: st.size };
  } finally {
    if (fd !== undefined) { try { fs.closeSync(fd); } catch { /* ignore */ } }
  }
}

// The region a comment names, checked the way every other argument is (a bad shape is a caller
// bug, so BadRequest) and rebuilt from its known fields: `kind`, `region` (fractions of the image's
// natural size, kept to four decimals — the client sends four, and this makes sure — and lying
// inside the image: x + w and y + h at most 1, so what the sidecar holds is always a region OF the
// picture, never a rectangle that overflows it or misses it), `page` (PDFs only, 1-based), and
// `src`. The hash is not the client's to send; stampTarget computes it, and checks `kind` against
// the file it hashes. `embedded` says whether the comment carries an anchor: a figure in a
// markdown file names its `src` (the embed's destination as written) and a standalone image or
// PDF has none, and the two cannot mix — a src with no embed line to stand on, or an embed line
// with no figure to hash, would hash the wrong file.
export function validateTarget(raw, embedded) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) throw new BadRequest('target must be an object {kind, region, page?, src?}');
  if (raw.kind !== 'image' && raw.kind !== 'pdf') throw new BadRequest('target.kind must be "image" or "pdf"');
  const reg = raw.region;
  if (!reg || typeof reg !== 'object' || Array.isArray(reg)) throw new BadRequest('target.region must be an object {x, y, w, h}');
  const region = {};
  for (const k of ['x', 'y', 'w', 'h']) {
    const v = reg[k];
    if (typeof v !== 'number' || !Number.isFinite(v) || v < 0 || v > 1) throw new BadRequest(`target.region.${k} must be a number between 0 and 1`);
    region[k] = Math.round(v * 1e4) / 1e4;
  }
  if (!(region.w > 0) || !(region.h > 0)) throw new BadRequest('target.region.w and .h must be greater than 0 at four decimals');
  // Each value is a multiple of 1e-4 up to float noise, so rounding the sum's ten-thousandths reads
  // it exactly: 0.9999 + 0.0001 is inside, 1 + 0.0001 is not.
  if (Math.round((region.x + region.w) * 1e4) > 1e4 || Math.round((region.y + region.h) * 1e4) > 1e4) {
    throw new BadRequest('target.region must lie inside the image: x + w and y + h must not exceed 1 at four decimals');
  }
  const out = { kind: raw.kind, region };
  if (raw.kind === 'pdf') {
    if (!Number.isInteger(raw.page) || raw.page < 1) throw new BadRequest('target.page must be a positive integer for a pdf');
    out.page = raw.page;
  } else if (raw.page != null) {
    throw new BadRequest('an image target takes no page');
  }
  if (raw.src != null) {
    if (typeof raw.src !== 'string' || !raw.src) throw new BadRequest('target.src must be a non-empty string when present');
    if (!embedded) throw new BadRequest('target.src names an embedded figure, which needs the anchor of its embed line');
    out.src = raw.src;
  } else if (embedded) {
    throw new BadRequest("a region on an embedded figure needs target.src, the embed's destination as written");
  }
  return out;
}

// Where an embedded figure's `src` points: the destination as the embed writes it, decoded the way
// the viewer decodes it (decodeSrc), so the host hashes the file the person saw; resolved against
// the commented file's directory as a path — an absolute src (`![x](/srv/figs/a.png)`, which the
// viewer also reads as a filesystem path) names that path itself, path.resolve dropping the
// directory — then confirmed by realpath to be INSIDE the project root: never above it, not through
// a symlink that leaves it, and an absolute src is held to the same check, which is the only thing
// keeping it in (the targets test sends one in each direction). `rootDir` is the root the file has,
// or for a loose file the one its first comment is about to create, its own directory (decision
// 37). Returns the resolved path or throws with the reason; the caller makes that a refusal
// (comment, retarget) or a null hash with the reason beside it (the hashes a reply carries).
// Whether it is a regular file is hashRegular's check, on the same descriptor it reads.
export function resolveSrc(ctx, rootDir, src) {
  if (/^[a-z][a-z0-9+.-]*:/i.test(src)) throw new Error(`${src} is a URL, not a file in the project`);
  const abs = path.resolve(path.dirname(ctx.abs), decodeSrc(src));
  let real;
  try {
    real = fs.realpathSync(abs);
  } catch (e) {
    throw new Error(`${tilde(abs)} cannot be resolved: ${e && e.message ? e.message : String(e)}`);
  }
  const rootReal = fs.realpathSync(rootDir);
  if (real !== rootReal && !real.startsWith(rootReal + path.sep)) {
    throw new Error(`${tilde(real)} is outside the project root ${tilde(rootReal)}`);
  }
  return real;
}

const errText = (e) => tildeText(e && e.message ? e.message : String(e));

// The figure's fence: `fence.figureHash`, the sha256 the caller last saw for the figure the region is
// on — the reply's `fileHash` on a media file, `embeddedHashes[src]` on a text file — or null when
// the request names none. Read before any disk read, like every fence key (a bad shape is a caller
// bug): a hash this script never emitted (not 64 lowercase hex digits) could only ever refuse, so it
// is refused as the bug it is rather than reported as a changed figure; and it fences a region, so a
// `comment` carrying it with no target is a caller bug too (the caller checks that). Absent is
// allowed, unlike the mtime fences: a caller has no hash for a figure no reply has hashed yet (a
// text file's replies hash only the figures its region comments already name), so the fence says
// what the caller saw, and is checked, in stampTarget, when it says anything.
const SHA256_HEX = /^[0-9a-f]{64}$/;
function figureFence(ctx) {
  const v = ctx.fence.figureHash;
  if (v == null) return null;
  if (typeof v !== 'string' || !SHA256_HEX.test(v)) {
    throw new BadRequest(`fence.figureHash must be the sha256 hex a reply carried for the figure (fileHash, or embeddedHashes[src]), not ${JSON.stringify(v)}`);
  }
  return v;
}

// The target `comment` and `retarget` write: the validated shape plus the hash of the bytes it
// is about — the figure `src` names, or the commented file itself for a standalone image or PDF.
// Three checks stand between the shape and the hash, in this order. A region with no anchor is on
// the commented file itself, so that file must be an image or a PDF (a region on a markdown file
// with no embed line to stand on would hash the markdown's bytes and be a rectangle on nothing).
// The src resolves inside the root (resolveSrc: not a URL, not above the root, not out through a
// symlink). Then `kind` must be what the named file's extension says it is, the way the viewer
// decides what to render — a `pdf` target on a png, or a figure whose extension the viewer never
// shows as media, is a caller bug, not a stored shape. Then the bytes are hashed under
// FILE_HASH_CAP, the most the viewer shows of any one file (the kernel's _PREVIEW_MAX_BYTES): a
// figure past it was never on the person's screen, so a request naming one refuses `too-large`
// instead of hashing it — before this cap a multi-GB src named by a client pinned the host for as
// long as the kernel's deadline allowed and then failed as a timeout. The constant, not the
// environment override: the override belongs to the reply-side hashes alone (their tests cap a
// tiny fixture; a write verb's cap is pinned with a sparse file). Key order is the contract's:
// kind, region, page (pdf), hash, src (embedded). Then, when the request said which bytes the person
// saw (`figureHash`, from figureFence), the hash taken must equal it — else the figure was
// regenerated between the picture the person drew on and this write, and the target refuses
// `figure-changed` rather than record a hash the person never saw as the one they did: every reply
// would then equal it, and the panel would read a rectangle drawn on the old picture as current on
// the new one, the very case the hash exists to mark stale. Deliberately NOT one of the `-moved`
// codes: the panel re-issues status and retries those once, and a retry here would stamp the new
// bytes — the person has to look at the picture as it is now and draw the region again, so this one
// is shown to them.
function stampTarget(ctx, rootDir, target, figureHash) {
  const what = target.src != null ? `the figure ${tilde(target.src)} in ${ctx.shown}` : ctx.shown;
  if (target.src == null && mediaKind(ctx.abs) == null) {
    throw new BadRequest(`a region with no anchor is on the file itself, and ${ctx.shown} is not an image or a PDF; a figure embedded in it takes the anchor of its embed line and target.src`);
  }
  let abs = ctx.abs;
  if (target.src != null) {
    try {
      abs = resolveSrc(ctx, rootDir, target.src);
    } catch (e) {
      throw new Refusal('unreadable', `${what} cannot be read: ${errText(e)}; nothing was changed`);
    }
  }
  const kind = mediaKind(target.src != null ? decodeSrc(target.src) : ctx.abs);
  if (kind == null) throw new BadRequest(`${what} is not an image or a PDF by its extension, so the viewer never showed it as one and no region can be drawn on it`);
  if (kind !== target.kind) throw new BadRequest(`target.kind is "${target.kind}" but ${what} is ${kind === 'pdf' ? 'a PDF' : 'an image'}`);
  let hashed;
  try {
    hashed = hashRegular(abs, FILE_HASH_CAP);
  } catch (e) {
    throw new Refusal('unreadable', `${what} cannot be read: ${errText(e)}; nothing was changed`);
  }
  if (hashed.hash == null) {
    throw new Refusal('too-large', `${what} is ${humanBytes(hashed.size)}, more than the ${humanBytes(FILE_HASH_CAP)} the viewer shows, so no region can be placed on it; nothing was changed`);
  }
  if (figureHash != null && hashed.hash !== figureHash) {
    throw new Refusal('figure-changed', `${what} changed on disk since it was shown — reload to see it as it is now, then draw the region again; nothing was changed`);
  }
  const out = { kind: target.kind, region: target.region };
  if (target.page != null) out.page = target.page;
  out.hash = hashed.hash;
  if (target.src != null) out.src = target.src;
  return out;
}

// The hash a reply carries for a media file: its bytes as they are now, for the panel to compare
// with each region comment's target.hash — {hash} when it could be taken, else {hash: null, reason}.
// Null past the cap, and null when the file cannot be read at this moment — the verb already read
// or stat'ed it, so that is a race with a writer, and "unknown" is the honest answer where a
// refusal would deny a write that landed. The reason travels IN the reply (fileHashReason): the
// kernel keeps this script's stderr only when the call fails, so a reason written there alone
// left the panel with a bare "unknown" that named neither the file nor what stopped the check.
function fileHashFor(ctx) {
  try {
    const r = hashRegular(ctx.abs, fileHashCap());
    if (r.hash != null) return { hash: r.hash };
    return { hash: null, reason: `${ctx.shown} is ${humanBytes(r.size)}, past the ${humanBytes(fileHashCap())} checked on each open, so whether it changed since its regions were drawn could not be checked` };
  } catch (e) {
    return { hash: null, reason: `${ctx.shown} could not be read to check it: ${errText(e)}` };
  }
}

// The hashes a reply carries for a text file: one per distinct `src` its region comments name, in
// order of first appearance, each the figure's bytes as they are now — or null when the src does
// not resolve to a regular file inside the root, or when hashing it would take the call past the
// shared budget, with the reason under the same src in `reasons` (the reply's embeddedHashReasons:
// a figure that is gone, one that moved outside the root, and one past the budget are three
// different situations for the person, and a null alone showed all three as one "unknown").
// Empty objects when the file has no sidecar or no region comments. `store` is the one the reply
// carries (derivedSrcsFor): a comment in the contract's src-less shape is hashed under the src its
// passage told, and skipped when it could not — its reason is in derivedSrcReasons.
function embeddedHashesFor(ctx, rootDir, store) {
  const hashes = new Map();
  const reasons = {};
  if (!store || !rootDir) return { hashes: {}, reasons };
  const cap = embeddedHashCap();
  let budget = cap;
  for (const c of store.comments || []) {
    const src = c && c.target && c.target.src;
    if (typeof src !== 'string' || !src || hashes.has(src)) continue;
    let hash = null;
    try {
      const r = hashRegular(resolveSrc(ctx, rootDir, src), budget);
      if (r.hash != null) { hash = r.hash; budget -= r.size; }
      else reasons[src] = `the figure ${tilde(src)} (${humanBytes(r.size)}) was not checked: the figures ${ctx.shown}'s comments name are checked up to ${humanBytes(cap)} together, and this one would pass it`;
    } catch (e) {
      reasons[src] = `the figure ${tilde(src)} in ${ctx.shown} was not hashed: ${errText(e)}`;
    }
    hashes.set(src, hash);
  }
  return { hashes: Object.fromEntries(hashes), reasons };
}

// ── regions: the embeds a passage holds ─────────────────────────────

// The image embeds in a markdown text, read as the panel reads them (ui/webview/file-comments.ts,
// imageEmbeds — the same forms, the same destinations): `![alt](dest "title")` with dest bare or
// in <>, `![alt][ref]` and `![ref]` through `[ref]: dest` definitions, and a raw `<img src>` tag;
// an embed inside fenced code renders as text and is skipped. Each is {start, end, dest} over the
// text's offsets, dest exactly as written, which is what a region comment's `src` is. The targets
// test runs the panel's fixture forms through this so the two readers stay in step.
//
// Linear in the text, on purpose: `comment` and `retarget` run this over the WHOLE file (a
// reference-style embed's destination sits in a definition anywhere in it) under the kernel's 10 s
// deadline, and the viewer shows texts up to 2 MB. Before the Slice 3 review two parts of the
// reading were quadratic — fence membership scanned per embed (#fences × #embeds), and the
// one-regex `<img>` form rescanning from every `<img` to the next `>` — so a 2 MB file of repeated
// fences and embeds, or of `<img ` with no `>`, took the host past the deadline on every attempt,
// and no region could be placed on any figure in it (measured). The embeds test pins the cost and
// the agreement with the one-regex reading.
const LABEL = '(?:\\\\.|[^\\[\\]\\\\])*';
const IMG_INLINE = new RegExp('!\\[(' + LABEL + ')\\]\\([ \\t]*(?:<([^<>\\n]*)>|([^\\s()]*(?:\\([^\\s()]*\\)[^\\s()]*)*))(?:[ \\t]+(?:"[^"]*"|\'[^\']*\'|\\([^()]*\\)))?[ \\t]*\\)', 'g');
const IMG_FULL_REF = new RegExp('!\\[(' + LABEL + ')\\]\\[(' + LABEL + ')\\]', 'g');
const IMG_SHORT_REF = new RegExp('!\\[(' + LABEL + ')\\](?![\\[(])', 'g');
const IMG_OPEN = /<img\b/gi;
const SRC_ATTR = /\bsrc[ \t]*=[ \t]*/gi;
const NOT_BARE = /[\s"'>]/;
const REF_DEF = /^ {0,3}\[((?:\\.|[^\[\]\\])+)\]:[ \t]*<?([^\s>]+)>?/gm;
const normLabel = (s) => s.trim().replace(/\s+/g, ' ').toLowerCase();

// Offsets of the text's fenced code blocks, [start, end).
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

// Whether offset i lies in one of the fenced ranges: a binary search, since fencedRanges walks the
// lines once and so yields them sorted and disjoint.
function inFencedRange(fences, i) {
  let lo = 0;
  let hi = fences.length;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (fences[mid][1] <= i) lo = mid + 1;
    else hi = mid;
  }
  return lo < fences.length && fences[lo][0] <= i;
}

// The raw `<img …>` tags of a text, each {start, end, dest}, in order: exactly the matches of
//   /<img\b[^>]*?\bsrc[ \t]*=[ \t]*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))[^>]*>/gi
// (the panel's regex), without its cost. That regex rescans from every `<img` to the next `>`, so a
// text of repeated `<img ` with no `>` costs #tags × distance. Read as the regex reads: from each
// `<img\b`, its window runs to the first `>` after it; the tag's src is the first `src=` in the
// window whose value can be read — a quoted value runs to its closing quote, even across `>` and
// newlines, a bare one to the next whitespace, quote or `>` — and is followed by a `>` somewhere
// later; the match runs through the value to the next `>`. Linear because every position asked of
// the cursors below is asked in increasing order, a tag's window is scanned for `src=` at most once
// (when a tag has no usable src, no `<img` between it and its `>` has one either — their windows
// are the tail of its own — so the walk resumes past that `>`), and a value's chars are inside the
// match they complete.
function htmlImgTags(text) {
  const out = [];
  const lastGt = text.lastIndexOf('>');
  if (lastGt < 0) return out;
  // Monotone cursors: the first '>' / '"' / "'" at or after the position last asked, or -1.
  let gt = -1;
  const nextGt = (i) => { if (gt < i) gt = text.indexOf('>', i); return gt; };
  const quote = { '"': -1, "'": -1 };
  const nextQuote = (ch, i) => { if (quote[ch] < i) quote[ch] = text.indexOf(ch, i); return quote[ch]; };
  let srcAt = -1;   // the `src=` last found: its offset, and the offset past its `=` and spaces
  let srcEnd = -1;
  const nextSrc = (i) => {
    if (srcAt >= i) return srcAt;
    SRC_ATTR.lastIndex = i;
    const m = SRC_ATTR.exec(text);
    if (m) { srcAt = m.index; srcEnd = SRC_ATTR.lastIndex; } else { srcAt = Infinity; srcEnd = Infinity; }
    return srcAt;
  };
  let pos = 0;
  let m;
  while (pos <= lastGt) {
    IMG_OPEN.lastIndex = pos;
    m = IMG_OPEN.exec(text);
    if (!m) break;
    const start = m.index;
    const winEnd = nextGt(start + 4);
    if (winEnd < 0) break;
    let dest;
    let valueEnd = -1;
    for (let from = start + 4; nextSrc(from) < winEnd; from = srcAt + 1) {
      const v = srcEnd;
      const ch = text[v];
      if (ch === '"' || ch === "'") {
        const close = nextQuote(ch, v + 1);
        if (close >= 0 && close < lastGt) { dest = text.slice(v + 1, close); valueEnd = close + 1; break; }
      } else if (v < lastGt && !NOT_BARE.test(ch)) {
        let e = v + 1;
        while (e < text.length && !NOT_BARE.test(text[e])) e++;
        dest = text.slice(v, e); valueEnd = e; break;
      }
    }
    if (valueEnd < 0) { pos = winEnd + 1; continue; }
    const end = nextGt(valueEnd) + 1;
    out.push({ start, end, dest });
    pos = end;
  }
  return out;
}

export function imageEmbeds(text) {
  const fences = fencedRanges(text);
  const inFence = (i) => inFencedRange(fences, i);
  const defs = new Map();
  let m;
  REF_DEF.lastIndex = 0;
  while ((m = REF_DEF.exec(text))) if (!inFence(m.index)) defs.set(normLabel(m[1]), m[2]);
  const out = [];
  const push = (start, len, dest) => {
    if (dest !== undefined && !inFence(start)) out.push({ start, end: start + len, dest });
  };
  for (const re of [IMG_INLINE, IMG_FULL_REF, IMG_SHORT_REF]) re.lastIndex = 0;
  while ((m = IMG_INLINE.exec(text))) push(m.index, m[0].length, m[2] ?? m[3] ?? '');
  while ((m = IMG_FULL_REF.exec(text))) push(m.index, m[0].length, defs.get(normLabel(m[2] || m[1])));
  while ((m = IMG_SHORT_REF.exec(text))) push(m.index, m[0].length, defs.get(normLabel(m[1])));
  for (const t of htmlImgTags(text)) push(t.start, t.end - t.start, t.dest);
  out.sort((a, b) => a.start - b.start);
  return out.filter((e, i) => !i || e.start >= out[i - 1].end);   // a shortcut form inside a longer one: the longer wins
}

// An anchored region's `src` must be a figure the anchored passage embeds: the panel finds the
// picture to paint on by the anchor and judges staleness by the src, so a src the passage does not
// name splits the two — the rectangle on one figure, the stale check on another — and hands any
// client a hash of whatever in-root file it cares to name. The dests are read from the whole text
// (a reference-style embed's destination sits in a definition elsewhere in the file) and the
// passage's embeds are the ones overlapping the located range; the embed's exact range, which the
// panel sends, and a whole line around it both qualify. A refusal, not a caller bug: a reference
// definition can change on disk between the drag and Enter.
function checkEmbedNamesSrc(ctx, text, from, to, src) {
  const dests = imageEmbeds(text).filter((e) => e.start < to && e.end > from).map((e) => e.dest);
  if (dests.includes(src)) return;
  const named = dests.length ? `embeds ${dests.map((d) => tilde(d)).join(', ')}, not ${tilde(src)}` : `embeds no figure, so nothing there is ${tilde(src)}`;
  throw new Refusal('figure-mismatch', `the passage this comment is anchored to in ${ctx.shown} ${named}; a region on that figure cannot stand on this passage; nothing was changed`);
}

// The figure an anchored region comment is on when its stored target names no src: the contract's
// own shape (plans/file-review.md, "The contract": the embed line's anchor plus {kind, region,
// hash}), which the panel never writes but another writer following the plan can leave. The
// anchored passage, located now, decides — the reading checkEmbedNamesSrc makes of a src the caller
// names, with no src to compare: {src} when the passage embeds exactly one distinct destination (a
// reference-style embed's through its definition, the case the anchor's quote alone cannot answer);
// else {src: null, code, reason} — the passage gone or ambiguous (locateExact's codes, the anchor
// unreadable counted with them) or embedding no figure or several (`no-figure`). The reason is a
// fragment for the person, as the hash reasons are. `embeds` is imageEmbeds(text), read once per
// reply by the caller.
function passageFigure(ctx, text, c, embeds) {
  const id = String(c.id);
  let anchor;
  try {
    anchor = validateAnchor(c.anchor);
  } catch (e) {
    return { src: null, code: 'anchor-not-found', reason: `the anchor of comment ${id} in ${ctx.shown} cannot be read (${e.message}), so which figure it is on cannot be told` };
  }
  const loc = locateExact(text, anchor, undefined);
  if (loc.error) return { src: null, code: loc.error, reason: `the passage of comment ${id} could not be placed in ${ctx.shown} (${loc.error}), so which figure it is on cannot be told` };
  const dests = [...new Set(embeds.filter((e) => e.start < loc.to && e.end > loc.from).map((e) => e.dest))];
  if (dests.length === 1) return { src: dests[0] };
  const named = dests.length ? `embeds ${dests.map((d) => tilde(d)).join(', ')}` : 'embeds no figure';
  return { src: null, code: 'no-figure', reason: `the passage of comment ${id} in ${ctx.shown} ${named}, so which figure it is on cannot be told` };
}

// Whether a comment's stored target is the contract's src-less shape on an anchored passage: a
// target object naming no usable src, under an anchor. A standalone image's target (no anchor) and
// a region another writer left on a text file with no embed line are not — nothing there names a
// figure by its passage.
function namesFigureByPassage(c) {
  return !!(c && c.anchor != null && c.target && typeof c.target === 'object' && !Array.isArray(c.target)
    && (typeof c.target.src !== 'string' || !c.target.src));
}

// The store as a reply carries it: every comment in the contract's src-less shape with the src its
// passage tells (passageFigure), the stored target's keys kept and `src` after them, so the panel
// keys the stale check and the re-place on it; a comment whose passage cannot tell is left as it
// is. Which srcs were told this way, and why the rest could not be, go beside the store in the
// reply (`derivedSrcs`, `derivedSrcReasons`, per comment id): a read never rewrites the sidecar,
// and the reply says where its store differs from the disk. `text` is the file as the load read
// it; a store with such a comment and no text is a program error (every verb that loads a sidecar
// reads the text to rebase it), never a silent "unknown".
function derivedSrcsFor(ctx, store, text) {
  const srcs = {};
  const reasons = {};
  if (!store || !(store.comments || []).some(namesFigureByPassage)) return { store, srcs, reasons };
  if (typeof text !== 'string') throw new Error(`a comment on ${ctx.shown} names its figure by its passage, and the file's text was not read`);
  const embeds = imageEmbeds(text);
  const comments = store.comments.map((c) => {
    if (!namesFigureByPassage(c)) return c;
    const f = passageFigure(ctx, text, c, embeds);
    if (f.src == null) {
      reasons[String(c.id)] = f.reason;
      return c;
    }
    srcs[String(c.id)] = f.src;
    return { ...c, target: { ...c.target, src: f.src } };
  });
  return { store: { ...store, comments }, srcs, reasons };
}

// `too-large`: only verbs that write the file check it, before any write (the kernel's cap).
export function checkTooLarge(shown, text) {
  if (Buffer.byteLength(text, 'utf8') > TEXT_MAX_BYTES) {
    throw new Refusal('too-large', `${shown} exceeds the 2 MB text cap, so its contents cannot be written from the dashboard`);
  }
}

// `not-text`: the verbs that write the file refuse a file whose bytes are not UTF-8 text, before
// any write. Writing back the lossy decode would replace every invalid sequence with U+FFFD and
// destroy the file; the sidecar-only verbs never write the file, so they take such a file as the
// CLIs do.
function checkIsText(shown, file) {
  if (!file.isText) {
    throw new Refusal('not-text', `${shown} is not UTF-8 text, so a change in it cannot be rejected from the dashboard: writing the file back would rewrite it from a lossy decode and destroy it; nothing was changed`);
  }
}

// Apply the engine's reverse edits ({from, to, insert} in CURRENT coordinates, highest offset
// first — the order engine.rejectSuggestions and rejectAll return them in, so no edit shifts the
// ones after it) to a string: the CodeMirror dispatch for a file with no editor. Adapted from
// track-changents' obsidian/src/track-rollup.js applyEditsToText with one change: an edit that
// does not fit the text, or that reaches past the one before it, THROWS instead of being skipped.
// A skipped edit would write a file with some changes reverted and others silently kept while
// the sidecar says they are all gone; a thrown one is a program error the kernel reports as such.
export function applyEdits(text, edits) {
  let out = String(text == null ? '' : text);
  let floor = out.length; // the lowest offset an applied edit reached; the next may not cross it
  for (const e of Array.isArray(edits) ? edits : []) {
    const from = e && e.from;
    const to = e && (e.to == null ? e.from : e.to);
    if (!Number.isInteger(from) || !Number.isInteger(to) || from < 0 || to < from || to > floor) {
      throw new Error(`reverse edit ${JSON.stringify(e)} does not fit the text (${out.length} chars, next edit must end at or before ${floor})`);
    }
    out = out.slice(0, from) + (e.insert == null ? '' : String(e.insert)) + out.slice(to);
    floor = from;
  }
  return out;
}

// Atomic write of a file's new text, for the verbs that change file bytes (reject, save): a
// temp file in the same directory whose name does not end in .json (so the other hosts' sidecar
// scans skip it), written through the realpath (never over a symlink), mode preserved, renamed
// into place. Returns the new mtime string. Reject writes through it; Slice 5's save will too.
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
// PDF page) is not attached here: doComment validates it and stamps the hash (stampTarget) once
// the anchor, if any, is placed. A CHANGE comment (`args.suggestionId`, the
// Reply on a change's card) has no anchor and no target, carries `suggestionId`, and takes its id
// from the change's current offset the way the other hosts' change threads do; the change must be
// pending in `suggestions`, else `{error: 'no-change'}`. The other hosts bind a thread to a change
// on this field (track-edit --thread sets it on a passage comment too), so accept's resolve pass
// and the panel's card both read it.
export function buildComment(text, args, now, suggestions) {
  const note = requireNote(args);
  let c;
  if (args.suggestionId != null) {
    if (args.anchor != null) throw new BadRequest('a change comment (suggestionId) takes no anchor');
    if (args.target != null) throw new BadRequest('a change comment (suggestionId) takes no target');
    if ((typeof args.suggestionId !== 'string' && typeof args.suggestionId !== 'number') || args.suggestionId === '') {
      throw new BadRequest('suggestionId must be a non-empty string');
    }
    const op = (suggestions || []).find((s) => s && String(s.id) === String(args.suggestionId));
    if (!op) return { error: 'no-change' };
    c = { id: `${now}-${engine.span(op).a}`, author: AUTHOR, ts: now, suggestionId: op.id, body: note, replies: [], resolved: false };
    return { comment: c };
  }
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
    // Where the anchor landed, for the checks a region comment makes on the passage (doComment).
    return { comment: c, range: { from: loc.from, to: loc.to } };
  }
  return { comment: c };
}

// ── the reply ───────────────────────────────────────────────────────

function reply(ctx, state, extra) {
  const { root, paths, store: loaded, text, fileMtimeNs } = state;
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
  // The store the reply carries: on a text file, with the src every comment in the contract's
  // src-less shape names by its passage (derivedSrcsFor); a media file's comments have no anchor,
  // so its store goes as loaded.
  const media = isMediaPath(ctx.abs);
  const derived = media ? null : derivedSrcsFor(ctx, loaded, text);
  const store = derived ? derived.store : loaded;
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
  // What a region comment's target.hash is compared with, on every reply (each one is the status
  // the panel holds next): a media file's own bytes, or the figures a text file's comments name —
  // and beside every null, why (fileHashReason: a string or null; embeddedHashReasons: one entry per
  // null src), so the panel can say which figure could not be checked and what stopped it. On a
  // text file, beside them, which comments name their figure by their passage (derivedSrcs) and
  // why the rest of that shape could not (derivedSrcReasons), per comment id. The same reasons go
  // to stderr, which the kernel keeps when a call fails.
  if (media) {
    const fh = fileHashFor(ctx);
    out.fileHash = fh.hash;
    out.fileHashReason = fh.reason || null;
    if (fh.reason) process.stderr.write(`file-comments-host: ${fh.reason}\n`);
  } else {
    const eh = embeddedHashesFor(ctx, root, store);
    out.embeddedHashes = eh.hashes;
    out.embeddedHashReasons = eh.reasons;
    out.derivedSrcs = derived.srcs;
    out.derivedSrcReasons = derived.reasons;
    for (const reason of [...Object.values(eh.reasons), ...Object.values(derived.reasons)]) process.stderr.write(`file-comments-host: ${reason}\n`);
  }
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
// runs every check the verb itself can refuse on (the anchor, the comment id, the change id a
// change comment binds to) and returns the
// step that changes the store; it runs BEFORE the landmark, so a refused verb leaves the disk as
// it found it. Ordered the other way, a passage comment whose passage was edited away between the
// selection and Enter left an empty `.trackchanges/` beside a loose file — a root for every later
// verb and for the CLIs — under a refusal that named no such thing. `store` is null in `plan` when
// no sidecar exists yet (a first comment); the seed is minted after the landmark, whose root
// gives the seed its relative path. `root` is null in `plan` for the same loose file; a check that
// needs the root then uses the one the landmark is about to make, the file's own directory.
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
  const apply = plan(store, file.text, root);
  if (!root) {
    root = createLandmark(ctx);
    paths = pathsFor(root, ctx.abs);
  }
  if (!store) store = seedStore(paths.rel);
  apply(store);
  saveStore(root, paths.storePath, store, file.text);
  return reply(ctx, { root, paths, store: reloadSaved(ctx, paths, file.text), ...file });
}

function noChange(ctx, ids) {
  const list = ids.map(String);
  const what = list.length === 1 ? `change ${list[0]} is` : `changes ${list.join(', ')} are`;
  return new Refusal('no-change', `${what} no longer pending in ${ctx.shown} — reload and retry`);
}

// comment {note}, {anchor, note}, {suggestionId, note}, {target, note}, {anchor, target, note}: the
// target's shape is checked first (a caller bug, before any disk read the anchor needs), the
// anchor is placed, the anchored passage is checked to embed the figure the target names
// (`figure-mismatch`), and only then is the figure hashed — the region's own refusals
// (`unreadable` for a src outside the root or unreadable, `too-large` past the viewer's cap, and
// `figure-changed` when the bytes are not the ones the request's fence.figureHash says were shown)
// come after the passage's, and all of them before the landmark and the write. The fence's shape is
// read first of all, before any disk read, as every fence key is.
function doComment(ctx) {
  const figureHash = figureFence(ctx);
  if (figureHash != null && ctx.args.target == null) throw new BadRequest('fence.figureHash fences the figure a region is on, and this comment has no target');
  return withSidecar(ctx, true, (store, text, root) => {
    const target = ctx.args.target == null ? null : validateTarget(ctx.args.target, ctx.args.anchor != null);
    const built = buildComment(text, ctx.args, Date.now(), store ? store.suggestions : []);
    if (built.error === 'anchor-not-found') {
      throw new Refusal('anchor-not-found', `the selected passage is no longer in ${ctx.shown} — reload and select it again`);
    }
    if (built.error === 'anchor-ambiguous') {
      throw new Refusal('anchor-ambiguous', `the selected passage occurs more than once in ${ctx.shown} with the same surroundings, so a comment on it could not be placed again later — select more of the text around it`);
    }
    if (built.error === 'no-change') throw noChange(ctx, [ctx.args.suggestionId]);
    if (target) {
      if (target.src != null) checkEmbedNamesSrc(ctx, text, built.range.from, built.range.to, target.src);
      built.comment.target = stampTarget(ctx, root || path.dirname(ctx.abs), target, figureHash);
    }
    return (s) => { s.comments.push(built.comment); };
  });
}

// retarget {commentId, target}: the re-place gesture on a region comment — a new rectangle (and
// for a PDF a page) over the same figure, the hash recomputed from the bytes as they are now, so a
// comment the figure's regeneration made stale is current again. The comment must exist (else
// `no-comment`) and be a region comment (a target on a comment that has none is a caller bug); an
// embedded figure's new target names its src as the old one did — the SAME src, checked: a
// re-place moves the rectangle, never the figure, and a src that differed would leave the anchor
// (and so the painted rectangle) on one figure while the stale check followed another. A stored
// target with an anchor but no src (the contract's own shape, which another writer can leave) is
// re-placed either way: a request naming a src takes it only when the anchored passage, located
// now, embeds it; a request naming none — the panel's, when no reply could tell the figure, or a
// caller following the plan — takes the figure that passage embeds (passageFigure), and a passage
// that cannot tell refuses with its reason rather than crashing as a caller bug. Either way the
// target written carries its src. A stored src must be named by the request, as ever: the panel's
// store view carries it (stored, or told by the passage on a reply), so a request without one is a
// caller bug. A standalone one's target has none — the anchor decides, as it does for comment.
// Fenced on the sidecar like every sidecar write, and on the figure's bytes when the request says
// which it saw (fence.figureHash, checked in stampTarget: a figure regenerated again between the
// status that showed it stale and this re-place refuses `figure-changed`, and is never stamped with
// bytes the person has not seen); the anchor, id, body and replies stay as they were; nothing is
// appended to the comments log, since a re-placed rectangle is not a decision.
function doRetarget(ctx) {
  const id = requireCommentId(ctx.args);
  const figureHash = figureFence(ctx);
  if (ctx.args.target == null) throw new BadRequest('retarget needs target: {kind, region, page?, src?}');
  return withSidecar(ctx, false, (store, text, root) => {
    const c = findComment(store, id);
    if (!c) throw new Refusal('no-comment', `comment ${String(id)} is not among the comments for ${ctx.shown} — reload and retry`);
    if (!c.target || typeof c.target !== 'object') throw new BadRequest(`comment ${String(id)} has no region to re-place`);
    const embedded = c.anchor != null;
    const stored = typeof c.target.src === 'string' && c.target.src ? c.target.src : null;
    let asked = ctx.args.target;
    let told = false;   // the src is the passage's own, located and checked in the telling
    if (embedded && stored == null && asked && typeof asked === 'object' && !Array.isArray(asked) && asked.src == null) {
      const f = passageFigure(ctx, text, c, imageEmbeds(text));
      if (f.src == null) throw new Refusal(f.code, `${f.reason}; a re-place needs the figure named in the comment's target (src); nothing was changed`);
      asked = { ...asked, src: f.src };
      told = true;
    }
    const validated = validateTarget(asked, embedded);
    if (validated.src != null && !told) {
      if (stored != null) {
        if (validated.src !== stored) throw new BadRequest(`retarget keeps the figure: comment ${String(id)} is on ${tilde(stored)}, and target.src names ${tilde(validated.src)}`);
      } else {
        const loc = locateExact(text, validateAnchor(c.anchor), undefined);
        if (loc.error) throw new Refusal(loc.error, `the passage of comment ${String(id)} could not be placed in ${ctx.shown} (${loc.error}), so which figure it embeds cannot be told — reload and retry`);
        checkEmbedNamesSrc(ctx, text, loc.from, loc.to, validated.src);
      }
    }
    const target = stampTarget(ctx, root || path.dirname(ctx.abs), validated, figureHash);
    return (s) => { findComment(s, id).target = target; };
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

// ── accept and reject ───────────────────────────────────────────────

function requireIds(ctx) {
  const ids = ctx.args.ids;
  if (!Array.isArray(ids) || !ids.length) throw new BadRequest(`${ctx.verb} needs ids: a non-empty array of change ids`);
  for (const id of ids) {
    if ((typeof id !== 'string' && typeof id !== 'number') || id === '') throw new BadRequest('every change id must be a non-empty string');
  }
  return ids;
}

// The file and its sidecar for a decision, checked in the order every fenced verb uses: the
// request's shape (a missing fence key is a caller bug whatever the disk says), the file, the
// sidecar fence, for the file-writing verbs the file fence too, the config, then the load. `store`
// is null when there is no sidecar, which for a decision means nothing is pending.
function loadForDecision(ctx, writesFile) {
  for (const k of writesFile ? ['storeMtimeNs', 'fileMtimeNs'] : ['storeMtimeNs']) {
    if (typeof ctx.fence[k] !== 'string') throw new BadRequest(`fence.${k} is required for ${ctx.verb}`);
  }
  const file = readFile(ctx);
  const root = findVaultRoot(ctx.abs);
  const paths = root ? pathsFor(root, ctx.abs) : null;
  requireFence(ctx, 'storeMtimeNs', paths ? statNs(paths.storePath) : null, 'store-moved', `the comments for ${ctx.shown}`);
  if (writesFile) requireFence(ctx, 'fileMtimeNs', file.fileMtimeNs, 'file-moved', `the file ${ctx.shown}`);
  if (paths) checkConfig(ctx, paths);
  const store = root ? loadOrRefuse(ctx, paths, file.text) : null;
  return { file, root, paths, store };
}

// The pending changes a verb decides, as toHunks rows in document order: every one for the -all
// verbs (none pending refuses no-change), else the caller's ids, each of which must still be
// pending. A change a later track-edit coalesced away, or one an earlier decision removed, refuses
// `no-change` by id and the whole request with it — nothing is decided under a name that no longer
// means what the caller saw. The rows carry the store's own id values, which the engine filters by.
function decidedChanges(ctx, store, all) {
  const hunks = store ? engine.toHunks(store.suggestions) : [];
  if (all) {
    if (!hunks.length) throw new Refusal('no-change', `no changes are pending in ${ctx.shown} — reload and retry`);
    return hunks;
  }
  const want = requireIds(ctx).map(String);
  const byId = new Set(hunks.map((h) => String(h.id)));
  const missing = want.filter((id) => !byId.has(id));
  if (missing.length) throw noChange(ctx, missing);
  const set = new Set(want);
  return hunks.filter((h) => set.has(String(h.id)));
}

// What the log remembers of a decision: the ids and their texts at the time, so the decision
// survives the change leaving the sidecar (and deriveUnsent counts one per element).
function changesOf(hunks) {
  return hunks.map((h) => ({ id: h.id, oldText: h.oldText, newText: h.newText }));
}

// The sidecar after a decision, or null once pruneIfClean has removed it. An emptied sidecar (no
// changes, no comments, no detached ops — pruneIfClean's own judgement, re-read from disk) is
// deleted, so the file returns to the absent state and the client renders it as such; a comment,
// resolved or not, keeps the sidecar, as does a detached op the person has not dealt with.
function afterDecision(ctx, paths, store, text) {
  if (pruneIfClean(paths.storePath, store)) return null;
  return reloadSaved(ctx, paths, text);
}

// accept / accept-all: the engine drops the records and the file is untouched (a change's effect
// is already in the text). Every comment bound to an accepted change by `suggestionId` is marked
// resolved and KEPT — a stated divergence from the Obsidian host, which drops them — so the ids a
// sent message named still answer to track-reply. The match is on the field alone, anchor or not:
// track-edit --thread gives a passage comment a suggestionId while it keeps its anchor.
function doAccept(ctx, all) {
  const { file, root, paths, store } = loadForDecision(ctx, false);
  const decided = decidedChanges(ctx, store, all);
  const ids = decided.map((h) => h.id);
  const set = new Set(ids.map(String));
  store.suggestions = (all ? engine.acceptAll(store.suggestions) : engine.acceptSuggestions(store.suggestions, ids)).suggestions;
  for (const c of store.comments) {
    if (c && c.suggestionId != null && set.has(String(c.suggestionId))) c.resolved = true;
  }
  saveStore(root, paths.storePath, store, file.text);
  appendLog(paths.logPath, logEntry('accept', { changes: changesOf(decided) }));
  return reply(ctx, { root, paths, store: afterDecision(ctx, paths, store, file.text), ...file }, { accepted: ids });
}

// Put the sidecar back as it was before a reject whose file write failed: the prior bytes, or
// nothing when there were none (a reject always finds a sidecar, so that branch is a guard).
// Replaced by temp-and-rename like every other sidecar write, with a name no .json scan matches.
function restoreSidecar(storePath, prior) {
  if (prior == null) { fs.unlinkSync(storePath); return; }
  const tmp = `${storePath}.romp-fc-restore-${process.pid}.tmp`;
  fs.writeFileSync(tmp, prior);
  fs.renameSync(tmp, storePath);
}

// reject / reject-all: the engine's reverse edits give the new text, applied by applyEdits and
// checked against the file before anything is written (not-text, too-large). Then the order
// track-edit uses: the sidecar first, saved against the NEW text so its fingerprint describes the
// file about to exist, then the file through writeFileAtomic; if the file write fails the prior
// sidecar bytes go back and the verb refuses `unreadable` with the OS text. The survivors come
// back from the engine remapped into post-reject coordinates; reloading the saved sidecar against
// the new text re-verifies them the way every later load will.
function doReject(ctx, all) {
  const { file, root, paths, store } = loadForDecision(ctx, true);
  const decided = decidedChanges(ctx, store, all);
  const ids = decided.map((h) => h.id);
  checkIsText(ctx.shown, file);
  for (const h of decided) {
    // The load-time rebase placed every kept op where its text is; a row that disagrees with the
    // file is an invariant broken upstream, and a reject written from it would eat other text.
    if (file.text.slice(h.curFrom, h.curTo) !== h.newText) {
      throw new Error(`change ${h.id} does not match ${ctx.shown} at ${h.curFrom}..${h.curTo} after the rebase; nothing was changed`);
    }
  }
  const res = all ? engine.rejectAll(store.suggestions) : engine.rejectSuggestions(store.suggestions, ids);
  const newText = applyEdits(file.text, res.edits);
  checkTooLarge(ctx.shown, newText);
  let prior = null;
  try { prior = fs.readFileSync(paths.storePath); } catch (e) { if (!e || e.code !== 'ENOENT') throw e; }
  store.suggestions = res.suggestions;
  saveStore(root, paths.storePath, store, newText);
  let fileMtimeNs;
  try {
    fileMtimeNs = writeFileAtomic(ctx.abs, newText);
  } catch (e) {
    const why = tildeText(e && e.message ? e.message : String(e));
    let restored = 'the comments file was put back as it was and nothing was changed';
    try { restoreSidecar(paths.storePath, prior); } catch (e2) {
      restored = `the comments file could not be put back either (${tildeText(e2 && e2.message ? e2.message : String(e2))}) — reload before doing anything else`;
    }
    throw new Refusal('unreadable', `cannot write ${ctx.shown}: ${why}; ${restored}`);
  }
  appendLog(paths.logPath, logEntry('reject', { changes: changesOf(decided) }));
  return reply(ctx, { root, paths, store: afterDecision(ctx, paths, store, newText), text: newText, fileMtimeNs }, { rejected: ids });
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
  accept: (ctx) => doAccept(ctx, false),
  'accept-all': (ctx) => doAccept(ctx, true),
  reject: (ctx) => doReject(ctx, false),
  'reject-all': (ctx) => doReject(ctx, true),
  retarget: doRetarget,
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
