// Region comments on images — the 2026-09-06 review's fourth round on the panel (plans/file-review.md, Slice 3;
// file-comments.ts), driven end to end through the DOM stand-in file-comments-regions-review.test.ts drives the first
// round with (a focus model, document listeners with a capture phase, an element's click()), the fixtures the same:
// the notes-api world, placeholder ids. What this round covers, each behavioural — a mutant that drops the branch under
// test fails here:
//   • a src-less region in the contract's own shape whose passage cannot tell its figure (two figures on it) shows the
//     host's reason from `derivedSrcReasons` — never the "kernel may predate region comments" sentence, which blamed a
//     kernel that had answered correctly; a src-less region on a text file with no reason filed says it names no figure;
//   • a region composer re-found after a repaint lands on the twin its embed line renders — the second of two embeds of
//     one destination — not the first picture of that src, so the pending rectangle, the thumbnail and Save agree;
//   • a malformed region (a coordinate missing, string coordinates) paints no rectangle and crops no canvas; its card wears
//     "unreadable" and says so in words, with Re-place as the way out;
//   • a Re-place whose card was collapsed re-opens it for the drag's answer: the refusal row, the loader for the retarget;
//   • closing the panel ends a pending Re-place: no cue on a disarmed picture, Escape is the viewer's again, and reopening
//     restores no re-place;
//   • the open stale card says in words what the tag's title says, with the recourse this card offers: Re-place when it is
//     there, resolve (and where Re-place is) on a coarse pointer or with the picture out of view.
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
/** A status override carrying fields the Status type does not name (the host's reasons, per src or per comment). */
type Extra = Partial<Status> & Record<string, unknown>;
const tagOf = (h: { q: (sel: string) => E | null }, id: string): E => h.q('.fc-card[data-id="' + id + '"] .fc-card-head .fc-tag')!;
const openNote = (h: { q: (sel: string) => E | null }, id: string): E | null => h.q('.fc-card.open[data-id="' + id + '"] .fc-note');
const REPLACE_NOW = "Re-place it where it belongs now, or resolve it.";
const STALE = "The image changed after this region was drawn, so it may no longer mark the right place.";
const UNREADABLE = "The region's coordinates could not be read from the comments file, so it is not drawn on the picture.";
const PREDATE = /kernel may predate region comments/;

// ── a src-less region whose passage cannot tell its figure ─────────────────────────────────────────

const FIGURES = "/repo/notes-api/docs/figures.md";
const BOTH_SRC = "## Charts\n\nBoth: ![left](figs/a.png) ![right](figs/b.png)\n\nText.\n";
const BOTH_HTML = '<h2>Charts</h2>\n<p>Both: <img src="figs/a.png" alt="left"> <img src="figs/b.png" alt="right"></p>\n<p>Text.</p>\n';
const BOTH_ANCHOR = { quote: "![left](figs/a.png) ![right](figs/b.png)", prefix: "## Charts\n\nBoth: ", suffix: "\n\nText.\n" };
const REASON = "the passage of comment " + RID + " in ~/notes-api/docs/figures.md embeds figs/a.png, figs/b.png, so which figure it is on cannot be told";
const REASON_SENTENCE = "The passage of comment " + RID + " in ~/notes-api/docs/figures.md embeds figs/a.png, figs/b.png, so which figure it is on cannot be told.";
const NO_FIGURE = "This region does not name the figure it is on, so there is no figure to check for changes since the region was drawn.";
/** The contract's own shape, as another writer leaves it: the anchor over the passage and {kind, region, hash}, no src. */
const srcless = (): StoreComment => regionComment({ anchor: BOTH_ANCHOR });
/** The host's reply for it: a text file (embeddedHashes, no fileHash), nothing hashed, the cause filed under the comment's id. */
const untold: Extra = { ...withStore([srcless()], "docs/figures.md"), embeddedHashes: {}, embeddedHashReasons: {}, derivedSrcs: {}, derivedSrcReasons: { [RID]: REASON } };

test("a src-less region whose passage embeds two figures: the tag's title and the open card carry the host's reason from derivedSrcReasons, never the 'kernel may predate' sentence; with no reason filed the card says the region names no figure; a passage that told its figure reads as current", async () => {
  const h = await harness({ kind: "rendered", html: BOTH_HTML, src: BOTH_SRC, path: FIGURES });
  await h.ok(untold);
  await h.open(untold);
  assert.deepEqual(h.tags(RID), ["unknown"], "which figure it is on cannot be told: unknown, never stale");
  assert.equal(tagOf(h, RID).title, REASON_SENTENCE, "the host's own reason, as a sentence");
  assert.doesNotMatch(tagOf(h, RID).title, PREDATE, "the kernel answered: it is not blamed");
  assert.equal(h.q('.fc-region[data-id="' + RID + '"]'), null, "no figure to paint it on");
  h.click('.fc-card[data-id="' + RID + '"] .fc-card-head');
  assert.equal(openNote(h, RID)!.textContent, REASON_SENTENCE, "open, the reason is a visible line");
  // no reason filed for it (a reply that reads no passages; a src-less region left with no embed line): the panel's own
  // words for a text file, not the media file's "no hash field" diagnosis
  await h.restatus({ ...withStore([srcless()], "docs/figures.md"), embeddedHashes: {}, embeddedHashReasons: {}, derivedSrcs: {}, derivedSrcReasons: {} } as Extra);
  assert.deepEqual(h.tags(RID), ["unknown"]);
  assert.equal(tagOf(h, RID).title, NO_FIGURE);
  assert.equal(openNote(h, RID)!.textContent, NO_FIGURE);
  // the host told the figure from a one-figure passage: the reply's copy of the comment carries the src and its hash
  const told: Extra = { ...withStore([regionComment({ anchor: BOTH_ANCHOR }, { src: "figs/a.png" })], "docs/figures.md"),
    embeddedHashes: { "figs/a.png": H1 }, embeddedHashReasons: {}, derivedSrcs: { [RID]: "figs/a.png" }, derivedSrcReasons: {} };
  await h.restatus(told);
  assert.deepEqual(h.tags(RID), [], "hashed and current: nothing to explain");
  assert.equal(openNote(h, RID), null);
  assert.ok(h.q('.fc-region[data-id="' + RID + '"]'), "and the rectangle paints on the figure the src names");
  h.dispose();
});

test("unknownReason, pure: the per-comment reason wins for the comment it names; without the id, or for another comment, a src-less region on a text-file reply says it names no figure; a media reply with no hash field still reads as an older kernel", async () => {
  const { unknownReason } = await import("./file-comments");
  const t = { kind: "image" as const, region: REGION, hash: H1 };
  const text = pngStatus({ fileHash: undefined, ...({ embeddedHashes: {}, embeddedHashReasons: {}, derivedSrcs: {}, derivedSrcReasons: { [RID]: REASON } } as Extra) });
  assert.equal(unknownReason(t, text, RID), REASON_SENTENCE);
  assert.equal(unknownReason(t, text, "other"), NO_FIGURE, "a reason filed for another comment is not this one's");
  assert.equal(unknownReason(t, text), NO_FIGURE, "no id to key the per-comment reasons on");
  assert.equal(unknownReason(t, pngStatus({ fileHash: undefined, embeddedHashes: {} }), RID), NO_FIGURE, "a text-file reply from a host that files no reasons");
  assert.doesNotMatch(unknownReason(t, text, RID), PREDATE);
  assert.match(unknownReason(t, pngStatus({ fileHash: undefined }), RID), PREDATE, "neither hash field: a kernel from before region comments");
  assert.match(unknownReason({ ...t, src: "figs/a.png" }, pngStatus({ fileHash: undefined, embeddedHashes: {} }), RID), PREDATE, "a src the host sent no hash for, as before");
  assert.equal(unknownReason({ ...t, hash: "" }, text, RID), "This region was saved without the image's hash, so a later change to the image cannot be detected.", "the comment's own gap comes first");
});

// ── a region composer re-found on the right twin ───────────────────────────────────────────────────

const TWINS_SRC = "![a](figs/p.png)\n\n![b](figs/p.png)\n";
const TWINS_HTML = '<p><img src="figs/p.png" alt="a"></p>\n<p><img src="figs/p.png" alt="b"></p>\n';
const pendingOn = (img: E): boolean => !!(img.parentNode as E).querySelector(".fc-overlay .fc-region-pending");
const lastDrawnFrom = (): unknown => (drawn[drawn.length - 1] || [])[0];

test("a region composer open on the SECOND of two embeds of one figure survives a repaint on the second: the pending rectangle and the thumbnail follow its embed line's picture, not the first twin, and Save anchors to that embed", async () => {
  let text = TWINS_SRC;
  const h = await harness({ kind: "rendered", html: TWINS_HTML, src: TWINS_SRC, text: () => text });
  await h.ok({ embeddedHashes: {} });
  await h.open({ embeddedHashes: {} });
  const [a, b] = h.qa(".fileview-md img");
  drawn.length = 0;
  h.drag((b.parentNode as E).querySelector(".fc-overlay")!, [150, 240], [250, 300]);
  assert.equal(h.q(".fc-composer")!.hidden, false);
  assert.equal(pendingOn(b), true, "the pending rectangle is on the picture dragged on");
  assert.equal(pendingOn(a), false);
  assert.equal(lastDrawnFrom(), b, "the composer's thumbnail is cut from it");
  h.input().value = "The axis";
  // the poll saw the file move and reloaded it: fresh nodes, the same text
  h.repaint(TWINS_HTML);
  const [a2, b2] = h.qa(".fileview-md img");
  assert.notEqual(b2, b, "new picture nodes");
  assert.equal(pendingOn(b2), true, "the pending rectangle is on the NEW second picture");
  assert.equal(pendingOn(a2), false, "not on the first twin of the same src");
  assert.equal(lastDrawnFrom(), b2, "the thumbnail too");
  assert.equal(h.input().value, "The axis", "the note stands");
  // a paragraph inserted above: the embed line is re-found in the new text (retargetComposer), and the picture follows it
  text = "Intro.\n\n" + TWINS_SRC;
  h.repaint("<p>Intro.</p>\n" + TWINS_HTML);
  const [a3, b3] = h.qa(".fileview-md img");
  assert.equal(h.q(".fc-composer-ref .fc-tag"), null, "no 'passage changed': the embed line was re-found");
  assert.equal(pendingOn(b3), true);
  assert.equal(pendingOn(a3), false);
  assert.equal(lastDrawnFrom(), b3);
  h.input().value = "The axis label is wrong.";
  h.input().dispatch("keydown", { key: "Enter" });
  await tick();
  const c = h.last();
  const at = text.indexOf("![b]");
  assert.equal(c.verb, "comment");
  assert.equal(c.args.hintOffset, at, "anchored to the second embed, the one the preview stood on");
  assert.equal(c.args.anchor.quote, "![b](figs/p.png)");
  assert.deepEqual(c.args.target, { kind: "image", region: REGION, src: "figs/p.png" });
  h.dispose();
});

test("the same composer on the FIRST twin stays on the first across a repaint (the order, not the last match)", async () => {
  const h = await harness({ kind: "rendered", html: TWINS_HTML, src: TWINS_SRC });
  await h.ok({ embeddedHashes: {} });
  await h.open({ embeddedHashes: {} });
  const [a] = h.qa(".fileview-md img");
  h.drag((a.parentNode as E).querySelector(".fc-overlay")!, [150, 240], [250, 300]);
  h.repaint(TWINS_HTML);
  const [a2, b2] = h.qa(".fileview-md img");
  assert.equal(pendingOn(a2), true);
  assert.equal(pendingOn(b2), false);
  h.input().value = "First.";
  h.input().dispatch("keydown", { key: "Enter" });
  await tick();
  assert.equal(h.last().args.hintOffset, 0);
  h.dispose();
});

// ── a malformed region ─────────────────────────────────────────────────────────────────────────────

const noNaN = (): boolean => drawn.every((args) => args.every((v) => typeof v !== "number" || !Number.isNaN(v)));

test("a region the sidecar holds without its h paints no rectangle and crops no canvas: the card wears 'unreadable', says so in words with Re-place as the way out, and its reference is no link; string coordinates likewise; a well-formed region beside it paints as before; resolved, the tag goes", async () => {
  const bad = regionComment({}, { region: { x: 0.1, y: 0.2, w: 0.3 } });
  const good = regionComment({ id: "c2", ts: T0 + 1, body: "Fine." });
  const h = await harness();
  drawn.length = 0;
  await h.ok({ ...withStore([bad, good]), fileHash: H1 });
  await h.open({ ...withStore([bad, good]), fileHash: H1 });
  assert.equal(h.qa(".fc-region").length, 1, "one rectangle: the well-formed region's");
  assert.equal(h.q('.fc-region[data-id="' + RID + '"]'), null, "none for the malformed one");
  assert.ok(h.q('.fc-region[data-id="c2"]'));
  assert.deepEqual(h.tags(RID), ["unreadable"]);
  assert.equal(tagOf(h, RID).title, UNREADABLE + " " + REPLACE_NOW);
  const ref = h.q('.fc-card[data-id="' + RID + '"] .fc-ref')!;
  assert.equal(ref.textContent, "the region at 0.10, 0.20, 0.30, ?", "the reference says which value is unreadable");
  assert.equal(ref.getAttribute("data-act"), null, "nothing on the picture to scroll to");
  h.click('.fc-card[data-id="' + RID + '"] .fc-card-head');
  const card = h.q('.fc-card.open[data-id="' + RID + '"]')!;
  assert.equal(card.querySelector("canvas.fc-crop"), null, "no thumbnail: a NaN crop made a 0×0 canvas");
  assert.equal(card.querySelector(".fc-note")!.textContent, UNREADABLE + " " + REPLACE_NOW);
  assert.ok(card.querySelector('[data-act="fcreplace"]'), "Re-place is the way out: it writes a region the host validates");
  h.click('.fc-card[data-id="c2"] .fc-card-head');
  assert.ok(h.q('.fc-card.open[data-id="c2"] canvas.fc-crop'), "the well-formed region's card has its thumbnail");
  assert.equal(noNaN(), true, "nothing drew with a NaN");
  assert.deepEqual(h.tags("c2"), []);
  // string coordinates: not a region either (the host refuses one); every slot unreadable
  await h.restatus({ ...withStore([regionComment({}, { region: { x: "0.1", y: "0.2", w: "0.3", h: "0.4" } })]), fileHash: H1 });
  assert.equal(h.qa(".fc-region").length, 0);
  assert.deepEqual(h.tags(RID), ["unreadable"]);
  assert.equal(h.q('.fc-card[data-id="' + RID + '"] .fc-ref')!.textContent, "the region at ?, ?, ?, ?");
  assert.equal(h.q('.fc-card.open[data-id="' + RID + '"] canvas.fc-crop'), null);
  assert.equal(noNaN(), true);
  // resolved: nothing left to report, as with stale and unknown
  await h.restatus({ ...withStore([regionComment({ resolved: true }, { region: { x: 0.1, y: 0.2, w: 0.3 } })]), fileHash: H1 });
  h.click('[data-act="fcresolved"]');
  assert.deepEqual(h.tags(RID), ["resolved"]);
  h.dispose();
});

// ── Re-place with the card collapsed ───────────────────────────────────────────────────────────────

const TWO_HTML = '<p><img src="figure.png" alt="Figure"></p>\n<p><img src="other.png" alt="Other"></p>\n';
const TWO_SRC = "![Figure](figure.png)\n\n![Other](other.png)\n";
const onFigure = (): StoreComment => embedded({ anchor: { quote: "![Figure](figure.png)", prefix: "", suffix: "\n\n![Other](other.png)\n" } });

test("a Re-place whose card was collapsed after arming: a drag on another figure re-opens the card with the refusal row; a drag on the comment's figure re-opens it with the loader for the retarget, and the card stays open when the reply lands", async () => {
  const st = { ...withStore([onFigure()], "docs/report.md"), embeddedHashes: { "figure.png": H1 } };
  const h = await harness({ kind: "rendered", html: TWO_HTML, src: TWO_SRC });
  await h.ok(st);
  await h.open(st);
  const [fig, other] = h.qa(".fileview-md img");
  h.click('.fc-card[data-id="' + RID + '"] .fc-card-head');
  h.click('.fc-card.open [data-act="fcreplace"]');
  assert.equal((fig.parentNode as E).querySelector(".fc-overlay")!.classList.contains("fc-replacing"), true, "re-place pending");
  h.click('.fc-card.open[data-id="' + RID + '"] .fc-card-head');   // collapsed while scrolling the panel
  assert.equal(h.q(".fc-card.open"), null, "the card is collapsed");
  assert.equal(h.q(".fc-composer-ref .fc-note")!.textContent.startsWith("Drag the comment's new place on the image"), true, "the re-place is still pending");
  const before = h.posted.length;
  h.drag((other.parentNode as E).querySelector(".fc-overlay")!, [150, 240], [250, 300]);
  assert.equal(h.posted.length, before, "nothing sent");
  assert.ok(h.q('.fc-card.open[data-id="' + RID + '"]'), "the drag's answer opens the card it is about");
  assert.equal(h.q('.fc-card.open[data-id="' + RID + '"] .fc-err')!.childNodes[0].textContent, "Draw the new place on the figure this comment is on, not on another one.");
  assert.equal(h.q('.fc-card[data-id="' + RID + '"]')!.scrolled, 1, "and scrolls to it");
  assert.equal(h.q(".fc-composer-ref .fc-note")!.textContent.startsWith("Drag the comment's new place"), true, "the re-place still waits for the right figure");
  // collapsed again, the right figure: the retarget goes, and the wait shows on the re-opened card
  h.click('.fc-card.open[data-id="' + RID + '"] .fc-card-head');
  assert.equal(h.q(".fc-card.open"), null);
  h.drag((fig.parentNode as E).querySelector(".fc-overlay")!, [150, 240], [250, 300]);
  await tick();
  assert.equal(h.last().verb, "retarget");
  assert.ok(h.q('.fc-card.open[data-id="' + RID + '"] .fc-load'), "the loader for the round trip, on the open card");
  assert.equal(h.q('.fc-card.open[data-id="' + RID + '"] .fc-err'), null, "the earlier refusal is cleared by the drag that went");
  assert.equal(h.q(".fc-composer")!.hidden, true, "the re-place is done");
  await h.ok(st);
  assert.ok(h.q('.fc-card.open[data-id="' + RID + '"]'), "still open once the reply lands");
  assert.equal(h.q(".fc-load"), null, "the wait is over");
  h.dispose();
});

// ── closing the panel during a Re-place ────────────────────────────────────────────────────────────

test("closing the panel ends a pending Re-place: the cue leaves the disarmed picture, Escape is the viewer's again, a drag posts nothing, and reopening restores no re-place — Re-place works afresh", async () => {
  const h = await harness();
  await h.ok(withStore([regionComment()]));
  await h.open(withStore([regionComment()]));
  const viewer: string[] = [];
  const onKey = (ev: Ev) => { if (ev.key === "Escape") viewer.push(ev.defaultPrevented ? "prevented" : "seen"); };   // file-view.ts's document-level onKey
  doc.addEventListener("keydown", onKey);
  try {
    h.click('.fc-card[data-id="' + RID + '"] .fc-card-head');
    h.click('.fc-card.open [data-act="fcreplace"]');
    const overlay = h.q(".fc-overlay")!;
    assert.equal(overlay.classList.contains("fc-replacing"), true, "re-place pending, the cue on the picture");
    h.button.dispatch("click");                        // the Comments button closes the panel
    assert.equal(overlay.classList.contains("fc-overlay-off"), true, "closed: disarmed");
    assert.equal(overlay.classList.contains("fc-replacing"), false, "no cue for a gesture the picture no longer takes");
    const before = h.posted.length;
    h.drag(overlay, [150, 240], [250, 300]);
    assert.equal(h.posted.length, before, "a drag on the closed panel's picture posts nothing, as before");
    doc.body.dispatch("keydown", { key: "Escape" });
    assert.deepEqual(viewer, ["seen"], "Escape reaches the viewer: nothing pending swallows it");
    await h.open(withStore([regionComment()]));
    assert.equal(h.q(".fc-composer")!.hidden, true, "reopened: no re-place is restored");
    assert.equal(overlay.classList.contains("fc-replacing"), false);
    assert.ok(h.q('.fc-region[data-id="' + RID + '"]'), "the comment kept its place");
    assert.ok(h.q('.fc-card.open[data-id="' + RID + '"]'), "the card is open as it was left: the keyed expand state survives the close");
    h.click('.fc-card.open [data-act="fcreplace"]');
    assert.equal(overlay.classList.contains("fc-replacing"), true, "Re-place is armed afresh");
    assert.equal(h.q(".fc-composer")!.hidden, false);
  } finally { doc.removeEventListener("keydown", onKey); }
  h.dispose();
});

// ── the stale card in words ────────────────────────────────────────────────────────────────────────

test("an open stale region card says in words what the tag's title says, with the recourse THIS card offers: Re-place where it is offered; on a coarse pointer, resolve or re-place from a desktop, with no Re-place button; with the picture out of view, resolve or re-place from the view that shows it", async () => {
  const stale = { ...withStore([regionComment()]), fileHash: H2 };   // H1 stored, H2 now: the image was regenerated
  const h = await harness();
  await h.ok(stale);
  await h.open(stale);
  assert.deepEqual(h.tags(RID), ["stale"]);
  assert.equal(tagOf(h, RID).title, STALE + " " + REPLACE_NOW);
  h.click('.fc-card[data-id="' + RID + '"] .fc-card-head');
  assert.equal(openNote(h, RID)!.textContent, STALE + " " + REPLACE_NOW, "the open card says it in words");
  assert.ok(h.q('.fc-card.open [data-act="fcreplace"]'), "and the button it names is there");
  // current again: no line
  await h.restatus({ ...withStore([regionComment()]), fileHash: H1 });
  assert.deepEqual(h.tags(RID), []);
  assert.equal(openNote(h, RID), null);
  h.dispose();
  // a phone: a coarse pointer draws nothing, so Re-place is absent — the words send the person to resolve, or to a desktop
  coarse = true;
  try {
    const h2 = await harness();
    await h2.ok(stale);
    await h2.open(stale);
    assert.deepEqual(h2.tags(RID), ["stale"]);
    h2.click('.fc-card[data-id="' + RID + '"] .fc-card-head');
    assert.equal(h2.q('.fc-card.open [data-act="fcreplace"]'), null, "no Re-place on a coarse pointer");
    const words = STALE + " Resolve it, or re-place it from a computer: drawing a region needs a mouse.";
    assert.equal(tagOf(h2, RID).title, words);
    assert.equal(openNote(h2, RID)!.textContent, words, "reachable without hover: a title never reaches touch");
    assert.ok(h2.q('.fc-card.open [data-act="fcresolve"]'), "Resolve, the recourse named, is on the card");
    h2.dispose();
  } finally { coarse = null; }
  // the picture out of view: the figure's embed was dropped from the page (the anchor detached), and the region is stale
  const gone = { ...withStore([embedded()], "docs/report.md"), embeddedHashes: { "figure.png": H2 } };
  const h3 = await harness({ kind: "rendered", html: "<p>No figure now.</p>\n", src: "No figure now.\n" });
  await h3.ok(gone);
  await h3.open(gone);
  assert.ok(h3.tags(RID).includes("stale"));
  h3.click('.fc-card[data-id="' + RID + '"] .fc-card-head');
  assert.equal(h3.q('.fc-card.open [data-act="fcreplace"]'), null, "nothing to draw on");
  const away = STALE + " Resolve it, or re-place it from the view that shows the image.";
  assert.equal(tagOf(h3, RID).title, away);
  assert.equal(openNote(h3, RID)!.textContent, away);
  h3.dispose();
});
