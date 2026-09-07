// The Comments panel's change cards and marks, driven AS A PANEL for what the Slice 2 review found untested or wrong
// (plans/file-review.md, Slice 2; the contract's D4 and D5): the painters' newText check armed from the panel (a BOM
// the fetch stripped paints nothing rather than marks one character off), the Rendered half of the paint pass (an
// insertion painted and linked, a deletion card-only with Reveal to Raw), the file's own `data-act="fcchange"` markup
// neither decorated nor owned, a bound comment's highlight opening its host change card, a painted change's reference
// scrolling to its mark, the author's colour on a mark and the repaint when the colours arrive, no retry of the
// id-less accept-all and reject-all after a moved fence, Send stating what the accept-all decided, the window between
// a reject's reply and its reload (no marks over the old bytes, no tag or Reveal flapping in), and the keyboard kept in
// the panel through a decision's busy render and reply. The stand-in is the changes suite's, with the focus rules the
// review-fixes suite has (a focusable enabled element takes focus; a removed one drops it to the body), a Rendered body
// built by hand to marked's shape, a reload that can be held until the test lands it, and a colour fetch that can be
// held the same way. Synthetic fixtures only: the notes-api world, placeholder ids.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import type { FileViewActionCtx } from "./file-view";
import type { Status, Hunk, StoreComment } from "./file-comments-model";

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
const h2 = H("h2", "ins", at(" and the p99"), at(" and the p99") + " and the p99 by 10%".length, "", " and the p99 by 10%", T0 - 80000);
const h3 = H("h3", "del", at("shipping"), at("shipping"), "quickly ", "", T0 - 70000);
const h5 = H("h5", "ins", at(" again"), at(" again") + 6, "", " again", T0 - 50000);
/** The same change with its offsets moved by `n` — hunks computed over another string. */
const shifted = (h: Hunk, n: number): Hunk => ({ ...h, curFrom: h.curFrom + n, curTo: h.curTo + n });
const passage: StoreComment = {
  id: T0 + "-118", author: "you", ts: T0, body: "Which cache? Say which.",
  anchor: { quote: "shipping the cache in v1.2", prefix: "We recommend ", suffix: "." }, replies: [], resolved: false,
};
// a passage comment the session answered with a revision: it keeps its anchor and gains the change's id
const hosted: StoreComment = {
  id: T0 + 5000 + "-7", author: "you", ts: T0 + 5000, body: "Cut is the right word.",
  anchor: { quote: "cut p95 latency", prefix: "The api session ", suffix: " by 40%" }, suggestionId: "h1", replies: [], resolved: false,
};
const SUGG = [{ id: "h1", author: "api", authorId: SID, ts: T0 - 90000, kind: "sub", from: h1.curFrom, oldText: "reduced", newText: "cut" },
  { id: "h3", author: "api", ts: T0 - 70000, kind: "del", from: h3.curFrom, oldText: "quickly " }];
function status(over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: ROOT, storePath: STORE_PATH, trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
    store: { v: 3, path: "docs/report.md", suggestions: SUGG, comments: [passage] },
    hunks: [h1, h3], log: [],
    unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 0, watermark: null },
    ...over,
  };
}
const MOVED_FILE = "the file ~/notes-api/docs/report.md changed on disk since you opened the file — reload and retry";
const MOVED_STORE = "the comments for ~/notes-api/docs/report.md changed on disk since you opened the file — reload and retry";

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

// ── the viewer stand-in: a Raw or Rendered body, the seam as closures, a file whose mtime the view tracks ──
type World = {
  ctx: FileViewActionCtx; posted: any[]; main: El; body: El;
  hooks: { rendered: Array<() => void>; close: Array<() => void> };
  disk: string; diskMtime: string; viewMtime: string; reloads: number; scrolls: number[]; modes: string[];
  mtimes: Record<string, string>;
  /** The held reload's landing (deferReload): the bytes and mtime now on disk, repainted, onRendered fired. */
  landReload: (() => void) | null;
  /** Releases the held colour fetch (holdSessions); the fetch stub awaits the gate. */
  releaseSessions: () => void;
  sessionsGate: Promise<void>;
  close(): void;
};
let cur: World | null = null;
(globalThis as any).fetch = async (url: string) => {
  if (url.includes("/sessions")) {
    await cur!.sessionsGate;
    return { json: async () => [{ id: SID, name: "api", bg: "#123456", fg: "#ffffff" }] };
  }
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
const el = (tag: string, ...kids: Array<El | string>): El => { const e = new El(tag); for (const k of kids) e.appendChild(typeof k === "string" ? new Txt(k) : k); return e; };
/** A file-authored inline element the sanitizer keeps: `<span data-act=… data-id=…>text</span>`. */
const fileSpan = (act: string, id: string, text: string): El => { const s = el("span", text); s.dataset.act = act; s.dataset.id = id; return s; };
/** marked's rendering of DOC, built by hand: one element per block, in order, holding the block's text. */
function renderedDoc(box: El, intro?: El): void {
  const blocks: El[] = [el("h1", "Report")];
  if (intro) blocks.push(intro);
  blocks.push(el("h2", "Findings"), el("p", "The api session cut p95 latency by 40% and the p99 by 10%."),
    el("p", "We recommend shipping the cache in v1.2."), el("p", "Risks remain in the fallback path."), el("p", "Next steps: measure again."));
  box.replaceChildren(...blocks);
}
type WorldOpts = { src?: string; mode?: "raw" | "rendered"; intro?: () => El; deferReload?: boolean; holdSessions?: boolean };
function world(over: WorldOpts = {}): World {
  const mode = over.mode || "raw";
  const main = new El("div"); main.className = "fileview-main";
  const body = new El("div"); body.className = "fileview-body";
  main.appendChild(body);
  let text = over.src ?? DOC;
  let code: El | null = null, md: El | null = null;
  if (mode === "raw") {
    const wrap = new El("div"); wrap.className = "fileview-code";
    const pre = new El("pre"); pre.className = "fileview-pre fileview-wrap";
    code = new El("code"); code.className = "hljs";
    pre.appendChild(code); wrap.appendChild(pre); body.appendChild(wrap);
    rows(code, text);
  } else {
    md = new El("div"); md.className = "fileview-md"; body.appendChild(md);
    renderedDoc(md, over.intro ? over.intro() : undefined);
  }
  let release: () => void = () => { /* set below */ };
  const gate = new Promise<void>((r) => { release = r; });
  if (!over.holdSessions) release();
  const w = {
    posted: [] as any[], main, body,
    hooks: { rendered: [] as Array<() => void>, close: [] as Array<() => void> },
    disk: text, diskMtime: "1757145600000000001", viewMtime: "1757145600000000001", reloads: 0, scrolls: [] as number[], modes: [] as string[], mtimes: {} as Record<string, string>,
    landReload: null as (() => void) | null, releaseSessions: release, sessionsGate: gate,
  } as World;
  const setText = (s: string) => {
    text = s;
    if (code) rows(code, s); else if (md) renderedDoc(md, over.intro ? over.intro() : undefined);
    for (const cb of w.hooks.rendered) cb();
  };
  const land = () => { w.landReload = null; w.viewMtime = w.diskMtime; setText(w.disk); };
  w.ctx = {
    path: ABS, sid: SID, todoId: null,
    body: () => body as unknown as HTMLElement, mode: () => mode, text: () => text, mtimeNs: () => w.viewMtime, media: () => null, mediaElement: () => null, renderedImages: () => [],
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
function answer(w: World, s: Status, m = lastOf(w, "fileComments", "status"), extra: Record<string, unknown> = {}): void {
  assert.ok(m, "an ask is outstanding");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: m.reqId, ...s, ...extra } }));
  w.mtimes[w.ctx.path] = s.fileMtimeNs;
  if (s.storePath && s.storeMtimeNs !== null) w.mtimes[s.storePath] = s.storeMtimeNs;
  if (s.root && s.configMtimeNs !== null) w.mtimes[s.root + "/.trackchanges/config.json"] = s.configMtimeNs;
}
function refuse(w: World, m: any, code: string, error: string): void {
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsFailed", reqId: m.reqId, verb: m.verb, code, error } }));
}
async function openPanel(w: World, s: Status = status()): Promise<{ unit: El; button: El; aside: El }> {
  const fc = await import("./file-comments");
  const unit = fc.fileCommentsAction.mount(w.ctx) as unknown as El;
  const button = unit.childNodes[0] as El;
  answer(w, s); await flush();
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
/** The row's text before `mark`, in document order (a point on a highlight's edge sits inside the highlight): where it begins. */
function before(mark: El): string {
  const row = mark.closest(".fv-cl")!;
  let s = ""; let done = false;
  const visit = (n: El | Txt) => { if (done || n === mark) { done = true; return; } if (n instanceof Txt) s += n.data; else for (const c of n.childNodes) visit(c); };
  visit(row);
  return s;
}

// ── the painters' check, armed from the panel ──────────────────────────────────────────────────────

test("hunks over the host's BOM-bearing text against a view without the BOM: nothing is painted, every card is card-only with Reveal — in Raw and in Rendered; over matching text the same hunks paint", async (t: TestContext) => {
  // the host decodes the file keeping a leading U+FEFF (track-edit's ignoreBOM) and computes the hunks over that string;
  // the viewer's fetch strips it, so every offset is one too many. The painters refuse the batch on the new text the
  // panel now hands them, rather than marking "ut " for "cut" (plans/file-review.md: Raw is exact).
  const w = world(); t.after(() => w.close());
  const bom = status({ hunks: [shifted(h1, 1), shifted(h3, 1)] });
  const { aside } = await openPanel(w, bom);
  assert.equal(marksOf(w).length, 0, "no change mark over the wrong characters");
  for (const key of ["chg:h1", "chg:h3"]) {
    const c = card(aside, key)!;
    assert.ok(tags(c).includes("not shown"), key + " is card-only");
    assert.ok(act(c, "fcreveal", key), key + " offers Reveal");
    assert.equal(isLink(c), false, key + "'s reference is no link");
  }
  w.close();
  const wr = world({ mode: "rendered" }); t.after(() => wr.close());
  const { aside: ar } = await openPanel(wr, status({ hunks: [shifted(h2, 1)] }));
  assert.equal(marksOf(wr).length, 0, "Rendered refuses the same batch");
  assert.ok(tags(card(ar, "chg:h2")!).includes("not shown"));
  wr.close();
  // the control: the same hunks over the text they index paint, "cut" under the substitution's mark
  const w2 = world(); t.after(() => w2.close());
  await openPanel(w2);
  assert.ok(marksOf(w2, "h1").some((m) => m.textContent === "cut"), "over matching text the substitution's new text is marked");
});

// ── the Rendered half of the paint pass ────────────────────────────────────────────────────────────

test("Rendered: an insertion is painted and its card links to the mark; a deletion is card-only, tagged for the Rendered view, and its Reveal switches to Raw at the change's start", async (t: TestContext) => {
  const w = world({ mode: "rendered" }); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ hunks: [h2, h3] }));
  const ins = marksOf(w, "h2");
  assert.equal(ins.length, 1, "the insertion is marked once in the rendered prose");
  assert.equal(ins[0].textContent.trim(), "and the p99 by 10%", "the insertion's words (a Rendered wrap runs from the first character to the last)");
  assert.equal(ins[0].getAttribute("role"), "button"); assert.equal(ins[0].tabIndex, 0);
  const c2 = card(aside, "chg:h2")!;
  assert.ok(isLink(c2), "a painted change's reference is a link to its mark");
  assert.equal(tags(c2).includes("not shown"), false);
  assert.equal(act(c2, "fcreveal", "chg:h2"), null, "a painted insertion needs no Reveal");
  assert.equal(marksOf(w, "h3").length, 0, "a deletion is never painted in Rendered");
  const c3 = card(aside, "chg:h3")!;
  const tag = c3.querySelectorAll(".fc-card-head .fc-tag").find((x) => x.textContent === "not shown")!;
  assert.ok(tag, "the deletion's card says the view does not show it");
  assert.equal(tag.title, "The Rendered view cannot show a deletion; Reveal opens it in Raw");
  assert.equal(isLink(c3), false);
  const rv = act(c3, "fcreveal", "chg:h3")!;
  assert.ok(rv, "…and offers Reveal");
  rv.click();
  assert.deepEqual(w.modes, ["raw"]); assert.deepEqual(w.scrolls, [h3.curFrom]);
  // the mark opens the card, as in Raw
  ins[0].click();
  assert.ok(card(aside, "chg:h2")!.classes.includes("open"), "a click on the rendered mark opens its card");
  assert.ok(scrolledInto.includes(card(aside, "chg:h2")!));
});

test("Rendered: the file's own data-act=fcchange markup is neither decorated nor owned, and a card's link scrolls to the panel's mark, not the file's element", async (t: TestContext) => {
  // the sanitizer keeps data-* attributes, so prose a session wrote can carry `<span data-act="fcchange" data-id="h2">`;
  // the panel's provenance rule (own / owns) says only what the panel MADE routes — here the marks are told from the
  // file's markup by what the paint added, and goTo scrolls only to a mark of ours
  const intro = "Intro <span data-act=\"fcchange\" data-id=\"h2\">spoof</span> <span data-act=\"fcchange\" data-id=\"zz\">zz</span> <span data-act=\"fcopen\" data-id=\"" + passage.id + "\">open</span> here.\n\n";
  const src = "# Report\n\n" + intro + DOC.slice("# Report\n\n".length);
  const n = intro.length;
  const w = world({ mode: "rendered", src, intro: () => el("p", "Intro ", fileSpan("fcchange", "h2", "spoof"), " ", fileSpan("fcchange", "zz", "zz"), " ", fileSpan("fcopen", passage.id, "open"), " here.") });
  t.after(() => w.close());
  const { aside } = await openPanel(w, status({ hunks: [shifted(h2, n)] }));
  const all = marksOf(w, "h2");
  const spoof = all.find((m) => m.textContent === "spoof")!;
  const mark = all.find((m) => m !== spoof)!;
  assert.ok(spoof && mark, "the file's span and the painted mark both carry the attributes");
  assert.equal(mark.textContent.trim(), "and the p99 by 10%", "the change is painted where it is");
  assert.equal(mark.getAttribute("role"), "button", "the panel's mark is a control");
  for (const s of [spoof, w.body.querySelector('[data-act="fcchange"][data-id="zz"]')!, w.body.querySelector('[data-act="fcopen"]')!]) {
    assert.equal(s.getAttribute("role"), null, s.textContent + ": the file's element is not made a control");
    assert.equal(s.hasAttribute("tabindex"), false);
    assert.equal(s.title, "");
  }
  // a click or Enter on the spoof opens nothing
  spoof.click();
  assert.equal(aside.querySelectorAll(".fc-card.open").length, 0, "the file's element is not the panel's: no card opens");
  const ev = new Ev("keydown", { key: "Enter" }); dispatch(spoof, ev);
  assert.equal(ev.defaultPrevented, false, "…and the keyboard is not claimed for it");
  w.body.querySelector('[data-act="fcopen"]')!.click();
  assert.equal(aside.querySelectorAll(".fc-card.open").length, 0);
  // the card's link goes to the mark the panel painted, though the spoof comes first in the document
  const c2 = card(aside, "chg:h2")!;
  assert.ok(isLink(c2));
  c2.querySelector(".fc-ref")!.click();
  assert.equal(scrolledInto[scrolledInto.length - 1], mark, "Scroll to the change reaches the mark, not the file's span");
  assert.deepEqual(w.modes, [], "and no view switch");
  // the real mark still opens the card
  mark.click();
  assert.ok(card(aside, "chg:h2")!.classes.includes("open"));
});

// ── the cards' links to the body ───────────────────────────────────────────────────────────────────

test("a comment bound to a change that keeps its anchor: its highlight is painted and opens the change card hosting it", async (t: TestContext) => {
  // a passage comment the session answered with track-edit --thread keeps its anchor and gains the change's id (the
  // host test "accept resolves every comment bound by suggestionId, anchor or not"): it has no card of its own
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ store: { v: 3, path: "docs/report.md", suggestions: SUGG, comments: [passage, hosted] } }));
  assert.equal(card(aside, hosted.id), null, "hosted on the change's card, no card of its own");
  const hl = w.body.querySelector('.fc-hl[data-act="fcopen"][data-id="' + hosted.id + '"]')!;
  assert.ok(hl, "its passage is highlighted all the same");
  assert.equal(card(aside, "chg:h1")!.classes.includes("open"), false);
  hl.click();
  const c1 = card(aside, "chg:h1")!;
  assert.ok(c1.classes.includes("open"), "the highlight opens the change card that hosts the comment");
  assert.ok(scrolledInto.includes(c1), "…and scrolls to it");
  assert.ok(c1.querySelector('.fc-hosted[data-id="' + hosted.id + '"]'), "where the comment is");
  assert.equal(aside.querySelectorAll(".fc-card.open").length, 1, "nothing else opened: no dead end on a card that does not exist");
});

test("a painted change's reference scrolls to its mark and switches no view; by Enter too", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  const ref = card(aside, "chg:h1")!.querySelector(".fc-ref")!;
  assert.ok(ref.classes.includes("fc-link"));
  assert.equal(ref.dataset.act, "fcgoto"); assert.equal(ref.dataset.id, "chg:h1");
  ref.click();
  const to = scrolledInto[scrolledInto.length - 1];
  assert.ok(to && to.dataset.act === "fcchange" && to.dataset.id === "h1", "the click scrolls to the change's mark");
  assert.deepEqual(w.modes, []); assert.deepEqual(w.scrolls, []);
  scrolledInto.length = 0;
  dispatch(card(aside, "chg:h1")!.querySelector(".fc-ref")!, new Ev("keydown", { key: "Enter" }));
  const to2 = scrolledInto[scrolledInto.length - 1];
  assert.ok(to2 && to2.dataset.act === "fcchange" && to2.dataset.id === "h1", "Enter on the reference does the same");
  assert.deepEqual(w.modes, []);
});

test("change marks carry the author's session colour as --fc-author; colours arriving after the first paint repaint the marks", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  await openPanel(w);
  const cut = marksOf(w, "h1").find((m) => m.textContent === "cut")!;
  assert.equal(cut.getAttribute("style"), "--fc-author: #123456;", "the sidecar record's authorId through the colour map");
  for (const m of marksOf(w, "h3")) assert.equal(m.getAttribute("style"), null, "a record without an authorId: the sheet's neutral");
  w.close();
  // the colour fetch answers after the status-driven first paint: the marks are repainted with the colour
  const w2 = world({ holdSessions: true }); t.after(() => w2.close());
  await openPanel(w2);
  const plain = marksOf(w2, "h1").find((m) => m.textContent === "cut")!;
  assert.ok(plain, "painted before the colours came");
  assert.equal(plain.getAttribute("style"), null);
  w2.releaseSessions(); await flush(); await flush();
  const coloured = marksOf(w2, "h1").find((m) => m.textContent === "cut")!;
  assert.equal(coloured.getAttribute("style"), "--fc-author: #123456;", "the colours' arrival repaints the marks");
  assert.equal(marksOf(w2, "h1").filter((m) => m.textContent === "cut").length, 1, "…without stacking");
});

// ── the id-less verbs after a moved fence ──────────────────────────────────────────────────────────

test("Reject all refused file-moved: status and the bytes are re-read, no second reject-all goes, and the row says nothing was decided; Send's accept-all refused store-moved sends nothing the same way", async (t: TestContext) => {
  // the plan's fence rule retries by stable change or comment id; accept-all and reject-all carry none, so a retry
  // would decide the change that landed since the click. The list is re-read and the choice is the person's again.
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  act(aside, "fcrejectall")!.click();
  assert.ok(aside.querySelector(".fc-foot .fc-choice")!.textContent.includes("all 2 changes"), "the confirm names the two on screen");
  act(aside, "fcrejectallgo")!.click(); await flush();
  const first = lastOf(w, "fileComments", "reject-all");
  assert.ok(first);
  // the session's track-edit landed meanwhile: a third change, and the file moved
  const h9 = H("h9", "ins", DOC.length, DOC.length + "A new line.".length, "", "A new line.", T0);
  w.disk = DOC + "A new line.\n"; w.diskMtime = "1757145600000000009";
  const asks = countOf(w, "fileComments", "status");
  refuse(w, first, "file-moved", MOVED_FILE); await flush();
  assert.equal(countOf(w, "fileComments", "status"), asks + 1, "status is re-issued");
  answer(w, status({ fileMtimeNs: "1757145600000000009", storeMtimeNs: "1757145600000000010", hunks: [h1, h3, h9] })); await flush(); await flush();
  assert.equal(w.reloads, 1, "the file moved under the view: its bytes are re-fetched");
  assert.equal(countOf(w, "fileComments", "reject-all"), 1, "no retry: the set the person confirmed is not the set on disk");
  assert.deepEqual(aside.querySelectorAll(".fc-card.fc-change").map((c) => c.dataset.id), ["chg:h1", "chg:h3", "chg:h9"], "the fresh set shows, the new change among it");
  const err = aside.querySelector(".fc-foot .fc-err")!;
  assert.ok(err, "the row sits under the foot that asked");
  assert.ok(err.textContent.startsWith("Nothing decided: " + MOVED_FILE), "the host's reason, and that nothing was decided");
  assert.ok(err.textContent.includes("re-read"), "…and that the list is fresh");
  assert.equal(act(err, "fcreload"), null, "no Reload: the re-read already happened");
  assert.equal(aside.querySelector(".fc-foot .fc-choice"), null, "the confirm is closed; a second Reject all asks again");
  assert.equal(act(aside, "fcrejectall")!.disabled, false); assert.equal(act(aside, "fcacceptall")!.disabled, false);
  // Send with the accept box checked: the accept-all refused store-moved is not retried, and nothing is sent
  act(aside, "fcsend")!.click();
  assert.ok(aside.querySelector('input[data-opt="accept"]')!.checked);
  act(aside, "fcsendgo")!.click(); await flush();
  const acc = lastOf(w, "fileComments", "accept-all");
  assert.ok(acc, "accept-all goes first");
  const asks2 = countOf(w, "fileComments", "status");
  refuse(w, acc, "store-moved", MOVED_STORE); await flush();
  assert.equal(countOf(w, "fileComments", "status"), asks2 + 1);
  answer(w, status({ fileMtimeNs: "1757145600000000009", storeMtimeNs: "1757145600000000013", hunks: [h1, h3, h9] })); await flush(); await flush();
  assert.equal(countOf(w, "fileComments", "accept-all"), 1, "no retry");
  assert.equal(countOf(w, "fileCommentsSend"), 0, "and no send: the message would claim decisions never made");
  assert.ok(aside.querySelector(".fc-send .fc-err")!.textContent.startsWith("Nothing decided: " + MOVED_STORE), "the row under Send");
});

// ── what Send states ───────────────────────────────────────────────────────────────────────────────

test("Send states what the accept-all decided: a set grown by the set-tracked reply is counted from the accept-all's reply, not from the confirm; a reply that does not say sends nothing", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ trackedBy: null, unsent: { comments: [passage.id], replies: [], accepted: 1, rejected: 0, watermark: null } }));
  act(aside, "fcsend")!.click();
  assert.ok(aside.querySelector('input[data-opt="track"]')!.checked, "untracked: the tracking box, checked");
  assert.equal(aside.querySelector('input[data-opt="accept"]')!.parentNode!.textContent, "accept the 2 pending changes", "the confirm names the two on screen");
  act(aside, "fcsendgo")!.click(); await flush();
  const tr = lastOf(w, "fileComments", "set-tracked");
  assert.deepEqual(tr.args, { on: true, scope: "file" });
  // the toggle's reply carries a third change: the session's track-edit landed between the confirm and the toggle
  const h9 = H("h9", "ins", DOC.length - 1, DOC.length + 3, "", " Ok.", T0);
  answer(w, status({ trackedBy: { kind: "file", entry: "docs/report.md" }, configMtimeNs: "1757145600000000014", storeMtimeNs: "1757145600000000015", hunks: [h1, h3, h9] }), tr); await flush(); await flush();
  const acc = lastOf(w, "fileComments", "accept-all");
  assert.ok(acc, "then the accept-all");
  assert.equal(acc.fence.storeMtimeNs, "1757145600000000015", "fenced on the sidecar the toggle's reply showed");
  assert.equal(countOf(w, "fileCommentsSend"), 0);
  answer(w, status({ trackedBy: { kind: "file", entry: "docs/report.md" }, configMtimeNs: "1757145600000000014", storeMtimeNs: "1757145600000000016", hunks: [],
    store: { v: 3, path: "docs/report.md", suggestions: [], comments: [passage] },
    unsent: { comments: [passage.id], replies: [], accepted: 4, rejected: 0, watermark: null } }), acc, { accepted: ["h1", "h3", "h9"] }); await flush(); await flush();
  const send = lastOf(w, "fileCommentsSend");
  assert.ok(send, "then the send");
  assert.equal(send.accepted, 4, "the log's 1 plus the THREE the accept-all decided — its reply's list, not the confirm's 2");
  assert.equal(send.rejected, 0); assert.equal(send.tracked, true);
  w.close();
  // a reply that lists nothing: the count cannot be stated, so nothing is sent and the row says why
  const w2 = world(); t.after(() => w2.close());
  const { aside: a2 } = await openPanel(w2);
  act(a2, "fcsend")!.click();
  act(a2, "fcsendgo")!.click(); await flush();
  const acc2 = lastOf(w2, "fileComments", "accept-all");
  answer(w2, status({ hunks: [], store: { v: 3, path: "docs/report.md", suggestions: [], comments: [passage] }, storeMtimeNs: "1757145600000000017",
    unsent: { comments: [passage.id], replies: [], accepted: 2, rejected: 0, watermark: null } }), acc2); await flush(); await flush();
  assert.equal(countOf(w2, "fileCommentsSend"), 0, "nothing sent");
  const err = a2.querySelector(".fc-send .fc-err")!;
  assert.ok(err && err.textContent.startsWith("Nothing sent: the reply to the accept did not list what it accepted"), "loud, under Send");
  assert.ok(a2.querySelector('[data-act="fcsend"]')!.textContent.includes("(3)"), "the decisions are in the log: the next Send carries them");
});

// ── between a reject's reply and its reload ────────────────────────────────────────────────────────

test("between a reject's reply and its reload: nothing is painted over the old bytes, the surviving cards neither claim 'not shown' nor grow a Reveal, and the marks land once the bytes arrive", async (t: TestContext) => {
  // the reply's hunks index the post-reject text; the view still shows the pre-reject bytes until fetchFile lands. A
  // deletion's point passes the painters' text check wherever it sits, so the mtime gate alone keeps it off the old text.
  const w = world({ deferReload: true }); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ hunks: [h1, h3, h5] }));
  assert.equal(act(card(aside, "chg:h5")!, "fcreveal", "chg:h5"), null, "a painted insertion: no Reveal");
  act(card(aside, "chg:h1")!, "fcreject", "h1")!.click(); await flush();
  const m = lastOf(w, "fileComments", "reject");
  // the reply: "cut" is "reduced" again, so every survivor sits four characters further on
  w.disk = DOC.replace("cut", "reduced"); w.diskMtime = "1757145600000000011";
  answer(w, status({ fileMtimeNs: "1757145600000000011", storeMtimeNs: "1757145600000000012", hunks: [shifted(h3, 4), shifted(h5, 4)],
    store: { v: 3, path: "docs/report.md", suggestions: [SUGG[1]], comments: [passage] },
    unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 1, watermark: null } }), m, { rejected: ["h1"] }); await flush(); await flush();
  assert.equal(w.reloads, 1, "the bytes are asked for"); assert.ok(w.landReload, "…and not yet here");
  assert.equal(w.viewMtime, "1757145600000000001", "the view still shows the old bytes");
  assert.equal(marksOf(w).length, 0, "nothing is painted over them — not the deletion's point four characters late");
  const c3 = card(aside, "chg:h3")!, c5 = card(aside, "chg:h5")!;
  assert.equal(tags(c3).includes("not shown"), false, "the window claims nothing about the view");
  assert.equal(tags(c5).includes("not shown"), false);
  assert.equal(c3.querySelectorAll('[data-act="fcreveal"]').length, 1, "a deletion's Reveal is constant");
  assert.equal(c5.querySelectorAll('[data-act="fcreveal"]').length, 0, "an insertion grows no Reveal for one fetch");
  assert.equal(isLink(c5), false, "and no link to a mark that is not there");
  assert.equal(act(c3, "fcreveal", "chg:h3")!.title, "Show the change in the Raw view", "no line number from offsets into other bytes");
  // the bytes land: the marks are painted where the changes now are
  w.landReload!(); await flush();
  assert.equal(w.viewMtime, "1757145600000000011");
  const point = marksOf(w, "h3");
  assert.equal(point.length, 1, "the deletion's point is painted once");
  assert.equal(before(point[0]), "We recommend ", "…at its place in the new text");
  const again = marksOf(w, "h5").find((x) => x.textContent === " again")!;
  assert.ok(again, "the insertion is marked over its text");
  assert.ok(isLink(card(aside, "chg:h5")!), "…and its card links to it");
  assert.equal(tags(card(aside, "chg:h5")!).includes("not shown"), false);
  assert.match(act(card(aside, "chg:h3")!, "fcreveal", "chg:h3")!.title, /\(line 6\)$/, "the line number is back with the bytes it indexes");
});

// ── the keyboard through a decision ────────────────────────────────────────────────────────────────

test("keyboard: Accept, Reject, Accept all and the Reject all confirm keep the focus in the panel through the busy render and after the reply; a refusal returns it to the button", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  const headOf = (key: string) => card(aside, key)!.querySelector(".fc-card-head")!;
  const inPanel = () => aside.contains(doc.activeElement);
  // Accept by Enter: the button comes back disabled, so the keyboard waits on the card's head; the card goes, the next takes it
  const ok = act(card(aside, "chg:h1")!, "fcaccept", "h1")!;
  ok.focus(); assert.equal(doc.activeElement, ok, "Tab reached Accept");
  ok.click(); await flush();
  assert.equal(act(card(aside, "chg:h1")!, "fcaccept", "h1")!.disabled, true, "busy: Accepting…");
  assert.ok(inPanel(), "the keyboard did not fall to the body");
  assert.equal(doc.activeElement, headOf("chg:h1"), "…it waits on the card's head");
  const m1 = lastOf(w, "fileComments", "accept");
  answer(w, status({ hunks: [h3], store: { v: 3, path: "docs/report.md", suggestions: [SUGG[1]], comments: [passage] }, storeMtimeNs: "1757145600000000004",
    unsent: { comments: [passage.id], replies: [], accepted: 1, rejected: 0, watermark: null } }), m1, { accepted: ["h1"] }); await flush(); await flush();
  assert.equal(card(aside, "chg:h1"), null, "the card is gone");
  assert.ok(inPanel());
  assert.equal(doc.activeElement, headOf("chg:h3"), "the card now at its place holds the keyboard");
  // Reject refused (not a moved fence): the card stays, and the keyboard returns to the button it left
  const no = act(card(aside, "chg:h3")!, "fcreject", "h3")!;
  no.focus(); no.click(); await flush();
  assert.equal(doc.activeElement, headOf("chg:h3"), "busy: on the head meanwhile");
  refuse(w, lastOf(w, "fileComments", "reject"), "corrupt", "the comments for ~/notes-api/docs/report.md are not valid JSON"); await flush(); await flush();
  const no2 = act(card(aside, "chg:h3")!, "fcreject", "h3")!;
  assert.equal(no2.disabled, false);
  assert.equal(doc.activeElement, no2, "the re-enabled Reject takes the focus back");
  assert.ok(card(aside, "chg:h3")!.querySelector(".fc-err"), "the refusal is the card's row");
  // Accept all: both foot buttons disable, so the keyboard waits on the last card's head; every change card goes, the comment card's head takes it
  const all = act(aside, "fcacceptall")!;
  all.focus(); all.click(); await flush();
  assert.equal(act(aside, "fcacceptall")!.disabled, true);
  assert.equal(doc.activeElement, headOf("chg:h3"), "busy: the change card before the foot");
  answer(w, status({ hunks: [], store: { v: 3, path: "docs/report.md", suggestions: [], comments: [passage] }, storeMtimeNs: "1757145600000000005",
    unsent: { comments: [passage.id], replies: [], accepted: 2, rejected: 0, watermark: null } }), lastOf(w, "fileComments", "accept-all"), { accepted: ["h3"] }); await flush(); await flush();
  assert.equal(aside.querySelectorAll(".fc-card.fc-change").length, 0);
  assert.equal(doc.activeElement, headOf(passage.id), "no change card left: the comment card at that place");
  w.close();
  // the Reject all confirm's own button
  const w2 = world(); t.after(() => w2.close());
  const { aside: a2 } = await openPanel(w2);
  act(a2, "fcrejectall")!.click();
  const go = act(a2, "fcrejectallgo")!;
  go.focus(); go.click(); await flush();
  assert.equal(act(a2, "fcrejectallgo"), null, "the confirm row is gone");
  assert.equal(doc.activeElement, card(a2, "chg:h3")!.querySelector(".fc-card-head"), "busy: the last change card's head");
  w2.disk = DOC.replace("cut", "reduced").replace("shipping", "quickly shipping"); w2.diskMtime = "1757145600000000021";
  answer(w2, status({ fileMtimeNs: "1757145600000000021", storeMtimeNs: "1757145600000000022", hunks: [], store: { v: 3, path: "docs/report.md", suggestions: [], comments: [passage] },
    unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 2, watermark: null } }), lastOf(w2, "fileComments", "reject-all"), { rejected: ["h1", "h3"] }); await flush(); await flush();
  assert.ok(a2.contains(doc.activeElement), "after the reply the keyboard is still in the panel");
  assert.equal(doc.activeElement, card(a2, passage.id)!.querySelector(".fc-card-head"));
  // (a control outside the cards list keeps Slice 1's rule — removed, the focus falls to the body, quietly — which the
  // review-fixes suite pins for the head row's tracking Cancel; the nearest-place rule is the cards list's alone)
});
