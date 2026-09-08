// Pinned notes (the user 2026-09-08): a session pins short notes above its own transcript for the
// person it works for: what they should see first whenever they open it (where things stand, a
// warning, a summary). The kernel's pinned-notes store ships the rows on build_session's `pinnedNotes`
// field and on every chatTail (the userTodos seam's shape); render.ts paints them into #pinned-notes,
// the strip between the tab bar and the transcript, through buildPinnedNotes below, and repaints only
// when pinnedNotesKey changes: a pin or an unpin, never a frame that carries the same rows.
//
// Pure but for the document it is handed (createElement), so a test runs it against a small DOM
// stand-in (the pr-links.test.ts convention). Everything a session wrote lands through textContent,
// never innerHTML: a note is untrusted text.
//
// Progressive disclosure (ui/CLAUDE.md): one compact row per note in pin order (newest last), ONE LINE
// each (the sheet cuts a long text with an ellipsis; the strip itself is capped at a few rows and
// scrolls past the cap, so the transcript and the composer stay on screen: review round 1, 2026-09-08),
// the detail folded behind a click on the row's text or on its "details" hint (the user-todo row's
// vocabulary; the hint is a button, so the keyboard reaches the fold), and a text the row cuts carried
// in full inside that fold and as the row's title. WHICH rows are cut is decided by measurement, not by a
// character count (below, pinnedMeasureCut). At most PINNED_VISIBLE rows showing, the NEWEST, since the
// kernel's own bound drops the oldest first, and the older rows behind one "+N more" fold that sits where
// they live, above the visible rows. An empty list renders nothing (null), so the strip takes no space.
//
// Click safety (ui/CLAUDE.md): no listener is hung on any node the BUILDER makes. Every control declares
// a data-act (PINNED_ACT) for the delegate render.ts installs ONCE on the stable #pinned-notes host, and
// the fold states are keyed by note id / session id in the state the caller holds, so a rebuild on the
// next push paints the same open folds. The one listener set this module knows is armUnpin's, hung on a
// GESTURE (the arming click) and taken down by the disarm, never by a render.
import { utHintFor, applyUtHint, UT_HINT_CLASS } from "./user-todo-hint";

export interface PinnedNote { id: string; text: string; detail?: string; createdT?: number }
export interface PinnedFoldState { openDetails: Set<string>; moreOpen: Set<string> }
// The two linkers the caller supplies: the row's one-line text takes the compact pass (paths become
// links, no figure previews), the detail the full one. render.ts hands in linkTodoLinePaths /
// linkTodoDetailPaths + linkifyPrRefs, the exact pair the user-todo row uses, so a path or a `#123`
// in a note links the way it does there (one code path).
export interface PinnedLinkers { line(node: HTMLElement): void; detail(node: HTMLElement): void }
// The element factory: a document, or a stand-in with the one method this module calls.
export interface PinnedDoc { createElement(tag: string): HTMLElement }

export const PINNED_VISIBLE = 3;
export const PINNED_ACT = { toggle: "pntoggle", more: "pnmore", unpin: "pnunpin" } as const;
export const PINNED_UNPIN_LABEL = "Unpin";
export const PINNED_UNPIN_ARMED = "Unpin?";
// A row is one line, and the sheet cuts a longer text with an ellipsis. Which rows it cuts is a LAYOUT fact
// (the pane's width, the font, the hint and Unpin controls beside the text) that the builder cannot see and
// no character count predicts: a 72-character bound left a 60-character note cut on a phone with no hint,
// no fold and no title, so the rest of it could not be read (review round 2, 2026-09-08). So every row
// carries its full text as its title, every row is BUILT with a fold holding the full text (and the detail),
// and the fold is OFFERED by measurement: pinnedMeasureCut reads each row's overflow after the paint
// (scrollWidth > clientWidth) and marks the cut rows with PINNED_CUT_CLASS; the sheet shows the hint, the
// click target and the fold's full text on a row wearing that class (or PINNED_BREAK_CLASS, a line break
// the one-line row shows as a space, which the builder does know; or PINNED_DETAIL_CLASS, a detail), and
// nothing on a row wearing none. render.ts runs the measure on the frame that carries the notes and on a
// width change of the strip (pinnedWatchWidth: a ResizeObserver, the tab bar's idiom; no timer).
export const PINNED_CUT_CLASS = "pn-over";
export const PINNED_BREAK_CLASS = "pn-break";
export const PINNED_DETAIL_CLASS = "pn-with-detail";
/** The classes that mean "this row has something behind its fold", in one place for the sheet's test. */
export const PINNED_FOLD_CLASSES: readonly string[] = [PINNED_CUT_CLASS, PINNED_BREAK_CLASS, PINNED_DETAIL_CLASS];

/** The repaint gate: what the strip shows is a function of the active session and its rows, so the
 *  strip repaints only when this string changes: new information (a pin, an unpin, a tab switch) and
 *  nothing else. Fixed store values only reach it (the kernel ships none that tick). */
export function pinnedNotesKey(sid: string, notes: readonly PinnedNote[] | undefined): string {
  return sid + " " + JSON.stringify(notes || []);
}

/** The fold row's words: how many older notes it hides, and what a click does. */
export function pinnedMoreLabel(hidden: number, open: boolean): string {
  return open ? "hide " + hidden + " more" : "+" + hidden + " more";
}

/** Split the rows into the ones the fold hides (the oldest) and the ones always shown (the newest
 *  PINNED_VISIBLE). PINNED_VISIBLE rows or fewer hide nothing: a fold over one row costs a click for
 *  nothing. */
export function pinnedSplit<T>(notes: readonly T[]): { hidden: T[]; shown: T[] } {
  if (notes.length <= PINNED_VISIBLE) return { hidden: [], shown: notes.slice() };
  return { hidden: notes.slice(0, notes.length - PINNED_VISIBLE), shown: notes.slice(notes.length - PINNED_VISIBLE) };
}

/** Whether the row has anything behind its fold: a cut text (measured, or a line break) or a detail. */
export function pinnedHasFold(item: { classList: { contains(c: string): boolean } }): boolean {
  return PINNED_FOLD_CLASSES.some((c) => item.classList.contains(c));
}

/** The row's one-line text overflows its box: the cut, read after paint (a layout fact, never a count). */
export function pinnedRowOverflows(txt: { scrollWidth: number; clientWidth: number }): boolean {
  return txt.scrollWidth > txt.clientWidth;
}

/** The row's text is the fold's click target exactly when the row has a fold: a bare row's text is not a
 *  control (nothing would open), so it declares no data-act and the delegate never fires for it. */
function setFoldTarget(item: { classList: { contains(c: string): boolean } }, txt: HTMLElement): void {
  if (pinnedHasFold(item)) txt.dataset.act = PINNED_ACT.toggle;
  else delete txt.dataset.act;
}

/** What pinnedMeasureCut needs of a painted strip: the host, or a stand-in with the two query methods. */
export interface PinnedStripRoot { querySelectorAll(sel: string): ArrayLike<HTMLElement> }

/** Measure every row of a painted strip and mark the cut ones (PINNED_CUT_CLASS), so the hint, the click
 *  target and the fold's full text show exactly where the one-line row does not show it all. Idempotent
 *  (a row keeps its class while its measurement holds; a hidden row, in a closed "+N more" fold, measures
 *  0 and 0 and wears nothing until the repaint that shows it). Returns how many rows changed. The events
 *  that call it: the paint that carries the rows, and a width change of the strip (pinnedWatchWidth). */
export function pinnedMeasureCut(root: PinnedStripRoot): number {
  let changed = 0;
  for (const item of Array.from(root.querySelectorAll(".pn-item"))) {
    const txt = item.querySelector<HTMLElement>(".pn-text");
    if (!txt) continue;
    const over = pinnedRowOverflows(txt);
    if (over !== item.classList.contains(PINNED_CUT_CLASS)) {
      if (over) item.classList.add(PINNED_CUT_CLASS); else item.classList.remove(PINNED_CUT_CLASS);
      changed++;
    }
    setFoldTarget(item, txt);
  }
  return changed;
}

const pnWatched = new WeakSet<object>();
/** Re-measure the rows when the strip's width changes: one ResizeObserver per host, installed once (the
 *  tab bar's idiom, render.ts ensureTabRowObserver), and once more when the document's fonts finish
 *  loading, since a font swap re-widths every row without moving the host's box. Events, not timers. A
 *  host without ResizeObserver (a stand-in) keeps the paint-time measure alone. */
export function pinnedWatchWidth(host: HTMLElement): void {
  if (pnWatched.has(host)) return;
  pnWatched.add(host);
  if (typeof ResizeObserver === "function") new ResizeObserver(() => { pinnedMeasureCut(host); }).observe(host);
  const fonts = (host.ownerDocument as any)?.fonts;
  if (fonts && fonts.ready && typeof fonts.ready.then === "function") fonts.ready.then(() => { pinnedMeasureCut(host); }, () => {});
}

function make(doc: PinnedDoc, tag: string, cls: string): HTMLElement {
  const e = doc.createElement(tag);
  e.className = cls;
  return e;
}

function noteItem(doc: PinnedDoc, sid: string, n: PinnedNote, state: PinnedFoldState, link: PinnedLinkers): HTMLElement {
  const item = make(doc, "div", "pn-item");
  item.dataset.nid = n.id;
  const detail = (n.detail || "").trim();
  if (detail) item.classList.add(PINNED_DETAIL_CLASS);
  if (/\n/.test(n.text)) item.classList.add(PINNED_BREAK_CLASS);   // the one-line row shows the break as a space
  const line = make(doc, "div", "pn-line");
  const txt = make(doc, "span", "pn-text");
  txt.textContent = n.text;
  txt.title = n.text;   // the whole text on hover, whatever the one-line row shows of it
  txt.dataset.nid = n.id;
  link.line(txt);   // paths and PR numbers link inside the one-line text
  const open = state.openDetails.has(n.id);
  const hint = utHintFor(open);
  line.appendChild(txt);
  // the hint is a BUTTON beside the text, not inside it: a keyboard reaches the fold through it (Enter /
  // Space are a button's own click), and the ellipsis on a long text cannot swallow it. Built on every
  // row; the sheet shows it on a row with a fold (pinnedHasFold), and display:none keeps a bare row's
  // out of the tab order.
  const more = make(doc, "button", UT_HINT_CLASS);
  more.setAttribute("type", "button");
  more.dataset.act = PINNED_ACT.toggle; more.dataset.nid = n.id;
  more.setAttribute("aria-expanded", open ? "true" : "false");
  applyUtHint(more, hint);
  line.appendChild(more);
  const unpin = make(doc, "button", "pn-unpin");
  unpin.setAttribute("type", "button");
  unpin.dataset.act = PINNED_ACT.unpin; unpin.dataset.nid = n.id; unpin.dataset.sid = sid;
  unpin.textContent = PINNED_UNPIN_LABEL;
  unpin.title = "take this note down (click twice)";
  line.appendChild(unpin);
  item.appendChild(line);
  // the fold: the full text first (shown when the row is cut), then the detail (when there is one)
  const d = make(doc, "div", "pn-detail" + (open ? " open" : ""));
  const full = make(doc, "div", "pn-full");
  full.textContent = n.text;
  d.appendChild(full);
  if (detail) {
    const rest = make(doc, "div", "pn-more");
    rest.textContent = detail;
    d.appendChild(rest);
  }
  link.detail(d);
  item.appendChild(d);
  setFoldTarget(item, txt);
  return item;
}

/** The strip's content for one session, or null when there is nothing to show. */
export function buildPinnedNotes(doc: PinnedDoc, sid: string, notes: readonly PinnedNote[], state: PinnedFoldState,
    link: PinnedLinkers): HTMLElement | null {
  if (!notes.length) return null;
  const strip = make(doc, "div", "pn-strip");
  const { hidden, shown } = pinnedSplit(notes);
  if (hidden.length) {
    const open = state.moreOpen.has(sid);
    const fold = make(doc, "button", "pn-fold");
    fold.setAttribute("type", "button");
    fold.dataset.act = PINNED_ACT.more; fold.dataset.sid = sid;
    fold.textContent = pinnedMoreLabel(hidden.length, open);
    fold.title = open ? "hide the older notes" : "show the older notes";
    strip.appendChild(fold);
    const rest = make(doc, "div", "pn-rest" + (open ? " open" : ""));
    for (const n of hidden) rest.appendChild(noteItem(doc, sid, n, state, link));
    strip.appendChild(rest);
  }
  for (const n of shown) strip.appendChild(noteItem(doc, sid, n, state, link));
  return strip;
}

// ── the armed Unpin ─────────────────────────────────────────────────────────────────────────────
// The document the arm listens on: a Document, or a stand-in with the two methods (tests).
export interface ArmDoc {
  addEventListener(type: string, fn: (ev: any) => void, capture?: boolean): void;
  removeEventListener(type: string, fn: (ev: any) => void, capture?: boolean): void;
}

/** Arm an Unpin control (the two-step confirm) and return its disarm. The arm is a transient state, and
 *  it ends on an EVENT, never a timer (ui/CLAUDE.md): the next pointerdown anywhere else (on a coarse
 *  pointer there is no hover, so without this the arm latched until the next pin, and a stray tap
 *  minutes later unpinned in one step: review round 1, 2026-09-08), the control losing focus (a
 *  keyboard user tabbing away), or, with a fine pointer, the pointer leaving it. A press ON the control
 *  keeps the arm: it is the confirming click, or a scroll that started there (the utdismiss lesson).
 *  The caller also disarms before it repaints the strip, so no listener outlives its row. */
export function armUnpin(btn: HTMLElement, doc: ArmDoc, coarse: boolean): () => void {
  btn.classList.add("armed"); btn.textContent = PINNED_UNPIN_ARMED;
  let off: (() => void) | null = null;
  const disarm = (): void => {
    if (!off) return;
    const f = off; off = null; f();
    btn.classList.remove("armed"); btn.textContent = PINNED_UNPIN_LABEL;
  };
  const onDown = (ev: any): void => { if (ev.target === btn) return; disarm(); };
  const onBlur = (): void => disarm();
  const onLeave = (): void => disarm();
  doc.addEventListener("pointerdown", onDown, true);
  btn.addEventListener("blur", onBlur);
  if (!coarse) btn.addEventListener("pointerleave", onLeave);
  off = () => {
    doc.removeEventListener("pointerdown", onDown, true);
    btn.removeEventListener("blur", onBlur);
    btn.removeEventListener("pointerleave", onLeave);
  };
  return disarm;
}

// ── the unpin latch ─────────────────────────────────────────────────────────────────────────────
// A confirmed Unpin removes the row at once (the acknowledgement), but the session's list still holds
// the note until the kernel's next frame, and a frame built BEFORE the unpin landed (the pusher's cycle
// already in flight, which carries the list on every chatTail) would paint the row back for one cycle
// and remove it again: a flap on a gesture that should move the strip exactly once (cards move on new
// information). The latch remembers the list as the last frame carried it and the ids unpinned against
// it; a frame carrying that same list is old news and shows without those rows, and any OTHER list for
// the session (the kernel's confirmation, a new pin, a refused unpin's repaint) is new information that
// releases the latch. A frame for another session says nothing about this one and leaves it armed.
export interface UnpinLatch { sid: string; key: string; nids: readonly string[] }

/** Arm the latch at a confirm, or extend it when another unpin lands against the same stale list. */
export function latchUnpinAt(latch: UnpinLatch | null, sid: string, notes: readonly PinnedNote[], nid: string): UnpinLatch {
  const key = pinnedNotesKey(sid, notes);
  if (latch && latch.sid === sid && latch.key === key) return { sid, key, nids: [...latch.nids, nid] };
  return { sid, key, nids: [nid] };
}

/** The rows the strip shows for a frame's list under the latch, and the latch after it. */
export function latchedNotes(latch: UnpinLatch | null, sid: string, notes: readonly PinnedNote[]): { notes: readonly PinnedNote[]; latch: UnpinLatch | null } {
  if (!latch || latch.sid !== sid) return { notes, latch };
  if (pinnedNotesKey(sid, notes) !== latch.key) return { notes, latch: null };
  return { notes: notes.filter((n) => !latch.nids.includes(n.id)), latch };
}
