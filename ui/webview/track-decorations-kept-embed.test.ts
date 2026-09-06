// The struck block widget's DOM contract for a KEPT embed (departure 4 in track-decorations.ts; the 2026-09-06
// review): a dense whole-paragraph substitution whose old text holds an `![[embed]]` token the current text still
// holds verbatim renders that token in its own span (tc-diff-del-kept-embed) with the removed runs around it in
// theirs (tc-diff-del-seg), so the sheet can un-strike the token — struck, it reads as "the picture is being
// deleted" when it only moved. A row without a kept token stays plain text, and a token the current text no longer
// holds is struck with the rest. The vendored helpers (keptEmbedTokens, segmentsByKeptTokens) decide WHICH; this
// pins what the widget emits, and that the two names are set in one place and named in the header for the sheet's
// owner (CLS, the element-level vocabulary, is pinned as an exact object by editor-track.test.ts).
//
// Executed under node: the extension set builds the decoration facet from an EditorState (no view), and toDOM runs
// against a minimal document stand-in, since the widget only needs createElement, className, textContent,
// appendChild, setAttribute, style.setProperty and addEventListener. The rendering itself (whether the kept span
// really reads un-struck) is the sheets' to pin, with their rules.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { EditorState } from "@codemirror/state";
import { EditorView, type DecorationSet, type WidgetType } from "@codemirror/view";
import { makeSuggestionField, setSuggestions } from "../../vendor/track-changents/obsidian/src/track-cm.js";
import { trackDecorations, displayItems, CLS, type TrackHost, type TrackRecord } from "./track-decorations";

const DECO = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "track-decorations.ts"), "utf8");
const codeOnly = (src: string) => src.split("\n").map((l) => l.replace(/\s\/\/.*$/, "")).filter((l) => { const t = l.trim(); return !t.startsWith("//") && !t.startsWith("*") && !t.startsWith("/*"); }).join("\n");

/** The split row's vocabulary (departure 4): the names the sheet's owner styles. */
const SEG = "tc-diff-del-seg";
const KEPT_EMBED = "tc-diff-del-kept-embed";

// ── a document stand-in: what DelWidget.toDOM touches, and nothing more ──────────────────────────

class Node {
  className = "";
  attrs: Record<string, string> = {};
  vars: Record<string, string> = {};
  readonly style = { setProperty: (k: string, v: string) => { this.vars[k] = v; } };
  children: Node[] = [];
  listeners: string[] = [];
  private text = "";
  constructor(readonly tag: string) {}
  get textContent(): string { return this.children.length ? this.children.map((c) => c.textContent).join("") : this.text; }
  set textContent(v: string) { this.text = v; this.children = []; }
  appendChild(c: Node): Node { this.children.push(c); return c; }
  setAttribute(k: string, v: string): void { this.attrs[k] = v; }
  addEventListener(type: string): void { this.listeners.push(type); }
  get classes(): string[] { return this.className.split(" ").filter(Boolean); }
}
function withDocument<T>(fn: () => T): T {
  const g = globalThis as { document?: unknown };
  const had = "document" in g;
  const prev = g.document;
  g.document = { createElement: (tag: string) => new Node(tag) };
  try { return fn(); } finally { if (had) g.document = prev; else delete g.document; }
}

// ── the block widget out of the real extension set ───────────────────────────────────────────────

const sub = (id: string, from: number, newText: string, oldText: string): TrackRecord => ({ id, author: "web", ts: 1, kind: "sub", from, newText, oldText });
const host: TrackHost = { onOpenPanel() {}, resolveInline() {}, hasResolvableAt: () => true, onOpsChanged() {}, hydrateView() {} };

/** The block widgets the decoration facet holds for `records` over `doc`, rendered through the stand-in. */
function blocks(doc: string, records: TrackRecord[]): Node[] {
  const field = makeSuggestionField();
  const state = EditorState.create({ doc, extensions: [field, ...trackDecorations(field, host, { authorColor: () => "#abcdef", mac: false })] })
    .update({ effects: setSuggestions.of(records) }).state;
  const widgets: WidgetType[] = [];
  for (const v of state.facet(EditorView.decorations)) {
    if (typeof v === "function") continue;                      // a view-dependent provider: none of ours
    (v as DecorationSet).between(0, state.doc.length, (_f, _t, d) => { if (d.spec.widget && d.spec.block) widgets.push(d.spec.widget as WidgetType); });
  }
  // DelWidget's toDOM reads no view (the DOM finds it at press time), so it is called as the widget declares it
  return withDocument(() => widgets.map((w) => (w as unknown as { toDOM(): Node }).toDOM()));
}
const spans = (row: Node) => row.children.map((s) => ({ cls: s.className, text: s.textContent }));

// Six substitutions in one paragraph: dense enough that planDiffDisplay collapses them to the paragraph form (the
// oracle in editor-track.test.ts uses the same shape). The embed token sits untouched among them.
const KEPT = "![[figure.png]]";
const DOC = `AA BB CC ${KEPT} DD EE FF gg`;                     // the token at 9..24 is in the current text
const ALL_ROUND = [sub("p1", 0, "AA", "aa"), sub("p2", 3, "BB", "bb"), sub("p3", 6, "CC", "cc"),
  sub("p4", 25, "DD", "dd"), sub("p5", 28, "EE", "ee"), sub("p6", 31, "FF", "ff")];

test("a kept embed in a struck paragraph is its own kept-embed span between seg spans over the removed runs", () => {
  const [item, ...rest] = displayItems(ALL_ROUND, DOC);
  assert.equal(rest.length, 0); assert.equal(item.display, "paragraph", "the fixture takes the block form");
  assert.equal(item.oldText, `aa bb cc ${KEPT} dd ee ff gg`);
  const [wrap, ...more] = blocks(DOC, ALL_ROUND);
  assert.equal(more.length, 0, "one block widget for the one paragraph");
  assert.deepEqual(wrap.classes, [CLS.del, CLS.block], "the wrapper is the clickable struck half");
  assert.equal(wrap.attrs["data-hk-from"], "0"); assert.equal(wrap.attrs["data-hk-side"], "old");
  assert.equal(wrap.vars["--fc-author"], "#abcdef");
  assert.deepEqual(wrap.listeners, ["mousedown", "mouseenter", "mouseleave"], "wired like the inline forms");
  assert.equal(wrap.children.length, 1, "one row per old line");
  const [row] = wrap.children;
  assert.equal(row.className, CLS.line);
  assert.deepEqual(spans(row), [
    { cls: SEG, text: "aa bb cc " },
    { cls: KEPT_EMBED, text: KEPT },
    { cls: SEG, text: " dd ee ff gg" },
  ]);
  assert.equal(row.textContent, item.oldText, "the row still reads as the whole old line");
});

test("a two-line paragraph: the row without a kept token is plain text, the row with one is split, the token first when it leads", () => {
  const doc = `AA BB CC\n${KEPT} DD EE FF gg`;                  // same offsets: the space at 8 became the line break
  const [item] = displayItems(ALL_ROUND, doc);
  assert.equal(item.display, "paragraph");
  const [wrap] = blocks(doc, ALL_ROUND);
  assert.equal(wrap.children.length, 2, "one row per old line");
  const [plain, split] = wrap.children;
  assert.deepEqual(spans(plain), [], "no kept token on this line: plain text, no spans");
  assert.equal(plain.textContent, "aa bb cc");
  assert.deepEqual(spans(split), [{ cls: KEPT_EMBED, text: KEPT }, { cls: SEG, text: " dd ee ff gg" }]);
});

test("an embed the current text no longer holds is struck with the rest: no kept span, the row is plain text", () => {
  const doc = "AA BB CC DD EE FF gg";                            // the token went with the substitution at 6
  const gone = [sub("p1", 0, "AA", "aa"), sub("p2", 3, "BB", "bb"), sub("p3", 6, "CC", `cc ${KEPT}`),
    sub("p4", 9, "DD", "dd"), sub("p5", 12, "EE", "ee"), sub("p6", 15, "FF", "ff")];
  const [item] = displayItems(gone, doc);
  assert.equal(item.display, "paragraph");
  assert.equal(item.oldText, `aa bb cc ${KEPT} dd ee ff gg`, "the old paragraph still names the embed");
  const [wrap] = blocks(doc, gone);
  const [row] = wrap.children;
  assert.deepEqual(spans(row), [], "nothing kept: the whole line is removed text");
  assert.equal(row.textContent, item.oldText);
});

test("the two names are set in one place, and departure 4 names them for the sheet's owner with the reason a bare text-decoration cannot un-strike", () => {
  const code = codeOnly(DECO);
  assert.match(code, /span\.className = seg\.kept \? "tc-diff-del-kept-embed" : "tc-diff-del-seg";/);
  assert.equal((code.match(/"tc-diff-del-kept-embed"/g) || []).length, 1, "the literal appears in code once");
  assert.equal((code.match(/"tc-diff-del-seg"/g) || []).length, 1);
  assert.match(DECO, /^\/\/\s*4\. Class names are romp's:[\s\S]*?tc-diff-del-seg over each removed run and tc-diff-del-kept-embed over the kept token/m);
  assert.match(DECO, /must also stop the propagation/, "the wrapper's line-through paints through an inline descendant");
  assert.match(DECO, /track-decorations-kept-embed\.test\.ts pins the names/, "the source points at this pin");
});
