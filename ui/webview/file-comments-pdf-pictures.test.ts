// The panel's PICTURES over a PDF (plans/file-review.md, Slice 4; contract F4): which pages take an overlay, and when, and
// which picture a region comment is on — driven end to end through the file-comments-page-states.test.ts stand-in, with an
// IntersectionObserver the test fires by hand (the pdf-chunk tests' FakeIO idiom).
//   • Making an overlay appends it to the page's shell and measures it: a forced layout of the whole page column, so one
//     per page in one pass is quadratic in the page count — 3 s with the pane unresponsive at 2,000 pages, ~20 s at the chunk's 5,000
//     cap, on the panel's first pass (the review, 2026-09-06). A page takes its overlay at once only when there is
//     something to paint or a bitmap is in (the page is near the reader): a region comment's rectangle, the composer's
//     pending region, the re-place cue, the chunk's draw. Every other page is watched by its shell and takes its overlay as
//     it nears — the same margin as the chunk's draws — armed and wired like the rest; without an IntersectionObserver,
//     every page takes one at once, as the chunk then draws every page.
//   • A region of kind "image" on a PDF (another host wrote it: no page) is on no page's canvas: no rectangle, no crop cut
//     from page 1, no Re-place. The panel itself never writes such a target for a PDF; the guard is for what arrives.
// Synthetic fixtures only: the notes-api world, placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import type { FileViewActionCtx } from "./file-view";
import type { Status, StoreComment } from "./file-comments-model";

// ── the DOM stand-in ───────────────────────────────────────────────────────────────────────────────
type Rect = { left: number; top: number; right: number; bottom: number; width: number; height: number };
const rectOf = (left: number, top: number, width: number, height: number): Rect => ({ left, top, width, height, right: left + width, bottom: top + height });
const ZERO = rectOf(0, 0, 0, 0);
class Doc {
  body: E;
  hidden = false;
  /** the focus model: what holds the keyboard; the body when nothing does */
  activeElement: E | null = null;
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
  focus(_opts?: unknown): void { if (this.tabIndex >= 0 && !this.disabled) this.ownerDocument.activeElement = this; }
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

/** The scroller lookup reads computed overflow: the stand-in's inline style stands for it. */
win.getComputedStyle = (el: E) => el.style;

// ── a fake IntersectionObserver the test fires by hand (the pdf-chunk tests' idiom) ─────────────────
class FakeIO {
  static instances: FakeIO[] = [];
  targets = new Set<E>();
  disconnected = false;
  constructor(public cb: (entries: unknown[], io: FakeIO) => void, public opts: { root?: unknown; rootMargin?: string }) { FakeIO.instances.push(this); }
  observe(t: E): void { this.targets.add(t); }
  unobserve(t: E): void { this.targets.delete(t); }
  disconnect(): void { this.disconnected = true; this.targets.clear(); }
  /** Entries for the given shells: intersecting or not. */
  fire(states: Array<[E, boolean]>): void { this.cb(states.map(([target, isIntersecting]) => ({ target, isIntersecting })), this); }
}
const withIO = () => { (globalThis as any).IntersectionObserver = FakeIO; FakeIO.instances.length = 0; };
const withoutIO = () => { delete (globalThis as any).IntersectionObserver; FakeIO.instances.length = 0; };

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const PDF = "/repo/notes-api/docs/deck.pdf";
const T0 = 1757145600000;
const ID = T0 + "-0";
const ID3 = T0 + "-3";
const H1 = "1111111111111111111111111111111111111111111111111111111111111111";
// US-letter pages drawn at 306×396 CSS px (the 612×792 backing store at half size), stacked 20px apart from (100, 200):
// a drag from (150, 656) to (250, 716) over page 2 is R2
const REGION = { x: 0.1667, y: 0.2, w: 0.3333, h: 0.3 };
const pageComment = (page: number, over: Partial<StoreComment> = {}): StoreComment => ({
  id: ID, author: "you", ts: T0, body: "Crop the header.", replies: [], resolved: false,
  target: { kind: "pdf", page, region: REGION, hash: H1 } as StoreComment["target"], ...over,
});
/** A region another host wrote on the PDF as a whole picture: kind image, no page (the host script accepts it on any path). */
const imageComment = (over: Partial<StoreComment> = {}): StoreComment => ({
  id: ID, author: "api", ts: T0, body: "Trim the margin.", replies: [], resolved: false,
  target: { kind: "image", region: REGION, hash: H1 } as StoreComment["target"], ...over,
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
/** How a test mounts each page's shell, as the chunk leaves it: drawn (a 612×792 bitmap in its canvas) or undrawn (the
 *  chunk's 0×0 canvas, before a draw or after an eviction). */
type PageState = "drawn" | "undrawn";
/** A mounted panel over a PDF body the chunk drew (`.fileview-pdfhost > .fileview-pdf > .fileview-pdf-page[data-page]`,
 *  one shell per page, each in the state given), inside the viewer's body row, which scrolls (overflow-y auto: the
 *  chunk's and the panel's watches are rooted there). `repaint` fires the seam's onRendered hooks, as fireRendered does
 *  after every page the chunk draws (its onPage); `mount` again is a reload's new shells and canvases. */
async function harness(states: PageState[]) {
  const fc = await import("./file-comments");
  const main = doc.createElement("div"); main.className = "fileview-main";
  const body = doc.createElement("div"); body.className = "fileview-body"; body.style.overflowY = "auto"; main.appendChild(body);
  let media: E | null = null;
  const pages: E[] = [];
  const rectFor = (i: number): Rect => rectOf(100, 200 + i * 416, 306, 396);
  const mount = (st: PageState[]): E[] => {
    body.querySelector(".fileview-pdfhost")?.remove();  // a reload: the chunk's root goes with its shells, new ones come
    const host = doc.createElement("div"); host.className = "fileview-pdfhost";
    const pdf = doc.createElement("div"); pdf.className = "fileview-pdf";
    const out: E[] = [];
    st.forEach((s, i) => {
      const w = doc.createElement("div"); w.className = "fileview-pdf-page"; w.dataset.page = String(i + 1); w.style.position = "relative"; w.rect = rectFor(i);
      const c = doc.createElement("canvas"); c.className = "fileview-pdf-canvas"; c.dataset.page = String(i + 1); c.rect = rectFor(i);
      if (s === "drawn") { c.width = 612; c.height = 792; }
      w.appendChild(c);
      pdf.appendChild(w); out.push(w);
    });
    host.appendChild(pdf); body.appendChild(host);
    media = pdf; pages.splice(0, pages.length, ...out);
    return out;
  };
  mount(states);
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
  };
  const unit = fc.fileCommentsAction.mount(ctx) as unknown as E;
  const button = unit.childNodes[0] as E;
  const last = (): Posted => posted[posted.length - 1];
  const reply = async (data: Record<string, unknown>) => { win.dispatchEvent(new MessageEvent("message", { data })); await tick(); await tick(); };
  const canvasOf = (page: number): E => { const c = pages[page - 1].querySelector("canvas"); assert.ok(c, "page " + page + " has a canvas"); return c!; };
  return {
    fc, main, body, unit, button, posted, saved, rendered, last, pages, mount,
    ok: (o: Partial<Status> = {}) => reply({ type: "fileCommentsResult", reqId: last().reqId, ...pdfStatus(o) }),
    q: (sel: string) => main.querySelector(sel),
    qa: (sel: string) => main.querySelectorAll(sel),
    click: (sel: string) => { const e = main.querySelector(sel); assert.ok(e, "a control " + sel); e!.dispatch("click"); },
    /** Open the panel: the button, then the status it re-asks. */
    open: async (o: Partial<Status> = {}) => { button.dispatch("click"); await reply({ type: "fileCommentsResult", reqId: last().reqId, ...pdfStatus(o) }); },
    /** Close the panel: the button again. */
    close: () => { button.dispatch("click"); },
    /** The seam's onRendered, fired as after every page draw (fireRendered from the chunk's onPage). */
    repaint: () => { for (const cb of rendered) cb(); },
    /** The chunk drew the page (a bitmap in its canvas). */
    draw: (page: number) => { const c = canvasOf(page); c.width = 612; c.height = 792; },
    drag: (overlay: E, from: [number, number], to: [number, number]) => {
      overlay.dispatch("pointerdown", { clientX: from[0], clientY: from[1], pointerId: 7, button: 0 });
      overlay.dispatch("pointermove", { clientX: to[0], clientY: to[1], pointerId: 7 });
      overlay.dispatch("pointerup", { clientX: to[0], clientY: to[1], pointerId: 7 });
      return overlay.dispatch("click");
    },
    overlays: () => main.querySelectorAll(".fileview-pdf-page .fc-overlay"),
    /** The 1-based pages that have an overlay. */
    overlaid: () => pages.map((p, i) => (p.querySelector(".fc-overlay") ? i + 1 : 0)).filter(Boolean),
    /** The 1-based pages whose shells the panel's watch holds. */
    watched: () => (FakeIO.instances[0] ? [...FakeIO.instances[0].targets].map((t) => Number(t.dataset.page)).sort((a, b) => a - b) : []),
    dispose: () => { for (const cb of closers) cb(); },
  };
}

// ── which pages take an overlay, and when ──────────────────────────────────────────────────────────

test("a long PDF, the panel opening: an overlay on the drawn page and on the page with a rectangle to place, every other page watched by its shell; a page nearing takes its overlay, armed and wired to the composer; the watch is rooted at the scroller with the chunk's margin", async () => {
  withIO();
  drawn.length = 0;
  const h = await harness(["drawn", ...Array<PageState>(11).fill("undrawn")]);
  const c7 = pageComment(7);
  await h.ok(withStore([c7]));
  await h.open(withStore([c7]));
  assert.deepEqual(h.overlaid(), [1, 7], "the drawn page, and the page with a rectangle to place");
  assert.ok(h.pages[6].querySelector('.fc-region[data-id="' + ID + '"]'), "the rectangle on page 7: percentages of the page's box, bitmap or not");
  assert.equal(FakeIO.instances.length, 1, "one watch for the panel");
  const io = FakeIO.instances[0];
  assert.equal(io.opts.root, h.body, "rooted at the scroller the pages live in: the viewer's body");
  assert.equal(io.opts.rootMargin, "100% 0px", "one scroller height ahead: the chunk's own margin for the draws");
  assert.deepEqual(h.watched(), [2, 3, 4, 5, 6, 8, 9, 10, 11, 12], "every page without an overlay, watched by its shell");
  io.fire([[h.pages[1], true], [h.pages[2], true], [h.pages[3], false]]);
  assert.deepEqual(h.overlaid(), [1, 2, 3, 7], "the two that neared took theirs; the one that did not, none");
  assert.deepEqual(h.watched(), [4, 5, 6, 8, 9, 10, 11, 12], "…and left the watch");
  const o2 = h.pages[1].querySelector(".fc-overlay")!;
  assert.equal(o2.classList.contains("fc-overlay-off"), false, "armed: the panel is open on a fine pointer");
  assert.equal(o2.getAttribute("aria-label"), "Drag to comment on a region of the page");
  assert.equal(h.pages[1].childNodes[0], h.pages[1].querySelector("canvas"), "the canvas stays the shell's first child");
  assert.equal(h.pages[1].childNodes[1], o2, "the overlay joins it inside the shell");
  h.drag(o2, [150, 656], [250, 716]);
  assert.equal(h.q(".fc-composer")!.hidden, false, "a drag on the late overlay opens the composer");
  assert.equal(h.q(".fc-composer-ref .fc-note")!.textContent, "On the region at 0.16, 0.10, 0.33, 0.15 of page 2", "the page named");
  assert.ok(o2.querySelector(".fc-region-pending"), "the pending rectangle on the page");
  h.repaint();
  assert.deepEqual(h.overlaid(), [1, 2, 3, 7], "a repaint makes no overlay for a far page");
  assert.deepEqual(h.watched(), [4, 5, 6, 8, 9, 10, 11, 12], "…and keeps the same watch: a page with an overlay is not watched again");
  h.draw(5); h.repaint();
  assert.deepEqual(h.overlaid(), [1, 2, 3, 5, 7], "a page the chunk drew takes its overlay on the draw's repaint");
  assert.deepEqual(h.watched(), [4, 6, 8, 9, 10, 11, 12]);
  h.close();
  assert.ok(h.pages[0].querySelector(".fc-overlay")!.classList.contains("fc-overlay-off"), "closed: the overlays stay, disarmed");
  io.fire([[h.pages[5], true]]);
  assert.deepEqual(h.overlaid(), [1, 2, 3, 5, 6, 7], "a page nearing while the panel is closed takes its overlay too: the rectangles show while closed");
  assert.ok(h.pages[5].querySelector(".fc-overlay")!.classList.contains("fc-overlay-off"), "…disarmed like the rest");
  h.dispose();
  assert.equal(io.disconnected, true, "the watch goes with the viewer");
  assert.equal(h.overlays().length, 0, "…and so do the overlays");
});

test("a reload hands back new canvases while a region is pending: the composer's page, undrawn and with no rectangle of its own, takes its overlay at once, so the pending rectangle follows the page; the old shells leave the watch", async () => {
  withIO();
  const h = await harness(["drawn", "drawn", "undrawn"]);
  await h.ok();
  await h.open();
  assert.deepEqual(h.overlaid(), [1, 2]);
  assert.deepEqual(h.watched(), [3]);
  const old3 = h.pages[2];
  h.drag(h.pages[1].querySelector(".fc-overlay")!, [150, 656], [250, 716]);
  assert.ok(h.pages[1].querySelector(".fc-region-pending"), "the pending rectangle on page 2");
  h.mount(["drawn", "undrawn", "undrawn"]); h.repaint();   // the poll saw the file move: new shells, page 2 not drawn yet
  assert.deepEqual(h.overlaid(), [1, 2], "page 1 for its bitmap, page 2 for the pending region");
  assert.ok(h.pages[1].querySelector(".fc-region-pending"), "the pending rectangle, re-found by page number, on the new page 2");
  assert.deepEqual(h.watched(), [3], "the new page 3");
  assert.equal(FakeIO.instances[0].targets.has(old3), false, "the old shell left the watch with its canvas");
  h.dispose();
});

test("no page drawn and nothing to place (every bitmap given back: the pane hidden): no overlay, and the empty state offers the whole-file comment alone; the first page to near takes one, and the aside is re-rendered to name the drag", async () => {
  withIO();
  const h = await harness(["undrawn", "undrawn", "undrawn"]);
  await h.ok();
  await h.open();
  assert.equal(h.overlays().length, 0);
  assert.equal(h.q(".fc-empty")!.textContent, "No comments yet. Comment on this file to leave one.");
  assert.deepEqual(h.watched(), [1, 2, 3]);
  FakeIO.instances[0].fire([[h.pages[0], true]]);
  assert.deepEqual(h.overlaid(), [1]);
  assert.equal(h.q(".fc-empty")!.textContent, "No comments yet. Drag a rectangle on a page, or comment on this file.", "the first overlay in view: the gesture is named");
  h.dispose();
});

test("no IntersectionObserver: every page takes its overlay at once — nothing can say which pages are near, and the chunk draws every page then, too", async () => {
  withoutIO();
  const h = await harness(["drawn", "undrawn", "undrawn", "undrawn"]);
  await h.ok();
  await h.open();
  assert.equal(h.overlays().length, 4, "one overlay per page");
  assert.equal(FakeIO.instances.length, 0);
  h.dispose();
});

// ── which picture a region is on ───────────────────────────────────────────────────────────────────

test("an image-kind region on a PDF (another host wrote it: no page) is on no page's canvas: no rectangle on any page, nothing cut from page 1, no Re-place — while the page region beside it paints and crops", async () => {
  withoutIO();
  drawn.length = 0;
  const h = await harness(["drawn", "drawn"]);
  const whole = imageComment();
  const p1 = pageComment(1, { id: ID3 });
  await h.ok(withStore([whole, p1]));
  await h.open(withStore([whole, p1]));
  assert.equal(h.overlays().length, 2);
  assert.equal(h.qa(".fc-region").length, 1, "one rectangle: the page region's");
  assert.ok(h.pages[0].querySelector('.fc-region[data-id="' + ID3 + '"]'), "…on page 1");
  assert.equal(h.q('.fc-region[data-id="' + ID + '"]'), null, "the image-kind region lands on no page");
  drawn.length = 0;
  h.click('.fc-card[data-id="' + ID + '"] .fc-card-head');
  const open = h.q('.fc-card.open[data-id="' + ID + '"]')!;
  assert.equal(open.querySelector("canvas.fc-crop"), null, "no page is its picture: nothing to crop");
  assert.equal(drawn.length, 0, "nothing cut from page 1's canvas");
  assert.equal(open.querySelector('[data-act="fcreplace"]'), null, "no picture in view for it: no Re-place");
  assert.equal(open.querySelector(".fc-ref")!.textContent, "the region at 0.17, 0.20, 0.33, 0.30", "the reference names no page");
  h.click('.fc-card[data-id="' + ID3 + '"] .fc-card-head');
  assert.ok(h.q('.fc-card.open[data-id="' + ID3 + '"] canvas.fc-crop'), "the page region beside it: cropped from page 1");
  h.dispose();
});
