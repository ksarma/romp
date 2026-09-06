// The editor chunk's `track` option (plans/file-review.md, Slice 5; decision 14): romp's OWN half of the
// tracked-changes editor — the decisions kept net of undo, the click policy, the marks built from the
// vendored field, and the transactions an in-editor accept or reject dispatches. The vendored field itself is
// covered by the ported upstream oracle (track-cm-oracle.test.ts); this file tests what romp adds on top.
// Executed where CodeMirror needs no DOM (EditorState + history + the decoration facet, and the update-listener
// facet run the way EditorView.update runs it); the DOM-only parts (widget rendering, the mouse handlers' wiring)
// are pinned at source.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { EditorState, Transaction, type TransactionSpec } from "@codemirror/state";
import { EditorView, type DecorationSet, type Decoration, type ViewUpdate } from "@codemirror/view";
import { undo, redo, isolateHistory } from "@codemirror/commands";
import { extensionsFor, trackSetup, applyDecision, EMPTY_DECISIONS, type TrackDecisions, type TrackSetup } from "./editor-chunk";
import { trackClickAction, idsAtPosition, displayItems, CLS, CHANGE_SEL, type TrackRecord } from "./track-decorations";

const W = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
/** A source with its comment lines removed, for bans: a header may NAME what the code must not contain. */
const codeOnly = (src: string) => src.split("\n").filter((l) => { const t = l.trim(); return !t.startsWith("//") && !t.startsWith("*") && !t.startsWith("/*"); }).join("\n");
const DECO = W("track-decorations.ts");
const DECO_CODE = codeOnly(DECO);
const CHUNK = W("editor-chunk.ts");
const noop = () => {};

const ins = (id: string, from: number, newText: string, author = "web"): TrackRecord => ({ id, author, ts: 1, kind: "ins", from, newText, oldText: "" });
const del = (id: string, from: number, oldText: string, author = "web"): TrackRecord => ({ id, author, ts: 1, kind: "del", from, newText: "", oldText });
const sub = (id: string, from: number, newText: string, oldText: string, author = "web"): TrackRecord => ({ id, author, ts: 1, kind: "sub", from, newText, oldText });

/** A headless tracked editor: the chunk's real extension set plus a track setup, seeded as mount() seeds it, with
 *  a dispatch target @codemirror/commands' undo/redo can drive. Every transaction after the seed also runs the
 *  update-listener facet the way EditorView.update does (view/dist/index.js: `for (let listener of
 *  this.state.facet(updateListener)) listener(update)`, over the NEW state), with an update that carries what a
 *  ViewUpdate carries minus the view. So the listeners the chunk's extension set actually holds execute — onChange
 *  keyed on docChanged, onDecisions keyed on the decisions field's identity, the decorations' onOpsChanged relay — and a
 *  listener dropped from that set is absent from the facet and never fires here either. The seed itself runs no
 *  listener, as in mount(), where it lands before the view exists. Unlike EditorView.update (which logs a
 *  listener's exception and goes on), this lets it throw: a listener that needs the view fails the test. */
function editor(doc: string, records: TrackRecord[], onDecisions?: (d: TrackDecisions) => void) {
  const t = trackSetup({ suggestions: records, onDecisions, authorColor: (a) => (a === "web" ? "#abcdef" : null) });
  let changed = 0;
  const fire = (tr: Transaction) => {
    const u = { view: undefined, state: tr.state, startState: tr.startState, transactions: [tr], changes: tr.changes, docChanged: tr.docChanged } as unknown as ViewUpdate;
    for (const listener of tr.state.facet(EditorView.updateListener)) listener(u);
  };
  const target = {
    state: EditorState.create({ doc, extensions: extensionsFor("md", { onChange: () => { changed++; }, onSave: noop }, t) }).update(t.seed).state,
    dispatch(tr: Transaction) { target.state = tr.state; fire(tr); },
  };
  const put = (spec: TransactionSpec) => { const tr = target.state.update(spec); target.state = tr.state; fire(tr); };
  return {
    t,
    /** How many times the mount's onChange ran: the chunk's listener fires it once per document-changing transaction. */
    changes: () => changed,
    doc: () => target.state.doc.toString(),
    ops: () => t.suggestions(target.state),
    decisions: () => t.decisions(target.state),
    type: (spec: TransactionSpec) => put({ ...spec, annotations: [isolateHistory.of("full")] }),
    resolve: (from: number, reject: boolean) => { const s = t.resolve(target.state, from, reject); if (s) put(s); return s; },
    undo: () => undo(target),
    redo: () => redo(target),
    /** The mark and widget specs the decoration facet holds, in document order. */
    decos: () => {
      const out: Array<{ from: number; to: number; spec: Decoration["spec"] }> = [];
      for (const v of target.state.facet(EditorView.decorations)) {
        if (typeof v === "function") continue;                      // a view-dependent provider: none of ours
        (v as DecorationSet).between(0, target.state.doc.length, (from, to, d) => { out.push({ from, to, spec: d.spec }); });
      }
      return out.sort((a, b) => a.from - b.from || a.to - b.to);
    },
  };
}

// ── the click policy (departure 3 in track-decorations.ts) ───────────────────────────────────────

test("trackClickAction: click accepts; Alt everywhere, Cmd on macOS, Ctrl elsewhere reject; the rest is the browser's", () => {
  const plain = { button: 0 };
  assert.equal(trackClickAction(plain, false), "accept");
  assert.equal(trackClickAction(plain, true), "accept");
  assert.equal(trackClickAction({ button: 0, altKey: true }, false), "reject", "Alt rejects on every platform");
  assert.equal(trackClickAction({ button: 0, altKey: true }, true), "reject");
  assert.equal(trackClickAction({ button: 0, metaKey: true }, true), "reject", "Cmd rejects on macOS");
  assert.equal(trackClickAction({ button: 0, ctrlKey: true }, false), "reject", "Ctrl rejects elsewhere");
  assert.equal(trackClickAction({ button: 0, ctrlKey: true }, true), null, "macOS Ctrl-click is the context-menu gesture: not ours");
  assert.equal(trackClickAction({ button: 0, metaKey: true }, false), "accept", "a bare Meta off macOS is no modifier of ours");
  assert.equal(trackClickAction({ button: 2 }, false), null, "a secondary button never decides");
  assert.equal(trackClickAction({ button: 1, altKey: true }, false), null);
  assert.equal(trackClickAction({}, false), "accept", "a synthetic event without a button counts as primary");
});

// ── idsAtPosition: the click's key is the display item's start, the same planning the marks use ──

test("idsAtPosition maps a mark's data-hk-from to the record ids it stands for, and [] elsewhere", () => {
  const doc = "The big cat sat.";
  const ops = [ins("a1", 4, "big "), sub("s1", 12, "sat", "lay")];
  assert.deepEqual(idsAtPosition(ops, doc, 4), ["a1"]);
  assert.deepEqual(idsAtPosition(ops, doc, 12), ["s1"]);
  assert.deepEqual(idsAtPosition(ops, doc, 5), [], "inside a change is not its start");
  assert.deepEqual(idsAtPosition([], doc, 4), []);
  // a dense paragraph collapses to ONE display item that stands for every record in it
  const para = "aa bb cc dd ee ff gg hh";
  const many = [sub("p1", 0, "aa", "AA"), sub("p2", 3, "bb", "BB"), sub("p3", 6, "cc", "CC"), sub("p4", 9, "dd", "DD"), sub("p5", 12, "ee", "EE"), sub("p6", 15, "ff", "FF")];
  const items = displayItems(many, para);
  assert.equal(items.length, 1);
  assert.equal(items[0].display, "paragraph");
  assert.deepEqual(idsAtPosition(many, para, items[0].curFrom), ["p1", "p2", "p3", "p4", "p5", "p6"]);
});

// ── the decisions reducer ────────────────────────────────────────────────────────────────────────

test("applyDecision adds and removes entries by id, keeps one side per id, and returns the same object when nothing changes", () => {
  const e1 = { id: "a1", oldText: "", newText: "big " };
  const e2 = { id: "s1", oldText: "lay", newText: "sat" };
  const l1 = applyDecision(EMPTY_DECISIONS, { side: "accepted", entries: [e1] }, true);
  assert.deepEqual(l1, { accepted: [e1], rejected: [] });
  const l2 = applyDecision(l1, { side: "rejected", entries: [e2] }, true);
  assert.deepEqual(l2, { accepted: [e1], rejected: [e2] });
  // undo of the accept: the entry leaves, the other side is untouched
  const l3 = applyDecision(l2, { side: "accepted", entries: [e1] }, false);
  assert.deepEqual(l3, { accepted: [], rejected: [e2] });
  // a new decision on an id already on the other side moves it: one verdict per id
  const l4 = applyDecision(l3, { side: "accepted", entries: [e2] }, true);
  assert.deepEqual(l4, { accepted: [e2], rejected: [] });
  // identity: removing what is not there, or re-adding the very same entry object, changes nothing
  assert.equal(applyDecision(l4, { side: "rejected", entries: [e1] }, false), l4);
  assert.equal(applyDecision(l4, { side: "accepted", entries: [e2] }, true), l4);
  assert.equal(applyDecision(EMPTY_DECISIONS, { side: "accepted", entries: [] }, true), EMPTY_DECISIONS);
  assert.deepEqual(EMPTY_DECISIONS, { accepted: [], rejected: [] }, "the reducer never mutates its input");
});

// ── executed: accept and reject inside the editor, undo and redo, the decisions net of undo ──────

test("the seed puts the records in the initial state outside history: nothing to undo, marks from the first state", () => {
  const h = editor("The big cat.", [ins("a1", 4, "big ")]);
  assert.deepEqual(h.ops().map((o) => o.id), ["a1"]);
  assert.equal(h.undo(), false, "no history event reaches before the seed");
  assert.equal(h.decos().length, 1, "the insertion's mark is already in the decoration facet");
});

test("accept: the record leaves the field, the text stays, the decisions gain the entry; undo reverses all three; redo redoes", () => {
  const seen: TrackDecisions[] = [];
  const h = editor("The big cat.", [ins("a1", 4, "big ")], (l) => seen.push(l));
  const spec = h.resolve(4, false);
  assert.ok(spec && !("changes" in spec), "an accept changes no text");
  assert.equal(h.doc(), "The big cat.");
  assert.deepEqual(h.ops(), []);
  assert.deepEqual(h.decisions(), { accepted: [{ id: "a1", oldText: "", newText: "big " }], rejected: [] });
  assert.equal(seen.length, 1, "the chunk's listener reported the decision once");
  assert.equal(seen[0], h.decisions(), "…with the very object the field holds (the reducer's identity contract)");
  assert.equal(h.undo(), true);
  assert.equal(h.doc(), "The big cat.");
  assert.deepEqual(h.ops().map((o) => o.id), ["a1"]);
  assert.deepEqual(h.decisions(), { accepted: [], rejected: [] }, "undo removes the entry: the decisions are net of undo");
  assert.equal(seen.length, 2);
  assert.deepEqual(seen[1], EMPTY_DECISIONS, "the undo is reported too: a listener keeping its own copy sees the entry leave");
  assert.equal(h.redo(), true);
  assert.deepEqual(h.ops(), []);
  assert.deepEqual(h.decisions().accepted.map((e) => e.id), ["a1"]);
  assert.equal(seen.length, 3);
  assert.deepEqual(seen[2].accepted.map((e) => e.id), ["a1"]);
  assert.equal(h.changes(), 0, "none of these transactions changed the document, so onChange never ran");
});

// file-view.ts derives `dirty` from the text in onChange and marks an accept dirty ONLY through the decisions
// callback, since an accept changes no text (an accept-then-Save with no decisions callback takes doSave's
// nothing-changed branch and drops the acceptance silently). file-view.ts still passes that callback by its old
// spelling, onLedger; editor-chunk-decisions.test.ts proves the alias reaches this same listener. This runs the
// listener facet the chunk's state actually carries — the regex pin below reads the listener's body, not its
// membership in the extension set — so that wiring is executed, not just pinned.
test("the onDecisions listener rides in the chunk's extension set: an accept alone reaches it and not onChange; typing reaches onChange and not onDecisions; a reject reaches both", () => {
  const seen: TrackDecisions[] = [];
  const h = editor("I like cats a lot.", [sub("s1", 2, "like", "love"), ins("a1", 11, " a lot")], (l) => seen.push(l));
  assert.equal(seen.length, 0, "the seed is no decision");
  assert.equal(h.changes(), 0, "…and no keystroke");
  // the save path's case: click to accept, no keystroke, Save — onDecisions is the only signal the buffer is worth saving
  assert.ok(h.resolve(11, false), "the insertion starts at 11");
  assert.equal(h.doc(), "I like cats a lot.");
  assert.equal(h.changes(), 0, "an accept changes no text: onChange did not run");
  assert.equal(seen.length, 1, "…so onDecisions is the one report of it");
  assert.deepEqual(seen[0], { accepted: [{ id: "a1", oldText: "", newText: " a lot" }], rejected: [] });
  // typing: the field remaps, onChange runs, the decisions are untouched and unreported
  h.type({ changes: { from: 0, to: 0, insert: ">> " } });
  assert.equal(h.changes(), 1);
  assert.equal(seen.length, 1, "typing is no decision");
  assert.deepEqual(h.ops().map((o) => o.from), [5], "the substitution moved with the text");
  // a reject carries the buffer edit AND the decision in one transaction: both listeners run once
  assert.ok(h.resolve(5, true));
  assert.equal(h.doc(), ">> I love cats a lot.");
  assert.equal(h.changes(), 2);
  assert.equal(seen.length, 2);
  assert.deepEqual(seen[1], { accepted: [{ id: "a1", oldText: "", newText: " a lot" }], rejected: [{ id: "s1", oldText: "love", newText: "like" }] });
  // undo of the reject: the text comes back (onChange) and the report says the decision is gone (onDecisions)
  assert.equal(h.undo(), true);
  assert.equal(h.doc(), ">> I like cats a lot.");
  assert.equal(h.changes(), 3);
  assert.equal(seen.length, 3);
  assert.deepEqual(seen[2], { accepted: [{ id: "a1", oldText: "", newText: " a lot" }], rejected: [] });
});

test("reject: the text reverts and the record leaves in ONE transaction; undo restores text, record and decisions together", () => {
  const h = editor("I like cats.", [sub("s1", 2, "like", "love")]);
  const spec = h.resolve(2, true);
  assert.ok(spec && "changes" in spec, "a reject carries the buffer edit");
  assert.equal(h.doc(), "I love cats.");
  assert.deepEqual(h.ops(), []);
  assert.deepEqual(h.decisions(), { accepted: [], rejected: [{ id: "s1", oldText: "love", newText: "like" }] });
  h.undo();
  assert.equal(h.doc(), "I like cats.");
  assert.deepEqual(h.ops().map((o) => o.id), ["s1"]);
  assert.deepEqual(h.decisions(), { accepted: [], rejected: [] });
  h.redo();
  assert.equal(h.doc(), "I love cats.");
  assert.deepEqual(h.decisions().rejected.map((e) => e.id), ["s1"]);
});

test("a decision records the texts as the field held them THEN: after typing inside a change, the remapped pieces", () => {
  const h = editor("The big cat.", [ins("a1", 4, "big ")]);
  h.type({ changes: { from: 5, to: 5, insert: "X" } });         // "The bXig cat." — the record splits around X
  assert.equal(h.ops().length, 2);
  const [first, second] = h.ops();
  h.resolve(first.from, false);                                  // accept the first piece only
  assert.deepEqual(h.decisions().accepted, [{ id: String(first.id), oldText: "", newText: first.newText }]);
  assert.deepEqual(h.ops().map((o) => o.id), [second.id]);
  h.undo();                                                      // the accept, not the typing
  assert.equal(h.doc(), "The bXig cat.");
  assert.equal(h.ops().length, 2);
  assert.deepEqual(h.decisions(), EMPTY_DECISIONS);
  h.undo();                                                      // now the typing
  assert.equal(h.doc(), "The big cat.");
  assert.equal(h.ops().length, 1);
});

test("type then accept then undo twice: the decisions empty on the FIRST undo, the typing on the second", () => {
  const h = editor("The big cat.", [ins("a1", 4, "big ")]);
  h.type({ changes: { from: 11, to: 11, insert: " fast" } });
  h.resolve(4, false);
  assert.equal(h.decisions().accepted.length, 1);
  h.undo();
  assert.equal(h.doc(), "The big cat fast.");
  assert.deepEqual(h.decisions(), EMPTY_DECISIONS);
  h.undo();
  assert.equal(h.doc(), "The big cat.");
  assert.deepEqual(h.decisions(), EMPTY_DECISIONS);
  assert.deepEqual(h.ops().map((o) => o.id), ["a1"]);
});

test("a paragraph item accepts every record it stands for, one decision per record", () => {
  const para = "aa bb cc dd ee ff gg hh";
  const many = [sub("p1", 0, "aa", "AA"), sub("p2", 3, "bb", "BB"), sub("p3", 6, "cc", "CC"), sub("p4", 9, "dd", "DD"), sub("p5", 12, "ee", "EE"), sub("p6", 15, "ff", "FF")];
  const h = editor(para, many);
  const item = displayItems(h.ops(), h.doc())[0];
  h.resolve(item.curFrom, true);
  assert.equal(h.doc(), "AA BB CC DD EE FF gg hh");
  assert.deepEqual(h.ops(), []);
  assert.deepEqual(h.decisions().rejected.map((e) => e.id), ["p1", "p2", "p3", "p4", "p5", "p6"]);
  h.undo();
  assert.equal(h.doc(), para);
  assert.equal(h.ops().length, 6);
  assert.deepEqual(h.decisions(), EMPTY_DECISIONS);
});

test("resolve() is null where no change starts, and the handle's suggestions() is the live, remapped field", () => {
  const h = editor("The big cat.", [ins("a1", 4, "big ")]);
  assert.equal(h.resolve(0, false), null);
  assert.equal(h.resolve(5, true), null);
  h.type({ changes: { from: 0, to: 0, insert: ">> " } });
  assert.equal(h.ops()[0].from, 7, "typing above the change moved it: a save gets THESE records");
  assert.deepEqual(h.decisions(), EMPTY_DECISIONS, "typing is no decision");
});

// ── executed: the marks the decoration facet holds ───────────────────────────────────────────────

test("an insertion is a tc-diff-ins mark over its text with data-hk-from and the author colour on --fc-author", () => {
  const h = editor("The big cat.", [ins("a1", 4, "big ")]);
  const [m] = h.decos();
  assert.equal(m.from, 4); assert.equal(m.to, 8);
  assert.equal(m.spec.class, CLS.ins);
  assert.deepEqual(m.spec.attributes, { "data-hk-from": "4", "data-hk-side": "new", style: "--fc-author:#abcdef" });
});

test("a substitution is a struck widget (mode replace) before a tc-diff-ins tc-diff-sub mark; a deletion is the widget alone", () => {
  const h = editor("I like cats.", [sub("s1", 2, "like", "love"), del("d1", 11, " a lot")]);
  const ds = h.decos();
  const widget = ds.find((d) => d.spec.widget && d.from === 2)!;
  assert.ok(widget, "the substitution's old text is a widget at curFrom");
  assert.equal(widget.spec.side, -1);
  assert.equal((widget.spec.widget as unknown as { mode: string; text: string; color: string | null }).mode, "replace");
  assert.equal((widget.spec.widget as unknown as { text: string }).text, "love");
  assert.equal((widget.spec.widget as unknown as { color: string | null }).color, "#abcdef");
  const mark = ds.find((d) => d.spec.class && d.from === 2 && d.to === 6)!;
  assert.equal(mark.spec.class, `${CLS.ins} ${CLS.sub}`);
  const point = ds.find((d) => d.spec.widget && d.from === 11)!;
  assert.equal((point.spec.widget as unknown as { mode: string }).mode, "place");
  assert.ok(!ds.some((d) => d.spec.class && d.from === 11), "a pure deletion has no new text to mark");
});

test("an unknown author gets no --fc-author; the block form is a real block widget at the paragraph's line start", () => {
  const h = editor("The big cat.", [ins("a1", 4, "big ", "someone-else")]);
  assert.deepEqual(h.decos()[0].spec.attributes, { "data-hk-from": "4", "data-hk-side": "new" });
  const para = "aa bb cc dd ee ff gg hh";
  const many = [sub("p1", 0, "aa", "AA"), sub("p2", 3, "bb", "BB"), sub("p3", 6, "cc", "CC"), sub("p4", 9, "dd", "DD"), sub("p5", 12, "ee", "EE"), sub("p6", 15, "ff", "FF")];
  const g = editor("intro\n\n" + para, many.map((r) => ({ ...r, from: r.from + 7 })));
  const block = g.decos().find((d) => d.spec.widget && d.spec.block)!;
  assert.ok(block, "a dense paragraph's old text is a block widget");
  assert.equal(block.from, 7, "at the paragraph's first line start");
  assert.equal((block.spec.widget as unknown as { mode: string }).mode, "block");
});

test("accepting every change empties the decoration set; undoing it brings the mark back", () => {
  const h = editor("The big cat.", [ins("a1", 4, "big ")]);
  h.resolve(4, false);
  assert.equal(h.decos().length, 0);
  h.undo();
  assert.equal(h.decos().length, 1);
});

// ── source pins: the derived module's provenance, its two fixes, and the DOM-only wiring ─────────

test("track-decorations.ts names its source, the pin, and the fixes; no Obsidian, no dead code, the class vocabulary", () => {
  assert.match(DECO, /^\/\/ SPDX-License-Identifier: MIT\n/);
  assert.match(DECO, /obsidian\/src\/track-snapshot\.js/);
  assert.match(DECO, /320cd25fda6fe218481fbf08fa5cfb4670404c96/, "the pinned upstream commit, in full");
  assert.match(DECO, /vendor\/track-changents\/obsidian\/src\/track-snapshot\.js as the citation/);
  // fix 1: the mouseover handler takes the view
  assert.match(DECO, /^\/\/\s*1\. FIX: the mouseover handler takes the EditorView/m);
  assert.match(DECO, /mouseover: \(event, view\) => \{\n\s*const hit = closest\(event\.target, CHANGE_SEL\);\n\s*hoverPair\(hit \? hit\.getAttribute\("data-hk-from"\) : null, view\.dom\.ownerDocument\);/);
  // fix 2: no live-preview read; the constant false
  assert.match(DECO, /^\/\/\s*2\. FIX: the Obsidian live-preview read/m);
  assert.match(DECO, /const livePreview = false;\n\s*const fmEnd = livePreview \? logic\.frontmatterEnd\(current\) : 0;/);
  // the bans read CODE lines: the header above names each of these as what it removed
  assert.doesNotMatch(DECO_CODE, /editorLivePreviewField/);
  // no Obsidian, no module-level field refs, none of the dead code
  assert.doesNotMatch(DECO_CODE, /['"]obsidian['"]/);
  assert.doesNotMatch(DECO_CODE, /suggestionsFieldRef|metaFieldRef/);
  assert.doesNotMatch(DECO_CODE, /'above'|"above"|inlineDelLayout|layoutInlineRemovals|tc-diff-del-inline/);
  assert.doesNotMatch(DECO_CODE, /diffClickAction/, "the click policy is romp's trackClickAction");
  assert.doesNotMatch(DECO_CODE, /contextmenu/, "no context-menu suppression without the Ctrl gesture it served");
  // the vocabulary the sheet's owner reads
  assert.deepEqual(CLS, { ins: "tc-diff-ins", del: "tc-diff-del", sub: "tc-diff-sub", block: "tc-diff-del-block", line: "tc-diff-del-line", hover: "tc-diff-hover" });
  assert.equal(CHANGE_SEL, ".tc-diff-ins[data-hk-from], .tc-diff-del[data-hk-from]");
  assert.match(DECO, /el\.style\.setProperty\("--fc-author", this\.color\)/);
  // the five host callbacks are the interface, supplied by the chunk
  for (const cb of ["onOpenPanel", "resolveInline", "hasResolvableAt", "onOpsChanged", "hydrateView"]) {
    assert.match(DECO, new RegExp(`^  ${cb}\\(`, "m"), `TrackHost.${cb}`);
    assert.match(CHUNK, new RegExp(`\\b${cb}: `), `editor-chunk.ts supplies ${cb}`);
  }
  // the widget's own mousedown honours the same policy and leaves what is not ours to the browser
  assert.match(DECO, /const action = trackClickAction\(e, this\.mac\);\n\s*if \(!action\) return;/);
  assert.match(DECO, /if \(view\) this\.host\.resolveInline\(this\.offset, action === "reject", view\);/);
  // the editor-level mousedown: the drift guard before any preventDefault
  assert.match(DECO, /if \(!host\.hasResolvableAt\(view, from\)\) return false;\n\s*event\.preventDefault\(\);\n\s*host\.resolveInline\(from, action === "reject", view\);/);
});

test("the chunk's decisions are a fold over decide/undecide effects with history inverses, and the listener keys on the field's identity", () => {
  assert.match(CHUNK, /const decide = StateEffect\.define<Decision>\(\);\nconst undecide = StateEffect\.define<Decision>\(\);/);
  assert.match(CHUNK, /if \(e\.is\(decide\)\) out\.push\(undecide\.of\(e\.value\)\);\n\s*else if \(e\.is\(undecide\)\) out\.push\(decide\.of\(e\.value\)\);/);
  // the listener reads the decisions field once, returns on the reducer's same-object identity, and reports the
  // canonical callback first (the old-spelling alias line after it belongs to editor-chunk-decisions.test.ts)
  assert.match(CHUNK, /EditorView\.updateListener\.of\(\(u\) => \{\n\s*const next = u\.state\.field\(decisionsField\);\n\s*if \(u\.startState\.field\(decisionsField\) === next\) return;\n\s*if \(opts\.onDecisions\) opts\.onDecisions\(next\);/);
  assert.doesNotMatch(codeOnly(CHUNK), /ledgerField/, "the field is spelled decisionsField; no listener reads a field by the old name");
  // one transaction per decision, isolated in history, so one undo reverses the whole decision
  assert.match(CHUNK, /annotations: isolateHistory\.of\("full"\),/);
  // the seed is outside history and marked as a sync, as upstream's loads are
  assert.match(CHUNK, /annotations: \[Transaction\.addToHistory\.of\(false\), syncAnnotation\.of\(true\)\],/);
  assert.match(CHUNK, /if \(track\) state = state\.update\(track\.seed\)\.state;/);
});

test("the vendored declaration file types the two Obsidian-side modules and the engine; no suppression directive in the chunk's files", () => {
  const DTS = W("vendor-track-changents.d.ts");
  for (const m of ["*/vendor/track-changents/engine.js", "*/vendor/track-changents/obsidian/src/track-cm.js", "*/vendor/track-changents/obsidian/src/track-logic.js"]) {
    assert.ok(DTS.includes(`declare module "${m}"`), m);
  }
  // code lines only: the declaration file's header may NAME anchor-map's directive; the probe is assembled so
  // this file's own line does not carry the literal
  const directive = new RegExp("@ts-" + "ignore|@ts-" + "expect-error");
  for (const f of ["editor-chunk.ts", "track-decorations.ts", "track-cm-oracle.test.ts", "editor-track.test.ts", "vendor-track-changents.d.ts"]) {
    assert.doesNotMatch(codeOnly(W(f)), directive, f);
  }
});

// keep the type import honest: a TrackSetup is what mount() threads through extensionsFor
const _typeOnly: TrackSetup | null = null;
void _typeOnly;
