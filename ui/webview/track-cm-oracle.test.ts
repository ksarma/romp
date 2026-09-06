// The behavioural ORACLE for the editor's track option (plans/file-review.md, Slice 5, Acceptance): upstream
// track-changents' `obsidian/tests/track-cm.test.mjs` and `track-cm.undo.test.mjs` at the pinned commit
// (vendor/track-changents/PIN.json), ported case for case from vitest to node:test + assert. They drive the
// REAL vendored field (vendor/track-changents/obsidian/src/track-cm.js, bundled unchanged) and the real engine
// through a live EditorState + @codemirror/commands history — the same @codemirror/state the chunk bundles
// (esbuild.js's oneCodeMirror alias gives the test bundle one copy, as the chunk gets). Every case here is
// upstream's; romp's own additions (the ledger, the click policy, the marks) are tested in
// editor-track.test.ts. Fixtures are upstream's synthetic ones: author 'FRO', docs about cats.
//
// upstream loaded `../src/track-cm.js`, `track-changents/engine`, `@codemirror/state` and `@codemirror/commands`
// through createRequire; here they are imports the test bundle resolves (the engine's self-reference from
// inside track-cm.js resolves through the vendored package.json).
import { describe, it } from "node:test";
import * as assert from "node:assert/strict";
import { setSuggestions, makeSuggestionField, makeInvertedEffects } from "../../vendor/track-changents/obsidian/src/track-cm.js";
import * as engine from "../../vendor/track-changents/engine.js";
import type { TrackRecord } from "../../vendor/track-changents/engine.js";
import { EditorState, Transaction, type TransactionSpec } from "@codemirror/state";
import { history, undo, redo, isolateHistory } from "@codemirror/commands";

const ins = (id: string, from: number, newText: string): TrackRecord => ({ id, author: "FRO", ts: 1, kind: "ins", from, newText, oldText: "" });
const sub = (id: string, from: number, newText: string, oldText: string): TrackRecord => ({ id, author: "FRO", ts: 1, kind: "sub", from, newText, oldText });

// ── track-cm.test.mjs ─────────────────────────────────────────────────────────────────────────────
// A tiny headless editor: EditorState + the field + invertedEffects + history, with a mock dispatch
// target so @codemirror/commands `undo` can drive it.
function harness(doc: string, ops: TrackRecord[]) {
  const field = makeSuggestionField();
  const invert = makeInvertedEffects(field);
  const target = {
    state: EditorState.create({ doc, extensions: [history(), field, invert] }),
    dispatch(tr: Transaction) { target.state = tr.state; },
  };
  // Seed the ops WITHOUT making the seed an undo step.
  target.state = target.state.update({
    effects: setSuggestions.of(ops), annotations: Transaction.addToHistory.of(false),
  }).state;
  return {
    ops: () => target.state.field(field),
    doc: () => target.state.doc.toString(),
    apply: (spec: TransactionSpec) => { target.state = target.state.update(spec).state; },
    type: (spec: TransactionSpec) => { target.state = target.state.update({ ...spec, annotations: Transaction.userEvent.of("input.type") }).state; },
    undo: () => undo(target),
    redo: () => redo(target),
  };
}

describe("track-cm: accept/reject are undoable, and undo does not eat typing", () => {
  it("ACCEPT (effect-only, no text change) is undoable — undo restores the op, not the text", () => {
    const h = harness("The big cat sat.", [ins("a1", 4, "big ")]);
    // accept a1: drop the op; the text already reads with it applied, so no doc change
    h.apply({ effects: setSuggestions.of([]) });
    assert.equal(h.ops().length, 0);
    assert.equal(h.doc(), "The big cat sat.");
    // Cmd-Z: the ACCEPT is undone (op comes back), the text is untouched. This is the
    // reported bug — previously undo hit the user's last typing instead.
    h.undo();
    assert.equal(h.doc(), "The big cat sat.");
    assert.deepEqual(h.ops().map((o) => o.id), ["a1"]);
    assert.equal(h.ops()[0].newText, "big ");
  });

  it("REJECT (text change + effect) undo restores both the text and the op", () => {
    const h = harness("The big cat sat.", [ins("a1", 4, "big ")]);
    // reject a1: revert current[4,8] to '' and drop the op
    h.apply({ changes: { from: 4, to: 8, insert: "" }, effects: setSuggestions.of([]) });
    assert.equal(h.doc(), "The cat sat.");
    assert.equal(h.ops().length, 0);
    h.undo();
    assert.equal(h.doc(), "The big cat sat.");
    assert.equal(h.ops().length, 1);
  });
});

describe("track-cm: human edits are mapped through, never tracked, and undo remaps back", () => {
  it("typing elsewhere leaves the op attributed + in place; undo restores the doc", () => {
    const h = harness("The big cat sat.", [ins("a1", 4, "big ")]);
    h.apply({ changes: { from: 15, to: 15, insert: " really" } });  // before the final "."
    assert.equal(h.doc(), "The big cat sat really.");
    assert.equal(h.ops().length, 1);
    assert.equal(h.ops()[0].from, 4);
    assert.equal(h.ops()[0].newText, "big ");
    h.undo();
    assert.equal(h.doc(), "The big cat sat.");
    assert.equal(h.ops()[0].from, 4);
  });

  it("typing INSIDE an op splits it (middle untracked); undo re-merges to one op", () => {
    const h = harness("The big cat sat.", [ins("a1", 4, "big ")]);
    h.apply({ changes: { from: 5, to: 5, insert: "X" } });
    assert.equal(h.doc(), "The bXig cat sat.");
    assert.equal(h.ops().length, 2);                 // split around the human 'X'
    assert.equal(h.ops().every((o) => o.author === "FRO"), true);
    h.undo();
    assert.equal(h.doc(), "The big cat sat.");
    assert.equal(h.ops().length, 1);                 // coalesced back
    assert.equal(h.ops()[0].newText, "big ");
  });
});

// The exact report: editing a SUBSTITUTION's added text dropped its struck-out
// removal, and undo/redo then thrashed. These pin both halves against real history.
describe("track-cm: editing a substitution keeps its removal, and undo/redo restore it exactly", () => {
  it("deleting the front of the addition preserves the removal; undo restores the whole op", () => {
    // doc shows "like" (newText); baseline "love" (oldText) is struck-through, not in doc
    const h = harness("I like cats.", [sub("s1", 2, "like", "love")]);
    h.apply({ changes: { from: 2, to: 3, insert: "" } });    // delete the leading "l"
    assert.equal(h.doc(), "I ike cats.");
    // the removal must still be pending somewhere in the ops (this was the bug)
    assert.equal(h.ops().some((o) => o.oldText === "love"), true);
    // undo restores the exact original op AND text — not a mangled, partly-untracked op
    h.undo();
    assert.equal(h.doc(), "I like cats.");
    assert.equal(h.ops().length, 1);
    assert.equal(h.ops()[0].newText, "like");
    assert.equal(h.ops()[0].oldText, "love");
    // redo returns to the edited state deterministically
    h.redo();
    assert.equal(h.doc(), "I ike cats.");
    assert.equal(h.ops().some((o) => o.oldText === "love"), true);
  });

  it("a batch of grouped keystrokes undoes as one, restoring the op exactly", () => {
    const h = harness("The big cat sat.", [ins("a1", 4, "big ")]);
    // three keystrokes with the same userEvent → CM groups them into one history event
    h.type({ changes: { from: 16, to: 16, insert: "X" } });
    h.type({ changes: { from: 17, to: 17, insert: "Y" } });
    h.type({ changes: { from: 18, to: 18, insert: "Z" } });
    assert.equal(h.doc(), "The big cat sat.XYZ");
    h.undo();                                        // ONE undo transaction carries several inverses
    assert.equal(h.doc(), "The big cat sat.");
    assert.equal(h.ops().length, 1);
    assert.equal(h.ops()[0].from, 4);
    assert.equal(h.ops()[0].newText, "big ");
  });
});

// ── track-cm.undo.test.mjs ────────────────────────────────────────────────────────────────────────
// A BROAD undo/redo suite on top of the one above: type / accept / reject / accept-all / reject-all,
// each interleaved and each undone AND redone, asserting the doc and the op-log land exactly where a
// track-changes user expects. accept/reject go through the real engine and dispatch EXACTLY what the
// plugin dispatches (engine result as a setSuggestions effect, plus the buffer edit when there is one),
// each in its own history group (isolateHistory — a real click is isolated in time anyway).
function harness2(doc: string, ops: TrackRecord[]) {
  const field = makeSuggestionField();
  const invert = makeInvertedEffects(field);
  const target = {
    state: EditorState.create({ doc, extensions: [history(), field, invert] }),
    dispatch(tr: Transaction) { target.state = tr.state; },
  };
  target.state = target.state.update({
    effects: setSuggestions.of(ops), annotations: Transaction.addToHistory.of(false),
  }).state;
  const put = (spec: TransactionSpec) => { target.state = target.state.update(spec).state; };
  const H = {
    ops: () => target.state.field(field),
    doc: () => target.state.doc.toString(),
    // a human edit as its own undo step
    apply: (spec: TransactionSpec) => put({ ...spec, annotations: [isolateHistory.of("full")] }),
    // a grouped keystroke (same userEvent → CM may batch adjacent ones)
    type: (spec: TransactionSpec) => put({ ...spec, annotations: Transaction.userEvent.of("input.type") }),
    undo: () => undo(target),
    redo: () => redo(target),
    accept: (id: string) => { const r = engine.acceptSuggestion(H.ops(), id);
      put({ effects: setSuggestions.of(r.suggestions), annotations: [isolateHistory.of("full")] }); },
    reject: (id: string) => { const r = engine.rejectSuggestion(H.ops(), id);
      const s: TransactionSpec = { effects: setSuggestions.of(r.suggestions), annotations: [isolateHistory.of("full")] };
      if (r.edit) s.changes = r.edit; put(s); },
    acceptAll: () => { const r = engine.acceptAll(H.ops());
      put({ effects: setSuggestions.of(r.suggestions), annotations: [isolateHistory.of("full")] }); },
    rejectAll: () => { const r = engine.rejectAll(H.ops());
      const s: TransactionSpec = { effects: setSuggestions.of(r.suggestions), annotations: [isolateHistory.of("full")] };
      if (r.edits.length) s.changes = r.edits; put(s); },
  };
  return H;
}

// every op's newText must sit exactly where it claims in the live doc
const sits = (h: ReturnType<typeof harness2>) => h.ops().every((o) => !o.newText || h.doc().slice(o.from, o.from + o.newText.length) === o.newText);

describe("track-cm undo/redo: human-edit staircases", () => {
  it("two separate human edits undo and redo one step at a time, ops staying consistent", () => {
    const h = harness2("The big cat.", [ins("a1", 4, "big ")]);
    h.apply({ changes: { from: 0, to: 0, insert: "X" } });   // "XThe big cat."
    assert.equal(sits(h), true);
    h.apply({ changes: { from: h.doc().length, to: h.doc().length, insert: "Y" } }); // "XThe big cat.Y"
    assert.equal(h.doc(), "XThe big cat.Y");
    assert.equal(sits(h), true);
    h.undo();
    assert.equal(h.doc(), "XThe big cat.");
    h.undo();
    assert.equal(h.doc(), "The big cat.");
    assert.equal(h.ops()[0].from, 4);
    assert.equal(sits(h), true);
    h.redo();
    assert.equal(h.doc(), "XThe big cat.");
    h.redo();
    assert.equal(h.doc(), "XThe big cat.Y");
    assert.equal(h.ops().length, 1);
    assert.equal(h.ops()[0].newText, "big ");
    assert.equal(sits(h), true);
  });

  it("typing inside a substitution splits it; undo re-merges, redo re-splits — exactly", () => {
    const h = harness2("I like cats.", [sub("s1", 2, "like", "love")]);
    h.apply({ changes: { from: 4, to: 4, insert: "X" } });   // inside "like"
    assert.equal(h.doc(), "I liXke cats.");
    assert.equal(h.ops().length, 2);
    assert.equal(h.ops().some((o) => o.oldText === "love"), true);
    h.undo();
    assert.equal(h.doc(), "I like cats.");
    assert.equal(h.ops().length, 1);
    assert.equal(h.ops()[0].newText, "like");
    assert.equal(h.ops()[0].oldText, "love");
    h.redo();
    assert.equal(h.doc(), "I liXke cats.");
    assert.equal(h.ops().length, 2);
    assert.equal(sits(h), true);
  });

  it("deleting a substitution's whole addition leaves a pending deletion; undo/redo exact", () => {
    const h = harness2("I like cats.", [sub("s1", 2, "like", "love")]);
    h.apply({ changes: { from: 2, to: 6, insert: "" } });    // delete "like"
    assert.equal(h.doc(), "I  cats.");
    assert.equal(h.ops().length, 1);
    assert.equal(h.ops()[0].kind, "del");
    assert.equal(h.ops()[0].oldText, "love");
    h.undo();
    assert.equal(h.doc(), "I like cats.");
    assert.equal(h.ops()[0].newText, "like");
    assert.equal(h.ops()[0].oldText, "love");
    h.redo();
    assert.equal(h.doc(), "I  cats.");
    assert.equal(h.ops()[0].kind, "del");
  });

  it("a batch of grouped keystrokes undoes and REDOES as one", () => {
    const h = harness2("The big cat.", [ins("a1", 4, "big ")]);
    h.type({ changes: { from: 12, to: 12, insert: "X" } });
    h.type({ changes: { from: 13, to: 13, insert: "Y" } });
    h.type({ changes: { from: 14, to: 14, insert: "Z" } });
    assert.equal(h.doc(), "The big cat.XYZ");
    h.undo();
    assert.equal(h.doc(), "The big cat.");
    h.redo();
    assert.equal(h.doc(), "The big cat.XYZ");
    assert.equal(h.ops().length, 1);
    assert.equal(h.ops()[0].newText, "big ");
  });
});

describe("track-cm undo/redo: accept / reject are undoable AND redoable", () => {
  it("reject → undo restores text+op → redo re-rejects", () => {
    const h = harness2("The big cat.", [ins("a1", 4, "big ")]);
    h.reject("a1");
    assert.equal(h.doc(), "The cat.");
    assert.equal(h.ops().length, 0);
    h.undo();
    assert.equal(h.doc(), "The big cat.");
    assert.deepEqual(h.ops().map((o) => o.id), ["a1"]);
    h.redo();
    assert.equal(h.doc(), "The cat.");
    assert.equal(h.ops().length, 0);
  });

  it("accept → undo restores the op with no text change → redo re-accepts", () => {
    const h = harness2("The big cat.", [ins("a1", 4, "big ")]);
    h.accept("a1");
    assert.equal(h.doc(), "The big cat.");
    assert.equal(h.ops().length, 0);
    h.undo();
    assert.equal(h.doc(), "The big cat.");
    assert.deepEqual(h.ops().map((o) => o.id), ["a1"]);
    h.redo();
    assert.equal(h.ops().length, 0);
  });

  it("accept-all → undo brings every op back → redo clears again", () => {
    const h = harness2("The big dog.", [ins("a1", 4, "big "), sub("a2", 8, "dog", "cat")]);
    h.acceptAll();
    assert.equal(h.ops().length, 0);
    assert.equal(h.doc(), "The big dog.");
    h.undo();
    assert.equal(h.ops().length, 2);
    assert.equal(h.doc(), "The big dog.");
    assert.equal(sits(h), true);
    h.redo();
    assert.equal(h.ops().length, 0);
  });

  it("reject-all → undo restores text and every op → redo re-rejects all", () => {
    const h = harness2("The big dog.", [ins("a1", 4, "big "), sub("a2", 8, "dog", "cat")]);
    h.rejectAll();
    assert.equal(h.doc(), "The cat.");
    assert.equal(h.ops().length, 0);
    h.undo();
    assert.equal(h.doc(), "The big dog.");
    assert.equal(h.ops().length, 2);
    assert.equal(sits(h), true);
    h.redo();
    assert.equal(h.doc(), "The cat.");
    assert.equal(h.ops().length, 0);
  });
});

describe("track-cm undo/redo: typing interleaved with accept/reject undoes in the right order", () => {
  it("type then accept: the FIRST undo reverses the accept, not the typing (the reported bug)", () => {
    const h = harness2("The big cat.", [ins("a1", 4, "big ")]);
    h.type({ changes: { from: 11, to: 11, insert: " fast" } });   // before "." → "The big cat fast."
    assert.equal(h.doc(), "The big cat fast.");
    h.accept("a1");
    assert.equal(h.ops().length, 0);
    h.undo();                                       // must undo the ACCEPT
    assert.equal(h.doc(), "The big cat fast.");       // typing untouched
    assert.deepEqual(h.ops().map((o) => o.id), ["a1"]); // op restored
    h.undo();                                       // now the typing
    assert.equal(h.doc(), "The big cat.");
    assert.equal(h.ops().length, 1);
  });

  it("reject then type: undo peels the typing first, then the reject restores text+op", () => {
    const h = harness2("The big cat.", [ins("a1", 4, "big ")]);
    h.reject("a1");                                  // "The cat.", op gone
    h.type({ changes: { from: 7, to: 7, insert: " now" } });  // "The cat now."
    assert.equal(h.doc(), "The cat now.");
    h.undo();                                       // undo the typing
    assert.equal(h.doc(), "The cat.");
    assert.equal(h.ops().length, 0);
    h.undo();                                       // undo the reject
    assert.equal(h.doc(), "The big cat.");
    assert.equal(h.ops().length, 1);
    assert.equal(h.ops()[0].newText, "big ");
  });
});
