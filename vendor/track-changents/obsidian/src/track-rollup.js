'use strict';

// Tracked-changes ROLLUP over a note's embed tree (2026-08-18): the
// count shown for a note covers the note itself plus every note
// reachable through whole-line [[link]]/![[embed]] lines, transitively
// — the same edge definition tracking inheritance uses (track-tree.js),
// so "what the rollup counts" and "what tracking covers" can never
// disagree. Pure helpers so the aggregation and the reject-edit
// application run under vitest; the closure walk itself stays in
// track-tree.js.

// Sum pending counts over a closure of paths. `closure` is any
// iterable of vault paths; `pendingByPath` maps path -> count.
function sumOverClosure(closure, pendingByPath) {
  if (!closure || !pendingByPath) return 0;
  let sum = 0;
  for (const p of closure) sum += pendingByPath.get(p) || 0;
  return sum;
}

// Apply CodeMirror-style change specs ({from, to, insert}) to a plain
// string. All positions are in ORIGINAL-document coordinates — the same
// contract as cm.dispatch({changes}) — so the edits are applied
// back-to-front and never remapped. Used to reject suggestions in a
// note that has no live editor (panel review of a closed embedded
// note): the engine's rejectSuggestions returns these edits expecting
// a CM dispatch; this is that dispatch for a string.
function applyEditsToText(text, edits) {
  const t = String(text == null ? '' : text);
  const list = (Array.isArray(edits) ? edits : [])
    .map((e) => ({ from: e.from | 0, to: (e.to == null ? e.from : e.to) | 0, insert: e.insert == null ? '' : String(e.insert) }))
    .sort((a, b) => b.from - a.from || b.to - a.to);
  let out = t;
  for (const e of list) {
    if (e.from < 0 || e.to < e.from || e.to > out.length) continue;
    out = out.slice(0, e.from) + e.insert + out.slice(e.to);
  }
  return out;
}

module.exports = { sumOverClosure, applyEditsToText };
