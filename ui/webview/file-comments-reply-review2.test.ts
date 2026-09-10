// The reply's box in its card, after the second review of that change (plans/file-review.md, "The composer follow-on
// (2026-09-07)", its closing sentence). What the review found, each pinned here by the behaviour it asked for:
//   • Save inside the card of a comment whose id holds a quote: the busy render's refocus (focusNear) built its selector from
//     the raw id, querySelector threw out of render() before mutate's try, and the reply was never posted while Save read
//     "Saving…" for good. The selector takes the id escaped (cssId), as placeComposer's and closeComposer's already did.
//   • Comment on this file, a picture's Comment, a selection's Comment or a region drawn over a reply left the card's head
//     saying it would not fold (holdHead: aria-disabled, a title) while a click on it already folded the card; the kind
//     change renders the cards too (renderFrom), as Cancel did.
//   • The slot's row names what hides the card, and only that (replyAway): the Resolved fold for a resolved comment, the
//     Changes filter otherwise. Before the about follow-on (2026-09-10) a resolved comment bound to a change was shown on the
//     change card, never under Resolved, and the review found the row naming a Resolved fold the list did not render for one
//     behind "… N more changes"; every comment is its own card now, so no comment is behind the changes fold.
//   • Escape or Cancel with the box in the slot found no Reply to hand the keyboard to and left it on the hidden box (the
//     body, in a browser); it goes to the fold row the slot's line names, or to the nearest control (focusAway).
//   • The textarea's scroll offset across the box's move was pinned at source only; here the stand-in's detach zeroes a
//     node's scroll offset, as a browser does (the browser leg is file-comments-reply-review2-browser.test.ts).
//   • graft's copy of the twin's class onto the kept card had no test: the card turning detached under the box.
//   • The held head explained itself in a title alone, which never reaches touch: on a coarse pointer the words stand
//     under the head as a line (heldNote).
// The DOM stand-in is the reply-keep test's, with a stricter selector parser (a selector a browser would refuse throws
// here too, so the raw-id path fails the way it failed there) and a scroll offset that a detach zeroes. Synthetic
// fixtures only: the notes-api world, placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inspect } from "node:util";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx, TrackedEdit } from "./file-view";
import type { Status, StoreComment, Hunk } from "./file-comments-model";
import { hideEdges, staysEnumerable } from "../test-dom-shim";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const SRC = web("file-comments.ts");

// ── the DOM stand-in ───────────────────────────────────────────────────────────────────────────────
class Doc {
  body: E;
  hidden = false;
  activeElement: E | null = null;
  scrolled: E[] = [];                                  // every scrollIntoView, in order
  detached: N[] = [];                                  // every node taken out of its parent, in order (a rebuild's detaches)
  focused: E[] = [];                                   // every focus() that landed, in order
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
type Init = { key?: string; ctrlKey?: boolean; metaKey?: boolean; shiftKey?: boolean; isComposing?: boolean };
type Ev = Init & { type: string; target: N; currentTarget: N | null; defaultPrevented: boolean; preventDefault(): void; stopPropagation(): void };
const kebab = (k: string | symbol): string => String(k).replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
type Compound = { tag: string | null; classes: string[]; attrs: Array<[string, string | null]> };
/** A compound selector, piece by piece from its start; a piece the grammar does not take — an unescaped quote inside a
 *  quoted value, say — is a SyntaxError, as querySelector throws it in a browser. A value may hold \" or \\ (cssId). */
function parseSelector(sel: string): Compound[] {
  return sel.split(",").map((part) => {
    const s = part.trim();
    const out: Compound = { tag: null, classes: [], attrs: [] };
    const re = /([a-zA-Z][\w-]*)|\.([\w-]+)|\[([\w-]+)(?:="((?:[^"\\]|\\.)*)")?\]/y;
    while (re.lastIndex < s.length) {
      const m = re.exec(s);
      if (!m) throw new SyntaxError("'" + sel + "' is not a valid selector");
      if (m[1]) out.tag = m[1].toUpperCase();
      else if (m[2]) out.classes.push(m[2]);
      else out.attrs.push([m[3], m[4] === undefined ? null : m[4].replace(/\\(.)/g, "$1")]);
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
  // the layout a test gives a box: what the browser would measure at height: auto (autosizeComposer reads these)
  scrollHeight = 0; offsetHeight = 0; clientHeight = 0;
  scrollTop = 0;                                       // the box's scroll offset; a detach zeroes it (unscroll), as a browser's does
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
  /** A node leaves its parent: it and its descendants lose their scroll offset (a textarea out of the document, even to
   *  come straight back, scrolls back to its first line — the graft's reason, and the browser leg measures it), and if it
   *  held the focus (itself or a descendant), the focus fixup rule moves it to the body. */
  detach(n: N): void {
    const i = this.childNodes.indexOf(n); if (i >= 0) this.childNodes.splice(i, 1); n.parentNode = null;
    const doc = this.ownerDocument;
    doc.detached.push(n);
    if (n instanceof E) { n.unscroll(); if (doc.activeElement && n.contains(doc.activeElement)) doc.activeElement = doc.body; }
  }
  unscroll(): void { this.scrollTop = 0; for (const c of this.childNodes) if (c instanceof E) c.unscroll(); }
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
  getBoundingClientRect(): { left: number; top: number; right: number; bottom: number; width: number; height: number } {
    return this.tagName === "IMG" ? { left: 100, top: 200, right: 400, bottom: 400, width: 300, height: 200 } : { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 };
  }
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
win.getSelection = () => ({ isCollapsed: true, rangeCount: 0, toString: () => "" });
(globalThis as any).window = win;
(globalThis as any).document = doc;
(globalThis as any).fetch = async () => ({ status: 404, headers: { get: () => null }, json: async () => [] });
const realSetInterval = globalThis.setInterval;
(globalThis as any).setInterval = (fn: () => void, ms: number) => { const t = realSetInterval(fn, ms); (t as any).unref?.(); return t; };
const tick = () => new Promise<void>((r) => setImmediate(r));
/** The pointer the panel sees (isCoarsePointer reads window.matchMedia): a finger, or none — the fine pointer, and what a
 *  stand-in without matchMedia answers. */
const pointer = (coarse: boolean | null): void => { if (coarse === null) delete win.matchMedia; else win.matchMedia = () => ({ matches: coarse }); };

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const T0 = 1757145600000;
const DOC = "# Report\n\n## Findings\nThe api session cut p95 latency by 40% and the p99 by 10%.\n\n"
  + "We recommend shipping the cache in v1.2.\n\nRisks remain in the fallback path.\n\nNext steps: measure again.\n";
const passage: StoreComment = {
  id: T0 + "-118", author: "you", ts: T0, body: "Which cache? Say which.",
  anchor: { quote: "shipping the cache in v1.2", prefix: "We recommend ", suffix: "." },
  replies: [{ author: "api", authorId: SID, ts: T0 + 1000, body: "The response cache." }, { author: "you", ts: T0 + 2000, body: "Say so in the text." }],
  resolved: false,
};
const whole: StoreComment = { id: T0 + "-119", author: "you", ts: T0 + 4000, body: "Lead with the numbers.", replies: [], resolved: false };
const odd: StoreComment = { ...whole, id: T0 + '-7"x', ts: T0 + 5000, body: "Quote the p99." };   // an id a hand wrote
const cut = DOC.indexOf("cut");
const h1: Hunk = { id: "h1", author: "api", ts: T0 - 90000, kind: "sub", curFrom: cut, curTo: cut + 3, baseFrom: cut, baseTo: cut + 7, oldText: "reduced", newText: "cut", anchor: null };
const SUGG = [{ id: "h1", author: "api", authorId: SID, ts: T0 - 90000, kind: "sub", from: cut, oldText: "reduced", newText: "cut" }];
const bound: StoreComment = { id: T0 + 1000 + "-5", author: "you", ts: T0 + 1000, body: "Say cut, not reduced.", suggestionId: "h1",
  replies: [{ author: "api", authorId: SID, ts: T0 + 3000, body: "Done." }], resolved: false };
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
const WITH_ODD: Partial<Status> = { store: { v: 3, path: "docs/report.md", suggestions: [], comments: [passage, whole, odd] }, unsent: unsent(passage.id, whole.id, odd.id) };
const WITH_CHANGE: Partial<Status> = { store: { v: 3, path: "docs/report.md", suggestions: SUGG, comments: [passage, bound] }, hunks: [h1], unsent: unsent(passage.id, bound.id) };
/** The passage comment gone from the sidecar. */
const GONE: Partial<Status> = { store: { v: 3, path: "docs/report.md", suggestions: [], comments: [whole] }, unsent: unsent(whole.id), storeMtimeNs: "1757145600000000005" };
/** The passage comment resolved. */
const RESOLVED: Partial<Status> = { store: { v: 3, path: "docs/report.md", suggestions: [], comments: [{ ...passage, resolved: true }, whole] }, unsent: unsent(whole.id), storeMtimeNs: "1757145600000000005" };
// four paragraphs with a change each (GROUP_LIMIT is 3), a comment bound to the last one
const sub = (id: string, word: string, was: string, ts: number): Hunk => {
  const at = DOC.indexOf(word);
  return { id, author: "api", ts, kind: "sub", curFrom: at, curTo: at + word.length, baseFrom: at, baseTo: at + was.length, oldText: was, newText: word, anchor: null };
};
const sugg = (x: Hunk) => ({ id: x.id, author: x.author, authorId: SID, ts: x.ts, kind: x.kind, from: x.curFrom, oldText: x.oldText, newText: x.newText });
const hA = sub("hA", "cut", "reduced", T0 - 90000), hB = sub("hB", "shipping", "releasing", T0 - 80000);
const hC = sub("hC", "Risks", "Hazards", T0 - 70000), hD = sub("hD", "measure", "check", T0 - 60000);
/** A RESOLVED comment the fourth paragraph's change answered: under the Resolved fold like any resolved comment (the about
 *  follow-on, 2026-09-10; before it, shown on the change card all the same), and not counted on the change's card
 *  (commentsAbout counts the open ones). */
const onD: StoreComment = { id: T0 + 2000 + "-9", author: "you", ts: T0 + 2000, body: "Measure what, exactly?", suggestionId: "hD", replies: [], resolved: true };
const THREE: Partial<Status> = { store: { v: 3, path: "docs/report.md", suggestions: [hB, hC, hD].map(sugg), comments: [whole, onD] }, hunks: [hB, hC, hD], unsent: unsent(whole.id) };
const FOUR: Partial<Status> = { store: { v: 3, path: "docs/report.md", suggestions: [hA, hB, hC, hD].map(sugg), comments: [whole, onD] }, hunks: [hA, hB, hC, hD], unsent: unsent(whole.id), storeMtimeNs: "1757145600000000011" };
const CHANGES_LINE = "fc-note:The comment's card is hidden while Changes is chosen above (All or Comments shows it); the reply still goes to it.";
const HOLD = "The card stays open while its reply is written; Save or Cancel the reply first";

// ── the harness: a mounted panel inside the viewer's body row ──────────────────────────────────────
type Posted = Record<string, any>;
const SLOT = ["fc-sec-head", "fc-composer", "fc-sec-cards", "fc-sec-send", "fc-sec-log"];   // the panel's sections with the box in its slot
const NO_SLOT = ["fc-sec-head", "fc-sec-cards", "fc-sec-send", "fc-sec-log"];              // …and with the box away in a card
async function harness(over: Partial<FileViewActionCtx> = {}) {
  const fc = await import("./file-comments");
  const main = doc.createElement("div"); main.className = "fileview-main";
  const body = doc.createElement("div"); body.className = "fileview-body"; main.appendChild(body);
  const posted: Posted[] = [];
  const tracked: Array<TrackedEdit | null> = [];
  const closers: Array<() => void> = [];
  const saved: Array<(info: { mtimeNs: string; logged: boolean }) => void> = [];
  const rendered: Array<() => void> = [];             // the viewer's repaint hooks (paintAll runs from them)
  let aside: E | null = null;
  const noop = () => { /* inert */ };
  const ctx: FileViewActionCtx = {
    path: ABS, sid: SID, todoId: null,
    body: () => body as unknown as HTMLElement, mode: () => "rendered", text: () => null,
    mtimeNs: () => "1757145600000000001", media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [], identity: () => ({ name: "api", color: null }),
    onRendered: (cb) => { rendered.push(cb); }, onSelection: noop, onSaved: (cb) => { saved.push(cb); }, onClose: (cb) => { closers.push(cb); },
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
    fc, main, body, posted, saved, rendered, last, kids,
    ok: (over: Partial<Status> = {}) => reply({ type: "fileCommentsResult", reqId: last().reqId, ...status(over) }),
    q: (sel: string) => main.querySelector(sel),
    click: (sel: string) => { const e = main.querySelector(sel); assert.ok(e, "a control " + sel); e!.dispatch("click"); },
    root: (): E => { const r = main.querySelector(".fc-panel"); assert.ok(r, "the panel"); return r!; },
    sections: (): string[] => kids(h.root()),
    box: (): E => { const b = main.querySelector("textarea.fc-input"); assert.ok(b, "the comment box is a textarea"); return b!; },
    composer: (): E => { const c = main.querySelector(".fc-composer"); assert.ok(c, "the composer box"); return c!; },
    card: (id: string): E | null => main.querySelector('.fc-card[data-id="' + id + '"]'),
    head: (key: string): E => { const e = main.querySelectorAll(".fc-card-head").find((x) => x.dataset.id === key); assert.ok(e, "the head of " + key); return e!; },
    replyBtn: (id: string): E | null => main.querySelectorAll('[data-act="fcreply"]').find((b) => b.dataset.id === id) || null,   // by the id as data: it may hold a quote
    cardBy: (id: string): E | null => main.querySelectorAll('.fc-card').find((c) => c.dataset.id === id) || null,
    /** The slot's reference row, class:text per span. */
    row: (): string[] => h.q('.fc-composer-ref')!.childNodes.map((n) => (n as E).className + ':' + n.textContent),
    /** The detaches since `mark` that took the textarea, or a node holding it, out of the document (read by length). */
    outOfDoc: (mark: number): N[] => doc.detached.slice(mark).filter((n) => n === h.box() || (n instanceof E && n.contains(h.box()))),
    key: (init: Init): Ev => h.box().dispatch("keydown", init),
    /** Open the panel on a status. */
    open: async (over: Partial<Status> = {}) => { await h.ok(over); button.dispatch("click"); await h.ok(over); },
    /** Expand a card (by its expand key) and press the Reply of a comment on it. */
    startReply: (key: string, id: string) => { if (!h.card(key)!.classList.contains("open")) h.click('.fc-card[data-id="' + key + '"] .fc-card-head'); h.click('[data-act="fcreply"][data-id="' + id + '"]'); },
    /** The poll's path: a save elsewhere re-asks status, and the reply rebuilds every section. */
    repoll: async (over: Partial<Status> = {}) => { saved[0]({ mtimeNs: "9", logged: true }); await tick(); assert.equal(last().verb, "status"); await h.ok(over); },
    dispose: () => { for (const cb of closers) cb(); },
  };
  return h;
}
/** Set the box's text with a caret and a measured height, as a person typing would leave it. */
function draft(box: E, text: string, caret: number, scrollHeight: number): void {
  box.value = text; box.setSelectionRange(caret, caret);
  box.scrollHeight = scrollHeight; box.offsetHeight = scrollHeight + 2; box.clientHeight = scrollHeight; box.dispatch("input");
}

// ── Save inside the card of a comment whose id holds a quote ──────────────────────────────────────

test("Save in the card of a comment whose id holds a quote: the busy render finds the keyboard in the card and refocuses by the escaped id — the reply posts, Save waits disabled, and the landing closes the box", async () => {
  const h = await harness();
  await h.open(WITH_ODD);
  h.cardBy(odd.id)!.querySelector(".fc-card-head")!.dispatch("click");
  h.replyBtn(odd.id)!.dispatch("click");
  const box = h.box();
  draft(box, "Yes.", 4, 42);
  // a click puts the keyboard on the button before the click lands (a mousedown; Tab reaches it the same way), so the busy
  // render's focusKey sees a control INSIDE the card and notes the card's id — the raw id used to go into a selector there
  const save = h.q('.fc-composer [data-act="fcsave"]')!;
  doc.activeElement = save;
  save.dispatch("click"); await tick();
  assert.equal(h.last().verb, "reply", "the reply went out: nothing threw out of the busy render");
  assert.deepEqual(h.last().args, { commentId: odd.id, note: "Yes." });
  const busy = h.q('.fc-composer [data-act="fcsave"]')!;
  assert.equal(busy.textContent, "Saving…"); assert.equal(busy.disabled, true, "Save waits, disabled, for the round trip");
  assert.equal(box.readOnly, true, "…and the box is read-only meanwhile");
  assert.ok(doc.activeElement === h.head(odd.id), "the keyboard went to the card's head, the nearest control (focusNear), not the body");
  // the reply lands: the box closes and frees; the turn is on the card
  const answered: StoreComment = { ...odd, replies: [{ author: "you", ts: T0 + 9000, body: "Yes." }] };
  await h.ok({ store: { v: 3, path: "docs/report.md", suggestions: [], comments: [passage, whole, answered] }, unsent: unsent(passage.id, whole.id), storeMtimeNs: "1757145600000000006" });
  assert.equal(h.composer().hidden, true, "saved: the composer closes");
  assert.equal(box.readOnly, false); assert.equal(box.value, "");
  assert.equal(h.cardBy(odd.id)!.querySelectorAll(".fc-reply").length, 1, "the new turn is on the card");
  assert.ok(doc.activeElement === h.head(odd.id), "the keyboard stays on the card");
  // a second Save is not swallowed by a stuck busy gate: Reply again, save by the chord
  h.replyBtn(odd.id)!.dispatch("click");
  draft(h.box(), "And the p95.", 12, 42);
  h.key({ key: "Enter", ctrlKey: true }); await tick();
  assert.equal(h.last().verb, "reply"); assert.equal(h.last().args.note, "And the p95.");
  h.dispose();
});

// ── the head is free the moment the composer stops being a reply ──────────────────────────────────

test("Comment on this file over a reply, and a picture's Comment: the head of the card that held the reply is free at once, and one click folds it", async () => {
  const MD = "# Report\n\n![the p99 chart](p99.png)\n\nWe recommend shipping the cache in v1.2.\n";
  const h = await harness({ text: () => MD });
  h.body.innerHTML = '<div class="fileview-md"><h1>Report</h1><p><img src="p99.png" alt="the p99 chart"></p></div>';
  await h.open();
  h.startReply(passage.id, passage.id);
  assert.equal(h.head(passage.id).getAttribute("aria-disabled"), "true", "held while the reply is written");
  assert.deepEqual(h.sections(), NO_SLOT);
  h.click('[data-act="fcfile"]');
  assert.deepEqual(h.sections(), SLOT, "a whole-file comment: the box is in the slot");
  assert.equal(h.head(passage.id).getAttribute("aria-disabled"), null, "the head is free at once, not at the next status");
  assert.equal(h.head(passage.id).title, "");
  assert.equal(h.head(passage.id).getAttribute("aria-expanded"), "true");
  h.click('.fc-card[data-id="' + passage.id + '"] .fc-card-head');
  assert.ok(!h.card(passage.id)!.classList.contains("open"), "one click folds it, as the head now says");
  assert.deepEqual(h.sections(), SLOT, "the fold did not take the box: it was in the slot");
  assert.equal(h.composer().hidden, false);
  // a picture's Comment (the float over a rendered figure) the same
  h.startReply(passage.id, passage.id);
  assert.equal(h.head(passage.id).getAttribute("aria-disabled"), "true");
  h.body.querySelector("img")!.dispatch("click");     // onImageClick: the float offers Comment beside the picture
  const float = doc.body.querySelector(".fc-float")!;
  assert.equal(float.hidden, false, "the float is up");
  float.dispatch("click");                             // startImageComment
  assert.deepEqual(h.sections(), SLOT);
  assert.match(h.q(".fc-composer-ref")!.textContent, /^On |not found/, "the picture's composer: its embed line, or the refusal");
  assert.equal(h.head(passage.id).getAttribute("aria-disabled"), null, "the head is free");
  assert.equal(h.head(passage.id).title, "");
  h.click('.fc-card[data-id="' + passage.id + '"] .fc-card-head');
  assert.ok(!h.card(passage.id)!.classList.contains("open"));
  h.dispose();
});

// ── the slot's row for a resolved comment a change answered ───────────────────────────────────────

test("a resolved comment answered by a change: its card is under the Resolved fold like any resolved comment's, and the change card counts it among no open comments; Reply from the open fold puts the box in that card, the changes fold moves nothing, and closing Resolved sends the box to the slot with the row naming Resolved", async () => {
  const h = await harness({ text: () => DOC, mode: () => "raw" });
  await h.open(FOUR);
  assert.ok(h.card("chg:hD") === null, "the fourth paragraph's change is behind the fold");
  assert.ok(h.card(onD.id) === null, "the resolved comment is under the closed Resolved fold");
  assert.equal(h.q('[data-act="fcresolved"]')!.textContent, "▸ Resolved (1)", "the fold is rendered for it");
  h.click('[data-act="fcmore"]');
  assert.ok(h.card("chg:hD"), "every change shown");
  assert.ok(h.card("chg:hD")!.querySelector(".fc-about-count") === null, "the change card counts open comments only: none for a resolved one");
  h.click('[data-act="fcresolved"]');
  assert.ok(h.card(onD.id), "the fold shows the comment's own card");
  assert.deepEqual(h.card(onD.id)!.querySelectorAll(".fc-card-head .fc-tag").map((t) => t.textContent), ["answered by a change", "resolved"], "the card names the change and its own state");
  h.startReply(onD.id, onD.id);                       // its render rebuilds the list (the box was in the slot): the card node is read after it
  const box = h.box(), card = h.card(onD.id);
  draft(box, "The p99.", 8, 42);
  assert.ok(card && card.contains(h.composer()), "the box stands in the comment's own card");
  h.click('[data-act="fcmore"]');                     // ▾ Fewer changes
  assert.ok(h.card("chg:hD") === null);
  assert.ok(h.card(onD.id) === card && card!.contains(h.composer()), "the changes fold hides the change card and nothing else");
  assert.deepEqual(h.sections(), NO_SLOT);
  h.click('[data-act="fcresolved"]');                 // the person closes Resolved
  assert.ok(h.card(onD.id) === null);
  assert.deepEqual(h.sections(), SLOT);
  assert.equal(h.row()[1], "fc-note:The comment's card is under “Resolved” below; the reply still goes to it.", "the row names the Resolved fold: the comment was resolved when the reply began");
  assert.equal(h.q('[data-act="fcmore"]')!.textContent, "… 1 more change");
  h.click('[data-act="fcresolved"]');
  assert.ok(h.card(onD.id)!.contains(h.composer()), "the named row brings the card and the box back");
  assert.equal(box.value, "The p99.");
  h.dispose();
  // the poll's way: the fourth change lands in the first paragraph while the reply is written; the comment's card is untouched
  const g = await harness({ text: () => DOC, mode: () => "raw" });
  await g.open(THREE);
  g.click('[data-act="fcresolved"]');
  g.startReply(onD.id, onD.id);
  draft(g.box(), "The p99.", 8, 42);
  await g.repoll(FOUR);
  assert.ok(g.card("chg:hD") === null, "pushed past the limit");
  assert.ok(g.card(onD.id)!.contains(g.composer()), "the box stays in the comment's card: nothing about the comment changed");
  assert.deepEqual(g.sections(), NO_SLOT);
  g.dispose();
});

// ── Escape or Cancel with the box in the slot ─────────────────────────────────────────────────────

test("Escape or Cancel with the box in the slot: the keyboard goes to the row that hides the card, the Resolved fold or the Changes filter's All, and with none, to the first card's head; never to the body", async () => {
  // the comment resolved meanwhile: its card is under the closed Resolved fold
  const h = await harness();
  await h.open();
  h.startReply(passage.id, passage.id);
  draft(h.box(), "One more thing.", 15, 42);
  await h.repoll(RESOLVED);
  assert.deepEqual(h.sections(), SLOT); assert.equal(h.card(passage.id), null); assert.ok(doc.activeElement === h.box());
  h.key({ key: "Escape" });
  assert.equal(h.composer().hidden, true, "cancelled");
  assert.equal(h.replyBtn(passage.id), null, "no Reply of the comment is rendered to hand the keyboard to");
  assert.ok(doc.activeElement === h.q('[data-act="fcresolved"]'), "Escape: the keyboard is on the Resolved fold, the row that brings the card back");
  h.click('[data-act="fcresolved"]');
  assert.ok(h.card(passage.id), "…and Enter there shows the card");
  h.dispose();
  // the comment's card hidden by the Changes filter: Cancel puts the keyboard on the filter group's first button, All (before
  // the about follow-on, 2026-09-10, this leg had the comment on its change card behind the changes fold, and the keyboard
  // went to the "… 1 more change" row)
  const g = await harness({ text: () => DOC, mode: () => "raw" });
  await g.open({ ...FOUR, store: { v: 3, path: "docs/report.md", suggestions: [hA, hB, hC, hD].map(sugg), comments: [whole, { ...onD, resolved: false }] } });
  g.startReply(onD.id, onD.id);
  draft(g.box(), "The p99.", 8, 42);
  g.click('[data-act="fcfilter"][data-key="changes"]');
  assert.deepEqual(g.sections(), SLOT); assert.equal(g.row()[1], CHANGES_LINE);
  g.click('[data-act="fccancel"]');
  assert.equal(g.composer().hidden, true);
  const back = doc.activeElement as E;
  assert.equal(back.dataset.act, "fcfilter", "Cancel: the keyboard is on the filter row that hides the card");
  assert.equal(back.dataset.key, "all", "…its first button, All, which shows the card again");
  g.dispose();
  // the comment gone from the sidecar: no fold hides its card, so the nearest control below the slot
  const k = await harness();
  await k.open();
  k.startReply(passage.id, passage.id);
  draft(k.box(), "Keep going.", 4, 42);
  await k.repoll(GONE);
  assert.deepEqual(k.sections(), SLOT); assert.match(k.row()[1], /gone from the file's comments/);
  k.key({ key: "Escape" });
  assert.equal(k.composer().hidden, true);
  assert.ok(doc.activeElement === k.head(whole.id), "Escape: the keyboard is on the first card's head");
  assert.ok(doc.activeElement !== doc.body && doc.activeElement !== k.box(), "never the body, never the hidden box");
  // a keyboard that was elsewhere is left alone, as ever
  k.startReply(whole.id, whole.id);
  await k.repoll({ store: { v: 3, path: "docs/report.md", suggestions: [], comments: [] }, unsent: unsent(), storeMtimeNs: "1757145600000000007" });
  assert.deepEqual(k.sections(), SLOT);
  doc.activeElement = doc.body;
  k.click('[data-act="fccancel"]');
  assert.ok(doc.activeElement === doc.body, "not ours to move");
  k.dispose();
});

// ── the scroll offset across the box's move ───────────────────────────────────────────────────────

test("the textarea's scroll offset survives the box's move to the slot and back: the move zeroes it, render puts it back", async () => {
  const h = await harness();
  await h.open();
  h.startReply(passage.id, passage.id);
  const box = h.box();
  draft(box, Array.from({ length: 16 }, (_, i) => "line " + (i + 1)).join("\n"), 120, 300);
  box.scrollTop = 56;                                  // scrolled to the caret, past the twelve-row cap
  const mark = doc.detached.length;
  await h.repoll(GONE);
  assert.deepEqual(h.sections(), SLOT, "the box moved to the slot");
  assert.ok(h.outOfDoc(mark).length > 0, "…which took the textarea out of the document on the way (the stand-in zeroes its offset then)");
  assert.equal(box.scrollTop, 56, "the scroll offset is back where the person had it");
  assert.ok(doc.activeElement === box, "and so is the keyboard");
  await h.repoll({ storeMtimeNs: "1757145600000000007" });   // the comment is back
  assert.ok(h.card(passage.id)!.contains(h.composer()), "the box returned to the card");
  assert.equal(box.scrollTop, 56, "the offset survived the return too");
  h.dispose();
});

// ── graft: the kept card wears the fresh render's class ───────────────────────────────────────────

test("the session rewrites the passage under an open reply: the repaint's locate loop marks the comment detached, and the kept card node wears the fresh render's detached dress and tag", async () => {
  let txt: string | null = null, md: "rendered" | "raw" = "rendered";
  const h = await harness({ text: () => txt, mode: () => md });
  await h.open();
  h.startReply(passage.id, passage.id);
  const box = h.box(), card = h.card(passage.id)!;
  draft(box, "Which one, then?", 16, 42);
  assert.equal(card.className, "fc-card open");
  // the Raw view shows a text that no longer holds the passage or its context; the viewer's repaint hook runs paintAll
  txt = DOC.replace("We recommend shipping the cache in v1.2.\n\n", "");
  md = "raw";
  const code = doc.createElement("code"); code.className = "hljs"; code.textContent = txt; h.body.appendChild(code);
  assert.equal(h.rendered.length, 1, "the panel registered its repaint hook");
  h.rendered[0]();
  assert.ok(h.card(passage.id) === card, "the same card node, kept around the box");
  assert.equal(card.className, "fc-card open fc-card-detached", "…wearing the fresh render's class: the detached dress");
  assert.ok(card.querySelectorAll(".fc-tag").some((t) => t.textContent === "detached"), "and the head's detached tag");
  assert.ok(card.contains(h.composer()), "the box is still in it");
  assert.ok(doc.activeElement === box); assert.equal(box.value, "Which one, then?");
  h.dispose();
});

// ── the held head's words, where the title cannot reach ───────────────────────────────────────────

test("on a coarse pointer the held head's words stand under it as a line on the comment's card (a change card never holds a reply, so never the line); a fine pointer keeps the title alone", async () => {
  pointer(true);
  try {
    const h = await harness();
    await h.open(WITH_CHANGE);
    h.startReply(passage.id, passage.id);
    const card = h.card(passage.id)!;
    assert.deepEqual(h.kids(card), ["fc-card-head", "fc-note fc-held", "fc-body fc-clip", "fc-replies fc-clip", "fc-clip-row", "fc-composer fc-composer-in", "fc-actions"], "the line under the head");
    assert.equal(card.querySelector(".fc-held")!.textContent, HOLD + ".");
    assert.equal(h.head(passage.id).title, HOLD, "the same words as the title");
    h.click('.fc-card[data-id="' + passage.id + '"] .fc-card-head');   // a tap: the card stays, the words are there to read
    assert.ok(h.card(passage.id)!.classList.contains("open")); assert.ok(h.card(passage.id)!.querySelector(".fc-held"));
    h.click('[data-act="fccancel"]');
    assert.ok(h.card(passage.id)!.querySelector(".fc-held") === null, "Cancel: the line goes with the reply");
    assert.ok(h.card("chg:h1")!.querySelector(".fc-held") === null, "no other card wears it");
    // a reply on the comment the change answered: the line stands in the comment's own card, never in the change card (no
    // reply's box stands in one since the about follow-on, 2026-09-10)
    h.startReply(bound.id, bound.id);
    assert.deepEqual(h.kids(h.card(bound.id)!).slice(0, 2), ["fc-card-head", "fc-note fc-held"], "the comment's card: the line under its head");
    assert.ok(h.card("chg:h1")!.querySelector(".fc-held") === null, "the change card wears no line");
    assert.equal(h.head("chg:h1").getAttribute("aria-disabled"), null, "…and its head is not held");
    h.key({ key: "Escape" });
    assert.ok(h.card(bound.id)!.querySelector(".fc-held") === null);
    h.dispose();
  } finally { pointer(null); }
  const g = await harness();
  await g.open();
  g.startReply(passage.id, passage.id);
  assert.ok(g.card(passage.id)!.querySelector(".fc-held") === null, "a fine pointer: no line, the card keeps its compact form");
  assert.equal(g.head(passage.id).title, HOLD, "…the title says it");
  g.dispose();
});

// ── pinned at source ──────────────────────────────────────────────────────────────────────────────

test("source: every kind change over a reply renders the cards (renderFrom); the ids go through cssId in every selector; replyAway names the Changes filter or the Resolved fold, never the changes fold; focusAway", () => {
  const slice = (from: string, to: string): string => { const a = SRC.indexOf(from), b = SRC.indexOf(to, a); assert.ok(a >= 0 && b > a, from); return SRC.slice(a, b); };
  // onRegionDrawn keeps one renderComposer: the re-place path, which closes a "replace" composer (never a reply)
  for (const [name, from, to, alone] of [
    ["startImageComment", "  startImageComment(range: SourceRange | null): void {", "  private contentRoot()", false],
    ["startComment", "  startComment(sel: Selection): void {", "  startFileComment(): void {", false],
    ["startFileComment", "  startFileComment(): void {", "  /** Reply on a comment:", false],
    ["onRegionDrawn", "  onRegionDrawn(img: Pictured, region: Region): void {", "  /** Re-place (a region card's button)", true],
    ["closeComposer", "  closeComposer(): void {", "  /** The box after the composer changed", false],
  ] as Array<[string, string, string, boolean]>) {
    const body = slice(from, to);
    assert.ok(body.includes("const was = this.composer;") && body.includes("this.renderFrom(was);"), name + " reads the composer it replaces and renders from it");
    if (!alone) assert.ok(!body.includes("this.renderComposer();"), name + " no longer renders the composer alone");
  }
  assert.match(SRC, /private renderFrom\(was: Composer \| null\): void \{\n\s*if \(was && was\.kind === "reply"\) this\.render\(\); else this\.renderComposer\(\);/, "the cards after a reply, the composer alone otherwise");
  assert.match(SRC, /if \(k\.card\) picks\.push\(head\(cards\.querySelector\('\.fc-card\[data-id="' \+ cssId\(k\.card\) \+ '"\]'\)\)\);/, "focusNear's selector takes the id escaped");
  assert.match(SRC, /'\[data-act="' \+ act \+ '"\]\[data-id="' \+ cssId\(id\) \+ '"\]'/, "ownMarks' too");
  assert.match(SRC, /'\[data-act="fcchange"\]\[data-id="' \+ cssId\(key\.slice\(4\)\) \+ '"\]' : '\.fc-hl\[data-id="' \+ cssId\(key\) \+ '"\], \.fc-region\[data-id="' \+ cssId\(key\) \+ '"\]'/, "goTo's");
  assert.match(SRC, /this\.root\?\.querySelector\('\.fc-card\[data-id="' \+ cssId\(id\) \+ '"\]'\)\?\.scrollIntoView/, "scrollCard's");
  // every selector built from an id: placeComposer's `id` is cssId(r) already; the rest wrap the id where they build the string
  const raw = SRC.match(/\[data-id="' \+ (?!cssId\()[\w.()]+ \+ '"\]/g) || [];
  assert.deepEqual(raw, ['[data-id="\' + id + \'"]'], "the one raw-looking selector is placeComposer's, over the escaped id");
  assert.match(SRC, /const id = r === null \? null : cssId\(r\);\s*\/\/[^\n]*\n\s*const host = id === null \? null : this\.sections\.cards\.querySelector\('\.fc-card\[data-id="' \+ id \+ '"\]'\)/, "…which escapes it first; the comment's own card is the one card a reply's box can stand in");
  assert.match(SRC, /if \(this\.activeFilter\(\) === "changes"\) return \{ gone: false, back: "fcfilter", text: "The comment's card is hidden while Changes is chosen above \(All or Comments shows it\); the reply still goes to it\." \};/, "replyAway: the Changes filter, the one row besides the Resolved fold that can hide a comment's card");
  assert.match(SRC, /if \(found\.resolved\) return \{ gone: false, back: "fcresolved",/, "…the Resolved fold for a resolved comment");
  assert.doesNotMatch(SRC, /back: "fcmore"/, "no comment is behind the changes fold: none is drawn inside a change card (the about follow-on, 2026-09-10)");
  assert.match(SRC, /if \(was && was\.kind === "reply" && held\) this\.focusAway\(was\);/, "closeComposer hands the keyboard on when no Reply is rendered");
  assert.match(SRC, /const back = this\.replyAway\(was\)\.back;\n\s*const row = back \? root\.querySelector\('\[data-act="' \+ back \+ '"\]'\) as HTMLElement \| null : null;\n\s*if \(row\) row\.focus\(\{ preventScroll: true \}\);\n\s*else this\.focusNear\(\{ act: "fcreply", id: was\.commentId, at: 0 \}\);/, "…to the fold row, else the nearest control");
  assert.match(SRC, /return isCoarsePointer\(\) \? el\("div", "fc-note fc-held", HOLD_WORDS \+ "\."\) : null;/, "the held head's line on a coarse pointer");
  for (const f of ["file-comments.ts", "file-comments-reply-keep.test.ts", "file-comments-reply-move.test.ts"]) assert.doesNotMatch(web(f), /under the (person's )?hands/, f + " says what moved, literally: the person was typing in the box");
});

test("the stand-in's nodes inspect as their projection: no enumerable edge, so a failing assertion's dump cannot walk the tree", () => {
  const root = doc.createElement("div");
  const kid = doc.createElement("span");
  root.appendChild(kid);
  kid.appendChild(doc.createTextNode("leaf"));
  root.setAttribute("data-x", "1"); root.classList.add("c");
  for (const n of [root, kid, kid.firstChild as T]) {
    assert.ok(Object.keys(n).every((k) => staysEnumerable((n as unknown as Record<string, unknown>)[k])), "only primitives stay enumerable on " + n.constructor.name);
    const dump = inspect(n, { compact: false, customInspect: false, depth: 1000, maxArrayLength: Infinity, showHidden: false, showProxy: false, sorted: true, getters: true });
    assert.ok(!dump.includes("parentNode") && !dump.includes("childNodes"), "no edge in the dump: " + dump);
  }
});
