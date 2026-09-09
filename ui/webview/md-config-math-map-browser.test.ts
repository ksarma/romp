// The anchor map where math meets it, over the REAL Files bundle in headless Chromium (plans/markdown-viewer.md, Slice 4,
// decision 1: KaTeX in the files and feed bundles; the review of that slice). Two things the node tests stand in for are
// read here off the real fill and the real layout. First, the fill's fallback shapes (math.ts renderMathPlaceholders): a
// display formula KaTeX cannot parse renders as KaTeX's bare `span.katex-error` holding the TeX, with no `.katex` root, and
// one past MATH_TEX_MAX_CHARS as the fill's `pre > code.md-math-src`, which the viewer dresses with its Copy button; the
// inline forms the same, inside the paragraph. Each is a formula to the map (a control whose text is not the note's), so
// the block pairing stays one to one and the prose around every formula maps. Before the fix the TeX stood in the block's
// rendered text: the paragraph with an inline fallback refused as not matching the file, and a display fallback took no
// element, so every block after it paired one element early (its paragraphs refused, the last one unowned) and the
// reader's place, read through the same pairing (reader-place.ts), named the block after the one at the body's top edge:
// a Rendered to Raw switch with paragraph 20 at the top landed on paragraph 21. Second, a selection endpoint inside a
// control, which ordinary gestures produce on the new constructs: a triple-click on a footnote definition anchors on the
// back link's label, a triple-click on the paragraph before a display formula puts its focus on the formula's first
// glyph, a drag starts or ends on a formula's glyphs. The map used to answer "reaches outside the rendered text" for all of
// them, the answer for a node under another surface; now an endpoint inside a formula's glyphs is the formula touched
// ("touches a formula", the Raw view offered at the formula's line), an endpoint at a formula's edge that selects none of
// it maps the prose beside it, and an endpoint inside another control stands at the control's edge, so the triple-clicked
// definition maps its words. Read with real KaTeX glyph nodes and with real mouse gestures. Skips LOUDLY without a
// playwright browser (CI installs none), as the other browser legs do. Synthetic values only: an invented note, TESTHOST
// paths, a placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { MATH_TEX_MAX_CHARS } from "./math";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
// resolve playwright and esbuild from the extension, not from wherever this bundle was written (a single-file run lands it under TMPDIR)
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");
const KATEX_CSS = fs.readFileSync(path.join(EXT, "node_modules", "katex", "dist", "katex.min.css"), "utf8");
const STYLES = fs.readFileSync(path.join(UI, "styles.css"), "utf8").replace('@import "katex/dist/katex.min.css";', KATEX_CSS);
const PANE = fs.readFileSync(path.join(UI, "files-pane.css"), "utf8");
const OBSIDIAN = fs.readFileSync(path.join(UI, "anchor-map-fixtures", "obsidian.md"), "utf8");

const SID = "11111111-2222-3333-4444-555555555555";
const DIR = "/tmp/TESTHOST/notes-api/docs/";

const HUGE = "x".repeat(MATH_TEX_MAX_CHARS + 1);
/** Every fallback shape of the fill, display and inline, between paragraphs; a rendered formula of each kind as the control. */
const FALLBACKS = [
  "# Title", "",
  "Para before the block.", "",
  "$$", "\\frac{a}{b", "$$", "",                 // KaTeX cannot parse it: span.katex-error
  "Para after the block.", "",
  "$$", HUGE, "$$", "",                          // past the length bound: pre > code.md-math-src
  "Second para after.", "",
  "Prose before $\\frac{a}{b$ broken formula and prose after.", "",
  "Huge before $" + HUGE + "$ huge after.", "",
  "Good before $x^2$ good after.", "",
  "$$", "\\sum_i i", "$$", "",
  "Last para.", "",
].join("\n");
/** A display formula the fill cannot render (or a rendered one) over forty paragraphs, for the reader's place. */
const FILLER = (i: number) => `Filler paragraph ${i} ` + "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor ".repeat(2).trim() + ".";
const PLACE_NOTE = (tex: string) => "# Title\n\n$$\n" + tex + "\n$$\n\n" + Array.from({ length: 40 }, (_, i) => FILLER(i + 1)).join("\n\n") + "\n";
const DOCS: Record<string, string> = {
  [DIR + "fallbacks.md"]: FALLBACKS,
  [DIR + "report.md"]: OBSIDIAN,
  [DIR + "place-broken.md"]: PLACE_NOTE("\\frac{a}{b"),
  [DIR + "place-huge.md"]: PLACE_NOTE(HUGE),
  [DIR + "place-fine.md"]: PLACE_NOTE("\\sum_i i"),
};

const BUILD = { bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
  nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent" };
/** The Files pane's bundle plus the anchor map's and the reader's place's exports, one module instance, for the reads over the page's own box. */
function filesBundle(): string {
  const contents = 'import "./files";\nimport { mapRenderedSelection, sourceBlockSpans, renderedBlockIndex } from "./anchor-map";\nimport { readPlace } from "./reader-place";\n(window as any).__rompProbe = { mapRenderedSelection, sourceBlockSpans, renderedBlockIndex, readPlace };\n';
  const r = requireCjs("esbuild").buildSync({ ...BUILD, stdin: { contents, resolveDir: UI, loader: "ts", sourcefile: "files-probe.ts" } });
  return r.outputFiles[0].text;
}
const FILES_HTML = `<!DOCTYPE html><html><head><meta charset=utf-8><style>${STYLES}\n${PANE}</style></head><body class=fileview-pane>
<div id=files-empty></div>
<script>window.__posts=[];window.acquireVsCodeApi=function(){return{postMessage:function(m){window.__posts.push(m);}}};</script>
<script src=/dist/files.js></script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

async function inBrowser(t: any, body: (browser: any) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box; the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  try { await body(browser); } finally { await browser.close(); }
}

/** A page of the Files pane with `file` open through the pane's relay, the first paint awaited (two frames after the box appears). */
async function openFile(browser: any, js: string, file: string, viewport = { width: 900, height: 400 }): Promise<{ page: any; errors: string[] }> {
  const ctx = await browser.newContext({ viewport });
  const page = await ctx.newPage();
  const errors: string[] = [];
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  await ctx.route("**/*", (route: any) => {
    const u = new URL(route.request().url());
    if (u.host !== "romp.test") return route.fulfill({ status: 404, body: "" });
    if (u.pathname === "/files") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: FILES_HTML });
    if (u.pathname === "/dist/files.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
    if (u.pathname === "/file" && DOCS[u.searchParams.get("path") || ""] !== undefined) {
      return route.fulfill({ status: 200, contentType: "text/plain; charset=utf-8", headers: { "X-Romp-Mtime-Ns": "1", "X-Romp-Text-Utf8": "1" }, body: DOCS[u.searchParams.get("path") || ""] });
    }
    return route.fulfill({ status: 404, body: "" });
  });
  await page.goto("http://romp.test/files");
  await page.evaluate(([p, sid]: [string, string]) => { window.postMessage({ romp: "viewFile", path: p, sid }, "*"); }, [file, SID] as [string, string]);
  await page.waitForSelector("#romp-fileview .fileview-body .fileview-md", { timeout: 15000 });
  await page.waitForFunction(() => !document.querySelector("#romp-fileview .fileview-md .md-math-inline, #romp-fileview .fileview-md .md-math-display"), null, { timeout: 15000 });   // the fill ran
  await frames(page, 2);
  return { page, errors };
}
/** `n` animation frames: the layout's own event, never a timer. */
const frames = (page: any, n = 2): Promise<null> => page.evaluate((k: number) => new Promise<null>((r) => { const f = () => (k-- <= 0 ? r(null) : requestAnimationFrame(f)); f(); }), n);

// ── what the page runs (a function reference travels as its text, so each reads everything it needs from the document) ──

type Pt = { node: Node; offset: number };
type MapOut = { ok: boolean; range?: { start: number; end: number }; quote?: string; reason?: string; blockStartLine?: number; blockStartOffset?: number; rawHasQuote?: boolean };

/** The fill's shapes and the pairing over `source`: each top-level child's tag and class, its block, the katex-error's and the
 *  source fallback's anatomy, and the map of every `needle` (its first occurrence in the rendered text) and `span` (from the
 *  start of one text to the end of another). */
function readPairing({ source, needles, spans }: { source: string; needles: string[]; spans: Array<[string, string]> }) {
  const probe = (window as any).__rompProbe;
  const md = document.querySelector("#romp-fileview .fileview-md") as HTMLElement;
  const point = (needle: string, atEnd: boolean): Pt => {
    const walker = document.createTreeWalker(md, NodeFilter.SHOW_TEXT);
    for (let n = walker.nextNode() as Text | null; n; n = walker.nextNode() as Text | null) { const i = n.data.indexOf(needle); if (i >= 0) return { node: n, offset: atEnd ? i + needle.length : i }; }
    throw new Error("not in the rendered text: " + needle);
  };
  const sel = (a: Pt, f: Pt) => ({ anchorNode: a.node, anchorOffset: a.offset, focusNode: f.node, focusOffset: f.offset, isCollapsed: false });
  const map: Record<string, MapOut> = {};
  for (const t of needles) map[t] = probe.mapRenderedSelection(sel(point(t, false), point(t, true)), md, source);
  for (const [a, b] of spans) map[a + "..." + b] = probe.mapRenderedSelection(sel(point(a, false), point(b, true)), md, source);
  const kids = Array.from(md.children) as HTMLElement[];
  const err = md.querySelector(":scope > .katex-error") as HTMLElement | null;
  const src = md.querySelector(":scope > pre") as HTMLElement | null;
  const inlineErr = md.querySelector(":scope > p > .katex-error") as HTMLElement | null;
  const inlineSrc = md.querySelector(":scope > p > code.md-math-src") as HTMLElement | null;
  return {
    tags: kids.map((k) => k.tagName + (k.className ? "." + String(k.className).split(" ")[0] : "")),
    owners: kids.map((k) => probe.renderedBlockIndex(md, source, k)),
    blocks: probe.sourceBlockSpans(source).length,
    displayError: err ? { text: err.textContent, katexInside: err.querySelectorAll(".katex").length, hasKatexClass: err.classList.contains("katex"), title: (err.getAttribute("title") || "").slice(0, 10) } : null,
    displaySource: src ? { cls: src.className, code: src.querySelector("code")?.className, codeText: (src.querySelector("code")?.textContent || "").length, copy: src.querySelectorAll("button.code-copy").length, title: (src.getAttribute("title") || "").slice(0, 12) } : null,
    inlineError: inlineErr ? { text: inlineErr.textContent, katexInside: inlineErr.querySelectorAll(".katex").length, tag: inlineErr.tagName } : null,
    inlineSource: inlineSrc ? { textLen: (inlineSrc.textContent || "").length, parent: inlineSrc.parentElement?.tagName } : null,
    katex: md.querySelectorAll(".katex").length, placeholders: md.querySelectorAll(".md-math-inline, .md-math-display").length,
    map,
  };
}

/** Selections with an endpoint inside a control, built from the real DOM (KaTeX's glyph text nodes, the back link's label) and
 *  mapped; the two real-gesture reads (`triple`, `dragFromGlyph`, `tripleParaBeforeDisplay`) take the live selection instead. */
function readEndpoints(source: string) {
  const probe = (window as any).__rompProbe;
  const md = document.querySelector("#romp-fileview .fileview-md") as HTMLElement;
  const texts = (root: Node): Text[] => { const out: Text[] = []; const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT); for (let n = w.nextNode(); n; n = w.nextNode()) if ((n as Text).data.length) out.push(n as Text); return out; };
  const point = (needle: string, atEnd = false): Pt => {
    for (const n of texts(md)) { const i = n.data.indexOf(needle); if (i >= 0) return { node: n, offset: atEnd ? i + needle.length : i }; }
    throw new Error("not in the rendered text: " + needle);
  };
  const sel = (a: Pt, f: Pt) => ({ anchorNode: a.node, anchorOffset: a.offset, focusNode: f.node, focusOffset: f.offset, isCollapsed: false });
  const map = (a: Pt, f: Pt): MapOut => probe.mapRenderedSelection(sel(a, f), md, source);
  const paras = Array.from(md.querySelectorAll(":scope > p")) as HTMLElement[];
  const mathP = paras.find((p) => (p.textContent || "").startsWith("Inline "))!;
  const inline = mathP.querySelector(".katex") as HTMLElement;
  const display = md.querySelector(":scope > .katex-display .katex") as HTMLElement;
  const g = texts(inline), dg = texts(display);
  const first = { node: g[0], offset: 0 }, last = { node: g[g.length - 1], offset: g[g.length - 1].data.length };
  const dfirst = { node: dg[0], offset: 0 };
  const displayNext = (display.closest(".katex-display") as HTMLElement).nextElementSibling as HTMLElement;
  const def = md.querySelector(":scope > div.md-footnote") as HTMLElement;
  const label = texts(def.querySelector("a.md-fnback")!)[0];
  return {
    glyphs: g.map((t) => t.data), displayGlyphs: dg.map((t) => t.data), displayNext: (displayNext.textContent || "").slice(0, 16), label: label.data,
    fromInside: map({ node: g[0], offset: 1 }, point(" math and", true)),
    intoIt: map(point("Inline "), { node: g[0], offset: 1 }),
    formulaAlone: map(first, last),
    fromStart: map(first, point(" math and", true)),
    upToIt: map(point("Inline "), first),
    fromEnd: map(last, point("math and", true)),
    across: map(point("Inline "), point("math and", true)),
    paraBeforeDisplay: map(point("Inline "), dfirst),
    displayWhole: map(dfirst, { node: displayNext, offset: 0 }),
    displayAcross: map(point("and display:"), point("Para after display", true)),
    tripleShape: map({ node: label, offset: 0 }, { node: def.nextElementSibling as HTMLElement, offset: 0 }),
    fromLabel: map({ node: label, offset: 1 }, point("footnote definition", true)),
    labelAlone: map({ node: label, offset: 0 }, { node: label, offset: label.data.length }),
  };
}
/** The live selection, described (where each end sits) and mapped. */
function readLiveSelection(source: string) {
  const probe = (window as any).__rompProbe;
  const md = document.querySelector("#romp-fileview .fileview-md") as HTMLElement;
  const s = window.getSelection()!;
  const where = (n: Node | null): string => {
    if (!n) return "(none)";
    const el = n.nodeType === 3 ? n.parentElement : (n as Element);
    const chain: string[] = [];
    for (let e: Element | null = el; e && e !== md; e = e.parentElement) chain.push(e.tagName.toLowerCase() + (e.className ? "." + String(e.className).trim().split(/\s+/).join(".") : ""));
    return chain.join(" < ");
  };
  return { text: s.toString(), anchor: where(s.anchorNode), anchorOffset: s.anchorOffset, focus: where(s.focusNode), result: probe.mapRenderedSelection(s, md, source) as MapOut };
}
/** The reader's place at the body's top edge: readPlace's start, and the top-visible block (Rendered) or row (Raw) and its offset from the edge. */
function readTop(source: string) {
  const probe = (window as any).__rompProbe;
  const body = document.querySelector("#romp-fileview .fileview-body") as HTMLElement;
  const br = body.getBoundingClientRect();
  const md = document.querySelector("#romp-fileview .fileview-md");
  const els = Array.from(body.querySelectorAll(md ? ".fileview-md > *" : "code.hljs .fv-cl")) as HTMLElement[];
  let top: { text: string; top: number } | null = null;
  for (const e of els) { const r = e.getBoundingClientRect(); if (r.bottom > br.top + 0.5) { top = { text: (e.textContent || "").trim().slice(0, 19).trim(), top: Math.round((r.top - br.top) * 10) / 10 }; break; } }
  const place = md ? probe.readPlace(body, source) : null;
  return { view: md ? "rendered" : "raw", top, placeStart: place ? place.start : null, scrollTop: body.scrollTop };
}
/** Scroll the body so the top-level block whose text starts with `text` sits at the body's top edge. */
function putAtTop(text: string) {
  const body = document.querySelector("#romp-fileview .fileview-body") as HTMLElement;
  const k = (Array.from(body.querySelectorAll(".fileview-md > *")) as HTMLElement[]).find((e) => (e.textContent || "").indexOf(text) === 0)!;
  body.scrollTop += k.getBoundingClientRect().top - body.getBoundingClientRect().top;
}

const at = (src: string, s: string): number => { const i = src.indexOf(s); assert.ok(i >= 0, "in the fixture: " + s.slice(0, 30)); return i; };
const okAt = (m: MapOut, src: string, text: string, what: string) => {
  assert.equal(m.ok, true, what + ": " + JSON.stringify(m));
  assert.deepEqual(m.range, { start: at(src, text), end: at(src, text) + text.length }, what);
};

test("the fill's fallback shapes over the real Files bundle (KaTeX's flag on TeX it cannot parse, the source past the length bound, display and inline) pair one block to one element and the prose around every formula maps", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openFile(browser, filesBundle(), DIR + "fallbacks.md");
    const needles = ["Para before the block.", "Para after the block.", "Second para after.", "Prose before", "broken formula and prose after", "Huge before", "huge after", "Good before", "good after", "Last para."];
    const r = await page.evaluate(readPairing, { source: FALLBACKS, needles, spans: [["Prose before", "broken formula"], ["Good before", "good after"], ["Second para", "Prose before"]] as Array<[string, string]> });
    // the real shapes, which anchor-map-obsidian.test.ts's stand-in fill mirrors: a bare span.katex-error with the TeX as text and no
    // .katex root; a pre with the fill's code.md-math-src and the viewer's Copy button; the inline forms inside their paragraphs
    assert.deepEqual(r.tags, ["H1", "P", "SPAN.katex-error", "P", "PRE.has-copy", "P", "P", "P", "P", "SPAN.katex-display", "P"], JSON.stringify(r.tags));
    assert.deepEqual(r.displayError, { text: "\\frac{a}{b", katexInside: 0, hasKatexClass: false, title: "ParseError" });
    assert.deepEqual(r.displaySource, { cls: "has-copy", code: "md-math-src", codeText: HUGE.length, copy: 1, title: "Not rendered" });
    assert.deepEqual(r.inlineError, { text: "\\frac{a}{b", katexInside: 0, tag: "SPAN" });
    assert.deepEqual(r.inlineSource, { textLen: HUGE.length, parent: "P" });
    assert.deepEqual([r.katex, r.placeholders], [2, 0], "the two formulas KaTeX could render, no placeholder left");
    // the pairing: element i is block i, the fallback elements included (before the fix: owners [0, 1, 3, 4, 5, 6, 7, 8, 9, 10, -1])
    assert.equal(r.blocks, 11);
    assert.deepEqual(r.owners, Array.from({ length: 11 }, (_, i) => i), "element i is block i: " + JSON.stringify(r.owners));
    // every paragraph maps to its own offsets, and the prose on both sides of an inline fallback (before the fix: every one after
    // the first display fallback refused as not matching the file, the last as unmatched; the fallback paragraphs refused whole)
    for (const n of needles) okAt(r.map[n], FALLBACKS, n, n);
    assert.equal(r.map["Prose before...broken formula"].quote, "Prose before $\\frac{a}{b$ broken formula", "a selection across the flagged formula quotes the TeX between");
    assert.equal(r.map["Good before...good after"].quote, "Good before $x^2$ good after");
    assert.equal(r.map["Second para...Prose before"].quote, "Second para after.\n\nProse before", "across the blank line between two blocks");
    assert.deepEqual(errors, [], "no page errors");
    await page.context().close();
  });
});

test("a selection endpoint inside a control over the real DOM: inside a formula's glyphs it is the formula touched (the Raw view offered at the formula), at the formula's edge selecting none of it the prose beside maps, inside a back link's label the definition maps; the same under real mouse gestures", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openFile(browser, filesBundle(), DIR + "report.md", { width: 900, height: 900 });
    const src = OBSIDIAN;
    const e = await page.evaluate(readEndpoints, src);
    assert.ok(e.glyphs.length >= 2 && e.glyphs.join("") === "x2", "KaTeX laid out x^2 as glyph text nodes: " + JSON.stringify(e.glyphs));
    assert.ok(e.displayGlyphs.length >= 2, "the display sum has glyph text nodes: " + JSON.stringify(e.displayGlyphs));
    assert.equal(e.displayNext, "Para after displ"); assert.equal(e.label, "1");
    const formulaLine = (src.slice(0, at(src, "$x^2$")).match(/\n/g) || []).length;
    const displayLine = (src.slice(0, at(src, "$$\n\\sum")).match(/\n/g) || []).length;
    // inside the glyphs: the formula touched, the Raw offer at the formula's first character
    for (const [what, m] of [["fromInside", e.fromInside], ["intoIt", e.intoIt], ["formulaAlone", e.formulaAlone], ["fromStart", e.fromStart]] as const) {
      assert.equal(m.ok, false, what);
      assert.equal(m.reason, "This selection touches a formula; comment on it from the Raw view.", what + ": " + m.reason);
      assert.equal(m.blockStartLine, formulaLine, what + ": the Raw view opens at the formula's line");
      assert.equal(m.blockStartOffset, at(src, "$x^2$"), what + ": at its first character");
    }
    // the edge that selects none of the formula maps the prose beside it
    assert.equal(e.upToIt.ok, true, JSON.stringify(e.upToIt)); assert.equal(e.upToIt.quote, "Inline");
    assert.equal(e.fromEnd.ok, true, JSON.stringify(e.fromEnd)); assert.equal(e.fromEnd.quote, "math and");
    assert.equal(e.across.quote, "Inline $x^2$ math and", "across the formula, as before");
    // the display formula: the paragraph before it selected to its first glyph maps the paragraph; the formula selected whole names it
    assert.equal(e.paraBeforeDisplay.ok, true, JSON.stringify(e.paraBeforeDisplay)); assert.equal(e.paraBeforeDisplay.quote, "Inline $x^2$ math and display:");
    assert.equal(e.displayWhole.ok, false); assert.equal(e.displayWhole.reason, "This selection touches a formula; comment on it from the Raw view.");
    assert.deepEqual([e.displayWhole.blockStartLine, e.displayWhole.blockStartOffset], [displayLine, at(src, "$$\n\\sum")], "the Raw view opens at the `$$` line");
    assert.equal(e.displayAcross.ok, true, JSON.stringify(e.displayAcross));
    assert.equal(e.displayAcross.quote, src.slice(at(src, "and display:"), at(src, "Para after display") + "Para after display".length), "prose to prose across the display formula still maps");
    // the back link: the triple-click's shape maps the definition's words; a drag from the label into the words maps them; the label alone is no text
    assert.equal(e.tripleShape.ok, true, JSON.stringify(e.tripleShape)); assert.equal(e.tripleShape.quote, "The footnote definition text.");
    assert.equal(e.fromLabel.ok, true, JSON.stringify(e.fromLabel)); assert.equal(e.fromLabel.quote, "The footnote definition");
    assert.deepEqual([e.labelAlone.ok, e.labelAlone.reason], [false, "Select some text to comment on."]);
    for (const m of Object.values(e)) if (m && typeof m === "object" && "ok" in m && !(m as MapOut).ok) assert.doesNotMatch((m as MapOut).reason || "", /reaches outside/, "no endpoint here is outside the rendered text: " + JSON.stringify(m));

    // real gestures. A triple-click on the first footnote definition (Chromium anchors it on the back link's label)
    const clear = () => page.evaluate(() => window.getSelection()!.removeAllRanges());
    const center = async (sel: string) => { const b = await page.locator(sel).first().boundingBox(); return { x: b.x + b.width / 2, y: b.y + b.height / 2 }; };
    await clear();
    let c = await center("#romp-fileview .fileview-md div.md-footnote");
    await page.mouse.click(c.x, c.y, { clickCount: 3 });
    const triple = await page.evaluate(readLiveSelection, src);
    assert.ok(triple.text.startsWith("1 The footnote definition text."), "the triple-click selected the definition's line from the label: " + JSON.stringify(triple.text));
    assert.match(triple.anchor, /md-fnback/, "Chromium anchors the triple-click on the back link's label: " + triple.anchor);
    assert.equal(triple.result.ok, true, "the triple-clicked definition maps: " + JSON.stringify(triple.result));
    assert.equal(triple.result.quote, "The footnote definition text.");
    // a triple-click on the paragraph before the display formula: Chromium's focus lands on the display formula's first glyph (and its
    // anchor after the inline formula, an inline-block it takes for a paragraph edge, so the selection reads " math and display:"); the
    // words it selected map, whatever the gesture's edges
    await clear();
    c = await center("#romp-fileview .fileview-md p:has(.katex)");
    await page.mouse.click(c.x, c.y, { clickCount: 3 });
    const tripleBefore = await page.evaluate(readLiveSelection, src);
    assert.ok(tripleBefore.text.includes("math and display:"), JSON.stringify(tripleBefore.text));
    assert.equal(tripleBefore.result.ok, true, "the paragraph before the display formula maps under a triple-click (anchor " + tripleBefore.anchor + ", focus " + tripleBefore.focus + "): " + JSON.stringify(tripleBefore.result));
    assert.equal(tripleBefore.result.quote, tripleBefore.text.trim(), "the words the gesture selected (focus " + tripleBefore.focus + ")");
    // a drag from the inline formula's first glyph into the prose after it
    await clear();
    const glyph = await page.locator("#romp-fileview .fileview-md p .katex .mord").first().boundingBox();
    const to = await page.evaluate(() => {
      const md = document.querySelector("#romp-fileview .fileview-md")!;
      const w = document.createTreeWalker(md, NodeFilter.SHOW_TEXT);
      for (let n = w.nextNode() as Text | null; n; n = w.nextNode() as Text | null) {
        const i = n.data.indexOf(" math and");
        if (i >= 0) { const r = document.createRange(); r.setStart(n, i + " math and".length); r.setEnd(n, i + " math and".length); const b = r.getBoundingClientRect(); return { x: b.x - 1, y: b.y + b.height / 2 }; }
      }
      throw new Error("no prose after the formula");
    });
    await page.mouse.move(glyph.x + glyph.width / 2, glyph.y + glyph.height / 2);
    await page.mouse.down();
    await page.mouse.move(to.x, to.y, { steps: 8 });
    await page.mouse.up();
    const drag = await page.evaluate(readLiveSelection, src);
    assert.match(drag.anchor, /katex/, "the drag anchored inside the formula: " + drag.anchor);
    assert.deepEqual([drag.result.ok, drag.result.reason], [false, "This selection touches a formula; comment on it from the Raw view."], JSON.stringify(drag.result));
    assert.equal(drag.result.blockStartLine, formulaLine);
    assert.deepEqual(errors, [], "no page errors");
    await page.context().close();
  });
});

test("the reader's place under a display formula the fill could not render: paragraph 20 at the body's top edge reads as paragraph 20, and the Raw view opens on it (before the fix: paragraph 21, the pairing one block off)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const js = filesBundle();
    for (const name of ["place-fine", "place-broken", "place-huge"]) {
      const src = DOCS[DIR + name + ".md"];
      const { page, errors } = await openFile(browser, js, DIR + name + ".md");
      const shape = await page.evaluate(() => { const md = document.querySelector("#romp-fileview .fileview-md")!; const k = md.children[1]; return k.tagName + "." + String(k.className).split(" ")[0]; });
      assert.equal(shape, name === "place-fine" ? "SPAN.katex-display" : name === "place-broken" ? "SPAN.katex-error" : "PRE.has-copy", name);
      await page.evaluate(putAtTop, "Filler paragraph 20 ");
      await frames(page, 2);
      const rendered = await page.evaluate(readTop, src);
      assert.equal(rendered.view, "rendered");
      assert.equal(rendered.top?.text, "Filler paragraph 20", name + ": the scene starts with paragraph 20 at the top: " + JSON.stringify(rendered));
      assert.ok(Math.abs(rendered.top!.top) <= 1, name + ": at the body's top edge");
      assert.equal(rendered.placeStart, at(src, "Filler paragraph 20 "), name + ": readPlace names paragraph 20's block (before the fix: paragraph 21's)");
      await page.locator("#romp-fileview .fileview-btn", { hasText: /^Raw$/ }).click();
      await page.waitForSelector("#romp-fileview .fileview-body code.hljs .fv-cl", { timeout: 10000 });
      await frames(page, 2);
      const raw = await page.evaluate(readTop, src);
      assert.equal(raw.view, "raw");
      assert.equal(raw.top?.text, "Filler paragraph 20", name + ": the Raw view opens on paragraph 20's row: " + JSON.stringify(raw));
      assert.deepEqual(errors, [], name + ": no page errors");
      await page.context().close();
    }
  });
});
