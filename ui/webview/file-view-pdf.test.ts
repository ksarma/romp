// The PDF pages body at the REAL openFileView (plans/file-review.md, Slice 4; "Images and PDFs"; decision 12) — what
// file-view-seam.test.ts's two-page, resolve-at-once stand-in cannot reach: a document pdf.js opens with NO pages, a
// render that resolves after the pages were dropped (the panel closed and reopened while it was in flight), a chunk load
// that settles after the panel closed, an engine too old for pdf.js (refused before the chunk is fetched), the reader's
// page carried across the pages/frame flip, and the frame kept — not reloaded — when the panel closes over a fallback.
// The DOM stand-in below is the seam test's (ancestry, ids, attributes, events, a small selector engine), copied rather
// than shared because that module installs its globals and registers its tests at import; keep the two in step. The
// chunk stand-in here takes a page count and can hold its resolution until a test releases it, which is how the stale
// paths are reached. Synthetic fixtures only: the notes-api world, placeholder ids, TESTHOST.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx } from "./file-view";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const VIEW = web("file-view.ts");

// ── a DOM stand-in: ancestry, ids, attributes, events with capture and bubbling, a small selector engine ──
class Ev {
  target: El | Txt | null = null;
  currentTarget: El | null = null;
  defaultPrevented = false;
  stopped = false;
  key: string; ctrlKey: boolean; metaKey: boolean;
  constructor(public type: string, init: { key?: string; ctrlKey?: boolean; metaKey?: boolean } = {}) {
    this.key = init.key || ""; this.ctrlKey = !!init.ctrlKey; this.metaKey = !!init.metaKey;
  }
  preventDefault(): void { this.defaultPrevented = true; }
  stopPropagation(): void { this.stopped = true; }
}
type Listener = (ev: Ev) => void;
type Reg = { type: string; cb: Listener; capture: boolean; once: boolean };
const optsOf = (o?: boolean | { capture?: boolean; once?: boolean }) =>
  typeof o === "boolean" ? { capture: o, once: false } : { capture: !!(o && o.capture), once: !!(o && o.once) };
const kebab = (k: string) => k.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
class Txt {
  nodeType = 3;
  parentNode: El | null = null;
  constructor(public data: string) {}
  get textContent(): string { return this.data; }
  get parentElement(): El | null { return this.parentNode; }
  splitText(off: number): Txt {
    const tail = new Txt(this.data.slice(off));
    this.data = this.data.slice(0, off);
    const p = this.parentNode;
    if (p) { const i = p.childNodes.indexOf(this); p.childNodes.splice(i + 1, 0, tail); tail.parentNode = p; }
    return tail;
  }
}
type Compound = { tag: string | null; id: string | null; classes: string[]; attrs: Array<[string, string | null]> };
/** Comma groups of descendant chains (`A B`), each link a compound `tag#id.class[attr="v"]`. */
function parseSel(sel: string): Compound[][] {
  return sel.split(",").map((g) => g.trim()).filter(Boolean).map((g) => g.split(/\s+/).map((s) => {
    const m = /^([a-zA-Z][\w-]*)?(#[\w-]+)?((?:\.[\w-]+)*)((?:\[[\w-]+(?:="[^"]*")?\])*)$/.exec(s);
    if (!m) throw new Error("stand-in: unsupported selector " + s);
    const classes = (m[3].match(/\.[\w-]+/g) || []).map((c) => c.slice(1));
    const attrs: Array<[string, string | null]> = [];
    for (const a of m[4].match(/\[[^\]]+\]/g) || []) { const am = /^\[([\w-]+)(?:="([^"]*)")?\]$/.exec(a)!; attrs.push([am[1], am[2] ?? null]); }
    return { tag: m[1] ? m[1].toUpperCase() : null, id: m[2] ? m[2].slice(1) : null, classes, attrs };
  }));
}
type Rect = { left: number; top: number; right: number; bottom: number; width: number; height: number };
const rect = (top: number, bottom: number): Rect => ({ left: 0, top, right: 800, bottom, width: 800, height: bottom - top });
class El {
  nodeType = 1;
  tagName: string;
  parentNode: El | null = null;
  childNodes: Array<El | Txt> = [];
  attrs = new Map<string, string>();
  listeners: Reg[] = [];
  hidden = false; disabled = false; title = ""; type = ""; value = ""; placeholder = ""; spellcheck = true; wrap = "";
  src = ""; alt = ""; href = ""; download = ""; target = ""; rel = "";
  innerHTML = "";
  style: Record<string, string> = {};
  onclick: ((ev: Ev) => void) | null = null;
  onload: (() => void) | null = null;            // a <script> tag's load, fired by the test that stands in for the fetch
  onerror: (() => void) | null = null;
  scrolled = 0;                                  // scrollIntoView calls
  rect: Rect = rect(0, 0);                       // getBoundingClientRect's answer; a test lays pages out by setting it
  constructor(tag: string) { this.tagName = tag.toUpperCase(); }
  get id(): string { return this.attrs.get("id") || ""; }
  set id(v: string) { this.attrs.set("id", v); }
  get isConnected(): boolean { return doc.body.contains(this); }
  get ownerDocument(): typeof doc { return doc; }
  get parentElement(): El | null { return this.parentNode; }
  get firstChild(): El | Txt | null { return this.childNodes[0] || null; }
  get className(): string { return this.attrs.get("class") || ""; }
  set className(v: string) { this.attrs.set("class", v); }
  get classes(): string[] { return this.className.split(/\s+/).filter(Boolean); }
  classList = {
    add: (...c: string[]) => { const s = new Set(this.classes); for (const x of c) s.add(x); this.className = [...s].join(" "); },
    remove: (...c: string[]) => { const s = new Set(this.classes); for (const x of c) s.delete(x); this.className = [...s].join(" "); },
    toggle: (c: string, on?: boolean) => { const want = on === undefined ? !this.classes.includes(c) : on; if (want) this.classList.add(c); else this.classList.remove(c); },
    contains: (c: string) => this.classes.includes(c),
  };
  dataset: Record<string, string> = new Proxy({} as Record<string, string>, {
    get: (_, k) => this.attrs.get("data-" + kebab(String(k))) as string,
    set: (_, k, v) => { this.attrs.set("data-" + kebab(String(k)), String(v)); return true; },
    has: (_, k) => this.attrs.has("data-" + kebab(String(k))),
    deleteProperty: (_, k) => { this.attrs.delete("data-" + kebab(String(k))); return true; },
  });
  get textContent(): string { return this.childNodes.map((c) => c.textContent).join(""); }
  set textContent(v: string) { for (const c of this.childNodes) c.parentNode = null; this.childNodes = []; if (v !== "") this.appendChild(new Txt(v)); }
  private detach(n: El | Txt): void { const p = n.parentNode; if (p) { const i = p.childNodes.indexOf(n); if (i >= 0) p.childNodes.splice(i, 1); n.parentNode = null; } }
  appendChild<T extends El | Txt>(n: T): T { this.detach(n); this.childNodes.push(n); n.parentNode = this; return n; }
  prepend(...ns: Array<El | Txt>): void { for (const n of ns.slice().reverse()) { this.detach(n); this.childNodes.unshift(n); n.parentNode = this; } }
  insertBefore<T extends El | Txt>(n: T, ref: El | Txt | null): T {
    if (!ref) return this.appendChild(n);
    this.detach(n);
    const i = this.childNodes.indexOf(ref);
    this.childNodes.splice(i < 0 ? this.childNodes.length : i, 0, n); n.parentNode = this; return n;
  }
  removeChild<T extends El | Txt>(n: T): T { this.detach(n); return n; }
  replaceChildren(...c: Array<El | Txt>): void { for (const x of this.childNodes) x.parentNode = null; this.childNodes = []; for (const x of c) this.appendChild(x); }
  remove(): void { this.detach(this); }
  normalize(): void {
    const out: Array<El | Txt> = [];
    for (const c of this.childNodes) {
      if (c instanceof Txt) { if (!c.data) { c.parentNode = null; continue; } const last = out[out.length - 1]; if (last instanceof Txt) { last.data += c.data; c.parentNode = null; continue; } }
      else c.normalize();
      out.push(c);
    }
    this.childNodes = out;
  }
  setAttribute(k: string, v: string): void { this.attrs.set(k, v); }
  getAttribute(k: string): string | null { return this.attrs.has(k) ? (this.attrs.get(k) as string) : null; }
  hasAttribute(k: string): boolean { return this.attrs.has(k); }
  removeAttribute(k: string): void { this.attrs.delete(k); }
  contains(n: El | Txt | null): boolean { for (let x: El | Txt | null = n; x; x = x.parentNode) if (x === this) return true; return false; }
  private fits(c: Compound): boolean {
    return (!c.tag || c.tag === this.tagName) && (!c.id || c.id === this.id) && c.classes.every((k) => this.classes.includes(k))
      && c.attrs.every(([a, v]) => this.attrs.has(a) && (v === null || this.attrs.get(a) === v));
  }
  matches(sel: string): boolean {
    return parseSel(sel).some((chain) => {
      if (!this.fits(chain[chain.length - 1])) return false;
      let k = chain.length - 2;
      for (let a: El | null = this.parentNode; a && k >= 0; a = a.parentNode) if (a.fits(chain[k])) k--;
      return k < 0;
    });
  }
  closest(sel: string): El | null { for (let x: El | null = this; x; x = x.parentNode) if (x.matches(sel)) return x; return null; }
  querySelectorAll(sel: string): El[] {
    const out: El[] = [];
    const visit = (n: El) => { for (const c of n.childNodes) if (c instanceof El) { if (c.matches(sel)) out.push(c); visit(c); } };
    visit(this);
    return out;
  }
  querySelector(sel: string): El | null { return this.querySelectorAll(sel)[0] || null; }
  addEventListener(type: string, cb: Listener, o?: boolean | { capture?: boolean; once?: boolean }): void { this.listeners.push({ type, cb, ...optsOf(o) }); }
  removeEventListener(type: string, cb: Listener, o?: boolean | { capture?: boolean }): void {
    const cap = optsOf(o).capture;
    this.listeners = this.listeners.filter((l) => !(l.type === type && l.cb === cb && l.capture === cap));
  }
  dispatchEvent(ev: Ev): boolean { return dispatch(this, ev); }
  click(): void { this.dispatchEvent(new Ev("click")); }
  focus(): void { doc.activeElement = this; }
  blur(): void { if (doc.activeElement === this) doc.activeElement = null; }
  scrollIntoView(): void { this.scrolled++; }
  getBoundingClientRect(): Rect { return this.rect; }
  get offsetWidth(): number { return 0; }
}
const doc = {
  listeners: [] as Reg[],
  body: null as unknown as El,
  head: null as unknown as El,
  hidden: false,
  activeElement: null as El | null,
  createElement: (tag: string) => new El(tag),
  createTextNode: (s: string) => new Txt(s),
  getElementById: (id: string): El | null => doc.body.querySelector("#" + id),
  querySelectorAll: (sel: string): El[] => doc.body.querySelectorAll(sel),
  addEventListener(type: string, cb: Listener, o?: boolean | { capture?: boolean; once?: boolean }): void { doc.listeners.push({ type, cb, ...optsOf(o) }); },
  removeEventListener(type: string, cb: Listener, o?: boolean | { capture?: boolean }): void {
    const cap = optsOf(o).capture;
    doc.listeners = doc.listeners.filter((l) => !(l.type === type && l.cb === cb && l.capture === cap));
  },
  contains: (n: El | Txt | null) => doc.body.contains(n),
};
doc.body = new El("body"); doc.head = new El("head");
function dispatch(target: El | Txt, ev: Ev): boolean {
  ev.target = target;
  const chain: El[] = [];
  for (let n: El | null = target instanceof El ? target : target.parentNode; n; n = n.parentNode) chain.push(n);
  const run = (owner: { listeners: Reg[] }, capture: boolean, node: El | null): boolean => {
    for (const l of owner.listeners.slice()) {
      if (l.type !== ev.type || l.capture !== capture) continue;
      if (l.once) owner.listeners = owner.listeners.filter((x) => x !== l);
      ev.currentTarget = node; l.cb.call(node, ev);
      if (ev.stopped) return true;
    }
    if (node && !capture && ev.type === "click" && node.onclick) node.onclick(ev);
    return false;
  };
  if (run(doc, true, null)) return !ev.defaultPrevented;
  for (let i = chain.length - 1; i >= 0; i--) if (run(chain[i], true, chain[i])) return !ev.defaultPrevented;
  for (const n of chain) if (run(n, false, n)) return !ev.defaultPrevented;
  run(doc, false, null);
  return !ev.defaultPrevented;
}
const win: any = new EventTarget();
win.parent = win; win.innerWidth = 1200; win.innerHeight = 800;
win.getSelection = () => null;
win.confirm = () => true;
win.postMessage = () => { /* our own window: nothing listens here */ };
(globalThis as any).window = win;
(globalThis as any).document = doc;
const store = new Map<string, string>();
(globalThis as any).localStorage = {
  getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
  setItem: (k: string, v: string) => { store.set(k, String(v)); },
  removeItem: (k: string) => { store.delete(k); },
};
win.__rompEditor = { mount() { throw new Error("no test here edits"); } };

// ── the PDF renderer chunk the viewer's pdfChunkLoad resolves from ─────────────────────────────────────
// The chunk's own DOM shape (div.fileview-pdf > div.fileview-pdf-page[data-page] > canvas.fileview-pdf-canvas), `pages`
// shells, the root appended and page 1 "drawn" before the promise resolves — as the real chunk does. `defer` holds each
// render's resolution until the test calls release(i), which is how a resolution AFTER the pages were dropped is reached.
const pdf = {
  renders: 0, disposed: 0, pages: 2, defer: false, refuse: null as string | null,
  opts: null as null | { maxBytes?: number; onPage?: (p: unknown) => void },
  roots: [] as El[], pending: [] as Array<() => void>,
  release(i: number): void { const r = this.pending[i]; assert.ok(r, "render " + i + " is pending"); r(); },
};
const chunkStub = {
  DEFAULT_MAX_BYTES: 25 * 1024 * 1024,
  render(bytes: ArrayBuffer, container: El, opts: { maxBytes?: number; onPage?: (p: unknown) => void } = {}) {
    pdf.renders++; pdf.opts = opts;
    if (pdf.refuse) return Promise.reject(new Error(pdf.refuse));
    const root = doc.createElement("div"); root.className = "fileview-pdf";
    for (let i = 1; i <= pdf.pages; i++) {
      const w = doc.createElement("div"); w.className = "fileview-pdf-page"; w.dataset.page = String(i); w.style.position = "relative";
      const c = doc.createElement("canvas"); c.className = "fileview-pdf-canvas"; c.dataset.page = String(i);
      w.appendChild(c); root.appendChild(w);
    }
    container.appendChild(root); pdf.roots.push(root);
    if (pdf.pages) opts.onPage?.({ index: 1, canvas: root.childNodes[0], width: 800, height: 1035 });
    const handle = { pages: pdf.pages, dispose() { pdf.disposed++; root.remove(); } };
    if (!pdf.defer) return Promise.resolve(handle);
    return new Promise<typeof handle>((res) => { pdf.pending.push(() => res(handle)); });
  },
};
win.__rompPdf = chunkStub;

// ── the kernel's /file, /version and /sessions, as the viewer fetches them ──────────────────────────
type Served = { bytes: string | Uint8Array; type: string; mtimeNs: string };
const disk: Record<string, Served> = {};
(globalThis as any).fetch = async (url: string) => {
  if (url.startsWith("/version")) return { json: async () => ({ fileEditing: true }) };
  if (url.startsWith("/sessions")) return { json: async () => [] };
  const p = decodeURIComponent((/[?&]path=([^&]*)/.exec(url) || [])[1] || "");
  const f = disk[p];
  const headers = { get: (h: string) => (f ? (h === "Content-Type" ? f.type : h === "X-Romp-Mtime-Ns" ? f.mtimeNs : h === "X-Romp-Text-Utf8" ? "1" : null) : null) };
  if (!f) return { ok: false, status: 404, headers, text: async () => "no such file: " + p };
  return {
    ok: true, status: 200, headers,
    text: async () => String(f.bytes),
    blob: async () => new Blob([f.bytes as unknown as BlobPart], { type: f.type }),
  };
};

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ROOT = "/repo/notes-api";
const DECK = ROOT + "/docs/deck.pdf";
const BIG = ROOT + "/docs/atlas.pdf";
const MT = "1757145600000000001";
const NOTICE_TAIL = " — showing the browser's PDF viewer instead; comments on the whole file still work.";

// ── the probe: an action whose only job is to keep the ctx the viewer hands it ──────────────────────
let seam: FileViewActionCtx | null = null;
let paints = 0;
let fvMod: typeof import("./file-view") | null = null;
async function mod(): Promise<typeof import("./file-view")> {
  if (fvMod) return fvMod;
  fvMod = await import("./file-view");
  fvMod.initFileView(() => { /* nothing here answers the panel */ });
  fvMod.registerFileViewAction({
    id: "seam-probe",
    mount(ctx) { seam = ctx; ctx.onRendered(() => { paints++; }); return null; },
  });
  return fvMod;
}
const settle = async () => { for (let i = 0; i < 8; i++) await new Promise<void>((r) => setImmediate(r)); };
type Open = { fv: typeof import("./file-view"); ctx: FileViewActionCtx; wrap: El; body: El };
async function open(p: string, t: TestContext): Promise<Open> {
  const fv = await mod();
  disk[DECK] = { bytes: "%PDF-1.4\n", type: "application/pdf", mtimeNs: MT };
  paints = 0; seam = null;
  pdf.renders = 0; pdf.disposed = 0; pdf.opts = null; pdf.refuse = null; pdf.roots.length = 0; pdf.pending.length = 0;
  assert.equal(fv.openFileView(p, SID), true, "the open happened");
  t.after(() => { fv.closeFileView(); pdf.pages = 2; pdf.defer = false; });
  await settle();
  const wrap = doc.getElementById("romp-fileview")!;
  assert.ok(wrap, "the viewer is up");
  const body = wrap.querySelector(".fileview-body")!;
  assert.ok(seam, "the probe action was mounted with the ctx");
  return { fv, ctx: seam!, wrap, body };
}
const panel = () => new El("div") as unknown as HTMLElement;
const frameIn = (body: El) => body.querySelector("iframe.fileview-frame");
const noteIn = (body: El) => body.querySelector(".fileview-pdffall .fileview-err");
/** Lay the scroller and its page shells out so that page `at` (1-based) sits under the scroller's middle. */
function layOut(body: El, shells: HTMLElement[], at: number): void {
  body.rect = rect(0, 800);                                                    // the scroller: 800 tall, middle at 400
  shells.forEach((s, i) => { (s as unknown as El).rect = rect((i - (at - 1)) * 1000 - 300, (i - (at - 1)) * 1000 + 700); });
}

// ── a page-less document ───────────────────────────────────────────────────────────────────────────

test("a PDF pdf.js opens with no pages: the frame under a notice saying so, the document released — never an empty pane", async (t) => {
  pdf.pages = 0;
  const { ctx, body } = await open(DECK, t);
  ctx.aside(panel()); await settle();
  assert.equal(pdf.renders, 1, "the chunk was asked, and opened the document");
  assert.equal(noteIn(body)!.textContent, "this PDF has no pages" + NOTICE_TAIL);
  const frame = frameIn(body)!;
  assert.ok(frame && frame.src.startsWith("blob:"), "the browser's viewer under the notice");
  assert.equal(body.querySelector(".fileview-load"), null, "no loader left behind");
  assert.equal(body.querySelector(".fileview-pdfhost"), null, "the chunk's host went with it");
  assert.equal(body.querySelector(".fileview-pdf"), null, "…and the empty root: nothing to overlay, nothing blank");
  assert.equal(pdf.disposed, 1, "the handle was disposed: the document and its worker released");
  assert.equal(ctx.mediaElement(), frame as unknown as HTMLElement, "the frame is the media element: whole-file comments work");
  assert.deepEqual(ctx.pdfPages(), []);
  assert.equal(paints, 2, "the frame's paint, after the open's");
});

// ── the stale-render guards (a render or a chunk load that settles after the pages were dropped) ──────

test("a render resolving after the panel closed and reopened is disposed at once and mounts nothing; the live render's handle is the one the close releases", async (t) => {
  pdf.defer = true;
  const { ctx, body } = await open(DECK, t);
  ctx.aside(panel()); await settle();
  assert.equal(pdf.renders, 1); assert.equal(pdf.pending.length, 1, "render A is in flight");
  const rootA = pdf.roots[0];
  assert.ok(body.querySelector(".fileview-load"), "the loader holds the body until page 1 is drawn");
  ctx.aside(null);                                       // closed before A resolved: the frame
  assert.ok(frameIn(body), "the frame is back");
  assert.equal(pdf.disposed, 0, "nothing to dispose yet — A has not resolved");
  ctx.aside(panel()); await settle();                    // reopened: render B, with A still pending
  assert.equal(pdf.renders, 2); assert.equal(pdf.pending.length, 2, "two renders in flight");
  assert.ok(body.querySelector(".fileview-load"), "B's loader");
  const before = paints;
  pdf.release(0); await settle();                        // A resolves late
  assert.equal(pdf.disposed, 1, "the stale resolution is disposed on arrival — its document and worker released");
  assert.equal(paints, before, "…and paints nothing: B's loader still shows");
  assert.ok(body.querySelector(".fileview-load"), "B's loader is untouched");
  assert.equal(rootA.isConnected, false, "A's root is not in the document");
  pdf.release(1); await settle();                        // B resolves
  assert.equal(body.querySelector(".fileview-load"), null, "B's page 1: the loader gives way");
  assert.equal(ctx.pdfPages().length, 2);
  assert.equal(paints, before + 1);
  assert.equal(pdf.disposed, 1, "B is live, not disposed");
  ctx.aside(null);
  assert.equal(pdf.disposed, 2, "the close releases B: both renders' documents are gone");
});

test("open, close, open before the chunk load settles asks the chunk once: the first load's continuation finds the body moved on", async (t) => {
  const { ctx, body } = await open(DECK, t);
  ctx.aside(panel());                                    // load 1 in flight
  ctx.aside(null);                                       // closed before it settled
  ctx.aside(panel());                                    // load 2 in flight
  await settle();
  assert.equal(pdf.renders, 1, "render() ran for the open that is still current, not for the one that closed");
  assert.equal(ctx.pdfPages().length, 2);
  assert.equal(body.querySelectorAll(".fileview-pdf").length, 1, "one root in the body");
  assert.equal(pdf.roots[0].isConnected, true);
  ctx.aside(null);
  assert.equal(pdf.disposed, 1);
});

// ── the engine check: refused before the fetch, the browser named ────────────────────────────────────

test("an engine without the Iterator global, or without Promise.try, is refused before the chunk is fetched and the notice names the browser; one with both fetches the chunk and renders", async (t) => {
  // no chunk registered yet, and a hosting page's bundle tag to derive the chunk's URL from (the Files pane's)
  const saved = win.__rompPdf; win.__rompPdf = undefined;
  const tag = new El("script"); tag.src = "http://TESTHOST:29855/dist/files.js?v=1725300000"; tag.setAttribute("src", tag.src);
  doc.body.appendChild(tag);
  const g = globalThis as any; const P = Promise as any;
  const iter = g.Iterator; const hadTry = Object.prototype.hasOwnProperty.call(P, "try"); const origTry = P.try;
  const shim = (fn: (...a: unknown[]) => unknown, ...args: unknown[]) => new Promise((r) => r(fn(...args)));
  t.after(() => {
    win.__rompPdf = saved; tag.remove(); doc.head.replaceChildren();
    g.Iterator = iter;
    if (hadTry) P.try = origTry; else delete P.try;
  });
  // (1) no Iterator (Safari before 18.4, Firefox before 131, Chrome before 122): pdf.js's module body would throw
  P.try = shim; delete g.Iterator;
  let o = await open(DECK, t);
  o.ctx.aside(panel()); await settle();
  assert.equal(noteIn(o.body)!.textContent, "this browser is too old for the page renderer" + NOTICE_TAIL);
  assert.ok(frameIn(o.body), "the frame under the notice");
  assert.equal(doc.head.querySelectorAll("script").length, 0, "no chunk script tag: nothing was fetched");
  assert.equal(pdf.renders, 0);
  // (2) Iterator but no Promise.try (Chrome 122-127, Firefox 131-133): pdf.js's message handler would fail on every document
  g.Iterator = iter; delete P.try;
  o = await open(DECK, t);
  o.ctx.aside(panel()); await settle();
  assert.equal(noteIn(o.body)!.textContent, "this browser is too old for the page renderer" + NOTICE_TAIL);
  assert.equal(doc.head.querySelectorAll("script").length, 0, "still nothing fetched");
  // (3) both: the chunk's script tag is appended, at the bundle's own directory and ?v= token, and the loader waits on it
  P.try = shim;
  o = await open(DECK, t);
  o.ctx.aside(panel()); await settle();
  const scripts = doc.head.querySelectorAll("script");
  assert.equal(scripts.length, 1, "the chunk is fetched by one script tag");
  assert.equal(scripts[0].src, "http://TESTHOST:29855/dist/pdf-chunk.js?v=1725300000");
  assert.ok(o.body.querySelector(".fileview-load"), "the loader holds the body while the chunk loads");
  assert.equal(pdf.renders, 0);
  win.__rompPdf = chunkStub; scripts[0].onload!();       // the chunk registers and the tag fires load
  await settle();
  assert.equal(pdf.renders, 1, "the registered chunk rendered the pages");
  assert.equal(o.ctx.pdfPages().length, 2);
  assert.equal(o.body.querySelector(".fileview-load"), null);
});

// ── the reader's page across the flip ────────────────────────────────────────────────────────────────

test("the reader's page survives the flip: the frame the close builds opens at #page=N, the pages a reopen draws scroll to it, a reload with the panel open keeps it, and page 1 adds no fragment", async (t) => {
  pdf.pages = 10;
  const { ctx, body } = await open(DECK, t);
  const bare = frameIn(body)!.src;
  assert.ok(bare.startsWith("blob:") && !bare.includes("#"), "the frame at open: the bare object URL");
  ctx.aside(panel()); await settle();
  let shells = ctx.pdfPages();
  assert.equal(shells.length, 10);
  assert.equal(shells.reduce((n, s) => n + (s as unknown as El).scrolled, 0), 0, "a first open scrolls nothing: no page is known yet");
  layOut(body, shells, 7);                               // the reader scrolled to page 7
  ctx.aside(null);
  const frame = frameIn(body)!;
  assert.equal(frame.src, bare + "#page=7", "the frame opens on the reader's page (the PDF open parameter)");
  assert.equal(ctx.mediaElement(), frame as unknown as HTMLElement);
  ctx.aside(panel()); await settle();
  shells = ctx.pdfPages();
  assert.equal(pdf.renders, 2);
  assert.deepEqual(shells.map((s) => (s as unknown as El).scrolled), [0, 0, 0, 0, 0, 0, 1, 0, 0, 0], "the reopened pages scroll page 7 into view, once");
  // a reload while the panel is open: the page is read off the shells about to go, and the fresh pages come back to it
  layOut(body, shells, 3);                               // the reader has moved on to page 3
  ctx.reload(); await settle();
  shells = ctx.pdfPages();
  assert.equal(pdf.renders, 3, "the reload rendered again from the new bytes");
  assert.deepEqual(shells.map((s) => (s as unknown as El).scrolled), [0, 0, 1, 0, 0, 0, 0, 0, 0, 0], "…scrolled to page 3");
  // back at the top: the close builds the frame with no fragment, the bare URL exactly as before this carry existed
  layOut(body, shells, 1);
  ctx.aside(null);
  const again = frameIn(body)!;
  assert.ok(again.src.startsWith("blob:") && !again.src.includes("#"), "page 1 adds nothing");
  assert.notEqual(again.src, bare, "…at the reload's object URL");
});

test("the panel closing over the fallback keeps the frame — the document is not reloaded — and drops the notice; a reload rebuilds the frame at the new bytes' URL", async (t) => {
  disk[BIG] = { bytes: new Uint8Array(26 * 1024 * 1024), type: "application/pdf", mtimeNs: MT };
  t.after(() => { delete disk[BIG]; });
  const { ctx, body } = await open(BIG, t);
  const f0 = frameIn(body)!;
  ctx.aside(panel()); await settle();
  assert.equal(pdf.renders, 0, "over the cap: refused before the chunk");
  const f1 = frameIn(body)!;
  assert.ok(f1 && f1 !== f0, "the fallback's frame, under the cap notice");
  assert.ok(noteIn(body), "the notice");
  const before = paints;
  ctx.aside(null);
  assert.equal(frameIn(body), f1, "the SAME frame element: the browser's viewer keeps the reader's place");
  assert.equal(noteIn(body), null, "the notice — about the panel's rendering — is gone with the panel");
  assert.equal(ctx.mediaElement(), f1 as unknown as HTMLElement);
  assert.deepEqual(ctx.pdfPages(), []);
  assert.equal(paints, before + 1, "the panel hears the body change");
  // other bytes: the frame is rebuilt, as every media body is on a reload
  ctx.reload(); await settle();
  const f2 = frameIn(body)!;
  assert.ok(f2 && f2 !== f1, "a fresh frame at the reload's object URL");
  assert.notEqual(f2.src, f1.src);
  assert.equal(body.querySelector(".fileview-pdffall"), null, "the fallback column went with the old frame");
});

// ── pinned at source: the guards' shape, and the engine check ahead of the fetch ────────────────────

test("source: the pre- and post-render stale guards, the page-less refusal, and the engine check before the script tag", () => {
  const show = VIEW.split("const showPdfPages = () => {")[1].split("closeHooks.push(dropPdf);")[0];
  assert.match(show, /Promise\.all\(\[pdfChunkLoad\(\), blob\.arrayBuffer\(\)\]\)\.then\(\(\[pdf, bytes\]\) => \{\n\s*if \(my !== pdfSeq \|\| !wrap\.isConnected\) return;\n\s*return pdf\.render\(/,
    "a chunk load or bytes read settling after the body moved on calls render() for nothing");
  assert.match(show, /\}\)\.then\(\(h\) => \{\n\s*if \(my !== pdfSeq \|\| !wrap\.isConnected\) \{ h\.dispose\(\); return; \}/,
    "a render resolving after the body moved on is disposed — its document and worker released — and mounts nothing");
  assert.match(show, /if \(h\.pages === 0\) \{ h\.dispose\(\); fallback\("this PDF has no pages"\); return; \}/);
  assert.ok(show.indexOf("h.pages === 0") < show.indexOf("pdfHandle = h;"), "the page-less check precedes the mount");
  assert.match(show, /^\s*notePdfPage\(\);[^\n]*\n\s*dropPdf\(\);/m, "the reader's page is read before the shells are dropped");
  const loader = VIEW.split("const pdfChunkLoad = () =>")[1].split("}));")[0];
  const check = loader.indexOf('typeof (globalThis as any).Iterator !== "function" || typeof (Promise as any).try !== "function"');
  assert.ok(check > 0, "the engine check names both APIs");
  assert.ok(check > loader.indexOf("if (!self) return rej("), "after the URL derivation (a page with no bundle tag says so first)");
  assert.ok(check < loader.indexOf("document.head.appendChild(sc)"), "…and before the fetch");
  assert.match(loader, /rej\(new Error\("this browser is too old for the page renderer"\)\)/);
  // the frame path in renderBody: the kept frame first, then the page read, then the drop, then the aim after the mount
  const media = VIEW.split("if (isImage || isPdf) {")[1].split("if (text === null || editing) return;")[0];
  assert.match(media, /if \(keepShownFrame\(\)\) return;[^\n]*\n\s*notePdfPage\(\);[^\n]*\n\s*dropPdf\(\);/);
  assert.match(media, /whenShown\(shown, fireRendered\);[^\n]*\n\s*aimFrame\(shown\);/);
});
