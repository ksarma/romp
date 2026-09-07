// The Comments panel's change cards WHILE THE EDITOR IS UP (plans/file-review.md, Slice 5; the 2026-09-06 review of
// the slice). The editor carries the sidecar's records as its own marks and Save writes them back, fenced on the
// sidecar they came from, so while it is up a decision from a card would move that sidecar under the editor and every
// later Save could only refuse, with the typed text stranded. Driven as a panel over the behavior suite's DOM stand-in:
// Accept, Reject, Accept all and Reject all answer in place with where to decide and ask the kernel nothing; the foot
// says it without a click; the send confirm offers no accept-all; the seed-fenced Save still goes through; the cards
// are live again once the edit ends. Also: routesSave holds while records are in the editor (a sidecar pruned under the
// edit refuses the save, never re-routes it to saveFile), the moved-under-edit row's ✕ dismisses the words and not the
// re-read Cancel owes, and Reveal and the card links (which act on a read view the editor has replaced) are not
// offered while editing. Synthetic fixtures only: the notes-api world, placeholder ids.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx, TrackedEdit } from "./file-view";
import type { Status, StoreComment, Hunk } from "./file-comments-model";
import { MOVED_UNDER_EDIT } from "./file-comments-model";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const SRC = web("file-comments.ts");

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


// ── fixtures: the notes-api world, with two pending changes ────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const ROOT = "/repo/notes-api";
const STORE_PATH = ROOT + "/.trackchanges/docs%2Freport.md.json";
const T0 = 1757145600000;
const QUOTE = "shipping the cache in v1.2";
const DOC = "# Report\n\n## Findings\nThe api session cut p95 latency by 40% and the p99 by 10%.\n\nWe recommend " + QUOTE + ".\n\nMore text here.\n";
const passage: StoreComment = {
  id: T0 + "-118", author: "you", ts: T0, body: "Which cache? Say which.",
  anchor: { quote: QUOTE, prefix: "We recommend ", suffix: "." }, replies: [], resolved: false,
};
const at = (needle: string): number => { const i = DOC.indexOf(needle); assert.ok(i >= 0, needle); return i; };
// h1: the session's "reduced" became "cut" (a substitution, painted in Raw); h2: it removed " quickly" (a deletion: Reveal-only)
const h1: Hunk = { id: "h1", author: "api", ts: T0 - 90000, kind: "sub", curFrom: at("cut"), curTo: at("cut") + 3, baseFrom: at("cut"), baseTo: at("cut") + 7, oldText: "reduced", newText: "cut", anchor: null };
const h2: Hunk = { id: "h2", author: "api", ts: T0 - 80000, kind: "del", curFrom: at(" here."), curTo: at(" here."), baseFrom: at(" here."), baseTo: at(" here.") + 8, oldText: " quickly", newText: "", anchor: null };
const rec1 = { id: "h1", author: "api", authorId: SID, ts: T0 - 90000, kind: "sub", from: h1.curFrom, newText: "cut", oldText: "reduced" };
const rec2 = { id: "h2", author: "api", authorId: SID, ts: T0 - 80000, kind: "del", from: h2.curFrom, newText: "", oldText: " quickly" };
function status(over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: ROOT, storePath: STORE_PATH, trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
    store: { v: 3, path: "docs/report.md", suggestions: [], comments: [passage] },
    hunks: [], log: [],
    unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 0, watermark: null },
    ...over,
  };
}
/** The status with changes pending: the hunks the host derived and the records the sidecar holds. */
function pending(over: Partial<Status> = {}, hunks: Hunk[] = [h1, h2], recs: Array<typeof rec1> = [rec1, rec2]): Status {
  return status({ hunks, store: { v: 3, path: "docs/report.md", suggestions: recs, comments: [passage] }, ...over });
}
const GONE = "the comments for ~/notes-api/docs/report.md disappeared from disk since you opened the file — reload and retry";

// ── the viewer stand-in: the body row with Raw rows, the seam as closures, the poll's HEAD answers ──
type World = {
  ctx: FileViewActionCtx; posted: any[]; main: El; body: El; code: El;
  hooks: { rendered: Array<() => void>; close: Array<() => void> };
  disk: string; diskMtime: string; viewMtime: string; reloads: number; scrolls: number[]; modes: string[];
  mtimes: Record<string, string>;
  editing: boolean; tracked: TrackedEdit | null;    // the viewer's edit mode, and the panel's half of editing over pending changes
  setText(src: string): void; close(): void;
};
let cur: World | null = null;
(globalThis as any).fetch = async (url: string) => {
  if (url.includes("/sessions")) return { json: async () => [{ id: SID, name: "api", bg: "#123456", fg: "#ffffff" }] };
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
function world(): World {
  const main = new El("div"); main.className = "fileview-main";
  const body = new El("div"); body.className = "fileview-body";
  const wrap = new El("div"); wrap.className = "fileview-code";
  const pre = new El("pre"); pre.className = "fileview-pre fileview-wrap";
  const code = new El("code"); code.className = "hljs";
  pre.appendChild(code); wrap.appendChild(pre);
  body.appendChild(wrap);
  main.appendChild(body);
  let text = DOC;
  const w = {
    posted: [] as any[], main, body, code,
    hooks: { rendered: [] as Array<() => void>, close: [] as Array<() => void> },
    disk: text, diskMtime: "1757145600000000001", viewMtime: "1757145600000000001", reloads: 0, scrolls: [] as number[], modes: [] as string[], mtimes: {} as Record<string, string>,
    editing: false, tracked: null,
  } as World;
  rows(code, text);
  // the viewer's renderBody + fireRendered — in the real viewer the one hook in edit mode is enterEdit's; a test that paints in edit
  // mode is exercising the panel's own render, which the hook reaches through paintAll's editing branch
  w.setText = (s) => { text = s; rows(code, s); for (const cb of w.hooks.rendered) cb(); };
  w.ctx = {
    path: ABS, sid: SID, todoId: null,
    body: () => body as unknown as HTMLElement, mode: () => "raw", text: () => text, mtimeNs: () => w.viewMtime, media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [],
    identity: () => ({ name: "api", color: null }),
    onRendered: (cb) => { w.hooks.rendered.push(cb); }, onSelection: () => { /* inert */ },
    onSaved: () => { /* inert */ }, onClose: (cb) => { w.hooks.close.push(cb); },
    post: (m) => { w.posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: () => { /* inert */ }, editing: () => w.editing, setTrackedEdit: (t) => { w.tracked = t; },
    aside: (node) => { main.querySelector(".fileview-aside")?.remove(); if (node) { const n = node as unknown as El; n.classList.add("fileview-aside"); main.appendChild(n); } },
    setMode: (m) => { w.modes.push(m); }, scrollToOffset: (n) => { w.scrolls.push(n); },
    // fetchFile: the bytes and mtime now on disk, repainted, the seam's onRendered fired; a no-op in edit mode, as the viewer's is
    reload: () => { if (w.editing) return; w.reloads++; w.viewMtime = w.diskMtime; w.setText(w.disk); },
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
  // the poll's baseline follows the reply: the HEADs answer these mtimes until a test moves one
  w.mtimes[w.ctx.path] = s.fileMtimeNs;
  if (s.storePath && s.storeMtimeNs !== null) w.mtimes[s.storePath] = s.storeMtimeNs;
  if (s.root && s.configMtimeNs !== null) w.mtimes[s.root + "/.trackchanges/config.json"] = s.configMtimeNs;
}
function refuse(w: World, m: any, code: string, error: string): void {
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsFailed", reqId: m.reqId, verb: m.verb, code, error } }));
}
/** Mount, answer the probe, open the panel, answer its refresh: the panel as a person first sees it. */
async function openPanel(w: World, s: Status): Promise<{ button: El; aside: El; DECIDE: string }> {
  const fc = await import("./file-comments");
  const unit = fc.fileCommentsAction.mount(w.ctx) as unknown as El;
  const button = unit.childNodes[0] as El;
  answer(w, s); await flush();
  button.click();
  answer(w, s); await flush(); await flush();
  const aside = w.main.querySelector(".fileview-aside")!;
  assert.ok(aside, "the panel is mounted beside the body");
  return { button, aside, DECIDE: fc.DECIDE_IN_EDITOR };
}
const card = (aside: El, key: string): El | null => aside.querySelector('.fc-card[data-id="' + key + '"]');
const act = (root: El, a: string, id?: string): El | null => root.querySelector('[data-act="' + a + '"]' + (id ? '[data-id="' + id + '"]' : ""));
const settle = (p: Promise<unknown>) => { const box: { ok?: unknown; err?: unknown } = {}; p.then((v) => { box.ok = v; }, (e) => { box.err = e; }); return box; };

// ── decisions from a card while the editor is up ───────────────────────────────────────────────────

test("while the editor is up, a card's Accept or Reject, Accept all and Reject all answer in place with where to decide and ask the kernel nothing; the foot says it without a click; the send confirm offers no accept-all; the seed-fenced Save goes through; the cards are live again when the edit ends", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside, button, DECIDE } = await openPanel(w, pending());
  assert.equal(button.textContent, "Comments · 1 · 2 changes");
  assert.match(DECIDE, /^While you edit, decide in the editor: click a change to accept it, Alt-click/);
  // read mode: the decisions are live, in the Slice 2 dress
  const before = act(card(aside, "chg:h1")!, "fcaccept", "h1")!;
  assert.equal(before.classes.includes("fileview-btn-blocked"), false);
  assert.equal(before.title, "Keep the text as it is and drop the change");
  assert.equal(aside.querySelector(".fc-decide-edit"), null, "no caption in read mode");
  // Edit: begin() runs at the click; the viewer then fires onRendered once in edit mode (enterEdit), and the cards take their edit-mode state from that paint (here begin() renders with editing already set, so it shows at once)
  w.editing = true;
  const begun = w.tracked!.begin()!;
  assert.deepEqual(begun.records, [rec1, rec2], "the records ride into the editor");
  const ok = act(card(aside, "chg:h1")!, "fcaccept", "h1")!;
  assert.equal(ok.disabled, false, "a real button: the reason reaches touch and keyboard users (the Edit button's idiom)");
  assert.ok(ok.classes.includes("fileview-btn-blocked"), "…dimmed");
  assert.equal(ok.title, DECIDE);
  assert.equal(act(card(aside, "chg:h1")!, "fcreject", "h1")!.title, DECIDE);
  assert.equal(act(aside, "fcacceptall")!.title, DECIDE);
  assert.equal(act(aside, "fcrejectall")!.title, DECIDE);
  assert.equal(aside.querySelector(".fc-foot .fc-decide-edit")!.textContent, DECIDE, "the foot says it without a click");
  // a decision from a card: refused under the card, nothing at all sent to the kernel
  const frames = w.posted.length;
  ok.click(); await flush();
  assert.equal(w.posted.length, frames, "nothing went to the kernel");
  assert.equal(countOf(w, "fileComments", "accept"), 0);
  const row = card(aside, "chg:h1")!.querySelector(".fc-err")!;
  assert.ok(row, "the row sits under the card that asked");
  assert.equal(row.childNodes[0].textContent, DECIDE);
  assert.equal(row.querySelector('[data-act="fcreload"]'), null, "nothing to reload: nothing moved");
  act(card(aside, "chg:h1")!, "fcreject", "h1")!.click(); await flush();
  assert.equal(countOf(w, "fileComments", "reject"), 0);
  act(aside, "fcacceptall")!.click(); await flush();
  assert.equal(countOf(w, "fileComments", "accept-all"), 0);
  assert.equal(aside.querySelector(".fc-foot .fc-err")!.childNodes[0].textContent, DECIDE, "the foot's row for the foot's buttons");
  act(aside, "fcrejectall")!.click(); await flush();
  assert.equal(aside.querySelector(".fc-choice"), null, "no confirm to walk into: the answer is the row");
  assert.equal(act(aside, "fcrejectall")!.getAttribute("aria-expanded"), "false");
  assert.equal(countOf(w, "fileComments", "reject-all"), 0);
  assert.equal(w.posted.length, frames, "four decisions, no frames");
  assert.equal(button.textContent, "Comments · 1 · 2 changes", "the status never moved");
  // the send confirm: no accept-all checkbox, and the send runs no accept-all on the way
  act(aside, "fcsend")!.click();
  assert.ok(aside.querySelector(".fc-confirm"), "Send itself is fine: it appends to the log, not the sidecar");
  assert.equal(aside.querySelector('input[data-opt="accept"]'), null, "no box to accept the pending changes under the editor");
  assert.equal(aside.querySelector(".fc-list")!.textContent.includes("accepted"), false, "the list claims no decisions");
  act(aside, "fcsendgo")!.click(); await flush();
  assert.equal(countOf(w, "fileComments", "accept-all"), 0);
  const sent = lastOf(w, "fileCommentsSend");
  assert.ok(sent, "the send went straight out");
  assert.equal(sent.accepted, 0);
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsSent", reqId: sent.reqId, queued: false } })); await flush(); await flush();
  answer(w, pending()); await flush();            // the send's own refresh
  // the editor's Save still goes through, fenced on the sidecar the records came from — the trap the gate exists to avoid
  const out = settle(w.tracked!.save("the typed text", [rec1, rec2], { accepted: [], rejected: [] }));
  await flush();
  const save = lastOf(w, "fileComments", "save");
  assert.ok(save, "the save verb");
  assert.equal(save.fence.storeMtimeNs, "1757145600000000002", "the sidecar as it stood at Edit, untouched by any card");
  assert.deepEqual(save.args.suggestions, [rec1, rec2]);
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: save.reqId, ...pending({ verb: "save", fileMtimeNs: "1757145600000000009", storeMtimeNs: "1757145600000000010" }), logged: true } }));
  await flush(); await flush();
  assert.deepEqual(out.ok, { mtimeNs: "1757145600000000009", logged: true });
  // the edit ends: the viewer repaints the read view and fires onRendered — the cards are live again
  w.editing = false; w.viewMtime = "1757145600000000009"; w.setText(w.disk);
  const after = act(card(aside, "chg:h1")!, "fcaccept", "h1")!;
  assert.equal(after.classes.includes("fileview-btn-blocked"), false);
  assert.equal(after.title, "Keep the text as it is and drop the change");
  assert.equal(aside.querySelector(".fc-decide-edit"), null);
  assert.equal(card(aside, "chg:h1")!.querySelector(".fc-err"), null, "the rows went with the edit-mode render");
  after.click(); await flush();
  const acc = lastOf(w, "fileComments", "accept");
  assert.ok(acc, "a decision goes to the kernel again");
  assert.deepEqual(acc.args, { ids: ["h1"] });
  assert.equal(acc.fence.storeMtimeNs, "1757145600000000010", "fenced on the sidecar the save reply reported");
});

test("source: the decision gate runs before anything is asked of the kernel, and Reject all's confirm is skipped for it", () => {
  const mut = SRC.split("async mutate(verb: string, args: Record<string, unknown>, slot: string): Promise<Status | null> {")[1].split("\n  }\n")[0];
  assert.ok(mut.indexOf("if (DECIDES.has(verb) && this.ctx.editing()) { this.refuseDecision(slot); return null; }") < mut.indexOf("if (this.busy.has(slot)) return null;"),
    "the gate is the first thing mutate does: no slot held, no status re-asked, no consent popup for a decision that cannot go");
  assert.match(SRC, /const DECIDES = new Set\(\["accept", "reject", "accept-all", "reject-all"\]\);/, "the four verbs that move records out of the sidecar");
  assert.match(SRC, /fcrejectall: \(\) => \{[^\n]*\n\s*if \(this\.ctx\.editing\(\)\) \{ this\.refuseDecision\("changes"\); return; \}/, "Reject all answers at the first click, not after its confirm");
  const send = SRC.split("async doSend(): Promise<void> {")[1].split("\n  }\n")[0];
  assert.match(send, /const pending = this\.ctx\.editing\(\) \? 0 : \(s\.hunks \|\| \[\]\)\.length;\n\s*const acceptAll = this\.sendOpts\.accept && pending > 0;/,
    "the send has no changes to accept on the way under an editor: acceptAll derives from that count");
  const conf = SRC.split("private renderSend(s: Status | null): HTMLElement {")[1].split("\n  }\n")[0];
  assert.match(conf, /const pending = this\.ctx\.editing\(\) \? 0 : \(s\.hunks \|\| \[\]\)\.length;\n(?:\s*\/\/[^\n]*\n)*\s*const counts = sendCounts\(parts, this\.sendOpts\.accept, pending\);/,
    "…and the confirm's box and counts derive from the same count");
});

// ── routesSave holds while records are in the editor ───────────────────────────────────────────────

test("routesSave holds while records are in the editor: a sidecar pruned under the edit does not re-route Save to saveFile; the seed-fenced save refuses store-moved and stands; once the edit ends the route follows the status again", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setInterval"] });
  const w = world(); t.after(() => w.close());
  // an untracked file whose sidecar holds one change a session recorded while tracking was on
  await openPanel(w, pending({ trackedBy: null }, [h1], [rec1]));
  const te = w.tracked!;
  assert.equal(te.routesSave(), true, "a sidecar: Save goes through the host");
  w.editing = true;
  assert.deepEqual(te.begin()!.records, [rec1]);
  // in another browser the person accepted the change: the host pruned the emptied sidecar, and the poll sees it gone
  delete w.mtimes[STORE_PATH];
  const asks = countOf(w, "fileComments", "status");
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  assert.equal(countOf(w, "fileComments", "status"), asks + 1, "the sidecar is still watched while the editor is up");
  const gone = status({ trackedBy: null, store: null, storeMtimeNs: null, hunks: [] });
  answer(w, gone); await flush();
  assert.equal(te.routesSave(), true, "the editor still carries the record: its save must meet the fence of the sidecar it came from, not bypass it");
  // the person rejected the change in the editor and typed; Save
  const out = settle(te.save("the typed text", [], { accepted: [], rejected: [{ id: "h1", oldText: "reduced", newText: "cut" }] }));
  await flush();
  const save = lastOf(w, "fileComments", "save");
  assert.ok(save, "the save verb (the viewer's saveFile is never what routesSave answers here)");
  assert.deepEqual(save.fence, { storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003", fileMtimeNs: "1757145600000000001" },
    "fenced on the sidecar the record came from, not the poll's latest (which says there is none)");
  assert.deepEqual(save.args.rejected, [{ id: "h1", oldText: "reduced", newText: "cut" }], "the editor's decision rides along, for the host to refuse or log");
  refuse(w, save, "store-moved", GONE); await flush();
  assert.equal(countOf(w, "fileComments", "status"), asks + 2, "one re-read before deciding");
  answer(w, gone); await flush(); await flush();
  assert.deepEqual(out.err, { code: "store-moved", error: GONE }, "the records changed under the editor: the refusal stands, in the host's words");
  assert.equal(countOf(w, "fileComments", "save"), 1, "no retry");
  assert.equal(te.routesSave(), true, "a later Save meets the same fence");
  // the edit ends (Cancel or Reload): nothing is in an editor any more, and the status says saveFile
  w.editing = false; w.setText(w.disk);
  assert.equal(te.routesSave(), false, "no sidecar, not tracked: the viewer's own save path");
  assert.equal(te.begin(), null, "…and a new Edit has nothing to carry");
  assert.equal(te.routesSave(), false);
});

// ── the moved-under-edit row: its ✕ dismisses the words, not the re-read ───────────────────────────

test("the moved-under-edit row's ✕ dismisses the words and not the re-read: Cancel still shows the file as it is now, as the row promised", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setInterval"] });
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, status());
  w.editing = true;
  // the session rewrote the file under the person's edit; the poll sees the move
  w.disk = DOC.replace("More text here.", "More text here, rewritten by the session."); w.diskMtime = "1757145600000000033"; w.mtimes[ABS] = w.diskMtime;
  const asks = countOf(w, "fileComments", "status");
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  assert.equal(w.reloads, 0, "never over the editor's buffer");
  assert.equal(countOf(w, "fileComments", "status"), asks + 1);
  answer(w, status({ fileMtimeNs: w.diskMtime })); await flush();
  const row = aside.querySelector(".fc-sec-head .fc-err")!;
  assert.ok(row, "the head says the bytes moved");
  assert.equal(row.childNodes[0].textContent, MOVED_UNDER_EDIT);
  assert.match(MOVED_UNDER_EDIT, /Cancel shows the file as it is now/, "the promise the ✕ must not break");
  // the person dismisses the row
  row.querySelector('[data-act="fcerrx"]')!.click();
  assert.equal(aside.querySelector(".fc-sec-head .fc-err"), null, "dismissed");
  assert.equal(w.reloads, 0, "…and still nothing re-read over the buffer");
  // no later tick notices: the baseline moved on with the status (this is why the re-read cannot be left to the poll)
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  assert.equal(countOf(w, "fileComments", "status"), asks + 1);
  // Cancel: the viewer repaints the bytes it loaded (the pre-rewrite text) and fires onRendered
  w.editing = false;
  w.setText(DOC);
  assert.equal(w.reloads, 1, "the first paint after the edit re-reads the file, dismissed row or not");
  assert.ok(w.code.textContent.includes("rewritten by the session"), "the read view shows the file as it is now");
  assert.equal(w.viewMtime, w.diskMtime);
  assert.equal(aside.querySelector(".fc-sec-head .fc-err"), null);
  w.setText(w.disk);
  assert.equal(w.reloads, 1, "the latch is spent: a later paint re-reads nothing");
});

// ── Reveal and the card links go with the read view ────────────────────────────────────────────────

test("Reveal and the card links act on the read view, so neither is offered while the editor holds the body — a deletion's card, a change's ref, a comment's ref — and all are back when the edit ends", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, pending());
  const chg = (id: string) => card(aside, "chg:" + id)!;
  const cmt = () => card(aside, passage.id)!;
  // read mode: the deletion offers Reveal; the painted substitution's ref and the painted passage's ref scroll to their marks
  assert.ok(act(chg("h2"), "fcreveal"), "a deletion is never painted: Reveal");
  assert.equal(chg("h1").querySelector(".fc-ref")!.dataset.act, "fcgoto");
  assert.equal(cmt().querySelector(".fc-ref")!.dataset.act, "fcgoto");
  // Edit
  w.editing = true; w.tracked!.begin();
  assert.equal(aside.querySelectorAll('[data-act="fcreveal"]').length, 0, "no Reveal anywhere: the viewer's setMode and scrollToOffset are no-ops while editing, and the editor shows every change itself");
  assert.equal(aside.querySelectorAll('[data-act="fcgoto"]').length, 0, "no link into a read view that is gone");
  assert.deepEqual(aside.querySelectorAll(".fc-tag").map((x) => x.textContent).filter((x) => x === "not shown"), [], "the editor shows the deletion: no tag promising a Reveal");
  assert.equal(chg("h2").querySelector(".fc-ref")!.title, "Removed:  quickly", "the ref still says what the change is");
  assert.deepEqual(w.modes, []); assert.deepEqual(w.scrolls, []);
  // the edit ends: the read view is back, and so are its offers
  w.editing = false; w.setText(w.disk);
  assert.ok(act(chg("h2"), "fcreveal"));
  assert.equal(chg("h1").querySelector(".fc-ref")!.dataset.act, "fcgoto");
  assert.equal(cmt().querySelector(".fc-ref")!.dataset.act, "fcgoto");
  act(chg("h2"), "fcreveal")!.click();
  assert.deepEqual(w.modes, ["raw"]); assert.deepEqual(w.scrolls, [h2.curFrom]);
});
