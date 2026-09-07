// The reply's box inside the card it answers (plans/file-review.md, "The composer follow-on (2026-09-07)", its closing
// sentence): after walking the loop the user asked for the reply box to open under the comment being answered, not in
// the panel's one composer slot above the cards. The box is the same persistent node every composer uses; for a reply it
// is moved into the card — the comment's own card, or the comment's box on the change card hosting it — below the turns
// and above the buttons (placeComposer), and back to the slot for every other kind, when the composer closes, and when
// the list stops showing the card (the comment resolved into the closed fold, gone from the sidecar), where a line says
// why and the words stay. The card opens for the reply and stays open while it is written; the poll's re-render keeps
// the box in its card — the card node stays, the children around the box are the fresh render's (swapCards) — with the
// words, the caret, the height and the keyboard, and moves it into the card's successor when the comment changes cards
// (a change accepted: the comment on its own card); Escape, Cancel and a save hand the keyboard back to the card's Reply.
// Driven through the DOM stand-in the composer test uses (there is no jsdom in this tree), with focus tracked and
// scrollIntoView recorded. Synthetic fixtures only: the notes-api world, placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx, TrackedEdit } from "./file-view";
import type { Status, StoreComment, Hunk, LogEntry } from "./file-comments-model";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const SRC = web("file-comments.ts");
const CHAT_CSS = web("styles.css");
const FEED_CSS = web("feed.css");
const GUIDE = fs.readFileSync(path.resolve(process.cwd(), "..", "docs", "guide.md"), "utf8");
const PLAN = fs.readFileSync(path.resolve(process.cwd(), "..", "plans", "file-review.md"), "utf8");

// ── the DOM stand-in ───────────────────────────────────────────────────────────────────────────────
class Doc {
  body: E;
  hidden = false;
  activeElement: E | null = null;
  scrolled: E[] = [];                                  // every scrollIntoView, in order (startReply scrolls the box's card)
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
  hidden = false; title = ""; type = ""; disabled = false; placeholder = ""; value = ""; checked = false; offsetWidth = 0; readOnly = false;
  rows = 0;
  // the layout a test gives a box: what the browser would measure at height: auto (autosizeNote reads these)
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
  focus(): void { if (this.tabIndex >= 0 && !this.disabled) this.ownerDocument.activeElement = this; }
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
    post: (m) => { posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: noop, editing: () => false, setTrackedEdit: (t) => { tracked.push(t); },
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
    replyBtn: (id: string): E | null => main.querySelector('[data-act="fcreply"][data-id="' + id + '"]'),
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

// ── where the box stands ───────────────────────────────────────────────────────────────────────────

test("Reply moves the box into the comment's card, below its replies and above its buttons; the card opens; the slot stands empty until Cancel", async () => {
  const h = await harness();
  await h.open();
  assert.deepEqual(h.sections(), SLOT, "the panel's five sections, the box in its slot");
  assert.equal(h.composer().hidden, true);
  assert.ok(!h.card(passage.id)!.classList.contains("open"), "the card starts collapsed");
  doc.scrolled.length = 0;
  h.startReply(passage.id, passage.id);
  const box = h.box(), card = h.card(passage.id)!;
  assert.ok(card.classList.contains("open"), "open for the reply");
  assert.deepEqual(h.kids(card), ["fc-card-head", "fc-body", "fc-replies", "fc-composer fc-composer-in", "fc-actions"],
    "the box after the turns and before the card's buttons, wearing the in-card dress");
  assert.deepEqual(h.sections(), NO_SLOT, "…and gone from the slot");
  assert.equal(h.composer().hidden, false);
  assert.equal(h.q(".fc-composer-ref")!.hidden, true, "no reference row: the card is the reference");
  assert.equal(box.placeholder, "Your reply", "the placeholder says what the box is for");
  assert.equal(box.getAttribute("aria-label"), "Reply text");
  assert.deepEqual(h.kids(h.q(".fc-composer .fc-actions")), ["fc-note fc-hint", "fileview-btn", "fileview-btn"], "the hint, Save and Cancel as ever");
  assert.equal(doc.activeElement, box, "the box takes the keyboard");
  assert.ok(doc.scrolled.includes(h.composer()), "the box's place in the card is scrolled into view");
  // Cancel: the box returns to the slot, hidden, undressed; the card stays open
  h.click('[data-act="fccancel"]');
  assert.deepEqual(h.sections(), SLOT);
  assert.equal(h.composer().hidden, true);
  assert.equal(h.composer().className, "fc-composer", "the in-card dress comes off in the slot");
  assert.ok(h.card(passage.id)!.classList.contains("open"), "the card the person opened stays open");
  assert.deepEqual(h.kids(h.card(passage.id)), ["fc-card-head", "fc-body", "fc-replies", "fc-actions"]);
  // a whole-file comment is the slot's box again, with its reference row and its own words
  h.click('[data-act="fcfile"]');
  assert.deepEqual(h.sections(), SLOT);
  assert.equal(h.composer().hidden, false);
  assert.equal(h.q(".fc-composer-ref")!.hidden, false);
  assert.equal(h.q(".fc-composer-ref")!.textContent, "On this file");
  assert.equal(box.placeholder, "Your comment"); assert.equal(box.getAttribute("aria-label"), "Comment text");
  h.dispose();
});

test("a comment bound to a change: Reply moves the box into its box on the change card, below its turns; once the change is accepted the comment's own card takes the box, opened for it", async () => {
  const h = await harness();
  await h.open(WITH_CHANGE);
  h.startReply("chg:h1", bound.id);
  const box = h.box();
  const hosted = h.hosted(bound.id)!;
  assert.ok(hosted, "the bound comment is on the change's card");
  assert.deepEqual(h.kids(hosted), ["fc-reply fc-reply-you", "fc-replies", "fc-composer fc-composer-in", "fc-actions"], "the box after the comment's turns, before its Reply and Resolve");
  assert.deepEqual(h.sections(), NO_SLOT);
  assert.equal(h.q(".fc-composer-ref")!.hidden, true);
  assert.equal(doc.activeElement, box);
  draft(box, "Trimmed is fine.", 8, 63);
  // the change is accepted elsewhere: the comment stands on its own card now, under a key the expand state never saw
  await h.repoll(ACCEPTED);
  assert.equal(h.card("chg:h1"), null, "the change's card is gone");
  const own = h.card(bound.id)!;
  assert.ok(own, "the comment's own card");
  assert.ok(own.classList.contains("open"), "opened for the reply being written");
  assert.deepEqual(h.kids(own), ["fc-card-head", "fc-body", "fc-replies", "fc-composer fc-composer-in", "fc-actions"], "the box rode into it");
  assert.equal(h.box(), box, "the same node");
  assert.equal(box.value, "Trimmed is fine."); assert.deepEqual([box.selectionStart, box.selectionEnd], [8, 8]); assert.equal(box.style.height, "65px");
  assert.equal(doc.activeElement, box, "the keyboard stays in the box");
  // Save from inside the card goes through the panel's delegate root as the reply verb
  h.click('[data-act="fcsave"]');
  await tick();
  assert.equal(h.last().verb, "reply");
  assert.deepEqual(h.last().args, { commentId: bound.id, note: "Trimmed is fine." });
  h.dispose();
});

test("the poll's re-render keeps the box in the same comment's card — the same card node, the fresh children around the box — with the text, caret, height and keyboard; the card stays open", async () => {
  const h = await harness();
  await h.open();
  h.startReply(passage.id, passage.id);
  const box = h.box(), before = h.card(passage.id)!;
  draft(box, "Line one.\nLine two.", 5, 63);
  assert.equal(box.style.height, "65px");
  // a status with a new comment on it: the list is rebuilt around the card holding the box (swapCards keeps that card's
  // node in the document, so nothing holding the textarea is detached), and the rest of the list is the fresh one
  const third: StoreComment = { ...whole, id: T0 + "-120", ts: T0 + 8000, body: "Cite the p99 too." };
  await h.repoll({ store: { v: 3, path: "docs/report.md", suggestions: [], comments: [passage, whole, third] }, unsent: unsent(passage.id, whole.id, third.id), storeMtimeNs: "1757145600000000004" });
  const after = h.card(passage.id)!;
  assert.equal(after, before, "the same card node: the rebuild goes around the box, never detaching what holds it");
  assert.ok(h.card(third.id), "…while the rest of the list is the fresh one: the new comment's card is there");
  assert.ok(after.classList.contains("open"), "still open: the keyed expand state holds");
  assert.deepEqual(h.kids(after), ["fc-card-head", "fc-body", "fc-replies", "fc-composer fc-composer-in", "fc-actions"], "the box is in the kept card, in the same place, the fresh children around it");
  assert.equal(h.box(), box, "the same textarea node");
  assert.equal(box.value, "Line one.\nLine two.", "the text");
  assert.deepEqual([box.selectionStart, box.selectionEnd], [5, 5], "the caret");
  assert.equal(box.style.height, "65px", "the height");
  assert.equal(doc.activeElement, box, "the keyboard, put back after the move");
  assert.deepEqual(h.sections(), NO_SLOT, "nothing stands in the slot");
  assert.equal(h.q('.fc-card[data-id="' + third.id + '"] .fc-composer'), null, "no other card has a box");
  // a refusal keeps the box in the card with the words
  h.chord(); await tick();
  assert.equal(h.last().verb, "reply");
  await h.refuse("no-comment", "no comment with that id");
  assert.deepEqual(h.kids(h.card(passage.id)), ["fc-card-head", "fc-body", "fc-replies", "fc-composer fc-composer-in", "fc-actions"]);
  assert.equal(box.value, "Line one.\nLine two.");
  assert.match(h.q(".fc-composer .fc-err")!.textContent, /no comment with that id/, "the refusal sits under the box, in the card");
  h.dispose();
});

test("the card cannot be folded while its reply is being written; other cards fold as before; Cancel frees the head", async () => {
  const h = await harness();
  await h.open();
  h.startReply(passage.id, passage.id);
  const box = h.box();
  box.value = "Half a thought";
  h.click('.fc-card[data-id="' + passage.id + '"] .fc-card-head');
  assert.ok(h.card(passage.id)!.classList.contains("open"), "still open: a fold would take the box and the words with it");
  assert.ok(h.card(passage.id)!.contains(h.composer()), "the box is still in it");
  assert.equal(box.value, "Half a thought");
  h.click('.fc-card[data-id="' + whole.id + '"] .fc-card-head');
  assert.ok(h.card(whole.id)!.classList.contains("open"), "another card opens");
  h.click('.fc-card[data-id="' + whole.id + '"] .fc-card-head');
  assert.ok(!h.card(whole.id)!.classList.contains("open"), "…and folds, as ever");
  h.click('[data-act="fccancel"]');
  h.click('.fc-card[data-id="' + passage.id + '"] .fc-card-head');
  assert.ok(!h.card(passage.id)!.classList.contains("open"), "the reply over, the head folds the card again");
  h.dispose();
});

test("the comment vanished: the box returns to the slot with the words and a line saying the comment is gone; the comment back, the box returns to its card", async () => {
  const h = await harness();
  await h.open();
  h.startReply(passage.id, passage.id);
  const box = h.box();
  draft(box, "Keep going.", 4, 42);
  await h.repoll({ store: { v: 3, path: "docs/report.md", suggestions: [], comments: [whole] }, unsent: unsent(whole.id), storeMtimeNs: "1757145600000000005" });
  assert.equal(h.card(passage.id), null, "the card is gone");
  assert.deepEqual(h.sections(), SLOT, "the box is back in the slot");
  assert.equal(h.composer().hidden, false, "…open");
  assert.equal(h.composer().className, "fc-composer", "…undressed");
  assert.equal(h.box(), box);
  assert.equal(box.value, "Keep going.", "the words are kept");
  assert.deepEqual([box.selectionStart, box.selectionEnd], [4, 4]); assert.equal(box.style.height, "44px");
  assert.equal(doc.activeElement, box);
  const ref = h.q(".fc-composer-ref")!;
  assert.equal(ref.hidden, false, "the reference row is back: the box has no card to be read against");
  assert.deepEqual(ref.childNodes.map((n) => (n as E).className + ":" + n.textContent),
    ["fc-note:Reply on shipping the cache in v1.2", "fc-note fc-refused:The comment is gone from the file's comments."], "which comment, and why the box moved");
  assert.ok(h.q('.fc-composer [data-act="fcsave"]'), "Save stays: the host answers a reply to a gone comment with its own refusal, under the box");
  // the comment is back (the sidecar was restored): the box goes back into its card, the words with it
  await h.repoll({ storeMtimeNs: "1757145600000000007" });
  assert.deepEqual(h.kids(h.card(passage.id)), ["fc-card-head", "fc-body", "fc-replies", "fc-composer fc-composer-in", "fc-actions"]);
  assert.equal(h.q(".fc-composer-ref")!.hidden, true);
  assert.equal(box.value, "Keep going.");
  h.dispose();
});

test("resolved elsewhere: the card goes into the closed Resolved fold and the box returns to the slot saying so; opening the fold brings the box back into the card", async () => {
  const h = await harness();
  await h.open();
  h.startReply(passage.id, passage.id);
  const box = h.box();
  box.value = "One more thing.";
  await h.repoll({ store: { v: 3, path: "docs/report.md", suggestions: [], comments: [{ ...passage, resolved: true }, whole] }, storeMtimeNs: "1757145600000000005" });
  assert.equal(h.card(passage.id), null, "under the fold");
  assert.ok(h.q('[data-act="fcresolved"]'), "the Resolved fold");
  assert.deepEqual(h.sections(), SLOT);
  assert.deepEqual(h.q(".fc-composer-ref")!.childNodes.map((n) => (n as E).className + ":" + n.textContent),
    ["fc-note:Reply on shipping the cache in v1.2", "fc-note:The comment was resolved meanwhile, so its card is under “Resolved” below; the reply still goes to it."],
    "the row says what happened and, like the other two fold rows, where the card is (ui/CLAUDE.md: no dead ends)");
  assert.equal(box.value, "One more thing.");
  h.click('[data-act="fcresolved"]');
  const card = h.card(passage.id)!;
  assert.ok(card && card.classList.contains("open"), "the card shows again, open");
  assert.deepEqual(h.kids(card), ["fc-card-head", "fc-body", "fc-replies", "fc-composer fc-composer-in", "fc-actions"], "and the box is in it");
  assert.equal(h.q(".fc-composer-ref")!.hidden, true);
  h.dispose();
});

test("every other kind keeps the slot: a whole-file comment and a comment bound to a change take the box out of a reply's card and back to the slot", async () => {
  const h = await harness();
  await h.open({ store: { v: 3, path: "docs/report.md", suggestions: SUGG, comments: [passage] }, hunks: [h1], unsent: unsent(passage.id) });
  h.startReply(passage.id, passage.id);
  assert.deepEqual(h.sections(), NO_SLOT);
  h.click('[data-act="fcfile"]');
  assert.deepEqual(h.sections(), SLOT, "a whole-file comment: the slot");
  assert.equal(h.composer().className, "fc-composer");
  assert.equal(h.q(".fc-composer-ref")!.textContent, "On this file");
  assert.equal(h.card(passage.id)!.contains(h.composer()), false);
  h.click('.fc-card[data-id="chg:h1"] .fc-card-head');
  h.click('[data-act="fcchangereply"][data-id="h1"]');
  assert.deepEqual(h.sections(), SLOT, "a comment bound to a change: the slot too");
  assert.equal(h.q(".fc-composer-ref")!.textContent, "Reply on the change reduced → cut");
  assert.equal(h.box().placeholder, "Your comment");
  assert.equal(h.card("chg:h1")!.contains(h.composer()), false, "the change card holds no box: the change is not a comment to answer under");
  h.startReply(passage.id, passage.id);
  assert.deepEqual(h.sections(), NO_SLOT, "…and a reply takes it into the card again");
  h.dispose();
});

// ── the keyboard ───────────────────────────────────────────────────────────────────────────────────

test("Escape, Cancel and a save hand the keyboard back to the card's Reply; a keyboard that was elsewhere is left alone", async () => {
  const h = await harness();
  await h.open();
  h.startReply(passage.id, passage.id);
  assert.equal(doc.activeElement, h.box());
  const ev = h.key({ key: "Escape" });
  assert.equal(ev.defaultPrevented, true);
  assert.equal(h.composer().hidden, true, "cancelled");
  assert.equal(doc.activeElement, h.replyBtn(passage.id), "Escape: the keyboard is on the Reply that opened the box");
  assert.ok(h.card(passage.id)!.classList.contains("open"), "the card stays open under it");
  // Cancel, from the keyboard on the box
  h.click('[data-act="fcreply"][data-id="' + passage.id + '"]');
  assert.equal(doc.activeElement, h.box());
  h.click('[data-act="fccancel"]');
  assert.equal(doc.activeElement, h.replyBtn(passage.id), "Cancel: the same");
  // a save: the reply lands, the composer closes, the keyboard is on the rebuilt card's Reply
  h.click('[data-act="fcreply"][data-id="' + passage.id + '"]');
  h.box().value = "The response cache, then.";
  h.chord(); await tick();
  assert.equal(h.last().verb, "reply");
  const answered: StoreComment = { ...passage, replies: [...passage.replies!, { author: "you", ts: T0 + 9000, body: "The response cache, then." }] };
  await h.ok({ store: { v: 3, path: "docs/report.md", suggestions: [], comments: [answered, whole] }, storeMtimeNs: "1757145600000000008" });
  assert.equal(h.composer().hidden, true, "saved: the composer closes");
  assert.deepEqual(h.sections(), SLOT);
  assert.equal(h.card(passage.id)!.querySelectorAll(".fc-reply").length, 3, "the new turn is on the card");
  assert.equal(doc.activeElement, h.replyBtn(passage.id), "a save: the keyboard is on Reply, ready for the next");
  // the keyboard was not in the box (the person clicked into the file): Cancel moves it nowhere
  h.click('[data-act="fcreply"][data-id="' + passage.id + '"]');
  doc.activeElement = doc.body;
  h.click('[data-act="fccancel"]');
  assert.equal(doc.activeElement, doc.body, "not ours to move");
  // a whole-file comment's Escape moves the keyboard nowhere either: there is no Reply it came from
  h.click('[data-act="fcfile"]');
  h.key({ key: "Escape" });
  assert.equal(h.composer().hidden, true);
  assert.notEqual(doc.activeElement, h.replyBtn(passage.id));
  h.dispose();
});

// ── pinned at source: the placement, the render order, the guards ─────────────────────────────────

test("source: render builds the cards before the composer and puts the typing box's keyboard back; placeComposer finds the card by comment id and moves the box only when it is out of place; the sections' slot order stands", () => {
  assert.match(SRC, /this\.root\.replaceChildren\(head, this\.composerBox, cards, send, log\);/, "the slot's place: head, the box, cards, send, log");
  assert.match(SRC, /const typing = document\.activeElement === this\.input;\n\s*const inCard = cards\.contains\(this\.composerBox\), scroll = this\.input\.scrollTop;\n\s*this\.latchReplyCard\(\);[^\n]*\n\s*head\.replaceChildren\(this\.renderHead\(s\)\);\n\s*this\.swapCards\(this\.renderCards\(s\)\);[^\n]*\n\s*this\.renderComposer\(\);/,
    "where the keyboard is, read before the rebuild; the cards swapped around the box first, then the composer: the box stands in a card of the FRESH list — the one the swap kept, or the one placeComposer moves it into");
  assert.match(SRC, /if \(typing && document\.activeElement !== this\.input\) this\.input\.focus\(\{ preventScroll: true \}\);/, "a moved node drops its focus; render puts it back");
  const place = SRC.slice(SRC.indexOf("  private placeComposer(): boolean {"), SRC.indexOf("  private renderCards("));
  assert.ok(place.includes(`this.sections.cards.querySelector('.fc-card[data-id="' + id + '"], .fc-hosted[data-id="' + id + '"]')`), "the card by comment id — its own, or its box on the change card");
  assert.ok(place.includes("if (at < 0 || at !== want - 1) parent.insertBefore(box, next);"), "no move when the box is already where it belongs (a move drops the keyboard)");
  assert.ok(place.includes('n.classList.contains("fc-actions")') && place.includes("before(root, this.sections.cards);"), "before the buttons in a card; before the cards in the slot");
  assert.ok(place.includes('box.classList.add("fc-composer-in");') && place.includes('box.classList.remove("fc-composer-in");'), "the in-card dress on and off");
  assert.match(SRC, /const inCard = this\.placeComposer\(\);\s*\/\/[^\n]*\n\s*if \(!c\) \{ this\.input\.hidden = false; return; \}/, "renderComposer places first, a closed box included (it returns to the slot)");
  assert.match(SRC, /ref\.hidden = inCard;/, "no reference row in the card");
  assert.match(SRC, /this\.input\.placeholder = c\.kind === "reply" \? "Your reply" : "Your comment";/);
  assert.match(SRC, /const isOpen = this\.openCards\.has\(c\.id\) \|\| this\.replyTo\(\) === c\.id;/, "a comment card is open while its reply is written");
  assert.match(SRC, /const isOpen = this\.openCards\.has\(c\.key\) \|\| c\.comments\.some\(\(cm\) => cm\.id === this\.replyTo\(\)\);/, "a change card too, for a hosted comment's reply");
  assert.match(SRC, /fccard: \(x\) => \{ const id = x\.dataset\.id!; if \(!this\.openCards\.has\(id\)\) this\.openCards\.add\(id\); else if \(!this\.hostsReply\(id\)\) this\.openCards\.delete\(id\); this\.render\(\); \},/, "the head folds every card but the one hosting the reply");
  assert.match(SRC, /this\.render\(\);\n\s*this\.composerBox\.scrollIntoView\(\{ block: "nearest" \}\);[^\n]*\n\s*this\.input\.focus\(\);\n\s*\}/, "startReply scrolls the box's place into view, then focuses it");
  assert.match(SRC, /const held = this\.composerBox\.contains\(document\.activeElement\);/, "closeComposer reads where the keyboard is before hiding the box");
  assert.match(SRC, /if \(was && was\.kind === "reply" && held\) \(this\.root\?\.querySelector\('\[data-act="fcreply"\]\[data-id="' \+ cssId\(was\.commentId\) \+ '"\]'\) as HTMLElement \| null\)\?\.focus\(\{ preventScroll: true \}\);/, "…and hands it to the card's Reply, found by the escaped id");
});

test("the sheets: .fc-composer-in is the reply-of-yours dress — the wash and the accent edge — byte-equal in both, tokens only", () => {
  const rule = (css: string, head: string): string => { const a = css.indexOf("\n" + head); assert.ok(a >= 0, head); return css.slice(a + 1, css.indexOf("}", a) + 1); };
  const chat = rule(CHAT_CSS, ".fc-composer-in {");
  assert.equal(chat, rule(FEED_CSS, ".fc-composer-in {"), "mirrors byte for byte");
  assert.equal(chat, ".fc-composer-in { border-radius: 6px; padding: 5px 8px; background: var(--accent-wash); border-left: 3px solid var(--accent); }");
  const you = rule(CHAT_CSS, ".fc-reply-you {");
  assert.ok(you.includes("background: var(--accent-wash); border-left: 3px solid var(--accent);"), "the same wash and edge a reply of yours wears");
  assert.doesNotMatch(chat, /#[0-9a-fA-F]{3,8}\b|rgba?\(|font-size/, "tokens only, no size of its own");
  for (const css of [CHAT_CSS, FEED_CSS]) assert.ok(css.indexOf(".fc-reply-you {") < css.indexOf(".fc-composer-in {") && css.indexOf(".fc-composer-in {") < css.indexOf("/* ── end file comments panel ── */"), "inside the panel block, beside the reply rules");
  // the reference row is hidden in the card by the attribute, and the row's own display: flex (an author rule) would beat the
  // UA sheet's [hidden] — so the sheet says display: none for it, as it does for .fc-composer[hidden]
  assert.equal(rule(CHAT_CSS, ".fc-composer-ref[hidden] {"), ".fc-composer-ref[hidden] { display: none; }");
  assert.equal(rule(FEED_CSS, ".fc-composer-ref[hidden] {"), ".fc-composer-ref[hidden] { display: none; }");
});

test("docs: the guide says Reply opens the box inside the card; the plan's follow-on note says where the box stands, where it returns, and who gets the keyboard", () => {
  const flat = (t: string) => t.replace(/\s+/g, " ");
  const files = flat(GUIDE.slice(GUIDE.indexOf("### Files"), GUIDE.indexOf("## Automatic nudges")));
  assert.ok(files.includes("**Reply** opens the reply box inside the card, under the comment and its replies"), "the guide");
  assert.ok(!files.includes("reply into it"), "the old phrase is gone");
  const note = flat(PLAN.slice(PLAN.indexOf("The composer follow-on (2026-09-07)"), PLAN.indexOf("### Slice 3: region comments on images")));
  for (const phrase of ["inside the card it answers", "below the comment's turns and above its buttons", "across the poll's re-render", "returns to the panel's slot", "a line saying why", "hands the keyboard back to the card's Reply", "file-comments-reply-place.test.ts"]) {
    assert.ok(note.includes(phrase), "the plan's note says: " + phrase);
  }
});
