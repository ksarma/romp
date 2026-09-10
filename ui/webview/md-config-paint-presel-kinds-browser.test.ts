// The Comments panel's repaint of the pending target measures nothing when no Rendered mark came or went (file-comments.ts
// repaintPresel; the Slice 4 review's round 15), in headless Chromium over the REAL viewer and panel (real-viewer-leg.ts: file-view.ts
// bundled as the webview build bundles it, the Files pane under styles.css and files-pane.css, the kernel's status answered from the
// page). One comment across a list item of 120 links (some 200 marks, half of them the spaces between the links, the trim's
// candidates) and one recorded change (an inserted word in the paragraph before it, so a change card stands). Eleven call sites run
// repaintPresel when a composer opens, closes or moves; a composer of a kind that paints no target (a reply, a comment on a deletion
// or a detached change, which startChangeComment opens by id alone, a re-place, a comment on the file, a region, a refusal) changes
// no line box, and the Raw view's row mark is no Rendered mark. Round
// 14 ran the trim on every repaint regardless: a layout forced and a Range.getClientRects per blank candidate of every standing mark,
// 22 to 27 ms per open or close on the paragraph of 5,000 links where nothing could have collapsed (the layout was the one the last
// trim measured), an inexact trigger (the root CLAUDE.md's Design section). Since round 15 the repaint reads the line boxes the
// target's marks leave and enter, and with none it trims nothing (repaintPresel's docblock). The leg wraps Range.prototype.getClientRects
// to count the measurements and watches anchor-map's TRIM_STATS.passes for the trim's resets (one per trimCollapsedMarks call):
// 1. Comment on this file opened and cancelled, Reply on the comment's card opened and cancelled, Comment on this change on a
//    deletion's card (by id alone: a deletion has no span in the text) opened and cancelled: zero measurements and zero trims for
//    each of the six clicks. A re-place and a region composer take the same branch (the composer's kind is not "comment",
//    paintPresel paints nothing); they need a drawable pointer and a figure in view, which this page does not carry.
// 2. The float's Comment on a selection of eleven of the links, then Cancel: the target's marks come and go, the highlight is
//    repainted with them (the presel-retrim leg pins the marks), and each click trims once with measurements, so the count is the
//    event's and not a count of zero everywhere. Comment on this change on the spanned insertion's card is the same event over the change's
//    span (startChangeComment's passage composer): the target comes and goes, one trim each.
// The panel's poll is answered quietly (quietPoll, as the presel-retrim leg does). Legs await the DOM's own states and frames, never
// a timer. Skips LOUDLY without a playwright browser (CI installs none). Synthetic values only: an invented report, /repo/notes-api
// paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openPanel, pageHtml, frames, REPORT, SID, MT, ORIGIN, STATUS } from "./real-viewer-leg";

const T0 = 1757145600000;
const LINKS = Array.from({ length: 120 }, (_, i) => "[Link" + i + " docs](#l" + i + ")").join(" ");
const INTRO = "Intro para. with a few words before the list.";
/** The report: a heading, the intro paragraph (its inserted word is the change), the list item of links, two closing paragraphs. */
const NOTE = "# Report\n\n" + INTRO + "\n\n- " + LINKS + "\n\nBetween para. with a few more words.\n\nAfter para. closing the report.\n";
const commentOn = (n: number, quote: string, prefix: string, suffix: string) => ({ id: `${T0 + n}-${n}`, author: "you", ts: T0 + n, body: `Note ${n}.`, anchor: { quote, prefix, suffix }, replies: [], resolved: false });
const COMMENT = commentOn(1, LINKS, "- ", "\n\nBetween");
/** The change: "few " inserted in the intro (the status's hunk indexes the text as the host read it, which is the note's). */
const AT = NOTE.indexOf("few ");
const HUNK = { id: "s1", author: "api", ts: T0 + 500, kind: "ins", curFrom: AT, curTo: AT + 4, baseFrom: AT, baseTo: AT, oldText: "", newText: "few ", anchor: null };
/** The deletion: a word gone from the Between paragraph. No span in the text, so its Comment on this change is by id alone
 *  (startChangeComment) and paints no target; the insertion's, spanned, paints one over the inserted word. */
const DEL_AT = NOTE.indexOf("more words");
const DEL = { id: "s2", author: "api", ts: T0 + 600, kind: "del", curFrom: DEL_AT, curTo: DEL_AT, baseFrom: DEL_AT, baseTo: DEL_AT + 8, oldText: "several ", newText: "", anchor: null };

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
/** The counters: Range.prototype.getClientRects wrapped (every measurement the trim or anything else takes), and anchor-map's
 *  TRIM_STATS.passes watched for its reset to 0, which trimCollapsedMarks does once per call. */
const install = (page: any): Promise<void> => page.evaluate(() => {
  const w = window as any; w.__rects = 0; const orig = Range.prototype.getClientRects;
  Range.prototype.getClientRects = function () { w.__rects++; return orig.call(this); };
  w.__trims = 0; const stats = w.FV.TRIM_STATS; let passes = stats.passes;
  Object.defineProperty(stats, "passes", { configurable: true, get: () => passes, set: (x: number) => { if (x === 0) w.__trims++; passes = x; } });
});
type Click = { trims: number; rects: number; presel: number; composer: boolean };
/** Click a control and read the trims and measurements its handler made, synchronously, with the target's marks and the box's state after. */
const clickCount = (page: any, sel: string): Promise<Click> => page.evaluate((s: string) => {
  const w = window as any; const el = document.querySelector(s) as HTMLElement | null;
  if (!el) throw new Error("no control " + s);
  const tr = w.__trims, rc = w.__rects;
  el.click();
  const box = document.querySelector(".fc-composer") as HTMLElement | null;
  return { trims: w.__trims - tr, rects: w.__rects - rc, presel: document.querySelectorAll(".fileview-body mark.fc-presel").length, composer: !!box && !box.hidden };
}, sel);
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

test("in a browser, the real panel: a composer that paints no target (Comment on this file, Reply on a comment, Comment on a deletion) opens and cancels with zero Range measurements and zero trims, where the float's Comment on a selection and its Cancel each trim once with measurements, and Comment on a spanned change once on open and once on Cancel", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const page = await browser.newPage({ viewport: { width: 1000, height: 700 } });
    const errors: string[] = [];
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    const html = pageHtml("pane", { [REPORT]: NOTE }, MT);
    await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
    await page.goto(ORIGIN + "/");
    const status = { ...STATUS, hunks: [HUNK, DEL], store: { ...STATUS.store, comments: [COMMENT] }, unsent: { ...STATUS.unsent, comments: [COMMENT.id] } };
    await quietPoll(page, status);
    await install(page);
    await page.evaluate(([p, sid, st]: [string, string, unknown]) => { (window as any).__status = st; (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID, status]);
    await page.waitForFunction(() => !!document.querySelector(".fileview-md > p"), null, { timeout: 10000 });
    await openPanel(page);
    await page.waitForFunction(() => document.querySelectorAll(".fileview-body mark.fc-hl").length > 100, null, { timeout: 10000 });
    await frames(page, 3);
    const standing = await page.evaluate(() => ({ hl: document.querySelectorAll(".fileview-body mark.fc-hl").length, ins: document.querySelectorAll(".fileview-body .fc-ins").length, cards: document.querySelectorAll(".fc-sec-cards .fc-card").length }));
    assert.ok(standing.hl > 100, "the comment's marks stand over the 120 links and their spaces: " + standing.hl);
    assert.ok(standing.ins >= 1, "the change's mark stands in the intro: " + standing.ins);
    assert.ok(standing.cards >= 3, "a comment card and two change cards: " + standing.cards);
    // (1) the kinds that paint no target: six clicks, none measures
    // a comment's Reply stands on its OPEN card (renderCard): the card is opened by a click on it first (fccard, the head's action);
    // a change card offers its Comment on this change closed (renderChangeCard)
    const kinds: Array<[string, string, string | null]> = [
      ["Comment on this file", '.fileview-aside [data-act="fcfile"]', null],
      ["Reply on the comment", '.fileview-aside [data-act="fcreply"][data-id="' + COMMENT.id + '"]', '.fc-sec-cards .fc-card[data-id="' + COMMENT.id + '"]'],
      ["Comment on a deletion", '.fileview-aside [data-act="fcchangecomment"][data-id="' + DEL.id + '"]', '.fc-sec-cards .fc-card[data-change="' + DEL.id + '"]'],
    ];
    for (const [name, sel, card] of kinds) {
      if (card && !(await page.$(sel))) { await page.click(card); await frames(page, 2); }
      const open = await clickCount(page, sel);
      assert.ok(open.composer, name + ": the box opens");
      assert.equal(open.presel, 0, name + ": no pending target is painted");
      assert.deepEqual([open.trims, open.rects], [0, 0], name + " opened: no trim and no Range measurement (round 14 measured every standing mark's blank candidates on this click): " + JSON.stringify(open));
      await frames(page, 1);
      const cancel = await clickCount(page, '.fileview-aside [data-act="fccancel"]');
      assert.ok(!cancel.composer, name + ": Cancel closes the box");
      assert.deepEqual([cancel.trims, cancel.rects], [0, 0], name + " cancelled: no trim and no Range measurement: " + JSON.stringify(cancel));
      await frames(page, 1);
    }
    // (2) the target's paint and unpaint: the event, each with one trim and its measurements
    const selected = await select(page, "Link50 docs", "Link60 docs");
    assert.ok(selected.startsWith("Link50 docs") && selected.endsWith("Link60 docs"), "the selection spans eleven links: " + JSON.stringify(selected.slice(0, 12) + ".." + selected.slice(-12)));
    await page.waitForFunction(() => { const f = document.querySelector(".fc-float") as HTMLElement | null; return !!f && !f.hidden; }, null, { timeout: 5000 });
    const open = await clickCount(page, ".fc-float");
    assert.ok(open.presel >= 11 && open.composer, "the float's Comment paints the target over the links and opens the box: " + JSON.stringify(open));
    assert.equal(open.trims, 1, "the target's paint trims once, the pass's one batched trim: " + JSON.stringify(open));
    assert.ok(open.rects > 0, "…with measurements over the standing marks' blank candidates: " + open.rects);
    await frames(page, 1);
    const cancel = await clickCount(page, '.fileview-aside [data-act="fccancel"]');
    assert.equal(cancel.presel, 0, "Cancel unpaints the target");
    assert.equal(cancel.trims, 1, "the target's unpaint trims once as well: " + JSON.stringify(cancel));
    assert.ok(cancel.rects > 0, "…with measurements: " + cancel.rects);
    // (3) Comment on this change on the spanned insertion: the target comes and goes over the inserted word, one trim each
    const changeSel = '.fileview-aside [data-act="fcchangecomment"][data-id="' + HUNK.id + '"]';
    if (!(await page.$(changeSel))) { await page.click('.fc-sec-cards .fc-card[data-change="' + HUNK.id + '"]'); await frames(page, 2); }
    const onChange = await clickCount(page, changeSel);
    assert.ok(onChange.presel >= 1 && onChange.composer, "Comment on this change paints the target over the inserted word and opens the box: " + JSON.stringify(onChange));
    assert.equal(onChange.trims, 1, "the target's paint trims once, the pass's one batched trim: " + JSON.stringify(onChange));
    assert.ok(onChange.rects > 0, "…with measurements over the standing marks' blank candidates: " + onChange.rects);
    await frames(page, 1);
    const offChange = await clickCount(page, '.fileview-aside [data-act="fccancel"]');
    assert.equal(offChange.presel, 0, "Cancel unpaints the target");
    assert.equal(offChange.trims, 1, "the target's unpaint trims once as well: " + JSON.stringify(offChange));
    assert.ok(offChange.rects > 0, "…with measurements: " + offChange.rects);
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});
