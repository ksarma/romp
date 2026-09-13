// A file:// URI in a Waiting-on-you row's detail opens like a bare path does (plans/file-review.md,
// Slice 0; the 2026-09-06 review). path-links.ts stamps data-sid on a bare path's span and NOT on a
// file:// URI's — an absolute path names no session — and the list delegate's openpath used to gate on
// the span's sid, so a URI link took the delegate's press flash and then opened nothing, while the same
// link in the Reply modal (sid from its closure) worked. The handler now reads the session from the row,
// the way it always read the todo id. Everything here is EXECUTED: the real matcher marks the spans, the
// real delegate() dispatches the click, and both openpath handlers are lifted out of waiting.ts's source
// and transpiled — a source pin of the old handler is exactly what let the defect through.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { inspect } from "node:util";
import { hideEdges, staysEnumerable } from "../test-dom-shim";
import { linkTarget } from "./path-links";   // the lifted handlers read a link's target through it (Slice 6 of plans/markdown-viewer.md)

const requireCjs = createRequire(__filename);
const UI = path.resolve(process.cwd(), "..", "ui", "webview");
const WAITING = fs.readFileSync(path.join(UI, "waiting.ts"), "utf8");

// synthetic world: the notes-api demo, placeholder ids
const SID = "11111111-2222-3333-4444-555555555555";
const TID = "t1";
const DETAIL = "Please read docs/design.md and /tmp/notes-api/out.png (see file:///tmp/notes-api/notes%20v2.md).";
const OPENS = ["docs/design.md", "/tmp/notes-api/out.png", "/tmp/notes-api/notes v2.md"];

// ── a DOM stand-in for the walk AND the delegate: text nodes in document order, closest() over tag
// names, one class or one data-attribute selector, contains(), classList (flash), click listeners
class TextNode {
  parentElement: Elm | null = null;
  constructor(public data: string) { hideEdges(this); }
  replaceWith(frag: Frag): void {
    const p = this.parentElement!;
    const i = p.childNodes.indexOf(this);
    const kids = frag.childNodes.map((c) => (typeof c === "string" ? new TextNode(c) : c));
    for (const k of kids) k.parentElement = p;
    p.childNodes.splice(i, 1, ...kids);
  }
}
class Frag {
  childNodes!: (Elm | TextNode | string)[];
  constructor() { Object.defineProperty(this, "childNodes", { value: [], writable: true, enumerable: false, configurable: true }); hideEdges(this); }
  appendChild(c: Elm | TextNode | string) { this.childNodes.push(c); }
}
class Elm {
  className = ""; title = ""; dataset: Record<string, string> = {}; parentElement: Elm | null = null;
  // the class and the title as attributes, reflected to the properties (markPathLink writes them as attributes, for an SVG <a>'s sake)
  attrs: Record<string, string> = {};
  setAttribute(n: string, v: string): void { if (n === "class") this.className = v; else if (n === "title") this.title = v; else this.attrs[n] = v; }
  getAttribute(n: string): string | null { if (n === "class") return this.className || null; if (n === "title") return this.title || null; return n in this.attrs ? this.attrs[n] : null; }
  childNodes!: (Elm | TextNode)[];
  listeners: Record<string, Array<(ev: unknown) => void>> = {};
  classes = new Set<string>();
  classList = { add: (c: string) => { this.classes.add(c); }, remove: (c: string) => { this.classes.delete(c); }, contains: (c: string) => this.classes.has(c) };
  get offsetWidth(): number { return 0; }
  constructor(public tagName: string) {
    Object.defineProperty(this, "childNodes", { value: [], writable: true, enumerable: false, configurable: true });
    hideEdges(this);
  }
  set textContent(s: string) { const t = new TextNode(s); t.parentElement = this; this.childNodes = [t]; }
  get textContent(): string { return this.childNodes.map((c) => (c instanceof TextNode ? c.data : c.textContent)).join(""); }
  appendChild(c: Elm | TextNode): Elm | TextNode { c.parentElement = this; this.childNodes.push(c); return c; }
  matches(sel: string): boolean {
    if (sel.startsWith(".")) return this.className.split(/\s+/).includes(sel.slice(1));
    const attr = sel.match(/^\[data-([\w-]+)\]$/);
    if (attr) return this.dataset[attr[1].replace(/-(\w)/g, (_, c: string) => c.toUpperCase())] !== undefined;
    return this.tagName === sel;
  }
  closest(sel: string): Elm | null {
    for (let n: Elm | null = this; n; n = n.parentElement) if (n.matches(sel)) return n;
    return null;
  }
  contains(other: Elm): boolean { for (let n: Elm | null = other; n; n = n.parentElement) if (n === this) return true; return false; }
  addEventListener(type: string, fn: (ev: unknown) => void): void { (this.listeners[type] ||= []).push(fn); }
  click(target: Elm): void { for (const fn of this.listeners.click || []) fn({ target }); }
  get spans(): Elm[] { return this.childNodes.filter((c): c is Elm => c instanceof Elm); }
}
function textNodesOf(root: Elm): TextNode[] {
  const out: TextNode[] = [];
  const walk = (n: Elm) => { for (const c of n.childNodes) { if (c instanceof TextNode) out.push(c); else walk(c); } };
  walk(root);
  return out;
}
(globalThis as any).NodeFilter = { SHOW_TEXT: 4 };
(globalThis as any).document = {
  createElement: (tag: string) => new Elm(tag),
  createTextNode: (s: string) => s,
  createDocumentFragment: () => new Frag(),
  createTreeWalker: (root: Elm) => { const nodes = textNodesOf(root); let i = 0; return { nextNode: () => (i < nodes.length ? nodes[i++] : null) }; },
};

// ── the two openpath handlers, lifted out of waiting.ts and transpiled (TS → JS) at run time; esbuild
// is required dynamically so the test bundle does not try to bundle it (the models-rev.test.ts idiom)
type Handler = (x: Elm) => void;
type Opened = [string, string, string];
function transpile(src: string): string { return requireCjs("esbuild").transformSync(src, { loader: "ts" }).code; }
function listHandler(opened: Opened[]): Handler {
  const map = WAITING.slice(WAITING.indexOf("delegate(list, {"), WAITING.indexOf("// A tap anywhere that is NOT an armed Dismiss"));
  const at = map.indexOf("\n    openpath: (x) => {");
  const end = map.indexOf("\n    },", at);
  assert.ok(at > 0 && end > at, "anchors not found — the list delegate's openpath moved; re-anchor");
  const src = map.slice(at, end + "\n    }".length).trim().replace(/^openpath:\s*/, "");
  const fn = new Function("openTodoPath", "linkTarget", transpile("const h = " + src + ";") + "\nreturn h;");
  return fn((p: string, sid: string, tid: string) => opened.push([p, sid, tid]), linkTarget) as Handler;
}
function modalHandler(opened: Opened[], sid: string, todoId: string): Handler {
  const line = WAITING.split("\n").find((l) => l.includes("delegate(box, { openpath: "));
  assert.ok(line, "anchor not found — the Reply modal's delegate moved; re-anchor");
  const src = line!.slice(line!.indexOf("openpath: ") + "openpath: ".length, line!.lastIndexOf(" });"));
  const fn = new Function("openTodoPath", "sid", "todoId", "linkTarget", transpile("const h = " + src + ";") + "\nreturn h;");
  return fn((p: string, s: string, t: string) => opened.push([p, s, t]), sid, todoId, linkTarget) as Handler;
}

// the row as rowEl builds it: .wt-item.ut-item[data-sid][data-tid] > .ut-detail, the detail's text
// marked by the real matcher with the todo's session
async function row(list: Elm): Promise<{ item: Elm; spans: Elm[] }> {
  const { linkifyPathTokens } = await import("./path-links");
  const item = new Elm("div"); item.className = "wt-item ut-item";
  item.dataset.sid = SID; item.dataset.tid = TID;
  const d = new Elm("div"); d.className = "ut-detail open";
  d.textContent = DETAIL;
  linkifyPathTokens(d as unknown as HTMLElement, SID);
  item.appendChild(d);
  list.appendChild(item);
  return { item, spans: d.spans };
}

test("every path in a row's detail opens through the list delegate — the file:// URI too, from the row's session", async () => {
  const { delegate } = await import("./actions");
  const opened: Opened[] = [];
  const list = new Elm("div");
  delegate(list as unknown as HTMLElement, { openpath: listHandler(opened) as any });   // installed once, on the stable root
  const { spans } = await row(list);
  assert.equal(spans.length, 3, "the relative path, the absolute path and the URI all marked");
  assert.deepEqual(spans.map((s) => s.dataset.sid), [SID, SID, undefined], "path-links.ts's contract: the URI span carries no sid");
  for (const s of spans) list.click(s);
  assert.deepEqual(opened, OPENS.map((p): Opened => [p, SID, TID]), "each click posts with the ROW's session and todo id");
  assert.ok(spans.every((s) => s.classList.contains("romp-acted")), "the delegate's press flash on each");
});

test("the Reply modal's own delegate opens the same three spans with its closure's session", async () => {
  const { linkifyPathTokens } = await import("./path-links");
  const opened: Opened[] = [];
  const dd = new Elm("div"); dd.className = "ut-detail open";
  dd.textContent = DETAIL;
  linkifyPathTokens(dd as unknown as HTMLElement, SID);
  const h = modalHandler(opened, SID, TID);
  for (const s of dd.spans) h(s);
  assert.deepEqual(opened, OPENS.map((p): Opened => [p, SID, TID]));
});

// A target after the path (Slice 6 of plans/markdown-viewer.md): waiting.ts marks a todo's detail with `targetSuffix`, so
// `docs/report.md#results` carries data-frag and `docs/report.md:12` data-line; both delegates read them through
// path-links.ts linkTarget and hand openTodoPath the target as its fourth argument, which rides the relay as `at`.
type OpenedAt = [string, string, string, unknown];
test("a target after a detail's path reaches openTodoPath from both delegates: a heading, a line, and nothing for a bare path", async () => {
  const { linkifyPathTokens } = await import("./path-links");
  const { delegate } = await import("./actions");
  const withAt = (opened: OpenedAt[]) => (p: string, sid: string, tid: string, at: unknown) => opened.push([p, sid, tid, at]);
  const text = "read docs/report.md#results, then docs/report.md:12 and docs/design.md";
  const mark = (d: Elm) => { d.textContent = text; linkifyPathTokens(d as unknown as HTMLElement, SID, undefined, { targetSuffix: true }); };
  const want: OpenedAt[] = [["docs/report.md", SID, TID, { heading: "results" }], ["docs/report.md", SID, TID, { line: 12 }], ["docs/design.md", SID, TID, null]];
  // the list: the lifted handler over the row's ids
  const listOpened: OpenedAt[] = [];
  const map = WAITING.slice(WAITING.indexOf("delegate(list, {"), WAITING.indexOf("// A tap anywhere that is NOT an armed Dismiss"));
  const at = map.indexOf("\n    openpath: (x) => {"), end = map.indexOf("\n    },", at);
  const src = map.slice(at, end + "\n    }".length).trim().replace(/^openpath:\s*/, "");
  const listH = new Function("openTodoPath", "linkTarget", transpile("const h = " + src + ";") + "\nreturn h;")(withAt(listOpened), linkTarget) as Handler;
  const list = new Elm("div");
  delegate(list as unknown as HTMLElement, { openpath: listH as any });
  const item = new Elm("div"); item.className = "wt-item ut-item"; item.dataset.sid = SID; item.dataset.tid = TID;
  const d = new Elm("div"); d.className = "ut-detail open"; mark(d); item.appendChild(d); list.appendChild(item);
  assert.deepEqual(d.spans.map((x) => [x.textContent, x.dataset.line, x.dataset.frag]), [["docs/report.md#results", undefined, "results"], ["docs/report.md:12", "12", undefined], ["docs/design.md", undefined, undefined]],
    "the shown text keeps the suffix; the attributes carry it");
  for (const x of d.spans) list.click(x);
  assert.deepEqual(listOpened, want);
  // the Reply modal: its one-line delegate over its closure
  const modalOpened: OpenedAt[] = [];
  const line = WAITING.split("\n").find((l) => l.includes("delegate(box, { openpath: "))!;
  const msrc = line.slice(line.indexOf("openpath: ") + "openpath: ".length, line.lastIndexOf(" });"));
  const modalH = new Function("openTodoPath", "sid", "todoId", "linkTarget", transpile("const h = " + msrc + ";") + "\nreturn h;")(withAt(modalOpened), SID, TID, linkTarget) as Handler;
  const dd = new Elm("div"); dd.className = "ut-detail open"; mark(dd);
  for (const x of dd.spans) modalH(x);
  assert.deepEqual(modalOpened, want);
  // the source: waiting.ts marks with targetSuffix and reads through linkTarget at both sites
  assert.match(WAITING, /linkifyPathTokens\(node, sid, undefined, \{ targetSuffix: true \}\);/);
  assert.equal((WAITING.match(/linkTarget\(x\)/g) || []).length, 2, "both delegates read the target off the clicked link");
  assert.match(WAITING, /import \{ linkTarget, type LinkTarget \} from "\.\/path-links";/);
});

test("a marked span with no row around it is a no-op in the list: the row is the source of both ids", async () => {
  const { linkifyPathTokens } = await import("./path-links");
  const opened: Opened[] = [];
  const h = listHandler(opened);
  const stray = new Elm("div"); stray.textContent = "see docs/design.md";
  linkifyPathTokens(stray as unknown as HTMLElement, SID);
  h(stray.spans[0]);                     // sid on the span, but no .ut-item to name the todo
  assert.deepEqual(opened, []);
});

// The projection rule (ui/test-dom-shim.ts, hideEdges): a stand-in node enumerates its primitives alone, so a failing
// assertion's dump of one stops at the node instead of walking the whole tree through its edges.
test("a stand-in node enumerates its primitives alone, and a dump of it names neither parentNode, parentElement nor childNodes", () => {
  const root = new Elm("div"); const kid = new Elm("span"); root.appendChild(kid); kid.appendChild(new TextNode("x"));
  const nodes = [root, kid, kid.childNodes[0]];
  for (const n of nodes) {
    assert.ok(Object.keys(n).every((k) => staysEnumerable((n as any)[k])), "every enumerable own key holds a primitive");
    const dump = inspect(n, { compact: false, customInspect: false, depth: 1000, maxArrayLength: Infinity, showHidden: false, showProxy: false, sorted: true, getters: true });
    assert.ok(!dump.includes("parentNode") && !dump.includes("parentElement") && !dump.includes("childNodes"), "the dump stops at the node");
  }
});
