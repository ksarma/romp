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
// (0 when level), for the sheet's leader line; negative, how far above it the focus moved it (below).
//
// The focus (the focus follow-on, 2026-09-08): the card the person last acted on — a mark clicked, a card opened, a
// reference followed — is placed at its mark whatever stands above it. Without one, a tall card above a passage
// pushed the passage's card a viewport below its mark, and the click that opened it scrolled the mark to the top
// edge of the body with the card still out of sight. With a focus: the focused card sits exactly at its desired
// top (at the top inset when its mark is under the header, the clamp every card has); the cards above it, by
// desired top, are laid by the push-down rule first and then moved UP, from the focus upward, each only as far as
// the card under it needs (its bottom a gap above that card's top), so a card that never met the focused card
// stays where it was; the loose group joins that chain when the moved cards reach it, moving up by the same
// minimum — to the track's start, and past it only when the cards above the focus do not fit between the start
// and the focus, since the focused card always wins. The cards below the focus follow the push-down rule from its
// bottom, as ever. A card moved above the track's start (a negative top) cannot be scrolled to; the panel's
// centering keeps the focused card and its mark in view, which is the point. A focus with no mark, or one not
// among the items, changes nothing.
export type LayoutItem = { key: string; desired: number | null; height: number };
export type PlacedItem = { key: string; top: number; height: number; desired: number | null; pushed: number };
export type Layout = { placed: PlacedItem[]; bottom: number };

/** The gap between cards, the sheet's `.fc-cards { gap: 8px }` (pinned by card-layout.test.ts). */
export const CARD_GAP = 8;

/** Place `items` in a track: the loose ones first from `gap` down, then the marked ones by desired top with the
 *  push-down rule — or, with `focus` naming a marked item, anchored on that item (the module comment). Returns the
 *  placements in placement order and the bottom edge of the last card (the track's content must reach at least
 *  that far). */
export function layoutCards(items: LayoutItem[], gap: number = CARD_GAP, focus: string | null = null): Layout {
  const placed: PlacedItem[] = [];
  let floor = gap;                                   // where the next card may begin at the earliest
  let bottom = 0;
  const put = (it: LayoutItem, top: number): void => {
    placed.push({ key: it.key, top, height: it.height, desired: it.desired, pushed: it.desired === null ? 0 : top - it.desired });
    floor = top + it.height + gap;
    bottom = Math.max(bottom, top + it.height);
  };
  const marked = items.map((it, i) => ({ it, i })).filter((x) => x.it.desired !== null)
    .sort((a, b) => (a.it.desired as number) - (b.it.desired as number) || a.i - b.i);
  const f = focus === null ? -1 : marked.findIndex((x) => x.it.key === focus);
  if (f < 0) {
    for (const it of items) if (it.desired === null) put(it, floor);
    for (const { it } of marked) put(it, Math.max(it.desired as number, floor));
    return { placed, bottom };
  }
  // the focus: the loose group and the cards above the focus as the push-down rule lays them, then each moved up only
  // as far as the card under it needs, from the focus upward (the module comment)
  const loose = items.filter((it) => it.desired === null);
  const above = marked.slice(0, f).map((x) => x.it), below = marked.slice(f + 1).map((x) => x.it), fit = marked[f].it;
  const tops = new Map<LayoutItem, number>();
  for (const it of loose) { tops.set(it, floor); floor += it.height + gap; }
  for (const it of above) { const top = Math.max(it.desired as number, floor); tops.set(it, top); floor = top + it.height + gap; }
  const focusTop = Math.max(fit.desired as number, gap);
  let ceiling = focusTop - gap;                      // the lowest bottom the card above may have
  for (const it of [...above.slice().reverse(), ...loose.slice().reverse()]) {
    const top = Math.min(tops.get(it) as number, ceiling - it.height);
    tops.set(it, top);
    ceiling = top - gap;
  }
  for (const it of loose) put(it, tops.get(it) as number);
  for (const it of above) put(it, tops.get(it) as number);
  put(fit, focusTop);
  for (const it of below) put(it, Math.max(it.desired as number, floor));
  return { placed, bottom };
}
