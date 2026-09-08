// The region composer over a figure whose embed line recurs, driven (the anchors follow-on's review, 2026-09-07;
// plans/file-review.md, Commenting from either view and the follow-on note). Two identical embeds of one destination with
// the same 24 characters around each: a region drawn on the SECOND, then the file changed at both ends, is a `tied` pair
// (followPassage) — the chip says "passage recurs" with the figure's own title (EMBED_TIED), Save carries no offset, and the
// pending rectangle claims NEITHER twin: by src alone the first twin took it, beside a chip saying the one drawn on cannot
// be told apart. And the second embed's line rewritten while the first stays is `elsewhere`: the anchor's one hit is the
// first twin, which is not the figure drawn on, so the rectangle claims neither and Save is refused here with the note
// kept (the host, handed that one hit, would place the region on the first). Until now the region half of both states was
// pinned at source alone (file-comments-follow.test.ts), so a swapped title or a hint sent for a tied region shipped green.
// Driven over the DOM stand-in file-comments-regions-review-4.test.ts uses; synthetic fixtures only: the notes-api world,
// placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import type { FileViewActionCtx } from "./file-view";
import type { Status, StoreComment } from "./file-comments-model";
import { makeAnchor } from "./anchor-map";

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

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const PNG = "/repo/notes-api/docs/figure.png";
const MD = "/repo/notes-api/docs/report.md";
const STORE_MD = "/repo/notes-api/.trackchanges/docs%2Freport.md.json";
const CONFIG = "/repo/notes-api/.trackchanges/config.json";
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
const REPORT = "## Findings\n\n![Figure](figure.png)\n\nWe recommend shipping the cache in v1.2.\n";
const REPORT_HTML = '<h2>Findings</h2>\n<p><img src="figure.png" alt="Figure"></p>\n<p>We recommend shipping the cache in v1.2.</p>\n';
const EMBED_ANCHOR = { quote: "![Figure](figure.png)", prefix: "## Findings\n\n", suffix: "\n\nWe recommend shipping " };
/** A region comment on the report's figure: the embed line's anchor and target.src, as the drag saves it. */
const embedded = (over: Partial<StoreComment> = {}, target: Record<string, unknown> = {}): StoreComment => regionComment({ anchor: EMBED_ANCHOR, ...over }, { src: "figure.png", ...target });
/** A passage comment on the embed line itself (the Slice 2 kind): no region, so its highlight is a frame on the picture. */
const onEmbedLine: StoreComment = { id: "c9", author: "you", ts: T0, body: "Use the p99 chart instead.", anchor: EMBED_ANCHOR, replies: [], resolved: false };
const figureStatus = (comments: StoreComment[], hashes: Record<string, string | null> = { "figure.png": H1 }): Partial<Status> => ({ ...withStore(comments, "docs/report.md"), embeddedHashes: hashes });

// ── the harness ────────────────────────────────────────────────────────────────────────────────────
type Posted = Record<string, any>;
const mk = (tag: string, cls: string): E => { const e = doc.createElement(tag); e.className = cls; return e; };
const picture = (img: E, loading: boolean): void => { img.rect = IMG_RECT; img.naturalWidth = 600; img.naturalHeight = 400; img.complete = !loading; };
/** A mounted panel over a media body (`kind: "media"`: `.fileview-imgbox > img.fileview-img`) or a rendered-markdown
 *  body (`html` + `src`), inside the viewer's body row. `loading` leaves the pictures undecoded (complete = false). */
async function harness(over: Partial<FileViewActionCtx> & { kind?: "media" | "rendered"; html?: string; src?: string; loading?: boolean } = {}) {
  const fc = await import("./file-comments");
  const { kind = "media", html, src, loading = false, ...ctxOver } = over;
  const main = mk("div", "fileview-main");
  const body = mk("div", "fileview-body"); main.appendChild(body);
  let media: E | null = null;
  if (kind === "media") {
    const box = mk("div", "fileview-imgbox");
    media = mk("img", "fileview-img"); media.setAttribute("src", "blob:romp/figure");
    picture(media, loading);
    box.appendChild(media); body.appendChild(box);
  } else if (html !== undefined) {
    const md = mk("div", "fileview-md"); md.innerHTML = html; body.appendChild(md);
    for (const img of md.querySelectorAll("img")) picture(img, loading);
  }
  const posted: Posted[] = [];
  const closers: Array<() => void> = [];
  const saved: Array<(info: { mtimeNs: string; logged: boolean }) => void> = [];
  const rendered: Array<() => void> = [];
  const modes: string[] = [];
  const offsets: number[] = [];
  let aside: E | null = null;
  const noop = () => { /* inert */ };
  const ctx: FileViewActionCtx = {
    path: kind === "media" ? PNG : MD, sid: SID, todoId: null,
    body: () => body as unknown as HTMLElement,
    mode: () => (kind === "media" ? "media" : "rendered"),
    text: () => (kind === "media" ? null : src === undefined ? null : src),
    mtimeNs: () => "1757145600000000001",
    media: () => (kind === "media" ? "image" : null),
    pdfPages: () => [],                              // the Slice 4 seam member: these harnesses mount no PDF pages
    mediaElement: () => media as unknown as HTMLElement | null, renderedImages: () => [],
    identity: () => ({ name: "api", color: null }),
    onRendered: (cb) => { rendered.push(cb); }, onSelection: noop, onSaved: (cb) => { saved.push(cb); }, onClose: (cb) => { closers.push(cb); },
    post: (m) => { posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: noop, editing: () => false, setTrackedEdit: noop,
    aside: (el) => { if (el) { aside = el as unknown as E; main.appendChild(aside); } else if (aside) { aside.remove(); aside = null; } },
    setMode: (m) => { modes.push(m); }, scrollToOffset: (n) => { offsets.push(n); }, reload: noop,
    ...ctxOver,
  };
  const unit = fc.fileCommentsAction.mount(ctx) as unknown as E;
  const button = unit.childNodes[0] as E;
  const last = (): Posted => posted[posted.length - 1];
  const reply = async (data: Record<string, unknown>) => { win.dispatchEvent(new MessageEvent("message", { data })); await tick(); await tick(); };
  const status = kind === "media" ? pngStatus : (o: Partial<Status> = {}) => pngStatus({ storePath: STORE_MD, fileHash: undefined, ...o });
  return {
    fc, main, body, unit, button, posted, modes, offsets, saved, rendered, last, media,
    ok: (o: Partial<Status> = {}) => reply({ type: "fileCommentsResult", reqId: last().reqId, ...status(o) }),
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
    /** The viewer repainted a rendered body (a reload, a view switch): fresh nodes from `html`, then the seam's onRendered. */
    repaint: (html2: string) => {
      const md = main.querySelector(".fileview-md")!;
      md.innerHTML = html2;
      for (const img of md.querySelectorAll("img")) picture(img, false);
      for (const cb of rendered) cb();
    },
    /** The tags on a card's head, in order. */
    tags: (id: string) => main.querySelector('.fc-card[data-id="' + id + '"] .fc-card-head')!.querySelectorAll(".fc-tag").map((t) => t.textContent),
    float: () => { const f = doc.body.querySelectorAll(".fc-float"); return f[f.length - 1]; },
    input: () => main.querySelector("input.fc-input")!,
    dispose: () => { for (const cb of closers) cb(); },
  };
}
/** A status override carrying fields the Status type does not name (the host's reasons, per src or per comment). */

// ── fixtures: a figure embedded twice with the same surroundings ───────────────────────────────────
const CAPTION = "The same caption on both figures.";   // longer than the anchor's 24 characters, so both embeds share their context
const EMBED = "![Latency](figs/p95.png)";
const TWINS = "# Report\n\n" + CAPTION + "\n\n" + EMBED + "\n\n" + CAPTION + "\n\n" + EMBED + "\n\n" + CAPTION + "\n";
const FIRST_AT = TWINS.indexOf(EMBED);
const SECOND_AT = TWINS.indexOf(EMBED, FIRST_AT + 1);
assert.ok(FIRST_AT > 0 && SECOND_AT > FIRST_AT, "two embeds");
const SECOND_RANGE = { start: SECOND_AT, end: SECOND_AT + EMBED.length };
const twinsHtml = (title: string, alts: [string, string], tail = ""): string =>
  "<h1>" + title + "</h1>\n<p>" + CAPTION + "</p>\n<p><img src=\"figs/p95.png\" alt=\"" + alts[0] + "\"></p>\n<p>" + CAPTION + "</p>\n<p><img src=\"figs/p95.png\" alt=\"" + alts[1] + "\"></p>\n<p>" + CAPTION + "</p>\n" + tail;
// edits at both ends in one write: the title, and a line at the end — the embeds tie
const BOTH = TWINS.replace("# Report", "# Report, revised") + "\nDone.\n";
// the second embed's line rewritten (its alt), the first left whole — the anchor's one hit is the first
const ALT_EMBED = "![Latency chart](figs/p95.png)";
const ALT = TWINS.slice(0, SECOND_AT) + ALT_EMBED + TWINS.slice(SECOND_AT + EMBED.length);
// the panel's words, copied here so a swap or a rewording fails a driven test
const EMBED_TIED = "The file changed and the line embedding this figure now occurs in it more than once with the same surroundings, so the one you drew on cannot be told apart; Save asks the file's machine to place it, and refuses if the copies still tie. Draw the region again to pick the figure.";
const EMBED_ELSEWHERE = "The file changed where you drew this region, and the line embedding this figure now occurs only elsewhere in the file, at a copy you did not draw on; Save is refused rather than put the note there. Draw the region again.";
const EMBED_ELSEWHERE_SAVE = "Nothing saved: the file changed where you drew this region, and the line embedding this figure now occurs only elsewhere in the file. Draw the region again.";
const pendingOn = (img: E): boolean => !!(img.parentNode as E).querySelector(".fc-overlay .fc-region-pending");
const overlayOf = (img: E): E => (img.parentNode as E).querySelector(".fc-overlay")!;
const composerTag = (h: { q: (sel: string) => E | null }): E | null => h.q(".fc-composer-ref .fc-tag");
async function fail(reqId: unknown, code: string, error: string): Promise<void> {
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsFailed", reqId, verb: "comment", code, error } }));
  await flush();
}

test("the fixture: the embeds tie for the anchor, edits at both ends make the pair tied, and the second's rewrite leaves one hit at the first", async () => {
  const { followPassage } = await import("./file-comments");
  const anchor = makeAnchor(TWINS, SECOND_RANGE);
  assert.equal(anchor.prefix, TWINS.slice(FIRST_AT - 24, FIRST_AT), "the same 24 characters before either embed");
  assert.equal(anchor.suffix, TWINS.slice(FIRST_AT + EMBED.length, FIRST_AT + EMBED.length + 24), "and after");
  assert.deepEqual(followPassage(TWINS, SECOND_RANGE, BOTH), { state: "tied" });
  assert.deepEqual(followPassage(TWINS, SECOND_RANGE, ALT), { state: "elsewhere" });
});

test("a region on the SECOND twin, the file changed at both ends: 'passage recurs' with the figure's title, the rectangle on neither twin, the thumbnail from the picture drawn on, Save with NO offset, the host's refusal keeps the note, and drawing on the second again pins it", async () => {
  let text = TWINS;
  const h = await harness({ kind: "rendered", html: twinsHtml("Report", ["Latency", "Latency"]), src: TWINS, text: () => text });
  await h.ok({ embeddedHashes: {} });
  await h.open({ embeddedHashes: {} });
  const [a, b] = h.qa(".fileview-md img");
  drawn.length = 0;
  h.drag(overlayOf(b), [150, 240], [250, 300]);
  assert.equal(h.q(".fc-composer")!.hidden, false);
  assert.equal(pendingOn(b), true, "the pending rectangle is on the picture dragged on");
  assert.equal(pendingOn(a), false);
  assert.equal(composerTag(h), null, "fresh: no tag");
  h.input().value = "Crop the y axis.";
  // the poll saw the file move and reloaded it: the title and the tail changed, so the embed line is re-found by its anchor,
  // and its two copies cannot be told apart
  text = BOTH;
  drawn.length = 0;
  h.repaint(twinsHtml("Report, revised", ["Latency", "Latency"], "<p>Done.</p>\n"));
  const [a2, b2] = h.qa(".fileview-md img");
  assert.notEqual(b2, b, "new picture nodes");
  const tg = composerTag(h);
  assert.ok(tg, "the composer wears a tag");
  assert.equal(tg!.textContent, "passage recurs");
  assert.equal(tg!.title, EMBED_TIED);
  assert.equal(pendingOn(a2), false, "no rectangle on the first twin: the chip says the figure drawn on cannot be told");
  assert.equal(pendingOn(b2), false, "nor on the second");
  assert.ok(drawn.length > 0, "the composer's thumbnail was drawn on the repaint");
  for (const args of drawn) assert.equal(args[0], b, "every thumbnail since the repaint is cut from the picture the region was drawn on, never from a twin now shown");
  assert.equal(h.input().value, "Crop the y axis.", "the note stands");
  assert.ok(h.q('.fc-composer [data-act="fcsave"]'), "Save is offered: the host rules on the tie");
  h.input().dispatch("keydown", { key: "Enter" });
  await tick();
  const c = h.last();
  assert.equal(c.verb, "comment");
  assert.equal("hintOffset" in c.args, false, "NO offset for a tied pair: the drag-time start indexes other text");
  assert.deepEqual(c.args.anchor, makeAnchor(TWINS, SECOND_RANGE), "the drag-time anchor, over the text its offsets index");
  assert.deepEqual(c.args.target, { kind: "image", region: REGION, src: "figs/p95.png" });
  assert.equal(c.args.note, "Crop the y axis.");
  // the host refuses the tie it cannot settle: the note stays, the chip still says why, and the rectangle still claims no twin
  await fail(c.reqId, "anchor-ambiguous", "the selected passage occurs more than once in docs/report.md with the same surroundings, and the selection's position was not sent to tell the copies apart — reload and select it again");
  assert.equal(h.input().value, "Crop the y axis.");
  assert.match(h.q(".fc-composer .fc-err")!.textContent, /more than once/);
  assert.equal(composerTag(h)!.title, EMBED_TIED);
  assert.equal(pendingOn(a2), false);
  assert.equal(pendingOn(b2), false);
  // the person draws on the second twin again, in the text as it is now: a fresh pair, no tag, the rectangle on it, and Save
  // sends its offset — the second embed's, in the current text
  h.drag(overlayOf(b2), [150, 240], [250, 300]);
  assert.equal(composerTag(h), null, "a fresh pair: no tag");
  assert.equal(pendingOn(b2), true);
  assert.equal(pendingOn(a2), false);
  assert.equal(h.input().value, "Crop the y axis.", "the note stays across the redraw");
  h.input().dispatch("keydown", { key: "Enter" });
  await tick();
  const again = h.last();
  assert.notEqual(again, c);
  const secondNow = BOTH.indexOf(EMBED, BOTH.indexOf(EMBED) + 1);
  assert.equal(again.args.hintOffset, secondNow, "the second embed's offset in the current text");
  assert.deepEqual(again.args.anchor, makeAnchor(BOTH, { start: secondNow, end: secondNow + EMBED.length }));
  assert.equal(again.args.note, "Crop the y axis.");
  h.dispose();
});

test("a region on the SECOND twin, that embed's line rewritten while the first stays whole: 'passage changed' with the elsewhere title, the rectangle on neither twin, Save refused here with the note kept, and drawing on the rewritten figure pins it", async () => {
  let text = TWINS;
  const h = await harness({ kind: "rendered", html: twinsHtml("Report", ["Latency", "Latency"]), src: TWINS, text: () => text });
  await h.ok({ embeddedHashes: {} });
  await h.open({ embeddedHashes: {} });
  const [, b] = h.qa(".fileview-md img");
  h.drag(overlayOf(b), [150, 240], [250, 300]);
  h.input().value = "Crop the y axis.";
  text = ALT;
  h.repaint(twinsHtml("Report", ["Latency", "Latency chart"]));
  const [a2, b2] = h.qa(".fileview-md img");
  const tg = composerTag(h);
  assert.ok(tg, "the composer wears a tag");
  assert.equal(tg!.textContent, "passage changed");
  assert.equal(tg!.title, EMBED_ELSEWHERE);
  assert.equal(pendingOn(a2), false, "the first twin is the anchor's one hit, and not the figure drawn on");
  assert.equal(pendingOn(b2), false);
  const posted = h.posted.length;
  h.input().dispatch("keydown", { key: "Enter" });
  await tick();
  assert.equal(h.posted.length, posted, "nothing posted: the host would place the one hit on the first twin");
  assert.ok(h.q(".fc-composer .fc-err")!.textContent.startsWith(EMBED_ELSEWHERE_SAVE), "the refusal row (its text, before the dismiss glyph)");
  assert.equal(h.input().value, "Crop the y axis.", "the note stays");
  // drawing on the rewritten figure: a fresh pair over the text shown, anchored to the line as it reads now
  h.drag(overlayOf(b2), [150, 240], [250, 300]);
  assert.equal(composerTag(h), null);
  assert.equal(pendingOn(b2), true);
  assert.equal(pendingOn(a2), false);
  h.input().dispatch("keydown", { key: "Enter" });
  await tick();
  const c = h.last();
  assert.equal(c.verb, "comment");
  assert.equal(c.args.hintOffset, ALT.indexOf(ALT_EMBED));
  assert.equal(c.args.anchor.quote, ALT_EMBED);
  assert.deepEqual(c.args.target, { kind: "image", region: REGION, src: "figs/p95.png" });
  assert.equal(c.args.note, "Crop the y axis.");
  h.dispose();
});

test("the same text back after a tie (the edit reverted): the pair is exact again, the tag clears, and the rectangle returns to the second twin", async () => {
  let text = TWINS;
  const h = await harness({ kind: "rendered", html: twinsHtml("Report", ["Latency", "Latency"]), src: TWINS, text: () => text });
  await h.ok({ embeddedHashes: {} });
  await h.open({ embeddedHashes: {} });
  const [, b] = h.qa(".fileview-md img");
  h.drag(overlayOf(b), [150, 240], [250, 300]);
  h.input().value = "Crop the y axis.";
  text = BOTH;
  h.repaint(twinsHtml("Report, revised", ["Latency", "Latency"], "<p>Done.</p>\n"));
  assert.equal(composerTag(h)!.textContent, "passage recurs");
  text = TWINS;
  h.repaint(twinsHtml("Report", ["Latency", "Latency"]));
  const [a3, b3] = h.qa(".fileview-md img");
  assert.equal(composerTag(h), null, "the pair's own text: no tag");
  assert.equal(pendingOn(b3), true, "the rectangle is back on the second twin");
  assert.equal(pendingOn(a3), false);
  h.input().dispatch("keydown", { key: "Enter" });
  await tick();
  assert.equal(h.last().args.hintOffset, SECOND_AT, "the offset is sent again: it indexes the text the host will read");
  h.dispose();
});
