// Two comments over one passage, in headless Chromium over the REAL viewer and panel (plans/markdown-viewer.md Slice 5, item 6;
// file-comments.ts openCovering; the sheets' `.fc-hl .fc-hl` rule; real-viewer-leg.ts: the Files pane under styles.css and
// files-pane.css, the kernel's status answered from the page, the poll answered quietly). The paint nests the marks where two
// comments overlap: the later comment's paint wraps the text where it stands, inside the earlier comment's mark, so the overlap
// wore two washes and two rings, and a click on it opened the innermost mark's card alone, the outer comment unreachable from
// that text (the Slice 5 probe (f), on this fixture's shape). Now: the nested mark's computed background is transparent and it
// draws no inset ring (one wash and one ring over the overlap; the outer mark keeps both); a real mouse click on the overlap
// opens both cards, the clicked comment's the focus (in the margin layout, level with its mark; the covering comment's card
// laid off it), in the margin layout (900 px, the aside beside the body) and the list layout (600 px, under the sheet's 680 px
// fold, the aside stacked under the body); and the same holds after a composer opened on a target in the same paragraph and was
// cancelled, since the repaint over the line boxes the target touched paints the highlights again in cards() order and the nest
// reads the same (md-config-paint-presel-scope-browser.test.ts pins that order). Legs await the DOM's own states and frames,
// never a timer. Skips LOUDLY without a playwright browser (CI installs none). Synthetic values only: an invented report,
// /repo/notes-api paths, the placeholder sid, placeholder comment ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openPanel, pageHtml, frames, REPORT, SID, MT, ORIGIN, STATUS } from "./real-viewer-leg";

const T0 = 1757145600000;
const LINE = "Intro paragraph one with several words in it.";
const NOTE = "# Report\n\nA first para. with a few words before.\n\n" + LINE + "\n\nAfter para. closing the report.\n";
/** A comment anchored on a passage (the shape the kernel's status carries); every quote recurs nowhere in the note. */
const commentOn = (id: string, ts: number, quote: string, prefix: string, suffix: string) => ({ id, author: "you", ts, body: `Note ${id}.`, anchor: { quote, prefix, suffix }, replies: [], resolved: false });
// A, the EARLIER comment (by time), over the first three words; B, the LATER one, from the second word past A's end: the overlap
// is "paragraph one", where B's first mark nests inside A's
const A = commentOn("aaaa-1", T0 + 1, "Intro paragraph one", "words before.\n\n", " with several words in i");
const B = commentOn("bbbb-2", T0 + 2, "paragraph one with several", "words before.\n\nIntro ", " words in it.\n\nAfter par");
const PARA = ".fileview-md > p:nth-of-type(2)";
const OUTER = '.fileview-body mark.fc-hl[data-id="aaaa-1"]';
const INNER = '.fileview-body mark.fc-hl[data-id="aaaa-1"] mark.fc-hl[data-id="bbbb-2"]';

/** The panel's poll answered quietly: the two HEADs return the status's own mtimes, so no tick refreshes and repaints. */
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
/** Every card has its place (style.top written): the margin layout's pass ran. */
const placed = (page: any): Promise<unknown> => page.waitForFunction(() => {
  const cards = Array.from(document.querySelectorAll(".fc-sec-cards .fc-card[data-id]"));
  return cards.length > 0 && cards.every((c) => (c as HTMLElement).style.top !== "");
}, null, { timeout: 10000 });

/** A page of the Files pane at `width`, the note open with the two comments in the kernel's status, the poll quiet, the REAL panel
 *  opened and its pass painted; in the margin layout the cards placed. Answers whether the layout is the margin one. */
async function openWith(browser: any, width: number): Promise<{ page: any; errors: string[]; margin: boolean }> {
  const page = await browser.newPage({ viewport: { width, height: 700 } });
  const errors: string[] = [];
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  const html = pageHtml("pane", { [REPORT]: NOTE }, MT);
  await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
  await page.goto(ORIGIN + "/");
  const comments = [A, B];
  const status = { ...STATUS, store: { ...STATUS.store, comments }, unsent: { ...STATUS.unsent, comments: comments.map((c) => c.id) } };
  await quietPoll(page, status);
  await page.evaluate(([p, sid, st]: [string, string, unknown]) => { (window as any).__status = st; (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID, status]);
  await page.waitForFunction(() => !!document.querySelector(".fileview-md > p"), null, { timeout: 10000 });
  await openPanel(page);
  await page.waitForFunction((sel: string) => !!document.querySelector(sel), INNER, { timeout: 10000 });
  const margin: boolean = await page.evaluate(() => getComputedStyle((document.querySelector(".fileview-body") as HTMLElement).parentElement!).flexDirection !== "column");
  if (margin) await placed(page);
  await frames(page, 3);
  return { page, errors, margin };
}
/** A passage selected as a person selects it: a Range over `length` characters from `from` in the text node under `scope` that
 *  holds it, the document's selection set to it, a mouseup on the scope, which the seam's onSelect hears and the panel answers
 *  with its float. */
const select = (page: any, scope: string, from: string, length: number): Promise<string> => page.evaluate(([scope, from, length]: [string, string, number]) => {
  const el = document.querySelector(scope) as HTMLElement;
  const nodes: Text[] = []; const walk = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
  for (let t = walk.nextNode(); t; t = walk.nextNode()) nodes.push(t as Text);
  const a = nodes.find((t) => t.data.indexOf(from) >= 0)!;
  const range = document.createRange(); const i = a.data.indexOf(from); range.setStart(a, i); range.setEnd(a, i + length);
  const sel = window.getSelection()!; sel.removeAllRanges(); sel.addRange(range);
  el.dispatchEvent(new MouseEvent("mouseup", { bubbles: true, cancelable: true, clientX: 50, clientY: 50 }));
  return sel.toString();
}, [scope, from, length]);
/** The float's Comment clicked: the composer opens and the pending target is painted. */
async function openComposer(page: any): Promise<void> {
  await page.waitForFunction(() => { const f = document.querySelector(".fc-float") as HTMLElement | null; return !!f && !f.hidden; }, null, { timeout: 5000 });
  await page.click(".fc-float");
  await page.waitForFunction(() => document.querySelectorAll(".fileview-body mark.fc-presel").length > 0, null, { timeout: 5000 });
  await frames(page, 2);
}
/** Cancel: the target unpainted. */
async function cancel(page: any): Promise<void> {
  await page.click('.fileview-aside [data-act="fccancel"]');
  await page.waitForFunction(() => document.querySelectorAll(".fileview-body mark.fc-presel").length === 0, null, { timeout: 5000 });
  await frames(page, 2);
}

type Paint = { nested: number; inverse: number; inner: { bg: string; shadow: string; outline: string }; outer: { bg: string; shadow: string } };
/** The nest as painted: B's marks inside A's and the inverse, and the computed wash and ring of the nested mark and of the outer. */
const readPaint = (page: any): Promise<Paint> => page.evaluate(([inner, outer]: [string, string]) => {
  const i = document.querySelector(inner) as HTMLElement, o = document.querySelector(outer) as HTMLElement;
  const ci = getComputedStyle(i), co = getComputedStyle(o);
  return {
    nested: document.querySelectorAll(inner).length,
    inverse: document.querySelectorAll('.fileview-body mark.fc-hl[data-id="bbbb-2"] mark.fc-hl[data-id="aaaa-1"]').length,
    inner: { bg: ci.backgroundColor, shadow: ci.boxShadow, outline: ci.outlineStyle },
    outer: { bg: co.backgroundColor, shadow: co.boxShadow },
  };
}, [INNER, OUTER]);
type Cards = { openA: boolean; openB: boolean; topA: number | null; topB: number | null; markTop: number };
/** The two cards' state, their screen tops, and the overlap mark's top. */
const readCards = (page: any): Promise<Cards> => page.evaluate((inner: string) => {
  const card = (id: string) => document.querySelector('.fc-sec-cards .fc-card[data-id="' + id + '"]') as HTMLElement | null;
  const a = card("aaaa-1"), b = card("bbbb-2");
  return {
    openA: !!a && a.classList.contains("open"), openB: !!b && b.classList.contains("open"),
    topA: a ? a.getBoundingClientRect().top : null, topB: b ? b.getBoundingClientRect().top : null,
    markTop: (document.querySelector(inner) as HTMLElement).getBoundingClientRect().top,
  };
}, INNER);
/** A real mouse click at the centre of the nested mark's box. */
async function clickOverlap(page: any): Promise<void> {
  const r = await page.evaluate((inner: string) => { const b = (document.querySelector(inner) as HTMLElement).getBoundingClientRect(); return { x: b.left + b.width / 2, y: b.top + b.height / 2 }; }, INNER);
  await page.mouse.click(r.x, r.y);
  await page.waitForFunction(() => !!document.querySelector('.fc-sec-cards .fc-card[data-id="bbbb-2"].open'), null, { timeout: 5000 });
  await frames(page, 3);
}
/** Both cards folded again by their heads (the head's own click, as Enter on it: its centre may hold a child control, the quote
 *  button, which a pointer's click there would activate instead). */
async function foldBoth(page: any): Promise<void> {
  for (const id of ["aaaa-1", "bbbb-2"]) {
    await page.evaluate((k: string) => { (document.querySelector('.fc-sec-cards .fc-card[data-id="' + k + '"] .fc-card-head') as HTMLElement).click(); }, id);
    await page.waitForFunction((k: string) => !document.querySelector('.fc-sec-cards .fc-card[data-id="' + k + '"].open'), id, { timeout: 5000 });
  }
  await frames(page, 2);
}
const near = (a: number, b: number, what: string) => assert.ok(Math.abs(a - b) <= 2, what + ": " + a + " against " + b);

test("in a browser, the real panel: two overlapping comments nest their marks, the nested mark wears no wash and no ring of its own, and a real click on the overlap opens BOTH cards with the clicked comment the focus, in the margin (900 px) and list (600 px) layouts, fresh and after a composer's open and Cancel over the same paragraph", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [width, wantMargin] of [[900, true], [600, false]] as const) {
      const at = "@" + width + "px: ";
      const { page, errors, margin } = await openWith(browser, width);
      assert.equal(margin, wantMargin, at + "the layout the width gives (the sheet folds the aside under the body at 680 px)");
      const p0 = await readPaint(page);
      assert.equal(p0.nested, 1, at + "B's first mark stands inside A's: the pass paints the later comment inside the earlier over the overlap");
      assert.equal(p0.inverse, 0, at + "and nothing of A inside B");
      assert.equal(p0.inner.bg, "rgba(0, 0, 0, 0)", at + "the nested mark's computed background is transparent (before this slice a second wash composited over the outer's)");
      assert.equal(p0.inner.shadow, "none", at + "and it draws no inset ring of its own");
      assert.notEqual(p0.outer.bg, "rgba(0, 0, 0, 0)", at + "the outer mark keeps the wash: " + p0.outer.bg);
      assert.notEqual(p0.outer.shadow, "none", at + "and the ring: " + p0.outer.shadow);
      assert.equal(p0.inner.outline, "none", at + "a located mark wears no dashed cue (the context cue is an outline the nested rule leaves alone)");
      // the click on the overlap, fresh
      const c0 = await readCards(page);
      assert.deepEqual([c0.openA, c0.openB], [false, false], at + "both cards start folded");
      await clickOverlap(page);
      const c1 = await readCards(page);
      assert.deepEqual([c1.openA, c1.openB], [true, true], at + "a click on the overlap opens the clicked comment's card AND the covering comment's (before this slice the innermost mark's alone)");
      if (margin) {
        near(c1.topB!, c1.markTop, at + "the clicked comment is the focus: its card is level with the overlap mark");
        assert.ok(Math.abs(c1.topA! - c1.markTop) > 8, at + "the covering comment's card is laid off the mark, above or below the focus: " + c1.topA + " against " + c1.markTop);
      }
      // a composer opened on a target in the same paragraph and cancelled: the repaint over the paragraph's line boxes paints the
      // two highlights again in cards() order, and the click reads the same nest
      await foldBoth(page);
      const selected = await select(page, PARA, "words in it", "words in it".length);
      assert.equal(selected, "words in it", at + "the target selected after both highlights in the paragraph");
      await openComposer(page);
      await cancel(page);
      const p1 = await readPaint(page);
      assert.deepEqual([p1.nested, p1.inverse], [1, 0], at + "after Cancel B's first mark stands inside A's again (the repaint keeps cards() order)");
      assert.equal(p1.inner.bg, "rgba(0, 0, 0, 0)", at + "and the nested mark is transparent again");
      await clickOverlap(page);
      const c2 = await readCards(page);
      assert.deepEqual([c2.openA, c2.openB], [true, true], at + "after the composer's open and Cancel the click opens both cards");
      if (margin) near(c2.topB!, c2.markTop, at + "the clicked comment is the focus after the repaint too");
      assert.deepEqual(errors, [], at + "no script error");
      await page.close();
    }
  });
});
