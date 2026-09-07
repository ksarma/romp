// The hover cue's cost while the pointer crosses ordinary text (departure 9 in track-decorations.ts; the 2026-09-07
// review). mouseover fires on every element boundary the pointer crosses, so the cache's job is to make the common
// crossing — no change under the pointer, nothing lit — free. Upstream's early return needs the cached root to equal
// the editor's document, and the root is reset to null together with the key, so that crossing never matched and each
// one ran a document-wide class query; in the dashboard's document, the largest romp has, that is the cost the
// cache's own comment claims to prevent. Executed under node with a document stand-in that counts its queries: none
// on a plain-text crossing while nothing is cued (from a cold start, after a cue was cleared, and in another
// document); the sweep still runs when a cue IS lit; the same-key short-circuit still holds.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import type { EditorView } from "@codemirror/view";
import { changeHandlers, releaseHover, CLS, type TrackHost } from "./track-decorations";

const DECO = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "track-decorations.ts"), "utf8");

// ── stand-ins: the elements the cue reads and writes, and a document that counts its queries ─────

/** Matches the module's selectors: simple selectors of `.class` and `[attr]` / `[attr="v"]` parts, joined by commas. */
function matches(el: El, sel: string): boolean {
  return sel.split(",").some((s) => {
    const parts = s.trim().match(/\.[\w-]+|\[[^\]]+\]/g) || [];
    return parts.length > 0 && parts.every((p) => {
      if (p[0] === ".") return el.classes.has(p.slice(1));
      const m = /^\[([\w-]+)(?:="([^"]*)")?\]$/.exec(p);
      assert.ok(m, "selector part the stand-in cannot read: " + p);
      const v = el.getAttribute(m[1]);
      return v !== null && (m[2] === undefined || v === m[2]);
    });
  });
}
class El {
  classes = new Set<string>();
  parent: El | null = null;
  ownerDocument: Doc | null = null;
  readonly classList = { add: (c: string) => { this.classes.add(c); }, remove: (c: string) => { this.classes.delete(c); } };
  constructor(readonly attrs: Record<string, string> = {}, cls: string[] = []) { cls.forEach((c) => this.classes.add(c)); }
  getAttribute(n: string): string | null { return n in this.attrs ? this.attrs[n] : null; }
  closest(sel: string): El | null { for (let e: El | null = this; e; e = e.parent) if (matches(e, sel)) return e; return null; }
  contains(other: unknown): boolean { for (let e = other as El | null; e; e = e.parent) if (e === this) return true; return false; }
  addEventListener(): void {}
  removeEventListener(): void {}
}
class Doc {
  els: El[] = [];
  queries: string[] = [];                                         // every querySelectorAll the cue ran on this document
  add(...els: El[]): this { for (const e of els) { e.ownerDocument = this; this.els.push(e); } return this; }
  querySelectorAll(sel: string): El[] { this.queries.push(sel); return this.els.filter((e) => matches(e, sel)); }
  /** The queries since the last call. */
  drain(): string[] { return this.queries.splice(0); }
}
function view(doc: Doc) {
  const dom = new El({}, ["cm-editor"]);
  doc.add(dom);
  return { dom, hasFocus: true, focus() {}, plugin: () => ({ pressType: "mouse" }) };
}
type V = ReturnType<typeof view>;
const asView = (v: V) => v as unknown as EditorView;
const h: TrackHost = { onOpenPanel: () => {}, resolveInline: () => {}, hasResolvableAt: () => true, onOpsChanged: () => {}, hydrateView: () => {} };
const over = (target: El, v: V) =>
  (changeHandlers(h, false).mouseover as (this: unknown, e: unknown, view: EditorView) => void)({ target, relatedTarget: null }, asView(v));
/** Both halves of the change at `from` in `v`, and a plain-text line to cross. */
function pair(v: V, from = 2) {
  const mk = (attrs: Record<string, string>, cls: string[]) => { const e = new El(attrs, cls); e.parent = v.dom; v.dom.ownerDocument!.add(e); return e; };
  return {
    ins: mk({ "data-hk-from": String(from), "data-hk-side": "new" }, [CLS.ins]),
    del: mk({ "data-hk-from": String(from), "data-hk-side": "old" }, [CLS.del]),
    text: mk({}, ["cm-line"]),
  };
}
const lit = (doc: Doc) => doc.els.filter((e) => e.classes.has(CLS.hover)).length;

// The module's cache is module-level and this file runs in its own process, so the first test sees it cold.

test("from a cold start, crossings over plain text with nothing cued run no query at all", () => {
  const doc = new Doc();
  const v = view(doc);
  const { text } = pair(v);
  for (let i = 0; i < 5; i++) over(text, v);
  assert.deepEqual(doc.drain(), [], "five boundary crossings, five mouseovers, no document-wide sweep");
  assert.equal(lit(doc), 0);
});

test("lighting a change runs the sweep and the halves lookup; clearing it runs one sweep; every plain-text crossing after that is free", () => {
  const doc = new Doc();
  const v = view(doc);
  const a = pair(v);
  over(a.ins, v);
  assert.equal(lit(doc), 2, "both halves lit");
  assert.deepEqual(doc.drain(), [`.${CLS.hover}`, `.${CLS.ins}[data-hk-from="2"], .${CLS.del}[data-hk-from="2"]`], "one sweep of the document, one lookup of the halves");
  over(a.text, v);
  assert.equal(lit(doc), 0, "the pointer left the change: the cue is cleared");
  assert.deepEqual(doc.drain(), [`.${CLS.hover}`], "the clearing crossing sweeps once — there was a cue to drop");
  for (let i = 0; i < 5; i++) over(a.text, v);
  assert.deepEqual(doc.drain(), [], "nothing cued, nothing under the pointer: the crossing is free");
  // a release (the editor destroyed under the pointer) leaves the same free state behind
  over(a.ins, v);
  doc.drain();
  releaseHover(asView(v));
  assert.equal(lit(doc), 0);
  doc.drain();
  over(a.text, v);
  assert.deepEqual(doc.drain(), []);
});

test("the same-key short-circuit still holds, and a plain-text crossing in another document with nothing cued is free too", () => {
  const doc = new Doc();
  const v = view(doc);
  const a = pair(v);
  over(a.ins, v);
  doc.drain();
  over(a.del, v);
  over(a.ins, v);
  assert.deepEqual(doc.drain(), [], "the same change, the same document: no repaint (the upstream behavior the release exists for)");
  over(a.text, v);
  doc.drain();
  const other = new Doc();
  const w = view(other);
  const b = pair(w);
  over(b.text, w);
  assert.deepEqual(other.drain(), [], "no cached root to compare against: the key alone says nothing is cued");
  assert.deepEqual(doc.drain(), []);
  over(b.ins, w);
  assert.equal(lit(other), 2, "and a change in that document still lights");
  over(b.text, w);
});

// ── source pin: departure 9 is named, and the condition is the one the tests count ───────────────

test("track-decorations.ts names departure 9 and short-circuits on the key alone when nothing is cued", () => {
  assert.match(DECO, /^\/\/\s*9\. FIX: the hover cache short-circuits a crossing over plain text while nothing is cued/m);
  assert.match(DECO, /if \(key === lastHoverKey && \(key == null \|\| scope === lastHoverRoot\)\) return;/);
  assert.match(DECO, /track-decorations-hover-cost\.test\.ts/, "the source points at this module");
});
