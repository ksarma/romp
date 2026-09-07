// The reply's box changing CARDS while the person types in it (plans/file-review.md, "The composer follow-on (2026-09-07)", its
// closing sentence; the review of that change). A reply's box stands in the card the list shows for its comment, and the
// list can show the comment in another card mid-reply: a passage comment the session answers with a track-edit bound to it
// moves onto the change's card, among the change cards at the top of the list; a hosted comment whose change is accepted —
// Accept on the card, Send's accept-all, a decision elsewhere — moves to its own card, among the comment cards below. render()
// used to scroll the box into view only for a move between a card and the slot (a slot-or-card bit, equal on both sides of a
// card-to-card move), so typing went on into a box that could be off-screen in a long list. Now render() keys the scroll on
// the node the box stood in: a different node after the rebuild is a move, whatever containers are on its two ends. The move
// itself still costs a detach — the chain from the section to the box changes depth, and a node cannot change parents without
// leaving the document (swapCards says why moveBefore would not help) — so the words, the caret, the height and the keyboard
// are what the test asks to survive, plus the one scroll. Driven through a copy of the reply-keep test's DOM stand-in, which
// logs every scrollIntoView, detach and focus. Synthetic fixtures only: the notes-api world, placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx, TrackedEdit } from "./file-view";
import type { Status, StoreComment, Hunk, LogEntry } from "./file-comments-model";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const SRC = web("file-comments.ts");

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
  parentNode: N | null = null;
  childNodes: N[] = [];
  constructor(public ownerDocument: Doc) {}
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
  constructor(doc: Doc, public data: string) { super(doc); }
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
// a pending change and the comment bound to it, shown on the change's card
const cut = DOC.indexOf("cut");
const h1: Hunk = { id: "h1", author: "api", ts: T0 - 90000, kind: "sub", curFrom: cut, curTo: cut + 3, baseFrom: cut, baseTo: cut + 7, oldText: "reduced", newText: "cut", anchor: null };
const SUGG = [{ id: "h1", author: "api", authorId: SID, ts: T0 - 90000, kind: "sub", from: cut, oldText: "reduced", newText: "cut" }];
const bound: StoreComment = { id: T0 + 1000 + "-5", author: "you", ts: T0 + 1000, body: "Say cut, not reduced.", suggestionId: "h1",
  replies: [{ author: "api", authorId: SID, ts: T0 + 3000, body: "Done." }], resolved: false };
const ACCEPT_LOG: LogEntry = { ts: "2026-09-06T08:01:00Z", kind: "accept", author: "you", changes: [{ id: "h1", oldText: "reduced", newText: "cut" }] };
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
/** The world with the change h1 pending and the comment bound to it on its card. */
const WITH_CHANGE: Partial<Status> = { store: { v: 3, path: "docs/report.md", suggestions: SUGG, comments: [passage, bound] }, hunks: [h1], unsent: unsent(passage.id, bound.id) };
/** The same world after the change was accepted: the comment stands on its own card, wearing the decision. */
const ACCEPTED: Partial<Status> = { store: { v: 3, path: "docs/report.md", suggestions: [], comments: [passage, bound] }, hunks: [], log: [ACCEPT_LOG],
  storeMtimeNs: "1757145600000000006", unsent: { comments: [passage.id, bound.id], replies: [], accepted: 1, rejected: 0, watermark: null } };

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
  let aside: E | null = null;
  const noop = () => { /* inert */ };
  const ctx: FileViewActionCtx = {
    path: ABS, sid: SID, todoId: null,
    body: () => body as unknown as HTMLElement, mode: () => "rendered", text: () => null,
    mtimeNs: () => "1757145600000000001", media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [], identity: () => ({ name: "api", color: null }),
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
    hosted: (id: string): E | null => main.querySelector('.fc-hosted[data-id="' + id + '"]'),
    replyBtn: (id: string): E | null => main.querySelectorAll('[data-act="fcreply"]').find((b) => b.dataset.id === id) || null,
    cardBy: (id: string): E | null => main.querySelectorAll('.fc-card').find((c) => c.dataset.id === id) || null,   // by the id as data: it may hold a quote
    /** The slot's reference row, class:text per span. */
    row: (): string[] => h.q('.fc-composer-ref')!.childNodes.map((n) => (n as E).className + ':' + n.textContent),
    /** The detaches since `mark` that took the textarea, or a node holding it, out of the document. Read by length: a failed
     *  deepEqual over stand-in nodes inspects the whole cyclic tree for its message and never returns. */
    outOfDoc: (mark: number): N[] => doc.detached.slice(mark).filter((n) => n === h.box() || (n instanceof E && n.contains(h.box()))),
    key: (init: Init): Ev => h.box().dispatch("keydown", init),
    chord: (): Ev => h.key({ key: "Enter", ctrlKey: true }),
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

// ── more fixtures: the passage comment bound to the change mid-reply ─────────────────────────────
/** The world after the session answered the passage comment with a track-edit bound to it (the plan's `track-edit --thread`):
 *  the comment keeps its anchor, gains the change's id, and the list shows it on the change's card. */
const boundPassage: StoreComment = { ...passage, suggestionId: "h1" };
const BOUND_MID_REPLY: Partial<Status> = { store: { v: 3, path: "docs/report.md", suggestions: SUGG, comments: [boundPassage, whole] }, hunks: [h1], unsent: unsent(passage.id, whole.id), storeMtimeNs: "1757145600000000004" };

// ── the box moved between two cards is brought into view ──────────────────────────────────────────

test("own card → the change card hosting it: the session's track-edit binds the comment under the reply; the box moves into the comment's box on the change card and is brought into view, with its words, caret, height and keyboard", async () => {
  const h = await harness();
  await h.open();
  h.startReply(passage.id, passage.id);
  const box = h.box(), compo = h.composer();
  draft(box, "The response cache, then.", 12, 63);
  const focusMark = doc.focused.length;
  doc.scrolled.length = 0;
  await h.repoll(BOUND_MID_REPLY);
  assert.equal(h.card(passage.id), null, "the comment's own card is gone: the list shows it on the change's card");
  const hosted = h.hosted(passage.id);
  assert.ok(hosted && hosted.contains(compo), "the box stands in the comment's box on the change card");
  assert.deepEqual(h.kids(hosted!), ["fc-reply fc-reply-you", "fc-replies", "fc-composer fc-composer-in", "fc-actions"], "below the turns, above the buttons");
  assert.ok(h.card("chg:h1")!.classList.contains("open"), "the change card is open for it");
  assert.equal(h.q('.fc-card[data-id="chg:h1"] .fc-card-head')!.getAttribute("aria-disabled"), "true", "…and its head is held");
  assert.deepEqual(h.sections(), NO_SLOT, "the slot is empty");
  assert.equal(doc.scrolled.length, 1, "brought into view — once"); assert.ok(doc.scrolled[0] === compo, "the box, where it now stands");
  assert.ok(h.box() === box, "the same textarea"); assert.equal(box.value, "The response cache, then.");
  assert.deepEqual([box.selectionStart, box.selectionEnd], [12, 12]); assert.equal(box.style.height, "65px");
  assert.ok(doc.activeElement === box, "the keyboard is back in it");
  assert.equal(doc.focused.length, focusMark + 1, "…put back by render, once: the move detached the box");
  // no move, no scroll: the next poll keeps the change card and the box in it
  doc.scrolled.length = 0;
  await h.repoll({ ...BOUND_MID_REPLY, storeMtimeNs: "1757145600000000005" });
  assert.ok(h.hosted(passage.id)!.contains(compo), "kept there"); assert.equal(doc.scrolled.length, 0, "no move, no scroll");
  h.dispose();
});

test("the change card → the comment's own card: the change accepted elsewhere lands by the poll; the box moves into the comment's own card, before its buttons, and is brought into view", async () => {
  const h = await harness();
  await h.open(WITH_CHANGE);
  h.startReply("chg:h1", bound.id);
  const box = h.box(), compo = h.composer();
  draft(box, "Trimmed is fine.", 8, 63);
  const focusMark = doc.focused.length;
  doc.scrolled.length = 0;
  await h.repoll(ACCEPTED);
  assert.equal(h.card("chg:h1"), null, "the change card is gone");
  const own = h.card(bound.id);
  assert.ok(own && own.contains(compo), "the box stands in the comment's own card");
  const ks = h.kids(own!);
  assert.equal(ks[ks.indexOf("fc-composer fc-composer-in") + 1], "fc-actions", "before the card's buttons");
  assert.equal(own!.querySelector(".fc-card-head")!.getAttribute("aria-disabled"), "true", "the own card's head is held");
  assert.deepEqual(h.sections(), NO_SLOT);
  assert.equal(doc.scrolled.length, 1, "brought into view — once"); assert.ok(doc.scrolled[0] === compo, "the box");
  assert.equal(box.value, "Trimmed is fine."); assert.deepEqual([box.selectionStart, box.selectionEnd], [8, 8]); assert.equal(box.style.height, "65px");
  assert.ok(doc.activeElement === box, "the keyboard is back in it"); assert.equal(doc.focused.length, focusMark + 1, "put back once");
  h.dispose();
});

test("the change accepted by the card's own Accept under the box: the busy render moves and scrolls nothing; the reply that lands moves the box into the comment's own card and brings it into view", async () => {
  const h = await harness();
  await h.open(WITH_CHANGE);
  h.startReply("chg:h1", bound.id);
  const box = h.box(), compo = h.composer();
  draft(box, "Trimmed is fine.", 16, 63);
  doc.scrolled.length = 0;
  h.click('[data-act="fcaccept"][data-id="h1"]'); await tick();
  assert.equal(h.last().verb, "accept");
  assert.ok(h.hosted(bound.id)!.contains(compo), "the busy render keeps the box where it is");
  assert.equal(doc.scrolled.length, 0, "…and scrolls nothing");
  await h.ok(ACCEPTED);
  assert.ok(h.card(bound.id)!.contains(compo), "the comment's own card took the box");
  assert.equal(doc.scrolled.length, 1, "brought into view — once"); assert.ok(doc.scrolled[0] === compo, "the box");
  assert.equal(box.value, "Trimmed is fine."); assert.ok(doc.activeElement === box, "the keyboard is back in it");
  h.dispose();
});

test("the same move with the keyboard elsewhere leaves the view where the person put it; the words ride with the box", async () => {
  const h = await harness();
  await h.open();
  h.startReply(passage.id, passage.id);
  draft(h.box(), "Half a thought", 14, 42);
  doc.activeElement = doc.body;                        // the person clicked into the file
  doc.scrolled.length = 0;
  await h.repoll(BOUND_MID_REPLY);
  assert.ok(h.hosted(passage.id)!.contains(h.composer()), "the box moved onto the change card");
  assert.equal(doc.scrolled.length, 0, "not typing: no scroll");
  assert.equal(h.box().value, "Half a thought", "the words rode with it");
  h.dispose();
});

// ── pinned at source ──────────────────────────────────────────────────────────────────────────────

test("source: render keys the scroll on the node the box stood in, so a card-to-card move scrolls too; the comments claim no more than the code keeps", () => {
  assert.match(SRC, /const home = this\.composerBox\.parentElement;[^\n]*\n\s*const typing = document\.activeElement === this\.input;/, "the box's node, read before the rebuild");
  assert.match(SRC, /if \(typing && this\.composerBox\.parentElement !== home\) this\.composerBox\.scrollIntoView\(\{ block: "nearest" \}\);/, "between a card and the slot, or between two cards: one check, the node the box stood in against the one it stands in");
  assert.doesNotMatch(SRC, /const inCard = cards\.contains\(this\.composerBox\)/, "no slot-or-card bit beside it: the parent check covers a move to or from the slot too");
  assert.doesNotMatch(SRC, /box leaves a card only when/, "swapCards no longer says the box leaves a card only when its card is gone");
  assert.doesNotMatch(SRC, /a rebuilt list never makes it move/, "placeComposer neither");
});
