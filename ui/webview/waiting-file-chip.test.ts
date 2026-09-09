// The Waiting-on-you pane's file chip, RUN (plans/file-review.md, "The todo-file follow-on (2026-09-07)"): waiting.ts
// booted under a DOM stand-in, fed feed frames through the window message it listens on, its rows read back, and its
// clicks dispatched through the real delegate on #waiting-list — so the chip is exercised as behavior, not pinned at
// source (the feed-render-incremental.test.ts idiom; there is no jsdom in this tree).
//
// A user todo may now NAME the file it is about: `file`, an absolute path the kernel resolved when the todo was
// filed, riding the feed's userTodoRows unchanged. The pane shows it as a chip on the row — the basename as the label,
// the full path on hover — and the same chip in the Reply modal; a click posts the very viewFile message a linkified
// path in the text posts (path, sid, identity, todoId), so the Files pane opens the file tied to the todo as before,
// and the panel then knows the todo by the file as well. The detail's linkified path keeps opening beside it, and a
// todo without `file` gets no chip. The stand-in is the tree of plain objects the pane's render and click paths
// touch: a selector engine (descendant chains, classes, ids, attribute presence and equality), data-* through
// dataset, text nodes with replaceWith (the path walk splices links in), a tree walker over text nodes, and
// bubbling dispatch to the list's delegate and the modal's. Synthetic only: the notes-api world, placeholder sids,
// paths under /tmp/notes-api.
import { test, after } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const WAITING = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "waiting.ts"), "utf8");

// ── a DOM stand-in ─────────────────────────────────────────────────────────────────────────────────
class Style {
  [key: string]: any;
  setProperty(k: string, v: string): void { this[k] = v; }
  removeProperty(k: string): void { delete this[k]; }
  getPropertyValue(k: string): string { return this[k] ?? ""; }
}
type Kid = El | Txt;
class Txt {
  nodeType = 3;
  parentNode: El | null = null;
  constructor(public data: string) {}
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
    this.parentNode = null;
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
  parentNode: El | null = null;
  childNodes: Kid[] = [];
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
    this.tagName = tagName.toUpperCase();
    this.dataset = new Proxy({} as Record<string, string | undefined>, {
      get: (_t, k) => (typeof k === "string" ? this.attrs.get("data-" + kebab(k)) : undefined),
      set: (_t, k, v) => { this.attrs.set("data-" + kebab(String(k)), String(v)); return true; },
      deleteProperty: (_t, k) => { this.attrs.delete("data-" + kebab(String(k))); return true; },
      has: (_t, k) => this.attrs.has("data-" + kebab(String(k))),
      ownKeys: () => Array.from(this.attrs.keys()).filter((k) => k.startsWith("data-")).map((k) => camel(k.slice(5))),
      getOwnPropertyDescriptor: (_t, k) => (this.attrs.has("data-" + kebab(String(k))) ? { enumerable: true, configurable: true, value: this.attrs.get("data-" + kebab(String(k))) } : undefined),
    });
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
  private detachAll(): void { for (const c of this.childNodes) c.parentNode = null; this.childNodes = []; }
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
const shellPosts: Array<[any, string]> = [];   // what it posts to the SHELL (window.parent)
const win: any = new EventTarget();
// the shell frames this pane: a parent that is not this window, whose document has no Files iframe to focus (the
// focus step then stands down, as it does under a shell without the pane) and no feed frame to open the gear in
win.parent = { postMessage: (m: any, origin: string) => { shellPosts.push([m, origin]); }, document: { getElementById: () => null, defaultView: undefined } };
win.top = win.parent;
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

// ── the world: the notes-api project's api session, two open todos ────────────────────────────────
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
// a child's kind for the order assertions: the chip is openPathLink's .file-uri-link span with .wt-file added, so it reads as the chip
const kinds = (parent: El) => parent.children.map((c) => (c.classList.contains("wt-file") ? "wt-file" : c.className.split(" ")[0]));
const viewFiles = () => shellPosts.filter(([m]) => m && m.romp === "viewFile").map(([m]) => m);

test("boot: the pane renders one row per todo from the frame, and only the todo that names a file wears the chip", async () => {
  await import("./waiting");
  assert.equal(posted.filter((m) => m.type === "ready").length, 1, "the ready handshake");
  await dispatch(frame([WITH_FILE, NO_FILE]));
  assert.equal(list.querySelectorAll(".ut-item").length, 2);
  const chip = row("t1").querySelector(".wt-file");
  assert.ok(chip, "the row of the todo with `file` carries the chip");
  assert.equal(chip!.textContent, "design.md", "the label is the basename");
  assert.equal(chip!.title, FILE, "the full path is the hover");
  assert.ok(chip!.classList.contains("file-uri-link"), "a path link: the same dress class the text's links wear, restyled as a chip");
  assert.equal(chip!.dataset.act, "openpath", "…and the same act, so the list delegate opens it");
  assert.equal(chip!.dataset.path, FILE);
  assert.equal(chip!.dataset.sid, SID, "the todo's own session, as a linkified path carries it");
  assert.equal(chip!.dataset.rel, undefined, "absolute: nothing to resolve");
  assert.equal(chip!.tabIndex, 0, "in the tab order, like the text's links");
  assert.equal(chip!.role, "link");
  // its place on the line: after the text, before the age — the session chip, the words, the file, then when and the buttons
  const line = row("t1").querySelector(".ut-line")!;
  assert.deepEqual(kinds(line), ["wt-sess", "ut-text", "wt-file", "wt-age", "ut-btn", "ut-btn"]);
  assert.equal(row("t2").querySelector(".wt-file"), null, "no `file`, no chip");
  assert.deepEqual(kinds(row("t2").querySelector(".ut-line")!), ["wt-sess", "ut-text", "wt-age", "ut-btn", "ut-btn"]);
});

test("a click on the chip posts the viewFile message a detail link posts: path, the todo's session, its chip identity, the todo id", async () => {
  shellPosts.length = 0;
  const chip = row("t1").querySelector(".wt-file")!;
  chip.dispatch("click");
  assert.deepEqual(viewFiles(), [{ romp: "viewFile", pane: "pane", path: FILE, sid: SID, identity: { name: "api", color: COLOR }, todoId: "t1" }]);
  assert.equal(shellPosts[0][1], "*");
  assert.ok(chip.classList.contains("romp-acted"), "the delegate's press flash: the click acknowledged");
  // Enter on the focused chip is its click (the path link's key handler): the same message again
  shellPosts.length = 0;
  chip.dispatch("keydown", { key: "Enter" });
  assert.deepEqual(viewFiles().map((m) => [m.path, m.todoId]), [[FILE, "t1"]], "the keyboard route opens it too");
});

test("the detail's linkified path still opens beside the chip, with the same session and todo id; the text's words stay plain", async () => {
  shellPosts.length = 0;
  const r = row("t1");
  const detail = r.querySelector(".ut-detail")!;
  const links = detail.querySelectorAll(".file-uri-link");
  assert.deepEqual(links.map((l) => l.textContent), ["docs/design.md"], "the relative path in the detail is linked as before");
  assert.equal(detail.textContent, DETAIL, "the detail reads as written");
  links[0].dispatch("click");
  assert.deepEqual(viewFiles(), [{ romp: "viewFile", pane: "pane", path: "docs/design.md", sid: SID, identity: { name: "api", color: COLOR }, todoId: "t1" }]);
  assert.equal(r.querySelectorAll(".wt-file").length, 1, "one chip, not one per path");
  assert.equal(r.querySelector(".ut-text")!.querySelector(".file-uri-link"), null, "the one-line text names no path: nothing linked there");
});

test("the Reply modal shows the same chip under the quoted line and opens it through its own delegate; a todo without a file gets none", async () => {
  shellPosts.length = 0;
  row("t1").querySelector(".ut-reply")!.dispatch("click");
  const modal = doc.getElementById("ut-reply-prompt");
  assert.ok(modal, "the Reply modal is up");
  const box = modal!.querySelector(".confirm-box")!;
  assert.deepEqual(kinds(box), ["confirm-title", "confirm-detail", "wt-file", "ut-detail", "ut-reply-input", "confirm-actions"], "title, the quoted line, the chip, the detail, the box, the buttons");
  const chip = box.querySelector(".wt-file")!;
  assert.equal(chip.textContent, "design.md"); assert.equal(chip.title, FILE);
  assert.equal(chip.dataset.act, "openpath"); assert.equal(chip.dataset.path, FILE);
  chip.dispatch("click");
  assert.deepEqual(viewFiles(), [{ romp: "viewFile", pane: "pane", path: FILE, sid: SID, identity: { name: "api", color: COLOR }, todoId: "t1" }], "the modal's closure names the session and the todo");
  assert.ok(doc.getElementById("ut-reply-prompt"), "the modal stays up behind the file");
  // the detail's link in the modal opens too, from the same closure
  shellPosts.length = 0;
  box.querySelector(".ut-detail .file-uri-link")!.dispatch("click");
  assert.deepEqual(viewFiles().map((m) => [m.path, m.todoId]), [["docs/design.md", "t1"]]);
  modal!.querySelector(".confirm-actions")!.children[0].dispatch("click");   // Cancel
  assert.equal(doc.getElementById("ut-reply-prompt"), null);
  // the other todo's modal: no chip
  row("t2").querySelector(".ut-reply")!.dispatch("click");
  const other = doc.getElementById("ut-reply-prompt")!;
  assert.equal(other.querySelector(".wt-file"), null, "no `file`, no chip in the modal either");
  assert.deepEqual(kinds(other.querySelector(".confirm-box")!), ["confirm-title", "confirm-detail", "ut-detail", "ut-reply-input", "confirm-actions"]);
  other.querySelector(".confirm-actions")!.children[0].dispatch("click");
});

test("the field is read from every frame: a frame that drops or changes `file` re-renders the row accordingly, and a non-string is no file", async () => {
  await dispatch(frame([{ ...WITH_FILE, file: "/tmp/notes-api/docs/rollout.md" }, { ...NO_FILE, file: 42 }]));
  assert.equal(row("t1").querySelector(".wt-file")!.textContent, "rollout.md");
  assert.equal(row("t1").querySelector(".wt-file")!.title, "/tmp/notes-api/docs/rollout.md");
  assert.equal(row("t2").querySelector(".wt-file"), null, "a malformed field is ignored, never a chip with garbage");
  await dispatch(frame([{ ...WITH_FILE, file: undefined }, NO_FILE]));
  assert.equal(row("t1").querySelector(".wt-file"), null, "the chip goes with the field");
  await dispatch(frame([{ ...WITH_FILE, file: "" }, NO_FILE]));
  assert.equal(row("t1").querySelector(".wt-file"), null, "an empty path is no file");
  await dispatch(frame([WITH_FILE, NO_FILE]));
  assert.equal(row("t1").querySelector(".wt-file")!.textContent, "design.md");
});

test("source pins: the chip is openPathLink's span restyled, plain when the pane is unframed; the modal takes the file from the Reply button", () => {
  assert.match(WAITING, /import \{ linkifyPathTokens, openPathLink \} from "\.\/path-links";/);
  assert.match(WAITING, /interface UserTodo \{ id: string; text: string; createdT: number; detail\?: string; file\?: string; link\?: string \}/);   // link: the address the todo carries (2026-09-08)
  assert.match(WAITING, /function fileChip\(file: string, sid: string\): HTMLElement \{\n\s*const base = file\.replace\(\/\\\/\+\$\/, ""\)\.split\("\/"\)\.pop\(\) \|\| file;\n\s*const chip = framed \? openPathLink\(base, file, false, sid\) : el\("span", ""\);/,
    "a path link when framed (the click has a Files pane to go to), a plain span otherwise — the linkTodoPaths gate");
  assert.match(WAITING, /chip\.classList\.add\("wt-file"\);\n\s*chip\.title = file;/, "the full path is the hover, over openPathLink's own title");
  assert.match(WAITING, /if \(w\.todo\.file\) line\.appendChild\(fileChip\(w\.todo\.file, w\.sid\)\);/);
  assert.match(WAITING, /\(reply as any\)\._utfile = w\.todo\.file \|\| "";/);
  assert.match(WAITING, /function showReply\(sid: string, todoId: string, todoText: string, todoDetail = "", todoFile = "", todoLink = ""\): void \{/);
  assert.match(WAITING, /const chip = todoFile \? fileChip\(todoFile, sid\) : null;/);
  assert.match(WAITING, /box\.append\(h, d\); if \(chip\) box\.appendChild\(chip\); if \(lchip\) box\.appendChild\(lchip\); if \(dd\) box\.appendChild\(dd\); box\.append\(input, actions\);/);
  assert.match(WAITING, /file: typeof t\.file === "string" && t\.file \? t\.file : undefined/, "the frame's field rides through as given, or not at all");
  const CSS = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "waiting-pane.css"), "utf8");
  assert.ok(CSS.includes(".wt-file{"), "the chip has its rule in the pane's sheet");
  assert.ok(CSS.includes("#ut-reply-prompt .wt-file{"), "…and its place in the modal");
});

// ── the web address a todo CARRIES (the user 2026-09-08): `link` rides the frame's rows like `file`; the row and the
// modal show it as a second chip in the file chip's dress, an anchor the pane's URL opener serves (a new tab on the
// web, the host's openExternal under VS Code), never the list delegate: the row's fold under it does not toggle
const LINK = "https://github.com/example-org/notes-api/pull/398";
const WITH_LINK = { id: "t3", text: "Review the pull request", createdT: T0 - 60, detail: "The description is stale.", file: FILE, link: LINK };
const LINK_ONLY = { id: "t4", text: "Read the design note online", createdT: T0 - 30, link: "https://example.invalid/notes-api/design/" };

test("a todo with a link: the row wears the link chip after the file chip; the label is the address without its scheme, the whole address on hover; an anchor, not a path link", async () => {
  await dispatch(frame([WITH_LINK, LINK_ONLY, NO_FILE]));
  const r = row("t3");
  const chip = r.querySelector(".wt-link");
  assert.ok(chip, "the row of the todo with `link` carries the chip");
  assert.equal(chip!.tagName, "A", "an ordinary anchor");
  assert.ok(chip!.classList.contains("url-link"), "the URL anchors' class: the pane's URL opener serves it");
  assert.equal(chip!.getAttribute("href"), LINK);
  assert.equal(chip!.textContent, "github.com/example-org/notes-api/pull/398", "the label: the address without its scheme");
  assert.equal(chip!.title, LINK, "the whole address on hover");
  assert.equal((chip as any).target, "_blank");
  assert.equal((chip as any).rel, "noopener noreferrer");
  assert.equal(chip!.dataset.act, undefined, "no data-act: never the list delegate's openpath");
  assert.ok(!chip!.classList.contains("file-uri-link"), "not a path link");
  const line = r.querySelector(".ut-line")!;
  const names = line.children.map((c) => (c.classList.contains("wt-link") ? "wt-link" : c.classList.contains("wt-file") ? "wt-file" : c.className.split(" ")[0]));
  assert.deepEqual(names, ["wt-sess", "ut-text", "wt-file", "wt-link", "wt-age", "ut-btn", "ut-btn"], "session, text, the file chip, the link chip, then the age and the buttons");
  assert.equal((r.querySelector(".ut-reply") as any)._utlink, LINK, "the Reply button rides the address to the modal");
  // a link without a file: the link chip alone, its trailing slash dropped from the label
  const r4 = row("t4");
  assert.equal(r4.querySelector(".wt-file"), null);
  assert.equal(r4.querySelector(".wt-link")!.textContent, "example.invalid/notes-api/design");
  // no link: no chip, an empty ride
  assert.equal(row("t2").querySelector(".wt-link"), null);
  assert.equal((row("t2").querySelector(".ut-reply") as any)._utlink, "");
});

test("a click on the link chip goes to the URL opener (openLink to the host here, where the page has no http origin), not the list delegate: no fold, no viewFile", async () => {
  await dispatch(frame([WITH_LINK, NO_FILE]));
  posted.length = 0; shellPosts.length = 0;
  const r = row("t3");
  const chip = r.querySelector(".wt-link")!;
  const detail = r.querySelector(".ut-detail")!;
  assert.ok(!detail.classList.contains("open"), "the fold is closed before the click");
  chip.dispatch("pointerdown"); chip.dispatch("pointerup");
  chip.click();
  win.dispatchEvent(new Event("pointerup"));   // the window's release, which the stand-in's bubbling never reaches: the list holds render() while pressed
  assert.deepEqual(posted.filter((m) => m.type === "openLink"), [{ type: "openLink", href: LINK }], "the host's openExternal takes it");
  assert.deepEqual(viewFiles(), [], "no file opened: the chip is not a path link");
  assert.ok(!detail.classList.contains("open"), "the click was spent at the capture phase: uttoggle never folded the row");
});

test("a URL in a todo's TEXT is an anchor as typed (the trailing period outside), and the file chip beside it is untouched", async () => {
  const url = "https://example.invalid/notes-api/pull/12";
  await dispatch(frame([{ id: "t5", text: "Approve " + url + ".", createdT: T0 - 10, file: FILE }, NO_FILE]));
  const r = row("t5");
  const txt = r.querySelector(".ut-text")!;
  const a = txt.querySelector("a.url-link");
  assert.ok(a, "the URL in the text is an anchor");
  assert.equal(a!.textContent, url, "as typed, not shortened");
  assert.equal(a!.getAttribute("href"), url);
  assert.equal((a as any).target, "_blank");
  assert.equal(txt.textContent, "Approve " + url + ".", "the text reads exactly as written; the period is outside the link");
  assert.equal(r.querySelector(".wt-file")!.textContent, "design.md", "the file chip is still the file's");
  assert.equal(r.querySelectorAll(".file-uri-link").length, 1, "the chip is the only path link: nothing in the URL was read as a path");
  posted.length = 0;
  a!.dispatch("pointerdown"); a!.dispatch("pointerup"); a!.click();
  win.dispatchEvent(new Event("pointerup"));
  assert.deepEqual(posted.filter((m) => m.type === "openLink"), [{ type: "openLink", href: url }]);
});

test("Reply on a todo with a link: the modal shows the file chip and then the link chip under the quoted line", async () => {
  await dispatch(frame([WITH_LINK, NO_FILE]));
  (row("t3").querySelector(".ut-reply") as El).click();
  const modal = doc.getElementById("ut-reply-prompt");
  assert.ok(modal, "the Reply modal");
  const box = modal!.querySelector(".confirm-box")!;
  const kindsOf = box.children.map((c) => (c.classList.contains("wt-link") ? "wt-link" : c.classList.contains("wt-file") ? "wt-file" : c.className.split(" ")[0]));
  assert.deepEqual(kindsOf, ["confirm-title", "confirm-detail", "wt-file", "wt-link", "ut-detail", "ut-reply-input", "confirm-actions"]);
  const chip = box.querySelector(".wt-link")!;
  assert.equal(chip.getAttribute("href"), LINK);
  assert.equal(chip.title, LINK);
  assert.equal(chip.textContent, "github.com/example-org/notes-api/pull/398");
  modal!.remove();
});

test("source pins: the link rides the frame's rows and the Reply button, the chip is url-links.ts's anchor in the pane's dress, and the pane installs the URL opener", () => {
  assert.match(WAITING, /import \{ linkifyUrls, urlChip, installUrlLinkOpener \} from "\.\/url-links";/);
  assert.match(WAITING, /installUrlLinkOpener\(document, vscodeApi \? \(m\) => vscodeApi\.postMessage\(m\) : undefined\);/);
  assert.match(WAITING, /function linkChip\(link: string\): HTMLElement \{\n\s*return urlChip\(link, "wt-link"\);\n\}/);
  assert.match(WAITING, /if \(w\.todo\.link\) line\.appendChild\(linkChip\(w\.todo\.link\)\);/);
  assert.ok(WAITING.indexOf("line.appendChild(fileChip(w.todo.file, w.sid))") < WAITING.indexOf("line.appendChild(linkChip(w.todo.link))"), "the file chip first, then the link chip");
  assert.match(WAITING, /\(reply as any\)\._utlink = w\.todo\.link \|\| "";/);
  assert.match(WAITING, /showReply\(sid, tid, \(\(x as any\)\._uttext as string\) \|\| "", \(\(x as any\)\._utdetail as string\) \|\| "", \(\(x as any\)\._utfile as string\) \|\| "", \(\(x as any\)\._utlink as string\) \|\| ""\);/);
  assert.match(WAITING, /const lchip = todoLink \? linkChip\(todoLink\) : null;/);
  assert.match(WAITING, /link: typeof t\.link === "string" && t\.link \? t\.link : undefined/, "the frame's field rides through as given, or not at all");
  const CSS = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "waiting-pane.css"), "utf8");
  assert.ok(CSS.includes(".wt-link,.wt-file{"), "the link chip shares the file chip's rule");
  assert.ok(CSS.includes("a.wt-link{color:var(--accent,#9cd2ff);text-decoration:none}"), "and wears the accent as an anchor on every page");
  assert.ok(CSS.includes("#ut-reply-prompt .wt-link,#ut-reply-prompt .wt-file{"), "and its place in the modal");
});
