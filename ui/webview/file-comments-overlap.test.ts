// Two comments over one passage, and the click on their overlap (plans/markdown-viewer.md Slice 5, item 6; file-comments.ts
// openCovering; the sheets' `.fc-hl .fc-hl` rule). The paint nests the marks: the later comment's paint wraps the text where it
// stands, inside the earlier comment's mark (anchor-map.ts wrapNode, in the Raw view as in Rendered), so the mark under the
// overlap is the innermost and the delegate resolves the control to it (actions.ts, closest("[data-act]")). Before this slice
// fcopen opened that one card, and the outer comment's card could not be reached from the overlapped text (the Slice 5 probe (f):
// a real click on the overlap opened the innermost card alone). Now every covering comment's card opens with the clicked one,
// which is the focus: the one scrolled into view. Driven over the behavior suite's DOM stand-in with the click's `detail` as
// browsers dispatch it (1 from a pointer, 0 from element.click() and the row's keydown): the pointer's click on the nested mark
// opens both cards and scrolls the clicked one; Enter on it does the same; a click on the outer mark alone opens its card alone;
// the click that ends a drag inside the nested mark opens nothing (dragClick stands); and the sheets carry the nested rule
// byte-equal, with the head in the parity list, dropping the wash and the ring and nothing else (the padding stays: open
// question 7's default; the dashed context cue is an outline, untouched). file-comments-overlap-browser.test.ts clicks a real
// mouse over the real panel. Nodes hide their edges at construction (hideEdges, ui/test-dom-shim.ts), so a failing assertion's
// dump shows a node's primitives and not the tree. Synthetic fixtures only: the notes-api world, placeholder ids.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx } from "./file-view";
import type { Status, StoreComment } from "./file-comments-model";
import { makeAnchor } from "./anchor-map";
import { hideEdges } from "../test-dom-shim";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");

// ── fixtures: the notes-api world, a report whose first paragraph carries two overlapping comments ──
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const ROOT = "/repo/notes-api";
const STORE_PATH = ROOT + "/.trackchanges/docs%2Freport.md.json";
const T0 = 1757145600000;
const LINE = "Intro paragraph one with several words in it.";
const DOC = "# Report\n\n## Findings\n" + LINE + "\n\nWe recommend shipping the cache in v1.2.\n\nRisks remain in the fallback path.\n";
const at = (needle: string): number => { const i = DOC.indexOf(needle); assert.ok(i >= 0, needle); return i; };
/** A passage comment anchored as the browser anchors one (24 characters of context either side). */
const commentOn = (id: string, ts: number, quote: string): StoreComment => ({
  id, author: "you", ts, body: "Note " + id + ".", anchor: makeAnchor(DOC, { start: at(quote), end: at(quote) + quote.length }), replies: [], resolved: false,
});
// A, the EARLIER comment (by time), on the paragraph's first three words; B, the LATER one, from its second word past A's end:
// the overlap is "paragraph one", where B's first mark nests inside A's
const OUTER = "Intro paragraph one";
const INNER = "paragraph one with several";
const A = commentOn(T0 + "-1", T0 + 1000, OUTER);
const B = commentOn(T0 + "-2", T0 + 2000, INNER);
function status(): Status {
  return {
    verb: "status", root: ROOT, storePath: STORE_PATH, trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
    store: { v: 3, path: "docs/report.md", suggestions: [], comments: [A, B] },
    hunks: [], log: [],
    unsent: { comments: [A.id, B.id], replies: [], accepted: 0, rejected: 0, watermark: null },
  };
}

// ── the DOM stand-in (the behavior suite's, with a click's `detail`): ancestry, attributes, events, a small selector engine ──
class Ev {
  target: El | Txt | null = null;
  currentTarget: El | null = null;
  defaultPrevented = false;
  stopped = false;
  key: string;
  detail: number;                                  // a click's count: 1 from a pointer, 0 from element.click() and a keyboard activation
  constructor(public type: string, init: { key?: string; detail?: number } = {}) { this.key = init.key || ""; this.detail = init.detail ?? 0; hideEdges(this); }
  preventDefault(): void { this.defaultPrevented = true; }
  stopPropagation(): void { this.stopped = true; }
}
type Listener = (ev: Ev) => void;
type Reg = { type: string; cb: Listener; capture: boolean };
const kebab = (k: string) => k.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
class Txt {
  nodeType = 3;
  parentNode: El | null = null;
  constructor(public data: string) { hideEdges(this); }
  get textContent(): string { return this.data; }
  get length(): number { return this.data.length; }
  get parentElement(): El | null { return this.parentNode; }
  splitText(off: number): Txt {
    const tail = new Txt(this.data.slice(off));
    this.data = this.data.slice(0, off);
    const p = this.parentNode;
    if (p) { const i = p.childNodes.indexOf(this); p.childNodes.splice(i + 1, 0, tail); tail.parentNode = p; }
    return tail;
  }
}
type Compound = { tag: string | null; classes: string[]; attrs: Array<[string, string | null]> };
function parseSel(sel: string): Compound[][] {
  return sel.split(",").map((g) => g.trim()).filter(Boolean).map((g) => g.split(/\s+/).map((s) => {
    const m = /^([a-zA-Z][\w-]*)?((?:\.[\w-]+)*)((?:\[[\w-]+(?:="[^"]*")?\])*)$/.exec(s);
    if (!m) throw new Error("stand-in: unsupported selector " + s);
    const classes = (m[2].match(/\.[\w-]+/g) || []).map((c) => c.slice(1));
    const attrs: Array<[string, string | null]> = [];
    for (const a of m[3].match(/\[[^\]]+\]/g) || []) { const am = /^\[([\w-]+)(?:="([^"]*)")?\]$/.exec(a)!; attrs.push([am[1], am[2] ?? null]); }
    return { tag: m[1] ? m[1].toUpperCase() : null, classes, attrs };
  }));
}
class El {
  nodeType = 1;
  tagName: string;
  parentNode: El | null = null;
  childNodes: Array<El | Txt> = [];
  attrs = new Map<string, string>();
  listeners: Reg[] = [];
  hidden = false; disabled = false; readOnly = false; title = ""; type = ""; value = ""; checked = false; placeholder = "";
  innerHTML = "";
  style: Record<string, string> = {};
  rect = { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 };
  constructor(tag: string) { this.tagName = tag.toUpperCase(); hideEdges(this); }
  get ownerDocument(): typeof doc { return doc; }
  get parentElement(): El | null { return this.parentNode; }
  get firstChild(): El | Txt | null { return this.childNodes[0] || null; }
  get className(): string { return this.attrs.get("class") || ""; }
  set className(v: string) { this.attrs.set("class", v); }
  get classes(): string[] { return this.className.split(/\s+/).filter(Boolean); }
  classList = {
    add: (...c: string[]) => { const s = new Set(this.classes); for (const x of c) s.add(x); this.className = [...s].join(" "); },
    remove: (...c: string[]) => { const s = new Set(this.classes); for (const x of c) s.delete(x); this.className = [...s].join(" "); },
    toggle: (c: string, on?: boolean) => { const want = on === undefined ? !this.classes.includes(c) : on; if (want) this.classList.add(c); else this.classList.remove(c); },
    contains: (c: string) => this.classes.includes(c),
  };
  get tabIndex(): number { return this.attrs.has("tabindex") ? Number(this.attrs.get("tabindex")) : -1; }
  set tabIndex(v: number) { this.attrs.set("tabindex", String(v)); }
  dataset: Record<string, string> = new Proxy({} as Record<string, string>, {
    get: (_, k) => this.attrs.get("data-" + kebab(String(k))) as string,
    set: (_, k, v) => { this.attrs.set("data-" + kebab(String(k)), String(v)); return true; },
    has: (_, k) => this.attrs.has("data-" + kebab(String(k))),
    deleteProperty: (_, k) => { this.attrs.delete("data-" + kebab(String(k))); return true; },
  });
  get textContent(): string { return this.childNodes.map((c) => c.textContent).join(""); }
  set textContent(v: string) { for (const c of this.childNodes) c.parentNode = null; this.childNodes = []; if (v !== "") this.appendChild(new Txt(v)); }
  private detach(n: El | Txt): void { const p = n.parentNode; if (p) { const i = p.childNodes.indexOf(n); if (i >= 0) p.childNodes.splice(i, 1); n.parentNode = null; } }
  appendChild<T extends El | Txt>(n: T): T { this.detach(n); this.childNodes.push(n); n.parentNode = this; return n; }
  insertBefore<T extends El | Txt>(n: T, ref: El | Txt | null): T {
    if (!ref) return this.appendChild(n);
    this.detach(n);
    const i = this.childNodes.indexOf(ref);
    this.childNodes.splice(i < 0 ? this.childNodes.length : i, 0, n); n.parentNode = this; return n;
  }
  removeChild<T extends El | Txt>(n: T): T { this.detach(n); return n; }
  replaceChildren(...c: Array<El | Txt>): void { for (const x of this.childNodes) x.parentNode = null; this.childNodes = []; for (const x of c) this.appendChild(x); }
  remove(): void { this.detach(this); }
  normalize(): void {
    const out: Array<El | Txt> = [];
    for (const c of this.childNodes) {
      if (c instanceof Txt) { if (!c.data) { c.parentNode = null; continue; } const last = out[out.length - 1]; if (last instanceof Txt) { last.data += c.data; c.parentNode = null; continue; } }
      else c.normalize();
      out.push(c);
    }
    this.childNodes = out;
  }
  setAttribute(k: string, v: string): void { this.attrs.set(k, v); }
  getAttribute(k: string): string | null { return this.attrs.has(k) ? (this.attrs.get(k) as string) : null; }
  hasAttribute(k: string): boolean { return this.attrs.has(k); }
  removeAttribute(k: string): void { this.attrs.delete(k); }
  contains(n: El | Txt | null): boolean { for (let x: El | Txt | null = n; x; x = x.parentNode) if (x === this) return true; return false; }
  private fits(c: Compound): boolean {
    return (!c.tag || c.tag === this.tagName) && c.classes.every((k) => this.classes.includes(k))
      && c.attrs.every(([a, v]) => this.attrs.has(a) && (v === null || this.attrs.get(a) === v));
  }
  matches(sel: string): boolean {
    return parseSel(sel).some((chain) => {
      if (!this.fits(chain[chain.length - 1])) return false;
      let k = chain.length - 2;
      for (let a: El | null = this.parentNode; a && k >= 0; a = a.parentNode) if (a.fits(chain[k])) k--;
      return k < 0;
    });
  }
  closest(sel: string): El | null { for (let x: El | null = this; x; x = x.parentNode) if (x.matches(sel)) return x; return null; }
  querySelectorAll(sel: string): El[] {
    const out: El[] = [];
    const visit = (n: El) => { for (const c of n.childNodes) if (c instanceof El) { if (c.matches(sel)) out.push(c); visit(c); } };
    visit(this);
    return out;
  }
  querySelector(sel: string): El | null { return this.querySelectorAll(sel)[0] || null; }
  addEventListener(type: string, cb: Listener, opts?: boolean | { capture?: boolean }): void {
    this.listeners.push({ type, cb, capture: typeof opts === "boolean" ? opts : !!(opts && opts.capture) });
  }
  removeEventListener(type: string, cb: Listener, opts?: boolean | { capture?: boolean }): void {
    const cap = typeof opts === "boolean" ? opts : !!(opts && opts.capture);
    this.listeners = this.listeners.filter((l) => !(l.type === type && l.cb === cb && l.capture === cap));
  }
  dispatchEvent(ev: Ev): boolean { return dispatch(this, ev); }
  click(): void { this.dispatchEvent(new Ev("click", { detail: 0 })); }   // element.click(): no pointer behind it
  focus(): void { doc.activeElement = this; }
  blur(): void { if (doc.activeElement === this) doc.activeElement = null; }
  scrollIntoView(): void { scrolledInto.push(this); }
  getBoundingClientRect(): typeof this.rect { return this.rect; }
  get offsetWidth(): number { return 0; }
}
const scrolledInto: El[] = [];
const doc = hideEdges({
  listeners: [] as Reg[],
  body: null as unknown as El,
  hidden: false,
  activeElement: null as El | null,
  createElement: (tag: string) => new El(tag),
  createTextNode: (s: string) => new Txt(s),
  getElementById: () => null,
  addEventListener(type: string, cb: Listener, opts?: boolean | { capture?: boolean }): void {
    doc.listeners.push({ type, cb, capture: typeof opts === "boolean" ? opts : !!(opts && opts.capture) });
  },
  removeEventListener(type: string, cb: Listener, opts?: boolean | { capture?: boolean }): void {
    const cap = typeof opts === "boolean" ? opts : !!(opts && opts.capture);
    doc.listeners = doc.listeners.filter((l) => !(l.type === type && l.cb === cb && l.capture === cap));
  },
  contains: (n: El | Txt | null) => doc.body.contains(n),
});
doc.body = new El("body");
/** The DOM event path: document capture, ancestors' capture root to target, target and ancestors' bubble, document bubble. */
function dispatch(target: El | Txt, ev: Ev): boolean {
  ev.target = target;
  const chain: El[] = [];
  for (let n: El | null = target instanceof El ? target : target.parentNode; n; n = n.parentNode) chain.push(n);
  const run = (ls: Reg[], capture: boolean, node: El | null): boolean => {
    for (const l of ls.slice()) {
      if (l.type !== ev.type || l.capture !== capture) continue;
      ev.currentTarget = node; l.cb.call(node, ev);
      if (ev.stopped) return true;
    }
    return false;
  };
  if (run(doc.listeners, true, null)) return !ev.defaultPrevented;
  for (let i = chain.length - 1; i >= 0; i--) if (run(chain[i].listeners, true, chain[i])) return !ev.defaultPrevented;
  for (const n of chain) if (run(n.listeners, false, n)) return !ev.defaultPrevented;
  run(doc.listeners, false, null);
  return !ev.defaultPrevented;
}
const win: any = new EventTarget();
win.parent = win; win.innerWidth = 1200; win.innerHeight = 800;
let selection: any = null;
win.getSelection = () => selection;
win.confirm = () => true;
hideEdges(win);
(globalThis as any).window = win;
(globalThis as any).document = doc;
const store = new Map<string, string>();
(globalThis as any).localStorage = {
  getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
  setItem: (k: string, v: string) => { store.set(k, String(v)); },
  removeItem: (k: string) => { store.delete(k); },
};

// ── the viewer stand-in: the body row with Raw rows, the seam as closures, the poll's HEAD answers ──
type World = { ctx: FileViewActionCtx; posted: any[]; main: El; body: El; code: El; hooks: { rendered: Array<() => void>; close: Array<() => void> }; mtimes: Record<string, string>; close(): void };
let cur: World | null = null;
(globalThis as any).fetch = async (url: string) => {
  if (url.includes("/sessions")) return { json: async () => [] };
  const p = decodeURIComponent((/[?&]path=([^&]*)/.exec(url) || [])[1] || "");
  const mt = cur!.mtimes[p];
  return { status: mt === undefined ? 404 : 200, headers: { get: (h: string) => (h === "X-Romp-Mtime-Ns" && mt !== undefined ? mt : null) } };
};
/** The Raw view's rows, as codeBlock builds them: one `.fv-cl > .fv-ct` per line, a trailing newline being no line. */
function rows(code: El, src: string): void {
  const lines = src.split("\n");
  if (lines.length && lines[lines.length - 1] === "") lines.pop();
  code.replaceChildren(...lines.map((ln) => {
    const cl = new El("span"); cl.className = "fv-cl";
    const ct = new El("span"); ct.className = "fv-ct";
    if (ln) ct.appendChild(new Txt(ln));
    cl.appendChild(ct);
    return cl;
  }));
}
function world(): World {
  const main = new El("div"); main.className = "fileview-main";
  const body = new El("div"); body.className = "fileview-body";
  const wrap = new El("div"); wrap.className = "fileview-code";
  const pre = new El("pre"); pre.className = "fileview-pre fileview-wrap";
  const code = new El("code"); code.className = "hljs";
  pre.appendChild(code); wrap.appendChild(pre);
  body.appendChild(wrap);
  main.appendChild(body);
  rows(code, DOC);
  const w = { posted: [] as any[], main, body, code, hooks: { rendered: [] as Array<() => void>, close: [] as Array<() => void> }, mtimes: {} as Record<string, string> } as World;
  w.ctx = {
    path: ABS, sid: SID, todoId: null,
    body: () => body as unknown as HTMLElement, mode: () => "raw", text: () => DOC, mtimeNs: () => "1757145600000000001", media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [],
    identity: () => ({ name: "api", color: null }),
    onRendered: (cb) => { w.hooks.rendered.push(cb); }, onSelection: () => { /* inert */ },
    onSaved: () => { /* inert */ }, onClose: (cb) => { w.hooks.close.push(cb); },
    post: (m) => { w.posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: () => { /* inert */ }, editing: () => false, setTrackedEdit: () => { /* inert */ }, guardClose: () => { /* inert */ },
    aside: (node) => { main.querySelector(".fileview-aside")?.remove(); if (node) { const n = node as unknown as El; n.classList.add("fileview-aside"); main.appendChild(n); } },
    setMode: () => { /* inert */ }, scrollToOffset: () => { /* inert */ },
    reload: () => { rows(code, DOC); for (const cb of w.hooks.rendered) cb(); },
  };
  w.close = () => { for (const cb of w.hooks.close) cb(); if (cur === w) cur = null; };
  cur = w;
  return w;
}
const flush = () => new Promise<void>((r) => setImmediate(r));
const lastOf = (w: World, type: string, verb?: string) => [...w.posted].reverse().find((m) => m.type === type && (verb === undefined || m.verb === verb));
function answer(w: World, s: Status, m = lastOf(w, "fileComments", "status")): void {
  assert.ok(m, "a status ask is outstanding");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: m.reqId, ...s } }));
  w.mtimes[w.ctx.path] = s.fileMtimeNs;
  if (s.storePath && s.storeMtimeNs !== null) w.mtimes[s.storePath] = s.storeMtimeNs;
  if (s.root && s.configMtimeNs !== null) w.mtimes[s.root + "/.trackchanges/config.json"] = s.configMtimeNs;
}
async function openPanel(w: World, s: Status = status()): Promise<{ aside: El }> {
  const fc = await import("./file-comments");
  const unit = fc.fileCommentsAction.mount(w.ctx) as unknown as El;
  const button = unit.childNodes[0] as El;
  answer(w, s); await flush();
  button.click();
  answer(w, s); await flush(); await flush();
  const aside = w.main.querySelector(".fileview-aside")!;
  assert.ok(aside, "the panel is mounted beside the body");
  return { aside };
}
const card = (aside: El, key: string): El => { const c = aside.querySelector('.fc-card[data-id="' + key + '"]'); assert.ok(c, "the card " + key); return c!; };
const isOpen = (aside: El, key: string): boolean => card(aside, key).classes.includes("open");
/** A pointer's click on `el`: detail 1, as a mouse or a finger dispatches it. */
const mouse = (el: El): void => { dispatch(el, new Ev("click", { detail: 1 })); };

/** The panel open over the fixture, and the three marks the two comments paint on the Findings row: A's one mark over
 *  "Intro paragraph one", B's first mark over "paragraph one" NESTED inside it, B's second over " with several" after it. */
async function openWithNest(t: TestContext): Promise<{ w: World; aside: El; outer: El; inner: El; tail: El }> {
  const w = world(); t.after(() => w.close());
  t.after(() => { selection = null; scrolledInto.length = 0; });
  const { aside } = await openPanel(w);
  const marksA = w.body.querySelectorAll('mark.fc-hl[data-act="fcopen"][data-id="' + A.id + '"]');
  const marksB = w.body.querySelectorAll('mark.fc-hl[data-act="fcopen"][data-id="' + B.id + '"]');
  assert.deepEqual(marksA.map((m) => m.textContent), [OUTER], "A paints one mark over its passage");
  assert.deepEqual(marksB.map((m) => m.textContent), ["paragraph one", " with several"], "B paints two marks, cut at A's end");
  const outer = marksA[0], inner = marksB[0], tail = marksB[1];
  assert.ok(outer.contains(inner), "the overlap: B's first mark stands INSIDE A's (the later paint wraps the text where it stands)");
  assert.ok(!outer.contains(tail) && !inner.contains(outer), "B's second mark stands after A's; nothing of A is inside B");
  assert.equal(inner.closest("[data-act]"), inner, "the control a click on the overlap resolves to is the innermost mark, B's");
  assert.equal(isOpen(aside, A.id), false); assert.equal(isOpen(aside, B.id), false);
  return { w, aside, outer, inner, tail };
}

test("the pointer's click on the nested mark opens BOTH cards in one render, the clicked comment's the one scrolled into view (the focus); the outer comment was unreachable from that text before", async (t) => {
  const { aside, inner } = await openWithNest(t);
  mouse(inner); await flush();
  assert.equal(isOpen(aside, B.id), true, "the clicked comment's card opens");
  assert.equal(isOpen(aside, A.id), true, "the covering comment's card opens with it (before this slice only the innermost mark's card opened)");
  assert.equal(scrolledInto.length, 1, "one scroll: the clicked card's (showCard), the covering card opens where it stands");
  assert.equal(scrolledInto[0], card(aside, B.id), "the clicked comment is the focus");
});

test("Enter on the focused nested mark does the same through the row's keydown (a click with no pointer behind it)", async (t) => {
  const { aside, inner } = await openWithNest(t);
  inner.focus();
  dispatch(inner, new Ev("keydown", { key: "Enter" })); await flush();
  assert.equal(isOpen(aside, B.id), true); assert.equal(isOpen(aside, A.id), true, "both cards open on Enter");
  assert.equal(scrolledInto[0], card(aside, B.id), "the clicked comment is the focus");
});

test("a click on the outer mark alone opens its own card alone, and one on B's second mark opens B alone: nothing covers those", async (t) => {
  const { aside, outer, tail } = await openWithNest(t);
  mouse(outer); await flush();
  assert.deepEqual([isOpen(aside, A.id), isOpen(aside, B.id)], [true, false], "the outer mark: A's card only");
  card(aside, A.id).querySelector('[data-act="fccard"]')!.click(); await flush();   // fold it again by its head
  assert.equal(isOpen(aside, A.id), false);
  mouse(tail); await flush();
  assert.deepEqual([isOpen(aside, A.id), isOpen(aside, B.id)], [false, true], "B's mark past A's end: B's card only");
});

test("the click that ends a drag inside the nested mark opens nothing, neither card (dragClick stands before the covering cards are read)", async (t) => {
  const { aside, inner } = await openWithNest(t);
  const words = inner.childNodes[0];
  assert.ok(words instanceof Txt, "the nested mark wraps its words");
  selection = { isCollapsed: false, anchorNode: words, focusNode: words, anchorOffset: 2, focusOffset: 9 };
  mouse(inner); await flush();
  assert.deepEqual([isOpen(aside, A.id), isOpen(aside, B.id)], [false, false], "the drag's click opens nothing");
  assert.equal(scrolledInto.length, 0, "and scrolls nothing");
});

test("the sheets: the nested rule `.fc-hl .fc-hl` drops the wash and the ring and nothing else, byte-equal in styles.css and feed.css, and its head is in the parity list", () => {
  const ruleOf = (css: string): string => { const m = /\n(\.fc-hl \.fc-hl \{[^}]*\})/.exec(css); assert.ok(m, "the nested rule at a line start"); return m![1]; };
  const chat = ruleOf(web("styles.css")), feed = ruleOf(web("feed.css"));
  assert.equal(chat, feed, "the feed page loads only feed.css: the same rule there");
  assert.equal(chat, ".fc-hl .fc-hl { background: none; box-shadow: none; }");
  assert.doesNotMatch(chat, /padding|outline|color:/, "the padding stays (every wrap point where the nest legs measure it: open question 7's default), the dashed context cue is an outline and stays, the ink is the mark's own");
  assert.match(web("fileview-parity.test.ts"), /"\.fc-hl \.fc-hl \{",/, "the head is pinned byte-equal by the parity test too");
  // the base rules the nest drops a level of: a wash and an inset ring on every .fc-hl, the dashed outline on a context mark
  assert.match(web("styles.css"), /\n\.fc-hl \{ background: color-mix\([^;]*; box-shadow: inset /);
  assert.match(web("styles.css"), /\n\.fc-hl-context \{ box-shadow: none; outline: 1\.5px dashed /);
});
