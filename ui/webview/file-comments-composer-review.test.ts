// The Comments panel's composer after the 2026-09-07 review of the multi-line box (plans/file-review.md, "The composer
// follow-on (2026-09-07)"): two findings, both in file-comments.ts. (1) A height the person dragged BEFORE the first
// keystroke was undone by that keystroke: autosize() told a drag from its own sizing by comparing the box's inline
// height with the one it last set, and before the first input it had set none, so the guard never ran and the box
// snapped back to its content — the plan says a dragged height stands until the composer closes. (2) On a coarse
// pointer the hint under the box named a chord (Cmd+Enter, Ctrl+Enter) a soft keyboard cannot press, and nothing in
// the composer's copy said Save is the way now that Return adds a line; the hint names the button there, read at each
// render as the decide-in-editor words are. Driven through the same DOM stand-in file-comments-composer.test.ts uses
// (there is no jsdom in this tree), with a matchMedia the test toggles for the primary pointer. Synthetic fixtures
// only: the notes-api world, placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx, TrackedEdit } from "./file-view";
import type { Status, StoreComment } from "./file-comments-model";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const SRC = web("file-comments.ts");

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
/** The primary pointer a test claims: null leaves matchMedia absent (a desktop without it); true is a finger. */
let coarse: boolean | null = null;
win.matchMedia = (q: string) => { if (coarse === null) throw new TypeError("matchMedia is not a function"); return { matches: q === "(pointer: coarse)" && coarse }; };
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
    post: (m) => { posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: noop, editing: () => false, setTrackedEdit: (t) => { tracked.push(t); }, guardClose: noop,
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

// ── the hint on a coarse pointer ───────────────────────────────────────────────────────────────────

test("composerHint: the platform's chord with a keyboard, the button on a coarse pointer; the default reads the device at each call", async () => {
  const { composerHint, COMPOSER_HINT_TOUCH, saveChord } = await import("./file-comments");
  assert.equal(COMPOSER_HINT_TOUCH, "Enter adds a line; tap Save when done");
  assert.doesNotMatch(COMPOSER_HINT_TOUCH, /\+Enter|Cmd|Ctrl/, "no chord: a soft keyboard has no modifier to hold");
  assert.ok(COMPOSER_HINT_TOUCH.includes("Save"), "the button is named: it is the save path there");
  for (const mac of [true, false]) {
    assert.equal(composerHint(mac, false), saveChord(mac) + " saves; Enter adds a line", "a keyboard: the platform's chord");
    assert.equal(composerHint(mac, true), COMPOSER_HINT_TOUCH, "a finger: the button, whatever the platform (an iPhone's platform reads as Mac)");
  }
  // the default is the device's answer, read when called — never once at import
  try {
    coarse = null;
    assert.equal(composerHint(false), "Ctrl+Enter saves; Enter adds a line", "no matchMedia (a desktop without it): the chord");
    coarse = false;
    assert.equal(composerHint(true), "Cmd+Enter saves; Enter adds a line", "a fine pointer: the chord");
    coarse = true;
    assert.equal(composerHint(true), COMPOSER_HINT_TOUCH, "a coarse pointer: the button");
    assert.equal(composerHint(false), COMPOSER_HINT_TOUCH);
  } finally { coarse = null; }
});

test("on a phone the hint under the box names Save, not a chord, and follows the primary pointer at each render; Return is the newline and Save saves", async () => {
  const h = await harness();
  try {
    coarse = true;
    await h.open();
    h.click('[data-act="fcfile"]');
    const hint = () => h.q(".fc-composer .fc-hint");
    assert.equal(hint()!.textContent, "Enter adds a line; tap Save when done", "an iPhone reads as Mac and Android as Linux: neither chord is named");
    assert.equal(h.q('.fc-composer [data-act="fcsave"]')!.textContent, "Save", "the Save it names is in the same row");
    assert.deepEqual(h.q(".fc-composer .fc-actions")!.childNodes.map((c) => (c as E).className), ["fc-note fc-hint", "fileview-btn", "fileview-btn"], "the row keeps its shape: hint, Save, Cancel");
    // a docked keyboard and trackpad: the next render (the one a landed status brings) says the chord
    coarse = false;
    h.saved[0]({ mtimeNs: "9", logged: true }); await tick();
    assert.equal(h.last().verb, "status");
    await h.ok();
    assert.equal(hint()!.textContent, (MAC ? "Cmd" : "Ctrl") + "+Enter saves; Enter adds a line", "read at each render, never once");
    // back to a finger: the next composer says the button again, and what it says is what happens
    coarse = true;
    h.click('[data-act="fccancel"]');
    h.click('[data-act="fcfile"]');
    assert.equal(hint()!.textContent, "Enter adds a line; tap Save when done");
    const box = h.box();
    box.value = "Trim the intro.";
    const before = h.posted.length;
    const plain = h.key({ key: "Enter" });
    assert.equal(plain.defaultPrevented, false, "Return is the textarea's newline, as the hint says");
    assert.equal(h.posted.length, before, "…and saves nothing");
    h.click('[data-act="fcsave"]'); await tick();
    assert.equal(h.last().verb, "comment");
    assert.equal(h.last().args.note, "Trim the intro.", "the button saves");
    await h.ok();
    assert.equal(h.q(".fc-composer")!.hidden, true);
  } finally { coarse = null; h.dispose(); }
});

test("a refused mapping on a phone offers no hint either: nothing to save, so nothing about saving", async () => {
  const html = "<h1>Report</h1>\n<p>Intro text here.</p>\n" + '<p><img src="figures/p95.png" alt="Latency chart"></p>';   // a picture the source holds no embed for
  const h = await harness({ src: "# Report\n\nIntro text here.\n", html });
  try {
    coarse = true;
    await h.open({ store: null, storeMtimeNs: null, unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null } });
    h.body.querySelector("img")!.dispatch("click");
    h.float().dispatch("click");
    assert.equal(h.q(".fc-composer")!.hidden, false);
    assert.match(h.q(".fc-composer-ref .fc-refused")!.textContent, /not found in the source/);
    assert.equal(h.q('.fc-composer [data-act="fcsave"]'), null, "no Save under a refusal");
    assert.equal(h.q(".fc-composer .fc-hint"), null, "…and no hint, on a phone as on a desktop");
  } finally { coarse = null; h.dispose(); }
});

// ── a drag before the first keystroke ──────────────────────────────────────────────────────────────

test("a height dragged before the first keystroke stands until the composer closes: on the first composer, after a cancel, and after a typed one", async () => {
  const h = await harness();
  await h.open();
  h.click('[data-act="fcfile"]');
  const box = h.box();
  const type = (text: string, scrollHeight: number) => { box.value = text; box.scrollHeight = scrollHeight; box.offsetHeight = scrollHeight + 2; box.clientHeight = scrollHeight; box.dispatch("input"); };
  assert.ok(!box.style.height, "no inline height at first: the sheet's rows and min-height");
  // the drag: the sheet's resize: vertical writes the inline height and fires no input, so autosize has set nothing yet
  box.style.height = "240px";
  type("o", 42);
  assert.equal(box.style.height, "240px", "the first keystroke leaves the dragged height alone");
  type("one\ntwo\nthree\nfour\nfive\nsix\nseven\neight", 168);
  assert.equal(box.style.height, "240px", "…and so does every later one, taller content included");
  type("", 42);
  assert.equal(box.style.height, "240px", "…and an emptied box");
  // Cancel: the height goes with the words, and the next composer autosizes again
  h.click('[data-act="fccancel"]');
  assert.equal(box.style.height, "");
  h.click('[data-act="fcfile"]');
  type("one\ntwo", 63);
  assert.equal(box.style.height, "65px", "autosize is back for the next comment");
  // a drag before typing on a composer opened after one that was typed in and cancelled (sizedTo was set, then cleared)
  h.click('[data-act="fccancel"]');
  h.click('[data-act="fcfile"]');
  assert.equal(box.style.height, "");
  box.style.height = "300px";
  type("one\ntwo", 63);
  assert.equal(box.style.height, "300px", "the drag stands after a cancel and reopen too");
  // a drag AFTER typing still stands (the case the follow-on's own test covers), and a save clears the height with the words
  h.click('[data-act="fccancel"]');
  h.click('[data-act="fcfile"]');
  type("one", 42);
  assert.equal(box.style.height, "44px", "autosized: nothing was dragged");
  box.style.height = "200px";
  type("one\ntwo", 63);
  assert.equal(box.style.height, "200px", "dragged since: stands");
  h.chord(); await tick();
  assert.equal(h.last().verb, "comment");
  await h.ok();
  assert.equal(h.q(".fc-composer")!.hidden, true, "saved: the composer closes");
  assert.equal(box.style.height, "", "…and the height is cleared with the words");
  h.dispose();
});

test("a drag before the first keystroke stands on a reply too (one box for every composer), and a re-render keeps it", async () => {
  const h = await harness();
  await h.open();
  h.click('.fc-card[data-id="' + passage.id + '"] .fc-card-head');
  h.click('[data-act="fcreply"][data-id="' + passage.id + '"]');
  const box = h.box();
  // the reply's box stands in the card it answers, the reference row hidden (the reply follow-on; file-comments-reply-place.test.ts)
  assert.ok(h.q('.fc-card[data-id="' + passage.id + '"] .fc-composer'), "the box stands in the card");
  assert.equal(box.placeholder, "Your reply");
  box.style.height = "180px";
  box.value = "The response cache."; box.scrollHeight = 42; box.offsetHeight = 44; box.clientHeight = 42; box.dispatch("input");
  assert.equal(box.style.height, "180px");
  // the poll's re-render: the same node, the dragged height still on it
  h.saved[0]({ mtimeNs: "9", logged: true }); await tick();
  await h.ok();
  assert.equal(h.box(), box, "the same textarea node");
  assert.equal(box.style.height, "180px", "the dragged height survives the re-render");
  box.value = "The response cache.\nNot the query cache."; box.scrollHeight = 63; box.offsetHeight = 65; box.clientHeight = 63; box.dispatch("input");
  assert.equal(box.style.height, "180px", "…and the next keystroke");
  h.dispose();
});

// ── pinned at source ───────────────────────────────────────────────────────────────────────────────

test("source: autosize has two guards — a drag before the first keystroke, a drag since — and the hint reads the device by default, per render", () => {
  assert.match(SRC, /if \(this\.sizedTo === null && ta\.style\.height\) return;/, "a drag before the first keystroke: sizedTo is null and the box has an inline height autosize never set");
  assert.match(SRC, /if \(this\.sizedTo !== null && ta\.style\.height !== this\.sizedTo\) return;/, "a drag since: the inline height is not the one autosize last set");
  assert.match(SRC, /export const COMPOSER_HINT_TOUCH = "Enter adds a line; tap Save when done";/);
  assert.match(SRC, /export function composerHint\(mac: boolean, touch: boolean = isCoarsePointer\(\)\): string \{\n\s*return touch \? COMPOSER_HINT_TOUCH : saveChord\(mac\) \+ " saves; Enter adds a line";\n\}/,
    "the device's answer by default, read at the call");
  assert.match(SRC, /const hint = el\("span", "fc-note fc-hint", composerHint\(IS_MAC\)\);/, "built in renderComposer, so the device is read at each render (a tablet docks to a keyboard)");
  assert.match(SRC, /import \{[^}]*\bisCoarsePointer\b[^}]*\} from "\.\/file-comments-regions";/, "the one coarse-pointer test the panel uses (the region overlays, the decide-in-editor words)");
});
