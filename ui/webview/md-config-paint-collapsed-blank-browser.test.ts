// The blank scenes of md-config-paint-collapsed-blank.test.ts over the REAL bundle in headless Chromium: marked with the one
// configuration (md-config.ts), the sanitizer (md-sanitize.ts) and paintRendered, the DOM built as the viewer's mdBlock builds it,
// laid out under feed.css's prose rules. The browser is the oracle (the Slice 4 review, rounds 11 and 12), read NODE BY NODE: every
// whitespace-only text node is held across the paint and measured before it and again in the painted layout (a Range over the
// node, its client rects' widths summed, the reading the painter's layout-time trim makes), and a node below the top level must
// carry a mark exactly when it has a width. The scenes are wrap-free at 800 px, so the two readings agree and the pins are stable.
// Round 12: the collapsed scenes were judged in aggregate before (some node at 0 px, no whitespace-only mark), which a scene
// holding a collapsed blank and a rendered one in one line passed with the rendered one left unpainted; test 4 holds such scenes.
// 1. A text node of zero-width format characters alone (U+FEFF, U+200B to U+200D, U+2060 to U+2064) measures 0 px wherever it
//    stands and gets no mark; round 10 painted a lone U+FEFF as the sheet's 4 px of padding around nothing under a div, a list item
//    or a paragraph. A node of U+FEFF and a space renders the space (3.89 px at this page's 14px sans-serif) and is painted.
// 2. Collapsible white space beside an inline element that renders nothing (an `<a name>` anchor, an icon `<i>`, an empty span, sup
//    or code, a `hidden` element), between it and the line's edge, measures 0 px and gets no mark; beside an atomic inline (an empty
//    `<kbd>`, a checkbox, an image) it measures its width and is painted.
// 3. Collapsible white space after a neighbour whose text ends with a space (`<b>Label: </b> <i>value</i>`) measures 0 px and gets
//    no mark; the node before a neighbour that begins with a space is the retained one, measures 3.89 px and is painted.
// 4. One line holding both: after an `<a name>` anchor at the line's start the space collapses, and the space between an inline
//    svg icon (a 16 px box) and its label renders and is painted; in a centred row of svg badges the newline between the badges
//    renders, the ones beside the row's anchor and at its edges collapse. Round 11's DOM-side reading looked past the svg and
//    skipped the rendered blank; the layout-time trim of round 12 measures it.
// Every whitespace-only mark is a rendered blank plus the padding (wider than 5 px), and the layout is unchanged box for box,
// painted, unpainted and repainted. Skips LOUDLY without a playwright browser (CI installs none). Synthetic prose, no paths.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
// resolve playwright and esbuild from the extension, not from wherever this bundle was written (a single-file run lands it under TMPDIR)
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");
const FEED = fs.readFileSync(path.join(UI, "feed.css"), "utf8");

/** marked with the viewer's grammar, the sanitizer and the paint, bundled as the webview build bundles them. */
function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: {
      contents: 'import { marked } from "marked";\nimport { applyMdConfig } from "./md-config";\nimport { sanitizeMd } from "./md-sanitize";\n'
        + 'import { paintRendered } from "./anchor-map";\napplyMdConfig();\n(window as any).__romp = { marked, sanitizeMd, paintRendered };\n',
      resolveDir: UI, loader: "ts", sourcefile: "paint-collapsed-blank-probe.ts",
    },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "*.woff2"], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
/** The sheet's rules the scenes live under: the viewer's prose root, its paragraphs, lists, quotes, tables, images, inline code,
 *  kbd (an inline-block with a border, the atomic inline of scene 2) and pre, and the highlight. */
function sheet(): string {
  const rule = (sel: string): string => {
    const m = new RegExp("\\n(" + sel.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + " \\{[^}]*\\})").exec(FEED);
    assert.ok(m, "a rule for " + sel + " in feed.css");
    return m![1];
  };
  return [".fileview-md", ".fileview-md p", ".fileview-md img", ".fileview-md ul, .fileview-md ol", ".fileview-md li", ".fileview-md blockquote",
          ".fileview-md table", ".fileview-md th, .fileview-md td", ".fileview-md :not(pre) > code", ".fileview-md kbd", ".fileview-md pre", ".fc-hl"].map(rule).join("\n");
}
const PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8><style>
body { margin: 0; padding: 0; font: 14px/1.5 sans-serif; background: #1e1e1e; color: #ccc; --fg: #ccc; --dim: #999; --accent: #9cd2ff; --accent-wash: rgba(156,210,255,0.15); --warn: #e0a030; --bg: #1e1e1e; --font-doc: sans-serif; --box-border: #555; --overlay-05: rgba(255,255,255,0.05); --kbd-bg: #1c1c1f; --kbd-border: #3d3d42; --mono: monospace; --code-bg: rgba(255,255,255,0.08); }
${sheet()}
#md { width: 800px; }</style></head><body><div class="fileview-md" id="md"></div><script src="/dist/probe.js"></script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

type Rect = { x: number; y: number; w: number; h: number };
type WsNode = { parent: string; top: boolean; text: string; w: number };
type WsAfter = { text: string; w: number; attached: boolean; marked: boolean; markText: string | null };
type Mark = { parent: string; top: boolean; text: string; wsOnly: boolean; visible: boolean; rect: Rect };
type Layout = { height: number; tops: Array<[string, number, number]>; imgs: number[] };

/** The page's own helpers: the viewer's render (mdBlock's shape: the sanitized body's children adopted), the whitespace-only text
 *  nodes measured and HELD (ASCII white space, the Unicode spaces and the zero-width format characters all count as blank; the
 *  width is the node's client rects summed, the trim's reading), a layout read, the paint with each mark measured (one call,
 *  trimmed as the panel's paint pass is), the held nodes read again in the painted layout (still in the document, the mark that
 *  holds each, its width now), a paint of one character alone, and the panel's unpaint (file-comments.ts unpaint: the mark's
 *  children back in place, the parent normalized). */
const HELPERS = `
const BLANK = /^[\\s\\u200b-\\u200d\\u2060-\\u2064\\ufeff]*$/;
const PAINT_OPTS = { trim: true };
const width = (t) => { const r = document.createRange(); r.selectNodeContents(t); let w = 0; for (const b of Array.from(r.getClientRects())) w += b.width; return Math.round(w * 100) / 100; };
window.__render = (src) => { const md = document.getElementById("md"); md.replaceChildren(...Array.from(window.__romp.sanitizeMd(window.__romp.marked.parse(src)).childNodes)); return md.innerHTML; };
window.__wsNodes = () => { const md = document.getElementById("md"); const out = []; const held = []; const w = document.createTreeWalker(md, NodeFilter.SHOW_TEXT);
  for (let t = w.nextNode(); t; t = w.nextNode()) { if (!BLANK.test(t.data)) continue; held.push(t);
    out.push({ parent: t.parentNode.tagName, top: t.parentNode === md, text: t.data, w: width(t) }); }
  window.__held = held; return out; };
window.__wsAfter = () => { const md = document.getElementById("md"); return window.__held.map((t) => { const mark = t.parentNode && t.parentNode.closest ? t.parentNode.closest("mark") : null;
  return { text: t.data, w: width(t), attached: md.contains(t), marked: !!mark, markText: mark ? mark.textContent : null }; }); };
window.__layout = () => { const md = document.getElementById("md"); const r = md.getBoundingClientRect();
  const tops = Array.from(md.children).map((c) => { const b = c.getBoundingClientRect(); return [c.tagName, Math.round(b.top * 100) / 100, Math.round(b.height * 100) / 100]; });
  const imgs = Array.from(md.querySelectorAll("img")).map((i) => { const b = i.getBoundingClientRect(); return Math.round(b.y * 100) / 100; });
  return { height: Math.round(r.height * 100) / 100, tops, imgs }; };
window.__paint = (src) => { const md = document.getElementById("md");
  const range = { start: src.indexOf("Intro para."), end: src.indexOf("After para.") + "After para.".length };
  const marks = window.__romp.paintRendered(md, src, range, "fc-hl", { id: "c1" }, PAINT_OPTS) || [];
  return marks.map((m) => { const b = m.getBoundingClientRect(); return { parent: m.parentElement.tagName, top: m.parentElement === md, text: m.textContent, wsOnly: BLANK.test(m.textContent), visible: m.checkVisibility(),
    rect: { x: Math.round(b.x * 100) / 100, y: Math.round(b.y * 100) / 100, w: Math.round(b.width * 100) / 100, h: Math.round(b.height * 100) / 100 } }; }); };
window.__paintAt = (src, ch) => { const md = document.getElementById("md"); const at = src.indexOf(ch);
  const marks = window.__romp.paintRendered(md, src, { start: at, end: at + 1 }, "fc-hl", { id: "c2" }, PAINT_OPTS); return { at, marks: marks === null ? null : marks.length }; };
window.__unpaint = () => { for (const n of Array.from(document.querySelectorAll("#md mark"))) { const p = n.parentNode; while (n.firstChild) p.insertBefore(n.firstChild, n); p.removeChild(n); p.normalize(); } };
`;

async function inBrowser(t: any, body: (page: any) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright chromium on this box; this leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [];
  try {
    const js = bundle() + "\n" + HELPERS;
    const page = await browser.newPage({ viewport: { width: 1100, height: 900 } });
    page.on("pageerror", (e: Error) => errors.push(String(e.message || e)));
    await page.route("http://romp.test/**", (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/page") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE });
      if (u.pathname === "/dist/probe.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/page");
    await page.waitForFunction(() => !!(window as any).__romp && !!(window as any).__paint);
    await body(page);
    assert.deepEqual(errors, [], "no page errors");
  } finally { await browser.close(); }
}
const same = (a: Layout, b: Layout, what: string): void => {
  assert.equal(b.height, a.height, what + ": the prose root keeps its height");
  assert.deepEqual(b.tops, a.tops, what + ": every top-level block where it stood, at its height");
  assert.deepEqual(b.imgs, a.imgs, what + ": every image on its line (a mark's 2 px of padding on either side moves what follows it on the line, as any highlight does; a new line would move it down)");
};
/** The oracle, node by node: every whitespace-only text node held across the paint is still in the document; a top-level one
 *  carries no mark (the root guard); one below the top level carries a mark exactly when it has a width, the mark holds that
 *  blank alone, and the paint changed no blank's rendering (its width before the paint and in the painted layout agree in sign:
 *  the scenes are wrap-free at 800 px). */
const oracle = (what: string, ws: WsNode[], after: WsAfter[]): void => {
  assert.equal(after.length, ws.length, what + ": every whitespace-only node read again after the paint");
  ws.forEach((n, i) => {
    const a = after[i];
    const at = what + ": " + n.parent + " " + JSON.stringify(n.text) + " (" + n.w + " px before the paint, " + a.w + " px painted, " + (a.marked ? "a mark " + JSON.stringify(a.markText) : "no mark") + ")";
    assert.ok(a.attached, at + ": the text node stands in the document after the paint");
    if (n.top) { assert.ok(!a.marked, at + ": a top-level blank carries no mark"); return; }
    assert.equal(a.marked, n.w > 0, at + ": a whitespace-only node below the top level carries a mark exactly when it renders with a width");
    assert.equal(a.w > 0, n.w > 0, at + ": the paint changes no blank's rendering");
    if (a.marked) assert.equal(a.markText, n.text, at + ": the mark holds the blank alone");
  });
};
/** Render, measure, paint, and hold: the marks' text is `texts`; every whitespace-only mark is visible and wider than the sheet's 4
 *  px of padding (a rendered blank under it); no mark is a top-level node; the oracle holds node by node; the layout is unchanged
 *  painted, unpainted and repainted. Returns the whitespace-only text nodes as measured before the paint and the marks. */
async function drive(page: any, what: string, src: string, texts: string[]): Promise<{ ws: WsNode[]; marks: Mark[] }> {
  await page.evaluate((s: string) => (window as any).__render(s), src);
  const ws: WsNode[] = await page.evaluate(() => (window as any).__wsNodes());
  const before: Layout = await page.evaluate(() => (window as any).__layout());
  const marks: Mark[] = await page.evaluate((s: string) => (window as any).__paint(s), src);
  const after: Layout = await page.evaluate(() => (window as any).__layout());
  const nodes: WsAfter[] = await page.evaluate(() => (window as any).__wsAfter());
  assert.deepEqual(marks.map((m) => m.text), texts, what + ": the marks' text");
  for (const m of marks) {
    assert.ok(!m.top, what + ": no mark is a top-level node: " + JSON.stringify(m.text));
    if (m.wsOnly) assert.ok(m.visible && m.rect.w > 5, what + ": a whitespace-only mark is a rendered blank plus the padding, not the padding alone: " + m.parent + " " + JSON.stringify(m.text) + " " + m.rect.w + "x" + m.rect.h);
  }
  oracle(what, ws, nodes);
  same(before, after, what + ", painted");
  await page.evaluate(() => (window as any).__unpaint());
  same(before, await page.evaluate(() => (window as any).__layout()), what + ", unpainted");
  const again: Mark[] = await page.evaluate((s: string) => (window as any).__paint(s), src);
  assert.deepEqual(again.map((m) => m.text), texts, what + ": the same marks on a repaint");
  same(before, await page.evaluate(() => (window as any).__layout()), what + ", repainted");
  await page.evaluate(() => (window as any).__unpaint());
  return { ws, marks };
}
/** A collapsed scene: every whitespace-only node below the top level measures 0 px before the paint (and there is one), and no
 *  whitespace-only mark is painted; the marks' text is pinned. drive()'s oracle has tied each node to its mark already. */
async function collapsed(page: any, why: string, src: string, texts: string[]): Promise<void> {
  const { ws, marks } = await drive(page, why, src, texts);
  const below = ws.filter((n) => !n.top);
  assert.ok(below.length >= 1 && below.every((n) => n.w === 0), why + ": every whitespace-only text node below the top level measures 0 px: " + JSON.stringify(ws));
  assert.deepEqual(marks.filter((m) => m.wsOnly), [], why + ": no whitespace-only mark");
}
/** A rendered scene: one whitespace-only mark per whitespace-only node with a width, each the blank plus the sheet's 4 px. */
async function rendered(page: any, why: string, src: string, texts: string[]): Promise<void> {
  const { ws, marks } = await drive(page, why, src, texts);
  const blanks = ws.filter((n) => !n.top && n.w > 0);
  assert.ok(blanks.length >= 1, why + ": a whitespace-only text node with a width before the paint: " + JSON.stringify(ws));
  const wsMarks = marks.filter((m) => m.wsOnly);
  assert.equal(wsMarks.length, blanks.length, why + ": one whitespace-only mark per rendered blank: " + JSON.stringify(wsMarks.map((m) => m.parent + " " + JSON.stringify(m.text) + " " + m.rect.w + "x" + m.rect.h)));
  for (const m of wsMarks) assert.ok(m.rect.w >= Math.min(...blanks.map((n) => n.w)) + 4 - 0.02, why + ": the mark is the blank plus the padding: " + m.rect.w + " over " + JSON.stringify(blanks.map((n) => n.w)));
}
/** A mixed scene: the whitespace-only nodes below the top level render as `renders` says, node by node (at least one collapsed
 *  and one rendered), and the whitespace-only marks are the rendered ones' alone, in order. */
async function mixed(page: any, why: string, src: string, texts: string[], renders: boolean[]): Promise<void> {
  const { ws, marks } = await drive(page, why, src, texts);
  const below = ws.filter((n) => !n.top);
  assert.deepEqual(below.map((n) => n.w > 0), renders, why + ": which blanks render, in order: " + JSON.stringify(below));
  assert.ok(renders.includes(true) && renders.includes(false), why + ": the scene holds a collapsed blank and a rendered one");
  assert.deepEqual(marks.filter((m) => m.wsOnly).map((m) => m.text), below.filter((n) => n.w > 0).map((n) => n.text), why + ": the whitespace-only marks are the rendered blanks'");
}
const wrap = (block: string): string => "Intro para.\n\n" + block + "\n\nAfter para.\n";
type Scene = [why: string, src: string, texts: string[]];
const NBSP = "\u00a0", FEFF = "\ufeff", ZWSP = "\u200b";
const PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==";
const IMG = (alt: string): string => '<img src="' + PNG + '" width="40" height="20" alt="' + alt + '">';
const SVG = (shape: string): string => '<svg width="16" height="16" viewBox="0 0 16 16">' + shape + "</svg>";

// ── 1. zero-width format characters ─────────────────────────────────────────────────────────────────────────────────────────
const ZERO_WIDTH: Scene[] = [
  ["a lone U+FEFF under a div beside a paragraph", wrap("<div>" + FEFF + "<p>x</p></div>"), ["Intro para.", "x", "After para."]],
  ["a lone U+FEFF in a list item", wrap("<ul><li>" + FEFF + "</li><li>two</li></ul>"), ["Intro para.", "two", "After para."]],
  ["a lone U+FEFF in a paragraph", wrap("<p>" + FEFF + "</p>"), ["Intro para.", "After para."]],
  ["a U+FEFF between two inline elements of a paragraph", wrap("<p><b>a</b>" + FEFF + "<i>b</i></p>"), ["Intro para.", "a", "b", "After para."]],
  ["a lone U+200B in a list item", wrap("<ul><li>" + ZWSP + "</li><li>two</li></ul>"), ["Intro para.", "two", "After para."]],
  ...["\u200b", "\u200c", "\u200d", "\u2060", "\u2061", "\u2062", "\u2063", "\u2064"].map((ch): Scene => ["a lone U+" + ch.codePointAt(0)!.toString(16) + " in a paragraph", wrap("<p>" + ch + "</p>"), ["Intro para.", "After para."]]),
];
const ZERO_WIDTH_RENDERED: Scene[] = [
  ["a node of U+FEFF and a space between two inline children of an item", wrap("<ul><li><b>a</b>" + FEFF + " <i>b</i></li></ul>"), ["Intro para.", "a", FEFF + " ", "b", "After para."]],
  ["a neighbour ending in a space then U+FEFF: the character breaks the run, the node's space renders", wrap("<ul><li><b>a " + FEFF + "</b> <i>b</i></li></ul>"), ["Intro para.", "a " + FEFF, " ", "b", "After para."]],
  ["a nbsp alone in a paragraph (the control)", wrap("<p>&nbsp;</p>"), ["Intro para.", NBSP, "After para."]],
];

test("a text node of zero-width format characters alone measures 0 px and gets no mark under a div, a list item or a paragraph; a node of U+FEFF and a space, or a space after a neighbour ending in one, renders the space and is painted", async (t) => {
  await inBrowser(t, async (page) => {
    for (const [why, src, texts] of ZERO_WIDTH) await collapsed(page, why, src, texts);
    for (const [why, src, texts] of ZERO_WIDTH_RENDERED) await rendered(page, why, src, texts);
    for (const [why, ch] of [["U+200B", ZWSP], ["U+FEFF", FEFF]] as Array<[string, string]>) {
      const src = wrap("<p>" + ch + "</p>");
      await page.evaluate((s: string) => (window as any).__render(s), src);
      const r = await page.evaluate(([s, c]: [string, string]) => (window as any).__paintAt(s, c), [src, ch]);
      assert.ok(r.at > 0, why + ": the source holds the character");
      assert.equal(r.marks, null, why + " alone as the passage: no highlight (the comment keeps its card)");
    }
  });
});

// ── 2. an inline element that renders nothing, between the node and the line's edge ─────────────────────────────────────────
const EMPTY_INLINE: Scene[] = [
  ["an anchor-led markdown item", wrap('- <a name="install"></a> **Install** the package'), ["Intro para.", "Install", " the package", "After para."]],
  ["an icon-led html item", wrap('<ul><li><i class="fa fa-check"></i> <b>Item</b> text</li></ul>'), ["Intro para.", "Item", " text", "After para."]],
  ["an id-anchor-led div", wrap('<div><a id="sec"></a> <b>Section</b> text</div>'), ["Intro para.", "Section", " text", "After para."]],
  ["an anchor-led html blockquote", wrap('<blockquote><a name="q"></a> <b>quote</b> text</blockquote>'), ["Intro para.", "quote", " text", "After para."]],
  ["an empty span leading an item", wrap('<ul><li><span></span> <a href="#x">Link</a></li></ul>'), ["Intro para.", "Link", "After para."]],
  ["an empty sup leading an item", wrap("<ul><li><sup></sup> <b>x</b></li></ul>"), ["Intro para.", "x", "After para."]],
  ["an empty code span leading an item", wrap("<ul><li><code></code> <b>x</b></li></ul>"), ["Intro para.", "x", "After para."]],
  ["a hidden span leading an item", wrap("<ul><li><span hidden>h</span> <b>x</b></li></ul>"), ["Intro para.", "h", "x", "After para."]],
  ["an anchor closing an item", wrap('<ul><li><b>a</b> <a name="end"></a></li></ul>'), ["Intro para.", "a", "After para."]],
  ["an empty anchor nested in a bold", wrap('<ul><li><b><a name="x"></a></b> <i>y</i></li></ul>'), ["Intro para.", "y", "After para."]],
  ["an empty link then an image", wrap('<ul><li><a href="#x"></a> ' + IMG("a") + "</li></ul>"), ["Intro para.", "After para."]],
  ["an anchor-led table cell", wrap('<table><tr><td><a name="c"></a> <b>x</b></td></tr></table>'), ["Intro para.", "x", "After para."]],
  ["an anchor-led paragraph", wrap('<p><a name="p"></a> <b>para</b> text</p>'), ["Intro para.", "para", " text", "After para."]],
  ["a space leading an inline element at its paragraph's start", wrap("<p><em> <b>a</b></em> tail</p>"), ["Intro para.", "a", " tail", "After para."]],
  ["a space closing an inline element at its paragraph's end", wrap("<p>head <em><b>a</b> </em></p>"), ["Intro para.", "head ", "a", "After para."]],
  ["a block inside an inline after the space", wrap("<ul><li><b>a</b> <span><p>x</p></span></li></ul>"), ["Intro para.", "a", "x", "After para."]],
];
const EMPTY_INLINE_RENDERED: Scene[] = [
  ["an empty kbd, an inline-block with a border", wrap("<ul><li><kbd></kbd> <b>x</b></li></ul>"), ["Intro para.", " ", "x", "After para."]],
  ["a span hidden until-found", wrap('<ul><li><span hidden="until-found">h</span> <b>x</b></li></ul>'), ["Intro para.", "h", " ", "x", "After para."]],
  ["a task item's space after its checkbox", wrap("- [ ] **a** *b*"), ["Intro para.", " ", "a", " ", "b", "After para."]],
  ["a space between two inline children of an inline parent", wrap("<p><em><b>a</b> <i>b</i></em></p>"), ["Intro para.", "a", " ", "b", "After para."]],
];

test("collapsible white space beside an inline element that renders nothing, between it and the line's edge, measures 0 px and gets no mark; beside an atomic inline or a rendered element it measures its width and is painted", async (t) => {
  await inBrowser(t, async (page) => {
    for (const [why, src, texts] of EMPTY_INLINE) await collapsed(page, why, src, texts);
    // the anchor-led badge row: the newline after the anchor collapses (0 px), the one between the images renders and is painted
    const badge = wrap('<div align="center">\n<a name="top"></a>\n' + IMG("a") + "\n" + IMG("b") + "\n</div>");
    await mixed(page, "an anchor-led centred badge row: the row's leading newline, the one after the anchor and the trailing one collapse, the one between the images renders", badge, ["Intro para.", "\n", "After para."], [false, false, true, false]);
    for (const [why, src, texts] of EMPTY_INLINE_RENDERED) await rendered(page, why, src, texts);
  });
});

// ── 3. a neighbour whose text ends with collapsible white space ─────────────────────────────────────────────────────────────
const TRAILING_SPACE: Scene[] = [
  ["a bold ending with a space in an item", wrap("<ul><li><b>Label: </b> <i>value</i></li></ul>"), ["Intro para.", "Label: ", "value", "After para."]],
  ["a markdown link whose text ends with a space", wrap("- [docs ](#a) *x*"), ["Intro para.", "docs ", "x", "After para."]],
  ["a bold ending with a space, a newline between, in a div", wrap("<div><b>a </b>\n<i>b</i></div>"), ["Intro para.", "a ", "b", "After para."]],
  ["a code span ending with a space in a blockquote", wrap("<blockquote><code>x </code> <i>b</i></blockquote>"), ["Intro para.", "x ", "b", "After para."]],
  ["the trailing space nested two inlines deep", wrap("<ul><li><b><i>x </i></b> <em>y</em></li></ul>"), ["Intro para.", "x ", "y", "After para."]],
  ["a line break closing the neighbour", wrap("<ul><li><b>x<br></b> <i>y</i></li></ul>"), ["Intro para.", "x", "y", "After para."]],
  ["the trailing space read through an empty anchor between", wrap('<ul><li><b>a </b><a name="z"></a> <i>x</i></li></ul>'), ["Intro para.", "a ", "x", "After para."]],
  ["a bold ending with a space in a paragraph", wrap("<p><b>Label: </b> <i>value</i></p>"), ["Intro para.", "Label: ", "value", "After para."]],
];
const TRAILING_SPACE_RENDERED: Scene[] = [
  ["the next neighbour begins with a space: the node is the retained one", wrap("<ul><li><i>a</i> <b> b</b></li></ul>"), ["Intro para.", "a", " ", " b", "After para."]],
  ["a neighbour ending with a no-break space", wrap("<ul><li><b>a&nbsp;</b> <i>b</i></li></ul>"), ["Intro para.", "a" + NBSP, " ", "b", "After para."]],
  ["a neighbour ending with an image after its space", wrap("<ul><li><b>a " + IMG("a") + "</b> <i>x</i></li></ul>"), ["Intro para.", "a ", " ", "x", "After para."]],
  ["a kbd ending with a space is an inline-block: the space after it renders", wrap("<ul><li><kbd>Ctrl </kbd> <b>x</b></li></ul>"), ["Intro para.", "Ctrl ", " ", "x", "After para."]],
  ["under pre nothing collapses", wrap("<pre><b>a </b> <i>b</i></pre>"), ["Intro para.", "a ", " ", "b", "After para."]],
];
/** Two whitespace-only siblings in one line: the first renders, the second (after an empty span, or after the first's run-mate
 *  inside the neighbour) collapses; the marks' text names the painted one alone. */
const TWO_BLANKS: Scene[] = [
  ["a whitespace-only node inside the neighbour is the retained space; the node after the neighbour collapses", wrap("<ul><li><b>a<i> </i></b> <em>y</em></li></ul>"), ["Intro para.", "a", " ", "y", "After para."]],
  ["two whitespace-only siblings around an empty span", wrap("<ul><li><b>a</b> <span></span> <i>b</i></li></ul>"), ["Intro para.", "a", " ", "b", "After para."]],
];

test("collapsible white space after a neighbour whose text ends with a space (or a line break) measures 0 px and gets no mark; before a neighbour that begins with one, after a no-break space, an image or a kbd, and under pre, it renders and is painted", async (t) => {
  await inBrowser(t, async (page) => {
    for (const [why, src, texts] of TRAILING_SPACE) await collapsed(page, why, src, texts);
    for (const [why, src, texts] of TRAILING_SPACE_RENDERED) await rendered(page, why, src, texts);
    for (const [why, src, texts] of TWO_BLANKS) await mixed(page, why + ": the first blank renders, the second measures 0 px", src, texts, [true, false]);
  });
});

// ── 4. a collapsed blank and a rendered one in one line, the rendered one beside an inline svg ──────────────────────────────
/** The scenes the round 12 finding named. Judged in aggregate (some node at 0 px, no whitespace-only mark) they pass with the
 *  rendered blank left unpainted, which round 11's DOM-side reading did (it looked past the svg as rendering nothing); judged
 *  node by node they hold the paint to the browser's layout. `renders` names each blank below the top level in order. */
const MIXED_SVG: Array<[why: string, src: string, texts: string[], renders: boolean[]]> = [
  ["an anchor then an svg icon leading an item: the space at the line's start collapses, the one between the icon and the label renders",
   wrap('<ul><li><a name="x"></a> ' + SVG('<circle cx="8" cy="8" r="6"/>') + " <b>Label</b></li></ul>"), ["Intro para.", " ", "Label", "After para."], [false, true]],
  ["a centred row of svg badges after an anchor: the newline between the badges renders, the ones beside the anchor and at the edges collapse",
   wrap('<div align="center">\n<a name="top"></a>\n<a href="#a">' + SVG('<rect width="16" height="16"/>') + '</a>\n<a href="#b">' + SVG('<rect width="16" height="16"/>') + "</a>\n</div>"),
   ["Intro para.", "\n", "After para."], [false, false, true, false]],
];
/** An svg between two labels is a 16 px box: the space on each side of it renders and is painted. */
const SVG_RENDERED: Scene[] = [
  ["an svg icon between two labels", wrap("<ul><li><b>Left</b> " + SVG('<circle cx="8" cy="8" r="6"/>') + " <b>Right</b></li></ul>"), ["Intro para.", "Left", " ", " ", "Right", "After para."]],
];

test("a line holding a collapsed blank and a rendered one beside an inline svg: node by node, the rendered blank is painted and the collapsed one is not", async (t) => {
  await inBrowser(t, async (page) => {
    for (const [why, src, texts, renders] of MIXED_SVG) await mixed(page, why, src, texts, renders);
    for (const [why, src, texts] of SVG_RENDERED) await rendered(page, why, src, texts);
  });
});
