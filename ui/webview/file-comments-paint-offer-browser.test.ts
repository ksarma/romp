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
// hidden and a shown one stays where it was, and the person's next keyboard change offers as before. Legs await the DOM's own
// states (the peer's mark appearing, the selectionchange count moving) and frames, never a timer; the poll's own interval is the
// panel's. Skips LOUDLY without a playwright browser (CI installs none). Synthetic values only: an invented report, /repo/notes-api
// paths, the placeholder sid, invented comment ids.
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
const MARK_A = '.fileview-body mark.fc-hl[data-id="aaaa-1"]', MARK_C = '.fileview-body mark.fc-hl[data-id="cccc-3"]';
const STORE_MT_1 = "1757145600000000002", STORE_MT_2 = "1757145600000000777";
const withComments = (comments: unknown[], storeMtimeNs: string) => ({ ...STATUS, storeMtimeNs, store: { ...STATUS.store, comments }, unsent: { ...STATUS.unsent, comments: comments.map((c: any) => c.id) } });

type Scene = { hidden: boolean; left: number; top: number; selected: string; expectedLeft: number; expectedTop: number; selChanges: number; anchorIsP: boolean };
/** The float's state and inline place, the selection's text, where showFloat would put the button for the selection's last range
 *  now, and the count of selectionchange events the page has seen since the counter was armed. */
const scene = (page: any): Promise<Scene> => page.evaluate(() => {
  const w = window as any; const f = document.querySelector(".fc-float") as HTMLElement; const sel = getSelection()!;
  const r = sel.rangeCount ? sel.getRangeAt(sel.rangeCount - 1).getBoundingClientRect() : null;
  return { hidden: f.hidden, left: parseFloat(f.style.left), top: parseFloat(f.style.top), selected: String(sel),
    expectedLeft: r ? Math.min(Math.max(8, r.right + 6), window.innerWidth - 90) : NaN, expectedTop: r ? Math.min(Math.max(8, r.top - 30), window.innerHeight - 34) : NaN,
    selChanges: w.__selChanges as number, anchorIsP: !!sel.anchorNode && sel.anchorNode.nodeName === "P" };
});
const near = (a: number, b: number, what: string) => assert.ok(Math.abs(a - b) < 0.01, what + ": " + a + " against " + b);

/** The page with comment A on the second paragraph and the panel open: the store's and the config's HEADs answered from a mutable
 *  mtime (equal to the status's the poll is quiet; moved, the next tick refreshes and applyStatus paints), a selectionchange counter. */
async function openWithA(browser: any): Promise<{ page: any; errors: string[] }> {
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
  }, [withComments([A], STORE_MT_1), STATUS.configMtimeNs]);
  await openPanel(page);
  await page.waitForFunction((s: string) => !!document.querySelector(s), MARK_A, { timeout: 10000 });
  await frames(page, 3);
  return { page, errors };
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
/** The peer's comment C lands through the poll: the status gains it under a moved store mtime, the HEAD reports the move, the tick
 *  refreshes and paints; awaited on C's mark and then on the selectionchange the paint's move of the selection fires. */
async function peerCommentLands(page: any, selChangesBefore: number): Promise<void> {
  await page.evaluate(([st]: [unknown]) => { const w = window as any; w.__status = st; w.__storeMtime = (st as any).storeMtimeNs; }, [withComments([A, C], STORE_MT_2)]);
  await page.waitForFunction((s: string) => !!document.querySelector(s), MARK_C, { timeout: 15000 });
  await page.waitForFunction((n: number) => (window as any).__selChanges > n, selChangesBefore, { timeout: 5000 });
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
