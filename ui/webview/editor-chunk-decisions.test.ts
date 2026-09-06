// The editor chunk's record of in-editor accepts and rejects is its `decisions` (plans/file-review.md, Slice 5:
// the save verb carries "the decisions taken in the editor, each {id, oldText, newText}"; file-view.ts's
// EditDecisions). The slice first named it a ledger — a word CONTEXT.md lists under Avoid for the comments log,
// which is where the host writes these very decisions — so a save trace's reader had two records of one set of
// decisions, told apart only by the word the glossary bans for one of them (the 2026-09-06 review). This file pins
// the vocabulary: the canonical contract is spelled `decisions`, and the old word survives only on the alias lines
// kept for callers that have not moved (each marked "old spelling"), which go with their last caller. The executed
// half runs the chunk's real extension set through EditorState, the way editor-track.test.ts does, so the aliases
// are proven to be the same field and the same object as the names they stand in for.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { EditorState, Transaction, type TransactionSpec } from "@codemirror/state";
import { EditorView, type ViewUpdate } from "@codemirror/view";
import { undo } from "@codemirror/commands";
import { extensionsFor, trackSetup, applyDecision, EMPTY_DECISIONS, EMPTY_LEDGER, type TrackDecisions, type TrackOpts } from "./editor-chunk";
import type { TrackRecord } from "./track-decorations";

const W = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const CHUNK = W("editor-chunk.ts");
const CONTEXT = fs.readFileSync(path.resolve(process.cwd(), "..", "CONTEXT.md"), "utf8");
const noop = () => {};

const ins = (id: string, from: number, newText: string): TrackRecord => ({ id, author: "web", ts: 1, kind: "ins", from, newText, oldText: "" });

/** A headless tracked editor over the chunk's real extension set, seeded as mount() seeds it; every transaction
 *  after the seed runs the update-listener facet the way EditorView.update does (over the new state). */
function editor(doc: string, records: TrackRecord[], listeners: Pick<TrackOpts, "onDecisions" | "onLedger">) {
  const t = trackSetup({ suggestions: records, authorColor: () => null, ...listeners });
  const fire = (tr: Transaction) => {
    const u = { view: undefined, state: tr.state, startState: tr.startState, transactions: [tr], changes: tr.changes, docChanged: tr.docChanged } as unknown as ViewUpdate;
    for (const listener of tr.state.facet(EditorView.updateListener)) listener(u);
  };
  const target = {
    state: EditorState.create({ doc, extensions: extensionsFor("md", { onChange: noop, onSave: noop }, t) }).update(t.seed).state,
    dispatch(tr: Transaction) { target.state = tr.state; fire(tr); },
  };
  const put = (spec: TransactionSpec) => { const tr = target.state.update(spec); target.state = tr.state; fire(tr); };
  return {
    t,
    state: () => target.state,
    type: (spec: TransactionSpec) => put(spec),
    accept: (from: number) => { const s = t.resolve(target.state, from, false); assert.ok(s, `a change starts at ${from}`); put(s!); },
    undo: () => undo(target),
  };
}

// ── the vocabulary, at source ────────────────────────────────────────────────────────────────────

test("CONTEXT.md reserves against the old word for the comments log, which is where the editor's decisions are written", () => {
  const entry = CONTEXT.slice(CONTEXT.indexOf("**Comments log**"));
  const avoid = entry.split("\n").find((l) => l.startsWith("_Avoid_:"));
  assert.ok(avoid, "the Comments log entry has an Avoid line");
  assert.match(avoid!, /\bledger\b/, "the word the chunk must not adopt for the record beside the log");
});

test("the chunk's contract is spelled `decisions`: the types, the option's callback, the handle and the setup", () => {
  assert.match(CHUNK, /export interface TrackDecision \{ id: string; oldText: string; newText: string \}/);
  assert.match(CHUNK, /export interface TrackDecisions \{ accepted: TrackDecision\[\]; rejected: TrackDecision\[\] \}/);
  assert.match(CHUNK, /onDecisions\?: \(decisions: TrackDecisions\) => void;/);
  assert.match(CHUNK, /export interface TrackHandle \{\n\s*suggestions\(\): unknown\[\];\n\s*decisions\(\): TrackDecisions;/);
  assert.match(CHUNK, /decisions\(state: EditorState\): TrackDecisions;/);
  assert.match(CHUNK, /export const EMPTY_DECISIONS: TrackDecisions = \{ accepted: \[\], rejected: \[\] \};/);
  assert.match(CHUNK, /export function applyDecision\(decisions: TrackDecisions, d: Decision, add: boolean\): TrackDecisions \{/);
  assert.match(CHUNK, /const decisionsField = StateField\.define<TrackDecisions>\(\{\n\s*create: \(\) => EMPTY_DECISIONS,/);
  // the handle reads the LIVE state under the canonical name; the listener reports on the field's identity
  assert.match(CHUNK, /decisions: \(\) => track\.decisions\(view\.state\),/);
  assert.match(CHUNK, /const next = u\.state\.field\(decisionsField\);\n\s*if \(u\.startState\.field\(decisionsField\) === next\) return;\n\s*if \(opts\.onDecisions\) opts\.onDecisions\(next\);/);
});

test("the old word appears in the chunk only on lines marked as the old spelling — aliases that go with their last caller", () => {
  const lines = CHUNK.split("\n");
  const unmarked = lines.map((l, i) => [i + 1, l] as const).filter(([, l]) => /ledger/i.test(l) && !/old spelling/.test(l));
  assert.deepEqual(unmarked, [], "every use of the old word is an alias line or the note explaining them");
  // and each alias line is one of the kept shapes: a type alias, the same-object const, an optional callback typed as
  // the canonical one, or a reader that reads the canonical field — never a definition of its own
  const aliasCode = lines.filter((l) => /ledger/i.test(l) && !l.trim().startsWith("//"));
  for (const l of aliasCode) {
    assert.match(l, /= TrackDecision;|= TrackDecisions;|= EMPTY_DECISIONS;|TrackOpts\["onDecisions"\]|TrackHandle\["decisions"\]|TrackSetup\["decisions"\]|state\.field\(decisionsField\)|track\.decisions\(view\.state\)|opts\.onLedger\(next\)/, l);
  }
  // no identifier of the old spelling is DEFINED as a field, an effect or a function: the aliases stand in for names
  assert.doesNotMatch(CHUNK, /const ledger[A-Za-z]* = |function [a-z]*[Ll]edger|interface Track[Ll]edger/);
});

// ── executed: the canonical names carry the decisions; the aliases read the same field and object ──

test("onDecisions reports a decision, its undo and nothing else, with the very object the handle's decisions() returns", () => {
  const seen: TrackDecisions[] = [];
  const h = editor("The cat.", [ins("a1", 4, "big ")], { onDecisions: (d) => seen.push(d) });
  assert.equal(h.t.decisions(h.state()), EMPTY_DECISIONS, "a fresh mount starts at the shared empty object");
  h.accept(4);
  assert.equal(seen.length, 1, "an accept reports once");
  assert.equal(seen[0], h.t.decisions(h.state()), "with the object the field holds (identity, so a listener can key on it)");
  assert.deepEqual(seen[0], { accepted: [{ id: "a1", oldText: "", newText: "big " }], rejected: [] });
  // typing remaps records, not decisions: no report
  h.type({ changes: { from: 0, insert: "x" } });
  assert.equal(seen.length, 1, "a keystroke is no decision");
  h.undo();   // the keystroke
  h.undo();   // the accept
  assert.equal(seen.length, 2, "the undo of the accept is reported");
  assert.deepEqual(seen[1], EMPTY_DECISIONS, "…as the empty decisions");
});

test("the old spelling still works for a caller that has not moved: onLedger fires with the same object, and ledger() reads the same field", () => {
  const viaOld: TrackDecisions[] = [];
  const viaNew: TrackDecisions[] = [];
  const h = editor("The cat.", [ins("a1", 4, "big ")], { onLedger: (d) => viaOld.push(d), onDecisions: (d) => viaNew.push(d) });
  h.accept(4);
  assert.equal(viaOld.length, 1, "file-view.ts's callback, by the old spelling, still runs");
  assert.equal(viaOld[0], viaNew[0], "both spellings report the one object");
  assert.equal(h.t.ledger(h.state()), h.t.decisions(h.state()), "the setup's old reader is the canonical field");
  // a caller passing only the old spelling is still served (file-view.ts today)
  const onlyOld: TrackDecisions[] = [];
  const h2 = editor("The cat.", [ins("a1", 4, "big ")], { onLedger: (d) => onlyOld.push(d) });
  h2.accept(4);
  assert.equal(onlyOld.length, 1);
  // and neither listener: a decision still lands, and nothing throws
  const h3 = editor("The cat.", [ins("a1", 4, "big ")], {});
  h3.accept(4);
  assert.deepEqual(h3.t.decisions(h3.state()).accepted.map((e) => e.id), ["a1"]);
});

test("EMPTY_LEDGER is EMPTY_DECISIONS itself, so the reducer's same-object contract holds under either name", () => {
  assert.equal(EMPTY_LEDGER, EMPTY_DECISIONS);
  assert.equal(applyDecision(EMPTY_LEDGER, { side: "accepted", entries: [] }, true), EMPTY_DECISIONS);
  assert.deepEqual(EMPTY_DECISIONS, { accepted: [], rejected: [] }, "and neither is ever mutated");
});
