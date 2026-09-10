// The sequential hint for a comment with no stored position (plans/markdown-viewer.md Slice 5, item 7; file-comments.ts paintAll,
// nextCopyHint). The painter hands the engine a comment's stored position (`anchorAt`) as the tie-break, so a comment on a passage
// that recurs with the same surroundings is highlighted on the copy that was chosen (file-comments-anchors.test.ts). A comment with
// NO position, written by the CLI or another editor, took no hint, so two such comments with the same anchor both painted on the
// first copy (the Slice 5 probe (g)'s remainder). Now the second takes a sequential hint, a position whose nearest tied copy is the
// copy after the previous same-anchor card's, so same-text comments without a position take the copies in turn; the pick stays a
// guess (the dashed cue and the "passage recurs" tag: copyUnsure reads the stored position, never the hint); a card WITH a position
// is unaffected wherever it stands in the order; a card whose copies are used up falls back to the engine's earliest pick, as
// before; a comment with a unique anchor takes no hint. Two shapes: a paragraph repeated three times, whose copies stand a
// thousand characters apart (the engine picks the tied copy nearest the hint, so the previous copy's end alone would name the
// same copy again: the probe steps the hint right until the pick moves), and a short line repeated back to back with a two-
// character context, the shape of the probe. Driven over the behavior suite's DOM stand-in (the Raw view's rows), the row a mark
// sits in telling the copies apart. Nodes hide their edges at construction (hideEdges, ui/test-dom-shim.ts). Synthetic fixtures
// only: the notes-api world, placeholder ids.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import type { FileViewActionCtx } from "./file-view";
import type { Status, StoreComment } from "./file-comments-model";
import { makeAnchor, locateComment } from "./anchor-map";
import { hideEdges } from "../test-dom-shim";

// ── fixtures: the notes-api world, a report whose paragraph recurs three times, a thousand characters apart ──
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const ROOT = "/repo/notes-api";
const STORE_PATH = ROOT + "/.trackchanges/docs%2Freport.md.json";
const T0 = 1757145600000;
const PARA = ("The quick brown fox jumps over the lazy dog. ".repeat(12) + "Here is the marker phrase to comment on. " + "Pack my box with five dozen liquor jugs. ".repeat(12)).trim();
const UNIQUE = "A closing line that occurs once.";
const DOC = "# Report\n\n" + PARA + "\n\n" + PARA + "\n\n" + PARA + "\n\n" + UNIQUE + "\n";
const MARKER = "the marker phrase";
const FIRST = DOC.indexOf(MARKER), SECOND = DOC.indexOf(MARKER, FIRST + 1), THIRD = DOC.indexOf(MARKER, SECOND + 1);
assert.ok(FIRST > 0 && SECOND > FIRST && THIRD > SECOND, "three copies");
assert.ok(SECOND - FIRST > 900, "the copies stand far apart: " + (SECOND - FIRST));
// the browser's own anchor (24 characters of context), made at the first copy: it ties at all three
const TIED = makeAnchor(DOC, { start: FIRST, end: FIRST + MARKER.length });
assert.equal(locateComment(DOC, TIED, 0).range!.start, FIRST); assert.equal(locateComment(DOC, TIED, DOC.length).range!.start, THIRD);
const ONCE = makeAnchor(DOC, { start: DOC.indexOf(UNIQUE), end: DOC.indexOf(UNIQUE) + UNIQUE.length });
const comment = (id: string, ts: number, anchor: StoreComment["anchor"], anchorAt?: number): StoreComment =>
  ({ id, author: "you", ts, body: "Note " + id + ".", anchor, ...(anchorAt === undefined ? {} : { anchorAt }), replies: [], resolved: false });
// in cards() order (by time): two positionless comments on the tied anchor, one WITH a position naming the third copy, a fourth
// positionless one, and a positionless comment on the unique line
const N1 = comment(T0 + "-1", T0 + 1000, TIED);
const N2 = comment(T0 + "-2", T0 + 2000, TIED);
const S3 = comment(T0 + "-3", T0 + 3000, TIED, THIRD);
const N4 = comment(T0 + "-4", T0 + 4000, TIED);
const U5 = comment(T0 + "-5", T0 + 5000, ONCE);
function status(comments: StoreComment[]): Status {
  return {
    verb: "status", root: ROOT, storePath: STORE_PATH, trackedBy: null, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: null,
    store: { v: 3, path: "docs/report.md", suggestions: [], comments },
    hunks: [], log: [],
    unsent: { comments: comments.map((c) => c.id), replies: [], accepted: 0, rejected: 0, watermark: null },
  };
}

// ── the DOM stand-in (the behavior suite's): ancestry, attributes, events, a small selector engine ──
class Ev {
  target: El | Txt | null = null;
  currentTarget: El | null = null;
  defaultPrevented = false;
  stopped = false;
  key: string;
  detail = 0;
  constructor(public type: string, init: { key?: string } = {}) { this.key = init.key || ""; hideEdges(this); }
  preventDefault(): void { this.defaultPrevented = true; }
  stopPropagation(): void { this.stopped = true; }
}
type Listener = (ev: Ev) => void;
type Reg = { type: string; cb: Listener; capture: boolean };
const kebab = (k: string) => k.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
class Txt {
  nodeType = 3;
  parentNode: El | null = null;
  constructor(public data: string) { hideEdges(this); }
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
  constructor(tag: string) { this.tagName = tag.toUpperCase(); hideEdges(this); }
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
const doc = hideEdges({
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
});
doc.body = new El("body");
/** The DOM event path: document capture, ancestors' capture root to target, target and ancestors' bubble, document bubble. */
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
hideEdges(win);
(globalThis as any).window = win;
(globalThis as any).document = doc;
const store = new Map<string, string>();
(globalThis as any).localStorage = {
  getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
  setItem: (k: string, v: string) => { store.set(k, String(v)); },
  removeItem: (k: string) => { store.delete(k); },
};

// ── the viewer stand-in: the body row with Raw rows, the seam as closures, the poll's HEAD answers ──
type World = { ctx: FileViewActionCtx; posted: any[]; main: El; body: El; code: El; hooks: { rendered: Array<() => void>; close: Array<() => void> }; mtimes: Record<string, string>; close(): void };
let cur: World | null = null;
(globalThis as any).fetch = async (url: string) => {
  if (url.includes("/sessions")) return { json: async () => [] };
  const p = decodeURIComponent((/[?&]path=([^&]*)/.exec(url) || [])[1] || "");
  const mt = cur!.mtimes[p];
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
function world(text: string): World {
  const main = new El("div"); main.className = "fileview-main";
  const body = new El("div"); body.className = "fileview-body";
  const wrap = new El("div"); wrap.className = "fileview-code";
  const pre = new El("pre"); pre.className = "fileview-pre fileview-wrap";
  const code = new El("code"); code.className = "hljs";
  pre.appendChild(code); wrap.appendChild(pre);
  body.appendChild(wrap);
  main.appendChild(body);
  rows(code, text);
  const w = { posted: [] as any[], main, body, code, hooks: { rendered: [] as Array<() => void>, close: [] as Array<() => void> }, mtimes: {} as Record<string, string> } as World;
  w.ctx = {
    path: ABS, sid: SID, todoId: null,
    body: () => body as unknown as HTMLElement, mode: () => "raw", text: () => text, mtimeNs: () => "1757145600000000001", media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [],
    identity: () => ({ name: "api", color: null }),
    onRendered: (cb) => { w.hooks.rendered.push(cb); }, onSelection: () => { /* inert */ },
    onSaved: () => { /* inert */ }, onClose: (cb) => { w.hooks.close.push(cb); },
    post: (m) => { w.posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: () => { /* inert */ }, editing: () => false, setTrackedEdit: () => { /* inert */ }, guardClose: () => { /* inert */ },
    aside: (node) => { main.querySelector(".fileview-aside")?.remove(); if (node) { const n = node as unknown as El; n.classList.add("fileview-aside"); main.appendChild(n); } },
    setMode: () => { /* inert */ }, scrollToOffset: () => { /* inert */ },
    reload: () => { rows(code, text); for (const cb of w.hooks.rendered) cb(); },
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
}
async function openPanel(w: World, s: Status): Promise<{ aside: El }> {
  const fc = await import("./file-comments");
  const unit = fc.fileCommentsAction.mount(w.ctx) as unknown as El;
  const button = unit.childNodes[0] as El;
  answer(w, s); await flush();
  button.click();
  answer(w, s); await flush(); await flush();
  const aside = w.main.querySelector(".fileview-aside")!;
  assert.ok(aside, "the panel is mounted beside the body");
  return { aside };
}
type Painted = { row: number; text: string; dashed: boolean; tagged: boolean };
/** Where a comment's highlight sits (the 0-based row of the Raw view), its text, whether it wears the guess's dashed cue, and
 *  whether its card wears the "passage recurs" tag. */
function painted(w: World, aside: El, id: string): Painted {
  const marks = w.code.querySelectorAll('mark.fc-hl[data-id="' + id + '"]');
  assert.equal(marks.length, 1, id + " paints one highlight");
  const row = w.code.childNodes.indexOf(marks[0].closest(".fv-cl")!);
  const tag = aside.querySelector('.fc-card[data-id="' + id + '"] .fc-tag');
  return { row, text: marks[0].textContent, dashed: marks[0].classes.includes("fc-hl-context"), tagged: !!tag && tag.textContent === "passage recurs" };
}
// the rows: the title, a blank, the first copy (2), a blank, the second (4), a blank, the third (6), a blank, the closing line (8)
const ROW = { first: 2, second: 4, third: 6, unique: 8 };

test("two comments without a position on a passage repeated three times, far apart: the first paints on the first copy and the second on the SECOND (the sequential hint; before, both on the first), both as guesses; one with a stored position is unaffected; a fourth with the copies used up falls back to the earliest; a unique anchor takes no hint", async (t: TestContext) => {
  const w = world(DOC); t.after(() => w.close());
  const { aside } = await openPanel(w, status([N1, N2, S3, N4, U5]));
  assert.deepEqual(painted(w, aside, N1.id), { row: ROW.first, text: MARKER, dashed: true, tagged: true }, "the first positionless comment: the engine's earliest pick, a guess");
  assert.deepEqual(painted(w, aside, N2.id), { row: ROW.second, text: MARKER, dashed: true, tagged: true }, "the second takes the copy after the first's (before this slice: the first copy again), still a guess: nothing vouches for it");
  assert.deepEqual(painted(w, aside, S3.id), { row: ROW.third, text: MARKER, dashed: false, tagged: false }, "a stored position names its copy whatever came before it in the order, and is no guess");
  assert.deepEqual(painted(w, aside, N4.id), { row: ROW.first, text: MARKER, dashed: true, tagged: true }, "no copy follows the previous card's (the third): the engine's earliest pick stands, as before the hint");
  assert.deepEqual(painted(w, aside, U5.id), { row: ROW.unique, text: UNIQUE, dashed: false, tagged: false }, "a unique anchor: its one copy, no guess");
  // the mark's own words say what the card says: no position stored, so this is a guess and not a confirmed copy
  const m2 = w.code.querySelector('mark.fc-hl[data-id="' + N2.id + '"]')!;
  assert.match(m2.title, /stores no position/, "the second copy's title names the missing position, never the hint as a choice");
});

test("the hint is scoped to an EQUAL anchor: a positionless comment whose anchor differs in context from the ones before it takes none, and paints where the engine puts it alone", async (t: TestContext) => {
  // the same quote with the host's widest context (480 characters), which still lies inside the paragraph's own text, so it ties at
  // all three copies as the browser's anchor does; to the hint it is another anchor. After N1 and N2 on the first two copies, a
  // hint that read ANY previous same-quote card would name the third copy; scoped to the equal anchor, it takes the first, the
  // engine's earliest tied pick, as it does alone
  const wide = { quote: MARKER, prefix: DOC.slice(SECOND - 480, SECOND), suffix: DOC.slice(SECOND + MARKER.length, SECOND + MARKER.length + 480) };
  assert.equal(locateComment(DOC, wide).range!.start, FIRST); assert.equal(locateComment(DOC, wide, DOC.length).range!.start, THIRD, "ties at the copies");
  const other = comment(T0 + "-6", T0 + 6000, wide);
  const w = world(DOC); t.after(() => w.close());
  const { aside } = await openPanel(w, status([N1, N2, other]));
  assert.deepEqual([painted(w, aside, N1.id).row, painted(w, aside, N2.id).row], [ROW.first, ROW.second]);
  assert.deepEqual(painted(w, aside, other.id), { row: ROW.first, text: MARKER, dashed: true, tagged: true }, "no hint for it: the engine's earliest tied copy, a guess (an unscoped hint would have put it on the third)");
});

test("the probe's shape: a short line repeated back to back, two positionless comments with a two-character context (an anchor another editor wrote) take the two copies in turn, and a third with no copy left takes the first again", async (t: TestContext) => {
  const LINE = "Repeated line here.";
  const SRC = "# Report\n\n" + LINE + "\n\n" + LINE + "\n\n" + UNIQUE + "\n";
  const short = { quote: LINE, prefix: "\n\n", suffix: "\n\n" };
  assert.equal(locateComment(SRC, short, 0).range!.start, SRC.indexOf(LINE)); assert.equal(locateComment(SRC, short, SRC.length).range!.start, SRC.indexOf(LINE, SRC.indexOf(LINE) + 1), "the anchor ties at both copies");
  const a = comment(T0 + "-7", T0 + 7000, short), b = comment(T0 + "-8", T0 + 8000, short), c = comment(T0 + "-9", T0 + 9000, short);
  const w = world(SRC); t.after(() => w.close());
  const { aside } = await openPanel(w, status([a, b, c]));
  assert.deepEqual([painted(w, aside, a.id).row, painted(w, aside, b.id).row, painted(w, aside, c.id).row], [2, 4, 2], "the first copy, the second, and the first again");
  assert.ok([a, b, c].every((x) => painted(w, aside, x.id).dashed && painted(w, aside, x.id).tagged), "every one a guess: the dashed cue and the tag");
});
