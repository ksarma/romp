// The Comments panel's change cards, driven AS A PANEL for what the Slice 2 review's third round found
// (plans/file-review.md, Slice 2; the contract's fence rule and its "stable id" premise):
//   • a by-id Accept or Reject refused on a moved fence is retried by its stable id ONLY while the change under that id
//     still reads as the card showed it. A same-author track-edit landing inside or beside a pending change is coalesced
//     into it under the same id with grown texts (engine.coalesceOps), so before this the retry accepted, or reverted,
//     text the person never saw; now the row under the card says nothing was decided, the card shows the new reading,
//     and the choice is theirs again. The same check stands on the first attempt, against a status that landed while
//     the consent dialog was up. A change whose texts are unchanged but whose offsets moved (an edit earlier in the
//     file) is still retried: the id names what the card showed.
//   • the chip beside a Raw mark reads the session's current name from the colour map, as the card's chip does, so a
//     renamed session's mark and card name it alike; an author with no live match keeps the sidecar's label.
//   • the send confirm's checkboxes are rebuilt on every change (the counts follow the boxes) and the rebuilt box takes
//     the keyboard back, so a Space on a box does not drop the focus to the body.
// The stand-in is the review2 suite's (focus semantics: a focusable enabled element takes focus; a removed one drops it
// to the body). Synthetic fixtures only: the notes-api world, placeholder ids.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import type { FileViewActionCtx } from "./file-view";
import { type Status, type Hunk, type StoreComment } from "./file-comments-model";

const web = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const SRC = web("file-comments.ts");

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const ROOT = "/repo/notes-api";
const STORE_PATH = ROOT + "/.trackchanges/docs%2Freport.md.json";
const T0 = 1757145600000;
const DOC = "# Report\n\n## Findings\nThe api session cut p95 latency by 40% and the p99 by 10%.\n\n"
  + "We recommend shipping the cache in v1.2.\n\nRisks remain in the fallback path.\n\nNext steps: measure again.\n";
const at = (needle: string, src = DOC): number => { const i = src.indexOf(needle); assert.ok(i >= 0, needle); return i; };
const H = (id: string, kind: Hunk["kind"], from: number, to: number, oldText: string, newText: string, ts = T0 - 90000, author = "api"): Hunk =>
  ({ id, author, ts, kind, curFrom: from, curTo: to, baseFrom: from, baseTo: from + oldText.length, oldText, newText, anchor: null });
const h1 = H("h1", "sub", at("cut"), at("cut") + 3, "reduced", "cut");
const h3 = H("h3", "del", at("shipping"), at("shipping"), "quickly ", "", T0 - 70000);
/** The same change with its offsets moved by `n` — hunks computed over another string. */
const shifted = (h: Hunk, n: number): Hunk => ({ ...h, curFrom: h.curFrom + n, curTo: h.curTo + n });
const passage: StoreComment = {
  id: T0 + "-118", author: "you", ts: T0, body: "Which cache? Say which.",
  anchor: { quote: "shipping the cache in v1.2", prefix: "We recommend ", suffix: "." }, replies: [], resolved: false,
};
const SUGG = [{ id: "h1", author: "api", authorId: SID, ts: T0 - 90000, kind: "sub", from: h1.curFrom, oldText: "reduced", newText: "cut" },
  { id: "h3", author: "api", ts: T0 - 70000, kind: "del", from: h3.curFrom, oldText: "quickly " }];
// The session's second track-edit, `--old cut --new "cut sharply"`, landed INSIDE its pending h1: the engine records
// the insertion adjacent to h1 and coalesces it in — same id, newText grown, the file holding the new words, and every
// later change moved by the insertion's length.
const DOC_GROWN = DOC.replace("cut p95", "cut sharply p95");
const GROWTH = " sharply".length;
const h1g = H("h1", "sub", at("cut"), at("cut") + "cut sharply".length, "reduced", "cut sharply");
const SUGG_GROWN = [{ ...SUGG[0], newText: "cut sharply" }, { ...SUGG[1], from: h3.curFrom + GROWTH }];
// An edit EARLIER in the file, a change of its own: h1 and h3 keep their texts and move by four
const DOC_V2 = DOC.replace("# Report", "# Report, v2");
const h0 = H("h0", "ins", at(", v2", DOC_V2), at(", v2", DOC_V2) + 4, "", ", v2", T0 - 10000);
const SUGG_V2 = [{ id: "h0", author: "api", authorId: SID, ts: T0 - 10000, kind: "ins", from: h0.curFrom, oldText: "", newText: ", v2" },
  { ...SUGG[0], from: h1.curFrom + 4 }, { ...SUGG[1], from: h3.curFrom + 4 }];
const F1 = "1757145600000000001", S2 = "1757145600000000002", C3 = "1757145600000000003";
const S9 = "1757145600000000009", F11 = "1757145600000000011", S12 = "1757145600000000012";
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
/** The status after the coalescing track-edit: the file and the sidecar both moved, h1 grown, h3 shifted. */
const grownStatus = (): Status => status({ fileMtimeNs: F11, storeMtimeNs: S9, hunks: [h1g, shifted(h3, GROWTH)],
  store: { v: 3, path: "docs/report.md", suggestions: SUGG_GROWN, comments: [passage] } });
const MOVED_STORE = "the comments for ~/notes-api/docs/report.md changed on disk since you opened the file — reload and retry";
const MOVED_FILE = "~/notes-api/docs/report.md changed since the panel read it";
const ROW_ONE = "Nothing decided: the session edited this change after you clicked, and it now reads differently. Look it over and try again.";

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
  hooks: { rendered: Array<() => void>; close: Array<() => void> };
  disk: string; diskMtime: string; viewMtime: string; reloads: number; scrolls: number[]; modes: string[];
  mtimes: Record<string, string>;
  close(): void;
};
let cur: World | null = null;
/** What GET /sessions answers: the local kernel's sessions, each with its CURRENT name and colour. */
let sessions: Array<Record<string, string>> = [{ id: SID, name: "api", bg: "#123456", fg: "#ffffff" }];
(globalThis as any).fetch = async (url: string) => {
  if (url.includes("/sessions")) return { json: async () => sessions };
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
function world(): World {
  const main = new El("div"); main.className = "fileview-main";
  const body = new El("div"); body.className = "fileview-body";
  main.appendChild(body);
  let text = DOC;
  const wrap = new El("div"); wrap.className = "fileview-code";
  const pre = new El("pre"); pre.className = "fileview-pre fileview-wrap";
  const code = new El("code"); code.className = "hljs";
  pre.appendChild(code); wrap.appendChild(pre); body.appendChild(wrap);
  rows(code, text);
  const w = {
    posted: [] as any[], main, body,
    hooks: { rendered: [] as Array<() => void>, close: [] as Array<() => void> },
    disk: text, diskMtime: F1, viewMtime: F1, reloads: 0, scrolls: [] as number[], modes: [] as string[], mtimes: {} as Record<string, string>,
  } as World;
  const setText = (s: string) => { text = s; rows(code, s); for (const cb of w.hooks.rendered) cb(); };
  w.ctx = {
    path: ABS, sid: SID, todoId: null,
    body: () => body as unknown as HTMLElement, mode: () => "raw", text: () => text, mtimeNs: () => w.viewMtime, media: () => null,
    identity: () => ({ name: "api", color: null }),
    onRendered: (cb) => { w.hooks.rendered.push(cb); }, onSelection: () => { /* inert */ },
    onSaved: () => { /* inert */ }, onClose: (cb) => { w.hooks.close.push(cb); },
    post: (m) => { w.posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: () => { /* inert */ },
    aside: (node) => { main.querySelector(".fileview-aside")?.remove(); if (node) { const n = node as unknown as El; n.classList.add("fileview-aside"); main.appendChild(n); } },
    setMode: (m) => { w.modes.push(m); }, scrollToOffset: (n) => { w.scrolls.push(n); },
    // fetchFile: an async GET in the real seam — landed at once here, with the disk's bytes and mtime
    reload: () => { w.reloads++; w.viewMtime = w.diskMtime; setText(w.disk); },
  };
  w.close = () => { for (const cb of w.hooks.close) cb(); if (cur === w) cur = null; };
  cur = w;
  return w;
}
const flush = () => new Promise<void>((r) => setImmediate(r));
const lastOf = (w: World, type: string, verb?: string) => [...w.posted].reverse().find((m) => m.type === type && (verb === undefined || m.verb === verb));
const countOf = (w: World, type: string, verb?: string) => w.posted.filter((m) => m.type === type && (verb === undefined || m.verb === verb)).length;
/** Answer the ask `m` with `s`; the HEADs follow this reply's mtimes. */
function answer(w: World, s: Status, m = lastOf(w, "fileComments", "status"), extra: Record<string, unknown> = {}): void {
  assert.ok(m, "an ask is outstanding");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: m.reqId, ...s, ...extra } }));
  w.mtimes[w.ctx.path] = s.fileMtimeNs;
  if (s.storePath) { if (s.storeMtimeNs !== null) w.mtimes[s.storePath] = s.storeMtimeNs; else delete w.mtimes[s.storePath]; }
  if (s.root && s.configMtimeNs !== null) w.mtimes[s.root + "/.trackchanges/config.json"] = s.configMtimeNs;
}
function refuse(w: World, m: any, code: string, error: string): void {
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsFailed", reqId: m.reqId, verb: m.verb, code, error } }));
}
/** Mount and answer the probe: the action row's button, the panel still closed. */
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
  return { unit, button, aside };
}
const card = (aside: El, key: string): El | null => aside.querySelector('.fc-card[data-id="' + key + '"]');
const act = (root: El, a: string, id?: string): El | null => root.querySelector('[data-act="' + a + '"]' + (id ? '[data-id="' + id + '"]' : ""));
const marksOf = (w: World, id?: string): El[] => w.body.querySelectorAll('[data-act="fcchange"]' + (id ? '[data-id="' + id + '"]' : ""));
const rowOf = (aside: El, slot: string): El | null => aside.querySelector('.fc-err[data-slot="' + slot + '"]');

// ── the pure half ──────────────────────────────────────────────────────────────────────────────────

test("seenChanges and changedSince: a change is 'grown' when its id is still pending with other texts; gone is not grown, and moved is not grown", async () => {
  const { seenChanges, changedSince, changedRowText } = await import("./file-comments");
  const seen = seenChanges(status(), { ids: ["h1"] });
  assert.deepEqual(seen, [{ id: "h1", kind: "sub", oldText: "reduced", newText: "cut" }], "the texts as the card showed them, by id");
  assert.deepEqual(seenChanges(status(), { ids: ["nope"] }), [], "an id the status does not list: nothing seen");
  assert.deepEqual(seenChanges(status(), {}), [], "no ids (the bulk verbs): nothing seen");
  assert.deepEqual(seenChanges(null, { ids: ["h1"] }), []);
  assert.deepEqual(changedSince(seen, [h1g, shifted(h3, GROWTH)]).map((c) => c.id), ["h1"], "newText grew under the same id: grown");
  assert.deepEqual(changedSince(seen, [{ ...h1, oldText: "reduced " }]).map((c) => c.id), ["h1"], "oldText grew (a coalesced deletion): grown");
  assert.deepEqual(changedSince(seen, [{ ...h1, kind: "ins", oldText: "" }]).map((c) => c.id), ["h1"], "the kind changed: grown");
  assert.deepEqual(changedSince(seen, [h0, shifted(h1, 4), shifted(h3, 4)]), [], "the same texts at other offsets: the change the card showed");
  assert.deepEqual(changedSince(seen, [h3]), [], "the id is gone: not grown — the host's no-change refusal names it");
  assert.deepEqual(changedSince([], [h1g]), []);
  assert.equal(changedRowText(1), ROW_ONE);
  assert.equal(changedRowText(2), "Nothing decided: the session edited these changes after you clicked, and they now read differently. Look it over and try again.");
  assert.doesNotMatch(changedRowText(1), /—|card|board|goal|nudge|sidecar|fence|coalesc/i, "the person's words: no dashes, no machinery");
});

// ── a by-id decision over a change that grew ───────────────────────────────────────────────────────

test("Accept refused store-moved, the change grown under its id by the session's coalesced track-edit: no retry, the row under the card says nothing was decided, the card shows the new reading over the re-fetched bytes, and a second click decides over it", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  assert.equal(card(aside, "chg:h1")!.querySelector(".fc-ref")!.textContent, "reduced → cut", "what the person clicked on");
  act(card(aside, "chg:h1")!, "fcaccept", "h1")!.click(); await flush();
  const first = lastOf(w, "fileComments", "accept");
  assert.deepEqual(first.args, { ids: ["h1"] });
  assert.equal(first.fence.storeMtimeNs, S2);
  // the session's track-edit landed: the sidecar h1 grown AND the file holding "cut sharply" — the refusal names the sidecar
  w.disk = DOC_GROWN; w.diskMtime = F11;
  refuse(w, first, "store-moved", MOVED_STORE); await flush();
  // the fresh status: h1 still pending under its id, its new text now "cut sharply"
  answer(w, grownStatus()); await flush(); await flush();
  assert.equal(countOf(w, "fileComments", "accept"), 1, "no retry: the id names a change the person has not seen");
  assert.equal(w.reloads, 1, "the file moved with the sidecar: the fresh status's mtime re-fetches the bytes (before, a store-moved left the old text up with no marks)");
  assert.equal(w.viewMtime, F11);
  assert.ok(marksOf(w, "h1").some((m) => m.textContent === "cut sharply"), "the grown change is marked over the new bytes");
  const c1 = card(aside, "chg:h1")!;
  assert.equal(c1.querySelector(".fc-ref")!.textContent, "reduced → cut sharply", "the card shows the new reading");
  const row = rowOf(aside, "change:h1")!;
  assert.ok(row, "the row sits under the card");
  assert.ok(c1.contains(row));
  assert.equal(row.textContent.replace(/✕$/, ""), ROW_ONE, "in the person's words");
  assert.equal(act(row, "fcreload"), null, "the list was re-read already: no Reload");
  assert.ok(act(row, "fcerrx"), "…but a dismissal");
  assert.equal(aside.querySelectorAll(".fc-load").length, 0, "the wait is over");
  const ok = act(c1, "fcaccept", "h1")!;
  assert.equal(ok.disabled, false); assert.equal(ok.textContent, "Accept");
  // the person looks it over and clicks again: a fresh request with the fresh fence, the row cleared
  ok.click(); await flush();
  const again = lastOf(w, "fileComments", "accept");
  assert.notEqual(again.reqId, first.reqId);
  assert.deepEqual(again.args, { ids: ["h1"] });
  assert.equal(again.fence.storeMtimeNs, S9, "the fence from the re-read status");
  assert.equal(rowOf(aside, "change:h1"), null, "a new click clears the row");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: again.reqId,
    ...status({ fileMtimeNs: F11, storeMtimeNs: S12, hunks: [shifted(h3, GROWTH)], store: { v: 3, path: "docs/report.md", suggestions: [SUGG_GROWN[1]], comments: [passage] },
      unsent: { comments: [passage.id], replies: [], accepted: 1, rejected: 0, watermark: null } }), verb: "accept", accepted: ["h1"] } })); await flush();
  assert.equal(card(aside, "chg:h1"), null, "decided, over what the person saw this time");
  assert.equal(aside.querySelectorAll(".fc-err").length, 0);
});

test("Reject refused file-moved with the change grown: the bytes are repainted and the grown change marked over them, and the reject is NOT retried — the retry would have reverted the words the session added after the click", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  act(card(aside, "chg:h1")!, "fcreject", "h1")!.click(); await flush();
  const first = lastOf(w, "fileComments", "reject");
  assert.equal(first.fence.fileMtimeNs, F1);
  // the session's track-edit landed: the file holds "cut sharply", the sidecar h1 grown
  w.disk = DOC_GROWN; w.diskMtime = F11;
  refuse(w, first, "file-moved", MOVED_FILE); await flush();
  answer(w, grownStatus()); await flush(); await flush();
  assert.equal(w.reloads, 1, "the file moved under the view: its bytes are re-fetched (the moved branch, as before)");
  assert.equal(w.viewMtime, F11);
  assert.equal(countOf(w, "fileComments", "reject"), 1, "no retry");
  assert.ok(marksOf(w, "h1").some((m) => m.textContent === "cut sharply"), "the grown change is marked over the new bytes");
  const row = rowOf(aside, "change:h1")!;
  assert.ok(row && card(aside, "chg:h1")!.contains(row), "the row under the card");
  assert.equal(row.textContent.replace(/✕$/, ""), ROW_ONE);
  assert.equal(card(aside, "chg:h1")!.querySelector(".fc-ref")!.textContent, "reduced → cut sharply");
  assert.equal(act(card(aside, "chg:h1")!, "fcreject", "h1")!.disabled, false, "Reject is theirs again");
  assert.equal(act(card(aside, "chg:h3")!, "fcreject", "h3")!.disabled, false, "the other card is untouched");
});

test("the retry by stable id stands when the change reads as it did: an edit earlier in the file moved h1's offsets, and the retry goes with the fresh fence", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  act(card(aside, "chg:h1")!, "fcaccept", "h1")!.click(); await flush();
  const first = lastOf(w, "fileComments", "accept");
  refuse(w, first, "store-moved", MOVED_STORE); await flush();
  answer(w, status({ fileMtimeNs: F11, storeMtimeNs: S9, hunks: [h0, shifted(h1, 4), shifted(h3, 4)],
    store: { v: 3, path: "docs/report.md", suggestions: SUGG_V2, comments: [passage] } })); await flush(); await flush();
  const retry = lastOf(w, "fileComments", "accept");
  assert.ok(retry && retry.reqId !== first.reqId, "one retry");
  assert.deepEqual(retry.args, { ids: ["h1"] });
  assert.equal(retry.fence.storeMtimeNs, S9, "…with the fresh fence");
  assert.equal(aside.querySelectorAll(".fc-err").length, 0, "no row: the change is the one the card showed");
  assert.ok(card(aside, "chg:h0"), "the new change has its own card, undecided");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: retry.reqId,
    ...status({ fileMtimeNs: F11, storeMtimeNs: S12, hunks: [h0, shifted(h3, 4)], store: { v: 3, path: "docs/report.md", suggestions: [SUGG_V2[0], SUGG_V2[2]], comments: [passage] },
      unsent: { comments: [passage.id], replies: [], accepted: 1, rejected: 0, watermark: null } }), verb: "accept", accepted: ["h1"] } })); await flush();
  assert.equal(card(aside, "chg:h1"), null);
  assert.ok(card(aside, "chg:h0") && card(aside, "chg:h3"));
});

test("the check stands on the first attempt too: a status the poll applied while the consent dialog was up shows the change grown, and no request goes at all", async (t: TestContext) => {
  t.mock.timers.enable({ apis: ["setInterval"] });
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  const held = { consent: null as ((ok: boolean) => void) | null };   // an object: TS does not follow an assignment made inside the promise's closure
  w.ctx.ensureEditingAllowed = () => new Promise<boolean>((r) => { held.consent = r; });
  act(card(aside, "chg:h1")!, "fcaccept", "h1")!.click(); await flush();
  assert.ok(held.consent, "the consent is up");
  assert.equal(countOf(w, "fileComments", "accept"), 0, "nothing sent before the consent");
  assert.equal(act(card(aside, "chg:h1")!, "fcaccept", "h1")!.textContent, "Accepting…");
  // meanwhile the session's track-edit lands; the poll sees both clocks move, repaints the bytes and re-reads
  w.disk = DOC_GROWN; w.diskMtime = F11; w.mtimes[ABS] = F11; w.mtimes[STORE_PATH] = S9;
  t.mock.timers.tick(2500); await flush(); await flush(); await flush();
  assert.equal(w.reloads, 1);
  answer(w, grownStatus()); await flush(); await flush();
  assert.equal(card(aside, "chg:h1")!.querySelector(".fc-ref")!.textContent, "reduced → cut sharply", "the card moved on while the dialog was up");
  held.consent!(true); await flush(); await flush();
  assert.equal(countOf(w, "fileComments", "accept"), 0, "the consent's yes decides nothing: the change is not the one clicked");
  const row = rowOf(aside, "change:h1")!;
  assert.ok(row && card(aside, "chg:h1")!.contains(row));
  assert.equal(row.textContent.replace(/✕$/, ""), ROW_ONE);
  assert.equal(act(card(aside, "chg:h1")!, "fcaccept", "h1")!.disabled, false);
});

test("source: the by-id verbs are named, the seen changes are kept from the status the card was rendered from, and the check runs before every request", () => {
  assert.match(SRC, /const DECIDE_VERBS = new Set\(\["accept", "reject"\]\);/);
  const mutate = SRC.split("async mutate(verb: string")[1].split("\n  }\n")[0];
  const pos = (s: string) => { const i = mutate.indexOf(s); assert.ok(i >= 0, "mutate has: " + s); return i; };
  assert.ok(pos("await this.requireStatus(slot)") < pos("if (DECIDE_VERBS.has(verb)) this.seen.set(slot, seenChanges(this.status, args));"), "after the status, before the consent");
  assert.ok(pos("this.seen.set(slot") < pos("await this.ctx.ensureEditingAllowed()"));
  assert.match(mutate, /finally \{ this\.busy\.delete\(slot\); this\.busyVerb\.delete\(slot\); this\.seen\.delete\(slot\); this\.render\(\); \}/, "cleared with the slot");
  const once = SRC.split("private async mutateOnce(")[1].split("\n  }\n")[0];
  const at = (s: string) => { const i = once.indexOf(s); assert.ok(i >= 0, "mutateOnce has: " + s); return i; };
  assert.ok(at("const grown = seen && s ? changedSince(seen, s.hunks || []) : [];") < at("await this.request(verb, args, fence)"), "the check precedes the request, on the first attempt and the retry alike");
  assert.match(once, /if \(grown\.length\) \{ this\.errors\.set\(slot, \{ text: changedRowText\(grown\.length\), reload: false \}\); return null; \}/);
});

// ── the Raw mark's chip names the session as the card does ─────────────────────────────────────────

test("the inline chip reads the session's CURRENT name from the colour map, as the card's chip does; an author with no live match keeps the sidecar's label", async (t: TestContext) => {
  // the sidecar's author is the session's name when it wrote the change (track-edit's sessionLabel); the session was renamed since
  const before = sessions;
  sessions = [{ id: SID, name: "web-2", bg: "#123456", fg: "#ffffff" }];
  t.after(() => { sessions = before; });
  const w = world(); t.after(() => w.close());
  const h1web = { ...h1, author: "web" };
  const { aside } = await openPanel(w, status({ hunks: [h1web, h3], store: { v: 3, path: "docs/report.md", suggestions: [{ ...SUGG[0], author: "web" }, SUGG[1]], comments: [passage] } }));
  assert.equal(card(aside, "chg:h1")!.querySelector(".fc-chip")!.textContent, "web-2", "the card's chip: the current name");
  const chip1 = w.body.querySelectorAll('[data-fc-chip][data-id="h1"]');
  assert.equal(chip1.length, 1, "one chip per change");
  assert.equal(chip1[0].getAttribute("data-fc-chip"), "web-2", "the mark's chip: the same name");
  assert.equal(chip1[0].getAttribute("data-author"), "web", "the sidecar's label stays on data-author");
  assert.match(chip1[0].getAttribute("style") || "", /--fc-author: #123456/, "painted with the map loaded: the colour and the name come from the same map");
  // h3 has no authorId: no live match, so the sidecar's label, on the card and on the mark alike
  assert.equal(card(aside, "chg:h3")!.querySelector(".fc-chip")!.textContent, "api");
  const chip3 = w.body.querySelectorAll('[data-fc-chip][data-id="h3"]');
  assert.equal(chip3.length, 1);
  assert.equal(chip3[0].getAttribute("data-fc-chip"), "api");
  assert.match(SRC, /label: col \? col\.name : undefined \}/, "paintChanges hands the painter the mapped name");
});

// ── the send confirm's checkboxes keep the keyboard ────────────────────────────────────────────────

/** Focus the confirm's `key` box, flip it, fire change: the rebuilt box holds the keyboard and the new state. */
function flipHoldsFocus(aside: El, key: string): El {
  const cb = aside.querySelector('input[data-opt="' + key + '"]')!;
  assert.ok(cb, "the " + key + " box is offered");
  cb.focus();
  assert.equal(doc.activeElement, cb, "the keyboard is on the box");
  const was = cb.checked;
  cb.checked = !was;
  dispatch(cb, new Ev("change"));
  const after = aside.querySelector('input[data-opt="' + key + '"]')!;
  assert.ok(after, "the box is offered again");
  assert.notEqual(after, cb, "the confirm was rebuilt (the counts follow the boxes)");
  assert.equal(aside.contains(cb), false, "the old box is gone from the panel");
  assert.equal(doc.activeElement, after, "the rebuilt box holds the keyboard");
  assert.equal(after.checked, !was, "…and the new state");
  return after;
}

test("a Space on a confirm checkbox rebuilds the confirm and the rebuilt box takes the keyboard back: the accept box on a tracked file, the tracking box on an untracked one, the todo box when the file came from one", async (t: TestContext) => {
  const w = world(); t.after(() => w.close());
  const { aside } = await openPanel(w);
  act(aside, "fcsend")!.click();
  assert.ok(aside.querySelector(".fc-list")!.textContent.includes("2 accepted, 0 rejected"), "the box checked: the two pending changes count");
  const off = flipHoldsFocus(aside, "accept");
  assert.equal(off.checked, false);
  assert.doesNotMatch(aside.querySelector(".fc-list")!.textContent, /accepted/, "unchecked: the decisions line is gone");
  const on = flipHoldsFocus(aside, "accept");
  assert.equal(on.checked, true);
  assert.ok(aside.querySelector(".fc-list")!.textContent.includes("2 accepted, 0 rejected"), "…and back");
  w.close();
  const w2 = world(); t.after(() => w2.close());
  const { aside: a2 } = await openPanel(w2, status({ trackedBy: null }));
  act(a2, "fcsend")!.click();
  flipHoldsFocus(a2, "track");
  flipHoldsFocus(a2, "accept");
  w2.close();
  const w3 = world(); t.after(() => w3.close());
  w3.ctx.todoId = "11111111-2222-3333-4444-666666666666";
  const { aside: a3 } = await openPanel(w3);
  act(a3, "fcsend")!.click();
  flipHoldsFocus(a3, "todo");
  // the mend at source: the checkbox's identity for focusKey and findControl
  assert.match(SRC, /: a\.dataset\.opt \? \{ act: "opt", key: a\.dataset\.opt \} : null;/, "focusKey: a confirm checkbox, by its option");
  assert.match(SRC, /if \(k\.act === "opt"\) return this\.root\.querySelector\('\[data-opt="' \+ k\.key \+ '"\]'\) as HTMLElement \| null;/, "findControl re-finds it");
});
