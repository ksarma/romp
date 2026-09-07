// The Comments panel driven end to end through a DOM stand-in (plans/file-review.md, Slice 1; the
// 2026-09-06 review fixes): the panel is mounted for real, its delegate root receives clicks, its composer
// receives keys, and the kernel's replies arrive as window messages — so what file-comments.test.ts pins at
// source is exercised here as behavior. The stand-in is the structural surface the panel and anchor-map.ts
// walk (there is no jsdom in this tree), plus the fragment parser anchor-map.test.ts uses for marked's HTML.
// Synthetic fixtures only: the notes-api world, placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { marked } from "marked";
import type { FileViewActionCtx } from "./file-view";
import type { Status, StoreComment, LogEntry } from "./file-comments-model";

// ── the DOM stand-in ───────────────────────────────────────────────────────────────────────────────
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
  /** A document-level event (the float's mousedown hide listens on the document, capture phase). */
  fire(type: string, target: N): void { for (const fn of this.listeners.get(type) || []) fn({ type, target }); }
}
class N {
  nodeType = 0;
  parentNode: N | null = null;
  childNodes: N[] = [];
  constructor(public ownerDocument: Doc) {}
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
  constructor(doc: Doc, public data: string) { super(doc); }
  get length(): number { return this.data.length; }
  splitText(offset: number): T {
    const tail = new T(this.ownerDocument, this.data.slice(offset));
    this.data = this.data.slice(0, offset);
    const p = this.parentNode as E | null;
    if (p) { const i = p.childNodes.indexOf(this); p.childNodes.splice(i + 1, 0, tail); tail.parentNode = p; }
    return tail;
  }
}
type Ev = { type: string; target: N; currentTarget: N | null; key?: string; defaultPrevented: boolean; preventDefault(): void; stopPropagation(): void };
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
  }
  private classes(): string[] { return (this.attrs.get("class") || "").split(/\s+/).filter(Boolean); }
  private setClasses(c: string[]): void { this.attrs.set("class", [...new Set(c)].join(" ")); }
  get className(): string { return this.attrs.get("class") || ""; }
  set className(v: string) { this.attrs.set("class", v); }
  set innerHTML(html: string) { this.replaceChildren(...parseHTML(this.ownerDocument, html)); }
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
  replaceChildren(...c: N[]): void { for (const x of this.childNodes) x.parentNode = null; this.childNodes = []; for (const x of c) this.appendChild(x); }
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
  /** Comma groups of descendant chains (`A B`), each link a compound selector. */
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
  /** Dispatch with bubbling: every ancestor's listeners run until one stops propagation. */
  dispatch(type: string, init: { key?: string } = {}): Ev {
    let stopped = false;
    const ev: Ev = { type, target: this, currentTarget: null, key: init.key, defaultPrevented: false,
      preventDefault() { this.defaultPrevented = true; }, stopPropagation() { stopped = true; } };
    for (let n: N | null = this; n && !stopped; n = n.parentNode) {
      if (!(n instanceof E)) continue;
      ev.currentTarget = n;
      for (const fn of [...(n.listeners.get(type) || [])]) fn(ev);
    }
    return ev;
  }
  getBoundingClientRect(): { left: number; top: number; right: number; bottom: number; width: number; height: number } {
    return this.tagName === "IMG" ? { left: 100, top: 200, right: 400, bottom: 400, width: 300, height: 200 } : { left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 };
  }
  scrollIntoView(): void { /* inert */ }
  focus(): void { /* inert */ }
}
const VOID = new Set(["br", "hr", "img", "input", "meta", "link", "area", "base", "col", "embed", "source", "track", "wbr"]);
const NAMED: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " " };
function decodeEntities(s: string): string {
  return s.replace(/&(#x[0-9a-fA-F]+|#\d+|[a-zA-Z]+);/g, (m, e: string) => {
    if (e[0] === "#") return String.fromCodePoint(parseInt(e[1] === "x" || e[1] === "X" ? e.slice(2) : e.slice(1), e[1] === "x" || e[1] === "X" ? 16 : 10));
    return e in NAMED ? NAMED[e] : m;
  });
}
function parseHTML(doc: Doc, html: string): N[] {
  html = html.replace(/\r\n?/g, "\n");
  const root = doc.createElement("#fragment");
  const stack: E[] = [root];
  let i = 0;
  const top = () => stack[stack.length - 1];
  while (i < html.length) {
    if (html[i] === "<") {
      if (html.startsWith("<!--", i)) { const e = html.indexOf("-->", i); i = e < 0 ? html.length : e + 3; continue; }
      if (html[i + 1] === "/") {
        const e = html.indexOf(">", i);
        const name = html.slice(i + 2, e).trim().toUpperCase();
        for (let k = stack.length - 1; k > 0; k--) { if (stack[k].tagName === name) { stack.length = k; break; } }
        i = e + 1; continue;
      }
      const m = /^<([a-zA-Z][\w:-]*)((?:\s+[^\s"'>\/=]+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'=<>`]+))?)*)\s*(\/?)>/.exec(html.slice(i));
      if (!m) { top().appendChild(doc.createTextNode("<")); i++; continue; }
      const el = doc.createElement(m[1]);
      const attrRe = /([^\s"'>\/=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?/g;
      let a: RegExpExecArray | null;
      while ((a = attrRe.exec(m[2]))) el.setAttribute(a[1], decodeEntities(a[2] ?? a[3] ?? a[4] ?? ""));
      top().appendChild(el);
      i += m[0].length;
      if (!m[3] && !VOID.has(m[1].toLowerCase())) {
        stack.push(el);
        if (m[1].toLowerCase() === "pre" && html[i] === "\n") i++;
      }
      continue;
    }
    let e = html.indexOf("<", i);
    if (e < 0) e = html.length;
    top().appendChild(doc.createTextNode(decodeEntities(html.slice(i, e))));
    i = e;
  }
  return root.childNodes.slice();
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
function status(over: Partial<Status> = {}): Status {
  return {
    verb: "status", root: "/repo/notes-api", storePath: "/repo/notes-api/.trackchanges/docs%2Freport.md.json",
    trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
    store: { v: 3, path: "docs/report.md", suggestions: [], comments: [passage] },
    hunks: [], log: [],
    unsent: { comments: [passage.id], replies: [], accepted: 0, rejected: 0, watermark: null },
    ...over,
  };
}
const CORRUPT = "the comments for ~/notes-api/docs/report.md could not be read: ~/notes-api/.trackchanges/docs%2Freport.md.json is not valid JSON in the expected shape; nothing was changed";

// ── the harness: a mounted panel inside the viewer's body row ──────────────────────────────────────
type Posted = Record<string, any>;
async function harness(over: Partial<FileViewActionCtx> & { html?: string; src?: string } = {}) {
  const fc = await import("./file-comments");
  const { html, src, ...ctxOver } = over;
  const main = doc.createElement("div"); main.className = "fileview-main";
  const body = doc.createElement("div"); body.className = "fileview-body"; main.appendChild(body);
  if (html !== undefined) { const md = doc.createElement("div"); md.className = "fileview-md"; md.innerHTML = html; body.appendChild(md); }
  const posted: Posted[] = [];
  const closers: Array<() => void> = [];
  const saved: Array<(info: { mtimeNs: string; logged: boolean }) => void> = [];
  const modes: string[] = [];
  let aside: E | null = null;
  const noop = () => { /* inert */ };
  const ctx: FileViewActionCtx = {
    path: ABS, sid: SID, todoId: null,
    body: () => body as unknown as HTMLElement, mode: () => "rendered", text: () => (src === undefined ? null : src),
    mtimeNs: () => "1757145600000000001", media: () => null, mediaElement: () => null, renderedImages: () => [], identity: () => ({ name: "api", color: null }),
    onRendered: noop, onSelection: noop, onSaved: (cb) => { saved.push(cb); }, onClose: (cb) => { closers.push(cb); },
    post: (m) => { posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: noop,
    aside: (el) => { if (el) { aside = el as unknown as E; main.appendChild(aside); } else if (aside) { aside.remove(); aside = null; } },
    setMode: (m) => { modes.push(m); }, scrollToOffset: noop, reload: noop,
    ...ctxOver,
  };
  const unit = fc.fileCommentsAction.mount(ctx) as unknown as E;
  const button = unit.childNodes[0] as E;
  const last = (): Posted => posted[posted.length - 1];
  const reply = async (data: Record<string, unknown>) => { win.dispatchEvent(new MessageEvent("message", { data })); await tick(); await tick(); };
  return {
    fc, main, body, unit, button, posted, modes, saved, last,
    ok: (over: Partial<Status> = {}) => reply({ type: "fileCommentsResult", reqId: last().reqId, ...status(over) }),
    refuse: (code: string, error: string) => reply({ type: "fileCommentsFailed", reqId: last().reqId, verb: last().verb, code, error }),
    sent: (queued = false) => reply({ type: "fileCommentsSent", reqId: last().reqId, queued }),
    q: (sel: string) => main.querySelector(sel),
    qa: (sel: string) => main.querySelectorAll(sel),
    click: (sel: string) => { const e = main.querySelector(sel); assert.ok(e, "a control " + sel); e!.dispatch("click"); },
    float: () => { const f = doc.body.querySelectorAll(".fc-float"); return f[f.length - 1]; },
    dispose: () => { for (const cb of closers) cb(); },
  };
}
const embedOf = (src: string, alt: string): string => src.match(new RegExp("!\\[" + alt + "\\]\\([^)]*\\)"))![0];

// ── the sidecar the kernel cannot read ─────────────────────────────────────────────────────────────

test("a status refusal is not a wait and not a moved fence: the cards say what follows, and a comment refuses under the composer with the host's own reason", async () => {
  const h = await harness();
  await h.refuse("corrupt", CORRUPT);
  assert.equal(h.unit.hidden, false, "a refusal other than no-node still shows the action");
  h.button.dispatch("click");                          // open: the panel re-asks
  assert.equal(h.last().verb, "status");
  await h.refuse("corrupt", CORRUPT);
  const cards = h.q(".fc-cards")!;
  assert.equal(cards.textContent, "The comments could not be read, so none can be shown or written.");
  assert.ok(h.q(".fc-sec-head .fc-err")!.textContent.includes(CORRUPT), "the head's row names the reason");
  // Comment on this file, a note, Enter: the panel re-asks status ONCE and sends no verb with an empty fence
  h.click('[data-act="fcfile"]');
  const input = h.q("input.fc-input")!;
  input.value = "Add a summary at the top.";
  const before = h.posted.length;
  input.dispatch("keydown", { key: "Enter" });
  await tick();
  assert.equal(h.posted.length, before + 1, "one re-ask");
  assert.equal(h.last().verb, "status");
  await h.refuse("corrupt", CORRUPT);
  assert.equal(h.posted.length, before + 1, "no comment went out: an empty fence would have drawn store-moved, a reason that is not the reason");
  const err = h.q(".fc-composer .fc-err")!;
  assert.equal(err.childNodes[0].textContent, "Nothing written: " + CORRUPT, "the refusal sits under the control that asked, in the host's words");
  assert.equal(err.querySelector('[data-act="fcreload"]'), null, "no Reload: re-reading cannot mend the sidecar");
  assert.equal(input.value, "Add a summary at the top.", "the note stays");
  assert.equal(h.q(".fc-cards")!.textContent, "The comments could not be read, so none can be shown or written.", "still not a wait");
  // the person mends the sidecar and presses Enter again: the re-ask succeeds and the comment carries the real fence
  input.dispatch("keydown", { key: "Enter" });
  await tick();
  assert.equal(h.last().verb, "status");
  await h.ok();
  const c = h.last();
  assert.equal(c.verb, "comment");
  assert.deepEqual(c.fence, { storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003" }, "the fence from the status just read");
  assert.equal(c.args.note, "Add a summary at the top.");
  await h.ok();
  assert.equal(h.q(".fc-composer")!.hidden, true, "saved: the composer closes");
  assert.equal(h.q(".fc-composer .fc-err"), null);
  assert.ok(h.q(".fc-card"), "the cards render from the status that came back");
  h.dispose();
});

test("a status still in flight is waited for, not fenced blind: the cards wear the loader, and the first mutating click re-asks and proceeds on the answer", async () => {
  const h = await harness();
  h.button.dispatch("click");                          // opened before the mount's status answered
  const cards = h.q(".fc-cards")!;
  assert.ok(cards.querySelector(".fc-load"), "no refusal yet: the wait wears the romp loader (ui/CLAUDE.md)");
  assert.equal(cards.querySelector(".fc-empty"), null, "…and no line claims a read that nothing is making");
  h.click('[data-act="fcfile"]');
  const input = h.q("input.fc-input")!;
  input.value = "Lead with the numbers.";
  input.dispatch("keydown", { key: "Enter" });
  await tick();
  assert.equal(h.last().verb, "status");
  await h.ok({ store: null, storeMtimeNs: null });
  const c = h.last();
  assert.equal(c.verb, "comment");
  assert.deepEqual(c.fence, { storeMtimeNs: "", configMtimeNs: "1757145600000000003" }, '"" only when the status itself says there is no sidecar');
  h.dispose();
});

// ── the Log ────────────────────────────────────────────────────────────────────────────────────────

test("Log rows open to what they hold — a send's comments as they went, a direct edit's diff — a toggle row is the whole entry, and the open state survives a re-render", async () => {
  const h = await harness();
  const DIFF = "@@ -3 +3 @@\n-We recommend shipping the cache.\n+We recommend shipping the cache in v1.2.";
  const log: LogEntry[] = [
    { ts: "2026-09-06T08:00:00.000Z", kind: "set-tracked", author: "you", on: true, scope: "file", entry: "docs/report.md" },
    { ts: "2026-09-06T08:05:00.000Z", kind: "send", author: "you", sid: SID, sessionName: "api", accepted: 0, rejected: 0, queued: false, watermark: T0,
      comments: [{ id: passage.id, desc: 'on "shipping the cache in v1.2"', body: "Which cache? Say which." }, { id: "x-1", desc: "on this file", body: "Add a summary at the top." }] },
    { ts: "2026-09-06T08:10:00.000Z", kind: "edit", author: "you", mtimeBeforeNs: "1", mtimeAfterNs: "2", bytesBefore: 1200, bytesAfter: 1209, diff: DIFF, truncated: false },
    { ts: "2026-09-06T08:12:00.000Z", kind: "edit", author: "you", mtimeBeforeNs: "2", mtimeAfterNs: "3", bytesBefore: 1209, bytesAfter: 40000, diff: "@@ -1 +1 @@\n-a\n+b", truncated: true },
  ];
  await h.ok({ log });
  h.button.dispatch("click");
  await h.ok({ log });
  h.click('[data-act="fclog"]');
  let rows = h.qa(".fc-log-row");
  assert.equal(rows.length, 4, "one row per entry, newest first");
  assert.match(rows[1].textContent, /▸ Edited the file directly \(1200 → 1209 bytes\)$/);
  assert.match(rows[2].textContent, /▸ Sent 2 comments to api$/);
  assert.equal(rows[2].dataset.act, "fclogrow"); assert.equal(rows[1].dataset.act, "fclogrow");
  assert.equal(rows[2].title, "Show what was sent"); assert.equal(rows[1].title, "Show the edit");
  assert.equal(rows[2].getAttribute("role"), "button");
  assert.equal(rows[3].dataset.act, undefined, "a tracking toggle has nothing underneath: the line is the entry");
  assert.doesNotMatch(rows[3].textContent, /[▸▾]/);
  assert.equal(h.qa(".fc-log-detail").length, 0, "compact by default");
  assert.ok(!h.q(".fc-log")!.textContent.includes("Which cache? Say which."), "no bodies in the compact view");
  // one click down: the send's comments in the confirm's own list dress
  rows[2].dispatch("click");
  let detail = h.qa(".fc-log-detail");
  assert.equal(detail.length, 1);
  const items = detail[0].querySelectorAll("li");
  assert.equal(items.length, 2);
  assert.equal(items[0].querySelector(".fc-list-desc")!.textContent, 'on "shipping the cache in v1.2": ');
  assert.equal(items[0].textContent, 'on "shipping the cache in v1.2": Which cache? Say which.');
  assert.equal(items[1].textContent, "on this file: Add a summary at the top.");
  rows = h.qa(".fc-log-row");
  assert.match(rows[2].textContent, /▾ Sent 2 comments to api$/);
  assert.equal(rows[2].title, "Hide");
  assert.ok(rows[2].classList.contains("open"));
  assert.equal(rows[2].parentNode!.childNodes.indexOf(detail[0]), rows[2].parentNode!.childNodes.indexOf(rows[2]) + 1, "the detail sits right under its row");
  // the edit's diff, and the cut-short note on the one the kernel capped (every click re-renders: re-query the rows,
  // as a real click lands on whatever row is under the pointer at that moment)
  h.qa(".fc-log-row")[1].dispatch("click");
  h.qa(".fc-log-row")[0].dispatch("click");
  detail = h.qa(".fc-log-detail");
  assert.equal(detail.length, 3);
  assert.equal(detail[1].querySelector("pre.fc-msg")!.textContent, DIFF);
  assert.equal(detail[1].querySelector(".fc-note"), null);
  assert.equal(detail[0].querySelector(".fc-note")!.textContent, "The diff was cut short; the file holds the rest.");
  // a poll's re-render (fresh status, same entries) keeps every open row open — keyed state, not DOM state
  h.saved[0]({ mtimeNs: "9", logged: true });
  await tick();
  assert.equal(h.last().verb, "status");
  await h.ok({ log });
  assert.equal(h.qa(".fc-log-detail").length, 3, "still open after the re-render");
  // and closes on a second click
  h.qa(".fc-log-row")[2].dispatch("click");
  assert.equal(h.qa(".fc-log-detail").length, 2);
  h.dispose();
});

test("a Log edit row whose entry recorded no diff has nothing to open", async () => {
  const h = await harness();
  const log: LogEntry[] = [{ ts: "2026-09-06T08:20:00.000Z", kind: "edit", author: "you", bytesBefore: 1, bytesAfter: 2 }];
  await h.ok({ log });
  h.button.dispatch("click");
  await h.ok({ log });
  h.click('[data-act="fclog"]');
  const row = h.q(".fc-log-row")!;
  assert.equal(row.dataset.act, undefined);
  assert.equal(row.textContent.replace(/^[^E]*/, ""), "Edited the file directly (1 → 2 bytes)");
  h.dispose();
});

// ── a picture in Rendered view ─────────────────────────────────────────────────────────────────────

const FIG_SRC = "# Report\n\nIntro text here.\n\n```\n![Chart in a fence](figures/p95.png)\n```\n\n![Latency chart](figures/p95.png)\n\nThe summary follows.\n\n![Logo](logo.svg)\n";

test("a click on a rendered picture offers Comment; the anchor is the embed's source text; the presel frame and the located ring go on the picture itself", async () => {
  const h = await harness({ src: FIG_SRC, html: marked.parse(FIG_SRC) as string });
  await h.ok({ store: null, storeMtimeNs: null, unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null } });
  const imgs = h.body.querySelectorAll("img");
  assert.equal(imgs.length, 2, "the fenced embed renders as text, not a picture");
  const float = h.float();
  imgs[0].dispatch("click");
  assert.equal(float.hidden, true, "with the panel closed a picture click offers nothing, as a selection does");
  h.button.dispatch("click");
  await h.ok({ store: null, storeMtimeNs: null, unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null } });
  imgs[0].dispatch("click");
  assert.equal(float.hidden, false, "the float offers Comment beside the picture");
  assert.equal(float.style.left, "406px"); assert.equal(float.style.top, "170px");
  doc.fire("mousedown", h.body);
  assert.equal(float.hidden, true, "a press elsewhere withdraws the offer");
  imgs[0].dispatch("click");
  assert.equal(float.hidden, false);
  float.dispatch("click");
  assert.equal(float.hidden, true);
  const embed = embedOf(FIG_SRC, "Latency chart");
  const at = FIG_SRC.indexOf(embed);
  assert.ok(at > FIG_SRC.indexOf("```"), "the real embed, after the fence");
  const ref = h.q(".fc-composer-ref")!;
  assert.equal(ref.querySelector(".fc-quote")!.textContent, embed, "the composer shows the embed's source as the quote");
  assert.ok(imgs[0].classList.contains("fc-presel") && imgs[0].classList.contains("fc-img"), "the presel is a frame on the picture");
  assert.equal(imgs[0].style.outline, "2px solid var(--accent)");
  assert.equal(imgs[1].classList.contains("fc-presel"), false);
  assert.ok(h.body.contains(imgs[0]), "framed, never wrapped or removed");
  const input = h.q("input.fc-input")!;
  input.value = "Use the p99 chart instead.";
  input.dispatch("keydown", { key: "Enter" });
  await tick();
  const c = h.last();
  assert.equal(c.verb, "comment");
  assert.equal(c.args.note, "Use the p99 chart instead.");
  assert.equal(c.args.hintOffset, at);
  assert.equal(c.args.anchor.quote, embed, "the anchor is the embed's source text");
  assert.deepEqual(c.fence, { storeMtimeNs: "", configMtimeNs: "1757145600000000003" });
  // the kernel answers with the comment in the sidecar: the frame becomes the located ring, a click opens the card
  const figure: StoreComment = { id: "c9", author: "you", ts: T0, body: "Use the p99 chart instead.", anchor: c.args.anchor, replies: [], resolved: false };
  await h.ok({ store: { v: 3, path: "docs/report.md", suggestions: [], comments: [figure] }, unsent: { comments: ["c9"], replies: [], accepted: 0, rejected: 0, watermark: null } });
  assert.equal(h.q(".fc-composer")!.hidden, true, "saved: the composer closes");
  assert.equal(imgs[0].classList.contains("fc-presel"), false, "the presel left with the composer");
  assert.ok(imgs[0].classList.contains("fc-hl"), "the located ring is on the picture");
  assert.equal(imgs[0].style.outline, "2px solid var(--warn)");
  assert.equal(imgs[0].dataset.act, "fcopen"); assert.equal(imgs[0].dataset.id, "c9");
  assert.ok(h.body.contains(imgs[0]) && h.body.querySelectorAll("img").length === 2, "still two pictures in the document");
  assert.equal(imgs[1].dataset.act, undefined);
  imgs[0].dispatch("click");                          // the highlight's own action opens the card…
  const card = h.q('.fc-card[data-id="c9"]')!;
  assert.ok(card.classList.contains("open"));
  assert.equal(card.querySelector('[data-act="fcreveal"]'), null, "painted, so no Reveal is needed");
  assert.equal(float.hidden, false, "…and the picture is still commentable");
  // the ref's link scrolls to the frame: it carries the goto action because the comment is painted
  assert.equal(card.querySelector(".fc-ref")!.dataset.act, "fcgoto");
  h.dispose();
});

test("a picture the source holds no embed for still gets the offer, and the composer then says why and offers Raw", async () => {
  const src = "Intro.\n\n![Latency chart](figures/p95.png)\n";
  const html = (marked.parse(src) as string) + '<p><img src="ghost.png" alt="ghost"></p>';
  const h = await harness({ src, html });
  await h.ok({ store: null, storeMtimeNs: null });
  h.button.dispatch("click");
  await h.ok({ store: null, storeMtimeNs: null });
  const imgs = h.body.querySelectorAll("img");
  imgs[1].dispatch("click");
  const float = h.float();
  assert.equal(float.hidden, false);
  float.dispatch("click");
  const ref = h.q(".fc-composer-ref")!;
  assert.equal(ref.querySelector(".fc-refused")!.textContent, "The line that embeds this image was not found in the source; select it in the Raw view.");
  assert.ok(ref.querySelector('[data-act="fcraw"]'), "Switch to Raw is offered");
  assert.equal(imgs[1].classList.contains("fc-presel"), false);
  h.click('[data-act="fcraw"]');
  assert.deepEqual(h.modes, ["raw"]);
  h.dispose();
});

test("imageEmbeds: every embed form, in order, fenced code skipped; sameDest and embedFor match marked's encoded src and tell twins apart by order", async () => {
  const fc = await import("./file-comments");
  const src = [
    "![a](one.png)", "text ![b](two.png \"title\") more", "![c][ref] and ![d] and ![e][]",
    "<img src=\"three.png\" alt=x> <img src='four%20five.png'>", "```", "![fenced](one.png)", "```",
    "~~~", "<img src=\"nope.png\">", "~~~", "![f](<six seven.png>)", "![a](one.png)",
    "", "[ref]: r.png", "[d]: d.png 'D'", "[e]: e.png",
  ].join("\n");
  const embeds = fc.imageEmbeds(src);
  assert.deepEqual(embeds.map((e) => [e.dest, src.slice(e.start, e.end)]), [
    ["one.png", "![a](one.png)"], ["two.png", '![b](two.png "title")'], ["r.png", "![c][ref]"], ["d.png", "![d]"], ["e.png", "![e][]"],
    ["three.png", '<img src="three.png" alt=x>'], ["four%20five.png", "<img src='four%20five.png'>"],
    ["six seven.png", "![f](<six seven.png>)"], ["one.png", "![a](one.png)"],
  ]);
  assert.ok(fc.sameDest("six seven.png", "six%20seven.png"), "marked percent-encodes the destination");
  assert.ok(fc.sameDest("four%20five.png", "four%20five.png"));
  assert.ok(!fc.sameDest("one.png", "two.png"));
  // twins: the second rendered picture with the same src is the second embed with that destination
  const root = doc.createElement("div");
  root.innerHTML = '<p><img src="one.png"></p><p><img src="six%20seven.png"></p><p><img src="one.png"></p>';
  const imgs = root.querySelectorAll("img");
  const a1 = fc.embedFor(imgs[0] as unknown as Element, root as unknown as Element, src)!;
  const a2 = fc.embedFor(imgs[2] as unknown as Element, root as unknown as Element, src)!;
  assert.equal(a1.start, 0);
  assert.equal(a2.start, src.lastIndexOf("![a](one.png)"), "the second twin, not the fenced decoy between them");
  assert.equal(fc.embedFor(imgs[1] as unknown as Element, root as unknown as Element, src)!.dest, "six seven.png");
  assert.equal(fc.imgForRange(root as unknown as Element, src, { start: a2.start, end: a2.end }), imgs[2], "the inverse, for painting");
  assert.equal(fc.imgForRange(root as unknown as Element, src, { start: 0, end: 3 }), null, "only an exact embed range frames a picture");
  const ghost = doc.createElement("img"); ghost.setAttribute("src", "ghost.png"); root.appendChild(ghost);
  assert.equal(fc.embedFor(ghost as unknown as Element, root as unknown as Element, src), null);
});

// ── one send answers the todo, across viewers of this page ─────────────────────────────────────────

test("a todo naming several files is answered by the first send: a later viewer opened from the same todo shows no checkbox and sends no todoId; another todo still asks", async () => {
  const TODO = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";
  const a = await harness({ todoId: TODO });
  await a.ok();
  a.button.dispatch("click");
  await a.ok();
  a.click('[data-act="fcsend"]');
  assert.ok(a.q('input[data-opt="todo"]'), "the first viewer offers to answer the todo");
  a.click('[data-act="fcsendgo"]');
  await tick();
  const s1 = a.last();
  assert.equal(s1.type, "fileCommentsSend"); assert.equal(s1.todoId, TODO);
  await a.sent();
  await a.ok();                                        // the refresh after the send
  assert.match(a.q(".fc-sent")!.textContent, /^Sent to api at /);
  a.dispose();
  // the same todo's other file, in a fresh viewer (another open from the todo, or a Reload of this one)
  const b = await harness({ todoId: TODO, path: "/repo/notes-api/docs/summary.md" });
  await b.ok();
  b.button.dispatch("click");
  await b.ok();
  b.click('[data-act="fcsend"]');
  assert.ok(b.q(".fc-confirm"), "the confirm renders");
  assert.equal(b.q('input[data-opt="todo"]'), null, "answered by the first send: no checkbox");
  b.click('[data-act="fcsendgo"]');
  await tick();
  const s2 = b.last();
  assert.equal(s2.type, "fileCommentsSend");
  assert.equal("todoId" in s2, false, "the second send does not claim the todo");
  await b.sent();
  await b.ok();
  b.dispose();
  // a viewer opened from a different todo is unaffected
  const c = await harness({ todoId: "ffffffff-1111-2222-3333-444444444444" });
  await c.ok();
  c.button.dispatch("click");
  await c.ok();
  c.click('[data-act="fcsend"]');
  assert.ok(c.q('input[data-opt="todo"]'));
  c.dispose();
  // the latch is the STAMP: a send the kernel warned it could not mark leaves the todo answerable, here and in later viewers
  const OFF = "99999999-8888-7777-6666-555555555555";
  const d = await harness({ todoId: OFF });
  await d.ok();
  d.button.dispatch("click");
  await d.ok();
  d.click('[data-act="fcsend"]');
  d.click('[data-act="fcsendgo"]');
  await tick();
  assert.equal(d.last().todoId, OFF);
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsSent", reqId: d.last().reqId, queued: false, warning: "the message went, but nothing was marked: user todos are turned off on this machine" } }));
  await tick(); await tick();
  await d.ok();
  assert.match(d.q(".fc-err-warn")!.textContent, /nothing was marked/);
  d.click('[data-act="fcsend"]');
  assert.ok(d.q('input[data-opt="todo"]'), "not stamped: the checkbox stays");
  d.dispose();
  const e = await harness({ todoId: OFF, path: "/repo/notes-api/docs/summary.md" });
  await e.ok();
  e.button.dispatch("click");
  await e.ok();
  e.click('[data-act="fcsend"]');
  assert.ok(e.q('input[data-opt="todo"]'), "…and a later viewer from the same todo still offers it");
  e.dispose();
});
