#!/usr/bin/env node
// The node host script behind the Files pane's comments panel (plans/file-review.md, "The host
// script" and "The comments log"). The kernel runs it once per verb, on the machine that holds the
// file, with one JSON request on stdin and reads one JSON object from stdout:
//
//   stdin   {"verb", "path", "args": {...}, "fence": {...}|null}
//   stdout  {"ok": true, "verb", "root", "storePath", "trackedBy", "agentTooling", "fileMtimeNs",
//            "storeMtimeNs", "configMtimeNs", "store", "hunks", "unsent", "log", "logTruncated",
//            "fileHash" | "embeddedHashes", "baseline"?, "logged"?, "logWarning"?, "accepted"?,
//            "rejected"?}
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
//   * the same for the decisions a `save` carries from the editor: every accepted or rejected id must
//     be rooted in a change the sidecar holds or the comments log already records as decided — the id
//     itself or a fragment of it (`<id>~n`, the engine's split scheme) — else `no-change` by id and
//     nothing written; an id the sidecar never held would otherwise stand in the append-only log as a
//     decision nobody took and be counted to the session (decisionRoots, doSave). And the same for the
//     change RECORDS a `save` carries: every record's id must be rooted the same way, else `desync` by
//     id and nothing written (recordsNeverPending). The records are written into the sidecar under the
//     author and session id they name, so an unrooted one would stand there as a change the session
//     made and never did — and the next save or the panel's Reject would then find it rooted, log a
//     decision on it and count it to the session. A real editor never submits such an id: its field is
//     seeded from the sidecar's records, the engine splits mint `<id>~n` (mapOpsThroughChange), and the
//     chunk's re-mint keeps the parent (editor-chunk's freshIds). And a record rooted in a change the
//     sidecar holds must name that change's author and session id (recordsMisattributed), else
//     `desync` by id and nothing written: the editor's remap copies both onto every fragment it splits
//     off (mapOpsThroughChange) and keeps the earlier record's on a merge (coalesceOps), so a record
//     that differs is not the editor's — written, it would put the session's change under another
//     author and session id in the sidecar, the record every change card shows and every later verb
//     reads as who changed what. The texts and `ts` stay the client's word: no equality against the
//     sidecar holds for them (a split shortens newText, a merge concatenates the texts and takes the
//     earlier ts), a record the log alone roots (the undo of a landed accept) has no author on record
//     to compare, and the decisions' texts come from a remap this script never saw (requireDecisions
//     checks the shape, decisionRoots the id). The sidecar is itself a file the viewer edits (the
//     plan: a sidecar hand-edited in the viewer traces like any other file), so none of this closes a
//     door that stands open beside it; it keeps the records this verb writes consistent with the
//     changes they claim to be;
//   * a region comment's `target.hash` is this script's sha256 of the figure's BYTES (Slice 3), never
//     the client's value and never a hash of the lossy text: for a standalone image or PDF the file's
//     own, for a figure embedded in a markdown file the bytes of the `src` the embed names, resolved
//     against the file's directory and refused unless it is a regular file inside the project root.
//     Every reply carries the current hash to compare against — `fileHash` on a media file,
//     `embeddedHashes` per src on a text file — with null for "unknown" (unreadable, or past the
//     size cap), which is never the same as stale;
//   * once a verb's primary write has landed — the file (reject, save), the sidecar (accept), the
//     config (set-tracked) — nothing after it fails the verb: a comments-log append that fails, or a
//     log or a sidecar that cannot be read back, is reported in the reply (`logged: false`,
//     `logWarning` with the OS text), the rule the kernel's saveFile path keeps for log-edit (a failed
//     append is reported in the reply and never fails the save). A non-zero exit there would report a
//     write that landed as one that did not: the kernel sends no trace for a failed verb, so the
//     session whose file changed is never told, and the client keeps a buffer it believes unsaved
//     behind a fence the write has already moved (appendLanded, settleLanded, reply's `landed`);
//   * `save` refuses what the kernel's saveFile refuses, before any write, so the second door widens
//     nothing: a name outside the viewer's text scope (TEXT_EXT and TEXT_NAMES — the kernel's
//     _is_text_path, pinned against its source by test; the kernel refuses the name before this script
//     runs, and this script refuses it again so the answer does not depend on the route) and a file
//     past the 2 MB cap on disk, refused on the stat before its bytes are read, as _save_file refuses
//     (checkTextPath, readFile's `cannot`, checkDiskSize). The NAME rule is save's alone: save writes
//     the client's content, and the allowlist is what bounds the text the dashboard may write under a
//     name. reject and reject-all write back only the text the sidecar recorded — the engine's reverse
//     edits over the file as it is, chosen by id — so they keep Slice 2's scope, every tracked file
//     that is UTF-8 text whatever its name, the scope the CLIs record changes in: a session's
//     track-edit in a .tex or .hs file makes a change card the panel shows, and the card's Reject must
//     be honored from the dashboard as it was before Slice 5 (the review, 2026-09-06, round 3). The
//     SIZE cap they share, a rule about bytes rather than names;
//   * nothing is written on a client's word that the kernel cannot carry back: the reply a verb would
//     send is built and measured before the write (checkReplyFits, REPLY_MAX_BYTES — the kernel's
//     _FILE_COMMENTS_REPLY_MAX) and refuses `too-large` past it. Over that cap the kernel kills this
//     process and discards its stdout AFTER the write landed, then does the same to every later
//     `status` on the file, so one oversized record or note would lock the file's comments until the
//     sidecar was fixed by hand;
//   * a path inside .trackchanges/ — the sidecar, the config, the log — is never logged (the log
//     would record itself), the kernel's _under_trackchanges rule for saveFile; and `save` logs an
//     edit only for a file that already has a sidecar, a comments log, or a tracked flag, the rule
//     log-edit follows (a save that created the log would make every later plain save of a file
//     nobody tracked logged too).
// The file's text is read only when a verb needs it: to rebase an existing sidecar, to place an
// anchor, to stamp a fingerprint. `status` runs on every viewer open, a file the viewer refuses
// above 2 MB included, so on a file with no sidecar it stats the file and reads nothing (statFile).
// The verbs that change the FILE (reject, reject-all, save) fence on its mtime too, refuse a file that
// is not UTF-8 text (`not-text`) or would exceed the 2 MB cap (`too-large`) before any write, write the
// sidecar first and the file second, and put the prior sidecar back if the file write fails — the
// order track-edit uses, so a reader never finds a file whose changes its sidecar does not describe.
// `save` (Slice 5) is the editor's Save over a file with pending changes: the new text and the
// change records the editor remapped as the person typed arrive together, every record is checked
// against the text (`desync` names the first that does not fit), and the sidecar, the file and the
// comments log (an `edit` entry plus an accept and a reject entry for what was decided in the
// editor) are written in this one process.
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
// The kernel's _FILE_COMMENTS_REPLY_MAX: the most stdout it holds for one reply before it kills this
// process and discards what it read. checkReplyFits measures the reply a verb would send before a
// write that carries a client's text into the sidecar or the log, with REPLY_SLACK left for the
// stand-ins the estimate uses (the mtimes the write will set, the reloaded sidecar's normalization,
// the tracking verdict and the hashes, each a few dozen bytes).
export const REPLY_MAX_BYTES = 16 * 1024 * 1024;
const REPLY_SLACK = 64 * 1024;
// The kernel's _TEXT_EXT and _TEXT_NAMES (_is_text_path): the files GET /file serves as text and
// saveFile writes. `save` keeps to the same names, so the dashboard writes no text of its own through
// this script under a name it would not write through saveFile; reject, which writes back only what
// the sidecar recorded, is not bound by them (checkTextPath). Mirrored, not imported; the scope test
// pins both sets against the kernel's source.
export const TEXT_EXT = new Set((
  'txt md markdown rst adoc org text log err out diff patch csv tsv'
  + ' py pyi rb rs go java kt kts swift c h cc cpp hpp cs m mm scala clj lua pl php r jl dart'
  + ' js jsx mjs cjs ts tsx json jsonc json5 yaml yml toml ini cfg conf properties'
  + ' html htm xml svg css scss sass less vue svelte astro'
  + ' sh bash zsh fish ps1 bat cmd nix tf hcl proto graphql gql sql prisma'
  + ' lock mod sum gradle cmake mk make bazel bzl gemspec podspec bats'
).split(' ').filter(Boolean));
export const TEXT_NAMES = new Set([
  'makefile', 'dockerfile', 'jenkinsfile', 'procfile', 'rakefile', 'gemfile', 'brewfile',
  'vagrantfile', 'caddyfile', 'justfile', 'license', 'licence', 'notice', 'authors',
  'changelog', 'readme', 'todo', 'codeowners', '.gitignore', '.gitattributes',
  '.dockerignore', '.editorconfig', '.env', '.bashrc', '.zshrc', '.profile',
]);
// The sidecar directory, the kernel's _TRACKCHANGES_DIR: a path inside one is the tracking
// machinery itself, and an edit to it is never logged.
export const TRACKCHANGES_DIR = '.trackchanges';
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

// The verbs through Slice 5 (retarget is Slice 3's re-place gesture, save is Slice 5's editor
// save). The verbs that write the FILE (not only the sidecar) — reject, reject-all, save — also
// fence on fileMtimeNs (requireFence with 'file-moved') and check the text (not-text, too-large)
// before any write; no other verb does.
const VERBS = new Set([
  'status', 'set-tracked', 'comment', 'reply', 'resolve', 'log-edit', 'log-send',
  'accept', 'accept-all', 'reject', 'reject-all', 'retarget', 'save',
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

// An error's text for the person: its message, tilde-collapsed.
function errText(e) {
  return tildeText(e && e.message ? e.message : String(e));
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

// The refusal for a comments log that exists but cannot be read, before any write: the log is the
// only state for what is unsent and for what was decided, so a verb that cannot read it neither
// answers from a guess nor writes past it.
function logUnreadable(ctx, paths, e) {
  return new Refusal('unreadable', `cannot read the comments log for ${ctx.shown} (${tilde(paths.logPath)}): ${errText(e)}; nothing was changed`);
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
// the file refuse (`not-text`) rather than write that decode back over the bytes. `bytes` is the
// size on disk, the "before" half of the edit entry a save logs. `cannot` is set by the verbs
// that WRITE the file (reject, reject-all, save; their clause, "cannot save" / "cannot write"):
// the same fstat that takes the mtime then refuses `too-large` past the text cap BEFORE the bytes
// are read — the kernel's _save_file discipline (refusing on the stat keeps the file out of
// memory). Read first and checked after, a save aimed at a 96 MB file under a .trackchanges/ tree
// loaded it whole into this process to refuse it, a file past V8's string limit crashed the host
// (ERR_STRING_TOO_LONG, the kernel's `host-error`) and one past Node's 2 GiB read limit answered
// `unreadable` — three answers for one fact the stat already held (the review, 2026-09-06). The
// viewer never loads a file past the cap (a 413), so nothing legitimate reaches the read.
function readFile(ctx, cannot) {
  const { fd, st } = openRegular(ctx);
  if (cannot && st.size > BigInt(TEXT_MAX_BYTES)) {
    try { fs.closeSync(fd); } catch { /* ignore */ }
    throw tooLargeOnDisk(ctx, Number(st.size), cannot);
  }
  let buf;
  try {
    buf = fs.readFileSync(fd);
  } catch (e) {
    throw new Refusal('unreadable', `cannot read ${ctx.shown}: ${tildeText(e && e.message ? e.message : String(e))}`);
  } finally {
    try { fs.closeSync(fd); } catch { /* ignore */ }
  }
  const strict = decodeTextOrNull(buf);
  return { text: strict != null ? strict : buf.toString('utf8'), isText: strict != null, fileMtimeNs: st.mtimeNs.toString(), bytes: buf.length };
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

export function isMediaPath(p) {
  const ext = path.extname(String(p == null ? '' : p)).slice(1).toLowerCase();
  return ext !== '' && MEDIA_EXTENSIONS.has(ext);
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
// natural size, kept to four decimals — the client sends four, and this makes sure), `page` (PDFs
// only, 1-based), and `src`. The hash is not the client's to send; stampTarget computes it.
// `embedded` says whether the comment carries an anchor: a figure in a markdown file names its
// `src` (the embed's destination as written) and a standalone image or PDF has none, and the two
// cannot mix — a src with no embed line to stand on, or an embed line with no figure to hash,
// would hash the wrong file.
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
// the viewer decodes it before loading the figure (decodeURI, so `p95%20latency.png` is the file
// with the space; a malformed escape is read as written — file-view.ts, rewriteFigureSrcs), so the
// host hashes the file the person saw; resolved against the commented file's directory as a path,
// then confirmed by realpath to be INSIDE the project root:
// never above it, and not through a symlink that leaves it. `rootDir` is the root the file has, or
// for a loose file the one its first comment is about to create, its own directory (decision 37).
// Returns the resolved path or throws with the reason; the caller makes that a refusal (comment,
// retarget) or a null hash (the hashes a reply carries). Whether it is a regular file is
// hashRegular's check, on the same descriptor it reads.
export function resolveSrc(ctx, rootDir, src) {
  if (/^[a-z][a-z0-9+.-]*:/i.test(src)) throw new Error(`${src} is a URL, not a file in the project`);
  let rel = src;
  try { rel = decodeURI(src); } catch { /* a malformed escape: the spelling as written, as the viewer reads it */ }
  const abs = path.resolve(path.dirname(ctx.abs), rel);
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

// The target `comment` and `retarget` write: the validated shape plus the hash of the bytes it
// is about — the figure `src` names, or the commented file itself for a standalone image or PDF.
// No size cap here: this is the one moment the bytes are known to be the ones the person drew on,
// and the viewer showed them, so they are within the kernel's cap already. Key order is the
// contract's: kind, region, page (pdf), hash, src (embedded).
function stampTarget(ctx, rootDir, target) {
  let abs = ctx.abs;
  if (target.src != null) {
    try {
      abs = resolveSrc(ctx, rootDir, target.src);
    } catch (e) {
      throw new Refusal('unreadable', `the figure ${target.src} in ${ctx.shown} cannot be read: ${tildeText(e && e.message ? e.message : String(e))}; nothing was changed`);
    }
  }
  let hash;
  try {
    hash = hashRegular(abs, null).hash;
  } catch (e) {
    const what = target.src != null ? `the figure ${target.src} in ${ctx.shown}` : ctx.shown;
    throw new Refusal('unreadable', `${what} cannot be read: ${tildeText(e && e.message ? e.message : String(e))}; nothing was changed`);
  }
  const out = { kind: target.kind, region: target.region };
  if (target.page != null) out.page = target.page;
  out.hash = hash;
  if (target.src != null) out.src = target.src;
  return out;
}

// The hash a reply carries for a media file: its bytes as they are now, for the panel to compare
// with each region comment's target.hash. Null past the cap, and null (with a note on stderr) when
// the file cannot be read at this moment — the verb already read or stat'ed it, so that is a race
// with a writer, and "unknown" is the honest answer where a refusal would deny a write that landed.
function fileHashFor(ctx) {
  try {
    return hashRegular(ctx.abs, fileHashCap()).hash;
  } catch (e) {
    process.stderr.write(`file-comments-host: ${ctx.shown} could not be hashed: ${tildeText(e && e.message ? e.message : String(e))}\n`);
    return null;
  }
}

// The hashes a reply carries for a text file: one per distinct `src` its region comments name, in
// order of first appearance, each the figure's bytes as they are now — or null when the src does
// not resolve to a regular file inside the root, or when hashing it would take the call past the
// shared budget. An empty object when the file has no sidecar or no region comments.
function embeddedHashesFor(ctx, rootDir, store) {
  if (!store || !rootDir) return {};
  const out = new Map();
  let budget = embeddedHashCap();
  for (const c of store.comments || []) {
    const src = c && c.target && c.target.src;
    if (typeof src !== 'string' || !src || out.has(src)) continue;
    let hash = null;
    try {
      const r = hashRegular(resolveSrc(ctx, rootDir, src), budget);
      if (r.hash != null) { hash = r.hash; budget -= r.size; }
    } catch (e) {
      process.stderr.write(`file-comments-host: the figure ${src} in ${ctx.shown} was not hashed: ${tildeText(e && e.message ? e.message : String(e))}\n`);
    }
    out.set(src, hash);
  }
  return Object.fromEntries(out);
}

// `too-large`: only verbs that write the file check it, before any write (the kernel's cap).
export function checkTooLarge(shown, text) {
  if (Buffer.byteLength(text, 'utf8') > TEXT_MAX_BYTES) {
    throw new Refusal('too-large', `${shown} exceeds the 2 MB text cap, so its contents cannot be written from the dashboard`);
  }
}

// The kernel's _human_bytes, for the refusals that name a size.
export function human(n) {
  for (const [unit, step] of [['GB', 1 << 30], ['MB', 1 << 20], ['KB', 1 << 10]]) {
    if (n >= step) return `${(n / step).toFixed(1)} ${unit}`;
  }
  return `${n} bytes`;
}

// The kernel's _is_text_path: the extension allowlist plus the extensionless names that are text
// by convention, on the basename lower-cased. The extension is Python's os.path.splitext's: the
// text after the last dot, unless every character before that dot is a dot (`.gitignore` has
// none). Name-based only; the bytes are checkIsText's.
export function isTextPath(p) {
  const base = path.basename(String(p == null ? '' : p)).toLowerCase();
  const dot = base.lastIndexOf('.');
  const ext = dot > 0 && /[^.]/.test(base.slice(0, dot)) ? base.slice(dot + 1) : '';
  return (ext !== '' && TEXT_EXT.has(ext)) || TEXT_NAMES.has(base);
}

// The kernel's _under_trackchanges: is the path inside a .trackchanges/ directory (a directory
// segment, not the basename)? The sidecar, the config and the log are files the viewer can open
// and edit; an edit to them is never logged, since the log would record itself.
export function underTrackchanges(abs) {
  return path.normalize(abs).split(path.sep).slice(0, -1).includes(TRACKCHANGES_DIR);
}

// Two refusals the kernel's _save_file makes that this script makes too, before any write. The name
// rule is `save`'s alone: save writes the client's content, and a name outside the viewer's text
// scope is one saveFile would not write that content under, so neither does this door. reject and
// reject-all do NOT check the name: they write back only the text the sidecar recorded for the ids
// the client chose, on every tracked file that is UTF-8 text — the scope the CLIs record changes in
// and the scope Slice 2 shipped (a session's change in a .tex or .hs file is a card the panel
// shows, and its Reject must land). The size rule is every file-writing verb's: a file past the text
// cap on disk is one the viewer never loaded (a 413), so no text a client sends about it is text the
// person saw, and reading it whole to refuse it is what the stat is for. The size is refused on the
// stat, before the bytes are read (readFile's `cannot`); checkDiskSize is the backstop over the
// bytes actually read, for a file that grew between the fstat and the read. `cannot` is the verb's
// clause: "cannot save", "cannot write".
function checkTextPath(ctx, cannot) {
  if (!isTextPath(ctx.abs)) {
    throw new Refusal('not-text', `${cannot} ${ctx.shown}: not a text file the viewer edits; nothing was changed`);
  }
}
function tooLargeOnDisk(ctx, bytes, cannot) {
  return new Refusal('too-large', `${cannot} ${ctx.shown}: the file on disk is ${human(bytes)}, past the ${human(TEXT_MAX_BYTES)} text cap the viewer loads; nothing was changed`);
}
function checkDiskSize(ctx, file, cannot) {
  if (file.bytes > TEXT_MAX_BYTES) throw tooLargeOnDisk(ctx, file.bytes, cannot);
}

// `not-text`: the verbs that write the file refuse a file whose bytes are not UTF-8 text, before
// any write. Writing back the lossy decode would replace every invalid sequence with U+FFFD and
// destroy the file; the sidecar-only verbs never write the file, so they take such a file as the
// CLIs do. `consequence` is the clause after "so": what the verb cannot do and why (reject's by
// default; save names its own).
function checkIsText(shown, file, consequence) {
  if (!file.isText) {
    const what = consequence || 'a change in it cannot be rejected from the dashboard: writing the file back would rewrite it from a lossy decode and destroy it';
    throw new Refusal('not-text', `${shown} is not UTF-8 text, so ${what}; nothing was changed`);
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
// into place. Returns the new mtime string. Reject and save write through it.
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
  }
  return { comment: c };
}

// ── the reply ───────────────────────────────────────────────────────

// A comments log that exists but cannot be read is a disk state, not a program error: before a
// write it refuses `unreadable` naming the log (nothing was changed — `status`, and every verb's
// pre-write estimate); after one — `opts.landed`, the landedState of a verb whose primary write has
// landed — it leaves `log` empty and is reported in `logWarning`, never failing the verb.
// `opts.estimate` builds
// the reply a verb WOULD send, for checkReplyFits to measure before the write: `opts.pending` are
// the log entries the verb is about to append, and the fields whose size is fixed but whose cost is
// not — the tracking verdict (a vault walk) and the hashes (the figures' bytes) — are stood in for.
function reply(ctx, state, extra, opts) {
  const o = opts || {};
  const { root, paths, store, text, fileMtimeNs } = state;
  let log = [];
  let logTruncated = false;
  let entries = [];
  if (paths) {
    let read;
    try {
      read = readLog(paths.logPath);
    } catch (e) {
      if (!o.landed) throw logUnreadable(ctx, paths, e);
      read = { entries: [], bad: 0 };
      landedProblem(o.landed, `the comments log for ${ctx.shown} could not be read back: ${errText(e)}`);
    }
    entries = o.pending && o.pending.length ? [...read.entries, ...o.pending] : read.entries;
    if (read.bad) process.stderr.write(`file-comments-host: ${read.bad} unreadable line(s) in ${tilde(paths.logPath)} skipped\n`);
    logTruncated = entries.length > LOG_TAIL;
    log = logTruncated ? entries.slice(entries.length - LOG_TAIL) : entries;
  }
  const out = {
    ok: true,
    verb: ctx.verb,
    root,
    storePath: paths ? paths.storePath : null,
    trackedBy: root && !o.estimate ? trackedByFor(root, ctx.abs) : null,
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
  // the panel holds next): a media file's own bytes, or the figures a text file's comments name.
  if (o.estimate) { if (isMediaPath(ctx.abs)) out.fileHash = null; else out.embeddedHashes = {}; }
  else if (isMediaPath(ctx.abs)) out.fileHash = fileHashFor(ctx);
  else out.embeddedHashes = embeddedHashesFor(ctx, root, store);
  if (ctx.args.baseline === true) out.baseline = engine.baselineOf(text, store ? store.suggestions : []);
  Object.assign(out, extra || {});
  if (o.landed && o.landed.problems.length) out.logWarning = `${o.landed.did}, but ${o.landed.problems.join('; and ')}`;
  return out;
}

// Re-read what was just written so the reply carries the sidecar as every later load sees it.
function reloadSaved(ctx, paths, text) {
  const store = loadOrRefuse(ctx, paths, text);
  if (!store) throw new Error(`the sidecar ${tilde(paths.storePath)} vanished after its write`);
  return store;
}

// ── after a write has landed ────────────────────────────────────────

// The state of a verb whose primary write has landed: `did` names it for the person ("saved",
// "the changes were rejected"), `problems` collects what went wrong after it. Nothing after the
// landed write may fail the verb: the kernel reads a non-zero exit as a verb that did nothing — it
// sends no trace to the session whose file just changed (never-lose-the-thread), and the client
// keeps a buffer it believes unsaved behind a fence the write has already moved, so its next try
// refuses store-moved or file-moved against its own write. So the log append, the sidecar's
// read-back and the log's read-back are reported instead, in `logged` and `logWarning`
// (plans/file-review.md, The comments log: a failed append is reported in the reply and never
// fails the save — the kernel's rule for log-edit after saveFile, kept here for the verbs that
// write in one process). Each problem also goes to stderr, for the kernel's tail.
function landedState(did) { return { did, problems: [] }; }
function landedProblem(landed, clause) {
  landed.problems.push(clause);
  process.stderr.write(`file-comments-host: ${landed.did}, but ${clause}\n`);
}

// Append a verb's log entries after its write landed: true when every entry landed; else false,
// with the entries that did not named in the warning (an append that fails midway leaves the
// earlier ones on disk, and the log is never rewritten).
function appendLanded(ctx, paths, entries, landed) {
  let n = 0;
  try {
    fs.mkdirSync(path.dirname(paths.logPath), { recursive: true });
    for (const e of entries) { appendLog(paths.logPath, e); n++; }
    return true;
  } catch (e) {
    const missing = entries.slice(n).map((x) => x.kind);
    const which = n
      ? `the ${missing.join(' and ')} ${missing.length > 1 ? 'entries were' : 'entry was'} not written to`
      : 'not written to';
    landedProblem(landed, `${which} the comments log for ${ctx.shown}: ${errText(e)}`);
    return false;
  }
}

// The sidecar after a landed write, re-read as every later load sees it (afterDecision: pruned
// when emptied); when it cannot be — a writer that replaced it in the same instant, a disk that
// stopped answering — the records this process wrote stand in and the reply says so.
function settleLanded(ctx, paths, store, text, landed) {
  try {
    return afterDecision(ctx, paths, store, text);
  } catch (e) {
    landedProblem(landed, `the comments for ${ctx.shown} could not be read back after the write: ${errText(e).replace(/; nothing was changed$/, '')} — reload`);
    return store;
  }
}

// Measure the reply a verb would send, before it writes: the sidecar it is about to save (carried
// as `store` and again as `hunks`), the log with the entries it is about to append, the baseline
// when asked — and refuse `too-large` when the kernel would not carry it. Past REPLY_MAX_BYTES the
// kernel kills this process and discards its stdout AFTER the write landed, then does the same to
// every later `status` on the file, so a record or a note a client sends at that size would lock
// the file's comments until the sidecar was fixed by hand. The records and notes the editor and
// the panel produce describe text the viewer showed, a file under the 2 MB cap, so nothing they
// send comes near it. `what` names the addition for the person ("this comment", "the change
// records and the decisions taken in the editor").
function checkReplyFits(ctx, state, extra, pending, what) {
  const est = reply(ctx, state, extra, { estimate: true, pending });
  const bytes = Buffer.byteLength(JSON.stringify(est), 'utf8') + 1;
  if (bytes > REPLY_MAX_BYTES - REPLY_SLACK) {
    throw new Refusal('too-large', `cannot write the comments for ${ctx.shown}: with ${what} they come to ${human(bytes)} in one reply, past the ${human(REPLY_MAX_BYTES)} the dashboard can carry back; nothing was changed`);
  }
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
  // The root the write will have: for a loose file, the landmark's — its own directory, created
  // below, after the last check that can refuse (the reply's size).
  const rootToBe = root || path.dirname(ctx.abs);
  const pathsToBe = paths || pathsFor(rootToBe, ctx.abs);
  if (!store) store = seedStore(pathsToBe.rel);
  apply(store);
  checkReplyFits(ctx, { root: rootToBe, paths: pathsToBe, store, ...file }, null, [], `this ${ctx.verb}`);
  if (!root) {
    root = createLandmark(ctx);
    paths = pathsFor(root, ctx.abs);
  }
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
// anchor is placed, and only then is the figure hashed — the region's own refusals (`unreadable`
// for a src outside the root or unreadable) come after the passage's, and all of them before the
// landmark and the write.
function doComment(ctx) {
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
    if (target) built.comment.target = stampTarget(ctx, root || path.dirname(ctx.abs), target);
    return (s) => { s.comments.push(built.comment); };
  });
}

// retarget {commentId, target}: the re-place gesture on a region comment — a new rectangle (and
// for a PDF a page) over the same figure, the hash recomputed from the bytes as they are now, so a
// comment the figure's regeneration made stale is current again. The comment must exist (else
// `no-comment`) and be a region comment (a target on a comment that has none is a caller bug); an
// embedded figure's new target names its src as the old one did and a standalone one's has none —
// the anchor decides, as it does for comment. Fenced on the sidecar like every sidecar write; the
// anchor, id, body and replies stay as they were; nothing is appended to the comments log, since a
// re-placed rectangle is not a decision.
function doRetarget(ctx) {
  const id = requireCommentId(ctx.args);
  if (ctx.args.target == null) throw new BadRequest('retarget needs target: {kind, region, page?, src?}');
  return withSidecar(ctx, false, (store, text, root) => {
    const c = findComment(store, id);
    if (!c) throw new Refusal('no-comment', `comment ${String(id)} is not among the comments for ${ctx.shown} — reload and retry`);
    if (!c.target || typeof c.target !== 'object') throw new BadRequest(`comment ${String(id)} has no region to re-place`);
    const target = stampTarget(ctx, root || path.dirname(ctx.abs), validateTarget(ctx.args.target, c.anchor != null));
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
// is null when there is no sidecar, which for a decision means nothing is pending. `writesFile`
// is false for the sidecar-only verbs and the verb's clause ("cannot write", "cannot save") for
// the ones that write the file: those fence on the file too, and their read refuses `too-large`
// on the stat, before the bytes (readFile).
function loadForDecision(ctx, writesFile) {
  for (const k of writesFile ? ['storeMtimeNs', 'fileMtimeNs'] : ['storeMtimeNs']) {
    if (typeof ctx.fence[k] !== 'string') throw new BadRequest(`fence.${k} is required for ${ctx.verb}`);
  }
  const file = readFile(ctx, writesFile);
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
  const landed = landedState('the changes were accepted');
  const logged = appendLanded(ctx, paths, [logEntry('accept', { changes: changesOf(decided) })], landed);
  const after = settleLanded(ctx, paths, store, file.text, landed);
  return reply(ctx, { root, paths, store: after, ...file }, { accepted: ids, logged }, { landed });
}

// Put the sidecar back as it was before a reject or a save whose file write failed: the prior
// bytes, or nothing when there were none (both verbs find a sidecar whenever they write one, so
// that branch is a guard). Replaced by temp-and-rename like every other sidecar write, with a
// name no .json scan matches.
function restoreSidecar(storePath, prior) {
  if (prior == null) { fs.unlinkSync(storePath); return; }
  const tmp = `${storePath}.romp-fc-restore-${process.pid}.tmp`;
  fs.writeFileSync(tmp, prior);
  fs.renameSync(tmp, storePath);
}

// reject / reject-all: the engine's reverse edits give the new text, applied by applyEdits and
// checked against the file before anything is written (not-text for bytes that are not UTF-8,
// too-large on the stat and on the restored text). No name check: the text written is the
// sidecar's own record of what the session replaced, not a client's, so the verb runs on every
// tracked file that is UTF-8 text, whatever its name (checkTextPath's comment). Then the order
// track-edit uses: the sidecar first, saved against the NEW text so its fingerprint describes the
// file about to exist, then the file through writeFileAtomic; if the file write fails the prior
// sidecar bytes go back and the verb refuses `unreadable` with the OS text. The survivors come
// back from the engine remapped into post-reject coordinates; reloading the saved sidecar against
// the new text re-verifies them the way every later load will.
function doReject(ctx, all) {
  const { file, root, paths, store } = loadForDecision(ctx, 'cannot write');
  const decided = decidedChanges(ctx, store, all);
  const ids = decided.map((h) => h.id);
  checkDiskSize(ctx, file, 'cannot write');
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
  const landed = landedState('the changes were rejected');
  const logged = appendLanded(ctx, paths, [logEntry('reject', { changes: changesOf(decided) })], landed);
  const after = settleLanded(ctx, paths, store, newText, landed);
  return reply(ctx, { root, paths, store: after, text: newText, fileMtimeNs }, { rejected: ids, logged }, { landed });
}

// ── save (Slice 5) ──────────────────────────────────────────────────

// `content` must be text the file can hold as UTF-8 and the tracking tools will read as text: a
// lone surrogate (a JSON string can carry one) encodes as U+FFFD, so the file would not hold what
// the person typed — the kernel's saveFile refuses the same — and a NUL character makes the file
// one decodeTextOrNull (this script, track-edit) reads as binary from then on.
const LONE_SURROGATE_RE = /[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/;
function checkContentText(shown, content) {
  if (content.includes('\0')) {
    throw new Refusal('not-text', `cannot save ${shown}: the text contains a NUL character, which would make the file one the tracking tools refuse as not text; nothing was changed`);
  }
  if (LONE_SURROGATE_RE.test(content)) {
    throw new Refusal('not-text', `cannot save ${shown}: the text contains a character UTF-8 cannot encode (a lone surrogate); nothing was changed`);
  }
}

// The decisions taken in the editor, `[{id, oldText, newText}]`, in the shape the accept and reject
// log entries keep (changesOf). Malformed is a caller bug; so is an id decided twice, or decided
// AND still among the records being saved (a decision drops its record from the editor's field,
// and undo takes the decision back with it, so the two never name one id together). `taken`
// collects the decided ids across both lists, for the membership check against the sidecar and
// the log once they are loaded (decisionRoots, in doSave) and for the comment resolve pass. The
// shape is all this checks: whether an id names a change that was pending needs the disk.
function requireDecisions(list, name, submitted, taken) {
  if (!Array.isArray(list)) throw new BadRequest(`save needs ${name}: an array of {id, oldText, newText}`);
  const out = [];
  for (const d of list) {
    if (!d || typeof d !== 'object' || Array.isArray(d)) throw new BadRequest(`every ${name} entry must be {id, oldText, newText}`);
    if ((typeof d.id !== 'string' && typeof d.id !== 'number') || d.id === '') throw new BadRequest(`every ${name} entry needs a non-empty id`);
    if (typeof d.oldText !== 'string' || typeof d.newText !== 'string') throw new BadRequest(`${name} entry ${String(d.id)} needs oldText and newText as strings`);
    const key = String(d.id);
    if (taken.has(key)) throw new BadRequest(`change ${key} is decided twice`);
    if (submitted.has(key)) throw new BadRequest(`change ${key} is ${name} and still among the suggestions being saved`);
    taken.add(key);
    out.push({ id: d.id, oldText: d.oldText, newText: d.newText });
  }
  return out;
}

// The ids a save's decisions and records may be rooted in: every change the sidecar holds, and every
// change the comments log records as accepted or rejected (the log outlives the sidecar's memory of
// a decided change — The comments log — and an editor kept alive past a landed save may decide one
// of those again after an undo, or hold its record again: undo of a landed accept puts the record
// back in the field, and the next save carries it as pending once more). The log is read the way
// reply() reads it; unreadable refuses before any write, as it would there.
function sidecarRoots(store) {
  const roots = new Set();
  for (const s of (store && store.suggestions) || []) if (s && s.id != null && s.id !== '') roots.add(String(s.id));
  return roots;
}
function decisionRoots(ctx, store, paths) {
  const roots = sidecarRoots(store);
  if (paths) {
    let read;
    try { read = readLog(paths.logPath); } catch (e) { throw logUnreadable(ctx, paths, e); }
    for (const e of read.entries) {
      if (!e || (e.kind !== 'accept' && e.kind !== 'reject') || !Array.isArray(e.changes)) continue;
      for (const c of e.changes) if (c && c.id != null && c.id !== '') roots.add(String(c.id));
    }
  }
  return roots;
}

// A decided id is rooted when it IS a root or descends from one by the engine's split scheme —
// `<id>~n`, nested for a fragment split again (`<id>~1~1`), and the editor's re-mint of a decided
// fragment's suffix keeps the parent (`<id>~2`) — the prefix rule the engine itself uses to tell a
// change's fragments from strangers (supersededOps).
function rootedIn(roots, id) {
  if (roots.has(id)) return true;
  for (const r of roots) if (id.startsWith(r + '~')) return true;
  return false;
}

// A save's change record whose id is rooted nowhere — not in the sidecar, not in the log, not a
// fragment of either: a record the editor cannot have been given, since its field is seeded from
// the sidecar and every id it mints descends from one (the header's rule on records). `desync`,
// the code for records that disagree with what the save claims they came from (fitRecords names a
// record that does not fit the text the same way), so the viewer shows the reason and keeps the
// buffer; the ids are named as noChange names ghosts, so the person and the log-derived state
// agree on what was refused.
function recordsNeverPending(ctx, ids) {
  const list = ids.map(String);
  const one = list.length === 1;
  const what = one ? `change ${list[0]} was` : `changes ${list.join(', ')} were`;
  const them = one ? 'it' : 'them';
  return new Refusal('desync', `${what} never pending in ${ctx.shown}: neither the comments file holds ${them} nor the comments log remembers ${them}, so the records being saved are not that file's; nothing was changed — reload and retry`);
}

// A record's author and session id as the sidecar holds them (fitRecords's normalization: a missing
// or empty author is 'unknown', a missing or empty authorId is none), so a submitted record and the
// stored change it claims to be compare on the same terms.
function authorOf(s) {
  return {
    author: typeof s.author === 'string' && s.author ? s.author : 'unknown',
    authorId: typeof s.authorId === 'string' && s.authorId ? s.authorId : null,
  };
}

// The sidecar's change a record descends from — the record's own id, else the nearest ancestor by
// the split scheme (`<id>~n`, the rule rootedIn applies) — or null when the sidecar holds none: a
// record the log alone roots, or a stranger recordsNeverPending refuses first.
function sidecarRootOf(store, id) {
  let best = null;
  for (const s of (store && store.suggestions) || []) {
    if (!s || s.id == null || s.id === '') continue;
    const r = String(s.id);
    if (id === r) return s;
    if (id.startsWith(r + '~') && (!best || r.length > String(best.id).length)) best = s;
  }
  return best;
}

// A save's change record that names another author or session id than the sidecar's change it is
// rooted in: not a record the editor derived from the seeded ones (the header's rule on records),
// refused `desync` as a record that does not fit the text is, so the viewer shows the reason and
// keeps the buffer, and a reload seeds the field from the sidecar again. Named as noChange names
// ghosts.
function recordsMisattributed(ctx, ids) {
  const list = ids.map(String);
  const one = list.length === 1;
  const what = one ? `change ${list[0]} is not the change ${ctx.shown} holds under that id (its author or session differs)`
    : `changes ${list.join(', ')} are not the changes ${ctx.shown} holds under those ids (their author or session differs)`;
  return new Refusal('desync', `${what}, so the records being saved are not that file's; nothing was changed — reload and retry`);
}

// Every change record the editor holds, checked against `content` the way the engine's load checks
// a sidecar's records against the file (rebaseSuggestions: the record's newText sits at its offset,
// and two placed spans never overlap) — but refusing where the engine would detach or relocate: the
// editor remapped these records through the person's own keystrokes, so one that does not fit is a
// desync between the editor's text and its field, and saving it would write a sidecar that
// describes another file. The first record that does not fit is named (`misfit`, in the caller's
// order; an overlap names the later span in document order); a record that is not even a record,
// or an id used twice, is a caller bug. The records written are rebuilt from the known fields in
// recordAgentEdit's shape and key order: `kind` from the texts (the engine's own rule, so a stale
// kind never disagrees with them), the anchor over `content` at the record's span, as
// recordAgentEdit builds it — byte-identical for a record the edit did not move, and current for
// one it split or shifted, which otherwise keeps an anchor describing text no longer around it —
// and unknown fields dropped. Returned in coalesceOps's order: by offset, the narrower span first.
export function fitRecords(content, suggestions) {
  const len = content.length;
  const seen = new Set();
  const records = [];
  for (const s of suggestions) {
    if (!s || typeof s !== 'object' || Array.isArray(s)) throw new BadRequest('every suggestion must be a change record {id, author, ts, from, newText, oldText, ...}');
    if ((typeof s.id !== 'string' && typeof s.id !== 'number') || s.id === '') throw new BadRequest('every suggestion needs a non-empty id');
    const key = String(s.id);
    if (seen.has(key)) throw new BadRequest(`suggestion id ${key} appears twice`);
    seen.add(key);
    const newText = s.newText == null ? '' : s.newText;
    const oldText = s.oldText == null ? '' : s.oldText;
    if (typeof newText !== 'string' || typeof oldText !== 'string') return { records: null, misfit: { id: key, why: 'its texts are not strings' } };
    if (!newText && !oldText) return { records: null, misfit: { id: key, why: 'it neither adds nor removes text' } };
    if (!Number.isInteger(s.from) || s.from < 0 || s.from > len) {
      return { records: null, misfit: { id: key, why: `its offset ${JSON.stringify(s.from)} is outside the text (${len} characters)` } };
    }
    const to = s.from + newText.length;
    if (newText && content.slice(s.from, to) !== newText) {
      return { records: null, misfit: { id: key, why: `the text at ${s.from}..${to} is not the change's text` } };
    }
    const who = authorOf(s);
    const rec = { id: s.id, author: who.author };
    if (who.authorId) rec.authorId = who.authorId;
    rec.ts = typeof s.ts === 'number' && Number.isFinite(s.ts) ? s.ts : 0;
    rec.kind = engine.kindOf(oldText, newText);
    rec.from = s.from;
    rec.newText = newText;
    rec.oldText = oldText;
    rec.anchor = engine.makeAnchor(content, s.from, to);
    records.push(rec);
  }
  records.sort((x, y) => x.from - y.from || x.newText.length - y.newText.length);
  // A zero-width deletion point never overlaps (the engine's rule: it may sit inside another
  // change's span); two spans do when the later starts before the earlier ends. Without an
  // overlap so far the spans end in increasing order, so the previous span's end is the furthest.
  let prev = null;
  for (const r of records) {
    if (!r.newText) continue;
    if (prev && r.from < prev.from + prev.newText.length) {
      return { records: null, misfit: { id: String(r.id), why: `it overlaps change ${String(prev.id)}` } };
    }
    prev = r;
  }
  return { records, misfit: null };
}

// The diff a save logs, in the shape the kernel's saveFile path logs for a direct edit
// (_edit_log_diff, Python's difflib): `--- a/<name>` and `+++ b/<name>`, then zero-context hunks
// `@@ -<range> +<range> @@` with the removed lines and then the added ones, every line
// newline-terminated, capped at EDIT_DIFF_MAX_LINES lines or EDIT_DIFF_MAX_BYTES bytes with
// `truncated: true` when cut — so the panel's Log reads a save's entry and a direct edit's the
// same way. Lines are split on '\n' (a CR stays with its line). The common head and tail are
// trimmed first and the engine's line LCS (lcsOps, the one diff this script has) aligns the rest;
// past DIFF_CELLS cells the middle is written as one replacement hunk, which the cap cuts anyway
// — an exact alignment of a wholesale paste is not worth the memory. An identical text yields ''
// (difflib writes no header when there is no hunk).
export const EDIT_DIFF_MAX_LINES = 200;
export const EDIT_DIFF_MAX_BYTES = 16 * 1024;
const DIFF_CELLS = 4_000_000;

// difflib's _format_range_unified: 1-based; a single line has no count; an empty range names the
// line before it.
function rangeUnified(start, length) {
  let beginning = start + 1;
  if (length === 1) return String(beginning);
  if (!length) beginning -= 1;
  return `${beginning},${length}`;
}

export function editDiff(oldText, newText, name) {
  const a = engine.splitLinesKeep(oldText);
  const b = engine.splitLinesKeep(newText);
  let head = 0;
  while (head < a.length && head < b.length && a[head] === b[head]) head++;
  let tail = 0;
  while (tail < a.length - head && tail < b.length - head && a[a.length - 1 - tail] === b[b.length - 1 - tail]) tail++;
  const am = a.slice(head, a.length - tail);
  const bm = b.slice(head, b.length - tail);
  const hunks = [];
  if (am.length || bm.length) {
    if (am.length * bm.length > DIFF_CELLS) {
      hunks.push({ aStart: head, del: am, bStart: head, ins: bm });
    } else {
      let ai = head;
      let bj = head;
      let cur = null;
      for (const op of engine.lcsOps(am, bm, (x, y) => x === y)) {
        if (op.type === 'eq') { cur = null; ai++; bj++; continue; }
        if (!cur) { cur = { aStart: ai, del: [], bStart: bj, ins: [] }; hunks.push(cur); }
        if (op.type === 'del') { cur.del.push(am[op.ai]); ai++; } else { cur.ins.push(bm[op.bj]); bj++; }
      }
    }
  }
  if (!hunks.length) return { diff: '', truncated: false };
  const lines = [`--- a/${name}\n`, `+++ b/${name}\n`];
  for (const h of hunks) {
    lines.push(`@@ -${rangeUnified(h.aStart, h.del.length)} +${rangeUnified(h.bStart, h.ins.length)} @@\n`);
    for (const l of h.del) lines.push(`-${l}`);
    for (const l of h.ins) lines.push(`+${l}`);
  }
  const out = [];
  let size = 0;
  let truncated = false;
  for (let ln of lines) {
    if (!ln.endsWith('\n')) ln += '\n';
    const bytes = Buffer.byteLength(ln, 'utf8');
    if (out.length >= EDIT_DIFF_MAX_LINES || size + bytes > EDIT_DIFF_MAX_BYTES) { truncated = true; break; }
    out.push(ln);
    size += bytes;
  }
  return { diff: out.join(''), truncated };
}

// save {content, suggestions, accepted, rejected}: the editor's Save over a file with pending
// changes (Slice 5). `content` is the whole new text; `suggestions` the change records as the
// editor's field holds them after the person's typing remapped them (the sidecar's v3 record
// shape); `accepted` and `rejected` the decisions taken in the editor, each
// `{id, oldText, newText}`, whose records the field has already dropped (and, for a reject, whose
// old text the buffer already holds). Fenced on the sidecar AND the file: "" for storeMtimeNs means
// no sidecar exists, so the editor had nothing to remap and nothing to decide (a non-empty list is
// then a caller bug), and no sidecar is created — the file (and, for a file the log has business
// with, the log) is written. Otherwise, in order and with nothing written until every check has
// passed: the file's name must be one the viewer edits and the file on disk under the cap (what
// saveFile refuses, `not-text` and `too-large`), every decided id must be rooted in the sidecar or
// the log (`no-change`), the file must be UTF-8 text on disk and `content` text the file can hold
// (`not-text`), under the cap (`too-large`), every record must fit `content` (`desync`, naming the
// first that does not), be rooted the way a decision must (`desync` by id, recordsNeverPending: a
// record the sidecar never held would be written into it as a change the session made) and name the
// author and session id of its root in the sidecar (`desync` by id, recordsMisattributed), and the
// reply this save would send — the records as `store` and `hunks`, the log entries it appends —
// must be one the kernel carries (`too-large`, checkReplyFits). Then the order track-edit and reject
// use: the sidecar first (the records, every comment bound by `suggestionId` to a decided change
// marked resolved and KEPT, the detached ops as they were, the fingerprint over `content`), the file
// through writeFileAtomic, the prior sidecar bytes put back if the file write fails. From here the
// write has landed and nothing fails the
// verb (appendLanded, settleLanded): the log gets one `edit` entry in the kernel's direct-edit
// shape (built before the writes from the old and new text, the mtime after filled in once known),
// then an `accept` and a `reject` entry for each non-empty list — for a file that already has a
// sidecar, a comments log, or a tracked flag, the rule log-edit follows, and never for a path
// inside .trackchanges/ — and pruneIfClean runs when nothing is pending and no comment or detached
// op remains (the reply then carries storeMtimeNs null and store null). The reply is the standard
// status with the new fileMtimeNs, `logged`, and `logWarning` when an append or a read-back failed.
// A save whose content equals the file and whose records equal the sidecar is still a write: the
// person pressed Save, so the file is replaced (a new inode, a new mtime), the sidecar is rewritten,
// and the log gets an edit entry with an empty diff — never a short-circuit, since the kernel sends
// the same trace saveFile sends and the person expects a saved file.
// With no root above the file the file is written and nothing is created — no landmark, no log —
// and the reply says `logged: false`; so does a save of a file under a root that has neither a
// sidecar, a log, nor a tracked flag (the request a browser sends when its status predates a peer's
// toggle-off; the host does not take its word for the route).
function doSave(ctx) {
  const a = ctx.args;
  if (typeof a.content !== 'string') throw new BadRequest('save needs content: the whole new text as a string');
  if (!Array.isArray(a.suggestions)) throw new BadRequest('save needs suggestions: the change records as the editor holds them (an array)');
  const submitted = new Set();
  for (const s of a.suggestions) if (s && typeof s === 'object' && s.id != null) submitted.add(String(s.id));
  const taken = new Set();
  const accepted = requireDecisions(a.accepted, 'accepted', submitted, taken);
  const rejected = requireDecisions(a.rejected, 'rejected', submitted, taken);
  checkTextPath(ctx, 'cannot save');
  // Fenced on the sidecar the records came from and on the file the editor loaded — the two things
  // this verb writes. Not on config.json: save only READS it, to decide below whether the edit is
  // logged, and reads the disk as it is at the save, so a config that moved since Edit changes
  // nothing written on a client's word; set-tracked, which writes it, is the verb that fences on
  // it (plans/file-review.md, the wire section). A `configMtimeNs` a client sends is not read.
  const { file, root, paths, store } = loadForDecision(ctx, 'cannot save');
  if (!store && a.suggestions.length) throw new BadRequest('save with no sidecar takes no suggestions: there was nothing to remap');
  // The ids this save may name, read once for the decisions and the records alike (decisionRoots
  // reads the log; unreadable refuses before any write).
  let roots = null;
  if (taken.size) {
    // Every decided id must name a change that WAS pending: one the sidecar holds, one the comments
    // log already records as decided (an editor kept alive past a landed save re-decides an id that
    // save carried — undo, then the other gesture — and the log then reads accept, reject: what
    // happened), or a fragment of either (`<id>~n`, the engine's split scheme: the person typed inside
    // the change and decided one half). Anything else is a decision nobody took: logged, it would
    // stand in the append-only log as fact and be counted to the session (the kernel tells it how many
    // changes the save rejected, from these decisions), so it refuses `no-change` by id, as accept and
    // reject do (decidedChanges), and nothing is written.
    roots = decisionRoots(ctx, store, paths);
    if (!store && !roots.size) throw new BadRequest('save with no sidecar takes no accepted or rejected changes: nothing was pending');
    const ghosts = [...taken].filter((id) => !rootedIn(roots, id));
    if (ghosts.length) throw noChange(ctx, ghosts);
  }
  checkDiskSize(ctx, file, 'cannot save');
  checkIsText(ctx.shown, file, 'it cannot be saved from the dashboard: the text the editor holds is a lossy decode of its bytes, and writing that back would destroy them');
  checkContentText(ctx.shown, a.content);
  checkTooLarge(ctx.shown, a.content);
  const fit = fitRecords(a.content, a.suggestions);
  if (fit.misfit) {
    throw new Refusal('desync', `change ${fit.misfit.id} does not fit the text being saved to ${ctx.shown}: ${fit.misfit.why}; nothing was changed — reload and retry`);
  }
  if (fit.records.length) {
    // Every record must be rooted the way a decision must: the sidecar holds it, the log remembers it
    // decided (undo of a landed accept puts its record back in the field, and this save carries it as
    // pending again), or it is a fragment of either. fitRecords checked each against `content` only,
    // and rebuilds the record from the id, author, authorId, ts and oldText the client sent: a record
    // rooted nowhere would be written into the sidecar as a change by the session it names, with an
    // old text the session never replaced — the state the decisions check above refuses to LOG, reached
    // through the sidecar instead, since the next save or the panel's Reject would find it pending.
    // After fitRecords, so a malformed record is still the caller bug it crashes as and a misfit is
    // still named first; before the reply is measured and anything written. The sidecar's own ids
    // root the records of every ordinary save (the seeded records and the engine's splits of them),
    // so the log is read only for an id the sidecar does not root — the undo of a landed accept, or a
    // stranger — and a save that names none reads the log exactly as it did (the estimate, then the
    // reply). Named in the caller's order, as noChange names ghosts.
    let strangers = [...submitted].filter((id) => !rootedIn(sidecarRoots(store), id));
    if (strangers.length) {
      if (!roots) roots = decisionRoots(ctx, store, paths);
      strangers = strangers.filter((id) => !rootedIn(roots, id));
      if (strangers.length) throw recordsNeverPending(ctx, strangers);
    }
    // Every record the sidecar roots must name its root's author and session id: the editor's remap
    // copies both onto each fragment it splits off (mapOpsThroughChange's `...s`) and keeps the earlier
    // record's on a merge (coalesceOps), so the pair holds for every record a real editor derives from
    // the seeded ones, and a record that differs is not the editor's — written, it would put the
    // session's change under another author or session id in the sidecar, which the panel's change
    // cards then show and every later verb reads as who changed what (the review, 2026-09-06).
    // Compared against the loaded store, the one the editor was seeded from (fenced on storeMtimeNs
    // and fileMtimeNs, so the load-time rebase produced the same records). A record the log alone
    // roots has no author on record to compare, and the texts and ts are the client's (the header's
    // rule on records). Named in the caller's order.
    const misnamed = [];
    for (const s of a.suggestions) {
      const rootRec = sidecarRootOf(store, String(s.id));
      if (!rootRec) continue;
      const got = authorOf(s);
      const want = authorOf(rootRec);
      if (got.author !== want.author || got.authorId !== want.authorId) misnamed.push(String(s.id));
    }
    if (misnamed.length) throw recordsMisattributed(ctx, misnamed);
  }
  // Whether the log has business with this file, decided before the writes from the disk as it is:
  // a sidecar, a log, or the tracked flag (read from a config checkConfig passed in loadForDecision),
  // and never a path inside .trackchanges/. The entries are built here too (editDiff is pure), so
  // nothing after the writes has anything left to compute but the append itself.
  const logs = !!paths && !underTrackchanges(ctx.abs)
    && (!!store || exists(paths.logPath) || isTrackedFile(root, ctx.abs));
  const entries = [];
  if (logs) {
    const { diff, truncated } = editDiff(file.text, a.content, path.basename(ctx.abs));
    entries.push(logEntry('edit', {
      mtimeBeforeNs: file.fileMtimeNs,
      mtimeAfterNs: file.fileMtimeNs, // a stand-in of the same width; the write's own mtime replaces it below
      bytesBefore: file.bytes,
      bytesAfter: Buffer.byteLength(a.content, 'utf8'),
      diff,
      truncated,
    }));
    if (accepted.length) entries.push(logEntry('accept', { changes: accepted }));
    if (rejected.length) entries.push(logEntry('reject', { changes: rejected }));
  }
  let prior = null;
  if (store) {
    try { prior = fs.readFileSync(paths.storePath); } catch (e) { if (!e || e.code !== 'ENOENT') throw e; }
    store.suggestions = fit.records;
    if (taken.size) {
      for (const c of store.comments) {
        if (c && c.suggestionId != null && taken.has(String(c.suggestionId))) c.resolved = true;
      }
    }
  }
  checkReplyFits(ctx, { root, paths, store, text: a.content, fileMtimeNs: file.fileMtimeNs }, { logged: logs }, entries,
    'the change records and the decisions taken in the editor');
  if (store) saveStore(root, paths.storePath, store, a.content);
  let fileMtimeNs;
  try {
    fileMtimeNs = writeFileAtomic(ctx.abs, a.content);
  } catch (e) {
    const why = tildeText(e && e.message ? e.message : String(e));
    let restored = 'nothing was changed';
    if (store) {
      restored = 'the comments file was put back as it was and nothing was changed';
      try { restoreSidecar(paths.storePath, prior); } catch (e2) {
        restored = `the comments file could not be put back either (${tildeText(e2 && e2.message ? e2.message : String(e2))}) — reload before doing anything else`;
      }
    }
    throw new Refusal('unreadable', `cannot write ${ctx.shown}: ${why}; ${restored}`);
  }
  const landed = landedState('saved');
  let logged = false;
  if (logs) {
    entries[0].mtimeAfterNs = fileMtimeNs;
    logged = appendLanded(ctx, paths, entries, landed);
  }
  const after = store ? settleLanded(ctx, paths, store, a.content, landed) : null;
  return reply(ctx, { root, paths, store: after, text: a.content, fileMtimeNs }, { logged }, { landed });
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
  const landed = landedState('the tracking setting was written');
  const logged = appendLanded(ctx, paths, [logEntry('set-tracked', { on, scope: kind, entry })], landed);
  return reply(ctx, { root, paths, ...file }, { logged }, { landed });
}

const EDIT_SUMMARY_KEYS = ['mtimeBeforeNs', 'mtimeAfterNs', 'bytesBefore', 'bytesAfter', 'diff', 'truncated'];

// A direct edit from the viewer (decision 33), logged by the kernel's saveFile path after the
// save: only for a file that already has a sidecar, a comments log, or a tracked flag; never
// creates a sidecar, a log, or a landmark; never for a path inside .trackchanges/ (the kernel does
// not call it for one — _under_trackchanges — and this script keeps the rule itself, as `save`
// does: the log would record itself). The append comes first so the record never depends on
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
      const own = !underTrackchanges(ctx.abs);
      if (own && (exists(paths.storePath) || exists(paths.logPath) || (cfg === 'ok' && isTrackedFile(root, ctx.abs)))) {
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
  save: doSave,
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
