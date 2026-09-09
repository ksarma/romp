// An http(s) URL in a user todo's text is a link (the user 2026-09-08, whose todo titles carried pull-request
// URLs that stayed plain text). Why they stayed plain: a todo's text is set with textContent and passed to the
// path walk (path-links.ts) and the PR-number linker (pr-links.ts) only; the path walk's gate refuses a token
// holding `:` or `//` on the note that http(s) links "are already <a>", which is true of a chat message (md()
// autolinks them) and false of a todo's text, which never sees the Markdown renderer. url-links.ts is the
// missing pass: the file viewer's URL grammar moved out of file-view-links.ts and a walk over the same text
// units the path walk uses, applied by both hosts' todo linkers BEFORE the path walk, so a URL is dead text to
// it (a path-shaped query value inside a URL is not a file). The anchors open in a new tab (target _blank, rel
// noopener noreferrer), show the URL as typed, and keep trailing punctuation and a sentence's closing bracket
// outside. The chat's document-level a[href] delegate opens them; the Waiting-on-you pane installs the same
// click-safe capture-phase opener the PR links use (link-opener.ts), keyed on the URL anchors' class.
//
// The walk runs for real over a DOM stand-in (the user-todo-links.test.ts idiom; there is no jsdom), the
// opener over the pr-links.test.ts document stand-in, and both hosts' wiring is pinned at source.
// Synthetic throughout: example.invalid addresses, the notes-api demo, a placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const UI = path.resolve(process.cwd(), "..", "ui", "webview");
const read = (f: string) => fs.readFileSync(path.join(UI, f), "utf8");
const RENDER = read("render.ts");
const WAITING = read("waiting.ts");
const URLS = read("url-links.ts");
const VIEWER_LINKS = read("file-view-links.ts");
const PR = read("pr-links.ts");
const OPENER = read("link-opener.ts");
const STYLES = read("styles.css");
const PANE_CSS = read("waiting-pane.css");

const SID = "11111111-2222-3333-4444-555555555555";
const PR_URL = "https://github.com/example-org/notes-api/pull/398";
const DOC_URL = "https://example.invalid/notes-api/docs/plan";

// ── a DOM stand-in just big enough for the walk: elements with class/dataset/title/href, text nodes, a tree
// walker over text nodes in document order, closest() over tag names and classes, replaceWith
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
  className = ""; title = ""; target = ""; rel = ""; dataset: Record<string, string> = {}; parentElement: Elm | null = null;
  attrs: Record<string, string> = {};
  get href(): string { return this.attrs.href || ""; }   // reflected from the attribute, as the browser's is
  setAttribute(n: string, v: string): void { if (n === "class") this.className = v; else if (n === "title") this.title = v; else this.attrs[n] = v; }
  getAttribute(n: string): string | null { if (n === "class") return this.className || null; if (n === "title") return this.title || null; return n in this.attrs ? this.attrs[n] : null; }
  childNodes: (Elm | TextNode)[] = [];
  constructor(public tagName: string) {}
  set textContent(s: string) { const t = new TextNode(s); t.parentElement = this; this.childNodes = [t]; }
  get textContent(): string { return this.childNodes.map((c) => (c instanceof TextNode ? c.data : c.textContent)).join(""); }
  appendChild(c: Elm | TextNode): Elm | TextNode { c.parentElement = this; this.childNodes.push(c); return c; }
  closest(sel: string): Elm | null {
    const alts = sel.split(",").map((s) => s.trim());
    for (let n: Elm | null = this; n; n = n.parentElement) {
      for (const a of alts) {
        if (a.startsWith(".") ? n.className.split(/\s+/).includes(a.slice(1)) : n.tagName === a) return n;
      }
    }
    return null;
  }
  get kids(): Elm[] { return this.childNodes.filter((c): c is Elm => c instanceof Elm); }
  get texts(): string[] { return this.childNodes.filter((c): c is TextNode => c instanceof TextNode).map((c) => c.data); }
}
function textNodesOf(root: Elm): TextNode[] {
  const out: TextNode[] = [];
  const walk = (n: Elm) => { for (const c of n.childNodes) { if (c instanceof TextNode) out.push(c); else walk(c); } };
  walk(root);
  return out;
}
(globalThis as any).NodeFilter = { SHOW_TEXT: 4, SHOW_ELEMENT: 1 };
(globalThis as any).document = {
  createElement: (tag: string) => new Elm(tag),
  createTextNode: (s: string) => s,
  createDocumentFragment: () => new Frag(),
  createTreeWalker: (root: Elm) => { const nodes = textNodesOf(root); let i = 0; return { nextNode: () => (i < nodes.length ? nodes[i++] : null) }; },
};
const span = (text: string, cls = "ut-text"): Elm => { const e = new Elm("span"); e.className = cls; e.textContent = text; return e; };
const anchorsOf = (e: Elm): Elm[] => e.kids.filter((k) => k.tagName === "a");

// ── the grammar (the viewer's, moved): what links and what stays outside the link
test("urlSegments: http and https, trailing sentence punctuation left out, a paren the URL opened kept, a sentence's closing paren not", async () => {
  const { urlSegments, urlRanges } = await import("./url-links");
  const hrefs = (s: string) => urlSegments(s).filter((x) => x.href).map((x) => x.href);
  assert.deepEqual(hrefs("see " + PR_URL), [PR_URL]);
  assert.deepEqual(hrefs("see " + PR_URL + "."), [PR_URL], "a trailing period is the sentence's");
  assert.deepEqual(hrefs("see " + PR_URL + ", then reply"), [PR_URL], "a trailing comma too");
  assert.deepEqual(hrefs("(see " + PR_URL + ")"), [PR_URL], "a closing paren the URL did not open");
  assert.deepEqual(hrefs("(see " + PR_URL + ")."), [PR_URL]);
  assert.deepEqual(hrefs("read https://example.invalid/wiki/Foo_(bar) first"), ["https://example.invalid/wiki/Foo_(bar)"], "a paren the URL opened is its own");
  assert.deepEqual(hrefs("read [https://example.invalid/a] and {http://example.invalid/b}"), ["https://example.invalid/a", "http://example.invalid/b"]);
  assert.deepEqual(hrefs("two: " + PR_URL + " and " + DOC_URL), [PR_URL, DOC_URL]);
  assert.deepEqual(hrefs("HTTPS://EXAMPLE.INVALID/X"), ["HTTPS://EXAMPLE.INVALID/X"], "the scheme is case-insensitive and the text is kept as typed");
  assert.deepEqual(hrefs("https:// is a bare scheme, ftp://example.invalid/x another scheme, example.invalid/x no scheme"), [], "no host, no http(s): prose");
  assert.deepEqual(hrefs("a URL with a query https://example.invalid/q?f=/docs/a.md&x=1 ends at the space"), ["https://example.invalid/q?f=/docs/a.md&x=1"]);
  for (const s of ["see " + PR_URL + ".", "(" + PR_URL + ")", "a " + PR_URL + " b " + DOC_URL + "."]) {
    assert.equal(urlSegments(s).map((x) => x.text).join(""), s, "the segments spell the text exactly: " + JSON.stringify(s));
  }
  assert.deepEqual(urlRanges("see " + PR_URL + "."), [[4, 4 + PR_URL.length]]);
});

// ── the walk, executed over a todo's text: anchors as typed, punctuation outside, paths still paths, a URL dead to the path walk
test("linkifyUrls over a todo's line: the URL as typed becomes an anchor that opens a new tab; the text around it is untouched", async () => {
  const { linkifyUrls, URL_LINK_CLASS } = await import("./url-links");
  const t = span("Need a review of " + PR_URL + " before the merge.");
  const made = linkifyUrls(t as unknown as HTMLElement) as unknown as Elm[];
  assert.equal(made.length, 1);
  const a = anchorsOf(t)[0];
  assert.equal(a, made[0], "the anchor made is the one in the tree");
  assert.equal(a.tagName, "a");
  assert.equal(a.className, URL_LINK_CLASS);
  assert.equal(URL_LINK_CLASS, "url-link");
  assert.equal(a.href, PR_URL);
  assert.equal(a.textContent, PR_URL, "the visible text is the URL as typed, not shortened");
  assert.equal(a.title, PR_URL, "the whole address on hover");
  assert.equal(a.target, "_blank");
  assert.equal(a.rel, "noopener noreferrer");
  assert.equal(a.getAttribute("draggable"), null, "a prose anchor drags as the chat's own anchors do (the viewer's rule is the viewer's)");
  assert.deepEqual(t.texts, ["Need a review of ", " before the merge."], "the trailing period stays outside the link");
  assert.equal(t.textContent, "Need a review of " + PR_URL + " before the merge.", "the text reads exactly as written");
});

test("linkifyUrls: a URL followed by a comma, one in parentheses, and two URLs in one text", async () => {
  const { linkifyUrls } = await import("./url-links");
  const comma = span("Merge " + PR_URL + ", then tag it");
  linkifyUrls(comma as unknown as HTMLElement);
  assert.deepEqual(anchorsOf(comma).map((a) => a.href), [PR_URL]);
  assert.deepEqual(comma.texts, ["Merge ", ", then tag it"]);
  const parens = span("Pick the design (" + DOC_URL + ").");
  linkifyUrls(parens as unknown as HTMLElement);
  assert.deepEqual(anchorsOf(parens).map((a) => a.textContent), [DOC_URL], "the closing paren and the period stay outside");
  assert.deepEqual(parens.texts, ["Pick the design (", ")."]);
  const two = span("Compare " + PR_URL + " with " + DOC_URL);
  const made = linkifyUrls(two as unknown as HTMLElement) as unknown as Elm[];
  assert.deepEqual(made.map((a) => a.href), [PR_URL, DOC_URL], "both, in document order");
  assert.deepEqual(two.texts, ["Compare ", " with "]);
  // a text with no URL is left alone entirely: no splice, no anchors
  const plain = span("Need the staging port and the fixture format pick.");
  assert.deepEqual(linkifyUrls(plain as unknown as HTMLElement), []);
  assert.deepEqual(plain.texts, ["Need the staging port and the fixture format pick."]);
});

test("URLs first, then the path walk: a URL and a file path in one text each link their own way, and a path-shaped run inside the URL is not a file", async () => {
  const { linkifyUrls } = await import("./url-links");
  const { linkifyPathTokens } = await import("./path-links");
  const t = span("Review " + PR_URL + " and docs/plan.md (see https://example.invalid/q?f=/docs/b.md).");
  linkifyUrls(t as unknown as HTMLElement);                    // the order both hosts' todo linkers use
  const hits = linkifyPathTokens(t as unknown as HTMLElement, SID);
  assert.deepEqual(hits.map((h) => h.open), ["docs/plan.md"], "the path links; /docs/b.md inside the URL is dead text to the walk");
  const kids = t.kids;
  assert.deepEqual(kids.map((k) => k.tagName), ["a", "span", "a"]);
  assert.deepEqual(kids.map((k) => k.textContent), [PR_URL, "docs/plan.md", "https://example.invalid/q?f=/docs/b.md"]);
  assert.equal(kids[1].className, "file-uri-link");
  assert.deepEqual(kids[1].dataset, { act: "openpath", path: "docs/plan.md", rel: "1", sid: SID }, "the path link is the todo's session's, as before");
  assert.deepEqual(t.texts, ["Review ", " and ", " (see ", ")."]);
  assert.equal(t.textContent, "Review " + PR_URL + " and docs/plan.md (see https://example.invalid/q?f=/docs/b.md).");
  // the same text with the path walk alone (the old world): the URL stayed prose and its query value linked as a file
  const old = span("Review " + PR_URL + " and docs/plan.md (see https://example.invalid/q?f=/docs/b.md).");
  const oldHits = linkifyPathTokens(old as unknown as HTMLElement, SID);
  assert.deepEqual(oldHits.map((h) => h.open), ["docs/plan.md", "/docs/b.md"], "the diagnosis: the gate refused the URL's `//` token, and the walk then read the query value as an absolute path");
  assert.equal(anchorsOf(old).length, 0);
  // text already inside an anchor is never re-marked: a second URL pass makes nothing
  assert.deepEqual(linkifyUrls(t as unknown as HTMLElement), []);
});

// ── the opener (the Waiting-on-you pane): the PR opener's mechanics, keyed on the URL anchors' class
function fakeDoc() {
  const handlers = new Map<string, (e: Event) => void>();
  const captures = new Map<string, boolean | undefined>();
  return {
    doc: { addEventListener: (type: string, fn: (e: Event) => void, cap?: boolean) => { handlers.set(type, fn); captures.set(type, cap); } },
    fire(type: string, target: any, extra: Record<string, unknown> = {}) {
      const calls: string[] = [];
      const ev: any = { target, button: 0, isPrimary: true, ...extra,
        preventDefault: () => calls.push("preventDefault"), stopPropagation: () => calls.push("stopPropagation") };
      const h = handlers.get(type);
      assert.ok(h, "a listener for " + type);
      h!(ev);
      return calls;
    },
    types: () => Array.from(handlers.keys()).sort(),
    capture: (type: string) => captures.get(type),
  };
}
/** a node standing for an anchor of class `cls` with `href`, a new object each call as a rebuilt node is */
const anchor = (href: string, cls = "url-link") => {
  const node = { closest: (sel: string) => sel.startsWith("a." + cls) ? { getAttribute: (k: string) => k === "href" ? href : null } : null, contains: (n: unknown) => n === node };
  return node;
};
const plain = { closest: () => null, contains: () => false };
const SPENT = ["preventDefault", "stopPropagation"];

test("installUrlLinkOpener: capture phase on the stable document; press and release on a url-link open it once, the click is spent, a keyboard click opens too", async () => {
  const { installUrlLinkOpener } = await import("./url-links");
  const f = fakeDoc(); const opened: string[] = []; const posted: any[] = [];
  installUrlLinkOpener(f.doc, (m) => posted.push(m), { protocol: () => "https:", open: (h) => opened.push(h) });
  assert.deepEqual(f.types(), ["click", "keydown", "pointercancel", "pointerdown", "pointerup"]);
  for (const t of f.types()) assert.equal(f.capture(t), true, t + ": the row's fold under the link must not fire");
  f.fire("pointerdown", anchor(PR_URL));
  assert.deepEqual(opened, [], "nothing on the press");
  const twin = anchor(PR_URL);                                 // the push rebuilt the row
  f.fire("pointerup", twin);
  assert.deepEqual(opened, [PR_URL]);
  assert.deepEqual(f.fire("click", twin), SPENT, "the native click is spent: uttoggle never folds the row");
  assert.deepEqual(opened, [PR_URL], "no second open");
  assert.deepEqual(f.fire("click", anchor(DOC_URL)), SPENT, "a click with no press (Enter on a focused link) opens");
  assert.deepEqual(opened, [PR_URL, DOC_URL]);
  assert.deepEqual(f.fire("click", plain), [], "an unrelated click passes");
  assert.deepEqual(posted, [], "on the web the browser's own tab, nothing posted");
});

test("installUrlLinkOpener serves only URL anchors with an http(s) href, and posts openLink under VS Code", async () => {
  const { installUrlLinkOpener } = await import("./url-links");
  const f = fakeDoc(); const opened: string[] = []; const posted: any[] = [];
  installUrlLinkOpener(f.doc, (m) => posted.push(m), { protocol: () => "vscode-webview:", open: (h) => opened.push(h) });
  assert.deepEqual(f.fire("click", anchor(PR_URL, "pr-link")), [], "a PR link is the PR opener's, not this one's");
  assert.deepEqual(f.fire("click", anchor("javascript:alert(1)")), [], "not a web address: never opened");
  assert.deepEqual(f.fire("click", anchor("file:///tmp/notes-api/a.md")), [], "nor a file URI");
  assert.deepEqual(f.fire("click", anchor(PR_URL)), SPENT);
  assert.deepEqual(opened, [], "the webview cannot window.open…");
  assert.deepEqual(posted, [{ type: "openLink", href: PR_URL }], "…so the host's openExternal takes it");
});

// ── the chip: a todo's own `link` beside its file chip, the same dress, the whole address on hover
test("urlChip / urlChipLabel: the address without its scheme as the label, the whole address as the title, a new tab on click, the caller's chip class beside url-link", async () => {
  const { urlChip, urlChipLabel, URL_LINK_CLASS } = await import("./url-links");
  assert.equal(urlChipLabel(PR_URL), "github.com/example-org/notes-api/pull/398");
  assert.equal(urlChipLabel("http://example.invalid/"), "example.invalid", "a trailing slash is dropped");
  assert.equal(urlChipLabel("HTTPS://Example.invalid/x/"), "Example.invalid/x", "the host as typed");
  const c = urlChip(PR_URL, "ut-link") as unknown as Elm;
  assert.equal(c.tagName, "a");
  assert.equal(c.className, URL_LINK_CLASS + " ut-link");
  assert.equal(c.href, PR_URL);
  assert.equal(c.title, PR_URL);
  assert.equal(c.textContent, "github.com/example-org/notes-api/pull/398");
  assert.equal(c.target, "_blank");
  assert.equal(c.rel, "noopener noreferrer");
  const w = urlChip(DOC_URL, "wt-link") as unknown as Elm;
  assert.equal(w.className, URL_LINK_CLASS + " wt-link", "the pane's dress on the same anchor");
});

// ── parity at source: both hosts run the URL pass first, and each opens the anchors its own way
test("render.ts: the two todo linkers run linkifyUrls before the path walk; the chat installs no opener (its a[href] delegate opens every absolute-scheme anchor)", () => {
  assert.match(RENDER, /import \{ linkifyUrls, urlChip \} from "\.\/url-links";/);
  assert.match(RENDER, /function linkTodoLinePaths\(node: HTMLElement, sid: string \| null\): void \{\n\s*linkifyUrls\(node\);\n\s*linkifyPathTokens\(node, sid\);\n\}/);
  assert.match(RENDER, /function linkTodoDetailPaths\(node: HTMLElement, sid: string \| null\): void \{\n\s*linkifyUrls\(node\);\n\s*linkifyFileUris\(node, undefined, undefined, undefined, undefined, sid, true\);\n\}/);
  assert.doesNotMatch(RENDER, /installUrlLinkOpener|installPrLinkOpener/, "the chat's own a[href] delegate already opens every absolute-scheme anchor");
  assert.match(RENDER, /if \(!url \|\| \(url\.protocol !== "http:" && url\.protocol !== "https:"\)\) return;/, "that delegate opens http(s) hrefs");
  assert.match(RENDER, /window\.open\(href, "_blank", "noopener,noreferrer"\); \/\/ web dashboard/);
  assert.match(RENDER, /vscodeApi\.postMessage\(\{ type: "openLink", href \}\);  \/\/ VS Code webview/);
});

test("waiting.ts: linkTodoPaths runs linkifyUrls before its framed gate (a URL opens from any page), and the pane installs the URL opener beside the PR one", () => {
  assert.match(WAITING, /import \{ linkifyUrls, urlChip, installUrlLinkOpener \} from "\.\/url-links";/);
  assert.match(WAITING, /const framed = window\.parent !== window;\nfunction linkTodoPaths\(node: HTMLElement, sid: string\): void \{\n\s*linkifyUrls\(node\);[^\n]*\n\s*if \(!framed\) return;\n\s*linkifyPathTokens\(node, sid\);\n\}/);
  assert.match(WAITING, /installPrLinkOpener\(document, vscodeApi \? \(m\) => vscodeApi\.postMessage\(m\) : undefined\);\n(?:\/\/[^\n]*\n)*installUrlLinkOpener\(document, vscodeApi \? \(m\) => vscodeApi\.postMessage\(m\) : undefined\);/);
  assert.equal((WAITING.match(/installUrlLinkOpener\(/g) || []).length, 1, "installed once, on the document");
});

test("the grammar has ONE home: file-view-links.ts imports it back from url-links.ts and its own pass is the same walk under the viewer's class, units and non-draggable anchors", () => {
  assert.match(VIEWER_LINKS, /import \{ urlSegments, urlRanges, linkifyUrls as markUrls \} from "\.\/url-links";/);
  assert.match(VIEWER_LINKS, /export \{ urlSegments, urlRanges \};/, "re-exported where the viewer's callers and tests read it");
  assert.doesNotMatch(VIEWER_LINKS, /const URL_RE = |function trimUrl\(|export function urlSegments\(/, "no second copy of the grammar");
  assert.match(VIEWER_LINKS, /export function linkifyUrls\(root: HTMLElement\): HTMLAnchorElement\[\] \{\n\s*return markUrls\(root, \{ className: URL_LINK_CLASS, unit: LINE_UNITS, draggable: false \}\);\n\}/);
  assert.match(URLS, /const URL_RE = \/https\?:\\\/\\\/\[\^\\s<>"'`\]\+\/gi;/);
  assert.match(URLS, /const URL_TRAIL = "\.,;:!\?'\\"";/);
  assert.match(URLS, /const PAIRS: Record<string, string> = \{ "\)": "\(", "\]": "\[", "\}": "\{" \};/);
});

test("the opener has ONE home: link-opener.ts; pr-links.ts and url-links.ts each install it with their own anchors", () => {
  assert.match(OPENER, /export function installLinkOpener\(doc: OpenerDoc, post: OpenerPost, hrefAt: HrefAt, env: OpenerEnv = browserEnv\): void \{/);
  assert.match(PR, /import \{ installLinkOpener, anchorHrefAt \} from "\.\/link-opener";/);
  assert.match(PR, /export function installPrLinkOpener\(doc: OpenerDoc, post: OpenerPost, env\?: OpenerEnv\): void \{\n\s*installLinkOpener\(doc, post, prLinkHrefAt, env\);\n\}/);
  assert.doesNotMatch(PR, /doc\.addEventListener\("pointerup"/, "pr-links.ts no longer carries the mechanics");
  assert.match(URLS, /export function installUrlLinkOpener\(doc: OpenerDoc, post: OpenerPost, env\?: OpenerEnv\): void \{\n\s*installLinkOpener\(doc, post, urlLinkHrefAt, env\);\n\}/);
  assert.match(URLS, /export const isWebUrl = \(href: string\): boolean => \/\^https\?:\\\/\\\/\[\^\\s\/\?#\]\+\/i\.test\(href\);/);
});

test("the sheets dress the anchors: .url-link in the hyperlink ink (styles.css, which the pane loads too); the chips in the file chip's pill on both surfaces", () => {
  assert.match(STYLES, /\.url-link \{ color: var\(--link\); text-decoration: none; \}\n\.url-link:hover \{ text-decoration: underline; \}/);
  assert.match(STYLES, /\.ut-link, \.ut-file \{ display: inline-block; max-width: 32%;/, "the link chip shares the file chip's rule (the file chip's selector kept whole, for the pins on it)");
  assert.match(STYLES, /a\.ut-link \{ color: var\(--accent\); text-decoration: none; \}\na\.ut-link:hover \{ filter: brightness\(1\.12\); text-decoration: none; \}/, "the element selector outranks .url-link's class rules, whichever order the sheet loads them");
  assert.match(STYLES, /#ut-reply-prompt \.ut-link, #ut-reply-prompt \.ut-file \{ max-width: 100%; \}/);
  assert.match(PANE_CSS, /\.wt-link,\.wt-file\{flex:0 0 auto;display:block;max-width:32%;/);
  assert.match(PANE_CSS, /a\.wt-link\{color:var\(--accent,#9cd2ff\);text-decoration:none\}\na\.wt-link:hover\{filter:brightness\(1\.12\);text-decoration:none\}/);
  assert.match(PANE_CSS, /#ut-reply-prompt \.wt-link,#ut-reply-prompt \.wt-file\{align-self:flex-start;max-width:100%;margin:2px 0 4px\}/);
});
