// The chunk loaders' latch across a load that registers NOTHING (plans/file-review.md Slice 4; decision 12: the frame
// is the fallback for a PDF the pages cannot show). The review of 2026-09-06 found the PDF loader clearing its latch in
// `onerror` only: a <script> the kernel is rewriting mid-fetch (esbuild writes dist/ in place) reaches the browser
// truncated, parses to nothing and fires `load`, not `error`, with the global unset — and that rejection stayed cached
// for the viewer's life, so every later open of the Comments panel over the same file repeated the notice without the
// fetch that would now succeed (closing the viewer was the only recovery). The editor's loader, which the PDF's copies,
// had the same shape. These tests fire `load` with nothing registered and pin the NEXT attempt fetching again, for both
// loaders, at the REAL openFileView. The DOM stand-in, the chunk stub and the fetch stub are file-view-pdf-frame.test.ts's
// (themselves file-view-pdf.test.ts's), copied rather than shared because each module installs its globals and registers
// its tests at import; keep them in step. Synthetic fixtures only: the notes-api world, placeholder ids, TESTHOST.
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

// ── the PDF chunk: load fires, nothing registered — the next open fetches again ────────────────────────

test("the chunk loading but not registering: the frame stays under the notice; the next open fetches the chunk AGAIN (the latch is cleared, as after a failed load), and that load renders", async (t) => {
  unregistered(t);
  const { ctx, body } = await open(DECK, t);
  const f0 = frameIn(body)!; const col = colOf(f0);
  ctx.aside(panel()); await settle();
  let scripts = doc.head.querySelectorAll("script");
  assert.equal(scripts.length, 1, "the chunk's script tag is out");
  scripts[0].onload!(); await settle();                  // `load` with nothing registered: a truncated delivery
  assert.equal(frameIn(body), f0, "the same frame under the notice");
  assert.equal(noteIn(body)!.textContent, "PDF chunk loaded but did not register" + NOTICE_TAIL);
  assert.equal(body.querySelector(".fileview-load"), null); assert.equal(body.querySelector(".fileview-pdfhost"), null);
  assert.equal(pdf.renders, 0, "nothing to render with");
  ctx.aside(null);
  assert.equal(noteIn(body), null); assert.equal(frameIn(body), f0);
  ctx.aside(panel()); await settle();
  scripts = doc.head.querySelectorAll("script");
  assert.equal(scripts.length, 2, "a second script tag: the load that registered nothing is retried, as a failed load is");
  assert.equal(frameIn(body), f0, "…over the same frame");
  assert.ok(col.querySelector(".fileview-load"), "under the loader");
  win.__rompPdf = chunkStub; scripts[1].onload!(); await settle();
  assert.equal(pdf.renders, 1, "the retry rendered");
  assert.equal(frameIn(body), null, "the pages replaced the frame");
  assert.equal(ctx.pdfPages().length, 2);
});

// The cleared latch runs the WHOLE loader again, its global-first check included: a chunk that registered on the page
// after the empty load (a second, whole delivery of the same tag) is used without another fetch. Before the fix the
// viewer never looked at the global again either.
test("…and a chunk registered on the page since that load is used by the next open without another fetch: the retry is the whole loader, the global first", async (t) => {
  unregistered(t);
  const { ctx, body } = await open(DECK, t);
  ctx.aside(panel()); await settle();
  const scripts = doc.head.querySelectorAll("script");
  assert.equal(scripts.length, 1);
  scripts[0].onload!(); await settle();
  assert.equal(noteIn(body)!.textContent, "PDF chunk loaded but did not register" + NOTICE_TAIL);
  win.__rompPdf = chunkStub;                             // the chunk is on the page now
  ctx.aside(null); ctx.aside(panel()); await settle();
  assert.equal(doc.head.querySelectorAll("script").length, 1, "no second tag: the global answered");
  assert.equal(pdf.renders, 1, "…and rendered");
  assert.equal(ctx.pdfPages().length, 2);
});

// ── the editor chunk: the loader the PDF's copies, the same latch, the same fix ────────────────────────

/** No editor registered, and a hosting page's bundle tag: the editor chunk is then fetched by a script tag the test fires. */
function unregisteredEditor(t: TestContext): void {
  const saved = win.__rompEditor; win.__rompEditor = undefined;
  const tag = new El("script"); tag.src = "http://TESTHOST:29855/dist/files.js?v=1725300000"; tag.setAttribute("src", tag.src);
  doc.body.appendChild(tag);
  t.after(() => { win.__rompEditor = saved; tag.remove(); doc.head.replaceChildren(); });
}
const button = (wrap: El, label: string): El => {
  const b = wrap.querySelectorAll("button").find((x) => x.textContent === label);
  assert.ok(b, "a " + label + " button"); return b!;
};

test("the editor chunk loading but not registering: the plain editor with the notice; the next Edit fetches the chunk AGAIN (the latch is cleared), and that load mounts the editor", async (t) => {
  unregisteredEditor(t);
  const { wrap, body } = await open(NOTE, t);
  const edit = button(wrap, "Edit");
  assert.equal(edit.hidden, false, "a text file with an mtime: Edit is offered");
  edit.click(); await settle();                          // consent is on (the /version stub); the chunk is fetched
  let scripts = doc.head.querySelectorAll("script");
  assert.equal(scripts.length, 1, "the editor chunk's script tag is out");
  scripts[0].onload!(); await settle();                  // `load` with nothing registered
  assert.ok(body.querySelector("textarea.fileview-editor"), "the plain fallback editor, loudly");
  assert.equal(doc.getElementById("fileview-save-err")!.textContent,
    "editor chunk loaded but did not register — editing in the plain fallback editor.");
  button(wrap, "Cancel").click(); await settle();        // nothing typed: leaving asks nothing
  assert.equal(body.querySelector("textarea.fileview-editor"), null, "back to the read view");
  button(wrap, "Edit").click(); await settle();
  scripts = doc.head.querySelectorAll("script");
  assert.equal(scripts.length, 2, "a second script tag: the load that registered nothing is retried");
  let mounted = 0;
  win.__rompEditor = { mount: (host: El) => { mounted++; host.appendChild(new Txt("cm")); return { value: () => "# notes\n", focus() { /* */ }, destroy() { /* */ } }; } };
  scripts[1].onload!(); await settle();
  assert.equal(mounted, 1, "the retry mounted the editor");
  assert.ok(body.querySelector(".fileview-cm"), "…in its host");
  assert.equal(doc.getElementById("fileview-save-err"), null, "and no notice remains");
});

// ── at source: the two loaders clear the latch in BOTH branches, in step ───────────────────────────────

test("both loaders clear their latch when `load` fires with nothing registered, exactly as in onerror", () => {
  assert.match(VIEW, /sc\.onload = \(\) => \{ const e = \(window as any\)\.__rompEditor; if \(!e\) edChunk = null; e \? res\(e\) : rej\(new Error\("editor chunk loaded but did not register"\)\); \};/);
  assert.match(VIEW, /sc\.onerror = \(\) => \{ edChunk = null; rej\(new Error\("the editor bundle failed to load"\)\); \};/);
  assert.match(VIEW, /sc\.onload = \(\) => \{ const p = \(window as any\)\.__rompPdf; if \(!p\) pdfChunk = null; p \? res\(p\) : rej\(new Error\("PDF chunk loaded but did not register"\)\); \};/);
  assert.match(VIEW, /sc\.onerror = \(\) => \{ pdfChunk = null; rej\(new Error\("the PDF renderer failed to load"\)\); \};/);
});
