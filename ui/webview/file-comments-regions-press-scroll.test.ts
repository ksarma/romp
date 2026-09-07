// A rectangle press must not scroll the viewer (plans/file-review.md, Slices 3 and 4; contract E5). The overlay
// cancels the press's default, and with it the focus the mousedown would have given the rectangle, so it focuses the
// rectangle itself — and a scripted focus() is not a mouse focus: the browser scrolls the element into view unless
// preventScroll is asked for, while a mouse-initiated focus never scrolls. A PDF page or a tall image outgrows the
// scrolling .fileview-body, so a rectangle can straddle its edge, and pressing the visible part of one jumped the body
// by the clipped amount on pointerdown: the content moved under the held pointer, on the first press of every edge
// rectangle (2026-09-06, measured in Chromium). The stand-in here models that part of the browser — focus() scrolls
// the nearest overflow ancestor to reveal the element, focus({ preventScroll: true }) does not, and the mousedown's
// own focus does not — so the test shows the press leaving the view where it was, while the model itself is shown to
// scroll on a bare focus(). Synthetic fixtures only: the notes-api world, placeholder ids.
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
  activeElement: E;
  /** every focus() call the stand-in saw, with the options it was given: what the layer asked the browser for */
  focusCalls: Array<{ el: E; opts: FocusOptions | undefined }> = [];
  constructor() { this.body = new E(this, "BODY"); this.activeElement = this.body; }
  createElement(tag: string): E { return new E(this, tag.toUpperCase()); }
}
const kebab = (k: string | symbol): string => String(k).replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
class E {
  attrs = new Map<string, string>();
  listeners = new Map<string, Array<(ev: Ev) => void>>();
  childNodes: E[] = [];
  parentNode: E | null = null;
  title = ""; tabIndex = -1;
  width = 0; height = 0;                              // a canvas
  naturalWidth = 0; naturalHeight = 0; complete: boolean | undefined = undefined;   // a picture
  /** the element's box in client coordinates, as laid out at scrollTop 0 */
  rect: Rect | null = null;
  /** a scroll container (`overflow: auto`): its scroll position; every descendant's client rect moves up by it */
  scrolls = false; scrollTop = 0;
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
  /** The nearest scroll container above this element, if any. */
  scroller(): E | null { for (let x = this.parentNode; x; x = x.parentNode) if (x.scrolls) return x; return null; }
  /** The rect a test gave the element, moved up by whatever its scroll container has scrolled. */
  getBoundingClientRect(): Rect {
    if (!this.rect) return ZERO;
    const s = this.scroller();
    const dy = s ? s.scrollTop : 0;
    return rectOf(this.rect.left, this.rect.top - dy, this.rect.width, this.rect.height);
  }
  setPointerCapture(): void { /* not reached by a rectangle press; a drag is not what this test presses */ }
  releasePointerCapture(): void { /* likewise */ }
  /** The browser's focus(): a Tab stop takes focus, and — the part this test is about — a SCRIPTED focus scrolls the
   *  element's scroll container until the element is in view, unless preventScroll is asked for. The mousedown's own
   *  focus goes through `mouseFocus` instead, which never scrolls. */
  focus(opts?: FocusOptions): void {
    this.ownerDocument.focusCalls.push({ el: this, opts });
    if (this.tabIndex < 0) return;
    this.ownerDocument.activeElement = this;
    if (opts && opts.preventScroll) return;
    const s = this.scroller();
    if (!s || !s.rect) return;
    const me = this.getBoundingClientRect(), box = s.getBoundingClientRect();
    if (me.bottom > box.bottom) s.scrollTop += me.bottom - box.bottom;        // reveal the clipped bottom
    else if (me.top < box.top) s.scrollTop -= box.top - me.top;              // or the clipped top
  }
  /** The focus a mousedown gives the control under it when its default stands: no scroll, ever. */
  mouseFocus(): void { if (this.tabIndex >= 0) this.ownerDocument.activeElement = this; }
}

// ── globals the module reaches for, installed before it is imported ────────────────────────────────
const doc = new Doc();
const win: any = new EventTarget();
win.devicePixelRatio = 1;
win.matchMedia = () => ({ matches: false });
(globalThis as any).window = win;
(globalThis as any).document = doc;

/** A press that does not move, as the browser delivers it: pointerdown at a point; a mousedown whose default stands
 *  focuses the control under it the mouse way (no scroll); the release; the click where the press began and ended. */
function press(on: E, at: [number, number]) {
  const down = on.dispatch("pointerdown", { clientX: at[0], clientY: at[1], pointerId: 1, button: 0, buttons: 1 });
  if (!down.defaultPrevented) { let f: E | null = on; while (f && f.tabIndex < 0) f = f.parentNode; if (f) f.mouseFocus(); }
  on.dispatch("pointerup", { clientX: at[0], clientY: at[1], pointerId: 1, button: 0, buttons: 0 });
  const click = on.dispatch("click", { clientX: at[0], clientY: at[1], button: 0 });
  return { down, click };
}

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const ID = "1757145600000-0";
// the viewer's body: 600px tall from y=100, the scroll container the PDF's pages sit in
const BODY_RECT = rectOf(0, 100, 500, 600);
// a US-letter page drawn at 306×396 CSS px whose lower part is below the fold: it runs from y=400 to y=796, the body
// ends at y=700
const PAGE_RECT = rectOf(100, 400, 306, 396);
// a region on the page's lower half: 20% down to 90% → y from 479 to 756, so its bottom 56px are clipped by the body
const REGION = { x: 0.2, y: 0.2, w: 0.5, h: 0.7 };
const REGION_RECT = rectOf(100 + 306 * 0.2, 400 + 396 * 0.2, 306 * 0.5, 396 * 0.7);
const CLIPPED = REGION_RECT.bottom - BODY_RECT.bottom;

/** A PDF page in the body with a layer anchored on its wrapper, one rectangle painted straddling the body's bottom
 *  edge, and the row's real delegate routing fcopen — the panel's wiring, without the panel. */
async function edgeRectangle() {
  const { RegionLayer } = await import("./file-comments-regions");
  const { delegate } = await import("./actions");
  doc.activeElement = doc.body; doc.focusCalls = [];
  const row = doc.createElement("div"); row.className = "fileview-main"; doc.body.appendChild(row);
  const body = doc.createElement("div"); body.className = "fileview-body"; body.rect = BODY_RECT; body.scrolls = true; row.appendChild(body);
  const anchor = doc.createElement("div"); anchor.className = "fileview-pdf-page"; anchor.dataset.page = "2"; anchor.rect = PAGE_RECT;
  const canvas = doc.createElement("canvas"); canvas.className = "fileview-pdf-canvas"; canvas.dataset.page = "2"; canvas.rect = PAGE_RECT; canvas.width = 612; canvas.height = 792;
  anchor.appendChild(canvas); body.appendChild(anchor);
  let clicks = 0;
  const layer = new RegionLayer(canvas as unknown as HTMLCanvasElement, { onDraw: () => {}, onClick: () => { clicks++; } }, anchor as unknown as HTMLElement);
  const opened: string[] = [];
  delegate(row as unknown as HTMLElement, { fcopen: (x) => { opened.push(x.dataset.id!); } });
  layer.paint([{ id: ID, region: REGION, label: "you", state: "current" }], null, false);
  const rect = (layer.overlay as unknown as E).querySelector(".fc-region")!;
  assert.ok(rect, "the rectangle painted");
  rect.rect = REGION_RECT;                              // where the sheet's percentages put it, at scrollTop 0
  // the geometry the test is about: the rectangle's top is in view, its bottom is not
  assert.ok(rect.getBoundingClientRect().top < BODY_RECT.bottom && rect.getBoundingClientRect().bottom > BODY_RECT.bottom, "the rectangle straddles the body's bottom edge");
  assert.ok(CLIPPED > 0);
  return { layer, body, rect, opened, get clicks() { return clicks; }, teardown: () => { layer.dispose(); row.remove(); } };
}

test("the stand-in's model: a bare focus() on the edge rectangle scrolls the body by the clipped amount; preventScroll and the mousedown's focus do not", async () => {
  const h = await edgeRectangle();
  h.rect.focus();
  assert.equal(h.body.scrollTop, CLIPPED, "a scripted focus reveals the element: the body scrolled");
  assert.equal(doc.activeElement, h.rect);
  h.body.scrollTop = 0; doc.activeElement = doc.body;
  h.rect.focus({ preventScroll: true });
  assert.equal(h.body.scrollTop, 0, "preventScroll: focused in place");
  assert.equal(doc.activeElement, h.rect);
  doc.activeElement = doc.body;
  h.rect.mouseFocus();
  assert.equal(h.body.scrollTop, 0, "a mouse focus never scrolls");
  assert.equal(doc.activeElement, h.rect);
  h.teardown();
});

test("a press on a rectangle straddling the body's edge while the overlay draws: the rectangle takes focus, the body does not scroll, and the card still opens", async () => {
  const h = await edgeRectangle();
  h.layer.setActive(true);
  const at: [number, number] = [h.rect.getBoundingClientRect().left + 20, h.rect.getBoundingClientRect().top + 20];   // the visible part
  const { down, click } = press(h.rect, at);
  assert.equal(down.defaultPrevented, true, "the press's default is cancelled (no selection behind the overlay), so the layer focuses the rectangle itself");
  assert.equal(doc.activeElement, h.rect, "the rectangle holds focus, as the mousedown would have left it");
  assert.equal(h.body.scrollTop, 0, "and the body did not scroll: the content stays under the held pointer");
  assert.deepEqual(doc.focusCalls.map((c) => [c.el === h.rect, !!(c.opts && c.opts.preventScroll)]), [[true, true]],
    "one focus, on the rectangle, with preventScroll — the scroll a scripted focus adds is not a mouse focus's");
  assert.equal(click.target, h.rect, "the click still lands on the rectangle");
  assert.deepEqual(h.opened, [ID], "and the row's delegate opened its card");
  assert.equal(h.clicks, 0, "not a picture click");
  h.teardown();
});

test("the same press with the overlay disarmed: the mousedown's own focus, no scroll — the armed press must match it", async () => {
  const h = await edgeRectangle();
  h.layer.setActive(false);
  const at: [number, number] = [h.rect.getBoundingClientRect().left + 20, h.rect.getBoundingClientRect().top + 20];
  const { down } = press(h.rect, at);
  assert.equal(down.defaultPrevented, false, "the browser's press");
  assert.equal(doc.activeElement, h.rect, "focused by the mousedown itself");
  assert.equal(h.body.scrollTop, 0, "which never scrolls");
  assert.deepEqual(doc.focusCalls, [], "the layer called nothing");
  assert.deepEqual(h.opened, [ID]);
  h.teardown();
});

test("a repeat press on the rectangle that already holds focus: still no scroll, and it keeps focus", async () => {
  const h = await edgeRectangle();
  h.layer.setActive(true);
  const at: [number, number] = [h.rect.getBoundingClientRect().left + 20, h.rect.getBoundingClientRect().top + 20];
  press(h.rect, at);
  press(h.rect, at);
  assert.equal(h.body.scrollTop, 0);
  assert.equal(doc.activeElement, h.rect);
  assert.deepEqual(h.opened, [ID, ID], "both clicks opened the card");
  assert.ok(doc.focusCalls.every((c) => c.el === h.rect && !!(c.opts && c.opts.preventScroll)), "every focus the layer asked for was in place");
  h.teardown();
});
