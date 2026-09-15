// The chat's path matcher, executed (path-links.ts). It lived inline in render.ts, whose only tests are source
// pins; lifted into a module of its own it runs for real over a small DOM stand-in (no jsdom): the walk over a
// message body, the shape gates, the trailing-punctuation trim, the kernel's pathLinks verdict narrowing the
// links, and the span each hit is marked as. What a click does is the hosting document's (render.ts binds
// openPath per span; chat-path-links.test.ts and chat-relpath-link.test.ts pin that wiring at source).
//
// Three promises beyond the matches, since the file viewer runs the same walk (file-view-links.ts):
// 1. A link is a CONTROL from the keyboard too: the span is a tab stop announced as a link, Enter or Space clicks
//    it, and a mouse press does not focus it (so a click leaves focus where a click on plain text leaves it).
// 2. The walk costs time LINEAR in the text. CLICKABLE_PATH_RE run with the g flag restarts at every position
//    and rescans an unbroken word run to its end each time: one slash plus a 40K-character run cost seconds per
//    text node, and a viewer shows whole files. PathTokenScanner drives the same regex in linear time; the
//    trailing-punctuation trim, quadratic for the same reason on a long token of dots, scans backwards. The
//    regex's TEXT is the kernel's parity contract (tests/fixtures/path_token_parity.json), so what is pinned
//    here is that the scanner finds exactly what the regex finds, from every start position, over fuzzed and
//    adversarial texts.
// 3. The text is read a UNIT at a time when a surface asks (PathLinkOptions.unit): a highlight's spans cut a
//    line into several nodes, and a token is what the line says; a token a span cuts through is left as text.
// Synthetic fixtures only: the notes-api demo world, a placeholder session id.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { inspect } from "node:util";
import { hideEdges, staysEnumerable } from "../test-dom-shim";

const UI = path.resolve(process.cwd(), "..", "ui", "webview");
const LINKS = fs.readFileSync(path.join(UI, "path-links.ts"), "utf8");

// synthetic world: the notes-api demo, a placeholder sid (this fork's links carry the session, data-sid)
const SID = "11111111-2222-3333-4444-555555555555";

// ── a DOM stand-in: text nodes, elements with attributes, a small selector engine, fragments; every node hides its edges at
// creation (ui/test-dom-shim.ts hideEdges), so a failing assertion dumps a node's primitives and never its tree ──
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
const kebab = (k: string) => k.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
class El {
  nodeType = 1;
  tagName: string;
  parentNode: El | null = null;
  childNodes: Array<El | Txt> = [];
  attrs = new Map<string, string>();
  role: string | null = null;
  onkeydown: ((e: unknown) => void) | null = null; onmousedown: ((e: unknown) => void) | null = null; onmouseup: ((e: unknown) => void) | null = null;
  onmouseleave: ((e: unknown) => void) | null = null; oncontextmenu: ((e: unknown) => void) | null = null; ondragstart: ((e: unknown) => void) | null = null;
  clicks = 0;
  dispatched: unknown[] = [];
  constructor(tag: string) { this.tagName = tag.toUpperCase(); hideEdges(this); }
  click(): void { this.clicks++; }
  dispatchEvent(e: unknown): boolean { this.dispatched.push(e); return true; }
  blur(): void { if (doc.activeElement === this) doc.activeElement = null; }
  get tabIndex(): number { return this.attrs.has("tabindex") ? Number(this.attrs.get("tabindex")) : -1; } set tabIndex(v: number) { this.attrs.set("tabindex", String(v)); }
  get parentElement(): El | null { return this.parentNode; }
  get className(): string { return this.attrs.get("class") || ""; } set className(v: string) { this.attrs.set("class", v); }
  get title(): string { return this.attrs.get("title") || ""; } set title(v: string) { this.attrs.set("title", v); }
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
}
/** Document-order nodes under `root`, as a browser's tree walker answers them (SHOW_TEXT = 4, SHOW_ELEMENT = 1). */
function walkNodes(root: El, what: number): Array<El | Txt> {
  const out: Array<El | Txt> = [];
  const walk = (n: El) => { for (const c of n.childNodes) { if (c instanceof Txt) { if (what & 4) out.push(c); } else { if (what & 1) out.push(c); walk(c); } } };
  walk(root);
  return out;
}
function textNodesOf(root: El): Txt[] { return walkNodes(root, 4) as Txt[]; }
const doc = {
  createElement: (tag: string) => new El(tag),
  createTextNode: (s: string) => new Txt(s),
  createDocumentFragment: () => new Frag(),
  createTreeWalker: (root: El, what = 4) => { const nodes = walkNodes(root, what); let i = 0; return { nextNode: () => (i < nodes.length ? nodes[i++] : null) }; },
  activeElement: null as El | null,
};
(globalThis as any).NodeFilter = { SHOW_ELEMENT: 1, SHOW_TEXT: 4 };
(globalThis as any).document = doc;
(globalThis as any).MouseEvent = class { constructor(public type: string, public init: Record<string, unknown>) {} };
// a keydown as the browser would deliver it to the span's own handler
function press(a: El, key: string, mods: { metaKey?: boolean; ctrlKey?: boolean } = {}): boolean {
  let prevented = false;
  a.onkeydown!({ key, currentTarget: a, preventDefault: () => { prevented = true; }, ...mods });
  return prevented;
}

const el = (tag: string, cls?: string, ...kids: Array<El | Txt | string>): El => {
  const e = new El(tag); if (cls) e.className = cls;
  for (const k of kids) e.appendChild(typeof k === "string" ? new Txt(k) : k);
  return e;
};
const links = (root: El) => root.querySelectorAll(".file-uri-link");
const shape = (a: El) => [a.textContent, a.dataset.path, a.dataset.rel, a.title];

// ── the span ──────────────────────────────────────────────────────────────────────────────────────
test("openPathLink marks a span: the raw text as written, the target in data-path and the title, data-rel for a bare path; a file:// URI's link opens its decoded path and carries no data-rel", async () => {
  const { openPathLink, fileUriLink } = await import("./path-links");
  const a = openPathLink("design/foo.md", "design/foo.md", true) as unknown as El;
  assert.equal(a.tagName, "SPAN"); assert.equal(a.className, "file-uri-link");
  assert.deepEqual(shape(a), ["design/foo.md", "design/foo.md", "1", "Open design/foo.md"]);
  const fixed = openPathLink("render.js", "ui/webview/render.js", true) as unknown as El;
  assert.deepEqual(shape(fixed), ["render.js", "ui/webview/render.js", "1", "Open ui/webview/render.js"], "a shortened mention shows as written and opens the kernel's fixed target");
  const abs = openPathLink("/tmp/TESTHOST/a.md", "/tmp/TESTHOST/a.md") as unknown as El;
  assert.deepEqual(shape(abs), ["/tmp/TESTHOST/a.md", "/tmp/TESTHOST/a.md", undefined, "Open /tmp/TESTHOST/a.md"]);
  const u = fileUriLink("file:///tmp/TESTHOST/a%20b.pdf") as unknown as El;
  assert.deepEqual(shape(u), ["file:///tmp/TESTHOST/a%20b.pdf", "/tmp/TESTHOST/a b.pdf", undefined, "Open /tmp/TESTHOST/a b.pdf"]);
  // the module binds no ACTION: no click handler on the span (render.ts's bindPathLink adds the click); its own handlers are about focus
  assert.equal((a as any).onclick, undefined);
  assert.equal(a.tabIndex, 0, "a tab stop, like the <a> it stands in for"); assert.equal(a.role, "link");
  for (const k of ["onkeydown", "onmousedown", "onmouseup", "onmouseleave", "oncontextmenu", "ondragstart"] as const) assert.equal(typeof a[k], "function", k);
});

test("a path link is a control from the keyboard: Enter or Space clicks it (the host's click, whoever bound it), other keys are left alone, and a held Cmd/Ctrl rides into the click as the same modifier", async () => {
  const { openPathLink, fileUriLink } = await import("./path-links");
  const a = openPathLink("docs/design.md", "docs/design.md", true) as unknown as El;
  assert.equal(press(a, "Enter"), true, "Enter is consumed…");
  assert.equal(a.clicks, 1, "…and becomes this span's click, which bubbles to whatever the host bound");
  assert.equal(press(a, " "), true, "Space too, prevented so it does not also scroll the pane");
  assert.equal(a.clicks, 2);
  for (const k of ["Tab", "Escape", "a", "ArrowDown", "Shift"]) assert.equal(press(a, k), false, k + " is left to the browser");
  assert.equal(a.clicks, 2, "no other key activates");
  assert.equal(press(a, "Enter", { metaKey: true }), true);
  assert.equal(a.clicks, 2, "element.click() carries no modifiers, so a modified key dispatches the click itself…");
  assert.deepEqual(a.dispatched.map((e) => [(e as any).type, (e as any).init]), [["click", { bubbles: true, cancelable: true, metaKey: true, ctrlKey: undefined }]], "…with the modifier on it");
  const u = fileUriLink("file:///tmp/TESTHOST/a.pdf") as unknown as El;
  assert.equal(u.tabIndex, 0); assert.equal(u.role, "link"); press(u, "Enter"); assert.equal(u.clicks, 1, "every span the module mints takes the same route");
});

test("a mouse press does not focus a path link: the press drops the tab stop (and blurs a keyboard focus), the release brings it back, so a click leaves focus where a click on plain text leaves it", async () => {
  const { openPathLink } = await import("./path-links");
  const a = openPathLink("docs/a.md", "docs/a.md", true) as unknown as El;
  a.onmousedown!({ currentTarget: a });
  assert.equal(a.hasAttribute("tabindex"), false, "not focusable for the rest of this press: the browser's default focus finds no tab stop");
  a.onmouseup!({ currentTarget: a });
  assert.equal(a.tabIndex, 0, "back in the tab order once the press has ended on it");
  for (const end of ["onmouseleave", "oncontextmenu", "ondragstart"] as const) {
    a.onmousedown!({ currentTarget: a }); assert.equal(a.hasAttribute("tabindex"), false);
    a[end]!({ currentTarget: a }); assert.equal(a.tabIndex, 0, end + " ends the press too (a drag away, a menu, a native drag)");
  }
  doc.activeElement = a;                          // focused by Tab, then pressed: the press ends the keyboard focus too
  a.onmousedown!({ currentTarget: a });
  assert.equal(doc.activeElement, null, "blurred by the press itself, since the browser fires no focus for an already-focused element");
});

test("markPathLink dresses an element the caller already has (a Markdown link's own <a>): the class is appended, the title and class are written as attributes (an SVG <a> has no such properties), the data and the handlers are the span's", async () => {
  const { markPathLink } = await import("./path-links");
  const a = new El("a"); a.className = "fancy"; a.appendChild(new Txt("the app"));
  markPathLink(a as unknown as HTMLElement, "/tmp/TESTHOST/app.py", true);
  assert.equal(a.getAttribute("class"), "fancy file-uri-link"); assert.equal(a.getAttribute("title"), "Open /tmp/TESTHOST/app.py");
  assert.equal(a.dataset.path, "/tmp/TESTHOST/app.py"); assert.equal(a.dataset.rel, "1"); assert.equal(a.tabIndex, 0); assert.equal(a.role, "link");
  markPathLink(a as unknown as HTMLElement, "/tmp/TESTHOST/app.py", true);
  assert.equal(a.getAttribute("class"), "fancy file-uri-link", "marked twice wears the class once");
  assert.equal(a.textContent, "the app", "the label is untouched");
});

test("a file:// URI is local with an empty authority or localhost only: file://host/path names another machine, is prose to the walk, and comes back from fileUriToPath as written", async () => {
  const { isFileUri, fileUriToPath, linkifyPathTokens } = await import("./path-links");
  for (const u of ["file:///tmp/TESTHOST/a.md", "file://localhost/tmp/a.md", "FILE:///tmp/a.md", "file://LOCALHOST/x"]) assert.equal(isFileUri(u), true, u);
  for (const u of ["file://evil.invalid/share/x.md", "file://TESTHOST/x.md", "file://localhost", "file:/x.md", "files:///x", "file://localhostx/y"]) assert.equal(isFileUri(u), false, u);
  assert.equal(fileUriToPath("file://localhost/tmp/a%20b.md"), "/tmp/a b.md");
  assert.equal(fileUriToPath("file://evil.invalid/share/x.md"), "file://evil.invalid/share/x.md");
  const p = el("p", "", "see file://evil.invalid/share/x.md and file:///tmp/TESTHOST/y.md");
  assert.deepEqual(linkifyPathTokens(p as unknown as HTMLElement).map((h) => h.open), ["/tmp/TESTHOST/y.md"], "the far URI is not a relative path named after its host");
});

// ── the shape gates, on the real functions ────────────────────────────────────────────────────────
test("looksLikeFilePath and looksLikeBareFileName: anchored starts and slashed paths with an extension link, prose fractions and idioms do not; a bare filename needs a known extension", async () => {
  const { looksLikeFilePath, looksLikeBareFileName, fileUriToPath } = await import("./path-links");
  for (const p of ["design/foo.md", "/abs/path", "~/x", "./rel", "../up", "a/b/c.py", "ui/webview/render.ts"]) assert.equal(looksLikeFilePath(p), true, p);
  for (const p of ["and/or", "TCP/IP", "24/7", "read/write", "http://x/y", "a:b/c.md", "noslash.md", "src/lib"]) assert.equal(looksLikeFilePath(p), false, p);
  for (const p of ["power2_watts.pdf", "report.md", "data.csv", "notes.MD"]) assert.equal(looksLikeBareFileName(p), true, p);
  for (const p of ["np.array", "s.color", "0.4.293", ".md", "a/b.md", "x:y.md", "romp.kernelPort"]) assert.equal(looksLikeBareFileName(p), false, p);
  assert.equal(fileUriToPath("file:///tmp/TESTHOST/a%20b.md"), "/tmp/TESTHOST/a b.md");
  assert.equal(fileUriToPath("file:///tmp/TESTHOST/%zz.md"), "/tmp/TESTHOST/%zz.md", "a malformed escape is kept as written");
});

// ── the walk over a message body ──────────────────────────────────────────────────────────────────
test("the walk over a chat body: slashed paths and file:// URIs become spans, prose stays, a sentence's closing punctuation is left as text, and the body's text reads exactly as before", async () => {
  const { linkifyPathTokens } = await import("./path-links");
  const p = el("p", "", "see design/foo.md. Then and/or 24/7, TCP/IP and (file:///tmp/TESTHOST/a%20b.pdf), then ui/webview/render.ts!");
  const before = p.textContent;
  const hits = linkifyPathTokens(p as unknown as HTMLElement);
  assert.equal(p.textContent, before, "the pass adds elements around text and changes no character");
  assert.deepEqual(links(p).map(shape), [
    ["design/foo.md", "design/foo.md", "1", "Open design/foo.md"],
    ["file:///tmp/TESTHOST/a%20b.pdf", "/tmp/TESTHOST/a b.pdf", undefined, "Open /tmp/TESTHOST/a b.pdf"],
    ["ui/webview/render.ts", "ui/webview/render.ts", "1", "Open ui/webview/render.ts"],
  ]);
  assert.deepEqual(textNodesOf(p).map((t) => t.data), ["see ", "design/foo.md", ". Then and/or 24/7, TCP/IP and (", "file:///tmp/TESTHOST/a%20b.pdf", "), then ", "ui/webview/render.ts", "!"]);
  // the hits, in document order, name the span and what it opens; nothing here was kernel-verified (no map)
  assert.deepEqual(hits.map((h) => [h.open, h.verified, (h.el as unknown as El).textContent]), [["design/foo.md", false, "design/foo.md"], ["/tmp/TESTHOST/a b.pdf", false, "file:///tmp/TESTHOST/a%20b.pdf"], ["ui/webview/render.ts", false, "ui/webview/render.ts"]]);
});

test("inline code: a bare filename with a known extension links inside <code> only; a dotted identifier, a version and an unknown extension stay; prose never links a bare name", async () => {
  const { linkifyPathTokens } = await import("./path-links");
  const p = el("p", "", "wrote ", el("code", "", "power2_watts.pdf"), " and ", el("code", "", "np.array"), " and ", el("code", "", "0.4.293"), " and ", el("code", "", "out.xyz"), "; also report.md in prose");
  const before = p.textContent;
  linkifyPathTokens(p as unknown as HTMLElement);
  assert.equal(p.textContent, before);
  assert.deepEqual(links(p).map((a) => a.textContent), ["power2_watts.pdf"]);
  assert.equal(links(p)[0].parentNode!.tagName, "CODE", "the link sits inside the code span");
  assert.deepEqual(textNodesOf(p).map((t) => t.data).slice(-1), ["; also report.md in prose"], "a bare name in prose is not a link");
});

test("skipped text: inside an existing anchor, inside a span already linked, and inside a fenced <pre> block; a unit with no slash (and, in code, no dot) is not even scanned", async () => {
  const { linkifyPathTokens, openPathLink } = await import("./path-links");
  const already = openPathLink("docs/x.md", "docs/x.md", true) as unknown as El;
  const p = el("div", "",
    el("p", "", "a ", el("a", "", "docs/linked.md"), " b ", already, " c docs/free.md"),
    el("pre", "", el("code", "", "cat docs/fenced.md")),
    el("p", "", "no path here at all"),
  );
  const before = p.textContent;
  const hits = linkifyPathTokens(p as unknown as HTMLElement);
  assert.equal(p.textContent, before);
  assert.deepEqual(hits.map((h) => h.open), ["docs/free.md"], "the anchor's, the linked span's and the fence's text are left as they are");
  assert.equal(links(p).length, 2, "the span that was already a link, and the one new link");
});

test("the kernel's pathLinks verdict: with a map, a token links ONLY when it is a key and opens the map's value (verified); with no map, shape alone decides; a file:// URI is never gated on the map", async () => {
  const { linkifyPathTokens } = await import("./path-links");
  const text = "fix render.js and kernel/sub/deep.py, not a/dup.py; see file:///tmp/TESTHOST/z.md";
  const gated = el("p", "", el("code", "", "render.js"), " " + text);
  // (this fork's walk takes the session second: linkifyPathTokens(root, sid, pathLinks, opts); the chat's callers hand null here)
  const hits = linkifyPathTokens(gated as unknown as HTMLElement, null, { "render.js": "ui/webview/render.js", "kernel/sub/deep.py": "kernel/sub/deep.py" });
  assert.deepEqual(hits.map((h) => [h.open, h.verified]), [["ui/webview/render.js", true], ["kernel/sub/deep.py", true], ["/tmp/TESTHOST/z.md", false]],
    "the backticked mention opens the fixed target (the bare name in prose fails the shape gate first: the map only ever narrows); a/dup.py, absent from the map (no such file, or several), stays prose; the URI rides regardless");
  assert.deepEqual(links(gated).map(shape)[0], ["render.js", "ui/webview/render.js", "1", "Open ui/webview/render.js"], "shown as written, opens the real file, hover names it");
  assert.equal(links(gated).length, 3);
  // no map at all (an old kernel, a cached payload): every shape-passing token links as written, none verified
  const free = el("p", "", text);
  const h2 = linkifyPathTokens(free as unknown as HTMLElement);
  assert.deepEqual(h2.map((h) => [h.open, h.verified]), [["kernel/sub/deep.py", false], ["a/dup.py", false], ["/tmp/TESTHOST/z.md", false]], "render.js has no slash and is not in code: prose either way");
  // an EMPTY map is a verdict too: nothing links but the URI
  const none = el("p", "", text);
  assert.deepEqual(linkifyPathTokens(none as unknown as HTMLElement, null, {}).map((h) => h.open), ["/tmp/TESTHOST/z.md"]);
});

test("the resume rule: after a linked token the scan resumes right after it, so a token's trimmed punctuation and the text after it are read again as prose; a token that stays prose is skipped whole", async () => {
  const { linkifyPathTokens } = await import("./path-links");
  const p = el("p", "", "a/b.md,c/d.md; and/or e/f.md");
  linkifyPathTokens(p as unknown as HTMLElement);
  assert.deepEqual(links(p).map((a) => a.textContent), ["a/b.md", "c/d.md", "e/f.md"]);
  assert.deepEqual(textNodesOf(p).map((t) => t.data), ["a/b.md", ",", "c/d.md", "; and/or ", "e/f.md"]);
});

// ── this fork's promises beyond upstream's (plans/file-review.md Slice 0; plans/markdown-viewer.md Slice 6) ──────────
// The links carry the ACT and the SESSION: data-act openpath is the route the hosts' delegates key on (waiting.ts's
// delegate, render.ts's body delegate for a todo card, per-span bindPathLink for a transcript), and data-sid names the
// session a relative path resolves against (a todo's note belongs to the session that flagged it, whichever tab reads
// it). The keyboard case below is this fork's reading of the same control, kept beside upstream's above: it reads the
// dataset the delegate reads and the key handler at source.
test("the act and the session ride on the span: data-act openpath for the hosts' delegate route, data-sid when the caller names a session and none otherwise, on openPathLink, markPathLink and every link the walk mints", async () => {
  const { openPathLink, markPathLink, fileUriLink, linkifyPathTokens, PATH_LINK_ACT } = await import("./path-links");
  assert.equal(PATH_LINK_ACT, "openpath");
  const a = openPathLink("docs/design.md", "docs/design.md", true, SID) as unknown as El;
  assert.deepEqual([a.dataset.act, a.dataset.path, a.dataset.rel, a.dataset.sid], ["openpath", "docs/design.md", "1", SID]);
  const bare = openPathLink("docs/design.md", "docs/design.md", true) as unknown as El;
  assert.equal(bare.dataset.act, "openpath"); assert.equal(bare.dataset.sid, undefined, "no session named: no data-sid");
  const u = fileUriLink("file:///tmp/TESTHOST/a.pdf") as unknown as El;
  assert.equal(u.dataset.act, "openpath"); assert.equal(u.dataset.sid, undefined, "fileUriLink names no session");
  const m = new El("a"); m.appendChild(new Txt("the app"));
  markPathLink(m as unknown as HTMLElement, "/tmp/TESTHOST/app.py", false, SID);
  assert.deepEqual([m.dataset.act, m.dataset.rel, m.dataset.sid], ["openpath", undefined, SID], "the marked anchor wears the act and the session too");
  const p = el("p", "", "see docs/a.md and file:///tmp/TESTHOST/b.md");
  linkifyPathTokens(p as unknown as HTMLElement, SID);
  assert.deepEqual(links(p).map((x) => [x.dataset.act, x.dataset.sid]), [["openpath", SID], ["openpath", SID]],
    "the walk hands its session to every link it mints, the URI's included (its path is absolute, so no relative resolve reads the sid; the host still learns which session the text belongs to)");
  assert.deepEqual(linkifyPathTokens(el("p", "", "see docs/c.md") as unknown as HTMLElement).map((h) => (h.el as unknown as El).dataset.sid), [undefined], "no session handed: none on the span");
  // at source: the stamp and the parameter
  assert.match(LINKS, /export const PATH_LINK_ACT = "openpath";/);
  assert.match(LINKS, /a\.dataset\.act = PATH_LINK_ACT;/);
  assert.match(LINKS, /if \(relative\) a\.dataset\.rel = "1";\n\s*if \(sid\) a\.dataset\.sid = sid;/);
  assert.match(LINKS, /export function openPathLink\(raw: string, open: string, relative = false, sid\?: string \| null\): HTMLElement \{/);
  assert.match(LINKS, /export function markPathLink\(a: HTMLElement, open: string, relative = false, sid\?: string \| null\): HTMLElement \{/);
});

test("a path link is a tab stop announced as a link, and Enter or Space clicks it — the host's click, from the keyboard", async () => {
  const { openPathLink, fileUriLink } = await import("./path-links");
  const a = openPathLink("docs/design.md", "docs/design.md", true, SID) as unknown as El;
  assert.equal(a.tabIndex, 0, "reachable with Tab, like the <a> it stands in for");
  assert.equal(a.role, "link");
  assert.equal(typeof a.onkeydown, "function");
  assert.equal(press(a, "Enter"), true, "Enter is consumed…");
  assert.equal(a.clicks, 1, "…and becomes this span's click, which bubbles to whatever the host bound");
  assert.equal(press(a, " "), true, "Space too — prevented, so it does not also scroll the pane");
  assert.equal(a.clicks, 2);
  for (const k of ["Tab", "Escape", "a", "ArrowDown", "Shift"]) {
    assert.equal(press(a, k), false, k + " is left to the browser");
  }
  assert.equal(a.clicks, 2, "no other key activates");
  // every span the module mints takes the same route — a file:// URI's included
  const u = fileUriLink("file:///tmp/notes-api/a.pdf") as unknown as El;
  assert.equal(u.tabIndex, 0); assert.equal(u.role, "link"); press(u, "Enter"); assert.equal(u.clicks, 1);
  // the click stays the host's: the span carries the act and the target, and no route of its own
  assert.deepEqual([a.dataset.act, a.dataset.path, a.dataset.rel, a.dataset.sid], ["openpath", "docs/design.md", "1", SID]);
  assert.match(LINKS, /a\.tabIndex = 0;/);
  assert.match(LINKS, /a\.role = "link";/);
  assert.match(LINKS, /a\.onkeydown = pathLinkKey;/);
  // a held Cmd/Ctrl rides into the click as the same modifier (the file viewer reads it as "in a tab of its own"); a plain key is element.click()
  assert.match(LINKS, /function pathLinkKey\(e: KeyboardEvent\): void \{\n\s*if \(e\.key !== "Enter" && e\.key !== " "\) return;\n\s*e\.preventDefault\(\);\n\s*const a = e\.currentTarget as HTMLElement;\n\s*if \(e\.metaKey \|\| e\.ctrlKey\) a\.dispatchEvent\(new MouseEvent\("click", \{ bubbles: true, cancelable: true, metaKey: e\.metaKey, ctrlKey: e\.ctrlKey \}\)\);\n\s*else a\.click\(\);/);
});

test("the walk's links carry the keyboard route too", async () => {
  const { linkifyPathTokens } = await import("./path-links");
  const d = el("div", "ut-detail"); d.textContent = "read docs/design.md and file:///tmp/notes-api/out.png";
  linkifyPathTokens(d as unknown as HTMLElement, SID);
  assert.equal(links(d).length, 2);
  for (const s of links(d)) { assert.equal(s.tabIndex, 0); assert.equal(s.role, "link"); press(s, "Enter"); assert.equal(s.clicks, 1); }
});

// The projection rule (ui/test-dom-shim.ts, hideEdges): a stand-in node enumerates its primitives alone, so a failing
// assertion's dump of one stops at the node instead of walking the whole tree through its edges.
test("a stand-in node enumerates its primitives alone, and a dump of it names neither parentNode, parentElement nor childNodes", () => {
  const root = new El("div"); const kid = new El("span"); root.appendChild(kid); kid.appendChild(new Txt("x"));
  const nodes: Array<El | Txt> = [root, kid, kid.childNodes[0]];
  for (const n of nodes) {
    assert.ok(Object.keys(n).every((k) => staysEnumerable((n as any)[k])), "every enumerable own key holds a primitive: " + Object.keys(n).join(","));
    const dump = inspect(n, { compact: false, customInspect: false, depth: 1000, maxArrayLength: Infinity, showHidden: false, showProxy: false, sorted: true, getters: true });
    assert.ok(!dump.includes("parentNode") && !dump.includes("parentElement") && !dump.includes("childNodes"), "the dump stops at the node:\n" + dump);
  }
});

// ── 3. a target after the path: `targetSuffix` (plans/markdown-viewer.md, Slice 6) ─────────────────
// A user todo's text or detail names a place in a file as `docs/report.md#results` or `docs/report.md:12`; under
// `targetSuffix` the walk reads the line grammar `lineSuffix` reads (data-line) and one more arm, the section
// (data-frag), the two attributes the viewer's body delegate reads off a link inside a shown file (file-view.ts;
// contract C3). The chat's default walk and the viewer's `lineSuffix` walk leave a `#section` as prose, as before.
type Marked = { text: string; path: string | undefined; line: string | undefined; frag: string | undefined; title: string };
/** The walk over a div of the given class with this fork's session handed in: the links in order, and the div's own text pieces (the prose left between them). */
async function walk(text: string, opts?: Record<string, unknown>, cls = "ut-detail"): Promise<{ links: Marked[]; texts: string[] }> {
  const { linkifyPathTokens } = await import("./path-links");
  const d = el("div", cls); d.textContent = text;
  linkifyPathTokens(d as unknown as HTMLElement, SID, undefined, opts);
  return { links: links(d).map((s) => ({ text: s.textContent, path: s.dataset.path, line: s.dataset.line, frag: s.dataset.frag, title: s.title })), texts: ownTexts(d) };
}
const ownTexts = (d: El): string[] => d.childNodes.filter((c): c is Txt => c instanceof Txt).map((c) => c.data);
test("targetSuffix: a line after the path rides in the link as lineSuffix reads it; a section rides as data-frag; the shown text grows by the suffix", async () => {
  const opts = { targetSuffix: true };
  let r = await walk("see docs/a.md:12 next", opts);
  assert.deepEqual(r.links, [{ text: "docs/a.md:12", path: "docs/a.md", line: "12", frag: undefined, title: "Open docs/a.md:12" }]);
  assert.deepEqual(r.texts, ["see ", " next"], "the suffix is the link's, not the prose's");
  r = await walk("see docs/a.md:12:4 next", opts);
  assert.deepEqual(r.links.map((l) => [l.text, l.line]), [["docs/a.md:12:4", "12"]], "a column rides in the text and is dropped from the line, as lineSuffix has it");
  r = await walk("see docs/a.md#results next", opts);
  assert.deepEqual(r.links, [{ text: "docs/a.md#results", path: "docs/a.md", line: undefined, frag: "results", title: "Open docs/a.md#results" }]);
  assert.deepEqual(r.texts, ["see ", " next"]);
  r = await walk("see docs/a.md#L7 next", opts);
  assert.deepEqual(r.links.map((l) => [l.text, l.line, l.frag]), [["docs/a.md#L7", "7", undefined]], "GitHub's line anchor is a line, never a section");
  r = await walk("see docs/a.md#L7-L9 next", opts);
  assert.deepEqual(r.links.map((l) => [l.text, l.line, l.frag]), [["docs/a.md#L7-L9", "7", undefined]], "a range: its first line");
  r = await walk("see docs/a.md#L7abc next", opts);
  assert.deepEqual(r.links.map((l) => [l.text, l.line, l.frag]), [["docs/a.md", undefined, undefined]], "`#L7abc` is neither a line (the line arm refuses it) nor a section (the L-digits start is the line arm's)");
  assert.deepEqual(r.texts, ["see ", "#L7abc next"]);
  r = await walk("see docs/a.md#l12 next", opts);
  assert.deepEqual(r.links.map((l) => [l.text, l.line, l.frag]), [["docs/a.md#l12", undefined, "l12"]], "a lowercase l is no line anchor: a heading slugged `l12`");
  r = await walk("see docs/a.md#Evidence%20Results next", opts);
  assert.deepEqual(r.links.map((l) => [l.text, l.frag, l.title]), [["docs/a.md#Evidence%20Results", "Evidence Results", "Open docs/a.md#Evidence Results"]], "percent-decoded: the viewer slugs it to the heading");
  r = await walk("see docs/a.md#results.", opts);
  assert.deepEqual(r.links.map((l) => [l.text, l.frag]), [["docs/a.md#results", "results"]], "the sentence's period is the prose's, as after a bare token");
  assert.deepEqual(r.texts, ["see ", "."]);
  r = await walk("(see docs/a.md#results), then", opts);
  assert.deepEqual(r.links.map((l) => [l.text, l.frag]), [["docs/a.md#results", "results"]]);
  assert.deepEqual(r.texts, ["(see ", "), then"]);
  r = await walk("see docs/a.md# next", opts);
  assert.deepEqual(r.links.map((l) => [l.text, l.frag]), [["docs/a.md", undefined]], "a bare `#` names no section");
  assert.deepEqual(r.texts, ["see ", "# next"]);
  r = await walk("see docs/a.md#one#two next", opts);
  assert.deepEqual(r.links.map((l) => [l.text, l.frag]), [["docs/a.md#one", "one"]], "a second `#` ends the section");
  assert.deepEqual(r.texts, ["see ", "#two next"]);
  r = await walk("see docs/a.md#results", opts);
  assert.deepEqual(r.links.map((l) => [l.text, l.frag]), [["docs/a.md#results", "results"]], "at the end of the text");
  assert.deepEqual(r.texts, ["see "]);
  r = await walk("see #results and and/or#x here", opts);
  assert.deepEqual(r.links, [], "a `#` with no path before it, or after a token that is prose, is never a section: the suffix is read only at a linked token's end");
  // a file:// URI swallows the suffix into the token (its own grammar admits `:` and `#`): the suffix is cut back out
  r = await walk("see file:///repo/notes-api/docs/a.md#results now", opts);
  assert.deepEqual(r.links.map((l) => [l.text, l.path, l.frag]), [["file:///repo/notes-api/docs/a.md#results", "/repo/notes-api/docs/a.md", "results"]]);
  r = await walk("see file:///repo/notes-api/docs/a.md:12 now", opts);
  assert.deepEqual(r.links.map((l) => [l.text, l.path, l.line, l.frag]), [["file:///repo/notes-api/docs/a.md:12", "/repo/notes-api/docs/a.md", "12", undefined]]);
  r = await walk("see file:///repo/notes-api/docs/a.md#L3 now", opts);
  assert.deepEqual(r.links.map((l) => [l.path, l.line, l.frag]), [["/repo/notes-api/docs/a.md", "3", undefined]]);
});

// A file:// URI carrying both a line and a section (`file:///repo/notes-api/docs/a.md:12#results`): the URI arm swallows
// both, and the two cuts that hand a swallowed tail back to the suffix walk each anchor at the token's END, so the
// section, which ends the token, must be cut before the line. The PR's review, round 1 (2026-09-14): the line cut ran
// first, found nothing at a token ending in a section, and the path kept `:12`, so the link opened `a.md:12` (the
// kernel's 404) with the section as data-frag, where a bare `docs/a.md:12#results` on the same line linked the file
// at line 12 and left `#results` to the prose all along. The URI is held to that bare form.
test("targetSuffix: a file URI carrying both a line and a section links the path at the line and leaves the section to the prose, as a bare token does", async () => {
  const opts = { targetSuffix: true };
  const bare = await walk("see docs/a.md:12#results now", opts);
  assert.deepEqual(bare.links.map((l) => [l.text, l.path, l.line, l.frag]), [["docs/a.md:12", "docs/a.md", "12", undefined]],
    "the bare form the URI is held to: the line arm reads `:12`, the walk reads one suffix, and `#results` stays prose");
  assert.deepEqual(bare.texts, ["see ", "#results now"]);
  let r = await walk("see file:///repo/notes-api/docs/a.md:12#results now", opts);
  assert.deepEqual(r.links, [{ text: "file:///repo/notes-api/docs/a.md:12", path: "/repo/notes-api/docs/a.md", line: "12", frag: undefined, title: "Open /repo/notes-api/docs/a.md:12" }],
    "the path is the file's with no `:12` in it, and the line rides as data-line");
  assert.deepEqual(r.texts, ["see ", "#results now"], "the section is the prose's, as after the bare token");
  r = await walk("see file:///repo/notes-api/docs/a.md:12#L3 now", opts);
  assert.deepEqual(r.links.map((l) => [l.text, l.path, l.line, l.frag]), [["file:///repo/notes-api/docs/a.md:12", "/repo/notes-api/docs/a.md", "12", undefined]],
    "a line anchor after a line: the first is the line and the anchor stays prose, as after `docs/a.md:12#L3`");
  assert.deepEqual(r.texts, ["see ", "#L3 now"]);
  r = await walk("see file:///repo/notes-api/docs/a.md:12:4#results now", opts);
  assert.deepEqual(r.links.map((l) => [l.text, l.path, l.line, l.frag]), [["file:///repo/notes-api/docs/a.md:12:4", "/repo/notes-api/docs/a.md", "12", undefined]],
    "a column rides in the text and is dropped from the line, as lineSuffix has it");
  assert.deepEqual(r.texts, ["see ", "#results now"]);
  r = await walk("see file:///repo/notes-api/docs/a.md:12#results.", opts);
  assert.deepEqual(r.links.map((l) => [l.text, l.path, l.line, l.frag]), [["file:///repo/notes-api/docs/a.md:12", "/repo/notes-api/docs/a.md", "12", undefined]]);
  assert.deepEqual(r.texts, ["see ", "#results."], "the sentence's period stays the prose's");
  // the one-tail URIs read as before: a section alone, a line alone, a line anchor alone
  r = await walk("see file:///repo/notes-api/docs/a.md#results and file:///repo/notes-api/docs/b.md:12 and file:///repo/notes-api/docs/c.md#L3 now", opts);
  assert.deepEqual(r.links.map((l) => [l.text, l.path, l.line, l.frag]), [
    ["file:///repo/notes-api/docs/a.md#results", "/repo/notes-api/docs/a.md", undefined, "results"],
    ["file:///repo/notes-api/docs/b.md:12", "/repo/notes-api/docs/b.md", "12", undefined],
    ["file:///repo/notes-api/docs/c.md#L3", "/repo/notes-api/docs/c.md", "3", undefined],
  ]);
  assert.deepEqual(r.texts, ["see ", " and ", " and ", " now"]);
  // the order at source: the section's tail is cut before the line's, both anchored at the token's end
  assert.match(LINKS, /if \(isUri && sections\) \{ const tail = URI_FRAG_TAIL_RE\.exec\(tok\); if \(tail\) tok = tok\.slice\(0, tail\.index\); \}\n\s*if \(isUri && lines\) \{ const tail = URI_LINE_TAIL_RE\.exec\(tok\); if \(tail\) tok = tok\.slice\(0, tail\.index\); \}/,
    "the section tail is cut first: a URI carrying both ends in the section, so a line cut tried first finds nothing");
});

test("controls: the chat's default walk and the viewer's lineSuffix walk leave a `#section` as prose, exactly as before", async () => {
  for (const opts of [undefined, { lineSuffix: true }]) {
    const r = await walk("see docs/a.md#results and docs/b.md:12 next", opts);
    assert.deepEqual(r.links.map((l) => [l.text, l.line, l.frag]),
      opts ? [["docs/a.md", undefined, undefined], ["docs/b.md:12", "12", undefined]] : [["docs/a.md", undefined, undefined], ["docs/b.md", undefined, undefined]],
      "opts " + JSON.stringify(opts));
    assert.deepEqual(r.texts, opts ? ["see ", "#results and ", " next"] : ["see ", "#results and ", ":12 next"]);
    const u = await walk("see file:///repo/notes-api/docs/a.md#results now", opts);
    assert.deepEqual(u.links.map((l) => [l.text, l.path, l.frag]), [["file:///repo/notes-api/docs/a.md#results", "/repo/notes-api/docs/a.md#results", undefined]],
      "the URI arm keeps its swallowed `#results` in the path, as it did: only targetSuffix cuts it");
    // a URI carrying both a line and a section: the same on these two walks, before and after the targetSuffix walk
    // learned to cut the section first (only targetSuffix cuts a section; the line cut alone finds no line at a token
    // ending in a section, the viewer's walk's recorded follow-up)
    const b = await walk("see file:///repo/notes-api/docs/a.md:12#results now", opts);
    assert.deepEqual(b.links.map((l) => [l.text, l.path, l.line, l.frag]), [["file:///repo/notes-api/docs/a.md:12#results", "/repo/notes-api/docs/a.md:12#results", undefined, undefined]],
      "opts " + JSON.stringify(opts) + ": both tails stay in the path, as they did");
    assert.deepEqual(b.texts, ["see ", " now"]);
  }
});

test("a section a highlight span cut into another node is refused as a line is: the link stops at the path", async () => {
  const { linkifyPathTokens } = await import("./path-links");
  const d = el("div", "ut-text", "see docs/a.md#res", el("span", "hl", "ults"), " next");
  linkifyPathTokens(d as unknown as HTMLElement, SID, undefined, { targetSuffix: true, unit: ".ut-text" });
  const link = links(d)[0];
  assert.ok(link, "the path itself links");
  assert.equal(link.textContent, "docs/a.md");
  assert.equal(link.dataset.frag, undefined, "the cut section stays prose in its pieces");
  assert.deepEqual(ownTexts(d), ["see ", "#res", " next"]);
  // the same text in one node, for contrast
  const w = await walk("see docs/a.md#results next", { targetSuffix: true, unit: ".ut-text" }, "ut-text");
  assert.deepEqual(w.links.map((l) => l.frag), ["results"]);
});

test("linkTarget reads a link's data-line as a line, else its data-frag as a heading, else nothing: the one reader the hosts share", async () => {
  const { linkTarget, FRAG_SUFFIX_RE, LINE_SUFFIX_RE } = await import("./path-links");
  const at = (dataset: Record<string, string>) => linkTarget({ dataset } as unknown as HTMLElement);
  assert.deepEqual(at({ line: "12" }), { line: 12 });
  assert.deepEqual(at({ frag: "results" }), { heading: "results" });
  assert.deepEqual(at({ line: "12", frag: "results" }), { line: 12 }, "a line wins where both stand (the walk writes one or the other)");
  assert.deepEqual(at({ line: "0", frag: "results" }), { heading: "results" }, "a line that is no line falls to the section");
  assert.deepEqual(at({ line: "abc" }), null);
  assert.deepEqual(at({ line: "1.5" }), null, "a positive integer, as the viewer reads it");
  assert.deepEqual(at({ frag: "" }), null);
  assert.deepEqual(at({}), null);
  // the arm's grammar, at source and by behaviour
  assert.match(LINKS, /export const FRAG_SUFFIX_RE = \/\^#\(\?!L\\d\)\(\[\^\\s#\]\+\)\/;/);
  assert.match(LINKS, /export interface PathLinkOptions \{\n\s*inPre\?: boolean;\n\s*preVerified\?: boolean;\n\s*accept\?: \(tok: string, ctx: \{ text: string; at: number; inPre: boolean \}\) => boolean;\n\s*resolve\?: \(tok: string\) => string;\n\s*lineSuffix\?: boolean;\n\s*targetSuffix\?: boolean;\n\s*unit\?: string;\n\}/);   // preVerified and the ctx's inPre: the chat's fenced blocks (2026-09-12)
  assert.equal(FRAG_SUFFIX_RE.exec("#L12"), null, "the line arm's shape is never a section");
  assert.equal(LINE_SUFFIX_RE.exec("#L12")![2], "12");
  assert.equal(FRAG_SUFFIX_RE.exec("#Lx")![1], "Lx", "an L not followed by a digit is a section (a heading named Lx)");
  assert.equal(FRAG_SUFFIX_RE.exec("#a b")![1], "a", "to the first space");
  // the line arm is tried first in the walk, so `#L12` reaches the line and never this arm
  assert.match(LINKS, /if \(lines\) \{ LINE_SUFFIX_AT_RE\.lastIndex = start \+ tok\.length; suffix = LINE_SUFFIX_AT_RE\.exec\(text\); \}/);
  assert.match(LINKS, /else if \(sections\) \{\n\s*FRAG_SUFFIX_AT_RE\.lastIndex = start \+ tok\.length;/);
  assert.match(LINKS, /const lines = !!\(opts && \(opts\.lineSuffix \|\| opts\.targetSuffix\)\);/, "targetSuffix reads the line grammar too");
  assert.match(LINKS, /const sections = !!\(opts && opts\.targetSuffix\);/);
  assert.doesNotMatch(LINKS, /text\.slice\(start \+ tok\.length/, "the section is read in place (sticky), never off a slice of the rest of the unit");
});

// ── the module's contract with render.ts, at source ───────────────────────────────────────────────
test("source: the module marks and binds nothing; render.ts binds the click and the middle button per span off the span's data, and reads the hits for its figure pass", () => {
  const RENDER = fs.readFileSync(path.join(UI, "render.ts"), "utf8");
  assert.doesNotMatch(LINKS, /addEventListener|onclick|openPath\(|window\.open|postMessage|fetch\(/, "no action of its own: its handlers are about focus (keydown, the press)");
  assert.match(LINKS, /export function linkifyPathTokens\(root: HTMLElement, sid\?: string \| null, pathLinks\?: Record<string, string>, opts\?: PathLinkOptions\): PathLinkHit\[\] \{/);   // the session the links carry (data-sid) is the caller's second argument
  assert.match(LINKS, /export interface PathLinkHit \{ el: HTMLElement; open: string; verified: boolean; inPre: boolean \}/, "+ inPre: the chat skips its figure pass for a fenced hit (2026-09-12)");
  assert.match(RENDER, /import \{ openPathLink, linkifyPathTokens, selectionOpenIn \} from "\.\/path-links";/);
  assert.match(RENDER, /import \{ linkTarget, type PathLinkOptions \} from "\.\/path-links";/, "the second import: the target reader the hosts share and the walk's options type (the chat's FENCE_WALK and the todo surfaces' walkOpts)");
  // the binder reads the span's data through one opener (openLinkedPath): the path, the rel bit, the session the span names (else the active tab) and the target the link named after its path (linkTarget)
  assert.match(RENDER, /function openLinkedPath\(a: HTMLElement, e\?: MouseEvent \| null\): void \{\n\s*const open = a\.dataset\.path \|\| "", relative = a\.dataset\.rel === "1", sid = a\.dataset\.sid \?\? null;\n\s*openPath\(open, relative \? \(sid \?\? activeId\) : null, e, linkTarget\(a\)\);/);
  // ...and binds the click and the middle button to it; around the click, T351's hover preview: the pending preview is cancelled at the click, and the span is armed for a hover or a focus (armFilePreview)
  assert.match(RENDER, /function bindPathLink\(a: HTMLElement\): HTMLElement \{\n\s*a\.addEventListener\("click", \(e\) => \{ e\.stopPropagation\(\); filePreviewIntent\.cancel\(\); openLinkedPath\(a, e\); \}\);\n\s*onMiddleClick\(a, \(e\) => openLinkedPath\(a, e\)\);[^\n]*\n\s*armFilePreview\(a\);[^\n]*\n\s*return a;\n\}/);
  assert.match(RENDER, /const link = bind\(openPathLink\(tok, tok, true, sid\)\);\n\s*armPreview\(link, tok, tok\);\n\s*code\.replaceChildren\(link\);/, "the kernel-verified spaced span takes the same binder (bind: bindPathLink, or the identity under the delegated mode a todo card asks for) and the kernel's preview verdict (T351)");
  assert.match(RENDER, /for \(const \{ el: link, open, verified, inPre \} of linkifyPathTokens\(root, sid, pathLinks, walkOpts \? \{ \.\.\.FENCE_WALK, \.\.\.walkOpts \} : FENCE_WALK\)\) \{\n\s*bind\(link\);\n\s*armPreview\(link, link\.textContent \|\| "", open\);\n\s*absorbFragment\(link\);\n\s*if \(verified\) kernelVerified\.add\(open\);/,
    "the chat's walk carries its fenced-block options (2026-09-12) under a todo surface's own; every hit is bound (unless delegated) and previewable, a `#slug` written after the path is absorbed into the link (T351), a fenced one renders no figure");
  // the matcher lives in ONE place: render.ts no longer declares the regex or its gates
  for (const name of ["CLICKABLE_PATH_RE", "function looksLikeFilePath", "function looksLikeBareFileName", "const BARE_FILE_EXTS", "function fileUriToPath", "function openPathLink", "function fileUriLink"]) {
    assert.ok(!RENDER.includes(name), name + " is path-links.ts's alone");
    assert.ok(LINKS.includes(name), name + " in path-links.ts");
  }
});

// ── the linear driver for the regex ───────────────────────────────────────────────────────────────
/** What CLICKABLE_PATH_RE.exec finds from `from` with the g flag: the reference the scanner must match exactly. */
function regexNext(re: RegExp, text: string, from: number): [number, number] | null {
  re.lastIndex = from;
  const m = re.exec(text);
  return m ? [m.index, m.index + m[0].length] : null;
}
async function scannerAgrees(text: string): Promise<void> {
  const { PathTokenScanner, CLICKABLE_PATH_RE } = await import("./path-links");
  const re = new RegExp(CLICKABLE_PATH_RE.source, "gi");
  const scan = new PathTokenScanner(text);
  for (let from = 0; from <= text.length; from++) {
    assert.deepEqual(scan.next(from), regexNext(re, text, from), JSON.stringify(text.slice(0, 80)) + " from " + from);
  }
  // …and the walk's own use: successive calls that never move `from` backwards, resuming after each match
  const s2 = new PathTokenScanner(text);
  let from = 0, m: [number, number] | null;
  while ((m = s2.next(from))) { assert.deepEqual(m, regexNext(re, text, from)); from = m[1]; }
  assert.equal(regexNext(re, text, from), null);
}

test("the scanner's arms are cut from CLICKABLE_PATH_RE itself: three, sticky, the regex's own text", async () => {
  const { CLICKABLE_PATH_RE } = await import("./path-links");
  const arms = CLICKABLE_PATH_RE.source.split("|");
  assert.equal(arms.length, 3);
  assert.match(arms[0], /^file:/); assert.match(arms[1], /^\[~\.\\w\\-\]\*\\\//); assert.match(arms[2], /^\[\\w\\-\]/);
  assert.match(LINKS, /const \[URI_ARM, PATH_ARM, BARE_ARM\] = CLICKABLE_PATH_RE\.source\.split\("\|"\)\.map\(\(arm\) => new RegExp\(arm, "iy"\)\);/);
  assert.equal(CLICKABLE_PATH_RE.source, "file:\\/\\/\\/?[^\\s<>\"'`)]+|[~.\\w\\-]*\\/[~.\\w\\-/]*[\\w\\-]|[\\w\\-][\\w\\-.]*\\.[A-Za-z0-9]{1,8}", "the parity contract's text, unchanged by the lift");
});

test("the scanner finds exactly what the regex finds, from every start position: adversarial shapes", async () => {
  for (const text of [
    "", "/", "a/b.md", "see a/b.md and c/d.py.", "file:///tmp/x.md and file://h/y", "FILE:///X", "f", "ff", "fil", "file:",
    "~/x", "./a", "../b/c", "a//b", "//", "a.b.c", ".md", "a.", "-a/b-", "_x/_y.z", "x/y/z/", "a b/c d.md e",
    "1/2.5", "24/7", "and/or", "np.array", "0.4.293", "a.verylongextensionx", "a.b.c.d.e.f.g.h.i", "x/.hidden", "..", ".",
    "α/β.md", "a/ß.py", "日本語/x.md", "a\tb/c.md", "a\nb/c.md", "(a/b.md)", "\"a/b.md\"", "`a/b.md`", "<a/b.md>", "[a/b.md]",
    "x".repeat(50) + "/" + "y".repeat(50) + ".md", "-".repeat(30), ".".repeat(30), "/".repeat(30), "~".repeat(10) + "/x",
    "f".repeat(20) + "ile:///a", "file:" + "/".repeat(10) + "a", "a/b.md:12", "a/b.md#L3", "http://x.y/z.html", "git@h:u/r.git",
    // non-ASCII letters that uppercase to ASCII (U+017F to S, the Kelvin sign U+212A to K) stay outside \\w under the i flag; a no-break space is \\s
    "\u017f.md K.md \u00e9/x.md", "\u212a.md", "a\u00a0b/c.md", "file:///a\u00a0b",
  ]) await scannerAgrees(text);
});

test("the scanner finds exactly what the regex finds, from every start position: fuzzed texts", async () => {
  const alphabet = "abfz09_-./~ :\n\"'`()<>ile";
  let seed = 12345;
  const rnd = () => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; };
  for (let i = 0; i < 300; i++) {
    const n = 1 + Math.floor(rnd() * 40);
    let t = "";
    for (let j = 0; j < n; j++) t += alphabet[Math.floor(rnd() * alphabet.length)];
    await scannerAgrees(t);
  }
});

test("tokenizer parity: the scanner over the shared kernel fixture, on the walk's own loop (the trim, the resume after the trimmed token)", async () => {
  const { PathTokenScanner, TRAILING_PUNCT_RE } = await import("./path-links");
  const fixture = JSON.parse(fs.readFileSync(path.resolve(process.cwd(), "..", "tests", "fixtures", "path_token_parity.json"), "utf8"));
  for (const c of fixture.cases as { text: string; tokens: string[] }[]) {
    const toks: string[] = [];
    const scan = new PathTokenScanner(c.text);
    let from = 0, m: [number, number] | null;
    while ((m = scan.next(from))) {
      const tok = c.text.slice(m[0], m[1]).replace(TRAILING_PUNCT_RE, "");
      from = Math.max(m[0] + tok.length, from + 1);
      if (tok && !toks.includes(tok)) toks.push(tok);
    }
    assert.deepEqual(toks, c.tokens, c.text);
  }
});

test("the trailing-punctuation set has one source: the regex is built from the characters the trim scans, and the walk trims as before", async () => {
  const { TRAILING_PUNCT, TRAILING_PUNCT_RE, linkifyPathTokens } = await import("./path-links");
  assert.equal(TRAILING_PUNCT, ".,;:!?)]}>\"'`");
  for (const ch of TRAILING_PUNCT) assert.match("a" + ch, TRAILING_PUNCT_RE, ch);
  for (const ch of "a/_-~") assert.doesNotMatch("a" + ch, TRAILING_PUNCT_RE, ch);
  assert.match(LINKS, /export const TRAILING_PUNCT_RE = new RegExp\("\[" \+ TRAILING_PUNCT\.replace\(\/\[\\\\\\\]\^-\]\/g, "\\\\\$&"\) \+ "\]\+\$"\);/);
  const p = el("p", "", "see a/b.md.), then c/d.md!?'\"`");
  linkifyPathTokens(p as unknown as HTMLElement);
  assert.deepEqual(textNodesOf(p).map((t) => t.data), ["see ", "a/b.md", ".), then ", "c/d.md", "!?'\"`"]);
});

test("pathological inputs finish and match: a slash before a 40K run of hex, a 40K token of dots, a 40K separator line, a minified dump", async () => {
  const { linkifyPathTokens, CLICKABLE_PATH_RE, PathTokenScanner } = await import("./path-links");
  const re = new RegExp(CLICKABLE_PATH_RE.source, "gi");
  for (const text of ["/" + "a1b2c3d4".repeat(5000), "/" + ".".repeat(40000), "-".repeat(40000) + "/x.md", "x/" + "_".repeat(40000), "var a=1;".repeat(5000) + "/a.b"]) {
    const scan = new PathTokenScanner(text);
    let from = 0, m: [number, number] | null;
    while ((m = scan.next(from))) { assert.deepEqual(m, regexNext(re, text, from)); from = m[1]; }
    assert.equal(regexNext(re, text, from), null);
    const p = el("p", "", text);
    linkifyPathTokens(p as unknown as HTMLElement);
    assert.equal(p.textContent, text, "the text reads as before");
  }
});

// ── the units: a line at a time, when a surface asks ──────────────────────────────────────────────
test("textUnits: with no unit selector every text node is a unit of its own (the chat's walk); under a selector the nodes sharing a unit ancestor join into one text; a <br> ends a unit; an empty unit element is an empty unit in its place; dead and inCode are read per node", async () => {
  const { textUnits, DEAD_TEXT } = await import("./path-links");
  const p = el("p", "", "a ", el("span", "x", "b"), " c");
  assert.deepEqual(textUnits(p as unknown as HTMLElement, undefined, DEAD_TEXT).map((u) => u.text), ["a ", "b", " c"], "no selector: node by node");
  const joined = textUnits(p as unknown as HTMLElement, "p", DEAD_TEXT);
  assert.equal(joined.length, 1); assert.equal(joined[0].text, "a b c");
  assert.deepEqual(joined[0].spans.map((s) => [s.start, s.end, s.dead, s.inCode]), [[0, 2, false, false], [2, 3, false, false], [3, 5, false, false]]);
  const rows = el("div", "", el("span", "fv-cl", el("span", "fv-ct", "one ", el("a", "", "docs/a.md"))), el("span", "fv-cl", el("span", "fv-ct")), el("span", "fv-cl", el("span", "fv-ct", el("code", "", "x.md"), " y", el("br"), "z")));
  const units = textUnits(rows as unknown as HTMLElement, ".fv-cl", DEAD_TEXT);
  assert.deepEqual(units.map((u) => u.text), ["one docs/a.md", "", "x.md y", "z"], "the second row is blank and stays a unit; the <br> cuts the third");
  assert.deepEqual(units[0].spans.map((s) => s.dead), [false, true], "the anchor's text is dead to marking but read");
  assert.deepEqual(units[2].spans.map((s) => s.inCode), [true, false]);
});

test("spanHolding and rewriteSpan: the span holding a range whole and open, null across an edge or in a dead span; a rewrite replaces one node with text and marks in order and changes no character", async () => {
  const { textUnits, spanHolding, rewriteSpan, DEAD_TEXT } = await import("./path-links");
  const p = el("p", "", "aa", el("a", "", "bb"), "ccdd");
  const u = textUnits(p as unknown as HTMLElement, "p", DEAD_TEXT)[0];
  assert.equal(u.text, "aabbccdd");
  assert.equal(spanHolding(u, 0, 2), u.spans[0]); assert.equal(spanHolding(u, 4, 8), u.spans[2]); assert.equal(spanHolding(u, 6, 8), u.spans[2]);
  assert.equal(spanHolding(u, 1, 3), null, "across an edge"); assert.equal(spanHolding(u, 2, 4), null, "in the link: dead"); assert.equal(spanHolding(u, 8, 9), null); assert.equal(spanHolding(u, -1, 1), null);
  const m1 = el("b", "", "c"), m2 = el("i", "", "d");
  rewriteSpan(u, u.spans[2], [{ start: 5, end: 6, el: m1 as unknown as Node }, { start: 7, end: 8, el: m2 as unknown as Node }]);
  assert.equal(p.textContent, "aabbccdd");
  assert.deepEqual(p.childNodes.map((c) => (c instanceof Txt ? c.data : (c as El).tagName + ":" + c.textContent)), ["aa", "A:bb", "c", "B:c", "d", "I:d"]);
});

test("the walk under the viewer's options: inPre reads a code body, unit joins a row's spans so a token the highlight cut through stays text while one held whole in a span links, accept and resolve are the surface's, lineSuffix rides a :12 into the link; without options the chat's walk is unchanged", async () => {
  const { linkifyPathTokens } = await import("./path-links");
  const row = (...kids: Array<El | string>) => el("span", "fv-cl", el("span", "fv-ct", ...kids));
  const c = el("pre", "", el("code", "hljs",
    row("cp ", el("span", "hljs-string", '"', el("span", "hljs-variable", "$HOME"), '/docs/a.md"')),
    row("x = ", el("span", "hljs-string", '"docs/b.md:12"'), " and/or docs/c.md"),
    row(el("span", "hljs-string", '"docs/'), el("span", "hljs-string", 'd.md"')),
  ));
  const seen: string[] = [];
  const hits = linkifyPathTokens(c as unknown as HTMLElement, null, undefined, {
    inPre: true, unit: ".fv-cl", lineSuffix: true,
    accept: (tok, ctx) => { seen.push(tok + "@" + ctx.at + "/" + ctx.text.length); return tok !== "docs/c.md"; },
    resolve: (tok) => "/tmp/TESTHOST/" + tok,
  });
  assert.deepEqual(seen, ["docs/b.md@5/35", "docs/c.md@26/35"],
    "the gate sees a LINE's token and its offset in the line; the first row's HOME/docs/a.md (what the line says, never the /docs/a.md the substitution's tail alone would read) is cut across two nodes and refused by the span test before any gate; and/or fails the shape gate");
  assert.deepEqual(hits.map((h) => h.open), ["/tmp/TESTHOST/docs/b.md"], "docs/c.md was refused by the surface's gate, the cut docs/d.md by the span test; the one link is resolved by the surface");
  // a substitution that leaves the path's tail whole in its own node: the token is `/notes/a.md`, and the gate is handed the line, where it is glued to the brace
  const glued = el("pre", "", el("code", "hljs", row("path: ", el("span", "hljs-string", el("span", "hljs-variable", "${HOME}"), "/notes/a.md"))));
  const seen2: Array<[string, string]> = [];
  linkifyPathTokens(glued as unknown as HTMLElement, null, undefined, { inPre: true, unit: ".fv-cl", accept: (tok, ctx) => { seen2.push([tok, ctx.text[ctx.at - 1]]); return false; } });
  assert.deepEqual(seen2, [["/notes/a.md", "}"]], "the surface's gate reads the character before the token off the LINE, not the node");
  const link = c.querySelectorAll(".file-uri-link")[0];
  assert.equal(link.textContent, "docs/b.md:12"); assert.equal(link.dataset.line, "12"); assert.equal(link.title, "Open /tmp/TESTHOST/docs/b.md:12");
  assert.equal(link.parentNode!.textContent, '"docs/b.md:12"', "inside the string span, the quotes outside");
  assert.equal(c.textContent, 'cp "$HOME/docs/a.md"x = "docs/b.md:12" and/or docs/c.md"docs/d.md"');
  // the chat's walk: no options, every node its own unit, <pre> skipped, no line suffix read
  const chat = el("div", "", el("p", "", "see docs/e.md:12 now"), el("pre", "", el("code", "", "docs/f.md")));
  const h2 = linkifyPathTokens(chat as unknown as HTMLElement);
  assert.deepEqual(h2.map((h) => h.open), ["docs/e.md"]);
  assert.deepEqual(textNodesOf(chat.childNodes[0] as El).map((t) => t.data), ["see ", "docs/e.md", ":12 now"], "the :12 stays prose in the chat");
});

test("the chat's fenced blocks (the user 2026-09-12): under inPre + preVerified a fenced token links ONLY on the kernel's verdict and under the surface's code gate; prose in the same body keeps the chat's rules; a fenced hit says so", async () => {
  const { linkifyPathTokens } = await import("./path-links");
  const { viewerPathGate } = await import("./file-view-links");
  const row = (...kids: Array<El | string>) => el("span", "cl", el("span", "ct", ...kids));   // code-block.ts's rows, as the chat's highlight leaves a fence
  const opts = { inPre: true, preVerified: true, unit: ".cl",
    accept: (tok: string, ctx: { text: string; at: number; inPre: boolean }) => !ctx.inPre || viewerPathGate(tok, ctx) };
  const body = () => el("div", "",
    el("p", "", "see docs/e.md and a/dup.md"),
    el("pre", "", el("code", "hljs",
      row("open ", el("span", "hljs-string", "'/tmp/TESTHOST/report/viewer.html'"), " now"),
      row("import fp from ", el("span", "hljs-string", "'lodash/fp.js'")),
      row("cat docs/e.md"))));
  // the kernel's map names the fenced path, the import's package and the prose path: the fenced path and both docs/e.md
  // link; the package stays text under the code gate, verdict or not; a/dup.md (no verdict) stays prose
  const map = { "/tmp/TESTHOST/report/viewer.html": "/tmp/TESTHOST/report/viewer.html", "lodash/fp.js": "node_modules/lodash/fp.js", "docs/e.md": "docs/e.md" };
  const b1 = body();
  assert.deepEqual(linkifyPathTokens(b1 as unknown as HTMLElement, null, map, opts).map((h) => [h.open, h.verified, h.inPre]),
    [["docs/e.md", true, false], ["/tmp/TESTHOST/report/viewer.html", true, true], ["docs/e.md", true, true]]);
  assert.deepEqual(links(b1).map((a) => a.textContent), ["docs/e.md", "/tmp/TESTHOST/report/viewer.html", "docs/e.md"], "the quotes around the fenced path stay text");
  // no map at all (an old kernel, a cached payload): prose links on shape as before; NOTHING in the fence does
  assert.deepEqual(linkifyPathTokens(body() as unknown as HTMLElement, null, undefined, opts).map((h) => [h.open, h.inPre]), [["docs/e.md", false], ["a/dup.md", false]]);
  // an empty map is a verdict of none: nothing links anywhere
  assert.deepEqual(linkifyPathTokens(body() as unknown as HTMLElement, null, {}, opts), []);
  // without the options the fence is dead text, as every other surface walked it before
  assert.deepEqual(linkifyPathTokens(body() as unknown as HTMLElement, null, map).map((h) => h.open), ["docs/e.md"]);
});
