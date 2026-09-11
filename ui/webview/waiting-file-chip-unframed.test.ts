// The Waiting-on-you pane's file chip when the pane is NOT framed (plans/file-review.md, "The todo-file follow-on
// (2026-09-07)"; the 2026-09-07 review): the kernel's /waiting page opened in a tab of its own, where window.parent is
// the window itself and there is no Files pane to send a click to. waiting.ts's fileChip then builds a plain span, not
// a path link (the linkTodoPaths gate), and the span must LOOK plain: the pane's sheet paints .wt-file in the accent,
// which on this pane is the path-link colour (the chip dress replaces the link's underline, so the colour is the only
// sign a chip is a link), and the plain chip wore it while doing nothing on a click — a dead end dressed as a control
// (ui/CLAUDE.md, every control acknowledges). fileChip now gives the plain chip the row's own text colour (inherit),
// where framed decides, so the look and the action cannot drift apart.
//
// Three legs. (1) waiting.ts booted under the DOM stand-in of waiting-file-chip.test.ts (copied: `framed` is fixed at
// import, so the unframed pane needs a module instance of its own, and node --test gives each file its own process)
// with window.parent === window, fed frames through the message it listens on, its rows read back and its clicks
// dispatched through the real delegate: the chip is a plain span with the file's name and path and none of a link's
// act, role, tab stop or key handler, its colour is the row's, and a click on it posts nothing and flashes nothing —
// on the row and in the Reply modal. (2) A source pin of the branch. (3) The rendered check, in Chromium and Firefox
// with the worktree's real waiting.ts bundle under the kernel's own composition of the page (styles.css, THEME_CSS,
// waiting-pane.css): the unframed chip's computed colour is the row text's and not the accent, the framed chip's (the
// same page in an iframe) IS the accent, and the two share every other part of the pill dress; a raw press on the
// unframed chip changes nothing. The browser legs skip LOUDLY without playwright or the browser (CI installs none).
// Synthetic only: the notes-api world, placeholder sids, paths under /tmp/notes-api.
import { test, after } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { inspect } from "node:util";
import { hideEdges, staysEnumerable } from "../test-dom-shim";

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
const WAITING = fs.readFileSync(path.join(UI, "waiting.ts"), "utf8");
const KERNEL = fs.readFileSync(path.resolve(EXT, "..", "kernel", "kernel.py"), "utf8");

// ── a DOM stand-in ─────────────────────────────────────────────────────────────────────────────────
class Style {
  [key: string]: any;
  setProperty(k: string, v: string): void { this[k] = v; }
  removeProperty(k: string): void { delete this[k]; }
  getPropertyValue(k: string): string { return this[k] ?? ""; }
}
type Kid = El | Txt;
/** the DOM's detach: a node that left its parent's list forgets the parent. A helper, so no class assigns an edge of
 *  its own (the ratchet in ui/test-dom-shim.test.ts reads a class's own null assignment to parentNode as an enumerable edge). */
const detach = (n: Kid): void => { n.parentNode = null; };
class Txt {
  nodeType = 3;
  parentNode!: El | null;
  constructor(public data: string) {
    Object.defineProperty(this, "parentNode", { value: null, writable: true, enumerable: false, configurable: true });
    hideEdges(this);
  }
  get textContent(): string { return this.data; }
  set textContent(v: string) { this.data = v; }
  get parentElement(): El | null { return this.parentNode; }
  get length(): number { return this.data.length; }
  get nextSibling(): Kid | null { return sib(this, 1); }
  get previousSibling(): Kid | null { return sib(this, -1); }
  remove(): void { this.parentNode?.removeChild(this); }
  /** the path walk's splice: the text node gives way to the fragment's children, in place */
  replaceWith(...nodes: Array<Kid | string>): void {
    const p = this.parentNode; if (!p) return;
    const i = p.childNodes.indexOf(this);
    const kids: Kid[] = [];
    for (const n of nodes) { if (n instanceof El && n.tagName === "#FRAGMENT") kids.push(...n.childNodes.splice(0)); else kids.push(typeof n === "string" ? new Txt(n) : n); }
    for (const k of kids) { k.parentNode?.removeChild(k); k.parentNode = p; }
    p.childNodes.splice(i, 1, ...kids);
    detach(this);
  }
  splitText(offset: number): Txt {
    const tail = new Txt(this.data.slice(offset)); this.data = this.data.slice(0, offset);
    const p = this.parentNode; if (p) { const i = p.childNodes.indexOf(this); p.childNodes.splice(i + 1, 0, tail); tail.parentNode = p; }
    return tail;
  }
}
function sib(n: Kid, d: number): Kid | null { const p = n.parentNode; if (!p) return null; const i = p.childNodes.indexOf(n); return p.childNodes[i + d] ?? null; }
const camel = (s: string) => s.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
const kebab = (s: string) => s.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
type Compound = { tag: string | null; id: string | null; classes: string[]; attrs: { name: string; value: string | null }[]; pseudo: boolean };
function parseCompound(s: string): Compound {
  const c: Compound = { tag: null, id: null, classes: [], attrs: [], pseudo: false };
  const m = /^([a-zA-Z][\w-]*)?(.*)$/.exec(s)!;
  c.tag = m[1] ? m[1].toUpperCase() : null;
  const re = /\.([\w-]+)|#([\w-]+)|\[([\w-]+)(?:="([^"]*)")?\]|:[\w-]+(?:\([^)]*\))?/g;
  let t: RegExpExecArray | null;
  while ((t = re.exec(m[2]))) {
    if (t[1]) c.classes.push(t[1]); else if (t[2]) c.id = t[2]; else if (t[3]) c.attrs.push({ name: t[3], value: t[4] ?? null }); else c.pseudo = true;
  }
  return c;
}
type Ev = { type: string; target: El; currentTarget: El | Doc | null; key?: string; defaultPrevented: boolean; preventDefault(): void; stopPropagation(): void };
class El {
  nodeType = 1;
  parentNode!: El | null;
  childNodes!: Kid[];
  style = new Style();
  hidden = false; disabled = false; checked = false; value = ""; type = ""; placeholder = ""; rows = 0; role = "";
  offsetWidth = 0; offsetHeight = 0;
  onkeydown: ((e: any) => void) | null = null; onmousedown: any = null; onmouseup: any = null; onmouseleave: any = null; oncontextmenu: any = null; ondragstart: any = null;
  listeners = new Map<string, Array<{ fn: (ev: Ev) => void; capture: boolean }>>();
  private attrs = new Map<string, string>();
  dataset: Record<string, string | undefined>;
  classList = {
    add: (...c: string[]) => { const s = this.classes(); for (const x of c) s.add(x); this.setClasses(s); },
    remove: (...c: string[]) => { const s = this.classes(); for (const x of c) s.delete(x); this.setClasses(s); },
    toggle: (c: string, force?: boolean) => { const s = this.classes(); const on = force === undefined ? !s.has(c) : force; if (on) s.add(c); else s.delete(c); this.setClasses(s); return on; },
    contains: (c: string) => this.classes().has(c),
  };
  constructor(public tagName: string) {
    Object.defineProperty(this, "parentNode", { value: null, writable: true, enumerable: false, configurable: true });
    Object.defineProperty(this, "childNodes", { value: [], writable: true, enumerable: false, configurable: true });
    this.tagName = tagName.toUpperCase();
    this.dataset = new Proxy({} as Record<string, string | undefined>, {
      get: (_t, k) => (typeof k === "string" ? this.attrs.get("data-" + kebab(k)) : undefined),
      set: (_t, k, v) => { this.attrs.set("data-" + kebab(String(k)), String(v)); return true; },
      deleteProperty: (_t, k) => { this.attrs.delete("data-" + kebab(String(k))); return true; },
      has: (_t, k) => this.attrs.has("data-" + kebab(String(k))),
      ownKeys: () => Array.from(this.attrs.keys()).filter((k) => k.startsWith("data-")).map((k) => camel(k.slice(5))),
      getOwnPropertyDescriptor: (_t, k) => (this.attrs.has("data-" + kebab(String(k))) ? { enumerable: true, configurable: true, value: this.attrs.get("data-" + kebab(String(k))) } : undefined),
    });
    hideEdges(this);
  }
  private classes(): Set<string> { return new Set((this.attrs.get("class") || "").split(/\s+/).filter(Boolean)); }
  private setClasses(s: Set<string>): void { this.attrs.set("class", [...s].join(" ")); }
  get className(): string { return this.attrs.get("class") || ""; }
  set className(v: string) { this.attrs.set("class", v); }
  get id(): string { return this.attrs.get("id") || ""; }
  set id(v: string) { this.attrs.set("id", v); }
  get title(): string { return this.attrs.get("title") || ""; }
  set title(v: string) { this.attrs.set("title", v); }
  get tabIndex(): number { const v = this.attrs.get("tabindex"); return v === undefined ? -1 : Number(v); }
  set tabIndex(v: number) { this.attrs.set("tabindex", String(v)); }
  get textContent(): string { return this.childNodes.map((c) => c.textContent).join(""); }
  set textContent(v: string | null) { this.detachAll(); if (v !== null && v !== "") this.appendChild(new Txt(String(v))); }
  get children(): El[] { return this.childNodes.filter((c): c is El => c instanceof El); }
  get firstChild(): Kid | null { return this.childNodes[0] ?? null; }
  get lastChild(): Kid | null { return this.childNodes[this.childNodes.length - 1] ?? null; }
  get firstElementChild(): El | null { return this.children[0] ?? null; }
  get nextSibling(): Kid | null { return sib(this, 1); }
  get previousSibling(): Kid | null { return sib(this, -1); }
  get parentElement(): El | null { return this.parentNode; }
  get isConnected(): boolean { return this === body || body.contains(this); }
  private detachAll(): void { for (const c of this.childNodes) c.parentNode = null; this.childNodes.length = 0; }
  private adopt(c: Kid | string): Kid[] {
    if (c instanceof El && c.tagName === "#FRAGMENT") { const kids = c.childNodes.splice(0); for (const k of kids) k.parentNode = this; return kids; }
    const n = typeof c === "string" ? new Txt(c) : c; n.parentNode?.removeChild(n); n.parentNode = this; return [n];
  }
  appendChild<T extends Kid>(c: T): T { this.childNodes.push(...this.adopt(c)); return c; }
  append(...cs: Array<Kid | string>): void { for (const c of cs) this.childNodes.push(...this.adopt(c)); }
  prepend(...cs: Array<Kid | string>): void { const all: Kid[] = []; for (const c of cs) all.push(...this.adopt(c)); this.childNodes.unshift(...all); }
  replaceChildren(...cs: Array<Kid | string>): void { this.detachAll(); this.append(...cs); }
  insertBefore<T extends Kid>(node: T, ref: Kid | null): T {
    const ns = this.adopt(node);
    const i = ref ? this.childNodes.indexOf(ref) : -1;
    if (i < 0) this.childNodes.push(...ns); else this.childNodes.splice(i, 0, ...ns);
    return node;
  }
  removeChild(c: Kid): void { const i = this.childNodes.indexOf(c); if (i >= 0) { this.childNodes.splice(i, 1); c.parentNode = null; } }
  remove(): void { this.parentNode?.removeChild(this); }
  replaceWith(...nodes: Array<Kid | string>): void { const p = this.parentNode; if (!p) return; for (const n of nodes) p.insertBefore(typeof n === "string" ? new Txt(n) : n, this); this.remove(); }
  normalize(): void {
    const out: Kid[] = [];
    for (const c of this.childNodes) { const prev = out[out.length - 1]; if (c instanceof Txt && prev instanceof Txt) { prev.data += c.data; c.parentNode = null; } else if (c instanceof Txt && c.data === "") c.parentNode = null; else out.push(c); }
    this.childNodes = out;
  }
  contains(x: Kid | null): boolean { for (let n: Kid | null = x; n; n = n.parentNode) if (n === this) return true; return false; }
  setAttribute(k: string, v: string): void { this.attrs.set(k, String(v)); }
  getAttribute(k: string): string | null { return this.attrs.has(k) ? this.attrs.get(k)! : null; }
  hasAttribute(k: string): boolean { return this.attrs.has(k); }
  removeAttribute(k: string): void { this.attrs.delete(k); }
  getBoundingClientRect() { return { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 }; }
  scrollIntoView(): void {}
  focus(): void { doc.activeElement = this; }
  blur(): void { if (doc.activeElement === this) doc.activeElement = body; }
  getAnimations(): unknown[] { return []; }
  matchesCompound(c: Compound): boolean {
    if (c.pseudo) return false;
    if (c.tag && c.tag !== this.tagName) return false;
    if (c.id && c.id !== this.id) return false;
    for (const k of c.classes) if (!this.classes().has(k)) return false;
    for (const a of c.attrs) { const v = this.getAttribute(a.name); if (v === null) return false; if (a.value !== null && v !== a.value) return false; }
    return true;
  }
  matches(sel: string): boolean {
    return sel.split(",").some((one) => {
      const parts = one.trim().split(/\s+/).map(parseCompound);
      if (!this.matchesCompound(parts[parts.length - 1])) return false;
      let anc: El | null = this.parentNode;
      for (let i = parts.length - 2; i >= 0; i--) { while (anc && !anc.matchesCompound(parts[i])) anc = anc.parentNode; if (!anc) return false; anc = anc.parentNode; }
      return true;
    });
  }
  closest(sel: string): El | null { for (let n: El | null = this; n; n = n.parentNode) if (n.matches(sel)) return n; return null; }
  querySelectorAll(sel: string): El[] { return [...this.walk()].filter((e) => e.matches(sel)); }
  querySelector(sel: string): El | null { for (const e of this.walk()) if (e.matches(sel)) return e; return null; }
  *walk(): Generator<El> { for (const c of this.childNodes) if (c instanceof El) { yield c; yield* c.walk(); } }
  *texts(): Generator<Txt> { for (const c of this.childNodes) { if (c instanceof Txt) yield c; else yield* c.texts(); } }
  addEventListener(type: string, fn: (ev: Ev) => void, opts?: boolean | { capture?: boolean }): void {
    const capture = typeof opts === "boolean" ? opts : !!(opts && opts.capture);
    (this.listeners.get(type) || this.listeners.set(type, []).get(type)!).push({ fn, capture });
  }
  removeEventListener(type: string, fn: (ev: Ev) => void): void { const l = this.listeners.get(type); if (l) { const i = l.findIndex((x) => x.fn === fn); if (i >= 0) l.splice(i, 1); } }
  /** dispatch with capture then bubble: the document's capture listeners first (the disarm, the PR-link opener),
   *  then this node up to the body, then the document's bubble listeners */
  dispatch(type: string, init: { key?: string } = {}): Ev {
    let stopped = false;
    const ev: Ev = { type, target: this, currentTarget: null, key: init.key, defaultPrevented: false, preventDefault() { this.defaultPrevented = true; }, stopPropagation() { stopped = true; } };
    ev.currentTarget = doc;
    for (const l of [...(doc.listeners.get(type) || [])]) if (l.capture && !stopped) l.fn(ev);
    const chain: El[] = []; for (let n: El | null = this; n; n = n.parentNode) chain.push(n);
    for (const n of [...chain].reverse()) { if (stopped) break; ev.currentTarget = n; for (const l of [...(n.listeners.get(type) || [])]) if (l.capture) l.fn(ev); }
    for (const n of chain) {
      if (stopped) break;
      ev.currentTarget = n;
      const h = (n as any)["on" + type]; if (typeof h === "function") h(ev);
      for (const l of [...(n.listeners.get(type) || [])]) if (!l.capture) l.fn(ev);
    }
    ev.currentTarget = doc;
    for (const l of [...(doc.listeners.get(type) || [])]) if (!l.capture && !stopped) l.fn(ev);
    return ev;
  }
  click(): void { this.dispatch("click"); }
}
class Doc {
  body = new El("body");
  documentElement = new El("html");
  head = new El("head");
  hidden = false;
  visibilityState = "visible";
  activeElement: El = this.body;
  listeners = new Map<string, Array<{ fn: (ev: Ev) => void; capture: boolean }>>();
  constructor() { hideEdges(this); }
  createElement(tag: string): El { return new El(tag); }
  createTextNode(s: string): Txt { return new Txt(s); }
  createDocumentFragment(): El { return new El("#fragment"); }
  createTreeWalker(root: El): { nextNode(): Txt | null } { const nodes = [...root.texts()]; let i = 0; return { nextNode: () => (i < nodes.length ? nodes[i++] : null) }; }
  getElementById(id: string): El | null { for (const e of this.body.walk()) if (e.id === id) return e; return null; }
  querySelectorAll(sel: string): El[] { return this.body.querySelectorAll(sel); }
  querySelector(sel: string): El | null { return this.body.querySelector(sel); }
  getElementsByTagName(): El[] { return []; }
  contains(x: Kid): boolean { return this.body.contains(x); }
  addEventListener(type: string, fn: (ev: Ev) => void, opts?: boolean | { capture?: boolean }): void {
    const capture = typeof opts === "boolean" ? opts : !!(opts && opts.capture);
    (this.listeners.get(type) || this.listeners.set(type, []).get(type)!).push({ fn, capture });
  }
  removeEventListener(type: string, fn: (ev: Ev) => void): void { const l = this.listeners.get(type); if (l) { const i = l.findIndex((x) => x.fn === fn); if (i >= 0) l.splice(i, 1); } }
}

// ── globals the module reaches for, installed before it is imported ────────────────────────────────
const doc = new Doc();
const body = doc.body;
const head = new El("div"); head.id = "waiting-head";
const list = new El("div"); list.id = "waiting-list";
body.append(head, list);
const stores = new Map<string, string>();
(globalThis as any).localStorage = { getItem: (k: string) => (stores.has(k) ? stores.get(k)! : null), setItem: (k: string, v: string) => { stores.set(k, String(v)); }, removeItem: (k: string) => { stores.delete(k); } };
(globalThis as any).NodeFilter = { SHOW_TEXT: 4 };
const posted: any[] = [];                 // what the pane posts to its host (the kernel socket)
const selfPosts: any[] = [];              // what it posts to window.parent — which, unframed, is this window
const win: any = new EventTarget();
// NOT framed: the kernel's /waiting page in a tab of its own. window.parent is the window itself (the check waiting.ts
// makes: `const framed = window.parent !== window`), so a viewFile the pane posted would land HERE — selfPosts holds it
win.parent = win;
win.top = win;
win.postMessage = (m: any) => { selfPosts.push(m); };
win.document = doc;                       // openTodoPath reads window.parent.document: this document, with no f-files
win.innerWidth = 1200; win.innerHeight = 800;
win.location = { hash: "", search: "", protocol: "http:" };
win.setTimeout = (...a: Parameters<typeof setTimeout>) => setTimeout(...a);
win.clearTimeout = (t: ReturnType<typeof setTimeout>) => clearTimeout(t);
win.setInterval = (...a: Parameters<typeof setInterval>) => { const t = setInterval(...a); (t as any).unref?.(); return t; };
win.clearInterval = (t: ReturnType<typeof setInterval>) => clearInterval(t);
win.requestAnimationFrame = (cb: () => void) => setTimeout(cb, 0);
win.matchMedia = () => ({ matches: false, addEventListener() {}, addListener() {} });
win.getComputedStyle = () => ({});
win.open = () => null;
win.acquireVsCodeApi = () => ({ postMessage: (m: any) => posted.push(m) });
(globalThis as any).window = win;
(globalThis as any).document = doc;
(globalThis as any).requestAnimationFrame = win.requestAnimationFrame;
(globalThis as any).getComputedStyle = win.getComputedStyle;
// the pane's own timers (the 15 s live pass, the loader hold) must never hold the test process open
const realSetInterval = globalThis.setInterval;
(globalThis as any).setInterval = (fn: () => void, ms: number) => { const t = realSetInterval(fn, ms); (t as any).unref?.(); return t; };

// ── the world: the notes-api project's api session, a todo that names its file and one that does not ──
const SID = "11111111-2222-3333-4444-555555555555";
const COLOR = { bg: "#123456", fg: "#ffffff" };
const FILE = "/tmp/notes-api/docs/design.md";
const DETAIL = "The two layouts are in docs/design.md; say which to keep.";
const T0 = 1781100000;
const rows = (todos: any[]) => [{ sid: SID, name: "api", color: COLOR, todos }];
const frame = (todos: any[]) => ({ type: "feed", now: T0, nowAt: T0 * 1000, buildId: 1, userTodosOn: true, userTodoRows: rows(todos),
  sessions: [{ sid: SID, name: "api", color: COLOR, githubRepo: null }], asks: [], userTodos: {} });
const WITH_FILE = { id: "t1", text: "Pick the layout", createdT: T0 - 300, detail: DETAIL, file: FILE };
const NO_FILE = { id: "t2", text: "Approve the rollout note", createdT: T0 - 120, detail: "It is in the chat above." };
const listenerErrors: Error[] = [];
process.on("uncaughtException", (e) => { listenerErrors.push(e); });
const settle = () => new Promise<void>((r) => setImmediate(r));
const dispatch = async (f: any) => {
  win.dispatchEvent(new MessageEvent("message", { data: f }));
  await settle();
  if (listenerErrors.length) { const es = listenerErrors.splice(0); throw new Error("a listener threw: " + es.map((e) => e.stack || e.message).join("\n---\n")); }
};
after(() => { assert.deepEqual(listenerErrors.map((e) => e.stack || e.message), [], "no listener threw outside a dispatch"); });
const row = (tid: string): El => { const r = list.querySelector(`.ut-item[data-tid="${tid}"]`); assert.ok(r, "a row for " + tid); return r!; };
const kinds = (parent: El) => parent.children.map((c) => (c.classList.contains("wt-file") ? "wt-file" : c.className.split(" ")[0]));
const viewFiles = () => selfPosts.filter((m) => m && m.romp === "viewFile");
/** the plain chip, checked the same way on the row and in the modal: a label, with nothing of a link on it */
function assertPlainChip(chip: El, where: string): void {
  assert.equal(chip.textContent, "design.md", where + ": the label is the basename");
  assert.equal(chip.title, FILE, where + ": the full path is the hover");
  assert.ok(chip.classList.contains("wt-file"), where + ": the chip dress");
  assert.equal(chip.classList.contains("file-uri-link"), false, where + ": NOT a path link — there is no Files pane to open the file in");
  assert.equal(chip.dataset.act, undefined, where + ": no act, so no delegate answers a click");
  assert.equal(chip.dataset.path, undefined, where + ": no path to open");
  assert.equal(chip.dataset.sid, undefined);
  assert.equal(chip.role, "", where + ": not announced as a link");
  assert.equal(chip.tabIndex, -1, where + ": not in the tab order");
  assert.equal(chip.onkeydown, null, where + ": no Enter/Space handler");
  assert.equal(chip.onmousedown, null, where + ": none of the link's press handlers");
  assert.equal(chip.style.color, "inherit", where + ": the row's own text colour, over the sheet's accent — it must not read as a link");
}

test("unframed boot: the todo that names a file wears the chip as a plain label — the file's name and path, none of a link's act, role, tab stop or handlers, and the row's text colour", async () => {
  await import("./waiting");
  assert.equal(posted.filter((m) => m.type === "ready").length, 1, "the ready handshake");
  await dispatch(frame([WITH_FILE, NO_FILE]));
  assert.equal(list.querySelectorAll(".ut-item").length, 2);
  const chip = row("t1").querySelector(".wt-file");
  assert.ok(chip, "the row of the todo with `file` carries the chip, unframed too: it names the file");
  assertPlainChip(chip!, "the row");
  // its place on the line is the framed chip's: session, the words, the file, then when and the buttons
  assert.deepEqual(kinds(row("t1").querySelector(".ut-line")!), ["wt-sess", "ut-text", "wt-file", "wt-age", "ut-btn", "ut-btn"]);
  assert.equal(row("t2").querySelector(".wt-file"), null, "no `file`, no chip");
  // the same gate keeps the detail's path plain text: the chip is not the only thing left unlinked
  const detail = row("t1").querySelector(".ut-detail")!;
  assert.equal(detail.querySelectorAll(".file-uri-link").length, 0, "unframed, a path in the detail stays plain (the linkTodoPaths gate)");
  assert.equal(detail.textContent, DETAIL);
  assert.equal(list.querySelectorAll(".file-uri-link").length, 0, "nothing on the list is a path link");
});

test("a click, a press and Enter on the plain chip do nothing: no viewFile posted, no press flash, no fold or modal — and nothing throws", async () => {
  selfPosts.length = 0;
  const r = row("t1");
  const chip = r.querySelector(".wt-file")!;
  const foldOpen = r.querySelector(".ut-detail")!.classList.contains("open");
  chip.dispatch("mousedown");
  chip.dispatch("mouseup");
  chip.dispatch("click");
  chip.dispatch("keydown", { key: "Enter" });
  chip.dispatch("keydown", { key: " " });
  await settle();
  assert.deepEqual(viewFiles(), [], "no viewFile went anywhere (unframed, the parent is this window: a post would land here)");
  assert.deepEqual(selfPosts.filter((m) => m && m.romp), [], "no shell message of any kind");
  assert.equal(chip.classList.contains("romp-acted"), false, "the delegate never flashed it: no data-act, so no act");
  assert.equal(list.querySelectorAll(".romp-acted").length, 0, "…and flashed nothing else on the list");
  assert.equal(r.querySelector(".ut-detail")!.classList.contains("open"), foldOpen, "the fold did not toggle");
  assert.equal(doc.getElementById("ut-reply-prompt"), null, "no modal opened");
  assert.equal(posted.filter((m) => m.type !== "ready").length, 0, "nothing went to the kernel");
  // the framed test's contrast: the session chip beside it IS a control, and the delegate flashes it
  const sess = r.querySelector(".wt-sess")!;
  sess.dispatch("click");
  assert.ok(sess.classList.contains("romp-acted"), "the session chip acknowledges a click (data-act open) — the file chip, with no action, does not pretend to");
  assert.deepEqual(posted.filter((m) => m.type === "openSession").map((m) => m.id), [SID]);
});

test("the Reply modal's chip is the same plain label, and a click on it leaves the modal up and posts nothing", async () => {
  selfPosts.length = 0;
  row("t1").querySelector(".ut-reply")!.dispatch("click");
  const modal = doc.getElementById("ut-reply-prompt");
  assert.ok(modal, "the Reply modal is up");
  const box = modal!.querySelector(".confirm-box")!;
  assert.deepEqual(kinds(box), ["confirm-title", "confirm-detail", "wt-file", "ut-detail", "ut-reply-input", "confirm-actions"], "title, the quoted line, the chip, the detail, the box, the buttons — as framed");
  const chip = box.querySelector(".wt-file")!;
  assertPlainChip(chip, "the modal");
  chip.dispatch("click");
  chip.dispatch("keydown", { key: "Enter" });
  await settle();
  assert.deepEqual(viewFiles(), [], "the modal's delegate answers no click on it: no act");
  assert.ok(doc.getElementById("ut-reply-prompt"), "the modal stays up");
  assert.equal(box.querySelectorAll(".romp-acted").length, 0, "no press flash in the box");
  assert.equal(box.querySelectorAll(".file-uri-link").length, 0, "the quoted line and the detail carry no path link either, unframed");
  modal!.querySelector(".confirm-actions")!.children[0].dispatch("click");   // Cancel
  assert.equal(doc.getElementById("ut-reply-prompt"), null);
});

test("source pin: the plain chip's colour is set in fileChip's unframed branch, where framed decides — the framed link keeps the sheet's accent", () => {
  assert.match(WAITING, /const framed = window\.parent !== window;/);
  assert.match(WAITING, /const chip = framed \? openPathLink\(base, file, false, sid\) : el\("span", ""\);\n\s*if \(!framed\) \{ chip\.textContent = base; chip\.style\.color = "inherit"; \}\n\s*chip\.classList\.add\("wt-file"\);/,
    "unframed: the basename as the text and the row's colour, on the plain span only; the link's branch sets no colour");
  const fn = WAITING.slice(WAITING.indexOf("function fileChip("), WAITING.indexOf("\n}", WAITING.indexOf("function fileChip(")));
  assert.equal((fn.match(/style\.color/g) || []).length, 1, "one colour write in fileChip, and it is the unframed one");
});

// ── the rendered check: the real bundle under the kernel's own page, in Chromium and Firefox ─────────
function bundle(entry: string): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    entryPoints: [path.join(UI, entry)], bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
// the kernel's THEME_CSS, verbatim: the :root tokens (--vscode-foreground and the rest) the /waiting page inlines
// before waiting-pane.css (_waiting_page), sliced from the Python source; CSS in a non-raw string, so a backslash
// would mean the served text differs — checked
function themeCss(): string {
  const open = 'THEME_CSS = """';
  const at = KERNEL.indexOf(open);
  assert.ok(at > 0, "THEME_CSS not found in kernel.py — re-anchor");
  const start = at + open.length;
  const css = KERNEL.slice(start, KERNEL.indexOf('"""', start));
  assert.ok(!css.includes("\\"), "THEME_CSS carries a backslash: Python would alter it — slice differently");
  return css;
}
const STYLES_CSS = fs.readFileSync(path.join(UI, "styles.css"), "utf8");        // linked first: the .ut-* dress, --accent, .file-uri-link
const PANE_CSS = fs.readFileSync(path.join(UI, "waiting-pane.css"), "utf8");    // then the pane's own sheet, in a <style> after it
// the page as _waiting_page composes it (no shim, no federation: frames come by postMessage, as the sibling tests feed them)
const WAITING_HTML = `<!DOCTYPE html><html lang=en><head><meta charset=utf-8><link href=/dist/styles.css rel=stylesheet>
<style>${themeCss()}\n${PANE_CSS}</style></head><body>
<div id=waiting-head></div><div id=waiting-list></div><script src=/dist/waiting.js></script></body></html>`;
// the shell, reduced to what frames the pane: an iframe on the same page (window.parent !== window inside it)
const SHELL_HTML = `<!DOCTYPE html><html><head><meta charset=utf-8></head><body>
<iframe id=f-waiting src=/waiting style="width:640px;height:400px;border:0"></iframe></body></html>`;
// what the pane's document says about the chip of row t1: its classes, its computed dress, the row text's colour beside
// it, and the accent as this page resolves it (a probe span coloured var(--accent), so a theme change cannot stale a hex)
const PROBE = `(d, sel) => {
  const chip = d.querySelector(sel);
  if (!chip) return null;
  const cs = getComputedStyle(chip);
  const text = getComputedStyle(d.querySelector('.ut-item[data-tid="t1"] .ut-text'));
  const probe = d.createElement("span"); probe.style.color = "var(--accent)"; d.body.appendChild(probe);
  const accent = getComputedStyle(probe).color; probe.remove();
  return { cls: chip.className, text: chip.textContent, title: chip.title, color: cs.color, cursor: cs.cursor, bg: cs.backgroundColor,
    radius: cs.borderTopLeftRadius, padding: cs.paddingLeft, fontSize: cs.fontSize, role: chip.getAttribute("role"),
    tabindex: chip.getAttribute("tabindex"), act: chip.dataset.act ?? null, textColor: text.color, accent };
}`;
const FEED = `(w) => { const now = Math.floor(Date.now() / 1000); w.postMessage({ type: "feed", now, userTodosOn: true,
  userTodoRows: [{ sid: ${JSON.stringify(SID)}, name: "api", color: ${JSON.stringify(COLOR)},
    todos: [{ id: "t1", text: "Pick the layout", createdT: now - 300, detail: ${JSON.stringify(DETAIL)}, file: ${JSON.stringify(FILE)} }] }] }, "*"); }`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

for (const name of ["chromium", "firefox"]) {
  test(`in ${name}: unframed, the chip wears the row's text colour and not the accent; framed, the same chip IS the accent link; a raw press on the plain chip changes nothing`, async (t) => {
    if (!pw) { t.skip("playwright is not installed under vscode-extension — the browser legs need it (CI installs no browsers)"); return; }
    let browser: any;
    try { browser = await pw[name].launch(); }
    catch (e) { t.skip("no playwright " + name + " on this box — this leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
    try {
      const waitingJs = bundle("waiting.ts");
      const errors: string[] = [];
      const open = async (url: string) => {
        const page = await browser.newPage({ viewport: { width: 1000, height: 500 } });
        page.on("pageerror", (e: Error) => { errors.push(e.message); });
        // every romp: message that reaches a window, and every window.open — an unframed pane's parent is itself, so a
        // viewFile it posted would arrive here
        await page.addInitScript(() => {
          (window as any).__romps = [];
          (window as any).__opens = [];
          window.addEventListener("message", (e) => { if (e.data && (e.data as any).romp) (window as any).__romps.push(e.data); });
          window.open = ((u: any) => { (window as any).__opens.push(String(u)); return null; }) as any;
        });
        await page.route("http://romp.test/**", (route: any) => {
          const u = new URL(route.request().url());
          const send = (type: string, b: string) => route.fulfill({ status: 200, contentType: type, body: b });
          if (u.pathname === "/waiting") return send("text/html; charset=utf-8", WAITING_HTML);
          if (u.pathname === "/shell") return send("text/html; charset=utf-8", SHELL_HTML);
          if (u.pathname === "/dist/waiting.js") return send("application/javascript", waitingJs);
          if (u.pathname === "/dist/styles.css") return send("text/css; charset=utf-8", STYLES_CSS);
          return route.fulfill({ status: 404, body: "" });   // fonts, media, katex: not what this leg measures
        });
        await page.goto("http://romp.test" + url);
        return page;
      };
      // ── unframed: the kernel's /waiting page in a tab of its own ──
      const top = await open("/waiting");
      assert.equal(await top.evaluate(() => window.parent === window), true, "the page is not framed");
      await top.evaluate(`(${FEED})(window)`);
      await top.locator(".ut-reply").first().waitFor({ timeout: 10000 });
      const plain = await top.evaluate(`(${PROBE})(document, '.ut-item[data-tid="t1"] .wt-file')`) as any;
      assert.ok(plain, "the unframed row carries the chip");
      assert.equal(plain.text, "design.md"); assert.equal(plain.title, FILE);
      assert.deepEqual(plain.cls.split(" ").sort(), ["wt-file"], "a plain span in the chip dress, not a path link");
      assert.equal(plain.act, null); assert.equal(plain.role, null); assert.equal(plain.tabindex, null);
      assert.equal(plain.cursor, "auto", "no pointer cursor: nothing to click");
      assert.notEqual(plain.accent, plain.textColor, "the page resolves the accent to something other than the text colour (else this leg proves nothing)");
      assert.equal(plain.color, plain.textColor, "the plain chip wears the row text's colour…");
      assert.notEqual(plain.color, plain.accent, "…and NOT the accent, the pane's path-link colour");
      // a raw press (mouse down and up, no retry) on the plain chip: nothing acknowledges, nothing opens, nothing is posted
      const box = await top.locator('.ut-item[data-tid="t1"] .wt-file').boundingBox();
      assert.ok(box, "the chip has a box");
      await top.mouse.move(box!.x + box!.width / 2, box!.y + box!.height / 2);
      await top.mouse.down(); await top.mouse.up();
      await top.evaluate(() => new Promise<void>((r) => { requestAnimationFrame(() => setTimeout(r, 0)); }));   // a posted message would have landed
      const afterPress = await top.evaluate(() => ({
        romps: (window as any).__romps, opens: (window as any).__opens, acted: document.querySelectorAll(".romp-acted").length,
        modal: !!document.getElementById("ut-reply-prompt"), url: location.href, hover: getComputedStyle(document.querySelector('.ut-item[data-tid="t1"] .wt-file')!).filter,
      }));
      assert.deepEqual(afterPress, { romps: [], opens: [], acted: 0, modal: false, url: "http://romp.test/waiting", hover: "none" },
        "no viewFile, no window.open, no press flash, no modal, no navigation, no hover brighten (the sheet scopes it to the link)");
      // the Reply modal's chip: the same plain label; a press leaves the modal up
      await top.locator(".ut-reply").click();
      await top.locator("#ut-reply-prompt .wt-file").waitFor({ timeout: 10000 });
      const modalChip = await top.evaluate(`(${PROBE})(document, '#ut-reply-prompt .wt-file')`) as any;
      assert.deepEqual(modalChip.cls.split(" ").sort(), ["wt-file"]);
      assert.equal(modalChip.color, plain.textColor, "the modal's chip wears the text colour too");
      assert.equal(modalChip.cursor, "auto");
      const mbox = await top.locator("#ut-reply-prompt .wt-file").boundingBox();
      assert.ok(mbox);
      await top.mouse.move(mbox!.x + mbox!.width / 2, mbox!.y + mbox!.height / 2);
      await top.mouse.down(); await top.mouse.up();
      await top.evaluate(() => new Promise<void>((r) => { requestAnimationFrame(() => setTimeout(r, 0)); }));
      assert.deepEqual(await top.evaluate(() => ({ romps: (window as any).__romps, modal: !!document.getElementById("ut-reply-prompt"), acted: document.querySelectorAll("#ut-reply-prompt .romp-acted").length })),
        { romps: [], modal: true, acted: 0 }, "the modal stays, nothing posted, nothing flashed");
      // ── framed: the same page in an iframe — the chip is the accent link ──
      const shell = await open("/shell");
      await shell.evaluate(`(${FEED})(document.getElementById("f-waiting").contentWindow)`);
      await shell.frameLocator("#f-waiting").locator(".ut-reply").first().waitFor({ timeout: 10000 });
      const link = await shell.evaluate(`(${PROBE})(document.getElementById("f-waiting").contentDocument, '.ut-item[data-tid="t1"] .wt-file')`) as any;
      assert.ok(link, "the framed row carries the chip");
      assert.deepEqual(link.cls.split(" ").sort(), ["file-uri-link", "wt-file"], "framed: a path link in the chip dress");
      assert.equal(link.act, "openpath"); assert.equal(link.role, "link"); assert.equal(link.tabindex, "0");
      assert.equal(link.cursor, "pointer");
      assert.equal(link.color, link.accent, "the link wears the accent, the pane's path-link colour");
      assert.equal(link.accent, plain.accent, "the two pages resolve the same accent");
      // the two chips differ in colour and in nothing else of the dress: one pill, two meanings
      assert.notEqual(plain.color, link.color);
      for (const k of ["bg", "radius", "padding", "fontSize", "text", "title"] as const) assert.equal(plain[k], link[k], "the same " + k + " on both chips");
      assert.deepEqual(errors, [], "no script error on either page");
    } finally { await browser.close(); }
  });
}

// The projection rule (ui/test-dom-shim.ts, hideEdges): a stand-in node enumerates its primitives alone, so a failing
// assertion's dump of one stops at the node instead of walking the whole tree through its edges.
test("a stand-in node enumerates its primitives alone, and a dump of it names neither parentNode nor childNodes", () => {
  const root = new El("div"); const kid = root.appendChild(new El("span")); kid.appendChild(new Txt("x"));
  const nodes = [root, kid, kid.childNodes[0]];
  for (const n of nodes) {
    assert.ok(Object.keys(n).every((k) => staysEnumerable((n as any)[k])), "every enumerable own key holds a primitive");
    const dump = inspect(n, { compact: false, customInspect: false, depth: 1000, maxArrayLength: Infinity, showHidden: false, showProxy: false, sorted: true, getters: true });
    assert.ok(!dump.includes("parentNode") && !dump.includes("childNodes"), "the dump stops at the node");
  }
});
