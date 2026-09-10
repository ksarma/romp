// The marks' drag guard is judged against the CLICKED mark, not the whole body (plans/file-review.md, Slice 2, the marks'
// click rule; the review of 2026-09-09 of the fix of that day; file-comments.ts dragClick and endInside). The first guard
// read any non-collapsed selection with both ends in the body as this click's drag, so a click on a control whose press
// cannot collapse a standing selection was dropped while words stood selected anywhere in the body: a deletion's struck
// label (`span.fc-del`, user-select: none, its text CSS-generated, so its press touches no selection), a region
// rectangle (the overlay cancels its pointerdown), a mark inside an author's link, a framed picture — verified with a
// real mouse in Chromium and Firefox, Rendered and Raw, on origin/main's behaviour too, where every such click opened
// its card. The guard now asks whether the selection's anchor and focus both lie inside the control the click landed on
// (the target's nearest data-act, the element the delegate routed): a drag begun and ended inside one mark puts both
// ends there; a selection standing elsewhere, or one that merely spans the mark from outside, has none, and its click
// opens the card whatever stands selected. An engine may report a drag's end at the mark's edge as a point in the mark's
// parent (at the mark's index, or the next) or in the neighbouring text node (its end, or the next one's start) rather
// than in the mark, and the guard takes those as the mark's (endInside). The click the guard stands down also SHOWS
// nothing: the delegate's press pulse (actions.ts flash, `.romp-acted`, added before the handler runs) comes off in the
// same task, as render.ts's once() does for a swallowed repeat. With the panel CLOSED the marks are painted too, and a
// drag inside one behaves as a drag over any passage does with the panel closed: no panel opens, no card (the review's
// ruling; the Comment float is a panel-open affordance, the plan's Comment-on-a-selection bullet); a plain click on the
// mark opens the panel and the card as before. Driven over the behavior suite's DOM stand-in (a copy, as every module
// carries: the selection faked per case with the offsets the guard reads, the pointer's click carrying detail 1 as
// browsers dispatch it); file-comments-markclick-controls-browser.test.ts drives a real mouse over the real viewer and
// panel in Chromium and Firefox. Synthetic fixtures only: the notes-api world, placeholder ids.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import { inspect } from "node:util";
import { assertHiddenEvent, hideEdges, staysEnumerable } from "../test-dom-shim";
import type { FileViewActionCtx } from "./file-view";
import type { Status, Hunk, StoreComment } from "./file-comments-model";

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const ROOT = "/repo/notes-api";
const STORE_PATH = ROOT + "/.trackchanges/docs%2Freport.md.json";
const T0 = 1757145600000;
// the CURRENT text: the session's insertion already applied, its deletion already gone (the file on disk reads as if accepted)
const DOC = "# Report\n\n## Findings\nThe api session cut p95 latency by 40% and the p99 by 10%.\n\n"
  + "We recommend shipping the cache in v1.2.\n\nRisks remain in the fallback path.\n\nNext steps: measure again.\n";
const at = (needle: string): number => { const i = DOC.indexOf(needle); assert.ok(i >= 0, needle); return i; };
// the insertion inside the findings line, the deletion at the head of the last line (a point: its label is CSS-generated), and
// a passage comment on the recommendation
const INS = " and the p99 by 10%";
const h2: Hunk = { id: "h2", author: "api", ts: T0 - 80000, kind: "ins", curFrom: at(INS), curTo: at(INS) + INS.length, baseFrom: at(INS), baseTo: at(INS), oldText: "", newText: INS, anchor: null };
const h3: Hunk = { id: "h3", author: "api", ts: T0 - 70000, kind: "del", curFrom: at("Next steps"), curTo: at("Next steps"), baseFrom: at("Next steps"), baseTo: at("Next steps") + 5, oldText: "Some ", newText: "", anchor: null };
const passage: StoreComment = {
  id: T0 + "-118", author: "you", ts: T0, body: "Which cache? Say which.",
  anchor: { quote: "shipping the cache in v1.2", prefix: "We recommend ", suffix: "." }, replies: [], resolved: false,
};
function status(): Status {
  return {
    verb: "status", root: ROOT, storePath: STORE_PATH, trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
    store: { v: 3, path: "docs/report.md", suggestions: [], comments: [passage] },
    hunks: [h2, h3], log: [],
    unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 0, watermark: null },
  };
}

// ── the DOM stand-in (the behavior suite's, with a click's `detail` and the siblings the guard's edge rule reads) ──
class Ev {
  target: El | Txt | null = null;
  currentTarget: El | null = null;
  defaultPrevented = false;
  stopped = false;
  key: string;
  ctrlKey: boolean; metaKey: boolean;
  detail: number;                                  // a click's count: 1 from a pointer, 0 from element.click() and a keyboard activation, as browsers dispatch them
  constructor(public type: string, init: { key?: string; ctrlKey?: boolean; metaKey?: boolean; detail?: number } = {}) { this.key = init.key || ""; this.ctrlKey = !!init.ctrlKey; this.metaKey = !!init.metaKey; this.detail = init.detail ?? 0; hideEdges(this); }
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
  get previousSibling(): El | Txt | null { return sibling(this, -1); }
  get nextSibling(): El | Txt | null { return sibling(this, 1); }
  splitText(off: number): Txt {
    const tail = new Txt(this.data.slice(off));
    this.data = this.data.slice(0, off);
    const p = this.parentNode;
    if (p) { const i = p.childNodes.indexOf(this); p.childNodes.splice(i + 1, 0, tail); tail.parentNode = p; }
    return tail;
  }
}
const sibling = (n: El | Txt, d: number): El | Txt | null => { const p = n.parentNode; if (!p) return null; const i = p.childNodes.indexOf(n); return p.childNodes[i + d] || null; };
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
  get previousSibling(): El | Txt | null { return sibling(this, -1); }
  get nextSibling(): El | Txt | null { return sibling(this, 1); }
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
  set textContent(v: string) { for (const c of this.childNodes) c.parentNode = null; this.childNodes.length = 0; if (v !== "") this.appendChild(new Txt(v)); }
  private detach(n: El | Txt): void { const p = n.parentNode; if (p) { const i = p.childNodes.indexOf(n); if (i >= 0) p.childNodes.splice(i, 1); n.parentNode = null; } }
  appendChild<T extends El | Txt>(n: T): T { this.detach(n); this.childNodes.push(n); n.parentNode = this; return n; }
  insertBefore<T extends El | Txt>(n: T, ref: El | Txt | null): T {
    if (!ref) return this.appendChild(n);
    this.detach(n);
    const i = this.childNodes.indexOf(ref);
    this.childNodes.splice(i < 0 ? this.childNodes.length : i, 0, n); n.parentNode = this; return n;
  }
  removeChild<T extends El | Txt>(n: T): T { this.detach(n); return n; }
  replaceChildren(...c: Array<El | Txt>): void { for (const x of this.childNodes) x.parentNode = null; this.childNodes.length = 0; for (const x of c) this.appendChild(x); }
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

// ── the viewer stand-in: the body row with Raw rows, the seam as closures, a file whose mtime the view tracks ──
type World = {
  ctx: FileViewActionCtx; posted: any[]; main: El; body: El; code: El;
  hooks: { rendered: Array<() => void>; close: Array<() => void> };
  disk: string; diskMtime: string; viewMtime: string; reloads: number; scrolls: number[]; modes: string[];
  mtimes: Record<string, string>;
  setText(src: string): void; close(): void;
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
function world(over: { todoId?: string | null; src?: string } = {}): World {
  const main = new El("div"); main.className = "fileview-main";
  const body = new El("div"); body.className = "fileview-body";
  const wrap = new El("div"); wrap.className = "fileview-code";
  const pre = new El("pre"); pre.className = "fileview-pre fileview-wrap";
  const code = new El("code"); code.className = "hljs";
  pre.appendChild(code); wrap.appendChild(pre);
  body.appendChild(wrap);
  main.appendChild(body);
  let text = over.src ?? DOC;
  const w = {
    posted: [] as any[], main, body, code,
    hooks: { rendered: [] as Array<() => void>, close: [] as Array<() => void> },
    disk: text, diskMtime: "1757145600000000001", viewMtime: "1757145600000000001", reloads: 0, scrolls: [] as number[], modes: [] as string[], mtimes: {} as Record<string, string>,
  } as World;
  rows(code, text);
  w.setText = (s) => { text = s; rows(code, s); for (const cb of w.hooks.rendered) cb(); };
  w.ctx = {
    path: ABS, sid: SID, todoId: over.todoId ?? null,
    body: () => body as unknown as HTMLElement, mode: () => "raw", text: () => text, mtimeNs: () => w.viewMtime, media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [],
    identity: () => ({ name: "api", color: null }),
    onRendered: (cb) => { w.hooks.rendered.push(cb); }, onSelection: () => { /* inert */ },
    onSaved: () => { /* inert */ }, onClose: (cb) => { w.hooks.close.push(cb); },
    post: (m) => { w.posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: () => { /* inert */ }, editing: () => false, setTrackedEdit: () => { /* inert */ }, guardClose: () => { /* inert */ },
    aside: (node) => { main.querySelector(".fileview-aside")?.remove(); if (node) { const n = node as unknown as El; n.classList.add("fileview-aside"); main.appendChild(n); } },
    setMode: (m) => { w.modes.push(m); }, scrollToOffset: (n) => { w.scrolls.push(n); },
    // fetchFile: the bytes and mtime now on disk, repainted, the seam's onRendered fired
    reload: () => { w.reloads++; w.viewMtime = w.diskMtime; w.setText(w.disk); },
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
/** Mount the panel's unit over the stand-in and answer its first status ask: the marks paint with the panel CLOSED (every
 *  status runs paintAll); with `open`, click the unit's button and answer the second ask, so the aside mounts. */
async function mount(w: World, open: boolean, s: Status = status()): Promise<{ unit: El; button: El; aside: El | null }> {
  const fc = await import("./file-comments");
  const unit = fc.fileCommentsAction.mount(w.ctx) as unknown as El;
  const button = unit.childNodes[0] as El;
  answer(w, s); await flush();
  if (open) { button.click(); answer(w, s); await flush(); await flush(); }
  const aside = w.main.querySelector(".fileview-aside");
  assert.equal(!!aside, open, open ? "the panel is mounted beside the body" : "the panel stays closed");
  return { unit, button, aside };
}
const card = (main: El, key: string): El | null => main.querySelector('.fileview-aside .fc-card[data-id="' + key + '"]');
const markOf = (w: World, act: string, id: string): El => {
  const m = w.body.querySelector('[data-act="' + act + '"][data-id="' + id + '"]');
  assert.ok(m, act + " " + id + " is marked in the body");
  return m!;
};

// ── the panel, driven ─────────────────────────────────────────────────────────────────────────────
/** A pointer's click on `el`: detail 1, as a mouse or a finger dispatches it (the stand-in's click() is element.click(), detail 0). */
const mouse = (el: El): void => { dispatch(el, new Ev("click", { detail: 1 })); };
/** What the guard reads of a selection: the ends with their offsets (the offsets carry the edge cases). */
type Sel = { isCollapsed: boolean; anchorNode: El | Txt | null; focusNode: El | Txt | null; anchorOffset?: number; focusOffset?: number } | null;
type Outcome = { open: boolean; scrolled: number; focusMoved: boolean; asides: number; acted: boolean };
/** Mount the panel (open, or closed) over the stand-in, fake the live selection as `selOf` reads it off the clicked mark and
 *  the body, click the mark with the pointer (or activate it by Enter), and read what followed: the card's state, the
 *  scrolls, the focus, the aside count, and whether the clicked node still wears the delegate's press pulse. */
async function press(t: TestContext, act: "fcchange" | "fcopen", id: string, key: string, selOf: (mark: El, body: El) => Sel,
  opts: { via?: "mouse" | "enter"; panel?: "open" | "closed" } = {}): Promise<Outcome> {
  const w = world(); t.after(() => w.close());
  t.after(() => { win.getSelection = () => null; });
  await mount(w, (opts.panel || "open") === "open");
  const mark = markOf(w, act, id);
  const c0 = card(w.main, key);
  assert.equal(!!c0 && c0.classes.includes("open"), false, "the card starts collapsed, or unmounted with the panel");
  win.getSelection = () => selOf(mark, w.body);
  if (opts.via === "enter") mark.focus();
  const scrolls = scrolledInto.length, focus = doc.activeElement;
  if (opts.via === "enter") dispatch(mark, new Ev("keydown", { key: "Enter" }));   // the row's keydown: x.click(), a click with no pointer behind it
  else mouse(mark);
  const acted = mark.classes.includes("romp-acted");   // read in the click's own task: flash's timer runs 280 ms later
  await flush();
  const c = card(w.main, key);
  return { open: !!c && c.classes.includes("open"), scrolled: scrolledInto.length - scrolls, focusMoved: doc.activeElement !== focus, asides: w.main.querySelectorAll(".fileview-aside").length, acted };
}
const rowText = (body: El, starts: string): Txt => {
  const ct = body.querySelectorAll(".fv-ct").find((x) => x.textContent.startsWith(starts));
  assert.ok(ct, "a Raw row starting " + JSON.stringify(starts));
  const words = ct!.childNodes.find((n) => n instanceof Txt) as Txt | undefined;
  assert.ok(words, "the row has words");
  return words!;
};
const firstText = (m: El): Txt => { const n = m.childNodes[0]; assert.ok(n instanceof Txt, "the mark wraps its words"); return n; };
const inMark = (m: El): Sel => ({ isCollapsed: false, anchorNode: firstText(m), focusNode: firstText(m), anchorOffset: 2, focusOffset: 9 });
const caretInMark = (m: El): Sel => ({ isCollapsed: true, anchorNode: firstText(m), focusNode: firstText(m), anchorOffset: 3, focusOffset: 3 });
/** Words selected in another row of the body, none of it in the clicked mark: the state a reader leaves by selecting a
 *  passage to read or copy, or by dropping the Comment float. */
const elsewhere = (m: El, body: El): Sel => { const words = rowText(body, "Risks remain"); assert.ok(!m.contains(words), "the selection stands apart from the mark"); return { isCollapsed: false, anchorNode: words, focusNode: words, anchorOffset: 0, focusOffset: 5 }; };
/** A selection that passes over the mark from outside: its anchor in the row above the mark's, its focus in the row below —
 *  or, for a mark on the last row, three characters into the text after the mark in its own row. */
const spanning = (m: El, body: El): Sel => {
  const rows = body.querySelectorAll(".fv-cl");
  const own = m.closest(".fv-cl")!; const i = rows.indexOf(own);
  const above = rows.slice(0, i).reverse().find((r) => r.textContent !== "")!, below = rows.slice(i + 1).find((r) => r.textContent !== "");
  const a = above.querySelector(".fv-ct")!.childNodes.find((n) => n instanceof Txt) as Txt;
  const f = (below ? below.querySelector(".fv-ct")!.childNodes.find((n) => n instanceof Txt) : m.nextSibling) as Txt | null;
  assert.ok(a && f instanceof Txt && !m.contains(a) && !m.contains(f), "both ends lie outside the mark, around it");
  return { isCollapsed: false, anchorNode: a, focusNode: f, anchorOffset: 2, focusOffset: 3 };
};
/** The mark's place among its parent's children, and the text nodes either side of it (the Raw paint splits the row's text around the mark). */
function around(m: El): { parent: El; index: number; before: Txt; after: Txt } {
  const parent = m.parentNode!; const index = parent.childNodes.indexOf(m);
  const before = parent.childNodes[index - 1], after = parent.childNodes[index + 1];
  assert.ok(before instanceof Txt && after instanceof Txt, "the mark stands between two text nodes of its row");
  return { parent, index, before: before as Txt, after: after as Txt };
}

test("a change mark: a selection standing elsewhere in the body, none of it in the mark, is not this click's drag — the card opens (the blocker: the guard's line is the clicked mark, not the body)", async (t) => {
  const r = await press(t, "fcchange", "h2", "chg:h2", elsewhere);
  assert.equal(r.open, true, JSON.stringify(r));
  assert.ok(r.scrolled > 0, "…and the card's open scrolls the mark into view, as a plain click's does: " + JSON.stringify(r));
});

test("a deletion's point (its label CSS-generated, so its press collapses nothing): the click with a selection standing elsewhere opens its card", async (t) => {
  const w = world(); t.after(() => w.close());
  await mount(w, true);
  const point = markOf(w, "fcchange", "h3");
  assert.ok(point.classes.includes("fc-del") && point.childNodes.length === 0, "a zero-width point, its label in data-fc-text: " + point.className);
  w.close();
  const r = await press(t, "fcchange", "h3", "chg:h3", elsewhere);
  assert.equal(r.open, true, JSON.stringify(r));
  const s = await press(t, "fcchange", "h3", "chg:h3", spanning);
  assert.equal(s.open, true, "a selection that passes over the point from outside is not its drag either: " + JSON.stringify(s));
});

test("a comment highlight: a selection standing elsewhere in the body, or one passing over the highlight from outside, is not its drag — the card opens", async (t) => {
  assert.equal((await press(t, "fcopen", passage.id, passage.id, elsewhere)).open, true, "words selected in another row: the card opens");
  assert.equal((await press(t, "fcopen", passage.id, passage.id, spanning)).open, true, "a selection spanning the highlight from outside: the card opens");
});

test("a change mark: a selection spanning the mark from outside (an end in the row above, one in the row below) is not its drag — the card opens", async (t) => {
  const r = await press(t, "fcchange", "h2", "chg:h2", spanning);
  assert.equal(r.open, true, JSON.stringify(r));
});

test("the drag's own click (both ends inside the mark) still opens nothing: no card, no scroll, no focus change — and no press pulse, taken back in the click's own task", async (t) => {
  const r = await press(t, "fcchange", "h2", "chg:h2", inMark);
  assert.deepEqual(r, { open: false, scrolled: 0, focusMoved: false, asides: 1, acted: false }, JSON.stringify(r));
  const h = await press(t, "fcopen", passage.id, passage.id, inMark);
  assert.deepEqual(h, { open: false, scrolled: 0, focusMoved: false, asides: 1, acted: false }, "the highlight, the same: " + JSON.stringify(h));
  // the control: a click that acts keeps the delegate's acknowledgement on the node it pressed
  const p = await press(t, "fcchange", "h2", "chg:h2", caretInMark);
  assert.equal(p.open, true, "a plain click leaves a caret: the card opens");
  assert.equal(p.acted, true, "…and the pressed node wears the pulse (the acknowledgement rule, ui/CLAUDE.md)");
  const e = await press(t, "fcchange", "h2", "chg:h2", inMark, { via: "enter" });
  assert.equal(e.open, true, "Enter on the focused mark opens the card with the selection standing (detail 0 is never a drag's)");
});

test("a drag's end reported at the mark's edge — in the mark's parent at the mark's index or the next, or in the neighbouring text node at its end or start — is the mark's; one past the edge is not", async (t) => {
  const edge = (pick: (m: El) => { node: El | Txt; offset: number }, end: "anchor" | "focus") => (m: El): Sel => {
    const inside = { node: firstText(m), offset: 2 }; const e = pick(m);
    const a = end === "anchor" ? e : inside, f = end === "focus" ? e : inside;
    return { isCollapsed: false, anchorNode: a.node, focusNode: f.node, anchorOffset: a.offset, focusOffset: f.offset };
  };
  // the parent, at the mark's index (its start) or the next (its end)
  assert.equal((await press(t, "fcchange", "h2", "chg:h2", edge((m) => ({ node: around(m).parent, offset: around(m).index + 1 }), "focus"))).open, false, "focus in the parent just after the mark: the drag's");
  assert.equal((await press(t, "fcchange", "h2", "chg:h2", edge((m) => ({ node: around(m).parent, offset: around(m).index }), "anchor"))).open, false, "anchor in the parent just before the mark (a drag begun at its first character): the drag's");
  assert.equal((await press(t, "fcchange", "h2", "chg:h2", edge((m) => ({ node: around(m).parent, offset: around(m).index + 2 }), "focus"))).open, true, "focus in the parent past the text after the mark: not the mark's, the card opens");
  // the neighbouring text nodes
  assert.equal((await press(t, "fcchange", "h2", "chg:h2", edge((m) => ({ node: around(m).after, offset: 0 }), "focus"))).open, false, "focus at the start of the text node after the mark: the drag's");
  assert.equal((await press(t, "fcchange", "h2", "chg:h2", edge((m) => ({ node: around(m).after, offset: 1 }), "focus"))).open, true, "focus one character into the text after the mark: the drag left the mark, the card opens");
  assert.equal((await press(t, "fcchange", "h2", "chg:h2", edge((m) => ({ node: around(m).before, offset: around(m).before.length }), "anchor"))).open, false, "anchor at the end of the text node before the mark: the drag's");
  assert.equal((await press(t, "fcchange", "h2", "chg:h2", edge((m) => ({ node: around(m).before, offset: around(m).before.length - 1 }), "anchor"))).open, true, "anchor one character before the mark: not the mark's, the card opens");
});

test("with the panel closed the marks are painted, and a drag inside one behaves as a drag over any passage does then: no panel opens, no card; a plain click on the mark opens both", async (t) => {
  const r = await press(t, "fcchange", "h2", "chg:h2", inMark, { panel: "closed" });
  assert.deepEqual(r, { open: false, scrolled: 0, focusMoved: false, asides: 0, acted: false }, JSON.stringify(r));
  const p = await press(t, "fcchange", "h2", "chg:h2", caretInMark, { panel: "closed" });
  assert.equal(p.asides, 1, "the plain click mounts the panel: " + JSON.stringify(p));
  assert.equal(p.open, true, "…and opens the card");
  const d = await press(t, "fcchange", "h3", "chg:h3", elsewhere, { panel: "closed" });
  assert.equal(d.asides === 1 && d.open, true, "the deletion's point with a selection standing elsewhere, panel closed: the panel and the card open: " + JSON.stringify(d));
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
