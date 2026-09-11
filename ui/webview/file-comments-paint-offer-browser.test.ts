// The Comment float across a paint the panel makes with no gesture, in headless Chromium over the REAL viewer and panel (plans/
// markdown-viewer.md Slice 5, item 9; file-comments.ts onSelectionChange, afterPaint, offeredFor; the Slice 5 review, round 1;
// real-viewer-leg.ts: the Files pane under styles.css and files-pane.css). A peer's comment lands through the REAL poll (the store's
// HEAD answers a moved mtime, the next tick refreshes, applyStatus runs paintAll), which unwraps and re-wraps every highlight. A
// selection drawn from the first character of a highlight into the plain text after it has an end inside the mark's text node, and
// the unwrap collapses that end to the mark's place: the selection is cut short to the part after the mark (main's behaviour too),
// and Chromium fires selectionchange for the move. The listener compared the moved ends with the OFFER's, read the change as a new
// selection of the person's, and re-showed a float a scroll had hidden, beside the truncated passage, with no gesture (the review's
// probe: the button's inline left equal to showFloat's arithmetic for " ipsum d"). Now paintAll ends by reading the selection as it
// left it into the record the listener compares with (afterPaint), so the paint's own event is no offer: the hidden float stays
// hidden and a shown one stays where it was, and the person's next keyboard change offers as before. The review's round 2 added the
// case where the paint leaves NOTHING selected and Chromium fires no selectionchange at all: a highlight that is its paragraph's
// whole text is the <p>'s only child, so the unwrap and the wrap again of its mark collapse a selection inside it to the paragraph,
// and the event fires for a merged or split text node alone (the prefix highlight of the first leg, beside plain text, fires it; a
// lone-child mark does not), so the listener never saw the collapse and the float stood beside nothing until a click on it hid it
// and opened no composer. Now paintAll ends by hiding a passage's float it left beside no selection (afterPaint, passageGone). Legs
// await the DOM's own states (the peer's mark appearing, the selectionchange count moving) and frames, never a timer; the poll's own
// interval is the panel's. Each leg asserts what the browser fired for the paint's move of the selection, its premise: one or more
// events for the prefix highlight, none for the lone-child mark (the Slice 5 review, round 3: a browser firing one there would hide
// the float through the listener's own collapsed-selection guard, and the leg would pass without reaching afterPaint's hide; the
// count read into an assertion message pinned nothing). Skips LOUDLY without a playwright browser (CI installs none). Synthetic
// values only: an invented report, /repo/notes-api paths, the placeholder sid, invented comment ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, openPanel, frames, REPORT, STATUS } from "./real-viewer-leg";

const T0 = 1757145600000;
const NOTE = "# Report\n\nParagraph 1: alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma tau.\n\n"
  + "Paragraph 2: lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor incididunt ut labore.\n\n"
  + "Paragraph 3: after words closing the report with a few more words so the line wraps somewhere.\n\n"
  + Array.from({ length: 40 }, (_, i) => `Filler ${i + 1}: more text so the body scrolls in a 700 px pane, long enough to wrap once or twice.`).join("\n\n") + "\n";
const commentOn = (id: string, ts: number, quote: string, prefix: string, suffix: string) =>
  ({ id, author: "you", ts, body: `Note ${id}.`, anchor: { quote, prefix, suffix }, replies: [], resolved: false });
const A = commentOn("aaaa-1", T0 + 1, "Paragraph 2: lorem", "sigma tau.\n\n", " ipsum dolor sit amet");
const C = commentOn("cccc-3", T0 + 3, "Paragraph 3: after", "labore.\n\n", " words closing the");
const P2 = "Paragraph 2: lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor incididunt ut labore.";
const W = commentOn("wwww-2", T0 + 2, P2, "sigma tau.\n\n", "\n\nParagraph 3");   // the whole of paragraph 2: its mark is the <p>'s only child
const MARK_A = '.fileview-body mark.fc-hl[data-id="aaaa-1"]', MARK_C = '.fileview-body mark.fc-hl[data-id="cccc-3"]', MARK_W = '.fileview-body mark.fc-hl[data-id="wwww-2"]';
const STORE_MT_1 = "1757145600000000002", STORE_MT_2 = "1757145600000000777";
const withComments = (comments: unknown[], storeMtimeNs: string) => ({ ...STATUS, storeMtimeNs, store: { ...STATUS.store, comments }, unsent: { ...STATUS.unsent, comments: comments.map((c: any) => c.id) } });

type Scene = { hidden: boolean; left: number; top: number; selected: string; collapsed: boolean; expectedLeft: number; expectedTop: number; selChanges: number; anchorIsP: boolean; pChildren: string; composer: boolean };
/** The float's state and inline place, the selection's text and whether it is collapsed, where showFloat would put the button for the
 *  selection's last range now, the count of selectionchange events the page has seen since the counter was armed, the anchor's
 *  paragraph's child nodes when the anchor is one, and whether a composer stands. */
const scene = (page: any): Promise<Scene> => page.evaluate(() => {
  const w = window as any; const f = document.querySelector(".fc-float") as HTMLElement; const sel = getSelection()!;
  const r = sel.rangeCount ? sel.getRangeAt(sel.rangeCount - 1).getBoundingClientRect() : null;
  const anchorIsP = !!sel.anchorNode && sel.anchorNode.nodeName === "P";
  return { hidden: f.hidden, left: parseFloat(f.style.left), top: parseFloat(f.style.top), selected: String(sel), collapsed: sel.isCollapsed,
    expectedLeft: r ? Math.min(Math.max(8, r.right + 6), window.innerWidth - 90) : NaN, expectedTop: r ? Math.min(Math.max(8, r.top - 30), window.innerHeight - 34) : NaN,
    selChanges: w.__selChanges as number, anchorIsP, pChildren: anchorIsP ? Array.from(sel.anchorNode!.childNodes).map((c) => c.nodeName).join(",") : "",
    composer: !!document.querySelector(".fileview-aside .fc-composer .fc-input") };
});
const near = (a: number, b: number, what: string) => assert.ok(Math.abs(a - b) < 0.01, what + ": " + a + " against " + b);

/** The page with `comments` on the note and the panel open: the store's and the config's HEADs answered from a mutable mtime (equal
 *  to the status's the poll is quiet; moved, the next tick refreshes and applyStatus paints), a selectionchange counter; awaited on
 *  the mark `markSel`. */
async function openWith(browser: any, comments: unknown[], markSel: string): Promise<{ page: any; errors: string[] }> {
  const { page, errors } = await openViewer(browser, "pane", 900, 700, { docs: { [REPORT]: NOTE } });
  await page.evaluate(([st, configMt]: [unknown, string]) => {
    const w = window as any; w.__status = st; w.__storeMtime = (st as any).storeMtimeNs;
    const real = w.fetch;
    w.fetch = async function (url: string, init?: RequestInit) {
      if (init && init.method === "HEAD") {
        const m = /[?&]path=([^&]*)/.exec(String(url)); const p = m ? decodeURIComponent(m[1]) : "";
        if (p.endsWith(".json")) return new Response("", { status: 200, headers: { "X-Romp-Mtime-Ns": p.endsWith("/config.json") ? configMt : w.__storeMtime } });
      }
      return real(url, init);
    };
    w.__selChanges = 0; document.addEventListener("selectionchange", () => { w.__selChanges++; });
  }, [withComments(comments, STORE_MT_1), STATUS.configMtimeNs]);
  await openPanel(page);
  await page.waitForFunction((s: string) => !!document.querySelector(s), markSel, { timeout: 10000 });
  await frames(page, 3);
  return { page, errors };
}
/** The page with comment A on the second paragraph (a prefix of it, plain text after the mark). */
const openWithA = (browser: any): Promise<{ page: any; errors: string[] }> => openWith(browser, [A], MARK_A);
/** A real mouse drag inside a highlight's text, from its character `from` to its character `to`, so both ends of the selection lie in
 *  the mark's text node; the seam's mouseup offers the float. */
async function dragInside(page: any, markSel: string, from: number, to: number): Promise<void> {
  await page.evaluate(() => getSelection()!.removeAllRanges());
  const r = await page.evaluate(([s, a, b]: [string, number, number]) => {
    const t = (document.querySelector(s) as HTMLElement).firstChild as Text;
    const ra = document.createRange(); ra.setStart(t, a); ra.setEnd(t, a + 1); const x = ra.getBoundingClientRect();
    const rb = document.createRange(); rb.setStart(t, b - 1); rb.setEnd(t, b); const y = rb.getBoundingClientRect();
    return { x1: x.left + 1, y1: x.top + x.height / 2, x2: y.right - 1, y2: y.top + y.height / 2 };
  }, [markSel, from, to]);
  await page.mouse.move(r.x1, r.y1); await page.mouse.down(); await page.mouse.move(r.x2, r.y2, { steps: 6 }); await page.mouse.up();
  await page.waitForFunction(() => { const f = document.querySelector(".fc-float") as HTMLElement | null; return !!f && !f.hidden; }, null, { timeout: 5000 });
  await frames(page, 2);
}
/** A real mouse drag from the highlight's first character to `n` characters into the text node right after it, so the selection
 *  starts inside the mark's text and ends in the plain text; the seam's mouseup offers the float. */
async function dragAcross(page: any, markSel: string, n: number): Promise<void> {
  await page.evaluate(() => getSelection()!.removeAllRanges());
  const r = await page.evaluate(([s, k]: [string, number]) => {
    const m = document.querySelector(s) as HTMLElement; const t0 = m.firstChild as Text; const after = m.nextSibling as Text;
    const a = document.createRange(); a.setStart(t0, 0); a.setEnd(t0, 1); const ra = a.getBoundingClientRect();
    const b = document.createRange(); b.setStart(after, k - 1); b.setEnd(after, k); const rb = b.getBoundingClientRect();
    return { x1: ra.left + 1, y1: ra.top + ra.height / 2, x2: rb.right - 1, y2: rb.top + rb.height / 2 };
  }, [markSel, n]);
  await page.mouse.move(r.x1, r.y1); await page.mouse.down(); await page.mouse.move(r.x2, r.y2, { steps: 6 }); await page.mouse.up();
  await page.waitForFunction(() => { const f = document.querySelector(".fc-float") as HTMLElement | null; return !!f && !f.hidden; }, null, { timeout: 5000 });
  await frames(page, 2);
}
/** The peer's comment C lands through the poll beside `standing`: the status gains it under a moved store mtime, the HEAD reports the
 *  move, the tick refreshes and paints; awaited on C's mark and then, where the paint's move of the selection fires one
 *  (`selChangesBefore` given), on that selectionchange. */
async function peerCommentLands(page: any, selChangesBefore: number | null, standing: unknown[] = [A]): Promise<void> {
  await page.evaluate(([st]: [unknown]) => { const w = window as any; w.__status = st; w.__storeMtime = (st as any).storeMtimeNs; }, [withComments([...standing, C], STORE_MT_2)]);
  await page.waitForFunction((s: string) => !!document.querySelector(s), MARK_C, { timeout: 15000 });
  if (selChangesBefore !== null) await page.waitForFunction((n: number) => (window as any).__selChanges > n, selChangesBefore, { timeout: 5000 });
  await frames(page, 4);
}

test("in a browser, the real viewer and panel: a peer's comment landing through the poll repaints the highlights and cuts a selection overlapping one short; the float a scroll hid stays hidden (before: re-shown beside the truncated passage with no gesture), a shown float stays where it was, and the next keyboard change offers", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    // leg 1: the float hidden by a scroll when the poll lands
    {
      const { page, errors } = await openWithA(browser);
      await dragAcross(page, MARK_A, 8);
      let s = await scene(page);
      assert.equal(s.selected, "Paragraph 2: lorem ipsum d", "the drag selected the highlight and eight characters after it");
      assert.equal(s.hidden, false, "the drag's mouseup offers the float");
      await page.evaluate(() => { (document.querySelector(".fileview-body") as HTMLElement).scrollTop += 40; });
      await page.waitForFunction(() => (document.querySelector(".fc-float") as HTMLElement).hidden, null, { timeout: 5000 });
      await frames(page, 2);
      s = await scene(page);
      assert.equal(s.hidden, true, "hidden by the scroll that moved the passage");
      const hiddenLeft = s.left, changes = s.selChanges;
      await peerCommentLands(page, changes);
      s = await scene(page);
      assert.equal(s.selected, " ipsum d", "the paint cut the selection to the part after the mark (the unwrap collapsed its start to the mark's place)");
      assert.equal(s.anchorIsP, true, "...its start now the paragraph itself");
      assert.ok(s.selChanges > changes, "and Chromium fired selectionchange for the move");
      assert.equal(s.hidden, true, "the paint's own selectionchange is no offer: the float stays hidden (before: shown beside the truncated selection)");
      assert.equal(s.left, hiddenLeft, "...and keeps the place it was hidden at, not showFloat's for the truncated selection");
      // the person's next keyboard change offers, beside the selection as it stands
      await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
      await page.keyboard.down("Shift"); await page.keyboard.press("ArrowRight"); await page.keyboard.up("Shift");
      await page.waitForFunction(() => String(getSelection()) === " ipsum do", null, { timeout: 5000 });
      await page.waitForFunction(() => { const f = document.querySelector(".fc-float") as HTMLElement; return !f.hidden; }, null, { timeout: 5000 });
      s = await scene(page);
      assert.equal(s.hidden, false, "the keyboard's change offers the float"); near(s.left, s.expectedLeft, "beside the selection's end"); near(s.top, s.expectedTop, "on its line");
      assert.deepEqual(errors, [], "no script error");
      await page.close();
    }
    // leg 2: the float SHOWN when the poll lands: it stays as the paint found it (where main leaves it), and moves for the next change
    {
      const { page, errors } = await openWithA(browser);
      await dragAcross(page, MARK_A, 8);
      let s = await scene(page);
      assert.equal(s.hidden, false); const offeredLeft = s.left, offeredTop = s.top, changes = s.selChanges;
      await peerCommentLands(page, changes);
      s = await scene(page);
      assert.equal(s.selected, " ipsum d", "the paint cut the selection short here too");
      assert.equal(s.hidden, false, "the float stays shown");
      assert.deepEqual([s.left, s.top], [offeredLeft, offeredTop], "...where the drag's offer put it: the paint's own event moved nothing");
      await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
      await page.keyboard.down("Shift"); await page.keyboard.press("ArrowRight"); await page.keyboard.up("Shift");
      await page.waitForFunction(() => String(getSelection()) === " ipsum do", null, { timeout: 5000 });
      await page.waitForFunction(() => { const f = document.querySelector(".fc-float") as HTMLElement; const sel = getSelection()!; if (f.hidden || !sel.rangeCount) return false;
        const r = sel.getRangeAt(sel.rangeCount - 1).getBoundingClientRect(); return Math.abs(parseFloat(f.style.left) - Math.min(Math.max(8, r.right + 6), window.innerWidth - 90)) < 0.01; }, null, { timeout: 5000 });
      s = await scene(page);
      near(s.left, s.expectedLeft, "the next change moves the float to the selection's end");
      assert.deepEqual(errors, [], "no script error");
      await page.close();
    }
  });
});

test("in a browser, the real viewer and panel: a highlight that is its paragraph's whole text, a real drag inside it, and a peer's comment landing through the poll: the paint collapses the selection to the paragraph with NO selectionchange, and the float goes with the paint (before: it stood beside nothing, and a click on it opened no composer); a fresh drag offers again, and the keyboard change after it follows", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openWith(browser, [W], MARK_W);
    const only = await page.evaluate((s: string) => { const m = document.querySelector(s)!; return Array.from(m.parentNode!.childNodes).map((c) => c.nodeName).join(","); }, MARK_W);
    assert.equal(only, "MARK", "the whole paragraph's mark is the <p>'s only child");
    await dragInside(page, MARK_W, 3, 11);
    let s = await scene(page);
    assert.equal(s.selected, P2.slice(3, 11), "the drag selected eight characters inside the highlight");
    assert.equal(s.hidden, false, "the drag's mouseup offers the float");
    const changes = s.selChanges;
    await peerCommentLands(page, null, [W]);
    s = await scene(page);
    assert.equal(s.collapsed, true, "the paint's unwrap and wrap again of the lone-child mark collapsed the selection");
    assert.equal(s.anchorIsP, true, "...to the paragraph itself"); assert.equal(s.pChildren, "MARK", "whose mark is its only child again");
    // the leg's premise, asserted as the first test's leg 1 asserts its own (Chromium fired for the prefix mark's move): NO selectionchange
    // for the lone-child mark's unwrap and wrap again, so the hide below is afterPaint's and not the listener's; a browser that fires one
    // here hides the float through onSelectionChange's collapsed-selection guard, and this leg then tests the paint-time hide no longer
    // (the shim's file-comments-paint-offer.test.ts does, with a fake that fires nothing): the title and the slice's record of the count
    // would be stale, and this says so instead of passing
    assert.equal(s.selChanges - changes, 0, "Chromium fired no selectionchange for the paint's collapse of the selection (the leg's premise: the float's hide below is the paint's own, afterPaint, not the listener's; a browser that fires one here makes the paint-time hide the shim test's to pin, and the title's and the record's count stale)");
    assert.equal(s.hidden, true, "the float went with the paint that left it beside no selection (before: shown, a Comment button that opened nothing)");
    // the paint left a caret, which Chromium's Shift+Arrow does not widen without an existing selection or caret browsing (the
    // keyboard-offer browser test's header), so the person's next gesture is a drag: the seam's mouseup offers again, and the keyboard
    // change after it offers beside the widened selection
    await dragInside(page, MARK_W, 3, 11);
    s = await scene(page);
    assert.deepEqual([s.selected, s.hidden], [P2.slice(3, 11), false], "a fresh drag inside the highlight offers the float again");
    await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
    await page.keyboard.down("Shift"); await page.keyboard.press("ArrowRight"); await page.keyboard.up("Shift");
    await page.waitForFunction((t: string) => String(getSelection()) === t, P2.slice(3, 12), { timeout: 5000 });
    await page.waitForFunction(() => { const f = document.querySelector(".fc-float") as HTMLElement; const sel = getSelection()!; if (f.hidden || !sel.rangeCount) return false;
      const r = sel.getRangeAt(sel.rangeCount - 1).getBoundingClientRect(); return Math.abs(parseFloat(f.style.left) - Math.min(Math.max(8, r.right + 6), window.innerWidth - 90)) < 0.01; }, null, { timeout: 5000 });
    s = await scene(page);
    assert.equal(s.selected, P2.slice(3, 12), "the keyboard widened the selection by one character");
    assert.equal(s.hidden, false, "the keyboard's change offers the float"); near(s.left, s.expectedLeft, "beside the selection's end");
    assert.equal(s.composer, false, "no composer opened on its own");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});
