// The margin layout's DOM half, driven (plans/file-review.md, "The margin-layout follow-on (2026-09-07)"): the real
// panel mounted over a DOM stand-in whose elements report sizes, scroll positions and a computed flex-direction, so
// placeCards, the scroll lock, the fold and edit-mode fallbacks, the foot's move to the footer, the re-layout on
// expand and the centering run as behavior. The pure rule is card-layout.test.ts; the numbers a real engine
// measures are file-comments-margin-browser.test.ts. The stand-in is the behavior test's (ancestry, events with
// capture and bubbling, a small selector engine) plus what this layout reads: getBoundingClientRect from a
// measurement table, scrollTop/scrollHeight/clientHeight, style.setProperty, getComputedStyle, a frame queue and a
// ResizeObserver whose callbacks the test fires. Synthetic fixtures only: the notes-api world, placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx, TrackedEdit } from "./file-view";
import type { Status, StoreComment, Hunk } from "./file-comments-model";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const SRC = web("file-comments.ts");
const CSS = web("styles.css");

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
type Rect = { left: number; top: number; right: number; bottom: number; width: number; height: number };
const R = (left: number, top: number, width: number, height: number): Rect => ({ left, top, width, height, right: left + width, bottom: top + height });
const ZERO = R(0, 0, 0, 0);
/** An element's inline style as the layout writes it: plain properties, and the custom property through setProperty. */
class Style {
  [k: string]: unknown;
  setProperty(k: string, v: string): void { this[k] = v; }
  removeProperty(k: string): void { delete this[k]; }
  getPropertyValue(k: string): string { return typeof this[k] === "string" ? (this[k] as string) : ""; }
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
  style = new Style();
  scrollTop = 0; scrollHeight = 0; clientHeight = 0;
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
  scrollIntoView(): void { scrolledInto.push(this); }
  getBoundingClientRect(): Rect { return cur ? cur.measure(this) : ZERO; }
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
(globalThis as any).fetch = async () => ({ status: 404, headers: { get: () => null }, json: async () => [] });
// the layout's environment: the sheet's verdict on the fold, the frame queue, the observers
let narrow = false;
(globalThis as any).getComputedStyle = (el: El) => ({ flexDirection: el.classList.contains("fileview-main") && narrow ? "column" : "row" });
const frames: Array<() => void> = [];
(globalThis as any).requestAnimationFrame = (cb: () => void): number => { frames.push(cb); return frames.length; };
(globalThis as any).cancelAnimationFrame = (): void => { /* inert */ };
const flush = (): void => { for (const f of frames.splice(0)) f(); };
class RO {
  static all: RO[] = [];
  targets = new Set<El>();
  constructor(public cb: () => void) { RO.all.push(this); }
  observe(t: El): void { this.targets.add(t); }
  unobserve(t: El): void { this.targets.delete(t); }
  disconnect(): void { this.targets.clear(); }
}
(globalThis as any).ResizeObserver = RO;
const resize = (): void => { for (const ro of RO.all) if (ro.targets.size) ro.cb(); };
const realSetInterval = globalThis.setInterval;
(globalThis as any).setInterval = (fn: () => void, ms: number) => { const t = realSetInterval(fn, ms); (t as any).unref?.(); return t; };
const tick = () => new Promise<void>((r) => setImmediate(r));

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const ROOT = "/repo/notes-api";
const T0 = 1757145600000;
const QUOTE = "shipping the cache in v1.2";
// one logical line per row: the rows of the Raw view, each ROW px tall in the measurement table
const DOC = "# Report\n\n## Findings\nThe api session cut p95 latency by 40% and the p99 by 10%.\n\nWe recommend " + QUOTE + ".\n\nMore text here.\n";
const passage: StoreComment = {   // row 5
  id: T0 + "-118", author: "you", ts: T0, body: "Which cache? Say which.",
  anchor: { quote: QUOTE, prefix: "We recommend ", suffix: "." }, replies: [], resolved: false,
};
const replied: StoreComment = {   // row 3
  id: (T0 - 60000) + "-40", author: "you", ts: T0 - 60000, body: "Cut this paragraph; it repeats the summary.",
  anchor: { quote: "The api session cut p95 latency by 40%", prefix: "## Findings\n", suffix: " and the" }, replies: [], resolved: false,
};
const whole: StoreComment = { id: (T0 - 120000) + "-0", author: "you", ts: T0 - 120000, body: "Add a summary at the top.", replies: [], resolved: false };
const detached: StoreComment = {
  id: (T0 - 90000) + "-7", author: "you", ts: T0 - 90000, body: "This claim needs a source.",
  anchor: { quote: "a paragraph the file no longer has", prefix: "", suffix: "" }, replies: [], resolved: false,
};
const hunk: Hunk = { id: "h1", author: "api", ts: T0 - 30000, kind: "ins", curFrom: DOC.indexOf("More"), curTo: DOC.indexOf("More") + 4, baseFrom: DOC.indexOf("More"), baseTo: DOC.indexOf("More"), oldText: "", newText: "More", anchor: null };   // row 7
function status(over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: ROOT, storePath: ROOT + "/.trackchanges/docs%2Freport.md.json", trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
    store: { v: 3, path: "docs/report.md", suggestions: [], comments: [whole, detached, replied, passage] },
    hunks: [hunk], log: [],
    unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 0, watermark: null },
    ...over,
  };
}

// ── the viewer stand-in: the body row with Raw rows, the seam as closures, a measurement table ─────
// Geometry: the body's box is at viewport y=100, BODY_VIEW tall; the track begins OFFSET below the body's top (the
// header stands there); row i's text sits at 100 + ROW·i − scrollTop; a card is CARD tall, OPEN when expanded.
const ROW = 60, OFFSET = 60, CARD = 40, OPEN = 120, BODY_VIEW = 200, CONTENT = 2000;
type World = {
  ctx: FileViewActionCtx; posted: any[]; main: El; body: El; code: El;
  hooks: { rendered: Array<() => void>; close: Array<() => void> };
  editing: boolean;
  measure(el: El): Rect;
  setText(src: string): void; close(): void;
  aside(): El; track(): El; card(key: string): El | null; top(key: string): number | null;
};
let cur: World | null = null;
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
  body.scrollHeight = CONTENT; body.clientHeight = BODY_VIEW;
  const wrap = new El("div"); wrap.className = "fileview-code";
  const pre = new El("pre"); pre.className = "fileview-pre fileview-wrap";
  const code = new El("code"); code.className = "hljs";
  pre.appendChild(code); wrap.appendChild(pre); body.appendChild(wrap); main.appendChild(body);
  doc.body.replaceChildren(main);
  let text = DOC;
  const w = {
    posted: [] as any[], main, body, code, hooks: { rendered: [] as Array<() => void>, close: [] as Array<() => void> }, editing: false,
  } as World;
  rows(code, text);
  w.measure = (el: El): Rect => {
    if (el === body) return R(0, 100, 400, BODY_VIEW);
    if (el.classList.contains("fc-sec-cards")) { el.clientHeight = BODY_VIEW - OFFSET; return R(400, 100 + OFFSET, 340, BODY_VIEW - OFFSET); }
    if (el.classList.contains("fc-card")) return R(412, 0, 316, el.classList.contains("open") ? OPEN : CARD);
    if (el.classList.contains("fc-hl") || el.classList.contains("fc-ins") || el.classList.contains("fc-del")) {
      const row = el.closest(".fv-cl");
      const i = row ? code.querySelectorAll(".fv-cl").indexOf(row) : -1;
      return i < 0 ? ZERO : R(20, 100 + ROW * i - body.scrollTop, 50, 20);
    }
    if (el.parentNode && el.parentNode.classList.contains("fc-cards")) return R(412, 0, 316, 20);   // a loader, a row, a fold button
    return ZERO;
  };
  w.setText = (s) => { text = s; rows(code, s); for (const cb of w.hooks.rendered) cb(); };
  w.ctx = {
    path: ABS, sid: SID, todoId: null,
    body: () => body as unknown as HTMLElement, mode: () => "raw", text: () => text, mtimeNs: () => "1757145600000000001", media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [],
    identity: () => ({ name: "api", color: null }),
    onRendered: (cb) => { w.hooks.rendered.push(cb); }, onSelection: () => { /* inert */ }, onSaved: () => { /* inert */ }, onClose: (cb) => { w.hooks.close.push(cb); },
    post: (m) => { w.posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: () => { /* inert */ }, editing: () => w.editing, setTrackedEdit: (_t: TrackedEdit | null) => { /* inert */ }, guardClose: () => { /* inert */ },   // the viewer's close ask (main, 2026-09-07): the stand-in asks nothing
    aside: (node) => { main.querySelector(".fileview-aside")?.remove(); if (node) { const n = node as unknown as El; n.classList.add("fileview-aside"); main.appendChild(n); } },
    setMode: () => { /* inert */ }, scrollToOffset: () => { /* inert */ }, reload: () => { /* inert */ },
  };
  w.aside = () => main.querySelector(".fileview-aside")!;
  w.track = () => w.aside().querySelector(".fc-sec-cards")!;
  w.card = (key) => w.aside().querySelector('.fc-card[data-id="' + key + '"]');
  w.top = (key) => { const c = w.card(key); const t = c ? c.style.top : undefined; return typeof t === "string" ? parseFloat(t) : null; };
  w.close = () => { for (const cb of w.hooks.close) cb(); if (cur === w) cur = null; };
  cur = w;
  return w;
}
type Posted = Record<string, any>;
async function open(over: Partial<Status> = {}) {
  narrow = false; frames.length = 0; RO.all.length = 0; scrolledInto.length = 0;
  const fc = await import("./file-comments");
  const w = world();
  const unit = fc.fileCommentsAction.mount(w.ctx) as unknown as El;
  const button = unit.childNodes[0] as El;
  const last = (): Posted => w.posted[w.posted.length - 1];
  const reply = async (data: Record<string, unknown>) => { win.dispatchEvent(new MessageEvent("message", { data })); await tick(); await tick(); };
  const ok = (o: Partial<Status> = {}) => reply({ type: "fileCommentsResult", reqId: last().reqId, ...status(o) });
  await ok(over);                                      // the probe's status
  button.click();                                      // open: the aside mounts, the panel re-asks
  await ok(over);
  return { w, fc, button, ok, last };
}
// the desired top of a mark on row i in the track's content: the row's top in the body's content, less the header's height
const desired = (i: number): number => ROW * i - OFFSET;

// ── the layout ─────────────────────────────────────────────────────────────────────────────────────

test("beside the body the aside is the margin layout: the track between the fixed head and footer, the foot in the footer, each marked card level with its mark, the track as tall as the body's content", async () => {
  const { w } = await open();
  const aside = w.aside();
  assert.ok(aside.classList.contains("fc-margin"), "the sheet's margin class is on the aside");
  // the root's children are the five sections as before: head, composer, cards (the track), send, log — the sheet fixes the first two and the last two
  assert.deepEqual(aside.childNodes.map((n) => (n as El).className), ["fc-sec-head", "fc-composer", "fc-sec-cards", "fc-sec-send", "fc-sec-log"]);
  const track = w.track(), list = track.querySelector(".fc-cards")!;
  assert.equal(list.style.height, (CONTENT - OFFSET) + "px", "the list's content is the body's, less the header the track begins under: one scroll range for both");
  // the foot (Accept all · Reject all) left the list for the footer, above Send
  assert.equal(list.querySelector(".fc-foot"), null);
  const send = aside.querySelector(".fc-sec-send")!;
  assert.ok(send.childNodes[0] instanceof El && (send.childNodes[0] as El).classList.contains("fc-foot"), "the foot heads the send section");
  assert.ok(send.querySelector('[data-act="fcacceptall"]'), "with its buttons");
  // the marked cards sit at their marks: the change on row 7, replied's passage on row 3, the passage comment on row 5
  assert.equal(w.top("chg:h1"), desired(7));
  assert.equal(w.top(replied.id), desired(3));
  assert.equal(w.top(passage.id), desired(5));
  for (const k of ["chg:h1", replied.id, passage.id]) assert.equal(w.card(k)!.dataset.pushed, undefined, k + " is level, not pushed");
  // the paragraph title the change card wore in the list is still in the DOM (the list layout needs it back) and the sheet hides it here
  assert.ok(list.querySelector(".fc-group"), "the group title is rendered");
  assert.match(CSS, /\.fc-margin \.fc-cards > \.fc-group \{ display: none; \}/);
  w.close();
});

test("the loose group: the whole-file comment and the detached comment stack at the top of the track in the list's order, and the marked cards begin below them", async () => {
  const { w } = await open();
  const list = w.track().querySelector(".fc-cards")!;
  const loose = list.querySelectorAll(".fc-card").filter((c) => [whole.id, detached.id].includes(c.dataset.id));
  assert.equal(loose.length, 2);
  assert.deepEqual(loose.map((c) => c.dataset.id), [whole.id, detached.id], "the list's order: by ts");
  assert.deepEqual(loose.map((c) => parseFloat(c.style.top as string)), [8, 8 + CARD + 8], "stacked from the top inset, a gap apart");
  assert.ok(w.card(detached.id)!.classList.contains("fc-card-detached"), "detached is the rendering state it had");
  // replied's mark on row 3 is at 120 in the track's content, under the loose group's bottom (96) plus the gap: level
  assert.equal(w.top(replied.id), desired(3));
  w.close();
});

test("the scroll lock: a body scroll event puts the body's scrollTop on the track, a track scroll event the reverse, and neither echo writes back", async () => {
  const { w } = await open();
  const body = w.body, track = w.track();
  assert.equal(track.scrollTop, 0);
  body.scrollTop = 300; body.dispatchEvent(new Ev("scroll"));
  assert.equal(track.scrollTop, 300, "the track follows the body");
  // the track's echo (the scroll event the write raised) is let through without a write back: the body stays where the person put it
  body.scrollTop = 320;                                // the person kept scrolling before the echo landed
  track.dispatchEvent(new Ev("scroll"));
  assert.equal(body.scrollTop, 320, "the echo did not yank the body back to 300");
  // the reverse: a wheel over the cards moves the text
  track.scrollTop = 500; track.dispatchEvent(new Ev("scroll"));
  assert.equal(body.scrollTop, 500);
  body.dispatchEvent(new Ev("scroll"));                // the body's echo
  assert.equal(track.scrollTop, 500);
  // a genuine body event after the echoes mirrors again
  body.scrollTop = 40; body.dispatchEvent(new Ev("scroll"));
  assert.equal(track.scrollTop, 40);
  w.close();
});

test("expand: the card's new height pushes the card below it down (with the leader's length on it), the pass runs before the scroll, and the body centers the card's mark", async () => {
  const { w } = await open();
  const body = w.body;
  assert.equal(w.top(passage.id), desired(5), "level before");
  w.card(replied.id)!.querySelector(".fc-card-head")!.click();   // the head: the delegate toggles the card open and re-renders
  await tick();
  const opened = w.card(replied.id)!;
  assert.ok(opened.classList.contains("open"));
  assert.equal(parseFloat(opened.style.top as string), desired(3), "the opened card keeps its mark's height");
  const pushedTo = desired(3) + OPEN + 8;
  assert.equal(w.top(passage.id), pushedTo, "the card below moved down to the open card's bottom plus the gap");
  const pushed = w.card(passage.id)!;
  assert.equal(pushed.dataset.pushed, "1");
  assert.equal(pushed.style.getPropertyValue("--fc-push"), (pushedTo - desired(5)) + "px", "the leader runs from the card up to its mark's height");
  // the click centered the opened card's mark: the least scroll that shows the card's bottom wins over the mark's center here (a short body),
  // capped so the mark's top stays in view. The card's top is in the TRACK's content, which scrolls with the body, so that
  // scroll has no header term: the card's bottom plus the gap, less the track's box (a header term here over-scrolled by the
  // header's height and put the opened card's head under it — the 2026-09-07 review; file-comments-margin-fixes.test.ts)
  const markY = desired(3) + OFFSET;
  const showCard = desired(3) + OPEN + 8 - (BODY_VIEW - OFFSET);
  assert.equal(body.scrollTop, Math.min(showCard, markY - 8));
  assert.equal(w.track().scrollTop, body.scrollTop, "the track came along at once");
  // a fold moves nothing: the text stays where it is
  const before = body.scrollTop;
  w.card(replied.id)!.querySelector(".fc-card-head")!.click();
  await tick();
  assert.ok(!w.card(replied.id)!.classList.contains("open"));
  assert.equal(body.scrollTop, before);
  assert.equal(w.top(passage.id), desired(5), "level again once the card above folded");
  w.close();
});

test("a card's reference link (fcgoto) and a mark's click (fcopen) center the mark in the body in the margin layout; a loose card's opening scrolls the track as a list item", async () => {
  const { w } = await open();
  const body = w.body;
  w.card(passage.id)!.querySelector('[data-act="fcgoto"]')!.click();
  const markY = desired(5) + OFFSET;
  const showCard = desired(5) + CARD + 8 - (BODY_VIEW - OFFSET);   // track content: no header term
  assert.equal(body.scrollTop, Math.max(markY - BODY_VIEW / 2, Math.min(showCard, markY - 8)));
  assert.equal(w.track().scrollTop, body.scrollTop);
  assert.deepEqual(scrolledInto, [], "no scrollIntoView: the body's position is set from the placement");
  // a highlight in the body: its card opens and the same centering runs
  body.scrollTop = 0; w.track().scrollTop = 0;
  const mark = w.code.querySelector('.fc-hl[data-id="' + replied.id + '"]')!;
  mark.click();
  await tick();
  assert.ok(w.card(replied.id)!.classList.contains("open"), "the mark opened its card");
  assert.ok(body.scrollTop > 0, "and the body scrolled to it");
  // the whole-file comment has no mark: opening it through a click scrolls nothing (no mark to center on)
  const at = body.scrollTop;
  w.card(whole.id)!.querySelector(".fc-card-head")!.click();
  await tick();
  assert.equal(body.scrollTop, at);
  w.close();
});

test("the fold: with the row stacked (the sheet's column direction) the aside is the list layout — no margin class, no placed tops, the foot back in the list — and it returns when the columns do", async () => {
  const { w } = await open();
  assert.ok(w.aside().classList.contains("fc-margin"));
  narrow = true;
  resize(); flush();                                   // the row's size changed: the observers' pass reads the fold
  assert.ok(!w.aside().classList.contains("fc-margin"), "the list layout");
  const list = w.track().querySelector(".fc-cards")!;
  assert.ok(list.querySelector(".fc-foot"), "the foot is back among the change cards");
  assert.equal(w.aside().querySelector(".fc-sec-send .fc-foot"), null);
  for (const c of list.querySelectorAll(".fc-card")) assert.equal(c.style.top, undefined, "no absolute top on " + c.dataset.id);
  assert.equal(list.style.height, undefined, "the list flows");
  // the lock is off: a body scroll leaves the aside alone
  w.body.scrollTop = 250; w.body.dispatchEvent(new Ev("scroll"));
  assert.equal(w.track().scrollTop, 0);
  // wide again
  narrow = false;
  resize(); flush();
  assert.ok(w.aside().classList.contains("fc-margin"));
  assert.equal(w.top(passage.id), desired(5));
  assert.equal(w.track().scrollTop, 250, "the track took the body's position as the layout came back");
  w.close();
});

test("edit mode: the editor's paint is the list layout, and the read view's repaint brings the margin back", async () => {
  const { w } = await open();
  w.editing = true;
  w.setText(DOC);                                      // the viewer's body swap on Edit fires onRendered
  await tick();
  assert.ok(!w.aside().classList.contains("fc-margin"));
  assert.ok(w.track().querySelector(".fc-cards .fc-foot"), "the foot in the list");
  w.editing = false;
  w.setText(DOC);
  await tick();
  assert.ok(w.aside().classList.contains("fc-margin"));
  assert.equal(w.top(replied.id), desired(3));
  w.close();
});

test("re-layout events: a figure's load (captured on the body), a resize of the observed boxes and the window's resize each schedule ONE pass for the next frame; a scroll schedules none", async () => {
  const { w } = await open();
  frames.length = 0;
  w.body.dispatchEvent(new Ev("load"));               // does not bubble in a browser; the panel listens in the capture phase
  assert.equal(frames.length, 1, "one frame asked for");
  resize(); win.dispatchEvent(new Event("resize"));
  assert.equal(frames.length, 1, "no second frame while one is pending");
  w.body.scrollTop = 100; w.body.dispatchEvent(new Ev("scroll"));
  assert.equal(frames.length, 1, "a scroll asks for no pass: the lock is its whole effect");
  flush();
  assert.equal(frames.length, 0);
  win.dispatchEvent(new Event("resize"));
  assert.equal(frames.length, 1, "after the frame ran, the next event schedules again");
  // the observers watch the body, the row and the track; the cards of the render are watched too (a growing card pushes the ones below)
  const watched = new Set<El>(); for (const ro of RO.all) for (const t of ro.targets) watched.add(t);
  assert.ok(watched.has(w.body) && watched.has(w.main) && watched.has(w.track()), "body, row, track");
  assert.ok(watched.has(w.card(passage.id)!), "and each card");
  w.close();
  assert.deepEqual(RO.all.map((ro) => ro.targets.size), [0, 0], "dispose disconnects both observers");
});

// ── at source ──────────────────────────────────────────────────────────────────────────────────────

test("at source: the pass runs from render (before the click's centering) and from the frame, never from a scroll handler; the fold is the row's computed flex-direction; the layout is the pure module's", () => {
  assert.match(SRC, /import \{ layoutCards, CARD_GAP, type LayoutItem, type PlacedItem \} from "\.\/card-layout";/);
  assert.match(SRC, /if \(keep\) this\.refocus\(keep, want\);\n\s*this\.afterRender\(\);/, "render ends with the pass");
  assert.match(SRC, /private afterRender\(\): void \{\n\s*this\.placeCards\(true\);\n\s*const intent = this\.expandIntent;/, "the pass, then the centering");
  assert.match(SRC, /body\.addEventListener\("scroll", \(\) => this\.mirrorScroll\("body"\)\);/);
  assert.match(SRC, /track\.addEventListener\("scroll", \(\) => this\.mirrorScroll\("track"\)\);/);
  assert.doesNotMatch(SRC, /"scroll", \(\) => this\.(scheduleLayout|placeCards)/, "no pass on scroll");
  assert.match(SRC, /getComputedStyle\(row\)\.flexDirection !== "column"/, "the sheet's fold verdict, read off the row");
  assert.match(SRC, /body\.addEventListener\("load", \(\) => this\.scheduleLayout\(\), true\);/, "a figure's load, captured");
  assert.match(SRC, /const out = layoutCards\(items, CARD_GAP, this\.focusCard\);/, "the pure rule, given the focus (the focus follow-on, 2026-09-08)");
});
