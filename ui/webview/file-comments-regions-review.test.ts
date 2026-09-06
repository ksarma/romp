// Region comments on images — what the 2026-09-06 review of Slice 3 found untested or wrong in the panel
// (plans/file-review.md, Slice 3; file-comments.ts), driven end to end through a DOM stand-in the way
// file-comments-regions.test.ts drives the slice itself. The stand-in is that file's, extended with what these
// cases need and nothing more: a focus model (focus() sets the document's activeElement, and removing the focused
// element drops it to the body, as a browser does), document listeners with a capture phase (the panel catches
// Esc there, ahead of the viewer's own), an element's click() (a bubbling click, as in a browser — the KEY_ACTS
// path and the layer's handOn call it), and a fetch the test picks per case (the poll's HEAD answers by path, the
// session colour map). Every test is behavioural: a mutant that drops the branch under test fails here.
// Synthetic fixtures only: the notes-api world, placeholder ids.
import { test, type TestContext } from "node:test";
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
    mediaElement: () => media as unknown as HTMLElement | null, renderedImages: () => [],
    identity: () => ({ name: "api", color: null }),
    onRendered: (cb) => { rendered.push(cb); }, onSelection: noop, onSaved: (cb) => { saved.push(cb); }, onClose: (cb) => { closers.push(cb); },
    post: (m) => { posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: noop,
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
const styleOf = (e: E): string => e.getAttribute("style") || "";
const RECT_STYLE = "left: 16.67%; top: 20.00%; width: 33.33%; height: 30.00%;";

// ── a click the armed overlay covers ───────────────────────────────────────────────────────────────

test("a framed figure under the armed overlay: a click on the picture opens the embed-line comment's card and still offers Comment (the Slice 2 behaviour, with the overlay in the way)", async () => {
  const h = await harness({ kind: "rendered", html: REPORT_HTML, src: REPORT });
  await h.ok(figureStatus([onEmbedLine], {}));
  await h.open(figureStatus([onEmbedLine], {}));
  const img = h.q(".fileview-md img")!;
  assert.ok(img.classList.contains("fc-hl") && img.dataset.act === "fcopen" && img.dataset.id === "c9", "the passage comment's highlight is a frame on the picture, a control");
  const overlay = (img.parentNode as E).querySelector(".fc-overlay")!;
  assert.equal(overlay.classList.contains("fc-overlay-off"), false, "the panel is open on a desktop: the overlay stands over the picture and takes every press");
  // the press lands on the overlay, and so do its release and the click the browser dispatches after them: the
  // overlay captured the pointer, and a captured pointer's click goes to the capturing element, never to the picture
  overlay.dispatch("pointerdown", { clientX: 150, clientY: 240, pointerId: 7, button: 0 });
  overlay.dispatch("pointerup", { clientX: 151, clientY: 240, pointerId: 7 });
  const click = overlay.dispatch("click");
  const card = h.q('.fc-card[data-id="c9"]')!;
  assert.ok(card.classList.contains("open"), "the frame's own action opened its card");
  assert.equal(card.querySelector('[data-act="fcreveal"]'), null, "painted, so no Reveal is needed");
  assert.equal(h.float().hidden, false, "…and the picture is still commentable: the Comment offer shows beside it");
  assert.equal(click.defaultPrevented, true, "the browser's own click, aimed at the overlay, is not a second activation");
  h.dispose();
});

// ── the poll and the figures ───────────────────────────────────────────────────────────────────────

test("the poll HEADs the figure a region comment names: a regenerated figure — the text file, sidecar and config untouched — re-asks status, reloads the view, and the rectangle goes stale by hash", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setInterval"] });
  const mtimes: Record<string, string | undefined> = { [MD]: "1757145600000000001", [STORE_MD]: "1757145600000000002", [PNG]: "1757145600000000005" };
  const heads: string[] = [];
  fetchImpl = async (url: string, init?: { method?: string }) => {
    if (!init || init.method !== "HEAD") return { status: 200, headers: { get: () => null }, json: async () => [] };   // GET /sessions
    const p = decodeURIComponent((/[?&]path=([^&]*)/.exec(url) || [])[1] || "");
    heads.push(p);
    const mt = mtimes[p];
    return { status: mt === undefined ? 404 : 200, headers: { get: (k: string) => (k === "X-Romp-Mtime-Ns" && mt !== undefined ? mt : null) } };
  };
  let reloads = 0;
  try {
    const h = await harness({ kind: "rendered", html: REPORT_HTML, src: REPORT, reload: () => { reloads++; } });
    await h.ok(figureStatus([embedded()]));
    await h.open(figureStatus([embedded()]));
    const asks = () => h.posted.filter((m) => m.type === "fileComments" && m.verb === "status").length;
    const n0 = asks();
    assert.equal(h.q('.fc-region[data-id="' + RID + '"]')!.classList.contains("fc-stale"), false, "h1 stored, h1 current");
    t.mock.timers.tick(2500); await flush();
    assert.deepEqual(heads, [MD, STORE_MD, CONFIG, PNG], "the figure is HEADed beside the three targets, resolved against the text file's folder");
    assert.equal(asks(), n0, "the figure's first reading is a baseline, not a move");
    assert.equal(reloads, 0);
    // the session regenerates the figure: only ITS mtime moves
    mtimes[PNG] = "1757145600000000009";
    t.mock.timers.tick(2500); await flush();
    assert.equal(asks(), n0 + 1, "the figure moved: status is re-asked");
    assert.equal(reloads, 1, "…and the view is reloaded, so the new picture is fetched (the kernel's no-cache lets the <img> revalidate)");
    await h.ok(figureStatus([embedded()], { "figure.png": H2 }));
    assert.equal(h.q('.fc-region[data-id="' + RID + '"]')!.classList.contains("fc-stale"), true, "the fresh status's hash flips the rectangle stale");
    assert.deepEqual(h.tags(RID), ["stale"]);
    t.mock.timers.tick(2500); await flush();
    assert.equal(asks(), n0 + 1, "nothing moved since: no re-ask, no flap");
    assert.equal(reloads, 1);
    h.dispose();
  } finally { fetchImpl = noKernel; }
});

// ── the card's thumbnail ───────────────────────────────────────────────────────────────────────────

test("a figure still loading when the status lands: the open region card gains its thumbnail on the figure's load", async () => {
  drawn.length = 0;
  const h = await harness({ kind: "rendered", html: REPORT_HTML, src: REPORT, loading: true });
  await h.ok(figureStatus([embedded()]));
  await h.open(figureStatus([embedded()]));
  const img = h.q(".fileview-md img")!;
  assert.equal(img.complete, false);
  h.click('.fc-card[data-id="' + RID + '"] .fc-card-head');
  const card = () => h.q('.fc-card.open[data-id="' + RID + '"]')!;
  assert.ok(card(), "the card is open");
  assert.equal(card().querySelector("canvas.fc-crop"), null, "nothing to crop from yet: the picture has not decoded");
  const before = drawn.length;
  img.complete = true;
  img.dispatch("load");
  assert.ok(card().querySelector("canvas.fc-crop"), "the load re-renders the cards: the crop appears");
  assert.equal(drawn.length, before + 1);
  assert.deepEqual(drawn[drawn.length - 1].slice(1, 5), [100, 80, 200, 120], "cut from the picture's natural pixels");
  h.dispose();
});

// ── the author's colour ────────────────────────────────────────────────────────────────────────────

test("a rectangle wears the author's session colour and name from the colour map, and a map that answers after the paint repaints it", async () => {
  const API = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee";
  const held: { answer: (() => void) | null } = { answer: null };
  fetchImpl = async (url: string) => {
    if (!url.includes("/sessions")) return noKernel(url);
    await new Promise<void>((r) => { held.answer = r; });   // the map's round trip, held until the test lets it land
    return { status: 200, headers: { get: () => null }, json: async () => [{ id: API, name: "api", bg: "#123456", fg: "#ffffff" }] };
  };
  try {
    const h = await harness();
    const bySession = regionComment({ author: "api-session", authorId: API });
    await h.ok(withStore([bySession]));
    await h.open(withStore([bySession]));
    const rect = () => h.q('.fc-region[data-id="' + RID + '"]')!;
    const chip = () => rect().querySelector(".fc-region-chip")!.getAttribute("data-label");
    assert.equal(styleOf(rect()), RECT_STYLE, "before the map answers: the sheet's fallback colour, no custom properties");
    assert.equal(chip(), "api-session", "…and the sidecar's own label");
    assert.ok(held.answer, "the map was asked for on open");
    held.answer!(); await flush();
    assert.equal(styleOf(rect()), RECT_STYLE + " --fc-author: #123456; --fc-author-fg: #ffffff;", "the map landed: the rectangle wears the session's colours");
    assert.equal(chip(), "api", "and the chip its name");
    h.dispose();
  } finally { fetchImpl = noKernel; }
});

// ── the reference scrolls to the rectangle ─────────────────────────────────────────────────────────

test("the card's reference scrolls to the rectangle — on a standalone image and on an embedded figure — with no view switch and no scroll to the embed line", async () => {
  const h = await harness();
  await h.ok(withStore([regionComment()]));
  await h.open(withStore([regionComment()]));
  const rect = h.q('.fc-region[data-id="' + RID + '"]')!;
  h.click('.fc-card[data-id="' + RID + '"] .fc-ref[data-act="fcgoto"]');
  assert.equal(rect.scrolled, 1, "the rectangle scrolled into view");
  assert.deepEqual(h.modes, [], "no switch to Raw");
  h.dispose();
  const h2 = await harness({ kind: "rendered", html: REPORT_HTML, src: REPORT });
  await h2.ok(figureStatus([embedded()]));
  await h2.open(figureStatus([embedded()]));
  const rect2 = h2.q('.fc-region[data-id="' + RID + '"]')!;
  h2.click('.fc-card[data-id="' + RID + '"] .fc-ref[data-act="fcgoto"]');
  assert.equal(rect2.scrolled, 1, "the rectangle on the figure scrolled into view");
  assert.deepEqual(h2.modes, [], "the embed line is not what is shown: the rectangle is");
  assert.deepEqual(h2.offsets, [], "no scroll to the embed line's offset either");
  h2.dispose();
});

// ── a detached embed anchor ────────────────────────────────────────────────────────────────────────

test("a region whose embed anchor detached (the figure moved into a rewritten section, its alt changed) is still painted on the figure its src names: the crop, Re-place, and the card says detached", async () => {
  drawn.length = 0;
  const html = '<h2>Results</h2>\n<p><img src="figure.png" alt="Latency chart"></p>\n<p>Ship it.</p>\n';
  const src = "## Results\n\n![Latency chart](figure.png)\n\nShip it.\n";
  const h = await harness({ kind: "rendered", html, src });
  await h.ok(figureStatus([embedded()]));
  await h.open(figureStatus([embedded()]));
  const img = h.q(".fileview-md img")!;
  assert.ok((img.parentNode as E).querySelector('.fc-region[data-id="' + RID + '"]'), "the rectangle is painted on the figure the src names");
  assert.deepEqual(h.tags(RID), ["detached"], "the anchor is gone: the card says so, and the region is current");
  h.click('.fc-card[data-id="' + RID + '"] .fc-card-head');
  const open = h.q('.fc-card.open[data-id="' + RID + '"]')!;
  assert.ok(open.querySelector("canvas.fc-crop"), "the crop, cut from that figure");
  assert.ok(open.querySelector('[data-act="fcreplace"]'), "Re-place is offered, so the comment can be placed on the moved figure");
  assert.equal(open.querySelector(".fc-ref")!.getAttribute("data-act"), "fcgoto", "the reference links to the rectangle");
  assert.equal(open.querySelector('[data-act="fcreveal"]'), null, "nothing to reveal in Raw: the mark is in view");
  h.dispose();
});

// ── a layer whose picture left the view ────────────────────────────────────────────────────────────

test("a decode failure's pane replaces the picture: the stale layer is taken down — the empty state stops naming the drag, the old picture's listener is released, the picture is back in its box", async () => {
  let media: E | null = null;
  const h = await harness({ mediaElement: () => media as unknown as HTMLElement | null });
  media = h.media;
  await h.ok();
  await h.open();
  assert.equal(h.q(".fc-empty")!.textContent, "No comments yet. Drag a rectangle on the image, or comment on this file.");
  const img = h.media!;
  assert.equal((img.listeners.get("load") || []).length, 1, "the layer listens for the picture's load");
  // the poll's reload lands bytes that fail to decode: the viewer's pane replaces the picture, mediaElement() is null,
  // and the refresh the same tick issued lands (no onRendered follows a decode failure)
  const box = h.q(".fileview-imgbox")!;
  box.remove(); media = null;
  h.body.appendChild(mk("div", "fileview-err"));
  await h.restatus();
  assert.equal(h.q(".fc-empty")!.textContent, "No comments yet. Comment on this file to leave one.", "no picture in view: the gesture is not offered");
  assert.equal(h.q(".fc-imgwrap"), null, "no layer in the body");
  assert.equal((img.listeners.get("load") || []).length, 0, "the stale layer's load listener is released");
  assert.equal(box.querySelector(".fc-imgwrap"), null, "the wrapper is gone from the old box…");
  assert.equal(box.childNodes[0], img, "…and the picture is back in it");
  h.dispose();
});

test("a reload that brings a new picture: the old picture's layer is dropped and one layer wraps the new one", async () => {
  let media: E | null = null;
  const h = await harness({ mediaElement: () => media as unknown as HTMLElement | null });
  media = h.media;
  await h.ok(withStore([regionComment()]));
  await h.open(withStore([regionComment()]));
  const img = h.media!;
  assert.ok(h.q('.fc-region[data-id="' + RID + '"]'));
  const box2 = mk("div", "fileview-imgbox");
  const img2 = mk("img", "fileview-img"); img2.setAttribute("src", "blob:romp/figure-2"); picture(img2, false);
  box2.appendChild(img2); h.body.replaceChildren(box2); media = img2;
  for (const cb of h.rendered) cb();                   // the media body's onRendered, once the new picture shows
  assert.equal(h.qa(".fc-imgwrap").length, 1, "one layer");
  assert.equal(h.q(".fc-imgwrap")!.childNodes[0], img2, "around the new picture");
  assert.equal((img.listeners.get("load") || []).length, 0, "the old picture's listener is released");
  assert.equal((img2.listeners.get("load") || []).length, 1);
  assert.ok((img2.parentNode as E).querySelector('.fc-region[data-id="' + RID + '"]'), "the rectangle is painted on the new picture");
  h.dispose();
});

// ── the region composer across a body repaint ──────────────────────────────────────────────────────

test("a region composer survives a body repaint: the pending rectangle follows the figure's new node, and a paragraph inserted above the embed moves the anchor with it", async () => {
  let text = REPORT;
  const h = await harness({ kind: "rendered", html: REPORT_HTML, src: REPORT, text: () => text });
  await h.ok({ embeddedHashes: {} });
  await h.open({ embeddedHashes: {} });
  const img = h.q(".fileview-md img")!;
  h.drag((img.parentNode as E).querySelector(".fc-overlay")!, [150, 240], [250, 300]);
  assert.equal(h.q(".fc-composer")!.hidden, false, "the composer is open on the region");
  h.input().value = "The axis";
  assert.ok((img.parentNode as E).querySelector(".fc-overlay .fc-region-pending"), "the pending region shows on the picture");
  // the poll saw the markdown move and reloaded it: fresh nodes, the same text
  h.repaint(REPORT_HTML);
  const img2 = h.q(".fileview-md img")!;
  assert.notEqual(img2, img, "a new picture node");
  assert.ok((img2.parentNode as E).querySelector(".fc-overlay .fc-region-pending"), "the pending rectangle is painted on the NEW picture");
  assert.equal(h.q(".fc-composer-ref .fc-note")!.textContent, "On the region at 0.17, 0.20, 0.33, 0.30", "the composer still describes it");
  assert.equal(h.input().value, "The axis", "the half-typed note stands");
  // the session inserted a paragraph above the embed: the embed line is re-found in the new text
  text = "## Findings\n\nNew intro.\n\n" + REPORT.slice("## Findings\n\n".length);
  h.repaint('<h2>Findings</h2>\n<p>New intro.</p>\n<p><img src="figure.png" alt="Figure"></p>\n<p>We recommend shipping the cache in v1.2.</p>\n');
  assert.equal(h.q(".fc-composer-ref .fc-tag"), null, "no 'passage changed': the embed line was re-found");
  assert.ok((h.q(".fileview-md img")!.parentNode as E).querySelector(".fc-overlay .fc-region-pending"), "the pending rectangle followed again");
  h.input().value = "The axis label is wrong.";
  h.input().dispatch("keydown", { key: "Enter" });
  await tick();
  const c = h.last();
  const at = text.indexOf("![Figure]");
  assert.equal(c.verb, "comment");
  assert.equal(c.args.hintOffset, at, "the hint is the embed's offset in the NEW text");
  assert.deepEqual(c.args.anchor, { quote: "![Figure](figure.png)", prefix: text.slice(at - 24, at), suffix: text.slice(at + 21, at + 45) }, "the anchor is built over the new text");
  assert.deepEqual(c.args.target, { kind: "image", region: REGION, src: "figure.png" });
  h.dispose();
});

// ── the rectangle as a keyboard control ────────────────────────────────────────────────────────────

test("Enter on a rectangle with the panel closed opens it without rebuilding the rectangle: the press pulse shows, the keyboard stays on it through the status that follows, and a rebuild re-finds it", async () => {
  const h = await harness();
  await h.ok(withStore([regionComment()]));
  const rect = h.q('.fc-region[data-id="' + RID + '"]')!;
  rect.focus();
  assert.equal(doc.activeElement, rect);
  rect.dispatch("keydown", { key: "Enter" });          // KEY_ACTS: the rectangle's click
  assert.ok(h.q('.fc-card.open[data-id="' + RID + '"]'), "the panel opened on the card");
  assert.equal(h.q('.fc-region[data-id="' + RID + '"]'), rect, "the same rectangle node stands: opening brought it nothing new to paint");
  assert.ok(rect.classList.contains("romp-acted"), "the press pulse is on a node in the document");
  assert.equal(doc.activeElement, rect, "the keyboard is still on it");
  // the open's status lands: nothing about the rectangle changed, so it stands, focus and all
  await h.ok(withStore([regionComment()]));
  assert.equal(h.q('.fc-region[data-id="' + RID + '"]'), rect);
  assert.equal(doc.activeElement, rect);
  // a status that changes what the rectangle shows (the image's bytes moved: stale) rebuilds it — the keyboard follows
  await h.restatus({ ...withStore([regionComment()]), fileHash: H2 });
  const fresh = h.q('.fc-region[data-id="' + RID + '"]')!;
  assert.notEqual(fresh, rect, "rebuilt on new information");
  assert.ok(fresh.classList.contains("fc-stale"));
  assert.equal(doc.activeElement, fresh, "re-found by its comment id, never left on the body");
  rect.blur(); fresh.blur();
  h.dispose();
});

test("a highlight holding the keyboard when a status repaints the body is re-found too", async () => {
  const passage: StoreComment = { id: T0 + "-118", author: "you", ts: T0 + 1000, body: "Which cache? Say which.",
    anchor: { quote: "shipping the cache in v1.2", prefix: "We recommend ", suffix: "." }, replies: [], resolved: false };
  const h = await harness({ kind: "rendered", html: REPORT_HTML, src: REPORT });
  await h.ok(figureStatus([passage], {}));
  await h.open(figureStatus([passage], {}));
  const hl = h.q('.fc-hl[data-id="' + passage.id + '"]')!;
  hl.focus();
  await h.restatus(figureStatus([passage], {}));
  const again = h.q('.fc-hl[data-id="' + passage.id + '"]')!;
  assert.notEqual(again, hl, "the highlights are re-wrapped on every paint");
  assert.equal(doc.activeElement, again, "the keyboard follows the passage");
  again.blur();
  h.dispose();
});

// ── Esc during a Re-place ──────────────────────────────────────────────────────────────────────────

test("Esc during a Re-place cancels the re-place and never reaches the viewer's own Escape (which closes the whole viewer); with none pending the key is the viewer's, and the input's own Esc is as before", async () => {
  const h = await harness();
  await h.ok(withStore([regionComment()]));
  await h.open(withStore([regionComment()]));
  const viewer: string[] = [];
  const onKey = (ev: Ev) => { if (ev.key === "Escape") viewer.push(ev.target === doc.body ? "body" : "element"); };   // file-view.ts's document-level onKey
  doc.addEventListener("keydown", onKey);
  try {
    h.click('.fc-card[data-id="' + RID + '"] .fc-card-head');
    h.click('.fc-card.open [data-act="fcreplace"]');
    const overlay = h.q(".fc-overlay")!;
    assert.equal(overlay.classList.contains("fc-replacing"), true, "re-place pending");
    assert.equal(h.input().hidden, true, "no input to catch the key");
    // the focus sits on the re-rendered Re-place button (render's refocus)…
    const rp = h.q('.fc-card.open [data-act="fcreplace"]')!;
    const ev = rp.dispatch("keydown", { key: "Escape" });
    assert.equal(h.q(".fc-composer")!.hidden, true, "the re-place is cancelled");
    assert.equal(overlay.classList.contains("fc-replacing"), false, "the cue leaves");
    assert.equal(ev.defaultPrevented, true);
    assert.deepEqual(viewer, [], "the viewer never saw the key: it stays open, the panel and the card with it");
    // …or on the body, where a browser does not focus a clicked button
    h.click('.fc-card.open [data-act="fcreplace"]');
    doc.body.dispatch("keydown", { key: "Escape" });
    assert.equal(h.q(".fc-composer")!.hidden, true, "cancelled from the body too");
    assert.deepEqual(viewer, []);
    // nothing pending: Esc is the viewer's, as before
    doc.body.dispatch("keydown", { key: "Escape" });
    assert.deepEqual(viewer, ["body"]);
    // another composer kind: its input catches Esc itself, as before
    h.click('.fc-card.open [data-act="fcreply"]');
    assert.equal(h.q(".fc-composer")!.hidden, false);
    h.input().dispatch("keydown", { key: "Escape" });
    assert.equal(h.q(".fc-composer")!.hidden, true);
    assert.deepEqual(viewer, ["body"], "stopped at the input");
  } finally { doc.removeEventListener("keydown", onKey); }
  h.dispose();
});

// ── the Rendered empty state ───────────────────────────────────────────────────────────────────────

test("the Rendered empty state names the drag when a figure's overlay is armed, and not on a coarse pointer or a page with no figure", async () => {
  const h = await harness({ kind: "rendered", html: REPORT_HTML, src: REPORT });
  await h.ok({ embeddedHashes: {} });
  await h.open({ embeddedHashes: {} });
  assert.equal(h.q(".fc-overlay")!.classList.contains("fc-overlay-off"), false, "the figure's overlay is armed");
  assert.equal(h.q(".fc-empty")!.textContent, "No comments yet. Select a passage and press Comment, drag a rectangle on a figure, or comment on this file.");
  h.dispose();
  coarse = true;
  try {
    const h2 = await harness({ kind: "rendered", html: REPORT_HTML, src: REPORT });
    await h2.ok({ embeddedHashes: {} });
    await h2.open({ embeddedHashes: {} });
    assert.equal(h2.q(".fc-overlay")!.classList.contains("fc-overlay-off"), true);
    assert.equal(h2.q(".fc-empty")!.textContent, "No comments yet. Select a passage and press Comment, or comment on this file.", "a finger cannot draw: the gesture is not named");
    h2.dispose();
  } finally { coarse = null; }
  const h3 = await harness({ kind: "rendered", html: "<p>No figure here.</p>\n", src: "No figure here.\n" });
  await h3.ok();
  await h3.open();
  assert.equal(h3.q(".fc-empty")!.textContent, "No comments yet. Select a passage and press Comment, or comment on this file.", "no figure, no overlay: nothing to drag on");
  h3.dispose();
});
