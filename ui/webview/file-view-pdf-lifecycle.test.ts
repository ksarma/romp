// What the PDF pages attempt RELEASES and what it KEEPS across the Comments panel's flips and a reload, at the REAL
// openFileView (plans/file-review.md Slice 4; decision 12). The round-4 review of 2026-09-06 found three gaps, each
// held here as behavior rather than as a source pin alone:
//   - a reload with the pages up disposes the previous render's handle before the fresh one mounts (showPdfPages's
//     opening dropPdf). Only a regex pinned it; the reload test asserted the render count and never that anything was
//     disposed, so replacing that dropPdf with a bare sequence bump left every behavioral test green while each reload
//     leaked one pdf.js document and its Worker for the tab's life.
//   - a frame the close AIMED at #page=N (the reader's page, as the open parameter) is the frame at these bytes:
//     shownFrame strips the fragment before comparing. Only a regex pinned that too; without the strip a reopen over
//     such a frame rebuilt it — for the loader, or under the notice when pdf.js refuses — and the browser's viewer
//     reloaded the document, losing the place the reader had reached in it (the round-2 kept-frame rule's regression).
//   - a hung open or first-page draw held its Worker for the tab's life: render() yields no handle until it resolves,
//     so the deadline (PDF_RENDER_BACKSTOP_MS) showed the frame and retired an attempt it had nothing to dispose of.
//     Every attempt is now handed an AbortSignal (`opts.signal`), one per attempt, aborted wherever an unsettled
//     attempt is retired — the deadline, the panel closing under the loader, a reload over it, both of the viewer's
//     exits — and never after the mount, where the handle's dispose() is the release. The chunk destroys the loading
//     task and terminates its Worker on the abort; the stub below stands in for that contract (honorAbort), so a
//     render rejecting on its own abort is shown to notice nothing.
// The DOM stand-in, the chunk stub and the fetch stub are file-view-pdf-backstop.test.ts's, copied rather than shared
// because that module installs its globals and registers its tests at import; keep them in step. Synthetic fixtures
// only: the notes-api world, placeholder ids, TESTHOST.
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
// render's resolution until the test calls release(i); `hang` is an open pdf.js never answers — nothing of the chunk's
// reaches the container and the promise never settles on its own; `honorAbort` is the contract the shipped chunk keeps
// for `opts.signal`: the abort rejects the pending render with the signal's reason and leaves nothing in the container.
// Every signal handed to render() is kept, in order, so a test can read each attempt's state.
type RenderOpts = { maxBytes?: number; signal?: AbortSignal; onPage?: (p: unknown) => void };
const pdf = {
  renders: 0, disposed: 0, pages: 2, defer: false, hang: false, honorAbort: false, refuse: null as string | null,
  opts: null as null | RenderOpts, signals: [] as AbortSignal[],
  roots: [] as El[], pending: [] as Array<() => void>,
  release(i: number): void { const r = this.pending[i]; assert.ok(r, "render " + i + " is pending"); r(); },
};
const chunkStub = {
  DEFAULT_MAX_BYTES: 25 * 1024 * 1024,
  render(bytes: ArrayBuffer, container: El, opts: RenderOpts = {}) {
    pdf.renders++; pdf.opts = opts;
    if (opts.signal) pdf.signals.push(opts.signal);
    if (pdf.refuse) return Promise.reject(new Error(pdf.refuse));
    const onAbort = (cb: () => void) => { if (pdf.honorAbort) opts.signal?.addEventListener("abort", cb, { once: true }); };
    if (pdf.hang) return new Promise<never>((_, rej) => { onAbort(() => rej(opts.signal!.reason)); });
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
    return new Promise<typeof handle>((res, rej) => {
      pdf.pending.push(() => res(handle));
      onAbort(() => { root.remove(); rej(opts.signal!.reason); });
    });
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
const NOTE = ROOT + "/docs/notes.md";
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
/** The open up to its fetch: the viewer is up and the probe holds the ctx, but the bytes have NOT landed. */
async function start(p: string, t: TestContext): Promise<Open> {
  const fv = await mod();
  disk[DECK] = { bytes: "%PDF-1.4\n", type: "application/pdf", mtimeNs: MT };
  disk[NOTE] = { bytes: "# notes\n", type: "text/plain; charset=utf-8", mtimeNs: MT };
  paints = 0; seam = null;
  pdf.renders = 0; pdf.disposed = 0; pdf.opts = null; pdf.refuse = null; pdf.roots.length = 0; pdf.pending.length = 0;
  pdf.signals.length = 0;
  assert.equal(fv.openFileView(p, SID), true, "the open happened");
  t.after(() => { fv.closeFileView(); pdf.pages = 2; pdf.defer = false; pdf.hang = false; pdf.honorAbort = false; });
  const wrap = doc.getElementById("romp-fileview")!;
  assert.ok(wrap, "the viewer is up");
  const body = wrap.querySelector(".fileview-body")!;
  assert.ok(seam, "the probe action was mounted with the ctx");
  return { fv, ctx: seam!, wrap, body };
}
async function open(p: string, t: TestContext): Promise<Open> {
  const o = await start(p, t);
  await settle();
  return o;
}
const panel = () => new El("div") as unknown as HTMLElement;
const frameIn = (body: El) => body.querySelector("iframe.fileview-frame");
const noteIn = (body: El) => body.querySelector(".fileview-pdffall .fileview-err");
const colOf = (frame: El) => frame.parentNode!;                    // the frame's column (pdfBlock's .fileview-pdffall)
/** No chunk registered, and a hosting page's bundle tag to derive the chunk's URL from: the chunk is then fetched by a
 *  script tag whose load or error the test fires. The engine check wants Promise.try, which this Node lacks. */
function unregistered(t: TestContext): void {
  const saved = win.__rompPdf; win.__rompPdf = undefined;
  const tag = new El("script"); tag.src = "http://TESTHOST:29855/dist/files.js?v=1725300000"; tag.setAttribute("src", tag.src);
  doc.body.appendChild(tag);
  const P = Promise as any; const hadTry = Object.prototype.hasOwnProperty.call(P, "try"); const origTry = P.try;
  P.try = (fn: (...a: unknown[]) => unknown, ...args: unknown[]) => new Promise((r) => r(fn(...args)));
  t.after(() => {
    win.__rompPdf = saved; tag.remove(); doc.head.replaceChildren();
    if (hadTry) P.try = origTry; else delete P.try;
  });
}

const BACKSTOP_WHY = (fv: typeof import("./file-view")) =>
  "the page renderer did not finish within " + fv.PDF_RENDER_BACKSTOP_MS / 1000 + " seconds";
const classesOf = (body: El) => body.childNodes.map((n) => (n as El).className);
/** Lay the scroller and its page shells out so that page `at` (1-based) sits under the scroller's middle. */
function layOut(body: El, shells: HTMLElement[], at: number): void {
  body.rect = rect(0, 800);                                                    // the scroller: 800 tall, middle at 400
  shells.forEach((s, i) => { (s as unknown as El).rect = rect((i - (at - 1)) * 1000 - 300, (i - (at - 1)) * 1000 + 700); });
}
const sig = (i: number): AbortSignal => { const s = pdf.signals[i]; assert.ok(s, "attempt " + i + " was handed a signal"); return s; };

// ── a reload with the pages up releases the previous render ──────────────────────────────────────────

test("a reload with the pages up disposes the previous render's handle — its document and Worker released — before the fresh pages mount: one release per reload, none accumulating, and the close releases the last", async (t) => {
  pdf.pages = 3;
  const { ctx, body } = await open(DECK, t);
  ctx.aside(panel()); await settle();
  assert.equal(pdf.renders, 1); assert.equal(pdf.disposed, 0, "the live render holds its document");
  const root1 = pdf.roots[0];
  ctx.reload(); await settle();
  assert.equal(pdf.renders, 2, "the reload rendered again from the new bytes");
  assert.equal(pdf.disposed, 1, "…and disposed render 1 first: the document and Worker of the pages that left the body are released");
  assert.equal(root1.isConnected, false, "render 1's root is out of the document");
  assert.equal(body.querySelectorAll(".fileview-pdf").length, 1, "one root in the body: the reload's");
  assert.equal(pdf.roots[1].isConnected, true);
  assert.equal(ctx.pdfPages().length, 3);
  ctx.reload(); await settle();
  assert.equal(pdf.renders, 3); assert.equal(pdf.disposed, 2, "every reload releases exactly the render before it");
  assert.equal(body.querySelectorAll(".fileview-pdf").length, 1);
  ctx.aside(null);
  assert.equal(pdf.disposed, 3, "the close releases the last: nothing is left holding a document");
  assert.ok(frameIn(body), "the frame is back");
});

// ── a frame aimed at #page=N is the frame at these bytes ─────────────────────────────────────────────

test("a frame the close aimed at #page=N is the frame a reopen keeps: under the loader while the chunk works, under the notice when pdf.js refuses, and through the next close — the same element, its src untouched, never rebuilt", async (t) => {
  pdf.pages = 10;
  const { ctx, body } = await open(DECK, t);
  const bare = frameIn(body)!.src;
  ctx.aside(panel()); await settle();
  layOut(body, ctx.pdfPages(), 3);                       // the reader is on page 3
  ctx.aside(null);
  const f1 = frameIn(body)!; const col1 = colOf(f1);
  assert.equal(f1.src, bare + "#page=3", "the close aimed the frame at the reader's page");
  // (a) the reopen, the render succeeding: the aimed frame stays under the loader until page 1 is drawn
  ctx.aside(panel());
  assert.equal(frameIn(body), f1, "the SAME frame element under the loader: a frame at these bytes, whatever its fragment");
  assert.equal(f1.src, bare + "#page=3", "…its src untouched: no navigation, no reload");
  assert.ok(col1.querySelector(".fileview-load") && col1.childNodes[1] === f1, "the loader heads the frame's own column");
  assert.equal(body.querySelectorAll("iframe.fileview-frame").length, 1, "one frame in the body: none was built beside it");
  await settle();
  assert.equal(frameIn(body), null, "page 1 drawn: the pages replaced the frame");
  assert.deepEqual(ctx.pdfPages().map((s) => (s as unknown as El).scrolled), [0, 0, 1, 0, 0, 0, 0, 0, 0, 0], "…scrolled to page 3");
  // (b) the reopen, pdf.js refusing: the aimed frame is the frame under the notice
  layOut(body, ctx.pdfPages(), 5);                       // the reader has moved on to page 5
  ctx.aside(null);
  const f2 = frameIn(body)!; const col2 = colOf(f2);
  assert.equal(f2.src, bare + "#page=5");
  pdf.refuse = "Invalid PDF structure.";
  ctx.aside(panel()); await settle();
  assert.equal(pdf.renders, 3, "the chunk was asked (the open's render, the reopen's, this one)");
  assert.equal(frameIn(body), f2, "the SAME frame element under the notice: the browser's viewer keeps the place the reader had reached in it");
  assert.equal(f2.src, bare + "#page=5", "…src untouched");
  const note = noteIn(body)!;
  assert.ok(note && col2.childNodes.length === 2 && col2.childNodes[0] === note && col2.childNodes[1] === f2, "the notice above the frame, in the frame's own column");
  assert.equal(note.textContent, "Invalid PDF structure." + NOTICE_TAIL);
  assert.equal(body.querySelectorAll("iframe.fileview-frame").length, 1);
  assert.equal(ctx.mediaElement(), f2 as unknown as HTMLElement, "whole-file comments work on it");
  // (c) the next close, over the fallback's kept frame: the same element again, the notice gone
  ctx.aside(null);
  assert.equal(frameIn(body), f2, "the close keeps it too"); assert.equal(f2.src, bare + "#page=5");
  assert.equal(noteIn(body), null, "the notice goes with the panel");
  assert.equal(col2.childNodes.length, 1, "the column holds the frame alone");
  // (d) a reopen over it with the render in flight, closed under the loader: still the same element
  pdf.refuse = null; pdf.defer = true;
  ctx.aside(panel()); await settle();
  assert.equal(pdf.pending.length, 1, "the render is in flight");
  assert.equal(frameIn(body), f2, "under the loader"); assert.ok(col2.querySelector(".fileview-load"));
  ctx.aside(null);
  assert.equal(frameIn(body), f2, "the frame the reader is back in is the one they had");
  assert.equal(f2.src, bare + "#page=5");
  assert.equal(body.querySelector(".fileview-load"), null); assert.equal(body.querySelector(".fileview-pdfhost"), null);
  const released = pdf.disposed;                         // the two closes over mounted pages released a render each
  pdf.release(0); await settle();
  assert.equal(pdf.disposed, released + 1, "the retired attempt's late resolution is disposed"); assert.equal(frameIn(body), f2);
});

// ── the attempt in flight: one signal per attempt, aborted by every retire of an unsettled attempt ────

test("a hung open at the deadline: the attempt's signal is aborted — the one way to reach the Worker a render that never settles holds — with the frame and the deadline's notice as before; the next open gets a fresh signal", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  pdf.hang = true;
  const o = await start(DECK, t);
  o.ctx.aside(panel());                                  // the click lands mid-fetch: no frame to keep, the loader is the body
  await settle();
  assert.equal(pdf.renders, 1); assert.equal(pdf.signals.length, 1, "render() was handed a signal");
  assert.ok(sig(0) instanceof AbortSignal, "…an AbortSignal");
  assert.equal(sig(0).aborted, false, "live while the attempt is in flight");
  t.mock.timers.tick(o.fv.PDF_RENDER_BACKSTOP_MS - 1); await settle();
  assert.equal(sig(0).aborted, false, "short of the deadline: still waiting");
  assert.deepEqual(classesOf(o.body), ["fileview-load", "fileview-pdfhost"]);
  t.mock.timers.tick(1); await settle();
  assert.equal(sig(0).aborted, true, "at the deadline: the attempt's signal is aborted, so the chunk destroys the loading task and its Worker");
  const f = frameIn(o.body)!;
  assert.ok(f && f.src.startsWith("blob:"), "the browser's frame, as before");
  assert.equal(noteIn(o.body)!.textContent, BACKSTOP_WHY(o.fv) + NOTICE_TAIL);
  assert.deepEqual(classesOf(o.body), ["fileview-pdffall"], "the loader and the host are gone");
  assert.equal(pdf.disposed, 0, "nothing to dispose: the hung attempt never yielded a handle — the signal was the release");
  o.ctx.aside(null); o.ctx.aside(panel()); await settle();
  assert.equal(pdf.signals.length, 2, "the next open is a new attempt…");
  assert.notEqual(sig(1), sig(0), "…with a signal of its own");
  assert.equal(sig(1).aborted, false, "live"); assert.equal(sig(0).aborted, true, "the first stays aborted");
});

test("the panel closing under the loader aborts the unsettled attempt — over a kept frame, and with the loader the whole body; the deadline then adds nothing", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  pdf.hang = true;
  // over a kept frame
  let o = await open(DECK, t);
  const f0 = frameIn(o.body)!;
  o.ctx.aside(panel()); await settle();
  assert.equal(sig(0).aborted, false, "in flight under the loader, over the frame");
  o.ctx.aside(null);
  assert.equal(sig(0).aborted, true, "the close retires the attempt: its signal is aborted");
  assert.equal(frameIn(o.body), f0, "the frame the reader is back in"); assert.equal(o.body.querySelector(".fileview-load"), null);
  const before = paints;
  t.mock.timers.tick(o.fv.PDF_RENDER_BACKSTOP_MS); await settle();
  assert.equal(o.body.querySelectorAll(".fileview-err").length, 0, "the deadline was disarmed with the attempt: no notice");
  assert.equal(paints, before);
  o.fv.closeFileView();
  // the loader the whole body (the panel opened before the bytes landed)
  o = await start(DECK, t);
  o.ctx.aside(panel()); await settle();
  assert.equal(pdf.signals.length, 1); assert.equal(sig(0).aborted, false);
  o.ctx.aside(null);
  assert.equal(sig(0).aborted, true, "aborted by the close here too");
  assert.ok(frameIn(o.body), "the frame, built for the closed panel");
});

test("a reload while the render is in flight aborts that attempt and starts a fresh one with its own signal; the retired attempt's late resolution is still disposed and mounts nothing", async (t) => {
  pdf.defer = true;
  const o = await start(DECK, t);
  o.ctx.aside(panel()); await settle();                  // no frame: the loader is the body
  assert.equal(pdf.pending.length, 1); assert.equal(sig(0).aborted, false);
  o.ctx.reload(); await settle();
  assert.equal(sig(0).aborted, true, "the reload retires the attempt over the old bytes: its signal is aborted");
  assert.equal(pdf.signals.length, 2, "…and the new bytes get an attempt of their own");
  assert.equal(sig(1).aborted, false);
  assert.equal(pdf.pending.length, 2);
  pdf.release(1); await settle();
  assert.equal(o.ctx.pdfPages().length, 2, "the reload's pages mounted");
  assert.equal(pdf.disposed, 0);
  pdf.release(0); await settle();
  assert.equal(pdf.disposed, 1, "the retired attempt's resolution is disposed on arrival, as ever");
  assert.equal(o.ctx.pdfPages().length, 2); assert.equal(o.body.querySelectorAll(".fileview-pdf").length, 1, "…and mounts nothing");
});

test("both of the viewer's exits abort an unsettled attempt: closing the viewer under the loader, and another file opening over it", async (t) => {
  pdf.hang = true;
  let o = await open(DECK, t);
  o.ctx.aside(panel()); await settle();
  assert.equal(sig(0).aborted, false);
  o.fv.closeFileView();
  assert.equal(sig(0).aborted, true, "closeFileView aborted the attempt");
  assert.equal(doc.getElementById("romp-fileview"), null);
  o = await open(DECK, t);
  o.ctx.aside(panel()); await settle();
  assert.equal(sig(0).aborted, false);
  assert.equal(o.fv.openFileView(NOTE, SID), true, "another file opens over the loader");
  assert.equal(sig(0).aborted, true, "the replace-open aborted it too");
  await settle();
  assert.ok(doc.getElementById("romp-fileview"), "the new viewer is up");
});

test("never after the mount: once page 1 is drawn the handle's dispose() is the release — the close disposes it and leaves the spent signal alone; a refusal's signal is spent, and the next attempt's is new", async (t) => {
  const { ctx, body } = await open(DECK, t);
  ctx.aside(panel()); await settle();
  assert.equal(ctx.pdfPages().length, 2); assert.equal(sig(0).aborted, false, "the attempt settled: nothing aborted it");
  ctx.aside(null);
  assert.equal(pdf.disposed, 1, "the close releases the mounted render through its handle");
  assert.equal(sig(0).aborted, false, "…not through the signal: that was the unsettled attempt's, and the attempt settled");
  assert.ok(frameIn(body));
  pdf.refuse = "Invalid PDF structure.";
  ctx.aside(panel()); await settle();
  assert.equal(noteIn(body)!.textContent, "Invalid PDF structure." + NOTICE_TAIL);
  assert.equal(sig(1).aborted, true, "a refused attempt's signal is spent with it: nothing lingers to the next retire");
  ctx.aside(null); pdf.refuse = null;
  ctx.aside(panel()); await settle();
  assert.equal(pdf.signals.length, 3); assert.equal(sig(2).aborted, false, "the next attempt's signal is new and live");
  assert.equal(ctx.pdfPages().length, 2);
});

test("the chunk keeping the contract — the abort rejects the pending render — notices nothing: no second notice at the deadline, none under a closed panel", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  pdf.honorAbort = true;
  // the deadline: the hung open rejects on the abort; the notice stays the deadline's, one of them
  pdf.hang = true;
  let o = await start(DECK, t);
  o.ctx.aside(panel()); await settle();
  t.mock.timers.tick(o.fv.PDF_RENDER_BACKSTOP_MS); await settle();
  assert.equal(sig(0).aborted, true);
  assert.equal(o.body.querySelectorAll(".fileview-err").length, 1, "one notice");
  assert.equal(noteIn(o.body)!.textContent, BACKSTOP_WHY(o.fv) + NOTICE_TAIL, "…the deadline's, not the rejection's");
  assert.equal(paints, 1, "the fallback's paint alone");
  o.fv.closeFileView();
  // the panel closing under the loader: the render in flight rejects on the abort and its root goes; the frame stands alone
  pdf.hang = false; pdf.defer = true;
  o = await open(DECK, t);
  const f0 = frameIn(o.body)!;
  o.ctx.aside(panel()); await settle();
  assert.equal(pdf.pending.length, 1); assert.ok(o.body.querySelector(".fileview-pdf"), "the root is in the host");
  const before = paints;
  o.ctx.aside(null); await settle();
  assert.equal(sig(0).aborted, true);
  assert.equal(frameIn(o.body), f0); assert.equal(colOf(f0).childNodes.length, 1, "the frame alone in its column");
  assert.equal(o.body.querySelectorAll(".fileview-err").length, 0, "no notice under a closed panel");
  assert.equal(o.body.querySelector(".fileview-pdf"), null, "the chunk's root went with its host");
  assert.equal(paints, before + 1, "the close's paint, nothing from the rejection");
  assert.equal(pdf.disposed, 0, "nothing resolved, so nothing to dispose: the abort was the release");
});

// ── pinned at source ─────────────────────────────────────────────────────────────────────────────────

test("source: one AbortController per attempt, its signal into render() beside the cap; aborted by dropPdf and by the fallback; cleared at the mount, after the deadline is disarmed", () => {
  assert.match(VIEW, /^\s*let pdfAttempt: AbortController \| null = null;/m, "the attempt in flight is one controller");
  assert.match(VIEW, /const abortPdfAttempt = \(\) => \{ if \(pdfAttempt\) \{ pdfAttempt\.abort\(\); pdfAttempt = null; \} \};/);
  assert.match(VIEW, /const dropPdf = \(\) => \{ pdfSeq\+\+; disarmBackstop\(\); abortPdfAttempt\(\); if \(pdfHandle\) \{ pdfHandle\.dispose\(\); pdfHandle = null; \} \};/,
    "retiring the attempt aborts it: the panel closing under the loader, a reload, both of the viewer's exits, the deadline");
  const show = VIEW.split("const showPdfPages = () => {")[1].split("closeHooks.push(dropPdf);")[0];
  const made = show.indexOf("const attempt = new AbortController();\n    pdfAttempt = attempt;");
  assert.ok(made > 0, "the attempt's controller is made in showPdfPages");
  assert.ok(made > show.indexOf("}, PDF_RENDER_BACKSTOP_MS);"), "after the deadline is armed");
  assert.ok(made < show.indexOf("Promise.all([pdfChunkLoad(), blob.arrayBuffer()])"), "before the wait it can end");
  const call = show.split("return pdf.render(bytes, host, {")[1].split("}).then((h) => {")[0];
  assert.match(call, /^\s*maxBytes: PDF_MAX_BYTES,\n\s*signal: attempt\.signal,/m, "the signal rides into render() beside the cap");
  assert.match(show, /const fallback = \(why: string\) => \{\n\s*if \(my !== pdfSeq \|\| !wrap\.isConnected\) return;[^\n]*\n\s*disarmBackstop\(\);[^\n]*\n\s*abortPdfAttempt\(\);/,
    "a failed attempt's signal is spent with it — and the deadline's fallback is where a hung attempt's Worker is reached");
  assert.match(show, /\}\)\.then\(\(h\) => \{\n\s*if \(my !== pdfSeq \|\| !wrap\.isConnected\) \{ h\.dispose\(\); return; \}[^\n]*\n\s*disarmBackstop\(\);[^\n]*\n\s*pdfAttempt = null;/,
    "the render settling clears the controller without aborting it: the handle owns the release from the mount on");
  assert.equal((VIEW.match(/new AbortController\(\)/g) || []).length, 1, "one controller, the attempt's: a second one needs the event it is aborted on named");
});
