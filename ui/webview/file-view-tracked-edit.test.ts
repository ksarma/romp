// The tracked-edit path's two guards at the REAL openFileView (plans/file-review.md Slice 5; the review of that slice):
//
// 1. Edit asks the panel what is pending twice: at the click, where a refusal needs no consent popup first, and again
//    at the mount, after the consent read (`ensureEditingAllowed`, a kernel round-trip) — the mount takes the second
//    answer, since the panel's status is the truth and it fences the save on the sidecar as it stands then. The CRLF
//    and older-bundle guards used to run at the click only, so a status landing inside the round-trip (the panel's
//    mount-time ask answered late, the poll's tick, a session's write) turned a click-time "nothing pending" into
//    records mounted over the LF-normalized buffer with their CRLF-disk offsets: marks on the wrong text, a reject
//    rewriting the wrong span, a deletion fitted at a shifted offset. Both guards now run over the begin() the editor
//    mounts, before edit mode is entered.
// 2. A save through the host that landed with a failed comments-log append answers `logged: false` and the host's
//    `logWarning`. The saveFile path put that text in the note bar; the tracked path dropped it, and the panel's head —
//    the other place it is said — is painted only while the aside is open, which a tracked file's edit never needs
//    (the panel's status lands at mount, so Save routes through the host with the aside closed). The tracked ack now
//    reads the warning into the save's hooks before `saved` runs, as the fileSaved branch does.
//
// The DOM stand-in, the editor-chunk stub and the kernel stubs are the ones file-view-edit-races.test.ts carries
// (node:test runs each bundled file in its own process and that file exports nothing), with two additions: a gate that
// holds the /version consent read until a test releases it, and a chunk stub that can ignore the track option (an older
// bundle). Synthetic fixtures only: the notes-api world, placeholder ids.
import { test, type TestContext } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as nodePath from "node:path";
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


// ── the editor chunk: a buffer, the two callbacks, and the track option's handle — or none, for an older bundle ──
type Entry = { id: string; oldText: string; newText: string };
type Decided = { accepted: Entry[]; rejected: Entry[] };
type TrackStub = { suggestions: unknown[]; authorColor: (a: string) => string | null; onDecisions: (l: Decided) => void };
const ed = {
  buf: "", onChange: null as (() => void) | null, mounted: 0, destroyed: 0,
  tracks: true,                                        // false: the bundle predates the option and returns a handle without `track`
  trackOpts: null as TrackStub | null, records: [] as unknown[], decisions: { accepted: [], rejected: [] } as Decided,
};
win.__rompEditor = {
  mount(host: El, opts: { text: string; onChange: () => void; onSave: () => void; track?: TrackStub }) {
    ed.buf = opts.text; ed.onChange = opts.onChange; ed.mounted++; ed.trackOpts = opts.track || null;
    host.appendChild(new Txt(opts.text));
    const h: { value(): string; focus(): void; destroy(): void; track?: { suggestions(): unknown[]; decisions(): Decided } } =
      { value: () => ed.buf, focus() { /* inert */ }, destroy() { ed.destroyed++; } };
    if (opts.track && ed.tracks) {
      ed.records = opts.track.suggestions.slice(); ed.decisions = { accepted: [], rejected: [] };
      h.track = { suggestions: () => ed.records, decisions: () => ed.decisions };
    }
    return h;
  },
};
const typeInto = (s: string) => { ed.buf = s; ed.onChange!(); };

// ── the kernel's /file, /version and /sessions, as the viewer fetches them — /version behind a gate ──
type Served = { bytes: string; type: string; mtimeNs: string };
const disk: Record<string, Served> = {};
const fetches: string[] = [];
/** While set, every /version read (the consent gate's) waits on it: the click's continuation is parked. */
let versionGate: Promise<void> | null = null;
const holdVersion = () => {
  let resolve!: () => void;
  versionGate = new Promise<void>((r) => { resolve = r; });
  return { release: () => { versionGate = null; resolve(); } };
};
(globalThis as any).fetch = async (url: string, init?: { method?: string }) => {
  const method = (init && init.method) || "GET";
  fetches.push(method + " " + url.replace(/[?&]token=[^&]*/, ""));
  if (url.startsWith("/version")) { if (versionGate) await versionGate; return { json: async () => ({ fileEditing: true }) }; }
  if (url.startsWith("/sessions")) return { json: async () => [{ id: SID, name: "api", bg: "#123456", fg: "#ffffff" }] };
  const p = decodeURIComponent((/[?&]path=([^&]*)/.exec(url) || [])[1] || "");
  const f = disk[p];
  const headers = { get: (h: string) => (f ? (h === "Content-Type" ? f.type : h === "X-Romp-Mtime-Ns" ? f.mtimeNs : h === "X-Romp-Text-Utf8" ? "1" : null) : null) };
  if (!f) return { ok: false, status: 404, headers, text: async () => "no such file: " + p };
  return { ok: true, status: 200, headers, text: async () => f.bytes, blob: async () => new Blob([f.bytes], { type: f.type }) };
};

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ROOT = "/repo/notes-api";
const REPORT = ROOT + "/docs/report.md";
const DOC = "# Report\n\n## Findings\nThe api session cut p95 latency by 40%.\n\nWe recommend shipping the cache in v1.2.\n";
const CRLF_DOC = DOC.replace(/\n/g, "\r\n");
const MT = "1757145600000000001";
const NS = (n: number) => "17571456000000000" + String(n).padStart(2, "0");   // a later mtime, in the fixture's own clock
const T0 = 1757145600000;
const hunk = (id: string): Hunk => ({ id, author: "api", ts: T0, kind: "sub", curFrom: 28, curTo: 31, baseFrom: 28, baseTo: 31, oldText: "p95", newText: "p99", anchor: null });
const record = (id: string) => ({ id, author: "api", authorId: SID, ts: T0, kind: "sub", from: DOC.indexOf("p95"), newText: "p99", oldText: "p95" });
function status(hunks: Hunk[], over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: ROOT, storePath: ROOT + "/.trackchanges/docs%2Freport.md.json", trackedBy: { kind: "file", entry: "docs/report.md" },
    agentTooling: "present", fileMtimeNs: MT, storeMtimeNs: NS(2), configMtimeNs: NS(3),
    store: { v: 3, path: "docs/report.md", suggestions: hunks.map((h) => record(h.id)), comments: [] }, hunks,
    unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null }, log: [],
    ...over,
  };
}
// the host's words for an append that failed on a save that landed (tools/file-comments-host.mjs, the save verb's `landed`)
const WARN = "saved, but the edit was not written to the comments log (the log file is not writable) — the Log will not show this edit";
const CRLF_WORDS = /^The editor rewrites this file's CRLF line endings as it loads the text, and that would move the pending changes\. /;

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
type Btns = { edit: El; save: El; cancel: El; comments: El };
type Open = { fv: typeof import("./file-view"); ctx: FileViewActionCtx; wrap: El; body: El; b: Btns };
/** Opens REPORT as the kernel serves `bytes` (DOC by default); the panel's mount-time status ask is left OUTSTANDING. */
async function open(t: TestContext, bytes = DOC): Promise<Open> {
  const fv = await mod();
  disk[REPORT] = { bytes, type: "text/plain; charset=utf-8", mtimeNs: MT };
  posted.length = 0; fetches.length = 0; savedInfos.length = 0; seam = null; versionGate = null;
  store.delete("romp:fileviewFmt");
  ed.mounted = 0; ed.destroyed = 0; ed.tracks = true; ed.trackOpts = null; ed.records = []; ed.decisions = { accepted: [], rejected: [] };
  assert.equal(fv.openFileView(REPORT, SID), true, "the open happened");
  t.after(() => { fv.closeFileView(); });
  await settle();
  const wrap = doc.getElementById("romp-fileview")!;
  assert.ok(wrap, "the viewer is up");
  const body = wrap.querySelector(".fileview-body")!;
  const acts = wrap.querySelector(".fileview-acts")!;
  const btn = (label: string) => { const b = acts.querySelectorAll("button").find((x) => x.textContent === label); assert.ok(b, "the " + label + " button"); return b!; };
  const comments = acts.querySelector(".fileview-fc button")!;
  assert.ok(comments, "the Comments button");
  const b: Btns = { edit: btn("Edit"), save: btn("Save"), cancel: btn("Cancel"), comments };
  assert.ok(seam, "the probe action was mounted with the ctx");
  return { fv, ctx: seam!, wrap, body, b };
}
const lastOf = (type: string, verb?: string) => [...posted].reverse().find((m) => m.type === type && (verb === undefined || m.verb === verb));
const countOf = (type: string, verb?: string) => posted.filter((m) => m.type === type && (verb === undefined || m.verb === verb)).length;
/** Answers the panel's NEWEST status ask — which must be outstanding, or the reply lands nowhere (Panel.settle). */
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
/** The host's reply to a save that landed: the status it now holds, plus `logged` and, when the append failed, its words. */
const saveReply = async (reqId: number, s: Status, log: { logged: boolean; logWarning?: string } = { logged: true }) => {
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId, ...s, verb: "save", ...log } }));
  await settle();
};
const errBar = (body: El) => body.querySelector(".fileview-err");
const versionReads = () => fetches.filter((f) => f === "GET /version").length;
const asideOpen = (wrap: El) => wrap.querySelector(".fc-panel") !== null;

// ── 1. the guards run over the begin() the editor mounts ────────────────────────────────────────────

test("CRLF: pending changes that land during the consent read are refused at the mount, in the click's words — no editor over the normalized buffer", async (t) => {
  const o = await open(t, CRLF_DOC);
  const { ctx, body, b } = o;
  // the panel's mount-time status ask is still out at the click: it knows of nothing pending, so the click's guards pass
  assert.ok(lastOf("fileComments", "status"), "the panel asked status at mount");
  const hold = holdVersion();
  b.edit.click();
  await settle();
  assert.equal(errBar(body), null, "nothing refused at the click");
  assert.equal(versionReads(), 1, "the consent read is out…");
  assert.equal(ed.mounted, 0, "…and nothing has mounted");
  await answerStatus(status([hunk("h1")]));            // one change lands inside the round-trip
  hold.release();
  await settle();
  assert.equal(ed.mounted, 0, "no mount: the record's offsets are into the CRLF disk text, the buffer would be LF");
  assert.equal(ctx.editing(), false, "edit mode was never entered");
  assert.equal(b.save.hidden, true); assert.equal(b.edit.hidden, false);
  assert.match(errBar(body)!.textContent, CRLF_WORDS, "the consequence, stated as the click states it");
  assert.match(errBar(body)!.textContent, /1 change is pending in this file, so Edit is off here/, "…with the panel's refusal");
  assert.doesNotMatch(errBar(body)!.textContent, /\bride/, "no metaphor in the refusal");
  assert.ok(body.childNodes.length > 1 && body.childNodes[0] === errBar(body), "above the read view, which stands");
  assert.equal(ctx.mode(), "rendered", "a refused Edit leaves the Rendered view it was clicked from: no Raw choice saved and unpainted");
});

test("the same race over LF endings mounts what landed: the editor carries the records the panel holds at the mount, not the click's empty answer", async (t) => {
  const o = await open(t);
  const { ctx, body, b } = o;
  const hold = holdVersion();
  b.edit.click();
  await settle();
  assert.equal(ed.mounted, 0);
  await answerStatus(status([hunk("h1")]));
  hold.release();
  await settle();
  assert.equal(ed.mounted, 1, "mounted");
  assert.equal(ctx.editing(), true);
  assert.deepEqual(ed.trackOpts!.suggestions, [record("h1")], "with the change that landed during the consent read as a mark");
  assert.equal(errBar(body), null);
  assert.equal(ctx.mode(), "raw", "markdown edits from its Raw view");
});

test("an editor bundle that ignored the track option once: pending changes landing during the consent read are refused at the mount in the panel's words, with no second mount", async (t) => {
  const o = await open(t);
  const { ctx, body, b } = o;
  await answerStatus(status([hunk("h1")]));
  ed.tracks = false;                                   // the bundle predates the option
  b.edit.click();
  await settle();
  assert.equal(ed.mounted, 1, "the first tracked mount was tried…");
  assert.equal(ctx.editing(), false, "…and the handle without `track` ended it");
  assert.match(errBar(body)!.textContent, /^1 change is pending in this file, so Edit is off here/);
  // the aside opens (its refresh asks status) and nothing pending lands; closed and opened again, a fresh ask is out
  b.comments.click(); await settle();
  await answerStatus(status([]));
  b.comments.click(); await settle();
  b.comments.click(); await settle();
  assert.ok(asideOpen(o.wrap));
  const hold = holdVersion();
  b.edit.click();
  await settle();
  assert.equal(ed.mounted, 1, "the click passed: the panel knew of nothing pending");
  assert.equal(versionReads(), 2, "the consent read is out");
  await answerStatus(status([hunk("h1"), hunk("h2")]));   // two changes land inside the round-trip
  hold.release();
  await settle();
  assert.equal(ed.mounted, 1, "no mount over records the bundle would drop");
  assert.equal(ctx.editing(), false);
  assert.match(errBar(body)!.textContent, /^2 changes are pending in this file, so Edit is off here/, "the panel's words for what landed");
});

test("the click's guard still comes first: a CRLF file whose pending change is known at the click is refused before the consent read", async (t) => {
  const o = await open(t, CRLF_DOC);
  const { ctx, body, b } = o;
  await answerStatus(status([hunk("h1")]));
  b.edit.click();
  await settle();
  assert.equal(versionReads(), 0, "no consent popup for an Edit that cannot happen");
  assert.equal(ed.mounted, 0);
  assert.equal(ctx.editing(), false);
  assert.match(errBar(body)!.textContent, CRLF_WORDS);
});

// ── 2. the host's logWarning reaches the viewer's note bar ──────────────────────────────────────────

test("a tracked save that landed with a failed comments-log append: the host's words go up in the note bar with the aside closed, and onSaved hears logged: false", async (t) => {
  const o = await open(t);
  const { ctx, body, b, wrap } = o;
  await answerStatus(status([]));                      // tracked, nothing pending: Save routes through the host, the editor carries no marks
  assert.equal(asideOpen(wrap), false, "the aside was never opened");
  await enterEdit(o);
  assert.equal(ed.trackOpts, null, "nothing pending: a plain mount");
  const m = saveTracked(o, DOC + "one\n");
  await saveReply(m.reqId, status([], { fileMtimeNs: NS(9), storeMtimeNs: NS(10) }), { logged: false, logWarning: WARN });
  assert.equal(ctx.editing(), false, "the save landed: edit mode ends");
  assert.equal(ctx.mtimeNs(), NS(9), "the fence moved to the saved file");
  assert.deepEqual(savedInfos, [{ mtimeNs: NS(9), logged: false }]);
  assert.ok(errBar(body), "the warning is shown");
  assert.equal(errBar(body)!.textContent, WARN, "in the host's words");
  assert.equal(body.childNodes[0], errBar(body), "above the saved read view, after its repaint");
  assert.ok(body.childNodes.length > 1, "which is painted");
  assert.equal(asideOpen(wrap), false, "with the aside still closed: the bar is the one surface");
  assert.equal(b.save.hidden, true);
});

test("in-flight typing: the warned ack keeps the editor and says the warning above it; a later clean save leaves with no bar", async (t) => {
  const o = await open(t);
  const { ctx, body, b } = o;
  await answerStatus(status([]));
  await enterEdit(o);
  const m1 = saveTracked(o, DOC + "one\n");
  typeInto(DOC + "one\ntwo");                          // typed during the round-trip
  await saveReply(m1.reqId, status([], { fileMtimeNs: NS(9), storeMtimeNs: NS(10) }), { logged: false, logWarning: WARN });
  assert.equal(ctx.editing(), true, "the in-flight keystrokes keep edit mode");
  assert.equal(ed.destroyed, 0);
  assert.equal(b.save.disabled, false); assert.equal(b.save.textContent, "Save", "re-armed");
  assert.equal(errBar(body)!.textContent, WARN, "said above the editor the stay keeps");
  assert.equal(body.childNodes[0], errBar(body));
  assert.ok(body.querySelector(".fileview-cm"), "the editor is still the body");
  assert.deepEqual(savedInfos, [{ mtimeNs: NS(9), logged: false }]);
  const m2 = saveTracked(o, DOC + "one\ntwo\n");
  await saveReply(m2.reqId, status([], { fileMtimeNs: NS(11), storeMtimeNs: NS(12) }));   // clean: logged, no warning
  assert.equal(ctx.editing(), false);
  assert.equal(errBar(body), null, "a clean save raises no bar, and the warned one went with the editor's repaint");
  assert.deepEqual(savedInfos.map((i) => i.logged), [false, true]);
});

test("a tracked save whose reply carries an empty or non-string logWarning raises no bar", async (t) => {
  const o = await open(t);
  const { ctx, body } = o;
  await answerStatus(status([]));
  await enterEdit(o);
  const m = saveTracked(o, DOC + "one\n");
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: m.reqId, ...status([], { fileMtimeNs: NS(9), storeMtimeNs: NS(10) }), verb: "save", logged: true, logWarning: "" } }));
  await settle();
  assert.equal(ctx.editing(), false);
  assert.equal(errBar(body), null);
});

// ── pinned at source: the two call sites share one guard, and the tracked ack reads the warning first ──

const VIEW = fs.readFileSync(nodePath.resolve(process.cwd(), "..", "ui", "webview", "file-view.ts"), "utf8");

test("source: trackedRefusal guards the click and the mount over each call's own begin(), before edit mode is entered", () => {
  assert.match(VIEW, /const trackedRefusal = \(pending: \{ refusal: string \} \| null\): string \| null => \{\n\s*if \(!pending\) return null;\n\s*if \(chunkTracks === false\) return pending\.refusal;\n\s*if \(text !== null && \/\\r\\n\/\.test\(text\)\) return CRLF_REFUSAL \+ pending\.refusal;/);
  const click = VIEW.split('editBtn.addEventListener("click", () => {')[1].split("ensureEditingAllowed")[0];
  assert.match(click, /const refused = trackedRefusal\(trackedEdit \? trackedEdit\.begin\(\) : null\);\n\s*if \(refused\) \{ noteBar\(refused\); return; \}/, "the click: a refusal needs no consent popup");
  const enter = VIEW.split("const enterEdit = () => {")[1].split("editorChunk().then(")[0];
  assert.match(enter, /const pending = trackedEdit \? trackedEdit\.begin\(\) : null;\n\s*const refused = trackedRefusal\(pending\);\n\s*if \(refused\) \{ noteBar\(refused\); return; \}\n[\s\S]*?editing = true;/,
    "the mount: guarded over the begin() whose records the editor takes, before editing is set");
  assert.equal((VIEW.match(/trackedEdit\.begin\(\)/g) || []).length, 2, "begin() is asked at the click and at the mount, nowhere else");
  assert.match(enter, /if \(isMd && fmt\.md === "rendered"\) \{ fmt\.md = "raw"; saveFmt\(fmt\); \}/, "the Raw switch follows the guard");
  assert.doesNotMatch(VIEW.split('editBtn.addEventListener("click", () => {')[1].split("const saveBtn")[0], /fmt\.md = "raw"/, "…and left the click");
});

test("source: the tracked ack reads the host's logWarning off the resolved value into the save's hooks before the ack runs, as the fileSaved branch reads its reply", () => {
  const ack = VIEW.split("trackedEdit.save(content, records, decisions).then(")[1].split("(e: { code?: unknown; error?: unknown }) =>")[0];
  assert.match(ack, /const w = \(r as \{ logWarning\?: unknown \}\)\.logWarning;\n\s*hooks\.logWarning = typeof w === "string" && w \? w : null;\n\s*hooks\.saved\(r\.mtimeNs, r\.logged\);/,
    "read off the resolved value, before the ack runs");
  // the member's text is pinned by file-comments.test.ts, so the field rides the value unnamed there and its doc says so
  assert.ok(VIEW.includes("save(content: string, records: unknown[], decided: EditDecisions): Promise<{ mtimeNs: string; logged: boolean }>;"));
  assert.match(VIEW, /The resolved value ALSO carries the host's `logWarning`/, "TrackedEdit.save's doc names what rides the value");
});
