// The Outline (plans/markdown-viewer.md Slice 6, item 2; the outline half of the audit's High "No heading ids, no outline"):
// a button in the viewer's actions row over a markdown file's Rendered view, a dropdown listing the note's headings by depth
// in the menu vocabulary, and a pick that lands the heading at the top of the body through the fragment landing's own steps.
// The REAL openFileView runs over the place suite's DOM stand-in (file-view-place-memory.test.ts: ancestry, attributes,
// events with capture and bubbling, a tolerant selector engine, a layout for the body and its blocks, and the sanitizer's
// stand-in of Slice 7, md-sanitize.ts setMdSanitizer, which hands mdBlock a body holding marked's markup parsed by the
// suite's parser, so the real mintHeadingIds mints the heading ids and the math fill runs over the formula heading; until
// Slice 7 the box's textContent setter parsed the source and minted the ids itself, since under node DOMPurify has no
// document and mdBlock's catch wrote the bare text), with three things this suite adds: a node's `style` takes setProperty (the
// rows' depth variable); scrollIntoView records its argument (the landing's block: "start"); and what KaTeX's fill needs to
// render the formula heading for real, a document in standards mode (compatMode) and an element's replaceWith. The fixture is the shared
// forty-two-heading report (file-view-outline-fixture.ts). What the browser alone can show, the box measured inside the
// card, the heading's top at the body's edge, the tokens' colours under both themes, is file-view-outline-browser.test.ts's.
// Before item 2: no Outline button in the actions row (red at the first assertion over a git archive of the base).
// Synthetic fixtures only: the notes-api world, placeholder ids.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import { inspect } from "node:util";
import * as fs from "node:fs";
import * as path from "node:path";
import { assertHiddenEvent, hideEdges, staysEnumerable } from "../test-dom-shim";
import { headingSlug, uniqueSlugs } from "./md-links";
import { OUTLINE_NOTE, OUTLINE_HEADINGS, FOLD_HEADING, MATH_HEADING, CODE_HEADING, QUOTED_HEADING } from "./file-view-outline-fixture";
import type { FileViewActionCtx, At } from "./file-view";
import { setMdSanitizer } from "./md-sanitize";   // the sanitizer seam the node suites install a stand-in through (Slice 7 of plans/markdown-viewer.md)
import { loadGatedHost, forgetLoadedHosts } from "./figure-gate";   // the gate lifted for a synthetic host before a paint of remote pictures (the picture-title case)
import { cssRules, renderRule } from "./css-rules.mjs";
import { hostSheets } from "./host-sheets.mjs";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const VIEW = web("file-view.ts");
const CHAT = web("styles.css");
const FEED = web("feed.css");

// ── the layout: the body's edge and height, a block's and a row's pitch ─────────────────────────────
const EDGE = 100;
const BODY_H = 200;
const BODY_W = 800;
const BLOCK_H = 40;
const BLOCK_BOX = 32;
const ROW_H = 20;
type Rect = { left: number; top: number; right: number; bottom: number; width: number; height: number };
const rect = (top: number, height: number, width = BODY_W): Rect => ({ left: 0, top, right: width, bottom: top + height, width, height });

// ── a DOM stand-in: ancestry, ids, attributes, events with capture and bubbling, a tolerant selector engine, a layout ──
class Ev {
  target: El | Txt | null = null;
  currentTarget: El | null = null;
  defaultPrevented = false;
  stopped = false;
  key: string; ctrlKey: boolean; metaKey: boolean; detail: number;
  button: number;                                // a pointer event's, 0 the primary (pressHold reads it; the card's hold parks a landing under a press on a row)
  relatedTarget: El | null;                      // a focus event's other side (the popover's focusout closer reads it); an object edge, hidden by hideEdges
  constructor(public type: string, init: { key?: string; ctrlKey?: boolean; metaKey?: boolean; detail?: number; button?: number; relatedTarget?: El | null } = {}) {
    this.key = init.key || ""; this.ctrlKey = !!init.ctrlKey; this.metaKey = !!init.metaKey; this.detail = init.detail ?? 0;
    this.button = init.button ?? 0; this.relatedTarget = init.relatedTarget ?? null;
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
type Compound = { tag: string | null; id: string | null; classes: string[]; attrs: Array<[string, string | null]>; pseudos: string[]; child: boolean };
/** Comma groups of chains; a chain's links are joined by a descendant (space) or a child (`>`) combinator. A selector the
 *  engine does not know parses to null and matches nothing, where a browser answers an empty list. */
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
        const am = /^\[(?:\*\|)?([\w-]+)(?:="([^"]*)")?\]$/.exec(a);
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
  style: any = styleOf();
  onclick: ((ev: Ev) => void) | null = null;
  scrolled = 0;                                  // scrollIntoView calls (the pick's landing on the heading)
  scrolledWith: unknown = null;                  // its last argument ({ block: "start" } for a heading)
  focused = 0;                                   // focus() calls
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
  /** One text node, as the browser's setter writes it (the `.fileview-md` box no longer parses the note or mints its ids
   *  here: the sanitizer's stand-in hands mdBlock the parsed markup and the real mintHeadingIds runs, the header). */
  set textContent(v: string) {
    this.clear();
    if (v !== "") this.appendChild(new Txt(v));
  }
  get innerHTML(): string { return this._html; }
  set innerHTML(v: string) { this._html = v; this.clear(); for (const n of parseHTML(v)) this.appendChild(n); }
  private clear(): void { for (const c of this.childNodes) { this.dropFocusIn(c); c.parentNode = null; } this.childNodes.length = 0; }
  /** The browser's focus fixup: a removed subtree that held the active element leaves the keyboard on the document's body
   *  (so the popover's removal reads here as it does in Chromium, and takeKeyboard then gives the body the keyboard). */
  private dropFocusIn(n: El | Txt): void { if (n instanceof El && doc.activeElement && n.contains(doc.activeElement)) doc.activeElement = doc.body; }
  private detach(n: El | Txt): void { const p = n.parentNode; if (p) { const i = p.childNodes.indexOf(n); if (i >= 0) p.childNodes.splice(i, 1); n.parentNode = null; } }
  appendChild<T extends El | Txt>(n: T): T {
    if (n instanceof El && n.tagName === "#FRAGMENT") { for (const c of n.childNodes.slice()) this.appendChild(c); return n; }
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
  /** The DOM's replaceWith: `ns` take this node's place among its parent's children (the math fill unwraps KaTeX's output
   *  with `el.replaceWith(...el.childNodes)`, and its source fallback puts a code element in the placeholder's place). */
  replaceWith(...ns: Array<El | Txt>): void {
    const p = this.parentNode; if (!p) return;
    let at = p.childNodes.indexOf(this);
    this.detach(this);
    for (const n of ns) { this.detach(n); p.childNodes.splice(at++, 0, n); n.parentNode = p; }
  }
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
        if (chain[k + 1].child) return false;
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
  scrollIntoView(arg?: unknown): void { this.scrolled++; this.scrolledWith = arg ?? null; }
  // ── the layout ──
  private isBody(): boolean { return this.classes.includes("fileview-body"); }
  private scroller(): El | null { for (let a: El | null = this.parentNode; a; a = a.parentNode) if (a.isBody()) return a; return null; }
  private laid(): { top: number; height: number } | null {
    const p = this.parentNode;
    if (this.classes.includes("fileview-md")) return { top: 0, height: this.children.length * BLOCK_H };
    if (this.tagName === "CODE" && this.classes.includes("hljs")) return { top: 0, height: this.children.filter((c) => c.classes.includes("fv-cl")).length * ROW_H };
    if (p && p.classes.includes("fileview-md")) return { top: p.children.indexOf(this) * BLOCK_H, height: BLOCK_BOX };
    if (p && p.tagName === "CODE" && p.classes.includes("hljs") && this.classes.includes("fv-cl")) return { top: p.children.filter((c) => c.classes.includes("fv-cl")).indexOf(this) * ROW_H, height: ROW_H };
    return null;
  }
  getBoundingClientRect(): Rect {
    if (this.isBody()) return rect(EDGE, BODY_H);
    const s = this.scroller(), box = this.laid();
    if (!s || !box) return rect(0, 0, 0);
    return rect(EDGE + box.top - s.scrollTop, box.height);
  }
  get clientHeight(): number { return this.isBody() ? BODY_H : 0; }
  get clientWidth(): number { return this.isBody() ? BODY_W : 0; }
  get offsetWidth(): number { return this.clientWidth; }
  get scrollHeight(): number {
    if (!this.isBody()) return 0;
    const md = this.querySelector(".fileview-md"); if (md) return md.children.length * BLOCK_H;
    const code = this.querySelector("code.hljs"); if (code) return code.children.filter((c) => c.classes.includes("fv-cl")).length * ROW_H;
    return 0;
  }
  get scrollTop(): number { return this._scrollTop; }
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
function walkNodes(root: El, what: number): Array<El | Txt> {
  const out: Array<El | Txt> = [];
  const walk = (n: El) => { for (const c of n.childNodes) { if (c instanceof Txt) { if (what & 4) out.push(c); } else { if (what & 1) out.push(c); walk(c); } } };
  walk(root);
  return out;
}
// ── the sanitizer's stand-in (md-sanitize.ts setMdSanitizer; Slice 7 of plans/markdown-viewer.md, item 1's first step) ──
// DOMPurify has no document under node, so before the seam every Rendered paint went through mdBlock's catch, and this
// suite's box parsed the note through marked in its textContent setter (file-view-seam.test.ts's record pin states the
// constraint). The stand-in hands mdBlock a body holding marked's markup parsed by this suite's parser, unsanitized (the
// fixtures are plain markdown), and the real mintHeadingIds and the registered passes run over it.
setMdSanitizer({ addHook: () => { /* the hooks are DOMPurify's; the stand-in has none */ }, sanitize: (dirty: string) => { const body = new El("body"); for (const n of parseHTML(dirty)) body.appendChild(n); return body; } } as unknown as Parameters<typeof setMdSanitizer>[0]);

const doc = {
  listeners: [] as Reg[],
  body: null as unknown as El,
  head: null as unknown as El,
  hidden: false,
  activeElement: null as El | null,
  createElement: (tag: string) => new El(tag),
  createTextNode: (s: string) => new Txt(s),
  createDocumentFragment: () => new El("#fragment"),
  compatMode: "CSS1Compat",                          // standards mode: KaTeX refuses to render into a quirks-mode document
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
/** The DOM event path: document capture, ancestors' capture root to target, target and ancestors' bubble, document bubble. */
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
type Served = { bytes: string; type: string; mtimeNs: string };
const disk: Record<string, Served> = {};
(globalThis as any).fetch = async (url: string) => {
  if (url.startsWith("/version")) return { json: async () => ({ fileEditing: true }) };
  if (url.startsWith("/sessions")) return { json: async () => [{ id: SID, name: "api", bg: "#123456", fg: "#ffffff" }] };
  const p = decodeURIComponent((/[?&]path=([^&]*)/.exec(url) || [])[1] || "");
  const f = disk[p];
  const headers = { get: (h: string) => (f ? (h === "Content-Type" ? f.type : h === "X-Romp-Mtime-Ns" ? f.mtimeNs : h === "X-Romp-Text-Utf8" ? "1" : null) : null) };
  if (!f) return { ok: false, status: 404, headers, text: async () => "no such file: " + p };
  return { ok: true, status: 200, headers, text: async () => f.bytes, blob: async () => new Blob([f.bytes], { type: f.type }) };
};

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ROOT = "/repo/notes-api";
const MT = "1757145600000000001";
const REPORT = ROOT + "/docs/report.md";
const NOTES = ROOT + "/docs/notes.txt";
const PLAIN = ROOT + "/docs/plain.md";
const PROSE = "Just a paragraph, with no heading above it.\n\nAnd a second one.\n";
/** The ids the viewer mints for the fixture's headings, in document order: md- plus the GitHub slug, unique in order. */
const IDS = uniqueSlugs(OUTLINE_HEADINGS.map(([, t]) => headingSlug(t))).map((s) => "md-" + s);
/** The row's words: the heading's text as marked renders it (inline code loses its backticks; the formula's placeholder is
 *  its TeX without the delimiters, which is also what KaTeX's html reads as once the fill has run in a browser). */
const WORDS = OUTLINE_HEADINGS.map(([, t]) => t.replace(/[`$]/g, ""));

// ── the module and its probe ─────────────────────────────────────────────────────────────────────────
let seam: FileViewActionCtx | null = null;
let paints = 0;
const posted: any[] = [];
let fvMod: typeof import("./file-view") | null = null;
async function mod(): Promise<typeof import("./file-view")> {
  if (fvMod) return fvMod;
  fvMod = await import("./file-view");
  fvMod.initFileView((m) => posted.push(m));
  fvMod.registerFileViewAction({ id: "outline-probe", mount(ctx) { seam = ctx; ctx.onRendered(() => { paints++; }); return null; } });
  fvMod.setFileViewIdentity((sid) => (sid === SID ? { name: "api", color: { bg: "#123456", fg: "#ffffff" } } : null));
  return fvMod;
}
const settle = async () => { for (let i = 0; i < 8; i++) await new Promise<void>((r) => setImmediate(r)); };
type Open = { fv: typeof import("./file-view"); ctx: FileViewActionCtx; wrap: El; card: El; body: El; acts: El };
/** Serve `text` at `p` and open it with the REAL openFileView; `raw`: the stored preference says Raw for a markdown file; `at`: the
 *  open's target (a heading, for the hidden-section case). */
async function open(p: string, text: string, t: TestContext, raw = false, at: At | null = null): Promise<Open> {
  const fv = await mod();
  disk[p] = { bytes: text, type: "text/plain; charset=utf-8", mtimeNs: MT };
  store.delete("romp:fileviewFmt");
  if (raw) store.set("romp:fileviewFmt", JSON.stringify({ md: "raw" }));
  seam = null; paints = 0;
  assert.equal(fv.openFileView(p, SID, at ? { at } : undefined), true, "the open happened");
  t.after(() => { fv.closeFileView(); doc.activeElement = null; });
  await settle();
  const wrap = doc.getElementById("romp-fileview")!;
  assert.ok(wrap, "the viewer is up");
  assert.ok(seam, "the probe action was mounted with the ctx");
  return { fv, ctx: seam!, wrap, card: wrap.querySelector(".fileview")!, body: wrap.querySelector(".fileview-body")!, acts: wrap.querySelector(".fileview-acts")! };
}
const button = (o: Open, label: string): El | undefined => o.acts.querySelectorAll("button").find((x) => x.textContent === label || x.getAttribute("aria-label") === label);   // a word button by its text, a glyph (Edit, Download; T367) by its aria-label
const outlineBtn = (o: Open): El => { const b = button(o, "Outline"); assert.ok(b, "the Outline button is in the actions row (before item 2 there was none)"); return b!; };
const popover = (o: Open): El | null => o.card.querySelector(".fileview-outline");
const rowsOf = (pop: El): El[] => pop.querySelectorAll(".fileview-outline-row");
const headings = (o: Open): El[] => o.body.querySelector(".fileview-md")!.querySelectorAll("h1, h2, h3, h4, h5, h6");
/** Click the button and hand back the popover it opened. */
const openOutline = (o: Open): El => { outlineBtn(o).click(); const pop = popover(o); assert.ok(pop, "the popover opened under the button"); return pop!; };
const key = (target: El, k: string): Ev => { const ev = new Ev("keydown", { key: k }); target.dispatchEvent(ev); return ev; };
/** The pointer's release, on the window as pressHold hears it: a press dispatched on a card child holds the landing until this. */
const release = (): void => { win.dispatchEvent(new Event("pointerup")); };
/** requestAnimationFrame as a queue for a case that lands a heading target (the seam suite's idiom): installed for the case, flushed by hand. */
const frames: Array<() => void> = [];
const withFrames = (t: TestContext): void => {
  (globalThis as any).requestAnimationFrame = (cb: () => void) => { frames.push(cb); return frames.length; };
  t.after(() => { delete (globalThis as any).requestAnimationFrame; frames.length = 0; });
};
const flushFrames = (): void => { const run = frames.splice(0); for (const cb of run) cb(); };
const noticeOf = (o: Open): string | null => { const n = o.card.querySelector("#fileview-save-err"); return n ? n.textContent : null; };

test("the Outline button: in the actions row right after the Rendered/Raw toggle over a markdown file's Rendered view that has a heading, with the menu's aria; hidden in Raw and back on Rendered; hidden while the editor holds the body and, since Edit took the Raw view, until Rendered is chosen again; hidden over a note with no heading; absent for a non-markdown file", async (t) => {
  const o = await open(REPORT, OUTLINE_NOTE, t);
  assert.equal(headings(o).length, 42, "the stand-in rendered the forty-two headings");
  const b = outlineBtn(o);
  assert.equal(b.hidden, false, "shown over the Rendered view");
  assert.equal(b.textContent, "Outline"); assert.equal(b.title, "The file's headings");
  assert.equal(b.getAttribute("aria-haspopup"), "menu"); assert.equal(b.getAttribute("aria-expanded"), "false");
  assert.equal(b.type, "button"); assert.ok(b.classes.includes("fileview-btn"), "a bar button like its neighbours");
  const btns = o.acts.querySelectorAll("button").map((x) => x.textContent);
  assert.equal(btns.indexOf("Outline"), btns.indexOf("Raw") + 1, "right after the Rendered/Raw toggle: " + btns.join(","));
  // Raw hides it (no heading elements in the rows), Rendered shows it again
  button(o, "Raw")!.click();
  assert.ok(o.body.querySelector("code.hljs"), "the Raw view is up");
  assert.equal(b.hidden, true, "hidden in Raw");
  button(o, "Rendered")!.click();
  assert.equal(b.hidden, false, "shown again on Rendered");
  // the editor: hidden while it holds the body, back after Cancel
  button(o, "Edit")!.click(); await settle();
  assert.ok(o.body.querySelector(".fileview-cm"), "the editor holds the body");
  assert.equal(b.hidden, true, "hidden in the editor");
  button(o, "Cancel")!.click();
  assert.equal(o.ctx.mode(), "raw", "Edit switched the note to its Raw view (what you edit is what Raw shows) and Cancel leaves that standing");
  assert.equal(b.hidden, true, "…so the button stays hidden after Cancel, by the Raw rule");
  button(o, "Rendered")!.click();
  assert.equal(b.hidden, false, "back on Rendered");
  o.fv.closeFileView();
  // a note with no heading: the button exists (a markdown file) and hides
  const plain = await open(PLAIN, PROSE, t);
  assert.equal(outlineBtn(plain).hidden, true, "no heading, no Outline");
  plain.fv.closeFileView();
  // a markdown file opened under the Raw preference: hidden until the Rendered toggle
  const raw = await open(REPORT, OUTLINE_NOTE, t, true);
  assert.equal(outlineBtn(raw).hidden, true, "hidden under the Raw preference");
  button(raw, "Rendered")!.click();
  assert.equal(outlineBtn(raw).hidden, false);
  raw.fv.closeFileView();
  // a text file has no Rendered form and no Outline
  const txt = await open(NOTES, "line one\nline two\n", t);
  assert.equal(button(txt, "Outline"), undefined, "no Outline button for a .txt file");
});

test("the list: one click opens a menu-role popover in the card with one menuitem row per heading in document order, the heading's id on each, its text on one line, the depth under the shallowest heading as the row's variable, the fold's and the quote's headings included and no row for the front-matter block; the popover takes the focus with the first row current and the button says it is expanded", async (t) => {
  const o = await open(REPORT, OUTLINE_NOTE, t);
  assert.ok(o.body.querySelector(".fileview-md details.md-frontmatter"), "the fixture's front matter rendered as the folded block");
  assert.equal(popover(o), null, "no popover before the click");
  const pop = openOutline(o);
  assert.equal(pop.getAttribute("role"), "menu"); assert.equal(pop.tabIndex, -1, "focusable by script, not a Tab stop");
  assert.ok(pop.parentNode === o.card, "a child of the viewer's card (positioned from the button's box as offsets from its offsetParent, the overlay: the card is not its containing block)");
  assert.equal(outlineBtn(o).getAttribute("aria-expanded"), "true");
  assert.ok(outlineBtn(o).classes.includes("on"), "the button wears the bar's selected dress, .fileview-btn.on, while the popover is up (the PR review's round 1: the build gave it a near-twin rule of its own on aria-expanded, without the weight and the hover)");
  assert.ok(doc.activeElement === pop, "the popover holds the keyboard");
  for (const k of ["top", "right", "maxWidth", "maxHeight"]) assert.match(String(pop.style[k]), /^-?\d+(\.\d+)?px$/, "the popover's " + k + " is set inline from the boxes at the open");
  const rows = rowsOf(pop);
  assert.equal(rows.length, 42, "one row per heading");
  assert.deepEqual(rows.map((r) => r.dataset.id), IDS, "the heading ids in document order; the second Results is results-1");
  assert.equal(IDS[4], "md-results"); assert.equal(IDS[8], "md-results-1"); assert.equal(IDS[9], "md-using-cacheget"); assert.equal(IDS[10], "md-ratio-x");
  assert.deepEqual(rows.map((r) => r.textContent), WORDS, "each row is the heading's text");
  assert.deepEqual(rows.map((r) => r.title), WORDS, "…and carries it whole as its title (the row clips at the popover's width)");
  assert.deepEqual(rows.map((r) => r.style.getPropertyValue("--fv-ol-depth")), OUTLINE_HEADINGS.map(([d]) => String(d - 1)), "the depth under the shallowest heading (the h1), as the row's indent variable");
  assert.ok(rows.every((r) => r.getAttribute("role") === "menuitem"));
  assert.equal(rows[13].textContent, FOLD_HEADING, "the heading inside the closed details is listed");
  assert.ok(headings(o)[13].closest("details") && !headings(o)[13].closest("details")!.hasAttribute("open"), "…and its fold is shut");
  assert.equal(rows[12].textContent, QUOTED_HEADING, "the heading inside the blockquote is listed");
  assert.equal(rows[9].textContent, CODE_HEADING.replace(/`/g, ""), "inline code reads as its text");
  assert.equal(rows[10].textContent, MATH_HEADING.replace(/\$/g, ""), "the formula heading reads as KaTeX's html reads (the fill runs over the seam's stand-in body here too, since Slice 7)");
  assert.ok(headings(o)[10].querySelector(".katex"), "…and the fill ran: KaTeX's markup stands in the heading, the ids minted before it from the TeX as written");
  assert.ok(!rows.some((r) => /Front matter|title:|tags:/.test(r.textContent)), "no row for the front-matter block");
  assert.deepEqual(rows.map((r) => r.classes.includes("current")), rows.map((_, i) => i === 0), "the first row is current");
  // a second click on the button closes it (the toggle)
  outlineBtn(o).click();
  assert.equal(popover(o), null, "the button toggles the popover closed");
  assert.equal(outlineBtn(o).getAttribute("aria-expanded"), "false");
  assert.ok(!outlineBtn(o).classes.includes("on"), "…and the dress comes off with it");
  // a note whose shallowest heading is an h2 indents nothing for its h2s
  o.fv.closeFileView();
  const deep = await open(PLAIN, "## Second\n\nText.\n\n### Third\n\nMore.\n\n## Another second\n", t);
  const rows2 = rowsOf(openOutline(deep));
  assert.deepEqual(rows2.map((r) => r.style.getPropertyValue("--fv-ol-depth")), ["0", "1", "0"], "relative to the shallowest heading, not to h1");
});

test("the pick: a click on the 40th row closes the popover, lands the 40th heading through the fragment landing (scrollIntoView block start on that element and no other) and returns the keyboard to the body; the row for the heading inside the closed details opens the fold first; the button reads collapsed again", async (t) => {
  const o = await open(REPORT, OUTLINE_NOTE, t);
  const heads = headings(o);
  const focusedBefore = o.body.focused;
  const pop = openOutline(o);
  rowsOf(pop)[39].click();
  assert.equal(popover(o), null, "the popover closed on the pick");
  assert.equal(outlineBtn(o).getAttribute("aria-expanded"), "false");
  assert.equal(heads[39].textContent, "Detail 9.1", "the 40th heading");
  assert.equal(heads[39].scrolled, 1, "the 40th heading was scrolled into view");
  assert.deepEqual(heads[39].scrolledWith, { block: "start" }, "…to the top of the body, the fragment landing's own call");
  assert.equal(heads.reduce((n, h) => n + h.scrolled, 0), 1, "and no other heading");
  assert.ok(doc.activeElement === o.body, "the keyboard is back on the body (the popover's removal left it on the document's body; takeKeyboard took it)");
  assert.equal(o.body.focused, focusedBefore + 1, "one focus call for the pick");
  assert.ok(doc.getElementById("romp-fileview") === o.wrap, "the viewer stands");
  // the fold: the heading inside the closed details, revealed before the scroll (revealFragmentTarget)
  const details = heads[13].closest("details")!;
  assert.equal(details.hasAttribute("open"), false, "shut before the pick");
  rowsOf(openOutline(o))[13].click();
  assert.equal(details.hasAttribute("open"), true, "the pick opened the fold above the heading");
  assert.equal(heads[13].scrolled, 1); assert.deepEqual(heads[13].scrolledWith, { block: "start" });
  assert.equal(popover(o), null);
});

test("the keyboard on the popover: ArrowDown twice then Enter picks the third heading; End and Home jump; Space picks; Escape closes the popover, stops the event before the document's handler (the viewer stays up) and puts the keyboard back on the Outline button, as a menu button's Escape does; ArrowUp above the first row and ArrowDown below the last stay put", async (t) => {
  const o = await open(REPORT, OUTLINE_NOTE, t);
  const heads = headings(o);
  let pop = openOutline(o);
  let rows = rowsOf(pop);
  const current = () => rows.findIndex((r) => r.classes.includes("current"));
  const down = key(pop, "ArrowDown");
  assert.ok(down.defaultPrevented && down.stopped, "the arrow is the popover's: prevented (the chat's arrow handler yields to a prevented key) and stopped");
  key(pop, "ArrowDown");
  assert.equal(current(), 2, "two ArrowDowns from the first row: the third is current");
  assert.equal(rows.filter((r) => r.classes.includes("current")).length, 1, "one current row");
  const enter = key(pop, "Enter");
  assert.ok(enter.defaultPrevented && enter.stopped);
  assert.equal(popover(o), null, "Enter picked and closed");
  assert.equal(heads[2].textContent, "Scope"); assert.equal(heads[2].scrolled, 1, "the third heading landed");
  assert.deepEqual(heads[2].scrolledWith, { block: "start" });
  assert.ok(doc.activeElement === o.body, "the keyboard is on the body after the pick");
  // End, Home, the ends, Space
  pop = openOutline(o); rows = rowsOf(pop);
  key(pop, "ArrowUp"); assert.equal(current(), 0, "ArrowUp above the first row stays on it");
  key(pop, "End"); assert.equal(current(), 41, "End: the last row");
  key(pop, "ArrowDown"); assert.equal(current(), 41, "ArrowDown below the last row stays on it");
  key(pop, "Home"); assert.equal(current(), 0, "Home: the first row");
  key(pop, "ArrowDown"); key(pop, " ");
  assert.equal(popover(o), null, "Space picked");
  assert.equal(heads[1].scrolled, 1, "the second heading landed");
  // Escape: the popover's, never the viewer's
  pop = openOutline(o);
  assert.ok(doc.activeElement === pop);
  const esc = key(pop, "Escape");
  assert.ok(esc.defaultPrevented && esc.stopped, "Escape is taken and stopped on the popover, so the document's onKey never sees it");
  assert.equal(popover(o), null, "the popover closed");
  assert.ok(doc.getElementById("romp-fileview") === o.wrap, "…and the viewer is still up");
  assert.ok(doc.activeElement === outlineBtn(o), "the keyboard went back on the Outline button, the menu-button pattern its aria-haspopup announces (the PR review's round 1; before: the body)");
  assert.ok(!outlineBtn(o).classes.includes("on") && outlineBtn(o).getAttribute("aria-expanded") === "false", "…which reads collapsed and wears no dress");
  // a key the popover does not take passes through untouched
  pop = openOutline(o);
  const other = key(pop, "x");
  assert.ok(!other.defaultPrevented && !other.stopped, "a letter is not the popover's");
  assert.ok(popover(o) === pop, "…and leaves it open");
});

test("closers: a press outside the popover closes it and a press on the button does not (the button's click is the toggle); every paint of the body closes it (a reload keeps the button, the Raw toggle hides it); the viewer's close drops its document listener; the popover is built afresh per open", async (t) => {
  const o = await open(REPORT, OUTLINE_NOTE, t);
  // initFileView installs one capture-phase pointerdown listener of its own on the document (watchInputKind, the kind of the last
  // press for the keyboard hand-over's ring; the review's round 4), so the popover's is counted over that base
  const base = doc.listeners.filter((l) => l.type === "pointerdown" && l.capture).length;
  const downs = () => doc.listeners.filter((l) => l.type === "pointerdown" && l.capture).length - base;
  assert.equal(downs(), 0, "no outside-press listener before the popover opens");
  let pop = openOutline(o);
  assert.equal(downs(), 1, "one capture-phase pointerdown listener on the document while it is open");
  o.body.dispatchEvent(new Ev("pointerdown"));
  assert.equal(popover(o), null, "a press on the body (outside) closed it");
  assert.equal(downs(), 0, "…and dropped the listener");
  release();   // every press below is released before the reload: the card's hold parks a landing under a press (the PR review's round 1)
  pop = openOutline(o);
  outlineBtn(o).dispatchEvent(new Ev("pointerdown"));
  assert.ok(popover(o) === pop, "a press on the button is not outside: the popover stays for the button's click to toggle it");
  release();
  pop.querySelector(".fileview-outline-row")!.dispatchEvent(new Ev("pointerdown"));
  assert.ok(popover(o) === pop, "a press inside the popover keeps it");
  release();
  // a paint: the reload's landing closes the popover (its rows were read off the DOM the paint replaced) and keeps the button
  const painted = paints;
  o.ctx.reload(); await settle();
  assert.equal(paints, painted + 1, "the reload painted");
  assert.equal(popover(o), null, "the paint closed the popover");
  assert.equal(outlineBtn(o).hidden, false, "the button stands over the Rendered paint");
  assert.equal(downs(), 0);
  // the view switch: closes it and hides the button
  pop = openOutline(o);
  button(o, "Raw")!.click();
  assert.equal(popover(o), null, "Raw closed the popover");
  assert.equal(outlineBtn(o).hidden, true, "…and hid the button");
  button(o, "Rendered")!.click();
  const again = openOutline(o);
  assert.ok(again !== pop, "a fresh popover per open (nothing kept)");
  assert.equal(rowsOf(again).length, 42);
  // the viewer's close with the popover open: the card goes, and the listener with it (closeHooks)
  o.fv.closeFileView();
  assert.equal(doc.getElementById("romp-fileview"), null, "closed");
  assert.equal(downs(), 0, "the close dropped the popover's document listener");
  assert.equal(again.parentNode, null, "the popover left with the card");
});

test("closers (review round 2): the fetch pipeline's failure pane closes an open popover too: with the popover up and holding the keyboard, the file gone and the panel's reload painting the 404 pane leave no popover, the button hidden and reading collapsed, and the body holding the keyboard the popover held (before: the catch painted the pane without renderBody's closer, so the popover stood over the pane with its 42 stale rows and the keyboard, the hidden button reading expanded)", async (t) => {
  const o = await open(REPORT, OUTLINE_NOTE, t);
  const pop = openOutline(o);
  assert.ok(doc.activeElement === pop, "the popover holds the keyboard");
  assert.equal(outlineBtn(o).getAttribute("aria-expanded"), "true");
  assert.equal(rowsOf(pop).length, 42);
  const painted = paints;
  delete disk[REPORT];                                     // gone by the time the poll's reload asks
  o.ctx.reload(); await settle();
  assert.equal(paints, painted + 1, "a failure paints no text, and the pane's paint fires the hooks once (Slice 7 of plans/markdown-viewer.md, item 3; before Slice 7: no paint)");
  assert.equal(o.ctx.error(), "no such file: " + REPORT, "the seam's error() is the pane's words");
  assert.ok(o.body.querySelector(".fileview-err"), "the failure pane is in the body");
  assert.equal(popover(o), null, "the pane's paint closed the popover (before the fix: it stood over the pane with its stale rows)");
  assert.equal(pop.parentNode, null, "\u2026and the popover left the card");
  assert.equal(outlineBtn(o).hidden, true, "the button is hidden over the pane (review round 1)");
  assert.equal(outlineBtn(o).getAttribute("aria-expanded"), "false", "\u2026and reads collapsed (before: expanded, on a hidden button)");
  assert.ok(doc.activeElement === o.body, "the body took the keyboard the popover held (the paint closer's rule; before: the browser's fixup left it on the document's body)");
});

test("file-view.ts and the two sheets: the button's label is the exported OUTLINE_LABEL with the menu's aria; the popover is built at the open (not at a paint) and read off the Rendered DOM through one query; every paint closes it and the text paint syncs the button; the pick closes, lands through scrollToFragment and takes the keyboard, in that order; Escape is taken and stopped; both exits run closeOutline; the sheets carry the popover's rules in the menu tokens, byte-equal, with no dark literal", () => {
  assert.match(VIEW, /export const OUTLINE_LABEL = "Outline";/);
  const openFn = VIEW.split("export function openFileView")[1].split("function offersDownload")[0];
  assert.match(openFn, /outlineBtn\.type = "button"; outlineBtn\.textContent = OUTLINE_LABEL; outlineBtn\.title = "The file's headings";\n\s*outlineBtn\.setAttribute\("aria-haspopup", "menu"\); outlineBtn\.setAttribute\("aria-expanded", "false"\);/);
  assert.match(openFn, /if \(isMd\) viewGroup\.appendChild\(outlineBtn\);/, "a markdown file's button, in the view group beside the Rendered|Raw pair (T367's grouping)");
  assert.match(openFn, /const headingsOf = \(\): HTMLElement\[\] => \{\n\s*const md = body\.querySelector\("\.fileview-md"\);\n(?:\s*\/\/[^\n]*\n)*\s*return md \? \(Array\.from\(md\.querySelectorAll\("h1, h2, h3, h4, h5, h6"\)\) as HTMLElement\[\]\)\.filter\(\(h\) => !underHidden\(h, md\)\) : \[\];/, "the one query, over the rendered box; a heading under a plain hidden wrapper has no row (review round 3)");
  assert.match(openFn, /const syncOutline = \(\): void => \{\n\s*outlineBtn\.hidden = editing \|\| ctx\.mode\(\) !== "rendered" \|\| headingsOf\(\)\.length === 0;\n\s*viewGroup\.hidden = !\(segBtns\.some\(\(\[, b\]\) => !b\.hidden\) \|\| !textSize\.trigger\.hidden \|\| !srcBtn\.hidden \|\| !outlineBtn\.hidden\);[^\n]*\n\s*\};/, "the button's rule, then the view group re-read on it (T367's all-hidden rule: the group follows the button it holds)");
  assert.match(openFn, /const openOutline = \(\): void => \{\n\s*const heads = headingsOf\(\);/, "the list is read when the popover opens");
  assert.match(openFn, /const pick = \(i: number\): void => \{\n\s*const id = rows\[i\] \? rows\[i\]\.dataset\.id : undefined;\n\s*closeOutline\(\);\n\s*if \(id\) scrollToFragment\(body, id\);\n\s*takeKeyboard\(\);\n\s*\};/, "close, land, keyboard");
  assert.match(openFn, /if \(e\.key === "Escape"\) \{ take\(\); closeOutlineKeeping\(false\); outlineBtn\.focus\(\{ preventScroll: true \}\); \}/, "Escape: the Tab branch's shape, the keyboard back on the button (the PR review's round 1)");
  assert.match(openFn, /const take = \(\): void => \{ e\.preventDefault\(\); e\.stopPropagation\(\); \};/, "a key the popover takes never reaches the document's onKey or the chat's window handlers");
  assert.match(openFn, /document\.addEventListener\("pointerdown", onDown, true\);\n\s*window\.addEventListener\("resize", closeOutline\);/);
  assert.match(openFn, /pop\.focus\(\{ preventScroll: true \}\);\n\s*\};/, "the popover takes the focus at the open, without moving the body");
  assert.match(openFn, /outlineBtn\.addEventListener\("click", \(\) => \{ flash\(outlineBtn\); if \(outline\) closeOutline\(\); else openOutline\(\); \}\);/, "the press pulse, then the toggle");
  assert.match(openFn, /textSize\.sync\(\);[^\n]*\n\s*closeOutline\(\);[^\n]*\n\s*if \(dropReseat\) dropReseat\(\);[^\n]*\n(?:\s*\/\/[^\n]*\n)*\s*if \(editing \|\| text === null\) outlineBtn\.hidden = true;\n/, "renderBody: every paint closes the popover and retires a remembered seat's re-seat on the pictures' loads (review round 3); the paths that paint no text hide the button here (the loader, the editor's entry)");
  assert.match(openFn, /stampBodyWidth\(\);[^\n]*\n\s*syncOutline\(\);[^\n]*\n\s*fireRendered\(\);[^\n]*\n\s*shownText = text;\n\s*seat\(kept\);/, "…and a text paint decides it inside the paint, after the swap and before the hooks measure and the seat writes (the consolidation: a bar whose height changes between the place read and the seat re-clamped a body at the document's end and lost the held place)");
  assert.doesNotMatch(openFn, /landRemembered\(\);[^\n]*\n\s*\}\);\n\s*syncOutline\(\);/, "never after the seat");
  // the one paint that opens it again (the PR review's round 2): a text landing the card's hold PARKED under a press, run after the
  // release's click on the Outline button had opened the popover; read before the paint, opened after the landing's target, and never for a landing
  // that ran at once, so a plain reload still closes it as the pin above says
  assert.match(openFn, /const reopenOutline = parked && outline !== null;\n(?:\s*\/\/[^\n]*\n)*\s*if \(pendingLine !== null && isMd && fmt\.md === "rendered"\) fmt\.md = "raw";\n\s*renderBody\(\);\n(?:\s*\/\/[^\n]*\n)*\s*if \(notUtf8 && !latin1LineStands\(\)\) noteBar\(LATIN1_NOTICE\);\n\s*landTarget\(\);[^\n]*\n\s*if \(reopenOutline\) openOutline\(\);/, "a landing the hold parked and a popover open at its run: opened again after the paint and the target, on the landed body (the Latin-1 line's raise stands between the paint and the target; Slice 7 of plans/markdown-viewer.md, item 5)");
  assert.equal((openFn.match(/openOutline\(\);/g) || []).length, 2, "openOutline is called from the button's toggle and the parked landing's re-open alone");
  assert.match(openFn, /closeHooks\.push\(dropPdf\);[^\n]*\n\s*closeHooks\.push\(closeOutline\);/, "both exits close the popover with the viewer");
  assert.equal((VIEW.match(/import \{ delegate, flash, pressHold \} from "\.\/actions";/g) || []).length, 1);
  // the sheets: the rules in the tokens, the same bytes in both, and no dark literal outside a var() fallback (menu-theme-tokens.test.ts's rule)
  const block = (css: string): string => { const a = css.indexOf("\n.fileview-outline {"), b = css.indexOf(".fileview-outline-row:hover, .fileview-outline-row.current {", a); return css.slice(a, css.indexOf("}", b) + 1); };
  const chat = block(CHAT), feed = block(FEED);
  assert.ok(chat.length > 200, "the Outline's rules are in styles.css");
  assert.equal(chat, feed, "…and byte-equal in feed.css");
  for (const tok of ["--menu-bg", "--menu-fg", "--menu-border", "--menu-hover", "--radius-menu", "--shadow-menu"]) assert.ok(chat.includes("var(" + tok + ")"), "the popover reads " + tok);
  assert.match(chat, /\.fileview-outline \{ position: absolute;/, "positioned absolutely, from its offsetParent (the overlay #romp-fileview: the card's container-type gives it no layout containment)");
  // the sheets' comment says where the box is placed from, in agreement with openOutline's own comment and the browser leg: its offsetParent, the
  // overlay, never the card (round 1 placed the box from the card's edges on the belief that container-type gives layout containment, which sat it
  // 18 px high and 25 px left in the chat and feed modals; round 2 found both sheets and the parity list still saying so after the fix)
  const note = (css: string): string => { const b = css.indexOf("\n.fileview-outline {"), a = css.lastIndexOf("/* The Outline's dropdown", b); return a < 0 ? "" : css.slice(a, b); };
  for (const [sheet, css] of [["styles.css", CHAT], ["feed.css", FEED]] as const) {
    const n = note(css);
    assert.ok(n.length > 200, sheet + ": the Outline comment stands over the rules");
    assert.match(n, /offsetParent/, sheet + ": the comment names the box the offsets are read against");
    assert.match(n, /#romp-fileview/, sheet + ": ...the viewer's overlay");
    assert.match(n, /no layout containment/, sheet + ": ...and why the card is not it");
    for (const stale of [/gives the card\s+layout containment/, /makes it the containing block/, /are card offsets/, /overflow: hidden clips it/]) assert.doesNotMatch(n, stale, sheet + ": the comment no longer says the card is the containing block");
  }
  assert.match(chat, /font-size: 12px;/, "the menu's size (ui/CLAUDE.md)");
  assert.match(chat, /\.fileview-outline-row \{ padding: 4px 10px 4px calc\(10px \+ var\(--fv-ol-depth, 0\) \* 1\.1em\);/, "the depth indent from the row's variable");
  assert.match(chat, /white-space: nowrap; overflow: hidden; text-overflow: ellipsis;/, "one line per row");
  assert.match(chat, /\.fileview-outline-row:hover, \.fileview-outline-row\.current \{ background: var\(--menu-hover\); \}/);
  assert.doesNotMatch(chat, /aria-expanded|fileview-outline-btn/, "no rule of the button's own: while the popover is up it wears the bar's selected dress, .fileview-btn.on, which file-view.ts toggles beside aria-expanded (the PR review's round 1: the build's own rule was a near-twin without the weight and the hover)");
  assert.match(openFn, /outlineBtn\.setAttribute\("aria-expanded", "true"\); outlineBtn\.classList\.add\("on"\);/, "the open puts the dress on");
  assert.match(openFn, /outlineBtn\.setAttribute\("aria-expanded", "false"\); outlineBtn\.classList\.remove\("on"\);/, "the close takes it off");
  const bare = chat.replace(/var\((--[\w-]+)\s*,\s*(?:[^()]|\([^()]*\))*\)/g, "var($1)");
  for (const re of [/#[0-9a-fA-F]{3,8}\b/, /rgba\(\s*255\s*,\s*255\s*,\s*255\s*,/i, /rgba\(\s*0\s*,\s*0\s*,\s*0\s*,\s*0?\.35\s*\)/]) assert.doesNotMatch(bare, re, "no literal colour in the popover's rules: the tokens carry the theme");
});

// ── the dress's reach: the open state is the bar's selected dress, on the Outline button alone ────────────────────────
// Review round 1: the build's rule was `.fileview-btn[aria-expanded="true"]`, and the Comments panel builds its buttons with
// the same class by default (file-comments.ts btn) and sets aria-expanded on two of them, the card foot's Show more (true
// while the body is open, so "Show less") and Reject all (true while its confirm row is armed); both turned accent, as a
// pressed toggle, in both sheets. The rule then keyed on the button's own class; the PR review's round 1 dropped that rule, a
// near-twin of the bar's selected dress without its 600 weight and its hover inversion, and the open button wears `.on`, the
// class the pressed Rendered toggle wears, which file-view.ts toggles beside aria-expanded (fileview-parity.test.ts holds the
// twin gone from both sheets). Red over a git archive of 3e433ceee: the twin's head in both sheets, and no `on` class at the
// open; the panel's own source is pinned so the hazard stays named. The census here and in fileview-parity.test.ts is on parsed
// rules through ui/webview/css-rules.mjs over every sheet a page of either host loads (ui/webview/host-sheets.mjs; the file
// review's round 10, correctness-5: heads read at a line start over the pair alone passed the twin indented inside an at-rule
// block, and a rule of the button's own in the Files page's sheet dresses the button there as one in styles.css does).
test("the open state's dress is the bar's selected dress and reaches the Outline button alone: no rule in any sheet a page of either host loads names aria-expanded or the button's class, however the sheet writes it, `.fileview-btn.on` matches the open Outline button and neither the panel's Show less nor its armed Reject all, which are .fileview-btn with aria-expanded too and never `on`", () => {
  const FC = web("file-comments.ts");
  assert.match(FC, /function btn\(label: string, act: string, cls = "fileview-btn"\)/, "the panel's buttons take the bar button's class by default");
  assert.match(FC, /const b = btn\(open \? "Show less" : "Show more", "fcclip"\);[\s\S]{0,300}?b\.setAttribute\("aria-expanded", open \? "true" : "false"\);/, "the card foot's Show more/Show less carries aria-expanded");
  assert.match(FC, /const none = btn\([^\n]*"Reject all", "fcrejectall"\);[\s\S]{0,400}?none\.setAttribute\("aria-expanded", this\.rejectAllConfirm && !editing \? "true" : "false"\);/, "Reject all carries aria-expanded while armed");
  // the stand-ins: the Outline button as file-view.ts builds it, popover up; the panel's two buttons in the states that set the attribute
  const card = new El("div"); card.className = "fileview";
  const acts = card.appendChild(new El("div")); acts.className = "fileview-acts";
  const outline = acts.appendChild(new El("button")); outline.className = "fileview-btn fileview-outline-btn";
  outline.setAttribute("aria-haspopup", "menu"); outline.setAttribute("aria-expanded", "true");
  const aside = card.appendChild(new El("aside")); aside.className = "fc-panel fileview-aside fc-margin";
  const clipRow = aside.appendChild(new El("div")); clipRow.className = "fc-clip-row";
  const showLess = clipRow.appendChild(new El("button")); showLess.className = "fileview-btn"; showLess.setAttribute("aria-expanded", "true");
  const rejectAll = aside.appendChild(new El("button")); rejectAll.className = "fileview-btn"; rejectAll.setAttribute("aria-expanded", "true");
  const showMore = clipRow.appendChild(new El("button")); showMore.className = "fileview-btn"; showMore.setAttribute("aria-expanded", "false");
  outline.classList.add("on");                                             // what file-view.ts adds at the open, beside aria-expanded
  // every rule naming the attribute or the button's class, read as parsed rules with their enclosing at-rules in every sheet a
  // page of either host loads: none (the twin; the PR review's round 1 dropped it for the shared dress)
  for (const { name, css } of hostSheets(path.resolve(process.cwd(), ".."))) {
    assert.deepEqual(cssRules(css).filter((r) => /aria-expanded|fileview-outline-btn/.test(r.selector)).map(renderRule), [], name + ": a rule of the button's own, however the sheet writes it (the twin; the PR review's round 1 dropped it for the shared dress)");
  }
  // the dress it wears instead, in the pair where it is written, read at a line start as fileview-parity.test.ts reads heads
  const heads = (css: string): string[] => css.split("\n").filter((l) => /^[.#:@a-zA-Z[][^{]*\{/.test(l)).map((l) => l.slice(0, l.indexOf("{")).trim());
  for (const [sheet, css] of [["styles.css", CHAT], ["feed.css", FEED]] as const) {
    const hs = heads(css);
    const dress = hs.filter((h) => h === ".fileview-btn.on" || h === ".fileview-btn.on:hover");
    assert.deepEqual(dress, [".fileview-btn.on", ".fileview-btn.on:hover"], sheet + ": the bar's selected dress and its hover are there for it to wear: " + inspect(dress));
    assert.ok(outline.matches(".fileview-btn.on"), sheet + ": the open Outline button wears it");
    for (const h of dress) {
      assert.ok(!showLess.matches(h), sheet + ": `" + h + "` reaches the panel's Show less");
      assert.ok(!rejectAll.matches(h), sheet + ": `" + h + "` reaches the panel's armed Reject all");
      assert.ok(!showMore.matches(h), sheet + ": `" + h + "` reaches the panel's Show more");
    }
  }
});

// ── the PR review's round 1: the current row at the open, the focusout closer's three branches, a press on a row under a
// landing, a heading target under a plain hidden wrapper ──────────────────────────────────────────────────────────────────
test("the current row at the open is the section under the reader's eye (PR review round 1): the last heading with a box whose top sits at or above the body's top edge, named by aria-activedescendant too; a heading a pixel under the edge is not yet the section; a heading inside the shut fold has no box and is passed over; at the top of the note the first row (before the fix: the first row whatever the reader was reading)", async (t) => {
  const o = await open(REPORT, OUTLINE_NOTE, t);
  const heads = headings(o);
  const current = (pop: El): number => rowsOf(pop).findIndex((r) => r.classes.includes("current"));
  const boxed = (h: El): boolean => { const r = h.getBoundingClientRect(); return !(r.height === 0 && r.width === 0); };
  // the reader forty sections in: the heading whose block the body's edge sits on
  const target = heads[30];
  assert.ok(boxed(target), "the scene's heading has a box (a direct child of the rendered box)");
  o.body.scrollTop += target.getBoundingClientRect().top - EDGE;   // its top at the edge
  assert.equal(target.getBoundingClientRect().top, EDGE, "the scene: heading 31's top at the body's edge");
  let pop = openOutline(o);
  assert.equal(current(pop), 30, "the row of the heading at the edge is current (before the fix: row 0)");
  assert.equal(pop.getAttribute("aria-activedescendant"), rowsOf(pop)[30].id, "…and named for assistive technology");
  outlineBtn(o).click();
  // a pixel under the edge: the previous heading with a box is the section under the eye (the stand-in's margin is 0; a browser
  // allows the heading's scroll margin, the gap a landing leaves above it: file-view-outline-browser.test.ts)
  o.body.scrollTop -= 1;
  pop = openOutline(o);
  const prev = heads.slice(0, 30).map((h, i) => [h, i] as const).filter(([h]) => boxed(h)).pop()![1];
  assert.equal(current(pop), prev, "a heading a pixel under the edge is not yet the section: the previous one with a box is");
  outlineBtn(o).click();
  // the fold's heading (row 13, inside the shut details) has no box: with the edge on the fold's own block, the last heading with a
  // box before it is current (the quoted heading, row 12, has no box of its own in the stand-in either: it is inside the blockquote)
  const fold = heads[13];
  assert.equal(boxed(fold), false, "the fold's heading has no box (the details is shut)");
  const details = fold.closest("details")!;
  assert.ok(boxed(details), "the fold itself is a block of the note");
  o.body.scrollTop += details.getBoundingClientRect().top - EDGE;   // the fold's top at the edge
  const lastBoxed = heads.slice(0, 13).map((h, i) => [h, i] as const).filter(([h]) => boxed(h)).pop()![1];
  assert.ok(lastBoxed < 13 && lastBoxed >= 10, "the scene: a heading with a box stands a few rows before the fold (" + lastBoxed + ")");
  pop = openOutline(o);
  assert.equal(current(pop), lastBoxed, "the shut fold's heading is passed over for the last heading with a box at or above the edge");
  outlineBtn(o).click();
  // at the note's top: the first row, as before
  o.body.scrollTop = 0;
  pop = openOutline(o);
  assert.equal(current(pop), 0, "at the top the first row is current");
  assert.equal(pop.getAttribute("aria-activedescendant"), rowsOf(pop)[0].id);
});

test("the popover's focusout closer, one executed case per branch (PR review round 1): a move inside the popover or onto the Outline button leaves it standing; a move to another element of this document closes it and that element keeps the keyboard, the body taking nothing; a null relatedTarget while the popover holds the keyboard (the window losing the focus) closes it and hands the keyboard to the body", async (t) => {
  const o = await open(REPORT, OUTLINE_NOTE, t);
  let pop = openOutline(o);
  const rows = rowsOf(pop);
  assert.ok(doc.activeElement === pop, "the popover holds the keyboard at the open");
  // (1) inside the popover, and onto the button: the closer stands aside
  pop.dispatchEvent(new Ev("focusout", { relatedTarget: rows[3] }));
  assert.ok(popover(o) === pop, "a move inside the popover leaves it standing");
  pop.dispatchEvent(new Ev("focusout", { relatedTarget: outlineBtn(o) }));
  assert.ok(popover(o) === pop, "a move onto the button leaves it standing (the button's click is the toggle)");
  assert.equal(outlineBtn(o).getAttribute("aria-expanded"), "true");
  // (2) to another element of this document (a Tab out, a press on a bar button): closed, the element keeps the keyboard
  const dl = button(o, "Download")!;
  const focusedBefore = o.body.focused;
  doc.activeElement = doc.body;                                  // the browser's order: the old holder is unfocused when focusout fires
  pop.dispatchEvent(new Ev("focusout", { relatedTarget: dl }));
  dl.focus();                                                    // …and the new holder takes it after
  assert.equal(popover(o), null, "a move to another element closed the popover");
  assert.ok(doc.activeElement === dl, "that element keeps the keyboard");
  assert.equal(o.body.focused, focusedBefore, "the body took nothing");
  assert.equal(outlineBtn(o).getAttribute("aria-expanded"), "false");
  // (3) a null relatedTarget while the popover holds the keyboard: the window lost the focus; closed, the body takes it for the return
  pop = openOutline(o);
  assert.ok(doc.activeElement === pop);
  const f2 = o.body.focused;
  pop.dispatchEvent(new Ev("focusout", { relatedTarget: null }));
  assert.equal(popover(o), null, "a null relatedTarget closed the popover");
  assert.ok(doc.activeElement === o.body, "the body holds the keyboard (the popover's removal left it on the document's body; takeKeyboard took it)");
  assert.equal(o.body.focused, f2 + 1, "one focus call");
});

test("a landing under a press on a row waits for the release (PR review round 1): with the pointer down on the 40th row the panel's reload lands, the popover stands and nothing paints; the release's click picks the 40th heading, and the landing paints after it (before the fix: the hold was on the body alone, the landing painted at once, closeOutline removed the pressed row before the mouseup, and the pick was lost)", async (t) => {
  const o = await open(REPORT, OUTLINE_NOTE, t);
  const heads = headings(o);
  const pop = openOutline(o);
  const row = rowsOf(pop)[39];
  row.dispatchEvent(new Ev("pointerdown", { button: 0 }));       // the press, in the capture phase up to the card's hold
  const painted = paints;
  o.ctx.reload(); await settle();                                 // the panel's poll saw the file move: the landing
  assert.ok(popover(o) === pop, "the popover stands under the press: the landing waits (before the fix: the paint closed it and removed the pressed row)");
  assert.ok(row.parentNode === pop, "the pressed row is still in the popover");
  assert.equal(paints, painted, "nothing painted under the press");
  release();                                                      // the release: the click follows, then the parked landing on the hold's zero timer
  row.click();
  assert.equal(popover(o), null, "the click picked: the popover closed");
  assert.equal(heads[39].scrolled, 1, "…and the 40th heading landed");
  assert.deepEqual(heads[39].scrolledWith, { block: "start" });
  assert.ok(doc.activeElement === o.body, "the keyboard is on the body");
  await new Promise<void>((r) => setTimeout(r, 2)); await settle();
  assert.equal(paints, painted + 1, "then the landing painted, once");
  assert.equal(o.ctx.text(), OUTLINE_NOTE, "the reload's text is on screen");
  // a right press holds nothing (pressHold's rule), so a landing under it paints at once
  const pop2 = openOutline(o);
  rowsOf(pop2)[5].dispatchEvent(new Ev("pointerdown", { button: 2 }));
  const p2 = paints;
  o.ctx.reload(); await settle();
  assert.equal(paints, p2 + 1, "a right press on a row parks nothing: the landing painted");
  assert.equal(popover(o), null, "…and its paint closed the popover, as every paint does");
  release();
});

test("a heading target under a plain hidden wrapper (PR review round 1): the open lands at the top and the notice bar says so in the ruled words, nothing scrolled (before the fix: scrollToFragment found the boxless heading, moved nothing and counted the landing as done, no notice); a shown heading beside it lands with no notice; the notice is a polite live region", async (t) => {
  withFrames(t);
  const NOTE = "# Title\n\nText.\n\n<div hidden>\n\n## Stashed\n\nStashed text.\n\n</div>\n\n## Shown\n\nMore.\n";
  const fv = await mod();
  const o = await open(PLAIN, NOTE, t, false, { heading: "stashed" });
  const stashed = headings(o).find((h) => h.textContent === "Stashed")!;
  assert.ok(stashed && stashed.parentNode!.getAttribute("hidden") === "", "the scene: the heading is under a plain hidden wrapper");
  assert.equal(frames.length, 1, "the Rendered paint queued the landing's frame");
  flushFrames();
  assert.equal(noticeOf(o), "That section is hidden in the rendered view; opened at the top.", "the ruled words (before the fix: no notice)");
  assert.equal(noticeOf(o), fv.HIDDEN_SECTION, "…the module's export");
  assert.equal(o.card.querySelector("#fileview-save-err")!.getAttribute("role"), "status", "the notice announces itself");
  assert.equal(stashed.scrolled, 0, "nothing scrolled: there is no box to land on");
  assert.equal(o.body.scrollTop, 0, "the note stands at its top");
  o.fv.closeFileView();
  // the control: the shown heading lands as before, with no notice
  const c = await open(PLAIN, NOTE, t, false, { heading: "shown" });
  flushFrames();
  assert.equal(noticeOf(c), null, "a shown heading: no notice");
  const shown = headings(c).find((h) => h.textContent === "Shown")!;
  assert.equal(shown.scrolled, 1, "…and it landed"); assert.deepEqual(shown.scrolledWith, { block: "start" });
  c.fv.closeFileView();
  // a section the note lacks: the missing section's words, as before
  const m = await open(PLAIN, NOTE, t, false, { heading: "absent" });
  flushFrames();
  assert.equal(noticeOf(m), 'No section named "absent" in this file.', "a heading the note lacks keeps its own words");
});

// ── the stand-in's projection (ui/test-dom-shim.ts): a node inspects as its primitives, never as the tree ─────────────
test("a stand-in node enumerates its primitives alone, so a failing assertion's dump shows neither parentNode nor childNodes; the md box takes text as one node (no parse and no minting in the setter since Slice 7: the sanitizer's stand-in hands mdBlock the parsed markup and the real mintHeadingIds mints the ids, which the list case pins)", () => {
  const body = new El("div"); body.className = "fileview-body";
  const md = body.appendChild(new El("div")); md.className = "fileview-md";
  md.textContent = "# A\n\n## B\n\n## B\n";
  const only = md.childNodes[0];
  assert.ok(md.childNodes.length === 1 && only instanceof Txt && md.textContent === "# A\n\n## B\n\n## B\n", "one text node, as the browser's setter writes it");
  md.replaceChildren(...parseHTML("<h1>A</h1>\n<h2>B</h2>\n<h2>B</h2>\n"));
  const heads = md.querySelectorAll("h1, h2, h3, h4, h5, h6");
  assert.equal(heads.length, 3, "the parser the stand-in hands mdBlock's body through");
  for (const n of [body, md, heads[0], heads[0].childNodes[0]] as Array<El | Txt>) {
    for (const k of Object.keys(n)) assert.ok(staysEnumerable((n as any)[k]), k + " is enumerable and holds a " + typeof (n as any)[k]);
    const dump = inspect(n, { compact: false, customInspect: false, depth: 1000, maxArrayLength: Infinity, showHidden: false, showProxy: false, sorted: true, getters: true });
    assert.ok(!dump.includes("parentNode") && !dump.includes("childNodes"), "the dump holds no edge: " + dump);
  }
  assert.ok(heads[0].parentNode === md && md.childNodes[0] === heads[0], "the tree is reachable as before");
  assertHiddenEvent(new Ev("click"), body, heads[0]);
  const r = new El("div"); r.style.setProperty("--fv-ol-depth", "2");
  assert.equal(r.style.getPropertyValue("--fv-ol-depth"), "2", "the style stand-in keeps a set property");
});

// ── review round 3: a hidden heading has no row; the current row is named for assistive technology; a captioned figure's
// heading reads its alt text in place; Tab leaves through the button ──────────────────────────────────────────────────
test("review round 3: a heading inside a plain `hidden` wrapper has no row (its pick would land nowhere and say nothing) while one under hidden=\"until-found\" keeps its row, and a note whose only heading is hidden shows no Outline button; every row has an id and the popover names the current row through aria-activedescendant on the open, ArrowDown and End; a heading holding a picture AND text reads the picture's alt in place; Tab from the popover closes it and puts the keyboard on the Outline button with the key's default left to run, so the browser moves on to the next bar control", async (t) => {
  const NOTE = "# Title\n\nText.\n\n<div hidden>\n\n## Hidden heading\n\nStashed.\n\n</div>\n\n<div hidden=\"until-found\">\n\n## Findable heading\n\nFound.\n\n</div>\n\n## ![Figure 3: latency](figs/l.png) (detail)\n\nMore.\n\n## ![Only a picture](figs/b.png)\n\nEnd.\n";
  const o = await open(PLAIN, NOTE, t);
  const heads = headings(o);
  assert.equal(heads.length, 5, "the DOM holds every heading, the hidden one among them");
  const hiddenHead = heads.find((h) => h.textContent === "Hidden heading")!;
  assert.ok(hiddenHead && hiddenHead.parentNode!.getAttribute("hidden") === "", "the stand-in kept the plain hidden attribute on the wrapper (the sanitizer keeps it too)");
  const pop = openOutline(o);
  const rows = rowsOf(pop);
  assert.deepEqual(rows.map((r) => r.textContent), ["Title", "Findable heading", "Figure 3: latency (detail)", "Only a picture"],
    "no row for the heading under the plain hidden wrapper (before the fix: listed, and its pick moved nothing); the until-found one is listed, since the landing lifts that attribute; the captioned figure's row reads the alt text where the picture stands (before: \"(detail)\" alone); the image-only row reads its alt as before");
  assert.deepEqual(rows.map((r) => r.title), rows.map((r) => r.textContent), "the title carries the same words");
  // ids and the current row for assistive technology
  assert.ok(rows.every((r) => /^fileview-outline-\d+-\d+$/.test(r.id)), "every row has an id: " + rows.map((r) => r.id).join(","));
  assert.equal(new Set(rows.map((r) => r.id)).size, rows.length, "…unique");
  assert.equal(pop.getAttribute("aria-activedescendant"), rows[0].id, "the popover names the first row at the open (before the fix: no aria-activedescendant, and rows with no id)");
  key(pop, "ArrowDown");
  assert.equal(pop.getAttribute("aria-activedescendant"), rows[1].id, "…and follows ArrowDown");
  key(pop, "End");
  assert.equal(pop.getAttribute("aria-activedescendant"), rows[3].id, "…and End");
  assert.ok(rows[3].classes.includes("current"), "the class and the attribute name the same row");
  // Tab: the popover closes, the button holds the keyboard, the key's default runs (the browser's sequential navigation moves on from the button)
  const tab = key(pop, "Tab");
  assert.equal(popover(o), null, "Tab closed the popover");
  assert.ok(doc.activeElement === outlineBtn(o), "…and put the keyboard back on the Outline button (before the fix: the popover, the card's last child, kept it and the browser's Tab left the viewer for the first focusable behind the modal)");
  assert.ok(!tab.defaultPrevented && !tab.stopped, "the key's own default is left to run, so the focus moves from the button to the next bar control");
  assert.equal(outlineBtn(o).getAttribute("aria-expanded"), "false");
  // a second popover after the Tab: fresh ids of its own, the current row named again
  const again = openOutline(o);
  assert.notEqual(rowsOf(again)[0].id, rows[0].id, "a new open mints new ids (the old rows are gone)");
  assert.equal(again.getAttribute("aria-activedescendant"), rowsOf(again)[0].id);
  o.fv.closeFileView();
  // a note whose only heading is under a plain hidden wrapper: no row to offer, so no button
  const none = await open(PLAIN, "<div hidden>\n\n## Stashed\n\n</div>\n\nJust text.\n", t);
  assert.equal(headings(none).length, 1, "the DOM holds the hidden heading");
  assert.equal(outlineBtn(none).hidden, true, "…and the Outline button is hidden, as over a note with no heading");
});

test("a landing under a press on the Outline BUTTON (PR review round 2): the landing parks until the release; the release's click opens the popover and the parked landing's paint leaves it open on the landed body, the new note's rows with the keyboard on the popover (before the fix: the paint ran closeOutline one task after the click, so the click appeared to do nothing); a press on the button with the popover up: the click closes it and the landing leaves it closed; a landing with no press under way still closes an open popover", async (t) => {
  const MT2 = "1757145600000000009";
  const APPENDIX = "\n## Appendix Z\n\nOne more section a session wrote while the reader pressed the button.\n";
  const o = await open(REPORT, OUTLINE_NOTE, t);
  const btn = outlineBtn(o);
  btn.dispatchEvent(new Ev("pointerdown", { button: 0 }));       // the press on the button, in the capture phase up to the card's hold
  const painted = paints;
  disk[REPORT] = { bytes: OUTLINE_NOTE + APPENDIX, type: "text/plain; charset=utf-8", mtimeNs: MT2 };
  o.ctx.reload(); await settle();                                 // the panel's poll saw the file move: the landing parks under the press
  assert.equal(paints, painted, "nothing painted under the press");
  assert.equal(popover(o), null, "no popover yet: the click has not happened");
  release();                                                      // the release: the click follows, then the parked landing on the hold's zero timer
  btn.click();
  const first = popover(o);
  assert.ok(first, "the release's click opened the popover");
  assert.equal(rowsOf(first!).length, 42, "on the note that shows: the landing has not painted yet");
  await new Promise<void>((r) => setTimeout(r, 2)); await settle();
  assert.equal(paints, painted + 1, "then the parked landing painted, once");
  assert.equal(o.ctx.text(), OUTLINE_NOTE + APPENDIX, "the reload's text is on screen");
  const pop = popover(o);
  assert.ok(pop, "the popover stands after the landing's paint (before the fix: the paint closed it and the click appeared to do nothing)");
  assert.ok(pop !== first, "built afresh over the landed body, as every open of it is");
  assert.equal(rowsOf(pop!).length, 43, "its rows are the landed note's headings");
  assert.equal(rowsOf(pop!)[42].dataset.id, "md-appendix-z", "the last row is the heading the landing brought");
  assert.equal(btn.getAttribute("aria-expanded"), "true", "the button says it is expanded"); assert.ok(btn.classList.contains("on"), "…and wears the open dress");
  assert.ok(doc.activeElement === pop, "the popover holds the keyboard, as after any open");
  assert.ok(rowsOf(pop!).some((r) => r.classList.contains("current")), "with a current row");
  // the toggle's other half: a press on the button with the popover up parks the landing too; the click closes the popover, and the
  // landing leaves it closed (the reader closed it)
  btn.dispatchEvent(new Ev("pointerdown", { button: 0 }));
  const p2 = paints;
  disk[REPORT] = { bytes: OUTLINE_NOTE, type: "text/plain; charset=utf-8", mtimeNs: MT };
  o.ctx.reload(); await settle();
  assert.equal(paints, p2, "nothing painted under the press");
  assert.ok(popover(o) === pop, "the popover stands under the press: a press on the button is not a press outside it");
  release();
  btn.click();
  assert.equal(popover(o), null, "the click closed the popover");
  assert.ok(doc.activeElement === o.body, "…and the keyboard went to the body");
  await new Promise<void>((r) => setTimeout(r, 2)); await settle();
  assert.equal(paints, p2 + 1, "the parked landing painted");
  assert.equal(popover(o), null, "…and opened nothing: the click had closed it");
  assert.equal(btn.getAttribute("aria-expanded"), "false");
  // no press under way: a landing closes an open popover, as every paint does (the round-1 pin stands; nothing opens it again)
  openOutline(o);
  const p3 = paints;
  o.ctx.reload(); await settle();
  assert.equal(paints, p3 + 1, "a landing with no press behind it paints at once");
  assert.equal(popover(o), null, "…and closes the popover: the reader did not just ask for it");
});

// ── the picture's title and the control's words for a picture from the web, over the stand-in's paint (the file review's round 12,
// tests-1): the address with credentials is ASSEMBLED at run time through the URL API, never written as a literal (the repository's
// rule against credential-shaped literals in fixtures)
test("a picture from the web whose address carries credentials, and one whose address carries a written port, painted with the host loaded: the picture's title is the address with the username and password taken out and the port kept (shownAddress), after the author's title when one stands; the control's title PROPERTY and aria-label name the host with its port (targetHost), with the web class; the local picture keeps the one word set and no title. file-figure-open.test.ts pins the call site's spelling alone, so this executed case is what holds the strip: red under a `return href;` body (a property pin over the paint)", async (t) => {
  const cred = new URL("http://example.test/p.svg"); cred.username = "user"; cred.password = "pass";
  assert.deepEqual([cred.username, cred.password, cred.host, cred.pathname], ["user", "pass", "example.test", "/p.svg"], "the assembled address carries the credentials (read back as its parts: the whole is spelled nowhere in this file, not as a pattern either)");
  loadGatedHost("example.test", doc as unknown as ParentNode);   // the host on no list: lifted for this document before the paint (remoteHost keys on the hostname, so the ported address is lifted with it)
  t.after(() => { forgetLoadedHosts(); });   // a module-level set: cleared, so no other case paints example.test unlisted
  const o = await open(REPORT, '# R\n\n<img src="' + cred.href + '" alt="cred">\n\n<img src="http://example.test:8080/q.svg" alt="port" title="Figure 9">\n\n![local](figs/plot.svg)\n', t);
  const imgs = o.body.querySelector(".fileview-md")!.querySelectorAll("img");
  assert.deepEqual(imgs.map((i) => i.getAttribute("alt")), ["cred", "port", "local"], "the three pictures painted, none gated");
  assert.deepEqual(imgs.map((i) => i.getAttribute("title")), ["Opens in a new tab: http://example.test/p.svg", "Figure 9\nOpens in a new tab: http://example.test:8080/q.svg", null],
    "the picture's title: the address with its credentials emptied (never the username or the password in a tooltip), the port kept, the author's title first on its own line; the local picture none");
  const controls = imgs.map((i) => { const n = i.nextSibling; return n instanceof El && n.hasAttribute("data-fv-figopen") ? n : null; });
  assert.ok(controls.every((c) => c !== null), "a control after each picture (a stand-in is decided from its source: no floor, no state)");
  const words = ["Open the picture in a new tab at example.test", "Open the picture in a new tab at example.test:8080", "Open the picture"];
  assert.deepEqual(controls.map((c) => c!.title), words, "the control's title PROPERTY (dressFigureControl writes the property; no attribute is set here): the host with its port, never the credentials or the path");
  assert.deepEqual(controls.map((c) => c!.getAttribute("aria-label")), words, "and the aria-label, the same words");
  assert.deepEqual(controls.map((c) => c!.classList.contains("fv-figopen-web")), [true, true, false], "the web class on the two remote controls alone");
});

// ── a credential in the address's query or fragment (the file review's round 14, correctness-1): the picture's title shows origin
// plus path, the whole query and the whole fragment dropped beside the userinfo, so a raw link's token, a presigned URL's
// signature pair or an OAuth fragment never stands in a tooltip. Every address is assembled at run time through the URL API and
// every planted value from parts, so no credential-shaped literal stands in this file.
test("a picture from the web whose address carries a query token, an S3 presigned signature pair, a fragment access_token, a userinfo plus a query, or a query plus a fragment, painted with its hosts loaded: the picture's title is origin plus path alone (shownAddress), after the author's title when one stands, with no planted value in it; the control's words name the host as before (a property pin over the paint, red at the head the round read, where the title kept the query and the fragment)", async (t) => {
  const tok = "tok" + "en", qv = "Q" + "TOKVAL" + String(7 * 13);
  const q = new URL("https://example.test/q.svg"); q.searchParams.set(tok, qv);
  const s3 = new URL("https://bucket.example.test/fig.png");
  const cred = "AKID" + "EXAMPLE" + "/20260923/us-east-1/s3/aws4_request", sig = "abc" + "def0123456789" + "fedcba";
  s3.searchParams.set("X-Amz-Algorithm", "AWS4-HMAC-SHA256"); s3.searchParams.set("X-Amz-Credential", cred); s3.searchParams.set("X-Amz-Signature", sig);
  const fr = new URL("http://example.test/f.svg"), hv = "H" + "ASHVAL" + String(3 * 11); fr.hash = "access_" + "token=" + hv;
  const uq = new URL("http://example.test/c.svg"), us = "u" + "ser", pw = "p" + "w" + String(4 * 4), cv = "C" + "OMBO" + String(5 * 5);
  uq.username = us; uq.password = pw; uq.searchParams.set(tok, cv);
  const qf = new URL("http://example.test/p.svg"), sv = "S" + "ECRETVALUE", fv2 = "H" + "ASHVALUE"; qf.searchParams.set(tok, sv); qf.hash = "access_" + "token=" + fv2;
  assert.deepEqual([q.search.includes(qv), s3.search.includes("X-Amz-Signature=" + sig), fr.hash.includes(hv), uq.username, uq.password, uq.search.includes(cv), qf.search.includes(sv), qf.hash.includes(fv2)], [true, true, true, us, pw, true, true, true],
    "each assembled address carries its planted value (read back as parts)");
  const planted = [qv, cred, encodeURIComponent(cred), sig, "X-Amz-", hv, "access_", us + ":", pw, cv, sv, fv2, "?", "#"];
  loadGatedHost("example.test", doc as unknown as ParentNode); loadGatedHost("bucket.example.test", doc as unknown as ParentNode);   // the hosts on no list: lifted for this document before the paint
  t.after(() => { forgetLoadedHosts(); });
  const hrefs = [q.href, s3.href, fr.href, uq.href, qf.href];
  const o = await open(REPORT, "# R\n\n" + hrefs.map((h, i) => '<img src="' + h + '" alt="c' + i + '"' + (i === 1 ? ' title="Fig"' : "") + ">").join("\n\n") + "\n", t);
  const imgs = o.body.querySelector(".fileview-md")!.querySelectorAll("img");
  assert.deepEqual(imgs.map((i) => i.getAttribute("alt")), ["c0", "c1", "c2", "c3", "c4"], "the five pictures painted, none gated");
  const titles = imgs.map((i) => i.getAttribute("title"));
  assert.deepEqual(titles, ["Opens in a new tab: https://example.test/q.svg", "Fig\nOpens in a new tab: https://bucket.example.test/fig.png", "Opens in a new tab: http://example.test/f.svg", "Opens in a new tab: http://example.test/c.svg", "Opens in a new tab: http://example.test/p.svg"],
    "origin plus path in every title, the author's title first on its own line: no query, no fragment, no userinfo (a property pin over the title attribute)");
  for (const ti of titles) for (const x of planted) assert.ok(!(ti || "").includes(x), "no planted value in a title (a property pin): " + JSON.stringify(x) + " in " + JSON.stringify(ti));
  const words = imgs.map((i) => { const n = i.nextSibling; return n instanceof El && n.hasAttribute("data-fv-figopen") ? n.title : null; });
  assert.deepEqual(words, ["Open the picture in a new tab at example.test", "Open the picture in a new tab at bucket.example.test", "Open the picture in a new tab at example.test", "Open the picture in a new tab at example.test", "Open the picture in a new tab at example.test"],
    "the control's words name the host alone, as before (targetHost; a control, green at the head the round read by design)");
});

test("a picture from the web whose address the stand-in cannot resolve, a protocol-relative one (the node DOM has no base to resolve it against) and one with an out-of-range port, each carrying a userinfo and a query token: the picture's title is cut as text, no userinfo and nothing from the first ? (shownAddress's refused arm, which the label shares; in a browser neither loads, so neither gets a title there, and the failed label holds the same cut in file-view-figure-error.test.ts) (a property pin over the paint, red at the head the round read, where the title printed the address as written)", async (t) => {
  const tok = "tok" + "en", us = "u" + "ser", pw = "p" + "w" + String(4 * 4), v1 = "PR" + "TOK" + String(9 * 9), v2 = "UP" + "TOK" + String(8 * 8);
  const pr = "//" + us + ":" + pw + "@example.test/r.svg?" + tok + "=" + v1;
  const up = "http://" + us + ":" + pw + "@example.test:99999/u.svg?" + tok + "=" + v2;
  loadGatedHost("example.test", doc as unknown as ParentNode);
  t.after(() => { forgetLoadedHosts(); });
  const o = await open(REPORT, '# R\n\n<img src="' + pr + '" alt="pr">\n\n<img src="' + up + '" alt="up">\n', t);
  const imgs = o.body.querySelector(".fileview-md")!.querySelectorAll("img");
  assert.deepEqual(imgs.map((i) => i.getAttribute("alt")), ["pr", "up"], "the two pictures painted, none gated");
  const titles = imgs.map((i) => i.getAttribute("title"));
  assert.deepEqual(titles, ["Opens in a new tab: //example.test/r.svg", "Opens in a new tab: http://example.test:99999/u.svg"], "each title cut as text: the userinfo and the query gone, the port kept (a property pin over the title attribute)");
  for (const ti of titles) for (const x of [us + ":", pw, v1, v2, "?"]) assert.ok(!(ti || "").includes(x), "no planted value in a title (a property pin): " + JSON.stringify(x) + " in " + JSON.stringify(ti));
});
