// The gate-before-adoption order (plans/markdown-viewer.md, section "Fix: the gate before adoption (2026-09-20)"), executed
// under plain node. mdBlock (file-view.ts) runs the figure chain (resolveFigureRefs for a URL document, rewriteFigureSrcs for a
// file, gateRemoteFigures for both) over the body the sanitizer hands back, and adopts that body's nodes into its live-document
// box only afterwards; at the base 2d41e5c9b the adoption came first and WebKit and Firefox requested gated figures while the
// placeholders stood. The two browser legs (file-view-figures-gate-adopt-browser.test.ts, file-view-figures-gate-adopt-svg-
// browser.test.ts) see the bytes: real servers' request logs, in each of Playwright's engines. They skip where the engines are
// absent, and CI's `npm test` runs before its one `npx playwright install` (.github/workflows/ci.yml), so in CI they skip and
// this scene is the guard that runs there. What it pins, by execution over the REAL openFileView and openUrlView:
//   (a) at the adoption of the sanitized nodes into the live document, no element of the adopted subtree carries a fetching
//       attribute (an img's or a source's src or srcset, a video's src or poster, an audio's or a track's src, an svg image's
//       href or xlink:href, an svg paint attribute naming a url) whose host is outside the allowed set, or that names a
//       page-relative path (a figure of the file's folder before the rewrite to /file; a URL document's figure before its
//       resolution against the document); read over every move into the live document whose parent is the Rendered box or
//       stands under it, so a node a later pass brings in at any depth of the box is read at its own moment too, and then
//       over the box's end state once the render is done, whatever road a node took;
//   (b) across the whole render, no write of such an attribute lands on an element whose node document is the live one
//       (the writes the chain makes all land while the nodes are the sanitizer's), and a live write the scene itself makes is
//       recorded, so the zero is measured;
//   (c) every gated figure stands under a `span[data-act="fv-load"]` naming its host, its attribute moved to
//       `data-fv-gated-<attr>` with the value the chain left there (the authored URL for a remote figure, the /file route for a
//       folder figure inside a gated picture or video), and a click on the host restores exactly those attributes, live;
//   (d) a figure of the file's folder is requested through /file, never page-relative, and a URL document's relative figure
//       against the document's directory, never the page's.
// The stand-in is the seam suite's DOM (file-view-seam.test.ts, by way of file-view-figure-error.test.ts) with two documents
// instead of one: the sanitizer's stand-in mints its body in an INERT document and the viewer's `document` is the LIVE one,
// every node carries its document, an insertion moves the child's subtree into the parent's document (the browser's adoption)
// and the move into the live document is what the scene observes, with a snapshot of the subtree's fetching attributes taken
// at that moment. That is WebKit's trigger as the chain block's comment records it (the node document, not a place in the
// tree: `box` is detached until the caller's body.replaceChildren, so a hook on isConnected would see nothing). Every
// setAttribute of a fetching attribute is recorded with the element's document at write time. The selector engine grew `*`, the
// child combinator, `:first-child`, `:disabled`, `:scope` and `[*|href]` for the passes mdBlock runs after the adoption.
// What it cannot see: no fetch happens under node, so a leak here is an attribute the browser WOULD fetch through, judged by the
// scene's own oracle (a URL parse against the page, the host against the allowed set, a same-origin path against /file or the
// document's directory), never by figure-gate's remoteHost; the engines' own loading, DOMPurify's document and its inertness
// (the seam test's premise pin), and the bytes are the browser legs'. So is the fence pass's re-parse (code-block.ts wrapCodeLines,
// `code.innerHTML = wrapLinesHtml(code.innerHTML)`), which the round-2 move put before the chain: the stand-in's innerHTML is a
// plain field, not a parser, so the HTML parser's rename of an svg <image> split from its svg into an HTML <img> cannot happen
// here, and the fence scene of file-view-figures-gate-adopt-browser.test.ts is where that is seen; the seam test pins the pass's
// place and derives the post-adoption re-parse population from the code.
// Mutations, each applied to a scratch copy of the branch head and run with this scene alone (2026-09-20, at 8a599db74 with
// the scene as first built and again at the head after the review's third round, which added road (a)'s tree-wide read and
// the end-state pin; the scene compiled through esbuild's testBuild, the build's report holds the commands): (i) the base's
// order, the branch's file-view.ts diff applied in reverse (the adoption first, the chain over `box` after): 2 of 4 tests red,
// the file kind on road (a) with 16 leaks at the adoption (every remote source, both svg image spellings, the paint reference,
// and three page-relative paths, the folder figure's, the picture img's and the video's), the URL kind on road (a) with 4 (the
// relative img and the relative svg image page-relative, the two remote imgs); (ii) the two gateRemoteFigures calls alone
// moved after the adoption, over `box`: 2 of 4 red, the file kind on road (a) with 13 leaks (every remote source; the rewrite
// still ran on `clean`, so nothing page-relative), the URL kind with 2; (iii) one added line after the adoption,
// `box.querySelectorAll("[data-fv-gated-src]")` writing each element's gated source back into `src`: 2 of 4 red, road (a)
// green and road (b) red, five live writes in the file kind and two in the URL kind; (iv) one added line after the adoption
// minting an img in the sanitizer's document with a src on an unlisted host and appending it into the box's first paragraph:
// with road (a) read at the box's top level alone (the scene before the third round) the file kind stayed GREEN, since the
// adoption's parent was the paragraph and the src write landed while the img was the sanitizer's, so road (b) held it inert;
// the tree-wide read reds it, 2 of 4, one leak at that adoption in each kind. At the head, 4 of 4 green. So (a) and (b) each
// hold on their own, and the tree-wide read runs before the batch-count pin, so an order regression names the leak, not a
// count.
// Synthetic values only: the notes-api world, a placeholder sid, .test hosts.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import { inspect } from "node:util";
import { assertHiddenEvent, hideEdges, staysEnumerable } from "../test-dom-shim";
import type { FileViewActionCtx } from "./file-view";
import { setMdSanitizer } from "./md-sanitize";   // the sanitizer seam the node suites install a stand-in through (Slice 7 of plans/markdown-viewer.md)
import { FIGURE_SEL, PAINT_ATTRS, forgetLoadedHosts, loadGatedHost } from "./figure-gate";
import { XLINK_NS } from "./md-links";

// ── what the scene records ────────────────────────────────────────────────────────────────────────────
/** The attributes an element fetches through, by tag (the scene's own table; pinned equal to figure-gate's FIGURE_SEL and
 *  FETCH_ATTRS below, so the two walks name the same tags). `xlink:href` is the stand-in's key for the XLink attribute. */
const FETCHING: Record<string, string[]> = {
  IMG: ["src", "srcset"], SOURCE: ["src", "srcset"], VIDEO: ["src", "poster"], AUDIO: ["src"], TRACK: ["src"],
  IMAGE: ["href", "xlink:href"], FEIMAGE: ["href", "xlink:href"],
};
/** An inline svg's presentation attributes whose url() tokens fetch (figure-gate.ts PAINT_ATTRS; pinned equal below). */
const PAINT = ["fill", "stroke", "filter", "clip-path", "mask", "marker-start", "marker-mid", "marker-end"];
type Ref = { el: El; tag: string; attr: string; value: string; inSvg: boolean };
/** One clock for every record below: a write, a move into the live document and a gate move-aside each take the next tick, so
 *  the order leg compares them (the gate's last move-aside on the body against the first move of any node of the body). */
let seq = 0;
type Write = Ref & { live: boolean; seq: number };
/** `body`: the moved subtree holds a node the sanitizer's stand-in minted (a node of the sanitizer's body), so the move is
 *  the body, or part of it, entering the live document. */
type Adoption = { root: El | Txt; parent: El; snapshot: Ref[]; seq: number; body: boolean };
/** A move-aside the gate makes on an element: a `data-fv-gated-<attr>` write, with the element's document at that moment. */
type GateMove = { el: El; attr: string; live: boolean; seq: number };
/** Every write of a fetching attribute by anyone, in order, with the element's document at write time. */
const writes: Write[] = [];
/** Every move of a subtree INTO the live document, with the subtree's fetching attributes as they stood at that moment. */
const adoptions: Adoption[] = [];
/** Every move-aside the gate made (figure-gate.ts gate: the fetching attribute removed, its value under data-fv-gated-*). */
const gateMoves: GateMove[] = [];
const isFetching = (el: El, attr: string): boolean => (FETCHING[el.tagName] || []).includes(attr) || PAINT.includes(attr);
const inSvg = (el: El): boolean => el.tagName === "SVG" || el.closest("svg") !== null;
/** The fetching attributes under `root` (the root included) as they stand now. */
function fetchRefsOf(root: El): Ref[] {
  const out: Ref[] = [];
  for (const el of [root, ...root.querySelectorAll("*")]) {
    for (const attr of FETCHING[el.tagName] || []) { const v = el.attrs.get(attr); if (v) out.push({ el, tag: el.tagName, attr, value: v, inSvg: inSvg(el) }); }
    for (const attr of PAINT) { const v = el.attrs.get(attr); if (v) out.push({ el, tag: el.tagName, attr, value: v, inSvg: inSvg(el) }); }
  }
  return out;
}

// ── a DOM stand-in with two documents: ancestry, attributes, events with capture and bubbling, a selector engine ──
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
/** A document: the live one (`doc`, the viewer's `document`) or the sanitizer's inert one. A node's `_doc` names its document. */
type Doc = { name: "live" | "inert"; createElement(tag: string): El; createTextNode(s: string): Txt; baseURI: string | undefined };
class Txt {
  nodeType = 3;
  parentNode!: El | null;
  _doc!: Doc;
  _sanitized = false;   // minted by the sanitizer's stand-in: a node of the body mdBlock is handed
  constructor(public data: string, owner?: Doc) {
    Object.defineProperty(this, "parentNode", { value: null, writable: true, enumerable: false, configurable: true });
    this._doc = owner || doc;
    hideEdges(this);
  }
  get textContent(): string { return this.data; }
  get nodeValue(): string { return this.data; }
  get parentElement(): El | null { return this.parentNode; }
  get ownerDocument(): Doc { return this._doc; }
  get nextSibling(): El | Txt | null { const p = this.parentNode; if (!p) return null; const i = p.childNodes.indexOf(this); return i >= 0 ? p.childNodes[i + 1] || null : null; }
}
type Compound = { tag: string | null; id: string | null; classes: string[]; attrs: Array<[string, string | null, boolean]>; pseudos: string[]; comb: " " | ">" };
/** One compound `tag#id.class[attr="v"][*|attr]:pseudo`, or `*`. */
function compound(s: string, comb: " " | ">"): Compound {
  const m = /^(\*|[a-zA-Z][\w-]*)?(#[\w-]+)?((?:\.[\w-]+)*)((?:\[(?:\*\|)?[\w-]+(?:="[^"]*")?\])*)((?::[\w-]+)*)$/.exec(s);
  if (!m) throw new Error("stand-in: unsupported selector " + s);
  const classes = (m[3].match(/\.[\w-]+/g) || []).map((c) => c.slice(1));
  const attrs: Array<[string, string | null, boolean]> = [];
  for (const a of m[4].match(/\[[^\]]+\]/g) || []) { const am = /^\[(\*\|)?([\w-]+)(?:="([^"]*)")?\]$/.exec(a)!; attrs.push([am[2], am[3] ?? null, !!am[1]]); }
  const pseudos = (m[5].match(/:[\w-]+/g) || []).map((p) => p.slice(1));
  for (const p of pseudos) if (!["first-child", "disabled", "scope"].includes(p)) throw new Error("stand-in: unsupported pseudo-class :" + p);
  return { tag: m[1] ? m[1].toUpperCase() : null, id: m[2] ? m[2].slice(1) : null, classes, attrs, pseudos, comb };
}
/** Comma groups of chains; each link a compound joined to the one before it by a descendant (` `) or child (`>`) combinator. */
function parseSel(sel: string): Compound[][] {
  return sel.split(",").map((g) => g.trim()).filter(Boolean).map((g) => {
    const out: Compound[] = [];
    let comb: " " | ">" = " ";
    for (const tok of g.split(/\s*(>)\s*|\s+/)) {
      if (tok === ">") { comb = ">"; continue; }
      if (tok === undefined || tok === "") continue;
      out.push(compound(tok, comb)); comb = " ";
    }
    return out;
  });
}
/** A node's inline style: the properties as written, plus the setProperty the Outline's rows use for their depth variable. */
const styleOf = (): any => { const st: any = {}; st.setProperty = (k: string, v: string) => { st[k] = v; }; st.getPropertyValue = (k: string) => st[k] ?? ""; return st; };
class El {
  nodeType = 1;
  tagName: string;
  parentNode!: El | null;
  childNodes!: Array<El | Txt>;
  _doc!: Doc;
  _sanitized = false;   // minted by the sanitizer's stand-in: a node of the body mdBlock is handed
  attrs = new Map<string, string>();
  listeners: Reg[] = [];
  hidden = false; disabled = false; title = ""; type = ""; value = ""; placeholder = ""; spellcheck = true; wrap = "";
  alt = ""; download = ""; target = ""; rel = "";
  innerHTML = "";
  style: any = styleOf();
  onclick: ((ev: Ev) => void) | null = null;
  scrolled = 0;
  scrolledWith: unknown = null;
  focused = 0;
  constructor(tag: string, owner?: Doc) {
    this.tagName = tag.toUpperCase();
    Object.defineProperty(this, "parentNode", { value: null, writable: true, enumerable: false, configurable: true });
    Object.defineProperty(this, "childNodes", { value: [], writable: true, enumerable: false, configurable: true });
    this._doc = owner || doc;
    hideEdges(this);
  }
  get localName(): string { return this.tagName.toLowerCase(); }
  get id(): string { return this.attrs.get("id") || ""; }
  set id(v: string) { this.attrs.set("id", v); }
  get isConnected(): boolean { return doc.body.contains(this); }
  get ownerDocument(): Doc { return this._doc; }
  get parentElement(): El | null { return this.parentNode; }
  get children(): El[] { return this.childNodes.filter((c): c is El => c instanceof El); }
  get firstChild(): El | Txt | null { return this.childNodes[0] || null; }
  get firstElementChild(): El | null { return this.children[0] || null; }
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
  // the fetching properties read and write the attribute, as the browser's reflect (mdBlock writes attributes, never these;
  // the accessors are here so a write through the property would be recorded too)
  get src(): string { return this.attrs.get("src") || ""; }
  set src(v: string) { this.setAttribute("src", v); }
  get srcset(): string { return this.attrs.get("srcset") || ""; }
  set srcset(v: string) { this.setAttribute("srcset", v); }
  get poster(): string { return this.attrs.get("poster") || ""; }
  set poster(v: string) { this.setAttribute("poster", v); }
  get href(): string { return this.attrs.get("href") || ""; }
  set href(v: string) { this.setAttribute("href", v); }
  get attributes(): Array<{ name: string; value: string }> { return Array.from(this.attrs, ([name, value]) => ({ name, value })); }
  get textContent(): string { return this.childNodes.map((c) => c.textContent).join(""); }
  set textContent(v: string) { for (const c of this.childNodes) { this.dropFocusIn(c); c.parentNode = null; } this.childNodes.length = 0; if (v !== "") this.appendChild(new Txt(v, this._doc)); }
  private dropFocusIn(n: El | Txt): void { if (n instanceof El && doc.activeElement && n.contains(doc.activeElement)) doc.activeElement = doc.body; }
  private detach(n: El | Txt): void { const p = n.parentNode; if (p) { const i = p.childNodes.indexOf(n); if (i >= 0) p.childNodes.splice(i, 1); n.parentNode = null; } }
  /** The browser's adoption: a node inserted under a parent of another document moves, with its subtree, into the parent's
   *  document. A move INTO the live document is recorded with the subtree's fetching attributes as they stand at that moment. */
  private adopt(n: El | Txt): void {
    if (n._doc === this._doc) return;
    const into = this._doc;
    const snapshot = into === doc && n instanceof El ? fetchRefsOf(n) : [];
    let body = false;
    const walk = (x: El | Txt) => { x._doc = into; if (x._sanitized) body = true; if (x instanceof El) for (const c of x.childNodes) walk(c); };
    walk(n);
    if (into === doc) adoptions.push({ root: n, parent: this, snapshot, seq: seq++, body });
  }
  appendChild<T extends El | Txt>(n: T): T { this.detach(n); this.adopt(n); this.childNodes.push(n); n.parentNode = this; return n; }
  append(...ns: Array<El | Txt>): void { for (const n of ns) this.appendChild(n); }
  prepend(...ns: Array<El | Txt>): void { for (const n of ns.slice().reverse()) { this.detach(n); this.adopt(n); this.childNodes.unshift(n); n.parentNode = this; } }
  insertBefore<T extends El | Txt>(n: T, ref: El | Txt | null): T {
    if (!ref) return this.appendChild(n);
    this.detach(n);
    this.adopt(n);
    const i = this.childNodes.indexOf(ref);
    this.childNodes.splice(i < 0 ? this.childNodes.length : i, 0, n); n.parentNode = this; return n;
  }
  removeChild<T extends El | Txt>(n: T): T { this.dropFocusIn(n); this.detach(n); return n; }
  replaceChildren(...c: Array<El | Txt>): void { for (const x of this.childNodes) { this.dropFocusIn(x); x.parentNode = null; } this.childNodes.length = 0; for (const x of c) this.appendChild(x); }
  replaceWith(n: El | Txt): void { const p = this.parentNode; if (!p) return; p.insertBefore(n, this); this.remove(); }
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
  /** Every write of a fetching attribute is recorded with this element's document at the moment of the write. */
  setAttribute(k: string, v: string): void {
    this.attrs.set(k, v);
    if (isFetching(this, k)) writes.push({ el: this, tag: this.tagName, attr: k, value: v, inSvg: inSvg(this), live: this._doc === doc, seq: seq++ });
    else if (k.startsWith("data-fv-gated-")) gateMoves.push({ el: this, attr: k.slice("data-fv-gated-".length), live: this._doc === doc, seq: seq++ });
  }
  getAttribute(k: string): string | null { return this.attrs.has(k) ? (this.attrs.get(k) as string) : null; }
  hasAttribute(k: string): boolean { return this.attrs.has(k); }
  removeAttribute(k: string): void { this.attrs.delete(k); }
  // SVG 1.1's XLink attribute, keyed `xlink:href` in the attribute map (the `[*|href]` selector reads either spelling)
  private nsKey(ns: string | null, k: string): string { return ns === XLINK_NS ? "xlink:" + k : k; }
  setAttributeNS(ns: string | null, k: string, v: string): void { this.setAttribute(this.nsKey(ns, k), v); }
  getAttributeNS(ns: string | null, k: string): string | null { return ns === XLINK_NS || ns === null ? this.getAttribute(this.nsKey(ns, k)) : null; }
  removeAttributeNS(ns: string | null, k: string): void { this.removeAttribute(this.nsKey(ns, k)); }
  contains(n: El | Txt | null): boolean { for (let x: El | Txt | null = n; x; x = x.parentNode) if (x === this) return true; return false; }
  private fits(c: Compound, scope: El | null): boolean {
    if (c.tag && c.tag !== "*" && c.tag !== this.tagName) return false;
    if (c.id && c.id !== this.id) return false;
    if (!c.classes.every((k) => this.classes.includes(k))) return false;
    for (const [a, v, anyNs] of c.attrs) {
      if (anyNs) { if (!this.attrs.has(a) && ![...this.attrs.keys()].some((k) => k.endsWith(":" + a))) return false; continue; }
      if (!this.attrs.has(a) || (v !== null && this.attrs.get(a) !== v)) return false;
    }
    for (const p of c.pseudos) {
      if (p === "first-child") { const par = this.parentNode; if (!par || par.children[0] !== this) return false; }
      else if (p === "disabled") { if (!this.attrs.has("disabled") && !this.disabled) return false; }
      else if (p === "scope") { if (this !== scope) return false; }
    }
    return true;
  }
  /** Right to left: this fits the last compound, then each earlier one on the parent (`>`) or on some ancestor (` `). */
  private chain(links: Compound[], i: number, node: El, scope: El | null): boolean {
    if (!node.fits(links[i], scope)) return false;
    if (i === 0) return true;
    if (links[i].comb === ">") return node.parentNode ? this.chain(links, i - 1, node.parentNode, scope) : false;
    for (let a: El | null = node.parentNode; a; a = a.parentNode) if (this.chain(links, i - 1, a, scope)) return true;
    return false;
  }
  matches(sel: string, scope: El | null = null): boolean { return parseSel(sel).some((links) => this.chain(links, links.length - 1, this, scope)); }
  closest(sel: string): El | null { for (let x: El | null = this; x; x = x.parentNode) if (x.matches(sel)) return x; return null; }
  querySelectorAll(sel: string): El[] {
    const out: El[] = [];
    const visit = (n: El) => { for (const c of n.childNodes) if (c instanceof El) { if (c.matches(sel, this)) out.push(c); visit(c); } };
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

// the live document: the viewer's `document`, with the page's baseURI (the gate resolves every source against it)
const PAGE = "http://romp.test/files";
const doc = {
  name: "live" as const,
  baseURI: PAGE as string | undefined,
  listeners: [] as Reg[],
  body: null as unknown as El,
  head: null as unknown as El,
  hidden: false,
  activeElement: null as El | null,
  createElement: (tag: string) => new El(tag, doc),
  createTextNode: (s: string) => new Txt(s, doc),
  getElementById: (id: string): El | null => doc.body.querySelector("#" + id),
  querySelectorAll: (sel: string): El[] => doc.body.querySelectorAll(sel),
  /** The link passes' walk (path-links.ts textUnits): document-order text nodes, the elements too under SHOW_ELEMENT. */
  createTreeWalker: (root: El, what = 4) => { const nodes: Array<El | Txt> = []; const walk = (n: El) => { for (const c of n.childNodes) { if (c instanceof Txt) { if (what & 4) nodes.push(c); } else { if (what & 1) nodes.push(c); walk(c); } } }; walk(root); let i = 0; return { nextNode: () => (i < nodes.length ? nodes[i++] : null) }; },
  addEventListener(type: string, cb: Listener, o?: boolean | { capture?: boolean; once?: boolean }): void { doc.listeners.push({ type, cb, ...optsOf(o) }); },
  removeEventListener(type: string, cb: Listener, o?: boolean | { capture?: boolean }): void {
    const cap = optsOf(o).capture;
    doc.listeners = doc.listeners.filter((l) => !(l.type === type && l.cb === cb && l.capture === cap));
  },
  contains: (n: El | Txt | null) => doc.body.contains(n),
};
doc.body = new El("body", doc); doc.head = new El("head", doc);
/** The sanitizer's document: no browsing context, no baseURI; the body the stand-in hands mdBlock is minted here. */
const inert: Doc = { name: "inert", createElement: (tag: string) => new El(tag, inert), createTextNode: (s: string) => new Txt(s, inert), baseURI: undefined };
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
  if (ev.type === "error" || ev.type === "load") return !ev.defaultPrevented;
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
(globalThis as any).NodeFilter = { SHOW_ELEMENT: 1, SHOW_TEXT: 4 };   // the link walk's mask (the tree walker above)
const store = new Map<string, string>();
(globalThis as any).localStorage = {
  getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
  setItem: (k: string, v: string) => { store.set(k, String(v)); },
  removeItem: (k: string) => { store.delete(k); },
};
// the gear's list: one allowed host (settings.ts, key romp:settings); the page's own origin is never gated
const ALLOWED_HOST = "allowed.test";
store.set("romp:settings", JSON.stringify({ figureHosts: [ALLOWED_HOST] }));

// ── the sanitizer's stand-in: the body a case lays by hand, minted in the INERT document ─────────────────
/** Every dirty string the stand-in was handed: one per Rendered paint. */
const sanitized: string[] = [];
/** Set for a case: the body the stand-in answers with (a fresh one per paint), else an empty inert body. */
let nextBody: (() => El) | null = null;
const fakeSanitizer = { addHook: () => { /* the hooks are DOMPurify's; the stand-in has none */ }, sanitize: (dirty: string) => {
  sanitized.push(dirty);
  const body = nextBody ? nextBody() : inert.createElement("body");
  const mark = (n: El | Txt) => { n._sanitized = true; if (n instanceof El) for (const c of n.childNodes) mark(c); };
  mark(body);   // every node of the body the sanitizer hands back, so a move of any of them into the live document is read as the body's
  return body;
} };
setMdSanitizer(fakeSanitizer as unknown as Parameters<typeof setMdSanitizer>[0]);
/** An element of the inert document with the author's attributes written straight into the map (an author's markup is not a
 *  pass's write) and its children appended. */
const ie = (tag: string, attrs: Record<string, string> = {}, ...kids: Array<El | Txt>): El => {
  const e = inert.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) e.attrs.set(k, v);
  e.append(...kids);
  return e;
};
const it = (s: string): Txt => inert.createTextNode(s);

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
const MT = "1757145600000000001";
/** The src rewriteFigureSrcs writes for a figure of the report's folder (preview.ts fileUrl): the /file route, the path whole. */
const fileSrc = (rel: string): string => "/file?path=" + encodeURIComponent(ROOT + "/docs/" + rel) + "&sid=" + SID;
const REMOTE = "http://remote.test/fig.png";
const PROTO = "//remote.test/proto.png";
const SRCSET = "http://remote.test/a.png 1x, http://remote.test/b.png 2x";
const BOTH = "http://remote.test/both.png", BOTH_SET = "http://remote.test/both-2x.png 2x";
const WEBP = "http://remote.test/w.webp";
const SVG_HREF = "http://remote.test/d.png";
const SVG_XLINK = "http://other.test/x.png";
const POSTER = "http://remote.test/poster.png";
const AUDIO = "http://remote.test/a.mp3";
const INSIDE = "http://remote.test/inside.png";
const OK = "http://" + ALLOWED_HOST + "/ok.png";
const PAINT_URL = "http://remote.test/p.svg#g";
const PAINT_REF = "url(" + PAINT_URL + ")";
/** The note as the file holds it: the same figures as the body below, so the dirty string mdBlock hands the sanitizer carries
 *  every URL (marked passes an HTML block through). */
const NOTE = [
  "# Figures", "", "Before the figures.", "",
  '<img src="' + REMOTE + '" alt="absolute">', "",
  '<img src="' + PROTO + '" alt="protocol-relative">', "",
  '<img srcset="' + SRCSET + '" alt="srcset-only">', "",
  '<img src="' + BOTH + '" srcset="' + BOTH_SET + '" alt="src-and-srcset">', "",
  '<picture><source srcset="' + WEBP + '" type="image/webp"><img src="fig2.png" alt="picture"></picture>', "",
  '<svg width="10" height="10"><image href="' + SVG_HREF + '" width="10" height="10"/></svg>', "",
  '<svg width="10" height="10"><image xlink:href="' + SVG_XLINK + '" width="10" height="10"/></svg>', "",
  '<video src="clip.mp4" poster="' + POSTER + '" width="640" height="360"></video>', "",
  '<audio src="' + AUDIO + '"></audio>', "",
  '<details><summary>More</summary><img src="' + INSIDE + '" alt="inside-details"></details>', "",
  '<img src="fig.png" alt="folder">', "",
  '<img src="' + OK + '" alt="allowed">', "",
  '<svg width="10" height="10" fill="' + PAINT_REF + '"><rect width="10" height="10"/></svg>', "",
].join("\n");
const FIXTURE_URLS = [REMOTE, PROTO, SRCSET, BOTH, BOTH_SET, WEBP, SVG_HREF, SVG_XLINK, POSTER, AUDIO, INSIDE, OK, PAINT_REF, "fig.png", "fig2.png", "clip.mp4"];
/** The sanitized body for the note, as DOMPurify's svg+html profile would hand it back: a heading, a paragraph of prose and
 *  the thirteen figure blocks, top-level children of the body (the count the adoption assertion reads). */
function fileBody(): El {
  return ie("body", {},
    ie("h1", {}, it("Figures")),
    ie("p", {}, it("Before the figures.")),
    ie("p", {}, ie("img", { src: REMOTE, alt: "absolute" })),
    ie("p", {}, ie("img", { src: PROTO, alt: "protocol-relative" })),
    ie("p", {}, ie("img", { srcset: SRCSET, alt: "srcset-only" })),
    ie("p", {}, ie("img", { src: BOTH, srcset: BOTH_SET, alt: "src-and-srcset" })),
    ie("picture", {}, ie("source", { srcset: WEBP, type: "image/webp" }), ie("img", { src: "fig2.png", alt: "picture" })),
    ie("svg", { width: "10", height: "10" }, ie("image", { href: SVG_HREF, width: "10", height: "10" })),
    ie("svg", { width: "10", height: "10" }, ie("image", { "xlink:href": SVG_XLINK, width: "10", height: "10" })),
    ie("video", { src: "clip.mp4", poster: POSTER, width: "640", height: "360" }),
    ie("audio", { src: AUDIO }),
    ie("details", {}, ie("summary", {}, it("More")), ie("img", { src: INSIDE, alt: "inside-details" })),
    ie("p", {}, ie("img", { src: "fig.png", alt: "folder" })),
    ie("p", {}, ie("img", { src: OK, alt: "allowed" })),
    ie("svg", { width: "10", height: "10", fill: PAINT_REF }, ie("rect", { width: "10", height: "10" })),
  );
}
const FILE_ROOTS = 15;         // the body's top-level children above: the heading, the prose paragraph and the thirteen figure blocks
const FILE_PLACEHOLDERS = 11;  // the gated roots: eleven of the thirteen figure blocks (the folder img and the allowed img load live)
/** The URL kind: a document on its own host, at a directory of its own (openUrlView; the own host loads beside the gear's list). */
const NOTE_HOST = "notes-api.test";
const NOTE_DIR = "http://" + NOTE_HOST + "/notes/";
const NOTE_URL = NOTE_DIR + "note.md";
const URL_NOTE = ["# Note", "", '<img src="rel.png" alt="r">', "", '<img src="' + REMOTE + '" alt="f">', "", '<img src="' + PROTO + '" alt="p">', "",
  '<svg width="10" height="10"><image xlink:href="d.png" width="10" height="10"/></svg>', ""].join("\n");
function urlBody(): El {
  return ie("body", {},
    ie("h1", {}, it("Note")),
    ie("p", {}, ie("img", { src: "rel.png", alt: "r" })),
    ie("p", {}, ie("img", { src: REMOTE, alt: "f" })),
    ie("p", {}, ie("img", { src: PROTO, alt: "p" })),
    ie("svg", { width: "10", height: "10" }, ie("image", { "xlink:href": "d.png", width: "10", height: "10" })),
  );
}
const URL_ROOTS = 5;
const URL_PLACEHOLDERS = 2;

// ── the scene's oracle: what the browser would fetch through, judged without figure-gate's remoteHost ─────────
type Kind = { kind: "file" } | { kind: "url"; dir: string; own: string };
/** The URLs one attribute names: a srcset's candidates, a paint value's url() tokens, else the value. */
function urlsOf(attr: string, value: string): string[] {
  if (attr === "srcset") return value.split(",").map((c) => c.trim().split(/\s+/)[0]).filter(Boolean);
  if (PAINT.includes(attr)) return Array.from(value.matchAll(/url\(\s*["']?([^"')\s]+)["']?\s*\)/g), (m) => m[1]);
  return [value];
}
/** Why `url`, as the browser would resolve it against the page, is a leak, or null. An http(s) URL on a host outside the allowed
 *  set (the gear's list, the URL kind's own host, a host the person clicked) leaks; one on the page's own origin leaks when it is
 *  not the kernel's /file route (the file kind) or is a page-relative path where the document's directory was due (the URL kind);
 *  one on the URL document's own host leaks when it is outside the document's directory. data:, blob: and unparseable values
 *  fetch nothing from another host. */
function leakOf(url: string, kind: Kind, allowed: Set<string>): string | null {
  let u: URL;
  try { u = new URL(url, PAGE); } catch { return null; }
  if (u.protocol !== "http:" && u.protocol !== "https:") return null;
  if (u.origin === new URL(PAGE).origin) {
    if (kind.kind === "file") return u.pathname === "/file" || /^\/remote\/[^/]+\/file$/.test(u.pathname) ? null : "a page-relative path on the page's origin, " + u.href;
    return "a page-relative path where the document's directory was due, " + u.href;
  }
  if (kind.kind === "url" && u.hostname === kind.own) return u.href.startsWith(kind.dir) ? null : "outside the document's directory, " + u.href;
  return allowed.has(u.hostname) ? null : "an unlisted host, " + u.href;
}
const leaksIn = (refs: Ref[], kind: Kind, allowed: Set<string>): string[] => {
  const out: string[] = [];
  for (const r of refs) {
    if (PAINT.includes(r.attr) && !r.inSvg) continue;   // a paint attribute on an HTML element fetches nothing
    for (const u of urlsOf(r.attr, r.value)) { const why = leakOf(u, kind, allowed); if (why) out.push(r.tag.toLowerCase() + "[" + r.attr + "]: " + why); }
  }
  return out;
};
const FILE_KIND: Kind = { kind: "file" };
const URL_KIND: Kind = { kind: "url", dir: NOTE_DIR, own: NOTE_HOST };
const allowedNow = (...more: string[]): Set<string> => new Set([ALLOWED_HOST, ...more]);

// ── the probe: an action whose only job is to keep the ctx the viewer hands it ──────────────────────
let seam: FileViewActionCtx | null = null;
const posted: any[] = [];
let fvMod: typeof import("./file-view") | null = null;
async function mod(): Promise<typeof import("./file-view")> {
  if (fvMod) return fvMod;
  fvMod = await import("./file-view");
  fvMod.initFileView((m) => posted.push(m));
  fvMod.registerFileViewAction({ id: "seam-probe", mount(ctx) { seam = ctx; return null; } });
  fvMod.setFileViewIdentity((sid) => (sid === SID ? { name: "api", color: { bg: "#123456", fg: "#ffffff" } } : null));
  return fvMod;
}
const settle = async () => { for (let i = 0; i < 8; i++) await new Promise<void>((r) => setImmediate(r)); };
const reset = () => { writes.length = 0; adoptions.length = 0; gateMoves.length = 0; sanitized.length = 0; posted.length = 0; seam = null; forgetLoadedHosts(); store.delete("romp:fileviewFmt"); };
/** The Rendered box the viewer built, and the body around it: the render stood (a `.fileview-md` and no `.fileview-err` line). */
function rendered(): { body: El; md: El } {
  const wrap = doc.getElementById("romp-fileview")!;
  assert.ok(wrap, "the viewer is up");
  const body = wrap.querySelector(".fileview-body")!;
  const err = body.querySelector(".fileview-err");
  assert.equal(err, null, "the render stood: no RENDER_FELL line" + (err ? " (" + err.textContent + ")" : ""));
  const md = body.querySelector(".fileview-md")!;
  assert.ok(md, "the Rendered box is up");
  return { body, md };
}
/** The adoption batches whose parent is the Rendered box: the chain's nodes moving into the live document. */
const intoBox = (md: El): Adoption[] => adoptions.filter((a) => a.parent === md);
/** Every move into the live document whose parent stands under the box (or is it) once the render is done: the batch above
 *  and any node a later pass brings in from another document, into any depth of the box. */
const intoBoxTree = (md: El): Adoption[] => adoptions.filter((a) => a.parent === md || md.contains(a.parent));
/** The order leg (road (e)): over EVERY move into the live document, not the box-filtered ones, the first move of any node of
 *  the sanitizer's body comes after the gate's last move-aside on that body, every one of those move-asides landed while the
 *  element was the sanitizer's, and no fetching attribute of a body element was written between the two; the body's fetching
 *  attributes at that first move are therefore the ones the chain left. A pass that puts the body, or a node of it, in the
 *  page before the gate (a caller pass inside sanitizeMd, a registered post-pass, a chain call over the live box) is red
 *  here by the clock, whatever it is called and however it got there. */
function assertGateBeforeFirstMove(): { firstMove: Adoption; lastGate: GateMove } {
  const bodyMoves = adoptions.filter((a) => a.body);
  assert.ok(bodyMoves.length > 0, "road (e): nodes of the sanitizer's body entered the live document during the render");
  const firstMove = bodyMoves.reduce((a, b) => (b.seq < a.seq ? b : a));
  const onBody = gateMoves.filter((g) => g.el._sanitized);
  assert.ok(onBody.length > 0, "road (e): the gate moved fetching attributes of the body's elements aside (the fixture holds figures on unlisted hosts)");
  assert.deepEqual(onBody.filter((g) => g.live).map((g) => g.el.tagName.toLowerCase() + "[" + g.attr + "]"), [], "road (e): every move-aside the gate made on the body landed while the element's document was the sanitizer's");
  const lastGate = onBody.reduce((a, b) => (b.seq > a.seq ? b : a));
  assert.ok(lastGate.seq < firstMove.seq, "road (e), the order: the first move of any node of the sanitizer's body into the live document (tick " + firstMove.seq + ", a " + (firstMove.root instanceof El ? firstMove.root.tagName.toLowerCase() : "text node") + " into a live " + firstMove.parent.tagName.toLowerCase() + ") comes after the gate's last move-aside on that body (tick " + lastGate.seq + ", " + lastGate.el.tagName.toLowerCase() + "[" + lastGate.attr + "])");
  assert.deepEqual(writes.filter((w) => w.el._sanitized && w.seq > lastGate.seq && w.seq < firstMove.seq), [], "road (e): no fetching attribute of a body element was written between the gate's last move-aside and the first move, so the body's fetching attributes at that move are the chain's");
  return { firstMove, lastGate };
}
/** The placeholders under `md` (by the delegated action, as regateFigures finds them). */
const placeholders = (md: El): El[] => md.querySelectorAll('span[data-act="fv-load"]');
/** The placeholder around `el`, or null when it stands unwrapped. */
const gateAround = (el: El): El | null => el.closest('[data-act="fv-load"]');
/** The `data-fv-gated-*` pairs under `root` (the root included), as (element, attribute name without the prefix, value); the
 *  `fv-src` one excluded, since restore writes it back as `data-fv-src`, which fetches nothing. */
function gatedPairs(root: El): Array<[El, string, string]> {
  const out: Array<[El, string, string]> = [];
  for (const el of [root, ...root.querySelectorAll("*")]) for (const [k, v] of el.attrs) if (k.startsWith("data-fv-gated-") && k !== "data-fv-gated-fv-src") out.push([el, k.slice("data-fv-gated-".length), v]);
  return out;
}
const pairKey = (el: El, attr: string, value: string): string => el.tagName + "#" + (el as any)._nid + " " + attr + "=" + value;
/** The figure elements of the file body, found by their alt (an img) or their tag, after the render. */
function figures(md: El) {
  const byAlt = (alt: string): El => { const i = md.querySelectorAll('img[alt="' + alt + '"]'); assert.equal(i.length, 1, "one img with alt " + alt); return i[0]; };
  const images = md.querySelectorAll("image");
  const svgs = md.querySelectorAll("svg");
  return {
    absolute: byAlt("absolute"), proto: byAlt("protocol-relative"), srcsetOnly: byAlt("srcset-only"), both: byAlt("src-and-srcset"),
    picture: md.querySelector("picture")!, source: md.querySelector("source")!, pictureImg: byAlt("picture"),
    imageHref: images[0], imageXlink: images[1], video: md.querySelector("video")!, audio: md.querySelector("audio")!,
    inside: byAlt("inside-details"), folder: byAlt("folder"), allowed: byAlt("allowed"), paintSvg: svgs[2],
  };
}

test("the scene's tables are the product's: FIGURE_SEL names the tags FETCHING keys, PAINT_ATTRS is PAINT", () => {
  assert.equal(FIGURE_SEL, "img, source, video, audio, track, image, feImage", "figure-gate's tag list, so the scene's table and the product's walk name the same tags");
  assert.deepEqual(FIGURE_SEL.split(",").map((t) => t.trim().toUpperCase()).sort(), Object.keys(FETCHING).sort(), "one FETCHING entry per tag of FIGURE_SEL");
  assert.deepEqual([...PAINT_ATTRS], PAINT, "the paint attributes the gate judges");
  // the oracle's own checks: a leak it must see, and the values it must let through
  assert.equal(leakOf(REMOTE, FILE_KIND, allowedNow()), "an unlisted host, " + REMOTE);
  assert.equal(leakOf(PROTO, FILE_KIND, allowedNow()), "an unlisted host, http://remote.test/proto.png", "a protocol-relative source takes the page's scheme");
  assert.equal(leakOf("fig.png", FILE_KIND, allowedNow()), "a page-relative path on the page's origin, http://romp.test/fig.png", "a folder figure before the rewrite would be fetched against the page");
  assert.equal(leakOf(fileSrc("fig.png"), FILE_KIND, allowedNow()), null, "the /file route is the kernel's own");
  assert.equal(leakOf("/remote/gpu1/file?path=x", FILE_KIND, allowedNow()), null, "so is the federation relay");
  assert.equal(leakOf(OK, FILE_KIND, allowedNow()), null, "an allowed host loads");
  assert.equal(leakOf(REMOTE, FILE_KIND, allowedNow("remote.test")), null, "a host the person clicked loads");
  assert.equal(leakOf("data:image/png;base64,AAAA", FILE_KIND, allowedNow()), null, "data: fetches from no host");
  assert.equal(leakOf("rel.png", URL_KIND, allowedNow()), "a page-relative path where the document's directory was due, http://romp.test/rel.png");
  assert.equal(leakOf(NOTE_DIR + "rel.png", URL_KIND, allowedNow()), null, "the document's own directory");
  assert.equal(leakOf("http://" + NOTE_HOST + "/elsewhere.png", URL_KIND, allowedNow()), "outside the document's directory, http://" + NOTE_HOST + "/elsewhere.png");
  assert.deepEqual(urlsOf("srcset", SRCSET), ["http://remote.test/a.png", "http://remote.test/b.png"]);
  assert.deepEqual(urlsOf("fill", PAINT_REF), [PAINT_URL]);
});

test("the file kind: the chain runs before the adoption, so the nodes that enter the live document carry no fetching attribute on an unlisted host and none page-relative; every write of one landed while the nodes were the sanitizer's; the gated figures stand as placeholders holding their sources in data-fv-gated-*; the folder figure is live through /file and the allowed host's figure as written; a click on a host restores exactly that host's attributes, live", async (t) => {
  const fv = await mod();
  reset();
  disk[REPORT] = { bytes: NOTE, type: "text/plain; charset=utf-8", mtimeNs: MT };
  nextBody = fileBody;
  t.after(() => { nextBody = null; fv.closeFileView(); doc.activeElement = null; });
  assert.equal(fv.openFileView(REPORT, SID), true, "the open happened");
  await settle();
  // A1: the render stood
  const { md } = rendered();
  const ctx = seam as FileViewActionCtx | null;
  assert.ok(ctx && ctx.mode() === "rendered", "the report opened Rendered");
  // A2: one paint, and the note the sanitizer was handed carries every figure's source (marked rendered the note; the body the
  // stand-in laid and the note agree on the sources)
  assert.equal(sanitized.length, 1, "one Rendered paint, one sanitize");
  for (const u of FIXTURE_URLS) assert.ok(sanitized[0].includes(u), "the dirty string carries " + u);
  // A3, road (a): one batch of adoptions into the box, the body's children, and the snapshot at that moment shows no leak
  assert.deepEqual(leaksIn(intoBoxTree(md).flatMap((a) => a.snapshot), FILE_KIND, allowedNow()), [], "road (a): no node that entered the live document anywhere under the Rendered box, at any depth, by any pass, carried a fetching attribute on an unlisted host or page-relative at that moment");
  // road (e): the body stayed the sanitizer's until the gate had run over it, by the clock, over every move into the live document
  const order = assertGateBeforeFirstMove();
  assert.equal(order.firstMove.parent, md, "road (e): and that first move is the adoption into the Rendered box itself (no earlier move of a body node anywhere in the live document)");
  const batch = intoBox(md);
  assert.equal(batch.length, FILE_ROOTS, "every top-level child of the sanitizer's body entered the live document, once each, into the Rendered box, adopted as it is (no wrapper around the batch, no re-parse)");
  const snapshot = batch.flatMap((a) => a.snapshot);
  assert.deepEqual(leaksIn(snapshot, FILE_KIND, allowedNow()), [], "road (a): no fetching attribute on an unlisted host, none page-relative, on any node at the moment it entered the live document");
  assert.deepEqual(snapshot.map((r) => r.tag.toLowerCase() + "[" + r.attr + "]=" + r.value).sort(), ["img[src]=" + OK, "img[src]=" + fileSrc("fig.png")].sort(),
    "the snapshot saw exactly the two sources the chain left live: the folder figure's /file src and the allowed host's src (every other fetching attribute was moved aside before the adoption)");
  assert.deepEqual(batch.map((a) => a.root), md.childNodes, "the adopted roots are the box's children now, in order");
  // A5, road (b): writes happened (the rewrite, the fold), all of them while the element's document was the sanitizer's
  const before = writes.length;
  assert.ok(before > 0, "the chain wrote fetching attributes: " + before);
  assert.ok(writes.some((w) => w.attr === "src" && w.value === fileSrc("fig.png") && !w.live), "the rewrite's /file write on the folder figure, inert");
  assert.ok(writes.some((w) => w.attr === "href" && w.value === SVG_XLINK && !w.live), "the fold of xlink:href into href on the svg image, inert (the write WebKit fetched on at the base)");
  const live = writes.filter((w) => w.live);
  assert.deepEqual(leaksIn(live, FILE_KIND, allowedNow()), [], "road (b): no write of a fetching attribute on an unlisted host, or page-relative, landed on a live-document element");
  assert.equal(live.length, 0, "no write of a fetching attribute landed on a live-document element at all during this render (the passes after the adoption write styles, classes, anchors' attributes and fences)");
  // the end state: whatever road a node took, nothing under the box carries a leaking fetching attribute once the render is done
  assert.deepEqual(leaksIn(fetchRefsOf(md), FILE_KIND, allowedNow()), [], "the rendered box holds no fetching attribute on an unlisted host and none page-relative");
  // A4, the shape: eleven placeholders, each naming its host, the sources moved aside with the value the chain left
  const f = figures(md);
  assert.equal(placeholders(md).length, FILE_PLACEHOLDERS, "eleven gated roots");
  const gated = (el: El, host: string, attr: string, value: string, msg: string) => {
    const g = gateAround(el);
    assert.ok(g, msg + ": under a placeholder");
    assert.equal(g!.getAttribute("data-fv-hosts"), host, msg + ": the placeholder names the host");
    assert.equal(el.getAttribute(attr), null, msg + ": the " + attr + " is gone from the element");
    assert.equal(el.getAttribute("data-fv-gated-" + attr), value, msg + ": data-fv-gated-" + attr + " holds the source");
  };
  gated(f.absolute, "remote.test", "src", REMOTE, "the absolute remote img");
  gated(f.proto, "remote.test", "src", PROTO, "the protocol-relative img (the file kind leaves a //host source as written; the gate resolves it against the page)");
  gated(f.srcsetOnly, "remote.test", "srcset", SRCSET, "the srcset-only img");
  gated(f.both, "remote.test", "src", BOTH, "the img with src and srcset, its src");
  gated(f.both, "remote.test", "srcset", BOTH_SET, "the img with src and srcset, its srcset");
  gated(f.source, "remote.test", "srcset", WEBP, "the picture's source");
  gated(f.pictureImg, "remote.test", "src", fileSrc("fig2.png"), "the picture's img: rewritten to /file, then moved aside with the picture");
  assert.equal(f.pictureImg.getAttribute("data-fv-gated-fv-src"), "fig2.png", "the picture img's authored spelling, moved aside with it");
  assert.equal(gateAround(f.source), gateAround(f.pictureImg), "one placeholder around the picture");
  gated(f.imageHref, "remote.test", "href", SVG_HREF, "the svg image spelt href");
  gated(f.imageXlink, "other.test", "href", SVG_XLINK, "the svg image spelt xlink:href: folded into href by rewriteFigureSrcs, then moved aside under that name");
  assert.equal(f.imageXlink.getAttribute("xlink:href"), null, "the xlink spelling is gone");
  gated(f.video, "remote.test", "poster", POSTER, "the video's poster");
  gated(f.video, "remote.test", "src", fileSrc("clip.mp4"), "the video's src: rewritten to /file BEFORE the gate moved it aside");
  gated(f.audio, "remote.test", "src", AUDIO, "the audio");
  gated(f.inside, "remote.test", "src", INSIDE, "the img inside details");
  gated(f.paintSvg, "remote.test", "fill", PAINT_REF, "the svg's paint reference");
  // A4, road (d): the folder figure through /file, never page-relative; the allowed host's figure as written; neither under a placeholder
  assert.equal(gateAround(f.folder), null, "the folder figure stands unwrapped");
  assert.equal(f.folder.getAttribute("src"), fileSrc("fig.png"), "the folder figure's src is the /file route");
  assert.equal(f.folder.getAttribute("data-fv-src"), "fig.png", "its authored spelling kept");
  assert.equal(gateAround(f.allowed), null, "the allowed host's figure stands unwrapped");
  assert.equal(f.allowed.getAttribute("src"), OK, "its src as written");
  // A6, the control: a live write is what the hook records, so the zero above is measured
  f.allowed.setAttribute("src", REMOTE);
  assert.equal(writes.length, before + 1, "the scene's own write was recorded");
  assert.equal(writes[before].live, true, "and as live: the element's document is the viewer's");
  assert.deepEqual(leaksIn([writes[before]], FILE_KIND, allowedNow()), ["img[src]: an unlisted host, " + REMOTE], "and the oracle calls it");
  f.allowed.setAttribute("src", OK);
  writes.length = before;
  // A7, the click: the host joins the loaded set and its placeholders are restored, the moved attributes written back live
  const remoteRoots = placeholders(md).filter((g) => g.getAttribute("data-fv-hosts") === "remote.test");
  assert.equal(remoteRoots.length, FILE_PLACEHOLDERS - 1, "every placeholder but the svg on other.test waits on remote.test");
  const expected = new Set(remoteRoots.flatMap((g) => gatedPairs(g)).map(([el, attr, value]) => pairKey(el, attr, value)));
  loadGatedHost("remote.test", doc as unknown as ParentNode);
  const restored = writes.slice(before);
  assert.deepEqual(new Set(restored.map((w) => pairKey(w.el, w.attr, w.value))), expected, "the restore wrote back exactly the moved attributes of that host's figures, and nothing else");
  assert.ok(restored.every((w) => w.live), "every restore write landed live (the figures are in the page now)");
  assert.deepEqual(leaksIn(restored, FILE_KIND, allowedNow("remote.test")), [], "and every one is on the host the person loaded, or the kernel's own route");
  assert.equal(placeholders(md).length, 1, "one placeholder still stands");
  assert.equal(placeholders(md)[0].getAttribute("data-fv-hosts"), "other.test", "the svg image on the other host");
  assert.equal(f.imageXlink.getAttribute("href"), null, "its href is still aside");
  assert.equal(f.absolute.getAttribute("src"), REMOTE, "the absolute img has its src back");
  assert.equal(f.video.getAttribute("src"), fileSrc("clip.mp4"), "the video has its /file src back");
  assert.equal(f.video.getAttribute("poster"), POSTER, "and its poster");
  assert.equal(f.pictureImg.getAttribute("data-fv-src"), "fig2.png", "the picture img's authored spelling is back under data-fv-src");
});

test("the URL kind: resolveFigureRefs and the gate run on the sanitizer's body, so the nodes that enter the live document carry the document's directory for a relative figure, the document's own host and the gear's list live, and every other host moved aside; no live write of a fetching attribute", async (t) => {
  const fv = await mod();
  reset();
  urls[NOTE_URL] = URL_NOTE;
  nextBody = urlBody;
  t.after(() => { nextBody = null; fv.closeFileView(); doc.activeElement = null; });
  fv.openUrlView(NOTE_URL);
  await settle();
  const { md } = rendered();
  assert.equal(sanitized.length, 1, "one paint");
  for (const u of ["rel.png", REMOTE, PROTO, "d.png"]) assert.ok(sanitized[0].includes(u), "the dirty string carries " + u);
  assert.deepEqual(leaksIn(intoBoxTree(md).flatMap((a) => a.snapshot), URL_KIND, allowedNow()), [], "road (a): no node that entered the live document anywhere under the Rendered box carried a leaking fetching attribute at that moment");
  assert.equal(assertGateBeforeFirstMove().firstMove.parent, md, "road (e): the first move of a body node into the live document is the adoption into the Rendered box, after the gate's last move-aside");
  const batch = intoBox(md);
  assert.equal(batch.length, URL_ROOTS, "every top-level child of the sanitizer's body entered the live document, once each, adopted as it is (no wrapper around the batch, no re-parse)");
  const snapshot = batch.flatMap((a) => a.snapshot);
  assert.ok(snapshot.length >= 2, "the snapshot saw the live sources (the relative img's, the svg image's): " + snapshot.length);
  assert.deepEqual(leaksIn(snapshot, URL_KIND, allowedNow()), [], "road (a) for a URL document: nothing page-relative, nothing outside the document's directory on its own host, no unlisted host");
  assert.deepEqual(batch.map((a) => a.root), md.childNodes, "in order, as the box's children");
  const live = writes.filter((w) => w.live);
  assert.ok(writes.some((w) => w.attr === "src" && w.value === NOTE_DIR + "rel.png" && !w.live), "the resolution's write on the relative img, inert");
  assert.deepEqual(leaksIn(live, URL_KIND, allowedNow()), [], "road (b): no live write of a fetching attribute on an unlisted host or page-relative");
  assert.equal(live.length, 0, "no live write of a fetching attribute at all");
  assert.deepEqual(leaksIn(fetchRefsOf(md), URL_KIND, allowedNow()), [], "the rendered box holds no leaking fetching attribute once the render is done");
  const imgs = md.querySelectorAll("img");
  assert.equal(imgs.length, 3);
  const [rel, far, proto] = imgs;
  assert.equal(rel.getAttribute("src"), NOTE_DIR + "rel.png", "road (d): the relative figure resolved against the document's directory, exactly, not the page's");
  assert.equal(gateAround(rel), null, "and it stands unwrapped: the document's own host loads");
  assert.equal(rel.getAttribute("data-fv-src"), null, "no data-fv-src for a URL document (no comments panel)");
  assert.equal(placeholders(md).length, URL_PLACEHOLDERS, "two placeholders");
  for (const [el, value, what] of [[far, REMOTE, "the absolute remote img"], [proto, "http://remote.test/proto.png", "the protocol-relative img, resolved to the document's scheme before the gate moved it aside"]] as Array<[El, string, string]>) {
    const g = gateAround(el);
    assert.ok(g, what + ": under a placeholder");
    assert.equal(g!.getAttribute("data-fv-hosts"), "remote.test", what + ": the host named");
    assert.equal(el.getAttribute("src"), null, what + ": src gone");
    assert.equal(el.getAttribute("data-fv-gated-src"), value, what + ": the source held aside");
  }
  const image = md.querySelector("image")!;
  assert.equal(image.getAttribute("href"), NOTE_DIR + "d.png", "the svg image's xlink:href folded into href, resolved against the document");
  assert.equal(image.getAttribute("xlink:href"), null);
  assert.equal(gateAround(image), null, "on the document's own host: not gated");
});

// ── the stand-in's projection (ui/test-dom-shim.ts): a node inspects as its primitives, never as the tree or its document ─────
test("a stand-in node enumerates its primitives alone, so a failing assertion's dump shows neither parentNode, childNodes nor the node's document", () => {
  const root = new El("p"); root.className = "row";
  const child = root.appendChild(inert.createElement("img")); root.appendChild(new Txt("beta"));
  assert.equal(child._doc, doc, "the child was adopted into the parent's document");
  for (const n of [root, child, root.childNodes[1]] as Array<El | Txt>) {
    for (const k of Object.keys(n)) assert.ok(staysEnumerable((n as any)[k]), k + " is enumerable and holds a " + typeof (n as any)[k]);
    const dump = inspect(n, { compact: false, customInspect: false, depth: 1000, maxArrayLength: Infinity, showHidden: false, showProxy: false, sorted: true, getters: true });
    assert.ok(!dump.includes("parentNode") && !dump.includes("childNodes") && !dump.includes("_doc"), "the dump holds no edge: " + dump);
  }
  assert.ok(child.parentNode === root && root.childNodes[0] === child && child.nextSibling === root.childNodes[1], "the tree is reachable as before, the next sibling included");
  assertHiddenEvent(new Ev("error"), root, child);
});
