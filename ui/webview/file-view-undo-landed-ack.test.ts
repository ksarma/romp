// The ack-time note for a decision undone during the save round-trip, at the REAL openFileView (plans/file-review.md
// Slice 5; the review of that slice's fixes, the undone-during-round-trip finding, both of its cases):
//
// hooks.saved used to check in-flight typing first and the undone landed decision second. An undone ACCEPT with no
// keystroke moves no text, so the second check caught it and the bar said the accept had landed. But when the buffer
// had moved as well — the save carried typing the undo took back too, or the undone decision was a REJECT, which moves
// text — the first check kept the editor and returned, and the person heard of the landed decision only when the next
// Save refused. The order is now: the undone decision first (the ack is the moment the undo became irreversible, and the
// bar says so whatever else the buffer holds), then in-flight typing, then a decision clicked during the round-trip.
// The bar also carries the comments-log warning when the same ack brought one, instead of replacing it.
//
// The DOM stand-in, the editor-chunk stub and the kernel stubs are the ones file-view-undo-landed.test.ts carries
// (copied: that file exports nothing, and node:test runs each bundled file in its own process). Synthetic fixtures
// only: the notes-api world, placeholder ids.
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

// ── the editor chunk: a buffer, the two callbacks, and the track option's handle (records + decisions with no reset) ──
type Entry = { id: string; oldText: string; newText: string };
type Decided = { accepted: Entry[]; rejected: Entry[] };
type TrackStub = { suggestions: unknown[]; authorColor: (a: string) => string | null; onDecisions: (l: Decided) => void };
const ed = {
  buf: "", onChange: null as (() => void) | null, mounted: 0, destroyed: 0,
  trackOpts: null as TrackStub | null, records: [] as unknown[], decisions: { accepted: [], rejected: [] } as Decided,
};
win.__rompEditor = {
  mount(host: El, opts: { text: string; onChange: () => void; onSave: () => void; track?: TrackStub }) {
    ed.buf = opts.text; ed.onChange = opts.onChange; ed.mounted++; ed.trackOpts = opts.track || null;
    host.appendChild(new Txt(opts.text));
    const h: { value(): string; focus(): void; destroy(): void; track?: { suggestions(): unknown[]; decisions(): Decided } } =
      { value: () => ed.buf, focus() { /* inert */ }, destroy() { ed.destroyed++; } };
    if (opts.track) {
      ed.records = opts.track.suggestions.slice(); ed.decisions = { accepted: [], rejected: [] };
      h.track = { suggestions: () => ed.records, decisions: () => ed.decisions };
    }
    return h;
  },
};
const typeInto = (s: string) => { ed.buf = s; ed.onChange!(); };
/** An in-editor decision: the chunk drops the record from its field and reports the decisions (no text change on an accept). */
const decideInEditor = (side: "accepted" | "rejected", id: string) => {
  ed.records = ed.records.filter((r) => (r as { id: string }).id !== id);
  ed.decisions = { ...ed.decisions, [side]: [...ed.decisions[side], entry(id)] };
  ed.trackOpts!.onDecisions(ed.decisions);
};
/** The chunk's decisions after an undo or a redo: what the field now holds, reported as the real chunk reports it. */
const redecide = (decisions: Decided, pending: string[]) => {
  ed.decisions = decisions; ed.records = pending.map(record);
  ed.trackOpts!.onDecisions(ed.decisions);
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
  ed.mounted = 0; ed.destroyed = 0; ed.trackOpts = null; ed.records = []; ed.decisions = { accepted: [], rejected: [] };
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

/** Save through the panel whose reply ALSO carries the host's comments-log account (file-view-tracked-edit.test.ts's shape). */
const saveReplyLogged = async (reqId: number, s: Status, log: { logged: boolean; logWarning?: string }) => {
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId, ...s, verb: "save", ...log } }));
  await settle();
};
const WARN = "the comments log for docs/report.md was not updated: the append failed";
const ACK_UNDONE_REJECT = /^Saved, but the reject you undid had already landed with this save and cannot be taken back: redo it \(Ctrl\/Cmd\+Shift\+Z\), accept the change here instead, or Cancel to see the file as it was saved\.$/;
const SAVE_UNDONE_REJECT = /^Not saved: the reject you undid had already landed with an earlier save and cannot be taken back\. Redo it \(Ctrl\/Cmd\+Shift\+Z\), accept the change here instead, or Cancel to see the file as it was saved\.$/;

// ── the ack over a moved buffer ─────────────────────────────────────────────────────────────────────

test("an accept undone during the round-trip of a save that also carried typing, the typing undone with it: the ack says the accept already landed instead of keeping the editor over the moved buffer in silence", async (t) => {
  const o = await open(REPORT, t);
  const { ctx, body, b } = o;
  await answerStatus(status([hunk("h1"), hunk("h2")]));
  await enterEdit(o);
  decideInEditor("accepted", "h1");                    // the accept first…
  const m1 = saveTracked(o, DOC + "q");                // …then a keystroke, and the save carries both
  assert.deepEqual(m1.args, { content: DOC + "q", suggestions: [record("h2")], accepted: [entry("h1")], rejected: [] });
  typeInto(DOC);                                       // Ctrl-Z before the ack: the keystroke goes…
  redecide({ accepted: [], rejected: [] }, ["h1", "h2"]);   // …and Ctrl-Z again: the accept goes, h1 is pending in the field
  await saveReply(m1.reqId, status([hunk("h2")], { fileMtimeNs: NS(9), storeMtimeNs: NS(10) }));
  assert.equal(ctx.editing(), true, "the ack keeps the editor");
  assert.equal(ed.destroyed, 0);
  assert.equal(b.save.disabled, false); assert.equal(b.save.textContent, "Save", "re-armed");
  assert.equal(ctx.mtimeNs(), NS(9), "the save landed all the same");
  assert.equal(ctx.text(), DOC, "text() is the buffer the undo left");
  assert.match(errBar(body)!.textContent, ACK_UNDONE, "the bar says so at the ack: before, the moved buffer kept the editor with no word until the next Save");
  await saveRefusedInPlace(o, SAVE_UNDONE);
  // redo the accept alone: the field holds h2, and the buffer still lacks the keystroke the save carried — a text change
  redecide({ accepted: [entry("h1")], rejected: [] }, ["h2"]);
  const m2 = saveAsIs(o);
  assert.notEqual(m2.reqId, m1.reqId, "a second save went out");
  assert.deepEqual(m2.args, { content: DOC, suggestions: [record("h2")], accepted: [], rejected: [] }, "the text as it stands; h1 landed with the first save and is not sent again");
});

test("the keystroke alone undone during the round-trip, the accept kept: the ack stays for the moved buffer and raises no bar", async (t) => {
  const o = await open(REPORT, t);
  const { ctx, body, b } = o;
  await answerStatus(status([hunk("h1"), hunk("h2")]));
  await enterEdit(o);
  decideInEditor("accepted", "h1");
  const m1 = saveTracked(o, DOC + "q");
  typeInto(DOC);                                       // Ctrl-Z once: the keystroke goes, the accept stands
  await saveReply(m1.reqId, status([hunk("h2")], { fileMtimeNs: NS(9), storeMtimeNs: NS(10) }));
  assert.equal(ctx.editing(), true, "in-flight typing keeps the editor");
  assert.equal(errBar(body), null, "nothing decided was undone: no bar");
  assert.equal(b.save.disabled, false); assert.equal(b.save.textContent, "Save");
  const m2 = saveAsIs(o);
  assert.notEqual(m2.reqId, m1.reqId);
  assert.deepEqual(m2.args, { content: DOC, suggestions: [record("h2")], accepted: [], rejected: [] }, "the accept landed with the first save and is not sent again");
});

test("a reject undone during the round-trip: the undo moves text, so the editor stayed before as well; now the ack says the reject already landed, and Save refuses until redo, an accept, or Cancel", async (t) => {
  const o = await open(REPORT, t);
  const { ctx, body, b } = o;
  await answerStatus(status([hunk("h1"), hunk("h2")]));
  await enterEdit(o);
  decideInEditor("rejected", "h1");
  typeInto(DOC.replace("p95", "p90"));                 // a reject moves text (the stub models the buffer by hand)
  const m1 = saveAsIs(o);
  assert.deepEqual(m1.args, { content: DOC.replace("p95", "p90"), suggestions: [record("h2")], accepted: [], rejected: [entry("h1")] });
  typeInto(DOC);                                       // Ctrl-Z before the ack: the text comes back…
  redecide({ accepted: [], rejected: [] }, ["h1", "h2"]);   // …with h1 pending in the field
  await saveReply(m1.reqId, status([hunk("h2")], { fileMtimeNs: NS(9), storeMtimeNs: NS(10) }));
  assert.equal(ctx.editing(), true);
  assert.equal(ed.destroyed, 0);
  assert.equal(b.save.disabled, false); assert.equal(b.save.textContent, "Save");
  assert.equal(ctx.mtimeNs(), NS(9));
  assert.match(errBar(body)!.textContent, ACK_UNDONE_REJECT, "the reject's wording: redo, or accept the change here instead");
  await saveRefusedInPlace(o, SAVE_UNDONE_REJECT);
  // accept it here instead: the reversal goes out alone (the log will read reject, accept), the record never as pending
  redecide({ accepted: [entry("h1")], rejected: [] }, ["h2"]);
  const m2 = saveAsIs(o);
  assert.notEqual(m2.reqId, m1.reqId);
  assert.deepEqual(m2.args, { content: DOC, suggestions: [record("h2")], accepted: [entry("h1")], rejected: [] });
});

test("the undone-landed note and a comments-log warning on the same ack share the bar: neither takes the other down", async (t) => {
  const o = await open(REPORT, t);
  const { ctx, body } = o;
  await answerStatus(status([hunk("h1"), hunk("h2")]));
  await enterEdit(o);
  decideInEditor("accepted", "h1");
  const m1 = saveAsIs(o);
  redecide({ accepted: [], rejected: [] }, ["h1", "h2"]);
  await saveReplyLogged(m1.reqId, status([hunk("h2")], { fileMtimeNs: NS(9), storeMtimeNs: NS(10) }), { logged: false, logWarning: WARN });
  assert.equal(ctx.editing(), true);
  const bars = body.querySelectorAll(".fileview-err");
  assert.equal(bars.length, 1, "one bar");
  assert.match(bars[0].textContent, /^Saved, but the accept you undid had already landed with this save and cannot be taken back: /);
  assert.ok(bars[0].textContent.endsWith(" Also: " + WARN), "…and the host's words follow in the same bar: " + bars[0].textContent);
  assert.deepEqual(savedInfos, [{ mtimeNs: NS(9), logged: false }], "onSaved heard the failed append");
});
