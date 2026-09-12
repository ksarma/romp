// The reader's place in a shut `<details>` that ENDS the document, in headless Chromium over the REAL module
// (plans/markdown-viewer.md Slice 5, item 1b; reader-place.ts Place.after; the Slice 5 review's round 6). A Raw row inside a
// fold carries the blocks after the fold for the seat to stand on when the Rendered view folds the block shut (round 2), no
// lower than the fold's summary at the edge (round 3). A fold with NOTHING standing after it (the document's last block, or
// followed only by a comment, a wrapper's end or a reference definition, which render nothing) carried no list at all, so the
// seat walked back through the hidden paragraphs to the wrapper's refused block and seated nothing: the numeric scrollTop
// stood over the shorter Rendered view, the summary landed 617 to 636px down in a 600px pane at 380 (off the pane; from a
// hidden row 437) and the way back returned the row 505 to 729px low at both widths (identical on 701728eae, 50b19bfdb and
// main: the round-1 refusal this slice set out to replace). Now the list is carried EMPTY and the seat stands on the fold's
// summary at the edge, the cap's own limit. The pane's end mostly clamps that write (nothing but the summary is shown below
// it), so the summary lands near the pane's bottom and file-view.ts holds the Raw place across the clamp, which makes the
// way back exact: the scene row is where it was. The scenes: the `<summary>` row, the `<details>` row and a hidden paragraph's
// row at the top edge, at 380 and 900px, for a fold ending the document, one followed by a comment alone and one followed by
// a reference definition alone; a fold with paragraphs after it is the control (as before: the seat, clamped by the pane's end at
// 900, holds the Raw place, and the way back is exact). A seat is pinned as
// what the viewer DOES (a setter trap on the body's scrollTop records every script write across the switch) and as where the
// summary lands, since the browser's clamp decides the second.
// Legs await frames and paint counts, never a timer. Skips LOUDLY without a playwright browser, as the other legs do.
// Synthetic values only: an invented report, /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, frames, PARA, REPORT } from "./real-viewer-leg";

const near = (a: number, b: number, what: string, tol = 1.5) => assert.ok(Math.abs(a - b) <= tol, `${what}: ${a} vs ${b}`);
const paras = (a: number, b: number) => Array.from({ length: b - a + 1 }, (_, i) => PARA(a + i)).join("\n\n");
const FOLD = "# Report\n\n" + paras(1, 30) + "\n\n<details>\n<summary>Fold title</summary>\n\n" + paras(31, 45) + "\n\n</details>\n";
const LAST = FOLD;
const LAST_COMMENT = FOLD + "\n<!-- end of file -->\n";
const LAST_REF = FOLD + "\n[ref]: https://example.test/\n";
const MID = FOLD + "\n" + paras(46, 50) + "\n";

const click = async (page: any, label: string) => { await page.locator("#romp-fileview .fileview-btn", { hasText: new RegExp("^" + label + "$") }).click(); await frames(page, 3); };
/** The box of the first element under the body matching `sel` whose text includes `text`, from the body's top edge, with the body's
 *  scroll geometry. */
const box = (page: any, sel: string, text: string) => page.evaluate(([s, t]: [string, string]) => {
  const body = document.querySelector(".fileview-body") as HTMLElement; const br = body.getBoundingClientRect();
  const el = Array.from(body.querySelectorAll(s)).find((e) => (e.textContent || "").includes(t)); if (!el) return null;
  const r = el.getBoundingClientRect();
  return { top: Math.round((r.top - br.top) * 10) / 10, bottom: Math.round((r.bottom - br.top) * 10) / 10, scrollTop: body.scrollTop, atEnd: body.scrollTop >= body.scrollHeight - body.clientHeight - 1, clientHeight: body.clientHeight };
}, [sel, text]);
/** Scroll so the Raw row whose text includes `text` has its top at the body's top edge. */
const rowToEdge = (page: any, text: string) => page.evaluate((t: string) => {
  const body = document.querySelector(".fileview-body")!;
  const row = Array.from(body.querySelectorAll("code.hljs .fv-cl")).find((r) => (r.textContent || "").includes(t))!;
  body.scrollTop += row.getBoundingClientRect().top - body.getBoundingClientRect().top;
}, text);
/** Trap every script write of the body's scrollTop from now on (the viewer's seat is one; the browser's own scrolls and clamps are
 *  not writes), so a switch can be shown to have seated, or not. Installed after the scene's own scroll. */
const trapWrites = (page: any) => page.evaluate(() => {
  const body = document.querySelector(".fileview-body") as HTMLElement;
  const proto = Object.getOwnPropertyDescriptor(Element.prototype, "scrollTop")!;
  (window as any).__writes = [];
  Object.defineProperty(body, "scrollTop", { get() { return proto.get!.call(this); }, set(v) { (window as any).__writes.push(v); proto.set!.call(this, v); }, configurable: true });
});
const writes = (page: any): Promise<number[]> => page.evaluate(() => (window as any).__writes as number[]);
const foldShut = (page: any): Promise<boolean | null> => page.evaluate(() => { const d = document.querySelector(".fileview-md details") as HTMLDetailsElement | null; return d ? !d.open : null; });

test("in a browser, the real module: a shut `<details>` that is the document's last block, or is followed only by a comment or a reference definition: its `<summary>` row, its `<details>` row and a hidden paragraph's row at the top edge of Raw, switched to Rendered, SEAT (a script write of the body's scrollTop) the fold's summary at the edge, which the pane's end clamps to the summary in view near the pane's bottom, at 380 and 900px, and the way back returns the row where it was (the review's round 6: nothing after the fold read as its own place, so the place carried no block to stand on, the seat walked back through the hidden paragraphs to the wrapper's refused block and wrote nothing, the numeric scrollTop stood over the shorter view, the summary 617 to 636px down at 380, off the pane, and the row came back 505 to 729px low; identical on 701728eae and main); a fold with paragraphs after it round-trips from its summary row exactly at 900, as before", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const width of [380, 900]) {
      for (const [name, doc] of [["the fold ending the document", LAST], ["the fold followed by a comment alone", LAST_COMMENT], ["the fold followed by a reference definition alone", LAST_REF]] as const) {
        for (const row of ["<summary>", "<details>", "Paragraph 33:"]) {
          const where = `pane ${width}, ${name}, the ${JSON.stringify(row)} row at the edge`;
          const { page, errors } = await openViewer(browser, "pane", width, 600, { docs: { [REPORT]: doc }, raw: true });
          await rowToEdge(page, row); await frames(page, 2);
          const start = (await box(page, "code.hljs .fv-cl", row))!;
          near(start.top, 0, where + ": the scene starts on the row", 1);
          await trapWrites(page);
          await click(page, "Rendered");
          const w = await writes(page);
          assert.equal(await foldShut(page), true, where + ": the fixture: the fold is shut in Rendered");
          const sum = (await box(page, ".fileview-md summary", "Fold title"))!;
          assert.ok(w.length >= 1, where + `: the switch seated (a script write of scrollTop; round 5: none, the summary at ${sum.top})`);
          // the seat asks for the summary at the edge; with nothing shown below the summary the body's end clamps the write and
          // the summary lands in view near the pane's bottom (either way it is in view: round 5 left it 617 to 636px down at 380)
          assert.ok(sum.top <= 1.5 || sum.atEnd, where + `: the summary is at the edge or the body is at its end (${JSON.stringify(sum)})`);
          assert.ok(sum.top >= -1.5 && sum.bottom <= sum.clientHeight + 0.5, where + `: the summary is in view (round 5: 617 to 636px down in a ${sum.clientHeight}px pane at 380; ${JSON.stringify(sum)})`);
          await click(page, "Raw");
          const back = (await box(page, "code.hljs .fv-cl", row))!;
          near(back.top, start.top, where + ": the way back returns the row where it was (round 5: 505 to 729px low)");
          assert.deepEqual(errors, [], where + ": no script error");
          await page.close();
        }
      }
    }
    {
      const where = "pane 900, the fold with paragraphs after it, the <summary> row at the edge (the control)";
      const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: MID }, raw: true });
      await rowToEdge(page, "<summary>"); await frames(page, 2);
      const start = (await box(page, "code.hljs .fv-cl", "<summary>"))!;
      await trapWrites(page);
      await click(page, "Rendered");
      assert.ok((await writes(page)).length >= 1, where + ": the switch seated");
      const sum = (await box(page, ".fileview-md summary", "Fold title"))!;
      assert.ok(sum.top <= 1.5 || sum.atEnd, where + `: the summary at the edge, or the body at its end (the block after the fold at its carried distance, capped at the summary; five paragraphs after the fold leave the pane's end to clamp the write: ${JSON.stringify(sum)})`);
      await click(page, "Raw");
      near((await box(page, "code.hljs .fv-cl", "<summary>"))!.top, start.top, where + ": the way back returns the row where it was");
      assert.deepEqual(errors, [], where + ": no script error");
      await page.close();
    }
  });
});
