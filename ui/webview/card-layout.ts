// The margin layout's pure half (plans/file-review.md, "The margin-layout follow-on (2026-09-07)"): where each
// card of the Comments panel sits in the cards track when the panel stands beside the body. The panel measures
// (file-comments.ts, placeCards: each card's height, and the top of its mark in the body's content); this decides.
//
// The rule is a document editor's margin. A card with a mark wants the mark's top (`desired`); cards are laid in
// order of desired top (a tie in the list's order, below) and each takes the larger of its desired top and the previous
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
// stays where it was; the loose group joins that chain when the moved cards reach it, moving up as one by the same
// minimum, as far as the track's start. No card is moved PAST the start: the track cannot scroll to a negative top,
// so a card there could be neither read nor reached — its head is its only control, a loose card has no mark to
// click, and the placement held until some other gesture changed the focus (the focus follow-on's review,
// 2026-09-08: a whole-file comment's card vanished on a click on the first paragraph's highlight). A card the chain
// would move past the start is laid BELOW the focused card instead, by the push-down rule from its end and ahead of
// the cards whose marks are below the focus, a marked card wearing the leader up to its mark as any pushed card
// does; the room above the focus stays for the cards further up the chain, so a small card above a tall one that
// did not fit keeps its place. Of the loose group, the cards at its END go below, in the list's order, until the
// rest fit, so the group's head stays at the start. A card laid below the focus stands above nothing, so the cards
// above are laid again without it — the push-down rule, then the chain — until a pass moves no card past the start: a
// card the tall card had pushed under its mark sits at its mark again, and a card under a spilled whole-file card
// takes the start the group gave up (the verification round, 2026-09-09: laid once, the card between a spilled tall
// card and the focus kept the push the tall card had given it, a leader up a gutter no card stood in). The cards
// below the focus follow the push-down rule from the end of the last card the focus displaced, as ever from a card's
// end. Every card so stands at or below the start, where the track's scroll reaches it. A focus with no mark, or one
// not among the items, changes nothing.
//
// A tie on the desired top (two marks on one line: a change's and a comment's, two changes', two comments', or a
// comment about a deletion laid at the change's own mark, since the deleted text is not in the file and the comment
// has no mark of its own: file-comments.ts, markTop) is broken by the cards' own fields, in the LIST's order, and never
// by the order the items are given in: a change card before a comment card, as the list shows the changes first; two
// change cards by position (`from`) then time (`ts`), the list's order for them, so a later edit to the left of an
// earlier one on the same line reads in text order; two comment cards by time; and the key last, so the order is
// total. So the placement is a function of the cards alone, every pass over the same cards lays them the same, and at
// every pass a tie lays as the list shows it, a comment about a change after the change it is about, but for two cases:
// a tied pair above the focus with room for the comment but not for both, where the change is the one laid below the
// focus and the comment holds the start (the focus rule, below); and two cards the fields do not part, two comment
// cards saved in the same millisecond on one line or two change cards at one position and time, which lay by key, an
// order the list need not share, since it sorts comments by time and changes by position then time, stably
// (file-comments-model.ts, cardModel and changeCards), and so keeps the store's order for them. The panel gives the
// pass the cards as its list stands (file-comments.ts, placeCards): the model's order after a render, and after every
// other pass (a resize, a card's growth, a figure's load, a comment composer's open or Cancel) the order the LAST pass
// left, since a pass re-appends the cards in placement order. A tie broken by that order, as first built, made the
// placement depend on which pass ran last: under a focus, with the tied pair straddling the spill, each pass reversed
// the pair, and a comment card and a change card whose marks shared a line swapped places at every composer open,
// Cancel and paint pass, every card below moving by their height difference (the Slice 4 review of
// plans/markdown-viewer.md, round 16, 2026-09-10). The fields are ones the panel reads off its model for every card it
// lays (the change's hunk, the comment's card), so no order is fed to the pass or held between renders; a rank stamped
// on each card at render and read by the pass would have been the other exact fix, and these make it moot. The focus
// rule works on the sorted order as it does for any two cards: a same-line comment card keeps the list's side of a
// focused change card, below it, and a same-line change card lays above a focused comment card, pulled up where there
// is room; of a tied pair above the focus, the chain reaches the comment first, so with room for the comment but not
// for both the change, first of the pair, is the one laid below the focus and the comment holds the start: there the
// comment displays above the change it is about, the case above (card-layout.test.ts and file-comments-margin.test.ts
// pin the scene); a comment too tall for the room spills itself and a change that fits holds the start, the list's
// order. An item with no `kind` (a bare test item) ranks as a comment card at time 0, so two of them tie by key. The
// loose group keeps the list's order: a pass never reorders loose cards among themselves (a spilled suffix follows the
// focus, the rest keep their places), so the order a pass reads back is the model's, and the two orders agree.
export type LayoutItem = {
  key: string; desired: number | null; height: number;
  /** the tie on a shared desired top (the module comment): a change card lays before a comment card, two change cards
   *  by `from` then `ts`, two comment cards by `ts`, and the key decides the rest; an item with none of these is laid
   *  as a comment card at time 0 */
  kind?: "change" | "comment"; from?: number; ts?: number;
};
export type PlacedItem = { key: string; top: number; height: number; desired: number | null; pushed: number };
export type Layout = { placed: PlacedItem[]; bottom: number };

/** The gap between cards, the sheet's `.fc-cards { gap: 8px }` (pinned by card-layout.test.ts). */
export const CARD_GAP = 8;

/** The order two marked items are laid in: by desired top, and on a tie in the list's order by the cards' fields, a
 *  change card before a comment card, two changes by `from` then `ts`, two comments by `ts`, the key last (the module
 *  comment). Total over items with distinct keys, so the placement never depends on the order the items came in. */
export function tieOrder(a: LayoutItem, b: LayoutItem): number {
  return (a.desired as number) - (b.desired as number)
    || (a.kind === "change" ? 0 : 1) - (b.kind === "change" ? 0 : 1)
    || (a.from ?? 0) - (b.from ?? 0)
    || (a.ts ?? 0) - (b.ts ?? 0)
    || (a.key < b.key ? -1 : a.key > b.key ? 1 : 0);
}

/** Place `items` in a track: the loose ones first from `gap` down, then the marked ones by desired top (a tie in the
 *  list's order: tieOrder) with the push-down rule, or, with `focus` naming a marked item, anchored on that item (the
 *  module comment). Returns the placements in placement order and the bottom edge of the last card (the track's
 *  content must reach at least that far). */
export function layoutCards(items: LayoutItem[], gap: number = CARD_GAP, focus: string | null = null): Layout {
  const placed: PlacedItem[] = [];
  let floor = gap;                                   // where the next card may begin at the earliest
  let bottom = 0;
  const put = (it: LayoutItem, top: number): void => {
    placed.push({ key: it.key, top, height: it.height, desired: it.desired, pushed: it.desired === null ? 0 : top - it.desired });
    floor = top + it.height + gap;
    bottom = Math.max(bottom, top + it.height);
  };
  const marked = items.filter((it) => it.desired !== null).sort(tieOrder);   // a tie in the list's order, never the input's (the module comment)
  const f = focus === null ? -1 : marked.findIndex((it) => it.key === focus);
  if (f < 0) {
    for (const it of items) if (it.desired === null) put(it, floor);
    for (const it of marked) put(it, Math.max(it.desired as number, floor));
    return { placed, bottom };
  }
  // the focus: the loose group and the cards above the focus as the push-down rule lays them, then each moved up only
  // as far as the card under it needs, from the focus upward — and a card the chain would move past the track's start
  // laid below the focused card instead, never at a top the track cannot scroll to (the module comment). A card laid
  // below stands above nothing: the pass runs again without it, so a card it had pushed is laid from its own mark, until
  // a pass moves no card past the start (each pass adds to the spilled set or is the last; the set is bounded by the items)
  const loose = items.filter((it) => it.desired === null);
  const above = marked.slice(0, f), below = marked.slice(f + 1), fit = marked[f];
  const tops = new Map<LayoutItem, number>();
  const focusTop = Math.max(fit.desired as number, gap);
  const spilled = new Set<LayoutItem>();             // the cards no room is left for above the focus: below it instead
  for (let grew = true; grew;) {
    const known = spilled.size;
    floor = gap;
    for (const it of loose) if (!spilled.has(it)) { tops.set(it, floor); floor += it.height + gap; }
    for (const it of above) if (!spilled.has(it)) { const top = Math.max(it.desired as number, floor); tops.set(it, top); floor = top + it.height + gap; }
    let ceiling = focusTop - gap;                    // the lowest bottom the card above may have
    for (const it of above.slice().reverse()) {
      if (spilled.has(it)) continue;                 // laid below the focus by a pass before: no part of the track above it
      const top = Math.min(tops.get(it) as number, ceiling - it.height);
      if (top < 0) { spilled.add(it); continue; }      // past the start: below the focus; the room above stays for the cards further up
      tops.set(it, top);
      ceiling = top - gap;
    }
    // the loose group stands at the start and moves up as one by the least the chain needs, no further than the start;
    // where even that leaves its end under the ceiling, the cards at its end go below the focus, in the list's order, until
    // the rest fit (the group's head keeps its place). The cards a pass before sent below are a suffix of the group, the
    // end going first, so the group this pass lays is the prefix before them
    let keep = loose.length, shift = 0;
    while (keep > 0 && spilled.has(loose[keep - 1])) keep--;
    for (; keep > 0; keep--) {
      const last = loose[keep - 1];
      shift = Math.max(0, (tops.get(last) as number) + last.height - ceiling);
      if ((tops.get(loose[0]) as number) - shift >= 0) break;
    }
    loose.forEach((it, i) => { if (i < keep) tops.set(it, (tops.get(it) as number) - shift); else spilled.add(it); });
    grew = spilled.size > known;
  }
  for (const it of loose) if (!spilled.has(it)) put(it, tops.get(it) as number);
  for (const it of above) if (!spilled.has(it)) put(it, tops.get(it) as number);
  put(fit, focusTop);
  // the cards the focus displaced, by the push-down rule from its end: the marked ones first (each stacks: its mark is
  // above the focus), then the loose ones; the cards below the focus follow from the last of them
  for (const it of above) if (spilled.has(it)) put(it, Math.max(it.desired as number, floor));
  for (const it of loose) if (spilled.has(it)) put(it, floor);
  for (const it of below) put(it, Math.max(it.desired as number, floor));
  return { placed, bottom };
}
