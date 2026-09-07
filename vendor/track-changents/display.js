'use strict';

// Diff-DISPLAY planning shared by both editor frontends (the Obsidian
// plugin and the VS Code extension): how a set of tracked hunks should be
// presented for review, independent of any DOM.
//
// A mostly-rewritten PARAGRAPH reads as an unreadable mess when every little
// edit is shown as its own change — many struck fragments crammed over one
// block of text. Past a density threshold we stop interleaving and show the
// WHOLE old paragraph struck with the WHOLE new paragraph in its place, like
// marking up paper: read the old, read the new. Sparse edits stay individual.
//
// planDiffDisplay groups the hunks by the paragraph (a maximal run of
// non-blank lines) each falls in; a DENSE paragraph (>= half its text churned,
// or very many separate edits) collapses to ONE merged hunk spanning the whole
// paragraph, while everything else passes through as individual hunks. Each
// returned item is a hunk object (the same { kind, baseFrom, baseTo, curFrom,
// curTo, oldText, newText, author } shape accept/reject already use — a merged
// item accepts/rejects the whole paragraph) PLUS a `display` field:
//   'inline'    — float the struck text at the word (short single-line sub)
//   'block'     — a struck section above the line (long/multi-line)
//   'deletion'  — a pure deletion, shown in place
//   'paragraph' — the merged whole-paragraph form (rendered like 'block')
// A merged item also carries `ids`: the op ids it covers, so a frontend can
// accept/reject the set with the engine's plural acceptSuggestions/
// rejectSuggestions. Pure, unit-tested without a DOM.

const INLINE_REMOVAL_MAX = 64;
const PARAGRAPH_COLLAPSE_FRACTION = 0.5; // >= half the paragraph's text churned → collapse
const PARAGRAPH_COLLAPSE_MIN_HUNKS = 6;  // OR this many separate edits packed into one paragraph

// A short single-line substitution whose struck old text can float at the word.
function isInlineRemoval(oldText, newText) {
  return !!newText && typeof oldText === 'string'
    && !oldText.includes('\n') && oldText.length <= INLINE_REMOVAL_MAX;
}

// How to render ONE hunk's struck old text.
function displayMode(h) {
  if (h.oldText && !h.newText) return 'deletion';
  return isInlineRemoval(h.oldText, h.newText) ? 'inline' : 'block';
}

// The [start, end) of the paragraph (maximal run of non-blank lines) containing `pos`.
function paragraphRange(text, pos) {
  const p = Math.max(0, Math.min(pos, text.length));
  let start = text.lastIndexOf('\n', p - 1) + 1;             // start of the line at pos (0 if none)
  const nl = text.indexOf('\n', p);
  let end = nl === -1 ? text.length : nl;                    // end of the line at pos (before the '\n')
  while (start > 0) {                                        // expand up over non-blank lines
    const prevEnd = start - 1;                               // the '\n' ending the previous line
    const prevStart = text.lastIndexOf('\n', prevEnd - 1) + 1;
    if (/^\s*$/.test(text.slice(prevStart, prevEnd))) break; // blank line → paragraph boundary
    start = prevStart;
  }
  while (end < text.length) {                                // expand down over non-blank lines
    const nextStart = end + 1;                               // skip the '\n'
    const nn = text.indexOf('\n', nextStart);
    const nextEnd = nn === -1 ? text.length : nn;
    if (nextStart > text.length || /^\s*$/.test(text.slice(nextStart, nextEnd))) break;
    end = nextEnd;
  }
  return { start, end };
}

function planDiffDisplay(hunks, baseline, current) {
  const src = Array.isArray(hunks) ? hunks.slice().sort((a, b) => a.curFrom - b.curFrom) : [];
  if (!src.length) return [];
  const base = baseline || '';
  const cur = current || '';
  // Group consecutive hunks (already sorted) that share a paragraph in the current text.
  const groups = [];
  let g = null;
  for (const h of src) {
    const pr = paragraphRange(cur, h.curFrom);
    if (g && g.start === pr.start && g.end === pr.end) g.hunks.push(h);
    else { g = { start: pr.start, end: pr.end, hunks: [h] }; groups.push(g); }
  }
  const out = [];
  for (const grp of groups) {
    const passthrough = () => {
      for (const h of grp.hunks) out.push({ ...h, display: displayMode(h) });
    };
    if (grp.hunks.length < 2) { passthrough(); continue; }   // a lone hunk is already inline/block-clean
    // Whole-paragraph span in current + the matching baseline span. The unchanged prefix
    // (paragraph start → first change) and suffix (last change → paragraph end) are identical
    // text in both, so the offset deltas are exact.
    const first = grp.hunks[0];
    let last = grp.hunks[0];
    for (const h of grp.hunks) if (h.curTo > last.curTo) last = h;
    const pCurFrom = Math.min(grp.start, first.curFrom);
    const pCurTo = Math.max(grp.end, last.curTo);
    const pBaseFrom = first.baseFrom - (first.curFrom - pCurFrom);
    const pBaseTo = last.baseTo + (pCurTo - last.curTo);
    if (pBaseFrom < 0 || pBaseTo > base.length || pBaseTo < pBaseFrom || pCurTo <= pCurFrom) {
      passthrough(); continue;                               // couldn't form a clean paragraph span
    }
    const oldChanged = grp.hunks.reduce((s, h) => s + h.oldText.length, 0);
    const newChanged = grp.hunks.reduce((s, h) => s + h.newText.length, 0);
    const denom = (pBaseTo - pBaseFrom) + (pCurTo - pCurFrom);
    const fraction = denom > 0 ? (oldChanged + newChanged) / denom : 0;
    const dense = grp.hunks.length >= PARAGRAPH_COLLAPSE_MIN_HUNKS || fraction >= PARAGRAPH_COLLAPSE_FRACTION;
    if (!dense) { passthrough(); continue; }
    const oldText = base.slice(pBaseFrom, pBaseTo);
    const newText = cur.slice(pCurFrom, pCurTo);
    const counts = {};
    for (const h of grp.hunks) { const a = h.author || 'unknown'; counts[a] = (counts[a] || 0) + 1; }
    const author = Object.keys(counts).sort((a, b) => counts[b] - counts[a])[0];
    out.push({
      kind: oldText && newText ? 'sub' : (newText ? 'ins' : 'del'),
      baseFrom: pBaseFrom, baseTo: pBaseTo, curFrom: pCurFrom, curTo: pCurTo,
      oldText, newText, author, display: 'paragraph',
      ids: grp.hunks.map((h) => h.id).filter((id) => id != null),
    });
  }
  return out.sort((a, b) => a.curFrom - b.curFrom);
}

// The change the cursor is "on", for the accept/reject-at-cursor keys: the hunk whose
// buffer span [curFrom,curTo] contains `pos`, else the nearest one at/after it, else the
// last. `hunks` must be sorted by curFrom.
function changeForCursor(hunks, pos) {
  if (!Array.isArray(hunks) || !hunks.length) return null;
  return hunks.find((h) => pos >= h.curFrom && pos <= h.curTo)
    || hunks.find((h) => h.curFrom >= pos) || hunks[hunks.length - 1];
}

// Every op id a display item stands for: the merged paragraph's covered set, or
// the item's own id. Frontends feed this to acceptSuggestions/rejectSuggestions.
function idsOf(item) {
  if (!item) return [];
  if (Array.isArray(item.ids) && item.ids.length) return item.ids;
  return item.id != null ? [item.id] : [];
}

module.exports = {
  INLINE_REMOVAL_MAX,
  isInlineRemoval,
  displayMode,
  paragraphRange,
  planDiffDisplay,
  changeForCursor,
  idsOf,
};
