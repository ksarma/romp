// A PDF region card whose page has no bitmap (plans/file-review.md, Slice 4: "the card shows the page crop"). The chunk
// draws a page as it nears the reader (one scroller height away) and gives a far page's bitmap back, so a comment on a
// page outside that window has a 0×0 canvas and cropFor has nothing to cut; the chunk's only API is render(), so the
// panel cannot ask for the page. The card must not dead-end there (ui/CLAUDE.md): in the crop's place it shows one line
// that says the page is not drawn and is itself the control that scrolls the page in (fcgoto), which draws it; the
// draw's repaint (the seam's onRendered, from the chunk's onPage) replaces the line with the crop. The line appears ONLY
// for a mounted page with a canvas and no bitmap: a drawn page crops, a page pdf.js could not draw wears its own tag, a
// page the document no longer has wears stale, and a kept crop stands in for an evicted page. Driven end to end through
// the DOM stand-in of file-comments-page-states.test.ts (copied: each test file is its own bundle). Synthetic fixtures
// only: the notes-api world, placeholder ids.
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
const REGION = { x: 0.1667, y: 0.2, w: 0.3333, h: 0.3 };
const idFor = (page: number): string => T0 + "-" + page;
const pageComment = (page: number, over: Partial<StoreComment> = {}, target: Record<string, unknown> = {}): StoreComment => ({
  id: idFor(page), author: "you", ts: T0, body: "Crop the header.", replies: [], resolved: false,
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
const FAIL_MSG = "Page dictionary kid reference points to wrong type of object.";

// ── the harness ────────────────────────────────────────────────────────────────────────────────────
type Posted = Record<string, any>;
/** How a test mounts each page's shell, as the chunk leaves it: drawn (a 612×792 bitmap in its canvas), undrawn (the
 *  chunk's 0×0 canvas, before a draw or after an eviction), or failed (pdf-chunk.ts fail(): no canvas, the notice in
 *  the shell, the shell kept). */
type PageState = "drawn" | "undrawn" | "failed";
/** A mounted panel over a PDF body the chunk drew (`.fileview-pdfhost > .fileview-pdf > .fileview-pdf-page[data-page]`,
 *  one shell per page, each in the state given), inside the viewer's body row. `repaint` fires the seam's onRendered
 *  hooks, as fireRendered does after every page the chunk draws (its onPage). */
async function harness(states: PageState[], over: Partial<FileViewActionCtx> = {}) {
  const fc = await import("./file-comments");
  const main = doc.createElement("div"); main.className = "fileview-main";
  const body = doc.createElement("div"); body.className = "fileview-body"; main.appendChild(body);
  let media: E | null = null;
  const pages: E[] = [];
  // US-letter pages drawn at 306×396 CSS px, stacked 20px apart from (100, 200)
  const rectFor = (i: number): Rect => rectOf(100, 200 + i * 416, 306, 396);
  const fail = (w: E, page: number): void => {   // what pdf-chunk.ts fail() leaves: the canvas gone, the notice in the shell, the shell kept
    w.querySelector("canvas")?.remove();
    const note = doc.createElement("div"); note.className = "fileview-err fileview-pdf-page-err";
    note.textContent = "Page " + page + " did not render — " + FAIL_MSG;
    w.appendChild(note);
  };
  const host = doc.createElement("div"); host.className = "fileview-pdfhost";
  const pdf = doc.createElement("div"); pdf.className = "fileview-pdf";
  states.forEach((s, i) => {
    const w = doc.createElement("div"); w.className = "fileview-pdf-page"; w.dataset.page = String(i + 1); w.style.position = "relative"; w.rect = rectFor(i);
    const c = doc.createElement("canvas"); c.className = "fileview-pdf-canvas"; c.dataset.page = String(i + 1); c.rect = rectFor(i);
    if (s === "drawn") { c.width = 612; c.height = 792; }
    w.appendChild(c);
    if (s === "failed") fail(w, i + 1);
    pdf.appendChild(w); pages.push(w);
  });
  host.appendChild(pdf); body.appendChild(host);
  media = pdf;
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
    /** Expand a card. */
    expand: (id: string) => { const e = main.querySelector('.fc-card[data-id="' + id + '"] .fc-card-head'); assert.ok(e, "the card " + id); e!.dispatch("click"); },
    card: (id: string) => main.querySelector('.fc-card.open[data-id="' + id + '"]'),
    tags: (id: string) => main.querySelectorAll('.fc-card[data-id="' + id + '"] .fc-card-head .fc-tag').map((t) => t.textContent),
    crop: (id: string) => main.querySelector('.fc-card.open[data-id="' + id + '"] canvas.fc-crop'),
    /** The line in the crop's place while the page has no bitmap. */
    wait: (id: string) => main.querySelector('.fc-card.open[data-id="' + id + '"] .fc-crop-wait'),
    rect: (id: string) => main.querySelector('.fileview-pdf-page .fc-region[data-id="' + id + '"]'),
    dispose: () => { for (const cb of closers) cb(); },
  };
}

// ── the crop's place while the page has no bitmap ──────────────────────────────────────────────────

test("a card on a page with no bitmap: no crop, and in its place one line that names the page and scrolls it in (click or Enter); the draw's repaint replaces the line with the crop", async () => {
  drawn.length = 0;
  const h = await harness(["drawn", "undrawn", "undrawn"]);
  const c2 = pageComment(2);
  await h.ok(withStore([c2]));
  await h.open(withStore([c2]));
  h.expand(c2.id);
  assert.equal(h.crop(c2.id), null, "page 2 has no bitmap: nothing to cut");
  assert.equal(drawn.length, 0, "and nothing was drawn from a 0×0 canvas");
  const line = h.wait(c2.id)!;
  assert.ok(line, "the crop's place says why there is none");
  assert.equal(line.textContent, "Page 2 is not drawn yet. Go to the page to see this region.");
  assert.equal(line.dataset.act, "fcgoto", "the line is the control that reaches the page");
  assert.equal(line.dataset.id, c2.id);
  assert.equal(line.tabIndex, 0, "a Tab stop");
  assert.equal(line.getAttribute("role"), "button");
  assert.ok(line.classList.contains("fc-link"), "reads as a control");
  assert.ok(line.classList.contains("fc-note"), "in the panel's note size, not a new one");
  assert.equal(line.title, "Go to page 2; the picture of this region appears here once the page is drawn");
  const card = h.card(c2.id)!;
  assert.equal(card.childNodes[1], line, "where the crop goes: after the head");
  assert.ok((card.childNodes[2] as E).classList.contains("fc-body"), "…before the body");
  assert.deepEqual(h.tags(c2.id), [], "no tag: the page is there and the file unchanged, only the bitmap is missing");
  // the click scrolls the rectangle on page 2 into view (goTo), placed on the undrawn page by percentages of its box
  const rect = h.rect(c2.id)!;
  assert.ok(rect, "the rectangle sits on the undrawn page");
  line.dispatch("click");
  assert.equal(rect.scrolled, 1, "the rectangle was scrolled into view: the page nears the reader, and the chunk draws it");
  assert.ok(h.wait(c2.id), "until the draw, the line stays");
  // Enter on the focused line is the same click (KEY_ACTS)
  line.focus();
  assert.equal(doc.activeElement, line);
  const ev = line.dispatch("keydown", { key: "Enter" });
  assert.equal(ev.defaultPrevented, true);
  assert.equal(rect.scrolled, 2);
  // the chunk drew the page: onPage → fireRendered → the repaint cuts the crop and the line goes
  h.draw(2); h.repaint();
  const cut = h.crop(c2.id)!;
  assert.ok(cut, "the crop comes with the draw's repaint");
  assert.equal(h.wait(c2.id), null, "…and the line goes");
  assert.equal(drawn[drawn.length - 1][0], h.pages[1].querySelector("canvas"), "cut from page 2's canvas");
  assert.ok(h.card(c2.id)!.childNodes[1] === cut, "in the same place");
  h.dispose();
});

test("the line appears only for a mounted page with a canvas and no bitmap: a drawn page crops, a failed page wears its tag, a gone page wears stale, a kept crop stands in for an evicted page until the file changes", async () => {
  drawn.length = 0;
  const h = await harness(["drawn", "failed", "undrawn"]);          // page 4 has no shell: the regenerated document lost it
  const cs = [pageComment(1), pageComment(2), pageComment(3), pageComment(4)];
  await h.ok(withStore(cs));
  await h.open(withStore(cs));
  for (const c of cs) h.expand(c.id);
  // page 1, drawn: the crop, no line
  assert.ok(h.crop(idFor(1)), "page 1's crop");
  assert.equal(h.wait(idFor(1)), null);
  // page 2, failed (no canvas): its own tag and reference, no line — the page is not one that will draw on a scroll
  assert.equal(h.crop(idFor(2)), null);
  assert.equal(h.wait(idFor(2)), null, "a failed page is not 'not drawn yet'");
  assert.deepEqual(h.tags(idFor(2)), ["not rendered"]);
  // page 3, undrawn: the line
  assert.equal(h.crop(idFor(3)), null);
  assert.equal(h.wait(idFor(3))!.textContent, "Page 3 is not drawn yet. Go to the page to see this region.");
  // page 4, gone (no shell): stale, no line — there is no page to scroll to
  assert.equal(h.crop(idFor(4)), null);
  assert.equal(h.wait(idFor(4)), null, "a page the document no longer has cannot be scrolled in");
  assert.deepEqual(h.tags(idFor(4)), ["stale"]);
  // page 1 evicted (a 0×0 canvas): the kept crop stands, so no line
  const kept = h.crop(idFor(1))!;
  h.evict(1); h.repaint();
  assert.equal(h.crop(idFor(1)), kept, "the kept crop: the same bytes, the same picture");
  assert.equal(h.wait(idFor(1)), null, "a card with a crop needs no line");
  // the PDF regenerated while page 1 is still evicted: the kept crop is dropped (it shows bytes the file no longer has)
  // and the line takes its place — a scroll draws the new page 1, and the fresh crop comes with it
  await h.restatus({ ...withStore(cs), fileHash: H2 });
  assert.equal(h.crop(idFor(1)), null, "dropped with the file's hash");
  assert.equal(h.wait(idFor(1))!.textContent, "Page 1 is not drawn yet. Go to the page to see this region.");
  h.draw(1); h.repaint();
  assert.ok(h.crop(idFor(1)), "cut fresh on the draw");
  assert.notEqual(h.crop(idFor(1)), kept);
  assert.equal(h.wait(idFor(1)), null);
  h.dispose();
});

test("source pins: the line takes the crop's place only when nothing was cut and the page has a canvas without a bitmap, and it is a fcgoto control", () => {
  const SRC = web("file-comments.ts");
  assert.match(SRC, /if \(crop\) card\.appendChild\(crop\);\n\s*else if \(c\.target && this\.pageUndrawn\(c\)\) card\.appendChild\(this\.cropWaitNote\(c\)\);/,
    "the slot: the crop when there is one, else the line for an undrawn page, else nothing");
  assert.match(SRC, /private pageUndrawn\(c: Card\): boolean \{\n\s*const shell = this\.pageShellFor\(c\);\n\s*if \(!shell\) return false;\n\s*const canvas = shell\.querySelector\("canvas\.fileview-pdf-canvas"\);\n\s*return isCanvas\(canvas\) && !\(canvas\.width > 0 && canvas\.height > 0\);/,
    "undrawn: a mounted shell whose canvas is there and has no bitmap (never a failed page, whose canvas the chunk removed)");
  assert.match(SRC, /n\.dataset\.act = "fcgoto"; n\.dataset\.id = c\.id;/, "the line reaches the page the way the reference does");
  assert.match(SRC, /n\.tabIndex = 0; n\.setAttribute\("role", "button"\);/, "a Tab stop, Enter through KEY_ACTS");
  assert.match(SRC, /const KEY_ACTS = new Set\(\[[^\]]*"fcgoto"/, "fcgoto is a keyboard act");
  assert.match(SRC, /el\("div", "fc-note fc-link fc-crop-wait", /, "the panel's note size and link treatment: no new font size (ui\/CLAUDE.md)");
});
