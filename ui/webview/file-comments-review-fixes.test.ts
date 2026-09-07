// The Comments panel's review fixes, driven AS A PANEL over a DOM stand-in that has focus semantics: an element
// takes focus only when it is focusable, and a focused element that leaves the tree hands focus to the body (the
// HTML focus-fixup rule) — the behavior suite's stand-in never moves focus, which is how the keyboard defect hid.
// Covered: a status reply that lands after a newer write's reply (dropped, unless its clocks read a later disk);
// a kernel that never answers a status ask (named after the deadline, and Reload asks again); Enter on a card
// head or a Log row keeping the keyboard where it was across the rebuild; a long path that can wrap.
// Synthetic fixtures only: the notes-api world, placeholder ids, TESTHOST.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import type { FileViewActionCtx } from "./file-view";
import type { Status, StoreComment } from "./file-comments-model";

// ── a DOM stand-in: ancestry, attributes, events with capture and bubbling, selectors, FOCUS ───────
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
  get parentElement(): El | null { return this.parentNode; }
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
  offsetWidth = 0;
  style: Record<string, string> = {};
  constructor(tag: string) { this.tagName = tag.toUpperCase(); }
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
  /** As the browser has it: a tabindex attribute, else 0 for a button or input, else -1 (not focusable). */
  get tabIndex(): number { return this.attrs.has("tabindex") ? Number(this.attrs.get("tabindex")) : (this.tagName === "BUTTON" || this.tagName === "INPUT" ? 0 : -1); }
  set tabIndex(v: number) { this.attrs.set("tabindex", String(v)); }
  dataset: Record<string, string> = new Proxy({} as Record<string, string>, {
    get: (_, k) => this.attrs.get("data-" + kebab(String(k))) as string,
    set: (_, k, v) => { this.attrs.set("data-" + kebab(String(k)), String(v)); return true; },
    has: (_, k) => this.attrs.has("data-" + kebab(String(k))),
    deleteProperty: (_, k) => { this.attrs.delete("data-" + kebab(String(k))); return true; },
  });
  get textContent(): string { return this.childNodes.map((c) => c.textContent).join(""); }
  set textContent(v: string) { for (const c of this.childNodes.slice()) this.detach(c); if (v !== "") this.appendChild(new Txt(v)); }
  /** A node leaves its parent; if it held the focus (itself or a descendant), the focus fixup rule moves it to the body. */
  private detach(n: El | Txt): void {
    const p = n.parentNode;
    if (p) { const i = p.childNodes.indexOf(n); if (i >= 0) p.childNodes.splice(i, 1); n.parentNode = null; }
    if (n instanceof El && doc.activeElement && n.contains(doc.activeElement)) doc.activeElement = doc.body;
  }
  appendChild<T extends El | Txt>(n: T): T { if (n.parentNode) n.parentNode.detach(n); this.childNodes.push(n); n.parentNode = this; return n; }
  insertBefore<T extends El | Txt>(n: T, ref: El | Txt | null): T {
    if (!ref) return this.appendChild(n);
    if (n.parentNode) n.parentNode.detach(n);
    const i = this.childNodes.indexOf(ref);
    this.childNodes.splice(i < 0 ? this.childNodes.length : i, 0, n); n.parentNode = this; return n;
  }
  removeChild<T extends El | Txt>(n: T): T { this.detach(n); return n; }
  replaceChildren(...c: Array<El | Txt>): void { for (const x of this.childNodes.slice()) this.detach(x); for (const x of c) this.appendChild(x); }
  remove(): void { if (this.parentNode) this.parentNode.detach(this); }
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
  /** Focus lands only on a focusable, enabled element — a div with no tabindex ignores focus(), as the browser does. */
  focus(): void { if (this.tabIndex >= 0 && !this.disabled) doc.activeElement = this; }
  blur(): void { if (doc.activeElement === this) doc.activeElement = doc.body; }
  scrollIntoView(): void { /* inert */ }
  getBoundingClientRect(): { left: number; top: number; right: number; bottom: number; width: number; height: number } { return { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 }; }
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
doc.activeElement = doc.body;
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
// the panel's poll interval must never hold the test process open when an assertion fails before dispose()
const realSetInterval = globalThis.setInterval;
(globalThis as any).setInterval = (fn: () => void, ms: number) => { const t = realSetInterval(fn, ms); (t as any).unref?.(); return t; };

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const ROOT = "/repo/notes-api";
const STORE_PATH = ROOT + "/.trackchanges/docs%2Freport.md.json";
const CONFIG_PATH = ROOT + "/.trackchanges/config.json";
const T0 = 1757145600000;
const F1 = "1757145600000000001", S2 = "1757145600000000002", C3 = "1757145600000000003";
const first: StoreComment = {
  id: T0 + "-118", author: "you", ts: T0, body: "Which cache? Say which.",
  anchor: { quote: "shipping the cache in v1.2", prefix: "We recommend ", suffix: "." }, replies: [], resolved: false,
};
const second: StoreComment = {
  id: (T0 - 60000) + "-40", author: "you", ts: T0 - 60000, body: "Cut this paragraph; it repeats the summary.",
  anchor: { quote: "The api session cut p95 latency by 40%", prefix: "## Findings\n", suffix: " and the" },
  replies: [{ author: "api", authorId: SID, ts: T0 - 30000, body: "Cut it." }], resolved: false,
};
const third: StoreComment = { id: T0 + 9000 + "-0", author: "you", ts: T0 + 9000, body: "Add a summary at the top.", replies: [], resolved: false };
const fourth: StoreComment = { id: T0 + 12000 + "-3", author: "api", authorId: SID, ts: T0 + 12000, body: "Should the p99 line stay?", replies: [], resolved: false };
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
/** The status after the person's whole-file comment landed: three cards, two unsent, the sidecar at `storeMtimeNs`. */
function withThird(storeMtimeNs: string, over: Partial<Status> = {}): Status {
  return status({ storeMtimeNs, store: { v: 3, path: "docs/report.md", suggestions: [], comments: [first, second, third] },
    unsent: { comments: [first.id, third.id], replies: [], accepted: 0, rejected: 0, watermark: T0 - 60000 }, ...over });
}

// ── the viewer stand-in: the body row, the seam as closures, the poll's HEAD answers ───────────────
type World = {
  ctx: FileViewActionCtx; posted: any[]; main: El; body: El;
  hooks: { saved: Array<(i: { mtimeNs: string; logged: boolean }) => void>; close: Array<() => void> };
  mtimes: Record<string, string>; close(): void;
};
let cur: World | null = null;
(globalThis as any).fetch = async (url: string) => {
  if (url.includes("/sessions")) return { json: async () => [] };
  const p = decodeURIComponent((/[?&]path=([^&]*)/.exec(url) || [])[1] || "");
  const mt = cur ? cur.mtimes[p] : undefined;
  return { status: mt === undefined ? 404 : 200, headers: { get: (h: string) => (h === "X-Romp-Mtime-Ns" && mt !== undefined ? mt : null) } };
};
function world(over: { path?: string; sid?: string | null } = {}): World {
  const main = new El("div"); main.className = "fileview-main";
  const body = new El("div"); body.className = "fileview-body";
  main.appendChild(body);
  const w = {
    posted: [] as any[], main, body,
    hooks: { saved: [] as Array<(i: { mtimeNs: string; logged: boolean }) => void>, close: [] as Array<() => void> },
    mtimes: {} as Record<string, string>,
  } as World;
  w.ctx = {
    path: over.path ?? ABS, sid: over.sid === undefined ? SID : over.sid, todoId: null,
    body: () => body as unknown as HTMLElement, mode: () => "raw", text: () => null, mtimeNs: () => F1, media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [],
    identity: () => ({ name: "api", color: null }),
    onRendered: () => { /* inert */ }, onSelection: () => { /* inert */ },
    onSaved: (cb) => { w.hooks.saved.push(cb); }, onClose: (cb) => { w.hooks.close.push(cb); },
    post: (m) => { w.posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: () => { /* inert */ },
    aside: (node) => { main.querySelector(".fileview-aside")?.remove(); if (node) { const n = node as unknown as El; n.classList.add("fileview-aside"); main.appendChild(n); } },
    setMode: () => { /* inert */ }, scrollToOffset: () => { /* inert */ }, reload: () => { /* inert */ },
  };
  w.close = () => { for (const cb of w.hooks.close) cb(); if (cur === w) cur = null; };
  cur = w;
  return w;
}
const flush = () => new Promise<void>((r) => setImmediate(r));
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
const input = (aside: El): El => aside.querySelector(".fc-input")!;
const press = (el: El, key: string) => dispatch(el, new Ev("keydown", { key }));
const cards = (aside: El): number => aside.querySelectorAll(".fc-card").length;
const sendLabel = (aside: El): string => aside.querySelector('[data-act="fcsend"]')!.textContent;
/** Comment on this file, a note, Enter: the `comment` ask that goes out. */
async function enterComment(w: World, aside: El, note: string): Promise<any> {
  aside.querySelector('[data-act="fcfile"]')!.click();
  input(aside).value = note;
  press(input(aside), "Enter"); await flush();
  const post = lastOf(w, "fileComments", "comment");
  assert.ok(post, "Enter posted the comment");
  return post;
}
const F55 = "1757145600000000055", S9 = "1757145600000000009", S12 = "1757145600000000012", S22 = "1757145600000000022", S30 = "1757145600000000030";

// ── replies land in the order their asks were issued ───────────────────────────────────────────────

test("a status asked before a comment and answered after it does not take the new card away — and the poll's baseline stays with the newer reply", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setInterval"] });
  const w = world(); t.after(() => w.close());
  const { aside, button } = await openPanel(w);
  assert.equal(cards(aside), 2); assert.equal(sendLabel(aside), "Send to session (1)");
  // a direct edit is acknowledged: the panel re-asks status (A) so the Log shows the edit entry
  w.hooks.saved[0]({ mtimeNs: F55, logged: true });
  const A = lastOf(w, "fileComments", "status");
  // before A is answered the person presses Enter on a whole-file comment (B); the kernel runs the two concurrently
  const B = await enterComment(w, aside, "Add a summary at the top.");
  assert.ok(B.reqId > A.reqId, "B was asked after A");
  answer(w, withThird(S9, { fileMtimeNs: F55 }), B); await flush();
  assert.equal(cards(aside), 3, "B's reply shows the new card");
  assert.equal(sendLabel(aside), "Send to session (2)");
  assert.equal(button.textContent, "Comments · 3");
  // A lands now, from a host run that read the sidecar BEFORE B's write
  answer(w, status({ fileMtimeNs: F55 }), A, false); await flush();
  assert.equal(cards(aside), 3, "the older reply is not applied over the newer one: the card stays");
  assert.equal(sendLabel(aside), "Send to session (2)", "…and Send's count does not drop");
  assert.equal(button.textContent, "Comments · 3");
  // the poll's baseline is B's too: the disk holds B's mtimes, so the next tick sees nothing move and asks nothing
  const asks = countOf(w, "fileComments", "status");
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  assert.equal(countOf(w, "fileComments", "status"), asks, "no re-read against a regressed baseline: the card never flaps");
});

test("the poll's own ask, outlasting a store-moved retry, lands nowhere: the retried comment's reply is the newer world", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setInterval"] });
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  const asks = countOf(w, "fileComments", "status");
  w.mtimes[STORE_PATH] = S22;                          // the session's track-reply wrote the sidecar
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  assert.equal(countOf(w, "fileComments", "status"), asks + 1, "a moved sidecar re-asks status (A)");
  const A = lastOf(w, "fileComments", "status");
  // the person's comment B carries the old fence; the host refuses it, the panel re-asks (A2) and retries (B2)
  const B = await enterComment(w, aside, "Add a summary at the top.");
  assert.equal(B.fence.storeMtimeNs, S2);
  refuse(w, B, "store-moved", "the comments for ~/notes-api/docs/report.md changed under this request; nothing was written"); await flush();
  const A2 = lastOf(w, "fileComments", "status");
  assert.ok(A2.reqId > B.reqId, "the refusal re-asked status");
  answer(w, status({ storeMtimeNs: S22 }), A2); await flush();
  const B2 = lastOf(w, "fileComments", "comment");
  assert.ok(B2.reqId > A2.reqId && B2.fence.storeMtimeNs === S22, "the retry carries the fresh fence");
  answer(w, withThird(S30), B2); await flush();
  assert.equal(cards(aside), 3); assert.equal(aside.querySelector(".fc-composer")!.hidden, true, "saved: the composer closed");
  // the poll's A, answered at last from a read that predates B2's write
  answer(w, status({ storeMtimeNs: S22 }), A, false); await flush();
  assert.equal(cards(aside), 3, "A's older world does not replace B2's");
  assert.equal(sendLabel(aside), "Send to session (2)");
  const after = countOf(w, "fileComments", "status");
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  assert.equal(countOf(w, "fileComments", "status"), after, "the baseline is B2's: nothing to re-read");
});

test("an older ask whose reply read a LATER disk is new information and lands", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  w.hooks.saved[0]({ mtimeNs: F55, logged: true });
  const A = lastOf(w, "fileComments", "status");
  const B = await enterComment(w, aside, "Add a summary at the top.");
  answer(w, withThird(S9, { fileMtimeNs: F55 }), B); await flush();
  assert.equal(cards(aside), 3);
  // A's run started late: it read the sidecar after B's write AND after the session's own track-comment
  const later = status({ fileMtimeNs: F55, storeMtimeNs: S12, store: { v: 3, path: "docs/report.md", suggestions: [], comments: [first, second, third, fourth] },
    unsent: { comments: [first.id, third.id], replies: [], accepted: 0, rejected: 0, watermark: T0 - 60000 } });
  answer(w, later, A); await flush();
  assert.equal(cards(aside), 4, "a later reading of the disk is applied whatever its ask's place in line");
});

test("newerStatus: any of the three clocks moving forward, digit strings ordered as numbers, a value beating null, no claim from equal or non-digit values", async () => {
  const { newerStatus } = await import("./file-comments");
  const base = status();
  assert.equal(newerStatus(status(), base), false, "equal clocks: not newer");
  assert.equal(newerStatus(status({ storeMtimeNs: S9 }), base), true);
  assert.equal(newerStatus(status({ fileMtimeNs: F55 }), base), true);
  assert.equal(newerStatus(status({ configMtimeNs: "1757145600000000004" }), base), true);
  assert.equal(newerStatus(base, status({ storeMtimeNs: S9 })), false, "the other direction is older");
  assert.equal(newerStatus(status({ storeMtimeNs: "9" }), base), false, "shorter digit string = smaller number, whatever the text order");
  assert.equal(newerStatus(status({ storeMtimeNs: "10000000000000000000" }), base), true, "a longer digit string is the larger number");
  assert.equal(newerStatus(status({ storeMtimeNs: S2 }), status({ storeMtimeNs: null, store: null })), true, "a sidecar that now exists is a later reading than none");
  assert.equal(newerStatus(status({ storeMtimeNs: null, store: null }), base), false, "…and the reverse claims nothing (the poll settles a deletion)");
  assert.equal(newerStatus(status({ storeMtimeNs: "not-a-clock" }), base), false, "a value that is not digits orders nothing");
});

// ── a kernel that never answers ────────────────────────────────────────────────────────────────────

test("a remote kernel that never answers the status ask: after the deadline the action appears naming the machine, the panel's head says why, and Reload asks again", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const w = world({ sid: "TESTHOST:" + SID }); t.after(() => w.close());
  const { unit, button } = await mount(w);
  const probe = lastOf(w, "fileComments", "status");
  assert.equal(probe.sid, "TESTHOST:" + SID, "the ask is routed to the owning kernel by its host-prefixed sid");
  t.mock.timers.tick(14999); await flush();
  assert.equal(unit.hidden, true, "within the deadline: still waiting on the kernel");
  t.mock.timers.tick(1); await flush();
  assert.equal(unit.hidden, false, "past it: the action appears so the reason can be read");
  assert.equal(button.textContent, "Comments");
  assert.equal(button.title, "Comments: No answer from the kernel on TESTHOST after 15 s. It may predate file comments: update and restart it, then Reload to ask again.");
  // an answer arriving now lands nowhere: that ask was retired
  answer(w, status(), probe, false); await flush();
  assert.equal(button.textContent, "Comments", "a retired ask's reply is not applied");
  button.click();
  const aside = w.main.querySelector(".fileview-aside")!;
  assert.match(aside.querySelector(".fc-sec-head .fc-err")!.textContent, /No answer from the kernel on TESTHOST/, "the head's row names the machine and the reason");
  assert.ok(aside.querySelector(".fc-sec-cards .fileview-load"), "the open re-asks and waits with the loader");
  t.mock.timers.tick(15000); await flush();
  assert.equal(aside.querySelector(".fc-sec-cards .fileview-load"), null, "the loader has a backstop: it cannot trap the person");
  assert.match(aside.querySelector(".fc-sec-cards .fc-empty")!.textContent, /could not be read/);
  const row = aside.querySelector(".fc-sec-head .fc-err")!;
  assert.match(row.textContent, /No answer from the kernel on TESTHOST after 15 s/);
  const reload = row.querySelector('[data-act="fcreload"]')!;
  assert.ok(reload, "Reload is the way back in");
  const asks = countOf(w, "fileComments", "status");
  reload.click();
  assert.equal(countOf(w, "fileComments", "status"), asks + 1, "Reload asks again");
  answer(w, status()); await flush();                   // the kernel was updated meanwhile
  assert.equal(cards(aside), 2, "the answer renders the cards");
  assert.equal(aside.querySelector(".fc-sec-head .fc-err"), null, "…and the no-answer row is gone");
  assert.equal(button.textContent, "Comments · 2");
});

test("a status answered in time arms no failure; a mutating verb is never failed by the clock; the local kernel is named 'this machine'", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const w = world(); t.after(() => w.close());
  const { aside, button } = await openPanel(w);
  t.mock.timers.tick(15000); await flush();
  assert.equal(aside.querySelector(".fc-sec-head .fc-err"), null, "answered asks leave nothing behind when the deadline passes");
  assert.equal(button.textContent, "Comments · 2");
  // a comment whose reply takes longer than the deadline: still in flight — failing it could duplicate a landed write
  const B = await enterComment(w, aside, "Add a summary at the top.");
  t.mock.timers.tick(15000); await flush();
  assert.equal(aside.querySelector(".fc-composer .fc-err"), null, "no failure from the clock");
  assert.equal(aside.querySelector('[data-act="fcsave"]')!.textContent, "Saving…", "still waiting on the kernel's own answer");
  answer(w, withThird(S9), B); await flush();
  assert.equal(aside.querySelector(".fc-composer")!.hidden, true, "the late reply still lands");
  assert.equal(cards(aside), 3);
  // a refresh's status ask the kernel drops names this machine (a bare sid: the local kernel)
  w.hooks.saved[0]({ mtimeNs: F55, logged: true });
  t.mock.timers.tick(15000); await flush();
  const row = aside.querySelector(".fc-sec-head .fc-err")!;
  assert.match(row.textContent, /^No answer from the kernel on this machine after 15 s\./);
  assert.ok(row.querySelector('[data-act="fcreload"]'));
  assert.equal(cards(aside), 3, "the panel keeps what it had");
  // the answer to a later ask retires that row
  w.hooks.saved[0]({ mtimeNs: F55, logged: true });
  answer(w, withThird(S9, { fileMtimeNs: F55 })); await flush();
  assert.equal(aside.querySelector(".fc-sec-head .fc-err"), null, "a status answers a status refusal's row");
});

// ── the keyboard stays on the control it activated ─────────────────────────────────────────────────

test("Enter on a card's head, then Enter again: the rebuilt head takes the focus, so the second press collapses; the same for a Log row and a fold button", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  const headOf = () => aside.querySelector('.fc-card[data-id="' + first.id + '"] .fc-card-head')!;
  const h0 = headOf();
  h0.focus();
  assert.equal(doc.activeElement, h0, "Tab reached the head");
  press(h0, "Enter");
  const h1 = headOf();
  assert.notEqual(h1, h0, "the rebuild made a new head node");
  assert.equal(h1.getAttribute("aria-expanded"), "true", "Enter opened the card");
  assert.equal(doc.activeElement, h1, "…and the keyboard is on the new head, not the body");
  press(doc.activeElement!, "Enter");
  assert.equal(headOf().getAttribute("aria-expanded"), "false", "the second Enter collapses it");
  assert.equal(doc.activeElement, headOf());
  press(doc.activeElement!, " ");
  assert.equal(headOf().getAttribute("aria-expanded"), "true", "Space works the same way");
  // a Log row with detail
  aside.querySelector('[data-act="fclog"]')!.click();
  const rowOf = () => aside.querySelector('.fc-log-row[data-act="fclogrow"]')!;
  const r0 = rowOf();
  r0.focus(); press(r0, "Enter");
  assert.ok(aside.querySelector(".fc-log-detail"), "Enter on the row opens its detail");
  assert.notEqual(rowOf(), r0); assert.equal(doc.activeElement, rowOf(), "the new row holds the focus");
  press(doc.activeElement!, "Enter");
  assert.equal(aside.querySelector(".fc-log-detail"), null, "the second Enter closes it");
  // a <button> the rebuild replaces: the Log fold
  const l0 = aside.querySelector('[data-act="fclog"]')!;
  l0.focus(); l0.click();
  assert.notEqual(aside.querySelector('[data-act="fclog"]'), l0);
  assert.equal(doc.activeElement, aside.querySelector('[data-act="fclog"]'), "a rebuilt button is re-found by its action");
  // the composer's input keeps its focus through a re-render, as before
  aside.querySelector('[data-act="fcfile"]')!.click();
  assert.equal(doc.activeElement, input(aside));
  w.hooks.saved[0]({ mtimeNs: F55, logged: true });
  answer(w, status({ fileMtimeNs: F55 })); await flush();
  assert.equal(doc.activeElement, input(aside), "the input is never rebuilt, so nothing moved");
  aside.querySelector('[data-act="fccancel"]')!.click();
  // a control the rebuild removed: Cancel on the tracking choice — the focus falls to the body, quietly
  w.hooks.saved[0]({ mtimeNs: F55, logged: true });
  answer(w, status({ fileMtimeNs: F55, trackedBy: null })); await flush();
  aside.querySelector('[data-act="fctrack"]')!.click();
  const cancel = aside.querySelector('[data-act="fctrackcancel"]')!;
  cancel.focus(); cancel.click();
  assert.equal(aside.querySelector('[data-act="fctrackcancel"]'), null, "the row is gone");
  assert.equal(doc.activeElement, doc.body, "nothing to re-find: no throw, no stray focus");
});

// ── a long path can wrap ───────────────────────────────────────────────────────────────────────────

test("a long path wraps: the folder button and the folder-off note break after every slash and may shrink; an error row wraps anywhere", async (t: TestContext) => {
  const DEEP = "/repo/notes-api/docs/reports/quarterly/latency/appendix/report.md";
  const w = world({ path: DEEP }); t.after(() => w.close());
  // the store's `path` is the file's relpath from the root, written by the host from the resolved path (store-io's
  // relPathFor): the panel names the folder from root + path, the kernel's own spelling (filePath), so the fixture
  // must carry the opened file's relpath — a status for this file cannot say "docs/report.md"
  const rel = "docs/reports/quarterly/latency/appendix/report.md";
  const { aside } = await openPanel(w, status({ trackedBy: null, storePath: ROOT + "/.trackchanges/" + encodeURIComponent(rel) + ".json",
    store: { v: 3, path: rel, suggestions: [], comments: [first, second] } }));
  aside.querySelector('[data-act="fctrack"]')!.click();
  const f = aside.querySelector('.fc-choice [data-act="fctrackfolder"]')!;
  assert.equal(f.textContent, "Its folder /repo/notes-api/docs/reports/quarterly/latency/appendix/", "the label reads as before");
  assert.equal(f.querySelectorAll("wbr").length, 7, "a break opportunity after each of the eight segments' slashes but the last");
  assert.equal(f.style.overflowWrap, "anywhere", "a single component wider than the aside still wraps");
  assert.equal(f.style.flex, "0 1 auto", "the button may shrink to its row (.fileview-btn is flex: 0 0 auto)");
  assert.equal(f.style.minWidth, "0");
  assert.equal(f.style.textAlign, "left");
  // the folder-off confirm names the entry the same way
  w.hooks.saved[0]({ mtimeNs: F55, logged: true });
  answer(w, status({ fileMtimeNs: F55, trackedBy: { kind: "folder", entry: "docs/reports/quarterly/latency/appendix/" } })); await flush();
  aside.querySelector('[data-act="fctrack"]')!.click();
  const note = aside.querySelector(".fc-choice .fc-note")!;
  assert.equal(note.textContent, "Stop tracking everything under docs/reports/quarterly/latency/appendix/?");
  assert.equal(note.querySelectorAll("wbr").length, 4);
  assert.equal(note.style.overflowWrap, "anywhere");
  // an error row: the host names a path in its refusal (tilde-collapsed, still one unbroken token)
  w.hooks.saved[0]({ mtimeNs: F55, logged: true });
  refuse(w, lastOf(w, "fileComments", "status"), "store-moved", "the comments for ~/notes-api/docs/reports/quarterly/latency/appendix/report.md changed under this request; nothing was written"); await flush();
  const err = aside.querySelector(".fc-sec-head .fc-err")!;
  assert.match(err.textContent, /^the comments for ~\/notes-api/);
  assert.equal((err.childNodes[0] as El).style.overflowWrap, "anywhere", "the text span wraps anywhere");
  // the split itself
  const { pathSegments } = await import("./file-comments");
  assert.deepEqual(pathSegments("/a/b/c.md"), ["/", "a/", "b/", "c.md"]);
  assert.deepEqual(pathSegments("docs/"), ["docs/"]);
  assert.deepEqual(pathSegments("README"), ["README"]);
  assert.deepEqual(pathSegments("/"), ["/"]);
  assert.deepEqual(pathSegments(""), []);
  assert.equal(pathSegments("/repo/notes-api/docs/reports/quarterly/latency/appendix/").join(""), "/repo/notes-api/docs/reports/quarterly/latency/appendix/", "nothing is lost in the split");
});

// ── Send stands down while a status refusal stands ─────────────────────────────────────────────────

test("a status refusal over a showing status disables Send until a fresh status lands: the unsent list was derived from a disk the kernel can no longer read", async (t: TestContext) => {
  // The panel keeps the last status showing after a refusal so the cards stay readable — but a Send built
  // from it would go out (and be recorded again) against a file deleted or moved since, or a sidecar gone
  // corrupt: the duplicate-send leg of the review's finding. Send is off, says why, and a click posts nothing.
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  assert.equal(aside.querySelector('[data-act="fcsend"]')!.disabled, false, "one unsent comment: Send is on");
  w.hooks.saved[0]({ mtimeNs: F55, logged: true });
  refuse(w, lastOf(w, "fileComments", "status"), "unreadable", "cannot read ~/notes-api/docs/report.md: ENOENT"); await flush();
  assert.equal(cards(aside), 2, "the cards stay readable");
  const send = aside.querySelector('[data-act="fcsend"]')!;
  assert.equal(send.disabled, true, "Send stands down");
  assert.equal(send.title, "The comments could not be re-read; Reload above, then send");
  assert.equal(aside.querySelector(".fc-send .fc-note")!.textContent, "The comments could not be re-read, so nothing can be sent until Reload above succeeds.");
  const before = countOf(w, "fileCommentsSend");
  send.click(); await flush();
  assert.equal(aside.querySelector('[data-act="fcsendgo"]'), null, "no confirm opens");
  assert.equal(countOf(w, "fileCommentsSend"), before, "nothing was posted");
  // Reload in the head asks again; a status answers the refusal and Send is back
  aside.querySelector('.fc-sec-head [data-act="fcreload"]')!.click(); await flush();
  answer(w, status({ fileMtimeNs: F55 })); await flush();
  assert.equal(aside.querySelector('[data-act="fcsend"]')!.disabled, false, "a fresh status re-enables Send");
  assert.equal(aside.querySelector(".fc-send .fc-note"), null);
});

// ── a send refused editing-off re-offers the consent and retries once ──────────────────────────────

test("a send the kernel refuses editing-off runs the consent-then-retry branch every mutating verb runs; a declined consent shows the refusal and sends nothing more", async (t: TestContext) => {
  // The kernel refuses fileCommentsSend while file editing is off: the send's log entry is a disk write, and a
  // send the log cannot record would be offered again. Its refusal text carries the phrase the consent helper
  // matches, so the panel re-offers the consent (naming the machine) and, on yes, sends the same message once more.
  const w = world(); t.after(() => w.close());
  const asked: string[] = [];
  let consent = true;
  w.ctx.ensureEditingAllowed = async (refusal?: string) => { asked.push(refusal ?? "(first consent)"); return consent; };
  const { aside } = await openPanel(w);
  const REFUSAL = "nothing was sent: the send would not be recorded in the comments log for ~/notes-api/docs/report.md while dashboard file editing is off on this machine — the viewer's Edit button asks to turn it on";
  aside.querySelector('[data-act="fcsend"]')!.click();
  aside.querySelector('[data-act="fcsendgo"]')!.click(); await flush();
  const s1 = lastOf(w, "fileCommentsSend");
  assert.ok(s1, "the first send went out");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsSendFailed", reqId: s1.reqId, code: "editing-off", error: REFUSAL } })); await flush();
  assert.deepEqual(asked, [REFUSAL], "the consent is re-offered with the kernel's own text, the way mutateOnce does it");
  const s2 = lastOf(w, "fileCommentsSend");
  assert.notEqual(s2.reqId, s1.reqId, "a yes sends once more");
  assert.deepEqual({ ...s2, reqId: 0 }, { ...s1, reqId: 0 }, "the same message");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsSent", reqId: s2.reqId, queued: false } })); await flush();
  answer(w, status({ unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: T0 } })); await flush();
  assert.match(aside.querySelector(".fc-sent")!.textContent, /^Sent to api at /);
  assert.equal(aside.querySelector(".fc-send .fc-err"), null, "no error row after the retry succeeded");
  // a second refusal after the yes is the error row, not a loop
  w.close();
  const w2 = world(); t.after(() => w2.close());
  asked.length = 0;
  w2.ctx.ensureEditingAllowed = async (refusal?: string) => { asked.push(refusal ?? "(first consent)"); return true; };
  const p2 = await openPanel(w2);
  p2.aside.querySelector('[data-act="fcsend"]')!.click();
  p2.aside.querySelector('[data-act="fcsendgo"]')!.click(); await flush();
  const t1 = lastOf(w2, "fileCommentsSend");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsSendFailed", reqId: t1.reqId, code: "editing-off", error: REFUSAL } })); await flush();
  const t2 = lastOf(w2, "fileCommentsSend");
  assert.notEqual(t2.reqId, t1.reqId);
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsSendFailed", reqId: t2.reqId, code: "editing-off", error: REFUSAL } })); await flush();
  assert.equal(asked.length, 1, "one consent per click: the second refusal is not re-offered");
  assert.equal(lastOf(w2, "fileCommentsSend").reqId, t2.reqId, "and nothing more went out");
  assert.match(p2.aside.querySelector(".fc-send .fc-err")!.textContent, /^nothing was sent: the send would not be recorded/);
  // a declined consent: the refusal shows, nothing more is sent
  w2.close();
  const w3 = world(); t.after(() => w3.close());
  consent = false; asked.length = 0;
  w3.ctx.ensureEditingAllowed = async (refusal?: string) => { asked.push(refusal ?? "(first consent)"); return consent; };
  const p3 = await openPanel(w3);
  p3.aside.querySelector('[data-act="fcsend"]')!.click();
  p3.aside.querySelector('[data-act="fcsendgo"]')!.click(); await flush();
  const u1 = lastOf(w3, "fileCommentsSend");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsSendFailed", reqId: u1.reqId, code: "editing-off", error: REFUSAL } })); await flush();
  assert.deepEqual(asked, [REFUSAL]);
  assert.equal(lastOf(w3, "fileCommentsSend").reqId, u1.reqId, "a no sends nothing more");
  assert.match(p3.aside.querySelector(".fc-send .fc-err")!.textContent, /^nothing was sent: the send would not be recorded/);
  assert.equal(p3.aside.querySelector('[data-act="fcsend"]')!.disabled, false, "Send is back for another try");
});
