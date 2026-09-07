// A file path in a user todo's ONE-LINE text is a link, the way a path in its detail already is (the
// user 2026-09-07: sessions often put the path in the line itself, and then the line gave no way to open
// the file). One matcher and one span for both (path-links.ts linkifyPathTokens / openPathLink), applied
// by the function each host already used for the detail: waiting.ts's linkTodoPaths on the row's text and
// the Reply modal's quoted line, render.ts's linkTodoLinePaths (the chat's binder, no figure pass) on the
// todo card's text and its Reply modal's quoted line. The grammar is the detail's, not a wider one: an
// absolute, ~/, ./ or ../ path, a relative path whose last segment has an extension, or a file:// URI. A
// ":line" suffix is not part of it, so the path before the colon links and the suffix stays text, on the
// line exactly as in the detail.
//
// The matcher runs for real over a DOM stand-in (the user-todo-links.test.ts idiom; there is no jsdom),
// and the click tests run the real delegate() from actions.ts with the openpath handlers lifted out of
// waiting.ts's source and transpiled (the waiting-detail-link.test.ts idiom): a link inside the fold's
// click target (.ut-text, data-act uttoggle) opens the file and does not fold; a click on the text beside
// it folds and opens nothing. Both hosts' wiring is pinned at source.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const requireCjs = createRequire(__filename);
const UI = path.resolve(process.cwd(), "..", "ui", "webview");
const read = (f: string) => fs.readFileSync(path.join(UI, f), "utf8");
const WAITING = read("waiting.ts");
const RENDER = read("render.ts");

// synthetic world: the notes-api demo, placeholder ids, paths under /tmp/TESTHOST
const SID = "11111111-2222-3333-4444-555555555555";
const TID = "t1";

// ── a DOM stand-in for the walk AND the delegate: text nodes in document order, closest() over tag
// names, classes and data-attribute selectors (comma lists too), contains(), classList (flash), click
// listeners with bubbling by target
class TextNode {
  parentElement: Elm | null = null;
  constructor(public data: string) {}
  replaceWith(frag: Frag): void {
    const p = this.parentElement!;
    const i = p.childNodes.indexOf(this);
    const kids = frag.childNodes.map((c) => (typeof c === "string" ? new TextNode(c) : c));
    for (const k of kids) k.parentElement = p;
    p.childNodes.splice(i, 1, ...kids);
  }
}
class Frag { childNodes: (Elm | TextNode | string)[] = []; appendChild(c: Elm | TextNode | string) { this.childNodes.push(c); } }
class Elm {
  className = ""; title = ""; dataset: Record<string, string> = {}; parentElement: Elm | null = null;
  childNodes: (Elm | TextNode)[] = [];
  listeners: Record<string, Array<(ev: unknown) => void>> = {};
  classes = new Set<string>();
  classList = { add: (c: string) => { this.classes.add(c); }, remove: (c: string) => { this.classes.delete(c); }, contains: (c: string) => this.classes.has(c) };
  get offsetWidth(): number { return 0; }
  constructor(public tagName: string) {}
  set textContent(s: string) { const t = new TextNode(s); t.parentElement = this; this.childNodes = [t]; }
  get textContent(): string { return this.childNodes.map((c) => (c instanceof TextNode ? c.data : c.textContent)).join(""); }
  appendChild(c: Elm | TextNode): Elm | TextNode { c.parentElement = this; this.childNodes.push(c); return c; }
  matchesOne(sel: string): boolean {
    if (sel.startsWith(".")) return this.className.split(/\s+/).includes(sel.slice(1));
    const attr = sel.match(/^\[data-([\w-]+)\]$/);
    if (attr) return this.dataset[attr[1].replace(/-(\w)/g, (_, c: string) => c.toUpperCase())] !== undefined;
    return this.tagName === sel;
  }
  matches(sel: string): boolean { return sel.split(",").some((s) => this.matchesOne(s.trim())); }
  closest(sel: string): Elm | null {
    for (let n: Elm | null = this; n; n = n.parentElement) if (n.matches(sel)) return n;
    return null;
  }
  contains(other: Elm): boolean { for (let n: Elm | null = other; n; n = n.parentElement) if (n === this) return true; return false; }
  addEventListener(type: string, fn: (ev: unknown) => void): void { (this.listeners[type] ||= []).push(fn); }
  click(target: Elm): void { for (const fn of this.listeners.click || []) fn({ target }); }
  get spans(): Elm[] { return this.childNodes.filter((c): c is Elm => c instanceof Elm); }
  get texts(): string[] { return this.childNodes.filter((c): c is TextNode => c instanceof TextNode).map((c) => c.data); }
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

// the line as rowEl builds it, marked by the real matcher with the todo's session
async function line(text: string, cls = "ut-text"): Promise<Elm> {
  const { linkifyPathTokens } = await import("./path-links");
  const t = new Elm(cls === "ut-text" ? "span" : "div"); t.className = cls;
  t.textContent = text;
  linkifyPathTokens(t as unknown as HTMLElement, SID);
  return t;
}

test("a path in the line becomes the link; the words around it stay text, with the todo's session on the span", async () => {
  const t = await line("Review docs/design.md before I go on");
  assert.equal(t.spans.length, 1);
  assert.equal(t.spans[0].className, "file-uri-link");
  assert.equal(t.spans[0].textContent, "docs/design.md", "shown as written");
  assert.deepEqual(t.spans[0].dataset, { act: "openpath", path: "docs/design.md", rel: "1", sid: SID });
  assert.deepEqual(t.texts, ["Review ", " before I go on"]);
  assert.equal(t.textContent, "Review docs/design.md before I go on", "the line reads exactly as written");
});

test("a :line suffix is outside the grammar: the path links and the suffix stays text, on the line as in the detail", async () => {
  const src = "Fix the null check in /tmp/TESTHOST/notes-api/app.py:42";
  const t = await line(src);
  assert.deepEqual(t.spans.map((s) => s.dataset.path), ["/tmp/TESTHOST/notes-api/app.py"]);
  assert.deepEqual(t.texts, ["Fix the null check in ", ":42"]);
  // the detail, through the same function, reads the same text the same way: one grammar, no wider one for the line
  const d = await line(src, "ut-detail");
  assert.deepEqual(d.spans.map((s) => s.dataset.path), t.spans.map((s) => s.dataset.path));
  assert.deepEqual(d.texts, t.texts);
});

test("a line with no path is left alone: no spans, one text node, nothing spliced", async () => {
  const t = await line("Decide between the two layouts and/or say why");
  assert.deepEqual(t.spans, []);
  assert.deepEqual(t.texts, ["Decide between the two layouts and/or say why"]);
});

test("paths inside other words and punctuation: the ~/ form, the ./ form and a file:// URI each link, the prose around them stays", async () => {
  const src = "Approve ~/notes-api/README.md, then merge (see ./notes/plan.md or file:///tmp/TESTHOST/out%20dir/a.png).";
  const t = await line(src);
  assert.deepEqual(t.spans.map((s) => s.textContent), ["~/notes-api/README.md", "./notes/plan.md", "file:///tmp/TESTHOST/out%20dir/a.png"], "shown as written");
  assert.deepEqual(t.spans.map((s) => s.dataset.path), ["~/notes-api/README.md", "./notes/plan.md", "/tmp/TESTHOST/out dir/a.png"], "what a click opens");
  assert.deepEqual(t.spans.map((s) => s.dataset.sid), [SID, SID, undefined], "a bare path carries the todo's session; a URI is absolute");
  assert.deepEqual(t.texts, ["Approve ", ", then merge (see ", " or ", ")."]);
  assert.equal(t.textContent, src);
});

test("a line with < or & reaches the DOM as characters: text set as text and split into nodes, never parsed as markup", async () => {
  const src = "Check <docs/a.md> & docs/b.md";
  const t = await line(src);
  assert.deepEqual(t.spans.map((s) => s.dataset.path), ["docs/a.md", "docs/b.md"]);
  assert.deepEqual(t.texts, ["Check <", "> & "]);
  assert.equal(t.textContent, src);
  // and no markup path exists in either host's todo rendering: textContent first, the linkers after
  const row = WAITING.slice(WAITING.indexOf("function rowEl("), WAITING.indexOf("function hostLine("));
  const modal = WAITING.slice(WAITING.indexOf("function showReply("), WAITING.indexOf("// ── render"));
  const card = RENDER.slice(RENDER.indexOf('const head = el("div", "todo-head ut-head");'), RENDER.indexOf("card.appendChild(row);"));
  const rmodal = RENDER.slice(RENDER.indexOf("function showUserTodoReply("), RENDER.indexOf('input.className = "ut-reply-input"'));
  for (const [name, src2] of [["waiting.ts rowEl", row], ["waiting.ts showReply", modal], ["render.ts todo card", card], ["render.ts showUserTodoReply", rmodal]] as const) {
    assert.ok(src2.length > 200, name + ": slice found");
    assert.doesNotMatch(src2, /innerHTML|outerHTML|insertAdjacentHTML/, name);
  }
  assert.match(row, /txt\.textContent = w\.todo\.text;/);
  assert.match(card, /txt\.textContent = t\.text;/);
});

// ── the click, through the real delegate: the list's openpath handler and the Reply modal's, lifted
// out of waiting.ts's source and transpiled at run time (esbuild is required dynamically so the test
// bundle does not bundle it)
type Handler = (x: Elm) => void;
type Opened = [string, string, string];
function transpile(src: string): string { return requireCjs("esbuild").transformSync(src, { loader: "ts" }).code; }
function listHandler(opened: Opened[]): Handler {
  const map = WAITING.slice(WAITING.indexOf("delegate(list, {"), WAITING.indexOf("// A tap anywhere that is NOT an armed Dismiss"));
  const at = map.indexOf("\n    openpath: (x) => {");
  const end = map.indexOf("\n    },", at);
  assert.ok(at > 0 && end > at, "anchors not found: the list delegate's openpath moved; re-anchor");
  const src = map.slice(at, end + "\n    }".length).trim().replace(/^openpath:\s*/, "");
  const fn = new Function("openTodoPath", transpile("const h = " + src + ";") + "\nreturn h;");
  return fn((p: string, sid: string, tid: string) => opened.push([p, sid, tid])) as Handler;
}
function modalHandler(opened: Opened[], sid: string, todoId: string): Handler {
  const ln = WAITING.split("\n").find((l) => l.includes("delegate(box, { openpath: "));
  assert.ok(ln, "anchor not found: the Reply modal's delegate moved; re-anchor");
  const src = ln!.slice(ln!.indexOf("openpath: ") + "openpath: ".length, ln!.lastIndexOf(" });"));
  const fn = new Function("openTodoPath", "sid", "todoId", transpile("const h = " + src + ";") + "\nreturn h;");
  return fn((p: string, s: string, t: string) => opened.push([p, s, t]), sid, todoId) as Handler;
}

// the row as rowEl builds it when the todo has detail: .ut-item[data-sid][data-tid] > .ut-line >
// .ut-text.ut-has-detail[data-act=uttoggle] (the linked line, then the "details" hint inside the same span)
async function rowWithDetail(list: Elm, text: string): Promise<{ txt: Elm; link: Elm; more: Elm }> {
  const item = new Elm("div"); item.className = "wt-item ut-item";
  item.dataset.sid = SID; item.dataset.tid = TID;
  const ln = new Elm("div"); ln.className = "ut-line";
  const txt = await line(text);
  txt.className = "ut-text ut-has-detail"; txt.dataset.act = "uttoggle"; txt.dataset.key = SID + "|" + TID;
  const more = new Elm("span"); more.className = "ut-more"; more.textContent = "details";
  txt.appendChild(more);
  ln.appendChild(txt); item.appendChild(ln); list.appendChild(item);
  return { txt, link: txt.spans[0], more };
}

test("a click on the line's link opens the file from the ROW's ids and does not fold; the text beside it folds and opens nothing", async () => {
  const { delegate } = await import("./actions");
  const opened: Opened[] = [];
  let folds = 0;
  const list = new Elm("div");
  delegate(list as unknown as HTMLElement, { openpath: listHandler(opened) as any, uttoggle: (() => { folds++; }) as any });   // installed once, on the stable root
  const { txt, link, more } = await rowWithDetail(list, "Review docs/design.md before I go on");
  assert.equal(link.dataset.act, "openpath", "the link is its own data-act, nested inside the fold's");
  list.click(link);
  assert.deepEqual(opened, [["docs/design.md", SID, TID]], "the click posts with the row's session and todo id");
  assert.equal(folds, 0, "the fold did not move: the nearest data-act wins (actions.ts)");
  assert.ok(link.classList.contains("romp-acted"), "the delegate's press flash on the link");
  list.click(txt);      // the plain text beside the link: the browser's target is the span itself
  assert.equal(folds, 1);
  list.click(more);     // the "details" hint: no data-act of its own, bubbles to .ut-text
  assert.equal(folds, 2);
  assert.equal(opened.length, 1, "neither fold click opened anything");
});

test("a todo with no detail: the line has no data-act, and its link still opens through the list delegate", async () => {
  const { delegate } = await import("./actions");
  const opened: Opened[] = [];
  const list = new Elm("div");
  delegate(list as unknown as HTMLElement, { openpath: listHandler(opened) as any });
  const item = new Elm("div"); item.className = "wt-item ut-item"; item.dataset.sid = SID; item.dataset.tid = TID;
  const ln = new Elm("div"); ln.className = "ut-line";
  const txt = await line("Look at /tmp/TESTHOST/notes-api/out.png and say if the axes read right");
  ln.appendChild(txt); item.appendChild(ln); list.appendChild(item);
  list.click(txt.spans[0]);
  assert.deepEqual(opened, [["/tmp/TESTHOST/notes-api/out.png", SID, TID]]);
  list.click(txt);
  assert.equal(opened.length, 1, "the plain text of a bare row is not a control");
});

test("the Reply modal's one delegate opens a link in the quoted line and one in the quoted detail alike, from its closure", async () => {
  const { delegate } = await import("./actions");
  const opened: Opened[] = [];
  const box = new Elm("div"); box.className = "picker-box confirm-box";
  const d = await line("Review docs/design.md before I go on", "confirm-detail ut-reply-quote");
  const dd = await line("The two layouts are in /tmp/TESTHOST/notes-api/layouts.md", "ut-detail open");
  box.appendChild(d); box.appendChild(dd);
  delegate(box as unknown as HTMLElement, { openpath: modalHandler(opened, SID, TID) as any });
  box.click(d.spans[0]);
  box.click(dd.spans[0]);
  assert.deepEqual(opened, [["docs/design.md", SID, TID], ["/tmp/TESTHOST/notes-api/layouts.md", SID, TID]]);
});

// ── parity at source: every site that links the detail links the line, on both hosts
test("both hosts apply their todo linker to the line AND the detail, at the row and in the Reply modal", () => {
  // waiting.ts: one function, four sites (the row's text and detail, the modal's quoted line and detail)
  const row = WAITING.slice(WAITING.indexOf("function rowEl("), WAITING.indexOf("function hostLine("));
  assert.match(row, /txt\.textContent = w\.todo\.text;\n\s*linkTodoPaths\(txt, w\.sid\);/);
  assert.match(row, /d\.textContent = w\.todo\.detail \|\| "";\n\s*linkTodoPaths\(d, w\.sid\);/);
  const modal = WAITING.slice(WAITING.indexOf("function showReply("), WAITING.indexOf("// ── render"));
  assert.match(modal, /d\.textContent = todoText;\n\s*linkTodoPaths\(d, sid\);/);
  assert.match(modal, /dd\.textContent = todoDetail;\n\s*linkTodoPaths\(dd, sid\);/);
  assert.equal((WAITING.match(/linkTodoPaths\(/g) || []).length, 5, "defined once, applied at the four sites");
  // render.ts: the line through linkTodoLinePaths (the chat's binder, no figure pass), the detail through
  // linkifyFileUris (the binder with the figure pass); both mark through path-links.ts and bind through bindPathLink
  assert.match(RENDER, /function linkTodoLinePaths\(node: HTMLElement, sid: string \| null\): void \{\n\s*for \(const \{ el: link \} of linkifyPathTokens\(node, sid\)\) bindPathLink\(link\);\n\}/);
  const card = RENDER.slice(RENDER.indexOf('const head = el("div", "todo-head ut-head");'), RENDER.indexOf("card.appendChild(row);"));
  assert.match(card, /txt\.textContent = t\.text;\n\s*linkTodoLinePaths\(txt, renderingSid \|\| null\);/);
  assert.match(card, /linkifyFileUris\(d, undefined, undefined, undefined, undefined, renderingSid \|\| null\);/);
  const cardLine = card.slice(card.indexOf('const txt = el("span", "ut-text");'), card.indexOf('const reply = el("button", "ut-btn ut-reply");'));
  assert.doesNotMatch(cardLine, /linkifyFileUris\(/, "no figure pass on a one-line row");
  const rmodal = RENDER.slice(RENDER.indexOf("function showUserTodoReply("), RENDER.indexOf('input.className = "ut-reply-input"'));
  assert.match(rmodal, /d\.textContent = todoText;\n\s*linkTodoLinePaths\(d, sid\);/);
  assert.match(rmodal, /dd\.textContent = todoDetail; linkifyFileUris\(dd, undefined, undefined, undefined, undefined, sid\);/);
  assert.equal((RENDER.match(/linkTodoLinePaths\(/g) || []).length, 3, "defined once, applied at the two line sites");
});
