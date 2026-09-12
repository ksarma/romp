// The panel's half of the block-level paint on a display formula (plans/markdown-viewer.md Slice 8, item 5; the Slice 8 contract
// line in the notes directory). A display formula is a block of its own line, which no inline mark can wrap: a mark around a
// block box paints nothing over it, and a mark between `.katex-display` and its `.katex` breaks KaTeX's layout, so the anchor
// map's paint STAMPS the formula's own `.katex-display` element instead of wrapping it (the block class `fc-hl-block` or
// `fc-presel-block` beside the caller's, and the paint's data attributes) and returns the element among the marks. The panel
// treats it as one of its marks, with one difference pinned here: where a mark is unwrapped, the element is STRIPPED in place.
// Before this change `unwrapMarks` unwrapped every element it was handed, so a stamped `.katex-display` would have had its
// `.katex` root hoisted into the page as a top-level node the block pairing meets (and paintAll's unpaint never selected the
// block classes, so the class stayed on the box across passes). Driven over a DOM stand-in of the RENDERED view (the unpaint-
// normalize suite's stand-in, its `title` an attribute as the DOM's is), the box stamped as the paint and the pass leave it, and
// the panel's own pass fired through the seam's onRendered; then the exported step directly; then the sheets and the readers by
// source text (the parity list holds the heads; fileview-parity.test.ts compares the bodies). Nodes hide their edges at
// construction (hideEdges, ui/test-dom-shim.ts). Synthetic fixtures only: the notes-api world, placeholder ids.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx } from "./file-view";
import type { Status } from "./file-comments-model";
import { hideEdges } from "../test-dom-shim";

const read = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const SRC = read("file-comments.ts");
const CHAT = read("styles.css");
const FEED = read("feed.css");

// ── fixtures: the notes-api world; a note with a display formula between two paragraphs ──
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const ROOT = "/repo/notes-api";
const STORE_PATH = ROOT + "/.trackchanges/docs%2Freport.md.json";
const BEFORE = "Para before the formula.";
const AFTER = "Para after the formula.";
const DOC = "# Report\n\n" + BEFORE + "\n\n$$\n\\sum_i i\n$$\n\n" + AFTER + "\n";
const CID = "1757145600000-9";
function status(): Status {
  return {
    verb: "status", root: ROOT, storePath: STORE_PATH, trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
    store: { v: 3, path: "docs/report.md", suggestions: [], comments: [] },
    hunks: [], log: [],
    unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null },
  };
}

// ── the DOM stand-in (the unpaint-normalize suite's), its normalize counted per element, `title` an attribute ──
const normalized = new Map<El, number>();
class Ev {
  target: El | Txt | null = null;
  currentTarget: El | null = null;
  defaultPrevented = false;
  stopped = false;
  key: string;
  detail = 0;
  constructor(public type: string, init: { key?: string } = {}) { this.key = init.key || ""; hideEdges(this); }
  preventDefault(): void { this.defaultPrevented = true; }
  stopPropagation(): void { this.stopped = true; }
}
type Listener = (ev: Ev) => void;
type Reg = { type: string; cb: Listener; capture: boolean };
const kebab = (k: string) => k.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
class Txt {
  nodeType = 3;
  parentNode: El | null = null;
  constructor(public data: string) { hideEdges(this); }
  get textContent(): string { return this.data; }
  get length(): number { return this.data.length; }
  get parentElement(): El | null { return this.parentNode; }
  splitText(off: number): Txt {
    const tail = new Txt(this.data.slice(off));
    this.data = this.data.slice(0, off);
    const p = this.parentNode;
    if (p) { const i = p.childNodes.indexOf(this); p.childNodes.splice(i + 1, 0, tail); tail.parentNode = p; }
    return tail;
  }
}
type Compound = { tag: string | null; classes: string[]; attrs: Array<[string, string | null]> };
function parseSel(sel: string): Compound[][] {
  return sel.split(",").map((g) => g.trim()).filter(Boolean).map((g) => g.split(/\s+/).map((s) => {
    const m = /^([a-zA-Z][\w-]*)?((?:\.[\w-]+)*)((?:\[[\w-]+(?:="[^"]*")?\])*)$/.exec(s);
    if (!m) throw new Error("stand-in: unsupported selector " + s);
    const classes = (m[2].match(/\.[\w-]+/g) || []).map((c) => c.slice(1));
    const attrs: Array<[string, string | null]> = [];
    for (const a of m[3].match(/\[[^\]]+\]/g) || []) { const am = /^\[([\w-]+)(?:="([^"]*)")?\]$/.exec(a)!; attrs.push([am[1], am[2] ?? null]); }
    return { tag: m[1] ? m[1].toUpperCase() : null, classes, attrs };
  }));
}
class El {
  nodeType = 1;
  tagName: string;
  parentNode: El | null = null;
  childNodes: Array<El | Txt> = [];
  attrs = new Map<string, string>();
  listeners: Reg[] = [];
  hidden = false; disabled = false; readOnly = false; type = ""; value = ""; checked = false; placeholder = "";
  innerHTML = "";
  style: Record<string, string> = {};
  rect = { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 };
  constructor(tag: string) { this.tagName = tag.toUpperCase(); hideEdges(this); }
  get ownerDocument(): typeof doc { return doc; }
  get parentElement(): El | null { return this.parentNode; }
  get firstChild(): El | Txt | null { return this.childNodes[0] || null; }
  get firstElementChild(): El | null { return (this.childNodes.find((c) => c instanceof El) as El | undefined) || null; }
  get children(): El[] { return this.childNodes.filter((c) => c instanceof El) as El[]; }
  get isConnected(): boolean { return doc.body.contains(this); }
  get className(): string { return this.attrs.get("class") || ""; }
  set className(v: string) { this.attrs.set("class", v); }
  get classes(): string[] { return this.className.split(/\s+/).filter(Boolean); }
  classList = {
    add: (...c: string[]) => { const s = new Set(this.classes); for (const x of c) s.add(x); this.className = [...s].join(" "); },
    remove: (...c: string[]) => { const s = new Set(this.classes); for (const x of c) s.delete(x); this.className = [...s].join(" "); },
    toggle: (c: string, on?: boolean) => { const want = on === undefined ? !this.classes.includes(c) : on; if (want) this.classList.add(c); else this.classList.remove(c); },
    contains: (c: string) => this.classes.includes(c),
  };
  get tabIndex(): number { return this.attrs.has("tabindex") ? Number(this.attrs.get("tabindex")) : -1; }
  set tabIndex(v: number) { this.attrs.set("tabindex", String(v)); }
  get title(): string { return this.attrs.get("title") || ""; }   // the DOM's title is the attribute, so removeAttribute clears it
  set title(v: string) { this.attrs.set("title", v); }
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
  insertBefore<T extends El | Txt>(n: T, ref: El | Txt | null): T {
    if (!ref) return this.appendChild(n);
    this.detach(n);
    const i = this.childNodes.indexOf(ref);
    this.childNodes.splice(i < 0 ? this.childNodes.length : i, 0, n); n.parentNode = this; return n;
  }
  removeChild<T extends El | Txt>(n: T): T { this.detach(n); return n; }
  replaceChildren(...c: Array<El | Txt>): void { for (const x of this.childNodes) x.parentNode = null; this.childNodes = []; for (const x of c) this.appendChild(x); }
  remove(): void { this.detach(this); }
  /** The DOM's normalize (adjacent text nodes merged, empty ones dropped, the subtree walked), counted per element (normalized). */
  normalize(): void {
    normalized.set(this, (normalized.get(this) || 0) + 1);
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
    return (!c.tag || c.tag === this.tagName) && c.classes.every((k) => this.classes.includes(k))
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
  addEventListener(type: string, cb: Listener, opts?: boolean | { capture?: boolean }): void {
    this.listeners.push({ type, cb, capture: typeof opts === "boolean" ? opts : !!(opts && opts.capture) });
  }
  removeEventListener(type: string, cb: Listener, opts?: boolean | { capture?: boolean }): void {
    const cap = typeof opts === "boolean" ? opts : !!(opts && opts.capture);
    this.listeners = this.listeners.filter((l) => !(l.type === type && l.cb === cb && l.capture === cap));
  }
  dispatchEvent(ev: Ev): boolean { return dispatch(this, ev); }
  click(): void { this.dispatchEvent(new Ev("click")); }
  focus(): void { doc.activeElement = this; }
  blur(): void { if (doc.activeElement === this) doc.activeElement = null; }
  scrollIntoView(): void { /* inert */ }
  getBoundingClientRect(): typeof this.rect { return this.rect; }
  getClientRects(): Array<typeof this.rect> { return [this.rect]; }
  get offsetWidth(): number { return 0; }
}
const doc = hideEdges({
  listeners: [] as Reg[],
  body: null as unknown as El,
  hidden: false,
  activeElement: null as El | null,
  createElement: (tag: string) => new El(tag),
  createTextNode: (s: string) => new Txt(s),
  getElementById: () => null,
  addEventListener(type: string, cb: Listener, opts?: boolean | { capture?: boolean }): void {
    doc.listeners.push({ type, cb, capture: typeof opts === "boolean" ? opts : !!(opts && opts.capture) });
  },
  removeEventListener(type: string, cb: Listener, opts?: boolean | { capture?: boolean }): void {
    const cap = typeof opts === "boolean" ? opts : !!(opts && opts.capture);
    doc.listeners = doc.listeners.filter((l) => !(l.type === type && l.cb === cb && l.capture === cap));
  },
  contains: (n: El | Txt | null) => doc.body.contains(n),
});
doc.body = new El("body");
function dispatch(target: El | Txt, ev: Ev): boolean {
  ev.target = target;
  const chain: El[] = [];
  for (let n: El | null = target instanceof El ? target : target.parentNode; n; n = n.parentNode) chain.push(n);
  const run = (ls: Reg[], capture: boolean, node: El | null): boolean => {
    for (const l of ls.slice()) {
      if (l.type !== ev.type || l.capture !== capture) continue;
      ev.currentTarget = node; l.cb.call(node, ev);
      if (ev.stopped) return true;
    }
    return false;
  };
  if (run(doc.listeners, true, null)) return !ev.defaultPrevented;
  for (let i = chain.length - 1; i >= 0; i--) if (run(chain[i].listeners, true, chain[i])) return !ev.defaultPrevented;
  for (const n of chain) if (run(n.listeners, false, n)) return !ev.defaultPrevented;
  run(doc.listeners, false, null);
  return !ev.defaultPrevented;
}
const win: any = new EventTarget();
win.parent = win; win.innerWidth = 1200; win.innerHeight = 800;
win.getSelection = () => null;
win.confirm = () => true;
hideEdges(win);
(globalThis as any).window = win;
(globalThis as any).document = doc;
const store = new Map<string, string>();
(globalThis as any).localStorage = {
  getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
  setItem: (k: string, v: string) => { store.set(k, String(v)); },
  removeItem: (k: string) => { store.delete(k); },
};

// ── the viewer stand-in: the RENDERED body as marked and the math fill leave it (a heading, a paragraph, the filled display
//    formula's `.katex-display` with its `.katex` root, a paragraph), the seam as closures, the poll's HEAD answers ──
type World = { ctx: FileViewActionCtx; posted: any[]; main: El; body: El; md: El; hooks: { rendered: Array<() => void>; close: Array<() => void> }; mtimes: Record<string, string>; close(): void };
let cur: World | null = null;
(globalThis as any).fetch = async (url: string) => {
  if (url.includes("/sessions")) return { json: async () => [] };
  const p = decodeURIComponent((/[?&]path=([^&]*)/.exec(url) || [])[1] || "");
  const mt = cur!.mtimes[p];
  return { status: mt === undefined ? 404 : 200, headers: { get: (h: string) => (h === "X-Romp-Mtime-Ns" && mt !== undefined ? mt : null) } };
};
const el = (tag: string, cls?: string, text?: string): El => { const e = new El(tag); if (cls) e.className = cls; if (text !== undefined) e.appendChild(new Txt(text)); return e; };
function renderMd(md: El): void {
  const h1 = el("h1", undefined, "Report");
  const p1 = el("p", undefined, BEFORE);
  const display = el("span", "katex-display");
  const katex = el("span", "katex");
  const html = el("span", "katex-html");
  html.appendChild(el("span", "mord", "∑"));
  katex.appendChild(html); display.appendChild(katex);
  const p2 = el("p", undefined, AFTER);
  md.replaceChildren(h1, new Txt("\n"), p1, new Txt("\n"), display, new Txt("\n"), p2, new Txt("\n"));
}
function world(): World {
  const main = new El("div"); main.className = "fileview-main";
  const body = new El("div"); body.className = "fileview-body";
  const md = new El("div"); md.className = "fileview-md";
  body.appendChild(md);
  main.appendChild(body);
  doc.body.appendChild(main);
  renderMd(md);
  const w = { posted: [] as any[], main, body, md, hooks: { rendered: [] as Array<() => void>, close: [] as Array<() => void> }, mtimes: {} as Record<string, string> } as World;
  w.ctx = {
    path: ABS, sid: SID, todoId: null,
    body: () => body as unknown as HTMLElement, mode: () => "rendered", text: () => DOC, mtimeNs: () => "1757145600000000001", media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [],
    identity: () => ({ name: "api", color: null }),
    onRendered: (cb) => { w.hooks.rendered.push(cb); }, onSelection: () => { /* inert */ },
    onSaved: () => { /* inert */ }, onClose: (cb) => { w.hooks.close.push(cb); },
    post: (m) => { w.posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: () => { /* inert */ }, editing: () => false, setTrackedEdit: () => { /* inert */ }, guardClose: () => { /* inert */ },
    aside: (node) => { main.querySelector(".fileview-aside")?.remove(); if (node) { const n = node as unknown as El; n.classList.add("fileview-aside"); main.appendChild(n); } },
    setMode: () => { /* inert */ }, scrollToOffset: () => { /* inert */ },
    reload: () => { renderMd(md); for (const cb of w.hooks.rendered) cb(); },
  };
  w.close = () => { for (const cb of w.hooks.close) cb(); main.remove(); if (cur === w) cur = null; };
  cur = w;
  return w;
}
const flush = () => new Promise<void>((r) => setImmediate(r));
const lastOf = (w: World, type: string, verb?: string) => [...w.posted].reverse().find((m) => m.type === type && (verb === undefined || m.verb === verb));
function answer(w: World, s: Status, m = lastOf(w, "fileComments", "status")): void {
  assert.ok(m, "a status ask is outstanding");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: m.reqId, ...s } }));
  w.mtimes[w.ctx.path] = s.fileMtimeNs;
  if (s.storePath && s.storeMtimeNs !== null) w.mtimes[s.storePath] = s.storeMtimeNs;
  if (s.root && s.configMtimeNs !== null) w.mtimes[s.root + "/.trackchanges/config.json"] = s.configMtimeNs;
}
async function openPanel(w: World): Promise<void> {
  const fc = await import("./file-comments");
  const unit = fc.fileCommentsAction.mount(w.ctx) as unknown as El;
  const button = unit.childNodes[0] as El;
  answer(w, status()); await flush();
  button.click();
  answer(w, status()); await flush(); await flush();
  assert.ok(w.main.querySelector(".fileview-aside"), "the panel is mounted beside the body");
}
/** The shape of an element's children: T(text) for a text node, TAG.class for an element. */
const shapeOf = (e: El): string[] => e.childNodes.map((c) => (c instanceof Txt ? "T(" + c.data + ")" : c.tagName + (c.className ? "." + c.classes.join(".") : "")));
const display = (w: World): El => { const d = w.md.querySelector(".katex-display"); assert.ok(d, "the filled display formula"); return d!; };
/** Stamp the box as the paint and the pass leave a highlight (the contract: the block class and the data attributes; the pass adds
 *  tabIndex, role, title, and the arrivals' data-new), or a pending target (`fc-presel-block`, the paint's stamp alone). */
function stampHighlight(d: El, id: string, context = false): void {
  d.classList.add("fc-hl-block"); if (context) d.classList.add("fc-hl-context");
  d.dataset.act = "fcopen"; d.dataset.id = id; d.dataset.new = "1";
  d.tabIndex = 0; d.setAttribute("role", "button"); d.title = "Open the comment on this passage";
}
/** Wrap `needle` inside the paragraph `p` in a highlight mark, as the paint leaves one. */
function markIn(p: El, needle: string, id: string): El {
  const t = p.childNodes[0] as Txt;
  const i = t.data.indexOf(needle); assert.ok(i >= 0, needle);
  const mid = t.splitText(i); mid.splitText(needle.length);
  const m = el("mark", "fc-hl"); m.dataset.act = "fcopen"; m.dataset.id = id;
  p.insertBefore(m, mid); m.appendChild(mid);
  return m;
}
const stripped = (d: El) => ({
  cls: d.className, act: d.getAttribute("data-act"), id: d.getAttribute("data-id"), isNew: d.getAttribute("data-new"),
  tab: d.getAttribute("tabindex"), role: d.getAttribute("role"), title: d.getAttribute("title"),
});
const CLEAN = { cls: "katex-display", act: null, id: null, isNew: null, tab: null, role: null, title: null };

test("a paint pass over a body whose display formula wears the highlight's block class strips the box in place (the class, the context cue, data-act, data-id, data-new, tabindex, role, title) and leaves KaTeX's root its child and the box a top-level node; the marks beside it unwrap as before (before: the box was unwrapped like a mark, its .katex hoisted to the top level)", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  await openPanel(w);
  const d = display(w);
  stampHighlight(d, CID, true);
  const p1 = w.md.querySelector("p")!;
  markIn(p1, "before", CID);
  assert.deepEqual(shapeOf(p1), ["T(Para )", "MARK.fc-hl", "T( the formula.)"], "the control: a standing mark in the paragraph");
  const tops = () => shapeOf(w.md).filter((s) => !s.startsWith("T("));
  assert.deepEqual(tops(), ["H1", "P", "SPAN.katex-display.fc-hl-block.fc-hl-context", "P"], "stamped as the paint and the pass leave it");
  normalized.clear();
  for (const cb of w.hooks.rendered) cb();   // the seam's onRendered for the same text: paintAll unpaints what stands, then repaints (nothing: no comment)
  assert.deepEqual(stripped(d), CLEAN, "the box stripped of everything the paint and the pass put on it");
  assert.equal(d.parentNode, w.md, "still a top-level node of the rendered root");
  assert.deepEqual(shapeOf(d), ["SPAN.katex"], "KaTeX's root still its child, nothing between them");
  assert.deepEqual(tops(), ["H1", "P", "SPAN.katex-display", "P"], "the block pairing meets the same four top-level elements");
  assert.equal(normalized.get(d) || 0, 0, "a strip normalizes nothing (no text node moved)");
  assert.deepEqual(shapeOf(p1), ["T(" + BEFORE + ")"], "the paragraph's mark unwrapped and the paragraph normalized whole");
  assert.equal(normalized.get(p1) || 0, 1, "the paragraph normalized once for its mark");
  // the pending target's twin: the presel's block class comes off the same way (the selector names both classes)
  d.classList.add("fc-presel-block"); d.dataset.act = "fcopen"; d.dataset.id = CID;
  for (const cb of w.hooks.rendered) cb();
  assert.deepEqual(stripped(d), CLEAN, "fc-presel-block stripped with its attributes");
  assert.deepEqual(shapeOf(d), ["SPAN.katex"]);
});

test("unwrapMarks over a mixed list: the mark is unwrapped and its parent normalized once, the stamped box is stripped where it stands (its children untouched, its parent not normalized, a class the paint never put on it kept)", async () => {
  const fc = await import("./file-comments");
  const md = el("div", "fileview-md");
  const p = el("p", undefined, "Some words in a paragraph.");
  const d = el("span", "katex-display extra-class");
  const katex = el("span", "katex"); katex.appendChild(el("span", "katex-html", "x"));
  d.appendChild(katex);
  md.replaceChildren(p, new Txt("\n"), d);
  const m = markIn(p, "words", CID);
  stampHighlight(d, CID);
  normalized.clear();
  fc.unwrapMarks([m, d] as unknown as Element[]);
  assert.deepEqual(shapeOf(p), ["T(Some words in a paragraph.)"], "the mark unwrapped, the paragraph whole");
  assert.equal(normalized.get(p) || 0, 1, "its parent normalized once");
  assert.equal(d.parentNode, md, "the box left in place");
  assert.deepEqual(shapeOf(d), ["SPAN.katex"], "its children untouched");
  assert.deepEqual(shapeOf(katex), ["SPAN.katex-html"]);
  assert.equal(d.className, "katex-display extra-class", "the paint's classes stripped, the box's own kept");
  assert.deepEqual([d.getAttribute("data-act"), d.getAttribute("data-id"), d.getAttribute("data-new"), d.getAttribute("tabindex"), d.getAttribute("role"), d.getAttribute("title")], [null, null, null, null, null, null]);
  assert.equal(normalized.get(md) || 0, 0, "a strip moves no text node, so nothing is normalized for it");
  assert.equal(normalized.get(d) || 0, 0);
});

/** Every rule whose selector opens a line as `head`, in sheet order (fileview-parity.test.ts's reader). */
function rulesOf(css: string, head: string): string[] {
  const text = "\n" + css, key = "\n" + head, out: string[] = [];
  for (let at = text.indexOf(key); at >= 0; at = text.indexOf(key, at + 1)) out.push(text.slice(at + 1, text.indexOf("}", at) + 1));
  return out;
}
const HL_HEAD = ".fileview-md .katex-display.fc-hl-block {";
const CTX_HEAD = ".fileview-md .katex-display.fc-hl-block.fc-hl-context {";
const PRESEL_HEAD = ".fileview-md .katex-display.fc-presel-block {";

test("the sheets: the block rules stand once in the panel block of BOTH sheets byte-equal, the highlight's wash and ring and the pending target's accent through tokens alone, no padding (the box is the layout's), the context cue's ring drop, the arrivals dot and the print strip naming the block class; the parity list holds the heads", () => {
  const block = (css: string) => css.slice(css.indexOf("/* ── file comments panel (plans/file-review.md Slice 1; file-comments.ts)"), css.indexOf("/* ── end file comments panel ── */"));
  for (const [name, css] of [["styles.css", CHAT], ["feed.css", FEED]] as const) {
    const panel = block(css);
    for (const head of [HL_HEAD, CTX_HEAD, PRESEL_HEAD]) {
      assert.equal(rulesOf(css, head).length, 1, name + ": one rule for " + head);
      assert.ok(panel.includes("\n" + head), name + ": " + head + " inside the panel block");
      assert.doesNotMatch(rulesOf(css, head)[0], /padding|margin/, name + ": " + head + " adds no padding or margin (the paint moves no layout)");
    }
    const hl = rulesOf(css, HL_HEAD)[0];
    assert.match(hl, /background: color-mix\(in srgb, var\(--warn\) 14%, transparent\); box-shadow: inset 0 0 0 1\.5px color-mix\(in srgb, var\(--warn\) 85%, transparent\);/, name + ": the highlight's own wash and ring, byte for byte");
    assert.match(hl, /cursor: pointer;/, name + ": a control, as a mark is");
    assert.equal(rulesOf(css, CTX_HEAD)[0], CTX_HEAD + " box-shadow: none; }", name + ": the context cue drops the ring, its dashed outline standing alone");
    const presel = rulesOf(css, PRESEL_HEAD)[0];
    assert.match(presel, /background: var\(--accent-wash\); box-shadow: inset 0 0 0 1\.5px var\(--accent\);/, name + ": the pending target's accent");
    for (const r of [hl, presel]) { assert.doesNotMatch(r, /#[0-9a-fA-F]{3,8}\b/, name + ": no bare hex"); assert.doesNotMatch(r, /rgba?\(/, name + ": no bare rgba"); }
    // the arrivals dot: its rule's own selector list names the block class (the block rule's background shorthand outranks a plain .fc-hl[data-new])
    assert.match(css, /\n\.fc-hl\[data-new\], \.fc-ins\[data-new\], \.fc-del\[data-new\]::before, \.fileview-md \.katex-display\.fc-hl-block\[data-new\] \{ background-image: radial-gradient/, name + ": the arrivals dot rides the stamped box");
    // print: the wash and ring come off the box as they come off a mark, at the rule's own weight (the block rules outrank the .fileview-body strip)
    const print = css.slice(css.indexOf("\n@media print {"));
    assert.match(print, /\n {2}\.fileview-md \.katex-display\.fc-hl-block, \.fileview-md \.katex-display\.fc-presel-block \{ background: none; box-shadow: none; outline: none; \}\n/, name + ": the print block strips the block classes");
  }
  for (const head of [HL_HEAD, CTX_HEAD, PRESEL_HEAD]) assert.deepEqual(rulesOf(CHAT, head), rulesOf(FEED, head), head + " mirrors exactly");
  assert.equal(block(CHAT), block(FEED), "the whole panel block still mirrors");
  const parity = read("fileview-parity.test.ts");
  for (const head of [HL_HEAD, CTX_HEAD, PRESEL_HEAD]) assert.ok(parity.includes(JSON.stringify(head)), "fileview-parity.test.ts RULES holds " + head);
});

test("the panel's readers select the block class beside the mark's: paintAll's unpaint and the pending target's three, the repaint's box read and lineBoxOf's own-box answer, goTo's fallback, the pass's context cue on a stamped box, and unwrapMarks' strip", () => {
  const paint = SRC.split("  paintAll(): void {")[1].split("\n  }\n")[0];
  assert.ok(paint.includes('this.unpaint(".fc-hl, .fc-presel, .fc-hl-block, .fc-presel-block");'), "paintAll unpaints both block classes with the marks");
  assert.match(paint, /if \(unsure \|\| \(loc\.state === "context" && !isMarkEl\(m\)\)\) m\.classList\.add\("fc-hl-context"\);/, "the context cue goes on a stamped box by hand (the paint stamps the first class token alone)");
  const repaint = SRC.split("  private repaintPreselPass(): void {")[1].split("\n  }\n")[0];
  assert.equal((repaint.match(/this\.unpaint\("\.fc-presel, \.fc-presel-block"\);/g) || []).length, 3, "the Raw branch, the standing target and the repaint proper");
  assert.doesNotMatch(repaint, /unpaint\("\.fc-presel"\)/, "no unpaint left that misses the block class");
  assert.match(repaint, /for \(const m of Array\.from\(root\.querySelectorAll\("\.fc-presel, \.fc-presel-block"\)\)\) if \(isMark\(m\) \|\| isBlockPaint\(m\)\) boxes\.add\(this\.lineBoxOf\(m, root, memo\)\);/, "a standing stamped box is read as a box; a framed picture still is not");
  const lineBox = SRC.split("  private lineBoxOf(m: Element, root: Element, memo: Map<Element, Element>): Element {")[1].split("\n  }\n")[0];
  assert.match(lineBox, /^\s*if \(isBlockPaint\(m\)\) return m;/, "a stamped box is its own line box: the climb stops at itself");
  const goTo = SRC.split("  goTo(key: string): void {")[1].split("\n  }\n")[0];
  assert.ok(goTo.includes(`'.fc-hl[data-id="' + cssId(key) + '"], .fc-hl-block[data-id="' + cssId(key) + '"], .fc-region[data-id="' + cssId(key) + '"]'`), "Scroll to the passage finds the stamped box");
  const unwrap = SRC.split("export function unwrapMarks(marks: Iterable<Element>): void {")[1].split("\n}\n")[0];
  assert.match(unwrap, /if \(!isMarkEl\(n\)\) \{ stripBlockPaint\(n\); continue; \}/, "an element that is not a mark is stripped, never unwrapped");
  assert.match(SRC, /const BLOCK_PAINT_CLASSES = \["fc-hl-block", "fc-presel-block"\];/);
  assert.match(SRC, /n\.classList\.remove\(\.\.\.BLOCK_PAINT_CLASSES, "fc-hl-context"\);\n\s*for \(const a of \["data-act", "data-id", "data-new", "tabindex", "role", "title"\]\) n\.removeAttribute\(a\);/, "the strip: the classes and every attribute the paint and the pass set");
});
