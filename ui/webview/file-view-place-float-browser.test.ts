// The reader's place beside a FLOATED figure, in headless Chromium over the REAL module (plans/markdown-viewer.md
// Slice 2; reader-place.ts, topVisibleIndex's pass-over; the Slice 2 review, rounds 1 and 3). An `<img align="left">`
// with short paragraphs wrapping beside it is a box whose successors end above the edge: with the reader at the
// second line beside it, the figure is the first top-level box ending below the body's top edge, and the pass-over
// reads past it to the first paragraph beside it that ends below the edge, the one the reader is reading. Two scenes
// where keeping the figure loses the passage and keeping the paragraph holds it, in the Files pane and the chat modal:
//   - the Rendered to Raw switch: the figure is one Raw row, so kept as the place it puts its own `<img` row at the
//     edge, 126px and six rows from the passage (pane 900: scrollTop 338 for 464); kept as the paragraph, that
//     paragraph's row is the top row. The numeric scrollTop alone, the base behaviour, shows paragraph 4 in the pane
//     and the `<img` row in the chat modal;
//   - a reload that grows the paragraph ABOVE the reader's line beside the figure (a sentence appended to Beside 1):
//     the figure's top edge does not move, so kept as the place the seat writes nothing and the passage drops 40px
//     below the edge (Beside 2 from -5 to 36); kept as the paragraph, Beside 2 comes back to the edge.
// The review's third round found the rule pinned by no test: the node fixtures were answered by the binary search
// alone, and no leg had a floated figure. This leg is red over a tree whose topVisibleIndex stops where the search
// lands (both scenes, both surfaces). The legs' topBlock helper is a first-in-DOM-order scan and reports the figure
// here, so the scenes read the paragraph's own box and the Raw top row instead. Legs await frames and paint counts,
// never a timer. Skips LOUDLY without a playwright browser, as the other legs do. Synthetic values only: an invented
// report, /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, frames, paintsReach, PARA, REPORT, MT2 } from "./real-viewer-leg";

const near = (a: number, b: number, what: string, tol = 1.5) => assert.ok(Math.abs(a - b) <= tol, `${what}: ${a} vs ${b}`);
const paras = (a: number, b: number) => Array.from({ length: b - a + 1 }, (_, i) => PARA(a + i)).join("\n\n");
/** A 300 by 600 picture as a data URL: the figure, floated left with `align`, which the sanitizer keeps. */
const SVG = "data:image/svg+xml;utf8," + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="300" height="600"><rect width="300" height="600" fill="steelblue"/></svg>');
const BESIDE = (i: number, extra = "") => `Beside ${i}: a short line beside the figure.${extra}`;
/** The report: four paragraphs, the floated figure, twelve one-line paragraphs beside it (the first grown by `grow1`), forty more. */
const report = (grow1 = "") => "# Report\n\n" + paras(1, 4) + "\n\n" + `<img src="${SVG}" align="left" width="300" height="600" alt="">` + "\n\n"
  + Array.from({ length: 12 }, (_, i) => BESIDE(i + 1, i === 0 ? grow1 : "")).join("\n\n") + "\n\n" + paras(5, 44) + "\n";
const GROWN = " And a sentence the session appended to the first line beside the figure, long enough to wrap twice in the column beside the picture, and a few words more.";

const click = async (page: any, label: string) => { await page.locator("#romp-fileview .fileview-btn", { hasText: new RegExp("^" + label + "$") }).click(); await frames(page, 3); };
/** The first Raw row ending below the body's top edge: its text, its top and the body's scrollTop. */
const rowAtTop = (page: any) => page.evaluate(() => {
  const body = document.querySelector(".fileview-body")!; const br = body.getBoundingClientRect();
  for (const r of Array.from(body.querySelectorAll("code.hljs .fv-cl"))) { const rr = r.getBoundingClientRect(); if (rr.bottom > br.top + 0.5) return { text: (r.textContent || "").trim().slice(0, 32), top: Math.round((rr.top - br.top) * 10) / 10, scrollTop: body.scrollTop }; }
  return null;
});
/** The box of the first element under the body matching `sel` whose text includes `text`, from the body's top edge. */
const box = (page: any, sel: string, text: string) => page.evaluate(([s, t]: [string, string]) => {
  const body = document.querySelector(".fileview-body")!; const br = body.getBoundingClientRect();
  const el = Array.from(body.querySelectorAll(s)).find((e) => (e.textContent || "").includes(t)); if (!el) return null;
  const r = el.getBoundingClientRect(); return { top: Math.round((r.top - br.top) * 10) / 10, bottom: Math.round((r.bottom - br.top) * 10) / 10, scrollTop: body.scrollTop };
}, [sel, text]);
/** Scroll so that element's top sits `extra` px above the body's top edge. */
const scrollInto = (page: any, sel: string, text: string, extra = 0) => page.evaluate(([s, t, x]: [string, string, number]) => {
  const body = document.querySelector(".fileview-body")!;
  const el = Array.from(body.querySelectorAll(s)).find((e) => (e.textContent || "").includes(t))!;
  body.scrollTop += el.getBoundingClientRect().top - body.getBoundingClientRect().top + x;
}, [sel, text, extra]);
const reload = async (page: any, text: string) => {
  const paints: number = await page.evaluate(() => (window as any).__paints);
  await page.evaluate(([p, t, m]: [string, string, string]) => { (window as any).__docs[p] = t; (window as any).__mtime = m; (window as any).__seam.reload(); }, [REPORT, text, MT2]);
  await paintsReach(page, paints + 1);
  await frames(page, 2);
};
const imagesDone = (page: any) => page.waitForFunction(() => Array.from(document.querySelectorAll(".fileview-md img")).every((i) => (i as HTMLImageElement).complete), null, { timeout: 10000 });

test("in a browser, the real module: beside a floated figure, the paragraph the reader is on is the place, not the figure: the Raw switch lands on its row and the return keeps it, and a reload growing the paragraph above it keeps it at the edge, pane and chat", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const mode of ["pane", "chat"] as const) {
      const { page, errors } = await openViewer(browser, mode, 900, 600, { docs: { [REPORT]: report() } });
      await imagesDone(page);
      // the fixture: the figure floats beside the short paragraphs (its top at Beside 1's, 600px tall, past Beside 6)
      const fig0 = (await box(page, ".fileview-md > img", ""))!, first = (await box(page, ".fileview-md > p", "Beside 1:"))!, sixth = (await box(page, ".fileview-md > p", "Beside 6:"))!;
      near(fig0.top, first.top, mode + ": the figure's top is Beside 1's (the float layout)", 1);
      assert.ok(fig0.bottom - fig0.top >= 590 && fig0.bottom > sixth.bottom, mode + `: the figure reaches below the paragraphs beside it (${fig0.top}..${fig0.bottom}, Beside 6 ends ${sixth.bottom})`);
      // the reader at Beside 2, its top 5px above the edge: Beside 1 has ended above the edge, the figure reaches far below
      await scrollInto(page, ".fileview-md > p", "Beside 2:", 5); await frames(page, 2);
      const b1 = (await box(page, ".fileview-md > p", "Beside 1:"))!, b2 = (await box(page, ".fileview-md > p", "Beside 2:"))!, fig = (await box(page, ".fileview-md > img", ""))!;
      assert.ok(b1.bottom < 0 && b2.top < 0 && b2.bottom > 0 && fig.bottom > 300, mode + `: the scene: Beside 1 above the edge (${b1.bottom}), Beside 2 across it (${b2.top}..${b2.bottom}), the figure reaching below (${fig.bottom})`);
      await click(page, "Raw");
      const row = (await rowAtTop(page))!;
      assert.match(row.text, /^Beside 2:/, mode + `: the Raw top row is Beside 2's (got ${JSON.stringify(row.text)} at scrollTop ${row.scrollTop}: with the figure kept as the place, its own <img row lands here, 126px and six rows from the passage)`);
      near(row.top, b2.top, mode + ": the row where the paragraph's top edge was", 1.5);
      await click(page, "Rendered");
      const b2back = (await box(page, ".fileview-md > p", "Beside 2:"))!;
      near(b2back.top, b2.top, mode + ": back in Rendered, Beside 2 where it was", 1.5);
      // a reload that grows the paragraph above the reader's line, beside the same figure
      await reload(page, report(GROWN));
      const b1g = (await box(page, ".fileview-md > p", "Beside 1:"))!, b2g = (await box(page, ".fileview-md > p", "Beside 2:"))!;
      assert.ok(b1g.bottom - b1g.top > (b1.bottom - b1.top) + 30, mode + `: Beside 1 grew (${b1.bottom - b1.top} to ${b1g.bottom - b1g.top})`);
      near(b2g.top, b2.top, mode + ": Beside 2 stays at the edge after the reload (with the figure kept as the place, its top edge holds and Beside 2 drops 40px below the edge)", 1.5);
      assert.deepEqual(errors, [], mode + ": no script error");
      await page.close();
    }
  });
});
