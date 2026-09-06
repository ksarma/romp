// A later PDF page pdf.js cannot draw, at the REAL openFileView (plans/file-review.md, Slice 4): the chunk's fail()
// removes that page's canvas, shows the failure in its shell and reports it ONCE through render()'s onPageError — and
// fires no onPage for it (pdf-chunk.test.ts pins that). The Comments panel derives its overlays and the card's
// 'not rendered' tag only in a paint pass, which runs on the seam's onRendered (file-comments.ts) — so the viewer
// must fire onRendered for a failed page as it does for a drawn one, or the panel keeps its overlay armed on a canvas
// that is gone and its card's region link without the tag until some unrelated repaint (round 3's finding: showPdfPages
// passed render() only maxBytes and onPage; file-comments-page-states.test.ts drove the repaint by hand). Pinned here:
// the repaint per failure once the pages are mounted, the same stale guards onPage has (nothing before the mount —
// the resolve's own paint covers a failure the pump reported first — and nothing after the panel closed or a reopen
// rendered afresh), and the wiring at source. The DOM stand-in is file-view-pdf.test.ts's, copied rather than shared
// because that module installs its globals and registers its tests at import; keep the two in step. Synthetic fixtures
// only: the notes-api world, placeholder ids.
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
// render's resolution until the test calls release(i). `fail(i)` does to a shell what pdf-chunk.ts fail() does — the
// canvas removed, the notice appended in the viewer's error dress, the shell kept — and reports it through the opts the
// viewer handed THAT render (an old render's opts stay reachable, for the stale paths).
type ChunkOpts = { maxBytes?: number; onPage?: (p: unknown) => void; onPageError?: (e: { index: number; message: string }) => void };
const FAIL_MSG = "Page dictionary kid reference points to wrong type of object.";
const pdf = {
  renders: 0, disposed: 0, pages: 3, defer: false,
  opts: null as null | ChunkOpts,
  roots: [] as El[], pending: [] as Array<() => void>,
  release(i: number): void { const r = this.pending[i]; assert.ok(r, "render " + i + " is pending"); r(); },
  fail(root: El, opts: ChunkOpts, page: number): void {
    const w = root.querySelector('.fileview-pdf-page[data-page="' + page + '"]')!;
    assert.ok(w, "page " + page + " has a shell");
    w.querySelector("canvas")?.remove();
    const note = doc.createElement("div"); note.className = "fileview-err fileview-pdf-page-err";
    note.textContent = "Page " + page + " did not render — " + FAIL_MSG;
    w.appendChild(note);
    opts.onPageError?.({ index: page, message: FAIL_MSG });
  },
};
const chunkStub = {
  DEFAULT_MAX_BYTES: 25 * 1024 * 1024,
  render(bytes: ArrayBuffer, container: El, opts: ChunkOpts = {}) {
    pdf.renders++; pdf.opts = opts;
    const root = doc.createElement("div"); root.className = "fileview-pdf";
    for (let i = 1; i <= pdf.pages; i++) {
      const w = doc.createElement("div"); w.className = "fileview-pdf-page"; w.dataset.page = String(i); w.style.position = "relative";
      const c = doc.createElement("canvas"); c.className = "fileview-pdf-canvas"; c.dataset.page = String(i);
      w.appendChild(c); root.appendChild(w);
    }
    container.appendChild(root); pdf.roots.push(root);
    opts.onPage?.({ index: 1, canvas: root.childNodes[0], width: 800, height: 1035 });
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
const MT = "1757145600000000001";

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
  pdf.renders = 0; pdf.disposed = 0; pdf.opts = null; pdf.roots.length = 0; pdf.pending.length = 0;
  assert.equal(fv.openFileView(p, SID), true, "the open happened");
  t.after(() => { fv.closeFileView(); pdf.pages = 3; pdf.defer = false; });
  await settle();
  const wrap = doc.getElementById("romp-fileview")!;
  assert.ok(wrap, "the viewer is up");
  const body = wrap.querySelector(".fileview-body")!;
  assert.ok(seam, "the probe action was mounted with the ctx");
  return { fv, ctx: seam!, wrap, body };
}
const panel = () => new El("div") as unknown as HTMLElement;
const shellOf = (ctx: FileViewActionCtx, page: number): El => {
  const s = ctx.pdfPages().find((p) => (p as unknown as El).dataset.page === String(page)) as unknown as El | undefined;
  assert.ok(s, "page " + page + " is among pdfPages()");
  return s!;
};

// ── a page the chunk cannot draw, after the pages are up ───────────────────────────────────────────

test("a later page pdf.js refuses repaints the panel: onPageError fires onRendered once per failure, with the failed shell still among pdfPages(), its canvas gone and the chunk's notice in it", async (t) => {
  const { ctx, body } = await open(DECK, t);
  ctx.aside(panel()); await settle();
  assert.equal(pdf.renders, 1);
  assert.equal(paints, 2, "the frame's paint at open, then the pages' once page 1 drew");
  assert.equal(typeof pdf.opts!.onPageError, "function", "render() is handed onPageError beside onPage");
  const root = body.querySelector(".fileview-pdf")!;
  // page 2 scrolled in and pdf.js could not read its page object: the chunk's fail(), no onPage for it
  pdf.fail(root, pdf.opts!, 2);
  assert.equal(paints, 3, "the failure is a repaint the panel hears — the pass that drops its overlay and tags the card");
  const shells = ctx.pdfPages();
  assert.equal(shells.length, 3, "the failed page's shell is kept: the page set is the shells, and the pages after it stay where they were");
  const s2 = shellOf(ctx, 2);
  assert.equal(s2.querySelector("canvas"), null, "…with no canvas: a page that will never have a bitmap takes no region comment");
  const note = s2.querySelector(".fileview-err.fileview-pdf-page-err")!;
  assert.ok(note, "…and the chunk's notice in the shell, for the card's reference to reach");
  assert.equal(note.textContent, "Page 2 did not render — " + FAIL_MSG);
  assert.equal(ctx.mediaElement(), root as unknown as HTMLElement, "the pages root is still the media element: the other pages are fine");
  assert.equal(ctx.mode(), "media"); assert.equal(ctx.media(), "pdf");
  // a second page failing is another repaint; a page drawing after that still is too (the two callbacks share the guard)
  pdf.fail(root, pdf.opts!, 3);
  assert.equal(paints, 4, "one repaint per failure");
  pdf.opts!.onPage!({ index: 1, canvas: shellOf(ctx, 1).querySelector("canvas"), width: 800, height: 1035 });
  assert.equal(paints, 5, "a redraw of a healthy page still repaints");
  assert.equal(body.querySelector(".fileview-load"), null, "no loader: the failure of one page is in that page, not the body's");
  assert.equal(body.querySelector("iframe.fileview-frame"), null, "…and no fallback to the frame: the pages stay");
});

// ── the stale guards: the same ones onPage has ─────────────────────────────────────────────────────

test("a failure the pump reports before render() resolves counts nothing by itself — the resolve's own paint is the pass that sees the failed shell, so the panel never paints an overlay on it", async (t) => {
  pdf.defer = true;
  const { ctx, body } = await open(DECK, t);
  ctx.aside(panel()); await settle();
  assert.equal(pdf.renders, 1); assert.equal(pdf.pending.length, 1, "the render is in flight: page 1 drew, the promise not yet settled");
  assert.equal(paints, 1, "no pages paint yet");
  assert.ok(body.querySelector(".fileview-load"), "the loader still holds the body");
  pdf.fail(pdf.roots[0], pdf.opts!, 2);
  assert.equal(paints, 1, "before the mount the failure fires nothing: there is no panel state over these pages to correct");
  pdf.release(0); await settle();
  assert.equal(paints, 2, "the resolve's paint, once");
  assert.equal(body.querySelector(".fileview-load"), null, "the loader gave way");
  assert.equal(shellOf(ctx, 2).querySelector("canvas"), null, "…and that pass finds page 2 already without a canvas");
  assert.ok(shellOf(ctx, 2).querySelector(".fileview-pdf-page-err"), "…with its notice");
  assert.equal(ctx.pdfPages().length, 3);
});

test("a failure reported after the panel closed, or from a render a reopen replaced, fires nothing; the live render's failures still repaint", async (t) => {
  const { ctx, body } = await open(DECK, t);
  ctx.aside(panel()); await settle();
  assert.equal(paints, 2);
  const first = pdf.opts!; const root0 = pdf.roots[0];
  ctx.aside(null);
  assert.equal(pdf.disposed, 1, "the close released the render");
  assert.equal(paints, 3, "the frame's own paint");
  assert.ok(body.querySelector("iframe.fileview-frame"), "the browser's viewer is back");
  pdf.fail(root0, first, 2);                              // a pump still winding down after dispose(): the real chunk's disposed flag stops it, but a late report must cost nothing either way
  assert.equal(paints, 3, "a failure from the pages that left fires nothing");
  ctx.aside(panel()); await settle();
  assert.equal(pdf.renders, 2); assert.equal(paints, 4, "the reopen's pages painted");
  pdf.fail(root0, first, 3);
  assert.equal(paints, 4, "the OLD render's report is nothing: its sequence retired when the panel closed");
  pdf.fail(pdf.roots[1], pdf.opts!, 2);
  assert.equal(paints, 5, "the live render's failure repaints");
  assert.equal(shellOf(ctx, 2).querySelector("canvas"), null);
  assert.equal(pdf.disposed, 1, "…and nothing about a page failure disposes the document: the other pages go on drawing");
});

// ── pinned at source: the wiring, and the seam's word on it ────────────────────────────────────────

test("source: render() is handed onPageError under the same stale guard as onPage, and the seam's onRendered doc names the page the chunk could not draw", () => {
  const show = VIEW.split("const showPdfPages = () => {")[1].split("closeHooks.push(dropPdf);")[0];
  const call = show.split("return pdf.render(bytes, host, {")[1].split("}).then((h) => {")[0];
  assert.match(call, /^\s*maxBytes: PDF_MAX_BYTES,/m, "the cap rides into render()");
  assert.match(call, /^\s*onPage: \(\) => \{ if \(my === pdfSeq && pdfHandle\) fireRendered\(\); \},/m, "onPage: a repaint, guarded by the sequence and the mount");
  assert.match(call, /^\s*onPageError: \(\) => \{ if \(my === pdfSeq && pdfHandle\) fireRendered\(\); \},/m,
    "onPageError: the same repaint under the same guard — a failed page's overlay leaves only on a paint pass, and a stale render's report is nothing");
  const seamDoc = VIEW.split("onRendered(cb: () => void): void;")[0].split("renderedImages(): HTMLImageElement[];")[1];
  assert.match(seamDoc, /could not draw/, "the seam's onRendered doc tells the panel a failed page is a paint too");
});
