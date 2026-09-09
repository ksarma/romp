// A REFLOW of the text (the pane dragged narrower, a text-size step) leaves the Comments panel's marks standing and only
// re-places its cards, in headless Chromium over the REAL module (file-view.ts fireRendered's `why`, file-comments.ts's
// onRendered hook; the 2026-09-09 stall). Before: the viewer fired onRendered on every width change and every A+/A−, and
// the panel answered every call with its whole paint pass (paintAll: unwrap every highlight and change mark, re-anchor
// every comment, re-wrap, rebuild the aside), once per animation frame of a pane drag. Measured with the bench
// (tools/viewer-resize-bench.ts) at 3,000 lines with 200 comments and 200 tracked changes, the panel open: 1.1 s of
// script per frame, 71 s for a 60-step drag; at 15,000 lines with 32 comments, 0.8 s a frame. A width change moves no
// node: a mark wrapped around a passage is still around it, so the pass rebuilt what stood. Now the hooks run with `why`
// "reflow" and the panel re-places its cards (scheduleLayout) and hides the float, nothing else; a PAINT (`why` "paint":
// new nodes from an open, a view switch, a reload) still runs the whole pass. The legs: a narrowing and an A+ over a
// report with comments and a change, the panel open: the mark elements are the same nodes afterwards (before: replaced),
// the count of paints proper (`__paints - __reflows`, real-viewer-leg.ts's probe) does not move (before: one per reflow),
// and each unpushed card's top follows its mark's by the same distance as before the reflow; then a reload with new text,
// where the marks ARE replaced and one paint proper is counted, so the paint path is shown intact. Legs await frames and
// hook counts, never a timer. Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs do.
// Synthetic values only: an invented report, /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openPanel, pageHtml, frames, LONG, LONG2, REPORT, SID, MT, MT2, ORIGIN, STATUS } from "./real-viewer-leg";

const T0 = 1757145600000;
/** One comment anchored on paragraph `n`'s first words (the shape the kernel's status carries). */
const commentOn = (n: number) => ({ id: `${T0 + n}-${n}`, author: "you", ts: T0 + n, body: `Note on paragraph ${n}.`, anchor: { quote: `Paragraph ${n}: lorem ipsum`, prefix: "", suffix: " dolor sit amet" }, replies: [], resolved: false });
// marks on paragraphs 3 and 30 (each alone in its stretch of the report: their cards are not pushed by a neighbour), on
// paragraph 4 (a line under 3: its card is pushed, so only its mark is checked) and on paragraph 60 (far down)
const COMMENTS = [commentOn(3), commentOn(4), commentOn(30), commentOn(60)];
const UNPUSHED = [COMMENTS[0].id, COMMENTS[2].id];
// one change: the first word of paragraph 6, inserted by a session (painted in Rendered as a tint, an .fc-ins mark)
const INS_AT = LONG.indexOf("Paragraph 6:");
const HUNK = { id: "h1", author: "api", ts: T0 - 30000, kind: "ins", curFrom: INS_AT, curTo: INS_AT + 9, baseFrom: INS_AT, baseTo: INS_AT, oldText: "", newText: "Paragraph", anchor: null };
const MARKS = ".fileview-body .fc-hl, .fileview-body .fc-ins";

type Placed = { paints: number; reflows: number; marks: number; stood: boolean; cards: Record<string, { card: number; mark: number }> };
/** The probe's counts, the marks (how many, and whether every element recorded by `keepMarks` is still in the document),
 *  and per card its `top` beside its mark's top edge, both measured from the body's top in the body's content. */
const read = (page: any): Promise<Placed> => page.evaluate((ids: string[]) => {
  const w = window as any; const body = document.querySelector(".fileview-body") as HTMLElement; const b0 = body.getBoundingClientRect().top - body.scrollTop;
  const marks = document.querySelectorAll(".fileview-body .fc-hl, .fileview-body .fc-ins");
  const cards: Record<string, { card: number; mark: number }> = {};
  for (const id of ids) {
    const card = document.querySelector('.fc-sec-cards .fc-card[data-id="' + id + '"]') as HTMLElement | null;
    const mark = document.querySelector('.fileview-body .fc-hl[data-id="' + id + '"]') as HTMLElement | null;
    if (card && mark) cards[id] = { card: parseFloat(card.style.top), mark: mark.getBoundingClientRect().top - b0 };
  }
  return { paints: w.__paints, reflows: w.__reflows, marks: marks.length, stood: (w.__kept as Element[] || []).every((m) => m.isConnected), cards };
}, UNPUSHED);
const keepMarks = (page: any): Promise<void> => page.evaluate((sel: string) => { (window as any).__kept = Array.from(document.querySelectorAll(sel)); }, MARKS);
/** Every card has its place (style.top written). */
const placed = (page: any): Promise<unknown> => page.waitForFunction(() => {
  const cards = Array.from(document.querySelectorAll(".fc-sec-cards .fc-card[data-id]"));
  return cards.length > 0 && cards.every((c) => (c as HTMLElement).style.top !== "");
}, null, { timeout: 10000 });
/** The hooks' frame has run (the probe's count of onRendered calls, reflow or paint, moved past `paints`), then four
 *  frames: the panel's re-place is the frame after the reflow (scheduleLayout's requestAnimationFrame, and the sizer's), and
 *  the cards' tops stand by then. The wait is on `__paints`, which moves whether the hook ran as a reflow or as a paint, so
 *  a viewer that still fires a paint here reaches the assertions below and fails on them in about a second; a wait on
 *  `__reflows` alone would time out at 10 s with no message. */
const reflowed = async (page: any, paints: number): Promise<void> => {
  await page.waitForFunction((n: number) => (window as any).__paints > n, paints, { timeout: 10000 });
  await frames(page, 4);
};

test("in a browser, the real module: a pane narrowing and a text-size step leave the panel's marks standing and re-place the cards over them, with no paint pass (before: every reflow unwrapped and re-wrapped every mark and rebuilt the aside); a reload with new text still repaints", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const page = await browser.newPage({ viewport: { width: 900, height: 600 } });
    const errors: string[] = [];
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    const html = pageHtml("pane", { [REPORT]: LONG }, MT);
    await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
    await page.goto(ORIGIN + "/");
    const status = { ...STATUS, store: { ...STATUS.store, comments: COMMENTS }, hunks: [HUNK], unsent: { ...STATUS.unsent, comments: COMMENTS.map((c) => c.id) } };
    await page.evaluate(([p, sid, st]: [string, string, unknown]) => { (window as any).__status = st; (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID, status]);
    await page.waitForFunction(() => !!document.querySelector(".fileview-md > p"), null, { timeout: 10000 });
    await openPanel(page);
    await placed(page);
    await frames(page, 2);
    await keepMarks(page);
    const r0 = await read(page);
    assert.equal(r0.marks, 5, "four highlights and one change mark painted");
    assert.ok(r0.stood, "the recorded marks are in the document");
    assert.deepEqual(Object.keys(r0.cards).sort(), [...UNPUSHED].sort(), "the two unpushed cards have a top and a mark");

    // (1) the pane narrower: paragraph 30's mark moves down as the text wraps more; the cards follow one frame later
    await page.setViewportSize({ width: 700, height: 600 });
    await reflowed(page, r0.paints);
    const r1 = await read(page);
    assert.equal(r1.reflows, r0.reflows + 1, "one reflow for the width change (the observer's frame)");
    assert.equal(r1.paints - r1.reflows, r0.paints - r0.reflows, "no paint proper: the hooks ran with why 'reflow' only");
    assert.ok(r1.stood, "the narrowing left every mark element in the document (before: the panel's pass replaced them)");
    assert.equal(r1.marks, 5, "the same five marks");
    assert.ok(r1.cards[COMMENTS[2].id].mark > r0.cards[COMMENTS[2].id].mark + 0.5, `the mark of paragraph 30 moved down with the wrap (${r0.cards[COMMENTS[2].id].mark} to ${r1.cards[COMMENTS[2].id].mark})`);
    for (const id of UNPUSHED) {
      assert.ok(Math.abs((r1.cards[id].card - r1.cards[id].mark) - (r0.cards[id].card - r0.cards[id].mark)) < 1, `${id}: the card follows its mark at the same distance (${r0.cards[id].card - r0.cards[id].mark} before, ${r1.cards[id].card - r1.cards[id].mark} after)`);
    }

    // (2) a text-size step: the text grows around the marks; the same holds
    await keepMarks(page);
    await page.click('button[aria-label="Larger text"]');
    await reflowed(page, r1.paints);
    const r2 = await read(page);
    assert.equal(r2.reflows, r1.reflows + 1, "one reflow for the step");
    assert.equal(r2.paints - r2.reflows, r1.paints - r1.reflows, "no paint proper for the step");
    assert.ok(r2.stood, "the step left every mark element in the document");
    assert.ok(r2.cards[COMMENTS[2].id].mark > r1.cards[COMMENTS[2].id].mark + 0.5, "the mark of paragraph 30 moved down as the text grew");
    for (const id of UNPUSHED) assert.ok(Math.abs((r2.cards[id].card - r2.cards[id].mark) - (r1.cards[id].card - r1.cards[id].mark)) < 1, `${id}: the card follows its mark across the step`);

    // (3) a reload with NEW text (twenty paragraphs inserted above): a paint proper, the marks re-painted over new nodes
    await keepMarks(page);
    await page.evaluate(([p, text, mt]: [string, string, string]) => { const w = window as any; w.__docs[p] = text; w.__mtime = mt; w.__seam.reload(); }, [REPORT, LONG2, MT2]);
    await page.waitForFunction((n: number) => (window as any).__paints - (window as any).__reflows > n, r2.paints - r2.reflows, { timeout: 10000 });
    await page.waitForFunction((n: number) => document.querySelectorAll(".fileview-body .fc-hl, .fileview-body .fc-ins").length >= n, 4, { timeout: 10000 });
    await frames(page, 3);
    const r3 = await read(page);
    assert.equal(r3.paints - r3.reflows, r2.paints - r2.reflows + 1, "the reload is one paint proper");
    assert.equal(r3.stood, false, "the paint replaced the marks (new nodes under the new text)");
    assert.ok(r3.marks >= 4, "the comments' highlights painted over the new text: " + r3.marks);
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});
