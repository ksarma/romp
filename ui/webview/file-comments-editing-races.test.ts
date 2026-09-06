// The Comments panel while the editor is up, when a DECISION LANDS ANYWAY (plans/file-review.md, Slice 5; the 2026-09-06
// review of the slice, second pass). The card gate (file-comments-editing-cards.test.ts) refuses a decision clicked while
// the editor is up; this suite covers the ways a decision still reaches the sidecar the editor's records came from, and
// what the panel does then. Two orderings the gate alone misses: a card click that passed the gate before Edit and whose
// send comes after the editor opened (refused again at the send, so nothing goes out), and a click whose request was
// already out when Edit began (its reply lands under the editor). And the decisions no gate can reach: another browser's
// card, a session's CLI. In every reached case the head says so from the status that shows it — before Save, which can
// only refuse — once per edit, and yields to the file's own row when the bytes moved too (a reject). Driven as a panel
// over the behavior suite's DOM stand-in. Synthetic fixtures only: the notes-api world, placeholder ids.
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
  consent: () => Promise<boolean>;                  // the file-editing consent, deferrable: a decision waits on it while Edit goes ahead
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
    editing: false, tracked: null, consent: async () => true,
  } as World;
  rows(code, text);
  // the viewer's renderBody + fireRendered — in the real viewer no hook fires while editing; a test that paints in edit
  // mode is exercising the panel's own render, which the hook reaches through paintAll's editing branch
  w.setText = (s) => { text = s; rows(code, s); for (const cb of w.hooks.rendered) cb(); };
  w.ctx = {
    path: ABS, sid: SID, todoId: null,
    body: () => body as unknown as HTMLElement, mode: () => "raw", text: () => text, mtimeNs: () => w.viewMtime, media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [],
    identity: () => ({ name: "api", color: null }),
    onRendered: (cb) => { w.hooks.rendered.push(cb); }, onSelection: () => { /* inert */ },
    onSaved: () => { /* inert */ }, onClose: (cb) => { w.hooks.close.push(cb); },
    post: (m) => { w.posted.push(m); }, ensureEditingAllowed: () => w.consent(), setEditBlocked: () => { /* inert */ }, editing: () => w.editing, setTrackedEdit: (t) => { w.tracked = t; },
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
async function openPanel(w: World, s: Status): Promise<{ button: El; aside: El; DECIDE: string; CHANGES_MOVED: string }> {
  const fc = await import("./file-comments");
  const unit = fc.fileCommentsAction.mount(w.ctx) as unknown as El;
  const button = unit.childNodes[0] as El;
  answer(w, s); await flush();
  button.click();
  answer(w, s); await flush(); await flush();
  const aside = w.main.querySelector(".fileview-aside")!;
  assert.ok(aside, "the panel is mounted beside the body");
  return { button, aside, DECIDE: fc.DECIDE_IN_EDITOR, CHANGES_MOVED: fc.CHANGES_MOVED_UNDER_EDIT };
}
const card = (aside: El, key: string): El | null => aside.querySelector('.fc-card[data-id="' + key + '"]');
const act = (root: El, a: string, id?: string): El | null => root.querySelector('[data-act="' + a + '"]' + (id ? '[data-id="' + id + '"]' : ""));
const settle = (p: Promise<unknown>) => { const box: { ok?: unknown; err?: unknown } = {}; p.then((v) => { box.ok = v; }, (e) => { box.err = e; }); return box; };
const CHANGED = "the comments for ~/notes-api/docs/report.md changed on disk since you opened the file — reload and retry";
const FILE_CHANGED = "~/notes-api/docs/report.md changed on disk since you opened it — reload and retry";
const headRows = (aside: El): El[] => aside.querySelectorAll(".fc-sec-head .fc-err");
const CLOCK5 = "1757145600000000005";

// ── the gate again, at the send ─────────────────────────────────────────────────────────────────────

test("a decision whose click passed the gate before the editor opened is refused at the send: nothing goes to the kernel, the row says where to decide, and the seed-fenced Save goes through", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside, DECIDE } = await openPanel(w, pending());
  // the consent's read is out when the person clicks Accept on h1's card (the editor is not up: the gate lets it by)
  let allow!: (ok: boolean) => void;
  w.consent = () => new Promise<boolean>((r) => { allow = r; });
  const ok = act(card(aside, "chg:h1")!, "fcaccept", "h1")!;
  assert.equal(ok.classes.includes("fileview-btn-blocked"), false, "read mode: the card is live");
  ok.click(); await flush();
  assert.ok(card(aside, "chg:h1")!.querySelector(".fc-load"), "the slot waits on the consent");
  assert.equal(countOf(w, "fileComments", "accept"), 0, "nothing sent yet");
  // Edit lands first: the records ride into the editor, fenced on the sidecar as it stands
  w.editing = true;
  assert.deepEqual(w.tracked!.begin()!.records, [rec1, rec2]);
  // the consent answers: the decision would now move the sidecar under the editor's records — refused at the send
  allow(true); await flush(); await flush();
  assert.equal(countOf(w, "fileComments", "accept"), 0, "no accept went out");
  const row = card(aside, "chg:h1")!.querySelector(".fc-err")!;
  assert.ok(row, "the row sits under the card that asked");
  assert.equal(row.childNodes[0].textContent, DECIDE);
  assert.equal(card(aside, "chg:h1")!.querySelector(".fc-load"), null, "the slot is free again");
  assert.equal(headRows(aside).length, 0, "nothing moved: no head row");
  // the seed-fenced Save goes through with both records: the trap the gate exists to avoid
  const out = settle(w.tracked!.save("the typed text", [rec1, rec2], { accepted: [], rejected: [] }));
  await flush();
  const save = lastOf(w, "fileComments", "save");
  assert.ok(save, "the save verb");
  assert.equal(save.fence.storeMtimeNs, "1757145600000000002", "the sidecar as it stood at Edit");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: save.reqId, ...pending({ verb: "save", fileMtimeNs: "1757145600000000009", storeMtimeNs: "1757145600000000010" }), logged: true } }));
  await flush(); await flush();
  assert.deepEqual(out.ok, { mtimeNs: "1757145600000000009", logged: true });
});

test("a decision refused on a moved fence while the editor opens during its re-read is refused at the retry's send, not re-sent", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside, DECIDE } = await openPanel(w, pending());
  act(card(aside, "chg:h1")!, "fcaccept", "h1")!.click(); await flush(); await flush();
  const acc = lastOf(w, "fileComments", "accept");
  assert.ok(acc, "the request is out");
  // the host refuses on the sidecar's clock (a comment landed from elsewhere); the panel re-reads before its one retry
  const asks = countOf(w, "fileComments", "status");
  refuse(w, acc, "store-moved", CHANGED); await flush();
  assert.equal(countOf(w, "fileComments", "status"), asks + 1, "the re-read");
  // Edit opens meanwhile: the records ride in from the status showing
  w.editing = true;
  assert.deepEqual(w.tracked!.begin()!.records, [rec1, rec2]);
  // the re-read answers with the same records under a moved clock: the retry would move the sidecar under the editor
  answer(w, pending({ storeMtimeNs: CLOCK5 })); await flush(); await flush();
  assert.equal(countOf(w, "fileComments", "accept"), 1, "no retry went out");
  assert.equal(card(aside, "chg:h1")!.querySelector(".fc-err")!.childNodes[0].textContent, DECIDE);
  assert.equal(headRows(aside).length, 0, "the records are still the editor's: no head row");
});

// ── a decision that lands anyway: the head says so from the status that shows it ───────────────────

test("a decision whose request was out when Edit began: its reply lands under the editor and the head says the changes left the sidecar — before Save, which refuses with no retry; the row goes when the edit ends", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside, button, CHANGES_MOVED } = await openPanel(w, pending());
  assert.match(CHANGES_MOVED, /^Pending changes in this file were accepted or rejected after you opened the editor, which still shows them as pending\. Save will refuse; copy anything you typed, then Cancel and Edit again\.$/);
  act(card(aside, "chg:h1")!, "fcaccept", "h1")!.click(); await flush(); await flush();
  const acc = lastOf(w, "fileComments", "accept");
  assert.ok(acc, "the request is out");
  // Edit, while it is: the records ride in as they stand
  w.editing = true;
  assert.deepEqual(w.tracked!.begin()!.records, [rec1, rec2]);
  assert.equal(headRows(aside).length, 0);
  // the reply: h1 is gone from the sidecar; the file did not move (an accept changes no bytes)
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: acc.reqId, ...pending({ verb: "accept", storeMtimeNs: CLOCK5 }, [h2], [rec2]) } }));
  await flush(); await flush();
  assert.equal(button.textContent, "Comments · 1 · 1 change", "the status landed");
  const row = headRows(aside)[0];
  assert.ok(row, "the head says so at once, not at Save");
  assert.equal(row.childNodes[0].textContent, CHANGES_MOVED);
  assert.equal(row.querySelector('[data-act="fcreload"]'), null, "no Reload: a re-read changes nothing");
  assert.equal(w.reloads, 0, "never over the editor's buffer");
  // Save: fenced on the sidecar the records came from; refused; the re-read shows other records; no retry
  const out = settle(w.tracked!.save("the typed text", [rec1, rec2], { accepted: [], rejected: [] }));
  await flush();
  const save = lastOf(w, "fileComments", "save");
  assert.equal(save.fence.storeMtimeNs, "1757145600000000002");
  const asks = countOf(w, "fileComments", "status");
  refuse(w, save, "store-moved", CHANGED); await flush();
  assert.equal(countOf(w, "fileComments", "status"), asks + 1);
  answer(w, pending({ storeMtimeNs: CLOCK5 }, [h2], [rec2])); await flush(); await flush();
  assert.deepEqual(out.err, { code: "store-moved", error: CHANGED });
  assert.equal(countOf(w, "fileComments", "save"), 1, "no retry: the records changed");
  assert.equal(headRows(aside).length, 1, "one row, not one per status");
  // the edit ends (Cancel): the row goes with it, and the read view is painted from the status showing
  w.editing = false; w.setText(w.disk);
  assert.equal(headRows(aside).length, 0);
  assert.equal(w.reloads, 0, "nothing to re-read: the bytes never moved");
});

test("another browser's decision, seen by the poll: the head says the changes left the sidecar; dismissed, the row does not return with the next status; a new edit starts a new latch", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setInterval"] });
  const w = world(); t.after(() => w.close());
  const { aside, CHANGES_MOVED } = await openPanel(w, pending());
  w.editing = true;
  assert.deepEqual(w.tracked!.begin()!.records, [rec1, rec2]);
  // elsewhere, h1 was accepted: the sidecar moved, the file did not
  w.mtimes[STORE_PATH] = CLOCK5;
  const asks = countOf(w, "fileComments", "status");
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  assert.equal(countOf(w, "fileComments", "status"), asks + 1, "the poll re-reads");
  answer(w, pending({ storeMtimeNs: CLOCK5 }, [h2], [rec2])); await flush();
  const row = headRows(aside)[0];
  assert.ok(row);
  assert.equal(row.childNodes[0].textContent, CHANGES_MOVED);
  assert.equal(w.reloads, 0);
  // dismissed; a comment lands from elsewhere (the clock moves, the records stay): the row stays dismissed
  row.querySelector('[data-act="fcerrx"]')!.click();
  assert.equal(headRows(aside).length, 0);
  w.mtimes[STORE_PATH] = "1757145600000000006";
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  answer(w, pending({ storeMtimeNs: "1757145600000000006" }, [h2], [rec2])); await flush();
  assert.equal(headRows(aside).length, 0, "said once per edit");
  // the edit ends; a new Edit over the one change left; a decision elsewhere again: the row again
  w.editing = false; w.setText(w.disk);
  w.editing = true;
  assert.deepEqual(w.tracked!.begin()!.records, [rec2]);
  w.mtimes[STORE_PATH] = "1757145600000000007";
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  answer(w, status({ storeMtimeNs: "1757145600000000007" })); await flush();
  assert.equal(headRows(aside)[0].childNodes[0].textContent, CHANGES_MOVED, "a new edit, a new latch");
});

test("a status with the same records under a moved clock (a comment landed) raises no row: Save's own retry covers that", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setInterval"] });
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, pending());
  w.editing = true;
  w.tracked!.begin();
  const note: StoreComment = { ...passage, id: T0 + "-119", body: "Also: cite the benchmark.", anchor: null };
  const withNote = (mt: string) => pending({ storeMtimeNs: mt, store: { v: 3, path: "docs/report.md", suggestions: [rec1, rec2], comments: [passage, note] } });
  w.mtimes[STORE_PATH] = CLOCK5;
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  answer(w, withNote(CLOCK5)); await flush();
  assert.equal(headRows(aside).length, 0, "the records are the editor's own: nothing to say");
  // Save: refused on the seed's clock, re-read, retried once on the fresh one
  const out = settle(w.tracked!.save("the typed text", [rec1, rec2], { accepted: [], rejected: [] }));
  await flush();
  const first = lastOf(w, "fileComments", "save");
  assert.equal(first.fence.storeMtimeNs, "1757145600000000002");
  refuse(w, first, "store-moved", CHANGED); await flush();
  answer(w, withNote(CLOCK5)); await flush(); await flush();
  const retry = lastOf(w, "fileComments", "save");
  assert.equal(countOf(w, "fileComments", "save"), 2, "the one retry");
  assert.equal(retry.fence.storeMtimeNs, CLOCK5);
  assert.equal(headRows(aside).length, 0);
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: retry.reqId, ...withNote("1757145600000000010"), verb: "save", fileMtimeNs: "1757145600000000009", logged: true } }));
  await flush(); await flush();
  assert.deepEqual(out.ok, { mtimeNs: "1757145600000000009", logged: true });
});

test("a reject elsewhere moves the file too: the file's row (MOVED_UNDER_EDIT), not this one, and Cancel re-reads the bytes", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setInterval"] });
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, pending());
  w.editing = true;
  w.tracked!.begin();
  // elsewhere, h1 was rejected: the engine put "reduced" back, so the file moved with the sidecar
  w.disk = DOC.replace("cut", "reduced"); w.diskMtime = "1757145600000000033"; w.mtimes[ABS] = w.diskMtime; w.mtimes[STORE_PATH] = CLOCK5;
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  assert.equal(w.reloads, 0, "never over the editor's buffer");
  answer(w, pending({ fileMtimeNs: w.diskMtime, storeMtimeNs: CLOCK5 }, [h2], [rec2])); await flush();
  const rows = headRows(aside);
  assert.equal(rows.length, 1, "one row");
  assert.equal(rows[0].childNodes[0].textContent, MOVED_UNDER_EDIT, "the file's: it says the same about Save and adds what Cancel shows");
  // Cancel: the viewer repaints the bytes it loaded and fires onRendered; the panel re-reads the file as it is now
  w.editing = false; w.setText(DOC);
  assert.equal(w.reloads, 1);
  assert.ok(w.code.textContent.includes("reduced"), "the read view shows the file as it is now");
  assert.equal(headRows(aside).length, 0);
});

test("the save's store-moved re-read can show the file moved too: the head says so, as the poll's would, and the one retry is refused on the file", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w, pending());
  w.editing = true;
  w.tracked!.begin();
  const out = settle(w.tracked!.save("the typed text", [rec1, rec2], { accepted: [], rejected: [] }));
  await flush();
  const save = lastOf(w, "fileComments", "save");
  refuse(w, save, "store-moved", CHANGED); await flush();
  // the re-read: a comment moved the sidecar (the records stay), and a session appended to the file meanwhile
  w.disk = DOC + "\nAppended by the session.\n"; w.diskMtime = "1757145600000000033";
  answer(w, pending({ fileMtimeNs: w.diskMtime, storeMtimeNs: CLOCK5 })); await flush(); await flush();
  const rows = headRows(aside);
  assert.equal(rows.length, 1);
  assert.equal(rows[0].childNodes[0].textContent, MOVED_UNDER_EDIT);
  assert.equal(w.reloads, 0, "never over the buffer");
  // the records are still the editor's: the retry goes, fenced on the fresh sidecar and the file the editor loaded
  const retry = lastOf(w, "fileComments", "save");
  assert.equal(countOf(w, "fileComments", "save"), 2);
  assert.deepEqual(retry.fence, { storeMtimeNs: CLOCK5, configMtimeNs: "1757145600000000003", fileMtimeNs: "1757145600000000001" });
  refuse(w, retry, "file-moved", FILE_CHANGED); await flush(); await flush();
  assert.deepEqual(out.err, { code: "file-moved", error: FILE_CHANGED }, "a moved file is never retried past that");
  // Cancel re-reads the bytes the session wrote, as the row promised
  w.editing = false; w.setText(DOC);
  assert.equal(w.reloads, 1);
  assert.ok(w.code.textContent.includes("Appended by the session"));
  assert.equal(headRows(aside).length, 0);
});

// ── source ──────────────────────────────────────────────────────────────────────────────────────────

test("source: the gate runs again at the send, the row is raised where every status lands and yields to the file's, the edit's end retires it, and the save's re-read notes a moved file", () => {
  const once = SRC.split("private async mutateOnce(")[1].split("\n  }\n")[0];
  const gate = "if (DECIDES.has(verb) && this.ctx.editing()) { this.refuseDecision(slot); return null; }";
  assert.ok(once.indexOf(gate) >= 0 && once.indexOf(gate) < once.indexOf("const s = this.status;"), "at the send, before the fence is read from the status");
  const apply = SRC.split("applyStatus(s: Reply): boolean {")[1].split("\n  }\n")[0];
  assert.ok(apply.indexOf("this.noteChangesMovedUnderEdit();") >= 0 && apply.indexOf("this.noteChangesMovedUnderEdit();") < apply.indexOf("this.paintAll();"),
    "every status lands in applyStatus; the row is set before the render that status gets");
  const note = SRC.split("private noteChangesMovedUnderEdit(): void {")[1].split("\n  }\n")[0];
  assert.match(note, /if \(!seed \|\| !s \|\| !this\.ctx\.editing\(\) \|\| this\.changesMovedUnderEdit\) return;/, "records in an editor, and not said yet this edit");
  assert.match(note, /if \(laterNs\(s\.fileMtimeNs, this\.ctx\.mtimeNs\(\)\)\) return;/, "yields to the file's row");
  assert.match(note, /if \(sameRecords\(seed\.records, pendingRecords\(s\.store\)\)\) return;/, "keyed on the records, not the sidecar's clock");
  assert.match(note, /this\.errors\.set\("edit", \{ text: CHANGES_MOVED_UNDER_EDIT, reload: false \}\);/, "the head's slot, no Reload");
  const paint = SRC.split("paintAll(): void {")[1].split("\n  }\n")[0];
  assert.match(paint, /if \(this\.changesMovedUnderEdit\) \{ this\.changesMovedUnderEdit = false; if \(this\.errors\.get\("edit"\)\?\.text === CHANGES_MOVED_UNDER_EDIT\) this\.errors\.delete\("edit"\); \}/,
    "the first paint after the edit ends retires the row and the latch");
  const begin = SRC.split("begin: () => {")[1].split("\n      },\n")[0];
  assert.match(begin, /this\.changesMovedUnderEdit = false;/, "a new edit starts a new latch");
  const save = SRC.split("async saveThroughComments(")[1].split("\n  }\n")[0];
  assert.match(save, /await this\.refresh\(\);\n\s*this\.noteMovedUnderEdit\(\);/, "the save's re-read says when the file moved too");
});
