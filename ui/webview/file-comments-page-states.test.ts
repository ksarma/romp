// A PDF page's states as the Comments panel reports them (plans/file-review.md, Slice 4), driven end to end through
// the DOM stand-in of file-comments-pages.test.ts: the chunk's shells stand for the pages (div.fileview-pdf-page,
// data-page), and a test puts each shell in the state the chunk would leave it in.
//   • a page pdf.js could not draw (pdf-chunk.ts fail(): the canvas removed, the notice appended, the shell kept) reads
//     "not rendered", never as a page the PDF no longer has: the hashes alone say whether the file changed, the card's
//     reference reaches the page's notice, and no Re-place is offered (the comment's place is not in question);
//   • a page the regenerated document no longer has (no shell) still reads gone, from the shells, not the canvases;
//   • a card keeps its page crop after the chunk evicts the page's bitmap (a 0×0 canvas) or fails the page, and drops
//     it when the file's bytes or the comment's region change, or while the file's hash is unknown;
//   • the unknown state's wording names the PDF, on the tag and on the rectangle.
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
const ID3 = T0 + "-3";
const ID4 = T0 + "-4";
const FAIL_MSG = "Page dictionary kid reference points to wrong type of object.";

// ── the harness ────────────────────────────────────────────────────────────────────────────────────
type Posted = Record<string, any>;
/** How a test mounts each page's shell, as the chunk leaves it: drawn (a 612×792 bitmap in its canvas), undrawn (the
 *  chunk's 0×0 canvas, before a draw or after an eviction), or failed (pdf-chunk.ts fail(): no canvas, the notice in
 *  the shell, the shell kept). */
type PageState = "drawn" | "undrawn" | "failed";
/** A mounted panel over a PDF body the chunk drew (`.fileview-pdfhost > .fileview-pdf > .fileview-pdf-page[data-page]`,
 *  one shell per page, each in the state given), inside the viewer's body row. `repaint` fires the seam's onRendered
 *  hooks, as fireRendered does after every page the chunk draws (its onPage) and would after a page it could not. */
async function harness(states: PageState[], over: Partial<FileViewActionCtx> = {}) {
  const fc = await import("./file-comments");
  const main = doc.createElement("div"); main.className = "fileview-main";
  const body = doc.createElement("div"); body.className = "fileview-body"; main.appendChild(body);
  let media: E | null = null;
  const pages: E[] = [];
  // US-letter pages drawn at 306×396 CSS px, stacked 20px apart from (100, 200): pages 1 and 2 are PAGE_RECTS
  const rectFor = (i: number): Rect => rectOf(100, 200 + i * 416, 306, 396);
  const fail = (w: E, page: number): void => {   // what pdf-chunk.ts fail() leaves: the canvas gone, the notice in the shell, the shell kept
    w.querySelector("canvas")?.remove();
    const note = doc.createElement("div"); note.className = "fileview-err fileview-pdf-page-err";
    note.textContent = "Page " + page + " did not render — " + FAIL_MSG;
    w.appendChild(note);
  };
  const mount = (st: PageState[]): E[] => {
    const host = doc.createElement("div"); host.className = "fileview-pdfhost";
    const pdf = doc.createElement("div"); pdf.className = "fileview-pdf";
    const out: E[] = [];
    st.forEach((s, i) => {
      const w = doc.createElement("div"); w.className = "fileview-pdf-page"; w.dataset.page = String(i + 1); w.style.position = "relative"; w.rect = rectFor(i);
      const c = doc.createElement("canvas"); c.className = "fileview-pdf-canvas"; c.dataset.page = String(i + 1); c.rect = rectFor(i);
      if (s === "drawn") { c.width = 612; c.height = 792; }
      w.appendChild(c);
      if (s === "failed") fail(w, i + 1);
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
    ...over,
  };
  const unit = fc.fileCommentsAction.mount(ctx) as unknown as E;
  const button = unit.childNodes[0] as E;
  const last = (): Posted => posted[posted.length - 1];
  const reply = async (data: Record<string, unknown>) => { win.dispatchEvent(new MessageEvent("message", { data })); await tick(); await tick(); };
  const canvasOf = (page: number): E => { const c = pages[page - 1].querySelector("canvas"); assert.ok(c, "page " + page + " has a canvas"); return c!; };
  return {
    fc, main, body, unit, button, posted, saved, rendered, last, pages,
    ok: (o: Partial<Status> = {}) => reply({ type: "fileCommentsResult", reqId: last().reqId, ...pdfStatus(o) }),
    q: (sel: string) => main.querySelector(sel),
    qa: (sel: string) => main.querySelectorAll(sel),
    click: (sel: string) => { const e = main.querySelector(sel); assert.ok(e, "a control " + sel); e!.dispatch("click"); },
    /** Open the panel: the button, then the status it re-asks. */
    open: async (o: Partial<Status> = {}) => { button.dispatch("click"); await reply({ type: "fileCommentsResult", reqId: last().reqId, ...pdfStatus(o) }); },
    /** A fresh status the way the poll or a save brings one: the onSaved hook re-asks, the reply lands. */
    restatus: async (o: Partial<Status> = {}) => { saved[0]({ mtimeNs: "1757145600000000001", logged: true }); await tick(); await reply({ type: "fileCommentsResult", reqId: last().reqId, ...pdfStatus(o) }); },
    /** The seam's onRendered, fired as after every page draw (fireRendered from the chunk's onPage). */
    repaint: () => { for (const cb of rendered) cb(); },
    /** The chunk drew the page (a bitmap in its canvas). */
    draw: (page: number) => { const c = canvasOf(page); c.width = 612; c.height = 792; },
    /** The chunk gave the page's bitmap back (it scrolled beyond one scroller height): a 0×0 canvas, the element kept. */
    evict: (page: number) => { const c = canvasOf(page); c.width = 0; c.height = 0; },
    /** pdf.js refused the page (a redraw, a return after an eviction): pdf-chunk.ts fail(). */
    fail: (page: number) => fail(pages[page - 1], page),
    overlays: () => main.querySelectorAll(".fileview-pdf-page .fc-overlay"),
    head: (id: string = ID) => main.querySelector('.fc-card[data-id="' + id + '"] .fc-card-head')!,
    tags: (id: string = ID) => main.querySelectorAll('.fc-card[data-id="' + id + '"] .fc-card-head .fc-tag'),
    crop: (id: string = ID) => main.querySelector('.fc-card.open[data-id="' + id + '"] canvas.fc-crop'),
    dispose: () => { for (const cb of closers) cb(); },
  };
}

// ── a page pdf.js could not draw ───────────────────────────────────────────────────────────────────

test("a page pdf.js could not draw reads 'not rendered', not as a page the PDF no longer has: no stale tag while the hashes agree, no Re-place, and the reference reaches the page's notice", async () => {
  drawn.length = 0;
  const h = await harness(["drawn", "failed", "drawn"]);
  const c2 = pageComment(2);
  await h.ok(withStore([c2]));
  await h.open(withStore([c2]));
  assert.equal(h.overlays().length, 2, "an overlay on each page with a picture, none on the failed one");
  assert.equal(h.q(".fc-region"), null, "no picture to paint the rectangle on");
  assert.deepEqual(h.tags().map((t) => t.textContent), ["not rendered"]);
  assert.equal(h.tags()[0].title, "Page 2 did not render, so this region is not shown; the PDF still has that page, and its notice says why");
  assert.equal(h.head().querySelector(".fc-tag-stale"), null, "the bytes did not change: nothing says stale");
  const ref = h.head().querySelector(".fc-ref")!;
  assert.equal(ref.textContent, "the region at 0.17, 0.20, 0.33, 0.30 of page 2");
  assert.equal(ref.getAttribute("data-act"), "fcgoto", "the compact card does not dead-end");
  assert.equal(ref.title, "Scroll to the page; its notice says why it did not render");
  ref.dispatch("click");
  assert.equal(h.pages[1].scrolled, 1, "the reference scrolls the page's shell, which holds the chunk's notice");
  assert.equal(h.pages[1].querySelector(".fileview-pdf-page-err")!.textContent, "Page 2 did not render — " + FAIL_MSG);
  h.click('.fc-card[data-id="' + ID + '"] .fc-card-head');
  const open = h.q('.fc-card.open[data-id="' + ID + '"]')!;
  assert.deepEqual(open.querySelectorAll(".fc-actions button").map((b) => b.textContent), ["Reply", "Resolve"], "no Re-place: the comment's place is not in question, only the picture");
  assert.equal(h.crop(), null, "the page never drew: nothing to cut");
  assert.equal(h.q(".fc-composer")!.hidden, true);
  // the file DID change under it: stale from the hashes, in the PDF's words (not "no longer has page 2"), and not rendered besides
  await h.restatus({ ...withStore([c2]), fileHash: H2 });
  assert.deepEqual(h.tags().map((t) => t.textContent), ["stale", "not rendered"]);
  assert.equal(h.tags()[0].title, "The PDF changed after this region was drawn, so it may no longer mark the right place. Resolve it; re-placing it needs its page drawn in the viewer.", "the PDF's words; no Re-place, so the recourse says what stands in its way");
  h.dispose();
});

test("the page set is the shells, not the canvases: beside a failed page 2, a comment on page 4 of a three-page document reads gone (stale, Re-place on any page) and one on the drawn page 3 reads current", async () => {
  const h = await harness(["drawn", "failed", "drawn"]);
  const c3 = pageComment(3, { id: ID3 }); const c4 = pageComment(4, { id: ID4 });
  await h.ok(withStore([c3, c4]));
  await h.open(withStore([c3, c4]));
  assert.deepEqual(h.tags(ID4).map((t) => t.textContent), ["stale"]);
  assert.equal(h.tags(ID4)[0].title, "The PDF changed after this region was drawn and no longer has page 4. Re-place it on a page it has, or resolve it.");
  h.click('.fc-card[data-id="' + ID4 + '"] .fc-card-head');
  const rp = h.q('.fc-card.open[data-id="' + ID4 + '"] [data-act="fcreplace"]')!;
  assert.ok(rp, "Re-place is the remedy the tag names");
  assert.equal(rp.title, "The PDF no longer has this page: draw the region again on a page it has");
  h.click('.fc-card.open[data-id="' + ID4 + '"] [data-act="fcreplace"]');
  assert.match(h.q(".fc-composer-ref .fc-note")!.textContent, /of page 4, a page the PDF no longer has\)\./);
  assert.equal(h.tags(ID3).length, 0, "page 3 drew: current");
  assert.ok(h.pages[2].querySelector('.fc-region[data-id="' + ID3 + '"]'), "…and its rectangle is on page 3");
  h.dispose();
});

test("a page that fails after the panel painted it: on the repaint the overlay leaves with the canvas, the card reads 'not rendered' rather than stale, and keeps the crop cut when the page was drawn (the same bytes)", async () => {
  drawn.length = 0;
  const h = await harness(["drawn", "drawn"]);
  const c2 = pageComment(2);
  await h.ok(withStore([c2]));
  await h.open(withStore([c2]));
  assert.ok(h.pages[1].querySelector('.fc-region[data-id="' + ID + '"]'), "the rectangle on page 2");
  h.click('.fc-card[data-id="' + ID + '"] .fc-card-head');
  const cut = h.crop()!;
  assert.ok(cut, "the crop, cut from page 2's canvas");
  assert.equal(drawn[drawn.length - 1][0], h.pages[1].querySelector("canvas"));
  h.fail(2);                                            // a redraw pdf.js refused: pdf-chunk.ts fail()
  h.repaint();                                          // the repaint onPageError brings (file-view.ts wires it to fireRendered)
  assert.equal(h.overlays().length, 1, "the failed page's overlay left with its canvas");
  assert.equal(h.pages[1].querySelector(".fc-overlay"), null);
  assert.equal(h.q(".fc-region"), null);
  assert.deepEqual(h.tags().map((t) => t.textContent), ["not rendered"]);
  const n = drawn.length;
  assert.equal(h.crop(), cut, "the kept crop: the same bytes, the same picture");
  assert.equal(drawn.length, n, "nothing is drawn from a page with no canvas");
  h.dispose();
});

// ── the crop across the chunk's evictions ──────────────────────────────────────────────────────────

test("a card keeps its page crop across the chunk's evictions: none before the page draws, cut on its draw, kept when the bitmap is given back, dropped when the file's bytes or the region change or the hash is unknown", async () => {
  drawn.length = 0;
  const h = await harness(["drawn", "undrawn"]);
  const c2 = pageComment(2);
  await h.ok(withStore([c2]));
  await h.open(withStore([c2]));
  h.click('.fc-card[data-id="' + ID + '"] .fc-card-head');
  assert.equal(h.crop(), null, "page 2 has no bitmap yet: nothing to cut");
  assert.ok(h.pages[1].querySelector('.fc-region[data-id="' + ID + '"]'), "the rectangle is placed all the same: percentages of the page's box");
  h.draw(2); h.repaint();                               // the page scrolled near: the chunk drew it (onPage → fireRendered)
  const cut = h.crop()!;
  assert.ok(cut, "the crop comes with the draw's repaint");
  assert.equal(drawn[drawn.length - 1][0], h.pages[1].querySelector("canvas"));
  h.evict(2); h.repaint();                              // scrolled away: the bitmap given back, a 0×0 canvas
  const n = drawn.length;
  assert.equal(h.crop(), cut, "the kept crop, the same node");
  assert.equal(drawn.length, n, "…not redrawn from the empty canvas");
  await h.restatus({ ...withStore([c2]), fileHash: H2 });   // the PDF regenerated: the crop shows bytes the file no longer has
  assert.equal(h.crop(), null, "dropped with the file's hash");
  assert.equal(h.tags()[0].textContent, "stale");
  await h.restatus({ ...withStore([c2]), fileHash: H1 });   // the same bytes again (the session put the file back)
  assert.equal(h.crop(), cut, "the same bytes: the kept crop shows again");
  await h.restatus({ ...withStore([c2]), fileHash: null });  // whether the bytes are the crop's cannot be told
  assert.equal(h.crop(), null, "nothing shown under an unknown hash");
  assert.equal(h.tags()[0].textContent, "unknown");
  // re-placed on the same, undrawn page: the old region's crop is not the new region's
  const moved = pageComment(2, {}, { region: R2 });
  await h.restatus({ ...withStore([moved]), fileHash: H1 });
  assert.equal(h.crop(), null, "another region: nothing kept for it until the page draws");
  h.draw(2); h.repaint();
  assert.ok(h.crop(), "cut on the draw");
  assert.notEqual(h.crop(), cut);
  h.dispose();
});

// ── the unknown state, in the PDF's words ──────────────────────────────────────────────────────────

test("the unknown state names the PDF: a status with no file hash tags the card 'unknown' in the PDF's words, and the rectangle's title too", async () => {
  const h = await harness(["drawn", "drawn"]);
  const c1 = pageComment(1);
  await h.ok({ ...withStore([c1]), fileHash: null });
  await h.open({ ...withStore([c1]), fileHash: null });
  assert.deepEqual(h.tags().map((t) => t.textContent), ["unknown"]);
  assert.equal(h.tags()[0].title, "Whether the PDF changed since this region was drawn could not be checked.");
  const rect = h.pages[0].querySelector('.fc-region[data-id="' + ID + '"]')!;
  assert.ok(rect.classList.contains("fc-unknown"));
  assert.equal(rect.title, "Open the comment on this region (whether the PDF changed could not be checked)");
  h.dispose();
});

// ── source pins: what the stand-in cannot show ─────────────────────────────────────────────────────

test("source pins: the page set is read from the shells, the crop is asked for with or without a picture in view, and the kept crops leave with the viewer", () => {
  const SRC = web("file-comments.ts");
  assert.match(SRC, /private pageGone\(c: Card\): boolean \{ return this\.pageShellFor\(c\) === null; \}/, "gone is a page with no shell");
  assert.match(SRC, /private pageShellFor\(c: Card\)[^]*?const shells = this\.ctx\.pdfPages\(\);/, "…read from the seam's shells, never the canvases");
  assert.match(SRC, /return !!shell && !isCanvas\(shell\.querySelector\("canvas\.fileview-pdf-canvas"\)\);/, "not rendered is a shell with no canvas (pdf-chunk.ts fail())");
  assert.match(SRC, /const crop = c\.target \? this\.cropFor\(picture, c\) : null;/, "the crop is asked for even with no picture in view");
  assert.match(SRC, /this\.crops\.clear\(\);/, "the kept crops leave with the viewer");
});
