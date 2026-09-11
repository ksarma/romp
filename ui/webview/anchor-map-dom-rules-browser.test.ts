// The DOM's side of the Slice 5 review's round-5 text rules, over the REAL viewer and the REAL Comments panel in headless
// Chromium (real-viewer-leg.ts; the reader's own side is anchor-map-html-rules.test.ts, in node): a body `<title>` is gone from
// the rendered DOM with its text, block, div, inline and cell alike, while an svg's `<title>` stays (md-sanitize.ts
// dropBodyTitle, the shared profile's hook, so the chat's sanitizeMd drops it too); a named character reference outside the
// reader's table is decoded by the browser itself in the webview (anchor-map.ts domRefText), so `&ltimes;` reads as the glyph
// the DOM shows and `&notxyz;` as the not sign and `xyz;`; and the tokens inside an inline `<textarea>` render as the viewer
// rendered the file, a wikilink an anchor. Then the paint: Raw comments served on those passages paint in Rendered with their
// cards offering Scroll, and a comment on the text inside a body title, which nothing shows, paints nothing and its card offers
// Reveal (before: a mark inside the hidden title with no box counted as painted, and its Scroll landed on nothing; the reference
// and textarea needles matched nothing). One page, one browser: the box's browser cap. Skips LOUDLY without a playwright browser
// (CI installs none), as the other browser legs do. Synthetic values only: an invented note, /repo/notes-api paths, the
// placeholder sid. Non-ASCII characters are written as escapes throughout.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as path from "node:path";
import { inBrowser, openPanel, frames, pageHtml, ORIGIN, REPORT, SID, MT, STATUS, UI, requireCjs } from "./real-viewer-leg";
import { makeAnchor } from "./anchor-map";

const T0 = 1757145600000;
const NOTE = [
  "# Report",
  "",
  "Intro t0 alpha beta.",
  "",
  "<title>mid title t4c</title>",
  "",
  "<div><title>div title t4d</title> beside t4e</div>",
  "",
  "Para t4f <title>inline t4g</title> tail t4h.",
  "",
  "| <title>cell t4i</title> x | y |",
  "|---|---|",
  "| a | b |",
  "",
  "Drawn <svg viewBox=\"0 0 10 10\"><title>svg t4j</title><text x=\"1\" y=\"8\">glyph</text></svg> end t4k.",
  "",
  "Fish &amp; use &ltimes; for the semidirect product.",
  "",
  "<div>&notxyz; and &notni; here t6b</div>",
  "",
  "Fish &amp; para15b <textarea>t15i [[Wiki Note]] ==hi== see[^1]</textarea> tail15h",
  "",
  "[^1]: A footnote.",
  "",
  "Closing words t9z.",
  "",
].join("\n");
const LTIMES = "\u22c9", NOT = "\u00ac", NOTNI = "\u220c";

/** A comment in the host's shape on the note's passage `quote`: the exact source slice, its 24-character context, its position. */
function comment(quote: string, k: number): Record<string, unknown> {
  const at = NOTE.indexOf(quote);
  assert.ok(at >= 0, "the note holds " + JSON.stringify(quote));
  return { id: (T0 + k) + "-" + at, author: "you", ts: T0 + k, body: "A note on this.", anchor: makeAnchor(NOTE, { start: at, end: at + quote.length }), anchorAt: at, replies: [], resolved: false };
}
const IN_TITLE = comment("inline t4g", 1);                                    // inside a body title: shown nowhere
const ACROSS = comment("div title t4d</title> beside t4e", 2);                 // across the title into the text beside it
const REF = comment("use &ltimes; for the semidirect product", 3);            // an HTML5 name the table lacks
const REF_BLOCK = comment("&notxyz; and &notni; here", 4);                    // the parser's longest-head reading and an HTML5 name, in an html block
const TA = comment("t15i [[Wiki Note]] ==hi== see[^1]", 5);                  // the textarea's content, a wikilink inside it
const FINAL = comment("Closing words t9z.", 6);                              // the pass's sentinel
const id = (c: Record<string, unknown>): string => c.id as string;
const range = (c: Record<string, unknown>): { start: number; end: number } => ({ start: c.anchorAt as number, end: (c.anchorAt as number) + ((c.anchor as { quote: string }).quote).length });
const withComments = (comments: Record<string, unknown>[]): Record<string, unknown> =>
  ({ ...STATUS, store: { ...STATUS.store, comments }, storeMtimeNs: "1757145600000000021", unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null } });

/** The reader's two exports and the shared sanitizer, bundled alone as window.__am (the panel paints with its own copy inside the
 *  viewer's bundle; the answers are a function of the DOM and the source, and the sanitizer's of its profile and hooks). */
function probeBundle(): string {
  const contents = 'import { renderedQuote, stripMarkupMapped } from "./anchor-map";\nimport { sanitizeMd } from "./md-sanitize";\n'
    + '(window as any).__am = { renderedQuote, stripMarkupMapped, sanitizeMd };\n';
  const r = requireCjs("esbuild").buildSync({ stdin: { contents, resolveDir: UI, loader: "ts", sourcefile: "dom-rules-probe.ts" },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020", nodePaths: [path.join(process.cwd(), "node_modules")],
    external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent" });
  return r.outputFiles[0].text as string;
}

const markPainted = (page: any, cid: string): Promise<unknown> =>
  page.waitForFunction((c: string) => !!document.querySelector('.fileview-body [data-act="fcopen"][data-id="' + c + '"]'), cid, { timeout: 10000 });
/** Open the comment's card from its head (the clock, since the quote is the Scroll link once painted), and wait for it: a folded
 *  card renders no actions row, so Reveal, or its absence, is only readable on the OPEN card. */
async function openCard(page: any, cid: string): Promise<void> {
  const card = '.fileview-aside .fc-card[data-id="' + cid + '"]';
  await page.click(card + " .fc-card-head .fc-time");
  await page.waitForFunction((k: string) => { const c = document.querySelector(k); return !!c && c.classList.contains("open"); }, card, { timeout: 5000 });
  await frames(page, 2);
}
type Read = { marks: number; text: string; boxed: number; inTitle: number; card: boolean; open: boolean; goto: boolean; reveal: boolean };
/** The comment's marks in the Rendered view (their count, text, how many have a box, how many stand inside a `<title>`) and what its card offers. */
const readMarks = (page: any, cid: string): Promise<Read> => page.evaluate((c: string) => {
  const md = document.querySelector(".fileview-md") as HTMLElement;
  const marks = Array.from(md.querySelectorAll('.fc-hl[data-act="fcopen"][data-id="' + c + '"]')) as HTMLElement[];
  const card = document.querySelector('.fileview-aside .fc-card[data-id="' + c + '"]');
  return {
    marks: marks.length, text: marks.map((m) => m.textContent).join("|").replace(/\s+/g, " ").trim(),
    boxed: marks.filter((m) => m.getClientRects().length > 0).length, inTitle: marks.filter((m) => !!m.closest("title")).length,
    card: !!card, open: !!card && card.classList.contains("open"),
    goto: !!card && !!card.querySelector('[data-act="fcgoto"]'), reveal: !!card && !!card.querySelector('[data-act="fcreveal"]'),
  };
}, cid);

test("in a browser, the real viewer and panel on the Files pane: a body <title> is gone from the DOM with its text (the svg's stays), the reader decodes `&ltimes;` and `&notxyz;` as the DOM does and renders a textarea's wikilink as the viewer did, the comments on those passages paint with Scroll, and the comment inside the title paints nothing and offers Reveal", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const page = await browser.newPage({ viewport: { width: 900, height: 700 } });
    const errors: string[] = [];
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    const html = pageHtml("pane", { [REPORT]: NOTE }, MT);
    await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
    await page.goto(ORIGIN + "/");
    await page.evaluate(([p, sid, st]: [string, string, unknown]) => { (window as any).__status = st; (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID, withComments([FINAL, IN_TITLE, ACROSS, REF, REF_BLOCK, TA])]);
    await page.waitForFunction(() => !!document.querySelector(".fileview-md > p"), null, { timeout: 10000 });
    await frames(page, 2);
    await page.addScriptTag({ content: probeBundle() });
    // ── the DOM: no body title, the svg's title kept, nothing of the titles' text shown or held
    const dom = await page.evaluate(() => {
      const md = document.querySelector(".fileview-md") as HTMLElement;
      const titles = Array.from(md.querySelectorAll("title")).map((e) => ({ ns: e.namespaceURI === "http://www.w3.org/1999/xhtml" ? "html" : "svg", text: e.textContent, parent: (e.parentElement as Element).tagName }));
      const text = (md.textContent || "").replace(/\s+/g, " ");
      return { titles, text, innerText: md.innerText.replace(/\s+/g, " "), kinds: Array.from(md.children).map((c) => c.tagName) };
    });
    assert.deepEqual(dom.titles, [{ ns: "svg", text: "svg t4j", parent: "svg" }], "the one <title> left is the svg's, in the SVG namespace (before: five, four of them HTML titles with display none)");
    for (const gone of ["mid title t4c", "div title t4d", "inline t4g", "cell t4i"]) assert.ok(!dom.text.includes(gone), "the body title's text is gone from the DOM: " + gone + " (before: held, and shown nowhere)");
    for (const kept of ["beside t4e", "Para t4f tail t4h.", "x y", "Drawn svg t4j"]) assert.ok(dom.text.includes(kept), "the text beside the titles stays: " + kept + " in " + dom.text);
    assert.ok(!dom.kinds.includes("TITLE"), "no TITLE among the top-level elements (before: the block title stood there, hidden)");
    // ── the reader in the webview: the browser's own reading of a reference the table lacks, and the file kind's textarea
    const reads: { quote: string; needle: string; domHas: boolean }[] = await page.evaluate(([src, ranges]: [string, { start: number; end: number }[]]) => {
      const md = document.querySelector(".fileview-md") as HTMLElement;
      const hay = (md.textContent || "").replace(/\s+/g, " ");
      return ranges.map((r) => { const needle = (window as any).__am.renderedQuote(src, r).replace(/\s+/g, " ").trim(); return { quote: src.slice(r.start, r.end), needle, domHas: hay.includes(needle) }; });
    }, [NOTE, [range(REF), range(REF_BLOCK), range(TA), range(ACROSS), range(IN_TITLE)]]);
    assert.equal(reads[0].needle, "use " + LTIMES + " for the semidirect product", "`&ltimes;` reads as the browser decodes it, the glyph (before: `<imes;`, the legacy head and the rest)");
    assert.equal(reads[1].needle, NOT + "xyz; and " + NOTNI + " here", "`&notxyz;` as the not sign and `xyz;`, `&notni;` as its own glyph (before: the not sign and `ni;`)");
    assert.ok(reads[2].needle.startsWith("t15i <a href=\"Wiki%20Note.md\">Wiki Note</a> <mark class=\"md-mark\">hi</mark> see"), "the textarea's wikilink renders as the file document's anchor: " + reads[2].needle);
    assert.equal(reads[3].needle, "beside t4e", "across the title: the text beside it alone");
    assert.equal(reads[4].needle, "", "inside the title: nothing");
    for (const r of reads.slice(0, 4)) assert.equal(r.domHas, true, "the needle occurs in the DOM's text: " + JSON.stringify(r.needle));
    // ── the chat's sanitizeMd, the same hook on the same profile: a body title goes with its text, an svg's stays
    const chat: string = await page.evaluate(() => (window as any).__am.sanitizeMd('<p>a <title>t &amp; u</title> b</p>\n<svg viewBox="0 0 1 1"><title>s</title></svg>').innerHTML);
    assert.ok(!/<title>t/.test(chat) && !/t &amp; u/.test(chat) && /<p>a  b<\/p>/.test(chat), "the chat's sanitize drops the body title with its text: " + chat);
    assert.ok(/<svg[^>]*><title>s<\/title><\/svg>/.test(chat), "and keeps the svg's: " + chat);
    // ── the paint: the panel open, the sentinel painted, each card read with its actions row rendered (open)
    await openPanel(page);
    await markPainted(page, id(FINAL));
    await frames(page, 2);
    for (const c of [REF, REF_BLOCK, TA, ACROSS]) {
      await openCard(page, id(c));
      const r = await readMarks(page, id(c));
      assert.ok(r.marks > 0 && r.boxed === r.marks, JSON.stringify((c.anchor as { quote: string }).quote) + ": painted, every mark with a box (before: no mark for the reference and textarea needles)");
      assert.equal(r.inTitle, 0, "no mark inside a title");
      assert.equal(r.open && r.goto && !r.reveal, true, JSON.stringify((c.anchor as { quote: string }).quote) + ": the open card offers Scroll and no Reveal");
    }
    assert.equal((await readMarks(page, id(ACROSS))).text, "beside t4e", "the comment across the title paints the text beside it alone (before: two marks, one inside the hidden title)");
    assert.equal((await readMarks(page, id(REF))).text, "use " + LTIMES + " for the semidirect product", "the reference comment's mark reads the glyph");
    await openCard(page, id(IN_TITLE));
    const inTitle = await readMarks(page, id(IN_TITLE));
    assert.equal(inTitle.marks, 0, "the comment inside the body title paints nothing (before: one mark inside the hidden title, 0 rects, counted as painted)");
    assert.equal(inTitle.card && inTitle.open && inTitle.reveal && !inTitle.goto, true, "its open card offers Reveal and no Scroll (before: Scroll to nothing)");
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});
