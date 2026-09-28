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
import * as fs from "node:fs";
import * as path from "node:path";
import { inspect } from "node:util";
import * as vm from "node:vm";
import { assertHiddenEvent, hideEdges, staysEnumerable } from "../test-dom-shim";
import type { FileViewActionCtx, TrackedEdit } from "./file-view";
import { cardStateCensus } from "./writer-census";
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
  constructor(public type: string, init: { key?: string } = {}) { this.key = init.key || ""; hideEdges(this); }
  preventDefault(): void { this.defaultPrevented = true; }
  stopPropagation(): void { this.stopped = true; }
}
type Listener = (ev: Ev) => void;
type Reg = { type: string; cb: Listener; capture: boolean };
const kebab = (k: string) => k.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
class Txt {
  nodeType = 3;
  parentNode!: El | null;
  constructor(public data: string) {
    Object.defineProperty(this, "parentNode", { value: null, writable: true, enumerable: false, configurable: true });
    hideEdges(this);
  }
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
  parentNode!: El | null;
  childNodes!: Array<El | Txt>;
  attrs = new Map<string, string>();
  listeners: Reg[] = [];
  hidden = false; disabled = false; readOnly = false; title = ""; type = ""; value = ""; checked = false; placeholder = "";
  innerHTML = "";
  style: Record<string, string> = {};
  rect = { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 };
  constructor(tag: string) {
    this.tagName = tag.toUpperCase();
    // the tree's edges are non-enumerable, so a node inspects as its own projection and a failing assertion's dump
    // stays small (ui/test-dom-shim.ts says why); assignments later keep them hidden
    Object.defineProperty(this, "parentNode", { value: null, writable: true, enumerable: false, configurable: true });
    Object.defineProperty(this, "childNodes", { value: [], writable: true, enumerable: false, configurable: true });
    hideEdges(this);
  }
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
  get tabIndex(): number { return this.attrs.has("tabindex") ? Number(this.attrs.get("tabindex")) : (this.tagName === "BUTTON" || this.tagName === "INPUT" || this.tagName === "TEXTAREA" ? 0 : -1); }
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
  hooks: { rendered: Array<() => void>; close: Array<() => void>; landed: Array<() => void>; replaced: Array<() => void> };   // landed: the seam's onLanded (an svg picture's landing, before or after its paint); replaced: its onReplaced (a picture or a loader put up with no paint yet: RoadSeam's and the unpainted media seam's)
  disk: string; diskMtime: string; viewMtime: string; reloads: number; scrolls: number[]; modes: string[];
  mtimes: Record<string, string>;
  /** The held reload's landing (deferReload): the bytes and mtime now on disk, repainted, onRendered fired. */
  landReload: (() => void) | null;
  /** The held reload's FAILURE (Slice 7 of plans/markdown-viewer.md, item 3): the real seam's fetch catch paints a `div.fileview-err`
   *  pane in place of the file, sets error() to its words and fires onRendered, text() and mtimeNs() still the last landing's. */
  failReload: ((words: string) => void) | null;
  /** What error() answers: the pane's words after a failed landing, null after a content paint (contract C1). */
  viewError: string | null;
  /** A format click's renderBody (file-view.ts): the last landing's text painted again over whatever the body held, the pane included,
   *  error() null, onRendered fired, text() and mtimeNs() unchanged. */
  repaint: () => void;
  /** The editor's entry and exit (file-view.ts enterEdit and exitEdit): the entry takes the body with the editor's box, clears
   *  error() and fires onRendered once with editing() true, text() and mtimeNs() unchanged (the round 2 review of Slice 7); the
   *  exit repaints the last landing's text (renderBody) with editing() false. */
  edit: (on: boolean) => void;
  editing: boolean;
  /** Every throw a rendered hook made, as the real fireRendered would swallow it (file-view.ts): a probe, so a panel exception
   *  inside the hook fails the test instead of vanishing. */
  hookErrors: unknown[];
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
    hooks: { rendered: [] as Array<() => void>, close: [] as Array<() => void>, landed: [] as Array<() => void>, replaced: [] as Array<() => void> },
    disk: text, diskMtime: F1, viewMtime: F1, reloads: 0, scrolls: [] as number[], modes: [] as string[], mtimes: {} as Record<string, string>,
    landReload: null as (() => void) | null, failReload: null as ((words: string) => void) | null, viewError: null as string | null, hookErrors: [] as unknown[],
    editing: false,
  } as World;
  const fire = () => { for (const cb of w.hooks.rendered) { try { cb(); } catch (e) { w.hookErrors.push(e); } } };
  const setText = (s: string) => { text = s; w.viewError = null; body.replaceChildren(wrap); rows(code, s); fire(); };
  const land = () => { w.landReload = null; w.failReload = null; w.viewMtime = w.diskMtime; setText(w.disk); };
  w.repaint = () => setText(text);
  w.edit = (on: boolean) => {
    if (on) { w.editing = true; const cm = new El("div"); cm.className = "fileview-cm"; body.replaceChildren(cm); w.viewError = null; fire(); }
    else { w.editing = false; setText(text); }
  };
  // the fetch chain's catch (file-view.ts): the pane swapped in, error() set, the hooks fired; the text and the mtime stay the landing's
  const fail = (words: string) => {
    w.landReload = null; w.failReload = null;
    const why = new El("div"); why.className = "fileview-err"; why.appendChild(new Txt(words));
    body.replaceChildren(why); w.viewError = words; fire();
  };
  w.ctx = {
    path: ABS, sid: SID, todoId: null,
    body: () => body as unknown as HTMLElement, mode: () => "raw", text: () => text, mtimeNs: () => w.viewMtime, error: () => w.viewError, media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [],
    identity: () => ({ name: "api", color: null }),
    onRendered: (cb) => { w.hooks.rendered.push(cb); }, onLanded: (cb) => { w.hooks.landed.push(cb); }, onReplaced: (cb) => { w.hooks.replaced.push(cb); }, onSelection: () => { /* inert */ },
    onSaved: () => { /* inert */ }, onClose: (cb) => { w.hooks.close.push(cb); },
    post: (m) => { w.posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: () => { /* inert */ }, editing: () => w.editing, setTrackedEdit: () => { /* inert */ }, guardClose: () => { /* inert */ },
    aside: (node) => { main.querySelector(".fileview-aside")?.remove(); if (node) { const n = node as unknown as El; n.classList.add("fileview-aside"); main.appendChild(n); } },
    setMode: (m) => { w.modes.push(m); }, scrollToOffset: (n) => { w.scrolls.push(n); },
    // fetchFile: an async GET in the real seam — held here until the test lands it (deferReload), else at once
    reload: () => { w.reloads++; if (over.deferReload) { w.landReload = land; w.failReload = fail; } else land(); },
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

test("a detached change's card offers no Accept, Reject, Comment on this change or Reveal, wears the detached dress and tag, and its group says why; its texts are one click down; the comment about it is its own card, counted on the change card; the foot counts pending changes only", async (t: TestContext) => {
  // the host decides pending changes only (decidedChanges and buildComment read store.suggestions), so each of those
  // buttons could only be refused `no-change … reload and retry`, and no reload clears it: the sidecar keeps the op
  const w = world(); t.after(() => w.close());
  const { aside, button } = await openPanel(w, status({ store: { ...NO_COMMENTS, comments: [passage, onD1], detached: [D1] }, hunks: [h1] }));
  assert.equal(button.textContent, "Comments · 2 · 1 change · 1 detached change", "the glance counts the comment about the change too, and the detached change apart");
  const d = card(aside, "chg:d1")!;
  assert.ok(d, "the detached change has a card");
  assert.ok(d.classes.includes("fc-card-detached"), "the comment cards' detached dress");
  for (const a of ["fcaccept", "fcreject", "fcchangecomment", "fcreveal"]) assert.equal(d.querySelector('[data-act="' + a + '"]') === null, true, "no " + a + " on a detached card");
  assert.equal(d.querySelector(".fc-actions") === null, true, "no empty button row either");
  const tag = d.querySelectorAll(".fc-card-head .fc-tag").find((x) => x.textContent === "detached")!;
  assert.ok(tag, "tagged detached");
  assert.match(tag.title, /cannot be accepted or rejected/);
  assert.equal(tags(d).includes("not shown"), false, "no claim about the view: the change is nowhere in it");
  assert.equal(isLink(d), false, "the reference links to no mark");
  const count = d.querySelector(".fc-about-count")!;
  assert.equal(count.textContent, "1 comment", "the comment about the change is counted while collapsed (the about follow-on: a tag, not a hosted card)");
  assert.equal(count.dataset.act, "fcaboutfirst"); assert.equal(count.dataset.id, "d1");
  const groups = aside.querySelectorAll(".fc-group");
  assert.equal(groups[groups.length - 1].textContent, DETACHED_GROUP_TITLE);
  assert.match(groups[groups.length - 1].title, /no longer holds/, "the group's own tooltip, not the paragraph one");
  // the pending change keeps its buttons; the foot counts it alone
  const c1 = card(aside, "chg:h1")!;
  assert.deepEqual(texts(c1.querySelectorAll(".fc-actions button")), ["Accept", "Reject", "Comment on this change"]);
  act(aside, "fcrejectall")!.click();
  assert.ok(aside.querySelector(".fc-foot .fc-choice")!.textContent.includes("for the change?"), "one pending change: the confirm counts one, not two");
  act(aside, "fcrejectallcancel")!.click();
  // one click down: the old and new text, and nothing that decides it (the card is re-found: the confirm's two renders
  // rebuilt the list)
  card(aside, "chg:d1")!.querySelector(".fc-card-head")!.click();
  const open = card(aside, "chg:d1")!;
  assert.ok(open.classes.includes("open"));
  assert.equal(open.querySelector("del")!.textContent, "cold starts were slow"); assert.equal(open.querySelector("ins")!.textContent, "cold starts stay slow");
  assert.equal(open.querySelector(".fc-hosted") === null, true, "no comment rides the card (before the about follow-on, 2026-09-10, the bound comment did)");
  assert.equal(open.querySelector(".fc-about-count")!.textContent, "1 comment", "the count stands open too");
  assert.equal(open.querySelector('[data-act="fcaccept"]') === null, true, "open or closed, nothing decides it");
  // the comment about the detached change: its own card after the changes, the change's words as its reference, the
  // answered tag naming the change and its state, and its own Reply and Resolve once open, by its id (verbs the host takes)
  const own = card(aside, onD1.id)!;
  assert.ok(own, "the comment has its own card");
  assert.equal(own.querySelector(".fc-ref")!.textContent, "cold starts were slow → cold starts stay slow", "no passage: the change's words are its reference");
  assert.equal(own.querySelector(".fc-kind")!.title, "A comment the session answered with a change", "the legacy binding, read as answered: the title says so (the review, 2026-09-10)");
  assert.deepEqual(tags(own), ["answered by a change"]);
  assert.equal(own.querySelector(".fc-tag.fc-about")!.title, "The session answered this comment with: cold starts were slow → cold starts stay slow (detached: the file no longer holds its text)");
  own.querySelector(".fc-card-head")!.click();
  const openOwn = card(aside, onD1.id)!;
  assert.ok(openOwn.classes.includes("open"));
  assert.ok(act(openOwn, "fcreply", onD1.id) && act(openOwn, "fcresolve", onD1.id), "the comment's own Reply and Resolve, by its id");
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
  assert.equal(aside.querySelectorAll('[data-act="fcaccept"], [data-act="fcreject"], [data-act="fcreveal"], [data-act="fcchangecomment"]').length, 0);
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

const BUSY = "another editor is writing ~/notes-api/docs/report.md; retry";

test("Accept refused busy (the host's lock was held past its wait, decision 49): status re-read and one retry by id with the fresh fence; a second busy shows the row verbatim with Reload and no third try; Accept all refused busy re-reads and says nothing was decided", async (t: TestContext) => {
  // `busy` joins the moved fences in MOVED, and the retry is the moved-fence path reused, not a wait for the holder: the
  // host refuses `busy` while the other writer STILL holds the lock (it releases after its last rename; `status` takes no
  // lock), so the one re-read shows that writer's write only when it landed in the gap before the re-read, and only then
  // does the retry carry a fence that lands (file-comments-busy-retry-fence.test.ts). The harness answers the re-read
  // with S9: that case. It is not a decision the person must make again, so a by-id verb retries once; an id-less one
  // stops and re-reads, as for a moved fence. A second refusal, `busy` again from a lock still held or `store-moved` from
  // a holder that finished under the retry, shows verbatim with Reload, and there is no third try.
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  act(card(aside, "chg:h1")!, "fcaccept", "h1")!.click(); await flush();
  const first = lastOf(w, "fileComments", "accept");
  refuse(w, first, "busy", BUSY); await flush();
  answer(w, status({ storeMtimeNs: S9 })); await flush(); await flush();
  const retry = lastOf(w, "fileComments", "accept");
  assert.ok(retry && retry.reqId !== first.reqId && retry.fence.storeMtimeNs === S9, "the retry by id, with the fresh fence");
  assert.deepEqual(retry.args, { ids: ["h1"] });
  refuse(w, retry, "busy", BUSY); await flush(); await flush();
  assert.equal(countOf(w, "fileComments", "accept"), 2, "one retry, never a third");
  const rows = aside.querySelectorAll(".fc-err");
  assert.equal(rows.length, 1);
  assert.equal(rows[0].dataset.slot, "change:h1");
  assert.ok(rows[0].textContent.startsWith(BUSY), "the host's words, verbatim");
  assert.ok(act(rows[0], "fcreload"), "handled as a moved fence: Reload offered");
  assert.equal(act(card(aside, "chg:h1")!, "fcaccept", "h1")!.disabled, false, "the card's Accept is live again");
  w.close();
  const w2 = world(); t.after(() => w2.close());
  const { aside: a2 } = await openPanel(w2);
  act(a2, "fcacceptall")!.click(); await flush();
  const acc = lastOf(w2, "fileComments", "accept-all");
  refuse(w2, acc, "busy", BUSY); await flush();
  answer(w2, status({ storeMtimeNs: S9 })); await flush(); await flush();
  assert.equal(countOf(w2, "fileComments", "accept-all"), 1, "no retry of an id-less verb");
  const nothing = a2.querySelector('.fc-err[data-slot="changes"]')!;
  assert.ok(nothing, "the row says so");
  assert.ok(nothing.textContent.startsWith("Nothing decided: " + BUSY));
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
  assert.equal(tag.title, "You accepted the change that answered this comment", "a legacy binding: the change that answered the comment, never \"on\" (CONTEXT.md, About: Avoid; the consolidation, 2026-09-10)");
  assert.equal(tags(c).includes("resolved"), false, "the decision is not 'resolved'");
  w.close();
  const w2 = world(); t.after(() => w2.close());
  const { aside: a2 } = await openPanel(w2, decided(REJECT_LOG));
  const c2 = card(a2, bound.id)!;
  const tag2 = c2.querySelectorAll(".fc-card-head .fc-tag").find((x) => x.textContent === "rejected")!;
  assert.ok(tag2);
  assert.equal(tag2.title, "You rejected the change that answered this comment");
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
  assert.match(row.textContent, /the earlier text, with no change marked/, "it says what the person is looking at");
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
  w2.close();
  // Slice 7 of plans/markdown-viewer.md, item 3: the deferred reload FAILS. The viewer paints its failure pane in place of the file
  // and fires onRendered with error() set (contract C1); the panel's hook reads it and ends the wait at that paint (bytesFailed):
  // no timer tick, the loader gone, the row in the seam's words with Reload, nothing marked over the pane, and a later tick changes
  // nothing since the deadline is cleared. Before Slice 7 the viewer fired nothing for a failed fetch and the loader stood the 15 s out.
  const w3 = world({ deferReload: true }); t.after(() => w3.close());
  const { aside: a3 } = await openPanel(w3, status({ hunks: [h1, h3, h5] }));
  act(card(a3, "chg:h1")!, "fcreject", "h1")!.click(); await flush();
  w3.disk = DOC.replace("cut", "reduced"); w3.diskMtime = F11;
  answer(w3, after, lastOf(w3, "fileComments", "reject"), { rejected: ["h1"] }); await flush(); await flush();
  assert.ok(a3.querySelector('.fc-load[data-slot="bytes"]'), "the wait is up"); assert.ok(w3.failReload, "the reload is out");
  const hooksBefore = w3.hooks.rendered.length;
  const WORDS = "no such file: " + ABS;                 // the kernel's 404 body, the words the seam's error() answers (contract C1)
  w3.failReload!(WORDS); await flush();
  assert.deepEqual(w3.hookErrors, [], "the panel's hook threw nothing over the pane (the real fireRendered would swallow it)");
  assert.equal(w3.hooks.rendered.length, hooksBefore, "no hook re-registered");
  assert.equal(a3.querySelectorAll(".fc-load").length, 0, "the loader went at the paint, with no timer tick");
  const row3 = a3.querySelector('.fc-cards .fc-err[data-slot="bytes"]')!;
  assert.ok(row3, "…to a row where it was");
  const { BYTES_FAILED } = await import("./file-comments");
  assert.equal(row3.childNodes[0].textContent, BYTES_FAILED + " (" + WORDS + "); the view shows that failure in place of the file, so no change is marked. Reload to read the file again.", "the seam's words, verbatim, in the row's fixed shape (contract C3)");
  assert.ok(act(row3, "fcreload"), "with Reload");
  assert.equal(marksOf(w3).length, 0, "nothing is marked over the pane");
  assert.equal(w3.body.querySelectorAll(".fileview-err").length, 1, "the viewer's pane stands in the body");
  assert.equal(w3.viewMtime, F1, "the view's mtime is still the last landing's: the wait ended on the failure, not on the bytes");
  t.mock.timers.tick(15000); await flush();
  assert.equal(a3.querySelectorAll('.fc-err[data-slot="bytes"]').length, 1, "the deadline was cleared: a later tick raises no second row");
  assert.equal(row3.textContent.includes("have not arrived"), false, "…and the row is the failure's, not the deadline's");
  // a status landing while the pane stands (the poll): its mtime is still not the view's, so a wait is armed again, and the pass
  // that follows reads the pane and ends it at once, since no bytes can land while the view shows the pane; no loader, the row stays
  answer(w3, after); await flush(); await flush();
  assert.equal(w3.reloads, 1, "the same mtime: no second fetch");
  assert.equal(a3.querySelectorAll(".fc-load").length, 0, "no loader over a standing pane");
  assert.ok(a3.querySelector('.fc-cards .fc-err[data-slot="bytes"]'), "the row stands");
  t.mock.timers.tick(15000); await flush();
  assert.equal(a3.querySelectorAll('.fc-err[data-slot="bytes"]').length, 1, "…and its deadline was cleared too");
  // Reload from the row re-fetches and re-asks, as the deadline row's does; the landing then ends the new wait with the paint
  const asks3 = countOf(w3, "fileComments", "status");
  act(row3, "fcreload")!.click(); await flush();
  assert.equal(w3.reloads, 2); assert.equal(countOf(w3, "fileComments", "status"), asks3 + 1);
  assert.ok(a3.querySelector('.fc-load[data-slot="bytes"]'), "the slot wears the loader for the re-read");
  // the browser's order (the Slice 7 consolidation pass's scene in file-view-failures-browser.test.ts): the status ask the row's
  // Reload sent is answered before the fetch it sent lands, over the standing pane. The pass arms the wait again and, a fetch of
  // the panel's asking being out (reloadOut), leaves it standing: the pane is the failure before the click, not that fetch's
  // answer, so the slot keeps the loader and no row is filed (the review's round 4; before it the head filed the row again off the
  // standing pane at once, the loader gone before the eye saw it, and the deadline went with the wait). THEN the fetch lands: the
  // landing paint shows the status's text, and the wait ends with the loader (bytesLanded, which also takes a row filed with no
  // fetch of the panel's out, the consolidation pass's clause).
  answer(w3, after); await flush(); await flush();
  assert.equal(w3.reloads, 2, "the same mtime: the status asks no third fetch");
  assert.ok(a3.querySelector('.fc-load[data-slot="bytes"]'), "the loader stands for the fetch the click sent (before round 4: gone at the status's landing)");
  assert.equal(a3.querySelectorAll('.fc-err[data-slot="bytes"]').length, 0, "no row while that fetch is out (before round 4: the row filed again off the standing pane)");
  assert.ok(w3.landReload, "the fetch is still out");
  w3.landReload!(); await flush(); await flush();
  assert.equal(w3.viewError, null, "a content paint clears error()");
  assert.equal(a3.querySelectorAll('.fc-err[data-slot="bytes"]').length, 0, "no row over the new text");
  assert.equal(a3.querySelectorAll(".fc-load").length, 0, "the landing ends the wait");
  assert.equal(marksOf(w3, "h5").length, 1, "the marks are back over the new text");
  assert.deepEqual(w3.hookErrors, []);
});

// ── the bytes row over a pane whose mtime is the status's, and over the earlier text (Slice 7 item 3, the review's round 1) ──

test("an svg picture's landing (the seam's onLanded, fired while the picture's own load is still out) ends the panel's wait for a reload's bytes only when the view's mtime is the status's: a landing of older bytes leaves the loader up, and the landing of the status's bytes takes it down, with no row at the deadline", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const w = world({ deferReload: true }); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ hunks: [h1, h3, h5] }));
  assert.equal(w.hooks.landed.length, 1, "the panel listens at the seam's onLanded");
  act(card(aside, "chg:h1")!, "fcreject", "h1")!.click(); await flush();
  w.disk = DOC.replace("cut", "reduced"); w.diskMtime = F11;
  const after = status({ fileMtimeNs: F11, storeMtimeNs: S12, hunks: [shifted(h3, 4), shifted(h5, 4)],
    store: { ...NO_COMMENTS, suggestions: [SUGG[1]], comments: [passage] }, unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 1, watermark: null } });
  answer(w, after, lastOf(w, "fileComments", "reject"), { rejected: ["h1"] }); await flush(); await flush();
  assert.ok(aside.querySelector('.fc-load[data-slot="bytes"]'), "the wait for the reload's bytes is up");
  const landed = (mt: string): void => { w.viewMtime = mt; for (const cb of w.hooks.landed) cb(); };
  landed("1757145600000000007");                        // bytes older than the status's land (mtimeNs() moves, to another mtime)
  await flush();
  assert.ok(aside.querySelector('.fc-load[data-slot="bytes"]'), "a landing of older bytes leaves the wait up: the loader stays");
  landed(F11);                                          // the status's bytes land
  await flush();
  assert.equal(aside.querySelectorAll(".fc-load").length, 0, "the landing of the status's bytes ends the wait: the loader goes, the picture's own load still out");
  t.mock.timers.tick(15000); await flush();
  assert.equal(aside.querySelectorAll('.fc-err[data-slot="bytes"]').length, 0, "and the deadline files no row");
});

test("the change cards between an svg picture's landing (the seam's onLanded) and the paint of its bytes (file-comments.ts, #cardState's doc): each card keeps the tags and buttons it had before the landing, the loader gone at the landing and no row at the deadline, and moves at the paint; when the paint comes first (a picture the page still holds), the landing after it changes nothing", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const after = status({ fileMtimeNs: F11, storeMtimeNs: S12, hunks: [shifted(h3, 4), shifted(h5, 4)],
    store: { ...NO_COMMENTS, suggestions: [SUGG[1]], comments: [passage] }, unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 1, watermark: null } });
  const shows = (aside: El): Record<string, { tags: string[]; buttons: string[]; reveal: string | null }> => {
    const out: Record<string, { tags: string[]; buttons: string[]; reveal: string | null }> = {};
    for (const key of ["chg:h3", "chg:h5"]) {
      const c = card(aside, key);
      assert.ok(c, key + ": the card is up");
      const rv = act(c!, "fcreveal");
      out[key] = { tags: tags(c!), buttons: texts(c!.querySelectorAll(".fc-actions button")), reveal: rv ? rv.title : null };
    }
    return out;
  };
  for (const order of ["the landing, then the paint", "the paint, then the landing"]) {
    const w = world({ deferReload: true }); t.after(() => w.close());
    const { aside } = await openPanel(w, status({ hunks: [h1, h3, h5] }));
    assert.equal(w.hooks.landed.length, 1, order + ": the panel listens at the seam's onLanded");
    act(card(aside, "chg:h1")!, "fcreject", "h1")!.click(); await flush();
    w.disk = DOC.replace("cut", "reduced"); w.diskMtime = F11;
    answer(w, after, lastOf(w, "fileComments", "reject"), { rejected: ["h1"] }); await flush(); await flush();
    assert.ok(aside.querySelector('.fc-load[data-slot="bytes"]'), order + ": the wait for the reload's bytes is up");
    const before = shows(aside);
    assert.deepEqual(before["chg:h5"], { tags: [], buttons: ["Accept", "Reject"], reveal: null }, order + ": the premise: the view's bytes are not the status's, so the insertion's card claims no tag, no Reveal and no Comment on this change");
    const landed = (): void => { w.viewMtime = F11; for (const cb of w.hooks.landed) cb(); };   // mtimeNs() the landed mtime; the body still shows the text before
    if (order === "the landing, then the paint") {
      landed(); await flush();
      assert.equal(aside.querySelectorAll(".fc-load").length, 0, order + ": the landing ends the wait: the loader goes");
      assert.deepEqual(shows(aside), before, order + ": between the landing and the paint each card keeps its tags and buttons (#cardState's doc)");
      t.mock.timers.tick(15000); await flush();
      assert.equal(aside.querySelectorAll('.fc-err[data-slot="bytes"]').length, 0, order + ": the deadline files no row");
      assert.deepEqual(shows(aside), before, order + ": and the cards still stand as before the landing");
      w.landReload!(); await flush(); await flush();   // the paint of the landed bytes
    } else {
      w.landReload!(); await flush(); await flush();   // the paint first, its onRendered with the landed mtime
      const painted = shows(aside);
      landed(); await flush();
      assert.deepEqual(shows(aside), painted, order + ": a landing told after its paint changes no card");
    }
    const now = shows(aside);
    assert.deepEqual(now["chg:h5"], { tags: [], buttons: ["Accept", "Reject", "Comment on this change"], reveal: null }, order + ": after the paint the insertion's mark is painted over the new text, so its card offers Comment on this change and no Reveal");
    assert.ok(now["chg:h3"].reveal !== null && /\(line \d+\)/.test(now["chg:h3"].reveal!), order + ": the deletion's Reveal names its line in the new text; got " + now["chg:h3"].reveal);
    assert.equal(marksOf(w, "h5").length, 1, order + ": the insertion's mark over the new text");
    assert.equal(aside.querySelectorAll(".fc-load").length, 0, order + ": no loader");
    assert.deepEqual(w.hookErrors, []);
  }
});

// ── before the view's first paint, and a panel mounted over a view that already shows the file (file-comments.ts, #cardState's
// doc, event 1) ──

/** The view as the Comments panel finds it at its mount in the viewer: the body shows none of the file and the view's mtime is
 *  empty. `media`: an svg picture's seam (mode() "media", text() null throughout, mediaElement() the picture once one is
 *  painted); else a text file's (text() null until the first paint). `land` puts a media landing's picture up (the seam's
 *  onReplaced) and tells the seam's onLanded (the bytes in hand, the picture's own load still out); `paint` paints the bytes on
 *  hand and fires onRendered. */
function unpainted(w: World, media: boolean): { land: (mt: string) => void; paint: () => void } {
  let shown = false;
  const textOf = w.ctx.text;
  const picture = new El("img"); picture.className = "fileview-img";
  w.body.replaceChildren();                              // the loader's place: no row of the file until the paint puts them back
  w.viewMtime = "";
  w.ctx.mode = () => (media ? "media" : "raw");
  w.ctx.text = () => (!media && shown ? textOf() : null);
  w.ctx.mediaElement = () => (media && shown ? picture as unknown as HTMLElement : null);
  return {
    land: (mt: string) => { w.viewMtime = mt; if (media) for (const cb of w.hooks.replaced) cb(); for (const cb of w.hooks.landed) cb(); },
    paint: () => { shown = true; w.repaint(); },
  };
}
/** The insertion's card as the person sees it: its tags, its buttons and its Reveal's title. */
const shown5 = (aside: El, key = "chg:h5"): { tags: string[]; buttons: string[]; reveal: string | null } => {
  const c = card(aside, key);
  assert.ok(c, key + ": the card is up");
  const rv = act(c!, "fcreveal");
  return { tags: tags(c!), buttons: texts(c!.querySelectorAll(".fc-actions button")), reveal: rv ? rv.title : null };
};

test("before an svg picture's first paint, a status for newer bytes than the landing's (file-comments.ts, #cardState's doc): the open's picture still loading (its landing told, no paint), a reply carrying the newer bytes' status leaves the insertion's card with no Reveal and no tag, the newer bytes' landing leaves it so, and the card moves once, at the paint that shows those bytes", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const w = world({ deferReload: true }); t.after(() => w.close());
  const view = unpainted(w, true);
  const { aside } = await openPanel(w, status({ hunks: [h1, h3, h5] }));
  view.land(F1);                                         // the open's bytes land; the picture's own request is still out, so no paint
  act(card(aside, "chg:h1")!, "fcreject", "h1")!.click(); await flush();
  w.disk = DOC.replace("cut", "reduced"); w.diskMtime = F11;
  const after = status({ fileMtimeNs: F11, storeMtimeNs: S12, hunks: [shifted(h3, 4), shifted(h5, 4)],
    store: { ...NO_COMMENTS, suggestions: [SUGG[1]], comments: [passage] }, unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 1, watermark: null } });
  answer(w, after, lastOf(w, "fileComments", "reject"), { rejected: ["h1"] }); await flush(); await flush();
  const before = shown5(aside);
  assert.deepEqual(before, { tags: [], buttons: ["Accept", "Reject"], reveal: null }, "before the first content paint the insertion's card claims no Reveal and no tag (#cardState's doc)");
  view.land(F11);                                        // the newer bytes land, their picture's load still out
  await flush();
  assert.deepEqual(shown5(aside), before, "at their landing the card keeps its state");
  view.paint(); await flush(); await flush();            // the picture of the newer bytes paints
  assert.deepEqual(shown5(aside), { tags: [], buttons: ["Accept", "Reject", "Reveal"], reveal: "Show the change in the Raw view" }, "at the paint the card moves, once: the picture marks no change, so a Reveal");
  assert.deepEqual(w.hookErrors, []);
});

test("an svg open whose status comes before its bytes land: no card moves at the landing; before the first paint the insertion's card claims no Reveal, and it takes its Reveal at the paint", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const w = world({ deferReload: true }); t.after(() => w.close());
  const view = unpainted(w, true);
  const { aside } = await openPanel(w, status({ hunks: [h1, h3, h5] }));   // the status first, the view's mtime still empty
  const before = shown5(aside);
  view.land(F1); await flush();
  assert.deepEqual(shown5(aside), before, "the landing moves no card (#cardState's doc)");
  assert.deepEqual(before, { tags: [], buttons: ["Accept", "Reject"], reveal: null }, "and before the first paint the card claims no Reveal and no tag (#cardState's doc)");
  view.paint(); await flush(); await flush();
  assert.deepEqual(shown5(aside), { tags: [], buttons: ["Accept", "Reject", "Reveal"], reveal: "Show the change in the Raw view" }, "at the paint of the status's bytes the card takes its Reveal");
  assert.deepEqual(w.hookErrors, []);
});

test("a text file's open whose status comes before its bytes land: the first paint comes and the panel reads it, marking the insertion over the text, whose card offers Comment on this change from that paint", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const w = world({ deferReload: true }); t.after(() => w.close());
  const view = unpainted(w, false);
  const { aside } = await openPanel(w, status({ hunks: [h1, h3, h5] }));
  assert.equal(marksOf(w, "h5").length, 0, "nothing marked before the text shows");
  w.viewMtime = F1; view.paint(); await flush(); await flush();   // a text landing is its paint
  assert.equal(marksOf(w, "h5").length, 1, "at the first paint the insertion is marked over the text");
  assert.deepEqual(shown5(aside), { tags: [], buttons: ["Accept", "Reject", "Comment on this change"], reveal: null }, "and its card offers Comment on this change");
  assert.deepEqual(w.hookErrors, []);
});

test("a panel mounted over a view that already shows the file (no paint heard since the mount; file-comments.ts, #cardState's doc, event 1): the insertion is marked and its card offers Comment on this change", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const w = world({ deferReload: true }); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ hunks: [h1, h3, h5] }));   // the stand-in shows DOC at F1 from the start
  assert.equal(marksOf(w, "h5").length, 1, "the insertion is marked over the text the view shows");
  assert.deepEqual(shown5(aside), { tags: [], buttons: ["Accept", "Reject", "Comment on this change"], reveal: null }, "and its card offers Comment on this change");
  assert.deepEqual(w.hookErrors, []);
});

// ── a failure pane, as the card-state rule takes it (file-comments.ts, #cardState's doc): a first open's pane, a re-ask's pane over
// landed bytes, and a failed reload of the bytes the view shows ──

/** A failure pane in place of the file, as the fetch chain's catch paints it (file-view.ts): the pane swapped in, error() the
 *  pane's words, the hooks fired; text() and mtimeNs() as they were. */
function paneOver(w: World, words: string): void {
  const why = new El("div"); why.className = "fileview-err"; why.appendChild(new Txt(words));
  w.body.replaceChildren(why); w.viewError = words;
  for (const cb of w.hooks.rendered) { try { cb(); } catch (e) { w.hookErrors.push(e); } }
}

test("a text file's first open whose fetch fails, the status in first: the failure pane moves no card, the insertion's card claiming no Reveal over it, and the card moves once, at the reload's content paint", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const w = world({ deferReload: true }); t.after(() => w.close());
  const view = unpainted(w, false);
  const { aside } = await openPanel(w, status({ hunks: [h1, h3, h5] }));   // the status first, nothing landed
  const before = shown5(aside);
  paneOver(w, "no such file: " + ABS); await flush();    // the first open's fetch fails: error() set, text() null, mtimeNs() empty
  assert.deepEqual(shown5(aside), before, "the pane moves no card (#cardState's doc)");
  assert.deepEqual(before, { tags: [], buttons: ["Accept", "Reject"], reveal: null }, "before any content paint, and over the pane, the card claims no Reveal and no tag (#cardState's doc)");
  w.viewMtime = F1; view.paint(); await flush(); await flush();   // a reload lands the file and paints it
  assert.deepEqual(shown5(aside), { tags: [], buttons: ["Accept", "Reject", "Comment on this change"], reveal: null }, "at the content paint the card moves, once: the insertion marked over the text");
  assert.equal(marksOf(w, "h5").length, 1, "the insertion's mark over the text");
  assert.deepEqual(w.hookErrors, []);
});

test("a first open whose fetch fails before the Comments panel is opened, for a text file and for an svg picture: the panel opened over the pane shows the insertion's card with no Reveal and no tag, as before any content paint (#cardState's doc)", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  for (const media of [false, true]) {
    const kind = media ? "an svg picture" : "a text file";
    const w = world({ deferReload: true }); t.after(() => w.close());
    unpainted(w, media);
    const s = status({ hunks: [h1, h3, h5] });
    const { button } = await mount(w, s);                  // the viewer mounts its actions before its first fetch
    paneOver(w, "no such file: " + ABS); await flush();   // that fetch answers 404: the pane, mtimeNs() empty
    button.click(); answer(w, s); await flush(); await flush();   // the person opens the panel over the pane
    const aside = w.main.querySelector(".fileview-aside")!;
    assert.ok(aside, kind + ": the panel is open");
    assert.deepEqual(shown5(aside), { tags: [], buttons: ["Accept", "Reject"], reveal: null }, kind + ": over the pane the card claims no Reveal and no tag (#cardState's doc)");
    assert.deepEqual(w.hookErrors, []);
    w.close();
  }
});

test("an svg picture's reload whose bytes land and whose picture fails, the address asked again and that fetch failing too: the card keeps its state through the pane and moves once, at the way back's paint of the landed bytes (#cardState's doc)", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const w = world({ deferReload: true }); t.after(() => w.close());
  const view = unpainted(w, true);
  const { aside } = await openPanel(w, status({ hunks: [h1, h3, h5] }));
  view.land(F1); view.paint(); await flush(); await flush();   // the open's picture: a content paint at F1
  act(card(aside, "chg:h1")!, "fcreject", "h1")!.click(); await flush();
  w.disk = DOC.replace("cut", "reduced"); w.diskMtime = F11;
  const after = status({ fileMtimeNs: F11, storeMtimeNs: S12, hunks: [shifted(h3, 4), shifted(h5, 4)],
    store: { ...NO_COMMENTS, suggestions: [SUGG[1]], comments: [passage] }, unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 1, watermark: null } });
  answer(w, after, lastOf(w, "fileComments", "reject"), { rejected: ["h1"] }); await flush(); await flush();
  const before = shown5(aside);
  assert.deepEqual(before, { tags: [], buttons: ["Accept", "Reject"], reveal: null }, "the premise: the view shows the picture of F1, not the status's bytes");
  view.land(F11); await flush();                         // the reload's bytes land; their picture's own request is still out
  assert.deepEqual(shown5(aside), before, "at the landing the card keeps its state");
  paneOver(w, "tunnel to TESTHOST is not answering; re-dialing"); await flush();   // the picture failed, the address was asked again, and that fetch failed: its pane
  assert.equal(w.ctx.mtimeNs(), F11, "the view's mtime is the landing's while the pane stands");
  assert.deepEqual(shown5(aside), before, "the pane moves no card (#cardState's doc)");
  view.paint(); await flush(); await flush();            // the way back: the address answers and the landed bytes' picture paints
  assert.deepEqual(shown5(aside), { tags: [], buttons: ["Accept", "Reject", "Reveal"], reveal: "Show the change in the Raw view" }, "at the way back's paint the card moves, once: the picture marks no change, so a Reveal");
  assert.deepEqual(w.hookErrors, []);
});

test("a painted text file whose reload fails with no landing: the pane moves no card (control: the view's mtime and the painted one are the same before and after it)", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const w = world({ deferReload: true }); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ hunks: [h1, h3, h5] }));   // the stand-in shows DOC at F1
  act(card(aside, "chg:h1")!, "fcreject", "h1")!.click(); await flush();
  w.disk = DOC.replace("cut", "reduced"); w.diskMtime = F11;
  const after = status({ fileMtimeNs: F11, storeMtimeNs: S12, hunks: [shifted(h3, 4), shifted(h5, 4)],
    store: { ...NO_COMMENTS, suggestions: [SUGG[1]], comments: [passage] }, unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 1, watermark: null } });
  answer(w, after, lastOf(w, "fileComments", "reject"), { rejected: ["h1"] }); await flush(); await flush();
  const before = shown5(aside);
  assert.ok(w.failReload, "the reject's reload is out");
  w.failReload!("no such file: " + ABS); await flush();  // the reload fails: the pane, the mtime still F1
  assert.deepEqual(shown5(aside), before, "the pane moves no card");
  assert.deepEqual(w.hookErrors, []);
});

// ── the change cards over a failure pane after a content paint, as the card-state rule takes them (file-comments.ts, #cardState's
// doc): the same bytes failing and coming back, a raster picture's bytes that do not decode, a status that differs arriving over
// the pane, and a landing of new bytes after one ──

/** Each change card of the three the status carries (h1 a substitution, h3 a deletion, h5 an insertion) as the person sees it: its
 *  tags, its buttons, its Reveal's title and whether its reference links to a mark. */
const cardsOf = (aside: El): Record<string, { tags: string[]; buttons: string[]; reveal: string | null; link: boolean }> =>
  Object.fromEntries(["chg:h1", "chg:h3", "chg:h5"].map((k) => [k, { ...shown5(aside, k), link: isLink(card(aside, k)!) }]));

test("a painted text file whose status is current and whose changes are marked, and a reload of the same bytes that fails: over the pane each change card keeps the state the last content paint gave it (no not shown tag, no Reveal, and Comment on this change and the link to its mark as they were), and the same bytes' content paint after the pane moves none", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const w = world({ deferReload: true }); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ hunks: [h1, h3, h5] }));   // the stand-in shows DOC at F1, the status's bytes
  const before = cardsOf(aside);
  assert.deepEqual(before["chg:h5"], { tags: [], buttons: ["Accept", "Reject", "Comment on this change"], reveal: null, link: true }, "the premise: the insertion is marked over the text the view shows, its card linking to the mark");
  assert.deepEqual(["h1", "h3", "h5"].map((id) => marksOf(w, id).length > 0), [true, true, true], "the premise: each change marked");
  w.ctx.reload();                                        // a reload the panel did not ask (the changed-on-disk bar's Reload, say)
  w.failReload!("no such file: " + ABS); await flush();  // its fetch answers 404: the pane, the text and the mtime as the last landing left them
  assert.equal(w.ctx.error(), "no such file: " + ABS, "the pane stands");
  assert.equal(w.ctx.mtimeNs(), F1, "the view's mtime is the status's under the pane");
  assert.deepEqual(cardsOf(aside), before, "over the pane each change card keeps the state the last content paint gave it: no not shown tag and no Reveal claimed, no Comment on this change and no link dropped (#cardState's doc; at fe43d2c2a every card took the not shown tag and lost its link at the pane, the insertion's and the substitution's a Reveal too, and the next paint took them back)");
  w.ctx.reload(); w.landReload!(); await flush(); await flush();   // the same bytes land and paint
  assert.equal(w.ctx.error(), null, "a content paint");
  assert.deepEqual(cardsOf(aside), before, "the same bytes' content paint moves no card either");
  assert.deepEqual(["h1", "h3", "h5"].map((id) => marksOf(w, id).length > 0), [true, true, true], "each change marked again");
  assert.deepEqual(w.hookErrors, []);
});

test("a raster picture's reload whose bytes do not decode: its landing tells the seam's onLanded nothing, so mtimeNs() is the landed mtime under the decode-failure pane, and still the change card keeps over the pane the state the last content paint gave it, and moves once, at the paint of bytes that decode", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const DECODE = "this image failed to decode: it may be mid-write or truncated";   // the pane's own sentence (DECODE_FAILED)
  const w = world({ deferReload: true }); t.after(() => w.close());
  const view = unpainted(w, true);                       // a picture's seam: mode() "media", text() null
  const { aside } = await openPanel(w, status({ hunks: [h1, h3, h5] }));
  w.viewMtime = F1; view.paint(); await flush(); await flush();   // the picture's first content paint at F1 (a raster landing tells no onLanded)
  act(card(aside, "chg:h1")!, "fcreject", "h1")!.click(); await flush();
  w.disk = DOC.replace("cut", "reduced"); w.diskMtime = F11;
  const after = status({ fileMtimeNs: F11, storeMtimeNs: S12, hunks: [shifted(h3, 4), shifted(h5, 4)],
    store: { ...NO_COMMENTS, suggestions: [SUGG[1]], comments: [passage] }, unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 1, watermark: null } });
  answer(w, after, lastOf(w, "fileComments", "reject"), { rejected: ["h1"] }); await flush(); await flush();
  const before = shown5(aside);
  assert.deepEqual(before, { tags: [], buttons: ["Accept", "Reject"], reveal: null }, "the premise: the view shows the picture of F1, not the status's bytes");
  assert.ok(w.failReload, "the reject's reload is out");
  w.viewMtime = F11;                                     // the landing: the mtime moves ahead of the decode, and no onLanded is told
  w.failReload!(DECODE); await flush();                  // the bytes do not decode: the pane
  assert.equal(w.ctx.mtimeNs(), F11, "the view's mtime is the landed one, the status's, under the pane");
  assert.deepEqual(shown5(aside), before, "the pane moves no card (#cardState's doc; at fe43d2c2a the card took a Reveal at the pane, read against the landed mtime)");
  act(aside.querySelector('.fc-err[data-slot="bytes"]')!, "fcreload")!.click(); await flush();   // the row's Reload
  answer(w, after); await flush(); await flush();        // its status, over the pane
  assert.deepEqual(shown5(aside), before, "the Reload's status over the pane, the same as the one showing, moves no card (#cardState's doc)");
  w.landReload!(); await flush(); await flush();         // the bytes decode this time: the picture's content paint at F11
  assert.deepEqual(shown5(aside), { tags: [], buttons: ["Accept", "Reject", "Reveal"], reveal: "Show the change in the Raw view" }, "at the paint of bytes that decode the card moves, once: the picture marks no change, so a Reveal");
  assert.deepEqual(w.hookErrors, []);
});

test("a status that differs arriving over a failure pane (#cardState's doc): the insertion's and the substitution's cards claim no tag, no Reveal, no Comment on this change and no link, the deletion's Reveal, naming no line, and its Comment on this change standing; the next content paint gives each card its state", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
  const w = world({ deferReload: true }); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ hunks: [h1, h3, h5] }));
  const painted = cardsOf(aside);
  w.ctx.reload(); w.failReload!("no such file: " + ABS); await flush();   // a reload of the same bytes fails: the pane
  assert.deepEqual(cardsOf(aside), painted, "the pane alone moves no card");
  // the sidecar moves (a comment written from another client), the file's mtime still F1: the poll re-reads the status over the pane
  w.mtimes[STORE_PATH] = S5;
  const asks = countOf(w, "fileComments", "status");
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  assert.equal(countOf(w, "fileComments", "status"), asks + 1, "the poll re-asked status");
  answer(w, status({ hunks: [h1, h3, h5], storeMtimeNs: S5 })); await flush(); await flush();
  assert.equal(w.ctx.error(), "no such file: " + ABS, "the pane still stands");
  const over = cardsOf(aside);
  assert.deepEqual(over["chg:h5"], { tags: [], buttons: ["Accept", "Reject"], reveal: null, link: false }, "the insertion's card at the status that differs: no Comment on this change, no Reveal, no tag and no link (#cardState's doc)");
  assert.deepEqual(over["chg:h1"], { tags: [], buttons: ["Accept", "Reject"], reveal: null, link: false }, "the substitution's card: the same");
  assert.deepEqual(over["chg:h3"], { tags: [], buttons: ["Accept", "Reject", "Comment on this change", "Reveal"], reveal: "Show the change in the Raw view", link: false }, "the deletion's card: its Reveal and its Comment on this change stand, the Reveal naming no line (#cardState's doc)");
  w.ctx.reload(); w.landReload!(); await flush(); await flush();   // the same bytes land and paint
  assert.deepEqual(cardsOf(aside), painted, "the next content paint gives each card its state: the marks over the text again");
  assert.deepEqual(w.hookErrors, []);
});

test("a pane, then a landing of new bytes: no card moves at the pane; with the status arriving over the pane each card moves at that status (#cardState's doc), and in both orders each moves once at the content paint of the new bytes", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
  const after = status({ fileMtimeNs: F11, storeMtimeNs: S12, hunks: [shifted(h3, 4), shifted(h5, 4)],
    store: { ...NO_COMMENTS, suggestions: [SUGG[1]], comments: [passage] }, unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 1, watermark: null } });
  const painted = { tags: [], buttons: ["Accept", "Reject", "Comment on this change"], reveal: null };
  for (const order of ["the status in before the pane", "the status arriving over the pane"]) {
    const w = world({ deferReload: true }); t.after(() => w.close());
    const { aside } = await openPanel(w, status({ hunks: [h1, h3, h5] }));
    if (order === "the status in before the pane") {
      act(card(aside, "chg:h1")!, "fcreject", "h1")!.click(); await flush();
      w.disk = DOC.replace("cut", "reduced"); w.diskMtime = F11;
      answer(w, after, lastOf(w, "fileComments", "reject"), { rejected: ["h1"] }); await flush(); await flush();
      const before = shown5(aside);
      assert.deepEqual(before, { tags: [], buttons: ["Accept", "Reject"], reveal: null }, order + ": the premise: the view's bytes are not the status's");
      w.failReload!("no such file: " + ABS); await flush();   // the reject's reload fails: the pane
      assert.deepEqual(shown5(aside), before, order + ": the pane moves no card");
      act(aside.querySelector('.fc-err[data-slot="bytes"]')!, "fcreload")!.click(); await flush();   // the row's Reload
      answer(w, after); await flush(); await flush();
      assert.deepEqual(shown5(aside), before, order + ": the Reload's status over the pane, the same as the one showing, moves no card (#cardState's doc)");
    } else {
      const before = shown5(aside);
      assert.deepEqual(before, painted, order + ": the premise: the insertion marked over the text the view shows");
      w.ctx.reload(); w.failReload!("no such file: " + ABS); await flush();   // a reload the panel did not ask fails: the pane
      assert.deepEqual(shown5(aside), before, order + ": the pane moves no card");
      // the session rewrote the file: the poll sees F11 and re-reads the status, and its fetch is asked on the mtime it saw
      w.disk = DOC.replace("cut", "reduced"); w.diskMtime = F11; w.mtimes[ABS] = F11;
      t.mock.timers.tick(2500); await flush(); await flush(); await flush();
      answer(w, after); await flush(); await flush();
      assert.equal(w.ctx.error(), "no such file: " + ABS, order + ": the pane still stands");
      assert.deepEqual(shown5(aside), { tags: [], buttons: ["Accept", "Reject"], reveal: null }, order + ": the status over the pane moves the card once (#cardState's doc)");
    }
    assert.ok(w.landReload, order + ": a fetch of the new bytes is out");
    w.landReload!(); await flush(); await flush();       // the new bytes land and paint
    assert.deepEqual(shown5(aside), painted, order + ": at the content paint of the new bytes the card moves, once: the insertion marked over the new text");
    assert.equal(marksOf(w, "h5").length, 1, order + ": the insertion's mark over the new text");
    assert.deepEqual(w.hookErrors, []);
    w.close();
  }
});

test("a picture's landing moves mtimeNs() to the status's mtime BEFORE its bytes decode (file-view.ts assigns the mtime ahead of the Blob branch; the img's error fires imgFailed later), so the pane has the status's mtime under it: the row bytesFailed files at that paint stands, with the pane's sentence and Reload, the loader gone, through a status over the pane and the deadline's tick; a Reload whose bytes decode takes it away", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const DECODE = "this image failed to decode: it may be mid-write or truncated";   // the pane's own sentence, as error() answers it (contract C1)
  const after = status({ fileMtimeNs: F11, storeMtimeNs: S12, hunks: [shifted(h3, 4), shifted(h5, 4)],
    store: { ...NO_COMMENTS, suggestions: [SUGG[1]], comments: [passage] }, unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 1, watermark: null } });
  const { BYTES_FAILED } = await import("./file-comments");
  // the text stand-in with the media landing's ORDER, then the same over a media seam (mode() "media", text() null, as a picture's is)
  for (const media of [false, true]) {
    const w = world({ deferReload: true }); t.after(() => w.close());
    if (media) { w.ctx.mode = () => "media"; w.ctx.text = () => null; }
    const { aside } = await openPanel(w, status({ hunks: [h1, h3, h5] }));
    act(card(aside, "chg:h1")!, "fcreject", "h1")!.click(); await flush();
    w.disk = DOC.replace("cut", "reduced"); w.diskMtime = F11;
    answer(w, after, lastOf(w, "fileComments", "reject"), { rejected: ["h1"] }); await flush(); await flush();
    assert.ok(aside.querySelector('.fc-load[data-slot="bytes"]'), "the wait is up"); assert.ok(w.failReload, "the reload is out");
    w.viewMtime = F11;                                   // the landing's mtime, ahead of the decode
    w.failReload!(DECODE); await flush();
    assert.equal(w.ctx.mtimeNs(), after.fileMtimeNs, "the view's mtime is the status's while the pane stands");
    assert.deepEqual(w.hookErrors, []);
    assert.equal(aside.querySelectorAll(".fc-load").length, 0, "the loader went at the pane's paint");
    const row = aside.querySelector('.fc-cards .fc-err[data-slot="bytes"]');
    assert.ok(row, (media ? "media seam" : "text stand-in") + ": the row stands (before: filed by bytesFailed and deleted by bytesLanded in the same pass, the mtime under the pane being the status's)");
    assert.equal(row!.childNodes[0].textContent, BYTES_FAILED + " (" + DECODE + "); the view shows that failure in place of the file, so no change is marked. Reload to read the file again.", "the pane's sentence, in the row's fixed shape");
    assert.ok(act(row!, "fcreload"), "with Reload");
    assert.equal(marksOf(w).length, 0, "nothing marked over the pane");
    // a status over the standing pane (the poll): the mtime is the view's, so no wait and no loader; the row stands; the deadline's tick adds nothing
    answer(w, after); await flush(); await flush();
    assert.equal(w.reloads, 1, "the same mtime: no second fetch");
    assert.equal(aside.querySelectorAll(".fc-load").length, 0, "no loader over the pane");
    assert.equal(aside.querySelectorAll('.fc-err[data-slot="bytes"]').length, 1, "the row stands through the status");
    t.mock.timers.tick(15000); await flush();
    assert.equal(aside.querySelectorAll('.fc-err[data-slot="bytes"]').length, 1, "no deadline row joins it");
    // the row's Reload: the bytes decode this time, and the landing that shows the file takes the row away (bytesLanded)
    act(row!, "fcreload")!.click(); await flush();
    assert.equal(w.reloads, 2, "Reload re-fetches");
    answer(w, after); await flush(); await flush();
    w.landReload!(); await flush(); await flush();
    assert.equal(w.viewError, null, "a content paint clears error()");
    assert.equal(aside.querySelectorAll('.fc-err[data-slot="bytes"]').length, 0, "the landing answers the row");
    assert.equal(aside.querySelectorAll(".fc-load").length, 0);
    if (!media) assert.equal(marksOf(w, "h5").length, 1, "the marks are back over the new text");
    assert.deepEqual(w.hookErrors, []);
    w.close();
  }
});

test("after the failure row, a Raw or Rendered click repaints the last landing's text over the pane (renderBody: error() null, the mtime still not the status's, so no landing answers the row): the row keeps the seam's words and takes the deadline row's tail, true of what shows now, with Reload; a second repaint leaves it; the pane coming back files the failure row again; the landing takes the row away", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const w = world({ deferReload: true }); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ hunks: [h1, h3, h5] }));
  act(card(aside, "chg:h1")!, "fcreject", "h1")!.click(); await flush();
  w.disk = DOC.replace("cut", "reduced"); w.diskMtime = F11;
  const after = status({ fileMtimeNs: F11, storeMtimeNs: S12, hunks: [shifted(h3, 4), shifted(h5, 4)],
    store: { ...NO_COMMENTS, suggestions: [SUGG[1]], comments: [passage] }, unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 1, watermark: null } });
  answer(w, after, lastOf(w, "fileComments", "reject"), { rejected: ["h1"] }); await flush(); await flush();
  const WORDS = "no such file: " + ABS;
  w.failReload!(WORDS); await flush();
  const { BYTES_FAILED } = await import("./file-comments");
  const FAILED_ROW = BYTES_FAILED + " (" + WORDS + "); the view shows that failure in place of the file, so no change is marked. Reload to read the file again.";
  const OVER_TEXT_ROW = BYTES_FAILED + " (" + WORDS + "); the view still shows the earlier text, with no change marked on it. Reload to read the file again.";
  const rowText = () => { const r = aside.querySelector('.fc-cards .fc-err[data-slot="bytes"]'); return r ? r.childNodes[0].textContent : null; };
  assert.equal(rowText(), FAILED_ROW, "the failure row over the pane");
  assert.equal(w.body.querySelectorAll(".fv-cl").length, 0, "the pane, no rows");
  // the format click: the earlier text is back, the pane gone, nothing landed
  w.repaint(); await flush();
  assert.equal(w.viewError, null, "a content paint: error() null");
  assert.equal(w.body.querySelectorAll(".fv-cl").length, 10, "the last landing's rows are back");
  assert.equal(w.viewMtime, F1, "the last landing's mtime, not the status's: no landing");
  assert.equal(marksOf(w).length, 0, "no change is marked over the earlier text (the offsets index other bytes)");
  assert.equal(rowText(), OVER_TEXT_ROW, "the seam's words, and the tail that says what shows now (before: the failure tail, false about a view showing the text)");
  assert.ok(act(aside.querySelector('.fc-err[data-slot="bytes"]')!, "fcreload"), "Reload stays");
  assert.equal(aside.querySelectorAll(".fc-load").length, 0, "no loader: nothing is out");
  assert.deepEqual(w.hookErrors, []);
  // the other format button: the same text again, the row left as it is
  w.repaint(); await flush();
  assert.equal(rowText(), OVER_TEXT_ROW, "a second repaint changes nothing");
  assert.equal(aside.querySelectorAll('.fc-err[data-slot="bytes"]').length, 1, "one row");
  t.mock.timers.tick(15000); await flush();
  assert.equal(rowText(), OVER_TEXT_ROW, "no deadline runs: the wait ended at the failure");
  // the row's Reload fails again (the browser's order: the status lands first, over the earlier text; then the pane): the failure row anew
  act(aside.querySelector('.fc-err[data-slot="bytes"]')!, "fcreload")!.click(); await flush();
  assert.equal(w.reloads, 2);
  answer(w, after); await flush(); await flush();
  assert.equal(rowText(), null, "the click took the row, and the status over the earlier text files none (no pane)");
  assert.ok(w.failReload, "the fetch is still out");
  w.failReload!(WORDS); await flush();
  assert.equal(aside.querySelectorAll(".fc-load").length, 0, "the pane's paint ends the wait");
  assert.equal(rowText(), FAILED_ROW, "the pane is back, and so is the row that says so");
  // and the landing: the row goes with the click, the loader stands through the status landing first over the pane (the click's
  // fetch is out, reloadOut; the review's round 4), and the paint that shows the status's text ends the wait
  act(aside.querySelector('.fc-err[data-slot="bytes"]')!, "fcreload")!.click(); await flush();
  answer(w, after); await flush(); await flush();
  assert.equal(rowText(), null, "the status over the standing pane files no row while the click's fetch is out (before round 4: the row again, off the standing pane)");
  assert.ok(aside.querySelector('.fc-load[data-slot="bytes"]'), "the loader stands for that fetch");
  w.landReload!(); await flush(); await flush();
  assert.equal(w.viewError, null); assert.equal(w.viewMtime, F11);
  assert.equal(rowText(), null, "no row over the new text"); assert.equal(aside.querySelectorAll(".fc-load").length, 0, "the landing ends the wait");
  assert.equal(marksOf(w, "h5").length, 1, "the marks are back over the new text");
  assert.deepEqual(w.hookErrors, []);
});

// ── the failure row against every later paint (Slice 7 item 3, the review's round 2) ──────────────────

/** The failure row up: a reject's reply, its reload failed with `WORDS` (the kernel's 404 body), the pane in the body. */
async function failureRow(t: TestContext, apis: Array<"setTimeout" | "setInterval"> = ["setTimeout"]): Promise<{ w: World; aside: El; after: Status; WORDS: string; FAILED_ROW: string; OVER_TEXT_ROW: string; rowText: () => string | null; failedRow: (words: string) => string }> {
  t.mock.timers.enable({ apis });
  const w = world({ deferReload: true }); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ hunks: [h1, h3, h5] }));
  act(card(aside, "chg:h1")!, "fcreject", "h1")!.click(); await flush();
  w.disk = DOC.replace("cut", "reduced"); w.diskMtime = F11;
  const after = status({ fileMtimeNs: F11, storeMtimeNs: S12, hunks: [shifted(h3, 4), shifted(h5, 4)],
    store: { ...NO_COMMENTS, suggestions: [SUGG[1]], comments: [passage] }, unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 1, watermark: null } });
  answer(w, after, lastOf(w, "fileComments", "reject"), { rejected: ["h1"] }); await flush(); await flush();
  const WORDS = "no such file: " + ABS;
  assert.ok(w.failReload, "the reject's reload is out");
  w.failReload!(WORDS); await flush();
  const { BYTES_FAILED } = await import("./file-comments");
  const failedRow = (words: string) => BYTES_FAILED + " (" + words + "); the view shows that failure in place of the file, so no change is marked. Reload to read the file again.";
  const FAILED_ROW = failedRow(WORDS);
  const OVER_TEXT_ROW = BYTES_FAILED + " (" + WORDS + "); the view still shows the earlier text, with no change marked on it. Reload to read the file again.";
  const rowText = () => { const r = aside.querySelector('.fc-cards .fc-err[data-slot="bytes"]'); return r ? r.childNodes[0].textContent : null; };
  assert.equal(rowText(), FAILED_ROW, "the failure row over the pane");
  assert.equal(w.body.querySelectorAll(".fileview-err").length, 1, "the pane stands in the body");
  assert.equal(w.viewMtime, F1, "the view's mtime is the last landing's");
  return { w, aside, after, WORDS, FAILED_ROW, OVER_TEXT_ROW, rowText, failedRow };
}

test("while the failure row stands, a landing of text NEWER than the status's (the disk bar's Reload, raised at focus; the poll's re-fetch landing before its status): the row goes with the landing, the file it said could not be read having been read; the status at that mtime then paints the marks; the row's own words never stand over the new text", async (t: TestContext) => {
  const { w, aside, after, rowText } = await failureRow(t, ["setTimeout", "setInterval"]);
  // the session rewrote the file (F21, newer than the status's F11) and the viewer re-fetched on its own: fetchFile alone, no status ask
  const NEWER = DOC.replace("cut", "reduced") + "One more line the session added.\n";
  w.disk = NEWER; w.diskMtime = F21;
  const asks = countOf(w, "fileComments", "status");
  w.ctx.reload(); assert.ok(w.landReload, "the viewer's own fetch is out");
  w.landReload!(); await flush(); await flush();
  assert.deepEqual(w.hookErrors, []);
  assert.equal(w.viewError, null, "a content paint: error() null");
  assert.equal(w.viewMtime, F21, "the view's mtime moved to the landing's");
  assert.notEqual(w.viewMtime, after.fileMtimeNs, "…which is not the status's");
  assert.equal(w.body.querySelectorAll(".fv-cl").length, 11, "the new text shows (the earlier text had 10 rows)");
  assert.equal(marksOf(w).length, 0, "nothing is marked over text the status does not index");
  assert.equal(countOf(w, "fileComments", "status"), asks, "no status was asked: the panel had no hand in this landing");
  assert.equal(rowText(), null, "the landing answers the row: the file was read again (before: 'the view still shows the earlier text, with no change marked on it' over the NEW text, until the status at F21 landed)");
  assert.equal(aside.querySelectorAll(".fc-load").length, 0, "no loader: nothing is out");
  // the poll's tick: its HEAD sees F21 against the status's F11, asks the fetch on it and re-asks status; the status at the
  // landing's mtime paints the marks over the new text; no row at any point
  w.mtimes[ABS] = F21;
  const reloads = w.reloads;
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  assert.equal(countOf(w, "fileComments", "status"), asks + 1, "the poll re-asked status");
  assert.equal(w.reloads, reloads + 1, "…and asked the fetch on the mtime it saw");
  assert.equal(rowText(), null, "no row while the ask is out");
  const newest = status({ fileMtimeNs: F21, storeMtimeNs: S12, hunks: [shifted(h3, 4), shifted(h5, 4)],
    store: { ...NO_COMMENTS, suggestions: [SUGG[1]], comments: [passage] }, unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 1, watermark: null } });
  answer(w, newest); await flush(); await flush();
  assert.equal(marksOf(w, "h5").length, 1, "the marks are back over the new text");
  assert.equal(rowText(), null, "and no row");
  assert.equal(aside.querySelectorAll(".fc-load").length, 0, "the view shows the status's text: no wait");
  w.landReload!(); await flush(); await flush();                  // the poll's fetch lands the same bytes: nothing changes
  assert.equal(rowText(), null); assert.equal(marksOf(w, "h5").length, 1);
  assert.deepEqual(w.hookErrors, []);
});

test("after the row flipped to the text tail (a Raw or Rendered click), a reload the panel did not ask (the seam's reload(): the disk bar's Reload, a moved figure's re-fetch; no wait armed, no status ask) that fails again brings the pane back: the row wears the failure tail again, in the pane's words, with Reload; a further repaint flips it back", async (t: TestContext) => {
  const { w, aside, FAILED_ROW, OVER_TEXT_ROW, WORDS, rowText } = await failureRow(t);
  w.repaint(); await flush();
  assert.equal(rowText(), OVER_TEXT_ROW, "the format click: the earlier text back, the row's tail says so");
  const reloads = w.reloads, asks = countOf(w, "fileComments", "status");
  w.ctx.reload(); await flush();
  assert.equal(w.reloads, reloads + 1, "the seam re-fetches");
  assert.equal(countOf(w, "fileComments", "status"), asks, "no status ask: the panel did not ask this reload");
  assert.equal(aside.querySelectorAll(".fc-load").length, 0, "no wait armed, no loader");
  assert.ok(w.failReload, "the fetch is out");
  w.failReload!(WORDS); await flush();
  assert.deepEqual(w.hookErrors, []);
  assert.equal(w.body.querySelectorAll(".fileview-err").length, 1, "the pane stands in the body again");
  assert.equal(w.body.querySelectorAll(".fv-cl").length, 0, "no text rows");
  assert.equal(w.viewError, WORDS, "error() answers the pane's words");
  assert.equal(aside.querySelectorAll(".fc-load").length, 0, "no loader");
  assert.equal(rowText(), FAILED_ROW, "the row says the view shows the failure (before: it kept 'the view still shows the earlier text' over the pane)");
  assert.ok(act(aside.querySelector('.fc-err[data-slot="bytes"]')!, "fcreload"), "Reload stays");
  assert.equal(aside.querySelectorAll('.fc-err[data-slot="bytes"]').length, 1, "one row");
  // and back: the earlier text repainted over the pane once more
  w.repaint(); await flush();
  assert.equal(rowText(), OVER_TEXT_ROW, "the text tail again");
  assert.deepEqual(w.hookErrors, []);
});

test("the row's Reload sends the status ask and the fetch together; the status lands first, over the standing pane, and files no row while the click's fetch is out (reloadOut: the loader stands, the wait armed); the fetch is then refused for another reason: the row files at the paint that shows the new pane, in its words; the other order as a control", async (t: TestContext) => {
  const { w, aside, rowText, failedRow } = await failureRow(t);
  const OTHER = "file too large to show: 60 MB, the cap is 8 MB";   // the session restored the file as a dump: the kernel refuses 413 with these words
  act(aside.querySelector('.fc-err[data-slot="bytes"]')!, "fcreload")!.click(); await flush();
  assert.equal(rowText(), null, "the click takes the row");
  assert.ok(aside.querySelector('.fc-load[data-slot="bytes"]'), "the slot wears the loader");
  assert.ok(w.failReload, "the fetch is out");
  const after = status({ fileMtimeNs: F11, storeMtimeNs: S12, hunks: [shifted(h3, 4), shifted(h5, 4)],
    store: { ...NO_COMMENTS, suggestions: [SUGG[1]], comments: [passage] }, unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 1, watermark: null } });
  answer(w, after); await flush(); await flush();
  assert.equal(rowText(), null, "the status over the standing pane files no row: the click's fetch is out and the pane is the failure before the click (before round 4: the row again, in that pane's words)");
  assert.ok(aside.querySelector('.fc-load[data-slot="bytes"]'), "the loader stands for that fetch (before round 4: gone)");
  w.failReload!(OTHER); await flush(); await flush();
  assert.deepEqual(w.hookErrors, []);
  assert.equal(w.viewError, OTHER, "error() answers the new pane's words");
  assert.equal(w.body.querySelector(".fileview-err")!.textContent, OTHER, "the new pane stands");
  assert.equal(rowText(), failedRow(OTHER), "the row files at the new pane's paint, in its words (before round 2: the first failure's words under the second's pane, until dismissed, the next status or a landing)");
  assert.equal(aside.querySelectorAll(".fc-load").length, 0, "the pane's paint ends the wait");
  assert.equal(aside.querySelectorAll('.fc-err[data-slot="bytes"]').length, 1, "one row");
  assert.equal(aside.querySelectorAll(".fc-load").length, 0);
  // the other order, as a control: the fetch refused first (no wait is armed until the status lands, so the pane's paint files
  // nothing and the slot wears the loader of the ask), then the status: the wait it arms ends at once off the new pane (the head's
  // clause), in its words
  act(aside.querySelector('.fc-err[data-slot="bytes"]')!, "fcreload")!.click(); await flush();
  w.failReload!(OTHER); await flush();
  assert.equal(rowText(), null, "no row yet: the status ask is out, and only its landing arms the wait");
  assert.ok(aside.querySelector('.fc-load[data-slot="bytes"]'), "the slot wears the loader for the ask");
  answer(w, after); await flush(); await flush();
  assert.equal(rowText(), failedRow(OTHER), "the status over the standing pane files the row in that pane's words");
  assert.equal(aside.querySelectorAll(".fc-load").length, 0);
  assert.deepEqual(w.hookErrors, []);
});

// ── a fetch of the panel's asking out over a standing pane (Slice 7 item 3, the review's round 4) ─────

test("the row's Reload over a standing pane whose fetch never answers (a kernel from before this feature, a stalled tunnel): the status lands first and arms the wait; the loader stands through it, no row is filed off the standing pane, and the deadline row files at 15 s where before nothing did (the head's re-file had cleared the deadline and the ask's end had taken the slot); the deadline row's Reload asks again, and its landing clears everything", async (t: TestContext) => {
  const { w, aside, rowText } = await failureRow(t);
  const asks = countOf(w, "fileComments", "status");
  act(aside.querySelector('.fc-err[data-slot="bytes"]')!, "fcreload")!.click(); await flush();
  assert.equal(w.reloads, 2, "the click re-fetches"); assert.equal(countOf(w, "fileComments", "status"), asks + 1, "…and re-asks status");
  assert.equal(rowText(), null, "the click takes the row");
  assert.ok(aside.querySelector('.fc-load[data-slot="bytes"]'), "the slot wears the loader");
  const after = status({ fileMtimeNs: F11, storeMtimeNs: S12, hunks: [shifted(h3, 4), shifted(h5, 4)],
    store: { ...NO_COMMENTS, suggestions: [SUGG[1]], comments: [passage] }, unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 1, watermark: null } });
  answer(w, after); await flush(); await flush();
  assert.equal(w.reloads, 2, "the same mtime: the status asks no second fetch");
  assert.equal(rowText(), null, "no row off the standing pane while the click's fetch is out (before round 4: the failure row again, at once)");
  assert.ok(aside.querySelector('.fc-load[data-slot="bytes"]'), "the loader stands through the status (before round 4: the ask's end took the slot)");
  assert.ok(w.landReload, "the fetch is still out");
  assert.equal(w.body.querySelectorAll(".fileview-err").length, 1, "the pane stands in the body meanwhile");
  // the fetch never answers: the deadline is the one event left, and it speaks
  t.mock.timers.tick(14999); await flush();
  assert.equal(rowText(), null, "nothing before the deadline"); assert.ok(aside.querySelector('.fc-load[data-slot="bytes"]'), "the loader holds");
  t.mock.timers.tick(1); await flush();
  assert.equal(aside.querySelectorAll(".fc-load").length, 0, "the loader yields at the deadline");
  const row = aside.querySelector('.fc-cards .fc-err[data-slot="bytes"]');
  assert.ok(row, "…to the deadline row where it was (before round 4: no row ever filed, the row's Reload the only door, and it repeated the sequence)");
  assert.match(row!.textContent, /have not arrived after 15 s/);
  assert.ok(act(row!, "fcreload"), "with Reload");
  // the deadline row's Reload: the same two sends, the status first again, and this time the fetch lands
  act(row!, "fcreload")!.click(); await flush();
  assert.equal(w.reloads, 3); assert.equal(countOf(w, "fileComments", "status"), asks + 2);
  assert.ok(aside.querySelector('.fc-load[data-slot="bytes"]'), "the loader for the re-read");
  answer(w, after); await flush(); await flush();
  assert.equal(rowText(), null, "no row while the fetch is out");
  assert.ok(aside.querySelector('.fc-load[data-slot="bytes"]'), "the loader stands through the status");
  w.landReload!(); await flush(); await flush();
  assert.equal(w.viewError, null); assert.equal(w.viewMtime, F11);
  assert.equal(rowText(), null, "no row over the new text"); assert.equal(aside.querySelectorAll(".fc-load").length, 0, "the landing ends the wait");
  assert.equal(marksOf(w, "h5").length, 1, "the marks are back over the new text");
  t.mock.timers.tick(15000); await flush();
  assert.equal(rowText(), null, "the landing cleared the deadline: a later tick files nothing");
  assert.deepEqual(w.hookErrors, []);
});

test("a fetch the panel asks on a NEW mtime while a pane stands (the poll's tick: its HEAD sees the file rewritten since the failure and asks the fetch on that mtime; a reply's askReload is the same path): the status that follows arms the wait and the loader stands, no row filed off the standing pane; the fetch's own paint settles it: refused, the row in the new pane's words at that paint; landed, the loader goes and the marks paint", async (t: TestContext) => {
  const { w, aside, rowText, failedRow, FAILED_ROW } = await failureRow(t, ["setTimeout", "setInterval"]);
  const OTHER = "file too large to show: 60 MB, the cap is 8 MB";
  const NEWER = DOC.replace("cut", "reduced") + "One more line the session added.\n";
  w.disk = NEWER; w.diskMtime = F21; w.mtimes[ABS] = F21;
  const asks = countOf(w, "fileComments", "status");
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  assert.equal(w.reloads, 2, "the poll asked the fetch on the mtime it saw"); assert.equal(countOf(w, "fileComments", "status"), asks + 1, "…and re-asked status");
  assert.ok(w.failReload, "the fetch is out");
  assert.equal(rowText(), FAILED_ROW, "the row stands until the status lands: nothing has answered it yet");
  const newest = status({ fileMtimeNs: F21, storeMtimeNs: S12, hunks: [shifted(h3, 4), shifted(h5, 4)],
    store: { ...NO_COMMENTS, suggestions: [SUGG[1]], comments: [passage] }, unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 1, watermark: null } });
  answer(w, newest); await flush(); await flush();
  assert.equal(w.reloads, 2, "the same mtime: the status asks no second fetch");
  assert.equal(rowText(), null, "no row off the standing pane: the fetch is the panel's own and the pane is the failure before it (before round 4: the failure row again, in the 404's words, the fetch still out)");
  assert.ok(aside.querySelector('.fc-load[data-slot="bytes"]'), "the wait's loader stands (before round 4: none)");
  assert.equal(w.body.querySelectorAll(".fileview-err").length, 1, "the pane stands in the body meanwhile");
  // refused for another reason: the row files at the paint that shows the new pane, in its words
  w.failReload!(OTHER); await flush(); await flush();
  assert.deepEqual(w.hookErrors, []);
  assert.equal(aside.querySelectorAll(".fc-load").length, 0, "the pane's paint ends the wait");
  assert.equal(rowText(), failedRow(OTHER), "the row in the new pane's words");
  t.mock.timers.tick(15000); await flush();
  assert.equal(aside.querySelectorAll('.fc-err[data-slot="bytes"]').length, 1, "the deadline was cleared at the paint: no second row");
  // the row's Reload lands this time
  act(aside.querySelector('.fc-err[data-slot="bytes"]')!, "fcreload")!.click(); await flush();
  assert.equal(w.reloads, 3);
  answer(w, newest); await flush(); await flush();
  assert.equal(rowText(), null, "no row while the click's fetch is out"); assert.ok(aside.querySelector('.fc-load[data-slot="bytes"]'), "the loader through the status");
  w.landReload!(); await flush(); await flush();
  assert.equal(w.viewError, null); assert.equal(w.viewMtime, F21);
  assert.equal(rowText(), null, "no row over the new text"); assert.equal(aside.querySelectorAll(".fc-load").length, 0, "the landing ends the wait");
  assert.equal(marksOf(w, "h5").length, 1, "the marks over the new text");
  assert.deepEqual(w.hookErrors, []);
});

test("Edit clicked over the pane (the button's gate reads the last landing's text and mtime, so it is offered): the editor's entry is a content paint of the earlier text, run by #latchCardState under paintPass's editing early return, and the row takes the text tail THERE, not at the exit; Cancel's repaint keeps it; a save under the editor moves the mtime, and the exit's repaint takes the row away", async (t: TestContext) => {
  const { w, aside, OVER_TEXT_ROW, rowText } = await failureRow(t);
  w.edit(true); await flush();
  assert.equal(w.ctx.editing(), true); assert.equal(w.viewError, null, "the editor took the body: no pane");
  assert.deepEqual(w.hookErrors, [], "the editing branch threw nothing");
  assert.equal(rowText(), OVER_TEXT_ROW, "the row says the view shows the earlier text (before: 'the view shows that failure in place of the file' beside an editor over the text, until the exit's repaint)");
  assert.ok(act(aside.querySelector('.fc-err[data-slot="bytes"]')!, "fcreload"), "Reload stays");
  // Cancel: the exit's repaint of the earlier text, the mtime unchanged
  w.edit(false); await flush();
  assert.equal(w.ctx.editing(), false); assert.equal(w.body.querySelectorAll(".fv-cl").length, 10, "the earlier text is back");
  assert.equal(rowText(), OVER_TEXT_ROW, "the exit's repaint changes nothing about the row");
  assert.equal(marksOf(w).length, 0, "no change is marked over the earlier text");
  // Edit again, then a save: the reply moves the view's mtime (file-view.ts's saved hook) and the exit repaints; the file was written and read
  w.edit(true); await flush();
  assert.equal(rowText(), OVER_TEXT_ROW);
  w.viewMtime = F21;
  w.edit(false); await flush();
  assert.equal(rowText(), null, "the row is answered by the mtime moving under a paint: the reload it spoke of is moot");
  assert.equal(aside.querySelectorAll(".fc-load").length, 0);
  assert.deepEqual(w.hookErrors, []);
});

// ── every status brings the view's bytes to the text it describes (the review: stale bytes after a store-moved) ──

test("an accept whose reply carries a file mtime the view does not show re-fetches the bytes: the session wrote the file between the poll's last look and the click, and the reply re-baselined the poll", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ hunks: [h1, h3, h5] }));
  act(card(aside, "chg:h1")!, "fcaccept", "h1")!.click(); await flush();
  const m = lastOf(w, "fileComments", "accept");
  // a plain write landed under the sidecar fence (the sidecar did not move, the file did): the host reads the new file
  w.disk = DOC.replace("Risks remain", "Risks still remain"); w.diskMtime = F11;
  const after = status({ fileMtimeNs: F11, storeMtimeNs: S12, hunks: [h3, shifted(h5, 6)],
    store: { ...NO_COMMENTS, suggestions: [SUGG[1]], comments: [passage] }, unsent: { comments: [passage.id], replies: [], accepted: 1, rejected: 0, watermark: null } });
  answer(w, after, m, { accepted: ["h1"] }); await flush(); await flush();
  assert.equal(w.reloads, 1, "the reply's file mtime is not the view's: the bytes are re-fetched (before, only a reject's reply did this)");
  assert.equal(w.viewMtime, F11);
  assert.ok(marksOf(w, "h5").some((x) => x.textContent === " again"), "the marks are painted over the NEW text");
  assert.equal(aside.querySelectorAll(".fc-load").length, 0, "the bytes landed: no wait");
  // the poll, re-baselined to F11 by the reply, sees no move and asks nothing more
  const asks = countOf(w, "fileComments", "status");
  await flush();
  assert.equal(countOf(w, "fileComments", "status"), asks);
});

test("Accept refused store-moved by a track-edit that ALSO rewrote the file: the fresh status re-fetches the bytes (the refusal named only the sidecar), and the retry's reply, carrying the same mtime, asks no second fetch", async (t: TestContext) => {
  const w = world({ deferReload: true }); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ hunks: [h1, h3, h5] }));
  act(card(aside, "chg:h1")!, "fcaccept", "h1")!.click(); await flush();
  const first = lastOf(w, "fileComments", "accept");
  // the session's track-edit on ANOTHER passage: the sidecar and the file both moved; h1 reads as it did
  w.disk = DOC.replace("Next steps", "Next step"); w.diskMtime = F11;
  refuse(w, first, "store-moved", MOVED_STORE); await flush();
  const fresh = status({ fileMtimeNs: F11, storeMtimeNs: S9, hunks: [h1, h3, { ...h5, curFrom: h5.curFrom - 1, curTo: h5.curTo - 1 }],
    store: { v: 3, path: "docs/report.md", suggestions: SUGG, comments: [passage] } });
  answer(w, fresh); await flush(); await flush();
  assert.equal(w.reloads, 1, "the file moved too: its bytes are asked for on the fresh status's mtime, not on the refusal's code");
  assert.ok(w.landReload, "…and are still in flight");
  assert.ok(aside.querySelector('.fc-load[data-slot="bytes"]'), "the wait wears the loader");
  assert.equal(marksOf(w).length, 0, "nothing is painted over the old bytes meanwhile");
  const retry = lastOf(w, "fileComments", "accept");
  assert.notEqual(retry.reqId, first.reqId, "h1 reads as the card showed it: the one retry goes");
  assert.equal(retry.fence.storeMtimeNs, S9);
  answer(w, status({ fileMtimeNs: F11, storeMtimeNs: S12, hunks: [h3, { ...h5, curFrom: h5.curFrom - 1, curTo: h5.curTo - 1 }],
    store: { ...NO_COMMENTS, suggestions: [SUGG[1]], comments: [passage] }, unsent: { comments: [passage.id], replies: [], accepted: 1, rejected: 0, watermark: null } }),
    retry, { accepted: ["h1"] }); await flush(); await flush();
  assert.equal(w.reloads, 1, "the same file mtime again: one fetch, not two (the retry path used to issue two un-sequenced ones)");
  w.landReload!(); await flush();
  assert.equal(w.viewMtime, F11);
  assert.equal(aside.querySelectorAll(".fc-load").length, 0, "the wait is over");
  assert.equal(card(aside, "chg:h1"), null, "decided");
  assert.ok(marksOf(w, "h5").some((x) => x.textContent === " again"), "the remaining change is marked over the new text");
});

test("the poll's file move: the HEAD asks the fetch on the mtime it saw, and the status that follows, knowing the same mtime, asks no second one", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setInterval"] });
  const w = world({ deferReload: true }); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ hunks: [h1, h3, h5] }));
  w.disk = DOC.replace("Risks remain", "Risks still remain"); w.diskMtime = F11; w.mtimes[ABS] = F11;
  const asks = countOf(w, "fileComments", "status");
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  assert.equal(countOf(w, "fileComments", "status"), asks + 1, "the poll re-read status");
  assert.equal(w.reloads, 1, "the poll asked for the bytes");
  answer(w, status({ fileMtimeNs: F11, storeMtimeNs: S2, hunks: [h1, h3, shifted(h5, 6)] })); await flush(); await flush();
  assert.equal(w.reloads, 1, "the status knows the same mtime: no second fetch");
  assert.ok(aside.querySelector('.fc-load[data-slot="bytes"]'), "the status's text is not on screen yet: the wait wears the loader");
  w.landReload!(); await flush();
  assert.equal(aside.querySelectorAll(".fc-load").length, 0);
  assert.ok(marksOf(w, "h5").some((x) => x.textContent === " again"));
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

// ── the card-state rule (file-comments.ts, #cardState's doc) ──────────────────────────────────────────────────────────────────
// Its writer and the functions that call it, and the callers of the passes that refile (paintAll, and repaintPresel with the
// repaintPreselPass it runs), read by the compiler's own parser (writer-census.ts cardStateCensus); its roads, each row of the doc's
// table run over a seam the rows drive and the change cards read after every step; and, from each of five starts, every ordering of
// three of the steps that act on it.

const PANEL_SRC = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "file-comments.ts"), "utf8");

/** The writer's callers, each with the event it names (file-comments.ts, #cardState's doc). */
const RULE_CALLERS = ["onRendered's callback paint", "constructor paint", "onSaved's callback paint", "paintAll refile", "repaintPreselPass refile", "applyStatus status", "toggleInline gesture", "setFilter gesture", "settingsFlipped gesture"];
/** The names whose callers the census counts: the five gestures, each of which reaches #latchCardState("gesture"), and the passes
 *  that refile (repaintPreselPass holds the composer's repaint's refile). */
const CARD_CALLEES = ["settingsFlipped", "toggleInline", "setFilter", "showAbout", "goToArrival", "paintAll", "repaintPresel", "repaintPreselPass"];

test("the card-state rule's writer: the one assignment to the private #cardState is #latchCardState's, #latchCardState's calls are the callers #cardState's doc names with their events, #replaced, the count of what the viewer put up other than a content paint, is written by the seam's onReplaced and a pane's onRendered alone, the callers of the five gestures and of paintAll, repaintPresel and repaintPreselPass, whose refile writes a card's filing, are the ones named here, and file-comments.ts, read by the compiler's own parser, holds no other mention of any of those eight names and none of the doors to code in a string the census lists (eval and Function by name; the identifier constructor; a string literal spelled eval, Function, constructor, setTimeout or setInterval; a timer given anything but a function written in place)", () => {
  const c = cardStateCensus(PANEL_SRC, CARD_CALLEES);
  assert.equal(c.decls, 1, "one #cardState, the Panel's private field whose doc states the rule");
  assert.deepEqual(c.writes.map((x) => x.fn + ": " + x.text), ["#latchCardState: this.#cardState = Object.freeze({ ...next, painted: Object.freeze(Array.from(this.paintedChanges)) })"],
    "the writer's one assignment is the only assignment to #cardState in the file (#cardState's doc)");
  assert.deepEqual(c.refs, [], "the writer is only ever called, never handed on");
  assert.deepEqual(c.evals, [], "none of the doors to code in a string the census lists is in the file (eval and Function by name; the identifier constructor; a string literal spelled eval, Function, constructor, setTimeout or setInterval; a timer given anything but a function written in place): a direct eval inside the class could write #cardState where no syntax shows it, and any of them can run code that calls a pass on a panel handed to it, so the census refuses them all; it reads none of the other ways a page runs code from a string (writer-census.ts, cardStateCensus's doc)");
  assert.deepEqual(c.calls.map((x) => x.fn + " " + x.at).sort(), [...RULE_CALLERS].sort(),
    "the writer's callers, each with its event (#cardState's doc): " + JSON.stringify(c.calls.map((x) => x.fn + " " + x.at + " at " + x.line)));
  assert.deepEqual(c.counts.map((x) => x.fn + ": " + x.text), ["onRendered's callback: this.#replaced++", "onReplaced's callback: this.#replaced++"],
    "#replaced counts the seam's onReplaced and a pane's onRendered, and nothing else writes it (#cardState's doc, event 1)");
  assert.deepEqual(c.callers.settingsFlipped, ["onExternalSettingsChange's callback", "onExternalSettingsChange's callback"], "a flip in another viewer reaches the writer through the two settings listeners alone");
  assert.deepEqual([...c.callers.toggleInline].sort(), ["fcinline's callback"], "Show changes inline from its button alone, one call");
  assert.deepEqual([...c.callers.setFilter].sort(), ["addEventListener's callback", "fcfilter's callback", "goToArrival", "showAbout"], "the filter from its buttons, their arrow keys, and two clicks that bring a hidden card into view, one call each");
  assert.deepEqual([c.callers.showAbout, c.callers.goToArrival], [["fcaboutfirst's callback"], ["fcarrivals's callback"]], "those two clicks: a change card's comments tag and the arrivals line");
  // A refile through a pass writes a card's filing (#cardState's doc, event 1), and repaintPreselPass holds the composer's repaint's
  // refile, so a new caller of paintAll, repaintPresel or repaintPreselPass is a new writer, as a new caller of any of the five
  // gestures above is (each reaches #latchCardState("gesture")). The census counts every call whose callee is the name or a property
  // access ending in it (this.paintAll()): a new one reds these lists until it is added deliberately, with its event named. Every
  // other mention of the name in this file's code (a bound reference or one handed on, an alias, a destructured name, a call through
  // parentheses or .call, a string literal spelled as the name, a decorator on its declaration or its parameters), the name's own
  // declarations aside, is listed apart and held empty below for all eight names, and the doors to code in a string the census
  // lists (eval and Function by name; the identifier constructor; a string literal spelled eval, Function, constructor, setTimeout
  // or setInterval; a timer given anything but a function written in place) are held empty above. No name computed at run time
  // (this[k]), no code in another module and none of the other ways a page runs code from a string (a module imported from a data
  // address, handler attributes or markup, an element whose text runs as code) is read.
  assert.deepEqual([...c.callers.paintAll].sort(), ["#latchCardState", "applyStatus", "loadColors", "onRendered's callback"],
    "paintAll's four callers: a pane's onRendered, applyStatus's status that does not differ, the colour fetch's repaint (loadColors) and a gesture over anything else (#latchCardState)");
  assert.deepEqual([...c.callers.repaintPresel].sort(), ["closeComposer", "onRegionDrawn", "onRegionDrawn", "restoreRefused", "settleAway", "startChangeComment", "startComment", "startFileComment", "startImageComment", "startReplace", "startReply", "switchToRaw", "switchToRaw"],
    "repaintPresel's thirteen calls, the composer's target painted again: a composer opened (a passage's, a region's, the file's, a reply's, a change's, a replace), closed, restored after a refusal, settled away, and the switch to Raw and a region drawn twice each");
  assert.deepEqual(c.callers.repaintPreselPass, ["repaintPresel"], "repaintPreselPass, which holds the composer's repaint's refile, is run by repaintPresel alone");
  assert.deepEqual(c.calleeRefs, Object.fromEntries(CARD_CALLEES.map((n) => [n, []])),
    "no mention of any of the eight names in the code but the calls counted above and their own declarations (writer-census.ts, cardStateCensus's doc: calleeRefs)");
});

test("the card-state census counts every assignment to the private #cardState (an assignment operator's, a compound one's, a destructuring target's, a for-of head's, an increment's) and to #replaced, and every call of the private #latchCardState; it lists a mention of the writer that is not a call and every identifier spelled eval, a direct eval's or any other; and it counts nothing a public name reaches, which the language keeps off a private field, as it keeps an indirect eval off one (executed below)", () => {
  const src = "class P {\n  #cardState: S = x;\n  #replaced = 0;\n  #latchCardState(at: string): void { this.#cardState = y; }\n  render(): void { this.#cardState = z; }\n  a(): void { ({ q: this.#cardState } = o); }\n"
    + "  b(): void { for (this.#cardState of zs) { /* each */ } }\n  c(): void { this.#cardState ??= w; }\n  d(): void { (this as any).#cardState++; }\n"
    + "  e(): void { Object.assign(this, { cardState: z }); Reflect.set(this, \"cardState\", z); Object.defineProperty(this, \"cardState\", { value: z }); (this as any)[k] = z; (this as any)[\"#cardState\"] = z; }\n"
    + "  f(): void { const g = this.#latchCardState; }\n  h(): void { (this as any)[\"#latchCardState\"](\"paint\"); this.#replaced += 1; }\n  constructor() { ctx.onRendered(() => { this.#latchCardState(\"paint\"); }); }\n"
    + "  i(): void { eval(\"this.#cardState = z\"); }\n  j(): void { \\u0065val(\"this.#cardState = z\"); }\n  k(): void { (0, globalThis.eval)(\"1\"); }\n}\n";
  const c = cardStateCensus(src);
  assert.equal(c.decls, 1);
  assert.deepEqual(c.writes.map((x) => x.fn), ["#latchCardState", "render", "a", "b", "c", "d"], "each assignment to #cardState is found and named by its function; e's public names are none");
  assert.deepEqual(c.refs.map((x) => x.fn), ["f"], "the writer handed on is reported; h's string key names a public property, no mention of the writer");
  assert.deepEqual(c.calls.map((x) => x.fn + " " + x.at), ["onRendered's callback paint"]);
  assert.deepEqual(c.counts.map((x) => x.fn), ["h"], "an assignment to #replaced");
  assert.deepEqual((c.evals ?? []).map((x) => x.fn + ": " + x.text), ["i: eval(\"this.#cardState = z\")", "j: \\u0065val(\"this.#cardState = z\")", "k: globalThis.eval"], "every identifier spelled eval is listed by its function, a unicode escape's and an indirect one's included (fail closed)");
  // the language's side of it: no public name reaches a private field or method, so e's and h's shapes write nothing the class reads
  class Probe {
    #cardState: Readonly<{ n: number }> = Object.freeze({ n: 0 });
    #latchCardState(): void { this.#cardState = Object.freeze({ n: 1 }); }
    read(): number { return this.#cardState.n; }
    latch(): void { this.#latchCardState(); }
  }
  const p = new Probe();
  const any = p as any;
  Object.assign(p, { cardState: { n: 9 } }); Reflect.set(p, "cardState", { n: 9 }); Object.defineProperty(p, "cardState", { value: { n: 9 } }); any["#cardState"] = { n: 9 };
  assert.equal(p.read(), 0, "Object.assign, Reflect.set, defineProperty and a computed key over the instance leave the private field as it was");
  assert.equal(any["#latchCardState"], undefined, "a computed name reaches no private method, so a computed call of the writer cannot be written");
  class Through { write(o: { n: number }): void { o.n = 1; } }
  assert.throws(() => new Through().write(Object.freeze({ n: 0 })), TypeError, "a write through the frozen state throws (a class body is strict code)");
  p.latch();
  assert.equal(p.read(), 1, "the private writer writes it");
  // a direct eval inside the class is the road besides these (why the census lists the name); an indirect one runs as global code, where
  // the private name does not parse. Compiled by the vm module, so this test file itself holds no eval.
  const run = (code: string): unknown => vm.runInNewContext("class Q { #x = 0; " + code + " read() { return this.#x; } } const q = new Q(); q.go(); q.read()");
  assert.equal(run("go() { eval('this.#x = 5'); }"), 5, "a direct eval inside the class writes its private field");
  assert.equal(run("go() { \\u0065val('this.#x = 6'); }"), 6, "so does one whose name is spelled with a unicode escape");
  assert.throws(() => run("go() { (0, eval)('this.#x = 7'); }"), (e: unknown) => e !== null && typeof e === "object" && (e as { name?: string }).name === "SyntaxError", "an indirect eval cannot name the private field");
});

test("the card-state census lists, by name, every mention of a callee in the code other than a call it counts (a bound reference or one handed on, an alias, a destructured name, a call through parentheses or .call, a string literal spelled as the name, a decorator on its declaration or its parameters, the last pinned in the next case), the name's own declarations aside, and no name computed at run time; so a caller that reaches paintAll through a bound reference, added to file-comments.ts, leaves the counted callers as they were and reds the hold on the eight names' other mentions", () => {
  const src = "class P {\n  paintAll(): void { /* the pass */ }\n  a(): void { this.paintAll(); }\n  b(): void { const f = this.paintAll.bind(this); f(); }\n"
    + "  c(): void { const g = this.paintAll; g(); }\n  d(): void { const { paintAll } = this; paintAll(); }\n  e(): void { (this.paintAll)(); this.paintAll.call(this); }\n"
    + "  f(): void { (this as any)[\"paintAll\"](); Reflect.get(this, \"paintAll\"); }\n  g(k: string): void { (this as any)[k](); }\n}\n";
  const c = cardStateCensus(src, ["paintAll"]);
  assert.deepEqual(c.callers.paintAll, ["a", "d"], "the calls counted: this.paintAll() and the destructured name's call");
  assert.deepEqual(c.calleeRefs.paintAll.map((x) => x.fn + ": " + x.text),
    ["b: this.paintAll.bind", "c: g = this.paintAll", "d: paintAll", "e: (this.paintAll)", "e: this.paintAll.call", "f: (this as any)[\"paintAll\"]", "f: Reflect.get(this, \"paintAll\")"],
    "each other mention, shown with what holds it; the declaration and g's computed key are not listed");
  // the real file with one caller added through a bound reference, in hideFloat under a guard that never runs
  const at = "  hideFloat(): void { ";
  assert.equal(PANEL_SRC.split(at).length, 2, "one hideFloat to add the caller to");
  const none = Object.fromEntries(CARD_CALLEES.map((n) => [n, []]));
  const real = cardStateCensus(PANEL_SRC, CARD_CALLEES);
  const added = cardStateCensus(PANEL_SRC.replace(at, at + "if (false) { const f = this.paintAll.bind(this); f(); } "), CARD_CALLEES);
  assert.deepEqual(added.callers, real.callers, "the counted callers do not see it");
  assert.deepEqual(real.calleeRefs, none, "the file as it is: nothing listed");
  assert.deepEqual(added.calleeRefs.paintAll.map((x) => x.fn + ": " + x.text), ["hideFloat: this.paintAll.bind"], "the bound reference is listed");
  assert.throws(() => assert.deepEqual(added.calleeRefs, none), assert.AssertionError, "so the rule's census, which holds that list empty, reds on it");
});

test("the card-state census lists these doors to code in a string, whose code no census reads: eval and Function by name; the identifier constructor (a function's constructor property); a string literal spelled eval, Function, constructor, setTimeout or setInterval; and a timer given anything but a function written in place, one handed on or given another name included; and it lists a decorator on a callee's declaration or its parameters, which is handed the method; a timer given a function written in place, a timer's name in a type and a decorator on another member are not listed; so a caller that reaches paintAll through the Function constructor, a timer given a string or a decorator on its declaration, added to file-comments.ts, leaves the counted callers as they were and reds the hold on the doors or, for the decorator, the hold on the eight names' other mentions", () => {
  const src = "class P {\n  @wrap paintAll(@mark n = 0): void { /* the pass */ }\n  @other q(): void { /* another member */ }\n"
    + "  a(): void { new Function(\"p\", \"p.paintAll()\")(this); Function(\"return 1\"); }\n  b(): void { (function () { return 0; }).constructor(\"p\", \"p.paintAll()\")(this); }\n"
    + "  c(): void { (globalThis as any)[\"eval\"](\"1\"); void (window as any)[\"Function\"]; }\n"
    + "  d(s: string): void { setTimeout(\"x.paintAll()\"); setInterval(s, 5); window.setTimeout(this.tick, 1); const t = setTimeout; setTimeout.call(window, s); }\n"
    + "  e(): void { setTimeout(() => this.paintAll(), 0); window.setInterval(function () { return 0; }, 5); const h: ReturnType<typeof setTimeout> | null = null; void h; }\n}\n";
  const c = cardStateCensus(src, ["paintAll"]);
  assert.deepEqual(c.evals.map((x) => x.fn + ": " + x.text),
    ["a: new Function(\"p\", \"p.paintAll()\")", "a: Function(\"return 1\")", "b: (function () { return 0; }).constructor", "c: (globalThis as any)[\"eval\"]", "c: (window as any)[\"Function\"]",
      "d: setTimeout(\"x.paintAll()\")", "d: setInterval(s, 5)", "d: window.setTimeout", "d: t = setTimeout", "d: setTimeout.call"],
    "each door, by its function, shown with what holds it; e's timers, given a function written in place or named in a type, are not listed");
  assert.deepEqual(c.calleeRefs.paintAll.map((x) => x.fn + ": " + x.text), ["paintAll: @wrap", "paintAll: @mark"], "the decorators on paintAll's declaration and on its parameter; q's is not listed, and no string's code is read");
  assert.deepEqual(c.callers.paintAll, ["setTimeout's callback"], "the one call counted: the arrow function a timer was given");
  // the real file with a caller added through each door, in hideFloat under a guard that never runs, and with a decorator on paintAll
  const at = "  hideFloat(): void { ", decl = "  paintAll(): void {";
  assert.deepEqual([PANEL_SRC.split(at).length, PANEL_SRC.split(decl).length], [2, 2], "one hideFloat to add the caller to, and one paintAll declaration");
  const none = Object.fromEntries(CARD_CALLEES.map((n) => [n, []]));
  const real = cardStateCensus(PANEL_SRC, CARD_CALLEES);
  assert.deepEqual([real.evals, real.calleeRefs], [[], none], "the file as it is: nothing listed");
  const viaFunction = cardStateCensus(PANEL_SRC.replace(at, at + "if (false) new Function(\"p\", \"p.paintAll()\")(this); "), CARD_CALLEES);
  const viaTimer = cardStateCensus(PANEL_SRC.replace(at, at + "if (false) setTimeout(\"globalThis.panel.paintAll()\", 0); "), CARD_CALLEES);
  const decorated = cardStateCensus(PANEL_SRC.replace(decl, "  @wrap paintAll(): void {"), CARD_CALLEES);
  for (const [what, x] of [["the Function constructor", viaFunction], ["a timer given a string", viaTimer], ["a decorator on paintAll's declaration", decorated]] as const)
    assert.deepEqual(x.callers, real.callers, "the counted callers do not see a caller through " + what);
  assert.deepEqual(viaFunction.evals.map((x) => x.fn + ": " + x.text), ["hideFloat: new Function(\"p\", \"p.paintAll()\")"], "the Function constructor is listed");
  assert.deepEqual(viaTimer.evals.map((x) => x.fn + ": " + x.text), ["hideFloat: setTimeout(\"globalThis.panel.paintAll()\", 0)"], "the timer given a string is listed");
  assert.deepEqual(decorated.calleeRefs.paintAll.map((x) => x.fn + ": " + x.text), ["paintAll: @wrap"], "the decorator is listed");
  assert.throws(() => assert.deepEqual(viaFunction.evals, []), assert.AssertionError, "so the rule's census, which holds the doors empty, reds on the Function constructor");
  assert.throws(() => assert.deepEqual(viaTimer.evals, []), assert.AssertionError, "and on the timer");
  assert.throws(() => assert.deepEqual(decorated.calleeRefs, none), assert.AssertionError, "and the hold on the eight names' other mentions reds on the decorator");
});

test("the card-state census lists a door's string literal written as a template with no substitution as it lists a quoted one, a timer's instantiation expression (setTimeout<[string]>, handed on under another name), which is a value and not a type, and a string literal spelled setTimeout, setInterval or constructor; a timer given a function written in place inside parentheses is not listed, as one given it bare is not", () => {
  const src = "class P {\n  paintAll(): void { /* the pass */ }\n  a(): void { (globalThis as any)[`eval`](\"1\"); void (window as any)[`Function`]; }\n"
    + "  b(): void { const t = setTimeout<[string]>; t(\"globalThis.panel.paintAll()\"); }\n"
    + "  c(): void { setTimeout((() => this.paintAll()), 5); window.setInterval(((function () { return 0; })), 5); }\n"
    + "  d(): void { (window as any)[\"setTimeout\"](\"globalThis.panel.paintAll()\", 0); (window as any)[\"setInterval\"](\"0\", 5); (function () { return 0; } as any)[\"constructor\"](\"p\", \"p.paintAll()\")(this); }\n}\n";
  const c = cardStateCensus(src, ["paintAll"]);
  const listed = (fn: string): string[] => c.evals.filter((x) => x.fn === fn).map((x) => x.text);
  assert.deepEqual(listed("a"), ["(globalThis as any)[`eval`]", "(window as any)[`Function`]"], "a string literal written as a template with no substitution is listed as a quoted one is");
  assert.deepEqual(listed("b"), ["setTimeout<[string]>"], "a timer's instantiation expression is a value, not a type: listed, since the name it is given may be called with a string");
  assert.deepEqual(listed("c"), [], "a timer given a function written in place inside parentheses is given one written in place: not listed");
  assert.deepEqual(listed("d"), ["(window as any)[\"setTimeout\"]", "(window as any)[\"setInterval\"]", "(function () { return 0; } as any)[\"constructor\"]"],
    "a string literal spelled setTimeout, setInterval or constructor is listed, as one spelled eval or Function is");
  assert.deepEqual([...new Set(c.evals.map((x) => x.fn))], ["a", "b", "d"], "and nothing else is listed");
});

type RoadKind = "text" | "svg" | "raster";
type CardRead = { tags: string[]; buttons: string[]; reveal: string | null; link: boolean };
const DOC11 = DOC.replace("cut", "reduced");
/** The status of the bytes at F1: a substitution, a deletion and an insertion pending (h1, h3, h5). */
const statusF1 = (over: Partial<Status> = {}): Status => status({ hunks: [h1, h3, h5], ...over });
/** The status of newer bytes (F11): h1 rejected, so the deletion and the insertion pending over them. */
const statusF11 = (): Status => status({ fileMtimeNs: F11, storeMtimeNs: S12, hunks: [shifted(h3, 4), shifted(h5, 4)],
  store: { ...NO_COMMENTS, suggestions: [SUGG[1]], comments: [passage] }, unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 1, watermark: null } });
const h7 = H("h7", "sub", at("Report"), at("Report") + 6, "Summary", "Report", T0 - 95000);
const h9 = H("h9", "sub", at("fallback"), at("fallback") + 8, "backup", "fallback", T0 - 60000);
/** The status of the bytes at F1 with a change in each of DOC's five paragraphs (h7, h1, h3, h9, h5): more paragraph groups than the
 *  change list shows before its fold (GROUP_LIMIT, three), so the list folds the last two over the text and folds nothing over a
 *  picture, which has no paragraphs. */
const statusMany = (over: Partial<Status> = {}): Status => status({ hunks: [h7, h1, h3, h9, h5], ...over });
/** Every change card as the person sees it, by key; null while the panel is closed. */
function changeCards(w: World): Record<string, CardRead> | null {
  const aside = w.main.querySelector(".fileview-aside");
  if (!aside) return null;
  const out: Record<string, CardRead> = {};
  for (const c of aside.querySelectorAll(".fc-card.fc-change")) {
    const rv = act(c, "fcreveal");
    out[c.getAttribute("data-id")!] = { tags: tags(c), buttons: texts(c.querySelectorAll(".fc-actions button")), reveal: rv ? rv.title : null, link: isLink(c) };
  }
  return out;
}
/** The change list as the person sees it: the paragraph titles, the change cards in the order listed, and the fold row's words
 *  (null with no fold row). */
function changeList(w: World): { titles: string[]; cards: string[]; fold: string | null } {
  const aside = w.main.querySelector(".fileview-aside")!;
  const more = act(aside, "fcmore");
  return { titles: texts(aside.querySelectorAll(".fc-group")), cards: Array.from(aside.querySelectorAll(".fc-card.fc-change")).map((c) => c.getAttribute("data-id")!), fold: more ? more.textContent : null };
}

/** The viewer as the rule's roads drive it, over the review world: a text file, an svg (its picture, mode() "media", and its Source
 *  view, a text view of its XML, which here is DOC) or a raster picture. Each step does what the real seam does at it (file-view.ts):
 *  a content paint puts the rows up and fires onRendered with error() null, or fires it at the load of a picture put up still loading,
 *  or puts a picture up (onReplaced) and fires it at once; a pane fires it with error() its words, text() and mtimeNs() as they were;
 *  a landing on the picture view puts the landed bytes' picture up still loading (onReplaced), an svg's then telling onLanded and a
 *  raster's nothing, and a landing under the Source view, or while a press to it waits for its decode, puts nothing up (an svg's tells
 *  onLanded); a landing of another type puts its picture up still loading and tells nothing more; a text file's landing is its paint; a press of the Source toggle to the picture puts up a picture still loading
 *  (onReplaced, mode() "media", error() null, no onRendered), and a press to the Source view waits for its decode (the picture stays,
 *  mode() still "media") until the decode's paint; an svg picture's failure puts the romp loader up behind the re-ask (onReplaced, no
 *  onRendered). A status reaches the panel through its poll (the HEAD sees the mtimes move), through its open's re-read, or as the
 *  answer to an ask already out (the mount's first, onSaved's re-read after a save through saveFile). The
 *  editor's entry asks the panel's begin() and then takes the body with a paint (enterEdit), text() answering its buffer once it is
 *  up; its exit repaints the bytes in hand; a save through the panel lands as the viewer's saved() does (save's doc), and one
 *  through saveFile as its ack does (savedFile's doc). */
class RoadSeam {
  show: "none" | "text" | "picture" | "loading" | "loader" | "pane" = "text";
  source = false; decoding = false;
  shownText: string | null = DOC;                        // what a text view last painted (text() keeps it over a pane, as the viewer's `text` does)
  hand = { text: DOC, mt: F1 };                          // the bytes in hand, the last landing's
  out: { text: string; mt: string } | null = null;      // a fetch asked and not answered yet
  s: Status = statusF1();                                // the status last answered
  button: El | null = null;
  tracked: TrackedEdit | null = null;                    // the panel's half of editing, as it hands it to the seam (setTrackedEdit)
  savedHooks: Array<(info: { mtimeNs: string; logged: boolean }) => void> = [];   // the seam's onSaved
  buffer: string | null = null;                          // the editor's buffer while it is up (text() answers it then, as the viewer's does)
  constructor(public t: TestContext, public w: World, public kind: RoadKind) {
    const img = (): El => { const i = new El("img"); i.className = "fileview-img"; return i; };
    let pic = img();
    this.pictureUp = (): void => { pic = img(); w.body.replaceChildren(pic); this.swapped(); };
    w.ctx.mode = () => (kind === "text" || (kind === "svg" && this.source && !this.decoding) ? "raw" : "media");
    w.ctx.text = () => (w.editing && this.buffer !== null ? this.buffer : kind === "text" || (kind === "svg" && this.source && !this.decoding) ? this.shownText : null);
    w.ctx.setTrackedEdit = (te) => { this.tracked = te; };
    w.ctx.onSaved = (cb) => { this.savedHooks.push(cb); };
    w.ctx.mediaElement = () => (w.ctx.mode() === "media" && (this.show === "picture" || this.show === "loading") ? pic as unknown as HTMLElement : null);
    w.ctx.reload = () => { w.reloads++; this.out = { text: w.disk, mt: w.diskMtime }; };
    if (kind !== "text") { this.shownText = kind === "svg" ? DOC : null; this.show = "picture"; this.pictureUp(); }
  }
  pictureUp: () => void;
  private fire(): void { for (const cb of this.w.hooks.rendered) { try { cb(); } catch (e) { this.w.hookErrors.push(e); } } }
  private swapped(): void { for (const cb of this.w.hooks.replaced) cb(); }
  /** Before the view's first paint: the body empty and the view's mtime empty, as the viewer mounts its actions. */
  unpainted(): void { this.show = "none"; this.shownText = null; this.w.body.replaceChildren(); this.w.viewMtime = ""; }
  /** The Source view up, painted (an svg's). */
  sourceUp(): void { this.source = true; this.decoding = false; this.shownText = this.hand.text; this.show = "text"; const code = new El("code"); code.className = "hljs"; rows(code, this.hand.text); this.w.body.replaceChildren(code); }
  /** A content paint of the bytes in hand: the rows, the load of the picture put up, or a picture put up and shown at once. */
  async paint(): Promise<void> {
    const w = this.w;
    w.viewError = null;
    if (this.kind === "svg" && this.decoding) { this.source = true; this.decoding = false; }
    if (this.kind === "text" || (this.kind === "svg" && this.source)) {
      this.shownText = this.hand.text; this.show = "text";
      const code = new El("code"); code.className = "hljs"; rows(code, this.hand.text); w.body.replaceChildren(code);
    } else if (this.show === "loading") this.show = "picture";   // the picture put up loads: its paint, the body unchanged
    else { this.show = "picture"; this.pictureUp(); }
    this.fire(); await flush(); await flush();
  }
  /** A failure pane in place of the view. */
  async pane(words = "no such file: " + ABS): Promise<void> {
    const why = new El("div"); why.className = "fileview-err"; why.appendChild(new Txt(words));
    this.w.body.replaceChildren(why); this.w.viewError = words; this.show = "pane";
    this.fire(); await flush(); await flush();
  }
  /** The fetch asked answers: its bytes in hand and mtimeNs() theirs. A text file's landing is its paint; on the picture view the
   *  landed bytes' picture goes up still loading, an svg's telling onLanded then and a raster's nothing; under the Source view, or
   *  while a press to it waits for its decode, the body stays and an svg's tells onLanded. With no fetch out, the bytes on disk (a
   *  reload of the seam's own, the re-ask's answer, the way back). */
  async land(): Promise<void> {
    this.hand = this.out || { text: this.w.disk, mt: this.w.diskMtime }; this.out = null;
    this.w.viewMtime = this.hand.mt;
    if (this.kind === "text") { await this.paint(); return; }
    if (!(this.kind === "svg" && (this.source || this.decoding))) { this.w.viewError = null; this.show = "loading"; this.pictureUp(); }
    if (this.kind === "svg") for (const cb of this.w.hooks.landed) cb();
    await flush(); await flush();
  }
  /** A landing of another type, a png where the svg was: its picture goes up still loading (onReplaced), whatever view was up, the
   *  Source view gone with the XML, and it tells no onLanded, as the viewer does for a raster picture. With no fetch out, the
   *  bytes on disk. */
  async landOther(): Promise<void> {
    this.hand = this.out || { text: this.w.disk, mt: this.w.diskMtime }; this.out = null;
    this.w.viewMtime = this.hand.mt; this.w.viewError = null;
    this.source = false; this.decoding = false; this.show = "loading"; this.pictureUp();
    await flush(); await flush();
  }
  /** An svg picture's failure: its address asked again behind the romp loader, with no onRendered (only over a picture). */
  async loader(): Promise<void> {
    if (this.kind === "svg" && !this.source && (this.show === "picture" || this.show === "loading")) {
      const load = new El("div"); load.className = "fileview-load"; this.w.body.replaceChildren(load); this.swapped(); this.show = "loader";
    }
    await flush(); await flush();
  }
  /** A press of the Source toggle (an svg's): to the picture, which is still loading; or to the Source view, waiting for its decode. */
  async press(): Promise<void> {
    if (this.kind !== "svg") return;
    if (this.source && !this.decoding) { this.source = false; this.show = "loading"; this.pictureUp(); this.w.viewError = null; }
    else if (!this.source) this.decoding = true;
    await flush(); await flush();
  }
  /** A status that differs from the one showing, through the panel's poll (its HEAD sees the file or the sidecar move). */
  async status(next: Status): Promise<void> {
    const w = this.w;
    if (next.fileMtimeNs !== this.s.fileMtimeNs) { w.disk = next.fileMtimeNs === F11 ? DOC11 : DOC; w.diskMtime = next.fileMtimeNs; }
    w.mtimes[ABS] = next.fileMtimeNs;
    if (next.storePath && next.storeMtimeNs !== null) w.mtimes[next.storePath] = next.storeMtimeNs;
    if (next.root && next.configMtimeNs !== null) w.mtimes[next.root + "/.trackchanges/config.json"] = next.configMtimeNs;
    const asks = countOf(w, "fileComments", "status");
    this.t.mock.timers.tick(2500); await flush(); await flush(); await flush();
    assert.equal(countOf(w, "fileComments", "status"), asks + 1, "the poll asked the status");
    answer(w, next); this.s = next; await flush(); await flush();
  }
  /** The panel's button: open it (its re-read of the status is asked, and answered by `reread`). */
  async open(): Promise<void> { this.button!.click(); await flush(); }
  /** The open's re-read answered with the status already showing: the same reading. */
  async reread(): Promise<void> { answer(this.w, this.s); await flush(); await flush(); }
  /** The panel's button: close it. */
  async close(): Promise<void> { this.button!.click(); await flush(); }
  /** A change card's head clicked: a render with nothing new. */
  async render(): Promise<void> { const head = this.w.main.querySelector(".fileview-aside .fc-card.fc-change .fc-card-head"); if (head) head.click(); await flush(); }
  /** Show changes inline, clicked. */
  async inline(): Promise<void> { act(this.w.main.querySelector(".fileview-aside")!, "fcinline")!.click(); await flush(); }
  /** A filter, clicked. */
  async filter(k: "all" | "comments" | "changes"): Promise<void> { this.w.main.querySelector('.fileview-aside [data-act="fcfilter"][data-key="' + k + '"]')!.click(); await flush(); }
  /** The editor taken up (enterEdit: the panel's begin() before the flip, the entry's paint as the editor takes the body, then its
   *  buffer, the text it loaded) or put down (exitEdit: the read view repainted from the bytes in hand). */
  async edit(on: boolean): Promise<void> {
    if (!on) { this.buffer = null; this.w.editing = false; await this.paint(); return; }
    this.tracked!.begin(); this.w.edit(true); this.buffer = this.shownText;
    await flush(); await flush();
  }
  /** The editor's Save through the panel (file-view.ts doSave's tracked path) of SAVED, and its reply: the panel's save goes out and
   *  `reply` answers it, then the viewer's saved() runs: mtimeNs() and the bytes in hand are the saved ones, the seam's onSaved is
   *  told, and the editor leaves, repainting them, or stays over what the person did while the save was out: keystrokes typed
   *  above the changes ("typed"), a decision clicked ("decided"), or the decision this save carried (the insertion accepted)
   *  undone ("undone"). */
  async save(how: "leaves" | "typed" | "decided" | "undone", reply: Status): Promise<void> {
    const w = this.w;
    this.buffer = SAVED;                                 // the text the save takes
    const decided = how === "undone" ? { accepted: [{ id: "h5", oldText: "", newText: " again" }], rejected: [] } : { accepted: [], rejected: [] };
    const done = this.tracked!.save(SAVED, [], decided);
    await flush();
    const m = lastOf(w, "fileComments", "save");
    assert.ok(m, "the save went out through the panel");
    if (how === "typed") this.buffer = "Typed during the save. " + SAVED;
    answer(w, reply, m, { verb: "save", logged: true });
    const r = await done;
    w.viewMtime = r.mtimeNs; w.disk = SAVED; w.diskMtime = r.mtimeNs; this.hand = { text: SAVED, mt: r.mtimeNs }; this.shownText = SAVED; this.s = reply;
    for (const cb of this.savedHooks) cb({ mtimeNs: r.mtimeNs, logged: r.logged });
    if (how === "leaves") { await this.edit(false); return; }
    await flush(); await flush();
  }
  /** The editor's Save through the panel of SAVED, sent and not answered yet: `lateAck` answers it. */
  pendingSave: { done: Promise<{ mtimeNs: string; logged: boolean }>; m: any } | null = null;
  async saveOut(): Promise<void> {
    this.buffer = SAVED;
    const done = this.tracked!.save(SAVED, [], { accepted: [], rejected: [] });
    await flush();
    const m = lastOf(this.w, "fileComments", "save");
    assert.ok(m, "the save went out through the panel");
    this.pendingSave = { done, m };
  }
  /** That save's reply, landing once the editor that sent it is gone (Cancel while it was out): the panel applies the reply, the
   *  viewer runs the seam's onSaved with mtimeNs() where it was and re-reads the saved bytes itself at once (the seam's onSaved doc
   *  in file-view.ts), and that re-read fails to a pane here, as the pane before it did. */
  async lateAck(reply: Status): Promise<void> {
    const { done, m } = this.pendingSave!; this.pendingSave = null;
    answer(this.w, reply, m, { verb: "save", logged: true });
    const r = await done;
    this.s = reply;
    for (const cb of this.savedHooks) cb({ mtimeNs: r.mtimeNs, logged: r.logged });
    await this.pane();
  }
  /** The editor's Save through saveFile of SAVED (file-view.ts doSave when routesSave() is false, as before the panel's first
   *  status): the frame is the viewer's, and nothing reaches the panel until the ack. */
  async saveFile(): Promise<void> { this.buffer = SAVED; await flush(); }
  /** That save's ack (the fileSaved branch) with keystrokes typed above the changes while it was out: the viewer's saved() moves
   *  mtimeNs() and the bytes in hand to the saved ones and tells the seam's onSaved, and the editor stays over the keystrokes.
   *  The panel's onSaved asks the status again (the save was not its own). */
  async savedFile(): Promise<void> {
    const w = this.w;
    this.buffer = "Typed during the save. " + SAVED;
    w.viewMtime = F21; w.disk = SAVED; w.diskMtime = F21; this.hand = { text: SAVED, mt: F21 }; this.shownText = SAVED;
    for (const cb of this.savedHooks) cb({ mtimeNs: F21, logged: true });
    await flush(); await flush();
  }
}
type RoadStart = "painted" | "unpainted" | "source" | "closed" | "closed-unpainted" | "unanswered";
/** A road's world: the viewer of `kind` at `start` (painted with the status of its bytes in; before its first paint; an svg's Source
 *  view painted; either with the panel not yet opened; or painted with the panel's first status not yet answered, so its button is
 *  still hidden and `first` is the status a step answers), the panel mounted and, unless closed or unanswered, open. */
async function roadStart(t: TestContext, kind: RoadKind, start: RoadStart, first: Status = statusF1()): Promise<RoadSeam> {
  store.clear();                                         // the settings a road before this one flipped (Show changes inline, the filter) go back to their defaults
  const w = world({ deferReload: true }); t.after(() => w.close());
  const m = new RoadSeam(t, w, kind);
  if (start === "unpainted" || start === "closed-unpainted") m.unpainted();
  if (start === "source") m.sourceUp();
  m.s = first;
  if (start === "unanswered") {
    const fc = await import("./file-comments");
    m.button = (fc.fileCommentsAction.mount(w.ctx) as unknown as El).childNodes[0] as El;
    await flush();
    return m;
  }
  const { button } = await mount(w, first);
  m.button = button;
  if (start === "painted" || start === "unpainted" || start === "source") { await m.open(); await m.reread(); }
  return m;
}
type RoadStep = [string, (m: RoadSeam) => Promise<void>];
type Road = { kind: RoadKind; start: RoadStart; first?: () => Status; steps: RoadStep[] };
/** Run a road: after each step, every change card read; a step MOVED the cards when what the person sees of them differs from the
 *  last read with the panel open (the panel closed reads nothing). Returns the moves, by step, and the reads. */
async function runRoad(t: TestContext, r: Road): Promise<{ moves: string[]; reads: Array<[string, Record<string, CardRead> | null]> }> {
  const m = await roadStart(t, r.kind, r.start, r.first ? r.first() : statusF1());
  let last = changeCards(m.w);
  const moves: string[] = []; const reads: Array<[string, Record<string, CardRead> | null]> = [["start", last]];
  for (const [label, step] of r.steps) {
    await step(m);
    const now = changeCards(m.w);
    if (now !== null && last !== null && JSON.stringify(now) !== JSON.stringify(last)) moves.push(label);
    if (now !== null) last = now;
    reads.push([label, now]);
  }
  assert.deepEqual(m.w.hookErrors, [], "no hook threw");
  m.w.close();
  return { moves, reads };
}
const DECODE_WORDS = "this image failed to decode: it may be mid-write or truncated";   // the raster pane's own sentence (DECODE_FAILED)
const S5_STATUS = (): Status => statusF1({ storeMtimeNs: S5 });   // the sidecar moved, the file not: the same hunks
const S9_STATUS = (): Status => statusF1({ storeMtimeNs: S9 });   // the sidecar moved again
const C7_STATUS = (): Status => statusF1({ configMtimeNs: "1757145600000000007" });   // the config moved, the file and the sidecar not
const TUNNEL = "tunnel to TESTHOST is not answering; re-dialing";   // a re-ask's pane (the fetch chain's catch after the address was asked again)
const SAVED = DOC + "\nMore.\n";                         // the text a save writes (RoadSeam's save): a line after the last paragraph, so every change keeps its offsets
const S23 = "1757145600000000023";
const SAVED_STATUS = (): Status => statusF1({ fileMtimeNs: F21, storeMtimeNs: S22 });   // the save's reply: the saved bytes, the three changes pending over them
const SAVED_S23 = (): Status => statusF1({ fileMtimeNs: F21, storeMtimeNs: S23 });     // a later status for the saved bytes, the sidecar moved
const UNDONE_STATUS = (): Status => status({ hunks: [h1, h3], fileMtimeNs: F21, storeMtimeNs: S22 });   // the reply to a save that carried the insertion's accept
const UNDONE_S23 = (): Status => status({ hunks: [h1, h3], fileMtimeNs: F21, storeMtimeNs: S23 });
/** The roads of the card-state rule, by the id each row of #cardState's table names (file-comments.ts). */
const ROADS: Record<string, Road> = {
  "text-first-open": { kind: "text", start: "unpainted", steps: [["paint", (m) => m.paint()]] },
  "text-first-open-pane": { kind: "text", start: "unpainted", steps: [["pane", (m) => m.pane()], ["paint", (m) => m.paint()]] },
  "text-pane-before-panel": { kind: "text", start: "closed-unpainted", steps: [["pane", (m) => m.pane()], ["open", (m) => m.open()], ["reread", (m) => m.reread()], ["paint", (m) => m.paint()]] },
  "text-reload-fails": { kind: "text", start: "painted", steps: [["pane", (m) => m.pane()], ["paint", (m) => m.land()]] },
  "text-second-pane": { kind: "text", start: "painted", steps: [["pane", (m) => m.pane()], ["pane again", (m) => m.pane("the kernel refused the read")], ["paint", (m) => m.land()]] },
  "text-status-over-pane": { kind: "text", start: "painted", steps: [["pane", (m) => m.pane()], ["status", (m) => m.status(S5_STATUS())], ["paint", (m) => m.land()]] },
  "text-config-status-over-pane": { kind: "text", start: "painted", steps: [["pane", (m) => m.pane()], ["status", (m) => m.status(C7_STATUS())], ["paint", (m) => m.land()]] },
  "text-reopen-over-pane": { kind: "text", start: "painted", steps: [["pane", (m) => m.pane()], ["close", (m) => m.close()], ["open", (m) => m.open()], ["reread", (m) => m.reread()], ["paint", (m) => m.land()]] },
  "text-first-panel-open-over-pane": { kind: "text", start: "closed", steps: [["pane", (m) => m.pane()], ["open", (m) => m.open()], ["reread", (m) => m.reread()], ["paint", (m) => m.land()]] },
  "text-reread-over-content": { kind: "text", start: "painted", steps: [["close", (m) => m.close()], ["open", (m) => m.open()], ["reread", (m) => m.reread()]] },
  "text-store-status": { kind: "text", start: "painted", steps: [["status", (m) => m.status(S5_STATUS())]] },
  "text-new-bytes": { kind: "text", start: "painted", steps: [["status", (m) => m.status(statusF11())], ["land", (m) => m.land()]] },
  "text-new-bytes-pane-first": { kind: "text", start: "painted", steps: [["pane", (m) => m.pane()], ["status", (m) => m.status(statusF11())], ["land", (m) => m.land()]] },
  "text-new-bytes-then-pane": { kind: "text", start: "painted", steps: [["status", (m) => m.status(statusF11())], ["pane", (m) => { m.out = null; return m.pane(); }], ["land", (m) => m.land()]] },
  "text-inline-over-content": { kind: "text", start: "painted", steps: [["inline off", (m) => m.inline()], ["inline on", (m) => m.inline()]] },
  "text-inline-over-pane": { kind: "text", start: "painted", steps: [["inline off", (m) => m.inline()], ["pane", (m) => m.pane()], ["inline on", (m) => m.inline()], ["paint", (m) => m.land()]] },
  "text-inline-before-first-paint": { kind: "text", start: "unpainted", steps: [["inline off", (m) => m.inline()], ["paint", (m) => m.paint()]] },
  "text-filter-over-content": { kind: "text", start: "painted", steps: [["comments", (m) => m.filter("comments")], ["all", (m) => m.filter("all")]] },
  "text-filter-over-pane": { kind: "text", start: "painted", steps: [["pane", (m) => m.pane()], ["comments", (m) => m.filter("comments")], ["all", (m) => m.filter("all")], ["paint", (m) => m.land()]] },
  "text-edit": { kind: "text", start: "painted", steps: [["edit", (m) => m.edit(true)], ["done", (m) => m.edit(false)]] },
  "text-save-leaves": { kind: "text", start: "painted", steps: [["edit", (m) => m.edit(true)], ["save", (m) => m.save("leaves", SAVED_STATUS())]] },
  "text-save-typed": { kind: "text", start: "painted", steps: [["edit", (m) => m.edit(true)], ["save", (m) => m.save("typed", SAVED_STATUS())], ["render", (m) => m.render()], ["status", (m) => m.status(SAVED_S23())], ["done", (m) => m.edit(false)]] },
  "text-save-decided": { kind: "text", start: "painted", steps: [["edit", (m) => m.edit(true)], ["save", (m) => m.save("decided", SAVED_STATUS())], ["render", (m) => m.render()], ["status", (m) => m.status(SAVED_S23())], ["done", (m) => m.edit(false)]] },
  "text-save-undone": { kind: "text", start: "painted", steps: [["edit", (m) => m.edit(true)], ["save", (m) => m.save("undone", UNDONE_STATUS())], ["render", (m) => m.render()], ["status", (m) => m.status(UNDONE_S23())], ["done", (m) => m.edit(false)]] },
  "text-late-ack-over-pane": { kind: "text", start: "painted", steps: [["edit", (m) => m.edit(true)], ["save", (m) => m.saveOut()], ["cancel", (m) => m.edit(false)], ["land", (m) => { m.out = { text: SAVED, mt: F21 }; return m.land(); }], ["pane", (m) => m.pane()], ["ack", (m) => m.lateAck(SAVED_STATUS())], ["render", (m) => m.render()]] },
  "text-savefile-typed": { kind: "text", start: "unanswered", steps: [["edit", (m) => m.edit(true)], ["save", (m) => m.saveFile()], ["status", async (m) => { answer(m.w, m.s); await flush(); await flush(); }], ["open", (m) => m.open()], ["reread", (m) => m.reread()], ["ack", (m) => m.savedFile()], ["saved status", async (m) => { m.s = SAVED_STATUS(); answer(m.w, m.s); await flush(); await flush(); }], ["done", (m) => m.edit(false)]] },
  "svg-landing-then-paint": { kind: "svg", start: "painted", steps: [["status", (m) => m.status(statusF11())], ["land", (m) => m.land()], ["paint", (m) => m.paint()]] },
  "svg-first-open": { kind: "svg", start: "unpainted", steps: [["land", (m) => m.land()], ["paint", (m) => m.paint()]] },
  "svg-reask-pane": { kind: "svg", start: "painted", steps: [["status", (m) => m.status(statusF11())], ["land", (m) => m.land()], ["pane", (m) => m.pane(TUNNEL)], ["way back", (m) => m.paint()]] },
  "svg-loader-status": { kind: "svg", start: "painted", steps: [["loader", (m) => m.loader()], ["status", (m) => m.status(S5_STATUS())], ["answer", (m) => m.land()], ["load", (m) => m.paint()]] },
  "svg-wayback-status": { kind: "svg", start: "painted", steps: [["loader", (m) => m.loader()], ["pane", (m) => m.pane(TUNNEL)], ["status", (m) => m.status(S5_STATUS())], ["way back", (m) => m.land()], ["second status", (m) => m.status(S9_STATUS())], ["load", (m) => m.paint()]] },
  "svg-inline-landing-window": { kind: "svg", start: "painted", steps: [["status", (m) => m.status(statusF11())], ["land", (m) => m.land()], ["inline off", (m) => m.inline()], ["load", (m) => m.paint()]] },
  "svg-inline-loader": { kind: "svg", start: "painted", steps: [["loader", (m) => m.loader()], ["inline off", (m) => m.inline()], ["answer", (m) => m.land()], ["load", (m) => m.paint()]] },
  "svg-inline-wayback": { kind: "svg", start: "painted", steps: [["loader", (m) => m.loader()], ["pane", (m) => m.pane(TUNNEL)], ["way back", (m) => m.land()], ["inline off", (m) => m.inline()], ["load", (m) => m.paint()]] },
  "svg-source-reload-fails": { kind: "svg", start: "source", steps: [["pane", (m) => m.pane()], ["paint", (m) => m.land().then(() => m.paint())]] },
  "svg-press-window": { kind: "svg", start: "source", steps: [["status", (m) => m.status(statusF11())], ["land", (m) => m.land()], ["pane", (m) => { m.out = null; return m.pane(); }], ["press", (m) => m.press()], ["render", (m) => m.render()], ["inline off", (m) => m.inline()], ["inline on", (m) => m.inline()], ["load", (m) => m.paint()]] },
  "svg-press-back": { kind: "svg", start: "source", steps: [["status", (m) => m.status(statusF11())], ["land", (m) => m.land()], ["press", (m) => m.press()], ["press back", (m) => m.press()], ["decode", (m) => m.paint()]] },
  "svg-source-landing-status": { kind: "svg", start: "source", steps: [["land", (m) => { m.out = { text: DOC11, mt: F11 }; return m.land(); }], ["status", (m) => m.status(statusF11())], ["decode", (m) => m.paint()]] },
  "svg-source-landing-store-status": { kind: "svg", start: "source", steps: [["land", (m) => { m.out = { text: DOC11, mt: F11 }; return m.land(); }], ["status", (m) => m.status(S5_STATUS())], ["decode", (m) => m.paint()]] },
  "svg-press-landing-status": { kind: "svg", start: "painted", steps: [["press", (m) => m.press()], ["land", (m) => { m.out = { text: DOC11, mt: F11 }; return m.land(); }], ["status", (m) => m.status(statusF11())], ["decode", (m) => m.paint()]] },
  "svg-press-marked": { kind: "svg", start: "source", steps: [["press", (m) => m.press()], ["render", (m) => m.render()], ["load", (m) => m.paint()]] },
  "svg-press-list": { kind: "svg", start: "source", first: statusMany, steps: [["press", (m) => m.press()], ["render", (m) => m.render()], ["close", (m) => m.close()], ["open", (m) => m.open()], ["reread", (m) => m.reread()], ["load", (m) => m.paint()]] },
  "svg-status-in-press-window": { kind: "svg", start: "source", steps: [["press", (m) => m.press()], ["status", (m) => m.status(S5_STATUS())], ["load", (m) => m.paint()]] },
  "svg-other-type-render": { kind: "svg", start: "source", steps: [["other type", (m) => m.landOther()], ["render", (m) => m.render()], ["load", (m) => m.paint()]] },
  "svg-other-type-reopen": { kind: "svg", start: "source", steps: [["other type", (m) => m.landOther()], ["close", (m) => m.close()], ["open", (m) => m.open()], ["reread", (m) => m.reread()], ["load", (m) => m.paint()]] },
  "svg-other-type-list": { kind: "svg", start: "source", first: statusMany, steps: [["other type", (m) => m.landOther()], ["render", (m) => m.render()], ["close", (m) => m.close()], ["open", (m) => m.open()], ["reread", (m) => m.reread()], ["load", (m) => m.paint()]] },
  "svg-picture-other-type-render": { kind: "svg", start: "painted", steps: [["other type", (m) => { m.out = { text: DOC11, mt: F11 }; return m.landOther(); }], ["render", (m) => m.render()], ["load", (m) => m.paint()]] },
  "svg-picture-other-type-reopen": { kind: "svg", start: "painted", steps: [["other type", (m) => { m.out = { text: DOC11, mt: F11 }; return m.landOther(); }], ["close", (m) => m.close()], ["open", (m) => m.open()], ["reread", (m) => m.reread()], ["load", (m) => m.paint()]] },
  "svg-picture-other-type-inline": { kind: "svg", start: "painted", steps: [["other type", (m) => { m.out = { text: DOC11, mt: F11 }; return m.landOther(); }], ["inline off", (m) => m.inline()], ["load", (m) => m.paint()]] },
  "svg-picture-other-type-pane": { kind: "svg", start: "painted", steps: [["other type", (m) => { m.out = { text: DOC11, mt: F11 }; return m.landOther(); }], ["pane", (m) => m.pane(DECODE_WORDS)], ["load", (m) => m.paint()]] },
  "raster-status-first": { kind: "raster", start: "painted", steps: [["status", (m) => m.status(statusF11())], ["land", (m) => m.land()], ["pane", (m) => m.pane(DECODE_WORDS)], ["close", (m) => m.close()], ["open", (m) => m.open()], ["reread", (m) => m.reread()], ["decode", (m) => m.paint()]] },
  "raster-poll-order": { kind: "raster", start: "painted", steps: [["land", (m) => { m.out = { text: DOC11, mt: F11 }; return m.land(); }], ["status", (m) => m.status(statusF11())], ["pane", (m) => m.pane(DECODE_WORDS)], ["decode", (m) => m.paint()]] },
  "raster-render-in-window": { kind: "raster", start: "painted", steps: [["status", (m) => m.status(statusF11())], ["land", (m) => m.land()], ["render", (m) => m.render()], ["pane", (m) => m.pane(DECODE_WORDS)], ["decode", (m) => m.paint()]] },
  "raster-landing-status": { kind: "raster", start: "painted", steps: [["land", (m) => { m.out = { text: DOC11, mt: F11 }; return m.land(); }], ["status", (m) => m.status(S5_STATUS())], ["pane", (m) => m.pane(DECODE_WORDS)], ["decode", (m) => m.paint()]] },
  "raster-inline-landing-window": { kind: "raster", start: "painted", steps: [["status", (m) => m.status(statusF11())], ["land", (m) => m.land()], ["inline off", (m) => m.inline()], ["decode", (m) => m.paint()]] },
  "raster-landing-then-render": { kind: "raster", start: "painted", steps: [["land", (m) => { m.out = { text: DOC11, mt: F11 }; return m.land(); }], ["render", (m) => m.render()], ["decode", (m) => m.paint()]] },
  "raster-landing-then-reopen": { kind: "raster", start: "painted", steps: [["land", (m) => { m.out = { text: DOC11, mt: F11 }; return m.land(); }], ["close", (m) => m.close()], ["open", (m) => m.open()], ["reread", (m) => m.reread()], ["decode", (m) => m.paint()]] },
  "raster-landing-then-inline": { kind: "raster", start: "painted", steps: [["land", (m) => { m.out = { text: DOC11, mt: F11 }; return m.land(); }], ["inline off", (m) => m.inline()], ["decode", (m) => m.paint()]] },
  "raster-landing-then-pane": { kind: "raster", start: "painted", steps: [["land", (m) => { m.out = { text: DOC11, mt: F11 }; return m.land(); }], ["pane", (m) => m.pane(DECODE_WORDS)], ["decode", (m) => m.paint()]] },
  "svg-landing-then-pane": { kind: "svg", start: "painted", steps: [["land", (m) => { m.out = { text: DOC11, mt: F11 }; return m.land(); }], ["pane", (m) => m.pane(TUNNEL)], ["way back", (m) => m.paint()]] },
  "svg-source-landing-then-pane": { kind: "svg", start: "source", steps: [["land", (m) => { m.out = { text: DOC11, mt: F11 }; return m.land(); }], ["pane", (m) => m.pane()], ["decode", (m) => m.paint()]] },
};

/** #cardState's doc's table (file-comments.ts): each row's id, its moves at fe43d2c2a and at this head, and what it says of the moves
 *  the head drops and adds. */
function roadsTable(src: string): Array<{ id: string; fe: string[]; head: string[]; dropped: string; added: string; line: string }> {
  const doc = src.slice(src.lastIndexOf("/**", src.indexOf("  #cardState: CardState =")), src.indexOf("  #cardState: CardState ="));
  const body = doc.slice(doc.indexOf("*  ROADS\n") + "*  ROADS\n".length, doc.indexOf("*  ROADS END"));
  const rows: string[] = [];
  for (const raw of body.split("\n")) {
    const l = raw.replace(/^\s*\*\s?/, "");
    if (/^ \S/.test(l)) rows.push(l.trim()); else if (l.trim()) { assert.ok(rows.length, "a continuation line before any row: " + raw); rows[rows.length - 1] += " " + l.trim(); }
  }
  const moves = (x: string): string[] => (x.trim() === "none" ? [] : x.split(",").map((y) => y.trim()));
  return rows.map((line) => {
    const m = /^([a-z0-9-]+) \([^)]*\): fe43d2c2a ([^;]+); head ([^.]+)\.(?: Dropped: (.*?))?(?: Added: (.*))?$/.exec(line);
    assert.ok(m, "a row of the table reads as `id (road): fe43d2c2a <moves>; head <moves>.` then its Dropped and Added clauses: " + line);
    return { id: m![1], fe: moves(m![2]), head: moves(m![3]), dropped: m![4] || "", added: m![5] || "", line };
  });
}

test("the card-state rule's roads: each row of #cardState's table runs over the seam, and the change cards move at the steps its head column names, no other; every move fe43d2c2a made there that the head drops, and every move the head adds, is named with its reason", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
  const ran: Record<string, { moves: string[]; reads: unknown }> = {};
  for (const id of Object.keys(ROADS)) { ran[id] = await runRoad(t, ROADS[id]); t.diagnostic("road " + id + " moves " + JSON.stringify(ran[id].moves)); }   // every road first, so the moves are on record whatever the table says
  const rows = roadsTable(PANEL_SRC);
  assert.deepEqual(rows.map((r) => r.id).sort(), Object.keys(ROADS).sort(), "one row per road the test runs, and a road for every row");
  for (const r of rows) {
    const { moves, reads } = ran[r.id];
    assert.deepEqual(moves, r.head, r.id + ": the change cards move at the steps the table's head column names (#cardState's doc); the reads: " + JSON.stringify(reads));
    const labels = ROADS[r.id].steps.map(([l]) => l);
    for (const x of [...r.fe, ...r.head]) assert.ok(labels.includes(x), r.id + ": the table names a step the road has: " + x);
    for (const x of r.fe.filter((y) => !r.head.includes(y))) assert.ok(r.dropped.includes("at the " + x), r.id + ": the move fe43d2c2a made at the " + x + " that the head drops is named with its reason");
    for (const x of r.head.filter((y) => !r.fe.includes(y))) assert.ok(r.added.includes("at the " + x), r.id + ": the move the head adds at the " + x + " is named with its reason");
    // ...and a clause names only steps of its own column: each "at the <step>" in a Dropped clause is a step where fe43d2c2a moved the
    // cards, and in an Added clause one where the head does, so a stale clause reds. A row whose columns agree may still carry a
    // clause, for a partial change at a step where both columns move (text-save-undone's Dropped clause, raster-inline-landing-window's
    // Added clause); the gap that leaves is a stale clause at such a step, which this check cannot tell from a partial one.
    const named = (clause: string): string[] => labels.filter((l) => new RegExp("\\bat the " + l + "(?![a-z])").test(clause));
    for (const x of named(r.dropped)) assert.ok(r.fe.includes(x), r.id + ": the Dropped clause names the " + x + ", a step where fe43d2c2a made no move");
    for (const x of named(r.added)) assert.ok(r.head.includes(x), r.id + ": the Added clause names the " + x + ", a step where the head makes no move");
  }
});

/** The test's own reading of each step, kept apart from the panel's: whether the body shows its last content paint and whether any
 *  content paint has come (file-comments.ts, #cardState's doc). A content paint puts it up; a pane, a picture put up (a landing's on
 *  the picture view, a press to the picture's) and the re-ask's loader take it down; a landing under the Source view, a press to the
 *  Source view waiting for its decode, a status, a render and a gesture leave it. A step's `event` says whether the rule names it for
 *  a card's state; its `lists`, whether for the cards the list shows (the same as `event` unless given). */
type Said = { painted: boolean; bodyIsPaint: boolean };
type OStep = { label: string; run: (m: RoadSeam, n: number) => Promise<void>; event: (o: Said, m: RoadSeam) => boolean; after: (o: Said, m: RoadSeam) => void; lists?: (o: Said, m: RoadSeam) => boolean };
const EVERY = (): boolean => true;   // the filter's list at the click, whatever the body shows (#cardState's doc, event 3)
const KEEP = (): void => { /* the body as it was */ };
const O_STEPS: Record<string, OStep> = {
  paint: { label: "paint", run: (m) => m.paint(), event: () => true, after: (o) => { o.painted = true; o.bodyIsPaint = true; } },
  pane: { label: "pane", run: (m) => m.pane(), event: () => false, after: (o) => { o.bodyIsPaint = false; } },
  land: { label: "land", run: (m) => { m.out = { text: DOC, mt: F11 }; return m.land(); }, event: () => false, after: (o, m) => { if (m.show === "loading") o.bodyIsPaint = false; } },   // on the picture view the landed bytes' picture goes up; under the Source view the body stays
  loader: { label: "loader", run: (m) => m.loader(), event: () => false, after: (o, m) => { if (m.show === "loader") o.bodyIsPaint = false; } },   // over a picture only
  press: { label: "press", run: (m) => m.press(), event: () => false, after: (o, m) => { if (m.show === "loading") o.bodyIsPaint = false; } },   // to the picture it takes the body down; to the Source view the picture stays until the decode
  status: { label: "status", run: (m, n) => m.status(statusMany({ storeMtimeNs: String(BigInt(S5) + BigInt(n)), fileMtimeNs: m.s.fileMtimeNs })), event: () => true, after: KEEP },
  reopen: { label: "reopen", run: async (m) => { await m.close(); await m.open(); await m.reread(); }, event: () => false, after: KEEP },
  render: { label: "render", run: (m) => m.render(), event: () => false, after: KEEP },
  inline: { label: "inline", run: (m) => m.inline(), event: (o) => o.painted && o.bodyIsPaint, after: KEEP },
  comments: { label: "comments", run: (m) => m.filter("comments"), event: (o) => o.painted && o.bodyIsPaint, after: KEEP, lists: EVERY },
  all: { label: "all", run: (m) => m.filter("all"), event: (o) => o.painted && o.bodyIsPaint, after: KEEP, lists: EVERY },
};
const ORDER_STARTS: Array<{ name: string; kind: RoadKind; start: RoadStart; steps: string[] }> = [
  { name: "a painted text file", kind: "text", start: "painted", steps: ["paint", "pane", "status", "reopen", "render", "inline", "comments", "all"] },
  { name: "a text file before its first paint", kind: "text", start: "unpainted", steps: ["paint", "pane", "status", "reopen", "render", "inline", "comments", "all"] },
  { name: "an svg's picture", kind: "svg", start: "painted", steps: ["paint", "pane", "land", "loader", "press", "status", "reopen", "render", "inline", "comments"] },
  { name: "an svg's Source view", kind: "svg", start: "source", steps: ["paint", "pane", "land", "loader", "press", "status", "reopen", "render", "inline", "all", "comments"] },
  { name: "a raster picture", kind: "raster", start: "painted", steps: ["paint", "pane", "land", "status", "render", "inline"] },
];

test("the card-state rule over every ordering of three of the steps that act on each start, from five starts, each with a change in more paragraphs than the list shows before its fold: a painted text file and one before its first paint (a content paint, a pane, a status that differs, the panel's re-open, a render, Show changes inline, Comments alone and All; 512 orderings each), an svg's picture (a content paint, a pane, a landing, the re-ask's loader, a press of the Source toggle, a status that differs, the re-open, a render, Show changes inline and Comments alone; 1000), its Source view (the same ten and All; 1331; the loader acts there only after a press puts the picture up) and a raster picture (a content paint, a pane, a landing, a status that differs, a render and Show changes inline; 216): a change card moves, and the cards listed change, only at a step the test's own reading of the rule names (file-comments.ts, #cardState's doc)", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
  let runs = 0; let moved = 0; let relisted = 0; const folded = new Set<string>();
  for (const st of ORDER_STARTS) {
    const seqs: string[][] = [];
    for (const a of st.steps) for (const b of st.steps) for (const c of st.steps) seqs.push([a, b, c]);
    for (const seq of seqs) {
      const m = await roadStart(t, st.kind, st.start, statusMany());
      const o: Said = { painted: st.start !== "unpainted", bodyIsPaint: st.start !== "unpainted" };
      let last = changeCards(m.w)!;
      for (let i = 0; i < seq.length; i++) {
        const s = O_STEPS[seq[i]];
        const event = s.event(o, m), lists = (s.lists || s.event)(o, m);
        await s.run(m, runs * 3 + i + 1);
        s.after(o, m);
        const now = changeCards(m.w)!;
        const keys = Object.keys(now).filter((k) => k in last);
        const changed = keys.filter((k) => JSON.stringify(now[k]) !== JSON.stringify(last[k]));
        const listed = Object.keys(now).length !== keys.length || Object.keys(last).length !== keys.length;
        const where = st.name + ", " + seq.slice(0, i + 1).join(" > ");
        if (changed.length) moved++;
        if (listed) relisted++;
        if (changeList(m.w).fold !== null) folded.add(st.name);
        assert.ok(event || !changed.length, where + ": a change card moved at a step the rule does not name (#cardState's doc): " + JSON.stringify(changed.map((k) => [k, last[k], now[k]])));
        assert.ok(lists || !listed, where + ": the change cards listed changed at a step the rule does not name for the list (#cardState's doc): " + JSON.stringify([Object.keys(last), Object.keys(now)]));
        last = now;
      }
      assert.deepEqual(m.w.hookErrors, [], st.name + ", " + seq.join(" > ") + ": no hook threw");
      m.w.close();
      runs++;
    }
  }
  t.diagnostic("orderings run " + runs + ", steps that moved a card " + moved + ", steps that changed the cards listed " + relisted + ", starts whose list folded " + folded.size);
  assert.ok(runs === 512 * 2 + 1000 + 1331 + 216 && moved > 0, "every ordering ran (3571), and some moved a card (the check reads real moves): " + runs + ", " + moved);
  assert.deepEqual([...folded].sort(), ["a painted text file", "a text file before its first paint", "an svg's Source view", "an svg's picture"], "the fixture folds the list over the text on every start that shows text, so the list's check sees a fold (a raster picture shows none)");
});

// ── the card-state rule's roads as pins with their own words (each also a row of #cardState's table), and the clicks on a card's
// link and on its Comment on this change while the body does not show the last content paint (notInView) ──

test("the panel re-opened over a failure pane, its status re-read unchanged, and the panel's first open over one: no change card moves at the pane, the open, the re-read or the same bytes' paint after the pane (file-comments.ts, #cardState's doc)", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
  for (const id of ["text-reopen-over-pane", "text-first-panel-open-over-pane"]) {
    const { moves, reads } = await runRoad(t, ROADS[id]);
    assert.deepEqual(moves, [], id + ": no change card moves at the pane, the open, the re-read of the same status, or the paint of the same bytes; the reads: " + JSON.stringify(reads));
    const [, open] = reads.find(([l]) => l === "reread")!;
    assert.deepEqual(open!["chg:h5"], { tags: [], buttons: ["Accept", "Reject", "Comment on this change"], reveal: null, link: true }, id + ": over the pane the insertion's card keeps what the last content paint gave it, Comment on this change and the link included");
  }
});

test("a raster picture's landing, its picture up and still decoding, then a status for its bytes, then its decode-failure pane, then a picture that decodes: the change card moves at the status and at the content paint of the bytes that decode, not at the landing or the pane (file-comments.ts, #cardState's doc)", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
  const { moves, reads } = await runRoad(t, ROADS["raster-poll-order"]);
  assert.deepEqual(moves, ["status", "decode"], "the moves come at the status and at the decode, not at the landing or the pane; the reads: " + JSON.stringify(reads));
  const at = (l: string) => reads.find(([x]) => x === l)![1]!["chg:h5"];
  assert.deepEqual(at("status"), { tags: [], buttons: ["Accept", "Reject"], reveal: null, link: false }, "at the status the insertion's card claims no Reveal (#cardState's doc)");
  assert.deepEqual(at("pane"), at("status"), "the pane moves no card");
  assert.deepEqual(at("decode"), { tags: [], buttons: ["Accept", "Reject", "Reveal"], reveal: "Show the change in the Raw view", link: false }, "at the paint of the bytes that decode the card takes its Reveal");
});

test("a raster picture whose status is current, newer bytes landing with their picture up and still decoding, then a status for the painted bytes whose sidecar moved: the change card moves at that status, the insertion's Reveal withheld over the landed picture, and keeps that state through the decode-failure pane and the decode (file-comments.ts, #cardState's doc)", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
  const { moves, reads } = await runRoad(t, ROADS["raster-landing-status"]);
  assert.deepEqual(moves, ["status"], "one move, at the status; the reads: " + JSON.stringify(reads));
  const at = (l: string) => reads.find(([x]) => x === l)![1]!["chg:h5"];
  assert.deepEqual(at("land"), { tags: [], buttons: ["Accept", "Reject", "Reveal"], reveal: "Show the change in the Raw view", link: false }, "the landing moves no card");
  for (const l of ["status", "pane", "decode"]) assert.deepEqual(at(l), { tags: [], buttons: ["Accept", "Reject"], reveal: null, link: false }, "at the " + l + " the insertion's card offers no Reveal (#cardState's doc)");
});

test("an svg picture's re-ask pane, a status for a moved sidecar over it, the way back's picture up and still loading, and a second status for a moved sidecar: the change card moves at the first status and at the way back's load, not at the second status over the loading picture (file-comments.ts, #cardState's doc)", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
  const { moves, reads } = await runRoad(t, ROADS["svg-wayback-status"]);
  assert.deepEqual(moves, ["status", "load"], "the moves come at the status over the pane and at the load; the reads: " + JSON.stringify(reads));
  const at = (l: string) => reads.find(([x]) => x === l)![1]!["chg:h5"];
  for (const l of ["status", "way back", "second status"]) assert.deepEqual(at(l), { tags: [], buttons: ["Accept", "Reject"], reveal: null, link: false }, "at the " + l + " the insertion's card offers no Reveal (#cardState's doc)");
  assert.deepEqual(at("load"), { tags: [], buttons: ["Accept", "Reject", "Reveal"], reveal: "Show the change in the Raw view", link: false }, "at the way back's load the card takes its Reveal");
});

test("Show changes inline turned off while the landed bytes' picture, the re-ask's loader or the way back's picture holds the body moves no change card; the next picture's load takes it (file-comments.ts, #cardState's doc)", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
  for (const id of ["svg-inline-landing-window", "svg-inline-loader", "svg-inline-wayback", "raster-inline-landing-window"]) {
    const { moves, reads } = await runRoad(t, ROADS[id]);
    const last = ROADS[id].steps[ROADS[id].steps.length - 1][0];
    assert.ok(!moves.includes("inline off") && moves.includes(last), id + ": no move at the flip, and one at the " + last + "; the reads: " + JSON.stringify(reads));
    const off = reads.find(([x]) => x === last)![1]!["chg:h3"];
    assert.ok(off.reveal !== null && off.reveal.startsWith("Open the Raw view at the change"), id + ": at the " + last + " the deletion's Reveal is titled for the marks being off: " + JSON.stringify(off));
  }
});

test("Show changes inline turned on over a failure pane moves no change card; the next content paint takes it, with the marks back over the text (file-comments.ts, #cardState's doc)", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
  const { moves, reads } = await runRoad(t, ROADS["text-inline-over-pane"]);
  assert.deepEqual(moves, ["inline off", "paint"], "Show changes inline off moves the cards at once over the text; on over the pane moves none; the paint after the pane moves them; the reads: " + JSON.stringify(reads));
  const at = (l: string) => reads.find(([x]) => x === l)![1]!;
  const off = at("inline off")["chg:h5"];
  assert.ok(off.tags.length === 0 && off.link === false && off.reveal !== null && off.reveal.startsWith("Open the Raw view at the change (line ") && off.reveal.endsWith("the marks are off, so the change is not marked there"), "Show changes inline off over the text: the card takes the marks-off state at once, no not shown tag and a Reveal titled for the marks being off: " + JSON.stringify(off));
  assert.deepEqual(at("inline on"), at("pane"), "over the pane the flip on takes no not shown tag and no Reveal naming a line");
  assert.deepEqual(at("paint")["chg:h5"], { tags: [], buttons: ["Accept", "Reject", "Comment on this change"], reveal: null, link: true }, "at the paint the insertion is marked again, its card linking to the mark");
  const del = at("paint")["chg:h3"];
  assert.ok(del.reveal !== null && del.reveal.startsWith("Show the change in the Raw view (line "), "at the paint the deletion's Reveal is titled for the marks being on: " + JSON.stringify(del));
});

test("Show changes inline turned off before a text file's first paint: the paint takes the flip, each unmarked change's card with no not shown tag and a Reveal titled for the marks being off (file-comments.ts, #cardState's doc)", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
  const { moves, reads } = await runRoad(t, ROADS["text-inline-before-first-paint"]);
  assert.deepEqual(moves, ["paint"], "one move, at the paint; the reads: " + JSON.stringify(reads));
  const at = reads.find(([x]) => x === "paint")![1]!;
  for (const k of ["chg:h1", "chg:h3", "chg:h5"]) {
    assert.deepEqual(at[k].tags, [], k + ": no not shown tag while the marks are off");
    assert.ok(at[k].reveal !== null && at[k].reveal!.startsWith("Open the Raw view at the change (line ") && at[k].reveal!.endsWith("the marks are off, so the change is not marked there"), k + ": a Reveal titled for the marks being off: " + JSON.stringify(at[k]));
  }
});

test("an svg's reload landing under its Source view, a second reload's failure pane, the pane left by a press of the Source toggle to a picture still loading, and then a render and Show changes inline off and on: no change card moves until the picture's load, the content paint of the landed bytes (file-comments.ts, #cardState's doc)", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
  const { moves, reads } = await runRoad(t, ROADS["svg-press-window"]);
  assert.deepEqual(moves, ["status", "load"], "the moves come at the status for the reload's bytes and at the picture's load; none at the landing, the pane, the press, the render or the flips; the reads: " + JSON.stringify(reads));
  const at = (l: string) => reads.find(([x]) => x === l)![1]!["chg:h5"];
  for (const l of ["land", "pane", "press", "render", "inline off", "inline on"]) assert.deepEqual(at(l), at("status"), "at the " + l + " the insertion's card keeps its state (#cardState's doc)");
  assert.deepEqual(at("load"), { tags: [], buttons: ["Accept", "Reject", "Reveal"], reveal: "Show the change in the Raw view", link: false }, "at the picture's load the card takes its Reveal: the picture marks no change");
});

/** What a click did apart from the row under its card: requests posted, marks scrolled into view, offsets scrolled to, switches of
 *  view, the composer, the keyboard. */
function sideEffects(m: RoadSeam): { posted: number; scrolled: number; offsets: number; modes: number; composer: boolean; focus: unknown } {
  const aside = m.w.main.querySelector(".fileview-aside")!;
  return { posted: m.w.posted.length, scrolled: scrolledInto.length, offsets: m.w.scrolls.length, modes: m.w.modes.length, composer: !(aside.querySelector(".fc-composer") as El).hidden, focus: doc.activeElement };
}
/** Every row under a change card, by its slot and its words. */
const rowsUnderCard = (m: RoadSeam, id: string): Array<[string, string]> => {
  const c = card(m.w.main.querySelector(".fileview-aside")!, "chg:" + id);
  return c ? c.querySelectorAll(".fc-err").map((r) => [r.getAttribute("data-slot")!, r.childNodes[0].textContent!] as [string, string]) : [];
};
/** The row under a change card, or null. */
const rowUnder = (m: RoadSeam, id: string): string | null => {
  const r = card(m.w.main.querySelector(".fileview-aside")!, "chg:" + id)!.querySelector(".fc-err");
  return r ? r.childNodes[0].textContent : null;
};
/** The insertion's link and its Comment on this change, clicked while the body does not show the last content paint: each answers in
 *  the row under the card and in the live region, and does nothing else. No requestAnimationFrame is installed here, so the region
 *  takes the words at once (speak's branch for a host with no frames; the live-region case below installs one). */
async function clicksSayNotInView(m: RoadSeam, where: string): Promise<void> {
  const { NOT_IN_VIEW_LINK, NOT_IN_VIEW_COMMENT } = await import("./file-comments");
  const aside = m.w.main.querySelector(".fileview-aside")!;
  const live = (): string | null => aside.querySelector(".fc-live")!.textContent;
  assert.deepEqual(changeCards(m.w)!["chg:h5"], { tags: [], buttons: ["Accept", "Reject", "Comment on this change"], reveal: null, link: true }, where + ": the premise: the card keeps the link and Comment on this change the last content paint gave it (#cardState's doc)");
  assert.equal(typeof (globalThis as { requestAnimationFrame?: unknown }).requestAnimationFrame, "undefined", where + ": the premise: no requestAnimationFrame, so speak writes the words at once");
  const before = sideEffects(m);
  card(aside, "chg:h5")!.querySelector(".fc-ref")!.click();
  assert.equal(live(), NOT_IN_VIEW_LINK, where + ": the live region holds the link's words right after its click, written at once with no frame to wait for (speak)");
  await flush(); await flush();
  assert.deepEqual(sideEffects(m), before, where + ": the link's click does nothing else: no scroll, no switch to Raw, no composer, no request");
  assert.equal(rowUnder(m, "h5"), NOT_IN_VIEW_LINK, where + ": the row under the card says the change is not in view (notInView)");
  act(card(aside, "chg:h5")!, "fcchangecomment", "h5")!.click();
  assert.equal(live(), NOT_IN_VIEW_COMMENT, where + ": and Comment on this change's words right after its click");
  await flush(); await flush();
  assert.deepEqual(sideEffects(m), before, where + ": Comment on this change's click does nothing else: no composer, no scroll, no request");
  assert.equal(rowUnder(m, "h5"), NOT_IN_VIEW_COMMENT, where + ": the row says so for Comment on this change");
}
/** After the next content paint: the row gone, and the same clicks act (the link scrolls to the mark, the composer opens). */
async function clicksAct(m: RoadSeam, where: string): Promise<void> {
  const aside = m.w.main.querySelector(".fileview-aside")!;
  assert.equal(rowUnder(m, "h5"), null, where + ": the content paint takes the row");
  const scrolled = scrolledInto.length;
  card(aside, "chg:h5")!.querySelector(".fc-ref")!.click(); await flush(); await flush();
  assert.ok(scrolledInto.length > scrolled && rowUnder(m, "h5") === null, where + ": the link's click scrolls to the change's mark");
  act(card(aside, "chg:h5")!, "fcchangecomment", "h5")!.click(); await flush(); await flush();
  assert.equal((aside.querySelector(".fc-composer") as El).hidden, false, where + ": Comment on this change's click opens the composer");
  assert.deepEqual(m.w.hookErrors, []);
}

test("over a failure pane after a content paint, a click on a change card's link or on its Comment on this change says in a row under the card that the change is not in view and does nothing else; after the next content paint the same clicks act (file-comments.ts, #cardState's doc and notInView)", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
  const m = await roadStart(t, "text", "painted");
  await m.pane();
  await clicksSayNotInView(m, "over the pane");
  await m.land();                                          // the same bytes land and paint
  await clicksAct(m, "after the paint");
});

test("in a press window, the Source view having marked the changes and a press of the Source toggle having put up a picture still loading, a click on the link or on Comment on this change says the change is not in view and does nothing else; after the Source view's next paint the same clicks act (file-comments.ts, #cardState's doc and notInView)", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
  const m = await roadStart(t, "svg", "source");
  await m.press();
  assert.equal(m.w.ctx.text(), null, "the premise: the press took the Source view's text away, the body holding a picture still loading");
  await clicksSayNotInView(m, "in the press window");
  await m.press(); await m.paint();                        // back to the Source view: its decode's paint
  await clicksAct(m, "after the Source view's paint");
});

test("a deletion's Comment on this change, over a failure pane after a content paint and in a press window, opens the composer by the change's id, as it does whatever the view shows, and puts no row under the card (file-comments.ts, startChangeComment: a deletion has no span, so the not-in-view answer is a spanned change's alone)", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
  const opens = async (m: RoadSeam, where: string): Promise<void> => {
    const aside = m.w.main.querySelector(".fileview-aside")!;
    const c = act(card(aside, "chg:h3")!, "fcchangecomment", "h3");
    assert.ok(c, where + ": the premise: the deletion's card offers Comment on this change");
    const posted = m.w.posted.length;
    c!.click(); await flush(); await flush();
    assert.equal((aside.querySelector(".fc-composer") as El).hidden, false, where + ": the click opens the composer");
    const ref = aside.querySelector(".fc-composer-ref")!.textContent!;
    assert.ok(ref.startsWith("About the change") && ref.includes("the comment names the change instead of a passage"), where + ": by the change's id, not a passage cut from the text: " + JSON.stringify(ref));
    assert.deepEqual(rowsUnderCard(m, "h3"), [], where + ": no row under the deletion's card");
    assert.equal(m.w.posted.length, posted, where + ": and no request");
    assert.deepEqual(m.w.hookErrors, []);
  };
  const p = await roadStart(t, "text", "painted");
  await p.pane();
  await opens(p, "over the pane");
  p.w.close();
  const q = await roadStart(t, "svg", "source");
  await q.press();
  assert.equal(q.w.ctx.text(), null, "the premise: the press took the Source view's text away");
  await opens(q, "in the press window");
});

test("a comment card's link in a press window or behind the re-ask's loader goes to the passage as goTo does, with no mark of the panel's in the body there: a switch to Raw and a scroll to the passage's offset, and no row anywhere (file-comments.ts, followLink: only a change card's link answers that the change is not in view)", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
  const { NOT_IN_VIEW_LINK, NOT_IN_VIEW_COMMENT } = await import("./file-comments");
  const goes = async (m: RoadSeam, where: string): Promise<void> => {
    const aside = m.w.main.querySelector(".fileview-aside")!;
    const ref = card(aside, passage.id)!.querySelector(".fc-ref")!;
    assert.ok(ref.classes.includes("fc-link"), where + ": the premise: the comment card offers its link, from the Source view's paint");
    const modes = m.w.modes.length, scrolls = m.w.scrolls.length;
    ref.click(); await flush(); await flush();
    assert.deepEqual(m.w.modes.slice(modes), ["raw"], where + ": the link switches to Raw (goTo, then reveal: no mark of the panel's in the body)");
    assert.deepEqual(m.w.scrolls.slice(scrolls), [at("shipping the cache in v1.2")], where + ": and scrolls to the passage's offset");
    const said = Array.from(aside.querySelectorAll(".fc-err")).map((r) => r.childNodes[0].textContent).filter((x) => x === NOT_IN_VIEW_LINK || x === NOT_IN_VIEW_COMMENT);
    assert.deepEqual(said, [], where + ": no row says a change is not in view");
    assert.equal(card(aside, passage.id)!.querySelector(".fc-err"), null, where + ": and none under the comment's card");
    assert.deepEqual(m.w.hookErrors, []);
  };
  const p = await roadStart(t, "svg", "source");
  await p.press();
  await goes(p, "in the press window");
  p.w.close();
  const q = await roadStart(t, "svg", "source");
  await q.press(); await q.loader();
  assert.equal(q.show, "loader", "the premise: the re-ask's loader holds the body");
  await goes(q, "behind the re-ask's loader");
});

test("Show changes inline and the filter flipped in another viewer (the settings signal: saveSettings, then the romp:settings event) move the change cards at the flip as the same click in this panel does; over a failure pane the flip moves no card and the next content paint takes it (file-comments.ts, settingsFlipped; #cardState's doc, event 3)", async (t: TestContext) => {
  const { saveSettings } = await import("./settings");
  const elsewhere = async (patch: { changesInline?: boolean; commentsFilter?: "all" | "comments" | "changes" }): Promise<void> => {
    saveSettings(patch); win.dispatchEvent(new Event("romp:settings")); await flush(); await flush();
  };
  /** The change cards on a road from `start` after `steps`, the world closed after the read. */
  const read = async (st: TestContext, start: RoadStart, steps: (m: RoadSeam) => Promise<void>): Promise<Record<string, CardRead> | null> => {
    const m = await roadStart(st, "text", start);
    await steps(m);
    const cards = changeCards(m.w);
    assert.deepEqual(m.w.hookErrors, []);
    m.w.close();
    return cards;
  };
  /** Comments picked before the first paint, then the paint: the list shows no change card, the marks off. */
  const underComments = async (m: RoadSeam): Promise<void> => { await m.filter("comments"); await m.paint(); assert.equal(card(m.w.main.querySelector(".fileview-aside")!, "chg:h5"), null, "the premise: Comments alone lists no change card"); };
  await t.test("Show changes inline turned off in another viewer over the painted file, read at the flip (the next paint would take it either way)", async (st: TestContext) => {
    st.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
    const shown = await read(st, "painted", async () => { /* the cards as painted */ });
    const clicked = await read(st, "painted", (m) => m.inline());
    assert.notDeepEqual(clicked, shown, "the premise: the click here moves the cards (the marks go off)");
    assert.deepEqual(await read(st, "painted", () => elsewhere({ changesInline: false })), clicked, "at the flip the change cards read as after the same click here");
  });
  await t.test("All picked in another viewer under Comments, a move that turns the marks on", async (st: TestContext) => {
    st.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
    const clicked = await read(st, "unpainted", async (m) => { await underComments(m); await m.filter("all"); });
    assert.ok(clicked && clicked["chg:h5"] && clicked["chg:h5"].link, "the premise: All clicked here lists the change cards with the marks on: " + JSON.stringify(clicked));
    assert.deepEqual(await read(st, "unpainted", async (m) => { await underComments(m); await elsewhere({ commentsFilter: "all" }); }), clicked, "at the flip the change cards read as after the same click here");
  });
  await t.test("the same flips over a failure pane (a control): no card moves at the flip, and the next content paint takes it", async (st: TestContext) => {
    st.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
    const inlineClicked = await read(st, "painted", (m) => m.inline());
    const inline = await read(st, "painted", async (m) => {
      await m.pane();
      const before = changeCards(m.w);
      await elsewhere({ changesInline: false });
      assert.deepEqual(changeCards(m.w), before, "over the pane Show changes inline off from another viewer moves no change card");
      await m.land();
    });
    assert.deepEqual(inline, inlineClicked, "the next content paint takes the flip: the cards read as after the click over the painted file");
    const allClicked = await read(st, "unpainted", async (m) => { await underComments(m); await m.pane(); await m.filter("all"); await m.land(); });
    const all = await read(st, "unpainted", async (m) => {
      await underComments(m); await m.pane();
      await elsewhere({ commentsFilter: "all" });
      const now = changeCards(m.w)!;
      assert.ok(now["chg:h5"] && !now["chg:h5"].link, "over the pane All lists the change cards at once, the list being the filter's own, with the marks still off until the next content paint: " + JSON.stringify(now));
      await m.land();
    });
    assert.deepEqual(all, allClicked, "and the next content paint takes it as it takes the same click here");
    assert.ok(all && all["chg:h5"] && all["chg:h5"].link, "with the marks on");
  });
});

test("the re-ask's loader after a press of the Source toggle, and a landing of another type under the Source view, each putting up something other than the text the Source view marked: a click on the link or on Comment on this change says the change is not in view and does nothing else; the next content paint takes the row (file-comments.ts, #cardState's doc and notInView)", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
  const m = await roadStart(t, "svg", "source");
  await m.press(); await m.loader();                       // the picture the press put up fails, and its address is asked again behind the loader
  assert.equal(m.show, "loader", "the premise: the loader holds the body");
  await clicksSayNotInView(m, "over the loader");
  await m.press(); await m.paint();                        // back to the Source view: its paint
  await clicksAct(m, "after the Source view's paint");
  m.w.close();
  const n = await roadStart(t, "svg", "source");
  await n.landOther();                                     // a landing of another type under the Source view: its picture goes up, still loading
  assert.equal(n.show, "loading", "the premise: the landed picture holds the body");
  await clicksSayNotInView(n, "over the landing's picture");
  await n.paint();                                         // the picture's load, a content paint: the picture marks nothing
  assert.equal(rowUnder(n, "h5"), null, "the picture's load takes the row");
  assert.deepEqual(changeCards(n.w)!["chg:h5"], { tags: [], buttons: ["Accept", "Reject", "Reveal"], reveal: "Show the change in the Raw view", link: false }, "and the card moves there, once: no mark, so a Reveal and no link");
  assert.deepEqual(n.w.hookErrors, []);
});

test("the change list's paragraph groups and its fold are the card state's (file-comments.ts, #cardState's doc): with a change in more paragraphs than the list shows before its fold and the Source view painted, a press of the Source toggle to a picture still loading, or a landing of another type under the Source view with its picture up and still loading, and then a render, or the panel closed and opened with its status re-read unchanged, leaves the cards listed, their titles and the fold row as the paint set them; the picture's load then sets the list as that paint shows it", async (t: TestContext) => {
  const PAINTED = { titles: ["# Report", "## Findings", "We recommend shipping the cache in v1.2."], cards: ["chg:h7", "chg:h1", "chg:h3"], fold: "… 2 more changes" };
  const UP = [["in the press window", "the press put up a picture still loading"], ["over the landing's picture", "a landing of another type put its picture up still loading, the Source view gone"]];
  for (const [where, premise] of UP) for (const gesture of ["a render", "the panel re-opened"]) await t.test(gesture + " " + where, async (st: TestContext) => {
    st.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
    const m = await roadStart(st, "svg", "source", statusMany());
    assert.deepEqual(changeList(m.w), PAINTED, gesture + " " + where + ": the premise: over the Source view's text the list shows three paragraph groups and folds the other two");
    if (where === "in the press window") await m.press(); else await m.landOther();
    assert.equal(m.w.ctx.mode(), "media", gesture + " " + where + ": the premise: " + premise + ", mode() media");
    if (gesture === "a render") await m.render();
    else { await m.close(); await m.open(); await m.reread(); }
    assert.deepEqual(changeList(m.w), PAINTED, gesture + " " + where + ": the same cards, titles and fold row as at the Source view's paint (#cardState's doc)");
    await m.paint();                                       // the picture's load, a content paint of a picture: no paragraphs
    assert.deepEqual(changeList(m.w), { titles: [], cards: ["chg:h7", "chg:h1", "chg:h3", "chg:h9", "chg:h5"], fold: null }, gesture + " " + where + ": at the picture's load the list is the picture's: every card in one group with no title, and no fold row");
    assert.deepEqual(m.w.hookErrors, []);
    m.w.close();
  });
});

test("a row saying a change is not in view goes with its change (file-comments.ts, notInView and retireViewRows): over a failure pane after a content paint, the insertion's link clicked puts the row under its card; a status that differs and still lists the change leaves the row there; a status that no longer lists it leaves no such row anywhere in the list, and a later status that lists it again brings no row back", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
  const { NOT_IN_VIEW_LINK, NOT_IN_VIEW_COMMENT } = await import("./file-comments");
  const m = await roadStart(t, "text", "painted");
  const aside = m.w.main.querySelector(".fileview-aside")!;
  const rowsSaid = (): string[] => Array.from(aside.querySelectorAll(".fc-err")).map((r) => r.childNodes[0].textContent!).filter((x) => x === NOT_IN_VIEW_LINK || x === NOT_IN_VIEW_COMMENT);
  await m.pane();
  card(aside, "chg:h5")!.querySelector(".fc-ref")!.click(); await flush(); await flush();
  assert.equal(rowUnder(m, "h5"), NOT_IN_VIEW_LINK, "the premise: the row under the insertion's card says the change is not in view");
  await m.status(S5_STATUS());                             // the sidecar moved and the insertion still pending, the pane still up
  assert.equal(rowUnder(m, "h5"), NOT_IN_VIEW_LINK, "a status that still lists the change leaves its row under the card");
  await m.status(statusF1({ storeMtimeNs: S12, hunks: [h1, h3] }));   // the insertion decided in another client: the sidecar moved again, the pane still up
  assert.equal(card(aside, "chg:h5"), null, "the status takes the insertion's card away");
  assert.deepEqual(rowsSaid(), [], "and its row with it: no row in the list says a change is not in view");
  await m.status(statusF1({ storeMtimeNs: S22 }));         // a later status lists the insertion again, the pane still up
  assert.ok(card(aside, "chg:h5"), "the insertion's card is back");
  assert.equal(rowUnder(m, "h5"), null, "with no row under it: the row went at the status, not merely out of sight");
  assert.deepEqual(rowsSaid(), [], "and none elsewhere");
  assert.deepEqual(m.w.hookErrors, []);
});

/** The insertion made detached: the sidecar keeps its op, at its last place, with `detached: true` (as D1 above). */
const H5_DETACHED = { id: "h5", author: "api", authorId: SID, ts: T0 - 50000, kind: "ins", from: h5.curFrom, oldText: "", newText: " again", anchor: null, detached: true };

test("a row saying a change is not in view shows only under its card (file-comments.ts, notInView, strayRows and retireViewRows): over a failure pane after a content paint, with the insertion's link clicked, Comments alone shows no such row and All brings the card back with the row under it; the fold closed over the card shows no such row, and opened again brings the card back with it; a status that lists the change detached takes the row away", async (t: TestContext) => {
  const { NOT_IN_VIEW_LINK, NOT_IN_VIEW_COMMENT } = await import("./file-comments");
  const rowsSaid = (m: RoadSeam): string[] => Array.from(m.w.main.querySelector(".fileview-aside")!.querySelectorAll(".fc-err")).map((r) => r.childNodes[0].textContent!).filter((x) => x === NOT_IN_VIEW_LINK || x === NOT_IN_VIEW_COMMENT);
  const linkOverPane = async (m: RoadSeam): Promise<void> => {
    await m.pane();
    card(m.w.main.querySelector(".fileview-aside")!, "chg:h5")!.querySelector(".fc-ref")!.click(); await flush(); await flush();
    assert.equal(rowUnder(m, "h5"), NOT_IN_VIEW_LINK, "the premise: over the pane the link's click puts the row under the insertion's card");
  };
  await t.test("Comments alone, then All", async (st: TestContext) => {
    st.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
    const m = await roadStart(st, "text", "painted");
    const aside = m.w.main.querySelector(".fileview-aside")!;
    await linkOverPane(m);
    await m.filter("comments");
    assert.equal(card(aside, "chg:h5"), null, "the premise: Comments alone lists no change card");
    assert.deepEqual(rowsSaid(m), [], "Comments alone over the pane: no row in the list says a change is not in view, its card hidden (notInView)");
    await m.filter("all");
    assert.equal(rowUnder(m, "h5"), NOT_IN_VIEW_LINK, "All brings the card back with its row under it");
    assert.deepEqual(rowsSaid(m), [NOT_IN_VIEW_LINK], "and that row alone");
    assert.deepEqual(m.w.hookErrors, []);
    m.w.close();
  });
  await t.test("the fold closed over the card, then opened", async (st: TestContext) => {
    st.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
    const m = await roadStart(st, "text", "painted", statusMany());
    const aside = m.w.main.querySelector(".fileview-aside")!;
    act(aside, "fcmore")!.click(); await flush();
    assert.ok(card(aside, "chg:h5"), "the premise: the fold opened lists the insertion's card");
    await linkOverPane(m);
    act(aside, "fcmore")!.click(); await flush();
    assert.equal(card(aside, "chg:h5"), null, "the premise: the fold closed hides the insertion's card");
    assert.deepEqual(rowsSaid(m), [], "the fold closed over the card: no row in the list says a change is not in view (notInView)");
    act(aside, "fcmore")!.click(); await flush();
    assert.equal(rowUnder(m, "h5"), NOT_IN_VIEW_LINK, "the fold opened again brings the card back with its row under it");
    assert.deepEqual(m.w.hookErrors, []);
    m.w.close();
  });
  await t.test("a status that lists the change detached", async (st: TestContext) => {
    st.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
    const m = await roadStart(st, "text", "painted");
    const aside = m.w.main.querySelector(".fileview-aside")!;
    await linkOverPane(m);
    await m.status(statusF1({ storeMtimeNs: S12, hunks: [h1, h3], store: { ...NO_COMMENTS, comments: [passage], detached: [H5_DETACHED] } }));   // the insertion's text gone from the file, its op kept detached; the pane still up
    const d = card(aside, "chg:h5");
    assert.ok(d && d.classes.includes("fc-card-detached") && !isLink(d) && !act(d, "fcchangecomment"), "the premise: the insertion's card is listed detached, with no link and no Comment on this change");
    assert.deepEqual(rowsSaid(m), [], "the status takes the row away: a detached change can have no link or Comment on this change (retireViewRows)");
    assert.deepEqual(m.w.hookErrors, []);
    m.w.close();
  });
});

/** The insertion's Accept, refused by the host `no-change` (another client decided it first): the refusal's row goes in the slot a
 *  decision's row uses under the card. Returns the refusal's words; asserts that the refused decision asks no status (no-change is
 *  none of MOVED's codes). */
async function refusedAccept(m: RoadSeam): Promise<string> {
  const words = "no pending change h5 in docs/report.md";
  const asks = countOf(m.w, "fileComments", "status");
  act(card(m.w.main.querySelector(".fileview-aside")!, "chg:h5")!, "fcaccept", "h5")!.click(); await flush(); await flush();
  const sent = lastOf(m.w, "fileComments", "accept");
  assert.ok(sent, "the premise: the Accept went out");
  refuse(m.w, sent, "no-change", words); await flush(); await flush();
  assert.equal(countOf(m.w, "fileComments", "status"), asks, "the refused decision asks no status (no-change is not a moved fence)");
  return words;
}

test("a decision refused on a card whose row says the change is not in view, over a failure pane after a content paint: the refusal stands beside that row, the next content paint takes the not-in-view row and leaves the refusal, which stands until the person dismisses it (file-comments.ts, notInView's own slot; the paint's retire in #latchCardState)", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
  const { NOT_IN_VIEW_LINK } = await import("./file-comments");
  const m = await roadStart(t, "text", "painted");
  await m.pane();
  card(m.w.main.querySelector(".fileview-aside")!, "chg:h5")!.querySelector(".fc-ref")!.click(); await flush(); await flush();
  assert.deepEqual(rowsUnderCard(m, "h5"), [["view:h5", NOT_IN_VIEW_LINK]], "the premise: the not-in-view row under the insertion's card");
  const words = await refusedAccept(m);
  assert.deepEqual(rowsUnderCard(m, "h5"), [["change:h5", words], ["view:h5", NOT_IN_VIEW_LINK]], "the refusal and the not-in-view row both show, each in its own slot");
  await m.land();                                          // the next content paint
  assert.deepEqual(rowsUnderCard(m, "h5"), [["change:h5", words]], "the paint takes the not-in-view row and leaves the refusal");
  await m.render(); await m.status(S5_STATUS());
  assert.deepEqual(rowsUnderCard(m, "h5"), [["change:h5", words]], "the refusal stands through a render and a status that still lists the change");
  card(m.w.main.querySelector(".fileview-aside")!, "chg:h5")!.querySelector('.fc-err[data-slot="change:h5"] [data-act="fcerrx"]')!.click(); await flush();
  assert.deepEqual(rowsUnderCard(m, "h5"), [], "until the person dismisses it");
  assert.deepEqual(m.w.hookErrors, []);
});

test("a decision refused on a card whose row says the change is not in view, then a status that no longer lists the change, the pane still up: the not-in-view row goes with the change, and the refusal stands as a stray row where the card was (file-comments.ts, retireViewRows and strayRows)", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
  const { NOT_IN_VIEW_LINK, NOT_IN_VIEW_COMMENT } = await import("./file-comments");
  const m = await roadStart(t, "text", "painted");
  const aside = m.w.main.querySelector(".fileview-aside")!;
  await m.pane();
  card(aside, "chg:h5")!.querySelector(".fc-ref")!.click(); await flush(); await flush();
  const words = await refusedAccept(m);
  await m.status(statusF1({ storeMtimeNs: S12, hunks: [h1, h3] }));   // the insertion decided in another client: the sidecar moved, the pane still up
  assert.equal(card(aside, "chg:h5"), null, "the premise: the status takes the insertion's card away");
  const rows = Array.from(aside.querySelectorAll(".fc-err")).map((r) => [r.getAttribute("data-slot"), r.childNodes[0].textContent]);
  assert.deepEqual(rows.filter(([, x]) => x === NOT_IN_VIEW_LINK || x === NOT_IN_VIEW_COMMENT), [], "no row says the change is not in view");
  assert.deepEqual(rows.filter(([slot]) => slot === "change:h5"), [["change:h5", words]], "the refusal stands, a stray row in the list");
  assert.deepEqual(m.w.hookErrors, []);
});

test("a refusal standing under a card, then over a failure pane that card's link, or a spanned change's Comment on this change, clicked: both rows show, the refusal's words unchanged, and the next content paint takes the not-in-view row and leaves the refusal (file-comments.ts, notInView's own slot)", async (t: TestContext) => {
  const { NOT_IN_VIEW_LINK, NOT_IN_VIEW_COMMENT } = await import("./file-comments");
  for (const [what, said] of [["the link", NOT_IN_VIEW_LINK], ["Comment on this change", NOT_IN_VIEW_COMMENT]] as const) await t.test(what, async (st: TestContext) => {
    st.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
    const m = await roadStart(st, "text", "painted");
    const words = await refusedAccept(m);
    assert.deepEqual(rowsUnderCard(m, "h5"), [["change:h5", words]], "the premise: the refusal stands under the insertion's card");
    await m.pane();
    const c = card(m.w.main.querySelector(".fileview-aside")!, "chg:h5")!;
    if (what === "the link") c.querySelector(".fc-ref")!.click(); else act(c, "fcchangecomment", "h5")!.click();
    await flush(); await flush();
    assert.deepEqual(rowsUnderCard(m, "h5"), [["change:h5", words], ["view:h5", said]], what + " over the pane: both rows show, the refusal's words unchanged");
    await m.land();                                        // the next content paint
    assert.deepEqual(rowsUnderCard(m, "h5"), [["change:h5", words]], "the paint takes the not-in-view row and leaves the refusal");
    assert.deepEqual(m.w.hookErrors, []);
    m.w.close();
  });
});

test("the not-in-view words go into the panel's one live region (file-comments.ts, notInView, speak and hush): made once, role status and polite, carrying the class fc-live, whose rule in both sheets (styles.css, feed.css) hides it from sight as the settings sheet's .rs-live does (absolute, 1px by 1px, overflow hidden, clipped), the same node through renders and a close and open; at each click on the link or on Comment on this change, over a failure pane and in a press window, it holds nothing at the end of the click's task and the words after the next animation frame, a second identical press included; the content paint empties it, and so do a status that drops the change and the row's dismiss when the row they take is the one the region speaks for, words still waiting for their frame dropped at each of the three; another card's row going, or a refusal's row dismissed, leaves the last click's words, landed or waiting for their frame; and the viewer's close drops a frame still pending (the sequence is what is pinned: the technique used so screen readers announce repeated text; the announcement itself was not measured with a screen reader)", async (t: TestContext) => {
  const { NOT_IN_VIEW_LINK, NOT_IN_VIEW_COMMENT } = await import("./file-comments");
  // the rule's text in both sheets, as widget-reorder.test.ts pins .rs-live's (a source pin, since the node leg lays nothing out),
  // and no other line of either sheet names the class
  for (const sheet of ["styles.css", "feed.css"])
    assert.deepEqual(fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", sheet), "utf8").split("\n").filter((l) => l.includes(".fc-live")),
      [".fc-live { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }"],
      sheet + "'s one .fc-live rule hides the region from sight (absolute, 1px by 1px, overflow hidden, clipped, as gear.css's .rs-live), since the row under the card already shows the words");
  const frames = new Map<number, () => void>(); let fid = 0;
  const g = globalThis as { requestAnimationFrame?: unknown; cancelAnimationFrame?: unknown };
  const had = { raf: g.requestAnimationFrame, caf: g.cancelAnimationFrame };
  g.requestAnimationFrame = (cb: () => void): number => { frames.set(++fid, cb); return fid; };
  g.cancelAnimationFrame = (id: number): void => { frames.delete(id); };
  t.after(() => { g.requestAnimationFrame = had.raf; g.cancelAnimationFrame = had.caf; });
  const frame = (): void => { const due = [...frames.values()]; frames.clear(); for (const cb of due) cb(); };
  const region = (m: RoadSeam): El => { const r = m.w.main.querySelectorAll(".fileview-aside .fc-live"); assert.equal(r.length, 1, "one live region in the panel"); return r[0]; };
  const click = async (m: RoadSeam, what: "link" | "comment", id = "h5"): Promise<void> => {
    const c = card(m.w.main.querySelector(".fileview-aside")!, "chg:" + id)!;
    if (what === "link") c.querySelector(".fc-ref")!.click(); else act(c, "fcchangecomment", id)!.click();
  };
  const says = async (m: RoadSeam, what: "link" | "comment", where: string, id = "h5"): Promise<void> => {
    await click(m, what, id);
    assert.equal(region(m).textContent, "", where + ", " + what + ": the region holds nothing at the end of the click's task");
    await flush(); await flush();
    frame();
    assert.equal(region(m).textContent, what === "link" ? NOT_IN_VIEW_LINK : NOT_IN_VIEW_COMMENT, where + ", " + what + ": the words after the next animation frame");
  };
  /** The link clicked again over the pane, its words waiting for their frame: the region empty, and one frame pending. */
  const again = async (m: RoadSeam, id = "h5"): Promise<void> => {
    frames.clear();
    await click(m, "link", id); await flush(); await flush();
    assert.deepEqual([region(m).textContent, frames.size], ["", 1], "the premise: the click's words wait for their frame, the one frame pending");
  };
  const dismiss = async (m: RoadSeam, slot: string): Promise<void> => { m.w.main.querySelector('.fileview-aside .fc-err[data-slot="' + slot + '"] [data-act="fcerrx"]')!.click(); await flush(); };
  await t.test("over a failure pane", async (st: TestContext) => {
    st.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
    const m = await roadStart(st, "text", "painted");
    const live = region(m);
    assert.deepEqual([live.getAttribute("role"), live.getAttribute("aria-live"), live.classes.includes("fc-live"), live.textContent], ["status", "polite", true, ""], "role status, polite, the class fc-live (its rule is pinned in both sheets above), empty");
    assert.equal(live.closest(".fc-card"), null, "in no card: the panel's own element");
    await m.pane();
    await says(m, "link", "over the pane");
    await says(m, "link", "over the pane, a second identical press");
    await says(m, "comment", "over the pane");
    const row = card(m.w.main.querySelector(".fileview-aside")!, "chg:h5")!.querySelector('.fc-err[data-slot="view:h5"]')!;
    assert.deepEqual([row.getAttribute("role"), row.getAttribute("aria-live")], [null, null], "the row under the card, rebuilt at every render, carries no role");
    await m.render();
    assert.equal(region(m), live, "the same node after a render");
    await m.close(); await m.open(); await m.reread();
    assert.equal(region(m), live, "and after the panel closes and opens");
    await m.land();                                          // the next content paint
    assert.equal(live.textContent, "", "the content paint empties it");
    await click(m, "link");                                  // over the painted text: the link acts, and says nothing
    frame();
    assert.equal(live.textContent, "", "a link that acts says nothing");
    await m.pane();
    await click(m, "link");
    await m.land();                                          // the paint comes before the frame
    frame();
    assert.equal(live.textContent, "", "words still waiting for their frame when the content paint comes are dropped");
    assert.deepEqual(m.w.hookErrors, []);
    m.w.close();
  });
  await t.test("in a press window", async (st: TestContext) => {
    st.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
    const m = await roadStart(st, "svg", "source");
    await m.press();
    await says(m, "link", "in the press window");
    await says(m, "comment", "in the press window");
    await says(m, "comment", "in the press window, a second identical press");
    await m.press(); await m.paint();                        // back to the Source view: its decode's paint
    assert.equal(region(m).textContent, "", "the Source view's paint empties it");
    assert.deepEqual(m.w.hookErrors, []);
    m.w.close();
  });
  await t.test("a status that drops the change", async (st: TestContext) => {
    st.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
    const m = await roadStart(st, "text", "painted");
    await m.pane();
    await says(m, "link", "over the pane");
    await m.status(S5_STATUS());
    assert.equal(region(m).textContent, NOT_IN_VIEW_LINK, "a status that still lists the change leaves the words");
    await m.status(statusF1({ storeMtimeNs: S12, hunks: [h1, h3] }));   // the insertion decided in another client
    assert.equal(region(m).textContent, "", "a status that drops the change empties it, with the row (retireViewRows)");
    assert.deepEqual(m.w.hookErrors, []);
    m.w.close();
  });
  await t.test("a status that drops the change while its words wait for their frame", async (st: TestContext) => {
    st.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
    const m = await roadStart(st, "text", "painted");
    await m.pane();
    await says(m, "link", "over the pane");
    await again(m);
    await m.status(statusF1({ storeMtimeNs: S12, hunks: [h1, h3] }));   // the insertion decided in another client, before the frame
    frame();
    assert.equal(region(m).textContent, "", "words still waiting for their frame when a status drops the change are dropped with the row (retireViewRows)");
    assert.deepEqual(m.w.hookErrors, []);
    m.w.close();
  });
  await t.test("the row's dismiss", async (st: TestContext) => {
    st.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
    const m = await roadStart(st, "text", "painted");
    await m.pane();
    await says(m, "link", "over the pane");
    await dismiss(m, "view:h5");
    assert.equal(region(m).textContent, "", "the row's dismiss empties it");
    assert.deepEqual(rowsUnderCard(m, "h5"), [], "and the row is gone");
    await again(m);                                          // the row back, its words waiting for their frame
    await dismiss(m, "view:h5");                             // dismissed before the frame
    frame();
    assert.equal(region(m).textContent, "", "words still waiting for their frame when the row is dismissed are dropped with it");
    assert.deepEqual(m.w.hookErrors, []);
    m.w.close();
  });
  await t.test("a refusal's row dismissed while the not-in-view row stands, the words landed or waiting for their frame", async (st: TestContext) => {
    st.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
    const m = await roadStart(st, "text", "painted");
    const words = await refusedAccept(m);
    await m.pane();
    await says(m, "link", "over the pane");
    assert.deepEqual(rowsUnderCard(m, "h5"), [["change:h5", words], ["view:h5", NOT_IN_VIEW_LINK]], "the premise: the refusal and the not-in-view row both show");
    await dismiss(m, "change:h5");
    assert.equal(region(m).textContent, NOT_IN_VIEW_LINK, "dismissing the refusal's row leaves the region's words: the row they are for still shows");
    assert.deepEqual(rowsUnderCard(m, "h5"), [["view:h5", NOT_IN_VIEW_LINK]], "and that row stands");
    assert.deepEqual(m.w.hookErrors, []);
    m.w.close();
    const p = await roadStart(st, "text", "painted");
    const refused = await refusedAccept(p);
    await p.pane();
    await again(p);                                          // the click's words waiting for their frame
    assert.deepEqual(rowsUnderCard(p, "h5"), [["change:h5", refused], ["view:h5", NOT_IN_VIEW_LINK]], "the premise: the refusal and the not-in-view row both show, the words waiting for their frame");
    await dismiss(p, "change:h5");                           // dismissed before the frame
    assert.deepEqual([region(p).textContent, frames.size], ["", 1], "dismissing the refusal's row before the frame leaves the words waiting for it, the one frame still pending");
    frame();
    assert.equal(region(p).textContent, NOT_IN_VIEW_LINK, "and the words land after the frame: the row they are for still shows");
    assert.deepEqual(rowsUnderCard(p, "h5"), [["view:h5", NOT_IN_VIEW_LINK]], "and that row stands");
    assert.deepEqual(p.w.hookErrors, []);
    p.w.close();
  });
  await t.test("two rows: another card's row going leaves the last click's words, landed or waiting for their frame; the row the region speaks for takes them, waiting or landed", async (st: TestContext) => {
    st.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
    const DROP_H1 = (): Status => statusF1({ storeMtimeNs: S12, hunks: [h3, h5] });   // the substitution decided in another client
    const DROP_H5 = (): Status => statusF1({ storeMtimeNs: S12, hunks: [h1, h3] });   // the insertion decided in another client
    /** Over a pane, h1's Comment on this change said and its words landed, then h5's link clicked, its words waiting for their frame. */
    const twoRows = async (): Promise<RoadSeam> => {
      const m = await roadStart(st, "text", "painted");
      await m.pane();
      await says(m, "comment", "over the pane, h1", "h1");
      await again(m, "h5");
      assert.deepEqual([rowsUnderCard(m, "h1"), rowsUnderCard(m, "h5")], [[["view:h1", NOT_IN_VIEW_COMMENT]], [["view:h5", NOT_IN_VIEW_LINK]]], "the premise: a row under each card");
      return m;
    };
    const done = (m: RoadSeam): void => { assert.deepEqual(m.w.hookErrors, []); m.w.close(); };
    let m = await twoRows();
    await m.status(DROP_H1());
    frame();
    assert.equal(region(m).textContent, NOT_IN_VIEW_LINK, "a status that drops h1 between h5's click and its frame leaves that click's sequence: h5's words land after the frame");
    assert.deepEqual([rowsUnderCard(m, "h5"), card(m.w.main.querySelector(".fileview-aside")!, "chg:h1")], [[["view:h5", NOT_IN_VIEW_LINK]], null], "h5's row stands, h1's card gone with its row");
    done(m);
    m = await twoRows();
    await dismiss(m, "view:h1");
    frame();
    assert.equal(region(m).textContent, NOT_IN_VIEW_LINK, "h1's row dismissed between h5's click and its frame: h5's words land after the frame");
    done(m);
    m = await twoRows();
    frame();
    await m.status(DROP_H1());
    assert.equal(region(m).textContent, NOT_IN_VIEW_LINK, "a status that drops h1 after h5's words landed leaves them");
    done(m);
    m = await twoRows();
    frame();
    await dismiss(m, "view:h1");
    assert.equal(region(m).textContent, NOT_IN_VIEW_LINK, "h1's row dismissed after h5's words landed leaves them");
    done(m);
    m = await twoRows();
    await m.status(DROP_H5());
    frame();
    assert.equal(region(m).textContent, "", "a status that drops h5 while its words wait drops them");
    assert.deepEqual(rowsUnderCard(m, "h1"), [["view:h1", NOT_IN_VIEW_COMMENT]], "h1's row still standing");
    done(m);
    m = await twoRows();
    await dismiss(m, "view:h5");
    frame();
    assert.equal(region(m).textContent, "", "h5's row dismissed while its words wait: dropped, h1's row still standing");
    done(m);
    m = await twoRows();
    frame();
    await m.status(DROP_H5());
    assert.equal(region(m).textContent, "", "a status that drops h5 after its words landed empties the region, h1's row still standing");
    done(m);
    m = await twoRows();
    frame();
    await dismiss(m, "view:h5");
    assert.equal(region(m).textContent, "", "h5's row dismissed after its words landed: emptied, h1's row still standing");
    done(m);
  });
  await t.test("the viewer closed while the words wait for their frame", async (st: TestContext) => {
    st.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
    const m = await roadStart(st, "text", "painted");
    await m.pane();
    const live = region(m);
    await again(m);
    m.w.close();                                             // the viewer's close: the seam's onClose, the panel's dispose
    assert.equal(frames.size, 0, "no frame of the panel's stays pending after the close, so the scheduler holds nothing that reaches the panel");
    frame();
    assert.equal(live.textContent, "", "and nothing is written into the closed panel's region");
  });
});

test("a status that arrives while the body shows its last content paint and mtimeNs() has moved on (an svg's reload landing under its Source view, or while a press to the Source view waits for its decode) is read against that paint's mtime (file-comments.ts, #cardState's doc): the card at the status, for the landed bytes and for the painted bytes whose sidecar moved, then at the decode", async (t: TestContext) => {
  const MARKED = { tags: [], buttons: ["Accept", "Reject", "Comment on this change"], reveal: null, link: true };
  const BARE = { tags: [], buttons: ["Accept", "Reject"], reveal: null, link: false };
  const land11 = async (m: RoadSeam): Promise<void> => { m.out = { text: DOC11, mt: F11 }; await m.land(); assert.equal(m.w.ctx.mtimeNs(), F11, "the premise: mtimeNs() is the landed bytes' and no paint of them has come"); };
  await t.test("the Source view marked, newer bytes landing under it with the decode out, and the status for those bytes", async (st: TestContext) => {
    st.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
    const m = await roadStart(st, "svg", "source");
    assert.deepEqual(changeCards(m.w)!["chg:h5"], MARKED, "the premise: the Source view marks the insertion");
    await land11(m);
    await m.status(statusF11());
    assert.deepEqual(changeCards(m.w)!["chg:h5"], BARE, "the status for the landed bytes over the older XML: no not shown tag, no Comment on this change, no Reveal and no link (#cardState's doc)");
    assert.equal(marksOf(m.w).length, 0, "and no change marked over the older XML");
    await m.paint();                                       // the decode's paint of the landed bytes
    assert.deepEqual(changeCards(m.w)!["chg:h5"], MARKED, "at the decode's paint the insertion is marked over the landed XML");
    assert.deepEqual(m.w.hookErrors, []);
  });
  await t.test("the same with a status for the painted bytes whose sidecar moved", async (st: TestContext) => {
    st.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
    const m = await roadStart(st, "svg", "source");
    await land11(m);
    await m.status(S5_STATUS());
    assert.deepEqual(changeCards(m.w)!["chg:h5"], MARKED, "the status for the painted bytes over their XML: the insertion's card keeps its mark, Comment on this change and the link (#cardState's doc)");
    assert.equal(marksOf(m.w, "h5").length, 1, "and the insertion's mark over the XML the status indexes");
    await m.paint();                                       // the decode's paint of the landed bytes, which that status does not index
    assert.deepEqual(changeCards(m.w)!["chg:h5"], BARE, "at the decode's paint the card gives them up");
    assert.deepEqual(m.w.hookErrors, []);
  });
  await t.test("an svg's picture, a press to the Source view waiting for its decode, newer bytes landing then, and their status", async (st: TestContext) => {
    st.mock.timers.enable({ apis: ["setTimeout", "setInterval"] });
    const m = await roadStart(st, "svg", "painted");
    assert.deepEqual(changeCards(m.w)!["chg:h5"], { tags: [], buttons: ["Accept", "Reject", "Reveal"], reveal: "Show the change in the Raw view", link: false }, "the premise: the picture marks nothing, so a Reveal");
    await m.press();
    assert.equal(m.decoding, true, "the premise: the press waits for its decode, the picture still up");
    await land11(m);
    await m.status(statusF11());
    assert.deepEqual(changeCards(m.w)!["chg:h5"], BARE, "the status for the landed bytes over the picture: no Reveal (#cardState's doc)");
    await m.paint();                                       // the decode's paint
    assert.deepEqual(changeCards(m.w)!["chg:h5"], MARKED, "at the decode's paint the insertion is marked over the landed XML");
    assert.deepEqual(m.w.hookErrors, []);
  });
});

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
  // the file's own Ev hides target and currentTarget the same way (hideEdges(this) at the end of its constructor)
  assertHiddenEvent(new Ev("click"), root, kid);
});
