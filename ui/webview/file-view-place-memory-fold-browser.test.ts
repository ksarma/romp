// A remembered place inside a fold, in headless Chromium over the REAL viewer (plans/markdown-viewer.md Slice 6, item 3; the
// review's round 1). A reopen paints every fold as authored (the viewer's foldKeeper is per open, and the record carries no
// fold state), so a place the reader read inside a fold they had opened met a shut fold on the reopen: the block had no shown
// box, the seat fell to the record's numeric scrollTop, and that number, read over the OPEN fold's layout, landed thirty
// paragraphs past the reader's in a document the shut fold had made thousands of pixels shorter (Paragraph 55 shown as the
// remembered Paragraph 25, at 900 and 380 px, in the pane and the chat modal); a folded callout, one block in the anchor map,
// seated its summary at the edge and then took the reader's depth into the open content over a box a summary tall. Now
// landRemembered opens the folds above the remembered block's elements before the seat, as the offset landing and a `#` link
// open them (revealFragmentTarget), and a fold that is the block itself when the record's edge was inside it. Through
// real-viewer-leg.ts's page, at 900 and 380 px: an author's <details> opened and read inside (the reopen shows the fold open and
// the same paragraph at the same edge, the scrollTop back within a pixel), an Obsidian `[!note]-` callout the same, a
// record read in Raw inside the fold's rows and reopened under the Rendered preference (the fold opened, the block at the
// edge), and the control: a fold left shut at the leave stays shut and the block after it comes back exactly. The reopen is
// the same page's (closeFileView, then openFileView of the path: the module's memory hands the record back, as a Recent row
// would through opts.place). Before the fix: red at the first "after" read over a git archive of d91f0c19d. The review's round
// 2 (the third test): a fold the reader left SHUT with its summary straddling the body's edge came back OPEN, since the block's
// own depth, read off the straddling summary, was taken as proof the content had been showing; now the block's own fold opens
// only for a depth past its shut box (a callout and the front matter, at both widths, stay shut; the open callout read inside
// still comes back open), and an open at an offset inside a shut callout opens the callout, where revealFragmentTarget opened
// ancestors alone and centred the shut summary over a hidden passage (red over a git archive of c88444f85). The review's round
// 3 (the fourth to sixth tests): the record carries the Rendered view's open folds by ordinal (RememberedPlace.folds), put back
// before the seat at the record's mtime, so a fold the reader had open comes back open whatever the edge's place in it (its
// summary straddling the edge, the round 2 trade; its box at or below the edge; a leave at 900 px reopened at 380, where the
// summary wraps and the shut box the round 2 gate measured is taller), a `[!tip]+` callout the reader closed comes back closed,
// and a changed mtime falls back to the round 2 rules; a Raw record inside a folded callout reopened under the Rendered
// preference opens the callout, the fold being the record's block; and an offset in a comment right after a shut callout,
// which stands aside for the callout's element, leaves the callout as authored (each red over a git archive of 27c56fbf7). The
// review's round 4 (the seventh to tenth tests, each red over a git archive of 7fbced030): a fold the record's own state put
// back is left as it says, so a callout left SHUT at 380 px with the edge 50 px into its two-line shut box, reopened at 900
// where the box is one line, stays shut (the depth rule had re-opened it, the reverse face of the width window round 3 closed);
// a Raw record left at the file's very top, the front matter's block starting under the edge, leaves the front matter shut on
// a Rendered reopen (round 3's other-view rule had read no sign; a Raw record inside the front matter's rows, and one with the
// callout's first row at the edge, still open the fold); a record's folds met by a Raw first paint (Edit saves the Raw
// preference) are held for the open's first Rendered paint, so the toggle after the reopen shows the fold open with the
// reader's passage (before: every fold as authored, the summary at the edge over the hidden passage); and a first paint under a
// body with no box (the pane's document display:none) keeps the record for the width hook's repaint at the show, where the
// note had stood at its top. Skips LOUDLY without a playwright browser (CI installs none), as the other legs do. Synthetic
// values only: an invented report, /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, frames, paintsReach, PARA, REPORT, SID, MT2, LONG, topBlock } from "./real-viewer-leg";

const paras = (a: number, b: number): string => Array.from({ length: b - a + 1 }, (_, i) => PARA(a + i)).join("\n\n");
/** Paragraphs 1 to 10, an author's closed <details> holding 11 to 40, then 41 to 70. */
const DETAILS_NOTE = "# Report\n\n" + paras(1, 10) + "\n\n<details>\n<summary>Closed one</summary>\n\n" + paras(11, 40) + "\n\n</details>\n\n" + paras(41, 70) + "\n";
/** The same shape as an Obsidian folded callout: one blockquote block holding paragraphs 11 to 40. */
const CALLOUT_NOTE = "# Report\n\n" + paras(1, 10) + "\n\n> [!note]- Closed one\n" + Array.from({ length: 30 }, (_, i) => "> " + PARA(11 + i)).join("\n>\n") + "\n\n" + paras(41, 70) + "\n";

type Shown = { text: string; top: number; scrollTop: number; scrollHeight: number; foldOpen: boolean | null } | null;
/** In the page: the first SHOWN paragraph, heading or summary whose box ends below the body's top edge (checkVisibility, so a
 *  shut fold's laid-out content does not count), its first characters and its top from the edge; the fold's state beside it. */
function shownTop(): Shown {
  const body = document.querySelector(".fileview-body") as HTMLElement;
  const br = body.getBoundingClientRect();
  const d = document.querySelector(".fileview-md details");
  const foldOpen = d ? d.hasAttribute("open") : null;
  const els = Array.from(body.querySelectorAll(".fileview-md p, .fileview-md h1, .fileview-md summary")) as HTMLElement[];
  for (const e of els) {
    if (typeof e.checkVisibility === "function" && !e.checkVisibility()) continue;
    const r = e.getBoundingClientRect();
    if (r.bottom > br.top + 0.5) return { text: (e.textContent || "").trim().slice(0, 12), top: Math.round((r.top - br.top) * 10) / 10, scrollTop: body.scrollTop, scrollHeight: body.scrollHeight, foldOpen };
  }
  return null;
}
/** In the page: scroll the body so the paragraph starting with `text` has its top `above` px above the body's edge. */
function putAbove([text, above]: [string, number]): void {
  const body = document.querySelector(".fileview-body") as HTMLElement;
  const p = (Array.from(body.querySelectorAll(".fileview-md p")) as HTMLElement[]).find((e) => (e.textContent || "").indexOf(text) === 0)!;
  body.scrollTop += p.getBoundingClientRect().top - body.getBoundingClientRect().top + above;
}
const read = (page: any): Promise<Shown> => page.evaluate(shownTop);
/** The callout note with the front matter above it: two folds, both shut as authored. */
const FM_NOTE = "---\ntitle: Report\ntags: [alpha, beta]\nowner: nobody\n---\n\n" + CALLOUT_NOTE;
/** In the page: scroll the body so the first `<details>` matching `sel` has its box top `above` px above the body's edge. */
function putFoldAbove([sel, above]: [string, number]): void {
  const body = document.querySelector(".fileview-body") as HTMLElement;
  const d = document.querySelector(sel) as HTMLElement;
  body.scrollTop += d.getBoundingClientRect().top - body.getBoundingClientRect().top + above;
}
type FoldRead = { open: boolean; top: number; bottom: number; summaryTop: number; summaryBottom: number; scrollTop: number; scrollHeight: number; edgeText: string };
/** In the page: the first `<details>` matching `sel`: its state, its box and its summary's against the body's edge, the body's numbers
 *  and the text of the first block whose box ends below the edge. */
function readFold(sel: string): FoldRead {
  const body = document.querySelector(".fileview-body") as HTMLElement; const br = body.getBoundingClientRect();
  const d = document.querySelector(sel) as HTMLElement; const r = d.getBoundingClientRect(); const sr = (d.querySelector("summary") as HTMLElement).getBoundingClientRect();
  const edge = (Array.from(body.querySelectorAll(".fileview-md > *")) as HTMLElement[]).find((e) => e.getBoundingClientRect().bottom > br.top + 0.5);
  const round = (x: number) => Math.round(x * 10) / 10;
  return { open: d.hasAttribute("open"), top: round(r.top - br.top), bottom: round(r.bottom - br.top), summaryTop: round(sr.top - br.top), summaryBottom: round(sr.bottom - br.top),
    scrollTop: body.scrollTop, scrollHeight: body.scrollHeight, edgeText: edge ? (edge.textContent || "").trim().slice(0, 12) : "" };
}
type OffsetRead = { foldOpen: boolean; shown: boolean; inBox: boolean; centreTag: string; centreText: string };
/** In the page: after an open at an offset, the callout's state, whether the paragraph holding the offset is shown inside the body's box,
 *  and what sits at the body's centre. */
function readOffsetLanding(text: string): OffsetRead {
  const body = document.querySelector(".fileview-body") as HTMLElement; const br = body.getBoundingClientRect();
  const d = document.querySelector(".fileview-md details") as HTMLElement;
  const p = (Array.from(body.querySelectorAll(".fileview-md p")) as HTMLElement[]).find((e) => (e.textContent || "").indexOf(text) === 0)!;
  const pr = p.getBoundingClientRect();
  const c = document.elementFromPoint((br.left + br.right) / 2, (br.top + br.bottom) / 2);
  return { foldOpen: d.hasAttribute("open"), shown: typeof p.checkVisibility === "function" ? p.checkVisibility() : pr.height > 0, inBox: pr.bottom > br.top && pr.top < br.bottom,
    centreTag: c ? c.localName : "", centreText: c ? (c.textContent || "").trim().slice(0, 12) : "" };
}
/** Close the viewer and open the same path again in the same page (the module's memory hands the record back), then wait for
 *  the reopen's paint. `raw` false switches the stored preference to Rendered first (a person's Rendered choice on the reopen). */
async function reopen(page: any, opts: { rendered?: boolean } = {}): Promise<void> {
  const before: number = await page.evaluate(() => (window as any).__paints);
  await page.evaluate(() => { (window as any).FV.closeFileView(); });
  if (opts.rendered) await page.evaluate(() => { localStorage.setItem("romp:fileviewFmt", JSON.stringify({ md: "rendered" })); });
  await page.evaluate(([p, sid]: [string, string]) => { (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID]);
  await paintsReach(page, before + 1);
  await frames(page, 3);
}
const near = (a: number, b: number, what: string, tol = 1) => assert.ok(Math.abs(a - b) <= tol, `${what}: ${a} vs ${b}`);

test("in a browser, at 900 and 380 px: a paragraph read inside an author's <details> the reader had opened comes back at the same edge on the reopen, the fold open and the scrollTop within a pixel (before the fix: the fold shut and a paragraph thirty past the reader's at the edge); the same for a folded callout; a fold left shut stays shut and the block after it comes back exactly", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [w, h] of [[900, 520], [380, 520]] as Array<[number, number]>) {
      const what = "pane " + w + "px";
      // the author's <details>: opened by a click on its summary, Paragraph 25 put 20 px above the edge
      {
        const { page, errors } = await openViewer(browser, "pane", w, h, { docs: { [REPORT]: DETAILS_NOTE } });
        await page.click(".fileview-md details > summary");
        await frames(page, 2);
        await page.evaluate(putAbove, ["Paragraph 25", 20]);
        await frames(page, 2);
        const before = (await read(page))!;
        assert.equal(before.text, "Paragraph 25", what + ": the scene starts with Paragraph 25 at the edge inside the open fold");
        assert.equal(before.foldOpen, true, what + ": the fold is open");
        await reopen(page);
        const after = (await read(page))!;
        assert.equal(after.foldOpen, true, what + ": the reopen opened the fold the remembered block sits in (before the fix it painted shut)");
        assert.equal(after.text, "Paragraph 25", what + ": the remembered paragraph is at the edge again (before the fix: Paragraph 55, the numeric scrollTop over the shorter document)");
        near(after.top, before.top, what + ": at its height");
        near(after.scrollTop, before.scrollTop, what + ": the scrollTop is back (the same layout at the same width)");
        assert.deepEqual(errors, [], what + ": no page errors");
        await page.close();
      }
      // the folded callout: one block in the anchor map, so the seat found its box (the shut summary) and applied the reader's
      // depth into the open content over a box a summary tall
      {
        const { page, errors } = await openViewer(browser, "pane", w, h, { docs: { [REPORT]: CALLOUT_NOTE } });
        assert.equal(await page.evaluate(() => !!document.querySelector(".fileview-md details.md-callout")), true, what + ": the callout rendered as a folded block");
        await page.click(".fileview-md details.md-callout > summary");
        await frames(page, 2);
        await page.evaluate(putAbove, ["Paragraph 25", 20]);
        await frames(page, 2);
        const before = (await read(page))!;
        assert.equal(before.text, "Paragraph 25", what + " (callout): the scene starts with Paragraph 25 at the edge inside the open callout");
        await reopen(page);
        const after = (await read(page))!;
        assert.equal(after.foldOpen, true, what + " (callout): the reopen opened the callout");
        assert.equal(after.text, "Paragraph 25", what + " (callout): the remembered paragraph is at the edge again (before the fix: the depth into the open content applied over the shut summary's box)");
        near(after.top, before.top, what + " (callout): at its height");
        assert.deepEqual(errors, [], what + " (callout): no page errors");
        await page.close();
      }
      // the control: the fold left shut, the block after it at the edge; the reopen changes nothing about the fold
      {
        const { page, errors } = await openViewer(browser, "pane", w, h, { docs: { [REPORT]: DETAILS_NOTE } });
        await page.evaluate(putAbove, ["Paragraph 41", 12]);
        await frames(page, 2);
        const before = (await read(page))!;
        assert.equal(before.text, "Paragraph 41", what + " (control): Paragraph 41, the block after the shut fold, at the edge");
        assert.equal(before.foldOpen, false, what + " (control): the fold is shut");
        await reopen(page);
        const after = (await read(page))!;
        assert.equal(after.foldOpen, false, what + " (control): a fold the reader never opened stays shut on the reopen");
        assert.equal(after.text, "Paragraph 41", what + " (control): the block is back at the edge");
        near(after.top, before.top, what + " (control): at its height");
        near(after.scrollTop, before.scrollTop, what + " (control): the scrollTop is back");
        assert.deepEqual(errors, [], what + " (control): no page errors");
        await page.close();
      }
    }
  });
});

test("in a browser, at 900 px: a place read in the Raw view inside the fold's rows, reopened under the Rendered preference, opens the fold and puts the remembered block at the edge (the record's depth is the Raw view's, so the block's top is what is known)", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 900, 520, { docs: { [REPORT]: DETAILS_NOTE }, raw: true });
    // the Raw row of Paragraph 25 (inside the fold's source) 5 px above the edge
    await page.evaluate(() => {
      const body = document.querySelector(".fileview-body") as HTMLElement;
      const row = (Array.from(body.querySelectorAll("code.hljs .fv-cl")) as HTMLElement[]).find((e) => (e.textContent || "").indexOf("Paragraph 25") === 0)!;
      body.scrollTop += row.getBoundingClientRect().top - body.getBoundingClientRect().top + 5;
    });
    await frames(page, 2);
    const rowAtEdge: string = await page.evaluate(() => {
      const body = document.querySelector(".fileview-body") as HTMLElement; const br = body.getBoundingClientRect();
      const rows = Array.from(body.querySelectorAll("code.hljs .fv-cl")) as HTMLElement[];
      const r = rows.find((e) => e.getBoundingClientRect().bottom > br.top + 0.5)!;
      return (r.textContent || "").trim().slice(0, 12);
    });
    assert.equal(rowAtEdge, "Paragraph 25", "the scene starts with Paragraph 25's row at the edge in Raw");
    await reopen(page, { rendered: true });
    const after = (await read(page))!;
    assert.equal(await page.evaluate(() => !!document.querySelector(".fileview-md > p")), true, "the reopen painted the Rendered view");
    assert.equal(after.foldOpen, true, "the fold holding the remembered block was opened (before the fix: shut, and Paragraph 54 at the edge)");
    assert.equal(after.text, "Paragraph 25", "the remembered block is at the edge");
    assert.ok(after.top <= 0.5 && after.top >= -1, "its top at the edge (the depth is the other view's and is not applied): read " + after.top);
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});


test("in a browser, at 900 and 380 px (review round 2): a fold the reader left SHUT with its summary straddling the body's edge stays shut on the reopen, the scrollTop and the scrollHeight unchanged (before: the block's own depth, read off the straddling summary, opened it, and the callout's thirty paragraphs came back shown), for a folded callout and for the front matter; the callout opened and read inside still comes back open; and an open at an offset inside a shut callout opens the callout with the passage shown (before: the shut summary was centred over the hidden passage)", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const CALLOUT = ".fileview-md details.md-callout", FM = ".fileview-md details.md-frontmatter";
    for (const [w, h] of [[900, 520], [380, 520]] as Array<[number, number]>) {
      const what = "pane " + w + "px";
      // the shut callout, its box top 6 px and then 14 px above the edge (the summary straddles it; the fold's content is not at the edge)
      for (const above of [6, 14]) {
        const { page, errors } = await openViewer(browser, "pane", w, h, { docs: { [REPORT]: CALLOUT_NOTE } });
        await page.evaluate(putFoldAbove, [CALLOUT, above]); await frames(page, 2);
        const before: FoldRead = await page.evaluate(readFold, CALLOUT);
        assert.equal(before.open, false, what + " (callout " + above + " above): the scene starts with the callout shut");
        assert.ok(before.top < 0 && before.summaryBottom > 0, what + " (callout " + above + " above): its summary straddles the edge (box top " + before.top + ", summary bottom " + before.summaryBottom + ")");
        await reopen(page);
        const after: FoldRead = await page.evaluate(readFold, CALLOUT);
        assert.equal(after.open, false, what + " (callout " + above + " above): a fold left shut stays shut on the reopen (before the fix: open, the depth into the summary read as a depth into the content)");
        assert.equal(after.scrollHeight, before.scrollHeight, what + " (callout " + above + " above): the document is the same height (before: the callout's thirty paragraphs came back shown)");
        near(after.scrollTop, before.scrollTop, what + " (callout " + above + " above): the scrollTop is back");
        near(after.top, before.top, what + " (callout " + above + " above): the summary is at the same place");
        assert.deepEqual(errors, [], what + ": no page errors");
        await page.close();
      }
      // the front matter, shut as authored, its box top 8 px above the edge (the reader scrolled a little into the note's head)
      {
        const { page, errors } = await openViewer(browser, "pane", w, h, { docs: { [REPORT]: FM_NOTE } });
        assert.equal(await page.evaluate(() => !!document.querySelector(".fileview-md details.md-frontmatter")), true, what + " (front matter): the front matter renders as a fold");
        await page.evaluate(putFoldAbove, [FM, 8]); await frames(page, 2);
        const before: FoldRead = await page.evaluate(readFold, FM);
        assert.equal(before.open, false, what + " (front matter): shut at the leave"); assert.ok(before.top < 0 && before.summaryBottom > 0, what + " (front matter): its summary straddles the edge");
        await reopen(page);
        const after: FoldRead = await page.evaluate(readFold, FM);
        assert.equal(after.open, false, what + " (front matter): stays shut (before the fix: open)");
        assert.equal(after.scrollHeight, before.scrollHeight, what + " (front matter): the same document height");
        near(after.scrollTop, before.scrollTop, what + " (front matter): the scrollTop is back");
        assert.deepEqual(errors, [], what + " (front matter): no page errors");
        await page.close();
      }
      // the callout the reader OPENED, with its summary straddling the edge and the content under it: the depth is inside the summary's
      // own height, which says nothing to the depth rule, so round 2 painted the fold as authored (shut) with the next section's passage
      // under the summary; since round 3 the record's fold state brings it back open (the fourth test reads that), and either way the
      // reader's edge block and its place are unchanged, which is what this scene pins
      {
        const { page, errors } = await openViewer(browser, "pane", w, h, { docs: { [REPORT]: CALLOUT_NOTE } });
        await page.click(CALLOUT + " > summary"); await frames(page, 2);
        await page.evaluate(putFoldAbove, [CALLOUT, 6]); await frames(page, 2);
        const before: FoldRead = await page.evaluate(readFold, CALLOUT);
        assert.equal(before.open, true, what + " (open callout, summary straddling): the scene starts open");
        await reopen(page);
        const after: FoldRead = await page.evaluate(readFold, CALLOUT);
        near(after.top, before.top, what + " (open callout, summary straddling): the summary is at the same place on the reopen");
        assert.equal(after.edgeText, before.edgeText, what + " (open callout, summary straddling): the same block at the edge");
        assert.deepEqual(errors, [], what + " (open callout, summary straddling): no page errors");
        await page.close();
      }
      // the callout the reader opened and read INSIDE (Paragraph 25 twenty px above the edge): the depth is far past the shut box, so the
      // fold comes back open with the passage at the edge, as the first test asserts; here as the control that the refinement kept it
      {
        const { page, errors } = await openViewer(browser, "pane", w, h, { docs: { [REPORT]: CALLOUT_NOTE } });
        await page.click(CALLOUT + " > summary"); await frames(page, 2);
        await page.evaluate(putAbove, ["Paragraph 25", 20]); await frames(page, 2);
        await reopen(page);
        const after = (await read(page))!;
        assert.equal(after.foldOpen, true, what + " (callout read inside): the reopen opened the callout");
        assert.equal(after.text, "Paragraph 25", what + " (callout read inside): the remembered paragraph is at the edge");
        assert.deepEqual(errors, [], what + " (callout read inside): no page errors");
        await page.close();
      }
      // an open at an offset inside the shut callout: the block holding the offset IS the callout, and it is opened before the scroll
      {
        const offset = CALLOUT_NOTE.indexOf("Paragraph 25");
        assert.ok(offset > 0);
        const { page, errors } = await openViewer(browser, "pane", w, h, { docs: { [REPORT]: CALLOUT_NOTE }, openOpts: { at: { offset } } });
        await frames(page, 4);
        const landed: OffsetRead = await page.evaluate(readOffsetLanding, "Paragraph 25");
        assert.equal(landed.foldOpen, true, what + " (offset in a shut callout): the callout was opened for the offset (before the fix: shut, its summary centred)");
        assert.equal(landed.shown, true, what + " (offset in a shut callout): the paragraph holding the offset is shown");
        assert.equal(landed.inBox, true, what + " (offset in a shut callout): …inside the body's box (before: hidden under the shut summary)");
        assert.notEqual(landed.centreTag, "summary", what + " (offset in a shut callout): the body's centre is not the shut summary (read " + landed.centreTag + " \"" + landed.centreText + "\")");
        assert.deepEqual(errors, [], what + " (offset in a shut callout): no page errors");
        await page.close();
      }
    }
  });
});

// ── review round 3: fold state in the record; a Raw record in a callout; an offset in a comment after a shut callout ──────
/** The callout block alone, as CALLOUT_NOTE holds it. */
const CALLOUT_BLOCK = "> [!note]- Closed one\n" + Array.from({ length: 30 }, (_, i) => "> " + PARA(11 + i)).join("\n>\n");
/** The same shape as a `[!tip]+` callout: open as authored. */
const TIP_NOTE = "# Report\n\n" + paras(1, 10) + "\n\n> [!tip]+ Open one\n" + Array.from({ length: 30 }, (_, i) => "> " + PARA(11 + i)).join("\n>\n") + "\n\n" + paras(41, 70) + "\n";
/** The callout with a title that is one line at 900 px and two at 380. */
const WRAP_NOTE = CALLOUT_NOTE.replace("[!note]- Closed one", "[!note]- A closed section whose title wraps in a narrow pane only");
/** The shut callout, then an HTML comment (a block with no element of its own), then paragraphs 41 to 70. */
const COMMENT_NOTE = "# Report\n\n" + paras(1, 10) + "\n\n" + CALLOUT_BLOCK + "\n\n<!-- a note to self about the next section -->\n\n" + paras(41, 70) + "\n";
/** The shut callout as the last block, with a trailing blank line. */
const TRAIL_NOTE = "# Report\n\n" + paras(1, 10) + "\n\n" + CALLOUT_BLOCK + "\n\n";
/** In the page: the first SHOWN paragraph whose box ends below the body's top edge (checkVisibility: a shut fold's content does not count). */
function shownPara(): string {
  const body = document.querySelector(".fileview-body") as HTMLElement; const br = body.getBoundingClientRect();
  for (const e of Array.from(body.querySelectorAll(".fileview-md p")) as HTMLElement[]) {
    if (typeof e.checkVisibility === "function" && !e.checkVisibility()) continue;
    if (e.getBoundingClientRect().bottom > br.top + 0.5) return (e.textContent || "").trim().slice(0, 12);
  }
  return "";
}
/** In the page: whether the paragraph starting with `text` is shown (checkVisibility). */
function paraShown(text: string): boolean {
  const p = (Array.from(document.querySelectorAll(".fileview-md p")) as HTMLElement[]).find((e) => (e.textContent || "").indexOf(text) === 0);
  return !!p && (typeof p.checkVisibility === "function" ? p.checkVisibility() : p.getBoundingClientRect().height > 0);
}
/** A second host on initFileView, so the record a leave hands the host is readable (window.__leaves); the poster answers a status
 *  ask as the page's own does. (A second call adds a second message listener; the replies it routes are consumed by the first.) */
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
const lastLeave = (page: any): Promise<any> => page.evaluate(() => { const l = (window as any).__leaves; return l.length ? l[l.length - 1] : null; });
/** Close, then open the same path again after `between` ran in the page (a viewport change, a moved mtime), and wait for the paint. */
async function reopenAfter(page: any, between: () => Promise<void>): Promise<void> {
  const before: number = await page.evaluate(() => (window as any).__paints);
  await page.evaluate(() => { (window as any).FV.closeFileView(); });
  await between();
  await page.evaluate(([p, sid]: [string, string]) => { (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID]);
  await paintsReach(page, before + 1);
  await frames(page, 3);
}

test("in a browser, at 900 and 380 px (review round 3): the record carries the Rendered view's open folds by ordinal, so at the same mtime a fold the reader had OPEN comes back open whatever the edge's place in it: its summary straddling the edge (the round 2 trade, closed: the passage under the summary is the reader's again), its box at or below the edge (a callout, the front matter, an author's <details>), and a `[!tip]+` callout the reader CLOSED comes back closed; the record's folds are numbers and the record holds no word of the note; a changed mtime falls back to the round 2 rules; and a leave at 900 px reopened at 380, where the summary wraps, comes back open too", { timeout: 420000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const CALLOUT = ".fileview-md details.md-callout", FM = ".fileview-md details.md-frontmatter", DET = ".fileview-md details";
    for (const [w, h] of [[900, 520], [380, 520]] as Array<[number, number]>) {
      const what = "pane " + w + "px";
      // the callout the reader opened, its summary straddling the edge (the round 2 scene): back open, Paragraph 11 under the summary again
      {
        const { page, errors } = await openViewer(browser, "pane", w, h, { docs: { [REPORT]: CALLOUT_NOTE } });
        await hookLeaves(page);
        await page.click(CALLOUT + " > summary"); await frames(page, 2);
        await page.evaluate(putFoldAbove, [CALLOUT, 6]); await frames(page, 2);
        const before: FoldRead = await page.evaluate(readFold, CALLOUT);
        assert.equal(before.open, true, what + " (straddling): the scene starts with the callout open");
        assert.equal(await page.evaluate(shownPara), "Paragraph 11", what + " (straddling): the passage under the summary");
        await reopen(page);
        const rec = await lastLeave(page);
        assert.ok(rec, what + ": the leave handed the host a record");
        assert.deepEqual(rec.folds, [0], what + ": the record names the open fold by its ordinal (numbers only)");
        assert.doesNotMatch(JSON.stringify(rec), /Paragraph|lorem|Closed one/, what + ": no word of the note in the record");
        const after: FoldRead = await page.evaluate(readFold, CALLOUT);
        assert.equal(after.open, true, what + " (straddling): the fold comes back open (round 2 painted it as authored, shut, the depth being inside the summary)");
        assert.equal(after.scrollHeight, before.scrollHeight, what + " (straddling): the same document height");
        near(after.top, before.top, what + " (straddling): the summary at the same place"); near(after.scrollTop, before.scrollTop, what + " (straddling): the scrollTop is back");
        assert.equal(await page.evaluate(shownPara), "Paragraph 11", what + " (straddling): the passage under the summary is the reader's again (before the fix: Paragraph 41, the section after the shut fold)");
        // the same leave under another mtime: the ordinals are not trusted, and the round 2 rule stands (the depth is inside the summary: as authored)
        await reopenAfter(page, () => page.evaluate((m: string) => { (window as any).__mtime = m; }, MT2));
        const moved: FoldRead = await page.evaluate(readFold, CALLOUT);
        assert.equal(moved.open, false, what + " (straddling, mtime moved): another mtime, another file: the fold state is not applied and the fold comes back as authored (the round 2 rule)");
        near(moved.top, before.top, what + " (straddling, mtime moved): the same block at the edge");
        assert.deepEqual(errors, [], what + ": no page errors");
        await page.close();
      }
      // the callout the reader opened with its box top 12 px BELOW the edge (the summary in the upper part of the view, the content under it)
      {
        const { page, errors } = await openViewer(browser, "pane", w, h, { docs: { [REPORT]: CALLOUT_NOTE } });
        await page.click(CALLOUT + " > summary"); await frames(page, 2);
        await page.evaluate(putFoldAbove, [CALLOUT, -12]); await frames(page, 2);
        const before: FoldRead = await page.evaluate(readFold, CALLOUT);
        assert.equal(before.open, true); assert.ok(before.top > 0, what + " (below the edge): the box starts under the edge: " + before.top);
        assert.equal(await page.evaluate(paraShown, "Paragraph 11"), true, what + " (below the edge): the content shows under the summary");
        await reopen(page);
        const after: FoldRead = await page.evaluate(readFold, CALLOUT);
        assert.equal(after.open, true, what + " (below the edge): the fold comes back open (before the fix: shut, and Paragraph 41 under the summary)");
        assert.equal(await page.evaluate(paraShown, "Paragraph 11"), true, what + " (below the edge): the content shows again");
        assert.equal(after.scrollHeight, before.scrollHeight, what + " (below the edge): the same document height"); near(after.scrollTop, before.scrollTop, what + " (below the edge): the scrollTop is back"); near(after.top, before.top, what + " (below the edge): the box at the same place");
        assert.deepEqual(errors, [], what + " (below the edge): no page errors");
        await page.close();
      }
      // the front matter opened, its box top 3 px below the edge: its lines come back
      {
        const { page, errors } = await openViewer(browser, "pane", w, h, { docs: { [REPORT]: FM_NOTE } });
        await page.click(FM + " > summary"); await frames(page, 2);
        await page.evaluate(putFoldAbove, [FM, -3]); await frames(page, 2);
        const before: FoldRead = await page.evaluate(readFold, FM);
        assert.equal(before.open, true, what + " (front matter): open at the leave");
        await reopen(page);
        const after: FoldRead = await page.evaluate(readFold, FM);
        assert.equal(after.open, true, what + " (front matter): back open (before the fix: shut, the h1 under its summary)");
        assert.equal(await page.evaluate(() => { const pre = document.querySelector(".fileview-md details.md-frontmatter pre") as HTMLElement | null; return !!pre && pre.checkVisibility(); }), true, what + " (front matter): its lines show");
        assert.equal(after.scrollHeight, before.scrollHeight, what + " (front matter): the same document height");
        assert.deepEqual(errors, [], what + " (front matter): no page errors");
        await page.close();
      }
      // an author's <details> opened, its box top 12 px below the edge (Paragraph 10 the recorded block)
      {
        const { page, errors } = await openViewer(browser, "pane", w, h, { docs: { [REPORT]: DETAILS_NOTE } });
        await page.click(DET + " > summary"); await frames(page, 2);
        await page.evaluate(putFoldAbove, [DET, -12]); await frames(page, 2);
        const before: FoldRead = await page.evaluate(readFold, DET);
        assert.equal(before.open, true); assert.equal(before.edgeText.slice(0, 12), "Paragraph 10", what + " (details): Paragraph 10 is the block at the edge");
        await reopen(page);
        const after: FoldRead = await page.evaluate(readFold, DET);
        assert.equal(after.open, true, what + " (details): back open (before the fix: shut)");
        assert.equal(after.scrollHeight, before.scrollHeight, what + " (details): the same document height"); near(after.scrollTop, before.scrollTop, what + " (details): the scrollTop is back");
        assert.deepEqual(errors, [], what + " (details): no page errors");
        await page.close();
      }
      // a `[!tip]+` callout, open as authored, that the reader closed: back closed (before: as authored, open)
      {
        const { page, errors } = await openViewer(browser, "pane", w, h, { docs: { [REPORT]: TIP_NOTE } });
        const authored: FoldRead = await page.evaluate(readFold, CALLOUT);
        assert.equal(authored.open, true, what + " (tip): open as authored");
        await page.click(CALLOUT + " > summary"); await frames(page, 2);
        await page.evaluate(putFoldAbove, [CALLOUT, -12]); await frames(page, 2);
        const before: FoldRead = await page.evaluate(readFold, CALLOUT);
        assert.equal(before.open, false, what + " (tip): the reader closed it");
        await reopen(page);
        const after: FoldRead = await page.evaluate(readFold, CALLOUT);
        assert.equal(after.open, false, what + " (tip): a fold the reader closed comes back closed (before the fix: open as authored, thirty paragraphs back)");
        assert.equal(after.scrollHeight, before.scrollHeight, what + " (tip): the same document height"); near(after.scrollTop, before.scrollTop, what + " (tip): the scrollTop is back");
        assert.deepEqual(errors, [], what + " (tip): no page errors");
        await page.close();
      }
    }
    // a width change between the leave and the reopen: the callout read open at 900 px with the edge 50 px into it (past its one-line
    // summary), reopened at 380 px where the title wraps to two lines and the shut box is taller than the recorded depth
    {
      const { page, errors } = await openViewer(browser, "pane", 900, 520, { docs: { [REPORT]: WRAP_NOTE } });
      await page.click(CALLOUT + " > summary"); await frames(page, 2);
      await page.evaluate(putFoldAbove, [CALLOUT, 50]); await frames(page, 2);
      const before: FoldRead = await page.evaluate(readFold, CALLOUT);
      assert.equal(before.open, true, "width change: open at the leave"); assert.ok(before.summaryBottom < 0, "width change: the one-line summary is wholly above the edge at 900 px: " + before.summaryBottom);
      assert.equal(await page.evaluate(shownPara), "Paragraph 11", "width change: the content at the edge");
      await reopenAfter(page, async () => { await page.setViewportSize({ width: 380, height: 520 }); await frames(page, 3); });
      const after: FoldRead = await page.evaluate(readFold, CALLOUT);
      assert.ok(after.summaryBottom - after.summaryTop > before.summaryBottom - before.summaryTop + 10, "width change: the summary wraps at 380 px (" + (after.summaryBottom - after.summaryTop) + " px against " + (before.summaryBottom - before.summaryTop) + ")");
      assert.equal(after.open, true, "width change: the fold comes back open (before the fix: the depth of 50 px fell short of the two-line shut box, and the callout came back shut with its summary straddling the edge)");
      assert.equal(await page.evaluate(shownPara), "Paragraph 11", "width change: the content is under the edge again, near where it was");
      assert.deepEqual(errors, [], "width change: no page errors");
      await page.close();
    }
  });
});

test("in a browser, at 900 and 380 px (review round 3): a place read in the Raw view inside a folded CALLOUT's rows, reopened under the Rendered preference, opens the callout, the fold being the record's own block and every Raw row having shown, and seats its top at the edge with the passage shown under the summary (before: revealFragmentTarget opened ancestors alone, and the shut summary sat at the edge over the hidden passage)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const w of [900, 380]) {
      const what = "pane " + w + "px";
      const { page, errors } = await openViewer(browser, "pane", w, 520, { docs: { [REPORT]: CALLOUT_NOTE }, raw: true });
      await page.evaluate(() => {
        const body = document.querySelector(".fileview-body") as HTMLElement;
        const row = (Array.from(body.querySelectorAll("code.hljs .fv-cl")) as HTMLElement[]).find((e) => (e.textContent || "").indexOf("> Paragraph 25") === 0)!;
        body.scrollTop += row.getBoundingClientRect().top - body.getBoundingClientRect().top + 5;
      });
      await frames(page, 2);
      await reopen(page, { rendered: true });
      assert.equal(await page.evaluate(() => !!document.querySelector(".fileview-md > p")), true, what + ": the reopen painted the Rendered view");
      const after: FoldRead = await page.evaluate(readFold, ".fileview-md details.md-callout");
      assert.equal(after.open, true, what + ": the callout the Raw rows were read in is open (before the fix: shut)");
      assert.ok(after.top <= 0.5 && after.top >= -1, what + ": its top at the edge (the other view's depth is not applied): " + after.top);
      assert.equal(await page.evaluate(paraShown, "Paragraph 25"), true, what + ": the passage the reader had is shown (before: hidden under the shut summary)");
      assert.equal(await page.evaluate(shownPara), "Paragraph 11", what + ": the fold's first paragraph under the summary");
      assert.deepEqual(errors, [], what + ": no page errors");
      await page.close();
    }
  });
});

test("in a browser, at 900 and 380 px (review round 3): an open at an offset inside an HTML comment right after a SHUT callout stands aside for the callout's element and leaves the callout as authored, the text after the comment inside the body's box (before: the round 2 line opened the fold the stand-in named, centred its middle and put Paragraph 41 thousands of pixels below the edge); the same for an offset in the trailing blank line after a shut callout that is the last block", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const CALLOUT = ".fileview-md details.md-callout";
    for (const w of [900, 380]) {
      const what = "pane " + w + "px";
      {
        const offset = COMMENT_NOTE.indexOf("a note to self");
        assert.ok(offset > 0);
        const { page, errors } = await openViewer(browser, "pane", w, 520, { docs: { [REPORT]: COMMENT_NOTE }, openOpts: { at: { offset } } });
        await frames(page, 4);
        const landed: OffsetRead = await page.evaluate(readOffsetLanding, "Paragraph 41");
        assert.equal(landed.foldOpen, false, what + " (comment after the callout): the callout stays as authored, shut (before the fix: opened, though the offset named the comment after it)");
        assert.equal(landed.inBox, true, what + " (comment after the callout): the text right after the comment is inside the body's box (before: 1377 px below the edge at 900)");
        assert.deepEqual(errors, [], what + " (comment after the callout): no page errors");
        await page.close();
      }
      {
        const { page, errors } = await openViewer(browser, "pane", w, 520, { docs: { [REPORT]: TRAIL_NOTE }, openOpts: { at: { offset: TRAIL_NOTE.length - 1 } } });
        await frames(page, 4);
        const fold: FoldRead = await page.evaluate(readFold, CALLOUT);
        assert.equal(fold.open, false, what + " (trailing blank line): the last block, a shut callout, stays as authored (before the fix: opened)");
        assert.deepEqual(errors, [], what + " (trailing blank line): no page errors");
        await page.close();
      }
    }
  });
});

/** In the page: the first Raw row (`.fv-cl`) whose box ends below the body's edge, its first characters and its top. */
function rawTop(): { text: string; top: number; scrollTop: number } | null {
  const body = document.querySelector(".fileview-body") as HTMLElement; const br = body.getBoundingClientRect();
  for (const e of Array.from(body.querySelectorAll("code.hljs .fv-cl")) as HTMLElement[]) {
    const r = e.getBoundingClientRect();
    if (r.bottom > br.top + 0.5) return { text: (e.textContent || "").trim().slice(0, 14), top: Math.round((r.top - br.top) * 10) / 10, scrollTop: body.scrollTop };
  }
  return null;
}
/** In the page: scroll the body so the Raw row starting with `text` has its top `above` px above the body's edge. */
function putRowAbove([text, above]: [string, number]): void {
  const body = document.querySelector(".fileview-body") as HTMLElement;
  const row = (Array.from(body.querySelectorAll("code.hljs .fv-cl")) as HTMLElement[]).find((e) => (e.textContent || "").indexOf(text) === 0)!;
  body.scrollTop += row.getBoundingClientRect().top - body.getBoundingClientRect().top + above;
}
/** In the page: every `<details>` of the Rendered body, open or shut, in document order. */
const foldsOpen = (page: any): Promise<boolean[]> => page.evaluate(() => Array.from(document.querySelectorAll(".fileview-md details")).map((d) => d.hasAttribute("open")));
/** Click the bar button labelled `label` and wait for the paint it asks for. */
async function clickBar(page: any, label: string): Promise<void> {
  const before: number = await page.evaluate(() => (window as any).__paints);
  await page.evaluate((l: string) => { const b = Array.from(document.querySelectorAll(".fileview-acts button")).find((x) => x.textContent === l) as HTMLElement; b.click(); }, label);
  await paintsReach(page, before + 1);
  await frames(page, 3);
}

test("in a browser (review round 4): a fold the record's own state put back is left as it says, so a callout left SHUT at 380 px with the edge 50 px into its two-line shut box (and 40 px, inside the wrapped summary), reopened at 900 px where the shut box is one line, stays shut with the shut layout's height (before the fix: the depth rule, measuring the one-line box against the 380 px depth, re-opened the fold restoreFolds had just put back shut, thirty paragraphs back); the 380 to 380 control stays shut; and the round 3 face, the callout read OPEN at 900 with the edge 50 px in and reopened at 380, still comes back open", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const CALLOUT = ".fileview-md details.md-callout";
    for (const D of [50, 40]) for (const [leaveW, reopenW] of [[380, 900], [380, 380]] as Array<[number, number]>) {
      const what = "D=" + D + " leave@" + leaveW + " reopen@" + reopenW;
      const { page, errors } = await openViewer(browser, "pane", leaveW, 520, { docs: { [REPORT]: WRAP_NOTE } });
      await hookLeaves(page);
      await page.evaluate(putFoldAbove, [CALLOUT, D]); await frames(page, 2);
      const before: FoldRead = await page.evaluate(readFold, CALLOUT);
      assert.equal(before.open, false, what + ": the callout is shut as authored at the leave");
      assert.ok(before.top < 0 && before.bottom > 0, what + ": the edge is inside its shut box (top " + before.top + ", bottom " + before.bottom + ")");
      assert.ok(before.summaryBottom - before.summaryTop > 30, what + ": the summary wraps to two lines at 380 px (" + (before.summaryBottom - before.summaryTop) + " px)");
      await reopenAfter(page, async () => { if (reopenW !== leaveW) { await page.setViewportSize({ width: reopenW, height: 520 }); await frames(page, 3); } });
      const rec = await lastLeave(page);
      assert.ok(rec && rec.view === "rendered" && Array.isArray(rec.folds) && rec.folds.length === 0, what + ": the record is Rendered with no open fold (folds " + JSON.stringify(rec && rec.folds) + ")");
      const after: FoldRead = await page.evaluate(readFold, CALLOUT);
      assert.equal(after.open, false, what + ": the fold the reader had SHUT stays shut (before the fix at a width change: open, the depth of " + D + " px past the one-line shut box, and Paragraph 11 shown under the edge)");
      assert.equal(await page.evaluate(paraShown, "Paragraph 11"), false, what + ": the callout's content stays hidden");
      if (reopenW === leaveW) assert.equal(after.scrollHeight, before.scrollHeight, what + ": the same document height");
      else assert.ok(after.scrollHeight < before.scrollHeight, what + ": the shut layout at 900 px is shorter than the shut layout at 380 (" + after.scrollHeight + " against " + before.scrollHeight + "), not the open one");
      assert.deepEqual(errors, [], what + ": no page errors");
      await page.close();
    }
    // the round 3 face: read OPEN at 900 with the edge 50 px in (past the one-line summary), reopened at 380 where the title wraps
    {
      const { page, errors } = await openViewer(browser, "pane", 900, 520, { docs: { [REPORT]: WRAP_NOTE } });
      await hookLeaves(page);
      await page.click(CALLOUT + " > summary"); await frames(page, 2);
      await page.evaluate(putFoldAbove, [CALLOUT, 50]); await frames(page, 2);
      const before: FoldRead = await page.evaluate(readFold, CALLOUT);
      assert.equal(before.open, true, "round 3 face: open at the leave"); assert.ok(before.summaryBottom < 0, "round 3 face: the one-line summary is above the edge");
      await reopenAfter(page, async () => { await page.setViewportSize({ width: 380, height: 520 }); await frames(page, 3); });
      const rec = await lastLeave(page);
      assert.deepEqual(rec.folds, [0], "round 3 face: the record names the open fold");
      const after: FoldRead = await page.evaluate(readFold, CALLOUT);
      assert.equal(after.open, true, "round 3 face: the fold the reader had OPEN comes back open at the other width (the record's state, not the depth rule)");
      assert.equal(await page.evaluate(shownPara), "Paragraph 11", "round 3 face: the content is under the edge again");
      assert.deepEqual(errors, [], "round 3 face: no page errors");
      await page.close();
    }
  });
});

test("in a browser, at 900 and 380 px (review round 4): a Raw record left at the file's very top, the front matter's block STARTING under the edge (top +10), reopened under the Rendered preference leaves the front matter shut, as a Rendered leave at the top does (before the fix: the other-view rule read no sign, and the `Front matter` fold came back open on every Rendered reopen after a Raw leave at the top, the state an Edit leaves a reader in); a Raw record inside the front matter's rows (the `tags:` row at the edge, top at most 0) still opens it, and a Raw record with the callout's first row at the edge (top 0) still opens the callout", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const FM = ".fileview-md details.md-frontmatter", CALLOUT = ".fileview-md details.md-callout";
    for (const w of [900, 380]) {
      const what = "pane " + w + "px";
      // the finding: Raw, at the very top
      {
        const { page, errors } = await openViewer(browser, "pane", w, 520, { docs: { [REPORT]: FM_NOTE }, raw: true });
        await hookLeaves(page);
        const rawBefore = await page.evaluate(rawTop);
        assert.ok(rawBefore && rawBefore.text.startsWith("---") && rawBefore.scrollTop === 0, what + " (top): the Raw view stands at the file's top, the `---` row first (" + JSON.stringify(rawBefore) + ")");
        await reopen(page, { rendered: true });
        const rec = await lastLeave(page);
        assert.ok(rec && rec.view === "raw" && rec.start === 0 && rec.top > 0 && rec.atTop === true, what + " (top): the record is the Raw view's at the top with the block's top under the edge (" + JSON.stringify(rec) + ")");
        assert.equal(await page.evaluate(() => !!document.querySelector(".fileview-md > p")), true, what + " (top): the reopen painted the Rendered view");
        assert.deepEqual(await foldsOpen(page), [false, false], what + " (top): the front matter and the callout stay shut (before the fix: [true, false], the front matter's lines unfolded over a block the reader's edge never reached)");
        const fm: FoldRead = await page.evaluate(readFold, FM);
        assert.ok(fm.bottom - fm.top < 60, what + " (top): the front matter's box is its summary alone (" + (fm.bottom - fm.top) + " px)");
        assert.deepEqual(errors, [], what + " (top): no page errors");
        await page.close();
      }
      // the control the rule keeps: Raw with the `tags:` row (the front matter's third row) at the edge, the edge inside the block's rows
      {
        const { page, errors } = await openViewer(browser, "pane", w, 520, { docs: { [REPORT]: FM_NOTE }, raw: true });
        await hookLeaves(page);
        await page.evaluate(putRowAbove, ["tags:", 0]); await frames(page, 2);
        await reopen(page, { rendered: true });
        const rec = await lastLeave(page);
        assert.ok(rec && rec.view === "raw" && rec.start === 0 && rec.top <= 0, what + " (inside): the record's block is the front matter with the edge inside its rows (" + JSON.stringify(rec) + ")");
        assert.equal((await foldsOpen(page))[0], true, what + " (inside): a Raw record inside the fold's rows opens it (the round 3 rule)");
        assert.deepEqual(errors, [], what + " (inside): no page errors");
        await page.close();
      }
      // the boundary the plan records: the callout's first row exactly at the edge (top 0) opens the callout
      {
        const { page, errors } = await openViewer(browser, "pane", w, 520, { docs: { [REPORT]: CALLOUT_NOTE }, raw: true });
        await hookLeaves(page);
        await page.evaluate(putRowAbove, ["> [!note]-", 0]); await frames(page, 2);
        await reopen(page, { rendered: true });
        const rec = await lastLeave(page);
        assert.ok(rec && rec.view === "raw" && Math.abs(rec.top) < 0.5, what + " (first row): the record's top is 0 (" + JSON.stringify(rec) + ")");
        const c: FoldRead = await page.evaluate(readFold, CALLOUT);
        assert.equal(c.open, true, what + " (first row): the callout opens for a Raw record whose first row was at the edge");
        assert.deepEqual(errors, [], what + " (first row): no page errors");
        await page.close();
      }
    }
  });
});

test("in a browser, at 900 and 380 px (review round 4): a record's folds met by a RAW first paint are held for the open's first Rendered paint: the reader opens the author's <details>, reads Paragraph 25 twenty px in, clicks Edit (the Raw preference saved), closes from the editor, reopens (Raw paints, Paragraph 25's row at the edge) and clicks Rendered: the fold is open, Paragraph 25 shown and the scrollTop back within a pixel (before the fix: every fold as authored, the summary `Closed one` at the edge over the hidden passage, the record's folds [0] lost); the same without Edit when the preference changed to Raw between the leave and the reopen; and a Rendered reopen of the same leave restores it exactly", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const DET = ".fileview-md details";
    for (const w of [900, 380]) for (const via of ["edit", "preference"] as const) {
      const what = "pane " + w + "px, " + via;
      const { page, errors } = await openViewer(browser, "pane", w, 520, { docs: { [REPORT]: DETAILS_NOTE } });
      await hookLeaves(page);
      await page.click(DET + " > summary"); await frames(page, 2);
      await page.evaluate(putAbove, ["Paragraph 25", 20]); await frames(page, 2);
      const before: FoldRead = await page.evaluate(readFold, DET);
      assert.equal(before.open, true, what + ": the fold is open at the leave");
      assert.equal(await page.evaluate(paraShown, "Paragraph 25"), true, what + ": Paragraph 25 shows");
      if (via === "edit") {
        await page.evaluate(() => { const b = Array.from(document.querySelectorAll(".fileview-acts button")).find((x) => x.textContent === "Edit" || x.getAttribute("aria-label") === "Edit") as HTMLElement; b.click(); });
        await page.waitForFunction(() => !!document.querySelector(".fileview-body textarea"), null, { timeout: 5000 });
        assert.equal(await page.evaluate(() => localStorage.getItem("romp:fileviewFmt")), JSON.stringify({ md: "raw" }), what + ": Edit saved the Raw preference");
      }
      // the leave (a clean buffer closes without an ask), the preference Raw, the reopen's first paint Raw
      const p0: number = await page.evaluate(() => (window as any).__paints);
      await page.evaluate(() => { (window as any).FV.closeFileView(); });
      if (via === "preference") await page.evaluate(() => { localStorage.setItem("romp:fileviewFmt", JSON.stringify({ md: "raw" })); });
      const rec = await lastLeave(page);
      assert.ok(rec && rec.view === "rendered" && Array.isArray(rec.folds) && rec.folds[0] === 0 && rec.top < 0, what + ": the leave's record is the Rendered read with the fold open (" + JSON.stringify(rec) + ")");
      await page.evaluate(([p, sid]: [string, string]) => { (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID]);
      await paintsReach(page, p0 + 1); await frames(page, 3);
      const raw = await page.evaluate(rawTop);
      assert.ok(raw && raw.text.startsWith("Paragraph 25"), what + ": the Raw first paint seats the block's first row at the edge (" + JSON.stringify(raw) + ")");
      // the toggle: the held folds go back before the seat
      await clickBar(page, "Rendered");
      const after: FoldRead = await page.evaluate(readFold, DET);
      assert.equal(after.open, true, what + ": the fold the reader had open is open after the Rendered toggle (before the fix: shut, painted as authored, with `Closed one` at the edge)");
      assert.equal(await page.evaluate(paraShown, "Paragraph 25"), true, what + ": Paragraph 25 is shown again (before: hidden under the shut summary)");
      assert.equal(after.scrollHeight, before.scrollHeight, what + ": the open layout's height");
      near(after.scrollTop, before.scrollTop, what + ": the scrollTop is back (the Raw row's place seats the block at the edge in the other view, the depth staying behind: Paragraph 25's top at the edge, 20 px from the leave's)", 21);
      assert.deepEqual(errors, [], what + ": no page errors");
      await page.close();
    }
    // the control: the same Edit leave with the preference put back to Rendered before the reopen restores the fold exactly
    {
      const { page, errors } = await openViewer(browser, "pane", 900, 520, { docs: { [REPORT]: DETAILS_NOTE } });
      await page.click(DET + " > summary"); await frames(page, 2);
      await page.evaluate(putAbove, ["Paragraph 25", 20]); await frames(page, 2);
      const before: FoldRead = await page.evaluate(readFold, DET);
      await page.evaluate(() => { const b = Array.from(document.querySelectorAll(".fileview-acts button")).find((x) => x.textContent === "Edit" || x.getAttribute("aria-label") === "Edit") as HTMLElement; b.click(); });
      await page.waitForFunction(() => !!document.querySelector(".fileview-body textarea"), null, { timeout: 5000 });
      await reopen(page, { rendered: true });
      const after: FoldRead = await page.evaluate(readFold, DET);
      assert.equal(after.open, true, "control: a Rendered first paint restores the fold"); near(after.scrollTop, before.scrollTop, "control: the scrollTop is back");
      assert.deepEqual(errors, [], "control: no page errors");
      await page.close();
    }
  });
});

test("in a browser, at 900 px (review round 4): a reopen whose first text paint happens while the viewer has no box (the pane's document display:none while the fetch was in flight, a phone's tab swap) keeps the remembered place pending, and the width hook's repaint at the show seats it: Paragraph 40 back at the same edge with the scrollTop within a pixel (before the fix: the record spent under the zero layout, its numeric write a no-op on a zero-height scroller, and the note stood at its top once the pane showed); the control with the viewer visible throughout lands the same", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const hidden of [false, true]) {
      const what = hidden ? "hidden at the paint" : "visible throughout";
      const { page, errors } = await openViewer(browser, "pane", 900, 520, { docs: { [REPORT]: LONG } });
      await page.evaluate(() => { const st = document.createElement("style"); st.textContent = "body.fv-pane-hidden #romp-fileview { display: none !important; }"; document.head.appendChild(st); });
      await page.evaluate(putAbove, ["Paragraph 40", 30]); await frames(page, 2);
      const before = await topBlock(page);
      assert.ok(before && before.text.startsWith("Paragraph 40") && before.top < -29 && before.top > -31, what + ": Paragraph 40 read 30 px in (" + JSON.stringify(before) + ")");
      const p0: number = await page.evaluate(() => (window as any).__paints);
      await page.evaluate(() => { (window as any).FV.closeFileView(); });
      if (hidden) await page.evaluate(() => { document.body.classList.add("fv-pane-hidden"); });
      await page.evaluate(([p, sid]: [string, string]) => { (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID]);
      await paintsReach(page, p0 + 1); await frames(page, 3);
      if (hidden) {
        const boxless = await page.evaluate(() => { const b = document.querySelector(".fileview-body") as HTMLElement; return { rects: b.getClientRects().length, clientHeight: b.clientHeight, scrollTop: b.scrollTop, painted: !!document.querySelector(".fileview-md > p") }; });
        assert.deepEqual(boxless, { rects: 0, clientHeight: 0, scrollTop: 0, painted: true }, what + ": the text painted under a body with no box");
        const p1: number = await page.evaluate(() => (window as any).__paints);
        await page.evaluate(() => { document.body.classList.remove("fv-pane-hidden"); });
        await paintsReach(page, p1 + 1);   // the width hook's repaint at the show (the ResizeObserver's report, one reflow paint)
        await frames(page, 3);
      }
      const after = await topBlock(page);
      assert.ok(after && after.text.startsWith("Paragraph 40"), what + ": Paragraph 40 is the top block again (read " + JSON.stringify(after) + "; before the fix, hidden: `Report` at scrollTop 0)");
      near(after!.scrollTop, before!.scrollTop, what + ": the scrollTop is back");
      near(after!.top, before!.top, what + ": the same edge");
      assert.deepEqual(errors, [], what + ": no page errors");
      await page.close();
    }
  });
});

// ── review round 5: the other-view rule reads the record's atTop flag; a Raw leave carries held folds on ────────────────────
/** The shut callout after an HTML comment of `rows` lines, a block with no element of its own whose Raw rows read as the block after
 *  them (reader-place.ts readPlace: nextShown), then paragraphs 41 to 70. */
const COMMENT_ROWS_NOTE = (rows: number): string => "# Report\n\n" + paras(1, 10) + "\n\n<!--\n" + Array.from({ length: rows - 2 }, (_, i) => "a note to self, line " + (i + 1)).join("\n") + "\n-->\n\n" + CALLOUT_BLOCK + "\n\n" + paras(41, 70) + "\n";

test("in a browser, at 900 and 380 px (review round 5): a Raw record read with the blank row before a SHUT callout at the edge and the callout's first row 4 and 12 px under it (the record's block is the callout, its top under the edge, the body not at the file's top) reopened under the Rendered preference opens the callout with Paragraph 11 shown, every Raw row having shown (before the fix: round 4's sign test, the block's top at most 0, left it shut where round 3 had opened it); the rule's bound: a row read as a block that starts below the body's height, a forty-row comment before the callout with its first row at the edge, leaves the callout shut (a guard: shut before the fix too), where a five-row comment opens it (red before)", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const CALLOUT = ".fileview-md details.md-callout";
    for (const w of [900, 380]) {
      const what = "pane " + w + "px";
      // the finding: the blank row before the callout at the edge (inside that row's height at every font: 4 and 12 px under)
      for (const under of [4, 12]) {
        const { page, errors } = await openViewer(browser, "pane", w, 520, { docs: { [REPORT]: CALLOUT_NOTE }, raw: true });
        await hookLeaves(page);
        await page.evaluate(putRowAbove, ["> [!note]-", -under]); await frames(page, 2);
        const raw = await page.evaluate(rawTop);
        assert.ok(raw && raw.text === "" && raw.scrollTop > 0, what + " (" + under + " under): the blank row before the callout is at the edge, the body scrolled (" + JSON.stringify(raw) + ")");
        await reopen(page, { rendered: true });
        const rec = await lastLeave(page);
        assert.ok(rec && rec.view === "raw" && rec.start === CALLOUT_NOTE.indexOf("> [!note]-") && rec.top > 0 && rec.atTop === false, what + " (" + under + " under): the record's block is the callout with its top under the edge, the body not at the file's top (" + JSON.stringify(rec) + ")");
        assert.equal(await page.evaluate(() => !!document.querySelector(".fileview-md > p")), true, what + " (" + under + " under): the reopen painted the Rendered view");
        const c: FoldRead = await page.evaluate(readFold, CALLOUT);
        assert.equal(c.open, true, what + " (" + under + " under): the callout opens for a Raw record whose rows the reader had in view under the blank row (before the fix: shut, the sign test reading the block as under the edge)");
        assert.equal(await page.evaluate(paraShown, "Paragraph 11"), true, what + " (" + under + " under): the callout's first paragraph is shown");
        assert.deepEqual(errors, [], what + " (" + under + " under): no page errors");
        await page.close();
      }
      // the bound: the comment's first row at the edge reads as the callout after it, whose top is the comment's rows down
      for (const [rows, opens] of [[40, false], [5, true]] as Array<[number, boolean]>) {
        const note = COMMENT_ROWS_NOTE(rows);
        const { page, errors } = await openViewer(browser, "pane", w, 520, { docs: { [REPORT]: note }, raw: true });
        await hookLeaves(page);
        await page.evaluate(putRowAbove, ["<!--", 0]); await frames(page, 2);
        const clientHeight: number = await page.evaluate(() => (document.querySelector(".fileview-body") as HTMLElement).clientHeight);
        await reopen(page, { rendered: true });
        const rec = await lastLeave(page);
        assert.ok(rec && rec.view === "raw" && rec.start === note.indexOf("> [!note]-") && rec.top > 0, what + " (" + rows + "-row comment): the comment's rows read as the callout after them, the block starting under the edge (" + JSON.stringify(rec) + ")");
        assert.equal(rec.top >= clientHeight, !opens, what + " (" + rows + "-row comment): the block starts " + (opens ? "inside" : "below") + " the body's height (top " + rec.top + ", clientHeight " + clientHeight + ")");
        const c: FoldRead = await page.evaluate(readFold, CALLOUT);
        assert.equal(c.open, opens, what + " (" + rows + "-row comment): the callout " + (opens ? "opens: its rows were within the view" : "stays shut: a block under the view's bottom names rows the reader never saw"));
        assert.deepEqual(errors, [], what + " (" + rows + "-row comment): no page errors");
        await page.close();
      }
    }
  });
});

test("in a browser, at 900 px (review round 5): a record's folds held past a Raw first paint (round 4's pendingFolds) are carried on by a leave from that Raw view: the reader opens the author's <details>, reads Paragraph 25, clicks Edit and closes from the editor (the record Rendered with folds [0], the Raw preference saved), the reopen paints Raw and the reader reads on to Paragraph 60's row and closes; that Raw record carries folds [0] (before the fix: no fold state, the held folds dying with the open), so the Rendered reopen puts the fold back open with Paragraph 60 at the edge", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const DET = ".fileview-md details";
    const { page, errors } = await openViewer(browser, "pane", 900, 520, { docs: { [REPORT]: DETAILS_NOTE } });
    await hookLeaves(page);
    await page.click(DET + " > summary"); await frames(page, 2);
    await page.evaluate(putAbove, ["Paragraph 25", 20]); await frames(page, 2);
    await page.evaluate(() => { const b = Array.from(document.querySelectorAll(".fileview-acts button")).find((x) => x.textContent === "Edit" || x.getAttribute("aria-label") === "Edit") as HTMLElement; b.click(); });
    await page.waitForFunction(() => !!document.querySelector(".fileview-body textarea"), null, { timeout: 5000 });
    let p0: number = await page.evaluate(() => (window as any).__paints);
    await page.evaluate(() => { (window as any).FV.closeFileView(); });
    const rec1 = await lastLeave(page);
    assert.ok(rec1 && rec1.view === "rendered" && Array.isArray(rec1.folds) && rec1.folds.length === 1 && rec1.folds[0] === 0, "the close from the editor writes the Rendered read with the fold open (" + JSON.stringify(rec1) + ")");
    assert.equal(await page.evaluate(() => localStorage.getItem("romp:fileviewFmt")), JSON.stringify({ md: "raw" }), "Edit saved the Raw preference");
    // the reopen paints Raw: the folds are held for a Rendered paint that never comes; the reader reads on to Paragraph 60's row
    await page.evaluate(([p, sid]: [string, string]) => { (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID]);
    await paintsReach(page, p0 + 1); await frames(page, 3);
    const raw = await page.evaluate(rawTop);
    assert.ok(raw && raw.text.startsWith("Paragraph 25"), "the Raw first paint seats the block's first row at the edge (" + JSON.stringify(raw) + ")");
    await page.evaluate(putRowAbove, ["Paragraph 60", 0]); await frames(page, 2);
    await page.evaluate(() => { (window as any).FV.closeFileView(); });
    const rec2 = await lastLeave(page);
    assert.ok(rec2 && rec2.view === "raw" && rec2.start === DETAILS_NOTE.indexOf("Paragraph 60:"), "the Raw leave's record names Paragraph 60's block (" + JSON.stringify(rec2) + ")");
    assert.deepEqual(rec2.folds, [0], "the Raw leave carries the folds the Raw paint held for a Rendered paint that never came (before the fix: undefined)");
    // the Rendered reopen: the record's folds go back before the seat
    p0 = await page.evaluate(() => (window as any).__paints);
    await page.evaluate(() => { localStorage.setItem("romp:fileviewFmt", JSON.stringify({ md: "rendered" })); });
    await page.evaluate(([p, sid]: [string, string]) => { (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID]);
    await paintsReach(page, p0 + 1); await frames(page, 3);
    const after: FoldRead = await page.evaluate(readFold, DET);
    assert.equal(after.open, true, "the fold the reader had open is open on the Rendered reopen (before the fix: shut, painted as authored)");
    assert.equal(await page.evaluate(paraShown, "Paragraph 25"), true, "Paragraph 25 is shown inside it");
    assert.equal(after.edgeText, "Paragraph 60", "Paragraph 60, the Raw leave's block, at the edge");
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});

// ── review round 6: the other-view rule runs over a fold the carried state put back shut when that fold is the Raw record's block ──
test("in a browser, at 900 px (review round 6): a record's folds carried on by a Raw leave (round 5's heldFolds) say the fold is SHUT when the Raw read's block IS that fold: the reader reads the note with the callout shut as authored, clicks Edit and closes from the editor (the record Rendered with folds [], the Raw preference saved), the Raw reopen holds that state, the reader reads into the callout's rows and closes (the Raw record's block is the callout, folds [] carried on), and the Rendered reopen opens the callout with the passage shown, the Raw place being newer evidence than the carried state (before the fix: restoreFolds put the callout back shut and the `!restored` gate skipped the other-view rule, so the shut summary stood at the edge over the passage the rows had shown); the same for the front matter, its `tags:` row at the edge", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const CALLOUT = ".fileview-md details.md-callout", FM = ".fileview-md details.md-frontmatter";
    for (const [what, note, row, sel, passage, blockStart] of [
      ["the callout", CALLOUT_NOTE, "> Paragraph 25", CALLOUT, "Paragraph 25", CALLOUT_NOTE.indexOf("> [!note]-")],
      ["the front matter", FM_NOTE, "tags:", FM, null, 0],
    ] as Array<[string, string, string, string, string | null, number]>) {
      const { page, errors } = await openViewer(browser, "pane", 900, 520, { docs: { [REPORT]: note } });
      await hookLeaves(page);
      await page.evaluate(putAbove, ["Paragraph 5", 20]); await frames(page, 2);
      const before: FoldRead = await page.evaluate(readFold, sel);
      assert.equal(before.open, false, what + ": shut as authored at the Rendered read");
      await page.evaluate(() => { const b = Array.from(document.querySelectorAll(".fileview-acts button")).find((x) => x.textContent === "Edit" || x.getAttribute("aria-label") === "Edit") as HTMLElement; b.click(); });
      await page.waitForFunction(() => !!document.querySelector(".fileview-body textarea"), null, { timeout: 5000 });
      let p0: number = await page.evaluate(() => (window as any).__paints);
      await page.evaluate(() => { (window as any).FV.closeFileView(); });
      const rec1 = await lastLeave(page);
      assert.ok(rec1 && rec1.view === "rendered" && Array.isArray(rec1.folds) && rec1.folds.length === 0, what + ": the close from the editor writes the Rendered read with every fold shut, folds [] (" + JSON.stringify(rec1) + ")");
      assert.equal(await page.evaluate(() => localStorage.getItem("romp:fileviewFmt")), JSON.stringify({ md: "raw" }), what + ": Edit saved the Raw preference");
      // the Raw reopen holds the folds for a Rendered paint that never comes; the reader reads into the fold's own rows
      await page.evaluate(([p, sid]: [string, string]) => { (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID]);
      await paintsReach(page, p0 + 1); await frames(page, 3);
      assert.equal(await page.evaluate(() => !!document.querySelector("code.hljs .fv-cl")), true, what + ": the reopen painted Raw");
      await page.evaluate(putRowAbove, [row, 0]); await frames(page, 2);
      const raw = await page.evaluate(rawTop);
      assert.ok(raw && raw.text.startsWith(row) && raw.scrollTop > 0, what + ": the fold's own row at the edge, the body scrolled (" + JSON.stringify(raw) + ")");
      await page.evaluate(() => { (window as any).FV.closeFileView(); });
      const rec2 = await lastLeave(page);
      assert.ok(rec2 && rec2.view === "raw" && rec2.start === blockStart && rec2.atTop === false, what + ": the Raw record's block is the fold, the body not at the file's top (" + JSON.stringify(rec2) + ")");
      assert.deepEqual(rec2.folds, [], what + ": the Raw leave carries the held state on (round 5)");
      // the Rendered reopen: the carried state puts every fold back shut, and the other-view rule opens the record's own block
      p0 = await page.evaluate(() => (window as any).__paints);
      await page.evaluate(() => { localStorage.setItem("romp:fileviewFmt", JSON.stringify({ md: "rendered" })); });
      await page.evaluate(([p, sid]: [string, string]) => { (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID]);
      await paintsReach(page, p0 + 1); await frames(page, 3);
      const after: FoldRead = await page.evaluate(readFold, sel);
      assert.equal(after.open, true, what + ": the fold that is the Raw record's block opens on the Rendered reopen, its rows having shown (before the fix: shut, its summary at the edge over the passage)");
      if (passage) assert.equal(await page.evaluate(paraShown, passage), true, what + ": " + passage + " is shown inside it");
      else assert.equal(await page.evaluate((s: string) => { const pre = document.querySelector(s + " pre") as HTMLElement | null; return !!pre && pre.checkVisibility(); }, sel), true, what + ": its text is shown");
      assert.deepEqual(errors, [], what + ": no page errors");
      await page.close();
    }
  });
});
