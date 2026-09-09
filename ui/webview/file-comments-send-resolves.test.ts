// A send whose accept-all resolves comments says so and shows them (the lost-update probe, 2026-09-09; plans/file-review.md,
// the arrivals follow-on under Slice 2), driven AS A PANEL over the third review round's stand-in
// (file-comments-review-fixes-3.test.ts, copied here). In the incident the Send's accept-all resolved the seven comments the
// session's edits had answered (the host resolves a comment when its change is accepted), and the panel folded them under a
// collapsed "Resolved (N)" with nothing said. Now the confirm's accept option reads "(resolves M comments)" when M unresolved
// comments are bound to the pending changes, composed with the arrivals' count in one parenthesis; and after a send whose
// accept-all resolved comments, the Resolved fold opens before the renders that follow and the acknowledgment line names what moved.
// The host's rule and the box's default are unchanged. Synthetic fixtures only: the notes-api world, placeholder ids.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import type { FileViewActionCtx } from "./file-view";
import type { Status, StoreComment, Hunk } from "./file-comments-model";

// ── a DOM stand-in: ancestry, attributes, events with capture and bubbling, a small selector engine ──
class Ev {
  target: El | Txt | null = null;
  currentTarget: El | null = null;
  defaultPrevented = false;
  stopped = false;
  key: string;
  ctrlKey: boolean; metaKey: boolean;
  constructor(public type: string, init: { key?: string; ctrlKey?: boolean; metaKey?: boolean } = {}) { this.key = init.key || ""; this.ctrlKey = !!init.ctrlKey; this.metaKey = !!init.metaKey; }
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
win.getSelection = () => null;
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
const F1 = "1757145600000000001", S2 = "1757145600000000002", C3 = "1757145600000000003";
const F55 = "1757145600000000055", S9 = "1757145600000000009", S12 = "1757145600000000012", S22 = "1757145600000000022";
const QUOTE = "shipping the cache in v1.2";
const DOC = "# Report\n\n## Findings\nThe api session cut p95 latency by 40% and the p99 by 10%.\n\nWe recommend " + QUOTE + ".\n\nMore text here.\n";
const first: StoreComment = {
  id: T0 + "-118", author: "you", ts: T0, body: "Which cache? Say which.",
  anchor: { quote: QUOTE, prefix: "We recommend ", suffix: "." }, replies: [], resolved: false,
};
const second: StoreComment = {
  id: (T0 - 60000) + "-40", author: "you", ts: T0 - 60000, body: "Cut this paragraph; it repeats the summary.",
  anchor: { quote: "The api session cut p95 latency by 40%", prefix: "## Findings\n", suffix: " and the" },
  replies: [{ author: "api", authorId: SID, ts: T0 - 30000, body: "Cut it." }], resolved: false,
};
const third: StoreComment = { id: T0 + 9000 + "-0", author: "you", ts: T0 + 9000, body: "Add a summary at the top.", replies: [], resolved: false };
const fourth: StoreComment = { id: T0 + 12000 + "-0", author: "you", ts: T0 + 12000, body: "And a date.", replies: [], resolved: false };
const fifth: StoreComment = { id: T0 + 15000 + "-3", author: "api", authorId: SID, ts: T0 + 15000, body: "Should the p99 line stay?", replies: [], resolved: false };
const NO_UNSENT = { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null };
function status(over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: ROOT, storePath: STORE_PATH, trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
    fileMtimeNs: F1, storeMtimeNs: S2, configMtimeNs: C3,
    store: { v: 3, path: "docs/report.md", suggestions: [], comments: [first, second] },
    hunks: [],
    log: [{ ts: "2026-09-06T07:59:00Z", kind: "send", author: "you", sid: SID, comments: [{ id: second.id, desc: 'on "The api session cut p95 latency by 40%"', body: second.body }], accepted: 0, rejected: 0, queued: false }],
    unsent: { comments: [first.id], replies: [], accepted: 0, rejected: 0, watermark: T0 - 60000 },
    ...over,
  };
}
/** The status after a whole-file comment landed: the given comments, every `you` one past the send unsent. */
function withComments(storeMtimeNs: string, comments: StoreComment[], over: Partial<Status> = {}): Status {
  return status({ storeMtimeNs, store: { v: 3, path: "docs/report.md", suggestions: [], comments },
    unsent: { comments: comments.filter((c) => c.author === "you" && c.id !== second.id).map((c) => c.id), replies: [], accepted: 0, rejected: 0, watermark: T0 - 60000 }, ...over });
}

// ── the viewer stand-in: the body row with Raw rows, the seam as closures, the poll's HEAD answers ──
type World = {
  ctx: FileViewActionCtx; posted: any[]; main: El; body: El; code: El;
  hooks: { rendered: Array<() => void>; saved: Array<(i: { mtimeNs: string; logged: boolean }) => void>; close: Array<() => void> };
  disk: string; reloads: number;
  /** the view's mtime (ctx.mtimeNs): the file's at open, then the saved mtime on a save, then the disk's on a reload */
  viewMtime: string;
  mtimes: Record<string, string>; codes: Record<string, number>; heads: string[];
  setText(src: string): void; close(): void;
};
let cur: World | null = null;
(globalThis as any).fetch = async (url: string) => {
  if (url.includes("/sessions")) return { json: async () => [] };
  const p = decodeURIComponent((/[?&]path=([^&]*)/.exec(url) || [])[1] || "");
  const w = cur!;
  w.heads.push(p);
  if (w.codes[p]) return { status: w.codes[p], headers: { get: () => null } };   // a 413 or 415: the kernel refuses the HEAD
  const mt = w.mtimes[p];
  return { status: mt === undefined ? 404 : 200, headers: { get: (h: string) => (h === "X-Romp-Mtime-Ns" && mt !== undefined ? mt : null) } };
};
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
function world(over: { path?: string; sid?: string | null; todoId?: string | null } = {}): World {
  const main = new El("div"); main.className = "fileview-main";
  const body = new El("div"); body.className = "fileview-body";
  const actions = new El("div"); actions.className = "fileview-actions"; actions.appendChild(new Txt("Rendered · Raw"));
  const wrap = new El("div"); wrap.className = "fileview-code";
  const pre = new El("pre"); pre.className = "fileview-pre fileview-wrap";
  const code = new El("code"); code.className = "hljs";
  pre.appendChild(code); wrap.appendChild(pre);
  body.appendChild(actions); body.appendChild(wrap);
  main.appendChild(body);
  let text = DOC;
  const w = {
    posted: [] as any[], main, body, code,
    hooks: { rendered: [] as Array<() => void>, saved: [] as Array<(i: { mtimeNs: string; logged: boolean }) => void>, close: [] as Array<() => void> },
    disk: text, reloads: 0, viewMtime: F1, mtimes: {} as Record<string, string>, codes: {} as Record<string, number>, heads: [] as string[],
  } as World;
  rows(code, text);
  w.setText = (s) => { text = s; rows(code, s); for (const cb of w.hooks.rendered) cb(); };
  w.ctx = {
    path: over.path ?? ABS, sid: over.sid === undefined ? SID : over.sid, todoId: over.todoId ?? null,
    body: () => body as unknown as HTMLElement, mode: () => "raw", text: () => text, mtimeNs: () => w.viewMtime, media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [],
    identity: () => ({ name: "api", color: null }),
    onRendered: (cb) => { w.hooks.rendered.push(cb); }, onSelection: () => { /* inert */ },
    onSaved: (cb) => { w.hooks.saved.push(cb); }, onClose: (cb) => { w.hooks.close.push(cb); },
    post: (m) => { w.posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: () => { /* inert */ }, editing: () => false, setTrackedEdit: () => { /* inert */ }, guardClose: () => { /* inert */ },
    aside: (node) => { main.querySelector(".fileview-aside")?.remove(); if (node) { const n = node as unknown as El; n.classList.add("fileview-aside"); main.appendChild(n); } },
    setMode: () => { /* inert */ }, scrollToOffset: () => { /* inert */ },
    // fetchFile: the bytes and the mtime now on disk (the HEAD table's, when the test set one)
    reload: () => { w.reloads++; if (w.mtimes[w.ctx.path] !== undefined) w.viewMtime = w.mtimes[w.ctx.path]; w.setText(w.disk); },
  };
  w.close = () => { for (const cb of w.hooks.close) cb(); if (cur === w) cur = null; };
  cur = w;
  return w;
}
const flush = () => new Promise<void>((r) => setImmediate(r));
/** A save acknowledged: the viewer sets its mtime to the saved one BEFORE it fires onSaved (file-view.ts doSave). */
function saved(w: World, mtimeNs: string): void { w.viewMtime = mtimeNs; for (const cb of w.hooks.saved) cb({ mtimeNs, logged: true }); }
const lastOf = (w: World, type: string, verb?: string) => [...w.posted].reverse().find((m) => m.type === type && (verb === undefined || m.verb === verb));
const countOf = (w: World, type: string, verb?: string) => w.posted.filter((m) => m.type === type && (verb === undefined || m.verb === verb)).length;
/** Answer the ask `m` with `s`. `disk` = the HEADs follow this reply's mtimes (the default); false for a reply that
 *  read the disk BEFORE what is now on it, which must not move the stand-in's disk backwards. */
function answer(w: World, s: Status, m = lastOf(w, "fileComments", "status"), disk = true): void {
  assert.ok(m, "an ask is outstanding");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: m.reqId, ...s } }));
  if (!disk) return;
  w.mtimes[w.ctx.path] = s.fileMtimeNs;
  if (s.storePath && s.storeMtimeNs !== null) w.mtimes[s.storePath] = s.storeMtimeNs;
  if (s.root && s.configMtimeNs !== null) w.mtimes[s.root + "/.trackchanges/config.json"] = s.configMtimeNs;
}
function refuse(w: World, m: any, code: string, error: string): void {
  assert.ok(m, "an ask is outstanding");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsFailed", reqId: m.reqId, verb: m.verb, code, error } }));
}
function sent(w: World, m = lastOf(w, "fileCommentsSend")): void {
  assert.ok(m, "a send is outstanding");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsSent", reqId: m.reqId, queued: false } }));
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
const input = (aside: El): El => aside.querySelector(".fc-input")!;
const press = (el: El, key: string) => dispatch(el, new Ev("keydown", { key }));
/** The save chord (Ctrl+Enter; Cmd+Enter is the same key policy): a plain Enter is a newline in the box now. */
const chord = (el: El) => dispatch(el, new Ev("keydown", { key: "Enter", ctrlKey: true }));
const cards = (aside: El): number => aside.querySelectorAll(".fc-card").length;
const sendLabel = (aside: El): string => aside.querySelector('[data-act="fcsend"]')!.textContent;
const errText = (row: El): string => row.childNodes[0].textContent;
/** Comment on this file, a note, Enter: the `comment` ask that goes out. */
async function enterComment(w: World, aside: El, note: string): Promise<any> {
  aside.querySelector('[data-act="fcfile"]')!.click();
  input(aside).value = note;
  chord(input(aside)); await flush();
  const post = lastOf(w, "fileComments", "comment");
  assert.ok(post, "Enter posted the comment");
  return post;
}
/** The file's own markup as the viewer places it: a `.fileview-md` box in the body holding what marked emitted
 *  and DOMPurify kept — here a paragraph of spans carrying the panel's own data-act names. */
function authorMarkup(w: World, acts: Array<[string, Record<string, string>]>): El[] {
  const md = new El("div"); md.className = "fileview-md";
  const p = new El("p"); md.appendChild(p);
  const out = acts.map(([act, data]) => {
    const s = new El("span"); s.dataset.act = act;
    for (const k of Object.keys(data)) s.dataset[k] = data[k];
    s.appendChild(new Txt("read more")); p.appendChild(s);
    return s;
  });
  w.body.appendChild(md);
  return out;
}
const CORRUPT = "the comments for ~/notes-api/docs/report.md could not be read: ~/notes-api/.trackchanges/docs%2Freport.md.json is not valid JSON in the expected shape; nothing was changed";
const MOVED = "the comments for ~/notes-api/docs/report.md changed under this request; nothing was written";
const GATE = "cannot write the comments for ~/notes-api/docs/report.md: dashboard file editing is off on this machine — the viewer's Edit button asks to turn it on";


// ── the scene: two pending changes, one with an open comment of the person's the session answered ──
const P99 = "and the p99 by 10%";
const P99_AT = DOC.indexOf(P99);
const MORE = "More text here.";
const MORE_AT = DOC.indexOf(MORE);
const h1: Hunk = { id: "h1", author: "api", ts: T0 - 30000, kind: "ins", curFrom: P99_AT, curTo: P99_AT + P99.length, baseFrom: P99_AT, baseTo: P99_AT, oldText: "", newText: P99, anchor: null };
const h3: Hunk = { id: "h3", author: "api", ts: T0 - 20000, kind: "ins", curFrom: MORE_AT, curTo: MORE_AT + MORE.length, baseFrom: MORE_AT, baseTo: MORE_AT, oldText: "", newText: MORE, anchor: null };
const REPLY = "The p99 is in now, from the same run.";
/** The person's comment on the first change, with the session's reply and its edit turn (the shape a track-edit answer leaves). */
const bound = (resolved: boolean): StoreComment => ({
  id: (T0 + 500) + "-3", author: "you", ts: T0 + 500, body: "Add the p99 too.", suggestionId: "h1", resolved,
  replies: [{ author: "api", authorId: SID, ts: T0 + 600, body: REPLY }, { author: "api", authorId: SID, ts: T0 + 700, kind: "edit", oldText: "by 40%", newText: "by 40% " + P99 }],
});
const withChanges = (over: Partial<Status> = {}): Status => status({
  store: { v: 3, path: "docs/report.md", suggestions: [{ id: "h1", authorId: SID }, { id: "h3", authorId: SID }], comments: [first, second, bound(false)] },
  hunks: [h1, h3], unsent: { comments: [first.id, bound(false).id], replies: [], accepted: 0, rejected: 0, watermark: T0 - 60000 }, ...over,
});
/** After the accept-all: no pending change, the bound comment resolved (the host's rule), the decisions unsent. */
const accepted = (): Status => status({
  storeMtimeNs: "1757145600000000005", store: { v: 3, path: "docs/report.md", suggestions: [], comments: [first, second, bound(true)] }, hunks: [],
  unsent: { comments: [first.id, bound(false).id], replies: [], accepted: 2, rejected: 0, watermark: T0 - 60000 },
});
const foldOf = (aside: El): El | null => aside.querySelector('[data-act="fcresolved"]');

test("the confirm's accept option names the comments the accept resolves, in one parenthesis with the arrivals' count when both apply", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, withChanges());
  aside.querySelector('[data-act="fcsend"]')!.click();
  const cb = aside.querySelector('input[data-opt="accept"]')!;
  assert.equal(cb.parentNode!.textContent, "accept the 2 pending changes (resolves 1 comment)");
  assert.equal(cb.checked, true, "the default is untouched");
  // the bound comment resolved already: nothing to resolve, the option as before
  aside.querySelector('[data-act="fcsendcancel"]')!.click();
  saved(w, "1757145600000000004"); await flush();
  answer(w, withChanges({ fileMtimeNs: "1757145600000000004", store: { v: 3, path: "docs/report.md", suggestions: [{ id: "h1", authorId: SID }, { id: "h3", authorId: SID }], comments: [first, second, bound(true)] } })); await flush();
  aside.querySelector('[data-act="fcsend"]')!.click();
  assert.equal(aside.querySelector('input[data-opt="accept"]')!.parentNode!.textContent, "accept the 2 pending changes");
});

test("a send whose accept-all resolves the comment: the Resolved fold opens with the comment's card and the session's reply in it, and the acknowledgment line names what moved (before: a collapsed fold, no card, the plain acknowledgment)", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, withChanges());
  assert.equal(foldOf(aside), null, "nothing resolved yet: no fold");
  aside.querySelector('[data-act="fcsend"]')!.click();
  aside.querySelector('[data-act="fcsendgo"]')!.click(); await flush();
  const acc = lastOf(w, "fileComments", "accept-all");
  assert.ok(acc, "the accept-all goes first");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: acc.reqId, ...accepted(), accepted: ["h1", "h3"] } })); await flush(); await flush();
  const msg = lastOf(w, "fileCommentsSend");
  assert.ok(msg, "then the send");
  assert.equal(msg.accepted, 2);
  sent(w); await flush();
  answer(w, status({ storeMtimeNs: "1757145600000000005", store: { v: 3, path: "docs/report.md", suggestions: [], comments: [first, second, bound(true)] }, hunks: [], unsent: NO_UNSENT })); await flush();
  const fold = foldOf(aside);
  assert.ok(fold, "the Resolved fold is offered");
  assert.equal(fold!.textContent, "▾ Resolved (1)", "open (before: ▸ Resolved (1))");
  const card = aside.querySelector('.fc-card[data-id="' + bound(true).id + '"]');
  assert.ok(card, "the resolved comment's card is rendered (before: none)");
  assert.ok(card!.textContent.includes("resolved"), "as resolved");
  card!.querySelector(".fc-card-head")!.click();      // open it: the run of turns shows the session's reply
  const open = aside.querySelector('.fc-card[data-id="' + bound(true).id + '"]')!;
  assert.ok(open.classList.contains("open"));
  assert.ok(open.textContent.includes(REPLY), "with the session's reply");
  assert.match(aside.querySelector(".fc-sent")!.textContent, /^Sent to api at .+ · accepted 2 changes; 1 comment with the session's replies moved to Resolved$/, "the acknowledgment line names what moved (before: the plain acknowledgment)");
});

test("a send that resolves nothing leaves the fold and the note as they were", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, withChanges({ store: { v: 3, path: "docs/report.md", suggestions: [{ id: "h1", authorId: SID }, { id: "h3", authorId: SID }], comments: [first, second] }, unsent: { comments: [first.id], replies: [], accepted: 0, rejected: 0, watermark: T0 - 60000 } }));
  aside.querySelector('[data-act="fcsend"]')!.click();
  assert.equal(aside.querySelector('input[data-opt="accept"]')!.parentNode!.textContent, "accept the 2 pending changes", "no bound comment: nothing to resolve");
  aside.querySelector('[data-act="fcsendgo"]')!.click(); await flush();
  const acc = lastOf(w, "fileComments", "accept-all");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: acc.reqId, ...status({ storeMtimeNs: "1757145600000000005", hunks: [], unsent: { comments: [first.id], replies: [], accepted: 2, rejected: 0, watermark: null } }), accepted: ["h1", "h3"] } })); await flush(); await flush();
  sent(w); await flush(); answer(w, status({ storeMtimeNs: "1757145600000000005", hunks: [], unsent: NO_UNSENT })); await flush();
  assert.equal(foldOf(aside), null, "no resolved comment, no fold");
  assert.match(aside.querySelector(".fc-sent")!.textContent, /^Sent to api at [^·]+$/, "the plain acknowledgment");
});
