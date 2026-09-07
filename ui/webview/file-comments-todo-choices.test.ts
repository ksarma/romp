// The Send confirm's answer-a-todo control, driven (plans/file-review.md, "The todo-file follow-on (2026-09-07)"): the
// panel mounted for real over the file-comments-panel.test.ts stand-in, the kernel's status replies arriving as window
// messages WITH the new `todos` list — the open user todos of the session whose `file` is this file — and the confirm's
// controls read back and flipped through the panel's own root.
//
// Before the follow-on the confirm offered "answer the todo" only when the file had been OPENED from a todo (ctx.todoId).
// A todo now names its file in its record, the kernel lists such todos on the file's status, and a Send answers one of
// them however the file was reached: one candidate is the checkbox (checked, the todo's text on one line), several are a
// radio group — Answer: the first selected, the others, none — so one send answers one todo (decision 28); the pick goes
// out as `todoId`; and after a send the list follows the next status, which no longer carries the settled todo. The
// page's own memory of what it stamped (answeredTodos) covers the moment between the send and that status, and a send
// the kernel could not stamp leaves the todo offered, as before. The pure half (todoChoices, todoChoiceLabel) runs
// directly; what the stand-in cannot show is pinned at source. Synthetic fixtures only: the notes-api world, placeholder
// ids.
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
    post: (m) => { posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: noop, editing: () => editingNow, setTrackedEdit: (t) => { tracked.push(t); },
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

test("a todo that names the file is offered on a file NOT opened from it: the checkbox, checked, wearing the todo's text; the send carries its id; the next status without it shows no checkbox", async () => {
  const A = todo("a1", "Pick the layout for the report");
  const h = await opened({}, [A]);       // ctx.todoId is null: the file was opened from a chat link, not a todo
  h.click('[data-act="fcsend"]');
  const cb = h.q('input[data-opt="todo"]')!;
  assert.ok(cb, "offered from the status's todos alone");
  assert.equal(cb.checked, true, "checked by default (decision 8)");
  assert.equal(optLabel(cb).textContent, "answer the todo: " + A.text, "the todo's own words, not the generic label");
  assert.equal(optLabel(cb).title, A.text, "the whole text is the hover");
  assert.equal(h.q('input[data-opt="todopick"]'), null, "one candidate: no radio group");
  h.click('[data-act="fcsendgo"]');
  await tick();
  const sent = h.last();
  assert.equal(sent.type, "fileCommentsSend");
  assert.equal(sent.todoId, A.id, "the send names the todo the status listed");
  await h.sent();
  await h.ok({ todos: [] });             // the refresh after the send: the kernel no longer lists the settled todo
  assert.match(h.q(".fc-sent")!.textContent, /^Sent to api at /);
  h.click('[data-act="fcsend"]');
  assert.ok(h.q(".fc-confirm"), "the confirm renders again");
  assert.equal(h.q('input[data-opt="todo"]'), null, "the todo left with the status");
  assert.equal(h.q('input[data-opt="todopick"]'), null);
  h.dispose();
});

test("the checkbox unchecked sends no todoId, and the todo stays offered for the next send", async () => {
  const A = todo("b1");
  const h = await opened({}, [A]);
  h.click('[data-act="fcsend"]');
  const cb = h.q('input[data-opt="todo"]')!;
  cb.checked = false; cb.dispatch("change");
  assert.equal(h.q('input[data-opt="todo"]')!.checked, false, "the re-render keeps the box unchecked");
  h.click('[data-act="fcsendgo"]'); await tick();
  const sent = h.last();
  assert.equal(sent.type, "fileCommentsSend");
  assert.equal("todoId" in sent, false, "nothing answered");
  await h.sent(); await h.ok({ todos: [A] });
  h.click('[data-act="fcsend"]');
  assert.ok(h.q('input[data-opt="todo"]'), "still offered: nothing was stamped");
  h.dispose();
});

test("several todos name the file: one radio group — Answer: the first selected, the second, none; the pick goes out as todoId; one left afterwards is the checkbox again", async () => {
  const A = todo("c1", "Pick the layout"), B = todo("c2", "Say whether the cache section can go");
  const h = await opened({}, [A, B]);
  h.click('[data-act="fcsend"]');
  assert.equal(h.q('input[data-opt="todo"]'), null, "several: no checkbox");
  const radios = h.qa('input[data-opt="todopick"]');
  assert.deepEqual(values(radios), [A.id, B.id, ""], "the kernel's order, then none");
  assert.deepEqual(checks(radios), [true, false, false], "the first selected");
  assert.deepEqual(labels(radios), [A.text, B.text, "none"]);
  assert.deepEqual(radios.map((r) => r.type), ["radio", "radio", "radio"]);
  const group = h.q(".fc-todo-pick")!;
  assert.equal(group.getAttribute("role"), "radiogroup");
  assert.equal(group.childNodes[0].textContent, "Answer:");
  assert.equal(optLabel(radios[1]).title, B.text, "each todo's whole text is its hover");
  // pick B: the change reaches the panel's root; the re-render keeps B selected
  radios[0].checked = false; radios[1].checked = true; radios[1].dispatch("change");
  assert.deepEqual(checks(h.qa('input[data-opt="todopick"]')), [false, true, false], "the pick survives the re-render");
  h.click('[data-act="fcsendgo"]'); await tick();
  assert.equal(h.last().todoId, B.id, "the pick goes out");
  await h.sent();
  await h.ok({ todos: [A] });            // B settled: the kernel lists A alone
  h.click('[data-act="fcsend"]');
  const cb = h.q('input[data-opt="todo"]')!;
  assert.ok(cb, "one left: the checkbox again");
  assert.equal(optLabel(cb).textContent, "answer the todo: " + A.text);
  assert.equal(h.q('input[data-opt="todopick"]'), null);
  h.dispose();
});

test("none picked: the send carries no todoId, answers nothing, and none stays the pick while every todo stays offered", async () => {
  const A = todo("d1"), B = todo("d2");
  const h = await opened({}, [A, B]);
  h.click('[data-act="fcsend"]');
  const none = h.qa('input[data-opt="todopick"]')[2];
  assert.equal(none.value, "");
  none.checked = true; none.dispatch("change");
  h.click('[data-act="fcsendgo"]'); await tick();
  const sent = h.last();
  assert.equal(sent.type, "fileCommentsSend");
  assert.equal("todoId" in sent, false);
  await h.sent(); await h.ok({ todos: [A, B] });
  h.click('[data-act="fcsend"]');
  const radios = h.qa('input[data-opt="todopick"]');
  assert.deepEqual(values(radios), [A.id, B.id, ""]);
  assert.deepEqual(checks(radios), [false, false, true], "none stays the pick");
  h.dispose();
});

test("the todo the file was opened from leads the group with the status's words; unlisted, it is the checkbox with the generic label, as before", async () => {
  const A = todo("e1"), B = todo("e2");
  const h = await opened({ todoId: B.id }, [A, B]);
  h.click('[data-act="fcsend"]');
  const radios = h.qa('input[data-opt="todopick"]');
  assert.deepEqual(values(radios), [B.id, A.id, ""], "the opened-from todo first, then the rest in the kernel's order, each once");
  assert.deepEqual(labels(radios), [B.text, A.text, "none"]);
  assert.equal(radios[0].checked, true);
  h.dispose();
  // the status lists none (a detail-path todo, or an older kernel): today's checkbox, today's words, today's todoId
  const C = todo("e3");
  const g = await opened({ todoId: C.id }, []);
  g.click('[data-act="fcsend"]');
  const cb = g.q('input[data-opt="todo"]')!;
  assert.ok(cb);
  assert.equal(optLabel(cb).textContent, "answer the todo this file was opened from");
  assert.equal(optLabel(cb).title, "", "no text to hover: the viewer never receives the opened-from todo's words");
  g.click('[data-act="fcsendgo"]'); await tick();
  assert.equal(g.last().todoId, C.id);
  await g.sent(); await g.ok();
  g.click('[data-act="fcsend"]');
  assert.equal(g.q('input[data-opt="todo"]'), null, "answered: no checkbox (decision 28)");
  g.dispose();
  // opened from D while the status lists another todo too: D leads, with the words the status gave it
  const D = todo("e4", "Approve the rollout note");
  const k = await opened({ todoId: D.id }, [A, D]);
  k.click('[data-act="fcsend"]');
  const rs = k.qa('input[data-opt="todopick"]');
  assert.deepEqual(values(rs), [D.id, A.id, ""]);
  assert.equal(optLabel(rs[0]).textContent, D.text);
  k.dispose();
});

test("the page remembers what it stamped: a status still listing an answered todo offers nothing for it; a send the kernel could not stamp leaves the todo offered", async () => {
  const A = todo("f1"), B = todo("f2");
  const h = await opened({}, [A, B]);
  h.click('[data-act="fcsend"]');
  h.click('[data-act="fcsendgo"]'); await tick();
  assert.equal(h.last().todoId, A.id, "the first selected by default");
  await h.sent();
  await h.ok({ todos: [A, B] });         // a status read before the stamp landed still lists A
  h.click('[data-act="fcsend"]');
  const cb = h.q('input[data-opt="todo"]')!;
  assert.ok(cb, "A is remembered as answered: B alone, as the checkbox");
  assert.equal(optLabel(cb).textContent, "answer the todo: " + B.text);
  // B's send is warned (nothing stamped): B stays offered
  h.click('[data-act="fcsendgo"]'); await tick();
  assert.equal(h.last().todoId, B.id);
  win.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsSent", reqId: h.last().reqId, queued: false, warning: "the message went, but nothing was marked: user todos are turned off on this machine" } }));
  await tick(); await tick();
  await h.ok({ todos: [A, B] });
  assert.match(h.q(".fc-err-warn")!.textContent, /nothing was marked/);
  h.click('[data-act="fcsend"]');
  assert.equal(optLabel(h.q('input[data-opt="todo"]')!).textContent, "answer the todo: " + B.text, "not stamped: still offered");
  h.dispose();
});

test("a long todo text is one line in the confirm: cut with an ellipsis, clipped in the label, the whole text on hover", async () => {
  const long = todo("g1", "Read the report's " + "very ".repeat(40) + "long section and say which of the two layouts to keep");
  const h = await opened({}, [long]);
  h.click('[data-act="fcsend"]');
  const label = optLabel(h.q('input[data-opt="todo"]')!);
  const shown = label.textContent.replace(/^answer the todo: /, "");
  assert.ok(shown.length <= 80 && shown.endsWith("…"), "cut to a line's worth: " + shown.length);
  assert.equal(label.title, long.text);
  const span = label.childNodes[1] as E;
  assert.equal(span.style.whiteSpace, "nowrap"); assert.equal(span.style.textOverflow, "ellipsis"); assert.equal(span.style.overflow, "hidden");
  h.dispose();
  // the radio group's labels are clipped the same way
  const M = todo("g2", "x".repeat(300)), N = todo("g3");
  const k = await opened({}, [M, N]);
  k.click('[data-act="fcsend"]');
  const rs = k.qa('input[data-opt="todopick"]');
  assert.equal(optLabel(rs[0]).textContent.length, 80);
  assert.equal(optLabel(rs[0]).title, M.text);
  assert.equal((optLabel(rs[0]).childNodes[1] as E).style.whiteSpace, "nowrap");
  k.dispose();
});

// ── the pure half ──────────────────────────────────────────────────────────────────────────────────

test("todoChoices: the opened-from todo first (its text from the status when listed), the status's todos in order, each once, minus the answered; the label is one line", async () => {
  const { todoChoices, todoChoiceLabel, TODO_OPENED_FROM } = await import("./file-comments-model");
  const A = { id: "a", text: "Alpha" }, B = { id: "b", text: "Beta" };
  const none = () => false;
  assert.deepEqual(todoChoices(null, { todos: [A, B] }, none), [{ id: "a", text: "Alpha" }, { id: "b", text: "Beta" }]);
  assert.deepEqual(todoChoices("b", { todos: [A, B] }, none), [{ id: "b", text: "Beta" }, { id: "a", text: "Alpha" }], "the opened-from todo leads, once");
  assert.deepEqual(todoChoices("z", { todos: [A] }, none), [{ id: "z", text: null }, { id: "a", text: "Alpha" }], "unlisted: no text");
  assert.deepEqual(todoChoices("z", null, none), [{ id: "z", text: null }]);
  assert.deepEqual(todoChoices("z", { todos: null }, none), [{ id: "z", text: null }]);
  assert.deepEqual(todoChoices("z", {}, none), [{ id: "z", text: null }], "an older kernel's status has no field");
  assert.deepEqual(todoChoices(null, {}, none), []);
  assert.deepEqual(todoChoices(undefined, { todos: [] }, none), []);
  assert.deepEqual(todoChoices("a", { todos: [A, B] }, (id) => id === "a"), [{ id: "b", text: "Beta" }], "an answered todo is not offered, wherever it came from");
  assert.deepEqual(todoChoices(null, { todos: [A, { id: "", text: "x" } as any, { id: 3, text: "y" } as any, null as any, "a" as any] }, none), [{ id: "a", text: "Alpha" }], "malformed rows are skipped");
  assert.deepEqual(todoChoices(null, { todos: [{ id: "q" } as any] }, none), [{ id: "q", text: null }], "a row without text is offered under the generic label");
  assert.equal(todoChoiceLabel({ id: "z", text: null }), TODO_OPENED_FROM);
  assert.equal(TODO_OPENED_FROM, "the todo this file was opened from");
  assert.equal(todoChoiceLabel({ id: "a", text: "  Alpha\n  beta  " }), "Alpha beta", "one line: whitespace collapsed");
  assert.equal(todoChoiceLabel({ id: "a", text: "" }), TODO_OPENED_FROM, "an empty text falls to the generic words");
  const long = "x".repeat(200);
  assert.equal(todoChoiceLabel({ id: "a", text: long }).length, 80);
  assert.ok(todoChoiceLabel({ id: "a", text: long }).endsWith("…"));
  assert.equal(todoChoiceLabel({ id: "a", text: "y".repeat(80) }), "y".repeat(80), "exactly a line's worth is not cut");
});

// ── what the stand-in cannot show, pinned at source ────────────────────────────────────────────────

test("source pins: the Status field, the radio group's option, the change handler's branch, the send's chosen id, the stamp latch, the one memory", () => {
  const MODEL = readSrc("file-comments-model.ts"), SRC = readSrc("file-comments.ts");
  assert.match(MODEL, /todos\?: Array<\{ id: string; text: string \}> \| null;/, "the kernel's list rides the status reply");
  assert.match(MODEL, /export function todoChoices\(todoId: string \| null \| undefined, s: Pick<Status, "todos"> \| null \| undefined, answered: \(id: string\) => boolean\): TodoChoice\[\] \{/);
  assert.match(SRC, /this\.todoOpts\(opts, s\);/, "the confirm's todo control comes from one place");
  assert.match(SRC, /cb\.type = "checkbox"; cb\.checked = this\.sendOpts\.todo; cb\.dataset\.opt = "todo";\n\s*opts\.appendChild\(optRow\(cb, c\.text === null \? "answer " \+ TODO_OPENED_FROM : "answer the todo: " \+ todoChoiceLabel\(c\), c\.text\)\);/,
    "one candidate: the checkbox opt() builds, on sendOpts.todo, with the todo's words");
  assert.match(SRC, /r\.type = "radio"; r\.name = "fc-todo"; r\.value = c\.id; r\.checked = c\.id === pick; r\.dataset\.opt = "todopick";/);
  assert.match(SRC, /\{ id: "", label: "none", title: null \}/, "the none choice closes the group");
  assert.match(SRC, /if \(k === "todopick"\) this\.todoPick = t\.value;/, "the radio's change lands in todoPick");
  assert.match(SRC, /const todoId = this\.chosenTodoId\(s\);/, "the send asks the one chooser");
  assert.match(SRC, /if \(todoId\) msg\.todoId = todoId;/);
  assert.match(SRC, /if \(todoId && reply\.todoStamped\) answeredTodos\.add\(todoId\);/, "the latch is the stamp, not the attempt");
  assert.doesNotMatch(SRC, /todoAnswered/, "the per-viewer flag is gone: answeredTodos is the one memory, for every candidate alike");
  assert.match(SRC, /todoChoices\(this\.ctx\.todoId, s, \(id\) => answeredTodos\.has\(id\)\)/);
  // the radio's focus is re-found by option AND value after a re-render, so the picked radio keeps the keyboard
  assert.match(SRC, /id: a\.dataset\.opt === "todopick" \? \(a as HTMLInputElement\)\.value : undefined/);
  assert.match(SRC, /return \(k\.id === undefined \? all\[0\] : all\.find\(\(n\) => \(n as HTMLInputElement\)\.value === k\.id\)\) \|\| null;/);
});
