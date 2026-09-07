// The Comments panel's composer as a multi-line box (plans/file-review.md, "The composer follow-on (2026-09-07)"):
// after walking the loop the user found the one-line box too small. Every composer the panel offers — a passage, the
// whole file, a region, a reply on a card, a comment bound to a change — is one textarea: three rows to start, grown
// to its content up to twelve rows (then it scrolls), draggable taller. Enter, plain or with Shift, adds a line (the
// textarea's own newline; never a save, whatever a chat tool taught the person's hands); Cmd+Enter or Ctrl+Enter, or
// the Save button, saves; Escape cancels as before. The draft (text, caret, chosen height) survives the poll's
// re-render and a refusal, saving trims the blank ends and keeps the breaks inside, a blank comment saves nothing, and
// a card renders a multi-line body with its breaks. Driven through the same DOM stand-in the panel tests use (there is
// no jsdom in this tree), with focus tracked and a scroll height a test can set; what a stand-in cannot lay out — the
// real cap, the real key events — is file-comments-composer-browser.test.ts. Synthetic fixtures only: the notes-api
// world, placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { marked } from "marked";
import type { FileViewActionCtx, TrackedEdit } from "./file-view";
import type { LogEntry, Status, StoreComment } from "./file-comments-model";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const SRC = web("file-comments.ts");
const CHAT_CSS = web("styles.css");
const FEED_CSS = web("feed.css");
const TRACK = web("track-decorations.ts");
const GUIDE = fs.readFileSync(path.resolve(process.cwd(), "..", "docs", "guide.md"), "utf8");
const PLAN = fs.readFileSync(path.resolve(process.cwd(), "..", "plans", "file-review.md"), "utf8");

// ── the DOM stand-in ───────────────────────────────────────────────────────────────────────────────
class Doc {
  body: E;
  hidden = false;
  activeElement: E | null = null;
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
  scrollIntoView(): void { /* inert */ }
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
// the platform the module detected at import (its IS_MAC reads navigator.platform once, the editor's rule)
const MAC = typeof navigator !== "undefined" && /Mac|iP(?:hone|ad|od)/.test(navigator.platform || "");

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const T0 = 1757145600000;
const passage: StoreComment = {
  id: T0 + "-118", author: "you", ts: T0, body: "Which cache? Say which.",
  anchor: { quote: "shipping the cache in v1.2", prefix: "We recommend ", suffix: "." }, replies: [], resolved: false,
};
function status(over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: "/repo/notes-api", storePath: "/repo/notes-api/.trackchanges/docs%2Freport.md.json",
    trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
    store: { v: 3, path: "docs/report.md", suggestions: [], comments: [passage] },
    hunks: [], log: [],
    unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 0, watermark: null },
    ...over,
  };
}

// ── the harness: a mounted panel inside the viewer's body row ──────────────────────────────────────
type Posted = Record<string, any>;
async function harness(over: Partial<FileViewActionCtx> & { html?: string; src?: string } = {}) {
  const fc = await import("./file-comments");
  const { html, src, ...ctxOver } = over;
  const main = doc.createElement("div"); main.className = "fileview-main";
  const body = doc.createElement("div"); body.className = "fileview-body"; main.appendChild(body);
  if (html !== undefined) { const md = doc.createElement("div"); md.className = "fileview-md"; md.innerHTML = html; body.appendChild(md); }
  const posted: Posted[] = [];
  const tracked: Array<TrackedEdit | null> = [];
  const closers: Array<() => void> = [];
  const saved: Array<(info: { mtimeNs: string; logged: boolean }) => void> = [];
  const modes: string[] = [];
  let aside: E | null = null;
  const noop = () => { /* inert */ };
  const ctx: FileViewActionCtx = {
    path: ABS, sid: SID, todoId: null,
    body: () => body as unknown as HTMLElement, mode: () => "rendered", text: () => (src === undefined ? null : src),
    mtimeNs: () => "1757145600000000001", media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [], identity: () => ({ name: "api", color: null }),
    onRendered: noop, onSelection: noop, onSaved: (cb) => { saved.push(cb); }, onClose: (cb) => { closers.push(cb); },
    post: (m) => { posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: noop, editing: () => false, setTrackedEdit: (t) => { tracked.push(t); },
    aside: (el) => { if (el) { aside = el as unknown as E; main.appendChild(aside); } else if (aside) { aside.remove(); aside = null; } },
    setMode: (m) => { modes.push(m); }, scrollToOffset: noop, reload: noop,
    ...ctxOver,
  };
  const unit = fc.fileCommentsAction.mount(ctx) as unknown as E;
  const button = unit.childNodes[0] as E;
  const last = (): Posted => posted[posted.length - 1];
  const reply = async (data: Record<string, unknown>) => { win.dispatchEvent(new MessageEvent("message", { data })); await tick(); await tick(); };
  const h = {
    fc, main, body, unit, button, posted, modes, saved, last,
    ok: (over: Partial<Status> = {}) => reply({ type: "fileCommentsResult", reqId: last().reqId, ...status(over) }),
    refuse: (code: string, error: string) => reply({ type: "fileCommentsFailed", reqId: last().reqId, verb: last().verb, code, error }),
    q: (sel: string) => main.querySelector(sel),
    qa: (sel: string) => main.querySelectorAll(sel),
    click: (sel: string) => { const e = main.querySelector(sel); assert.ok(e, "a control " + sel); e!.dispatch("click"); },
    box: (): E => { const b = main.querySelector("textarea.fc-input"); assert.ok(b, "the comment box is a textarea"); return b!; },
    /** The keys as the browser sends them to the focused box. */
    key: (init: Init): Ev => h.box().dispatch("keydown", init),
    chord: (): Ev => h.key({ key: "Enter", ctrlKey: true }),
    /** Open the panel on a status and start a whole-file comment. */
    open: async (over: Partial<Status> = {}) => { await h.ok(over); button.dispatch("click"); await h.ok(over); },
    float: () => { const f = doc.body.querySelectorAll(".fc-float"); return f[f.length - 1]; },
    dispose: () => { for (const cb of closers) cb(); },
  };
  return h;
}

// ── the key policy, pure ───────────────────────────────────────────────────────────────────────────

test("composerKeyAction: Enter, plain or with Shift, is the browser's newline; Enter with Cmd or Ctrl saves; Escape cancels; a composing IME keeps its keys", async () => {
  const { composerKeyAction, saveChord, composerHint, NOTE_ROWS, NOTE_MAX_ROWS } = await import("./file-comments");
  assert.equal(composerKeyAction({ key: "Enter" }), null, "a plain Enter is not ours: the textarea inserts the newline");
  // The browser's KeyboardEvent carries shiftKey; the function's parameter type names only the modifiers it reads, so
  // the key arrives as the event would (a typed value, not a literal) — and the point is that shiftKey is NOT read: the
  // chat composer sends on Enter and breaks a line on Shift+Enter, and a hand trained there must not save a half-written
  // comment here (the docstring's "a plain or Shift+Enter is the browser's own newline").
  const shiftEnter: Pick<KeyboardEvent, "key" | "shiftKey"> = { key: "Enter", shiftKey: true };
  assert.equal(composerKeyAction(shiftEnter), null, "Shift+Enter is the textarea's newline too, never a save");
  const shiftEscape: Pick<KeyboardEvent, "key" | "shiftKey"> = { key: "Escape", shiftKey: true };
  assert.equal(composerKeyAction(shiftEscape), "cancel", "Shift changes nothing about Escape");
  assert.equal(composerKeyAction({ key: "Enter", metaKey: true }), "save", "Cmd+Enter");
  assert.equal(composerKeyAction({ key: "Enter", ctrlKey: true }), "save", "Ctrl+Enter");
  assert.equal(composerKeyAction({ key: "Enter", ctrlKey: true, metaKey: true }), "save");
  assert.equal(composerKeyAction({ key: "Escape" }), "cancel");
  assert.equal(composerKeyAction({ key: "Enter", ctrlKey: true, isComposing: true }), null, "an IME's Enter commits the composition, never a save");
  assert.equal(composerKeyAction({ key: "Escape", isComposing: true }), null);
  assert.equal(composerKeyAction({ key: "a", ctrlKey: true }), null);
  assert.equal(composerKeyAction({ key: "Tab" }), null);
  assert.equal(saveChord(true), "Cmd+Enter"); assert.equal(saveChord(false), "Ctrl+Enter");
  assert.equal(composerHint(true), "Cmd+Enter saves; Enter adds a line");
  assert.equal(composerHint(false), "Ctrl+Enter saves; Enter adds a line");
  assert.equal(NOTE_ROWS, 3); assert.equal(NOTE_MAX_ROWS, 12);
});

test("autosizeNote: height auto, then the scroll height plus the border; a box with no layout keeps the height it had", async () => {
  const { autosizeNote } = await import("./file-comments");
  const fake = { style: { height: "" } as Record<string, string>, scrollHeight: 100, offsetHeight: 102, clientHeight: 100 };
  const ta = fake as unknown as HTMLTextAreaElement;
  assert.equal(autosizeNote(ta), "102px");
  assert.equal(fake.style.height, "102px", "border-box: the two 1px borders ride on the scroll height");
  fake.scrollHeight = 40;
  assert.equal(autosizeNote(ta), "42px", "…and it shrinks when lines go (the sheet's min-height floors it at three rows)");
  const none = { style: { height: "77px" } as Record<string, string>, scrollHeight: 0, offsetHeight: 0, clientHeight: 0 } as unknown as HTMLTextAreaElement;
  assert.equal(autosizeNote(none), null, "nothing to measure (hidden, or a document with no renderer)");
  assert.equal(none.style.height, "77px", "the inline height it had is put back, never left at auto");
});

// ── the box ────────────────────────────────────────────────────────────────────────────────────────

test("every composer is one textarea of three rows with the reference row above it, Save and Cancel beside it and the platform's chord in a hint", async () => {
  const h = await harness();
  await h.open();
  h.click('[data-act="fcfile"]');
  const box = h.box();
  assert.equal(box.tagName, "TEXTAREA");
  assert.equal(box.rows, 3, "three rows to start");
  assert.equal(box.placeholder, "Your comment", "short and plain");
  assert.equal(box.getAttribute("aria-label"), "Comment text");
  assert.equal(doc.activeElement, box, "the box takes the keyboard");
  const composer = h.q(".fc-composer")!;
  assert.deepEqual(composer.childNodes.map((c) => (c as E).className), ["fc-composer-ref", "fc-input", "fc-actions", ""], "the reference row, the box, the buttons row, the error slot");
  assert.equal(h.q(".fc-composer-ref")!.textContent, "On this file");
  const acts = h.q(".fc-composer .fc-actions")!;
  assert.deepEqual(acts.childNodes.map((c) => (c as E).className + ":" + c.textContent),
    ["fc-note fc-hint:" + (MAC ? "Cmd" : "Ctrl") + "+Enter saves; Enter adds a line", "fileview-btn:Save", "fileview-btn:Cancel"],
    "the hint at the row's left in the platform's words, then Save, then Cancel");
  assert.equal(acts.querySelector('[data-act="fcsave"]')!.textContent, "Save");
  assert.equal(acts.querySelector('[data-act="fccancel"]')!.textContent, "Cancel");
  // a reply on a card is the same box, the reference row naming the card
  h.click('[data-act="fccancel"]');
  h.click('.fc-card[data-id="' + passage.id + '"] .fc-card-head');
  h.click('[data-act="fcreply"][data-id="' + passage.id + '"]');
  assert.equal(h.box(), box, "one box for every composer the panel offers");
  assert.equal(h.q(".fc-composer-ref")!.textContent, "Reply on shipping the cache in v1.2");
  assert.ok(h.q(".fc-composer .fc-hint"), "the hint is there for a reply too");
  h.dispose();
});

test("Enter, plain or with Shift, adds a line and saves nothing; Ctrl+Enter or Cmd+Enter saves the text with its line breaks, the blank ends trimmed", async () => {
  const h = await harness();
  await h.open();
  h.click('[data-act="fcfile"]');
  const box = h.box();
  box.value = "First line.";
  const before = h.posted.length;
  const plain = h.key({ key: "Enter" });
  assert.equal(plain.defaultPrevented, false, "the browser's default — a newline in the box — is left to it");
  assert.equal(h.posted.length, before, "nothing was written");
  assert.equal(h.q(".fc-composer")!.hidden, false, "the composer stays open");
  // Shift+Enter, the chat composer's soft break, is the same newline here: the listener leaves it alone and nothing is saved
  const soft = h.key({ key: "Enter", shiftKey: true });
  assert.equal(soft.defaultPrevented, false, "Shift+Enter is left to the textarea as well");
  assert.equal(h.posted.length, before, "…and writes nothing");
  assert.equal(h.q(".fc-composer")!.hidden, false);
  assert.equal(box.value, "First line.", "the draft is untouched (the stand-in inserts no newline; the browser leg sees the real one)");
  box.value = "First line.\nSecond line.  \n\n";
  const ev = h.chord();
  assert.equal(ev.defaultPrevented, true, "the chord is ours: no newline goes in with the save");
  await tick();
  const c = h.last();
  assert.equal(c.verb, "comment");
  assert.equal(c.args.note, "First line.\nSecond line.", "the break inside stays; the blank tail goes");
  await h.ok();
  assert.equal(h.q(".fc-composer")!.hidden, true, "saved: the composer closes");
  assert.equal(box.value, "", "…and the box is empty for the next comment");
  // Cmd+Enter is the same chord (a Mac's), whatever the platform
  h.click('[data-act="fcfile"]');
  box.value = "  Lead with the numbers.";
  const mac = h.key({ key: "Enter", metaKey: true });
  assert.equal(mac.defaultPrevented, true);
  await tick();
  assert.equal(h.last().verb, "comment");
  assert.equal(h.last().args.note, "Lead with the numbers.");
  await h.ok();
  h.dispose();
});

test("the Save button saves through the panel's delegate root; a reply and its line breaks go out verbatim", async () => {
  const h = await harness();
  await h.open();
  h.click('.fc-card[data-id="' + passage.id + '"] .fc-card-head');
  h.click('[data-act="fcreply"][data-id="' + passage.id + '"]');
  const box = h.box();
  box.value = "The response cache.\n\nNot the query cache.";
  h.click('[data-act="fcsave"]');
  await tick();
  const c = h.last();
  assert.equal(c.verb, "reply");
  assert.deepEqual(c.args, { commentId: passage.id, note: "The response cache.\n\nNot the query cache." });
  assert.equal(h.q('[data-act="fcsave"]')!.textContent, "Saving…", "posts-and-waits: relabeled for the round trip");
  assert.equal(h.q('[data-act="fcsave"]')!.disabled, true);
  assert.equal(box.readOnly, true);
  await h.ok();
  assert.equal(h.q(".fc-composer")!.hidden, true);
  h.dispose();
});

test("Escape cancels: the composer closes, the text and the chosen height go, and the viewer's own Escape never hears it", async () => {
  const h = await harness();
  await h.open();
  h.click('[data-act="fcfile"]');
  const box = h.box();
  box.value = "Drop this.\nAnd this.";
  box.style.height = "160px";
  let viewerSawEscape = 0;
  h.main.addEventListener("keydown", (ev) => { if (ev.key === "Escape") viewerSawEscape++; });
  const ev = h.key({ key: "Escape" });
  assert.equal(ev.defaultPrevented, true);
  assert.equal(viewerSawEscape, 0, "stopped at the box: the viewer's document-level Escape (which closes the viewer) never fires");
  assert.equal(h.q(".fc-composer")!.hidden, true, "cancelled");
  assert.equal(box.value, "");
  assert.equal(box.style.height, "", "the next comment starts at three rows");
  assert.equal(h.posted.filter((p) => p.verb === "comment").length, 0, "nothing was written");
  h.dispose();
});

test("an empty or whitespace-only comment saves nothing, by the chord or the button", async () => {
  const h = await harness();
  await h.open();
  h.click('[data-act="fcfile"]');
  const box = h.box();
  const before = h.posted.length;
  for (const v of ["", "   ", "\n\n", "  \n \t \n  "]) {
    box.value = v;
    h.chord(); await tick();
    h.click('[data-act="fcsave"]'); await tick();
    assert.equal(h.posted.length, before, JSON.stringify(v) + ": nothing goes out");
    assert.equal(h.q(".fc-composer")!.hidden, false, "the composer stays open for the words");
  }
  assert.equal(h.q(".fc-composer .fc-err"), null, "and no error row: an empty box is not a mistake to report");
  h.dispose();
});

test("the box grows with its content and shrinks back; a height the person dragged stands until the composer closes", async () => {
  const h = await harness();
  await h.open();
  h.click('[data-act="fcfile"]');
  const box = h.box();
  assert.ok(!box.style.height, "no inline height at first: the sheet's rows and min-height");
  const type = (text: string, scrollHeight: number) => { box.value = text; box.scrollHeight = scrollHeight; box.offsetHeight = scrollHeight + 2; box.clientHeight = scrollHeight; box.dispatch("input"); };
  type("one\ntwo\nthree\nfour", 84);
  assert.equal(box.style.height, "86px", "the scroll height plus the border, on every input");
  type("one\ntwo\nthree\nfour\nfive\nsix\nseven\neight", 168);
  assert.equal(box.style.height, "170px", "grown");
  type("one", 42);
  assert.equal(box.style.height, "44px", "shrunk (the sheet's min-height keeps three rows on screen)");
  // the person drags the handle (resize: vertical writes the inline height): their height stands
  box.style.height = "240px";
  type("one\ntwo", 63);
  assert.equal(box.style.height, "240px", "autosize stands down after a drag");
  // Cancel resets it: the next comment autosizes again
  h.click('[data-act="fccancel"]');
  assert.equal(box.style.height, "");
  h.click('[data-act="fcfile"]');
  type("one\ntwo", 63);
  assert.equal(box.style.height, "65px", "autosize is back for the next comment");
  h.dispose();
});

test("the draft survives the poll's re-render and a refusal: the same node, its text, its caret, its height and the keyboard", async () => {
  const h = await harness();
  await h.open();
  h.click('[data-act="fcfile"]');
  const box = h.box();
  box.value = "Line one.\nLine two.";
  box.setSelectionRange(5, 5);
  box.scrollHeight = 63; box.offsetHeight = 65; box.clientHeight = 63; box.dispatch("input");
  assert.equal(box.style.height, "65px");
  // a save elsewhere re-asks status; the status lands; the panel re-renders every section
  h.saved[0]({ mtimeNs: "9", logged: true });
  await tick();
  assert.equal(h.last().verb, "status");
  await h.ok();
  assert.equal(h.box(), box, "the same textarea node: the composer's parts persist across render()");
  assert.equal(box.value, "Line one.\nLine two.", "the text");
  assert.deepEqual([box.selectionStart, box.selectionEnd], [5, 5], "the caret");
  assert.equal(box.style.height, "65px", "the height");
  assert.equal(doc.activeElement, box, "the keyboard");
  // the host refuses the save: the note is never discarded
  h.chord(); await tick();
  assert.equal(h.last().verb, "comment");
  assert.equal(h.last().args.note, "Line one.\nLine two.");
  await h.refuse("anchor-not-found", "the passage was not found in the file as it is now");
  assert.equal(h.q(".fc-composer")!.hidden, false, "still open");
  assert.equal(box.value, "Line one.\nLine two.", "the words stay where they were typed");
  assert.equal(box.style.height, "65px");
  assert.equal(box.readOnly, false, "the round trip is over: the box takes typing again");
  const err = h.q(".fc-composer .fc-err")!;
  assert.ok(err, "the refusal sits under the box");
  assert.ok(err.textContent.includes("the passage was not found in the file as it is now"), err.textContent);
  assert.equal(h.q('[data-act="fcsave"]')!.textContent, "Save");
  h.dispose();
});

test("a refused mapping offers no Save and no hint — Switch to Raw and Cancel — and the chord refuses in words, the text kept", async () => {
  const SRC_MD = "# Report\n\nIntro text here.\n";
  const html = (marked.parse(SRC_MD) as string) + '<p><img src="figures/p95.png" alt="Latency chart"></p>';   // a picture the source holds no embed for
  const h = await harness({ src: SRC_MD, html });
  await h.open({ store: null, storeMtimeNs: null, unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null } });
  const img = h.body.querySelector("img")!;
  img.dispatch("click");
  const float = h.float();
  assert.equal(float.hidden, false, "the picture click offers Comment");
  float.dispatch("click");
  assert.equal(h.q(".fc-composer")!.hidden, false);
  assert.match(h.q(".fc-composer-ref .fc-refused")!.textContent, /not found in the source/);
  assert.ok(h.q('.fc-composer [data-act="fcraw"]'), "Switch to Raw");
  assert.equal(h.q('.fc-composer [data-act="fcsave"]'), null, "no Save under a refusal");
  assert.equal(h.q(".fc-composer .fc-hint"), null, "…and no hint about saving");
  assert.ok(h.q('.fc-composer [data-act="fccancel"]'), "Cancel stays");
  const box = h.box();
  box.value = "Use the p99 chart.\nAnd label the axis.";
  const before = h.posted.length;
  h.chord(); await tick();
  assert.equal(h.posted.length, before, "nothing was posted");
  assert.match(h.q(".fc-composer .fc-err")!.textContent, /^Nothing saved: /);
  assert.equal(box.value, "Use the p99 chart.\nAnd label the axis.", "the text survives the refusal");
  h.dispose();
});

// ── bodies with line breaks ────────────────────────────────────────────────────────────────────────

test("a card renders a two-line body with its break; the collapsed preview and the Log's list fold it to one line", async () => {
  const two: StoreComment = { ...passage, id: T0 + "-119", body: "Which cache?\nSay which." };
  // the same comment after a send: the Log's entry carries the body as it went, break included
  const log: LogEntry[] = [{ ts: "2026-09-06T08:05:00.000Z", kind: "send", author: "you", sid: SID, sessionName: "api", accepted: 0, rejected: 0, queued: false, watermark: T0,
    comments: [{ id: two.id, desc: 'on "shipping the cache in v1.2"', body: two.body }] }];
  const h = await harness();
  const over: Partial<Status> = {
    store: { v: 3, path: "docs/report.md", suggestions: [], comments: [two] },
    unsent: { comments: [two.id], replies: [], accepted: 0, rejected: 0, watermark: null },
    log,
  };
  await h.open(over);
  const card = h.q('.fc-card[data-id="' + two.id + '"]')!;
  assert.equal(card.querySelector(".fc-preview")!.textContent, "Which cache? Say which.", "the glance is one line");
  h.click('.fc-card[data-id="' + two.id + '"] .fc-card-head');
  const body = h.q('.fc-card[data-id="' + two.id + '"] .fc-body')!;
  assert.equal(body.textContent, "Which cache?\nSay which.", "the open card holds the body verbatim, break included");
  // the Log's list: one click down, the send's item holds the body verbatim in one span — the break is in the text,
  // not split into lines — and the sheet's nowrap is what folds the item to one line (the desc, then the first line)
  h.click('[data-act="fclog"]');
  h.click('[data-act="fclogrow"]');
  const items = h.qa(".fc-log-detail .fc-list li");
  assert.equal(items.length, 1, "the one comment the send carried");
  assert.equal(items[0].textContent, 'on "shipping the cache in v1.2": Which cache?\nSay which.', "the desc, then the body as it went, break included");
  assert.deepEqual(items[0].childNodes.map((c) => (c as E).tagName + ":" + (c as E).className), ["SPAN:fc-list-desc", "SPAN:"], "two spans, no line split: the fold is the sheet's");
  assert.equal(items[0].childNodes[1].textContent, "Which cache?\nSay which.", "the body span keeps the break");
  // the sheets: pre-wrap on .fc-body keeps a card's break on screen; nowrap on .fc-list li folds the Log's item — both pages' sheets
  for (const [name, css] of [["styles.css", CHAT_CSS], ["feed.css", FEED_CSS]] as const) {
    assert.match(css, /\n\.fc-body \{ font-size: 0\.86em; white-space: pre-wrap; overflow-wrap: anywhere; cursor: text; \}\n/, name + ": .fc-body wraps and keeps its breaks");
    assert.match(css, /\n\.fc-list li \{ margin: 2px 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; \}\n/, name + ": .fc-list li folds to one line with an ellipsis");
  }
  h.dispose();
});

// ── pinned at source: the box, the chord, the delegate action, the sheets, the docs ───────────────

test("source: the box is a textarea of NOTE_ROWS rows; keydown goes through composerKeyAction; input autosizes; Save is the delegate's fcsave; the hint rides the platform", () => {
  assert.match(SRC, /input = el\("textarea", "fc-input"\) as HTMLTextAreaElement;/);
  assert.doesNotMatch(SRC, /el\("input", "fc-input"\)/, "the one-line input is gone");
  assert.doesNotMatch(SRC, /this\.input\.type = "text";/);
  assert.match(SRC, /this\.input\.rows = NOTE_ROWS;\n\s*this\.input\.placeholder = "Your comment";/);
  assert.match(SRC, /const act = composerKeyAction\(e\);\n\s*if \(act === "save"\) \{ e\.preventDefault\(\); void this\.saveComposer\(\); \}\n\s*else if \(act === "cancel"\) \{ e\.preventDefault\(\); e\.stopPropagation\(\); this\.closeComposer\(\); \}/,
    "the chord saves, Escape cancels and stops there, a plain Enter is left to the textarea");
  assert.match(SRC, /this\.input\.addEventListener\("input", \(\) => this\.autosize\(\)\);/);
  assert.match(SRC, /if \(this\.sizedTo !== null && ta\.style\.height !== this\.sizedTo\) return;/, "a dragged height stands");
  assert.match(SRC, /this\.input\.style\.height = ""; this\.sizedTo = null;/, "closeComposer resets the height with the words");
  assert.match(SRC, /fcsave: \(\) => \{ void this\.saveComposer\(\); \},/, "Save is a delegated action on the panel's one root (click-safe, flash())");
  assert.match(SRC, /const hint = el\("span", "fc-note fc-hint", composerHint\(IS_MAC\)\);\n\s*acts\.replaceChildren\(\.\.\.\(noSave \? \[\] : \[hint, save\]\), btn\("Cancel", "fccancel"\)\);/);
  assert.match(SRC, /const note = this\.input\.value\.trim\(\);/, "the blank ends go, the breaks inside stay");
  // the platform rule is the editor's, character for character
  const rule = '/Mac|iP(?:hone|ad|od)/.test(navigator.platform || "")';
  assert.ok(SRC.includes('const IS_MAC = typeof navigator !== "undefined" && ' + rule + ";"), "the panel's IS_MAC");
  assert.ok(TRACK.includes('const IS_MAC = typeof navigator !== "undefined" && ' + rule + ";"), "…is track-decorations.ts's, the same test");
  assert.doesNotMatch(SRC, /Enter saves, Esc cancels/, "the old placeholder is gone");
});

test("the sheets: the box rule says textarea — resize, a floor of NOTE_ROWS and a cap of NOTE_MAX_ROWS rows — and the hint rule exists, byte-equal in both", async () => {
  const { NOTE_ROWS, NOTE_MAX_ROWS } = await import("./file-comments");
  const rule = (css: string, head: string): string => { const a = css.indexOf("\n" + head); assert.ok(a >= 0, head); return css.slice(a + 1, css.indexOf("}", a) + 1); };
  const input = rule(CHAT_CSS, ".fc-input {");
  assert.equal(input, rule(FEED_CSS, ".fc-input {"), ".fc-input mirrors byte for byte");
  assert.ok(input.includes("resize: vertical;"), "draggable taller or shorter");
  assert.ok(input.includes("overflow-y: auto;"), "scrolls past the cap");
  assert.ok(input.includes("line-height: 1.4;"), "one row is 1.4em, which the floor and the cap count in");
  assert.ok(input.includes("min-height: calc(" + NOTE_ROWS + " * 1.4em + 12px);"), "the floor is NOTE_ROWS rows plus padding and border");
  assert.ok(input.includes("max-height: calc(" + NOTE_MAX_ROWS + " * 1.4em + 12px);"), "the cap is NOTE_MAX_ROWS rows plus padding and border");
  assert.ok(input.includes("padding: 5px 8px;") && input.includes("border: 1px solid var(--box-border);") && input.includes("box-sizing: border-box;"), "5+5 padding and 1+1 border are the 12px");
  assert.ok(input.includes("width: 100%;"), "full panel width");
  assert.equal(rule(CHAT_CSS, ".fc-hint {"), rule(FEED_CSS, ".fc-hint {"));
  assert.ok(rule(CHAT_CSS, ".fc-hint {").includes("margin-right: auto;"), "the hint takes the row's left, the buttons keep the right");
});

test("docs: the guide says Enter adds a line and names the chord and Save; the plan's bullet is multi-line and the follow-on note is there", () => {
  const flat = (t: string) => t.replace(/\s+/g, " ");
  const files = flat(GUIDE.slice(GUIDE.indexOf("### Files"), GUIDE.indexOf("## Automatic nudges")));
  assert.ok(files.includes("Enter adds a line"), "the guide: Enter adds a line");
  assert.ok(files.includes("**Cmd+Enter**") && files.includes("**Ctrl+Enter**") && files.includes("**Save**"), "the guide names both chords and the button");
  assert.ok(!files.includes("type the note and press Enter"), "the one-line sentence is gone");
  const bullet = flat(PLAN.slice(PLAN.indexOf("- **Comment on a selection**"), PLAN.indexOf("- **Send to session**")));
  assert.ok(!bullet.includes("one-line composer"), "the plan's bullet no longer says one-line");
  assert.ok(bullet.includes("multi-line composer"), "…it says multi-line");
  assert.ok(bullet.includes("Cmd+Enter") && bullet.includes("Ctrl+Enter") && bullet.includes("Enter adds a line"), "…and names the chord and the newline");
  assert.ok(PLAN.includes("The composer follow-on (2026-09-07)"), "the follow-on note beside the Slice 2 build note");
  const note = flat(PLAN.slice(PLAN.indexOf("The composer follow-on (2026-09-07)"), PLAN.indexOf("### Slice 3: region comments on images")));
  for (const phrase of ["three rows", "twelve", "Enter adds a line", "Escape cancels", "never discarded", "verbatim"]) assert.ok(note.includes(phrase), "the note says: " + phrase);
});
