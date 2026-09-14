// A figure with an EMPTY destination wears a label that says so (the Slice 7 review's round 2 over item 2 of
// plans/markdown-viewer.md). marked renders `![alt]()` as `<img src="" alt="alt">`, and an author can write `<img src="">`
// by hand; for either the browser fires the img's `error` with no request made (the HTML spec's empty-src rule),
// figure-gate.ts's figureRefs skips the empty value so nothing rewrote or gated it, and failedSource answers the empty
// string, so the label's source part had nothing to name: "Image failed to load:  (alt)", a dangling colon before two spaces,
// or "Image failed to load: " alone when the alt was empty too. The label now puts FIGURE_NO_SOURCE ("the source is empty")
// in the source's place. The viewer runs over file-view-figure-error.test.ts's DOM stand-in (copied: node --test runs each
// file in its own process, and that file's cases are a peer's this round), the sanitizer's stand-in handing every Rendered
// paint an empty body and the case laying the figures by hand. Red over a git archive of 402f95d2d at the first label
// assertion (the two spaces). Synthetic fixtures only: the notes-api world, placeholder ids, /repo/notes-api paths.
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

// ── the case: a figure with an empty destination (the Slice 7 review's round 2) ────────────────────────────────────────────
test("a figure with an empty destination (`![alt]()`, which marked renders as <img src=\"\" alt=\"alt\">, or an authored <img src=\"\">): the browser fires its error with no request made (the HTML spec's empty-src rule), and the label names the fact and that the source is empty, the alt in parentheses when there is one (before: \"Image failed to load:  (alt)\", a dangling colon before two spaces and nothing named, or \"Image failed to load: \" alone); a figure whose source is written keeps its label; a second error rewrites the one label", async (t) => {
  const { md } = await open(t);
  const fv = await mod();
  const empty = img({ src: "", alt: "diagram" });
  const bare = img({ src: "", alt: "" });
  const written = img({ src: fileSrc("figs/p95.png"), "data-fv-src": "figs/p95.png", alt: "p95" });
  const p = block("p", txt("Empty: "), empty, txt(" bare: "), bare, txt(" written: "), written);
  md.appendChild(p);
  fire(empty, "error");
  const l1 = labelAfter(empty);
  assert.ok(l1, "the label is the img's next sibling");
  assert.equal(l1!.textContent, fv.FIGURE_FAILED + " the source is empty (diagram)", "the fact, the empty source named as such, the alt (before: \"Image failed to load:  (diagram)\")");
  assert.doesNotMatch(l1!.textContent, /:\s\s|:\s\(|:\s*$/, "no dangling colon, no double space, nothing unnamed");
  fire(bare, "error");
  assert.equal(labelAfter(bare)!.textContent, fv.FIGURE_FAILED + " the source is empty", "an empty alt adds no parentheses (before: \"Image failed to load: \")");
  fire(written, "error");
  assert.equal(labelAfter(written)!.textContent, fv.FIGURE_FAILED + " figs/p95.png (p95)", "a written source, as before");
  assert.equal(labels(md).length, 3, "one label per img");
  sameNodes(p.childNodes, [p.childNodes[0], empty, l1!, p.childNodes[3], bare, labelAfter(bare)!, p.childNodes[6], written, labelAfter(written)!], "each label right after its img; nothing else moved");
  // a second error on the empty figure (the chat page's heal retrying) rewrites the one label, never adds
  fire(empty, "error");
  assert.equal(labels(md).length, 3); assert.equal(labelAfter(empty)!.textContent, fv.FIGURE_FAILED + " the source is empty (diagram)");
  assert.equal(paints, 1, "no paint hook fired for a label");
  // the formula: the words take the source's place when failedSource answers "" or null
  assert.match(VIEW, /\nconst FIGURE_NO_SOURCE = "the source is empty";\n/, "the words, module-private: the guide's Figures sentence stands (the fact, the path when there is one, the alt)");
  assert.match(VIEW, /function figureLabelText\(img: Element\): string \{\n\s*const alt = img\.getAttribute\("alt"\);\n\s*const src = failedSource\(img\);\n\s*return FIGURE_FAILED \+ " " \+ \(src \? shownSource\(src\) : FIGURE_NO_SOURCE\) \+ \(alt \? " \(" \+ alt \+ "\)" : ""\);\n\}/, "the label's text: FIGURE_FAILED, the source through shownSource or the words when there is none, the alt in parentheses when it is not empty");
});
