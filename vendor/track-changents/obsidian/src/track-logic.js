'use strict';

// The track-changes slice of the host's pure logic: click policy, inline
// removal layout, UI visibility, compose-box policy, frontmatter bounds,
// kept-embed segmentation — plus the display-planning functions re-exported
// from the shared trackchanges core so call sites and tests read them off
// one module. Everything here is PURE (no obsidian, no DOM) and
// unit-tested in tests/track-logic.test.mjs.

// How a compose textarea (reply box, message/comment modal) should treat a
// keydown: plain Enter SENDS; Shift+Enter and ⌘/Ctrl+Enter insert a NEWLINE;
// anything else is left to the browser. Pure so it's unit-tested without a DOM;
// the thin glue that applies it lives in compose-keys.js. Returns
// 'send' | 'newline' | 'ignore'.
function composeEnterAction(e) {
  if (!e || e.key !== 'Enter') return 'ignore';
  if (e.shiftKey || e.metaKey || e.ctrlKey) return 'newline';
  return 'send';
}

// What an inline diff click does, by modifier:
//   • Ctrl held       → 'jump'   (go to this change's panel card to reply — NOT reject)
//   • Cmd/Option held → 'reject'
//   • otherwise       → 'accept'
// Ctrl deliberately does not reject. Pure so the policy is unit-tested in one place
// and the green-addition and struck-removal click handlers can't drift apart.
function diffClickAction(e) {
  if (e && e.ctrlKey) return 'jump';
  if (e && (e.metaKey || e.altKey)) return 'reject';
  return 'accept';
}

// Diff-display planning + accept/reject-at-cursor targeting live in the SHARED
// trackchanges core (display.js, next to the engine) so the VS Code extension
// groups paragraph rewrites with the SAME rules; re-exported below so plugin
// call sites and tests keep reading them off logic.
const {
  isInlineRemoval, changeForCursor, paragraphRange, planDiffDisplay, idsOf,
} = require('track-changents/display');

// Pack the floating "struck text above the word" boxes for ONE wrap row so they neither
// overlap each other nor spill past the text column. `items` are the row's boxes in any
// order, each { ax, w, h }: ax = the box's anchor x (the new run's left, in content
// coords), w/h = the box's measured size. `contentW` = the text column width. Returns
// `{ height, placed }` where `placed[i]` = { left, top } for items[i] (left RELATIVE to
// its anchor; top within the opened space) and `height` is the space every anchor on the
// row must open above itself. Each box is clamped into [0, contentW]; boxes that still
// overlap horizontally stack into LANES (lane 0 just above the text, extras above it).
// Pure, so the packing is unit-tested without a DOM; the ViewPlugin only measures + applies.
const INLINE_DEL_LANE_GAP = 5;   // vertical gap added to the tallest box → lane height
const INLINE_DEL_ROW_GAP = 5;    // gap above the top lane and below the bottom lane
const INLINE_DEL_MIN_SEP = 6;    // min horizontal gap to treat two boxes as non-overlapping
// `lineH` is the height of the line's OWN text (the new/green run on that wrap row). The
// struck boxes sit baseline-aligned, so the box's bottom is the line's baseline — but the
// line's glyphs rise ~one ascent ABOVE that baseline. We must therefore reserve `lineH`
// BELOW the struck stack, or the lowest struck box lands on top of the line's own text (the
// overlap bug — worse for headings, whose ascent is tall). Default 0 keeps the pure math
// testable without a measured line height.
function layoutInlineRemovals(items, contentW, lineH) {
  const n = Array.isArray(items) ? items.length : 0;
  const placed = new Array(n);
  if (!n) return { height: 0, placed };
  const reserve = Math.max(0, lineH || 0);
  const order = items.map((_, i) => i).sort((a, b) => items[a].ax - items[b].ax);
  const laneH = Math.max(...items.map((it) => it.h)) + INLINE_DEL_LANE_GAP;
  const laneEnd = [];           // current right edge (content-x) per lane
  const lane = new Array(n);
  const left = new Array(n);
  let maxLane = 0;
  for (const i of order) {
    const it = items[i];
    const x = Math.max(0, Math.min(it.ax, contentW - it.w));   // clamp into the text column
    let k = 0;
    while (k < laneEnd.length && x < laneEnd[k] + INLINE_DEL_MIN_SEP) k++;
    laneEnd[k] = x + it.w;
    maxLane = Math.max(maxLane, k);
    lane[i] = k;
    left[i] = x;
  }
  // height = top gap + the lane stack + the line's own text height reserved at the bottom,
  // so the whole struck stack clears the line's glyphs and can't overlap them.
  const height = INLINE_DEL_ROW_GAP * 2 + (maxLane + 1) * laneH + reserve;
  for (let i = 0; i < n; i++) {
    placed[i] = { left: left[i] - items[i].ax, top: INLINE_DEL_ROW_GAP + (maxLane - lane[i]) * laneH };
  }
  return { height, placed };
}

// Whether to render the track-changes UI (inline overlay + panel diff) for a file.
// ALWAYS when tracking is ON; ALSO when it's OFF but the file still has UNRESOLVED
// changes or comments — so reopening a note (or reloading Obsidian) with the toggle off
// still lets you see and resolve what's pending. The toggle then governs only whether
// NEW edits get tracked, not the visibility of already-pending ones. Pure (the plugin
// passes the change/comment counts it has already computed) so the rule is unit-tested.
function shouldShowTrackUI(trackingOn, pendingChangeCount, commentCount) {
  if (trackingOn) return true;
  return (pendingChangeCount || 0) > 0 || (commentCount || 0) > 0;
}

// Clamp a dragged box's new position on ONE axis into the viewport: base + delta, but never
// before 0 nor past (viewSize - boxSize) so the box can't be dragged off-screen. Pure so the
// drag math is unit-tested — the pointer wiring in diff-rewrite's compose modal needs a
// browser and isn't.
function clampDragAxis(base, delta, boxSize, viewSize) {
  const max = Math.max(0, (viewSize || 0) - (boxSize || 0));
  return Math.max(0, Math.min((base || 0) + (delta || 0), max));
}

// Pick the default Cmd-M target session: the FIRST of these candidates that is still alive —
//   1. perNote     — the session I last MESSAGED about THIS note (persisted)
//   2. noteEditors — whoever most recently EDITED this note (most-recent-first; from the store)
//   3. global      — my usual last-messaged session, any note (persisted)
//   4. lastInMemory— my last pick this session (pre-persistence speed path)
// then the first alive session, else null (→ caller offers "New session"). So after a reload
// Cmd-M still lands on the live session I was working with, with no dropdown trip. Pure so the
// precedence is unit-tested; persistence + liveness are resolved by the caller.
function chooseMessageTarget(alive, candidates = {}) {
  const live = new Set(Array.isArray(alive) ? alive : []);
  const ok = (n) => !!n && live.has(n);
  const { perNote, noteEditors, global, lastInMemory } = candidates;
  if (ok(perNote)) return perNote;
  const ed = (Array.isArray(noteEditors) ? noteEditors : []).find(ok);
  if (ed) return ed;
  if (ok(global)) return global;
  if (ok(lastInMemory)) return lastInMemory;
  return (Array.isArray(alive) && alive[0]) || null;
}

// The Cmd-M compose box opens BEFORE the first sessions fetch resolves — a
// remote host can take seconds to answer, and the box is where typing starts
// (user 2026-08-16: the box must pop immediately and say loading, never wait
// on the server). These two pure helpers pin that contract for the modal:
//
// What the session-picker trigger shows: a resolved selection always wins
// (even while a refresh is still in flight); otherwise "loading" until the
// first fetch settles; "empty" only after it settled with nothing.
function composeTriggerState({ loading, selected } = {}) {
  if (selected != null) return 'selected';
  return loading ? 'loading' : 'empty';
}

// What a SEND gesture does given the draft and target state (composeEnterAction
// above decides send-vs-newline from the keystroke; this decides what a send
// means): an empty draft dismisses the box; a typed draft with no target yet
// HOLDS (the box stays open, the draft is never dropped on the floor while the
// session table loads); a draft with a target submits.
function composeSendAction({ text, selected } = {}) {
  if (!text || !String(text).trim()) return 'dismiss';
  return selected == null ? 'hold' : 'submit';
}

// Character length of the leading YAML frontmatter block including its
// closing delimiter line (0 when the text has none). Used by the track
// overlay to keep inline suggestion widgets out of the frontmatter in
// Live Preview, where the Properties UI replaces those lines and a
// widget floats with no readable context.
function frontmatterEnd(text) {
  const m = /^---\r?\n[\s\S]*?\r?\n---(?:\r?\n|$)/.exec(String(text == null ? '' : text));
  return m ? m[0].length : 0;
}


// ── moved-embed detection (2026-08-25, update_writer report) ─────────
// A tracked edit that MOVES an `![[embed]]` to another line renders as
// delete+add, and the struck red `![[img.png]]` reads as "the picture
// is being deleted". These helpers let the deletion renderer show an
// embed token that still exists VERBATIM in the current note as kept —
// un-struck, tagged "moved" — instead of deleted.
const EMBED_TOKEN_RE = /!\[\[[^\]]+\]\]/g;

// The embed tokens of `text` that also appear in `current`.
function keptEmbedTokens(text, current) {
  const cur = String(current || '');
  const out = [];
  const seen = new Set();
  for (const m of String(text || '').matchAll(EMBED_TOKEN_RE)) {
    const tok = m[0];
    if (!seen.has(tok) && cur.includes(tok)) { seen.add(tok); out.push(tok); }
  }
  return out;
}

// Split a line into segments: { text, kept } — kept segments are embed
// tokens from `keptTokens`, in place, so a renderer can style them
// separately from the genuinely deleted text around them.
function segmentsByKeptTokens(line, keptTokens) {
  const l = String(line || '');
  if (!keptTokens || !keptTokens.length) return [{ text: l, kept: false }];
  const kept = new Set(keptTokens);
  const segs = [];
  let last = 0;
  for (const m of l.matchAll(EMBED_TOKEN_RE)) {
    if (!kept.has(m[0])) continue;
    if (m.index > last) segs.push({ text: l.slice(last, m.index), kept: false });
    segs.push({ text: m[0], kept: true });
    last = m.index + m[0].length;
  }
  if (last < l.length) segs.push({ text: l.slice(last), kept: false });
  return segs.length ? segs : [{ text: l, kept: false }];
}


module.exports = {
  composeEnterAction,
  diffClickAction,
  isInlineRemoval, changeForCursor, paragraphRange, planDiffDisplay, idsOf,
  layoutInlineRemovals,
  shouldShowTrackUI,
  clampDragAxis,
  composeTriggerState,
  composeSendAction,
  frontmatterEnd,
  keptEmbedTokens,
  segmentsByKeptTokens,
};
