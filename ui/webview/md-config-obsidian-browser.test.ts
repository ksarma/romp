// The Slice 4 constructs over the REAL Files bundle in headless Chromium (plans/markdown-viewer.md, "one markdown
// configuration, Obsidian constructs included"): the synthetic fixture anchor-map-fixtures/obsidian.md opened as a file
// document through the pane's relay, so every construct goes through marked under md-config.ts, DOMPurify, the viewer's
// own passes (heading ids, rewriteFigureSrcs, linkMarkdownAnchors, the figure gate) and KaTeX's fill, and the page's
// DOM is what the assertions read: the front matter as one folded block at the top, the footnote reference and its
// definition in place under the sanitizer's prefixed ids, the callouts as titled quotes and a closed details, the mark,
// the wikilinks as path links to the sibling note (decision 2) and the embeds as pictures through /file, two KaTeX
// roots (decision 1: the files bundle carries the grammar and KaTeX). Then the acceptance clicks: a `#section` link, a
// footnote reference and its back link scroll `.fileview-body` and open no tab, and the page's location stands. Then
// the anchor map over the real DOM (the same probe shape as md-sanitize-anchor-map-browser.test.ts, over the pane's own
// rendered box): a paragraph after each construct maps to its indexOf offset, a callout's body and a definition's text
// map inside their marker lines, a paragraph with inline math maps around the formula, and the viewer's own text (the
// YAML, a callout's title, a footnote's number) refuses with a reason in the person's terms. The feed page is opened
// once too, under feed.css BUILT as the webview build builds it, so the KaTeX sheet the feed gains with this slice is
// seen applied. Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs do. Synthetic
// values only: an invented note, TESTHOST paths, a placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { FEED_BODY } from "../../vscode-extension/src/page-skeleton";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
// resolve playwright and esbuild from the extension, not from wherever this bundle was written (a single-file run lands it under TMPDIR)
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");
const KATEX_CSS = fs.readFileSync(path.join(EXT, "node_modules", "katex", "dist", "katex.min.css"), "utf8");
const STYLES = fs.readFileSync(path.join(UI, "styles.css"), "utf8").replace('@import "katex/dist/katex.min.css";', KATEX_CSS);
const PANE = fs.readFileSync(path.join(UI, "files-pane.css"), "utf8");
const FIX = fs.readFileSync(path.join(UI, "anchor-map-fixtures", "obsidian.md"), "utf8");

const SID = "11111111-2222-3333-4444-555555555555";
const DIR = "/tmp/TESTHOST/notes-api/docs/";
const FILE_PATH = DIR + "report.md";

const BUILD = { bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
  nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent" };
/** The Files pane's bundle plus the anchor map's exports, for the mapping over the page's own rendered box. */
function filesBundle(): string {
  const contents = 'import "./files";\nimport { mapRenderedSelection, sourceBlockSpans, renderedBlockIndex } from "./anchor-map";\n(window as any).__rompProbe = { mapRenderedSelection, sourceBlockSpans, renderedBlockIndex };\n';
  const r = requireCjs("esbuild").buildSync({ ...BUILD, stdin: { contents, resolveDir: UI, loader: "ts", sourcefile: "files-probe.ts" } });
  return r.outputFiles[0].text;
}
function feedBundle(): string {
  const r = requireCjs("esbuild").buildSync({ ...BUILD, entryPoints: [path.join(UI, "feed.ts")] });
  return r.outputFiles[0].text;
}
/** feed.css as the webview build emits it: the KaTeX @import inlined (esbuild.js's webview config, in memory). */
async function builtFeedCss(): Promise<string> {
  const { webview } = requireCjs("./esbuild.js") as { webview: Record<string, unknown> };
  const r = await (requireCjs("esbuild") as typeof import("esbuild")).build({ ...(webview as object), entryPoints: ["../ui/webview/feed.css"], write: false, logLevel: "silent" });
  return r.outputFiles!.find((f) => f.path.endsWith(".css"))!.text;
}
const FILES_HTML = `<!DOCTYPE html><html><head><meta charset=utf-8><style>${STYLES}\n${PANE}</style></head><body class=fileview-pane>
<div id=files-empty></div>
<script>window.__posts=[];window.acquireVsCodeApi=function(){return{postMessage:function(m){window.__posts.push(m);}}};</script>
<script src=/dist/files.js></script></body></html>`;
const FEED_HTML = (css: string) => `<!DOCTYPE html><html><head><meta charset=utf-8><style>${css}</style></head><body>
${FEED_BODY}
<script>window.__posts=[];window.acquireVsCodeApi=function(){return{postMessage:function(m){window.__posts.push(m);}}};</script>
<script src=/dist/feed.js></script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

async function inBrowser(t: any, body: (browser: any) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box; the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  try { await body(browser); } finally { await browser.close(); }
}

type Opened = { page: any; errors: string[]; requests: string[]; newPages: () => number };
/** A page of the surface with the fixture open as a file document (the pane's relay), every request logged, the first paint awaited. */
async function openFixture(browser: any, surface: "files" | "feed", js: string, html: string, viewport = { width: 900, height: 260 }): Promise<Opened> {
  const ctx = await browser.newContext({ viewport });
  let pages = 0;
  ctx.on("page", () => { pages++; });
  const page = await ctx.newPage();
  pages = 0;
  const errors: string[] = [];
  const requests: string[] = [];
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  page.on("request", (r: any) => { requests.push(r.url()); });
  await ctx.route("**/*", (route: any) => {
    const u = new URL(route.request().url());
    if (u.host !== "romp.test") return route.fulfill({ status: 404, body: "" });
    if (u.pathname === "/" + surface) return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: html });
    if (u.pathname === "/dist/" + surface + ".js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
    if (u.pathname === "/file" && u.searchParams.get("path") === FILE_PATH) {
      return route.fulfill({ status: 200, contentType: "text/plain; charset=utf-8", headers: { "X-Romp-Mtime-Ns": "1", "X-Romp-Text-Utf8": "1" }, body: FIX });
    }
    return route.fulfill({ status: 404, body: "" });
  });
  await page.goto("http://romp.test/" + surface);
  await page.evaluate(([p, sid]: [string, string]) => { window.postMessage({ romp: "viewFile", path: p, sid }, "*"); }, [FILE_PATH, SID] as [string, string]);
  await page.waitForSelector("#romp-fileview .fileview-body .fileview-md", { timeout: 15000 });
  await page.evaluate(() => new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r()))));
  return { page, errors, requests, newPages: () => pages };
}

/** Everything the page shows for each construct, read in the page. */
function readConstructs() {
  const md = document.querySelector("#romp-fileview .fileview-md") as HTMLElement;
  const q = (s: string) => md.querySelector(s) as HTMLElement | null;
  const qa = (s: string) => Array.from(md.querySelectorAll(s)) as HTMLElement[];
  const attrs = (e: Element | null, names: string[]) => { const o: Record<string, string | null> = {}; for (const n of names) o[n] = e ? e.getAttribute(n) : "(none)"; return o; };
  const kids = Array.from(md.children) as HTMLElement[];
  const fm = q(":scope > details.md-frontmatter");
  const fn1 = q("#user-content-fn-1"), fn2 = q("#user-content-fn-2");
  const wikiP = qa(":scope > p").find((p) => (p.textContent || "").startsWith("Wiki "))!;
  const embedP = qa(":scope > p").find((p) => (p.textContent || "").startsWith("Embed "))!;
  const linkP = qa(":scope > p").find((p) => (p.textContent || "").startsWith("Links: "))!;
  const linkOf = (a: Element): Record<string, string | null> => ({ text: a.textContent, ...attrs(a, ["href", "class", "data-path", "data-frag", "data-act", "title", "target"]) });
  return {
    tags: kids.map((k) => k.tagName + (k.className ? "." + String(k.className).split(" ")[0] : "")),
    frontMatter: fm ? { first: md.firstElementChild === fm, open: fm.hasAttribute("open"), summary: fm.querySelector("summary.md-frontmatter-head")?.textContent, pre: fm.querySelector("pre")?.textContent, hr: qa(":scope > hr").length, h2Top: qa(":scope > h2").map((h) => h.id) } : null,
    fnref: qa("sup.md-fnref a").map(linkOf),
    fnrefIds: qa("sup.md-fnref a").map((a) => a.id),
    fn1: fn1 ? { tag: fn1.tagName, cls: fn1.className, text: fn1.textContent, prevHasRef: !!fn1.previousElementSibling?.querySelector("sup.md-fnref"), body: [fn1.firstElementChild?.tagName, fn1.children.length, fn1.firstElementChild?.firstElementChild?.className], back: linkOf(fn1.querySelector(".md-fnback")!) } : null,
    fn2: fn2 ? { text: fn2.textContent, link: linkOf(fn2.querySelector("a[href^='https://']")!) } : null,
    callouts: qa(".md-callout").map((c) => ({ tag: c.tagName, cls: c.className, open: c.hasAttribute("open"), title: c.querySelector(".md-callout-title")?.tagName + ":" + c.querySelector(".md-callout-title")?.textContent, body: Array.from(c.children).slice(1).map((e) => e.textContent).join("|") })),
    mark: qa("mark").map((m) => m.textContent), del: qa("del").map((d) => d.textContent), single: (q("h1")!.nextElementSibling!.textContent || "").includes("~single~"),
    wiki: Array.from(wikiP.querySelectorAll("a, span.fv-wikilink")).map(linkOf),
    embeds: { imgs: Array.from(embedP.querySelectorAll("img")).map((i) => attrs(i, ["src", "data-fv-src", "alt", "width", "height"])), chips: Array.from(embedP.querySelectorAll("a.fv-embed")).map(linkOf), dead: embedP.querySelectorAll(".fv-wikilink").length },
    math: { katex: qa(".katex").length, display: qa(".katex-display").length, displayTop: !!q(":scope > .katex-display"), placeholders: qa(".md-math-inline, .md-math-display").length, dollars: (md.textContent || "").includes("$"), displayH: q(".katex-display")?.getBoundingClientRect().height || 0 },
    headings: { h1: q("h1")?.id, h2: q("h2")?.id },
    links: Array.from(linkP.querySelectorAll("a")).map(linkOf),
  };
}
type Constructs = ReturnType<typeof readConstructs>;

/** The anchor map over the page's own rendered box: `needles` are [text, occurrence] pairs selected in the rendered text, `spans`
 *  are [fromText, toText] selections from the start of one to the end of the other; plus the block pairing of every top-level child. */
function mapInPage({ needles, spans, source }: { needles: Array<[string, number]>; spans: Array<[string, string]>; source: string }) {
  const probe = (window as any).__rompProbe;
  const md = document.querySelector("#romp-fileview .fileview-md") as HTMLElement;
  const point = (needle: string, atEnd: boolean, k: number) => {
    const walker = document.createTreeWalker(md, NodeFilter.SHOW_TEXT);
    let seen = 0;
    for (let n = walker.nextNode() as Text | null; n; n = walker.nextNode() as Text | null) {
      let from = 0;
      for (;;) { const i = n.data.indexOf(needle, from); if (i < 0) break; if (seen++ === k) return { node: n, offset: atEnd ? i + needle.length : i }; from = i + 1; }
    }
    throw new Error("not in the rendered text: " + needle);
  };
  const sel = (a: { node: Text; offset: number }, f: { node: Text; offset: number }) => ({ anchorNode: a.node, anchorOffset: a.offset, focusNode: f.node, focusOffset: f.offset, isCollapsed: false });
  const one = (t: string, k: number) => probe.mapRenderedSelection(sel(point(t, false, k), point(t, true, k)), md, source);
  const out: Record<string, unknown> = {};
  for (const [t, k] of needles) out[t + "#" + k] = one(t, k);
  for (const [a, b] of spans) out[a + "..." + b] = probe.mapRenderedSelection(sel(point(a, false, 0), point(b, true, 0)), md, source);
  const kids = Array.from(md.children);
  return { map: out, owners: kids.map((k) => probe.renderedBlockIndex(md, source, k)), blocks: probe.sourceBlockSpans(source).length, children: kids.length };
}

test("the Files bundle renders every construct of the fixture as its element, in place; the `#` clicks scroll the body and open no tab; the anchor map over the real DOM maps around every construct", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const js = filesBundle();
    const { page, errors, requests, newPages } = await openFixture(browser, "files", js, FILES_HTML);
    const c: Constructs = await page.evaluate(readConstructs);

    // one element per block, in the fixture's order (the anchor map's 1:1 pairing rests on it); the display formula is
    // KaTeX's own top-level span once the fill unwraps the placeholder
    assert.deepEqual(c.tags, ["DETAILS.md-frontmatter", "P", "H1", "P", "DIV.md-footnote", "P", "DIV.md-footnote", "P", "BLOCKQUOTE.md-callout", "P", "BLOCKQUOTE.md-callout", "DETAILS.md-callout", "P", "P", "P", "P", "SPAN.katex-display", "P", "H2", "P", "P"]);
    // front matter: the first child, folded, the YAML as text; no <hr> and no setext h2 minted from the keys (the High defect)
    assert.deepEqual(c.frontMatter, { first: true, open: false, summary: "Front matter", pre: "title: Test Note\ntags: [a, b]", hr: 0, h2Top: ["md-heading-two"] });
    // footnotes: the reference is a section link to the definition (the sanitizer's prefixed id, found by fragmentTarget), the
    // definition stands right after the paragraph that refers to it, its back link points at the reference; the URL-only
    // definition renders as a footnote whose text is a web link (marked's def rule used to swallow it)
    assert.deepEqual(c.fnref.map((l) => [l.text, l.href, l["data-frag"], /fv-frag/.test(l.class || ""), /fv-dead/.test(l.class || "")]), [["1", "#fn-1", "fn-1", true, false]]);
    assert.deepEqual(c.fnrefIds, ["user-content-fnref-1"]);
    assert.ok(c.fn1, "the definition renders");
    assert.deepEqual([c.fn1!.tag, c.fn1!.cls, c.fn1!.text, c.fn1!.prevHasRef], ["DIV", "md-footnote", "1 The footnote definition text.", true]);
    assert.deepEqual(c.fn1!.body, ["P", 1, "md-fnback fv-frag"], "the body is one paragraph inside the div, the back link first in it (round 10: its spaces paint as a paragraph's)");
    assert.deepEqual([c.fn1!.back.text, c.fn1!.back.href, c.fn1!.back["data-frag"], c.fn1!.back.class], ["1", "#fnref-1", "fnref-1", "md-fnback fv-frag"]);
    assert.ok(c.fn2, "the URL-only definition renders");
    assert.equal(c.fn2!.text, "[^2]: https://example.test/def-only", "nothing refers to this definition: its label is the marker as written (md-config.ts), never a number that looks like a reference's");
    assert.deepEqual([c.fn2!.link.href, c.fn2!.link.target], ["https://example.test/def-only", "_blank"]);
    // callouts: GitHub's and Obsidian's as one blockquote with a title line; the fold marker as a closed details
    assert.deepEqual(c.callouts, [
      { tag: "BLOCKQUOTE", cls: "md-callout md-callout-note", open: false, title: "P:Title", body: "Callout body line." },
      { tag: "BLOCKQUOTE", cls: "md-callout md-callout-note", open: false, title: "P:Note", body: "GitHub alert body." },
      { tag: "DETAILS", cls: "md-callout md-callout-tip", open: false, title: "SUMMARY:Folded tip", body: "Hidden body." },
    ]);
    assert.deepEqual([c.mark, c.del, c.single], [["marked text"], ["struck"], true], "==mark== renders, ~~del~~ renders, a lone ~ stays literal");
    // wikilinks in a file document: path links to the sibling note beside this file (decision 2; the fragment rides data-frag),
    // a `[[#Heading]]` is this document's section link, `[[img.png]]` keeps its extension; none is the dead span
    assert.deepEqual(c.wiki.map((l) => [l.text, l["data-path"], l["data-frag"], l["data-act"], l.href, /fv-frag/.test(l.class || ""), /fv-dead/.test(l.class || "")]), [
      ["Note", DIR + "Note.md", null, "openpath", null, false, false],
      ["alias", DIR + "Note.md", null, "openpath", null, false, false],
      ["Note#Heading", DIR + "Note.md", "Heading", "openpath", null, false, false],
      ["#Heading Two", null, "Heading Two", null, "#Heading%20Two", true, false],
      ["img.png", DIR + "img.png", null, "openpath", null, false, false],
    ]);
    // embeds: a picture through /file with the authored spelling kept for the comments panel, sized as written; a note embed is a chip
    assert.deepEqual(c.embeds.imgs.map((i) => [i["data-fv-src"], i.alt, i.width, i.height, (i.src || "").startsWith("/file?path=" + encodeURIComponent(DIR + "image.png"))]), [["image.png", "image.png", null, null, true], ["image.png", "image.png", "300", null, true]]);
    assert.deepEqual(c.embeds.chips.map((l) => [l.text, l["data-path"], l["data-act"]]), [["Note", DIR + "Note.md", "openpath"]]);
    assert.equal(c.embeds.dead, 0, "in a file document no wikilink is the dead span");
    assert.ok(requests.some((u) => u.startsWith("http://romp.test/file?path=" + encodeURIComponent(DIR + "image.png"))), "the embed's picture was fetched through /file: " + JSON.stringify(requests));
    // math: KaTeX in the Files pane (decision 1), the display formula at the top level, no placeholder and no TeX delimiter left as text
    assert.deepEqual([c.math.katex, c.math.display, c.math.displayTop, c.math.placeholders, c.math.dollars], [2, 1, true, 0, false], JSON.stringify(c.math));
    assert.ok(c.math.displayH > 20, "the display sum has KaTeX's layout height: " + c.math.displayH);
    assert.deepEqual(c.headings, { h1: "md-heading-one", h2: "md-heading-two" });
    assert.deepEqual(c.links.map((l) => [l.text, l.href, l["data-frag"], /fv-frag/.test(l.class || ""), /fv-dead/.test(l.class || "")]), [["one", "#heading-one", "heading-one", true, false], ["two", "#Heading%20Two", "Heading Two", true, false], ["fn", "#fn-1", "fn-1", true, false]], "`#fn-1` lands on the definition under its prefix");

    // the `#` clicks: the body scrolls, the location stands, no tab opens
    const url0: string = await page.evaluate(() => location.href);
    const inView = (sel: string) => page.evaluate((s: string) => {
      const b = document.querySelector("#romp-fileview .fileview-body")!.getBoundingClientRect();
      const r = document.querySelector("#romp-fileview .fileview-md " + s)!.getBoundingClientRect();
      return { top: Math.round(r.top - b.top), inside: r.top >= b.top - 1 && r.bottom <= b.bottom, scrollTop: document.querySelector("#romp-fileview .fileview-body")!.scrollTop };
    }, sel);
    const settle = () => page.evaluate(() => new Promise((r) => requestAnimationFrame(() => setTimeout(r, 60))));
    assert.equal((await inView("h1")).inside, true, "the fixture opens at its top: the h1 is in view");
    await page.locator("#romp-fileview .fileview-md a", { hasText: /^one$/ }).click(); await settle();
    const h1 = await inView("h1");
    assert.ok(h1.inside && h1.top <= 12 && h1.scrollTop > 0, "the h1 sits at the body's top edge (scroll-margin-top 10px) after the `#heading-one` click: " + JSON.stringify(h1));
    await page.locator("#romp-fileview .fileview-md a", { hasText: /^fn$/ }).click(); await settle();
    const def = await inView("#user-content-fn-1");
    assert.ok(def.inside && def.top <= 12, "the footnote's definition sits at the body's top after the `#fn-1` click: " + JSON.stringify(def));
    await page.locator("#romp-fileview .fileview-md a.md-fnback").first().click(); await settle();   // the first definition's back link (the URL-only definition has one too)
    const ref = await inView("#user-content-fnref-1");
    assert.ok(ref.inside, "the back link brings the reference into view: " + JSON.stringify(ref));
    assert.equal(await page.evaluate(() => location.href), url0, "the page's location never changed");
    assert.equal(newPages(), 0, "no tab opened");

    // the anchor map over the real DOM
    const at = (s: string) => { const i = FIX.indexOf(s); assert.ok(i >= 0, s); return i; };
    const needles: Array<[string, number]> = [
      ["Para after front", 0], ["Para after footnote", 0], ["Para after url-only", 0], ["Para after callout", 0], ["Para after folded", 0], ["Para after display", 0], ["Last para.", 0],
      ["Callout body line.", 0], ["Hidden body.", 0], ["The footnote definition text.", 0], ["marked text", 0], ["alias", 0], ["Note#Heading", 0],
      ["title: Test Note", 0], ["Title", 0], ["Note", 1],
    ];
    const spans: Array<[string, string]> = [["Inline ", "math and"], ["footnote ref", " here"], ["Para after front", "Heading One"]];
    const r = await page.evaluate(mapInPage, { needles, spans, source: FIX });   // the function itself is what the page runs (a reference from an arrow would not travel)
    assert.equal(r.children, 21); assert.equal(r.blocks, 21, "as many blocks as top-level elements");
    assert.deepEqual(r.owners, Array.from({ length: 21 }, (_, i) => i), "element i is block i (the 1:1 pairing over the real DOM)");
    const m = r.map as Record<string, any>;
    for (const s of ["Para after front", "Para after footnote", "Para after url-only", "Para after callout", "Para after folded", "Para after display", "Last para.", "Callout body line.", "Hidden body.", "The footnote definition text.", "marked text"]) {
      assert.equal(m[s + "#0"].ok, true, s + ": " + JSON.stringify(m[s + "#0"]));
      assert.deepEqual(m[s + "#0"].range, { start: at(s), end: at(s) + s.length }, s);
      assert.equal(m[s + "#0"].quote, s);
    }
    assert.deepEqual(m["alias#0"].range, { start: at("|alias") + 1, end: at("|alias") + 6 }, "the alias of [[Note|alias]] maps at its own offset");
    assert.equal(m["Note#Heading#0"].range.start, at("[[Note#Heading]]") + 2);
    assert.equal(m["Inline ...math and"].ok, true, JSON.stringify(m["Inline ...math and"]));
    assert.equal(m["Inline ...math and"].quote, "Inline $x^2$ math and", "a selection across the rendered formula quotes the TeX between: the .katex root is skipped and the token is a zero-text hole");
    assert.equal(m["Para after front...Heading One"].quote, FIX.slice(at("Para after front matter."), at("# Heading One") + "# Heading One".length));
    assert.equal(m["title: Test Note#0"].ok, false); assert.match(m["title: Test Note#0"].reason, /the front matter/);
    assert.equal(m["Title#0"].ok, false); assert.match(m["Title#0"].reason, /a callout's title/);
    assert.equal(m["Note#1"].ok, false); assert.match(m["Note#1"].reason, /a callout's title/, "the generated title of the GitHub alert");
    assert.equal(m["footnote ref... here"].ok, false); assert.match(m["footnote ref... here"].reason, /a footnote reference/);
    for (const k of Object.keys(m)) if (m[k].ok === false) assert.doesNotMatch(m[k].reason, /frontMatter|footnoteRef|callout'?s? title\b.*token|mathInline|wikilink/, "no token name in a refusal: " + m[k].reason);

    assert.deepEqual(errors, [], "no page errors");
    await page.context().close();
  });
});

test("the feed page renders the fixture's math as KaTeX under feed.css built as the webview build builds it (the KaTeX sheet inlined), and the same constructs", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const css = await builtFeedCss();
    assert.ok(css.includes(".katex-html") && !css.includes('@import "katex'), "the built feed sheet carries KaTeX's classes inline");
    const { page, errors } = await openFixture(browser, "feed", feedBundle(), FEED_HTML(css), { width: 900, height: 700 });
    const f = await page.evaluate(() => {
      const md = document.querySelector("#romp-fileview .fileview-md") as HTMLElement;
      const katex = md.querySelector(".katex") as HTMLElement | null;
      return {
        katex: md.querySelectorAll(".katex").length, display: md.querySelectorAll(":scope > .katex-display").length, placeholders: md.querySelectorAll(".md-math-inline, .md-math-display").length,
        font: katex ? getComputedStyle(katex).fontFamily : null, displayH: (md.querySelector(".katex-display") as HTMLElement | null)?.getBoundingClientRect().height || 0,
        overflow: getComputedStyle(md.querySelector(".katex-display")!).overflowX,
        frontMatter: md.firstElementChild?.matches("details.md-frontmatter"), callouts: md.querySelectorAll(".md-callout").length, footnotes: md.querySelectorAll(".md-footnote").length, marks: md.querySelectorAll("mark").length,
      };
    });
    assert.deepEqual([f.katex, f.display, f.placeholders], [2, 1, 0], JSON.stringify(f));
    assert.match(f.font || "", /KaTeX_Main/, "KaTeX's own face is what the sheet asks for: the feed page has the layout CSS now (it had none before this slice)");
    assert.ok(f.displayH > 20, "the display sum has KaTeX's height under the feed sheet: " + f.displayH);
    assert.equal(f.overflow, "auto", "the .katex-display twin in feed.css applies");
    assert.deepEqual([f.frontMatter, f.callouts, f.footnotes, f.marks], [true, 3, 2, 1]);
    assert.deepEqual(errors, [], "no page errors on the feed page");
    await page.context().close();
  });
});
