// The rule for an inline start tag with no end tag in its block (md-literal-tags.ts; plans/file-review.md, decision 52) over the
// REAL viewer and the REAL Comments panel in headless Chromium (real-viewer-leg.ts: file-view.ts bundled from this tree, so
// mdBlock's own parse, DOMPurify's quirks-mode document, the panel's own paint). The node suites hold the rule at the token level
// (md-literal-tags.test.ts) and the map over a stand-in DOM (anchor-map-literal-tags.test.ts); this leg holds what the browser
// makes of the viewer's HTML: a paragraph holding `(<table>__widths.csv)` renders as its own text with `<table>` in it, the
// heading, the paragraph and the pipe table after it stand at the top level (before: the browser opened a table inside the
// paragraph and parsed the three into it, so the map refused the paragraph and every later block); an unclosed `<title>`,
// `<script>` or `<style>` no longer takes the rest of the note (before: the parser read it as the element's text and the
// sanitizer dropped it, so nothing after the tag was on the page); closed tags, void tags and the self-closing syntax render as
// before; a selection over any passage after the tags maps to its own source through the real DOM; a comment on the literal
// `<table>` characters paints through the panel's own pass and a tracked change over them through the painter; the Raw view maps
// the same characters to the same range. One page, one browser: the box's browser cap. Skips LOUDLY without a playwright browser
// (CI installs none), as the other browser legs do. Synthetic values only: an invented note in the notes-api demo domain, an
// invented file name, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as path from "node:path";
import { inBrowser, openViewer, openPanel, frames, REPORT, STATUS, UI, requireCjs } from "./real-viewer-leg";
import { makeAnchor } from "./anchor-map";

const T0 = 1757145600000;
const NOTE = [
  "# Report",
  "",
  "Intro t0 alpha beta.",
  "",
  "Widths come from the sheet (<table>__widths.csv) beside the note t1.",
  "",
  "## Second heading t2",
  "",
  "Para after the heading t3.",
  "",
  "| Col A | Col B |",
  "|---|---|",
  "| cell one t4 | cell two t5 |",
  "",
  "Lead <title> title rest t6.",
  "",
  "Lead <script> script rest t7.",
  "",
  "Lead <style> style rest t8.",
  "",
  "Press <b>bold t9</b> now, see <span class=\"a\">spanned t10</span>, hold <kbd>Ctrl</kbd> t11.",
  "",
  "First line<br>second line t12 and a <wbr> break and <x/> custom t13.",
  "",
  "Start <b>rest of the line t14.",
  "",
  "Pair <b>x<b>y</b> z t15. Case <B>x</b> t16. Emph <b>x *y</b>* t17.",
  "",
  "## Head <table> tail t18",
  "",
  "- item <b>one t19",
  "- item two t20",
  "",
  "| <span> x t21 | y |",
  "|---|---|",
  "| a | <i>b t22 |",
  "",
  "Note <!-- an aside --> here t23. A stray </div> closer t24.",
  "",
  "Closing words t25.",
  "",
].join("\n");
const KINDS = ["H1", "P", "P", "H2", "P", "TABLE", "P", "P", "P", "P", "P", "P", "P", "H2", "UL", "TABLE", "P", "P"];
/** The passages a selection is dragged over in the real DOM, each the first occurrence of its text there and in the source. */
const PASSAGES = ["beside the note t1", "<table>", "__widths.csv", "Second heading t2", "Para after the heading t3", "cell one t4", "cell two t5",
  "<title>", "title rest t6", "<script>", "script rest t7", "<style>", "style rest t8", "bold t9", "spanned t10", "Ctrl", "second line t12", "custom t13",
  "<b>rest", "rest of the line t14", "z t15", "t16", "tail t18", "<b>one t19", "item two t20", "<span> x t21", "<i>b t22", "here t23", "closer t24", "Closing words t25"];
const at = (s: string): number => { const i = NOTE.indexOf(s); assert.ok(i >= 0, "the note holds " + JSON.stringify(s)); return i; };
const rangeOf = (s: string): { start: number; end: number } => ({ start: at(s), end: at(s) + s.length });
const TABLE_RANGE = rangeOf("<table>");
/** A comment in the host's shape on the literal `<table>` characters: the exact source slice, its 24-character context, its position. */
const ON_TAG = { id: (T0 + 1) + "-" + TABLE_RANGE.start, author: "you", ts: T0 + 1, body: "Is this the right sheet?", anchor: makeAnchor(NOTE, TABLE_RANGE), anchorAt: TABLE_RANGE.start, replies: [], resolved: false };
const FINAL = (() => { const r = rangeOf("Closing words t25."); return { id: (T0 + 2) + "-" + r.start, author: "you", ts: T0 + 2, body: "The pass's sentinel.", anchor: makeAnchor(NOTE, r), anchorAt: r.start, replies: [], resolved: false }; })();
const withComments = (comments: Record<string, unknown>[]): Record<string, unknown> =>
  ({ ...STATUS, store: { ...STATUS.store, comments }, storeMtimeNs: "1757145600000000031", unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null } });

/** The map's four entry points, bundled alone as window.__am (the panel paints with its own copy inside the viewer's bundle; the
 *  answers are a function of the DOM and the source). */
function probeBundle(): string {
  const contents = 'import { mapRenderedSelection, mapRawSelection, paintChangesRendered, unpaintChanges } from "./anchor-map";\n'
    + '(window as any).__am = { mapRenderedSelection, mapRawSelection, paintChangesRendered, unpaintChanges };\n';
  const r = requireCjs("esbuild").buildSync({ stdin: { contents, resolveDir: UI, loader: "ts", sourcefile: "literal-tags-probe.ts" },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020", nodePaths: [path.join(process.cwd(), "node_modules")],
    external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent" });
  return r.outputFiles[0].text as string;
}

type Mapped = { needle: string; found: boolean; ok: boolean; reason: string; range: { start: number; end: number } | null; quote: string | null };
/** In the page: a real Selection over the first text node under `rootSel` holding each needle, mapped through the map's own entry point. */
const mapPassages = (page: any, rootSel: string, needles: string[], src: string, raw: boolean): Promise<Mapped[]> => page.evaluate(([rs, ns, s, isRaw]: [string, string[], string, boolean]) => {
  const root = document.querySelector(rs) as HTMLElement;
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const texts: Text[] = [];
  for (let n = walker.nextNode(); n; n = walker.nextNode()) texts.push(n as Text);
  const out: Mapped[] = [];
  for (const needle of ns) {
    const t = texts.find((x) => x.data.includes(needle));
    if (!t) { out.push({ needle, found: false, ok: false, reason: "not in the rendered text", range: null, quote: null }); continue; }
    const range = document.createRange();
    range.setStart(t, t.data.indexOf(needle)); range.setEnd(t, t.data.indexOf(needle) + needle.length);
    const sel = window.getSelection() as Selection;
    sel.removeAllRanges(); sel.addRange(range);
    const r = isRaw ? (window as any).__am.mapRawSelection(sel, root, s) : (window as any).__am.mapRenderedSelection(sel, root, s);
    sel.removeAllRanges();
    out.push(r.ok ? { needle, found: true, ok: true, reason: "", range: r.range, quote: r.quote } : { needle, found: true, ok: false, reason: r.reason, range: null, quote: null });
  }
  return out;
}, [rootSel, needles, src, raw] as [string, string[], string, boolean]);
const refusals = (ms: Mapped[]): string => ms.filter((m) => !m.ok).map((m) => JSON.stringify(m.needle) + ": " + m.reason).join("; ");

test("in a browser, the real viewer and panel on the Files pane: the paragraph holding `(<table>__widths.csv)` renders as its own text and the heading, paragraph and table after it stand at the top level, an unclosed `<title>`, `<script>` or `<style>` takes nothing after it, closed and void tags render as before, every passage maps to its own source, a comment on the literal `<table>` paints through the panel and a change through the painter, and the Raw view maps the same characters to the same range (before: the browser nested the three blocks inside the tag's paragraph and the map refused them, and nothing after the `<title>` was on the page)", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 900, 700, { docs: { [REPORT]: NOTE },
      before: async (p) => { await p.evaluate((st: unknown) => { (window as any).__status = st; }, withComments([FINAL, ON_TAG])); } });
    await page.addScriptTag({ content: probeBundle() });
    // ── the DOM: one top-level element per block, no block nested in a paragraph, the tag paragraph's text the source line
    const dom = await page.evaluate(() => {
      const md = document.querySelector(".fileview-md") as HTMLElement;
      return {
        kinds: Array.from(md.children).map((c) => c.tagName),
        nested: Array.from(md.querySelectorAll("p table, p title, p script, p style, p h2, p ul")).map((e) => e.tagName),
        rawText: Array.from(md.querySelectorAll("title, script, style, textarea")).map((e) => e.tagName),
        tagPara: (md.children[2] && md.children[2].textContent || "").replace(/\s+/g, " ").trim(),
        titlePara: (md.children[6] && md.children[6].textContent || "").replace(/\s+/g, " ").trim(),
        bolds: Array.from(md.querySelectorAll("b")).map((b) => (b.textContent || "").replace(/\s+/g, " ").trim()),
        span: (md.querySelector("span.a") || {}).textContent || null,
        kbd: (md.querySelector("kbd") || {}).textContent || null,
        br: md.querySelectorAll("p > br").length, wbr: md.querySelectorAll("p > wbr").length,
        text: (md.textContent || "").replace(/\s+/g, " "),
      };
    });
    assert.deepEqual(dom.kinds, KINDS, "one top-level element per block (before: the second paragraph held the heading, the paragraph and the table, and the `<title>` paragraph held the rest of the note)");
    assert.deepEqual(dom.nested, [], "no block nested in a paragraph");
    assert.deepEqual(dom.rawText, [], "no title, script, style or textarea element on the page");
    assert.equal(dom.tagPara, "Widths come from the sheet (<table>__widths.csv) beside the note t1.", "the tag paragraph's text is the source line, `<table>` included");
    assert.equal(dom.titlePara, "Lead <title> title rest t6.", "the `<title>` paragraph's text is the source line");
    assert.ok(dom.text.includes("Closing words t25."), "the end of the note is on the page (before: gone with the title)");
    assert.ok(dom.bolds.includes("bold t9") && dom.bolds.includes("y"), "closed tags keep their elements: `<b>bold t9</b>`, the inner pair of `<b>x<b>y</b>`: " + JSON.stringify(dom.bolds));
    assert.ok(!dom.bolds.some((b: string) => b.includes("rest of the line") || b.includes("one t19")), "no bold element holds the text after an unclosed `<b>`: " + JSON.stringify(dom.bolds));
    assert.equal(dom.span, "spanned t10", "`<span class=\"a\">` keeps its element and class");
    assert.equal(dom.kbd, "Ctrl", "`<kbd>` closed keeps its element");
    assert.equal(dom.br, 1, "`<br>` stays HTML"); assert.equal(dom.wbr, 1, "`<wbr>` stays HTML");
    // ── the map through the real DOM: every passage at its own offsets
    const mapped = await mapPassages(page, ".fileview-md", PASSAGES, NOTE, false);
    assert.equal(refusals(mapped), "", "every passage maps (the refusals listed; before: the mismatch sentence for the passages inside the tag paragraph's element, and nothing found after the title)");
    for (const m of mapped) { assert.deepEqual(m.range, rangeOf(m.needle), JSON.stringify(m.needle) + ": its own source offsets"); assert.equal(m.quote, m.needle); }
    // ── the paint: the panel's own pass paints the comment on the literal `<table>`; the painter paints a change over the same characters
    await openPanel(page);
    await page.waitForFunction((c: string) => !!document.querySelector('.fileview-body [data-act="fcopen"][data-id="' + c + '"]'), FINAL.id, { timeout: 10000 });
    await frames(page, 2);
    const painted = await page.evaluate(([cid, src, range]: [string, string, { start: number; end: number }]) => {
      const md = document.querySelector(".fileview-md") as HTMLElement;
      const marks = Array.from(md.querySelectorAll('.fc-hl[data-act="fcopen"][data-id="' + cid + '"]')) as HTMLElement[];
      const comment = { marks: marks.length, text: marks.map((m) => m.textContent).join("|"), boxed: marks.filter((m) => m.getClientRects().length > 0).length };
      const res = (window as any).__am.paintChangesRendered(md, src, [{ id: "i1", kind: "ins", curFrom: range.start, curTo: range.end, oldText: "", author: "api", newText: "<table>" }], () => ({}));
      const ins = Array.from(md.querySelectorAll('.fc-ins[data-id="i1"]')) as HTMLElement[];
      const change = { painted: res.painted, unpainted: res.unpainted, marks: ins.length, text: ins.map((m) => m.textContent).join("|"), boxed: ins.filter((m) => m.getClientRects().length > 0).length };
      (window as any).__am.unpaintChanges(md);
      return { comment, change, after: md.querySelectorAll(".fc-ins").length };
    }, [ON_TAG.id, NOTE, TABLE_RANGE] as [string, string, { start: number; end: number }]);
    assert.deepEqual(painted.comment, { marks: 1, text: "<table>", boxed: 1 }, "the comment on the tag paints one mark reading its characters, with a box");
    assert.deepEqual(painted.change, { painted: ["i1"], unpainted: [], marks: 1, text: "<table>", boxed: 1 }, "the change over the tag paints one mark reading its characters");
    assert.equal(painted.after, 0, "unpainted");
    // ── the Raw view: the same characters, the same range
    await page.evaluate(() => { const b = Array.from(document.querySelectorAll(".fileview-seg button")).find((x) => x.textContent === "Raw") as HTMLElement; b.click(); });   // the bar's Rendered|Raw pair (file-view.ts, T367)
    await page.waitForFunction(() => !!document.querySelector(".fileview-body code.hljs .fv-cl"), null, { timeout: 10000 });
    await frames(page, 2);
    const raw = await mapPassages(page, ".fileview-body code.hljs", ["__widths.csv", "beside the note t1", "Closing words t25"], NOTE, true);
    assert.equal(refusals(raw), "", "the Raw view maps the passages");
    for (const m of raw) assert.deepEqual(m.range, rangeOf(m.needle), "Raw: " + JSON.stringify(m.needle) + " at its own offsets");
    const rawTag = await page.evaluate(([src]: [string, { start: number; end: number }]) => {
      // the highlighter may split `<table>` across its spans: the Range runs from the row's text offset of the tag to its end, node by node
      const code = document.querySelector(".fileview-body code.hljs") as HTMLElement;
      const row = Array.from(code.querySelectorAll(".fv-cl")).find((r) => (r.textContent || "").includes("(<table>__widths.csv)")) as HTMLElement;
      if (!row) return { found: false };
      const walker = document.createTreeWalker(row, NodeFilter.SHOW_TEXT);
      const texts: Text[] = [];
      for (let n = walker.nextNode(); n; n = walker.nextNode()) texts.push(n as Text);
      const full = texts.map((x) => x.data).join("");
      const from = full.indexOf("<table>"), to = from + "<table>".length;
      const spot = (g: number): [Text, number] => { let acc = 0; for (const x of texts) { if (g <= acc + x.data.length) return [x, g - acc]; acc += x.data.length; } const last = texts[texts.length - 1]; return [last, last.data.length]; };
      const range = document.createRange();
      const [a, ao] = spot(from), [f, fo] = spot(to);
      range.setStart(a, ao); range.setEnd(f, fo);
      const sel = window.getSelection() as Selection;
      sel.removeAllRanges(); sel.addRange(range);
      const r = (window as any).__am.mapRawSelection(sel, code, src);
      sel.removeAllRanges();
      return { found: true, selected: range.toString(), ok: r.ok, range: r.ok ? r.range : null, quote: r.ok ? r.quote : r.reason };
    }, [NOTE, TABLE_RANGE] as [string, { start: number; end: number }]);
    assert.equal(rawTag.found, true, "the Raw row holding the tag");
    assert.deepEqual({ ok: rawTag.ok, range: rawTag.range, quote: rawTag.quote }, { ok: true, range: TABLE_RANGE, quote: "<table>" }, "Raw and Rendered agree on the tag's range");
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});
