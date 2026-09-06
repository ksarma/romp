// The pages attempt's backstop (plans/file-review.md Slice 4; ui/CLAUDE.md, loading states: the romp loader fades on the
// event, with a backstop timeout so it can never trap the user). The round-3 review of 2026-09-06 found showPdfPages with
// no such timeout: it put up the loader and waited on the chunk load, the bytes and render() with nothing else able to end
// the wait — and with no frame kept (the Comments panel opened before the bytes landed, or the pages were up and the file
// reloaded) the loader was the whole body, so a render that never settles (pdf.js puts no deadline on opening a document;
// a worker stuck in a pathological content stream, a chunk fetch that stalls without erroring) left a spinning loader
// with nothing saying why and nothing on screen pointing at a way out. These tests drive the clock with node:test's mock
// timers and pin: the deadline (PDF_RENDER_BACKSTOP_MS) ends the attempt in the fallback's own shape — the frame with a
// line saying why — and over a kept frame in place; a resolution landing after it is disposed and mounts nothing; every
// event that ends the attempt disarms the deadline, so it fires only for one that never settled; a stalled chunk fetch
// is fetched afresh by the next open. The DOM stand-in, the chunk stub and the fetch stub are
// file-view-pdf-frame.test.ts's, copied rather than shared because that module installs its globals and registers its
// tests at import; keep them in step. Synthetic fixtures only: the notes-api world, placeholder ids, TESTHOST.
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

const BACKSTOP_WHY = (fv: typeof import("./file-view")) =>
  "the page renderer did not finish within " + fv.PDF_RENDER_BACKSTOP_MS / 1000 + " seconds";
const classesOf = (body: El) => body.childNodes.map((n) => (n as El).className);

// ── the deadline ends an attempt that never settles ─────────────────────────────────────────────────

test("no frame kept (the panel opened before the bytes landed) and a render that never settles: the loader is the whole body up to the deadline, then the frame with a line saying why; the late resolution is disposed and mounts nothing; closing keeps that frame; the next open asks again", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  pdf.defer = true;
  const o = await start(DECK, t);
  o.ctx.aside(panel());                                  // the click lands mid-fetch
  await settle();
  assert.equal(pdf.pending.length, 1, "the render is in flight");
  assert.deepEqual(classesOf(o.body), ["fileview-load", "fileview-pdfhost"], "the loader and the chunk's host are the whole body: no frame under an open panel");
  assert.equal(paints, 0, "nothing has painted");
  t.mock.timers.tick(o.fv.PDF_RENDER_BACKSTOP_MS - 1); await settle();
  assert.deepEqual(classesOf(o.body), ["fileview-load", "fileview-pdfhost"], "short of the deadline: still waiting, nothing else");
  assert.equal(paints, 0);
  t.mock.timers.tick(1); await settle();
  const f = frameIn(o.body)!;
  assert.ok(f, "at the deadline: the browser's frame");
  assert.ok(f.src.startsWith("blob:") && !f.src.includes("#"), "aimed at the held bytes, page 1");
  const note = noteIn(o.body)!;
  assert.equal(note.textContent, BACKSTOP_WHY(o.fv) + NOTICE_TAIL);
  const col = colOf(f);
  assert.ok(col.childNodes.length === 2 && col.childNodes[0] === note && col.childNodes[1] === f, "the notice above the frame, in its column");
  assert.deepEqual(classesOf(o.body), ["fileview-pdffall"], "the column is the body: the loader and the host are gone");
  assert.equal(o.ctx.mediaElement(), f as unknown as HTMLElement, "whole-file comments work on it");
  assert.deepEqual(o.ctx.pdfPages(), []);
  assert.equal(paints, 1, "the panel hears the fallback");
  pdf.release(0); await settle();
  assert.equal(pdf.disposed, 1, "the resolution landing after the deadline is disposed on arrival: the document and its worker released");
  assert.equal(frameIn(o.body), f); assert.equal(col.childNodes.length, 2); assert.deepEqual(classesOf(o.body), ["fileview-pdffall"]);
  assert.equal(paints, 1, "…and mounts nothing");
  o.ctx.aside(null);
  assert.equal(frameIn(o.body), f, "closing the panel keeps the frame the deadline built");
  assert.equal(noteIn(o.body), null, "the notice goes with the panel");
  o.ctx.aside(panel()); await settle();
  assert.equal(pdf.pending.length, 2, "the next open asks the chunk again");
  assert.equal(frameIn(o.body), f, "over the same frame"); assert.ok(col.querySelector(".fileview-load"), "under the loader");
  pdf.release(1); await settle();
  assert.equal(frameIn(o.body), null, "the pages replaced the frame"); assert.equal(o.ctx.pdfPages().length, 2);
});

test("over a kept frame: the deadline's notice goes above the SAME frame in place, the loader and the host go, and the late resolution changes nothing", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  pdf.defer = true;
  const { ctx, body, fv } = await open(DECK, t);
  const f0 = frameIn(body)!; const col = colOf(f0); const bare = f0.src;
  ctx.aside(panel()); await settle();
  assert.equal(pdf.pending.length, 1);
  assert.ok(col.querySelector(".fileview-load") && body.querySelector(".fileview-pdfhost"), "the loader heads the frame's column, the host follows it");
  t.mock.timers.tick(fv.PDF_RENDER_BACKSTOP_MS); await settle();
  assert.equal(frameIn(body), f0, "the same frame element"); assert.equal(f0.src, bare, "its src untouched: no navigation");
  const note = noteIn(body)!;
  assert.equal(note.textContent, BACKSTOP_WHY(fv) + NOTICE_TAIL);
  assert.ok(col.childNodes.length === 2 && col.childNodes[0] === note && col.childNodes[1] === f0, "the notice above the frame, in the frame's own column");
  assert.equal(body.querySelector(".fileview-load"), null); assert.equal(body.querySelector(".fileview-pdfhost"), null);
  assert.equal(body.childNodes.length, 1);
  assert.equal(paints, 2, "the open's paint, then the fallback's");
  pdf.release(0); await settle();
  assert.equal(pdf.disposed, 1, "disposed on arrival");
  assert.equal(frameIn(body), f0); assert.equal(col.childNodes.length, 2); assert.equal(body.childNodes.length, 1); assert.equal(paints, 2);
});

test("a chunk fetch that stalls: the deadline gives up over the kept frame and clears the latch, so the next open fetches the chunk again — a second script tag — whose load renders the pages; the first tag's late load changes nothing", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  unregistered(t);
  const { ctx, body, fv } = await open(DECK, t);
  const f0 = frameIn(body)!;
  ctx.aside(panel()); await settle();
  let scripts = doc.head.querySelectorAll("script");
  assert.equal(scripts.length, 1, "the chunk's script tag is out"); assert.ok(colOf(f0).querySelector(".fileview-load"), "under the loader");
  t.mock.timers.tick(fv.PDF_RENDER_BACKSTOP_MS); await settle();
  assert.equal(frameIn(body), f0, "the same frame under the notice");
  assert.equal(noteIn(body)!.textContent, BACKSTOP_WHY(fv) + NOTICE_TAIL);
  assert.equal(body.querySelector(".fileview-load"), null); assert.equal(body.querySelector(".fileview-pdfhost"), null);
  assert.equal(pdf.renders, 0, "nothing rendered: the chunk never arrived");
  ctx.aside(null); assert.equal(noteIn(body), null);
  ctx.aside(panel()); await settle();
  scripts = doc.head.querySelectorAll("script");
  assert.equal(scripts.length, 2, "a second script tag: the stalled fetch is not waited on a second time");
  assert.equal(frameIn(body), f0, "…over the same frame");
  win.__rompPdf = chunkStub; scripts[1].onload!(); await settle();
  assert.equal(pdf.renders, 1, "the retry rendered"); assert.equal(frameIn(body), null, "the pages replaced the frame"); assert.equal(ctx.pdfPages().length, 2);
  scripts[0].onload!(); await settle();                  // the stalled tag finally loads: it resolves a promise nothing waits on
  assert.equal(pdf.renders, 1); assert.equal(ctx.pdfPages().length, 2); assert.equal(body.querySelectorAll(".fileview-err").length, 0);
});

// ── every event that ends the attempt disarms the deadline ───────────────────────────────────────────

test("disarmed by every event that ends the attempt — page 1 drawn, the panel closed under the loader, the viewer closed under it, a refusal: nothing more happens when the clock passes the deadline", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  // page 1 drawn in time
  let o = await open(DECK, t);
  o.ctx.aside(panel()); await settle();
  assert.equal(o.ctx.pdfPages().length, 2); assert.equal(paints, 2);
  t.mock.timers.tick(o.fv.PDF_RENDER_BACKSTOP_MS); await settle();
  assert.equal(o.ctx.pdfPages().length, 2, "the pages stay"); assert.equal(o.body.querySelectorAll(".fileview-err").length, 0, "no notice");
  assert.equal(paints, 2, "the panel heard nothing");
  o.fv.closeFileView();
  // the panel closed under the loader: the frame the reader is back in, and the clock adds nothing
  pdf.defer = true;
  o = await open(DECK, t);
  const f0 = frameIn(o.body)!;
  o.ctx.aside(panel()); await settle();
  assert.equal(pdf.pending.length, 1);
  o.ctx.aside(null);
  const before = paints;
  t.mock.timers.tick(o.fv.PDF_RENDER_BACKSTOP_MS); await settle();
  assert.equal(frameIn(o.body), f0); assert.equal(o.body.querySelectorAll(".fileview-err").length, 0, "no notice under a closed panel");
  assert.equal(colOf(f0).childNodes.length, 1, "the column holds the frame alone"); assert.equal(paints, before);
  pdf.release(0); await settle();
  assert.equal(pdf.disposed, 1, "the retired attempt's resolution is disposed (the frame test's rule, unchanged by the deadline)");
  // the viewer closed under the loader
  o = await open(DECK, t);
  o.ctx.aside(panel()); await settle();
  assert.equal(pdf.pending.length, 1);
  o.fv.closeFileView();
  assert.equal(doc.getElementById("romp-fileview"), null);
  t.mock.timers.tick(o.fv.PDF_RENDER_BACKSTOP_MS); await settle();
  assert.equal(doc.getElementById("romp-fileview"), null, "nothing came back"); assert.equal(doc.body.querySelectorAll(".fileview-err").length, 0);
  pdf.release(0); await settle();
  assert.equal(pdf.disposed, 1);
  pdf.defer = false; pdf.pending.length = 0;
  // a refusal: one notice, the refusal's
  o = await open(DECK, t);
  pdf.refuse = "Invalid PDF structure.";
  o.ctx.aside(panel()); await settle();
  assert.equal(o.body.querySelectorAll(".fileview-err").length, 1);
  assert.equal(noteIn(o.body)!.textContent, "Invalid PDF structure." + NOTICE_TAIL);
  const p2 = paints;
  t.mock.timers.tick(o.fv.PDF_RENDER_BACKSTOP_MS); await settle();
  assert.equal(o.body.querySelectorAll(".fileview-err").length, 1, "one notice — the deadline adds nothing to a refusal");
  assert.equal(noteIn(o.body)!.textContent, "Invalid PDF structure." + NOTICE_TAIL);
  assert.equal(paints, p2);
});

test("over the cap: refused before any wait, so there is no deadline to reach — one notice, the cap's, after the clock passes it", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  disk[BIG] = { bytes: new Uint8Array(26 * 1024 * 1024), type: "application/pdf", mtimeNs: MT };
  t.after(() => { delete disk[BIG]; });
  const { ctx, body, fv } = await open(BIG, t);
  const f0 = frameIn(body)!;
  ctx.aside(panel()); await settle();
  assert.equal(pdf.renders, 0);
  const cap = noteIn(body)!.textContent;
  assert.ok(cap.startsWith("this PDF is 26.0 MB, over the 25.0 MB cap"), "the cap's notice");
  const p = paints;
  t.mock.timers.tick(fv.PDF_RENDER_BACKSTOP_MS); await settle();
  assert.equal(body.querySelectorAll(".fileview-err").length, 1); assert.equal(noteIn(body)!.textContent, cap);
  assert.equal(frameIn(body), f0); assert.equal(paints, p);
});

// ── pinned at source ─────────────────────────────────────────────────────────────────────────────────

test("source: the constant, exported and the one figure the notice names; armed after the cap refusal and the loader, before the wait it bounds; the handler's order (guard, latch, fallback, retire); disarmed after each stale guard and by dropPdf", () => {
  const m = /^export const PDF_RENDER_BACKSTOP_MS = ([\d_]+);$/m.exec(VIEW);
  assert.ok(m, "the deadline is one exported constant");
  const ms = Number(m![1].replace(/_/g, ""));
  assert.ok(ms >= 30_000, "long: the pane loader's 8 s failsafe fired in normal cold starts and its 30 s never has (kernel.py _pane_spin); a 25 MB document on a phone is a real wait");
  assert.ok(ms % 1000 === 0, "a whole number of seconds, since the notice states it in seconds");
  const show = VIEW.split("const showPdfPages = () => {")[1].split("closeHooks.push(dropPdf);")[0];
  const armAt = show.indexOf("pdfBackstop = setTimeout(() => {");
  assert.ok(armAt > 0, "the attempt arms the deadline");
  assert.ok(armAt > show.indexOf("if (blob.size > PDF_MAX_BYTES) { fallback("), "after the cap refusal: a refused PDF waits on nothing");
  assert.ok(armAt > show.indexOf("else body.replaceChildren(wait, host);"), "after the loader is up");
  assert.ok(armAt < show.indexOf("Promise.all([pdfChunkLoad(), blob.arrayBuffer()])"), "before the wait it bounds");
  const handler = show.slice(armAt).split("}, PDF_RENDER_BACKSTOP_MS);")[0];
  const guard = handler.indexOf("if (my !== pdfSeq || !wrap.isConnected) return;");
  const latch = handler.indexOf("pdfChunk = null;");
  const fall = handler.indexOf('fallback("the page renderer did not finish within " + PDF_RENDER_BACKSTOP_MS / 1000 + " seconds");');
  const retire = handler.indexOf("dropPdf();");
  assert.ok(guard > 0 && latch > guard && fall > latch && retire > fall,
    "the stale guard first (the shape the other continuations wear), then the latch cleared, then the fallback while the attempt is still current (its own guard), then the attempt retired so a late resolution is disposed");
  assert.match(show, /const fallback = \(why: string\) => \{\n\s*if \(my !== pdfSeq \|\| !wrap\.isConnected\) return;[^\n]*\n\s*disarmBackstop\(\);/,
    "a refusal disarms it, after fallback's own stale guard");
  assert.match(show, /\}\)\.then\(\(h\) => \{\n\s*if \(my !== pdfSeq \|\| !wrap\.isConnected\) \{ h\.dispose\(\); return; \}[^\n]*\n\s*disarmBackstop\(\);/,
    "the render settling disarms it, after its stale guard and before the page-less check");
  assert.match(VIEW, /const disarmBackstop = \(\) => \{ clearTimeout\(pdfBackstop\); pdfBackstop = undefined; \};/);
  assert.match(VIEW, /const dropPdf = \(\) => \{ pdfSeq\+\+; disarmBackstop\(\); if \(pdfHandle\) \{ pdfHandle\.dispose\(\); pdfHandle = null; \} \};/,
    "retiring the attempt disarms it: the panel closing, a reload, both of the viewer's exits");
  assert.equal((VIEW.match(/setTimeout\(/g) || []).length, 3, "the viewer's timers: the two label restores and this one deadline — a new timer here needs an event it approximates named, or this rule's failsafe carve-out");
});
