// The editor chunk's id rule over the vendored field (plans/file-review.md, Slice 5): an id the ledger holds is
// never minted again. The engine mints a split's right half against the ids in play NOW (`X~1` for the first
// split of X) and the vendored field passes it no `mint`, so once the person decides a fragment — `X~1` leaves the
// field for the ledger — the next split of the same parent minted `X~1` a second time (found 2026-09-06). A save
// then named one id as decided AND pending, which the host refuses (requireDecisions, exit 2 → `host-error` in
// the kernel) although the records fit the text; and a decision on the new `X~1` replaced the earlier entry by id,
// so the first decision was never logged and one undo emptied both. These cases drive the real field, engine and
// history headless, the way editor-track.test.ts does, and pin the rule: the two lists a save sends never share
// an id, every decision stays in the ledger, and undo/redo restore what history recorded.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { EditorState, Transaction, type TransactionSpec } from "@codemirror/state";
import { undo, redo, isolateHistory } from "@codemirror/commands";
import { extensionsFor, trackSetup, type TrackLedger } from "./editor-chunk";
import { setSuggestions } from "../../vendor/track-changents/obsidian/src/track-cm.js";
import * as engine from "../../vendor/track-changents/engine.js";
import type { TrackRecord } from "./track-decorations";

const noop = () => {};
const ins = (id: string, from: number, newText: string, author = "web"): TrackRecord => ({ id, author, ts: 1, kind: "ins", from, newText, oldText: "" });
const idsOf = (l: TrackLedger) => [...l.accepted, ...l.rejected].map((e) => e.id);

/** A headless tracked editor: the chunk's real extension set plus a track setup, seeded as mount() seeds it. */
function editor(doc: string, records: TrackRecord[], ext = "md") {
  const t = trackSetup({ suggestions: records, authorColor: () => null });
  const target = {
    state: EditorState.create({ doc, extensions: extensionsFor(ext, { onChange: noop, onSave: noop }, t) }).update(t.seed).state,
    dispatch(tr: Transaction) { target.state = tr.state; },
  };
  const put = (spec: TransactionSpec): Transaction => { const tr = target.state.update(spec); target.state = tr.state; return tr; };
  const h = {
    doc: () => target.state.doc.toString(),
    ops: () => t.suggestions(target.state),
    ids: () => h.ops().map((o) => String(o.id)),
    ledger: () => t.ledger(target.state),
    type: (from: number, insert: string) => put({ changes: { from, to: from, insert }, annotations: [isolateHistory.of("full")] }),
    /** A keystroke as the view dispatches one: user event `input.type`, the caret after the text — what indentOnInput
     *  and history's grouping key on. */
    keystroke: (from: number, insert: string) => put({ changes: { from, to: from, insert }, selection: { anchor: from + insert.length }, userEvent: "input.type" }),
    apply: (spec: TransactionSpec) => put(spec),
    resolve: (from: number, reject: boolean) => { const s = t.resolve(target.state, from, reject); assert.ok(s, `a change starts at ${from}`); put(s!); },
    undo: () => undo(target),
    redo: () => redo(target),
    /** The save's invariant, the host's requireDecisions: no id is both pending and decided. */
    disjoint: () => { for (const id of idsOf(h.ledger())) assert.ok(!h.ids().includes(id), `${id} is decided and still pending`); },
    /** The host's fitRecords rule: every record's text sits at its offset in the buffer being saved. */
    fits: () => { const d = h.doc(); for (const o of h.ops()) { const t = o.newText || ""; assert.equal(d.slice(o.from, o.from + t.length), t, `${o.id} at ${o.from} holds ${JSON.stringify(t)}`); } },
  };
  return h;
}

// The finding's scenario, step for step.
const DOC = "The big fluffy cat sat.";
const X = ins("X", 4, "big fluffy ");

test("a decided fragment's id is not minted again by the next split of its parent: the save's two lists stay disjoint", () => {
  const h = editor(DOC, [X]);
  h.type(8, "very ");                                            // "The big very fluffy cat sat." — X splits around the typing
  assert.deepEqual(h.ops().map((o) => [o.id, o.from, o.newText]), [["X", 4, "big "], ["X~1", 13, "fluffy "]]);
  h.resolve(13, false);                                          // accept the right fragment
  assert.deepEqual(h.ids(), ["X"]);
  assert.deepEqual(h.ledger(), { accepted: [{ id: "X~1", oldText: "", newText: "fluffy " }], rejected: [] });
  const before = h.ops();
  h.type(6, "g");                                                // "The bigg very fluffy cat sat." — X splits again
  assert.equal(h.doc(), "The bigg very fluffy cat sat.");
  // the engine alone would mint X~1 here (it knows only the ids in play); the chunk renames it to the parent's next suffix
  assert.deepEqual(engine.ingestHumanChanges(before, [{ from: 6, to: 6, insert: "g" }]).map((o) => o.id), ["X", "X~1"], "the engine's own result, the collision");
  assert.deepEqual(h.ids(), ["X", "X~2"]);
  h.disjoint();
  // only the id changed: the fragment's span and texts are the engine's
  const [, frag] = h.ops();
  assert.equal(frag.from, 7); assert.equal(frag.newText, "g "); assert.equal(frag.kind, "ins");
  assert.deepEqual(h.ledger().accepted.map((e) => e.id), ["X~1"], "the earlier decision is untouched");
});

test("a second decision joins the first in the ledger; undoing it leaves the first in place", () => {
  const h = editor(DOC, [X]);
  h.type(8, "very ");
  h.resolve(13, false);
  h.type(6, "g");
  h.resolve(7, false);                                           // accept the new fragment
  assert.deepEqual(h.ids(), ["X"]);
  assert.deepEqual(h.ledger().accepted, [{ id: "X~1", oldText: "", newText: "fluffy " }, { id: "X~2", oldText: "", newText: "g " }]);
  h.disjoint();
  assert.equal(h.undo(), true);                                  // the second accept, not the first
  assert.deepEqual(h.ids(), ["X", "X~2"]);
  assert.deepEqual(h.ledger().accepted.map((e) => e.id), ["X~1"], "one undo removes one decision");
  assert.equal(h.redo(), true);
  assert.deepEqual(h.ledger().accepted.map((e) => e.id), ["X~1", "X~2"]);
});

test("undo of the typing restores the records before it; redo restores the renamed list history recorded", () => {
  const h = editor(DOC, [X]);
  h.type(8, "very ");
  h.resolve(13, false);
  h.type(6, "g");
  assert.equal(h.undo(), true);
  assert.equal(h.doc(), "The big very fluffy cat sat.");
  assert.deepEqual(h.ids(), ["X"]);
  assert.deepEqual(h.ledger().accepted.map((e) => e.id), ["X~1"], "typing is no decision: undoing it leaves the ledger");
  assert.equal(h.redo(), true);
  assert.deepEqual(h.ids(), ["X", "X~2"], "history holds the renamed list, not a re-derived one");
  h.disjoint();
  assert.equal(h.undo(), true); assert.equal(h.undo(), true);    // the typing, then the accept
  assert.deepEqual(h.ids(), ["X", "X~1"]);
  assert.deepEqual(h.ledger(), { accepted: [], rejected: [] });
});

test("a rejected id is taken too: the ledger's other side counts", () => {
  const h = editor(DOC, [X]);
  h.type(8, "very ");
  h.resolve(13, true);                                           // reject the right fragment: its text leaves
  assert.equal(h.doc(), "The big very cat sat.");
  assert.deepEqual(h.ledger().rejected.map((e) => e.id), ["X~1"]);
  h.type(6, "g");
  assert.deepEqual(h.ids(), ["X", "X~2"]);
  h.disjoint();
});

test("each decided split counts up: the ledger keeps every fragment and the field never reuses one", () => {
  const h = editor(DOC, [X]);
  h.type(8, "very ");
  h.resolve(13, false);                                          // X~1 decided
  h.type(6, "g");                                                // X~2 minted
  h.resolve(7, false);                                           // X~2 decided
  h.type(5, "i");                                                // "The biigg very fluffy cat sat." — X splits a third time
  assert.deepEqual(h.ids(), ["X", "X~3"]);
  assert.deepEqual(idsOf(h.ledger()), ["X~1", "X~2"]);
  h.disjoint();
});

test("the parent of a fragment is its id less the last suffix: a decided X~1~1 makes the next split of X~1 mint X~1~2", () => {
  // two records from the start, the second already a fragment by name
  const h = editor("aa bb cccc dd", [ins("X", 0, "aa "), ins("X~1", 6, "cccc ")]);
  h.type(8, "-");                                                // "aa bb cc-cc dd": X~1 splits into X~1 ('cc') and X~1~1 ('cc ')
  assert.deepEqual(h.ids(), ["X", "X~1", "X~1~1"]);
  h.resolve(9, false);                                           // accept X~1~1
  assert.deepEqual(idsOf(h.ledger()), ["X~1~1"]);
  h.type(7, "-");                                                // "aa bb c-c-cc dd": X~1 ('cc', 6..8) splits again, inside it
  assert.deepEqual(h.ids(), ["X", "X~1", "X~1~2"]);
  h.disjoint();
});

test("without a collision an ordinary keystroke is untouched: the records are exactly the engine's and the transaction carries no list effect", () => {
  const h = editor(DOC, [X]);
  const before = h.ops();
  const tr = h.type(8, "very ");
  assert.ok(!tr.effects.some((e) => e.is(setSuggestions)), "no explicit list rides on a plain keystroke");
  assert.deepEqual(h.ops(), engine.ingestHumanChanges(before, [{ from: 8, to: 8, insert: "very " }]));
  // with a non-empty ledger but no collision, still untouched
  h.resolve(13, false);
  const mid = h.ops();
  const tr2 = h.type(0, ">> ");                                  // above every change: a shift, no split
  assert.ok(!tr2.effects.some((e) => e.is(setSuggestions)));
  assert.deepEqual(h.ops(), engine.ingestHumanChanges(mid, [{ from: 0, to: 0, insert: ">> " }]));
  h.disjoint();
});

// ── Beyond the finding's sequence: the rename has to hold for every shape a keystroke's transaction takes ──────────

test("a re-split keystroke that also reindents its line (indentOnInput adds a change to the same transaction) leaves records that fit the text", () => {
  // A JS file: the chunk's own indentOnInput() is a transaction filter too, and a `}` typed on an otherwise blank line
  // makes it ADD a change (the line's indentation rewritten) to the person's keystroke. The renamed list has to be
  // computed over the transaction's final changes; a list computed over the keystroke alone describes another text,
  // and the field would take it verbatim — the very desync the plan's "typing remaps the changes" rules out.
  const h = editor("if (a) {\n  aa\n  \n}\n", [ins("X", 9, "  aa\n  ")], "js");
  h.type(14, "-");                                                 // X splits: X('  aa\n', 9) + X~1('  ', 15)
  assert.deepEqual(h.ids(), ["X", "X~1"]);
  h.resolve(15, false);                                            // X~1 decided
  const before = h.ops();
  h.keystroke(11, "}");                                            // inside X, closing the block: "  }aa" reindents to "}aa"
  assert.equal(h.doc(), "if (a) {\n}aa\n-  \n}\n", "the keystroke carried the reindent (indentOnInput fired)");
  h.fits();
  h.disjoint();
  // the engine over the transaction's one composed change (9..11 replaced by '}'): X's right part survives under its own id
  assert.deepEqual(h.ops(), engine.ingestHumanChanges(before, [{ from: 9, to: 11, insert: "}" }]));
  assert.deepEqual(h.ledger().accepted.map((e) => e.id), ["X~1"]);
});

test("two splits of one parent in one transaction (a two-cursor keystroke): every fragment gets an id of its own, none the ledger holds", () => {
  const h = editor(DOC, [X]);
  h.type(8, "very ");
  h.resolve(13, false);                                            // X~1 decided; field [X 'big ']
  const before = h.ops();
  const changes = [{ from: 5, to: 5, insert: "1" }, { from: 7, to: 7, insert: "2" }];
  h.apply({ changes, annotations: [isolateHistory.of("full")] });
  assert.equal(h.doc(), "The b1ig2 very fluffy cat sat.");
  const raw = engine.ingestHumanChanges(before, changes);
  assert.deepEqual(raw.map((o) => o.id), ["X", "X~2", "X~1"], "the engine's own result: the collision again, beside a fresh fragment");
  assert.deepEqual(h.ids(), ["X", "X~2", "X~3"]);
  h.fits();
  h.disjoint();
  assert.deepEqual(h.ops().map((o) => [o.from, o.newText]), raw.map((o) => [o.from, o.newText]), "only the colliding id changed");
});

test("keystrokes history groups into one event undo together across a rename: one undo restores the list before them, one redo the renamed list", () => {
  const h = editor(DOC, [X]);
  h.type(8, "very ");
  h.resolve(13, false);                                            // X~1 decided; field [X]
  h.keystroke(6, "g");                                             // X splits again: the fragment is renamed X~2
  h.keystroke(7, "h");                                             // adjacent typing: history joins it to the first
  assert.equal(h.doc(), "The bighg very fluffy cat sat.");
  assert.deepEqual(h.ids(), ["X", "X~2"]);
  const after = h.ops();
  assert.equal(h.undo(), true);
  assert.equal(h.doc(), "The big very fluffy cat sat.", "one undo takes both keystrokes");
  assert.deepEqual(h.ops().map((o) => [o.id, o.from, o.newText]), [["X", 4, "big "]], "the list before the first keystroke, the last of the grouped inverses");
  assert.deepEqual(h.ledger().accepted.map((e) => e.id), ["X~1"]);
  assert.equal(h.redo(), true);
  assert.deepEqual(h.ops(), after, "redo restores the recorded renamed list");
  h.disjoint();
});
