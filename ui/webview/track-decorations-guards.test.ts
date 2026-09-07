// Two press paths the executed leg of track-decorations.test.ts never reached (the 2026-09-07 review), driven under
// node so a machine without a browser (CI installs none) still holds them:
//  - the click handler's drift guard: a mouse click on a change whose position no longer resolves (records and
//    document drifted) is left alone, as the mousedown before it was, so a drifted mark cannot swallow the click
//    that places the caret. Only the mousedown twin had an executed case.
//  - the struck widget's OWN mousedown listener (DelWidget.toDOM's `wire`): the path a press on struck text takes,
//    because the widget ignores events and CodeMirror's handler chain skips it, so changeHandlers.mousedown never
//    runs for it. Departure 6 (a touch or pen press decides nothing), departure 3 (the click policy) and departure 7
//    (a decision focuses the editor) on the widget half. Until now only the Chromium and Firefox legs executed it,
//    and both skip without playwright's browsers; the source pin alone cannot tell a gate from a neutered one.
// The widget is the real one: the decoration facet is built from an EditorState through the extension set, and
// toDOM renders against a document stand-in that keeps the listener functions. The view the listener finds is a
// stand-in reached through the same EditorView.findFromDOM it calls: the Tile hangs off the element as `cmTile`,
// and its root's `view` is the editor. Fixtures are synthetic (the notes-api world's `web` session).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { EditorState } from "@codemirror/state";
import { EditorView, type DecorationSet, type WidgetType } from "@codemirror/view";
import { makeSuggestionField, setSuggestions } from "../../vendor/track-changents/obsidian/src/track-cm.js";
import { changeHandlers, trackDecorations, CLS, type TrackHost, type TrackRecord } from "./track-decorations";

const DECO = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "track-decorations.ts"), "utf8");

// ── stand-ins ────────────────────────────────────────────────────────────────────────────────────

type Press = { pressType: string | null } | null;
/** An editor as both paths see it: the PointerTracker plugin (or none), focus, and a root for the hover code. */
function view(o: { press?: Press; hasFocus?: boolean } = {}) {
  const calls: string[] = [];
  const v = {
    dom: { ownerDocument: null, contains: () => false },
    calls,
    hasFocus: o.hasFocus ?? false,
    focus() { calls.push("focus"); v.hasFocus = true; },
    plugin: () => (o.press === undefined ? { pressType: "mouse" } : o.press),
  };
  return v;
}
type V = ReturnType<typeof view>;
const asView = (v: V) => v as unknown as EditorView;

function host(resolvable: number[]) {
  const resolved: Array<[number, boolean, EditorView]> = [];
  const h: TrackHost = {
    onOpenPanel: () => {},
    resolveInline: (from, reject, v) => { resolved.push([from, reject, v]); },
    hasResolvableAt: (_v, from) => resolvable.includes(from),
    onOpsChanged: () => {},
    hydrateView: () => {},
  };
  return { h, resolved };
}
function press(target: unknown, o: { button?: number; altKey?: boolean; ctrlKey?: boolean } = {}) {
  const ev = { target, button: o.button ?? 0, altKey: !!o.altKey, metaKey: false, ctrlKey: !!o.ctrlKey, prevented: false, stopped: false,
    preventDefault() { ev.prevented = true; }, stopPropagation() { ev.stopped = true; } };
  return ev;
}
type Ev = ReturnType<typeof press>;

/** A change element as the editor-level handlers read it: its class and data-hk-from, with a `closest` that answers
 *  the module's selectors (`.class[data-hk-from]` parts, comma-joined) for itself and nothing else. */
class Change {
  constructor(readonly cls: string, readonly from: number) {}
  getAttribute(n: string): string | null { return n === "data-hk-from" ? String(this.from) : null; }
  closest(sel: string): Change | null { return sel.split(",").some((s) => s.trim().startsWith(`.${this.cls}[data-hk-from]`)) ? this : null; }
}
const run = (h: TrackHost, name: "mousedown" | "click", ev: Ev, v: V) =>
  (changeHandlers(h, false)[name] as (this: unknown, e: unknown, view: EditorView) => boolean | void)(ev, asView(v));

/** What DelWidget.toDOM touches on an element, plus what EditorView.findFromDOM reads to locate the view. */
class Node {
  className = "";
  attrs: Record<string, string> = {};
  readonly style = { setProperty: () => {} };
  children: Node[] = [];
  listeners = new Map<string, (e: unknown) => void>();
  textContent = "";
  ownerDocument = null;
  cmTile: { root: { view: EditorView } } | undefined;
  constructor(readonly tag: string) {}
  appendChild(c: Node): Node { this.children.push(c); return c; }
  setAttribute(k: string, v: string): void { this.attrs[k] = v; }
  addEventListener(type: string, fn: (e: unknown) => void): void { this.listeners.set(type, fn); }
  querySelector(): null { return null; }                          // findFromDOM looks for a .cm-content child first
  /** The widget's own listener, with the element's Tile pointing at `v` so findFromDOM resolves it. */
  mousedown(v: V | null, ev: Ev): void {
    this.cmTile = v ? { root: { view: asView(v) } } : undefined;
    this.listeners.get("mousedown")!(ev);
  }
}
function withDocument<T>(fn: () => T): T {
  const g = globalThis as { document?: unknown };
  const had = "document" in g;
  const prev = g.document;
  g.document = { createElement: (tag: string) => new Node(tag) };
  try { return fn(); } finally { if (had) g.document = prev; else delete g.document; }
}

const rec = (id: string, kind: "ins" | "del" | "sub", from: number, newText: string, oldText: string): TrackRecord =>
  ({ id, author: "web", ts: 1, kind, from, newText, oldText });
// the `web` session inserted "big " and removed " a lot": one mark, one struck widget in place
const DOC = "The big cat sat.";
const RECORDS = [rec("a1", "ins", 4, "big ", ""), rec("d1", "del", 15, "", " a lot")];
// a substitution: the struck old text right before the new run
const SUB_DOC = "I like cats.";
const SUB_RECORDS = [rec("s1", "sub", 2, "like", "love")];
// six substitutions in one paragraph, dense enough for the whole-paragraph block form
const BLOCK_DOC = "AA BB CC DD EE FF gg";
const BLOCK_RECORDS = [rec("p1", "sub", 0, "AA", "aa"), rec("p2", "sub", 3, "BB", "bb"), rec("p3", "sub", 6, "CC", "cc"),
  rec("p4", "sub", 9, "DD", "dd"), rec("p5", "sub", 12, "EE", "ee"), rec("p6", "sub", 15, "FF", "ff")];

/** The struck widgets' elements for `records` over `doc` (inline and block forms alike), keyed by data-hk-from. */
function struck(doc: string, records: TrackRecord[], h: TrackHost): Map<string, Node> {
  const field = makeSuggestionField();
  const state = EditorState.create({ doc, extensions: [field, ...trackDecorations(field, h, { authorColor: () => null, mac: false })] })
    .update({ effects: setSuggestions.of(records) }).state;
  const widgets: WidgetType[] = [];
  for (const v of state.facet(EditorView.decorations)) {
    if (typeof v === "function") continue;                      // a view-dependent provider: none of ours
    (v as DecorationSet).between(0, state.doc.length, (_f, _t, d) => { if (d.spec.widget) widgets.push(d.spec.widget as WidgetType); });
  }
  const out = new Map<string, Node>();
  withDocument(() => { for (const w of widgets) { const el = (w as unknown as { toDOM(): Node }).toDOM(); out.set(el.attrs["data-hk-from"], el); } });
  return out;
}

// ── the click handler's drift guard ──────────────────────────────────────────────────────────────

test("a mouse click on a change whose position no longer resolves is left alone, on either half: the drifted mark cannot swallow the click", () => {
  const { h: none, resolved } = host([]);
  const v = view({ press: { pressType: "mouse" }, hasFocus: true });
  for (const el of [new Change(CLS.ins, 4), new Change(CLS.del, 4)]) {
    const md = press(el);
    assert.equal(run(none, "mousedown", md, v), false, el.cls + ": the mousedown fell through");
    const ck = press(el);
    assert.equal(run(none, "click", ck, v), false, el.cls + ": so the click after it is not swallowed either");
    assert.equal(ck.prevented, false, el.cls + ": the click keeps its default");
    assert.equal(ck.stopped, false, el.cls + ": and propagates");
  }
  assert.deepEqual(resolved, [], "nothing was decided");
  // the contrast the guard is measured against: the same click over a change that resolves IS swallowed
  const { h } = host([4]);
  const ck = press(new Change(CLS.ins, 4));
  assert.equal(run(h, "click", ck, v), true);
  assert.ok(ck.prevented && ck.stopped);
});

// ── the struck widget's own listener ─────────────────────────────────────────────────────────────

test("a touch or pen press on the struck widget decides nothing: its listener returns before the click policy, and the caret lands natively", () => {
  const { h, resolved } = host([15]);
  const el = struck(DOC, RECORDS, h).get("15")!;
  assert.ok(el, "the deletion renders as a struck widget at 15");
  assert.equal(el.className, CLS.del);
  for (const pressType of ["touch", "pen"]) {
    const v = view({ press: { pressType }, hasFocus: false });
    const ev = press(el);
    el.mousedown(v, ev);
    assert.equal(ev.prevented, false, pressType + ": the browser and CodeMirror place the caret");
    assert.equal(ev.stopped, false, pressType + ": CodeMirror's own handler still sees the press");
    assert.deepEqual(resolved, [], pressType + ": no accept");
    assert.deepEqual(v.calls, [], pressType + ": no focus stolen; the native tap focuses");
  }
});

test("a mouse press on the struck widget accepts, Alt or Ctrl (non-mac) rejects, and a secondary button is left to the browser", () => {
  const { h, resolved } = host([15]);
  const el = struck(DOC, RECORDS, h).get("15")!;
  const v = view({ press: { pressType: "mouse" }, hasFocus: true });
  const md = press(el);
  el.mousedown(v, md);
  assert.equal(md.prevented && md.stopped, true, "decided: the press is ours, CodeMirror's handler does not run");
  assert.deepEqual(resolved, [[15, false, asView(v)]], "accepted at the widget's offset, on the view the DOM found");
  el.mousedown(v, press(el, { altKey: true }));
  assert.deepEqual(resolved.at(-1)?.slice(0, 2), [15, true], "Alt rejects");
  el.mousedown(v, press(el, { ctrlKey: true }));
  assert.deepEqual(resolved.at(-1)?.slice(0, 2), [15, true], "Ctrl rejects off macOS (the mount said mac: false)");
  const right = press(el, { button: 2 });
  el.mousedown(v, right);
  assert.equal(right.prevented, false, "not ours: the browser keeps its context menu");
  assert.equal(resolved.length, 3);
  assert.deepEqual(v.calls, [], "already focused: nothing to do");
});

test("a mouse decision on the struck widget focuses an unfocused editor (the undo chord needs it); a view without the tracker keeps the mouse rule", () => {
  const { h, resolved } = host([15]);
  const el = struck(DOC, RECORDS, h).get("15")!;
  const cold = view({ press: { pressType: "mouse" }, hasFocus: false });
  el.mousedown(cold, press(el));
  assert.deepEqual(resolved.map((r) => r[0]), [15]);
  assert.deepEqual(cold.calls, ["focus"], "the prevented mousedown moves no focus natively: we focus");
  const bare = view({ press: null, hasFocus: true });          // the tracker crashed or was never installed
  el.mousedown(bare, press(el));
  assert.deepEqual(resolved.map((r) => r[0]), [15, 15], "the policy is the mouse's, as before the tracker");
});

test("the substitution's struck half and the whole-paragraph block carry the same listener: a tap decides nothing, a mouse press decides at the item's start", () => {
  for (const [doc, records, from] of [[SUB_DOC, SUB_RECORDS, "2"], [BLOCK_DOC, BLOCK_RECORDS, "0"]] as Array<[string, TrackRecord[], string]>) {
    const { h, resolved } = host([Number(from)]);
    const el = struck(doc, records, h).get(from)!;
    assert.ok(el, doc + ": a struck widget at " + from);
    assert.deepEqual([...el.listeners.keys()], ["mousedown", "mouseenter", "mouseleave"]);
    const tap = press(el);
    el.mousedown(view({ press: { pressType: "touch" } }), tap);
    assert.equal(tap.prevented, false, doc + ": a tap places the caret");
    assert.equal(resolved.length, 0, doc + ": the tap decided nothing");
    el.mousedown(view({ press: { pressType: "mouse" }, hasFocus: true }), press(el));
    assert.deepEqual(resolved.map((r) => r.slice(0, 2)), [[Number(from), false]], doc + ": a mouse press accepts");
  }
  assert.equal(struck(SUB_DOC, SUB_RECORDS, host([2]).h).get("2")!.className, `${CLS.del} ${CLS.sub}`, "the substitution's half wears both classes");
  assert.equal(struck(BLOCK_DOC, BLOCK_RECORDS, host([0]).h).get("0")!.className, `${CLS.del} ${CLS.block}`, "the paragraph form is the block wrapper");
});

// ── source pin: the click branch checks drift before it swallows ─────────────────────────────────

test("track-decorations.ts: the click branch's drift guard comes before the swallow, and names where it is driven", () => {
  assert.match(DECO, /if \(!host\.hasResolvableAt\(view, from\)\) return false;[^\n]*\n\s*event\.preventDefault\(\);\n\s*event\.stopPropagation\(\);\n\s*return true;/);
  assert.match(DECO, /track-decorations-guards\.test\.ts/, "the source points at this module");
});
