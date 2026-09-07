// On-disk store for the OP-LOG track-changes model (Node side: agent CLIs +
// hooks). The note file itself stays clean — it is the CURRENT text, with every
// pending suggestion applied. One sidecar JSON per tracked note:
//
//   <vault>/.trackchanges/<encodeURIComponent(relpath)>.json
//   {
//     "v": 3,
//     "path": "Whitepapers/foo.md",              // vault-relative, for humans
//     "suggestions": [ { id, author, authorId?, ts, kind, from, newText, oldText, anchor } ],
//     "comments":    [ { id, author, ts, anchor?, change?, body, replies, resolved } ],
//     "id": "<uuid>", "fingerprint": { hash, size }
//   }
//
// `current` is NOT stored — it is always the live note file. Suggestions are
// expressed in current-text coordinates and carry a text-quote anchor so a note
// moved/edited outside the editor can be re-matched (by content) and its ops
// re-located. The store is committed to git as-is (backup); nothing else lives in
// .trackchanges/, so there are no ignore rules.

import fs from 'node:fs';
import path from 'node:path';
import { createHash, randomUUID } from 'node:crypto';

import engine from './engine.js';

export const STORE_VERSION = 3;

const STORE_DIR = '.trackchanges';

function hashText(s) {
  return createHash('sha256').update(String(s == null ? '' : s), 'utf8').digest('hex');
}

// Content fingerprint over the CURRENT note text (the sidecar's ops are anchored
// to it), so an unedited move is an exact match and orphan-heal can re-associate.
export function fingerprintOf(currentText) {
  const t = currentText || '';
  return { hash: hashText(t), size: t.length };
}

// ── root + path helpers (unchanged cross-tool contract) ─────────────
const ROOT_MARKERS = ['.obsidian', '.git', '.trackchanges'];
export function findVaultRoot(file) {
  let dir = path.dirname(path.resolve(file));
  for (let i = 0; i < 40; i++) {
    for (const m of ROOT_MARKERS) {
      try { if (fs.existsSync(path.join(dir, m))) return dir; } catch { /* ignore */ }
    }
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return null;
}

export function storePathFor(vaultRoot, file) {
  const rel = path.relative(vaultRoot, path.resolve(file));
  return path.join(vaultRoot, STORE_DIR, encodeURIComponent(rel) + '.json');
}

export function relPathFor(vaultRoot, file) {
  return path.relative(vaultRoot, path.resolve(file));
}

function ensureTrackDir(vaultRoot) {
  fs.mkdirSync(path.join(vaultRoot, STORE_DIR), { recursive: true });
}

// ── tracked-path scope (.trackchanges/config.json, v2) — unchanged ──
const CONFIG_FILE = 'config.json';
const CONFIG_VERSION = 2;

export function configPathFor(vaultRoot) {
  return path.join(vaultRoot, STORE_DIR, CONFIG_FILE);
}
export function readConfig(vaultRoot) {
  try {
    const obj = JSON.parse(fs.readFileSync(configPathFor(vaultRoot), 'utf8'));
    return obj && typeof obj === 'object' ? obj : null;
  } catch { return null; }
}
export function trackedPaths(vaultRoot) {
  const cfg = readConfig(vaultRoot);
  return cfg && Array.isArray(cfg.tracked) ? cfg.tracked : [];
}

// Exclusions (2026-08-23): `untracked` is the vault owner's veto over
// tracking INHERITANCE — same entry shapes as `tracked` (exact
// vault-relative file, or `dir/` prefix), checked last and winning, so
// a machine-written subtree (machine-owned `_details/` sub-notes, by
// design direct-write with no review cards) stays untracked even
// though the tracked parent embeds it. The closure also refuses to
// traverse INTO an excluded note, so nothing beyond it is dragged in
// through its links.
export function untrackedPaths(vaultRoot) {
  const cfg = readConfig(vaultRoot);
  return cfg && Array.isArray(cfg.untracked) ? cfg.untracked : [];
}

// ── tracking inheritance (2026-08-09): the flag propagates DOWN a note
// tree. A note is tracked when it is listed (or under a listed folder)
// OR reachable from a tracked note through whole-line [[link]]/![[embed]]
// lines, transitively (engine.childLinkLines defines the edge — the
// same one slides composition uses). The config stays EXPLICIT-ONLY and
// the closure is derived at read time, so untracking a parent releases
// its subtree automatically while an explicitly-listed child stays on.
//
// Link resolution outside Obsidian: an index of every .md in the vault
// (dot-dirs skipped) resolves a link target the way Obsidian does —
// path-ish text resolves against the full relative path, a bare name
// against its basename, SHORTEST path winning ties.

function walkVaultMd(vaultRoot) {
  const rels = [];
  const walk = (dir) => {
    let entries;
    try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { return; }
    for (const e of entries) {
      if (e.name.startsWith('.')) continue;
      const p = path.join(dir, e.name);
      if (e.isDirectory()) { if (e.name !== 'node_modules') walk(p); }
      else if (e.isFile() && e.name.toLowerCase().endsWith('.md')) {
        rels.push(path.relative(vaultRoot, p));
      }
    }
  };
  walk(vaultRoot);
  return rels;
}

function buildLinkIndex(vaultRoot) {
  const rels = walkVaultMd(vaultRoot);
  const byLowerRel = new Map();
  const byBasename = new Map();
  for (const rel of rels) {
    byLowerRel.set(rel.toLowerCase(), rel);
    const base = path.basename(rel, path.extname(rel)).toLowerCase();
    if (!byBasename.has(base)) byBasename.set(base, []);
    byBasename.get(base).push(rel);
  }
  return { rels, byLowerRel, byBasename };
}

function resolveLinkTarget(index, linkText) {
  const t = String(linkText || '').trim().replace(/^\.?\//, '');
  if (!t) return null;
  const lower = t.toLowerCase();
  const withMd = lower.endsWith('.md') ? lower : lower + '.md';
  if (index.byLowerRel.has(withMd)) return index.byLowerRel.get(withMd);
  const base = path.basename(lower, lower.endsWith('.md') ? '.md' : '');
  const hits = index.byBasename.get(base) || [];
  if (!hits.length) return null;
  return [...hits].sort((a, b) =>
    (a.split('/').length - b.split('/').length) || a.localeCompare(b))[0];
}

// The full derived-tracked set: explicit file entries, files under
// explicit folder entries, and everything reachable from either.
export function trackedClosure(vaultRoot) {
  const list = trackedPaths(vaultRoot);
  const out = new Set();
  if (!list.length) return out;
  const off = untrackedPaths(vaultRoot);
  const index = buildLinkIndex(vaultRoot);
  const queue = [];
  for (const raw of list) {
    if (typeof raw !== 'string' || !raw) continue;
    const e = raw.replace(/^\.?\//, '');
    if (e.endsWith('/')) {
      for (const rel of index.rels) if (rel.startsWith(e)) queue.push(rel);
    } else {
      queue.push(e);
    }
  }
  while (queue.length) {
    const rel = queue.pop();
    if (out.has(rel)) continue;
    if (engine.isTracked(off, rel)) continue;   // excluded: not in, not through
    out.add(rel);
    let text;
    try { text = fs.readFileSync(path.join(vaultRoot, rel), 'utf8'); } catch { continue; }
    for (const target of engine.childLinkLines(text)) {
      const child = resolveLinkTarget(index, target);
      if (child && !out.has(child)) queue.push(child);
    }
  }
  return out;
}

// Files a TRACKED EDIT must never touch. track-edit reads a file as UTF-8 text and
// writes the text back, which destroys any file that is not text (an image
// decoded with replacement characters is re-encoded over the original). So
// track-edit refuses these by name before reading a byte, and the guard hook
// lets the raw tools through for them instead of steering the agent to
// track-edit — a tracked image or PDF can only be regenerated, never edited as
// text. The list is names only, because the guard runs on every Edit/Write in
// every session and must stay cheap; hasNulBytes is the byte-level check for a
// binary file under a text-looking name, used once a file is known to be tracked.
export const NON_TEXT_EXTENSIONS = new Set((
  // images
  'png jpg jpeg gif webp bmp ico tif tiff heic heif avif psd'
  // documents and books
  + ' pdf doc docx xls xlsx ppt pptx odt ods odp odg epub pages numbers key'
  // archives
  + ' zip gz tgz bz2 tbz xz zst lz4 7z rar tar jar war ear'
  // audio and video
  + ' mp3 mp4 m4a m4v aac wav ogg oga ogv flac mov avi mkv webm wmv'
  // fonts
  + ' ttf otf woff woff2 eot'
  // executables, objects, bundles
  + ' exe dll so dylib o a bin class pyc pyo pyd wasm iso dmg'
  // binary data and model files
  + ' sqlite sqlite3 db parquet arrow feather npy npz pkl pickle h5 hdf5 pt pth onnx safetensors ckpt gguf'
).split(' '));

export function isNonTextPath(file) {
  const ext = path.extname(String(file == null ? '' : file)).slice(1).toLowerCase();
  return ext !== '' && NON_TEXT_EXTENSIONS.has(ext);
}

// True when the first 8 KB of an EXISTING file contain a NUL byte — text never
// does, binaries almost always do. Absent or unreadable → false: the caller's
// own read then decides.
export function hasNulBytes(file) {
  let fd;
  try {
    fd = fs.openSync(file, 'r');
    const buf = Buffer.alloc(8192);
    const n = fs.readSync(fd, buf, 0, buf.length, 0);
    return buf.subarray(0, n).includes(0);
  } catch { return false; } finally {
    if (fd !== undefined) { try { fs.closeSync(fd); } catch { /* ignore */ } }
  }
}

export function isTrackedFile(vaultRoot, file) {
  const rel = relPathFor(vaultRoot, file);
  if (engine.isTracked(untrackedPaths(vaultRoot), rel)) return false;   // veto wins
  const list = trackedPaths(vaultRoot);
  if (engine.isTracked(list, rel)) return true;
  if (!list.length) return false;
  return trackedClosure(vaultRoot).has(rel);
}
export function writeTrackedPaths(vaultRoot, list) {
  ensureTrackDir(vaultRoot);
  const clean = Array.isArray(list) ? [...new Set(list.filter((s) => typeof s === 'string' && s))] : [];
  const cfg = { v: CONFIG_VERSION, tracked: clean };
  // The rewrite must not eat the vault owner's exclusions.
  const off = untrackedPaths(vaultRoot);
  if (off.length) cfg.untracked = off;
  fs.writeFileSync(configPathFor(vaultRoot), JSON.stringify(cfg, null, 2) + '\n', 'utf8');
  return cfg;
}
export function setTracked(vaultRoot, relPath, on) {
  const list = trackedPaths(vaultRoot);
  if (on === false) return writeTrackedPaths(vaultRoot, list.filter((p) => p !== relPath));
  if (!list.includes(relPath)) list.push(relPath);
  return writeTrackedPaths(vaultRoot, list);
}

// ── store read / write ──────────────────────────────────────────────

// Normalize any on-disk store to the v3 shape. A v1 snapshot store (baseline +
// full-text edits chain) is migrated to ops; a v3 store is returned as-is.
// `currentText`, when given, re-anchors the ops to the live file (handles an
// external edit while the store was closed).
// True when a store was written by a NEWER version than this build understands.
// README states the contract: a consumer that reads a `v` it does not understand
// MUST refuse rather than risk corrupting a shared file. Without this the
// migration branch below treats a v4 store as a v1 snapshot store, finds none of
// the fields it expects, and yields zero suggestions — which the next save then
// writes back over the real data.
export function isUnsupportedVersion(obj) {
  return !!obj && typeof obj === 'object' && typeof obj.v === 'number' && obj.v > STORE_VERSION;
}

function normalize(obj, currentText) {
  if (!obj || typeof obj !== 'object') return null;
  if (isUnsupportedVersion(obj)) return null;
  let store = obj;
  if (obj.v !== STORE_VERSION || !Array.isArray(obj.suggestions)) {
    // v1 (or anything lacking suggestions): migrate. migrateV1 derives `current`
    // from the old snapshot chain; we keep the CALLER's current if provided.
    const mig = engine.migrateV1(obj);
    store = { v: STORE_VERSION, path: obj.path, suggestions: mig.suggestions, comments: mig.comments };
  }
  if (!Array.isArray(store.suggestions)) store.suggestions = [];
  if (!Array.isArray(store.comments)) store.comments = [];
  if (!Array.isArray(store.detached)) store.detached = Array.isArray(obj.detached) ? obj.detached : [];
  if (currentText != null) {
    // Rebase, don't drop: an op whose text an out-of-band writer edited
    // away is DETACHED — preserved with its diff + attribution for human
    // review (the review panel renders it as a stale card) — so the next
    // save keeps it instead of silently erasing it (design 2026-08-18).
    const rb = engine.rebaseSuggestions(currentText, store.suggestions, { merge: true });
    store.suggestions = rb.kept;
    if (rb.detached.length) {
      const have = new Set(store.detached.map((d) => d && d.id));
      for (const d of rb.detached) if (!have.has(d.id)) store.detached.push(d);
    }
    // RE-ATTACH: a detached op whose text places again (a sync race
    // detached it against transiently-stale text; the newer note then
    // arrived) returns to LIVE suggestions — reviewable, not a stale
    // card forever (user incident 2026-08-18).
    if (store.detached.length) {
      // STRICT + occupied: re-attach is exact-only and may never land on
      // a live op's span (review 2026-08-26 — this pass used to bypass
      // the merge stages' guards in the same load).
      const back = engine.rebaseSuggestions(currentText, store.detached,
        { occupied: store.suggestions });
      if (back.kept.length) {
        for (const op of back.kept) {
          const { detached: _d, ...live } = op;
          store.suggestions.push(live);
        }
        store.suggestions.sort((x, y) => x.from - y.from);
        store.detached = back.detached;
      }
    }
  }
  return store;
}

// Load, reporting WHY there is no store. `loadStore` collapses every failure to
// null, which makes an unparseable sidecar indistinguishable from one that was
// never written — and callers that delete or overwrite on "absent" then destroy
// data they merely failed to read. Callers that can do damage use this instead.
//   absent      no file
//   corrupt     unparseable, or structurally unusable
//   unsupported written by a newer version
//   unreadable  I/O error (permissions, etc.)
export function loadStoreStatus(storePath, currentText) {
  let raw;
  try {
    raw = fs.readFileSync(storePath, 'utf8');
  } catch (e) {
    return { store: null, status: e && e.code === 'ENOENT' ? 'absent' : 'unreadable' };
  }
  let obj;
  try { obj = JSON.parse(raw); } catch { return { store: null, status: 'corrupt' }; }
  if (isUnsupportedVersion(obj)) return { store: null, status: 'unsupported' };
  try {
    const store = normalize(obj, currentText);
    return store ? { store, status: 'ok' } : { store: null, status: 'corrupt' };
  } catch { return { store: null, status: 'corrupt' }; }
}

export function loadStore(storePath, currentText) {
  return loadStoreStatus(storePath, currentText).store;
}

// Write atomically: a full write into a temp file, fsync, then rename over the
// target. A bare writeFileSync leaves a TRUNCATED sidecar if the process dies or
// the disk fills mid-write, and a truncated sidecar reads as "no suggestions" —
// so an interrupted save silently discarded every pending suggestion for a note.
// rename(2) within one directory is atomic, so a reader sees either the old file
// or the new one, never a partial.
export function saveStore(vaultRoot, storePath, obj, currentText) {
  ensureTrackDir(vaultRoot);
  if (!obj.id) obj.id = randomUUID();
  obj.v = STORE_VERSION;
  obj.fingerprint = fingerprintOf(currentText);
  const tmp = `${storePath}.tmp`;
  const data = JSON.stringify(obj, null, 2);
  let fd;
  try {
    fd = fs.openSync(tmp, 'w');
    fs.writeFileSync(fd, data, 'utf8');
    try { fs.fsyncSync(fd); } catch { /* fsync unsupported on some filesystems */ }
  } finally {
    if (fd !== undefined) { try { fs.closeSync(fd); } catch { /* ignore */ } }
  }
  fs.renameSync(tmp, storePath);
}

// Delete the sidecar once a note has no pending suggestions and no comments.
// The caller's `store` can be stale — an agent CLI may have written new ops to
// the sidecar since it was loaded, and a delete based on the caller's belief
// alone would silently drop them. So the sidecar is re-read first and only
// deleted when the store ON DISK is clean too.
export function pruneIfClean(storePath, store) {
  if (!store || (store.suggestions || []).length > 0 || (store.comments || []).length > 0
    || (store.detached || []).length > 0) return false;
  const { store: disk, status } = loadStoreStatus(storePath);
  // Only an empty store that we could actually READ may be deleted. Previously a
  // corrupt or newer-version sidecar read as null, which this treated as "clean"
  // and unlinked — turning a recoverable read failure into permanent deletion of
  // the very suggestions it failed to parse.
  if (status !== 'ok' && status !== 'absent') return false;
  if (disk && ((disk.suggestions || []).length > 0 || (disk.comments || []).length > 0
    || (disk.detached || []).length > 0)) return false;
  try { fs.unlinkSync(storePath); return true; } catch { /* ignore */ }
  return false;
}

// When a file has NO sidecar at its keyed path, it may have been moved/renamed
// outside the editor (git mv, mv, a pull), orphaning its sidecar under the old
// key. Re-find it by content fingerprint — an unedited move is an exact hash
// match — and re-key it to this file. Won't steal a sidecar whose original file
// still exists (e.g. a duplicated file with identical text). Returns the healed
// store, or null. Mirrors the Obsidian plugin's healOrphanStore semantics.
export function healOrphanStore(vaultRoot, file, currentText) {
  if (currentText == null) return null;
  const target = storePathFor(vaultRoot, file);
  try { if (fs.existsSync(target)) return null; } catch { return null; }
  let entries;
  try { entries = fs.readdirSync(path.join(vaultRoot, STORE_DIR)); } catch { return null; }
  const want = hashText(currentText);
  const rel = relPathFor(vaultRoot, file);
  for (const name of entries) {
    if (!name.endsWith('.json') || name === CONFIG_FILE) continue;
    const p = path.join(vaultRoot, STORE_DIR, name);
    if (p === target) continue;
    let obj;
    try { obj = JSON.parse(fs.readFileSync(p, 'utf8')); } catch { continue; }
    const fp = obj && obj.fingerprint;
    if (!fp || fp.hash !== want) continue;
    if (obj.path && obj.path !== rel) {
      try { if (fs.existsSync(path.join(vaultRoot, obj.path))) continue; } catch { continue; }
    }
    const store = normalize(obj, currentText);
    if (!store) continue;
    store.path = rel;
    saveStore(vaultRoot, target, store, currentText);
    try { fs.unlinkSync(p); } catch { /* ignore */ }
    return store;
  }
  return null;
}

// Follow an EDITOR-OBSERVED rename: re-key the sidecar to the new path (across
// roots when the move crosses them) and carry the tracked-paths config entry
// along. `currentText` stamps the fingerprint; when omitted the new file is
// read from disk (a pure rename doesn't change content). Returns whether a
// sidecar was moved (the tracked flag moves regardless).
export function moveStoreForRename(oldRoot, oldFile, newRoot, newFile, currentText) {
  const oldRel = relPathFor(oldRoot, oldFile);
  const newRel = relPathFor(newRoot, newFile);
  const oldList = trackedPaths(oldRoot);
  if (oldList.includes(oldRel)) {
    writeTrackedPaths(oldRoot, oldList.filter((p) => p !== oldRel));
    setTracked(newRoot, newRel, true);
  }
  const oldPath = storePathFor(oldRoot, oldFile);
  const store = loadStore(oldPath);
  if (!store) return false;
  let text = currentText;
  if (text == null) {
    try { text = fs.readFileSync(path.resolve(newFile), 'utf8'); } catch { text = ''; }
  }
  store.path = newRel;
  saveStore(newRoot, storePathFor(newRoot, newFile), store, text);
  try { fs.unlinkSync(oldPath); } catch { /* ignore */ }
  return true;
}

// Load the store for a note (creating an empty v3 store if none), keyed to the
// note's CURRENT text.
export function ensureStore(vaultRoot, file, currentText) {
  const storePath = storePathFor(vaultRoot, file);
  const existing = loadStore(storePath, currentText);
  if (existing) return existing;
  return { v: STORE_VERSION, path: relPathFor(vaultRoot, file), suggestions: [], comments: [] };
}

// Record an agent edit as a tracked suggestion. `preText` is the note BEFORE the
// edit; `ch` = { from, to, insert } is the change that was applied to it. Reads
// the store (in pre-edit coords), remaps its ops through `ch`, appends the
// agent's op, and saves against the new text. Returns the saved store.
// Thrown when the caller's `preText` is too stale to record against safely.
export class StaleTextError extends Error {
  constructor(dropped) {
    super(`The note changed since it was read: recording this edit against that stale `
      + `text would discard ${dropped} suggestion(s) recorded by someone else. `
      + `Re-read the file and redo the edit against its current contents.`);
    this.name = 'StaleTextError';
    this.dropped = dropped;
  }
}

export function recordAgentEdit(vaultRoot, file, preText, ch, author, now, authorId) {
  const storePath = storePathFor(vaultRoot, file);
  // When re-anchoring against the caller's text cannot place some ops,
  // WHY decides what happens (design 2026-08-18, replacing the blanket
  // refusal that froze a note for agent editing until a review pass):
  //
  //  * The caller read STALE text (the note on disk has moved on) —
  //    writing would clobber another writer's text, the original
  //    two-sessions-erasing-each-other incident. REFUSE: re-reading and
  //    retrying is cheap and correct. Also refuse when a lost op is only
  //    seconds old — the CLI writes the sidecar BEFORE the note, so a
  //    racing writer's note write may still be in flight even though
  //    disk equals the caller's text.
  //
  //  * The caller's text IS the note's current content, and the ops were
  //    orphaned by an out-of-band writer editing inside their spans (the
  //    rename link-updater, footer stampers). Those ops are already
  //    DETACHED by the load above — preserved for review, shown as stale
  //    cards in the panel — and this edit proceeds. Nothing in the note
  //    is overwritten and nothing in the sidecar is lost.
  // STRICT rebase for the evidence (review 2026-08-26): the merge
  // stages can absorb an op against STALE caller text (its anchor
  // contexts exist there too), which silently defeated this refusal —
  // the original two-sessions-erasing-each-other class. The saved store
  // may merge; the judgement may not.
  const lostVs = (disk, text) => {
    const strictKept = new Set(engine.rebaseSuggestions(String(text == null ? '' : text),
      (disk && disk.suggestions) || []).kept.map((x) => x && x.id));
    return ((disk && disk.suggestions) || []).filter((x) => x && !strictKept.has(x.id));
  };
  let onDisk = loadStore(storePath);
  let store = ensureStore(vaultRoot, file, preText);
  if (onDisk) {
    let lost = lostVs(onDisk, preText);
    if (lost.length) {
      // Obsidian writes the NOTE first and its sidecar about half a
      // second later (debounced save) — the inverse of this CLI's
      // ordering. An edit landing in that window sees a just-resolved
      // op as "lost" and would detach (or worse, RELOCATE) a change the
      // user explicitly accepted/rejected. When the note file itself
      // changed within the last few seconds, wait out the debounce and
      // re-read both sides before judging (verify pass 2026-08-18).
      let noteFresh = false;
      try { noteFresh = Date.now() - fs.statSync(file).mtimeMs < 3000; } catch { /* strict below */ }
      if (noteFresh) {
        Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 1500);
        onDisk = loadStore(storePath);
        store = ensureStore(vaultRoot, file, preText);
        lost = lostVs(onDisk, preText);
      }
    }
    if (lost.length) {
      let diskNow = null;
      try { diskNow = fs.readFileSync(file, 'utf8'); } catch { /* unreadable — be strict */ }
      const youngest = Math.max(0, ...lost.map((s) => s.ts || 0));
      const racing = (now || Date.now()) - youngest < 15000;
      if (diskNow !== preText || racing) throw new StaleTextError(lost.length);
    }
  }
  const newText = preText.slice(0, ch.from) + ch.insert + preText.slice(ch.to);
  // `oldText` is what REJECTING this op must restore, so it may contain only
  // BASELINE text — not characters that are themselves another op's pending
  // insertion. Editing over a pending suggestion is routine (an agent revising
  // its own or another's proposal), and the raw slice double-counted it: the
  // overwritten op's removal survives as its own del (mapOpsThroughChange's
  // preserved-removal), and this op claimed the pending text again — so
  // reject-all restored the original AND the intermediate version, duplicating
  // the paragraph. Subtract the pending spans; what remains is genuine baseline.
  let removed = '';
  {
    const spans = (store.suggestions || [])
      .map((s) => engine.span(s))
      .filter((sp) => sp.b > sp.a && sp.a < ch.to && sp.b > ch.from)
      .sort((x, y) => x.a - y.a);
    let pos = ch.from;
    for (const sp of spans) {
      if (sp.a > pos) removed += preText.slice(pos, Math.min(sp.a, ch.to));
      pos = Math.max(pos, sp.b);
      if (pos >= ch.to) break;
    }
    if (pos < ch.to) removed += preText.slice(pos, ch.to);
  }
  const anchor = engine.makeAnchor(newText, ch.from, ch.from + ch.insert.length);
  // Timestamp+offset alone collides when two edits land at the same spot in the
  // same millisecond, and a duplicate id makes accept/reject ambiguous — the
  // filter-by-id in acceptSuggestion removes BOTH ops. Disambiguate against the
  // ids already in the store, the way the engine's split-id minting does.
  const used = new Set((store.suggestions || []).map((s) => s.id));
  let id = `${now || 0}-${ch.from}`;
  for (let n = 2; used.has(id); n++) id = `${now || 0}-${ch.from}#${n}`;
  store.suggestions = engine.recordAgentEdit(store.suggestions, ch,
    { id, author: author || 'unknown', ...(authorId ? { authorId } : {}), ts: now || 0, oldText: removed, anchor });
  store.path = relPathFor(vaultRoot, file);
  saveStore(vaultRoot, storePath, store, newText);
  // In-memory only (set after the save): lets the caller link this op to
  // a conversation thread (track-edit --thread → addThreadEditTurn).
  store.lastOpId = id;
  return store;
}

// Record an agent's responding edit as a turn in a thread (linked by the thread
// id it was pinged with), so a change made in answer to a comment shows up in
// that conversation even when it lands away from the comment's anchor.
// A thread stranded in a `.superseded` park: accepting the last change
// resolves-and-drops its thread and deleteStore parks the emptied store
// — but an agent may still be answering an in-flight ping into that
// thread (agent-session report 2026-08-27). Revive JUST that
// thread into a fresh live store so the conversation continues;
// everything else in the park stays archived. Returns the store or null.
export function reviveThreadFromSuperseded(vaultRoot, file, threadId, currentText) {
  const store = {
    v: 3,
    path: relPathFor(vaultRoot, file),
    suggestions: [],
    comments: [],
    detached: [],
  };
  if (!reviveThreadInto(vaultRoot, file, threadId, store)) return null;
  saveStore(vaultRoot, storePathFor(vaultRoot, file), store, currentText == null ? '' : currentText);
  return store;
}

// The same revive INTO a store that is already live, in place and without
// saving: the parked thread is appended to `store.comments` (reopened) and
// everything else in the store — its pending suggestions, its other
// comments — is kept. Use this when a live store exists but lacks the
// thread; reviveThreadFromSuperseded is only for the no-live-store case,
// because it builds a fresh store with an EMPTY suggestion list, and saving
// that over a live sidecar erased every pending change (a track-edit
// --thread reply used to erase the very op it had just recorded). Returns
// true when the thread was found in the park and added, false otherwise.
export function reviveThreadInto(vaultRoot, file, threadId, store) {
  const storePath = storePathFor(vaultRoot, file);
  let parked = null;
  try { parked = JSON.parse(fs.readFileSync(storePath + '.superseded', 'utf8')); }
  catch { return false; }
  const thread = ((parked && parked.comments) || [])
    .find((c) => c && String(c.id) === String(threadId));
  if (!thread) return false;
  if (!Array.isArray(store.comments)) store.comments = [];
  store.comments.push({ ...thread, resolved: false });
  return true;
}

export function addThreadEditTurn(vaultRoot, file, threadId, author, oldText, newText, now, currentText, opId, authorId) {
  if (!threadId) return false;
  const storePath = storePathFor(vaultRoot, file);
  const store = loadStore(storePath, currentText);
  if (!store) return false;
  const c = (store.comments || []).find((x) => String(x.id) === String(threadId));
  if (!c) return false;
  if (!Array.isArray(c.replies)) c.replies = [];
  c.replies.push({ author: author || 'unknown', ...(authorId ? { authorId } : {}), ts: now || 0, kind: 'edit', oldText: oldText || '', newText: newText || '' });
  // Link the thread to the op it answers (first edit wins): the panel
  // then merges the conversation into the change's card — the user's
  // prompt, the old→new revision, and the replies review as ONE unit,
  // and accepting/rejecting the change resolves the whole thread
  // (design 2026-08-24: no more stranded cards to dismiss by hand).
  if (opId != null && c.suggestionId == null) c.suggestionId = opId;
  saveStore(vaultRoot, storePath, store, currentText);
  return true;
}
