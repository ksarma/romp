// Three guards in the region layer that no behavioural test exercised (plans/file-review.md, Slice 3; the
// 2026-09-06 review of the slice), each pinned here against the stand-in the click harness uses:
//
// - A paint pass can land MID-DRAG — a peer's region comment arriving, the colour map answering, a stale flip
//   — and paint() rebuilds every rectangle. It must keep the rubber band of the drag in progress (and put it back
//   on top of what it drew), or the band is a detached node the next pointermove styles for nobody, and the
//   person draws blind until the release. Dropping the `n !== this.band` guard passed every test before this one.
// - Only the PRIMARY button draws or clicks: a right-button press (the context menu's gesture) or a middle-button
//   drag on an armed overlay is not the overlay's, so the browser's own context menu comes up over a plain picture
//   with no Comment offer beside it, and no region is drawn from it. The guard was pinned by a regex on the source
//   text alone.
// - The wrapper takes over the picture's own place in the author's flow (carriedLayout): a percentage width, a
//   float from `align`, an inline `display: block` with auto margins, a vertical-align — and gives it back on
//   dispose, with the picture's inline style exactly as it was. The geometry itself is measured in Chromium
//   (file-comments-regions-layout-browser.test.ts); this leg pins what is written to the DOM and the pure carry.
//
// The stand-in models pointer capture, an element's click(), a client rect, an inline `style` record and a
// computed style per element, and nothing more. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";

// ── the DOM stand-in ───────────────────────────────────────────────────────────────────────────────
type Rect = { left: number; top: number; right: number; bottom: number; width: number; height: number };
const rectOf = (left: number, top: number, width: number, height: number): Rect => ({ left, top, width, height, right: left + width, bottom: top + height });
type Init = { clientX?: number; clientY?: number; pointerId?: number; button?: number };
type Ev = Init & { type: string; target: E; currentTarget: E | null; defaultPrevented: boolean; preventDefault(): void; stopPropagation(): void };
const kebab = (k: string | symbol): string => String(k).replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
/** Which element holds each pointer's capture — what a browser keeps per pointer id. */
const captured = new Map<number, E>();

class Doc {
  createElement(tag: string): E { return new E(this, tag.toUpperCase()); }
}
class E {
  parentNode: E | null = null;
  childNodes: E[] = [];
  attrs = new Map<string, string>();
  listeners = new Map<string, Array<(ev: Ev) => void>>();
  title = ""; tabIndex = -1; offsetWidth = 0;
  naturalWidth = 0; naturalHeight = 0; complete = true;
  /** the client rect a test gives the element; a wrapper hugs its picture (the sheet's inline-block around a block img) */
  rect: Rect | null = null;
  /** the computed `object-fit` a test gives the picture ("" — no rule — is CSS's initial fill) */
  fit = "";
  /** the rest of the computed style a test gives the element (float, verticalAlign, margins) */
  computed: Record<string, string> = {};
  /** the inline style a test gives the element, as the CSSOM would read it (camelCase, specified values) */
  style: Record<string, string> = {};
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
  remove(): void { if (this.parentNode) this.parentNode.removeChild(this); }
  contains(n: E | null): boolean { for (let x: E | null = n; x; x = x.parentNode) if (x === this) return true; return false; }
  matches(sel: string): boolean {
    if (sel === "[data-act]") return this.attrs.has("data-act");
    if (sel.startsWith(".")) return this.classList.contains(sel.slice(1));
    throw new Error("the stand-in knows class and [data-act] selectors only: " + sel);
  }
  closest(sel: string): E | null { for (let x: E | null = this; x; x = x.parentNode) if (x.matches(sel)) return x; return null; }
  querySelectorAll(sel: string): E[] {
    const out: E[] = [];
    const visit = (n: E) => { for (const c of n.childNodes) { if (c.matches(sel)) out.push(c); visit(c); } };
    visit(this);
    return out;
  }
  addEventListener(type: string, fn: (ev: Ev) => void): void { (this.listeners.get(type) || this.listeners.set(type, []).get(type)!).push(fn); }
  removeEventListener(type: string, fn: (ev: Ev) => void): void { const l = this.listeners.get(type); if (l) l.splice(l.indexOf(fn), 1); }
  /** Dispatch with bubbling: every ancestor's listeners run until one stops propagation. */
  dispatch(type: string, init: Init = {}): Ev {
    let stopped = false;
    const ev: Ev = { ...init, type, target: this, currentTarget: null, defaultPrevented: false,
      preventDefault() { this.defaultPrevented = true; }, stopPropagation() { stopped = true; } };
    for (let n: E | null = this; n && !stopped; n = n.parentNode) {
      ev.currentTarget = n;
      for (const fn of [...(n.listeners.get(type) || [])]) fn(ev);
    }
    return ev;
  }
  /** HTMLElement.click(): a synthetic click that bubbles like a real one. */
  click(): void { this.dispatch("click"); }
  getBoundingClientRect(): Rect {
    if (this.rect) return this.rect;
    if (this.classList.contains("fc-imgwrap")) { const img = this.childNodes.find((c) => c.tagName === "IMG"); return img ? img.getBoundingClientRect() : rectOf(0, 0, 0, 0); }
    return rectOf(0, 0, 0, 0);
  }
  setPointerCapture(id: number): void { captured.set(id, this); }
  releasePointerCapture(id: number): void { if (captured.get(id) === this) captured.delete(id); }
}

// ── globals the module reaches for, installed before it is imported ────────────────────────────────
const doc = new Doc();
const win: any = new EventTarget();
win.getComputedStyle = (el: E) => ({ objectFit: el.fit, ...el.computed });
(globalThis as any).window = win;
(globalThis as any).document = doc;   // the delegate compares its root against it

import { RegionLayer, carriedLayout, pctOf, type RegionMark } from "./file-comments-regions";
import { delegate } from "./actions";

// ── the harness: the viewer's body row with one picture, the panel's listeners on the row ─────────
/** A 600×400 picture drawn at half size, 100px in and 200px down, like the regions harness's figure. */
const IMG_RECT = rectOf(100, 200, 300, 200);
const mark = (id: string, region = { x: 0.1667, y: 0.2, w: 0.3333, h: 0.3 }): RegionMark => ({ id, region, label: "you", state: "current" });
/** a `style` attribute's declarations as a map, so an assertion does not lean on their order */
const decls = (s: string | null): Record<string, string> => {
  const out: Record<string, string> = {};
  for (const d of (s || "").split(";")) { const i = d.indexOf(":"); if (i > 0) out[d.slice(0, i).trim()] = d.slice(i + 1).trim(); }
  return out;
};

type Over = { rect?: Rect; fit?: string; active?: boolean; attrs?: Record<string, string>; style?: Record<string, string>; styleAttr?: string; computed?: Record<string, string> };
function harness(over: Over = {}) {
  captured.clear();
  const calls: string[] = [];
  const row = doc.createElement("div"); row.className = "fileview-body";
  const p = doc.createElement("p"); row.appendChild(p);
  const img = doc.createElement("img"); p.appendChild(img);
  img.rect = over.rect || IMG_RECT; img.naturalWidth = 600; img.naturalHeight = 400; img.fit = over.fit ?? "contain";
  for (const [k, v] of Object.entries(over.attrs || {})) img.setAttribute(k, v);
  if (over.styleAttr !== undefined) img.setAttribute("style", over.styleAttr);
  img.style = over.style || {}; img.computed = over.computed || {};
  delegate(row as unknown as HTMLElement, { fcopen: (el) => { calls.push("fcopen:" + el.dataset.id); } });
  row.addEventListener("click", (ev) => { if (ev.target.tagName === "IMG") calls.push("imgclick"); });
  const layer = new RegionLayer(img as unknown as HTMLImageElement, {
    onDraw: (_i, r) => { calls.push("onDraw:" + JSON.stringify(r)); },
    onClick: () => { calls.push("onClick"); },
    onPress: () => { calls.push("press"); },
  });
  layer.setActive(over.active ?? true);
  const overlay = layer.overlay as unknown as E;
  const wrap = layer.wrap as unknown as E;
  return {
    calls, row, p, img, layer, overlay, wrap,
    rects: () => overlay.querySelectorAll(".fc-region"),
    band: () => overlay.querySelectorAll(".fc-draw")[0] || null,
    down: (x: number, y: number, init: Init = {}): Ev => overlay.dispatch("pointerdown", { clientX: x, clientY: y, pointerId: 7, button: 0, ...init }),
    move: (x: number, y: number, id = 7): Ev => (captured.get(id) || overlay).dispatch("pointermove", { clientX: x, clientY: y, pointerId: id }),
    up: (x: number, y: number, init: Init = {}): Ev => { const id = init.pointerId ?? 7; const cap = captured.get(id) || overlay; cap.dispatch("pointerup", { clientX: x, clientY: y, pointerId: id, ...init }); return cap.dispatch("click", init); },
  };
}
const drawnOf = (calls: string[]): { x: number; y: number; w: number; h: number } | null => {
  const s = calls.find((c) => c.startsWith("onDraw:"));
  return s ? JSON.parse(s.slice("onDraw:".length)) : null;
};
const near = (a: number, b: number, msg: string) => assert.ok(Math.abs(a - b) < 0.002, msg + ": " + a + " vs " + b);

// ── the rubber band across a paint pass ────────────────────────────────────────────────────────────

test("a paint pass mid-drag keeps the rubber band in the overlay, above what it drew; the next move still styles it and the release draws the region", () => {
  const h = harness();
  h.layer.paint([mark("c1")], null, false);
  h.down(150, 240);
  h.move(250, 300);
  const band = h.band();
  assert.ok(band, "past the click threshold: the band is drawn");
  assert.equal(band!.parentNode, h.overlay);
  const styled = band!.getAttribute("style");
  assert.ok(styled && /left: 16\.67%/.test(styled), "the band is where the drag is: " + styled);
  // a peer's comment lands and the colour map answers: the panel repaints every rectangle while the pointer is down
  const fresh = h.layer.paint([mark("c1"), mark("c2", { x: 0.6, y: 0.1, w: 0.2, h: 0.2 })], { x: 0.5, y: 0.5, w: 0.2, h: 0.2 }, false) as unknown as E[];
  assert.equal(fresh.length, 2, "the pass drew its rectangles");
  assert.equal(h.band(), band, "the SAME band node is still in the overlay — not a detached node the next move would style for nobody");
  assert.equal(band!.parentNode, h.overlay);
  assert.equal(h.overlay.childNodes[h.overlay.childNodes.length - 1], band, "and it is back on top: above the rectangles and the composer's pending region");
  assert.equal(h.rects().length, 4, "two rectangles, the pending region, the band");
  h.move(280, 330);
  const restyled = band!.getAttribute("style");
  assert.notEqual(restyled, styled, "the move after the pass still reaches the band the person sees");
  assert.ok(restyled && /width: 43\.33%/.test(restyled), restyled || "");
  const click = h.up(280, 330);
  assert.equal(h.band(), null, "the release takes the band down");
  assert.equal(h.rects().length, 3, "the pass's rectangles and the pending region stand");
  const r = drawnOf(h.calls);
  assert.ok(r, "the region is drawn: " + JSON.stringify(h.calls));
  near(r!.x, 0.1667, "x"); near(r!.y, 0.2, "y"); near(r!.w, 0.4333, "w"); near(r!.h, 0.45, "h");
  assert.equal(click.defaultPrevented, true, "the click after the drag is swallowed");
  // a pass with the pointer down but not yet moved (no band) draws nothing extra, and a later move starts the band as usual
  h.calls.length = 0;
  h.down(150, 240, { pointerId: 8 });
  h.layer.paint([mark("c1")], null, false);
  assert.equal(h.band(), null, "no band before the threshold, so none to keep");
  h.move(250, 300, 8);
  assert.ok(h.band(), "the band starts on the first move past the threshold, as before");
  h.up(250, 300, { pointerId: 8 });
  assert.ok(drawnOf(h.calls));
});

// ── the primary button ─────────────────────────────────────────────────────────────────────────────

test("an armed overlay takes only the primary button: a right or middle press records nothing, captures nothing, keeps the browser's default, and its release neither clicks nor draws", () => {
  for (const button of [1, 2]) {
    const h = harness();
    h.layer.paint([mark("c1")], null, false);
    const down = h.down(300, 300, { button });
    assert.deepEqual(h.calls, [], "button " + button + ": no press hook — the float is not hidden for a gesture the overlay declines");
    assert.equal(captured.size, 0, "button " + button + ": nothing captured");
    assert.equal(down.defaultPrevented, false, "button " + button + ": the browser's default stands (the context menu, the image drag)");
    h.move(200, 250);
    assert.equal(h.band(), null, "button " + button + ": no rubber band from a drag the overlay never took");
    const click = h.up(200, 250, { button });
    assert.deepEqual(h.calls, [], "button " + button + ": no region, no Comment offer");
    assert.equal(click.defaultPrevented, false, "button " + button + ": the click after it is left alone");
    // the same gesture that began on a rectangle: the overlay opens nothing for it either
    const [rect] = h.rects();
    rect.dispatch("pointerdown", { clientX: 160, clientY: 250, pointerId: 9, button });
    assert.deepEqual(h.calls, []); assert.equal(captured.size, 0);
    rect.dispatch("pointerup", { clientX: 160, clientY: 250, pointerId: 9, button });
    assert.deepEqual(h.calls, [], "button " + button + ": the layer hands no click on");
    // a primary press right after works as ever
    h.down(300, 300);
    h.up(300, 300);
    assert.deepEqual(h.calls, ["press", "onClick"], "button 0 after: the plain picture's click reaches the panel");
  }
  // an event with no button field at all (a stand-in's, an old synthesizer's) is the primary button
  const h = harness();
  h.overlay.dispatch("pointerdown", { clientX: 300, clientY: 300, pointerId: 7 });
  assert.deepEqual(h.calls, ["press"]);
  assert.equal(captured.get(7), h.overlay);
  captured.get(7)!.dispatch("pointerup", { clientX: 300, clientY: 300, pointerId: 7 });
  assert.deepEqual(h.calls, ["press", "onClick"]);
});

// ── the picture's place in the flow, carried onto the wrapper ──────────────────────────────────────

test("carriedLayout: a percentage width goes to the wrapper and the picture fills it; a float goes to the wrapper and the picture stops floating; a block figure keeps its auto margins on a content-sized wrapper; a vertical-align sits the wrapper on the line", () => {
  assert.deepEqual(carriedLayout({ attrWidth: null, inline: {}, computed: {} }), { wrap: {}, img: {} }, "a plain picture: nothing carried");
  assert.deepEqual(carriedLayout({ attrWidth: "100%", inline: {}, computed: {} }), { wrap: { width: "100%" }, img: { width: "100%" } });
  assert.deepEqual(carriedLayout({ attrWidth: "50%", inline: {}, computed: { marginLeft: "0px", marginRight: "0px" } }), { wrap: { width: "50%" }, img: { width: "100%" } }, "zero margins are not worth a declaration");
  assert.deepEqual(carriedLayout({ attrWidth: "120", inline: {}, computed: {} }), { wrap: {}, img: {} }, "a pixel width hugs as before: the wrapper shrinks to it");
  assert.deepEqual(carriedLayout({ attrWidth: "50%", inline: { width: "300px" }, computed: {} }), { wrap: {}, img: {} }, "the inline width wins over the attribute, and it is not a percentage");
  assert.deepEqual(carriedLayout({ attrWidth: null, inline: { width: "40%" }, computed: {} }), { wrap: { width: "40%" }, img: { width: "100%" } });
  assert.deepEqual(carriedLayout({ attrWidth: null, inline: { maxWidth: "60%" }, computed: {} }), { wrap: { "max-width": "60%" }, img: { "max-width": "100%" } });
  assert.deepEqual(carriedLayout({ attrWidth: "120", inline: {}, computed: { float: "right" } }), { wrap: { float: "right" }, img: { float: "none" } }, "align=right, as the UA sheet computes it");
  assert.deepEqual(carriedLayout({ attrWidth: null, inline: { float: "left" }, computed: {} }), { wrap: { float: "left" }, img: { float: "none" } }, "a stand-in with no computed style: the inline float");
  assert.deepEqual(carriedLayout({ attrWidth: null, inline: {}, computed: { float: "none" } }), { wrap: {}, img: {} });
  assert.deepEqual(
    carriedLayout({ attrWidth: null, inline: { display: "block", marginLeft: "auto", marginRight: "auto" }, computed: { marginLeft: "150px", marginRight: "150px" } }),
    { wrap: { display: "block", width: "fit-content", "margin-left": "auto", "margin-right": "auto" }, img: {} },
    "the centered figure: the SPECIFIED auto, never the computed pixels, so it stays centered when the column changes — and the picture keeps its own auto, which never overflows");
  assert.deepEqual(
    carriedLayout({ attrWidth: "50%", inline: { display: "block", marginLeft: "auto", marginRight: "auto" }, computed: {} }),
    { wrap: { width: "50%", display: "block", "margin-left": "auto", "margin-right": "auto" }, img: { width: "100%" } },
    "a percentage width on a block figure: the percentage, not fit-content; auto stays on the picture too, for the case where a pixel max-width keeps it from filling the wrapper (the layout leg's capped figures)");
  assert.deepEqual(
    carriedLayout({ attrWidth: "50%", inline: { display: "block", maxWidth: "200px", marginLeft: "auto" }, computed: { marginRight: "0px" } }),
    { wrap: { width: "50%", display: "block", "margin-left": "auto" }, img: { width: "100%" } },
    "a right-aligned capped figure (margin-left: auto, a pixel max-width the wrapper does not take): the picture's auto stands, so it keeps its right edge inside a wrapper it no longer fills");
  assert.deepEqual(
    carriedLayout({ attrWidth: "100%", inline: {}, computed: { marginLeft: "8px", marginRight: "8px" } }),
    { wrap: { width: "100%", "margin-left": "8px", "margin-right": "8px" }, img: { width: "100%", "margin-left": "0", "margin-right": "0" } },
    "an hspace beside a percentage width: inside a wrapper the picture fills it would push the picture out, so it moves");
  assert.deepEqual(carriedLayout({ attrWidth: "120", inline: {}, computed: { marginLeft: "8px", marginRight: "8px" } }), { wrap: {}, img: {} }, "an hspace on a hugged picture stays where it is: the wrapper contains it");
  assert.deepEqual(carriedLayout({ attrWidth: null, inline: {}, computed: { verticalAlign: "middle" } }), { wrap: { "vertical-align": "middle" } , img: {} }, "align=middle");
  assert.deepEqual(carriedLayout({ attrWidth: null, inline: {}, computed: { verticalAlign: "baseline" } }), { wrap: {}, img: {} }, "the default alignment is the wrapper's own");
  assert.deepEqual(carriedLayout({ attrWidth: null, inline: {}, computed: { float: "right", verticalAlign: "middle" } }), { wrap: { float: "right" }, img: { float: "none" } }, "a float is out of the line: no vertical-align");
  assert.deepEqual(carriedLayout({ attrWidth: null, inline: { display: "block", verticalAlign: "middle" }, computed: {} }), { wrap: { display: "block", width: "fit-content" }, img: {} }, "a block is not on a line either");
  // the percentage parse: the attribute's dimension syntax and the CSSOM's serialization
  assert.equal(pctOf("100%"), "100%"); assert.equal(pctOf(" 50% "), "50%"); assert.equal(pctOf("33.3%"), "33.3%"); assert.equal(pctOf(".5%"), ".5%");
  assert.equal(pctOf("300"), null); assert.equal(pctOf("50px"), null); assert.equal(pctOf("auto"), null); assert.equal(pctOf(""), null); assert.equal(pctOf(null), null); assert.equal(pctOf("abc%"), null);
});

test("the layer writes the carried layout to the wrapper's style and the picture's, and dispose puts the picture's style attribute back exactly", () => {
  // a width="100%" plot: the wrapper is 100% of the paragraph, the picture 100% of the wrapper
  const plot = harness({ attrs: { src: "plot.png", width: "100%" } });
  assert.deepEqual(decls(plot.wrap.getAttribute("style")), { width: "100%" });
  assert.deepEqual(decls(plot.img.getAttribute("style")), { width: "100%" }, "the picture had no style attribute: it gets the one declaration");
  assert.equal(plot.img.getAttribute("width"), "100%", "the attribute itself is not touched");
  plot.layer.dispose();
  assert.equal(plot.img.getAttribute("style"), null, "no style attribute before, none after");
  assert.equal(plot.img.parentNode, plot.p, "back in its paragraph");
  // a right-aligned logo: the UA sheet floats it, and the wrapper takes the float
  const logo = harness({ attrs: { src: "logo.png", align: "right", width: "120" }, computed: { float: "right", verticalAlign: "baseline", marginLeft: "0px", marginRight: "0px" } });
  assert.deepEqual(decls(logo.wrap.getAttribute("style")), { float: "right" });
  assert.deepEqual(decls(logo.img.getAttribute("style")), { float: "none" });
  logo.layer.dispose();
  assert.equal(logo.img.getAttribute("style"), null);
  // an author's centered block figure: what they wrote is kept, the layer's declarations appended after it, and the
  // attribute restored byte for byte on dispose
  const centered = harness({ attrs: { src: "figure.png", width: "50%" }, styleAttr: "display:block;margin:0 auto", style: { display: "block", marginLeft: "auto", marginRight: "auto" }, computed: { marginLeft: "150px", marginRight: "150px" } });
  assert.deepEqual(decls(centered.wrap.getAttribute("style")), { display: "block", width: "50%", "margin-left": "auto", "margin-right": "auto" });
  assert.equal(centered.img.getAttribute("style"), "display:block;margin:0 auto; width: 100%;", "appended after the author's declarations, so the later ones win; the auto margins are not overridden (they stay on the picture too)");
  centered.layer.dispose();
  assert.equal(centered.img.getAttribute("style"), "display:block;margin:0 auto");
  // a badge on its line
  const badge = harness({ attrs: { src: "badge.svg", align: "middle" }, computed: { verticalAlign: "middle" } });
  assert.deepEqual(decls(badge.wrap.getAttribute("style")), { "vertical-align": "middle" });
  assert.equal(badge.img.getAttribute("style"), null, "nothing for the picture to give up");
  badge.layer.dispose();
  assert.equal(badge.img.getAttribute("style"), null);
  // a plain picture, and the media body's: no inline style anywhere, the sheet's rules alone (the existing tests' world)
  const plain = harness({ attrs: { src: "plain.png" } });
  assert.equal(plain.wrap.getAttribute("style"), null);
  assert.equal(plain.img.getAttribute("style"), null);
  plain.layer.dispose();
  assert.equal(plain.img.getAttribute("style"), null);
  // a picture with a style attribute the layer has no reason to touch keeps it through dispose
  const styled = harness({ attrs: { src: "x.png" }, styleAttr: "border: 1px solid red", style: {} });
  assert.equal(styled.img.getAttribute("style"), "border: 1px solid red");
  styled.layer.dispose();
  assert.equal(styled.img.getAttribute("style"), "border: 1px solid red");
});

test("a carried layout changes nothing about the overlay: it still hugs the picture, still draws, and the wrapper's inline style is the wrapper's alone", () => {
  const h = harness({ attrs: { src: "plot.png", width: "100%" } });
  assert.equal(h.overlay.getAttribute("style"), null, "the wrapper hugs the picture: the sheet's inset: 0 places the overlay");
  assert.equal(h.overlay.parentNode, h.wrap); assert.equal(h.img.parentNode, h.wrap);
  h.down(150, 240); h.move(250, 300); h.up(250, 300);
  const r = drawnOf(h.calls);
  assert.ok(r); near(r!.x, 0.1667, "x"); near(r!.w, 0.3333, "w");
  h.layer.dispose();
  assert.equal(h.p.childNodes[0], h.img, "the picture first in its paragraph again");
  assert.equal(h.p.querySelectorAll(".fc-imgwrap").length, 0);
});
