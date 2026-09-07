// Region comments on images — the 2026-09-06 review's third round on the panel (plans/file-review.md, Slice 3;
// file-comments.ts), driven end to end through the DOM stand-in file-comments-regions-review.test.ts drives the first
// round with (a focus model, document listeners with a capture phase, an element's click()), the fixtures the same:
// the notes-api world, placeholder ids. What this round covers, each behavioural — a mutant that drops the branch under
// test fails here:
//   • embedFor and imgForRange pair a figure with the embed spelled as its OWN destination (the authored spelling the
//     viewer keeps in data-fv-src beside a src it rewrote through /file), twins by order, and are each other's inverse —
//     for one file embedded under two spellings (`./fig.png` and `fig.png`), which the rewrite made two different srcs
//     that normalize to one path: a region drawn on the second figure was anchored to the first's embed line, and the
//     second embed's rectangle was painted on the first figure;
//   • a resolved region comment wears "resolved" alone: no stale tag (whose title names Re-place), no unknown tag or
//     note, no Re-place button, no rectangle — the plan and the guide end "stale" at resolve or re-place;
//   • the panel over a PDF body: the browser's frame takes no layer (Slice 4 renders pages), so no overlay, no drag
//     offered, and a whole-file comment still renders as a card;
//   • a pending region on a standalone image survives the poll's reload of the picture: the composer's rectangle and
//     thumbnail move to the NEW <img>, and Save posts the region;
//   • a rectangle on a LINKED figure (`[![alt](fig.png)](url)`, which mdBlock gives target=_blank): its click, Enter and
//     the handed-on press open the card and cancel the anchor's activation — no new tab; the file's own markup wearing
//     the same data-act is left alone;
//   • the same figure under the CHAT pane's document-level link handler (render.ts), which opens every absolute `a[href]`
//     at the capture phase, before the delegate root: it asks the panel's registry (panelMark) and leaves the panel's
//     marks — the rectangle, its chip, the overlay a press was handed on from — to the panel, while the file's own link
//     still opens; before, the tab opened and no card did.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import type { FileViewActionCtx } from "./file-view";
import type { Status, StoreComment } from "./file-comments-model";

// ── the DOM stand-in ───────────────────────────────────────────────────────────────────────────────
type Rect = { left: number; top: number; right: number; bottom: number; width: number; height: number };
const rectOf = (left: number, top: number, width: number, height: number): Rect => ({ left, top, width, height, right: left + width, bottom: top + height });
const ZERO = rectOf(0, 0, 0, 0);
type Listener = { fn: (ev: Ev) => void; capture: boolean };
class Doc {
  body: E;
  hidden = false;
  /** the focused element: the body until something takes focus, and again once the focused element leaves the tree */
  activeElement: E;
  listeners = new Map<string, Listener[]>();
  constructor() { this.body = new E(this, "BODY"); this.activeElement = this.body; }
  createElement(tag: string): E { return new E(this, tag.toUpperCase()); }
  createTextNode(s: string): T { return new T(this, s); }
  getElementById(): null { return null; }
  addEventListener(type: string, fn: (ev: Ev) => void, opts?: boolean | { capture?: boolean }): void {
    const capture = typeof opts === "boolean" ? opts : !!(opts && opts.capture);
    (this.listeners.get(type) || this.listeners.set(type, []).get(type)!).push({ fn, capture });
  }
  removeEventListener(type: string, fn: (ev: Ev) => void): void { const l = this.listeners.get(type); if (l) { const i = l.findIndex((x) => x.fn === fn); if (i >= 0) l.splice(i, 1); } }
  /** An event at `target`, dispatched as a browser would (E.dispatch). */
  fire(type: string, target: E, init: Init = {}): Ev { return target.dispatch(type, init); }
  /** A node left the tree: a focused element inside it loses focus to the body (the browser's focus fixup). */
  left(n: N): void { if (n.contains(this.activeElement)) this.activeElement = this.body; }
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
  hidden = false; title = ""; type = ""; disabled = false; placeholder = ""; value = ""; checked = false; offsetWidth = 0; tabIndex = -1; readOnly = false;
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
  removeChild(n: N): N { const i = this.childNodes.indexOf(n); if (i >= 0) this.childNodes.splice(i, 1); n.parentNode = null; this.ownerDocument.left(n); return n; }
  appendChild<X extends N>(n: X): X { if (n.parentNode) (n.parentNode as E).removeChild(n); this.childNodes.push(n); n.parentNode = this; return n; }
  insertBefore(n: N, ref: N | null): N {
    if (!ref) return this.appendChild(n);
    if (n.parentNode) (n.parentNode as E).removeChild(n);
    const i = this.childNodes.indexOf(ref);
    this.childNodes.splice(i, 0, n); n.parentNode = this; return n;
  }
  replaceChildren(...c: N[]): void { for (const x of this.childNodes) { x.parentNode = null; this.ownerDocument.left(x); } this.childNodes = []; for (const x of c) this.appendChild(x); }
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
  /** Dispatch as a browser does: the document's capture listeners, then this element and its ancestors, then the
   *  document's bubble listeners — each stage skipped once propagation is stopped. */
  dispatch(type: string, init: Init = {}): Ev {
    let stopped = false;
    const ev: Ev = { ...init, type, target: this, currentTarget: null, defaultPrevented: false,
      preventDefault() { this.defaultPrevented = true; }, stopPropagation() { stopped = true; } };
    const doc = this.ownerDocument;
    const at = doc.listeners.get(type) || [];
    for (const l of [...at]) if (l.capture) l.fn(ev);
    for (let n: N | null = this; n && !stopped; n = n.parentNode) {
      if (!(n instanceof E)) continue;
      ev.currentTarget = n;
      for (const fn of [...(n.listeners.get(type) || [])]) fn(ev);
    }
    if (!stopped) for (const l of [...at]) if (!l.capture) l.fn(ev);
    return ev;
  }
  /** HTMLElement.click(): a synthetic click that bubbles like a real one. */
  click(): void { this.dispatch("click"); }
  focus(): void { this.ownerDocument.activeElement = this; }
  blur(): void { if (this.ownerDocument.activeElement === this) this.ownerDocument.activeElement = this.ownerDocument.body; }
  /** The rect a test gave the element; a wrapper hugs its picture (the sheet's inline-block around a block img). */
  getBoundingClientRect(): Rect {
    if (this.rect) return this.rect;
    if (this.classList.contains("fc-imgwrap")) { const img = this.childNodes.find((c) => c instanceof E && c.tagName === "IMG") as E | undefined; return img ? img.getBoundingClientRect() : ZERO; }
    return ZERO;
  }
  setPointerCapture(): void { /* inert: the tests dispatch the release and the click where a capturing browser sends them */ }
  releasePointerCapture(): void { /* inert */ }
  getContext(): { drawImage(...a: unknown[]): void } | null {
    return this.tagName === "CANVAS" ? { drawImage: (...a: unknown[]) => { drawn.push(a); } } : null;
  }
  scrollIntoView(): void { this.scrolled++; }
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
/** The kernel a test stands up: a 404 to every HEAD and no sessions, unless the test says otherwise. */
type Fetch = (url: string, init?: { method?: string }) => Promise<unknown>;
const noKernel: Fetch = async () => ({ status: 404, headers: { get: () => null }, json: async () => [] });
let fetchImpl: Fetch = noKernel;
(globalThis as any).fetch = (url: string, init?: { method?: string }) => fetchImpl(url, init);
const realSetInterval = globalThis.setInterval;
(globalThis as any).setInterval = (fn: () => void, ms: number) => { const t = realSetInterval(fn, ms); (t as any).unref?.(); return t; };
const tick = () => new Promise<void>((r) => setImmediate(r));
const flush = async (n = 3) => { for (let i = 0; i < n; i++) await tick(); };
// the viewer persists its view choices in localStorage (file-view.ts), read behind a try/catch; the stand-in gives it one
const store = new Map<string, string>();
(globalThis as any).localStorage = {
  getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
  setItem: (k: string, v: string) => { store.set(k, String(v)); },
  removeItem: (k: string) => { store.delete(k); },
};

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const PNG = "/repo/notes-api/docs/figure.png";
const PDF = "/repo/notes-api/docs/deck.pdf";
const MD = "/repo/notes-api/docs/report.md";
const DIR = "/repo/notes-api/docs/";
const STORE_MD = "/repo/notes-api/.trackchanges/docs%2Freport.md.json";
const STORE_PDF = "/repo/notes-api/.trackchanges/docs%2Fdeck.pdf.json";
const T0 = 1757145600000;
const H1 = "1111111111111111111111111111111111111111111111111111111111111111";
const H2 = "2222222222222222222222222222222222222222222222222222222222222222";
// the figure: a 600×400 picture drawn at half size, 100px in and 200px down
const IMG_RECT = rectOf(100, 200, 300, 200);
const REGION = { x: 0.1667, y: 0.2, w: 0.3333, h: 0.3 };   // the drag from (150,240) to (250,300) over IMG_RECT
const RID = T0 + "-0";
const regionComment = (over: Partial<StoreComment> = {}, target: Record<string, unknown> = {}): StoreComment => ({
  id: RID, author: "you", ts: T0, body: "The axis label is wrong.", replies: [], resolved: false,
  target: { kind: "image", region: REGION, hash: H1, ...target } as StoreComment["target"], ...over,
});
type Extra = Partial<Status> & Record<string, unknown>;
function pngStatus(over: Extra = {}): Status {
  return {
    verb: "status", root: "/repo/notes-api", storePath: "/repo/notes-api/.trackchanges/docs%2Ffigure.png.json",
    trackedBy: null, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: null, configMtimeNs: null,
    store: null, hunks: [], log: [], unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null },
    fileHash: H1,
    ...over,
  } as Status;
}
const withStore = (comments: StoreComment[], path = "docs/figure.png"): Extra => ({
  storeMtimeNs: "1757145600000000002", store: { v: 3, path, suggestions: [], comments },
  unsent: { comments: comments.map((c) => c.id), replies: [], accepted: 0, rejected: 0, watermark: null },
});
const figureStatus = (comments: StoreComment[], hashes: Record<string, string | null> = { "figure.png": H1 }): Extra => ({ ...withStore(comments, "docs/report.md"), embeddedHashes: hashes });
/** A region comment on the report's figure, the way the drag saves it: the embed line's anchor (makeAnchor over the
 *  source, as saveComposer builds it) and target.src as the embed writes it. */
async function embeddedOn(text: string, embed: string, over: Partial<StoreComment> = {}, src = "figure.png"): Promise<StoreComment> {
  const { makeAnchor } = await import("./anchor-map");
  const start = text.indexOf(embed);
  assert.ok(start >= 0, "the fixture embeds " + embed);
  return regionComment({ anchor: makeAnchor(text, { start, end: start + embed.length }), ...over }, { src });
}

// ── the harness ────────────────────────────────────────────────────────────────────────────────────
type Posted = Record<string, any>;
const mk = (tag: string, cls: string): E => { const e = doc.createElement(tag); e.className = cls; return e; };
const picture = (img: E, loading: boolean): void => { img.rect = IMG_RECT; img.naturalWidth = 600; img.naturalHeight = 400; img.complete = !loading; };
/** A mounted panel over a media body — an image (`kind: "media"`: `.fileview-imgbox > img.fileview-img`) or a PDF
 *  (`kind: "pdf"`: the browser's `iframe.fileview-frame`, as pdfBlock builds it) — or a rendered-markdown body (`html` +
 *  `src`; `prepare` runs over the built `.fileview-md` before the panel mounts, the way the viewer's own rewrite does),
 *  inside the viewer's body row. `loading` leaves the pictures undecoded (complete = false). */
async function harness(over: Partial<FileViewActionCtx> & { kind?: "media" | "pdf" | "rendered"; html?: string; src?: string; loading?: boolean; prepare?: (md: E) => void } = {}) {
  const fc = await import("./file-comments");
  const { kind = "media", html, src, loading = false, prepare, ...ctxOver } = over;
  const main = mk("div", "fileview-main");
  const body = mk("div", "fileview-body"); main.appendChild(body);
  let media: E | null = null;
  if (kind === "media") {
    const box = mk("div", "fileview-imgbox");
    media = mk("img", "fileview-img"); media.setAttribute("src", "blob:romp/figure");
    picture(media, loading);
    box.appendChild(media); body.appendChild(box);
  } else if (kind === "pdf") {
    media = mk("iframe", "fileview-frame"); media.setAttribute("src", "blob:romp/deck"); media.rect = rectOf(0, 0, 800, 600);
    body.appendChild(media);
  } else if (html !== undefined) {
    const md = mk("div", "fileview-md"); md.innerHTML = html; body.appendChild(md);
    if (prepare) prepare(md);
    for (const img of md.querySelectorAll("img")) picture(img, loading);
  }
  const posted: Posted[] = [];
  const closers: Array<() => void> = [];
  const saved: Array<(info: { mtimeNs: string; logged: boolean }) => void> = [];
  const rendered: Array<() => void> = [];
  const modes: string[] = [];
  let reloads = 0;
  let aside: E | null = null;
  const noop = () => { /* inert */ };
  const ctx: FileViewActionCtx = {
    path: kind === "media" ? PNG : kind === "pdf" ? PDF : MD, sid: SID, todoId: null,
    body: () => body as unknown as HTMLElement,
    mode: () => (kind === "rendered" ? "rendered" : "media"),
    text: () => (kind === "rendered" && src !== undefined ? src : null),
    mtimeNs: () => "1757145600000000001",
    media: () => (kind === "media" ? "image" : kind === "pdf" ? "pdf" : null),
    pdfPages: () => [],                              // the Slice 4 seam member: these harnesses mount no PDF pages
    mediaElement: () => media as unknown as HTMLElement | null, renderedImages: () => [],
    identity: () => ({ name: "api", color: null }),
    onRendered: (cb) => { rendered.push(cb); }, onSelection: noop, onSaved: (cb) => { saved.push(cb); }, onClose: (cb) => { closers.push(cb); },
    post: (m) => { posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: noop,
    aside: (el) => { if (el) { aside = el as unknown as E; main.appendChild(aside); } else if (aside) { aside.remove(); aside = null; } },
    setMode: (m) => { modes.push(m); }, scrollToOffset: noop, reload: () => { reloads++; },
    ...ctxOver,
  };
  const unit = fc.fileCommentsAction.mount(ctx) as unknown as E;
  const button = unit.childNodes[0] as E;
  const last = (): Posted => posted[posted.length - 1];
  const reply = async (data: Record<string, unknown>) => { win.dispatchEvent(new MessageEvent("message", { data })); await tick(); await tick(); };
  const status = (o: Extra = {}): Status => (kind === "media" ? pngStatus(o) : kind === "pdf" ? pngStatus({ storePath: STORE_PDF, ...o }) : pngStatus({ storePath: STORE_MD, fileHash: undefined, ...o }));
  return {
    fc, main, body, unit, button, posted, modes, saved, rendered, last, media, reloads: () => reloads,
    ok: (o: Extra = {}) => reply({ type: "fileCommentsResult", reqId: last().reqId, ...status(o) }),
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
    open: async (o: Extra = {}) => { button.dispatch("click"); await reply({ type: "fileCommentsResult", reqId: last().reqId, ...status(o) }); },
    /** A fresh status the way the poll or a save brings one: the onSaved hook re-asks, the reply lands. */
    restatus: async (o: Extra = {}) => { saved[0]({ mtimeNs: "1757145600000000001", logged: true }); await tick(); await reply({ type: "fileCommentsResult", reqId: last().reqId, ...status(o) }); },
    /** The tags on a card's head, in order. */
    tags: (id: string) => main.querySelector('.fc-card[data-id="' + id + '"] .fc-card-head')!.querySelectorAll(".fc-tag").map((t) => t.textContent),
    float: () => { const f = doc.body.querySelectorAll(".fc-float"); return f[f.length - 1]; },
    input: () => main.querySelector("input.fc-input")!,
    dispose: () => { for (const cb of closers) cb(); },
  };
}
/** The overlay a picture's layer put beside it. */
const overlayOf = (img: E): E => { const o = (img.parentNode as E).querySelector(".fc-overlay"); assert.ok(o, "a layer wraps the picture"); return o!; };

// ── one file embedded under two spellings ──────────────────────────────────────────────────────────

const TWO = "## Findings\n\n![a](./fig.png)\n\n![b](fig.png)\n\nShip it.\n";
const TWO_HTML = '<h2>Findings</h2>\n<p><img src="./fig.png" alt="a"></p>\n<p><img src="fig.png" alt="b"></p>\n<p>Ship it.</p>\n';   // marked keeps `./` as written

test("embedFor and imgForRange pair each figure with the embed spelled as its own destination once the viewer rewrote both srcs through /file: `./fig.png` and `fig.png` are two destinations with one picture each, in both directions; identical and percent-encoded twins pair by order; a spelling the source lacks is refused, not lent the other's embed", async () => {
  const fc = await import("./file-comments");
  const fv = await import("./file-view");
  const root = doc.createElement("div"); root.className = "fileview-md";
  root.innerHTML = TWO_HTML;
  fv.rewriteFigureSrcs(root as unknown as ParentNode, DIR, SID);        // the REAL rewrite, on the stand-in DOM
  const [i1, i2] = root.querySelectorAll("img");
  // the shape that broke it: two srcs, byte-different, naming ONE path — and the authored spellings kept beside them
  assert.notEqual(i1.getAttribute("src"), i2.getAttribute("src"));
  assert.equal(fc.normPath(fc.fileUrlPath(i1.getAttribute("src")!)!), fc.normPath(fc.fileUrlPath(i2.getAttribute("src")!)!));
  assert.equal(i1.getAttribute("data-fv-src"), "./fig.png"); assert.equal(i2.getAttribute("data-fv-src"), "fig.png");
  assert.equal(fc.pictureDest(i1 as unknown as Element), "./fig.png", "the authored spelling is the picture's destination");
  const R = root as unknown as Element;
  const [a, b] = fc.imageEmbeds(TWO);
  assert.equal(a.dest, "./fig.png"); assert.equal(b.dest, "fig.png");
  assert.deepEqual(fc.embedFor(i1 as unknown as Element, R, TWO, MD), a, "the first picture is `./fig.png`'s embed");
  assert.deepEqual(fc.embedFor(i2 as unknown as Element, R, TWO, MD), b, "the second is `fig.png`'s — not the first's, which merely names the same file");
  assert.equal(fc.imgForRange(R, TWO, { start: a.start, end: a.end }, MD), i1, "the inverse: `./fig.png`'s embed paints on the first picture");
  assert.equal(fc.imgForRange(R, TWO, { start: b.start, end: b.end }, MD), i2, "…and `fig.png`'s on the second");
  // the same with an absolute and a relative spelling of the file
  const ABS = "![a](/repo/notes-api/docs/fig.png)\n\n![b](fig.png)\n";
  const abs = doc.createElement("div"); abs.innerHTML = '<p><img src="/repo/notes-api/docs/fig.png" alt="a"></p>\n<p><img src="fig.png" alt="b"></p>\n';
  fv.rewriteFigureSrcs(abs as unknown as ParentNode, DIR, SID);
  const [x1, x2] = abs.querySelectorAll("img");
  const [ea, eb] = fc.imageEmbeds(ABS);
  assert.deepEqual(fc.embedFor(x2 as unknown as Element, abs as unknown as Element, ABS, MD), eb);
  assert.equal(fc.imgForRange(abs as unknown as Element, ABS, { start: eb.start, end: eb.end }, MD), x2);
  assert.equal(fc.imgForRange(abs as unknown as Element, ABS, { start: ea.start, end: ea.end }, MD), x1);
  // percent-encoded twins: `six%20seven.png` and `<six seven.png>` are one spelling to marked (it emits six%20seven.png for
  // both), so the two pictures are twins of one destination and pair by order — in both directions (before, imgForRange
  // counted the embeds by exact dest, so the second embed's rectangle went to the FIRST picture)
  const PCT = "![a](six%20seven.png)\n\n![b](<six seven.png>)\n";
  const pct = doc.createElement("div"); pct.innerHTML = '<p><img src="six%20seven.png" alt="a"></p>\n<p><img src="six%20seven.png" alt="b"></p>\n';
  fv.rewriteFigureSrcs(pct as unknown as ParentNode, DIR, SID);
  const [p1, p2] = pct.querySelectorAll("img");
  const [pa, pb] = fc.imageEmbeds(PCT);
  assert.equal(pa.dest, "six%20seven.png"); assert.equal(pb.dest, "six seven.png");
  assert.deepEqual(fc.embedFor(p1 as unknown as Element, pct as unknown as Element, PCT, MD), pa);
  assert.deepEqual(fc.embedFor(p2 as unknown as Element, pct as unknown as Element, PCT, MD), pb);
  assert.equal(fc.imgForRange(pct as unknown as Element, PCT, { start: pb.start, end: pb.end }, MD), p2, "the second embed's picture is the second picture");
  assert.equal(fc.imgForRange(pct as unknown as Element, PCT, { start: pa.start, end: pa.end }, MD), p1);
  // identical spellings, as before: twins by order, both ways
  const SAME = "![a](fig.png)\n\n![b](fig.png)\n";
  const same = doc.createElement("div"); same.innerHTML = '<p><img src="fig.png" alt="a"></p>\n<p><img src="fig.png" alt="b"></p>\n';
  fv.rewriteFigureSrcs(same as unknown as ParentNode, DIR, SID);
  const [s1, s2] = same.querySelectorAll("img");
  const [sa, sb] = fc.imageEmbeds(SAME);
  assert.deepEqual(fc.embedFor(s1 as unknown as Element, same as unknown as Element, SAME, MD), sa);
  assert.deepEqual(fc.embedFor(s2 as unknown as Element, same as unknown as Element, SAME, MD), sb);
  assert.equal(fc.imgForRange(same as unknown as Element, SAME, { start: sb.start, end: sb.end }, MD), s2);
  // a picture spelled `./fig.png` in a source whose only embed is `fig.png`: no embed of its own — refused (null), never
  // anchored to the other spelling's line (the plan's Rendered rule: refuse rather than mis-anchor)
  const ONE = "![b](fig.png)\n";
  const one = doc.createElement("div"); one.innerHTML = '<p><img src="./fig.png" alt="a"></p>\n<p><img src="fig.png" alt="b"></p>\n';
  fv.rewriteFigureSrcs(one as unknown as ParentNode, DIR, SID);
  const [o1, o2] = one.querySelectorAll("img");
  assert.deepEqual(fc.embedFor(o1 as unknown as Element, one as unknown as Element, ONE, MD), null);
  assert.deepEqual(fc.embedFor(o2 as unknown as Element, one as unknown as Element, ONE, MD), fc.imageEmbeds(ONE)[0]);
  // a picture the viewer left as written (no data-fv-src) still matches its embed by src, as before
  const plain = doc.createElement("div"); plain.innerHTML = '<p><img src="fig.png" alt="b"></p>';
  assert.deepEqual(fc.embedFor(plain.querySelector("img") as unknown as Element, plain as unknown as Element, ONE, MD), fc.imageEmbeds(ONE)[0]);
  // a rewritten picture that carries no authored spelling (a stand-in's DOM) still matches its embed by path
  const bare = doc.createElement("div"); bare.innerHTML = '<p><img src="/file?path=' + encodeURIComponent(DIR + "fig.png") + '" alt="b"></p>';
  assert.deepEqual(fc.embedFor(bare.querySelector("img") as unknown as Element, bare as unknown as Element, ONE, MD), fc.imageEmbeds(ONE)[0]);
});

test("a region drawn on the second of two figures that embed one file under two spellings is anchored to ITS embed line, and its rectangle paints back on it — while the first spelling's passage comment frames the first picture", async () => {
  const fv = await import("./file-view");
  const h = await harness({ kind: "rendered", html: TWO_HTML, src: TWO, prepare: (md) => fv.rewriteFigureSrcs(md as unknown as ParentNode, DIR, SID) });
  await h.ok({ embeddedHashes: {} });
  await h.open({ embeddedHashes: {} });
  const [img1, img2] = h.qa(".fileview-md img");
  assert.notEqual(img1.getAttribute("src"), img2.getAttribute("src"), "the rewrite made two srcs");
  h.drag(overlayOf(img2), [150, 240], [250, 300]);
  assert.equal(h.q(".fc-composer-ref .fc-refused"), null, "the embed was found: no refusal");
  assert.equal(h.q(".fc-composer-ref .fc-note")!.textContent, "On the region at 0.17, 0.20, 0.33, 0.30");
  assert.ok(overlayOf(img2).querySelector(".fc-region-pending"), "the pending rectangle is on the picture drawn on");
  assert.equal(overlayOf(img1).querySelector(".fc-region-pending"), null, "…and not on the other spelling's picture");
  h.input().value = "The axis label is wrong.";
  h.input().dispatch("keydown", { key: "Enter" });
  await tick();
  const c = h.last();
  const at = TWO.indexOf("![b](fig.png)");
  assert.equal(c.verb, "comment");
  assert.equal(c.args.anchor.quote, "![b](fig.png)", "the anchor is the SECOND figure's embed line");
  assert.equal(c.args.hintOffset, at);
  assert.deepEqual(c.args.target, { kind: "image", region: REGION, src: "fig.png" }, "src as the second embed writes it");
  // the comments come back: the region on `fig.png`'s line, a passage comment on `./fig.png`'s line
  const onB = await embeddedOn(TWO, "![b](fig.png)", {}, "fig.png");
  const { makeAnchor } = await import("./anchor-map");
  const aStart = TWO.indexOf("![a](./fig.png)");
  const onA: StoreComment = { id: "c9", author: "you", ts: T0, body: "Use the p99 chart.", anchor: makeAnchor(TWO, { start: aStart, end: aStart + "![a](./fig.png)".length }), replies: [], resolved: false };
  await h.ok(figureStatus([onB, onA], { "fig.png": H1 }));
  assert.ok(overlayOf(img2).querySelector('.fc-region[data-id="' + RID + '"]'), "the rectangle is painted on the second picture");
  assert.equal(overlayOf(img1).querySelector('.fc-region[data-id="' + RID + '"]'), null, "not on the first");
  assert.ok(img1.classList.contains("fc-hl") && img1.dataset.id === "c9", "the passage comment on `./fig.png`'s line frames the FIRST picture (imgForRange)");
  assert.equal(img2.classList.contains("fc-hl"), false, "the second wears no frame");
  assert.deepEqual(h.tags(RID), [], "current: the hash is keyed by the second embed's own spelling");
  h.dispose();
});

// ── a resolved region's card ───────────────────────────────────────────────────────────────────────

test("a resolved region comment wears 'resolved' alone: no stale tag, no unknown tag or note, no Re-place, no rectangle — the same comment unresolved wears the stale tag and offers Re-place", async () => {
  const h = await harness();
  const resolved = regionComment({ resolved: true });
  await h.ok({ ...withStore([resolved]), fileHash: H2 });       // the image was regenerated: H1 stored, H2 now
  await h.open({ ...withStore([resolved]), fileHash: H2 });
  assert.equal(h.q('.fc-region[data-id="' + RID + '"]'), null, "a resolved region paints no rectangle");
  h.click('[data-act="fcresolved"]');
  h.click('.fc-card[data-id="' + RID + '"] .fc-card-head');
  assert.ok(h.q('.fc-card.open[data-id="' + RID + '"]'), "the card is open in the Resolved fold");
  assert.deepEqual(h.tags(RID), ["resolved"], "no 'stale' beside 'resolved': the plan ends the stale state at resolve");
  assert.equal(h.q('.fc-card.open [data-act="fcreplace"]'), null, "Re-place is withheld from a resolved comment");
  assert.ok(h.q('.fc-card.open [data-act="fcresolve"][data-on="0"]'), "Reopen is the way back");
  // no hash to compare (an older kernel): unknown is a staleness verdict too, and a resolved region has none to report
  await h.restatus({ ...withStore([resolved]), fileHash: null });
  assert.deepEqual(h.tags(RID), ["resolved"], "no 'unknown' either");
  assert.equal(h.q('.fc-card.open .fc-note'), null, "and no sentence about it on the card");
  // the same comment reopened: the staleness is live again — the tag, and Re-place with the stale wording
  await h.restatus({ ...withStore([regionComment()]), fileHash: H2 });
  assert.deepEqual(h.tags(RID), ["stale"]);
  const rp = h.q('.fc-card.open [data-act="fcreplace"]');
  assert.ok(rp, "Re-place is offered on an open region");
  assert.equal(rp!.title, "The image changed: draw the region again where it belongs now");
  assert.ok(h.q('.fc-region[data-id="' + RID + '"]'), "the rectangle is painted again");
  await h.restatus({ ...withStore([regionComment()]), fileHash: null });
  assert.deepEqual(h.tags(RID), ["unknown"]);
  assert.ok(h.q('.fc-card.open .fc-note'), "the open card says why");
  h.dispose();
});

// ── the panel over a PDF body ──────────────────────────────────────────────────────────────────────

test("the panel over a PDF: the browser's frame takes no layer — no wrapper, no overlay, the empty state does not name the drag, and a whole-file comment is a card as before (Slice 4 renders pages; until then the frame is the browser's)", async () => {
  const h = await harness({ kind: "pdf" });
  const frame = h.media!;
  assert.equal(frame.tagName, "IFRAME");
  await h.ok();
  await h.open();
  assert.equal(h.q(".fc-imgwrap"), null, "no wrapper around the frame");
  assert.equal(h.q(".fc-overlay"), null, "no overlay over it");
  assert.equal(frame.parentNode, h.body, "the frame stands where the viewer put it");
  assert.equal(h.q(".fc-empty")!.textContent, "No comments yet. Comment on this file to leave one.", "the gesture is not offered: nothing here takes it");
  for (const cb of h.rendered) cb();                            // the media body's onRendered fires for a frame the moment it is in the body
  assert.equal(h.q(".fc-overlay"), null, "still none after the shown moment");
  const whole: StoreComment = { id: RID, author: "you", ts: T0, body: "Page 3 is out of date.", replies: [], resolved: false };
  await h.restatus(withStore([whole], "docs/deck.pdf"));
  assert.ok(h.q('.fc-card[data-id="' + RID + '"]'), "the whole-file comment is a card");
  assert.equal(h.q(".fc-overlay"), null);
  assert.equal(h.q(".fc-imgwrap"), null);
  h.dispose();
});

// ── a pending region across the picture's reload ───────────────────────────────────────────────────

test("a region composer open on a standalone image when the poll reloads the picture: the pending rectangle and the thumbnail move to the NEW <img>, the note stands, and Save posts the region", async () => {
  let media: E | null = null;
  const h = await harness({ mediaElement: () => media as unknown as HTMLElement | null });
  media = h.media;
  await h.ok();
  await h.open();
  const img = h.media!;
  h.drag(overlayOf(img), [150, 240], [250, 300]);
  assert.equal(h.q(".fc-composer")!.hidden, false, "the composer is open on the region");
  assert.ok(overlayOf(img).querySelector(".fc-region-pending"), "the pending rectangle shows on the picture");
  h.input().value = "The axis";
  // the session regenerated the image: the poll saw the file move, reload built a new <img>, its load fired onRendered
  const box2 = mk("div", "fileview-imgbox");
  const img2 = mk("img", "fileview-img"); img2.setAttribute("src", "blob:romp/figure-2"); picture(img2, false);
  box2.appendChild(img2); h.body.replaceChildren(box2); media = img2;
  drawn.length = 0;
  for (const cb of h.rendered) cb();
  assert.equal(h.qa(".fc-imgwrap").length, 1, "one layer, on the new picture");
  assert.ok(overlayOf(img2).querySelector(".fc-region-pending"), "the pending rectangle is painted on the NEW picture");
  assert.equal(h.q(".fc-composer-ref .fc-note")!.textContent, "On the region at 0.17, 0.20, 0.33, 0.30", "the composer still describes it");
  assert.ok(drawn.length > 0 && drawn.every((a) => a[0] === img2), "the thumbnail is cut from the new picture, not the detached old one");
  assert.equal(h.input().value, "The axis", "the half-typed note stands");
  h.input().value = "The axis label is wrong.";
  h.input().dispatch("keydown", { key: "Enter" });
  await tick();
  const c = h.last();
  assert.equal(c.verb, "comment");
  assert.deepEqual(c.args.target, { kind: "image", region: REGION });
  assert.equal(c.args.anchor, undefined, "a standalone image: no text anchor");
  h.dispose();
});

// ── a rectangle on a linked figure ─────────────────────────────────────────────────────────────────

const LINKED = "## Findings\n\n[![Figure](figure.png)](https://example.invalid/full.png)\n\nWe recommend shipping the cache in v1.2.\n";
// as mdBlock renders it: marked's <a><img></a>, every link given target=_blank rel=noopener; plus a link the AUTHOR wrote
// wearing the panel's own data-act, which is not the panel's to act on
const LINKED_HTML = '<h2>Findings</h2>\n<p><a href="https://example.invalid/full.png" target="_blank" rel="noopener"><img src="figure.png" alt="Figure"></a></p>\n'
  + '<p>We recommend shipping the cache in v1.2.</p>\n<p><a href="https://example.invalid/more" target="_blank" rel="noopener"><span data-act="fcopen" data-id="zz">more</span></a></p>\n';

test("a rectangle on a linked figure opens its card and cancels the link's activation — by click with the panel closed, by Enter, and by the press the armed overlay hands on; the browser's own click after the hand-on is swallowed; the author's own link wearing data-act=fcopen is neither cancelled nor acted on", async () => {
  const h = await harness({ kind: "rendered", html: LINKED_HTML, src: LINKED });
  const linked = await embeddedOn(LINKED, "![Figure](figure.png)");
  await h.ok(figureStatus([linked]));
  const img = h.q(".fileview-md img")!;
  const rect = h.q('.fc-region[data-id="' + RID + '"]')!;
  assert.ok(rect, "the figure has a rectangle to show, so its layer stands with the panel closed");
  assert.equal(rect.closest("a")!.getAttribute("href"), "https://example.invalid/full.png", "the rectangle stands INSIDE the author's link, where the picture was");
  const seen: boolean[] = [];
  const atDoc = (ev: Ev) => { seen.push(ev.defaultPrevented); };   // what the browser reads after dispatch: a cancelled click activates no anchor
  doc.addEventListener("click", atDoc);
  try {
    // 1. the panel closed: the browser's own click on the rectangle
    const ev1 = rect.dispatch("click");
    assert.ok(h.q('.fc-card.open[data-id="' + RID + '"]'), "the card opened");
    assert.equal(ev1.defaultPrevented, true, "the link's activation is cancelled: no new tab");
    assert.deepEqual(seen, [true]);
    await h.ok(figureStatus([linked]));                          // the open's status
    // 2. Enter on the focused rectangle (KEY_ACTS: its click)
    const rect2 = h.q('.fc-region[data-id="' + RID + '"]')!;
    rect2.focus();
    rect2.dispatch("keydown", { key: "Enter" });
    assert.deepEqual(seen, [true, true], "the synthetic click is cancelled too");
    // 3. the panel open: the press begins on the rectangle, the overlay captures it and hands the click on
    const overlay = overlayOf(img);
    assert.equal(overlay.classList.contains("fc-overlay-off"), false, "armed");
    rect2.dispatch("pointerdown", { clientX: 160, clientY: 250, pointerId: 9, button: 0 });
    overlay.dispatch("pointerup", { clientX: 160, clientY: 250, pointerId: 9 });
    assert.deepEqual(seen, [true, true, true], "the handed-on click is cancelled");
    const own = overlay.dispatch("click");                        // the browser's own click, to the capturing overlay
    assert.equal(own.defaultPrevented, true, "…and the browser's own click after it is swallowed");
    assert.deepEqual(seen, [true, true, true], "it reached nothing past the overlay");
    // 4. the file's own markup: a link the author wrote around a span wearing the panel's data-act
    const theirs = h.q('span[data-act="fcopen"][data-id="zz"]')!;
    const ev4 = theirs.dispatch("click");
    assert.equal(ev4.defaultPrevented, false, "not the panel's control: the author's link follows as written");
    assert.equal(h.q('.fc-card[data-id="zz"]'), null, "and nothing was acted on");
    assert.deepEqual(seen, [true, true, true, false]);
  } finally { doc.removeEventListener("click", atDoc); }
  h.dispose();
});

// ── the chat pane's link handler over a linked figure ──────────────────────────────────────────────

test("under the chat pane's capture-phase link handler, a rectangle on a linked figure still opens its card and opens no tab — the handler asks panelMark; the author's own link inside the file still opens", async () => {
  const h = await harness({ kind: "rendered", html: LINKED_HTML, src: LINKED });
  const isMark = (e: E): boolean => h.fc.panelMark(e as unknown as Element);
  const before = h.q(".fileview-md img")!;
  assert.equal(isMark(before), false, "a picture no panel has touched is the file's own");
  const linked = await embeddedOn(LINKED, "![Figure](figure.png)");
  await h.ok(figureStatus([linked]));
  const img = h.q(".fileview-md img")!;
  const rect = h.q('.fc-region[data-id="' + RID + '"]')!;
  const chip = rect.querySelector(".fc-region-chip")!;
  const overlay = overlayOf(img);
  assert.equal(isMark(rect), true, "the rectangle is the panel's");
  assert.equal(isMark(chip), true, "…and so is a press on its chip, through the rectangle");
  assert.equal(isMark(overlay), true, "the overlay the browser's own click lands on after a handed-on press");
  assert.equal(isMark(img), false, "the picture itself is not a mark until an embed-line comment frames it");
  // render.ts's handler, as it stands: every absolute a[href] is opened at the capture phase and the event ends there —
  // unless the panel's registry says the target is the panel's
  const opened: string[] = [];
  const chat = (ev: Ev) => {
    const a = (ev.target as E).closest("a[href]");
    if (!a) return;
    if (isMark(ev.target as E)) return;
    const href = a.getAttribute("href") || "";
    if (!/^[a-z][a-z0-9+.-]*:/i.test(href)) return;
    ev.preventDefault(); ev.stopPropagation();
    opened.push(href);
  };
  doc.addEventListener("click", chat, true);
  try {
    // 1. the panel closed: the browser's own click on the rectangle
    const ev1 = rect.dispatch("click");
    assert.deepEqual(opened, [], "no tab");
    assert.ok(h.q('.fc-card.open[data-id="' + RID + '"]'), "the card opened: the click reached the delegate root");
    assert.equal(ev1.defaultPrevented, true, "the panel cancelled the anchor");
    await h.ok(figureStatus([linked]));
    // 2. the panel open: the press begins on the chip, the overlay hands the click on, then the browser's own click lands
    //    on the overlay
    const rect2 = h.q('.fc-region[data-id="' + RID + '"]')!;
    const chip2 = rect2.querySelector(".fc-region-chip")!;
    assert.equal(overlayOf(img).classList.contains("fc-overlay-off"), false, "armed");
    h.click('.fc-card.open .fc-card-head');                       // collapse it, so the hand-on has something to open
    assert.equal(h.q('.fc-card.open[data-id="' + RID + '"]'), null);
    chip2.dispatch("pointerdown", { clientX: 160, clientY: 250, pointerId: 9, button: 0 });
    overlayOf(img).dispatch("pointerup", { clientX: 160, clientY: 250, pointerId: 9 });
    assert.ok(h.q('.fc-card.open[data-id="' + RID + '"]'), "the handed-on click opened the card");
    const own = overlayOf(img).dispatch("click");
    assert.equal(own.defaultPrevented, true, "the browser's own click is swallowed by the layer");
    assert.deepEqual(opened, [], "neither click opened a tab");
    // 3. the file's own link, and the author's span wearing the panel's data-act inside it: the chat handler's, as before
    const theirs = h.q('span[data-act="fcopen"][data-id="zz"]')!;
    assert.equal(isMark(theirs), false, "the file's markup, whatever it wears");
    const ev3 = theirs.dispatch("click");
    assert.deepEqual(opened, ["https://example.invalid/more"], "the author's link opens in a tab");
    assert.equal(ev3.defaultPrevented, true, "…and the anchor's own activation is cancelled by that handler");
    assert.equal(h.q('.fc-card[data-id="zz"]'), null, "nothing of the panel's was acted on");
  } finally { doc.removeEventListener("click", chat); }
  h.dispose();
});

// ── the picture that would not decode after a reload ───────────────────────────────────────────────

test("a reload whose bytes fail to decode: the viewer's failure pane fires onRendered, the panel takes the old picture's layer down, and the empty state stops naming the drag", async () => {
  let media: E | null = null;
  const h = await harness({ mediaElement: () => media as unknown as HTMLElement | null });
  media = h.media;
  await h.ok();
  await h.open();
  const img = h.media!;
  assert.ok(overlayOf(img), "the picture wears its layer with the panel open");
  assert.equal(overlayOf(img).classList.contains("fc-overlay-off"), false, "armed");
  assert.equal(h.q(".fc-empty")!.textContent, "No comments yet. Drag a rectangle on the image, or comment on this file.", "the empty state names the drag while a picture takes it");
  // the poll saw the file move and reloaded; the new bytes would not decode: imgFailed's pane takes the body and, being a
  // paint of the body, fires the seam's onRendered (file-view.ts) — before that line the hook fired only for a picture that
  // decoded, and the panel kept this layer, armed, over a body with no picture until some later paint
  const pane = mk("div", "fileview-err"); pane.textContent = "this image failed to decode — it may be mid-write or truncated";
  h.body.replaceChildren(pane); media = null;
  for (const cb of h.rendered) cb();
  assert.equal(h.qa(".fc-imgwrap").length, 0, "the old picture's layer is gone with the picture");
  assert.equal(h.qa(".fc-overlay").length, 0);
  assert.equal(h.q(".fc-empty")!.textContent, "No comments yet. Comment on this file to leave one.", "nothing in view takes a drag, so none is named");
  h.dispose();
});
