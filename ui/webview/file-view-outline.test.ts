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
import { loadGatedHost, forgetLoadedHosts, remoteHost } from "./figure-gate";   // the gate lifted for a synthetic host before a paint of remote pictures (the picture-title cases; the sign-in table derives the hosts with the gate's own reader)
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
const urls: Record<string, string> = {};   // a URL document for the URL viewer, by its address (the sign-in table's URL-document rows)
(globalThis as any).fetch = async (url: string) => {
  if (url.startsWith("/version")) return { json: async () => ({ fileEditing: true }) };
  if (url.startsWith("/sessions")) return { json: async () => [{ id: SID, name: "api", bg: "#123456", fg: "#ffffff" }] };
  if (urls[url] !== undefined) return new Response(urls[url], { status: 200, headers: { "Content-Type": "text/markdown; charset=utf-8" } });   // the URL viewer streams a real Response's body (the figure-error suite's branch, so openUrlView paints through the real resolveFigureRefs)
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
// rule against credential-shaped literals in fixtures). Since the file review's round 15 (correctness-1 with extra9-2) a source that
// appears to carry a sign-in shows the withheld address on every surface, and any other address its origin alone.
/** The words in a withheld address's place and each surface's frame around them, as the ruling's wording reads (literals, so the
 *  expected text never moves with the product: file-view.ts FIGURE_ADDRESS_WITHHELD, figureWebTitleLine, FIGURE_OPEN_WEB_WITHHELD). */
const WITHHELD = "address withheld because it appears to carry a sign-in";
const WITHHELD_TITLE = "Opens in a new tab: " + WITHHELD;
const WITHHELD_WORDS = "Open the picture in a new tab (" + WITHHELD + ")";
test("a picture from the web whose address carries credentials, and one whose address carries a written port, painted with the host loaded: the credentialed picture's title and its control's title PROPERTY and aria-label show the withheld address in their own frames and no part of the address (figureSourceCredentialed, since the file review's round 15, tests-1 with extra9-3: the control's words print the parse, which reads some sign-in spellings as a host and a port, so they read the rule first, at that rule's stated cost, a harmless address with an at sign after its scheme (https://cdn/img/a@2x.png) withheld too); the ported picture's title is its origin, the port kept, after the author's title, and its control names the host with its port (targetHost), with the web class; the local picture keeps the one word set and no title. file-figure-open.test.ts pins the call sites' spelling alone, so this executed case holds the property: red under a `return href;` body or a words line that skips the rule (a property pin over the paint)", async (t) => {
  const cred = new URL("http://example.test/p.svg"); cred.username = "user"; cred.password = "pass";
  assert.deepEqual([cred.username, cred.password, cred.host, cred.pathname], ["user", "pass", "example.test", "/p.svg"], "the assembled address carries the credentials (read back as its parts: the whole is spelled nowhere in this file, not as a pattern either)");
  loadGatedHost("example.test", doc as unknown as ParentNode);   // the host on no list: lifted for this document before the paint (remoteHost keys on the hostname, so the ported address is lifted with it)
  t.after(() => { forgetLoadedHosts(); });   // a module-level set: cleared, so no other case paints example.test unlisted
  const o = await open(REPORT, '# R\n\n<img src="' + cred.href + '" alt="cred">\n\n<img src="http://example.test:8080/q.svg" alt="port" title="Figure 9">\n\n![local](figs/plot.svg)\n', t);
  const imgs = o.body.querySelector(".fileview-md")!.querySelectorAll("img");
  assert.deepEqual(imgs.map((i) => i.getAttribute("alt")), ["cred", "port", "local"], "the three pictures painted, none gated");
  assert.deepEqual(imgs.map((i) => i.getAttribute("title")), [WITHHELD_TITLE, "Figure 9\nOpens in a new tab: http://example.test:8080", null],
    "the picture's title: the withheld address for the credentialed one (never the username, the password or the path in a tooltip; the sign-in rule's stated cost withholds a harmless address with an at sign after its scheme too, the sign-in table's cost rows), the origin with its port for the other, the author's title first on its own line; the local picture none");
  const controls = imgs.map((i) => { const n = i.nextSibling; return n instanceof El && n.hasAttribute("data-fv-figopen") ? n : null; });
  assert.ok(controls.every((c) => c !== null), "a control after each picture (a stand-in is decided from its source: no floor, no state)");
  const words = [WITHHELD_WORDS, "Open the picture in a new tab at example.test:8080", "Open the picture"];
  assert.deepEqual(controls.map((c) => c!.title), words, "the control's title PROPERTY (dressFigureControl writes the property; no attribute is set here): the withheld address for the credentialed picture, the host with its port for the other, never a credential or a path");
  assert.deepEqual(controls.map((c) => c!.getAttribute("aria-label")), words, "and the aria-label, the same words");
  assert.deepEqual(controls.map((c) => c!.classList.contains("fv-figopen-web")), [true, true, false], "the web class on the two remote controls alone");
});

// ── a credential in the address's query or fragment (the file review's round 14, correctness-1): the picture's title drops the whole
// query and the whole fragment, so a raw link's token, a presigned URL's signature pair or an OAuth fragment never stands in a
// tooltip, and since the file review's round 15 (extra9-2) the path too, the title showing the origin alone. Every address is
// assembled at run time through the URL API and every planted value from parts, so no credential-shaped literal stands in this file.
test("a picture from the web whose address carries a query token, an S3 presigned signature pair, a fragment access_token, a userinfo plus a query, or a query plus a fragment, painted with its hosts loaded: the picture's title is its origin alone (shownAddress), after the author's title when one stands, and the withheld address for the one with a userinfo (figureSourceCredentialed), with no planted value and no path in any; the control's words name the host, and the withheld address for the userinfo (a property pin over the paint, red at the head the round read, where the title kept the path)", async (t) => {
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
  const planted = [qv, cred, encodeURIComponent(cred), sig, "X-Amz-", hv, "access_", us + ":", pw, cv, sv, fv2, "?", "#", ".svg", ".png"];
  loadGatedHost("example.test", doc as unknown as ParentNode); loadGatedHost("bucket.example.test", doc as unknown as ParentNode);   // the hosts on no list: lifted for this document before the paint
  t.after(() => { forgetLoadedHosts(); });
  const hrefs = [q.href, s3.href, fr.href, uq.href, qf.href];
  const o = await open(REPORT, "# R\n\n" + hrefs.map((h, i) => '<img src="' + h + '" alt="c' + i + '"' + (i === 1 ? ' title="Fig"' : "") + ">").join("\n\n") + "\n", t);
  const imgs = o.body.querySelector(".fileview-md")!.querySelectorAll("img");
  assert.deepEqual(imgs.map((i) => i.getAttribute("alt")), ["c0", "c1", "c2", "c3", "c4"], "the five pictures painted, none gated");
  const titles = imgs.map((i) => i.getAttribute("title"));
  assert.deepEqual(titles, ["Opens in a new tab: https://example.test", "Fig\nOpens in a new tab: https://bucket.example.test", "Opens in a new tab: http://example.test", WITHHELD_TITLE, "Opens in a new tab: http://example.test"],
    "the origin alone in every title, the author's title first on its own line, and the withheld address for the userinfo: no path, no query, no fragment, no userinfo (a property pin over the title attribute)");
  for (const ti of titles) for (const x of planted) assert.ok(!(ti || "").includes(x), "no planted value in a title (a property pin): " + JSON.stringify(x) + " in " + JSON.stringify(ti));
  const words = imgs.map((i) => { const n = i.nextSibling; return n instanceof El && n.hasAttribute("data-fv-figopen") ? n.title : null; });
  assert.deepEqual(words, ["Open the picture in a new tab at example.test", "Open the picture in a new tab at bucket.example.test", "Open the picture in a new tab at example.test", WITHHELD_WORDS, "Open the picture in a new tab at example.test"],
    "the control's words name the host alone (targetHost), and the withheld address for the userinfo (figureSourceCredentialed)");
});

test("a picture from the web whose address the stand-in cannot resolve, a protocol-relative one (the node DOM has no base to resolve it against) and one with an out-of-range port: each carrying a userinfo and a query token shows the withheld address in its title and its control's words (figureSourceCredentialed), and each carrying a query token alone shows its authority cut, no path and nothing from the first ?, in its title and in its control's words (shownAddress's and targetHost's refused arm, authorityCut, which the label shares; in a browser neither loads, so neither gets a title there, and the failed label holds the same cut in file-view-figure-error.test.ts) (a property pin over the paint, red at the head the round read, where the title printed the path and the control's words the address as written)", async (t) => {
  const tok = "tok" + "en", us = "u" + "ser", pw = "p" + "w" + String(4 * 4), v1 = "PR" + "TOK" + String(9 * 9), v2 = "UP" + "TOK" + String(8 * 8), v3 = "PN" + "TOK" + String(7 * 7), v4 = "UN" + "TOK" + String(6 * 6);
  const pr = "//" + us + ":" + pw + "@example.test/r.svg?" + tok + "=" + v1;
  const up = "http://" + us + ":" + pw + "@example.test:99999/u.svg?" + tok + "=" + v2;
  const pn = "//example.test/rn.svg?" + tok + "=" + v3;
  const un = "http://example.test:99999/un.svg?" + tok + "=" + v4;
  loadGatedHost("example.test", doc as unknown as ParentNode);
  t.after(() => { forgetLoadedHosts(); });
  const o = await open(REPORT, "# R\n\n" + [[pr, "pr"], [up, "up"], [pn, "pn"], [un, "un"]].map(([s, a]) => '<img src="' + s + '" alt="' + a + '">').join("\n\n") + "\n", t);
  const imgs = o.body.querySelector(".fileview-md")!.querySelectorAll("img");
  assert.deepEqual(imgs.map((i) => i.getAttribute("alt")), ["pr", "up", "pn", "un"], "the four pictures painted, none gated");
  const titles = imgs.map((i) => i.getAttribute("title"));
  assert.deepEqual(titles, [WITHHELD_TITLE, WITHHELD_TITLE, "Opens in a new tab: //example.test", "Opens in a new tab: http://example.test:99999"], "the two with a userinfo withheld, the two without cut at their authority, the port kept (a property pin over the title attribute)");
  const words = imgs.map((i) => { const n = i.nextSibling; return n instanceof El && n.hasAttribute("data-fv-figopen") ? n.title : null; });
  assert.deepEqual(words, [WITHHELD_WORDS, WITHHELD_WORDS, "Open the picture in a new tab at //example.test", "Open the picture in a new tab at http://example.test:99999"], "the control's words: withheld, and for a refused address its authority cut (targetHost's fallback, which printed the address as written, query and all)");
  for (const s of [...titles, ...words]) for (const x of [us + ":", pw, v1, v2, v3, v4, "?", ".svg"]) assert.ok(!(s || "").includes(x), "no planted value and no path in a title or the control's words (a property pin): " + JSON.stringify(x) + " in " + JSON.stringify(s));
});

// ── the sign-in rule over the paint (the file review's round 15, correctness-1 with extra5-1, extra6-2, tests-1 and extra9-3, on the
// coordinator's decision): the rule that replaced the disclosed residual of two credential spellings, whose witness stood here. The
// URL parser reads many spellings of a sign-in with no userinfo, as a host and a port, a path of the page's own origin or an opaque
// path, so the viewer's words read the source's text instead: an at sign (ASCII, U+FF20 or U+FE6B, after the percent-escapes are
// decoded until the text stops changing) anywhere after a scheme other than data: or a leading run of two or more slashes or
// backslashes, in the head a data: source's label prints, or after a colon in a source with neither, withholds the whole address on
// every surface: the picture's title line, the web control's title property and aria-label, and the failed label. One table, each
// row painted over the stand-in (real marked, the sanitizer's stand-in, the real rewrite, gate and decision) on the base it names,
// then failed through the real error listener; the stand-in keeps a web picture's control through the error, so a web row reads all
// four surfaces here. A row that is not a web target (s3:, data:, and on the Files pane a workspace path: the two-backslash, the
// leading-control, the tab-in-scheme and the schemeless forms) has no title, and its control, where one stands, is the local one.
// Each row is red at the head the round read on each surface that printed any part of its address (every surface, since none
// withheld it), and each surface's print there is recorded as a diagnostic line of this case, so the run at either head shows what
// printed. The cost rows print their address at that head and show the withheld address now: the rule's stated cost. The controls,
// outside the rule, print their words at both heads. Every value is assembled at run time.
test("the sign-in rule over the paint, one table (the file review's round 15, correctness-1): every spelling the rulings name, the refuters' (https: with no slash, one slash or one backslash on an https base; http: likewise, and HTTP:, on an http base; a tab before one slash; a password beginning with a slash or a backslash; a numeric head before a backslash; a backslash in the sign-in name; s3:), those an authority-only rule missed (a numeric password head before a /, a ? or a #; a token or a name holding a slash; https: with a numeric head on an https base), the leading run, the tab and control-character forms, the schemeless forms marked renders, the encoded, double-encoded and lookalike at signs, the data: forms, a data: head past 40 characters to its comma, two leading backslashes before a token with no colon, percent-encoded colons before a sign-in, and a plain userinfo or token on an http, an https and a VS Code webview base, and on a URL document the two-backslash form, shows the withheld address and no part of itself on every surface it has: the picture's title line, the control's title property and aria-label, and the failed label; a picture in a fold's own summary and one in a link holding it alone carry it in the control's words, their title withheld; the cost rows (an @ in a web address's path, a profile path, a refused address with an @, a relative a@2x.png on a URL document) are withheld too; the controls print as before: a relative a@2x.png on the Files pane, an inline svg holding @media after its comma, past or inside its first 40 characters, a ported address as its origin, a refused one cut at its authority, at a slash or a backslash (a property pin over the paint, red at the head the round read on each surface that printed)", async (t) => {
  const fv = await mod();
  const US = "u" + "ser", PW = "p" + "w" + String(4 * 4), PORT = String(2000 + 24), TK = "tok" + "en", H = "example.test", BS = "\\", TAB = "\t";
  const SIGN = US + ":" + PW + "@", NUM = US + ":" + PORT;
  const FF20 = String.fromCharCode(0xff20), FE6B = String.fromCharCode(0xfe6b), ZW = String.fromCharCode(0x200b), C1 = String.fromCharCode(1);
  const BASES: Record<string, string> = { http: "http://notes-api.test/", https: "https://notes-api.test/", vscode: "vscode-webview://abc123/index.html?id=x" };
  const ALL = ["http", "https", "vscode"];
  /** A row: its markup (raw HTML, attribute text written with entities where a character must reach the attribute, or markdown), the
   *  source the viewer must hold for it (read back before any surface: data-fv-src when the viewer rewrote the src, else src), whether
   *  it is a web target, the bases it paints on, and the parts of its address that must never print. */
  type Row = { name: string; md: (alt: string) => string; holds: string; web: boolean; bases: string[]; planted: string[]; place?: "fold" | "link" };
  const html = (attr: string) => (alt: string) => '<img src="' + attr + '" alt="' + alt + '">';
  const raw = (src: string, name: string, web: boolean, bases: string[], planted: string[]): Row => ({ name, md: html(src), holds: src, web, bases, planted });
  const ent = (attr: string, holds: string, name: string, web: boolean, bases: string[], planted: string[]): Row => ({ name, md: html(attr), holds, web, bases, planted });
  const mdRow = (dest: string, holds: string, name: string, web: boolean, bases: string[], planted: string[]): Row => ({ name, md: (alt) => "![" + alt + "](" + dest + ")", holds, web, bases, planted });
  const rows: Row[] = [
    // the refuters' spellings
    raw("https:" + SIGN + H + "/x.png", "https: with no slash, on an https base (the phone's road)", true, ["https"], [PW, US + ":"]),
    raw("https:/" + SIGN + H + "/x.png", "https: with one slash, on an https base", true, ["https"], [PW, US + ":"]),
    raw("https:" + BS + SIGN + H + "/x.png", "https: with one backslash, on an https base", true, ["https"], [PW, US + ":"]),
    raw("http:" + SIGN + H + "/a.png", "http: with no slash, on an http base (the withdrawn residual's second spelling)", true, ["http"], [PW, US + ":"]),
    raw("http:/" + SIGN + H + "/a.png", "http: with one slash, on an http base", true, ["http"], [PW, US + ":"]),
    raw("http:" + BS + SIGN + H + "/a.png", "http: with one backslash, on an http base", true, ["http"], [PW, US + ":"]),
    raw("HTTP:" + SIGN + H + "/a.png", "HTTP: in upper case, on an http base", true, ["http"], [PW, US + ":"]),
    ent("http:&#9;/" + SIGN + H + "/x.png", "http:" + TAB + "/" + SIGN + H + "/x.png", "http: with a tab before its one slash, on an http base", true, ["http"], [PW, US + ":"]),
    raw("http://" + US + ":/" + PW + "@" + H + "/e.png", "a password that begins with a slash", true, ALL, [PW, US]),
    raw("http://" + US + ":" + BS + PW + "@" + H + "/e.png", "a password that begins with a backslash", true, ALL, [PW, US]),
    raw("http://" + NUM + BS + PW + "@" + H + "/i.png", "a numeric password head followed by a backslash", true, ALL, [PW, NUM]),
    raw("http://" + US + BS + PW + "@" + H + "/i.png", "a sign-in name holding a backslash", true, ALL, [PW, US]),
    raw("s3:" + SIGN + H + "/a.png", "s3: written without slashes (the label only: no target)", false, ALL, [PW, US + ":"]),
    // the spellings a rule reading the authority alone missed
    raw("http://" + NUM + "/" + PW + "@" + H + "/i.png", "a numeric password head, then a / (the withdrawn residual's first spelling)", true, ALL, [PW, NUM]),
    raw("http://" + NUM + "?" + PW + "@" + H + "/j.png", "a numeric password head, then a ?", true, ALL, [PW, NUM]),
    raw("http://" + NUM + "#" + PW + "@" + H + "/k.png", "a numeric password head, then a #", true, ALL, [PW, NUM]),
    raw("http://" + TK.slice(0, 3) + "/" + TK.slice(3) + "16@" + H + "/t.png", "a sign-in token holding a slash", true, ALL, [TK.slice(3) + "16", TK.slice(0, 3) + "/"]),
    raw("http://" + US + "/x:" + PW + "@" + H + "/t.png", "a sign-in name holding a slash before its password", true, ALL, [PW, US]),
    raw("https://AbCx/dEf" + String(4 * 33) + "@img." + H + "/b.png", "a mixed-case token holding a slash", true, ALL, ["dEf" + String(4 * 33), "AbCx", "abcx"]),
    raw("https:" + NUM + "?" + PW + "@" + H + "/x.png", "https: with a numeric password head and a ?, on an https base", true, ["https"], [PW, NUM]),
    // the leading run
    raw("//" + SIGN + H + "/x.png", "a leading // before a userinfo", true, ALL, [PW, US + ":"]),
    raw("//" + TK + "@" + H + "/x.png", "a leading // before a token with no colon", true, ALL, [TK]),
    raw("//" + NUM + "/" + PW + "@" + H + "/x.png", "a leading // before a numeric password head and a /", true, ALL, [PW, NUM]),
    raw("//" + NUM + BS + PW + "@" + H + "/x.png", "a leading // before a numeric password head and a backslash", true, ALL, [PW, NUM]),
    raw(BS + BS + NUM + "/" + PW + "@" + H + "/x.png", "two leading backslashes, a workspace path on the Files pane (the label only)", false, ALL, [PW, NUM]),
    raw(BS + BS + TK + "@" + H + "/x.png", "two leading backslashes before a token with no colon, a workspace path on the Files pane (the label only; the row that holds backslashes in the leading run, since with no colon the schemeless clause cannot catch it)", false, ALL, [TK]),
    // the parser's normalisation: a tab inside the scheme and a leading control character, in raw HTML
    ent("ht&#9;tp://" + NUM + "/" + PW + "@" + H + "/i.png", "ht" + TAB + "tp://" + NUM + "/" + PW + "@" + H + "/i.png", "raw HTML with a tab inside the scheme, a workspace path here (the label only)", false, ALL, [PW, NUM]),
    ent("ht&#9;tp:" + SIGN + H + "/a.png", "ht" + TAB + "tp:" + SIGN + H + "/a.png", "raw HTML with a tab inside a slashless scheme, on an http base (the label only)", false, ["http"], [PW, US + ":"]),
    ent("&#1;http://" + NUM + "/" + PW + "@" + H + "/i.png", C1 + "http://" + NUM + "/" + PW + "@" + H + "/i.png", "raw HTML with a leading control character (the label only)", false, ALL, [PW, NUM]),
    // the schemeless forms, workspace paths on the Files pane (the label only)
    mdRow("<ht" + TAB + "tp://" + NUM + "/" + PW + "@" + H + "/i.png>", "ht%09tp://" + NUM + "/" + PW + "@" + H + "/i.png", "markdown with a tab inside the scheme, which marked writes as %09", false, ALL, [PW, NUM]),
    mdRow("<" + C1 + "http://" + NUM + "/" + PW + "@" + H + "/i.png>", "%01http://" + NUM + "/" + PW + "@" + H + "/i.png", "markdown with a leading control character, which marked writes as %01", false, ALL, [PW, NUM]),
    mdRow(ZW + "http://" + NUM + "/" + PW + "@" + H + "/i.png", "%E2%80%8Bhttp://" + NUM + "/" + PW + "@" + H + "/i.png", "markdown with a pasted zero-width space before the scheme", false, ALL, [PW, NUM]),
    mdRow("./http://" + SIGN + H + "/x.png", "./http://" + SIGN + H + "/x.png", "markdown with ./ before the scheme", false, ALL, [PW, US + ":"]),
    raw("http%3a%2f%2f" + US + "%3a" + PW + "@" + H + "/x.png", "percent-encoded colons and slashes before a sign-in, schemeless as written (the row that holds the schemeless clause's colon read on the decoded text, since the text as written has no colon)", false, ALL, [PW]),
    ent("&#127;http://" + NUM + "/" + PW + "@" + H + "/i.png", String.fromCharCode(127) + "http://" + NUM + "/" + PW + "@" + H + "/i.png", "raw HTML with a leading U+007F", false, ALL, [PW, NUM]),
    ent("&#8203;http://" + NUM + "/" + PW + "@" + H + "/i.png", ZW + "http://" + NUM + "/" + PW + "@" + H + "/i.png", "raw HTML with a leading U+200B", false, ALL, [PW, NUM]),
    ent("&#1;//" + TK + "@" + H + "/x.png", C1 + "//" + TK + "@" + H + "/x.png", "raw HTML with a leading control character before //token, no colon (red at the head the round read by the missing words: its label dropped the token)", false, ALL, [TK]),
    // the encoded and lookalike at signs
    raw("http://" + US + ":" + PW + "%40" + H + "/x.png", "a %40 in place of the at sign, which the parser refuses", true, ALL, [PW, US + ":"]),
    raw("http://" + TK.slice(0, 3) + "%40" + H + "/x.png", "a token before a %40, which the parser refuses", true, ALL, [TK.slice(0, 3) + "%40"]),
    raw("https:" + US + ":" + PW + "%40" + H + "/x.png", "https: with no slash and a %40, on an https base", true, ["https"], [PW, US + ":"]),
    mdRow("https:" + US + ":" + PW + FF20 + H + "/x.png", "https:" + US + ":" + PW + "%EF%BC%A0" + H + "/x.png", "markdown https: with no slash and a fullwidth at sign, which marked writes as %EF%BC%A0, on an https base", true, ["https"], [PW, US + ":"]),
    mdRow("https:" + US + ":" + PW + FE6B + H + "/x.png", "https:" + US + ":" + PW + "%EF%B9%AB" + H + "/x.png", "markdown https: with no slash and a small at sign, which marked writes as %EF%B9%AB, on an https base", true, ["https"], [PW, US + ":"]),
    ent("https:" + US + ":" + PW + "&#xFF20;" + H + "/x.png", "https:" + US + ":" + PW + FF20 + H + "/x.png", "raw HTML https: with no slash and a fullwidth at sign, on an https base", true, ["https"], [PW, US + ":"]),
    ent("https:" + US + ":" + PW + "&#xFE6B;" + H + "/x.png", "https:" + US + ":" + PW + FE6B + H + "/x.png", "raw HTML https: with no slash and a small at sign, on an https base", true, ["https"], [PW, US + ":"]),
    mdRow("http://" + US + ":" + PW + FF20 + H + "/x.png", "http://" + US + ":" + PW + "%EF%BC%A0" + H + "/x.png", "markdown http:// with a fullwidth at sign, which the parser refuses", true, ALL, [PW, US + ":"]),
    raw("http://" + US + ":" + PW + "%2540" + H + "/x.png", "a double-encoded at sign, which the parser refuses", true, ALL, [PW, US + ":"]),
    // the data: forms (the label only)
    raw("data://" + SIGN + H + "/x.png", "raw HTML data: with a sign-in in its printed head", false, ALL, [PW, US + ":"]),
    mdRow("data://" + SIGN + H + "/x.png", "data://" + SIGN + H + "/x.png", "markdown data: with a sign-in in its printed head", false, ALL, [PW, US + ":"]),
    raw("data://" + SIGN + H + "/,x", "raw HTML data: with a sign-in before its comma", false, ALL, [PW, US + ":"]),
    mdRow("data://" + SIGN + H + "/,x", "data://" + SIGN + H + "/,x", "markdown data: with a sign-in before its comma", false, ALL, [PW, US + ":"]),
    raw("data:image/png;name=" + "a".repeat(24) + ";" + SIGN + "x,AAAA", "raw HTML data: whose head runs past 40 characters to a sign-in before its comma (the row that holds the head read through the comma, not cut at 40)", false, ALL, [PW, US + ":"]),
    // a plain userinfo and a token
    raw("https://" + SIGN + H + "/x.png", "a standard userinfo (red at the head the round read by the missing words: its sign-in part was dropped, its path printed)", true, ALL, [PW, US + ":"]),
    raw("https://" + TK + "@" + H + "/x.png", "a username-only token (red there the same way)", true, ALL, [TK]),
    // the placements where the control is the only surface carrying the address: a fold's own summary, a link holding the picture alone
    { name: "a credentialed picture in a details element's own first summary (the title withheld, the control carries the words)", md: (alt) => '<details><summary><img src="http://' + NUM + "/" + PW + "@" + H + '/i.png" alt="' + alt + '"> fold</summary>body</details>', holds: "http://" + NUM + "/" + PW + "@" + H + "/i.png", web: true, bases: ["http"], planted: [PW, NUM], place: "fold" },
    { name: "a credentialed picture in a link holding it alone (the title withheld, the control carries the words)", md: (alt) => '<a href="https://notes-api.test/next"><img src="http://' + NUM + "/" + PW + "@" + H + '/i.png" alt="' + alt + '"></a>', holds: "http://" + NUM + "/" + PW + "@" + H + "/i.png", web: true, bases: ["http"], planted: [PW, NUM], place: "link" },
  ];
  /** The rule's cost: harmless addresses withheld, printed whole at the head the round read. */
  const cost: Row[] = [
    raw("https://cdn/img/a@2x.png", "the cost: an at sign in a web address's path", true, ALL, ["cdn", "a@2x"]),
    raw("https://social.example/@api/avatar.png", "the cost: a profile path", true, ALL, ["social.example", "@api"]),
    raw("http://" + H + ":99999/a@2x.png", "the cost: a refused address with an at sign in its path (the file review's round 14 cut printed a wrong host)", true, ALL, ["99999", "2x.png"]),
  ];
  /** The controls, outside the rule: [row, the label's source, the title (null for none), the control's words (null for none)]. */
  const controls: Array<[Row, string, string | null, string | null]> = [
    [raw("a@2x.png", "a relative a@2x.png on the Files pane, a workspace path with no colon before its at sign", false, ALL, []), "a@2x.png", null, "Open the picture"],
    [ent("data:image/svg+xml;utf8,&lt;svg xmlns='http://www.w3.org/2000/svg'&gt;&lt;style&gt;@media (min-width:1px){rect{fill:red}}&lt;/style&gt;&lt;rect width='4' height='4'/&gt;&lt;/svg&gt;", "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg'><style>@media (min-width:1px){rect{fill:red}}</style><rect width='4' height='4'/></svg>", "an inline svg whose CSS holds @media after the comma (the rule reads a data: source's printed head alone)", false, ALL, []), "data:image/svg+xml;utf8,…", null, null],
    [raw("http://" + H + ":8080/a.png", "a ported address: its origin, and the host with its port in the control's words", true, ALL, []), "http://" + H + ":8080", "Opens in a new tab: http://" + H + ":8080", "Open the picture in a new tab at " + H + ":8080"],
    [raw("http://" + H + ":99999/a.png", "a refused address: its authority cut", true, ALL, []), "http://" + H + ":99999", "Opens in a new tab: http://" + H + ":99999", "Open the picture in a new tab at http://" + H + ":99999"],
    [ent("data:image/svg+xml;utf8,&lt;svg&gt;&lt;style&gt;@media{}&lt;/style&gt;&lt;/svg&gt;", "data:image/svg+xml;utf8,<svg><style>@media{}</style></svg>", "a short inline svg whose @media stands after the comma and inside the first 40 characters (kept: the head is read through the comma, not cut at 40)", false, ALL, []), "data:image/svg+xml;utf8,…", null, null],
    [raw("http://" + H + ":99999" + BS + "seg9" + BS + "x.png", "a refused address with a backslash after its authority: cut at the backslash", true, ALL, []), "http://" + H + ":99999", "Opens in a new tab: http://" + H + ":99999", "Open the picture in a new tab at http://" + H + ":99999"],
  ];
  t.after(() => { delete (doc as any).baseURI; forgetLoadedHosts(); });
  const fails: string[] = [];
  const surfacesOf = (img: El): { title: string | null; words: string | null; aria: string | null; web: boolean | null; label: string | null } => {
    const a = img.parentNode instanceof El && img.parentNode.tagName === "A" && img.parentNode.children.length === 1 ? img.parentNode : img;
    const c = a.nextSibling instanceof El && a.nextSibling.hasAttribute("data-fv-figopen") ? a.nextSibling : null;
    const l = (c || a).nextSibling;
    return { title: img.getAttribute("title"), words: c ? c.title : null, aria: c ? c.getAttribute("aria-label") : null, web: c ? c.classList.contains("fv-figopen-web") : null, label: l instanceof El && l.hasAttribute("data-fv-figerr") ? l.textContent : null };
  };
  const heldOf = (img: El): string | null => img.hasAttribute("data-fv-src") ? img.getAttribute("data-fv-src") : img.getAttribute("src");
  for (const b of ALL) {
    const base = BASES[b];
    const here = [...rows, ...cost].filter((r) => r.bases.includes(b));
    const ctl = controls.filter(([r]) => r.bases.includes(b));
    (doc as any).baseURI = base;   // the stand-in's document has no base: the page's own address, as document.baseURI reads there
    for (const r of [...here, ...ctl.map(([r]) => r)]) { const h = remoteHost(r.holds, base); if (h) loadGatedHost(h, doc as unknown as ParentNode); }   // the hosts the gate would hold, lifted before the paint (derived with the gate's own reader)
    const alts = [...here.map((_, i) => "r" + i), ...ctl.map((_, i) => "k" + i)];
    const o = await open(REPORT, "# R\n\n" + [...here, ...ctl.map(([r]) => r)].map((r, i) => r.md(alts[i])).join("\n\n") + "\n", t);
    const imgs = o.body.querySelector(".fileview-md")!.querySelectorAll("img");
    const byAlt = new Map(imgs.map((i) => [i.getAttribute("alt"), i] as [string | null, El]));
    for (const alt of alts) {
      const i = byAlt.get(alt);
      assert.ok(i, b + ": the row " + alt + " painted an img");
      assert.equal(i!.closest('[data-act="fv-load"]'), null, b + ": the row " + alt + " is not gated (a gated figure has no src, no title and no error: a silent green)");
    }
    here.forEach((r, k) => assert.equal(heldOf(byAlt.get("r" + k)!), r.holds, b + ": " + r.name + ": the source the viewer holds is the spelling the row means (read back before any surface)"));
    ctl.forEach(([r], k) => assert.equal(heldOf(byAlt.get("k" + k)!), r.holds, b + ": " + r.name + ": the source the viewer holds"));
    for (const i of imgs) i.dispatchEvent(new Ev("error"));
    here.forEach((r, k) => {
      const alt = "r" + k, s = surfacesOf(byAlt.get(alt)!);
      t.diagnostic(b + " " + alt + " " + JSON.stringify(r.name) + " printed " + JSON.stringify(s));
      const want = {
        title: r.web && !r.place ? WITHHELD_TITLE : null,
        words: r.web ? WITHHELD_WORDS : null, aria: r.web ? WITHHELD_WORDS : null, web: r.web ? true : null,
        label: fv.FIGURE_FAILED + " " + WITHHELD + " (" + alt + ")",
      };
      if (!r.web && s.words !== null) { want.words = "Open the picture"; want.aria = "Open the picture"; want.web = false; }   // a workspace path's local control, where one stands
      if (r.place) {
        // the placement rows: the control's words are what the row holds, the one surface a browser leaves carrying the address there
        // (file-figure-open-browser.test.ts asserts the title's withholding inside a fold's summary and a link holding the picture
        // alone). This stand-in has no firstElementChild, so figureFoldOf finds no fold, and its getAttributeNS reads a plain href as
        // the XLink one, so mdBlock's fold takes every anchor's href off and the link is dead here: the title may stand, and when it
        // does it must be the withheld line; the placement itself is read back so the row is what it names
        const img = byAlt.get(alt)!, host = img.parentNode as El;
        assert.equal(r.place === "fold" ? host.tagName : host.tagName + ":" + host.children.length, r.place === "fold" ? "SUMMARY" : "A:1", b + ": " + r.name + ": the picture stands where the row says");
        if (s.title === WITHHELD_TITLE) want.title = WITHHELD_TITLE;
      }
      for (const k2 of ["title", "words", "aria", "web", "label"] as const) if (s[k2] !== want[k2]) fails.push(b + " " + alt + " (" + r.name + "): the " + k2 + " is " + JSON.stringify(s[k2]) + ", not " + JSON.stringify(want[k2]));
      for (const k2 of ["title", "words", "aria", "label"] as const) for (const x of r.planted) if ((s[k2] || "").includes(x)) fails.push(b + " " + alt + " (" + r.name + "): the " + k2 + " prints " + JSON.stringify(x));
    });
    ctl.forEach(([r, label, title, words], k) => {
      const alt = "k" + k, s = surfacesOf(byAlt.get(alt)!);
      t.diagnostic(b + " " + alt + " " + JSON.stringify(r.name) + " printed " + JSON.stringify(s));
      const want = { title, words, aria: words, web: words === null ? null : r.web, label: fv.FIGURE_FAILED + " " + label + " (" + alt + ")" };
      for (const k2 of ["title", "words", "aria", "web", "label"] as const) if (s[k2] !== want[k2]) fails.push(b + " " + alt + " (" + r.name + "): the " + k2 + " is " + JSON.stringify(s[k2]) + ", not " + JSON.stringify(want[k2]));
    });
    o.fv.closeFileView();
    forgetLoadedHosts();
  }
  // a URL document (labels alone: the URL view arms the labels and no control or title), whose figures resolveFigureRefs resolves
  // against the document before any reader, so the two-backslash form reaches the label as a web address, and a relative a@2x.png
  // too: the rule's cost there
  const NOTE = "https://notes-api.test/notes/note.md";
  (doc as any).baseURI = BASES.https;
  const docRows: Array<[string, string, string, string[]]> = [
    ["two leading backslashes on a URL document", BS + BS + NUM + "/" + PW + "@" + H + "/x.png", WITHHELD, [PW, NUM]],
    ["the cost: a relative a@2x.png on a URL document", "a@2x.png", WITHHELD, ["a@2x", "/notes/"]],
    ["a control: a relative figs/p.png on a URL document shows the document's origin", "figs/p.png", "https://notes-api.test", ["/notes/", "p.png"]],
  ];
  urls[NOTE] = "# Note\n\n" + docRows.map(([, src], i) => '<img src="' + src + '" alt="u' + i + '">').join("\n\n") + "\n";
  for (const [, src] of docRows) { const h = remoteHost(new URL(src, NOTE).href, BASES.https); if (h && h !== "notes-api.test") loadGatedHost(h, doc as unknown as ParentNode); }
  fv.openUrlView(NOTE);
  t.after(() => { fv.closeFileView(); doc.activeElement = null; delete urls[NOTE]; delete (doc as any).baseURI; forgetLoadedHosts(); });
  await settle();
  const md = doc.getElementById("romp-fileview")!.querySelector(".fileview-md")!;
  const uimgs = md.querySelectorAll("img");
  assert.deepEqual(uimgs.map((i) => i.getAttribute("alt")), docRows.map((_, i) => "u" + i), "the URL document's figures painted");
  assert.ok(uimgs.every((i) => i.closest('[data-act="fv-load"]') === null), "none gated on the URL document");
  assert.equal(uimgs[0].getAttribute("src"), new URL(docRows[0][1], NOTE).href, "resolveFigureRefs resolved the two-backslash form to a web address before any reader (read back)");
  for (const i of uimgs) i.dispatchEvent(new Ev("error"));
  docRows.forEach(([name, , want, planted], k) => {
    const s = surfacesOf(uimgs[k]);
    t.diagnostic("url u" + k + " " + JSON.stringify(name) + " printed " + JSON.stringify(s));
    const wantLabel = fv.FIGURE_FAILED + " " + want + " (u" + k + ")";
    if (s.label !== wantLabel) fails.push("url u" + k + " (" + name + "): the label is " + JSON.stringify(s.label) + ", not " + JSON.stringify(wantLabel));
    if (s.title !== null || s.words !== null) fails.push("url u" + k + " (" + name + "): a URL document's figure wears no title line and no control: " + JSON.stringify(s));
    for (const x of planted) if ((s.label || "").includes(x)) fails.push("url u" + k + " (" + name + "): the label prints " + JSON.stringify(x));
  });
  assert.deepEqual(fails, [], "every row shows the withheld address and no part of itself on each surface it has, the cost rows too, and the controls print as before (a property pin over the paint; each surface's print is in this case's diagnostic lines)");
});

// ── a credential in the path (the file review's round 15, extra9-2, on the coordinator's answer): the picture's title and the failed
// label show the origin alone, so a path parameter carrying a session or an opaque capability segment never prints; the control's
// words were host-only already. Each planted value is assembled at run time.
test("a picture from the web whose path carries a ;jsessionid= parameter, and one whose path carries an opaque token segment, painted with the host loaded and failed through the real error listener: the picture's title and the failed label show the origin alone, with no planted value, and the control's words name the host as before (a property pin over the paint, red at the head the round read by the planted value in both texts; the control's words are the control, green at both heads)", async (t) => {
  const fv = await mod();
  const sess = "S" + "ESS" + String(41 * 41) + "abcdef", seg = "k" + "ey" + String(97 * 89) + "ZyXw";
  const srcs = ["https://example.test/img/a.png;jsessionid=" + sess, "https://example.test/s/" + seg + "/a.png"];
  assert.deepEqual(srcs.map((s) => new URL(s).pathname.includes(s === srcs[0] ? sess : seg)), [true, true], "each planted value is in the path the parser reads (read back)");
  loadGatedHost("example.test", doc as unknown as ParentNode);
  t.after(() => { forgetLoadedHosts(); });
  const o = await open(REPORT, "# R\n\n" + srcs.map((s, i) => '<img src="' + s + '" alt="b' + i + '">').join("\n\n") + "\n", t);
  const imgs = o.body.querySelector(".fileview-md")!.querySelectorAll("img");
  assert.deepEqual(imgs.map((i) => i.getAttribute("alt")), ["b0", "b1"], "the two pictures painted, none gated");
  for (const i of imgs) i.dispatchEvent(new Ev("error"));
  const read = imgs.map((i) => { const c = i.nextSibling instanceof El && i.nextSibling.hasAttribute("data-fv-figopen") ? i.nextSibling : null; const l = (c || i).nextSibling; return { title: i.getAttribute("title"), words: c ? c.title : null, label: l instanceof El && l.hasAttribute("data-fv-figerr") ? l.textContent : null }; });
  assert.deepEqual(read.map((r) => r.title), ["Opens in a new tab: https://example.test", "Opens in a new tab: https://example.test"], "the picture's title: the origin alone (a property pin over the title attribute)");
  assert.deepEqual(read.map((r) => r.label), [fv.FIGURE_FAILED + " https://example.test (b0)", fv.FIGURE_FAILED + " https://example.test (b1)"], "the failed label: the origin alone (a property pin over the label's text)");
  for (const r of read) for (const x of [sess, seg, "jsessionid", ";", "/s/", "a.png"]) for (const v of [r.title, r.label]) assert.ok(!(v || "").includes(x), "no planted value and no path (a property pin): " + JSON.stringify(x) + " in " + JSON.stringify(v));
  assert.deepEqual(read.map((r) => r.words), ["Open the picture in a new tab at example.test", "Open the picture in a new tab at example.test"], "the control's words name the host alone, as before (a control, green at both heads by design)");
});

// ── the one rule, called directly: the rows no painted table can hold (the file review's round 15, correctness-1). The sanitizer's
// default list removes a file: source and an upper-case DATA: source before any reader (DOMPurify's data: test is case-sensitive),
// so these are calls on the label builder and on the rule itself, beside an s3: and a blob: source in upper case, which a rule
// that judged http and https alone would pass.
test("the one rule called directly (figureSourceCredentialed, through the label builder shownSource first): a file: source written without slashes and an upper-case DATA: source, which the sanitizer removes before any painted reader, and an upper-case S3: and BLOB: source, each holding a sign-in, are withheld on no base and on an https base, and the rule answers true for each and false for the controls (a property pin over the returned strings, red at the head the round read, where the label printed each address, the file: one as file:///user:pw16@... on both bases)", async () => {
  const fv = await mod();
  const US = "u" + "ser", PW = "p" + "w" + String(4 * 4), H = "example.test";
  const srcs = ["file:" + US + ":" + PW + "@" + H + "/x.png", "DATA://" + US + ":" + String(2000 + 24) + "/" + PW + "@" + H + "/x.png", "S3:" + US + ":" + PW + "@" + H + "/a.png", "BLOB:https://" + US + ":" + PW + "@" + H + "/x.png"];
  const out = srcs.map((s) => [fv.shownSource(s, undefined), fv.shownSource(s, "https://notes-api.test/")]);
  assert.deepEqual(out, srcs.map(() => [WITHHELD, WITHHELD]), "each withheld by the label builder on no base and on an https base (a property pin over the returned strings)");
  assert.deepEqual(srcs.map((s) => (fv as any).figureSourceCredentialed(s)), [true, true, true, true], "and the rule answers true for each (a property pin over the rule's answers)");
  assert.deepEqual(["a@2x.png", "/img/a@2x.png", "https://cdn.example/plot.png", "data:image/png;base64,iVBORw0KGgo"].map((s) => (fv as any).figureSourceCredentialed(s)), [false, false, false, false], "and false for the controls: a relative and a root-relative at sign with no colon before it, a plain address, a data: head with no at sign (controls, outside the rule)");
});

// ── the key gate over the stand-in's paint, the gate's one guard CI runs (the file review's round 15, tests-3 with extra5-2; the
// browser leg that presses the keys skips in CI): Enter or Space on a web picture's control is cancelled while the control is out
// of view (keyOnHiddenWebControl, registered on the viewer's body for keydown and, for Space, keyup; controlInView the region it
// reads). Each key is a synthetic event dispatched on the focused control, so it reaches the gate only through the body's two
// registrations, and the region answers through its inputs alone: the control's box, the window's layout and visual viewports,
// the body's scrollport and, for a framed viewer, the frame element's box, the parent's layout viewport, the parent's clipping
// ancestors and the top's visual viewport. The stand-in's layout gives a control no box and it has no getComputedStyle and no
// clientLeft or clientTop, and a NaN answers out everywhere, so the scene fills them: the viewer's body clips on both axes at its
// box (0 to 800 across, 100 to 300 down), its border 0, every other ancestor visible; the window is 1200 by 800 and its own parent.
// The stand-in document has no elementFromPoint either, which the one gate's hit test reads since the file review's round 16
// (extra5-1: a sign in view must be uncovered too, and a document without the read answers covered), so the scene gives it one:
// the control for a point inside the control's placed box, the viewer's body anywhere else, or `cover`'s element when a case
// lays one over the control.
type KeyGate = { ctl: El; img: El; body: El; place: (r: Rect) => void; cover: (e: El | null) => void; frame: (f: StandInFrame | null, foreign?: "null" | "throws") => void; gate: () => boolean[] };
/** A same-origin parent for the framed cells: the frame element's box and border in the parent's viewport, the parent's layout
 *  viewport, an optional wrapper around the frame element with its padding box and overflow (and, for the cells of the file
 *  review's round 16, regression-1, its computed display and a client size apart from its box), and the parent's visual
 *  viewport. */
type StandInFrame = { box: Rect; border?: [number, number]; inner: [number, number]; wrap?: { box: Rect; overflow: string; display?: string; client?: [number, number] }; vv?: [number, number, number, number] };
const boxAt = (left: number, top: number, width = 22, height = 22): Rect => ({ left, top, right: left + width, bottom: top + height, width, height });
const vvOf = (v: [number, number, number, number]) => ({ offsetLeft: v[0], offsetTop: v[1], width: v[2], height: v[3] });
/** The viewer open on one remote picture from a loaded host (`md`, a case's own document holding it, for the cells that wrap it in
 *  an author's element), its web control focused, and the region's inputs filled for the case and restored after it. `place` gives the control its box; `frame` hosts the window in a same-origin parent (a StandInFrame), in a
 *  parent of another origin (`foreign`: its frameElement reads null, or its read throws, the parent itself throwing on any read),
 *  or in none (null: the window its own parent); `cover` lays an element over the control for the document's elementFromPoint (null
 *  takes it off); `gate` dispatches keydown Enter, keydown Space and keyup Space on the control and returns whether each was
 *  prevented. */
async function keyGateScene(t: TestContext, md = '# R\n\n<img src="http://example.test/pic.svg" alt="big">\n'): Promise<KeyGate> {
  loadGatedHost("example.test", doc as unknown as ParentNode);
  t.after(() => { forgetLoadedHosts(); });
  const o = await open(REPORT, md, t);
  const img = o.body.querySelector(".fileview-md")!.querySelectorAll("img")[0];
  const ctl = img && img.nextSibling;
  assert.ok(ctl instanceof El && ctl.hasAttribute("data-fv-figopen") && ctl.classList.contains("fv-figopen-web"), "the web control after the remote picture (the scene's premise)");
  const saved = { gcs: (globalThis as any).getComputedStyle, wgcs: win.getComputedStyle, wdoc: win.document, wvv: win.visualViewport, parent: win.parent, efp: (doc as any).elementFromPoint };
  const cs = (e: any) => {   // the viewer's body clips (auto), every other element of the viewer's document is visible unless a case marks it (__clip); a parent's stand-in says its own; a display only where a case sets one (__display)
    if (e.__throws) throw new Error("read " + e.__throws);
    const o = e.__clip || (e instanceof El && e.classes.includes("fileview-body") ? "auto" : "visible");
    return { overflowX: o, overflowY: o, display: e.__display };
  };
  (globalThis as any).getComputedStyle = cs; win.getComputedStyle = cs; win.document = doc;   // the global too: the viewer before this round read it
  Object.defineProperty(o.body, "clientLeft", { value: 0, configurable: true });
  Object.defineProperty(o.body, "clientTop", { value: 0, configurable: true });
  const unframe = (): void => { win.parent = win; delete win.frameElement; delete win.visualViewport; };
  t.after(() => {
    unframe();
    for (const [k, v] of [["getComputedStyle", saved.wgcs], ["document", saved.wdoc], ["visualViewport", saved.wvv]] as const) if (v === undefined) delete win[k]; else win[k] = v;
    win.parent = saved.parent;
    if (saved.gcs === undefined) delete (globalThis as any).getComputedStyle; else (globalThis as any).getComputedStyle = saved.gcs;
    if (saved.efp === undefined) delete (doc as any).elementFromPoint; else (doc as any).elementFromPoint = saved.efp;
  });
  ctl.focus();
  Object.defineProperty(ctl, "previousElementSibling", { get: () => img, configurable: true });   // the stand-in has no previousElementSibling, which figureOfControl reads for the picture a control stands after (a click on the control)
  let placed: Rect | null = null, over: El | null = null;
  (doc as any).elementFromPoint = (x: number, y: number): El => (placed && x >= placed.left && x <= placed.right && y >= placed.top && y <= placed.bottom ? over || ctl : o.body);
  const place = (r: Rect): void => { placed = r; (ctl as any).getBoundingClientRect = () => r; };
  const cover = (e: El | null): void => { over = e; };
  const frame = (f: StandInFrame | null, foreign?: "null" | "throws"): void => {
    unframe();
    if (foreign) {
      win.parent = new Proxy({}, { get: () => { throw new Error("a parent of another origin: every read throws"); } });
      if (foreign === "null") win.frameElement = null;
      else Object.defineProperty(win, "frameElement", { get: () => { throw new Error("SecurityError: the frame element of a parent of another origin"); }, configurable: true });
      return;
    }
    if (!f) return;
    const root: any = { parentElement: null, __throws: "the parent's root (its overflow is the viewport's: passed over)" };
    const body: any = { parentElement: root, __throws: "the parent's body (its overflow is the viewport's: passed over)" };
    const wrap: any = f.wrap ? { parentElement: body, __clip: f.wrap.overflow, __display: f.wrap.display, getBoundingClientRect: () => f.wrap!.box, clientLeft: 0, clientTop: 0, clientWidth: f.wrap.client ? f.wrap.client[0] : f.wrap.box.width, clientHeight: f.wrap.client ? f.wrap.client[1] : f.wrap.box.height } : null;
    const fe: any = { parentElement: wrap || body, getBoundingClientRect: () => f.box, clientLeft: (f.border || [0, 0])[0], clientTop: (f.border || [0, 0])[1] };
    const parent: any = { innerWidth: f.inner[0], innerHeight: f.inner[1], getComputedStyle: cs, document: { body, documentElement: root }, visualViewport: f.vv ? vvOf(f.vv) : null };
    parent.parent = parent;
    win.parent = parent; win.frameElement = fe;
  };
  const gate = (): boolean[] => ([["keydown", "Enter"], ["keydown", " "], ["keyup", " "]] as const).map(([type, k]) => {
    const ev = new Ev(type, { key: k });
    ctl.dispatchEvent(ev);
    return ev.defaultPrevented;
  });
  assert.equal(doc.activeElement, ctl, "the keyboard on the web control (the scene's premise)");
  return { ctl, img, body: o.body, place, cover, frame, gate };
}
const OUT3 = [true, true, true], IN3 = [false, false, false];
const IN_BOX = boxAt(342, 206);   // inside the window (1200 by 800) and the body's scrollport (0 to 800, 100 to 300)
test("the key gate, a guard CI runs (the file review's round 15, tests-3): Enter's keydown, Space's keydown and Space's keyup dispatched on a focused web control inside the viewer's body are each cancelled while the control's box lies outside the window, or inside the window and below the body's scrollport, and none is cancelled while its box lies inside the window and the body's scrollport; each reaches the gate only through the body's keydown and keyup registrations (a property pin over each key's defaultPrevented, red with the keydown registration removed at the Enter and the Space keydown cells, red with the keyup registration removed at the Space release cell, red at the scrollport's cell under a region that reads the viewport alone or clips nothing down, and red at the in-view cells under a gate that always cancels; green at the head the round read, the gate there working, by design)", async (t) => {
  const g = await keyGateScene(t);
  g.frame(null);
  g.place(boxAt(342, 900));
  assert.deepEqual(g.gate(), OUT3, "the control below the window (900 against a height of 800): Enter's keydown, Space's keydown and Space's keyup each cancelled, [Enter keydown, Space keydown, Space keyup] (a property pin over defaultPrevented)");
  g.place(boxAt(342, 310));
  assert.deepEqual(g.gate(), OUT3, "the control inside the window and below the body's scrollport (310, the body's box ending at 300): each of the three cancelled (a property pin over defaultPrevented)");
  g.place(IN_BOX);
  assert.deepEqual(g.gate(), IN3, "the control inside the window and the body's scrollport: none of the three cancelled (a property pin over defaultPrevented)");
});
test("the key gate's region, the terms the file review's round 15 added (extra5-2), each in a cell of its own where it alone excludes a control every other read keeps: the window's visual viewport, a pinch zoom leaving 300 by 200 of the layout viewport on the screen; and, the viewer's window framed by a same-origin parent as the dashboard frames it, the parent's layout viewport across (the frame element at 700 in a parent 900 wide), the frame element's border (its top border of 10 moves the control past a parent 590 tall), a clipping ancestor of the frame element in the parent's document (a wrapper 300 wide with overflow hidden), and the top's visual viewport read through the parent (300 by 200) while the viewer's own visual viewport is its whole window; and at a parent of another origin, where the walk stops, the viewer's own visual viewport; each cancels the three keys, and the same frame with nothing excluding cancels none, the parent's body and root never read (a property pin over each key's defaultPrevented, red at the head the round read, which read no visual viewport and walked no frame, and each cell red with its own term deleted; the dashboard's cell red too under a walk that reads the viewer's own visual viewport)", async (t) => {
  const g = await keyGateScene(t);
  g.place(IN_BOX);
  const cells: Array<[string, () => void, boolean[]]> = [
    ["the window's visual viewport (0, 0, 300 by 200): the control at 342 past its right edge", () => { g.frame(null); win.visualViewport = vvOf([0, 0, 300, 200]); }, OUT3],
    ["the window's visual viewport at a scale of 1.2 (0, 0, 1000 by 667): the control inside (keep)", () => { g.frame(null); win.visualViewport = vvOf([0, 0, 1000, 667]); }, IN3],
    ["a same-origin parent with nothing excluding: the frame at 0, 0 in a parent 900 by 600 (keep)", () => { g.frame({ box: boxAt(0, 0, 900, 600), inner: [900, 600] }); }, IN3],
    ["the parent's layout viewport: the frame at 700 across in a parent 900 wide, the control at 1042", () => { g.frame({ box: boxAt(700, 0, 900, 600), inner: [900, 600] }); }, OUT3],
    ["the frame element's border: the frame at 380 down with a top border of 10 in a parent 590 tall, the control at 596", () => { g.frame({ box: boxAt(0, 380, 900, 600), border: [0, 10], inner: [900, 590] }); }, OUT3],
    ["a clipping ancestor of the frame element in the parent's document: a wrapper 300 wide with overflow hidden, the control at 342", () => { g.frame({ box: boxAt(0, 0, 900, 600), inner: [900, 600], wrap: { box: boxAt(0, 0, 300, 600), overflow: "hidden" } }); }, OUT3],
    ["the top's visual viewport through the parent (0, 0, 300 by 200), the viewer's own visual viewport its whole window (0, 0, 1200 by 800)", () => { g.frame({ box: boxAt(0, 0, 900, 600), inner: [900, 600], vv: [0, 0, 300, 200] }); win.visualViewport = vvOf([0, 0, 1200, 800]); }, OUT3],
    ["the top's visual viewport through the parent at a scale of 1.2 (0, 0, 750 by 500) (keep)", () => { g.frame({ box: boxAt(0, 0, 900, 600), inner: [900, 600], vv: [0, 0, 750, 500] }); win.visualViewport = vvOf([0, 0, 1200, 800]); }, IN3],
    ["a parent of another origin, its frame element null: the walk stops at the viewer's window, whose own visual viewport (0, 0, 300 by 200) still applies", () => { g.frame(null, "null"); win.visualViewport = vvOf([0, 0, 300, 200]); }, OUT3],
  ];
  const got = cells.map(([what, set]) => { set(); return [what, g.gate()] as const; });
  for (const [what, read] of got) t.diagnostic(what + ": " + JSON.stringify(read));
  assert.deepEqual(got.map(([what, read]) => [what, read]), cells.map(([what, , want]) => [what, want]), "each cell's three keys, [Enter keydown, Space keydown, Space keyup], cancelled where its term excludes the control and not where every term keeps it (a property pin over defaultPrevented)");
});
test("the key gate's region at a parent of another origin (the file review's round 15, extra5-2): the walk stops there with the reads made so far, which is not an out, so a control in view in the viewer's window keeps its keys whether the frame element reads null, as Chromium answers, or its read throws, and the parent itself, which throws on any read, is never read (a property pin over each key's defaultPrevented; green at the head the round read, which walked no frame, by design, and red under a walk that reads a null or a throwing frame element as out; the cell where the viewer's own visual viewport applies at the stop is the region case's)", async (t) => {
  const g = await keyGateScene(t);
  g.place(IN_BOX);
  g.frame(null, "null");
  assert.deepEqual(g.gate(), IN3, "a parent of another origin whose frame element reads null: none of the three keys cancelled (the stop is not an out; a property pin over defaultPrevented)");
  g.frame(null, "throws");
  assert.deepEqual(g.gate(), IN3, "a parent of another origin whose frame element's read throws: none of the three keys cancelled (a property pin over defaultPrevented)");
});

// ── the region's two corrections, guards CI runs (the file review's round 16, regression-1 with the coordinator's decision 1, and
// fresh-1; the browser leg that drives the dashboard's layout and the body zoom skips in CI): an ancestor on which overflow clips
// nothing, display: contents or display: inline, is passed over whatever its overflow reads, since either reads a client size of
// 0 by 0 and, read as a clip, put a control on the screen out of view (the dashboard's pane wrapper in its narrow layout; an
// author's inline span of a page class that sets overflow hidden); and an ancestor's border and client size, in its own CSS pixels,
// are scaled into the window's pixels, since under a body zoom the box is scaled and they were not. Each cell reads the three keys
// and a click dispatched on the control (openStub): under the one gate the click reads the same region, so a region that reads out
// refuses the click too.
test("the key gate's region passes over an ancestor of the frame element on which overflow clips nothing (the file review's round 16, regression-1 with the coordinator's decision 1): a wrapper with display: contents, a box and a client size of 0 by 0 and overflow hidden (the dashboard's pane wrapper in its narrow and touch layout), and one with display: inline and a client size of 0 by 0 around a box the frame's size, each leave the control in view, so none of the three keys is cancelled and a click on the control opens once; the same wrapper with display: block, a box that clips, still reads out (a property pin over each key's defaultPrevented and window.open's calls; the contents and inline cells red at the head the file review's round 16 read, where each wrapper's 0 by 0 put the control out of view and cancelled all three keys, and red under a region without the skip, where the click is refused too; the inline cell green at 2e9205301 by design, whose region walked no frame; the block cell's keys green there by design and its click red there by group A's open, since that head had no gate)", async (t) => {
  const g = await keyGateScene(t);
  g.place(IN_BOX);
  g.cover(null);
  const stub = openStub(t, g.ctl);
  const pane = (display: string, box: Rect, client: [number, number]): StandInFrame => ({ box: boxAt(0, 0, 900, 600), inner: [900, 600], wrap: { box, overflow: "hidden", display, client } });
  const cells: Array<[string, StandInFrame, [boolean[], number]]> = [
    ["a wrapper with display: contents, its box and client size 0 by 0, overflow hidden (the dashboard's pane wrapper under its narrow layout)", pane("contents", boxAt(0, 0, 0, 0), [0, 0]), [IN3, 1]],
    ["a wrapper with display: inline, its client size 0 by 0 around a box the frame's size, overflow hidden", pane("inline", boxAt(0, 0, 900, 600), [0, 0]), [IN3, 1]],
    ["the control: a wrapper with display: block, its box and client size 0 by 0, overflow hidden, which clips everything", pane("block", boxAt(0, 0, 0, 0), [0, 0]), [OUT3, 0]],
  ];
  const got = cells.map(([what, f]) => {
    g.frame(f);
    const keys = g.gate();
    const a = stub.read().opened;
    click(g.ctl);
    return [what, [keys, stub.read().opened - a]] as const;
  });
  for (const [what, read] of got) t.diagnostic(what + ": " + JSON.stringify(read));
  assert.deepEqual(got.map(([what, read]) => [what, read]), cells.map(([what, , want]) => [what, want]), "each wrapper's [three keys cancelled, the click's opens]: the wrappers on which overflow clips nothing keep the control in view, the block wrapper clips it (a property pin over defaultPrevented and window.open's calls)");
});
test("the key gate's region passes over the control's own ancestor on which overflow clips nothing (the file review's round 16, regression-1 with the coordinator's decision 1): the web picture inside an author's span of a page class that sets overflow hidden (sub-head-waits), the span read with display: inline and a client size of 0 by 0 around a box that holds the control, and with display: contents and a box of 0 by 0 (an author's span of a second page class that sets it), each leaves the control in view, so none of the three keys is cancelled and a click on the control opens once; the same span read as an inline-block, a block container that clips, reads out (a property pin over each key's defaultPrevented and window.open's calls; the inline and contents cells red at the head the file review's round 16 read and at 2e9205301, whose region read the span as a clip and cancelled all three keys, and red under a region without the skip, where the click is refused too; the inline-block cell's keys green at both by design and its click red there by group A's open)", async (t) => {
  const g = await keyGateScene(t, '# R\n\nGist words <span class="sub-head-waits"><img src="http://example.test/pic.svg" alt="big"></span> after.\n');
  g.frame(null);
  g.place(IN_BOX);
  g.cover(null);
  const span = g.ctl.parentElement as any;
  assert.ok(span && span.tagName === "SPAN" && span.classes.includes("sub-head-waits") && g.img.parentElement === span, "the picture and its control inside the author's span (the case's premise)");
  Object.defineProperty(span, "clientLeft", { value: 0, configurable: true });
  Object.defineProperty(span, "clientTop", { value: 0, configurable: true });
  const stub = openStub(t, g.ctl);
  const cells: Array<[string, string, Rect, [boolean[], number]]> = [
    ["display: inline, overflow hidden, its client size 0 by 0 around a box that holds the control", "inline", boxAt(300, 200, 120, 30), [IN3, 1]],
    ["display: contents, overflow hidden, its box and client size 0 by 0", "contents", boxAt(0, 0, 0, 0), [IN3, 1]],
    ["the control: display: inline-block, overflow hidden, its client size 0 by 0, a block container that clips", "inline-block", boxAt(300, 200, 120, 30), [OUT3, 0]],
  ];
  const got = cells.map(([what, display, box]) => {
    span.__display = display; span.__clip = "hidden"; span.getBoundingClientRect = () => box;
    assert.equal(span.clientWidth + span.clientHeight, 0, "the span's client size reads 0 by 0 (the case's premise)");
    const keys = g.gate();
    const a = stub.read().opened;
    click(g.ctl);
    return [what, [keys, stub.read().opened - a]] as const;
  });
  for (const [what, read] of got) t.diagnostic(what + ": " + JSON.stringify(read));
  assert.deepEqual(got.map(([what, read]) => [what, read]), cells.map(([what, , , want]) => [what, want]), "each reading of the span, [three keys cancelled, the click's opens]: inline and contents keep the control in view, inline-block clips it (a property pin over defaultPrevented and window.open's calls)");
});
test("the key gate's region in one coordinate space under a body zoom (the file review's round 16, fresh-1): the viewer's body zoomed, its box in the window's pixels and its client size in its own CSS pixels (800 by 200), read through its zoom (currentCSSZoom) and, where the browser gives none, through the ratio of its box to its layout size (offsetWidth, offsetHeight): at 1.25 a control in the body's bottom band and one at its right edge, each inside the body's box and outside what its unscaled client size spans, keep their keys and open on a click, and one below the body's box does not; at 0.8 a control past the body's bottom edge and one past its right edge, each inside what the unscaled client size spans and inside the window, are out of view, so their keys are cancelled and a click opens nothing, and one inside keeps them; and a same-origin frame element's top border of 40 CSS px at a zoom of 1.25 moves the control 50 px, past a parent 630 tall (a property pin over each key's defaultPrevented and window.open's calls; red at the head the file review's round 16 read, where the band and right-edge cells read out, the 0.8 past cells read in, the direction that opens a tab with the control hidden, and the border cell read in, and red under a region that reads the client size unscaled, where the band and right-edge clicks are refused and the 0.8 past clicks open; the out-of-view clicks red at that head by group A's open)", async (t) => {
  const g = await keyGateScene(t);
  g.frame(null);
  g.cover(null);
  const stub = openStub(t, g.ctl);
  const body = g.body as any;
  const zoomBody = (z: number, road: "zoom" | "ratio"): void => {
    const w = BODY_W * z, h = BODY_H * z;
    body.getBoundingClientRect = () => ({ left: 0, top: EDGE, right: w, bottom: EDGE + h, width: w, height: h });
    Object.defineProperty(body, "currentCSSZoom", { value: road === "zoom" ? z : undefined, configurable: true });
    Object.defineProperty(body, "offsetHeight", { value: road === "ratio" ? BODY_H : undefined, configurable: true });   // offsetWidth is the stand-in's own, the client width (800)
  };
  const at = (x: number, y: number, z: number): Rect => boxAt(x, y, 22 * z, 22 * z);
  const cells: Array<[string, () => void, [boolean[], number]]> = [];
  for (const road of ["zoom", "ratio"] as const) {
    const via = road === "zoom" ? " (currentCSSZoom)" : " (the box over offsetWidth and offsetHeight)";
    cells.push(
      ["1.25" + via + ": a control in the body's bottom band, 310 down, the body's box ending at 350 and its unscaled client height at 300", () => { zoomBody(1.25, road); g.place(at(342, 310, 1.25)); }, [IN3, 1]],
      ["1.25" + via + ": a control at the body's right edge, 960 across, the body's box ending at 1000 and its unscaled client width at 800", () => { zoomBody(1.25, road); g.place(at(960, 206, 1.25)); }, [IN3, 1]],
      ["1.25" + via + ": a control below the body's box, 360 down (keep)", () => { zoomBody(1.25, road); g.place(at(342, 360, 1.25)); }, [OUT3, 0]],
      ["0.8" + via + ": a control past the body's bottom edge, 265 down, the body's box ending at 260 and its unscaled client height at 300", () => { zoomBody(0.8, road); g.place(at(342, 265, 0.8)); }, [OUT3, 0]],
      ["0.8" + via + ": a control past the body's right edge, 650 across, the body's box ending at 640 and its unscaled client width at 800", () => { zoomBody(0.8, road); g.place(at(650, 150, 0.8)); }, [OUT3, 0]],
      ["0.8" + via + ": a control inside the body's box (keep)", () => { zoomBody(0.8, road); g.place(at(342, 150, 0.8)); }, [IN3, 1]],
    );
  }
  cells.push(["a same-origin frame element zoomed 1.25 with a top border of 40 CSS px, at 380 down in a parent 630 tall: the border 50 px in the parent's pixels, the control at 636", () => {
    zoomBody(1, "zoom"); g.place(IN_BOX);
    g.frame({ box: boxAt(0, 380, 900, 600), border: [0, 40], inner: [900, 630] });
    Object.defineProperty(win.frameElement, "currentCSSZoom", { value: 1.25, configurable: true });
  }, [OUT3, 0]]);
  const got = cells.map(([what, set]) => {
    set();
    const keys = g.gate();
    const a = stub.read().opened;
    click(g.ctl);
    return [what, [keys, stub.read().opened - a]] as const;
  });
  for (const [what, read] of got) t.diagnostic(what + ": " + JSON.stringify(read));
  assert.deepEqual(got.map(([what, read]) => [what, read]), cells.map(([what, , want]) => [what, want]), "each cell's [three keys cancelled, the click's opens] under the body zoom, read in the window's pixels (a property pin over defaultPrevented and window.open's calls)");
});

// ── the one gate on the click, the guards CI runs (the file review's round 16, extra5-1; the browser leg that drives the pointers
// skips in CI): a tap, a click or a Cmd/Ctrl-click on a picture from the web opens its tab only while the picture's sign (its web
// control here) is in view and uncovered, and otherwise opens nothing and reveals the sign (scrollIntoView, block and inline
// "nearest"). A click dispatched on the stand-in carries no pointer, so openFigure's gate reads it at the click (a script's road;
// a pointer's press is read at its pointerdown in the window's capture phase, which the browser leg drives). window.open is the
// open's stub (the page is http:, so openUrlTab takes the browser's tab), and the reveal is read off the stand-in's
// scrollIntoView record. Every value is synthetic.
/** The opens window.open received and the reveal's count on the control since the case began, read by `read`. */
function openStub(t: TestContext, ctl: El): { read: () => { opened: number; reveals: number; revealedWith: unknown } } {
  const saved = win.open, before = ctl.scrolled;
  const opened: string[] = [];
  win.open = (u: unknown) => { opened.push(String(u)); return null; };
  t.after(() => { if (saved === undefined) delete win.open; else win.open = saved; });
  return { read: () => ({ opened: opened.length, reveals: ctl.scrolled - before, revealedWith: ctl.scrolledWith }) };
}
const click = (target: El, detail = 0): void => { target.dispatchEvent(new Ev("click", { detail })); };
test("the one gate on the click, a guard CI runs (the file review's round 16, extra5-1): a click dispatched on a remote picture and one on its web control open nothing while the control's box lies outside the window, or inside the window and below the body's scrollport, or in view with another element over it at the hit test's points, and each such click reveals the control (scrollIntoView, block and inline nearest); in view and uncovered each opens once (a property pin over window.open's calls and the stand-in's scrollIntoView record, red at the head the file review's round 16 read, which opened a tab on every out-of-view and covered click and revealed nothing)", async (t) => {
  const g = await keyGateScene(t);
  g.frame(null);
  const stub = openStub(t, g.ctl);
  const cells: Array<[string, () => void, El, { opened: number; reveals: number }]> = [
    ["the picture, its control below the window (900 against a height of 800)", () => { g.place(boxAt(342, 900)); g.cover(null); }, g.img, { opened: 0, reveals: 1 }],
    ["the control itself, below the window", () => { g.place(boxAt(342, 900)); g.cover(null); }, g.ctl, { opened: 0, reveals: 1 }],
    ["the picture, its control inside the window and below the body's scrollport (310, the body's box ending at 300)", () => { g.place(boxAt(342, 310)); g.cover(null); }, g.img, { opened: 0, reveals: 1 }],
    ["the picture, its control in view with another element laid over it at every sample point", () => { g.place(IN_BOX); g.cover(new El("div")); }, g.img, { opened: 0, reveals: 1 }],
    ["the control itself, in view and covered", () => { g.place(IN_BOX); g.cover(new El("div")); }, g.ctl, { opened: 0, reveals: 1 }],
    ["the picture, its control in view and uncovered (keep)", () => { g.place(IN_BOX); g.cover(null); }, g.img, { opened: 1, reveals: 0 }],
    ["the control itself, in view and uncovered (keep)", () => { g.place(IN_BOX); g.cover(null); }, g.ctl, { opened: 1, reveals: 0 }],
  ];
  const got = cells.map(([what, set, target]) => {
    set();
    const a = stub.read();
    click(target);
    const b = stub.read();
    return [what, { opened: b.opened - a.opened, reveals: b.reveals - a.reveals }] as const;
  });
  for (const [what, read] of got) t.diagnostic(what + ": " + JSON.stringify(read));
  assert.deepEqual(got.map(([what, read]) => [what, read]), cells.map(([what, , , want]) => [what, want]), "each click's opens and reveals: none opened and one reveal where the control is out of view or covered, one open and no reveal where it is shown (a property pin over window.open's calls and the scrollIntoView record)");
  assert.deepEqual(stub.read().revealedWith, { block: "nearest", inline: "nearest" }, "the reveal scrolls the control into view the least way, in each scroll container (a property pin over scrollIntoView's argument)");
});
test("the one gate's later events of one gesture, a guard CI runs (the file review's round 16, extra5-1, the coordinator's decision 2: by the events' own fields, never by time): with the web control out of view, a refused first keydown of Enter reveals it, and a repeat of that held Enter (repeat true) is cancelled even once the control is in view; a refused Space keydown's repeat and its keyup are cancelled with the control in view too; a click of detail 1 refused out of view is followed, the control in view, by a click of detail 2 that opens nothing; and the next press opens: a new keydown (repeat false) is not cancelled, and a click of detail 1 opens once (a property pin over defaultPrevented and window.open's calls; the cancelled repeat and keyup and the detail-2 click are red under a gate that reads each event afresh, and the click cells red at the head the file review's round 16 read, which opened on every click)", async (t) => {
  const g = await keyGateScene(t);
  g.frame(null);
  const stub = openStub(t, g.ctl);
  const OUT = boxAt(342, 900);
  const keyEv = (type: string, k: string, repeat: boolean): boolean => { const ev = new Ev(type, { key: k }); (ev as any).repeat = repeat; g.ctl.dispatchEvent(ev); return ev.defaultPrevented; };
  const got: Record<string, unknown> = {};
  g.place(OUT);
  const r0 = stub.read().reveals;
  got.enterFirst = keyEv("keydown", "Enter", false);
  got.enterRevealed = stub.read().reveals - r0;
  g.place(IN_BOX);                                                       // where the reveal put it
  got.enterRepeat = keyEv("keydown", "Enter", true);
  got.enterUp = keyEv("keyup", "Enter", false);
  got.enterNext = keyEv("keydown", "Enter", false);
  keyEv("keyup", "Enter", false);
  g.place(OUT);
  got.spaceFirst = keyEv("keydown", " ", false);
  g.place(IN_BOX);
  got.spaceRepeat = keyEv("keydown", " ", true);
  got.spaceUp = keyEv("keyup", " ", false);
  got.spaceNext = [keyEv("keydown", " ", false), keyEv("keyup", " ", false)];
  g.place(OUT);
  const o0 = stub.read().opened;
  click(g.img, 1);
  got.clickFirst = stub.read().opened - o0;
  g.place(IN_BOX);
  click(g.img, 2);
  got.clickSecond = stub.read().opened - o0;
  click(g.img, 1);
  got.clickNext = stub.read().opened - o0;
  t.diagnostic("record " + JSON.stringify(got));
  assert.deepEqual(got, { enterFirst: true, enterRevealed: 1, enterRepeat: true, enterUp: false, enterNext: false, spaceFirst: true, spaceRepeat: true, spaceUp: true, spaceNext: [false, false], clickFirst: 0, clickSecond: 0, clickNext: 1 },
    "the refused press's later events take its verdict: the held Enter's repeat and the held Space's repeat and release cancelled, the double click's second click opening nothing, while the next press, a new keydown or a click of detail 1, is read afresh and opens (a property pin over defaultPrevented and window.open's calls)");
});
