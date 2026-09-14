// The reader's place, remembered across opens (plans/markdown-viewer.md Slice 6, item 3): file-view.ts's RememberedPlace
// with its two pure functions (rememberedPlaceOf, placeFromRemembered), the module's per-path memory, the write at the
// three moments the reader leaves a file (closeFileView, a replace-open, the window's pagehide) through initFileView's
// host `onLeave`, and the seat on the next open's first text paint (openFileView's `place`, or the memory). The REAL
// openFileView runs over a DOM stand-in (the seam test's idiom: ancestry, attributes, events, a selector engine), given
// what the reader's place needs and the other stand-ins have not: a layout. Every block under `.fileview-md` and every
// row under `code.hljs` has a box by its index (BLOCK_H and ROW_H apart, in content coordinates), the body scrolls
// (scrollTop clamped to its content, as a browser clamps a write) and getBoundingClientRect answers the box less the
// scroll, so reader-place.ts's readPlace and seatPlaceOutcome run as they do in a browser, over the elements the paint
// built, at the paint. Two things build them here where the browser's parser would: an innerHTML setter parses the
// markup codeBlock writes (the .fv-cl rows, hljs spans inside), and the `.fileview-md` box renders its text through
// marked when mdBlock falls back to the bare text, which it does under node because DOMPurify has no document to work in
// (the sanitizer returns its input, and mdBlock's catch writes the text): the blocks' elements, unsanitized (the fixture
// is plain markdown) and without the heading ids the sanitizer's own pass mints. The review's closing pass adds two cases over the
// same stand-ins: the visible leave after a reload whose seat the browser clamped (the seam's reload, a ResizeObserver-free open),
// and the unread-scroll flag under the editor (a ResizeObserver stand-in the case reports through, the body's rects and width
// faked for the hide and the show). Synthetic fixtures only: the notes-api world, placeholder ids, hostname none.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import { inspect } from "node:util";
import * as fs from "node:fs";
import * as path from "node:path";
import { marked } from "marked";
import { assertHiddenEvent, hideEdges, staysEnumerable } from "../test-dom-shim";
import { sourceBlockSpans } from "./anchor-map";
import type { Place } from "./reader-place";
import type { RememberedPlace, At } from "./file-view";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const VIEW = web("file-view.ts");

// ── the layout: the body's edge and height, a block's and a row's pitch ─────────────────────────────
const EDGE = 100;          // the body's top edge in the viewport
const BODY_H = 200;        // the body's clientHeight
const BODY_W = 800;
const BLOCK_H = 40;        // one Rendered block per BLOCK_H px, its box BLOCK_BOX tall (a gap under each)
const BLOCK_BOX = 32;
const ROW_H = 20;          // one Raw row per ROW_H px
type Rect = { left: number; top: number; right: number; bottom: number; width: number; height: number };
const rect = (top: number, height: number, width = BODY_W): Rect => ({ left: 0, top, right: width, bottom: top + height, width, height });

// ── a DOM stand-in: ancestry, ids, attributes, events with capture and bubbling, a tolerant selector engine, a layout ──
class Ev {
  target: El | Txt | null = null;
  currentTarget: El | null = null;
  defaultPrevented = false;
  stopped = false;
  key: string; ctrlKey: boolean; metaKey: boolean; detail: number;
  constructor(public type: string, init: { key?: string; ctrlKey?: boolean; metaKey?: boolean; detail?: number } = {}) {
    this.key = init.key || ""; this.ctrlKey = !!init.ctrlKey; this.metaKey = !!init.metaKey; this.detail = init.detail ?? 0;
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
  get nodeValue(): string { return this.data; }
  set nodeValue(v: string) { this.data = v; }
  get length(): number { return this.data.length; }
  get parentElement(): El | null { return this.parentNode; }
  get nextSibling(): El | Txt | null { const p = this.parentNode; if (!p) return null; const i = p.childNodes.indexOf(this); return p.childNodes[i + 1] || null; }
  get previousSibling(): El | Txt | null { const p = this.parentNode; if (!p) return null; const i = p.childNodes.indexOf(this); return i > 0 ? p.childNodes[i - 1] : null; }
  splitText(off: number): Txt {
    const tail = new Txt(this.data.slice(off));
    this.data = this.data.slice(0, off);
    const p = this.parentNode;
    if (p) { const i = p.childNodes.indexOf(this); p.childNodes.splice(i + 1, 0, tail); tail.parentNode = p; }
    return tail;
  }
}
/** One compound of a selector chain (`tag#id.class[attr="v"]:pseudo`) and whether it must be the next one's parent. */
type Compound = { tag: string | null; id: string | null; classes: string[]; attrs: Array<[string, string | null]>; pseudos: string[]; child: boolean };
/** Comma groups of chains; a chain's links are joined by a descendant (space) or a child (`>`) combinator. A selector the
 *  engine does not know (`:not(...)`, `:is(...)`, an attribute operator other than `=`) parses to null and matches nothing:
 *  the paint queries a few the fixture never satisfies (a task list's checkbox, a KaTeX box), and a throw there would cost
 *  the paint, where a browser answers an empty list. */
function parseSel(sel: string): Compound[][] | null {
  const groups: Compound[][] = [];
  for (const g of sel.split(",").map((s) => s.trim()).filter(Boolean)) {
    const chain: Compound[] = [];
    let child = false;
    for (const tok of g.split(/\s+/)) {
      if (tok === ">") { child = true; continue; }
      const m = /^(\*|[a-zA-Z][\w-]*)?(#[\w-]+)?((?:\.[\w-]+)*)((?:\[[^\]]+\])*)((?::[\w-]+)*)$/.exec(tok);
      if (!m) return null;
      const attrs: Array<[string, string | null]> = [];
      for (const a of m[4].match(/\[[^\]]+\]/g) || []) {
        const am = /^\[(?:\*\|)?([\w-]+)(?:="([^"]*)")?\]$/.exec(a);   // `*|href` (any namespace) reads as the plain attribute
        if (!am) return null;
        attrs.push([am[1], am[2] ?? null]);
      }
      const pseudos = (m[5].match(/:[\w-]+/g) || []).map((p) => p.slice(1));
      if (pseudos.some((p) => p !== "first-child" && p !== "disabled")) return null;
      chain.push({ tag: m[1] && m[1] !== "*" ? m[1].toUpperCase() : null, id: m[2] ? m[2].slice(1) : null, classes: (m[3].match(/\.[\w-]+/g) || []).map((c) => c.slice(1)), attrs, pseudos, child });
      child = false;
    }
    if (chain.length) groups.push(chain);
  }
  return groups;
}
class El {
  nodeType = 1;
  tagName: string;
  parentNode!: El | null;
  childNodes!: Array<El | Txt>;
  attrs = new Map<string, string>();
  listeners: Reg[] = [];
  hidden = false; disabled = false; title = ""; type = ""; value = ""; placeholder = ""; spellcheck = true; wrap = "";
  src = ""; alt = ""; href = ""; download = ""; target = ""; rel = "";
  style: Record<string, string> = {};
  onclick: ((ev: Ev) => void) | null = null;
  scrolled = 0;                                  // scrollIntoView calls (an `at` line's landing, which the memory must not make)
  focused = 0;                                   // focus() calls
  rectReads = 0;                                 // getBoundingClientRect calls: the layout cost a leave adds is read off the body's
  _html = "";
  _scrollTop = 0;
  constructor(tag: string) {
    this.tagName = tag.toUpperCase();
    Object.defineProperty(this, "parentNode", { value: null, writable: true, enumerable: false, configurable: true });
    Object.defineProperty(this, "childNodes", { value: [], writable: true, enumerable: false, configurable: true });
    hideEdges(this);
  }
  get id(): string { return this.attrs.get("id") || ""; }
  set id(v: string) { this.attrs.set("id", v); }
  get localName(): string { return this.tagName.toLowerCase(); }
  get isConnected(): boolean { return doc.body.contains(this); }
  get ownerDocument(): typeof doc { return doc; }
  get parentElement(): El | null { return this.parentNode; }
  get children(): El[] { return this.childNodes.filter((c): c is El => c instanceof El); }
  get firstChild(): El | Txt | null { return this.childNodes[0] || null; }
  get nextSibling(): El | Txt | null { const p = this.parentNode; if (!p) return null; const i = p.childNodes.indexOf(this); return p.childNodes[i + 1] || null; }
  get previousSibling(): El | Txt | null { const p = this.parentNode; if (!p) return null; const i = p.childNodes.indexOf(this); return i > 0 ? p.childNodes[i - 1] : null; }
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
  /** The browser's parser stands in here for the one text write that is a paint: mdBlock's fallback writes the note's
   *  source into the `.fileview-md` box when the sanitizer could not hand it a tree (the header), and the box renders
   *  it through marked as the sanitizer would have; every other element takes the text as one node. */
  set textContent(v: string) {
    this.clear();
    if (v === "") return;
    if (this.classes.includes("fileview-md")) { for (const n of parseHTML(marked.parse(v) as string)) this.appendChild(n); return; }
    this.appendChild(new Txt(v));
  }
  get innerHTML(): string { return this._html; }
  set innerHTML(v: string) { this._html = v; this.clear(); for (const n of parseHTML(v)) this.appendChild(n); }
  private clear(): void { for (const c of this.childNodes) { this.dropFocusIn(c); c.parentNode = null; } this.childNodes.length = 0; }
  private dropFocusIn(n: El | Txt): void { if (n instanceof El && doc.activeElement && n.contains(doc.activeElement)) doc.activeElement = doc.body; }
  private detach(n: El | Txt): void { const p = n.parentNode; if (p) { const i = p.childNodes.indexOf(n); if (i >= 0) p.childNodes.splice(i, 1); n.parentNode = null; } }
  appendChild<T extends El | Txt>(n: T): T {
    if (n instanceof El && n.tagName === "#FRAGMENT") { for (const c of n.childNodes.slice()) this.appendChild(c); return n; }   // a fragment empties into its target
    this.detach(n); this.childNodes.push(n); n.parentNode = this; return n;
  }
  prepend(...ns: Array<El | Txt>): void { for (const n of ns.slice().reverse()) { this.detach(n); this.childNodes.unshift(n); n.parentNode = this; } }
  insertBefore<T extends El | Txt>(n: T, ref: El | Txt | null): T {
    if (!ref) return this.appendChild(n);
    if (n instanceof El && n.tagName === "#FRAGMENT") { for (const c of n.childNodes.slice()) this.insertBefore(c, ref); return n; }
    this.detach(n);
    const i = this.childNodes.indexOf(ref);
    this.childNodes.splice(i < 0 ? this.childNodes.length : i, 0, n); n.parentNode = this; return n;
  }
  removeChild<T extends El | Txt>(n: T): T { this.dropFocusIn(n); this.detach(n); return n; }
  replaceChildren(...c: Array<El | Txt>): void { this.clear(); for (const x of c) this.appendChild(x); }
  append(...c: Array<El | Txt | string>): void { for (const x of c) this.appendChild(typeof x === "string" ? new Txt(x) : x); }
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
  getAttributeNS(_ns: string | null, k: string): string | null { return this.getAttribute(k); }
  hasAttribute(k: string): boolean { return this.attrs.has(k); }
  removeAttribute(k: string): void { this.attrs.delete(k); }
  removeAttributeNS(_ns: string | null, k: string): void { this.attrs.delete(k); }
  contains(n: El | Txt | null): boolean { for (let x: El | Txt | null = n; x; x = x.parentNode) if (x === this) return true; return false; }
  private fits(c: Compound): boolean {
    if (c.tag && c.tag !== this.tagName) return false;
    if (c.id && c.id !== this.id) return false;
    if (!c.classes.every((k) => this.classes.includes(k))) return false;
    if (!c.attrs.every(([a, v]) => this.attrs.has(a) && (v === null || this.attrs.get(a) === v))) return false;
    for (const p of c.pseudos) {
      if (p === "first-child" && !(this.parentNode && this.parentNode.children[0] === this)) return false;
      if (p === "disabled" && !this.disabled) return false;
    }
    return true;
  }
  matches(sel: string): boolean {
    const groups = parseSel(sel);
    if (!groups) return false;
    return groups.some((chain) => {
      if (!this.fits(chain[chain.length - 1])) return false;
      let k = chain.length - 2, a: El | null = this.parentNode;
      while (k >= 0 && a) {
        if (a.fits(chain[k])) { k--; a = a.parentNode; continue; }
        if (chain[k + 1].child) return false;   // a child combinator: the parent had to fit
        a = a.parentNode;
      }
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
  blur(): void { if (doc.activeElement === this) doc.activeElement = null; }
  get tabIndex(): number { const v = this.attrs.get("tabindex"); return v === undefined ? -1 : Number(v); }
  set tabIndex(v: number) { this.attrs.set("tabindex", String(v)); }
  scrollIntoView(): void { this.scrolled++; }
  // ── the layout ──
  private isBody(): boolean { return this.classes.includes("fileview-body"); }
  private scroller(): El | null { for (let a: El | null = this.parentNode; a; a = a.parentNode) if (a.isBody()) return a; return null; }
  /** The element's box in the body's content coordinates: a block of the Rendered view by its index among the box's
   *  element children, a row of the Raw view by its index among the code element's rows, the two roots by their content;
   *  null for everything else (no layout, as the other stand-ins answer). */
  private laid(): { top: number; height: number } | null {
    const p = this.parentNode;
    if (this.classes.includes("fileview-md")) return { top: 0, height: this.children.length * BLOCK_H };
    if (this.tagName === "CODE" && this.classes.includes("hljs")) return { top: 0, height: this.children.filter((c) => c.classes.includes("fv-cl")).length * ROW_H };
    if (p && p.classes.includes("fileview-md")) return { top: p.children.indexOf(this) * BLOCK_H, height: BLOCK_BOX };
    if (p && p.tagName === "CODE" && p.classes.includes("hljs") && this.classes.includes("fv-cl")) return { top: p.children.filter((c) => c.classes.includes("fv-cl")).indexOf(this) * ROW_H, height: ROW_H };
    return null;
  }
  getBoundingClientRect(): Rect {
    this.rectReads++;
    if (this.isBody()) return rect(EDGE, BODY_H);
    const s = this.scroller(), box = this.laid();
    if (!s || !box) return rect(0, 0, 0);
    return rect(EDGE + box.top - s.scrollTop, box.height);
  }
  get clientHeight(): number { return this.isBody() ? BODY_H : 0; }
  get clientWidth(): number { return this.isBody() ? BODY_W : 0; }
  get offsetWidth(): number { return this.clientWidth; }
  /** The body's content height: its Rendered blocks or its Raw rows (the loader, a picture: none). */
  get scrollHeight(): number {
    if (!this.isBody()) return 0;
    const md = this.querySelector(".fileview-md"); if (md) return md.children.length * BLOCK_H;
    const code = this.querySelector("code.hljs"); if (code) return code.children.filter((c) => c.classes.includes("fv-cl")).length * ROW_H;
    return 0;
  }
  get scrollTop(): number { return this._scrollTop; }
  /** Clamped to the content, as a browser clamps a write (reader-place.ts seatPlaceOutcome reads the clamp off the write). */
  set scrollTop(v: number) { const max = Math.max(0, this.scrollHeight - this.clientHeight); this._scrollTop = Math.max(0, Math.min(Number(v) || 0, max)); }
}
const VOID = new Set(["br", "hr", "img", "input", "meta", "link", "area", "base", "col", "embed", "source", "track", "wbr"]);
const NAMED: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " " };
const decodeEntities = (s: string) => s.replace(/&(#x[0-9a-fA-F]+|#\d+|[a-zA-Z]+);/g, (m, e: string) => {
  if (e[0] === "#") return String.fromCodePoint(parseInt(e[1] === "x" || e[1] === "X" ? e.slice(2) : e.slice(1), e[1] === "x" || e[1] === "X" ? 16 : 10));
  return e in NAMED ? NAMED[e] : m;
});
/** Markup as a tree (the place suite's parser): tags, text, entities; void elements do not nest; a comment is no node. */
function parseHTML(html: string): Array<El | Txt> {
  const root = new El("#root");
  let cur: El = root;
  const re = /<!--[\s\S]*?-->|<\/?([a-zA-Z][\w-]*)([^>]*)>|([^<]+)/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(html))) {
    if (m[0].startsWith("<!--")) continue;
    if (m[3] !== undefined) { cur.appendChild(new Txt(decodeEntities(m[3]))); continue; }
    const tag = m[1].toLowerCase();
    if (m[0][1] === "/") { if (cur.tagName === tag.toUpperCase() && cur.parentNode) cur = cur.parentNode; continue; }
    const el = new El(tag);
    const attrRe = /([\w-]+)(?:="([^"]*)")?/g; let a: RegExpExecArray | null;
    while ((a = attrRe.exec(m[2]))) el.setAttribute(a[1], a[2] === undefined ? "" : decodeEntities(a[2]));
    cur.appendChild(el);
    if (!VOID.has(tag) && !m[2].endsWith("/")) { cur = el; if (tag === "pre" && html[re.lastIndex] === "\n") re.lastIndex++; }
  }
  return root.childNodes.slice();
}
/** Document-order nodes under `root`, as a browser's tree walker answers them (the text nodes; the elements too under
 *  SHOW_ELEMENT, which the link walk asks for to see a <br>). */
function walkNodes(root: El, what: number): Array<El | Txt> {
  const out: Array<El | Txt> = [];
  const walk = (n: El) => { for (const c of n.childNodes) { if (c instanceof Txt) { if (what & 4) out.push(c); } else { if (what & 1) out.push(c); walk(c); } } };
  walk(root);
  return out;
}
const doc = {
  listeners: [] as Reg[],
  body: null as unknown as El,
  head: null as unknown as El,
  hidden: false,
  activeElement: null as El | null,
  createElement: (tag: string) => new El(tag),
  createTextNode: (s: string) => new Txt(s),
  createDocumentFragment: () => new El("#fragment"),
  createTreeWalker: (root: El, what = 4) => { const nodes = walkNodes(root, what); let i = 0; return { nextNode: () => (i < nodes.length ? nodes[i++] : null) }; },
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
(globalThis as any).NodeFilter = { SHOW_ELEMENT: 1, SHOW_TEXT: 4 };
(globalThis as any).location = { protocol: "http:" };
const store = new Map<string, string>();
(globalThis as any).localStorage = {
  getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
  setItem: (k: string, v: string) => { store.set(k, String(v)); },
  removeItem: (k: string) => { store.delete(k); },
};
// the editor chunk the viewer's Edit resolves from (the seam test's stub): a buffer with the two callbacks the viewer wires
const ed = { buf: "", mounted: 0 };
win.__rompEditor = {
  mount(host: El, opts: { text: string; onChange: () => void; onSave: () => void }) {
    ed.buf = opts.text; ed.mounted++;
    host.appendChild(new Txt(opts.text));
    return { value: () => ed.buf, focus() { /* inert */ }, destroy() { /* inert */ } };
  },
};

// ── the kernel's /file, /version and /sessions, as the viewer fetches them ──────────────────────────
type Served = { bytes: string | Uint8Array; type: string; mtimeNs: string };
const disk: Record<string, Served> = {};
(globalThis as any).fetch = async (url: string) => {
  if (url.startsWith("/version")) return { json: async () => ({ fileEditing: true }) };
  if (url.startsWith("/sessions")) return { json: async () => [{ id: SID, name: "api", bg: "#123456", fg: "#ffffff" }] };
  const p = decodeURIComponent((/[?&]path=([^&]*)/.exec(url) || [])[1] || "");
  const f = disk[p];
  const headers = { get: (h: string) => (f ? (h === "Content-Type" ? f.type : h === "X-Romp-Mtime-Ns" ? f.mtimeNs : h === "X-Romp-Text-Utf8" ? "1" : null) : null) };
  if (!f) return { ok: false, status: 404, headers, text: async () => "no such file: " + p };
  return { ok: true, status: 200, headers, text: async () => String(f.bytes), blob: async () => new Blob([f.bytes as unknown as BlobPart], { type: f.type }) };
};

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ROOT = "/repo/notes-api";
const MT = "1757145600000000001";
const MT2 = "1757145600000000002";
const PARA = (i: number) => `Paragraph ${i}: some words of the report, enough to make a line.`;
/** A 41-block note: an h1 and forty paragraphs (block k is paragraph k; block 12 starts at Raw row 24). */
const NOTE = "# Report\n\n" + Array.from({ length: 40 }, (_, i) => PARA(i + 1)).join("\n\n") + "\n";
/** The note with ten paragraphs appended: every block above keeps its span. */
const APPENDED = NOTE + "\n" + Array.from({ length: 10 }, (_, i) => PARA(41 + i)).join("\n\n") + "\n";
/** The note with a sentence added to paragraph 12: the block starts where it did and ends later. */
const GROWN = NOTE.replace(PARA(12), PARA(12) + " And one more sentence the session wrote.");
/** The note with twenty paragraphs put in above the report's own: every block below them moved. */
const INSERTED = "# Report\n\n" + Array.from({ length: 20 }, (_, i) => `Preface ${i + 1}: a paragraph the session put in above.`).join("\n\n") + "\n\n" + NOTE.slice("# Report\n\n".length);
/** The note cut to eight paragraphs: nine blocks, 160px of scroll. */
const SHORT = "# Report\n\n" + Array.from({ length: 8 }, (_, i) => PARA(i + 1)).join("\n\n") + "\n";
/** The note with the twenty paragraphs put in above and its last eight cut: the reader's block moved down and the file's end up
 *  to it, so a seat of the block clamps at the end (53 blocks, 1920px of scroll; paragraph 30 is block 50, at 2000px). */
const INSERTED_CUT = "# Report\n\n" + Array.from({ length: 20 }, (_, i) => `Preface ${i + 1}: a paragraph the session put in above.`).join("\n\n") + "\n\n" + Array.from({ length: 32 }, (_, i) => PARA(i + 1)).join("\n\n") + "\n";
/** The note with a sixty-item list after paragraph 40: one block (the 42nd), sixty Raw rows, so the Raw view's end lies inside it
 *  and its Rendered box, one block tall, cannot show the rows the Raw view had at the edge: the Rendered seat clamps and holds. */
const LISTED = NOTE + "\n" + Array.from({ length: 60 }, (_, i) => `- item ${i + 1}`).join("\n") + "\n";
/** A code file, thirty lines with no blank line: one block to the lexer, thirty Raw rows. */
const PY = Array.from({ length: 30 }, (_, i) => `value_${i + 1} = ${i + 1}`).join("\n") + "\n";
const PLOT = ROOT + "/docs/plot.png";
const NOTE_SPANS = sourceBlockSpans(NOTE);
const notePath = (tag: string) => ROOT + "/docs/report-" + tag + ".md";

// ── the module, its host and its probe ─────────────────────────────────────────────────────────────
type Leave = { path: string; sid: string | null; rec: RememberedPlace };
const leaves: Leave[] = [];
const posted: any[] = [];
let fvMod: typeof import("./file-view") | null = null;
async function mod(): Promise<typeof import("./file-view")> {
  if (fvMod) return fvMod;
  fvMod = await import("./file-view");
  fvMod.initFileView((m) => posted.push(m), undefined, { onLeave: (path, sid, rec) => { leaves.push({ path, sid, rec }); } });
  fvMod.setFileViewIdentity((sid) => (sid === SID ? { name: "api", color: { bg: "#123456", fg: "#ffffff" } } : null));
  return fvMod;
}
const settle = async () => { for (let i = 0; i < 8; i++) await new Promise<void>((r) => setImmediate(r)); };
type Open = { fv: typeof import("./file-view"); wrap: El; body: El };
/** Serve `text` at `p` (mtime `mt`) and open it with the REAL openFileView; `raw`: the stored preference says Raw for a
 *  markdown file (every open otherwise starts from the default, Rendered). The open's paint has landed when it returns. */
async function open(p: string, text: string | Uint8Array, t: TestContext, opts?: { at?: At | null; place?: RememberedPlace | null }, raw = false, mt = MT): Promise<Open> {
  const fv = await mod();
  disk[p] = { bytes: text, type: typeof text === "string" ? "text/plain; charset=utf-8" : "image/png", mtimeNs: mt };
  store.delete("romp:fileviewFmt");
  if (raw) store.set("romp:fileviewFmt", JSON.stringify({ md: "raw" }));
  assert.equal(fv.openFileView(p, SID, opts), true, "the open happened");
  t.after(() => { fv.closeFileView(); });
  await settle();
  return current(fv);
}
const current = (fv: typeof import("./file-view")): Open => {
  const wrap = doc.getElementById("romp-fileview")!;
  assert.ok(wrap, "the viewer is up");
  return { fv, wrap, body: wrap.querySelector(".fileview-body")! };
};
/** Re-open through the module (a replace-open) and wait for the paint. */
async function reopen(fv: typeof import("./file-view"), p: string, opts?: { at?: At | null; place?: RememberedPlace | null }): Promise<Open> {
  assert.equal(fv.openFileView(p, SID, opts), true, "the re-open happened");
  await settle();
  return current(fv);
}
const blocks = (o: Open): El[] => { const md = o.body.querySelector(".fileview-md"); assert.ok(md, "the Rendered view is up"); return md!.children; };
const rows = (o: Open): El[] => { const code = o.body.querySelector("code.hljs"); assert.ok(code, "the Raw view is up"); return code!.children.filter((c) => c.classes.includes("fv-cl")); };
/** The block or row at the body's top edge, by the layout: its rect top less the edge. */
const topOf = (el: El): number => el.getBoundingClientRect().top - EDGE;
const btn = (o: Open, label: string): El => { const b = o.wrap.querySelector(".fileview-acts")!.querySelectorAll("button").find((x) => x.textContent === label); assert.ok(b, "the " + label + " button"); return b!; };
const FIXTURE_WORDS = ["Paragraph", "Preface", "Report", "words", "report", "line", "value_"];

// ── the record and its two pure functions ─────────────────────────────────────────────────────────
test("rememberedPlaceOf keeps the place's span, offset, flag and view with the mtime, the scrollTop and the time, and no text; placeFromRemembered gives a Place over the new text when a block of it starts where the remembered one did (an edit inside or below the block keeps that), null when the text above moved it or the file ends before it", async () => {
  const { rememberedPlaceOf, placeFromRemembered } = await mod();
  const s12 = NOTE_SPANS[12];
  const place: Place = { source: NOTE, view: "rendered", start: s12.start, end: s12.end, top: -10, height: BLOCK_BOX, atTop: false, prev: NOTE_SPANS[11], next: NOTE_SPANS[13], line: { start: s12.start, end: s12.end, top: -10 } };
  const before = Date.now();
  const rec = rememberedPlaceOf(place, MT, 490);
  assert.deepEqual(Object.keys(rec).sort(), ["atTop", "end", "mtimeNs", "scrollTop", "start", "t", "top", "view"], "the eight fields and no other");
  assert.deepEqual({ ...rec, t: 0 }, { start: s12.start, end: s12.end, top: -10, atTop: false, view: "rendered", mtimeNs: MT, scrollTop: 490, t: 0 });
  assert.ok(rec.t >= before && rec.t <= Date.now(), "t is when the record was made");
  const json = JSON.stringify(rec);
  for (const w of FIXTURE_WORDS) assert.ok(!json.includes(w), "the record carries no word of the file: " + w);
  assert.ok(!("source" in rec) && !("prev" in rec) && !("line" in rec), "nor the place's source, neighbours or line");
  // back over the same text: the block, the record's offset and flag, no height, no neighbours
  assert.deepEqual(placeFromRemembered(rec, NOTE), { source: NOTE, view: "rendered", start: s12.start, end: s12.end, top: -10, height: 0, atTop: false, prev: null, next: null });
  // an edit below the block (APPENDED) or inside it (GROWN) keeps its start: the same block, with its span as the new text has it
  assert.deepEqual(placeFromRemembered(rec, APPENDED)!.end, s12.end);
  const grown = placeFromRemembered(rec, GROWN)!;
  assert.equal(grown.start, s12.start); assert.equal(grown.end, sourceBlockSpans(GROWN)[12].end); assert.ok(grown.end > s12.end, "the block grew");
  assert.equal(grown.source, GROWN, "a Place over the NEW text");
  // text put in above moved every block below it: no block of the new text starts where the remembered one did, and the old
  // source is not kept to follow it (the numeric scrollTop is the caller's fallback); a file that ends before the span too
  assert.equal(placeFromRemembered(rec, INSERTED), null);
  assert.equal(placeFromRemembered(rec, SHORT), null);
  assert.equal(placeFromRemembered(rec, ""), null, "an empty text has no block");
  // the flag rides through: a body that stood at its very top comes back to it
  const top = rememberedPlaceOf({ ...place, top: 0, atTop: true, start: 0, end: NOTE_SPANS[0].end }, MT, 0);
  assert.equal(placeFromRemembered(top, NOTE)!.atTop, true);
  // the Raw view's record names the same block: the place is in the file's terms
  assert.equal(placeFromRemembered({ ...rec, view: "raw" }, NOTE)!.view, "raw");
});

// ── the write at the close, and the seat at the next open ────────────────────────────────────────
test("closing a scrolled note hands the host one record (the top block's span, its offset, the view, the mtime, the scrollTop; no text) at the cost of one layout read; the next open of the path seats the block where it stood, to the pixel, with nothing scrolled into view; a record handed in as `place` seats a path the memory has not seen; of the host's record and the memory's, the later wins", async (t) => {
  const P = notePath("close");
  const o = await open(P, NOTE, t);
  assert.equal(blocks(o).length, 41, "the stand-in rendered the note's blocks");
  assert.equal(o.body.scrollTop, 0, "a first open starts at the top");
  o.body.scrollTop = 490;                                  // 10px into paragraph 12 (block 12 spans 480 to 512)
  assert.equal(topOf(blocks(o)[12]), -10);
  const n0 = leaves.length, reads0 = o.body.rectReads;
  o.fv.closeFileView();
  assert.equal(doc.getElementById("romp-fileview"), null, "closed");
  assert.equal(leaves.length, n0 + 1, "one record");
  assert.equal(o.body.rectReads - reads0, 1, "the leave read the body's box once (one readPlace, never one per frame)");
  const { path: lp, sid, rec } = leaves[n0];
  assert.equal(lp, P); assert.equal(sid, SID);
  assert.deepEqual({ ...rec, t: 0 }, { start: NOTE_SPANS[12].start, end: NOTE_SPANS[12].end, top: -10, atTop: false, view: "rendered", mtimeNs: MT, scrollTop: 490, t: 0 });
  for (const w of FIXTURE_WORDS) assert.ok(!JSON.stringify(rec).includes(w), "no text in the record: " + w);
  // the same path again, no target: the block back where it stood, inside the first paint
  const r = await reopen(o.fv, P);
  assert.equal(r.body.scrollTop, 490, "the scrollTop is the remembered one");
  assert.equal(topOf(blocks(r)[12]), -10, "paragraph 12 at the same depth");
  assert.equal(blocks(r).reduce((n, b) => n + b.scrolled, 0), 0, "nothing was scrolled into view: the seat is a scrollTop write");
  // a path the memory has not seen, with the host's record as `place`: the same seat (the Files pane's Recent row)
  disk[notePath("close-copy")] = { bytes: NOTE, type: "text/plain; charset=utf-8", mtimeNs: MT };
  const p2 = await reopen(o.fv, notePath("close-copy"), { place: rec });
  assert.equal(p2.body.scrollTop, 490);
  // the host's record against the memory's for one path: the later read wins, whichever side it came from
  const at3 = { ...rec, start: NOTE_SPANS[3].start, end: NOTE_SPANS[3].end, top: 0, scrollTop: 120 };
  const older = await reopen(o.fv, P, { place: { ...at3, t: 1 } });
  assert.equal(older.body.scrollTop, 490, "an older host record yields to the memory's");
  const newer = await reopen(o.fv, P, { place: { ...at3, t: Date.now() + 1e6 } });
  assert.equal(newer.body.scrollTop, 120, "a newer host record wins: paragraph 3 at the edge");
  assert.equal(topOf(blocks(newer)[3]), 0);
  const none = await reopen(o.fv, P, { place: null });
  assert.equal(none.body.scrollTop, 120, "null is no record: the memory stands (the last leave was at 120)");
});

// ── the replace path: the old file's place written, the new file's read ─────────────────────────────
test("opening another file over a scrolled one writes the first file's record before its body goes and reads the second's; a Raw code file's place (one block, the depth in rows) comes back the same way", async (t) => {
  const P = notePath("replace"), APP = ROOT + "/src/app-replace.py";
  const o = await open(P, NOTE, t);
  o.body.scrollTop = 490;
  const n0 = leaves.length;
  disk[APP] = { bytes: PY, type: "text/plain; charset=utf-8", mtimeNs: MT };
  const a = await reopen(o.fv, APP);
  assert.equal(leaves.length, n0 + 1); assert.equal(leaves[n0].path, P); assert.equal(leaves[n0].rec.scrollTop, 490);
  assert.equal(rows(a).length, 30, "the code file's rows"); assert.equal(a.body.scrollTop, 0, "the code file was never left: its top");
  a.body.scrollTop = 200;                                  // row 10 at the edge, 200px into the file's one block
  const back = await reopen(o.fv, P);
  assert.equal(leaves.length, n0 + 2); assert.equal(leaves[n0 + 1].path, APP);
  assert.deepEqual({ ...leaves[n0 + 1].rec, t: 0 }, { start: 0, end: sourceBlockSpans(PY)[0].end, top: -200, atTop: false, view: "raw", mtimeNs: MT, scrollTop: 200, t: 0 }, "the code file's record: one block, 200px in");
  assert.equal(back.body.scrollTop, 490, "the note is back where it was");
  const again = await reopen(o.fv, APP);
  assert.equal(again.body.scrollTop, 200, "the code file too: the block's top at the edge, then the depth in pixels");
  assert.equal(topOf(rows(again)[10]), 0, "row 11 at the edge");
});

// ── a changed file ────────────────────────────────────────────────────────────────────────────────
test("a file that changed since it was left: paragraphs appended below, or a sentence added to the block itself, keep the block's start and it is seated by span at the record's depth (the new mtime rides into the next record); paragraphs put in above move every block and the numeric scrollTop stands in, clamped by a shorter file", async (t) => {
  const P = notePath("changed");
  const o = await open(P, NOTE, t);
  o.body.scrollTop = 490;
  o.fv.closeFileView();
  const rec = leaves[leaves.length - 1].rec;
  assert.equal(rec.mtimeNs, MT);
  // appended below: the same span, 10px in
  disk[P] = { bytes: APPENDED, type: "text/plain; charset=utf-8", mtimeNs: MT2 };
  const a = await reopen(o.fv, P);
  assert.equal(blocks(a).length, 51); assert.equal(a.body.scrollTop, 490); assert.equal(topOf(blocks(a)[12]), -10);
  o.fv.closeFileView();
  const rec2 = leaves[leaves.length - 1].rec;
  assert.equal(rec2.mtimeNs, MT2, "the next record carries the file's new mtime"); assert.equal(rec2.start, NOTE_SPANS[12].start);
  // the block grew: still the block that starts there
  disk[P] = { bytes: GROWN, type: "text/plain; charset=utf-8", mtimeNs: "1757145600000000003" };
  const g = await reopen(o.fv, P);
  assert.equal(g.body.scrollTop, 490); assert.equal(topOf(blocks(g)[12]), -10);
  o.fv.closeFileView();
  assert.equal(leaves[leaves.length - 1].rec.end, sourceBlockSpans(GROWN)[12].end, "the record now names the grown block's span");
  // text above: the span is no block of this text; the number is written (the file is long enough to take it)
  const { placeFromRemembered } = o.fv;
  assert.equal(placeFromRemembered(leaves[leaves.length - 1].rec, INSERTED), null, "the fixture: no block of the new text starts at the old offset");
  disk[P] = { bytes: INSERTED, type: "text/plain; charset=utf-8", mtimeNs: "1757145600000000004" };
  const i = await reopen(o.fv, P);
  assert.equal(blocks(i).length, 61); assert.equal(i.body.scrollTop, 490, "the numeric scrollTop, as the record had it");
  o.fv.closeFileView();
  assert.equal(leaves[leaves.length - 1].rec.start, sourceBlockSpans(INSERTED)[12].start, "the block at that scrollTop is the twelfth of the new text (a preface), not paragraph 12 followed down the file");
  // …and clamped when the file got shorter than the number
  disk[P] = { bytes: SHORT, type: "text/plain; charset=utf-8", mtimeNs: "1757145600000000005" };
  const s = await reopen(o.fv, P);
  assert.equal(blocks(s).length, 9);
  assert.equal(s.body.scrollTop, 9 * BLOCK_H - BODY_H, "clamped to the end of the shorter file (160px)");
});

// ── the view the record was read in against the view of the open ────────────────────────────────────
test("a record read in the Rendered view seats by span under the Raw preference (the block's first row at the edge: the depth is not carried across views), and one read in Raw seats its block in Rendered; an open with a target lands on the target and ignores the memory, and its leave still writes", async (t) => {
  const P = notePath("views");
  const o = await open(P, NOTE, t);
  o.body.scrollTop = 490;
  o.fv.closeFileView();
  // the Raw preference: paragraph 12 is Raw row 24 (the h1, a blank, then two rows per paragraph)
  store.set("romp:fileviewFmt", JSON.stringify({ md: "raw" }));
  const r = await reopen(o.fv, P);
  assert.equal(rows(r).length, 81, "the Raw rows");
  assert.equal(r.body.scrollTop, 24 * ROW_H, "row 25, paragraph 12's, at the edge");
  assert.equal(topOf(rows(r)[24]), 0);
  store.delete("romp:fileviewFmt");
  // a `{ line }` target: the Raw view for this open, the row centred, the memory (row 24 at the edge) not applied
  const n0 = leaves.length;
  const l = await reopen(o.fv, P, { at: { line: 25 } });
  assert.equal(leaves[n0].rec.view, "raw", "the Raw view's leave wrote its record");
  assert.ok(rows(l).length === 81 && rows(l)[24].scrolled === 1, "the target's row was scrolled into view");
  assert.equal(l.body.scrollTop, 0, "the memory stood aside for the target (the stand-in's scrollIntoView moves no scrollTop)");
  l.body.scrollTop = 200;                                  // row 10, paragraph 5's, at the edge
  o.fv.closeFileView();
  const rec = leaves[leaves.length - 1].rec;
  assert.deepEqual({ ...rec, t: 0 }, { start: NOTE_SPANS[5].start, end: NOTE_SPANS[5].end, top: 0, atTop: false, view: "raw", mtimeNs: MT, scrollTop: 200, t: 0 }, "the leave after a targeted open writes as any leave does");
  // …and that Raw record seats paragraph 5 in the Rendered view (the preference was not saved by the targeted open)
  const back = await reopen(o.fv, P);
  assert.equal(back.body.scrollTop, 5 * BLOCK_H, "paragraph 5's block at the edge");
  assert.equal(topOf(blocks(back)[5]), 0);
});

// ── pagehide writes without retiring the viewer; editing writes the place read at Edit; media writes nothing ──
test("the window's pagehide writes the record with the viewer still up, and the close writes again; while the editor holds the body the leave writes the place of the text view Edit replaced, read at Edit (review round 2: before, nothing was written and the reopen fell to the top), and the reopen the reader then gets paints Raw, the preference Edit saved, with the block's first row at the edge, a Rendered reopen after that Raw round trip seating the block at the edge (review round 3); a picture and a missing file write nothing", async (t) => {
  const P = notePath("pagehide");
  const o = await open(P, NOTE, t);
  o.body.scrollTop = 490;
  const n0 = leaves.length;
  win.dispatchEvent(new Event("pagehide"));
  assert.equal(leaves.length, n0 + 1); assert.equal(leaves[n0].path, P); assert.equal(leaves[n0].rec.scrollTop, 490);
  assert.ok(doc.getElementById("romp-fileview"), "the viewer is still up (the page may come back from the cache)");
  o.body.scrollTop = 530;
  o.fv.closeFileView();
  assert.equal(leaves.length, n0 + 2); assert.equal(leaves[n0 + 1].rec.scrollTop, 530, "the close writes the place as it stands now");
  const back = await reopen(o.fv, P);
  assert.equal(back.body.scrollTop, 530, "the later record is the memory's");
  o.fv.closeFileView();
  // editing: the buffer is not the text, so the leave writes the place of the text view Edit replaced, read at Edit (before the
  // review's round 2 it wrote nothing: a first read closed from the editor was forgotten, a re-read fell to the read before it)
  const E = notePath("editing");
  const e = await open(E, NOTE, t);
  e.body.scrollTop = 490;
  btn(e, "Edit").click();
  await settle();
  assert.ok(e.body.querySelector(".fileview-cm"), "the editor holds the body");
  const n1 = leaves.length;
  win.dispatchEvent(new Event("pagehide"));
  assert.equal(leaves.length, n1 + 1, "a page hidden while editing writes the pre-Edit place");
  assert.equal(leaves[n1].rec.scrollTop, 490); assert.equal(leaves[n1].rec.view, "rendered", "…of the view the reader read, before Edit's Raw switch");
  assert.deepEqual({ ...leaves[n1].rec, t: 0 }, { start: NOTE_SPANS[12].start, end: NOTE_SPANS[12].end, top: -10, atTop: false, view: "rendered", mtimeNs: MT, scrollTop: 490, t: 0 }, "block 12, ten pixels in");
  e.fv.closeFileView();
  assert.equal(doc.getElementById("romp-fileview"), null, "closed (no unsaved change: no ask)");
  assert.equal(leaves.length, n1 + 2, "the close from the editor writes it too (before: no record while editing)");
  assert.equal(leaves[n1 + 1].rec.scrollTop, 490);
  // Edit saved the Raw preference (markdown edits from its Raw view), so the reopen the reader gets paints Raw over the
  // Rendered record: the other view's seat (case 5), the block's first row at the edge and the ten pixels not carried
  // across views (review round 3: before, the case cleared the preference and measured a Rendered reopen no reader gets)
  assert.equal(JSON.parse(store.get("romp:fileviewFmt") || "{}").md, "raw", "Edit saved the Raw preference");
  const e2 = await reopen(e.fv, E);
  assert.equal(e2.body.querySelector(".fileview-md"), null, "the Raw view, not the one the record was read in");
  assert.equal(rows(e2).length, 81);
  assert.equal(e2.body.scrollTop, 24 * ROW_H, "paragraph 12's first row at the edge (before the round 2 fix: the top, nothing remembered for the path)");
  assert.equal(topOf(rows(e2)[24]), 0);
  assert.ok(rows(e2)[24].textContent.startsWith("Paragraph 12:"), "the row is the block's first");
  // the Raw close writes the record in Raw's terms (block 12, its first row at the edge), so a Rendered reopen after the
  // Raw round trip seats the block at the edge: the depth read before Edit went with the round trip
  e.fv.closeFileView();
  assert.deepEqual({ ...leaves[n1 + 2].rec, t: 0 }, { start: NOTE_SPANS[12].start, end: NOTE_SPANS[12].end, top: 0, atTop: false, view: "raw", mtimeNs: MT, scrollTop: 24 * ROW_H, t: 0 }, "the Raw record");
  store.set("romp:fileviewFmt", JSON.stringify({ md: "rendered" }));
  const e3 = await reopen(e.fv, E);
  assert.equal(e3.body.scrollTop, 12 * BLOCK_H, "block 12 at the edge, the ten pixels gone");
  assert.equal(topOf(blocks(e3)[12]), 0);
  e.fv.closeFileView();
  store.delete("romp:fileviewFmt");
  // a picture: no text view, no record; a missing file: the failure pane, no record
  const pic = await open(PLOT, new Uint8Array([0x89, 0x50, 0x4e, 0x47]), t);
  const n2 = leaves.length;
  pic.fv.closeFileView();
  assert.equal(leaves.length, n2, "a picture writes no record");
  assert.equal(pic.fv.openFileView(ROOT + "/docs/missing.md", SID), true);
  await settle();
  pic.fv.closeFileView();
  assert.equal(leaves.length, n2, "a fetch failure writes no record");
});

// ── the key: a relative path is one file per session ───────────────────────────────────────────────
test("the memory's key (review round 2): a RELATIVE path carries the session, since the kernel resolves it against the session's cwd and two sessions' docs/report.md are two files (before: session B's file, never read here, opened at session A's place); an absolute or ~ path is one file for every session and its key stays the path; placeKey says so", async (t) => {
  const fv = await mod();
  const SID_B = "22222222-3333-4444-5555-666666666666";
  assert.equal(fv.placeKey("/repo/notes-api/docs/report.md", SID), "/repo/notes-api/docs/report.md", "an absolute path: the path alone");
  assert.equal(fv.placeKey("~/notes/report.md", SID), "~/notes/report.md", "a ~ path: the kernel expands it for every session alike");
  assert.equal(fv.placeKey("docs/report.md", SID), "docs/report.md\u0000" + SID, "a relative path: the session folded in");
  assert.equal(fv.placeKey("docs/report.md", null), "docs/report.md\u0000", "…with no session, an empty one (still apart from the absolute spelling)");
  // session A reads the relative path to block 12 and closes; session B's open of the same relative path is another file: the top
  const REL = "docs/report-rel.md";
  const a = await open(REL, NOTE, t);
  a.body.scrollTop = 490;
  a.fv.closeFileView();
  assert.equal(fv.openFileView(REL, SID_B), true, "session B's open happened"); await settle();
  const b = current(fv);
  assert.equal(b.body.scrollTop, 0, "session B's file, never read here, opens at its top (before the fix: at session A's place, 490)");
  b.body.scrollTop = 200;
  fv.closeFileView();
  // …and each session's own place stands
  const a2 = await reopen(fv, REL);
  assert.equal(a2.body.scrollTop, 490, "session A's reopen returns to A's place (before the fix: B's newer record, 200, won the path's one key)");
  fv.closeFileView();
  assert.equal(fv.openFileView(REL, SID_B), true); await settle();
  assert.equal(current(fv).body.scrollTop, 200, "session B's reopen returns to B's");
  fv.closeFileView();
  // the host hears the leave with the path as written and the session, as before
  const last = leaves[leaves.length - 1];
  assert.equal(last.path, REL); assert.equal(last.sid, SID_B);
  // an absolute path: one file for every session, so the key is shared and B's open seats A's place
  const ABS = notePath("shared");
  const s1 = await open(ABS, NOTE, t);
  s1.body.scrollTop = 330;
  s1.fv.closeFileView();
  assert.equal(fv.openFileView(ABS, SID_B), true); await settle();
  assert.equal(current(fv).body.scrollTop, 330, "the absolute path's place is shared across sessions (the same bytes are the same file)");
  fv.closeFileView();
});

// ── the source: where the write and the seat sit ─────────────────────────────────────────────────
// ── the visible leave after a reload whose seat clamped (review closing pass) ─────────────────────────────────────
test("a reload whose seat the browser CLAMPS (the session's write moved the reader's block down and the file's end up to it: the block wants more scroll than the new view has) holds the place read before the swap, in the OLD text's terms (seat's hold, the Slice 3 round trip), and the visible leave after it, the pagehide or a close with the body standing where the clamp left it, writes that block followed into the text that landed, at its mtime (review closing pass: through keptPlace's held arm it wrote the old text's offset under the new mtime, a record that claimed exactness and named an offset no block of the new text starts at, so the reopen fell to the numeric scrollTop; the mirror of round 6's boxless defect); a reload seated without a clamp writes the block read anew over the new body, before and after", async (t) => {
  const fv = await mod();
  const probe: { seam: { reload(): void; mtimeNs(): string } | null } = { seam: null };   // a holder: the mount below assigns it, which a bare `let` would not carry past the assignment
  fv.registerFileViewAction({ id: "closing-pass-seam", mount: (ctx) => { probe.seam = ctx; return null; } });   // the seam, for the reload the Comments panel's poll calls (registered once; every later open mounts it, adding no node)
  const P = notePath("clamped-reload");
  const o = await open(P, NOTE, t);
  assert.ok(probe.seam, "the probe mounted");
  o.body.scrollTop = 30 * BLOCK_H;   // paragraph 30 (block 30) at the edge
  assert.equal(topOf(blocks(o)[30]), 0);
  // the session's write lands through the seam's reload (the panel's poll): twenty paragraphs above the reader's block, the last eight gone
  disk[P] = { bytes: INSERTED_CUT, type: "text/plain; charset=utf-8", mtimeNs: MT2 };
  probe.seam!.reload(); await settle();
  assert.equal(probe.seam!.mtimeNs(), MT2, "the reload landed");
  const spans = sourceBlockSpans(INSERTED_CUT);
  assert.equal(spans.length, 53); assert.equal(blocks(o).length, 53);
  const max = 53 * BLOCK_H - BODY_H;
  assert.equal(o.body.scrollTop, max, "the seat clamped: paragraph 30, block 50 of the new text, wants " + 50 * BLOCK_H + " and the body ends at " + max);
  assert.equal(topOf(blocks(o)[50]), 50 * BLOCK_H - max, "paragraph 30 stands 80px below the edge, where the clamp left it");
  assert.ok(blocks(o)[50].textContent.startsWith("Paragraph 30:"));
  const n0 = leaves.length;
  win.dispatchEvent(new Event("pagehide"));
  assert.equal(leaves.length, n0 + 1, "the pagehide wrote a record");
  const rec = leaves[n0].rec;
  assert.equal(rec.mtimeNs, MT2, "at the landed file's mtime");
  assert.equal(rec.start, spans[50].start, "the record names paragraph 30's block in the text that landed (before the fix: " + NOTE_SPANS[30].start + ", the old text's offset, at which no block of the new text starts)");
  assert.equal(rec.end, spans[50].end);
  assert.deepEqual([rec.top, rec.view, rec.scrollTop], [0, "rendered", max], "with the depth as read before the swap, the view, and the clamp's scrollTop");
  assert.ok(o.fv.placeFromRemembered(rec, INSERTED_CUT), "a block of the new text starts at the record's offset, so the reopen seats by span");
  o.fv.closeFileView();
  assert.equal(leaves.length, n0 + 2);
  assert.equal(leaves[n0 + 1].rec.start, spans[50].start, "the close writes the same block");
  // the reopen seats the block and clamps at the same end the reader saw
  const back = await reopen(o.fv, P);
  assert.equal(back.body.scrollTop, max); assert.ok(blocks(back)[50].textContent.startsWith("Paragraph 30:"));
  o.fv.closeFileView();
  // control: the write with the file long enough below the block seats without a clamp, and the leave reads the body anew
  const C = notePath("followed-reload");
  const c = await open(C, NOTE, t);
  c.body.scrollTop = 30 * BLOCK_H;
  disk[C] = { bytes: INSERTED, type: "text/plain; charset=utf-8", mtimeNs: MT2 };
  probe.seam!.reload(); await settle();
  assert.equal(probe.seam!.mtimeNs(), MT2);
  assert.equal(c.body.scrollTop, 50 * BLOCK_H, "seated, not clamped: paragraph 30 back at the edge");
  const n1 = leaves.length;
  c.fv.closeFileView();
  assert.equal(leaves[n1].rec.start, sourceBlockSpans(INSERTED)[50].start, "the followed block, read anew");
});

// ── the unread-scroll flag falls with the measurement it stands in for (review closing pass) ─────────────────────
test("scrollUnread, the flag a scroll's frame read sets when it finds the body with no box, is cleared by the measurement it stands in for, a read of the place or a clamped seat's hold, so a flag set while the show's repaint stood down (the editor holding the body) never makes a later show read a scroll that did not happen (review closing pass: only the repaint cleared it, past its early returns, so the stale flag made the show after a clamped Rendered seat read the block the clamp shows in place of the held passage, and the swap back to Raw landed that block's first row, 1160px above the rows the reader had)", async (t) => {
  // the body's width report, through a ResizeObserver stand-in the case reports through (the viewer's repaint is keyed on it; with
  // no requestAnimationFrame the report itself is the frame, and the scroll listener reads at the event)
  const observers: Array<{ cb: (entries: unknown[]) => void; targets: unknown[] }> = [];
  (globalThis as any).ResizeObserver = class {
    private rec: { cb: (entries: unknown[]) => void; targets: unknown[] };
    constructor(cb: (entries: unknown[]) => void) { this.rec = { cb, targets: [] }; observers.push(this.rec); }
    observe(el: unknown): void { this.rec.targets.push(el); }
    disconnect(): void { /* inert */ }
  };
  t.after(() => { delete (globalThis as any).ResizeObserver; });
  const P = notePath("stale-flag");
  const o = await open(P, LISTED, t);
  // the pane's hide and show: no rects and a width of 0 under the hide, and the width hook's report of each
  let hidden = false;
  (o.body as any).getClientRects = () => (hidden ? [] : [rect(EDGE, BODY_H)]);
  Object.defineProperty(o.body, "clientWidth", { get: () => (hidden ? 0 : BODY_W), configurable: true });
  const report = () => { for (const ob of observers) if (ob.targets.includes(o.body)) ob.cb([{ contentRect: { width: hidden ? 0 : BODY_W } }]); };
  report();   // the first report describes the size at observe(), not a change
  const maxRendered = 42 * BLOCK_H - BODY_H, maxRaw = 142 * ROW_H - BODY_H;
  assert.equal(blocks(o).length, 42);
  // the editor holds the body; the pane is hidden in the task of a scroll, whose read finds no box (the flag), and shown again: the
  // show's repaint stands down under the editor and the flag stays
  btn(o, "Edit").click(); await settle();
  assert.ok(o.body.querySelector(".fileview-cm"), "the editor holds the body");
  hidden = true; dispatch(o.body, new Ev("scroll")); report();
  hidden = false; report();
  // Cancel: the exit paints Raw (the preference Edit saved) at the top, a measured read
  btn(o, "Cancel").click(); await settle();
  assert.equal(rows(o).length, 142, "the Raw view, 142 rows");
  assert.equal(o.body.scrollTop, 0);
  // the reader scrolls to the Raw view's end, inside the list, and swaps to Rendered: the list's one block cannot show its rows, the
  // seat clamps at the Rendered end and holds the Raw place (seat)
  o.body.scrollTop = maxRaw; dispatch(o.body, new Ev("scroll"));
  assert.equal(topOf(rows(o)[132]), 0); assert.ok(rows(o)[132].textContent.startsWith("- item 51"), "item 51 at the edge");
  btn(o, "Rendered").click(); await settle();
  assert.equal(o.body.scrollTop, maxRendered, "clamped at the Rendered end");
  assert.equal(topOf(blocks(o)[37]), 0, "paragraph 37 at the edge, the clamp's landing; the list block below the view");
  // the pane hidden and shown with no scroll: the show's repaint seats the held place again (before the fix: the stale flag read the
  // clamp's landing as the reader's place and dropped the hold)
  hidden = true; report();
  hidden = false; report();
  assert.equal(o.body.scrollTop, maxRendered);
  // the swap back to Raw seats the reader's own rows
  btn(o, "Raw").click(); await settle();
  assert.equal(o.body.scrollTop, maxRaw, "item 51's row back at the edge (before the fix: paragraph 37's first row, " + 37 * 2 * ROW_H + ")");
  assert.ok(rows(o)[132].textContent.startsWith("- item 51"));
  // and the leave writes the list block, the reader's passage
  const n0 = leaves.length;
  o.fv.closeFileView();
  assert.equal(leaves[n0].rec.start, sourceBlockSpans(LISTED)[41].start, "the record names the list block");
  assert.equal(leaves[n0].rec.view, "raw");
});

test("file-view.ts: runLeave runs once the close guard has passed in closeFileView and both replace paths (three sites), landRemembered runs right after the first paint's own seat in both text branches, the leave writes the place read at Edit while the editor is up and stands down without a text view, pagehide runs the live write without retiring it, and the option and the host type carry RememberedPlace", () => {
  const closeFn = VIEW.split("export function closeFileView")[1].split("/** Show `path`")[0];
  const openFn = VIEW.split("export function openFileView")[1].split("function offersDownload")[0];
  const urlFn = VIEW.split("export function openUrlView")[1].split("// Kick the browser's downloader")[0];
  assert.match(closeFn, /if \(closeGuard && !closeGuard\(\)\) return;[^\n]*\n\s*closeGuard = null;\n\s*closeAsks = \[\];\n\s*runLeave\(\);[^\n]*\n\s*editHooks = null;/, "the close: once the guard has passed, before anything the body needs is dropped");
  assert.match(openFn, /&& closeGuard && !closeGuard\(\)\) return false;\n\s*closeGuard = null;\n\s*closeAsks = \[\];\n\s*const priorRing = ringInOld\([^\n]*\n\s*runLeave\(\);[^\n]*\n\s*editHooks = null;/, "the file replace path (the old holder's ring read between the guard and the leave since the review's round 4)");
  assert.match(urlFn, /&& closeGuard && !closeGuard\(\)\) return;\n\s*closeGuard = null;\n\s*runLeave\(\);[^\n]*\n\s*editHooks = null;/, "the URL replace path");
  assert.equal((VIEW.match(/runLeave\(\);/g) || []).length, 3, "the three exits and no other caller");
  assert.match(VIEW, /function runLeave\(\): void \{ const f = leaveLive; leaveLive = null; if \(f\) f\(\); \}/, "an exit retires the write it runs");
  const initFn = VIEW.split("export function initFileView(")[1].split("\nexport function ")[0];
  assert.match(initFn, /window\.addEventListener\("pagehide", \(\) => \{ if \(leaveLive\) leaveLive\(\); \}\);/, "pagehide runs it and keeps it, installed once with the module's other window listeners");
  assert.equal((VIEW.match(/"pagehide"/g) || []).length, 1, "one listener");
  assert.equal((openFn.match(/seat\(kept\);[^\n]*\n\s*landRemembered\(\);/g) || []).length, 2, "the remembered seat follows the paint's own seat in the SVG Source branch and the text branch");
  assert.match(openFn, /const memKey = placeKey\(path, sid\);[^\n]*\n\s*let pendingPlace: RememberedPlace \| null = at === null \? newerPlace\(opts\?\.place, rememberedPlaces\.get\(memKey\)\) : null;/, "a target stands the memory down; else the later of the host's and the memory's, read by the file's key (placeKey: the path, and the session for a relative path)");
  assert.match(openFn, /const landRemembered = \(\) => \{\n\s*if \(pendingPlace === null \|\| shownText === null\) return;\n(?:\s*\/\/[^\n]*\n)*\s*if \(unmeasurable\(\)\) return;\n\s*const rec = pendingPlace; pendingPlace = null;/, "spent once, at a text paint over a body that has a box (a paint under a hidden pane keeps it for the width hook's repaint at the show; the review's round 4)");
  assert.match(openFn, /const measuredPlace = \(\): Place \| null => \{\n\s*if \(!place \|\| shownText === null \|\| place\.source === shownText\) return place;\n\s*const spans = sourceBlockSpans\(shownText\);\n\s*const \{ at, step \} = followPlace\(place, shownText\);\n\s*const found = blockIndexAt\(spans, at\);\n\s*if \(found < 0\) return null;\n\s*const b = Math\.max\(0, Math\.min\(spans\.length - 1, found \+ step\)\);\n\s*return \{ \.\.\.place, source: shownText, start: spans\[b\]\.start, end: spans\[b\]\.end, prev: null, next: null, line: null, row: null, after: undefined, pic: null, lead: null \};\n\s*\};/, "the last measured place, followed into the text that shows when a reload landed under a boxless body (the paint's seat could read nothing there, so `place` still names its block in the text it was read from): the block followPlace puts the reader's block at, stepped to its neighbour when the write rewrote it, as the seat steps; null when no block stands at or before it (review round 6: the boxless leave wrote the old text's span under the new mtime)");
  assert.match(openFn, /const liveRecord = \(\): RememberedPlace \| null => \{\n\s*if \(shownText === null \|\| !textShowing\(\)\) return null;\n(?:\s*\/\/[^\n]*\n)*\s*const boxless = unmeasurable\(\);\n\s*const p = boxless \|\| held\(\) \? measuredPlace\(\) : readPlace\(body, shownText\);\n\s*if \(!p\) return null;\n\s*const rec = rememberedPlaceOf\(p, mtimeNs, boxless \? placeScrollTop : body\.scrollTop\);\n\s*const folds = openFoldOrdinals\(body\) \?\? heldFolds\(\);[^\n]*\n\s*return folds \? \{ \.\.\.rec, folds \} : rec;\n\s*\};/, "the live record: a non-text body writes nothing; one keptPlace read, or the place as last measured with its scrollTop under a body with no box (review round 5: a leave under a hidden pane wrote nothing), followed into the text a reload landed under the hide (round 6), and so is a clamped seat's held place, read over the old text before a reload's swap (the closing pass); the Rendered view's open folds ride on it by ordinal, else the folds a Raw first paint holds for a Rendered paint that has not come (round 5), absent when there is nothing to record (review round 3)");
  assert.match(openFn, /leaveLive = \(\) => \{\n\s*const rec = editing \? editPlace : liveRecord\(\);\n\s*if \(!rec\) return;\n\s*rememberedPlaces\.set\(memKey, rec\);/, "the write: the place read at Edit while the editor is up, else the live one, by the file's key");
  assert.match(openFn, /if \(refused\) \{ noteBar\(refused\); return; \}\n\s*editPlace = liveRecord\(\);[^\n]*\n(?:\s*\/\/[^\n]*\n)*\s*if \(isMd && fmt\.md === "rendered"\) \{ fmt\.md = "raw"; saveFmt\(fmt\); \}/, "enterEdit reads the place past the guard and before the Raw switch (the view the reader read)");
  assert.match(openFn, /editing = false; dirty = false; ta = null;\n\s*editPlace = null;/, "exitEdit clears it: the text view is back and the leave reads it live");
  assert.match(VIEW, /export function openFileView\(path: string, sid\?: string \| null, opts\?: \{ todoId\?: string \| null; at\?: At \| null; place\?: RememberedPlace \| null \}\): boolean \{/);
  assert.match(VIEW, /host\?: \{ openFile\?: \(path: string, sid: string \| null, at: At \| null\) => void; onLeave\?: \(path: string, sid: string \| null, rec: RememberedPlace\) => void \}\): void \{/);
  assert.match(VIEW, /export type RememberedPlace = \{ start: number; end: number; top: number; atTop: boolean; view: "rendered" \| "raw"; mtimeNs: string; scrollTop: number; t: number; folds\?: number\[\] \};/, "the eight fields and, since review round 3, the optional fold state");
  assert.match(VIEW, /export function rememberedPlaceOf\(place: Place, mtimeNs: string, scrollTop: number\): RememberedPlace \{/);
  assert.match(VIEW, /export function placeFromRemembered\(rec: RememberedPlace, source: string\): Place \| null \{/);
});

// ── the stand-in's projection (ui/test-dom-shim.ts): a node inspects as its primitives, never as the tree ─────────────
test("a stand-in node enumerates its primitives alone, so a failing assertion's dump shows neither parentNode nor childNodes; a laid block's box follows the body's scroll", () => {
  const body = new El("div"); body.className = "fileview-body";
  const md = body.appendChild(new El("div")); md.className = "fileview-md";
  const child = md.appendChild(new El("p")); child.appendChild(new Txt("alpha")); md.appendChild(new Txt("beta"));
  for (const n of [body, md, child, md.childNodes[1]] as Array<El | Txt>) {
    for (const k of Object.keys(n)) assert.ok(staysEnumerable((n as any)[k]), k + " is enumerable and holds a " + typeof (n as any)[k]);
    const dump = inspect(n, { compact: false, customInspect: false, depth: 1000, maxArrayLength: Infinity, showHidden: false, showProxy: false, sorted: true, getters: true });
    assert.ok(!dump.includes("parentNode") && !dump.includes("childNodes"), "the dump holds no edge: " + dump);
  }
  assert.ok(child.parentNode === md && md.childNodes[0] === child && md.textContent === "alphabeta", "the tree is reachable as before");
  assertHiddenEvent(new Ev("click"), body, child);
  // the layout: block 0 at the edge, then 30px above it once the body scrolls; a write past the content is clamped
  doc.body.appendChild(body);
  assert.equal(child.getBoundingClientRect().top, EDGE);
  body.scrollTop = 30; assert.equal(body.scrollTop, 0, "one block: nothing to scroll (clamped)");
  for (let i = 1; i < 10; i++) md.appendChild(new El("p"));
  body.scrollTop = 30; assert.equal(body.scrollTop, 30); assert.equal(child.getBoundingClientRect().top, EDGE - 30);
  body.scrollTop = 10000; assert.equal(body.scrollTop, 10 * BLOCK_H - BODY_H, "clamped to the content");
  body.remove();
});
