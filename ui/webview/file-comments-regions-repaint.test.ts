// The overlay's rectangles across a repaint UNDER A HELD POINTER (plans/file-review.md, Slice 4; ui/CLAUDE.md,
// click-safe). With a PDF the panel's paint pass runs on every page draw, redraw and width change (the chunk's onPage
// → fireRendered → paintAll → paintRegions → RegionLayer.paint), and a press on a rectangle is deliberately not
// captured so the browser's click reaches the rectangle. A paint that removed and remade every rectangle therefore
// detached the pressed one whenever a neighbouring page finished drawing mid-press: mousedown and mouseup on
// different nodes, and no click reached a data-act (2026-09-06). paint() now updates a rectangle in place, keyed by
// the comment it opens, and never re-inserts one that is up. The DOM stand-in is the press test's, plus the browser's
// two rules that make the defect visible: a node removed from the document loses its focus to the body, and a
// synthesized click is dropped when the node the press began on was removed (or moved) before the release, as
// Chromium's mouse event manager does; Firefox retargets it to the nearest common ancestor instead, and nothing on the
// overlay's ancestor chain carries a data-act, so the card stays shut either way. Synthetic fixtures only: the
// notes-api world, placeholder ids.
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
  /** the element holding pointer capture, as the browser tracks it */
  captured: E | null = null;
  captures = 0;
  activeElement: E;
  /** every node taken out of its parent since the last press began: what the browser's click tracking sees */
  removals = new Set<E>();
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
  /** A node leaves its parent: the browser's click tracking sees a removal, and a focused node (or a focused
   *  descendant) loses the keyboard to the body. */
  removeChild(n: E): E {
    const i = this.childNodes.indexOf(n); if (i >= 0) this.childNodes.splice(i, 1); n.parentNode = null;
    const doc = this.ownerDocument; doc.removals.add(n);
    if (n.contains(doc.activeElement)) doc.activeElement = doc.body;
    return n;
  }
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
  dispatch(type: string, init: Init = {}): Ev {
    let stopped = false;
    const ev: Ev = { ...init, type, target: this, currentTarget: null, defaultPrevented: false,
      preventDefault() { this.defaultPrevented = true; }, stopPropagation() { stopped = true; } };
    for (let n: E | null = this; n && !stopped; n = n.parentNode) { ev.currentTarget = n; for (const fn of [...(n.listeners.get(type) || [])]) fn(ev); }
    return ev;
  }
  getBoundingClientRect(): Rect {
    if (this.rect) return this.rect;
    if (this.classList.contains("fc-imgwrap")) { const img = this.childNodes.find((c) => c.tagName === "IMG"); return img ? img.getBoundingClientRect() : ZERO; }
    return ZERO;
  }
  setPointerCapture(): void { this.ownerDocument.captured = this; this.ownerDocument.captures++; }
  releasePointerCapture(): void { if (this.ownerDocument.captured === this) this.ownerDocument.captured = null; }
  focus(): void { if (this.tabIndex >= 0) this.ownerDocument.activeElement = this; }
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
const under = (el: E): E => doc.captured || el;
function common(a: E, b: E): E { for (let x: E | null = a; x; x = x.parentNode) if (x.contains(b)) return x; return doc.body; }
/** A press as the browser delivers it, with `held` run while the button is down (here: the paint pass a page draw
 *  brings). The click the browser synthesizes goes to the capture target held through the release, else to the node
 *  common to where the press began and ended — and is DROPPED when the node the press began on was removed from
 *  the document in between (a re-insertion is a removal too). Returns the events; `click` is null when none fired. */
function press(on: E, from: Pt, held?: () => void, release: { at: Pt; over: E } = { at: from, over: on }) {
  doc.removals.clear();
  const down = on.dispatch("pointerdown", { clientX: from[0], clientY: from[1], pointerId: 1, button: 0, buttons: 1 });
  if (!down.defaultPrevented) { let f: E | null = on; while (f && f.tabIndex < 0) f = f.parentNode; if (f) f.focus(); }
  if (held) held();
  const upOn = under(release.over);
  upOn.dispatch("pointerup", { clientX: release.at[0], clientY: release.at[1], pointerId: 1, button: 0, buttons: 0 });
  if (doc.removals.has(on) || !doc.body.contains(on)) return { down, click: null as Ev | null };
  const click = common(on, upOn).dispatch("click", { clientX: release.at[0], clientY: release.at[1], button: 0 });
  return { down, click: click as Ev | null };
}

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const ID = "1757145600000-0";
const ID2 = "1757145600000-1";
const ID3 = "1757145600000-2";
const REGION = { x: 0.1634, y: 0.101, w: 0.3268, h: 0.1515 };   // page 1's header
const REGION2 = { x: 0.5, y: 0.5, w: 0.25, h: 0.2 };            // a table lower on the page
const REGION3 = { x: 0.05, y: 0.8, w: 0.9, h: 0.1 };            // the footer
type Mark = { id: string; region: typeof REGION; label: string; state: "current" | "stale" | "unknown"; style?: Record<string, string> };
const MARK: Mark = { id: ID, region: REGION, label: "you", state: "current" };
const PAGE_RECT = rectOf(100, 200, 306, 396);                   // a US-letter page at 306×396 CSS px, its canvas 612×792
const IMG_RECT = rectOf(100, 200, 300, 200);                    // a 600×400 figure at half size

/** The same nodes, in the same order — by identity (a node holds its parent, so a deep comparison is not the question). */
function sameNodes(actual: E[], expected: E[], msg: string): void {
  assert.equal(actual.length, expected.length, msg + " (count)");
  for (let i = 0; i < expected.length; i++) assert.equal(actual[i], expected[i], msg + " (node " + i + ")");
}

/** The viewer's body row (the panel's delegate root) with a PDF page or a standalone image, a layer over it, and the
 *  row's delegate routing fcopen — the panel's wiring, without the panel. */
async function layerOver(kind: "pdf" | "image", marks: Mark[] = [MARK]) {
  const { RegionLayer } = await import("./file-comments-regions");
  const { delegate } = await import("./actions");
  doc.captured = null; doc.captures = 0; doc.activeElement = doc.body; doc.removals.clear();
  const row = doc.createElement("div"); row.className = "fileview-main"; doc.body.appendChild(row);
  const body = doc.createElement("div"); body.className = "fileview-body"; row.appendChild(body);
  let picture: E; let anchor: E | null = null;
  if (kind === "pdf") {
    const host = doc.createElement("div"); host.className = "fileview-pdfhost"; body.appendChild(host);
    const pdf = doc.createElement("div"); pdf.className = "fileview-pdf"; host.appendChild(pdf);
    anchor = doc.createElement("div"); anchor.className = "fileview-pdf-page"; anchor.dataset.page = "1"; anchor.rect = PAGE_RECT;
    picture = doc.createElement("canvas"); picture.className = "fileview-pdf-canvas"; picture.dataset.page = "1"; picture.rect = PAGE_RECT; picture.width = 612; picture.height = 792;
    anchor.appendChild(picture); pdf.appendChild(anchor);
  } else {
    picture = doc.createElement("img"); picture.className = "fileview-img"; picture.rect = IMG_RECT; picture.naturalWidth = 600; picture.naturalHeight = 400; picture.complete = true;
    body.appendChild(picture);
  }
  const drawn: Array<{ x: number; y: number; w: number; h: number }> = [];
  let clicks = 0;
  const layer = new RegionLayer(picture as unknown as HTMLCanvasElement, {
    onDraw: (_i, r) => { drawn.push(r); }, onClick: () => { clicks++; },
  }, anchor as unknown as HTMLElement | null);
  const opened: string[] = [];
  delegate(row as unknown as HTMLElement, { fcopen: (x) => { opened.push(x.dataset.id!); } });
  const overlay = layer.overlay as unknown as E;
  const paint = (ms: Mark[] = marks, pending: typeof REGION | null = null, replacing = false) =>
    layer.paint(ms, pending, replacing) as unknown as E[];
  paint();
  const rectFor = (id: string) => overlay.querySelectorAll(".fc-region").find((r) => r.dataset.id === id) || null;
  const rects = () => overlay.querySelectorAll(".fc-region").filter((r) => !r.classList.contains("fc-region-pending"));
  return { layer, overlay, paint, rectFor, rects, drawn, opened, teardown: () => { layer.dispose(); row.remove(); }, get clicks() { return clicks; } };
}

for (const kind of ["pdf", "image"] as const) {
  test("a repaint while a rectangle is pressed (" + kind + "): the rectangle is the same node, still attached and focused, so the release's click lands on it and the card opens", async () => {
    const h = await layerOver(kind);
    h.layer.setActive(true);
    const r0 = h.rectFor(ID)!;
    const { click } = press(r0, [160, 250], () => {
      // page 2 finished drawing (or the width changed) with the button held: the panel's paint pass runs
      const out = h.paint();
      assert.equal(out.length, 1);
      assert.equal(out[0], r0, "the pass hands back the rectangle that was up, not a new one");
    });
    assert.equal(doc.removals.has(r0), false, "the pressed rectangle was never taken out of the overlay (a re-insertion counts)");
    assert.equal(r0.parentNode, h.overlay, "and is still on it");
    assert.equal(h.rectFor(ID), r0, "one rectangle for the comment, the same node");
    assert.ok(click, "so the browser fired the click");
    assert.equal(click!.target, r0, "at the rectangle");
    assert.deepEqual(h.opened, [ID], "and the row's delegate opened its card");
    assert.equal(doc.activeElement, r0, "the rectangle kept the keyboard through the pass");
    assert.equal(h.clicks, 0, "not a picture click");
    assert.equal(h.drawn.length, 0, "nothing drawn");
    h.teardown();
  });
}

test("the contrast the stand-in models: a rectangle removed and remade under the pointer takes the click with it (what every page draw did before)", async () => {
  const h = await layerOver("pdf");
  h.layer.setActive(true);
  const r0 = h.rectFor(ID)!;
  const { click } = press(r0, [160, 250], () => {
    // the old pass, by hand: every child but the band removed and made again
    for (const n of [...h.overlay.childNodes]) h.overlay.removeChild(n);
    h.paint();
  });
  assert.notEqual(h.rectFor(ID), r0, "a different node now answers for the comment");
  assert.equal(click, null, "no click fired");
  assert.deepEqual(h.opened, [], "and the card did not open");
  assert.equal(doc.activeElement, doc.body, "the keyboard fell to the body");
  h.teardown();
});

test("several passes, the marks unchanged: the same nodes every time, one per comment, in the stacking order", async () => {
  const h = await layerOver("pdf", [MARK, { id: ID2, region: REGION2, label: "web", state: "current" }]);
  const before = h.rects();
  assert.equal(before.length, 2);
  doc.removals.clear();
  for (let i = 0; i < 3; i++) h.paint();
  sameNodes(h.rects(), before, "the same two nodes, in the same order");
  assert.equal(doc.removals.size, 0, "nothing was removed or moved");
  assert.deepEqual(h.rects().map((r) => r.dataset.id), [ID2, ID], "largest first (stackOrder): the table's rectangle stands under the header's, which is the smaller");
  h.teardown();
});

test("a mark that changed is updated on its node: place, staleness (class and title), the author chip's label and colour", async () => {
  const h = await layerOver("pdf");
  const r0 = h.rectFor(ID)!;
  assert.equal(r0.classList.contains("fc-stale"), false);
  assert.match(r0.getAttribute("style")!, /left: 16\.34%/);
  h.paint([{ id: ID, region: REGION2, label: "web", state: "stale", style: { "--fc-author": "#123456", "--fc-author-fg": "#ffffff" } }]);
  assert.equal(h.rectFor(ID), r0, "the same node");
  assert.equal(r0.className, "fc-region fc-stale", "now stale");
  assert.equal(r0.title, "Open the comment on this region (the PDF changed after it was drawn)");
  const style = r0.getAttribute("style")!;
  assert.match(style, /left: 50\.00%/, "moved to the new place");
  assert.doesNotMatch(style, /16\.34%/, "and not the old one");
  assert.match(style, /--fc-author: #123456/, "the session's colour");
  const chips = r0.querySelectorAll(".fc-region-chip");
  assert.equal(chips.length, 1, "one chip");
  assert.equal(chips[0].dataset.label, "web", "relabelled");
  assert.equal(chips[0].childNodes.length, 0, "still no text node under the picture");
  h.paint([{ id: ID, region: REGION2, label: "web", state: "unknown" }]);
  assert.equal(h.rectFor(ID), r0);
  assert.equal(r0.className, "fc-region fc-unknown");
  assert.equal(r0.title, "Open the comment on this region (whether the PDF changed could not be checked)");
  assert.doesNotMatch(r0.getAttribute("style")!, /--fc-author/, "the colour left with the mark's style");
  h.paint([MARK]);
  assert.equal(r0.className, "fc-region", "current again");
  assert.equal(r0.title, "Open the comment on this region");
  assert.equal(r0.dataset.act, "fcopen"); assert.equal(r0.tabIndex, 0); assert.equal(r0.getAttribute("role"), "button");
  h.teardown();
});

test("marks that come and go: a new mark's rectangle goes in at its place in the stacking order without moving the ones up; a gone mark's rectangle leaves", async () => {
  // by area the footer (REGION3) is the largest, the table (REGION2) next, the header (REGION) the smallest: the stacking
  // order (stackOrder, largest first) puts them footer, table, header — whatever order the marks arrive in
  const h = await layerOver("pdf", [MARK, { id: ID3, region: REGION3, label: "you", state: "current" }]);
  const r1 = h.rectFor(ID)!, r3 = h.rectFor(ID3)!;
  sameNodes(h.rects(), [r3, r1], "largest first");
  doc.removals.clear();
  // a comment arrives between the two
  h.paint([MARK, { id: ID2, region: REGION2, label: "web", state: "current" }, { id: ID3, region: REGION3, label: "you", state: "current" }]);
  const r2 = h.rectFor(ID2)!;
  sameNodes(h.rects(), [r3, r2, r1], "in the stacking order, the two that were up untouched");
  assert.equal(doc.removals.size, 0);
  // the smallest is resolved
  h.paint([{ id: ID2, region: REGION2, label: "web", state: "current" }, { id: ID3, region: REGION3, label: "you", state: "current" }]);
  sameNodes(h.rects(), [r3, r2], "the two that remain");
  assert.equal(r1.parentNode, null, "its rectangle left");
  sameNodes([...doc.removals], [r1], "and nothing else moved");
  // the comment comes back
  h.paint([MARK, { id: ID2, region: REGION2, label: "web", state: "current" }, { id: ID3, region: REGION3, label: "you", state: "current" }]);
  const r1b = h.rectFor(ID)!;
  assert.notEqual(r1b, r1, "a fresh node for the comment that came back");
  sameNodes(h.rects(), [r3, r2, r1b], "at its place, the others where they were");
  // all gone
  h.paint([]);
  assert.equal(h.rects().length, 0);
  h.teardown();
});

test("the composer's pending region is one node updated in place, removed when the composer closes; the re-place cue toggles on the overlay", async () => {
  const h = await layerOver("pdf");
  const r0 = h.rectFor(ID)!;
  h.paint([MARK], REGION2);
  const p = h.overlay.querySelector(".fc-region-pending")!;
  assert.ok(p, "the pending region");
  assert.match(p.getAttribute("style")!, /left: 50\.00%/);
  assert.equal(p.dataset.act, undefined, "not a control");
  doc.removals.clear();
  h.paint([MARK], REGION3);
  assert.equal(h.overlay.querySelectorAll(".fc-region-pending").length, 1, "still one");
  assert.equal(h.overlay.querySelector(".fc-region-pending"), p, "the same node");
  assert.match(p.getAttribute("style")!, /top: 80\.00%/, "moved");
  assert.equal(doc.removals.size, 0);
  assert.equal(h.rectFor(ID), r0, "the rectangle beside it untouched");
  h.paint([MARK], null, true);
  assert.equal(h.overlay.querySelector(".fc-region-pending"), null, "gone with the composer");
  assert.equal(h.overlay.classList.contains("fc-replacing"), true, "the re-place cue");
  h.paint([MARK], null, false);
  assert.equal(h.overlay.classList.contains("fc-replacing"), false);
  h.teardown();
});

test("a paint pass mid-drag leaves the rubber band alone, and the drag still draws", async () => {
  const h = await layerOver("pdf");
  h.layer.setActive(true);
  h.overlay.dispatch("pointerdown", { clientX: 130, clientY: 230, pointerId: 1, button: 0, buttons: 1 });
  h.overlay.dispatch("pointermove", { clientX: 230, clientY: 330, pointerId: 1, buttons: 1 });
  const band = h.overlay.querySelector(".fc-draw")!;
  assert.ok(band, "the band is up");
  doc.removals.clear();
  h.paint();                                            // a page draw completes during the drag
  assert.equal(h.overlay.querySelector(".fc-draw"), band, "the band stayed");
  assert.equal(doc.removals.size, 0);
  h.overlay.dispatch("pointerup", { clientX: 230, clientY: 330, pointerId: 1, button: 0, buttons: 0 });
  assert.equal(h.drawn.length, 1, "the drag drew its region");
  assert.equal(h.overlay.querySelector(".fc-draw"), null, "the band left with the release");
  h.teardown();
});

test("nothing is ever stacked: a stray child and a second node for the same comment are removed by the pass", async () => {
  const h = await layerOver("pdf");
  const r0 = h.rectFor(ID)!;
  const stray = doc.createElement("div"); stray.className = "fc-something-else"; h.overlay.appendChild(stray);
  const dup = doc.createElement("div"); dup.className = "fc-region"; dup.dataset.id = ID; dup.dataset.act = "fcopen"; h.overlay.appendChild(dup);
  const dupPending = doc.createElement("div"); dupPending.className = "fc-region fc-region-pending"; h.overlay.appendChild(dupPending);
  const out = h.paint([MARK], REGION2);
  sameNodes(out, [r0], "the first node for the comment is the one kept");
  assert.equal(stray.parentNode, null);
  assert.equal(dup.parentNode, null);
  assert.equal(h.rects().length, 1);
  assert.equal(h.overlay.querySelectorAll(".fc-region-pending").length, 1, "one pending region (the one that was up, reused)");
  assert.equal(h.overlay.querySelector(".fc-region-pending"), dupPending);
  h.teardown();
});

test("keyboard focus on a rectangle survives the pass with no mend: the node never left", async () => {
  const h = await layerOver("pdf", [MARK, { id: ID2, region: REGION2, label: "web", state: "current" }]);
  const r2 = h.rectFor(ID2)!;
  r2.focus();
  assert.equal(doc.activeElement, r2);
  h.paint();
  h.paint([{ id: ID2, region: REGION2, label: "web", state: "stale" }, MARK]);   // reordered and restated
  assert.equal(doc.activeElement, r2, "still focused");
  assert.equal(h.rectFor(ID2), r2);
  h.teardown();
});
