// The whitespace rule of the Rendered paint (anchor-map.ts skipBlockWs and trimCollapsedMarks), over the REAL bundle in headless
// Chromium: marked with the one configuration (md-config.ts), the sanitizer (md-sanitize.ts) and paintRendered, the DOM built as
// the viewer's mdBlock builds it. Four legs (the Slice 4 review, rounds 9, 12 and 13):
// 1. BLOCK_BOXES, the tags a whitespace-only text node between two of which is skipped without a measurement, is DERIVED here and
//    held equal to the shipped set: every
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
//    Since round 12 the "\n\n" between two blocks is the pre-skip's and the "\n" beside an image or a br is painted, measured at
//    zero width and unwrapped by the trim: the same DOM after the paint either way. The layout is read box for box, unpainted
//    against painted and again after the panel's unpaint and a repaint; the controls (a space inside an inline element beside an
//    image, mid-line and rendered; a figure whose body is a paragraph) hold the rule's two sides.
// 3. The paint less the trim is linear in a paragraph's inline children: the pre-skip's neighbour reads (stepping with sibling)
//    and follows step over the DOM's sibling pointers (round 8 indexed the parent's child list per whitespace node, so one mark
//    across 3,000 links cost 850 ms against 27 ms before the rule). Timed as equal work in the same run with the trim deferred
//    (`trim: false`, the panel's own call shape): a paragraph of LARGE links painted once against a paragraph of SMALL links
//    painted LARGE / SMALL times, seven pairs, the median of the pair ratios bounded at LINEAR_BOUND (a linear paint gives about 1,
//    the quadratic one about LARGE / SMALL; the method md-config-block-start-memo.test.ts adopted in round 8, whose equal-work legs
//    hold under a CPU quota where unequal ones did not), with an absolute guard on the large paint as the load-independent
//    catcher. The source table (anchor-map.ts sourceTable) is one entry keyed on the source, and marked's lex of a 5,000-link
//    paragraph is 300 ms of its own, so each timed paint follows an untimed one over the same source (the table warm, as it is for
//    the panel, which paints one text many times) and the marks are unwrapped between paints, the DOM built once a size.
// 4. The trim's shape and cost on the same LARGE paragraph, the pathological case (one comment across 5,000 links; rounds 12 and
//    13): at 800 px the trimmed paint unwraps exactly one blank mark per line break of the painted paragraph (the space the line
//    wraps at, collapsed as the line's trailing space) and leaves no blank mark of zero width and no rendered blank unmarked. Its
//    passes are read off the DOM calls themselves (Range.getClientRects, one per blank mark measured, and the unwrap's removeChild
//    of a mark, both counted through wrappers on their prototypes): every measurement of a pass before its first unwrap, the first
//    pass over every blank mark, each later pass over exactly the marks the last one kept, the loop ending with a pass that
//    unwrapped nothing or with no candidate left, and the passes as many as the cascade takes. Round 12 capped them at three and
//    pinned the cap here as `calls <= 3B`; at 700 px, where each unwrap moves the wrap point of a longer cascade, that cap left
//    366 padding-only marks standing after the trim, so round 13 runs the loop to its fixpoint and this leg paints the paragraph
//    at 700 px as well and holds no zero-width blank mark there either. Never one measurement per unwrap (which relaid the block
//    out 373 times and cost 12 s in the prototype). And it costs a bounded multiple of the untrimmed paint in the same run
//    (TRIM_BOUND; the prototype measured about 8 for one pass, the build box about 16 with the confirming pass), with an absolute
//    guard. Skips LOUDLY without a playwright browser (CI installs none). Synthetic prose, no paths.
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
        + 'import { sanitizeMd, MD_PURIFY, MD_FORBID_TAGS } from "./md-sanitize";\nimport { paintRendered, BLOCK_BOXES } from "./anchor-map";\nimport { unwrapMarks } from "./file-comments";\n'
        + 'applyMdConfig();\n(window as any).__romp = { DOMPurify, marked, sanitizeMd, MD_PURIFY, MD_FORBID_TAGS, paintRendered, unwrapMarks, BLOCK_BOXES: Array.from(BLOCK_BOXES) };\n',
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
 *  read, and the panel's own unpaint step (file-comments.ts unwrapMarks, the same function Panel.unpaint runs: the marks' children back
 *  in place, each parent normalized once; plans/markdown-viewer.md Slice 5, section 2 (d)). */
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
window.__unpaint = () => { window.__romp.unwrapMarks(Array.from(document.querySelectorAll("#md mark"))); };
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

test("one mark across a paragraph of 5,000 links costs what ten across 500 cost with the trim deferred: the neighbour and adjacency reads step over the DOM's sibling pointers, so the paint less the trim is linear in the inline children (equal-work legs, the median pair ratio bounded)", async (t) => {
  await inBrowser(t, async (page) => {
    const r = await page.evaluate(([large, small, pairs]: [string, string, number]) => {
      const w = window as any;
      const host = (): HTMLElement => { const h = document.createElement("div"); h.className = "fileview-md"; document.body.appendChild(h); return h; };
      const build = (h: HTMLElement, src: string) => { h.replaceChildren(...Array.from(w.__romp.sanitizeMd(w.__romp.marked.parse(src)).childNodes as ArrayLike<Node>)); };
      // the panel's own unpaint step (file-comments.ts unwrapMarks, what Panel.unpaint runs): the marks' children back in place, each parent
      // normalized once, after the loop (Slice 5, section 2 (d): per mark it cost the square of the paragraph's inline children)
      const unpaint = (h: HTMLElement) => { w.__romp.unwrapMarks(Array.from(h.querySelectorAll("mark"))); };
      const range = (src: string) => ({ start: src.indexOf("[w0]"), end: src.indexOf("\n\nAfter para.") });
      const paint = (h: HTMLElement, src: string): { ms: number; marks: number; ws: number } => {
        const rg = range(src);
        // the trim deferred, as the panel defers it to its pass (leg 4 times the trim itself)
        const t0 = performance.now(); const marks = w.__romp.paintRendered(h, src, rg, "fc-hl", { id: "c1" }, { trim: false }) || []; const t1 = performance.now();
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
    assert.equal(r.largeMarks, 2 * LARGE - 1, "the large paragraph, the trim deferred: every link text and every space a mark (the spaces are the passage's own text)");
    assert.equal(r.largeWs, LARGE - 1);
    assert.equal(r.smallMarks, 2 * SMALL - 1);
    assert.equal(r.smallWs, SMALL - 1);
    assert.ok(r.restored, "the unpaint between paints gives the paragraphs back as built");
    assert.ok(r.median <= LINEAR_BOUND, "one paint of " + LARGE + " links against " + r.reps + " of " + SMALL + ": pair ratios " + r.ratios.join(" ") + ", median " + r.median + " over the bound " + LINEAR_BOUND + ": not linear");
    assert.ok(r.largeMedian <= ABSOLUTE_MS, "the large paint's median " + r.largeMedian + " ms is over " + ABSOLUTE_MS + " (about 50 ms with the pointers, 2,160 indexed, on the build box)");
  });
});

// ── leg 4: the trim's shape and cost on the large paragraph ────────────────────────────────────────────────────────────────
/** The trimmed paint against the untrimmed one, the median of PAIRS pair ratios: about 16 on the build box (two measurement
 *  passes over 4,999 blank marks, 6 to 50 us a Range.getClientRects inside a 10k-box inline formatting context, against a 50 ms
 *  paint), bounded with room for a loaded runner; a measurement per unwrap would read 200 and more. */
const TRIM_BOUND = 60;
/** The trimmed paint alone, the table warm: about 0.8 s on the build box; the load-independent catcher (12 s per unwrap-relayout). */
const TRIM_ABSOLUTE_MS = 6000;

test("the trim over one mark across 5,000 links at 800 px unwraps one blank mark per line break and no other, leaves no zero-width blank mark and no rendered blank unmarked, and costs a bounded multiple of the untrimmed paint; its passes, read off the DOM calls, each measure before any unwrap and cover exactly the marks the last pass kept, until a pass unwraps nothing or no candidate is left (never once per unwrap, never a fixed count); at 700 px, where the cascade outruns round 12's cap of three passes, no zero-width blank mark stands either", async (t) => {
  await inBrowser(t, async (page) => {
    const r = await page.evaluate(([large, pairs]: [string, number]) => {
      const w = window as any;
      const host = (): HTMLElement => { const h = document.createElement("div"); h.className = "fileview-md"; h.style.width = "800px"; document.body.appendChild(h); return h; };
      const build = (h: HTMLElement, src: string) => { h.replaceChildren(...Array.from(w.__romp.sanitizeMd(w.__romp.marked.parse(src)).childNodes as ArrayLike<Node>)); };
      const unpaint = (h: HTMLElement) => { w.__romp.unwrapMarks(Array.from(h.querySelectorAll("mark"))); };   // the panel's own step (leg 3's comment)
      const range = (src: string) => ({ start: src.indexOf("[w0]"), end: src.indexOf("\n\nAfter para.") });
      const blank = (s: string) => /^\s*$/.test(s);
      const width = (n: Node): number => { const rg = document.createRange(); rg.selectNodeContents(n); let x = 0; for (const b of Array.from(rg.getClientRects())) x += b.width; return x; };
      // the trim's passes read off the DOM calls, through wrappers on the prototypes: Range.getClientRects, one per blank mark
      // measured (M), and the unwrap's removeChild of a mark (U); a run of Ms is a pass's measurements, the run of Us after it
      // the pass's unwraps, so "M4999 U324 M4675" is two passes, the second confirming the fixpoint
      let calls = 0; let recording = false; let events: string[] = [];
      const proto = Range.prototype as any; const orig = proto.getClientRects;
      proto.getClientRects = function (this: Range) { calls++; if (recording) events.push("M"); return orig.call(this); };
      const nproto = Node.prototype as any; const origRemove = nproto.removeChild;
      nproto.removeChild = function (this: Node, n: Node) { if (recording && (n as Element).tagName === "MARK") events.push("U"); return origRemove.call(this, n); };
      const runs = (ev: string[]): { passes: number[]; unwraps: number[]; order: string } => {
        const seq: Array<[string, number]> = [];
        for (const e of ev) { const last = seq[seq.length - 1]; if (last && last[0] === e) last[1]++; else seq.push([e, 1]); }
        const shown = seq.slice(0, 12).map((x) => x[0] + x[1]).join(" ") + (seq.length > 12 ? " and " + (seq.length - 12) + " more runs" : "");
        return { passes: seq.filter((x) => x[0] === "M").map((x) => x[1]), unwraps: seq.filter((x) => x[0] === "U").map((x) => x[1]), order: shown };
      };
      const L = host(); build(L, large);
      const p = L.querySelector("p")!; const lineHeight = parseFloat(getComputedStyle(p).lineHeight);
      const rg = range(large);
      const paint = (trim: boolean): { ms: number; marks: Element[]; calls: number; events: string[] } => {
        calls = 0; events = []; recording = true;
        const t0 = performance.now(); const marks = w.__romp.paintRendered(L, large, rg, "fc-hl", { id: "c1" }, { trim }) || []; const t1 = performance.now();
        recording = false;
        return { ms: t1 - t0, marks, calls, events };
      };
      // the trimmed paint's shape at the host's width of the moment: the marks kept and unwrapped, the lines, the blank marks of
      // zero width left standing, the rendered blanks left bare, and the passes
      const shapeOf = (tr: { marks: Element[]; calls: number; events: string[] }, uBlank: number) => {
        const kept = tr.marks.filter((m: Element) => blank(m.textContent || ""));
        const lines = Math.round(p.getBoundingClientRect().height / lineHeight);
        const zeroKept = kept.filter((m: Element) => width(m) === 0).length;
        // every blank text node of the paragraph with a width in the painted layout carries a mark
        let bareRendered = 0; const walk = document.createTreeWalker(p, NodeFilter.SHOW_TEXT);
        for (let n = walk.nextNode(); n; n = walk.nextNode()) if (blank((n as Text).data) && width(n) > 0 && !(n.parentElement && n.parentElement.closest("mark"))) bareRendered++;
        return { tMarks: tr.marks.length, tBlank: kept.length, trimmed: uBlank - kept.length, lines, zeroKept, bareRendered, calls: tr.calls, ...runs(tr.events) };
      };
      const ratios: number[] = []; const trimmedMs: number[] = []; let shape: any = null; let untrimmed: any = null;
      for (let i = 0; i < pairs; i++) {
        paint(false); unpaint(L);                                          // the table warm (untimed)
        const u = paint(false); const uMarks = u.marks.length, uBlank = u.marks.filter((m: Element) => blank(m.textContent || "")).length; const uCalls = u.calls, uUnwraps = u.events.length; unpaint(L);
        const tr = paint(true); trimmedMs.push(tr.ms);
        if (!shape) { untrimmed = { uMarks, uBlank, uCalls, uUnwraps }; shape = shapeOf(tr, uBlank); }
        unpaint(L);
        ratios.push(tr.ms / u.ms);
      }
      // the second width: the same paragraph at 700 px, where each unwrap moves the wrap point of a longer cascade of blanks
      L.style.width = "700px";
      const narrow = shapeOf(paint(true), untrimmed.uBlank);
      unpaint(L); L.style.width = "800px";
      proto.getClientRects = orig; nproto.removeChild = origRemove;
      const med = (a: number[]) => { const c = a.slice().sort((x, y) => x - y); return c[Math.floor(c.length / 2)]; };
      return { ...untrimmed, ...shape, narrow, ratios: ratios.map((x) => Math.round(x * 10) / 10), median: Math.round(med(ratios) * 10) / 10, trimmedMedian: Math.round(med(trimmedMs)) };
    }, [links(LARGE), PAIRS]);
    assert.equal(r.uMarks, 2 * LARGE - 1, "the untrimmed paint: every link text and every space a mark");
    assert.equal(r.uBlank, LARGE - 1, "the untrimmed paint: every space a blank mark");
    assert.equal(r.uCalls, 0, "the untrimmed paint measures nothing");
    assert.equal(r.uUnwraps, 0, "the untrimmed paint unwraps nothing");
    assert.ok(r.lines > 100, "the paragraph wraps into many lines at 800 px: " + r.lines);
    assert.equal(r.trimmed, r.lines - 1, "at 800 px the trim unwraps one blank mark per line break of the painted paragraph, the space the line wraps at, and no other: " + r.trimmed + " unwrapped, " + r.lines + " lines");
    assert.equal(r.tMarks, r.uMarks - r.trimmed, "the non-blank marks all stay");
    assert.equal(r.zeroKept, 0, "no blank mark of zero width stands after the trim at 800 px");
    assert.equal(r.bareRendered, 0, "no rendered blank of the paragraph is left without a mark at 800 px");
    const B = r.uBlank;
    /** The passes, read off the calls: the runs alternate from a measurement run (no unwrap precedes the first measurement), the
     *  first pass measures every blank mark, each later pass exactly the marks the pass before it kept, and the loop ends with a
     *  pass that unwrapped nothing (the runs end in M) or with no candidate left (they end in U and the last pass unwrapped every
     *  mark it measured); a measurement per unwrap reads "M.. U1 M1 U1", a pass cut short by a cap ends in U with marks kept. */
    const passes = (s: { passes: number[]; unwraps: number[]; order: string; calls: number; trimmed: number }, at: string) => {
      const why = at + ", the runs " + s.order;
      assert.equal(s.order[0], "M", why + ": the first call is a measurement");
      assert.equal(s.passes[0], B, why + ": the first pass measures every blank mark once");
      for (let i = 1; i < s.passes.length; i++) assert.equal(s.passes[i], s.passes[i - 1] - s.unwraps[i - 1], why + ": pass " + (i + 1) + " measures exactly the marks pass " + i + " kept");
      const last = s.passes.length - 1;
      if (s.unwraps.length === s.passes.length) assert.equal(s.passes[last] - s.unwraps[last], 0, why + ": the runs end in an unwrap, so the loop must have run out of candidates; a cap cut it short with marks standing");
      else assert.equal(s.unwraps.length, s.passes.length - 1, why + ": the runs end in a pass that unwrapped nothing");
      assert.equal(s.unwraps.reduce((a, b) => a + b, 0), s.trimmed, why + ": the unwraps read are the marks the trim removed");
      assert.equal(s.passes.reduce((a, b) => a + b, 0), s.calls, why + ": the measurements read are the getClientRects calls");
    };
    passes(r, "at 800 px");
    assert.ok(r.passes.length >= 2, "at 800 px marks were unwrapped and candidates remained, so a pass confirmed the fixpoint: " + r.order);
    passes(r.narrow, "at 700 px");
    assert.equal(r.narrow.zeroKept, 0, "no blank mark of zero width stands after the trim at 700 px (round 12's cap of three passes left 366; " + r.narrow.trimmed + " unwrapped over the passes " + r.narrow.order + ", " + r.narrow.lines + " lines, " + r.narrow.bareRendered + " rendered blanks bare, the reverse flip plan item 10 records)");
    assert.ok(r.median <= TRIM_BOUND, "the trimmed paint against the untrimmed one: pair ratios " + r.ratios.join(" ") + ", median " + r.median + " over the bound " + TRIM_BOUND);
    assert.ok(r.trimmedMedian <= TRIM_ABSOLUTE_MS, "the trimmed paint's median " + r.trimmedMedian + " ms is over " + TRIM_ABSOLUTE_MS);
  });
});
