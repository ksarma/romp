// The browser's frame kept in place across the Comments panel's flips, at the REAL openFileView (plans/file-review.md
// Slice 4; decision 12: the frame is the fallback for a PDF the pages cannot show). The review of 2026-09-06 found the
// frame REBUILT on every open of the panel over such a PDF — over the cap, refused by pdf.js, page-less, a chunk that
// would not load — which reloads the document at page 1 and loses the place the reader had reached in the browser's
// viewer (the frame never reports it), where the round-1 fix had kept the frame only when the panel CLOSED. These tests
// pin the frame as the same element through the open, the loader and the fallback, and the attempt ending when the
// panel closes under the loader (fallback's own stale guard, which no test reached before). Also here, from the same
// review: the viewer's exits disposing the chunk's handle, the reader's page read at the MIDDLE of the scroller, and the
// panel opening before the bytes land. The DOM stand-in, the chunk stub and the fetch stub are file-view-pdf.test.ts's,
// copied rather than shared because that module installs its globals and registers its tests at import; keep them in
// step. Synthetic fixtures only: the notes-api world, placeholder ids, TESTHOST.
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
  assert.equal(fv.openFileView(p, SID), true, "the open happened");
  t.after(() => { fv.closeFileView(); pdf.pages = 2; pdf.defer = false; });
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

// ── the frame kept through the panel's OPEN (the review, 2026-09-06) ─────────────────────────────────

test("over the cap: the Comments panel opens over the SAME frame, kept in place under the notice, and every later open keeps it; the notice comes and goes around it", async (t) => {
  disk[BIG] = { bytes: new Uint8Array(26 * 1024 * 1024), type: "application/pdf", mtimeNs: MT };
  t.after(() => { delete disk[BIG]; });
  const { ctx, body } = await open(BIG, t);
  const f0 = frameIn(body)!;
  const col = colOf(f0);
  assert.ok(col.classList.contains("fileview-pdffall") && col.parentNode === body, "the frame comes in its column from the first paint");
  assert.equal(body.childNodes.length, 1, "…and the column is the body");
  const bare = f0.src;
  ctx.aside(panel()); await settle();
  assert.equal(pdf.renders, 0, "over the cap: refused before the chunk");
  assert.equal(frameIn(body), f0, "the SAME frame element: the browser's viewer keeps the place the reader had reached");
  assert.equal(f0.src, bare, "…and its src untouched: no navigation");
  const note = noteIn(body)!;
  assert.equal(note.textContent, "this PDF is 26.0 MB, over the 25.0 MB cap for rendering pages in the viewer" + NOTICE_TAIL);
  assert.ok(col.childNodes.length === 2 && col.childNodes[0] === note && col.childNodes[1] === f0, "the notice above the frame, in the frame's own column");
  assert.equal(body.childNodes.length, 1);
  assert.equal(ctx.mediaElement(), f0 as unknown as HTMLElement, "whole-file comments work on it");
  assert.deepEqual(ctx.pdfPages(), []);
  assert.equal(paints, 2, "the panel hears the body change");
  ctx.aside(null);
  assert.equal(frameIn(body), f0, "closing keeps it too (the round-1 fix)");
  assert.equal(noteIn(body), null, "the notice goes with the panel");
  assert.equal(paints, 3);
  ctx.aside(panel()); await settle();
  assert.equal(frameIn(body), f0, "the second open: still the same frame");
  assert.equal(body.querySelectorAll(".fileview-err").length, 1, "one notice");
  assert.equal(paints, 4);
});

test("pdf.js refusing the document: the frame stays under the loader while the chunk works and under the notice when it refuses; a second open asks the chunk again, over the same frame", async (t) => {
  const { ctx, body } = await open(DECK, t);
  const f0 = frameIn(body)!; const col = colOf(f0);
  pdf.refuse = "Invalid PDF structure.";                 // pdf.js's own words for a file it will not open
  ctx.aside(panel());
  assert.equal(frameIn(body), f0, "the frame is not dropped for the loader");
  const wait = col.querySelector(".fileview-load")!;
  assert.ok(wait && col.childNodes[0] === wait && col.childNodes[1] === f0, "the loader heads the frame's column");
  const host = body.querySelector(".fileview-pdfhost")!;
  assert.ok(host && host.parentNode === body && body.childNodes[0] === col && body.childNodes[1] === host,
    "the chunk's host follows the column in the body: the frame is never moved (a moved iframe reloads like a rebuilt one)");
  assert.equal(paints, 1, "nothing painted for the loader: the frame is what it was");
  await settle();
  assert.equal(pdf.renders, 1, "the chunk was asked");
  assert.equal(frameIn(body), f0, "the SAME frame under the notice");
  assert.equal(noteIn(body)!.textContent, "Invalid PDF structure." + NOTICE_TAIL);
  assert.equal(body.querySelector(".fileview-load"), null, "the loader is gone");
  assert.equal(body.querySelector(".fileview-pdfhost"), null, "…and the host");
  assert.equal(body.childNodes.length, 1);
  assert.equal(col.childNodes.length, 2, "the notice and the frame, nothing else");
  assert.equal(paints, 2, "the panel hears the fallback");
  ctx.aside(null);
  assert.equal(noteIn(body), null); assert.equal(frameIn(body), f0);
  ctx.aside(panel()); await settle();
  assert.equal(pdf.renders, 2, "asked again: the document, not the chunk, was the problem");
  assert.equal(frameIn(body), f0);
  assert.equal(body.querySelectorAll(".fileview-err").length, 1);
});

test("a page-less document: the frame it falls back to is the one that was showing", async (t) => {
  pdf.pages = 0;
  const { ctx, body } = await open(DECK, t);
  const f0 = frameIn(body)!;
  ctx.aside(panel()); await settle();
  assert.equal(pdf.renders, 1); assert.equal(pdf.disposed, 1, "the document released");
  assert.equal(frameIn(body), f0, "the same frame");
  assert.equal(noteIn(body)!.textContent, "this PDF has no pages" + NOTICE_TAIL);
  assert.equal(body.querySelector(".fileview-pdf"), null, "the empty root is gone");
  assert.equal(body.querySelector(".fileview-pdfhost"), null); assert.equal(body.querySelector(".fileview-load"), null);
  assert.equal(ctx.mediaElement(), f0 as unknown as HTMLElement);
});

test("the chunk failing to load: the frame stays; the next open fetches the chunk again (the latch is cleared), over the same frame", async (t) => {
  unregistered(t);
  const { ctx, body } = await open(DECK, t);
  const f0 = frameIn(body)!; const col = colOf(f0);
  ctx.aside(panel()); await settle();
  let scripts = doc.head.querySelectorAll("script");
  assert.equal(scripts.length, 1, "the chunk's script tag is out");
  assert.equal(frameIn(body), f0, "the frame stays while the chunk loads");
  assert.ok(col.querySelector(".fileview-load"), "under the loader");
  scripts[0].onerror!(); await settle();
  assert.equal(frameIn(body), f0, "the same frame under the notice");
  assert.equal(noteIn(body)!.textContent, "the PDF renderer failed to load" + NOTICE_TAIL);
  assert.equal(body.querySelector(".fileview-load"), null); assert.equal(body.querySelector(".fileview-pdfhost"), null);
  ctx.aside(null);
  assert.equal(noteIn(body), null); assert.equal(frameIn(body), f0);
  ctx.aside(panel()); await settle();
  scripts = doc.head.querySelectorAll("script");
  assert.equal(scripts.length, 2, "a second script tag: the failed load is retried");
  assert.equal(frameIn(body), f0, "…over the same frame");
  assert.ok(col.querySelector(".fileview-load"));
  win.__rompPdf = chunkStub; scripts[1].onload!(); await settle();
  assert.equal(pdf.renders, 1, "the retry rendered");
  assert.equal(frameIn(body), null, "the pages replaced the frame");
  assert.equal(ctx.pdfPages().length, 2);
});

test("the chunk rendering: the frame stays under the loader until page 1 is drawn, then the pages are the body and the frame is gone with its column", async (t) => {
  const { ctx, body } = await open(DECK, t);
  const f0 = frameIn(body)!; const col = colOf(f0);
  ctx.aside(panel());
  assert.equal(frameIn(body), f0, "still showing under the loader");
  assert.ok(col.querySelector(".fileview-load"));
  assert.equal(ctx.mediaElement(), f0 as unknown as HTMLElement, "the frame is the media element until the pages show");
  await settle();
  assert.equal(pdf.renders, 1);
  assert.equal(frameIn(body), null, "the frame went with page 1");
  assert.equal(body.querySelector(".fileview-pdffall"), null, "…and its column");
  assert.equal(body.querySelector(".fileview-load"), null);
  const host = body.querySelector(".fileview-pdfhost")!;
  assert.ok(host && body.childNodes.length === 1 && body.childNodes[0] === host, "the host is the body, where it was laid out");
  assert.equal(ctx.pdfPages().length, 2);
  assert.equal(ctx.mediaElement(), body.querySelector(".fileview-pdf") as unknown as HTMLElement);
  assert.equal(paints, 2, "the open's paint, then page 1's");
});

// ── the panel closing under the loader: the attempt ends, and its late failure notices nothing ─────────

test("the chunk failing to load AFTER the panel closed: nothing changes under the closed panel — the frame the reader is back in stays, no notice", async (t) => {
  unregistered(t);
  const { ctx, body } = await open(DECK, t);
  const f0 = frameIn(body)!; const col = colOf(f0);
  ctx.aside(panel());
  const scripts = doc.head.querySelectorAll("script");
  assert.equal(scripts.length, 1, "the chunk is fetching");
  ctx.aside(null);                                       // the person closes the panel: back to the frame
  assert.equal(frameIn(body), f0, "the frame was never rebuilt");
  assert.equal(body.querySelector(".fileview-load"), null, "the attempt's loader went with the panel");
  assert.equal(body.querySelector(".fileview-pdfhost"), null, "…and its host");
  const before = paints;
  scripts[0].onerror!(); await settle();                 // the fetch then fails
  assert.equal(frameIn(body), f0, "the same frame element");
  assert.equal(noteIn(body), null, "no notice about rendering pages under a closed panel");
  assert.equal(body.querySelectorAll(".fileview-err").length, 0);
  assert.equal(body.childNodes.length, 1); assert.equal(col.childNodes.length, 1, "the column holds the frame alone");
  assert.equal(paints, before, "the panel heard nothing: nothing changed");
});

test("the panel closing while a render is in flight keeps the frame and ends the attempt: the late resolution is disposed and mounts nothing", async (t) => {
  pdf.defer = true;
  const { ctx, body } = await open(DECK, t);
  const f0 = frameIn(body)!; const col = colOf(f0);
  ctx.aside(panel()); await settle();
  assert.equal(pdf.pending.length, 1, "the render is in flight");
  assert.ok(body.querySelector(".fileview-pdf"), "its root is in the host already");
  ctx.aside(null);
  assert.equal(frameIn(body), f0, "the frame the reader had is the one they are back in");
  assert.equal(body.querySelector(".fileview-load"), null); assert.equal(body.querySelector(".fileview-pdfhost"), null);
  assert.equal(body.querySelector(".fileview-pdf"), null, "the root went with the host");
  assert.deepEqual(ctx.pdfPages(), []);
  pdf.release(0); await settle();
  assert.equal(pdf.disposed, 1, "the stale resolution is disposed on arrival");
  assert.equal(frameIn(body), f0); assert.equal(col.childNodes.length, 1); assert.equal(body.childNodes.length, 1);
  assert.equal(noteIn(body), null);
});

// ── the viewer's exits release the handle ────────────────────────────────────────────────────────────

test("the viewer closing with the pages up disposes the chunk's handle — the document and its worker released; a replace-open does the same", async (t) => {
  let o = await open(DECK, t);
  o.ctx.aside(panel()); await settle();
  assert.equal(pdf.renders, 1); assert.equal(pdf.disposed, 0);
  o.fv.closeFileView();
  assert.equal(pdf.disposed, 1, "closeFileView released the handle");
  assert.equal(doc.getElementById("romp-fileview"), null);
  o = await open(DECK, t);
  o.ctx.aside(panel()); await settle();
  assert.equal(pdf.disposed, 0);
  assert.equal(o.fv.openFileView(NOTE, SID), true, "another file opens over the pages");
  assert.equal(pdf.disposed, 1, "the replace-open released the handle too");
  await settle();
  assert.ok(doc.getElementById("romp-fileview"), "the new viewer is up");
});

// ── the reader's page: the page under the MIDDLE of the scroller ─────────────────────────────────────

test("the reader's page is the one under the middle of the scroller, not the one whose last lines show at the top; every page above the middle is page 1", async (t) => {
  pdf.pages = 10;
  const { ctx, body } = await open(DECK, t);
  const bare = frameIn(body)!.src;
  ctx.aside(panel()); await settle();
  let shells = ctx.pdfPages() as unknown as El[];
  assert.equal(shells.length, 10);
  // page 6's last 100px at the top of an 800px scroller, page 7 filling the rest: the reader is on page 7
  body.rect = rect(0, 800);
  shells.forEach((s, i) => { s.rect = i < 5 ? rect(-9000, -8000) : i === 5 ? rect(-900, 100) : i === 6 ? rect(100, 1100) : rect(2000, 3000); });
  ctx.aside(null);
  assert.equal(frameIn(body)!.src, bare + "#page=7", "page 7, under the middle — not page 6, whose tail shows at the top");
  ctx.aside(panel()); await settle();
  shells = ctx.pdfPages() as unknown as El[];
  assert.deepEqual(shells.map((s) => s.scrolled), [0, 0, 0, 0, 0, 0, 1, 0, 0, 0], "the reopened pages scroll to page 7");
  // ten 30px pages, the last bottom at 300: nothing reaches the middle, so page 1 and no fragment
  shells.forEach((s, i) => { s.rect = rect(i * 30, i * 30 + 30); });
  ctx.aside(null);
  assert.equal(frameIn(body)!.src, bare, "page 1 adds nothing");
});

// ── the panel opening before the bytes land ──────────────────────────────────────────────────────────

test("the Comments panel opening before the PDF's bytes land: the pages once they do (the fetch continuation reads the flag); closed again before they land: the frame", async (t) => {
  let o = await start(DECK, t);
  assert.ok(o.body.querySelector(".fileview-load"), "the open's loader: the bytes are still out");
  o.ctx.aside(panel());                                  // the click lands mid-fetch
  assert.equal(pdf.renders, 0); assert.equal(o.body.querySelector(".fileview-pdfhost"), null, "nothing to render yet");
  await settle();
  assert.equal(pdf.renders, 1, "the pages were rendered once the bytes landed");
  assert.equal(o.ctx.pdfPages().length, 2);
  assert.equal(frameIn(o.body), null, "no frame under an open panel");
  assert.equal(o.ctx.mediaElement(), o.body.querySelector(".fileview-pdf") as unknown as HTMLElement);
  o.fv.closeFileView();
  o = await start(DECK, t);
  o.ctx.aside(panel()); o.ctx.aside(null);               // opened and closed again, all before the bytes
  await settle();
  assert.equal(pdf.renders, 0, "the chunk was never asked");
  assert.ok(frameIn(o.body), "the frame, as for a closed panel");
});

// ── pinned at source ─────────────────────────────────────────────────────────────────────────────────

test("source: fallback's own stale guard; the kept frame through the loader step and the fallback; the close ending the attempt; the column from pdfBlock; the middle rule", () => {
  const show = VIEW.split("const showPdfPages = () => {")[1].split("closeHooks.push(dropPdf);")[0];
  assert.match(show, /const fallback = \(why: string\) => \{\n\s*if \(my !== pdfSeq \|\| !wrap\.isConnected\) return;/,
    "a failure landing after the body moved on (the panel closed under the loader) notices nothing");
  assert.match(show, /const kept = shownFrame\(\);\n\s*const col = kept \? kept\.parentElement : null;/);
  assert.match(show, /if \(col\) \{ col\.prepend\(wait\); body\.appendChild\(host\); \}\n\s*else body\.replaceChildren\(wait, host\);/,
    "the loader heads the kept frame's column and the host follows it: the frame is never moved");
  assert.match(show, /if \(col\) \{[^\n]*\n\s*col\.querySelector\("\.fileview-load"\)\?\.remove\(\);\n\s*body\.querySelector\("\.fileview-pdfhost"\)\?\.remove\(\);\n\s*col\.prepend\(note\);/,
    "the fallback over a kept frame: the attempt's loader and host go, the notice goes above the frame");
  assert.match(show, /const fall = pdfBlock\(url, path\);[^\n]*\n\s*fall\.prepend\(note\);\n\s*aimFrame\(fall\);/, "no frame to keep: a fresh column, the notice above its frame");
  assert.match(show, /wait\.remove\(\);[^\n]*\n\s*col\?\.remove\(\);/, "page 1 drawn: the loader and the kept frame's column go");
  assert.ok(show.indexOf("pdfHandle = h;") < show.indexOf("col?.remove();"), "…after the mount");
  const keep = VIEW.split("const keepShownFrame = (): boolean => {")[1].split("};")[0];
  assert.match(keep, /const kept = shownFrame\(\);\n\s*if \(!kept\) return false;\n\s*dropPdf\(\);/, "the close over a kept frame retires the attempt's sequence first");
  assert.match(keep, /col\.querySelector\("\.fileview-err"\)\?\.remove\(\);/);
  assert.match(keep, /col\.querySelector\("\.fileview-load"\)\?\.remove\(\);/);
  assert.match(keep, /body\.querySelector\("\.fileview-pdfhost"\)\?\.remove\(\);/);
  const shown = VIEW.split("const shownFrame = (): HTMLIFrameElement | null => {")[1].split("};")[0];
  assert.match(shown, /f\.src\.replace\(\/#\.\*\$\/, ""\) === objUrl \? f : null/, "the frame counts only at THESE bytes: a reload's is rebuilt");
  const pdfFn = VIEW.split("function pdfBlock")[1].split("/** Bind the pane's WS poster")[0];
  assert.match(pdfFn, /const col = el\("div", "fileview-pdffall"\);\n\s*const frame = el\("iframe", "fileview-frame"\) as HTMLIFrameElement;/);
  assert.match(pdfFn, /col\.appendChild\(frame\);\n\s*return col;/, "the frame comes in its column from the first paint");
  const aim = VIEW.split("const aimFrame = (shown: Element | null) => {")[1].split("};")[0];
  assert.match(aim, /shown\.matches\("iframe\.fileview-frame"\) \? shown : shown\.querySelector\("iframe\.fileview-frame"\)/, "aimFrame takes the column or the frame");
  const note = VIEW.split("const notePdfPage = () => {")[1].split("};")[0];
  assert.match(note, /const mid = r\.top \+ r\.height \/ 2;/);
  assert.match(note, /getBoundingClientRect\(\)\.bottom >= mid\)/, "the page whose bottom clears the MIDDLE of the scroller, not its top");
});
