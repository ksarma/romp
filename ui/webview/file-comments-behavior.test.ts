// The Comments panel driven AS A PANEL: the real module mounted over a DOM stand-in with ancestry, events
// and selectors, so the anchor-map walkers, the one delegate root, the composer, the poll and the send all
// run for real — what file-comments.test.ts pins at source is exercised as behavior here. Covered: a note
// typed while the file changes underneath (the composer follows the passage, and Save anchors the
// SELECTED passage); a refused mapping has no Save; one write per Enter; the poll's re-read; the todo
// latch keyed on the stamp; the onSaved refresh; touch on the floating button; selections inside the
// panel; the card toggle and keyboard reach; the status wait; a kernel warn leaving a request alone.
// Synthetic fixtures only: the notes-api world, placeholder ids, TESTHOST.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx, TrackedEdit } from "./file-view";
import type { Status, StoreComment } from "./file-comments-model";
import { MOVED_UNDER_EDIT } from "./file-comments-model";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const SRC = web("file-comments.ts");
const FED = web("federation.ts");

// ── a DOM stand-in: ancestry, attributes, events with capture and bubbling, a small selector engine ──
class Ev {
  target: El | Txt | null = null;
  currentTarget: El | null = null;
  defaultPrevented = false;
  stopped = false;
  key: string;
  constructor(public type: string, init: { key?: string } = {}) { this.key = init.key || ""; }
  preventDefault(): void { this.defaultPrevented = true; }
  stopPropagation(): void { this.stopped = true; }
}
type Listener = (ev: Ev) => void;
type Reg = { type: string; cb: Listener; capture: boolean };
const kebab = (k: string) => k.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
class Txt {
  nodeType = 3;
  parentNode: El | null = null;
  constructor(public data: string) {}
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
/** Comma groups of descendant chains (`A B`), each link a compound `tag.class[attr="v"]`. */
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
  constructor(tag: string) { this.tagName = tag.toUpperCase(); }
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
  click(): void { this.dispatchEvent(new Ev("click")); }
  focus(): void { doc.activeElement = this; }
  blur(): void { if (doc.activeElement === this) doc.activeElement = null; }
  scrollIntoView(): void { /* inert */ }
  getBoundingClientRect(): typeof this.rect { return this.rect; }
  get offsetWidth(): number { return 0; }
}
const doc = {
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
};
doc.body = new El("body");
/** The DOM event path: document capture, ancestors' capture root→target, target and ancestors' bubble, document bubble. */
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
(globalThis as any).window = win;
(globalThis as any).document = doc;
const store = new Map<string, string>();
(globalThis as any).localStorage = {
  getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
  setItem: (k: string, v: string) => { store.set(k, String(v)); },
  removeItem: (k: string) => { store.delete(k); },
};

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const ROOT = "/repo/notes-api";
const STORE_PATH = ROOT + "/.trackchanges/docs%2Freport.md.json";
const CONFIG_PATH = ROOT + "/.trackchanges/config.json";
const T0 = 1757145600000;
const QUOTE = "shipping the cache in v1.2";
const DOC = "# Report\n\n## Findings\nThe api session cut p95 latency by 40% and the p99 by 10%.\n\nWe recommend " + QUOTE + ".\n\nMore text here.\n";
const passage: StoreComment = {
  id: T0 + "-118", author: "you", ts: T0, body: "Which cache? Say which.",
  anchor: { quote: QUOTE, prefix: "We recommend ", suffix: "." }, replies: [], resolved: false,
};
const replied: StoreComment = {
  id: (T0 - 60000) + "-40", author: "you", ts: T0 - 60000, body: "Cut this paragraph; it repeats the summary.",
  anchor: { quote: "The api session cut p95 latency by 40%", prefix: "## Findings\n", suffix: " and the" },
  replies: [{ author: "api", authorId: SID, ts: T0 - 30000, body: "Cut it." }], resolved: false,
};
function status(over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: ROOT, storePath: STORE_PATH, trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
    store: { v: 3, path: "docs/report.md", suggestions: [], comments: [passage, replied] },
    hunks: [],
    log: [{ ts: "2026-09-06T07:59:00Z", kind: "send", author: "you", sid: SID, comments: [{ id: replied.id, desc: 'on "The api session cut p95 latency by 40%"', body: replied.body }], accepted: 0, rejected: 0, queued: false }],
    unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 0, watermark: T0 - 60000 },
    ...over,
  };
}

// ── the viewer stand-in: the body row with Raw rows, the seam as closures, the poll's HEAD answers ──
type World = {
  ctx: FileViewActionCtx; posted: any[]; main: El; body: El; code: El; actions: El;
  hooks: { rendered: Array<() => void>; selection: Array<(s: Selection) => void>; saved: Array<(i: { mtimeNs: string; logged: boolean }) => void>; close: Array<() => void> };
  disk: string; reloads: number; scrolls: number[]; modes: string[];
  mtimes: Record<string, string>; heads: string[];
  editing: boolean; tracked: TrackedEdit | null;    // the viewer's edit mode, and the panel's half of editing over pending changes (Slice 5)
  setText(src: string): void; close(): void;
};
let cur: World | null = null;
(globalThis as any).fetch = async (url: string) => {
  if (url.includes("/sessions")) return { json: async () => [] };
  const p = decodeURIComponent((/[?&]path=([^&]*)/.exec(url) || [])[1] || "");
  const w = cur!;
  w.heads.push(p);
  const mt = w.mtimes[p];
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
function world(over: { path?: string; sid?: string | null; todoId?: string | null; src?: string } = {}): World {
  const main = new El("div"); main.className = "fileview-main";
  const body = new El("div"); body.className = "fileview-body";
  const actions = new El("div"); actions.className = "fileview-actions"; actions.appendChild(new Txt("Rendered · Raw"));
  const wrap = new El("div"); wrap.className = "fileview-code";
  const pre = new El("pre"); pre.className = "fileview-pre fileview-wrap";
  const code = new El("code"); code.className = "hljs";
  pre.appendChild(code); wrap.appendChild(pre);
  body.appendChild(actions); body.appendChild(wrap);
  main.appendChild(body);
  let text = over.src ?? DOC;
  const w = {
    posted: [] as any[], main, body, code, actions,
    hooks: { rendered: [] as Array<() => void>, selection: [] as Array<(s: Selection) => void>, saved: [] as Array<(i: { mtimeNs: string; logged: boolean }) => void>, close: [] as Array<() => void> },
    disk: text, reloads: 0, scrolls: [] as number[], modes: [] as string[], mtimes: {} as Record<string, string>, heads: [] as string[],
    editing: false, tracked: null,
  } as World;
  rows(code, text);
  w.setText = (s) => { text = s; rows(code, s); for (const cb of w.hooks.rendered) cb(); };   // the viewer's renderBody + fireRendered
  w.ctx = {
    path: over.path ?? ABS, sid: over.sid === undefined ? SID : over.sid, todoId: over.todoId ?? null,
    body: () => body as unknown as HTMLElement, mode: () => "raw", text: () => text, mtimeNs: () => "1757145600000000001", media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [],
    identity: () => ({ name: "api", color: null }),
    onRendered: (cb) => { w.hooks.rendered.push(cb); }, onSelection: (cb) => { w.hooks.selection.push(cb); },
    onSaved: (cb) => { w.hooks.saved.push(cb); }, onClose: (cb) => { w.hooks.close.push(cb); },
    post: (m) => { w.posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: () => { /* inert */ }, editing: () => w.editing, setTrackedEdit: (t) => { w.tracked = t; },
    aside: (node) => { main.querySelector(".fileview-aside")?.remove(); if (node) { const n = node as unknown as El; n.classList.add("fileview-aside"); main.appendChild(n); } },
    setMode: (m) => { w.modes.push(m); }, scrollToOffset: (n) => { w.scrolls.push(n); },
    reload: () => { w.reloads++; w.setText(w.disk); },   // fetchFile: the bytes now on disk, repainted, the seam's onRendered fired
  };
  w.close = () => { for (const cb of w.hooks.close) cb(); if (cur === w) cur = null; };
  cur = w;
  return w;
}
const flush = () => new Promise<void>((r) => setImmediate(r));
const lastOf = (w: World, type: string, verb?: string) => [...w.posted].reverse().find((m) => m.type === type && (verb === undefined || m.verb === verb));
const countOf = (w: World, type: string, verb?: string) => w.posted.filter((m) => m.type === type && (verb === undefined || m.verb === verb)).length;
function answer(w: World, s: Status, m = lastOf(w, "fileComments", "status")): void {
  assert.ok(m, "a status ask is outstanding");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: m.reqId, ...s } }));
  // the poll's baseline follows the reply: the HEADs answer these mtimes until a test moves one
  w.mtimes[w.ctx.path] = s.fileMtimeNs;
  if (s.storePath && s.storeMtimeNs !== null) w.mtimes[s.storePath] = s.storeMtimeNs;
  if (s.root && s.configMtimeNs !== null) w.mtimes[s.root + "/.trackchanges/config.json"] = s.configMtimeNs;
}
function refuse(w: World, m: any, code: string, error: string): void {
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsFailed", reqId: m.reqId, verb: m.verb, code, error } }));
}
async function mount(w: World): Promise<{ unit: El; button: El }> {
  const fc = await import("./file-comments");
  const unit = fc.fileCommentsAction.mount(w.ctx) as unknown as El;
  return { unit, button: unit.childNodes[0] as El };
}
/** Mount, answer the probe, open the panel, answer its refresh: the panel as a person first sees it. */
async function openPanel(w: World, s: Status = status()): Promise<{ unit: El; button: El; aside: El }> {
  const { unit, button } = await mount(w);
  answer(w, s); await flush();
  button.click();
  answer(w, s); await flush();
  const aside = w.main.querySelector(".fileview-aside")!;
  assert.ok(aside, "the panel is mounted beside the body");
  return { unit, button, aside };
}
function textNodeWith(root: El, needle: string): { node: Txt; at: number } | null {
  for (const c of root.childNodes) {
    if (c instanceof Txt) { const i = c.data.indexOf(needle); if (i >= 0) return { node: c, at: i }; }
    else { const r = textNodeWith(c, needle); if (r) return r; }
  }
  return null;
}
const RECT = { left: 100, top: 200, right: 300, bottom: 220, width: 200, height: 20 };
function selectIn(root: El, quote: string): any {
  const hit = textNodeWith(root, quote);
  assert.ok(hit, "the passage " + JSON.stringify(quote) + " is in the DOM");
  return { rangeCount: 1, isCollapsed: false, anchorNode: hit.node, anchorOffset: hit.at, focusNode: hit.node, focusOffset: hit.at + quote.length,
    toString: () => quote, getRangeAt: () => ({ getBoundingClientRect: () => RECT }) };
}
const theFloat = (): El => { const all = doc.body.querySelectorAll(".fc-float"); return all[all.length - 1]; };
const marksText = (root: El, sel: string) => root.querySelectorAll(sel).map((m) => m.textContent);
const input = (aside: El): El => aside.querySelector(".fc-input")!;
const press = (el: El, key: string) => dispatch(el, new Ev("keydown", { key }));
/** Select `quote` in the body, let the seam fire, and press the floating Comment button. */
function startComment(w: World, quote: string): El {
  const sel = selectIn(w.body, quote);
  for (const cb of w.hooks.selection) cb(sel);
  const float = theFloat();
  assert.equal(float.hidden, false, "the float appears beside a selection in the body");
  selection = sel;
  float.click();
  return float;
}

// ── the composer follows the passage, not its offsets ──────────────────────────────────────────────

test("a note typed while the session inserts text above: the composer follows the passage after the reload, and Save anchors the SELECTED passage", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  startComment(w, QUOTE);
  assert.equal(aside.querySelector(".fc-quote")!.textContent, QUOTE);
  assert.deepEqual(marksText(w.code, ".fc-presel"), [QUOTE], "the presel marks the selected passage");
  const before = DOC.indexOf(QUOTE);
  // the session inserts a paragraph above; the poll saw the file move and the viewer reloaded the bytes
  const NEW = DOC.replace("## Findings\n", "## Findings\nThe session added this paragraph meanwhile.\n\n");
  w.disk = NEW; w.ctx.reload();
  assert.notEqual(NEW.slice(before, before + QUOTE.length), QUOTE, "the old offsets now hold other text — the trap");
  assert.equal(aside.querySelector(".fc-quote")!.textContent, QUOTE, "the chip still names the selected passage");
  assert.equal(aside.querySelector(".fc-composer-ref .fc-tag"), null, "re-found: no passage-changed tag");
  assert.deepEqual(marksText(w.code, ".fc-presel"), [QUOTE], "the presel moved with the passage");
  input(aside).value = "Which cache?";
  press(input(aside), "Enter"); await flush();
  const post = lastOf(w, "fileComments", "comment");
  assert.ok(post, "Enter saves");
  assert.equal(post.args.note, "Which cache?");
  assert.equal(post.args.anchor.quote, QUOTE, "the anchor is the SELECTED passage, not whatever now sits at the old offsets");
  assert.ok(post.args.anchor.prefix.endsWith("We recommend ") && post.args.anchor.prefix.length === 24, "the engine's 24 characters of context, from the text the range indexes");
  assert.ok(post.args.anchor.suffix.startsWith("."));
  assert.equal(post.args.hintOffset, NEW.indexOf(QUOTE), "the hint follows the passage into the new text");
});

test("the passage is gone after the reload: the chip says so, nothing is painted, and Save hands the host the selection-time anchor to rule on", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  startComment(w, QUOTE);
  const start = DOC.indexOf(QUOTE);
  w.disk = DOC.replace("We recommend " + QUOTE + ".\n\n", ""); w.ctx.reload();
  assert.equal(aside.querySelector(".fc-quote")!.textContent, QUOTE);
  assert.equal(aside.querySelector(".fc-composer-ref .fc-tag")!.textContent, "passage changed");
  assert.deepEqual(marksText(w.code, ".fc-presel"), [], "no presel over text that is not the passage");
  input(aside).value = "Which cache?";
  press(input(aside), "Enter"); await flush();
  const post = lastOf(w, "fileComments", "comment");
  assert.equal(post.args.anchor.quote, QUOTE, "the anchor is still the selected passage: the host relocates or refuses, never a wrong passage");
  assert.ok(post.args.anchor.prefix.endsWith("We recommend ") && post.args.anchor.prefix.length === 24, "the engine's 24 characters of context, from the text the range indexes");
  assert.ok(post.args.anchor.suffix.startsWith("."));
  assert.equal(post.args.hintOffset, start);
  // the host's refusal keeps the note where it was typed
  refuse(w, post, "anchor-not-found", "the passage was not found in the file as it is now"); await flush();
  assert.equal(input(aside).value, "Which cache?");
  assert.match(aside.querySelector(".fc-composer .fileview-err")!.textContent, /not found/);
});

test("a view repaint over the SAME text leaves the composer where it was", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  startComment(w, QUOTE);
  w.setText(DOC);   // a rendered→raw switch repaints the same bytes
  assert.deepEqual(marksText(w.code, ".fc-presel"), [QUOTE]);
  assert.equal(aside.querySelector(".fc-composer-ref .fc-tag"), null);
});

// ── a refused mapping has nothing to save to ───────────────────────────────────────────────────────

test("a refused mapping shows no Save; Enter refuses in words and keeps the note — never a silent whole-file comment", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  startComment(w, "Rendered · Raw");   // a selection in the action row, outside the file text: the mapper refuses
  const box = aside.querySelector(".fc-composer")!;
  assert.equal(box.hidden, false, "the composer opens with the refusal");
  assert.match(aside.querySelector(".fc-refused")!.textContent, /outside the file text/);
  assert.ok(aside.querySelector('.fc-composer [data-act="fcraw"]'), "Switch to Raw is offered");
  assert.equal(aside.querySelector('.fc-composer [data-act="fcsave"]'), null, "no Save under a refusal");
  assert.ok(aside.querySelector('.fc-composer [data-act="fccancel"]'), "Cancel stays");
  input(aside).value = "this cell is wrong";
  press(input(aside), "Enter"); await flush();
  assert.equal(lastOf(w, "fileComments", "comment"), undefined, "nothing was posted");
  assert.match(aside.querySelector(".fc-composer .fileview-err")!.textContent, /^Nothing saved: /);
  assert.equal(input(aside).value, "this cell is wrong", "the note survives");
});

// ── the switch to Raw targets the passage in the refused block ─────────────────────────────────────

test("rawTarget: the refused block's own occurrence wins over an earlier copy; the mapper's source spelling survives tabs and CRLF; no occurrence scrolls only", async () => {
  const { rawTarget } = await import("./file-comments");
  const src = "Latency: p95 in prose.\n\n| Route | p95 |\n|---|---|\n| /a | 1 |\n";
  const table = src.indexOf("| Route");
  const base = { ok: false as const, reason: "This selection touches a table; comment on it from the Raw view.", blockStartLine: 2 };
  // the mapper's own rawRange is a first-occurrence lookup (the prose); the selection came from the table
  assert.deepEqual(rawTarget(src, { ...base, rawHasQuote: true, rawRange: { start: 9, end: 12 }, blockStartOffset: table, selText: "p95" }),
    { start: src.indexOf("p95", table), end: src.indexOf("p95", table) + 3 });
  // no rawRange (the contract sheet's shape): the trimmed selection, searched from the block
  assert.deepEqual(rawTarget(src, { ...base, rawHasQuote: true, blockStartOffset: table, selText: "p95\n" }),
    { start: src.indexOf("p95", table), end: src.indexOf("p95", table) + 3 });
  // a fenced block whose source has a tab where the DOM has four spaces: the DOM string is nowhere in the source
  const code = "Intro.\n\n```\ndef handler(request):\n\treturn 1\n```\n";
  const fence = code.indexOf("```");
  const rr = { start: code.indexOf("def"), end: code.indexOf("return 1") + 8 };
  assert.equal(code.indexOf("def handler(request):\n    return 1"), -1, "the DOM spelling misses");
  assert.deepEqual(rawTarget(code, { ...base, rawHasQuote: true, rawRange: rr, blockStartOffset: fence, selText: "def handler(request):\n    return 1" }), rr);
  const crlf = "Intro.\r\n\r\n```\r\nline one\r\nline two\r\n```\r\n";
  const rr2 = { start: crlf.indexOf("line one"), end: crlf.indexOf("line two") + 8 };
  assert.deepEqual(rawTarget(crlf, { ...base, rawHasQuote: true, rawRange: rr2, blockStartOffset: crlf.indexOf("```"), selText: "line one\nline two" }), rr2);
  // the mapper saw no occurrence: null, and the button only scrolls
  assert.equal(rawTarget(src, { ...base, rawHasQuote: false, blockStartOffset: table, selText: "p95" }), null);
  // switchToRaw is wired to it and records the text the new range indexes
  const raw = SRC.split("switchToRaw(): void {")[1].split("\n  }\n")[0];
  assert.match(raw, /const range = rawTarget\(src, r\);/);
  assert.match(raw, /c\.range = range; c\.quote = src\.slice\(range\.start, range\.end\); c\.text = src; c\.refusal = null;/);
  assert.doesNotMatch(raw, /src\.indexOf\(r\.selText\)/, "no first-occurrence lookup of the DOM string");
});

// ── one write per Enter ────────────────────────────────────────────────────────────────────────────

test("a second Enter (or Save click) during the round trip is not a second write: Save disables and relabels, the input is read-only, one `comment` goes", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  aside.querySelector('[data-act="fcfile"]')!.click();
  assert.equal(aside.querySelector(".fc-composer-ref")!.textContent, "On this file");
  input(aside).value = "Add a summary at the top.";
  press(input(aside), "Enter");
  press(input(aside), "Enter");
  await flush();
  aside.querySelector('[data-act="fcsave"]')!.click();
  await flush();
  assert.equal(countOf(w, "fileComments", "comment"), 1, "one write");
  const save = aside.querySelector('[data-act="fcsave"]')!;
  assert.equal(save.disabled, true); assert.equal(save.textContent, "Saving…");
  assert.equal(input(aside).readOnly, true);
  assert.ok(aside.querySelector(".fc-composer .fileview-load"), "the loader while it is out");
  const post = lastOf(w, "fileComments", "comment");
  answer(w, status({ storeMtimeNs: "1757145600000000009" }), post); await flush();
  assert.equal(aside.querySelector(".fc-composer")!.hidden, true, "the reply closes the composer");
  assert.equal(input(aside).value, ""); assert.equal(input(aside).readOnly, false);
});

test("Resolve clicked twice while its request is out resolves once", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  aside.querySelector('.fc-card[data-id="' + passage.id + '"] .fc-card-head')!.click();
  const res = aside.querySelector('[data-act="fcresolve"][data-id="' + passage.id + '"]')!;
  res.click(); res.click();
  await flush();
  assert.equal(countOf(w, "fileComments", "resolve"), 1);
});

// ── the poll: a moved sidecar re-reads status; the file re-baselines on the person's own save ──────

test("the poll: a moved sidecar mtime re-asks status (that is how a track-reply appears), the reply re-baselines, a moved file also reloads the view", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setInterval"] });
  const w = world(); t.after(() => w.close());
  await openPanel(w);
  const asks = countOf(w, "fileComments", "status");
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  assert.equal(countOf(w, "fileComments", "status"), asks, "nothing moved: no re-read");
  assert.ok(w.heads.includes(ABS) && w.heads.includes(STORE_PATH) && w.heads.includes(CONFIG_PATH), "the three targets are HEADed");
  w.mtimes[STORE_PATH] = "1757145600000000022";           // the session's track-reply wrote the sidecar
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  assert.equal(countOf(w, "fileComments", "status"), asks + 1, "a moved sidecar re-reads status");
  assert.equal(w.reloads, 0, "the file did not move: no reload");
  answer(w, status({ storeMtimeNs: "1757145600000000022" })); await flush();
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  assert.equal(countOf(w, "fileComments", "status"), asks + 1, "the reply re-baselined: the same mtime is no change");
  w.mtimes[ABS] = "1757145600000000033";                  // the session wrote the file itself
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  assert.equal(w.reloads, 1, "a moved file repaints the bytes");
  assert.equal(countOf(w, "fileComments", "status"), asks + 2, "…and re-reads status");
});

test("onSaved (a direct edit acknowledged): the Log is re-read, and the poll does not treat the person's own save as a change", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setInterval"] });
  const w = world(); t.after(() => w.close());
  await openPanel(w);
  const asks = countOf(w, "fileComments", "status");
  assert.equal(w.hooks.saved.length, 1, "the panel registered onSaved");
  w.hooks.saved[0]({ mtimeNs: "1757145600000000055", logged: true });
  assert.equal(countOf(w, "fileComments", "status"), asks + 1, "the save re-asks status: the Log gained the edit entry before the reply");
  w.mtimes[ABS] = "1757145600000000055";                  // the disk now carries the saved mtime
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  assert.equal(w.reloads, 0, "the saved mtime is the baseline, not a change");
  assert.equal(countOf(w, "fileComments", "status"), asks + 1);
  answer(w, status({ fileMtimeNs: "1757145600000000055" })); await flush();
});

// ── the todo latch is the stamp, not the attempt ───────────────────────────────────────────────────

const OFF_WARN = "The message was sent, but the request was not marked answered: user todos are turned off on this machine. Turn them on in the gear to answer or dismiss it.";
async function sendOnce(w: World, aside: El, reply: Record<string, unknown>): Promise<{ hadCheckbox: boolean; sent: any }> {
  aside.querySelector('[data-act="fcsend"]')!.click();
  const hadCheckbox = !!aside.querySelector('input[data-opt="todo"]');
  aside.querySelector('[data-act="fcsendgo"]')!.click();
  await flush();
  const sent = lastOf(w, "fileCommentsSend");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsSent", reqId: sent.reqId, queued: false, ...reply } }));
  await flush();
  answer(w, status()); await flush();
  return { hadCheckbox, sent };
}

test("a send the kernel warned it could not stamp leaves the todo checkbox; the send that stamps latches it, and later sends carry no todoId", async (t: TestContext) => {
  const w = world({ todoId: "todo-latch-1" }); t.after(() => w.close());
  const { aside } = await openPanel(w);
  const first = await sendOnce(w, aside, { warning: OFF_WARN });
  assert.equal(first.hadCheckbox, true); assert.equal(first.sent.todoId, "todo-latch-1");
  assert.equal(aside.querySelector(".fc-err-warn")!.textContent.replace(/✕$/, ""), OFF_WARN, "the warning shows, in the warn dress");
  const second = await sendOnce(w, aside, {});
  assert.equal(second.hadCheckbox, true, "not stamped yet: the todo is still answerable from here once the switch is back on");
  assert.equal(second.sent.todoId, "todo-latch-1");
  const third = await sendOnce(w, aside, {});
  assert.equal(third.hadCheckbox, false, "stamped: later sends show no checkbox");
  assert.equal(third.sent.todoId, undefined, "…and carry no todoId");
});

// ── touch: the floating button acts on the lift ────────────────────────────────────────────────────

test("on a phone the float acts on touchend (a cancelled touchstart synthesizes no click), and a finger elsewhere hides it", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  const sel = selectIn(w.body, QUOTE);
  for (const cb of w.hooks.selection) cb(sel);
  const float = theFloat();
  assert.equal(float.hidden, false);
  selection = sel;
  assert.equal(dispatch(float, new Ev("touchstart")), false, "touchstart is cancelled (the selection must survive the press)");
  assert.equal(dispatch(float, new Ev("touchend")), false, "touchend is cancelled too (no second act from a synthesized click)");
  assert.equal(aside.querySelector(".fc-quote")!.textContent, QUOTE, "the tap opened the composer on the selection");
  assert.equal(float.hidden, true);
  // a finger elsewhere hides the float, the way a mousedown does
  for (const cb of w.hooks.selection) cb(sel);
  assert.equal(float.hidden, false);
  dispatch(w.code, new Ev("touchstart"));
  assert.equal(float.hidden, true);
});

// ── a selection inside the panel offers nothing ────────────────────────────────────────────────────

test("selecting text in a card, the Log or the preview shows no Comment button: a passage is text of the file", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  aside.querySelector('.fc-card[data-id="' + replied.id + '"] .fc-card-head')!.click();
  const inCard = selectIn(aside, "Cut it.");
  for (const cb of w.hooks.selection) cb(inCard);
  assert.equal(theFloat().hidden, true, "a selection in the aside: no offer");
  const inBody = selectIn(w.body, QUOTE);
  for (const cb of w.hooks.selection) cb(inBody);
  assert.equal(theFloat().hidden, false, "a selection in the body: the offer");
});

// ── cards: the head toggles, the body is for selecting; keyboard reach ─────────────────────────────

test("an open card's body text is not a collapse target: only the head toggles, and the head is a keyboard control", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  const card = () => aside.querySelector('.fc-card[data-id="' + replied.id + '"]')!;
  assert.equal(card().dataset.act, "fccard", "collapsed: the whole card expands");
  assert.equal(card().querySelector(".fc-card-head")!.tabIndex, 0);
  assert.equal(card().querySelector(".fc-card-head")!.getAttribute("role"), "button");
  assert.equal(card().querySelector(".fc-card-head")!.getAttribute("aria-expanded"), "false");
  card().querySelector(".fc-card-head")!.click();
  assert.equal(card().classList.contains("open"), true);
  assert.equal(card().dataset.act, undefined, "open: the card itself is no longer a click target");
  assert.equal(card().querySelector(".fc-card-head")!.getAttribute("aria-expanded"), "true");
  card().querySelector(".fc-body")!.click();          // a drag-select of the reply text ends in a click here
  assert.equal(card().classList.contains("open"), true, "the body click leaves the card open (and the selection alive)");
  card().querySelector(".fc-replies .fc-body")!.click();
  assert.equal(card().classList.contains("open"), true);
  press(card().querySelector(".fc-card-head")!, "Enter");
  assert.equal(card().classList.contains("open"), false, "Enter on the head collapses");
  press(card().querySelector(".fc-card-head")!, " ");
  assert.equal(card().classList.contains("open"), true, "Space on the head expands");
  // the passage link inside the head is its own keyboard control
  const ref = card().querySelector('[data-act="fcgoto"]')!;
  assert.equal(ref.tabIndex, 0); assert.equal(ref.getAttribute("role"), "button");
});

test("a painted highlight is a Tab stop, and Enter on it opens its card; a Log row with detail is one too", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { button } = await openPanel(w);
  const marks = w.code.querySelectorAll(".fc-hl");
  assert.ok(marks.length >= 2, "both passage comments are painted");
  for (const m of marks) { assert.equal(m.tabIndex, 0); assert.equal(m.getAttribute("role"), "button"); }
  button.click();                                       // close the panel: the highlight must still open it
  assert.equal(w.main.querySelector(".fileview-aside"), null);
  const mark = w.code.querySelector('.fc-hl[data-id="' + passage.id + '"]')!;
  press(mark, "Enter");
  const aside2 = w.main.querySelector(".fileview-aside")!;
  assert.ok(aside2, "Enter on a highlight opens the panel");
  assert.equal(aside2.querySelector('.fc-card[data-id="' + passage.id + '"]')!.classList.contains("open"), true, "…with its card open");
  aside2.querySelector('[data-act="fclog"]')!.click();
  const row = aside2.querySelector('.fc-log-row[data-act="fclogrow"]')!;
  assert.equal(row.tabIndex, 0);
  press(row, "Enter");
  assert.ok(aside2.querySelector(".fc-log-detail"), "Enter on a Log row opens its detail");
});

// ── the status wait wears the loader; a refusal offers Reload ──────────────────────────────────────

test("no status yet: the cards section shows the romp loader while the ask is out, the refusal's line once refused, and the head's row offers Reload", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { unit, button } = await mount(w);
  refuse(w, lastOf(w, "fileComments", "status"), "host-error", "the comments helper crashed"); await flush();
  assert.equal(unit.hidden, false, "a refusal other than no-node reveals the action");
  button.click();
  const aside = w.main.querySelector(".fileview-aside")!;
  assert.ok(aside.querySelector(".fc-sec-cards .fileview-load"), "the loader while the refresh is out");
  assert.equal(aside.querySelector(".fc-sec-cards .fc-empty"), null, "no line claiming a read");
  refuse(w, lastOf(w, "fileComments", "status"), "host-error", "the comments helper crashed"); await flush();
  assert.equal(aside.querySelector(".fc-sec-cards .fileview-load"), null, "refused: no loader");
  assert.match(aside.querySelector(".fc-sec-cards .fc-empty")!.textContent, /could not be read/);
  assert.doesNotMatch(aside.textContent, /Reading the file/);
  const reload = aside.querySelector('.fc-sec-head .fileview-err [data-act="fcreload"]')!;
  assert.ok(reload, "the head's row offers Reload: the one way back in");
  const asks = countOf(w, "fileComments", "status");
  reload.click();
  assert.equal(countOf(w, "fileComments", "status"), asks + 1);
  answer(w, status()); await flush();
  assert.equal(aside.querySelectorAll(".fc-card").length, 2, "the answer renders the cards");
});

// ── a kernel warn on the chat socket leaves a request alone ────────────────────────────────────────

test("an unrelated kernel `warn` leaves an outstanding request in flight; federation's drop of one of our ops fails it", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  aside.querySelector('[data-act="fcfile"]')!.click();
  input(aside).value = "Add a summary."; press(input(aside), "Enter"); await flush();
  let post = lastOf(w, "fileComments", "comment");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "warn", text: "session names use letters, digits, . _ - only." } }));
  await flush();
  assert.equal(aside.querySelector(".fc-composer .fileview-err"), null, "a rename refusal is not this request's failure");
  assert.equal(input(aside).value, "Add a summary.");
  answer(w, status(), post); await flush();
  assert.equal(aside.querySelector(".fc-composer")!.hidden, true, "the real reply still lands: the comment saved once");
  aside.querySelector('[data-act="fcfile"]')!.click();
  input(aside).value = "And a date."; press(input(aside), "Enter"); await flush();
  post = lastOf(w, "fileComments", "comment");
  const drop = "TESTHOST is unreachable (its kernel isn't answering) — “fileComments” was not delivered";
  win.dispatchEvent(new MessageEvent("message", { data: { type: "warn", text: drop } }));
  await flush();
  assert.equal(aside.querySelector(".fc-composer .fileview-err")!.textContent.replace(/✕$/, ""), drop, "the drop of our op is the failure");
  assert.equal(input(aside).value, "And a date.", "the note stays for a retry");
  // the drop notice's shape is federation's; pinned there so a rewording fails here, not in the field
  assert.match(FED, /private dropWarn\(host: string, msg: any\): void \{\n\s*window\.dispatchEvent\(new MessageEvent\("message", \{ data: \{ type: "warn",\n\s*text: `\$\{host\} is unreachable \(its kernel isn't answering\) — “\$\{\(msg && msg\.type\) \|\| "action"\}” was not delivered` \} \}\)\);/);
  const { droppedRequestText } = await import("./file-comments");
  assert.equal(droppedRequestText(drop), drop);
  const sendDrop = "TESTHOST is unreachable (its kernel isn't answering) — “fileCommentsSend” was not delivered";
  assert.equal(droppedRequestText(sendDrop), sendDrop);
  assert.equal(droppedRequestText("TESTHOST is unreachable (its kernel isn't answering) — “saveFile” was not delivered"), null, "another op's drop is not ours");
  assert.equal(droppedRequestText("session names use letters, digits, . _ - only."), null);
  assert.equal(droppedRequestText(undefined), null);
});

// ── Send: the reason it is off is visible ──────────────────────────────────────────────────────────

test("a disabled Send says why in a visible caption, not only a tooltip: no owning session, or nothing unsent", async (t: TestContext) => {
  const w = world({ sid: null }); t.after(() => w.close());
  const { aside } = await openPanel(w);
  const send = aside.querySelector('[data-act="fcsend"]')!;
  assert.equal(send.disabled, true);
  assert.equal(aside.querySelector(".fc-send .fc-note")!.textContent, "No session owns this file; open it from a session's link or todo to send.");
  w.close();
  const w2 = world(); t.after(() => w2.close());
  const sent = status({ unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: T0 } });
  const p2 = await openPanel(w2, sent);
  assert.equal(p2.aside.querySelector('[data-act="fcsend"]')!.disabled, true);
  assert.equal(p2.aside.querySelector(".fc-send .fc-note")!.textContent, "Nothing unsent: every comment, reply, and decision has gone.");
  w2.close();
  const w3 = world(); t.after(() => w3.close());
  const p3 = await openPanel(w3, status({ store: null, unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null } }));
  assert.equal(p3.aside.querySelector(".fc-send .fc-note"), null, "no comments yet: the empty state says it, no caption");
  w3.close();
  const w4 = world(); t.after(() => w4.close());
  const p4 = await openPanel(w4, status());
  assert.equal(p4.aside.querySelector(".fc-send .fc-note"), null, "something to send: no caption");
});

// ── what the stand-in cannot show, pinned at source ────────────────────────────────────────────────

test("source pins: the in-flight guard, the touch handlers, the selection gate, the keyboard root, the stamp latch", () => {
  const mut = SRC.split("async mutate(verb: string, args: Record<string, unknown>, slot: string): Promise<Status | null> {")[1].split("\n  }\n")[0];
  assert.match(mut, /if \(this\.busy\.has\(slot\)\) return null;/, "one write in flight per control");
  assert.ok(mut.indexOf("this.busy.add(slot)") < mut.indexOf("ensureEditingAllowed"), "the slot is held before the consent round trip");
  assert.match(SRC, /this\.float\.addEventListener\("touchend", \(e\) => \{ e\.preventDefault\(\); act\(\); \}\);/);
  assert.match(SRC, /for \(const ev of \["mousedown", "touchstart"\]\) document\.addEventListener\(ev, this\.hideFloatOnDown, true\);/);
  assert.match(SRC, /if \(!body\.contains\(sel\.anchorNode\) \|\| !body\.contains\(sel\.focusNode\)\) return;/);
  assert.match(SRC, /const KEY_ACTS = new Set\(\["fccard", "fcgoto", "fcopen", "fcchange", "fclogrow"\]\);/, "a change mark is a keyboard control too (Slice 2)");
  assert.match(SRC, /if \(answerTodo && reply\.todoStamped\) \{ this\.todoAnswered = true; answeredTodos\.add\(this\.ctx\.todoId!\); \}/);
  assert.match(SRC, /todoStamped: !str\(m\.warning\)/, "the kernel's `warning` on a sent reply is exclusively the nothing-stamped text");
  assert.match(SRC, /const src = c\.text === undefined \? null : c\.text;\n\s*if \(c\.range && src !== null\) \{ args\.anchor = makeAnchor\(src, c\.range\); args\.hintOffset = c\.range\.start; \}/,
    "the anchor is built over the text the range indexes");
  assert.match(SRC, /if \(!c \|\| c\.kind !== "comment" \|\| !c\.range \|\| c\.text !== src\) return;/, "the presel paints only over the text its range indexes");
  assert.match(SRC, /ctx\.onRendered\(\(\) => \{ this\.float\.hidden = true; this\.retargetComposer\(\); this\.paintAll\(\); \}\);/);
  assert.match(SRC, /this\.errors\.set\("head", \{ text: e\.error, reload: true \}\);/, "a refused refresh offers Reload");
  assert.doesNotMatch(SRC, /Reading the file's comments/, "no line claims a read");
});

// ── editing over pending changes (Slice 5): the poll and the paint pass while the editor is up ─────

test("while the editor is up (Slice 5): a moved file never reloads the view — the head says the bytes moved, with no Reload — the sidecar and config are still watched, and the first paint after the edit ends re-reads the bytes and drops the row", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setInterval"] });
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  const asks = countOf(w, "fileComments", "status");
  w.editing = true;
  w.mtimes[ABS] = "1757145600000000033";                  // the session wrote the file under the person's edit
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  assert.equal(w.reloads, 0, "no reload over the person's buffer");
  assert.equal(countOf(w, "fileComments", "status"), asks + 1, "status is still re-read");
  answer(w, status({ fileMtimeNs: "1757145600000000033" })); await flush();
  const row = aside.querySelector(".fc-sec-head .fc-err")!;
  assert.ok(row, "the head says so");
  assert.equal(row.childNodes[0].textContent, MOVED_UNDER_EDIT);
  assert.equal(row.querySelector('[data-act="fcreload"]'), null, "no Reload here: the viewer's own Save refusal offers it, and Cancel re-reads");
  assert.equal(w.reloads, 0);
  // the sidecar is still watched while the editor is up (a reply the session writes shows up in the cards)
  w.mtimes[STORE_PATH] = "1757145600000000044";
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  assert.equal(countOf(w, "fileComments", "status"), asks + 2, "a moved sidecar re-reads status in edit mode too");
  answer(w, status({ fileMtimeNs: "1757145600000000033", storeMtimeNs: "1757145600000000044" })); await flush();
  assert.equal(w.reloads, 0);
  assert.ok(aside.querySelector(".fc-sec-head .fc-err"), "the row stays across the re-read");
  // the edit ends (Cancel): the viewer repaints the OLD bytes and fires onRendered — the panel re-reads the bytes and drops the row
  w.editing = false;
  w.setText(w.disk);
  await flush();
  assert.equal(w.reloads, 1, "the first paint after the edit re-reads the file the session rewrote");
  assert.equal(aside.querySelector(".fc-sec-head .fc-err"), null, "…and the row is gone");
  // the same row after a reject from a card while editing: the second call site, pinned at source
  assert.match(SRC, /this\.ctx\.reload\(\);\n\s*this\.noteMovedUnderEdit\(\);\s*\/\/ a reject from a card while the editor is up/);
  assert.match(SRC, /await this\.refresh\(\);[^\n]*\n\s*this\.noteMovedUnderEdit\(\);/, "…and the poll's, after its refresh");
  assert.match(SRC, /if \(!this\.ctx\.editing\(\) \|\| !s \|\| !laterNs\(s\.fileMtimeNs, this\.ctx\.mtimeNs\(\)\)\) return;/, "keyed on the clocks: the status read a later file than the editor loaded");
});

test("the paint pass stands down while the editor is up (Slice 5): a repaint marks nothing in the body and the panel still renders; the paint after the edit ends marks the passage again", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  assert.ok(w.body.querySelector(".fc-hl"), "read mode: the passage comment is marked in the rows");
  w.editing = true;
  w.setText(w.disk);                                     // the viewer's body swap on Edit: fresh rows, onRendered
  assert.equal(w.body.querySelectorAll(".fc-hl").length, 0, "nothing painted over the editor's host");
  assert.ok(aside.querySelector(".fc-card"), "the cards still render");
  w.editing = false;
  w.setText(w.disk);                                     // Cancel or Save: the read view is back
  assert.ok(w.body.querySelector(".fc-hl"), "…and the marks with it");
  assert.match(SRC, /paintAll\(\): void \{\n\s*if \(this\.ctx\.editing\(\)\) \{ this\.render\(\); return; \}/, "the first line of the pass");
});
