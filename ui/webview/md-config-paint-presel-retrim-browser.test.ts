// The Comments panel's re-trim when the pending target alone is painted or unpainted (file-comments.ts repaintPresel, paintPresel
// and trimBlanks; the Slice 4 review's round 14), in headless Chromium over the REAL viewer and panel (real-viewer-leg.ts: file-view.ts
// bundled as the webview build bundles it, the Files pane under styles.css and files-pane.css, the kernel's status answered from the
// page). One comment across a list item of fourteen links, which wraps at every pane width the leg opens; the panel opened, so its
// pass has painted the highlight and trimmed the wrap points' blanks (no padding-only mark). Then a passage is selected the way a
// person selects it (a Range over the item and a mouseup on it: the seam's selection hooks show the panel's float) and the float's
// Comment is clicked: startComment paints the pending target (`.fc-presel`) over the item's text, inside the highlight's marks.
// 1. The target's 2 px side padding is in the layout, so its paint moves the item's wrap points, and a blank of the HIGHLIGHT that
//    is the wrap point now lays out at zero width inside a mark with a box of its own, the sheet's 4 px of padding around nothing,
//    a ringed 4 x 18 px box at the end of the line. Before round 14 repaintPresel trimmed the target's own marks alone and nothing
//    measured the highlight's again until a reflow, a figure's load, a font's arrival or the next paint pass: with the whole item
//    selected over its comment, two such marks stood at 600 px, three at 500, four at 400 and four at 300 for as long as the
//    composer was pending (round 14's probe). Since round 14 the repaint is a paint pass like paintAll's: the target is painted with
//    the trim deferred and the panel's one trim runs after it over every standing mark (trimBlanks), so no padding-only mark stands
//    after the click, the highlight's blank marks are fewer than before it (the collapsed ones unwrapped), the target's own marks
//    hold none either, and the seam reported neither a paint nor a reflow (the path was the repaint, not the hooks).
// 2. Cancel unpaints the target (closeComposer runs the same repaint) and the wrap points move back: no padding-only mark stands
//    after it either. A blank of the highlight trimmed while the target stood that renders once it is gone is not re-wrapped (the
//    trim never re-wraps: anchor-map.ts's header), and stays bare until the next paint pass, the recorded shape of plan item 10 (b)
//    under one more trigger; the leg bounds the item's bare rendered blanks after the close by the ones before the click plus the
//    marks the target's stand unwrapped, never more.
// The Comments panel polls every 2.5 s and HEADs the sidecar and the config through fetch; the harness's stub answers those paths
// 404, a move against the status's mtimes, so a tick during a scene would refresh and repaint the marks, a paint pass that would
// hide the path under test: the page answers those two HEADs with the status's own mtimes, as the kernel would (quietPoll). Legs
// await the DOM's own states and frames, never a timer. Skips LOUDLY without a playwright browser (CI installs none). Synthetic
// values only: an invented report, /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openPanel, pageHtml, frames, REPORT, SID, MT, ORIGIN, STATUS } from "./real-viewer-leg";

const T0 = 1757145600000;
const LINKS = Array.from({ length: 14 }, (_, i) => "[Link" + i + " docs](#l" + i + ")").join(" ");
/** The report: a heading, a paragraph, the list item of links, two closing paragraphs. */
const NOTE = "# Report\n\nIntro para. with a few words before the list.\n\n- " + LINKS + "\n\nBetween para. with a few more words.\n\nAfter para. closing the report.\n";
/** A comment anchored on a passage's first words (the shape the kernel's status carries); the quote recurs nowhere. */
const commentOn = (n: number, quote: string, prefix: string, suffix: string) => ({ id: `${T0 + n}-${n}`, author: "you", ts: T0 + n, body: `Note ${n}.`, anchor: { quote, prefix, suffix }, replies: [], resolved: false });
const COMMENTS = [commentOn(1, LINKS, "- ", "\n\nBetween")];

/** The panel's poll answered quietly: the two HEADs return the status's own mtimes, so no tick refreshes (the header). */
const quietPoll = (page: any, status: any): Promise<void> => page.evaluate((st: any) => {
  const w = window as any; const real = w.fetch;
  w.fetch = async function (url: string, init?: RequestInit) {
    if (init && init.method === "HEAD") {
      const m = /[?&]path=([^&]*)/.exec(String(url)); const p = m ? decodeURIComponent(m[1]) : "";
      if (p.endsWith(".json")) return new Response("", { status: 200, headers: { "X-Romp-Mtime-Ns": p.endsWith("/config.json") ? st.configMtimeNs : st.storeMtimeNs } });
    }
    return real(url, init);
  };
}, status);

type Marks = { n: number; blank: number; paddingOnly: string[] };
type Read = { paints: number; reflows: number; hl: Marks; presel: Marks; stood: boolean; bare: string[]; column: boolean };
/** The probe's counts and, per class, the marks, the blank marks and the padding-only ones (the trim's own oracle: every text node
 *  of the mark lays out at zero width and the mark has a box of its own; the text measured node by node, as the trim reads it);
 *  whether the highlight's non-blank marks recorded before still stand; and the item's blank text nodes that render with a width
 *  and carry no mark of either class (bare). */
const read = (page: any): Promise<Read> => page.evaluate(() => {
  const w = window as any; const body = document.querySelector(".fileview-body") as HTMLElement;
  const BLANK = /^(?:[^\p{L}\p{N}\p{P}\p{S}]|[\u115f\u1160\u3164\uffa0])*$/u;
  const width = (n: Node) => { const r = document.createRange(); r.selectNodeContents(n); let x = 0; for (const b of Array.from(r.getClientRects())) x += b.width; return x; };
  const textWidth = (k: Element) => { let x = 0; const walk = document.createTreeWalker(k, NodeFilter.SHOW_TEXT); for (let t = walk.nextNode(); t; t = walk.nextNode()) x += width(t); return x; };
  const scan = (cls: string) => {
    const marks = Array.from(body.querySelectorAll("mark." + cls));
    const blanks = marks.filter((k) => BLANK.test(k.textContent || ""));
    const paddingOnly = blanks.filter((k) => textWidth(k) === 0 && k.getClientRects().length > 0).map((k) => { const b = k.getBoundingClientRect(); return k.parentElement!.tagName + " " + JSON.stringify(k.textContent) + " box " + Math.round(b.width * 100) / 100 + "x" + Math.round(b.height * 100) / 100; });
    return { n: marks.length, blank: blanks.length, paddingOnly };
  };
  const bare: string[] = [];
  const walk = document.createTreeWalker(document.querySelector(".fileview-md > ul")!, NodeFilter.SHOW_TEXT);
  for (let t = walk.nextNode(); t; t = walk.nextNode()) if (BLANK.test((t as Text).data) && width(t) > 0 && !(t.parentElement && t.parentElement.closest("mark"))) bare.push(t.parentNode!.nodeName + " " + JSON.stringify((t as Text).data));
  return { paints: w.__paints, reflows: w.__reflows, hl: scan("fc-hl"), presel: scan("fc-presel"), stood: (w.__kept as Element[] || []).every((m) => m.isConnected), bare, column: getComputedStyle(body.parentElement!).flexDirection === "column" };
});
const keepMarks = (page: any): Promise<void> => page.evaluate(() => { (window as any).__kept = Array.from(document.querySelectorAll(".fileview-body mark.fc-hl")).filter((k) => !/^\s*$/.test(k.textContent || "")); });
/** Every card has its place (style.top written): the margin layout's pass ran. */
const placed = (page: any): Promise<unknown> => page.waitForFunction(() => {
  const cards = Array.from(document.querySelectorAll(".fc-sec-cards .fc-card[data-id]"));
  return cards.length > 0 && cards.every((c) => (c as HTMLElement).style.top !== "");
}, null, { timeout: 10000 });

/** A page of the Files pane at `width`, the report open with the comment in the kernel's status, the poll quiet, the REAL panel
 *  opened and its pass painted (the marks stand; the trim ran inside the pass); in the margin layout the cards placed, in the narrow
 *  fold (the row's computed flex-direction `column`, file-comments.ts marginMode) a frame awaited. */
async function openWith(browser: any, width: number): Promise<{ page: any; errors: string[] }> {
  const page = await browser.newPage({ viewport: { width, height: 700 } });
  const errors: string[] = [];
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  const html = pageHtml("pane", { [REPORT]: NOTE }, MT);
  await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
  await page.goto(ORIGIN + "/");
  const status = { ...STATUS, store: { ...STATUS.store, comments: COMMENTS }, unsent: { ...STATUS.unsent, comments: COMMENTS.map((c) => c.id) } };
  await quietPoll(page, status);
  await page.evaluate(([p, sid, st]: [string, string, unknown]) => { (window as any).__status = st; (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID, status]);
  await page.waitForFunction(() => !!document.querySelector(".fileview-md > p"), null, { timeout: 10000 });
  await openPanel(page);
  await page.waitForFunction(() => document.querySelectorAll(".fileview-body mark.fc-hl").length > 0, null, { timeout: 10000 });
  const column: boolean = await page.evaluate(() => getComputedStyle((document.querySelector(".fileview-body") as HTMLElement).parentElement!).flexDirection === "column");
  if (!column) await placed(page);
  await frames(page, 2);
  return { page, errors };
}
/** The item's links `from` to `to` selected as a person selects them (a Range from the first text node to the end of the last, the
 *  document's selection set to it, a mouseup on the item, which the seam's onSelect hears and the panel answers with its float). */
const select = (page: any, from: string, to: string): Promise<string> => page.evaluate(([from, to]: [string, string]) => {
  const li = document.querySelector(".fileview-md > ul > li") as HTMLElement;
  const nodes: Text[] = []; const walk = document.createTreeWalker(li, NodeFilter.SHOW_TEXT);
  for (let t = walk.nextNode(); t; t = walk.nextNode()) nodes.push(t as Text);
  const a = nodes.find((t) => t.data.startsWith(from))!, b = nodes.find((t) => t.data.startsWith(to))!;
  const range = document.createRange(); range.setStart(a, 0); range.setEnd(b, b.data.length);
  const sel = window.getSelection()!; sel.removeAllRanges(); sel.addRange(range);
  li.dispatchEvent(new MouseEvent("mouseup", { bubbles: true, cancelable: true, clientX: 50, clientY: 50 }));
  return sel.toString();
}, [from, to]);

test("in a browser, the real panel: the pending target painted over a standing comment's lines (the float's Comment on a selection of the whole item, at 300 and 500 px) re-trims the standing marks in the same repaint, so no padding-only highlight mark stands while the composer is pending, and none after Cancel unpaints it; the seam reported no paint and no reflow for either", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const width of [300, 500]) {
      const at = "@" + width + "px: ";
      const { page, errors } = await openWith(browser, width);
      await keepMarks(page);
      const r0 = await read(page);
      assert.ok(r0.column, at + "the narrow fold (the aside under the body), the layout the scene wraps in");
      assert.ok(r0.hl.blank >= 6, at + "the comment's marks over the spaces between the links stand after the pass: " + r0.hl.blank);
      assert.deepEqual(r0.hl.paddingOnly, [], at + "the pass left no padding-only mark");
      assert.equal(r0.presel.n, 0, at + "no pending target before the selection");
      // (1) the whole item selected, the float's Comment clicked: the target painted inside the highlight, the standing marks re-trimmed
      const selected = await select(page, "Link0 docs", "Link13 docs");
      assert.ok(selected.startsWith("Link0 docs") && selected.endsWith("Link13 docs"), at + "the selection spans the item: " + JSON.stringify(selected.slice(0, 12) + ".." + selected.slice(-12)));
      await page.waitForFunction(() => { const f = document.querySelector(".fc-float") as HTMLElement | null; return !!f && !f.hidden; }, null, { timeout: 5000 });
      await page.click(".fc-float");
      await page.waitForFunction(() => document.querySelectorAll(".fileview-body mark.fc-presel").length > 0, null, { timeout: 5000 });
      await frames(page, 2);
      const r1 = await read(page);
      assert.ok(r1.presel.n >= 14 && r1.presel.blank >= 6, at + "the target paints the links and the spaces between them: " + r1.presel.n + " marks, " + r1.presel.blank + " blank");
      assert.equal(r1.paints, r0.paints, at + "no paint pass and no reflow for the click: the repaint's own path");
      assert.ok(r1.stood, at + "the highlight's non-blank marks stand as the same nodes");
      assert.deepEqual(r1.hl.paddingOnly, [], at + "no padding-only highlight mark stands while the composer is pending (before round 14 the target's padding moved the wrap points and the highlight's blanks there stood as ringed 4 x 18 px boxes)");
      assert.ok(r1.hl.blank < r0.hl.blank, at + "the repaint's trim unwrapped the highlight's blanks the moved wrap points collapsed: " + r1.hl.blank + " blank marks against " + r0.hl.blank);
      assert.deepEqual(r1.presel.paddingOnly, [], at + "the target's own marks hold no padding-only one");
      // (2) Cancel: the target unpainted, the wrap points back; the same trim runs; a blank unwrapped meanwhile is not re-wrapped (item 10 (b))
      const unwrapped = r0.hl.blank - r1.hl.blank;
      await page.click('.fileview-aside [data-act="fccancel"]');
      await page.waitForFunction(() => document.querySelectorAll(".fileview-body mark.fc-presel").length === 0, null, { timeout: 5000 });
      await frames(page, 2);
      const r2 = await read(page);
      assert.equal(r2.paints, r0.paints, at + "no paint pass and no reflow for the cancel either");
      assert.ok(r2.stood, at + "the highlight's non-blank marks stand after the cancel");
      assert.deepEqual(r2.hl.paddingOnly, [], at + "no padding-only highlight mark stands after the cancel");
      assert.equal(r2.hl.blank, r1.hl.blank, at + "the cancel re-wraps nothing and unwraps nothing more: " + r2.hl.blank + " blank marks");
      assert.ok(r2.bare.length <= r0.bare.length + unwrapped, at + "a bare rendered blank of the item after the cancel is one the target's stand unwrapped (the recorded shape, plan item 10 (b)), never more: " + JSON.stringify(r2.bare) + " against " + r0.bare.length + " before and " + unwrapped + " unwrapped");
      assert.deepEqual(errors, [], at + "no script error");
      await page.close();
    }
  });
});
