// The Comments panel's repaint when the pending target alone is painted or unpainted (file-comments.ts repaintPresel, paintPresel,
// lineBoxOf and trimBlanks; the Slice 4 review's rounds 14 and 15), in headless Chromium over the REAL viewer and panel
// (real-viewer-leg.ts: file-view.ts bundled as the webview build bundles it, the Files pane under styles.css and files-pane.css, the
// kernel's status answered from the page). One comment across a list item of fourteen links, which wraps at every pane width the leg
// opens; the panel opened, so its pass has painted the highlight and trimmed the wrap points' blanks (no padding-only mark). Then a
// passage is selected the way a person selects it (a Range over the links and a mouseup on the item: the seam's selection hooks show
// the panel's float) and the float's Comment is clicked: startComment paints the pending target (`.fc-presel`) over the selected
// links, inside the highlight's marks. Two selections: the whole item (Link0 to Link13), and four of its links (Link2 to Link5).
// 1. The target's 2 px side padding is in the layout, so its paint moves the item's wrap points. Before round 14 nothing measured the
//    highlight's marks again, and a blank of the highlight that was the wrap point now stood as the sheet's 4 px of padding around
//    nothing, a ringed 4 x 18 px box at the end of the line (two to four of them at 600 to 300 px with the whole item selected).
//    Round 14 trimmed the standing marks after the target's paint, which unwrapped those; but the trim never re-wraps
//    (anchor-map.ts's header), so a blank of the highlight trimmed at the OLD wrap points that renders at the new ones stood bare
//    (3 of the item's spaces with four links selected at 600 px; 39 of the 120-link item's 119 at 800 px), a gap in the ring while
//    the person typed. Since round 15 the repaint is a paint pass over the line boxes the target enters and leaves: the highlights
//    standing in them are unpainted and painted again with the target inside them, then the one trim runs (lineBoxOf; repaintPresel's
//    docblock). So while the composer is pending: no padding-only mark of either class, no bare rendered blank in the item, the
//    target's marks nested inside the highlight's (the pass's order), and the marks are what a paint pass leaves under the same
//    target (the settings signal runs paintAll with the composer standing: the same blank-mark counts), with the seam reporting
//    neither a paint nor a reflow (the path was the repaint, not the hooks).
// 2. Cancel unpaints the target (closeComposer runs the same repaint) and the wrap points move back: round 14's trim left the blanks
//    its stand had unwrapped bare, 4, 4, 3 and 2 of them at 300 to 600 px with the whole item selected, until the next paint pass (a
//    status move, a reload), the ring gapped for as long as a quiet file stayed open. Since round 15 the highlight is painted again
//    at the unpaint too: no padding-only mark, no bare blank, and the highlight's blank marks are the ones the panel's own pass
//    painted before the click, the same count.
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
type Read = { paints: number; reflows: number; hl: Marks; presel: Marks; nested: number; inverted: number; bare: string[]; column: boolean };
/** The probe's counts and, per class, the marks, the blank marks and the padding-only ones (the trim's own oracle: every text node
 *  of the mark lays out at zero width and the mark has a box of its own; the text measured node by node, as the trim reads it);
 *  the target's marks nested inside a highlight's (the pass's order) and the inverse (a highlight painted inside the target, which
 *  no pass produces); and the item's blank text nodes that render with a width and carry no mark of either class (bare). */
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
  return { paints: w.__paints, reflows: w.__reflows, hl: scan("fc-hl"), presel: scan("fc-presel"), nested: body.querySelectorAll("mark.fc-hl > mark.fc-presel").length, inverted: body.querySelectorAll("mark.fc-presel > mark.fc-hl").length, bare, column: getComputedStyle(body.parentElement!).flexDirection === "column" };
});
/** A paint pass with everything as it stands, the composer included: the shared settings signal (settings.ts onExternalSettingsChange,
 *  the `romp:settings` event) flips Show changes inline off and back on, and the panel answers each change it sees with paintAll. The
 *  note carries no change, so the marks the pass paints are the highlight's and the target's alone. */
const paintPass = (page: any): Promise<void> => page.evaluate(() => {
  const cur = JSON.parse(localStorage.getItem("romp:settings") || "{}");
  for (const v of [false, true]) { localStorage.setItem("romp:settings", JSON.stringify({ ...cur, changesInline: v })); window.dispatchEvent(new Event("romp:settings")); }
});
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

const SHAPES: Array<[string, string, string]> = [["the whole item", "Link0 docs", "Link13 docs"], ["four of its links", "Link2 docs", "Link5 docs"]];
test("in a browser, the real panel: the pending target painted over a standing comment's lines (the float's Comment on the whole item and on four of its links, at 300, 400, 500 and 600 px) repaints the highlight with the target inside it and trims once, so no padding-only mark and no bare rendered blank stands while the composer is pending or after Cancel unpaints it, the marks being a paint pass's under the same target; the seam reported no paint and no reflow for either", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const width of [300, 400, 500, 600]) for (const [shape, from, to] of SHAPES) {
      const at = "@" + width + "px, " + shape + ": ";
      const { page, errors } = await openWith(browser, width);
      const r0 = await read(page);
      assert.ok(r0.column, at + "the narrow fold (the aside under the body), the layout the scene wraps in");
      assert.ok(r0.hl.blank >= 6, at + "the comment's marks over the spaces between the links stand after the pass: " + r0.hl.blank);
      assert.deepEqual(r0.hl.paddingOnly, [], at + "the pass left no padding-only mark");
      assert.deepEqual(r0.bare, [], at + "the pass left no bare rendered blank in the item (the shape's precondition: one comment over the item shows none fresh)");
      assert.equal(r0.presel.n, 0, at + "no pending target before the selection");
      // (1) the links selected, the float's Comment clicked: the highlight repainted with the target inside it, one trim
      const selected = await select(page, from, to);
      assert.ok(selected.startsWith(from) && selected.endsWith(to), at + "the selection spans the links: " + JSON.stringify(selected.slice(0, 12) + ".." + selected.slice(-12)));
      await page.waitForFunction(() => { const f = document.querySelector(".fc-float") as HTMLElement | null; return !!f && !f.hidden; }, null, { timeout: 5000 });
      await page.click(".fc-float");
      await page.waitForFunction(() => document.querySelectorAll(".fileview-body mark.fc-presel").length > 0, null, { timeout: 5000 });
      await frames(page, 2);
      const r1 = await read(page);
      assert.ok(r1.presel.n >= 4 && r1.presel.blank >= 3, at + "the target paints the links and the spaces between them: " + r1.presel.n + " marks, " + r1.presel.blank + " blank");
      assert.equal(r1.paints, r0.paints, at + "no paint pass and no reflow for the click: the repaint's own path");
      assert.deepEqual(r1.hl.paddingOnly, [], at + "no padding-only highlight mark stands while the composer is pending (before round 14 the target's padding moved the wrap points and the highlight's blanks there stood as ringed 4 x 18 px boxes)");
      assert.deepEqual(r1.presel.paddingOnly, [], at + "the target's own marks hold no padding-only one");
      assert.deepEqual(r1.bare, [], at + "no bare rendered blank in the item while the composer is pending (round 14's trim left the highlight's blanks trimmed at the old wrap points bare where they render at the new ones)");
      assert.equal(r1.inverted, 0, at + "no highlight mark is painted inside the target: the pass's order, the target inside the highlight");
      assert.equal(r1.nested, r1.presel.n, at + "every mark of the target sits inside a highlight mark (the links are all under the comment): " + r1.nested + " of " + r1.presel.n);
      // the exact form: a paint pass under the same target paints the same marks
      await paintPass(page);
      await frames(page, 2);
      const r1b = await read(page);
      assert.equal(r1b.presel.n, r1.presel.n, at + "the target's marks are what a paint pass under it paints: " + r1b.presel.n + " against the repaint's " + r1.presel.n);
      assert.equal(r1b.hl.blank, r1.hl.blank, at + "the highlight's blank marks are what a paint pass under the same target leaves: " + r1b.hl.blank + " against the repaint's " + r1.hl.blank);
      assert.deepEqual([r1b.hl.paddingOnly, r1b.bare], [[], []], at + "the pass leaves no padding-only mark and no bare blank either");
      // (2) Cancel: the target unpainted, the wrap points back, the highlight painted again and trimmed: the pass's marks before the click
      await page.click('.fileview-aside [data-act="fccancel"]');
      await page.waitForFunction(() => document.querySelectorAll(".fileview-body mark.fc-presel").length === 0, null, { timeout: 5000 });
      await frames(page, 2);
      const r2 = await read(page);
      assert.equal(r2.paints, r1b.paints, at + "no paint pass and no reflow for the cancel either");
      assert.deepEqual(r2.hl.paddingOnly, [], at + "no padding-only highlight mark stands after the cancel");
      assert.deepEqual(r2.bare, [], at + "no bare rendered blank in the item after the cancel (round 14 left the blanks the target's stand had unwrapped bare, 4, 4, 3 and 2 of them at 300 to 600 px with the whole item selected, until the next paint pass)");
      assert.equal(r2.hl.blank, r0.hl.blank, at + "the highlight's blank marks after the cancel are the pass's before the click: " + r2.hl.blank + " against " + r0.hl.blank);
      assert.deepEqual(errors, [], at + "no script error");
      await page.close();
    }
  });
});
