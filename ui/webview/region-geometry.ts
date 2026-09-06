// Region comments on images — the PURE geometry (plans/file-review.md, Slice 3; contract E6).
//
// A region is a rectangle stored in FRACTIONS of the image's natural size (`target.region`, x y w h in
// 0..1, four decimals stored, two shown), so it re-paints correctly at any viewer width by construction:
// the overlay places each rectangle by CSS percentages, and nothing here depends on pixels once the
// fractions exist. This module turns the browser's measurements (an element's client rect, its computed
// `object-fit`, the image's natural size, two pointer points) into those fractions and back, computes the
// crop the card's thumbnail draws, words the region for the composer and the sent message, and rules on
// staleness.
// No DOM: every function is a transform over plain numbers, so region-geometry.test.ts runs it under
// node with no stand-in, and file-comments-regions.ts (the overlay) holds only the wiring.

export type Size = { width: number; height: number };
/** A box in one coordinate space: the client rect of an element, or the drawn image inside it. */
export type Box = { left: number; top: number; width: number; height: number };
export type Point = { x: number; y: number };
/** The stored shape: fractions of the image's natural size. */
export type Region = { x: number; y: number; w: number; h: number };
export type Staleness = "current" | "stale" | "unknown";

/** The smallest region in either dimension: a drag thinner than 1% of the image is widened to it, so a
 *  region can always be seen and clicked. */
export const MIN_FRACTION = 0.01;
/** Fractions are stored to four decimals (0.01% of the image). */
export const FRACTION_DECIMALS = 4;
/** A press that moves less than this many client pixels in both axes is a click, not a drag. */
export const CLICK_THRESHOLD_PX = 4;

const round4 = (v: number): number => Math.round(v * 10 ** FRACTION_DECIMALS) / 10 ** FRACTION_DECIMALS;
const clamp01 = (v: number): number => Math.min(1, Math.max(0, v));

/** The box the image's pixels are DRAWN in, relative to the element's client rect: a fraction of the
 *  natural size is a fraction of THIS box, not of the element, and the two differ whenever the element's
 *  aspect is not the picture's. Which box depends on the element's `object-fit`, so `fit` is its COMPUTED
 *  value (`getComputedStyle(img).objectFit`), and it is REQUIRED: the caller measures, it never assumes a
 *  stylesheet's rule. The two rules romp's sheets give a picture differ, and an assumed one placed the
 *  overlay wrong: the media body's `.fileview-img` has `object-fit: contain`, while `.fileview-md img` sets
 *  none, so a figure in rendered markdown with `width` and `height` that disagree with its aspect (raw HTML
 *  the sanitizer keeps, or a correct pair squeezed by `max-width: 100%` in a narrow column) is drawn under
 *  the initial `fill`, stretched over the whole element — and a letterbox computed for it put the overlay
 *  over pixels that hold no picture. Per keyword: `contain` letterboxes the picture inside the element;
 *  `fill` stretches it over the whole element, so the box IS the rect; `cover` and `none` can overflow the
 *  element (the element clips what falls outside); `scale-down` is `none` for a picture that fits and
 *  `contain` otherwise. A word that is none of the five (a stand-in with no computed style, or a value a
 *  JavaScript caller left out) is `fill`, the CSS initial value. Centered placement (`object-position`'s
 *  initial `50% 50%`) is assumed: no romp stylesheet moves it. Equal to `rect` when the natural size is
 *  unknown (an SVG with no intrinsic size, a picture still loading) or either box is empty. */
export function drawnBox(rect: Box, natural: Size | null | undefined, fit: string): Box {
  if (!natural || !(natural.width > 0) || !(natural.height > 0) || !(rect.width > 0) || !(rect.height > 0)) return { ...rect };
  const scale = drawnScale(rect, natural, fit);
  if (scale === null) return { ...rect };
  const width = natural.width * scale, height = natural.height * scale;
  return { left: rect.left + (rect.width - width) / 2, top: rect.top + (rect.height - height) / 2, width, height };
}

/** The factor the natural size is drawn at under `fit`; null when the picture is stretched to the element
 *  (`fill`, or a word that is not an object-fit keyword — `undefined` included), where no single factor
 *  applies. */
function drawnScale(rect: Box, natural: Size, fit: string): number | null {
  const contain = Math.min(rect.width / natural.width, rect.height / natural.height);
  switch (fit) {
    case "contain": return contain;
    case "cover": return Math.max(rect.width / natural.width, rect.height / natural.height);
    case "none": return 1;
    case "scale-down": return Math.min(1, contain);
    default: return null;
  }
}

/** Where the overlay sits inside its wrapper, in pixels, when the drawn image does not fill the wrapper —
 *  null when the two coincide (within half a pixel), so the sheet's `inset: 0` places it with no inline
 *  style. Both boxes in the same coordinate space (client rects). */
export function overlayOffsets(wrap: Box, drawn: Box): Box | null {
  const left = drawn.left - wrap.left, top = drawn.top - wrap.top;
  const same = (a: number, b: number) => Math.abs(a - b) < 0.5;
  if (same(left, 0) && same(top, 0) && same(drawn.width, wrap.width) && same(drawn.height, wrap.height)) return null;
  return { left, top, width: drawn.width, height: drawn.height };
}

/** A region at least MIN_FRACTION in both dimensions and inside the unit square: a thin one grows toward
 *  the far edge, and one that would then overflow is shifted back. */
export function enforceMin(r: Region): Region {
  let { x, y, w, h } = r;
  x = clamp01(x); y = clamp01(y);
  w = Math.max(0, Math.min(w, 1 - x)); h = Math.max(0, Math.min(h, 1 - y));
  if (w < MIN_FRACTION) { w = MIN_FRACTION; if (x + w > 1) x = 1 - w; }
  if (h < MIN_FRACTION) { h = MIN_FRACTION; if (y + h > 1) y = 1 - h; }
  return { x, y, w, h };
}

/** Rounded to the stored precision, still inside the unit square after rounding. */
export function roundRegion(r: Region): Region {
  const x = round4(r.x), y = round4(r.y);
  let w = round4(r.w), h = round4(r.h);
  if (x + w > 1) w = round4(1 - x);
  if (y + h > 1) h = round4(1 - y);
  return { x, y, w, h };
}

/** Two pointer points (client coordinates) over the drawn box → the region they span, normalized (either
 *  corner first), clamped into the box, at least MIN_FRACTION each way, rounded. Null for an empty box:
 *  nothing can be a fraction of nothing. */
export function regionFromPoints(box: Box, a: Point, b: Point): Region | null {
  if (!(box.width > 0) || !(box.height > 0)) return null;
  const fx = (px: number) => clamp01((px - box.left) / box.width);
  const fy = (py: number) => clamp01((py - box.top) / box.height);
  const x0 = Math.min(fx(a.x), fx(b.x)), x1 = Math.max(fx(a.x), fx(b.x));
  const y0 = Math.min(fy(a.y), fy(b.y)), y1 = Math.max(fy(a.y), fy(b.y));
  return roundRegion(enforceMin({ x: x0, y: y0, w: x1 - x0, h: y1 - y0 }));
}

/** Whether a press that started at `a` and ended at `b` is a click (below the threshold in both axes). */
export function dragIsClick(a: Point, b: Point, threshold = CLICK_THRESHOLD_PX): boolean {
  return Math.abs(b.x - a.x) < threshold && Math.abs(b.y - a.y) < threshold;
}

const pct = (v: number): string => (v * 100).toFixed(2) + "%";

/** The rectangle's inline style: percentages of the overlay, which is the drawn image. */
export function regionStyle(r: Region): { left: string; top: string; width: string; height: string } {
  return { left: pct(r.x), top: pct(r.y), width: pct(r.w), height: pct(r.h) };
}

/** The crop in NATURAL pixels for drawImage's source rectangle: integers, at least one pixel each way,
 *  never past the image's edge. Null when the natural size is unknown. */
export function cropRect(r: Region, natural: Size | null | undefined): { sx: number; sy: number; sw: number; sh: number } | null {
  if (!natural || !(natural.width > 0) || !(natural.height > 0)) return null;
  const W = natural.width, H = natural.height;
  const sx = Math.min(Math.max(0, Math.round(r.x * W)), W - 1);
  const sy = Math.min(Math.max(0, Math.round(r.y * H)), H - 1);
  const sw = Math.max(1, Math.min(Math.round(r.w * W), W - sx));
  const sh = Math.max(1, Math.min(Math.round(r.h * H), H - sy));
  return { sx, sy, sw, sh };
}

/** The thumbnail's size: the crop's aspect fitted inside `max` (grown or shrunk), integers, at least 1×1. */
export function cropSize(crop: { sw: number; sh: number }, max: Size): Size {
  const scale = Math.min(max.width / crop.sw, max.height / crop.sh);
  return { width: Math.max(1, Math.round(crop.sw * scale)), height: Math.max(1, Math.round(crop.sh * scale)) };
}

/** Two decimals, always ("0.40", "1.00"): the form the composer shows and the sent message carries (E7). */
export const fmt2 = (v: number): string => v.toFixed(2);

/** "the region at 0.12, 0.40, 0.35, 0.20", and for a PDF page "… of page 2" — the phrase after "on" in the
 *  message's parenthetical (contract C2/E7) and the card's reference. */
export function regionDesc(r: Region, page?: number | null): string {
  const at = "the region at " + [r.x, r.y, r.w, r.h].map(fmt2).join(", ");
  return page ? at + " of page " + page : at;
}

/** Stale when the region's stored hash and the file's current hash are both known and differ; unknown
 *  when either is missing (a hash the host could not compute — over its cap — or a comment written
 *  without one). Unknown is never shown as stale (E2). */
export function staleness(targetHash: unknown, currentHash: unknown): Staleness {
  const a = typeof targetHash === "string" && targetHash ? targetHash : null;
  const b = typeof currentHash === "string" && currentHash ? currentHash : null;
  if (a === null || b === null) return "unknown";
  return a === b ? "current" : "stale";
}
