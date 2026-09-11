// The comment box's save chord against the CHAT pane's own window-capture listener (plans/file-review.md, "The composer
// follow-on (2026-09-07)"; the 2026-09-07 review, round 3). render.ts runs the chat's history keys, chat.navBack and
// chat.navForward, from a keydown listener on the WINDOW in the capture phase, added when render.ts loads and reading the
// same overrides store the shell's dispatcher does; Ctrl+Enter and Meta+Enter are bindable to either (keybindings.ts
// bindable, and the shortcuts dialog names a conflict only with another shell command). The claim that keeps the box's
// chord from the shell's document-capture dispatcher (file-comments-composer-shell-chord.test.ts) sat on the same window in
// the same phase, added when the panel was built — after render.ts's — and listeners on one target in one phase run in the
// order they were added, stopPropagation stopping none of them: with chat.navBack bound to Ctrl+Enter, the chord in the box
// navigated the chat back one step (the session switched under the open viewer) AND saved. The claim is now ONE listener
// for the module (claimSaveChord), added when file-comments.ts loads — a static dependency of render.ts, so before
// render.ts's body runs — keyed on the live panel, and it stops the event with stopImmediatePropagation, which stops every
// later listener on the window. Four legs: the shape at source; the order in render.js as the webview build bundles it;
// the claim driven through the panel tests' DOM stand-in (node's EventTarget stands in for the window) against a listener
// shaped like render.ts's, added after the module as render.ts's is; and the order itself in headless Chromium and Firefox
// with the real panel — which skips LOUDLY without a playwright browser (CI installs none). The stand-in is the panel tests'
// (copied, as each of them carries it; there is no jsdom in this tree). Synthetic fixtures only: the notes-api world,
// placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inspect } from "node:util";
import { hideEdges, staysEnumerable } from "../test-dom-shim";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import type { FileViewActionCtx, TrackedEdit } from "./file-view";
import type { Status, StoreComment } from "./file-comments-model";
import { chordOf, effectiveChord, type Bindings } from "./keybindings";
import { DEFAULT_CHORDS } from "./commands";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const SRC = web("file-comments.ts");
const RENDER = web("render.ts");
const FILE_VIEW = web("file-view.ts");
const FEED_TS = web("feed.ts");
const FEED = web("feed.css");

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
// node's EventTarget reads a boolean third argument on add but not on remove (node 22: a listener added with `true` is not
// found by a remove with `true`), where a browser reads both as { capture }. The stand-in gives the boolean the browser's
// meaning. Every keydown listener added to the window is also recorded with its phase, so a test can say what the module
// added at import and what came after it.
const added: Array<{ type: string; capture: boolean; fn: EventListener }> = [];
{
  const add = win.addEventListener.bind(win), rm = win.removeEventListener.bind(win);
  const opt = (o: unknown): { capture?: boolean } | undefined => (typeof o === "boolean" ? { capture: o } : (o as { capture?: boolean } | undefined));
  win.addEventListener = (type: string, fn: EventListener, o?: unknown) => { const c = opt(o); added.push({ type, capture: !!(c && c.capture), fn }); add(type, fn, c); };
  win.removeEventListener = (type: string, fn: EventListener, o?: unknown) => rm(type, fn, opt(o));
}
(globalThis as any).document = doc;
(globalThis as any).fetch = async () => ({ status: 404, headers: { get: () => null }, json: async () => [] });
const realSetInterval = globalThis.setInterval;
(globalThis as any).setInterval = (fn: () => void, ms: number) => { const t = realSetInterval(fn, ms); (t as any).unref?.(); return t; };
const tick = () => new Promise<void>((r) => setImmediate(r));

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



// ── the chat's history listener, as render.ts adds it: on the window, capture, after this module's ─
/** render.ts's listener with navHist.go replaced by a record: the same reads (chordOf, effectiveChord, DEFAULT_CHORDS),
 *  the overrides handed in where render.ts calls loadOverrides() (localStorage, which node has none of). A test adds it to
 *  the window AFTER file-comments.ts was imported, as render.ts's body runs after its dependencies' bodies. */
function chatHistoryListener(overrides: Bindings, went: number[]): EventListener {
  return ((e: KeyboardEvent) => {
    if (!e.ctrlKey && !e.metaKey) return;
    const ch = chordOf(e);
    if (!ch || !ch.includes("+")) return;
    const mac = /Mac|iP(hone|ad|od)/.test((typeof navigator !== "undefined" && navigator.platform) || "");
    if (ch === effectiveChord("chat.navBack", DEFAULT_CHORDS["chat.navBack"], overrides, mac)) { e.preventDefault(); e.stopPropagation(); went.push(-1); }
    else if (ch === effectiveChord("chat.navForward", DEFAULT_CHORDS["chat.navForward"], overrides, mac)) { e.preventDefault(); e.stopPropagation(); went.push(1); }
  }) as EventListener;
}
/** The rebind the scenario needs: both history keys on the box's chords, one modifier each. */
const REBOUND: Bindings = { "chat.navBack": "Ctrl+Enter", "chat.navForward": "Meta+Enter" };

/** A keydown as the window's capture listeners first meet it: the target as an own property over node's getter (which
 *  would otherwise name the window), the key and modifiers as the event's own fields; every modifier present, as a
 *  KeyboardEvent's are, since chordOf reads them all. */
function atWindow(target: N, init: Init): Event & Init {
  const ev = Object.assign(new Event("keydown", { cancelable: true }), { ctrlKey: false, altKey: false, shiftKey: false, metaKey: false }, init) as Event & Init;
  Object.defineProperty(ev, "target", { value: target, configurable: true });
  win.dispatchEvent(ev);
  return ev;
}

// ── pinned at source: one listener for the module, added at load, keyed on the live panel ─────────

test("source: the claim is a module function added to the window once, when the module loads, keyed on `live`; it stops every later listener; no panel adds or removes one", () => {
  assert.match(SRC, /\nfunction claimSaveChord\(ev: KeyboardEvent\): void \{\n\s*const p = live;\n\s*if \(!p \|\| composerKeyAction\(ev\) !== "save"\) return;\n\s*if \(ev\.target === p\.input\) \{ ev\.stopImmediatePropagation\(\); p\.boxKey\(ev\); \}\n\s*else if \(ev\.target === p\.noteBox\) \{ ev\.stopImmediatePropagation\(\); p\.noteKey\(ev\); \}[^\n]*\n\}\n/,
    "the live panel's box as target and the save verdict, or nothing; then the event stops short of every other listener on the window and boxKey saves");
  assert.match(SRC, /^if \(typeof window !== "undefined"\) window\.addEventListener\("keydown", claimSaveChord, true\);$/m,
    "added at the module's top level — when it loads, before render.ts's body — on the window, capture");
  assert.equal((SRC.match(/addEventListener\("keydown", claimSaveChord/g) || []).length, 1, "once");
  assert.doesNotMatch(SRC, /this\.claimSaveChord/, "no per-panel copy: none added in the constructor, none removed in dispose");
  assert.doesNotMatch(SRC, /removeEventListener\("keydown", claimSaveChord/, "the module's listener lives with the module");
  assert.match(SRC, /if \(live === this\) live = null;/, "dispose retires the claim for its box by clearing `live`");
  assert.match(SRC, /this\.input\.addEventListener\("keydown", this\.boxKey\);/, "the box's own listener still takes Escape at the target");
});

test("source: render.ts runs the chat's history keys from a window-capture listener, and this module is a static dependency of render.ts, so its listener is added first", () => {
  // the listener the claim precedes: on the window, capture phase, matching the two history commands from the overrides store
  const nav = /window\.addEventListener\("keydown", \(e\) => \{\n\s*if \(!e\.ctrlKey && !e\.metaKey\) return;[^]*?effectiveChord\("chat\.navBack"[^]*?navHist\.go\(-1\);[^]*?effectiveChord\("chat\.navForward"[^]*?navHist\.go\(1\);\n\s*\}\n\}, true\);/;
  assert.match(RENDER, nav, "the chat's history listener: window, capture, both commands read from the store per press");
  // the static chain that puts this module's body before render.ts's: value imports at the top level, never import()
  assert.match(RENDER, /^import \{[^}]*\} from "\.\/file-view";$/m, "render.ts imports file-view.ts statically");
  assert.match(RENDER, /^import \{[^}]*\bpanelMark\b[^}]*\} from "\.\/file-comments";$/m, "…and this module directly");
  assert.match(FILE_VIEW, /^import \{[^}]*\bfileCommentsAction\b[^}]*\} from "\.\/file-comments";$/m, "file-view.ts imports this module statically");
  assert.doesNotMatch(RENDER, /import\("\.\/file-(view|comments)"\)/, "neither is a lazy import");
  assert.doesNotMatch(FILE_VIEW, /import\("\.\/file-comments"\)/);
  // the feed's window listeners leave every Ctrl and Meta chord alone: the module's stopImmediatePropagation shadows none of them
  const feedWindowKeys = FEED_TS.match(/window\.addEventListener\("keydown", \(e\) => \{[^]*?\n\}(, true)?\);/g) || [];
  assert.ok(feedWindowKeys.length >= 3, "the feed's window keydown listeners are there to check");
  for (const l of feedWindowKeys) assert.ok(/e\.ctrlKey \|\| e\.metaKey\) return;/.test(l) || /e\.key === "Escape"/.test(l) || /e\.key === "Tab"/.test(l), "a feed window listener yields to chords, or reads only Escape or Tab: " + l.slice(0, 80));
});

// ── the order in the built bundle: file-comments.ts's body, then render.ts's ─────────────────────

const requireCjs = createRequire(__filename);
const pkgRequire = createRequire(path.resolve(process.cwd(), "package.json"));   // npm test runs in vscode-extension
const EXT = process.cwd();
const UI = path.resolve(EXT, "..", "ui", "webview");

test("built: in render.js as the webview build bundles it, the claim's registration precedes the chat's history listener", () => {
  const esbuild = requireCjs("esbuild");
  const { webview } = pkgRequire("./esbuild.js") as { webview: Record<string, unknown> };
  const r = esbuild.buildSync({ ...webview, entryPoints: [path.join(UI, "render.ts")], write: false, sourcemap: false, logLevel: "silent" });
  const out: string = r.outputFiles.find((f: { path: string }) => f.path.endsWith("render.js")).text;
  const claim = out.search(/window\.addEventListener\("keydown", claimSaveChord\d*, true\);/);
  const nav = out.indexOf("navHist.go(-1);");
  assert.ok(claim >= 0, "the module's registration is in the bundle (the guard is not folded away: typeof window is the browser's)");
  assert.ok(nav >= 0, "the chat's listener is in the bundle");
  assert.ok(claim < nav, "the module's body runs first: its listener is the earlier one on the window (" + claim + " < " + nav + ")");
  assert.equal((out.match(/addEventListener\("keydown", claimSaveChord\d*, true\)/g) || []).length, 1, "one registration in the bundle");
});

// ── the claim, driven: the module adds its listener at import; a chat listener added after it never sees the box's chord ──

test("at import the module adds one capture keydown listener to the window, before any panel exists; building a panel adds none", async () => {
  const before = added.filter((a) => a.type === "keydown").length;
  assert.equal(before, 0, "nothing on the window before the import");
  await import("./file-comments");
  const atImport = added.filter((a) => a.type === "keydown");
  assert.equal(atImport.length, 1, "one keydown listener, added by the import");
  assert.equal(atImport[0].capture, true, "…in the capture phase");
  const h = await harness();
  await h.open();
  assert.equal(added.filter((a) => a.type === "keydown").length, 1, "the panel added none of its own");
  h.dispose();
});

test("with chat.navBack on Ctrl+Enter and chat.navForward on Meta+Enter: the chord in the box saves and the chat stays put; outside the box the chat navigates; after the viewer closes the chord in what was the box is the chat's again", async () => {
  await import("./file-comments");                                   // this module first, as in the bundle…
  const went: number[] = [];
  const chat = chatHistoryListener(REBOUND, went);
  win.addEventListener("keydown", chat, true);                        // …then render.ts's listener
  try {
    const h = await harness();
    await h.open();
    h.click('[data-act="fcfile"]');
    const box = h.box();
    box.value = "Which cache?\nSay which.  ";
    const before = h.posted.length;
    const ev = atWindow(box, { key: "Enter", ctrlKey: true });
    assert.equal(ev.defaultPrevented, true, "the chord is the box's: no newline goes in with the save");
    assert.equal(ev.cancelBubble, true, "and it goes no further: the shell's document dispatcher never meets it");
    await tick();
    assert.equal(h.posted.length, before + 1, "one save");
    assert.equal(h.last().verb, "comment");
    assert.equal(h.last().args.note, "Which cache?\nSay which.", "the blank tail goes, the break inside stays");
    assert.deepEqual(went, [], "the chat did not navigate: its listener, added after the module's, never ran");
    await h.ok();
    assert.equal(h.q(".fc-composer")!.hidden, true, "saved: the composer closes");
    // the other modifier, bound to the other direction
    h.click('[data-act="fcfile"]');
    box.value = "Lead with the numbers.";
    const mac = atWindow(box, { key: "Enter", metaKey: true });
    assert.equal(mac.defaultPrevented, true);
    await tick();
    assert.equal(h.posted.length, before + 2, "Meta+Enter saves the same");
    assert.equal(h.last().args.note, "Lead with the numbers.");
    assert.deepEqual(went, [], "…and chat.navForward stayed quiet too");
    await h.ok();
    // the person's bindings still work everywhere else: with nothing of ours focused, and in another text field
    atWindow(doc.body, { key: "Enter", ctrlKey: true });
    atWindow(doc.body, { key: "Enter", metaKey: true });
    assert.deepEqual(went, [-1, 1], "outside the box the chat navigates back, then forward");
    const other = doc.createElement("textarea"); doc.body.appendChild(other);
    atWindow(other, { key: "Enter", ctrlKey: true });
    assert.deepEqual(went, [-1, 1, -1], "another text field's Ctrl+Enter is the chat's: the claim is the comment box's alone");
    other.remove();
    await tick();
    assert.equal(h.posted.length, before + 2, "nothing more saved");
    // the viewer closes: the claim is no longer this box's, and the chord there is the chat's again
    h.click('[data-act="fcfile"]');
    box.value = "Late.";
    h.dispose();
    const late = atWindow(box, { key: "Enter", ctrlKey: true });
    assert.equal(late.cancelBubble, true, "stopped by the chat's listener this time, not the claim");
    assert.deepEqual(went, [-1, 1, -1, -1], "a disposed panel's box is no longer claimed");
    await tick();
    assert.equal(h.posted.length, before + 2, "…and it saves nothing");
  } finally { win.removeEventListener("keydown", chat, true); }
});

test("the order is the mechanism: a claim added after the chat's listener does not stop it, with stopPropagation or stopImmediatePropagation (the shape the panel had)", async () => {
  await import("./file-comments");
  const went: number[] = [];
  const chat = chatHistoryListener(REBOUND, went);
  win.addEventListener("keydown", chat, true);
  const calls: string[] = [];
  const box1 = doc.createElement("textarea"), box2 = doc.createElement("textarea");
  doc.body.appendChild(box1); doc.body.appendChild(box2);
  // the panel's old claim, on the window in the capture phase but added when the panel was built: after render.ts's
  const lateStop = ((e: KeyboardEvent) => { if ((e.target as unknown) !== box1 || e.key !== "Enter" || !(e.ctrlKey || e.metaKey)) return; e.stopPropagation(); calls.push("late-stop:save"); }) as EventListener;
  const lateImmediate = ((e: KeyboardEvent) => { if ((e.target as unknown) !== box2 || e.key !== "Enter" || !(e.ctrlKey || e.metaKey)) return; e.stopImmediatePropagation(); calls.push("late-immediate:save"); }) as EventListener;
  win.addEventListener("keydown", lateStop, true);
  win.addEventListener("keydown", lateImmediate, true);
  try {
    atWindow(box1, { key: "Enter", ctrlKey: true });
    assert.deepEqual(went, [-1], "the chat navigated: stopPropagation stops no listener on the same target");
    assert.deepEqual(calls, ["late-stop:save"], "…and the late claim ran too: the defect, both at once");
    atWindow(box2, { key: "Enter", ctrlKey: true });
    assert.deepEqual(went, [-1, -1], "stopImmediatePropagation from a LATER listener is too late as well: the chat's had run");
    assert.deepEqual(calls, ["late-stop:save", "late-immediate:save"]);
  } finally {
    win.removeEventListener("keydown", chat, true);
    win.removeEventListener("keydown", lateStop, true);
    win.removeEventListener("keydown", lateImmediate, true);
    box1.remove(); box2.remove();
  }
});

// ── the order itself, in a real browser: the module's listener at load, render.ts's after, the real panel last ─────

/** The panel and the shell's key modules, bundled as the webview build bundles them (in memory), as window.__romp. The
 *  bundle's own load adds the module's listener — before the page adds render.ts's, as render.ts's body runs after this
 *  module's in render.js. */
function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: {
      contents: 'import { fileCommentsAction } from "./file-comments";\nimport { chordOf, effectiveChord, loadOverrides, saveOverride } from "./keybindings";\nimport { DEFAULT_CHORDS } from "./commands";\n(window as any).__romp = { fileCommentsAction, keys: { chordOf, effectiveChord, loadOverrides, saveOverride }, DEFAULT_CHORDS };\n',
      resolveDir: UI, loader: "ts", sourcefile: "composer-chat-nav-chord-probe.ts",
    },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
/** The whole file-comments block of the sheet, as the feed page loads it (styles.css is pinned byte-equal to it). */
function sheet(): string {
  const a = FEED.indexOf("/* ── file comments panel (plans/file-review.md Slice 1; file-comments.ts)");
  const b = FEED.indexOf("/* ── end file comments panel ── */");
  assert.ok(a >= 0 && b > a, "the file-comments block's markers in feed.css");
  return FEED.slice(a, b);
}
// the viewer's row with an empty body, for the real panel to hang its aside on; the tokens the block reads, resolved
const PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8><style>
:root { --box-border: #555; --input-bg: #222; --fg: #ccc; --dim: #999; --accent: #9cd2ff; --card-border: #444; --bg: #1e1e1e; }
body { margin: 0; font: 13px sans-serif; color: var(--fg); background: #1e1e1e; }
.fileview-btn { font: inherit; padding: 2px 8px; }
${sheet()}</style></head><body>
<div id="romp-fileview"><div class="fileview-main" style="height: 600px"><div class="fileview-body"><div class="fileview-md"><p>Intro text here.</p></div></div></div></div>
<script src="/dist/composer.js"></script></body></html>`;
/** The page's side: render.ts's history listener as render.ts adds it (the window, capture, the shell's own decision
 *  functions and the real overrides store — this origin's localStorage, written through saveOverride as the shortcuts
 *  dialog writes it), added after the bundle ran; a box wired the way the panel's claim was BEFORE this change (added after
 *  the chat's, stopPropagation), for the leg's own sensitivity; and the real panel on a stubbed viewer context — the driven
 *  harness's, in the page — with its status asks answered by hand through the window message the host would post. */
const JS = `window.__went = [];
window.__calls = [];
window.__chat = () => {
  const k = window.__romp.keys, D = window.__romp.DEFAULT_CHORDS;
  window.addEventListener("keydown", (e) => {
    if (!e.ctrlKey && !e.metaKey) return;
    const ch = k.chordOf(e);
    if (!ch || !ch.includes("+")) return;
    const mac = /Mac|iP(hone|ad|od)/.test(navigator.platform || "");
    const ov = k.loadOverrides();
    if (ch === k.effectiveChord("chat.navBack", D["chat.navBack"], ov, mac)) { e.preventDefault(); e.stopPropagation(); window.__went.push(-1); }
    else if (ch === k.effectiveChord("chat.navForward", D["chat.navForward"], ov, mac)) { e.preventDefault(); e.stopPropagation(); window.__went.push(1); }
  }, true);
};
window.__bind = (id, chord) => { window.__romp.keys.saveOverride(id, chord); return window.__romp.keys.loadOverrides()[id]; };
window.__late = () => {
  const ta = document.createElement("textarea"); ta.className = "late";
  window.addEventListener("keydown", (e) => {
    if (e.target !== ta || e.key !== "Enter" || !(e.ctrlKey || e.metaKey)) return;
    e.preventDefault(); e.stopPropagation(); window.__calls.push("late:save");
  }, true);
  document.body.appendChild(ta); ta.focus();
};
window.__posted = [];
window.__mount = () => {
  const main = document.querySelector(".fileview-main");
  const body = main.querySelector(".fileview-body");
  let aside = null;
  const noop = () => {};
  const closers = [];
  window.__close = () => { for (const cb of closers) cb(); };
  const ctx = {
    path: "/repo/notes-api/docs/report.md", sid: "11111111-2222-3333-4444-555555555555", todoId: null,
    body: () => body, mode: () => "rendered", text: () => null, mtimeNs: () => "1757145600000000001",
    media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [], identity: () => ({ name: "api", color: null }),
    onRendered: noop, onSelection: noop, onSaved: noop, onClose: (cb) => { closers.push(cb); },
    post: (m) => { window.__posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: noop, editing: () => false, setTrackedEdit: noop, guardClose: noop,
    aside: (el) => { if (el) { el.classList.add("fileview-aside"); aside = el; main.appendChild(el); } else if (aside) { aside.remove(); aside = null; } },
    setMode: noop, scrollToOffset: noop, reload: noop,
  };
  const unit = window.__romp.fileCommentsAction.mount(ctx);
  document.body.appendChild(unit);
  return unit;
};
window.__answer = () => {
  const last = window.__posted[window.__posted.length - 1];
  if (!last || last.verb !== "status") return null;
  window.dispatchEvent(new MessageEvent("message", { data: {
    type: "fileCommentsResult", reqId: last.reqId, verb: "status", root: "/repo/notes-api", storePath: "/repo/notes-api/.trackchanges/docs%2Freport.md.json",
    trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
    store: { v: 3, path: "docs/report.md", suggestions: [], comments: [] }, hunks: [], log: [],
    unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null },
  } }));
  return last.reqId;
};
window.__box = () => {
  const ta = document.querySelector(".fc-panel textarea.fc-input");
  return { value: ta.value, focused: document.activeElement === ta, hidden: ta.closest(".fc-composer").hidden };
};
window.__blur = () => { if (document.activeElement && document.activeElement.blur) document.activeElement.blur(); return document.activeElement === document.body; };`;

type BoxRead = { value: string; focused: boolean; hidden: boolean };
type PagePost = { verb: string; reqId: string; args?: Record<string, unknown> };

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

async function inBrowser(t: any, name: "chromium" | "firefox", body: (page: any) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension — the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw[name].launch(); }
  catch (e) { t.skip("no playwright " + name + " on this box — this leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [];
  try {
    const script = bundle() + "\n" + JS;
    const page = await browser.newPage({ viewport: { width: 1000, height: 900 } });
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    await page.route("http://romp.test/**", (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/page") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE });
      if (u.pathname === "/dist/composer.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: script });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/page");
    await page.waitForFunction(() => !!(window as any).__romp);
    await body(page);
    assert.deepEqual(errors, [], "no script error in the page");
  } finally { await browser.close(); }
}

for (const name of ["chromium", "firefox"] as const) {
  test("in " + name + ": chat.navBack rebound to Ctrl+Enter through the real store, the chat's window listener added after the module's — the chord in the real box saves and the chat stays put; outside the box the chat navigates; a claim added after the chat's loses", async (t) => {
    await inBrowser(t, name, async (page) => {
      const went = (): Promise<number[]> => page.evaluate(() => (window as any).__went.splice(0));
      const calls = (): Promise<string[]> => page.evaluate(() => (window as any).__calls.splice(0));
      const posted = (): Promise<PagePost[]> => page.evaluate(() => (window as any).__posted);
      const box = (): Promise<BoxRead> => page.evaluate(() => (window as any).__box());
      const answer = (): Promise<string | null> => page.evaluate(() => (window as any).__answer());
      await page.evaluate(() => (window as any).__chat());                         // render.ts's listener: after the bundle (this module) ran
      assert.equal(await page.evaluate(() => (window as any).__bind("chat.navBack", "Ctrl+Enter")), "Ctrl+Enter", "the rebind is in the store the listener reads");
      // the shape the panel had, for the leg's own sensitivity: a claim added after the chat's listener stops nothing of it
      await page.evaluate(() => (window as any).__late());
      await page.keyboard.type("late");
      await page.keyboard.press("Control+Enter");
      assert.deepEqual(await went(), [-1], "the chat navigated: same target, same phase, registration order");
      assert.deepEqual(await calls(), ["late:save"], "…and the late claim ran as well: both at once, the defect");
      // the real panel, mounted last as a pane's panel always is
      await page.evaluate(() => (window as any).__mount());
      assert.ok(await answer(), "the probe's status ask, answered");
      await page.click(".fileview-fc button");                                              // Comments: the panel opens
      assert.ok(await answer(), "the open's status ask, answered");
      await page.click('.fc-panel [data-act="fcfile"]');                                    // Comment on this file
      const b0 = await box();
      assert.equal(b0.hidden, false, "the composer is open");
      assert.ok(b0.focused, "the box has the keyboard");
      await page.keyboard.type("Which cache?\nSay which.");
      assert.equal((await box()).value, "Which cache?\nSay which.", "Enter added the line");
      const n0 = (await posted()).length;
      await page.keyboard.press("Control+Enter");
      const after = await posted();
      assert.equal(after.length, n0 + 1, "one save");
      assert.equal(after[after.length - 1].verb, "comment");
      assert.deepEqual(after[after.length - 1].args, { note: "Which cache?\nSay which." }, "the whole-file comment, the typed text");
      assert.deepEqual(await went(), [], "the chat stayed put: the module's listener, added at load, stopped the event before render.ts's");
      assert.equal((await box()).value, "Which cache?\nSay which.", "no line went in with the chord");
      // the same chord with nothing of ours focused is the chat's, as before
      assert.ok(await page.evaluate(() => (window as any).__blur()), "focus left the box");
      await page.keyboard.press("Control+Enter");
      assert.deepEqual(await went(), [-1], "outside the box the person's binding navigates");
      assert.equal((await posted()).length, n0 + 1, "…and nothing more is saved");
      // the viewer closes: the claim is no longer this box's, and the chord in a text field is the chat's again
      await page.evaluate(() => (window as any).__close());
      await page.evaluate(() => (window as any).__late());
      await page.keyboard.press("Control+Enter");
      assert.deepEqual(await went(), [-1], "after dispose the chat's listener meets the chord first again");
    });
  });
}

// The stand-in's nodes inspect as their own projection, never as the tree: every edge (parentNode, childNodes, the
// attribute map, the listener table, style, dataset, classList) is non-enumerable, so a failing assertion's dump of a
// node is a few lines, not the whole document (ui/test-dom-shim.ts says why; ui/test-dom-shim.test.ts keeps the ratchet).
test("stand-in: a node enumerates its primitives alone and inspects without its edges", () => {
  const root = doc.createElement("div");
  const kid = root.appendChild(doc.createElement("span"));
  kid.appendChild(doc.createTextNode("leaf"));
  kid.setAttribute("data-id", "k1");
  for (const n of [root, kid, kid.firstChild!]) {
    const o = n as unknown as Record<string, unknown>;
    assert.ok(Object.keys(o).every((k) => staysEnumerable(o[k])), "only primitives enumerate on " + n.constructor.name + ": " + Object.keys(o).join(","));
    const dump = inspect(n, { compact: false, customInspect: false, depth: 1000, maxArrayLength: Infinity, showHidden: false, showProxy: false, sorted: true, getters: true });
    assert.ok(!dump.includes("parentNode") && !dump.includes("childNodes"), "no edge in the dump of " + n.constructor.name);
  }
  assert.equal(kid.parentNode, root); assert.equal(root.childNodes.length, 1); assert.equal(kid.textContent, "leaf");
});
