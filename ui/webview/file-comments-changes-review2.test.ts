// The Comments panel's change cards, driven AS A PANEL for what the Slice 2 review's second round found
// (plans/file-review.md, Slice 2; the contract's fence rule): a status ask that read the sidecar BEFORE an accept-all
// pruned it, answered after, no longer brings the decided changes back with live buttons (provablyNewer: a sidecar
// mtime against an applied null is no proof of a later read); a DETACHED change's card offers no Accept, Reject, Reply
// or Reveal and the foot counts pending changes only; a by-id Accept refused after the refresh removed its card still
// shows its refusal (and its wait) where the card was, as does the foot's when nothing is pending any more; the
// standalone card of a comment whose change was decided wears the decision's tag; the window between a reject's reply
// and its reload wears the romp loader, with the same deadline backstop a status ask has; and Enter on a painted mark
// keeps the keyboard on the mark's successor through the repaints that opening the panel runs. The stand-in is the
// review suite's (focus semantics: a focusable enabled element takes focus; a removed one drops it to the body), with
// a reload that can be held until the test lands it. Synthetic fixtures only: the notes-api world, placeholder ids.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import type { FileViewActionCtx } from "./file-view";
import { type Status, type Hunk, type StoreComment, type LogEntry, DETACHED_GROUP_TITLE } from "./file-comments-model";

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const ROOT = "/repo/notes-api";
const STORE_PATH = ROOT + "/.trackchanges/docs%2Freport.md.json";
const T0 = 1757145600000;
const DOC = "# Report\n\n## Findings\nThe api session cut p95 latency by 40% and the p99 by 10%.\n\n"
  + "We recommend shipping the cache in v1.2.\n\nRisks remain in the fallback path.\n\nNext steps: measure again.\n";
const at = (needle: string, src = DOC): number => { const i = src.indexOf(needle); assert.ok(i >= 0, needle); return i; };
const H = (id: string, kind: Hunk["kind"], from: number, to: number, oldText: string, newText: string, ts = T0 - 90000): Hunk =>
  ({ id, author: "api", ts, kind, curFrom: from, curTo: to, baseFrom: from, baseTo: from + oldText.length, oldText, newText, anchor: null });
const h1 = H("h1", "sub", at("cut"), at("cut") + 3, "reduced", "cut");
const h3 = H("h3", "del", at("shipping"), at("shipping"), "quickly ", "", T0 - 70000);
const h5 = H("h5", "ins", at(" again"), at(" again") + 6, "", " again", T0 - 50000);
/** The same change with its offsets moved by `n` — hunks computed over another string. */
const shifted = (h: Hunk, n: number): Hunk => ({ ...h, curFrom: h.curFrom + n, curTo: h.curTo + n });
const passage: StoreComment = {
  id: T0 + "-118", author: "you", ts: T0, body: "Which cache? Say which.",
  anchor: { quote: "shipping the cache in v1.2", prefix: "We recommend ", suffix: "." }, replies: [], resolved: false,
};
/** A comment bound to h1 and nothing else: on the change's card while h1 is pending, its own card once h1 is decided. */
const bound: StoreComment = { id: T0 + 1000 + "-5", author: "you", ts: T0 + 1000, body: "Say cut, not reduced.", suggestionId: "h1", replies: [], resolved: false };
// a detached op as store-io keeps it: the engine's op record with `detached: true`, at its LAST place in a text that
// has moved on (300 is past the end of DOC), and a comment bound to it
const D1 = { id: "d1", author: "api", authorId: SID, ts: T0 - 40000, kind: "sub", from: 300, oldText: "cold starts were slow",
  newText: "cold starts stay slow", anchor: { quote: "cold starts stay slow", prefix: "and ", suffix: "." }, detached: true };
const onD1: StoreComment = { id: T0 + 5000 + "-300", author: "you", ts: T0 + 5000, body: "Keep the old wording.", suggestionId: "d1", replies: [], resolved: false };
const SUGG = [{ id: "h1", author: "api", authorId: SID, ts: T0 - 90000, kind: "sub", from: h1.curFrom, oldText: "reduced", newText: "cut" },
  { id: "h3", author: "api", ts: T0 - 70000, kind: "del", from: h3.curFrom, oldText: "quickly " }];
const ACCEPT_LOG: LogEntry = { ts: "2026-09-06T08:01:00Z", kind: "accept", author: "you", changes: [{ id: "h1", oldText: "reduced", newText: "cut" }] };
const REJECT_LOG: LogEntry = { ts: "2026-09-06T08:02:00Z", kind: "reject", author: "you", changes: [{ id: "h1", oldText: "reduced", newText: "cut" }] };
const F1 = "1757145600000000001", S2 = "1757145600000000002", C3 = "1757145600000000003";
const S5 = "1757145600000000005", S9 = "1757145600000000009", F11 = "1757145600000000011", S12 = "1757145600000000012", F21 = "1757145600000000021", S22 = "1757145600000000022";
function status(over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: ROOT, storePath: STORE_PATH, trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
    fileMtimeNs: F1, storeMtimeNs: S2, configMtimeNs: C3,
    store: { v: 3, path: "docs/report.md", suggestions: SUGG, comments: [passage] },
    hunks: [h1, h3], log: [],
    unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 0, watermark: null },
    ...over,
  };
}
const MOVED_STORE = "the comments for ~/notes-api/docs/report.md changed on disk since you opened the file — reload and retry";
const NO_CHANGE = "change h1 is no longer pending in ~/notes-api/docs/report.md — reload and retry";
const NO_PENDING = "no changes are pending in ~/notes-api/docs/report.md — reload and retry";

// ── the DOM stand-in: ancestry, attributes, events, focus, a small selector engine ─────────────────
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
  scrollIntoView(): void { scrolledInto.push(this); }
  getBoundingClientRect(): typeof this.rect { return this.rect; }
  get offsetWidth(): number { return 0; }
}
const scrolledInto: El[] = [];
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

// ── the viewer stand-in: a Raw body, the seam as closures, a file whose mtime the view tracks ──────
type World = {
  ctx: FileViewActionCtx; posted: any[]; main: El; body: El;
  hooks: { rendered: Array<() => void>; close: Array<() => void> };
  disk: string; diskMtime: string; viewMtime: string; reloads: number; scrolls: number[]; modes: string[];
  mtimes: Record<string, string>;
  /** The held reload's landing (deferReload): the bytes and mtime now on disk, repainted, onRendered fired. */
  landReload: (() => void) | null;
  close(): void;
};
let cur: World | null = null;
(globalThis as any).fetch = async (url: string) => {
  if (url.includes("/sessions")) return { json: async () => [{ id: SID, name: "api", bg: "#123456", fg: "#ffffff" }] };
  const p = decodeURIComponent((/[?&]path=([^&]*)/.exec(url) || [])[1] || "");
  const mt = cur!.mtimes[p];
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
type WorldOpts = { src?: string; deferReload?: boolean };
function world(over: WorldOpts = {}): World {
  const main = new El("div"); main.className = "fileview-main";
  const body = new El("div"); body.className = "fileview-body";
  main.appendChild(body);
  let text = over.src ?? DOC;
  const wrap = new El("div"); wrap.className = "fileview-code";
  const pre = new El("pre"); pre.className = "fileview-pre fileview-wrap";
  const code = new El("code"); code.className = "hljs";
  pre.appendChild(code); wrap.appendChild(pre); body.appendChild(wrap);
  rows(code, text);
  const w = {
    posted: [] as any[], main, body,
    hooks: { rendered: [] as Array<() => void>, close: [] as Array<() => void> },
    disk: text, diskMtime: F1, viewMtime: F1, reloads: 0, scrolls: [] as number[], modes: [] as string[], mtimes: {} as Record<string, string>,
    landReload: null as (() => void) | null,
  } as World;
  const setText = (s: string) => { text = s; rows(code, s); for (const cb of w.hooks.rendered) cb(); };
  const land = () => { w.landReload = null; w.viewMtime = w.diskMtime; setText(w.disk); };
  w.ctx = {
    path: ABS, sid: SID, todoId: null,
    body: () => body as unknown as HTMLElement, mode: () => "raw", text: () => text, mtimeNs: () => w.viewMtime, media: () => null,
    identity: () => ({ name: "api", color: null }),
    onRendered: (cb) => { w.hooks.rendered.push(cb); }, onSelection: () => { /* inert */ },
    onSaved: () => { /* inert */ }, onClose: (cb) => { w.hooks.close.push(cb); },
    post: (m) => { w.posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: () => { /* inert */ },
    aside: (node) => { main.querySelector(".fileview-aside")?.remove(); if (node) { const n = node as unknown as El; n.classList.add("fileview-aside"); main.appendChild(n); } },
    setMode: (m) => { w.modes.push(m); }, scrollToOffset: (n) => { w.scrolls.push(n); },
    // fetchFile: an async GET in the real seam — held here until the test lands it (deferReload), else at once
    reload: () => { w.reloads++; if (over.deferReload) w.landReload = land; else land(); },
  };
  w.close = () => { for (const cb of w.hooks.close) cb(); if (cur === w) cur = null; };
  cur = w;
  return w;
}
const flush = () => new Promise<void>((r) => setImmediate(r));
const lastOf = (w: World, type: string, verb?: string) => [...w.posted].reverse().find((m) => m.type === type && (verb === undefined || m.verb === verb));
const countOf = (w: World, type: string, verb?: string) => w.posted.filter((m) => m.type === type && (verb === undefined || m.verb === verb)).length;
/** Answer the ask `m` with `s`. `disk` = the HEADs follow this reply's mtimes (the default) — a reply with no sidecar
 *  takes it OFF the disk, as a prune does; false for a reply that read the disk BEFORE what is now on it, which must
 *  not move the stand-in's disk backwards. */
function answer(w: World, s: Status, m = lastOf(w, "fileComments", "status"), extra: Record<string, unknown> = {}, disk = true): void {
  assert.ok(m, "an ask is outstanding");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: m.reqId, ...s, ...extra } }));
  if (!disk) return;
  w.mtimes[w.ctx.path] = s.fileMtimeNs;
  if (s.storePath) { if (s.storeMtimeNs !== null) w.mtimes[s.storePath] = s.storeMtimeNs; else delete w.mtimes[s.storePath]; }
  if (s.root && s.configMtimeNs !== null) w.mtimes[s.root + "/.trackchanges/config.json"] = s.configMtimeNs;
}
function refuse(w: World, m: any, code: string, error: string): void {
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsFailed", reqId: m.reqId, verb: m.verb, code, error } }));
}
/** Mount and answer the probe: the action row's button, the panel still closed (its marks are painted all the same). */
async function mount(w: World, s: Status = status()): Promise<{ unit: El; button: El }> {
  const fc = await import("./file-comments");
  const unit = fc.fileCommentsAction.mount(w.ctx) as unknown as El;
  const button = unit.childNodes[0] as El;
  answer(w, s); await flush();
  return { unit, button };
}
async function openPanel(w: World, s: Status = status()): Promise<{ unit: El; button: El; aside: El }> {
  const { unit, button } = await mount(w, s);
  button.click();
  answer(w, s); await flush(); await flush();
  const aside = w.main.querySelector(".fileview-aside")!;
  assert.ok(aside, "the panel is mounted beside the body");
  scrolledInto.length = 0;
  return { unit, button, aside };
}
const card = (aside: El, key: string): El | null => aside.querySelector('.fc-card[data-id="' + key + '"]');
const act = (root: El, a: string, id?: string): El | null => root.querySelector('[data-act="' + a + '"]' + (id ? '[data-id="' + id + '"]' : ""));
const texts = (els: El[]) => els.map((e) => e.textContent);
const marksOf = (w: World, id?: string): El[] => w.body.querySelectorAll('[data-act="fcchange"]' + (id ? '[data-id="' + id + '"]' : ""));
const tags = (c: El): string[] => texts(c.querySelectorAll(".fc-card-head .fc-tag"));
const isLink = (c: El): boolean => c.querySelector(".fc-ref")!.classes.includes("fc-link");
const press = (el: El, key: string) => dispatch(el, new Ev("keydown", { key }));
const NO_COMMENTS = { v: 3, path: "docs/report.md", suggestions: SUGG, comments: [] as StoreComment[] };
const UNSENT_NONE = { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null };

// ── a stale reading after a pruning decision ───────────────────────────────────────────────────────

test("a status asked before an accept-all that pruned the sidecar, answered after it, does not bring the decided changes back: no cards, no Accept, the glance and the poll's baseline stay with the pruned reply", async (t: TestContext) => {
  // the host's afterDecision prunes a sidecar left with no changes and no comments (pruneIfClean), so the reply carries
  // store null and storeMtimeNs null. The open's own refresh is still out when Accept all is clicked; its host run read the
  // sidecar BEFORE the write and answers after it with two hunks and the old sidecar mtime. Before: newerStatus judged that
  // value "later than null" and applyStatus re-installed it — two cards with live buttons over a sidecar the host had
  // deleted, until the next poll tick (a card move on no new information, CLAUDE.md).
  t.mock.timers.enable({ apis: ["setInterval"] });
  const w = world(); t.after(() => w.close());
  const before = status({ store: NO_COMMENTS, unsent: UNSENT_NONE });
  const { button } = await mount(w, before);
  button.click(); await flush();
  const A = lastOf(w, "fileComments", "status");
  const aside = w.main.querySelector(".fileview-aside")!;
  assert.ok(card(aside, "chg:h1") && card(aside, "chg:h3"), "two pending changes show from the probe's status");
  assert.equal(button.textContent, "Comments · 0 · 2 changes");
  act(aside, "fcacceptall")!.click(); await flush();
  const acc = lastOf(w, "fileComments", "accept-all");
  assert.ok(acc, "the accept-all went while A is still out");
  const pruned = status({ store: null, hunks: [], storeMtimeNs: null, unsent: { ...UNSENT_NONE, accepted: 2 } });
  answer(w, pruned, acc, { accepted: ["h1", "h3"] }); await flush(); await flush();
  assert.equal(card(aside, "chg:h1"), null); assert.equal(card(aside, "chg:h3"), null);
  assert.equal(button.textContent, "Comments · tracked", "the glance: a tracked file with no sidecar");
  // A answers now, from the read that predates the write
  answer(w, before, A, {}, false); await flush(); await flush();
  assert.equal(card(aside, "chg:h1"), null, "the stale reading is dropped: the accepted change does not come back");
  assert.equal(card(aside, "chg:h3"), null);
  assert.equal(aside.querySelectorAll('[data-act="fcaccept"], [data-act="fcreject"], [data-act="fcacceptall"]').length, 0, "no live button over a deleted sidecar");
  assert.equal(button.textContent, "Comments · tracked", "…and the glance does not flap");
  // the poll's baseline is the pruned reply's: the sidecar is absent on disk, so the next tick sees nothing move
  const asks = countOf(w, "fileComments", "status");
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  assert.equal(countOf(w, "fileComments", "status"), asks, "no re-read against a baseline that names a sidecar the host deleted");
});

test("the same after a reject-all that pruned the sidecar, though the file's clock moved: a stale read with the old file mtime and a sidecar mtime lands nowhere; a stale read against a SURVIVING sidecar is dropped as before", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const before = status({ store: NO_COMMENTS, unsent: UNSENT_NONE });
  const { button } = await mount(w, before);
  button.click(); await flush();
  const A = lastOf(w, "fileComments", "status");
  const aside = w.main.querySelector(".fileview-aside")!;
  act(aside, "fcrejectall")!.click();
  act(aside, "fcrejectallgo")!.click(); await flush();
  const rej = lastOf(w, "fileComments", "reject-all");
  w.disk = DOC.replace("cut", "reduced").replace("shipping", "quickly shipping"); w.diskMtime = F21;
  answer(w, status({ fileMtimeNs: F21, store: null, hunks: [], storeMtimeNs: null, unsent: { ...UNSENT_NONE, rejected: 2 } }), rej, { rejected: ["h1", "h3"] });
  await flush(); await flush();
  assert.equal(w.reloads, 1); assert.equal(aside.querySelectorAll(".fc-card").length, 0);
  answer(w, before, A, {}, false); await flush(); await flush();
  assert.equal(aside.querySelectorAll(".fc-card").length, 0, "the file's clock says older; the sidecar's says nothing: dropped");
  assert.equal(button.textContent, "Comments · tracked");
  w.close();
  // a comment keeps the sidecar: the accept-all's reply carries a NEWER sidecar mtime, so the stale value reads as older
  const w2 = world(); t.after(() => w2.close());
  const { button: b2 } = await mount(w2);
  b2.click(); await flush();
  const A2 = lastOf(w2, "fileComments", "status");
  const a2 = w2.main.querySelector(".fileview-aside")!;
  act(a2, "fcacceptall")!.click(); await flush();
  answer(w2, status({ storeMtimeNs: S5, hunks: [], store: { ...NO_COMMENTS, suggestions: [], comments: [passage] }, unsent: { ...UNSENT_NONE, comments: [passage.id], accepted: 2 } }),
    lastOf(w2, "fileComments", "accept-all"), { accepted: ["h1", "h3"] }); await flush(); await flush();
  answer(w2, status(), A2, {}, false); await flush(); await flush();
  assert.equal(card(a2, "chg:h1"), null, "the control: a stale read against a surviving sidecar is dropped by its clock");
  assert.equal(b2.textContent, "Comments · 1");
});

test("provablyNewer: a sidecar or config mtime against an applied null proves nothing, while newerStatus still counts it; clocks both hold, and the file's, decide", async () => {
  const { provablyNewer, newerStatus } = await import("./file-comments");
  const gone = status({ store: null, hunks: [], storeMtimeNs: null });
  assert.equal(newerStatus(status(), gone), true, "the general comparison: a sidecar that exists reads later than none");
  assert.equal(provablyNewer(status(), gone), false, "…but for a suspect reply that value may predate the prune: no proof");
  assert.equal(provablyNewer(status({ configMtimeNs: "1757145600000000004" }), status({ configMtimeNs: null })), false, "the config the same way");
  assert.equal(provablyNewer(status({ fileMtimeNs: F11 }), gone), true, "the file's clock, never null, decides");
  assert.equal(provablyNewer(status({ storeMtimeNs: S9 }), status()), true, "a clock both hold: later is later");
  assert.equal(provablyNewer(status(), status({ storeMtimeNs: S9 })), false);
  assert.equal(provablyNewer(status({ configMtimeNs: "1757145600000000004" }), status()), true);
  assert.equal(provablyNewer(gone, status()), false, "a suspect that saw the deletion reads as older, as before (the poll settles it)");
});

// ── detached changes ───────────────────────────────────────────────────────────────────────────────

test("a detached change's card offers no Accept, Reject, Reply or Reveal, wears the detached dress and tag, and its group says why; its texts and the comment bound to it are one click down; the foot counts pending changes only", async (t: TestContext) => {
  // the host decides pending changes only (decidedChanges and buildComment read store.suggestions), so each of those
  // buttons could only be refused `no-change … reload and retry`, and no reload clears it: the sidecar keeps the op
  const w = world(); t.after(() => w.close());
  const { aside, button } = await openPanel(w, status({ store: { ...NO_COMMENTS, comments: [passage, onD1], detached: [D1] }, hunks: [h1] }));
  assert.equal(button.textContent, "Comments · 2 · 1 change · 1 detached change", "the glance counts the bound comment too, and the detached change apart");
  const d = card(aside, "chg:d1")!;
  assert.ok(d, "the detached change has a card");
  assert.ok(d.classes.includes("fc-card-detached"), "the comment cards' detached dress");
  for (const a of ["fcaccept", "fcreject", "fcchangereply", "fcreveal"]) assert.equal(d.querySelector('[data-act="' + a + '"]'), null, "no " + a + " on a detached card");
  assert.equal(d.querySelector(".fc-actions"), null, "no empty button row either");
  const tag = d.querySelectorAll(".fc-card-head .fc-tag").find((x) => x.textContent === "detached")!;
  assert.ok(tag, "tagged detached");
  assert.match(tag.title, /cannot be accepted or rejected/);
  assert.equal(tags(d).includes("not shown"), false, "no claim about the view: the change is nowhere in it");
  assert.equal(isLink(d), false, "the reference links to no mark");
  assert.equal(d.querySelector(".fc-count")!.textContent, "1", "the bound comment is counted while collapsed");
  const groups = aside.querySelectorAll(".fc-group");
  assert.equal(groups[groups.length - 1].textContent, DETACHED_GROUP_TITLE);
  assert.match(groups[groups.length - 1].title, /no longer holds/, "the group's own tooltip, not the paragraph one");
  // the pending change keeps its buttons; the foot counts it alone
  const c1 = card(aside, "chg:h1")!;
  assert.deepEqual(texts(c1.querySelectorAll(".fc-actions button")), ["Accept", "Reject", "Reply"]);
  act(aside, "fcrejectall")!.click();
  assert.ok(aside.querySelector(".fc-foot .fc-choice")!.textContent.includes("for the change?"), "one pending change: the confirm counts one, not two");
  act(aside, "fcrejectallcancel")!.click();
  // one click down: the old and new text, and the comment bound to it with its own Reply and Resolve (the card is
  // re-found: the confirm's two renders rebuilt the list)
  card(aside, "chg:d1")!.querySelector(".fc-card-head")!.click();
  const open = card(aside, "chg:d1")!;
  assert.ok(open.classes.includes("open"));
  assert.equal(open.querySelector("del")!.textContent, "cold starts were slow"); assert.equal(open.querySelector("ins")!.textContent, "cold starts stay slow");
  const hosted = open.querySelector('.fc-hosted[data-id="' + onD1.id + '"]')!;
  assert.ok(hosted, "the bound comment rides the card");
  assert.ok(act(hosted, "fcreply", onD1.id) && act(hosted, "fcresolve", onD1.id), "the comment's own Reply and Resolve, by its id — verbs the host takes");
  assert.equal(open.querySelector('[data-act="fcaccept"]'), null, "open or closed, nothing decides it");
  assert.deepEqual(w.modes, [], "no view switch happened");
});

test("with only detached changes the foot does not render at all: no Accept all, no Reject all, and the empty line yields to the cards", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside, button } = await openPanel(w, status({ store: { ...NO_COMMENTS, suggestions: [], comments: [], detached: [D1] }, hunks: [], unsent: UNSENT_NONE }));
  assert.equal(button.textContent, "Comments · 0 · 1 detached change");
  assert.ok(card(aside, "chg:d1"));
  assert.equal(aside.querySelector(".fc-foot"), null, "nothing is pending: no foot");
  assert.equal(act(aside, "fcacceptall"), null); assert.equal(act(aside, "fcrejectall"), null);
  assert.equal(aside.querySelector(".fc-empty"), null, "a card shows, so no 'No comments yet'");
  assert.equal(aside.querySelectorAll('[data-act="fcaccept"], [data-act="fcreject"], [data-act="fcreveal"], [data-act="fcchangereply"]').length, 0);
});

// ── a refusal whose card is gone ───────────────────────────────────────────────────────────────────

test("Accept refused store-moved, retried by id after the refresh removed the card, refused no-change: the wait and then the refusal show where the changes were, verbatim, dismissable, and a dismissal clears the slot for good", async (t: TestContext) => {
  // the host refuses `no-change` by id for a change a later track-edit coalesced away or another client decided; the
  // plan's fence rule surfaces the second refusal verbatim. Before, the row lived only inside the change's card, so with the
  // card gone the click had no visible outcome and the map entry lingered to reappear under a later card of the same id.
  t.mock.timers.enable({ apis: ["setInterval"] });
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  act(card(aside, "chg:h1")!, "fcaccept", "h1")!.click(); await flush();
  const first = lastOf(w, "fileComments", "accept");
  refuse(w, first, "store-moved", MOVED_STORE); await flush();
  // the fresh status: h1 coalesced away, h3 stands
  answer(w, status({ storeMtimeNs: S9, hunks: [h3], store: { ...NO_COMMENTS, suggestions: [SUGG[1]], comments: [passage] } })); await flush(); await flush();
  assert.equal(card(aside, "chg:h1"), null, "the card is gone with the refresh");
  const retry = lastOf(w, "fileComments", "accept");
  assert.ok(retry && retry.reqId !== first.reqId && retry.fence.storeMtimeNs === S9, "the retry by id, with the fresh fence");
  assert.deepEqual(retry.args, { ids: ["h1"] });
  const wait = aside.querySelector('.fc-cards .fc-load[data-slot="change:h1"]');
  assert.ok(wait, "the retry's wait wears the loader where the card was");
  refuse(w, retry, "no-change", NO_CHANGE); await flush(); await flush();
  const rows = aside.querySelectorAll(".fc-err");
  assert.equal(rows.length, 1, "the refusal shows once");
  assert.equal(rows[0].dataset.slot, "change:h1");
  assert.ok(rows[0].textContent.startsWith(NO_CHANGE), "the host's words, verbatim");
  assert.equal(act(rows[0], "fcreload"), null, "no-change is not a moved fence: no Reload");
  assert.ok(act(rows[0], "fcerrx"), "…but a dismissal");
  const list = aside.querySelector(".fc-cards")!;
  assert.ok(list.childNodes.indexOf(rows[0]) > list.childNodes.indexOf(card(aside, "chg:h3")!), "after the changes");
  assert.ok(list.childNodes.indexOf(rows[0]) < list.childNodes.indexOf(card(aside, passage.id)!), "…before the comments: where the card was");
  assert.equal(aside.querySelectorAll(".fc-load").length, 0, "the wait is over");
  assert.equal(act(card(aside, "chg:h3")!, "fcaccept", "h3")!.disabled, false, "the other card is untouched");
  // ✕ clears it; a later status listing h1 again shows no stale row under the new card
  act(rows[0], "fcerrx")!.click();
  assert.equal(aside.querySelectorAll(".fc-err").length, 0);
  w.mtimes[STORE_PATH] = S12;
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  answer(w, status({ storeMtimeNs: S12 })); await flush(); await flush();
  assert.ok(card(aside, "chg:h1"), "h1 is back in the sidecar");
  assert.equal(card(aside, "chg:h1")!.querySelector(".fc-err"), null, "…with no row from the dismissed refusal");
});

test("Reject refused the same way shows its row too; Accept all refused after a refresh that left nothing pending shows 'Nothing decided' though no foot renders, even on an otherwise empty list", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  act(card(aside, "chg:h3")!, "fcreject", "h3")!.click(); await flush();
  const first = lastOf(w, "fileComments", "reject");
  refuse(w, first, "store-moved", MOVED_STORE); await flush();
  answer(w, status({ storeMtimeNs: S9, hunks: [h1], store: { ...NO_COMMENTS, suggestions: [SUGG[0]], comments: [passage] } })); await flush(); await flush();
  refuse(w, lastOf(w, "fileComments", "reject"), "no-change", "change h3 is no longer pending in ~/notes-api/docs/report.md — reload and retry"); await flush(); await flush();
  const row = aside.querySelector('.fc-err[data-slot="change:h3"]')!;
  assert.ok(row, "the reject's refusal shows with its card gone");
  assert.ok(row.textContent.includes("change h3 is no longer pending"));
  w.close();
  // the foot's slot: Accept all, store-moved, the fresh status has no pending change and no comment
  const w2 = world(); t.after(() => w2.close());
  const { aside: a2 } = await openPanel(w2, status({ store: NO_COMMENTS, unsent: UNSENT_NONE }));
  act(a2, "fcacceptall")!.click(); await flush();
  const acc = lastOf(w2, "fileComments", "accept-all");
  refuse(w2, acc, "store-moved", MOVED_STORE); await flush();
  answer(w2, status({ storeMtimeNs: S9, hunks: [], store: { ...NO_COMMENTS, suggestions: [] }, unsent: UNSENT_NONE })); await flush(); await flush();
  assert.equal(countOf(w2, "fileComments", "accept-all"), 1, "no retry of an id-less verb");
  assert.equal(a2.querySelector(".fc-foot"), null, "nothing pending: no foot");
  assert.ok(a2.querySelector(".fc-empty"), "and no card at all: the empty line");
  const nothing = a2.querySelector('.fc-cards .fc-err[data-slot="changes"]')!;
  assert.ok(nothing, "the row still shows");
  assert.ok(nothing.textContent.startsWith("Nothing decided: " + MOVED_STORE));
  // a no-change refusal of the id-less verb (another client emptied the set first) shows the same way
  act(nothing, "fcerrx")!.click();
  assert.equal(a2.querySelectorAll(".fc-err").length, 0);
  w2.close();
  const w3 = world(); t.after(() => w3.close());
  const { aside: a3 } = await openPanel(w3, status({ store: NO_COMMENTS, unsent: UNSENT_NONE }));
  act(a3, "fcacceptall")!.click(); await flush();
  refuse(w3, lastOf(w3, "fileComments", "accept-all"), "no-change", NO_PENDING); await flush(); await flush();
  assert.ok(a3.querySelector(".fc-foot .fc-err"), "the cards still show (no refresh ran): the row is the foot's");
});

// ── the standalone card of a comment whose change was decided ──────────────────────────────────────

test("a comment bound to a change the log has decided stands on its own card, tagged with the decision and titled for it; accepted and rejected alike", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const decided = (log: LogEntry) => status({ hunks: [], store: { ...NO_COMMENTS, suggestions: [], comments: [passage, bound] }, log: [log],
    unsent: { comments: [passage.id, bound.id], replies: [], accepted: 1, rejected: 0, watermark: null } });
  const { aside } = await openPanel(w, decided(ACCEPT_LOG));
  const c = card(aside, bound.id)!;
  assert.ok(c, "no change card hosts it any more: its own card");
  assert.equal(c.querySelector(".fc-ref")!.textContent, "reduced → cut", "the change's texts, from the log");
  const tag = c.querySelectorAll(".fc-card-head .fc-tag").find((x) => x.textContent === "accepted")!;
  assert.ok(tag, "tagged with the decision");
  assert.equal(tag.title, "You accepted the change this comment is on");
  assert.equal(tags(c).includes("resolved"), false, "the decision is not 'resolved'");
  w.close();
  const w2 = world(); t.after(() => w2.close());
  const { aside: a2 } = await openPanel(w2, decided(REJECT_LOG));
  const c2 = card(a2, bound.id)!;
  const tag2 = c2.querySelectorAll(".fc-card-head .fc-tag").find((x) => x.textContent === "rejected")!;
  assert.ok(tag2);
  assert.equal(tag2.title, "You rejected the change this comment is on");
  assert.equal(c2.querySelectorAll(".fc-card-head .fc-tag").filter((x) => x.textContent === "accepted").length, 0);
});

// ── the window between a reject's reply and its reload ─────────────────────────────────────────────

test("between a reject's reply and its reload the cards wear the romp loader at their head; it goes the moment the bytes land; a fetch that never lands yields to a row with Reload after the deadline, and Reload re-fetches", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const w = world({ deferReload: true }); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ hunks: [h1, h3, h5] }));
  assert.equal(aside.querySelectorAll(".fc-load").length, 0);
  act(card(aside, "chg:h1")!, "fcreject", "h1")!.click(); await flush();
  const m = lastOf(w, "fileComments", "reject");
  w.disk = DOC.replace("cut", "reduced"); w.diskMtime = F11;
  const after = status({ fileMtimeNs: F11, storeMtimeNs: S12, hunks: [shifted(h3, 4), shifted(h5, 4)],
    store: { ...NO_COMMENTS, suggestions: [SUGG[1]], comments: [passage] }, unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 1, watermark: null } });
  answer(w, after, m, { rejected: ["h1"] }); await flush(); await flush();
  assert.equal(w.reloads, 1, "the bytes are asked for"); assert.ok(w.landReload, "…and not yet here");
  assert.equal(marksOf(w).length, 0, "nothing is painted over the old bytes");
  const list = aside.querySelector(".fc-cards")!;
  const load = list.querySelector('.fc-load[data-slot="bytes"]');
  assert.ok(load, "the wait wears the loader");
  assert.equal(list.childNodes[0], load, "…at the head of the cards, over the changes it is about");
  assert.equal(load!.classes.includes("fileview-load"), true, "the viewer's loader dress: swirl, wordmark, dots");
  assert.equal(aside.querySelectorAll(".fc-err").length, 0);
  // the bytes land: the loader goes with the paint that shows them, no timer involved
  w.landReload!(); await flush();
  assert.equal(w.viewMtime, F11);
  assert.equal(aside.querySelectorAll(".fc-load").length, 0, "the wait is over");
  assert.equal(marksOf(w, "h5").length, 1, "…and the marks are back over the new text");
  w.close();
  // the backstop: the fetch neither lands nor tells the seam it failed
  const w2 = world({ deferReload: true }); t.after(() => w2.close());
  const { aside: a2 } = await openPanel(w2, status({ hunks: [h1, h3, h5] }));
  act(card(a2, "chg:h1")!, "fcreject", "h1")!.click(); await flush();
  w2.disk = DOC.replace("cut", "reduced"); w2.diskMtime = F11;
  answer(w2, after, lastOf(w2, "fileComments", "reject"), { rejected: ["h1"] }); await flush(); await flush();
  assert.ok(a2.querySelector('.fc-load[data-slot="bytes"]'));
  t.mock.timers.tick(15000); await flush();
  assert.equal(a2.querySelectorAll(".fc-load").length, 0, "the loader never traps: it yields at the deadline");
  const row = a2.querySelector('.fc-cards .fc-err[data-slot="bytes"]')!;
  assert.ok(row, "…to a row where it was");
  assert.match(row.textContent, /have not arrived after 15 s/);
  assert.match(row.textContent, /text from before your decision, with no change marked/, "it says what the person is looking at");
  const reload = act(row, "fcreload")!;
  assert.ok(reload, "with Reload");
  const asks = countOf(w2, "fileComments", "status");
  reload.click(); await flush();
  assert.equal(w2.reloads, 2, "Reload re-fetches the bytes"); assert.equal(countOf(w2, "fileComments", "status"), asks + 1, "…and re-asks status");
  assert.equal(a2.querySelector('.fc-err[data-slot="bytes"]'), null, "the row is answered by the click");
  assert.ok(a2.querySelector('.fc-load[data-slot="bytes"]'), "the slot wears the loader for the re-read");
  w2.landReload!(); answer(w2, after); await flush(); await flush();
  assert.equal(a2.querySelectorAll(".fc-load").length, 0);
  assert.equal(marksOf(w2, "h5").length, 1);
});

// ── the keyboard on a painted mark ─────────────────────────────────────────────────────────────────

test("Enter on a focused change mark with the panel closed: the panel opens with the card, and after the colour fetch's and the status reply's repaints the keyboard is on the mark's successor, not the body; a comment highlight the same", async (t: TestContext) => {
  // every paintAll unwraps the marks, and a removed focused element drops the focus to the body; refocus() mends only the
  // aside's controls. Before, the next Tab started from the top of the document after every activation that repainted.
  const w = world(); t.after(() => w.close());
  const { button } = await mount(w);                  // the probe painted the marks; the panel is closed
  assert.equal(w.main.querySelector(".fileview-aside"), null);
  const mark = marksOf(w, "h1").find((x) => x.textContent === "cut")!;
  assert.ok(mark && mark.tabIndex === 0, "a mark is a Tab stop");
  mark.focus(); assert.equal(doc.activeElement, mark);
  press(mark, "Enter");
  const aside = w.main.querySelector(".fileview-aside")!;
  assert.ok(aside, "Enter opened the panel");
  await flush();                                       // the colour fetch lands: paintAll repaints the marks
  const again = marksOf(w, "h1").find((x) => x.textContent === "cut")!;
  assert.ok(again && again !== mark, "the mark was repainted (a fresh element)");
  assert.equal(doc.activeElement, again, "…and holds the keyboard");
  answer(w, status()); await flush(); await flush();   // the status reply: another repaint
  const third = marksOf(w, "h1").find((x) => x.textContent === "cut")!;
  assert.ok(third !== again);
  assert.equal(doc.activeElement, third, "still on the mark after the reply's repaint");
  assert.ok(card(aside, "chg:h1")!.classes.includes("open"), "the card the mark opened is open");
  assert.equal(marksOf(w, "h1").filter((x) => x.textContent === "cut").length, 1, "one mark, not a stack");
  // a comment highlight, panel closed again
  button.click();
  assert.equal(w.main.querySelector(".fileview-aside"), null);
  const hl = w.body.querySelector('.fc-hl[data-id="' + passage.id + '"]')!;
  hl.focus(); assert.equal(doc.activeElement, hl);
  press(hl, "Enter");
  await flush(); answer(w, status()); await flush(); await flush();
  const hl2 = w.body.querySelector('.fc-hl[data-id="' + passage.id + '"]')!;
  assert.ok(hl2 && hl2 !== hl, "the highlight was repainted");
  assert.equal(doc.activeElement, hl2, "…and holds the keyboard");
  assert.ok(card(w.main.querySelector(".fileview-aside")!, passage.id)!.classes.includes("open"));
  // a mark whose change the repaint no longer paints: the focus is not left on a detached element
  const m1 = marksOf(w, "h1").find((x) => x.textContent === "cut")!;
  m1.focus();
  const a3 = w.main.querySelector(".fileview-aside")!;
  act(card(a3, "chg:h1")!, "fcaccept", "h1")!.click(); await flush();
  answer(w, status({ storeMtimeNs: S22, hunks: [h3], store: { ...NO_COMMENTS, suggestions: [SUGG[1]], comments: [passage] } }), lastOf(w, "fileComments", "accept"), { accepted: ["h1"] });
  await flush(); await flush();
  assert.equal(marksOf(w, "h1").length, 0, "the accepted change is unmarked");
  assert.notEqual(doc.activeElement, m1, "the old mark, out of the tree, does not keep the keyboard");
});
