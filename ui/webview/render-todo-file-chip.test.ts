// The chat's split to-do card and its Reply modal show the file a user todo NAMES (plans/file-review.md,
// "The todo-file follow-on (2026-09-07)"), RUN: render.ts's renderTodo, showUserTodoReply and todoFileChip
// lifted out of the source and transpiled, executed under a DOM stand-in with the real path-links.ts
// linkifier, the real user-todo-hint.ts and the real delegate() from actions.ts, the body delegate's
// openpath and utreply handlers lifted from the same source (the user-todo-title-links.test.ts idiom;
// there is no jsdom in this tree).
//
// A todo's `file` — the absolute path the kernel resolved when the todo was filed, riding the todo event's
// userTodos rows — is a chip trailing the row's text and the modal's quoted line: the basename as the
// label, the full path on hover, a path link the body delegate opens against the todo's OWN session. Before
// this the chat surface read only text and detail, so a todo filed the way the session prompt now says (the
// path as `file`, the detail merely describing it) had no clickable file on the card or in its modal, while
// the Waiting-on-you pane had its chip (waiting-file-chip.test.ts); the review of 2026-09-07 found it.
// Synthetic only: the notes-api world, placeholder sids, paths under /tmp/TESTHOST.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { LINK_SEL, linkHref, isMarkdownUrl, browserTabClick } from "./md-links";   // what the chat's anchor opener names from its siblings
import { userContentTarget } from "./md-sanitize";

const requireCjs = createRequire(__filename);
const UI = path.resolve(process.cwd(), "..", "ui", "webview");
const RENDER = fs.readFileSync(path.join(UI, "render.ts"), "utf8");

const SID = "11111111-2222-3333-4444-555555555555";       // the session that filed the todo (the card's renderingSid)
const ACTIVE = "66666666-7777-8888-9999-000000000000";    // a different active tab, so a click's session is provably the todo's
const TID = "t1";
const FILE = "/tmp/TESTHOST/notes-api/docs/report.md";
const TEXT = "Need a look at the findings report";
const DETAIL = "the summary section reads as too confident";
const EV = { kind: "todo", tasks: [], userTodos: [{ id: TID, text: TEXT, detail: DETAIL, createdT: 1, file: FILE }] };

// ── a DOM stand-in: elements with children in order, text nodes the path walk splices, class/id/data
// selectors for closest() and querySelector(), and click dispatch to a root's listeners by target
class TextNode {
  nodeType = 3;
  parentElement: Elm | null = null;
  constructor(public data: string) {}
  get textContent(): string { return this.data; }
  replaceWith(frag: Frag): void {
    const p = this.parentElement!;
    const i = p.childNodes.indexOf(this);
    for (const k of frag.childNodes) k.parentElement = p;
    p.childNodes.splice(i, 1, ...frag.childNodes);
    this.parentElement = null;
  }
}
class Frag { childNodes: Kid[] = []; appendChild(c: Kid): Kid { this.childNodes.push(c); return c; } }
type Kid = Elm | TextNode;
type Compound = { tag: string | null; id: string | null; classes: string[]; attrs: { name: string; value: string | null }[] };
const camel = (s: string) => s.replace(/-([a-z])/g, (_, c: string) => c.toUpperCase());
function parseCompound(s: string): Compound {
  const c: Compound = { tag: null, id: null, classes: [], attrs: [] };
  const m = /^([a-zA-Z][\w-]*)?(.*)$/.exec(s)!;
  c.tag = m[1] ? m[1].toLowerCase() : null;
  const re = /\.([\w-]+)|#([\w-]+)|\[(?:\*\|)?([\w-]+)(?:="([^"]*)")?\]/g;   // `[*|href]` (any namespace) reads as `[href]`: the stand-in has one
  let t: RegExpExecArray | null;
  while ((t = re.exec(m[2]))) {
    if (t[1]) c.classes.push(t[1]); else if (t[2]) c.id = t[2]; else c.attrs.push({ name: t[3], value: t[4] ?? null });
  }
  return c;
}
class Elm {
  nodeType = 1;
  tagName: string;
  className = ""; title = ""; id = ""; role = ""; tabIndex = -1; type = ""; placeholder = ""; rows = 0; value = "";
  dataset: Record<string, string | undefined> = {};
  parentElement: Elm | null = null;
  childNodes: Kid[] = [];
  listeners: Record<string, Array<(ev: unknown) => void>> = {};
  attrs: Record<string, string> = {};
  onkeydown: unknown = null; onmousedown: unknown = null; onmouseup: unknown = null; onmouseleave: unknown = null; oncontextmenu: unknown = null; ondragstart: unknown = null;
  classList = {
    add: (...cs: string[]) => { const s = this.classes(); for (const c of cs) s.add(c); this.className = [...s].join(" "); },
    remove: (...cs: string[]) => { const s = this.classes(); for (const c of cs) s.delete(c); this.className = [...s].join(" "); },
    toggle: (c: string, force?: boolean) => { const s = this.classes(); const on = force === undefined ? !s.has(c) : force; if (on) s.add(c); else s.delete(c); this.className = [...s].join(" "); return on; },
    contains: (c: string) => this.classes().has(c),
  };
  constructor(tag: string) { this.tagName = tag.toLowerCase(); }
  private classes(): Set<string> { return new Set(this.className.split(/\s+/).filter(Boolean)); }
  get offsetWidth(): number { return 0; }
  get textContent(): string { return this.childNodes.map((c) => c.textContent).join(""); }
  set textContent(s: string) { for (const c of this.childNodes) c.parentElement = null; this.childNodes = s ? [this.adopt(s)] : []; }
  private adopt(c: Kid | string): Kid {
    const n = typeof c === "string" ? new TextNode(c) : c;
    const p = n.parentElement; if (p) p.childNodes.splice(p.childNodes.indexOf(n), 1);   // moving a node re-parents it, as the DOM does
    n.parentElement = this; return n;
  }
  appendChild<T extends Kid>(c: T): T { this.childNodes.push(this.adopt(c)); return c; }
  append(...cs: Array<Kid | string>): void { for (const c of cs) this.childNodes.push(this.adopt(c)); }
  remove(): void { const p = this.parentElement; if (!p) return; p.childNodes.splice(p.childNodes.indexOf(this), 1); this.parentElement = null; }
  matchesOne(sel: string): boolean {
    const c = parseCompound(sel.trim());
    if (c.tag && c.tag !== this.tagName) return false;
    if (c.id && c.id !== this.id) return false;
    if (!c.classes.every((k) => this.classList.contains(k))) return false;
    for (const a of c.attrs) {
      const v = a.name.startsWith("data-") ? this.dataset[camel(a.name.slice(5))] : this.attrs[a.name];
      if (v === undefined || (a.value !== null && v !== a.value)) return false;
    }
    return true;
  }
  /** a selector list of compounds, each possibly a descendant chain (`.ut-item [data-tid="x"]`) */
  matches(sel: string): boolean {
    return sel.split(",").some((s) => {
      const chain = s.trim().split(/\s+/);
      if (!this.matchesOne(chain[chain.length - 1])) return false;
      let anc: Elm | null = this.parentElement;
      for (let i = chain.length - 2; i >= 0; i--) { while (anc && !anc.matchesOne(chain[i])) anc = anc.parentElement; if (!anc) return false; anc = anc.parentElement; }
      return true;
    });
  }
  closest(sel: string): Elm | null { for (let n: Elm | null = this; n; n = n.parentElement) if (n.matches(sel)) return n; return null; }
  contains(other: Kid | null): boolean { for (let n: Kid | null = other; n; n = n.parentElement) if (n === this) return true; return false; }
  querySelector(sel: string): Elm | null { return all(this, (e) => e.matches(sel))[0] ?? null; }
  querySelectorAll(sel: string): Elm[] { return all(this, (e) => e.matches(sel)); }
  addEventListener(type: string, fn: (ev: unknown) => void): void { (this.listeners[type] ||= []).push(fn); }
  removeEventListener(type: string, fn: (ev: unknown) => void): void { this.listeners[type] = (this.listeners[type] || []).filter((f) => f !== fn); }
  setAttribute(k: string, v: string): void { this.attrs[k] = v; }
  getAttribute(k: string): string | null { return k in this.attrs ? this.attrs[k] : null; }
  hasAttribute(k: string): boolean { return k in this.attrs; }
  removeAttribute(k: string): void { delete this.attrs[k]; }
  focus(): void { /* a stand-in takes no focus */ }
  /** the browser's dispatch for a click that bubbled to THIS root: its listeners, with the pressed node as target */
  click(target: Elm): void { for (const fn of this.listeners.click || []) fn({ target }); }
}
/** every element under root, in document order, that pred admits */
function all(root: Elm, pred: (e: Elm) => boolean): Elm[] {
  const out: Elm[] = [];
  const walk = (n: Elm) => { for (const c of n.childNodes) if (c instanceof Elm) { if (pred(c)) out.push(c); walk(c); } };
  walk(root);
  return out;
}
function one(root: Elm, pred: (e: Elm) => boolean, what: string): Elm {
  const hits = all(root, pred);
  assert.equal(hits.length, 1, "exactly one " + what);
  return hits[0];
}
const hasClass = (c: string) => (e: Elm) => e.classList.contains(c);
function textNodesOf(root: Elm): TextNode[] {
  const out: TextNode[] = [];
  const walk = (n: Elm) => { for (const c of n.childNodes) { if (c instanceof TextNode) out.push(c); else walk(c); } };
  walk(root);
  return out;
}
const doc = {
  body: new Elm("body"),
  activeElement: null as Elm | null,
  createElement: (tag: string) => new Elm(tag),
  createTextNode: (s: string) => new TextNode(s),
  createDocumentFragment: () => new Frag(),
  createTreeWalker: (root: Elm) => { const nodes = textNodesOf(root); let i = 0; return { nextNode: () => (i < nodes.length ? nodes[i++] : null) }; },
  getElementById: (id: string): Elm | null => all(doc.body, (e) => e.id === id)[0] ?? null,
  querySelector: (sel: string): Elm | null => doc.body.querySelector(sel),
  addEventListener(): void { /* the modal's Escape handler: not exercised */ },
  removeEventListener(): void { /* … */ },
  contains: (e: Kid | null) => doc.body.contains(e),
};
(globalThis as any).NodeFilter = { SHOW_TEXT: 4 };
(globalThis as any).document = doc;
/** a fresh body per test: the delegate installs on the stable root once, and the modal appends to body */
function freshBody(): Elm { doc.body = new Elm("body"); return doc.body; }

// ── the chat host, lifted out of render.ts and transpiled (esbuild is required dynamically so the test
// bundle does not bundle it): the card, the modal, the chip, the line/detail linkers, openLinkedPath, and the
// body delegate's openpath and utreply handlers; the chat's module state comes in as arguments
function transpile(src: string): string { return requireCjs("esbuild").transformSync(src, { loader: "ts" }).code; }
function liftRender(name: string): string {
  const at = RENDER.indexOf("\nfunction " + name + "(");
  const end = RENDER.indexOf("\n}\n", at);
  assert.ok(at > 0 && end > at, "anchor not found: render.ts's " + name + " moved; re-anchor");
  return RENDER.slice(at, end + 3);
}
function bodyHandler(act: string): string {
  const map = RENDER.slice(RENDER.indexOf("delegate(document.body, {"), RENDER.indexOf("delegate(tabs, {"));
  const at = map.indexOf("\n    " + act + ": (");
  assert.ok(at > 0, "anchor not found: the body delegate's " + act + " moved; re-anchor");
  const line = map.slice(at + 1, map.indexOf("\n", at + 1));
  if (/,\s*$/.test(line) && !/\{\s*$/.test(line)) return line.trim().replace(new RegExp("^" + act + ":\\s*"), "").replace(/,$/, "");   // a one-liner
  const end = map.indexOf("\n    },", at);
  assert.ok(end > at, "anchor not found: the body delegate's " + act + " has no close; re-anchor");
  return map.slice(at, end + "\n    }".length).trim().replace(new RegExp("^" + act + ":\\s*"), "");
}
type Opened = [string, string | null];
type Handler = (el: Elm, ev: unknown) => void;
interface Host {
  renderTodo: (ev: unknown) => Elm;
  showUserTodoReply: (sid: string, todoId: string, todoText: string, todoDetail?: string, todoFile?: string, todoLink?: string) => void;
  todoFileChip: (file: string, sid: string | null) => Elm;
  todoLinkChip: (link: string) => Elm;
  openpath: Handler;
  utreply: Handler;
  opened: Opened[];
}
async function host(activeId: string | null = ACTIVE): Promise<Host> {
  const { linkifyPathTokens, openPathLink } = await import("./path-links");
  const { linkifyUrls, urlChip } = await import("./url-links");   // the URL pass the linkers run first, and the link chip's anchor (2026-09-08)
  const hint = await import("./user-todo-hint");
  const opened: Opened[] = [];
  const code = transpile([
    liftRender("todoFileChip"), liftRender("todoLinkChip"), liftRender("linkTodoLinePaths"), liftRender("linkTodoDetailPaths"),
    liftRender("renderTodo"), liftRender("showUserTodoReply"), liftRender("openLinkedPath"),
    "const openpath = " + bodyHandler("openpath") + ";",
    "const utreply = " + bodyHandler("utreply") + ";",
  ].join("\n"));
  const fn = new Function(
    "el", "dot", "applyFold", "rememberFold", "utDetailHint", "applyUtHint", "utHintFor", "UT_HINT_CLASS",
    "linkifyPrRefs", "prRepoFor", "isCoarsePointer", "renderingSid", "utDetailOpen", "linkifyPathTokens", "linkifyFileUris",
    "openPathLink", "vscodeApi", "activeId", "openPath", "linkifyUrls", "urlChip",
    code + "\nreturn { renderTodo, showUserTodoReply, todoFileChip, todoLinkChip, openpath, utreply };");
  const el = (tag: string, cls?: string) => { const e = document.createElement(tag); if (cls) e.className = cls; return e; };
  const out = fn(
    el, () => el("span", "dot ring"), () => undefined, () => undefined, hint.utDetailHint, hint.applyUtHint, hint.utHintFor, hint.UT_HINT_CLASS,
    () => undefined, () => null, () => false, SID, new Set<string>(), linkifyPathTokens,
    (node: HTMLElement, _a: unknown, _b: unknown, _c: unknown, _d: unknown, sid: string | null) => linkifyPathTokens(node, sid),   // the detail's figure pass is not under test: its paths link the same way
    openPathLink, null, activeId,
    (p: string, sid: string | null) => opened.push([p, sid]),
    linkifyUrls, urlChip,
  );
  return { ...out, opened };
}

test("a todo that names its file: the card's row trails the text with the chip — the basename, the full path on hover, a path link marked with the todo's session — and the Reply button carries the file", async () => {
  const h = await host();
  const turn = h.renderTodo(EV);
  const links = all(turn, hasClass("file-uri-link"));
  assert.equal(links.length, 1, "no path in the text or the detail: the chip is the one link on the card");
  const chip = links[0];
  assert.ok(chip.classList.contains("ut-file"), "named for the sheet");
  assert.equal(chip.tagName, "span");
  assert.equal(chip.textContent, "report.md", "the basename is the label");
  assert.equal(chip.title, FILE, "the full path on hover");
  assert.deepEqual(chip.dataset, { act: "openpath", path: FILE, rel: "1", sid: SID }, "a path link the body delegate opens, with the todo's session");
  assert.equal(chip.tabIndex, 0, "in the tab order, as every path link is");
  assert.equal(chip.childNodes.length, 1, "the label is one text node: the linkifiers ran before it and never scanned it");
  // where it sits: inside the text span — the fold's click target — after the text and before the "details" hint
  const txt = chip.parentElement!;
  assert.equal(txt.className, "ut-text ut-has-detail");
  assert.equal(txt.dataset.act, "uttoggle");
  const kids = txt.childNodes;
  assert.equal(kids.length, 4);
  assert.equal((kids[0] as TextNode).data, TEXT);
  assert.equal((kids[1] as TextNode).data, " ", "a space keeps the chip off the text");
  assert.equal(kids[2], chip);
  assert.equal((kids[3] as Elm).className, "ut-more", "the hint still trails everything");
  // the Reply button rides the file to the modal, beside the text and the detail it already carried
  const reply = one(turn, hasClass("ut-reply"), "Reply button");
  assert.equal((reply as any)._utfile, FILE);
  assert.equal((reply as any)._uttext, TEXT);
  assert.equal((reply as any)._utdetail, DETAIL);
  assert.equal(reply.dataset.act, "utreply");
});

test("the label is the basename however the path is spelled; the chip itself hangs no listener", async () => {
  const h = await host();
  assert.equal(h.todoFileChip("/tmp/TESTHOST/notes-api/docs/report.md", SID).textContent, "report.md");
  assert.equal(h.todoFileChip("/tmp/TESTHOST/notes-api/figures/", SID).textContent, "figures", "a trailing slash names the directory");
  assert.equal(h.todoFileChip("report.md", SID).textContent, "report.md", "a bare name is its own label");
  const chip = h.todoFileChip(FILE, null);
  assert.deepEqual(chip.dataset, { act: "openpath", path: FILE, rel: "1" }, "no session named: the click resolves against the active tab, as a linkified path's does");
  assert.equal(chip.listeners.click, undefined, "nothing bound: the click is the stable root's delegate");
});

test("a todo without a file: no chip on the row, an empty file on Reply, and none in the modal", async () => {
  const body = freshBody();
  const h = await host();
  const turn = h.renderTodo({ kind: "todo", tasks: [], userTodos: [{ id: TID, text: TEXT, detail: DETAIL, createdT: 1 }] });
  assert.deepEqual(all(turn, hasClass("ut-file")), []);
  assert.deepEqual(all(turn, hasClass("file-uri-link")), [], "and no other link: the text and the detail spell no path");
  const txt = one(turn, hasClass("ut-text"), "text span");
  assert.equal(txt.childNodes.length, 2, "the text and the hint, nothing between");
  assert.equal((one(turn, hasClass("ut-reply"), "Reply button") as any)._utfile, "");
  h.showUserTodoReply(SID, TID, TEXT, DETAIL, "");
  const overlay = one(body, (e) => e.id === "ut-reply-prompt", "Reply modal");
  assert.deepEqual(all(overlay, hasClass("ut-file")), []);
  assert.equal(one(overlay, hasClass("ut-reply-quote"), "quoted line").textContent, TEXT, "the quote is the text alone");
  // the two-argument-shorter call the older delegate made still works: the file defaults to none
  h.showUserTodoReply(SID, TID, TEXT);
  assert.deepEqual(all(one(body, (e) => e.id === "ut-reply-prompt", "Reply modal"), hasClass("ut-file")), []);
});

test("a click on the chip opens the file through the BODY delegate against the todo's own session, does not fold, and still opens after the card is rebuilt", async () => {
  const body = freshBody();
  const { delegate } = await import("./actions");
  const h = await host(ACTIVE);   // the active tab is another session: the click must still name the todo's
  let folds = 0;
  delegate(body as unknown as HTMLElement, { openpath: h.openpath as any, uttoggle: (() => { folds++; }) as any });   // once, on the stable root, as render.ts does
  const card = new Elm("div"); body.appendChild(card);
  let turn = h.renderTodo(EV); card.appendChild(turn);
  let chip = one(turn, hasClass("ut-file"), "chip");
  assert.equal(chip.listeners.click, undefined, "nothing is bound on the chip: the click is the delegate's");
  body.click(chip);
  assert.deepEqual(h.opened, [[FILE, SID]], "the file opens against the session that filed the todo, not the active tab");
  assert.equal(folds, 0, "the fold did not move: the nearest data-act wins (actions.ts)");
  assert.ok(chip.classList.contains("romp-acted"), "the delegate's press flash on the chip");
  // a push rebuilds the card: the pressed node is gone, and the new chip opens through the same root
  turn.remove();
  turn = h.renderTodo(EV); card.appendChild(turn);
  chip = one(turn, hasClass("ut-file"), "chip");
  body.click(chip);
  assert.deepEqual(h.opened, [[FILE, SID], [FILE, SID]]);
  // the text beside the chip folds and opens nothing
  body.click(chip.parentElement!);
  assert.equal(folds, 1);
  assert.equal(h.opened.length, 2);
});

test("Reply carries the file into the modal: the quoted line trails the same chip, the detail is quoted beneath, and a click on the chip opens the file from the same root", async () => {
  const body = freshBody();
  const { delegate } = await import("./actions");
  const h = await host(ACTIVE);
  delegate(body as unknown as HTMLElement, { openpath: h.openpath as any, utreply: h.utreply as any });
  const turn = h.renderTodo(EV); body.appendChild(turn);
  body.click(one(turn, hasClass("ut-reply"), "Reply button"));
  const overlay = one(body, (e) => e.id === "ut-reply-prompt", "Reply modal");
  const quote = one(overlay, hasClass("ut-reply-quote"), "quoted line");
  const chip = one(overlay, hasClass("ut-file"), "chip in the modal");
  assert.equal(chip.parentElement, quote, "the chip trails the quoted line");
  assert.equal(quote.textContent, TEXT + " report.md");
  assert.deepEqual(chip.dataset, { act: "openpath", path: FILE, rel: "1", sid: SID });
  assert.equal(chip.title, FILE);
  assert.equal(one(overlay, hasClass("ut-detail"), "quoted detail").textContent, DETAIL, "the detail is still quoted beneath, open");
  assert.ok(body.contains(overlay), "the modal is in the body, where the delegate is");
  body.click(chip);
  assert.deepEqual(h.opened, [[FILE, SID]], "the modal's chip opens the file with the todo's session too");
});

test("a todo whose text spells the path AND names the file: the text's path links as before, the chip is added once, and no label is re-linkified", async () => {
  const h = await host();
  const turn = h.renderTodo({ kind: "todo", tasks: [], userTodos: [{
    id: TID, text: "Look at " + FILE + " before the meeting", detail: "the figure in " + FILE + " reads wrong", createdT: 1, file: FILE }] });
  const links = all(turn, hasClass("file-uri-link"));
  assert.deepEqual(links.map((l) => l.textContent), [FILE, "report.md", FILE], "the text's path as written, the chip, the detail's path as written");
  assert.deepEqual(links.map((l) => l.classList.contains("ut-file")), [false, true, false], "one chip");
  for (const l of links) {
    assert.equal(l.childNodes.length, 1, "each label is one text node: nothing linked twice");
    assert.deepEqual(l.dataset, { act: "openpath", path: FILE, rel: "1", sid: SID }, "all three open the same file with the same session");
  }
});

// ── at source: the field, the button's ride, the signature, the delegate's hand-off, the chip's shape and its
// place after the linkifiers, on both surfaces
test("render.ts: the todo row carries `file`, the Reply button rides it, the modal takes it, and the chip is a path link appended after the line's linkifiers", () => {
  assert.match(RENDER, /interface UserTodo \{ id: string; text: string; detail\?: string; createdT\?: number; file\?: string; link\?: string \}/);   // link: the address the todo carries (2026-09-08)
  assert.match(RENDER, /\(reply as any\)\._utfile = t\.file \|\| "";/);
  assert.match(RENDER, /function showUserTodoReply\(sid: string, todoId: string, todoText: string, todoDetail = "", todoFile = "", todoLink = ""\): void/);
  assert.match(RENDER, /showUserTodoReply\(sid, tid, \(\(elx as any\)\._uttext as string\) \|\| "", \(\(elx as any\)\._utdetail as string\) \|\| "", \(\(elx as any\)\._utfile as string\) \|\| "", \(\(elx as any\)\._utlink as string\) \|\| ""\);/);
  const chip = liftRender("todoFileChip");
  assert.match(chip, /openPathLink\(base, file, true, sid\)/, "a path link, marked as a bare path with the todo's session so openLinkedPath opens it against that session");
  assert.match(chip, /chip\.classList\.add\("ut-file"\)/);
  assert.match(chip, /chip\.title = file;/);
  assert.doesNotMatch(chip, /addEventListener|onclick/, "nothing bound on the chip: the body delegate's openpath is the click");
  const card = RENDER.slice(RENDER.indexOf('const txt = el("span", "ut-text");'), RENDER.indexOf('const reply = el("button", "ut-btn ut-reply");'));
  assert.match(card, /if \(t\.file\) txt\.append\(" ", todoFileChip\(t\.file, renderingSid \|\| null\)\);/);
  assert.ok(card.indexOf("linkTodoLinePaths(txt") < card.indexOf("todoFileChip(t.file"), "the chip comes after the line's linkifier, so its label is never scanned");
  assert.ok(card.indexOf("todoFileChip(t.file") < card.indexOf("utDetailHint(t.detail"), "and before the hint: text, chip, hint");
  const modal = RENDER.slice(RENDER.indexOf("function showUserTodoReply("), RENDER.indexOf('input.className = "ut-reply-input"'));
  assert.match(modal, /if \(todoFile\) d\.append\(" ", todoFileChip\(todoFile, sid\)\);/);
  assert.ok(modal.indexOf("linkTodoLinePaths(d, sid)") < modal.indexOf("todoFileChip(todoFile, sid)"), "the modal's chip too comes after the quoted line's linkifier");
  assert.equal((RENDER.match(/todoFileChip\(/g) || []).length, 3, "defined once, applied at the two sites");
});

// ── the web address a todo CARRIES (the user 2026-09-08, whose todo titles named pull requests by URL): the
// record's `link`, a second chip beside the file's in the same dress, an anchor the chat's document-level
// a[href] delegate opens (target _blank, rel noopener noreferrer, the whole address on hover)
const LINK = "https://github.com/example-org/notes-api/pull/398";
const LINK_LABEL = "example-org/notes-api#398";   // urlChipLabel: a GitHub pull request reads owner/repo#N, so the number survives the pill's cut (url-links.test.ts pins the forms)
const LINK_EV = { kind: "todo", tasks: [], userTodos: [{ id: TID, text: TEXT, detail: DETAIL, createdT: 1, file: FILE, link: LINK }] };

test("a todo that carries a link: the row trails the file chip with the link chip, the short label (owner/repo#N) with the whole address on hover, an anchor that opens a new tab; Reply carries it", async () => {
  const h = await host();
  const turn = h.renderTodo(LINK_EV);
  const chip = one(turn, hasClass("ut-link"), "link chip");
  assert.equal(chip.tagName, "a", "an ordinary anchor: the document's a[href] delegate opens it, at the capture phase, so uttoggle never folds the row");
  assert.ok(chip.classList.contains("url-link"), "the URL anchors' class, for the sheets and the pane's opener");
  assert.equal(chip.getAttribute("href"), LINK, "the href as an attribute, which the openers read");
  assert.equal(chip.textContent, LINK_LABEL, "the label: the pull request's owner/repo#N, the part that tells two links apart");
  assert.equal(chip.title, LINK, "the whole address on hover");
  assert.equal((chip as any).target, "_blank");
  assert.equal((chip as any).rel, "noopener noreferrer");
  assert.deepEqual(chip.dataset, {}, "no data-act: the click is the anchor's own, never the body delegate's");
  assert.equal(chip.listeners.click, undefined, "nothing bound on the chip");
  assert.equal(chip.childNodes.length, 1, "the label is one text node: the linkifiers ran before it and never scanned it");
  // its place: inside the text span, after the file chip, before the hint
  const txt = chip.parentElement!;
  assert.equal(txt.className, "ut-text ut-has-detail");
  const kids = txt.childNodes;
  assert.equal(kids.length, 6);
  assert.equal((kids[0] as TextNode).data, TEXT);
  assert.equal((kids[1] as TextNode).data, " ");
  assert.ok((kids[2] as Elm).classList.contains("ut-file"), "the file chip first");
  assert.equal((kids[3] as TextNode).data, " ", "a space keeps the two chips apart");
  assert.equal(kids[4], chip);
  assert.equal((kids[5] as Elm).className, "ut-more", "the hint still trails everything");
  const reply = one(turn, hasClass("ut-reply"), "Reply button");
  assert.equal((reply as any)._utlink, LINK, "the Reply button rides the address to the modal");
  assert.equal((reply as any)._utfile, FILE);
});

test("a todo with a link and no file: the link chip alone; without either: no chip and an empty link on Reply", async () => {
  const h = await host();
  const turn = h.renderTodo({ kind: "todo", tasks: [], userTodos: [{ id: TID, text: TEXT, createdT: 1, link: LINK }] });
  assert.equal(all(turn, hasClass("ut-file")).length, 0);
  assert.equal(all(turn, hasClass("ut-link")).length, 1);
  assert.equal(all(turn, hasClass("file-uri-link")).length, 0, "no path link anywhere: the address is not a path");
  const bare = h.renderTodo({ kind: "todo", tasks: [], userTodos: [{ id: TID, text: TEXT, createdT: 1 }] });
  assert.equal(all(bare, hasClass("ut-link")).length, 0);
  assert.equal((one(bare, hasClass("ut-reply"), "Reply button") as any)._utlink, "");
  assert.equal(h.todoLinkChip(LINK).textContent, LINK_LABEL);
});

test("Reply carries the link into the modal: the quoted line trails the file chip and then the link chip, the same anchor", async () => {
  const body = freshBody();
  const { delegate } = await import("./actions");
  const h = await host(ACTIVE);
  delegate(body as unknown as HTMLElement, { openpath: h.openpath as any, utreply: h.utreply as any });
  const turn = h.renderTodo(LINK_EV); body.appendChild(turn);
  body.click(one(turn, hasClass("ut-reply"), "Reply button"));
  const overlay = one(body, (e) => e.id === "ut-reply-prompt", "Reply modal");
  const quote = one(overlay, hasClass("ut-reply-quote"), "quoted line");
  const chip = one(overlay, hasClass("ut-link"), "link chip in the modal");
  assert.equal(chip.parentElement, quote, "the chip trails the quoted line");
  assert.equal(quote.textContent, TEXT + " report.md " + LINK_LABEL, "text, the file chip, the link chip");
  assert.equal(chip.getAttribute("href"), LINK);
  assert.equal(chip.title, LINK);
  assert.equal((chip as any).target, "_blank");
  assert.equal(one(overlay, hasClass("ut-detail"), "quoted detail").textContent, DETAIL);
});

// ── the click on a URL anchor and on the link chip, through the chat's REAL document-level anchor opener (render.ts,
// lifted and transpiled; the 2026-09-09 review: the source pins in url-links.test.ts name the branch, this executes it).
// The opener is installed at the capture phase on the document, so it runs before the body delegate; for an anchor
// whose href names a scheme it spends the click (preventDefault, stopPropagation) and opens the href the host's way
// (web: window.open; VS Code: an openLink post), and the click never reaches the fold's uttoggle beneath the anchor.
type Spent = { prevented: boolean; stopped: boolean };
interface OpenerEnv { protocol: string; origin: string; open: (href: string) => void; post: ((m: unknown) => void) | null; view: (href: string) => void }
function anchorOpener(env: OpenerEnv): (e: unknown) => void {
  const head = 'document.addEventListener("click", (e) => {\n  const a = (e.target as Element)?.closest?.(LINK_SEL)';
  const start = RENDER.indexOf(head);
  const end = RENDER.indexOf("}, true);", start) + "}, true);".length;
  assert.ok(start > 0 && end > start, "anchor not found: render.ts's document-level anchor opener moved; re-anchor");
  const src = RENDER.slice(start, end).replace('document.addEventListener("click", ', "install(");
  let handler: ((e: unknown) => void) | null = null;
  const install = (h: (e: unknown) => void, capture: boolean) => { assert.equal(capture, true, "installed at the capture phase"); handler = h; };
  // every free name the opener uses: the shared selector and href read (md-links.ts, real), the `#` branch's helpers
  // (real; not reached by an absolute href), the panel's registry and the selection test (a plain click: neither
  // holds), the same-origin .md route (recorded), the host and the platform read
  const fn = new Function("install", "LINK_SEL", "linkHref", "isMarkdownUrl", "browserTabClick", "userContentTarget",
    "panelMark", "selectionOpenIn", "openUrlView", "vscodeApi", "location", "window",
    transpile("const IS_MAC = false;\n" + src));
  fn(install, LINK_SEL, linkHref, isMarkdownUrl, browserTabClick, userContentTarget,
    () => false, () => false, env.view, env.post ? { postMessage: env.post } : null,
    { protocol: env.protocol, origin: env.origin }, { open: (href: string) => env.open(href) });
  assert.ok(handler, "the opener registered its listener");
  return handler!;
}
/** the browser's dispatch for a click on `target`: the document's capture-phase opener first, then the body's listeners
 *  (the delegate) unless the opener stopped the propagation */
function clickThrough(opener: (e: unknown) => void, body: Elm, target: Elm): Spent {
  const spent: Spent = { prevented: false, stopped: false };
  const ev = { target, preventDefault: () => { spent.prevented = true; }, stopPropagation: () => { spent.stopped = true; } };
  opener(ev);
  if (!spent.stopped) for (const fn of body.listeners.click || []) fn(ev);
  return spent;
}

test("a click on the URL anchor in a todo's text, and on the link chip, goes through the chat's document-level anchor opener: one window.open on the web, one openLink post under VS Code, the click spent, the fold beneath unmoved, no path opened", async () => {
  const body = freshBody();
  const { delegate } = await import("./actions");
  const { isWebUrl } = await import("./url-links");
  const h = await host(ACTIVE);
  let folds = 0;
  delegate(body as unknown as HTMLElement, { openpath: h.openpath as any, utreply: h.utreply as any, uttoggle: (() => { folds++; }) as any });   // the body delegate, once, as render.ts installs it
  const opened: string[] = [], viewed: string[] = [];
  const web = anchorOpener({ protocol: "https:", origin: "https://TESTHOST", open: (u) => opened.push(u), post: null, view: (u) => viewed.push(u) });
  const turn = h.renderTodo({ kind: "todo", tasks: [], userTodos: [{ id: TID, text: "Review " + LINK + " before the merge.", detail: DETAIL, createdT: 1, file: FILE, link: LINK }] });
  body.appendChild(turn);
  const txt = one(turn, hasClass("ut-text"), "text span");
  assert.equal(txt.dataset.act, "uttoggle", "the fold's click target is the span the anchors stand in");
  const anchors = all(turn, (e) => e.tagName === "a");
  assert.equal(anchors.length, 2, "the URL in the text and the chip");
  const [inText, chip] = anchors;
  assert.ok(chip.classList.contains("ut-link") && !inText.classList.contains("ut-link"));
  for (const a of anchors) assert.ok(isWebUrl(a.getAttribute("href")!), "every anchor the card built carries a web address (the kernel's check is the chat's gate; the pane's opener adds its own)");
  // the anchor in the text: the opener opens the href once and spends the click; the body delegate never sees it
  let spent = clickThrough(web, body, inText);
  assert.deepEqual(opened, [LINK], "one tab, the href");
  assert.deepEqual(spent, { prevented: true, stopped: true }, "the click is spent at the capture phase");
  assert.equal(folds, 0, "the fold beneath the anchor did not move");
  assert.deepEqual(h.opened, [], "no path opened: the anchor is not a path link");
  assert.equal(viewed.length, 0, "another origin: no viewer route");   // a length, not deepEqual([]): that narrows the array to never[] for the closure below
  // the chip: the same
  spent = clickThrough(web, body, chip);
  assert.deepEqual(opened, [LINK, LINK]);
  assert.deepEqual(spent, { prevented: true, stopped: true });
  assert.equal(folds, 0);
  // the text beside the anchors: no anchor above the target, so the opener stands aside and the body delegate folds
  spent = clickThrough(web, body, txt);
  assert.deepEqual(spent, { prevented: false, stopped: false });
  assert.equal(folds, 1);
  assert.equal(opened.length, 2, "nothing opened by a fold click");
  // the file chip: a path link (a span with a data-act, no href), so the opener stands aside and the delegate opens the file
  spent = clickThrough(web, body, one(turn, hasClass("ut-file"), "file chip"));
  assert.deepEqual(h.opened, [[FILE, SID]]);
  assert.deepEqual(spent, { prevented: false, stopped: false }, "the delegate's click, not the opener's");
  assert.equal(folds, 1);
  // under VS Code the same click on the chip posts openLink to the host once, opens no window, and is spent the same way
  const posted: unknown[] = [], opened2: string[] = [];
  const code = anchorOpener({ protocol: "vscode-webview:", origin: "vscode-webview://TESTHOST", open: (u) => opened2.push(u), post: (m) => posted.push(m), view: (u) => viewed.push(u) });
  spent = clickThrough(code, body, chip);
  assert.deepEqual(posted, [{ type: "openLink", href: LINK }], "the host's openExternal takes it");
  assert.deepEqual(opened2, [], "the webview cannot window.open");
  assert.deepEqual(spent, { prevented: true, stopped: true });
  assert.equal(folds, 1);
  spent = clickThrough(code, body, inText);
  assert.deepEqual(posted, [{ type: "openLink", href: LINK }, { type: "openLink", href: LINK }]);
  assert.equal(folds, 1);
  // the Reply modal's chip goes through the same opener
  body.click(one(turn, hasClass("ut-reply"), "Reply button"));
  const overlay = one(body, (e) => e.id === "ut-reply-prompt", "Reply modal");
  spent = clickThrough(web, body, one(overlay, hasClass("ut-link"), "link chip in the modal"));
  assert.deepEqual(opened, [LINK, LINK, LINK]);
  assert.deepEqual(spent, { prevented: true, stopped: true });
});

test("a todo whose text spells the URL AND carries it as its link: the text's URL links as typed, the chip is added once with its label, and nothing is linked twice", async () => {
  const h = await host();
  const turn = h.renderTodo({ kind: "todo", tasks: [], userTodos: [{
    id: TID, text: "Review " + LINK + " before the merge.", detail: "the description at " + LINK + " is stale", createdT: 1, link: LINK }] });
  const anchors = all(turn, (e) => e.tagName === "a");
  assert.deepEqual(anchors.map((a) => a.textContent), [LINK, LINK_LABEL, LINK], "the text's URL as typed, the chip's label, the detail's URL as typed");
  assert.deepEqual(anchors.map((a) => a.classList.contains("ut-link")), [false, true, false], "one chip");
  for (const a of anchors) {
    assert.equal(a.childNodes.length, 1, "each label is one text node: nothing linked twice");
    assert.equal(a.getAttribute("href"), LINK);
  }
  const txt = anchors[0].parentElement!;
  assert.ok(txt.classList.contains("ut-text") || txt.className.includes("ut-text"));
  assert.ok(txt.textContent.startsWith("Review " + LINK + " before the merge. " + LINK_LABEL), "the period stays outside the text's link, the chip follows: " + txt.textContent);
  assert.equal(txt.textContent.slice(("Review " + LINK + " before the merge. " + LINK_LABEL).length), "▸ details", "and the hint still trails everything (the todo has detail)");
});

test("render.ts: the todo row carries `link`, the Reply button rides it, the modal takes it, and the chip is an anchor appended after the file chip", () => {
  assert.match(RENDER, /\(reply as any\)\._utlink = t\.link \|\| "";/);
  const chip = liftRender("todoLinkChip");
  assert.match(chip, /return urlChip\(link, "ut-link"\);/, "url-links.ts's chip anchor in the card's dress");
  assert.doesNotMatch(chip, /addEventListener|onclick|dataset/, "nothing bound and no data-act: the document's a[href] delegate is the click");
  const card = RENDER.slice(RENDER.indexOf('const txt = el("span", "ut-text");'), RENDER.indexOf('const reply = el("button", "ut-btn ut-reply");'));
  assert.match(card, /if \(t\.link\) txt\.append\(" ", todoLinkChip\(t\.link\)\);/);
  assert.ok(card.indexOf("todoFileChip(t.file") < card.indexOf("todoLinkChip(t.link"), "the file chip first, then the link chip");
  assert.ok(card.indexOf("todoLinkChip(t.link") < card.indexOf("utDetailHint(t.detail"), "and both before the hint");
  const modal = RENDER.slice(RENDER.indexOf("function showUserTodoReply("), RENDER.indexOf('input.className = "ut-reply-input"'));
  assert.match(modal, /if \(todoLink\) d\.append\(" ", todoLinkChip\(todoLink\)\);/);
  assert.ok(modal.indexOf("todoFileChip(todoFile, sid)") < modal.indexOf("todoLinkChip(todoLink)"), "the modal's chips in the row's order");
  assert.equal((RENDER.match(/todoLinkChip\(/g) || []).length, 3, "defined once, applied at the two sites");
});
