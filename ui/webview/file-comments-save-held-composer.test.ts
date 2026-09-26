// A comment's save held open, and a new comment or a reply started under it (the user, 2026-09-24, who started a new
// comment, and a reply, while the last comment still read Saving, and found the saving comment's words in the new box).
// The panel has ONE comment box (FileComments.input) that every composer reuses: startComment, startFileComment,
// startReply and the other openers swapped the composer and left the box's value alone, and saveComposer's settle
// closed whichever composer was open when the reply landed (closeComposer) or, on a refusal, left the words in that
// box. So the saving comment's words showed in the new comment's box and in the reply's, read-only under a Saving
// button that was not theirs; the landing closed the box the person had just opened; and a refusal left the words
// in the reply's box, where Save filed them as a reply on another comment. Now an opener empties the box while it still
// holds the saving comment's words (releaseSavingBox, keyed on savingFor), the saving look and the slot's row are the
// saving composer's alone, a second composer's Save waits with the reason in its title and in a line with the romp loader
// in place of the chord hint, under Save and Cancel, and the settle acts on its own comment (settleAway): a refused comment
// comes back into an empty box (after a Cancel too), or waits in a note under a composer holding the person's input (words
// typed, a rectangle drawn, a pending Re-place; words a Re-place's drag left in the hidden box open as a comment on the file
// to hold it), its words whole, with Bring it back once it holds none; a comment that comes back is used up there, and its
// refusal row is its own, shown under it alone; the viewer's close asks while a save is out and about words a Re-place
// hides, and the ask names every comment a yes would drop. With no save out the box still carries its words from one
// composer to the next. Driven through the DOM stand-in the reply-keep test uses, the write held by
// answering it only when the test says; the figure world at the end (a rendered report with a figure and changes, the
// stand-in given the region test's rects, pointer fields and matchMedia) reaches the openers a view with no text cannot, and
// the composers whose input is a drawn rectangle or a pending Re-place. Synthetic fixtures only: the notes-api world,
// placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx, TrackedEdit } from "./file-view";
import type { Status, StoreComment, Hunk } from "./file-comments-model";
import { hideEdges } from "../test-dom-shim";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");

// ── the DOM stand-in ───────────────────────────────────────────────────────────────────────────────
class Doc {
  body: E;
  hidden = false;
  activeElement: E | null = null;
  scrolled: E[] = [];                                  // every scrollIntoView, in order (startReply scrolls the box's card)
  detached: N[] = [];                                  // every node taken out of its parent, in order (a rebuild's detaches)
  focused: E[] = [];                                   // every focus() that landed, in order (a refocus after a move)
  listeners = new Map<string, Array<(ev: unknown) => void>>();
  constructor() { this.body = new E(this, "BODY"); this.activeElement = this.body; }
  createElement(tag: string): E { return new E(this, tag.toUpperCase()); }
  createTextNode(s: string): T { return new T(this, s); }
  getElementById(): null { return null; }
  addEventListener(type: string, fn: (ev: unknown) => void): void { (this.listeners.get(type) || this.listeners.set(type, []).get(type)!).push(fn); }
  removeEventListener(type: string, fn: (ev: unknown) => void): void { const l = this.listeners.get(type); if (l) l.splice(l.indexOf(fn), 1); }
  fire(type: string, target: N): void { for (const fn of this.listeners.get(type) || []) fn({ type, target }); }
}
class N {
  nodeType = 0;
  parentNode!: N | null;
  childNodes!: N[];
  constructor(public ownerDocument: Doc) {
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
type Rect = { left: number; top: number; right: number; bottom: number; width: number; height: number };
const rectOf = (left: number, top: number, width: number, height: number): Rect => ({ left, top, width, height, right: left + width, bottom: top + height });
// a figure drawn at half its 600x400 size, 100px in and 200px down
const IMG_RECT = rectOf(100, 200, 300, 200);
/** A card's client rect by its comment id, which a test gives when where the card stands matters (the saved line reads it:
 *  cardWhere), kept across the renders that rebuild the card's node; a card not listed measures nothing, as before. */
const cardRects = new Map<string, Rect>();
type Init = { key?: string; ctrlKey?: boolean; metaKey?: boolean; shiftKey?: boolean; isComposing?: boolean; clientX?: number; clientY?: number; pointerId?: number; button?: number };
type Ev = Init & { type: string; target: N; currentTarget: N | null; defaultPrevented: boolean; preventDefault(): void; stopPropagation(): void };
const kebab = (k: string | symbol): string => String(k).replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
type Compound = { tag: string | null; classes: string[]; attrs: Array<[string, string | null]> };
function parseSelector(sel: string): Compound[] {
  return sel.split(",").map((part) => {
    const s = part.trim();
    const out: Compound = { tag: null, classes: [], attrs: [] };
    const re = /^([a-zA-Z][\w-]*)|\.([\w-]+)|\[([\w-]+)(?:="((?:[^"\\]|\\.)*)")?\]/g;   // a value may hold \" or \\ (cssId)
    let m: RegExpExecArray | null;
    while ((m = re.exec(s))) {
      if (m[1]) out.tag = m[1].toUpperCase();
      else if (m[2]) out.classes.push(m[2]);
      else out.attrs.push([m[3], m[4] === undefined ? null : m[4].replace(/\\(.)/g, "$1")]);
      if (re.lastIndex === s.length) break;
    }
    return out;
  });
}
class E extends N {
  nodeType = 1;
  attrs = new Map<string, string>();
  listeners = new Map<string, Array<(ev: Ev) => void>>();
  hidden = false; title = ""; type = ""; disabled = false; placeholder = ""; value = ""; checked = false; offsetWidth = 0; readOnly = false;
  rows = 0;
  width = 0; height = 0;                              // a canvas
  naturalWidth = 0; naturalHeight = 0; complete: boolean | undefined = undefined;   // a picture
  rect: Rect | null = null;                          // the client rect a test gives the element (a figure: the overlay places a drag by it)
  // the layout a test gives a box: what the browser would measure at height: auto (autosizeComposer reads these)
  scrollHeight = 0; offsetHeight = 0; clientHeight = 0;
  selectionStart = 0; selectionEnd = 0;
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
  /** As the browser has it: a tabindex attribute, else 0 for a button, an input or a textarea, else -1. */
  get tabIndex(): number { return this.attrs.has("tabindex") ? Number(this.attrs.get("tabindex")) : (this.tagName === "BUTTON" || this.tagName === "INPUT" || this.tagName === "TEXTAREA" ? 0 : -1); }
  set tabIndex(v: number) { this.attrs.set("tabindex", String(v)); }
  private classes(): string[] { return (this.attrs.get("class") || "").split(/\s+/).filter(Boolean); }
  private setClasses(c: string[]): void { this.attrs.set("class", [...new Set(c)].join(" ")); }
  get className(): string { return this.attrs.get("class") || ""; }
  set className(v: string) { this.attrs.set("class", v); }
  set innerHTML(html: string) { this.replaceChildren(...parseHTML(this.ownerDocument, html)); }
  getAttribute(n: string): string | null { return this.attrs.has(n) ? (this.attrs.get(n) as string) : null; }
  setAttribute(n: string, v: string): void { this.attrs.set(n, v); }
  removeAttribute(n: string): void { this.attrs.delete(n); }
  /** A node leaves its parent; if it held the focus (itself or a descendant), the focus fixup rule moves it to the body. */
  detach(n: N): void {
    const i = this.childNodes.indexOf(n); if (i >= 0) this.childNodes.splice(i, 1); n.parentNode = null;
    const doc = this.ownerDocument;
    doc.detached.push(n);
    if (n instanceof E && doc.activeElement && n.contains(doc.activeElement)) doc.activeElement = doc.body;
  }
  removeChild(n: N): N { this.detach(n); return n; }
  appendChild<X extends N>(n: X): X { if (n.parentNode) (n.parentNode as E).detach(n); this.childNodes.push(n); n.parentNode = this; return n; }
  insertBefore(n: N, ref: N | null): N {
    if (!ref) return this.appendChild(n);
    if (n.parentNode) (n.parentNode as E).detach(n);
    const i = this.childNodes.indexOf(ref);
    this.childNodes.splice(i, 0, n); n.parentNode = this; return n;
  }
  replaceChildren(...c: N[]): void { for (const x of this.childNodes.slice()) this.detach(x); for (const x of c) this.appendChild(x); }
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
  /** Dispatch with bubbling: every ancestor's listeners run until one stops propagation. */
  dispatch(type: string, init: Init = {}): Ev {
    let stopped = false;
    const ev: Ev = { ...init, type, target: this, currentTarget: null, defaultPrevented: false,
      preventDefault() { this.defaultPrevented = true; }, stopPropagation() { stopped = true; } };
    for (let n: N | null = this; n && !stopped; n = n.parentNode) {
      if (!(n instanceof E)) continue;
      ev.currentTarget = n;
      for (const fn of [...(n.listeners.get(type) || [])]) fn(ev);
    }
    return ev;
  }
  /** The rect a test gave the element; a figure's wrapper hugs its picture (the sheet's inline-block around a block img). */
  getBoundingClientRect(): Rect {
    if (this.rect) return this.rect;
    if (this.classList.contains("fc-card") && cardRects.has(this.dataset.id)) return cardRects.get(this.dataset.id)!;
    if (this.classList.contains("fc-imgwrap")) { const img = this.childNodes.find((c) => c instanceof E && c.tagName === "IMG") as E | undefined; if (img) return img.getBoundingClientRect(); }
    return this.tagName === "IMG" ? IMG_RECT : rectOf(0, 0, 0, 0);
  }
  setPointerCapture(): void { /* inert */ }
  releasePointerCapture(): void { /* inert */ }
  getContext(): { drawImage(...a: unknown[]): void } | null { return this.tagName === "CANVAS" ? { drawImage: () => { /* inert */ } } : null; }
  scrollIntoView(): void { this.ownerDocument.scrolled.push(this); }
  setSelectionRange(a: number, b: number): void { this.selectionStart = a; this.selectionEnd = b; }
  /** Focus lands only on a focusable, enabled element, as in the browser. */
  focus(): void { if (this.tabIndex >= 0 && !this.disabled) { this.ownerDocument.activeElement = this; this.ownerDocument.focused.push(this); } }
  blur(): void { if (this.ownerDocument.activeElement === this) this.ownerDocument.activeElement = this.ownerDocument.body; }
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

// ── globals the module reaches for, installed before it is imported ────────────────────────────────
const doc = new Doc();
const win: any = new EventTarget();
win.parent = win;
win.innerWidth = 1200; win.innerHeight = 800;
win.devicePixelRatio = 1;
win.getSelection = () => ({ isCollapsed: true, rangeCount: 0, toString: () => "" });
/** The primary pointer a test claims (isCoarsePointer reads window.matchMedia): null leaves matchMedia failing, as on a
 *  desktop without it, which the panel reads as a fine pointer; true is a finger. */
let coarse: boolean | null = null;
win.matchMedia = (q: string) => { if (coarse === null) throw new TypeError("matchMedia is not a function"); return { matches: q === "(pointer: coarse)" && coarse }; };
(globalThis as any).window = win;
(globalThis as any).document = doc;
(globalThis as any).fetch = async () => ({ status: 404, headers: { get: () => null }, json: async () => [] });
const realSetInterval = globalThis.setInterval;
(globalThis as any).setInterval = (fn: () => void, ms: number) => { const t = realSetInterval(fn, ms); (t as any).unref?.(); return t; };
const tick = () => new Promise<void>((r) => setImmediate(r));

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const T0 = 1757145600000;
const DOC = "# Report\n\n## Findings\nThe api session cut p95 latency by 40% and the p99 by 10%.\n\n"
  + "We recommend shipping the cache in v1.2.\n\nRisks remain in the fallback path.\n\nNext steps: measure again.\n";
// a passage comment with two turns under it, so "below the replies" is a place the test can see
const passage: StoreComment = {
  id: T0 + "-118", author: "you", ts: T0, body: "Which cache? Say which.",
  anchor: { quote: "shipping the cache in v1.2", prefix: "We recommend ", suffix: "." },
  replies: [{ author: "api", authorId: SID, ts: T0 + 1000, body: "The response cache." }, { author: "you", ts: T0 + 2000, body: "Say so in the text." }],
  resolved: false,
};
const whole: StoreComment = { id: T0 + "-119", author: "you", ts: T0 + 4000, body: "Lead with the numbers.", replies: [], resolved: false };
const unsent = (...ids: string[]) => ({ comments: ids, replies: [], accepted: 0, rejected: 0, watermark: null });
function status(over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: "/repo/notes-api", storePath: "/repo/notes-api/.trackchanges/docs%2Freport.md.json",
    trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
    store: { v: 3, path: "docs/report.md", suggestions: [], comments: [passage, whole] },
    hunks: [], log: [], unsent: unsent(passage.id, whole.id),
    ...over,
  };
}

// ── the harness: a mounted panel inside the viewer's body row ──────────────────────────────────────
type Posted = Record<string, any>;
const SLOT = ["fc-sec-head", "fc-composer", "fc-sec-cards", "fc-sec-send", "fc-sec-log"];   // the panel's sections with the box in its slot
/** `fig`: the rendered report with a figure (the figure world below), its source the view's text, for the openers a text-less
 *  view cannot reach: a selection's Comment, the figure's Comment, a drag on the figure, Re-place, a spanned change's Comment. */
async function harness(over: Partial<FileViewActionCtx> = {}, fig: { html: string; src: string } | null = null) {
  const fc = await import("./file-comments");
  const main = doc.createElement("div"); main.className = "fileview-main";
  const body = doc.createElement("div"); body.className = "fileview-body"; main.appendChild(body);
  if (fig) {
    const md = doc.createElement("div"); md.className = "fileview-md"; md.innerHTML = fig.html; body.appendChild(md);
    for (const img of md.querySelectorAll("img")) { img.rect = IMG_RECT; img.naturalWidth = 600; img.naturalHeight = 400; img.complete = true; }
  }
  const posted: Posted[] = [];
  const tracked: Array<TrackedEdit | null> = [];
  const closers: Array<() => void> = [];
  const saved: Array<(info: { mtimeNs: string; logged: boolean }) => void> = [];
  let aside: E | null = null;
  const noop = () => { /* inert */ };
  const ctx: FileViewActionCtx = {
    path: ABS, sid: SID, todoId: null,
    body: () => body as unknown as HTMLElement, mode: () => "rendered", text: () => (fig ? fig.src : null),
    mtimeNs: () => "1757145600000000001", error: () => null, media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [], identity: () => ({ name: "api", color: null }),
    onRendered: noop, onSelection: noop, onSaved: (cb) => { saved.push(cb); }, onClose: (cb) => { closers.push(cb); },
    post: (m) => { posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: noop, editing: () => false, setTrackedEdit: (t) => { tracked.push(t); }, guardClose: noop,
    aside: (el) => { if (el) { aside = el as unknown as E; main.appendChild(aside); } else if (aside) { aside.remove(); aside = null; } },
    setMode: noop, scrollToOffset: noop, reload: noop,
    ...over,
  };
  const unit = fc.fileCommentsAction.mount(ctx) as unknown as E;
  const button = unit.childNodes[0] as E;
  const last = (): Posted => posted[posted.length - 1];
  const reply = async (data: Record<string, unknown>) => { win.dispatchEvent(new MessageEvent("message", { data })); await tick(); await tick(); };
  /** The class of each element child, in order: where the box stands is read off this. */
  const kids = (e: E | null): string[] => { assert.ok(e, "an element to read the children of"); return e!.childNodes.filter((n): n is E => n instanceof E).map((n) => n.className); };
  const h = {
    fc, main, body, posted, saved, last, kids,
    ok: (over: Partial<Status> = {}) => reply({ type: "fileCommentsResult", reqId: last().reqId, ...status(over) }),
    refuse: (code: string, error: string) => reply({ type: "fileCommentsFailed", reqId: last().reqId, verb: last().verb, code, error }),
    q: (sel: string) => main.querySelector(sel),
    click: (sel: string) => { const e = main.querySelector(sel); assert.ok(e, "a control " + sel); e!.dispatch("click"); },
    root: (): E => { const r = main.querySelector(".fc-panel"); assert.ok(r, "the panel"); return r!; },
    sections: (): string[] => kids(h.root()),
    box: (): E => { const b = main.querySelector("textarea.fc-input"); assert.ok(b, "the comment box is a textarea"); return b!; },
    composer: (): E => { const c = main.querySelector(".fc-composer"); assert.ok(c, "the composer box"); return c!; },
    card: (id: string): E | null => main.querySelector('.fc-card[data-id="' + id + '"]'),
    /** The slot's reference row, class:text per span. */
    row: (): string[] => h.q('.fc-composer-ref')!.childNodes.map((n) => (n as E).className + ':' + n.textContent),
    key: (init: Init): Ev => h.box().dispatch("keydown", init),
    chord: (): Ev => h.key({ key: "Enter", ctrlKey: true }),
    /** Open the panel on a status. */
    open: async (over: Partial<Status> = {}) => { await h.ok(over); button.dispatch("click"); await h.ok(over); },
    /** Expand a card (by its expand key) and press the Reply of a comment on it. */
    startReply: (key: string, id: string) => { if (!h.card(key)!.classList.contains("open")) h.click('.fc-card[data-id="' + key + '"] .fc-card-head'); h.click('[data-act="fcreply"][data-id="' + id + '"]'); },
    /** The poll's path: a save elsewhere re-asks status, and the reply rebuilds every section. */
    repoll: async (over: Partial<Status> = {}) => { saved[0]({ mtimeNs: "9", logged: true }); await tick(); assert.equal(last().verb, "status", "the precondition: a save elsewhere re-asks the status"); await h.ok(over); },
    dispose: () => { for (const cb of closers) cb(); },
    /** A drag on a figure's overlay: press, move, release, then the click a browser synthesizes after it. */
    drag: (overlay: E, from: [number, number], to: [number, number]) => {
      overlay.dispatch("pointerdown", { clientX: from[0], clientY: from[1], pointerId: 7, button: 0 });
      overlay.dispatch("pointermove", { clientX: to[0], clientY: to[1], pointerId: 7 });
      overlay.dispatch("pointerup", { clientX: to[0], clientY: to[1], pointerId: 7 });
      return overlay.dispatch("click");
    },
    /** The Comment float (the panel's button in the document's body): a selection's offer, or a figure's. */
    float: (): E => { const f = doc.body.querySelectorAll(".fc-float"); assert.ok(f.length, "the Comment float is in the body"); return f[f.length - 1]; },
  };
  return h;
}
/** Set the box's text with a caret and a measured height, as a person typing would leave it. */
function draft(box: E, text: string, caret: number, scrollHeight: number): void {
  box.value = text; box.setSelectionRange(caret, caret);
  box.scrollHeight = scrollHeight; box.offsetHeight = scrollHeight + 2; box.clientHeight = scrollHeight; box.dispatch("input");
}

/** A pending change as the store lists it (the figure world's changes below). */
const sugg = (x: Hunk) => ({ id: x.id, author: x.author, authorId: SID, ts: x.ts, kind: x.kind, from: x.curFrom, oldText: x.oldText, newText: x.newText });

// ── a comment's save held open ────────────────────────────────────────────────────────────────────
const FIRST = "Which fallback? Name it in the text.";
const SAVED: StoreComment = { id: T0 + "-300", author: "you", ts: T0 + 9000, body: FIRST, replies: [], resolved: false };
const AFTER: Partial<Status> = { store: { v: 3, path: "docs/report.md", suggestions: [], comments: [passage, whole, SAVED] }, unsent: unsent(passage.id, whole.id, SAVED.id), storeMtimeNs: "1757145600000000007" };
type H = Awaited<ReturnType<typeof harness>>;
const answer = async (data: Record<string, unknown>) => { win.dispatchEvent(new MessageEvent("message", { data })); await tick(); await tick(); };
/** Comment on this file, the words typed, Save: the comment write is posted and not answered. Returns its reqId. */
async function heldSave(h: H): Promise<number> {
  h.click('[data-act="fcfile"]');
  draft(h.box(), FIRST, FIRST.length, 40);
  h.click('[data-act="fcsave"]');
  await tick(); await tick();
  const m = h.last();
  assert.equal(m.verb, "comment", "the Save posted the comment write");
  assert.equal(m.args.note, FIRST, "…with the words typed");
  assert.equal(h.q('[data-act="fcsave"]')!.textContent, "Saving…", "the precondition: the comment reads Saving while its write is out");
  return m.reqId as number;
}
const landed = (reqId: number) => answer({ type: "fileCommentsResult", reqId, ...status(AFTER) });
const refused = (reqId: number) => answer({ type: "fileCommentsFailed", reqId, verb: "comment", code: "failed", error: "The comments file could not be written; nothing was saved." });

test("a reply started while a comment saves opens empty and takes typing, and the comment's save landing leaves it open with the words typed", async () => {
  const h = await harness();
  await h.open();
  const reqId = await heldSave(h);
  h.startReply(passage.id, passage.id);
  assert.equal(h.box().placeholder, "Your reply", "the Reply opened the reply's box");
  assert.equal(h.box().value, "", "a reply started while another comment saves opens empty: the saving comment's words are not the reply's");
  assert.equal(h.box().readOnly, false, "the reply's box takes typing while the other comment saves");
  draft(h.box(), "The stale-read fallback.", 24, 20);
  await landed(reqId);
  assert.equal(h.composer().hidden, false, "the other comment's save landing leaves the reply's box open");
  assert.equal(h.box().placeholder, "Your reply", "…still the reply");
  assert.equal(h.box().value, "The stale-read fallback.", "…with the words typed in it");
  h.dispose();
});

test("a new comment started while a comment saves opens empty and takes typing, and the first comment's save landing leaves it open with the words typed", async () => {
  const h = await harness();
  await h.open();
  const reqId = await heldSave(h);
  h.click('[data-act="fcfile"]');                      // Comment on this file again: a second comment
  assert.equal(h.box().value, "", "a new comment started while another comment saves opens empty: the saving comment's words are not the new comment's");
  assert.equal(h.box().readOnly, false, "the new comment's box takes typing while the other comment saves");
  draft(h.box(), "Cite the p99 too.", 17, 20);
  await landed(reqId);
  assert.equal(h.composer().hidden, false, "the first comment's save landing leaves the new comment's box open");
  assert.equal(h.box().value, "Cite the p99 too.", "…with the words typed in it");
  h.dispose();
});

test("a comment refused after a reply was started under its save: its words are never filed as that reply", async () => {
  const h = await harness();
  await h.open();
  const reqId = await heldSave(h);
  h.startReply(passage.id, passage.id);
  await refused(reqId);
  const mark = h.posted.length;
  const save = h.q('[data-act="fcsave"]');
  if (save && !save.disabled && !h.composer().hidden) { h.click('[data-act="fcsave"]'); await tick(); await tick(); }
  const asReply = h.posted.slice(mark).filter((p) => p.type === "fileComments" && p.verb === "reply" && p.args && p.args.note === FIRST);
  assert.equal(asReply.length, 0, "the refused comment's words were posted as a reply on another comment");
  h.dispose();
});

// ── where a refused comment's words go when its box was handed on ─────────────────────────────────────
const REFUSAL = "The comments file could not be written; nothing was saved.";
/** The title of the head of a card holding a reply (holdHead). */
const HOLD = "The card stays open while its reply is written; Save or Cancel the reply first";
/** The rows under the open box that are the composer slot's (errRow's data-slot), by their text. */
const slotRows = (h: H): string[] => h.composer().querySelectorAll(".fc-err").filter((e) => e.dataset.slot === "composer").map((e) => e.textContent);
/** The refused comment's note under the open box (heldRows), or null. */
const heldNote = (h: H): E | null => h.composer().querySelector(".fc-held-save");
const bringBack = (h: H): E => { const b = h.composer().querySelector('[data-act="fcheldback"]'); assert.ok(b, "the note's Bring it back"); return b!; };

test("a comment refused after a reply was started under its save, the reply's box still empty: the comment comes back in the box, its words and its refusal row with it", async () => {
  const h = await harness();
  await h.open();
  const reqId = await heldSave(h);
  h.startReply(passage.id, passage.id);
  await refused(reqId);
  assert.equal(h.composer().hidden, false, "the box stays open");
  assert.equal(h.box().placeholder, "Your comment", "the refused comment is back in the box: the comment's, not the reply's");
  assert.equal(h.box().value, FIRST, "…with its words");
  assert.deepEqual(h.row(), ["fc-note:On this file"], "…on its own target, the file");
  assert.deepEqual(h.sections(), SLOT, "…in the panel's slot, out of the card the reply stood in");
  assert.equal(slotRows(h).length, 1, "…with its refusal row under it");
  assert.ok(slotRows(h)[0].includes(REFUSAL), "…the refusal's own words: " + slotRows(h)[0]);
  assert.equal(heldNote(h), null, "no note: the comment itself is back");
  assert.equal(h.box().readOnly, false, "…and its box takes typing");
  const head = h.card(passage.id)!.querySelector(".fc-card-head")!;
  assert.equal(head.getAttribute("aria-disabled"), null, "the card the reply stood in is free again: its head no longer says it holds a reply");
  assert.notEqual(head.title, HOLD, "…nor asks for the reply to be saved or cancelled first");
  h.dispose();
});

test("a reply refused after a new comment was started under its save, the new box still empty: the reply comes back in its card with its words and its refusal row", async () => {
  const h = await harness();
  await h.open();
  h.startReply(passage.id, passage.id);
  draft(h.box(), "The response cache.", 19, 20);
  h.click('[data-act="fcsave"]');
  await tick(); await tick();
  const m = h.last();
  assert.equal(m.verb, "reply", "the precondition: the reply's write is out");
  h.click('[data-act="fcfile"]');
  assert.equal(h.box().value, "", "the new comment opens empty");
  h.click('.fc-card[data-id="' + passage.id + '"] .fc-card-head');   // the card folded meanwhile: the box had left it
  assert.equal(h.card(passage.id)!.classList.contains("open"), false, "the precondition: the card the reply answers is folded");
  await answer({ type: "fileCommentsFailed", reqId: m.reqId, verb: "reply", code: "failed", error: REFUSAL });
  assert.equal(h.box().placeholder, "Your reply", "the refused reply is back in the box");
  assert.equal(h.box().value, "The response cache.", "…with its words");
  assert.equal(h.card(passage.id)!.classList.contains("open"), true, "…its card open again to hold it, as a Reply opens it");
  assert.ok(h.card(passage.id)!.contains(h.box()), "…in the card of the comment it answers");
  assert.equal(h.card(passage.id)!.querySelector(".fc-card-head")!.title, HOLD, "…whose head says it holds the reply, as the cards were rendered with it");
  assert.equal(slotRows(h).length, 1, "…with its refusal row");
  assert.ok(slotRows(h)[0].includes(REFUSAL), "…the refusal's words: " + slotRows(h)[0]);
  h.dispose();
});

test("a comment refused after the person typed in a reply started under its save: the reply keeps its words, and a note under it names the comment and quotes its words, with Bring it back once the box is empty", async () => {
  const h = await harness();
  await h.open();
  const reqId = await heldSave(h);
  h.startReply(passage.id, passage.id);
  draft(h.box(), "The stale-read fallback.", 24, 20);
  const mark = doc.detached.length;
  await refused(reqId);
  assert.equal(h.box().placeholder, "Your reply", "the reply stays open");
  assert.equal(h.box().value, "The stale-read fallback.", "…with the words typed in it");
  assert.equal(h.q('[data-act="fcsave"]')!.disabled, false, "…and its Save is free: the other save settled");
  assert.deepEqual(slotRows(h), [], "the comment's refusal row is not under the reply, which it does not belong to");
  assert.equal(doc.detached.slice(mark).filter((n) => n instanceof E && n.dataset.slot === "composer" && n.classList.contains("fc-err")).length, 0,
    "…at no render, not even the one mutate's end runs before the settle");
  const note = heldNote(h);
  assert.ok(note, "a note under the reply for the refused comment");
  assert.ok(note!.textContent.startsWith("Your comment on this file was not saved:"), "…naming what it was on: " + note!.textContent);
  assert.equal(note!.querySelector(".fc-held-words")?.textContent, FIRST, "…quoting its words, in the note's own element");
  assert.equal(bringBack(h).disabled, true, "Bring it back waits while the reply's box holds words: nothing typed is overwritten");
  assert.equal(bringBack(h).title, "Save or clear this reply first", "…and says why, in the reply's terms");
  const drop = note!.querySelector('[data-act="fcheldx"]')!;
  assert.equal(drop.textContent, "✕", "the note's dismiss keeps its glyph");
  assert.equal(drop.getAttribute("aria-label"), "Dismiss the comment that was not saved; its words go with it", "…and its name says what it drops, since the words go with it");
  assert.equal(drop.title, "Dismiss the comment that was not saved; its words go with it", "…and so does its title");
  bringBack(h).dispatch("click");                     // a browser sends a disabled button no click; one that arrives anyway changes nothing
  await tick();
  assert.equal(h.box().value, "The stale-read fallback.", "a click on the waiting Bring it back leaves the reply's words where they are");
  assert.ok(heldNote(h), "…and the note in place");
  draft(h.box(), "", 0, 20);
  assert.equal(bringBack(h).disabled, false, "the box emptied: Bring it back is enabled");
  assert.equal(bringBack(h).title, "", "…with no reason left in its title");
  draft(h.box(), "x", 1, 20);
  assert.equal(bringBack(h).disabled, true, "a word typed again: it waits again");
  draft(h.box(), "", 0, 20);
  doc.activeElement = doc.body;                       // the press left the keyboard on the page: Safari gives a clicked button no focus
  bringBack(h).dispatch("click");
  await tick();
  assert.equal(h.box().placeholder, "Your comment", "Bring it back puts the refused comment in the box");
  assert.equal(h.box().value, FIRST, "…with its words");
  assert.deepEqual(h.row(), ["fc-note:On this file"], "…on its own target");
  assert.equal(slotRows(h).length, 1, "…and its refusal row");
  assert.ok(slotRows(h)[0].includes(REFUSAL), "…the refusal's words: " + slotRows(h)[0]);
  const rowX = h.composer().querySelectorAll(".fc-err").find((e) => e.dataset.slot === "composer")!.querySelector('[data-act="fcerrx"]')!;
  assert.equal(rowX.getAttribute("aria-label"), "Dismiss", "the refusal row's ✕, which only hides the message, keeps its name");
  assert.equal(heldNote(h), null, "the note is used up");
  assert.equal(h.box().readOnly, false, "the comment's box takes typing");
  assert.equal(doc.activeElement, h.box(), "…and has the keyboard, though the press left it on the page: the person asked for the comment back");
  h.dispose();
});

test("the refused comment's note stays through a re-render until it is used or dismissed; with the note standing, a Cancel of the reply brings the comment back, and a dismissed note brings nothing back", async () => {
  const h = await harness();
  await h.open();
  let reqId = await heldSave(h);
  h.startReply(passage.id, passage.id);
  draft(h.box(), "The stale-read fallback.", 24, 20);
  await refused(reqId);
  await h.repoll();
  assert.ok(heldNote(h), "the note stays through the poll's re-render");
  h.click('[data-act="fccancel"]');
  assert.equal(h.composer().hidden, false, "the reply cancelled with the note standing: the refused comment comes back, as a refusal with no box open does");
  assert.equal(h.box().placeholder, "Your comment", "…the comment's box");
  assert.equal(h.box().value, FIRST, "…with its words");
  assert.ok(slotRows(h).length === 1 && slotRows(h)[0].includes(REFUSAL), "…and its refusal row: " + slotRows(h).join(" | "));
  h.dispose();
  const g = await harness();
  await g.open();
  reqId = await heldSave(g);
  g.startReply(passage.id, passage.id);
  draft(g.box(), "The stale-read fallback.", 24, 20);
  await refused(reqId);
  g.q('[data-act="fcheldx"]')!.focus();              // the keyboard on the dismiss itself, which goes with its note
  g.click('[data-act="fcheldx"]');
  assert.equal(heldNote(g), null, "dismissed: the note is gone");
  assert.equal(g.box().value, "The stale-read fallback.", "…and the reply's words stay");
  assert.equal(doc.activeElement, g.box(), "…and the keyboard, on the dismiss that went with the note, is in the box, not on the page");
  g.click('[data-act="fccancel"]');
  assert.equal(g.composer().hidden, true, "the reply cancelled after the dismiss: nothing comes back, the comment was dropped on purpose");
  g.dispose();
});

test("a refused comment waiting in its note is asked about when the viewer closes, even with the box emptied, and not once it is dismissed", async () => {
  const asks: Array<() => { question: string; kept: string } | null> = [];
  const h = await harness({ guardClose: (a) => { asks.push(a); } });
  await h.open();
  const reqId = await heldSave(h);
  h.startReply(passage.id, passage.id);
  draft(h.box(), "The stale-read fallback.", 24, 20);
  await refused(reqId);
  draft(h.box(), "", 0, 20);
  const put = () => asks.map((a) => a()).filter((q): q is { question: string; kept: string } => q !== null);
  assert.deepEqual(put(), [{ question: "Discard the unsaved comment on report.md?", kept: "This file stays open: a comment on report.md was not saved. Bring it back and save it, or dismiss it, then try again." }],
    "the close asks about the refused comment: its words are not saved, and the box being empty drops nothing else");
  h.click('[data-act="fcheldx"]');
  assert.deepEqual(put(), [], "dismissed: nothing left to ask about");
  h.dispose();
});

test("the close names every comment a yes would drop: the one typed and each refused one waiting in its note, so a yes never discards a comment the ask left out", async () => {
  type Ask = { question: string; kept: string };
  const asks: Array<() => Ask | null> = [];
  const h = await harness({ guardClose: (a) => { asks.push(a); } });
  await h.open();
  const put = () => asks.map((a) => a()).filter((q): q is Ask => q !== null);
  const first = await heldSave(h);
  h.startReply(passage.id, passage.id);
  draft(h.box(), "The stale-read fallback.", 24, 20);
  await refused(first);
  assert.ok(heldNote(h), "the precondition: the refused comment waits in a note under the reply, whose words stay");
  assert.deepEqual(put(), [{ question: "Discard the reply typed to a comment on report.md and the comment that was not saved?",
    kept: "This file stays open: the reply typed to a comment on report.md and the comment that was not saved are still here. Save or clear the box, and bring back or dismiss the one that was not saved, then try again." }],
    "words typed and a refused comment waiting, no save out: the ask names both, the typed reply as a reply");
  h.click('[data-act="fcsave"]');                      // the reply's save, then a new comment typed under it, and the reply refused too
  await tick(); await tick();
  const second = h.last();
  assert.equal(second.verb, "reply", "the precondition: the reply's write is out");
  h.click('[data-act="fcfile"]');
  draft(h.box(), "Cite the p99 too.", 17, 20);
  await answer({ type: "fileCommentsFailed", reqId: second.reqId, verb: "reply", code: "failed", error: REFUSAL });
  assert.equal(h.composer().querySelectorAll(".fc-held-save").length, 2, "the precondition: two refused comments wait in notes");
  assert.deepEqual(put(), [{ question: "Discard the comment typed on report.md and the 2 comments and replies that were not saved?",
    kept: "This file stays open: the comment typed on report.md and the 2 comments and replies that were not saved are still here. Save or clear the box, and bring back or dismiss the ones that were not saved, then try again." }],
    "…and with two waiting, a comment and a reply, the ask counts them in words that fit both");
  draft(h.box(), "", 0, 20);
  assert.deepEqual(put(), [{ question: "Discard the 2 unsaved comments and replies on report.md?", kept: "This file stays open: 2 comments and replies on report.md were not saved. Bring each back and save it, or dismiss it, then try again." }],
    "the box emptied: the ask names the two refused ones, not one");
  h.dispose();
});

test("while a save is out, each ask's kept text says a comment or a reply on the file is still saving, and to act once it has finished: words typed with a refused comment waiting, one waiting, several, and a refused reply named as a reply", async () => {
  type Ask = { question: string; kept: string };
  const asks: Array<() => Ask | null> = [];
  const h = await harness({ guardClose: (a) => { asks.push(a); } });
  await h.open();
  const put = () => asks.map((a) => a()).filter((q): q is Ask => q !== null);
  const first = await heldSave(h);
  h.startReply(passage.id, passage.id);
  draft(h.box(), "The stale-read fallback.", 24, 20);
  await refused(first);
  assert.ok(heldNote(h), "the precondition: the refused comment waits in a note under the reply");
  h.click('[data-act="fcsave"]');                      // the reply's save out, then a new comment typed under it
  await tick(); await tick();
  const second = h.last();
  assert.equal(second.verb, "reply", "the precondition: the reply's write is out");
  h.click('[data-act="fcfile"]');
  draft(h.box(), "Cite the p99 too.", 17, 20);
  const REPLY_OUT = " A reply to a comment on report.md is still saving; if it is not saved, its words are lost too.";
  assert.deepEqual(put(), [{ question: "Discard the comment typed on report.md and the comment that was not saved?" + REPLY_OUT,
    kept: "This file stays open: the comment typed on report.md and the comment that was not saved are still here, and a reply to a comment on report.md is still saving. When that save has finished, save or clear the box, and bring back or dismiss the one that was not saved, then try again." }],
    "words typed and a refused comment waiting while a reply saves: the kept text says the reply is still saving, and to act once it has finished");
  draft(h.box(), "", 0, 20);
  assert.deepEqual(put(), [{ question: "Discard the unsaved comment on report.md?" + REPLY_OUT,
    kept: "This file stays open: a comment on report.md was not saved, and a reply to a comment on report.md is still saving. When that save has finished, bring back the comment that was not saved and save it, or dismiss it, then try again." }],
    "one refused comment waiting while a reply saves: the same");
  draft(h.box(), "Cite the p99 too.", 17, 20);
  await answer({ type: "fileCommentsFailed", reqId: second.reqId, verb: "reply", code: "failed", error: REFUSAL });
  assert.equal(h.composer().querySelectorAll(".fc-held-save").length, 2, "the precondition: the reply refused too, two wait in notes");
  h.click('[data-act="fcsave"]');                      // the new comment's own save out over the two notes
  await tick(); await tick();
  const third = h.last();
  assert.equal(third.args.note, "Cite the p99 too.", "the precondition: the new comment's save is out");
  assert.deepEqual(put(), [{ question: "Discard the 2 unsaved comments and replies on report.md? A comment on report.md is still saving; if it is not saved, its words are lost too.",
    kept: "This file stays open: 2 comments and replies on report.md were not saved, and a comment on report.md is still saving. When that save has finished, bring back each one that was not saved and save it, or dismiss it, then try again." }],
    "several waiting while the open comment's own save is out: the same, a comment and a reply counted in words that fit both");
  await answer({ type: "fileCommentsResult", reqId: third.reqId, ...status(AFTER) });
  assert.equal(h.box().value, FIRST, "the precondition: the save landed and the first refused comment came back");
  assert.deepEqual(put(), [{ question: "Discard the comment typed on report.md and the reply that was not saved?",
    kept: "This file stays open: the comment typed on report.md and the reply that was not saved are still here. Save or clear the box, and bring back or dismiss the one that was not saved, then try again." }],
    "the comment back in the box and the reply waiting: the refused reply named as a reply");
  draft(h.box(), "", 0, 20);
  assert.deepEqual(put(), [{ question: "Discard the unsaved reply to a comment on report.md?", kept: "This file stays open: a reply to a comment on report.md was not saved. Bring it back and save it, or dismiss it, then try again." }],
    "the box emptied: the one refused reply, as a reply");
  h.dispose();
});

test("a refused comment waiting in a note under a composer whose own save is out: Bring it back says the comment comes back when that save lands, since the box can be neither saved nor cleared then, and it does", async () => {
  for (const [name, start, words, reason] of [
    ["a reply", (h: H) => h.startReply(passage.id, passage.id), "The stale-read fallback.", "It comes back when this reply has saved"],
    ["a new comment", (h: H) => h.click('[data-act="fcfile"]'), "Cite the p99 too.", "It comes back when this comment has saved"],
  ] as Array<[string, (h: H) => void, string, string]>) {
    const h = await harness();
    await h.open();
    const reqId = await heldSave(h);
    start(h);
    draft(h.box(), words, words.length, 20);
    await refused(reqId);
    assert.ok(heldNote(h), name + ": the precondition: the refused comment waits in a note under it");
    h.click('[data-act="fcsave"]');
    await tick(); await tick();
    const m = h.last();
    assert.equal(h.q('[data-act="fcsave"]')!.textContent, "Saving…", name + ": the precondition: its own save is out");
    assert.equal(h.box().readOnly, true, name + ": …its box read-only");
    assert.equal(bringBack(h).disabled, true, name + ": Bring it back waits while that save is out");
    assert.equal(bringBack(h).title, reason, name + ": …and says when the comment comes back, not to save or clear a box that cannot be saved or cleared now");
    await answer({ type: "fileCommentsResult", reqId: m.reqId, ...status(AFTER) });
    assert.equal(h.box().placeholder, "Your comment", name + ": its save landed: the refused comment comes back, as the reason said");
    assert.equal(h.box().value, FIRST, name + ": …with its words");
    h.dispose();
  }
});

test("while a comment saves, the viewer's close asks, a new comment's empty box open or none: a refusal after the close would lose the comment's words with no ask and no row", async () => {
  type Ask = { question: string; kept: string };
  const asks: Array<() => Ask | null> = [];
  const h = await harness({ guardClose: (a) => { asks.push(a); } });
  await h.open();
  const put = () => asks.map((a) => a()).filter((q): q is Ask => q !== null);
  const SAVING: Ask = { question: "A comment on report.md is still saving. Close anyway? If it is not saved, its words are lost.", kept: "This file stays open: a comment on report.md is still saving. Try again when it has finished." };
  const reqId = await heldSave(h);
  h.click('[data-act="fcfile"]');                      // a new comment under the save: its box empty
  assert.equal(h.box().value, "", "the precondition: the new comment's box is empty");
  assert.deepEqual(put(), [SAVING], "an empty new comment open while the other saves: the close asks about the comment saving");
  draft(h.box(), "Cite the p99 too.", 17, 20);
  assert.deepEqual(put(), [{ question: "Discard the unsaved comment on report.md? A comment on report.md is still saving; if it is not saved, its words are lost too.",
    kept: "This file stays open: the comment typed on report.md is not saved, and a comment on report.md is still saving. When that save has finished, save the typed comment or clear the box, then try again." }],
    "words typed in the new box as well: the ask names both, and the kept text says to act once the save has finished, since Save waits until then");
  h.click('[data-act="fccancel"]');
  assert.deepEqual(put(), [SAVING], "the new comment cancelled, no box open: the close still asks about the comment saving");
  await landed(reqId);
  assert.deepEqual(put(), [], "the save landed: nothing left to ask about");
  h.dispose();
  const gAsks: Array<() => Ask | null> = [];
  const g = await harness({ guardClose: (a) => { gAsks.push(a); } });
  await g.open();
  await heldSave(g);
  assert.deepEqual(gAsks.map((a) => a()).filter((q): q is Ask => q !== null), [SAVING], "the saving comment's own box open, its words the save's: the ask is the save's too");
  g.dispose();
  // a reply as the saving one: named as a reply, alone and beside a comment typed under it
  const rAsks: Array<() => Ask | null> = [];
  const r = await harness({ guardClose: (a) => { rAsks.push(a); } });
  await r.open();
  const rPut = () => rAsks.map((a) => a()).filter((q): q is Ask => q !== null);
  await heldFrom(r, (x) => x.startReply(passage.id, passage.id), "The response cache.");
  assert.equal(r.last().verb, "reply", "the precondition: the reply's write is out");
  assert.deepEqual(rPut(), [{ question: "A reply to a comment on report.md is still saving. Close anyway? If it is not saved, its words are lost.", kept: "This file stays open: a reply to a comment on report.md is still saving. Try again when it has finished." }],
    "a reply saving: the ask names it as a reply, to a comment on the file");
  r.click('[data-act="fcfile"]');
  draft(r.box(), "Cite the p99 too.", 17, 20);
  assert.deepEqual(rPut(), [{ question: "Discard the unsaved comment on report.md? A reply to a comment on report.md is still saving; if it is not saved, its words are lost too.",
    kept: "This file stays open: the comment typed on report.md is not saved, and a reply to a comment on report.md is still saving. When that save has finished, save the typed comment or clear the box, then try again." }],
    "…and beside a comment typed under it, still as a reply");
  r.dispose();
});

test("Cancel during a comment's save, then a refusal: the comment comes back in the box with its words and its refusal row", async () => {
  const h = await harness();
  await h.open();
  const reqId = await heldSave(h);
  h.click('[data-act="fccancel"]');
  assert.equal(h.composer().hidden, true, "the precondition: Cancel closed the box during the save");
  await refused(reqId);
  assert.equal(h.composer().hidden, false, "the refused comment comes back in view");
  assert.equal(h.box().placeholder, "Your comment", "…the comment's box");
  assert.equal(h.box().value, FIRST, "…with its words, which the Cancel had taken out of the box but the save still held");
  assert.equal(slotRows(h).length, 1, "…and its refusal row, shown");
  assert.ok(slotRows(h)[0].includes(REFUSAL), "…the refusal's words: " + slotRows(h)[0]);
  h.dispose();
});

test("a refused comment brought back while another comment's save is out shows its own refusal row, whatever that save does to the shared row, until its own next save", async () => {
  const h = await harness();
  await h.open();
  const first = await heldSave(h);
  h.startReply(passage.id, passage.id);
  draft(h.box(), "The stale-read fallback.", 24, 20);
  await refused(first);
  assert.ok(heldNote(h), "the precondition: the refused comment waits in a note under the reply");
  h.click('[data-act="fcsave"]');
  await tick(); await tick();
  const second = h.last();
  assert.equal(second.verb, "reply", "the precondition: the reply's write is out");
  h.click('[data-act="fcfile"]');                      // a new comment under the reply's save: the box is handed on, empty
  assert.equal(h.box().value, "", "the precondition: the new comment opens empty");
  bringBack(h).focus();
  bringBack(h).dispatch("click");
  await tick();
  assert.equal(h.box().value, FIRST, "the refused comment is back with its words");
  assert.equal(slotRows(h).length, 1, "…and its own refusal row, though the reply's save holds the shared slot");
  assert.ok(slotRows(h)[0].includes(REFUSAL), "…the comment's refusal: " + slotRows(h)[0]);
  const OTHER = "The comments file moved; nothing was saved.";
  await answer({ type: "fileCommentsFailed", reqId: second.reqId, verb: "reply", code: "failed", error: OTHER });
  assert.deepEqual(slotRows(h).map((r) => r.replace(/✕$/, "")), [REFUSAL], "the reply refused too: under the comment, the comment's own row still, never the reply's");
  assert.ok(heldNote(h) && heldNote(h)!.textContent.startsWith("Your reply to “Which cache? Say which.” was not saved:"), "…and the reply waits in a note under it: " + (heldNote(h) ? heldNote(h)!.textContent : "none"));
  h.click('[data-act="fcsave"]');                      // the comment's next save attempt
  await tick(); await tick();
  assert.equal(h.last().verb, "comment", "the precondition: the comment's save went");
  assert.deepEqual(slotRows(h), [], "its next save attempt: the old row goes, the slot's row is this save's");
  h.dispose();
});

test("a comment refused with a Reload, brought back while another comment's save is out: its row offers no Reload during that save, whose slot a Reload's status ask would free for a second write, and offers it once the save settles", async () => {
  const h = await harness();
  await h.open();
  const first = await heldSave(h);
  h.startReply(passage.id, passage.id);
  draft(h.box(), "The stale-read fallback.", 24, 20);
  // the comments file busy twice: the write goes once more from a fresh status, and the second refusal offers Reload (mutateOnce)
  const BUSY = "Another write to the comments file is under way; nothing was saved.";
  await answer({ type: "fileCommentsFailed", reqId: first, verb: "comment", code: "busy", error: BUSY });
  assert.equal(h.last().verb, "status", "the precondition: a busy refusal reads the status again before its one retry");
  await h.ok();
  const retry = h.last();
  assert.equal(retry.verb, "comment", "…and the write goes once more");
  await answer({ type: "fileCommentsFailed", reqId: retry.reqId, verb: "comment", code: "busy", error: BUSY });
  assert.ok(heldNote(h), "the precondition: the refused comment waits in a note under the reply");
  h.click('[data-act="fcsave"]');
  await tick(); await tick();
  const second = h.last();
  assert.equal(second.verb, "reply", "the precondition: the reply's write is out");
  h.click('[data-act="fcfile"]');                      // a new comment under the reply's save: the box is handed on, empty
  bringBack(h).focus();
  bringBack(h).dispatch("click");
  await tick();
  assert.equal(h.box().value, FIRST, "the precondition: the refused comment is back with its words");
  const row = () => h.composer().querySelectorAll(".fc-err").find((e) => e.dataset.slot === "composer") || null;
  assert.ok(row() && row()!.textContent.includes(BUSY), "…and its own refusal row: " + (row() ? row()!.textContent : "none"));
  // the person takes what the row offers, then presses Save: while the reply's write is out nothing else may be written
  const mark = h.posted.length;
  const offered = row()!.querySelector('[data-act="fcreload"]');
  if (offered) { offered.dispatch("click"); await tick(); if (h.last().verb === "status") await h.ok(); }
  h.click('[data-act="fcsave"]');
  await tick(); await tick();
  assert.equal(h.posted.slice(mark).filter((p) => p.type === "fileComments" && (p.verb === "comment" || p.verb === "reply")).length, 0,
    "no second write while the reply's is out: a Reload's status ask ends by freeing the slot the reply's write holds");
  assert.equal(offered, null, "during the reply's save the comment's row offers no Reload");
  await answer({ type: "fileCommentsResult", reqId: second.reqId, ...status() });
  assert.ok(row() && row()!.textContent.includes(BUSY), "the reply landed: the comment's own row still stands");
  assert.ok(row()!.querySelector('[data-act="fcreload"]'), "…and offers its Reload now that no save holds the slot");
  h.dispose();
});

test("while a comment saves, a new comment's Save waits with the reason in its title, the chord writes nothing, and both are free once the save settles", async () => {
  const h = await harness();
  await h.open();
  const reqId = await heldSave(h);
  h.click('[data-act="fcfile"]');
  const save = () => h.q('[data-act="fcsave"]')!;
  assert.equal(save().textContent, "Save", "the new comment's Save is its own: it does not read Saving");
  assert.equal(save().disabled, true, "…and waits: one write at a time");
  assert.equal(save().title, "The previous comment is still saving", "…saying why");
  assert.equal(h.composer().querySelector('.fc-load[data-slot="composer"]'), null, "the save's loader is the saving comment's, not under the new box");
  draft(h.box(), "Cite the p99 too.", 17, 20);
  const mark = h.posted.length;
  h.chord();
  await tick(); await tick();
  assert.equal(h.posted.slice(mark).filter((p) => p.type === "fileComments" && p.verb === "comment").length, 0, "the chord writes nothing while the other save is out");
  assert.equal(save().textContent, "Save", "…and leaves the new comment as it was: no Saving on it");
  assert.equal(h.box().readOnly, false, "…its box still taking typing");
  assert.equal(save().title, "The previous comment is still saving", "…its Save still waiting for the other save");
  await h.repoll();                                   // a re-render while the first save is still out
  assert.equal(save().textContent, "Save", "after the chord and a re-render the new comment still does not read Saving: the chord left the first save marked as the one out");
  assert.equal(h.box().readOnly, false, "…and its box still takes typing");
  await landed(reqId);
  assert.equal(save().disabled, false, "the save settled: the new comment's Save is free");
  assert.equal(save().title, "", "…with no reason left in its title");
  h.chord();
  await tick(); await tick();
  assert.equal(h.last().verb, "comment", "the chord now saves the new comment");
  assert.equal(h.last().args.note, "Cite the p99 too.", "…with its own words");
  h.dispose();
});

const MAC = typeof navigator !== "undefined" && /Mac|iP(?:hone|ad|od)/.test(navigator.platform || "");
const SAVE_WAITS = "The previous comment is still saving";
/** Under a composer waiting on another save, one line in place of the chord hint, with the romp loader and the reason, on a
 *  fine pointer and on a coarse one: a title reaches no touch pointer, the saving composer's loader is not on screen, and the
 *  hint would say the chord saves while it does nothing. A reply's save is named as a reply. The line stands on a row of its
 *  own under Save and Cancel, never between them: at a phone's width the row wrapped with the line first, and Cancel fell to a
 *  row below Save. */
const SAVE_WAITS_REPLY = "The previous reply is still saving";
const holdComment = (h: H): Promise<number> => heldSave(h);
const holdReply = async (h: H): Promise<number> => (await heldFrom(h, (x) => x.startReply(passage.id, passage.id), "The response cache.")).reqId as number;
/** The rules of a sheet whose selector names `cls` as a class, with their bodies: a rule pin reads them. */
const rulesNaming = (css: string, cls: string): Array<{ sel: string; body: string }> =>
  Array.from(css.replace(/\/\*[\s\S]*?\*\//g, "").matchAll(/([^{}]+)\{([^{}]*)\}/g)).map((m) => ({ sel: m[1].trim(), body: m[2] }))
    .filter((r) => new RegExp("\\." + cls + "(?![\\w-])").test(r.sel));
for (const [pointer, touch, name, start, hold, words] of [
  ["a fine pointer", null, "a new comment under a comment's save", (h: H) => h.click('[data-act="fcfile"]'), holdComment, SAVE_WAITS],
  ["a coarse pointer", true, "a reply under a comment's save", (h: H) => h.startReply(passage.id, passage.id), holdComment, SAVE_WAITS],
  ["a fine pointer", null, "a new comment under a reply's save", (h: H) => h.click('[data-act="fcfile"]'), holdReply, SAVE_WAITS_REPLY],
] as Array<[string, boolean | null, string, (h: H) => void, (h: H) => Promise<number>, string]>) {
  test("on " + pointer + ", " + name + ", whose Save waits on that save, shows one line with the romp loader and the reason in place of the chord hint, on a row of its own under Save and Cancel (a rule pin on both sheets), and the hint comes back once the save settles", async () => {
    coarse = touch;
    try {
      const h = await harness();
      await h.open();
      const reqId = await hold(h);
      start(h);
      const acts = () => h.composer().querySelector(".fc-actions")!;
      const wait = acts().querySelector(".fc-wait");
      assert.ok(wait, "a line in the hint's place under the waiting composer: the previous save is out");
      assert.equal(wait!.querySelector(".fc-wait-words")?.textContent, words, "…saying so in the Save's words, a reply's save named as a reply");
      assert.ok(wait!.querySelector('img[src="/media/romp-swirl-glyph.svg"]'), "…with the romp loader's swirl");
      assert.equal(wait!.querySelectorAll(".fileview-dot").length, 3, "…and its three dots");
      assert.equal(h.composer().querySelector(".fc-hint"), null, "the chord hint gives its place: the chord saves nothing meanwhile");
      const row = acts().childNodes.filter((n): n is E => n instanceof E);
      assert.deepEqual(row.map((n) => n.dataset.act || n.className), ["fcsave", "fccancel", "fileview-load fc-load fc-wait"],
        "Save and Cancel side by side, then the line after both: never between the two buttons");
      for (const f of ["styles.css", "feed.css"]) {
        // a rule pin: the stand-in lays nothing out, so the row of its own is held by the two rules it needs in each sheet (a
        // Chromium check at 390 and 320 px, made by hand and not committed, saw the line on its own row under the buttons)
        const rule = web(f).split("\n").find((l) => l.startsWith(".fc-wait {"));
        assert.ok(rule, f + ": a rule for the line");
        assert.match(rule!, /\{[^}]*\bflex: 1 1 100%;/, f + ": the line takes the full width of the buttons' row, so it wraps onto a row of its own under Save and Cancel: " + rule);
        assert.doesNotMatch(rule!, /\{[^}]*(?:white-space: nowrap|margin-right: auto|order:)/, f + ": nothing keeps it on the buttons' row or moves it before them: " + rule);
        const actsRules = rulesNaming(web(f), "fc-actions");
        const base = actsRules.filter((r) => r.sel === ".fc-actions");
        assert.equal(base.length, 1, f + ": one rule for the buttons' row: " + JSON.stringify(base));
        assert.match(base[0].body, /\bdisplay: flex;/, f + ": the buttons' row is a flex row (a rule pin): " + base[0].body);
        assert.match(base[0].body, /\bflex-wrap: wrap;/, f + ": …that wraps, which the line's row of its own needs (a rule pin; with the wrap gone, a Chromium render put the line back on the buttons' row at every width tried, 390, 320 and 1000 px): " + base[0].body);
        const over = actsRules.filter((r) => r !== base[0] && /\bflex-wrap\s*:/.test(r.body));
        assert.deepEqual(over.map((r) => r.sel), [], f + ": no other rule sets flex-wrap on the buttons' row (a rule pin)");
      }
      assert.equal(h.composer().querySelectorAll(".fc-wait-words").length, 1, "…and the reason once under the box, not a second time elsewhere");
      assert.equal(h.q('[data-act="fcsave"]')!.title, words, "the waiting Save keeps its title, in the same words");
      await landed(reqId);
      assert.equal(h.composer().querySelector(".fc-wait"), null, "the save landed: the line goes");
      const hint = h.composer().querySelector(".fc-hint");
      assert.ok(hint, "…and the chord hint is back");
      assert.equal(hint!.textContent, h.fc.composerHint(MAC, touch === true), "…in the device's words");
      h.dispose();
    } finally { coarse = null; }
  });
}

test("on a coarse pointer, where a title never reaches, a waiting Bring it back's reason stands as a line inside its note; a fine pointer keeps the title alone", async () => {
  coarse = true;
  try {
    const h = await harness();
    await h.open();
    const reqId = await heldSave(h);
    h.startReply(passage.id, passage.id);
    draft(h.box(), "The stale-read fallback.", 24, 20);
    await refused(reqId);
    const backWhy = () => { const l = h.composer().querySelector(".fc-held-why"); assert.ok(l, "a line under the note"); return l!; };
    assert.equal(backWhy().hidden, false, "Bring it back waits: its reason shows");
    assert.equal(backWhy().textContent, "Save or clear this reply first.", "…in the title's words");
    assert.equal(backWhy().parentElement, heldNote(h), "…as a line inside its note, so it stands closer to its own note than to the next one");
    draft(h.box(), "", 0, 20);
    assert.equal(backWhy().hidden, true, "the box emptied: Bring it back acts, and the line hides");
    draft(h.box(), "x", 1, 20);
    assert.equal(backWhy().hidden, false, "a word typed again: the line again");
    assert.equal(backWhy().textContent, "Save or clear this reply first.", "…in the same words, kept in step by the keystroke");
    h.dispose();
  } finally { coarse = null; }
  const g = await harness();
  await g.open();
  const reqId = await heldSave(g);
  g.startReply(passage.id, passage.id);
  draft(g.box(), "The stale-read fallback.", 24, 20);
  await refused(reqId);
  assert.equal(g.composer().querySelector(".fc-held-why"), null, "a fine pointer: Bring it back's title alone");
  assert.equal(bringBack(g).title, "Save or clear this reply first", "…which says why it waits, in the reply's terms");
  g.dispose();
});

test("with no save out the box still carries its words from one composer to the next, and words typed in a composer opened during a save carry on the same way", async () => {
  const h = await harness();
  await h.open();
  h.click('[data-act="fcfile"]');
  draft(h.box(), "Lead with the p95.", 18, 20);
  h.startReply(passage.id, passage.id);
  assert.equal(h.box().placeholder, "Your reply", "the Reply opened the reply's box");
  assert.equal(h.box().value, "Lead with the p95.", "no save out: the words carry from the comment into the reply's box, as they always have");
  h.click('[data-act="fcfile"]');
  assert.equal(h.box().value, "Lead with the p95.", "…and back into Comment on this file");
  h.dispose();
  const g = await harness();
  await g.open();
  const reqId = await heldSave(g);
  g.click('[data-act="fcfile"]');
  draft(g.box(), "Cite the p99 too.", 17, 20);
  g.startReply(passage.id, passage.id);
  assert.equal(g.box().value, "Cite the p99 too.", "words typed in a composer opened during the save are that composer's, not the save's: they carry on to the next one");
  await landed(reqId);
  assert.equal(g.box().value, "Cite the p99 too.", "…and stay through the save's landing");
  g.dispose();
});

// ── the figure world: a rendered report with a figure, a long sentence and three changes ─────────────
const FIG_SRC = "## Findings\n\n![Figure](figure.png)\n\nWe recommend shipping the cache in v1.2 once the fallback path has been measured again under the full production load.\n\nRisks remain in the fallback path.\n";
const FIG_HTML = '<h2>Findings</h2>\n<p><img src="figure.png" alt="Figure"></p>\n<p>We recommend shipping the cache in v1.2 once the fallback path has been measured again under the full production load.</p>\n<p>Risks remain in the fallback path.</p>\n';
const FIG = { html: FIG_HTML, src: FIG_SRC };
const HASH = "1111111111111111111111111111111111111111111111111111111111111111";
const REGION = { x: 0.1667, y: 0.2, w: 0.3333, h: 0.3 };   // the drag from (150,240) to (250,300) over IMG_RECT
const figRegion: StoreComment = { id: T0 + "-400", author: "you", ts: T0, body: "The axis label is wrong.", replies: [], resolved: false,
  anchor: { quote: "![Figure](figure.png)", prefix: "## Findings\n\n", suffix: "\n\nWe recommend shipping" }, target: { kind: "image", region: REGION, hash: HASH, src: "figure.png" } };
const figPassage: StoreComment = { id: T0 + "-401", author: "you", ts: T0 + 1000, body: "Which cache? Say which.",
  anchor: { quote: "shipping the cache in v1.2", prefix: "We recommend ", suffix: " once the fallback" }, replies: [], resolved: false };
const at = (s: string) => FIG_SRC.indexOf(s);
const LONG = "once the fallback path has been measured again under the full production load";   // 79 characters
const hR: Hunk = { id: "hR", author: "api", ts: T0 - 90000, kind: "sub", curFrom: at("Risks"), curTo: at("Risks") + 5, baseFrom: at("Risks"), baseTo: at("Risks") + 7, oldText: "Hazards", newText: "Risks", anchor: null };
const hL: Hunk = { id: "hL", author: "api", ts: T0 - 80000, kind: "ins", curFrom: at(LONG), curTo: at(LONG) + LONG.length, baseFrom: at(LONG), baseTo: at(LONG), oldText: "", newText: LONG, anchor: null };
const hX: Hunk = { id: "hX", author: "api", ts: T0 - 70000, kind: "del", curFrom: at(" in the fallback path."), curTo: at(" in the fallback path."), baseFrom: at(" in the fallback path."), baseTo: at(" in the fallback path.") + 6, oldText: " still", newText: "", anchor: null };
const FIG_STATUS: Partial<Status> = { store: { v: 3, path: "docs/report.md", suggestions: [hR, hL, hX].map(sugg), comments: [figRegion, figPassage] },
  hunks: [hR, hL, hX], unsent: unsent(figRegion.id, figPassage.id), embeddedHashes: { "figure.png": HASH } };
const overlayOf = (h: H): E => { const o = h.q(".fileview-md .fc-overlay"); assert.ok(o, "the figure's overlay"); return o!; };
/** A selection of `text` inside the long sentence's paragraph, as the panel reads it (window.getSelection). */
function selectIn(h: H, text: string): void {
  const p = h.body.querySelectorAll(".fileview-md p").find((x) => x.textContent.includes(text));
  assert.ok(p, "the paragraph holding " + text);
  const node = p!.childNodes.find((n): n is T => n instanceof T && n.data.includes(text));
  assert.ok(node, "a text node holding " + text);
  const a = node!.data.indexOf(text), f = a + text.length;
  win.getSelection = () => ({ isCollapsed: false, anchorNode: node, focusNode: node, anchorOffset: a, focusOffset: f, rangeCount: 1,
    getRangeAt: () => ({ intersectsNode: (n: N) => n === node || (n instanceof E && n.contains(node!)), commonAncestorContainer: p }), toString: () => text });
}
const unselect = () => { win.getSelection = () => ({ isCollapsed: true, rangeCount: 0, toString: () => "" }); };
/** The seven openers, each by the gesture that opens it, with the placeholder its box wears. */
const OPENERS: Array<[string, (h: H) => void | Promise<void>, string]> = [
  ["startImageComment (the figure's Comment)", (h) => {
    const o = overlayOf(h);
    o.dispatch("pointerdown", { clientX: 150, clientY: 240, pointerId: 8, button: 0 });
    o.dispatch("pointerup", { clientX: 150, clientY: 240, pointerId: 8 });
    assert.equal(h.float().hidden, false, "the precondition: the figure's click offers Comment");
    h.float().dispatch("click");
  }, "Your comment"],
  ["startComment (a selection's Comment)", (h) => { selectIn(h, "We recommend"); try { h.float().dispatch("click"); } finally { unselect(); } }, "Your comment"],
  ["startFileComment (Comment on this file)", (h) => h.click('[data-act="fcfile"]'), "Your comment"],
  ["startReply (Reply)", (h) => h.startReply(figPassage.id, figPassage.id), "Your reply"],
  ["startChangeComment (Comment on this change)", (h) => h.click('[data-act="fcchangecomment"][data-id="hR"]'), "Your comment"],
  ["onRegionDrawn (a drag on the figure)", (h) => { h.drag(overlayOf(h), [150, 240], [250, 300]); }, "Your comment"],
  ["startReplace (Re-place)", (h) => { if (!h.card(figRegion.id)!.classList.contains("open")) h.click('.fc-card[data-id="' + figRegion.id + '"] .fc-card-head'); h.click('.fc-card[data-id="' + figRegion.id + '"] [data-act="fcreplace"]'); }, "Your comment"],
];
for (const [name, open, placeholder] of OPENERS) {
  // a Re-place takes a drag on the picture, not words: its box is hidden, and emptied all the same, since the saving words
  // left in it would carry to the next composer
  const replace = name.startsWith("startReplace");
  test("while a comment saves, " + name + (replace ? " opens with its box hidden and emptied" : " opens an empty box that takes typing") + ": the saving comment's words stay the save's", async () => {
    const h = await harness({}, FIG);
    await h.open(FIG_STATUS);
    await heldSave(h);
    await open(h);
    assert.equal(h.composer().hidden, false, "the composer is open");
    assert.equal(h.box().placeholder, placeholder, "…the opener's own");
    assert.equal(h.box().value, "", name + " during the save opens empty: the saving comment's words are not its box's");
    if (replace) assert.equal(h.box().hidden, true, "…its box hidden: a Re-place takes a drag on the picture, not words");
    else assert.equal(h.box().readOnly, false, "…and its box takes typing");
    h.dispose();
  });
}

/** A composer opened by `start`, the words typed, Save: its write is posted and not answered. Returns the write. */
async function heldFrom(h: H, start: (h: H) => void, words: string): Promise<Posted> {
  start(h);
  draft(h.box(), words, words.length, 20);
  h.click('[data-act="fcsave"]');
  await tick(); await tick();
  const m = h.last();
  assert.ok(m.verb === "comment" || m.verb === "reply", "the precondition: the Save posted the write");
  assert.equal(m.args.note, words, "…with the words typed");
  return m;
}
const refuseWrite = (m: Posted) => answer({ type: "fileCommentsFailed", reqId: m.reqId, verb: m.verb, code: "failed", error: REFUSAL });
/** What each kind of refused comment is named as in its note under a box the person typed in (refusedWhat's branches). */
const LABELS: Array<[string, (h: H) => void, string]> = [
  ["a reply to a passage comment names the comment it answers by its first words, in quote marks", (h) => h.startReply(figPassage.id, figPassage.id), "Your reply to “Which cache? Say which.”"],
  ["a reply to a region comment names the comment by its first words too, not by the region's corners", (h) => h.startReply(figRegion.id, figRegion.id), "Your reply to “The axis label is wrong.”"],
  ["a comment on a passage longer than a card's reference names it as the card would, on one line, cut to 72 characters", (h) => h.click('[data-act="fcchangecomment"][data-id="hL"]'),
    "Your comment on “" + LONG.slice(0, 71) + "…”"],
  ["a comment on a region names the region", (h) => { h.drag(overlayOf(h), [150, 240], [250, 300]); }, "Your comment on the region at 0.17, 0.20, 0.33, 0.30"],
  ["a comment about a change with no passage names the change by what it did, the verb outside the quote marks and the change's words inside", (h) => h.click('[data-act="fcchangecomment"][data-id="hX"]'), "Your comment about the change that removed “still”"],
];
/** The sheet rule a class carries in each of the two sheets (the viewer mounts in both documents), by its head at a line start. */
const sheet = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const ruleOf = (css: string, head: string): string => { const at = css.indexOf("\n" + head); assert.ok(at >= 0, "a rule " + head); return css.slice(at + 1, css.indexOf("}", at)); };
for (const [name, start, label] of LABELS) {
  test("the note for a refused comment, the box handed on to a comment the person typed in: " + name + ", and shows the refused words whole, wrapped, with nothing clipped", async () => {
    const h = await harness({}, FIG);
    await h.open(FIG_STATUS);
    const WORDS = "Say which figure, and cite the run it came from.";
    const m = await heldFrom(h, start, WORDS);
    h.click('[data-act="fcfile"]');
    // the box at the opening, before a word is typed in it: the held write is this row's kind (a region's among them), and the
    // opener hands on an empty box only when that write marked its composer as the one saving (writeFor)
    assert.equal(h.box().value, "", "Comment on this file during the save opens empty: the saving comment's words are not its box's");
    assert.equal(h.box().readOnly, false, "…and its box takes typing");
    assert.equal(h.q('[data-act="fcsave"]')!.textContent, "Save", "…its Save its own, not reading Saving");
    draft(h.box(), "Lead with the numbers.", 22, 20);
    await refuseWrite(m);
    const note = heldNote(h);
    assert.ok(note, "a note under the new comment for the refused one");
    assert.equal(note!.querySelector(".fc-note")!.textContent, label + " was not saved:", "the note names what the refused comment was on");
    const words = note!.querySelector(".fc-held-words");
    assert.ok(words, "the refused words in the note's own element, not the reference row's one clipped line (.fc-quote)");
    assert.equal(words!.textContent, WORDS, "…all of them");
    assert.equal(note!.querySelector(".fc-quote"), null, "…and nothing in the note wears the reference row's clipping class");
    for (const f of ["styles.css", "feed.css"]) {
      const r = ruleOf(sheet(f), ".fc-held-words {");
      assert.match(r, /white-space: pre-wrap;/, f + ": the words wrap, their line breaks kept");
      assert.doesNotMatch(r, /nowrap|ellipsis|overflow: hidden/, f + ": nothing clips them: " + r);
    }
    assert.equal(bringBack(h).title, "Save or clear this comment first", "Bring it back waits on the new comment's words, in a comment's terms");
    assert.equal(h.box().value, "Lead with the numbers.", "the new comment's words stay");
    h.dispose();
  });
}

test("a region comment's save held: Comment on this file opens empty and takes typing, its Save its own; with that box left empty, the refusal brings the region's comment back in its own composer, with its own refusal row", async () => {
  const h = await harness({}, FIG);
  await h.open(FIG_STATUS);
  const WORDS = "The axis starts at zero.";
  const m = await heldFrom(h, (x) => { x.drag(overlayOf(x), [150, 240], [250, 300]); }, WORDS);
  assert.ok(m.args.target, "the precondition: the region's write is out, with its target: " + JSON.stringify(m.args));
  h.click('[data-act="fcfile"]');
  assert.equal(h.box().value, "", "Comment on this file during the region's save opens empty: the region's words are not its box's");
  assert.equal(h.box().readOnly, false, "…and its box takes typing");
  assert.equal(h.q('[data-act="fcsave"]')!.textContent, "Save", "…its Save its own, not reading Saving");
  await refuseWrite(m);
  assert.deepEqual(h.row().slice(0, 1), ["fc-note:On the region at 0.17, 0.20, 0.33, 0.30"], "the box left empty: the refused region comment is back in its own composer, its reference row naming the region");
  assert.equal(h.box().value, WORDS, "…with its words");
  assert.ok(slotRows(h).length === 1 && slotRows(h)[0].includes(REFUSAL), "…and its own refusal row: " + slotRows(h).join(" | "));
  assert.equal(heldNote(h), null, "no note: the comment itself is back");
  h.dispose();
});

/** A reply's note names the comment it answers by that comment's first words whatever the comment is on: a comment on the whole
 *  file (the card's reference alone reads "this file"), and a comment whose words run past a card's bound or over lines. */
const LONG_WHOLE: StoreComment = { id: T0 + "-121", author: "you", ts: T0 + 6000, replies: [], resolved: false,
  body: "Lead with the numbers, then the method.\nSay which run the p99 came from and how many requests it covered." };
const WITH_LONG: Partial<Status> = { store: { v: 3, path: "docs/report.md", suggestions: [], comments: [passage, whole, LONG_WHOLE] }, unsent: unsent(passage.id, whole.id, LONG_WHOLE.id) };
for (const [name, id, label] of [
  ["a comment on the whole file", whole.id, "Your reply to “Lead with the numbers.”"],
  ["a comment whose words run over two lines and past 72 characters, on one line and cut as a card's reference is", LONG_WHOLE.id,
    "Your reply to “" + LONG_WHOLE.body.replace(/\s+/g, " ").slice(0, 71) + "…”"],
] as Array<[string, string, string]>) {
  test("the note for a refused reply names the comment it answers by its first words: " + name, async () => {
    const h = await harness();
    await h.open(WITH_LONG);
    const m = await heldFrom(h, (g) => g.startReply(id, id), "The stale-read fallback.");
    assert.equal(m.verb, "reply", "the precondition: the reply's write is out");
    h.click('[data-act="fcfile"]');
    draft(h.box(), "Cite the p99 too.", 17, 20);
    await refuseWrite(m);
    const note = heldNote(h);
    assert.ok(note, "a note under the new comment for the refused reply");
    assert.equal(note!.querySelector(".fc-note")!.textContent, label + " was not saved:", "the note names the comment the reply answers");
    h.dispose();
  });
}

// ── a composer holding a drawn rectangle or a pending Re-place is not an empty one ─────────────────────
test("a refused comment, the box handed on to a region just drawn: the region stays with its rectangle and the refused comment waits in a note until the region is cancelled", async () => {
  const h = await harness({}, FIG);
  await h.open(FIG_STATUS);
  const reqId = await heldSave(h);
  h.drag(overlayOf(h), [150, 240], [250, 300]);
  assert.equal(h.box().value, "", "the precondition: the region's box is empty");
  await refused(reqId);
  assert.deepEqual(h.row().slice(0, 1), ["fc-note:On the region at 0.17, 0.20, 0.33, 0.30"], "the region drawn stays: the rectangle is the person's input, as typed words are");
  assert.equal(h.box().value, "", "…its box as it was");
  const note = heldNote(h);
  assert.ok(note, "the refused comment waits in a note under it");
  assert.ok(note!.textContent.startsWith("Your comment on this file was not saved:"), note!.textContent);
  assert.equal(bringBack(h).disabled, true, "Bring it back waits: it would replace the region");
  assert.equal(bringBack(h).title, "Save or Cancel this comment first", "…and says why");
  assert.deepEqual(slotRows(h), [], "no refusal row under the region, which it does not belong to");
  h.click('[data-act="fccancel"]');
  assert.equal(h.box().placeholder, "Your comment", "the region cancelled: the refused comment comes back");
  assert.equal(h.box().value, FIRST, "…with its words");
  assert.deepEqual(h.row(), ["fc-note:On this file"], "…on its own target");
  assert.ok(slotRows(h).length === 1 && slotRows(h)[0].includes(REFUSAL), "…and its refusal row: " + slotRows(h).join(" | "));
  h.dispose();
});

test("a refused comment, the box handed on to a pending Re-place: the Re-place stays and the refused comment waits in a note; the drag that places the region brings the comment back", async () => {
  const h = await harness({}, FIG);
  await h.open(FIG_STATUS);
  const reqId = await heldSave(h);
  h.click('.fc-card[data-id="' + figRegion.id + '"] .fc-card-head');
  h.click('.fc-card[data-id="' + figRegion.id + '"] [data-act="fcreplace"]');
  await refused(reqId);
  assert.ok(h.row()[0].startsWith("fc-note:Drag the comment's new place on the image"), "the Re-place stays: its pending placement is the person's input: " + h.row()[0]);
  const note = heldNote(h);
  assert.ok(note, "the refused comment waits in a note under it");
  assert.ok(note!.textContent.startsWith("Your comment on this file was not saved:"), note!.textContent);
  assert.equal(bringBack(h).disabled, true, "Bring it back waits: it would end the Re-place");
  assert.equal(bringBack(h).title, "Draw the new place or Cancel the re-place first", "…and says why");
  h.drag(overlayOf(h), [110, 210], [190, 260]);
  await tick();
  assert.equal(h.last().verb, "retarget", "the precondition: the drag placed the region");
  assert.equal(h.composer().hidden, false, "the Re-place done: the refused comment comes back, as when a composer closes over its note");
  assert.equal(h.box().placeholder, "Your comment", "…the comment's box");
  assert.equal(h.box().value, FIRST, "…with its words");
  assert.ok(slotRows(h).length === 1 && slotRows(h)[0].includes(REFUSAL), "…and its refusal row: " + slotRows(h).join(" | "));
  h.dispose();
});

test("a Re-place's drag with a refused comment waiting in its note and words an earlier composer left in the box: the words and the note stand in the panel's slot, not in a hidden box", async () => {
  const h = await harness({}, FIG);
  await h.open(FIG_STATUS);
  const reqId = await heldSave(h);
  h.click('[data-act="fcfile"]');                      // a new comment under the save, the words typed, then Re-place: the words carry, hidden
  draft(h.box(), "Cite the p99 too.", 17, 20);
  h.click('.fc-card[data-id="' + figRegion.id + '"] .fc-card-head');
  h.click('.fc-card[data-id="' + figRegion.id + '"] [data-act="fcreplace"]');
  await refused(reqId);
  assert.ok(heldNote(h), "the precondition: the refused comment waits in a note under the Re-place");
  h.drag(overlayOf(h), [110, 210], [190, 260]);
  await tick();
  assert.equal(h.last().verb, "retarget", "the precondition: the drag placed the region");
  assert.equal(h.composer().hidden, false, "the Re-place done: the box stays in view, the note and the words with it");
  assert.deepEqual(h.sections(), SLOT, "…in the panel's slot");
  assert.equal(h.box().hidden, false, "…the words in a box that shows");
  assert.equal(h.box().value, "Cite the p99 too.", "…the words the earlier composer left, as they were");
  assert.deepEqual(h.row(), ["fc-note:On this file"], "…as a comment on the file, which Save files and Cancel drops");
  const note = heldNote(h);
  assert.ok(note, "the note under them");
  assert.ok(note!.textContent.startsWith("Your comment on this file was not saved:"), note!.textContent);
  assert.equal(bringBack(h).disabled, true, "…whose Bring it back waits on the words");
  h.click('[data-act="fccancel"]');
  assert.equal(h.box().value, FIRST, "the words cancelled: the refused comment comes back");
  h.dispose();
});

// ── a refused comment that comes back is used up; its own row is its own ─────────────────────────────
const FIG_AFTER: Partial<Status> = { ...FIG_STATUS, store: { v: 3, path: "docs/report.md", suggestions: [hR, hL, hX].map(sugg), comments: [figRegion, figPassage, SAVED] },
  unsent: unsent(figRegion.id, figPassage.id, SAVED.id), storeMtimeNs: "1757145600000000007" };
/** The two places a waiting comment comes back when the composer over its note ends: that composer's close (closeComposer:
 *  Cancel here; Escape and its own save landing take the same path), and a Re-place's drag, which ends the Re-place without it. */
const COMEBACKS: Array<[string, boolean, (h: H) => void, (h: H) => void]> = [
  ["a reply's Cancel (the composer's close)", false,
    (h) => { h.startReply(passage.id, passage.id); draft(h.box(), "The stale-read fallback.", 24, 20); },
    (h) => h.click('[data-act="fccancel"]')],
  ["a Re-place's drag", true,
    (h) => { h.click('.fc-card[data-id="' + figRegion.id + '"] .fc-card-head'); h.click('.fc-card[data-id="' + figRegion.id + '"] [data-act="fcreplace"]'); },
    (h) => { h.drag(overlayOf(h), [110, 210], [190, 260]); }],
];
for (const [name, fig, setUp, end] of COMEBACKS) {
  test("a refused comment that comes back at " + name + " is used up there: its note goes with it, its save lands once, and it never comes back again with the words it filed", async () => {
    const h = fig ? await harness({}, FIG) : await harness();
    await h.open(fig ? FIG_STATUS : {});
    const first = await heldSave(h);
    setUp(h);
    await refused(first);
    assert.ok(heldNote(h), "the precondition: the refused comment waits in a note under the composer");
    end(h);
    await tick();
    assert.equal(h.box().placeholder, "Your comment", "the precondition: the refused comment came back");
    assert.equal(h.box().value, FIRST, "…with its words");
    const noteLeft = heldNote(h) !== null;             // read now, asserted with the rest below, so the record shows every consequence at once
    const mark = h.posted.length;
    h.click('[data-act="fcsave"]');
    await tick(); await tick();
    const m = h.last();
    assert.equal(m.verb, "comment", "the precondition: the comment's save went");
    assert.equal(m.args.note, FIRST, "…with its words");
    await answer({ type: "fileCommentsResult", reqId: m.reqId, ...status(fig ? FIG_AFTER : AFTER) });
    const cameBackAgain = !h.composer().hidden && h.box().value === FIRST;
    // the person saves whatever the box then shows, as they would any comment in front of them
    if (!h.composer().hidden && !h.q('[data-act="fcsave"]')!.disabled) { h.click('[data-act="fcsave"]'); await tick(); await tick(); }
    const writes = h.posted.slice(mark).filter((p) => p.type === "fileComments" && p.verb === "comment" && p.args && p.args.note === FIRST).length;
    assert.deepEqual({ noteLeft, cameBackAgain, writes }, { noteLeft: false, cameBackAgain: false, writes: 1 },
      "coming back used the note up: no note stands under the comment it names, the comment's save landing brings nothing back, and its words are written once");
    assert.equal(h.composer().hidden, true, "the box closed with the save");
    h.dispose();
  });
}

for (const [name, open, placeholder] of [
  ["a reply", (h: H) => h.startReply(passage.id, passage.id), "Your reply"],
  ["a new comment", (h: H) => h.click('[data-act="fcfile"]'), "Your comment"],
] as Array<[string, (h: H) => void, string]>) {
  test("a refused comment's own refusal row shows under that comment alone: " + name + " opened in its place shows none, at the opening or after", async () => {
    const h = await harness();
    await h.open();
    const reqId = await heldSave(h);
    h.click('[data-act="fccancel"]');
    await refused(reqId);
    assert.ok(slotRows(h).length === 1 && slotRows(h)[0].includes(REFUSAL), "the precondition: the comment came back with its own refusal row: " + slotRows(h).join(" | "));
    open(h);
    assert.equal(h.box().placeholder, placeholder, "the precondition: " + name + " opened in the comment's place");
    assert.deepEqual(slotRows(h), [], name + " in the comment's place: the comment's row is not under it, which it does not belong to");
    await h.repoll();
    assert.deepEqual(slotRows(h), [], "…nor after the poll's re-render");
    h.dispose();
  });
}

test("a refused comment's own refusal row goes on its dismiss (✕) and on its Reload, and no render after brings it back", async () => {
  const ownRow = (x: H): E | null => x.composer().querySelectorAll(".fc-err").find((e) => e.dataset.slot === "composer") || null;
  const h = await harness();
  await h.open();
  const reqId = await heldSave(h);
  h.click('[data-act="fccancel"]');
  await refused(reqId);
  assert.ok(ownRow(h) && ownRow(h)!.textContent.includes(REFUSAL), "the precondition: the comment came back with its own refusal row");
  ownRow(h)!.querySelector('[data-act="fcerrx"]')!.dispatch("click");
  assert.equal(ownRow(h), null, "dismissed: the comment's own row is gone");
  await h.repoll();
  assert.equal(ownRow(h), null, "…and the poll's re-render does not bring it back");
  assert.equal(h.box().value, FIRST, "the comment's words stay in the box");
  h.dispose();
  const g = await harness();
  await g.open();
  const first = await heldSave(g);
  g.click('[data-act="fccancel"]');
  // the comments file busy twice: the write goes once more from a fresh status, and the second refusal offers Reload (mutateOnce)
  const BUSY = "Another write to the comments file is under way; nothing was saved.";
  await answer({ type: "fileCommentsFailed", reqId: first, verb: "comment", code: "busy", error: BUSY });
  assert.equal(g.last().verb, "status", "the precondition: a busy refusal reads the status again before its one retry");
  await g.ok();
  const retry = g.last();
  assert.equal(retry.verb, "comment", "…and the write goes once more");
  await answer({ type: "fileCommentsFailed", reqId: retry.reqId, verb: "comment", code: "busy", error: BUSY });
  assert.equal(g.box().value, FIRST, "the precondition: the comment came back with its words");
  assert.ok(ownRow(g) && ownRow(g)!.textContent.includes(BUSY), "…and its own refusal row");
  const reload = ownRow(g)!.querySelector('[data-act="fcreload"]');
  assert.ok(reload, "…which offers Reload");
  reload!.dispatch("click");
  await tick();
  assert.equal(g.last().verb, "status", "the precondition: Reload asked the status again");
  assert.equal(ownRow(g), null, "Reload taken: the comment's own row gives way to the wait");
  await g.ok();
  assert.equal(ownRow(g), null, "…and the status's landing does not bring it back");
  assert.equal(g.box().value, FIRST, "…the comment's words stay in the box");
  g.dispose();
});

// ── Bring it back's reason, as the composer over the note changes ───────────────────────────────────
for (const [pointer, name, start, words, saving, reason, touch] of [
  ["a fine pointer", "a reply", (h: H) => h.startReply(passage.id, passage.id), "The stale-read fallback.", "It comes back when this reply has saved", "Save or clear this reply first", null],
  ["a coarse pointer", "a new comment", (h: H) => h.click('[data-act="fcfile"]'), "Cite the p99 too.", "It comes back when this comment has saved", "Save or clear this comment first", true],
] as Array<[string, string, (h: H) => void, string, string, string, boolean | null]>) {
  test("on " + pointer + ", " + name + " whose own save is refused with a refused comment's note under it: Bring it back's reason turns at once to saving or clearing the box, with no keystroke", async () => {
    coarse = touch;
    try {
      const h = await harness();
      await h.open();
      const first = await heldSave(h);
      start(h);
      draft(h.box(), words, words.length, 20);
      await refused(first);
      assert.ok(heldNote(h), "the precondition: the refused comment waits in a note under it");
      h.click('[data-act="fcsave"]');
      await tick(); await tick();
      const m = h.last();
      assert.equal(bringBack(h).title, saving, "the precondition: while its own save is out, the reason says when the comment comes back");
      await answer({ type: "fileCommentsFailed", reqId: m.reqId, verb: m.verb, code: "failed", error: REFUSAL });
      assert.equal(h.box().value, words, "the precondition: its save refused, it stays open with its words");
      assert.equal(bringBack(h).disabled, true, "Bring it back still waits: the box holds the words");
      assert.equal(bringBack(h).title, reason, "…and its reason is to save or clear them now, at the refusal, with no keystroke");
      if (touch) {
        const line = h.composer().querySelector(".fc-held-why");
        assert.ok(line && !line.hidden, "the reason's line under the note shows");
        assert.equal(line!.textContent, reason + ".", "…in the title's words");
      }
      h.dispose();
    } finally { coarse = null; }
  });
}

test("a refused comment's note under a region drawn and typed in: Bring it back says to save or cancel the region whether or not words are typed, since clearing the box leaves the rectangle holding it; a pending Re-place's reason is its own, words or not", async () => {
  const REGION_WHY = "Save or Cancel this comment first";
  const h = await harness({}, FIG);
  await h.open(FIG_STATUS);
  const reqId = await heldSave(h);
  h.drag(overlayOf(h), [150, 240], [250, 300]);
  draft(h.box(), "The axis starts at zero.", 24, 20);
  await refused(reqId);
  assert.ok(heldNote(h), "the precondition: the refused comment waits in a note under the region");
  assert.equal(bringBack(h).disabled, true, "Bring it back waits: it would replace the region");
  assert.equal(bringBack(h).title, REGION_WHY, "words typed in the region's box: the reason names Save or Cancel, not clearing the box, which would leave the rectangle");
  draft(h.box(), "", 0, 20);
  assert.equal(bringBack(h).disabled, true, "the box cleared: Bring it back still waits, on the rectangle");
  assert.equal(bringBack(h).title, REGION_WHY, "…with the same reason");
  draft(h.box(), "x", 1, 20);
  assert.equal(bringBack(h).title, REGION_WHY, "a word typed again: the same reason still");
  h.dispose();
  const g = await harness({}, FIG);
  await g.open(FIG_STATUS);
  const again = await heldSave(g);
  g.click('[data-act="fcfile"]');                      // a new comment under the save, words typed, then Re-place: the words carry, hidden
  draft(g.box(), "Cite the p99 too.", 17, 20);
  g.click('.fc-card[data-id="' + figRegion.id + '"] .fc-card-head');
  g.click('.fc-card[data-id="' + figRegion.id + '"] [data-act="fcreplace"]');
  await refused(again);
  assert.ok(heldNote(g), "the precondition: the refused comment waits in a note under the Re-place");
  assert.equal(bringBack(g).title, "Draw the new place or Cancel the re-place first", "a pending Re-place over words an earlier composer left: its reason is the Re-place's, which has no Save and no box of its own");
  g.dispose();
});

test("a change is named by what it did: the verb outside the quote marks and the change's words inside, each bounded as the change card bounds it", async () => {
  const fc = await import("./file-comments");
  assert.equal(fc.changeByDeed({ kind: "del", oldText: " still", newText: "" }), "the change that removed “still”", "a deletion: what it removed");
  assert.equal(fc.changeByDeed({ kind: "ins", oldText: "", newText: "  said so\nplainly  " }), "the change that added “said so plainly”", "on one line, the blank ends gone");
  assert.equal(fc.changeByDeed({ kind: "ins", oldText: "", newText: LONG }), "the change that added “once the fallback path has been measured again under the fu…”", "cut to 60 characters, as the card cuts it");
  assert.equal(fc.changeByDeed({ kind: "sub", oldText: "Hazards", newText: "Risks" }), "the change that replaced “Hazards” with “Risks”", "a replacement: both texts, each in its own quote marks");
  assert.equal(fc.changeByDeed({ kind: "sub", oldText: "The api session reduced p95 latency by forty percent", newText: "cut" }), "the change that replaced “The api session reduced p95 l…” with “cut”", "each side cut to 30 characters");
});

// ── words a Re-place's drag leaves in the hidden box are the person's (boxHoldsTyped) ─────────────────────
/** Re-place on the figure's region comment (its card opened first), and the drag that places it. */
const rePlace = (h: H): void => { h.click('.fc-card[data-id="' + figRegion.id + '"] .fc-card-head'); h.click('.fc-card[data-id="' + figRegion.id + '"] [data-act="fcreplace"]'); };
async function placeDrag(h: H): Promise<void> {
  h.drag(overlayOf(h), [110, 210], [190, 260]);
  await tick();
  assert.equal(h.last().verb, "retarget", "the precondition: the drag placed the region");
}
for (const [name, start, words] of [
  ["Comment on this file", (h: H) => h.click('[data-act="fcfile"]'), "Cite the p99 too."],
  ["a reply", (h: H) => h.startReply(figPassage.id, figPassage.id), "The stale-read fallback."],
] as Array<[string, (h: H) => void, string]>) {
  test("a refusal after a Re-place's drag, the words typed in " + name + " opened under the save still in the hidden box: they stay, shown as a comment on the file, and the refused comment waits in a note under them", async () => {
    const h = await harness({}, FIG);
    await h.open(FIG_STATUS);
    const reqId = await heldSave(h);
    start(h);
    draft(h.box(), words, words.length, 20);
    rePlace(h);
    await placeDrag(h);
    assert.equal(h.composer().hidden, true, "the precondition: the drag ended the Re-place with no composer open, the words hidden in the box");
    await refused(reqId);
    assert.equal(h.composer().hidden, false, "the refusal: the words typed are in view");
    assert.deepEqual(h.sections(), SLOT, "…in the panel's slot");
    assert.equal(h.box().hidden, false, "…in a box that shows");
    assert.equal(h.box().value, words, "…the words typed, as they were: the refused comment's words are not written over them");
    assert.deepEqual(h.row(), ["fc-note:On this file"], name === "a reply"
      ? "…as a comment on the file, not as the reply they were typed for: the reply's composer ended at the Re-place, and the refusal opens words carried from a reply through a Re-place's drag as a comment on the file, an edge disclosed with the user's decision of 2026-09-24, not a comment acted on in error"
      : "…as a comment on the file, which Save files and Cancel drops");
    const note = heldNote(h);
    assert.ok(note, "the refused comment waits in a note under them");
    assert.equal(note!.querySelector(".fc-note")!.textContent, "Your comment on this file was not saved:", "…naming what it was on");
    assert.equal(note!.querySelector(".fc-held-words")?.textContent, FIRST, "…with its words whole");
    assert.equal(bringBack(h).disabled, true, "…and its Bring it back waits on the words typed");
    assert.equal(bringBack(h).title, "Save or clear this comment first", "…saying why, in a comment's terms");
    assert.deepEqual(slotRows(h), [], "the refusal's row is not under the words typed, which it does not belong to");
    h.dispose();
  });
}

test("a Re-place's drag with words typed in a composer opened under a save, then that save lands: the words stay hidden where the drag left them, nothing opens for them, and the next composer shows them", async () => {
  const h = await harness({}, FIG);
  await h.open(FIG_STATUS);
  const reqId = await heldSave(h);
  h.click('[data-act="fcfile"]');
  draft(h.box(), "Cite the p99 too.", 17, 20);
  rePlace(h);
  await placeDrag(h);
  assert.equal(h.composer().hidden, true, "the drag with no refusal waiting: nothing opens for the words, which stay where the drag left them");
  await answer({ type: "fileCommentsResult", reqId, ...status(FIG_AFTER) });
  assert.equal(h.composer().hidden, true, "the save landed: still nothing opens, the landing moves nothing");
  h.click('[data-act="fcfile"]');
  assert.equal(h.box().value, "Cite the p99 too.", "the next composer shows the words typed, carried to it as a box's words always are");
  h.dispose();
});

test("with no save out, words typed, then a Re-place and its drag: the words stay in the box with no composer open, and Comment on this file opens with them", async () => {
  const h = await harness({}, FIG);
  await h.open(FIG_STATUS);
  h.click('[data-act="fcfile"]');
  draft(h.box(), "Lead with the p95.", 18, 20);
  rePlace(h);
  await placeDrag(h);
  assert.equal(h.composer().hidden, true, "the precondition: the drag ended the Re-place, no composer open");
  h.click('[data-act="fcfile"]');
  assert.equal(h.box().value, "Lead with the p95.", "no save out: the words carry from the box the drag left into Comment on this file, as a box's words always carry");
  h.dispose();
});

test("the viewer's close asks about words a Re-place hides, typed in a composer opened while a save was out: behind the pending Re-place and after its drag, named as the words typed, with the way to see them", async () => {
  type Ask = { question: string; kept: string };
  const asks: Array<() => Ask | null> = [];
  const h = await harness({ guardClose: (a) => { asks.push(a); } }, FIG);
  await h.open(FIG_STATUS);
  const put = () => asks.map((a) => a()).filter((q): q is Ask => q !== null);
  await heldSave(h);
  h.click('[data-act="fcfile"]');
  draft(h.box(), "Cite the p99 too.", 17, 20);
  rePlace(h);
  const OUT = " A comment on report.md is still saving; if it is not saved, its words are lost too.";
  assert.deepEqual(put(), [{ question: "Discard the unsaved words typed on report.md?" + OUT,
    kept: "This file stays open: the words typed on report.md before the re-place are not saved, and a comment on report.md is still saving. When that save has finished, draw the new place and open Comment on this file: the words are in its box. Save them or clear the box, then try again." }],
    "a save out, words typed, then a Re-place: the close names the words it hides as well as the save, and says how to see them");
  await placeDrag(h);
  assert.deepEqual(put(), [{ question: "Discard the unsaved words typed on report.md?" + OUT,
    kept: "This file stays open: the words typed on report.md are not saved, and a comment on report.md is still saving. When that save has finished, open Comment on this file: the words are in its box. Save them or clear the box, then try again." }],
    "…and after its drag, no composer open and the words hidden in the box: named the same, with the way to them from there");
  h.click('[data-act="fcfile"]');
  assert.equal(h.box().value, "Cite the p99 too.", "the way the kept text gives: Comment on this file shows the words");
  h.dispose();
});

test("with no save out, the viewer's close asks about words a Re-place hides, behind the pending Re-place and after its drag, where it asked nothing before", async () => {
  type Ask = { question: string; kept: string };
  const asks: Array<() => Ask | null> = [];
  const h = await harness({ guardClose: (a) => { asks.push(a); } }, FIG);
  await h.open(FIG_STATUS);
  const put = () => asks.map((a) => a()).filter((q): q is Ask => q !== null);
  h.click('[data-act="fcfile"]');
  draft(h.box(), "Lead with the p95.", 18, 20);
  rePlace(h);
  assert.deepEqual(put(), [{ question: "Discard the unsaved words typed on report.md?",
    kept: "This file stays open: the words typed on report.md before the re-place are not saved. Draw the new place and open Comment on this file: the words are in its box. Save them or clear the box, then try again." }],
    "words typed, then a Re-place: the close names the words it hides, and says how to see them");
  await placeDrag(h);
  assert.deepEqual(put(), [{ question: "Discard the unsaved words typed on report.md?",
    kept: "This file stays open: the words typed on report.md are not saved. Open Comment on this file: the words are in its box. Save them or clear the box, then try again." }],
    "…and after its drag, no composer open and the words hidden in the box: the close names them, with the way to them from there");
  h.click('[data-act="fcfile"]');
  assert.equal(h.box().value, "Lead with the p95.", "the way the kept text gives: Comment on this file shows the words");
  assert.deepEqual(put(), [{ question: "Discard the unsaved comment on report.md?", kept: "This file stays open: the comment typed on report.md is not saved. Save it, or clear the box, then try again." }],
    "…where the ask is the typed comment's, as on main");
  h.dispose();
});

// ── the keyboard stays on the control it was on ──────────────────────────────────────────────────────
/** Enter on a focused button: its click. */
const press = (): void => { (doc.activeElement as E).dispatch("click"); };
/** Two refused comments waiting in notes under a comment typed in, the first a comment and the second a reply. */
async function twoNotes(): Promise<H> {
  const h = await harness();
  await h.open();
  const first = await heldSave(h);
  h.startReply(passage.id, passage.id);
  draft(h.box(), "The stale-read fallback.", 24, 20);
  await refused(first);
  h.click('[data-act="fcsave"]');
  await tick(); await tick();
  const second = h.last();
  assert.equal(second.verb, "reply", "the precondition: the reply's write is out");
  h.click('[data-act="fcfile"]');
  draft(h.box(), "Cite the p99 too.", 17, 20);
  await answer({ type: "fileCommentsFailed", reqId: second.reqId, verb: "reply", code: "failed", error: REFUSAL });
  assert.equal(h.composer().querySelectorAll(".fc-held-save").length, 2, "the precondition: two refused comments wait in notes, a comment and then a reply");
  return h;
}
const notesOf = (h: H): E[] => h.composer().querySelectorAll(".fc-held-save");

test("with two notes, the keyboard on the second note's dismiss stays on it through a re-render, and Enter dismisses that note, not the first; with the box empty, the same for its Bring it back, which brings back the second", async () => {
  const h = await twoNotes();
  const ids = notesOf(h).map((n) => n.querySelector('[data-act="fcheldx"]')!.dataset.held);
  notesOf(h)[1].querySelector('[data-act="fcheldx"]')!.focus();
  await h.repoll();
  assert.equal((doc.activeElement as E).dataset.act, "fcheldx", "a re-render keeps the keyboard on a note's dismiss");
  assert.equal((doc.activeElement as E).dataset.held, ids[1], "…the second note's, the one it was on, not the first note's");
  press();
  assert.deepEqual(notesOf(h).map((n) => n.querySelector('[data-act="fcheldx"]')!.dataset.held), [ids[0]], "Enter dismissed the second note, the one the keyboard was on: the first still waits");
  h.dispose();
  const g = await twoNotes();
  draft(g.box(), "", 0, 20);
  const back2 = notesOf(g)[1].querySelector('[data-act="fcheldback"]')!;
  assert.equal(back2.disabled, false, "the precondition: the box emptied, Bring it back acts");
  const held2 = back2.dataset.held;
  back2.focus();
  await g.repoll();
  assert.equal((doc.activeElement as E).dataset.act, "fcheldback", "a re-render keeps the keyboard on a note's Bring it back");
  assert.equal((doc.activeElement as E).dataset.held, held2, "…the second note's, not the first note's");
  press();
  assert.equal(g.box().placeholder, "Your reply", "Enter brings back the second note's comment, the reply");
  assert.equal(g.box().value, "The stale-read fallback.", "…with its words");
  g.dispose();
});

for (const [what, typed, settle] of [
  ["lands", "", (reqId: number) => landed(reqId)],
  ["is refused into a note", "Cite the p99 too.", (reqId: number) => refused(reqId)],
] as Array<[string, string, (reqId: number) => Promise<void>]>) {
  test("the keyboard on the open composer's Cancel stays there when another comment's save " + what, async () => {
    const h = await harness();
    await h.open();
    const reqId = await heldSave(h);
    h.click('[data-act="fcfile"]');
    if (typed) draft(h.box(), typed, typed.length, 20);
    h.q('[data-act="fccancel"]')!.focus();
    await settle(reqId);
    if (typed) assert.ok(heldNote(h), "the precondition: the refused comment waits in a note");
    assert.equal((doc.activeElement as E).dataset.act, "fccancel", "the other comment's save " + what + ": the keyboard stays on the open composer's Cancel");
    assert.ok(h.composer().contains(doc.activeElement as E), "…the Cancel in the open box");
    h.dispose();
  });
}

test("with two notes standing, a reply's save landing keeps the keyboard on the second note's dismiss, and shows that reply's saved line at the landing", async () => {
  const h = await twoNotes();
  // the words typed carry into a reply, whose save goes out; a new comment opens under it, the two notes with it
  h.startReply(passage.id, passage.id);
  assert.equal(h.box().value, "Cite the p99 too.", "the precondition: the words carried into the reply");
  h.click('[data-act="fcsave"]');
  await tick(); await tick();
  const m = h.last();
  assert.equal(m.verb, "reply", "the precondition: the reply's write is out");
  h.click('[data-act="fcfile"]');
  assert.equal(notesOf(h).length, 2, "the precondition: the two notes stand under the new comment");
  const x2 = notesOf(h)[1].querySelector('[data-act="fcheldx"]')!;
  x2.focus();
  cardRects.set(passage.id, rectOf(0, 900, 300, 60));   // the reply's card below the view: its landing raises the saved line
  try {
    const answered: StoreComment = { ...passage, replies: [...(passage.replies || []), { author: "you", ts: T0 + 9000, body: "Cite the p99 too." }] };
    await answer({ type: "fileCommentsResult", reqId: m.reqId, ...status({ store: { v: 3, path: "docs/report.md", suggestions: [], comments: [answered, whole] }, storeMtimeNs: "1757145600000000008" }) });
    const line = h.q('[data-act="fcsavedgo"]');
    // both read at the landing and asserted together, so the record shows each
    assert.deepEqual({ keyboard: (doc.activeElement as E).dataset.held === x2.dataset.held, savedLine: line ? line.textContent : null },
      { keyboard: true, savedLine: "Saved · the card is below" },
      "the reply landed: the keyboard stays on the second note's dismiss, and the reply's saved line shows now, not at the next render");
  } finally { cardRects.clear(); }
  h.dispose();
});

test("a note dismissed under a pending Re-place: the keyboard goes to the Re-place's Cancel, since the hidden box cannot take it", async () => {
  const h = await harness({}, FIG);
  await h.open(FIG_STATUS);
  const reqId = await heldSave(h);
  rePlace(h);
  await refused(reqId);
  assert.ok(heldNote(h), "the precondition: the refused comment waits in a note under the Re-place");
  assert.equal(h.box().hidden, true, "the precondition: the Re-place hides the box");
  const x = h.composer().querySelector('[data-act="fcheldx"]')!;
  x.focus();
  x.dispatch("click");
  assert.equal(heldNote(h), null, "the precondition: dismissed");
  assert.equal((doc.activeElement as E).dataset.act, "fccancel", "the keyboard, on the dismiss that went with its note, goes to the Re-place's Cancel: the hidden box cannot take it");
  h.dispose();
});

// ── Bring it back's reason names only buttons the composer shows ────────────────────────────────────
// a second figure the source holds no embed line for: a region on it has nothing to anchor to, and its Comment no passage
const FIG2 = { html: FIG_HTML + '<p><img src="chart.png" alt="Chart"></p>\n', src: FIG_SRC };
const overlay2 = (h: H): E => { const o = h.body.querySelectorAll(".fileview-md .fc-overlay"); assert.equal(o.length, 2, "the two figures' overlays"); return o[1]; };
const NO_HX: Partial<Status> = { ...FIG_STATUS, store: { v: 3, path: "docs/report.md", suggestions: [hR, hL].map(sugg), comments: [figRegion, figPassage] }, hunks: [hR, hL], storeMtimeNs: "1757145600000000009" };
for (const [name, fig, open, words, gone, reason] of [
  ["a region drawn on a figure with no embed line", FIG2, (h: H) => { h.drag(overlay2(h), [150, 240], [250, 300]); }, "", false, "Cancel this comment first"],
  ["a comment typed on a figure with no embed line, its passage refused as it opened", FIG2, (h: H) => {
    const o = overlay2(h);
    o.dispatch("pointerdown", { clientX: 150, clientY: 240, pointerId: 8, button: 0 });
    o.dispatch("pointerup", { clientX: 150, clientY: 240, pointerId: 8 });
    h.float().dispatch("click");
  }, "Which run is this?", false, "Clear or Cancel this comment first"],
  ["a comment typed about a change that has gone since", FIG, (h: H) => h.click('[data-act="fcchangecomment"][data-id="hX"]'), "Say why it went.", true, "Clear or Cancel this comment first"],
] as Array<[string, { html: string; src: string }, (h: H) => void, string, boolean, string]>) {
  test("a refused comment's note under " + name + ", which shows no Save: Bring it back's reason names only what frees it, in its title and, on a coarse pointer, in its line", async () => {
    try {
      const h = await harness({}, fig);
      await h.open(FIG_STATUS);
      const reqId = await heldSave(h);
      open(h);
      if (words) draft(h.box(), words, words.length, 20);
      // the pointer a finger from here on: a figure takes a drag or a Comment from a fine pointer only (paintRegions arms its
      // overlay then), so the finger comes after, as on a laptop's touch screen, and the note is rendered for it
      coarse = true;
      await refused(reqId);
      if (gone) await h.repoll(NO_HX);
      assert.ok(heldNote(h), "the precondition: the refused comment waits in a note under it");
      assert.equal(h.q('[data-act="fcsave"]'), null, "the precondition: the composer shows no Save");
      assert.equal(bringBack(h).disabled, true, "Bring it back waits");
      assert.equal(bringBack(h).title, reason, "…and its reason names only buttons on screen, no Save");
      const line = heldNote(h)!.querySelector(".fc-held-why");
      assert.ok(line && !line.hidden, "…and on a coarse pointer the line in the note shows");
      assert.equal(line!.textContent, reason + ".", "…in the title's words");
      h.dispose();
    } finally { coarse = null; }
  });
}

// ── each note's reason is true for that note ─────────────────────────────────────────────────────────
for (const [pointer, touch] of [["a fine pointer", null], ["a coarse pointer", true]] as Array<[string, boolean | null]>) {
  test("on " + pointer + ", two notes under a composer whose own save is out: the first says it comes back when that save has saved, the other that it waits its turn behind the one above; the landing brings back the first, and the other's reason is at once the words of the comment now open", async () => {
    coarse = touch;
    try {
      const g = await twoNotes();
      g.click('[data-act="fcsave"]');
      await tick(); await tick();
      const third = g.last();
      assert.equal(third.args.note, "Cite the p99 too.", "the precondition: the new comment's own save is out");
      // each note's title, and on a coarse pointer the lines in order under the box (where the line stands is the test above's)
      const lines = () => g.composer().querySelectorAll(".fc-held-why").map((l) => l.textContent);
      const whys = () => notesOf(g).map((n, i) => ({ title: n.querySelector('[data-act="fcheldback"]')!.title, line: touch ? lines()[i] ?? null : null }));
      const dot = (s: string) => (touch ? s + "." : null);
      assert.deepEqual(whys(), [
        { title: "It comes back when this comment has saved", line: dot("It comes back when this comment has saved") },
        { title: "It waits its turn behind the one above", line: dot("It waits its turn behind the one above") },
      ], "during the save each note says what is true for it: the landing brings back the first alone");
      await answer({ type: "fileCommentsResult", reqId: third.reqId, ...status(AFTER) });
      assert.equal(g.box().value, FIRST, "the new comment's save landed: the first refused comment comes back");
      assert.equal(notesOf(g).length, 1, "…and the reply still waits in its note");
      assert.equal(bringBack(g).title, "Save or clear this comment first", "…whose reason is at once the words of the comment now open");
      g.dispose();
    } finally { coarse = null; }
  });
}

// ── a comment about a change that has gone: named by that state, never by its id ─────────────────────
const GONE_LABEL = "Your comment about a change that is no longer pending was not saved:";
test("a refused comment about a change that went while its save was out is named in its note as a change no longer pending, never by the change's id", async () => {
  const h = await harness({}, FIG);
  await h.open(FIG_STATUS);
  const m = await heldFrom(h, (x) => x.click('[data-act="fcchangecomment"][data-id="hX"]'), "Say why it went.");
  h.click('[data-act="fcfile"]');
  draft(h.box(), "Lead with the numbers.", 22, 20);
  await h.repoll(NO_HX);                               // the change decided while the save was out
  await refuseWrite(m);
  const label = heldNote(h)!.querySelector(".fc-note")!.textContent;
  assert.equal(label, GONE_LABEL, "the note names the change by its state, in the panel's words for it");
  assert.doesNotMatch(label, /hX/, "…and never by its id");
  h.dispose();
});

test("a refused comment about a change waits in its note named by what the change did; when the change goes, the same note names it as no longer pending, and brought back it shows the change gone, never its id", async () => {
  const h = await harness({}, FIG);
  await h.open(FIG_STATUS);
  const m = await heldFrom(h, (x) => x.click('[data-act="fcchangecomment"][data-id="hX"]'), "Say why it went.");
  h.click('[data-act="fcfile"]');
  draft(h.box(), "Lead with the numbers.", 22, 20);
  await refuseWrite(m);
  const label = () => heldNote(h)!.querySelector(".fc-note")!.textContent;
  assert.equal(label(), "Your comment about the change that removed “still” was not saved:", "the precondition: the note names the change by what it did");
  await h.repoll(NO_HX);                               // the change decided while the note stands
  assert.equal(label(), GONE_LABEL, "the change gone: the same note names it by its state");
  assert.doesNotMatch(label(), /hX/, "…never by its id");
  draft(h.box(), "", 0, 20);
  bringBack(h).dispatch("click");
  await tick();
  assert.equal(h.box().value, "Say why it went.", "the precondition: brought back with its words");
  const row = h.row();
  assert.equal(row[0], "fc-note fc-refused:The change this comment was about is no longer pending: it was accepted or rejected, or the session's next edit took it into a new one.",
    "brought back, the composer says at once that its change is gone, as any open composer does at the next status");
  assert.doesNotMatch(row.join(" | "), /hX/, "…and shows no id: " + row.join(" | "));
  assert.equal(h.q('[data-act="fcsave"]'), null, "…with no Save that would post the gone change's id");
  h.dispose();
});
