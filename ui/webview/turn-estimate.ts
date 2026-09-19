// The chat window's two height figures, pure (PR E, 2026-09-19; render.ts measureUnits wires them to a view): the rows' AVERAGE, which
// sizes the hidden units the spacers stand for, and the head gap's estimate PER TURN, which sizes the history the page does not hold
// (chat-regions.ts gapHeight). Both read the heights the unit ResizeObserver reported (render.ts ensureView, `v.uh`), never a layout
// property: the render task forces no layout for them.
//
// The per-turn figure is the MEDIAN over the turns the window holds WHOLE. A turn starts at a visible user row and ends at the next
// one; the rows before the window's first user row belong to a turn whose prompt is above the window, and the rows after its last
// belong to the turn still streaming, so neither is a turn the window can measure and neither is counted. At least two complete
// turns are required, else the caller keeps the figure it had (the default, until a window has two). The old figure was the window's
// whole height over its count of user rows, measured once for the view's life: the tail window of a long agentic turn holds one user
// row and about 79 dense rows, so it measured about 7,150 px per turn, and the 200-turn head gap above it went from 24k px to 1.43M px
// on the paint after the first (the phone, 2026-09-19). The median over complete turns cannot see that shape at all: a window with one
// user row has no complete turn.
//
// Heights are BORDER-BOX (padding included), the height offsetHeight reports and the browser leg recomputes; the observer's
// contentRect is the content box and under-reads a row by its 14 to 22 px of padding. A row the observer has not reported yet has no
// height: a turn holding one is not counted (never a 0), and the average skips it.

/** One rendered row of a view as the estimator sees it: its class list, whether it is hidden inline (display:none — a stripped user
 *  record, the echo of a send: no box, and the observer never reports one), and its border-box height when the observer has reported it. */
export interface EstRow { cls: string; hidden: boolean; h: number | undefined }

/** The rows of a view's children, in order, through three readers (the class list, the inline hidden state, the reported height). */
export function rowsFor<T>(children: ArrayLike<T>, classOf: (c: T) => string, hiddenOf: (c: T) => boolean, heightOf: (c: T) => number | undefined): EstRow[] {
  const out: EstRow[] = [];
  for (let i = 0; i < children.length; i++) { const c = children[i]; out.push({ cls: String(classOf(c) || ""), hidden: !!hiddenOf(c), h: heightOf(c) }); }
  return out;
}

const has = (cls: string, c: string): boolean => (" " + cls + " ").indexOf(" " + c + " ") >= 0;
/** A virtualization spacer or a gap element: never row content. */
export const isSpacerRow = (r: EstRow): boolean => has(r.cls, "tx-spacer") || has(r.cls, "tx-gap");
/** A turn row (every event's root is `turn …`; a day divider is not). */
export const isTurnRow = (r: EstRow): boolean => has(r.cls, "turn") && !isSpacerRow(r);
/** A row that STARTS a turn: a visible user row. A hidden one (turn-user-empty, turn-echo-hidden) has no box and starts nothing, so a
 *  stripped record inside a long agentic turn does not split it into two turns of zero-height prompts. */
export const isUserRow = (r: EstRow): boolean => isTurnRow(r) && has(r.cls, "turn-user") && !r.hidden;

/** The rows' mean height over every non-spacer, non-gap child: the population the old measure averaged (dividers included, a hidden row
 *  at 0), less the rows the observer has not reported. Null when nothing measurable is there. */
export function meanRowHeight(rows: readonly EstRow[]): number | null {
  let h = 0, n = 0;
  for (const r of rows) {
    if (isSpacerRow(r)) continue;   // the gap's own estimate must not feed the average that sizes it (T386 stage 2, medium 3)
    if (r.hidden) { n++; continue; }
    if (r.h == null) continue;
    h += r.h; n++;
  }
  return h > 0 && n > 0 ? h / n : null;
}

/** The heights of the turns the window holds whole, in order: from each visible user row to the next. The leading rows (a prompt
 *  above the window) and the trailing rows (the turn still open, the one streaming) are not counted; a turn with an unreported row is
 *  dropped rather than counted short. Only turn rows count (spacers, gaps and dividers are not turn content, as before). */
export function completeTurnHeights(rows: readonly EstRow[]): number[] {
  const out: number[] = [];
  let open = false;                 // inside a turn (a visible user row has been seen)
  let acc: number | null = null;    // the open turn's height so far; null once a row of it had no height
  for (const r of rows) {
    if (!isTurnRow(r)) continue;
    if (isUserRow(r)) {
      if (open && acc != null) out.push(acc);
      open = true; acc = r.h == null ? null : r.h;
      continue;
    }
    if (!open || acc == null || r.hidden) continue;
    if (r.h == null) { acc = null; continue; }
    acc += r.h;
  }
  return out;   // the turn still open at the end is the streaming one: never counted
}

/** The median of a non-empty list; null for an empty one. */
export function median(xs: readonly number[]): number | null {
  if (!xs.length) return null;
  const s = xs.slice().sort((a, b) => a - b);
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

/** The minimum count of complete turns a window must hold before its median stands as the per-turn figure. */
export const MIN_COMPLETE_TURNS = 2;

/** The head gap's per-turn estimate from a window's rows: the median over its complete turns when it holds at least MIN_COMPLETE_TURNS
 *  of them, else null (the caller keeps what it had). */
export function perTurnEstimate(rows: readonly EstRow[]): number | null {
  const hs = completeTurnHeights(rows);
  return hs.length >= MIN_COMPLETE_TURNS ? median(hs) : null;
}
