// The click that ends a drag-selection inside a body mark opens nothing (plans/file-review.md, Slice 2, the marks' click
// rule; the fix of 2026-09-09; file-comments.ts dragClick and endInside). The user's requirement: a comment must be
// possible inside a tracked change other than by replying to the change. A change mark and a comment highlight are
// controls (data-act fcchange and fcopen, tabIndex, role=button), and a drag begun and ended inside one fires a click on
// it, the common ancestor of the press and the release; the click opened the card and its scroll hid the Comment float
// the same mouseup had offered. The guard reads the click's own state against the CLICKED mark: a non-collapsed
// selection whose anchor and focus both lie inside that mark is the drag's, and the handler does nothing; a collapsed
// selection, none, one in the aside, one with an end outside the mark, or one standing elsewhere in the body with none
// of it in the mark leaves the click a click, and the card opens as before; a click with no pointer behind it (`detail`
// 0: Enter or Space through the row's keydown, element.click()) opens the card whatever selection stands. The guard's
// line is the clicked mark, not the body. As first built it read any selection with both ends in the body as a drag's,
// and a real browser reaches that state, since not every press collapses a standing selection: a deletion's label
// (`span.fc-del`, `user-select: none`, its text CSS-generated) and a mark inside an author's link keep it, and the click
// arrives with the selection standing in another paragraph (the review of 2026-09-09, with a real mouse in Chromium and
// Firefox), so a click on such a mark opened nothing until the reader clicked plain text. The `elsewhere` cases pin the
// narrowed line: a guard widened back to the body turns them red. file-comments-markclick-controls.test.ts drives the
// narrowing's own cases (the deletion's point, a selection spanning the mark from outside, the edge reports, the pulse
// taken back, the panel closed). Driven here over the behavior suite's DOM stand-in with the selection faked per case
// (window.getSelection is what the panel reads), the pointer's click carrying detail 1 and the keyboard's 0 as browsers
// dispatch them; file-comments-markclick-browser.test.ts drags a real mouse in Chromium and Firefox. Synthetic fixtures
// only: the notes-api world, placeholder ids.
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
// the CURRENT text: the session's insertion already applied (the file on disk always reads as if accepted)
const DOC = "# Report\n\n## Findings\nThe api session cut p95 latency by 40% and the p99 by 10%.\n\n"
  + "We recommend shipping the cache in v1.2.\n\nRisks remain in the fallback path.\n\nNext steps: measure again.\n";
const at = (needle: string): number => { const i = DOC.indexOf(needle); assert.ok(i >= 0, needle); return i; };
// the insertion inside the findings line, and a passage comment on the recommendation
const INS = " and the p99 by 10%";
const h2: Hunk = { id: "h2", author: "api", ts: T0 - 80000, kind: "ins", curFrom: at(INS), curTo: at(INS) + INS.length, baseFrom: at(INS), baseTo: at(INS), oldText: "", newText: INS, anchor: null };
const passage: StoreComment = {
  id: T0 + "-118", author: "you", ts: T0, body: "Which cache? Say which.",
  anchor: { quote: "shipping the cache in v1.2", prefix: "We recommend ", suffix: "." }, replies: [], resolved: false,
};
function status(): Status {
  return {
    verb: "status", root: ROOT, storePath: STORE_PATH, trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
    store: { v: 3, path: "docs/report.md", suggestions: [], comments: [passage] },
    hunks: [h2], log: [],
    unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 0, watermark: null },
  };
}

// ── the DOM stand-in (the behavior suite's, with a click's `detail`): ancestry, attributes, events, a small selector engine ──
class Ev {
  target: El | Txt | null = null;
  currentTarget: El | null = null;
  defaultPrevented = false;
  stopped = false;
  key: string;
  ctrlKey: boolean; metaKey: boolean;
  detail: number;                                  // a click's count: 1 from a pointer, 0 from element.click() and a keyboard activation, as browsers dispatch them
  constructor(public type: string, init: { key?: string; ctrlKey?: boolean; metaKey?: boolean; detail?: number } = {}) { this.key = init.key || ""; this.ctrlKey = !!init.ctrlKey; this.metaKey = !!init.metaKey; this.detail = init.detail ?? 0; }
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
const countOf = (w: World, type: string, verb?: string) => w.posted.filter((m) => m.type === type && (verb === undefined || m.verb === verb)).length;
function answer(w: World, s: Status, m = lastOf(w, "fileComments", "status")): void {
  assert.ok(m, "a status ask is outstanding");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: m.reqId, ...s } }));
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
  return { unit, button, aside };
}
const card = (aside: El, key: string): El | null => aside.querySelector('.fc-card[data-id="' + key + '"]');
const act = (root: El, a: string, id?: string): El | null => root.querySelector('[data-act="' + a + '"]' + (id ? '[data-id="' + id + '"]' : ""));
const texts = (els: El[]) => els.map((e) => e.textContent);


// ── the panel, driven ─────────────────────────────────────────────────────────────────────────────
/** A pointer's click on `el`: detail 1, as a mouse or a finger dispatches it (the stand-in's click() is element.click(), detail 0). */
const mouse = (el: El): void => { dispatch(el, new Ev("click", { detail: 1 })); };
/** What the guard reads of a selection: its ends, with their offsets (a real Selection always carries them; endInside reads them). */
type Sel = { isCollapsed: boolean; anchorNode: El | Txt | null; focusNode: El | Txt | null; anchorOffset: number; focusOffset: number } | null;
type Outcome = { open: boolean; scrolled: number; focusMoved: boolean; asides: number };
/** Open the panel over the stand-in, fake the live selection as `selOf` reads it off the mark and the aside, activate the
 *  mark by the pointer or by Enter, and read what followed: the card's state, the scrolls, the focus, the aside count. */
async function activate(t: TestContext, act: "fcchange" | "fcopen", id: string, key: string, selOf: (mark: El, aside: El) => Sel, via: "mouse" | "enter" = "mouse"): Promise<Outcome> {
  const w = world(); t.after(() => w.close());
  t.after(() => { win.getSelection = () => null; });
  const { aside } = await openPanel(w, status());
  const mark = w.body.querySelector('[data-act="' + act + '"][data-id="' + id + '"]');
  assert.ok(mark, act + " " + id + " is marked in the body");
  assert.ok(mark!.childNodes[0] instanceof Txt, "the mark wraps its words");
  assert.equal(card(aside, key)!.classes.includes("open"), false, "the card starts collapsed");
  win.getSelection = () => selOf(mark!, aside);
  if (via === "enter") mark!.focus();
  const scrolls = scrolledInto.length, focus = doc.activeElement;
  if (via === "mouse") mouse(mark!);
  else dispatch(mark!, new Ev("keydown", { key: "Enter" }));   // the row's keydown: x.click(), a click with no pointer behind it
  await flush();
  const c = card(aside, key);
  return { open: !!c && c.classes.includes("open"), scrolled: scrolledInto.length - scrolls, focusMoved: doc.activeElement !== focus, asides: w.main.querySelectorAll(".fileview-aside").length };
}
const inMark = (m: El): Sel => ({ isCollapsed: false, anchorNode: m.childNodes[0], focusNode: m.childNodes[0], anchorOffset: 2, focusOffset: 9 });
const caretInMark = (m: El): Sel => ({ isCollapsed: true, anchorNode: m.childNodes[0], focusNode: m.childNodes[0], anchorOffset: 3, focusOffset: 3 });
const none = (): Sel => null;
const inAside = (_m: El, aside: El): Sel => { const head = aside.querySelector(".fc-card-head")!; return { isCollapsed: false, anchorNode: head, focusNode: head, anchorOffset: 0, focusOffset: 1 }; };
const halfIn = (m: El, aside: El): Sel => ({ isCollapsed: false, anchorNode: m.childNodes[0], focusNode: aside.querySelector(".fc-card-head"), anchorOffset: 2, focusOffset: 0 });
/** A selection standing elsewhere in the body: both ends in the Risks row's text, a Raw row that carries neither the
 *  change mark nor the comment highlight, so nothing of it lies in the clicked mark: the state a reader leaves by
 *  selecting a passage to read or copy, which a press on a deletion's label or on a mark inside a link does not collapse. */
const elsewhere = (m: El): Sel => {
  const body = m.closest(".fileview-body")!;
  const row = body.querySelectorAll(".fv-ct").find((ct) => ct.textContent.startsWith("Risks remain"))!;
  assert.ok(row && !row.contains(m) && !m.contains(row), "the Risks row stands apart from the mark");
  const words = row.childNodes[0];
  assert.ok(words instanceof Txt && !m.contains(words), "the selection's ends lie in another row's text, none in the mark");
  return { isCollapsed: false, anchorNode: words, focusNode: words, anchorOffset: 0, focusOffset: 5 };
};

test("a change mark: the pointer's click arriving with a selection inside the mark opens nothing — no card, no scroll, no focus change", async (t) => {
  const r = await activate(t, "fcchange", "h2", "chg:h2", inMark);
  assert.deepEqual(r, { open: false, scrolled: 0, focusMoved: false, asides: 1 }, JSON.stringify(r));
});

test("a change mark: a click with the selection collapsed, or none, opens the card as before", async (t) => {
  assert.equal((await activate(t, "fcchange", "h2", "chg:h2", caretInMark)).open, true, "a plain click leaves a caret: the card opens");
  assert.equal((await activate(t, "fcchange", "h2", "chg:h2", none)).open, true, "no selection at all: the card opens");
});

test("a change mark: a selection outside the body, or with one end outside the mark, is not the mark's drag — the card opens", async (t) => {
  assert.equal((await activate(t, "fcchange", "h2", "chg:h2", inAside)).open, true, "words selected in the aside: the card opens");
  assert.equal((await activate(t, "fcchange", "h2", "chg:h2", halfIn)).open, true, "a selection with its focus in the aside: the card opens");
});

test("a change mark: a selection standing elsewhere in the body, both ends in another row and none in the mark, is not this click's drag — the card opens, the same outcome as a plain click's (the guard's line is the clicked mark, not the body)", async (t) => {
  const r = await activate(t, "fcchange", "h2", "chg:h2", elsewhere);
  assert.equal(r.open, true, JSON.stringify(r));
  assert.ok(r.scrolled > 0, "…and the card's open scrolls the mark into view, as a plain click's does: " + JSON.stringify(r));
  const plain = await activate(t, "fcchange", "h2", "chg:h2", caretInMark);
  assert.deepEqual(r, plain, "the selection standing elsewhere changes nothing of the click: " + JSON.stringify({ r, plain }));
});

test("a change mark: Enter on the focused mark opens the card with the body selection standing (a click with no pointer behind it is never a drag's)", async (t) => {
  const r = await activate(t, "fcchange", "h2", "chg:h2", inMark, "enter");
  assert.equal(r.open, true, JSON.stringify(r));
});

test("a comment highlight: the same guard — the drag's click opens nothing, the caret's click opens the card, Enter opens it with the selection standing", async (t) => {
  const r = await activate(t, "fcopen", passage.id, passage.id, inMark);
  assert.deepEqual(r, { open: false, scrolled: 0, focusMoved: false, asides: 1 }, JSON.stringify(r));
  assert.equal((await activate(t, "fcopen", passage.id, passage.id, caretInMark)).open, true, "the caret's click opens the comment's card");
  assert.equal((await activate(t, "fcopen", passage.id, passage.id, inMark, "enter")).open, true, "Enter opens it");
});

test("a comment highlight: a selection standing elsewhere in the body, none of it in the highlight, is not its drag either — the card opens, the same outcome as a plain click's", async (t) => {
  const r = await activate(t, "fcopen", passage.id, passage.id, elsewhere);
  assert.equal(r.open, true, JSON.stringify(r));
  const plain = await activate(t, "fcopen", passage.id, passage.id, caretInMark);
  assert.deepEqual(r, plain, "the selection standing elsewhere changes nothing of the click: " + JSON.stringify({ r, plain }));
});
