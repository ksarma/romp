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
// kernel does, and can hold one, fail one on the network or answer it 413. A 404 carries the kernel's one-word cause in
// X-Romp-Reason (the PR review's round 2): `missing` for a file gone from an absolute path, which the bar reads as a deletion,
// and the other causes the route answers 404 for while the file may still exist (a relative path a session move re-aimed, a
// detached remote host) or no header at all (a kernel from before it), which the bar reads as a change. Synthetic fixtures
// only: the notes-api world, placeholder ids, TESTHOST for a remote session's host.
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
  key: string; ctrlKey: boolean; metaKey: boolean; button: number;   // button: a pointer event's, 0 the primary (pressHold reads it)
  constructor(public type: string, init: { key?: string; ctrlKey?: boolean; metaKey?: boolean; button?: number } = {}) {
    this.key = init.key || ""; this.ctrlKey = !!init.ctrlKey; this.metaKey = !!init.metaKey; this.button = init.button ?? 0;
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
// on it (a slow kernel, for the one-in-flight cases); `headFail`: the HEAD fails on the network (the fetch rejects); `get`: the
// status a GET answers instead of 200, with `getBody` as its body (413 for a file grown past the cap between the HEAD that saw
// the move and the Reload's GET; the kernel's body names the size, the cap and the resolved path; the Slice 7 review's round 2).
type Served = { bytes: string | Uint8Array; type: string; mtimeNs: string; blob?: () => Blob; text?: () => Promise<string>; head?: number; headWait?: Promise<void>; headFail?: boolean; get?: number; getBody?: string };
const disk: Record<string, Served> = {};
// A path with no entry in `disk` answers 404 as the kernel's route does for a file gone from an absolute path: X-Romp-Reason
// `missing`, the GET's body naming the path. An entry here says the 404 has another cause (the PR review's round 2): the reason
// the header carries (`relative` for a relative path the session's cwd moved from under, `detached` for a remote host with no
// tunnel; null for a kernel from before the header, which sends none) and the GET's own body for it. Cleared at every open.
type Gone = { reason: string | null; body: string };
const gone: Record<string, Gone> = {};
const goneOf = (p: string): Gone => gone[p] || { reason: "missing", body: "no such file: " + p };
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
  // the 404's headers: the kernel's one-word reason alone, when its answer carries one (tests/test_kernel_preview.py and
  // tests/test_kernel_remote_file_relay.py pin the header server-side)
  const g = goneOf(p);
  const headers404 = { get: (h: string) => (h === "X-Romp-Reason" ? g.reason : null) };
  if (method === "HEAD") {
    // the kernel's HEAD /file: the GET's headers and no bytes (tests/test_kernel_preview.py pins the empty body)
    if (f && f.headWait) await f.headWait;
    if (f && f.headFail) throw new TypeError("network gone");
    if (!f) return { ok: false, status: 404, headers: headers404, text: async () => "" };
    if (f.head) return { ok: false, status: f.head, headers, text: async () => "" };
    return { ok: true, status: 200, headers, text: async () => "" };
  }
  if (!f) return { ok: false, status: 404, headers: headers404, text: async () => g.body };
  if (f.get) return { ok: false, status: f.get, headers, text: async () => f.getBody || "" };   // the kernel's refusal: its status and its words, no bytes
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
const MT5 = "1757145600000000010";

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
async function open(p: string, t: TestContext, sid = SID): Promise<Open> {
  const fv = await mod();
  disk[PLOT] = { bytes: PNG1, type: "image/png", mtimeNs: MT };
  disk[FIG] = { bytes: SVG1, type: "image/svg+xml", mtimeNs: MT };
  disk[APP] = { bytes: PY, type: "text/plain; charset=utf-8", mtimeNs: MT };
  for (const k of Object.keys(gone)) delete gone[k];
  posted.length = 0; fetches.length = 0; paints = 0; seam = null;
  assert.equal(fv.openFileView(p, sid), true, "the open happened");
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

// An svg's picture loads from its /file address, which carries the landed mtime as a version key: while the page still holds the
// picture of an address it has loaded, a new <img> at that address shows it and asks for nothing, so the reload's picture needs
// the new mtime's address.
const figAt = (key: string) => "/file?path=" + encodeURIComponent(FIG) + "&sid=" + SID + "&v=" + key;

test("reload on an svg picture: the picture's /file address follows the landed mtime, a new <img> at the new mtime's address, and no object URL is released at the reload or the close", async (t) => {
  const revoked = watchRevokes(t);
  const { fv, ctx, body } = await open(FIG, t);
  const first = img(body)!;
  assert.equal(first.src, figAt(MT), "the open's picture: the /file address at the landed mtime; got " + first.src);
  disk[FIG] = { bytes: SVG2, type: "image/svg+xml", mtimeNs: MT2 };   // a session regenerated the figure
  ctx.reload();
  await settle();
  const second = img(body)!;
  assert.notEqual(second, first, "the reload built a new picture");
  assert.equal(second.src, figAt(MT2), "the reload's picture: the address at the new mtime; got " + second.src);
  assert.equal(ctx.mtimeNs(), MT2);
  assert.equal(body.querySelectorAll("img").length, 1, "the reload replaced the picture, it did not stack one");
  fv.closeFileView();
  assert.deepEqual(revoked, [], "no object URL was made, so none is released");
});

test("an svg answer that carries no mtime: each landing's picture takes a key of its own, so a reload still shows the new picture", async (t) => {
  const { ctx, body } = await open(FIG, t);
  disk[FIG] = { bytes: SVG2, type: "image/svg+xml", mtimeNs: "" };   // a kernel that sends no X-Romp-Mtime-Ns
  ctx.reload();
  await settle();
  const k1 = img(body)!.src;
  disk[FIG] = { bytes: SVG3, type: "image/svg+xml", mtimeNs: "" };
  ctx.reload();
  await settle();
  const k2 = img(body)!.src;
  const keyOf = (src: string) => (src.startsWith(figAt("")) ? src.slice(figAt("").length) : null);
  assert.ok(/^\d+$/.test(keyOf(k1) ?? "") && /^\d+$/.test(keyOf(k2) ?? ""), "the /file address with a numeric key: " + k1 + " then " + k2);
  assert.notEqual(k2, k1, "a key per landing");
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
  assert.equal(barOf(wrap)!.getAttribute("role"), "status", "a polite live region: the bar is raised with no gesture of the reader's, so assistive technology hears it (the PR review's round 1)");
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
  acts.querySelectorAll("button").find((x) => x.textContent === "Edit" || x.getAttribute("aria-label") === "Edit")!.click(); await settle();
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
  const before = paints;
  assert.equal(fv.openFileView(ROOT + "/docs/missing.md", SID), true); await settle();
  const wrap2 = doc.getElementById("romp-fileview")!;
  assert.ok(wrap2.querySelector(".fileview-body .fileview-err"), "the 404 pane");
  assert.equal(paints, before + 1, "a first open's failure is a paint (Slice 7 of plans/markdown-viewer.md, item 3)");
  assert.equal(seam!.error(), "no such file: " + ROOT + "/docs/missing.md", "error() the pane's words"); assert.equal(seam!.text(), null);
  fetches.length = 0;
  focusWindow(); visibility(false); await settle();
  assert.equal(heads(), 0, "no mtime to compare against: no HEAD");
});

test("changed on disk (PR review round 1): a HEAD answering 404 with the kernel's reason `missing` (the file deleted from its absolute path; the reason since the PR review's round 2) raises the bar with the deletion's words, Deleted on disk., not the change's (before the fix: a deletion read as a move and the bar said Changed on disk.); its Reload paints the 404 pane in the body with the bar standing and its button re-armed, under the one-bar rule as before; the file back on disk, Reload lands it and its own ask clears the bar", async (t) => {
  const { wrap, ctx, body } = await open(APP, t);
  delete disk[APP];                                            // a session removed the file
  focusWindow(); await settle();
  assert.equal(heads(), 1, "one HEAD for the focus");
  let b = readBar(wrap);
  assert.equal(b.text, "Deleted on disk.", "the deletion's words (before the fix: " + CHANGED + ")");
  assert.equal(b.button, "Reload", "and its one button"); assert.equal(b.disabled, false);
  assert.equal(barOf(wrap)!.getAttribute("role"), "status");
  assert.equal(ctx.text(), PY, "the body shows the text the reader has: the probe fetched no bytes"); assert.equal(gets(), 1);
  focusWindow(); await settle();
  assert.equal(heads(), 2); assert.deepEqual(readBar(wrap), b, "one bar: a second answer while it stands replaces nothing");
  // Reload: the GET meets the 404, the pane is the body, the bar stands with its button armed again (the failed own ask's re-arm)
  reloadButton(wrap).click();
  assert.equal(gets(), 2, "the GET is out"); await settle();
  const pane = body.querySelector(".fileview-err");
  assert.ok(pane, "the 404 pane is in the body");
  assert.match(pane!.textContent, /no such file/, "the kernel's words for a missing file");
  assert.equal(body.querySelectorAll("button").length, 0, "no Download offer: the file is not there");
  assert.equal(paints, 2, "the pane's paint fired the hooks (Slice 7 of plans/markdown-viewer.md, item 3; before: no paint, and the Comments panel's wait ran to its deadline)");
  assert.equal(ctx.error(), "no such file: " + APP, "error() is the pane's words"); assert.equal(ctx.text(), PY, "text() the last landing's");
  b = readBar(wrap);
  assert.equal(b.text, "Deleted on disk.", "the bar stands over the pane"); assert.equal(b.button, "Reload"); assert.equal(b.disabled, false, "its button re-armed: the bar is no dead end");
  // the file back on disk (a session wrote it again): the bar's own Reload lands it and clears the bar
  disk[APP] = { bytes: PY2, type: TEXT, mtimeNs: MT2 };
  reloadButton(wrap).click(); await settle();
  assert.equal(barOf(wrap), null, "the own ask's landing clears the bar"); assert.equal(ctx.text(), PY2); assert.equal(ctx.mtimeNs(), MT2);
  assert.equal(body.querySelector(".fileview-err"), null, "the pane went with the landing");
  assert.equal(paints, 3, "the landing's paint"); assert.equal(ctx.error(), null, "a text view again: error() null");
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
  assert.equal(ctx.mtimeNs(), MT3, "a failed landing lends no mtime"); assert.equal(paints, 4, "and the pane's paint (Slice 7 of plans/markdown-viewer.md, item 3: a failed reload fires the hooks; before: no paint)");
  assert.equal(ctx.error(), "no such file: " + APP, "error() the pane's words"); assert.equal(ctx.text(), PY3, "text() the last landing's");
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
  assert.equal(paints, 2, "the open's paint and the newer fetch's failure pane (Slice 7 of plans/markdown-viewer.md, item 3): the overtaken answer painted nothing");
  assert.equal(ctx.error(), "no such file: " + APP, "error() the newer fetch's words");
  // the way out the re-armed button offers: the file is back, the click lands it and clears the bar
  disk[APP] = { bytes: PY3, type: TEXT, mtimeNs: MT3 };
  btn.click(); await settle();
  assert.equal(barOf(wrap), null, "the bar's own landing clears it"); assert.equal(ctx.text(), PY3); assert.equal(ctx.mtimeNs(), MT3); assert.equal(paints, 3); assert.equal(ctx.error(), null);
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

// ── review round 3 ───────────────────────────────────────────────────────────────────────────────────────────────────
test("changed on disk (review round 3): a failed Reload re-arms its button AFTER the failure pane's paint, so a keyboard the reader put on the old body's content during the flight, which that paint removes, goes back on the re-armed button (before: the re-arm ran first, read the content's element as the holder and stood down, and the paint's removal left the keyboard on the document's body, where PageDown, Space and Enter did nothing until a click)", async (t) => {
  const { wrap, ctx, body } = await open(APP, t);
  disk[APP] = { bytes: PY2, type: TEXT, mtimeNs: MT2 };
  focusWindow(); await settle();
  const btn = reloadButton(wrap);
  btn.focus();
  const slow = heldText("");                                 // the bar's GET: its body read waits on the test, then fails
  disk[APP] = { bytes: "", type: TEXT, mtimeNs: MT2, text: slow.text };
  btn.click();
  assert.equal(btn.disabled, true); assert.equal(doc.activeElement, doc.body, "the disable dropped the click's keyboard");
  const inner = body.querySelector("code.hljs")!;           // an element of the old body's content (a link, a fold's summary): the reader clicks or tabs to it during the flight
  inner.focus();
  assert.equal(doc.activeElement, inner, "the content holds the keyboard mid-flight");
  slow.fail("network gone"); await settle();
  assert.ok(body.querySelector(".fileview-err"), "the failure pane replaced the content");
  assert.equal(ctx.error(), "network gone", "error() is the message alone (Slice 7 of plans/markdown-viewer.md, item 3): the hint naming the path is the pane's, since this message does not name it");
  assert.equal(body.querySelector(".fileview-err")!.textContent, "network gone" + APP, "the pane the person reads: the message, then the path as its hint");
  assert.equal(inner.isConnected, false, "…and the element the reader held is gone with it");
  assert.equal(readBar(wrap).text, CHANGED, "the bar stands"); assert.equal(btn.disabled, false, "re-armed");
  assert.equal(doc.activeElement, btn, "the re-armed button has the keyboard: nothing held it once the paint removed the holder (before the fix: the document's body)");
  // the round 2 rule stands: a box the reader moved to during the flight keeps it, since the paint does not remove the aside
  const aside = new El("div"); const box = aside.appendChild(new El("textarea"));
  disk[APP] = { bytes: PY2, type: TEXT, mtimeNs: MT2 };
  btn.click(); await settle();                               // the file is back: the landing clears the bar
  assert.equal(barOf(wrap), null);
  disk[APP] = { bytes: PY3, type: TEXT, mtimeNs: MT3 };
  focusWindow(); await settle();
  const btn2 = reloadButton(wrap); btn2.focus();
  const slow2 = heldText("");
  disk[APP] = { bytes: "", type: TEXT, mtimeNs: MT3, text: slow2.text };
  btn2.click();
  wrap.appendChild(aside); box.focus();
  slow2.fail("network gone"); await settle();
  assert.equal(btn2.disabled, false, "re-armed");
  assert.equal(doc.activeElement, box, "the box keeps the keyboard");
});

test("changed on disk (review round 3): a HEAD answered while the pointer is pressed on the body parks the bar's raise until the release (a drag begun on the body in a Files frame that did not hold the page's focus is itself the window focus that ran the HEAD, and the bar is a card row above the body: raised mid-press it moved the body under the pointer and the drag's selection ended on other text); the release raises it; a landing during the press stands the parked raise down; a press on the bar holds nothing; and (review round 4) a press in the Comments ASIDE, the other column of the row the bar is inserted above, parks the raise too (before: held on the body alone, a press on a card's head or a drag in the reply box had the bar land under it, the click lost)", async (t) => {
  const { wrap, ctx, body } = await open(APP, t);
  disk[APP] = { bytes: PY2, type: TEXT, mtimeNs: MT2 };
  body.dispatchEvent(new Ev("pointerdown", { button: 0 }));   // the drag's press on the body
  focusWindow(); await settle();                               // the focus grant's HEAD: the file moved
  assert.equal(heads(), 1, "the HEAD ran");
  assert.equal(barOf(wrap), null, "no bar while the pointer is down (before the fix: raised at once, under the press)");
  win.dispatchEvent(new Event("pointerup"));                    // the release: the parked raise goes on a zero timer
  await new Promise<void>((r) => setTimeout(r, 2)); await settle();
  assert.equal(readBar(wrap).text, CHANGED, "raised at the release");
  assert.equal(readBar(wrap).disabled, false); assert.equal(heads(), 1, "no second HEAD");
  reloadButton(wrap).click(); await settle();
  assert.equal(barOf(wrap), null); assert.equal(ctx.mtimeNs(), MT2);
  // a landing during the press (the panel's poll reloaded the moved file, parked by the same press and run first at the release,
  // the raise waiting for its settle: parkedLanding, the review's round 5): the raise's guards re-run after it and find the file
  // that shows is the moved one
  disk[APP] = { bytes: PY3, type: TEXT, mtimeNs: MT3 };
  body.dispatchEvent(new Ev("pointerdown", { button: 0 }));
  focusWindow(); await settle();
  assert.equal(barOf(wrap), null);
  ctx.reload(); await settle();                                // parked too (the landing's own hold)
  assert.equal(ctx.mtimeNs(), MT2, "the landing waits for the release as every landing does");
  // the release order (the review's round 5): both holds listen for the press in the capture phase and `main` is the body's
  // ancestor, so the row's hold heard it first, installed its release listener first, and its parked run went on the zero timer
  // first; the raise then inserted a bar over the old mtime, which the landing's settle removed a task later (a flash, and a
  // press on a bar that then went). The raise now waits for the parked landing's settle, so no bar is inserted at the release.
  // Counted at the card's insertBefore, the one call noteBar makes (the bar carries its id before it).
  const card = wrap.querySelector(".fileview")!; const ins = card.insertBefore.bind(card); let raised = 0;
  card.insertBefore = ((n: El | Txt, ref: El | Txt | null) => { if (n instanceof El && n.id === "fileview-save-err") raised++; return ins(n, ref); }) as unknown as typeof card.insertBefore;
  win.dispatchEvent(new Event("pointerup"));
  await new Promise<void>((r) => setTimeout(r, 2)); await settle();
  assert.equal(ctx.mtimeNs(), MT3, "the landing ran at the release");
  assert.equal(barOf(wrap), null, "…and the raise stood down: the moved file is what shows");
  assert.equal(raised, 0, "the landing ran first: no bar was inserted and removed at the release (before the fix: one, over the old mtime, gone a task later)");
  delete (card as any).insertBefore;
  // a press on the bar (the title and actions row ABOVE the notice, which a raise never moves) holds nothing: a HEAD answered
  // under it raises at once
  disk[APP] = { bytes: PY3, type: TEXT, mtimeNs: MT4 };
  wrap.querySelector(".fileview-bar")!.dispatchEvent(new Ev("pointerdown", { button: 0 }));
  focusWindow(); await settle();
  assert.equal(readBar(wrap).text, CHANGED, "a press on the bar is over nothing the raise moves: raised at once");
  win.dispatchEvent(new Event("pointerup"));
  reloadButton(wrap).click(); await settle();
  assert.equal(barOf(wrap), null); assert.equal(ctx.mtimeNs(), MT4);
  // a press in the ASIDE (the Comments panel's column, mounted beside the body in the row the bar is inserted above; a card's
  // head, Resolve, the reply box): the raise moves that column too, so the press is held and the release raises (the review's
  // round 4: held on the body alone, the bar landed under the press and the card head moved out from under the pointer)
  const aside = new El("div"); const head = aside.appendChild(new El("div")); head.className = "fc-card-head";
  ctx.aside(aside as unknown as HTMLElement);
  assert.equal(wrap.querySelector(".fileview-main")!.contains(aside), true, "the aside is mounted in the body row");
  disk[APP] = { bytes: PY2, type: TEXT, mtimeNs: MT5 };
  head.dispatchEvent(new Ev("pointerdown", { button: 0 }));   // the press on a card's head
  focusWindow(); await settle();
  assert.equal(heads(), 4, "the HEAD ran");
  assert.equal(barOf(wrap), null, "no bar while the pointer is down in the aside (before the fix: raised at once, and the aside dropped under the press)");
  win.dispatchEvent(new Event("pointerup"));
  await new Promise<void>((r) => setTimeout(r, 2)); await settle();
  assert.equal(readBar(wrap).text, CHANGED, "raised at the release");
  assert.equal(heads(), 4, "no second HEAD");
  win.dispatchEvent(new Event("pointerup"));
});

test("changed on disk (review round 6): a landing parked under the same press that brings a mtime NEWER than the one the HEAD saw (a second write between the HEAD's answer and the poll's GET, all under one drag) stands the raise down, since the body no longer shows the file the HEAD compared against (before the fix: the release guard read the landed mtime as moved against the HEAD's answer and raised a false bar over the newest file, standing until Reload); the trade, recorded in the plan: a parked landing that brought an OLDER mtime than the HEAD saw (a GET served before the write the HEAD saw) stands the raise down too, and the next focus HEAD raises the bar over the file that shows", async (t) => {
  const { wrap, ctx, body } = await open(APP, t);
  // the HEAD sees MT2 under the press; a second write lands MT3 under the same press
  disk[APP] = { bytes: PY2, type: TEXT, mtimeNs: MT2 };
  body.dispatchEvent(new Ev("pointerdown", { button: 0 }));   // the drag's press on the body
  focusWindow(); await settle();                               // the focus grant's HEAD: the file moved to MT2
  assert.equal(heads(), 1, "the HEAD ran"); assert.equal(barOf(wrap), null, "no bar while the pointer is down");
  disk[APP] = { bytes: PY3, type: TEXT, mtimeNs: MT3 };       // the second write, after the HEAD's answer
  ctx.reload(); await settle();                                // the poll's GET brings MT3, parked under the same press
  assert.equal(ctx.mtimeNs(), MT, "the landing waits for the release");
  const card = wrap.querySelector(".fileview")!; const ins = card.insertBefore.bind(card); let raised = 0;
  card.insertBefore = ((n: El | Txt, ref: El | Txt | null) => { if (n instanceof El && n.id === "fileview-save-err") raised++; return ins(n, ref); }) as unknown as typeof card.insertBefore;
  win.dispatchEvent(new Event("pointerup"));
  await new Promise<void>((r) => setTimeout(r, 2)); await settle();
  assert.equal(ctx.mtimeNs(), MT3, "the landing ran at the release and the body shows the newest file");
  assert.equal(barOf(wrap), null, "no bar over the newest file (before the fix: `Changed on disk.` with Reload, MT3 read as moved against the HEAD's MT2)");
  assert.equal(raised, 0, "and none was inserted at the release");
  delete (card as any).insertBefore;
  focusWindow(); await settle();                               // the next HEAD sees the mtime the body shows
  assert.equal(heads(), 2); assert.equal(barOf(wrap), null, "the next HEAD finds nothing moved");
  // the trade: a GET served under MT4 and parked, then a write to MT5 the HEAD sees under the same press: the landing brings MT4 and the
  // raise stands down (the body no longer shows MT3, the file the HEAD compared against); the next focus HEAD finds MT5 against the MT4
  // that shows and raises
  body.dispatchEvent(new Ev("pointerdown", { button: 0 }));
  disk[APP] = { bytes: PY2, type: TEXT, mtimeNs: MT4 };
  ctx.reload(); await settle();                                // the GET's headers read MT4; its landing parks under the press
  assert.equal(ctx.mtimeNs(), MT3, "parked");
  disk[APP] = { bytes: PY3, type: TEXT, mtimeNs: MT5 };       // the write after the GET was served
  focusWindow(); await settle();                               // the HEAD sees MT5 against MT3; the raise parks
  assert.equal(heads(), 3); assert.equal(barOf(wrap), null, "no bar while the pointer is down");
  win.dispatchEvent(new Event("pointerup"));
  await new Promise<void>((r) => setTimeout(r, 2)); await settle();
  assert.equal(ctx.mtimeNs(), MT4, "the parked landing brought the older file");
  assert.equal(barOf(wrap), null, "the raise stood down: a landing since the HEAD's compare, whatever it brought (the trade)");
  focusWindow(); await settle();
  assert.equal(heads(), 4);
  assert.equal(readBar(wrap).text, CHANGED, "the next focus HEAD finds MT5 against the MT4 that shows and raises the bar at once");
  reloadButton(wrap).click(); await settle();
  assert.equal(barOf(wrap), null); assert.equal(ctx.mtimeNs(), MT5);
});

test("changed on disk (PR review round 2): a HEAD answering 404 says Deleted on disk. only when the kernel's X-Romp-Reason reads `missing`; a 404 with another reason, `relative` for a relative path the session's cwd moved from under, `detached` for a remote session whose host is no longer attached (the HEAD went to the relay's URL), or with no reason header at all (a kernel from before the header) raises the bar with the change's words, Changed on disk., its Reload painting the kernel's own pane for what the GET answers, the bar standing with its button re-armed (before the fix: every 404 read as a deletion, and the bar said Deleted on disk. over a file still on disk)", async (t) => {
  // a relative path, joined to the session's cwd at the kernel: the session moved, and the kernel says so
  const REL = "src/app.py";
  disk[REL] = { bytes: PY, type: TEXT, mtimeNs: MT };
  const rel = await open(REL, t);
  delete disk[REL]; gone[REL] = { reason: "relative", body: "not found: /repo/elsewhere/src/app.py" };
  focusWindow(); await settle();
  assert.equal(heads(), 1, "one HEAD for the focus");
  let b = readBar(rel.wrap);
  assert.equal(b.text, CHANGED, "a relative path's 404 is not a deletion: the file may stand at the old cwd (before the fix: Deleted on disk.)");
  assert.equal(b.button, "Reload"); assert.equal(b.disabled, false);
  assert.equal(rel.ctx.text(), PY, "the body shows the text the reader has");
  reloadButton(rel.wrap).click(); await settle();
  const pane = rel.body.querySelector(".fileview-err");
  assert.ok(pane, "Reload paints the kernel's own pane");
  assert.match(pane!.textContent, /not found: \/repo\/elsewhere\/src\/app\.py/, "…with the path the kernel resolved");
  b = readBar(rel.wrap);
  assert.equal(b.text, CHANGED, "the bar stands over the pane with the same words"); assert.equal(b.disabled, false, "its button re-armed");
  rel.fv.closeFileView();
  // a remote session (a host-prefixed sid): the HEAD goes to the relay, and a detached host's 404 says so
  const remote = await open(APP, t, "TESTHOST:" + SID);
  assert.ok(fetches[0].startsWith("GET /remote/TESTHOST/file?"), "the open fetched through the relay (read " + fetches[0] + ")");
  delete disk[APP]; gone[APP] = { reason: "detached", body: "no attached host 'TESTHOST'" };
  focusWindow(); await settle();
  assert.equal(heads(), 1);
  assert.ok(fetches.some((f) => f.startsWith("HEAD /remote/TESTHOST/file?")), "the HEAD went to the relay's URL");
  assert.equal(readBar(remote.wrap).text, CHANGED, "a detached host's 404 is not a deletion: the remote's disk was not consulted (before the fix: Deleted on disk.)");
  reloadButton(remote.wrap).click(); await settle();
  assert.match(remote.body.querySelector(".fileview-err")!.textContent, /no attached host/, "Reload paints the relay's own answer");
  assert.equal(readBar(remote.wrap).text, CHANGED); assert.equal(readBar(remote.wrap).disabled, false);
  remote.fv.closeFileView();
  // a kernel from before the header: its 404 carries no reason, and the bar keeps to the change's words
  const old = await open(APP, t);
  delete disk[APP]; gone[APP] = { reason: null, body: "not found: " + APP };
  focusWindow(); await settle();
  assert.equal(heads(), 1);
  assert.equal(readBar(old.wrap).text, CHANGED, "no reason header: the cause is unknown, so the words claim no deletion (before the fix: Deleted on disk.)");
  old.fv.closeFileView();
  // and the one cause that IS a deletion, beside them: the words the round-1 case pins
  const goneFor = await open(APP, t);
  delete disk[APP];                                            // no entry in `gone`: the kernel's `missing`
  focusWindow(); await settle();
  assert.equal(readBar(goneFor.wrap).text, "Deleted on disk.", "`missing` alone says the file is gone");
});

test("changed on disk (PR review round 2): the deletion's words survive the editor: with the Deleted on disk. bar up, Edit takes it with the other notices and Cancel brings it back reading Deleted on disk., not Changed on disk., its Reload armed, no HEAD sent and the keyboard on the body (the words are kept on the bar's record for the exit's re-raise; red with the re-raise reading CHANGED_ON_DISK in place of the record's words); its Reload then paints the 404 pane with the bar standing", async (t) => {
  visibleAfter(t);
  const { wrap, ctx, body } = await open(APP, t);
  delete disk[APP];                                            // a session removed the file: the kernel's 404 says `missing`
  focusWindow(); await settle();
  assert.equal(readBar(wrap).text, "Deleted on disk.", "the deletion's words");
  const acts = wrap.querySelector(".fileview-acts")!;
  const mounted = ed.mounted;
  acts.querySelectorAll("button").find((x) => x.textContent === "Edit" || x.getAttribute("aria-label") === "Edit")!.click(); await settle();
  assert.equal(ctx.editing(), true, "the editor is up over the text the reader has"); assert.equal(ed.mounted, mounted + 1);
  assert.equal(barOf(wrap), null, "the editor's entry took the bar with the other notices");
  const n = heads();
  const cancel = acts.querySelectorAll("button").find((x) => x.textContent === "Cancel")!;
  cancel.focus();                                          // a real click focuses the button
  cancel.click(); await settle();
  assert.equal(ctx.editing(), false, "Cancel left the editor");
  const b = readBar(wrap);
  assert.equal(b.text, "Deleted on disk.", "the exit re-raises the bar with the words it had (a mutation to raiseDiskBar(CHANGED_ON_DISK) reads Changed on disk. here)");
  assert.equal(b.button, "Reload"); assert.equal(b.disabled, false, "…with its Reload armed");
  assert.equal(barOf(wrap)!.getAttribute("role"), "status");
  assert.equal(heads(), n, "…and without a HEAD: nothing new is known");
  assert.equal(doc.activeElement, body, "the exit's repaint hands the keyboard to the body");
  assert.equal(ctx.text(), PY, "the old text shows again under the bar");
  reloadButton(wrap).click(); await settle();
  assert.ok(body.querySelector(".fileview-err"), "Reload paints the 404 pane");
  assert.equal(readBar(wrap).text, "Deleted on disk.", "the bar stands over it"); assert.equal(readBar(wrap).disabled, false);
});

test("changed on disk (the Slice 7 review's round 2; the brief's item 3 named the failed Reload's 413 beside its 404, and two rounds left the scene open): a Reload whose GET answers 413 (the file grew past the cap between the HEAD that saw the move and the click) paints the too-large pane in the body with the kernel's words and a Download offer (the file exists), fires the paint hooks once at that paint and never again for it, exposes error() with the pane's words while text() and mtimeNs() keep the last landing's, and leaves the bar standing with its button armed again; the seam's own reload (the Comments panel's poll) refused the same way paints the same pane with one paint and sends no HEAD; the file back under the cap lands, clears the bar and the pane, and error() is null again", async (t) => {
  const { wrap, ctx, body } = await open(APP, t);
  assert.equal(paints, 1, "the open's paint");
  disk[APP] = { bytes: PY2, type: TEXT, mtimeNs: MT2 };
  focusWindow(); await settle();
  assert.equal(readBar(wrap).text, CHANGED, "the HEAD saw the move: the bar is up"); assert.equal(paints, 1, "its raise is no paint");
  const TOO_LARGE = "file too large to show: 60 MB, the cap is 8 MB: " + APP;   // the kernel's 413 body: the size, the cap and the resolved path
  disk[APP] = { bytes: "", type: TEXT, mtimeNs: MT2, get: 413, getBody: TOO_LARGE };
  const btn = reloadButton(wrap);
  btn.click();
  assert.equal(btn.disabled, true, "the click disables the button");
  await settle();
  const pane = body.querySelector(".fileview-err")!;
  assert.ok(pane, "the pane says what happened");
  assert.equal(pane.childNodes.filter((x): x is Txt => x instanceof Txt).map((x) => x.textContent).join(""), TOO_LARGE, "the kernel's words, as the person reads them");
  assert.equal(pane.querySelectorAll(".fileview-err-hint").length, 0, "no hint: the words name the path");
  const offers = pane.querySelectorAll("button");
  assert.equal(offers.length, 1, "one offer"); assert.equal(offers[0].textContent, "Download", "the way out: the file exists, the view could not be (a 404 offers none)");
  assert.equal(paints, 2, "the pane's paint fired the hooks once (Slice 7 of plans/markdown-viewer.md, item 3), and nothing else did (red under the mutation that removes the catch's fireRendered())");
  assert.equal(ctx.error(), TOO_LARGE, "error() the pane's words");
  assert.equal(ctx.text(), PY, "text() the last landing's"); assert.equal(ctx.mtimeNs(), MT, "a failed landing lends no mtime");
  assert.equal(readBar(wrap).text, CHANGED, "the bar stands"); assert.equal(btn.textContent, "Reload"); assert.equal(btn.disabled, false, "armed again: no dead end");
  assert.equal(gets(), 2, "the open's GET and the Reload's: the refusal asked no second request");
  // the seam's own reload, the panel's poll: the same pane, one paint, no HEAD, the bar as it was
  const heads0 = heads();
  ctx.reload(); await settle();
  assert.equal(heads(), heads0, "no HEAD: the seam's reload is a GET"); assert.equal(gets(), 3);
  assert.equal(paints, 3, "one paint for the pane");
  assert.equal(ctx.error(), TOO_LARGE, "error() the pane's words again");
  assert.equal(body.querySelector(".fileview-err")!.querySelectorAll("button").length, 1, "the offer again");
  assert.equal(readBar(wrap).text, CHANGED, "the bar stands"); assert.equal(readBar(wrap).disabled, false, "its button armed");
  // the file back under the cap: the bar's Reload lands it and clears the bar and the pane
  disk[APP] = { bytes: PY2, type: TEXT, mtimeNs: MT2 };
  reloadButton(wrap).click(); await settle();
  assert.equal(barOf(wrap), null, "the landing clears the bar"); assert.equal(body.querySelector(".fileview-err"), null, "and the pane");
  assert.equal(ctx.error(), null, "error() null over the text"); assert.equal(ctx.text(), PY2); assert.equal(ctx.mtimeNs(), MT2); assert.equal(paints, 4, "the landing's paint");
});
