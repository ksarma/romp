// The Comments panel's use of the layout-time trim (anchor-map.ts trimCollapsedMarks; file-comments.ts paintAll and trimBlanks, the
// Slice 4 review's round 12) in headless Chromium over the REAL viewer and panel (real-viewer-leg.ts: file-view.ts bundled as the
// webview build bundles it, the Files pane under styles.css and files-pane.css, the kernel's status answered from the page). Two
// comments over a report: one across a list item of fourteen links, one across a paragraph of the same links, each wrapping at
// every pane width the leg opens.
// 1. The pass: the panel paints every comment with the trim deferred (`trim: false`) and trims once over every mark of the pass
//    (paintAll, trimBlanks), so after the open no blank mark of zero width stands in the body (before round 12 the space at each
//    wrap point was painted as the sheet's 4 px of padding around nothing, a 4 x 18 px ringed box at the end of every wrapped line
//    of the item; the paragraph showed the same on main). A rendered blank of the two blocks left without a mark is bounded by the
//    blanks the trim unwrapped (the fixpoint's price, md-config-paint-trim-browser.test.ts point 2: a blank unwrapped as collapsed
//    can render once a later unwrap moves its line's wrap point back, and is never re-wrapped), never more.
// 2. The reflow: the pane narrowed (the viewport resized: the observer's frame fires the seam's onRendered with `why` "reflow", and
//    the panel re-places its cards and does NOT repaint), the marks stand as the same nodes, no paint proper is counted, and the
//    blank marks the new wrap points collapsed are unwrapped in the same hook (trimBlanks), so no padding-only mark stands after
//    the reflow either. A blank trimmed at the wide width that renders at the narrow one stays bare until the next paint pass, the
//    recorded stale shape, so the leg asserts nothing about bare rendered blanks after the reflow; after the paint it holds point 1's
//    bound, never an exact "every rendered blank marked" (the pass here unwraps something, an assertion of the leg, so the exact form
//    cannot apply to its scene; md-config-paint-trim-browser.test.ts holds it where nothing was unwrapped, keyed on the event).
// 3. A text-size step (A+) is a reflow too: the same holds.
// 4. Overlapping comments (round 13): four and eight comments over the one list item nest their marks (the later paint wraps the
//    text node where it stands, inside the earlier comment's mark), and the pass's one trim leaves no padding-only mark at any
//    level of a nest, fresh at 300 px and after a narrowing from 1400 px. Round 12 measured a mark with a Range over its contents,
//    which reads an inner MARK element's border box (4 px of padding a level), so a nest over a collapsed blank was peeled one level
//    per pass and four or more comments over a wrap point left ringed boxes inside one another at the cap. The padding-only oracle
//    here is the trim's own reading since round 13, a Range over each text node of the mark: a Range over the mark's contents would
//    call an outer ring of 4 px "rendered" and miss it.
// Legs await frames and hook counts, never a timer. Skips LOUDLY without a playwright browser (CI installs none). Synthetic values
// only: an invented report, /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openPanel, pageHtml, frames, REPORT, SID, MT, ORIGIN, STATUS } from "./real-viewer-leg";

const T0 = 1757145600000;
const LINKS = Array.from({ length: 14 }, (_, i) => "[Link" + i + " docs](#l" + i + ")").join(" ");
/** The report: a heading, a paragraph, the list item of links, a paragraph, the paragraph of links, a closing paragraph. */
const NOTE = "# Report\n\nIntro para. with a few words before the lists.\n\n- " + LINKS + "\n\nBetween para. with a few more words.\n\n" + LINKS + "\n\nAfter para. closing the report.\n";
/** A comment anchored on a passage's first words (the shape the kernel's status carries); the quote must recur nowhere. */
const commentOn = (n: number, quote: string, prefix: string, suffix: string) => ({ id: `${T0 + n}-${n}`, author: "you", ts: T0 + n, body: `Note ${n}.`, anchor: { quote, prefix, suffix }, replies: [], resolved: false });
const ITEM = LINKS, PARA = LINKS;
const COMMENTS = [commentOn(1, ITEM, "- ", "\n\nBetween"), commentOn(2, PARA, "words.\n\n", "\n\nAfter")];

type Read = { paints: number; reflows: number; marks: number; stood: boolean; blankMarks: number; paddingOnly: string[]; bare: string[]; maxNest: number };
/** The probe's counts, the marks (how many, whether the recorded ones still stand, how deep they nest), and the trim's two oracles
 *  over the body: the blank marks whose text lays out at zero width and that have a box of their own (padding-only; the text
 *  measured node by node, the trim's own reading, so an outer mark of a nest is read by its text and not by the inner mark's box),
 *  and the blank text nodes of the two link blocks that render with a width and carry no mark (bare). */
const read = (page: any): Promise<Read> => page.evaluate(() => {
  const w = window as any; const body = document.querySelector(".fileview-body") as HTMLElement;
  const BLANK = /^(?:[^\p{L}\p{N}\p{P}\p{S}]|[\u115f\u1160\u3164\uffa0])*$/u;
  const width = (n: Node) => { const r = document.createRange(); r.selectNodeContents(n); let x = 0; for (const b of Array.from(r.getClientRects())) x += b.width; return x; };
  const textWidth = (k: Element) => { let x = 0; const walk = document.createTreeWalker(k, NodeFilter.SHOW_TEXT); for (let t = walk.nextNode(); t; t = walk.nextNode()) x += width(t); return x; };
  const nest = (k: Element) => { let d = 0; for (let e: Element | null = k; e && e.tagName === "MARK"; e = e.parentElement) d++; return d; };
  const marks = Array.from(body.querySelectorAll("mark.fc-hl"));
  const blanks = marks.filter((k) => BLANK.test(k.textContent || ""));
  const paddingOnly = blanks.filter((k) => textWidth(k) === 0 && k.getClientRects().length > 0).map((k) => k.parentElement!.tagName + " " + JSON.stringify(k.textContent) + " nest " + nest(k) + " box " + Math.round(k.getBoundingClientRect().width * 100) / 100);
  const bare: string[] = [];
  for (const block of Array.from(body.querySelectorAll(".fileview-md > ul, .fileview-md > p")).filter((b) => b.querySelector("mark.fc-hl"))) {
    const walk = document.createTreeWalker(block, NodeFilter.SHOW_TEXT);
    for (let t = walk.nextNode(); t; t = walk.nextNode()) if (BLANK.test((t as Text).data) && width(t) > 0 && !(t.parentElement && t.parentElement.closest("mark.fc-hl"))) bare.push(t.parentNode!.nodeName + " " + JSON.stringify((t as Text).data));
  }
  return { paints: w.__paints, reflows: w.__reflows, marks: marks.length, stood: (w.__kept as Element[] || []).every((m) => m.isConnected), blankMarks: blanks.length, paddingOnly, bare, maxNest: Math.max(0, ...marks.map(nest)) };
});
const keepMarks = (page: any): Promise<void> => page.evaluate(() => { (window as any).__kept = Array.from(document.querySelectorAll(".fileview-body mark.fc-hl")).filter((k) => !/^\s*$/.test(k.textContent || "")); });
/** Every card has its place (style.top written). */
const placed = (page: any): Promise<unknown> => page.waitForFunction(() => {
  const cards = Array.from(document.querySelectorAll(".fc-sec-cards .fc-card[data-id]"));
  return cards.length > 0 && cards.every((c) => (c as HTMLElement).style.top !== "");
}, null, { timeout: 10000 });
/** The hooks' frame has run (the probe's count moved past `paints`), then four frames for the panel's re-place. */
const reflowed = async (page: any, paints: number): Promise<void> => {
  await page.waitForFunction((n: number) => (window as any).__paints > n, paints, { timeout: 10000 });
  await frames(page, 4);
};

/** A page of the Files pane at `width`, the report open with `comments` in the kernel's status, the REAL panel opened and its pass
 *  painted (the marks stand in the body; the trim runs inside the pass), then its cards placed where the aside stands beside the
 *  body (the margin layout); in the narrow fold (the sheet's container query stacks the aside under the body, the row's computed
 *  flex-direction `column`, file-comments.ts marginMode) the cards are a list with no top of their own, so a frame is awaited. */
async function openWith(browser: any, width: number, comments: unknown[]): Promise<{ page: any; errors: string[] }> {
  const page = await browser.newPage({ viewport: { width, height: 700 } });
  const errors: string[] = [];
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  const html = pageHtml("pane", { [REPORT]: NOTE }, MT);
  await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
  await page.goto(ORIGIN + "/");
  const status = { ...STATUS, store: { ...STATUS.store, comments }, unsent: { ...STATUS.unsent, comments: (comments as Array<{ id: string }>).map((c) => c.id) } };
  await page.evaluate(([p, sid, st]: [string, string, unknown]) => { (window as any).__status = st; (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID, status]);
  await page.waitForFunction(() => !!document.querySelector(".fileview-md > p"), null, { timeout: 10000 });
  await openPanel(page);
  await page.waitForFunction(() => document.querySelectorAll(".fileview-body mark.fc-hl").length > 0, null, { timeout: 10000 });
  const column: boolean = await page.evaluate(() => getComputedStyle((document.querySelector(".fileview-body") as HTMLElement).parentElement!).flexDirection === "column");
  if (!column) await placed(page);
  await frames(page, 2);
  return { page, errors };
}
/** `k` comments on the one passage, the list item of links: overlapping comments, whose marks nest. */
const overlapping = (k: number) => Array.from({ length: k }, (_, j) => commentOn(j + 1, ITEM, "- ", "\n\nBetween"));

test("in a browser, the real panel: the paint pass trims its marks once (no padding-only mark after the open, a bare rendered blank only where a mark was unwrapped), and a pane narrowing or a text-size step re-trims the standing marks in the reflow hook with no paint pass", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const page = await browser.newPage({ viewport: { width: 1000, height: 700 } });
    const errors: string[] = [];
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    const html = pageHtml("pane", { [REPORT]: NOTE }, MT);
    await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
    await page.goto(ORIGIN + "/");
    const status = { ...STATUS, store: { ...STATUS.store, comments: COMMENTS }, unsent: { ...STATUS.unsent, comments: COMMENTS.map((c) => c.id) } };
    await page.evaluate(([p, sid, st]: [string, string, unknown]) => { (window as any).__status = st; (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID, status]);
    await page.waitForFunction(() => !!document.querySelector(".fileview-md > p"), null, { timeout: 10000 });
    await openPanel(page);
    await placed(page);
    await frames(page, 2);
    await keepMarks(page);
    // (1) the pass: both comments painted across their links, every wrap point's blank trimmed, a bare rendered blank only where a mark was unwrapped
    const r0 = await read(page);
    assert.ok(r0.marks >= 28, "the two comments paint their fourteen links each and the spaces between: " + r0.marks + " marks");
    assert.ok(r0.blankMarks >= 20, "the spaces between the links carry marks: " + r0.blankMarks);
    assert.deepEqual(r0.paddingOnly, [], "no blank mark of zero width stands after the pass (the wrap points' spaces were trimmed)");
    const unwrapped = 2 * 13 - r0.blankMarks;                                  // thirteen spaces in each block of fourteen links
    assert.ok(unwrapped > 0, "the wrap points' blanks were unwrapped: " + unwrapped);
    assert.ok(r0.bare.length <= unwrapped, "a rendered blank of the two commented blocks left without a mark is one the fixpoint unwrapped and a later unwrap brought back onto its line, never more: " + JSON.stringify(r0.bare) + " against " + unwrapped + " unwrapped");
    // (2) the pane narrower: a reflow, no paint proper; the marks stand; the new wrap points' blanks are unwrapped in the hook
    await page.setViewportSize({ width: 560, height: 700 });
    await reflowed(page, r0.paints);
    const r1 = await read(page);
    assert.equal(r1.reflows, r0.reflows + 1, "one reflow for the width change (the observer's frame)");
    assert.equal(r1.paints - r1.reflows, r0.paints - r0.reflows, "no paint proper: the hooks ran with why 'reflow' only");
    assert.ok(r1.stood, "the narrowing left every non-blank mark element in the document");
    assert.ok(r1.marks < r0.marks, "the re-trim unwrapped the blank marks the new wrap points collapsed: " + r1.marks + " marks against " + r0.marks);
    assert.deepEqual(r1.paddingOnly, [], "no blank mark of zero width stands after the reflow (the panel re-trimmed in the hook)");
    // (3) a text-size step: a reflow too, the same holds
    await keepMarks(page);
    await page.click('button[aria-label="Larger text"]');
    await reflowed(page, r1.paints);
    const r2 = await read(page);
    assert.equal(r2.reflows, r1.reflows + 1, "one reflow for the step");
    assert.equal(r2.paints - r2.reflows, r1.paints - r1.reflows, "no paint proper for the step");
    assert.ok(r2.stood, "the step left every non-blank mark element in the document");
    assert.deepEqual(r2.paddingOnly, [], "no blank mark of zero width stands after the step");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

test("in a browser, the real panel: four and eight comments over one wrapping list item nest their marks one level per comment, and the pass's one trim leaves no padding-only mark at any level of a nest, fresh at 300 px and after a narrowing from 1400 px (round 12 peeled a nest one level per pass and left ringed boxes inside one another at its cap)", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const k of [4, 8]) {
      const what = k + " comments over the item";
      // fresh at 300 px: the item wraps at every link or two
      const fresh = await openWith(browser, 300, overlapping(k));
      const r0 = await read(fresh.page);
      assert.equal(r0.maxNest, k, what + " @300px: the marks nest one level per comment");
      assert.ok(r0.blankMarks > 0, what + " @300px: the rendered spaces between the links carry marks: " + r0.blankMarks);
      assert.deepEqual(r0.paddingOnly, [], what + " @300px: no padding-only mark at any level after the pass");
      assert.deepEqual(fresh.errors, [], what + " @300px: no script error");
      await fresh.page.close();
      // painted wide, the pane narrowed to 300 px: the reflow hook's re-trim, no paint proper
      const wide = await openWith(browser, 1400, overlapping(k));
      const w0 = await read(wide.page);
      assert.equal(w0.maxNest, k, what + " @1400px: the marks nest");
      await wide.page.setViewportSize({ width: 300, height: 700 });
      await reflowed(wide.page, w0.paints);
      const w1 = await read(wide.page);
      assert.equal(w1.paints - w1.reflows, w0.paints - w0.reflows, what + " narrowed: no paint proper, the hooks ran with why 'reflow' only");
      assert.ok(w1.marks < w0.marks, what + " narrowed: the re-trim unwrapped the blank marks the new wrap points collapsed: " + w1.marks + " marks against " + w0.marks);
      assert.deepEqual(w1.paddingOnly, [], what + " narrowed 1400 -> 300px: no padding-only mark at any level after the reflow's re-trim");
      assert.deepEqual(wide.errors, [], what + " narrowed: no script error");
      await wide.page.close();
    }
  });
});
