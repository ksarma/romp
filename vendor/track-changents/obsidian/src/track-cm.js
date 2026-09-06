'use strict';

// The pure CodeMirror-6 state wiring for the op-log track-changes overlay.
// Deliberately free of Obsidian (only @codemirror/state, @codemirror/commands and
// the engine) so the same wiring the plugin ships is exercised directly by
// track-cm.test.mjs — the undo behaviour (the headline fix) is the kind of thing
// that must be tested against the REAL field, not a copy.
//
// The op list IS the field's value. It changes in exactly three ways:
//   1) an explicit setSuggestions effect (accept/reject, or loading the store) wins;
//   2) the human typed → every op is mapped through the exact change (shift /
//      shrink / split) via engine.ingestHumanChanges — no re-diff, and because the
//      field derives from tr.changes, UNDO of the typing remaps the ops back;
//   3) otherwise unchanged.
// invertedEffects stores the PREVIOUS ops as the inverse of a setSuggestions
// effect, which is what makes an accept (a text-unchanged, effect-only
// transaction) recorded in history and undoable — Cmd-Z restores the suggestion
// rather than undoing the user's earlier typing.

const { StateField, StateEffect, Annotation } = require('@codemirror/state');
const { invertedEffects } = require('@codemirror/commands');
const track = require('track-changents/engine');

// setSuggestions: replace the op list (accept/reject, and loading the store).
// setTrackMeta: replace the { trackingOn, comments } side-data that drives the
// comment highlights + the enabled gate.
const setSuggestions = StateEffect.define();
const setTrackMeta = StateEffect.define();
// Marks a load/sync dispatch so the persist listener doesn't echo it straight
// back to disk (which would bump mtime and re-trigger the reload poll).
const syncAnnotation = Annotation.define();

// The op-list field. Exported as a factory because a StateField instance is
// single-use per editor-extension set.
function makeSuggestionField() {
  return StateField.define({
    create: () => [],
    update(value, tr) {
      // An explicit setSuggestions wins (accept/reject, or loading the store). Fold
      // ALL of them and take the LAST: undoing a BATCHED history event (several
      // grouped keystrokes) arrives as ONE transaction carrying several stored
      // inverses, and the last corresponds to the state to restore. Early-returning
      // on the first was wrong for that batched-undo case.
      let next = value;
      let replaced = false;
      for (const e of tr.effects) if (e.is(setSuggestions)) { next = e.value; replaced = true; }
      if (replaced) return next;
      if (tr.docChanged) {
        const changes = [];
        tr.changes.iterChanges((fromA, toA, fromB, toB, inserted) => {
          changes.push({ from: fromA, to: toA, insert: inserted.toString() });
        });
        return track.ingestHumanChanges(value, changes);
      }
      return value;
    },
  });
}

// The undo glue for a given suggestion field: snapshot the EXACT op list before a
// change as its history inverse. This fires for ANY history transaction that alters
// the ops — an explicit setSuggestions (accept/reject) OR a human doc edit folded
// through ingestHumanChanges — so undo/redo restores the recorded ops verbatim
// instead of RE-DERIVING them from the inverse change. ingestHumanChanges is lossy
// (it splits/coalesces) and is not a clean inverse, so re-deriving turned a
// hand-edited suggestion into a mangled, partly-untracked op on undo. Loads/syncs
// carry addToHistory.of(false), so they never reach history and are never snapshotted.
function makeInvertedEffects(field) {
  return invertedEffects.of((tr) => {
    if (!tr.docChanged && !tr.effects.some((e) => e.is(setSuggestions))) return [];
    return [setSuggestions.of(tr.startState.field(field))];
  });
}

module.exports = {
  setSuggestions, setTrackMeta, syncAnnotation,
  makeSuggestionField, makeInvertedEffects,
};
