// The whitespace rule of the Rendered paint (anchor-map.ts skipBlockWs), over the REAL bundle in headless Chromium: marked with
// the one configuration (md-config.ts), the sanitizer (md-sanitize.ts) and paintRendered, the DOM built as the viewer's mdBlock
// builds it. Three legs (the Slice 4 review, round 9):
// 1. BLOCK_BOXES, the tags a whitespace-only text node is skipped beside, is DERIVED here and held equal to the shipped set: every
//    tag the sanitizer keeps (DOMPurify's allowlist under MD_PURIFY, read off the instance itself through its element hook, less
//    MD_FORBID_TAGS) that Chromium lays out as a block-level box or a table or one of a table's parts (the computed display of the
//    element under the viewer's prose root), the document's own html and body left out, which the parser never places in a
//    fragment. Round 8 wrote the list by hand and left out center, dir, menu and search while naming form and fieldset, which the
//    sanitizer strips; a list read from the sanitizer and the browser cannot drift from either. The leg also holds the checked-in
//    fixture anchor-map-fixtures/block-tags.json (the Rendering section's block-level tags) to Chromium over every kept tag, in
//    both directions and to the display named, since md-config-block-boxes.test.ts pins the set to that fixture in node, where CI
//    runs and this leg skips (round 10).
// 2. A highlight from the paragraph before an author's html block to the paragraph after it paints the block's text and no
//    whitespace-only mark, and moves nothing: the "\n" between a figure or a details and its image (the parent's edge, an inline
//    neighbour), the "\n\n" beside a center, menu, dir or search, and the "\n" between two <br>s each painted an empty ringed box
//    before (4 x 16 px on this page's 14px/1.5 sans-serif; 4 x 18 on the viewer's sheet), the figure or details taller by a line.
//    The layout is read box for box, unpainted against painted and again after the panel's unpaint and a repaint; the controls
//    (a space inside an inline element beside an image, mid-line and rendered; a figure whose body is a paragraph) hold the
//    rule's two sides.
// 3. The paint's cost is linear in a paragraph's inline children: besideNonWs and follows step over the DOM's sibling pointers
//    (round 8 indexed the parent's child list per whitespace node, so one mark across 3,000 links cost 850 ms against 27 ms
//    before the rule). Timed as equal work in the same run: a paragraph of LARGE links painted once against a paragraph of SMALL
//    links painted LARGE / SMALL times, seven pairs, the median of the pair ratios bounded at LINEAR_BOUND (a linear paint gives
//    about 1, the quadratic one about LARGE / SMALL; the method md-config-block-start-memo.test.ts adopted in round 8, whose
//    equal-work legs hold under a CPU quota where unequal ones did not), with an absolute guard on the large paint as the
//    load-independent catcher. The source table (anchor-map.ts sourceTable) is one entry keyed on the source, and marked's lex
//    of a 5,000-link paragraph is 300 ms of its own, so each timed paint follows an untimed one over the same source (the table
//    warm, as it is for the panel, which paints one text many times) and the marks are unwrapped between paints, the DOM built
//    once a size. Skips LOUDLY without a playwright browser (CI installs none). Synthetic prose, no paths.
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
/** The Rendering section's block-level tags, the node pin's fixture (md-config-block-boxes.test.ts); leg 1 holds it to Chromium. */
const FIXTURE = JSON.parse(fs.readFileSync(path.join(UI, "anchor-map-fixtures", "block-tags.json"), "utf8")) as { tags: Record<string, string> };

/** marked with the viewer's grammar, the sanitizer and its profile, DOMPurify itself (for the allowlist), the paint and the
 *  shipped set, bundled as the webview build bundles them. */
function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: {
      contents: 'import DOMPurify from "dompurify";\nimport { marked } from "marked";\nimport { applyMdConfig } from "./md-config";\n'
        + 'import { sanitizeMd, MD_PURIFY, MD_FORBID_TAGS } from "./md-sanitize";\nimport { paintRendered, BLOCK_BOXES } from "./anchor-map";\n'
        + 'applyMdConfig();\n(window as any).__romp = { DOMPurify, marked, sanitizeMd, MD_PURIFY, MD_FORBID_TAGS, paintRendered, BLOCK_BOXES: Array.from(BLOCK_BOXES) };\n',
      resolveDir: UI, loader: "ts", sourcefile: "paint-whitespace-probe.ts",
    },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "*.woff2"], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
/** The sheet's rules the scenes live under: the viewer's prose root and its paragraphs and images, and the two highlight classes. */
function sheet(): string {
  const rule = (sel: string): string => {
    const m = new RegExp("\\n(" + sel.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + " \\{[^}]*\\})").exec(FEED);
    assert.ok(m, "a rule for " + sel + " in feed.css");
    return m![1];
  };
  return [rule(".fileview-md"), rule(".fileview-md p"), rule(".fileview-md img"), rule(".fc-hl"), rule(".fc-presel")].join("\n");
}
const PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8><style>
body { margin: 0; padding: 0; font: 14px/1.5 sans-serif; background: #1e1e1e; color: #ccc; --fg: #ccc; --dim: #999; --accent: #9cd2ff; --accent-wash: rgba(156,210,255,0.15); --warn: #e0a030; --bg: #1e1e1e; --font-doc: sans-serif; }
${sheet()}
#md { width: 800px; }</style></head><body><div class="fileview-md" id="md"></div><script src="/dist/probe.js"></script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

/** The page's own helpers: the viewer's render (mdBlock's shape: the sanitized body's children adopted), a layout read, a mark
 *  read, and the panel's unpaint (file-comments.ts unpaint: the mark's children back in place, the parent normalized). */
const HELPERS = `
window.__render = (src) => { const md = document.getElementById("md"); md.replaceChildren(...Array.from(window.__romp.sanitizeMd(window.__romp.marked.parse(src)).childNodes)); };
window.__layout = () => { const md = document.getElementById("md"); const r = md.getBoundingClientRect();
  const tops = Array.from(md.children).map((c) => { const b = c.getBoundingClientRect(); return [c.tagName, Math.round(b.top * 100) / 100, Math.round(b.height * 100) / 100]; });
  const imgs = Array.from(md.querySelectorAll("img")).map((i) => { const b = i.getBoundingClientRect(); return [Math.round(b.x * 100) / 100, Math.round(b.y * 100) / 100]; });
  return { height: Math.round(r.height * 100) / 100, tops, imgs }; };
window.__paint = (src, cls) => { const md = document.getElementById("md");
  const range = { start: src.indexOf("Intro para."), end: src.indexOf("After para.") + "After para.".length };
  const marks = window.__romp.paintRendered(md, src, range, cls, { id: "c1" }) || [];
  return marks.map((m) => { const b = m.getBoundingClientRect(); return { parent: m.parentElement.tagName, text: m.textContent, wsOnly: !m.textContent.trim(), w: Math.round(b.width * 100) / 100, h: Math.round(b.height * 100) / 100, visible: m.checkVisibility() }; }); };
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

// ── leg 1: the set, derived ─────────────────────────────────────────────────────────────────────────────────────────────────
/** Chromium's block-level displays and the table's: an element with one of these makes no line with the white space beside it. */
const BLOCK_DISPLAYS = ["block", "list-item", "flow-root", "flex", "grid", "table", "table-caption", "table-column", "table-column-group", "table-header-group", "table-row-group", "table-footer-group", "table-row", "table-cell"];
/** The document's own elements, which the HTML parser never places in a fragment (a `<body>` in a note's html is dropped). */
const NEVER_IN_A_FRAGMENT = ["HTML", "BODY"];

test("BLOCK_BOXES is the set of tags the sanitizer keeps that Chromium lays out as blocks or a table's parts, html and body left out: read off DOMPurify's allowlist under MD_PURIFY and the computed display, it equals the shipped set", async (t) => {
  await inBrowser(t, async (page) => {
    const r = await page.evaluate((displays: string[]) => {
      const w = window as any;
      const inst = w.__romp.DOMPurify(window);
      let allowed: string[] | null = null;
      inst.addHook("uponSanitizeElement", (_n: unknown, data: { allowedTags: Record<string, boolean> }) => { if (!allowed) allowed = Object.keys(data.allowedTags); });
      inst.sanitize("<div>x</div>", { ...w.__romp.MD_PURIFY });
      const forbid = new Set<string>(w.__romp.MD_FORBID_TAGS);
      const host = document.getElementById("md")!;
      const kept: Array<[string, string]> = [];
      const forbidden: string[] = [];
      for (const tag of allowed || []) {
        if (tag === "#text") continue;
        if (forbid.has(tag)) { forbidden.push(tag); continue; }
        const el = document.createElement(tag);
        host.appendChild(el);
        kept.push([tag, getComputedStyle(el).display]);
        host.removeChild(el);
      }
      const derived = kept.filter(([, d]) => displays.includes(d)).map(([tag]) => tag.toUpperCase()).sort();
      const survive = ["center", "dir", "menu", "search", "hgroup"].map((tag) => { const clean = w.__romp.sanitizeMd("<" + tag + ">x</" + tag + ">"); return [tag, !!clean.querySelector(tag)]; });
      return { allowedCount: (allowed || []).length, forbidden: forbidden.sort(), derived, shipped: (w.__romp.BLOCK_BOXES as string[]).slice().sort(), survive, displays: Object.fromEntries(kept) };
    }, BLOCK_DISPLAYS);
    assert.ok(r.allowedCount > 100, "the hook read the instance's allowlist: " + r.allowedCount + " tags");
    for (const tag of ["form", "fieldset", "legend", "dialog"]) assert.ok(r.forbidden.includes(tag), tag + " is a tag the sanitizer strips (MD_FORBID_TAGS), so it is no neighbour a note can have");
    for (const tag of ["center", "dir", "menu", "search", "hgroup"]) {
      assert.equal(r.displays[tag], "block", tag + " is a block in Chromium");
      assert.ok(r.derived.includes(tag.toUpperCase()), tag + " is in the derived set (kept by the sanitizer, a block in Chromium)");
    }
    assert.deepEqual(r.survive.filter((s: [string, boolean]) => !s[1]), [], "sanitizeMd keeps each of the five");
    for (const tag of NEVER_IN_A_FRAGMENT) assert.ok(r.derived.includes(tag), tag + " is derived (a block the sanitizer allows) and left out of the set by name");
    const expected = r.derived.filter((tag: string) => !NEVER_IN_A_FRAGMENT.includes(tag));
    assert.deepEqual(r.shipped, expected, "the shipped BLOCK_BOXES equals the derived set: every kept block tag is in it and nothing else is");
    // the fixture the node pin reads is Chromium's over every kept tag: a tag is on it exactly when Chromium lays the element out
    // as a block-level box or a table's part, and with the display the fixture names (the section's rule for the bare element)
    const off = Object.entries(r.displays as Record<string, string>)
      .filter(([tag, d]) => (tag in FIXTURE.tags ? FIXTURE.tags[tag] !== d : BLOCK_DISPLAYS.includes(d)))
      .map(([tag, d]) => tag + " (fixture " + (FIXTURE.tags[tag] || "absent") + ", Chromium " + d + ")");
    assert.deepEqual(off, [], "anchor-map-fixtures/block-tags.json is Chromium's over the kept tags");
    assert.ok(Object.keys(r.displays).filter((tag) => tag in FIXTURE.tags).length >= 40, "the kept tags cover the fixture's blocks");
  });
});

// ── leg 2: the author shapes, painted ───────────────────────────────────────────────────────────────────────────────────────
const PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==";
const IMG = '<img src="' + PNG + '" width="100" height="50" alt="pic">';
const wrap = (block: string): string => "Intro para.\n\n" + block + "\n\nAfter para.\n";
/** Each scene: the html block between the two paragraphs and the text the marks must read, block by block. */
const SCENES: Array<[string, string, string[]]> = [
  ["a figure with an image and a caption", wrap("<figure>\n" + IMG + "\n<figcaption>Caption text</figcaption>\n</figure>"), ["Intro para.", "Caption text", "After para."]],
  ["a figure with an image alone", wrap("<figure>\n" + IMG + "\n</figure>"), ["Intro para.", "After para."]],
  ["an open details with a summary and an image", wrap("<details open>\n<summary>Shots</summary>\n\n" + IMG + "\n\n</details>"), ["Intro para.", "Shots", "After para."]],
  ["a center with an image alone", wrap("<center>\n" + IMG + "\n</center>"), ["Intro para.", "After para."]],
  ["an open details whose body is a center", wrap("<details open>\n<summary>Screenshots</summary>\n\n<center>alpha centred</center>\n\n</details>"), ["Intro para.", "Screenshots", "alpha centred", "After para."]],
  ["a figure whose body is a menu", wrap("<figure>\n\n<menu><li>one</li></menu>\n\n</figure>"), ["Intro para.", "one", "After para."]],
  ["a figure whose body is a dir", wrap("<figure>\n\n<dir><li>one</li></dir>\n\n</figure>"), ["Intro para.", "one", "After para."]],
  ["an open details whose body is a search", wrap("<details open>\n<summary>Find</summary>\n\n<search>find it</search>\n\n</details>"), ["Intro para.", "Find", "find it", "After para."]],
  ["a double line break in a paragraph", wrap("line one<br>\n<br>\nline three"), ["Intro para.", "line one", "\nline three", "After para."]],
  ["white space before and after a line break, beside inline elements", wrap("text *one* <br>\n**bold** tail"), ["Intro para.", "text ", "one", "bold", " tail", "After para."]],
  ["the control: a figure whose body is a paragraph", wrap("<figure>\n<p>Body text</p>\n</figure>"), ["Intro para.", "Body text", "After para."]],
];
type Mark = { parent: string; text: string; wsOnly: boolean; w: number; h: number; visible: boolean };
type Layout = { height: number; tops: Array<[string, number, number]>; imgs: Array<[number, number]> };
const same = (a: Layout, b: Layout, what: string): void => {
  assert.equal(b.height, a.height, what + ": the prose root keeps its height");
  assert.deepEqual(b.tops, a.tops, what + ": every top-level block where it stood, at its height");
  assert.deepEqual(b.imgs, a.imgs, what + ": every image where it stood");
};

test("a highlight from the paragraph before an author's html block to the paragraph after it paints the block's text, no whitespace-only mark, and moves nothing: the parent's edge beside an image, center, menu, dir and search, a double line break", async (t) => {
  await inBrowser(t, async (page) => {
    for (const [why, src, texts] of SCENES) {
      for (const cls of ["fc-hl", "fc-presel"]) {
        const what = why + " (" + cls + ")";
        await page.evaluate((s: string) => (window as any).__render(s), src);
        const before: Layout = await page.evaluate(() => (window as any).__layout());
        assert.ok(before.tops.length >= 3, what + ": the html block stands between the two paragraphs: " + JSON.stringify(before.tops));
        const marks: Mark[] = await page.evaluate(([s, c]: [string, string]) => (window as any).__paint(s, c), [src, cls]);
        const after: Layout = await page.evaluate(() => (window as any).__layout());
        assert.deepEqual(marks.filter((m) => m.wsOnly).map((m) => m.parent + " " + JSON.stringify(m.text) + " " + m.w + "x" + m.h), [], what + ": no whitespace-only mark");
        assert.deepEqual(marks.map((m) => m.text), texts, what + ": the blocks' text and nothing else");
        same(before, after, what + ", painted");
        await page.evaluate(() => (window as any).__unpaint());
        same(before, await page.evaluate(() => (window as any).__layout()), what + ", unpainted");
        const again: Mark[] = await page.evaluate(([s, c]: [string, string]) => (window as any).__paint(s, c), [src, cls]);
        assert.deepEqual(again.map((m) => m.text), texts, what + ": the same marks on a repaint");
        same(before, await page.evaluate(() => (window as any).__layout()), what + ", repainted");
      }
    }
    // the other side of the rule: a space inside an inline element beside an image, mid-line, is rendered and is painted, a box
    // wider than the sheet's 4 px of padding (a rendered space plus the padding)
    const mid = wrap("Some text<span> " + IMG + "</span> tail.");
    await page.evaluate((s: string) => (window as any).__render(s), mid);
    const marks: Mark[] = await page.evaluate(([s, c]: [string, string]) => (window as any).__paint(s, c), [mid, "fc-hl"]);
    assert.deepEqual(marks.map((m) => m.text), ["Intro para.", "Some text", " ", " tail.", "After para."], "the rendered space is painted with the passage");
    const space = marks.find((m) => m.text === " ")!;
    assert.equal(space.parent, "SPAN");
    assert.ok(space.visible && space.w > 5, "the space's mark is a rendered space plus the padding, not the padding alone: " + space.w + "x" + space.h);
  });
});

// ── leg 3: the cost, equal work ─────────────────────────────────────────────────────────────────────────────────────────────
const LARGE = 5000, SMALL = 500, PAIRS = 7;
/** The median of seven pair ratios, large once against small LARGE / SMALL times, the source table warm for both: a linear
 *  paint measures about 1 (0.9 to 1.2 alone on the build box, the pointers in place), the indexed one about LARGE / SMALL (8 to
 *  9; 2,160 ms against 250). Bounded with the room round 8's memo test measured its equal-work legs need under a CPU quota (a
 *  worst median of 1.68 there). */
const LINEAR_BOUND = 3;
/** The large paint alone, the table warm: about 50 ms with the pointers on the build box, 2,160 ms indexed; the load-independent
 *  catcher, with room for a slow runner. */
const ABSOLUTE_MS = 1000;
const links = (n: number): string => "# Title\n\n" + Array.from({ length: n }, (_, i) => "[w" + i + "](#a" + i + ")").join(" ") + "\n\nAfter para.\n";

test("one mark across a paragraph of 5,000 links costs what ten across 500 cost: the neighbour and adjacency reads step over the DOM's sibling pointers, so the paint is linear in the inline children (equal-work legs, the median pair ratio bounded)", async (t) => {
  await inBrowser(t, async (page) => {
    const r = await page.evaluate(([large, small, pairs]: [string, string, number]) => {
      const w = window as any;
      const host = (): HTMLElement => { const h = document.createElement("div"); h.className = "fileview-md"; document.body.appendChild(h); return h; };
      const build = (h: HTMLElement, src: string) => { h.replaceChildren(...Array.from(w.__romp.sanitizeMd(w.__romp.marked.parse(src)).childNodes as ArrayLike<Node>)); };
      // the panel's unpaint (file-comments.ts): the marks' children back in place, each parent normalized, here once per parent
      const unpaint = (h: HTMLElement) => { const parents = new Set<Node>(); for (const n of Array.from(h.querySelectorAll("mark"))) { const p = n.parentNode!; parents.add(p); while (n.firstChild) p.insertBefore(n.firstChild, n); p.removeChild(n); } for (const p of parents) p.normalize(); };
      const range = (src: string) => ({ start: src.indexOf("[w0]"), end: src.indexOf("\n\nAfter para.") });
      const paint = (h: HTMLElement, src: string): { ms: number; marks: number; ws: number } => {
        const rg = range(src);
        const t0 = performance.now(); const marks = w.__romp.paintRendered(h, src, rg, "fc-hl", { id: "c1" }) || []; const t1 = performance.now();
        const out = { ms: t1 - t0, marks: marks.length, ws: marks.filter((m: Element) => !(m.textContent || "").trim()).length };
        unpaint(h);
        return out;
      };
      const reps = Math.round(large.split("](#").length / small.split("](#").length);   // LARGE / SMALL, read off the sources
      const L = host(), S = host();
      build(L, large); build(S, small);
      const shape = (h: HTMLElement) => Array.from(h.querySelector("p")!.childNodes).map((n) => n.nodeType === 3 ? "t" : (n as Element).tagName).join("");
      const lShape = shape(L), sShape = shape(S);
      const ratios: number[] = []; const larges: number[] = []; let lm = 0, lws = 0, sm = 0, sws = 0;
      for (let i = 0; i < pairs; i++) {
        paint(L, large);                                                    // the table warm for the large source (untimed)
        const l = paint(L, large); lm = l.marks; lws = l.ws; larges.push(l.ms);
        paint(S, small);                                                    // and for the small one
        let s = 0;
        for (let k = 0; k < reps; k++) { const S1 = paint(S, small); sm = S1.marks; sws = S1.ws; s += S1.ms; }
        ratios.push(l.ms / s);
      }
      const med = (a: number[]) => { const c = a.slice().sort((x, y) => x - y); return c[Math.floor(c.length / 2)]; };
      return { reps, ratios: ratios.map((x) => Math.round(x * 100) / 100), median: Math.round(med(ratios) * 100) / 100, largeMedian: Math.round(med(larges) * 10) / 10,
               largeMarks: lm, largeWs: lws, smallMarks: sm, smallWs: sws, restored: shape(L) === lShape && shape(S) === sShape };
    }, [links(LARGE), links(SMALL), PAIRS]);
    assert.equal(r.reps, LARGE / SMALL);
    assert.equal(r.largeMarks, 2 * LARGE - 1, "the large paragraph: every link text and every space a mark (the spaces are the passage's own text)");
    assert.equal(r.largeWs, LARGE - 1);
    assert.equal(r.smallMarks, 2 * SMALL - 1);
    assert.equal(r.smallWs, SMALL - 1);
    assert.ok(r.restored, "the unpaint between paints gives the paragraphs back as built");
    assert.ok(r.median <= LINEAR_BOUND, "one paint of " + LARGE + " links against " + r.reps + " of " + SMALL + ": pair ratios " + r.ratios.join(" ") + ", median " + r.median + " over the bound " + LINEAR_BOUND + ": not linear");
    assert.ok(r.largeMedian <= ABSOLUTE_MS, "the large paint's median " + r.largeMedian + " ms is over " + ABSOLUTE_MS + " (about 50 ms with the pointers, 2,160 indexed, on the build box)");
  });
});
