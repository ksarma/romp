// Links inside a file the viewer shows (file-view-links.ts; the user 2026-09-07): URLs become anchors that open a
// new tab, paths become the chat's path links resolved against the shown file, a Markdown link's target follows the
// same two rules, and the text of every row reads exactly as the file's after the pass (the comments panel's Raw index
// verifies the rows against the file, anchor-map.ts). The grammar and the pass run for real over a small DOM stand-in
// (the path-links.test.ts idiom, grown to what the pass and the painters touch: splitText, insertBefore, a selector
// engine for closest and querySelectorAll); the interplay with the comment painters runs the real anchor-map.ts over
// the same stand-in. The viewer's wiring (where the pass runs, the body's delegate and its gesture, the close guard,
// the line scroll, the sheets) is pinned at source; the browser leg, where the sanitizer, the highlighter, the comments
// panel and the pointer are real, is file-view-links-browser.test.ts. Synthetic fixtures only: the notes-api world
// under /tmp/TESTHOST, a placeholder session id.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const UI = path.resolve(process.cwd(), "..", "ui", "webview");
const read = (f: string) => fs.readFileSync(path.join(UI, f), "utf8");
const VIEW = read("file-view.ts");
const LINKS = read("path-links.ts");
const MOD = read("file-view-links.ts");
const FILES = read("files.ts");
const FC = read("file-comments.ts");
const RENDER = read("render.ts");
const CHAT_CSS = read("styles.css");
const FEED_CSS = read("feed.css");

const SID = "11111111-2222-3333-4444-555555555555";
const FILE = "/tmp/TESTHOST/notes-api/src/app.py";
const DIR = "/tmp/TESTHOST/notes-api/src/";

// ── a DOM stand-in: text nodes that split, elements with attributes, a selector engine, fragments ─────
type Compound = { tag: string | null; classes: string[]; attrs: Array<[string, string | null]> };
function parseSel(sel: string): Compound[][] {
  return sel.split(",").map((g) => g.trim()).filter(Boolean).map((g) => g.split(/\s+/).map((s) => {
    const m = /^([a-zA-Z][\w-]*)?((?:\.[\w-]+)*)((?:\[[\w-]+(?:="[^"]*")?\])*)$/.exec(s);
    if (!m) throw new Error("stand-in: unsupported selector " + s);
    const classes = (m[2].match(/\.[\w-]+/g) || []).map((c) => c.slice(1));
    const attrs: Array<[string, string | null]> = [];
    for (const a of m[3].match(/\[[^\]]+\]/g) || []) { const am = /^\[([\w-]+)(?:="([^"]*)")?\]$/.exec(a)!; attrs.push([am[1], am[2] ?? null]); }
    return { tag: m[1] ? m[1].toUpperCase() : null, classes, attrs };
  }));
}
class Txt {
  nodeType = 3;
  parentNode: El | null = null;
  constructor(public data: string) {}
  get textContent(): string { return this.data; }
  get parentElement(): El | null { return this.parentNode; }
  get ownerDocument(): typeof doc { return doc; }
  splitText(off: number): Txt {
    const tail = new Txt(this.data.slice(off));
    this.data = this.data.slice(0, off);
    this.parentNode!.insertBefore(tail, this.nextSibling());
    return tail;
  }
  nextSibling(): El | Txt | null { const p = this.parentNode!; const i = p.childNodes.indexOf(this); return p.childNodes[i + 1] || null; }
  replaceWith(n: El | Txt | Frag): void {
    const p = this.parentNode!;
    const i = p.childNodes.indexOf(this);
    const kids = n instanceof Frag ? n.childNodes.slice() : [n];
    for (const k of kids) { if (k.parentNode) k.parentNode.removeChild(k); k.parentNode = p; }
    p.childNodes.splice(i, 1, ...kids);
    this.parentNode = null;
  }
}
class Frag { childNodes: Array<El | Txt> = []; appendChild(c: El | Txt): void { this.childNodes.push(c); } }
const kebab = (k: string) => k.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
class El {
  nodeType = 1;
  tagName: string;
  parentNode: El | null = null;
  childNodes: Array<El | Txt> = [];
  attrs = new Map<string, string>();
  role: string | null = null;
  onkeydown: unknown = null; onmousedown: unknown = null; onmouseup: unknown = null; onmouseleave: unknown = null; oncontextmenu: unknown = null; ondragstart: unknown = null;
  constructor(tag: string) { this.tagName = tag.toUpperCase(); }
  get ownerDocument(): typeof doc { return doc; }
  get parentElement(): El | null { return this.parentNode; }
  // reflected attributes, as the DOM has them
  get className(): string { return this.attrs.get("class") || ""; } set className(v: string) { this.attrs.set("class", v); }
  get title(): string { return this.attrs.get("title") || ""; } set title(v: string) { this.attrs.set("title", v); }
  get href(): string { return this.attrs.get("href") || ""; } set href(v: string) { this.attrs.set("href", v); }
  get target(): string { return this.attrs.get("target") || ""; } set target(v: string) { this.attrs.set("target", v); }
  get rel(): string { return this.attrs.get("rel") || ""; } set rel(v: string) { this.attrs.set("rel", v); }
  get tabIndex(): number { return this.attrs.has("tabindex") ? Number(this.attrs.get("tabindex")) : -1; } set tabIndex(v: number) { this.attrs.set("tabindex", String(v)); }
  get classes(): string[] { return this.className.split(/\s+/).filter(Boolean); }
  classList = { add: (...c: string[]) => { const s = new Set(this.classes); for (const x of c) s.add(x); this.className = [...s].join(" "); }, contains: (c: string) => this.classes.includes(c) };
  dataset: Record<string, string> = new Proxy({} as Record<string, string>, {
    get: (_, k) => this.attrs.get("data-" + kebab(String(k))) as string,
    set: (_, k, v) => { this.attrs.set("data-" + kebab(String(k)), String(v)); return true; },
    has: (_, k) => this.attrs.has("data-" + kebab(String(k))),
  });
  get textContent(): string { return this.childNodes.map((c) => c.textContent).join(""); }
  set textContent(v: string) { for (const c of this.childNodes) c.parentNode = null; this.childNodes = []; if (v !== "") this.appendChild(new Txt(v)); }
  private detach(n: El | Txt): void { const p = n.parentNode; if (p) { const i = p.childNodes.indexOf(n); if (i >= 0) p.childNodes.splice(i, 1); n.parentNode = null; } }
  appendChild<T extends El | Txt>(n: T): T { this.detach(n); this.childNodes.push(n); n.parentNode = this; return n; }
  insertBefore<T extends El | Txt>(n: T, ref: El | Txt | null): T {
    if (!ref) return this.appendChild(n);
    this.detach(n);
    const i = this.childNodes.indexOf(ref);
    this.childNodes.splice(i < 0 ? this.childNodes.length : i, 0, n); n.parentNode = this; return n;
  }
  removeChild<T extends El | Txt>(n: T): T { this.detach(n); return n; }
  setAttribute(k: string, v: string): void { this.attrs.set(k, v); }
  getAttribute(k: string): string | null { return this.attrs.has(k) ? (this.attrs.get(k) as string) : null; }
  hasAttribute(k: string): boolean { return this.attrs.has(k); }
  removeAttribute(k: string): void { this.attrs.delete(k); }
  contains(n: El | Txt | null): boolean { for (let x: El | Txt | null = n; x; x = x.parentNode) if (x === this) return true; return false; }
  private fits(c: Compound): boolean {
    return (!c.tag || c.tag === this.tagName) && c.classes.every((k) => this.classes.includes(k))
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
}
function textNodesOf(root: El): Txt[] {
  const out: Txt[] = [];
  const walk = (n: El) => { for (const c of n.childNodes) { if (c instanceof Txt) out.push(c); else walk(c); } };
  walk(root);
  return out;
}
const doc = {
  createElement: (tag: string) => new El(tag),
  createTextNode: (s: string) => new Txt(s),
  createDocumentFragment: () => new Frag(),
  createTreeWalker: (root: El) => { const nodes = textNodesOf(root); let i = 0; return { nextNode: () => (i < nodes.length ? nodes[i++] : null) }; },
  activeElement: null as El | null,
};
(globalThis as any).NodeFilter = { SHOW_TEXT: 4 };
(globalThis as any).document = doc;

// ── builders: what codeBlock's DOM looks like (one .fv-cl row per line, hljs spans inside) ─────────
const el = (tag: string, cls?: string, ...kids: Array<El | Txt | string>): El => {
  const e = new El(tag); if (cls) e.className = cls;
  for (const k of kids) e.appendChild(typeof k === "string" ? new Txt(k) : k);
  return e;
};
const row = (...kids: Array<El | Txt | string>): El => el("span", "fv-cl", el("span", "fv-ct", ...kids));
const code = (...rows: El[]): El => el("code", "hljs", ...rows);
const links = (root: El) => root.querySelectorAll(".file-uri-link");
const urls = (root: El) => root.querySelectorAll("a.fv-url");

// ── the URL grammar ───────────────────────────────────────────────────────────────────────────────
test("urlSegments: http and https URLs, trailing sentence punctuation left out, a paren balanced inside kept, one closing the sentence's not", async () => {
  const { urlSegments } = await import("./file-view-links");
  const hrefs = (s: string) => urlSegments(s).filter((x) => x.href).map((x) => x.href);
  assert.deepEqual(hrefs("see https://example.invalid/a/b?x=1&y=2 now"), ["https://example.invalid/a/b?x=1&y=2"]);
  assert.deepEqual(hrefs("plain http://example.invalid:8080/p too"), ["http://example.invalid:8080/p"]);
  assert.deepEqual(hrefs("HTTPS://EXAMPLE.invalid/X"), ["HTTPS://EXAMPLE.invalid/X"], "the scheme's case is the browser's business");
  assert.deepEqual(hrefs("ends https://example.invalid/a."), ["https://example.invalid/a"]);
  assert.deepEqual(hrefs("ends https://example.invalid/a, then"), ["https://example.invalid/a"]);
  assert.deepEqual(hrefs("ends https://example.invalid/a?q=1!?"), ["https://example.invalid/a?q=1"]);
  assert.deepEqual(hrefs("(see https://example.invalid/a/b)"), ["https://example.invalid/a/b"], "the sentence's paren");
  assert.deepEqual(hrefs("(see https://example.invalid/a/b)."), ["https://example.invalid/a/b"]);
  assert.deepEqual(hrefs("https://example.invalid/wiki/Foo_(bar) x"), ["https://example.invalid/wiki/Foo_(bar)"], "a paren opened inside the URL closes inside it");
  assert.deepEqual(hrefs("[https://example.invalid/a]"), ["https://example.invalid/a"]);
  assert.deepEqual(hrefs("<https://example.invalid/a>"), ["https://example.invalid/a"], "an autolink's angle brackets");
  assert.deepEqual(hrefs('url = "https://example.invalid/api/v1"'), ["https://example.invalid/api/v1"], "a quoted string in code");
  assert.deepEqual(hrefs("url = 'https://example.invalid/x'; y = `https://example.invalid/z`"), ["https://example.invalid/x", "https://example.invalid/z"]);
  // not URLs: a bare scheme, a scheme with no host, other schemes, a hostname alone
  for (const s of ["https://", "http:// x", "https:///nohost", "ftp://example.invalid/a", "example.invalid/a/b.html", "file:///tmp/TESTHOST/a.md"]) {
    assert.deepEqual(hrefs(s), [], s);
  }
  // the runs reassemble to the text, always
  for (const s of ["a https://example.invalid/x) b http://y.invalid/z. c", "no urls here", "", "https://example.invalid/(a)(b))"]) {
    assert.equal(urlSegments(s).map((x) => x.text).join(""), s, JSON.stringify(s));
  }
  assert.deepEqual(hrefs("https://example.invalid/(a)(b))"), ["https://example.invalid/(a)(b)"], "two balanced pairs kept, the extra closer left");
});

// ── the path gate and the resolution ─────────────────────────────────────────────────────────────
test("viewerPathGate, the token alone: a slash and a letter-led extension on the last segment; anchored dotfiles; a hostname-shaped first segment and a `~user` home are refused", async () => {
  const { viewerPathGate } = await import("./file-view-links");
  for (const p of ["docs/a.md", "ui/webview/x.ts", "/tmp/TESTHOST/notes-api/a.py", "~/notes/plan.md", "./x.py", "../y.ts", "~/.zshrc", "./.env",
                   "file:///tmp/TESTHOST/a.pdf", "file://localhost/tmp/TESTHOST/a.pdf", "a/b.h5", "img/photo.jpeg", "data/out.tar.gz", "src/mod.d.ts",
                   "a.b/c.md", "notes.d/x.md"]) {
    assert.equal(viewerPathGate(p), true, p);
  }
  for (const p of ["./foo", "/api/users", "/usr/bin", "~/code", "1/2.5", "and/or", "TCP/IP", "config/.env", "kernel.py", "a/b.123",
                   "img/photo.jpeg2000x", "x/y", "react/jsx-runtime", "a/b.", "../", "./",
                   "www.example.org/docs/index.html", "WWW.example.org/x.html", "example.com/index.html", "docs.example.invalid/a.md", "sub.example.co.uk/a/b.md",
                   "~user/x.md", "~user/.zshrc"]) {
    assert.equal(viewerPathGate(p), false, p);
  }
});

test("viewerPathGate, with the line: a token glued to what stands before it (a substitution, a scope, a drive, a host) is not one, and an unanchored token is not an import's specifier; an opener or the line's start admits it", async () => {
  const { viewerPathGate } = await import("./file-view-links");
  const at = (text: string, tok: string) => ({ text, at: text.indexOf(tok) });
  for (const [text, tok] of [
    ['cp "$HOME/docs/a.md" ./out/', "HOME/docs/a.md"], ["cat ${ROOT}/src/x.py", "/src/x.py"], ["SRC = $(ROOT)/src/main.c", "/src/main.c"],
    ["const s = `${dir}/out.json`;", "/out.json"], ['f"{base}/out.csv"', "/out.csv"], ["path: ${HOME}/notes/a.md", "/notes/a.md"],
    ['import x from "@scope/pkg/dist/index.js";', "scope/pkg/dist/index.js"], ["C:/Users/x/file.txt", "/Users/x/file.txt"],
    ["git clone git@github.invalid:user/repo.git", "user/repo.git"], ["a%s/x.md", "s/x.md"], ["x#/docs/a.md", "/docs/a.md"],
    ['import b from "lodash/fp.js";', "lodash/fp.js"], ['const x = require("pkg/sub.js");', "pkg/sub.js"], ['export * from "pkg/sub.js";', "pkg/sub.js"],
    ['import "pkg/x.css";', "pkg/x.css"], ["const m = await import('pkg/m.mjs');", "pkg/m.mjs"],
  ] as const) {
    assert.equal(viewerPathGate(tok, at(text, tok)), false, text);
  }
  for (const [text, tok] of [
    ['cp "docs/a.md" ./out/', "docs/a.md"], ["see docs/a.md here", "docs/a.md"], ["docs/a.md", "docs/a.md"], ["x=/docs/a.md", "/docs/a.md"],
    ["(see /docs/a.md)", "/docs/a.md"], ["[docs/a.md]", "docs/a.md"], ['<img src="docs/a.png">', "docs/a.png"], ["a, docs/a.md", "docs/a.md"],
    ["\tdocs/a.md", "docs/a.md"], ["a|docs/a.md", "docs/a.md"], ["{docs/a.md}", "docs/a.md"],
    ['import s from "./app.css";', "./app.css"], ['import b from "../lib/util.js";', "../lib/util.js"], ['<script src="lib/x.js">', "lib/x.js"],
    ["open(~/notes/a.md)", "~/notes/a.md"], ["readme = 'file:///tmp/TESTHOST/README.md'", "file:///tmp/TESTHOST/README.md"],
  ] as const) {
    assert.equal(viewerPathGate(tok, at(text, tok)), true, text);
  }
});

test("normalizePath and resolveViewerPath: `.` and `..` are resolved once, here; relative tokens join the shown file's directory; absolute, ~/ and local file:// pass through; a file with no directory joins nothing", async () => {
  const { normalizePath, resolveViewerPath } = await import("./file-view-links");
  for (const [p, want] of [["/a/b/../c.md", "/a/c.md"], ["/../x.md", "/x.md"], ["/a/./b//c.md", "/a/b/c.md"], ["~/a/../b.md", "~/b.md"], ["~/../x.md", "~/../x.md"],
                           ["docs/../src/app.py", "src/app.py"], ["../../x.md", "../../x.md"], ["a/../../x.md", "../x.md"], ["./x.py", "x.py"], ["a/b/", "a/b/"], ["/", "/"],
                           ["docs/a.md", "docs/a.md"], ["/tmp/TESTHOST/x.md", "/tmp/TESTHOST/x.md"], ["", ""]] as const) {
    assert.equal(normalizePath(p), want, p);
  }
  assert.equal(resolveViewerPath("docs/a.md", FILE), DIR + "docs/a.md");
  assert.equal(resolveViewerPath("./x.py", FILE), DIR + "x.py", "./ is resolved here");
  assert.equal(resolveViewerPath("../y.ts", FILE), "/tmp/TESTHOST/notes-api/y.ts", ".. is resolved here: the title bar, the Recent list and the folder link all see one spelling");
  assert.equal(resolveViewerPath("/tmp/TESTHOST/other/../z.md", FILE), "/tmp/TESTHOST/z.md");
  assert.equal(resolveViewerPath("~/notes/plan.md", FILE), "~/notes/plan.md", "the kernel expands ~ on the session's machine");
  assert.equal(resolveViewerPath("file:///tmp/TESTHOST/a%20b.pdf", FILE), "/tmp/TESTHOST/a b.pdf", "a URI's own path, percent-decoded");
  assert.equal(resolveViewerPath("file://localhost/tmp/TESTHOST/a.pdf", FILE), "/tmp/TESTHOST/a.pdf", "localhost is this machine");
  assert.equal(resolveViewerPath("docs/a.md", "README.md"), "docs/a.md", "a file named without a directory: the token as written, for the session's cwd");
  assert.equal(resolveViewerPath("a.md", "docs/README.md"), "docs/a.md", "a relative shown file keeps its relative directory");
  assert.equal(resolveViewerPath("../a.md", "docs/README.md"), "a.md");
});

test("a file:// URI is a path only with an empty authority or localhost: file://host/path names another machine and is prose to the walk; a line after a URI is the line, not the path", async () => {
  const { isFileUri, fileUriToPath } = await import("./path-links");
  for (const u of ["file:///tmp/TESTHOST/a.md", "file://localhost/tmp/a.md", "FILE:///tmp/a.md", "file://LOCALHOST/x"]) assert.equal(isFileUri(u), true, u);
  for (const u of ["file://evil.invalid/share/x.md", "file://TESTHOST/x.md", "file://localhost", "file:/x.md", "files:///x", "file://localhostx/y"]) assert.equal(isFileUri(u), false, u);
  assert.equal(fileUriToPath("file://localhost/tmp/a%20b.md"), "/tmp/a b.md");
  assert.equal(fileUriToPath("file://evil.invalid/share/x.md"), "file://evil.invalid/share/x.md", "not a local path: returned as written, never as a relative path");
  const { linkifyFileText } = await import("./file-view-links");
  const c = code(row('y = "file://evil.invalid/share/x.md"'), row("z = 'file:///tmp/TESTHOST/x.md:12'"), row("w = 'file://localhost/tmp/TESTHOST/y.md#L7'"), row("v = file:///tmp/TESTHOST/z.md:3:4 end"));
  const before = c.childNodes.map((r) => r.textContent);
  linkifyFileText(c as unknown as HTMLElement, FILE);
  assert.deepEqual(c.childNodes.map((r) => r.textContent), before);
  assert.deepEqual(links(c).map((x) => [x.textContent, x.dataset.path, x.dataset.line, x.title]), [
    ["file:///tmp/TESTHOST/x.md:12", "/tmp/TESTHOST/x.md", "12", "Open /tmp/TESTHOST/x.md:12"],
    ["file://localhost/tmp/TESTHOST/y.md#L7", "/tmp/TESTHOST/y.md", "7", "Open /tmp/TESTHOST/y.md:7"],
    ["file:///tmp/TESTHOST/z.md:3:4", "/tmp/TESTHOST/z.md", "3", "Open /tmp/TESTHOST/z.md:3"],
  ], "the host-bearing URI stays text; the line rides in the link and off the path");
});

// ── the pass over a code body ─────────────────────────────────────────────────────────────────────
test("the pass, executed over codeBlock's rows: URLs in a comment become anchors, quoted paths become path links resolved against the file, :line rides in, prose and identifiers stay", async () => {
  const { linkifyFileText } = await import("./file-view-links");
  const c = code(
    row(el("span", "hljs-comment", "# see https://example.invalid/docs/setup.html, then docs/guide.md:12.")),
    row("cfg = open(", el("span", "hljs-string", '"data/config.json"'), ")"),
    row("from . import util  # and/or 24/7 x = 1/2.5 /api/users ./foo"),
    row("readme = ", el("span", "hljs-string", "'file:///tmp/TESTHOST/notes-api/README.md'")),
    row("see ", el("span", "hljs-string", '"ui/x.ts#L7"'), " and ", el("span", "hljs-string", '"ui/y.ts:12abc"')),
  );
  const before = c.childNodes.map((r) => r.textContent);
  linkifyFileText(c as unknown as HTMLElement, FILE);
  // every row's text reads exactly as before: the pass adds elements around text and changes no character
  assert.deepEqual(c.childNodes.map((r) => r.textContent), before);
  // the URL: an anchor that opens a new tab, its text the URL without the sentence's comma, not draggable (a drag on it selects)
  const a = urls(c);
  assert.equal(a.length, 1);
  assert.equal(a[0].textContent, "https://example.invalid/docs/setup.html");
  assert.equal(a[0].href, "https://example.invalid/docs/setup.html");
  assert.equal(a[0].target, "_blank"); assert.equal(a[0].rel, "noopener noreferrer");
  assert.equal(a[0].title, "https://example.invalid/docs/setup.html");
  assert.equal(a[0].getAttribute("draggable"), "false");
  assert.equal(a[0].closest(".hljs-comment")!.className, "hljs-comment", "inside the highlight's own span");
  assert.equal(links(a[0]).length, 0, "the URL's path-shaped tail is not a path link inside the anchor");
  // the paths: the chat's span, the act, the resolved target, the line
  const l = links(c);
  assert.deepEqual(l.map((x) => x.textContent), ["docs/guide.md:12", "data/config.json", "file:///tmp/TESTHOST/notes-api/README.md", "ui/x.ts#L7", "ui/y.ts"]);
  assert.deepEqual(l.map((x) => x.dataset.path), [DIR + "docs/guide.md", DIR + "data/config.json", "/tmp/TESTHOST/notes-api/README.md", DIR + "ui/x.ts", DIR + "ui/y.ts"]);
  assert.deepEqual(l.map((x) => x.dataset.line), ["12", undefined, undefined, "7", undefined]);
  assert.equal(l[0].title, "Open " + DIR + "docs/guide.md:12");
  assert.equal(l[1].title, "Open " + DIR + "data/config.json");
  for (const x of l) { assert.equal(x.dataset.act, "openpath"); assert.equal(x.role, "link"); assert.equal(x.tabIndex, 0); assert.equal(typeof x.onmousedown, "function"); }
  assert.equal(l[1].parentNode!.textContent, '"data/config.json"', "the string's quotes stay outside the link, as text");
  // `.` after :12 is the sentence's, left as text; `:12abc` is not a line, so ui/y.ts links alone and `:12abc"` stays text
  assert.equal(textNodesOf(c.childNodes[0] as El).map((t) => t.data).pop(), ".");
  assert.equal(textNodesOf(c.childNodes[4] as El).map((t) => t.data).pop(), ':12abc"');
});

test("the pass reads a line, not a node: a highlight's substitution span cannot turn a path's tail into an absolute link, a token the highlight cut through is left as it is, and so is a URL", async () => {
  const { linkifyFileText } = await import("./file-view-links");
  // what hljs makes of `cp "$HOME/docs/a.md" ./out/` (bash), `${ROOT}/src/x.py`, `$(ROOT)/src/main.c` (makefile), a TS template
  // literal, a Python f-string and a YAML value: the substitution in a span of its own, the path's tail in the node after it
  const c = code(
    row("cp ", el("span", "hljs-string", '"', el("span", "hljs-variable", "$HOME"), '/docs/a.md"'), " ./out/"),
    row("cat ", el("span", "hljs-variable", "${ROOT}"), "/src/x.py"),
    row("SRC = ", el("span", "hljs-variable", "$(ROOT)"), "/src/main.c"),
    row("const s = ", el("span", "hljs-string", "`", el("span", "hljs-subst", "${dir}"), "/out.json`"), ";"),
    row("p = ", el("span", "hljs-string", 'f"', el("span", "hljs-subst", "{base}"), '/out.csv"')),
    row("path: ", el("span", "hljs-string", el("span", "hljs-variable", "${HOME}"), "/notes/a.md")),
    row("x = ", el("span", "hljs-string", '"docs/'), el("span", "hljs-string", 'c.md"')),   // one token across two nodes: left as it is
    row("see ", el("span", "hljs-string", '"docs/a.md"'), " and ", el("span", "hljs-comment", "# https://example.invalid/x")),
    row("u = ", el("span", "hljs-string", "`https://example.invalid/", el("span", "hljs-subst", "${host}"), "/x`")),
    row("q = ", el("span", "hljs-string", '"docs/b.md'), ":", el("span", "hljs-number", "12"), '"'),   // the line reference cut off the path: the path links, the line stays text
  );
  const before = c.childNodes.map((r) => r.textContent);
  linkifyFileText(c as unknown as HTMLElement, FILE);
  assert.deepEqual(c.childNodes.map((r) => r.textContent), before);
  assert.deepEqual(links(c).map((x) => [x.textContent, x.dataset.path, x.dataset.line]), [["docs/a.md", DIR + "docs/a.md", undefined], ["docs/b.md", DIR + "docs/b.md", undefined]],
    "the two real paths; no fabricated /docs/a.md, /src/x.py, /src/main.c, /out.json, /out.csv or /notes/a.md, and the cut docs/c.md stays text");
  assert.deepEqual(urls(c).map((x) => x.href), ["https://example.invalid/x"], "a URL a substitution cuts through is not one");
});

test("the pass links nothing in text that is not a URL or a file: identifiers, imports, fractions, routes, folders, sites", async () => {
  const { linkifyFileText } = await import("./file-view-links");
  const c = code(
    row("from . import util"), row("import x from \"react/jsx-runtime\""), row("import y from \"lodash/fp.js\""), row("x = 1/2.5 + a/b"), row("app.get(\"/api/users\")"),
    row("cd /usr/bin && ls ~/code"), row("and/or read/write TCP/IP"), row("np.array(kernel.py)"), row("https://"),
    row("see www.example.org/docs/index.html or example.com/index.html"), row("git clone git@github.invalid:user/repo.git"), row("C:/Users/x/file.txt"), row("cat ~user/x.md"),
  );
  const before = c.textContent;
  linkifyFileText(c as unknown as HTMLElement, FILE);
  assert.equal(links(c).length, 0); assert.equal(urls(c).length, 0);
  assert.equal(c.textContent, before);
});

test("escaping: <, &, > and quotes around a link stay literal text; text inside an existing anchor is skipped; an empty body is a no-op", async () => {
  const { linkifyFileText } = await import("./file-view-links");
  const c = code(
    row('if (a < b && c > "docs/a.md") go(https://example.invalid/x?a=1&b=2)'),
    row(el("a", "", "docs/b.md and https://example.invalid/y")),      // an author's anchor: left as it is
  );
  const before = c.childNodes.map((r) => r.textContent);
  linkifyFileText(c as unknown as HTMLElement, FILE);
  assert.deepEqual(c.childNodes.map((r) => r.textContent), before);
  const first = c.childNodes[0] as El;
  const texts = textNodesOf(first).map((t) => t.data);
  assert.deepEqual(texts, ['if (a < b && c > "', "docs/a.md", '") go(', "https://example.invalid/x?a=1&b=2", ")"]);
  assert.equal(links(first).length, 1); assert.equal(urls(first).length, 1);
  assert.equal(urls(first)[0].href, "https://example.invalid/x?a=1&b=2", "the & is a character of the URL, not an entity");
  assert.equal(links(c.childNodes[1] as El).length + urls(c.childNodes[1] as El).length, 0, "the anchor's text is not re-linked");
  const empty = el("code", "hljs");
  linkifyFileText(empty as unknown as HTMLElement, FILE);
  assert.equal(empty.childNodes.length, 0);
});

// ── Markdown links ────────────────────────────────────────────────────────────────────────────────
test("viewerLinkTarget (marked's walkTokens, before the sanitizer): a same-directory `name.ext:12` and a local file:// URI take the form the sanitizer keeps; everything else is left as written; only link tokens are touched", async () => {
  const { viewerLinkTarget, viewerWalkTokens } = await import("./file-view-links");
  assert.equal(viewerLinkTarget("notes.md:7"), "./notes.md:7");
  assert.equal(viewerLinkTarget("README.md:12:3"), "./README.md:12:3");
  assert.equal(viewerLinkTarget("app.py:7#x"), "./app.py:7#x");
  assert.equal(viewerLinkTarget("file:///tmp/TESTHOST/a.md"), "/tmp/TESTHOST/a.md");
  assert.equal(viewerLinkTarget("file://localhost/tmp/TESTHOST/a.md"), "/tmp/TESTHOST/a.md");
  for (const h of ["docs/a.md:7", "./a.md:7", "../a.md:7", "a.md#L7", "https://example.invalid/x", "mailto:someone@example.invalid", "tel:12345",
                   "javascript:alert(1)", "file://evil.invalid/x.md", "Makefile:12", "#section", "?x=1", "notes.md", ""]) {
    assert.equal(viewerLinkTarget(h), h, JSON.stringify(h));
  }
  const tok = { type: "link", href: "notes.md:7" }; viewerWalkTokens(tok); assert.equal(tok.href, "./notes.md:7");
  const img = { type: "image", href: "notes.md:7" }; viewerWalkTokens(img); assert.equal(img.href, "notes.md:7", "a figure's src is rewriteFigureSrcs's business");
});

test("linkMarkdownAnchors: a URL target opens a tab, a file target becomes a path link on the anchor itself (label intact, path normalized), a query alone opens a tab, a fragment alone is the viewer's, a stripped target is a dead link that says why", async () => {
  const { linkMarkdownAnchors, DEAD_LINK_TITLE, noSectionTitle } = await import("./file-view-links");
  const md = "/tmp/TESTHOST/notes-api/docs/guide.md";
  const A = (href: string, ...kids: Array<El | string>) => { const a = el("a", "", ...kids); a.setAttribute("href", href); return a; };
  const web = A("https://example.invalid/x", "web"), mail = A("mailto:someone@example.invalid", "mail"), proto = A("//example.invalid/p", "p");
  const rel = A("../src/app.py", el("strong", "", "the"), " app"), enc = A("my%20notes.md", "notes"), abs = A("/tmp/TESTHOST/other.md", "abs");
  const lineHash = A("../src/app.py#L12", "l12"), lineColon = A("../src/app.py:7", "l7"), same = A("./notes.md:7", "same"), query = A("a.md?x=1#top", "q");
  const qOnly = A("?x=1", "qo"), frag = A("#section", "here"), fragHit = A("#top", "top"), dead = el("a", "", "dead"), named = el("a", "", "");
  named.setAttribute("name", "anchor");
  const target = el("h2", "", "Top"); target.setAttribute("id", "top");
  const box = el("div", "fileview-md", target, el("p", "", web, mail, proto, rel, enc, abs, lineHash, lineColon, same, query, qOnly, frag, fragHit, dead, named));
  linkMarkdownAnchors(box as unknown as HTMLElement, md);
  for (const a of [web, mail, proto]) { assert.equal(a.getAttribute("target"), "_blank", a.href); assert.equal(a.getAttribute("rel"), "noopener"); assert.equal(a.dataset.act, undefined); }
  assert.equal(web.href, "https://example.invalid/x", "the href stays");
  for (const a of [rel, enc, abs, lineHash, lineColon, same, query]) {
    assert.equal(a.getAttribute("href"), null, "the href comes off: the browser must not follow it");
    assert.equal(a.dataset.act, "openpath"); assert.equal(a.role, "link"); assert.equal(a.tabIndex, 0);
    assert.ok(a.classes.includes("file-uri-link"), "the shared class on the anchor");
    assert.equal(a.target, "", "not a tab");
  }
  assert.equal(rel.dataset.path, "/tmp/TESTHOST/notes-api/src/app.py", "resolved against the shown file and normalized");
  assert.equal(rel.childNodes.length, 2); assert.equal((rel.childNodes[0] as El).tagName, "STRONG", "the label's nested formatting is kept");
  assert.equal(rel.textContent, "the app");
  assert.equal(enc.dataset.path, "/tmp/TESTHOST/notes-api/docs/my notes.md", "marked's percent-encoding undone");
  assert.equal(abs.dataset.path, "/tmp/TESTHOST/other.md");
  assert.equal(lineHash.dataset.path, "/tmp/TESTHOST/notes-api/src/app.py"); assert.equal(lineHash.dataset.line, "12");
  assert.equal(lineHash.getAttribute("title"), "Open /tmp/TESTHOST/notes-api/src/app.py:12");
  assert.equal(lineColon.dataset.line, "7");
  assert.equal(same.dataset.path, "/tmp/TESTHOST/notes-api/docs/notes.md", "the same-directory target the hook prefixed with ./, resolved and normalized");
  assert.equal(same.dataset.line, "7"); assert.equal(same.getAttribute("title"), "Open /tmp/TESTHOST/notes-api/docs/notes.md:7");
  assert.equal(query.dataset.path, "/tmp/TESTHOST/notes-api/docs/a.md", "the query and a plain fragment are dropped from the path");
  assert.equal(query.dataset.line, undefined);
  // a query alone: a web-style link to the page's own address, a new tab as main had it, never this document
  assert.equal(qOnly.getAttribute("href"), "?x=1"); assert.equal(qOnly.getAttribute("target"), "_blank"); assert.equal(qOnly.getAttribute("rel"), "noopener noreferrer"); assert.equal(qOnly.dataset.act, undefined);
  // a fragment alone: the viewer's click; with no element of that id the link is dead and says so
  assert.equal(frag.getAttribute("href"), "#section"); assert.ok(frag.classes.includes("fv-frag") && frag.classes.includes("fv-dead"), frag.className);
  assert.equal(frag.dataset.frag, undefined); assert.equal(frag.getAttribute("title"), noSectionTitle("section"));
  assert.ok(fragHit.classes.includes("fv-frag") && !fragHit.classes.includes("fv-dead"), fragHit.className);
  assert.equal(fragHit.dataset.frag, "top"); assert.equal(fragHit.getAttribute("title"), "Go to top");
  // an anchor the sanitizer stripped: dead, with the reason; a named target never was a link and is left alone
  assert.ok(dead.classes.includes("fv-dead")); assert.equal(dead.getAttribute("title"), DEAD_LINK_TITLE);
  assert.equal(named.getAttribute("class"), null); assert.equal(named.getAttribute("title"), null);
});

test("in a rendered body the prose's bare paths link under the viewer's gate, a fenced block's URL links, and inline code's bare filename does not", async () => {
  const { linkifyFileText } = await import("./file-view-links");
  const md = "/tmp/TESTHOST/notes-api/docs/guide.md";
  const marked = el("a", "", "https://example.invalid/auto"); marked.setAttribute("href", "https://example.invalid/auto");
  const box = el("div", "fileview-md",
    el("p", "", "Read ../src/app.py:3 and ", el("code", "", "setup.py"), " then ", marked, "."),
    el("pre", "", el("code", "language-bash hljs", "curl https://example.invalid/dl -o data/x.json")),
  );
  const before = box.textContent;
  linkifyFileText(box as unknown as HTMLElement, md);
  assert.equal(box.textContent, before);
  const l = links(box);
  assert.deepEqual(l.map((x) => x.textContent), ["../src/app.py:3", "data/x.json"], "the prose path with its line, the fenced block's path; not the backticked bare filename");
  assert.equal(l[0].dataset.path, "/tmp/TESTHOST/notes-api/src/app.py"); assert.equal(l[0].dataset.line, "3");
  assert.equal(l[1].dataset.path, "/tmp/TESTHOST/notes-api/docs/data/x.json");
  const u = urls(box);
  assert.deepEqual(u.map((x) => x.href), ["https://example.invalid/dl"], "the fenced block's URL; marked's own anchor is not wrapped twice");
});

// ── the comment painters over a body with links in it (the real anchor-map.ts) ────────────────────
test("a comment highlight painted over a line with a link, a highlight spanning a link, and a selection anchored inside a link all map and paint against the unchanged text", async () => {
  const { linkifyFileText } = await import("./file-view-links");
  const { paintRaw, mapRawSelection } = await import("./anchor-map");
  const source = 'x = 1\ncfg = open("data/config.json")  # see https://example.invalid/d\ny = 2\n';
  const c = code(row("x = 1"), row("cfg = open(", el("span", "hljs-string", '"data/config.json"'), ")  ", el("span", "hljs-comment", "# see https://example.invalid/d")), row("y = 2"));
  linkifyFileText(c as unknown as HTMLElement, FILE);
  const link = links(c)[0], url = urls(c)[0];
  // a highlight over the whole second line: marks land inside the link and the anchor as well as around them
  const line2 = { start: source.indexOf("cfg"), end: source.indexOf("\ny = 2") };
  const marks = paintRaw(c as unknown as Element, source, line2, "fc-hl", { id: "c1" }) as unknown as El[];
  assert.ok(marks.length >= 3, "several marks: one per text node the row holds");
  assert.ok(marks.some((m) => link.contains(m)), "a mark inside the path link (the link is not split)");
  assert.ok(marks.some((m) => url.contains(m)), "a mark inside the URL anchor");
  assert.equal(link.textContent, "data/config.json"); assert.equal(url.textContent, "https://example.invalid/d");
  assert.equal((c.childNodes[1] as El).textContent, 'cfg = open("data/config.json")  # see https://example.invalid/d', "the row's text is unchanged by links and marks alike");
  // a highlight that starts before the link and ends inside it
  const c2 = code(row("see docs/a.md here"));
  linkifyFileText(c2 as unknown as HTMLElement, FILE);
  const src2 = "see docs/a.md here\n";
  const m2 = paintRaw(c2 as unknown as Element, src2, { start: 0, end: src2.indexOf("a.md") }, "fc-hl") as unknown as El[];
  assert.equal(m2.map((m) => m.textContent).join(""), "see docs/", "the mark covers the words before and the first half of the link");
  assert.equal(links(c2)[0].textContent, "docs/a.md", "the link still reads whole");
  assert.equal(c2.textContent, "see docs/a.md here");
  // a selection whose anchor sits inside the link's text (a drag that started on it) maps to the source
  const c3 = code(row("see docs/a.md here"));
  linkifyFileText(c3 as unknown as HTMLElement, FILE);
  const tn = textNodesOf(links(c3)[0])[0];
  const r = mapRawSelection({ isCollapsed: false, anchorNode: tn as unknown as Node, anchorOffset: 5, focusNode: textNodesOf(c3)[2] as unknown as Node, focusOffset: 3 } as unknown as Selection, c3 as unknown as Element, src2);
  assert.ok(r.ok, "maps"); if (r.ok) { assert.equal(r.quote, "a.md he"); assert.deepEqual(r.range, { start: 9, end: 16 }); }
});

// ── the gesture helpers, executed ─────────────────────────────────────────────────────────────────
test("wantsOwnTab reads a Cmd/Ctrl-click or the middle button; openFileTab opens the kernel's /file URL in a tab with the opener severed, reports a blocked popup, and stands down off the web", async () => {
  const { wantsOwnTab, openFileTab, fileUrl } = await import("./preview");
  assert.equal(wantsOwnTab({ metaKey: true }), true); assert.equal(wantsOwnTab({ ctrlKey: true }), true); assert.equal(wantsOwnTab({ button: 1 }), true);
  assert.equal(wantsOwnTab({}), false); assert.equal(wantsOwnTab({ button: 0 }), false); assert.equal(wantsOwnTab(null), false); assert.equal(wantsOwnTab(undefined), false);
  const g = globalThis as any;
  const saved = { loc: g.location, win: g.window };
  try {
    const calls: unknown[][] = [];
    const handle: { opener: unknown } = { opener: { theDashboard: true } };
    g.location = { protocol: "https:" }; g.window = { open: (...a: unknown[]) => { calls.push(a); return handle; } };
    assert.equal(openFileTab("/tmp/TESTHOST/notes-api/docs/guide.md", SID), true);
    assert.deepEqual(calls, [[fileUrl("/tmp/TESTHOST/notes-api/docs/guide.md", SID), "_blank"]], "the same-origin file URL, a new tab, no noopener feature (it returns null even on success)");
    assert.equal(calls[0][0], "/file?path=%2Ftmp%2FTESTHOST%2Fnotes-api%2Fdocs%2Fguide.md&sid=" + SID);
    assert.equal(handle.opener, null, "severed on the handle: a link inside the opened file must not hold the dashboard");
    g.window = { open: () => null };
    assert.equal(openFileTab("/tmp/TESTHOST/x.md", SID), false, "blocked: the caller's viewer takes over");
    let tried = false;
    g.location = { protocol: "vscode-webview:" }; g.window = { open: () => { tried = true; return {}; } };
    assert.equal(openFileTab("/tmp/TESTHOST/x.md", SID), false); assert.equal(tried, false, "the webview has no tabs and no kernel origin: never tried");
  } finally { g.location = saved.loc; g.window = saved.win; }
});

// ── the viewer's wiring, at source ────────────────────────────────────────────────────────────────
test("source: codeBlock and mdBlock run the one pass on the DOM they built; the markdown anchors are sorted before the fenced-block highlight and the text after it; marked's parse carries the link-target hook per call; the fallback is left bare", () => {
  assert.match(VIEW, /import \{ linkifyFileText, linkMarkdownAnchors, viewerWalkTokens, URL_LINK_CLASS, FRAG_LINK_CLASS \} from "\.\/file-view-links";/);
  const codeFn = VIEW.split("function codeBlock(text: string, path: string, wrapLines: boolean): HTMLElement {")[1].split("\n}\n")[0];
  assert.match(codeFn, /code\.innerHTML = wrapNumberedHtml\(hl !== null \? hl : escapeHtml\(text\)\);\n\s*linkifyFileText\(code, path\);/, "the wrap branch: after the rows are in the DOM");
  assert.match(codeFn, /if \(hl !== null\) code\.innerHTML = hl; else code\.textContent = text;\n\s*linkifyFileText\(code, path\);/, "the gutter branch too");
  assert.doesNotMatch(codeFn, /linkifyFileText\(text|escapeHtml\(linkify/, "never over the HTML string");
  const mdFn = VIEW.split("function mdBlock(text: string, path: string, sid: string | null | undefined): HTMLElement {")[1].split("\n}\n")[0];
  assert.match(mdFn, /const base = marked\.defaults\.walkTokens;\n\s*const dirty = marked\.parse\(text, \{ walkTokens: \(t\) => \{ viewerWalkTokens\(t\); if \(base\) void base\.call\(marked, t\); \} \}\) as string;/,
    "the hook rides on this parse alone: the singleton is the chat's too");
  const anchorsAt = mdFn.indexOf("if (rendered) linkMarkdownAnchors(box, path);");
  const hlAt = mdFn.indexOf('box.querySelectorAll("pre code").forEach');
  const textAt = mdFn.indexOf("if (rendered) linkifyFileText(box, path);");
  assert.ok(anchorsAt > 0 && hlAt > anchorsAt && textAt > hlAt && mdFn.indexOf("return box;") > textAt, "anchors → highlight → text, then return");
  assert.match(mdFn, /box\.textContent = text;[^\n]*\n\s*rendered = false;/, "the fallback's bare text takes no links");
  assert.doesNotMatch(mdFn, /querySelectorAll\("a\[href\]"\)/, "the anchors' sorting moved to the module");
});

test("source: the body's delegate and its gesture: a plain click on a panel mark is the card's alone (an anchor's own open cancelled), a drag-select opens nothing, a path click stops before the row and the chat's body delegate (its openpath would open the file again) and opens through the host's opener, a modified click or a middle-click opens the link's own tab, a section link never moves the document", () => {
  const d = VIEW.split('body.addEventListener("click", (ev) => {')[1].split("\n  });\n")[0];
  assert.match(d, /const x = linkOf\(t\);\n\s*if \(!x\) return;/);
  assert.match(d, /if \(panelMark\(t\) && !wantsOwnTab\(ev\)\) \{[^\n]*\n\s*if \(x\.dataset\.act !== "openpath"\) ev\.preventDefault\(\);\n\s*return;/, "the card's click, and the anchor under the mark does not open too");
  assert.match(d, /const sel = window\.getSelection\(\);\n\s*if \(sel && !sel\.isCollapsed && box\.contains\(sel\.anchorNode\)\) \{ ev\.preventDefault\(\); return; \}/, "a drag-select that ended on the link opens nothing");
  assert.ok(d.indexOf("panelMark(t)") < d.indexOf("getSelection()") && d.indexOf("getSelection()") < d.indexOf("openLink(x, ev)"), "the mark first, then the selection, then the link");
  assert.match(VIEW, /const linkOf = \(t: Element \| null\): HTMLElement \| null => \{\n\s*const x = t && typeof t\.closest === "function" \? t\.closest\('\[data-act="openpath"\], a\.' \+ URL_LINK_CLASS \+ ", a\." \+ FRAG_LINK_CLASS\) as HTMLElement \| null : null;\n\s*return x && body\.contains\(x\) \? x : null;/);
  const o = VIEW.split("const openLink = (x: HTMLElement, ev: MouseEvent) => {")[1].split("\n  };\n")[0];
  assert.match(o, /const own = wantsOwnTab\(ev\);/);
  assert.match(o, /if \(x\.classList\.contains\(FRAG_LINK_CLASS\)\) \{[^\n]*\n\s*ev\.preventDefault\(\);\n\s*const id = x\.dataset\.frag;\n\s*const hit = id \? Array\.from\(box\.querySelectorAll\("\[id\]"\)\)\.find\(\(e\) => e\.getAttribute\("id"\) === id\) : undefined;\n\s*if \(hit\) hit\.scrollIntoView\(\{ block: "start" \}\);\n\s*return;/, "a section link: this document's scroll or nothing, never the page's location");
  assert.match(o, /if \(x\.dataset\.act !== "openpath"\) \{[^\n]*\n\s*if \(!own\) return;[^\n]*\n\s*ev\.preventDefault\(\); ev\.stopPropagation\(\);[^\n]*\n\s*openUrlTab\(x\.getAttribute\("href"\) \|\| ""\);\n\s*return;/, "a URL anchor: plain is the browser's, modified is one tab from here");
  assert.match(o, /ev\.preventDefault\(\); ev\.stopPropagation\(\);[^\n]*\n\s*const p = x\.dataset\.path;\n\s*if \(!p\) return;\n\s*if \(own && openFileTab\(p, sid \|\| null\)\) return;[^\n]*\n\s*const ln = Number\(x\.dataset\.line\);\n\s*openLinkedFile\(p, sid \|\| null, ln > 0 \? ln : null\);/, "a path link: the click stops here on every gesture (render.ts's body delegate has an openpath of its own), then its own tab on the gesture, the viewer otherwise or when the popup was blocked");
  assert.match(RENDER, /\n    openpath: \(elx\) => openLinkedPath\(elx\),\n/, "the reason the viewer stops the click: the chat's body delegate routes the same data-act");
  assert.match(VIEW, /const openUrlTab = \(href: string\) => \{\n\s*if \(!href\) return;\n\s*if \(canPreview\(\)\) window\.open\(href, "_blank", "noopener,noreferrer"\);[^\n]*\n\s*else post\(\{ type: "openLink", href \}\);/, "render.ts's two openers, by host");
  assert.match(VIEW, /body\.addEventListener\("mousedown", \(ev\) => \{\n\s*const x = ev\.button === 1 \? linkOf\(ev\.target as Element \| null\) : null;\n\s*if \(x && x\.dataset\.act === "openpath"\) ev\.preventDefault\(\);\n\s*\}\);/, "the middle press on a path link starts no autoscroll");
  assert.match(VIEW, /body\.addEventListener\("auxclick", \(ev\) => \{\n\s*if \(ev\.button !== 1\) return;\n\s*const x = linkOf\(ev\.target as Element \| null\);\n\s*if \(x && x\.dataset\.act === "openpath"\) openLink\(x, ev\);\n\s*\}\);/, "the middle-click on a path link is its own tab; an anchor's is the browser's");
  assert.match(VIEW, /import \{ fileUrl, wantsOwnTab, openFileTab, canPreview \} from "\.\/preview";/);
  assert.match(VIEW, /import \{ fileCommentsAction, panelMark \} from "\.\/file-comments";/);
  // the opener: the host's when registered (the Files pane), else the viewer in place
  assert.match(VIEW, /let openLinkedFile: \(path: string, sid: string \| null, line: number \| null\) => void =\n\s*\(path, sid, line\) => \{ openFileView\(path, sid, \{ line \}\); \};/);
  assert.match(VIEW, /host\?: \{ openFile\?: \(path: string, sid: string \| null, line: number \| null\) => void \}\): void \{\n\s*post = poster;\n\s*if \(host && host\.openFile\) openLinkedFile = host\.openFile;/);
  assert.match(FILES, /openFile: \(p, sid, line\) => openHere\(p, sid, null, null, line\),/, "the Files pane: a linked file enters its Recent list");
  assert.match(FILES, /function openHere\(path: string, sid: string \| null, identity: FileViewIdentity \| null, todoId: string \| null = null, line: number \| null = null\): void \{\n\s*if \(sid && identity\) identities\.set\(sid, identity\);\n\s*if \(!openFileView\(path, sid, \{ todoId, line \}\)\) return;/);
  // the panel's change mark cancels the anchor's activation as its comment mark does; the keyboard route lands on the same handlers
  assert.match(FC, /fcchange: \(x, ev\) => \{ ev\.preventDefault\(\); this\.openPanel\(\); this\.showCard\("chg:" \+ x\.dataset\.id!\); \},/);
  assert.match(FC, /fcopen: \(x, ev\) => \{ ev\.preventDefault\(\);/);
  // a held Cmd/Ctrl rides from the keyboard into the click (path-links.ts)
  assert.match(LINKS, /if \(e\.metaKey \|\| e\.ctrlKey\) a\.dispatchEvent\(new MouseEvent\("click", \{ bubbles: true, cancelable: true, metaKey: e\.metaKey, ctrlKey: e\.ctrlKey \}\)\);\n\s*else a\.click\(\);/);
  // the gesture is the project's one rule, in preview.ts
  const PREVIEW = read("preview.ts");
  assert.match(PREVIEW, /export function wantsOwnTab\(ev\?: \{ metaKey\?: boolean; ctrlKey\?: boolean; button\?: number \} \| null\): boolean \{\n\s*return !!ev && \(!!ev\.metaKey \|\| !!ev\.ctrlKey \|\| ev\.button === 1\);\n\}/);
  assert.match(PREVIEW, /export function openFileTab\(path: string, sid\?: string \| null\): boolean \{\n\s*if \(!canPreview\(\)\) return false;\n\s*const w = window\.open\(fileUrl\(path, sid\), "_blank"\);\n\s*if \(!w\) return false;/);
});

test("source: a close or a replace-open asks about an unsaved comment the way it asks about unsaved edits: one guard (the editor's ask, then every ask registered through the seam), reset on both exits; the panel registers its draft ask", () => {
  assert.match(VIEW, /closeGuard = \(\) => confirmDiscard\(\) && closeAsks\.every\(\(ask\) => ask\(\)\);/);
  assert.match(VIEW, /guardClose\(ask: \(\) => boolean\): void;/, "the seam member");
  assert.match(VIEW, /guardClose: \(ask\) => \{ closeAsks\.push\(ask\); \},/);
  assert.match(VIEW, /if \(closeGuard && !closeGuard\(\)\) return;[^\n]*\n\s*closeGuard = null;\n\s*closeAsks = \[\];/, "closeFileView");
  assert.match(VIEW, /if \(document\.getElementById\("romp-fileview"\) && closeGuard && !closeGuard\(\)\) return false;\n\s*closeGuard = null;\n\s*closeAsks = \[\];/, "the replace path");
  assert.match(FC, /ctx\.guardClose\(\(\) => this\.draftAsk\(\)\);/);
  assert.match(FC, /draftAsk\(\): boolean \{\n\s*const c = this\.composer;\n\s*if \(!c \|\| c\.kind === "replace" \|\| !this\.input\.value\.trim\(\)\) return true;\n\s*const p = this\.ctx\.path;\n\s*return window\.confirm\("Discard the unsaved comment on " \+ p\.slice\(p\.lastIndexOf\("\/"\) \+ 1\) \+ "\?"\);/);
  assert.match(VIEW, /window\.confirm\("Discard unsaved changes to " \+ path\.slice\(cut \+ 1\) \+ "\?"\)/, "the editor's ask, whose words the panel's follow");
});

test("source: a link's line scrolls the code view's row once the text lands, spent once; a line past the end says so in the notice bar and lands on the last row; a markdown file takes its Raw view for that open without saving the preference", () => {
  assert.match(VIEW, /export function openFileView\(path: string, sid\?: string \| null, opts\?: \{ todoId\?: string \| null; line\?: number \| null \}\): boolean \{/);
  assert.match(VIEW, /const scrollToLine = \(n: number\) => \{\n\s*const rows = body\.querySelectorAll\("code\.hljs \.fv-cl"\);\n\s*if \(!rows\.length\) return;\n\s*if \(n > rows\.length\) noteBar\("Line " \+ n \+ " is past the end of this file, which has " \+ rows\.length \+ \(rows\.length === 1 \? " line" : " lines"\) \+ "; showing the last line\."\);\n\s*\(rows\[Math\.min\(Math\.max\(0, n - 1\), rows\.length - 1\)\] as HTMLElement\)\.scrollIntoView\(\{ block: "center" \}\);/);
  assert.match(VIEW, /let pendingLine: number \| null = opts && typeof opts\.line === "number" && opts\.line > 0 \? Math\.floor\(opts\.line\) : null;/);
  assert.match(VIEW, /text = t;\n\s*\/\/[^\n]*\n\s*if \(pendingLine !== null && isMd && fmt\.md === "rendered"\) fmt\.md = "raw";\n\s*renderBody\(\);\n\s*if \(pendingLine !== null\) \{ scrollToLine\(pendingLine\); pendingLine = null; \}/);
  const landing = VIEW.split("text = t;\n")[1].split("}).catch(")[0];
  assert.doesNotMatch(landing, /saveFmt/, "the Raw view for this open only: the preference is not written");
});

test("source: the shared walk's options, the line units and the anchor marker live in path-links.ts, defaults unchanged for the chat; the module writes attributes, never markup", () => {
  assert.match(LINKS, /export interface PathLinkOptions \{\n\s*inPre\?: boolean;\n\s*accept\?: \(tok: string, ctx: \{ text: string; at: number \}\) => boolean;\n\s*resolve\?: \(tok: string\) => string;\n\s*lineSuffix\?: boolean;\n\s*unit\?: string;\n\}/);
  assert.match(LINKS, /export function linkifyPathTokens\(root: HTMLElement, sid\?: string \| null, pathLinks\?: Record<string, string>, opts\?: PathLinkOptions\): PathLinkHit\[\] \{/);
  assert.match(LINKS, /const skip = opts && opts\.inPre \? "a, \.file-uri-link" : "a, \.file-uri-link, pre";/, "the chat still skips fenced blocks");
  assert.match(LINKS, /for \(const u of textUnits\(root, opts && opts\.unit, skip\)\) \{/, "no unit: every node its own unit, the chat's walk as it was");
  assert.match(LINKS, /const span = spanHolding\(u, start, start \+ tok\.length\);\n\s*if \(!span\) continue;/, "a token across a node's edge is left as it is");
  assert.match(LINKS, /if \(!isUri && opts && opts\.accept && !opts\.accept\(tok, \{ text, at: start \}\)\) continue;/);
  assert.match(LINKS, /if \(isUri && opts && opts\.lineSuffix\) \{ const tail = URI_LINE_TAIL_RE\.exec\(tok\); if \(tail\) tok = tok\.slice\(0, tail\.index\); \}/);
  assert.match(LINKS, /export const LINE_SUFFIX_RE = \/\^\(\?::\(\\d\+\)\(\?::\\d\+\)\?\|#L\(\\d\+\)\(\?:-L\?\\d\+\)\?\)\(\?!\[\\w\/\]\)\/;/);
  assert.match(LINKS, /export function markPathLink\(a: HTMLElement, open: string, relative = false, sid\?: string \| null\): HTMLElement \{\n\s*const cls = a\.getAttribute\("class"\) \|\| "";\n\s*if \(!\(" " \+ cls \+ " "\)\.includes\(" file-uri-link "\)\) a\.setAttribute\("class", \(cls \? cls \+ " " : ""\) \+ "file-uri-link"\);\n\s*a\.setAttribute\("title", "Open " \+ open\);/, "attributes, so an SVG <a> is marked too");
  assert.match(LINKS, /const a = el\("span", "file-uri-link"\);\n\s*a\.textContent = raw;[^\n]*\n\s*return markPathLink\(a, open, relative, sid\);/, "openPathLink mints and marks");
  assert.match(MOD, /linkifyPathTokens\(root, null, undefined, \{\n\s*inPre: true,\n\s*accept: viewerPathGate,\n\s*resolve: \(tok\) => resolveViewerPath\(tok, filePath\),\n\s*lineSuffix: true,\n\s*unit: LINE_UNITS,\n\s*\}\);/, "the viewer runs the chat's walk under its own gate, a line at a time");
  assert.match(MOD, /for \(const u of textUnits\(root, LINE_UNITS, "a, \.file-uri-link"\)\) \{/, "the URL pass reads the same lines");
  assert.match(MOD, /a\.setAttribute\("target", "_blank"\);\n\s*a\.setAttribute\("rel", "noopener"\);/);
  assert.doesNotMatch(MOD, /innerHTML|outerHTML|insertAdjacentHTML/, "the module builds elements; it never writes markup");
});

test("the dress is light, and in both sheets: the token keeps its colour under a faint dotted underline, solid on hover; a Markdown file link keeps the link ink; a dead link says so", () => {
  for (const [name, css] of [["styles.css", CHAT_CSS], ["feed.css", FEED_CSS]] as const) {
    const rule = (head: string) => { const at = css.indexOf(head); assert.ok(at >= 0, name + ": " + head); return css.slice(at, css.indexOf("}", at) + 1); };
    const base = rule(".fileview-body .file-uri-link, .fileview-body .fv-url {");
    assert.match(base, /color: inherit;/, name + ": the highlight's colour stays");
    assert.match(base, /text-decoration: underline dotted;/); assert.match(base, /text-decoration-color: color-mix\(in srgb, currentColor 35%, transparent\);/);
    assert.match(base, /cursor: pointer;/);
    const hover = rule(".fileview-body .file-uri-link:hover, .fileview-body .fv-url:hover {");
    assert.match(hover, /text-decoration: underline;/); assert.match(hover, /text-decoration-color: currentColor;/);
    assert.match(rule(".fileview-md a.file-uri-link {"), /color: var\(--link\); text-decoration: none;/);
    assert.match(rule(".fileview-md a.file-uri-link:hover {"), /text-decoration: underline;/);
    assert.match(rule(".fileview-md a.fv-dead {"), /cursor: help;/);
  }
});
