// The region geometry (plans/file-review.md, Slice 3; contract E6): plain numbers in, plain numbers out,
// so the acceptance criterion "the rectangle re-paints correctly at any viewer width" is checked here as
// arithmetic — fractions of the natural size from client-space points, percentages from fractions, the
// crop in natural pixels, the two-decimal wording, and the staleness rule. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import {
  drawnBox, overlayOffsets, regionFromPoints, enforceMin, roundRegion, regionStyle, cropRect, cropSize, regionDesc, fmt2,
  staleness, dragIsClick, MIN_FRACTION, CLICK_THRESHOLD_PX, type Box, type Region,
} from "./region-geometry";
import { describeComment, regionState, regionTarget, type StoreComment, type Status } from "./file-comments-model";

// a 600×400 picture drawn at half size, 100px in and 200px down the viewport — the figure in the notes-api report
const RECT: Box = { left: 100, top: 200, width: 300, height: 200 };
const NATURAL = { width: 600, height: 400 };

test("drawnBox: the element's rect when the aspects agree or the natural size is unknown; the centered letterbox otherwise", () => {
  assert.deepEqual(drawnBox(RECT, NATURAL), RECT, "same aspect: the picture fills its element");
  assert.deepEqual(drawnBox(RECT, null), RECT, "no natural size (still loading, an SVG without one): the element stands in");
  assert.deepEqual(drawnBox(RECT, { width: 0, height: 0 }), RECT);
  // a square picture in the 3:2 element: object-fit contain draws it 200×200, centered, 50px in from each side
  assert.deepEqual(drawnBox(RECT, { width: 100, height: 100 }), { left: 150, top: 200, width: 200, height: 200 });
  // a wide strip in the same element: 300 wide, 75 tall, 62.5px down from the top
  assert.deepEqual(drawnBox(RECT, { width: 400, height: 100 }), { left: 100, top: 262.5, width: 300, height: 75 });
  assert.deepEqual(drawnBox({ left: 0, top: 0, width: 0, height: 0 }, NATURAL), { left: 0, top: 0, width: 0, height: 0 }, "an empty element draws nothing");
});

test("overlayOffsets: null when the drawn image fills the wrapper (the sheet's inset: 0 holds), pixel offsets when it does not", () => {
  assert.equal(overlayOffsets(RECT, RECT), null);
  assert.equal(overlayOffsets(RECT, { ...RECT, left: 100.3, width: 299.6 }), null, "sub-pixel differences are the browser's rounding, not a letterbox");
  assert.deepEqual(overlayOffsets(RECT, drawnBox(RECT, { width: 100, height: 100 })), { left: 50, top: 0, width: 200, height: 200 });
});

test("regionFromPoints: fractions of the drawn box, either corner first, clamped into the box, four decimals", () => {
  const r = regionFromPoints(RECT, { x: 150, y: 240 }, { x: 250, y: 300 });
  assert.deepEqual(r, { x: 0.1667, y: 0.2, w: 0.3333, h: 0.3 }, "50/300, 40/200, 100/300, 60/200 — rounded to the stored precision");
  assert.deepEqual(regionFromPoints(RECT, { x: 250, y: 300 }, { x: 150, y: 240 }), r, "dragged from the bottom-right corner: the same region");
  assert.deepEqual(regionFromPoints(RECT, { x: 250, y: 240 }, { x: 150, y: 300 }), r, "dragged from the top-right corner: the same region");
  // a drag that leaves the picture is clamped to its edge — the region never reaches outside the image
  assert.deepEqual(regionFromPoints(RECT, { x: 300, y: 300 }, { x: 900, y: 900 }), { x: 0.6667, y: 0.5, w: 0.3333, h: 0.5 });
  assert.deepEqual(regionFromPoints(RECT, { x: 0, y: 0 }, { x: 400, y: 400 }), { x: 0, y: 0, w: 1, h: 1 }, "the whole picture");
  assert.equal(regionFromPoints({ left: 0, top: 0, width: 0, height: 0 }, { x: 1, y: 1 }, { x: 5, y: 5 }), null, "nothing is a fraction of an empty box");
});

test("regionFromPoints: a thin drag is widened to the 1% minimum, inside the picture", () => {
  const thin = regionFromPoints(RECT, { x: 150, y: 240 }, { x: 151, y: 300 })!;   // 1px wide: below 1% of 300
  assert.equal(thin.w, MIN_FRACTION);
  assert.equal(thin.x, 0.1667, "it grows toward the far edge, keeping its start");
  const edge = regionFromPoints(RECT, { x: 399, y: 240 }, { x: 400, y: 300 })!;   // at the right edge: no room to grow
  assert.equal(edge.w, MIN_FRACTION);
  assert.equal(edge.x, 0.99, "so it is shifted back to stay inside");
  const flat = regionFromPoints(RECT, { x: 150, y: 240 }, { x: 250, y: 240 })!;   // zero height
  assert.equal(flat.h, MIN_FRACTION);
  assert.equal(flat.y, 0.2);
  assert.deepEqual(enforceMin({ x: 0.995, y: 0.999, w: 0, h: 0 }), { x: 0.99, y: 0.99, w: 0.01, h: 0.01 });
  assert.deepEqual(enforceMin({ x: -0.5, y: 0.2, w: 2, h: 0.1 }), { x: 0, y: 0.2, w: 1, h: 0.1 }, "clamped into the unit square first");
});

test("roundRegion: four decimals, never past the far edge once rounded", () => {
  assert.deepEqual(roundRegion({ x: 0.12345, y: 0.5, w: 0.87656, h: 0.5 }), { x: 0.1235, y: 0.5, w: 0.8765, h: 0.5 }, "x + w would round to 1.0001: w gives");
  assert.deepEqual(roundRegion({ x: 1 / 3, y: 2 / 3, w: 1 / 3, h: 1 / 3 }), { x: 0.3333, y: 0.6667, w: 0.3333, h: 0.3333 });
});

test("regionStyle: percentages of the overlay with two decimals — the rectangle is right at any width by construction", () => {
  assert.deepEqual(regionStyle({ x: 0.1667, y: 0.2, w: 0.3333, h: 0.3 }), { left: "16.67%", top: "20.00%", width: "33.33%", height: "30.00%" });
  assert.deepEqual(regionStyle({ x: 0, y: 0, w: 1, h: 1 }), { left: "0.00%", top: "0.00%", width: "100.00%", height: "100.00%" });
});

test("cropRect: the source rectangle in natural pixels, whole pixels, never off the picture; null with no natural size", () => {
  assert.deepEqual(cropRect({ x: 0.1667, y: 0.2, w: 0.3333, h: 0.3 }, NATURAL), { sx: 100, sy: 80, sw: 200, sh: 120 });
  assert.deepEqual(cropRect({ x: 0.99, y: 0.99, w: 0.01, h: 0.01 }, NATURAL), { sx: 594, sy: 396, sw: 6, sh: 4 });
  assert.deepEqual(cropRect({ x: 0.999, y: 0.999, w: 0.01, h: 0.01 }, NATURAL), { sx: 599, sy: 399, sw: 1, sh: 1 }, "at least one pixel, inside the last one");
  assert.deepEqual(cropRect({ x: 0, y: 0, w: 0.0001, h: 0.0001 }, NATURAL), { sx: 0, sy: 0, sw: 1, sh: 1 });
  assert.equal(cropRect({ x: 0, y: 0, w: 1, h: 1 }, null), null);
  assert.equal(cropRect({ x: 0, y: 0, w: 1, h: 1 }, { width: 0, height: 0 }), null);
});

test("cropSize: the crop's aspect fitted inside the thumbnail's bounds, grown or shrunk, at least 1×1", () => {
  assert.deepEqual(cropSize({ sw: 200, sh: 120 }, { width: 240, height: 140 }), { width: 233, height: 140 }, "the height binds: 200 × 140/120");
  assert.deepEqual(cropSize({ sw: 600, sh: 100 }, { width: 240, height: 140 }), { width: 240, height: 40 }, "the width binds");
  assert.deepEqual(cropSize({ sw: 6, sh: 4 }, { width: 240, height: 140 }), { width: 210, height: 140 }, "a tiny crop is enlarged so it can be seen");
  assert.deepEqual(cropSize({ sw: 1, sh: 1000 }, { width: 240, height: 140 }), { width: 1, height: 140 });
});

test("regionDesc and fmt2: two decimals always, comma-separated, the page form for a PDF (contract E7)", () => {
  assert.equal(regionDesc({ x: 0.12, y: 0.4, w: 0.35, h: 0.2 }), "the region at 0.12, 0.40, 0.35, 0.20");
  assert.equal(regionDesc({ x: 0, y: 0, w: 1, h: 1 }), "the region at 0.00, 0.00, 1.00, 1.00", "an integer fraction still shows two decimals");
  assert.equal(regionDesc({ x: 0.1667, y: 0.2, w: 0.3333, h: 0.3 }), "the region at 0.17, 0.20, 0.33, 0.30", "the stored four decimals shown as two");
  assert.equal(regionDesc({ x: 0.12, y: 0.4, w: 0.35, h: 0.2 }, 2), "the region at 0.12, 0.40, 0.35, 0.20 of page 2");
  assert.equal(regionDesc({ x: 0.12, y: 0.4, w: 0.35, h: 0.2 }, null), "the region at 0.12, 0.40, 0.35, 0.20");
  assert.equal(fmt2(1), "1.00");
  // the model's desc (the message's parenthetical) is built from the same words: "on " + the phrase
  const whole: StoreComment = { id: "1757145600000-0", author: "you", ts: 1757145600000, body: "Axis label is wrong.", replies: [], resolved: false };
  assert.equal(describeComment({ ...whole, target: { kind: "image", region: { x: 0, y: 0.5, w: 1, h: 0.5 }, hash: "a" } }, []), "on the region at 0.00, 0.50, 1.00, 0.50");
  assert.equal(describeComment({ ...whole, target: { kind: "pdf", region: { x: 0.12, y: 0.4, w: 0.35, h: 0.2 }, page: 3, hash: "a" } }, []), "on the region at 0.12, 0.40, 0.35, 0.20 of page 3");
});

test("staleness: stale only when both hashes are known and differ; unknown for a missing side, never stale (contract E2)", () => {
  assert.equal(staleness("abc", "abc"), "current");
  assert.equal(staleness("abc", "def"), "stale");
  assert.equal(staleness("abc", null), "unknown", "the host could not hash the file (over its cap)");
  assert.equal(staleness("abc", undefined), "unknown", "an older host sends no hash");
  assert.equal(staleness(undefined, "abc"), "unknown", "a comment written without a hash");
  assert.equal(staleness("", "abc"), "unknown");
  assert.equal(staleness(null, null), "unknown");
});

test("regionState: a standalone image compares with the file's hash, an embedded figure with its src's entry", () => {
  const base = { fileHash: "h1", embeddedHashes: { "figure.png": "f1" } } as Pick<Status, "fileHash" | "embeddedHashes">;
  assert.equal(regionState({ kind: "image", region: { x: 0, y: 0, w: 1, h: 1 }, hash: "h1" }, base), "current");
  assert.equal(regionState({ kind: "image", region: { x: 0, y: 0, w: 1, h: 1 }, hash: "h0" }, base), "stale");
  assert.equal(regionState({ kind: "image", region: { x: 0, y: 0, w: 1, h: 1 }, hash: "f1", src: "figure.png" }, base), "current");
  assert.equal(regionState({ kind: "image", region: { x: 0, y: 0, w: 1, h: 1 }, hash: "f0", src: "figure.png" }, base), "stale");
  assert.equal(regionState({ kind: "image", region: { x: 0, y: 0, w: 1, h: 1 }, hash: "f1", src: "other.png" }, base), "unknown", "a figure the status did not hash");
  assert.equal(regionState({ kind: "image", region: { x: 0, y: 0, w: 1, h: 1 }, hash: "f1", src: "figure.png" }, { fileHash: null, embeddedHashes: null }), "unknown");
  assert.equal(regionState({ kind: "image", region: { x: 0, y: 0, w: 1, h: 1 }, hash: "h1" }, { fileHash: null }), "unknown", "null is unknown, not stale");
  assert.equal(regionState(null, base), "unknown");
});

test("regionTarget: the wire shape carries the kind, the fractions and the embed's src — never a hash (the host stamps it, E1)", () => {
  const region: Region = { x: 0.1667, y: 0.2, w: 0.3333, h: 0.3 };
  assert.deepEqual(regionTarget(region, null), { kind: "image", region });
  assert.deepEqual(regionTarget(region, "figure.png"), { kind: "image", region, src: "figure.png" });
  assert.deepEqual(Object.keys(regionTarget(region, "")), ["kind", "region"], "an empty src is no src");
  // a page makes it a PDF region (F4): kind pdf, the 1-based page, and never a src — a PDF is always its own file
  assert.deepEqual(regionTarget(region, null, 2), { kind: "pdf", region, page: 2 });
  assert.deepEqual(regionTarget(region, "deck.pdf", 1), { kind: "pdf", region, page: 1 }, "a src beside a page is dropped");
  assert.deepEqual(regionTarget(region, null, 0), { kind: "image", region }, "page 0 is no page (the host refuses one anyway)");
  assert.deepEqual(regionTarget(region, null, null), { kind: "image", region });
});

test("dragIsClick: a press that moves less than the threshold in both axes is a click, not a region", () => {
  assert.equal(dragIsClick({ x: 10, y: 10 }, { x: 12, y: 13 }), true);
  assert.equal(dragIsClick({ x: 10, y: 10 }, { x: 10 + CLICK_THRESHOLD_PX, y: 10 }), false, "the threshold itself is a drag");
  assert.equal(dragIsClick({ x: 10, y: 10 }, { x: 10, y: 30 }), false);
});
