// The margin layout's pure half (plans/file-review.md, "The margin-layout follow-on (2026-09-07)"): where each
// card of the Comments panel sits in the cards track when the panel stands beside the body. The panel measures
// (file-comments.ts, placeCards: each card's height, and the top of its mark in the body's content); this decides.
//
// The rule is a document editor's margin. A card with a mark wants the mark's top (`desired`); cards are laid in
// order of desired top (ties by the list's order) and each takes the larger of its desired top and the previous
// card's bottom plus the gap — so cards never overlap, and a card only ever moves DOWN from its mark, never up
// over an earlier passage's card. Cards with no mark (`desired` null: a whole-file comment, a detached anchor, a
// change the view does not paint, a region whose figure has not loaded) form the loose group at the top of the
// track, in the list's order, and the placed cards begin below it. `pushed` is how far a card sits below its mark
// (0 when level), for the sheet's leader line.
export type LayoutItem = { key: string; desired: number | null; height: number };
export type PlacedItem = { key: string; top: number; height: number; desired: number | null; pushed: number };
export type Layout = { placed: PlacedItem[]; bottom: number };

/** The gap between cards, the sheet's `.fc-cards { gap: 8px }` (pinned by card-layout.test.ts). */
export const CARD_GAP = 8;

/** Place `items` in a track: the loose ones first from `gap` down, then the marked ones by desired top with the
 *  push-down rule. Returns the placements in placement order and the bottom edge of the last card (the track's
 *  content must reach at least that far). */
export function layoutCards(items: LayoutItem[], gap: number = CARD_GAP): Layout {
  const placed: PlacedItem[] = [];
  let floor = gap;                                   // where the next card may begin at the earliest
  let bottom = 0;
  const put = (it: LayoutItem, top: number): void => {
    placed.push({ key: it.key, top, height: it.height, desired: it.desired, pushed: it.desired === null ? 0 : top - it.desired });
    floor = top + it.height + gap;
    bottom = Math.max(bottom, top + it.height);
  };
  for (const it of items) if (it.desired === null) put(it, floor);
  const marked = items.map((it, i) => ({ it, i })).filter((x) => x.it.desired !== null)
    .sort((a, b) => (a.it.desired as number) - (b.it.desired as number) || a.i - b.i);
  for (const { it } of marked) put(it, Math.max(it.desired as number, floor));
  return { placed, bottom };
}
