// The editor chunk's record of in-editor accepts and rejects is its `decisions` (plans/file-review.md, Slice 5:
// the save verb carries "the decisions taken in the editor, each {id, oldText, newText}"; file-view.ts's
// EditDecisions). The slice's first name for it was a word CONTEXT.md lists under Avoid for the comments log,
// which is where the host writes these very decisions — so a save trace's reader had two records of one set of
// decisions, told apart only by the word the glossary bans for one of them (the 2026-09-06 review). This file pins
// the vocabulary: the canonical contract is spelled `decisions`, and the old word appears nowhere in the chunk nor in
// any other webview module — the round-2 aliases for callers that had not moved (the viewer, the chunk's own tests)
// went with the consolidation pass that moved them all. The executed half runs the chunk's real extension set through
// EditorState, the way editor-track.test.ts does, so the canonical callback and reader are proven to carry the field.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { EditorState, Transaction, type TransactionSpec } from "@codemirror/state";
import { EditorView, type ViewUpdate } from "@codemirror/view";
import { undo } from "@codemirror/commands";
import { extensionsFor, trackSetup, applyDecision, EMPTY_DECISIONS, type TrackDecisions, type TrackOpts } from "./editor-chunk";
import type { TrackRecord } from "./track-decorations";

const W = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const CHUNK = W("editor-chunk.ts");
const CONTEXT = fs.readFileSync(path.resolve(process.cwd(), "..", "CONTEXT.md"), "utf8");
const WEBVIEW = path.resolve(process.cwd(), "..", "ui", "webview");
const OLD = new RegExp("led" + "ger", "i");   // assembled so this file's own text is not a hit
const noop = () => {};

const ins = (id: string, from: number, newText: string): TrackRecord => ({ id, author: "web", ts: 1, kind: "ins", from, newText, oldText: "" });

/** A headless tracked editor over the chunk's real extension set, seeded as mount() seeds it; every transaction
 *  after the seed runs the update-listener facet the way EditorView.update does (over the new state). */
function editor(doc: string, records: TrackRecord[], listeners: Pick<TrackOpts, "onDecisions">) {
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
  assert.match(avoid!, OLD, "the word the chunk must not adopt for the record beside the log");
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

test("the old word appears nowhere in the chunk, and no webview module or test names an alias shape of it", () => {
  const hits = CHUNK.split("\n").map((l, i) => [i + 1, l] as const).filter(([, l]) => OLD.test(l));
  assert.deepEqual(hits, [], "editor-chunk.ts says decisions and nothing else");
  // the shapes a caller of the round-2 aliases wrote: the type, the const, the option, the handle's and the setup's readers
  const shapes = new RegExp(["\\bTrack" + "Ledger\\b", "\\bEMPTY_" + "LEDGER\\b", "\\bon" + "Ledger\\b", "\\." + "ledger\\(", "\\b" + "ledger\\(\\): "].join("|"));
  const SELF = "editor-chunk-decisions.test.ts";
  const hitFiles = fs.readdirSync(WEBVIEW).filter((f) => f.endsWith(".ts") && f !== SELF)
    .filter((f) => shapes.test(fs.readFileSync(path.join(WEBVIEW, f), "utf8")));
  assert.deepEqual(hitFiles, [], "pass onDecisions and read decisions(): the aliases are gone, and a new caller must not re-mint them");
  assert.ok(fs.readdirSync(WEBVIEW).includes(SELF), "this file's own name, or its regexes count as a caller");
});

// ── executed: the canonical names carry the decisions ─────────────────────────────────────────────

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

test("a caller with no listener is still served: a decision lands and nothing throws", () => {
  const h = editor("The cat.", [ins("a1", 4, "big ")], {});
  h.accept(4);
  assert.deepEqual(h.t.decisions(h.state()).accepted.map((e) => e.id), ["a1"]);
  assert.equal(applyDecision(EMPTY_DECISIONS, { side: "accepted", entries: [] }, true), EMPTY_DECISIONS, "the reducer's same-object contract");
  assert.deepEqual(EMPTY_DECISIONS, { accepted: [], rejected: [] }, "and the shared empty object is never mutated");
});
