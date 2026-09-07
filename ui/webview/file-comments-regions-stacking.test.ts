// The rectangles' stacking order (plans/file-review.md, Slice 3; the 2026-09-06 review of the slice). The
// rectangles are absolutely positioned siblings with no z-index, so the one appended later paints over, and is hit
// before, the ones appended before it. paint() appended them in card order, so a whole-plot comment made after a
// detail comment covered the detail's rectangle, and a click at the detail's centre opened the plot's card — with
// the panel closed (the browser's own hit test) and open (the press handed on to the rectangle it began on) alike.
// paint() now appends them largest first (stackOrder), so a rectangle inside another is always above it.
//
// This file pins the ORDER through a DOM stand-in, since that is the whole mechanism (no inline z-index: the
// rectangle's style attribute stays the four percentages, which file-comments-regions.test.ts pins byte for byte);
// file-comments-regions-stacking-browser.test.ts drives the same module in Chromium, where the browser's hit test
// and a real click show the order doing its work. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

// ── the DOM stand-in: what the constructor and paint() reach for, and nothing more ────────────────
const kebab = (k: string | symbol): string => String(k).replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
class Doc {
  createElement(tag: string): E { return new E(this, tag.toUpperCase()); }
}
class E {
  parentNode: E | null = null;
  childNodes: E[] = [];
  attrs = new Map<string, string>();
  title = ""; tabIndex = -1;
  naturalWidth = 0; naturalHeight = 0; complete = true;
  dataset: Record<string, string | undefined>;
  classList = {
    add: (...c: string[]) => this.setClasses([...this.classes(), ...c]),
    remove: (...c: string[]) => this.setClasses(this.classes().filter((x) => !c.includes(x))),
    toggle: (c: string, on?: boolean) => { if (on === undefined ? !this.classes().includes(c) : on) this.classList.add(c); else this.classList.remove(c); },
    contains: (c: string) => this.classes().includes(c),
  };
  constructor(public ownerDocument: Doc, public tagName: string) {
    this.dataset = new Proxy({} as Record<string, string | undefined>, {
      get: (_t, k) => (typeof k === "string" ? this.attrs.get("data-" + kebab(k)) : undefined),
      set: (_t, k, v) => { this.attrs.set("data-" + kebab(k), String(v)); return true; },
      deleteProperty: (_t, k) => { this.attrs.delete("data-" + kebab(k)); return true; },
      has: (_t, k) => this.attrs.has("data-" + kebab(k)),
    });
  }
  private classes(): string[] { return (this.attrs.get("class") || "").split(/\s+/).filter(Boolean); }
  private setClasses(c: string[]): void { this.attrs.set("class", [...new Set(c)].join(" ")); }
  get className(): string { return this.attrs.get("class") || ""; }
  set className(v: string) { this.attrs.set("class", v); }
  getAttribute(n: string): string | null { return this.attrs.has(n) ? (this.attrs.get(n) as string) : null; }
  setAttribute(n: string, v: string): void { this.attrs.set(n, v); }
  removeAttribute(n: string): void { this.attrs.delete(n); }
  appendChild<X extends E>(n: X): X { if (n.parentNode) n.parentNode.removeChild(n); this.childNodes.push(n); n.parentNode = this; return n; }
  removeChild(n: E): E { const i = this.childNodes.indexOf(n); if (i >= 0) this.childNodes.splice(i, 1); n.parentNode = null; return n; }
  insertBefore(n: E, ref: E | null): E {
    if (!ref) return this.appendChild(n);
    if (n.parentNode) n.parentNode.removeChild(n);
    this.childNodes.splice(this.childNodes.indexOf(ref), 0, n); n.parentNode = this; return n;
  }
  contains(n: E | null): boolean { for (let x: E | null = n; x; x = x.parentNode) if (x === this) return true; return false; }
  querySelectorAll(sel: string): E[] {
    assert.ok(sel.startsWith("."), "the stand-in knows class selectors only: " + sel);
    const out: E[] = [];
    const visit = (n: E) => { for (const c of n.childNodes) { if (c.classList.contains(sel.slice(1))) out.push(c); visit(c); } };
    visit(this);
    return out;
  }
  addEventListener(): void { /* the layer's pointer, load and click listeners: not driven here */ }
  removeEventListener(): void { /* idem */ }
  /** not laid out: place() then claims nothing, which is all this file needs of it */
  getBoundingClientRect(): { left: number; top: number; width: number; height: number; right: number; bottom: number } { return { left: 0, top: 0, width: 0, height: 0, right: 0, bottom: 0 }; }
}

// ── globals the module reaches for, installed before it is imported ────────────────────────────────
const doc = new Doc();
const win: any = new EventTarget();
win.getComputedStyle = () => ({ objectFit: "contain" });
(globalThis as any).window = win;

import { RegionLayer, stackOrder, type RegionMark } from "./file-comments-regions";

// ── the harness ────────────────────────────────────────────────────────────────────────────────────
type Region = { x: number; y: number; w: number; h: number };
const R = (x: number, y: number, w: number, h: number): Region => ({ x, y, w, h });
/** the axis label's rectangle, the whole plot's around it, and a legend's in the corner: three sizes on one picture */
const SMALL = R(0.4, 0.4, 0.1, 0.1), LARGE = R(0.1, 0.1, 0.8, 0.8), MEDIUM = R(0.5, 0.5, 0.3, 0.3);
const mark = (id: string, region: Region, style?: Record<string, string>): RegionMark => ({ id, region, label: "you", state: "current", ...(style ? { style } : {}) });

function layer() {
  const row = doc.createElement("div"); row.className = "fileview-body";
  const p = doc.createElement("p"); row.appendChild(p);
  const img = doc.createElement("img"); p.appendChild(img);
  const l = new RegionLayer(img as unknown as HTMLImageElement, { onDraw: () => undefined, onClick: () => undefined });
  const overlay = l.overlay as unknown as E;
  /** the overlay's children in DOM order — the stacking order — by comment id, the pending region named */
  const ids = () => overlay.childNodes.map((c) => c.classList.contains("fc-region-pending") ? "(pending)" : c.dataset.id);
  return { l, overlay, ids };
}
const idsOf = (els: HTMLElement[]) => (els as unknown as E[]).map((e) => e.dataset.id);

test("paint appends the rectangles largest first, whatever the card order: the enclosing plot goes under the detail inside it", () => {
  const { l, overlay, ids } = layer();
  // card order is creation order: the detail was commented first, then the whole plot, then the legend
  const out = l.paint([mark("c1", SMALL), mark("c2", LARGE), mark("c3", MEDIUM)], null, false);
  assert.deepEqual(ids(), ["c2", "c3", "c1"], "DOM order — the stacking order and the Tab order — runs outer to inner");
  assert.deepEqual(idsOf(out), ["c2", "c3", "c1"], "the controls handed to the panel, in the same order");
  for (const r of out as unknown as E[]) {
    assert.equal(r.dataset.act, "fcopen"); assert.equal(r.tabIndex, 0);
    assert.equal(r.getAttribute("role"), "button");
  }
  const c1 = (out as unknown as E[])[2];
  assert.equal(c1.getAttribute("style"), "left: 40.00%; top: 40.00%; width: 10.00%; height: 10.00%;", "the order IS the stacking: no z-index in the style attribute");
  // another paint pass with the cards in another order (a status re-sorted them): the same DOM order, nothing accumulated
  const again = l.paint([mark("c3", MEDIUM), mark("c1", SMALL), mark("c2", LARGE)], null, false);
  assert.deepEqual(ids(), ["c2", "c3", "c1"]);
  assert.deepEqual(idsOf(again), ["c2", "c3", "c1"]);
  assert.equal(overlay.childNodes.length, 3);
});

test("the author's colour rides along, identical rectangles keep card order with the later above, and the pending region is last, above them all", () => {
  const { l, ids } = layer();
  const out = l.paint([mark("c1", LARGE, { "--fc-author": "#123456", "--fc-author-fg": "#ffffff" }), mark("c2", LARGE)], SMALL, false);
  assert.deepEqual(ids(), ["c1", "c2", "(pending)"], "equal areas: card order; the composer's region on top of every rectangle, small as it is");
  assert.equal((out as unknown as E[])[0].getAttribute("style"), "left: 10.00%; top: 10.00%; width: 80.00%; height: 80.00%; --fc-author: #123456; --fc-author-fg: #ffffff;", "the session's colour after the position, as before");
  assert.deepEqual(idsOf(out), ["c1", "c2"], "the pending region is not a control and is not returned");
});

test("stackOrder: by area descending, ties by the given order, the input untouched", () => {
  const tall = mark("a", R(0, 0, 0.2, 0.4)), wide = mark("b", R(0.5, 0.5, 0.4, 0.2)), tiny = mark("c", R(0.9, 0.9, 0.01, 0.01)), all = mark("d", R(0, 0, 1, 1));
  const given = [tall, wide, tiny, all];
  const ordered = stackOrder(given);
  assert.deepEqual(ordered.map((m) => m.id), ["d", "a", "b", "c"], "equal areas of different shapes (a, b) keep their order");
  assert.deepEqual(given.map((m) => m.id), ["a", "b", "c", "d"], "the caller's list is not re-sorted in place");
  assert.deepEqual(stackOrder([]), []);
  assert.deepEqual(stackOrder([tiny]).map((m) => m.id), ["c"]);
});

// ── the source: every plan reference in the module resolves in the plan ───────────────────────────
const UI = path.resolve(process.cwd(), "..", "ui", "webview");
const LAYER = fs.readFileSync(path.join(UI, "file-comments-regions.ts"), "utf8");
const PLAN = fs.readFileSync(path.resolve(process.cwd(), "..", "plans", "file-review.md"), "utf8");

test("source: the module cites the plan by headings a reader can find, never a lettered contract item the plan does not have", () => {
  assert.doesNotMatch(LAYER, /contract [A-Z]\d/, "the 2026-09-06 review: `contract E5` named an item no tracked file defines");
  assert.doesNotMatch(LAYER, /\((?:[A-Z]\d(?:[–-][A-Z]?\d)?)\)/, "nor a bare (E5)");
  for (const heading of ["Slice 3: region comments on images"]) {
    assert.ok(LAYER.includes('"' + heading + '"'), "the module names the section: " + heading);
    assert.ok(PLAN.includes("\n### " + heading + "\n"), "and the plan has it: " + heading);
  }
  assert.ok(LAYER.includes('"Images and PDFs"') && /\nImages and PDFs\. /.test(PLAN), "the UX paragraph the header points at");
  assert.ok(LAYER.includes("decision 26") && /\n26\. \*\*Phone\*\*/.test(PLAN), "the coarse-pointer gate cites the decision that made region drawing desktop-only");
});
