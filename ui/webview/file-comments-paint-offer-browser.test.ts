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
// and opened no composer. Now paintAll ends by hiding a passage's float it left beside no selection (afterPaint, passageGone). The
// review's round 5 added the remnant with NO box: a real drag from inside the lone-child mark into the next paragraph's start, and the
// poll's paint moves the anchor to the paragraph's end (a removed node's descendant boundary points move to its parent: the mark's
// text out of the mark, the mark out of the paragraph, the text into the new mark) while the focus at the next paragraph's start
// stays, a selection of a bare line break between the two blocks, in the body and not collapsed but with no client rect, which
// passageGone read as a standing passage, so the float stood beside text nobody can see and a click on it opened a composer the
// whitespace refusal closed at once; now afterPaint hides it by the offer's own test (a range with no width and no height is no
// subject, floatSubjectRect). The review's round 6 added the remnant WITH a box that the paint MOVED from under the button: the same
// drag carried into the next paragraph's middle leaves the line break and that paragraph's first half, a line or more below the
// offer's box, and the float stayed where the drag offered it, 52 px above where the remnant would seat it in leg 4's 900 by 700 px
// pane (the review's 74 px is its own narrower scene's, the node test's RECT_BELOW; the leg's diagnostic reports each run's own
// measure), while a scroll that moves the passage a pixel hides it (hideFloatOnScroll); now afterPaint reads the scroll's whole test
// (subjectHeld: the remnant's top and right edges within a pixel of the offer's), and the float goes with the paint. The review's round 7
// added the selection the paint moved WHOLE: a peer's comment landing through the poll on the selection's own line, before it, on it or
// inside it, wraps a mark whose 2 px side padding (.fc-hl) puts the still-selected text 4 px further right with no character cut, and
// round 6's test hid the offer while the passage stood selected and visible (8924fa17e and main kept it, 4 px off); now afterPaint tells
// a selection moved whole from a remnant by its text between two ends in the body (the seam's own test of a selection its paint left
// standing; not the ends by node identity, which the wrap's split of the text node renames) and offers the float again beside the
// selection's box now, so leg 5's float follows the passage at showFloat's arithmetic for the live range, and a mark landing AFTER the
// selection on its line moves nothing. The review's round 8 added two limits on that re-seat. A float the picture overlay's PRESS hid
// (RegionLayer's pointerdown, whose preventDefault cancels the mousedown the document's hideFloatOnDown hears, so the text selection
// stands through the press): the press set the float's hidden bit alone and left floatAt, the record round 7's re-seat read as a showing
// float, so a peer's mark landing on the still-selected line while the person pressed on the picture, or after a click on a standing
// region's rectangle had opened its card, showed the passage's Comment button again beside a selection the press had dismissed, and a
// click on it opened a text composer beside the open card; now the press goes through hideFloat and afterPaint guards on the hidden bit
// (leg 6). And a passage the paint moved whole PAST THE BODY'S BOX: the body clips what it scrolls and showFloat clamps to the window
// alone, so the Show changes inline toggle pressed from the keyboard, with a last-visible-line selection under a deletion's struck label,
// pushed the passage below the body's bottom edge and seated the button 30 px above it, inside the body's band, beside other text (78c0806ce
// hid it, as for any move); now the re-seat takes a box at least partly inside the body's (inBodyBox) and hides otherwise (leg 7). Legs
// await the DOM's own states (the peer's mark appearing, the selectionchange count moving) and frames, never a timer; the poll's own
// interval is the panel's. Each leg asserts what the browser fired for the paint's move of the selection, its premise: one or more
// events for the prefix highlight, none for the lone-child mark (the Slice 5 review, round 3: a browser firing one there would hide
// the float through the listener's own collapsed-selection guard, and the leg would pass without reaching afterPaint's hide; the
// count read into an assertion message pinned nothing). Skips LOUDLY without a playwright browser (CI installs none). Synthetic
// values only: an invented report, /repo/notes-api paths, the placeholder sid, invented comment ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, openPanel, frames, pageHtml, PARA, REPORT, ROOT, SID, MT, ORIGIN, STATUS } from "./real-viewer-leg";

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
const P3 = "Paragraph 3: after words closing the report with a few more words so the line wraps somewhere.";
const W = commentOn("wwww-2", T0 + 2, P2, "sigma tau.\n\n", "\n\nParagraph 3");   // the whole of paragraph 2: its mark is the <p>'s only child
const MARK_A = '.fileview-body mark.fc-hl[data-id="aaaa-1"]', MARK_C = '.fileview-body mark.fc-hl[data-id="cccc-3"]', MARK_W = '.fileview-body mark.fc-hl[data-id="wwww-2"]';
const STORE_MT_1 = "1757145600000000002", STORE_MT_2 = "1757145600000000777";
const withComments = (comments: unknown[], storeMtimeNs: string) => ({ ...STATUS, storeMtimeNs, store: { ...STATUS.store, comments }, unsent: { ...STATUS.unsent, comments: comments.map((c: any) => c.id) } });

type Scene = { hidden: boolean; left: number; top: number; selected: string; collapsed: boolean; expectedLeft: number; expectedTop: number; rectTop: number; rectRight: number; selChanges: number; anchorIsP: boolean; pChildren: string; composer: boolean; boxless: boolean; inBody: boolean; marks: number };
/** The float's state and inline place, the selection's text and whether it is collapsed, where showFloat would put the button for the
 *  selection's last range now and that range's top and right edges (what the subject test compares with the offer's), the count of
 *  selectionchange events the page has seen since the counter was armed, the anchor's paragraph's child nodes when the anchor is
 *  one, whether a composer stands, whether the selection's last range has no box (no width and no height: the offer's own refusal),
 *  whether both its ends lie in the body, and the count of highlight marks on the body. */
const scene = (page: any): Promise<Scene> => page.evaluate(() => {
  const w = window as any; const f = document.querySelector(".fc-float") as HTMLElement; const sel = getSelection()!; const body = document.querySelector(".fileview-body");
  const r = sel.rangeCount ? sel.getRangeAt(sel.rangeCount - 1).getBoundingClientRect() : null;
  const anchorIsP = !!sel.anchorNode && sel.anchorNode.nodeName === "P";
  return { hidden: f.hidden, left: parseFloat(f.style.left), top: parseFloat(f.style.top), selected: String(sel), collapsed: sel.isCollapsed,
    expectedLeft: r ? Math.min(Math.max(8, r.right + 6), window.innerWidth - 90) : NaN, expectedTop: r ? Math.min(Math.max(8, r.top - 30), window.innerHeight - 34) : NaN,
    rectTop: r ? r.top : NaN, rectRight: r ? r.right : NaN,
    selChanges: w.__selChanges as number, anchorIsP, pChildren: anchorIsP ? Array.from(sel.anchorNode!.childNodes).map((c) => c.nodeName).join(",") : "",
    composer: !!document.querySelector(".fileview-aside .fc-composer .fc-input"),
    boxless: !r || (!r.width && !r.height), inBody: !!body && !!sel.anchorNode && !!sel.focusNode && body.contains(sel.anchorNode) && body.contains(sel.focusNode),
    marks: document.querySelectorAll(".fileview-body mark.fc-hl").length };
});
const near = (a: number, b: number, what: string) => assert.ok(Math.abs(a - b) < 0.01, what + ": " + a + " against " + b);

/** The page with `comments` on the note and the panel open: the store's and the config's HEADs answered from a mutable mtime (equal
 *  to the status's the poll is quiet; moved, the next tick refreshes and applyStatus paints), a selectionchange counter; awaited on
 *  the mark `markSel`, when one is given (null for a note with no comment yet: leg 5's peer's comment is the first to land). */
async function openWith(browser: any, comments: unknown[], markSel: string | null): Promise<{ page: any; errors: string[] }> {
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
  if (markSel) await page.waitForFunction((s: string) => !!document.querySelector(s), markSel, { timeout: 10000 });
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
/** A real mouse drag from character `from` inside a highlight's text to the START of the next paragraph's text (its first character's
 *  left edge), so the selection's anchor lies in the mark's text node and its focus at the next block's start, the paragraph's end and
 *  the block boundary selected with the text; the seam's mouseup offers the float. */
async function dragIntoNext(page: any, markSel: string, from: number): Promise<void> {
  await page.evaluate(() => getSelection()!.removeAllRanges());
  const r = await page.evaluate(([s, a]: [string, number]) => {
    const m = document.querySelector(s) as HTMLElement; const t = m.firstChild as Text; const next = (m.parentElement as HTMLElement).nextElementSibling!.firstChild as Text;
    const ra = document.createRange(); ra.setStart(t, a); ra.setEnd(t, a + 1); const x = ra.getBoundingClientRect();
    const rb = document.createRange(); rb.setStart(next, 0); rb.setEnd(next, 1); const y = rb.getBoundingClientRect();
    return { x1: x.left + 1, y1: x.top + x.height / 2, x2: y.left + 1, y2: y.top + y.height / 2 };
  }, [markSel, from]);
  await page.mouse.move(r.x1, r.y1); await page.mouse.down(); await page.mouse.move(r.x2, r.y2, { steps: 6 }); await page.mouse.up();
  await page.waitForFunction(() => { const f = document.querySelector(".fc-float") as HTMLElement | null; return !!f && !f.hidden; }, null, { timeout: 5000 });
  await frames(page, 2);
}
/** A real mouse drag from character `from` inside a highlight's text to character `n` of the NEXT paragraph's text, so the selection's
 *  anchor lies in the mark's text node and its focus in the middle of the next block; the seam's mouseup offers the float. */
async function dragIntoMiddle(page: any, markSel: string, from: number, n: number): Promise<void> {
  await page.evaluate(() => getSelection()!.removeAllRanges());
  const r = await page.evaluate(([s, a, k]: [string, number, number]) => {
    const m = document.querySelector(s) as HTMLElement; const t = m.firstChild as Text; const next = (m.parentElement as HTMLElement).nextElementSibling!.firstChild as Text;
    const ra = document.createRange(); ra.setStart(t, a); ra.setEnd(t, a + 1); const x = ra.getBoundingClientRect();
    const rb = document.createRange(); rb.setStart(next, k - 1); rb.setEnd(next, k); const y = rb.getBoundingClientRect();
    return { x1: x.left + 1, y1: x.top + x.height / 2, x2: y.right - 1, y2: y.top + y.height / 2 };
  }, [markSel, from, n]);
  await page.mouse.move(r.x1, r.y1); await page.mouse.down(); await page.mouse.move(r.x2, r.y2, { steps: 6 }); await page.mouse.up();
  await page.waitForFunction(() => { const f = document.querySelector(".fc-float") as HTMLElement | null; return !!f && !f.hidden; }, null, { timeout: 5000 });
  await frames(page, 2);
}
/** A real mouse drag over the text of the note's paragraph `p` (the p-th `<p>` of the rendered note, counted from 0; its first text
 *  node, no mark in it yet), from its character `from` to its character `to`; the seam's mouseup offers the float. */
async function dragOver(page: any, p: number, from: number, to: number): Promise<void> {
  await page.evaluate(() => getSelection()!.removeAllRanges());
  const r = await page.evaluate(([n, a, b]: [number, number, number]) => {
    const t = document.querySelectorAll(".fileview-md > p")[n].firstChild as Text;
    const ra = document.createRange(); ra.setStart(t, a); ra.setEnd(t, a + 1); const x = ra.getBoundingClientRect();
    const rb = document.createRange(); rb.setStart(t, b - 1); rb.setEnd(t, b); const y = rb.getBoundingClientRect();
    return { x1: x.left + 1, y1: x.top + x.height / 2, x2: y.right - 1, y2: y.top + y.height / 2 };
  }, [p, from, to]);
  await page.mouse.move(r.x1, r.y1); await page.mouse.down(); await page.mouse.move(r.x2, r.y2, { steps: 6 }); await page.mouse.up();
  await page.waitForFunction(() => { const f = document.querySelector(".fc-float") as HTMLElement | null; return !!f && !f.hidden; }, null, { timeout: 5000 });
  await frames(page, 2);
}
/** The peer's comment `c`, the note's first, lands through the poll: the status gains it under a moved store mtime, the HEAD reports the
 *  move, the tick refreshes and paints; awaited on its mark and then frames (the paint's move of the selection fires its selectionchange
 *  a task later, which the frames cover). */
async function firstCommentLands(page: any, c: { id: string }): Promise<void> {
  await page.evaluate(([st]: [unknown]) => { const w = window as any; w.__status = st; w.__storeMtime = (st as any).storeMtimeNs; }, [withComments([c], STORE_MT_2)]);
  await page.waitForFunction((s: string) => !!document.querySelector(s), `.fileview-body mark.fc-hl[data-id="${c.id}"]`, { timeout: 15000 });
  await frames(page, 6);
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

test("in a browser, the real viewer and panel: a real drag from inside a whole-paragraph highlight into the next paragraph's start, and a peer's comment landing through the poll: the paint moves the anchor to the paragraph's end and leaves a bare line break selected, in the body, not collapsed, with NO box, and the float goes with the paint (before: it stood beside text nobody can see, and a click on it opened a composer the whitespace refusal closed at once); a fresh drag offers again", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openWith(browser, [W], MARK_W);
    const only = await page.evaluate((s: string) => { const m = document.querySelector(s)!; return Array.from(m.parentNode!.childNodes).map((c) => c.nodeName).join(","); }, MARK_W);
    assert.equal(only, "MARK", "the whole paragraph's mark is the <p>'s only child");
    const from = P2.length - 8;
    await dragIntoNext(page, MARK_W, from);
    let s = await scene(page);
    assert.equal(s.selected.replace(/\n+$/, ""), P2.slice(from), "the drag selected the paragraph's last eight characters and the block boundary after them");
    assert.ok(/\n$/.test(s.selected), "...the boundary read as a line break");
    assert.deepEqual([s.hidden, s.collapsed, s.boxless], [false, false, false], "the drag's mouseup offers the float beside a selection with a box");
    await peerCommentLands(page, null, [W]);
    s = await scene(page);
    // the leg's premise: the paint's unwrap and wrap again of the lone-child mark moved the anchor to the paragraph's end (after the
    // mark) while the focus stayed at the next paragraph's start, so what stands selected is the line break between the blocks: in the
    // body, not collapsed (passageGone's rule reads it as a passage), and with no client rect (the offer's own guard refuses it)
    assert.equal(s.selected.trim(), "", "the paint left only the block boundary selected, a bare line break");
    assert.ok(/^\n+$/.test(s.selected), "...read as one or more line breaks");
    assert.equal(s.anchorIsP, true, "its anchor the paragraph itself (the mark's text out and in again moved the end to the paragraph)");
    assert.deepEqual([s.collapsed, s.inBody, s.boxless], [false, true, true], "not collapsed, both ends in the body, and no box: the remnant passageGone reads as a standing passage and the offer refuses");
    assert.equal(s.hidden, true, "the float went with the paint that left it beside a selection with no box (before: shown at the drag's place, a Comment button whose composer the whitespace refusal closed at once)");
    assert.equal(s.composer, false, "no composer opened on its own");
    // the person's next gesture, a drag inside the highlight: the seam's mouseup offers again, beside a selection with a box
    await dragInside(page, MARK_W, 3, 11);
    s = await scene(page);
    assert.deepEqual([s.selected, s.hidden, s.boxless], [P2.slice(3, 11), false, false], "a fresh drag inside the highlight offers the float again");
    near(s.left, s.expectedLeft, "beside the selection's end");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

test("in a browser, the real viewer and panel: a real drag from inside a whole-paragraph highlight into the next paragraph's middle, and a peer's comment landing through the poll: the paint moves the anchor to the paragraph's end and leaves the line break and the next paragraph's first half selected, a remnant WITH a box a line or more below the offer's, and the float goes with the paint, by the test the scroll reads (before: it stood where the drag offered it, 52 px above where the remnant would seat it in this leg's 900 by 700 px pane, the review's 74 px being its own narrower scene's, and a click on it opened the composer on that remnant); a fresh drag offers again", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openWith(browser, [W], MARK_W);
    const only = await page.evaluate((s: string) => { const m = document.querySelector(s)!; return Array.from(m.parentNode!.childNodes).map((c) => c.nodeName).join(","); }, MARK_W);
    assert.equal(only, "MARK", "the whole paragraph's mark is the <p>'s only child");
    await dragIntoMiddle(page, MARK_W, 20, 60);
    let s = await scene(page);
    assert.equal(s.selected.replace(/\n+/g, "\n"), P2.slice(20) + "\n" + P3.slice(0, 60), "the drag selected the rest of paragraph 2, the block boundary and the first sixty characters of paragraph 3");
    assert.deepEqual([s.hidden, s.collapsed, s.boxless], [false, false, false], "the drag's mouseup offers the float beside a selection with a box");
    const offered = { left: s.left, top: s.top, rectTop: s.rectTop, rectRight: s.rectRight };
    await peerCommentLands(page, null, [W]);
    s = await scene(page);
    // the leg's premise: the paint's unwrap and wrap again of the lone-child mark moved the anchor to the paragraph's end while the
    // focus in the next paragraph stayed, so what stands selected is the line break and that paragraph's first half: in the body,
    // not collapsed, WITH a box, and that box a line or more below where the button was offered (the subject moved from under it)
    assert.equal(s.selected.replace(/^\n+/, ""), P3.slice(0, 60), "the paint left the next paragraph's first sixty characters selected, after the block boundary");
    assert.ok(/^\n/.test(s.selected), "...the boundary read as a line break at the start");
    assert.equal(s.anchorIsP, true, "its anchor the paragraph itself (the mark's text out and in again moved the end to the paragraph)");
    assert.deepEqual([s.collapsed, s.inBody, s.boxless], [false, true, false], "not collapsed, both ends in the body, and a box: a remnant the offer would accept");
    assert.ok(s.rectTop - offered.rectTop >= 1, "the remnant's box sits a pixel or more below the offer's (here " + (s.rectTop - offered.rectTop).toFixed(1) + " px): the subject moved from under the button");
    t.diagnostic("leg 4: the paint moved the offer's subject " + (s.rectTop - offered.rectTop).toFixed(1) + " px down in this 900 by 700 px pane (the title's before-record, 52 px, is this measure on the pre-fix tree)");
    assert.equal(s.hidden, true, "the float went with the paint that moved its subject from under it, as it goes on a scroll that moves the passage a pixel (before: shown at the drag's place, " + (s.rectTop - offered.rectTop).toFixed(0) + " px above where the remnant would seat it, a Comment button for text the person had not chosen)");
    assert.deepEqual([s.left, s.top], [offered.left, offered.top], "...hidden where it stood: no re-offer beside the remnant");
    assert.equal(s.composer, false, "no composer opened on its own");
    // the person's next gesture, a drag inside the highlight: the seam's mouseup offers again, beside the selection's own box
    await dragInside(page, MARK_W, 3, 11);
    s = await scene(page);
    assert.deepEqual([s.selected, s.hidden, s.boxless], [P2.slice(3, 11), false, false], "a fresh drag inside the highlight offers the float again");
    near(s.left, s.expectedLeft, "beside the selection's end");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

type Reseat = { name: string; drag: [number, number]; peer: { id: string }; moves: boolean };
/** Leg 5's scenes: a real drag over paragraph 2's plain text, then a peer's comment on the same paragraph landing through the poll, its
 *  mark BEFORE the selection on its line (the review's own scene: comment A on the paragraph's first words), ON the selected words,
 *  INSIDE them, and, the control, AFTER the selection on its line. The mark's 2 px side padding moves the selection's right edge 4 px in
 *  the first three (both edges in the first) and nothing in the control. */
const RESEATS: Reseat[] = [
  { name: "the peer's mark BEFORE the selection on its line", drag: [40, 70], peer: A, moves: true },
  { name: "the peer's mark ON the selected words", drag: [13, 40], peer: commentOn("bbbb-2", T0 + 2, "lorem ipsum dolor sit amet", "Paragraph 2: ", " consectetur adipiscing"), moves: true },
  { name: "the peer's mark INSIDE the selection", drag: [13, 40], peer: commentOn("dddd-4", T0 + 4, "psum dolor", "Paragraph 2: lorem i", " sit amet consectetur"), moves: true },
  { name: "the control, the peer's mark AFTER the selection on its line", drag: [13, 30], peer: commentOn("eeee-5", T0 + 5, P2.slice(40, 57), P2.slice(20, 40), P2.slice(57, 77)), moves: false },
];

test("in a browser, the real viewer and panel: a real drag over a plain paragraph's words, and a peer's comment landing through the poll on the same line, before the selection, on it or inside it: the mark's 2 px side padding moves the still-selected text 4 px right with no character cut, and the float follows the passage to its box now (before: hidden by the remnant's test while the passage stood selected and visible, no Comment offer); a mark landing after the selection on its line moves nothing and the float stands; a scroll event that moved nothing keeps the re-seated float, Shift+ArrowRight offers at the grown selection, and a scroll that moves the passage hides as ever", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const c of RESEATS) {
      const { page, errors } = await openWith(browser, [], null);
      await dragOver(page, 1, c.drag[0], c.drag[1]);
      let s = await scene(page);
      assert.equal(s.selected, P2.slice(c.drag[0], c.drag[1]), c.name + ": the drag selected the passage");
      assert.deepEqual([s.hidden, s.marks], [false, 0], c.name + ": the drag's mouseup offers the float, no mark on the body yet");
      const offered = { left: s.left, top: s.top, rectTop: s.rectTop, rectRight: s.rectRight, selected: s.selected };
      await firstCommentLands(page, c.peer);
      s = await scene(page);
      assert.equal(s.marks, 1, c.name + ": the peer's mark landed through the poll");
      assert.equal(s.selected, offered.selected, c.name + ": the paint left every selected character selected: no remnant, the passage whole");
      assert.deepEqual([s.collapsed, s.inBody], [false, true], c.name + ": ...not collapsed, both ends in the body");
      const d = { right: s.rectRight - offered.rectRight, top: s.rectTop - offered.rectTop };
      t.diagnostic("leg 5, " + c.name + ": the paint moved the selection's right edge " + d.right.toFixed(2) + " px and its top " + d.top.toFixed(2) + " px");
      if (c.moves) {
        // the leg's premise: the mark's padding moved the selection's box a pixel or more (4 px, the sheet's 2 px a side), the move
        // round 6's test reads as the subject gone from under the button
        assert.ok(Math.abs(d.right) >= 1, c.name + ": the premise: the mark's padding moved the selection's right edge (" + d.right.toFixed(2) + " px)");
        assert.equal(s.hidden, false, c.name + ": the float follows the passage the paint moved whole (before: hidden by the remnant's test, the passage still selected and visible with no Comment offer)");
        near(s.left, s.expectedLeft, c.name + ": ...re-seated beside the selection's new right edge, showFloat's arithmetic for the live range");
        near(s.top, s.expectedTop, c.name + ": ...on its line");
        // the re-seat re-recorded the offer's place: a scroll event that moved nothing keeps the float (measured from the old place, the
        // 4 px would hide it)
        await page.evaluate(() => { document.querySelector(".fileview-body")!.dispatchEvent(new Event("scroll")); });
        await frames(page, 1);
        s = await scene(page);
        assert.equal(s.hidden, false, c.name + ": a scroll event that moved nothing keeps the float: the scroll's test measures from the re-seated place");
      } else {
        assert.ok(Math.abs(d.right) < 0.01 && Math.abs(d.top) < 0.01, c.name + ": the control's premise: a mark after the selection moved nothing");
        assert.equal(s.hidden, false, c.name + ": the float stays shown");
        assert.deepEqual([s.left, s.top], [offered.left, offered.top], c.name + ": ...where the drag's offer put it: the paint's own event moved nothing");
      }
      assert.equal(s.composer, false, c.name + ": no composer opened on its own");
      // the person's next keyboard change offers, beside the grown selection
      await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
      await page.keyboard.down("Shift"); await page.keyboard.press("ArrowRight"); await page.keyboard.up("Shift");
      await page.waitForFunction((tx: string) => String(getSelection()) === tx, P2.slice(c.drag[0], c.drag[1] + 1), { timeout: 5000 });
      await page.waitForFunction(() => { const f = document.querySelector(".fc-float") as HTMLElement; const sel = getSelection()!; if (f.hidden || !sel.rangeCount) return false;
        const r = sel.getRangeAt(sel.rangeCount - 1).getBoundingClientRect(); return Math.abs(parseFloat(f.style.left) - Math.min(Math.max(8, r.right + 6), window.innerWidth - 90)) < 0.01; }, null, { timeout: 5000 });
      s = await scene(page);
      assert.equal(s.hidden, false, c.name + ": the keyboard's change offers the float"); near(s.left, s.expectedLeft, c.name + ": beside the grown selection's end");
      // a scroll that moves the passage hides the float, as ever
      await page.evaluate(() => { (document.querySelector(".fileview-body") as HTMLElement).scrollTop += 40; });
      await page.waitForFunction(() => (document.querySelector(".fc-float") as HTMLElement).hidden, null, { timeout: 5000 });
      assert.deepEqual(errors, [], c.name + ": no script error");
      await page.close();
    }
  });
});


// ── the review's round 8: a float the picture overlay's press hid, and a passage the paint moved past the body's box ──────────────
const LOGO = ROOT + "/docs/logo.svg";
const SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="120"><rect width="300" height="120" fill="#336699"/><rect width="150" height="60" fill="#ffcc00"/></svg>';
const NOTE_LOGO = "# Report\n\n![logo](logo.svg)\n\n" + NOTE.slice("# Report\n\n".length);   // the note with a figure above its paragraphs
const ON = commentOn("bbbb-2", T0 + 2, "lorem ipsum dolor sit amet", "Paragraph 2: ", " consectetur adipiscing");   // the peer's mark ON the words leg 6 selects
const RR = { ...commentOn("rrrr-7", T0 + 7, "![logo](logo.svg)", "# Report\n\n", "\n\nParagraph 1: alpha"), target: { kind: "image", region: { x: 0.1, y: 0.1, w: 0.3, h: 0.3 }, src: "logo.svg" } };   // a standing region comment on the figure: its rectangle is a control on the overlay
const RECT_RR = '.fileview-body .fc-overlay .fc-region[data-id="rrrr-7"]';

type PressScene = Scene & { active: string; rects: number; cardOpen: boolean; band: boolean };
/** The paint-offer scene, plus the focused element, the count of region rectangles on the figure's overlay, whether RR's card stands open
 *  in the aside, and whether the overlay's rubber band is drawn. */
const pressScene = (page: any): Promise<PressScene> => page.evaluate(() => {
  const w = window as any; const f = document.querySelector(".fc-float") as HTMLElement; const sel = getSelection()!; const body = document.querySelector(".fileview-body");
  const r = sel.rangeCount ? sel.getRangeAt(sel.rangeCount - 1).getBoundingClientRect() : null;
  const anchorIsP = !!sel.anchorNode && sel.anchorNode.nodeName === "P";
  return { hidden: f.hidden, left: parseFloat(f.style.left), top: parseFloat(f.style.top), selected: String(sel), collapsed: sel.isCollapsed,
    expectedLeft: r ? Math.min(Math.max(8, r.right + 6), window.innerWidth - 90) : NaN, expectedTop: r ? Math.min(Math.max(8, r.top - 30), window.innerHeight - 34) : NaN,
    rectTop: r ? r.top : NaN, rectRight: r ? r.right : NaN,
    selChanges: w.__selChanges as number, anchorIsP, pChildren: anchorIsP ? Array.from(sel.anchorNode!.childNodes).map((c) => c.nodeName).join(",") : "",
    composer: !!document.querySelector(".fileview-aside .fc-composer .fc-input"),
    boxless: !r || (!r.width && !r.height), inBody: !!body && !!sel.anchorNode && !!sel.focusNode && body.contains(sel.anchorNode) && body.contains(sel.focusNode),
    marks: document.querySelectorAll(".fileview-body mark.fc-hl").length,
    active: document.activeElement ? document.activeElement.tagName + "." + (document.activeElement as HTMLElement).className : "null",
    rects: document.querySelectorAll(".fileview-body .fc-overlay .fc-region").length,
    cardOpen: !!document.querySelector('.fileview-aside .fc-card.open[data-id="rrrr-7"]'),
    band: !!document.querySelector(".fileview-body .fc-region.fc-draw") };
});
/** The page with the figure's note and `comments` standing, the panel open and the figure's overlay armed (and RR's rectangle painted when
 *  RR stands). The figure's own request is a resource load, not the page's fetch, so a route for it is registered AFTER the page's
 *  catch-all (Playwright matches the last route first); the poll's HEAD stub and the selectionchange counter as openWith has them. */
async function openWithLogo(browser: any, comments: unknown[]): Promise<{ page: any; errors: string[] }> {
  const page = await browser.newPage({ viewport: { width: 900, height: 700 } });
  const errors: string[] = [];
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  const html = pageHtml("pane", { [REPORT]: NOTE_LOGO, [LOGO]: SVG }, MT, "");
  await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
  await page.route((u: URL) => u.href.startsWith(ORIGIN) && u.pathname === "/file" && /\.svg$/.test(u.searchParams.get("path") || ""), (route: any) => route.fulfill({ status: 200, contentType: "image/svg+xml", body: SVG }));
  await page.goto(ORIGIN + "/");
  await page.evaluate(([p, sid]: [string, string]) => { (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID]);
  await page.waitForFunction(() => !!document.querySelector(".fileview-md > p"), null, { timeout: 10000 });
  await frames(page, 2);
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
  await page.waitForFunction((withRect: boolean) => {
    const i = document.querySelector(".fileview-md img") as HTMLImageElement | null; const ov = document.querySelector(".fileview-body .fc-overlay");
    return !!i && i.complete && i.naturalWidth > 0 && i.getBoundingClientRect().width > 50 && !!ov && !ov.classList.contains("fc-overlay-off") && (!withRect || !!ov.querySelector(".fc-region"));
  }, comments.length > 0, { timeout: 10000 });
  await frames(page, 3);
  return { page, errors };
}
/** A real mouse drag over the paragraph whose text starts with `head`, from its character `from` to `to`; the seam's mouseup offers the float. */
async function dragOverHead(page: any, head: string, from: number, to: number): Promise<void> {
  await page.evaluate(() => getSelection()!.removeAllRanges());
  const r = await page.evaluate(([h, a, b]: [string, number, number]) => {
    const p = Array.from(document.querySelectorAll(".fileview-md > p")).find((e) => (e.textContent || "").startsWith(h))!;
    const t = p.firstChild as Text;
    const ra = document.createRange(); ra.setStart(t, a); ra.setEnd(t, a + 1); const x = ra.getBoundingClientRect();
    const rb = document.createRange(); rb.setStart(t, b - 1); rb.setEnd(t, b); const y = rb.getBoundingClientRect();
    return { x1: x.left + 1, y1: x.top + x.height / 2, x2: y.right - 1, y2: y.top + y.height / 2 };
  }, [head, from, to]);
  await page.mouse.move(r.x1, r.y1); await page.mouse.down(); await page.mouse.move(r.x2, r.y2, { steps: 6 }); await page.mouse.up();
  await page.waitForFunction(() => { const f = document.querySelector(".fc-float") as HTMLElement | null; return !!f && !f.hidden; }, null, { timeout: 5000 });
  await frames(page, 2);
}
/** The peer's comments `comments` (the set now standing) land through the poll: the status gains them under a moved store mtime, the HEAD
 *  reports the move, the tick refreshes and paints; awaited on the mark of `id` and then frames. */
async function landsWith(page: any, comments: unknown[], id: string): Promise<void> {
  await page.evaluate(([st]: [unknown]) => { const w = window as any; w.__status = st; w.__storeMtime = (st as any).storeMtimeNs; }, [withComments(comments, STORE_MT_2)]);
  await page.waitForFunction((s: string) => !!document.querySelector(s), `.fileview-body mark.fc-hl[data-id="${id}"]`, { timeout: 15000 });
  await frames(page, 6);
}
const imgBox = (page: any): Promise<{ left: number; top: number; width: number; height: number }> => page.evaluate(() => { const b = (document.querySelector(".fileview-md img") as HTMLElement).getBoundingClientRect(); return { left: b.left, top: b.top, width: b.width, height: b.height }; });
/** Shift+ArrowRight with nothing else focused: the person's keyboard change, awaited on the selection's text and the float beside it. */
async function growByKeyboard(page: any, text: string): Promise<void> {
  await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
  await page.keyboard.down("Shift"); await page.keyboard.press("ArrowRight"); await page.keyboard.up("Shift");
  await page.waitForFunction((tx: string) => String(getSelection()) === tx, text, { timeout: 5000 });
  await page.waitForFunction(() => { const f = document.querySelector(".fc-float") as HTMLElement; const sel = getSelection()!; if (f.hidden || !sel.rangeCount) return false;
    const r = sel.getRangeAt(sel.rangeCount - 1).getBoundingClientRect(); return Math.abs(parseFloat(f.style.left) - Math.min(Math.max(8, r.right + 6), window.innerWidth - 90)) < 0.01; }, null, { timeout: 5000 });
}

test("in a browser, the real viewer and panel: a passage's float hidden by a real press on a picture's overlay (a click on a standing region's rectangle, which opens its card and leaves the pointer free; a press that begins a region drag, held while the person draws), and a peer's comment landing through the poll on the selected line, its mark's padding moving the still-selected passage whole: the float stays hidden (before: shown again beside a selection the press had dismissed, at showFloat's arithmetic for the moved passage, and a click on it opened a text composer beside the open card); the next keyboard change offers; the drag's release opens the region composer with the float hidden", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    // scene 1: a click on a standing region's rectangle (the durable window: the card opens, no text control takes focus, the pointer is free)
    {
      const { page, errors } = await openWithLogo(browser, [RR]);
      await dragOverHead(page, "Paragraph 2", 13, 40);
      let s = await pressScene(page);
      assert.equal(s.selected, P2.slice(13, 40), "the drag selected the passage");
      assert.deepEqual([s.hidden, s.rects, s.marks], [false, 1, 0], "the drag's mouseup offers the float; the region's rectangle stands on the overlay; no highlight yet");
      const offered = { left: s.left, top: s.top, rectRight: s.rectRight, selected: s.selected };
      const rb = await page.evaluate((sel: string) => { const b = (document.querySelector(sel) as HTMLElement).getBoundingClientRect(); return { x: b.left + b.width / 2, y: b.top + b.height / 2 }; }, RECT_RR);
      await page.mouse.click(rb.x, rb.y);
      await page.waitForFunction(() => !!document.querySelector('.fileview-aside .fc-card.open[data-id="rrrr-7"]'), null, { timeout: 5000 });
      await frames(page, 3);
      s = await pressScene(page);
      assert.equal(s.hidden, true, "the press on the overlay hid the float (RegionLayer's onPress)");
      assert.deepEqual([s.selected, s.collapsed, s.inBody], [offered.selected, false, true], "...and the text selection stands through it: the overlay cancels the mousedown that would have collapsed it");
      assert.equal(s.cardOpen, true, "the rectangle's own click opened its card");
      assert.equal(s.composer, false, "no text control took focus");
      await landsWith(page, [RR, ON], ON.id);
      s = await pressScene(page);
      assert.equal(s.marks, 1, "the peer's mark landed through the poll on the selected words");
      assert.deepEqual([s.selected, s.collapsed, s.inBody], [offered.selected, false, true], "the paint left the passage whole, in the body");
      const d = s.rectRight - offered.rectRight;
      t.diagnostic("leg 6, scene 1: the paint moved the selection's right edge " + d.toFixed(2) + " px");
      assert.ok(Math.abs(d) >= 1, "the premise: the mark's padding moved the still-selected passage a pixel or more (" + d.toFixed(2) + " px), the whole move the re-seat follows for a SHOWING float");
      assert.equal(s.hidden, true, "the press's hide holds across the paint: a hidden float is no re-seat (before: shown again beside the moved passage, a selection the press had dismissed, while the card stood open)");
      assert.deepEqual([s.left, s.top], [offered.left, offered.top], "...and it keeps the place it was hidden at, not showFloat's for the moved box");
      assert.equal(s.composer, false, "no composer opened on its own");
      // the person's next keyboard change offers, beside the grown selection
      await growByKeyboard(page, P2.slice(13, 41));
      s = await pressScene(page);
      assert.equal(s.hidden, false, "the keyboard's change offers the float"); near(s.left, s.expectedLeft, "beside the grown selection's end");
      assert.deepEqual(errors, [], "scene 1: no script error");
      await page.close();
    }
    // scene 2: a press that begins a region drag, the button held while the peer's comment lands
    {
      const { page, errors } = await openWithLogo(browser, []);
      await dragOverHead(page, "Paragraph 2", 13, 40);
      let s = await pressScene(page);
      assert.deepEqual([s.selected, s.hidden, s.marks], [P2.slice(13, 40), false, 0], "the drag's mouseup offers the float, no highlight yet");
      const offered = { left: s.left, top: s.top, rectRight: s.rectRight, selected: s.selected };
      const b = await imgBox(page);
      await page.mouse.move(b.left + b.width * 0.3, b.top + b.height * 0.3); await page.mouse.down();
      await frames(page, 2);
      s = await pressScene(page);
      assert.equal(s.hidden, true, "the press on the overlay hid the float");
      assert.deepEqual([s.selected, s.collapsed, s.inBody], [offered.selected, false, true], "...the text selection standing through it");
      await landsWith(page, [ON], ON.id);
      s = await pressScene(page);
      assert.deepEqual([s.marks, s.selected], [1, offered.selected], "the peer's mark landed on the selected words while the button is held, the passage whole");
      const d = s.rectRight - offered.rectRight;
      t.diagnostic("leg 6, scene 2: the paint moved the selection's right edge " + d.toFixed(2) + " px with the button held");
      assert.ok(Math.abs(d) >= 1, "the premise: the mark's padding moved the passage (" + d.toFixed(2) + " px)");
      assert.equal(s.hidden, true, "hidden it stays while the person draws (before: the passage's Comment button reappeared beside the text mid-drag)");
      await page.mouse.move(b.left + b.width * 0.7, b.top + b.height * 0.7, { steps: 4 });
      await frames(page, 1);
      s = await pressScene(page);
      assert.deepEqual([s.band, s.hidden], [true, true], "the rubber band is drawn, the float hidden");
      await page.mouse.up();
      await page.waitForFunction(() => !!document.querySelector(".fileview-aside .fc-composer .fc-input"), null, { timeout: 5000 });
      await frames(page, 4);
      s = await pressScene(page);
      assert.deepEqual([s.composer, s.hidden], [true, true], "the drag's release opens the region composer, the float hidden");
      assert.deepEqual(errors, [], "scene 2: no script error");
      await page.close();
    }
  });
});

// leg 7's note: forty paragraphs, a deletion recorded at the end of the fifth (its struck label, shown inline, adds a line above the sixth)
const NOTE_TRACKED = "# Report\n\n" + Array.from({ length: 40 }, (_, i) => PARA(i + 1)).join("\n\n") + "\n";
const P5_END = NOTE_TRACKED.indexOf(PARA(5)) + PARA(5).length;
const OLD = " Removed sentence: this text was cut from the end of the fifth paragraph and is long enough to add at least one line at the pane's width.";
const DEL = { id: "d1", author: "api", ts: T0 + 1000, kind: "del", curFrom: P5_END, curTo: P5_END, baseFrom: P5_END, baseTo: P5_END + OLD.length, oldText: OLD, newText: "", anchor: null };
const TRACKED = { ...STATUS, hunks: [DEL], store: { ...STATUS.store, suggestions: [{ id: "d1", authorId: SID }] } };
type ClipScene = { hidden: boolean; left: number; top: number; expectedLeft: number; expectedTop: number; selected: string; selTop: number; selBottom: number; bodyTop: number; bodyBottom: number; selInBody: boolean; selBelowBody: boolean; floatInBodyBand: boolean | null; dels: number; composer: boolean };
/** The float's state and inline place, where showFloat would put it for the selection now, the selection's text and its box's top and
 *  bottom against the body's, whether any of the box lies inside the body's (in view) or the whole of it below the body's bottom edge,
 *  whether the shown button's own box lies inside the body's band, the count of struck deletion marks, and whether a composer stands. */
const clipScene = (page: any): Promise<ClipScene> => page.evaluate(() => {
  const f = document.querySelector(".fc-float") as HTMLElement; const sel = getSelection()!;
  const body = document.querySelector(".fileview-body") as HTMLElement; const b = body.getBoundingClientRect();
  const r = sel.rangeCount && !sel.isCollapsed ? sel.getRangeAt(sel.rangeCount - 1).getBoundingClientRect() : null;
  const fr = f.hidden ? null : f.getBoundingClientRect();
  return { hidden: f.hidden, left: parseFloat(f.style.left), top: parseFloat(f.style.top),
    expectedLeft: r ? Math.min(Math.max(8, r.right + 6), window.innerWidth - 90) : NaN, expectedTop: r ? Math.min(Math.max(8, r.top - 30), window.innerHeight - 34) : NaN,
    selected: String(sel), selTop: r ? r.top : NaN, selBottom: r ? r.bottom : NaN, bodyTop: b.top, bodyBottom: b.bottom,
    selInBody: !!r && r.bottom > b.top && r.top < b.bottom, selBelowBody: !!r && r.top >= b.bottom,
    floatInBodyBand: fr ? fr.bottom > b.top && fr.top < b.bottom : null,
    dels: document.querySelectorAll(".fileview-body .fc-del").length, composer: !!document.querySelector(".fileview-aside .fc-composer .fc-input") };
});

test("in a browser, the real Files pane at 500 by 400 px: a tracked note with a deletion above the sixth paragraph, Show changes inline off, a real drag over that paragraph's words, a scroll that makes its line the body's last visible one (the float hides), Shift+ArrowRight (offered beside the line), then the inline toggle pressed from the keyboard (focus and Space, no mousedown): the struck label above pushes the still-selected passage whole below the body's bottom edge, and the float goes with the paint (before: shown 30 px above a passage nobody can see, inside the body's band beside other text, and a click on it commented on text out of view); scrolled back into view, the next keyboard change offers beside the passage", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 500, 400, { docs: { [REPORT]: NOTE_TRACKED } });
    await page.evaluate((st: unknown) => { (window as any).__status = st; }, TRACKED);
    await openPanel(page);
    await page.waitForFunction(() => document.querySelectorAll(".fileview-body .fc-del").length === 1, null, { timeout: 10000 });
    // inline off, by a click (no float yet, so the click's mousedown hides nothing)
    await page.click('button[data-act="fcinline"]');
    await page.waitForFunction(() => document.querySelectorAll(".fileview-body .fc-del").length === 0, null, { timeout: 10000 });
    await frames(page, 2);
    // paragraph 6 forty pixels under the body's top; a real drag over its first line's characters 5 to 20
    await page.evaluate(() => {
      const body = document.querySelector(".fileview-body") as HTMLElement;
      const p = Array.from(document.querySelectorAll(".fileview-md > p")).find((e) => (e.textContent || "").startsWith("Paragraph 6:")) as HTMLElement;
      body.scrollTop += p.getBoundingClientRect().top - body.getBoundingClientRect().top - 40;
    });
    await frames(page, 2);
    const g = await page.evaluate(() => {
      const p = Array.from(document.querySelectorAll(".fileview-md > p")).find((e) => (e.textContent || "").startsWith("Paragraph 6:")) as HTMLElement;
      const range = document.createRange(); range.setStart(p.firstChild!, 5); range.setEnd(p.firstChild!, 20);
      const b = range.getBoundingClientRect(); return { x1: b.left + 1, x2: b.right - 1, y: b.top + b.height / 2 };
    });
    await page.mouse.move(g.x1, g.y); await page.mouse.down(); await page.mouse.move(g.x2, g.y, { steps: 4 }); await page.mouse.up();
    await page.waitForFunction(() => !(document.querySelector(".fc-float") as HTMLElement).hidden, null, { timeout: 5000 });
    let s = await clipScene(page);
    assert.equal(s.selected, PARA(6).slice(5, 20), "the drag selected the passage");
    // the selected line the body's LAST visible one, three pixels above its bottom edge: the scroll hides the float
    await page.evaluate(() => {
      const body = document.querySelector(".fileview-body") as HTMLElement; const sel = getSelection()!;
      const r = sel.getRangeAt(0).getBoundingClientRect(); const b = body.getBoundingClientRect();
      body.scrollTop -= (b.bottom - r.bottom) - 3;
    });
    await page.waitForFunction(() => (document.querySelector(".fc-float") as HTMLElement).hidden, null, { timeout: 5000 });
    await frames(page, 2);
    // Shift+ArrowRight: the keyboard's offer beside the line
    await page.keyboard.down("Shift"); await page.keyboard.press("ArrowRight"); await page.keyboard.up("Shift");
    await page.waitForFunction((n: number) => !(document.querySelector(".fc-float") as HTMLElement).hidden && String(getSelection()).length === n, 16, { timeout: 5000 });
    await frames(page, 2);
    s = await clipScene(page);
    assert.deepEqual([s.selected, s.selInBody, s.hidden], [PARA(6).slice(5, 21), true, false], "the keyboard's offer stands beside the passage, in view on the body's last visible line");
    assert.ok(s.bodyBottom - s.selBottom < 30, "the premise: the selected line is the body's last visible one (its bottom " + (s.bodyBottom - s.selBottom).toFixed(1) + " px above the body's)");
    const offered = { selected: s.selected, top: s.top, left: s.left };
    // the toggle from the keyboard: focus and Space, no mousedown, so nothing but the paint itself touches the float; inline on again
    // paints the deletion's struck label at the fifth paragraph's end, a line more above the sixth
    await page.evaluate(() => { (document.querySelector('button[data-act="fcinline"]') as HTMLElement).focus(); });
    await page.keyboard.press("Space");
    await page.waitForFunction(() => document.querySelectorAll(".fileview-body .fc-del").length === 1, null, { timeout: 10000 });
    await frames(page, 4);
    s = await clipScene(page);
    assert.equal(s.selected, offered.selected, "the paint left the selection whole");
    t.diagnostic("leg 7: after the keyboard toggle the passage sits at " + s.selTop.toFixed(1) + " to " + s.selBottom.toFixed(1) + " against the body's bottom edge at " + s.bodyBottom.toFixed(1));
    assert.equal(s.selBelowBody, true, "the premise: the struck label above pushed the whole passage below the body's bottom edge, out of view");
    assert.equal(s.hidden, true, "the float goes with the paint that moved its subject out of the body's box (before: shown at top " + s.expectedTop.toFixed(1) + ", 30 px above a passage nobody can see, inside the body's band beside other text)");
    assert.equal(s.composer, false, "no composer opened on its own");
    // scrolled back into view (a scroll leaves a hidden float hidden), the person's next keyboard change offers beside the passage
    await page.evaluate(() => {
      const body = document.querySelector(".fileview-body") as HTMLElement; const sel = getSelection()!;
      const r = sel.getRangeAt(0).getBoundingClientRect(); const b = body.getBoundingClientRect();
      body.scrollTop += (r.bottom - b.bottom) + 40;
    });
    await frames(page, 2);
    s = await clipScene(page);
    assert.deepEqual([s.selInBody, s.hidden], [true, true], "scrolled into view, the float stays hidden until the person's next change");
    await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
    await page.keyboard.down("Shift"); await page.keyboard.press("ArrowRight"); await page.keyboard.up("Shift");
    await page.waitForFunction((n: number) => !(document.querySelector(".fc-float") as HTMLElement).hidden && String(getSelection()).length === n, 17, { timeout: 5000 });
    s = await clipScene(page);
    assert.equal(s.selected, PARA(6).slice(5, 22), "the keyboard widened the selection by one character");
    near(s.left, s.expectedLeft, "the keyboard's change offers the float beside the selection's end"); near(s.top, s.expectedTop, "on its line");
    assert.equal(s.floatInBodyBand, true, "...inside the body's band, beside the passage");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});
