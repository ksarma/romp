// The overlay's pointer protocol against the browser's part of it (plans/file-review.md, Slices 3 and 4; contract
// E5): where the click a press synthesizes LANDS. A DOM stand-in here models what the regions test's cannot — pointer
// capture retargets the events that follow it, and the synthesized click goes to the capture target (else to the
// element the press began and ended on), and a press whose default is not cancelled focuses the control under it.
// That is the mechanism behind the 2026-09-06 defect: the overlay captured every press, so a click on a rectangle
// reached the delegate root as a click on the overlay, with no data-act to route, and the card never opened while the
// panel was open. The layer is driven directly, with the REAL delegate helper on the row the panel uses as its root.
// Synthetic fixtures only: the notes-api world, placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";

// ── the DOM stand-in ───────────────────────────────────────────────────────────────────────────────
type Rect = { left: number; top: number; right: number; bottom: number; width: number; height: number };
const rectOf = (left: number, top: number, width: number, height: number): Rect => ({ left, top, width, height, right: left + width, bottom: top + height });
const ZERO = rectOf(0, 0, 0, 0);
type Init = { clientX?: number; clientY?: number; pointerId?: number; button?: number; buttons?: number };
type Ev = Init & { type: string; target: E; currentTarget: E | null; defaultPrevented: boolean; preventDefault(): void; stopPropagation(): void };
class Doc {
  body: E;
  /** the element holding pointer capture, as the browser tracks it; the tests read where a click then lands */
  captured: E | null = null;
  captures = 0;
  activeElement: E;
  constructor() { this.body = new E(this, "BODY"); this.activeElement = this.body; }
  createElement(tag: string): E { return new E(this, tag.toUpperCase()); }
}
const kebab = (k: string | symbol): string => String(k).replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
class E {
  attrs = new Map<string, string>();
  listeners = new Map<string, Array<(ev: Ev) => void>>();
  childNodes: E[] = [];
  parentNode: E | null = null;
  title = ""; tabIndex = -1; offsetWidth = 0;
  width = 0; height = 0;                              // a canvas
  naturalWidth = 0; naturalHeight = 0; complete: boolean | undefined = undefined;   // a picture
  rect: Rect | null = null;
  dataset: Record<string, string>;
  classList = {
    add: (...c: string[]) => this.setClasses([...this.classes(), ...c]),
    remove: (...c: string[]) => this.setClasses(this.classes().filter((x) => !c.includes(x))),
    toggle: (c: string, on?: boolean) => { if (on === undefined ? !this.classes().includes(c) : on) this.classList.add(c); else this.classList.remove(c); },
    contains: (c: string) => this.classes().includes(c),
  };
  constructor(public ownerDocument: Doc, public tagName: string) {
    this.dataset = new Proxy({} as Record<string, string>, {
      get: (_t, k) => (typeof k === "string" ? this.attrs.get("data-" + kebab(k)) : undefined),
      set: (_t, k, v) => { this.attrs.set("data-" + kebab(k), String(v)); return true; },
    });
  }
  private classes(): string[] { return (this.attrs.get("class") || "").split(/\s+/).filter(Boolean); }
  private setClasses(c: string[]): void { this.attrs.set("class", [...new Set(c)].join(" ")); }
  get className(): string { return this.attrs.get("class") || ""; }
  set className(v: string) { this.attrs.set("class", v); }
  get parentElement(): E | null { return this.parentNode; }
  getAttribute(n: string): string | null { return this.attrs.has(n) ? (this.attrs.get(n) as string) : null; }
  setAttribute(n: string, v: string): void { this.attrs.set(n, v); }
  removeAttribute(n: string): void { this.attrs.delete(n); }
  appendChild<X extends E>(n: X): X { if (n.parentNode) n.parentNode.removeChild(n); this.childNodes.push(n); n.parentNode = this; return n; }
  insertBefore(n: E, ref: E | null): E { if (!ref) return this.appendChild(n); if (n.parentNode) n.parentNode.removeChild(n); this.childNodes.splice(this.childNodes.indexOf(ref), 0, n); n.parentNode = this; return n; }
  removeChild(n: E): E { const i = this.childNodes.indexOf(n); if (i >= 0) this.childNodes.splice(i, 1); n.parentNode = null; return n; }
  remove(): void { if (this.parentNode) this.parentNode.removeChild(this); }
  contains(n: E | null): boolean { for (let x: E | null = n; x; x = x.parentNode) if (x === this) return true; return false; }
  matches(sel: string): boolean {
    const m = /^(?:\.([\w-]+)|\[([\w-]+)\])$/.exec(sel);
    if (!m) throw new Error("the stand-in matches one class or one attribute: " + sel);
    return m[1] ? this.classList.contains(m[1]) : this.attrs.has(m[2]);
  }
  closest(sel: string): E | null { for (let x: E | null = this; x; x = x.parentNode) if (x.matches(sel)) return x; return null; }
  querySelectorAll(sel: string): E[] { const out: E[] = []; const visit = (n: E) => { for (const c of n.childNodes) { if (c.matches(sel)) out.push(c); visit(c); } }; visit(this); return out; }
  querySelector(sel: string): E | null { return this.querySelectorAll(sel)[0] || null; }
  addEventListener(type: string, fn: (ev: Ev) => void): void { (this.listeners.get(type) || this.listeners.set(type, []).get(type)!).push(fn); }
  removeEventListener(type: string, fn: (ev: Ev) => void): void { const l = this.listeners.get(type); if (l) l.splice(l.indexOf(fn), 1); }
  /** Dispatch with bubbling: every ancestor's listeners run until one stops propagation. */
  dispatch(type: string, init: Init = {}): Ev {
    let stopped = false;
    const ev: Ev = { ...init, type, target: this, currentTarget: null, defaultPrevented: false,
      preventDefault() { this.defaultPrevented = true; }, stopPropagation() { stopped = true; } };
    for (let n: E | null = this; n && !stopped; n = n.parentNode) { ev.currentTarget = n; for (const fn of [...(n.listeners.get(type) || [])]) fn(ev); }
    return ev;
  }
  /** The rect a test gave the element; a wrapper the layer made hugs its picture. */
  getBoundingClientRect(): Rect {
    if (this.rect) return this.rect;
    if (this.classList.contains("fc-imgwrap")) { const img = this.childNodes.find((c) => c.tagName === "IMG"); return img ? img.getBoundingClientRect() : ZERO; }
    return ZERO;
  }
  setPointerCapture(): void { this.ownerDocument.captured = this; this.ownerDocument.captures++; }
  releasePointerCapture(): void { if (this.ownerDocument.captured === this) this.ownerDocument.captured = null; }
  focus(): void { if (this.tabIndex >= 0) this.ownerDocument.activeElement = this; }
  click(): void { this.dispatch("click"); }
}

// ── globals the modules reach for, installed before they are imported ──────────────────────────────
const doc = new Doc();
const win: any = new EventTarget();
win.devicePixelRatio = 1;
win.matchMedia = () => ({ matches: false });
(globalThis as any).window = win;
(globalThis as any).document = doc;

// ── the browser's part of a press ──────────────────────────────────────────────────────────────────
type Pt = [number, number];
/** The element the pointer is over at a point of the press, or, once something holds capture, that element. */
const under = (el: E): E => doc.captured || el;
/** The common ancestor of two elements: where a click lands when the press began and ended on different ones. */
function common(a: E, b: E): E { for (let x: E | null = a; x; x = x.parentNode) if (x.contains(b)) return x; return doc.body; }
/** A press as the browser delivers it: pointerdown at `on`; a mousedown whose default stands focuses the control
 *  under it (a rectangle is a Tab stop); each move at the element under the pointer, or the capture target once one
 *  is set; pointerup likewise; then the click the browser synthesizes, at the capture target held through the release,
 *  else at the element common to where the press began and ended. Returns the down and click events. */
function press(on: E, from: Pt, moves: Array<{ at: Pt; over: E; buttons?: number }>, release: { at: Pt; over: E } = { at: from, over: on }) {
  const down = on.dispatch("pointerdown", { clientX: from[0], clientY: from[1], pointerId: 1, button: 0, buttons: 1 });
  if (!down.defaultPrevented) { let f: E | null = on; while (f && f.tabIndex < 0) f = f.parentNode; if (f) f.focus(); }
  for (const m of moves) under(m.over).dispatch("pointermove", { clientX: m.at[0], clientY: m.at[1], pointerId: 1, buttons: m.buttons ?? 1 });
  const upOn = under(release.over);
  upOn.dispatch("pointerup", { clientX: release.at[0], clientY: release.at[1], pointerId: 1, button: 0, buttons: 0 });
  const click = common(on, upOn).dispatch("click", { clientX: release.at[0], clientY: release.at[1], button: 0 });
  return { down, click };
}

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const ID = "1757145600000-0";
const REGION = { x: 0.1634, y: 0.101, w: 0.3268, h: 0.1515 };   // page 2's header, from the regions test
// a US-letter page drawn at 306×396 CSS px from (100, 200), its canvas the 612×792 backing store
const PAGE_RECT = rectOf(100, 200, 306, 396);
// a 600×400 figure drawn at half size from (100, 200)
const IMG_RECT = rectOf(100, 200, 300, 200);

/** The viewer's body row (the panel's delegate root) holding a PDF page or a standalone image, a layer over it with
 *  one rectangle painted, and the row's delegate routing fcopen — the panel's wiring, without the panel. */
async function layerOver(kind: "pdf" | "image") {
  const { RegionLayer } = await import("./file-comments-regions");
  const { delegate } = await import("./actions");
  doc.captured = null; doc.captures = 0; doc.activeElement = doc.body;
  const row = doc.createElement("div"); row.className = "fileview-main"; doc.body.appendChild(row);
  const body = doc.createElement("div"); body.className = "fileview-body"; row.appendChild(body);
  const outside = doc.createElement("div"); outside.className = "fileview-elsewhere"; row.appendChild(outside);   // the rest of the viewer, past the picture
  let picture: E; let anchor: E | null = null;
  if (kind === "pdf") {
    anchor = doc.createElement("div"); anchor.className = "fileview-pdf-page"; anchor.dataset.page = "2"; anchor.rect = PAGE_RECT;
    picture = doc.createElement("canvas"); picture.className = "fileview-pdf-canvas"; picture.dataset.page = "2"; picture.rect = PAGE_RECT; picture.width = 612; picture.height = 792;
    anchor.appendChild(picture); body.appendChild(anchor);
  } else {
    picture = doc.createElement("img"); picture.className = "fileview-img"; picture.rect = IMG_RECT; picture.naturalWidth = 600; picture.naturalHeight = 400; picture.complete = true;
    body.appendChild(picture);
  }
  const drawn: Array<{ x: number; y: number; w: number; h: number }> = [];
  let clicks = 0, presses = 0;
  const layer = new RegionLayer(picture as unknown as HTMLCanvasElement, {
    onDraw: (_i, r) => { drawn.push(r); }, onClick: () => { clicks++; }, onPress: () => { presses++; },
  }, anchor as unknown as HTMLElement | null);
  const opened: string[] = [];
  delegate(row as unknown as HTMLElement, { fcopen: (x) => { opened.push(x.dataset.id!); } });
  const overlay = layer.overlay as unknown as E;
  const paint = () => layer.paint([{ id: ID, region: REGION, label: "you", state: "current" }], null, false);
  paint();
  const rect = overlay.querySelector(".fc-region")!;
  assert.ok(rect, "the rectangle painted");
  assert.equal(rect.dataset.act, "fcopen");
  return { layer, overlay, rect, outside, picture, drawn, opened, teardown: () => { layer.dispose(); row.remove(); },
    get clicks() { return clicks; }, get presses() { return presses; } };
}

for (const kind of ["pdf", "image"] as const) {
  test("a press on a rectangle while the overlay draws (" + kind + "): not captured, so the click reaches the rectangle and fcopen opens its card; the rectangle takes focus", async () => {
    const h = await layerOver(kind);
    h.layer.setActive(true);
    const { down, click } = press(h.rect, [160, 250], []);
    assert.deepEqual(h.opened, [ID], "the row's delegate routed fcopen for the comment: the card opens");
    assert.equal(click.target, h.rect, "because the browser's click landed on the rectangle");
    assert.equal(doc.captures, 0, "the overlay did not take the pointer: a capture would have sent the click to the overlay");
    assert.equal(down.defaultPrevented, true, "the press's default is still cancelled: no selection starts behind the overlay");
    assert.equal(click.defaultPrevented, false, "nothing swallowed it");
    assert.equal(doc.activeElement, h.rect, "the rectangle holds focus, as the mousedown would have left it");
    assert.equal(h.clicks, 0, "not a picture click");
    assert.equal(h.drawn.length, 0, "nothing drawn");
    assert.equal(h.presses, 1, "the panel still heard the press (its float hides on one)");
    h.teardown();
  });
}

test("the contrast the stand-in models: a press on the bare picture IS captured, and the click the browser synthesizes then lands on the capture target, not under the pointer", async () => {
  const h = await layerOver("pdf");
  h.layer.setActive(true);
  const { click } = press(h.overlay, [130, 230], []);
  assert.equal(doc.captures, 1, "the overlay took the pointer, as it must for a drag that leaves the picture");
  assert.equal(click.target, h.overlay);
  assert.equal(h.clicks, 1, "the picture click the viewer already had");
  assert.deepEqual(h.opened, [], "no card: nothing on the overlay's own path carries a data-act");
  assert.equal(doc.captured, null, "released with the pointer");
  h.teardown();
});

test("a drag that begins on a rectangle still draws: capture is taken when the band appears, so a release past the picture's edge lands, and the synthesized click is swallowed", async () => {
  const h = await layerOver("pdf");
  h.layer.setActive(true);
  const { click } = press(h.rect, [160, 250],
    [{ at: [162, 251], over: h.rect }, { at: [200, 280], over: h.overlay }, { at: [500, 700], over: h.outside }],
    { at: [500, 700], over: h.outside });
  assert.equal(doc.captures, 1, "captured once, when the band appeared — not at the press");
  assert.deepEqual(h.drawn, [{ x: 0.1961, y: 0.1263, w: 0.8039, h: 0.8737 }], "the region from the press to the picture's far corner: the release beyond it reached the overlay through capture");
  assert.equal(click.target, h.overlay, "the click went to the capture target");
  assert.equal(click.defaultPrevented, true, "and was swallowed there: a drag is not an activation");
  assert.deepEqual(h.opened, [], "the card did not open on a drag");
  assert.equal(h.overlay.querySelector(".fc-draw"), null, "the band left with the release");
  assert.equal(doc.captured, null);
  h.teardown();
});

test("a rectangle press whose release landed elsewhere: the next move with the button up ends it, and no band trails the pointer", async () => {
  const h = await layerOver("pdf");
  h.layer.setActive(true);
  // the press, then the pointer is off the picture in one move; the release lands on the rest of the viewer
  h.rect.dispatch("pointerdown", { clientX: 160, clientY: 250, pointerId: 1, button: 0, buttons: 1 });
  h.outside.dispatch("pointerup", { clientX: 500, clientY: 700, pointerId: 1, button: 0, buttons: 0 });
  assert.equal(doc.captures, 0);
  // the pointer comes back over the picture with no button held
  h.overlay.dispatch("pointermove", { clientX: 300, clientY: 500, pointerId: 1, buttons: 0 });
  assert.equal(h.overlay.querySelector(".fc-draw"), null, "no band: the press is over");
  assert.equal(doc.captures, 0, "and nothing was captured for it");
  h.overlay.dispatch("pointermove", { clientX: 320, clientY: 520, pointerId: 1, buttons: 0 });
  assert.equal(h.overlay.querySelector(".fc-draw"), null);
  assert.equal(h.drawn.length, 0);
  // the next press works as ever
  press(h.overlay, [130, 230], [{ at: [230, 290], over: h.overlay }], { at: [230, 290], over: h.overlay });
  assert.equal(h.drawn.length, 1, "a fresh drag draws");
  h.teardown();
});

test("with the overlay disarmed (the panel closed, or a coarse pointer), a rectangle press is the browser's: no capture, its default stands, the click still opens the card", async () => {
  const h = await layerOver("pdf");
  h.layer.setActive(false);
  const { down, click } = press(h.rect, [160, 250], []);
  assert.equal(doc.captures, 0);
  assert.equal(down.defaultPrevented, false);
  assert.equal(click.target, h.rect);
  assert.deepEqual(h.opened, [ID]);
  assert.equal(doc.activeElement, h.rect, "focused by the mousedown itself");
  h.teardown();
});
