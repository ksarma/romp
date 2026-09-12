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
// definition maps its words. Read with real KaTeX glyph nodes and with real mouse gestures. Third (the review's round 2), the
// highlight a comment across a formula paints: paintRendered wrapped the text nodes either side of the `.katex` root and nothing
// else, so the passage `Inline $x^2$ math and` showed two ringed boxes with the rendered formula bare between them; now the
// formula goes under one mark with the words beside it, and the panel's unpaint gives the paragraph back. The dress that mark
// wears is read too (the review's round 3): the panel's classes are single-class rules (.fc-hl, .fc-presel, .fc-ins, .fc-del),
// and the slice's `==mark==` construct rule (`.fileview-md mark`, one class and a type) outranked them inside the viewer, so a
// comment highlight painted as the construct's 35% amber wash with its padding and corners, the composer's pending target lost
// its accent wash and an insertion's tint went amber, while the assertion here read only that SOME wash was painted and passed
// either way. Now each element the panel paints in this view is compared, computed wash, padding, corner radius and ring, with
// the same element outside any markdown surface (its own rule alone, the reference md-config-chat-styles-browser.test.ts reads
// for mark.cmt-hl) and with the fixture's own `==marked text==` beside it, which it must not match. Skips LOUDLY without a
// playwright browser (CI installs none), as the other browser legs do. Synthetic values only: an invented note, TESTHOST
// paths, a placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { MATH_TEX_MAX_CHARS } from "./math";
import { inBrowser as inRealViewer, openViewer, openPanel, frames as viewerFrames, REPORT as VIEWER_REPORT, type Mode } from "./real-viewer-leg";

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
/** A paragraph that opens with a formula, and one that ends in one (the Slice 5 review's round 2: a formula covered whole). */
const FIRST_NOTE = "# Title\n\n$E = mc^2$ opens this paragraph with prose after it.\n\nPara after, ending in $a+b$\n\nLast para.\n";
const DOCS: Record<string, string> = {
  [DIR + "fallbacks.md"]: FALLBACKS,
  [DIR + "report.md"]: OBSIDIAN,
  [DIR + "first.md"]: FIRST_NOTE,
  [DIR + "place-broken.md"]: PLACE_NOTE("\\frac{a}{b"),
  [DIR + "place-huge.md"]: PLACE_NOTE(HUGE),
  [DIR + "place-fine.md"]: PLACE_NOTE("\\sum_i i"),
};

const BUILD = { bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
  nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent" };
/** The Files pane's bundle plus the anchor map's and the reader's place's exports, one module instance, for the reads over the page's own box. */
function filesBundle(): string {
  const contents = 'import "./files";\nimport { mapRenderedSelection, sourceBlockSpans, renderedBlockIndex, paintRendered, paintRenderedPoint, unpaintChanges } from "./anchor-map";\nimport { readPlace } from "./reader-place";\n(window as any).__rompProbe = { mapRenderedSelection, sourceBlockSpans, renderedBlockIndex, paintRendered, paintRenderedPoint, unpaintChanges, readPlace };\n';
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
  return { text: s.toString(), anchor: where(s.anchorNode), anchorOffset: s.anchorOffset, anchorIsText: !!s.anchorNode && s.anchorNode.nodeType === 3, focus: where(s.focusNode), result: probe.mapRenderedSelection(s, md, source) as MapOut };
}
/** The highlight over `Inline $x^2$ math and`, painted as the panel paints a comment's (paintRendered with the panel's class and
 *  data) over a real selection made across the formula: the marks, their children, their boxes and the dress each wears (the
 *  computed wash, padding, corner radius and ring); the map over the painted paragraph; then the panel's unpaint
 *  (file-comments.ts unpaint(".fc-hl, .fc-presel"): its own marks by class, every child back in its place, the parent normalized)
 *  and the paragraph after it; then the ranges a comment made in the Raw view carries (the formula at an edge, the formula alone).
 *  The dress is read for every element the panel paints in this view: the highlight above, the composer's pending target
 *  (fc-presel, the first Raw-made range), an insertion's tint (fc-ins) and a deletion's point (fc-del, a span) over a plain
 *  paragraph, given back by unpaintChanges as the panel gives them back; beside two references on the same page, the fixture's
 *  own `==marked text==` (the construct's dress) and the same four elements outside any markdown surface (each class's own rule
 *  alone). */
function readPaint(source: string) {
  const probe = (window as any).__rompProbe;
  const md = document.querySelector("#romp-fileview .fileview-md") as HTMLElement;
  const p = (Array.from(md.querySelectorAll(":scope > p")) as HTMLElement[]).find((x) => (x.textContent || "").startsWith("Inline "))!;
  const texts = (root: Node): Text[] => { const out: Text[] = []; const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT); for (let n = w.nextNode(); n; n = w.nextNode()) out.push(n as Text); return out; };
  const shape = (n: Node): string[] => Array.from(n.childNodes).map((c) => c.nodeType === 3 ? "#text(" + (c as Text).data + ")" : (c as Element).tagName + "." + String((c as Element).className).split(" ")[0]);
  const box = (el: Element) => { const b = el.getBoundingClientRect(); return { left: Math.round(b.left), right: Math.round(b.right), top: Math.round(b.top), width: Math.round(b.width), height: Math.round(b.height) }; };
  const dress = (el: Element | null) => { if (!el) return null; const cs = getComputedStyle(el); return { bg: cs.backgroundColor, padding: cs.padding, radius: cs.borderRadius, shadow: cs.boxShadow }; };
  // the panel's own unpaint: its marks by class (never every mark, which would take the fixture's ==marked text== with them)
  const unpaint = () => { for (const m of Array.from(md.querySelectorAll("mark.fc-hl, mark.fc-presel"))) { const par = m.parentNode!; while (m.firstChild) par.insertBefore(m.firstChild, m); par.removeChild(m); par.normalize(); } };
  // the construct's mark, as the fixture renders it (whatever class the renderer gives it; never one of the panel's)
  const construct = (Array.from(md.querySelectorAll("mark")) as HTMLElement[]).find((x) => x.textContent === "marked text" && !/(^|\s)fc-/.test(x.className)) || null;
  const mapAcross = (): MapOut => {
    const first = texts(p).find((t) => t.data.startsWith("Inline"))!, last = texts(p).find((t) => t.data.includes(" math and"))!;
    const s = window.getSelection()!; s.removeAllRanges();
    const r = document.createRange(); r.setStart(first, 0); r.setEnd(last, last.data.indexOf(" math and") + " math and".length); s.addRange(r);
    const m = probe.mapRenderedSelection(s, md, source); s.removeAllRanges(); return m;
  };
  const katex = p.querySelector(".katex") as HTMLElement;
  const katexBefore = box(katex);
  const mapped = mapAcross();
  const marks = (probe.paintRendered(md, source, mapped.range, "fc-hl", { act: "fcopen", id: "c6" }) || []) as HTMLElement[];
  const across = {
    marks: marks.map((m) => ({ shape: shape(m), box: box(m), act: m.dataset.act, id: m.dataset.id, dress: dress(m) })),
    paragraph: shape(p), katexInMark: !!marks.length && katex.closest(".fc-hl") === marks[0], katexBox: box(katex), katexBefore,
    mappedPainted: mapAcross(),
  };
  unpaint();
  const after = { paragraph: shape(p), mapped: mapAcross(), katexBox: box(katex) };
  const raw: Record<string, string[][]> = {};
  let presel: ReturnType<typeof dress> = null;
  for (const text of ["$x^2$ math and", "Inline $x^2$", "$x^2$"]) {
    const i = source.indexOf(text);
    const ms = (probe.paintRendered(md, source, { start: i, end: i + text.length }, "fc-presel") || []) as HTMLElement[];
    raw[text] = ms.map((m) => shape(m));
    if (presel === null) presel = dress(ms[0] || null);
    unpaint();
  }
  // the change marks over a plain paragraph, one at a time, each given back by unpaintChanges (the panel's own, before each repaint)
  const plain = "Para after callout.";
  const q = (Array.from(md.querySelectorAll(":scope > p")) as HTMLElement[]).find((x) => x.textContent === plain)!;
  const qi = source.indexOf(plain);
  const insMarks = (probe.paintRendered(md, source, { start: qi, end: qi + plain.length }, "fc-ins", { act: "fcchange", id: "h1" }) || []) as HTMLElement[];
  const ins = { shape: shape(q), dress: dress(insMarks[0] || null) };
  probe.unpaintChanges(md);
  const point = probe.paintRenderedPoint(md, source, qi, "fc-del", { act: "fcchange", id: "h2" }, "old words") as HTMLElement | null;
  const del = { shape: shape(q), dress: dress(point) };
  probe.unpaintChanges(md);
  const changes = { ins, del, after: shape(q) };
  // the reference: the same four elements outside any markdown surface, each class's own rule alone
  const ref = document.createElement("p");
  ref.innerHTML = 'ref <mark class="fc-hl">a</mark> <mark class="fc-presel">b</mark> <mark class="fc-ins">c</mark> <span class="fc-del" data-fc-text="old words"></span>';
  document.body.appendChild(ref);
  const refDress = { "fc-hl": dress(ref.querySelector(".fc-hl")), "fc-presel": dress(ref.querySelector(".fc-presel")), "fc-ins": dress(ref.querySelector(".fc-ins")), "fc-del": dress(ref.querySelector(".fc-del")) };
  ref.remove();
  const viewer = { "fc-hl": across.marks[0] ? across.marks[0].dress : null, "fc-presel": presel, "fc-ins": ins.dress, "fc-del": del.dress };
  return { mapped: { ok: mapped.ok, quote: mapped.quote, range: mapped.range }, across, after, raw, changes, dress: { viewer, ref: refDress, construct: dress(construct) }, final: shape(p) };
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
    for (const [what, m] of [["fromInside", e.fromInside], ["intoIt", e.intoIt], ["formulaAlone", e.formulaAlone]] as const) {
      assert.equal(m.ok, false, what);
      assert.equal(m.reason, "This selection touches a formula; comment on it from the Raw view.", what + ": " + m.reason);
      assert.equal(m.blockStartLine, formulaLine, what + ": the Raw view opens at the formula's line");
      assert.equal(m.blockStartOffset, at(src, "$x^2$"), what + ": at its first character");
    }
    // from the formula's first glyph out into the prose: the formula is covered whole, prose holding a formula, its source in the quote
    // (the Slice 5 review's round 2 ruling; before: refused as the formula)
    assert.equal(e.fromStart.ok, true, JSON.stringify(e.fromStart)); assert.equal(e.fromStart.quote, "$x^2$ math and");
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
    // a drag from the middle of the inline formula's first glyph into the prose after it: Chromium puts the caret at the superscript's
    // first glyph (probed: the left fifth of the `x` box gives the `x` at 0, the formula's first character, which covers the formula
    // whole and maps since the Slice 5 review's round 2; the middle gives the `2` at 0, strictly inside; the right fifth the `2` at 1,
    // its end, which selects none of it)
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
    assert.deepEqual([drag.result.ok, drag.result.reason], [false, "This selection touches a formula; comment on it from the Raw view."], "a drag begun strictly inside the glyphs is the formula's (anchor " + drag.anchor + " at " + drag.anchorOffset + "): " + JSON.stringify(drag.result));
    assert.equal(drag.result.blockStartLine, formulaLine);
    assert.deepEqual(errors, [], "no page errors");
    await page.context().close();
  });
});

/** The formula-first paragraph's endpoints, mapped through the probe: the triple-click's shape, a start strictly inside, a drag to
 *  the closing formula's last glyph. */
function readFirstEndpoints(source: string) {
  const probe = (window as any).__rompProbe;
  const md = document.querySelector("#romp-fileview .fileview-md") as HTMLElement;
  const texts = (root: Node): Text[] => { const out: Text[] = []; const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT); for (let n = w.nextNode(); n; n = w.nextNode()) if ((n as Text).data.length) out.push(n as Text); return out; };
  const point = (needle: string, atEnd = false): Pt => {
    for (const n of texts(md)) { const i = n.data.indexOf(needle); if (i >= 0) return { node: n, offset: atEnd ? i + needle.length : i }; }
    throw new Error("not in the rendered text: " + needle);
  };
  const map = (a: Pt, f: Pt): MapOut => probe.mapRenderedSelection({ anchorNode: a.node, anchorOffset: a.offset, focusNode: f.node, focusOffset: f.offset, isCollapsed: false }, md, source);
  const paras = Array.from(md.querySelectorAll(":scope > p")) as HTMLElement[];
  const g = texts(paras[0].querySelector(".katex")!), lg = texts(paras[1].querySelector(".katex")!);
  const last = lg[lg.length - 1];
  return {
    glyphs: g.map((t) => t.data),
    triple: map({ node: g[0], offset: 0 }, { node: paras[1], offset: 0 }),
    toWord: map({ node: g[0], offset: 0 }, point(" opens this", true)),
    inside: map({ node: g[0], offset: 1 }, point(" opens this", true)),
    toEnd: map(point("Para after"), { node: last, offset: last.data.length }),
    toInside: map(point("Para after"), { node: last, offset: Math.max(0, last.data.length - 1) }),
    afterFormula: map(point(" opens this"), { node: paras[1], offset: 0 }),
    onParagraph: map({ node: paras[0], offset: 0 }, { node: paras[1], offset: 0 }),
  };
}

test("a paragraph that opens with a formula over the real Files bundle: the triple-click's shape (the formula's first glyph to the next paragraph's start) and a range from the first glyph to a word map with the formula's source inside the quote, a range begun strictly inside the glyphs is the formula's, a drag ending at a closing formula's last glyph covers it (the Slice 5 review's round 2 ruling: a formula covered whole is prose holding a formula; before: refused as the formula, the Raw view preselecting the formula alone); and a REAL triple-click on the paragraph selects the words after the formula and maps them, the formula's source outside the quote (Chromium's paragraph selection leaves the leading inline-block out of its range: the anchor is the text node after the formula at 0; the whole-source mapping stands on the synthetic shapes)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openFile(browser, filesBundle(), DIR + "first.md", { width: 900, height: 900 });
    const src = FIRST_NOTE;
    const e = await page.evaluate(readFirstEndpoints, src);
    assert.ok(e.glyphs.length >= 2, "KaTeX laid the opening formula out as glyph text nodes: " + JSON.stringify(e.glyphs));
    assert.equal(e.triple.ok, true, "the triple-click's shape maps: " + JSON.stringify(e.triple));
    assert.equal(e.triple.quote, "$E = mc^2$ opens this paragraph with prose after it.", "the paragraph's whole source, the formula first");
    assert.equal(e.toWord.ok, true, JSON.stringify(e.toWord)); assert.equal(e.toWord.quote, "$E = mc^2$ opens this");
    assert.equal(e.onParagraph.ok, true, JSON.stringify(e.onParagraph)); assert.equal(e.onParagraph.quote, "$E = mc^2$ opens this paragraph with prose after it.", "a boundary on the paragraph before its first child covers the formula from outside it");
    assert.deepEqual([e.inside.ok, e.inside.reason], [false, "This selection touches a formula; comment on it from the Raw view."], "strictly inside: the formula's");
    assert.deepEqual(e.inside.rawRange, { start: src.indexOf("$E"), end: src.indexOf("$E") + "$E = mc^2$".length }, "the Raw offer preselects the formula");
    assert.equal(e.toEnd.ok, true, JSON.stringify(e.toEnd)); assert.equal(e.toEnd.quote, "Para after, ending in $a+b$", "the closing formula, covered whole, travels inside the quote");
    assert.deepEqual([e.toInside.ok, e.toInside.reason], [false, "This selection touches a formula; comment on it from the Raw view."], "to inside the closing formula: the formula's");
    // a selection begun on the text right after the formula does not cover it: the formula stands before the selection's start
    assert.equal(e.afterFormula.ok, true, JSON.stringify(e.afterFormula)); assert.equal(e.afterFormula.quote, "opens this paragraph with prose after it.", "the words alone, the formula outside the selection");
    // the real gesture: a triple-click on the formula-first paragraph's words. Chromium's paragraph selection leaves the leading
    // inline-block out of its range: the anchor is the text node after the formula at 0, the focus the next paragraph's start, so the
    // words alone are selected and map, the formula outside the selection and its source outside the quote (probed at ten positions
    // across the paragraph's width, the words' shape at every one past the glyphs; a click on the glyphs themselves selects the formula
    // alone, refused as the formula, which leg 6 reads). The whole-source mapping stands on the synthetic shapes above (e.triple,
    // e.onParagraph). The anchor is pinned here, as the footnote leg pins its back-link anchor, so a browser that changes the gesture's
    // shape fails this line and the records naming the shape (the plan's item 5 note, the build report) are revisited; and the quote is
    // read against what the selection covers, not derived from the anchor (the review's round 3: the assertion that stood here took the
    // formula's presence in the quote from the anchor's own description, so it accepted the words alone under a title claiming the
    // paragraph's whole source, and could not fail on the difference).
    await page.evaluate(() => window.getSelection()!.removeAllRanges());
    const b = await page.locator("#romp-fileview .fileview-md p:has(.katex)").first().boundingBox();
    await page.mouse.click(b.x + b.width * 0.7, b.y + b.height / 2, { clickCount: 3 });
    const triple = await page.evaluate(readLiveSelection, src);
    const coversFormula = await page.evaluate(() => {
      const s = window.getSelection()!;
      const katex = document.querySelector("#romp-fileview .fileview-md p .katex")!;
      return s.rangeCount > 0 && s.getRangeAt(0).intersectsNode(katex);
    });
    assert.equal(triple.text.trim(), "opens this paragraph with prose after it.", "the triple-click selected the paragraph's words, none of the formula's glyphs: " + JSON.stringify(triple.text));
    assert.deepEqual([triple.anchorIsText, triple.anchor, triple.anchorOffset], [true, "p", 0], "Chromium anchors the triple-click on the text node after the formula at 0, the leading inline-block outside its range (a different anchor is a new gesture shape: check the map's rules for it and the records that name this one): " + JSON.stringify({ anchor: triple.anchor, anchorOffset: triple.anchorOffset, anchorIsText: triple.anchorIsText, focus: triple.focus }));
    assert.equal(coversFormula, false, "the selection's range leaves the formula out: " + JSON.stringify(triple.text));
    assert.equal(triple.result.ok, true, "the formula-first paragraph maps under a triple-click (anchor " + triple.anchor + " at " + triple.anchorOffset + ", focus " + triple.focus + "): " + JSON.stringify(triple.result));
    assert.equal(triple.result.quote, "opens this paragraph with prose after it.", "the words the gesture selected, the formula's source outside the quote as the formula is outside the selection: " + JSON.stringify(triple.result));
    assert.deepEqual(errors, [], "no page errors");
    await page.context().close();
  });
});

test("a comment across an inline formula over the real Files bundle is ONE highlight holding the KaTeX root (before: two marks with the formula bare between them), the panel's own wash behind the formula and not the ==mark== construct's (every element the panel paints wears its class's dress as it does outside any markdown surface), the map unchanged over the painted paragraph, the paragraph given back by the panel's unpaint, and a Raw-made range at or on the formula highlights it", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openFile(browser, filesBundle(), DIR + "report.md", { width: 900, height: 900 });
    const src = OBSIDIAN;
    const r = await page.evaluate(readPaint, src);
    assert.equal(r.mapped.ok, true, JSON.stringify(r.mapped)); assert.equal(r.mapped.quote, "Inline $x^2$ math and");
    assert.equal(r.across.marks.length, 1, "one mark: " + JSON.stringify(r.across.marks.map((m: any) => m.shape)));
    const m = r.across.marks[0];
    assert.deepEqual(m.shape, ["#text(Inline )", "SPAN.katex", "#text( math and)"], "the formula under the mark with the words beside it");
    assert.deepEqual(r.across.paragraph, ["MARK.fc-hl", "#text( display:)"]);
    assert.deepEqual([m.act, m.id], ["fcopen", "c6"], "the panel's data on the mark: a click on the formula opens the card");
    assert.equal(r.across.katexInMark, true, "the .katex root's closest .fc-hl is the mark");
    assert.ok(m.box.left <= r.across.katexBox.left && m.box.right >= r.across.katexBox.right, "the mark's box spans the formula: " + JSON.stringify([m.box, r.across.katexBox]));
    assert.ok(Math.abs(r.across.katexBox.width - r.across.katexBefore.width) <= 1, "KaTeX's layout is unchanged under the mark: " + JSON.stringify([r.across.katexBefore, r.across.katexBox]));
    // the dress (the review's round 3): the panel's marks inside .fileview-md wear their own single-class rules, computed wash,
    // padding, corner radius and ring, as the same elements do outside any markdown surface, and the comment wash is not the
    // ==mark== construct's beside it. Before the fix the construct rule `.fileview-md mark` outranked .fc-hl, .fc-presel and .fc-ins
    // (a type and a class against a class), so the highlight here was the 35% amber wash with the construct's em padding and 2px
    // corners, identical to the fixture's `==marked text==`; the assertion that stood here read only that some wash was painted
    assert.ok(r.dress.construct, "the fixture's ==marked text== rendered as a mark in the viewer");
    assert.notEqual(r.dress.construct!.bg, "rgba(0, 0, 0, 0)", "the construct's wash is painted: " + JSON.stringify(r.dress.construct));
    assert.notEqual(r.dress.ref["fc-hl"]!.bg, "rgba(0, 0, 0, 0)", "the highlight's own rule paints a wash: " + JSON.stringify(r.dress.ref["fc-hl"]));
    assert.notEqual(r.dress.ref["fc-hl"]!.shadow, "none", "the highlight's own rule paints the ring");
    for (const cls of ["fc-hl", "fc-presel", "fc-ins", "fc-del"] as const) {
      assert.ok(r.dress.viewer[cls], cls + " was painted in the viewer");
      assert.deepEqual(r.dress.viewer[cls], r.dress.ref[cls], cls + " inside .fileview-md wears its own dress, as outside any markdown surface (viewer, reference): " + JSON.stringify([r.dress.viewer[cls], r.dress.ref[cls]]));
    }
    for (const cls of ["fc-hl", "fc-presel", "fc-ins"] as const) assert.notEqual(r.dress.viewer[cls]!.bg, r.dress.construct!.bg, cls + "'s wash is not the ==mark== construct's: " + r.dress.construct!.bg);
    assert.deepEqual([r.changes.ins.shape, r.changes.del.shape.length, r.changes.after], [["MARK.fc-ins"], 2, ["#text(Para after callout.)"]], "the insertion's tint over the plain paragraph, the deletion's point beside its text, and the paragraph given back: " + JSON.stringify(r.changes));
    assert.deepEqual(r.across.mappedPainted.range, r.mapped.range, "the map over the painted paragraph reads the same range: " + JSON.stringify(r.across.mappedPainted));
    assert.deepEqual(r.after.paragraph, ["#text(Inline )", "SPAN.katex", "#text( math and display:)"], "unpainted: the paragraph as rendered");
    assert.deepEqual(r.after.mapped.range, r.mapped.range, JSON.stringify(r.after.mapped));
    assert.deepEqual(r.raw, { "$x^2$ math and": [["SPAN.katex", "#text( math and)"]], "Inline $x^2$": [["#text(Inline )", "SPAN.katex"]], "$x^2$": [["SPAN.katex"]] }, "a Raw-made range at the formula's edge or on the formula alone highlights the formula (before: the words alone, or nothing)");
    assert.deepEqual(r.final, ["#text(Inline )", "SPAN.katex", "#text( math and display:)"]);
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

// ── Slice 5, item 3: the Raw offer at a formula preselects the formula, over the REAL viewer and the REAL Comments panel ──
// A selection that touched a formula was refused with the Raw view offered at the formula's line and nothing selected there
// (the slice's probe (c)): the map took the Raw range from the selected rendered text, and KaTeX's glyphs are not in the source,
// so the switch preselected the prose the drag ran into (`math and`) or, for a formula selected alone, nothing, the button reading
// "scrolled to the block; select the passage there", and the person had to find the formula in the Raw view themselves. Now the map answers the formula's hole (formulaExtra: rawHasQuote with the hole's span), so the button
// reads "with this passage selected", the switch preselects the formula with its delimiters and the composer quotes it, with
// Save (the owner's ruling 7: the whole formula, not the TeX between the delimiters). Read through real-viewer-leg.ts (the panel
// registered by the viewer's own module) under the Files pane's sheet and the chat modal's, with real gestures: a drag begun at
// the inline formula's left edge into the prose after it (a drag begun at the centre of a lone glyph collapses to a caret in
// Chromium, whatever the harness; probed over five formula shapes), and a triple-click on the display formula (Chromium anchors
// it on the formula's first glyph and ends it at the next paragraph's start). Each gesture runs on a fresh page.
const PRESEL_NOTE = "# Title\n\nInline $E = mc^2$ math and after.\n\n$$\n\\sum_i i\n$$\n\nPara after display.\n";
const INLINE_Q = "$E = mc^2$", DISPLAY_Q = "$$\n\\sum_i i\n$$";
const REFUSAL = "This selection touches a formula; comment on it from the Raw view.";
type ComposerState = { open: boolean; refused: string | null; rawTitle: string | null; quote: string | null; save: boolean | null; raw: boolean };
/** The composer as the panel shows it: the refusal line, the Raw button's title, the quote, whether Save is offered. */
const composerState = (page: any): Promise<ComposerState> => page.evaluate(() => {
  const box = document.querySelector(".fc-composer") as HTMLElement | null;
  if (!box || !document.contains(box) || box.getClientRects().length === 0) return { open: false, refused: null, rawTitle: null, quote: null, save: null, raw: false };
  const sw = box.querySelector('[data-act="fcraw"]') as HTMLElement | null;
  const save = box.querySelector('[data-act="fcsave"]') as HTMLButtonElement | null;
  return { open: true, refused: box.querySelector(".fc-refused")?.textContent ?? null, rawTitle: sw ? sw.title : null, quote: box.querySelector(".fc-quote")?.textContent ?? null, save: save ? !save.disabled : null, raw: !!sw };
});
/** The Raw view's preselection: the marks' text in order, and whether the first sits inside the body's box (the view scrolled to it). */
const preselRead = (page: any): Promise<{ text: string; rows: number; inView: boolean }> => page.evaluate(() => {
  const body = document.querySelector(".fileview-body") as HTMLElement;
  const marks = Array.from(body.querySelectorAll(".fc-presel")) as HTMLElement[];
  const rows = new Set(marks.map((m) => m.closest(".fv-cl")));
  const b = body.getBoundingClientRect(), r = marks.length ? marks[0].getBoundingClientRect() : null;
  return { text: marks.map((m) => m.textContent).join(""), rows: rows.size, inView: !!r && r.top >= b.top - 1 && r.bottom <= b.bottom + 1 };
});
const squash = (s: string): string => s.replace(/\s+/g, "");
/** The float's click, the refusal, the Raw switch, the preselection and the composer's quote; the box cancelled at the end. */
async function throughRaw(page: any, what: string, quote: string, rows: number): Promise<void> {
  await page.waitForFunction(() => { const f = document.querySelector(".fc-float") as HTMLElement | null; return !!f && !f.hidden; }, null, { timeout: 5000 });
  await page.click(".fc-float");
  await viewerFrames(page, 2);
  const c1 = await composerState(page);
  assert.equal(c1.open, true, what + ": the composer opens");
  assert.equal(c1.refused, REFUSAL, what + ": the refusal, as before");
  assert.equal(c1.rawTitle, "Raw view, with this passage selected", what + ": the Raw button promises the passage (before: 'Raw view, scrolled to the block; select the passage there')");
  await page.click('.fc-composer [data-act="fcraw"]');
  await page.waitForFunction(() => !!document.querySelector(".fileview-body .fv-cl"), null, { timeout: 10000 });
  await viewerFrames(page, 3);
  const p = await preselRead(page);
  assert.equal(squash(p.text), squash(quote), what + ": the Raw view preselects the formula with its delimiters (before: the prose beside it, or nothing): " + JSON.stringify(p));
  assert.equal(p.rows, rows, what + ": over the formula's rows");
  assert.equal(p.inView, true, what + ": the view scrolled to it");
  const c2 = await composerState(page);
  assert.equal(c2.refused, null, what + ": the refusal is answered");
  assert.equal(c2.raw, false, what + ": no Switch to Raw left");
  assert.equal(c2.quote, quote.replace(/\s+/g, " ").trim(), what + ": the composer quotes the formula");
  assert.equal(c2.save, true, what + ": Save is offered");
  await page.click('.fc-composer [data-act="fccancel"]');
  await viewerFrames(page, 2);
  assert.equal((await composerState(page)).open, false, what + ": Cancel closes the box");
}
/** A page of the surface with the note open and filled, the panel open. KaTeX's own sheet is added to the page: real-viewer-leg.ts
 *  drops the sheet's `@import` (no bundler resolves it in the page), where the viewer's own page carries it through styles.css,
 *  and without it KaTeX's MathML copy is laid out beside the HTML one and a drag that starts on a glyph selects nothing (probed). */
async function openPresel(browser: any, mode: Mode, width: number): Promise<{ page: any; errors: string[] }> {
  const { page, errors } = await openViewer(browser, mode, width, 900, { docs: { [VIEWER_REPORT]: PRESEL_NOTE } });
  await page.addStyleTag({ content: KATEX_CSS });
  await page.waitForFunction(() => !document.querySelector(".fileview-md .md-math-inline, .fileview-md .md-math-display"), null, { timeout: 15000 });   // the fill ran
  await viewerFrames(page, 2);
  await openPanel(page);
  return { page, errors };
}

test("Switch to Raw at a formula preselects the formula with its delimiters over the real viewer and panel, on the Files pane and in the chat modal: a real drag from inside the inline formula's glyphs into the prose, and a real triple-click on the display formula, each refused as touching a formula with the Raw button promising the passage; the Raw view opens on `$E = mc^2$` (or the `$$` block over its three rows) selected, and the composer quotes it with Save (before: the prose the drag ran into was selected, or nothing for the display formula alone)", { timeout: 240000 }, async (t) => {
  await inRealViewer(t, async (browser) => {
    for (const [mode, width] of [["pane", 900], ["chat", 1000]] as [Mode, number][]) {
      // the inline formula: a drag from inside its glyphs into the prose after it (a press at its left edge covers the formula whole
      // and maps since the Slice 5 review's round 2; the inside is the formula's)
      let { page, errors } = await openPresel(browser, mode, width);
      const kbox = await page.locator(".fileview-md p .katex").first().boundingBox();
      const to = await page.evaluate(() => {
        const md = document.querySelector(".fileview-md")!;
        const w = document.createTreeWalker(md, NodeFilter.SHOW_TEXT);
        for (let n = w.nextNode() as Text | null; n; n = w.nextNode() as Text | null) {
          const i = n.data.indexOf(" math and");
          if (i >= 0) { const r = document.createRange(); r.setStart(n, i + " math and".length); r.setEnd(n, i + " math and".length); const b = r.getBoundingClientRect(); return { x: b.x - 1, y: b.y + b.height / 2 }; }
        }
        throw new Error("no prose after the formula");
      });
      await page.mouse.move(kbox.x + kbox.width * 0.6, kbox.y + kbox.height / 2);
      await page.mouse.down();
      await page.mouse.move(to.x, to.y, { steps: 8 });
      await page.mouse.up();
      await viewerFrames(page, 2);
      const drag = await page.evaluate(() => { const s = getSelection()!; const el = s.anchorNode && (s.anchorNode.nodeType === 3 ? s.anchorNode.parentElement : s.anchorNode as Element); return { text: String(s), inKatex: !!el && !!el.closest(".katex"), atStart: !!el && !!el.closest(".katex") && s.anchorOffset === 0 && !s.anchorNode!.previousSibling && !(s.anchorNode!.parentElement as HTMLElement).previousElementSibling }; });
      assert.equal(drag.inKatex, true, mode + ": the drag anchored inside the formula: " + JSON.stringify(drag));
      await throughRaw(page, mode + " " + width + "px, inline drag", INLINE_Q, 1);
      assert.deepEqual(errors, [], mode + ": no script error");
      await page.close();
      // the display formula: a triple-click on it
      ({ page, errors } = await openPresel(browser, mode, width));
      const box = await page.locator(".fileview-md .katex-display").first().boundingBox();
      await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2, { clickCount: 3 });
      await viewerFrames(page, 2);
      const triple = await page.evaluate(() => { const s = getSelection()!; const el = s.anchorNode && (s.anchorNode.nodeType === 3 ? s.anchorNode.parentElement : s.anchorNode as Element); return { text: String(s), inDisplay: !!el && !!el.closest(".katex-display") }; });
      assert.equal(triple.inDisplay, true, mode + ": the triple-click anchored in the display formula: " + JSON.stringify(triple));
      await throughRaw(page, mode + " " + width + "px, display triple-click", DISPLAY_Q, 3);
      assert.deepEqual(errors, [], mode + ": no script error");
      await page.close();
    }
  });
});
