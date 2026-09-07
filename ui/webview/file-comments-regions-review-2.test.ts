// Region comments on images — the 2026-09-06 review's second round on the panel (plans/file-review.md, Slice 3;
// file-comments.ts), driven end to end through the DOM stand-in file-comments-regions-review.test.ts drives the first
// round with (a focus model, document listeners with a capture phase, an element's click()), the fixtures the same:
// the notes-api world, placeholder ids. What this round covers, each behavioural — a mutant that drops the branch under
// test fails here:
//   • an unknown region names the host's reason (fileHashReason / embeddedHashReasons) in the tag's title and, open, in
//     a sentence on the card — the over-cap file, a deleted figure, one outside the project, one past the budget — and
//     the panel-side causes the host cannot explain (a comment saved without a hash, a host that sent no hash);
//   • a standalone SVG's region seen in the Source view wears a "not shown" tag naming the way back to the picture;
//   • closing the viewer during a Re-place takes the panel's document-level Escape listener down with it;
//   • the region composer's "passage changed" tag appears when the embed line was rewritten under it;
//   • an embed dest with a percent escape of a reserved character still matches its rewritten picture (embedPath
//     decodes as the viewer's rewrite does);
//   • a region on a figure with no embed line offers Switch to Raw and keeps the note;
//   • a figure in rendered markdown is wrapped by its overlay only while the panel is open or it has a rectangle to show.
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

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const PNG = "/repo/notes-api/docs/figure.png";
const SVG = "/repo/notes-api/docs/diagram.svg";
const MD = "/repo/notes-api/docs/report.md";
const README = "/repo/notes-api/README.md";
const STORE_MD = "/repo/notes-api/.trackchanges/docs%2Freport.md.json";
const T0 = 1757145600000;
const H1 = "1111111111111111111111111111111111111111111111111111111111111111";
// the figure: a 600×400 picture drawn at half size, 100px in and 200px down
const IMG_RECT = rectOf(100, 200, 300, 200);
const REGION = { x: 0.1667, y: 0.2, w: 0.3333, h: 0.3 };   // the drag from (150,240) to (250,300) over IMG_RECT
const RID = T0 + "-0";
const regionComment = (over: Partial<StoreComment> = {}, target: Record<string, unknown> = {}): StoreComment => ({
  id: RID, author: "you", ts: T0, body: "The axis label is wrong.", replies: [], resolved: false,
  target: { kind: "image", region: REGION, hash: H1, ...target } as StoreComment["target"], ...over,
});
/** A status reply, plus whatever else the host puts beside the typed fields (the hash reasons ride outside the Status type). */
type Extra = Partial<Status> & Record<string, unknown>;
function pngStatus(over: Extra = {}): Status {
  return {
    verb: "status", root: "/repo/notes-api", storePath: "/repo/notes-api/.trackchanges/docs%2Ffigure.png.json",
    trackedBy: null, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: null, configMtimeNs: null,
    store: null, hunks: [], log: [], unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null },
    fileHash: H1,
    ...over,
  };
}
const withStore = (comments: StoreComment[], path = "docs/figure.png"): Extra => ({
  storeMtimeNs: "1757145600000000002", store: { v: 3, path, suggestions: [], comments },
  unsent: { comments: comments.map((c) => c.id), replies: [], accepted: 0, rejected: 0, watermark: null },
});
const REPORT = "## Findings\n\n![Figure](figure.png)\n\nWe recommend shipping the cache in v1.2.\n";
const REPORT_HTML = '<h2>Findings</h2>\n<p><img src="figure.png" alt="Figure"></p>\n<p>We recommend shipping the cache in v1.2.</p>\n';
const EMBED_ANCHOR = { quote: "![Figure](figure.png)", prefix: "## Findings\n\n", suffix: "\n\nWe recommend shipping " };
/** A region comment on the report's figure: the embed line's anchor and target.src, as the drag saves it. */
const embedded = (over: Partial<StoreComment> = {}, target: Record<string, unknown> = {}): StoreComment => regionComment({ anchor: EMBED_ANCHOR, ...over }, { src: "figure.png", ...target });
const figureStatus = (comments: StoreComment[], hashes: Record<string, string | null> = { "figure.png": H1 }): Extra => ({ ...withStore(comments, "docs/report.md"), embeddedHashes: hashes });
// the host's reasons for a hash it could not take, in the host's own words (tools/file-comments-host.mjs fileHashFor,
// embeddedHashesFor; the host tests pin the shapes) — lowercase fragments, tilde-collapsed paths
const OVER_CAP = "~/notes-api/docs/figure.png is 60000000 bytes, past the 50000000 bytes checked on each open, so whether it changed since its regions were drawn could not be checked";
const GONE = "the figure figure.png in ~/notes-api/docs/report.md was not hashed: ENOENT: no such file or directory, open '~/notes-api/docs/figure.png'";
const OUTSIDE = "the figure figure.png in ~/notes-api/docs/report.md was not hashed: ~/notes-api/docs/figure.png is outside the project root ~/notes-api";
const BUDGET = "the figure figure.png (60000000 bytes) was not checked: the figures ~/notes-api/docs/report.md's comments name are checked up to 200000000 bytes together, and this one would pass it";
const GENERIC = "Whether the image changed since this region was drawn could not be checked.";

// ── the harness ────────────────────────────────────────────────────────────────────────────────────
type Posted = Record<string, any>;
const mk = (tag: string, cls: string): E => { const e = doc.createElement(tag); e.className = cls; return e; };
const picture = (img: E, loading: boolean): void => { img.rect = IMG_RECT; img.naturalWidth = 600; img.naturalHeight = 400; img.complete = !loading; };
/** A mounted panel over a media body (`kind: "media"`: `.fileview-imgbox > img.fileview-img`), a rendered-markdown body
 *  (`html` + `src`), or a Raw body (`kind: "raw"` + `src`: one `.fv-cl` row per line inside `code.hljs`, as codeBlock
 *  builds them — the SVG Source view is this, with `media: () => "svg"` and no media element), inside the viewer's body
 *  row. `loading` leaves the pictures undecoded (complete = false). */
async function harness(over: Partial<FileViewActionCtx> & { kind?: "media" | "rendered" | "raw"; html?: string; src?: string; loading?: boolean } = {}) {
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
  } else if (kind === "rendered" && html !== undefined) {
    const md = mk("div", "fileview-md"); md.innerHTML = html; body.appendChild(md);
    for (const img of md.querySelectorAll("img")) picture(img, loading);
  } else if (kind === "raw" && src !== undefined) {
    const code = mk("code", "hljs");
    for (const line of src.split("\n")) { const row = mk("span", "fv-cl"); row.textContent = line; code.appendChild(row); }
    body.appendChild(code);
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
    mode: () => (kind === "media" ? "media" : kind === "rendered" ? "rendered" : "raw"),
    text: () => (kind === "media" ? null : src === undefined ? null : src),
    mtimeNs: () => "1757145600000000001",
    media: () => (kind === "media" ? "image" : null),
    pdfPages: () => [],                              // the Slice 4 seam member: these harnesses mount no PDF pages
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
  const status = (o: Extra = {}): Status => (kind === "media" ? pngStatus(o) : pngStatus({ storePath: STORE_MD, fileHash: undefined, ...o }));
  return {
    fc, main, body, unit, button, posted, modes, offsets, saved, rendered, last, media,
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
    /** The viewer repainted a rendered body (a reload, a view switch): fresh nodes from `html`, then the seam's onRendered. */
    repaint: (html2: string) => {
      const md = main.querySelector(".fileview-md")!;
      md.innerHTML = html2;
      for (const img of md.querySelectorAll("img")) picture(img, false);
      for (const cb of rendered) cb();
    },
    /** The tags on a card's head, in order. */
    tags: (id: string) => main.querySelector('.fc-card[data-id="' + id + '"] .fc-card-head')!.querySelectorAll(".fc-tag").map((t) => t.textContent),
    /** The one tag on a card's head. */
    tag: (id: string) => main.querySelector('.fc-card[data-id="' + id + '"] .fc-card-head .fc-tag')!,
    float: () => { const f = doc.body.querySelectorAll(".fc-float"); return f[f.length - 1]; },
    input: () => main.querySelector("input.fc-input")!,
    dispose: () => { for (const cb of closers) cb(); },
  };
}
const captureKeydowns = (): number => (doc.listeners.get("keydown") || []).filter((l) => l.capture).length;

// ── an unknown region names its reason ─────────────────────────────────────────────────────────────

test("a standalone image's unknown region names the host's reason: the tag's title collapsed, a sentence on the open card — the over-cap file; and the panel's own words for no reason, an older host, a comment saved without a hash", async () => {
  const over = { ...withStore([regionComment()]), fileHash: null, fileHashReason: OVER_CAP };
  const h = await harness();
  await h.ok(over);
  await h.open(over);
  assert.deepEqual(h.tags(RID), ["unknown"]);
  assert.equal(h.tag(RID).title, OVER_CAP + ".", "the host's own words, as a sentence");
  assert.ok(h.q('.fc-region[data-id="' + RID + '"]')!.classList.contains("fc-unknown"), "dotted on the picture, never stale");
  h.click('.fc-card[data-id="' + RID + '"] .fc-card-head');
  const why = () => h.q('.fc-card.open[data-id="' + RID + '"] .fc-note');
  assert.ok(why(), "open, the reason is a visible line: a title never reaches touch");
  assert.equal(why()!.textContent, OVER_CAP + ".");
  assert.ok(h.q('.fc-card.open [data-act="fcreplace"]'), "Re-place is still offered");
  // the host nulls the hash and gives no reason: the generic sentence
  await h.restatus({ ...withStore([regionComment()]), fileHash: null, fileHashReason: null });
  assert.equal(h.tag(RID).title, GENERIC);
  assert.equal(why()!.textContent, GENERIC);
  // a host from before region comments: no hash field at all
  await h.restatus({ ...withStore([regionComment()]), fileHash: undefined });
  assert.match(h.tag(RID).title, /^The file's machine sent no hash for this image, so whether it changed since this region was drawn could not be checked/);
  // a comment saved without a hash: the panel's own cause, whatever the host sent
  await h.restatus({ ...withStore([regionComment({}, { hash: undefined })]), fileHash: H1 });
  assert.equal(h.tag(RID).title, "This region was saved without the image's hash, so a later change to the image cannot be detected.");
  // hashed and current: no tag, no line
  await h.restatus({ ...withStore([regionComment()]), fileHash: H1 });
  assert.deepEqual(h.tags(RID), []);
  assert.equal(why(), null);
  h.dispose();
});

test("an embedded figure's unknown region says which figure and why — deleted, moved outside the project, past the budget — from embeddedHashReasons by src; a src the host sent no hash for reads as an older host", async () => {
  const deleted = { ...figureStatus([embedded()], { "figure.png": null }), embeddedHashReasons: { "figure.png": GONE } };
  const h = await harness({ kind: "rendered", html: REPORT_HTML, src: REPORT });
  await h.ok(deleted);
  await h.open(deleted);
  assert.deepEqual(h.tags(RID), ["unknown"]);
  assert.equal(h.tag(RID).title, "The figure figure.png in ~/notes-api/docs/report.md was not hashed: ENOENT: no such file or directory, open '~/notes-api/docs/figure.png'.");
  assert.ok(h.q('.fc-region[data-id="' + RID + '"]')!.classList.contains("fc-unknown"));
  h.click('.fc-card[data-id="' + RID + '"] .fc-card-head');
  assert.equal(h.q('.fc-card.open[data-id="' + RID + '"] .fc-note')!.textContent, "The figure figure.png in ~/notes-api/docs/report.md was not hashed: ENOENT: no such file or directory, open '~/notes-api/docs/figure.png'.");
  await h.restatus({ ...figureStatus([embedded()], { "figure.png": null }), embeddedHashReasons: { "figure.png": OUTSIDE } });
  assert.match(h.tag(RID).title, /^The figure figure\.png in .* is outside the project root ~\/notes-api\.$/);
  await h.restatus({ ...figureStatus([embedded()], { "figure.png": null }), embeddedHashReasons: { "figure.png": BUDGET } });
  assert.match(h.tag(RID).title, /^The figure figure\.png \(\d+ bytes\) was not checked: the figures .* are checked up to \d+ bytes together, and this one would pass it\.$/);
  // hashed again: nothing to explain
  await h.restatus(figureStatus([embedded()], { "figure.png": H1 }));
  assert.deepEqual(h.tags(RID), []);
  // the host answered with hashes but none under this src (and no reason): not a null it explained
  await h.restatus({ ...figureStatus([embedded()], {}), embeddedHashReasons: {} });
  assert.match(h.tag(RID).title, /^The file's machine sent no hash for this image/);
  h.dispose();
});

test("unknownReason, pure: the host's reason as a sentence when there is one, else the cause the panel can see, else the generic line", async () => {
  const { unknownReason } = await import("./file-comments");
  const t = { kind: "image" as const, region: REGION, hash: H1 };
  assert.equal(unknownReason(t, null), GENERIC);
  assert.equal(unknownReason(t, pngStatus({ fileHash: null })), GENERIC, "null with no reason");
  assert.equal(unknownReason(t, pngStatus({ fileHash: null, fileHashReason: OVER_CAP })), OVER_CAP + ".");
  assert.equal(unknownReason(t, pngStatus({ fileHash: null, fileHashReason: "  it moved.  " })), "It moved.", "capitalized, trimmed, one period");
  assert.equal(unknownReason({ ...t, src: "figs/a.png" }, pngStatus({ fileHash: undefined, embeddedHashes: { "figs/a.png": null }, embeddedHashReasons: { "figs/a.png": GONE } })), GONE.charAt(0).toUpperCase() + GONE.slice(1) + ".");
  assert.equal(unknownReason({ ...t, src: "figs/a.png" }, pngStatus({ fileHash: undefined, embeddedHashes: { "figs/b.png": H1 }, embeddedHashReasons: {} })).startsWith("The file's machine sent no hash for this image"), true, "no entry under the src");
  assert.equal(unknownReason({ ...t, src: "figs/a.png" }, pngStatus({ fileHash: undefined })).startsWith("The file's machine sent no hash for this image"), true, "no embeddedHashes at all");
  assert.equal(unknownReason({ ...t, hash: "" }, pngStatus({ fileHash: null, fileHashReason: OVER_CAP })), "This region was saved without the image's hash, so a later change to the image cannot be detected.", "the comment's own gap comes first");
});

// ── a standalone SVG's region in the Source view ───────────────────────────────────────────────────

const DIAGRAM = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 400">\n  <rect x="10" y="10" width="100" height="50"/>\n</svg>\n';
const SVG_STATUS: Extra = { ...withStore([regionComment()], "docs/diagram.svg"), storePath: "/repo/notes-api/.trackchanges/docs%2Fdiagram.svg.json", fileHash: H1 };

test("a standalone SVG's region comment seen in the Source view (the XML) is not a silent dead end: the card wears a 'not shown' tag naming the way back; the Image view of the same file shows the card with the rectangle as its mark and no tag", async () => {
  const h = await harness({ kind: "raw", src: DIAGRAM, path: SVG, media: () => "svg", mediaElement: () => null });
  await h.ok(SVG_STATUS);
  await h.open(SVG_STATUS);
  assert.equal(h.q(".fc-imgwrap"), null, "no picture in the Source view: nothing to paint the region on");
  assert.deepEqual(h.tags(RID), ["not shown"]);
  assert.equal(h.tag(RID).title, "The Source view shows the XML, not the image; press Source again to see the region on it");
  const head = h.q('.fc-card[data-id="' + RID + '"] .fc-card-head')!;
  assert.equal(head.querySelector(".fc-ref")!.getAttribute("data-act"), null, "the reference is words, not a link: there is no rectangle to scroll to");
  h.click('.fc-card[data-id="' + RID + '"] .fc-card-head');
  const open = h.q('.fc-card.open[data-id="' + RID + '"]')!;
  assert.equal(open.querySelector('[data-act="fcreveal"]'), null, "no passage to reveal: a standalone region has no anchor");
  assert.equal(open.querySelector('[data-act="fcreplace"]'), null, "nothing to draw on here");
  assert.equal(open.querySelector("canvas.fc-crop"), null);
  assert.ok(open.querySelector('[data-act="fcreply"]') && open.querySelector('[data-act="fcresolve"]'), "Reply and Resolve stand");
  h.dispose();
  const h2 = await harness({ path: SVG, media: () => "svg" });
  await h2.ok(SVG_STATUS);
  await h2.open(SVG_STATUS);
  assert.deepEqual(h2.tags(RID), [], "the Image view: the rectangle is the mark, nothing to say");
  assert.equal(h2.q('.fc-card[data-id="' + RID + '"] .fc-ref')!.getAttribute("data-act"), "fcgoto");
  h2.dispose();
  // an embedded region in Raw carries its anchor: the embed line is its mark there, so no tag either
  const h3 = await harness({ kind: "raw", src: REPORT });
  await h3.ok(figureStatus([embedded()]));
  await h3.open(figureStatus([embedded()]));
  assert.deepEqual(h3.tags(RID), []);
  assert.equal(h3.q('.fc-card[data-id="' + RID + '"] .fc-ref')!.getAttribute("data-act"), "fcgoto", "the highlight on the embed line");
  h3.dispose();
});

// ── the Escape listener leaves with the panel ──────────────────────────────────────────────────────

test("closing the viewer during a Re-place (the close button, another file opened over it) takes the panel's document-level Escape listener down with it: the next Escape is the page's again", async () => {
  const before = captureKeydowns();
  const h = await harness();
  await h.ok(withStore([regionComment()]));
  await h.open(withStore([regionComment()]));
  h.click('.fc-card[data-id="' + RID + '"] .fc-card-head');
  h.click('.fc-card.open [data-act="fcreplace"]');
  assert.equal(h.q(".fc-overlay")!.classList.contains("fc-replacing"), true, "a re-place is pending");
  assert.equal(captureKeydowns(), before + 1, "the panel's Esc listener is on the document, in the capture phase");
  const viewer: string[] = [];
  const onKey = (ev: Ev) => { if (ev.key === "Escape") viewer.push("viewer"); };   // file-view.ts's document-level onKey
  doc.addEventListener("keydown", onKey);
  try {
    h.dispose();                                          // runCloseHooks → dispose, the re-place still pending
    assert.equal(captureKeydowns(), before, "…and leaves with the panel");
    const ev = doc.body.dispatch("keydown", { key: "Escape" });
    assert.deepEqual(viewer, ["viewer"], "the page's own Escape handling hears the key");
    assert.equal(ev.defaultPrevented, false, "nothing swallowed it");
  } finally { doc.removeEventListener("keydown", onKey); }
});

// ── the region composer's "passage changed" ────────────────────────────────────────────────────────

test("a region composer whose embed line was rewritten under it (the poll reloaded the file; the alt text changed) wears 'passage changed' with the figure's own explanation, keeps the note, and Save hands the host the drag-time anchor to rule on", async () => {
  let text = REPORT;
  const h = await harness({ kind: "rendered", html: REPORT_HTML, src: REPORT, text: () => text });
  await h.ok({ embeddedHashes: {} });
  await h.open({ embeddedHashes: {} });
  const img = h.q(".fileview-md img")!;
  h.drag((img.parentNode as E).querySelector(".fc-overlay")!, [150, 240], [250, 300]);
  h.input().value = "The axis label is wrong.";
  assert.equal(h.q(".fc-composer-ref .fc-tag"), null, "fresh: no tag");
  text = REPORT.replace("![Figure](figure.png)", "![Chart](figure.png)");
  h.repaint(REPORT_HTML.replace('alt="Figure"', 'alt="Chart"'));
  const tag = h.q(".fc-composer-ref .fc-tag");
  assert.ok(tag, "the composer wears a tag once the embed line is not re-found");
  assert.equal(tag!.textContent, "passage changed");
  assert.equal(tag!.title, "The file changed and the line embedding this figure was not found in it; Save asks the file's machine to place it, and refuses if it cannot");
  assert.equal(h.input().value, "The axis label is wrong.", "the note stands");
  const img2 = h.q(".fileview-md img")!;
  assert.notEqual(img2, img, "a new picture node");
  assert.ok((img2.parentNode as E).querySelector(".fc-overlay .fc-region-pending"), "the pending rectangle followed the figure, found by its src");
  assert.ok(h.q('.fc-composer [data-act="fcsave"]'), "Save is offered: the host rules on the anchor");
  h.input().dispatch("keydown", { key: "Enter" });
  await tick();
  const c = h.last();
  assert.equal(c.verb, "comment");
  assert.deepEqual(c.args.anchor, EMBED_ANCHOR, "the drag-time anchor, over the text its offsets index");
  assert.equal(c.args.hintOffset, REPORT.indexOf("![Figure]"));
  assert.deepEqual(c.args.target, { kind: "image", region: REGION, src: "figure.png" });
  h.dispose();
});

// ── an embed dest with a reserved-character escape ─────────────────────────────────────────────────

test("embedPath decodes an embed's dest as the viewer's rewrite does (decodeURI): a dest with a percent escape of a reserved character (a%26b.png, fig%231.png) names one path both ways, an unreserved escape is decoded as before, and fileUrlPath stays fileUrl's inverse", async () => {
  const { embedPath, srcIsEmbed, fileUrlPath, normPath } = await import("./file-comments");
  const { fileUrl } = await import("./preview");
  const decodeDest = (d: string): string => { try { return decodeURI(d); } catch { return d; } };
  const loaded = (dest: string): string => fileUrl("/repo/notes-api/docs/" + decodeDest(dest), SID);   // what rewriteFigureSrcs emits for a relative dest
  for (const dest of ["a%26b.png", "fig%231.png", "q%3Fmark.png", "plus%2B.png", "six%20seven.png", "100%.png", "figure.png", "./figs/../figure.png"]) {
    assert.ok(srcIsEmbed(loaded(dest), dest, MD), "the rewritten picture matches its embed, for " + dest);
    assert.equal(normPath(fileUrlPath(loaded(dest))!), embedPath(MD, dest), "one path both ways, for " + dest);
  }
  assert.equal(embedPath(MD, "a%26b.png"), "/repo/notes-api/docs/a%26b.png", "a reserved escape is kept, as the viewer keeps it");
  assert.equal(embedPath(MD, "six%20seven.png"), "/repo/notes-api/docs/six seven.png", "an unreserved one is decoded");
  assert.equal(embedPath(MD, "100%.png"), "/repo/notes-api/docs/100%.png", "a malformed escape is taken as written");
  assert.equal(fileUrlPath("/file?path=%2Frepo%2Fa%2526b.png"), "/repo/a%26b.png", "fileUrlPath undoes encodeURIComponent, so %2526 is the file's own %26");
  assert.equal(srcIsEmbed(loaded("a%26b.png"), "a&b.png", MD), false, "a%26b.png and a&b.png are two files");
});

test("a figure embedded as a%26b.png, rewritten through /file: a drag saves a region on it, the embed-line comment's frame paints on it, and a click offers Comment on its line", async () => {
  const { fileUrl } = await import("./preview");
  const AMP = "## Findings\n\n![Latency](a%26b.png)\n\nShip it.\n";
  const AMP_HTML = '<h2>Findings</h2>\n<p><img src="' + fileUrl("/repo/notes-api/docs/a%26b.png", SID).replace(/&/g, "&amp;") + '" alt="Latency"></p>\n<p>Ship it.</p>\n';
  const onLine: StoreComment = { id: "c9", author: "you", ts: T0, body: "Use the p99 chart.", anchor: { quote: "![Latency](a%26b.png)", prefix: "## Findings\n\n", suffix: "\n\nShip it.\n" }, replies: [], resolved: false };
  const h = await harness({ kind: "rendered", html: AMP_HTML, src: AMP });
  await h.ok({ embeddedHashes: {} });
  await h.open({ embeddedHashes: {} });
  const img = h.q(".fileview-md img")!;
  const overlay = (img.parentNode as E).querySelector(".fc-overlay")!;
  h.drag(overlay, [150, 240], [250, 300]);
  assert.equal(h.q(".fc-composer-ref .fc-refused"), null, "the embed was found: no refusal");
  assert.equal(h.q(".fc-composer-ref .fc-note")!.textContent, "On the region at 0.17, 0.20, 0.33, 0.30");
  h.input().value = "The axis label is wrong.";
  h.input().dispatch("keydown", { key: "Enter" });
  await tick();
  assert.equal(h.last().verb, "comment");
  assert.deepEqual(h.last().args.target, { kind: "image", region: REGION, src: "a%26b.png" }, "src exactly as the embed writes it");
  assert.equal(h.last().args.anchor.quote, "![Latency](a%26b.png)");
  const st = { ...withStore([regionComment({ anchor: { quote: "![Latency](a%26b.png)", prefix: "## Findings\n\n", suffix: "\n\nShip it.\n" } }, { src: "a%26b.png" }), onLine], "docs/report.md"), embeddedHashes: { "a%26b.png": H1 } };
  await h.ok(st);
  assert.ok(overlay.querySelector('.fc-region[data-id="' + RID + '"]'), "the rectangle is painted back on the figure");
  assert.ok(img.classList.contains("fc-hl") && img.dataset.id === "c9", "the embed-line comment frames the picture (imgForRange found it)");
  assert.deepEqual(h.tags(RID), []);
  // a press that does not move: the picture click's offer, on the embed line
  overlay.dispatch("pointerdown", { clientX: 150, clientY: 240, pointerId: 8, button: 0 });
  overlay.dispatch("pointerup", { clientX: 151, clientY: 240, pointerId: 8 });
  overlay.dispatch("click");
  assert.equal(h.float().hidden, false, "Comment is offered beside the figure");
  h.float().dispatch("click");
  assert.equal(h.q(".fc-composer-ref .fc-quote")!.textContent, "![Latency](a%26b.png)", "on its embed line, not on the whole file");
  h.dispose();
});

// ── a refused region offers the switch to Raw ──────────────────────────────────────────────────────

test("a region on a figure the source holds no embed for: the refusal offers Switch to Raw, which keeps the note and hands it to a passage composer awaiting the embed line — Cancel is no longer the only exit", async () => {
  const html = '<h2>Findings</h2>\n<p><img src="https://example.invalid/chart.png" alt="Chart"></p>\n';
  const h = await harness({ kind: "rendered", html, src: "## Findings\n\nNo embed here.\n" });
  await h.ok({ embeddedHashes: {} });
  await h.open({ embeddedHashes: {} });
  const img = h.q(".fileview-md img")!;
  h.drag((img.parentNode as E).querySelector(".fc-overlay")!, [150, 240], [250, 300]);
  const box = h.q(".fc-composer")!;
  assert.equal(box.hidden, false);
  assert.equal(h.q(".fc-composer-ref .fc-refused")!.textContent, "The line that embeds this image was not found in the source, so a region on it cannot be saved. Select its line in the Raw view instead; the note stays.");
  assert.ok(h.q('.fc-composer-ref [data-act="fcraw"]'), "Switch to Raw is offered, as the passage refusal offers it");
  assert.deepEqual(h.qa(".fc-composer .fc-actions [data-act]").map((b) => b.dataset.act), ["fccancel"], "no Save: nothing to anchor a region to");
  h.input().value = "Wrong chart.";
  h.click('.fc-composer-ref [data-act="fcraw"]');
  assert.deepEqual(h.modes, ["raw"], "the view switches");
  assert.equal(h.input().value, "Wrong chart.", "the note stays");
  assert.equal(box.hidden, false, "the composer stays open");
  assert.equal(h.q(".fc-composer-ref .fc-refused")!.textContent, "The line that embeds this image was not found in the source; select it in the Raw view.", "now the passage composer the picture click's offer builds: a Raw selection places the note");
  assert.ok(h.q('.fc-composer-ref [data-act="fcraw"]'), "the switch stays offered, as on the click path");
  assert.equal(h.q('.fc-composer [data-act="fcsave"]'), null, "still nothing to save to");
  assert.equal(h.q(".fc-region-pending"), null, "the drawn rectangle leaves the overlay: there is no region to save");
  const before = h.posted.length;
  h.input().dispatch("keydown", { key: "Enter" });
  await tick();
  assert.equal(h.posted.length, before, "Enter saves nothing to the wrong place");
  assert.equal(h.input().value, "Wrong chart.");
  h.dispose();
});

// ── a figure is wrapped only when there is something to show ───────────────────────────────────────

const README_SRC = '<img src="logo.png" align="right" width="120"> The notes API.\n\n![Plot](plot.png)\n';
const README_HTML = '<p><img src="logo.png" align="right" width="120"> The notes API.</p>\n<p><img src="plot.png" alt="Plot"></p>\n';
const PLOT_AT = README_SRC.indexOf("![Plot]");
const plotRegion = regionComment({ anchor: { quote: "![Plot](plot.png)", prefix: README_SRC.slice(PLOT_AT - 24, PLOT_AT), suffix: README_SRC.slice(PLOT_AT + 17, PLOT_AT + 41) } }, { src: "plot.png" });

test("a figure in rendered markdown is wrapped only while the panel is open or it has a rectangle to show: closed, a README's floated logo and its plot keep the browser's layout; a region comment wraps its own figure alone; closing the panel puts an empty layer's picture back", async () => {
  const h = await harness({ kind: "rendered", html: README_HTML, src: README_SRC, path: README });
  const [logo, plot] = h.qa(".fileview-md img");
  const p1 = logo.parentNode as E, p2 = plot.parentNode as E;
  await h.ok({ embeddedHashes: {} });
  assert.equal(h.qa(".fc-imgwrap").length, 0, "the probe's status, no comments, panel closed: nothing is wrapped");
  assert.equal(logo.parentNode, p1); assert.equal(p1.childNodes[0], logo, "the logo stands where the author put it");
  assert.equal(plot.parentNode, p2);
  // a region comment on the plot lands: its figure alone takes a layer, with the panel still closed
  const st = { ...withStore([plotRegion], "README.md"), embeddedHashes: { "plot.png": H1 } };
  await h.restatus(st);
  assert.equal(h.qa(".fc-imgwrap").length, 1);
  assert.equal((plot.parentNode as E).className, "fc-imgwrap"); assert.equal(plot.parentNode!.parentNode, p2, "the plot's wrapper, inside its paragraph");
  assert.ok((plot.parentNode as E).querySelector('.fc-region[data-id="' + RID + '"]'), "its rectangle shows with the panel closed, as a highlight would");
  assert.equal(logo.parentNode, p1, "the logo is not wrapped: nothing to show on it");
  // open: every figure in view is a drawing surface
  await h.open(st);
  assert.equal(h.qa(".fc-imgwrap").length, 2);
  assert.equal((logo.parentNode as E).className, "fc-imgwrap");
  assert.equal((logo.parentNode as E).querySelector(".fc-overlay")!.classList.contains("fc-overlay-off"), false, "armed");
  // closed again: the logo's layer comes down and the picture goes back where it was; the plot keeps its rectangle
  h.button.dispatch("click");
  assert.equal(h.qa(".fc-imgwrap").length, 1);
  assert.equal(logo.parentNode, p1); assert.equal(p1.childNodes[0], logo, "back in its paragraph, first as before");
  assert.ok(h.q('.fc-region[data-id="' + RID + '"]'));
  // resolved: nothing left to show on the plot either, so its layer comes down too
  await h.restatus({ ...withStore([regionComment({ ...plotRegion, resolved: true })], "README.md"), embeddedHashes: { "plot.png": H1 } });
  assert.equal(h.qa(".fc-imgwrap").length, 0);
  assert.equal(plot.parentNode, p2);
  h.dispose();
  // the media body's one picture keeps its layer with the panel closed and no comment, as before
  const h2 = await harness();
  await h2.ok();
  assert.ok(h2.q(".fileview-imgbox .fc-imgwrap"), "the file's own picture, in a box built for it");
  h2.dispose();
});
