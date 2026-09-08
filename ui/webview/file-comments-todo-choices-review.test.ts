// The Send confirm's answer-a-todo control after the 2026-09-07 review of the todo-file follow-on (plans/file-review.md,
// "The todo-file follow-on (2026-09-07)"), driven the way file-comments-todo-choices.test.ts drives it: the panel mounted
// for real over the file-comments-panel.test.ts stand-in, the kernel's status replies as window messages carrying `todos`,
// the confirm's controls read back and flipped through the panel's own root. Three things the review found, pinned here:
// - A declined answer survives a change in the candidate count. The verdict lives in two controls — the one box when one
//   todo is offered, the radio group when several — and the next status can swap one for the other (a todo the session
//   filed naming the file joins the list; one settled from Waiting on you leaves it) while the confirm stays open. The
//   change handler writes a decline to both, so the box unchecked holds as the "none" pick when a second todo arrives and
//   a "none" pick holds as the box unchecked when one todo is left. Before, the other control's default re-asserted itself
//   and the send stamped a todo the person had declined.
// - A pick that left the list while two or more todos are still offered falls to the first offered, as a fresh confirm
//   would (chosenTodoId's fallback), by either route: the send that answered it, or a status read while the confirm was
//   open. The suite pinned that at source only.
// - Each todo's whole text is one click away: the label stays one clipped line with the text on hover, and a row whose
//   todo has words carries a fold that shows the whole text under the line, wrapped, keyed by todo id so a re-render keeps
//   it open. A hover never reaches touch, and two todos that begin alike clipped to the same words.
// Synthetic fixtures only: the notes-api world, placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { marked } from "marked";
import type { FileViewActionCtx, TrackedEdit } from "./file-view";
import type { Status, StoreComment, LogEntry, Hunk } from "./file-comments-model";

const UI = path.resolve(process.cwd(), "..", "ui", "webview");
const readSrc = (f: string) => fs.readFileSync(path.join(UI, f), "utf8");

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
  const tracked: Array<TrackedEdit | null> = [];      // the panel's half of editing over pending changes, as registered (Slice 5)
  let editingNow = false;
  const closers: Array<() => void> = [];
  const saved: Array<(info: { mtimeNs: string; logged: boolean }) => void> = [];
  const modes: string[] = [];
  let aside: E | null = null;
  const noop = () => { /* inert */ };
  const ctx: FileViewActionCtx = {
    path: ABS, sid: SID, todoId: null,
    body: () => body as unknown as HTMLElement, mode: () => "rendered", text: () => (src === undefined ? null : src),
    mtimeNs: () => "1757145600000000001", media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [], identity: () => ({ name: "api", color: null }),
    onRendered: noop, onSelection: noop, onSaved: (cb) => { saved.push(cb); }, onClose: (cb) => { closers.push(cb); },
    post: (m) => { posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: noop, editing: () => editingNow, setTrackedEdit: (t) => { tracked.push(t); }, guardClose: noop,   // the viewer's close guard (#370): inert here
    aside: (el) => { if (el) { aside = el as unknown as E; main.appendChild(aside); } else if (aside) { aside.remove(); aside = null; } },
    setMode: (m) => { modes.push(m); }, scrollToOffset: noop, reload: noop,
    ...ctxOver,
  };
  const unit = fc.fileCommentsAction.mount(ctx) as unknown as E;
  const button = unit.childNodes[0] as E;
  const last = (): Posted => posted[posted.length - 1];
  const reply = async (data: Record<string, unknown>) => { win.dispatchEvent(new MessageEvent("message", { data })); await tick(); await tick(); };
  return {
    fc, main, body, unit, button, posted, modes, saved, last, tracked,
    setEditing: (on: boolean) => { editingNow = on; },
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


// ── the todos a status lists ───────────────────────────────────────────────────────────────────────
// ids are per test: the page's memory of what it answered (answeredTodos) is module-level and outlives a harness
const tid = (tag: string) => tag.padEnd(8, "0") + "-1111-2222-3333-444444444444";
const todo = (tag: string, text?: string) => ({ id: tid(tag), text: text ?? "Pick the layout for " + tag });
async function opened(over: Partial<FileViewActionCtx> = {}, todos: Array<{ id: string; text: string }> = []) {
  const h = await harness(over);
  await h.ok({ todos });                 // the mount's status
  h.button.dispatch("click");            // open the panel: it re-asks
  await h.ok({ todos });
  return h;
}
const optLabel = (input: E): E => input.parentNode as E;
const values = (rs: E[]) => rs.map((r) => r.value);
const checks = (rs: E[]) => rs.map((r) => r.checked);
const labels = (rs: E[]) => rs.map((r) => optLabel(r).textContent);

// ── a status read while the confirm is open ────────────────────────────────────────────────────────
// The editor's onSaved callback (a save made with the confirm up) has the panel re-ask, and the reply lands through
// applyStatus, which leaves the confirm open — so the candidate count can change under a choice already made. The poll's
// re-read after a moved sidecar and Reload land the same way.
type H = Awaited<ReturnType<typeof opened>>;
async function reread(h: H, todos: Array<{ id: string; text: string }>) {
  for (const cb of h.saved) cb({ mtimeNs: "1757145600000000009", logged: true });
  await tick();
  assert.equal(h.last().verb, "status", "the save had the panel re-ask");
  await h.ok({ todos });
  assert.ok(h.q(".fc-confirm"), "the confirm is still open");
}
const sendNow = async (h: H) => { h.click('[data-act="fcsendgo"]'); await tick(); const m = h.last(); assert.equal(m.type, "fileCommentsSend"); return m; };

test("the one box unchecked holds as the none pick when a second todo names the file: after the send's own refresh, and under an open confirm", async () => {
  const A = todo("ra1", "Pick the layout for the report"), B = todo("ra2", "Say whether the appendix can go");
  const h = await opened({}, [A]);
  h.click('[data-act="fcsend"]');
  const cb = h.q('input[data-opt="todo"]')!;
  cb.checked = false; cb.dispatch("change");
  assert.equal("todoId" in (await sendNow(h)), false, "declined: nothing answered");
  await h.sent(); await h.ok({ todos: [A, B] });        // the session filed B, naming the file, before the refresh
  h.click('[data-act="fcsend"]');
  let radios = h.qa('input[data-opt="todopick"]');
  assert.deepEqual(values(radios), [A.id, B.id, ""], "two now: the radio group");
  assert.deepEqual(checks(radios), [false, false, true], "the decline holds as none — not the first by default");
  assert.equal("todoId" in (await sendNow(h)), false, "the send stamps nothing");
  await h.sent(); await h.ok({ todos: [A, B] });
  h.dispose();
  // the count changing under an OPEN confirm
  const C = todo("ra3"), D = todo("ra4");
  const k = await opened({}, [C]);
  k.click('[data-act="fcsend"]');
  const box = k.q('input[data-opt="todo"]')!;
  box.checked = false; box.dispatch("change");
  await reread(k, [C, D]);
  radios = k.qa('input[data-opt="todopick"]');
  assert.deepEqual(values(radios), [C.id, D.id, ""], "the radio group took the box's place while the confirm stayed open");
  assert.deepEqual(checks(radios), [false, false, true], "none, as the box said");
  assert.equal("todoId" in (await sendNow(k)), false);
  k.dispose();
});

test("a none pick holds as the box unchecked when one todo is left: after the send's own refresh, and under an open confirm", async () => {
  const A = todo("rb1"), B = todo("rb2");
  const h = await opened({}, [A, B]);
  h.click('[data-act="fcsend"]');
  const none = h.qa('input[data-opt="todopick"]')[2];
  none.checked = true; none.dispatch("change");
  assert.equal("todoId" in (await sendNow(h)), false);
  await h.sent(); await h.ok({ todos: [A] });            // B answered from Waiting on you meanwhile
  h.click('[data-act="fcsend"]');
  const cb = h.q('input[data-opt="todo"]')!;
  assert.ok(cb, "one left: the box");
  assert.equal(cb.checked, false, "unchecked, as none said — not the default");
  assert.equal("todoId" in (await sendNow(h)), false, "the send stamps nothing");
  await h.sent(); await h.ok({ todos: [A] });
  h.dispose();
  const C = todo("rb3"), D = todo("rb4");
  const k = await opened({}, [C, D]);
  k.click('[data-act="fcsend"]');
  const n2 = k.qa('input[data-opt="todopick"]')[2];
  n2.checked = true; n2.dispatch("change");
  await reread(k, [C]);
  const box = k.q('input[data-opt="todo"]')!;
  assert.ok(box, "the box took the group's place while the confirm stayed open");
  assert.equal(box.checked, false);
  assert.equal("todoId" in (await sendNow(k)), false);
  k.dispose();
});

test("an answer holds across the count too: the box checked again is the default (the first) once a second todo arrives; a picked todo stays the pick when it is the one left", async () => {
  const A = todo("rc1"), B = todo("rc2");
  const h = await opened({}, [A]);
  h.click('[data-act="fcsend"]');
  const cb = h.q('input[data-opt="todo"]')!;
  cb.checked = false; cb.dispatch("change");
  const again = h.q('input[data-opt="todo"]')!;
  again.checked = true; again.dispatch("change");
  await reread(h, [A, B]);
  assert.deepEqual(checks(h.qa('input[data-opt="todopick"]')), [true, false, false], "checked: the default again, the first offered");
  assert.equal((await sendNow(h)).todoId, A.id);
  h.dispose();
  // none, then D: D is the pick; C settles elsewhere, and the box for D is checked — the pick, not the decline before it
  const C = todo("rc3"), D = todo("rc4");
  const k = await opened({}, [C, D]);
  k.click('[data-act="fcsend"]');
  let rs = k.qa('input[data-opt="todopick"]');
  rs[2].checked = true; rs[2].dispatch("change");
  rs = k.qa('input[data-opt="todopick"]');
  rs[2].checked = false; rs[1].checked = true; rs[1].dispatch("change");
  assert.deepEqual(checks(k.qa('input[data-opt="todopick"]')), [false, true, false]);
  await reread(k, [D]);
  const box = k.q('input[data-opt="todo"]')!;
  assert.equal(box.checked, true, "the pick is the one left: the box is checked");
  assert.equal(optLabel(box).textContent, "answer the todo: " + D.text);
  assert.equal((await sendNow(k)).todoId, D.id);
  k.dispose();
});

test("a pick that left the list while two or more are still offered falls to the first, as a fresh confirm would: answered by the send before (the status's word), or settled elsewhere under an open confirm; a pick the refresh still lists holds", async () => {
  const A = todo("rd1"), B = todo("rd2"), C = todo("rd3");
  const h = await opened({}, [A, B, C]);
  h.click('[data-act="fcsend"]');
  let rs = h.qa('input[data-opt="todopick"]');
  rs[0].checked = false; rs[1].checked = true; rs[1].dispatch("change");
  assert.equal((await sendNow(h)).todoId, B.id, "the pick goes out");
  await h.sent(); await h.ok({ todos: [A, C] });         // B settled by that send: the kernel lists the other two
  h.click('[data-act="fcsend"]');
  rs = h.qa('input[data-opt="todopick"]');
  assert.deepEqual(values(rs), [A.id, C.id, ""], "still several: the radio group");
  assert.deepEqual(checks(rs), [true, false, false], "the pick is gone: the first offered, not none and not the last pick");
  assert.equal((await sendNow(h)).todoId, A.id, "the send carries the first");
  await h.sent(); await h.ok({ todos: [C] });
  h.dispose();
  // the page's own memory drops no pick the kernel still lists: the refresh is asked after the send's reply, so a
  // todo on it is open (a parked send, or a reopened one) and the memory is released for it (file-comments-todo-choices
  // .test.ts) — the pick holds, since it never left the list
  const D = todo("rd4"), E2 = todo("rd5"), F = todo("rd6");
  const g = await opened({}, [D, E2, F]);
  g.click('[data-act="fcsend"]');
  rs = g.qa('input[data-opt="todopick"]');
  rs[0].checked = false; rs[2].checked = true; rs[2].dispatch("change");   // F, the last todo (the radio before none)
  assert.equal((await sendNow(g)).todoId, F.id);
  await g.sent(); await g.ok({ todos: [D, E2, F] });
  g.click('[data-act="fcsend"]');
  rs = g.qa('input[data-opt="todopick"]');
  assert.deepEqual(values(rs), [D.id, E2.id, F.id, ""], "F is listed by a status asked after the send: open, so offered");
  assert.deepEqual(checks(rs), [false, false, true, false], "the pick holds: F never left the list");
  g.dispose();
  // settled elsewhere while the confirm is open: the same fallback, the confirm still up
  const P = todo("rd7"), Q = todo("rd8"), R = todo("rd9");
  const k = await opened({}, [P, Q, R]);
  k.click('[data-act="fcsend"]');
  rs = k.qa('input[data-opt="todopick"]');
  rs[0].checked = false; rs[2].checked = true; rs[2].dispatch("change");   // R
  assert.deepEqual(checks(k.qa('input[data-opt="todopick"]')), [false, false, true, false]);
  await reread(k, [P, Q]);
  rs = k.qa('input[data-opt="todopick"]');
  assert.deepEqual(values(rs), [P.id, Q.id, ""]);
  assert.deepEqual(checks(rs), [true, false, false], "R left the list: the first offered");
  assert.equal((await sendNow(k)).todoId, P.id);
  k.dispose();
});

test("each todo's whole text is one click away: the row's fold shows it under the line, wrapped, and a re-render keeps it open; the label stays one clipped line with the text on hover", async () => {
  // two todos that begin alike: at the aside's width their labels clip to the same words, and a hover never reaches touch
  // (both under todoChoiceLabel's 80-character cut, so the CSS clip alone is what hides the difference)
  const A = todo("re1", "Pick the layout for the quarterly report: two columns, or one"),
    B = todo("re2", "Pick the layout for the quarterly report: keep the appendix,\nor move it out");
  const h = await opened({}, [A, B]);
  h.click('[data-act="fcsend"]');
  const rs = h.qa('input[data-opt="todopick"]');
  let folds = h.qa('[data-act="fctodotext"]');
  assert.deepEqual(folds.map((f) => f.dataset.id), [A.id, B.id], "a fold per todo with words; none has none");
  assert.deepEqual(folds.map((f) => f.textContent), ["▸", "▸"], "the Log rows' glyph");
  assert.deepEqual(folds.map((f) => f.getAttribute("aria-expanded")), ["false", "false"]);
  assert.equal(folds[0].title, "Show the whole todo");
  assert.equal(folds[0].tagName, "BUTTON", "a real button: click-safe through the root's delegate, Enter and Space for free");
  assert.equal(h.q(".fc-todo-text"), null, "closed by default: the one-line label is the glance");
  assert.equal(optLabel(rs[1]).textContent, "Pick the layout for the quarterly report: keep the appendix, or move it out", "the label: one line, under the cut");
  assert.equal(optLabel(rs[1]).title, B.text, "and the hover, as before");
  assert.equal((optLabel(rs[1]).childNodes[1] as E).style.whiteSpace, "nowrap", "still clipped inline");
  assert.equal(folds[1].parentNode, optLabel(rs[1]).parentNode, "the glyph shares the label's line");
  h.click('[data-act="fctodotext"][data-id="' + B.id + '"]');
  let whole = h.qa(".fc-todo-text");
  assert.equal(whole.length, 1, "B's row alone unfolded");
  assert.equal(whole[0].textContent, B.text, "the whole text, its own line break kept");
  assert.ok(whole[0].classList.contains("fc-body"), "the card body's dress: pre-wrap, wrapping anywhere (the sheets)");
  assert.equal(whole[0].parentNode, optLabel(h.qa('input[data-opt="todopick"]')[1]).parentNode!.parentNode, "under B's line, in B's row (the click re-rendered: the radios are re-read)");
  folds = h.qa('[data-act="fctodotext"]');
  assert.deepEqual(folds.map((f) => f.textContent), ["▸", "▾"]);
  assert.equal(folds[1].getAttribute("aria-expanded"), "true");
  assert.equal(folds[1].title, "Hide the whole todo");
  assert.equal(optLabel(h.qa('input[data-opt="todopick"]')[1]).textContent, "Pick the layout for the quarterly report: keep the appendix, or move it out", "the label unchanged");
  // a re-render keeps it open: a pick, then a status read while the confirm is up
  const now = h.qa('input[data-opt="todopick"]');
  now[0].checked = false; now[1].checked = true; now[1].dispatch("change");
  assert.equal(h.qa(".fc-todo-text").length, 1, "open through the pick's re-render");
  await reread(h, [A, B]);
  whole = h.qa(".fc-todo-text");
  assert.equal(whole.length, 1, "open through the status's re-render");
  assert.equal(whole[0].textContent, B.text);
  assert.deepEqual(checks(h.qa('input[data-opt="todopick"]')), [false, true, false], "and the pick held");
  h.click('[data-act="fctodotext"][data-id="' + B.id + '"]');
  assert.equal(h.q(".fc-todo-text"), null, "a second click closes it");
  assert.deepEqual(h.qa('[data-act="fctodotext"]').map((f) => f.textContent), ["▸", "▸"]);
  h.dispose();
  // one candidate: the box's row folds the same way, keyed by the todo it answers; the label is the one the box always wore
  const C = todo("re3", "Approve the rollout note");
  const k = await opened({}, [C]);
  k.click('[data-act="fcsend"]');
  const cb = k.q('input[data-opt="todo"]')!;
  assert.equal(cb.value, C.id, "the box's value is the todo it answers");
  assert.equal(k.q('[data-act="fctodotext"]')!.dataset.id, C.id);
  k.click('[data-act="fctodotext"]');
  assert.equal(k.q(".fc-todo-text")!.textContent, C.text);
  assert.equal(optLabel(k.q('input[data-opt="todo"]')!).textContent, "answer the todo: " + C.text);
  assert.equal(k.q('input[data-opt="todo"]')!.checked, true, "the fold flips nothing: the box is as it was");
  assert.equal((await sendNow(k)).todoId, C.id);
  k.dispose();
  // no words to show (the opened-from todo the status never listed): nothing underneath, so no fold
  const g = await opened({ todoId: tid("re4") }, []);
  g.click('[data-act="fcsend"]');
  assert.ok(g.q('input[data-opt="todo"]'));
  assert.equal(g.q('[data-act="fctodotext"]'), null);
  g.dispose();
});

// ── what the stand-in cannot show, pinned at source ────────────────────────────────────────────────

test("source pins: the handler writes a decline to both slots; the fold's set is keyed by todo id; the whole text wears the sheets' wrapping body", () => {
  const SRC = readSrc("file-comments.ts");
  assert.match(SRC, /if \(k === "todopick"\) this\.sendOpts\.todo = t\.value !== "";\n\s*else if \(k === "todo"\) this\.todoPick = t\.checked \? null : "";/,
    "a none pick unchecks the box; the box unchecked is the \"\" pick, checked the null default");
  assert.match(SRC, /openTodoText = new Set<string>\(\);/);
  assert.match(SRC, /fctodotext: \(x\) => \{ const id = x\.dataset\.id!; if \(this\.openTodoText\.has\(id\)\) this\.openTodoText\.delete\(id\); else this\.openTodoText\.add\(id\); this\.render\(\); \}/);
  assert.match(SRC, /const fold = btn\(open \? "▾" : "▸", "fctodotext", "fc-sec"\);/, "the preview's dress, the Log rows' glyph");
  for (const sheet of ["styles.css", "feed.css"]) {
    assert.match(readSrc(sheet), /^\.fc-body \{ font-size: 0\.86em; white-space: pre-wrap; overflow-wrap: anywhere;/m, sheet + ": the whole text wraps, its line breaks kept");
  }
});
