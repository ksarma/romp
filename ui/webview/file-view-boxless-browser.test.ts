// An open's target, its keyboard and its leave under a body with NO box, in headless Chromium over the REAL viewer
// (plans/markdown-viewer.md Slice 6, items 1, 3 and 4; the review's round 5). The Files pane's document can be display:none
// while a fetch is in flight or while the reader is away (the pane toggled off, a phone's tab swap, a restart's pagehide over
// a hidden pane): every rect then reads zero and scrollTop 0, scrollIntoView moves nothing and body.focus() is a no-op. Before
// this round the landing spent the open's line, offset or heading over that zero layout and counted it done, so once the pane
// showed the note stood at its top with no notice (item 4); it took the keyboard while nothing could hold it, so nothing held
// it after the show until a click (item 1); and the hide's own width report re-read the place over the hidden layout and
// cleared it, so a leave under the hidden pane wrote nothing and the Recent row kept the leave before it (item 3). Now the
// line, the offset, the heading and the keyboard wait for a body with a box (file-view.ts landTarget; the heading's frame parks
// the target again) and are spent from the width hook's repaint at the show; notePlace keeps the last measured place under a
// boxless body, the hide's report seats and lands nothing (its reflow still reaches the panel's hooks), and the leave writes that
// place with its scrollTop (liveRecord). Item 3's remembered place has had the same guard since round 4 (the fold leg's tenth
// test, file-view-place-memory-fold-browser.test.ts). The page's document stays visible here (the viewer's overlay alone is
// display:none), so its animation frames run under the
// hide, and the heading's frame parks the target for the show; an iframe its parent hides may run none until the show, where
// that frame then lands the target itself and the repaint finds nothing pending: the landing is the same either way. Every
// arm is red over a `git archive` of ad612d193 (scrollTop 0 and no notice after the show, the document's body active, no leave
// record); the visible control lands the same before and after. The review's round 6 (the third and fourth legs, each red over a
// `git archive` of 85fa51bf5): a reload that landed under the hide left `place` naming its block in the OLD text, and the leave
// stamped that span with the NEW mtime; the leave now follows the place into the text that shows (measuredPlace). And a scroll in
// the task of the hide, whose frame found no box, was undone at the show by the repaint's seat over the place read before it; the
// show now reads the offset the browser restored (scrollUnread). The review's closing pass (the fifth leg, red over a `git archive`
// of 14a246665): in the Raw view Chromium restores the offset SHORT when the reader stood in the note's last 144 px (a clamp
// against a layout pass shorter than the final one; the Rendered view's restore is exact), and the show read that offset as the
// reader's, so a clamped seat's hold was dropped and a small scroll into the end zone came back behind the place before it; a
// restore that moved the body, told by its own scroll event, an exact restore firing none, and landed below the place last measured
// now seats the place. Skips LOUDLY without a playwright browser (CI installs none).
// Synthetic values only: an invented report, /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, frames, paintsReach, topBlock, PARA, LONG, LONG2, MT2, REPORT, SID } from "./real-viewer-leg";

/** A heading and a paragraph per section, fifty-nine sections: `## Section i` then Paragraph i. */
const SECTIONS = "# Report\n\n" + Array.from({ length: 59 }, (_, i) => `## Section ${i + 1}\n\n${PARA(i + 1)}`).join("\n\n") + "\n";
const near = (a: number, b: number, what: string, tol = 1) => assert.ok(Math.abs(a - b) <= tol, `${what}: ${a} vs ${b}`);

type Landing = { rects: number; scrollTop: number; clientHeight: number; notice: string | null; active: string; found: boolean; top: number | null; inBox: boolean; painted: boolean };
/** In the page: the body's box (rects, scrollTop, height), the notice bar's words, the active element, and the target: the `idx`-th
 *  element matching `sel` whose text starts with `prefix` (none: any), its top from the body's edge and whether its box lies inside
 *  the body's. */
function readLanding([sel, idx, prefix]: [string, number, string]): Landing {
  const body = document.querySelector(".fileview-body") as HTMLElement; const br = body.getBoundingClientRect();
  const els = (Array.from(document.querySelectorAll(sel)) as HTMLElement[]).filter((e) => !prefix || (e.textContent || "").startsWith(prefix));
  const el = els[idx] || null; const r = el ? el.getBoundingClientRect() : null;
  const bar = document.getElementById("fileview-save-err");
  const a = document.activeElement as HTMLElement | null;
  return {
    rects: body.getClientRects().length, scrollTop: body.scrollTop, clientHeight: body.clientHeight, notice: bar ? (bar.textContent || "") : null,
    active: a ? a.tagName + "." + String(a.className).split(/\s+/).filter(Boolean).join(".") : "none",
    found: !!el, top: r ? Math.round((r.top - br.top) * 10) / 10 : null, inBox: !!r && r.height > 0 && r.bottom > br.top + 0.5 && r.top < br.bottom - 0.5,
    painted: !!document.querySelector(".fileview-md > p, code.hljs .fv-cl"),
  };
}
/** In the page: the overlay's hide rule (the pane's iframe display:none, as its parent hides it), and a gate the file GET awaits
 *  while `window.__gate` is set (a HEAD and every other request pass), so the hide can come while the fetch is in flight. */
const install = (page: any): Promise<void> => page.evaluate(() => {
  const st = document.createElement("style"); st.textContent = "body.fv-pane-hidden #romp-fileview { display: none !important; }"; document.head.appendChild(st);
  const w = window as any; const real = w.fetch; w.__gate = null; w.__release = null;
  w.fetch = async (url: any, init: any) => { if (/[?&]path=/.test(String(url)) && !(init && init.method === "HEAD") && w.__gate) await w.__gate; return real(url, init); };
});
const gate = (page: any): Promise<void> => page.evaluate(() => { const w = window as any; w.__gate = new Promise<void>((r) => { w.__release = r; }); });
const release = (page: any): Promise<void> => page.evaluate(() => { const w = window as any; const r = w.__release; w.__gate = null; w.__release = null; r(); });
const hide = (page: any, on: boolean): Promise<void> => page.evaluate((h: boolean) => { document.body.classList.toggle("fv-pane-hidden", h); }, on);
const paints = (page: any): Promise<number> => page.evaluate(() => (window as any).__paints);
/** Press PageDown and wait for the body's scrollTop to pass `from`; false when it never does. */
const pageDownMoves = (page: any, from: number): Promise<boolean> => page.keyboard.press("PageDown").then(() => page.waitForFunction((v: number) => (document.querySelector(".fileview-body") as HTMLElement).scrollTop > v, from, { timeout: 3000 }).then(() => true, () => false));
const BODY_EL = "DIV.fileview-body";

type Arm = { name: string; at: Record<string, unknown>; target: [string, number, string] };
const ARMS: Arm[] = [
  { name: "heading", at: { heading: "section-39" }, target: ["#md-section-39", 0, ""] },                    // item 4's `{ heading }`: the section's top at the body's edge less the 10 px scroll margin
  { name: "line", at: { line: 40 }, target: ["code.hljs .fv-cl", 39, ""] },                                   // `{ line }`: the Raw view for this open, row 40 centred
  { name: "offset", at: { offset: SECTIONS.indexOf("Paragraph 39:") }, target: [".fileview-md > p", 0, "Paragraph 39:"] },   // `{ offset }`: the block holding it centred
];

test("in a browser, the pane at 900 px (review round 5): an open at a heading, a line or an offset whose first text paint happens while the viewer has no box (the pane's document display:none while the fetch was in flight) lands its target once the pane shows, with no notice, and the body then holds the keyboard so PageDown scrolls (before the fix: the target spent over the zero layout and counted as done, the note at its top with no notice after the show, and nothing holding the keyboard until a click); the visible control lands the same", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const hidden of [false, true]) for (const arm of ARMS) {
      const what = arm.name + (hidden ? ", hidden at the paint" : ", visible throughout");
      const { page, errors } = await openViewer(browser, "pane", 900, 520, { docs: { [REPORT]: SECTIONS } });
      await install(page);
      await page.evaluate(() => { (window as any).FV.closeFileView(); });
      assert.equal(await page.evaluate(() => document.activeElement === document.body), true, what + ": the close dropped the keyboard to the document's body");
      await gate(page);
      const p0 = await paints(page);
      await page.evaluate(([p, sid, o]: [string, string, Record<string, unknown>]) => { (window as any).FV.openFileView(p, sid, { at: o }); }, [REPORT, SID, arm.at]);
      await frames(page, 2);
      if (hidden) { await hide(page, true); await frames(page, 2); }
      await release(page);
      await paintsReach(page, p0 + 1); await frames(page, 3);
      if (hidden) {
        const under: Landing = await page.evaluate(readLanding, arm.target);
        assert.equal(under.painted, true, what + ": the text painted under the hide");
        assert.deepEqual([under.rects, under.clientHeight, under.scrollTop, under.notice], [0, 0, 0, null], what + ": a body with no box, nothing scrolled, no notice (" + JSON.stringify(under) + ")");
        const p1 = await paints(page);
        await hide(page, false);
        await paintsReach(page, p1 + 1);   // the width hook's repaint at the show (the ResizeObserver's report, one reflow paint), which spends the target
        await frames(page, 3);
      }
      const l: Landing = await page.evaluate(readLanding, arm.target);
      assert.ok(l.rects > 0 && l.clientHeight > 0, what + ": the body has a box now");
      assert.equal(l.found, true, what + ": the target element is in the body");
      assert.ok(l.scrollTop > 0, what + ": the body scrolled to the target (before the fix, hidden: 0, the note at its top; " + JSON.stringify(l) + ")");
      if (arm.name === "heading") assert.ok(l.top !== null && l.top >= -1 && l.top <= 12, what + ": the heading's top at the body's edge less its scroll margin (" + l.top + ")");
      else assert.equal(l.inBox, true, what + ": the target's box lies inside the body's (top " + l.top + ", height " + l.clientHeight + ")");
      assert.equal(l.notice, null, what + ": no notice: the section exists and nothing is past the end");
      assert.equal(l.active, BODY_EL, what + ": the body holds the keyboard (before the fix, hidden: the document's body, the landing's focus call a no-op under display:none)");
      if (arm.name === "heading") assert.equal(await pageDownMoves(page, l.scrollTop), true, what + ": PageDown scrolls the note with no click first");
      assert.deepEqual(errors, [], what + ": no page errors");
      await page.close();
    }
  });
});

/** A second host on initFileView, so the record a leave hands the host is readable (window.__leaves); the poster answers a status ask
 *  as the page's own does (file-view-place-memory-fold-browser.test.ts's idiom). */
const hookLeaves = (page: any): Promise<void> => page.evaluate(() => {
  const w = window as any; w.__leaves = [];
  w.FV.initFileView((m: any) => {
    w.__posted.push(m);
    if (m && m.type === "fileComments" && w.__autoReply) {
      const reply = Object.assign({ type: "fileCommentsResult", reqId: m.reqId, fileMtimeNs: w.__mtime }, w.__status);
      setTimeout(() => { window.dispatchEvent(new MessageEvent("message", { data: reply })); }, 0);
    }
  }, undefined, { onLeave: (_p: string, _sid: string | null, rec: unknown) => { w.__leaves.push(rec); } });
});
const leaves = (page: any): Promise<any[]> => page.evaluate(() => (window as any).__leaves);

test("in a browser, the pane at 900 px (review round 5): a leave while the viewer has no box (the pane hidden: a restart's pagehide, or a close) writes the reader's place as last measured with its scrollTop, so the next open returns to it (before the fix: the hide's own width report re-read the place over the hidden layout and cleared it, the leave wrote nothing, and the Recent row kept the leave before it)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 900, 520, { docs: { [REPORT]: LONG } });
    await install(page);
    await hookLeaves(page);
    await page.evaluate(() => { (window as any).putAtTop("Paragraph 80"); }); await frames(page, 1);
    await page.evaluate(() => { (document.querySelector(".fileview-body") as HTMLElement).scrollTop += 12; }); await frames(page, 2);
    const before = (await topBlock(page))!;
    assert.ok(before.text.startsWith("Paragraph 80") && before.top < -11 && before.top > -13, "the scene: Paragraph 80 read 12 px in (" + JSON.stringify(before) + ")");
    const start = LONG.indexOf("Paragraph 80:");
    assert.ok(start > 0);
    // the pane hidden, then the page's pagehide (a restart reloads the panes; the viewer writes without retiring)
    await hide(page, true); await frames(page, 3);
    assert.equal(await page.evaluate(() => (document.querySelector(".fileview-body") as HTMLElement).getClientRects().length), 0, "the body has no box under the hide");
    await page.evaluate(() => { window.dispatchEvent(new Event("pagehide")); });
    let recs = await leaves(page);
    assert.ok(recs.length >= 1, "the pagehide under the hidden pane wrote a record (before the fix: none, the place cleared by the hide's width report)");
    const rec = recs[recs.length - 1];
    assert.equal(rec.start, start, "the record names Paragraph 80's block, the place as last measured (" + JSON.stringify(rec) + ")");
    assert.equal(rec.view, "rendered"); near(rec.scrollTop, before.scrollTop, "with the scrollTop as last measured, not the hidden layout's 0");
    near(rec.top, before.top, "and the depth as read");
    // a close under the hidden pane writes the same place
    await page.evaluate(() => { (window as any).FV.closeFileView(); });
    recs = await leaves(page);
    const rec2 = recs[recs.length - 1];
    assert.ok(recs.length >= 2 && rec2 !== rec, "the close wrote too");
    assert.equal(rec2.start, start, "the close's record names the same block (" + JSON.stringify(rec2) + ")"); near(rec2.scrollTop, before.scrollTop, "with the same scrollTop");
    // the pane shown again: the reopen (the memory's record, as a Recent row would hand it back) returns to the place
    await hide(page, false); await frames(page, 2);
    const p0 = await paints(page);
    await page.evaluate(([p, sid]: [string, string]) => { (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID]);
    await paintsReach(page, p0 + 1); await frames(page, 3);
    const after = (await topBlock(page))!;
    assert.ok(after.text.startsWith("Paragraph 80"), "the reopen returns to Paragraph 80 (read " + JSON.stringify(after) + "; before the fix: the leave before it, or the top)");
    near(after.top, before.top, "at the same edge"); near(after.scrollTop, before.scrollTop, "the scrollTop back");
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});

test("in a browser, the pane at 900 px (review round 6): a reload that lands while the viewer has no box (the Comments panel's poll after a session's write, the pane toggled off) followed by a leave under the hide (a restart's pagehide, a close) writes the reader's block in the text that landed, at its mtime, so the reopen returns to it (before the fix: the place as last measured, read in the OLD text, was stamped with the NEW mtime, a record that claimed exactness and named an offset the new text has no block at, and the reopen fell to its numeric scrollTop, another passage); the visible control writes the same span", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const start2 = LONG2.indexOf("Paragraph 80:");
    assert.ok(start2 > LONG.indexOf("Paragraph 80:"), "the write moved the block");
    for (const hidden of [false, true]) {
      const what = hidden ? "hidden at the landing" : "visible throughout";
      const { page, errors } = await openViewer(browser, "pane", 900, 520, { docs: { [REPORT]: LONG } });
      await install(page); await hookLeaves(page);
      await page.evaluate(() => { (window as any).putAtTop("Paragraph 80"); }); await frames(page, 1);
      await page.evaluate(() => { (document.querySelector(".fileview-body") as HTMLElement).scrollTop += 12; }); await frames(page, 2);
      const before = (await topBlock(page))!;
      assert.ok(before.text.startsWith("Paragraph 80") && before.top < -11 && before.top > -13, what + ": Paragraph 80 read 12 px in (" + JSON.stringify(before) + ")");
      if (hidden) {
        await hide(page, true); await frames(page, 3);
        assert.equal(await page.evaluate(() => (document.querySelector(".fileview-body") as HTMLElement).getClientRects().length), 0, what + ": the body has no box under the hide");
      }
      // the session's write, twenty paragraphs above the reader's block; the poll's reload lands (the seam's reload is the poll's own call)
      await page.evaluate(([p, t2, m2]: [string, string, string]) => { const w = window as any; w.__docs[p] = t2; w.__mtime = m2; w.__seam.reload(); }, [REPORT, LONG2, MT2]);
      await page.waitForFunction((m2: string) => (window as any).__seam.mtimeNs() === m2, MT2, { timeout: 10000 });
      await frames(page, 2);
      await page.evaluate(() => { window.dispatchEvent(new Event("pagehide")); });
      let recs = await leaves(page);
      const rec = recs[recs.length - 1];
      assert.ok(rec, what + ": the pagehide wrote a record");
      assert.equal(rec.mtimeNs, MT2, what + ": at the landed file's mtime");
      assert.equal(rec.start, start2, what + ": the record names Paragraph 80's block in the text that landed (" + JSON.stringify(rec) + "; before the fix, hidden: " + LONG.indexOf("Paragraph 80:") + ", the old text's offset under the new mtime)");
      near(rec.top, before.top, what + ": with the depth as read");
      await page.evaluate(() => { (window as any).FV.closeFileView(); });
      recs = await leaves(page);
      assert.equal(recs[recs.length - 1].start, start2, what + ": the close's record names the same block");
      if (hidden) { await hide(page, false); await frames(page, 2); }
      const p0 = await paints(page);
      await page.evaluate(([p, sid]: [string, string]) => { (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID]);
      await paintsReach(page, p0 + 1); await frames(page, 3);
      const after = (await topBlock(page))!;
      assert.ok(after.text.startsWith("Paragraph 80"), what + ": the reopen returns to Paragraph 80 (read " + JSON.stringify(after) + ")");
      near(after.top, before.top, what + ": at the same edge");
      assert.deepEqual(errors, [], what + ": no page errors");
      await page.close();
    }
  });
});

test("in a browser, the pane at 900 px (review round 6): a scroll in the task of the hide (a wheel tick, or a fling's last frame as the rail is clicked or a phone swaps tabs), whose frame finds the body with no box, is kept at the show: the body stands where the browser restores it, 100 px on, and the place is read there, so the next reflow keeps the block that scroll put at the edge (before the fix: the show's repaint seated the place read before that scroll and moved the body back; the tree before round 5 seated nothing there, its place cleared by the hide); the control, the scroll three frames before the hide, lands the same", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const sameTask of [true, false]) {
      const what = sameTask ? "the scroll in the hide's task" : "the scroll three frames before the hide (control)";
      const { page, errors } = await openViewer(browser, "pane", 900, 520, { docs: { [REPORT]: LONG } });
      await install(page);
      await page.evaluate(() => { (window as any).putAtTop("Paragraph 50"); }); await frames(page, 3);
      const before = (await topBlock(page))!;
      assert.ok(before.text.startsWith("Paragraph 50") && Math.abs(before.top) < 1, what + ": Paragraph 50 at the edge (" + JSON.stringify(before) + ")");
      const p0 = await paints(page);
      if (sameTask) await page.evaluate(() => { (document.querySelector(".fileview-body") as HTMLElement).scrollTop += 100; document.body.classList.add("fv-pane-hidden"); });
      else { await page.evaluate(() => { (document.querySelector(".fileview-body") as HTMLElement).scrollTop += 100; }); await frames(page, 3); await hide(page, true); }
      await paintsReach(page, p0 + 1);   // the hide's report reaches the panel's hooks as a reflow; nothing is seated over the boxless body
      await frames(page, 3);
      const under = await page.evaluate(() => { const b = document.querySelector(".fileview-body") as HTMLElement; return { rects: b.getClientRects().length, scrollTop: b.scrollTop }; });
      assert.deepEqual(under, { rects: 0, scrollTop: 0 }, what + ": no box under the hide, the scrollTop reading 0");
      const p1 = await paints(page);
      await hide(page, false);
      await paintsReach(page, p1 + 1);   // the show's report
      await frames(page, 3);
      const after = (await topBlock(page))!;
      near(after.scrollTop, before.scrollTop + 100, what + ": the body stands 100 px on from the read before the scroll, where the browser restored it (before the fix, in the hide's task: back at " + before.scrollTop + ")");
      assert.ok(!after.text.startsWith("Paragraph 50") || after.top <= -99, what + ": the edge is 100 px into the text past Paragraph 50's top (" + JSON.stringify(after) + ")");
      // the place was read there: a reflow (the pane a pixel narrower) seats the block the scroll put at the edge, not the one read before it
      const p2 = await paints(page);
      await page.setViewportSize({ width: 899, height: 520 });
      await paintsReach(page, p2 + 1); await frames(page, 3);
      const reflowed = (await topBlock(page))!;
      assert.equal(reflowed.text, after.text, what + ": the reflow keeps the block the scroll put at the edge (before the fix: the place a frame stale)");
      assert.deepEqual(errors, [], what + ": no page errors");
      await page.close();
    }
  });
});

/** Click the actions row's view toggle by its label ("Rendered" or "Raw"), as the person does. */
const clickView = (page: any, label: string): Promise<void> => page.evaluate((l: string) => { (Array.from(document.querySelectorAll(".fileview-acts button")) as HTMLButtonElement[]).find((x) => x.textContent === l)!.click(); }, label);
/** The body's scrollTop and its scroll extent. */
const extent = (page: any): Promise<{ top: number; max: number }> => page.evaluate(() => { const b = document.querySelector(".fileview-body") as HTMLElement; return { top: b.scrollTop, max: b.scrollHeight - b.clientHeight }; });

test("in a browser, the pane at 900 px (review closing pass): in the Raw view Chromium restores the offset SHORT at the show when the reader stood in the note's last 144 px (a clamp against a layout pass shorter than the final one; the Rendered view's restore is exact), and the restore's own scroll event, which an exact restore never fires, tells the show's repaint the offset moved: a restore landing below the place last measured seats the place instead of reading the offset, so the hold a clamped Raw seat took from the Rendered view's end survives a hide in the seat's own scroll event and the swap back lands where the reader was (before the fix: the short offset read as the reader's, the hold dropped, the swap back four blocks off), and a small scroll into the end zone with the hide in its task comes back no further behind than the place a frame before it (before: 116 px short of the scroll and 86 px behind that place); the controls, the hide three frames after the swap, the scroll three frames before the hide, and the Rendered view's end zone, land exact", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    // (a) the hold: Rendered at the note's end, the swap to Raw clamps and holds; the hide in the seat's own scroll event, or three frames later
    for (const sameEvent of [true, false]) {
      const what = "the hold, the hide " + (sameEvent ? "in the seat's own scroll event" : "three frames after the swap (control)");
      const { page, errors } = await openViewer(browser, "pane", 900, 520, { docs: { [REPORT]: LONG } });
      await install(page);
      await page.evaluate(() => { const b = document.querySelector(".fileview-body") as HTMLElement; b.scrollTop = b.scrollHeight; }); await frames(page, 3);
      const before = (await topBlock(page))!;
      const endR = await extent(page);
      assert.equal(before.view, "rendered"); assert.equal(endR.top, endR.max, what + ": the Rendered view at its end (" + JSON.stringify(before) + ")");
      const p0 = await paints(page);
      if (sameEvent) await page.evaluate(() => { (document.querySelector(".fileview-body") as HTMLElement).addEventListener("scroll", () => { document.body.classList.add("fv-pane-hidden"); }, { once: true }); });
      await clickView(page, "Raw");
      await paintsReach(page, p0 + 1);   // the swap's paint (its seat clamps at the Raw view's end and holds the Rendered place)
      if (!sameEvent) { await frames(page, 3); await hide(page, true); }
      await paintsReach(page, p0 + 2);   // the hide's report reaches the hooks as a reflow; nothing is seated over the boxless body
      await frames(page, 3);
      const under = await page.evaluate(() => { const b = document.querySelector(".fileview-body") as HTMLElement; return { rects: b.getClientRects().length, scrollTop: b.scrollTop, raw: !!b.querySelector("code.hljs") }; });
      assert.deepEqual(under, { rects: 0, scrollTop: 0, raw: true }, what + ": the Raw view painted, no box under the hide");
      const p1 = await paints(page);
      await hide(page, false);
      await paintsReach(page, p1 + 1); await frames(page, 3);   // the show's report
      const shown = (await topBlock(page))!;
      const endRaw = await extent(page);
      assert.equal(shown.view, "raw");
      near(endRaw.top, endRaw.max, what + ": the body stands at the Raw view's end after the show, where the clamped seat left it (before the fix, in the seat's event: the short restore read as the reader's place; " + JSON.stringify({ shown, endRaw }) + ")");
      const p2 = await paints(page);
      await clickView(page, "Rendered");
      await paintsReach(page, p2 + 1); await frames(page, 3);
      const after = (await topBlock(page))!;
      assert.equal(after.text, before.text, what + ": the swap back lands the block the reader had at the edge (before the fix, in the seat's event: four blocks earlier; " + JSON.stringify({ before, after }) + ")");
      near(after.top, before.top, what + ": at the same edge"); near(after.scrollTop, before.scrollTop, what + ": the scrollTop back");
      assert.deepEqual(errors, [], what + ": no page errors");
      await page.close();
    }
    // (b) the end zone: Raw or Rendered, the reader 58 px from the end scrolls 30 px on, with the hide in the scroll's task or three frames later
    for (const raw of [true, false]) for (const sameTask of [true, false]) {
      const what = (raw ? "Raw" : "Rendered") + " end zone, the hide " + (sameTask ? "in the scroll's task" : "three frames after the scroll (control)");
      const { page, errors } = await openViewer(browser, "pane", 900, 520, { docs: { [REPORT]: LONG }, raw });
      await install(page);
      await page.evaluate(() => { const b = document.querySelector(".fileview-body") as HTMLElement; b.scrollTop = b.scrollHeight - b.clientHeight - 58; }); await frames(page, 3);
      const before = (await topBlock(page))!;
      const { max } = await extent(page);
      assert.equal(before.view, raw ? "raw" : "rendered"); near(before.scrollTop, max - 58, what + ": 58 px from the end, the place read there");
      const p0 = await paints(page);
      if (sameTask) await page.evaluate(() => { (document.querySelector(".fileview-body") as HTMLElement).scrollTop += 30; document.body.classList.add("fv-pane-hidden"); });
      else { await page.evaluate(() => { (document.querySelector(".fileview-body") as HTMLElement).scrollTop += 30; }); await frames(page, 3); await hide(page, true); }
      await paintsReach(page, p0 + 1); await frames(page, 3);   // the hide's report
      const p1 = await paints(page);
      await hide(page, false);
      await paintsReach(page, p1 + 1); await frames(page, 3);   // the show's report
      const after = (await topBlock(page))!;
      if (raw && sameTask) {
        // the reader's offset (max - 28) is lost to the clamp; the place a frame before it is what the show can seat
        assert.ok(after.scrollTop >= before.scrollTop - 1, what + ": the body stands no further behind than the place a frame before the scroll (before the fix: the short restore, " + (max - 144) + ", read as the reader's; " + JSON.stringify({ before, after, max }) + ")");
        assert.ok(after.scrollTop <= before.scrollTop + 31, what + ": and no further on than the scroll put it");
      } else {
        near(after.scrollTop, before.scrollTop + 30, what + ": the body stands where the scroll put it (" + JSON.stringify({ before, after, max }) + ")");
      }
      assert.deepEqual(errors, [], what + ": no page errors");
      await page.close();
    }
  });
});
