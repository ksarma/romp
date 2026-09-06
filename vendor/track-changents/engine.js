'use strict';

// Pure engine for the OP-LOG track-changes model (v3).
//
// The on-disk note is the CURRENT text: the document as it reads with every
// pending suggestion APPLIED (insertions present, replacements swapped in,
// deletions removed). Alongside it a sidecar holds an ordered list of
// SUGGESTIONS, each an attributed operation expressed in CURRENT-text
// coordinates:
//
//   { id, author, ts, kind:'ins'|'del'|'sub', from, newText, oldText, anchor }
//     ins : current[from .. from+newText.length] is pending-inserted text.  oldText=''
//     del : at point `from`, `oldText` was removed (not present in current).  newText=''
//     sub : current[from .. from+newText.length] replaced `oldText`.
//   anchor {prefix,quote,suffix} re-locates the op if the file is edited by
//   another tool while the store is closed.
//
// The defining choice vs. the old snapshot-diff engine: authorship is RECORDED
// at the moment an edit happens, never reconstructed by diffing two texts. The
// human's own edits are observed (a CodeMirror change, or the reverse of an
// accept/reject) and fold in as plain text — they are never tracked. Only an
// agent's edit adds a tracked suggestion. Because every edit is a known change,
// each pending op is MAPPED through it (shift / shrink / split) instead of the
// whole document being re-diffed — so attribution can't flip and cost is
// O(pending ops), not O(document) per keystroke.
//
// No imports: unit-tested in node, bundled into the plugin, run by the CLIs.
// Keep it free of Obsidian / CodeMirror so the same logic runs everywhere.

// ── tokenization + 2-way word diff (kept for migration + the agent CLI) ──
// Still useful: turning an opaque old->new text pair into ops (CLI, v1
// migration). NOT used on the hot path — live editing maps ops through the
// exact change instead of diffing.

// The `u` flag makes `[^\w\s]` match a whole CODE POINT rather than a UTF-16
// code unit, so an emoji is one token instead of two lone surrogates. Without it
// a changed emoji produced a hunk boundary in the middle of a surrogate pair —
// an offset no editor can render or slice correctly.
function tokenizeWords(s) {
  return s.match(/\w+|\s+|[^\w\s]/gu) || [];
}

function splitLinesKeep(s) {
  return s.match(/[^\n]*\n|[^\n]+$/g) || (s === '' ? [] : [s]);
}

function lcsOps(a, b, eq, weight) {
  const n = a.length;
  const m = b.length;
  const w = weight || (() => 1);
  const dp = [];
  for (let i = 0; i <= n; i++) dp.push(new Uint32Array(m + 1));
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      const match = eq(a[i], b[j]) ? dp[i + 1][j + 1] + w(a[i]) : 0;
      const skip = dp[i + 1][j] >= dp[i][j + 1] ? dp[i + 1][j] : dp[i][j + 1];
      dp[i][j] = match >= skip ? match : skip;
    }
  }
  const ops = [];
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (eq(a[i], b[j]) && dp[i][j] === dp[i + 1][j + 1] + w(a[i])) {
      ops.push({ type: 'eq', ai: i, bj: j }); i++; j++;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) { ops.push({ type: 'del', ai: i }); i++; }
    else { ops.push({ type: 'ins', bj: j }); j++; }
  }
  while (i < n) { ops.push({ type: 'del', ai: i }); i++; }
  while (j < m) { ops.push({ type: 'ins', bj: j }); j++; }
  return ops;
}

const STR_EQ = (x, y) => x === y;

function tokenOps(aText, bText) {
  const a = tokenizeWords(aText);
  const b = tokenizeWords(bText);
  return lcsOps(a, b, STR_EQ, (t) => t.length).map((o) => (
    o.type === 'eq' ? { type: 'eq', text: a[o.ai] }
      : o.type === 'del' ? { type: 'del', text: a[o.ai] }
        : { type: 'ins', text: b[o.bj] }
  ));
}

function trimTrailingWs(line) {
  return line.replace(/[ \t]+(\n?)$/, '$1');
}

function rawOps(baseline, current) {
  const aLines = splitLinesKeep(baseline);
  const bLines = splitLinesKeep(current);
  const lineEq = (x, y) => x === y || trimTrailingWs(x) === trimTrailingWs(y);
  const aN = aLines.length;
  const bN = bLines.length;
  let lo = 0;
  const minN = Math.min(aN, bN);
  while (lo < minN && lineEq(aLines[lo], bLines[lo])) lo++;
  let aHi = aN;
  let bHi = bN;
  while (aHi > lo && bHi > lo && lineEq(aLines[aHi - 1], bLines[bHi - 1])) { aHi--; bHi--; }

  const ops = [];
  let pendA = '';
  let pendB = '';
  const flush = () => {
    if (pendA || pendB) for (const o of tokenOps(pendA, pendB)) ops.push(o);
    pendA = '';
    pendB = '';
  };
  const emitEq = (a, b) => {
    flush();
    if (a === b) ops.push({ type: 'eq', text: a });
    else for (const t of tokenOps(a, b)) ops.push(t);
  };
  for (let i = 0; i < lo; i++) emitEq(aLines[i], bLines[i]);
  const lineOps = lcsOps(aLines.slice(lo, aHi), bLines.slice(lo, bHi), lineEq);
  for (const o of lineOps) {
    if (o.type === 'eq') emitEq(aLines[lo + o.ai], bLines[lo + o.bj]);
    else if (o.type === 'del') pendA += aLines[lo + o.ai];
    else pendB += bLines[lo + o.bj];
  }
  flush();
  for (let k = 0; aHi + k < aN; k++) emitEq(aLines[aHi + k], bLines[bHi + k]);
  return ops;
}

// 2-way change set: baseline vs current -> [{kind,baseFrom,baseTo,curFrom,curTo,oldText,newText}].
// Used to seed ops from an opaque before/after pair (CLI without explicit spans,
// v1 migration). Coalesces whitespace-separated hunks and drops pure-whitespace
// reflow so a rewrap isn't reported as a change.
function changeSet(baseline, current) {
  const ops = rawOps(baseline, current);
  const hunks = [];
  let aOff = 0;
  let bOff = 0;
  let run = null;
  const flush = () => {
    if (!run) return;
    const kind = run.oldText && run.newText ? 'sub' : (run.newText ? 'ins' : 'del');
    hunks.push({
      kind,
      baseFrom: run.aFrom, baseTo: run.aFrom + run.oldText.length,
      curFrom: run.bFrom, curTo: run.bFrom + run.newText.length,
      oldText: run.oldText, newText: run.newText,
    });
    run = null;
  };
  for (const op of ops) {
    if (op.type === 'eq') { flush(); aOff += op.text.length; bOff += op.text.length; }
    else {
      if (!run) run = { aFrom: aOff, bFrom: bOff, oldText: '', newText: '' };
      if (op.type === 'del') { run.oldText += op.text; aOff += op.text.length; }
      else { run.newText += op.text; bOff += op.text.length; }
    }
  }
  flush();
  return hunks
    .filter((h) => h.oldText !== h.newText)
    .filter((h) => !(/^\s*$/.test(h.oldText) && /^\s*$/.test(h.newText)));
}

// ── op-log geometry ─────────────────────────────────────────────────

// A suggestion's occupied span in current text: [from, from+newText.length].
// A del is a zero-width point (newText === '').
function span(s) {
  const len = s.newText ? s.newText.length : 0;
  return { a: s.from, b: s.from + len };
}

// Kind implied by the text pair, so callers never have to keep `kind` in sync.
function kindOf(oldText, newText) {
  return oldText && newText ? 'sub' : (newText ? 'ins' : 'del');
}

// Order ops for REVERSAL (reject / baseline reconstruction): highest offset first
// so an earlier revert never reindexes a later one, and — at the SAME offset — the
// WIDER span first. That tie-break matters when a zero-width deletion point shares
// an offset with the left edge of another (different-author, so un-coalesced) op:
// the wide op must be reverted before the del re-inserts its text at the point, or
// the del's insertion shifts the coordinates the wide revert relied on and the
// reconstructed baseline is corrupted.
// The width tie-break above resolves a del-point sitting at the left edge of a
// wider op. When several zero-width ops (e.g. two different-author deletion points)
// pile onto the SAME offset their spatial order in the baseline is genuinely
// ambiguous — nothing in the op model records it — so fall through to ts then id
// purely to make baselineOf a DETERMINISTIC function of the op set (independent of
// array order), not a claim about which struck-out deletion "really" came first.
function reversalOrder(x, y) {
  if (y.from !== x.from) return y.from - x.from;
  const wy = span(y).b - span(y).a;
  const wx = span(x).b - span(x).a;
  if (wy !== wx) return wy - wx;
  if ((x.ts || 0) !== (y.ts || 0)) return (x.ts || 0) - (y.ts || 0);
  return String(x.id) < String(y.id) ? -1 : String(x.id) > String(y.id) ? 1 : 0;
}

// Merge adjacent same-author ops (one's end === the next's start) into a single
// op — the behaviour Word/CKEditor/Tiptap all have. This both re-fuses the two
// halves a mid-op deletion leaves behind and fuses a same-author delete+insert at
// one point into a substitution. Different authors are never merged (that would
// be exactly the mis-attribution we are eliminating).
function coalesceOps(ops) {
  const sorted = [...ops].sort((x, y) => x.from - y.from
    || (span(x).b - span(x).a) - (span(y).b - span(y).a));
  const out = [];
  for (const s of sorted) {
    const prev = out[out.length - 1];
    if (prev && prev.author === s.author && span(prev).b === s.from) {
      const oldText = (prev.oldText || '') + (s.oldText || '');
      const newText = (prev.newText || '') + (s.newText || '');
      out[out.length - 1] = { ...prev, oldText, newText, kind: kindOf(oldText, newText),
        ts: Math.min(prev.ts || 0, s.ts || 0) };
    } else out.push({ ...s });
  }
  return out;
}

// Map a single point through a change {from,to,insert}. A point strictly inside
// the deleted range collapses to the change start.
function mapPoint(pos, ch) {
  const delta = ch.insert.length - (ch.to - ch.from);
  if (pos <= ch.from) return pos;
  if (pos >= ch.to) return pos + delta;
  return ch.from;
}

// Fold ONE change (from,to,insert) — a human keystroke, or the reverse of an
// accept/reject — into the pending ops, WITHOUT tracking it. Each op is shifted,
// shrunk, or split so it keeps pointing at the same text:
//   • change entirely before/after an op → shift / no-op
//   • change inside an op's inserted range → the op splits around it and the
//     changed middle becomes plain (untracked) text — this is exactly the case
//     the old engine got wrong (a human typing inside an agent suggestion used
//     to re-attribute the human's text to the agent).
// `mint(base, n)` supplies fresh ids for the right half of a split.
// `deferCoalesce` returns the raw (un-coalesced) ops so a caller that is about to
// add ANOTHER op at the seam (recordAgentEdit) can coalesce once, with that op
// present — otherwise two same-author ops the change made adjacent would fuse
// BEFORE the new op lands between them, burying it inside the merged span.
function mapOpsThroughChange(suggestions, ch, mint, deferCoalesce) {
  const delta = ch.insert.length - (ch.to - ch.from);
  const out = [];
  let splitN = 0;
  // Split ids must be unique across the WHOLE op set, not just this call: the same op can
  // split again on a later edit, and a naive per-call `~1` suffix would collide with a `~1`
  // minted by an earlier edit (two ops one id → accept/reject-ambiguous). Mint against every
  // id already in play (the input ops plus ones minted so far in this call).
  const used = new Set(suggestions.map((s) => s.id));
  const mintId = (baseId) => {
    if (mint) return mint(baseId, ++splitN);
    let n = 1, id;
    while (used.has(id = `${baseId}~${n}`)) n++;
    used.add(id);
    return id;
  };
  for (const s of suggestions) {
    const { a, b } = span(s);
    if (b === a) { out.push({ ...s, from: mapPoint(a, ch) }); continue; }   // del point
    if (ch.from >= b) { out.push(s); continue; }                            // change after op
    if (ch.to <= a) { out.push({ ...s, from: a + delta }); continue; }      // change before op
    // Overlap: keep the parts of [a,b] outside [ch.from,ch.to]; the removed +
    // newly-inserted middle is untracked. The op's pending REMOVAL (oldText) is
    // baseline text that stays gone no matter what happens to newText, so it must
    // survive the edit: it rides with the surviving LEFT fragment, or — when the left
    // fragment is edited away — is re-emitted as a del at the edit site (which
    // coalesces back onto the right fragment into a substitution). Previously a delete
    // that consumed the START of a sub's addition dropped oldText entirely, so the
    // struck-through "removed" text silently vanished.
    const leftEnd = Math.min(b, ch.from);
    const rightStart = Math.max(a, ch.to);
    const leftNew = s.newText.slice(0, Math.max(0, leftEnd - a));
    const rightNew = s.newText.slice(rightStart - a);
    let leftEmitted = false;
    if (leftNew) {
      out.push({ ...s, from: a, newText: leftNew, oldText: s.oldText || '',
        kind: kindOf(s.oldText, leftNew) });
      leftEmitted = true;
    } else if (s.oldText) {
      out.push({ ...s, from: mapPoint(a, ch), newText: '', oldText: s.oldText, kind: 'del' });
      leftEmitted = true;   // the preserved-removal del KEEPS s.id, so the right ins must not
    }
    if (rightNew) {
      // Mint a fresh id for the right fragment whenever ANY left op was emitted (a surviving
      // left fragment OR the preserved-removal del) — both keep s.id, so reusing it here would
      // create two ops sharing one id, which collides accept/reject targeting and panel keys.
      const id = leftEmitted ? mintId(s.id) : s.id;
      out.push({ ...s, id, from: rightStart + delta, newText: rightNew, oldText: '',
        kind: 'ins' });
    }
  }
  return deferCoalesce ? out : coalesceOps(out);
}

// Ops that VANISHED across a human edit: present before, and afterwards
// neither the id nor any split fragment (`id~n`) survives. The canonical
// case is a pure insert fully consumed by the user's own typing — the
// overlap branch above emits nothing for it, so the card disappeared
// without trace; callers turn these into visible "superseded by your
// edit" ghosts instead (user-approved 2026-09-01). Pure.
function supersededOps(prevOps, nextOps) {
  const survivors = (nextOps || []).map((o) => String(o && o.id));
  const alive = (id) => survivors.some((v) => v === id || v.startsWith(id + '~'));
  return (prevOps || []).filter((s) => !alive(String(s && s.id)));
}

// Fold a whole CodeMirror transaction (a list of {from,to,insert} in ASCENDING,
// pre-image coordinates) into the ops. Applying changes right-to-left keeps each
// op's coordinates valid as earlier changes are folded.
function ingestHumanChanges(suggestions, changes, mint) {
  let next = suggestions;
  for (const ch of [...changes].sort((p, q) => q.from - p.from)) {
    next = mapOpsThroughChange(next, ch, mint);
  }
  return next;
}

// Record an AGENT edit: remap existing ops through the change, then add one
// tracked op for the agent's own contribution. `oldText` is the removed text
// (already gone from the new current); `newText` is what the agent inserted.
// `anchor` should be built against the NEW current around the inserted span.
function recordAgentEdit(suggestions, ch, meta) {
  // Remap RAW (deferCoalesce) so the agent's own op is present for the single
  // coalesce below: a del-point the agent introduces at the seam of two same-author
  // ops must keep them apart, not end up buried inside a prematurely-merged span.
  const remapped = mapOpsThroughChange(suggestions, ch, meta.mint, true);
  const newText = ch.insert || '';
  const oldText = meta.oldText || '';
  if (!newText && !oldText) return coalesceOps(remapped);
  const op = {
    id: meta.id, author: meta.author,
    // The author's stable session id (ROMP_SID) when known — names get
    // renamed; the id lets consumers resolve the CURRENT name/session
    // (user ask 2026-08-26).
    ...(meta.authorId ? { authorId: meta.authorId } : {}),
    ts: meta.ts || 0,
    kind: kindOf(oldText, newText), from: ch.from, newText, oldText,
    anchor: meta.anchor || null,
  };
  return coalesceOps([...remapped, op]);
}

// ── render (drop-in for the panel + inline overlay) ─────────────────
// Each op -> a hunk the existing UI already understands. baseFrom/baseTo (the
// span in the clean baseline) are derived from the running length delta of the
// ops before this one, so the paragraph-grouping display logic keeps working.
function toHunks(suggestions) {
  const sorted = [...suggestions].sort((x, y) => x.from - y.from);
  const out = [];
  let shift = 0; // net (newText - oldText) length of the ops before this one
  for (const s of sorted) {
    const { a, b } = span(s);
    const oldText = s.oldText || '';
    const newText = s.newText || '';
    const baseFrom = a - shift;
    out.push({
      id: s.id, author: s.author, ts: s.ts, kind: kindOf(oldText, newText),
      curFrom: a, curTo: b, baseFrom, baseTo: baseFrom + oldText.length,
      oldText, newText, anchor: s.anchor || null,
    });
    shift += newText.length - oldText.length;
  }
  return out;
}

// ── accept / reject ─────────────────────────────────────────────────
// Accept: the op's effect is ALREADY in current (insert present, deletion gone),
// so there is NO text edit — just drop the op. Returns { edit:null, suggestions }.
function acceptSuggestion(suggestions, id) {
  return { edit: null, suggestions: suggestions.filter((s) => s.id !== id) };
}

// Reject: revert current at the op's site to its pre-suggestion text and drop the
// op. Returns the buffer edit to dispatch (so it lands in CM undo history) plus
// the remaining ops, remapped through that reversal.
function rejectSuggestion(suggestions, id) {
  const s = suggestions.find((x) => x.id === id);
  if (!s) return { edit: null, suggestions };
  const { a, b } = span(s);
  const edit = { from: a, to: b, insert: s.oldText || '' };
  const rest = suggestions.filter((x) => x.id !== id);
  return { edit, suggestions: mapOpsThroughChange(rest, edit) };
}

// Accept a SET of ops (e.g. every op in a collapsed paragraph card): no text
// change, just drop them.
function acceptSuggestions(suggestions, ids) {
  const set = new Set(ids);
  return { edits: [], suggestions: suggestions.filter((s) => !set.has(s.id)) };
}

// Reject a SET of ops: revert each at its site and remap the survivors. Edits are
// returned high-offset-first so they dispatch as one batch without reindexing.
function rejectSuggestions(suggestions, ids) {
  const set = new Set(ids);
  const rest = suggestions.filter((s) => !set.has(s.id));
  const edits = suggestions.filter((s) => set.has(s.id))
    .sort(reversalOrder)
    .map((s) => { const { a, b } = span(s); return { from: a, to: b, insert: s.oldText || '' }; });
  let remapped = rest;
  for (const e of edits) remapped = mapOpsThroughChange(remapped, e);
  return { edits, suggestions: remapped };
}

function acceptAll(suggestions) {
  return { edits: [], suggestions: [] };
}

// Reject every op: revert current back to the clean baseline. Edits are returned
// high-offset first so they can be dispatched as one batch without reindexing.
function rejectAll(suggestions) {
  const edits = [...suggestions]
    .sort(reversalOrder)
    .map((s) => { const { a, b } = span(s); return { from: a, to: b, insert: s.oldText || '' }; });
  return { edits, suggestions: [] };
}

// The INVERSE of rejecting `ops`: the buffer edits (in POST-reject coordinates,
// ascending, non-overlapping) that re-apply each op's suggested text, undoing
// the reversal. Dispatch them high-offset-first as one batch, then restore the
// pre-reject op list (reanchored against the resulting text). `removes` is the
// text each edit replaces — the op's restored-baseline oldText — so a caller
// can verify the document hasn't drifted since the reject before undoing.
// (CodeMirror hosts get this for free via invertedEffects; this serves hosts
// without invertible-transaction history, e.g. the VS Code extension.)
function invertReject(ops) {
  // Exact mirror of `reversalOrder`: that applies high offset first and, at the
  // same offset, the WIDER op first; undoing it must walk the same sequence
  // backwards — low offset first, narrower first — or an insertion sharing an
  // offset with a zero-width deletion produces a negative range. The store's
  // order happens to satisfy this today, which is precisely why the invariant
  // needs stating rather than relying on.
  const sorted = [...ops].sort((x, y) => {
    const d = span(x).a - span(y).a;
    if (d) return d;
    const wx = span(x).b - span(x).a;
    const wy = span(y).b - span(y).a;
    if (wx !== wy) return wx - wy;
    if ((x.ts || 0) !== (y.ts || 0)) return (y.ts || 0) - (x.ts || 0);
    return String(x.id) < String(y.id) ? 1 : String(x.id) > String(y.id) ? -1 : 0;
  });
  let delta = 0; // net length change of the reversals BEFORE this op
  const out = [];
  for (const s of sorted) {
    const { a } = span(s);
    const oldText = s.oldText || '';
    const newText = s.newText || '';
    out.push({ from: a + delta, to: a + delta + oldText.length, insert: newText, removes: oldText });
    delta += oldText.length - newText.length;
  }
  return out;
}

// The clean text: current with every suggestion reverted (all rejected).
function baselineOf(current, suggestions) {
  let text = current;
  for (const s of [...suggestions].sort(reversalOrder)) {
    const { a, b } = span(s);
    text = text.slice(0, a) + (s.oldText || '') + text.slice(b);
  }
  return text;
}

// ── reload robustness ───────────────────────────────────────────────
// After the store is loaded, verify each op still sits on the text it claims; if
// the file was edited by another tool while closed, re-locate it by its anchor.
// An op that can no longer be placed is DETACHED — returned separately with its
// diff and attribution intact so the caller can preserve it for human review —
// never silently dropped, and never a reason to freeze the file (design
// 2026-08-18: a machine writer editing INSIDE a pending suggestion's inserted
// text — the vault-wide rename link-updater was the incident — used to make
// every subsequent tracked edit to that note refuse until a review pass).
// ── Google-Docs-style rebase helpers (user ask 2026-08-26) ──────────
// Word-multiset Dice similarity — cheap, order-insensitive; enough to
// tell "the user edited inside this" from "an unrelated rewrite".
function textSimilarity(a, b) {
  const words = (t) => String(t || '').toLowerCase().split(/\s+/).filter(Boolean);
  const wa = words(a);
  const wb = words(b);
  if (!wa.length && !wb.length) return 1;
  if (!wa.length || !wb.length) return 0;
  const count = new Map();
  for (const w of wa) count.set(w, (count.get(w) || 0) + 1);
  let inter = 0;
  for (const w of wb) {
    const c = count.get(w) || 0;
    if (c > 0) { inter++; count.set(w, c - 1); }
  }
  return (2 * inter) / (wa.length + wb.length);
}

// The region the op's surviving anchor CONTEXT still brackets — where
// its text used to sit, whatever sits there now. A context quote must
// be substantial (a one-char context would bracket almost anything) —
// EXCEPT that an empty quote is a BOUNDARY BIND when the op sat at that
// file edge when recorded: a whole-file create has prefix '' (nothing
// before offset 0) and suffix '' (nothing after EOF), which is exactly
// the op class agents use most, and it could never absorb at all
// (agent-session report 2026-08-26: an agent_id stamp inside
// a created file falsely orphaned the whole creation).
function anchorWindowIn(current, anchor, hint, opFrom) {
  if (!anchor) return null;
  const pre = anchor.prefix || '';
  const suf = anchor.suffix || '';
  const startBound = pre === '' && opFrom === 0;
  if (!startBound && pre.length < 8) return null;
  let start;
  if (startBound) {
    start = 0;
  } else {
    const pHits = allIndexesOf(current, pre);
    if (!pHits.length) return null;
    let p = pHits[0];
    for (const h of pHits) if (Math.abs(h - (hint || 0)) < Math.abs(p - (hint || 0))) p = h;
    start = p + pre.length;
  }
  if (suf === '') return { from: start, to: current.length, eofBound: true };
  if (suf.length < 8) return null;
  const sIdx = current.indexOf(suf, start);
  if (sIdx < 0) return null;
  return { from: start, to: sIdx };
}

// An EOF-bound window may cover text APPENDED after the op was recorded
// — user prose the suggestion must not claim (rejecting it would delete
// the user's addition). Trim trailing paragraphs that have no similar
// counterpart among the op's own paragraphs. Pure.
function trimAbsorbTail(windowText, newText) {
  const opParas = String(newText).split(/\n{2,}/).map((t) => t.trim()).filter(Boolean);
  const sep = /(\n{2,})/;
  const parts = String(windowText).split(sep);   // keeps separators at odd indexes
  let end = parts.length;
  while (end > 0) {
    const seg = parts[end - 1];
    if (sep.test(seg) || !seg.trim()) { end--; continue; }
    const para = seg.trim();
    const owned = para.length < 12
      || opParas.some((p) => p.includes(para) || para.includes(p)
        || textSimilarity(p, para) >= 0.5);
    if (owned) break;
    end--;
  }
  return parts.slice(0, end).join('').replace(/\n+$/, (m) =>
    String(windowText).endsWith(m) && end === parts.length ? m : '');
}

function rebaseSuggestions(current, suggestions, opts) {
  // opts (2026-08-26, adversarial review):
  //   merge    — opt IN to the Google-Docs stages (ABSORB out-of-band
  //              edits into a suggestion; SPLIT a partially-surviving
  //              insertion). Display/normalize passes want this; the
  //              CLI's stale-read discriminator and the detached
  //              re-attach pass MUST NOT (strict = default).
  //   occupied — ops whose spans are already claimed (the live
  //              suggestions, when re-attaching detached ops): no
  //              placement may overlap them.
  // Every placement — exact, anchor, relocation, absorb, split — goes
  // through one span REGISTRY: two kept ops may never overlap, because
  // reject applies inverse edits as a batch and overlapping spans make
  // it eat user text (execution-verified, review 2026-08-26).
  const o = opts || {};
  const merge = o.merge === true;
  const occupied = [];
  for (const k of Array.isArray(o.occupied) ? o.occupied : []) {
    if (!k || typeof k.from !== 'number') continue;
    const { a, b } = span(k);
    if (b > a) occupied.push({ a, b });
  }
  const kept = [];
  const detached = [];
  const collides = (a, b) => {
    if (b <= a) return false;                    // zero-width never collides
    for (const t of occupied) if (Math.max(a, t.a) < Math.min(b, t.b)) return true;
    for (const k of kept) {
      if (!k.newText) continue;
      const ks = span(k);
      if (Math.max(a, ks.a) < Math.min(b, ks.b)) return true;
    }
    return false;
  };
  const place = (op, from) => {
    if (collides(from, from + op.newText.length)) return false;
    kept.push(from === op.from ? op : { ...op, from });
    return true;
  };
  const pending = [];
  for (const s of Array.isArray(suggestions) ? suggestions : []) {
    // One malformed entry must not cost the whole store: `span()` on a non-object
    // throws, and every caller wraps the load in a blanket try/catch, so a single
    // bad record used to make an entire sidecar — suggestions AND comments —
    // read as absent. Garbage is dropped, not detached.
    if (!s || typeof s !== 'object' || typeof s.from !== 'number' || !isFinite(s.from)) continue;
    const { a } = span(s);
    if (s.newText) {
      if (current.slice(a, a + s.newText.length) === s.newText && place(s, a)) continue;
      // Verify over the op's OWN length, not the anchor's. An op that was split
      // or coalesced since the anchor was made carries a quote that is only PART
      // of its newText, so a quote-length slice can never match and the op was
      // silently dropped — leaving its text in the prose, untracked.
      const loc = s.anchor ? locateAnchor(current, s.anchor, a) : null;
      if (loc && current.slice(loc.from, loc.from + s.newText.length) === s.newText
          && place(s, loc.from)) continue;
      // Last resort: the op's own inserted text is the strongest anchor it has.
      // Prefer the occurrence nearest where the op used to be (skipping any that
      // would overlap an already-placed op). Relocating to the wrong copy of a
      // repeated string is visible and correctable; losing the op is silent and
      // permanent, so this is the better failure.
      const hits = allIndexesOf(current, s.newText)
        .sort((x, y) => Math.abs(x - a) - Math.abs(y - a));
      let placed = false;
      for (const h of hits) { if (place(s, h)) { placed = true; break; } }
      if (placed) continue;
      pending.push(s);
    } else {                                            // del point
      // Trust the stored offset when the surviving context still agrees with it.
      // A deletion holds no text of its own, so nothing AT the offset can confirm
      // it — the old code skipped this check entirely and relocated every del on
      // every load, including loads of a completely unchanged file.
      const anchor = s.anchor;
      const pre = (anchor && anchor.prefix) || '';
      const suf = (anchor && anchor.suffix) || '';
      const fits = a <= current.length
        && (!pre || current.slice(Math.max(0, a - pre.length), a) === pre)
        && (!suf || current.startsWith(suf, a));
      if (fits) { kept.push(s); continue; }
      const loc = anchor ? locateAnchor(current, anchor, a) : null;
      if (loc) { kept.push({ ...s, from: loc.from }); continue; }
      if (a <= current.length) { kept.push(s); continue; }
      detached.push({ ...s, detached: true });          // beyond EOF, anchor gone
    }
  }
  // Second pass — the Google-Docs stages run only once EVERY exactly-
  // placeable op has claimed its span, so a window or fragment can never
  // swallow a live neighbor (one-sided-order bug, review 2026-08-26).
  const usedIds = new Set();
  for (const x of Array.isArray(suggestions) ? suggestions : []) if (x && x.id) usedIds.add(x.id);
  for (const s of pending) {
    const { a } = span(s);
    if (merge) {
      // ABSORB: the anchor context still brackets a region whose text
      // was edited out-of-band. Fold those edits INTO the suggestion —
      // newText becomes what is there now, reject still restores
      // oldText — the way editing suggested text merges into the
      // suggestion in a Google Doc. Similarity-gated so an unrelated
      // rewrite still detaches for review.
      const win = anchorWindowIn(current, s.anchor, a, s.from);
      if (win && win.to > win.from && !collides(win.from, win.to)) {
        let text = current.slice(win.from, win.to);
        // EOF-bound windows must not claim user text appended after the
        // op was recorded — rejecting the suggestion would delete it.
        if (win.eofBound) text = trimAbsorbTail(text, s.newText);
        const okSize = text.length > 0
          && text.length <= Math.max(s.newText.length * 2 + 80, 400);
        if (okSize && !collides(win.from, win.from + text.length)
            && textSimilarity(s.newText, text) >= 0.5) {
          kept.push({ ...s, from: win.from, newText: text,
            kind: kindOf(s.oldText || '', text) });
          continue;
        }
      }
      // SPLIT for insertions ("broken apart", user ask 2026-08-26):
      // paragraphs of the inserted text that survive verbatim keep as
      // their own smaller ops; everything unplaceable — missing, too
      // short to place safely, ambiguous, or colliding with a live op —
      // becomes a small detached residual. Nothing is dropped. The
      // FIRST kept fragment keeps the original id, so comment threads
      // (suggestionId) and accept-by-id keep working — the same rule
      // the live-edit splitter uses.
      if (!s.oldText) {
        const parts = String(s.newText).split(/\n{2,}/)
          .map((t) => t.trim()).filter(Boolean);
        if (parts.length >= 2) {
          const found = [];
          const missing = [];
          for (const f of parts) {
            if (f.length < 12) { missing.push(f); continue; }
            const fh = allIndexesOf(current, f);
            if (fh.length !== 1) { missing.push(f); continue; }
            const at = fh[0];
            if (collides(at, at + f.length)
                || found.some((g) => Math.max(at, g.at) < Math.min(at + f.length, g.at + g.f.length))) {
              missing.push(f);
              continue;
            }
            found.push({ f, at });
          }
          if (found.length) {
            let n = 1;
            const mint = () => {
              let idn;
              do { idn = `${s.id}#p${n++}`; } while (usedIds.has(idn));
              usedIds.add(idn);
              return idn;
            };
            found.sort((x, y) => x.at - y.at);
            let first = true;
            for (const hit of found) {
              const id = first ? s.id : mint();
              first = false;
              kept.push({ ...s, id, from: hit.at, newText: hit.f, kind: 'ins',
                anchor: makeAnchor(current, hit.at, hit.at + hit.f.length) });
            }
            for (const f of missing) {
              detached.push({ ...s, id: mint(), newText: f, kind: 'ins',
                anchor: null, detached: true });
            }
            continue;
          }
        }
      }
    }
    detached.push({ ...s, detached: true });            // its text is gone — for review
  }
  return { kept: kept.sort((x, y) => x.from - y.from), detached };
}

// Back-compat wrapper: keep only the placeable ops. Callers that can
// persist detached ops should use rebaseSuggestions instead.
function reanchorSuggestions(current, suggestions) {
  return rebaseSuggestions(current, suggestions).kept;
}

// ── comment anchoring (text-quote) ──────────────────────────────────
// `hint` (optional) is the op/comment's last known offset. It never overrides a
// better context match — it only breaks ties between candidates that score
// EQUALLY, by preferring the one nearest where the anchor used to be. Without it
// a repeated phrase resolves to whichever copy appears first in the file, which
// is how a deletion point could jump to an earlier paragraph on a reload of an
// otherwise unchanged note (and then corrupt the text when rejected).
function allIndexesOf(text, needle) {
  const hits = [];
  if (!needle) return hits;
  let i = text.indexOf(needle);
  while (i !== -1) { hits.push(i); i = text.indexOf(needle, i + 1); }
  return hits;
}

// Pick the best of several candidate positions: highest context score wins;
// ties go to the candidate nearest `hint`; with no hint, the earliest.
function pickCandidate(cands, hint) {
  let best = null;
  for (const c of cands) {
    if (!best || c.score > best.score) { best = c; continue; }
    if (c.score < best.score) continue;
    if (hint == null) continue;
    if (Math.abs(c.pos - hint) < Math.abs(best.pos - hint)) best = c;
  }
  return best;
}

// A ZERO-WIDTH anchor (quote === '') marks a point, not a span — the site of a
// pending deletion, whose text is by definition absent from the current file.
// Both neighbours must be consulted: scoring prefix candidates against the
// suffix is what tells two similar paragraphs apart. The old code took
// `text.indexOf(prefix)` and never looked at the suffix at all.
function locatePoint(text, prefix, suffix, hint) {
  if (!prefix && !suffix) return null;
  const cands = [];
  if (prefix) {
    for (const i of allIndexesOf(text, prefix)) {
      const pos = i + prefix.length;
      cands.push({ pos, score: 2 + (suffix && text.startsWith(suffix, pos) ? 2 : 0) });
    }
  } else {
    for (const i of allIndexesOf(text, suffix)) cands.push({ pos: i, score: 2 });
  }
  const best = pickCandidate(cands, hint);
  return best ? { from: best.pos, to: best.pos } : null;
}

function locateAnchor(text, anchor, hint) {
  if (!anchor || typeof anchor.quote !== 'string') return null;
  const { quote } = anchor;
  const prefix = anchor.prefix || '';
  const suffix = anchor.suffix || '';
  if (!quote) return locatePoint(text, prefix, suffix, hint);
  const hits = allIndexesOf(text, quote);
  if (hits.length) {
    const cands = hits.map((h) => {
      const before = text.slice(Math.max(0, h - prefix.length), h);
      const after = text.slice(h + quote.length, h + quote.length + suffix.length);
      let score = 0;
      if (prefix && before.endsWith(prefix)) score += 2;
      if (suffix && after.startsWith(suffix)) score += 2;
      return { pos: h, score };
    });
    const best = pickCandidate(cands, hint);
    if (best) return { from: best.pos, to: best.pos + quote.length };
  }
  // The quoted text is gone. Fall back to the region BETWEEN the surviving
  // context, which is where that text used to sit — this is what lets a comment
  // follow prose that was rewritten under it rather than being orphaned.
  if (!prefix && !suffix) return null;
  let start = prefix ? text.indexOf(prefix) : 0;
  if (prefix && start !== -1) start += prefix.length;
  if (start === -1) return null;
  let end = suffix ? text.indexOf(suffix, start) : text.length;
  if (end === -1 || end < start) return null;
  return { from: start, to: end };
}

function makeAnchor(text, from, to, ctx) {
  const c = ctx == null ? 24 : ctx;
  return {
    quote: text.slice(from, to),
    prefix: text.slice(Math.max(0, from - c), from),
    suffix: text.slice(to, to + c),
  };
}

// A bare/message comment auto-resolves when the text it anchored to changes.
function messageStillPending(current, anchor) {
  if (!anchor || typeof anchor.quote !== 'string' || !anchor.quote) return false;
  const text = current || '';
  const loc = locateAnchor(text, anchor);
  return !!loc && text.slice(loc.from, loc.to) === anchor.quote;
}

function pruneAddressedMessages(comments, current) {
  const list = Array.isArray(comments) ? comments : [];
  return list.filter((c) => !c || c.kind !== 'message' || messageStillPending(current, c.anchor));
}

// Comment whose anchored text is gone from current for good (not merely hidden
// by a rejectable op) is dropped.
function pruneOrphanedComments(comments, current) {
  const list = Array.isArray(comments) ? comments : [];
  return list.filter((c) => {
    if (!c || !c.anchor) return true;
    return locateAnchor(current, c.anchor) != null;
  });
}

// ── note-tree edges (tracking inheritance, 2026-08-09) ──────────────
//
// Tracking propagates DOWN a note tree: turning it on for a note makes
// every note it links to tracked, transitively. "Links to" means a
// WHOLE-LINE `[[link]]` / `![[embed]]` line — the same organizer/leaf
// edge the slides composer uses, so "child note" means one thing
// vault-wide. `$` (deck-backup) and `!!` (appendix) prefixed lines are
// children too: those marks change deck PRESENTATION, not tree shape.
// Bulleted and inline links are citations and do not inherit.
//
// Fence- and %%-comment-aware, with the DANGLING-OPENER rule: only a
// fence/comment that actually CLOSES hides its contents — a stray `%%`
// in draft prose must not silently untrack half the tree.
//
// Pure and sync; each consumer (store-io on Node, the Obsidian plugin)
// drives its own closure walk with its own I/O and link resolution.
const CHILD_LINK_LINE_RE = /^[ \t]*\$?!{0,2}\[\[([^\]#|]+?)(?:\|[^\]]*)?\]\][ \t]*$/;
// Embeds only — the bang is REQUIRED. These are the notes that RENDER
// INSIDE the page; the review panel + rollup counts follow this edge so
// the sidebar matches what the document shows (user ask 2026-08-18).
// Plain [[link]] lines stay separate notes there. Tracking INHERITANCE
// keeps the wider link-or-embed edge (childLinkLines) — untouched.
const CHILD_EMBED_LINE_RE = /^[ \t]*\$?!{1,2}\[\[([^\]#|]+?)(?:\|[^\]]*)?\]\][ \t]*$/;
const CHILD_FENCE_RE = /^[ \t]*(`{3,}|~{3,})(.*)$/;

function childLines(text, lineRe) {
  const src = typeof text === 'string' ? text : '';
  const lines = src.split(/\r?\n/);
  const fmMatch = /^---\r?\n[\s\S]*?\r?\n---\r?\n?/.exec(src);
  const fmLines = fmMatch ? (fmMatch[0].match(/\n/g) || []).length : 0;
  const inertFences = new Set();
  const inertComments = new Set();
  const scan = () => {
    const found = [];
    let fence = null;
    let fenceLine = -1;
    let inComment = false;
    let commentLine = -1;
    for (let i = 0; i < lines.length; i++) {
      if (i < fmLines) continue;
      const line = lines[i];
      const fm = CHILD_FENCE_RE.exec(line);
      if (fm && !inComment) {
        const marker = fm[1];
        if (!fence) {
          if (!inertFences.has(i)) { fence = { char: marker[0], len: marker.length }; fenceLine = i; }
        } else if (marker[0] === fence.char && marker.length >= fence.len
            && fm[2].trim() === '') { fence = null; }
        continue;
      }
      const marks = (line.match(/%%/g) || []).length;
      if (inComment) {
        if (marks % 2 === 1) inComment = false;
        continue;
      }
      if (marks % 2 === 1 && !inertComments.has(i)) {
        inComment = true; commentLine = i; continue;
      }
      if (fence || marks > 0) continue;
      const m = lineRe.exec(line);
      if (m) found.push(m[1].trim());
    }
    return {
      found,
      danglingFence: fence ? fenceLine : -1,
      danglingComment: inComment ? commentLine : -1,
    };
  };
  let result = scan();
  while (result.danglingFence !== -1 || result.danglingComment !== -1) {
    if (result.danglingFence !== -1) inertFences.add(result.danglingFence);
    if (result.danglingComment !== -1) inertComments.add(result.danglingComment);
    result = scan();
  }
  return result.found.filter((t) => t.length > 0);
}

function childLinkLines(text) { return childLines(text, CHILD_LINK_LINE_RE); }
function childEmbedLines(text) { return childLines(text, CHILD_EMBED_LINE_RE); }

// ── tracked-path scope (per-file tracking) — unchanged ──────────────
function isTracked(trackedList, relPath) {
  if (!Array.isArray(trackedList) || typeof relPath !== 'string') return false;
  const p = relPath.replace(/^\.?\//, '');
  for (const entry of trackedList) {
    if (typeof entry !== 'string' || !entry) continue;
    const e = entry.replace(/^\.?\//, '');
    if (e.endsWith('/')) { if (p.startsWith(e)) return true; }
    else if (p === e) return true;
  }
  return false;
}

// ── scope maintenance: renames and deletions ────────────────────────
//
// The tracked list holds two entry shapes: an exact file path, and a folder
// prefix ending in `/`. Neither survives a rename on its own, and the failure is
// SILENT — the note keeps its sidecar but no longer matches any entry, so
// tracking is simply off and edits land in the prose un-suggested. That is the
// worst failure this feature has, because its entire purpose is that nothing
// changes the document without showing up as a suggestion. Hit in the vault on
// 2026-08-02 by renaming a tracked note in Obsidian.
//
// Pure, and shared, so the Obsidian plugin and the CLI cannot drift on what a
// rename means to the scope list.

function normEntry(s) {
  return String(s == null ? '' : s).replace(/^\.?\//, '');
}

// Rewrite the tracked list for a path that moved. `isFolder` distinguishes a
// folder rename — which must also carry every entry filed underneath it — from a
// file rename. Order is preserved and duplicates collapse, so running it twice
// is harmless.
function renameTracked(trackedList, oldPath, newPath, isFolder) {
  if (!Array.isArray(trackedList)) return [];
  const from = normEntry(oldPath).replace(/\/+$/, '');
  const to = normEntry(newPath).replace(/\/+$/, '');
  if (!from || !to || from === to) return trackedList.slice();
  const out = [];
  for (const raw of trackedList) {
    if (typeof raw !== 'string' || !raw) continue;
    const e = normEntry(raw);
    let next = raw;
    if (isFolder) {
      if (e === from || e === `${from}/`) next = `${to}/`;
      else if (e.startsWith(`${from}/`)) next = to + e.slice(from.length);
    } else if (e === from) {
      next = to;
    }
    if (!out.includes(next)) out.push(next);
  }
  // A file covered by a FOLDER entry has no entry of its own, so the loop above
  // moves nothing — and if the file moved OUT of that folder it silently stops
  // being tracked. Give it an explicit entry at its new home. (The 2026-08-02 fix
  // covered exact-path entries; this is the same failure for folder-covered
  // files, and "tracking silently switched off" is the worst outcome this
  // feature has.)
  if (!isFolder && isTracked(trackedList, from) && !isTracked(out, to)) out.push(to);
  return out;
}

// Drop the entries for a path that no longer exists. A folder takes everything
// beneath it with it.
function pruneTracked(trackedList, path, isFolder) {
  if (!Array.isArray(trackedList)) return [];
  const gone = normEntry(path).replace(/\/+$/, '');
  if (!gone) return trackedList.slice();
  return trackedList.filter((raw) => {
    if (typeof raw !== 'string' || !raw) return false;
    const e = normEntry(raw);
    if (isFolder) return !(e === gone || e === `${gone}/` || e.startsWith(`${gone}/`));
    return e !== gone;
  });
}

// ── migration: v1 snapshot store -> v3 op-log ───────────────────────
// Best-effort. The old store kept baseline + full-text snapshots; authorship of
// individual regions can't be recovered exactly, so each diff hunk is attributed
// to the most recent snapshot's author (the common single-agent case is exact).
function migrateV1(store, mkId) {
  const baseline = (store && store.baseline) || '';
  const edits = Array.isArray(store && store.edits) ? store.edits : [];
  const current = edits.length ? (edits[edits.length - 1].text || '') : baseline;
  const author = edits.length ? (edits[edits.length - 1].author || 'unknown') : 'unknown';
  const ts = edits.length ? (edits[edits.length - 1].ts || 0) : 0;
  const suggestions = changeSet(baseline, current).map((h, i) => ({
    id: (mkId ? mkId(i) : `mig-${i}`), author, ts,
    kind: h.kind, from: h.curFrom, newText: h.newText, oldText: h.oldText,
    anchor: makeAnchor(current, h.curFrom, h.curTo),
  }));
  return {
    v: 3,
    path: store && store.path,
    current,
    suggestions,
    comments: Array.isArray(store && store.comments) ? store.comments : [],
  };
}

module.exports = {
  // reusable diff helpers (migration + CLI seed)
  tokenizeWords, splitLinesKeep, lcsOps, rawOps, changeSet,
  // op-log core
  span, kindOf, coalesceOps, mapPoint, mapOpsThroughChange, ingestHumanChanges, supersededOps,
  recordAgentEdit, toHunks,
  acceptSuggestion, rejectSuggestion, acceptSuggestions, rejectSuggestions,
  acceptAll, rejectAll, invertReject, baselineOf, reanchorSuggestions, rebaseSuggestions,
  // comments + anchoring
  locateAnchor, makeAnchor, messageStillPending, pruneAddressedMessages, pruneOrphanedComments,
  // scope + migration
  isTracked, renameTracked, pruneTracked, migrateV1,
  // note-tree edges (tracking inheritance; embed-only variant for the
  // review panel + rollup counts)
  childLinkLines, childEmbedLines,
  textSimilarity, anchorWindowIn, trimAbsorbTail,
};
