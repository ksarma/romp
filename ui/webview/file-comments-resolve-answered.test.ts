// Resolve answered (plans/file-review.md, "The about follow-on (2026-09-10)" under Slice 2; decision 46): nothing resolves
// a comment except the person, and a header action resolves at once every open comment of theirs the session has answered.
// Driven over the Slice 2 stand-in (copied here as the sibling modules copy it, the tree's edges hidden from a failing
// assertion). Pinned: the model's pick of the answered comments (unresolved, the person's, with a turn by another author,
// words or a revision, after the person's last turn on the comment); the header action "Resolve answered (N)" while N > 0
// and its absence at N = 0; the plain confirm line and Cancel; one resolve request per comment, in order, each answered;
// a refusal reported under its card, the rest resolved; "Reopen all" under the header (the list layout, this stand-in's;
// the margin layout's stands in the acknowledgment's position and displaces it, pinned by layout in
// file-comments-resolve-answered-review2.test.ts), its click reopening the same comments, and its end at the person's next
// gesture (a press on the button itself excepted), the sent acknowledgment at the foot untouched throughout (in place,
// before any render, and kept by the next); nothing else in the panel resolving a comment. Synthetic fixtures only: the notes-api world, placeholder ids, the sessions "api"
// and "web".
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import { inspect } from "node:util";
import { assertHiddenEvent, hideEdges, staysEnumerable } from "../test-dom-shim";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx } from "./file-view";
import { type Status, type Hunk, type StoreComment, type Card, answeredComments, cardModel } from "./file-comments-model";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const SRC = web("file-comments.ts");
const HOST = fs.readFileSync(path.resolve(process.cwd(), "..", "tools", "file-comments-host.mjs"), "utf8");

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const SID2 = "11111111-2222-3333-4444-666666666666";
const ABS = "/repo/notes-api/docs/report.md";
const ROOT = "/repo/notes-api";
const STORE_PATH = ROOT + "/.trackchanges/docs%2Freport.md.json";
const T0 = 1757145600000;
const DOC = "# Report\n\n## Findings\nThe api session cut p95 latency by 40% and the p99 by 10%.\n\n"
  + "We recommend shipping the cache in v1.2.\n\nRisks remain in the fallback path.\n\nNext steps: measure again.\n";
const at = (needle: string, from = 0): number => { const i = DOC.indexOf(needle, from); assert.ok(i >= 0, needle); return i; };
const H = (id: string, kind: Hunk["kind"], from: number, to: number, oldText: string, newText: string, ts = T0 - 90000): Hunk =>
  ({ id, author: "api", ts, kind, curFrom: from, curTo: to, baseFrom: from, baseTo: from + oldText.length, oldText, newText, anchor: null });
const h1 = H("h1", "sub", at("cut"), at("cut") + 3, "reduced", "cut");
const SUGG = [{ id: "h1", author: "api", authorId: SID, ts: T0 - 90000, kind: "sub", from: h1.curFrom, oldText: "reduced", newText: "cut" }];
const reply = (author: string, ts: number, body: string) => ({ author, authorId: author === "you" ? undefined : SID, ts, body });
const edit = (ts: number) => ({ author: "api", authorId: SID, ts, kind: "edit", oldText: "cut", newText: "trimmed" });
/** The person's comment the session answered in words. */
const answered: StoreComment = { id: T0 + "-118", author: "you", ts: T0, body: "Which cache? Say which.", anchor: { quote: "shipping the cache in v1.2", prefix: "We recommend ", suffix: "." },
  replies: [reply("api", T0 + 1000, "The response cache; the sentence names it now.")], resolved: false };
/** The person's comment the session answered with a revision (a turn of kind edit), no words. */
const revised: StoreComment = { id: T0 + 2000 + "-5", author: "you", ts: T0 + 2000, body: "Say cut, not reduced.", changeIds: ["h1"], replies: [edit(T0 + 3000)], resolved: false };
/** The person's comment with the person's own word last: the session's reply came before it. */
const mineLast: StoreComment = { id: T0 + 4000 + "-40", author: "you", ts: T0 + 4000, body: "Cite the run.", anchor: { quote: "Risks remain", prefix: "", suffix: " in the fallback path." },
  replies: [reply("api", T0 + 4100, "Done."), reply("you", T0 + 4200, "Which run, though?")], resolved: false };
/** The person's comment nobody answered. */
const open: StoreComment = { id: T0 + 5000 + "-0", author: "you", ts: T0 + 5000, body: "Add a summary at the top.", replies: [], resolved: false };
/** The session's own comment the person answered: not the person's to resolve in bulk. */
const theirs: StoreComment = { id: T0 + 6000 + "-60", author: "api", authorId: SID, ts: T0 + 6000, body: "Is the p99 number final?", anchor: { quote: "p99 by 10%", prefix: "by 40% and the ", suffix: "." },
  replies: [reply("you", T0 + 6100, "Yes.")], resolved: false };
/** The person's answered comment already resolved. */
const done: StoreComment = { ...answered, id: T0 + 7000 + "-7", ts: T0 + 7000, replies: [reply("web", T0 + 7100, "Fixed.")], resolved: true };
const ALL = [answered, revised, mineLast, open, theirs, done];
function status(over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: ROOT, storePath: STORE_PATH, trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
    store: { v: 3, path: "docs/report.md", suggestions: SUGG, comments: ALL },
    hunks: [h1], log: [],
    unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null },
    ...over,
  };
}

// ── the pure half ──────────────────────────────────────────────────────────────────────────────────

test("answeredComments: the person's unresolved comments with a turn by another author after the person's last turn; a revision counts; the person's own last word, a resolved one and the session's own comment do not", () => {
  const cards = cardModel(status().store, [h1]);
  assert.deepEqual(answeredComments(cards).map((c) => c.id), [answered.id, revised.id], "in the cards' order (oldest first)");
  assert.deepEqual(answeredComments([]), []);
  const byId = (id: string): Card => cards.find((c) => c.id === id)!;
  assert.deepEqual(answeredComments([byId(mineLast.id)]), [], "the person replied after the session: not answered since");
  assert.deepEqual(answeredComments([byId(open.id)]), [], "no reply at all");
  assert.deepEqual(answeredComments([byId(theirs.id)]), [], "the session's comment, answered by the person: not the person's");
  assert.deepEqual(answeredComments([byId(done.id)]), [], "already resolved");
  const twice = cardModel({ v: 3, path: "docs/report.md", suggestions: SUGG, comments: [{ ...mineLast, replies: [...mineLast.replies!, reply("api", T0 + 4300, "The nightly one.")] }] }, [h1]);
  assert.deepEqual(answeredComments(twice).map((c) => c.id), [mineLast.id], "answered again after the person's last word: answered");
});

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
  get previousSibling(): El | Txt | null { const p = this.parentNode; if (!p) return null; const i = p.childNodes.indexOf(this); return i > 0 ? p.childNodes[i - 1] : null; }
  get nextSibling(): El | Txt | null { const p = this.parentNode; if (!p) return null; const i = p.childNodes.indexOf(this); return i >= 0 && i + 1 < p.childNodes.length ? p.childNodes[i + 1] : null; }
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
  get previousSibling(): El | Txt | null { const p = this.parentNode; if (!p) return null; const i = p.childNodes.indexOf(this); return i > 0 ? p.childNodes[i - 1] : null; }
  get nextSibling(): El | Txt | null { const p = this.parentNode; if (!p) return null; const i = p.childNodes.indexOf(this); return i >= 0 && i + 1 < p.childNodes.length ? p.childNodes[i + 1] : null; }
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



// ── the drive ─────────────────────────────────────────────────────────────────────────────────────
const headBtn = (aside: El): El | null => act(aside, "fcresolveanswered");
const confirmRow = (aside: El): El | null => act(aside, "fcresolveanswereddo")?.parentNode || null;
const reopen = (aside: El): El | null => act(aside, "fcreopenall");
const resolves = (w: World) => w.posted.filter((m) => m.type === "fileComments" && m.verb === "resolve").map((m) => m.args);
const resolvedAll = (ids: string[]): Status => status({ verb: "resolve", storeMtimeNs: "1757145600000000009", store: { v: 3, path: "docs/report.md", suggestions: SUGG, comments: ALL.map((c) => (ids.includes(c.id) ? { ...c, resolved: true } : c)) } });
const gesture = (el: El, type: string): void => { el.dispatchEvent(new Ev(type)); };
/** A send of the person's words alone (nothing is unsent in the fixture), so a sent acknowledgment stands at the foot: the
 *  confirm, its accept option unchecked (the pending change stays out of this: no accept goes before the send), the words in
 *  the note box, its Send; the send answered, the refresh it asks answered with the status. */
async function sendWords(w: World, aside: El, words: string): Promise<void> {
  act(aside, "fcsend")!.click();
  const accept = aside.querySelector('input[data-opt="accept"]');
  if (accept) { accept.checked = false; dispatch(accept, new Ev("change")); }
  const box = aside.querySelector(".fc-confirm .fc-send-note")!;
  assert.ok(box, "the confirm is up, with its note box");
  box.value = words; dispatch(box, new Ev("input"));
  act(aside, "fcsendgo")!.click(); await flush();
  const m = lastOf(w, "fileCommentsSend");
  assert.ok(m, "the send went out");
  assert.equal(lastOf(w, "fileComments", "accept"), undefined, "the words alone: no accept went before it");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsSent", reqId: m.reqId, queued: false } })); await flush();
  answer(w, status()); await flush(); await flush();
}
/** The plain sent acknowledgment in the Send section: the div in the acknowledgment's dress that is not the Reopen all line
 *  (the line and its button wear the same dress, so the class alone does not tell them apart). */
const sentAck = (aside: El): El[] => aside.querySelectorAll(".fc-send div.fc-sent").filter((d) => !d.classList.contains("fc-reopen"));

test("the header action names the count while the session has answered open comments of the person's, and is absent at zero; its click asks in one line, Cancel withdraws", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  const b = headBtn(aside)!;
  assert.ok(b, "the action is in the header");
  assert.equal(b.textContent, "Resolve answered (2)", "the two answered: in words and by a revision");
  assert.equal(b.title, "Resolve the 2 comments of yours the session has answered; a comment stays open until you resolve it");
  assert.ok(aside.querySelector(".fc-head")!.contains(b), "in the head");
  assert.equal(confirmRow(aside), null, "no confirm until the click");
  b.click();
  const row = confirmRow(aside)!;
  assert.ok(row, "the confirm row");
  assert.equal(row.querySelector(".fc-note")!.textContent, "Resolve the 2 comments the session has answered?");
  assert.deepEqual(texts(row.querySelectorAll("button")), ["Resolve", "Cancel"]);
  act(aside, "fcresolveansweredcancel")!.click();
  assert.equal(confirmRow(aside), null, "Cancel withdraws the question");
  assert.deepEqual(resolves(w), [], "nothing resolved");
  // at zero the action is not offered: the person's last word stands on every comment
  const w2 = world(); t.after(() => w2.close());
  const { aside: a2 } = await openPanel(w2, status({ store: { v: 3, path: "docs/report.md", suggestions: SUGG, comments: [mineLast, open, theirs, done] } }));
  assert.equal(headBtn(a2), null, "nothing answered: no action (progressive disclosure)");
});

test("Resolve: one resolve request per answered comment, in order, each with on true; the acknowledgment says how many, Reopen all stands in its place; the header action is gone with the count", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  headBtn(aside)!.click();
  act(aside, "fcresolveanswereddo")!.click(); await flush();
  const first = lastOf(w, "fileComments", "resolve");
  assert.deepEqual(first.args, { commentId: answered.id, on: true }, "the first, the oldest");
  assert.equal(countOf(w, "fileComments", "resolve"), 1, "one at a time: the next waits for the reply");
  assert.equal(headBtn(aside)!.textContent, "Resolving…"); assert.equal(headBtn(aside)!.disabled, true, "the action says it is at work");
  answer(w, resolvedAll([answered.id]), first); await flush(); await flush();
  const second = lastOf(w, "fileComments", "resolve");
  assert.deepEqual(second.args, { commentId: revised.id, on: true });
  answer(w, resolvedAll([answered.id, revised.id]), second); await flush(); await flush();
  assert.deepEqual(resolves(w), [{ commentId: answered.id, on: true }, { commentId: revised.id, on: true }]);
  assert.equal(headBtn(aside), null, "nothing answered is open now: the action is gone");
  const line = aside.querySelector(".fc-reopen")!;
  assert.ok(line, "the acknowledgment's position carries the line");
  assert.ok(aside.querySelector(".fc-head")!.contains(line), "…under the header, the list layout's place (this stand-in's layout; the margin layout's offer stands in the Send section, where the sent acknowledgment stands: file-comments-resolve-answered-review2.test.ts)");
  assert.equal(line.querySelector(".fc-note")!.textContent, "Resolved 2 comments");
  assert.equal(reopen(aside)!.textContent, "Reopen all");
  assert.ok(card(aside, answered.id) === null && card(aside, revised.id) === null, "the two cards left the open list");
  assert.match(aside.querySelectorAll(".fc-sec").find((s) => s.textContent.includes("Resolved ("))!.textContent, /Resolved \(3\)/, "…for the Resolved fold");
});

test("Reopen all: one resolve request per comment with on false, the same comments; the line goes with the click", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  headBtn(aside)!.click();
  act(aside, "fcresolveanswereddo")!.click(); await flush();
  answer(w, resolvedAll([answered.id]), lastOf(w, "fileComments", "resolve")); await flush(); await flush();
  answer(w, resolvedAll([answered.id, revised.id]), lastOf(w, "fileComments", "resolve")); await flush(); await flush();
  assert.ok(reopen(aside));
  reopen(aside)!.click(); await flush();
  assert.equal(aside.querySelector(".fc-reopen"), null, "the offer is taken: the line goes");
  let m = lastOf(w, "fileComments", "resolve");
  assert.deepEqual(m.args, { commentId: answered.id, on: false });
  answer(w, resolvedAll([revised.id]), m); await flush(); await flush();
  m = lastOf(w, "fileComments", "resolve");
  assert.deepEqual(m.args, { commentId: revised.id, on: false });
  answer(w, status({ verb: "resolve", storeMtimeNs: "1757145600000000011" }), m); await flush(); await flush();
  assert.equal(resolves(w).length, 4);
  assert.equal(headBtn(aside)!.textContent, "Resolve answered (2)", "both open and answered again");
  assert.ok(card(aside, answered.id) && card(aside, revised.id), "their cards are back in the open list");
});

test("a refusal on one comment: its row under the card, the rest resolved, the acknowledgment counts the resolved alone and Reopen all reopens those alone", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  headBtn(aside)!.click();
  act(aside, "fcresolveanswereddo")!.click(); await flush();
  const first = lastOf(w, "fileComments", "resolve");
  refuse(w, first, "no-comment", "comment " + answered.id + " is not among the comments for ~/notes-api/docs/report.md — reload and retry"); await flush(); await flush();
  const second = lastOf(w, "fileComments", "resolve");
  assert.deepEqual(second.args, { commentId: revised.id, on: true }, "the refusal does not stop the rest");
  answer(w, resolvedAll([revised.id]), second); await flush(); await flush();
  const row = aside.querySelector('.fc-err[data-slot="card:' + answered.id + '"]');
  assert.ok(row && row.textContent.includes("is not among the comments"), "the refusal, in the comment's slot, verbatim (the card's own Resolve would put it in the same slot)");
  assert.ok(aside.querySelector(".fc-cards")!.contains(row!), "in the list: inside the card when it is open, else where the section is (strayRows), as a card's own refused Resolve stands");
  card(aside, answered.id)!.querySelector(".fc-card-head")!.click();
  assert.ok(card(aside, answered.id)!.contains(aside.querySelector('.fc-err[data-slot="card:' + answered.id + '"]')!), "open, the card carries its row");
  assert.equal(aside.querySelector(".fc-reopen .fc-note")!.textContent, "Resolved 1 comment");
  reopen(aside)!.click(); await flush();
  assert.deepEqual(lastOf(w, "fileComments", "resolve").args, { commentId: revised.id, on: false }, "only the one that was resolved");
  answer(w, status({ verb: "resolve", storeMtimeNs: "1757145600000000012" }), lastOf(w, "fileComments", "resolve")); await flush(); await flush();
  assert.equal(countOf(w, "fileComments", "resolve"), 3);
});

test("the offer ends at the person's next gesture, a press on the offer itself excepted; the sent acknowledgment at the foot stands throughout (the list layout displaces nothing), once, and the next render keeps it", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  // a send's acknowledgment stands first
  await sendWords(w, aside, "The findings read well now.");
  assert.equal(sentAck(aside).length, 1, "the acknowledgment at the foot");
  assert.match(sentAck(aside)[0].textContent, /^Sent to api at /);
  headBtn(aside)!.click();
  act(aside, "fcresolveanswereddo")!.click(); await flush();
  answer(w, resolvedAll([answered.id]), lastOf(w, "fileComments", "resolve")); await flush(); await flush();
  answer(w, resolvedAll([answered.id, revised.id]), lastOf(w, "fileComments", "resolve")); await flush(); await flush();
  const line = aside.querySelector(".fc-reopen")!;
  assert.ok(line);
  assert.ok(aside.querySelector(".fc-head")!.contains(line), "the list layout: the offer under the header");
  assert.equal(sentAck(aside).length, 1, "the acknowledgment at the foot is not displaced there, and not doubled");
  gesture(reopen(aside)!, "pointerdown");
  assert.ok(aside.querySelector(".fc-reopen"), "a press on the offer itself ends nothing: its click is what it is for");
  assert.equal(sentAck(aside).length, 1, "…and changes nothing at the foot");
  gesture(w.body, "pointerdown");
  assert.equal(aside.querySelector(".fc-reopen"), null, "a press anywhere else ends the offer");
  assert.equal(resolves(w).length, 2, "and reopens nothing");
  // the end is in place (reflectLines, no render): the foot shows the acknowledgment as before, once, never twice
  const back = sentAck(aside);
  assert.equal(back.length, 1, "the acknowledgment stands at the foot, once");
  assert.match(back[0].textContent, /^Sent to api at /, "the same words");
  assert.ok(aside.querySelector(".fc-send")!.contains(back[0]), "in the Send section, where it stood");
  // the next render (a fold toggled: a click, no gesture) puts the same back and no offer
  act(aside, "fcresolved")!.click();
  assert.equal(aside.querySelector(".fc-reopen"), null, "the offer stays ended across the render");
  assert.equal(sentAck(aside).length, 1, "the render shows the acknowledgment, once");
  assert.match(sentAck(aside)[0].textContent, /^Sent to api at /);
  // a key ends it too, Tab and a modifier alone excepted; a wheel ends it, and the acknowledgment at the foot stands the same way
  const w2 = world(); t.after(() => w2.close());
  const { aside: a2 } = await openPanel(w2);
  await sendWords(w2, a2, "Ship it.");
  assert.equal(sentAck(a2).length, 1);
  headBtn(a2)!.click(); act(a2, "fcresolveanswereddo")!.click(); await flush();
  answer(w2, resolvedAll([answered.id]), lastOf(w2, "fileComments", "resolve")); await flush(); await flush();
  answer(w2, resolvedAll([answered.id, revised.id]), lastOf(w2, "fileComments", "resolve")); await flush(); await flush();
  assert.ok(a2.querySelector(".fc-reopen"));
  assert.equal(sentAck(a2).length, 1, "the list layout: not displaced");
  dispatch(w2.body, new Ev("keydown", { key: "Tab" }));
  assert.ok(a2.querySelector(".fc-reopen"), "Tab moves the keyboard toward the offer and ends nothing");
  dispatch(w2.body, new Ev("keydown", { key: "Shift" }));
  assert.ok(a2.querySelector(".fc-reopen"), "a modifier alone ends nothing");
  assert.equal(sentAck(a2).length, 1, "…and neither touches the acknowledgment");
  gesture(w2.body, "wheel");
  assert.equal(a2.querySelector(".fc-reopen"), null, "a wheel ends it");
  assert.equal(sentAck(a2).length, 1, "the acknowledgment stands in place after the wheel too, once");
  assert.match(sentAck(a2)[0].textContent, /^Sent to api at /);
  // with no send before the offer the foot is bare, not an empty line, before and after the offer
  const w3 = world(); t.after(() => w3.close());
  const { aside: a3 } = await openPanel(w3);
  assert.equal(sentAck(a3).length, 0, "no acknowledgment before");
  headBtn(a3)!.click(); act(a3, "fcresolveanswereddo")!.click(); await flush();
  answer(w3, resolvedAll([answered.id]), lastOf(w3, "fileComments", "resolve")); await flush(); await flush();
  answer(w3, resolvedAll([answered.id, revised.id]), lastOf(w3, "fileComments", "resolve")); await flush(); await flush();
  assert.ok(a3.querySelector(".fc-reopen"));
  gesture(w3.body, "pointerdown");
  assert.equal(a3.querySelector(".fc-reopen"), null);
  assert.equal(sentAck(a3).length, 0, "nothing to restore: no acknowledgment appears");
});

test("sources: nothing resolves a comment but the person's two actions; the host writes resolved in doResolve alone; the acts in the delegate table", () => {
  assert.equal((HOST.match(/\.resolved\s*=(?!=)/g) || []).length, 1, "the host's one write to resolved is the resolve verb's");
  const writes = SRC.match(/mutate\("resolve"/g) || [];
  assert.equal(writes.length, 3, "the card's Resolve, Resolve answered, and Reopen all: " + writes.length);
  assert.match(SRC, /fcresolveanswered: \(\) => \{ this\.resolveAnsweredConfirm = true; this\.render\(\); \},/);
  assert.match(SRC, /fcresolveansweredcancel: \(\) => \{ this\.resolveAnsweredConfirm = false; this\.render\(\); \},/);
  assert.match(SRC, /fcresolveanswereddo: \(\) => \{ void this\.resolveAnswered\(\); \},/);
  assert.match(SRC, /fcreopenall: \(\) => \{ void this\.reopenAnswered\(\); \},/);
  assert.match(SRC, /const undo = this\.reopenAll !== null && !on\("fcreopenall"\);/, "the gesture ends the offer, a press on it excepted");
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
