// The comment box's save chord against the shell's keyboard dispatcher (plans/file-review.md, "The composer follow-on
// (2026-09-07)"; the 2026-09-07 review). The combined shell runs every bound chord from palette-main.ts's onKey, a CAPTURE
// listener on the shell document and on every pane document, wired when the pane loads; a chord with a real modifier
// dispatches while typing (keybindings.ts dispatchable), Ctrl+Enter and Meta+Enter are bindable there (bindable), and the
// shortcuts dialog names a conflict only with another shell command (conflictOf). So a person who bound a command to
// Ctrl+Enter, then typed a comment and pressed the chord the hint under the box names, got the command: the dispatcher
// stopped the event before the box's own listener, nothing saved, and the Save button was the only way out. The panel now
// claims the chord at the WINDOW in the capture phase while the live panel's box is the key's target (claimSaveChord, one
// listener the module adds when it loads, keyed on `live`): the DOM's phase order puts a window listener ahead of a document
// one whoever registered first, so the chord typed in the box is the box's, as a bare Enter is (the shell refuses to bind
// that). Three legs: the shell's rule as its pure module states it, the claim driven through the panel tests' DOM stand-in
// (node's EventTarget stands in for the window), and the order itself in headless Chromium and Firefox — the shell's own
// decision functions wired as its dispatcher is, ahead of the real panel — which skips LOUDLY without a playwright browser
// (CI installs none). Synthetic fixtures only: the notes-api world, placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import type { FileViewActionCtx, TrackedEdit } from "./file-view";
import type { Status, StoreComment } from "./file-comments-model";
import { bindable, conflictOf, dispatchable, chordMap } from "./keybindings";
import { DEFAULT_CHORDS } from "./commands";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const SRC = web("file-comments.ts");
const PALETTE = web("palette-main.ts");
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
(globalThis as any).window = win;
// node's EventTarget reads a boolean third argument on add but not on remove (node 22: a listener added with `true` is not
// found by a remove with `true`), where a browser reads both as { capture }. The stand-in gives the boolean the browser's
// meaning: the claim is added and removed in that form, as the panel's other capture listeners are, and the browser leg
// below sees the real removal.
{
  const add = win.addEventListener.bind(win), rm = win.removeEventListener.bind(win);
  const opt = (o: unknown) => (typeof o === "boolean" ? { capture: o } : o);
  win.addEventListener = (type: string, fn: EventListener, o?: unknown) => add(type, fn, opt(o));
  win.removeEventListener = (type: string, fn: EventListener, o?: unknown) => rm(type, fn, opt(o));
}
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


// ── the shell's rule, as keybindings.ts states it: the exposure the claim answers ──────────────────

test("the shell lets a command take Ctrl+Enter or Meta+Enter, names no conflict for it, and dispatches either while typing; no default holds one", () => {
  const cmds = [{ id: "palette.toggle", chord: "Mod+P" }, { id: "session.jump", chord: "Mod+O" }];
  for (const chord of ["Ctrl+Enter", "Meta+Enter"]) {
    assert.equal(bindable(chord), true, chord + " records in the shortcuts dialog");
    assert.equal(conflictOf(chord, "palette.toggle", cmds, {}, false), null, chord + ": the dialog names no conflict — the box is not a shell command");
    assert.equal(conflictOf(chord, "palette.toggle", cmds, {}, true), null);
  }
  assert.equal(bindable("Enter"), false, "a bare Enter the shell refuses: the panes own it — the box's chord gets the same standing from the claim");
  assert.equal(dispatchable({ ctrlKey: true, altKey: false, metaKey: false }, true), true, "a Ctrl chord dispatches while typing");
  assert.equal(dispatchable({ ctrlKey: false, altKey: false, metaKey: true }, true), true, "…and a Meta chord");
  assert.equal(chordMap(cmds, { "palette.toggle": "Ctrl+Enter" }, false).get("Ctrl+Enter"), "palette.toggle", "the override lands in the dispatcher's map");
  assert.ok(!Object.values(DEFAULT_CHORDS).some((c) => /\+Enter$/.test(c)), "no default chord ends in Enter: the exposure takes a deliberate rebind");
});

// ── pinned at source: the claim, its life, and the dispatcher it precedes ─────────────────────────

test("source: the box's keys are one handler; the claim is the module's one window-capture listener, keyed on the live panel, and takes only its box's save chord; the shell's dispatcher is the document-capture listener it precedes", () => {
  assert.match(SRC, /this\.input\.addEventListener\("keydown", this\.boxKey\);/, "the box's own listener is the named handler the claim hands the chord to");
  // One listener for the module, added when it loads and reading `live` — not one per panel: a per-panel claim added in the
  // constructor ran AFTER the chat pane's window-capture history keys (the 2026-09-07 review); the full shape of the
  // function, its stopImmediatePropagation and dispose's `live = null` are pinned where that finding lives,
  // file-comments-composer-chat-nav-chord.test.ts.
  assert.match(SRC, /^if \(typeof window !== "undefined"\) window\.addEventListener\("keydown", claimSaveChord, true\);$/m, "on the window, capture, added when the module loads");
  assert.match(SRC, /\nfunction claimSaveChord\(ev: KeyboardEvent\): void \{\n\s*const p = live;\n\s*if \(!p \|\| ev\.target !== p\.input \|\| composerKeyAction\(ev\) !== "save"\) return;/,
    "the live panel's box as target and the save verdict, or nothing");
  assert.doesNotMatch(SRC, /this\.claimSaveChord/, "no per-panel copy: none added in the constructor, none removed in dispose");
  assert.match(SRC, /boxKey = \(e: KeyboardEvent\) => \{\n\s*if \(e\.key === "Escape"\) e\.stopPropagation\(\);\n\s*const act = composerKeyAction\(e\);\n\s*if \(act === "save"\) \{ e\.preventDefault\(\); void this\.saveComposer\(\); \}/);
  // the shell's side: a capture listener on each pane document, wired at pane load, that stops the event before the command
  assert.match(PALETTE, /f\.contentDocument\.addEventListener\("keydown", onKey, true\)/, "the shell dispatches from a capture listener on each pane document");
  assert.match(PALETTE, /document\.addEventListener\("keydown", onKey, true\);/);
  assert.match(PALETTE, /e\.preventDefault\(\); e\.stopPropagation\(\);\n\s*palette\.close\(\);[^\n]*\n\s*runCommand\(id\);/, "…and stops the event before running the command, so a target-phase listener never sees it");
  assert.match(PALETTE, /if \(!dispatchable\(e, isTyping\(e\.target\)\)\) return;/, "typing spares only modifier-less chords (dispatchable)");
});

// ── the claim, driven: node's EventTarget stands in for the window ─────────────────────────────────

/** A keydown as the window's capture listeners first meet it: the box as its target (an own property over node's getter,
 *  which would otherwise name the window), the key and modifiers as the event's own fields. */
function atWindow(target: N, init: Init): Event & Init {
  const ev = Object.assign(new Event("keydown", { cancelable: true }), init) as Event & Init;
  Object.defineProperty(ev, "target", { value: target, configurable: true });
  win.dispatchEvent(ev);
  return ev;
}

test("at the window: the save chord with the box as its target saves the comment and stops the event there, Ctrl or Cmd", async () => {
  const h = await harness();
  await h.open();
  h.click('[data-act="fcfile"]');
  const box = h.box();
  box.value = "Which cache?\nSay which.  ";
  const before = h.posted.length;
  const ev = atWindow(box, { key: "Enter", ctrlKey: true });
  assert.equal(ev.cancelBubble, true, "propagation stopped at the window: the shell's document-capture dispatcher never meets it");
  assert.equal(ev.defaultPrevented, true, "the chord is the box's: no newline goes in with the save");
  await tick();
  assert.equal(h.posted.length, before + 1, "one save, not one per listener");
  assert.equal(h.last().verb, "comment");
  assert.equal(h.last().args.note, "Which cache?\nSay which.", "the comment as boxKey saves it: the blank tail goes, the break inside stays");
  await h.ok();
  assert.equal(h.q(".fc-composer")!.hidden, true, "saved: the composer closes");
  h.click('[data-act="fcfile"]');
  box.value = "Lead with the numbers.";
  const mac = atWindow(box, { key: "Enter", metaKey: true });
  assert.equal(mac.cancelBubble, true, "Cmd+Enter is claimed the same, whatever the platform");
  assert.equal(mac.defaultPrevented, true);
  await tick();
  assert.equal(h.posted.length, before + 2);
  assert.equal(h.last().args.note, "Lead with the numbers.");
  await h.ok();
  h.dispose();
});

test("the claim takes nothing else: a plain or Shift+Enter, an IME's chord and an Escape pass on to the box; a chord aimed anywhere but the box passes on to the shell", async () => {
  const h = await harness();
  await h.open();
  h.click('[data-act="fcfile"]');
  const box = h.box();
  box.value = "First line.";
  const before = h.posted.length;
  const passes: Init[] = [{ key: "Enter" }, { key: "Enter", shiftKey: true }, { key: "Enter", ctrlKey: true, isComposing: true }, { key: "Escape" }];
  for (const init of passes) {
    const ev = atWindow(box, init);
    assert.equal(ev.cancelBubble, false, JSON.stringify(init) + " is not claimed");
    assert.equal(ev.defaultPrevented, false, JSON.stringify(init) + " keeps its default");
  }
  const elsewhere = atWindow(doc.body, { key: "Enter", ctrlKey: true });
  assert.equal(elsewhere.cancelBubble, false, "the chord with nothing of ours focused is the shell's: its binding fires there as before");
  assert.equal(elsewhere.defaultPrevented, false);
  const other = doc.createElement("textarea"); doc.body.appendChild(other);
  const otherBox = atWindow(other, { key: "Enter", ctrlKey: true });
  assert.equal(otherBox.cancelBubble, false, "…and so is another text field's Ctrl+Enter: the claim is the comment box's alone");
  other.remove();
  await tick();
  assert.equal(h.posted.length, before, "nothing written");
  assert.equal(h.q(".fc-composer")!.hidden, false, "the composer stands");
  assert.equal(box.value, "First line.", "the draft is untouched");
  h.dispose();
});

test("the claim lives with the panel: once the viewer closes, a chord at the window is no longer claimed", async () => {
  const h = await harness();
  await h.open();
  h.click('[data-act="fcfile"]');
  const box = h.box();
  box.value = "Late.";
  const before = h.posted.length;
  h.dispose();
  const ev = atWindow(box, { key: "Enter", ctrlKey: true });
  assert.equal(ev.cancelBubble, false, "the window listener went with the panel");
  assert.equal(ev.defaultPrevented, false);
  await tick();
  assert.equal(h.posted.length, before, "a disposed panel saves nothing");
});

// ── the order itself, in a real browser: the shell's dispatcher first on the document, the real panel after ─────

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");

/** The panel and the shell's decision functions, bundled as the webview build bundles them (in memory), as window.__romp. */
function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: {
      contents: 'import { fileCommentsAction, composerKeyAction } from "./file-comments";\nimport { chordOf, dispatchable, chordMap } from "./keybindings";\n(window as any).__romp = { fileCommentsAction, composerKeyAction, keys: { chordOf, dispatchable, chordMap } };\n',
      resolveDir: UI, loader: "ts", sourcefile: "composer-shell-chord-probe.ts",
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
/** The page's side: the shell's dispatcher as palette-main.ts wires it (a capture listener on the document, the shell's
 *  own decision functions, one command the person bound by override), a box wired the way the panel's was BEFORE the claim
 *  (the defect, for the leg's own sensitivity), and the real panel on a stubbed viewer context — the driven harness's, in
 *  the page — with its status asks answered by hand through the window message the host would post. */
const JS = `window.__calls = [];
window.__shell = (chord) => {
  const k = window.__romp.keys;
  const cmds = [{ id: "palette.toggle", chord: "Mod+P" }, { id: "session.jump", chord: "Mod+O" }];
  const byChord = k.chordMap(cmds, { "palette.toggle": chord }, false);
  const isTyping = (t) => !!(t && t.closest && t.closest("input, textarea, select, [contenteditable=true]"));
  document.addEventListener("keydown", (e) => {
    if (!k.dispatchable(e, isTyping(e.target))) return;
    const ch = k.chordOf(e);
    if (!ch) return;
    const id = byChord.get(ch);
    if (!id) return;
    e.preventDefault(); e.stopPropagation();
    window.__calls.push("shell:" + id);
  }, true);
};
window.__bare = () => {
  const ta = document.createElement("textarea"); ta.className = "bare";
  ta.addEventListener("keydown", (e) => {
    const act = window.__romp.composerKeyAction(e);
    if (act === "save") { e.preventDefault(); window.__calls.push("bare:save"); }
  });
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
    post: (m) => { window.__posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: noop, editing: () => false, setTrackedEdit: noop,
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
  test("in " + name + ": a shell command bound to Ctrl+Enter, its dispatcher on the document before the panel exists — the chord in the real box saves and the command stays quiet; outside the box the command fires; a box wired at its target alone loses the chord", async (t) => {
    await inBrowser(t, name, async (page) => {
      const calls = (): Promise<string[]> => page.evaluate(() => (window as any).__calls.splice(0));
      const posted = (): Promise<PagePost[]> => page.evaluate(() => (window as any).__posted);
      const box = (): Promise<BoxRead> => page.evaluate(() => (window as any).__box());
      const answer = (): Promise<string | null> => page.evaluate(() => (window as any).__answer());
      await page.evaluate(() => (window as any).__shell("Ctrl+Enter"));   // the shell wires its dispatcher when the pane loads: before any panel
      // the defect, for the leg's own sensitivity: a box whose only listener sits at the target loses the chord to the shell
      await page.evaluate(() => (window as any).__bare());
      await page.keyboard.type("bare");
      await page.keyboard.press("Control+Enter");
      assert.deepEqual(await calls(), ["shell:palette.toggle"], "the dispatcher stops the event in the capture phase: the bare box's own save never ran");
      // the real panel, mounted after the dispatcher as a pane's panel always is
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
      assert.deepEqual(await calls(), [], "the shell command stayed quiet: the claim at the window met the event first");
      assert.equal((await box()).value, "Which cache?\nSay which.", "no line went in with the chord");
      // the same chord with nothing of ours focused is the shell's, as before
      assert.ok(await page.evaluate(() => (window as any).__blur()), "focus left the box");
      await page.keyboard.press("Control+Enter");
      assert.deepEqual(await calls(), ["shell:palette.toggle"], "outside the box the command runs");
      assert.equal((await posted()).length, n0 + 1, "…and nothing more is saved");
      // the viewer closes: the claim goes with the panel, and the chord in what was its box is the shell's again
      await page.evaluate(() => (window as any).__close());
      await page.evaluate(() => (window as any).__bare());
      await page.keyboard.press("Control+Enter");
      assert.deepEqual(await calls(), ["shell:palette.toggle"], "after dispose no window listener of the panel's remains");
    });
  });
}
