// The comments painter's layout-time trim (anchor-map.ts trimCollapsedMarks) after the Slice 4 review's round 13, over the REAL
// bundle in headless Chromium: marked with the one configuration (md-config.ts), the sanitizer (md-sanitize.ts), paintRendered and
// the trim, the DOM built as the viewer's mdBlock builds it, laid out under the whole of feed.css at 14px sans-serif. Three legs, each
// the browser half of md-config-paint-trim-fixpoint.test.ts:
// 1. The fixpoint runs to convergence. A mark's 2 px side padding is in the layout, so each pass that unwraps the wrap points'
//    marks moves the wrap points and collapses another set of blanks, and on an inline-heavy passage the cascade runs for many
//    passes (the paragraph of 5,000 links: eight fresh at 700 px, twelve after a narrowing from 800 to 400 px on the build box).
//    Round 12 stopped after three and left hundreds of padding-only marks (4 x 18 px ringed boxes at the wrap points) at every
//    width but the 800 px the tests pinned: 366 fresh at 700 px, 406 at 400, 271 at 300; after a narrowing 800 to 400 px 266 and
//    800 to 300 px 652. The leg paints the 120-link list item and the 5,000-link paragraph at 800, 700, 500, 400 and 300 px, fresh
//    and narrowed from 800 px with one re-trim (the panel's reflow shape), and holds zero padding-only marks at every width, no call
//    reaching the safety cap (TRIM_STATS), and that the paragraph's cascade does run past three passes here. A rendered blank left
//    unmarked (the fixpoint's recorded price, plan item 10 (a)) is counted and reported, not bounded: the cost of the pathological
//    paragraph is recorded, not optimised (the plan). A second pass at the same width (the marks unpainted, the passage painted and
//    trimmed again: the panel's next paint pass with the pane's width unchanged) is held equal to the first in its pass count, the
//    blank marks it keeps and the rendered blanks it leaves bare, since the same layout runs the same cascade: the price is not one
//    a later pass repays, and a gap stands while the pane keeps the width (the Slice 4 review, round 16; anchor-map.ts's header).
// 2. Overlapping comments. k comments over one passage nest their marks (the later paint wraps the text node where it stands, inside
//    the earlier comment's mark); a Range over an outer mark's contents reads the inner MARK element's border box, 4 px a level, so
//    round 12's measurement peeled a nest one level per pass and four or more comments over a wrap point left ringed boxes inside
//    one another at the cap. The trim now measures each mark's text nodes: one, two, four and eight comments over the fourteen-link
//    item at 300 px, painted as the panel paints them (every comment with the trim deferred, one trim over the pass), leave no
//    padding-only mark at any level, fresh and after a narrowing from 800 px.
// 3. An author's pre. Under white-space: pre nothing collapses, so spaces or a tab between two block children render a line of
//    their own (16.86 and 67.44 px at this size); round 12's block-neighbour pre-skip skipped them unmeasured, a ring gap inside the
//    pre. Each is painted and keeps its mark; a newline alone is painted, measured at zero and unwrapped; every rendered blank under
//    the pre carries a mark and no padding-only mark stands.
// The oracle is the trim's own reading, a Range over each text node of a mark (a Range over the mark's contents would miss an outer
// ring, point 2). Skips LOUDLY without a playwright browser (CI installs none). Synthetic prose, no paths.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
const requireCjs = createRequire(path.join(EXT, "package.json"));  // playwright and esbuild from the extension, wherever the bundle lands
const UI = path.resolve(EXT, "..", "ui", "webview");
const FEED = fs.readFileSync(path.join(UI, "feed.css"), "utf8");

/** marked with the viewer's grammar, the sanitizer, the paint and the trim with its record, bundled as the webview build bundles them. */
function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: {
      contents: 'import { marked } from "marked";\nimport { applyMdConfig } from "./md-config";\nimport { sanitizeMd } from "./md-sanitize";\n'
        + 'import { paintRendered, trimCollapsedMarks, TRIM_STATS, TRIM_PASSES_MAX } from "./anchor-map";\n'
        + 'applyMdConfig();\n(window as any).__romp = { marked, sanitizeMd, paintRendered, trimCollapsedMarks, TRIM_STATS, TRIM_PASSES_MAX };\n',
      resolveDir: UI, loader: "ts", sourcefile: "paint-trim-fixpoint-probe.ts",
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

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

/** The page's helpers. BLANK is the trim's candidate alphabet (anchor-map.ts TRIM_CANDIDATE). `textW` is the trim's own reading of a
 *  mark, a Range over each of its text nodes with the rects' widths summed; `__paint` paints k comments over the whole range as the
 *  panel paints a pass (every one with the trim deferred, then ONE trimCollapsedMarks over every mark of the pass); `__retrim` is the
 *  panel's reflow re-trim over the standing marks; `__read` counts the standing blank marks, the padding-only ones (text at zero
 *  width, a box of their own), the deepest nest of marks, the rendered blanks below the top level without a mark, and the record. */
const HELPERS = `
const BLANK = /^(?:[^\\p{L}\\p{N}\\p{P}\\p{S}]|[\\u115f\\u1160\\u3164\\uffa0])*$/u;
const md = () => document.getElementById("md");
const rectsW = (n) => { const r = document.createRange(); r.selectNodeContents(n); let w = 0; for (const b of Array.from(r.getClientRects())) w += b.width; return w; };
const textW = (k) => { let w = 0; const walk = document.createTreeWalker(k, NodeFilter.SHOW_TEXT); for (let t = walk.nextNode(); t; t = walk.nextNode()) w += rectsW(t); return Math.round(w * 100) / 100; };
const ownW = (k) => { let w = 0; for (const b of Array.from(k.getClientRects())) w += b.width; return Math.round(w * 100) / 100; };
const range = (src) => ({ start: src.indexOf("Intro para."), end: src.indexOf("After para.") + "After para.".length });
window.__render = (src, w) => { const m = md(); m.style.width = w + "px"; m.replaceChildren(...Array.from(window.__romp.sanitizeMd(window.__romp.marked.parse(src)).childNodes)); return m.innerHTML; };
window.__width = (w) => { md().style.width = w + "px"; return md().getBoundingClientRect().width; };
window.__paint = (src, k) => {
  const t0 = performance.now(); const all = [];
  for (let i = 0; i < k; i++) all.push(...(window.__romp.paintRendered(md(), src, range(src), "fc-hl", { id: "c" + i }, { trim: false }) || []));
  const t1 = performance.now(); const untrimmedBlank = all.filter((m) => BLANK.test(m.textContent || "")).map((m) => m.textContent);
  window.__marks = window.__romp.trimCollapsedMarks(all); const t2 = performance.now();
  return { paintMs: Math.round(t1 - t0), trimMs: Math.round(t2 - t1), passes: window.__romp.TRIM_STATS.passes, untrimmedBlank }; };
window.__retrim = () => { const t0 = performance.now(); window.__marks = window.__romp.trimCollapsedMarks(window.__marks.filter((k) => k.isConnected)); return { trimMs: Math.round(performance.now() - t0), passes: window.__romp.TRIM_STATS.passes }; };
window.__read = () => {
  const marks = Array.from(md().querySelectorAll("mark.fc-hl"));
  const blanks = marks.filter((k) => BLANK.test(k.textContent || ""));
  const paddingOnly = blanks.filter((k) => textW(k) === 0 && k.getClientRects().length > 0);
  const nest = (k) => { let d = 0; for (let e = k; e && e.tagName === "MARK"; e = e.parentElement) d++; return d; };
  const bare = []; const w = document.createTreeWalker(md(), NodeFilter.SHOW_TEXT);
  for (let t = w.nextNode(); t; t = w.nextNode()) { if (t.parentNode === md() || !BLANK.test(t.data)) continue; if (rectsW(t) > 0 && !(t.parentElement && t.parentElement.closest("mark"))) bare.push(t.parentNode.tagName + " " + JSON.stringify(t.data)); }
  return { marks: marks.length, blankMarks: blanks.length, blankTexts: blanks.map((k) => k.textContent), paddingOnly: paddingOnly.length,
    sample: paddingOnly.slice(0, 3).map((k) => k.parentElement.tagName + " own " + ownW(k) + " contents " + Math.round(rectsW(k) * 100) / 100 + " nest " + nest(k)),
    maxNest: Math.max(0, ...marks.map(nest)), bare, capped: window.__romp.TRIM_STATS.capped, cap: window.__romp.TRIM_PASSES_MAX }; };
window.__unpaint = () => { const parents = new Set(); for (const n of Array.from(md().querySelectorAll("mark.fc-hl"))) { const p = n.parentNode; parents.add(p); while (n.firstChild) p.insertBefore(n.firstChild, n); p.removeChild(n); } for (const p of parents) p.normalize(); return md().innerHTML; };
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
type Paint = { paintMs: number; trimMs: number; passes: number; untrimmedBlank: string[] };
type Read = { marks: number; blankMarks: number; blankTexts: string[]; paddingOnly: number; sample: string[]; maxNest: number; bare: string[]; capped: number; cap: number };
const render = (page: any, src: string, w: number): Promise<string> => page.evaluate(([s, x]: [string, number]) => (window as any).__render(s, x), [src, w]);
const paint = (page: any, src: string, k: number): Promise<Paint> => page.evaluate(([s, n]: [string, number]) => (window as any).__paint(s, n), [src, k]);
const narrow = (page: any, w: number): Promise<number> => page.evaluate((x: number) => (window as any).__width(x), w);
const retrim = (page: any): Promise<{ trimMs: number; passes: number }> => page.evaluate(() => (window as any).__retrim());
const read = (page: any): Promise<Read> => page.evaluate(() => (window as any).__read());
const unpaint = (page: any): Promise<void> => page.evaluate(() => { (window as any).__unpaint(); });
const wrap = (block: string): string => "Intro para.\n\n" + block + "\n\nAfter para.";
/** A mark's text for a message, every character past ASCII spelt as its escape (the blanks are invisible otherwise). */
const show = (s: string): string => JSON.stringify(s).replace(/[^\x00-\x7f]/g, (c) => "\\u" + c.charCodeAt(0).toString(16).padStart(4, "0"));

// -- 1. the fixpoint at five widths ------------------------------------------------------------------------------------------------
const PARA = wrap(Array.from({ length: 5000 }, (_, i) => "[w" + i + "](#a" + i + ")").join(" "));
const ITEM = wrap("- " + Array.from({ length: 120 }, (_, i) => "[Link" + i + " docs](#l" + i + ")").join(" "));
const WIDTHS = [800, 700, 500, 400, 300];

test("the fixpoint runs to convergence: one comment across the 120-link item and across the 5,000-link paragraph leaves no padding-only mark at 800, 700, 500, 400 or 300 px, fresh or narrowed from 800 px with one re-trim; the paragraph's cascade runs past three passes; no call reaches the safety cap; a second pass at the same width takes the same passes, keeps the same blank marks and leaves the same rendered blanks bare", { timeout: 900000 }, async (t) => {
  await inBrowser(t, async (page) => {
    for (const [why, src] of [["the list item of 120 links", ITEM], ["the paragraph of 5,000 links", PARA]] as Array<[string, string]>) {
      let maxPasses = 0;
      for (const w of WIDTHS) {
        await render(page, src, w);
        const p = await paint(page, src, 1);
        const r = await read(page);
        const what = why + " fresh @" + w + "px";
        assert.ok(r.blankMarks > 0, what + ": blank marks stand (the rendered spaces between the links)");
        assert.equal(r.paddingOnly, 0, what + ": no padding-only mark after the fixpoint (" + p.passes + " passes): " + JSON.stringify(r.sample));
        assert.equal(r.capped, 0, what + ": no call reached the cap of " + r.cap);
        maxPasses = Math.max(maxPasses, p.passes);
        t.diagnostic(what + ": " + p.passes + " passes, paint " + p.paintMs + " ms, trim " + p.trimMs + " ms, " + p.untrimmedBlank.length + " blank marks painted, " + r.blankMarks + " kept, " + r.bare.length + " rendered blanks bare (the recorded price)");
        // the next paint pass at the same width: the marks unpainted (the panel's unpaint normalizes the text nodes too), the passage
        // painted and trimmed again over the same layout. The same cascade runs, so a blank the first pass left bare is bare after the
        // second as well: the recorded price is the width's, not the pass's, and nothing short of a layout change or the layout-neutral
        // mark mends it (anchor-map.ts's header, the fixpoint bullet; the counts are diagnostics, the equality is the assertion)
        await unpaint(page);
        const p2 = await paint(page, src, 1);
        const r2 = await read(page);
        assert.equal(p2.passes, p.passes, what + ": a second pass at the same width takes the same passes");
        assert.equal(r2.blankMarks, r.blankMarks, what + ": a second pass keeps the same blank marks");
        assert.deepEqual(r2.bare, r.bare, what + ": a second pass leaves the same rendered blanks bare (" + r.bare.length + " after the first)");
        assert.equal(r2.paddingOnly, 0, what + ": no padding-only mark after the second pass: " + JSON.stringify(r2.sample));
        assert.equal(r2.capped, 0, what + ": the second pass did not reach the cap");
        t.diagnostic(what + ", second pass: " + p2.passes + " passes, trim " + p2.trimMs + " ms, " + r2.blankMarks + " kept, " + r2.bare.length + " bare");
      }
      for (const w of WIDTHS.slice(1)) {
        await render(page, src, 800);
        await paint(page, src, 1);
        await narrow(page, w);
        const stale = await read(page);
        const rt = await retrim(page);
        const r = await read(page);
        const what = why + " narrowed 800 -> " + w + "px";
        assert.equal(r.paddingOnly, 0, what + ": no padding-only mark after the re-trim (" + rt.passes + " passes; " + stale.paddingOnly + " stood before it): " + JSON.stringify(r.sample));
        assert.equal(r.capped, 0, what + ": no call reached the cap of " + r.cap);
        maxPasses = Math.max(maxPasses, rt.passes);
        t.diagnostic(what + ": " + stale.paddingOnly + " padding-only before the re-trim, " + rt.passes + " passes, " + rt.trimMs + " ms, " + r.blankMarks + " blank marks kept, " + r.bare.length + " bare");
      }
      if (why.indexOf("5,000") >= 0) assert.ok(maxPasses > 3, why + ": the cascade runs past round 12's three passes at one of the widths (the shape the cap cut): " + maxPasses);
    }
  });
});

// -- 2. overlapping comments -------------------------------------------------------------------------------------------------------
const ITEM14 = wrap("- " + Array.from({ length: 14 }, (_, i) => "[Link" + i + " docs](#l" + i + ")").join(" "));

test("overlapping comments: one, two, four and eight comments over the fourteen-link item nest their marks one level per comment, and at 300 px the pass's one trim leaves no padding-only mark at any level (the text measurement drops a nest together), fresh and after a narrowing from 800 px", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (page) => {
    for (const k of [1, 2, 4, 8]) {
      await render(page, ITEM14, 300);
      const p = await paint(page, ITEM14, k);
      const r = await read(page);
      const what = k + " comment" + (k > 1 ? "s" : "") + " over the item @300px";
      assert.equal(r.maxNest, k, what + ": the marks nest one level per comment");
      assert.ok(p.untrimmedBlank.length >= 13 * k, what + ": every comment painted the thirteen spaces: " + p.untrimmedBlank.length);
      assert.ok(r.blankMarks < p.untrimmedBlank.length, what + ": the wrap points' blanks were unwrapped: " + r.blankMarks + " of " + p.untrimmedBlank.length + " kept");
      assert.equal(r.paddingOnly, 0, what + ": no padding-only mark at any level after " + p.passes + " passes: " + JSON.stringify(r.sample));
      assert.equal(r.capped, 0, what + ": not capped");
      t.diagnostic(what + ": " + p.passes + " passes, " + r.blankMarks + " blank marks kept of " + p.untrimmedBlank.length + ", " + r.bare.length + " bare");
      // painted wide, narrowed to 300 px, one re-trim: the reflow shape
      await render(page, ITEM14, 800);
      await paint(page, ITEM14, k);
      await narrow(page, 300);
      const stale = await read(page);
      const rt = await retrim(page);
      const n = await read(page);
      const whatN = what.replace("@300px", "narrowed 800 -> 300px");
      assert.equal(n.maxNest, k, whatN + ": the marks still nest");
      assert.equal(n.paddingOnly, 0, whatN + ": no padding-only mark at any level after the re-trim (" + rt.passes + " passes; " + stale.paddingOnly + " stood before it): " + JSON.stringify(n.sample));
      assert.equal(n.capped, 0, whatN + ": not capped");
    }
  });
});

// -- 3. an author's pre -----------------------------------------------------------------------------------------------------------
const PRE_SCENES: Array<[string, string, string]> = [
  ["two spaces between two divs of a pre", "<pre><div>a</div>  <div>b</div></pre>", "  "],
  ["two spaces before the first div of a pre", "<pre>  <div>a</div></pre>", "  "],
  ["a newline and two spaces between two divs of a pre", "<pre><div>a</div>\n  <div>b</div></pre>", "\n  "],
  ["a tab between two divs of a pre", "<pre><div>a</div>\t<div>b</div></pre>", "\t"],
];

test("under an author's pre a blank of spaces or a tab between block children renders a line of its own and keeps its mark (round 12's pre-skip left it bare), a newline alone is unwrapped at zero width; every rendered blank under the pre carries a mark and no padding-only mark stands", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (page) => {
    for (const [why, block, blank] of PRE_SCENES) {
      const src = wrap(block);
      const html = await render(page, src, 800);
      assert.ok(html.indexOf(block) >= 0, why + ": the html block passes through the sanitizer intact: " + html);
      const p = await paint(page, src, 1);
      const r = await read(page);
      assert.deepEqual(p.untrimmedBlank, [blank], why + ": the blank is painted before the trim (not skipped by the pre-skip)");
      assert.deepEqual(r.blankTexts, [blank], why + ": the blank keeps its mark after the trim, rendered at a width");
      assert.deepEqual(r.bare, [], why + ": every rendered blank under the pre carries a mark");
      assert.equal(r.paddingOnly, 0, why + ": no padding-only mark");
    }
    // a newline alone between the divs: painted, a forced break of zero width, unwrapped
    const nl = wrap("<pre><div>a</div>\n<div>b</div></pre>");
    await render(page, nl, 800);
    const p = await paint(page, nl, 1);
    const r = await read(page);
    assert.deepEqual(p.untrimmedBlank, ["\n"], "the newline is painted before the trim");
    assert.deepEqual(r.blankTexts, [], "the newline's mark is unwrapped at zero width");
    assert.deepEqual(r.bare, [], "no rendered blank bare");
    assert.equal(r.paddingOnly, 0);
    // the control: the same blank outside a pre is collapsed and no mark stands
    const ctl = wrap("<div><div>a</div>  <div>b</div></div>");
    await render(page, ctl, 800);
    const cp = await paint(page, ctl, 1);
    const cr = await read(page);
    assert.deepEqual(cp.untrimmedBlank, [], "outside a pre the blank between two blocks is the pre-skip's, unpainted");
    assert.deepEqual(cr.bare, [], "and renders nothing: " + show(JSON.stringify(cr.bare)));
    assert.equal(cr.paddingOnly, 0);
  });
});
