// Reload at the real openFileView (plans/file-review.md, "The viewer seam"; Slice 1's whole-file comments
// on standalone images, Slice 2's re-fetch after a decision). The comments panel calls ctx.reload() whenever
// the file's mtime moves — a session regenerating a figure under an open panel — and the blob branch of
// the fetch pipeline then has two jobs the text branch does not: revoke the previous bytes' object URL
// before minting the new one (a leak per reload otherwise), and give the SVG Source view the NEW XML (the
// old decode is a lie about the file). The seam suite's only reload is a text file, so either line could
// go missing and every suite stayed green (review round 3, a mutation probe). And two reloads in flight
// must resolve to the NEWER bytes whatever order the kernel answers in: the Slice 2 review found the panel's
// moved-fence retry issuing two fetches with nothing ordering them, and an older response landing last
// would put its bytes in the body under the newer response's mtime. Here the viewer runs over the seam
// suite's DOM stand-in (file-view-seam.test.ts, copied: node --test runs each file in its own process, and
// this one stubs URL.revokeObjectURL and hands the viewer Blobs and texts whose decode it can hold) and
// each job is checked by what the viewer DOES. The changed-on-disk cases at the end (plans/markdown-viewer.md Slice 6,
// item 5) drive the same stand-in through the window's `focus` and the document's `visibilitychange`, the two events
// that run the viewer's HEAD /file while the Comments panel is closed, and read the bar the moved mtime raises above the
// body row, its Reload, and the landing that clears it; the fetch stub answers a HEAD with the headers and no body, as the
// kernel does, and can hold one, fail one on the network or answer it 413. Synthetic fixtures only: the notes-api world,
// placeholder ids.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import { inspect } from "node:util";
import { assertHiddenEvent, hideEdges, staysEnumerable } from "../test-dom-shim";
import type { FileViewActionCtx } from "./file-view";


// ── a DOM stand-in: ancestry, ids, attributes, events with capture and bubbling, a small selector engine ──
class Ev {
  target: El | Txt | null = null;
  currentTarget: El | null = null;
  defaultPrevented = false;
  stopped = false;
  key: string; ctrlKey: boolean; metaKey: boolean;
  constructor(public type: string, init: { key?: string; ctrlKey?: boolean; metaKey?: boolean } = {}) {
    this.key = init.key || ""; this.ctrlKey = !!init.ctrlKey; this.metaKey = !!init.metaKey;
    hideEdges(this);
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
  parentNode!: El | null;
  constructor(public data: string) { Object.defineProperty(this, "parentNode", { value: null, writable: true, enumerable: false, configurable: true }); hideEdges(this); }
  get textContent(): string { return this.data; }
  get parentElement(): El | null { return this.parentNode; }
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
class El {
  nodeType = 1;
  tagName: string;
  parentNode!: El | null;
  childNodes!: Array<El | Txt>;
  attrs = new Map<string, string>();
  listeners: Reg[] = [];
  hidden = false; _disabled = false; title = ""; type = ""; value = ""; placeholder = ""; spellcheck = true; wrap = "";
  src = ""; alt = ""; href = ""; download = ""; target = ""; rel = "";
  innerHTML = "";
  style: Record<string, string> = {};
  onclick: ((ev: Ev) => void) | null = null;
  scrolled = 0;                                  // scrollIntoView calls (scrollToOffset's visible effect)
  constructor(tag: string) {
    this.tagName = tag.toUpperCase();
    Object.defineProperty(this, "parentNode", { value: null, writable: true, enumerable: false, configurable: true });
    Object.defineProperty(this, "childNodes", { value: [], writable: true, enumerable: false, configurable: true });
    hideEdges(this);
  }
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
  set textContent(v: string) { for (const c of this.childNodes) c.parentNode = null; this.childNodes.length = 0; if (v !== "") this.appendChild(new Txt(v)); }
  private detach(n: El | Txt): void { const p = n.parentNode; if (p) { const i = p.childNodes.indexOf(n); if (i >= 0) p.childNodes.splice(i, 1); n.parentNode = null; } }
  /** The browser's focus fixup: a removed subtree that holds the active element drops it to the document's body (the
   *  changed-on-disk bar's Reload, focused by its click and removed with the bar at the landing). */
  private dropFocusIn(n: El | Txt): void { if (n instanceof El && doc.activeElement && n.contains(doc.activeElement)) doc.activeElement = doc.body; }
  appendChild<T extends El | Txt>(n: T): T { this.detach(n); this.childNodes.push(n); n.parentNode = this; return n; }
  prepend(...ns: Array<El | Txt>): void { for (const n of ns.slice().reverse()) { this.detach(n); this.childNodes.unshift(n); n.parentNode = this; } }
  insertBefore<T extends El | Txt>(n: T, ref: El | Txt | null): T {
    if (!ref) return this.appendChild(n);
    this.detach(n);
    const i = this.childNodes.indexOf(ref);
    this.childNodes.splice(i < 0 ? this.childNodes.length : i, 0, n); n.parentNode = this; return n;
  }
  removeChild<T extends El | Txt>(n: T): T { this.dropFocusIn(n); this.detach(n); return n; }
  replaceChildren(...c: Array<El | Txt>): void { for (const x of this.childNodes) { this.dropFocusIn(x); x.parentNode = null; } this.childNodes.length = 0; for (const x of c) this.appendChild(x); }
  remove(): void { this.dropFocusIn(this); this.detach(this); }
  normalize(): void { /* no adjacent text nodes are built here */ }
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
  get disabled(): boolean { return this._disabled; }
  /** A browser drops the focus off a control the moment it is disabled (Chromium: synchronously, to the document's body), so
   *  the changed-on-disk bar's Reload, focused by its click and disabled by its own handler, has lost the keyboard before its
   *  landing. The review's round 1: as a plain field the stand-in kept the focus on the disabled button, and case 14 passed
   *  over a path the browser never takes (the landing-time read found the button; in a browser it found the document's body). */
  set disabled(v: boolean) { this._disabled = v; if (v && doc.activeElement && this.contains(doc.activeElement)) doc.activeElement = doc.body; }
  focus(): void { doc.activeElement = this; }
  blur(): void { if (doc.activeElement === this) doc.activeElement = null; }
  scrollIntoView(): void { this.scrolled++; }
  getBoundingClientRect(): { left: number; top: number; right: number; bottom: number; width: number; height: number } { return { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 }; }
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
  /** An event on the document itself (visibilitychange): its capture listeners, then its bubble listeners. */
  dispatchEvent(ev: Ev): boolean {
    for (const capture of [true, false]) for (const l of doc.listeners.slice()) {
      if (l.type !== ev.type || l.capture !== capture) continue;
      if (l.once) doc.listeners = doc.listeners.filter((x) => x !== l);
      ev.currentTarget = null; l.cb.call(null, ev);
    }
    return !ev.defaultPrevented;
  },
};
doc.body = new El("body"); doc.head = new El("head");
/** The DOM event path: document capture, ancestors' capture root→target, target and ancestors' bubble, document bubble. */
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
let selection: any = null;
win.getSelection = () => selection;
win.confirm = () => true;
win.postMessage = () => { /* our own window: nothing listens here */ };
(globalThis as any).window = win;
(globalThis as any).location = { protocol: "http:" };   // the web dashboard: the viewer's discard ask is a confirm here (canPreview)
(globalThis as any).document = doc;
const store = new Map<string, string>();
(globalThis as any).localStorage = {
  getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
  setItem: (k: string, v: string) => { store.set(k, String(v)); },
  removeItem: (k: string) => { store.delete(k); },
};
// The editing substrate: the lazily-loaded CodeMirror chunk registers a window global the viewer's
// editorChunk() resolves from; this one is a buffer with the two callbacks the viewer wires.
const ed = { buf: "", onChange: null as (() => void) | null, mounted: 0, destroyed: 0 };
win.__rompEditor = {
  mount(host: El, opts: { text: string; onChange: () => void; onSave: () => void }) {
    ed.buf = opts.text; ed.onChange = opts.onChange; ed.mounted++;
    host.appendChild(new Txt(opts.text));
    return { value: () => ed.buf, focus() { /* inert */ }, destroy() { ed.destroyed++; } };
  },
};

// ── the kernel's /file, /version and /sessions, as the viewer fetches them ──────────────────────────
// A served file may bring its own Blob, or its own text(): the deferrable tests hand the viewer bytes
// whose decode (or whose body read) resolves when the test says so, which is how a response gets
// overtaken by a newer reload or a close.
// `head`: the status a HEAD of the file answers instead of 200 (413: too large to serve); `headWait`: a HEAD's answer waits
// on it (a slow kernel, for the one-in-flight cases); `headFail`: the HEAD fails on the network (the fetch rejects).
type Served = { bytes: string | Uint8Array; type: string; mtimeNs: string; blob?: () => Blob; text?: () => Promise<string>; head?: number; headWait?: Promise<void>; headFail?: boolean };
const disk: Record<string, Served> = {};
const fetches: string[] = [];
(globalThis as any).fetch = async (url: string, init?: { method?: string }) => {
  const method = (init && init.method) || "GET";
  fetches.push(method + " " + url.replace(/[?&]token=[^&]*/, ""));
  if (url.startsWith("/version")) return { json: async () => ({ fileEditing: true }) };   // consent already given
  if (url.startsWith("/sessions")) return { json: async () => [] };
  const p = decodeURIComponent((/[?&]path=([^&]*)/.exec(url) || [])[1] || "");
  const f = disk[p];
  // an image 200 wears image/* and no X-Romp-Text-Utf8 (tests/test_kernel_preview.py pins that server-side)
  const headers = { get: (h: string) => (f ? (h === "Content-Type" ? f.type : h === "X-Romp-Mtime-Ns" ? f.mtimeNs : h === "X-Romp-Text-Utf8" && f.type.startsWith("text/") ? "1" : null) : null) };
  if (method === "HEAD") {
    // the kernel's HEAD /file: the GET's headers and no bytes (tests/test_kernel_preview.py pins the empty body)
    if (f && f.headWait) await f.headWait;
    if (f && f.headFail) throw new TypeError("network gone");
    if (!f) return { ok: false, status: 404, headers, text: async () => "" };
    if (f.head) return { ok: false, status: f.head, headers, text: async () => "" };
    return { ok: true, status: 200, headers, text: async () => "" };
  }
  if (!f) return { ok: false, status: 404, headers, text: async () => "no such file: " + p };
  return {
    ok: true, status: 200, headers,
    text: () => (f.text ? f.text() : Promise.resolve(String(f.bytes))),
    blob: async () => (f.blob ? f.blob() : new Blob([f.bytes as unknown as BlobPart], { type: f.type })),
  };
};
/** A body read that waits for the test: resolves with the text on `release()`, rejects on `fail()`. */
function heldText(text: string): { text: () => Promise<string>; release: () => void; fail: (why: string) => void } {
  let release!: () => void, fail!: (why: string) => void;
  const held = new Promise<string>((ok, no) => { release = () => ok(text); fail = (why) => no(new Error(why)); });
  return { text: () => held, release, fail };
}
/** A Blob whose decode waits for the test: text() resolves with the bytes only once `release()` is called. */
class HeldBlob extends Blob {
  private readonly held: Promise<string>;
  release!: () => void;
  constructor(xml: string, type: string) {
    super([xml], { type });
    this.held = new Promise<string>((r) => { this.release = () => r(xml); });
  }
  override text(): Promise<string> { return this.held; }
}

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ROOT = "/repo/notes-api";
const PLOT = ROOT + "/docs/plot.png";
const FIG = ROOT + "/docs/figure.svg";
const APP = ROOT + "/src/app.py";
const PY = "def main():\n    return 40  # p95 latency, percent\n";
const PY2 = PY.replace("40", "41");
const PY3 = PY.replace("40", "42");
const PNG1 = new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x01]);
const PNG2 = new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x02, 0x02]);
const svg = (label: string) => '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">\n  <text x="1" y="8">' + label + "</text>\n</svg>\n";
const SVG1 = svg("p95 latency, v1");
const SVG2 = svg("p95 latency, v2");
const SVG3 = svg("p99 latency, v3");
const MT = "1757145600000000001";
const MT2 = "1757145600000000007";
const MT3 = "1757145600000000008";
const MT4 = "1757145600000000009";

// ── the probe: an action whose only job is to keep the ctx the viewer hands it ──────────────────────
let seam: FileViewActionCtx | null = null;
let paints = 0;
const posted: any[] = [];
let fvMod: typeof import("./file-view") | null = null;
async function mod(): Promise<typeof import("./file-view")> {
  if (fvMod) return fvMod;
  fvMod = await import("./file-view");
  fvMod.initFileView((m) => posted.push(m));
  fvMod.registerFileViewAction({
    id: "seam-probe",
    mount(ctx) { seam = ctx; ctx.onRendered(() => { paints++; }); return null; },
  });
  fvMod.setFileViewIdentity((sid) => (sid === SID ? { name: "api", color: { bg: "#123456", fg: "#ffffff" } } : null));
  return fvMod;
}
const settle = async () => { for (let i = 0; i < 8; i++) await new Promise<void>((r) => setImmediate(r)); };
type Open = { fv: typeof import("./file-view"); ctx: FileViewActionCtx; wrap: El; body: El; src: El };
async function open(p: string, t: TestContext): Promise<Open> {
  const fv = await mod();
  disk[PLOT] = { bytes: PNG1, type: "image/png", mtimeNs: MT };
  disk[FIG] = { bytes: SVG1, type: "image/svg+xml", mtimeNs: MT };
  disk[APP] = { bytes: PY, type: "text/plain; charset=utf-8", mtimeNs: MT };
  posted.length = 0; fetches.length = 0; paints = 0; seam = null;
  assert.equal(fv.openFileView(p, SID), true, "the open happened");
  t.after(() => { fv.closeFileView(); });
  await settle();
  const wrap = doc.getElementById("romp-fileview")!;
  assert.ok(wrap, "the viewer is up");
  const body = wrap.querySelector(".fileview-body")!;
  const src = wrap.querySelector(".fileview-acts")!.querySelectorAll("button").find((x) => x.textContent === "Source")!;
  assert.ok(src, "the Source button exists (hidden unless the body is an SVG)");
  assert.ok(seam, "the probe action was mounted with the ctx");
  return { fv, ctx: seam!, wrap, body, src };
}
/** Count and record every URL.revokeObjectURL for the test's duration. */
function watchRevokes(t: TestContext): string[] {
  const revoked: string[] = [];
  const real = URL.revokeObjectURL;
  URL.revokeObjectURL = ((u: string) => { revoked.push(u); real.call(URL, u); }) as typeof URL.revokeObjectURL;
  t.after(() => { URL.revokeObjectURL = real; });
  return revoked;
}
const img = (body: El) => body.querySelector("img.fileview-img");

test("reload on an image: the previous object URL is revoked once, the <img> gets the new bytes' URL, and close revokes only that one", async (t) => {
  const revoked = watchRevokes(t);
  const { fv, ctx, body } = await open(PLOT, t);
  const firstImg = img(body)!;
  const first = firstImg.src;
  assert.ok(first.startsWith("blob:"), "the open minted an object URL");
  assert.equal(ctx.mode(), "media"); assert.equal(ctx.mtimeNs(), MT);
  assert.equal(ctx.mediaElement(), firstImg as unknown as HTMLElement, "the seam's media element is the picture in the body");
  disk[PLOT] = { bytes: PNG2, type: "image/png", mtimeNs: MT2 };   // a session regenerated the figure
  ctx.reload();
  await settle();
  assert.deepEqual(revoked, [first], "the old bytes' URL went, exactly once, before the new one was minted");
  const secondImg = img(body)!;
  const second = secondImg.src;
  assert.ok(second.startsWith("blob:") && second !== first, "one <img>, at a NEW object URL");
  assert.equal(body.querySelectorAll("img").length, 1, "the reload replaced the image, it did not stack one");
  assert.equal(ctx.mtimeNs(), MT2, "the mtime followed the kernel's header");
  assert.equal(ctx.mode(), "media"); assert.equal(ctx.media(), "image"); assert.equal(ctx.text(), null);
  assert.equal(ctx.mediaElement(), secondImg as unknown as HTMLElement, "mediaElement() follows the reload — read from the body, never a kept handle");
  // the media paint (Slice 3): onRendered waits for the picture to load, and only the picture that is showing counts
  assert.equal(paints, 0, "neither picture has loaded: no onRendered yet");
  firstImg.dispatchEvent(new Ev("load"));
  assert.equal(paints, 0, "a load landing on the REPLACED picture fires nothing — an overlay sized against it would frame nothing anyone sees");
  secondImg.dispatchEvent(new Ev("load"));
  assert.equal(paints, 1, "the showing picture's load is the media paint");
  fv.closeFileView();
  assert.deepEqual(revoked, [first, second], "close revokes the CURRENT URL — the registration moved with the reload");
});

test("reload under the SVG Source view: text() and the body follow the new XML, the view stays Source, one repaint", async (t) => {
  const { ctx, body, src } = await open(FIG, t);
  assert.equal(src.hidden, false, "an image/svg+xml body unlocks Source");
  assert.equal(ctx.mode(), "media"); assert.equal(ctx.media(), "svg"); assert.equal(ctx.text(), null);
  src.click();
  await settle();
  assert.equal(ctx.mode(), "raw", "the Source view is a text view");
  assert.equal(ctx.text(), SVG1, "the decoded bytes");
  assert.ok(body.querySelector("code.hljs") && !img(body), "the highlighted XML holds the body");
  assert.equal(paints, 1, "the Source paint fires onRendered");
  disk[FIG] = { bytes: SVG2, type: "image/svg+xml", mtimeNs: MT2 };
  ctx.reload();
  await settle();
  assert.equal(ctx.text(), SVG2, "text() is the NEW XML — the panel's anchors and quotes read this");
  assert.equal(ctx.mtimeNs(), MT2);
  assert.equal(ctx.mode(), "raw", "still the Source view");
  assert.equal(src.classList.contains("on"), true); assert.equal(src.getAttribute("aria-pressed"), "true");
  assert.ok(body.querySelector("code.hljs") && !img(body), "…and the body is still the XML, not a flash of the image");
  assert.equal(paints, 2, "exactly one repaint for the reload, with the new text");
});

test("reload with the Source view toggled OFF: the stale decode is dropped, so the next Source click shows the new XML", async (t) => {
  const { ctx, body, src } = await open(FIG, t);
  src.click(); await settle();
  assert.equal(ctx.text(), SVG1);
  src.click();                                            // back to the image: the decode stays cached…
  assert.equal(ctx.mode(), "media"); assert.equal(ctx.text(), null);
  assert.ok(img(body));
  disk[FIG] = { bytes: SVG3, type: "image/svg+xml", mtimeNs: MT3 };   // …until the bytes change under it
  ctx.reload();
  await settle();
  assert.equal(ctx.mode(), "media"); assert.equal(ctx.mtimeNs(), MT3);
  assert.equal(paints, 1, "the reloaded picture has not loaded: the Source paint is still the only one");
  src.click();
  await settle();
  assert.equal(ctx.mode(), "raw");
  assert.equal(ctx.text(), SVG3, "the Source view decodes the reloaded blob, never the one it read before the reload");
  assert.equal(paints, 2);
});

test("a Source-view decode overtaken by a newer reload, or landing after close, paints nothing — and the view never flaps to media while it waits", async (t) => {
  const { fv, ctx, src } = await open(FIG, t);
  src.click(); await settle();
  assert.equal(ctx.text(), SVG1);
  const held = new HeldBlob(SVG2, "image/svg+xml");
  disk[FIG] = { bytes: SVG2, type: "image/svg+xml", mtimeNs: MT2, blob: () => held };
  ctx.reload();
  await settle();                                         // the bytes landed; their decode has not
  assert.equal(ctx.mtimeNs(), MT2, "the fetch landed");
  assert.equal(ctx.mode(), "raw", "no flap to media while the decode is pending");
  assert.equal(ctx.text(), SVG1, "the old XML stands until the new one is decoded — never a null in between");
  assert.equal(paints, 1, "nothing repainted yet: no stale repaint, no image flash");
  disk[FIG] = { bytes: SVG3, type: "image/svg+xml", mtimeNs: MT3 };   // a second write lands first
  ctx.reload();
  await settle();
  assert.equal(ctx.text(), SVG3); assert.equal(ctx.mtimeNs(), MT3); assert.equal(paints, 2);
  held.release();                                         // the overtaken decode finally resolves…
  await settle();
  assert.equal(ctx.text(), SVG3, "…and changes nothing: the newest bytes are what show");
  assert.equal(paints, 2, "no repaint for a superseded decode");
  const late = new HeldBlob(svg("v4"), "image/svg+xml");
  disk[FIG] = { bytes: svg("v4"), type: "image/svg+xml", mtimeNs: MT4, blob: () => late };
  ctx.reload();
  await settle();
  fv.closeFileView();
  assert.equal(doc.getElementById("romp-fileview"), null);
  late.release();
  await settle();
  assert.equal(paints, 2, "a decode landing after the close fires no onRendered — the panel's hooks were drained with the viewer");
});

test("two text reloads in flight: the newer wins whatever order they answer in — an older response landing last repaints nothing and lends the view no mtime; an older FAILURE landing last raises no error row", async (t) => {
  const { ctx, body } = await open(APP, t);
  assert.equal(ctx.mode(), "raw"); assert.equal(ctx.text(), PY); assert.equal(ctx.mtimeNs(), MT);
  assert.equal(paints, 1, "the open's paint");
  // reload 1 answers its headers at once (the viewer reads the mtime there) but its body waits
  const slow = heldText(PY2);
  disk[APP] = { bytes: PY2, type: "text/plain; charset=utf-8", mtimeNs: MT2, text: slow.text };
  ctx.reload();
  await settle();
  // reload 2, issued while 1 is out, lands whole
  disk[APP] = { bytes: PY3, type: "text/plain; charset=utf-8", mtimeNs: MT3 };
  ctx.reload();
  await settle();
  assert.equal(ctx.text(), PY3, "the newer bytes show");
  assert.equal(ctx.mtimeNs(), MT3, "under their own mtime");
  assert.equal(paints, 2, "one repaint for the newer reload");
  slow.release();                                          // the older body finally arrives…
  await settle();
  assert.equal(ctx.text(), PY3, "…and changes nothing: the view never shows older bytes than it did");
  assert.equal(ctx.mtimeNs(), MT3, "…nor takes the older response's mtime (the panel trusts mtimeNs() to name the text it paints over)");
  assert.equal(paints, 2, "no repaint for an overtaken response");
  assert.ok(body.querySelector("code.hljs"), "the body is the text view");
  assert.equal(body.querySelector(".fileview-err"), null);
  // an older response that FAILS after a newer one landed is nobody's error: the body keeps the newer text
  const failing = heldText("");
  disk[APP] = { bytes: "", type: "text/plain; charset=utf-8", mtimeNs: MT4, text: failing.text };
  ctx.reload();
  await settle();
  const v5 = PY.replace("40", "45");
  disk[APP] = { bytes: v5, type: "text/plain; charset=utf-8", mtimeNs: "1757145600000000010" };
  ctx.reload();
  await settle();
  assert.equal(ctx.text(), v5); assert.equal(paints, 3);
  failing.fail("network gone");
  await settle();
  assert.equal(body.querySelector(".fileview-err"), null, "an overtaken failure replaces nothing");
  assert.equal(ctx.text(), v5); assert.equal(ctx.mtimeNs(), "1757145600000000010"); assert.equal(paints, 3);
});

// ── changed on disk (plans/markdown-viewer.md Slice 6, item 5) ────────────────────────────────────────────────────────
// The events: a `focus` on the window and a `visibilitychange` on the document (the stand-in's window is a real
// EventTarget; the document dispatches its own). The reading: the requests the stub saw by method, the bar
// `#fileview-save-err` as a row of the card between the title bar and the body row, its words as its own text nodes (the
// button's label is a child, not the words), its one button and that button's state.
const TEXT = "text/plain; charset=utf-8";
const CHANGED = "Changed on disk.";
const heads = () => fetches.filter((f) => f.startsWith("HEAD ")).length;
const gets = () => fetches.filter((f) => f.startsWith("GET ") && /[?&]path=/.test(f)).length;
const focusWindow = () => { win.dispatchEvent(new Event("focus")); };
const visibility = (hidden: boolean) => { doc.hidden = hidden; doc.dispatchEvent(new Ev("visibilitychange")); };
const barOf = (wrap: El): El | null => wrap.querySelector("#fileview-save-err");
const cardRows = (wrap: El): string[] => wrap.querySelector(".fileview")!.childNodes.filter((x): x is El => x instanceof El).map((x) => x.className);
type BarRead = { text: string; button: string | null; disabled: boolean; rows: string[] };
function readBar(wrap: El): BarRead {
  const bar = barOf(wrap);
  const btns = bar ? bar.querySelectorAll("button") : [];
  return {
    text: bar ? bar.childNodes.filter((x): x is Txt => x instanceof Txt).map((x) => x.textContent).join("") : "",
    button: btns.length === 1 ? btns[0].textContent : btns.length ? "(" + btns.length + " buttons)" : null,
    disabled: btns.length === 1 && btns[0].disabled, rows: cardRows(wrap),
  };
}
/** Every element under `root`, for a read the stand-in's selector engine has no word for (`*`). */
const allEls = (root: El): El[] => { const out: El[] = []; const visit = (n: El) => { for (const c of n.childNodes) if (c instanceof El) { out.push(c); visit(c); } }; visit(root); return out; };
const reloadButton = (wrap: El): El => { const b = barOf(wrap)!.querySelectorAll("button"); assert.equal(b.length, 1, "one button in the bar"); return b[0]; };
/** A HEAD whose answer waits for the test. */
function heldHead(): { wait: Promise<void>; release: () => void } { let release!: () => void; const wait = new Promise<void>((r) => { release = r; }); return { wait, release }; }
const visibleAfter = (t: TestContext) => { t.after(() => { doc.hidden = false; }); };

test("changed on disk: a window focus sends one HEAD of the file's URL and the same mtime raises nothing; a moved mtime raises the bar above the body row with its words and a Reload button, fetching no bytes; a second move while it stands changes nothing; a visibilitychange to hidden asks nothing and to visible asks once", async (t) => {
  visibleAfter(t);
  const { wrap, ctx } = await open(APP, t);
  assert.equal(heads(), 0, "the open sends no HEAD");
  focusWindow(); await settle();
  assert.equal(heads(), 1, "one HEAD for the focus");
  assert.match(fetches.find((f) => f.startsWith("HEAD "))!, /^HEAD \/file\?path=%2Frepo%2Fnotes-api%2Fsrc%2Fapp\.py&sid=11111111-2222-3333-4444-555555555555$/, "the URL the GET used (fileUrl)");
  assert.equal(barOf(wrap), null, "the same mtime: no bar");
  assert.deepEqual(cardRows(wrap), ["fileview-bar", "fileview-main"]);
  disk[APP] = { bytes: PY2, type: TEXT, mtimeNs: MT2 };   // a session wrote the file
  focusWindow(); await settle();
  assert.equal(heads(), 2);
  const b = readBar(wrap);
  assert.equal(b.text, CHANGED, "the bar's words");
  assert.equal(b.button, "Reload", "and its one button");
  assert.equal(b.disabled, false);
  assert.deepEqual(b.rows, ["fileview-bar", "fileview-err", "fileview-main"], "a row of the card between the title bar and the body row (noteBar's place)");
  assert.equal(ctx.text(), PY, "the body shows the text the reader has: the probe fetched no bytes");
  assert.equal(ctx.mtimeNs(), MT); assert.equal(gets(), 1, "the open's GET alone"); assert.equal(paints, 1, "no repaint");
  disk[APP] = { bytes: PY3, type: TEXT, mtimeNs: MT3 };   // and again, while the bar stands
  focusWindow(); await settle();
  assert.equal(heads(), 3, "the probe still asks while the bar stands");
  assert.deepEqual(readBar(wrap), b, "one bar, the same words, one button");
  assert.equal(wrap.querySelectorAll("#fileview-save-err").length, 1);
  visibility(true); await settle();
  assert.equal(heads(), 3, "hidden: nothing asked");
  focusWindow(); await settle();
  assert.equal(heads(), 3, "a focus while the document is hidden asks nothing either");
  visibility(false); await settle();
  assert.equal(heads(), 4, "visible again: one HEAD");
});

test("changed on disk: one HEAD in flight: a focus, a second focus and a visibilitychange while it is out send one request, and the next event after its answer asks again; a HEAD that fails on the network raises nothing and does not retire the probe", async (t) => {
  visibleAfter(t);
  const { wrap } = await open(APP, t);
  const held = heldHead();
  disk[APP] = { bytes: PY, type: TEXT, mtimeNs: MT, headWait: held.wait };
  focusWindow(); focusWindow(); visibility(false); await settle();
  assert.equal(heads(), 1, "folded into the one out: no timer, no queue");
  held.release(); await settle();
  assert.equal(barOf(wrap), null, "the same mtime");
  focusWindow(); await settle();
  assert.equal(heads(), 2, "the answer landed: the next event asks");
  disk[APP] = { bytes: PY2, type: TEXT, mtimeNs: MT2, headFail: true };
  focusWindow(); await settle();
  assert.equal(heads(), 3); assert.equal(barOf(wrap), null, "a network failure says nothing: nothing the reader sees has changed");
  disk[APP] = { bytes: PY2, type: TEXT, mtimeNs: MT2 };
  focusWindow(); await settle();
  assert.equal(heads(), 4, "not retired"); assert.equal(readBar(wrap).text, CHANGED, "and the move is seen this time");
});

test("changed on disk: a 413 retires the probe for the open: a later focus or visibility sends nothing though the file moved; a replace-open of the path arms a fresh probe, and one focus is one HEAD (the replaced viewer's listeners left with it)", async (t) => {
  visibleAfter(t);
  const { fv, wrap } = await open(APP, t);
  disk[APP] = { bytes: PY, type: TEXT, mtimeNs: MT, head: 413 };
  focusWindow(); await settle();
  assert.equal(heads(), 1); assert.equal(barOf(wrap), null, "a stop verdict raises nothing");
  disk[APP] = { bytes: PY2, type: TEXT, mtimeNs: MT2 };
  focusWindow(); visibility(false); await settle();
  assert.equal(heads(), 1, "retired for this open");
  assert.equal(fv.openFileView(APP, SID), true); await settle();   // the replace path: a fresh viewer over the moved file
  const wrap2 = doc.getElementById("romp-fileview")!;
  assert.ok(wrap2 !== wrap && !wrap.isConnected, "a new card");
  fetches.length = 0;
  focusWindow(); await settle();
  assert.equal(heads(), 1, "one HEAD, the new viewer's: the replaced viewer's listeners are gone");
  assert.equal(barOf(wrap2), null, "the fresh open read the moved file; nothing moved since");
});

test("changed on disk: Reload disables the button and relabels it Reloading at the click, fetches the file once, and the landing with the moved mtime removes the bar: one repaint, the new text under the new mtime, nothing scrolled into view (a reload keeps the reader's place by its own rule)", async (t) => {
  const { wrap, ctx, body } = await open(APP, t);
  disk[APP] = { bytes: PY2, type: TEXT, mtimeNs: MT2 };
  focusWindow(); await settle();
  const bar = barOf(wrap)!; const btn = reloadButton(wrap);
  assert.equal(gets(), 1);
  btn.click();
  assert.equal(btn.disabled, true); assert.equal(btn.textContent, "Reloading", "acknowledged at the click, before the round-trip");
  assert.equal(gets(), 2, "the GET is out");
  btn.click();
  assert.equal(gets(), 2, "a second click on the disabled button asks nothing");
  await settle();
  assert.equal(barOf(wrap), null, "the landing took the bar"); assert.equal(bar.isConnected, false, "detached, not hidden");
  assert.deepEqual(cardRows(wrap), ["fileview-bar", "fileview-main"]);
  assert.equal(ctx.text(), PY2); assert.equal(ctx.mtimeNs(), MT2); assert.equal(paints, 2, "one repaint");
  assert.equal(heads(), 1, "no HEAD rode along with the reload");
  assert.ok(allEls(body).every((x) => x.scrolled === 0), "nothing scrolled into view");
});

test("changed on disk: a reload another ask ran (the seam's reload(): the Comments panel's poll) clears the bar when its landing brings the moved mtime; a landing under the SAME mtime (a GET that was out before the write) keeps it, and the bar's own Reload then clears it", async (t) => {
  const { wrap, ctx } = await open(APP, t);
  disk[APP] = { bytes: PY2, type: TEXT, mtimeNs: MT2 };
  focusWindow(); await settle();
  assert.equal(readBar(wrap).text, CHANGED);
  ctx.reload(); await settle();                            // the panel's poll saw the move too and asked its own reload
  assert.equal(barOf(wrap), null, "the poll's landing clears it: the later landing rules"); assert.equal(ctx.mtimeNs(), MT2);
  // a GET out before the write: its headers say MT2; the write moves the file to MT3; the focus HEAD sees MT3 and the bar
  // goes up under MT2; the old GET then lands MT2, the same mtime: the moved file is still not what shows, the bar stands
  const slow = heldText(PY2);
  disk[APP] = { bytes: PY2, type: TEXT, mtimeNs: MT2, text: slow.text };
  ctx.reload(); await settle();
  disk[APP] = { bytes: PY3, type: TEXT, mtimeNs: MT3 };
  focusWindow(); await settle();
  assert.equal(readBar(wrap).text, CHANGED, "the HEAD saw the newer write");
  slow.release(); await settle();
  assert.equal(ctx.mtimeNs(), MT2, "the older GET landed its own bytes");
  assert.equal(readBar(wrap).text, CHANGED, "under the same mtime the bar stands");
  assert.equal(readBar(wrap).disabled, false, "its button untouched: this was not its ask");
  reloadButton(wrap).click(); await settle();
  assert.equal(barOf(wrap), null); assert.equal(ctx.text(), PY3); assert.equal(ctx.mtimeNs(), MT3);
});

test("changed on disk: while editing no HEAD runs and the editor's entry takes the bar with the other notices; Cancel brings the bar back at once with no HEAD and hands the keyboard to the body, and the probe asks again on the next focus; after the close no event sends anything", async (t) => {
  visibleAfter(t);
  const { fv, wrap, ctx, body } = await open(APP, t);
  disk[APP] = { bytes: PY2, type: TEXT, mtimeNs: MT2 };
  focusWindow(); await settle();
  assert.equal(readBar(wrap).text, CHANGED);
  const acts = wrap.querySelector(".fileview-acts")!;
  acts.querySelectorAll("button").find((x) => x.textContent === "Edit")!.click(); await settle();
  assert.equal(ctx.editing(), true, "the editor is up"); assert.equal(ed.mounted, 1);
  assert.equal(barOf(wrap), null, "the editor's entry took the bar (enterEdit: a notice over the read view goes as the editor takes the body)");
  const n = heads();
  focusWindow(); visibility(false); await settle();
  assert.equal(heads(), n, "editing: the probe stands down (the save's fence has its own Reload)");
  const cancel = acts.querySelectorAll("button").find((x) => x.textContent === "Cancel")!;
  cancel.focus();                                          // a real click focuses the button
  cancel.click(); await settle();
  assert.equal(ctx.editing(), false);
  assert.equal(readBar(wrap).text, CHANGED, "Cancel brings the bar back at once: the file that shows is still the one it was raised under, and the exit is the event (review round 1: the old text came back with no line above it until the next focus)");
  assert.equal(readBar(wrap).disabled, false, "…with its Reload armed");
  assert.equal(heads(), n, "…and without a HEAD: nothing new is known");
  assert.equal(doc.activeElement, body, "the exit's repaint is a paint the reader asked for: the body takes the keyboard from the button the click focused (review round 1: it stayed on the hidden Cancel, and PageDown scrolled nothing)");
  focusWindow(); await settle();
  assert.equal(heads(), n + 1, "the edit over, the probe asks again");
  assert.equal(readBar(wrap).text, CHANGED, "the file still moved: the bar stands (one bar: the HEAD's raise replaced nothing)");
  fv.closeFileView();
  assert.equal(doc.getElementById("romp-fileview"), null);
  const m = heads();
  focusWindow(); visibility(false); await settle();
  assert.equal(heads(), m, "closed: the listeners left with the viewer");
});

test("changed on disk: a picture probes too (a regenerated figure is a change on disk) and its Reload lands the new bytes and clears the bar; a failed open (the 404 pane, no mtime) never probes", async (t) => {
  visibleAfter(t);
  const { fv, wrap, ctx, body } = await open(PLOT, t);
  assert.equal(ctx.mode(), "media");
  disk[PLOT] = { bytes: PNG2, type: "image/png", mtimeNs: MT2 };
  focusWindow(); await settle();
  assert.equal(heads(), 1); assert.equal(readBar(wrap).text, CHANGED);
  const first = img(body)!.src;
  reloadButton(wrap).click(); await settle();
  assert.equal(barOf(wrap), null); assert.equal(ctx.mtimeNs(), MT2); assert.notEqual(img(body)!.src, first, "the new bytes' URL");
  assert.equal(fv.openFileView(ROOT + "/docs/missing.md", SID), true); await settle();
  const wrap2 = doc.getElementById("romp-fileview")!;
  assert.ok(wrap2.querySelector(".fileview-body .fileview-err"), "the 404 pane");
  fetches.length = 0;
  focusWindow(); visibility(false); await settle();
  assert.equal(heads(), 0, "no mtime to compare against: no HEAD");
});

test("changed on disk: the bar's own Reload clears it whatever mtime lands (a HEAD answered after a newer landing had already put the moved file in the body raised it over the file that shows); a Reload that fails leaves the failure pane in the body, the bar standing and its button armed again", async (t) => {
  const { wrap, ctx, body } = await open(APP, t);
  const held = heldHead();
  disk[APP] = { bytes: PY2, type: TEXT, mtimeNs: MT2, headWait: held.wait };
  focusWindow(); await settle();                           // the HEAD is out and will answer MT2
  disk[APP] = { bytes: PY3, type: TEXT, mtimeNs: MT3 };
  ctx.reload(); await settle();                            // the poll's reload lands MT3 first
  assert.equal(ctx.mtimeNs(), MT3); assert.equal(barOf(wrap), null);
  held.release(); await settle();
  assert.equal(readBar(wrap).text, CHANGED, "the stale answer read as a move (a string compare, the panel's contract)");
  reloadButton(wrap).click(); await settle();
  assert.equal(ctx.mtimeNs(), MT3, "the reload brought the same file"); assert.equal(barOf(wrap), null, "its own ask's landing clears the bar");
  assert.equal(paints, 3, "the open, the poll's reload, the bar's");
  disk[APP] = { bytes: PY3, type: TEXT, mtimeNs: MT4 };
  focusWindow(); await settle();
  assert.equal(readBar(wrap).text, CHANGED);
  delete disk[APP];                                        // gone by the time the GET runs
  const btn = reloadButton(wrap);
  btn.click(); await settle();
  assert.ok(body.querySelector(".fileview-err"), "the failure pane says what happened");
  assert.equal(readBar(wrap).text, CHANGED, "the bar stands"); assert.equal(btn.textContent, "Reload"); assert.equal(btn.disabled, false, "armed again: no dead end");
  assert.equal(ctx.mtimeNs(), MT3, "a failed landing lends no mtime"); assert.equal(paints, 3, "and no paint");
});

test("changed on disk: the Reload button holds the keyboard at its click (a click focuses a button), the click's disable drops it to the document's body (the browser's rule), and the landing that removes the bar hands it to the body, so PageDown reads on; a bar another ask's landing clears while a box in the aside holds the keyboard leaves it there; a failed Reload puts it back on the re-armed button", async (t) => {
  const { wrap, ctx, body } = await open(APP, t);
  disk[APP] = { bytes: PY2, type: TEXT, mtimeNs: MT2 };
  focusWindow(); await settle();
  const btn = reloadButton(wrap);
  btn.focus();                                             // a real click focuses the button; the stand-in's click() moves nothing, so the focus is put there first
  assert.equal(doc.activeElement, btn);
  btn.click();
  assert.equal(btn.disabled, true, "acknowledged at the click");
  assert.equal(doc.activeElement, doc.body, "the disable dropped the focus to the document's body at once (the stand-in's disabled setter is the browser's rule), so a read at the landing would find no holder");
  await settle();
  assert.equal(barOf(wrap), null, "the landing took the bar"); assert.equal(ctx.mtimeNs(), MT2);
  assert.equal(doc.activeElement, body, "the body took the keyboard the button held at its click (review round 1: read at the landing, after the disable's drop, the consolidation's hand-over never fired in a browser and PageDown after every Reload scrolled nothing)");
  // another ask's landing (the seam's reload(): the panel's poll) clears the bar while the panel's box holds the keyboard:
  // the button never held it, so nothing moves
  const aside = new El("div"); const box = aside.appendChild(new El("textarea"));
  ctx.aside(aside as unknown as HTMLElement);
  box.focus();
  disk[APP] = { bytes: PY3, type: TEXT, mtimeNs: MT3 };
  focusWindow(); await settle();
  assert.equal(readBar(wrap).text, CHANGED);
  ctx.reload(); await settle();
  assert.equal(barOf(wrap), null, "the poll's landing cleared it"); assert.equal(ctx.mtimeNs(), MT3);
  assert.equal(doc.activeElement, box, "the box kept the keyboard");
  // the bar's own Reload failing: the bar stands with its button armed again, and the keyboard stays on the button
  disk[APP] = { bytes: PY3, type: TEXT, mtimeNs: MT4 };
  focusWindow(); await settle();
  const btn2 = reloadButton(wrap);
  btn2.focus();
  delete disk[APP];                                        // gone by the time the GET runs
  btn2.click(); await settle();
  assert.equal(readBar(wrap).text, CHANGED, "the bar stands"); assert.equal(btn2.disabled, false, "armed again");
  assert.equal(doc.activeElement, btn2, "and the re-armed button takes the keyboard back (the disable had dropped it to the document's body; nothing was removed)");
  // …but only while nothing holds it: the reader who moved to a box during the failed GET's flight keeps the keyboard there (review
  // round 2: the re-armed button took it from the box, the next keystrokes landed on the button and a Space fired Reload again)
  btn2.click();                                            // the click holds the keyboard again (btn2 is the active element); the disable drops it
  assert.equal(doc.activeElement, doc.body);
  box.focus();                                             // mid-flight, the reader clicks into the panel's box and types
  await settle();
  assert.equal(readBar(wrap).text, CHANGED, "the bar stands"); assert.equal(btn2.disabled, false, "armed again");
  assert.equal(doc.activeElement, box, "the box keeps the keyboard (before the fix: the re-armed button took it back, unconditionally on the click's record)");
});

test("changed on disk: the bar's Reload overtaken by another ask during its flight (the seam's reload(): the Comments panel's poll saw the move too, or the deletion): the newer fetch's failed landing re-arms the button, since the overtaken GET reads nothing and never lands (before: the bar stood over the failure pane with its button disabled at Reloading for the rest of the open, no later event re-arming it); the late answer of the overtaken GET changes nothing; a newer fetch's landing that brings the moved file clears the bar as before", async (t) => {
  const { wrap, ctx, body } = await open(APP, t);
  disk[APP] = { bytes: PY2, type: TEXT, mtimeNs: MT2 };
  focusWindow(); await settle();
  assert.equal(readBar(wrap).text, CHANGED);
  const slow = heldText(PY2);
  disk[APP] = { bytes: PY2, type: TEXT, mtimeNs: MT2, text: slow.text };
  const btn = reloadButton(wrap);
  btn.click(); await settle();                             // the bar's ask: its GET's body read waits on the test
  assert.equal(btn.disabled, true); assert.equal(btn.textContent, "Reloading");
  delete disk[APP];                                        // gone by the time the poll asks
  ctx.reload(); await settle();                            // the panel's poll asked its own reload: a newer fetch, and it 404s
  assert.ok(body.querySelector(".fileview-err"), "the newer fetch's failure pane is in the body");
  assert.equal(readBar(wrap).text, CHANGED, "the bar stands over it");
  assert.equal(btn.disabled, false, "…with its button armed again (before the fix: disabled at Reloading, the failure being another fetch's and the bar's own ask never landing)");
  assert.equal(btn.textContent, "Reload");
  assert.equal(ctx.mtimeNs(), MT, "a failed landing lends no mtime");
  slow.release(); await settle();                          // the overtaken GET answers late: it reads nothing and never lands
  assert.ok(body.querySelector(".fileview-err"), "the pane stands"); assert.equal(btn.disabled, false, "the button stays armed"); assert.equal(ctx.mtimeNs(), MT);
  assert.equal(paints, 1, "the open's paint alone: neither failure painted text, and the overtaken answer painted nothing");
  // the way out the re-armed button offers: the file is back, the click lands it and clears the bar
  disk[APP] = { bytes: PY3, type: TEXT, mtimeNs: MT3 };
  btn.click(); await settle();
  assert.equal(barOf(wrap), null, "the bar's own landing clears it"); assert.equal(ctx.text(), PY3); assert.equal(ctx.mtimeNs(), MT3); assert.equal(paints, 2);
  // the other face: the bar's ask overtaken by a poll's reload that lands the moved file clears the bar (the later landing rules, as before)
  disk[APP] = { bytes: PY3, type: TEXT, mtimeNs: MT4 };
  focusWindow(); await settle();
  assert.equal(readBar(wrap).text, CHANGED);
  const slow2 = heldText(PY3);
  disk[APP] = { bytes: PY3, type: TEXT, mtimeNs: MT4, text: slow2.text };
  reloadButton(wrap).click(); await settle();
  disk[APP] = { bytes: PY3, type: TEXT, mtimeNs: MT4 };
  ctx.reload(); await settle();
  assert.equal(barOf(wrap), null, "the newer fetch landed the moved file: the bar goes"); assert.equal(ctx.mtimeNs(), MT4);
  slow2.release(); await settle();
  assert.equal(barOf(wrap), null); assert.equal(ctx.mtimeNs(), MT4, "the late answer changes nothing");
});

// ── the stand-in's projection (ui/test-dom-shim.ts): a node inspects as its primitives, never as the tree ─────────────
test("a stand-in node enumerates its primitives alone, so a failing assertion's dump shows neither parentNode nor childNodes", () => {
  const root = new El("div"); root.className = "row";
  const child = root.appendChild(new El("span")); child.appendChild(new Txt("alpha")); root.appendChild(new Txt("beta"));
  for (const n of [root, child, root.childNodes[1]] as Array<El | Txt>) {
    for (const k of Object.keys(n)) assert.ok(staysEnumerable((n as any)[k]), k + " is enumerable and holds a " + typeof (n as any)[k]);
    const dump = inspect(n, { compact: false, customInspect: false, depth: 1000, maxArrayLength: Infinity, showHidden: false, showProxy: false, sorted: true, getters: true });
    assert.ok(!dump.includes("parentNode") && !dump.includes("childNodes"), "the dump holds no edge: " + dump);
  }
  assert.ok(child.parentNode === root && root.childNodes[0] === child && root.textContent === "alphabeta", "the tree is reachable as before");
  // the file's own Ev hides target and currentTarget the same way (hideEdges(this) at the end of its constructor)
  assertHiddenEvent(new Ev("click"), root, child);
});
