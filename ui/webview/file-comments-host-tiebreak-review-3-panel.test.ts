// The recurring-passage tie-break, the review's third round (2026-09-11; plans/file-review.md, decision 51): the PANEL's
// half of the state the host module of the same stem, tools/file-comments-host-tiebreak-review-3.test.mjs, pins on the
// host. The state: a passage comment whose QUOTE sits at its stored position while the surroundings there were edited,
// the whole anchor still matching at the other copies. The host's one reader of a stored anchor answers the position
// itself (locateStored's `position`, quoteSitsAt), and the reply's placed map carries no entry for the comment
// (placedFor), on the stated ground that the panel paints the nearest WHOLE copy as a guess: its engine scores a whole
// copy over an edited one (locateComment), and copyUnsure finds the stored position at none of the tied copies. So the
// two halves place the comment on different copies, on purpose: the host on the quote at the position, the panel on a
// whole copy elsewhere, in the dashed cue with the words of a stale position, never plainly on either. Until this module
// the panel's half stood only in the host module's prose: no panel fixture left the quote exactly at anchorAt with
// edited context and whole copies elsewhere (the tie-break modules open ABOVE, whose position names nothing, and NEAR
// with the position seven characters before the quote), so a panel that trusted the quote at the position and painted
// it plainly passed every panel module (the review's third round). Four legs: the state after a tracked edit inside the
// chosen copy's context (the position carried to the quote, the copy fields standing) with no entry; the same after a
// raw edit of the surroundings alone (the position unchanged, still the quote's); the entry the host declines to
// forward, had it forwarded it (the panel paints no confirmed copy from an offset the whole anchor is not at, and its
// words then name a last confirmed place that is the quote's own position: forwarding closes nothing); and the real
// host as a child process over the finding's own scenario (two copies under one heading and one under another, a
// tracked two-character insertion inside the first copy's prefix, a write), its reply fed to the panel as the kernel
// forwards it (every success field), in the window before the write and after it. Driven over the DOM stand-in
// file-comments-tiebreak.test.ts uses. Synthetic fixtures only: the notes-api world under a scratch directory,
// placeholder ids.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { spawnSync } from "node:child_process";
import { hideEdges } from "../test-dom-shim";
import type { FileViewActionCtx, TrackedEdit } from "./file-view";
import type { Placed, Status, StoreComment } from "./file-comments-model";
import { locateComment, makeAnchor } from "./anchor-map";

// ── a DOM stand-in: ancestry, attributes, events with capture and bubbling, a small selector engine ──
class Ev {
  target: El | Txt | null = null;
  currentTarget: El | null = null;
  defaultPrevented = false;
  stopped = false;
  key: string;
  ctrlKey: boolean; metaKey: boolean;
  constructor(public type: string, init: { key?: string; ctrlKey?: boolean; metaKey?: boolean } = {}) { this.key = init.key || ""; this.ctrlKey = !!init.ctrlKey; this.metaKey = !!init.metaKey; hideEdges(this); }
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



// ── fixtures: the notes-api world, a report whose paragraph recurs three times ─────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const ROOT = "/repo/notes-api";
const STORE_PATH = ROOT + "/.trackchanges/docs%2Freport.md.json";
const T0 = 1757145600000;
// the tie-break modules' paragraph: a phrase in its middle has the same surroundings for more than the host's widening
// cap (480 characters) on both sides of every copy, so every anchor on it ties
const PARA = ("The quick brown fox jumps over the lazy dog. ".repeat(12)
  + "Here is the marker phrase to comment on. "
  + "Pack my box with five dozen liquor jugs. ".repeat(12)).trim();
const DOC = "# Report\n\n" + PARA + "\n\n" + PARA + "\n\n" + PARA + "\n";
const MARKER = "the marker phrase";
const FIRST = DOC.indexOf(MARKER);
const SECOND = DOC.indexOf(MARKER, FIRST + 1);
const THIRD = DOC.indexOf(MARKER, SECOND + 1);
assert.ok(FIRST > 0 && SECOND > FIRST && THIRD > SECOND, "the fixture has three copies");
// DOC's Raw rows: the title, a blank, then the copies with a blank between each
const FIRST_ROW = 2;
const SECOND_ROW = 4;
const THIRD_ROW = 6;
// the anchor the host stores at its cap for the second copy (engine.makeAnchor with 480 characters of context)
const CAP_ANCHOR = { quote: MARKER, prefix: DOC.slice(SECOND - 480, SECOND), suffix: DOC.slice(SECOND + MARKER.length, SECOND + MARKER.length + 480) };
// a tracked edit inside the second copy's context before the passage (the tie-break modules' NEAR): the quote moves
// seven characters on, the other two copies stay whole, and the host's refresh carries the position to the quote
// (movedCopy's occurrences), leaving the copy fields as they were
const NEAR = DOC.slice(0, SECOND - "Here is ".length) + "Here, then, is " + DOC.slice(SECOND);
const NEAR_AT = SECOND + "Here, then, is ".length - "Here is ".length;
// a raw edit of the second copy's context after the passage: the quote stays where the position says, the third copy
// moves two characters on
const SUFFIX = DOC.slice(0, DOC.indexOf("Pack my box", SECOND)) + "Pack my crate" + DOC.slice(DOC.indexOf("Pack my box", SECOND) + "Pack my box".length);
const ID = T0 + "-" + SECOND;
/** The comment as the host leaves it in this state: the position at the quote, the copy fields standing (stampCopy
 *  writes none for a position among no whole match, so the ones written at creation stay). The panel reads none of
 *  the fields; they are here so the store is the host's. */
const atQuote = (anchorAt: number): StoreComment => ({
  id: ID, author: "you", ts: T0, body: "Say it once.", anchor: CAP_ANCHOR, anchorAt, ordinal: 2, copies: 3, section: "Report", replies: [], resolved: false,
});
// the panel's words, copied here so a swap or a rewording fails a driven test: the stored-position state, the state a
// confirmed place the view's text lacks puts a card in, and the mark's title on each
const CONFIRM = " Reveal it and save again from the right copy to confirm.";
const UNSURE_POSITION = "This passage occurs in the file more than once with the same surroundings, and the position stored with the comment names none of the copies as the file is now, so the copy nearest that position is highlighted, not a confirmed one." + CONFIRM;
const UNSURE_CONFIRMED_PLACE = "This passage occurs in the file more than once with the same surroundings, and the place where the comment's copy was last confirmed names none of the copies as the file is now, so the copy nearest that place is highlighted, not a confirmed one." + CONFIRM;
const MARK_POSITION = "Open the comment; this passage recurs, and this copy is the nearest to the comment's stored position, not a confirmed one";
const MARK_CONFIRMED_PLACE = "Open the comment; this passage recurs, and this copy is the nearest to where the comment's copy was last confirmed, not a confirmed one";
const storeWith = (comments: StoreComment[]): Status["store"] => ({ v: 3, path: "docs/report.md", suggestions: [], comments });
function status(over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: ROOT, storePath: STORE_PATH, trackedBy: null, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: null,
    store: storeWith([]),
    hunks: [], log: [],
    unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null },
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
function world(over: { path?: string; sid?: string | null; todoId?: string | null; src?: string; mtimeNs?: string } = {}): World {
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
    body: () => body as unknown as HTMLElement, mode: () => "raw", text: () => text, mtimeNs: () => over.mtimeNs ?? "1757145600000000001", media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [],
    identity: () => ({ name: "api", color: null }),
    onRendered: (cb) => { w.hooks.rendered.push(cb); }, onSelection: (cb) => { w.hooks.selection.push(cb); },
    onSaved: (cb) => { w.hooks.saved.push(cb); }, onClose: (cb) => { w.hooks.close.push(cb); },
    post: (m) => { w.posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: () => { /* inert */ }, editing: () => w.editing, setTrackedEdit: (t) => { w.tracked = t; }, guardClose: () => { /* inert */ },   // the viewer's close ask (main, 2026-09-07): the stand-in asks nothing
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
function answer(w: World, s: Status, m = lastOf(w, "fileComments", "status")): void {
  assert.ok(m, "a status ask is outstanding");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: m.reqId, ...s } }));
  // the poll's baseline follows the reply: the HEADs answer these mtimes until a test moves one
  w.mtimes[w.ctx.path] = s.fileMtimeNs;
  if (s.storePath && s.storeMtimeNs !== null) w.mtimes[s.storePath] = s.storeMtimeNs;
  if (s.root && s.configMtimeNs !== null) w.mtimes[s.root + "/.trackchanges/config.json"] = s.configMtimeNs;
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



/** The row (0-based line) a mark sits in: the `.fv-cl` ancestor's index among the code's rows. */
function rowOf(w: World, mark: El): number { return w.code.childNodes.indexOf(mark.closest(".fv-cl")!); }
const headOf = (aside: El, id: string): El => aside.querySelector('.fc-card[data-id="' + id + '"] .fc-card-head')!;
const tagsOf = (head: El): El[] => head.querySelectorAll(".fc-tag");
const marksOf = (w: World): El[] => w.code.querySelectorAll(".fc-hl");
const marksInRow = (w: World, row: number): number => (w.code.childNodes[row] as El).querySelectorAll(".fc-hl").length;
/** The row (0-based line) an offset of `text` falls in. */
const rowAt = (text: string, at: number): number => text.slice(0, at).split("\n").length - 1;
/** The n-th (0-based) occurrence of `quote` in `text`. */
function nth(text: string, quote: string, n: number): number {
  let i = -1;
  for (let k = 0; k <= n; k++) i = text.indexOf(quote, i + 1);
  assert.ok(i >= 0, "the fixture lacks occurrence " + n + " of " + JSON.stringify(quote));
  return i;
}

// ── the panel's half of the split: the nearest whole copy, dashed, and nothing at the quote ──────────

/** The paint this module is about: ONE highlight, on `row`, in the dashed cue with `markTitle`; the card wears the
 *  "passage recurs" tag with `words`, and its open card says them; and the row the quote sits in (`quoteRow`, where the
 *  host's own reader places the comment) wears no mark of the comment's. `id` is the comment's: the module's own for the
 *  stand-in store, the host's minted one for the real reply. A panel that trusted the quote at the stored position would
 *  paint `quoteRow` plainly, with no tag, and fail here on every line. */
function assertGuessedOn(w: World, aside: El, id: string, row: number, quoteRow: number, markTitle: string, words: string): void {
  const marks = marksOf(w);
  assert.equal(marks.length, 1, "one highlight");
  assert.equal(marks[0].textContent, MARKER);
  assert.equal(rowOf(w, marks[0]), row, "the copy nearest the hint among the copies still whole: the engine's pick");
  assert.ok(marks[0].classList.contains("fc-hl-context"), "the dashed cue: a guess, not the copy chosen");
  assert.equal(marks[0].title, markTitle);
  assert.equal(marksInRow(w, quoteRow), 0, "the quote at the stored position, the copy the host's own reader places the comment on, wears no mark: the panel's engine scores a whole copy over an edited one");
  const head = headOf(aside, id);
  // the tag among the card's: a comment with replies (the real host's, after the write) wears its reply count beside it
  const recurs = tagsOf(head).filter((x) => x.textContent === "passage recurs");
  assert.equal(recurs.length, 1, "the passage recurs tag, once");
  assert.equal(recurs[0].title, words);
  head.click();
  const note = aside.querySelector('.fc-card.open[data-id="' + id + '"] .fc-note');
  assert.ok(note, "the open card says it in words");
  assert.equal(note!.textContent, words);
}

test("the quote sits at the stored position inside a copy whose context a tracked edit changed (the position carried to the quote, the copy fields standing), and the reply has no entry for the comment: the panel paints the nearest WHOLE copy, the third, in the dashed cue with the stored-position words, and nothing on the second, where the host's reader places it", async (t: TestContext) => {
  // the fixture: the quote alone sits at the position, the whole anchor at the first and the third copies (the engine's
  // earliest and latest picks), and from the position the third is the nearer (the first is seven characters farther)
  assert.ok(NEAR.startsWith(MARKER, NEAR_AT), "the quote sits at the carried position");
  assert.equal(locateComment(NEAR, CAP_ANCHOR, 0).range!.start, FIRST);
  assert.equal(locateComment(NEAR, CAP_ANCHOR, NEAR.length).range!.start, THIRD + 7);
  assert.equal(rowAt(NEAR, NEAR_AT), SECOND_ROW);
  const w = world({ src: NEAR }); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ store: storeWith([atQuote(NEAR_AT)]), placed: {} }));
  assertGuessedOn(w, aside, ID, THIRD_ROW, SECOND_ROW, MARK_POSITION, UNSURE_POSITION);
});

test("a raw edit of the surroundings after the quote alone: the position is unchanged and still the quote's, the whole anchor sits at the other two copies, and with no entry the panel paints the nearer of them, the first, as a guess with the stored-position words", async (t: TestContext) => {
  assert.ok(SUFFIX.startsWith(MARKER, SECOND), "the quote still sits at the position");
  assert.equal(locateComment(SUFFIX, CAP_ANCHOR, 0).range!.start, FIRST);
  assert.equal(locateComment(SUFFIX, CAP_ANCHOR, SUFFIX.length).range!.start, THIRD + 2, "the third copy moved two characters on, so the first is the nearer to the position");
  const w = world({ src: SUFFIX }); t.after(() => w.close());
  const { aside } = await openPanel(w, status({ store: storeWith([atQuote(SECOND)]), placed: {} }));
  assertGuessedOn(w, aside, ID, FIRST_ROW, SECOND_ROW, MARK_POSITION, UNSURE_POSITION);
});

test("had the host forwarded its position verdict as an entry (the shape the third round declines to send): the panel would still paint the whole copy, dashed, and its words would name a last confirmed place that is the quote's own position, so forwarding would close nothing and mislead; the drop stands", async (t: TestContext) => {
  const w = world({ src: NEAR }); t.after(() => w.close());
  const forwarded = { at: NEAR_AT, confirmed: true, by: "position" } as unknown as Placed;
  const { aside } = await openPanel(w, status({ store: storeWith([atQuote(NEAR_AT)]), placed: { [ID]: forwarded } }));
  assertGuessedOn(w, aside, ID, THIRD_ROW, SECOND_ROW, MARK_CONFIRMED_PLACE, UNSURE_CONFIRMED_PLACE);
});

// ── the real host over the finding's scenario, its reply fed to the panel ───────────────────────────

const REPO = path.resolve(process.cwd(), "..");
const HOST = path.join(REPO, "tools", "file-comments-host.mjs");
const VENDOR = path.join(REPO, "vendor", "track-changents");
// two copies under one heading and a third under another (the host module's ALPHA): the state in which, before the
// third round, the section rule confirmed the second copy under the heading while the reply's own anchorAt named the
// first, and the panel painted the second plainly
const ALPHA = "# Report\n\nA short opening line that occurs once.\n\n## Alpha\n\n" + PARA + "\n\n" + PARA + "\n\n## Beta\n\n" + PARA + "\n";
type HostWorld = { home: string; alpha: string };
function hostWorld(t: TestContext): HostWorld {
  const scratch = fs.mkdtempSync(path.join(os.tmpdir(), "romp-fc-tiebreak-r3-panel-"));
  t.after(() => { try { fs.rmSync(scratch, { recursive: true, force: true }); } catch { /* ignore */ } });
  const home = path.join(scratch, "home");
  const root = path.join(home, "notes-api");
  fs.mkdirSync(path.join(root, ".git"), { recursive: true });
  fs.mkdirSync(path.join(root, "docs"));
  const alpha = path.join(root, "docs", "alpha.md");
  fs.writeFileSync(alpha, ALPHA);
  return { home, alpha };
}
/** The host's environment, as the host module builds it: the scratch home, no root override, and the session's identity
 *  only where the session did something (the CLI). */
function hostEnv(hw: HostWorld, extra: Record<string, string> = {}): NodeJS.ProcessEnv {
  const e: NodeJS.ProcessEnv = { ...process.env, FILE_COMMENTS_HOME: hw.home, ...extra };
  delete e.TRACKCHANGES_ROOT;
  if (!("ROMP_SID" in extra)) { delete e.ROMP_SID; delete e.ROMP_SESSION_NAME; }
  return e;
}
type Reply = Status & { ok: boolean };
/** One verb through the real host as a child process: the reply parsed, ok:true asserted. */
function host(hw: HostWorld, req: { verb: string; path: string; args: Record<string, unknown>; fence?: Record<string, string> }): Reply {
  const r = spawnSync(process.execPath, [HOST], { input: JSON.stringify(req), encoding: "utf8", env: hostEnv(hw), timeout: 60000, maxBuffer: 64 * 1024 * 1024 });
  assert.equal(r.status, 0, "the host exits 0: " + r.stderr);
  const json = JSON.parse(r.stdout) as Reply;
  assert.equal(json.ok, true, "ok:true, got " + r.stdout.slice(0, 300));
  assert.equal(json.verb, req.verb);
  return json;
}
const fenceFor = (s: Status): Record<string, string> => ({ storeMtimeNs: s.storeMtimeNs == null ? "" : s.storeMtimeNs });
/** The session's edit, on record: the vendored track-edit CLI, as the host module drives it. */
function trackedEdit(hw: HostWorld, old: string, now: string): void {
  const r = spawnSync(process.execPath, [path.join(VENDOR, "cli", "track-edit.mjs"), "--file", hw.alpha, "--old", old, "--new", now],
    { encoding: "utf8", env: hostEnv(hw, { ROMP_SESSION_NAME: "web", ROMP_SID: SID }), timeout: 60000 });
  assert.equal(r.status, 0, "track-edit: " + r.stderr);
}

test("the real host over the finding's scenario: a comment on the first of two copies under one heading, a tracked two-character insertion inside that copy's prefix, a write; the reply's position is the quote's own offset and its placed map is empty, and the panel fed that very reply paints the second copy under the heading, dashed, with the stored-position words, and nothing on the first, before the write and after it", async (t: TestContext) => {
  const hw = hostWorld(t);
  const idx = nth(ALPHA, MARKER, 0);
  const st0 = host(hw, { verb: "status", path: hw.alpha, args: {} });
  const made = host(hw, { verb: "comment", path: hw.alpha, args: { anchor: makeAnchor(ALPHA, { start: idx, end: idx + MARKER.length }), note: "Say it once.", hintOffset: idx }, fence: fenceFor(st0) });
  const c = made.store!.comments[0];
  assert.equal(c.anchorAt, idx);
  assert.deepEqual([c.ordinal, c.copies, c.section], [1, 3, "Report > Alpha"], "the host's copy fields at creation");
  // the session inserts two characters inside the first copy's 480-character prefix; the heading makes the --old unique
  const head = "## Alpha\n\n" + PARA.slice(0, 100);
  assert.equal(ALPHA.indexOf(head), ALPHA.lastIndexOf(head), "the fixture: unique --old");
  trackedEdit(hw, head, head + "X ");
  const edited = fs.readFileSync(hw.alpha, "utf8");
  const quoteAt = idx + 2;
  assert.equal(nth(edited, MARKER, 0), quoteAt, "the fixture: the quote moved by two");
  const second = nth(edited, MARKER, 1);
  const third = nth(edited, MARKER, 2);
  // the panel's engine over the anchor the host widened: whole at the second and the third copies alone, and from the
  // position, stale or carried, it picks the second, the nearer
  assert.equal(locateComment(edited, c.anchor!, 0).range!.start, second);
  assert.equal(locateComment(edited, c.anchor!, edited.length).range!.start, third);
  assert.equal(locateComment(edited, c.anchor!, idx).range!.start, second);
  assert.equal(locateComment(edited, c.anchor!, quoteAt).range!.start, second);
  // the window before the write: the disk's position two characters stale, and no entry (the recorded edit carries the
  // position to the quote inside the first copy, not to the second)
  const before = host(hw, { verb: "status", path: hw.alpha, args: {} });
  assert.equal(before.store!.comments[0].anchorAt, idx, "a read rewrites nothing");
  assert.deepEqual(before.placed, {}, "no entry before the write");
  // the write: the refresh carries the position to the quote, the fields stand, and no entry either
  const written = host(hw, { verb: "reply", path: hw.alpha, args: { commentId: c.id, note: "Still once." }, fence: fenceFor(before) });
  assert.equal(written.store!.comments[0].anchorAt, quoteAt, "the recorded change carried the position to where it left the quote");
  assert.deepEqual([written.store!.comments[0].ordinal, written.store!.comments[0].copies, written.store!.comments[0].section], [1, 3, "Report > Alpha"]);
  assert.deepEqual(written.placed, {}, "no entry on the write");
  const after = host(hw, { verb: "status", path: hw.alpha, args: {} });
  assert.equal(after.store!.comments[0].anchorAt, quoteAt);
  assert.ok(edited.startsWith(MARKER, after.store!.comments[0].anchorAt!), "the host's half: the quote sits at the stored position");
  assert.deepEqual(after.placed, {}, "and no entry on every later status");
  assert.equal(after.fileMtimeNs, before.fileMtimeNs, "the write touched the sidecar, not the file");
  // the edited file's Raw rows: the title, a blank, the opening line, a blank, the heading, a blank, the first copy, a
  // blank, the second, a blank, the second heading, a blank, the third
  const quoteRow = rowAt(edited, quoteAt);
  const secondRow = rowAt(edited, second);
  assert.deepEqual([quoteRow, secondRow, rowAt(edited, third)], [6, 8, 12]);
  // the panel over the file as the edit left it, fed the reply after the write as the kernel forwards it (every success
  // field): the second copy, dashed, with the words of a stale position, and nothing on the first
  const w = world({ path: hw.alpha, src: edited, mtimeNs: after.fileMtimeNs ?? undefined }); t.after(() => w.close());
  const { aside } = await openPanel(w, after);
  assertGuessedOn(w, aside, String(c.id), secondRow, quoteRow, MARK_POSITION, UNSURE_POSITION);
  w.close();
  // and in the window before the write, from the stale position, the same paint
  const w2 = world({ path: hw.alpha, src: edited, mtimeNs: before.fileMtimeNs ?? undefined }); t.after(() => w2.close());
  const { aside: aside2 } = await openPanel(w2, before);
  assertGuessedOn(w2, aside2, String(c.id), secondRow, quoteRow, MARK_POSITION, UNSURE_POSITION);
});
