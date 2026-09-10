// The whitespace rule of the Rendered paint (anchor-map.ts skipBlockWs and trimCollapsedMarks) over the REAL bundle in headless
// Chromium: marked with the one configuration (md-config.ts), the sanitizer (md-sanitize.ts) and paintRendered, the DOM built as
// the viewer's mdBlock builds it, laid out under feed.css's prose rules. The browser is the oracle here for what
// md-config-paint-rendered-space.test.ts pins over a stand-in (the Slice 4 review, round 10; the layout-time trim since round
// 12): a whitespace-only text node is measured BEFORE the paint (a Range around it), and the paint must leave it marked when it
// has a width and unmarked when it has none (a DOM-side skip, or the trim's unwrap of the mark measured at zero width).
// 1. The collapsible set: HTML's ASCII white space alone in a paragraph renders nothing (width 0, and the paragraph makes no line),
//    and the paint skips it (the block-neighbour pre-skip: a collapsible node at a block-box parent's edge with nothing beside
//    it); a no-break, ideographic, em, thin or medium mathematical space renders its glyph's width and is painted. JavaScript's
//    `\s` matches all of them, which is how round 9's readings unpainted the rendered ones. Before a paragraph's first inline
//    element the same characters measure 0 px too, and since round 12 the paint measures rather than predicts (anchor-map.ts
//    trimCollapsedMarks: the node is painted, its mark measured in the painted layout and unwrapped at zero width): a space, a
//    tab and a line feed lose their mark there; a FORM FEED keeps it, since Chromium collapses a leading form feed in a bare text
//    node and renders it as a 14 px glyph once the node stands in an inline box of its own (a span or the mark, measured in
//    round 12), so the highlighted paragraph shows the glyph under its ring where the unpainted one shows nothing. A form feed
//    leading a block is written by no author; recorded, not predicted around (plans/markdown-viewer.md, item 10).
// 2. The scenes those readings unpainted, each a visible mark on main and at round 8: a `&nbsp;` spacer paragraph or cell (html
//    and markdown tables), a nbsp before a paragraph's first inline element, a nbsp alone between two `<br>`s, a full-width
//    indent. The mark is visible and wider than the sheet's 4 px of padding (7.89 x 16 for a nbsp, 18 x 16 for U+3000 at this
//    page's 14px sans-serif), and the layout is unchanged box for box, painted, unpainted and repainted. The collapsible
//    controls paint no whitespace-only mark.
// 3. The space between two inline children of a list item, a task item, a badge row, an html blockquote or a section, which main's
//    container rule skipped whatever the neighbours: it renders 3.89 px before the paint at this page's 14px sans-serif (the
//    viewer's sheet, where `--fs` is defined, renders it 4.75 px; this page defines no `--fs`, so `.fileview-md`'s font-size
//    is invalid at computed-value time and the prose inherits the body's 14px, the size every number in this file is read at),
//    and after it the marks on the line are contiguous (the space's mark, 7.89 x 16, abuts its neighbours' rings), where before
//    there was a bare gap of the space's width. Block children and the root's own white space paint no whitespace-only mark
//    and no top-level mark (the two DOM-side skips); a collapsed blank beside an inline child (an html blockquote's edges, the
//    newline between two br elements, the one beside a figure's image) is painted and its mark trimmed at zero width, so none
//    stands after the paint either.
// Skips LOUDLY without a playwright browser (CI installs none). Synthetic prose, no paths.
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
      resolveDir: UI, loader: "ts", sourcefile: "paint-rendered-space-probe.ts",
    },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "*.woff2"], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
/** The sheet's rules the scenes live under: the viewer's prose root, its paragraphs, lists, quotes, tables and images, and the highlight. */
function sheet(): string {
  const rule = (sel: string): string => {
    const m = new RegExp("\\n(" + sel.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + " \\{[^}]*\\})").exec(FEED);
    assert.ok(m, "a rule for " + sel + " in feed.css");
    return m![1];
  };
  return [".fileview-md", ".fileview-md p", ".fileview-md img", ".fileview-md ul, .fileview-md ol", ".fileview-md li", ".fileview-md blockquote",
          ".fileview-md table", ".fileview-md th, .fileview-md td", ".fc-hl"].map(rule).join("\n");
}
const PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8><style>
body { margin: 0; padding: 0; font: 14px/1.5 sans-serif; background: #1e1e1e; color: #ccc; --fg: #ccc; --dim: #999; --accent: #9cd2ff; --accent-wash: rgba(156,210,255,0.15); --warn: #e0a030; --bg: #1e1e1e; --font-doc: sans-serif; --box-border: #555; --overlay-05: rgba(255,255,255,0.05); }
${sheet()}
#md { width: 800px; }</style></head><body><div class="fileview-md" id="md"></div><script src="/dist/probe.js"></script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

type Rect = { x: number; y: number; w: number; h: number };
type WsNode = { parent: string; top: boolean; text: string; w: number };
type Mark = { parent: string; top: boolean; text: string; wsOnly: boolean; visible: boolean; rect: Rect };
type Layout = { height: number; tops: Array<[string, number, number]>; imgs: number[] };
const r2 = (n: number): number => Math.round(n * 100) / 100;

/** The page's own helpers: the viewer's render (mdBlock's shape: the sanitized body's children adopted), the whitespace-only text
 *  nodes measured, a layout read, the paint with each mark measured, and the panel's unpaint (file-comments.ts unpaint: the mark's
 *  children back in place, the parent normalized). */
const HELPERS = `
window.__render = (src) => { const md = document.getElementById("md"); md.replaceChildren(...Array.from(window.__romp.sanitizeMd(window.__romp.marked.parse(src)).childNodes)); return md.innerHTML; };
window.__wsNodes = () => { const md = document.getElementById("md"); const out = []; const w = document.createTreeWalker(md, NodeFilter.SHOW_TEXT);
  for (let t = w.nextNode(); t; t = w.nextNode()) { if (!/^\\s*$/.test(t.data)) continue; const r = document.createRange(); r.selectNodeContents(t); const b = r.getBoundingClientRect();
    out.push({ parent: t.parentNode.tagName, top: t.parentNode === md, text: t.data, w: Math.round(b.width * 100) / 100 }); } return out; };
window.__layout = () => { const md = document.getElementById("md"); const r = md.getBoundingClientRect();
  const tops = Array.from(md.children).map((c) => { const b = c.getBoundingClientRect(); return [c.tagName, Math.round(b.top * 100) / 100, Math.round(b.height * 100) / 100]; });
  const imgs = Array.from(md.querySelectorAll("img")).map((i) => { const b = i.getBoundingClientRect(); return Math.round(b.y * 100) / 100; });
  return { height: Math.round(r.height * 100) / 100, tops, imgs }; };
window.__paint = (src) => { const md = document.getElementById("md");
  const range = { start: src.indexOf("Intro para."), end: src.indexOf("After para.") + "After para.".length };
  const marks = window.__romp.paintRendered(md, src, range, "fc-hl", { id: "c1" }) || [];
  return marks.map((m) => { const b = m.getBoundingClientRect(); return { parent: m.parentElement.tagName, top: m.parentElement === md, text: m.textContent, wsOnly: !m.textContent.trim(), visible: m.checkVisibility(),
    rect: { x: Math.round(b.x * 100) / 100, y: Math.round(b.y * 100) / 100, w: Math.round(b.width * 100) / 100, h: Math.round(b.height * 100) / 100 } }; }); };
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
/** Render, measure, paint, and hold: the marks' text is `texts`; every whitespace-only mark is visible and wider than the sheet's 4
 *  px of padding (a rendered blank under it); no mark is a top-level node; the layout is unchanged painted, unpainted and repainted.
 *  Returns the whitespace-only text nodes as measured before the paint and the marks. */
async function drive(page: any, what: string, src: string, texts: string[]): Promise<{ ws: WsNode[]; marks: Mark[] }> {
  await page.evaluate((s: string) => (window as any).__render(s), src);
  const ws: WsNode[] = await page.evaluate(() => (window as any).__wsNodes());
  const before: Layout = await page.evaluate(() => (window as any).__layout());
  const marks: Mark[] = await page.evaluate((s: string) => (window as any).__paint(s), src);
  const after: Layout = await page.evaluate(() => (window as any).__layout());
  assert.deepEqual(marks.map((m) => m.text), texts, what + ": the marks' text");
  for (const m of marks) {
    assert.ok(!m.top, what + ": no mark is a top-level node: " + JSON.stringify(m.text));
    if (m.wsOnly) assert.ok(m.visible && m.rect.w > 5, what + ": a whitespace-only mark is a rendered blank plus the padding, not the padding alone: " + m.parent + " " + JSON.stringify(m.text) + " " + m.rect.w + "x" + m.rect.h);
  }
  same(before, after, what + ", painted");
  await page.evaluate(() => (window as any).__unpaint());
  same(before, await page.evaluate(() => (window as any).__layout()), what + ", unpainted");
  const again: Mark[] = await page.evaluate((s: string) => (window as any).__paint(s), src);
  assert.deepEqual(again.map((m) => m.text), texts, what + ": the same marks on a repaint");
  same(before, await page.evaluate(() => (window as any).__layout()), what + ", repainted");
  await page.evaluate(() => (window as any).__unpaint());
  return { ws, marks };
}
const wrap = (block: string): string => "Intro para.\n\n" + block + "\n\nAfter para.\n";
const NBSP = "\u00a0", IDEO = "\u3000";

// ── 1. the collapsible set, against the browser ─────────────────────────────────────────────────────────────────────────────
/** A text node of each alone in a paragraph, then before the paragraph's first inline element: what it measures decides whether the
 *  paint may skip it. A carriage return is not among the scenes: marked's preprocessing turns it into a line feed before any of
 *  this. */
const COLLAPSIBLE: Array<[string, string]> = [["a space", " "], ["a tab", "\t"], ["a line feed", "\n"], ["a form feed", "\f"]];
const RENDERED_SPACES: Array<[string, string]> = [["a no-break space", NBSP], ["an ideographic space", IDEO], ["an em space", "\u2003"], ["a thin space", "\u2009"], ["a medium mathematical space", "\u205f"]];

test("HTML's ASCII white space alone in a paragraph measures 0 px and is skipped, and before the paragraph's first inline element it is measured and trimmed (a form feed excepted: a glyph inside the mark); a no-break, ideographic, em, thin or medium mathematical space measures its glyph and is painted (JavaScript's \\s matches every one of them)", async (t) => {
  await inBrowser(t, async (page) => {
    for (const [why, ch] of COLLAPSIBLE) {
      assert.ok(/^\s$/.test(ch), why + " is \\s");
      const alone = await drive(page, why + " alone in a paragraph", wrap("<p>" + ch + "</p>"), ["Intro para.", "After para."]);
      const node = alone.ws.find((n) => !n.top && n.parent === "P");
      assert.ok(node, why + ": the paragraph holds the whitespace-only text node: " + JSON.stringify(alone.ws));
      assert.equal(node!.w, 0, why + " alone in a paragraph renders nothing");
      // a form feed leading the paragraph: 0 px as a bare text node, a 14 px glyph inside the mark (header, point 1), so the trim
      // keeps its mark and drive()'s own check holds the mark wider than the padding; the other three measure 0 px under the mark
      // too and lose it
      const glyph = ch === "\f";
      const led = await drive(page, why + " before a paragraph's first inline element", wrap("<p>" + ch + "<b>x</b> tail</p>"), glyph ? ["Intro para.", ch, "x", " tail", "After para."] : ["Intro para.", "x", " tail", "After para."]);
      assert.equal(led.ws.find((n) => !n.top && n.parent === "P")!.w, 0, why + " at a paragraph's edge renders nothing as a bare text node");
      assert.equal(led.marks.filter((m) => m.wsOnly).length, glyph ? 1 : 0, why + " at a paragraph's edge: " + (glyph ? "a mark, the glyph Chromium renders inside an inline box" : "no mark once measured in the painted layout"));
    }
    for (const [why, ch] of RENDERED_SPACES) {
      assert.ok(/^\s$/.test(ch), why + " is \\s too");
      const alone = await drive(page, why + " alone in a paragraph", wrap("<p>" + ch + "</p>"), ["Intro para.", ch, "After para."]);
      const node = alone.ws.find((n) => !n.top && n.parent === "P")!;
      assert.ok(node.w > 0, why + " alone in a paragraph renders its glyph: " + node.w + " px");
      const mark = alone.marks.find((m) => m.wsOnly)!;
      assert.ok(mark.rect.w >= node.w + 4 - 0.02, why + ": the mark is the glyph plus the sheet's 4 px of padding: " + mark.rect.w + " over " + node.w);
      const led = await drive(page, why + " before a paragraph's first inline element", wrap("<p>" + ch + "<b>x</b> tail</p>"), ["Intro para.", ch, "x", " tail", "After para."]);
      assert.ok(led.ws.find((n) => !n.top && n.parent === "P")!.w > 0, why + " at a paragraph's edge renders its glyph");
    }
  });
});

// ── 2. the scenes round 9 unpainted ─────────────────────────────────────────────────────────────────────────────────────────
type Scene = [why: string, src: string, texts: string[]];
const RENDERED: Scene[] = [
  ["a nbsp spacer paragraph", wrap("<p>&nbsp;</p>"), ["Intro para.", NBSP, "After para."]],
  ["a nbsp spacer cell in an html table", wrap("<table><tr><td>&nbsp;</td><td>x</td></tr></table>"), ["Intro para.", NBSP, "x", "After para."]],
  ["a nbsp spacer cell in a markdown table", wrap("| a | b |\n|---|---|\n| &nbsp; | x |"), ["Intro para.", "a", "b", NBSP, "x", "After para."]],
  ["a nbsp before a paragraph's first inline element", wrap("<p>&nbsp;<b>bold</b> tail</p>"), ["Intro para.", NBSP, "bold", " tail", "After para."]],
  ["a nbsp alone on a line between two line breaks", wrap("line one<br>\n&nbsp;<br>\nline three"), ["Intro para.", "line one", "\n" + NBSP, "\nline three", "After para."]],
  ["an ideographic space indenting a paragraph", wrap("<p>" + IDEO + "<b>x</b> tail</p>"), ["Intro para.", IDEO, "x", " tail", "After para."]],
  ["a nbsp beside a block box at a div's edge", wrap("<div>&nbsp;<p>x</p></div>"), ["Intro para.", NBSP, "x", "After para."]],
  ["a nbsp alone in a div (main's container rule skipped it; a blank line the note renders)", wrap("<div>&nbsp;</div>"), ["Intro para.", NBSP, "After para."]],
];
const COLLAPSED: Scene[] = [
  ["a newline alone in a cell", wrap("<table><tr><td>\n</td><td>x</td></tr></table>"), ["Intro para.", "x", "After para."]],
  ["a newline between two line breaks", wrap("line one<br>\n<br>\nline three"), ["Intro para.", "line one", "\nline three", "After para."]],
  ["the newline between a figure and its image", wrap('<figure>\n<img src="data:image/gif;base64,R0lGODlhAQABAAAAACw=" width="100" height="50" alt="pic">\n<figcaption>Caption text</figcaption>\n</figure>'), ["Intro para.", "Caption text", "After para."]],
];

test("a highlight across a nbsp spacer paragraph or cell, a nbsp-led line, a nbsp between two line breaks or a full-width indent paints the blank (7.89 x 16, or 18 x 16, on this page) and moves nothing; collapsible white space at the same positions is skipped", async (t) => {
  await inBrowser(t, async (page) => {
    for (const [why, src, texts] of RENDERED) {
      const { ws, marks } = await drive(page, why, src, texts);
      const rendered = ws.filter((n) => !n.top && n.w > 0);
      assert.ok(rendered.length >= 1, why + ": a whitespace-only text node with a width before the paint: " + JSON.stringify(ws));
      const wsMarks = marks.filter((m) => m.wsOnly);
      assert.equal(wsMarks.length, rendered.length, why + ": one whitespace-only mark per rendered blank: " + JSON.stringify(wsMarks.map((m) => m.parent + " " + JSON.stringify(m.text) + " " + m.rect.w + "x" + m.rect.h)));
      for (const m of wsMarks) assert.ok(m.rect.w >= 7.5 && m.rect.h >= 14, why + ": the mark is the blank plus the padding: " + m.rect.w + "x" + m.rect.h);
    }
    for (const [why, src, texts] of COLLAPSED) {
      const { ws, marks } = await drive(page, why, src, texts);
      assert.ok(ws.some((n) => !n.top && n.w === 0), why + ": a whitespace-only text node of no width below the top level: " + JSON.stringify(ws));
      assert.deepEqual(marks.filter((m) => m.wsOnly), [], why + ": no whitespace-only mark");
    }
  });
});

// ── 3. the space between two inline children of a container ────────────────────────────────────────────────────────────────
const PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==";
const IMG = (alt: string): string => '<img src="' + PNG + '" width="40" height="20" alt="' + alt + '">';
/** Each scene: the block, the marks' text, and the texts of the two marks that stand on either side of the space on its line. */
const INLINE_CHILDREN: Array<[string, string, string[], [string, string]]> = [
  ["a tight list item of two inline elements", wrap("- **Deadline:** *Friday*"), ["Intro para.", "Deadline:", " ", "Friday", "After para."], ["Deadline:", "Friday"]],
  ["a nested tight item", wrap("- top\n  - **a** *b*"), ["Intro para.", "top", "a", " ", "b", "After para."], ["a", "b"]],
  ["a task item", wrap("- [ ] **a** *b*"), ["Intro para.", " ", "a", " ", "b", "After para."], ["a", "b"]],
  ["two links in an item", wrap("- [a](#a) [b](#b)"), ["Intro para.", "a", " ", "b", "After para."], ["a", "b"]],
  ["an html blockquote of inline elements", wrap("<blockquote> <b>q</b> <i>r</i> </blockquote>"), ["Intro para.", "q", " ", "r", "After para."], ["q", "r"]],
  ["a section of inline elements", wrap("<section><b>a</b> <i>b</i></section>"), ["Intro para.", "a", " ", "b", "After para."], ["a", "b"]],
  ["an item inside a quote", wrap("> - **a** *b*"), ["Intro para.", "a", " ", "b", "After para."], ["a", "b"]],
];
const BLOCK_CHILDREN: Scene[] = [
  ["a markdown list", wrap("- one\n- two"), ["Intro para.", "one", "two", "After para."]],
  ["an html list with a blank line between its items", wrap("<ul>\n<li>one</li>\n\n<li>two</li>\n</ul>"), ["Intro para.", "one", "two", "After para."]],
  ["an html table with newlines between its parts", wrap("<table>\n<tr>\n<td>one</td>\n<td>two</td>\n</tr>\n</table>"), ["Intro para.", "one", "two", "After para."]],
  ["a quote of two paragraphs", wrap("> one\n>\n> two"), ["Intro para.", "one", "two", "After para."]],
  ["a div of two paragraphs", wrap("<div>\n<p>one</p>\n<p>two</p>\n</div>"), ["Intro para.", "one", "two", "After para."]],
  ["an item holding a space alone", wrap("<ul><li> </li><li>two</li></ul>"), ["Intro para.", "two", "After para."]],
  ["two images as one html block: the newline between them is the root's", wrap(IMG("a") + "\n" + IMG("b")), ["Intro para.", "After para."]],
];

test("a highlight across a list item, a task item, a badge row, an html blockquote or a section paints the space between two inline children, and the marks on the line abut where main's container rule left a bare gap of the space's width; block children and the root's white space are skipped", async (t) => {
  await inBrowser(t, async (page) => {
    for (const [why, src, texts, [left, right]] of INLINE_CHILDREN) {
      const { ws, marks } = await drive(page, why, src, texts);
      const spaces = ws.filter((n) => !n.top && n.text === " " && n.w > 0);
      assert.ok(spaces.length >= 1, why + ": the space between the inline children renders before the paint: " + JSON.stringify(ws));
      const a = marks.find((m) => m.text === left)!, b = marks.find((m) => m.text === right)!;
      const sp = marks.find((m) => m.wsOnly && m.rect.y === a.rect.y && m.rect.x >= a.rect.x + a.rect.w - 0.5)!;
      assert.ok(a && b && sp, why + ": the two inline marks and the space's mark on their line: " + JSON.stringify(marks.map((m) => [m.parent, m.text, m.rect])));
      assert.ok(Math.abs(sp.rect.x - (a.rect.x + a.rect.w)) < 0.5 && Math.abs(b.rect.x - (sp.rect.x + sp.rect.w)) < 0.5,
                why + ": the space's mark abuts both neighbours (no bare gap on the line): " + JSON.stringify([a.rect, sp.rect, b.rect]));
      assert.ok(sp.rect.w > spaces[0].w + 3.5, why + ": the space's mark is the space plus the padding: " + sp.rect.w + " over " + spaces[0].w);
    }
    // the badge row: two linked images with a space between, the space the only text under the highlight's div
    const badge = wrap('<div align="center"><a href="#a">' + IMG("a") + '</a> <a href="#b">' + IMG("b") + "</a></div>");
    const { ws, marks } = await drive(page, "a centred badge row", badge, ["Intro para.", " ", "After para."]);
    assert.ok(ws.some((n) => n.parent === "DIV" && !n.top && n.w > 0), "the badge row's space renders before the paint: " + JSON.stringify(ws));
    assert.equal(marks.find((m) => m.wsOnly)!.parent, "DIV", "the space's mark stands under the row's div");
    for (const [why, src, texts] of BLOCK_CHILDREN) {
      const { marks } = await drive(page, why, src, texts);
      assert.deepEqual(marks.filter((m) => m.wsOnly), [], why + ": no whitespace-only mark");
    }
  });
});
