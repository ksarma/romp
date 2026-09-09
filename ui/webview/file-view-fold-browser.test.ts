// The Comments aside folds below a pane-wide body in a narrow column, in headless Chromium over the REAL viewer with the
// REAL panel open (plans/markdown-viewer.md, Slice 2: "at 380 and 640 .fileview-main computes flex-direction: column
// with a pane-wide body"). The fold itself has held since fork PR #375 put `container-type: inline-size` on `.fileview`,
// the viewer's card: a container query styles a container's descendants and never the container, and the row it stacks
// had been the only container. The row's own declaration was left in place then, redundant (the aside's rule inside the
// query resolved against the row, whose inline size is the card's), and this slice removes it; the query resolves against
// the card in both surfaces here. This leg replaces the CSS-text match that stood in file-comments.test.ts (the plan's
// acceptance names it): the Files pane and the chat modal at 380 and 640px, the row a column and the body the row's whole
// width with the aside below it, and at 900px the row (the margin layout) as the control. Legs await frames, never a
// timer. Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs do. Synthetic values only:
// an invented report, /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, openPanel } from "./real-viewer-leg";

type Layout = { viewport: number; card: number; main: number; body: number; aside: number; flex: string; asideBelow: boolean; cardContainer: string; mainContainer: string; bodyScrolls: boolean };
function layout(): Layout {
  const w = (s: string) => Math.round(document.querySelector(s)!.getBoundingClientRect().width * 10) / 10;
  const body = document.querySelector(".fileview-body") as HTMLElement, aside = document.querySelector(".fileview-aside")!;
  return {
    viewport: innerWidth, card: w(".fileview"), main: w(".fileview-main"), body: w(".fileview-body"), aside: w(".fileview-aside"),
    flex: getComputedStyle(document.querySelector(".fileview-main")!).flexDirection,
    asideBelow: aside.getBoundingClientRect().top >= body.getBoundingClientRect().bottom - 0.5,
    cardContainer: getComputedStyle(document.querySelector(".fileview")!).containerType,
    mainContainer: getComputedStyle(document.querySelector(".fileview-main")!).containerType,
    bodyScrolls: body.scrollHeight > body.clientHeight,
  };
}

test("in a browser, the real viewer with the real panel open: at 380 and 640px the row stacks and the body is pane-wide with the aside below, in the Files pane and the chat modal; at 900px the two sit side by side; the card is the one query container", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const mode of ["pane", "chat"] as const) for (const width of [380, 640, 900]) {
      const cell = `${mode} ${width}px`;
      const { page, errors } = await openViewer(browser, mode, width, 600);
      await openPanel(page);
      const l: Layout = await page.evaluate(layout);
      assert.equal(l.cardContainer, "inline-size", cell + ": the card declares the container the fold resolves against");
      assert.equal(l.mainContainer, "normal", cell + ": the row declares none (the redundant declaration is gone; before the slice: inline-size)");
      if (width < 700) {
        assert.equal(l.flex, "column", cell + ": the row stacks");
        assert.ok(Math.abs(l.body - l.main) <= 0.5, cell + `: the body is the row's whole width (${l.body} of ${l.main})`);
        assert.ok(Math.abs(l.aside - l.main) <= 0.5, cell + `: so is the aside (${l.aside})`);
        assert.ok(l.asideBelow, cell + ": the aside sits below the body");
      } else {
        assert.equal(l.flex, "row", cell + ": two columns");
        assert.ok(l.body + l.aside <= l.main + 0.5 && l.aside >= 300, cell + `: body ${l.body} beside aside ${l.aside} in ${l.main}`);
        assert.equal(l.asideBelow, false, cell + ": the aside is beside the body, not under it");
      }
      assert.ok(l.bodyScrolls, cell + ": the body still scrolls its hundred paragraphs");
      assert.deepEqual(errors, [], cell + ": no script error");
      await page.close();
    }
  });
});
