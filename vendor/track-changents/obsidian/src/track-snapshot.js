'use strict';

// Op-log track-changes: the Obsidian-side of the clean-file + side-store +
// inline-overlay model (engine in trackchanges/engine.js, agent CLIs in
// claude/hooks/track-*.mjs). The note on disk is the CURRENT text — the document
// as it reads with every pending suggestion APPLIED. A sidecar (v3) holds an
// ordered list of attributed OPS in current-text coordinates; this module renders
// them as an inline overlay (green insertions, struck-red deletions, author-
// colored in the panel), keeps the ops in sync with the human's own edits by
// MAPPING them through each change (never re-diffing), and drives accept/reject +
// comments through a review panel. Gated by a per-file default-OFF tracking
// toggle (the shared .trackchanges/config.json scope).
//
// The CodeMirror core: the ops live in a StateField (`suggestionsField`) whose
// value IS the op list. A human keystroke maps every op through tr.changes; an
// accept/reject dispatches a `setSuggestions` StateEffect. `invertedEffects`
// stores each effect's inverse in the undo history, so ACCEPT (an effect-only,
// text-unchanged transaction) is undoable and restores the suggestion — NOT the
// user's prior typing (the bug this rewrite fixes). Attribution is RECORDED, never
// reconstructed, so it cannot flip and cost is O(pending ops), not O(document).

const {
  ItemView, TFile, Modal, debounce, setIcon, editorLivePreviewField,
} = require('obsidian');
const { EditorView, Decoration, WidgetType, ViewPlugin } = require('@codemirror/view');
const { StateField, Transaction } = require('@codemirror/state');
const {
  setSuggestions, setTrackMeta, syncAnnotation, makeSuggestionField, makeInvertedEffects,
} = require('./track-cm.js');
const track = require('track-changents/engine');
const trackTree = require('./track-tree.js');
const rollup = require('./track-rollup.js');
const view = require('./host-badges.js');
const logic = require('./track-logic.js');
const { wireEnterToSend } = require('./compose-keys.js');

// Node's crypto is desktop-only: requiring it at module top-level throws on
// mobile (no Node) and aborts plugin load. Resolve it lazily so this module
// loads everywhere; the store flows that call it are desktop-only (registration
// is gated to desktop in main.js) and never run on mobile.
let _crypto;
function nodeCrypto() {
  if (_crypto === undefined) {
    try { _crypto = require('crypto'); } catch (e) { _crypto = null; }
  }
  return _crypto;
}

const PANEL_TYPE = 'tc-track-panel';
// Dedicated, plugin-agnostic store directory at the vault/repo root — committed
// to git as-is (the whole dir is the backup), nothing else lives here.
const STORE_DIR = '.trackchanges';
const SAVE_DEBOUNCE_MS = 400;
// Coalesce external-write reloads and let Obsidian's own buffer reload land first,
// so reloadActive re-anchors against a buffer that already matches disk.
const RELOAD_DEBOUNCE_MS = 150;

const sha = (s) => nodeCrypto().createHash('sha256').update(String(s == null ? '' : s), 'utf8').digest('hex');
// Content fingerprint over the CURRENT note text (the ops are anchored to it), so
// an unedited move is an exact match and orphan-heal can re-associate. MUST match
// store-io.mjs fingerprintOf: { hash: sha256(current), size: current.length }.
const fingerprintOf = (currentText) => {
  const t = currentText == null ? '' : currentText;
  return { hash: sha(t), size: t.length };
};

// A message timestamp: the clock time when it's from today, else a short date.
function fmtTime(ts) {
  if (!ts) return '';
  const d = new Date(ts);
  const now = new Date();
  const sameDay = d.getFullYear() === now.getFullYear()
    && d.getMonth() === now.getMonth() && d.getDate() === now.getDate();
  return sameDay
    ? d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
    : d.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

// ── store I/O over the vault adapter (v3 op-log) ────────────────────

function storePath(file) {
  return STORE_DIR + '/' + encodeURIComponent(file.path) + '.json';
}
function storePathFor(relPath) {
  return STORE_DIR + '/' + encodeURIComponent(relPath) + '.json';
}

async function ensureStoreDir(adapter) {
  try { if (!(await adapter.exists(STORE_DIR))) await adapter.mkdir(STORE_DIR); } catch (e) { /* may already exist */ }
}

// The sidecar schema version this build reads and writes. MUST track
// store-io.mjs's STORE_VERSION — it was hard-coded as a bare `3` in three places
// here, so bumping the shared constant would have left this host silently
// writing the old shape while claiming the new one.
const STORE_VERSION = 3;

// An empty in-memory store, so the panel + host always have a concrete object.
function emptyStore(relPath) {
  return { v: STORE_VERSION, path: relPath, suggestions: [], comments: [], detached: [] };
}

// Normalize any on-disk store to the v3 shape and re-anchor its ops to the live
// text. A v1 snapshot store (baseline + full-text edit chain) is migrated to ops;
// a v3 store is returned as-is. `currentText` re-locates the ops by their text-
// quote anchors (handles an external edit while the store was closed).
function normalizeStore(obj, currentText) {
  if (!obj || typeof obj !== 'object') return null;
  // Refuse a store written by a NEWER version instead of migrating it. Falling
  // through to migrateV1 here treated a v4 sidecar as a v1 snapshot store, found
  // none of the fields it expects, produced zero suggestions — and the next save
  // wrote that emptiness back over real data. The VS Code host has always had
  // this gate; the README calls it a MUST.
  if (typeof obj.v === 'number' && obj.v > STORE_VERSION) return null;
  let store = obj;
  if (obj.v !== STORE_VERSION || !Array.isArray(obj.suggestions)) {
    const mig = track.migrateV1(obj);
    store = { v: STORE_VERSION, path: obj.path, suggestions: mig.suggestions, comments: mig.comments, id: obj.id };
  }
  if (!Array.isArray(store.suggestions)) store.suggestions = [];
  if (!Array.isArray(store.comments)) store.comments = [];
  if (!Array.isArray(store.detached)) store.detached = Array.isArray(obj.detached) ? obj.detached : [];
  if (currentText != null) {
    // Rebase, don't drop: an op whose text an out-of-band writer edited
    // away is DETACHED — preserved with its diff + attribution and shown
    // in the panel as a stale card — instead of silently vanishing on
    // the next save (design 2026-08-18).
    const rb = track.rebaseSuggestions(currentText, store.suggestions, { merge: true });
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
      // STRICT + occupied: exact-only, never onto a live op's span
      // (review 2026-08-26 — this pass bypassed the merge guards).
      const back = track.rebaseSuggestions(currentText, store.detached,
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

async function loadStore(app, file, currentText) {
  const adapter = app.vault.adapter;
  const p = storePath(file);
  try {
    if (!(await adapter.exists(p))) return null;
    const obj = JSON.parse(await adapter.read(p));
    return normalizeStore(obj, currentText);
  } catch (e) { return null; }
}

async function saveStore(app, file, store, currentText, opts) {
  const adapter = app.vault.adapter;
  await ensureStoreDir(adapter);
  if (!store.id) store.id = nodeCrypto().randomUUID();
  store.v = 3;
  store.path = file.path;
  store.fingerprint = fingerprintOf(currentText);
  const p = storePath(file);
  const payload = JSON.stringify(store, null, 2);
  // Never DESTROY foreign work (review round 2, 2026-08-30): disk ids
  // absent from the payload AND not deliberately resolved by the caller
  // (opts.resolvedIds), or shared ids whose CONTENT diverged (a CLI
  // revising an op in place, a reply appended to a thread — no new id),
  // get the disk bytes parked to a TIMESTAMPED twin: the in-place
  // .superseded churns on routine resolutions and would be destroyed by
  // the very next one. Position shifts (`from`) are routine and never
  // count as divergence.
  let parkRaw = null;
  let parkNotice = false;
  try {
    const raw = await adapter.read(p);
    if (raw && raw !== payload) {
      const disk = JSON.parse(raw);
      const resolved = (opts && opts.resolvedIds) || new Set();
      const baseOf = (id) => String(id).replace(/([~#]p?\d+)+$/, '');
      const sig = (x) => JSON.stringify({
        o: (x && x.oldText) || '', n: (x && x.newText) || '',
        b: (x && x.body) || '', r: ((x && (x.replies || x.messages)) || []).length,
      });
      const mine = new Map();
      const mineBases = new Set();
      for (const k of ['suggestions', 'detached', 'comments']) {
        for (const x of store[k] || []) {
          const id = String(x && x.id);
          mine.set(id, sig(x));
          mineBases.add(baseOf(id));
        }
      }
      let unknownId = false;
      const foreign = ['suggestions', 'detached', 'comments'].some((k) =>
        (disk[k] || []).some((x) => {
          const id = String(x && x.id);
          if (resolved.has(id) || resolved.has(baseOf(id))) return false;
          if (mine.has(id)) return mine.get(id) !== sig(x);
          // Lineage kin (round 3): a payload fragment (`id~n`) and its
          // disk base (or vice versa) is USUALLY an in-editor split —
          // no foreign-writer Notice — but the kin content can't be
          // sig-verified across generations, so the disk bytes still
          // QUIET-PARK before the overwrite (a CLI revision of the base
          // after the split was otherwise destroyed with no trace).
          if (mine.has(baseOf(id)) || mineBases.has(id)) return true;
          unknownId = true; return true;
        }));
      if (foreign) { parkRaw = raw; parkNotice = unknownId; }
    }
  } catch (e) { /* absent or unreadable — nothing to park */ }
  // Fence BEFORE the park (round 2, 2026-09-01): callers that measured
  // the sidecar pass their expectation; a mismatch means a foreign
  // write just landed — write NOTHING (no park either: the foreign
  // bytes stay live on disk, and the deferred reload merges them; the
  // old park-then-defer left one junk .superseded-<ts> per deferral).
  if (opts && opts.expectedMtime !== undefined) {
    let st = null;
    try { st = await adapter.stat(p); } catch (e) { st = null; }
    if (st && (st.mtime || 0) !== opts.expectedMtime) return null;
  }
  if (parkRaw != null) {
    await adapter.write(`${p}.superseded-${Date.now()}`, parkRaw);
    if (parkNotice) {
      try {
        new (require('obsidian').Notice)(
          `Track changes: parked concurrent suggestions on ${file.basename} (recoverable in .trackchanges).`, 8000);
      } catch (e) { /* headless */ }
    }
  }
  await adapter.write(p, payload);
  return payload;
}

// Return contract (review round 2, 2026-08-30): true = disk no longer
// holds these bytes (caller may disarm/adopt mtime 0); false = nothing
// removed (foreign write detected, unaccounted entries on disk, or the
// remove itself failed) — the caller defers. An ABSENT sidecar is
// success, not deferral: returning falsy there put every clean,
// sidecar-less note into an unbounded save↔reload loop (executed
// repro, 312 cycles from one flush).
//
// `allowedIds` (incident 2026-09-01, two CLI stores parked ~1s after
// being written): a delete is only ever justified because the caller
// believes every entry was DELIBERATELY resolved — so the caller must
// say WHICH (the armed pendingByPath ids / the ids its mutation
// dropped). Any id on disk outside that set means a writer this caller
// never saw — defer, never park. Every mtime fence here is a race
// guard; this is the invariant that holds when all of them lose.
// Split residuals (`id~n` / `id#pN`, possibly nested) of an allowed id
// count as allowed. Omitted allowedIds = empty set (nothing vouched).
async function deleteStore(app, file, expectedMtime, allowedIds) {
  const adapter = app.vault.adapter;
  const p = storePath(file);
  try {
    if (!(await adapter.exists(p))) return true;
    // Never silently destroy review history (peer report 2026-08-26).
    let load = 1;   // unreadable counts as worth parking
    let diskIds = null;
    try {
      const obj = JSON.parse(await adapter.read(p));
      diskIds = [];
      for (const k of ['suggestions', 'comments', 'detached']) {
        for (const x of (obj && obj[k]) || []) diskIds.push(String(x && x.id));
      }
      load = diskIds.length;
    } catch (e) { /* keep load = 1, diskIds = null */ }
    if (load > 0) {
      const allowed = allowedIds || new Set();
      const baseOf = (id) => String(id).replace(/([~#]p?\d+)+$/, '');
      // Lineage vouching is SYMMETRIC (round 2, 2026-09-01): a disk
      // fragment is vouched by its armed base, and a disk BASE by an
      // armed fragment — the engine keeps s.id on the left half of a
      // split and mints `id~n` for the right, so either generation can
      // be the one that got armed. Bounded risk: this branch only runs
      // with an empty field, and a non-empty store parks by rename.
      const allowedBases = new Set([...allowed].map(baseOf));
      const vouched = (id) => allowed.has(id) || allowed.has(baseOf(id))
        || allowedBases.has(id) || allowedBases.has(baseOf(id));
      if (!diskIds || !diskIds.every(vouched)) return false;   // unaccounted → defer
    }
    // A foreign write during the read must survive: verify the sidecar
    // is still the one the caller measured (review 2026-08-30).
    if (expectedMtime !== undefined) {
      let st = null;
      try { st = await adapter.stat(p); } catch (e) { st = null; }
      if (st && (st.mtime || 0) !== expectedMtime) return false;
    }
    if (load > 0) {
      // Park by RENAME — atomic, so bytes landing up to the removal
      // instant survive in the park by construction (round 2: the old
      // write-then-remove could destroy a write in its final gap).
      // A PRIOR plain park is promoted to a timestamped twin first —
      // remove-then-rename destroyed it (incident 2026-09-01: the
      // second kill's park would have erased the first's only copy).
      // The plain name stays the rename target: the CLI's revive path
      // (store-io reviveThreadFromPark) reads exactly that name.
      try { await adapter.rename(`${p}.superseded`, `${p}.superseded-${Date.now()}`); } catch (e) { /* none */ }
      await adapter.rename(p, `${p}.superseded`);
    } else {
      // Empty store: plain remove; keep any prior (valuable) park.
      await adapter.remove(p);
    }
    return true;
  } catch (e) { return false; }   // failed remove/rename must not disarm
}

// mtime of a note's sidecar (0 if absent) — the cheap signal the poll watches so
// agent CLI writes (which land under .trackchanges/, unseen by vault events) get
// picked up without stringifying the whole store every tick.
async function storeMtime(app, file) {
  try { const st = await app.vault.adapter.stat(storePath(file)); return st ? (st.mtime || 0) : 0; } catch (e) { return 0; }
}

// Read the note's text straight from disk — the source of truth an agent CLI just
// wrote — NOT the live editor buffer, which lags a disk write by an async tick.
// Used when reloading after an external write so the sidecar's ops re-anchor
// against the exact text they were recorded against.
async function readNoteFromDisk(app, file) {
  try { return await app.vault.adapter.read(file.path); } catch (e) { return null; }
}

// Tracking SCOPE (.trackchanges/config.json) — the SINGLE control, shared with the
// skill + CLIs via store-io's contract: a flat LIST of vault-relative paths
// ({ v:2, tracked:[...] }). Read async over the adapter; plugin._trackEnabled
// caches whether the ACTIVE file is tracked so isEnabled() stays synchronous.
const CONFIG_PATH = STORE_DIR + '/config.json';
async function loadTrackedList(app) {
  const adapter = app.vault.adapter;
  try {
    if (!(await adapter.exists(CONFIG_PATH))) return [];
    const cfg = JSON.parse(await adapter.read(CONFIG_PATH));
    return cfg && Array.isArray(cfg.tracked) ? cfg.tracked : [];
  } catch (e) { return []; }
}
// The vault owner's exclusion list (untracked, 2026-08-23): same entry
// shapes as tracked, checked last and winning — see track-tree.js.
async function loadUntrackedList(app) {
  const adapter = app.vault.adapter;
  try {
    if (!(await adapter.exists(CONFIG_PATH))) return [];
    const cfg = JSON.parse(await adapter.read(CONFIG_PATH));
    return cfg && Array.isArray(cfg.untracked) ? cfg.untracked : [];
  } catch (e) { return []; }
}
async function saveTrackedList(app, list) {
  const adapter = app.vault.adapter;
  await ensureStoreDir(adapter);
  const clean = [...new Set((Array.isArray(list) ? list : []).filter((s) => typeof s === 'string' && s))];
  const cfg = { v: 2, tracked: clean };
  // The toggle's rewrite must not eat the owner's exclusions.
  const off = await loadUntrackedList(app);
  if (off.length) cfg.untracked = off;
  await adapter.write(CONFIG_PATH, JSON.stringify(cfg, null, 2) + '\n');
}
// I/O deps for the tracking-inheritance closure (track-tree.js): read
// notes through Obsidian's memory-backed cache, resolve links the way
// Obsidian itself does.
function trackTreeDeps(app) {
  return {
    readNote: async (p) => {
      const f = app.vault.getAbstractFileByPath(p);
      if (!(f instanceof TFile) || f.extension !== 'md') return null;
      try { return await app.vault.cachedRead(f); } catch (e) { return null; }
    },
    resolveLink: (target, fromPath) => {
      const dest = app.metadataCache.getFirstLinkpathDest(String(target || '').trim(), fromPath || '');
      return dest && dest.extension === 'md' ? dest.path : null;
    },
    listUnder: (folder) =>
      app.vault.getMarkdownFiles().filter((f) => f.path.startsWith(folder)).map((f) => f.path),
  };
}
async function isFileTracked(app, file) {
  if (!file) return false;
  return trackTree.isTrackedInTree(
    await loadTrackedList(app), file.path, trackTreeDeps(app),
    await loadUntrackedList(app),
  );
}
// EMBED-only closure deps: the review panel + rollup counts follow
// ![[embeds]] (the notes that render INSIDE the page — collapsed ones
// included), NOT plain [[link]] lines, so the sidebar matches what the
// document shows (user ask 2026-08-18). Tracking inheritance keeps the
// wider edge via trackTreeDeps.
function embedTreeDeps(app) {
  return { ...trackTreeDeps(app), childLines: track.childEmbedLines };
}

// When a note has NO store at its path, it may have been moved/renamed OUTSIDE
// Obsidian (git mv, mv, another editor, a pull), orphaning its store under the old
// key. Re-find it by content fingerprint — an unedited move is an exact hash match
// — then re-key it to this note. Won't steal a store whose original note still
// exists. Returns the normalized store, or null.
async function healOrphanStore(app, file, curText) {
  if (curText == null) return null;
  const adapter = app.vault.adapter;
  let listing;
  try { listing = await adapter.list(STORE_DIR); } catch (e) { return null; }
  const files = (listing && listing.files) || [];
  const want = sha(curText);
  const target = storePath(file);
  for (const f of files) {
    if (!f.endsWith('.json') || f === target || f === CONFIG_PATH) continue;
    let obj;
    try { obj = JSON.parse(await adapter.read(f)); } catch (e) { continue; }
    const fp = obj && obj.fingerprint;
    if (!fp || fp.hash !== want) continue;
    // Don't steal a store whose note still exists (e.g. a duplicated note with
    // identical text) — only adopt genuinely orphaned ones.
    if (obj.path && obj.path !== file.path) {
      try { if (await adapter.exists(obj.path)) continue; } catch (e) { /* gone → adopt */ }
    }
    const store = normalizeStore(obj, curText);
    if (!store) continue;
    await saveStore(app, file, store, curText);
    try { await adapter.remove(f); } catch (e) { /* ignore */ }
    return store;
  }
  return null;
}

// ── inline overlay decorations ──────────────────────────────────────

// setSuggestions / setTrackMeta / syncAnnotation now live in ./track-cm.js (the
// pure, Obsidian-free CM6 wiring) so the undo behaviour is exercised by a real
// unit test; they are imported at the top of this file.

// The two StateFields are created per makeExtension call, but buildDecorations
// (module-level) needs to read them off a given state. These boxes hold the
// current field instances so buildDecorations can resolve them.
const suggestionsFieldRef = { f: null };
const metaFieldRef = { f: null };

// The struck "old" text for a deletion/substitution — no longer in the document,
// so it must be a widget. Rendered with the legacy `tc-diff-del` look (red
// strikethrough), clickable per "click the version you want": a plain click
// accepts, Cmd/Option rejects (keep the original), Ctrl jumps to the panel.
// `mode`:
//   'above'   — float the struck old text ABOVE the word that replaced it (short sub)
//   'block'   — a struck section above the whole line, via a real block widget (used only
//               for a dense WHOLE-paragraph collapse, whose new text IS the paragraph)
//   'place'   — render the struck old text IN PLACE, inline (a PURE deletion)
//   'replace' — like 'place' but tinted as a substitution: the struck old text inline right
//               before the green new run, so a mid-paragraph rewrite reads old→new AT the change
class DelWidget extends WidgetType {
  constructor(text, offset, host, mode, keptTokens) {
    super();
    this.text = text;
    this.offset = offset;
    this.host = host;
    this.mode = mode || 'block';
    // Embed tokens still present in the CURRENT note: the move case —
    // rendered un-struck with a "moved" tag so a relocated image never
    // reads as deleted (update_writer report 2026-08-25).
    this.keptTokens = keptTokens || [];
  }
  eq(other) {
    return other instanceof DelWidget && other.text === this.text
      && other.offset === this.offset && other.mode === this.mode
      && (other.keptTokens || []).join(',') === (this.keptTokens || []).join(',');
  }
  toDOM() {
    const self = this;
    const wire = (el) => {
      el.setAttribute('data-hk-from', String(this.offset));
      el.setAttribute('data-hk-side', 'old');
      el.addEventListener('mousedown', (e) => {
        e.preventDefault();
        e.stopPropagation();
        // Ctrl → jump to this change's card to reply; Cmd/Option → reject; plain → accept.
        const action = logic.diffClickAction(e);
        if (action === 'jump') {
          // The widget may live in an EMBED editor: the panel card for
          // its change is keyed by that file, not the active note.
          self.host.onOpenPanel(self.offset, true, EditorView.findFromDOM(el));
          return;
        }
        // Same for resolution: without the view, an embed's deletion
        // resolves against the ACTIVE file and silently no-ops (user
        // report 2026-08-18 — insertion marks got this fix on 08-17 via
        // the editor-level handler; widgets stopPropagation before it).
        self.host.resolveInline(self.offset, action === 'reject', EditorView.findFromDOM(el));
      });
      el.addEventListener('contextmenu', (e) => e.preventDefault());  // macOS Ctrl-click
      el.addEventListener('mouseenter', () => hoverPair(self.offset, el.ownerDocument));
      el.addEventListener('mouseleave', () => hoverPair(null, el.ownerDocument));
    };
    if (this.mode === 'above') {
      const box = document.createElement('span');
      box.className = 'tc-diff-del-inline';
      const t = box.appendChild(document.createElement('span'));
      t.className = 'tc-diff-del-inline-text';
      t.textContent = String(this.text);
      box.appendChild(document.createElement('span')).className = 'tc-diff-chip';
      wire(box);
      return box;
    }
    if (this.mode === 'place' || this.mode === 'replace') {
      const span = document.createElement('span');
      span.className = this.mode === 'replace'
        ? 'tc-diff-del-place tc-diff-del-replace' : 'tc-diff-del-place';
      span.textContent = String(this.text);
      wire(span);
      return span;
    }
    const wrap = document.createElement('div');
    wrap.className = 'tc-diff-del-block';
    for (const ln of String(this.text).split('\n')) {
      const row = document.createElement('div');
      row.className = 'tc-diff-del-line';
      const segs = logic.segmentsByKeptTokens(ln, this.keptTokens);
      if (segs.length === 1 && !segs[0].kept) {
        row.textContent = ln.length ? ln : '​'; // zero-width so an empty removed line still has height
      } else {
        for (const seg of segs) {
          if (!seg.text) continue;
          const span = document.createElement('span');
          span.className = seg.kept ? 'tc-diff-del-kept-embed' : 'tc-diff-del-seg';
          span.textContent = seg.text;
          row.appendChild(span);
        }
      }
      wrap.appendChild(row);
    }
    wrap.appendChild(document.createElement('span')).className = 'tc-diff-chip';
    wire(wrap);
    return wrap;
  }
  ignoreEvent() { return true; }
}

// Box a change AND the removal it replaces together (they share data-hk-from).
//
// `root` is the editor's own DOM (and therefore its own document): a popped-out
// note lives in a SEPARATE window, so querying the main window's `document` found
// nothing and hover boxing was simply dead there. `lastHoverKey` short-circuits
// the common case — mouseover fires on every element boundary the pointer
// crosses, so without it, dragging the mouse across ordinary prose ran two
// document-wide queries per crossing.
let lastHoverKey = null;
let lastHoverRoot = null;
function hoverPair(key, root) {
  const scope = root || document;
  if (key === lastHoverKey && scope === lastHoverRoot) return;
  const prev = lastHoverRoot || document;
  prev.querySelectorAll('.tc-diff-hover').forEach((e) => e.classList.remove('tc-diff-hover'));
  if (scope !== prev) {
    scope.querySelectorAll('.tc-diff-hover').forEach((e) => e.classList.remove('tc-diff-hover'));
  }
  lastHoverKey = key;
  lastHoverRoot = key == null ? null : scope;
  if (key == null) return;
  scope.querySelectorAll('.tc-diff-add[data-hk-from="' + key + '"], .tc-diff-del-block[data-hk-from="' + key + '"], .tc-diff-del-inline[data-hk-from="' + key + '"], .tc-diff-del-place[data-hk-from="' + key + '"]')
    .forEach((e) => e.classList.add('tc-diff-hover'));
}

// Build the decoration set for one editor from the live ops + comments. The ops
// (suggestionsField) are turned into hunks (track.toHunks) against the derived
// baseline (track.baselineOf), then grouped for display (logic.planDiffDisplay) —
// the SAME rendering the snapshot engine fed, so the inline look is unchanged.
function buildDecorations(state, host) {
  if (!suggestionsFieldRef.f || !metaFieldRef.f) return Decoration.none;
  const meta = state.field(metaFieldRef.f);
  const ops = state.field(suggestionsFieldRef.f);
  const doc = state.doc;
  const comments = (meta && meta.comments) || [];
  // Check FIRST, materialize after. This extension is registered globally, so
  // hoisting `doc.toString()` above the gate made every markdown editor in the
  // vault — tracked or not, with ops or without — allocate a full copy of its
  // document on every keystroke.
  const enabled = logic.shouldShowTrackUI(!!(meta && meta.trackingOn), ops.length, comments.length);
  if (!enabled) return Decoration.none;
  const current = doc.toString();
  const baseline = track.baselineOf(current, ops);
  const hunks = logic.planDiffDisplay(track.toHunks(ops), baseline, current);
  // Frontmatter ops get NO inline widgets in Live Preview: the Properties
  // UI replaces those lines, so a struck-red widget there floats detached
  // from any readable context ("something in the frontmatter was deleted"
  // — user report 2026-08-14, from a remote editor's legitimate rename of
  // an experiment id field). The review panel still shows the full
  // old→new change and accept/reject work from there; SOURCE mode still
  // renders inline, where the YAML lines really exist. Zero-width points
  // exactly at the frontmatter's end belong to the body and still render.
  const livePreview = editorLivePreviewField
    ? state.field(editorLivePreviewField, false) === true : false;
  const fmEnd = livePreview ? logic.frontmatterEnd(current) : 0;
  const insideFm = (from, to) => fmEnd > 0 && from < fmEnd && Math.max(to, from) <= fmEnd;
  const ranges = [];
  for (const h of hunks) {
    if (insideFm(h.curFrom, h.curTo)) continue;
    if (h.oldText) {
      const at = Math.min(h.curFrom, doc.length);
      if (h.display === 'paragraph') {
        // A dense WHOLE-paragraph collapse — the new text IS the whole paragraph, so a real
        // block widget at the paragraph top sits directly above its all-green form.
        ranges.push(Decoration.widget({
          widget: new DelWidget(h.oldText, h.curFrom, host, 'block',
            logic.keptEmbedTokens(h.oldText, current)),
          block: true,
          side: -1,
        }).range(doc.lineAt(at).from));
      } else {
        // Every other case — a short or long substitution, or a pure deletion — renders the
        // struck OLD text INLINE right before the new run (at curFrom), so it reads with the
        // change and adds NO extra vertical space. This replaces the old 'above' FLOAT (which
        // opened a fixed vertical band above the line — its reserve was the whole green run's
        // height, so a multi-row replacement opened a huge empty gap) and the old paragraph-top
        // 'block' widget (which stranded the struck text far from the change). A substitution
        // gets the 'replace' tint (reads old→new); a pure deletion gets plain 'place'.
        ranges.push(Decoration.widget({
          widget: new DelWidget(h.oldText, h.curFrom, host, h.newText ? 'replace' : 'place',
            logic.keptEmbedTokens(h.oldText, current)),
          side: -1,
        }).range(at));
      }
    }
    if (h.newText) {
      ranges.push(Decoration.mark({
        class: 'tc-diff-add',
        attributes: { 'data-hk-from': String(h.curFrom), 'data-hk-side': 'new' },
      }).range(h.curFrom, h.curTo));
    }
  }
  // Anchored highlights: a real comment thread is YELLOW (tc-hl-anchor); a Cmd-M
  // "pending message" (kind:'message') is BLUE (tc-hl-pending) — shown while it's
  // STILL PENDING (the anchored text is unchanged), auto-resolving when it changes.
  for (const c of comments) {
    const isMsg = c.kind === 'message';
    if (isMsg && !track.messageStillPending(current, c.anchor)) continue;
    const loc = track.locateAnchor(current, c.anchor);
    if (!loc) continue;
    if (insideFm(loc.from, loc.to)) continue; // same Properties-UI rule as ops
    if (loc.from === loc.to) {
      // A ZERO-WIDTH anchor — ⌘M sent from a bare cursor, no selection.
      // A mark can't render on nothing, so the message used to have no
      // inline presence at all (user report 2026-08-18: "highlight the
      // area I sent the message from until the response comes back").
      // Tint the whole LINE while the message is pending.
      if (isMsg) {
        ranges.push(Decoration.line({
          class: 'tc-hl-pending-line',
          attributes: { 'data-hk-message': String(c.id), 'data-hk-from': String(loc.from) },
        }).range(doc.lineAt(loc.from).from));
      }
      continue;
    }
    const attributes = isMsg
      ? { 'data-hk-message': String(c.id), 'data-hk-from': String(loc.from) }
      : { 'data-hk-comment': String(c.id), 'data-hk-from': String(loc.from) };
    ranges.push(Decoration.mark({ class: isMsg ? 'tc-hl-pending' : 'tc-hl-anchor', attributes }).range(loc.from, loc.to));
  }
  return Decoration.set(ranges, true);
}

function makeExtension(host) {
  // The op list IS this field's value (see ./track-cm.js for the update rules).
  const suggestionsField = makeSuggestionField();
  const metaField = StateField.define({
    create: () => ({ trackingOn: false, comments: [] }),
    update(value, tr) {
      for (const e of tr.effects) if (e.is(setTrackMeta)) return e.value;
      return value;
    },
  });
  suggestionsFieldRef.f = suggestionsField;
  metaFieldRef.f = metaField;

  const decoField = StateField.define({
    create(state) { return buildDecorations(state, host); },
    update(value, tr) {
      const pushed = tr.effects.some((e) => e.is(setSuggestions) || e.is(setTrackMeta));
      if (tr.docChanged || pushed) return buildDecorations(tr.state, host);
      return value;
    },
    provide: (f) => EditorView.decorations.from(f),
  });

  // Undo history glue (see ./track-cm.js): storing the previous ops as the inverse
  // of a setSuggestions effect is what makes an accept — a text-unchanged,
  // effect-only transaction — recorded in history and undoable (Cmd-Z restores the
  // suggestion, not the user's earlier typing).
  const invert = makeInvertedEffects(suggestionsField);

  // Persist + refresh: whenever the ops changed (human keystroke mapped through, or
  // an accept/reject), mirror the field into the host's store and schedule a
  // debounced sidecar save. Loads (carrying syncAnnotation) are skipped so they
  // don't echo back to disk.
  const persist = EditorView.updateListener.of((update) => {
    if (update.transactions.some((t) => t.annotation(syncAnnotation))) return;
    const opsEffect = update.transactions.some((t) => t.effects.some((e) => e.is(setSuggestions)));
    if (!update.docChanged && !opsEffect) return;
    // `deliberate` = the user resolved something (accept/reject), as opposed to a
    // doc change the ops were folded through. The save path needs to tell these
    // apart: a doc change may be Obsidian replaying an agent CLI's file write, in
    // which case DISK is authoritative; a deliberate resolution only exists in the
    // field, so it must be persisted or it is lost.
    host.onOpsChanged(update.view, opsEffect);
  });

  const CHANGE_SEL = '.tc-diff-add[data-hk-from], .tc-diff-del-block[data-hk-from], .tc-diff-del-inline[data-hk-from], .tc-diff-del-place[data-hk-from]';
  const clicks = EditorView.domEventHandlers({
    mousedown: (event, view) => {
      const t = event.target;
      const add = t && t.closest ? t.closest('.tc-diff-add[data-hk-from]') : null;
      if (add) {
        const from = Number(add.getAttribute('data-hk-from'));
        const action = logic.diffClickAction(event);
        if (action === 'jump') { event.preventDefault(); host.onOpenPanel(from, true, view); return true; }
        // A mark whose position no longer RESOLVES — sidecar/doc drift
        // while the heal machinery catches up (agent rewrote the note
        // underneath) — must NOT swallow the click: that reads as
        // "cannot edit the note" (user reports 2026-08-17/18, a 3.5k-char
        // pending block ate every click). Let CM place the cursor.
        if (!host.hasResolvableAt(view, from)) return false;
        event.preventDefault();
        // Pass the clicked editor: an EMBED editor hosts a different
        // file than the active view, and position lookup must happen in
        // ITS doc (user report 2026-08-17: accept/reject clicks inside
        // embedded notes did nothing).
        host.resolveInline(from, action === 'reject', view);
        return true;
      }
      const com = t && t.closest ? t.closest('[data-hk-comment], [data-hk-message]') : null;
      if (com) {
        // Jump by ID, never by offset: mid-edit the text shifts between
        // the mark's build and the panel's render, and an offset match
        // lands on whatever stale card shares the number.
        const cid = com.getAttribute('data-hk-comment') || com.getAttribute('data-hk-message');
        host.onOpenPanel(cid ? 'id:' + cid : Number(com.getAttribute('data-hk-from')), undefined, view);
        return false;
      }
      return false;
    },
    // A pending change may CONTAIN a link. While it is pending, click
    // means accept/reject (handled on mousedown above) — never navigate
    // (user's call 2026-08-15: the double meaning made accepting a
    // linked insertion jump away). The text still RENDERS as a link;
    // navigation returns the moment the change is resolved and the mark
    // is gone. mousedown's preventDefault doesn't cancel Obsidian's
    // link handling, which runs on click — so click is suppressed too.
    click: (event, view) => {
      const t = event.target;
      const hit = t && t.closest ? t.closest(CHANGE_SEL) : null;
      if (hit) {
        // Same drift guard as mousedown: a dead mark keeps normal click
        // behavior (links navigate, cursor stays placed).
        const from = Number(hit.getAttribute('data-hk-from'));
        if (!host.hasResolvableAt(view, from)) return false;
        event.preventDefault();
        event.stopPropagation();
        return true;
      }
      return false;
    },
    contextmenu: (event) => {
      const t = event.target;
      if (t && t.closest && t.closest('.tc-diff-add[data-hk-from], .tc-diff-del-block[data-hk-from], .tc-diff-del-inline[data-hk-from], .tc-diff-del-place[data-hk-from], [data-hk-comment]')) {
        event.preventDefault();
        return true;
      }
      return false;
    },
    mouseover: (event) => {
      const t = event.target;
      const hit = t && t.closest ? t.closest(CHANGE_SEL) : null;
      hoverPair(hit ? hit.getAttribute('data-hk-from') : null, view.dom.ownerDocument);
    },
    mouseout: (event, view) => {
      if (!event.relatedTarget || !view.dom.contains(event.relatedTarget)) hoverPair(null, view.dom.ownerDocument);
    },
  });

  // Hydrate an editor's overlay the instant it mounts (workspace restore on reload,
  // a new split pane), so unresolved changes show without waiting for focus.
  const hydrateOnMount = ViewPlugin.fromClass(class {
    constructor(view) { Promise.resolve().then(() => host.hydrateView(view)); }
  });
  return [suggestionsField, metaField, decoField, invert, persist, clicks, inlineDelLayout, hydrateOnMount];
}

// After CM lays out the text, pack each wrap row's floating "struck text above the
// word" boxes so they don't overlap or spill past the text column. The packing
// math is the pure logic.layoutInlineRemovals; here we only measure + apply.
const inlineDelLayout = ViewPlugin.fromClass(class {
  constructor(view) { this.run(view); }
  update(u) { if (u.docChanged || u.viewportChanged || u.geometryChanged) this.run(u.view); }
  run(view) {
    view.requestMeasure({
      key: 'tcDelInlineLayout',
      read: (v) => {
        const content = v.contentDOM;
        const cRect = content.getBoundingClientRect();
        const items = [];
        content.querySelectorAll('.tc-diff-del-inline').forEach((a) => {
          const b = a.querySelector('.tc-diff-del-inline-text');
          if (!b) return;
          const ar = a.getBoundingClientRect();
          const br = b.getBoundingClientRect();
          const line = a.closest ? a.closest('.cm-line') : null;
          let lineH = 0;
          const addRun = line ? line.querySelector('.tc-diff-add') : null;
          if (addRun) lineH = addRun.getBoundingClientRect().height;
          else if (line) lineH = parseFloat(getComputedStyle(line).lineHeight) || 0;
          if (!lineH) lineH = br.height;
          items.push({ a, b, row: Math.round(ar.top), ax: ar.left - cRect.left, w: br.width, h: br.height, lineH });
        });
        return { cW: cRect.width, items };
      },
      write: (data) => {
        const rows = new Map();
        for (const it of data.items) {
          if (!rows.has(it.row)) rows.set(it.row, []);
          rows.get(it.row).push(it);
        }
        for (const row of rows.values()) {
          const lineH = Math.max(0, ...row.map((it) => it.lineH || 0));
          const { height, placed } = logic.layoutInlineRemovals(row, data.cW, lineH);
          for (let i = 0; i < row.length; i++) {
            row[i].a.style.height = height + 'px';
            row[i].b.style.left = placed[i].left + 'px';
            row[i].b.style.top = placed[i].top + 'px';
          }
        }
      },
    });
  }
});

// ── review panel ────────────────────────────────────────────────────

class TrackPanelView extends ItemView {
  constructor(leaf, host) {
    super(leaf);
    this.host = host;
    this.rerender = debounce(() => this.refresh(), 150, true);
  }
  getViewType() { return PANEL_TYPE; }
  getDisplayText() { return 'Track changes'; }
  getIcon() { return 'git-compare'; }

  async onOpen() {
    this.contentEl.addClass('tc-panel');
    this.refresh(true);
  }
  async onClose() {
    // Cancel the queued rebuild, or a 150ms refresh fires against a detached
    // view after teardown. The flash timer is the same class of leak.
    try { this.rerender.cancel(); } catch (e) { /* older debounce impls */ }
    if (this._flashTimer) { window.clearTimeout(this._flashTimer); this._flashTimer = null; }
    this._lastSig = null;
    this.contentEl.empty();
  }

  notifyChanged() { this.rerender(); }

  // Jump to a change's card and (optionally) drop the caret into its reply box.
  // `offset` is a bare number for the active note, "path#offset" for a
  // closure note's card.
  focusChange(offset, focusReply) {
    if (offset == null || (typeof offset !== 'number' && typeof offset !== 'string')) return;
    this._focusReq = { offset, focusReply: !!focusReply };
    this.rerender.cancel();
    this.refresh();
  }

  _applyPendingFocus() {
    const req = this._focusReq;
    if (!req) return;
    const want = String(req.offset);
    const byId = want.startsWith('id:') ? want.slice(3) : null;
    const card = byId
      ? Array.from(this.contentEl.querySelectorAll('[data-tc-card-id]'))
        .find((el) => el.getAttribute('data-tc-card-id') === byId)
      : Array.from(this.contentEl.querySelectorAll('[data-tc-card-offset]'))
        .find((el) => el.getAttribute('data-tc-card-offset') === want);
    if (!card) {
      // A closure card may not exist yet (its sections render from the
      // async snapshot) — keep the request alive a few refreshes.
      req.tries = (req.tries || 0) + 1;
      if (req.tries >= 5) this._focusReq = null;
      return;
    }
    this._focusReq = null;
    card.scrollIntoView({ behavior: 'smooth', block: 'center' });
    card.addClass('tc-card-flash');
    if (this._flashTimer) window.clearTimeout(this._flashTimer);
    this._flashTimer = window.setTimeout(() => {
      this._flashTimer = null;
      card.removeClass('tc-card-flash');
    }, 1200);
    if (req.focusReply) {
      const ta = card.querySelector('.tc-reply-input');
      if (ta) ta.focus({ preventScroll: true });
    }
  }

  // The ON/OFF control at the top of the panel — the editor-side toggle that writes
  // the shared per-repo flag. Guarded so a click can't be dropped: the button
  // DISABLES itself for the duration of the async flip (a mid-flight panel rebuild
  // can't then destroy it under the pointer), and the host ignores a config-poll
  // reload while a toggle is in flight.
  renderToggleBar(container) {
    const on = this.host.isTrackingOn();
    const bar = container.createDiv({ cls: 'tc-toggle-bar' });
    const btn = bar.createEl('button', { cls: 'tc-toggle', text: on ? 'Tracking ON' : 'Tracking OFF' });
    btn.dataset.tcOn = on ? '1' : '0';
    btn.setAttr('title', on
      ? 'Tracked changes are recorded for review in this note. Click to turn off.'
      : 'Edits apply normally in this note. Click to turn on tracked changes.');
    btn.addEventListener('click', async () => {
      if (btn.disabled) return;
      btn.disabled = true;
      try { await this.host.toggleTracking(); } finally { btn.disabled = false; }
    });
  }

  // Everything a rebuild would otherwise throw away.
  //
  // `_render` empties contentEl and rebuilds every card, and it is driven by
  // every keystroke in the note, every leaf change, and a 2s poll. With nothing
  // preserved, clicking a card to see it in context (which refocuses the editor,
  // which fires active-leaf-change, which rebuilds) discarded a half-typed reply
  // and threw the scroll position back to the top. Reviewing a long diff meant
  // fighting the panel.
  _captureUiState() {
    const drafts = new Map();
    for (const ta of this.contentEl.querySelectorAll('.tc-reply-input')) {
      if (!ta.value) continue;
      const card = ta.closest('[data-tc-card-offset]');
      const key = card && card.getAttribute('data-tc-card-offset');
      if (key != null) {
        drafts.set(key, { value: ta.value, focused: ta === ta.ownerDocument.activeElement,
          start: ta.selectionStart, end: ta.selectionEnd });
      }
    }
    return { scrollTop: this.contentEl.scrollTop, drafts };
  }

  _restoreUiState(saved) {
    if (!saved) return;
    for (const [key, d] of saved.drafts) {
      const card = this.contentEl.querySelector(`[data-tc-card-offset="${key}"]`);
      const ta = card && card.querySelector('.tc-reply-input');
      if (!ta) continue;                     // that change is gone; the draft goes with it
      ta.value = d.value;
      if (d.focused) {
        ta.focus({ preventScroll: true });
        try { ta.setSelectionRange(d.start, d.end); } catch (e) { /* ignore */ }
      }
    }
    if (saved.scrollTop) this.contentEl.scrollTop = saved.scrollTop;
  }

  // What the panel actually displays. If this is unchanged there is nothing to
  // redraw, so the 2s poll and every keystroke that doesn't move a change become
  // free instead of a full teardown. Deliberately includes the note text: a pure
  // text edit shifts where changes sit, so a signature over ops alone would go
  // stale.
  _renderSignature(ctx) {
    if (!ctx) return 'none:' + (this.host.isTrackingOn() ? '1' : '0');
    const ops = (ctx.ops || []).map((o) => `${o.id}@${o.from}+${(o.newText || '').length}-${(o.oldText || '').length}`);
    const cs = (ctx.comments || []).map((c) => `${c.id}:${(c.replies || []).length}:${c.resolved ? 1 : 0}:${c.detached ? 1 : 0}`);
    return [ctx.file && ctx.file.path, this.host.isTrackingOn() ? '1' : '0',
      ops.join(','), cs.join(','),
      (((ctx.store && ctx.store.detached) || []).map((d) => d && d.id)).join(','),
      ctx.current || ''].join('\x00');
  }

  refresh(force) {
    const ctx = this.host.activeContext();
    // The closure snapshot belongs to ONE active file: on switch, drop
    // it immediately (stale sections for the previous tree would render
    // until the async rebuild lands) and force a fresh build.
    const forPath = ctx && ctx.file ? ctx.file.path : null;
    if (forPath !== this._closureForPath) {
      this._closureForPath = forPath;
      this._closureCtxs = [];
      this._closureFreshAt = null;
    }
    const sig = this._renderSignature(ctx) + '||' + this._closureSig(this._closureCtxs);
    // A focus request must always rebuild — it targets a card that may not exist yet.
    if (!force && !this._focusReq && sig === this._lastSig && this.contentEl.firstChild) {
      this._kickClosureRefresh();
      return;
    }
    const saved = this._captureUiState();
    this._render(ctx);
    this._lastSig = sig;
    this._restoreUiState(saved);
    this._applyPendingFocus();
    this._kickClosureRefresh();
  }

  // Closure notes (the active note's embed tree) render from a cached
  // snapshot: building their contexts reads files (async) while
  // refresh() must stay sync. Every refresh kicks an async rebuild;
  // when the result differs from what's on screen, ONE forced re-render
  // follows and then settles on the signature (observer-convergence
  // contract — the kick after a forced render hits an equal signature
  // and stops).
  _closureSig(ctxs) {
    if (!ctxs || !ctxs.length) return '';
    // djb2 over the text, not just its length: a same-length edit in a
    // closure note (checkbox toggle, 1:1 word swap) must still move the
    // signature or its cards' anchors silently go stale.
    const hash = (s) => {
      let h = 5381;
      for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) | 0;
      return h;
    };
    return ctxs.map((c) => [c.file.path,
      (c.ops || []).map((o) => `${o.id}@${o.from}+${(o.newText || '').length}-${(o.oldText || '').length}`).join(','),
      (c.comments || []).map((x) => `${x.id}:${(x.replies || []).length}:${x.resolved ? 1 : 0}`).join(','),
      ((c.detached || []).map((d) => d && d.id)).join(','),
      hash(c.current || '')].join('~')).join(' || ');
  }

  _kickClosureRefresh(force) {
    if (!this.host.closureContexts) return;
    if (this._closureBusy) { this._closureAgain = true; return; }
    // Rebuilding reads every closure note's sidecar from disk;
    // unthrottled, a panel refreshing per keystroke would do that every
    // 150ms. A just-completed build stays authoritative for a second —
    // the 2.5s scan poll re-notifies when a sidecar really changes.
    if (!force && this._closureFreshAt && Date.now() - this._closureFreshAt < 1000) return;
    this._closureBusy = true;
    void this.host.closureContexts().then((ctxs) => {
      this._closureBusy = false;
      this._closureFreshAt = Date.now();
      const changed = this._closureSig(ctxs) !== this._closureSig(this._closureCtxs);
      this._closureCtxs = ctxs;
      if (changed) this.refresh(true);
      if (this._closureAgain) { this._closureAgain = false; this._kickClosureRefresh(true); }
    }).catch(() => { this._closureBusy = false; });
  }

  _render(precomputedCtx) {
    const ctx = precomputedCtx !== undefined ? precomputedCtx : this.host.activeContext();
    this.contentEl.empty();
    this.renderToggleBar(this.contentEl);
    if (!ctx) {
      this.contentEl.createEl('p', { cls: 'tc-empty', text: this.host.isTrackingOn()
        ? 'Open a markdown note to review tracked changes.'
        : 'Tracking is off for this note — edits apply normally. Turn it on above to review changes.' });
      return;
    }
    const { file, ops, comments, current } = ctx;
    const baseline = ctx.baseline;
    // Panel change cards derive from the SAME ops → hunks → display grouping the
    // inline overlay uses, so a card and its inline form stay in lockstep and
    // Accept/Reject acts on the same unit.
    const hunks = logic.planDiffDisplay(track.toHunks(ops), baseline, current);
    const threadComments = (comments || []).filter((c) => c.kind !== 'message');
    const pendingMsgs = (comments || []).filter((c) => c.kind === 'message' && track.messageStillPending(current, c.anchor));

    const header = this.contentEl.createDiv({ cls: 'tc-header' });
    header.createDiv({ cls: 'tc-header-title', text: file.basename });
    const countParts = [`${hunks.length} ${hunks.length === 1 ? 'change' : 'changes'}`,
      `${threadComments.length} ${threadComments.length === 1 ? 'comment' : 'comments'}`];
    if (pendingMsgs.length) countParts.push(`${pendingMsgs.length} pending`);
    if (((ctx.store && ctx.store.detached) || []).length) countParts.push(`${ctx.store.detached.length} stale`);
    header.createDiv({ cls: 'tc-header-counts', text: countParts.join(' · ') });

    const closureCtxs = this._closureCtxs || [];
    const detachedOps = (ctx.store && ctx.store.detached) || [];
    if (hunks.length === 0 && threadComments.length === 0 && pendingMsgs.length === 0
        && detachedOps.length === 0) {
      this.contentEl.createEl('p', { cls: 'tc-empty', text: this.host.isTrackingOn()
        ? 'No pending changes or comments.'
        : 'Tracking is off for this note — edits apply normally. Turn it on above to track new changes.' });
      // Embedded notes' work still needs reviewing even when the note
      // itself is clean — fall through to the closure sections.
      for (const c of closureCtxs) this._renderClosureSection(this.contentEl, c);
      return;
    }

    const bulk = this.contentEl.createDiv({ cls: 'tc-card-actions' });
    if (hunks.length > 0) {
      const a = bulk.createEl('button', { cls: 'tc-btn-accept', text: 'Accept all' });
      a.addEventListener('click', () => this.host.acceptAll());
      const r = bulk.createEl('button', { cls: 'tc-btn-reject', text: 'Reject all' });
      r.addEventListener('click', () => this.host.rejectAll());
    }

    const list = this.contentEl.createDiv({ cls: 'tc-card-list' });
    // A change-thread is keyed to its op by `suggestionId` (the op id) — the same
    // key the VS Code side uses, so the shared sidecar agrees across editors.
    const changeThreads = threadComments.filter((c) => c.suggestionId != null);
    const bareComments = threadComments.filter((c) => c.suggestionId == null);
    const overlapsHunk = (c, h) => {
      if (!c.anchor) return false;
      const loc = track.locateAnchor(current, c.anchor);
      return !!loc && loc.from < h.curTo && loc.to > h.curFrom;
    };
    const threadFor = (h) => changeThreads.find((c) => c.suggestionId === h.id)
      || bareComments.find((c) => overlapsHunk(c, h));
    const matched = new Set();
    const items = [];
    for (const h of hunks) {
      const th = threadFor(h);
      if (th) matched.add(th.id);
      items.push({ at: h.curFrom, render: () => this.renderChangeCard(list, h, th) });
    }
    for (const c of bareComments) {
      if (matched.has(c.id)) continue;
      const loc = track.locateAnchor(current, c.anchor);
      items.push({ at: loc ? loc.from : Number.MAX_SAFE_INTEGER, render: () => this.renderCommentCard(list, c, current) });
    }
    for (const c of changeThreads) {
      if (matched.has(c.id)) continue;
      items.push({ at: Number.MAX_SAFE_INTEGER - 1, render: () => this.renderCommentCard(list, c, current) });
    }
    for (const c of pendingMsgs) {
      const loc = track.locateAnchor(current, c.anchor);
      items.push({ at: loc ? loc.from : Number.MAX_SAFE_INTEGER, render: () => this.renderPendingCard(list, c, current) });
    }
    // Detached ops (an out-of-band writer edited away their anchor text)
    // have no position — they review at the end, dismiss-only.
    for (const d of detachedOps) {
      items.push({ at: Number.MAX_SAFE_INTEGER, render: () => this.renderDetachedCard(list, d, file) });
    }
    items.sort((a, b) => a.at - b.at);
    for (const it of items) it.render();
    for (const c of closureCtxs) this._renderClosureSection(this.contentEl, c);
  }

  // One section per embed-tree note with pending work — header (note
  // name + counts; click opens the note), its own Accept/Reject all,
  // then the same cards as the active note with every action routed to
  // the *InFile host methods, so reviewing the whole tree never
  // requires opening a child note ("everything I could do from the top
  // level", 2026-08-18).
  _renderClosureSection(container, ctx) {
    const hunks = logic.planDiffDisplay(track.toHunks(ctx.ops), ctx.baseline, ctx.current);
    const threadComments = (ctx.comments || []).filter((c) => c.kind !== 'message');
    const pendingMsgs = (ctx.comments || []).filter((c) => c.kind === 'message' && track.messageStillPending(ctx.current, c.anchor));
    const detachedOps = ctx.detached || [];
    if (!hunks.length && !threadComments.length && !pendingMsgs.length && !detachedOps.length) return;
    const sec = container.createDiv({ cls: 'tc-embed-section' });
    const head = sec.createDiv({ cls: 'tc-embed-section-header' });
    const name = head.createDiv({ cls: 'tc-embed-section-title', text: ctx.file.basename });
    name.setAttr('title', 'Open ' + ctx.file.path);
    name.addEventListener('click', () => {
      void this.app.workspace.openLinkText(ctx.file.path, '', false);
    });
    const parts = [`${hunks.length} ${hunks.length === 1 ? 'change' : 'changes'}`];
    if (threadComments.length) parts.push(`${threadComments.length} ${threadComments.length === 1 ? 'comment' : 'comments'}`);
    if (pendingMsgs.length) parts.push(`${pendingMsgs.length} pending`);
    if (detachedOps.length) parts.push(`${detachedOps.length} stale`);
    head.createDiv({ cls: 'tc-header-counts', text: parts.join(' · ') });
    if (hunks.length > 0) {
      const bulk = sec.createDiv({ cls: 'tc-card-actions' });
      const a = bulk.createEl('button', { cls: 'tc-btn-accept', text: 'Accept all' });
      a.addEventListener('click', () => this.host.acceptAllInFile(ctx.file));
      const r = bulk.createEl('button', { cls: 'tc-btn-reject', text: 'Reject all' });
      r.addEventListener('click', () => this.host.rejectAllInFile(ctx.file));
    }
    const list = sec.createDiv({ cls: 'tc-card-list' });
    const changeThreads = threadComments.filter((c) => c.suggestionId != null);
    const bareComments = threadComments.filter((c) => c.suggestionId == null);
    const overlapsHunk = (c, h) => {
      if (!c.anchor) return false;
      const loc = track.locateAnchor(ctx.current, c.anchor);
      return !!loc && loc.from < h.curTo && loc.to > h.curFrom;
    };
    const threadFor = (h) => changeThreads.find((c) => c.suggestionId === h.id)
      || bareComments.find((c) => overlapsHunk(c, h));
    const matched = new Set();
    const items = [];
    for (const h of hunks) {
      const th = threadFor(h);
      if (th) matched.add(th.id);
      // Freeze the hunk's op IDS against the snapshot it renders from —
      // the click resolves those ids against fresh state, never a
      // possibly-shifted position.
      const hh = { ...h, _tcIds: this.host.idsForHunk ? this.host.idsForHunk(ctx.ops, ctx.current, h) : [] };
      items.push({ at: h.curFrom, render: () => this.renderChangeCard(list, hh, th, ctx.file) });
    }
    for (const c of bareComments) {
      if (matched.has(c.id)) continue;
      const loc = track.locateAnchor(ctx.current, c.anchor);
      items.push({ at: loc ? loc.from : Number.MAX_SAFE_INTEGER, render: () => this.renderCommentCard(list, c, ctx.current, ctx.file) });
    }
    for (const c of changeThreads) {
      if (matched.has(c.id)) continue;
      items.push({ at: Number.MAX_SAFE_INTEGER - 1, render: () => this.renderCommentCard(list, c, ctx.current, ctx.file) });
    }
    for (const c of pendingMsgs) {
      const loc = track.locateAnchor(ctx.current, c.anchor);
      items.push({ at: loc ? loc.from : Number.MAX_SAFE_INTEGER, render: () => this.renderPendingCard(list, c, ctx.current, ctx.file) });
    }
    for (const d of detachedOps) {
      items.push({ at: Number.MAX_SAFE_INTEGER, render: () => this.renderDetachedCard(list, d, ctx.file) });
    }
    items.sort((a, b) => a.at - b.at);
    for (const it of items) it.render();
  }

  // A DETACHED op: an out-of-band writer (rename link-updater, footer
  // stamper) edited away the text this suggestion anchored to, so it can
  // no longer be applied in place — but its diff and attribution are
  // preserved for a human call. Dismiss is the only action; reapplying
  // by hand is a normal edit.
  renderDetachedCard(list, d, file) {
    const card = list.createDiv({ cls: 'tc-card tc-card-detached' });
    const head = card.createDiv({ cls: 'tc-thread-header' });
    head.createDiv({ cls: 'tc-line-ref', text: d.newText ? (d.oldText ? 'Replace' : 'Insert') : 'Delete' });
    // A ghost the USER's own typing created reads differently from an
    // out-of-band orphan: their edit WON, this is the audit trail.
    const sup = d.superseded === 'user-edit';
    head.createSpan({ cls: 'tc-stale-tag' + (sup ? ' tc-superseded-tag' : ''),
      text: sup
        ? 'superseded by your edit' + (d.supersededTs ? ' · ' + fmtTime(d.supersededTs) : '')
        : 'text since edited — cannot auto-apply' });
    const tl = card.createDiv({ cls: 'tc-timeline' });
    this.revRow(tl, { author: d.author, authorId: d.authorId, ts: d.ts || 0, oldText: d.oldText, newText: d.newText });
    const actions = card.createDiv({ cls: 'tc-reply-actions' });
    // Send the orphaned change back to its author (canned re-apply
    // request; user ask 2026-08-26) — resolution by recorded session id
    // survives renames. Success dismisses the stale copy here.
    if (!sup && this.host && typeof this.host.sendDetachedBack === 'function') {
      const back = actions.createEl('button', { text: 'Send back' });
      back.setAttr('title', 'Ask the author to re-apply this against the current text');
      back.addEventListener('click', async () => {
        back.disabled = true;
        let ok = false;
        try { ok = await this.host.sendDetachedBack(file, d); } catch (e) { ok = false; }
        if (ok) this.host.dismissDetached(file, d.id);
        else back.disabled = false;
      });
    }
    const dis = actions.createEl('button', { cls: 'tc-btn-danger', text: 'Dismiss' });
    dis.addEventListener('click', () => this.host.dismissDetached(file, d.id));
  }

  // A Cmd-M "pending message": a lightweight, auto-resolving card. It clears itself
  // when the anchored text changes (the edit lands), but a message whose text never
  // changes would otherwise linger — so it also carries a manual Dismiss control.
  renderPendingCard(list, c, current, forFile) {
    const card = list.createDiv({ cls: 'tc-card tc-card-pending' });
    card.setAttr('data-tc-card-id', String(c.id));
    const loc = c.anchor ? track.locateAnchor(current, c.anchor) : null;
    if (loc) card.setAttr('data-tc-card-offset', forFile ? `${forFile.path}#${loc.from}` : String(loc.from));
    card.addEventListener('click', (e) => {
      if (e.target.closest('button, textarea')) return;
      if (forFile) { void this.app.workspace.openLinkText(forFile.path, '', false); return; }
      if (loc) this.host.reveal(loc.from);
    });
    const head = card.createDiv({ cls: 'tc-thread-header' });
    head.createDiv({ cls: 'tc-line-ref', text: c.anchor && c.anchor.quote ? `“${c.anchor.quote.slice(0, 40)}”` : 'Message' });
    this._peerChip(head, c);
    head.createSpan({ cls: 'tc-pending-tag', text: 'pending' });
    // The quote can outlive its anchor briefly (the agent edits the anchored
    // region; the auto-resolve prune lands on the next reload) — during that
    // window the card must not look broken (user ask 2026-08-18).
    if (c.anchor && !loc) head.createSpan({ cls: 'tc-stale-tag', text: 'text since edited' });
    this.renderMessages(card, c);
    const awaited = c.pingAuthor || null;
    if (awaited) this.host.typingRow(card, awaited);
    const actions = card.createDiv({ cls: 'tc-reply-actions' });
    const dismiss = actions.createEl('button', { cls: 'tc-btn-danger', text: 'Dismiss' });
    dismiss.addEventListener('click', () => (forFile
      ? this.host.resolveCommentInFile(forFile, c.id)
      : this.host.dismissMessage(c.id)));
  }

  // The session a thread talks TO (or last talked to): pingAuthor when
  // recorded, else the first non-'you' author in the conversation. The
  // card header shows its colored chip UNCONDITIONALLY (user ask
  // 2026-08-31) — before it has replied, after it replied last, always —
  // so every thread names its counterpart at a glance.
  _peerChip(head, c) {
    const peer = (c && c.pingAuthor)
      || (c && c.author && c.author !== 'you' ? c.author : null)
      || (((c && c.replies) || []).find((r) => r && r.author && r.author !== 'you') || {}).author
      || null;
    if (!peer) return;
    const chip = head.createSpan({ cls: 'tc-message-author tc-attr-chip tc-thread-peer', text: peer });
    try { this.host.colorChip(chip, peer); } catch (e) { /* uncolored */ }
    try { this.host.stateChip(head, peer); } catch (e) { /* no dot */ }
    this._refreshAuthorChip(chip, { author: peer, authorId: c && c.pingAuthorId });
  }

  // One message row: author chip + live status dot + right-aligned time + body.
  msgRow(container, author, body, ts, authorId) {
    const m = container.createDiv({ cls: `tc-message tc-message-${author && author !== 'you' ? 'named' : 'you'}` });
    const meta = m.createDiv({ cls: 'tc-message-meta' });
    const who = meta.createDiv({ cls: 'tc-message-who' });
    const a = who.createSpan({ cls: 'tc-message-author tc-attr-chip', text: author || 'you' });
    if (author && author !== 'you') this.host.colorChip(a, author);
    this.host.stateChip(who, author);
    this._refreshAuthorChip(a, { author, authorId });
    meta.createSpan({ cls: 'tc-message-time', text: fmtTime(ts) });
    m.createDiv({ cls: 'tc-message-body' }).setText(body || '');
  }

  // One diff row: the same who·when header as a message, body is an old→new diff.
  // Live-name refresh (user ask 2026-08-26): ops record the session's
  // stable id; the rows resolve the CURRENT name, so a renamed agent's
  // chip self-heals. Recorded name renders immediately; the patch (and
  // its color re-key) lands async. A name with no live session gets the
  // stale styling instead — the send-back button explains itself then.
  _refreshAuthorChip(el, ref) {
    if (!ref || !ref.author || ref.author === 'you') return;
    if (!this.host || typeof this.host.resolveAuthorRow !== 'function') return;
    void Promise.resolve(this.host.resolveAuthorRow({ author: ref.author, authorId: ref.authorId }))
      .then((r) => {
        if (!r || !el.isConnected) return;
        if (r.live && r.renamed && r.name) {
          el.setAttr('title', `edited as ${ref.author} — session renamed`);
          el.setText(r.name);
          try { this.host.colorChip(el, r.name); } catch (e) { /* keep old color */ }
        } else if (!r.live) {
          el.addClass('tc-attr-stale');
          el.setAttr('title', 'no live session with this name (renamed or exited)');
        }
      })
      .catch(() => {});
  }

  revRow(container, step) {
    const m = container.createDiv({ cls: 'tc-message tc-message-rev' });
    const meta = m.createDiv({ cls: 'tc-message-meta' });
    const who = meta.createDiv({ cls: 'tc-message-who' });
    const a = who.createSpan({ cls: 'tc-message-author tc-attr-chip', text: step.author || 'you' });
    if (step.author && step.author !== 'you') this.host.colorChip(a, step.author);
    this.host.stateChip(who, step.author);
    this._refreshAuthorChip(a, step);
    meta.createSpan({ cls: 'tc-message-time', text: fmtTime(step.ts) });
    const diff = m.createDiv({ cls: 'tc-diff tc-diff-rev' });
    if (step.oldText) diff.createDiv({ cls: 'tc-diff-removed' }).setText(step.oldText);
    if (step.oldText && step.newText) diff.createDiv({ cls: 'tc-diff-arrow' }).setText('→');
    if (step.newText) diff.createDiv({ cls: 'tc-diff-added' }).setText(step.newText);
  }

  renderMessages(container, comment) {
    if (!comment) return;
    const msgs = container.createDiv({ cls: 'tc-messages' });
    this.msgRow(msgs, comment.author, comment.body, comment.ts, comment.authorId);
    for (const r of (comment.replies || [])) {
      if (r.kind === 'edit') this.revRow(msgs, { author: r.author, authorId: r.authorId, ts: r.ts, oldText: r.oldText, newText: r.newText });
      else this.msgRow(msgs, r.author, r.body, r.ts, r.authorId);
    }
  }

  renderReplyBox(container, placeholder, onSubmit) {
    const reply = container.createDiv({ cls: 'tc-reply tc-edit-reply' });
    const ta = reply.createEl('textarea', { cls: 'tc-reply-input', attr: { placeholder, rows: '2', title: 'Enter to reply · Shift+Enter for a new line' } });
    const actions = reply.createDiv({ cls: 'tc-reply-actions' });
    const send = actions.createEl('button', { cls: 'tc-btn-primary', text: 'Reply' });
    const submit = () => { const t = ta.value.trim(); if (!t) return; ta.value = ''; onSubmit(t); };
    wireEnterToSend(ta, submit);
    send.addEventListener('click', submit);
    return actions;
  }

  // A change card: its CURRENT diff (op-log has no revision chain) then the thread's
  // messages in time order — suggestion → comment → reply.
  renderChangeCard(list, h, thread, forFile) {
    const card = list.createDiv({ cls: 'tc-card tc-card-suggestion' });
    card.setAttr('data-tc-card-offset', forFile ? `${forFile.path}#${h.curFrom}` : String(h.curFrom));
    card.addEventListener('click', (e) => {
      if (e.target.closest('button, textarea')) return;
      if (forFile) { void this.app.workspace.openLinkText(forFile.path, '', false); return; }
      this.host.reveal(h.curFrom);
    });
    card.createDiv({ cls: 'tc-line-ref', text: h.kind === 'ins' ? 'Insert' : h.kind === 'del' ? 'Delete' : 'Replace' });
    const actions = card.createDiv({ cls: 'tc-card-actions' });
    const acc = actions.createEl('button', { cls: 'tc-btn-accept', text: 'Accept' });
    acc.addEventListener('click', () => (forFile
      ? this.host.resolveIdsInFile(forFile, h._tcIds || [], false)
      : this.host.acceptAt(h.curFrom)));
    const rej = actions.createEl('button', { cls: 'tc-btn-reject', text: 'Reject' });
    rej.addEventListener('click', () => (forFile
      ? this.host.resolveIdsInFile(forFile, h._tcIds || [], true)
      : this.host.rejectAt(h.curFrom)));

    const tl = card.createDiv({ cls: 'tc-timeline' });
    this.revRow(tl, { author: h.author, authorId: h.authorId, ts: h.ts || (thread && thread.ts) || 0, oldText: h.oldText, newText: h.newText });
    if (thread) {
      this.msgRow(tl, thread.author, thread.body, thread.ts);
      for (const r of (thread.replies || [])) {
        if (r.kind === 'edit') this.revRow(tl, { author: r.author, authorId: r.authorId, ts: r.ts, oldText: r.oldText, newText: r.newText });
        else this.msgRow(tl, r.author, r.body, r.ts);
      }
    }
    // If your turn is the latest, the change's author owes a reply — "typing" dots
    // (visible only while that session is working).
    let lastAuthor = h.author;
    if (thread) {
      const last = (thread.replies && thread.replies.length) ? thread.replies[thread.replies.length - 1] : thread;
      lastAuthor = last.author;
    }
    const awaited = (thread && lastAuthor === 'you')
      ? (thread.pingAuthor || (thread.author && thread.author !== 'you' ? thread.author : null)) : null;
    if (awaited) this.host.typingRow(card, awaited);
    this.renderReplyBox(card, 'Reply to this change…', (t) => (forFile
      ? this.host.replyToChangeInFile(forFile, h, t)
      : this.host.replyToChange(h, t)));
  }

  renderCommentCard(list, c, current, forFile) {
    const card = list.createDiv({ cls: 'tc-card tc-card-thread' });
    card.setAttr('data-tc-card-id', String(c.id));
    const loc = c.anchor ? track.locateAnchor(current, c.anchor) : null;
    if (loc) card.setAttr('data-tc-card-offset', forFile ? `${forFile.path}#${loc.from}` : String(loc.from));
    card.addEventListener('click', (e) => {
      if (e.target.closest('button, textarea')) return;
      if (forFile) { void this.app.workspace.openLinkText(forFile.path, '', false); return; }
      if (loc) this.host.reveal(loc.from);
    });
    const head = card.createDiv({ cls: 'tc-thread-header' });
    head.createDiv({ cls: 'tc-line-ref', text: c.anchor && c.anchor.quote ? `“${c.anchor.quote.slice(0, 40)}”` : 'Discussion' });
    this._peerChip(head, c);
    if (c.anchor && !loc) head.createSpan({ cls: 'tc-stale-tag', text: 'text since edited' });
    // A FORKED thread runs on a parallel branch of the session — not
    // first-class, reachable only from this card (user ask 2026-08-31).
    if (c.fork && c.fork.id) head.createSpan({ cls: 'tc-fork-badge', text: 'forked' });
    this.renderMessages(card, c);
    const lastMsg = (c.replies && c.replies.length) ? c.replies[c.replies.length - 1] : c;
    const awaited = (lastMsg.author === 'you')
      ? (c.pingAuthor || (c.author && c.author !== 'you' ? c.author : null)) : null;
    if (awaited) this.host.typingRow(card, awaited);
    const actions = this.renderReplyBox(card, 'Reply…', (t) => (forFile
      ? this.host.replyToCommentInFile(forFile, c.id, t)
      : this.host.replyToComment(c.id, t)));
    if (c.fork && c.fork.id) {
      const out = actions.createEl('button', { text: 'Branch out' });
      out.setAttr('title', 'Promote this fork to a first-class session');
      out.addEventListener('click', async () => {
        out.disabled = true;
        const r = await require('./romp.js').kernelForkPromote(c.fork.id);
        new Notice(r
          ? `Branched out${r.promotedName ? ` as "${r.promotedName}"` : ''} — the fork is now a full session.`
          : 'Could not promote the fork (kernel unreachable or unsupported).');
        out.disabled = false;
      });
    }
    const del = actions.createEl('button', { cls: 'tc-btn-danger', text: 'Resolve' });
    del.addEventListener('click', () => (forFile
      ? this.host.resolveCommentInFile(forFile, c.id)
      : this.host.resolveComment(c.id)));
  }
}

// Small modal to type a new comment's body.
class CommentModal extends Modal {
  constructor(app, quote, onSubmit) { super(app); this.quote = quote; this.onSubmit = onSubmit; }
  onOpen() {
    const { contentEl } = this;
    this.titleEl.setText('Comment');
    if (this.quote) contentEl.createEl('blockquote', { text: this.quote.slice(0, 200) });
    const ta = contentEl.createEl('textarea', { cls: 'tc-diff-rewrite-input', attr: { rows: '3', placeholder: 'Your comment… (↵ to add · ⇧/⌘↵ newline)' } });
    wireEnterToSend(ta, () => { const v = ta.value.trim(); this.close(); if (v) this.onSubmit(v); });
    setTimeout(() => ta.focus(), 0);
  }
  onClose() { this.contentEl.empty(); }
}

// ── plugin wiring ───────────────────────────────────────────────────

function isEnabled(plugin) { return plugin._trackEnabled === true; } // default OFF

function activeMarkdownEditor(app) {
  const { MarkdownView } = require('obsidian');
  const view = app.workspace.getActiveViewOfType(MarkdownView);
  return view && view.file ? view : null;
}

function cmOf(editor) { return editor && editor.cm ? editor.cm : null; }

function register(plugin) {
  const app = plugin.app;
  const diffRewrite = require('./romp.js');
  const resolveColor = diffRewrite.makeColorResolver();

  plugin._trackEnabled = false;
  Promise.resolve().then(() => pushActive().catch(() => {}));

  // Live modifier cues on <body> (CSS keys on these): Cmd/Option → reject-mode,
  // Ctrl → jump-mode.
  // Every window the workspace spans. A popped-out note is a separate window with
  // its OWN document, so cueing only the main window's <body> left the reject/jump
  // affordances dead in a popout — the same main-window-`document` assumption that
  // broke hover boxing there.
  const allBodies = () => {
    const docs = new Set([document]);
    try {
      app.workspace.iterateAllLeaves((leaf) => {
        const el = leaf && leaf.view && (leaf.view.containerEl || leaf.view.contentEl);
        if (el && el.ownerDocument) docs.add(el.ownerDocument);
      });
    } catch (e) { /* transient */ }
    return Array.from(docs).map((d) => d.body).filter(Boolean);
  };
  const syncModeCues = (e) => {
    const reject = !!(e && (e.metaKey || e.altKey));
    const jump = !!(e && e.ctrlKey);
    for (const b of allBodies()) {
      b.classList.toggle('tc-diff-reject-mode', reject);
      b.classList.toggle('tc-diff-jump-mode', jump);
    }
  };
  const clearModeCues = () => {
    for (const b of allBodies()) {
      b.classList.remove('tc-diff-reject-mode', 'tc-diff-jump-mode');
    }
  };
  plugin.registerDomEvent(window, 'keydown', syncModeCues);
  plugin.registerDomEvent(window, 'keyup', syncModeCues);
  plugin.registerDomEvent(window, 'blur', clearModeCues);
  // A popout window gets its own key events; without these the cues never fire
  // while the pointer and focus are inside it.
  plugin.registerEvent(app.workspace.on('window-open', (ww) => {
    const win = ww && (ww.win || ww.window);
    if (!win) return;
    plugin.registerDomEvent(win, 'keydown', syncModeCues);
    plugin.registerDomEvent(win, 'keyup', syncModeCues);
    plugin.registerDomEvent(win, 'blur', clearModeCues);
  }));

  // Cache of the active file's store so the panel + host are synchronous.
  // { file, store, mtime }. store is always a concrete v3 object (empty if clean).
  let active = null;
  // Set while a toggle is mid-flight so the config poll / leaf-change can't clobber it.
  let toggling = false;
  // Set while reloadActive re-syncs from disk after an external (agent CLI) write, so
  // the editor buffer catching up to disk isn't mistaken for a human edit and
  // persisted over the freshly written sidecar (the read-after-write race).
  let externalReloading = false;
  // Set when the field holds an accept/reject not yet on disk. See doSave.
  // Deliberate resolutions (accept/reject/dismiss) exist only in memory
  // until the debounced save lands. They used to arm a BOOLEAN that let
  // the save bypass the external-write guard — which deterministically
  // clobbered a CLI-written sidecar whenever a reload's opening flush ran
  // with the flag up (agent-session incident 2026-08-30: the
  // agent's op became untracked plain text and the sidecar vanished).
  // Now: per-op ID SETS. The guard always defers to disk; reloadActive
  // filters ONLY these ids out of what it loads, so the user's
  // resolutions survive without ever overwriting foreign ops.
  // ops/detached: id → {o, n} snapshot of the resolved entry (a same-id
  // CLI revision — including of a DELETION, whose newText is always ''
  // — must stay live, so both texts are compared); comments: id → a
  // content signature (an appended reply revives the thread). `path`
  // stamps which file the ids belong to: folds must never disarm ids
  // into the wrong file's sidecar (review round 2, 2026-08-30).
  // KEYED PER FILE (review round 3, 2026-08-30): a single pool with a
  // path stamp let (a) armed ids of a file you switched away from be
  // orphan-cleared on the way back and (b) an arm in file B re-attribute
  // and then disarm file A's unwritten ids. Entries exist only while a
  // save is deferred; the fold and the load-filter both look up by path.
  const pendingByPath = new Map();   // path → { ops, detached, comments } (Maps id → snapshot)
  const resolvedFor = (path) => {
    let e = pendingByPath.get(path);
    if (!e) { e = { ops: new Map(), detached: new Map(), comments: new Map() }; pendingByPath.set(path, e); }
    return e;
  };
  const entryEmpty = (e) => !e || (!e.ops.size && !e.detached.size && !e.comments.size);
  const pruneEntry = (path) => { if (entryEmpty(pendingByPath.get(path))) pendingByPath.delete(path); };
  const opSnapshot = (x) => ({ o: String((x && x.oldText) || ''), n: String((x && x.newText) || '') });
  const snapMatches = (snap, x) => !!snap && typeof snap === 'object'
    && snap.o === String((x && x.oldText) || '') && snap.n === String((x && x.newText) || '');
  const commentSig = (c) => { try { return JSON.stringify(c); } catch (e) { return null; } };
  // Filter a disk store through the pending resolutions, keeping
  // everything foreign. Both op lists check the UNION of resolved ids —
  // normalizeStore moves ops between suggestions and detached (rebase
  // detach / re-attach) — and split residuals (`id#pN`, possibly
  // nested) of a resolved id drop with their parent.
  const applyPendingResolved = (store, e) => {
    if (entryEmpty(e)) return store;
    const baseOf = (id) => String(id).replace(/(#p\d+)+$/, '');
    const snapFor = (id) => (e.ops.has(id) ? e.ops.get(id)
      : e.detached.has(id) ? e.detached.get(id) : undefined);
    const gone = (x) => {
      const id = String(x && x.id);
      const snap = snapFor(id);
      if (snap !== undefined) return snap == null || snapMatches(snap, x);
      const b = baseOf(id);
      return b !== id && snapFor(b) !== undefined;   // split residuals of a resolved op
    };
    store.suggestions = (store.suggestions || []).filter((o) => !gone(o));
    store.detached = (store.detached || []).filter((d) => !gone(d));
    if (e.comments.size) {
      store.comments = (store.comments || []).filter((c) => {
        const sig = e.comments.get(String(c && c.id));
        if (sig === undefined) return true;
        return !(sig === null || sig === commentSig(c));   // revived by new content
      });
    }
    return store;
  };
  // Scoped clears: only ids armed BEFORE a write may clear after it — an
  // id armed during the write's awaits is not in the written bytes.
  // KEYS(), not entries — Maps iterate [id, snapshot] pairs, and a
  // pair-Set neither disarms nor exempts anything (round 3: every
  // comment resolution false-parked with a spurious Notice).
  const armSnapshot = (e) => ({
    ops: new Set(e ? e.ops.keys() : []),
    detached: new Set(e ? e.detached.keys() : []),
    comments: new Set(e ? e.comments.keys() : []),
  });
  const disarm = (e, snap) => {
    if (!e) return;
    for (const id of snap.ops) e.ops.delete(id);
    for (const id of snap.detached) e.detached.delete(id);
    for (const id of snap.comments) e.comments.delete(id);
  };
  // Auto-addressed Cmd-M messages are a resolution the protocol makes on
  // the user's behalf — they must ARM like one at EVERY prune site, or
  // the empty-branch delete can't vouch for them (defer loop) and a
  // disk-deferred save resurrects them (round 2, 2026-09-01). Returns
  // the kept list; the sig snapshot keeps a CLI-extended thread alive.
  // EXCEPT a thread that carries REPLIES (round 3): that message became
  // a conversation, and arming its sig would let the next reload drop
  // the CLI's answer silently (the sig-mismatch revival only survives
  // one cycle against a re-prune). It converts to an ordinary comment
  // thread instead — visible in the panel, dismissed by hand.
  const pruneAndArmAddressed = (comments, cur, path) => {
    const all = comments || [];
    const keptByEngine = new Set(track.pruneAddressedMessages(all, cur));
    const kept = [];
    for (const c of all) {
      if (keptByEngine.has(c)) { kept.push(c); continue; }
      if (((c && c.replies) || []).length) {
        const { kind: _k, ...thread } = c;
        kept.push(thread);
        continue;
      }
      resolvedFor(path).comments.set(String(c && c.id), commentSig(c));
    }
    return kept;
  };

  const colorChip = (el, name) => {
    Promise.resolve(resolveColor(name)).then((c) => {
      if (c && c.bg) { el.style.background = c.bg; el.style.color = c.fg || '#fff'; }
    }).catch(() => {});
  };

  const resolveState = diffRewrite.makeStateResolver();
  const applyState = (dot, name) => {
    Promise.resolve(resolveState(name)).then((st) => {
      dot.dataset.tcState = st || '';
      dot.setAttr('title', st ? `${name} — ${st}` : name);
    }).catch(() => {});
  };
  const stateChip = (el, name) => {
    if (!name || name === 'you') return null;
    const dot = el.createSpan({ cls: 'tc-state-chip', attr: { 'data-tc-session': name } });
    applyState(dot, name);
    return dot;
  };
  const typingRow = (el, session) => {
    if (!session || session === 'you') return null;
    const t = el.createDiv({ cls: 'tc-typing', attr: { 'data-tc-session': session } });
    const chip = t.createSpan({ cls: 'tc-message-author tc-attr-chip', text: session });
    colorChip(chip, session);
    const dots = t.createSpan({ cls: 'tc-typing-dots' });
    dots.createSpan({ cls: 'tc-typing-dot' });
    dots.createSpan({ cls: 'tc-typing-dot' });
    dots.createSpan({ cls: 'tc-typing-dot' });
    applyState(t, session);
    return t;
  };

  const getPanel = () => {
    for (const leaf of app.workspace.getLeavesOfType(PANEL_TYPE)) {
      if (leaf.view instanceof TrackPanelView) return leaf.view;
    }
    return null;
  };

  // The editor to read from and dispatch into for `file`.
  //
  // Prefer the FOCUSED leaf. Obsidian mirrors a file's TEXT between panes but
  // nothing mirrors a CodeMirror StateField, so with the same note open twice,
  // always taking the first leaf sent every accept/reject to the other pane: the
  // pane you clicked in kept showing the change, clicking it again found no op
  // (the lookup read the other editor) and did nothing at all, and the untouched
  // pane's field — now describing a change that had already been resolved — is
  // what got persisted if the other pane closed first.
  const viewForFile = (file) => {
    const { MarkdownView } = require('obsidian');
    const activeLeaf = app.workspace.activeLeaf;
    if (activeLeaf && activeLeaf.view instanceof MarkdownView && activeLeaf.view.file === file) {
      return activeLeaf.view;
    }
    let fallback = null;
    for (const leaf of app.workspace.getLeavesOfType('markdown')) {
      const v = leaf.view;
      if (v instanceof MarkdownView && v.file === file) { fallback = fallback || v; }
    }
    return fallback;
  };
  // Embedded editors (embed-edit.js): editable `![[Note]]` embeds
  // mount real editors that belong to no leaf, registered in
  // plugin._embedEditorFiles (cm → embed component). They must resolve
  // to the CHILD file: an unresolved editor hydrates empty, and then a
  // keystroke in an embed of a TRACKED note maps an empty op list and
  // silently drifts the child's sidecar coordinates.
  const embedCompForCm = (view) => {
    const m = plugin._embedEditorFiles;
    return (m && m.get(view)) || null;
  };
  const cmForFile = (file) => {
    const v = viewForFile(file);
    const ed = v && v.editor;
    if (ed) return cmOf(ed);
    const m = plugin._embedEditorFiles;
    if (m) {
      for (const [cm, comp] of m) {
        if (comp && comp.getFile && comp.getFile() === file) return cm;
      }
    }
    return null;
  };
  const fileForCm = (view) => {
    const { MarkdownView } = require('obsidian');
    for (const leaf of app.workspace.getLeavesOfType('markdown')) {
      const v = leaf.view;
      if (v instanceof MarkdownView && v.editor && cmOf(v.editor) === view) return v.file;
    }
    const comp = embedCompForCm(view);
    if (comp && comp.getFile) return comp.getFile() || null;
    return null;
  };
  const currentText = (file) => {
    const v = viewForFile(file);
    if (!v || !v.editor) return null;
    const cm = cmOf(v.editor);
    return cm ? cm.state.doc.toString() : v.editor.getValue();
  };
  const activeMarkdownFile = () => {
    const { MarkdownView } = require('obsidian');
    const v = app.workspace.getActiveViewOfType(MarkdownView);
    return v && v.file ? v.file : null;
  };
  // Live ops for a file: the mounted editor's field is the source of truth (it
  // holds edits not yet flushed to disk); fall back to the cached store.
  const liveOps = (file, fallback) => {
    const cm = cmForFile(file);
    if (cm && suggestionsFieldRef.f) {
      const v = cm.state.field(suggestionsFieldRef.f, false);
      if (v != null) return v;
    }
    return fallback || [];
  };

  // Push the store into the editor showing `file` — a LOAD/SYNC (non-undoable, and
  // skipped by the persist listener). Sets both fields. `_tcHydrated`
  // marks the editor as having received sidecar state at least once —
  // the unhydrated-editor self-heal keys on its absence.
  // `mt` (when the caller measured it): the sidecar generation this
  // dispatch delivers — the non-active persist/mutate paths refuse to
  // trust a field whose stamp lags the disk (round 2, 2026-09-01).
  const syncEditor = (file, store, on, mt) => {
    const cm = cmForFile(file);
    if (!cm) return;
    cm.dispatch({
      effects: [setSuggestions.of(store.suggestions || []), setTrackMeta.of({ trackingOn: on, comments: store.comments || [] })],
      annotations: [Transaction.addToHistory.of(false), syncAnnotation.of(true)],
    });
    cm._tcHydrated = true;
    if (mt !== undefined) cm._tcSidecarMtime = mt;
    stampKnownIds(cm, store);
  };
  // Every id ever pushed into an editor's field — the set that lets a
  // later persist tell "this editor resolved/consumed that op" from
  // "this editor never saw that op" (foreign; must survive the persist).
  const stampKnownIds = (cm, store) => {
    const known = cm._tcKnownIds || (cm._tcKnownIds = new Set());
    for (const o of store.suggestions || []) known.add(String(o && o.id));
    const knownC = cm._tcKnownCommentIds || (cm._tcKnownCommentIds = new Set());
    for (const c of store.comments || []) knownC.add(String(c && c.id));
    // The DISK-generation content of each ingested op (round 4): an arm
    // must snapshot what disk holds, not the live field copy — user
    // typing inside a suggestion diverges the field from disk, and a
    // field-generation snapshot then reads as "CLI revision, keep",
    // resurrecting the user's own resolution.
    const snaps = cm._tcIngestedSnaps || (cm._tcIngestedSnaps = new Map());
    for (const o of store.suggestions || []) snaps.set(String(o && o.id), opSnapshot(o));
  };
  // Push only the meta (comments + trackingOn) — for a comment mutation that didn't
  // touch the ops. Non-undoable, skipped by persist.
  const syncMeta = (file, store, on) => {
    const cm = cmForFile(file);
    if (!cm) return;
    cm.dispatch({
      effects: setTrackMeta.of({ trackingOn: on, comments: store.comments || [] }),
      annotations: [Transaction.addToHistory.of(false), syncAnnotation.of(true)],
    });
  };

  // Switch the tracked context to the active markdown file. When a non-markdown
  // leaf (the panel) is focused, KEEP the current context so the panel doesn't lose
  // its file.
  // SEQUENCED (user report 2026-08-18: the panel showed a file that was
  // no longer being viewed): pushActive spans several awaits, and two
  // rapid leaf switches (A→B→C) could interleave so the EARLIER call
  // finished LAST and repointed `active` back at the old file — which
  // the panel then rendered until the next leaf event. Every await is
  // followed by a generation check; a superseded call simply stops and
  // lets the newest one land. A flush failure logs and continues — it
  // must not strand `active` on the outgoing file.
  let pushActiveGen = 0;
  const pushActive = async () => {
    const gen = ++pushActiveGen;
    const file = activeMarkdownFile();
    // Flush the OUTGOING file before repointing `active` or pushing the on-disk
    // store into an editor. Without this, an accept made in the last 400ms is
    // dropped and then actively undone: the disk store (which still holds the op)
    // is synced back into the field and the next save writes it out again.
    try {
      if (active && active.file) await flushSave();
    } catch (e) { console.error('[track-changents] outgoing flush failed:', e); }
    if (gen !== pushActiveGen) return;
    if (!file) { const p = getPanel(); if (p) p.notifyChanged(); return; }
    const on = track.isTracked(await loadTrackedList(app), file.path);
    if (gen !== pushActiveGen) return;
    plugin._trackEnabled = on;
    // Unwritten resolutions of the OUTGOING file: the flush above defers
    // when a foreign sidecar write is pending, so clearing here would
    // forfeit them (resolved cards return on reopen — review
    // 2026-08-30). Fold them into the outgoing sidecar with a disk
    // read-modify-write, which starts FROM disk and so cannot clobber
    // foreign ops. Same-file re-pushes skip the fold and let the load
    // below filter instead.
    const switching = !active || !active.file || active.file !== file;
    // Fold EVERY file's unwritten resolutions into ITS OWN sidecar when
    // switching (per-file keying, round 3): entries only exist while a
    // save was deferred, and each folds by disk read-modify-write —
    // never through a stale field, never into the wrong file. Failures
    // keep the entry armed; returning to the file re-applies it at load.
    if (switching && pendingByPath.size) {
      for (const path of [...pendingByPath.keys()]) await foldResolvedToDisk(path);
    }
    const cur = currentText(file);
    // Stat BEFORE the read it fences (review 2026-08-30): stat-after-read
    // let a foreign write in the gap poison active.mtime with ITS
    // timestamp while `store` held pre-write content — every later mtime
    // guard then matched and the poll went blind. Honestly-stale is safe:
    // the poll fires one redundant reload at worst.
    const mtimeAtLoad = await storeMtime(app, file);
    let store = await loadStore(app, file, cur);
    if (!store && cur != null) store = await healOrphanStore(app, file, cur);
    if (gen !== pushActiveGen) return;
    if (!store) store = emptyStore(file.path);
    // The incoming file's own still-armed entry (a failed fold, or a
    // same-file re-push) filters what disk says — round 3, variant (a).
    applyPendingResolved(store, pendingByPath.get(file.path));
    if (gen !== pushActiveGen) return;
    active = { file, store, mtime: mtimeAtLoad };
    syncEditor(file, store, on, mtimeAtLoad);
    const p = getPanel(); if (p) p.notifyChanged();
  };

  // Reload the store for the active file from disk (an agent CLI wrote it) and
  // re-push. The note file itself is reloaded by Obsidian's own on-disk sync; here
  // we only re-key the ops/comments. Auto-clears any pending Cmd-M message that a
  // tracked change has now addressed.
  let reloadInFlight = false;
  let reloadRetries = 0;
  const reloadActive = async () => {
    if (!active || !active.file) return;
    if (reloadInFlight) return;   // the 2.5s poll will catch anything missed
    reloadInFlight = true;
    try { await reloadActiveInner(); } finally { reloadInFlight = false; }
  };
  const reloadActiveInner = async () => {
    const file = active.file;
    await flushSave();
    externalReloading = true;
    try {
      // Re-anchor against the note text ON DISK — what the agent CLI just wrote — not
      // the live editor buffer, which lags a disk write by an async tick. Re-anchoring
      // against the stale buffer would fail to locate the fresh op and drop it, after
      // which a transient-empty save deleted the whole sidecar. Fall back to the
      // buffer only if the file can't be read from disk.
      let cur = await readNoteFromDisk(app, file);
      if (cur == null) cur = currentText(file);
      // The ops we are about to push are in DISK coordinates. If the live buffer
      // does not match disk, pushing them puts every marker on the wrong text —
      // and a Reject then dispatches a range computed against the other version,
      // replacing the wrong words (or throwing "Invalid change range", which the
      // guard swallows, so the click just does nothing). Wait and retry instead:
      // either Obsidian's own buffer reload or the user's typing will settle.
      // Bounded: retrying forever would spin at the debounce rate if buffer and
      // disk never converge (e.g. a normalization difference), reading the whole
      // file each pass. After ~8 tries, re-anchor against the BUFFER — anchors
      // make that safe, and it is strictly better than either spinning or
      // pushing disk-coordinate ops into a buffer they don't describe.
      const buf = currentText(file);
      if (cur != null && buf != null && buf !== cur) {
        if (reloadRetries < 8) { reloadRetries++; scheduleReload(); return; }
        cur = buf;
      }
      reloadRetries = 0;
      // Stat BEFORE the read it fences (review 2026-08-30, executed
      // repro): a foreign write between loadStore and a trailing stat
      // used to poison active.mtime while `store` held pre-write
      // content, blinding every later guard. Honestly-stale self-heals.
      const mtimeAtLoad = await storeMtime(app, file);
      let store = await loadStore(app, file, cur);
      if (!store) store = emptyStore(file.path);
      // Deliberate resolutions the debounced save hasn't written yet:
      // drop exactly those (content-matched, split-residual-aware) from
      // what disk says, keep EVERYTHING else — foreign ops included.
      applyPendingResolved(store, pendingByPath.get(file.path));
      if (cur != null && store.comments && store.comments.length) {
        store.comments = pruneAndArmAddressed(store.comments, cur, file.path);
      }
      const on = isEnabled(plugin);
      active = { file, store, mtime: mtimeAtLoad };
      syncEditor(file, store, on, mtimeAtLoad);
      const p = getPanel(); if (p) p.notifyChanged();
      // Persist the filtered state so the resolved ids reach disk and
      // the sets can clear (doSaveInner clears them after a clean write).
      if (!entryEmpty(pendingByPath.get(file.path))) scheduleSave();
    } finally {
      externalReloading = false;
    }
  };

  // A note renamed/moved INSIDE Obsidian: re-key its store to the new path AND
  // carry its tracking scope across.
  //
  // Moving only the sidecar is what this used to do, and it left the note
  // SILENTLY UNTRACKED: `config.json` still named the old path, so `isTracked`
  // said no and subsequent edits landed in the prose as plain text instead of
  // suggestions. Nothing warned — the failure only surfaced because an agent's
  // next write failed on the old path. For a feature whose whole promise is that
  // nothing changes the document without appearing as a suggestion, silently
  // switching itself off is the worst way to fail, so the scope list moves here
  // together with the store and neither half can be forgotten alone.
  const rekeyStoreOnRename = async (file, oldPath) => {
    const adapter = app.vault.adapter;
    const { TFolder } = require('obsidian');
    // Armed-but-unwritten resolutions are keyed by PATH — rekey them
    // FIRST (round 4, 2026-08-31: Obsidian mutates TFile.path before
    // firing rename, so the flush below already runs under the new
    // path; an entry left under the old key resurrects the resolution
    // and is later dropped as a vanished file). Folder renames move
    // every entry under the prefix; on collision the old entry's
    // snapshots win (they are the older, still-unwritten intent).
    const rekeyPending = (fromPath, toPath) => {
      const moves = [];
      for (const key of pendingByPath.keys()) {
        if (key === fromPath) moves.push([key, toPath]);
        else if (key.startsWith(fromPath + '/')) moves.push([key, toPath + key.slice(fromPath.length)]);
      }
      for (const [from, to] of moves) {
        const e = pendingByPath.get(from);
        pendingByPath.delete(from);
        if (entryEmpty(e)) continue;
        const existing = pendingByPath.get(to);
        if (!existing) { pendingByPath.set(to, e); continue; }
        for (const k of ['ops', 'detached', 'comments']) {
          for (const [id, snap] of e[k]) existing[k].set(id, snap);
        }
      }
    };
    try { rekeyPending(oldPath, file.path); } catch (e) { /* best effort */ }
    // A pending save still targets the OLD key. Flush before re-keying the
    // SIDECAR, or the debounce fires mid-rename and the stale sidecar is
    // copied over the fresh one — resurrecting a change just accepted.
    await flushSave();
    const moveOne = async (oldRel, newRel) => {
      const oldKey = storePathFor(oldRel);
      if (oldKey === CONFIG_PATH) return;   // never move the scope list (see below)
      try { if (!(await adapter.exists(oldKey))) return; } catch (e) { return; }
      let obj;
      try { obj = JSON.parse(await adapter.read(oldKey)); } catch (e) { return; }
      obj.path = newRel;
      await ensureStoreDir(adapter);
      const newKey = storePathFor(newRel);
      if (newKey === CONFIG_PATH) return;
      // Refuse to overwrite a sidecar that still holds unreviewed work. This is
      // reachable: `pruneStoreOnDelete` deliberately KEEPS a deleted note's
      // sidecar when it has pending suggestions, so deleting B.md and then
      // renaming A.md → B.md used to destroy exactly the work that handler went
      // out of its way to preserve. Park it instead of losing it.
      if (newKey !== oldKey) {
        let occupied = null;
        try {
          if (await adapter.exists(newKey)) occupied = JSON.parse(await adapter.read(newKey));
        } catch (e) { occupied = { unreadable: true }; }
        const pending = occupied && (occupied.unreadable
          || ((occupied.suggestions || []).length + (occupied.comments || []).length
            + (occupied.detached || []).length) > 0);
        if (pending) {
          const parked = `${newKey}.superseded-${Date.now()}`;
          try { await adapter.write(parked, JSON.stringify(occupied, null, 2)); } catch (e) { return; }
          console.warn(`[track-changents] ${newRel} already had a sidecar with unreviewed `
            + `changes; parked it at ${parked} rather than overwriting.`);
        }
      }
      await adapter.write(newKey, JSON.stringify(obj, null, 2));
      if (newKey !== oldKey) {
        // Retire the old key by atomic RENAME, not remove (round 2,
        // 2026-09-01): a CLI write landing between the read above and
        // this point survives in the park by construction — this was
        // the last destructive removal in the protocol that bypassed
        // deleteStore's park. Byte-identical park (nothing foreign
        // landed) is deleted to avoid churn.
        const park = `${oldKey}.superseded-${Date.now()}`;
        try {
          await adapter.rename(oldKey, park);
          let same = false;
          try {
            const p2 = JSON.parse(await adapter.read(park));
            // obj was parsed from these same bytes (then re-pathed), so
            // key order matches; any difference means a concurrent
            // writer landed mid-rename. A false negative just keeps the
            // park — safe.
            same = JSON.stringify({ ...p2, path: oldRel })
              === JSON.stringify({ ...obj, path: oldRel });
          } catch (e) { same = false; }
          if (same) {
            try { await adapter.remove(park); } catch (e) { /* keep it */ }
          } else {
            console.warn(`[track-changents] ${oldRel}: concurrent sidecar write during rename — parked at ${park}`);
            try {
              new (require('obsidian').Notice)(
                `Track changes: parked concurrent suggestions on ${oldRel} (recoverable in .trackchanges).`, 8000);
            } catch (e) { /* headless */ }
          }
        } catch (e) { /* rename failed — old key stays, better than loss */ }
      }
    };
    try {
      if (file instanceof TFolder) {
        let listing; try { listing = await adapter.list(STORE_DIR); } catch (e) { return; }
        const head = STORE_DIR + '/';
        const prefix = oldPath + '/';
        for (const f of ((listing && listing.files) || [])) {
          // `config.json` is the SCOPE LIST, not a note's sidecar, and it decodes
          // to the vault-relative name `config` — so a folder (or extensionless
          // file) called `config` at the vault root matched it here and the rename
          // carried the tracking config away, silently untracking every file in
          // the vault. The other two loops over this directory already skip it.
          if (!f.endsWith('.json') || f === CONFIG_PATH) continue;
          let rel; try { rel = decodeURIComponent(f.slice(head.length, -('.json'.length))); } catch (e) { continue; }
          if (rel === oldPath || rel.startsWith(prefix)) await moveOne(rel, file.path + rel.slice(oldPath.length));
        }
      } else {
        await moveOne(oldPath, file.path);
      }
      // The scope list, which is the half that decides whether tracking is ON.
      try {
        const list = await loadTrackedList(app);
        const next = track.renameTracked(list, oldPath, file.path, file instanceof TFolder);
        if (JSON.stringify(next) !== JSON.stringify(list)) {
          await saveTrackedList(app, next);
          void applyTrackedBadges();
          if (active && active.file) plugin._trackEnabled = track.isTracked(next, active.file.path);
        }
      } catch (e) { /* best effort */ }
      if (active && active.file && active.file.path === file.path) await reloadActive();
    } catch (e) { /* best effort */ }
  };

  // A tracked note deleted INSIDE Obsidian: drop its scope entry so the list does
  // not accumulate paths that no longer exist.
  //
  // The sidecar is only removed when it holds NOTHING PENDING. Obsidian deletes
  // to the system trash, so restoring a note is an ordinary thing to do — and
  // discarding someone's un-reviewed suggestions on a delete they can undo would
  // be the same silent loss of work this whole handler exists to prevent. An
  // orphan sidecar with real content costs a few KB and can be re-armed; deleted
  // suggestions cannot be got back.
  const pruneStoreOnDelete = async (file) => {
    const adapter = app.vault.adapter;
    const { TFolder } = require('obsidian');
    const isFolder = file instanceof TFolder;
    const dropSidecar = async (rel) => {
      const key = storePathFor(rel);
      try { if (!(await adapter.exists(key))) return; } catch (e) { return; }
      try {
        const obj = JSON.parse(await adapter.read(key));
        const pending = ((obj && obj.suggestions) || []).length
          + ((obj && obj.comments) || []).length
          + ((obj && obj.detached) || []).length;
        if (pending > 0) return;                       // keep: unreviewed work
      } catch (e) { return; }                          // unreadable: keep, don't guess
      try { await adapter.remove(key); } catch (e) { /* ignore */ }
    };
    try {
      if (isFolder) {
        let listing; try { listing = await adapter.list(STORE_DIR); } catch (e) { listing = null; }
        const head = STORE_DIR + '/';
        const prefix = file.path + '/';
        for (const f of ((listing && listing.files) || [])) {
          if (!f.endsWith('.json') || f === CONFIG_PATH) continue;
          let rel; try { rel = decodeURIComponent(f.slice(head.length, -('.json'.length))); } catch (e) { continue; }
          if (rel === file.path || rel.startsWith(prefix)) await dropSidecar(rel);
        }
      } else {
        await dropSidecar(file.path);
      }
      // Keep the scope entry for anything whose sidecar we just PRESERVED. The
      // two halves of this handler used to disagree: the sidecar was kept when it
      // held unreviewed work, but the scope entry was pruned unconditionally — so
      // restoring the note from the system trash brought the suggestions back
      // with tracking silently OFF, and the next agent edit landed as plain
      // prose. Silently switching tracking off is the worst failure this feature
      // has, so it must not be a side effect of a delete the user may undo.
      const stillHasSidecar = async (rel) => {
        try { return await adapter.exists(storePathFor(rel)); } catch (e) { return false; }
      };
      const list = await loadTrackedList(app);
      const pruned = track.pruneTracked(list, file.path, isFolder);
      const next = [];
      for (const entry of list) {
        if (pruned.includes(entry)) { next.push(entry); continue; }
        if (!entry.endsWith('/') && await stillHasSidecar(entry)) next.push(entry);
      }
      if (JSON.stringify(next) !== JSON.stringify(list)) {
        await saveTrackedList(app, next);
        void applyTrackedBadges();
      }
    } catch (e) { /* best effort */ }
  };

  // Persist the current ops+comments for the active file, debounced. Reads the ops
  // straight from the editor field (the live truth), prunes orphaned/addressed
  // comments, then writes (or deletes) the sidecar. No blocking popups.
  // Re-entrancy latch. doSave can reach reloadActive (stale-sidecar branch), and
  // reloadActive flushes pending saves — i.e. calls doSave — before it re-reads
  // disk. Without this latch that pair is UNBOUNDED MUTUAL RECURSION: nothing in
  // the cycle updates active.mtime (the code that would sits after the flush), so
  // the guard condition held forever, every pending frame pinned a full copy of
  // the document, and the renderer died on V8's fatal-OOM CHECK about two minutes
  // after load — the 2026-08-04 crash loop that took out every vault. With the
  // latch, the inner doSave is a no-op and the cycle terminates.
  let saveInFlight = false;
  const doSave = async () => {
    if (saveInFlight) return;
    saveInFlight = true;
    try { await doSaveInner(); } finally { saveInFlight = false; }
  };
  const doSaveInner = async () => {
    if (!active || !active.file) return;
    const file = active.file;
    const cur = currentText(file);
    if (cur == null) return;
    const ops = liveOps(file, active.store.suggestions);
    let comments = active.store.comments || [];
    comments = pruneAndArmAddressed(comments, cur, file.path);
    // DON'T hard-delete a thread whose anchor we merely failed to place. Comments
    // live only in the store, never in the CodeMirror field, so they are not in
    // undo history: retyping a paragraph used to destroy the conversation
    // attached to it and ⌘Z brought back the text but not the discussion. Mark it
    // detached instead — the panel already has a label for that state — so the
    // replies survive and can re-attach if the text comes back.
    const placeable = new Set(track.pruneOrphanedComments(comments, cur));
    comments = comments.map((c) => {
      if (placeable.has(c)) return c.detached ? { ...c, detached: false } : c;
      return c.detached ? c : { ...c, detached: true };
    });
    active.store.suggestions = ops;
    active.store.comments = comments;
    try {
      if (ops.length === 0 && comments.length === 0
          && !(active.store.detached || []).length) {
        // Never delete a sidecar an external tool (an agent CLI) wrote AFTER our last
        // sync: an empty field here is a transient reload artifact, not the user
        // having accepted the last suggestion. Reload it instead of erasing it.
        const mt = await storeMtime(app, file);
        // Schedule, never await, the reload from inside a save: awaiting it here
        // was one half of the recursion described above, and the debounce also
        // lets Obsidian's own buffer reload land first.
        // A deliberate resolution survives the defer through
        // the file's pendingByPath entry — the reload filters those ids from disk (no
        // ghost cards, 2026-08-18) without this path ever overwriting a
        // foreign write (2026-08-30).
        if (mt && mt !== (active.mtime || 0)) { scheduleReload(); return; }
        // mt=0 with a NONZERO active.mtime means a sidecar we loaded was
        // foreign-deleted (our own delete zeroes it synchronously) —
        // defer to the reload rather than acting on a phantom.
        if (!mt && (active.mtime || 0)) { scheduleReload(); return; }
        // Same last-moment narrowing as the write branch, and the delete
        // itself verifies the mtime right before removal (its park/read
        // sequence spans several awaits — review 2026-08-30).
        const mt2 = await storeMtime(app, file);
        if (mt2 !== mt) { scheduleReload(); return; }
        const entryDel = pendingByPath.get(file.path);
        const armed = armSnapshot(entryDel);
        // The delete may only take ids the user demonstrably resolved
        // (the armed entry); anything else on disk defers to the reload.
        const vouchDel = new Set([...armed.ops, ...armed.detached, ...armed.comments]);
        if (!(await deleteStore(app, file, mt2, vouchDel))) { scheduleReload(); return; }
        disarm(entryDel, armed);
        pruneEntry(file.path);
        active.mtime = 0;
      } else {
        // The SAME external-write guard as the empty branch, for the same reason.
        // When an agent CLI writes the sidecar while the note is open, Obsidian's
        // buffer refresh reaches the CM field as an ordinary doc change and is
        // folded through ingestHumanChanges — which correctly mangles the ops it
        // KNOWS about (the agent's replaced span becomes an orphan del) and knows
        // nothing of the op the CLI just recorded. Blind-writing here persisted
        // that mangled field over the CLI's correct sidecar — the flush at the
        // top of reloadActive made it deterministic — so the agent's insertion
        // became untracked plain text with a struck-through removal beside it
        // (hit in the vault 2026-08-04 18:25). Defer to disk instead: the reload
        // re-anchors the CLI's ops against the new text and replaces the field.
        // ...but never at the cost of a resolution the user actually made: an
        // accept is text-unchanged, so it exists ONLY in the field and deferring
        // it to a reload would silently un-accept it. Disk wins for folded doc
        // changes; the user's own accept/reject wins over disk.
        const mt = await storeMtime(app, file);
        if (mt && mt !== (active.mtime || 0)) { scheduleReload(); return; }
        if (!mt && (active.mtime || 0)) { scheduleReload(); return; }   // foreign delete
        // Re-stat at the last moment; saveStore itself re-checks this
        // expectation right before its write (its park block spans
        // several awaits — review round 2) and returns null to defer.
        const mt2 = await storeMtime(app, file);
        if (mt2 !== mt) { scheduleReload(); return; }
        const entryW = pendingByPath.get(file.path);
        const armed = armSnapshot(entryW);
        const armedIds = new Set([...armed.ops, ...armed.detached, ...armed.comments]);
        const payload = await saveStore(app, file, active.store, cur,
          { expectedMtime: mt2, resolvedIds: armedIds });
        if (payload == null) { scheduleReload(); return; }
        // Adopt the post-write mtime only when the bytes on disk are OURS
        // — a foreign write inside the save window otherwise gets its
        // mtime absorbed and the poll goes permanently blind (review
        // 2026-08-30, executed repro). Stat first, then read back: a
        // write after the stat shows as foreign bytes; a write after the
        // read-back leaves the adopted mtime honestly stale.
        const post = await storeMtime(app, file);
        let ours = false;
        try { ours = (await app.vault.adapter.read(storePath(file))) === payload; } catch (e) { ours = false; }
        if (!ours) { scheduleReload(); return; }
        disarm(entryW, armed);
        pruneEntry(file.path);
        active.mtime = post;
      }
    } catch (e) { console.error('[track-changents] save failed:', e); }
    const p = getPanel(); if (p) p.notifyChanged();
  };
  const scheduleSave = debounce(() => { void doSave(); }, SAVE_DEBOUNCE_MS, false);

  // Persist NOW, before the active context changes under us.
  //
  // Accepting is a text-unchanged operation by design — the engine just drops the
  // op — so the ONLY record of an accept is the debounced sidecar write. `doSave`
  // reads the editor at fire time and bails when the file no longer has one, so
  // closing the note (or switching tabs) inside the debounce window silently threw
  // the accept away: reloading found the suggestion's text still in place and
  // restored the op verbatim. Anything that repoints `active` or re-reads from
  // disk must therefore flush first.
  const flushSave = async () => {
    if (!active || !active.file) return;
    try { scheduleSave.cancel(); } catch (e) { /* older debounce impls */ }
    await doSave();
  };
  // Coalesce external-write reloads; the delay lets Obsidian's own buffer reload land
  // first so reloadActive re-anchors against a buffer that already matches disk.
  const scheduleReload = debounce(() => { void reloadActive(); }, RELOAD_DEBOUNCE_MS, false);

  // A comment-only mutation (reply/resolve/new comment/message): re-push meta so the
  // highlights update, refresh the panel, and persist.
  const commitComments = async (file) => {
    const on = (active && active.file === file) ? isEnabled(plugin) : await isFileTracked(app, file);
    if (active && active.file === file) syncMeta(file, active.store, on);
    const p = getPanel(); if (p) p.notifyChanged();
    scheduleSave();
  };

  const guard = (label, fn) => async (...args) => {
    try { await fn(...args); } catch (e) {
      // No blocking Notice — surface to console only (a popup over the panel
      // controls was the "the click gets eaten" bug).
      console.error(`[track-changents] ${label} failed:`, e);
    }
  };

  const openPanel = async () => {
    try {
      if (!active || !active.file) await pushActive();
      const existing = app.workspace.getLeavesOfType(PANEL_TYPE);
      if (existing.length) {
        await app.workspace.revealLeaf(existing[0]);
        const v = getPanel(); if (v) v.notifyChanged();
        return;
      }
      let leaf = app.workspace.getRightLeaf(false);
      if (!leaf) leaf = app.workspace.getLeaf(true);
      if (!leaf) return;
      await leaf.setViewState({ type: PANEL_TYPE, active: true });
      await app.workspace.revealLeaf(leaf);
      const v = getPanel(); if (v) v.notifyChanged();
    } catch (e) {
      console.error('[track-changents] openPanel failed:', e);
    }
  };

  const reveal = (offset) => {
    const cm = active && active.file ? cmForFile(active.file) : null;
    if (!cm) return;
    const off = Math.min(offset, cm.state.doc.length);
    cm.dispatch({ selection: { anchor: off }, effects: EditorView.scrollIntoView(off, { y: 'center' }) });
    cm.focus();
  };

  // Map a display-hunk position (curFrom) to the op ids it covers: recompute the
  // display hunks, find the one at curFrom, then every op whose `from` sits within
  // [curFrom, curTo] (a collapsed paragraph card spans several ops; a normal card
  // is one).
  const idsAtPosition = (ops, current, curFrom) => {
    const hunks = logic.planDiffDisplay(track.toHunks(ops), track.baselineOf(current, ops), current);
    const h = hunks.find((x) => x.curFrom === curFrom);
    if (!h) return [];
    // Use the display layer's own answer for "which ops does this card stand
    // for" — `idsOf` exists for exactly this and a merged paragraph card already
    // carries its covered set. Re-deriving it positionally with INCLUSIVE bounds
    // swept in any zero-width op sitting at the hunk's end: with two agents on
    // one note, accepting one author's substitution also accepted the other
    // author's deletion at that boundary, applying it permanently and removing
    // its card unreviewed.
    return logic.idsOf(h);
  };

  // `inFile` — the note the thread lives in. Defaults to the active
  // note; the panel's closure-section replies MUST pass their own file
  // or the agent is instructed to answer in the parent's sidecar, where
  // the thread id doesn't exist (review 2026-08-18).
  const pingAgent = async (sessName, threadId, changeDesc, message, inFile) => {
    const file = inFile || (active && active.file);
    if (!sessName || !file) return;
    try { await diffRewrite.pingThreadReply(plugin, sessName, file, threadId, changeDesc, message); } catch (e) { /* best effort */ }
  };

  // Drop a change-thread once its change is accepted/rejected: match by the
  // resolved op id (its `suggestionId`), the key the thread was created with.
  const dropResolvedThreads = (file, ids) => {
    if (!active || active.file !== file || !active.store.comments || !active.store.comments.length) return;
    const idset = new Set(ids);
    const before = active.store.comments.length;
    active.store.comments = active.store.comments.filter((c) => {
      const drop = c && c.suggestionId != null && idset.has(c.suggestionId);
      // Deliberate removal — survives a disk-deferred save (2026-08-30);
      // signature keeps a CLI-extended thread alive (round 2).
      if (drop) resolvedFor(file.path).comments.set(String(c.id), commentSig(c));
      return !drop;
    });
    if (active.store.comments.length !== before) void commitComments(file);
  };

  // Persist a NON-ACTIVE file's sidecar straight from its editor's field
  // state. Embed editors are the case: onOpsChanged only mirrors the
  // ACTIVE file's store, so an accept/reject inside an embedded note
  // would render correctly and then vanish on reload. Comments ride in
  // the meta field; threads of the resolved changes are dropped by
  // suggestionId, mirroring dropResolvedThreads for the active store.
  // Sidecar mtime each path last synced into mounted editors (shared
  // with the resync watcher below) — deleting a path's entry wakes the
  // watcher for it.
  const embedSyncSeen = new Map();   // path → sidecar mtime last synced
  // Paths with a persist mid-flight (not just a timer pending): the
  // watcher must not dispatch into a field a persist is reading (round
  // 2, 2026-09-01 — the timer used to delete its map entry before the
  // async body ran, blinding the guard for the whole persist).
  const nonActivePersisting = new Set();
  // Gate-deferred persists WAITING on the watcher (round 3, 2026-09-01,
  // critical): the generation gate must NOT self-reschedule — the timer
  // it re-arms is exactly what skipBusy keys on, so the watcher could
  // never service the file and the defer looped forever. The gate parks
  // the intent here instead; the watcher re-schedules after it has
  // converged the file (one-way handoff, no circular wait).
  const persistAfterResync = new Set();

  // {id, snap} pairs for persistNonActiveStore's arming. The snapshot
  // preference order (round 4): the DISK generation the editor last
  // ingested (cm._tcIngestedSnaps — what applyPendingResolved will
  // actually compare against), then the pre-dispatch field copy the
  // call site holds (round 3 — for in-editor splits disk never saw),
  // then null.
  const resolvedPairs = (ids, ops, cm) => (ids || []).map((id) => {
    const key = String(id);
    const ingested = cm && cm._tcIngestedSnaps && cm._tcIngestedSnaps.get(key);
    if (ingested) return { id: key, snap: ingested };
    const o = (ops || []).find((x) => String(x && x.id) === key);
    return { id: key, snap: o ? opSnapshot(o) : null };
  });

  const persistNonActiveStore = async (file, cm, resolvedIds) => {
    // Mark the persist busy HERE, not only in the scheduler (round 3):
    // the direct call sites (panel resolves, accept/reject-all) were
    // invisible to the watcher's skipBusy, which could then dispatch a
    // stale snapshot into the field mid-persist.
    nonActivePersisting.add(file.path);
    try {
      // An editor that never received sidecar state has a meaningless []
      // field; persisting it wholesale is the clobber class of 2026-09-01
      // (a CLI-written store replaced by an unhydrated embed's emptiness).
      if (!cm._tcHydrated) return;
      // Durable arming (round 2, 2026-09-01): a non-active resolution
      // used to exist only in THIS call's resolvedIds — every deferral
      // retried with [] and the accepted op resurrected, or demoted to
      // a false "superseded by your edit" ghost. Arm into the file's
      // pendingByPath entry; the working idset is the armed UNION, so
      // retries and sibling-editor persists all keep honoring it.
      // resolvedIds entries may be bare ids or {id, snap} pairs — the
      // call sites snapshot the op AS THE USER SAW IT (round 3): a null
      // arm is match-any, and a gate-deferred null reaching the
      // pushActive fold silently killed same-id CLI revisions.
      const ridOf = (r) => String(r && r.id !== undefined ? r.id : r);
      if (resolvedIds && resolvedIds.length) {
        const e0 = resolvedFor(file.path);
        for (const r of resolvedIds) {
          const id = ridOf(r);
          const snap = (r && r.id !== undefined && r.snap) ? r.snap : null;
          if (!e0.ops.has(id)) e0.ops.set(id, snap);
        }
      }
      const entry = pendingByPath.get(file.path);
      const armed = armSnapshot(entry);
      const idset = new Set([...(resolvedIds || []).map(ridOf),
        ...armed.ops, ...armed.detached, ...armed.comments]);
      const baseOf = (id) => String(id).replace(/([~#]p?\d+)+$/, '');
      const cur = cm.state.doc.toString();
      const rawFieldOps = suggestionsFieldRef.f
        ? (cm.state.field(suggestionsFieldRef.f, false) || []) : [];
      // A sibling editor's field may still hold an op resolved through
      // another editor — armed ids never re-enter from a field (C2).
      const ops = rawFieldOps.filter((o) => {
        const id = String(o && o.id);
        return !idset.has(id) && !idset.has(baseOf(id));
      });
      const meta = metaFieldRef.f ? cm.state.field(metaFieldRef.f, false) : null;
      // Stat BEFORE the read it fences (the 2026-08-30 rule) — the write
      // at the bottom passes this as its expectation.
      const mtimeAtLoad = await storeMtime(app, file);
      // GENERATION GATE (round 2, 2026-09-01): "absent from the field"
      // only means "consumed or resolved in this editor" when the field
      // ingested the sidecar generation on disk. A CLI write since the
      // last sync (new op, split fragment, same-id revision, or a
      // foreign DELETE of the whole store) makes field-absence
      // meaningless — let the watcher resync this file, then retry.
      if (mtimeAtLoad !== (cm._tcSidecarMtime || 0)) {
        embedSyncSeen.delete(file.path);
        // Hand the retry to the WATCHER (round 3): a self-reschedule
        // kept the path in the busy set the watcher skips — circular
        // wait, unbounded 2.5s defers. The armed entry above already
        // carries any resolution durably across the handoff.
        persistAfterResync.add(file.path);
        return;
      }
      const loadedStore = await loadStore(app, file, cur);
      const store = loadedStore || emptyStore(file.path);
      // Upgrade null-armed snapshots from the disk copy, then filter the
      // armed resolutions out of disk state — a deliberate drop must not
      // read as foreign or ghost below, while a same-id CLI revision
      // (snapshot mismatch) survives applyPendingResolved and merges.
      if (entry) {
        for (const k of ['suggestions', 'detached']) {
          for (const x of store[k] || []) {
            const id = String(x && x.id);
            const bucket = k === 'suggestions' ? entry.ops : entry.detached;
            if (bucket.has(id) && bucket.get(id) == null) bucket.set(id, opSnapshot(x));
          }
        }
        applyPendingResolved(store, entry);
      }
      // Which disk entries does this FIELD account for? Every id ever
      // pushed into it (hydrations/resyncs) plus what it holds now;
      // lineage counts BOTH ways — a fragment (`id~n`/`id#pN`) through
      // its base, and a base through a known fragment. Anything else is
      // a foreign write this editor never saw and must SURVIVE the
      // persist, not be parked (incident 2026-09-01: embed persists
      // shredded a CLI batch one op per cycle, 11 ops lost on one note).
      const known = new Set(cm._tcKnownIds ? [...cm._tcKnownIds] : []);
      for (const o of rawFieldOps) known.add(String(o && o.id));
      const knownAncestors = new Set();
      for (const k of known) {
        let curId = String(k); let next;
        while ((next = curId.replace(/[~#]p?\d+$/, '')) !== curId) { knownAncestors.add(next); curId = next; }
      }
      const accounted = (id) => known.has(id) || known.has(baseOf(id))
        || knownAncestors.has(id)
        || idset.has(id) || idset.has(baseOf(id));
      const foreignSugg = (store.suggestions || []).filter((x) => !accounted(String(x && x.id)));
      const foreignDet = (store.detached || []).filter((x) => !accounted(String(x && x.id)));
      const droppedCommentIds = new Set();
      const fieldComments = ((meta && meta.comments) || []).filter((c) => {
        const drop = c && c.suggestionId != null && idset.has(String(c.suggestionId));
        if (drop) droppedCommentIds.add(String(c.id));
        return !drop;
      });
      // Foreign comments survive too, and for a SHARED thread the copy
      // with more replies wins — a CLI-appended reply must not be
      // rolled back by a stale meta field.
      const knownC = new Set(cm._tcKnownCommentIds ? [...cm._tcKnownCommentIds] : []);
      for (const c of (meta && meta.comments) || []) knownC.add(String(c && c.id));
      const diskComments = new Map((store.comments || []).map((c) => [String(c && c.id), c]));
      const comments = fieldComments.map((c) => {
        const disk = diskComments.get(String(c && c.id));
        return (disk && ((disk.replies || []).length > ((c && c.replies) || []).length)) ? disk : c;
      });
      for (const c of store.comments || []) {
        const id = String(c && c.id);
        if (!knownC.has(id) && !idset.has(id)) comments.push(c);
        else if (!comments.some((x) => String(x && x.id) === id)) droppedCommentIds.add(id);
      }
      // Same supersede ghosts as the active path (2026-09-01): ops the
      // embed's field lost WHOLE to user typing — deliberate embed
      // resolutions (idset) and foreign ops (merged back below, not
      // gone) excluded.
      {
        const prev = (store.suggestions || []).filter((x) => {
          const id = String(x && x.id);
          return !idset.has(id) && accounted(id);
        });
        const gone = track.supersededOps(prev, ops);
        if (gone.length) {
          const det = store.detached = store.detached || [];
          const now = Date.now();
          for (const g of gone) {
            if (!det.some((d) => String(d && d.id) === String(g.id))) {
              det.push({ ...g, detached: true, superseded: 'user-edit', supersededTs: now });
            }
          }
        }
      }
      store.suggestions = ops.concat(foreignSugg);
      store.comments = comments;
      // GHOST GUARD (verify pass 2026-08-18): `cur` is POST-resolution
      // text, so loading rebases the lagging disk sidecar against text
      // the just-resolved op no longer matches — detaching it as a
      // permanent stale card of the change the user just accepted or
      // rejected. The FIELD is authoritative here: an op absent from it
      // was resolved, not orphaned. Keep only detached entries that were
      // already detached ON DISK (true out-of-band orphans).
      try {
        const rawStore = JSON.parse(await app.vault.adapter.read(storePath(file)));
        const prior = new Set(((rawStore.detached) || []).map((d) => d && d.id));
        // Split residuals (id `…#pN`, review 2026-08-26) are freshly minted
        // from an op that WAS on disk — the parent id vouches for them, or
        // this guard would erase the record the split just preserved.
        const priorSugg = new Set(((rawStore.suggestions) || []).map((x) => x && x.id));
        const parentOf = (id) => String(id || '').replace(/#p\d+$/, '');
        store.detached = (store.detached || []).filter((d) => d && (prior.has(d.id)
          || (d.superseded === 'user-edit' && priorSugg.has(d.id))
          || (/#p\d+$/.test(String(d.id))
            && (priorSugg.has(parentOf(d.id)) || prior.has(parentOf(d.id))))));
      } catch (e) { store.detached = []; }   // no prior sidecar → nothing was orphaned
      // Foreign detached entries (load-time rebase of an op this field
      // never saw) fail every guard clause above by construction — put
      // them back; they are records of someone else's pending work.
      for (const d of foreignDet) {
        if (!(store.detached || []).some((x) => String(x && x.id) === String(d && d.id))) {
          (store.detached = store.detached || []).push(d);
        }
      }
      const empty = !(store.suggestions || []).length
        && !(store.comments || []).length && !(store.detached || []).length;
      if (empty) {
        // Everything the field accounted for was deliberately resolved
        // — anything else would have merged back in. Delete the emptied
        // store (vouched + fenced) instead of writing {[],[],[]} junk;
        // with nothing loaded there is nothing to do at all. A refused
        // delete RETRIES (round 2: swallowing the false dropped the
        // resolution on the floor and the watcher un-accepted it on
        // screen); success disarms.
        if (loadedStore) {
          const vouch = new Set([...idset, ...droppedCommentIds]);
          if (await deleteStore(app, file, mtimeAtLoad, vouch)) {
            disarm(entry, armed); pruneEntry(file.path);
            cm._tcSidecarMtime = 0;
          } else {
            embedSyncSeen.delete(file.path);
            scheduleNonActivePersist(file);
          }
        } else {
          disarm(entry, armed); pruneEntry(file.path);
        }
        return;
      }
      const written = await saveStore(app, file, store, cur,
        { expectedMtime: mtimeAtLoad, resolvedIds: idset });
      // A foreign write landed mid-persist: retry from fresh disk bytes
      // via the debounced scheduler (it re-checks buffer/disk parity).
      // The armed entry keeps the resolution across the retry.
      if (written == null) { scheduleNonActivePersist(file); return; }
      disarm(entry, armed); pruneEntry(file.path);
      cm._tcSidecarMtime = await storeMtime(app, file);
      stampKnownIds(cm, store);
    } catch (e) { console.error('[track-changents] embed sidecar persist failed:', e); }
    finally { nonActivePersisting.delete(file.path); }
  };

  // Ordinary KEYSTROKES in an embed editor change ops with no persist
  // path at all: onOpsChanged mirrors only the ACTIVE file's store, so
  // the child's sidecar went stale against the embed component's own
  // autosave — and the next load rebased the stale ops against strange
  // text, where the ghost guard (rightly distrusting freshly-detached
  // ops) erased the record entirely (peer report 2026-08-26: a
  // whole-file suggestion deleted through an embed left a 0-byte note
  // and a vanished sidecar). Debounced per file; waits out the embed
  // component's save so the persisted fingerprint describes DISK text;
  // gives up when the editor unmounts (disk owns it again) or the file
  // becomes active (the active save path owns it).
  const nonActiveTimers = new Map(); // path → timeout id
  const scheduleNonActivePersist = (file) => {
    const prev = nonActiveTimers.get(file.path);
    if (prev) clearTimeout(prev);
    const arm = (delay, tries) => {
      nonActiveTimers.set(file.path, setTimeout(async () => {
        nonActiveTimers.delete(file.path);
        // The set marks the persist for its WHOLE async duration — the
        // timer map alone blinded the resync watcher mid-persist
        // (round 2, 2026-09-01).
        nonActivePersisting.add(file.path);
        try {
          if (active && active.file === file) return;
          const cm = cmForFile(file);
          if (!cm || !cm.dom || !cm.dom.isConnected) return;
          if (!(await bufferMatchesDisk(file, cm))) {
            if (tries < 8) arm(1500, tries + 1);
            return;
          }
          await persistNonActiveStore(file, cm, []);
        } catch (e) { console.error('[track-changents] embed ops persist failed:', e); }
        finally { nonActivePersisting.delete(file.path); }
      }, delay));
    };
    arm(2500, 0);
  };

  // ── Staleness gates for panel-driven mutations of NON-ACTIVE notes
  // (review 2026-08-18). The active file has reload machinery (mtime
  // poll, externalReloading); closure notes have none, so every write
  // here must verify the state it's about to replace is the state it
  // derived from — an agent CLI may have written the note or sidecar in
  // between (the 2026-08-04 doSave incident class). On any mismatch:
  // abort, warn, refresh — an aborted click is recoverable, a clobbered
  // suggestion is not.
  const diskTextOf = async (file) => {
    try { return await app.vault.adapter.read(file.path); } catch (e) { return null; }
  };
  // For a note with a live embed editor: only trust the editor's field
  // state when its buffer matches disk. A lagging buffer (external write
  // not yet ingested) or a leading one (unsaved keystrokes) means field-
  // derived ops may not describe what's on disk — retry in a beat.
  const bufferMatchesDisk = async (file, cm, opts) => {
    const disk = await diskTextOf(file);
    if (disk != null && cm.state.doc.toString() === disk) return true;
    // The resync watcher polls this on a bounded retry — per-tick warns
    // for a known-divergent buffer are noise (round 2, 2026-09-01).
    if (!(opts && opts.quiet)) {
      console.warn(`[track-changents] ${file.path}: editor buffer and disk differ — action skipped, retry in a moment`);
    }
    return false;
  };

  // Load a closure note's store keyed to its CURRENT text (live editor
  // when one is mounted — an embed editor's field holds unsaved
  // resolutions — else disk), let `fn` mutate it, write it back, and
  // push the new meta into any live editor so inline comment marks
  // follow. The panel's whole-tree review mutates non-active notes
  // exclusively through this.
  // Returns true when the mutation reached disk (or was a clean no-op),
  // false when it was skipped — callers relying on the write (the
  // pushActive fold) must not treat a silent skip as success (review
  // round 2, 2026-08-30). opts.diskOnly bypasses the trustField path:
  // a fold must start FROM DISK — a mounted editor's field predates a
  // CLI sidecar-only write (buffer===disk holds by construction then)
  // and trusting it silently drops the foreign op.
  const mutateStoreInFile = async (file, fn, opts) => {
    const cm = (opts && opts.diskOnly) ? null : cmForFile(file);
    const mtimeAtLoad = await storeMtime(app, file);
    // An UNHYDRATED editor's field is [] (its create() value) and its
    // buffer matches disk, so text equality can't catch it — the field
    // of an editor that never received sidecar state is meaningless
    // (review 2026-08-18: the iframe-mounted embed path makes
    // non-hydration deterministic; hardened to the flag 2026-09-01).
    // GENERATION GATE (round 2): the field is also untrustworthy when
    // disk holds a sidecar write this editor never ingested — fall back
    // to the disk-authoritative path, which cannot drop it.
    const trustField = (cm && cm._tcHydrated
      && mtimeAtLoad === (cm._tcSidecarMtime || 0))
      ? await bufferMatchesDisk(file, cm) : false;
    const cur = trustField ? cm.state.doc.toString() : await diskTextOf(file);
    if (cur == null) return false;
    const loaded = await loadStore(app, file, cur);
    const store = loaded || emptyStore(file.path);
    // Snapshot what DISK held BEFORE any merge (round 2, 2026-09-01):
    // ids the trustField merge drops as field-consumed must count as
    // deliberately dropped, or the write below false-parks them and an
    // emptying mutation can never vouch its delete.
    const beforeIds = new Set();
    for (const k of ['suggestions', 'detached', 'comments']) {
      for (const x of store[k] || []) beforeIds.add(String(x && x.id));
    }
    if (trustField) {
      const fieldOps = liveOps(file, null);
      if (fieldOps && (fieldOps.length || !(store.suggestions || []).length)) {
        // MERGE, don't replace: disk ops whose id (or fragment lineage,
        // BOTH directions) this editor's field never carried are a
        // foreign write it never saw — they must survive (incident
        // 2026-09-01).
        const known = new Set(cm._tcKnownIds || []);
        for (const o of fieldOps) known.add(String(o && o.id));
        const knownAncestors = new Set();
        for (const k of known) {
          let curId = String(k); let next;
          while ((next = curId.replace(/[~#]p?\d+$/, '')) !== curId) { knownAncestors.add(next); curId = next; }
        }
        const baseOf = (id) => String(id).replace(/([~#]p?\d+)+$/, '');
        const foreign = (store.suggestions || []).filter((x) => {
          const id = String(x && x.id);
          return !known.has(id) && !known.has(baseOf(id)) && !knownAncestors.has(id);
        });
        store.suggestions = fieldOps.concat(foreign);
        // GHOST GUARD (see persistNonActiveStore): with the field
        // authoritative, an op this load's rebase detached but that was
        // not detached ON DISK was resolved in-editor, not orphaned.
        try {
          const rawStore = JSON.parse(await app.vault.adapter.read(storePath(file)));
          const prior = new Set(((rawStore.detached) || []).map((d) => d && d.id));
          // Split residuals (id `…#pN`, review 2026-08-26) are freshly minted
          // from an op that WAS on disk — the parent id vouches for them, or
          // this guard would erase the record the split just preserved.
          const priorSugg = new Set(((rawStore.suggestions) || []).map((x) => x && x.id));
          const parentOf = (id) => String(id || '').replace(/#p\d+$/, '');
          store.detached = (store.detached || []).filter((d) => d && (prior.has(d.id)
            || (d.superseded === 'user-edit' && priorSugg.has(d.id))
            || (/#p\d+$/.test(String(d.id))
              && (priorSugg.has(parentOf(d.id)) || prior.has(parentOf(d.id))))));
        } catch (e) { store.detached = []; }
      }
    }
    await fn(store, cur);
    // Ids fn deliberately dropped — saveStore must not park them as
    // foreign losses (round 2: false parks + notices on every dismiss).
    const dropped = new Set(beforeIds);
    for (const k of ['suggestions', 'detached', 'comments']) {
      for (const x of store[k] || []) dropped.delete(String(x && x.id));
    }
    // No sidecar existed and fn left nothing: a clean no-op — never
    // manufacture an empty junk sidecar (round 2).
    if (!loaded && !(store.suggestions || []).length
        && !(store.comments || []).length && !(store.detached || []).length) {
      return true;
    }
    if ((await storeMtime(app, file)) !== mtimeAtLoad) {
      console.warn(`[track-changents] ${file.path}: sidecar changed during the edit — action skipped, retry`);
      scheduleRollupPush();
      return false;
    }
    // fn emptied an EXISTING store: delete it (fenced), matching
    // doSaveInner's empty branch — writing {[],[],[]} left junk
    // sidecars accreting in .trackchanges/ (round 4, 2026-08-31).
    // `dropped` is exactly the set this mutation deliberately resolved,
    // so it is what the delete may vouch for (incident 2026-09-01).
    if (loaded && !(store.suggestions || []).length
        && !(store.comments || []).length && !(store.detached || []).length) {
      const ok = await deleteStore(app, file, mtimeAtLoad, dropped);
      if (!ok) {
        console.warn(`[track-changents] ${file.path}: emptied sidecar holds unvouched entries — delete deferred, retry`);
        scheduleRollupPush();
      }
      return ok;
    }
    const written = await saveStore(app, file, store, cur,
      { expectedMtime: mtimeAtLoad, resolvedIds: dropped });
    if (written == null) {
      console.warn(`[track-changents] ${file.path}: sidecar changed during the write — action skipped, retry`);
      scheduleRollupPush();
      return false;
    }
    if (cm) {
      try { syncMeta(file, store, await isFileTracked(app, file)); } catch (e) { /* best effort */ }
      try {
        cm._tcSidecarMtime = await storeMtime(app, file);
        stampKnownIds(cm, store);
      } catch (e) { /* best effort */ }
    }
    return true;
  };

  // Fold ONE file's unwritten resolutions into its own sidecar by disk
  // read-modify-write (factored from pushActive's switch fold, round 4,
  // so the watcher's give-up path can drain a stranded gate-deferred
  // persist too). Failures keep the entry armed.
  const foldResolvedToDisk = async (path) => {
    const e = pendingByPath.get(path);
    if (!e) return true;
    if (entryEmpty(e)) { pendingByPath.delete(path); return true; }
    const f = app.vault.getAbstractFileByPath(path);
    if (!f) {
      console.error('[track-changents] dropping resolutions for a vanished file:', path);
      pendingByPath.delete(path);
      return true;
    }
    const armed = armSnapshot(e);
    try {
      let ok = false;
      // Bounded retries: each attempt re-reads disk, so a retry after a
      // fence trip starts from fresh (foreign-incl.) bytes.
      for (let i = 0; i < 3 && !ok; i++) {
        ok = await mutateStoreInFile(f, (st) => { applyPendingResolved(st, e); }, { diskOnly: true });
      }
      if (ok) { disarm(e, armed); pruneEntry(path); return true; }
      console.error('[track-changents] resolution fold kept failing; ids stay armed:', path);
    } catch (err) { console.error('[track-changents] outgoing resolution fold failed:', err); }
    return false;
  };

  const host = {
    hydrateView: async (view) => {
      try {
        const file = fileForCm(view);
        if (!file) return;
        const on = track.isTracked(await loadTrackedList(app), file.path);
        const cur = view.state.doc.toString();
        // Stat BEFORE the load: an honestly-stale stamp only defers one
        // persist to the resync watcher; a too-fresh one would let a
        // stale field mask a CLI write (round 2, 2026-09-01).
        const mt = await storeMtime(app, file);
        let store = await loadStore(app, file, cur);
        if (!store && cur != null) store = await healOrphanStore(app, file, cur);
        if (!store) store = emptyStore(file.path);
        // Same filter every other ingestion point has (round 4): a
        // remount must not re-render an op whose resolution is armed
        // but not yet folded to disk.
        applyPendingResolved(store, pendingByPath.get(file.path));
        view.dispatch({
          effects: [setSuggestions.of(store.suggestions || []), setTrackMeta.of({ trackingOn: on, comments: store.comments || [] })],
          annotations: [Transaction.addToHistory.of(false), syncAnnotation.of(true)],
        });
        view._tcHydrated = true;
        view._tcSidecarMtime = mt;
        stampKnownIds(view, store);
      } catch (e) { /* best effort */ }
    },
    // The ops changed in an editor (human keystroke mapped through, or accept/reject).
    // Mirror them into the active store, refresh the panel, schedule a save.
    onOpsChanged: (view, deliberate) => {
      // Ignore field churn from the editor buffer catching up to a disk write during
      // an external reload — the sidecar on disk is the source of truth then, and
      // persisting the transiently-mapped ops here is what erased it.
      // ...but an accept/reject CLICKED during the reload's multi-await
      // window is deliberate and must still ARM, or the reload's own
      // save resurrects the op (review round 2, 2026-08-30). Arm only —
      // no store mirror, no save — then bail as before.
      if (externalReloading) {
        try {
          if (deliberate && active && active.file && fileForCm(view) === active.file
              && suggestionsFieldRef.f) {
            const opsNow = view.state.field(suggestionsFieldRef.f, false) || [];
            const nowIds = new Set(opsNow.map((o) => String(o && o.id)));
            // Arm only ids THIS editor's field actually carried (round
            // 2, 2026-09-01): store-minus-field over a stale field
            // fabricated vouches for CLI ops nobody resolved, and the
            // empty-branch delete then took them.
            const knownArm = new Set(view._tcKnownIds ? [...view._tcKnownIds] : []);
            for (const id of nowIds) knownArm.add(id);
            const baseOfArm = (id) => String(id).replace(/([~#]p?\d+)+$/, '');
            const e = resolvedFor(active.file.path);
            for (const prev of active.store.suggestions || []) {
              const id = String(prev && prev.id);
              if (!nowIds.has(id) && (knownArm.has(id) || knownArm.has(baseOfArm(id)))) {
                e.ops.set(id, opSnapshot(prev));
              }
            }
            for (const id of nowIds) e.ops.delete(id);
          }
        } catch (e) { /* best-effort arming */ }
        return;
      }
      const file = fileForCm(view);
      if (!file) return;
      if (!active || active.file !== file) {
        // EMBED (or otherwise non-active) editor: mirror to ITS sidecar
        // on a debounce — see scheduleNonActivePersist. The panel still
        // refreshes so closure cards track the keystroke.
        scheduleNonActivePersist(file);
        const p = getPanel(); if (p) p.notifyChanged();
        return;
      }
      const ops = view.state.field(suggestionsFieldRef.f, false);
      if (ops != null) {
        // User typing that consumed a pending op WHOLE (the engine emits
        // no fragment for it) leaves a visible "superseded by your edit"
        // ghost instead of vanishing silently (user-approved 2026-09-01,
        // fourth confusion round). Deliberate accept/reject is a
        // resolution, not a supersede — excluded below.
        if (!deliberate) {
          const gone = track.supersededOps(active.store.suggestions || [], ops);
          if (gone.length) {
            const det = active.store.detached = active.store.detached || [];
            const now = Date.now();
            for (const g of gone) {
              if (!det.some((d) => String(d && d.id) === String(g.id))) {
                det.push({ ...g, detached: true, superseded: 'user-edit', supersededTs: now });
              }
            }
          }
        }
        // A deliberate accept/reject exists solely in the field: remember
        // WHICH ids it removed, so a disk-deferred save can still honor
        // them at reload time (id filter) without a blanket bypass.
        if (deliberate) {
          const now = new Set(ops.map((o) => String(o && o.id)));
          // Same gate as the externalReloading arm: only ids this
          // editor's field actually carried may be armed as resolved —
          // a stale field must not vouch away foreign ops (round 2).
          const knownArm = new Set(view._tcKnownIds ? [...view._tcKnownIds] : []);
          for (const id of now) knownArm.add(id);
          const baseOfArm = (id) => String(id).replace(/([~#]p?\d+)+$/, '');
          const e = resolvedFor(file.path);
          for (const prev of active.store.suggestions || []) {
            const id = String(prev && prev.id);
            // Snapshot BOTH texts: a same-id CLI revision — including of
            // a deletion, whose newText is always '' — must stay live
            // (review round 2, 2026-08-30).
            if (!now.has(id) && (knownArm.has(id) || knownArm.has(baseOfArm(id)))) {
              e.ops.set(id, opSnapshot(prev));
            }
          }
          // Symmetric: an id back in the field (Cmd-Z of an accept) is
          // live again — leaving it armed would re-resolve it at the
          // next deferred reload (review 2026-08-30). Sync pushes carry
          // syncAnnotation and never reach this code.
          for (const id of now) e.ops.delete(id);
        }
        active.store.suggestions = ops;
      }
      const p = getPanel(); if (p) p.notifyChanged();
      scheduleSave();
    },
    onOpenPanel: (offset, focusReply, view) => {
      // A click in an EMBED editor targets that file's card, which is
      // keyed "path#offset" (closure sections); the active note's cards
      // keep bare numeric keys.
      let key = offset;
      if (typeof offset === 'number' && view) {
        const f = fileForCm(view);
        if (f && (!active || active.file !== f)) key = `${f.path}#${offset}`;
      }
      void openPanel().then(() => {
        const p = getPanel();
        if (p) { if (key != null) p.focusChange(key, focusReply); else p.notifyChanged(); }
      });
    },
    colorChip,
    stateChip,
    typingRow,
    acceptAt: (from, view) => host.resolveInline(from, false, view),
    rejectAt: (from, view) => host.resolveInline(from, true, view),
    // Current-name resolution for author chips (renames self-heal via the
    // recorded ROMP_SID), and the detached card's send-back action.
    resolveAuthorRow: (ref) => diffRewrite.resolveAuthorRow(plugin, ref),
    sendDetachedBack: (file, det) => diffRewrite.sendDetachedBack(plugin,
      { author: det.author, authorId: det.authorId }, file, det),
    // Sync probe for the click handlers: does any op actually resolve at
    // this position in this editor's CURRENT doc? False during
    // sidecar/doc drift — the moment clicks must fall through to CM.
    hasResolvableAt: (view, from) => {
      try {
        const ops = suggestionsFieldRef.f
          ? (view.state.field(suggestionsFieldRef.f, false) || []) : [];
        if (!ops.length) return false;
        return idsAtPosition(ops, view.state.doc.toString(), from).length > 0;
      } catch (e) { return false; }
    },
    // Inline click on either side of a change: plain accepts, modifier rejects.
    // `view` (optional) is the editor the click landed in — for an EMBED
    // editor that is a DIFFERENT file than `active`, and both the
    // position lookup and the persistence must target ITS file.
    resolveInline: guard('resolve', async (from, reject, view) => {
      const file = (view && fileForCm(view)) || (active && active.file);
      if (!file) return;
      const inActive = !!(active && active.file === file);
      const cm = inActive ? cmForFile(file) : view;
      if (!cm) return;
      const ops = liveOps(file, inActive ? active.store.suggestions : []);
      const cur = cm.state.doc.toString();
      const ids = idsAtPosition(ops, cur, from);
      if (!ids.length) return;
      if (reject) {
        const { edits, suggestions } = track.rejectSuggestions(ops, ids);
        cm.dispatch({ changes: edits, effects: setSuggestions.of(suggestions) });
      } else {
        const { suggestions } = track.acceptSuggestions(ops, ids);
        cm.dispatch({ effects: setSuggestions.of(suggestions) });
      }
      dropResolvedThreads(file, ids, ops);
      // onOpsChanged mirrors only the ACTIVE file's store, so an embed
      // resolution would evaporate on reload — persist the embed file's
      // sidecar straight from its editor's field state.
      if (!inActive) await persistNonActiveStore(file, cm, resolvedPairs(ids, ops, cm));
    }),
    activeContext: () => {
      if (!active || !active.file) return null;
      const cur = currentText(active.file);
      if (cur == null) return null;
      const ops = liveOps(active.file, active.store.suggestions);
      return {
        file: active.file,
        ops,
        comments: active.store ? (active.store.comments || []) : [],
        current: cur,
        baseline: track.baselineOf(cur, ops),
        store: active.store || null,
      };
    },
    reveal,
    acceptAll: guard('accept all', async () => {
      if (!active || !active.file) return;
      const file = active.file;
      const cm = cmForFile(file); if (!cm) return;
      const ops = liveOps(file, active.store.suggestions);
      const { suggestions } = track.acceptAll(ops);
      cm.dispatch({ effects: setSuggestions.of(suggestions) });
      // Every change accepted → drop all change-threads, ARMED so a
      // disk-deferred save cannot resurrect them (review round 2).
      active.store.comments = (active.store.comments || []).filter((c) => {
        const drop = c && c.suggestionId != null;
        if (drop) resolvedFor(file.path).comments.set(String(c.id), commentSig(c));
        return !drop;
      });
      await commitComments(file);
    }),
    rejectAll: guard('reject all', async () => {
      if (!active || !active.file) return;
      const file = active.file;
      const cm = cmForFile(file); if (!cm) return;
      const ops = liveOps(file, active.store.suggestions);
      const { edits, suggestions } = track.rejectAll(ops);
      cm.dispatch({ changes: edits, effects: setSuggestions.of(suggestions) });
      active.store.comments = (active.store.comments || []).filter((c) => {
        const drop = c && c.suggestionId != null;
        if (drop) resolvedFor(file.path).comments.set(String(c.id), commentSig(c));
        return !drop;
      });
      await commitComments(file);
    }),
    replyToComment: guard('reply', async (id, text) => {
      if (!active || !active.store || !(text && text.trim())) return;
      const c = (active.store.comments || []).find((x) => String(x.id) === String(id));
      if (!c) return;
      if (!Array.isArray(c.replies)) c.replies = [];
      c.replies.push({ author: 'you', ts: Date.now(), body: text.trim() });
      await commitComments(active.file);
      await pingAgent(c.pingAuthor || (c.author && c.author !== 'you' ? c.author : null),
        c.id, 'your comment', text.trim());
    }),
    // Reply to a CHANGE: a change IS a thread, keyed to the op by `suggestionId`
    // (the op id) — the same key VS Code writes, so the shared sidecar agrees. A
    // collapsed paragraph card has no single id, so use the first op it covers.
    replyToChange: guard('reply', async (h, text) => {
      if (!active || !active.file || !(text && text.trim())) return;
      const body = text.trim();
      const cur = currentText(active.file);
      const sid = h.id != null ? h.id
        : (idsAtPosition(active.store.suggestions || [], cur, h.curFrom)[0] || null);
      let thread = (active.store.comments || []).find((c) => c.suggestionId != null && c.suggestionId === sid);
      if (thread) {
        if (!Array.isArray(thread.replies)) thread.replies = [];
        thread.replies.push({ author: 'you', ts: Date.now(), body });
      } else {
        thread = {
          id: `${Date.now()}-${h.curFrom}`,
          author: 'you', ts: Date.now(),
          suggestionId: sid,
          pingAuthor: (h.author && h.author !== 'you') ? h.author : null,
          body, replies: [], resolved: false,
        };
        active.store.comments.push(thread);
      }
      await commitComments(active.file);
      const cut = (s) => (s && s.length > 40 ? s.slice(0, 40) + '…' : s);
      const desc = h.kind === 'del' ? `your deletion of "${cut(h.oldText)}"`
        : h.kind === 'ins' ? `your insertion of "${cut(h.newText)}"`
          : `your change of "${cut(h.oldText)}" to "${cut(h.newText)}"`;
      await pingAgent((h.author && h.author !== 'you') ? h.author : null, thread.id, desc, body);
    }),
    resolveComment: guard('resolve comment', async (id) => {
      if (!active || !active.store) return;
      const c = (active.store.comments || []).find((x) => String(x.id) === String(id));
      resolvedFor(active.file.path).comments.set(String(id), c ? commentSig(c) : null);
      active.store.comments = (active.store.comments || []).filter((x) => String(x.id) !== String(id));
      await commitComments(active.file);
    }),
    // A pending Cmd-M message the user manually clears (its anchored text never
    // changed, so it wouldn't auto-resolve).
    dismissMessage: guard('dismiss', async (id) => {
      if (!active || !active.store) return;
      const c = (active.store.comments || []).find((x) => String(x.id) === String(id));
      resolvedFor(active.file.path).comments.set(String(id), c ? commentSig(c) : null);
      active.store.comments = (active.store.comments || []).filter((x) => String(x.id) !== String(id));
      await commitComments(active.file);
    }),
    isTrackingOn: () => isEnabled(plugin),
    toggleTracking: () => toggle(),

    // ── Whole-tree review (user ask 2026-08-18): the panel covers the
    // active note PLUS every note in its embed tree — "everything I
    // could do from the top level". Closure notes' contexts come from
    // their live editors when mounted, else disk + sidecar.
    closureContexts: async () => {
      if (!active || !active.file) return [];
      let closure;
      try { closure = await trackTree.trackedClosure([active.file.path], embedTreeDeps(app)); }
      catch (e) { return []; }
      closure.delete(active.file.path);
      const out = [];
      for (const p of closure) {
        const f = app.vault.getAbstractFileByPath(p);
        if (!(f instanceof TFile)) continue;
        try {
          const cm = cmForFile(f);
          const cur = cm ? cm.state.doc.toString() : await app.vault.cachedRead(f);
          if (cur == null) continue;
          const store = (await loadStore(app, f, cur)) || emptyStore(p);
          // Same filter every ingestion point has (round 5): an armed
          // resolution whose write deferred must not re-render as a live
          // card in the panel it was just resolved from.
          applyPendingResolved(store, pendingByPath.get(p));
          const ops = liveOps(f, store.suggestions || []);
          const comments = store.comments || [];
          const detached = store.detached || [];
          if (!ops.length && !comments.length && !detached.length) continue;
          out.push({ file: f, ops, comments, detached, current: cur, baseline: track.baselineOf(cur, ops), store });
        } catch (e) { /* skip unreadable */ }
      }
      out.sort((a, b) => a.file.basename.localeCompare(b.file.basename));
      return out;
    },
    // Panel cards resolve hunks to op IDS at render time, against the
    // same snapshot the card was drawn from — the click then acts on
    // those ids against FRESH state, so a note that shifted since the
    // snapshot can never resolve the wrong op (review 2026-08-18; ids
    // are stable across reanchoring, positions are not).
    idsForHunk: (ops, current, h) => (h.id != null ? [h.id] : idsAtPosition(ops || [], current, h.curFrom)),
    // Accept/Reject changes (by op id) in a closure note. With a live
    // (embed) editor mounted, dispatch through CM so the inline overlay
    // and undo history stay correct; otherwise operate on disk text +
    // sidecar directly — accept keeps the text and drops the op, reject
    // applies the inverse edits (applyEditsToText is the CM "dispatch"
    // for a string).
    resolveIdsInFile: guard('resolve in file', async (file, ids, reject) => {
      if (!Array.isArray(ids) || !ids.length) return;
      const cm = cmForFile(file);
      if (cm) {
        if (!(await bufferMatchesDisk(file, cm))) return;
        const ops = liveOps(file, []);
        const alive = ids.filter((id) => ops.some((o) => o.id === id));
        if (!alive.length) { scheduleRollupPush(); return; }
        if (reject) {
          const { edits, suggestions } = track.rejectSuggestions(ops, alive);
          cm.dispatch({ changes: edits, effects: setSuggestions.of(suggestions) });
        } else {
          const { suggestions } = track.acceptSuggestions(ops, alive);
          cm.dispatch({ effects: setSuggestions.of(suggestions) });
        }
        if (active && active.file === file) dropResolvedThreads(file, alive);
        else await persistNonActiveStore(file, cm, resolvedPairs(alive, ops, cm));
      } else {
        const cur = await diskTextOf(file);
        if (cur == null) return;
        const mtimeAtLoad = await storeMtime(app, file);
        const store = await loadStore(app, file, cur);
        if (!store) return;
        const ops = store.suggestions || [];
        const alive = ids.filter((id) => ops.some((o) => o.id === id));
        if (!alive.length) { scheduleRollupPush(); return; }
        const idset = new Set(alive);
        // Vouch the resolved ops AND their dropped threads to saveStore
        // (round 3): unvouched, every no-editor panel resolution wrote a
        // junk park plus a false 'parked concurrent suggestions' Notice.
        // ARM them durably too (round 4): the reject path edits the NOTE
        // before the fenced sidecar write, and a fence-null left a torn
        // state whose next load rebase-detached the rejected ops into
        // permanent stale cards. Armed, they filter at every load and
        // the fold eventually writes them out.
        const e0 = resolvedFor(file.path);
        const droppedThreadIds = [];
        const dropThreads = (s) => { s.comments = (s.comments || []).filter((c) => {
          const drop = c && c.suggestionId != null && idset.has(c.suggestionId);
          if (drop) {
            droppedThreadIds.push(String(c.id));
            e0.comments.set(String(c.id), commentSig(c));   // armed pre-drop
          }
          return !drop;
        }); };
        // Staleness gate: note text and sidecar must both still be what
        // this resolution was computed against.
        if ((await diskTextOf(file)) !== cur || (await storeMtime(app, file)) !== mtimeAtLoad) {
          console.warn(`[track-changents] ${file.path}: changed under the panel — action skipped, retry`);
          scheduleRollupPush();
          return;
        }
        for (const id of alive) {
          const o = ops.find((x) => String(x && x.id) === String(id));
          e0.ops.set(String(id), o ? opSnapshot(o) : null);
        }
        let written;
        if (reject) {
          const { edits, suggestions } = track.rejectSuggestions(ops, alive);
          const next = rollup.applyEditsToText(cur, edits);
          store.suggestions = suggestions;
          dropThreads(store);
          await app.vault.modify(file, next);
          written = await saveStore(app, file, store, next,
            { expectedMtime: mtimeAtLoad, resolvedIds: new Set([...alive.map(String), ...droppedThreadIds]) });
        } else {
          const { suggestions } = track.acceptSuggestions(ops, alive);
          store.suggestions = suggestions;
          dropThreads(store);
          written = await saveStore(app, file, store, cur,
            { expectedMtime: mtimeAtLoad, resolvedIds: new Set([...alive.map(String), ...droppedThreadIds]) });
        }
        if (written == null) {
          console.warn(`[track-changents] ${file.path}: sidecar changed during the write — resolution armed, will fold`);
          scheduleRollupPush();
          return;
        }
        for (const id of alive) e0.ops.delete(String(id));
        for (const id of droppedThreadIds) e0.comments.delete(id);
        pruneEntry(file.path);
      }
      bumpRollupGen(); scheduleRollupPush();
    }),
    acceptAllInFile: guard('accept all in file', async (file) => {
      const cm = cmForFile(file);
      if (cm) {
        if (!(await bufferMatchesDisk(file, cm))) return;
        const ops = liveOps(file, []);
        if (!ops.length) return;
        const { suggestions } = track.acceptAll(ops);
        cm.dispatch({ effects: setSuggestions.of(suggestions) });
        await persistNonActiveStore(file, cm, resolvedPairs(ops.map((o) => o.id), ops, cm));
      } else {
        const cur = await diskTextOf(file);
        if (cur == null) return;
        const mtimeAtLoad = await storeMtime(app, file);
        const store = await loadStore(app, file, cur);
        if (!store || !(store.suggestions || []).length) return;
        if ((await storeMtime(app, file)) !== mtimeAtLoad) {
          console.warn(`[track-changents] ${file.path}: sidecar changed under the panel — action skipped, retry`);
          scheduleRollupPush();
          return;
        }
        // Arm-before-mutate + fence-null handling (round 4) — the armed
        // resolution survives a refused write and folds later.
        const e0 = resolvedFor(file.path);
        for (const o of store.suggestions || []) e0.ops.set(String(o && o.id), opSnapshot(o));
        const droppedC = (store.comments || []).filter((c) => c && c.suggestionId != null);
        for (const c of droppedC) e0.comments.set(String(c.id), commentSig(c));
        const vouch = new Set([
          ...(store.suggestions || []).map((o) => String(o && o.id)),
          ...droppedC.map((c) => String(c.id)),
        ]);
        const { suggestions } = track.acceptAll(store.suggestions);
        store.suggestions = suggestions;
        store.comments = (store.comments || []).filter((c) => !(c && c.suggestionId != null));
        const written = await saveStore(app, file, store, cur, { expectedMtime: mtimeAtLoad, resolvedIds: vouch });
        if (written == null) {
          console.warn(`[track-changents] ${file.path}: sidecar changed during the write — resolution armed, will fold`);
          scheduleRollupPush();
          return;
        }
        for (const id of vouch) { e0.ops.delete(id); e0.comments.delete(id); }
        pruneEntry(file.path);
      }
      bumpRollupGen(); scheduleRollupPush();
    }),
    rejectAllInFile: guard('reject all in file', async (file) => {
      const cm = cmForFile(file);
      if (cm) {
        if (!(await bufferMatchesDisk(file, cm))) return;
        const ops = liveOps(file, []);
        if (!ops.length) return;
        const { edits, suggestions } = track.rejectAll(ops);
        cm.dispatch({ changes: edits, effects: setSuggestions.of(suggestions) });
        await persistNonActiveStore(file, cm, resolvedPairs(ops.map((o) => o.id), ops, cm));
      } else {
        const cur = await diskTextOf(file);
        if (cur == null) return;
        const mtimeAtLoad = await storeMtime(app, file);
        const store = await loadStore(app, file, cur);
        if (!store || !(store.suggestions || []).length) return;
        if ((await diskTextOf(file)) !== cur || (await storeMtime(app, file)) !== mtimeAtLoad) {
          console.warn(`[track-changents] ${file.path}: changed under the panel — action skipped, retry`);
          scheduleRollupPush();
          return;
        }
        // Arm-before-mutate + fence-null handling (round 4): the note
        // edit below lands BEFORE the fenced sidecar write, so a refused
        // write must leave the resolution armed or the rejected ops
        // resurrect as permanent stale cards on the next load.
        const e0 = resolvedFor(file.path);
        for (const o of store.suggestions || []) e0.ops.set(String(o && o.id), opSnapshot(o));
        const droppedC = (store.comments || []).filter((c) => c && c.suggestionId != null);
        for (const c of droppedC) e0.comments.set(String(c.id), commentSig(c));
        const vouch = new Set([
          ...(store.suggestions || []).map((o) => String(o && o.id)),
          ...droppedC.map((c) => String(c.id)),
        ]);
        const { edits, suggestions } = track.rejectAll(store.suggestions);
        const next = rollup.applyEditsToText(cur, edits);
        store.suggestions = suggestions;
        store.comments = (store.comments || []).filter((c) => !(c && c.suggestionId != null));
        await app.vault.modify(file, next);
        const written = await saveStore(app, file, store, next, { expectedMtime: mtimeAtLoad, resolvedIds: vouch });
        if (written == null) {
          console.warn(`[track-changents] ${file.path}: sidecar changed during the write — resolution armed, will fold`);
          scheduleRollupPush();
          return;
        }
        for (const id of vouch) { e0.ops.delete(id); e0.comments.delete(id); }
        pruneEntry(file.path);
      }
      bumpRollupGen(); scheduleRollupPush();
    }),
    replyToChangeInFile: guard('reply', async (file, h, text) => {
      if (!(text && text.trim())) return;
      const body = text.trim();
      let threadId = null;
      await mutateStoreInFile(file, (store, cur) => {
        const sid = h.id != null ? h.id
          : ((h._tcIds && h._tcIds[0]) != null ? h._tcIds[0]
            : (idsAtPosition(store.suggestions || [], cur, h.curFrom)[0] || null));
        let thread = (store.comments || []).find((c) => c.suggestionId != null && c.suggestionId === sid);
        if (thread) {
          if (!Array.isArray(thread.replies)) thread.replies = [];
          thread.replies.push({ author: 'you', ts: Date.now(), body });
        } else {
          thread = {
            id: `${Date.now()}-${h.curFrom}`,
            author: 'you', ts: Date.now(),
            suggestionId: sid,
            pingAuthor: (h.author && h.author !== 'you') ? h.author : null,
            body, replies: [], resolved: false,
          };
          if (!Array.isArray(store.comments)) store.comments = [];
          store.comments.push(thread);
        }
        threadId = thread.id;
      });
      const cut = (s) => (s && s.length > 40 ? s.slice(0, 40) + '…' : s);
      const desc = h.kind === 'del' ? `your deletion of "${cut(h.oldText)}"`
        : h.kind === 'ins' ? `your insertion of "${cut(h.newText)}"`
          : `your change of "${cut(h.oldText)}" to "${cut(h.newText)}"`;
      await pingAgent((h.author && h.author !== 'you') ? h.author : null, threadId, desc, body, file);
      const p = getPanel(); if (p) p.notifyChanged();
    }),
    replyToCommentInFile: guard('reply', async (file, id, text) => {
      if (!(text && text.trim())) return;
      let ping = null;
      await mutateStoreInFile(file, (store) => {
        const c = (store.comments || []).find((x) => String(x.id) === String(id));
        if (!c) return;
        if (!Array.isArray(c.replies)) c.replies = [];
        c.replies.push({ author: 'you', ts: Date.now(), body: text.trim() });
        ping = c.pingAuthor || (c.author && c.author !== 'you' ? c.author : null);
      });
      await pingAgent(ping, id, 'your comment', text.trim(), file);
      const p = getPanel(); if (p) p.notifyChanged();
    }),
    resolveCommentInFile: guard('resolve comment', async (file, id) => {
      await mutateStoreInFile(file, (store) => {
        store.comments = (store.comments || []).filter((x) => String(x.id) !== String(id));
      });
      bumpRollupGen(); scheduleRollupPush();
    }),
    // Clear a DETACHED op (its anchor text was edited away by an
    // out-of-band writer; the panel showed it as a stale card).
    dismissDetached: guard('dismiss stale', async (file, id) => {
      if (active && active.file === file) {
        const entry = (active.store.detached || []).find((d) => String(d && d.id) === String(id));
        active.store.detached = (active.store.detached || []).filter((d) => String(d && d.id) !== String(id));
        // The dismissal exists only in memory until written — the
        // snapshot lets a disk-deferred save still honor it at reload
        // time (no ghost card, 2026-08-18) while a same-id CLI revision
        // stays live (round 2). A missing entry arms null = drop always.
        resolvedFor(file.path).detached.set(String(id), entry ? opSnapshot(entry) : null);
        await commitComments(file);
        return;
      }
      await mutateStoreInFile(file, (store) => {
        store.detached = (store.detached || []).filter((d) => String(d && d.id) !== String(id));
      });
      bumpRollupGen(); scheduleRollupPush();
      const p = getPanel(); if (p) p.notifyChanged();
    }),
  };

  plugin.registerView(PANEL_TYPE, (leaf) => new TrackPanelView(leaf, host));
  plugin.registerEditorExtension(makeExtension(host));

  plugin.registerEvent(app.workspace.on('active-leaf-change', () => { if (!toggling) void pushActive(); }));
  plugin.registerEvent(app.workspace.on('file-open', () => { if (!toggling) void pushActive(); }));
  // The note file changed on disk (an agent/external tool). Obsidian reloads the
  // buffer itself; we re-key the ops/comments from the freshly-written sidecar.
  plugin.registerEvent(app.vault.on('modify', (file) => {
    if (active && active.file === file) scheduleReload();
  }));
  plugin.registerEvent(app.vault.on('rename', (file, oldPath) => { void rekeyStoreOnRename(file, oldPath); }));
  plugin.registerEvent(app.vault.on('delete', (file) => { void pruneStoreOnDelete(file); }));

  // How many unreviewed items each note has, keyed by vault path.
  //
  // "Tracked" and "has work waiting" are different questions, and only the first
  // had an answer anywhere in the UI. Nothing told you a file had pending
  // suggestions unless you happened to open it — which is how a real suggestion
  // sat unreviewed in this vault for two days after a rename took its note out of
  // the tracked list. Sidecars are re-parsed only when their mtime moves, so the
  // poll stays cheap as `.trackchanges/` grows.
  const pendingCache = new Map();   // storeKey -> { mtime, path, count }
  const scanPending = async () => {
    const adapter = app.vault.adapter;
    let listing;
    try { listing = await adapter.list(STORE_DIR); } catch (e) { return new Map(); }
    const seen = new Set();
    for (const f of ((listing && listing.files) || [])) {
      if (!f.endsWith('.json') || f === CONFIG_PATH || f.endsWith('.tmp')) continue;
      seen.add(f);
      let mtime = 0;
      try { const st = await adapter.stat(f); mtime = (st && st.mtime) || 0; } catch (e) { /* ignore */ }
      const hit = pendingCache.get(f);
      if (hit && hit.mtime === mtime) continue;
      try {
        const obj = JSON.parse(await adapter.read(f));
        const count = ((obj && obj.suggestions) || []).length + ((obj && obj.comments) || []).length
          + ((obj && obj.detached) || []).length;
        pendingCache.set(f, { mtime, path: (obj && obj.path) || null, count });
      } catch (e) {
        pendingCache.set(f, { mtime, path: null, count: 0 });
      }
    }
    for (const k of Array.from(pendingCache.keys())) if (!seen.has(k)) pendingCache.delete(k);
    const byPath = new Map();
    for (const v of pendingCache.values()) {
      if (!v.path || v.count <= 0) continue;
      // Only count work you can actually go and review. `pruneStoreOnDelete`
      // deliberately KEEPS the sidecar of a deleted note that still holds
      // unreviewed changes, so counting those would put a number in the status
      // bar for a file that cannot be opened.
      if (!app.vault.getAbstractFileByPath(v.path)) continue;
      byPath.set(v.path, v.count);
    }
    return byPath;
  };

  // File-explorer badges: "track" for scope, a count for unreviewed work.
  const applyTrackedBadges = async () => {
    let list;
    try { list = await loadTrackedList(app); } catch (e) { return; }
    let pending;
    try { pending = await scanPending(); } catch (e) { pending = new Map(); }
    plugin._pendingByPath = pending;
    // Changed pending work invalidates every rollup and wakes the
    // panel, so an embedded note's fresh changes surface in the
    // top-level review without opening that note.
    const pendingSig = Array.from(pending, ([p, n]) => p + ':' + n).sort().join('|');
    if (pendingSig !== lastPendingSig) {
      lastPendingSig = pendingSig;
      bumpRollupGen();
      const pv = getPanel(); if (pv) pv.notifyChanged();
    }
    // Nested outlines surface their children's pending work: push the
    // fresh counts onto the embed badges (a collapsed embed's content
    // never re-renders, so a pull model would go stale).
    try { if (plugin._refreshEmbedTrackBadges) plugin._refreshEmbedTrackBadges(pending); }
    catch (e) { /* ignore */ }
    // Self-heal NEVER-hydrated editors (user report 2026-08-18: an embed
    // showed a change the note's own open tab didn't — the tab's field
    // was empty until the panel forced a sync; iframe-mounted embeds can
    // also miss mount-time hydration deterministically). Keyed strictly
    // on the absence of the hydration mark, so an editor whose user just
    // resolved everything (legitimately empty field, unsaved sidecar)
    // is never touched.
    try {
      const m = plugin._embedEditorFiles;
      if (m) for (const [cm] of m) { if (cm && !cm._tcHydrated) void host.hydrateView(cm); }
      if (active && active.file) {
        const acm = cmForFile(active.file);
        if (acm && !acm._tcHydrated) syncEditor(active.file, active.store, isEnabled(plugin));
      }
    } catch (e) { /* ignore */ }
    // Derived-tracked files (tracking inheritance) badge like explicit
    // ones, so the explorer answers "will my edits be suggestions here?"
    let derived = new Set();
    try {
      derived = await trackTree.trackedClosure(
        list, trackTreeDeps(app), await loadUntrackedList(app),
      );
    } catch (e) { /* ignore */ }
    const folders = list.filter((p) => p.endsWith('/'));
    const isOn = (path, folder) => folder
      ? folders.includes(path.replace(/\/+$/, '') + '/')
      : (track.isTracked(list, path) || derived.has(path));
    for (const leaf of app.workspace.getLeavesOfType('file-explorer')) {
      const root = leaf && leaf.view && leaf.view.containerEl;
      if (!root) continue;
      root.querySelectorAll('.nav-file-title[data-path], .nav-folder-title[data-path]').forEach((el) => {
        const path = el.getAttribute('data-path');
        const on = !!path && isOn(path, el.classList.contains('nav-folder-title'));
        const has = el.querySelector(':scope > .tc-tracked-badge');
        if (on && !has) el.createSpan({ cls: 'tc-tracked-badge', text: 'track' });
        else if (!on && has) has.remove();
        const n = path ? (pending.get(path) || 0) : 0;
        let pb = el.querySelector(':scope > .tc-pending-badge');
        if (n > 0) {
          if (!pb) pb = el.createSpan({ cls: 'tc-pending-badge' });
          // Only write when the count changed. setText assigns
          // textContent, which replaces the text node even when the
          // string is identical — a childList mutation in the (observed)
          // left split that other plugins' workspace MutationObservers
          // react to. Unguarded, this 2.5s tick woke track-changents-workflow's
          // full dashboard re-evaluate forever, even with Obsidian idle.
          const txt = String(n);
          if (pb.textContent !== txt) {
            pb.setText(txt);
            pb.setAttr('title', `${n} unreviewed change${n === 1 ? '' : 's'} — click the note to review`);
          }
        } else if (pb) pb.remove();
      });
    }
    updatePendingStatus(pending);
  };
  plugin._applyTrackedBadges = applyTrackedBadges;

  // Embed counts ("⑃ N" in the embed title row): view.js owns the DOM,
  // this side owns the counts. A count AGGREGATES over the note's whole
  // embed tree (user ask 2026-08-18) — closure walked by track-tree.js,
  // so the rollup and tracking inheritance share one edge definition.
  //
  // The provider must stay synchronous (it's called mid-DOM-walk), but
  // the closure walk reads notes. So: answer from a generation-stamped
  // cache; on a miss, return the note's OWN count and queue the walk,
  // which re-pushes when it lands. The generation bumps when the
  // pending map changes content and on any markdown modify (an edit can
  // add/remove embed lines, changing the tree). Convergence: push →
  // provider hits cache → no queue → no further push (and every DOM
  // write downstream is diff-guarded).
  let rollupGen = 0;
  let lastPendingSig = null;
  const rollupCache = new Map();   // path -> { gen, count }
  const rollupQueued = new Set();
  let rollupPushTimer = null;
  const scheduleRollupPush = () => {
    if (rollupPushTimer) return;
    rollupPushTimer = window.setTimeout(() => {
      rollupPushTimer = null;
      view.refreshTrackBadges();
      const p = getPanel(); if (p) p.notifyChanged();
    }, 120);
  };
  const computeRollup = async (path) => {
    const gen = rollupGen;
    let closure;
    try { closure = await trackTree.trackedClosure([path], embedTreeDeps(app)); }
    catch (e) { closure = new Set([path]); }
    const count = rollup.sumOverClosure(closure, plugin._pendingByPath || new Map());
    if (gen !== rollupGen) return false;   // stale walk — discard silently
    rollupCache.set(path, { gen, count });
    return true;
  };
  const rollupFor = (path) => {
    const hit = rollupCache.get(path);
    if (hit && hit.gen === rollupGen) return hit.count;
    if (!rollupQueued.has(path)) {
      rollupQueued.add(path);
      // Push only when the walk actually landed at the current gen. A
      // discarded (stale-gen) walk must NOT push: push → provider miss →
      // requeue is a self-sustaining loop while modifies stream in (the
      // review's spin finding); the 2.5s scan tick re-queues instead.
      void computeRollup(path)
        .then((cached) => { if (cached) scheduleRollupPush(); })
        .catch(() => { /* next tick retries */ })
        .finally(() => { rollupQueued.delete(path); });
    }
    // While invalidated, a STALE aggregate beats a fresh own-count: the
    // latter visibly dips (5 → 2 → 5) on every generation bump.
    if (hit) return hit.count;
    const pending = plugin._pendingByPath;
    return pending ? (pending.get(path) || 0) : 0;
  };
  const bumpRollupGen = () => {
    rollupGen++;
    if (rollupCache.size > 500) rollupCache.clear();
  };
  plugin._trackRollupFor = rollupFor;
  view.setTrackCountProvider((src) => {
    const linktext = String(src || '').split('#')[0].split('|')[0].trim();
    if (!linktext) return null;
    const dest = app.metadataCache.getFirstLinkpathDest(linktext, '');
    if (!dest) return null;
    return rollupFor(dest.path);
  });
  // Trailing-debounced: an agent CLI streaming note writes fires modify
  // every save; bumping per-event would invalidate every in-flight walk
  // forever (nothing would ever cache). One bump per quiet period is
  // enough — edges only matter once the burst settles, and the pending-
  // signature bump in applyTrackedBadges covers count changes meanwhile.
  let bumpTimer = null;
  plugin.registerEvent(app.vault.on('modify', (f) => {
    if (!(f && f.path && f.path.endsWith('.md'))) return;
    if (bumpTimer) window.clearTimeout(bumpTimer);
    bumpTimer = window.setTimeout(() => { bumpTimer = null; bumpRollupGen(); }, 2000);
  }));
  plugin._refreshEmbedTrackBadges = () => view.refreshTrackBadges();

  // Status-bar total, so unreviewed work is visible without the file explorer
  // open. Silent when there is nothing waiting.
  let pendingStatusEl = null;
  const updatePendingStatus = (pending) => {
    const files = pending.size;
    let total = 0;
    for (const n of pending.values()) total += n;
    if (!files) {
      if (pendingStatusEl) { pendingStatusEl.remove(); pendingStatusEl = null; }
      return;
    }
    if (!pendingStatusEl) {
      pendingStatusEl = plugin.addStatusBarItem();
      pendingStatusEl.addClass('tc-track-status');
      pendingStatusEl.addEventListener('click', () => void openNextPending());
      pendingStatusEl.setAttr('title', 'Unreviewed tracked changes. Click to open the next file.');
    }
    // Same guard as the explorer badges: unchanged totals → zero DOM
    // writes, so the 2.5s tick can't wake workspace MutationObservers.
    const statusTxt = `⑃ ${total} in ${files} file${files === 1 ? '' : 's'}`;
    if (pendingStatusEl.textContent !== statusTxt) pendingStatusEl.setText(statusTxt);
  };

  // Open the next note that has unreviewed work, skipping the one already open.
  const openNextPending = async () => {
    const pending = plugin._pendingByPath || new Map();
    const cur = activeMarkdownFile();
    const paths = Array.from(pending.keys()).sort();
    const next = paths.find((p) => !cur || p !== cur.path) || paths[0];
    if (!next) return;
    const f = app.vault.getAbstractFileByPath(next);
    if (!f) return;
    await app.workspace.getLeaf(false).openFile(f);
    await openPanel();
  };
  plugin.addCommand({ id: 'tc-track-next-pending', name: 'Track changes: open next file with unreviewed changes',
    callback: () => void openNextPending() });

  // Poll: follow an EXTERNAL flip of the shared tracked flag, and watch the active
  // note's sidecar mtime — reloading only when it actually changed on disk (agent
  // CLIs write only the sidecar, which Obsidian's vault events don't watch). No
  // whole-store stringify per tick.
  plugin.registerInterval(window.setInterval(() => {
    void (async () => {
      try {
        if (toggling) return;   // don't fight an in-flight toggle
        // Self-heal a stale context: whatever the cause (a race this
        // code hasn't met yet, a swallowed event), if the viewed file
        // and `active` disagree, repoint — the panel must never show a
        // file that is not being viewed (user report 2026-08-18).
        const viewed = activeMarkdownFile();
        if (viewed && (!active || active.file !== viewed)) { await pushActive(); return; }
        const on = (active && active.file) ? await isFileTracked(app, active.file) : false;
        if (on !== isEnabled(plugin)) { plugin._trackEnabled = on; await pushActive(); return; }
        if (!active || !active.file) return;
        if (!isEnabled(plugin) && (!active.store || (active.store.suggestions.length === 0 && active.store.comments.length === 0))) return;
        const mt = await storeMtime(app, active.file);
        if (mt !== (active.mtime || 0)) await reloadActive();
      } catch (e) { /* ignore */ }
    })();
  }, 2000));
  // Keep the live working/ready dots + tracked badges current.
  plugin.registerInterval(window.setInterval(() => {
    void applyTrackedBadges();
    const p = getPanel();
    if (!p || !p.contentEl) return;
    p.contentEl.querySelectorAll('[data-tc-session]')
      .forEach((d) => applyState(d, d.getAttribute('data-tc-session')));
  }, 2500));

  // Mounted NON-ACTIVE editors (embeds, background tabs) get no sidecar
  // mtime watch of their own, so a CLI write stayed invisible until
  // remount — and the stale field then persisted over it (incident
  // 2026-09-01). Watch their sidecars and re-sync the fields. Convergence
  // (observer-convergence contract): dispatches are diff-guarded, sync-
  // annotated (the persist listener skips them), and our own persists
  // just move the seen-mtime forward, so a quiet vault reaches zero
  // dispatches. Deferred while a user-driven persist is pending OR
  // mid-flight on the same file — the field is ahead of disk then, not
  // behind. (embedSyncSeen itself is declared beside
  // persistNonActiveStore, which deletes entries to wake this watcher.)
  let embedSyncBusy = false;
  const embedSyncFails = new Map();  // path → consecutive non-converged ticks
  const resyncNonActiveEditors = async () => {
    if (embedSyncBusy) return;
    embedSyncBusy = true;
    try {
      const { MarkdownView } = require('obsidian');
      const targets = new Map();   // path → { file, cms: [] } (a tab AND an embed can both show it)
      const addTarget = (file, cm) => {
        let t = targets.get(file.path);
        if (!t) { t = { file, cms: [] }; targets.set(file.path, t); }
        if (!t.cms.includes(cm)) t.cms.push(cm);
      };
      for (const leaf of app.workspace.getLeavesOfType('markdown')) {
        const v = leaf.view;
        if (v instanceof MarkdownView && v.file && v.editor) {
          const cm = cmOf(v.editor);
          if (cm) addTarget(v.file, cm);
        }
      }
      const m = plugin._embedEditorFiles;
      if (m) {
        for (const [cm, comp] of m) {
          const f = comp && comp.getFile && comp.getFile();
          if (f && cm && cm.dom && cm.dom.isConnected) addTarget(f, cm);
        }
      }
      if (embedSyncSeen.size > 500) embedSyncSeen.clear();
      const opSig = (list) => (list || []).map((o) =>
        `${o.id}@${o.from}+${(o.newText || '').length}-${(o.oldText || '').length}`).join(',');
      const cSig = (list) => (list || []).map((c) => commentSig(c)).join('|');
      const skipBusy = (file) => nonActiveTimers.has(file.path) || nonActivePersisting.has(file.path);
      for (const { file, cms } of targets.values()) {
        if (active && active.file === file) continue;   // the active machinery owns it
        if (skipBusy(file)) continue;                    // user edit / persist in flight
        const mt = await storeMtime(app, file);
        if (embedSyncSeen.get(file.path) === mt) continue;
        const entry = pendingByPath.get(file.path);
        // Signature of the armed entry at capture time — a resolution
        // armed during this tick's awaits means `entry`'s filtering is
        // stale and the dispatch below could resurrect it (round 3).
        const armedSigOf = (e) => (e ? `${e.ops.size}:${e.detached.size}:${e.comments.size}` : '0:0:0');
        const armedSig0 = armedSigOf(entry);
        // A permanently divergent buffer (normalization difference)
        // would otherwise re-read the note + sidecar every tick forever
        // — bound it like reloadActive/scheduleNonActivePersist do (8),
        // then give up until the sidecar mtime moves again.
        const fails = embedSyncFails.get(file.path) || 0;
        if (fails >= 8) {
          console.warn(`[track-changents] ${file.path}: embed resync gave up after 8 divergent ticks (buffer≠disk); will retry on the next sidecar write`);
          embedSyncFails.delete(file.path);
          embedSyncSeen.set(file.path, mt);
          // A gate-deferred persist waiting on this file would strand
          // (round 4) — fold its armed resolutions to disk directly, the
          // one write path that needs no editor convergence.
          if (persistAfterResync.delete(file.path)) await foldResolvedToDisk(file.path);
          continue;
        }
        const on = await isFileTracked(app, file);
        let synced = true;   // only advance the seen-mtime when every editor converged
        for (const cm of cms) {
          if (!cm.dom || !cm.dom.isConnected) continue;
          if (!mt) {
            // Sidecar GONE (foreign delete: a CLI or peer machine
            // resolved everything). An editor that ingested ops from it
            // must clear, or its next keystroke-persist recreates the
            // whole resolved batch (round 2, 2026-09-01). Only entries
            // this editor got FROM DISK clear — anything else stays.
            const knewOps = cm._tcKnownIds && cm._tcKnownIds.size;
            const knewComments = cm._tcKnownCommentIds && cm._tcKnownCommentIds.size;
            if (!cm._tcHydrated || (!knewOps && !knewComments)) {
              // The editor has now OBSERVED the absent generation — the
              // stamp must say so (round 4: a stale nonzero stamp here
              // made the persist gate defer and this branch skip, in
              // alternation, forever; C4 says absent is a fine state).
              if (cm._tcHydrated) cm._tcSidecarMtime = 0;
              continue;
            }
            const fieldOps = suggestionsFieldRef.f
              ? (cm.state.field(suggestionsFieldRef.f, false) || []) : [];
            const meta = metaFieldRef.f ? cm.state.field(metaFieldRef.f, false) : null;
            const known = cm._tcKnownIds || new Set();
            const baseOf = (id) => String(id).replace(/([~#]p?\d+)+$/, '');
            const keep = fieldOps.filter((o) => {
              const id = String(o && o.id);
              return !known.has(id) && !known.has(baseOf(id));
            });
            const knownC = cm._tcKnownCommentIds || new Set();
            const keepC = ((meta && meta.comments) || []).filter((c) => !knownC.has(String(c && c.id)));
            if (keep.length === fieldOps.length
                && keepC.length === ((meta && meta.comments) || []).length) {
              cm._tcSidecarMtime = 0;   // nothing to clear, but the absence is now ingested
              continue;
            }
            if (skipBusy(file) || (active && active.file === file)) { synced = false; break; }
            cm.dispatch({
              effects: [setSuggestions.of(keep), setTrackMeta.of({ trackingOn: on, comments: keepC })],
              annotations: [Transaction.addToHistory.of(false), syncAnnotation.of(true)],
            });
            cm._tcKnownIds = new Set();
            cm._tcKnownCommentIds = new Set();
            cm._tcSidecarMtime = 0;
            const p = getPanel(); if (p) p.notifyChanged();
            continue;
          }
          if (!(await bufferMatchesDisk(file, cm, { quiet: true }))) { synced = false; continue; }
          const cur = cm.state.doc.toString();
          const store = await loadStore(app, file, cur);
          if (!store) { synced = false; continue; }   // mt raced the delete — next tick
          // Deliberate resolutions awaiting their persist must not
          // resurrect through this dispatch (C2).
          applyPendingResolved(store, entry);
          const fieldOps = suggestionsFieldRef.f
            ? (cm.state.field(suggestionsFieldRef.f, false) || []) : [];
          const fieldSig = opSig(fieldOps);
          const meta = metaFieldRef.f ? cm.state.field(metaFieldRef.f, false) : null;
          if (fieldSig === opSig(store.suggestions)
              && cSig((meta && meta.comments) || []) === cSig(store.comments)) {
            cm._tcSidecarMtime = mt;
            stampKnownIds(cm, store);
            continue;
          }
          // SYNCHRONOUS re-verify after the awaits above (round 2): a
          // resolution clicked or a keystroke landed mid-tick, or the
          // tab became active — dispatching the pre-move snapshot would
          // undo it. No await may separate these checks from dispatch.
          if (skipBusy(file) || (active && active.file === file)
              || cm.state.doc.toString() !== cur
              || opSig(cm.state.field(suggestionsFieldRef.f, false) || []) !== fieldSig
              || armedSigOf(pendingByPath.get(file.path)) !== armedSig0) {
            synced = false; continue;
          }
          // Dispatch into THIS editor, not via cmForFile — the lookup
          // could keep picking a sibling editor of the same file and
          // never converge the one that diffed.
          cm.dispatch({
            effects: [setSuggestions.of(store.suggestions || []),
              setTrackMeta.of({ trackingOn: on, comments: store.comments || [] })],
            annotations: [Transaction.addToHistory.of(false), syncAnnotation.of(true)],
          });
          cm._tcHydrated = true;
          cm._tcSidecarMtime = mt;
          stampKnownIds(cm, store);
          const p = getPanel(); if (p) p.notifyChanged();
        }
        if (synced) {
          embedSyncSeen.set(file.path, mt);
          embedSyncFails.delete(file.path);
          // Gate-deferred persist handoff (round 3): the field now holds
          // the current sidecar generation, so the persist can pass the
          // gate and flush the armed resolutions / keystroke ops.
          if (persistAfterResync.delete(file.path)) scheduleNonActivePersist(file);
        } else {
          embedSyncFails.set(file.path, fails + 1);
        }
      }
      // Armed resolutions of files with NO mounted editor (a panel
      // resolve on a collapsed embed whose write deferred) have no
      // persist path and no handoff — they only folded on the next
      // active-file switch, and quit-before-switch resurrected them
      // (round 5). Drain them here: the fold is an editor-free disk
      // read-modify-write, so no convergence gate applies.
      for (const path of [...pendingByPath.keys()]) {
        if (targets.has(path)) continue;                    // mounted → the persist/handoff owns it
        if (active && active.file && active.file.path === path) continue;
        if (nonActiveTimers.has(path) || nonActivePersisting.has(path)) continue;
        if (await foldResolvedToDisk(path)) { bumpRollupGen(); scheduleRollupPush(); }
      }
    } catch (e) { /* best effort; next tick retries */ }
    finally { embedSyncBusy = false; }
  };
  plugin.registerInterval(window.setInterval(() => { void resyncNonActiveEditors(); }, 2500));
  void applyTrackedBadges();

  const addComment = async () => {
    // Same rule the mouse paths use: if the review UI is on screen — tracking on,
    // OR tracking off with changes still pending — commenting works. A bare
    // isEnabled check made this silently do nothing in a state the panel is
    // actively rendering.
    if (!isEnabled(plugin) && orderedHunks().length === 0) return;
    const ed = activeMarkdownEditor(app);
    if (!ed || !ed.file) return;
    const cm = cmOf(ed.editor); if (!cm) return;
    const sel = cm.state.selection.main;
    if (sel.from === sel.to) return;
    const cur = cm.state.doc.toString();
    const anchor = track.makeAnchor(cur, sel.from, sel.to);
    new CommentModal(app, anchor.quote, async (body) => {
      if (!active || active.file !== ed.file) await pushActive();
      if (!active || active.file !== ed.file) return;
      active.store.comments.push({ id: `${Date.now()}-${Math.round(sel.from)}`, author: 'you', ts: Date.now(), anchor, body, replies: [], resolved: false });
      await commitComments(ed.file);
      void openPanel();
    }).open();
  };

  // Cmd-M "message the editor" → a persistent anchored COMMENT THREAD.
  // Works for NON-ACTIVE files too (a selection inside an EMBED editor —
  // user report 2026-08-24): the comment then writes to the embedded
  // note's own sidecar via the same gated path the panel's whole-tree
  // review uses, and the outer page's panel shows it in that note's
  // section.
  plugin._trackMessageComment = async (file, range, body, target) => {
    if (!file || !(body && body.trim())) return null;
    const cm = cmForFile(file);
    const cur = cm ? cm.state.doc.toString() : currentText(file);
    if (cur == null && !(active && active.file === file)) {
      // No live editor and not active — fall through to the sidecar path
      // below, which reads disk itself.
    } else if (cur == null) return null;
    const at = (range && range.from != null) ? Math.round(range.from) : 'msg';
    const comment = {
      id: `${Date.now()}-${at}`,
      author: 'you', ts: Date.now(), body: body.trim(),
      replies: [], resolved: false,
      pingAuthor: (target && target !== 'you') ? target : null,
    };
    if (cur != null && range && range.from != null && range.to != null && range.to > range.from) {
      // Anchor from the editor's own text — the offsets are ITS
      // coordinates; the content anchor re-locates against disk on load.
      comment.anchor = track.makeAnchor(cur, range.from, range.to);
    }
    if (active && active.file === file) {
      active.store.comments.push(comment);
      await commitComments(file);
    } else {
      await mutateStoreInFile(file, (store) => {
        if (!Array.isArray(store.comments)) store.comments = [];
        store.comments.push(comment);
      });
      bumpRollupGen(); scheduleRollupPush();
      const p = getPanel(); if (p) p.notifyChanged();
    }
    void openPanel();
    return comment.id;
  };

  // Stamp a comment thread as FORKED (user ask 2026-08-31): the Cmd-M
  // dispatch ran on a parallel branch of the target session — the card
  // shows a badge and a "Branch out" button that promotes the branch to
  // a first-class session via the kernel.
  plugin._trackSetCommentFork = async (file, id, fork) => {
    const setIt = (store) => {
      const c = (store.comments || []).find((x) => String(x.id) === String(id));
      if (c) c.fork = fork;
      return !!c;
    };
    if (active && active.file === file) {
      if (setIt(active.store)) await commitComments(file);
      return;
    }
    await mutateStoreInFile(file, (store) => { setIt(store); });
    const p = getPanel(); if (p) p.notifyChanged();
  };

  // Cmd-M default: an EPHEMERAL "pending message" (kind:'message') anchored to the
  // selection — a blue highlight + auto-resolving side card. Clears when the
  // anchored text changes (the edit landed), or via the card's Dismiss button.
  plugin._trackPendingMessage = async (file, range, body, target) => {
    if (!file || !(body && body.trim())) return null;
    const cm = cmForFile(file);
    const cur = cm ? cm.state.doc.toString() : currentText(file);
    if (cur == null) return null;
    if (!(range && range.from != null && range.to != null && range.to > range.from)) return null;
    const marker = {
      id: `${Date.now()}-${Math.round(range.from)}`,
      kind: 'message',
      author: 'you', ts: Date.now(), body: body.trim(),
      anchor: track.makeAnchor(cur, range.from, range.to),
      pingAuthor: (target && target !== 'you') ? target : null,
      replies: [], resolved: false,
    };
    if (active && active.file === file) {
      active.store.comments.push(marker);
      await commitComments(file);
    } else {
      // A selection inside an EMBED editor: the marker lives in that
      // note's sidecar (its editor renders the blue highlight via the
      // meta sync inside mutateStoreInFile).
      await mutateStoreInFile(file, (store) => {
        if (!Array.isArray(store.comments)) store.comments = [];
        store.comments.push(marker);
      });
      bumpRollupGen(); scheduleRollupPush();
      const p = getPanel(); if (p) p.notifyChanged();
    }
    void openPanel();
    return marker.id;
  };

  // Toggle tracking for the ACTIVE FILE by adding/removing its exact path in the
  // shared list. Guarded (`toggling`) so a config poll / leaf-change can't clobber
  // the in-flight flip, and the panel button disables itself during the await. No
  // blocking popups.
  const toggle = async () => {
    const file = activeMarkdownFile() || (active && active.file);
    if (!file) return;
    toggling = true;
    try {
      const list = await loadTrackedList(app);
      const next = list.includes(file.path) ? list.filter((p) => p !== file.path) : [...list, file.path];
      await saveTrackedList(app, next);
      void applyTrackedBadges();
      plugin._trackEnabled = track.isTracked(next, file.path);
      await pushActive();
    } finally {
      toggling = false;
    }
  };

  const toggleFolder = async () => {
    const file = activeMarkdownFile() || (active && active.file);
    if (!file) return;
    const dir = file.parent && file.parent.path ? file.parent.path : '';
    if (!dir || dir === '/' || dir === '.') return;   // vault root refused (would be vault-wide)
    const entry = dir.replace(/\/+$/, '') + '/';
    toggling = true;
    try {
      const list = await loadTrackedList(app);
      const next = list.includes(entry) ? list.filter((p) => p !== entry) : [...list, entry];
      await saveTrackedList(app, next);
      void applyTrackedBadges();
      plugin._trackEnabled = track.isTracked(next, file.path);
      await pushActive();
    } finally {
      toggling = false;
    }
  };

  // The display hunks for the active note, ordered by position — the same units the
  // overlay/panel show, so ⌘⇧A/⌘⇧R at the cursor act on the same collapsed item.
  const orderedHunks = () => {
    const ctx = host.activeContext();
    if (!ctx) return [];
    return logic.planDiffDisplay(track.toHunks(ctx.ops), ctx.baseline, ctx.current)
      .sort((a, b) => a.curFrom - b.curFrom);
  };
  // Tracking OFF with changes still pending is a supported state — the overlay
  // and panel deliberately keep rendering (shouldShowTrackUI), and every MOUSE
  // path honours that. Gating the keyboard on isEnabled alone meant ⌘⇧A/⌘⇧R
  // silently did nothing in exactly that state, with no feedback at all. Match
  // what the user can see.
  const canResolveNow = () => isEnabled(plugin) || orderedHunks().length > 0;
  const resolveAtCursor = async (reject) => {
    if (!canResolveNow()) return;
    const ed = activeMarkdownEditor(app);
    const cm = ed && ed.editor ? cmOf(ed.editor) : null;
    if (!cm) return;
    const pos = cm.state.selection.main.head;
    const h = logic.changeForCursor(orderedHunks(), pos);
    if (!h) return;
    const at = h.curFrom;
    await host.resolveInline(at, reject);
    const remaining = orderedHunks();
    const nextH = remaining.find((x) => x.curFrom >= at) || remaining[0];
    if (nextH) reveal(nextH.curFrom);
  };

  // Move between changes WITHOUT resolving one. Until now the only way to reach
  // the next change was to accept or reject the current one — so skimming a diff
  // meant scrolling by hand. Wraps at both ends; flashes the target the way the
  // panel flashes a focused card, so you can see where you landed.
  const gotoChange = (dir) => {
    if (!canResolveNow()) return;
    const ed = activeMarkdownEditor(app);
    const cm = ed && ed.editor ? cmOf(ed.editor) : null;
    if (!cm) return;
    const hunks = orderedHunks();
    if (!hunks.length) return;
    const pos = cm.state.selection.main.head;
    const target = dir > 0
      ? (hunks.find((h) => h.curFrom > pos) || hunks[0])
      : ([...hunks].reverse().find((h) => h.curFrom < pos) || hunks[hunks.length - 1]);
    if (target) reveal(target.curFrom);
  };

  plugin.addCommand({ id: 'tc-track-toggle', name: 'Track changes: toggle tracking (this file)', callback: () => void toggle() });
  plugin.addCommand({ id: 'tc-track-next', name: 'Track changes: next change',
    hotkeys: [{ modifiers: ['Mod', 'Shift'], key: ']' }], editorCallback: () => gotoChange(1) });
  plugin.addCommand({ id: 'tc-track-prev', name: 'Track changes: previous change',
    hotkeys: [{ modifiers: ['Mod', 'Shift'], key: '[' }], editorCallback: () => gotoChange(-1) });
  plugin.addCommand({ id: 'tc-track-accept-cursor', name: 'Track changes: accept change at cursor (and go to next)',
    hotkeys: [{ modifiers: ['Mod', 'Shift'], key: 'a' }], editorCallback: () => void resolveAtCursor(false) });
  plugin.addCommand({ id: 'tc-track-reject-cursor', name: 'Track changes: reject change at cursor (and go to next)',
    hotkeys: [{ modifiers: ['Mod', 'Shift'], key: 'r' }], editorCallback: () => void resolveAtCursor(true) });
  plugin.addCommand({ id: 'tc-track-toggle-folder', name: 'Track changes: toggle tracking (this folder)', callback: () => void toggleFolder() });
  plugin.addCommand({ id: 'tc-track-panel', name: 'Track changes: open panel', callback: () => void openPanel() });
  plugin.addCommand({ id: 'tc-track-accept-all', name: 'Track changes: accept all', callback: () => void host.acceptAll() });
  plugin.addCommand({ id: 'tc-track-reject-all', name: 'Track changes: reject all', callback: () => void host.rejectAll() });
  plugin.addCommand({ id: 'tc-track-comment', name: 'Track changes: comment on selection', editorCallback: () => void addComment() });
}

module.exports = { register, makeExtension, buildDecorations,
  // Test-only handles for the sidecar I/O protocol (2026-09-01): these
  // functions carry the no-silent-loss invariants and were previously
  // exercised only by ad-hoc repro scripts.
  _io: { deleteStore, saveStore, normalizeStore, emptyStore } };
