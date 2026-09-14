// A figure that failed to load says so beside itself (plans/markdown-viewer.md Slice 7, item 2: "a failed figure shows an
// inline error naming its src"; acceptance "never a blank or bare glyph"). The kernel's answers for a figure that fails (a 404,
// a 415, a 413, a text file named as a figure) all fire the img's `error` event with no status on it, and until this slice
// nothing in the Rendered box listened: the browser drew a wordless broken-image glyph, or nothing. Now the REAL openFileView
// arms one capture-phase `error` listener on the body per open (an img's error does not bubble; armReseat's idiom for `load`)
// that parks a label after the img, `span.fv-figerr[data-fv-figerr]`, naming the fact (FIGURE_FAILED), the authored source
// (pictureDest's rule: `data-fv-src` when the viewer rewrote the src, else `src`) and the alt in parentheses when there is one;
// its twin `load` listener removes the label when a retry lands. The img stays in the DOM with every attribute untouched
// (the panel pairs by img order and `data-fv-src`, the regions layer wraps THE img, the reader's place counts `<img` tags),
// the label is one per img (a second `error`, the chat page's heal retrying, rewrites its text), found by its mark and never
// by its class, placed after an enclosing `<picture>` or the regions layer's `span.fc-imgwrap`, never inside a gate's
// placeholder, and its insertion fires no paint hook. headingWords skips it, so a heading holding a failed figure keeps an
// Outline row reading the alt alone. Here the viewer runs over the seam suite's DOM stand-in (file-view-seam.test.ts, copied:
// node --test runs each file in its own process; this one adds a node's next sibling, `localName`, and a `style` with
// setProperty for the Outline's rows), its dispatch running the capture chain root to target, with the sanitizer's stand-in
// of Slice 7 handing every Rendered paint an empty body and the cases laying the figures by hand. What the browser alone
// can show, a real 404 and a real decode failure, the heal's retry on romp:wsup, the regions layer over a failed figure and
// a comment's highlight in its paragraph, is file-view-figure-error-browser.test.ts's. Before item 2: no element follows
// the img after its error event (red at the first label assertion over a git archive of the base). Synthetic fixtures only:
// the notes-api world, placeholder ids, /repo/notes-api paths.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import { inspect } from "node:util";
import * as fs from "node:fs";
import * as path from "node:path";
import { assertHiddenEvent, hideEdges, sameNodes, staysEnumerable } from "../test-dom-shim";
import type { FileViewActionCtx } from "./file-view";
import { setMdSanitizer } from "./md-sanitize";   // the sanitizer seam the node suites install a stand-in through (Slice 7 of plans/markdown-viewer.md)

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const VIEW = web("file-view.ts");

// ── a DOM stand-in: ancestry, ids, attributes, events with capture and bubbling, a small selector engine ──
class Ev {
  target: El | Txt | null = null;
  currentTarget: El | null = null;
  defaultPrevented = false;
  stopped = false;
  key: string; ctrlKey: boolean; metaKey: boolean;
  deltaY: number; deltaMode: number;
  detail: number;
  constructor(public type: string, init: { key?: string; ctrlKey?: boolean; metaKey?: boolean; deltaY?: number; deltaMode?: number; detail?: number } = {}) {
    this.key = init.key || ""; this.ctrlKey = !!init.ctrlKey; this.metaKey = !!init.metaKey;
    this.deltaY = init.deltaY || 0; this.deltaMode = init.deltaMode || 0; this.detail = init.detail ?? 0;
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
  get nextSibling(): El | Txt | null { const p = this.parentNode; if (!p) return null; const i = p.childNodes.indexOf(this); return i >= 0 ? p.childNodes[i + 1] || null : null; }
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
/** A node's inline style: the properties as written, plus the setProperty the Outline's rows use for their depth variable. */
const styleOf = (): any => { const st: any = {}; st.setProperty = (k: string, v: string) => { st[k] = v; }; st.getPropertyValue = (k: string) => st[k] ?? ""; return st; };
class El {
  nodeType = 1;
  tagName: string;
  parentNode!: El | null;
  childNodes!: Array<El | Txt>;
  attrs = new Map<string, string>();
  listeners: Reg[] = [];
  hidden = false; disabled = false; title = ""; type = ""; value = ""; placeholder = ""; spellcheck = true; wrap = "";
  src = ""; alt = ""; href = ""; download = ""; target = ""; rel = "";
  innerHTML = "";
  style: any = styleOf();
  onclick: ((ev: Ev) => void) | null = null;
  scrolled = 0;
  scrolledWith: unknown = null;
  focused = 0;
  constructor(tag: string) {
    this.tagName = tag.toUpperCase();
    Object.defineProperty(this, "parentNode", { value: null, writable: true, enumerable: false, configurable: true });
    Object.defineProperty(this, "childNodes", { value: [], writable: true, enumerable: false, configurable: true });
    hideEdges(this);
  }
  get localName(): string { return this.tagName.toLowerCase(); }
  get id(): string { return this.attrs.get("id") || ""; }
  set id(v: string) { this.attrs.set("id", v); }
  get isConnected(): boolean { return doc.body.contains(this); }
  get ownerDocument(): typeof doc { return doc; }
  get parentElement(): El | null { return this.parentNode; }
  get children(): El[] { return this.childNodes.filter((c): c is El => c instanceof El); }
  get firstChild(): El | Txt | null { return this.childNodes[0] || null; }
  get nextSibling(): El | Txt | null { const p = this.parentNode; if (!p) return null; const i = p.childNodes.indexOf(this); return i >= 0 ? p.childNodes[i + 1] || null : null; }
  get nextElementSibling(): El | null { for (let n = this.nextSibling; n; n = n.nextSibling) if (n instanceof El) return n; return null; }
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
  set textContent(v: string) { for (const c of this.childNodes) { this.dropFocusIn(c); c.parentNode = null; } this.childNodes.length = 0; if (v !== "") this.appendChild(new Txt(v)); }
  private dropFocusIn(n: El | Txt): void { if (n instanceof El && doc.activeElement && n.contains(doc.activeElement)) doc.activeElement = doc.body; }
  private detach(n: El | Txt): void { const p = n.parentNode; if (p) { const i = p.childNodes.indexOf(n); if (i >= 0) p.childNodes.splice(i, 1); n.parentNode = null; } }
  appendChild<T extends El | Txt>(n: T): T { this.detach(n); this.childNodes.push(n); n.parentNode = this; return n; }
  append(...ns: Array<El | Txt>): void { for (const n of ns) this.appendChild(n); }
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
  focus(): void { this.focused++; doc.activeElement = this; }
  get tabIndex(): number { const v = this.attrs.get("tabindex"); return v === undefined ? -1 : Number(v); }
  set tabIndex(v: number) { this.attrs.set("tabindex", String(v)); }
  blur(): void { if (doc.activeElement === this) doc.activeElement = null; }
  scrollIntoView(arg?: unknown): void { this.scrolled++; this.scrolledWith = arg ?? null; }
  getBoundingClientRect(): { left: number; top: number; right: number; bottom: number; width: number; height: number } { return { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 }; }
  get offsetWidth(): number { return 0; }
}
// the sanitizer's stand-in (md-sanitize.ts setMdSanitizer): an empty body per Rendered paint; the cases lay the figures by hand
const fakeSanitizer = { addHook: () => { /* the hooks are DOMPurify's; the stand-in has none */ }, sanitize: () => new El("body") };
setMdSanitizer(fakeSanitizer as unknown as Parameters<typeof setMdSanitizer>[0]);

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
/** The DOM event path: document capture, ancestors' capture root to target, target and ancestors' bubble, document bubble.
 *  (An img's `error` and `load` do not bubble in a browser; the viewer's listeners are capture-phase and hear them here as there.) */
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
  if (ev.type === "error" || ev.type === "load") return !ev.defaultPrevented;   // neither bubbles: the target's own listeners and the capture chain alone
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
(globalThis as any).location = { protocol: "http:" };
const store = new Map<string, string>();
(globalThis as any).localStorage = {
  getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
  setItem: (k: string, v: string) => { store.set(k, String(v)); },
  removeItem: (k: string) => { store.delete(k); },
};

// ── the kernel's /file, /version and /sessions as the viewer fetches them, and a URL document for the URL viewer ──────
type Served = { bytes: string; type: string; mtimeNs: string };
const disk: Record<string, Served> = {};
const urls: Record<string, string> = {};
(globalThis as any).fetch = async (url: string) => {
  if (url.startsWith("/version")) return { json: async () => ({ fileEditing: true }) };
  if (url.startsWith("/sessions")) return { json: async () => [{ id: SID, name: "api", bg: "#123456", fg: "#ffffff" }] };
  if (urls[url] !== undefined) return new Response(urls[url], { status: 200, headers: { "Content-Type": "text/markdown; charset=utf-8" } });   // the URL viewer streams a real Response's body
  const p = decodeURIComponent((/[?&]path=([^&]*)/.exec(url) || [])[1] || "");
  const f = disk[p];
  const headers = { get: (h: string) => (f ? (h === "Content-Type" ? f.type : h === "X-Romp-Mtime-Ns" ? f.mtimeNs : h === "X-Romp-Text-Utf8" ? "1" : null) : null) };
  if (!f) return { ok: false, status: 404, headers, text: async () => "no such file: " + p };
  return { ok: true, status: 200, headers, text: async () => f.bytes };
};

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ROOT = "/repo/notes-api";
const REPORT = ROOT + "/docs/report.md";
const NOTE_URL = "http://notes-api.test/notes/note.md";
const DOC = "# Report\n\n## Findings\nThe api session cut p95 latency by 40%.\n\n![p95 by day](figs/p95.png)\n";
const MT = "1757145600000000001";
/** The src rewriteFigureSrcs writes for a figure of the report (preview.ts fileUrl): the kernel's /file route, the authored spelling kept in data-fv-src. */
const fileSrc = (rel: string): string => "/file?path=" + encodeURIComponent(ROOT + "/docs/" + rel) + "&sid=" + SID;

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
type Open = { fv: typeof import("./file-view"); ctx: FileViewActionCtx; wrap: El; card: El; body: El; md: El; acts: El; rendered: El; raw: El };
/** The report open Rendered over the stand-in: the viewer's card, its body, the (empty) Rendered box the cases lay figures into, and the view buttons. */
async function open(t: TestContext): Promise<Open> {
  const fv = await mod();
  disk[REPORT] = { bytes: DOC, type: "text/plain; charset=utf-8", mtimeNs: MT };
  posted.length = 0; paints = 0; seam = null;
  store.delete("romp:fileviewFmt");
  assert.equal(fv.openFileView(REPORT, SID), true, "the open happened");
  t.after(() => { fv.closeFileView(); doc.activeElement = null; });
  await settle();
  const wrap = doc.getElementById("romp-fileview")!;
  assert.ok(wrap, "the viewer is up");
  const card = wrap.querySelector(".fileview")!;
  const body = wrap.querySelector(".fileview-body")!;
  const acts = wrap.querySelector(".fileview-acts")!;
  const btn = (label: string) => { const b = acts.querySelectorAll("button").find((x) => x.textContent === label); assert.ok(b, "the " + label + " button"); return b!; };
  const ctx = seam as FileViewActionCtx | null;   // read through a local: the compiler narrowed the module's `seam` to the null written above
  assert.ok(ctx, "the probe action was mounted with the ctx");
  assert.equal(ctx.mode(), "rendered", "the report opened Rendered");
  const md = body.querySelector(".fileview-md")!;
  assert.ok(md, "the Rendered box is up (the stand-in's sanitizer handed it an empty body)");
  return { fv, ctx, wrap, card, body, md, acts, rendered: btn("Rendered"), raw: btn("Raw") };
}
/** An img as the viewer's DOM holds one: the attributes as written (src, alt, and data-fv-src where rewriteFigureSrcs stamped the authored spelling). */
const img = (attrs: Record<string, string>): El => { const i = new El("img"); for (const [k, v] of Object.entries(attrs)) i.setAttribute(k, v); return i; };
const txt = (s: string): Txt => new Txt(s);
const block = (tag: string, ...kids: Array<El | Txt>): El => { const e = new El(tag); e.append(...kids); return e; };
/** Every label under `root`, by the MARK (contract C2: the label is found by `[data-fv-figerr]`, never by its class). */
const labels = (root: El): El[] => root.querySelectorAll("[data-fv-figerr]");
/** The label right after `n`: its next sibling when that carries the mark, else null. */
const labelAfter = (n: El): El | null => { const s = n.nextSibling; return s instanceof El && s.hasAttribute("data-fv-figerr") ? s : null; };
const fire = (n: El, type: "error" | "load"): void => { n.dispatchEvent(new Ev(type)); };
/** The body's capture listeners of `type` (the viewer's error and load listeners are armed there, once per open). */
const captures = (body: El, type: string): number => body.listeners.filter((l) => l.type === type && l.capture).length;

test("a failed figure's label: the img's `error` puts one span.fv-figerr[data-fv-figerr] right after it naming FIGURE_FAILED, the authored src (data-fv-src when the viewer rewrote the src, else src) and the alt in parentheses when there is one; a second error rewrites the one label, never adds; `load` removes it and a later error brings it back; the img stays in place with its attributes and no onerror; renderedImages() still lists the figures; no paint hook fires", async (t) => {
  const { ctx, md } = await open(t);
  const fv = await mod();
  assert.equal(fv.FIGURE_FAILED, "Image failed to load:", "the constant's text (contract C5), without a terminal period so the guide can carry the words");
  const rewritten = img({ src: fileSrc("figs/p95.png"), "data-fv-src": "figs/p95.png", alt: "p95 by day" });   // a relative embed the viewer re-pointed at /file
  const bare = img({ src: "figs/bad.png", alt: "" });                                                       // a figure left as written, with an empty alt
  const p = block("p", txt("Figure one: "), rewritten, txt(" and "), bare);
  md.appendChild(p);
  const painted = paints;
  assert.equal(labels(md).length, 0, "no label before any error");
  fire(rewritten, "error");
  assert.equal(labels(md).length, 1, "the error put ONE label in the box (before item 2: no element followed the img, the browser's mute glyph alone)");
  const l1 = labelAfter(rewritten);
  assert.ok(l1, "the label is the img's next sibling");
  assert.equal(l1!.tagName, "SPAN"); assert.ok(l1!.classes.includes("fv-figerr"), "it wears fv-figerr for the sheets: " + l1!.className);
  assert.equal(l1!.getAttribute("data-fv-figerr"), "", "and carries the mark it is found by");
  assert.equal(l1!.textContent, fv.FIGURE_FAILED + " figs/p95.png (p95 by day)", "the fact, the AUTHORED src (data-fv-src, not the /file URL the viewer wrote into src), and the alt in parentheses");
  sameNodes(p.childNodes, [p.childNodes[0], rewritten, l1!, p.childNodes[3], bare], "the label sits between the img and the text after it; nothing else moved");
  assert.equal(labels(md).some((l) => l.querySelector("button")), false, "no button in the label (contract C2)");
  fire(bare, "error");
  assert.equal(labels(md).length, 2, "one label per img");
  const l2 = labelAfter(bare);
  assert.ok(l2 && l2 !== l1, "the second img's own label, after it");
  assert.equal(l2!.textContent, fv.FIGURE_FAILED + " figs/bad.png", "a figure with no data-fv-src names its src; an empty alt adds no parentheses");
  assert.equal(p.childNodes[p.childNodes.length - 1], l2, "…as the paragraph's last child, after the last img");
  // the chat page's heal retries a failed <img> on every kernel message and on romp:wsup (preview.ts): a second error on the
  // same img finds the label by its mark and rewrites its text, never stacking a second one
  rewritten.setAttribute("alt", "p95 by day, v2");
  fire(rewritten, "error");
  assert.equal(labels(md).length, 2, "a second error on an img adds no second label");
  assert.equal(labelAfter(rewritten), l1, "the same label node stands");
  assert.equal(l1!.textContent, fv.FIGURE_FAILED + " figs/p95.png (p95 by day, v2)", "…its text rewritten from the img as it now reads");
  assert.equal(paints, painted, "the insertion fires no paint hook: the body's nodes stand and the panel's marks are unaffected");
  // the img is untouched: every attribute as written, no onerror (the heal skips an img with one), its place in the paragraph
  assert.equal(rewritten.getAttribute("src"), fileSrc("figs/p95.png")); assert.equal(rewritten.getAttribute("data-fv-src"), "figs/p95.png"); assert.equal(rewritten.getAttribute("alt"), "p95 by day, v2");
  assert.equal((rewritten as any).onerror, undefined, "img.onerror is never set: the img is only listened to (preview.ts's heal skips an img with an onerror property)");
  assert.equal(rewritten.parentNode, p, "the img stands where the author put it (not hidden, not wrapped, not replaced)");
  sameNodes(ctx.renderedImages(), [rewritten, bare], "renderedImages() still lists both figures: the panel's pairing and the regions layer keep their subject");
  // a retry that lands: the load removes the label; the other img's label stands
  fire(rewritten, "load");
  assert.equal(labelAfter(rewritten), null, "the img's load removed its label");
  assert.equal(l1!.parentNode, null, "…the node left the tree");
  assert.equal(labels(md).length, 1, "the other figure's label stands"); assert.equal(labelAfter(bare), l2);
  assert.equal(rewritten.parentNode, p, "the img is still in place after the load");
  fire(rewritten, "load");
  assert.equal(labels(md).length, 1, "a load with no label to remove changes nothing");
  fire(rewritten, "error");
  assert.equal(labels(md).length, 2, "a later failure (a reload of the figure under a new write) puts the label back");
  assert.equal(labelAfter(rewritten)!.textContent, fv.FIGURE_FAILED + " figs/p95.png (p95 by day, v2)");
  fire(bare, "load"); fire(rewritten, "load");
  assert.equal(labels(md).length, 0, "both loaded: no label anywhere");
  assert.equal(paints, painted, "no paint hook through any of it");
});

test("where the label goes and where it does not: found by its mark, never by its class (an authored span.fv-figerr beside the img is left alone and the label goes between them); after an enclosing <picture>, never inside it; after the regions layer's span.fc-imgwrap, so the layer's dispose (the img back in the wrap's place, the wrap removed) keeps it, and a re-wrap finds it again; no label for an img inside a gate's placeholder, nor for an img outside the Rendered box", async (t) => {
  const { body, md } = await open(t);
  const fv = await mod();
  // an author can type the class (the sanitizer keeps `class`): a span.fv-figerr with no mark is the author's, not a label
  const i1 = img({ src: fileSrc("figs/a.png"), "data-fv-src": "figs/a.png", alt: "a" });
  const decoy = block("span", txt("decoy")); decoy.className = "fv-figerr";
  const p1 = block("p", i1, decoy); md.appendChild(p1);
  fire(i1, "error");
  assert.equal(labels(md).length, 1, "one label, found by the mark");
  assert.equal(md.querySelectorAll(".fv-figerr").length, 2, "…beside the author's span of the same class");
  assert.equal(labelAfter(i1)!.textContent, fv.FIGURE_FAILED + " figs/a.png (a)", "the label went in between the img and the author's span");
  assert.equal(decoy.textContent, "decoy", "the author's span was not taken for the label and not rewritten");
  sameNodes(p1.childNodes, [i1, labelAfter(i1)!, decoy], "img, label, the author's span");
  fire(i1, "error");
  assert.equal(labels(md).length, 1, "the second error found the marked label, not the author's span");
  // a <picture>: the img fires once every source failed; the label follows the picture (a span is not a picture's content)
  const source = new El("source"); source.setAttribute("srcset", fileSrc("figs/hero.avif"));
  const i2 = img({ src: fileSrc("figs/hero.png"), "data-fv-src": "figs/hero.png", alt: "hero" });
  const picture = block("picture", source, i2);
  const p2 = block("p", txt("Lead: "), picture, txt(" tail")); md.appendChild(p2);
  fire(i2, "error");
  assert.equal(labels(md).length, 2);
  assert.equal(labelAfter(i2), null, "nothing was put inside the picture after the img");
  sameNodes(picture.childNodes, [source, i2], "the picture's content is untouched");
  const lp = labelAfter(picture);
  assert.ok(lp, "the label is the picture's next sibling"); assert.equal(lp!.textContent, fv.FIGURE_FAILED + " figs/hero.png (hero)");
  fire(i2, "error");
  assert.equal(labels(md).length, 2, "a second error finds the label after the picture");
  fire(i2, "load");
  assert.equal(labelAfter(picture), null, "the load removes it from there"); assert.equal(labels(md).length, 1);
  // the Comments panel open at the error's time: the regions layer has wrapped THE img in span.fc-imgwrap (file-comments-regions.ts)
  // with its overlay after it; the label follows the WRAP, since the layer's dispose puts the img back in the wrap's place and
  // removes the wrap with everything else in it
  const i3 = img({ src: fileSrc("figs/c.png"), "data-fv-src": "figs/c.png", alt: "c" });
  const overlay = new El("div"); overlay.className = "fc-overlay fc-overlay-off";
  const wrapSpan = block("span", i3, overlay); wrapSpan.className = "fc-imgwrap";
  const p3 = block("p", txt("Wrapped: "), wrapSpan, txt(" end")); md.appendChild(p3);
  fire(i3, "error");
  assert.equal(labelAfter(i3), null, "nothing inside the layer's wrap");
  sameNodes(wrapSpan.childNodes, [i3, overlay], "the wrap holds the img and the overlay, as the layer built it");
  const lw = labelAfter(wrapSpan);
  assert.ok(lw, "the label is the wrap's next sibling"); assert.equal(lw!.textContent, fv.FIGURE_FAILED + " figs/c.png (c)");
  // the layer's dispose, as file-comments-regions.ts does it: the img before the wrap, the wrap removed
  p3.insertBefore(i3, wrapSpan); p3.removeChild(wrapSpan);
  assert.equal(labelAfter(i3), lw, "the label survived the dispose as the img's next sibling (inside the wrap it would have left with it)");
  fire(i3, "error");
  assert.equal(p3.querySelectorAll("[data-fv-figerr]").length, 1, "a retry after the panel's close rewrites that label, adding none");
  // the layer built again (the panel reopened): a new wrap before the img, the img moved into it; the label is the wrap's next sibling once more
  const wrap2 = new El("span"); wrap2.className = "fc-imgwrap";
  p3.insertBefore(wrap2, i3); wrap2.appendChild(i3); wrap2.appendChild(new El("div"));
  assert.equal(labelAfter(wrap2), lw, "the label follows the new wrap");
  fire(i3, "error");
  assert.equal(p3.querySelectorAll("[data-fv-figerr]").length, 1, "…and the retry found it there");
  fire(i3, "load");
  assert.equal(p3.querySelectorAll("[data-fv-figerr]").length, 0, "the load removed it from after the wrap");
  // a gated figure (figure-gate.ts): no src, so it never errors; were one dispatched, a label inside the placeholder would leave
  // with restore, so an img under a placeholder gets none
  const gated = img({ "data-fv-gated-src": "https://cdn.example/fig.png", alt: "remote" });
  const gateLabel = new El("span"); gateLabel.className = "fv-gate-label"; gateLabel.setAttribute("data-fv-label", ""); gateLabel.appendChild(txt("Image from cdn.example. Click to load."));
  const gate = block("span", gated, gateLabel); gate.className = "fv-gate"; gate.setAttribute("data-act", "fv-load"); gate.setAttribute("role", "button");
  const p4 = block("p", gate); md.appendChild(p4);
  const before = labels(md).length;
  fire(gated, "error");
  assert.equal(labels(md).length, before, "no label for an img inside a gate's placeholder");
  sameNodes(gate.childNodes, [gated, gateLabel], "the placeholder is untouched");
  // an img outside the Rendered box (the body's own chrome): not a figure of the note
  const stray = img({ src: "/media/romp-swirl-glyph.svg", alt: "" }); body.appendChild(stray);
  fire(stray, "error");
  assert.equal(labelAfter(stray), null, "an img outside .fileview-md gets no label"); assert.equal(labels(md).length, before);
});

test("a heading holding a failed figure keeps an Outline row reading the alt alone (headingWords skips the label's element), while the heading's own textContent carries the label's words", async (t) => {
  const { md, card, acts } = await open(t);
  const fv = await mod();
  const fig = img({ src: fileSrc("figs/missing.png"), "data-fv-src": "figs/missing.png", alt: "Figure 3" });
  const h2 = block("h2", fig, txt(" detail")); h2.id = "md-figure-3-detail";
  md.appendChild(h2);
  fire(fig, "error");
  assert.equal(labelAfter(fig)!.textContent, fv.FIGURE_FAILED + " figs/missing.png (Figure 3)", "the label is in the heading, after the img");
  assert.ok(h2.textContent.includes(fv.FIGURE_FAILED), "the heading's textContent carries the label's words (a text walk that did not skip the mark would too)");
  const outline = acts.querySelectorAll("button").find((b) => b.textContent === "Outline");
  assert.ok(outline, "the Outline button is in the actions row");
  outline!.click();
  const pop = card.querySelector(".fileview-outline");
  assert.ok(pop, "the popover opened (headingsOf reads the box live: the heading laid after the paint counts)");
  const rows = pop!.querySelectorAll(".fileview-outline-row");
  assert.equal(rows.length, 1, "one row for the one heading");
  assert.equal(rows[0].textContent, "Figure 3 detail", "the row reads the figure's alt in place of the picture and the heading's words, and NOT the label (before A4's skip: the label's words between them)");
  assert.equal(rows[0].title, "Figure 3 detail");
  outline!.click();
});

test("the listeners: two capture listeners on the body per open (error and load), armed once at the open and not per paint, so after a Rendered/Raw round trip an error in the NEW box still gets its label; none on the document; both gone after the close (the file-view-outline.test.ts closers idiom)", async (t) => {
  const docBefore = doc.listeners.filter((l) => l.type === "error" || l.type === "load").length;
  const o = await open(t);
  const { fv, body, rendered, raw } = o;
  assert.equal(captures(body, "error"), 1, "one capture-phase error listener on the body (the viewer's; nothing else listens for error there)");
  // the Comments panel arms capture-phase load listeners of its own on the same body (file-comments.ts: the float's hide, the
  // layout's retrim), so the viewer's twin is counted among them and shown by what it does: a load removes a label
  const loadsAtOpen = captures(body, "load");
  assert.ok(loadsAtOpen >= 1, "at least one capture-phase load listener on the body: " + loadsAtOpen);
  assert.equal(doc.listeners.filter((l) => l.type === "error" || l.type === "load").length, docBefore, "none on the document: the viewer's, not the page's");
  raw.click();
  assert.equal(o.ctx.mode(), "raw", "the Raw view");
  rendered.click();
  assert.equal(o.ctx.mode(), "rendered", "and back");
  const md2 = body.querySelector(".fileview-md")!;
  assert.ok(md2 && md2 !== o.md, "a new Rendered box after the round trip");
  assert.equal(captures(body, "error"), 1, "still the one listener: installed per open, not per paint");
  assert.equal(captures(body, "load"), loadsAtOpen, "no load listener added by the paints either");
  const late = img({ src: fileSrc("figs/late.png"), "data-fv-src": "figs/late.png", alt: "late" });
  const stays = img({ src: fileSrc("figs/stays.png"), "data-fv-src": "figs/stays.png", alt: "stays" });
  md2.appendChild(block("p", late, stays));
  fire(late, "error");
  assert.equal(labelAfter(late)!.textContent, fv.FIGURE_FAILED + " figs/late.png (late)", "the listener hears an error in the new box");
  fire(late, "load");
  assert.equal(labelAfter(late), null, "and the load twin hears a load there (the viewer's own among the body's load listeners)");
  fire(stays, "error");
  const kept = labelAfter(stays)!;
  assert.ok(kept, "a label standing at the close");
  fv.closeFileView();
  assert.equal(doc.getElementById("romp-fileview"), null, "the viewer is closed");
  assert.equal(captures(body, "error"), 0, "the close dropped the error listener (ctx.onClose)");
  assert.ok(captures(body, "load") < loadsAtOpen, "…and the load twin (the count fell; the panel's own body listeners are the panel's to drop, and the check below is the viewer's)");
  assert.equal(doc.listeners.filter((l) => l.type === "error" || l.type === "load").length, docBefore, "the document's listeners are as before the open");
  // the dropped listeners hear nothing: an error on a figure of the old body adds no label, and a load removes none
  const orphan = img({ src: fileSrc("figs/orphan.png"), "data-fv-src": "figs/orphan.png", alt: "orphan" });
  md2.appendChild(block("p", orphan));
  fire(orphan, "error");
  assert.equal(labelAfter(orphan), null, "no listener, no label");
  fire(stays, "load");
  assert.equal(labelAfter(stays), kept, "no listener, the standing label is not removed");
});

test("the URL viewer arms the same two listeners on its body: a figure of a URL document that fails wears the label naming its src (a URL document's figures carry no data-fv-src), and the close drops them", async (t) => {
  const fv = await mod();
  urls[NOTE_URL] = "# Note\n\nSee ![p95](figs/p95.png) here.\n";
  fv.openUrlView(NOTE_URL);
  t.after(() => { fv.closeFileView(); doc.activeElement = null; });
  await settle();
  const wrap = doc.getElementById("romp-fileview")!;
  assert.ok(wrap, "the URL viewer is up");
  const body = wrap.querySelector(".fileview-body")!;
  const md = body.querySelector(".fileview-md")!;
  assert.ok(md, "a Rendered box (the stand-in's sanitizer handed it an empty body)");
  assert.equal(captures(body, "error"), 1, "one capture-phase error listener on the URL viewer's body");
  assert.equal(captures(body, "load"), 1);
  const fig = img({ src: "http://notes-api.test/notes/figs/p95.png", alt: "p95" });   // resolveDocRelative made it absolute; no data-fv-src for a URL document
  md.appendChild(block("p", txt("See "), fig, txt(" here.")));
  fire(fig, "error");
  assert.equal(labelAfter(fig)!.textContent, fv.FIGURE_FAILED + " http://notes-api.test/notes/figs/p95.png (p95)", "the label names the src the figure carries");
  fire(fig, "load");
  assert.equal(labelAfter(fig), null);
  fv.closeFileView();
  assert.equal(captures(body, "error"), 0, "the close dropped both (closeHooks)"); assert.equal(captures(body, "load"), 0);
});

test("the label names the candidate the browser asked for (the Slice 7 review's round 1): an img inside a <picture> whose <source srcset> the browser chose, or an img with its own srcset, reports that candidate in currentSrc and never falls back to src, so the label names it by the authored spelling rewriteFigureSrcs kept in data-fv-srcset, or as written when the candidates were left as written; an img whose own src failed, or one with no currentSrc to read, keeps pictureDest's rule", async (t) => {
  const { md } = await open(t);
  const fv = await mod();
  // a <picture> whose <source> the browser chose: the source's srcset rewritten through /file, the authored candidates kept beside it
  const source = new El("source"); source.setAttribute("type", "image/webp");
  source.setAttribute("srcset", fileSrc("figs/dark.webp")); source.setAttribute("data-fv-srcset", "figs/dark.webp");
  const pImg = img({ src: fileSrc("figs/plot.png"), "data-fv-src": "figs/plot.png", alt: "plot" });
  (pImg as any).currentSrc = fileSrc("figs/dark.webp");   // the browser's answer: the candidate it fetched (absolute in a browser; the stand-in resolves nothing, so as the attribute reads)
  const picture = block("picture", source, pImg);
  const p1 = block("p", picture); md.appendChild(p1);
  fire(pImg, "error");
  assert.equal(labelAfter(picture)!.textContent, fv.FIGURE_FAILED + " figs/dark.webp (plot)", "the source's candidate, as the author wrote it (before: figs/plot.png, a file the browser never asked for and that may well be there)");
  // the Comments panel's wrap inside the picture: the img still finds its picture and the candidate
  const wrapSpan = block("span", pImg); wrapSpan.className = "fc-imgwrap"; picture.appendChild(wrapSpan);
  fire(pImg, "error");
  assert.equal(labelAfter(picture)!.textContent, fv.FIGURE_FAILED + " figs/dark.webp (plot)", "through the layer's wrap");
  assert.equal(p1.querySelectorAll("[data-fv-figerr]").length, 1);
  // an img with its own srcset: the 1x candidate chosen (a 1x display)
  const dense = img({ src: fileSrc("figs/plot.png"), "data-fv-src": "figs/plot.png", alt: "dense", srcset: fileSrc("figs/missing-2x.png") + " 2x, " + fileSrc("figs/missing-1x.png") + " 1x", "data-fv-srcset": "figs/missing-2x.png 2x, figs/missing-1x.png 1x" });
  (dense as any).currentSrc = fileSrc("figs/missing-1x.png");
  md.appendChild(block("p", dense));
  fire(dense, "error");
  assert.equal(labelAfter(dense)!.textContent, fv.FIGURE_FAILED + " figs/missing-1x.png (dense)", "the img's own candidate, by its authored spelling");
  // candidates left as written (a remote host's absolute ones; a URL document's relative candidates are rewritten to absolute URLs with no data-fv-srcset, so its label names the resolved URL): no data-fv-srcset, the candidate named as it stands in srcset
  const remote = img({ src: "https://cdn.example/plot.png", alt: "remote", srcset: "https://cdn.example/plot-2x.png 2x" });
  (remote as any).currentSrc = "https://cdn.example/plot-2x.png";
  md.appendChild(block("p", remote));
  fire(remote, "error");
  assert.equal(labelAfter(remote)!.textContent, fv.FIGURE_FAILED + " https://cdn.example/plot-2x.png (remote)");
  // the browser chose the img's own src (a light-scheme page under a dark-only source): pictureDest's rule, as before
  const own = img({ src: fileSrc("figs/plot.png"), "data-fv-src": "figs/plot.png", alt: "own" });
  (own as any).currentSrc = fileSrc("figs/plot.png");
  const dark = new El("source"); dark.setAttribute("media", "(prefers-color-scheme: dark)"); dark.setAttribute("srcset", fileSrc("figs/dark.png")); dark.setAttribute("data-fv-srcset", "figs/dark.png");
  const picture2 = block("picture", dark, own);
  md.appendChild(block("p", picture2));
  fire(own, "error");
  assert.equal(labelAfter(picture2)!.textContent, fv.FIGURE_FAILED + " figs/plot.png (own)", "the img's own src failed: its authored spelling");
  // a currentSrc no carrier accounts for (a browser spelling the URL another way): pictureDest's rule, never a blank
  const odd = img({ src: fileSrc("figs/plot.png"), "data-fv-src": "figs/plot.png", alt: "odd", srcset: fileSrc("figs/x.png") + " 2x", "data-fv-srcset": "figs/x.png 2x" });
  (odd as any).currentSrc = "http://elsewhere.test/x.png";
  md.appendChild(block("p", odd)); fire(odd, "error");
  assert.equal(labelAfter(odd)!.textContent, fv.FIGURE_FAILED + " figs/plot.png (odd)");
  // no currentSrc to read (the stand-in's default, the first case's imgs): pictureDest's rule
  const plain = img({ src: fileSrc("figs/p.png"), "data-fv-src": "figs/p.png", alt: "p", srcset: fileSrc("figs/p-2x.png") + " 2x", "data-fv-srcset": "figs/p-2x.png 2x" });
  md.appendChild(block("p", plain)); fire(plain, "error");
  assert.equal(labelAfter(plain)!.textContent, fv.FIGURE_FAILED + " figs/p.png (p)");
});

test("a data: source is cut to its head in the label (the Slice 7 review's round 1: an inline image's whole payload wrapped into a box the height of the column), the scheme and media type through the comma with an ellipsis; a link holding the figure alone gets the label after the link, never inside it (inside, the label wore the link's pointer and a click on it followed the link); a link with more in it keeps the label beside its img, one label per img", async (t) => {
  const { md } = await open(t);
  const fv = await mod();
  const inline = img({ src: "data:image/png;base64,iVBORw0KGgo" + "A".repeat(3000), alt: "inline" });
  md.appendChild(block("p", inline));
  fire(inline, "error");
  assert.equal(labelAfter(inline)!.textContent, fv.FIGURE_FAILED + " data:image/png;base64,\u2026 (inline)", "the head through the comma and an ellipsis (before: the whole URI, three thousand characters of base64)");
  const svgInline = img({ src: "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg'/>", alt: "" });
  md.appendChild(block("p", svgInline)); fire(svgInline, "error");
  assert.equal(labelAfter(svgInline)!.textContent, fv.FIGURE_FAILED + " data:image/svg+xml;utf8,\u2026", "any data: source, whatever its length; an empty alt adds no parentheses");
  const noComma = img({ src: "data:" + "x".repeat(100), alt: "" });   // malformed: no comma
  md.appendChild(block("p", noComma)); fire(noComma, "error");
  assert.equal(labelAfter(noComma)!.textContent, fv.FIGURE_FAILED + " data:" + "x".repeat(35) + "\u2026", "no comma: the first forty characters");
  // a link holding the figure alone: [![linked](figs/missing5.png)](https://example.com/x)
  const linked = img({ src: fileSrc("figs/missing5.png"), "data-fv-src": "figs/missing5.png", alt: "linked" });
  const a = block("a", linked); a.setAttribute("href", "https://example.com/x");
  const p = block("p", txt("Link: "), a, txt(" tail.")); md.appendChild(p);
  fire(linked, "error");
  assert.equal(labelAfter(linked), null, "nothing inside the link");
  const la = labelAfter(a);
  assert.ok(la, "the label is the link's next sibling"); assert.equal(la!.textContent, fv.FIGURE_FAILED + " figs/missing5.png (linked)");
  sameNodes(p.childNodes, [p.childNodes[0], a, la!, p.childNodes[3]], "text, the link, the label, text");
  sameNodes(a.childNodes, [linked], "the link holds the img alone still");
  fire(linked, "error"); assert.equal(p.querySelectorAll("[data-fv-figerr]").length, 1, "a second error rewrites the one label after the link");
  fire(linked, "load"); assert.equal(labelAfter(a), null, "the load removes it from there");
  // the regions layer's wrap inside the link (the panel open): <a><span.fc-imgwrap><img></span></a>, the label after the link still
  const wrapSpan = block("span", linked); wrapSpan.className = "fc-imgwrap"; a.appendChild(wrapSpan);
  fire(linked, "error");
  assert.equal(labelAfter(a)!.textContent, fv.FIGURE_FAILED + " figs/missing5.png (linked)", "climbed through the wrap and the link");
  assert.equal(a.querySelectorAll("[data-fv-figerr]").length, 0);
  fire(linked, "load"); assert.equal(labelAfter(a), null);
  // a link with text beside the figure: the label stays beside its img, as the browser's alt text does
  const inText = img({ src: fileSrc("figs/missing6.png"), "data-fv-src": "figs/missing6.png", alt: "badge" });
  const a2 = block("a", inText, txt(" docs")); a2.setAttribute("href", "https://example.com/docs");
  md.appendChild(block("p", a2));
  fire(inText, "error");
  assert.equal(labelAfter(inText)!.textContent, fv.FIGURE_FAILED + " figs/missing6.png (badge)", "inside the link, after the img");
  assert.equal(labelAfter(a2), null);
  // two figures in one link: each keeps its own label beside itself
  const b1 = img({ src: fileSrc("figs/b1.png"), "data-fv-src": "figs/b1.png", alt: "b1" });
  const b2 = img({ src: fileSrc("figs/b2.png"), "data-fv-src": "figs/b2.png", alt: "b2" });
  const a3 = block("a", b1, b2); a3.setAttribute("href", "https://example.com/two");
  md.appendChild(block("p", a3));
  fire(b1, "error"); fire(b2, "error");
  assert.equal(labelAfter(b1)!.textContent, fv.FIGURE_FAILED + " figs/b1.png (b1)"); assert.equal(labelAfter(b2)!.textContent, fv.FIGURE_FAILED + " figs/b2.png (b2)");
  assert.equal(a3.querySelectorAll("[data-fv-figerr]").length, 2, "one label per img, both inside the link that holds more than one");
  assert.equal(labelAfter(a3), null);
});

// ── source pins: what the node cases cannot execute here (the browser leg executes the rest) ──────────────────────────
test("source: armFigureLabels is armed in both viewers and dropped with each (ctx.onClose in the local one, closeHooks in the URL one); it arms exactly two capture listeners, error and load, removes both, and never assigns img.onerror; the label is span.fv-figerr with the mark data-fv-figerr; its text is FIGURE_FAILED, a space, pictureDest's answer and the alt in parentheses (contract C2); FIGURE_FAILED's text is contract C5's; headingWords skips the mark's element after its img line", () => {
  assert.match(VIEW, /\n  ctx\.onClose\(armFigureLabels\(body\)\);\n/, "the local viewer: armed once at the open beside the re-seat's listener and dropped by onClose");
  assert.match(VIEW, /\n  closeHooks\.push\(armFigureLabels\(body\)\);/, "the URL viewer: the same, dropped through the module's close hooks");
  assert.equal(VIEW.split("armFigureLabels(body)").length - 1, 2, "two call sites, one per viewer");
  const arm = VIEW.slice(VIEW.indexOf("function armFigureLabels(body: HTMLElement): () => void {"), VIEW.indexOf("/** A URL document's figures resolve against where the document LIVES"));
  assert.ok(arm.length > 0, "armFigureLabels is a module-level function (found)");
  assert.match(arm, /body\.addEventListener\("error", onError, true\);\n\s*body\.addEventListener\("load", onLoad, true\);/, "two capture listeners on the body: an img's error and load do not bubble");
  assert.match(arm, /return \(\) => \{ body\.removeEventListener\("error", onError, true\); body\.removeEventListener\("load", onLoad, true\); \};/, "the drop removes both");
  assert.equal((arm.match(/addEventListener\(/g) || []).length, 2, "exactly two listeners, nothing per paint or per img");
  assert.doesNotMatch(arm, /\.onerror\s*=/, "img.onerror is never set (preview.ts's heal skips an img with one)");
  assert.doesNotMatch(arm, /setTimeout|requestAnimationFrame|Date\.now/, "keyed on the events alone: no timer, no debounce");
  assert.doesNotMatch(arm, /fetch\(|new Image\(|\.src = /, "no second request to learn a reason: the event carries no status and the label names the fact and the source");
  assert.match(VIEW, /\nconst FIGERR_MARK = "data-fv-figerr";\n/, "the mark");
  assert.match(VIEW, /\nconst FIGERR_CLASS = "fv-figerr";\n/, "the class, for the sheets alone");
  assert.match(arm, /const label = el\("span", FIGERR_CLASS\);\n\s*label\.setAttribute\(FIGERR_MARK, ""\);/, "the label is a span wearing the class and the mark");
  assert.match(VIEW, /function figureLabelAfter\(anchor: Element\): Element \| null \{\n\s*const n = anchor\.nextSibling;\n\s*return n && n\.nodeType === 1 && \(n as Element\)\.hasAttribute\(FIGERR_MARK\) \? n as Element : null;/, "found by the mark on the anchor's next sibling, never by the class");
  assert.match(VIEW, /const src = failedSource\(img\);\n\s*return FIGURE_FAILED \+ " " \+ \(src \? shownSource\(src\) : FIGURE_NO_SOURCE\) \+ \(alt \? " \(" \+ alt \+ "\)" : ""\);/, "the text (contract C2, the review's round 1 and its round 2): FIGURE_FAILED, a space, the source the browser asked for (failedSource) as the label shows it (shownSource) or FIGURE_NO_SOURCE when the figure names none (an empty destination), the alt in parentheses when not empty");
  // the review's round 1: the source is the candidate the browser asked for, read off currentSrc and matched against the srcset carriers
  // by the authored candidates rewriteFigureSrcs keeps in data-fv-srcset; the img's own src, or no currentSrc, keeps pictureDest's rule
  assert.match(VIEW, /\nconst FV_SRCSET = "data-fv-srcset";\n/, "the authored candidates' attribute");
  assert.match(VIEW, /if \(changed\) \{ el\.setAttribute\(FV_SRCSET, ref\.value\); el\.setAttribute\("srcset", serializeSrcset\(cands\)\); \}[^\n]*\n\s*else el\.removeAttribute\(FV_SRCSET\);/, "rewriteFigureSrcs keeps the authored srcset beside its rewrite, for the img's and a source's alike, and clears a stale one");
  const fs = VIEW.slice(VIEW.indexOf("function failedSource(img: Element): string | null {"), VIEW.indexOf("function shownSource(src: string): string {"));
  assert.match(fs, /const cur = \(img as HTMLImageElement\)\.currentSrc \|\| "";\n\s*if \(!cur \|\| cur === absUrl\(img\.getAttribute\("src"\) \|\| ""\)\) return pictureDest\(img\);/, "the img's own src, or nothing to read: pictureDest's rule");
  assert.match(fs, /const picture = img\.closest\("picture"\);\n\s*const carriers: Element\[\] = picture \? \[\.\.\.Array\.from\(picture\.querySelectorAll\("source"\)\), img\] : \[img\];/, "the carriers: the picture's sources, then the img");
  assert.match(fs, /const was = c\.hasAttribute\(FV_SRCSET\) \? parseSrcset\(c\.getAttribute\(FV_SRCSET\) \|\| ""\) : now;\n\s*for \(let i = 0; i < now\.length; i\+\+\) if \(absUrl\(now\[i\]\.url\) === cur\) return \(was\[i\] \?\? now\[i\]\)\.url;/, "the candidate matched by its resolved URL, named by its authored spelling");
  assert.doesNotMatch(fs, /fetch\(|new Image\(|\.src = /, "no second request");
  assert.match(VIEW, /function shownSource\(src: string\): string \{\n\s*if \(!\/\^data:\/i\.test\(src\)\) return src;\n\s*const comma = src\.indexOf\(","\);\n\s*return \(comma >= 0 \? src\.slice\(0, comma \+ 1\) : src\.slice\(0, 40\)\) \+ "\u2026";\n\}/, "a data: source cut to its head with an ellipsis; anything else as written");
  assert.match(VIEW, /function linkAround\(p: Element, a: Element\): boolean \{\n\s*return p\.localName === "a" && p\.children\.length === 1 && p\.children\[0\] === a && \(p\.textContent \|\| ""\)\.trim\(\) === "";\n\}/, "a link holding the figure alone is climbed (figureAnchor), so the label is not a click target that follows the link");
  assert.match(VIEW, /p\.localName === "picture" \|\| p\.classList\.contains\("fc-imgwrap"\) \|\| linkAround\(p, a\)/, "…beside the picture and the wrap");
  assert.match(VIEW, /\nimport \{ pictureDest \} from "\.\/file-comments";/, "pictureDest is the panel's own rule, imported (on a line of its own, as the preview imports are: the registry pin in file-comments.test.ts holds the action's import line), not a second reading of data-fv-src");
  assert.match(VIEW, /\nexport const FIGURE_FAILED = "Image failed to load:";\n/, "contract C5's text, exported for the guide's pin");
  assert.match(VIEW, /p\.localName === "picture" \|\| p\.classList\.contains\("fc-imgwrap"\)/, "the anchor climbs a <picture> and the regions layer's wrap (C2 and its addendum)");
  assert.match(VIEW, /if \(t\.closest\('\[data-act="' \+ GATE_ACT \+ '"\]'\)\) return null;/, "an img under a gate's placeholder is left alone");
  assert.match(VIEW, /function headingWords\(n: Node\): string \{\n\s*if \(n\.nodeType === 3\) return \(n as Text\)\.data;\n\s*const e = n as Element;\n\s*if \(e\.localName === "img"\) return " " \+ \(e\.getAttribute\("alt"\) \|\| ""\) \+ " ";\n\s*if \(e\.hasAttribute\(FIGERR_MARK\)\) return "";/, "headingWords: the img's alt in place, then the label's element skipped");
});

// ── the stand-in's projection (ui/test-dom-shim.ts): a node inspects as its primitives, never as the tree ─────────────
test("a stand-in node enumerates its primitives alone, so a failing assertion's dump shows neither parentNode nor childNodes", () => {
  const root = new El("p"); root.className = "row";
  const child = root.appendChild(new El("img")); root.appendChild(new Txt("beta"));
  for (const n of [root, child, root.childNodes[1]] as Array<El | Txt>) {
    for (const k of Object.keys(n)) assert.ok(staysEnumerable((n as any)[k]), k + " is enumerable and holds a " + typeof (n as any)[k]);
    const dump = inspect(n, { compact: false, customInspect: false, depth: 1000, maxArrayLength: Infinity, showHidden: false, showProxy: false, sorted: true, getters: true });
    assert.ok(!dump.includes("parentNode") && !dump.includes("childNodes"), "the dump holds no edge: " + dump);
  }
  assert.ok(child.parentNode === root && root.childNodes[0] === child && child.nextSibling === root.childNodes[1], "the tree is reachable as before, the next sibling included");
  assertHiddenEvent(new Ev("error"), root, child);
});
