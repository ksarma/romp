// The comments painter's layout-time trim (anchor-map.ts trimCollapsedMarks, the Slice 4 review's round 12) over the REAL bundle in
// headless Chromium: marked with the one configuration (md-config.ts), the sanitizer (md-sanitize.ts) and paintRendered, the DOM
// built as the viewer's mdBlock builds it, laid out under the whole of feed.css at 14px sans-serif. The scenes are the union the
// review's rounds 7 to 12 collected (anchor-map-fixtures/blank-scenes.json: folds, an author's figure, details, dl and center,
// badge rows, br pairs, wrap points at several widths, a nbsp and an ideographic space, U+FEFF and the zero-width and bidi
// characters, svg icons, audio with and without controls, an author pre with br and block children, tables, footnote
// definitions, list items, a form feed, a CRLF, a floated image, a picture without an image, ruby and rp, a space inside a kbd, a
// table caption, and a plain note), each painted from the paragraph before to the paragraph after at its width. No expected
// marks are recorded anywhere: the browser's layout is the oracle, read after the paint.
// 1. Every scene: the trimmed paint's non-blank marks are the untrimmed paint's (the trim removes blank marks alone); no blank mark
//    of zero content width stands (the padding-only box, 4 x 16 px on this page, rounds 7 to 11's defect) unless the mark has no
//    box of its own (a hidden ancestor); every blank text node below the top level that renders with a width in the painted layout
//    carries a mark (no ring gap at a rendered blank) in the scenes at 800 px, which are wrap-free by construction, and in the wrap
//    scenes at a narrower width point 2's bound holds; no mark is a top-level node; the panel's unpaint restores the exact HTML
//    after either paint; on the plain note the trim unwraps nothing.
// 2. The wrap points: the list item and the paragraph of fourteen links painted at 800, 500, 300, 260, 240, 220, 200 and 180 px:
//    no padding-only mark at any width after the fixpoint (a mark's 2 px side padding is in the layout, so the paint moves the wrap
//    points and the trim measures again after a pass that unwrapped something), and the wrap points' blanks unwrapped. The
//    fixpoint's price, recorded and bounded: a blank unwrapped as collapsed can render once a later unwrap on its line moves the
//    wrap point back, and it is never re-wrapped (a mark at a line's last inch would flip with every pass), so at a tight width a
//    rendered space may stand unmarked, a ring gap of the space's width (the list item at 240 px shows one on the build box); never
//    more such blanks than marks unwrapped, and none at all where nothing was unwrapped. The layout-neutral mark (`margin: 0 -2px`
//    beside the padding) removes the shape and is the owner's call (plans/markdown-viewer.md, item 10).
// 3. The reflow: marks painted at 800 px and the root narrowed to 300 px with no repaint (the panel does not repaint on a reflow)
//    show padding-only marks at the new wrap points until trimCollapsedMarks runs over them again, the panel's re-trim
//    (file-comments.ts trimBlanks on the seam's "reflow"); after it none stands. A blank trimmed at 800 px that renders at 300 px
//    stays unmarked until the next paint pass, the recorded stale shape.
// 4. The cost profile the panel pays (round 12's prototype measured it on this shape): 300 paragraphs of twenty words with bold and
//    italic runs, 200 comments across `word **b** *i*` (two blank marks each); the batched pass (every paint with `trim: false`,
//    one trimCollapsedMarks over every mark) against the untrimmed pass, the median of PAIRS pair ratios bounded at BATCH_BOUND
//    (about 1.0 to 1.1 on the build box: one layout for the pass), and the unbatched pass (a trim per paint, one layout each)
//    recorded in the failure text; the batched and the unbatched pass paint the same marks.
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
 *  or symbol, or the hangul fillers. `__paint` paints the whole range with or without the trim and reads each mark's text, its
 *  content width (a Range over its contents, the rects' widths summed), whether it has a box of its own and whether it is a
 *  top-level node; `__bare` lists the blank text nodes below the top level that render with a width and carry no mark, inside the
 *  top-level blocks the paint reached (a block the pairing refused holds no mark and is no unmarked blank of the trim's: the union
 *  holds one such scene, an html block whose stripped text equals the list item's after it, the pairing's own recorded defect);
 *  `__unpaint` is the panel's (children back, the parent normalized) and returns the HTML. */
const HELPERS = `
const BLANK = /^(?:[^\\p{L}\\p{N}\\p{P}\\p{S}]|[\\u115f\\u1160\\u3164\\uffa0])*$/u;
const md = () => document.getElementById("md");
const width = (n) => { const r = document.createRange(); r.selectNodeContents(n); let w = 0; for (const b of Array.from(r.getClientRects())) w += b.width; return Math.round(w * 100) / 100; };
const range = (src) => ({ start: src.indexOf("Intro para."), end: src.indexOf("After para.") + "After para.".length });
window.__render = (src, w) => { const m = md(); m.style.width = w + "px"; m.replaceChildren(...Array.from(window.__romp.sanitizeMd(window.__romp.marked.parse(src)).childNodes)); return m.innerHTML; };
window.__width = (w) => { md().style.width = w + "px"; return md().getBoundingClientRect().width; };
const readMark = (k) => ({ text: k.textContent, blank: BLANK.test(k.textContent), w: width(k), own: k.getClientRects().length, top: k.parentNode === md() });
window.__paint = (src, trim) => { const marks = window.__romp.paintRendered(md(), src, range(src), "fc-hl", { id: "c1" }, { trim }) || []; window.__marks = marks; return marks.map(readMark); };
window.__retrim = () => { window.__marks = window.__romp.trimCollapsedMarks(window.__marks.filter((k) => k.isConnected)); return window.__marks.map(readMark); };
window.__staleZero = () => window.__marks.filter((k) => BLANK.test(k.textContent) && width(k) === 0 && k.getClientRects().length > 0).map((k) => k.textContent);
const topOf = (n) => { let c = n; while (c.parentNode && c.parentNode !== md()) c = c.parentNode; return c; };
window.__bare = () => { const out = []; const w = document.createTreeWalker(md(), NodeFilter.SHOW_TEXT);
  for (let t = w.nextNode(); t; t = w.nextNode()) { if (t.parentNode === md() || !BLANK.test(t.data)) continue;
    // a blank in a block the paint never reached (an html block the pairing refused, its marks none) is no unmarked blank of the trim's
    const top = topOf(t); if (!(top.querySelector && top.querySelector("mark.fc-hl"))) continue;
    if (width(t) > 0 && !(t.parentElement && t.parentElement.closest("mark"))) out.push({ parent: t.parentNode.tagName, text: t.data, w: width(t) }); }
  return out; };
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
      if (/\.(png|gif|jpg|avif|webp)$/i.test(u.pathname)) return route.fulfill({ status: 200, contentType: "image/png", body: PNG });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/page");
    await page.waitForFunction(() => !!(window as any).__romp && !!(window as any).__paint);
    await body(page);
    assert.deepEqual(errors, [], "no page errors");
  } finally { await browser.close(); }
}
type Mark = { text: string; blank: boolean; w: number; own: number; top: boolean };
type Bare = { parent: string; text: string; w: number };
/** A mark's text for a message, every character past ASCII spelt as its escape (the blanks are invisible otherwise). */
const show = (s: string): string => JSON.stringify(s).replace(/[^\x00-\x7f]/g, (c) => "\\u" + c.charCodeAt(0).toString(16).padStart(4, "0"));
/** The blank marks of zero content width that have a box of their own: the padding-only marks. */
const paddingOnly = (marks: Mark[]): string[] => marks.filter((m) => m.blank && m.w === 0 && m.own > 0).map((m) => show(m.text));
/** Render at `width`, paint untrimmed and trimmed, hold point 1's properties, and return both paints' marks and the bare blanks. */
async function drive(page: any, what: string, src: string, width: number): Promise<{ untrimmed: Mark[]; trimmed: Mark[]; bare: Bare[] }> {
  const fresh: string = await page.evaluate(([s, w]: [string, number]) => (window as any).__render(s, w), [src, width]);
  const untrimmed: Mark[] = await page.evaluate((s: string) => (window as any).__paint(s, false), src);
  assert.ok(untrimmed.length, what + ": painted");
  for (const m of untrimmed) assert.ok(!m.top, what + ": no top-level mark (untrimmed): " + show(m.text));
  assert.equal(await page.evaluate(() => (window as any).__unpaint()), fresh, what + ": the unpaint after the untrimmed paint restores the HTML");
  const trimmed: Mark[] = await page.evaluate((s: string) => (window as any).__paint(s, true), src);
  const bare: Bare[] = await page.evaluate(() => (window as any).__bare());
  assert.deepEqual(trimmed.filter((m) => !m.blank).map((m) => m.text), untrimmed.filter((m) => !m.blank).map((m) => m.text), what + ": the trim removes blank marks alone");
  assert.deepEqual(paddingOnly(trimmed), [], what + ": no blank mark of zero width with a box of its own (the padding-only box)");
  for (const m of trimmed) assert.ok(!m.top, what + ": no top-level mark: " + show(m.text));
  assert.equal(await page.evaluate(() => (window as any).__unpaint()), fresh, what + ": the unpaint after the trimmed paint restores the HTML");
  return { untrimmed, trimmed, bare };
}

// -- 1. every scene of the union ---------------------------------------------------------------------------------------------
test("every scene of the union: the trim removes blank marks alone, leaves no padding-only mark and no rendered blank unmarked, no top-level mark, the unpaint exact; the plain note is painted as without the trim", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (page) => {
    assert.ok(SCENES.length >= 90, "the fixture holds the union: " + SCENES.length + " scenes");
    let trimmedSomething = 0;
    for (const sc of SCENES) {
      const what = sc.name + " @" + sc.width + "px";
      const { untrimmed, trimmed, bare } = await drive(page, what, sc.markdown, sc.width);
      // wrap-free at 800 px by construction, so every rendered blank carries a mark there; a scene at a narrower width is a wrap
      // scene, where the fixpoint's price applies (point 2): a rendered blank unmarked only where a mark was unwrapped, never more
      if (sc.width >= 800) assert.deepEqual(bare.map((b) => b.parent + " " + show(b.text) + " " + b.w), [], what + ": every blank below the top level that renders in the painted layout carries a mark");
      else assert.ok(bare.length <= untrimmed.length - trimmed.length, what + ": a rendered blank unmarked only where a mark was unwrapped: " + JSON.stringify(bare.map((b) => b.parent + " " + show(b.text) + " " + b.w)) + " against " + (untrimmed.length - trimmed.length) + " unwrapped");
      if (trimmed.length < untrimmed.length) trimmedSomething++;
      if (sc.name.startsWith("plain note")) assert.deepEqual(trimmed.map((m) => m.text), untrimmed.map((m) => m.text), what + ": the trim unwraps nothing on the plain note");
    }
    assert.ok(trimmedSomething >= 30, "the trim unwrapped something in most collapsed scenes: " + trimmedSomething + " of " + SCENES.length);
  });
});

// -- 2. the wrap points at several widths ----------------------------------------------------------------------------------------
const LINKS = Array.from({ length: 14 }, (_, i) => "[Link" + i + " docs](#l" + i + ")").join(" ");
const WRAPS: Array<[string, string]> = [["the list item of fourteen links", "Intro para.\n\n- " + LINKS + "\n\nAfter para."], ["the paragraph of fourteen links", "Intro para.\n\n" + LINKS + "\n\nAfter para."]];
const WIDTHS = [800, 500, 300, 260, 240, 220, 200, 180];

test("the wrap points: a list item and a paragraph of fourteen links painted at eight widths from 800 to 180 px leave no padding-only mark after the fixpoint and unwrap the wrap points' blanks; a rendered blank left unmarked is bounded by the unwraps (the fixpoint's price, recorded)", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (page) => {
    for (const [why, src] of WRAPS) {
      for (const w of WIDTHS) {
        const what = why + " @" + w + "px";
        const { untrimmed, trimmed, bare } = await drive(page, what, src, w);
        const kept = trimmed.filter((m) => m.blank).length, all = untrimmed.filter((m) => m.blank).length, unwrapped = all - kept;
        assert.ok(kept <= all && (w >= 800 || unwrapped > 0), what + ": at a narrow width the wrap points' blanks are unwrapped (" + kept + " of " + all + " blank marks kept)");
        assert.ok(bare.length <= unwrapped, what + ": a rendered blank left unmarked is one the fixpoint unwrapped and a later unwrap brought back onto its line, never more than the unwraps: " + JSON.stringify(bare.map((b) => b.parent + " " + show(b.text) + " " + b.w)) + " against " + unwrapped + " unwrapped");
        if (w >= 800) assert.deepEqual(bare, [], what + ": nothing unwrapped, so no rendered blank unmarked");
      }
    }
  });
});

// -- 3. the reflow: marks painted at one width, the root narrowed, the re-trim ----------------------------------------------------
test("marks painted at 800 px and reflowed to 300 px with no repaint show padding-only marks at the new wrap points; trimCollapsedMarks over the standing marks (the panel's re-trim on a reflow) leaves none", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (page) => {
    const [, src] = WRAPS[0];
    await page.evaluate(([s, w]: [string, number]) => (window as any).__render(s, w), [src, 800]);
    const at800: Mark[] = await page.evaluate((s: string) => (window as any).__paint(s, true), src);
    assert.deepEqual(paddingOnly(at800), [], "painted at 800 px: exact");
    await page.evaluate((w: number) => (window as any).__width(w), 300);
    const staleZero: string[] = await page.evaluate(() => (window as any).__staleZero());
    assert.ok(staleZero.length >= 1, "narrowed to 300 px with no repaint: some blank marks are the padding alone at the new wrap points: " + staleZero.length);
    const retrimmed: Mark[] = await page.evaluate(() => (window as any).__retrim());
    assert.deepEqual(paddingOnly(retrimmed), [], "after the re-trim no padding-only mark stands");
    assert.ok(retrimmed.length <= at800.length - staleZero.length, "the re-trim unwrapped the collapsed ones (and any the fixpoint's next pass found)");
    assert.deepEqual(retrimmed.filter((m) => !m.blank).map((m) => m.text), at800.filter((m) => !m.blank).map((m) => m.text), "the non-blank marks all stand");
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
