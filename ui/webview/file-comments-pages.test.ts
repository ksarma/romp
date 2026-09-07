// Region comments on a PDF's pages across the events Slice 4 added (plans/file-review.md, Slice 4; contract F4),
// driven end to end through a DOM stand-in — the file-comments-regions.test.ts idiom, with the focus model from
// file-comments-review-fixes.test.ts (focus() lands on a focusable element; detaching the focused node drops the
// focus to the body, the browser's fixup rule), because a PDF repaints its overlays far more often than an image
// does: the chunk fires onPage after every page draw, every redraw on return, every width change.
//   • a region whose page the regenerated document no longer has: stale, no rectangle, and Re-place STILL offered —
//     the tag names Re-place as the remedy, and a PDF re-place may land on any page;
//   • a pending region composer re-found by page number after a reload hands back new canvases;
//   • keyboard focus on a rectangle kept across a page draw (the node stays: a repaint updates it in place), and
//     following the comment's rectangle when a paint pass remakes it on another page.
// Synthetic fixtures only: the notes-api world, placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx } from "./file-view";
import type { Status, StoreComment } from "./file-comments-model";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");

// ── the DOM stand-in ───────────────────────────────────────────────────────────────────────────────
type Rect = { left: number; top: number; right: number; bottom: number; width: number; height: number };
const rectOf = (left: number, top: number, width: number, height: number): Rect => ({ left, top, width, height, right: left + width, bottom: top + height });
const ZERO = rectOf(0, 0, 0, 0);
class Doc {
  body: E;
  hidden = false;
  /** the focus model: what holds the keyboard; the body when nothing does */
  activeElement: E | null = null;
  /** the last focus() that took: the element and the options it was given (a refocus must ask for no scroll) */
  lastFocus: { el: E; opts: unknown } | null = null;
  listeners = new Map<string, Array<(ev: unknown) => void>>();
  constructor() { this.body = new E(this, "BODY"); this.activeElement = this.body; }
  createElement(tag: string): E { return new E(this, tag.toUpperCase()); }
  createTextNode(s: string): T { return new T(this, s); }
  getElementById(): null { return null; }
  addEventListener(type: string, fn: (ev: unknown) => void): void { (this.listeners.get(type) || this.listeners.set(type, []).get(type)!).push(fn); }
  removeEventListener(type: string, fn: (ev: unknown) => void): void { const l = this.listeners.get(type); if (l) l.splice(l.indexOf(fn), 1); }
  fire(type: string, target: N): void { for (const fn of this.listeners.get(type) || []) fn({ type, target }); }
}
class N {
  nodeType = 0;
  parentNode: N | null = null;
  childNodes: N[] = [];
  constructor(public ownerDocument: Doc) {}
  get parentElement(): E | null { return this.parentNode instanceof E ? this.parentNode : null; }
  get firstChild(): N | null { return this.childNodes[0] || null; }
  get textContent(): string { return this.nodeType === 3 ? (this as unknown as T).data : this.childNodes.map((c) => c.textContent).join(""); }
  set textContent(v: string) {
    for (const c of this.childNodes.slice()) (this as unknown as E).detach(c);
    this.childNodes = v === "" ? [] : [this.ownerDocument.createTextNode(v)];
    for (const c of this.childNodes) c.parentNode = this;
  }
  contains(n: N | null): boolean { for (let x: N | null = n; x; x = x.parentNode) if (x === this) return true; return false; }
  remove(): void { if (this.parentNode) (this.parentNode as E).removeChild(this); }
}
class T extends N {
  nodeType = 3;
  constructor(doc: Doc, public data: string) { super(doc); }
  get length(): number { return this.data.length; }
  splitText(offset: number): T {
    const tail = new T(this.ownerDocument, this.data.slice(offset));
    this.data = this.data.slice(0, offset);
    const p = this.parentNode as E | null;
    if (p) { const i = p.childNodes.indexOf(this); p.childNodes.splice(i + 1, 0, tail); tail.parentNode = p; }
    return tail;
  }
}
type Init = { key?: string; clientX?: number; clientY?: number; pointerId?: number; button?: number };
type Ev = Init & { type: string; target: N; currentTarget: N | null; defaultPrevented: boolean; preventDefault(): void; stopPropagation(): void };
const kebab = (k: string | symbol): string => String(k).replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
type Compound = { tag: string | null; classes: string[]; attrs: Array<[string, string | null]> };
function parseSelector(sel: string): Compound[] {
  return sel.split(",").map((part) => {
    const s = part.trim();
    const out: Compound = { tag: null, classes: [], attrs: [] };
    const re = /^([a-zA-Z][\w-]*)|\.([\w-]+)|\[([\w-]+)(?:="([^"]*)")?\]/g;
    let m: RegExpExecArray | null;
    while ((m = re.exec(s))) {
      if (m[1]) out.tag = m[1].toUpperCase();
      else if (m[2]) out.classes.push(m[2]);
      else out.attrs.push([m[3], m[4] ?? null]);
      if (re.lastIndex === s.length) break;
    }
    return out;
  });
}
/** What a canvas was asked to draw: drawImage's arguments, in order. */
const drawn: unknown[][] = [];
class E extends N {
  nodeType = 1;
  attrs = new Map<string, string>();
  listeners = new Map<string, Array<(ev: Ev) => void>>();
  hidden = false; title = ""; type = ""; disabled = false; placeholder = ""; value = ""; checked = false; offsetWidth = 0; readOnly = false;
  width = 0; height = 0;                              // a canvas
  naturalWidth = 0; naturalHeight = 0; complete: boolean | undefined = undefined;   // a picture
  rect: Rect | null = null;                          // the client rect a test gives the element
  scrolled = 0;
  style: Record<string, string> = {};
  dataset: Record<string, string>;
  classList = {
    add: (...c: string[]) => this.setClasses([...this.classes(), ...c]),
    remove: (...c: string[]) => this.setClasses(this.classes().filter((x) => !c.includes(x))),
    toggle: (c: string, on?: boolean) => { if (on === undefined ? !this.classes().includes(c) : on) this.classList.add(c); else this.classList.remove(c); },
    contains: (c: string) => this.classes().includes(c),
  };
  constructor(doc: Doc, public tagName: string) {
    super(doc);
    this.dataset = new Proxy({} as Record<string, string>, {
      get: (_t, k) => (typeof k === "string" ? this.attrs.get("data-" + kebab(k)) : undefined),
      set: (_t, k, v) => { this.attrs.set("data-" + kebab(k), String(v)); return true; },
      deleteProperty: (_t, k) => { this.attrs.delete("data-" + kebab(k)); return true; },
      has: (_t, k) => this.attrs.has("data-" + kebab(k)),
    });
  }
  /** As the browser has it: a tabindex attribute, else 0 for a button or input, else -1 (not focusable). */
  get tabIndex(): number { return this.attrs.has("tabindex") ? Number(this.attrs.get("tabindex")) : (this.tagName === "BUTTON" || this.tagName === "INPUT" ? 0 : -1); }
  set tabIndex(v: number) { this.attrs.set("tabindex", String(v)); }
  private classes(): string[] { return (this.attrs.get("class") || "").split(/\s+/).filter(Boolean); }
  private setClasses(c: string[]): void { this.attrs.set("class", [...new Set(c)].join(" ")); }
  get className(): string { return this.attrs.get("class") || ""; }
  set className(v: string) { this.attrs.set("class", v); }
  set innerHTML(html: string) { this.replaceChildren(...parseHTML(this.ownerDocument, html)); }
  getAttribute(n: string): string | null { return this.attrs.has(n) ? (this.attrs.get(n) as string) : null; }
  setAttribute(n: string, v: string): void { this.attrs.set(n, v); }
  removeAttribute(n: string): void { this.attrs.delete(n); }
  /** A node leaves its parent; if it held the focus (itself or a descendant), the focus fixup rule moves it to the body. */
  detach(n: N): void {
    const i = this.childNodes.indexOf(n); if (i >= 0) this.childNodes.splice(i, 1); n.parentNode = null;
    const doc = this.ownerDocument;
    if (n instanceof E && doc.activeElement && n.contains(doc.activeElement)) doc.activeElement = doc.body;
  }
  removeChild(n: N): N { this.detach(n); return n; }
  appendChild<X extends N>(n: X): X { if (n.parentNode) (n.parentNode as E).detach(n); this.childNodes.push(n); n.parentNode = this; return n; }
  insertBefore(n: N, ref: N | null): N {
    if (!ref) return this.appendChild(n);
    if (n.parentNode) (n.parentNode as E).detach(n);
    const i = this.childNodes.indexOf(ref);
    this.childNodes.splice(i, 0, n); n.parentNode = this; return n;
  }
  replaceChildren(...c: N[]): void { for (const x of this.childNodes.slice()) this.detach(x); for (const x of c) this.appendChild(x); }
  normalize(): void {
    const out: N[] = [];
    for (const c of this.childNodes) {
      const prev = out[out.length - 1];
      if (c instanceof T && prev instanceof T) { prev.data += c.data; c.parentNode = null; }
      else if (c instanceof T && c.data === "") c.parentNode = null;
      else out.push(c);
    }
    this.childNodes = out;
  }
  matches(sel: string): boolean {
    return parseSelector(sel).some((c) => (c.tag === null || c.tag === this.tagName)
      && c.classes.every((k) => this.classList.contains(k))
      && c.attrs.every(([a, v]) => this.attrs.has(a) && (v === null || this.attrs.get(a) === v)));
  }
  closest(sel: string): E | null { for (let x: N | null = this; x; x = x.parentNode) if (x instanceof E && x.matches(sel)) return x; return null; }
  querySelectorAll(sel: string): E[] {
    const out: E[] = [];
    const chains = sel.split(",").map((g) => g.trim().split(/\s+/));
    const fits = (el: E, chain: string[]): boolean => {
      if (!el.matches(chain[chain.length - 1])) return false;
      let k = chain.length - 2;
      for (let a: N | null = el.parentNode; a && k >= 0 && a !== this.parentNode; a = a.parentNode) if (a instanceof E && a.matches(chain[k])) k--;
      return k < 0;
    };
    const visit = (n: N) => { for (const c of n.childNodes) { if (c instanceof E) { if (chains.some((ch) => fits(c, ch))) out.push(c); visit(c); } } };
    visit(this);
    return out;
  }
  querySelector(sel: string): E | null { return this.querySelectorAll(sel)[0] || null; }
  addEventListener(type: string, fn: (ev: Ev) => void): void { (this.listeners.get(type) || this.listeners.set(type, []).get(type)!).push(fn); }
  removeEventListener(type: string, fn: (ev: Ev) => void): void { const l = this.listeners.get(type); if (l) l.splice(l.indexOf(fn), 1); }
  /** Dispatch with bubbling: every ancestor's listeners run until one stops propagation. */
  dispatch(type: string, init: Init = {}): Ev {
    let stopped = false;
    const ev: Ev = { ...init, type, target: this, currentTarget: null, defaultPrevented: false,
      preventDefault() { this.defaultPrevented = true; }, stopPropagation() { stopped = true; } };
    for (let n: N | null = this; n && !stopped; n = n.parentNode) {
      if (!(n instanceof E)) continue;
      ev.currentTarget = n;
      for (const fn of [...(n.listeners.get(type) || [])]) fn(ev);
    }
    return ev;
  }
  click(): void { this.dispatch("click"); }
  /** The rect a test gave the element; a wrapper hugs its picture (the sheet's inline-block around a block img). */
  getBoundingClientRect(): Rect {
    if (this.rect) return this.rect;
    if (this.classList.contains("fc-imgwrap")) { const img = this.childNodes.find((c) => c instanceof E && c.tagName === "IMG") as E | undefined; return img ? img.getBoundingClientRect() : ZERO; }
    return ZERO;
  }
  setPointerCapture(): void { /* inert */ }
  releasePointerCapture(): void { /* inert */ }
  getContext(): { drawImage(...a: unknown[]): void } | null {
    return this.tagName === "CANVAS" ? { drawImage: (...a: unknown[]) => { drawn.push(a); } } : null;
  }
  scrollIntoView(): void { this.scrolled++; }
  /** Focus lands only on a focusable, enabled element — a div with no tabindex ignores focus(), as the browser does. */
  focus(opts?: unknown): void { if (this.tabIndex >= 0 && !this.disabled) { this.ownerDocument.activeElement = this; this.ownerDocument.lastFocus = { el: this, opts }; } }
  blur(): void { if (this.ownerDocument.activeElement === this) this.ownerDocument.activeElement = this.ownerDocument.body; }
}
const VOID = new Set(["br", "hr", "img", "input", "meta", "link", "area", "base", "col", "embed", "source", "track", "wbr"]);
const NAMED: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " " };
function decodeEntities(s: string): string {
  return s.replace(/&(#x[0-9a-fA-F]+|#\d+|[a-zA-Z]+);/g, (m, e: string) => {
    if (e[0] === "#") return String.fromCodePoint(parseInt(e[1] === "x" || e[1] === "X" ? e.slice(2) : e.slice(1), e[1] === "x" || e[1] === "X" ? 16 : 10));
    return e in NAMED ? NAMED[e] : m;
  });
}
function parseHTML(doc: Doc, html: string): N[] {
  html = html.replace(/\r\n?/g, "\n");
  const root = doc.createElement("#fragment");
  const stack: E[] = [root];
  let i = 0;
  const top = () => stack[stack.length - 1];
  while (i < html.length) {
    if (html[i] === "<") {
      if (html.startsWith("<!--", i)) { const e = html.indexOf("-->", i); i = e < 0 ? html.length : e + 3; continue; }
      if (html[i + 1] === "/") {
        const e = html.indexOf(">", i);
        const name = html.slice(i + 2, e).trim().toUpperCase();
        for (let k = stack.length - 1; k > 0; k--) { if (stack[k].tagName === name) { stack.length = k; break; } }
        i = e + 1; continue;
      }
      const m = /^<([a-zA-Z][\w:-]*)((?:\s+[^\s"'>\/=]+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'=<>`]+))?)*)\s*(\/?)>/.exec(html.slice(i));
      if (!m) { top().appendChild(doc.createTextNode("<")); i++; continue; }
      const el = doc.createElement(m[1]);
      const attrRe = /([^\s"'>\/=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?/g;
      let a: RegExpExecArray | null;
      while ((a = attrRe.exec(m[2]))) el.setAttribute(a[1], decodeEntities(a[2] ?? a[3] ?? a[4] ?? ""));
      top().appendChild(el);
      i += m[0].length;
      if (!m[3] && !VOID.has(m[1].toLowerCase())) {
        stack.push(el);
        if (m[1].toLowerCase() === "pre" && html[i] === "\n") i++;
      }
      continue;
    }
    let e = html.indexOf("<", i);
    if (e < 0) e = html.length;
    top().appendChild(doc.createTextNode(decodeEntities(html.slice(i, e))));
    i = e;
  }
  return root.childNodes.slice();
}

// ── globals the modules reach for, installed before they are imported ──────────────────────────────
const doc = new Doc();
const win: any = new EventTarget();
win.parent = win;
win.innerWidth = 1200; win.innerHeight = 800;
win.devicePixelRatio = 1;
win.getSelection = () => ({ isCollapsed: true, rangeCount: 0, toString: () => "" });
/** The primary pointer a test claims: null leaves matchMedia absent (a desktop without it); true is a finger. */
let coarse: boolean | null = null;
win.matchMedia = (q: string) => { if (coarse === null) throw new TypeError("matchMedia is not a function"); return { matches: q === "(pointer: coarse)" && coarse }; };
(globalThis as any).window = win;
(globalThis as any).document = doc;
(globalThis as any).fetch = async () => ({ status: 404, headers: { get: () => null }, json: async () => [] });
const realSetInterval = globalThis.setInterval;
(globalThis as any).setInterval = (fn: () => void, ms: number) => { const t = realSetInterval(fn, ms); (t as any).unref?.(); return t; };
const tick = () => new Promise<void>((r) => setImmediate(r));

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const PDF = "/repo/notes-api/docs/deck.pdf";
const T0 = 1757145600000;
const ID = T0 + "-0";
const H1 = "1111111111111111111111111111111111111111111111111111111111111111";
const H2 = "2222222222222222222222222222222222222222222222222222222222222222";
// the PDF's pages: US-letter pages drawn at 306×396 CSS px (the 612×792 backing store at half size), stacked 20px
// apart from (100, 200); a drag from (150, 240) to (250, 300) over page 1 is REGION, and from (150, 656) to
// (250, 716) over page 2 is R2
const PAGE_RECTS = [rectOf(100, 200, 306, 396), rectOf(100, 616, 306, 396)];
const REGION = { x: 0.1667, y: 0.2, w: 0.3333, h: 0.3 };
const R2 = { x: 0.1634, y: 0.101, w: 0.3268, h: 0.1515 };
const pageComment = (page: number, over: Partial<StoreComment> = {}, target: Record<string, unknown> = {}): StoreComment => ({
  id: ID, author: "you", ts: T0, body: "Crop the header.", replies: [], resolved: false,
  target: { kind: "pdf", page, region: REGION, hash: H1, ...target } as StoreComment["target"], ...over,
});
function pdfStatus(over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: "/repo/notes-api", storePath: "/repo/notes-api/.trackchanges/docs%2Fdeck.pdf.json",
    trackedBy: null, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: null, configMtimeNs: null,
    store: null, hunks: [], log: [], unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null },
    fileHash: H1,
    ...over,
  };
}
const withStore = (comments: StoreComment[]): Partial<Status> => ({
  storeMtimeNs: "1757145600000000002", store: { v: 3, path: "docs/deck.pdf", suggestions: [], comments },
  unsent: { comments: comments.map((c) => c.id), replies: [], accepted: 0, rejected: 0, watermark: null },
});

// ── the harness ────────────────────────────────────────────────────────────────────────────────────
type Posted = Record<string, any>;
/** A mounted panel over a PDF body the chunk drew (`.fileview-pdfhost > .fileview-pdf > .fileview-pdf-page[data-page] >
 *  canvas.fileview-pdf-canvas`, one shell per page as the chunk builds them), inside the viewer's body row. `remount`
 *  is what a reload does to the pages (showPdfPages: dropPdf, a fresh host, new shells and canvases); `repaint` fires
 *  the seam's onRendered hooks, as fireRendered does after every page the chunk draws (its onPage). */
async function harness(over: Partial<FileViewActionCtx> = {}) {
  const fc = await import("./file-comments");
  const main = doc.createElement("div"); main.className = "fileview-main";
  const body = doc.createElement("div"); body.className = "fileview-body"; main.appendChild(body);
  let media: E | null = null;
  const pages: E[] = [];
  const mount = (rects: Rect[]): E[] => {
    const host = doc.createElement("div"); host.className = "fileview-pdfhost";
    const pdf = doc.createElement("div"); pdf.className = "fileview-pdf";
    const out: E[] = [];
    rects.forEach((rect, i) => {
      const w = doc.createElement("div"); w.className = "fileview-pdf-page"; w.dataset.page = String(i + 1); w.style.position = "relative"; w.rect = rect;
      const c = doc.createElement("canvas"); c.className = "fileview-pdf-canvas"; c.dataset.page = String(i + 1); c.rect = rect; c.width = 612; c.height = 792;
      w.appendChild(c); pdf.appendChild(w); out.push(w);
    });
    host.appendChild(pdf); body.appendChild(host);
    media = pdf; pages.splice(0, pages.length, ...out);
    return out;
  };
  mount(PAGE_RECTS);
  const posted: Posted[] = [];
  const closers: Array<() => void> = [];
  const saved: Array<(info: { mtimeNs: string; logged: boolean }) => void> = [];
  const rendered: Array<() => void> = [];
  let aside: E | null = null;
  const noop = () => { /* inert */ };
  const ctx: FileViewActionCtx = {
    path: PDF, sid: SID, todoId: null,
    body: () => body as unknown as HTMLElement,
    mode: () => "media",
    text: () => null,
    mtimeNs: () => "1757145600000000001",
    media: () => "pdf",
    mediaElement: () => media as unknown as HTMLElement | null, renderedImages: () => [],
    pdfPages: () => pages as unknown as HTMLElement[],
    identity: () => ({ name: "api", color: null }),
    onRendered: (cb) => { rendered.push(cb); }, onSelection: noop, onSaved: (cb) => { saved.push(cb); }, onClose: (cb) => { closers.push(cb); },
    post: (m) => { posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: noop,
    aside: (el) => { if (el) { aside = el as unknown as E; main.appendChild(aside); } else if (aside) { aside.remove(); aside = null; } },
    setMode: noop, scrollToOffset: noop, reload: noop,
    ...over,
  };
  const unit = fc.fileCommentsAction.mount(ctx) as unknown as E;
  const button = unit.childNodes[0] as E;
  const last = (): Posted => posted[posted.length - 1];
  const reply = async (data: Record<string, unknown>) => { win.dispatchEvent(new MessageEvent("message", { data })); await tick(); await tick(); };
  return {
    fc, main, body, unit, button, posted, saved, rendered, last, pages,
    ok: (o: Partial<Status> = {}) => reply({ type: "fileCommentsResult", reqId: last().reqId, ...pdfStatus(o) }),
    q: (sel: string) => main.querySelector(sel),
    qa: (sel: string) => main.querySelectorAll(sel),
    click: (sel: string) => { const e = main.querySelector(sel); assert.ok(e, "a control " + sel); e!.dispatch("click"); },
    /** A drag on an overlay: press, move, release, then the click a browser synthesizes after it. */
    drag: (overlay: E, from: [number, number], to: [number, number]) => {
      overlay.dispatch("pointerdown", { clientX: from[0], clientY: from[1], pointerId: 7, button: 0 });
      overlay.dispatch("pointermove", { clientX: to[0], clientY: to[1], pointerId: 7 });
      overlay.dispatch("pointerup", { clientX: to[0], clientY: to[1], pointerId: 7 });
      return overlay.dispatch("click");
    },
    /** Open the panel: the button, then the status it re-asks. */
    open: async (o: Partial<Status> = {}) => { button.dispatch("click"); await reply({ type: "fileCommentsResult", reqId: last().reqId, ...pdfStatus(o) }); },
    /** A fresh status the way the poll or a save brings one: the onSaved hook re-asks, the reply lands. */
    restatus: async (o: Partial<Status> = {}) => { saved[0]({ mtimeNs: "1757145600000000001", logged: true }); await tick(); await reply({ type: "fileCommentsResult", reqId: last().reqId, ...pdfStatus(o) }); },
    /** The pages redrawn from scratch, as a reload does: the old host leaves the body, a new one with fresh shells and canvases takes its place. */
    remount: (rects: Rect[] = PAGE_RECTS): E[] => { body.replaceChildren(); return mount(rects); },
    /** The seam's onRendered, fired as after every page draw (fireRendered from the chunk's onPage). */
    repaint: () => { for (const cb of rendered) cb(); },
    overlays: () => main.querySelectorAll(".fileview-pdf-page .fc-overlay"),
    head: () => main.querySelector('.fc-card[data-id="' + ID + '"] .fc-card-head')!,
    input: () => main.querySelector("input.fc-input")!,
    dispose: () => { for (const cb of closers) cb(); },
  };
}

// ── a page the regenerated PDF no longer has ───────────────────────────────────────────────────────

test("a region on page 3 of a PDF regenerated with two pages: stale (whatever the hashes say), no rectangle, and Re-place still offered — the tag names it as the remedy, and the next drag on any page moves the comment there", async () => {
  drawn.length = 0;
  const h = await harness();
  const c3 = pageComment(3);
  await h.ok({ ...withStore([c3]), fileHash: H2 });
  await h.open({ ...withStore([c3]), fileHash: H2 });
  const overlays = h.overlays();
  assert.equal(overlays.length, 2, "one overlay per page the document has");
  assert.equal(h.q(".fc-region"), null, "no page 3 to paint the rectangle on");
  const ref = h.head().querySelector(".fc-ref")!;
  assert.equal(ref.textContent, "the region at 0.17, 0.20, 0.33, 0.30 of page 3");
  assert.equal(ref.getAttribute("data-act"), null, "nothing in view to scroll to");
  const tag = () => h.head().querySelector(".fc-tag")!;
  assert.equal(tag().textContent, "stale");
  assert.equal(tag().title, "The PDF changed after this region was drawn and no longer has page 3. Re-place it on a page it has, or resolve it.");
  await h.restatus({ ...withStore([c3]), fileHash: null });
  assert.equal(tag().textContent, "stale", "a host with no hash cannot make a vanished page unknown: the page is not there to be current on");
  await h.restatus({ ...withStore([c3]), fileHash: H2 });
  h.click('.fc-card[data-id="' + ID + '"] .fc-card-head');
  const open = h.q('.fc-card.open[data-id="' + ID + '"]')!;
  assert.equal(open.querySelector("canvas.fc-crop"), null, "no page to crop");
  assert.deepEqual(open.querySelectorAll(".fc-actions button").map((b) => b.textContent), ["Reply", "Resolve", "Re-place"], "Resolve is not the only way out");
  const rp = open.querySelector('[data-act="fcreplace"]')!;
  assert.equal(rp.title, "The PDF no longer has this page: draw the region again on a page it has");
  h.click('.fc-card.open [data-act="fcreplace"]');
  assert.equal(h.q(".fc-composer")!.hidden, false);
  assert.equal(h.q(".fc-composer-ref .fc-note")!.textContent,
    "Drag the comment's new place on a page (now the region at 0.17, 0.20, 0.33, 0.30 of page 3, a page the PDF no longer has). Cancel keeps it where it is.");
  assert.ok(overlays.every((o) => !o.classList.contains("fc-replacing")), "no page is the comment's own, so no page wears the cue: the note carries it");
  h.drag(overlays[1], [150, 656], [250, 716]);
  await tick();
  assert.equal(h.last().verb, "retarget");
  assert.deepEqual(h.last().args, { commentId: ID, target: { kind: "pdf", region: R2, page: 2 } }, "the new page rides in the target");
  const moved = pageComment(2, {}, { region: R2, hash: H2 });
  await h.ok({ ...withStore([moved]), fileHash: H2 });
  assert.equal(h.q(".fc-composer")!.hidden, true);
  assert.ok(overlays[1].querySelector('.fc-region[data-id="' + ID + '"]'), "the rectangle now on page 2");
  assert.equal(h.head().querySelector(".fc-tag"), null, "current again");
  assert.equal(h.head().querySelector(".fc-ref")!.textContent, "the region at 0.16, 0.10, 0.33, 0.15 of page 2");
  h.dispose();
});

test("controls: a vanished page's card offers no Re-place where nothing could take the drag — a coarse pointer, or no page mounted (the frame fallback, which also knows nothing of the pages)", async () => {
  const c3 = pageComment(3);
  coarse = true;
  try {
    const h = await harness();
    await h.ok({ ...withStore([c3]), fileHash: H2 });
    await h.open({ ...withStore([c3]), fileHash: H2 });
    h.click('.fc-card[data-id="' + ID + '"] .fc-card-head');
    assert.equal(h.q('.fc-card.open [data-act="fcreplace"]'), null, "a finger draws nothing");
    assert.match(h.q(".fc-card.open .fc-tag")!.title, /no longer has page 3/, "the tag still says which page went");
    h.dispose();
  } finally { coarse = null; }
  const h = await harness({ pdfPages: () => [], mediaElement: () => null });
  await h.ok({ ...withStore([c3]), fileHash: H2 });
  await h.open({ ...withStore([c3]), fileHash: H2 });
  assert.equal(h.overlays().length, 0, "no pages: no overlays");
  h.click('.fc-card[data-id="' + ID + '"] .fc-card-head');
  assert.equal(h.q('.fc-card.open [data-act="fcreplace"]'), null);
  assert.equal(h.q(".fc-card.open .fc-tag")!.title, "The PDF changed after this region was drawn, so it may no longer mark the right place. Resolve it; re-placing it needs its page drawn in the viewer.", "nothing is known about the pages: the plain stale tag, and no Re-place to name");
  h.dispose();
});

// ── a pending region across a reload of the pages ──────────────────────────────────────────────────

test("a pending region drawn on page 2 survives the pages being redrawn: the composer re-finds page 2 by its number on the new canvases, the crop is cut from the new page, and Enter still sends page 2", async () => {
  drawn.length = 0;
  const h = await harness();
  await h.ok();
  await h.open();
  const before = h.overlays();
  h.drag(before[1], [150, 656], [250, 716]);
  assert.ok(before[1].querySelector(".fc-region-pending"), "the pending mark on page 2");
  h.input().value = "Crop the header.";
  // the session regenerated the PDF: the poll's reload re-renders the pages, and the chunk hands back NEW canvases
  const fresh = h.remount();
  drawn.length = 0;
  h.repaint();
  const after = h.overlays();
  assert.equal(after.length, 2, "overlays on the new pages");
  assert.notEqual(after[1], before[1], "…new ones: the old wrappers left with the old host");
  assert.ok(after[1].querySelector(".fc-region-pending"), "the pending mark re-found on the new page 2");
  assert.equal(after[0].querySelector(".fc-region-pending"), null, "and not on page 1");
  assert.equal(h.q(".fc-composer")!.hidden, false, "the composer stays open");
  assert.equal(h.q(".fc-composer-ref .fc-note")!.textContent, "On the region at 0.16, 0.10, 0.33, 0.15 of page 2");
  assert.equal(drawn[drawn.length - 1][0], fresh[1].querySelector("canvas"), "the composer's crop is cut from the NEW page 2 canvas");
  assert.equal(h.input().value, "Crop the header.", "the words typed so far stay");
  h.input().dispatch("keydown", { key: "Enter" });
  await tick();
  assert.equal(h.last().verb, "comment");
  assert.deepEqual(h.last().args, { note: "Crop the header.", target: { kind: "pdf", region: R2, page: 2 } }, "the wire target and the mark agree on the page");
  h.dispose();
});

// ── keyboard focus on a rectangle across a page draw ───────────────────────────────────────────────

test("keyboard focus on a rectangle survives a page draw: the rectangle is the same node, still on its overlay and still focused, and Enter opens its card; a rectangle remade on another page (the comment moved) takes the keyboard with it, without a scroll; a focus elsewhere is left alone", async () => {
  drawn.length = 0;
  const h = await harness();
  const c1 = pageComment(1);
  await h.ok(withStore([c1]));
  await h.open(withStore([c1]));
  const rect = () => h.q('.fc-region[data-id="' + ID + '"]')!;
  const r0 = rect();
  assert.equal(r0.tabIndex, 0, "a Tab stop");
  assert.equal(r0.parentNode, h.overlays()[0], "on page 1's overlay");
  r0.focus();
  assert.equal(doc.activeElement, r0, "Tab reached the rectangle");
  doc.lastFocus = null;
  h.repaint();                                          // the chunk drew a page (onPage → fireRendered): every overlay's rectangles are brought up to date IN PLACE
  assert.equal(rect(), r0, "the same node: a repaint updates the rectangle it has, never removes and remakes it (a remade node would take a held click with it)");
  assert.equal(r0.parentNode, h.overlays()[0], "still on its overlay");
  assert.equal(h.qa('.fc-region[data-id="' + ID + '"]').length, 1, "one rectangle for the comment");
  assert.equal(doc.activeElement, r0, "…and it holds the keyboard, which never fell to the body");
  assert.equal(doc.lastFocus, null, "so nothing had to be refocused");
  doc.activeElement!.dispatch("keydown", { key: "Enter" });
  assert.ok(h.q('.fc-card.open[data-id="' + ID + '"]'), "Enter opens the card, as before the draw");
  // the comment moved to page 2 (a Re-place, the session's or another's): page 1's pass removes its rectangle, which
  // drops the keyboard to the body; page 2's pass makes one; the keyboard is put back on that one — the mend that
  // remains for a rectangle a pass does remake — and asks for no scroll, so the view is not yanked to page 2
  const moved = pageComment(2, {}, { region: R2 });
  await h.restatus(withStore([moved]));
  assert.equal(r0.parentNode, null, "page 1's rectangle left");
  const r1 = rect();
  assert.notEqual(r1, r0, "a new rectangle…");
  assert.equal(r1.parentNode, h.overlays()[1], "…on page 2's overlay");
  assert.equal(h.qa('.fc-region[data-id="' + ID + '"]').length, 1, "and only there");
  assert.equal(doc.activeElement, r1, "the keyboard followed the comment's rectangle");
  assert.equal(doc.lastFocus!.el, r1);
  assert.deepEqual(doc.lastFocus!.opts, { preventScroll: true }, "a refocus never scrolls");
  h.repaint();
  assert.equal(rect(), r1, "and the next draw keeps that node too");
  assert.equal(doc.activeElement, r1);
  // a redraw while the composer's input holds the keyboard moves nothing: the input is never rebuilt
  h.drag(h.overlays()[1], [150, 656], [250, 716]);
  assert.equal(doc.activeElement, h.input(), "the composer took the keyboard");
  h.repaint();
  assert.equal(doc.activeElement, h.input());
  // nothing focused: a draw focuses nothing
  h.input().blur();
  assert.equal(doc.activeElement, doc.body);
  doc.lastFocus = null;
  h.repaint();
  assert.equal(doc.activeElement, doc.body, "no stray focus");
  assert.equal(doc.lastFocus, null, "nothing was focused by the draw");
  h.dispose();
});

// ── source pins: what the stand-in cannot show ─────────────────────────────────────────────────────

test("source pins: the keep runs before any layer is dropped, the refocus scrolls nothing, and Re-place is gated on the picture OR the vanished page", () => {
  const SRC = web("file-comments.ts");
  assert.match(SRC, /private paintRegions\(\): void \{\n\s*const held = this\.heldMark\(\);/, "the focused mark is read before a layer is dropped or a pass removes a rectangle (a comment moved to another page)");
  assert.match(SRC, /if \(held\) this\.refocusMark\(held\);\n\s*\}\n\s*\/\*\* The overlay for a picture/, "…and refocused after every layer has painted, when the keyboard fell to the body");
  assert.match(SRC, /next\[Math\.min\(Math\.max\(held\.k, 0\), next\.length - 1\)\]\.focus\(\{ preventScroll: true \}\);/, "a page drawing in as it scrolls near must not yank the view back");
  assert.match(SRC, /const replaceOffered = \(!!picture \|\| gone\) && !c\.resolved && this\.drawsRegions\(\);/, "Re-place is gated on the picture OR the vanished page");
  assert.match(SRC, /const gone = this\.pageGone\(c\);\n\s*const regionSt = c\.target \? regionState\(c\.target, this\.status\) : "current";/);
  assert.match(SRC, /const shownGone = gone && !c\.resolved;\n[\s\S]*?if \(shownGone \|\| shownSt === "stale"\) \{/, "a vanished page reads stale whatever the hashes say — unless resolved, when nothing is left to report");
  assert.match(SRC, /\(c\.page \? imgs\.find\(\(i\) => pageOf\(i\) === c\.page\) : imgs\[0\]\)/, "a pending PDF region is re-found by its page number");
});
