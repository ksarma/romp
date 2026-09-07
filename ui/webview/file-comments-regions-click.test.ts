// A press the overlay covers is handed on, and the overlay is placed by the picture's COMPUTED object-fit
// (plans/file-review.md, Slice 3; the 2026-09-06 review of the slice). Two defects, one cause each:
//
// - The armed overlay captures every pointer it takes (so a drag that leaves the picture stays alive), and a
//   captured pointer's pointerup AND the click after it are dispatched to the CAPTURING element (Pointer Events,
//   event dispatch). So a click on a rectangle, or on a picture an embed-line comment had framed as a control,
//   reached the delegate root with the overlay as its target — no data-act on the way up, nothing opened — and
//   only Tab + Enter still worked. The layer now clicks the covered control itself (handOn) and swallows the
//   browser's own click after it. The file-comments-regions.test.ts stand-in could not show this: its
//   setPointerCapture is inert and it dispatches the click on the rectangle, which a browser never does there.
// - place() assumed `object-fit: contain` for every picture. The media body's .fileview-img has it; a figure
//   in rendered markdown has no rule, so a `width`/`height` pair the author wrote (the sanitizer keeps both)
//   is honoured by STRETCHING, and the letterbox computed for it put the overlay over the middle of the element.
//   The layer now reads the computed value and hands it to drawnBox; the pixel-offset branch of place() was
//   also untested (the harness's pictures always shared their element's aspect).
//
// The stand-in here models what those two need and nothing more: pointer capture (the pointerup and the click
// go to the capturing element), an element's click() (a bubbling click, as in a browser), a client rect and a
// computed object-fit per element. The real delegate (actions.ts) resolves the activations, as the panel's body
// row does. file-comments-regions-browser.test.ts drives the same module with a real pointer in Chromium.
// Synthetic values only.
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
win.getComputedStyle = (el: E) => ({ objectFit: el.fit });
(globalThis as any).window = win;
(globalThis as any).document = doc;   // the delegate compares its root against it

import { RegionLayer, type RegionMark } from "./file-comments-regions";
import { delegate } from "./actions";

// ── the harness: the viewer's body row with one picture, the panel's listeners on the row ─────────
/** A 600×400 picture drawn at half size, 100px in and 200px down, like the regions harness's figure. */
const IMG_RECT = rectOf(100, 200, 300, 200);
const mark = (id: string, region = { x: 0.1667, y: 0.2, w: 0.3333, h: 0.3 }): RegionMark => ({ id, region, label: "you", state: "current" });

function harness(over: { rect?: Rect; fit?: string; active?: boolean } = {}) {
  captured.clear();
  const calls: string[] = [];
  const acted: E[] = [];
  const row = doc.createElement("div"); row.className = "fileview-body";
  const p = doc.createElement("p"); row.appendChild(p);
  const img = doc.createElement("img"); p.appendChild(img);
  img.rect = over.rect || IMG_RECT; img.naturalWidth = 600; img.naturalHeight = 400; img.fit = over.fit ?? "contain";
  // the panel's wiring on the body row, in its order: the delegate first, the picture listener after it
  delegate(row as unknown as HTMLElement, { fcopen: (el) => { calls.push("fcopen:" + el.dataset.id); acted.push(el as unknown as E); } });
  row.addEventListener("click", (ev) => { if (ev.target.tagName === "IMG") calls.push("imgclick"); });
  const layer = new RegionLayer(img as unknown as HTMLImageElement, {
    onDraw: (_i, r) => { calls.push("onDraw:" + JSON.stringify(r)); },
    onClick: () => { calls.push("onClick"); },
    onPress: () => { calls.push("press"); },
  });
  layer.setActive(over.active ?? true);
  const overlay = layer.overlay as unknown as E;
  return {
    calls, acted, row, img, layer, overlay,
    rects: () => overlay.querySelectorAll(".fc-region"),
    /** A press and release without movement, then the click a browser dispatches after it: to the element
     *  that captured the pointer while it was down, else to the press target itself. */
    press: (el: E, x: number, y: number, id = 7): Ev => {
      el.dispatch("pointerdown", { clientX: x, clientY: y, pointerId: id, button: 0 });
      const cap = captured.get(id) || el;
      cap.dispatch("pointerup", { clientX: x, clientY: y, pointerId: id });
      return cap.dispatch("click");
    },
    /** A drag: the moves, the release and the click all go to the capturing element. */
    drag: (el: E, from: [number, number], to: [number, number], id = 7): Ev => {
      el.dispatch("pointerdown", { clientX: from[0], clientY: from[1], pointerId: id, button: 0 });
      const cap = captured.get(id) || el;
      cap.dispatch("pointermove", { clientX: to[0], clientY: to[1], pointerId: id });
      cap.dispatch("pointerup", { clientX: to[0], clientY: to[1], pointerId: id });
      return cap.dispatch("click");
    },
  };
}

// ── the click on a rectangle ───────────────────────────────────────────────────────────────────────

test("armed: a press on a rectangle is captured by the overlay, so the layer clicks the rectangle itself and the card's action fires once", () => {
  const h = harness();
  const [rect] = h.layer.paint([mark("c1")], null, false) as unknown as E[];
  const click = h.press(rect, 160, 250);
  assert.equal(captured.size, 0, "the capture was released with the pointer");
  assert.deepEqual(h.calls, ["press", "fcopen:c1"], "the float hides on the press; the card opens; no picture click, no Comment offer");
  assert.equal(h.acted[0], rect, "the rectangle is the activated control");
  assert.ok(rect.classList.contains("romp-acted"), "and it acknowledged the press (flash)");
  assert.equal(click.defaultPrevented, true, "the browser's own click, on the overlay, is swallowed: it is not a second activation");
  assert.equal(h.rects().length, 1);
});

test("armed: a rectangle rebuilt by a paint pass mid-press still opens its comment — the one now carrying the same id", () => {
  const h = harness();
  const [old] = h.layer.paint([mark("c1")], null, false) as unknown as E[];
  old.dispatch("pointerdown", { clientX: 160, clientY: 250, pointerId: 7, button: 0 });
  const [fresh] = h.layer.paint([mark("c1", { x: 0.2, y: 0.2, w: 0.3, h: 0.3 })], null, false) as unknown as E[];   // a status arrived: every rectangle is rebuilt
  assert.notEqual(fresh, old); assert.equal(old.parentNode, null, "the pressed rectangle is gone from the overlay");
  const cap = captured.get(7)!;
  cap.dispatch("pointerup", { clientX: 160, clientY: 250, pointerId: 7 });
  const click = cap.dispatch("click");
  assert.deepEqual(h.calls, ["press", "fcopen:c1"]);
  assert.equal(h.acted[0], fresh, "the click landed on the rectangle that now stands for the comment");
  assert.equal(click.defaultPrevented, true);
  // the comment resolved mid-press: nothing is left to open, nothing throws, the browser's click is left alone
  h.calls.length = 0;
  fresh.dispatch("pointerdown", { clientX: 160, clientY: 250, pointerId: 8, button: 0 });
  h.layer.paint([], null, false);
  const cap2 = captured.get(8)!;
  cap2.dispatch("pointerup", { clientX: 160, clientY: 250, pointerId: 8 });
  const click2 = cap2.dispatch("click");
  assert.deepEqual(h.calls, ["press"]);
  assert.equal(click2.defaultPrevented, false);
});

test("armed: a press on the composer's pending region opens nothing, and a drag that begins on a rectangle draws (it does not open the card)", () => {
  const h = harness();
  h.layer.paint([mark("c1")], { x: 0.5, y: 0.5, w: 0.2, h: 0.2 }, false);
  const pending = h.rects().find((r) => r.classList.contains("fc-region-pending"))!;
  assert.ok(pending && pending.dataset.act === undefined, "the pending region is not a control");
  h.press(pending, 280, 330);
  assert.deepEqual(h.calls, ["press"], "no card, no picture click");
  h.calls.length = 0;
  const rect = h.rects().find((r) => r.dataset.id === "c1")!;
  const click = h.drag(rect, [160, 250], [250, 300]);
  assert.equal(h.calls.length, 2); assert.equal(h.calls[0], "press");
  assert.match(h.calls[1], /^onDraw:\{"x":0\.2,"y":0\.25,"w":0\.3,"h":0\.25\}$/, "the drag is measured from where it began, rectangle or not");
  assert.equal(click.defaultPrevented, true, "the click after a drag is swallowed, as before");
});

// ── the click on the picture ───────────────────────────────────────────────────────────────────────

test("armed: a picture an embed-line comment framed (data-act=fcopen) gets its click back — the card opens AND the panel's picture listener hears it; a plain picture goes to onClick", () => {
  const h = harness();
  h.layer.paint([], null, false);
  h.img.dataset.act = "fcopen"; h.img.dataset.id = "c9";   // frameImage's marks, as the panel paints them on an embed line's figure
  const click = h.press(h.overlay, 300, 300);
  assert.deepEqual(h.calls, ["press", "fcopen:c9", "imgclick"], "what a click on the picture did before the overlay stood over it: the card, then the Comment offer");
  assert.equal(h.acted[0], h.img);
  assert.equal(click.defaultPrevented, true, "the browser's click on the overlay is swallowed");
  // the frame comes off (the comment resolved): the picture's click is the panel's, through onClick
  delete h.img.dataset.act; delete h.img.dataset.id;
  h.calls.length = 0;
  const plain = h.press(h.overlay, 300, 300);
  assert.deepEqual(h.calls, ["press", "onClick"]);
  assert.equal(plain.defaultPrevented, false, "a click the layer did not hand on is left alone");
});

test("disarmed (the panel closed, or a coarse pointer): the overlay takes no press, so the browser's own click reaches the rectangle", () => {
  const h = harness({ active: false });
  const [rect] = h.layer.paint([mark("c1")], null, false) as unknown as E[];
  const click = h.press(rect, 160, 250);
  assert.equal(captured.size, 0, "nothing captured: the pointerdown handler stood down");
  assert.deepEqual(h.calls, ["fcopen:c1"], "no press hook either; the delegate root resolved the rectangle's own click");
  assert.equal(click.defaultPrevented, false);
  assert.equal(click.target, rect);
});

// ── the overlay's place: the computed object-fit ──────────────────────────────────────────────────

test("place: under object-fit contain a picture drawn smaller than its element gets pixel offsets, and a drag that leaves into the letterbox band is clamped to the picture", () => {
  const h = harness({ rect: rectOf(100, 200, 300, 300), fit: "contain" });   // a 600×400 picture in a square element: 300×200, 50px down
  assert.equal(h.overlay.getAttribute("style"), "left: 0px; top: 50px; width: 300px; height: 200px;", "the overlay is the drawn picture, not the element");
  assert.deepEqual(h.layer.box(), { left: 100, top: 250, width: 300, height: 200 });
  h.drag(h.overlay, [250, 300], [150, 210]);   // from the picture's middle up into the band above it (the captured pointer keeps the drag alive)
  assert.deepEqual(h.calls, ["press", 'onDraw:{"x":0.1667,"y":0,"w":0.3333,"h":0.25}'], "the fractions are of the drawn picture: the end clamps to its top edge");
  // re-measured on the picture's load and on a resize (the window's, where no ResizeObserver exists)
  h.img.rect = rectOf(100, 200, 300, 400);
  h.img.dispatch("load");
  assert.equal(h.overlay.getAttribute("style"), "left: 0px; top: 100px; width: 300px; height: 200px;");
  h.img.rect = rectOf(100, 200, 300, 200);
  win.dispatchEvent(new Event("resize"));
  assert.equal(h.overlay.getAttribute("style"), null, "the element at the picture's own aspect: the sheet's inset: 0 places it again");
  h.layer.dispose();
});

test("place: a figure in rendered markdown has no object-fit rule — fill — so a width/height pair the author wrote stretches the picture over the element and the overlay covers all of it", () => {
  // <img src="plot.png" width="1200" height="800"> for a 600×400 picture in a narrow column: the element is 300×300 here
  const h = harness({ rect: rectOf(100, 200, 300, 300), fit: "fill" });
  assert.equal(h.overlay.getAttribute("style"), null, "no letterbox: the sheet's inset: 0 is the whole element");
  assert.deepEqual(h.layer.box(), { left: 100, top: 200, width: 300, height: 300 });
  h.drag(h.overlay, [250, 300], [150, 210]);
  assert.deepEqual(h.calls, ["press", 'onDraw:{"x":0.1667,"y":0.0333,"w":0.3333,"h":0.3}'], "what the person sees at the top of the element IS the top of the picture");
  // a picture with no rule at all reads "" from the computed style: the initial value, fill
  const none = harness({ rect: rectOf(100, 200, 300, 300), fit: "" });
  assert.equal(none.overlay.getAttribute("style"), null);
  assert.deepEqual(none.layer.box(), { left: 100, top: 200, width: 300, height: 300 });
});

test("place: a document with no computed style to read is fill, the initial value; a wrapper not laid out claims nothing", () => {
  const gcs = win.getComputedStyle;
  delete win.getComputedStyle;
  try {
    const h = harness({ rect: rectOf(100, 200, 300, 300), fit: "contain" });
    assert.equal(h.overlay.getAttribute("style"), null, "nothing to measure the fit with: the element is the picture");
    assert.deepEqual(h.layer.box(), { left: 100, top: 200, width: 300, height: 300 });
  } finally { win.getComputedStyle = gcs; }
  const unlaid = harness({ rect: rectOf(0, 0, 0, 0), fit: "contain" });
  assert.equal(unlaid.overlay.getAttribute("style"), null);
});
