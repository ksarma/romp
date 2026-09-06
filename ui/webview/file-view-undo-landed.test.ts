// Undo against a landed save, and Cancel during one, at the REAL openFileView (plans/file-review.md Slice 5; the review
// of that slice's round-1 fixes):
//
// 1. The editor's history has no boundary at a save, and undoing a decision puts the record back in the field and takes
//    the ledger entry with it (editor-chunk.ts). A landed save has applied and logged that decision, and the host has no
//    verb that takes one back. Before this, an accept undone DURING the round-trip exited edit mode at the ack with the
//    accept standing on disk and not a word (the undo moved no text and left nothing beyond `applied`), and an undo
//    reaching past a landed save followed by Save sent the restored record among the suggestions: the host wrote it
//    back as pending over a log that says accepted (and counted a later accept twice), or refused with a caller-bug
//    error when that save had pruned the sidecar. Now such a record makes the buffer dirty, the ack that shows one
//    keeps the editor and says so, and Save refuses in words; redo, a reversal, and Cancel are the ways out.
// 2. Cancel confirmed while a save through the panel was in flight dropped the ack, and the panel had already applied
//    the reply as its status, so its poll's baseline was the saved file and no tick ever noticed the view still showed
//    the bytes from before (saveFile's dropped ack was healed by the next tick). The late ack now heals the view.
//
// The DOM stand-in, the editor-chunk stub and the kernel stubs are the ones file-view-edit-races.test.ts carries (that
// file exports nothing, and node:test runs each bundled file in its own process). Synthetic fixtures only: the notes-api
// world, placeholder ids.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import type { FileViewActionCtx } from "./file-view";
import type { Status, Hunk } from "./file-comments-model";

// ── a DOM stand-in: ancestry, ids, attributes, events with capture and bubbling, a small selector engine ──
class Ev {
  target: El | Txt | null = null;
  currentTarget: El | null = null;
  defaultPrevented = false;
  stopped = false;
  key: string; ctrlKey: boolean; metaKey: boolean;
  constructor(public type: string, init: { key?: string; ctrlKey?: boolean; metaKey?: boolean } = {}) {
    this.key = init.key || ""; this.ctrlKey = !!init.ctrlKey; this.metaKey = !!init.metaKey;
  }
  preventDefault(): void { this.defaultPrevented = true; }
  stopPropagation(): void { this.stopped = true; }
}
type Listener = (ev: Ev) => void;
type Reg = { type: string; cb: Listener; capture: boolean; once: boolean };
const optsOf = (o?: boolean | { capture?: boolean; once?: boolean }) =>
  typeof o === "boolean" ? { capture: o, once: false } : { capture: !!(o && o.capture), once: !!(o && o.once) };
const kebab = (k: string) => k.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
class Txt {
  nodeType = 3;
  parentNode: El | null = null;
  constructor(public data: string) {}
  get textContent(): string { return this.data; }
  get parentElement(): El | null { return this.parentNode; }
  splitText(off: number): Txt {
    const tail = new Txt(this.data.slice(off));
    this.data = this.data.slice(0, off);
    const p = this.parentNode;
    if (p) { const i = p.childNodes.indexOf(this); p.childNodes.splice(i + 1, 0, tail); tail.parentNode = p; }
    return tail;
  }
}
type Compound = { tag: string | null; id: string | null; classes: string[]; attrs: Array<[string, string | null]> };
function parseSel(sel: string): Compound[][] {
  return sel.split(",").map((g) => g.trim()).filter(Boolean).map((g) => g.split(/\s+/).map((s) => {
    const m = /^([a-zA-Z][\w-]*)?(#[\w-]+)?((?:\.[\w-]+)*)((?:\[[\w-]+(?:="[^"]*")?\])*)$/.exec(s);
    if (!m) throw new Error("stand-in: unsupported selector " + s);
    const classes = (m[3].match(/\.[\w-]+/g) || []).map((c) => c.slice(1));
    const attrs: Array<[string, string | null]> = [];
    for (const a of m[4].match(/\[[^\]]+\]/g) || []) { const am = /^\[([\w-]+)(?:="([^"]*)")?\]$/.exec(a)!; attrs.push([am[1], am[2] ?? null]); }
    return { tag: m[1] ? m[1].toUpperCase() : null, id: m[2] ? m[2].slice(1) : null, classes, attrs };
  }));
}
class El {
  nodeType = 1;
  tagName: string;
  parentNode: El | null = null;
  childNodes: Array<El | Txt> = [];
  attrs = new Map<string, string>();
  listeners: Reg[] = [];
  hidden = false; disabled = false; title = ""; type = ""; value = ""; placeholder = ""; spellcheck = true; wrap = "";
  src = ""; alt = ""; href = ""; download = ""; target = ""; rel = "";
  innerHTML = "";
  style: Record<string, string> = {};
  onclick: ((ev: Ev) => void) | null = null;
  scrolled = 0;
  constructor(tag: string) { this.tagName = tag.toUpperCase(); }
  get id(): string { return this.attrs.get("id") || ""; }
  set id(v: string) { this.attrs.set("id", v); }
  get isConnected(): boolean { return doc.body.contains(this); }
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
  prepend(...ns: Array<El | Txt>): void { for (const n of ns.slice().reverse()) { this.detach(n); this.childNodes.unshift(n); n.parentNode = this; } }
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
    return (!c.tag || c.tag === this.tagName) && (!c.id || c.id === this.id) && c.classes.every((k) => this.classes.includes(k))
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
  addEventListener(type: string, cb: Listener, o?: boolean | { capture?: boolean; once?: boolean }): void { this.listeners.push({ type, cb, ...optsOf(o) }); }
  removeEventListener(type: string, cb: Listener, o?: boolean | { capture?: boolean }): void {
    const cap = optsOf(o).capture;
    this.listeners = this.listeners.filter((l) => !(l.type === type && l.cb === cb && l.capture === cap));
  }
  dispatchEvent(ev: Ev): boolean { return dispatch(this, ev); }
  click(): void { this.dispatchEvent(new Ev("click")); }
  focus(): void { doc.activeElement = this; }
  blur(): void { if (doc.activeElement === this) doc.activeElement = null; }
  scrollIntoView(): void { this.scrolled++; }
  getBoundingClientRect(): { left: number; top: number; right: number; bottom: number; width: number; height: number } { return { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 }; }
  get offsetWidth(): number { return 0; }
}
const doc = {
  listeners: [] as Reg[],
  body: null as unknown as El,
  head: null as unknown as El,
  hidden: false,
  activeElement: null as El | null,
  createElement: (tag: string) => new El(tag),
  createTextNode: (s: string) => new Txt(s),
  getElementById: (id: string): El | null => doc.body.querySelector("#" + id),
  querySelectorAll: (sel: string): El[] => doc.body.querySelectorAll(sel),
  addEventListener(type: string, cb: Listener, o?: boolean | { capture?: boolean; once?: boolean }): void { doc.listeners.push({ type, cb, ...optsOf(o) }); },
  removeEventListener(type: string, cb: Listener, o?: boolean | { capture?: boolean }): void {
    const cap = optsOf(o).capture;
    doc.listeners = doc.listeners.filter((l) => !(l.type === type && l.cb === cb && l.capture === cap));
  },
  contains: (n: El | Txt | null) => doc.body.contains(n),
};
doc.body = new El("body"); doc.head = new El("head");
function dispatch(target: El | Txt, ev: Ev): boolean {
  ev.target = target;
  const chain: El[] = [];
  for (let n: El | null = target instanceof El ? target : target.parentNode; n; n = n.parentNode) chain.push(n);
  const run = (owner: { listeners: Reg[] }, capture: boolean, node: El | null): boolean => {
    for (const l of owner.listeners.slice()) {
      if (l.type !== ev.type || l.capture !== capture) continue;
      if (l.once) owner.listeners = owner.listeners.filter((x) => x !== l);
      ev.currentTarget = node; l.cb.call(node, ev);
      if (ev.stopped) return true;
    }
    if (node && !capture && ev.type === "click" && node.onclick) node.onclick(ev);
    return false;
  };
  if (run(doc, true, null)) return !ev.defaultPrevented;
  for (let i = chain.length - 1; i >= 0; i--) if (run(chain[i], true, chain[i])) return !ev.defaultPrevented;
  for (const n of chain) if (run(n, false, n)) return !ev.defaultPrevented;
  run(doc, false, null);
  return !ev.defaultPrevented;
}
const win: any = new EventTarget();
win.parent = win; win.innerWidth = 1200; win.innerHeight = 800;
win.getSelection = () => null;
win.confirm = () => true;
win.postMessage = () => { /* our own window: nothing listens here */ };
(globalThis as any).window = win;
(globalThis as any).document = doc;
const store = new Map<string, string>();
(globalThis as any).localStorage = {
  getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
  setItem: (k: string, v: string) => { store.set(k, String(v)); },
  removeItem: (k: string) => { store.delete(k); },
};

// ── the editor chunk: a buffer, the two callbacks, and the track option's handle (records + a ledger with no reset) ──
type Entry = { id: string; oldText: string; newText: string };
type Decided = { accepted: Entry[]; rejected: Entry[] };
type TrackStub = { suggestions: unknown[]; authorColor: (a: string) => string | null; onLedger: (l: Decided) => void };
const ed = {
  buf: "", onChange: null as (() => void) | null, mounted: 0, destroyed: 0,
  trackOpts: null as TrackStub | null, records: [] as unknown[], ledger: { accepted: [], rejected: [] } as Decided,
};
win.__rompEditor = {
  mount(host: El, opts: { text: string; onChange: () => void; onSave: () => void; track?: TrackStub }) {
    ed.buf = opts.text; ed.onChange = opts.onChange; ed.mounted++; ed.trackOpts = opts.track || null;
    host.appendChild(new Txt(opts.text));
    const h: { value(): string; focus(): void; destroy(): void; track?: { suggestions(): unknown[]; ledger(): Decided } } =
      { value: () => ed.buf, focus() { /* inert */ }, destroy() { ed.destroyed++; } };
    if (opts.track) {
      ed.records = opts.track.suggestions.slice(); ed.ledger = { accepted: [], rejected: [] };
      h.track = { suggestions: () => ed.records, ledger: () => ed.ledger };
    }
    return h;
  },
};
const typeInto = (s: string) => { ed.buf = s; ed.onChange!(); };
/** An in-editor decision: the chunk drops the record from its field and reports the ledger (no text change on an accept). */
const decideInEditor = (side: "accepted" | "rejected", id: string) => {
  ed.records = ed.records.filter((r) => (r as { id: string }).id !== id);
  ed.ledger = { ...ed.ledger, [side]: [...ed.ledger[side], entry(id)] };
  ed.trackOpts!.onLedger(ed.ledger);
};
/** The chunk's ledger after an undo or a redo: what the field now holds, reported as the real chunk reports it. */
const reledger = (ledger: Decided, pending: string[]) => {
  ed.ledger = ledger; ed.records = pending.map(record);
  ed.trackOpts!.onLedger(ed.ledger);
};

// ── the kernel's /file, /version and /sessions, as the viewer fetches them — with a gate ──────────────
type Served = { bytes: string; type: string; mtimeNs: string };
const disk: Record<string, Served> = {};
const fetches: string[] = [];
/** Holds the NEXT file GET: `headers` keeps the whole response back, `body` lets the headers land and keeps the bytes back. */
let gate: { headers?: Promise<void>; body?: Promise<void> } | null = null;
const deferred = () => { let resolve!: () => void; const p = new Promise<void>((r) => { resolve = r; }); return { p, resolve }; };
(globalThis as any).fetch = async (url: string, init?: { method?: string }) => {
  const method = (init && init.method) || "GET";
  fetches.push(method + " " + url.replace(/[?&]token=[^&]*/, ""));
  if (url.startsWith("/version")) return { json: async () => ({ fileEditing: true }) };
  if (url.startsWith("/sessions")) return { json: async () => [{ id: SID, name: "api", bg: "#123456", fg: "#ffffff" }] };
  const p = decodeURIComponent((/[?&]path=([^&]*)/.exec(url) || [])[1] || "");
  const f = disk[p];                                   // the file as the kernel reads it NOW: headers and bytes agree
  const g = method === "GET" ? gate : null;
  if (g) gate = null;
  if (g && g.headers) await g.headers;
  const headers = { get: (h: string) => (f ? (h === "Content-Type" ? f.type : h === "X-Romp-Mtime-Ns" ? f.mtimeNs : h === "X-Romp-Text-Utf8" ? "1" : null) : null) };
  if (!f) return { ok: false, status: 404, headers, text: async () => { if (g && g.body) await g.body; return "no such file: " + p; } };
  return {
    ok: true, status: 200, headers,
    text: async () => { if (g && g.body) await g.body; return f.bytes; },
    blob: async () => new Blob([f.bytes], { type: f.type }),
  };
};

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ROOT = "/repo/notes-api";
const REPORT = ROOT + "/docs/report.md";
const APP = ROOT + "/src/app.py";
const DOC = "# Report\n\n## Findings\nThe api session cut p95 latency by 40%.\n\nWe recommend shipping the cache in v1.2.\n";
const PY = "def main():\n    return 0\n";
const MT = "1757145600000000001";
const NS = (n: number) => "17571456000000000" + String(n).padStart(2, "0");   // a later mtime, in the fixture's own clock
const T0 = 1757145600000;
const hunk = (id: string): Hunk => ({ id, author: "api", ts: T0, kind: "sub", curFrom: 28, curTo: 31, baseFrom: 28, baseTo: 31, oldText: "p95", newText: "p99", anchor: null });
const record = (id: string) => ({ id, author: "api", authorId: SID, ts: T0, kind: "sub", from: DOC.indexOf("p95"), newText: "p99", oldText: "p95" });
const entry = (id: string): Entry => ({ id, oldText: "p95", newText: "p99" });
function status(hunks: Hunk[], over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: ROOT, storePath: ROOT + "/.trackchanges/docs%2Freport.md.json", trackedBy: { kind: "file", entry: "docs/report.md" },
    agentTooling: "present", fileMtimeNs: MT, storeMtimeNs: NS(2), configMtimeNs: NS(3),
    store: { v: 3, path: "docs/report.md", suggestions: hunks.map((h) => record(h.id)), comments: [] }, hunks,
    unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null }, log: [],
    ...over,
  };
}
const UNTRACKED: Status = { ...status([]), storePath: null, trackedBy: null, store: null, storeMtimeNs: null };
const FILE_MOVED = "the file ~/notes-api/docs/report.md changed on disk since you opened the file — reload and retry";

// ── the probe: an action whose only job is to keep the ctx the viewer hands it ──────────────────────
let seam: FileViewActionCtx | null = null;
const savedInfos: Array<{ mtimeNs: string; logged: boolean }> = [];
const posted: any[] = [];
let fvMod: typeof import("./file-view") | null = null;
async function mod(): Promise<typeof import("./file-view")> {
  if (fvMod) return fvMod;
  fvMod = await import("./file-view");
  fvMod.initFileView((m) => posted.push(m));
  fvMod.registerFileViewAction({
    id: "seam-probe",
    mount(ctx) { seam = ctx; ctx.onSaved((info) => { savedInfos.push(info); }); return null; },
  });
  fvMod.setFileViewIdentity((sid) => (sid === SID ? { name: "api", color: { bg: "#123456", fg: "#ffffff" } } : null));
  return fvMod;
}
const settle = async () => { for (let i = 0; i < 8; i++) await new Promise<void>((r) => setImmediate(r)); };
type Btns = { edit: El; save: El; cancel: El };
type Open = { fv: typeof import("./file-view"); ctx: FileViewActionCtx; wrap: El; body: El; b: Btns };
async function open(p: string, t: TestContext): Promise<Open> {
  const fv = await mod();
  disk[REPORT] = { bytes: DOC, type: "text/plain; charset=utf-8", mtimeNs: MT };
  disk[APP] = { bytes: PY, type: "text/plain; charset=utf-8", mtimeNs: MT };
  posted.length = 0; fetches.length = 0; savedInfos.length = 0; seam = null; gate = null;
  store.delete("romp:fileviewFmt");
  ed.mounted = 0; ed.destroyed = 0; ed.trackOpts = null; ed.records = []; ed.ledger = { accepted: [], rejected: [] };
  assert.equal(fv.openFileView(p, SID), true, "the open happened");
  t.after(() => { fv.closeFileView(); });
  await settle();
  const wrap = doc.getElementById("romp-fileview")!;
  assert.ok(wrap, "the viewer is up");
  const body = wrap.querySelector(".fileview-body")!;
  const acts = wrap.querySelector(".fileview-acts")!;
  const btn = (label: string) => { const b = acts.querySelectorAll("button").find((x) => x.textContent === label); assert.ok(b, "the " + label + " button"); return b!; };
  const b: Btns = { edit: btn("Edit"), save: btn("Save"), cancel: btn("Cancel") };
  assert.ok(seam, "the probe action was mounted with the ctx");
  return { fv, ctx: seam!, wrap, body, b };
}
const lastOf = (type: string, verb?: string) => [...posted].reverse().find((m) => m.type === type && (verb === undefined || m.verb === verb));
const countOf = (type: string, verb?: string) => posted.filter((m) => m.type === type && (verb === undefined || m.verb === verb)).length;
async function answerStatus(s: Status): Promise<void> {
  const m = lastOf("fileComments", "status");
  assert.ok(m, "the panel's status ask is outstanding");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: m.reqId, ...s } }));
  await settle();
}
async function enterEdit(o: Open): Promise<void> {
  o.b.edit.click();
  await settle();
  assert.equal(o.b.save.hidden, false, "edit mode: Save is up");
  assert.ok(o.body.querySelector(".fileview-cm"), "the editor host holds the body");
}
/** Save through the PANEL: the `save` verb goes out; the frame comes back for its args, fence and reqId. */
function saveTracked(o: Open, content: string): any {
  typeInto(content);
  const saves = countOf("saveFile");
  o.b.save.click();
  const m = lastOf("fileComments", "save");
  assert.ok(m, "the save went through the panel");
  assert.equal(countOf("saveFile"), saves, "…and not through saveFile");
  assert.equal(o.b.save.disabled, true); assert.equal(o.b.save.textContent, "Saving…", "acknowledged before the round-trip");
  return m;
}
const saveReply = async (reqId: number, s: Status) => {
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId, ...s, verb: "save", logged: true } }));
  await settle();
};
const saveRefused = async (reqId: number, code: string, error: string) => {
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsFailed", reqId, verb: "save", code, error } }));
  await settle();
};
const errBar = (body: El) => body.querySelector(".fileview-err");
const fileGets = () => fetches.filter((f) => f.startsWith("GET /file")).length;
/** Save with NO keystroke (the buffer as it stands): the `save` verb goes out; the frame comes back. */
function saveAsIs(o: Open): any {
  const saves = countOf("saveFile");
  o.b.save.click();
  const m = lastOf("fileComments", "save");
  assert.ok(m, "the save went through the panel");
  assert.equal(countOf("saveFile"), saves, "…and not through saveFile");
  assert.equal(o.b.save.disabled, true); assert.equal(o.b.save.textContent, "Saving…");
  return m;
}
/** Save clicked and refused in the viewer: nothing posted, edit mode and the buffer kept, the button armed, the bar says why. */
async function saveRefusedInPlace(o: Open, why: RegExp): Promise<void> {
  const saves = countOf("fileComments", "save"), plain = countOf("saveFile"), destroyed = ed.destroyed;
  o.b.save.click();
  await settle();
  assert.equal(countOf("fileComments", "save"), saves, "no save went out");
  assert.equal(countOf("saveFile"), plain, "…through either door");
  assert.equal(o.ctx.editing(), true, "edit mode stays"); assert.equal(ed.destroyed, destroyed, "the buffer stays");
  assert.equal(o.b.save.disabled, false); assert.equal(o.b.save.textContent, "Save", "Save is armed");
  assert.match(errBar(o.body)!.textContent, why);
}
const ACK_UNDONE = /^Saved, but the accept you undid had already landed with this save and cannot be taken back: redo it \(Ctrl\/Cmd\+Shift\+Z\), reject the change here instead, or Cancel to see the file as it was saved\.$/;
const SAVE_UNDONE = /^Not saved: the accept you undid had already landed with an earlier save and cannot be taken back\. Redo it \(Ctrl\/Cmd\+Shift\+Z\), reject the change here instead, or Cancel to see the file as it was saved\.$/;

// ── 1. undo against a landed save ───────────────────────────────────────────────────────────────────

test("an accept undone during the round-trip is not dropped with the editor: the ack stays in edit mode and says the accept already landed; Save refuses while it stands; redo makes Save a clean exit", async (t) => {
  const o = await open(REPORT, t);
  const { ctx, body, b } = o;
  await answerStatus(status([hunk("h1"), hunk("h2")]));
  await enterEdit(o);
  decideInEditor("accepted", "h1");
  const m1 = saveAsIs(o);                              // no keystroke: the save carries the accept alone
  assert.deepEqual(m1.args, { content: DOC, suggestions: [record("h2")], accepted: [entry("h1")], rejected: [] });
  reledger({ accepted: [], rejected: [] }, ["h1", "h2"]);   // Ctrl-Z before the ack: h1 is pending in the field again
  await saveReply(m1.reqId, status([hunk("h2")], { fileMtimeNs: NS(9), storeMtimeNs: NS(10) }));
  assert.equal(ctx.editing(), true, "the ack keeps the editor: leaving would drop the undo without a word");
  assert.equal(ed.destroyed, 0);
  assert.equal(b.save.disabled, false); assert.equal(b.save.textContent, "Save", "re-armed");
  assert.equal(ctx.mtimeNs(), NS(9), "the save landed all the same");
  assert.match(errBar(body)!.textContent, ACK_UNDONE, "the bar says the accept stands on disk and names the ways out");
  // Save while the undone accept still stands: refused in place, nothing sent (the host has no verb that takes it back)
  await saveRefusedInPlace(o, SAVE_UNDONE);
  // redo (the chunk's ledger holds h1 again, its field does not): the editor agrees with the disk, and Save leaves
  reledger({ accepted: [entry("h1")], rejected: [] }, ["h2"]);
  const saves = countOf("fileComments", "save");
  b.save.click();
  await settle();
  assert.equal(countOf("fileComments", "save"), saves, "nothing to save: the accept landed with the first save");
  assert.equal(ctx.editing(), false, "leaving is the honest ack");
  assert.equal(ed.destroyed, 1);
  assert.equal(ctx.text(), DOC);
});

test("the undone accept turned into a reject after the ack: the reversal goes out alone (the log will read accept, reject), never the restored record", async (t) => {
  const o = await open(REPORT, t);
  await answerStatus(status([hunk("h1"), hunk("h2")]));
  await enterEdit(o);
  decideInEditor("accepted", "h1");
  const m1 = saveAsIs(o);
  reledger({ accepted: [], rejected: [] }, ["h1", "h2"]);
  await saveReply(m1.reqId, status([hunk("h2")], { fileMtimeNs: NS(9), storeMtimeNs: NS(10) }));
  assert.equal(o.ctx.editing(), true);
  reledger({ accepted: [], rejected: [entry("h1")] }, ["h2"]);   // modifier-click: h1 leaves the field for the rejected side
  typeInto(DOC.replace("p95", "p90"));                 // …and a reject moves text
  const m2 = saveAsIs(o);
  assert.deepEqual(m2.args, { content: DOC.replace("p95", "p90"), suggestions: [record("h2")], accepted: [], rejected: [entry("h1")] });
});

test("typing undone by hand and the accept undone after it: the buffer is the saved bytes, yet Save must not exit as 'nothing changed' over an undone landed accept", async (t) => {
  const o = await open(REPORT, t);
  await answerStatus(status([hunk("h1")]));
  await enterEdit(o);
  decideInEditor("accepted", "h1");
  const m1 = saveAsIs(o);
  typeInto(DOC + "q");                                 // typed during the round-trip: the ack keeps the editor
  await saveReply(m1.reqId, status([], { fileMtimeNs: NS(9), storeMtimeNs: NS(10) }));
  assert.equal(o.ctx.editing(), true);
  assert.equal(errBar(o.body), null, "nothing undone yet: no bar");
  typeInto(DOC);                                       // Ctrl-Z: the keystroke goes…
  reledger({ accepted: [], rejected: [] }, ["h1"]);    // …and Ctrl-Z again: the accept goes, h1 is back in the field
  await saveRefusedInPlace(o, SAVE_UNDONE);            // before: dirty read false and Save exited, the undo lost silently
  assert.equal(o.ctx.text(), DOC, "text() is still the buffer");
});

test("undo past a landed save with a sidecar left (two changes): Save refuses instead of sending the restored record as pending; after redo the next Save sends the text with the decision not re-sent", async (t) => {
  const o = await open(REPORT, t);
  const { ctx, b } = o;
  await answerStatus(status([hunk("h1"), hunk("h2")]));
  await enterEdit(o);
  decideInEditor("accepted", "h1");
  const m1 = saveTracked(o, DOC + "one\n");
  assert.deepEqual(m1.args, { content: DOC + "one\n", suggestions: [record("h2")], accepted: [entry("h1")], rejected: [] });
  typeInto(DOC + "one\ntwo");                          // typed during the round-trip
  await saveReply(m1.reqId, status([hunk("h2")], { fileMtimeNs: NS(9), storeMtimeNs: NS(10) }));
  assert.equal(ctx.editing(), true);
  assert.equal(errBar(o.body), null, "the ack shows no bar: nothing undone at that point");
  // Ctrl-Z past the typing and the accept: h1 is back in the field with h2, the ledger is empty
  typeInto(DOC);
  reledger({ accepted: [], rejected: [] }, ["h1", "h2"]);
  await saveRefusedInPlace(o, SAVE_UNDONE);            // before: suggestions [h1, h2], accepted [] went out and the host re-pended h1
  // redo the accept: the field holds h2 alone again, and the text change is what the next Save carries
  reledger({ accepted: [entry("h1")], rejected: [] }, ["h2"]);
  b.save.click();
  const m2 = lastOf("fileComments", "save");
  assert.notEqual(m2.reqId, m1.reqId, "a second save went out");
  assert.deepEqual(m2.args, { content: DOC, suggestions: [record("h2")], accepted: [], rejected: [] }, "h1 landed with the first save: not sent again");
  assert.deepEqual(m2.fence, { storeMtimeNs: NS(10), configMtimeNs: NS(3), fileMtimeNs: NS(9) });
});

test("undo past a landed save that pruned the sidecar (the only change accepted): Save refuses in place rather than sending suggestions under an empty store fence", async (t) => {
  const o = await open(REPORT, t);
  await answerStatus(status([hunk("h1")]));
  await enterEdit(o);
  decideInEditor("accepted", "h1");
  const m1 = saveTracked(o, DOC + "one\n");
  assert.deepEqual(m1.args, { content: DOC + "one\n", suggestions: [], accepted: [entry("h1")], rejected: [] });
  typeInto(DOC + "one\ntwo");
  // the reply: no sidecar any more (the save pruned it), the file still tracked
  await saveReply(m1.reqId, status([], { fileMtimeNs: NS(9), storeMtimeNs: null, store: null }));
  assert.equal(o.ctx.editing(), true);
  typeInto(DOC);
  reledger({ accepted: [], rejected: [] }, ["h1"]);
  await saveRefusedInPlace(o, SAVE_UNDONE);            // before: the host answered BadRequest, a programmer-facing error
  // Cancel is one of the named ways out: the view shows the file as it was saved
  o.b.cancel.click();
  await settle();
  assert.equal(o.ctx.editing(), false);
  assert.equal(o.ctx.text(), DOC + "one\n"); assert.equal(o.ctx.mtimeNs(), NS(9));
});

test("several decisions undone past a save: the bar counts them and offers deciding them again", async (t) => {
  const o = await open(REPORT, t);
  await answerStatus(status([hunk("h1"), hunk("h2"), hunk("h3")]));
  await enterEdit(o);
  decideInEditor("accepted", "h1");
  decideInEditor("rejected", "h2");
  const m1 = saveTracked(o, DOC + "one\n");
  assert.deepEqual([m1.args.accepted, m1.args.rejected], [[entry("h1")], [entry("h2")]]);
  reledger({ accepted: [], rejected: [] }, ["h1", "h2", "h3"]);   // both undone before the ack
  await saveReply(m1.reqId, status([hunk("h3")], { fileMtimeNs: NS(9), storeMtimeNs: NS(10) }));
  assert.equal(o.ctx.editing(), true);
  assert.match(errBar(o.body)!.textContent, /^Saved, but the 2 decisions you undid had already landed with this save and cannot be taken back: redo them \(Ctrl\/Cmd\+Shift\+Z\), decide the changes again here, or Cancel to see the file as it was saved\.$/);
  // one redone, one still undone: the bar names the one
  reledger({ accepted: [entry("h1")], rejected: [] }, ["h2", "h3"]);
  await saveRefusedInPlace(o, /^Not saved: the reject you undid had already landed with an earlier save and cannot be taken back\. Redo it \(Ctrl\/Cmd\+Shift\+Z\), accept the change here instead, or Cancel to see the file as it was saved\.$/);
});

// ── 2. Cancel during a save through the panel ───────────────────────────────────────────────────────

test("Cancel confirmed while a tracked save is in flight: the late ack re-reads the file, so the view shows the saved bytes and mtime without waiting for a poll that would never notice", async (t) => {
  const o = await open(REPORT, t);
  const { ctx, b } = o;
  await answerStatus(status([]));                      // tracked, nothing pending: Save routes through the panel
  await enterEdit(o);
  const m = saveTracked(o, DOC + "x");
  b.cancel.click();                                    // confirm says yes: edit mode ends while the host is writing
  await settle();
  assert.equal(ctx.editing(), false);
  assert.equal(ctx.text(), DOC, "the view shows the bytes from before the save…"); assert.equal(ctx.mtimeNs(), MT);
  const gets = fileGets(), asks = countOf("fileComments", "status");
  disk[REPORT] = { bytes: DOC + "x", type: "text/plain; charset=utf-8", mtimeNs: NS(9) };   // …which the host has written
  await saveReply(m.reqId, status([], { fileMtimeNs: NS(9) }));
  assert.equal(fileGets(), gets + 1, "one re-read, at the ack");
  assert.equal(ctx.text(), DOC + "x", "the view shows the file as saved"); assert.equal(ctx.mtimeNs(), NS(9));
  assert.deepEqual(savedInfos.map((i) => i.mtimeNs), [NS(9)], "the seam's onSaved still fires: the panel's bookkeeping completes");
  assert.equal(countOf("fileComments", "status"), asks, "and the panel asks nothing more: the reply was its status");
  assert.equal(b.save.hidden, true); assert.equal(b.save.disabled, false); assert.equal(b.save.textContent, "Save");
});

test("Cancel during the save, then Edit again before the ack: the new editor keeps its bytes, and the exit re-reads", async (t) => {
  const o = await open(REPORT, t);
  const { ctx, b } = o;
  await answerStatus(status([]));
  await enterEdit(o);
  const m = saveTracked(o, DOC + "x");
  b.cancel.click();
  await settle();
  await enterEdit(o);                                  // a second editor, over the pre-save bytes
  assert.equal(ed.buf, DOC);
  const gets = fileGets();
  disk[REPORT] = { bytes: DOC + "x", type: "text/plain; charset=utf-8", mtimeNs: NS(9) };
  await saveReply(m.reqId, status([], { fileMtimeNs: NS(9) }));
  assert.equal(ctx.editing(), true, "the late ack touches no editor");
  assert.equal(fileGets(), gets, "no read while the editor holds the truth");
  assert.equal(ctx.text(), DOC, "text() is the buffer"); assert.equal(ctx.mtimeNs(), MT, "the fence is the file this editor loaded");
  b.cancel.click();
  await settle();
  assert.equal(fileGets(), gets + 1, "the exit is the event the owed read waited for");
  assert.equal(ctx.text(), DOC + "x"); assert.equal(ctx.mtimeNs(), NS(9));
});

test("a refusal landing after Cancel changes nothing: nothing was written, so there is nothing to re-read", async (t) => {
  const o = await open(REPORT, t);
  await answerStatus(status([]));
  await enterEdit(o);
  const m = saveTracked(o, DOC + "x");
  o.b.cancel.click();
  await settle();
  const gets = fileGets();
  await saveRefused(m.reqId, "file-moved", FILE_MOVED);
  assert.equal(fileGets(), gets);
  assert.equal(o.ctx.text(), DOC); assert.equal(o.ctx.mtimeNs(), MT);
  assert.equal(errBar(o.body), null, "no bar over a view whose edit was cancelled");
});

test("the viewer closed before the ack: the late ack touches nothing", async (t) => {
  const o = await open(REPORT, t);
  await answerStatus(status([]));
  await enterEdit(o);
  const m = saveTracked(o, DOC + "x");
  o.b.cancel.click();
  await settle();
  o.fv.closeFileView();
  assert.equal(doc.getElementById("romp-fileview"), null);
  const gets = fileGets();
  disk[REPORT] = { bytes: DOC + "x", type: "text/plain; charset=utf-8", mtimeNs: NS(9) };
  await saveReply(m.reqId, status([], { fileMtimeNs: NS(9) }));
  assert.equal(fileGets(), gets, "no read for a viewer that is gone");
  assert.deepEqual(savedInfos, []);
});
