// The comments painter's layout-time trim (anchor-map.ts trimCollapsedMarks, the Slice 4 review's round 12) over the REAL bundle in
// headless Chromium: marked with the one configuration (md-config.ts), the sanitizer (md-sanitize.ts) and paintRendered, the DOM
// built as the viewer's mdBlock builds it, laid out under the whole of feed.css at 14px sans-serif. The scenes are the union the
// review's rounds 7 to 13 collected (anchor-map-fixtures/blank-scenes.json: folds, an author's figure, details, dl and center,
// badge rows, br pairs, wrap points at several widths, a nbsp and an ideographic space, U+FEFF and the zero-width and bidi
// characters, svg icons, audio with and without controls, an author pre with br and block children and with spaces or a tab
// between its block children, tables, footnote definitions, list items, a form feed, a CRLF, a floated image, a picture without
// an image, ruby and rp, a space inside a kbd, a table caption, and a plain note), each painted from the paragraph before to the paragraph after at its width, once with one
// comment and once with two comments across the same passage (the Comments panel paints overlapping comments nested, the later
// comment's mark inside the earlier one's around every text node, and trims the pass once: point 5). No expected marks are recorded
// anywhere: the browser's layout is the oracle, read after the paint.
// 1. Every scene: the trimmed paint's non-blank marks are the untrimmed paint's (the trim removes blank marks alone); no blank mark
//    whose text lays out at zero width stands with a box of its own (the padding-only box: 4 x 16 px on this page for one mark, 8
//    and 12 px for the rings around a collapsed mark's ring; rounds 7 to 11's defect) unless the mark has no box of its own (a hidden
//    ancestor); every blank text node below the top level that renders with a width in the painted layout carries a mark (no ring
//    gap at a rendered blank) wherever the trim unwrapped nothing, which is the case for most scenes at 800 px but not by
//    construction (the paragraph of fourteen links lays out on two lines at 800 px in the leg's font, and the trim unwraps the space
//    at its wrap point; another font's metrics move the break), and where it unwrapped something point 2's bound holds; no mark is a
//    top-level node; the panel's unpaint restores the exact HTML after either paint; on the plain note the trim unwraps nothing.
// 2. The wrap points: the list item and the paragraph of fourteen links painted at 800, 500, 300, 260, 240, 220, 200 and 180 px:
//    no padding-only mark at any width after the fixpoint (a mark's 2 px side padding is in the layout, so the paint moves the wrap
//    points and the trim measures again after a pass that unwrapped something); every blank mark whose text the untrimmed layout
//    collapsed is among the unwrapped (the first pass measures that layout; a ring around a collapsed mark follows once the mark
//    inside it is gone), and the sweep unwraps something at some width (which widths break the line at a space between two links
//    rather than inside a link's text is the font's: 800 px is the widest of the wrap widths, not a wrap-free layout). The
//    fixpoint's price, recorded and bounded: a blank unwrapped as collapsed can render once a later unwrap on its line moves the
//    wrap point back, and it is never re-wrapped (a mark at a line's last inch would flip with every pass), so a rendered space may
//    stand unmarked, a ring gap of the space's width; the price is bimodal by width, none at most widths and a cascade through the
//    lines below at a width where a line's slack falls inside the marks' padding (on the build box the list item here shows one of
//    eleven at 240 px and four of ten at 220; a list item of 120 links 80 of 90 at 240 px and none at 25 of 31 widths sampled every
//    20 px; the paragraph of 5,000 links 341 to 2,095 of about 4,400 at seven of eleven widths and none at four, once the fixpoint
//    completes; plan item 10 (a) has the figures); never more such blanks than marks unwrapped, and none at all where nothing was
//    unwrapped. The layout-neutral mark (`margin: 0 -2px` beside the padding) removes the shape and is the owner's call
//    (plans/markdown-viewer.md, item 10).
// 3. The reflow: marks painted at 800 px and the root narrowed to 300 px with no repaint (the panel does not repaint on a reflow)
//    show padding-only marks at the new wrap points until trimCollapsedMarks runs over them again, the panel's re-trim
//    (file-comments.ts trimBlanks on the seam's "reflow"); after it none stands, at any depth of nesting. A blank trimmed at 800 px
//    that renders at 300 px stays unmarked until the next paint pass, the recorded stale shape (the 120-link item narrowed in one
//    step from 800 px shows 10 to 44 of about 100 rendered blanks bare, the paragraph of 5,000 links 295 to 3,267 of about 4,400 once
//    the re-trim converges, and a 10 px stepwise drag to 300 px leaves 115 of 118 bare; plan item 10 (b)).
// 4. The cost profile the panel pays (round 12's prototype measured it on this shape): 300 paragraphs of twenty words with bold and
//    italic runs, 200 comments across `word **b** *i*` (two blank marks each); the batched pass (every paint with `trim: false`,
//    one trimCollapsedMarks over every mark) against the untrimmed pass, the median of PAIRS pair ratios bounded at BATCH_BOUND
//    (about 1.0 to 1.1 on the build box: one layout for the pass), and the unbatched pass (a trim per paint, one layout each)
//    recorded in the failure text; the batched and the unbatched pass paint the same marks.
// 5. The oracle's own check, and the shape it exists for. The padding-only oracle measures the TEXT NODES under a mark, never the
//    mark's contents: a Range over an outer mark's contents reads the inner mark's box, its padding included, so a ring of padding
//    around a collapsed mark's ring reads 4 px, and a third ring 8 px, and a contents reading lists neither (the review round 13,
//    which found the legs proving "no padding-only mark" for one comment per passage alone). An outer mark hand-wrapped around a
//    collapsed blank mark, and a third around that, are listed at every depth. The trim itself reads the contents (anchor-map.ts
//    contentWidth) and peels a nest one ring per pass, so two comments across one passage (points 1 to 3, painted as the panel's
//    pass paints them: every paint with `trim: false`, one trimCollapsedMarks over both) leave no ring at any width or after a
//    reflow within the fixpoint's passes; deeper nests are the fixpoint's own legs' (md-config-paint-trim-fixpoint-browser.test.ts).
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
type Scene = { name: string; width: number; markdown: string };
const SCENES = (JSON.parse(fs.readFileSync(path.join(UI, "anchor-map-fixtures", "blank-scenes.json"), "utf8")) as { scenes: Scene[] }).scenes;
/** The one scene the block pairing refuses early (the recorded defect, plan item 10 (d); the helpers' comment below): its paint
 *  stops at the html block and never reaches the closing paragraph. */
const REFUSED = "adjacent whitespace nodes left by a stripped comment";

/** marked with the viewer's grammar, the sanitizer, the paint and the trim, bundled as the webview build bundles them. */
function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: {
      contents: 'import { marked } from "marked";\nimport { applyMdConfig } from "./md-config";\nimport { sanitizeMd } from "./md-sanitize";\n'
        + 'import { paintRendered, trimCollapsedMarks } from "./anchor-map";\napplyMdConfig();\n(window as any).__romp = { marked, sanitizeMd, paintRendered, trimCollapsedMarks };\n',
      resolveDir: UI, loader: "ts", sourcefile: "paint-trim-probe.ts",
    },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "*.woff2"], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
/** The whole feed sheet, its KaTeX import and its print block left out (the scenes render no math and print nothing). */
const sheet = (): string => FEED.replace('@import "katex/dist/katex.min.css";', "").replace(/@media print \{[\s\S]*$/, "");
const PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8><style>${sheet()}</style><style>
body { margin: 0; padding: 0; font: 14px/1.5 sans-serif; background: #1e1e1e; color: #ccc; --fg: #ccc; --dim: #999; --accent: #9cd2ff; --accent-wash: rgba(156,210,255,0.15); --warn: #e0a030; --bg: #1e1e1e; --font-doc: sans-serif; --box-border: #555; --overlay-05: rgba(255,255,255,0.05); --kbd-bg: #1c1c1f; --kbd-border: #3d3d42; --mono: monospace; --code-bg: rgba(255,255,255,0.08); --green: #7bc67b; --err: #e06060; --surface-raised: #252526; --shadow-menu: none; --radius-pill: 999px; }
#md { width: 800px; padding: 0; contain: none; font-size: 14px; }</style></head><body><div class="fileview-md" id="md"></div><script src="/dist/probe.js"></script></body></html>`;
/** A 1 x 1 PNG for every image a scene names (a broken image renders its alt text instead of a box). */
const PNG = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==", "base64");

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

/** The page's own helpers. BLANK is the trim's candidate alphabet (anchor-map.ts TRIM_CANDIDATE): no letter, digit, punctuation
 *  or symbol, or the hangul fillers. `width` is the trim's own reading of a node, a Range over its contents with the rects' widths
 *  summed; `textWidth` sums that reading over the TEXT NODES under an element, the oracle's reading (point 5: over a mark holding
 *  another mark, `width` reads the inner mark's padding as width). `__paint` paints the whole range with or without the trim, once
 *  per comment (`k` comments nest, the later inside the earlier; two or more are painted as the panel's pass paints them, every
 *  paint with `trim: false` and one trimCollapsedMarks over all of them), and reads each mark's text, both widths, whether it has a
 *  box of its own, how many marks it holds and whether it is a top-level node; `__bare` lists the blank text nodes below the top
 *  level that render with a width and carry no mark, inside the top-level blocks the paint reached (a block the pairing refused
 *  holds no mark and is no unmarked blank of the trim's: the union holds one such scene, REFUSED, an html block followed by a list
 *  item whose source text the sanitizer shortens, a stripped style, the pairing's own recorded defect, plan item 10 (d); every other
 *  scene's paint must reach the closing paragraph, test 1); `__unpaint` is the panel's (children back, the parent normalized) and
 *  returns the HTML; `__nest` hand-wraps a collapsed blank mark of an untrimmed paint in two more marks and reads all three. */
const HELPERS = `
const BLANK = /^(?:[^\\p{L}\\p{N}\\p{P}\\p{S}]|[\\u115f\\u1160\\u3164\\uffa0])*$/u;
const md = () => document.getElementById("md");
const width = (n) => { const r = document.createRange(); r.selectNodeContents(n); let w = 0; for (const b of Array.from(r.getClientRects())) w += b.width; return Math.round(w * 100) / 100; };
const textWidth = (n) => { let w = 0; const walk = document.createTreeWalker(n, NodeFilter.SHOW_TEXT); for (let t = walk.nextNode(); t; t = walk.nextNode()) w += width(t); return Math.round(w * 100) / 100; };
const range = (src) => ({ start: src.indexOf("Intro para."), end: src.indexOf("After para.") + "After para.".length });
window.__render = (src, w) => { const m = md(); m.style.width = w + "px"; m.replaceChildren(...Array.from(window.__romp.sanitizeMd(window.__romp.marked.parse(src)).childNodes)); return m.innerHTML; };
window.__width = (w) => { md().style.width = w + "px"; return md().getBoundingClientRect().width; };
const readMark = (k) => ({ text: k.textContent, blank: BLANK.test(k.textContent), w: width(k), wt: textWidth(k), own: k.getClientRects().length, holds: k.querySelectorAll("mark").length, top: k.parentNode === md() });
const paintOne = (src, id, trim) => window.__romp.paintRendered(md(), src, range(src), "fc-hl", { id }, { trim }) || [];
window.__paint = (src, trim, k = 1) => {
  let marks;
  if (k === 1) marks = paintOne(src, "c1", trim);
  else { marks = []; for (let i = 1; i <= k; i++) marks = marks.concat(paintOne(src, "c" + i, false)); if (trim) marks = window.__romp.trimCollapsedMarks(marks); }
  window.__marks = marks; return marks.map(readMark); };
window.__retrim = () => { window.__marks = window.__romp.trimCollapsedMarks(window.__marks.filter((k) => k.isConnected)); return window.__marks.map(readMark); };
window.__staleZero = () => window.__marks.filter((k) => BLANK.test(k.textContent) && textWidth(k) === 0 && k.getClientRects().length > 0).map(readMark);
const topOf = (n) => { let c = n; while (c.parentNode && c.parentNode !== md()) c = c.parentNode; return c; };
window.__bare = () => { const out = []; const w = document.createTreeWalker(md(), NodeFilter.SHOW_TEXT);
  for (let t = w.nextNode(); t; t = w.nextNode()) { if (t.parentNode === md() || !BLANK.test(t.data)) continue;
    // a blank in a block the paint never reached (an html block the pairing refused, its marks none) is no unmarked blank of the trim's
    const top = topOf(t); if (!(top.querySelector && top.querySelector("mark.fc-hl"))) continue;
    if (width(t) > 0 && !(t.parentElement && t.parentElement.closest("mark"))) out.push({ parent: t.parentNode.tagName, text: t.data, w: width(t) }); }
  return out; };
window.__unpaint = () => { const parents = new Set(); for (const n of Array.from(md().querySelectorAll("mark.fc-hl"))) { const p = n.parentNode; parents.add(p); while (n.firstChild) p.insertBefore(n.firstChild, n); p.removeChild(n); } for (const p of parents) p.normalize(); return md().innerHTML; };
window.__nest = (src) => { const marks = paintOne(src, "c1", false);
  const inner = marks.find((k) => BLANK.test(k.textContent) && textWidth(k) === 0 && k.getClientRects().length > 0); if (!inner) return null;
  const wrap = (n) => { const o = document.createElement("mark"); o.className = "fc-hl"; n.parentNode.insertBefore(o, n); o.appendChild(n); return o; };
  const outer = wrap(inner), third = wrap(outer); return [inner, outer, third].map(readMark); };
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
      if (/\.(png|gif|jpg|avif|webp)$/i.test(u.pathname)) return route.fulfill({ status: 200, contentType: "image/png", body: PNG });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/page");
    await page.waitForFunction(() => !!(window as any).__romp && !!(window as any).__paint);
    await body(page);
    assert.deepEqual(errors, [], "no page errors");
  } finally { await browser.close(); }
}
/** A mark as the page reads it: `w` the trim's reading over its contents, `wt` the oracle's over its text nodes, `own` its client
 *  rects, `holds` the marks nested inside it. */
type Mark = { text: string; blank: boolean; w: number; wt: number; own: number; holds: number; top: boolean };
type Bare = { parent: string; text: string; w: number };
/** A mark's text for a message, every character past ASCII spelt as its escape (the blanks are invisible otherwise). */
const show = (s: string): string => JSON.stringify(s).replace(/[^\x00-\x7f]/g, (c) => "\\u" + c.charCodeAt(0).toString(16).padStart(4, "0"));
/** The blank marks whose text nodes lay out at zero width and that have a box of their own: the padding-only marks, a ring around
 *  nothing or around another ring (point 5; the contents reading `w` is shown beside the text reading so a ring is told from a
 *  single mark). */
const paddingOnly = (marks: Mark[]): string[] => marks.filter((m) => m.blank && m.wt === 0 && m.own > 0).map((m) => show(m.text) + " (contents " + m.w + " px, text 0 px, " + m.holds + " marks inside)");
const bareList = (bare: Bare[]): string[] => bare.map((b) => b.parent + " " + show(b.text) + " " + b.w);
/** Render at `width`, paint `k` comments across the whole passage untrimmed and trimmed, hold point 1's properties, and return
 *  both paints' marks and the bare blanks. */
async function drive(page: any, what: string, src: string, width: number, k = 1): Promise<{ untrimmed: Mark[]; trimmed: Mark[]; bare: Bare[]; unwrapped: number }> {
  const fresh: string = await page.evaluate(([s, w]: [string, number]) => (window as any).__render(s, w), [src, width]);
  const untrimmed: Mark[] = await page.evaluate(([s, k]: [string, number]) => (window as any).__paint(s, false, k), [src, k]);
  assert.ok(untrimmed.length, what + ": painted");
  for (const m of untrimmed) assert.ok(!m.top, what + ": no top-level mark (untrimmed): " + show(m.text));
  assert.equal(await page.evaluate(() => (window as any).__unpaint()), fresh, what + ": the unpaint after the untrimmed paint restores the HTML");
  const trimmed: Mark[] = await page.evaluate(([s, k]: [string, number]) => (window as any).__paint(s, true, k), [src, k]);
  const bare: Bare[] = await page.evaluate(() => (window as any).__bare());
  assert.deepEqual(trimmed.filter((m) => !m.blank).map((m) => m.text), untrimmed.filter((m) => !m.blank).map((m) => m.text), what + ": the trim removes blank marks alone");
  assert.deepEqual(paddingOnly(trimmed), [], what + ": no blank mark whose text lays out at zero width stands with a box of its own (the padding-only box, at any depth)");
  for (const m of trimmed) assert.ok(!m.top, what + ": no top-level mark: " + show(m.text));
  assert.equal(await page.evaluate(() => (window as any).__unpaint()), fresh, what + ": the unpaint after the trimmed paint restores the HTML");
  const unwrapped = untrimmed.length - trimmed.length;
  // where the trim unwrapped nothing every blank the paint reached keeps its mark, so a rendered blank without one is a blank the
  // paint skipped: none may render. Where it unwrapped something the fixpoint's price applies (point 2): a rendered blank unmarked
  // only where a mark was unwrapped, never more. The event, not the width, picks the pin: a scene at 800 px can wrap.
  if (unwrapped === 0) assert.deepEqual(bareList(bare), [], what + ": nothing unwrapped, so every blank below the top level that renders in the painted layout carries a mark");
  else assert.ok(bare.length <= unwrapped, what + ": a rendered blank unmarked only where a mark was unwrapped: " + JSON.stringify(bareList(bare)) + " against " + unwrapped + " unwrapped");
  return { untrimmed, trimmed, bare, unwrapped };
}
/** One comment, and two comments across the same passage (the panel's nested paint). */
const COMMENTS = [1, 2];
const across = (k: number): string => k === 1 ? "one comment" : k + " comments across the passage";

// -- 1. every scene of the union ---------------------------------------------------------------------------------------------
test("every scene of the union, one comment and two comments across the passage: the trim removes blank marks alone, leaves no padding-only mark at any depth and, where it unwrapped nothing, no rendered blank unmarked, no top-level mark, the unpaint exact; the plain note is painted as without the trim", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (page) => {
    assert.ok(SCENES.length >= 90, "the fixture holds the union: " + SCENES.length + " scenes");
    for (const k of COMMENTS) {
      let trimmedSomething = 0;
      for (const sc of SCENES) {
        const what = sc.name + " @" + sc.width + "px, " + across(k);
        const { untrimmed, trimmed, unwrapped } = await drive(page, what, sc.markdown, sc.width, k);
        // the paint reaches the closing paragraph: a scene the pairing refuses early passes every oracle above vacuously, its
        // construct never painted (round 13 found two such scenes in the union, a lone CR that split an html block and a list item
        // whose stripped text equalled the html block's before it); the recorded refused scene is the one exception
        if (!sc.name.startsWith(REFUSED)) assert.equal(untrimmed[untrimmed.length - 1].text, "After para.", what + ": the paint reaches the closing paragraph (a scene the pairing refuses early exercises nothing)");
        if (unwrapped > 0) trimmedSomething++;
        if (sc.name.startsWith("plain note")) assert.deepEqual(trimmed.map((m) => m.text), untrimmed.map((m) => m.text), what + ": the trim unwraps nothing on the plain note");
      }
      assert.ok(trimmedSomething >= 30, across(k) + ": the trim unwrapped something in most collapsed scenes: " + trimmedSomething + " of " + SCENES.length);
    }
  });
});

// -- 2. the wrap points at several widths ----------------------------------------------------------------------------------------
const LINKS = Array.from({ length: 14 }, (_, i) => "[Link" + i + " docs](#l" + i + ")").join(" ");
const WRAPS: Array<[string, string]> = [["the list item of fourteen links", "Intro para.\n\n- " + LINKS + "\n\nAfter para."], ["the paragraph of fourteen links", "Intro para.\n\n" + LINKS + "\n\nAfter para."]];
const WIDTHS = [800, 500, 300, 260, 240, 220, 200, 180];

test("the wrap points: a list item and a paragraph of fourteen links, one comment and two across them, painted at eight widths from 800 to 180 px leave no padding-only mark after the fixpoint and unwrap every blank the untrimmed layout collapsed; a rendered blank left unmarked is bounded by the unwraps (the fixpoint's price, recorded)", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (page) => {
    for (const k of COMMENTS) for (const [why, src] of WRAPS) {
      let sweepUnwrapped = 0;
      for (const w of WIDTHS) {
        const what = why + " @" + w + "px, " + across(k);
        const { untrimmed, trimmed, bare, unwrapped } = await drive(page, what, src, w, k);
        const kept = trimmed.filter((m) => m.blank).length, all = untrimmed.filter((m) => m.blank).length;
        // the first pass measures the untrimmed layout and drops every mark whose contents it collapsed (two-phase: measured, then
        // dropped, before any layout changed); a ring around one reads that mark's padding and follows once the mark inside it is
        // gone; so every blank mark whose text that layout collapsed is unwrapped by the fixpoint, and later passes may unwrap more
        const collapsed = untrimmed.filter((m) => m.blank && m.wt === 0 && m.own > 0).length;
        assert.ok(kept <= all && unwrapped >= collapsed, what + ": every blank mark the untrimmed layout collapsed is unwrapped (" + collapsed + " collapsed, " + unwrapped + " unwrapped, " + kept + " of " + all + " blank marks kept)");
        assert.ok(bare.length <= unwrapped, what + ": a rendered blank left unmarked is one the fixpoint unwrapped and a later unwrap brought back onto its line, never more than the unwraps: " + JSON.stringify(bareList(bare)) + " against " + unwrapped + " unwrapped");
        sweepUnwrapped += unwrapped;
      }
      // which widths break the line at a space between two links (a blank mark, unwrapped) rather than inside a link's text (no
      // blank mark there) is the font's; the sweep of eight widths meets the wrap points somewhere
      assert.ok(sweepUnwrapped > 0, why + ", " + across(k) + ": the sweep unwrapped the wrap points' blanks at some width");
    }
  });
});

// -- 3. the reflow: marks painted at one width, the root narrowed, the re-trim ----------------------------------------------------
test("marks painted at 800 px and reflowed to 300 px with no repaint show padding-only marks at the new wrap points, a ring per comment at each; trimCollapsedMarks over the standing marks (the panel's re-trim on a reflow) leaves none at any depth", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (page) => {
    const [, src] = WRAPS[0];
    for (const k of COMMENTS) {
      const what = across(k);
      await page.evaluate(([s, w]: [string, number]) => (window as any).__render(s, w), [src, 800]);
      const at800: Mark[] = await page.evaluate(([s, k]: [string, number]) => (window as any).__paint(s, true, k), [src, k]);
      assert.deepEqual(paddingOnly(at800), [], what + ": painted at 800 px: exact");
      await page.evaluate((w: number) => (window as any).__width(w), 300);
      const stale: Mark[] = await page.evaluate(() => (window as any).__staleZero());
      assert.ok(stale.length >= k, what + ": narrowed to 300 px with no repaint: some blank marks are the padding alone at the new wrap points: " + stale.length);
      // the k marks around one collapsed blank all stand on it, the inner reading 0 over its contents and the outer ones the padding
      // of the marks inside them: the oracle lists every ring, and the contents reading would list the innermost alone
      assert.equal(stale.length % k, 0, what + ": the stale marks come in rings of " + k + ": " + stale.length);
      assert.equal(stale.filter((m) => m.holds === 0).length, stale.length / k, what + ": one innermost mark per collapsed blank, its contents at 0 px: " + JSON.stringify(stale.map((m) => m.w + "/" + m.holds)));
      assert.equal(stale.filter((m) => m.holds > 0 && m.w > 0).length, stale.length - stale.length / k, what + ": every ring around a ring reads its padding over its contents and 0 over its text");
      const retrimmed: Mark[] = await page.evaluate(() => (window as any).__retrim());
      assert.deepEqual(paddingOnly(retrimmed), [], what + ": after the re-trim no padding-only mark stands, at any depth");
      assert.ok(retrimmed.length <= at800.length - stale.length, what + ": the re-trim unwrapped the collapsed ones (and any the fixpoint's next pass found)");
      assert.deepEqual(retrimmed.filter((m) => !m.blank).map((m) => m.text), at800.filter((m) => !m.blank).map((m) => m.text), what + ": the non-blank marks all stand");
      await page.evaluate(() => (window as any).__unpaint());
    }
  });
});

// -- 4. the cost profile the panel pays ------------------------------------------------------------------------------------------
const PAIRS = 5;
/** The batched pass against the untrimmed one: about 1.0 to 1.1 on the build box (one layout and 400 measurements), bounded with
 *  room for a loaded runner; the unbatched pass measured about 4 (200 layouts) and is recorded, not bounded. */
const BATCH_BOUND = 2;

test("the panel's pass: 200 comments over a 300-paragraph note painted with the trim deferred and trimmed once cost within a bounded multiple of the untrimmed pass and paint the same marks as 200 paints each trimming its own", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (page) => {
    const r = await page.evaluate((pairs: number) => {
      const w = window as any;
      const words = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma tau upsilon".split(" ");
      const paras: string[] = [];
      for (let i = 0; i < 300; i++) paras.push(words.map((x, k) => (k % 7 === 3 ? "**" + x + i + "**" : k % 7 === 5 ? "*" + x + i + "*" : x + i)).join(" ") + ".");
      const src = "Intro para.\n\n" + paras.join("\n\n") + "\n\nAfter para.";
      w.__render(src, 800);
      // 200 comments, one per paragraph over `word **b** *i*`: from the word before the first bold run to the end of the italic run after it
      const ranges: Array<{ start: number; end: number }> = [];
      for (let i = 0; i < 200; i++) { const b = src.indexOf("**" + words[3] + i + "**"); const s = src.lastIndexOf(" ", b - 2) + 1; const it = src.indexOf("*" + words[5] + i + "*", b); ranges.push({ start: s, end: it + words[5].length + String(i).length + 2 }); }
      const unpaint = () => { const parents = new Set<Node>(); for (const n of Array.from(document.querySelectorAll("#md mark.fc-hl"))) { const p = n.parentNode!; parents.add(p); while (n.firstChild) p.insertBefore(n.firstChild, n); p.removeChild(n); } for (const p of parents) p.normalize(); };
      const md = document.getElementById("md")!;
      const shape = () => Array.from(md.querySelectorAll("mark.fc-hl")).map((k) => k.textContent).join("|");
      const pass = (mode: "untrimmed" | "batched" | "unbatched"): { ms: number; marks: number; shape: string } => {
        const t0 = performance.now();
        let all: Element[] = [];
        for (let i = 0; i < ranges.length; i++) { const marks = w.__romp.paintRendered(md, src, ranges[i], "fc-hl", { id: "c" + i }, { trim: mode === "unbatched" }) || []; if (mode === "batched") all = all.concat(marks); }
        if (mode === "batched") all = w.__romp.trimCollapsedMarks(all);
        void md.offsetHeight;                                                   // the layout the panel's placement reads next
        const t1 = performance.now();
        const out = { ms: t1 - t0, marks: md.querySelectorAll("mark.fc-hl").length, shape: shape() };
        unpaint();
        return out;
      };
      pass("untrimmed"); pass("batched"); pass("unbatched");                     // warm (the source table, the JIT)
      const ratiosB: number[] = [], ratiosU: number[] = []; let shapes: { untrimmed: string; batched: string; unbatched: string } | null = null; let counts: Record<string, number> | null = null;
      for (let i = 0; i < pairs; i++) {
        const u = pass("untrimmed"), b = pass("batched"), n = pass("unbatched");
        ratiosB.push(b.ms / u.ms); ratiosU.push(n.ms / u.ms);
        if (!shapes) { shapes = { untrimmed: u.shape, batched: b.shape, unbatched: n.shape }; counts = { untrimmed: u.marks, batched: b.marks, unbatched: n.marks }; }
      }
      const med = (a: number[]) => { const c = a.slice().sort((x, y) => x - y); return c[Math.floor(c.length / 2)]; };
      return { counts, sameShape: shapes!.batched === shapes!.unbatched, batched: Math.round(med(ratiosB) * 100) / 100, unbatched: Math.round(med(ratiosU) * 100) / 100, ratiosB: ratiosB.map((x) => Math.round(x * 100) / 100) };
    }, PAIRS);
    assert.ok(r.counts.untrimmed >= 600, "200 comments of three or four marks each: " + JSON.stringify(r.counts));
    assert.ok(r.sameShape, "the batched pass and the unbatched pass paint the same marks");
    assert.ok(r.counts.batched <= r.counts.untrimmed, "the trim never adds a mark");
    assert.ok(r.batched <= BATCH_BOUND, "the batched pass against the untrimmed one: pair ratios " + r.ratiosB.join(" ") + ", median " + r.batched + " over the bound " + BATCH_BOUND + " (the unbatched pass, a layout per comment, measured " + r.unbatched + ")");
  });
});

// -- 5. the oracle's own check ---------------------------------------------------------------------------------------------------
test("the padding-only oracle lists a ring around a collapsed mark's ring: an outer mark hand-wrapped around a collapsed blank mark, and a third around that, read 4 and 8 px over their contents (the inner marks' padding) and 0 over their text, and all three are listed", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (page) => {
    const [, src] = WRAPS[0];
    await page.evaluate(([s, w]: [string, number]) => (window as any).__render(s, w), [src, 300]);
    const rings: Mark[] | null = await page.evaluate((s: string) => (window as any).__nest(s), src);
    assert.ok(rings, "the untrimmed paint at 300 px has a collapsed blank mark to wrap (the list item wraps at a space there)");
    const [inner, outer, third] = rings!;
    assert.deepEqual(rings!.map((m) => [m.blank, m.wt, m.own > 0, m.holds]), [[true, 0, true, 0], [true, 0, true, 1], [true, 0, true, 2]], "three blank marks on one collapsed blank, each with a box of its own, 0 px of text, nested one in the next");
    assert.equal(inner.w, 0, "the innermost mark's contents read 0 px (the collapsed blank)");
    assert.ok(outer.w > 0 && third.w > outer.w, "the rings' contents read the padding of the marks inside them, never 0: " + outer.w + " and " + third.w + " px (a contents oracle lists neither)");
    assert.equal(paddingOnly(rings!).length, 3, "the oracle lists all three: " + JSON.stringify(paddingOnly(rings!)));
    await page.evaluate(() => (window as any).__unpaint());
  });
});
