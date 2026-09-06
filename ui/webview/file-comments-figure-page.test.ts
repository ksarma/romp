// A rendered figure whose markup carries `data-page` is NOT a PDF page (plans/file-review.md, Slice 4; contract F4:
// kind "pdf" means a page of a PDF file). The sanitizer keeps a figure's data-* attributes, so a raw
// `<img src="figure.png" data-page="2">` a session wrote into markdown reached pageOf() as page 2: the composer said
// "of page 2", regionTarget dropped the embed's src for kind "pdf", the Re-place own-picture guard was bypassed, and
// the host then refused the comment for the missing src — a misleading composer and a comment that could not be saved.
// Only the chunk's own carriers name a page: canvas.fileview-pdf-canvas and its shell div.fileview-pdf-page. Driven end
// to end through the DOM stand-in of file-comments-regions.test.ts (copied: each test file is its own bundle).
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
  listeners = new Map<string, Array<(ev: unknown) => void>>();
  constructor() { this.body = new E(this, "BODY"); }
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
    for (const c of this.childNodes) c.parentNode = null;
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
  hidden = false; title = ""; type = ""; disabled = false; placeholder = ""; value = ""; checked = false; offsetWidth = 0; tabIndex = -1;
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
  private classes(): string[] { return (this.attrs.get("class") || "").split(/\s+/).filter(Boolean); }
  private setClasses(c: string[]): void { this.attrs.set("class", [...new Set(c)].join(" ")); }
  get className(): string { return this.attrs.get("class") || ""; }
  set className(v: string) { this.attrs.set("class", v); }
  set innerHTML(html: string) { this.replaceChildren(...parseHTML(this.ownerDocument, html)); }
  getAttribute(n: string): string | null { return this.attrs.has(n) ? (this.attrs.get(n) as string) : null; }
  setAttribute(n: string, v: string): void { this.attrs.set(n, v); }
  removeAttribute(n: string): void { this.attrs.delete(n); }
  removeChild(n: N): N { const i = this.childNodes.indexOf(n); if (i >= 0) this.childNodes.splice(i, 1); n.parentNode = null; return n; }
  appendChild<X extends N>(n: X): X { if (n.parentNode) (n.parentNode as E).removeChild(n); this.childNodes.push(n); n.parentNode = this; return n; }
  insertBefore(n: N, ref: N | null): N {
    if (!ref) return this.appendChild(n);
    if (n.parentNode) (n.parentNode as E).removeChild(n);
    const i = this.childNodes.indexOf(ref);
    this.childNodes.splice(i, 0, n); n.parentNode = this; return n;
  }
  replaceChildren(...c: N[]): void { for (const x of this.childNodes) x.parentNode = null; this.childNodes = []; for (const x of c) this.appendChild(x); }
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
  focus(): void { /* inert */ }
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
const PNG = "/repo/notes-api/docs/figure.png";
const MD = "/repo/notes-api/docs/report.md";
const T0 = 1757145600000;
const H1 = "1111111111111111111111111111111111111111111111111111111111111111";
const H2 = "2222222222222222222222222222222222222222222222222222222222222222";
// the figure: a 600×400 picture drawn at half size, 100px in and 200px down
const IMG_RECT = rectOf(100, 200, 300, 200);
const REGION = { x: 0.1667, y: 0.2, w: 0.3333, h: 0.3 };   // the drag from (150,240) to (250,300) over IMG_RECT
const regionComment = (over: Partial<StoreComment> = {}, target: Record<string, unknown> = {}): StoreComment => ({
  id: T0 + "-0", author: "you", ts: T0, body: "The axis label is wrong.", replies: [], resolved: false,
  target: { kind: "image", region: REGION, hash: H1, ...target } as StoreComment["target"], ...over,
});
function pngStatus(over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: "/repo/notes-api", storePath: "/repo/notes-api/.trackchanges/docs%2Ffigure.png.json",
    trackedBy: null, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: null, configMtimeNs: null,
    store: null, hunks: [], log: [], unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null },
    fileHash: H1,
    ...over,
  };
}
const withStore = (comments: StoreComment[], path = "docs/figure.png"): Partial<Status> => ({
  storeMtimeNs: "1757145600000000002", store: { v: 3, path, suggestions: [], comments },
  unsent: { comments: comments.map((c) => c.id), replies: [], accepted: 0, rejected: 0, watermark: null },
});

// ── the harness ────────────────────────────────────────────────────────────────────────────────────
type Posted = Record<string, any>;
// the PDF's pages (Slice 4): two US-letter pages drawn at 306×396 CSS px (the 612×792 backing store at half size),
// stacked 20px apart from (100, 200); a drag from (150, 240) to (250, 300) over page 1 is REGION again
const PAGE_RECTS = [rectOf(100, 200, 306, 396), rectOf(100, 616, 306, 396)];
const PDF = "/repo/notes-api/docs/deck.pdf";
/** A mounted panel over a media body (`kind: "media"`: `.fileview-imgbox > img.fileview-img`; `kind: "pdf"`: the chunk's
 *  `.fileview-pdfhost > .fileview-pdf > .fileview-pdf-page[data-page] > canvas.fileview-pdf-canvas`, two pages) or a
 *  rendered-markdown body (`html` + `src`), inside the viewer's body row. */
async function harness(over: Partial<FileViewActionCtx> & { kind?: "media" | "pdf" | "rendered"; html?: string; src?: string; imgSrc?: string } = {}) {
  const fc = await import("./file-comments");
  const { kind = "media", html, src, imgSrc, ...ctxOver } = over;
  const main = doc.createElement("div"); main.className = "fileview-main";
  const body = doc.createElement("div"); body.className = "fileview-body"; main.appendChild(body);
  let media: E | null = null;
  let pages: E[] = [];
  if (kind === "pdf") {
    const host = doc.createElement("div"); host.className = "fileview-pdfhost";
    media = doc.createElement("div"); media.className = "fileview-pdf";
    PAGE_RECTS.forEach((rect, i) => {
      const w = doc.createElement("div"); w.className = "fileview-pdf-page"; w.dataset.page = String(i + 1); w.style.position = "relative"; w.rect = rect;
      const c = doc.createElement("canvas"); c.className = "fileview-pdf-canvas"; c.dataset.page = String(i + 1); c.rect = rect; c.width = 612; c.height = 792;
      w.appendChild(c); media!.appendChild(w); pages.push(w);
    });
    host.appendChild(media); body.appendChild(host);
  } else if (kind === "media") {
    const box = doc.createElement("div"); box.className = "fileview-imgbox";
    media = doc.createElement("img"); media.className = "fileview-img"; media.setAttribute("src", imgSrc || "blob:romp/figure");
    media.rect = IMG_RECT; media.naturalWidth = 600; media.naturalHeight = 400; media.complete = true;
    box.appendChild(media); body.appendChild(box);
  } else if (html !== undefined) {
    const md = doc.createElement("div"); md.className = "fileview-md"; md.innerHTML = html; body.appendChild(md);
    for (const img of md.querySelectorAll("img")) { img.rect = IMG_RECT; img.naturalWidth = 600; img.naturalHeight = 400; img.complete = true; }
  }
  const posted: Posted[] = [];
  const closers: Array<() => void> = [];
  const saved: Array<(info: { mtimeNs: string; logged: boolean }) => void> = [];
  const rendered: Array<() => void> = [];
  const modes: string[] = [];
  let aside: E | null = null;
  const noop = () => { /* inert */ };
  const ctx: FileViewActionCtx = {
    path: kind === "media" ? PNG : kind === "pdf" ? PDF : MD, sid: SID, todoId: null,
    body: () => body as unknown as HTMLElement,
    mode: () => (kind === "rendered" ? "rendered" : "media"),
    text: () => (kind === "rendered" && src !== undefined ? src : null),
    mtimeNs: () => "1757145600000000001",
    media: () => (kind === "media" ? "image" : kind === "pdf" ? "pdf" : null),
    mediaElement: () => media as unknown as HTMLElement | null, renderedImages: () => [],
    pdfPages: () => pages as unknown as HTMLElement[],
    identity: () => ({ name: "api", color: null }),
    onRendered: (cb) => { rendered.push(cb); }, onSelection: noop, onSaved: (cb) => { saved.push(cb); }, onClose: (cb) => { closers.push(cb); },
    post: (m) => { posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: noop,
    aside: (el) => { if (el) { aside = el as unknown as E; main.appendChild(aside); } else if (aside) { aside.remove(); aside = null; } },
    setMode: (m) => { modes.push(m); }, scrollToOffset: noop, reload: noop,
    ...ctxOver,
  };
  const unit = fc.fileCommentsAction.mount(ctx) as unknown as E;
  const button = unit.childNodes[0] as E;
  const last = (): Posted => posted[posted.length - 1];
  const reply = async (data: Record<string, unknown>) => { win.dispatchEvent(new MessageEvent("message", { data })); await tick(); await tick(); };
  const status = kind === "media" ? pngStatus
    : kind === "pdf" ? (o: Partial<Status> = {}) => pngStatus({ storePath: "/repo/notes-api/.trackchanges/docs%2Fdeck.pdf.json", ...o })
    : (o: Partial<Status> = {}) => pngStatus({ storePath: "/repo/notes-api/.trackchanges/docs%2Freport.md.json", fileHash: undefined, ...o });
  return {
    fc, main, body, unit, button, posted, modes, saved, rendered, last, media, pages,
    ok: (o: Partial<Status> = {}) => reply({ type: "fileCommentsResult", reqId: last().reqId, ...status(o) }),
    refuse: (code: string, error: string) => reply({ type: "fileCommentsFailed", reqId: last().reqId, verb: last().verb, code, error }),
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
    open: async (o: Partial<Status> = {}) => { button.dispatch("click"); await reply({ type: "fileCommentsResult", reqId: last().reqId, ...status(o) }); },
    /** A fresh status the way the poll or a save brings one: the onSaved hook re-asks, the reply lands. */
    restatus: async (o: Partial<Status> = {}) => { saved[0]({ mtimeNs: "1757145600000000001", logged: true }); await tick(); await reply({ type: "fileCommentsResult", reqId: last().reqId, ...status(o) }); },
    float: () => { const f = doc.body.querySelectorAll(".fc-float"); return f[f.length - 1]; },
    input: () => main.querySelector("input.fc-input")!,
    dispose: () => { for (const cb of closers) cb(); },
  };
}

// ── pageOf: the chunk's carriers only ──────────────────────────────────────────────────────────────

test("pageOf: a page for the chunk's canvas or its shell; null for an <img> or any other element, whatever data-page it carries", async () => {
  const { pageOf } = await import("./file-comments");
  const canvas = doc.createElement("canvas"); canvas.className = "fileview-pdf-canvas"; canvas.dataset.page = "2";
  const shell = doc.createElement("div"); shell.className = "fileview-pdf-page"; shell.dataset.page = "3";
  assert.equal(pageOf(canvas as unknown as Element), 2, "the page's canvas");
  assert.equal(pageOf(shell as unknown as Element), 3, "the page's shell");
  const img = doc.createElement("img"); img.setAttribute("src", "figure.png"); img.dataset.page = "2";
  assert.equal(pageOf(img as unknown as Element), null, "an <img> is never a PDF page, whatever its markup says");
  const div = doc.createElement("div"); div.dataset.page = "2";
  assert.equal(pageOf(div as unknown as Element), null, "a div that is not the chunk's shell carries no page");
  const p = doc.createElement("p"); p.className = "fileview-pdf-page-err"; p.dataset.page = "2";
  assert.equal(pageOf(p as unknown as Element), null, "a class that merely starts like the shell's is not the shell");
  for (const bad of ["0", "-1", "1.5", "two", ""]) {
    const c = doc.createElement("canvas"); c.className = "fileview-pdf-canvas"; c.dataset.page = bad;
    assert.equal(pageOf(c as unknown as Element), null, "a carrier without a positive integer: " + JSON.stringify(bad));
  }
  const bare = doc.createElement("canvas"); bare.className = "fileview-pdf-canvas";
  assert.equal(pageOf(bare as unknown as Element), null, "a carrier with no data-page");
  assert.equal(pageOf(null), null); assert.equal(pageOf(undefined), null);
});

// ── a rendered figure written as raw HTML with data-page ───────────────────────────────────────────
// marked passes a raw <img> tag through verbatim and the sanitizer keeps its data-* attributes, so the rendered figure
// carries data-page="2" exactly as the source wrote it.
const RAW_IMG = '<img src="figure.png" alt="Figure" data-page="2">';
const RAW_REPORT = "## Findings\n\n" + RAW_IMG + "\n\nWe recommend shipping the cache in v1.2.\n";
const RAW_HTML = "<h2>Findings</h2>\n" + RAW_IMG + "\n<p>We recommend shipping the cache in v1.2.</p>\n";
const rawEmbedded = (over: Partial<StoreComment> = {}, target: Record<string, unknown> = {}): StoreComment => regionComment({
  anchor: { quote: RAW_IMG, prefix: "## Findings\n\n", suffix: "\n\nWe recommend shipping " }, ...over,
}, { src: "figure.png", ...target });

test("a rendered figure carrying data-page: the composer names no page, and Enter saves target {kind image, src} with the embed's anchor — never kind pdf on a markdown file", async () => {
  drawn.length = 0;
  const h = await harness({ kind: "rendered", html: RAW_HTML, src: RAW_REPORT });
  await h.ok({ embeddedHashes: {} });
  await h.open({ embeddedHashes: {} });
  const img = h.q(".fileview-md img")!;
  assert.equal(img.dataset.page, "2", "the fixture's premise: the rendered figure carries the attribute");
  const overlay = (img.parentNode as E).querySelector(".fc-overlay")!;
  assert.equal(overlay.getAttribute("aria-label"), "Drag to comment on a region of the image", "the overlay knows a picture, not a page");
  h.drag(overlay, [150, 240], [250, 300]);
  assert.equal(h.q(".fc-composer")!.hidden, false);
  assert.equal(h.q(".fc-composer-ref .fc-note")!.textContent, "On the region at 0.17, 0.20, 0.33, 0.30", "no 'of page 2': the figure is not a PDF page");
  assert.ok(h.q('.fc-composer [data-act="fcsave"]'), "Save offered: the embed line anchors the region");
  h.input().value = "The axis label is wrong.";
  h.input().dispatch("keydown", { key: "Enter" });
  await tick();
  const c = h.last();
  assert.equal(c.verb, "comment");
  assert.deepEqual(c.args.target, { kind: "image", region: REGION, src: "figure.png" }, "kind image with the embed's src (E1/E4), no page");
  assert.deepEqual(c.args.anchor, { quote: RAW_IMG, prefix: "## Findings\n\n", suffix: "\n\nWe recommend shipping " }, "the raw tag is the embed line");
  assert.equal(c.args.hintOffset, RAW_REPORT.indexOf("<img"));
  // the saved comment paints back on the figure and follows embeddedHashes, as any embedded figure's does
  await h.ok({ ...withStore([rawEmbedded()], "docs/report.md"), embeddedHashes: { "figure.png": H1 } });
  const rect = overlay.querySelector('.fc-region[data-id="' + T0 + '-0"]')!;
  assert.ok(rect, "the rectangle on the figure");
  assert.equal(rect.classList.contains("fc-stale"), false);
  assert.equal(h.q('.fc-card[data-id="' + T0 + '-0"] .fc-ref')!.textContent, "the region at 0.17, 0.20, 0.33, 0.30", "the card names no page either");
  await h.restatus({ ...withStore([rawEmbedded()], "docs/report.md"), embeddedHashes: { "figure.png": H2 } });
  assert.equal(overlay.querySelector('.fc-region[data-id="' + T0 + '-0"]')!.classList.contains("fc-stale"), true, "staleness reads embeddedHashes by src");
  h.dispose();
});

test("Re-place on a rendered figure carrying data-page keeps the own-picture guard: another figure is refused, its own retargets kind image with the src", async () => {
  drawn.length = 0;
  const two = "<p>" + RAW_IMG + '</p>\n<p><img src="other.png" alt="Other" data-page="1"></p>\n';
  const src = RAW_IMG + '\n\n<img src="other.png" alt="Other" data-page="1">\n';
  const h = await harness({ kind: "rendered", html: two, src });
  const cm = rawEmbedded({ anchor: { quote: RAW_IMG, prefix: "", suffix: '\n\n<img src="other.png" alt' } });
  await h.ok({ ...withStore([cm], "docs/report.md"), embeddedHashes: { "figure.png": H1 } });
  await h.open({ ...withStore([cm], "docs/report.md"), embeddedHashes: { "figure.png": H1 } });
  const [fig, other] = h.qa(".fileview-md img");
  assert.equal(fig.dataset.page, "2"); assert.equal(other.dataset.page, "1");
  h.click('.fc-card[data-id="' + T0 + '-0"] .fc-card-head');
  h.click('.fc-card.open [data-act="fcreplace"]');
  assert.equal((fig.parentNode as E).querySelector(".fc-overlay")!.classList.contains("fc-replacing"), true, "the cue on the comment's own figure");
  const before = h.posted.length;
  h.drag((other.parentNode as E).querySelector(".fc-overlay")!, [150, 240], [250, 300]);
  assert.equal(h.posted.length, before, "nothing sent: a figure's data-page does not make it a page a re-place may land on");
  assert.equal(h.q(".fc-card.open .fc-err")!.childNodes[0].textContent, "Draw the new place on the figure this comment is on, not on another one.");
  h.drag((fig.parentNode as E).querySelector(".fc-overlay")!, [150, 240], [250, 300]);
  await tick();
  assert.equal(h.last().verb, "retarget");
  assert.deepEqual(h.last().args, { commentId: T0 + "-0", target: { kind: "image", region: REGION, src: "figure.png" } }, "kind image, the src along, no page");
  h.dispose();
});

test("the chunk's pages still name theirs: a drag on page 2's canvas sends target {kind pdf, page 2}", async () => {
  drawn.length = 0;
  const h = await harness({ kind: "pdf" });
  await h.ok();
  await h.open();
  const overlays = h.qa(".fileview-pdf-page .fc-overlay");
  assert.equal(overlays.length, 2, "one overlay per page");
  h.drag(overlays[1], [150, 656], [250, 716]);
  assert.equal(h.q(".fc-composer-ref .fc-note")!.textContent, "On the region at 0.16, 0.10, 0.33, 0.15 of page 2");
  h.input().value = "Crop the header.";
  h.input().dispatch("keydown", { key: "Enter" });
  await tick();
  assert.equal(h.last().verb, "comment");
  assert.deepEqual(h.last().args.target, { kind: "pdf", region: { x: 0.1634, y: 0.101, w: 0.3268, h: 0.1515 }, page: 2 });
  assert.equal(h.last().args.anchor, undefined, "a PDF region has no anchor");
  h.dispose();
});

test("source pin: pageOf reads data-page only off a canvas or the chunk's shell", () => {
  const SRC = web("file-comments.ts");
  assert.match(SRC, /export function pageOf\(el: Element \| null \| undefined\): number \| null \{\n\s*if \(!el\) return null;\n\s*const cl = el\.classList;\n\s*const shell = !!cl && typeof cl\.contains === "function" && cl\.contains\("fileview-pdf-page"\);\n\s*if \(!isCanvas\(el\) && !shell\) return null;/,
    "an element that is neither the page's canvas nor its shell carries no page, whatever its data-page says");
});
