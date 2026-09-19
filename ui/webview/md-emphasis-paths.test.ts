// Emphasis never cuts a file path in the chat (md-config.ts pathAwareEmphasis, on chat-md.ts's two instances),
// executed over the REAL marked. The class, measured row by row before the fix (the population note,
// md-emphasis-population.md: 55 rows and 20 adversarial ones): the chat renders a reply with marked and then links
// the file paths it finds in the rendered text, one text node at a time (path-links.ts linkifyPathTokens), and a
// path's own punctuation makes its underscores legal emphasis delimiters under CommonMark's flanking rules, so
// `/a-_b/c_/d.md` rendered `/a-<em>b/c</em>/d.md`, `__init__.py` rendered strong, the walk never saw the token whole
// and the kernel's key for it matched no text node (the 2026-09-19 browser census, Entry 5: a temp directory whose
// random name began with an underscore). marked is spec-correct on every row, so the fix is a tokenizer override on
// the chat's instances that refuses an opener or closer lying strictly inside a token the walk's own scanner and
// gates would link. Pinned here, by execution: every member row renders literal on both chat renderers and the walk
// then links every wanted token (C36 both of its two); every other row is byte-identical to the base grammar (the
// singleton's configuration on a private instance), real emphasis, strong, strikethrough, autolinks, code spans and
// fences included; the adversarial rows change only where the note says, A08 the one accepted loss; the base grammar
// still cuts every member row (the defect, reproduced, so the reason for the road is on record); a footnote reference
// inside a refused pair is numbered once (the built-in lexes a pair's body before it returns, so the override runs it
// dry); and the instance boundary: the singleton, which the viewer and the hover preview render on, keeps GitHub's
// rendering of `foo/__pycache__/bar.pyc`. The walk runs over a small DOM stand-in fed marked's HTML (no jsdom), the
// chat's own options minus the fenced gate, with a map holding the wanted tokens, as the kernel's verdict would.
// Synthetic fixtures only: invented paths (`/a-_b/c_/d.md` and the like), a placeholder session id.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { Marked, marked } from "marked";
import { hideEdges } from "../test-dom-shim";
import * as chatMd from "./chat-md";
import { applyMdConfig, mdExtensions } from "./md-config";
import { linkifyPathTokens } from "./path-links";

const UI = path.resolve(process.cwd(), "..", "ui", "webview");
const read = (f: string): string => fs.readFileSync(path.join(UI, f), "utf8");
const SID = "11111111-2222-3333-4444-555555555555";

// the road before the fix: the singleton's configuration (gfm, breaks off, the shared list, nothing else) on a private
// instance, so this file leaves the singleton as the other tests find it
const base = new Marked({ gfm: true, breaks: false }, ...mdExtensions);
const baseHtml = (src: string): string => base.parse(src) as string;
// the chat's two renderers: a reply's (render.ts md() parses through chatMdHtml) and the user's own words' (userMd). Every
// table test runs over both, the user's first: that renderer exists on the tree before this change too, so a run there
// reports the rendering the class produced, not a missing export.
const chatExported = (): void => assert.equal(typeof chatMd.chatMdHtml, "function", "chat-md.ts exports chatMdHtml, the reply renderer render.ts md() parses through");
const chatHtml = (src: string): string => { chatExported(); return chatMd.chatMdHtml(src); };
const userHtml = (src: string): string => chatMd.userMdHtml(src);
const RENDERERS: Array<[string, (src: string) => string]> = [["the user's own words (userMdHtml)", userHtml], ["a reply (chatMdHtml)", chatHtml]];

// ── the population: id, text, the chat's HTML where it differs from the base grammar (`after`), a shape the base and the
// chat must both keep (`keeps`: real emphasis and the like, so "identical" is not vacuous), the tokens the walk must link
// over the chat's DOM (`links`, in order), and the keys the map holds beyond those (`keys`: a bare name in prose, which the
// override protects and the walk still does not link) ──
type Row = { id: string; text: string; after?: string; keeps?: string[]; links: string[]; keys?: string[] };
const P = "/a-_b/c_/d.md";
const CASES: Row[] = [
  { id: "C01", text: "notes outside the project sit at /tmp/lab-_abc/preview-xyz_/outside/notes.md.", after: "<p>notes outside the project sit at /tmp/lab-_abc/preview-xyz_/outside/notes.md.</p>\n", links: ["/tmp/lab-_abc/preview-xyz_/outside/notes.md"] },
  { id: "C02", text: "see /a-_b/c_/d.md today", after: "<p>see /a-_b/c_/d.md today</p>\n", links: [P] },
  { id: "C03", text: "snake_case_name", links: [] },
  { id: "C04", text: "a_b_c", links: [] },
  { id: "C05", text: "__init__.py", after: "<p>__init__.py</p>\n", links: [], keys: ["__init__.py"] },
  { id: "C06", text: "foo/__pycache__/bar.pyc", after: "<p>foo/__pycache__/bar.pyc</p>\n", links: ["foo/__pycache__/bar.pyc"] },
  { id: "C07", text: "_private", links: [] },
  { id: "C08", text: "trailing_", links: [] },
  { id: "C09", text: "-_x", links: [] },
  { id: "C10", text: "x_-", links: [] },
  { id: "C11", text: "a-_b/c_/d.md", after: "<p>a-_b/c_/d.md</p>\n", links: ["a-_b/c_/d.md"] },
  { id: "C12", text: "*.py", links: [] },
  { id: "C13", text: "src/*.py", links: [] },
  { id: "C14", text: "**/*.ts", links: [] },
  { id: "C15", text: "~/code/romp", links: ["~/code/romp"] },
  { id: "C16", text: "~~/x", links: [] },
  { id: "C17", text: "a*b*c", keeps: ["a<em>b</em>c"], links: [] },
  { id: "C18", text: "2*3*4", keeps: ["2<em>3</em>4"], links: [] },
  { id: "C19", text: "\\_escaped\\_", keeps: ["<p>_escaped_</p>"], links: [] },
  { id: "C20", text: "_", links: [] },
  { id: "C21", text: "__", links: [] },
  { id: "C22", text: "___", keeps: ["<hr>"], links: [] },
  { id: "C23", text: "foo _bar_ baz", keeps: ["foo <em>bar</em> baz"], links: [] },
  { id: "C24", text: "**bold**", keeps: ["<strong>bold</strong>"], links: [] },
  { id: "C25", text: "*em*", keeps: ["<em>em</em>"], links: [] },
  { id: "C26", text: "https://example.test/a_b_c/d_", keeps: ['<a href="https://example.test/a_b_c/d">https://example.test/a_b_c/d</a>_'], links: [] },
  { id: "C27", text: "first_last@example.test", keeps: ['<a href="mailto:first_last@example.test">'], links: [] },
  { id: "C28", text: "C:\\dir_\\_x", keeps: ["<p>C:\\dir__x</p>"], links: [] },
  { id: "C29", text: "see `/a-_b/c_/d.md` now", keeps: ["<code>/a-_b/c_/d.md</code>"], links: [P] },
  { id: "C30", text: "```\n/a-_b/c_/d.md\n```", keeps: ["<pre><code>/a-_b/c_/d.md\n</code></pre>"], links: [P] },
  { id: "C31", text: "/a-_b/c_/d.md is the note", after: "<p>/a-_b/c_/d.md is the note</p>\n", links: [P] },
  { id: "C32", text: "the note is /a-_b/c_/d.md", after: "<p>the note is /a-_b/c_/d.md</p>\n", links: [P] },
  { id: "C33", text: "see /a-_b/c_/d.md.", after: "<p>see /a-_b/c_/d.md.</p>\n", links: [P] },
  { id: "C34", text: "see /a-_b/c_/d.md, then", after: "<p>see /a-_b/c_/d.md, then</p>\n", links: [P] },
  { id: "C35", text: "see /a-_b/c_/d.md and /e-_f/g_/h.md today", after: "<p>see /a-_b/c_/d.md and /e-_f/g_/h.md today</p>\n", links: [P, "/e-_f/g_/h.md"] },
  { id: "C36", text: "see /tmp/a-_b/c.md and /tmp/d_/e.md today", after: "<p>see /tmp/a-_b/c.md and /tmp/d_/e.md today</p>\n", links: ["/tmp/a-_b/c.md", "/tmp/d_/e.md"] },
  { id: "C37", text: "_private_ sits beside /a-_b/c_/d.md", after: "<p><em>private</em> sits beside /a-_b/c_/d.md</p>\n", links: [P] },
  { id: "C38", text: "_private /a-b/c_/d.md", after: "<p>_private /a-b/c_/d.md</p>\n", links: ["/a-b/c_/d.md"] },
  { id: "C39", text: "__init__.py and __main__.py", after: "<p>__init__.py and __main__.py</p>\n", links: [], keys: ["__init__.py", "__main__.py"] },
  { id: "C40", text: "src/*.py and lib/*.ts", keeps: ["src/<em>.py and lib/</em>.ts"], links: [] },
  { id: "C41", text: "see /a-\\_b/c\\_/d.md today", keeps: ["<p>see /a-_b/c_/d.md today</p>"], links: [P] },
  { id: "C42", text: "_docs/notes.md_", keeps: ["<em>docs/notes.md</em>"], links: ["docs/notes.md"] },
  { id: "C43", text: "~~/old/notes.md~~", keeps: ["<del>/old/notes.md</del>"], links: ["/old/notes.md"] },
  { id: "C44", text: "/x/_y_/z.md", after: "<p>/x/_y_/z.md</p>\n", links: ["/x/_y_/z.md"] },
  { id: "C45", text: "https://example.test/a-_b/c_/d", keeps: ['<a href="https://example.test/a-_b/c_/d">https://example.test/a-_b/c_/d</a>'], links: [] },
  { id: "C46", text: "/tmp/x_/y.md", links: ["/tmp/x_/y.md"] },
  { id: "C47", text: "/tmp/-_x/y.md", links: ["/tmp/-_x/y.md"] },
  { id: "C48", text: "/pkg/__init__.py", after: "<p>/pkg/__init__.py</p>\n", links: ["/pkg/__init__.py"] },
  { id: "C49", text: "/a/_b/c_/d.md", after: "<p>/a/_b/c_/d.md</p>\n", links: ["/a/_b/c_/d.md"] },
  { id: "C50", text: "[x](/a-_b/c_/d.md)", keeps: ['<a href="/a-_b/c_/d.md">x</a>'], links: [] },
  { id: "C51", text: "`/a-_b/c_/d.md` then /e-_f/g_/h.md", after: "<p><code>/a-_b/c_/d.md</code> then /e-_f/g_/h.md</p>\n", links: [P, "/e-_f/g_/h.md"] },
  { id: "C52", text: "see *a-_b/c_/d.md* now", after: "<p>see <em>a-_b/c_/d.md</em> now</p>\n", links: ["a-_b/c_/d.md"] },
  { id: "C53", text: "/tmp/a_/b-_c/d.md", links: ["/tmp/a_/b-_c/d.md"] },
  { id: "C54", text: "/tmp/x__/y-__z/w.md", links: ["/tmp/x__/y-__z/w.md"] },
  { id: "C55", text: "see /tmp/a-__b/c__/d.md now", after: "<p>see /tmp/a-__b/c__/d.md now</p>\n", links: ["/tmp/a-__b/c__/d.md"] },
];
const MEMBERS = ["C01", "C02", "C05", "C06", "C11", "C31", "C32", "C33", "C34", "C35", "C36", "C37", "C38", "C39", "C44", "C48", "C49", "C51", "C52", "C55"];
const ADVERSARIAL: Row[] = [
  { id: "A01", text: "the _docs/notes.md_.", keeps: ["<em>docs/notes.md</em>."], links: ["docs/notes.md"] },
  { id: "A02", text: "_notes.md_", keeps: ["<em>notes.md</em>"], links: [], keys: ["notes.md"] },
  { id: "A03", text: "**docs/a.md**", keeps: ["<strong>docs/a.md</strong>"], links: ["docs/a.md"] },
  { id: "A04", text: "*docs/a_b.md*", keeps: ["<em>docs/a_b.md</em>"], links: ["docs/a_b.md"] },
  { id: "A05", text: "_a/b.md_ and _c/d.md_", keeps: ["<em>a/b.md</em> and <em>c/d.md</em>"], links: ["a/b.md", "c/d.md"] },
  { id: "A06", text: "see _the docs/notes.md_ file", keeps: ["<em>the docs/notes.md</em>"], links: ["docs/notes.md"] },
  { id: "A07", text: "a _b/c_ d", keeps: ["a <em>b/c</em> d"], links: [] },
  { id: "A08", text: "_foo_-bar/baz.md", after: "<p>_foo_-bar/baz.md</p>\n", links: ["_foo_-bar/baz.md"] },   // the accepted loss: emphasis glued to a path
  { id: "A09", text: "*foo*/bar.md", keeps: ["<em>foo</em>/bar.md"], links: ["/bar.md"] },
  { id: "A10", text: "run `__init__.py` and **stop**", keeps: ["<code>__init__.py</code> and <strong>stop</strong>"], links: ["__init__.py"] },
  { id: "A11", text: "_/abs/x.md_", keeps: ["<em>/abs/x.md</em>"], links: ["/abs/x.md"] },
  { id: "A12", text: "see _/a-_b/c_/d.md_ now", after: "<p>see <em>/a-_b/c_/d.md</em> now</p>\n", links: [P] },
  { id: "A13", text: "__init__", keeps: ["<strong>init</strong>"], links: [] },
  { id: "A14", text: "the _x_ in a-_b/c_/d.md", after: "<p>the <em>x</em> in a-_b/c_/d.md</p>\n", links: ["a-_b/c_/d.md"] },
  { id: "A15", text: "_ab12cd/file-preview-ef34gh_", keeps: ["<em>ab12cd/file-preview-ef34gh</em>"], links: [] },
  { id: "A16", text: "a/b_c/d_ and _e", keeps: ["<p>a/b_c/d_ and _e</p>"], links: [] },
  { id: "A17", text: "[x](/a-\\_b/c\\_/d.md)", keeps: ['<a href="/a-_b/c_/d.md">x</a>'], links: [] },
  { id: "A18", text: "2026-09-19_notes/run_1.log", links: ["2026-09-19_notes/run_1.log"] },
  { id: "A19", text: "dir_/_file.md", links: ["dir_/_file.md"] },
  { id: "A20", text: "see ~/code/my_proj/_drafts/a_.md now", after: "<p>see ~/code/my_proj/_drafts/a_.md now</p>\n", links: ["~/code/my_proj/_drafts/a_.md"] },
];
const ADVERSARIAL_CHANGED = ["A08", "A12", "A14", "A20"];
const byId = (rows: Row[], id: string): Row => rows.find((r) => r.id === id)!;

// ── a DOM stand-in: text nodes, elements with attributes and a tag-and-class selector engine, fragments, a tree walker;
// every node hides its edges at creation (ui/test-dom-shim.ts hideEdges), so a failing assertion dumps a node's primitives
// and never its tree ──
type Compound = { tag: string | null; classes: string[] };
function parseSel(sel: string): Compound[] {
  return sel.split(",").map((s) => s.trim()).filter(Boolean).map((s) => {
    const m = /^([a-zA-Z][\w-]*)?((?:\.[\w-]+)*)$/.exec(s);
    if (!m) throw new Error("stand-in: unsupported selector " + s);
    return { tag: m[1] ? m[1].toUpperCase() : null, classes: (m[2].match(/\.[\w-]+/g) || []).map((c) => c.slice(1)) };
  });
}
class Txt {
  nodeType = 3;
  parentNode: El | null = null;
  constructor(public data: string) { hideEdges(this); }
  get textContent(): string { return this.data; }
  get parentElement(): El | null { return this.parentNode; }
  replaceWith(n: El | Txt | Frag): void {
    const p = this.parentNode!;
    const i = p.childNodes.indexOf(this);
    const kids = n instanceof Frag ? n.childNodes.slice() : [n];
    for (const k of kids) { if (k.parentNode) k.parentNode.removeChild(k); k.parentNode = p; }
    p.childNodes.splice(i, 1, ...kids);
    this.parentNode = null;
  }
}
class Frag { childNodes: Array<El | Txt> = []; constructor() { hideEdges(this); } appendChild(c: El | Txt): void { this.childNodes.push(c); } }
const kebab = (k: string): string => k.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
class El {
  nodeType = 1;
  tagName: string;
  parentNode: El | null = null;
  childNodes: Array<El | Txt> = [];
  attrs = new Map<string, string>();
  role: string | null = null;
  onkeydown: unknown = null; onmousedown: unknown = null; onmouseup: unknown = null; onmouseleave: unknown = null; oncontextmenu: unknown = null; ondragstart: unknown = null;
  constructor(tag: string) { this.tagName = tag.toUpperCase(); hideEdges(this); }
  get tabIndex(): number { return this.attrs.has("tabindex") ? Number(this.attrs.get("tabindex")) : -1; } set tabIndex(v: number) { this.attrs.set("tabindex", String(v)); }
  get parentElement(): El | null { return this.parentNode; }
  get className(): string { return this.attrs.get("class") || ""; } set className(v: string) { this.attrs.set("class", v); }
  get classes(): string[] { return this.className.split(/\s+/).filter(Boolean); }
  dataset: Record<string, string> = new Proxy({} as Record<string, string>, {
    get: (_, k) => this.attrs.get("data-" + kebab(String(k))) as string,
    set: (_, k, v) => { this.attrs.set("data-" + kebab(String(k)), String(v)); return true; },
    has: (_, k) => this.attrs.has("data-" + kebab(String(k))),
  });
  get textContent(): string { return this.childNodes.map((c) => c.textContent).join(""); }
  set textContent(v: string) { for (const c of this.childNodes) c.parentNode = null; this.childNodes = []; if (v !== "") this.appendChild(new Txt(v)); }
  private detach(n: El | Txt): void { const p = n.parentNode; if (p) { const i = p.childNodes.indexOf(n); if (i >= 0) p.childNodes.splice(i, 1); n.parentNode = null; } }
  appendChild<T extends El | Txt>(n: T): T { this.detach(n); this.childNodes.push(n); n.parentNode = this; return n; }
  removeChild<T extends El | Txt>(n: T): T { this.detach(n); return n; }
  setAttribute(k: string, v: string): void { this.attrs.set(k, v); }
  getAttribute(k: string): string | null { return this.attrs.has(k) ? (this.attrs.get(k) as string) : null; }
  hasAttribute(k: string): boolean { return this.attrs.has(k); }
  removeAttribute(k: string): void { this.attrs.delete(k); }
  matches(sel: string): boolean { return parseSel(sel).some((c) => (!c.tag || c.tag === this.tagName) && c.classes.every((k) => this.classes.includes(k))); }
  closest(sel: string): El | null { for (let x: El | null = this; x; x = x.parentNode) if (x.matches(sel)) return x; return null; }
  querySelectorAll(sel: string): El[] {
    const out: El[] = [];
    const visit = (n: El) => { for (const c of n.childNodes) if (c instanceof El) { if (c.matches(sel)) out.push(c); visit(c); } };
    visit(this);
    return out;
  }
}
/** Document-order nodes under `root`, as a browser's tree walker answers them (SHOW_ELEMENT = 1, SHOW_TEXT = 4). */
function walkNodes(root: El, what: number): Array<El | Txt> {
  const out: Array<El | Txt> = [];
  const walk = (n: El) => { for (const c of n.childNodes) { if (c instanceof Txt) { if (what & 4) out.push(c); } else { if (what & 1) out.push(c); walk(c); } } };
  walk(root);
  return out;
}
(globalThis as any).NodeFilter = { SHOW_ELEMENT: 1, SHOW_TEXT: 4 };
(globalThis as any).document = {
  createElement: (tag: string) => new El(tag),
  createTextNode: (s: string) => new Txt(s),
  createDocumentFragment: () => new Frag(),
  createTreeWalker: (root: El, what = 4) => { const nodes = walkNodes(root, what); let i = 0; return { nextNode: () => (i < nodes.length ? nodes[i++] : null) }; },
  activeElement: null as El | null,
};
// marked's HTML read into the stand-in: tags and text, the class attribute kept, the entities marked writes decoded
const VOID_TAGS = new Set(["BR", "HR", "IMG", "INPUT", "WBR"]);
const ENTITIES: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: "\"", "#39": "'" };
const unescapeHtml = (s: string): string => s.replace(/&(amp|lt|gt|quot|#39);/g, (_, k: string) => ENTITIES[k]);
function fromHtml(html: string): El {
  const root = new El("DIV");
  let cur = root;
  const re = /<\/([A-Za-z][\w-]*)\s*>|<([A-Za-z][\w-]*)([^>]*)>|([^<]+)/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(html))) {
    if (m[1]) { cur = cur.parentNode || root; continue; }
    if (m[2]) {
      const e = cur.appendChild(new El(m[2]));
      const c = /class="([^"]*)"/.exec(m[3] || "");
      if (c) e.className = c[1];
      if (!VOID_TAGS.has(e.tagName) && !/\/\s*$/.test(m[3] || "")) cur = e;
      continue;
    }
    cur.appendChild(new Txt(unescapeHtml(m[4])));
  }
  return root;
}
/** The chat's walk over `html`, the kernel's verdict standing in as a map that holds `keys`: what it linked, by target, in
 *  document order. The options are render.ts's FENCE_WALK minus its fenced gate (the file viewer's, on the kind of file;
 *  every fenced token here is a markdown file that gate admits). */
function walkLinks(html: string, keys: string[]): string[] {
  const root = fromHtml(html);
  const map: Record<string, string> = {};
  for (const k of keys) map[k] = k;
  const hits = linkifyPathTokens(root as unknown as HTMLElement, SID, map, { inPre: true, preVerified: true, unit: ".cl" });
  const marked_ = root.querySelectorAll(".file-uri-link").map((a) => a.dataset.path);
  assert.deepEqual(hits.map((h) => h.open), marked_, "the hits the walk returns are the links it marked");
  return marked_;
}
const keysOf = (r: Row): string[] => [...r.links, ...(r.keys || [])];

// ── the tables, rendered ─────────────────────────────────────────────────────────────────────────────────────────────

test("the chat renders every member row literal, on both of its renderers: exactly the 20 member rows change against the base grammar and none of the other 35", () => {
  for (const [who, render] of RENDERERS) {
    for (const id of MEMBERS) {
      const r = byId(CASES, id);
      assert.equal(render(r.text), r.after, id + ", " + who + ": " + JSON.stringify(r.text));
    }
    const changed = CASES.filter((r) => render(r.text) !== baseHtml(r.text)).map((r) => r.id);
    assert.deepEqual(changed, MEMBERS, who + ": the rows whose rendering changed are the member rows, all of them and no other");
  }
  assert.equal(CASES.length, 55); assert.equal(MEMBERS.length, 20);
});

test("every other row is byte-identical to the base grammar, and its emphasis, strong, strikethrough, autolink, link, code span or fence is kept", () => {
  for (const [who, render] of RENDERERS) for (const r of CASES) {
    if (MEMBERS.includes(r.id)) continue;
    const b = baseHtml(r.text), c = render(r.text);
    assert.equal(c, b, r.id + ", " + who + ": " + JSON.stringify(r.text));
    for (const k of r.keeps || []) { assert.ok(b.includes(k), r.id + " base keeps " + k + ": " + b); assert.ok(c.includes(k), r.id + ", " + who + " keeps " + k + ": " + c); }
  }
  // the rows that decide the boundary: real emphasis the user or the session typed, at a token's edge or around one
  for (const id of ["C17", "C23", "C24", "C25", "C40", "C42", "C43"]) assert.ok(byId(CASES, id).keeps, id + " asserts a kept shape");
});

test("the adversarial rows change only where the note says: A08 the accepted loss (emphasis glued to a path), A12, A14 and A20 to the literal path; the other 16 stand", () => {
  for (const [who, render] of RENDERERS) {
    for (const r of ADVERSARIAL) {
      const b = baseHtml(r.text), c = render(r.text);
      if (r.after !== undefined) { assert.equal(c, r.after, r.id + ", " + who + ": " + JSON.stringify(r.text)); assert.notEqual(c, b, r.id + " changes"); }
      else { assert.equal(c, b, r.id + ", " + who + ": " + JSON.stringify(r.text)); for (const k of r.keeps || []) assert.ok(c.includes(k), r.id + " keeps " + k + ": " + c); }
    }
    assert.deepEqual(ADVERSARIAL.filter((r) => render(r.text) !== baseHtml(r.text)).map((r) => r.id), ADVERSARIAL_CHANGED, who);
    const loss = byId(ADVERSARIAL, "A08");
    assert.equal(baseHtml(loss.text), "<p><em>foo</em>-bar/baz.md</p>\n", "the base grammar emphasised the word");
    assert.equal(render(loss.text), "<p>_foo_-bar/baz.md</p>\n", who + ": the accepted loss: the closer lies inside the token the walk links, so the pair is refused");
  }
  assert.equal(ADVERSARIAL.length, 20);
});

test("the user's own words take the same grammar: identical HTML to a reply's on every row of both tables", () => {
  chatExported();
  for (const r of [...CASES, ...ADVERSARIAL]) assert.equal(userHtml(r.text), chatHtml(r.text), r.id);
});

// ── the walk over the rendered DOM ───────────────────────────────────────────────────────────────────────────────────

test("the chat's walk links every wanted token whole over the chat's rendering, with the kernel's map holding the keys: both of C36's, the code span's, the fenced one's; a bare name in prose still does not link", () => {
  for (const [who, render] of RENDERERS) for (const r of [...CASES, ...ADVERSARIAL]) {
    assert.deepEqual(walkLinks(render(r.text), keysOf(r)), r.links, r.id + ", " + who + ": " + JSON.stringify(r.text) + " -> " + render(r.text));
  }
  for (const id of ["C05", "C39"]) {
    const r = byId(CASES, id);
    assert.deepEqual(r.links, [], id + ": a bare filename in prose is protected and not linked (the bare gate needs a code span)");
    assert.ok((r.keys || []).length > 0, id + " puts the bare names in the map to show that");
  }
  assert.deepEqual(byId(CASES, "C36").links.length, 2, "C36: one pair across two tokens, both linked");
});

test("the base grammar cuts every member row's token: the defect, reproduced (an em or strong opened or closed inside the path, and the walk finds no whole token)", () => {
  for (const id of MEMBERS) {
    const r = byId(CASES, id);
    const b = baseHtml(r.text);
    assert.match(b, /<(em|strong)>/, id + ": the base grammar emphasises inside the path: " + b);
    if (r.links.length === 0) continue;
    const got = walkLinks(b, keysOf(r));
    assert.ok(r.links.some((t) => !got.includes(t)), id + ": a wanted token is lost to the cut; the base walk linked " + JSON.stringify(got));
  }
});

// ── the mechanism's edges ────────────────────────────────────────────────────────────────────────────────────────────

test("a footnote reference inside a refused pair is numbered once: the built-in's body lex runs dry, and the body is lexed only when the pair stands", () => {
  for (const [who, render] of RENDERERS) {
    const out = render("_private [^1] /a-b/c_/d.md\n\n[^1]: the note");
    assert.match(out, /^<p>_private <sup class="md-fnref"><a href="#fn-1" id="fnref-1">1<\/a><\/sup> \/a-b\/c_\/d\.md<\/p>\n/, who + ": the pair refused, the reference numbered 1 with its first id: " + out);
    assert.doesNotMatch(out, /fnref-1-2/, "no second reference was counted for the same citation");
    assert.equal((out.match(/id="fnref-1"/g) || []).length, 1);
    const kept = render("_private [^1] word_ and /a-b/c_/d.md\n\n[^1]: the note");
    assert.match(kept, /^<p><em>private <sup class="md-fnref"><a href="#fn-1" id="fnref-1">1<\/a><\/sup> word<\/em> and \/a-b\/c_\/d\.md<\/p>\n/, who + ": a pair that stands keeps its body, the reference numbered once: " + kept);
  }
});

test("a file:// URI, a table cell, a list item, a heading and a quote are protected too; a `*` pair and the prose around a path render as before", () => {
  assert.equal(baseHtml("see file:///a-_b/c_/d.md now"), "<p>see file:///a-<em>b/c</em>/d.md now</p>\n");
  for (const [who, render] of RENDERERS) {
    assert.equal(render("see file:///a-_b/c_/d.md now"), "<p>see file:///a-_b/c_/d.md now</p>\n", who + ": the URI arm is a token the walk links, ungated");
    assert.match(render("| a | b |\n|---|---|\n| x | /a-_b/c_/d.md |"), /<td>\/a-_b\/c_\/d\.md<\/td>/, who);
    assert.equal(render("- see /a-_b/c_/d.md\n- and __init__.py"), "<ul>\n<li>see /a-_b/c_/d.md</li>\n<li>and __init__.py</li>\n</ul>\n", who);
    assert.equal(render("## /a-_b/c_/d.md"), "<h2>/a-_b/c_/d.md</h2>\n", who);
    assert.equal(render("> the note is /a-_b/c_/d.md"), "<blockquote>\n<p>the note is /a-_b/c_/d.md</p>\n</blockquote>\n", who);
    assert.equal(render("_x_ /a-_b/c_/d.md _y_"), "<p><em>x</em> /a-_b/c_/d.md <em>y</em></p>\n", who + ": emphasis on either side of a path stands");
    assert.equal(render("**x**/a-_b/c_/d.md"), "<p><strong>x</strong>/a-_b/c_/d.md</p>\n", who + ": a `*` pair glued to a path stands: `*` is not a path character");
  }
  assert.equal(userHtml("see /a-_b/c_/d.md\nnext _em_ line"), "<p>see /a-_b/c_/d.md<br>next <em>em</em> line</p>\n", "the user renderer keeps its one difference, hard breaks");
});

test("the instance boundary: the singleton (the viewer, the hover preview, the anchor map) keeps GitHub's rendering; the chat's two instances take the override and the shared list does not", () => {
  applyMdConfig();
  assert.equal(marked.parse("foo/__pycache__/bar.pyc"), "<p>foo/<strong>pycache</strong>/bar.pyc</p>\n", "the singleton renders a note as GitHub does (whether the viewer should follow is a separate decision)");
  chatExported();
  assert.equal(chatHtml("foo/__pycache__/bar.pyc"), "<p>foo/__pycache__/bar.pyc</p>\n");
  const CONFIG = read("md-config.ts"), CHAT = read("chat-md.ts"), RENDER = read("render.ts");
  const list = CONFIG.match(/export const mdExtensions: MarkedExtension\[\] = \[[\s\S]*?\n\];/)?.[0] || "";
  assert.ok(list, "the shared list is there");
  assert.doesNotMatch(list, /pathAwareEmphasis/, "the shared list, which the singleton takes, does not carry the override");
  assert.match(CONFIG, /^export const pathAwareEmphasis = \{\n {2}tokenizer: \{\n {4}emStrong\(this: Tokenizer, src: string, maskedSrc: string, prevChar = ""\) \{/m, "the override is an emStrong tokenizer override, delDoubleTilde's shape");
  assert.match(CONFIG, /^import \{ isFileUri, looksLikeBareFileName, looksLikeFilePath, PathTokenScanner, trailingPunct \} from "\.\/path-links";/m, "the scanner and the gates are the walk's own, imported");
  const override = CONFIG.slice(CONFIG.indexOf("const WHITESPACE_RE = "), CONFIG.indexOf("} as MarkedExtension;", CONFIG.indexOf("export const pathAwareEmphasis")));
  assert.ok(override.includes("function linkableRuns(") && override.includes("emStrong(this: Tokenizer"), "the override's code, from its first constant to its close");
  assert.doesNotMatch(override, /\[~\.|BARE_FILE_EXTS|A-Za-z0-9|\\\.\[|new RegExp\(/, "and never restated: no path grammar of its own in the override's code (a whitespace test is its one regex)");
  assert.match(CONFIG, /Tokenizer\.prototype\.emStrong\.call\(dry, src, maskedSrc, prevChar\)/, "the built-in decides the pair, on the dry stand-in");
  assert.match(CHAT, /^export const chatMarked = new Marked\(\{ gfm: true, breaks: false \}, \.\.\.mdExtensions, pathAwareEmphasis\);/m, "the reply instance");
  assert.match(CHAT, /^export const userMarked = new Marked\(\{ gfm: true, breaks: true \}, \.\.\.mdExtensions, pathAwareEmphasis\);/m, "the user instance");
  assert.match(RENDER, /^import \{ chatMdHtml, userMdHtml \} from "\.\/chat-md";/m);
  const mdFn = RENDER.match(/\nfunction md\(src: string[^\n]*?\): string \{[\s\S]*?\n\}/)?.[0] || "";
  assert.match(mdFn, /const dirty = chatMdHtml\(src\);/, "md() parses a reply on the chat instance");
  assert.doesNotMatch(mdFn, /marked\.parse/, "and no longer on the singleton");
  assert.match(RENDER, /function previewMdClean\(src: string\): HTMLElement \{\n\s*let clean: HTMLElement;\n\s*try \{ clean = sanitizeMd\(marked\.parse\(src\) as string\); \}/, "the hover preview stays on the singleton: a previewed file is a note, rendered as the viewer renders it");
  assert.doesNotMatch(read("file-view.ts"), /pathAwareEmphasis|chatMarked|chatMdHtml/, "the viewer takes none of it");
});
