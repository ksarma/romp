// drawnBox under each `object-fit` (plans/file-review.md, Slice 3; contract E6). The overlay is placed
// over the box the picture is DRAWN in, and that box is not always the contain-letterbox: a figure in
// rendered markdown has no `object-fit` rule, so a `width`/`height` pair that disagrees with its aspect
// (raw HTML the sanitizer keeps, or a correct pair squeezed by `max-width: 100%` in a narrow column)
// stretches the picture over the whole element. A letterbox computed for THAT figure put the overlay over
// the middle of the element and left the picture's edges undrawable — the fractions stored from a drag and
// the rectangles painted from them were both wrong. drawnBox now takes the element's computed value, and
// REQUIRES it: an optional `fit` defaulting to `contain` would hand the same bug to the next caller that
// omitted it, so the compiler refuses the omission and the runtime treats a missing word as `fill`.
// Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { drawnBox, overlayOffsets, regionFromPoints, cropRect, type Box } from "./region-geometry";

// the 3:2 element of region-geometry.test.ts, and the square picture that does not share its aspect
const RECT: Box = { left: 100, top: 200, width: 300, height: 200 };
const SQUARE = { width: 100, height: 100 };

test("fill: a stretched figure is drawn over its whole element, so the box is the rect and the overlay's inset: 0 holds", () => {
  // the README figure: <img src="fig.png" width="400" height="100"> for a 400×400 picture
  const el: Box = { left: 0, top: 0, width: 400, height: 100 };
  const fig = { width: 400, height: 400 };
  assert.deepEqual(drawnBox(el, fig, "fill"), el);
  assert.equal(overlayOffsets(el, drawnBox(el, fig, "fill")), null, "no inline offsets: the sheet covers the element");
  assert.deepEqual(drawnBox(el, fig, "contain"), { left: 150, top: 0, width: 100, height: 100 }, "the letterbox this figure never had");
  // the drag over the visible left quarter stores the left quarter, and the crop it names is the picture's left quarter
  const box = drawnBox(el, fig, "fill");
  assert.deepEqual(regionFromPoints(box, { x: 0, y: 0 }, { x: 100, y: 100 }), { x: 0, y: 0, w: 0.25, h: 1 });
  assert.deepEqual(regionFromPoints(box, { x: 300, y: 0 }, { x: 400, y: 100 }), { x: 0.75, y: 0, w: 0.25, h: 1 });
  assert.deepEqual(cropRect({ x: 0, y: 0, w: 0.25, h: 1 }, fig), { sx: 0, sy: 0, sw: 100, sh: 400 });
  assert.deepEqual(regionFromPoints(box, { x: 0, y: 0 }, { x: 400, y: 100 }), { x: 0, y: 0, w: 1, h: 1 }, "the whole picture is the whole element");
});

test("fill: a figure with the right width and height, squeezed by max-width in a narrow column, is stretched too", () => {
  // an 800×400 figure with width="800" height="400" in a 500px column: the width caps, the height attribute holds
  const el: Box = { left: 0, top: 0, width: 500, height: 400 };
  const fig = { width: 800, height: 400 };
  assert.deepEqual(drawnBox(el, fig, "fill"), el);
  assert.deepEqual(drawnBox(el, fig, "contain"), { left: 0, top: 75, width: 500, height: 250 }, "what the letterbox would have claimed");
});

test("contain: the letterbox, only when the caller measured it — fit is required, and never assumed to be the media body's rule", () => {
  const letterbox = { left: 150, top: 200, width: 200, height: 200 };
  assert.deepEqual(drawnBox(RECT, SQUARE, "contain"), letterbox);
  assert.deepEqual(drawnBox(RECT, { width: 600, height: 400 }, "contain"), RECT, "same aspect: the letterbox is the element");
  // `npm run typecheck` verifies this directive: were `fit` optional again, the line below would compile and the
  // unused @ts-expect-error would fail the build — the compiler is what refuses a caller that assumes a stylesheet
  // @ts-expect-error drawnBox's fit is required: a caller measures the element's computed object-fit
  const omitted = drawnBox(RECT, SQUARE);
  assert.deepEqual(omitted, RECT, "a JavaScript caller that reaches the function with no fit gets fill, the CSS initial value — not a letterbox");
  assert.deepEqual(drawnBox(RECT, SQUARE, undefined as unknown as string), RECT, "the same word, spelled out");
});

test("cover and none can overflow the element; scale-down is none for a picture that fits and contain otherwise", () => {
  // cover: the square scaled to the element's width (×3), centered: 100px above and below the element
  assert.deepEqual(drawnBox(RECT, SQUARE, "cover"), { left: 100, top: 150, width: 300, height: 300 });
  // none: natural pixels, centered — a large picture overflows, a small one sits in the middle
  assert.deepEqual(drawnBox(RECT, { width: 600, height: 400 }, "none"), { left: -50, top: 100, width: 600, height: 400 });
  assert.deepEqual(drawnBox(RECT, { width: 100, height: 50 }, "none"), { left: 200, top: 275, width: 100, height: 50 });
  assert.deepEqual(drawnBox(RECT, { width: 100, height: 50 }, "scale-down"), drawnBox(RECT, { width: 100, height: 50 }, "none"));
  assert.deepEqual(drawnBox(RECT, { width: 600, height: 400 }, "scale-down"), drawnBox(RECT, { width: 600, height: 400 }, "contain"));
  assert.deepEqual(drawnBox(RECT, SQUARE, "scale-down"), drawnBox(RECT, SQUARE, "none"), "the square fits: drawn at its own 100×100, centered");
  assert.deepEqual(drawnBox(RECT, { width: 400, height: 100 }, "scale-down"), drawnBox(RECT, { width: 400, height: 100 }, "contain"), "a strip wider than the element is shrunk");
  // an overflowing box still yields honest offsets for the overlay (negative: the sheet starts above the wrapper)
  assert.deepEqual(overlayOffsets(RECT, drawnBox(RECT, SQUARE, "cover")), { left: 0, top: -50, width: 300, height: 300 });
});

test("a word that is not an object-fit keyword is fill, the initial value; no natural size or an empty element is the rect under any fit", () => {
  assert.deepEqual(drawnBox(RECT, SQUARE, ""), RECT, "a stand-in with no computed style");
  assert.deepEqual(drawnBox(RECT, SQUARE, "inherit"), RECT);
  for (const fit of ["fill", "contain", "cover", "none", "scale-down"]) {
    assert.deepEqual(drawnBox(RECT, null, fit), RECT, fit + ": no natural size");
    assert.deepEqual(drawnBox(RECT, { width: 0, height: 0 }, fit), RECT, fit + ": a zero natural size");
    assert.deepEqual(drawnBox({ left: 0, top: 0, width: 0, height: 0 }, SQUARE, fit), { left: 0, top: 0, width: 0, height: 0 }, fit + ": an empty element");
  }
});
