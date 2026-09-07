// The overlay follows the drawn picture through a ResizeObserver on the picture AND its wrapper, and lets go of both
// on dispose (plans/file-review.md, Slice 3: the rectangle re-paints correctly at any viewer width; the 2026-09-06
// review of the slice). Every other stand-in runs under node, where `ResizeObserver` is undefined, so only the
// window-resize fallback ever ran under test: `observe(this.wrap)` and `disconnect()` could be deleted with the whole
// family green. The wrapper's observation is not decoration. A wrapper that outgrows its picture — a carried
// `width="100%"` with the picture capped by `max-width: 300px`, and a `margin-top: 10%` that resolves against the
// wrapper's width — moves the picture inside it when the column narrows (the aside opening: no window resize) while
// the picture's own size does not change, so only the wrapper's observation fires, and place()'s pixel offsets
// against the wrapper are stale until it does. The numbers below are the ones headless Chromium lays out for that
// figure in a 600px column (file-comments-regions-sizer-browser.test.ts drives the same scene in a real browser).
//
// The fake observer keeps a browser's semantics where they matter: a callback fires only for an element that
// instance observes, and a disconnected instance observes nothing. So the wrapper's layout change reaches the layer
// only through `observe(this.wrap)`, and a dropped `disconnect()` shows as an instance still holding its targets.
// Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";

// ── the DOM stand-in ───────────────────────────────────────────────────────────────────────────────
type Rect = { left: number; top: number; right: number; bottom: number; width: number; height: number };
const rectOf = (left: number, top: number, width: number, height: number): Rect => ({ left, top, width, height, right: left + width, bottom: top + height });

class Doc {
  createElement(tag: string): E { return new E(this, tag.toUpperCase()); }
}
class E {
  parentNode: E | null = null;
  childNodes: E[] = [];
  attrs = new Map<string, string>();
  listeners = new Map<string, Array<(ev: unknown) => void>>();
  title = ""; tabIndex = -1;
  naturalWidth = 0; naturalHeight = 0; complete = true;
  /** the client rect a test gives the element; a wrapper with none hugs its picture (the sheet's inline-block
   *  around a block img), a wrapper with one stands where the test says — outgrowing the picture */
  rect: Rect | null = null;
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
      get: (_t, k) => (typeof k === "string" ? this.attrs.get("data-" + String(k).replace(/[A-Z]/g, (c) => "-" + c.toLowerCase())) : undefined),
      set: (_t, k, v) => { this.attrs.set("data-" + String(k).replace(/[A-Z]/g, (c) => "-" + c.toLowerCase()), String(v)); return true; },
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
  addEventListener(type: string, fn: (ev: unknown) => void): void { (this.listeners.get(type) || this.listeners.set(type, []).get(type)!).push(fn); }
  removeEventListener(type: string, fn: (ev: unknown) => void): void { const l = this.listeners.get(type); if (l) l.splice(l.indexOf(fn), 1); }
  getBoundingClientRect(): Rect {
    if (this.rect) return this.rect;
    if (this.classList.contains("fc-imgwrap")) { const img = this.childNodes.find((c) => c.tagName === "IMG"); return img ? img.getBoundingClientRect() : rectOf(0, 0, 0, 0); }
    return rectOf(0, 0, 0, 0);
  }
}

// ── the fake ResizeObserver: a browser's semantics where they matter ──────────────────────────────
type Callback = (entries: Array<{ target: E }>, observer: FakeObserver) => void;
/** every instance the module constructed, in order */
const observers: FakeObserver[] = [];
class FakeObserver {
  targets = new Set<E>();
  disconnected = false;
  constructor(readonly cb: Callback) { observers.push(this); }
  observe(t: E): void { this.targets.add(t); }
  unobserve(t: E): void { this.targets.delete(t); }
  disconnect(): void { this.targets.clear(); this.disconnected = true; }
}
/** An element's box changed after layout: every instance observing THAT element is called, as a browser does; an
 *  element nobody observes reaches nobody. */
function resized(el: E): number {
  let fired = 0;
  for (const o of observers) if (o.targets.has(el)) { o.cb([{ target: el }], o); fired++; }
  return fired;
}

// ── globals the module reaches for ────────────────────────────────────────────────────────────────
const doc = new Doc();
const win: any = new EventTarget();
win.getComputedStyle = (el: E) => ({ objectFit: el.fit });
/** the `resize` listeners registered on the window right now (a removal of one never added changes nothing, as in a browser) */
const resizeFns = new Set<EventListener>();
const resizeListeners = (): number => resizeFns.size;
const addL = win.addEventListener.bind(win), removeL = win.removeEventListener.bind(win);
win.addEventListener = (type: string, fn: EventListener) => { if (type === "resize") resizeFns.add(fn); addL(type, fn); };
win.removeEventListener = (type: string, fn: EventListener) => { if (type === "resize") resizeFns.delete(fn); removeL(type, fn); };
(globalThis as any).window = win;

import { RegionLayer } from "./file-comments-regions";

/** A 300×150 figure in a paragraph — a picture in rendered markdown, no object-fit rule (fill). */
function harness() {
  const p = doc.createElement("p");
  const img = doc.createElement("img"); p.appendChild(img);
  img.naturalWidth = 300; img.naturalHeight = 150;
  img.rect = rectOf(20, 88, 300, 150);
  const layer = new RegionLayer(img as unknown as HTMLImageElement, { onDraw: () => {}, onClick: () => {} });
  return { p, img, layer, wrap: layer.wrap as unknown as E, overlay: layer.overlay as unknown as E, style: () => (layer.overlay as unknown as E).getAttribute("style") };
}

test("with a ResizeObserver the layer observes the picture AND its wrapper, and no window listener: the wrapper's own resize re-places an overlay whose picture moved without changing size", () => {
  observers.length = 0;
  (globalThis as any).ResizeObserver = FakeObserver;
  try {
    const h = harness();
    assert.equal(observers.length, 1, "one observer per layer");
    const ro = observers[0];
    assert.ok(ro.targets.has(h.img), "the picture is observed: the drawn size's own event");
    assert.ok(ro.targets.has(h.wrap), "the wrapper is observed: the picture can move inside it with no size change of its own");
    assert.equal(ro.targets.size, 2);
    assert.equal(resizeListeners(), 0, "the observer is the event; the window's resize stands in only where it is missing");
    assert.equal(h.style(), null, "a wrapper that hugs the picture: the sheet's inset: 0 is the overlay");
    // the figure whose wrapper outgrows it: width="100%" carried onto the wrapper (600px of the column), the picture capped by
    // max-width: 300px, margin-top: 10% — Chromium lays the wrapper out 600×210 at (20, 28) and the picture 300×150 at (20, 88)
    h.wrap.rect = rectOf(20, 28, 600, 210); h.img.rect = rectOf(20, 88, 300, 150);
    assert.equal(resized(h.wrap), 1, "laid out: the wrapper's observation fires");
    assert.equal(h.style(), "left: 0px; top: 60px; width: 300px; height: 150px;", "pixel offsets against the wrapper");
    // the aside opens and the column narrows to 400px, with no window resize: the wrapper is 400×190, the picture the SAME
    // 300×150 but 40px down instead of 60 — the picture's observation has nothing to report; only the wrapper's fires
    h.wrap.rect = rectOf(20, 28, 400, 190); h.img.rect = rectOf(20, 68, 300, 150);
    assert.equal(resized(h.wrap), 1, "the wrapper's layout change reaches the layer through observe(this.wrap) alone");
    assert.equal(h.style(), "left: 0px; top: 40px; width: 300px; height: 150px;", "the overlay follows the picture down the wrapper");
    // narrower than the picture: the picture shrinks (200×100, 20px down) and its own observation fires
    h.wrap.rect = rectOf(20, 28, 200, 120); h.img.rect = rectOf(20, 48, 200, 100);
    assert.equal(resized(h.img), 1);
    assert.equal(h.style(), "left: 0px; top: 20px; width: 200px; height: 100px;");
    // dispose: the observer is disconnected — nothing left observing a picture the layer no longer stands over
    h.layer.dispose();
    assert.equal(ro.disconnected, true, "dispose disconnects the observer");
    assert.equal(ro.targets.size, 0);
    assert.equal(resizeListeners(), 0);
    const last = h.style();
    h.wrap.rect = rectOf(20, 28, 600, 210); h.img.rect = rectOf(20, 88, 300, 150);
    assert.equal(resized(h.wrap), 0, "a later layout change reaches no one");
    assert.equal(h.style(), last);
    // the picture is back in its paragraph, the wrapper gone
    assert.equal(h.img.parentNode, h.p);
    assert.equal(h.wrap.parentNode, null);
  } finally { delete (globalThis as any).ResizeObserver; }
});

test("two layers, two observers: disposing one leaves the other's observations standing", () => {
  observers.length = 0;
  (globalThis as any).ResizeObserver = FakeObserver;
  try {
    const a = harness(), b = harness();
    assert.equal(observers.length, 2);
    a.layer.dispose();
    assert.equal(observers[0].disconnected, true);
    assert.equal(observers[1].disconnected, false);
    assert.ok(observers[1].targets.has(b.img) && observers[1].targets.has(b.wrap));
    b.wrap.rect = rectOf(20, 28, 600, 210); b.img.rect = rectOf(20, 88, 300, 150);
    assert.equal(resized(b.wrap), 1);
    assert.equal(b.style(), "left: 0px; top: 60px; width: 300px; height: 150px;");
    b.layer.dispose();
    assert.equal(observers[1].disconnected, true);
  } finally { delete (globalThis as any).ResizeObserver; }
});

test("without a ResizeObserver the window's resize stands in, and dispose removes that listener", () => {
  observers.length = 0;
  assert.equal(typeof (globalThis as any).ResizeObserver, "undefined", "node has none: the fallback path");
  const h = harness();
  assert.equal(observers.length, 0);
  assert.equal(resizeListeners(), 1, "one resize listener on the window");
  h.wrap.rect = rectOf(20, 28, 600, 210); h.img.rect = rectOf(20, 88, 300, 150);
  win.dispatchEvent(new Event("resize"));
  assert.equal(h.style(), "left: 0px; top: 60px; width: 300px; height: 150px;", "a window resize re-places");
  h.layer.dispose();
  assert.equal(resizeListeners(), 0, "dispose removes the listener");
  const last = h.style();
  h.img.rect = rectOf(20, 68, 300, 150);
  win.dispatchEvent(new Event("resize"));
  assert.equal(h.style(), last, "a resize after dispose reaches nothing");
});
