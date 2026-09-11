// The recurring-passage tie-break on a coarse pointer (the review, 2026-09-11; plans/file-review.md, decision 51). A
// REGION comment whose embed line ties has its rectangle on the guessed figure and its card says how a region's copy is
// confirmed: a new region drawn on the figure meant, with a mouse. On a pointer that draws that card offers Re-place, and
// the words say what Re-place does instead (it redraws the rectangle on the figure shown and moves nothing), so the
// person does not take the button for the recourse. On a phone the same picture is in view but no overlay takes a drag
// (RegionLayer's active is the panel open AND a fine pointer), so the card offers Reply and Resolve alone: the words kept
// the sentence about Re-place all the same, the class the third round had closed for the editor (a Reveal the card
// lacked) and for Raw (a figure the view lacked). Now renderCard stamps the pointer half of the Re-place gate on the card
// its words read (Shown.draws, from the same drawsRegions() replaceOffered reads), and a pictured card with no pointer
// that draws ends with REGION_CONFIRM_TOUCH: the pictured view's words with the sentence about Re-place left out, still
// ending with what drawing takes, so the card does not dead-end. Driven over the DOM stand-in the region module uses
// (copied, as every module here copies it), with the primary pointer switchable; the fine pointer is the control.
// Synthetic fixtures only: the notes-api world, placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inspect } from "node:util";
import * as fs from "node:fs";
import * as path from "node:path";
import { hideEdges, staysEnumerable } from "../test-dom-shim";
import type { FileViewActionCtx } from "./file-view";
import type { Status, StoreComment } from "./file-comments-model";
import { locateComment } from "./anchor-map";

// ── the DOM stand-in ───────────────────────────────────────────────────────────────────────────────
type Rect = { left: number; top: number; right: number; bottom: number; width: number; height: number };
const rectOf = (left: number, top: number, width: number, height: number): Rect => ({ left, top, width, height, right: left + width, bottom: top + height });
const ZERO = rectOf(0, 0, 0, 0);
type Listener = { fn: (ev: Ev) => void; capture: boolean };
class Doc {
  body: E;
  hidden = false;
  activeElement: E;
  listeners = new Map<string, Listener[]>();
  constructor() { this.body = new E(this, "BODY"); this.activeElement = this.body; }
  createElement(tag: string): E { return new E(this, tag.toUpperCase()); }
  createTextNode(s: string): T { return new T(this, s); }
  getElementById(): null { return null; }
  addEventListener(type: string, fn: (ev: Ev) => void, opts?: boolean | { capture?: boolean }): void {
    const capture = typeof opts === "boolean" ? opts : !!(opts && opts.capture);
    (this.listeners.get(type) || this.listeners.set(type, []).get(type)!).push({ fn, capture });
  }
  removeEventListener(type: string, fn: (ev: Ev) => void): void { const l = this.listeners.get(type); if (l) { const i = l.findIndex((x) => x.fn === fn); if (i >= 0) l.splice(i, 1); } }
  left(n: N): void { if (n.contains(this.activeElement)) this.activeElement = this.body; }
}
class N {
  nodeType = 0;
  parentNode!: N | null;
  childNodes!: N[];
  constructor(public ownerDocument: Doc) {
    // the tree's edges are non-enumerable, so a node inspects as its own projection and a failing assertion's dump
    // stays small (ui/test-dom-shim.ts says why); assignments later keep them hidden
    Object.defineProperty(this, "parentNode", { value: null, writable: true, enumerable: false, configurable: true });
    Object.defineProperty(this, "childNodes", { value: [], writable: true, enumerable: false, configurable: true });
    hideEdges(this);
  }
  get parentElement(): E | null { return this.parentNode instanceof E ? this.parentNode : null; }
  get firstChild(): N | null { return this.childNodes[0] || null; }
  get textContent(): string { return this.nodeType === 3 ? (this as unknown as T).data : this.childNodes.map((c) => c.textContent).join(""); }
  set textContent(v: string) {
    for (const c of this.childNodes) c.parentNode = null;
    this.childNodes = v === "" ? [] : [this.ownerDocument.createTextNode(v)];
    for (const c of this.childNodes) c.parentNode = this;
  }
  contains(n: N | null): boolean { for (let x: N | null = n; x; x = x.parentNode) if (x === this) return true; return false; }
  remove(): void { if (this.parentNode) (this.parentNode as E).removeChild(this); }
}
class T extends N {
  nodeType = 3;
  constructor(doc: Doc, public data: string) { super(doc); hideEdges(this); }
  get length(): number { return this.data.length; }
  splitText(offset: number): T {
    const tail = new T(this.ownerDocument, this.data.slice(offset));
    this.data = this.data.slice(0, offset);
    const p = this.parentNode as E | null;
    if (p) { const i = p.childNodes.indexOf(this); p.childNodes.splice(i + 1, 0, tail); tail.parentNode = p; }
    return tail;
  }
}
type Init = { key?: string; clientX?: number; clientY?: number; pointerId?: number; button?: number };
type Ev = Init & { type: string; target: N; currentTarget: N | null; defaultPrevented: boolean; preventDefault(): void; stopPropagation(): void };
const kebab = (k: string | symbol): string => String(k).replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
type Compound = { tag: string | null; classes: string[]; attrs: Array<[string, string | null]> };
function parseSelector(sel: string): Compound[] {
  return sel.split(",").map((part) => {
    const s = part.trim();
    const out: Compound = { tag: null, classes: [], attrs: [] };
    const re = /^([a-zA-Z][\w-]*)|\.([\w-]+)|\[([\w-]+)(?:="([^"]*)")?\]/g;
    let m: RegExpExecArray | null;
    while ((m = re.exec(s))) {
      if (m[1]) out.tag = m[1].toUpperCase();
      else if (m[2]) out.classes.push(m[2]);
      else out.attrs.push([m[3], m[4] ?? null]);
      if (re.lastIndex === s.length) break;
    }
    return out;
  });
}
class E extends N {
  nodeType = 1;
  attrs = new Map<string, string>();
  listeners = new Map<string, Array<(ev: Ev) => void>>();
  hidden = false; title = ""; type = ""; disabled = false; placeholder = ""; value = ""; checked = false; offsetWidth = 0; tabIndex = -1; readOnly = false;
  width = 0; height = 0;
  naturalWidth = 0; naturalHeight = 0; complete: boolean | undefined = undefined;
  rect: Rect | null = null;
  scrolled = 0;
  style: Record<string, string> = {};
  dataset: Record<string, string>;
  classList = {
    add: (...c: string[]) => this.setClasses([...this.classes(), ...c]),
    remove: (...c: string[]) => this.setClasses(this.classes().filter((x) => !c.includes(x))),
    toggle: (c: string, on?: boolean) => { if (on === undefined ? !this.classes().includes(c) : on) this.classList.add(c); else this.classList.remove(c); },
    contains: (c: string) => this.classes().includes(c),
  };
  constructor(doc: Doc, public tagName: string) {
    super(doc);
    this.dataset = new Proxy({} as Record<string, string>, {
      get: (_t, k) => (typeof k === "string" ? this.attrs.get("data-" + kebab(k)) : undefined),
      set: (_t, k, v) => { this.attrs.set("data-" + kebab(k), String(v)); return true; },
      deleteProperty: (_t, k) => { this.attrs.delete("data-" + kebab(k)); return true; },
      has: (_t, k) => this.attrs.has("data-" + kebab(k)),
    });
    hideEdges(this);
  }
  private classes(): string[] { return (this.attrs.get("class") || "").split(/\s+/).filter(Boolean); }
  private setClasses(c: string[]): void { this.attrs.set("class", [...new Set(c)].join(" ")); }
  get className(): string { return this.attrs.get("class") || ""; }
  set className(v: string) { this.attrs.set("class", v); }
  set innerHTML(html: string) { this.replaceChildren(...parseHTML(this.ownerDocument, html)); }
  getAttribute(n: string): string | null { return this.attrs.has(n) ? (this.attrs.get(n) as string) : null; }
  setAttribute(n: string, v: string): void { this.attrs.set(n, v); }
  removeAttribute(n: string): void { this.attrs.delete(n); }
  hasAttribute(n: string): boolean { return this.attrs.has(n); }
  removeChild(n: N): N { const i = this.childNodes.indexOf(n); if (i >= 0) this.childNodes.splice(i, 1); n.parentNode = null; this.ownerDocument.left(n); return n; }
  appendChild<X extends N>(n: X): X { if (n.parentNode) (n.parentNode as E).removeChild(n); this.childNodes.push(n); n.parentNode = this; return n; }
  insertBefore(n: N, ref: N | null): N {
    if (!ref) return this.appendChild(n);
    if (n.parentNode) (n.parentNode as E).removeChild(n);
    const i = this.childNodes.indexOf(ref);
    this.childNodes.splice(i, 0, n); n.parentNode = this; return n;
  }
  replaceChildren(...c: N[]): void { for (const x of this.childNodes) { x.parentNode = null; this.ownerDocument.left(x); } this.childNodes.length = 0; for (const x of c) this.appendChild(x); }
  normalize(): void {
    const out: N[] = [];
    for (const c of this.childNodes) {
      const prev = out[out.length - 1];
      if (c instanceof T && prev instanceof T) { prev.data += c.data; c.parentNode = null; }
      else if (c instanceof T && c.data === "") c.parentNode = null;
      else out.push(c);
    }
    this.childNodes = out;
  }
  matches(sel: string): boolean {
    return parseSelector(sel).some((c) => (c.tag === null || c.tag === this.tagName)
      && c.classes.every((k) => this.classList.contains(k))
      && c.attrs.every(([a, v]) => this.attrs.has(a) && (v === null || this.attrs.get(a) === v)));
  }
  closest(sel: string): E | null { for (let x: N | null = this; x; x = x.parentNode) if (x instanceof E && x.matches(sel)) return x; return null; }
  querySelectorAll(sel: string): E[] {
    const out: E[] = [];
    const chains = sel.split(",").map((g) => g.trim().split(/\s+/));
    const fits = (el: E, chain: string[]): boolean => {
      if (!el.matches(chain[chain.length - 1])) return false;
      let k = chain.length - 2;
      for (let a: N | null = el.parentNode; a && k >= 0 && a !== this.parentNode; a = a.parentNode) if (a instanceof E && a.matches(chain[k])) k--;
      return k < 0;
    };
    const visit = (n: N) => { for (const c of n.childNodes) { if (c instanceof E) { if (chains.some((ch) => fits(c, ch))) out.push(c); visit(c); } } };
    visit(this);
    return out;
  }
  querySelector(sel: string): E | null { return this.querySelectorAll(sel)[0] || null; }
  addEventListener(type: string, fn: (ev: Ev) => void): void { (this.listeners.get(type) || this.listeners.set(type, []).get(type)!).push(fn); }
  removeEventListener(type: string, fn: (ev: Ev) => void): void { const l = this.listeners.get(type); if (l) l.splice(l.indexOf(fn), 1); }
  dispatch(type: string, init: Init = {}): Ev {
    let stopped = false;
    const ev: Ev = { ...init, type, target: this, currentTarget: null, defaultPrevented: false,
      preventDefault() { this.defaultPrevented = true; }, stopPropagation() { stopped = true; } };
    const doc = this.ownerDocument;
    const at = doc.listeners.get(type) || [];
    for (const l of [...at]) if (l.capture) l.fn(ev);
    for (let n: N | null = this; n && !stopped; n = n.parentNode) {
      if (!(n instanceof E)) continue;
      ev.currentTarget = n;
      for (const fn of [...(n.listeners.get(type) || [])]) fn(ev);
    }
    if (!stopped) for (const l of [...at]) if (!l.capture) l.fn(ev);
    return ev;
  }
  click(): void { this.dispatch("click"); }
  focus(): void { this.ownerDocument.activeElement = this; }
  blur(): void { if (this.ownerDocument.activeElement === this) this.ownerDocument.activeElement = this.ownerDocument.body; }
  getBoundingClientRect(): Rect {
    if (this.rect) return this.rect;
    if (this.classList.contains("fc-imgwrap")) { const img = this.childNodes.find((c) => c instanceof E && c.tagName === "IMG") as E | undefined; return img ? img.getBoundingClientRect() : ZERO; }
    return ZERO;
  }
  setPointerCapture(): void { /* inert */ }
  releasePointerCapture(): void { /* inert */ }
  getContext(): { drawImage(): void } | null { return this.tagName === "CANVAS" ? { drawImage: () => { /* the crop's draw: inert */ } } : null; }   // a canvas draws: the open region card cuts its crop (cropFor)
  scrollIntoView(): void { this.scrolled++; }
}
const VOID = new Set(["br", "hr", "img", "input", "meta", "link", "area", "base", "col", "embed", "source", "track", "wbr"]);
const NAMED: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " " };
function decodeEntities(s: string): string {
  return s.replace(/&(#x[0-9a-fA-F]+|#\d+|[a-zA-Z]+);/g, (m, e: string) => {
    if (e[0] === "#") return String.fromCodePoint(parseInt(e[1] === "x" || e[1] === "X" ? e.slice(2) : e.slice(1), e[1] === "x" || e[1] === "X" ? 16 : 10));
    return e in NAMED ? NAMED[e] : m;
  });
}
function parseHTML(doc: Doc, html: string): N[] {
  html = html.replace(/\r\n?/g, "\n");
  const root = doc.createElement("#fragment");
  const stack: E[] = [root];
  let i = 0;
  const top = () => stack[stack.length - 1];
  while (i < html.length) {
    if (html[i] === "<") {
      if (html.startsWith("<!--", i)) { const e = html.indexOf("-->", i); i = e < 0 ? html.length : e + 3; continue; }
      if (html[i + 1] === "/") {
        const e = html.indexOf(">", i);
        const name = html.slice(i + 2, e).trim().toUpperCase();
        for (let k = stack.length - 1; k > 0; k--) { if (stack[k].tagName === name) { stack.length = k; break; } }
        i = e + 1; continue;
      }
      const m = /^<([a-zA-Z][\w:-]*)((?:\s+[^\s"'>\/=]+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'=<>`]+))?)*)\s*(\/?)>/.exec(html.slice(i));
      if (!m) { top().appendChild(doc.createTextNode("<")); i++; continue; }
      const el = doc.createElement(m[1]);
      const attrRe = /([^\s"'>\/=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?/g;
      let a: RegExpExecArray | null;
      while ((a = attrRe.exec(m[2]))) el.setAttribute(a[1], decodeEntities(a[2] ?? a[3] ?? a[4] ?? ""));
      top().appendChild(el);
      i += m[0].length;
      if (!m[3] && !VOID.has(m[1].toLowerCase())) {
        stack.push(el);
        if (m[1].toLowerCase() === "pre" && html[i] === "\n") i++;
      }
      continue;
    }
    let e = html.indexOf("<", i);
    if (e < 0) e = html.length;
    top().appendChild(doc.createTextNode(decodeEntities(html.slice(i, e))));
    i = e;
  }
  return root.childNodes.slice();
}

// ── globals the modules reach for, installed before they are imported ──────────────────────────────
const doc = new Doc();
const win: any = new EventTarget();
win.parent = win;
win.innerWidth = 1200; win.innerHeight = 800;
win.devicePixelRatio = 1;
win.getSelection = () => ({ isCollapsed: true, rangeCount: 0, toString: () => "" });
/** The primary pointer a test claims: null leaves matchMedia absent (a desktop without it); true is a finger. */
let coarse: boolean | null = null;
win.matchMedia = (q: string) => { if (coarse === null) throw new TypeError("matchMedia is not a function"); return { matches: q === "(pointer: coarse)" && coarse }; };
(globalThis as any).window = win;
(globalThis as any).document = doc;
/** The kernel a test stands up: a 404 to every HEAD and no sessions. */
(globalThis as any).fetch = async () => ({ status: 404, headers: { get: () => null }, json: async () => [] });
const realSetInterval = globalThis.setInterval;
(globalThis as any).setInterval = (fn: () => void, ms: number) => { const t = realSetInterval(fn, ms); (t as any).unref?.(); return t; };
const tick = () => new Promise<void>((r) => setImmediate(r));

// ── fixtures: the notes-api world, a report embedding one figure twice with the same long paragraphs around each ──
const SID = "11111111-2222-3333-4444-555555555555";
const MD = "/repo/notes-api/docs/report.md";
const STORE_MD = "/repo/notes-api/.trackchanges/docs%2Freport.md.json";
const T0 = 1757145600000;
const H1 = "1111111111111111111111111111111111111111111111111111111111111111";
// each paragraph is longer than the host's widening cap (480 characters), so an anchor on either embed line, widened to
// the cap by the host, has the same context at both copies: the copies tie, and only the stored position tells them apart
const BEFORE = "The quick brown fox jumps over the lazy dog. ".repeat(12).trim();
const AFTER = "Pack my box with five dozen liquor jugs. ".repeat(12).trim();
assert.ok(BEFORE.length > 480 && AFTER.length > 480, "the paragraphs outrun the cap");
const EMBED = "![Latency](figs/p95.png)";
const BLOCK = BEFORE + "\n\n" + EMBED + "\n\n" + AFTER;
const DOC = "# Report\n\n" + BLOCK + "\n\n" + BLOCK + "\n";
const FIRST_AT = DOC.indexOf(EMBED);
const SECOND_AT = DOC.indexOf(EMBED, FIRST_AT + 1);
assert.ok(FIRST_AT > 0 && SECOND_AT > FIRST_AT && DOC.indexOf(EMBED, SECOND_AT + 1) === -1, "two embeds");
// the anchor the host stores at its cap for the second embed (engine.makeAnchor with 480 characters of context)
const CAP_ANCHOR = { quote: EMBED, prefix: DOC.slice(SECOND_AT - 480, SECOND_AT), suffix: DOC.slice(SECOND_AT + EMBED.length, SECOND_AT + EMBED.length + 480) };
assert.equal(CAP_ANCHOR.prefix, DOC.slice(FIRST_AT - 480, FIRST_AT), "the same 480 characters before either embed");
// the title edited, and nothing recorded it: both copies moved by the edit's length, and the stored position names neither
const REVISED = DOC.replace("# Report", "# Report, revised");
const SHIFT = REVISED.length - DOC.length;
assert.ok(SHIFT > 0 && SHIFT < (SECOND_AT - FIRST_AT) / 2, "the shift is small: the nearest tied copy to the old position is still the second");
const GUESS_AT = SECOND_AT + SHIFT;   // the engine's pick in REVISED from the stale position: the second copy, a guess
assert.equal(locateComment(REVISED, CAP_ANCHOR, SECOND_AT).range!.start, GUESS_AT, "nearest-wins from the stale position picks the second copy");
const GUESS_LINE = REVISED.slice(0, GUESS_AT).split("\n").length;   // its 1-based line, as the Reveal's title names it
/** The Rendered body marked produces for the report, its title as given. */
const html = (title: string): string =>
  "<h1>" + title + "</h1>\n<p>" + BEFORE + "</p>\n<p><img src=\"figs/p95.png\" alt=\"Latency\"></p>\n<p>" + AFTER + "</p>\n"
  + "<p>" + BEFORE + "</p>\n<p><img src=\"figs/p95.png\" alt=\"Latency\"></p>\n<p>" + AFTER + "</p>\n";
/** A passage comment on the second embed line, as the host saved it: the cap anchor and the located offset. */
const onSecond: StoreComment = {
  id: T0 + "-" + SECOND_AT, author: "you", ts: T0, body: "Use the p99 chart instead.", anchor: CAP_ANCHOR, anchorAt: SECOND_AT, replies: [], resolved: false,
};
// the figure: a 600×400 picture drawn at half size, 100px in and 200px down; the region, a rectangle inside it
const IMG_RECT = rectOf(100, 200, 300, 200);
const REGION = { x: 0.1667, y: 0.2, w: 0.3333, h: 0.3 };
/** A REGION comment drawn on the second figure, as the host saved it: the same anchor and position on the embed line, and
 *  the rectangle with the figure's hash (regionState reads it against the status's embeddedHashes: current). */
const regionOnSecond: StoreComment = {
  id: T0 + "-region", author: "you", ts: T0, body: "Crop the y axis.", anchor: CAP_ANCHOR, anchorAt: SECOND_AT, replies: [], resolved: false,
  target: { kind: "image", region: REGION, hash: H1, src: "figs/p95.png" } as StoreComment["target"],
};
// the panel's words, copied here so a swap or a rewording fails a driven test
const STATE_POSITION = "This passage occurs in the file more than once with the same surroundings, and the position stored with the comment names none of the copies as the file is now, so the copy nearest that position is highlighted, not a confirmed one.";
const REGION_CONFIRM = "To confirm the copy, draw a new region on the figure you mean; this comment keeps its tag until you resolve it. Re-place redraws the rectangle on the figure shown and does not move the comment to another figure. Drawing a region needs a mouse.";
const REGION_CONFIRM_TOUCH = "To confirm the copy, draw a new region on the figure you mean; this comment keeps its tag until you resolve it. Drawing a region needs a mouse.";
const REGION_CONFIRM_TAIL = "; this comment keeps its tag until you resolve it. Re-placing it there redraws the rectangle on the figure it is on and does not move the comment to another figure. Drawing a region needs a mouse.";
const REGION_CONFIRM_UNSEEN = "To confirm the copy, draw a new region on the figure you mean in the view that shows the image" + REGION_CONFIRM_TAIL;
const UNSURE_REGION = STATE_POSITION + " " + REGION_CONFIRM;
const UNSURE_REGION_TOUCH = STATE_POSITION + " " + REGION_CONFIRM_TOUCH;
const UNSURE_REGION_UNSEEN = STATE_POSITION + " " + REGION_CONFIRM_UNSEEN;
/** The sentence a phone's card leaves out: what Re-place does, on a card that has the button. */
const REPLACE_SENTENCE = " Re-place redraws the rectangle on the figure shown and does not move the comment to another figure.";
/** The panel's source, for the pins on how the words are chosen (the tests run from vscode-extension/). */
const web = (f: string): string => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
function mdStatus(comments: StoreComment[]): Status {
  return {
    verb: "status", root: "/repo/notes-api", storePath: STORE_MD, trackedBy: null, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: null,
    store: { v: 3, path: "docs/report.md", suggestions: [], comments },
    hunks: [], log: [], unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null },
    embeddedHashes: { "figs/p95.png": H1 },
  };
}

// ── the harness: a Rendered body (`html`) or a Raw body (the code rows), the seam as closures ──────
const mk = (tag: string, cls: string): E => { const e = doc.createElement(tag); e.className = cls; return e; };
const picture = (img: E): void => { img.rect = IMG_RECT; img.naturalWidth = 600; img.naturalHeight = 400; img.complete = true; };
/** The Raw view's rows, as codeBlock builds them: one `.fv-cl > .fv-ct` per line, a trailing newline being no line. */
function rows(code: E, src: string): void {
  const lines = src.split("\n");
  if (lines.length && lines[lines.length - 1] === "") lines.pop();
  code.replaceChildren(...lines.map((ln) => {
    const cl = mk("span", "fv-cl");
    const ct = mk("span", "fv-ct");
    if (ln) ct.appendChild(doc.createTextNode(ln));
    cl.appendChild(ct);
    return cl;
  }));
}
async function harness(over: { mode: "rendered" | "raw"; src: string; html?: string }) {
  const fc = await import("./file-comments");
  const main = mk("div", "fileview-main");
  const body = mk("div", "fileview-body"); main.appendChild(body);
  if (over.mode === "rendered") {
    const md = mk("div", "fileview-md"); md.innerHTML = over.html!; body.appendChild(md);
    for (const img of md.querySelectorAll("img")) picture(img);
  } else {
    const wrap = mk("div", "fileview-code"); const pre = mk("pre", "fileview-pre fileview-wrap"); const code = mk("code", "hljs");
    rows(code, over.src); pre.appendChild(code); wrap.appendChild(pre); body.appendChild(wrap);
  }
  const posted: Array<Record<string, any>> = [];
  const closers: Array<() => void> = [];
  const modes: string[] = [];
  const offsets: number[] = [];
  let aside: E | null = null;
  const noop = () => { /* inert */ };
  const ctx: FileViewActionCtx = {
    path: MD, sid: SID, todoId: null,
    body: () => body as unknown as HTMLElement,
    mode: () => over.mode,
    text: () => over.src,
    mtimeNs: () => "1757145600000000001",
    media: () => null, pdfPages: () => [], mediaElement: () => null, renderedImages: () => [],
    identity: () => ({ name: "api", color: null }),
    onRendered: noop, onSelection: noop, onSaved: noop, onClose: (cb) => { closers.push(cb); },
    post: (m) => { posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: noop, editing: () => false, setTrackedEdit: noop, guardClose: noop,
    aside: (el) => { if (el) { aside = el as unknown as E; main.appendChild(aside); } else if (aside) { aside.remove(); aside = null; } },
    setMode: (m) => { modes.push(m); }, scrollToOffset: (n) => { offsets.push(n); }, reload: noop,
  };
  const unit = fc.fileCommentsAction.mount(ctx) as unknown as E;
  const button = unit.childNodes[0] as E;
  const last = () => posted[posted.length - 1];
  const reply = async (s: Status) => { win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: last().reqId, ...s } })); await tick(); await tick(); };
  return {
    main, modes, offsets,
    /** Answer the mount's probe, open the panel, answer its refresh: the panel as a person first sees it. */
    open: async (s: Status) => { await reply(s); button.dispatch("click"); await reply(s); },
    q: (sel: string) => main.querySelector(sel),
    qa: (sel: string) => main.querySelectorAll(sel),
    head: (id: string): E => main.querySelector('.fc-card[data-id="' + id + '"] .fc-card-head')!,
    tags: (id: string): E[] => main.querySelector('.fc-card[data-id="' + id + '"] .fc-card-head')!.querySelectorAll(".fc-tag"),
    /** Open the comment's card and hand it back. */
    openCard: (id: string): E => { main.querySelector('.fc-card[data-id="' + id + '"] .fc-card-head')!.dispatch("click"); const card = main.querySelector('.fc-card.open[data-id="' + id + '"]'); assert.ok(card, "the card opens"); return card!; },
    dispose: () => { for (const cb of closers) cb(); },
  };
}
const notesOf = (card: E): string[] => card.querySelectorAll(".fc-note").map((n) => n.textContent);
const buttonsOf = (card: E): string[] => card.querySelectorAll(".fc-actions button").map((b) => b.textContent);
const revealOf = (card: E): E | null => card.querySelector('[data-act="fcreveal"]');
/** The picture a region's rectangle is painted on: the overlay's wrapper holds the picture and the rectangle. */
const pictureOf = (rect: E): E | null => rect.closest(".fc-imgwrap")?.querySelector("img") ?? null;

/** Whether any of a card's words name the Re-place button (not "Re-placing", the verb Raw's words use for the act). */
const namesReplace = (words: string): boolean => /\bRe-place\b/.test(words);

// ── the phone: the picture in view, no pointer that draws, and words that name no Re-place ─────────

test("Rendered view on a coarse pointer (a phone), a region on the second of two embeds after an unrecorded title edit: the rectangle is on the guessed figure, and the tag's title and the open card's one line end with the recourse worded for a card with no Re-place (nothing about a button it lacks; drawing needs a mouse), while the actions are Reply and Resolve", async () => {
  coarse = true;
  try {
    const h = await harness({ mode: "rendered", src: REVISED, html: html("Report, revised") });
    await h.open(mdStatus([regionOnSecond]));
    const [first, second] = h.qa(".fileview-md img");
    const rects = h.qa('.fc-region[data-id="' + regionOnSecond.id + '"]');
    assert.equal(rects.length, 1, "the picture is in view and wears the rectangle: the pictured branch, not Raw's");
    assert.equal(pictureOf(rects[0]), second, "on the second figure: the copy nearest the stale position, the engine's guess");
    assert.notEqual(pictureOf(rects[0]), first);
    const tags = h.tags(regionOnSecond.id);
    assert.deepEqual(tags.map((t) => t.textContent), ["passage recurs"], "the tag: the embed line recurs and the position names no copy");
    assert.equal(tags[0].title, UNSURE_REGION_TOUCH, "its title: the state, then the recourse worded for a card with no Re-place");
    const card = h.openCard(regionOnSecond.id);
    assert.deepEqual(notesOf(card), [UNSURE_REGION_TOUCH], "the open card says the same, in one line");
    assert.deepEqual(buttonsOf(card), ["Reply", "Resolve"], "a finger draws nothing: no Re-place; a region: no Reveal");
    assert.equal(revealOf(card), null);
    assert.ok(!namesReplace(notesOf(card).join(" ")) && !namesReplace(tags[0].title), "no control this card lacks is named");
    assert.ok(UNSURE_REGION_TOUCH.endsWith("Drawing a region needs a mouse."), "the words still say what drawing takes, so the card does not dead-end");
    assert.ok(UNSURE_REGION_TOUCH.includes("draw a new region on the figure you mean;"), "and the recourse a region has");
    h.dispose();
  } finally { coarse = null; }
});

test("the control: the same card on a pointer that draws, with matchMedia absent (a desktop without it) and with it answering fine, names the Re-place it offers (the pictured view's words, word for word), so the sentence about Re-place goes with the button", async () => {
  for (const pointer of [null, false] as Array<boolean | null>) {
    coarse = pointer;
    try {
      const h = await harness({ mode: "rendered", src: REVISED, html: html("Report, revised") });
      await h.open(mdStatus([regionOnSecond]));
      const tags = h.tags(regionOnSecond.id);
      assert.equal(tags[0].title, UNSURE_REGION, "matchMedia " + (pointer === null ? "absent" : "fine") + ": the pictured view's words");
      const card = h.openCard(regionOnSecond.id);
      assert.deepEqual(notesOf(card), [UNSURE_REGION]);
      assert.deepEqual(buttonsOf(card), ["Reply", "Resolve", "Re-place"], "a pointer that draws: Re-place, and no Reveal");
      assert.ok(namesReplace(notesOf(card)[0]), "the words explain the button the card has");
      h.dispose();
    } finally { coarse = null; }
  }
});

test("Raw view on a coarse pointer: the view with no picture is judged first, so the words name the view that shows the image, as they do on a pointer that draws, and the pointer changes nothing there", async () => {
  for (const pointer of [true, null] as Array<boolean | null>) {
    coarse = pointer;
    try {
      const h = await harness({ mode: "raw", src: REVISED });
      await h.open(mdStatus([regionOnSecond]));
      const marks = h.qa(".fc-hl");
      assert.equal(marks.length, 1);
      assert.equal(marks[0].textContent, EMBED, "the embed line stands in for the picture Raw does not show");
      assert.equal(h.tags(regionOnSecond.id)[0].title, UNSURE_REGION_UNSEEN);
      const card = h.openCard(regionOnSecond.id);
      assert.deepEqual(notesOf(card), [UNSURE_REGION_UNSEEN]);
      assert.deepEqual(buttonsOf(card), ["Reply", "Resolve"]);
      assert.ok(!namesReplace(notesOf(card)[0]), "no Re-place on this card either, and none named");
      h.dispose();
    } finally { coarse = null; }
  }
});

test("the words and the actions agree on every pointer in either view: the card's line names Re-place exactly when the card has the button", async () => {
  for (const mode of ["rendered", "raw"] as const) {
    for (const pointer of [null, false, true] as Array<boolean | null>) {
      coarse = pointer;
      try {
        const h = await harness(mode === "rendered" ? { mode, src: REVISED, html: html("Report, revised") } : { mode, src: REVISED });
        await h.open(mdStatus([regionOnSecond]));
        const card = h.openCard(regionOnSecond.id);
        const notes = notesOf(card);
        assert.equal(notes.length, 1, mode + ", pointer " + String(pointer) + ": one line");
        assert.equal(namesReplace(notes[0]), buttonsOf(card).includes("Re-place"), mode + ", pointer " + String(pointer) + ": Re-place is named when, and only when, the card offers it");
        assert.equal(namesReplace(h.tags(regionOnSecond.id)[0].title), buttonsOf(card).includes("Re-place"), "and the tag's title agrees with the line");
        h.dispose();
      } finally { coarse = null; }
    }
  }
});

test("a region whose position names its copy (the text as saved) carries no tag and no note on a coarse pointer, so the phone's words are for a guess alone", async () => {
  coarse = true;
  try {
    const h = await harness({ mode: "rendered", src: DOC, html: html("Report") });
    await h.open(mdStatus([regionOnSecond]));
    assert.deepEqual(h.tags(regionOnSecond.id), []);
    const card = h.openCard(regionOnSecond.id);
    assert.deepEqual(notesOf(card), []);
    assert.deepEqual(buttonsOf(card), ["Reply", "Resolve"]);
    h.dispose();
  } finally { coarse = null; }
});

// ── the words, and how the panel chooses them ─────────────────────────────────────────────────────

test("the phone's words are the pictured view's with the sentence about Re-place left out and nothing else changed; the panel holds both as one literal each, stamps the pointer half of the Re-place gate on the card its words read, and judges the picture before the pointer", () => {
  assert.equal(REGION_CONFIRM_TOUCH, REGION_CONFIRM.replace(REPLACE_SENTENCE, ""), "one sentence fewer, the rest word for word");
  assert.ok(REGION_CONFIRM.includes(REPLACE_SENTENCE), "the sentence is the pictured view's middle one");
  assert.notEqual(REGION_CONFIRM_TOUCH, REGION_CONFIRM);
  assert.ok(!namesReplace(REGION_CONFIRM_TOUCH) && namesReplace(REGION_CONFIRM), "the button is named on the pointer that has it alone");
  assert.ok(REGION_CONFIRM_TOUCH.endsWith("Drawing a region needs a mouse.") && REGION_CONFIRM.endsWith("Drawing a region needs a mouse."), "both end with what drawing takes");
  assert.ok(!/Reveal/.test(REGION_CONFIRM_TOUCH) && !/save/i.test(REGION_CONFIRM_TOUCH), "a region's words name neither the Reveal nor a save");
  const SRC = web("file-comments.ts");
  assert.ok(SRC.includes('const REGION_CONFIRM_TOUCH = "' + REGION_CONFIRM_TOUCH + '";'), "the module holds the panel's words, so a change to either fails here");
  assert.ok(SRC.includes('const REGION_CONFIRM = "' + REGION_CONFIRM + '";'));
  assert.ok(SRC.includes("type Shown = { editing: boolean; pictured: boolean; draws: boolean };"), "what the render shows: the editor, the picture, and a pointer that draws");
  assert.ok(SRC.includes("const c: WordedCard = { ...given, hintedCopy: this.hintedCopies.has(given.id), shown: { editing, pictured: !!picture, draws: this.drawsRegions() } };"), "stamped from the same test the Re-place gate makes");
  assert.match(SRC, /const replaceOffered = \(!!picture \|\| gone\) && !c\.resolved && this\.drawsRegions\(\);/, "the gate: the picture (or a page the PDF lost), an unresolved card, a pointer that draws");
  assert.ok(SRC.includes("if (card.resolved || !card.anchor) continue;"), "the paint skips resolved cards, so a card wearing these words is never resolved and the picture and the pointer are the whole gate");
  const start = SRC.indexOf("function copyUnsureWords(");
  const words = SRC.slice(start, SRC.indexOf("\n}\n", start));
  const unseen = words.indexOf('if (c.target && !c.shown.pictured) return state + ", not a confirmed one. " + REGION_CONFIRM_UNSEEN;');
  const touch = words.indexOf('if (c.target && !c.shown.draws) return state + ", not a confirmed one. " + REGION_CONFIRM_TOUCH;');
  const fine = words.indexOf('if (c.target) return state + ", not a confirmed one. " + REGION_CONFIRM;');
  const passage = words.indexOf('return state + ", not a confirmed one. Reveal it and save again from the right copy to confirm.";');
  assert.ok(unseen >= 0 && touch > unseen && fine > touch && passage > fine, "no picture first, then no pointer that draws, then the pictured view on a pointer that draws, then a passage comment");
});

test("a node of the stand-in enumerates its primitives alone, and its dump names neither its parent nor its children", () => {
  const root = doc.createElement("div");
  const kid = root.appendChild(doc.createElement("span"));
  kid.appendChild(doc.createTextNode("leaf"));
  for (const n of [root, kid, kid.firstChild!]) {
    const o = n as unknown as Record<string, unknown>;
    assert.ok(Object.keys(o).every((k) => staysEnumerable(o[k])), "only primitives enumerate on " + n.constructor.name + ": " + Object.keys(o).join(","));
    const dump = inspect(n, { compact: false, customInspect: false, depth: 1000, maxArrayLength: Infinity, showHidden: false, showProxy: false, sorted: true, getters: true });
    assert.ok(!dump.includes("parentNode") && !dump.includes("childNodes"), "no edge in the dump of " + n.constructor.name);
  }
  assert.equal(kid.parentNode, root); assert.equal(root.childNodes.length, 1); assert.equal(kid.textContent, "leaf");
});
