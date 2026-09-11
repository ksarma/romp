// The editor's Save through the panel refused `busy` (plans/file-review.md, decision 49: the host's lock on the
// sidecar was still held by another writer after its wait). The panel suite drives this save path over the moved
// fences (file-comments-panel.test.ts: a store-moved refusal that stands, a config-moved one retried once) and the
// changes suite drives `busy` for the by-id and id-less decisions (file-comments-changes-review2.test.ts), but the
// save's own `busy` leg in saveThroughComments was held by a source pin alone (tools/file-review-plan-sidecar.test.mjs),
// so a regression that kept the literal and lost the retry passed every behavioral suite (the slice review, 2026-09-11).
// Here the same harness as the panel suite's drives the save: one status re-read, one retry with the fresh fence
// when the sidecar's records are still the editor's, the success applied as the status; the refusal handed to the
// viewer with its code and the host's words on a second `busy` or when the re-read shows other records, with no
// third save and no further re-read; and the saving editor's fence following the re-read. The viewer's half (the
// Reload offer on `busy`, file-view.ts) is the viewer suites' to drive. Synthetic fixtures only: the notes-api
// world, placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inspect } from "node:util";
import type { FileViewActionCtx, TrackedEdit } from "./file-view";
import type { Status, StoreComment, Hunk } from "./file-comments-model";
import { hideEdges, staysEnumerable } from "../test-dom-shim";

// ── the DOM stand-in (the panel suite's) ───────────────────────────────────────────────────────────
class Doc {
  body: E;
  hidden = false;
  listeners = new Map<string, Array<(ev: unknown) => void>>();
  constructor() { this.body = new E(this, "BODY"); }
  createElement(tag: string): E { return new E(this, tag.toUpperCase()); }
  createTextNode(s: string): T { return new T(this, s); }
  getElementById(): null { return null; }
  addEventListener(type: string, fn: (ev: unknown) => void): void { (this.listeners.get(type) || this.listeners.set(type, []).get(type)!).push(fn); }
  removeEventListener(type: string, fn: (ev: unknown) => void): void { const l = this.listeners.get(type); if (l) l.splice(l.indexOf(fn), 1); }
  fire(type: string, target: N): void { for (const fn of this.listeners.get(type) || []) fn({ type, target }); }
}
class N {
  nodeType = 0;
  parentNode!: N | null;
  childNodes!: N[];
  constructor(public ownerDocument: Doc) {
    Object.defineProperty(this, "parentNode", { value: null, writable: true, enumerable: false, configurable: true });
    Object.defineProperty(this, "childNodes", { value: [], writable: true, enumerable: false, configurable: true });
    hideEdges(this);
  }
  get parentElement(): E | null { return this.parentNode instanceof E ? this.parentNode : null; }
  get firstChild(): N | null { return this.childNodes[0] || null; }
  get textContent(): string { return this.nodeType === 3 ? (this as unknown as T).data : this.childNodes.map((c) => c.textContent).join(""); }
  set textContent(v: string) {
    for (const c of this.childNodes) c.parentNode = null;
    this.childNodes = v === "" ? [] : [this.ownerDocument.createTextNode(v)];
    for (const c of this.childNodes) c.parentNode = this;
  }
  contains(n: N | null): boolean { for (let x: N | null = n; x; x = x.parentNode) if (x === this) return true; return false; }
  remove(): void { if (this.parentNode) (this.parentNode as E).removeChild(this); }
}
class T extends N {
  nodeType = 3;
  constructor(doc: Doc, public data: string) { super(doc); hideEdges(this); }
  get length(): number { return this.data.length; }
  splitText(offset: number): T {
    const tail = new T(this.ownerDocument, this.data.slice(offset));
    this.data = this.data.slice(0, offset);
    const p = this.parentNode as E | null;
    if (p) { const i = p.childNodes.indexOf(this); p.childNodes.splice(i + 1, 0, tail); tail.parentNode = p; }
    return tail;
  }
}
type Ev = { type: string; target: N; currentTarget: N | null; key?: string; ctrlKey?: boolean; metaKey?: boolean; defaultPrevented: boolean; preventDefault(): void; stopPropagation(): void };
const kebab = (k: string | symbol): string => String(k).replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
type Compound = { tag: string | null; classes: string[]; attrs: Array<[string, string | null]> };
function parseSelector(sel: string): Compound[] {
  return sel.split(",").map((part) => {
    const s = part.trim();
    const out: Compound = { tag: null, classes: [], attrs: [] };
    const re = /^([a-zA-Z][\w-]*)|\.([\w-]+)|\[([\w-]+)(?:="([^"]*)")?\]/g;
    let m: RegExpExecArray | null;
    while ((m = re.exec(s))) {
      if (m[1]) out.tag = m[1].toUpperCase();
      else if (m[2]) out.classes.push(m[2]);
      else out.attrs.push([m[3], m[4] ?? null]);
      if (re.lastIndex === s.length) break;
    }
    return out;
  });
}
class E extends N {
  nodeType = 1;
  attrs = new Map<string, string>();
  listeners = new Map<string, Array<(ev: Ev) => void>>();
  hidden = false; title = ""; type = ""; disabled = false; placeholder = ""; value = ""; checked = false; offsetWidth = 0;
  style: Record<string, string> = {};
  dataset: Record<string, string>;
  classList = {
    add: (...c: string[]) => this.setClasses([...this.classes(), ...c]),
    remove: (...c: string[]) => this.setClasses(this.classes().filter((x) => !c.includes(x))),
    toggle: (c: string, on?: boolean) => { if (on === undefined ? !this.classes().includes(c) : on) this.classList.add(c); else this.classList.remove(c); },
    contains: (c: string) => this.classes().includes(c),
  };
  constructor(doc: Doc, public tagName: string) {
    super(doc);
    this.dataset = new Proxy({} as Record<string, string>, {
      get: (_t, k) => (typeof k === "string" ? this.attrs.get("data-" + kebab(k)) : undefined),
      set: (_t, k, v) => { this.attrs.set("data-" + kebab(k), String(v)); return true; },
      deleteProperty: (_t, k) => { this.attrs.delete("data-" + kebab(k)); return true; },
      has: (_t, k) => this.attrs.has("data-" + kebab(k)),
    });
    hideEdges(this);
  }
  private classes(): string[] { return (this.attrs.get("class") || "").split(/\s+/).filter(Boolean); }
  private setClasses(c: string[]): void { this.attrs.set("class", [...new Set(c)].join(" ")); }
  get className(): string { return this.attrs.get("class") || ""; }
  set className(v: string) { this.attrs.set("class", v); }
  // the panel writes innerHTML for the loader of an OPEN panel's slot only; these tests never open it, so a write here
  // is a stand-in gap to hear about, not to paper over
  set innerHTML(_html: string) { throw new Error("innerHTML is not modelled by this stand-in; open-panel paints belong in file-comments-panel.test.ts"); }
  getAttribute(n: string): string | null { return this.attrs.has(n) ? (this.attrs.get(n) as string) : null; }
  setAttribute(n: string, v: string): void { this.attrs.set(n, v); }
  removeAttribute(n: string): void { this.attrs.delete(n); }
  removeChild(n: N): N { const i = this.childNodes.indexOf(n); if (i >= 0) this.childNodes.splice(i, 1); n.parentNode = null; return n; }
  appendChild<X extends N>(n: X): X { if (n.parentNode) (n.parentNode as E).removeChild(n); this.childNodes.push(n); n.parentNode = this; return n; }
  insertBefore(n: N, ref: N | null): N {
    if (!ref) return this.appendChild(n);
    if (n.parentNode) (n.parentNode as E).removeChild(n);
    const i = this.childNodes.indexOf(ref);
    this.childNodes.splice(i, 0, n); n.parentNode = this; return n;
  }
  replaceChildren(...c: N[]): void { for (const x of this.childNodes) x.parentNode = null; this.childNodes.length = 0; for (const x of c) this.appendChild(x); }
  normalize(): void {
    const out: N[] = [];
    for (const c of this.childNodes) {
      const prev = out[out.length - 1];
      if (c instanceof T && prev instanceof T) { prev.data += c.data; c.parentNode = null; }
      else if (c instanceof T && c.data === "") c.parentNode = null;
      else out.push(c);
    }
    this.childNodes = out;
  }
  matches(sel: string): boolean {
    return parseSelector(sel).some((c) => (c.tag === null || c.tag === this.tagName)
      && c.classes.every((k) => this.classList.contains(k))
      && c.attrs.every(([a, v]) => this.attrs.has(a) && (v === null || this.attrs.get(a) === v)));
  }
  closest(sel: string): E | null { for (let x: N | null = this; x; x = x.parentNode) if (x instanceof E && x.matches(sel)) return x; return null; }
  querySelectorAll(sel: string): E[] {
    const out: E[] = [];
    const chains = sel.split(",").map((g) => g.trim().split(/\s+/));
    const fits = (el: E, chain: string[]): boolean => {
      if (!el.matches(chain[chain.length - 1])) return false;
      let k = chain.length - 2;
      for (let a: N | null = el.parentNode; a && k >= 0 && a !== this.parentNode; a = a.parentNode) if (a instanceof E && a.matches(chain[k])) k--;
      return k < 0;
    };
    const visit = (n: N) => { for (const c of n.childNodes) { if (c instanceof E) { if (chains.some((ch) => fits(c, ch))) out.push(c); visit(c); } } };
    visit(this);
    return out;
  }
  querySelector(sel: string): E | null { return this.querySelectorAll(sel)[0] || null; }
  addEventListener(type: string, fn: (ev: Ev) => void): void { (this.listeners.get(type) || this.listeners.set(type, []).get(type)!).push(fn); }
  removeEventListener(type: string, fn: (ev: Ev) => void): void { const l = this.listeners.get(type); if (l) l.splice(l.indexOf(fn), 1); }
  dispatch(type: string, init: { key?: string; ctrlKey?: boolean; metaKey?: boolean } = {}): Ev {
    let stopped = false;
    const ev: Ev = { type, target: this, currentTarget: null, key: init.key, ctrlKey: init.ctrlKey, metaKey: init.metaKey, defaultPrevented: false,
      preventDefault() { this.defaultPrevented = true; }, stopPropagation() { stopped = true; } };
    for (let n: N | null = this; n && !stopped; n = n.parentNode) {
      if (!(n instanceof E)) continue;
      ev.currentTarget = n;
      for (const fn of [...(n.listeners.get(type) || [])]) fn(ev);
    }
    return ev;
  }
  getBoundingClientRect(): { left: number; top: number; right: number; bottom: number; width: number; height: number } {
    return { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 };
  }
  scrollIntoView(): void { /* inert */ }
  focus(): void { /* inert */ }
}

// ── globals the module reaches for, installed before it is imported ────────────────────────────────
const doc = new Doc();
const win: any = new EventTarget();
win.parent = win;
win.innerWidth = 1200; win.innerHeight = 800;
win.getSelection = () => ({ isCollapsed: true, rangeCount: 0, toString: () => "" });
(globalThis as any).window = win;
(globalThis as any).document = doc;
(globalThis as any).fetch = async () => ({ status: 404, headers: { get: () => null }, json: async () => [] });
// the panel's poll interval must never hold the test process open when an assertion fails before dispose()
const realSetInterval = globalThis.setInterval;
(globalThis as any).setInterval = (fn: () => void, ms: number) => { const t = realSetInterval(fn, ms); (t as any).unref?.(); return t; };
const tick = () => new Promise<void>((r) => setImmediate(r));

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const T0 = 1757145600000;
const passage: StoreComment = {
  id: T0 + "-118", author: "you", ts: T0, body: "Which cache? Say which.",
  anchor: { quote: "shipping the cache in v1.2", prefix: "We recommend ", suffix: "." }, replies: [], resolved: false,
};
const FILE_NS = "1757145600000000001", STORE_NS = "1757145600000000002", CONFIG_NS = "1757145600000000003";
const S9 = "1757145600000000020";                      // the sidecar's clock after the other writer's rename landed
function status(over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: "/repo/notes-api", storePath: "/repo/notes-api/.trackchanges/docs%2Freport.md.json",
    trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
    fileMtimeNs: FILE_NS, storeMtimeNs: STORE_NS, configMtimeNs: CONFIG_NS,
    store: { v: 3, path: "docs/report.md", suggestions: [], comments: [passage] },
    hunks: [], log: [],
    unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 0, watermark: null },
    ...over,
  };
}
const chg = (id: string, from: number, oldText: string, newText: string) => ({
  rec: { id, author: "api", authorId: SID, ts: T0, kind: "sub", from, newText, oldText },
  hunk: { id, author: "api", ts: T0, kind: "sub", curFrom: from, curTo: from + newText.length, baseFrom: from, baseTo: from + oldText.length, oldText, newText, anchor: null } as Hunk,
});
const withChanges = (...cs: Array<ReturnType<typeof chg>>): Partial<Status> => ({
  hunks: cs.map((c) => c.hunk), store: { v: 3, path: "docs/report.md", suggestions: cs.map((c) => c.rec), comments: [passage] },
});
/** The host's refusal, verbatim (tools/file-comments-host.mjs, underStoreLock): the path as the host shows it. */
const BUSY = "another editor is writing ~/notes-api/docs/report.md; retry";
const settleOf = (p: Promise<unknown>) => { const box: { ok?: unknown; err?: unknown } = {}; p.then((v) => { box.ok = v; }, (e) => { box.err = e; }); return box; };

// ── the harness: a mounted panel inside the viewer's body row, the editor's seam captured ──────────
type Posted = Record<string, any>;
async function harness() {
  const fc = await import("./file-comments");
  const main = doc.createElement("div"); main.className = "fileview-main";
  const body = doc.createElement("div"); body.className = "fileview-body"; main.appendChild(body);
  const posted: Posted[] = [];
  const tracked: Array<TrackedEdit | null> = [];
  let editingNow = false;
  const closers: Array<() => void> = [];
  let aside: E | null = null;
  const noop = () => { /* inert */ };
  const ctx: FileViewActionCtx = {
    path: ABS, sid: SID, todoId: null,
    body: () => body as unknown as HTMLElement, mode: () => "rendered", text: () => null,
    mtimeNs: () => FILE_NS, media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [], identity: () => ({ name: "api", color: null }),
    onRendered: noop, onSelection: noop, onSaved: noop, onClose: (cb) => { closers.push(cb); },
    post: (m) => { posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: noop, editing: () => editingNow, setTrackedEdit: (t) => { tracked.push(t); }, guardClose: noop,
    aside: (el) => { if (el) { aside = el as unknown as E; main.appendChild(aside); } else if (aside) { aside.remove(); aside = null; } },
    setMode: noop, scrollToOffset: noop, reload: noop,
  };
  const unit = fc.fileCommentsAction.mount(ctx) as unknown as E;
  const button = unit.childNodes[0] as E;
  const last = (): Posted => posted[posted.length - 1];
  const reply = async (data: Record<string, unknown>) => { win.dispatchEvent(new MessageEvent("message", { data })); await tick(); await tick(); };
  return {
    button, posted, last, tracked,
    setEditing: (on: boolean) => { editingNow = on; },
    ok: (over: Partial<Status> = {}) => reply({ type: "fileCommentsResult", reqId: last().reqId, ...status(over) }),
    refuse: (code: string, error: string) => reply({ type: "fileCommentsFailed", reqId: last().reqId, verb: last().verb, code, error }),
    count: (verb: string) => posted.filter((m) => m.type === "fileComments" && m.verb === verb).length,
    dispose: () => { for (const cb of closers) cb(); },
  };
}
/** Mount over one pending change, click Edit (begin) and send the editor's Save: the first save frame and its box. */
async function saveFromEditor(h: Awaited<ReturnType<typeof harness>>, c1: ReturnType<typeof chg>) {
  await h.ok(withChanges(c1));
  const te = h.tracked[0]!;
  te.begin();
  h.setEditing(true);
  const out = settleOf(te.save("the new text", [c1.rec], { accepted: [], rejected: [] }));
  await tick();
  const first = h.last();
  assert.equal(first.verb, "save");
  assert.deepEqual(first.fence, { storeMtimeNs: STORE_NS, configMtimeNs: CONFIG_NS, fileMtimeNs: FILE_NS }, "fenced on the sidecar the records came from, the config, and the file as loaded");
  return { te, out, first };
}

test("a save refused busy: the panel re-reads status once and, with the sidecar's records still the editor's, retries once with the fresh fence; the success is applied as the status", async () => {
  const h = await harness();
  const c1 = chg("c1", 5, "old", "new");
  const { out, first } = await saveFromEditor(h, c1);
  const asks = h.count("status");
  await h.refuse("busy", BUSY);
  assert.equal(h.last().verb, "status", "one re-read before deciding: the other writer's write is on disk by now");
  assert.equal(h.count("status"), asks + 1);
  assert.equal(out.ok, undefined); assert.equal(out.err, undefined, "still open");
  await h.ok({ ...withChanges(c1), storeMtimeNs: S9 });   // a reply a session wrote mid-edit moved the clock; the records are the same
  const again = h.last();
  assert.equal(again.verb, "save", "retried once");
  assert.notEqual(again.reqId, first.reqId);
  assert.deepEqual(again.args, first.args, "the same text, records and decisions");
  assert.deepEqual(again.fence, { storeMtimeNs: S9, configMtimeNs: CONFIG_NS, fileMtimeNs: FILE_NS }, "re-fenced on the sidecar as it stands after the other writer");
  assert.equal(h.count("status"), asks + 1, "no second re-read before the retry");
  await h.ok({ verb: "save", fileMtimeNs: "1757145600000000009", storeMtimeNs: "1757145600000000010", hunks: [],
    store: { v: 3, path: "docs/report.md", suggestions: [], comments: [passage] }, logged: true } as unknown as Partial<Status>);
  assert.deepEqual(out.ok, { mtimeNs: "1757145600000000009", logged: true }, "the saved fields the viewer fires onSaved with");
  assert.equal(h.count("save"), 2);
  assert.equal(h.button.textContent, "Comments · 1", "the reply is the panel's status: no changes left");
  h.dispose();
});

test("a second busy on the retry is not retried: the refusal reaches the viewer with its code and the host's words, with no third save and no further re-read; the saving editor's fence followed the re-read, so its next Save goes out fenced on the sidecar as it stands", async () => {
  const h = await harness();
  const c1 = chg("c1", 5, "old", "new");
  const { te, out } = await saveFromEditor(h, c1);
  await h.refuse("busy", BUSY);
  await h.ok({ ...withChanges(c1), storeMtimeNs: S9 });
  assert.equal(h.last().verb, "save", "the one retry");
  const asks = h.count("status");
  await h.refuse("busy", BUSY);
  assert.deepEqual(out.err, { code: "busy", error: BUSY }, "the viewer gets the code (its Reload offer keys on it) and the words for its bar");
  assert.equal(h.count("save"), 2, "one retry, never a third");
  assert.equal(h.count("status"), asks, "no re-read after the second refusal: the viewer's bar is the next move");
  // the editor stays up (the viewer keeps the buffer over a refused save); Save again goes straight out, fenced on the
  // sidecar the re-read showed, not the one the records first rode in from: the stale fence would draw store-moved
  const out2 = settleOf(te.save("the new text", [c1.rec], { accepted: [], rejected: [] }));
  await tick();
  const next = h.last();
  assert.equal(next.verb, "save");
  assert.equal(h.count("status"), asks, "no re-read before it");
  assert.deepEqual(next.fence, { storeMtimeNs: S9, configMtimeNs: CONFIG_NS, fileMtimeNs: FILE_NS }, "the seed followed the re-read");
  assert.equal(out2.err, undefined);
  h.dispose();
});

test("a save refused busy whose re-read shows the sidecar's records changed: the refusal stands with its code and the host's words, and there is no retry", async () => {
  const h = await harness();
  const c1 = chg("c1", 5, "old", "new"), c2 = chg("c2", 40, "was", "is");
  const { out } = await saveFromEditor(h, c1);
  await h.refuse("busy", BUSY);
  assert.equal(h.last().verb, "status");
  await h.ok({ ...withChanges(c1, c2), storeMtimeNs: S9 });   // the writer that held the lock recorded a second change
  assert.deepEqual(out.err, { code: "busy", error: BUSY }, "the records changed under the editor: the refusal stands, in the host's words");
  assert.equal(h.last().verb, "status", "no retry");
  assert.equal(h.count("save"), 1);
  assert.match(h.button.textContent, /2 changes$/, "the panel shows the re-read status meanwhile");
  h.dispose();
});

test("the stand-in's nodes inspect as their projection: no enumerable edge, so a failing assertion's dump cannot walk the tree", () => {
  const root = doc.createElement("div");
  const kid = doc.createElement("span");
  root.appendChild(kid);
  kid.appendChild(doc.createTextNode("leaf"));
  root.setAttribute("data-x", "1"); root.classList.add("c");
  for (const n of [root, kid, kid.firstChild as T]) {
    assert.ok(Object.keys(n).every((k) => staysEnumerable((n as unknown as Record<string, unknown>)[k])), "only primitives stay enumerable on " + n.constructor.name);
    const dump = inspect(n, { compact: false, customInspect: false, depth: 1000, maxArrayLength: Infinity, showHidden: false, showProxy: false, sorted: true, getters: true });
    assert.ok(!dump.includes("parentNode") && !dump.includes("childNodes"), "no edge in the dump: " + dump);
  }
});
