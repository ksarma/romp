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
// vocabulary; the hint is a button, so the keyboard reaches the fold), and a text long enough to be cut
// carried in full inside that fold; at most PINNED_VISIBLE rows showing, the NEWEST, since the kernel's
// own bound drops the oldest first, and the older rows behind one "+N more" fold that sits where they
// live, above the visible rows. An empty list renders nothing (null), so the strip takes no space.
//
// Click safety (ui/CLAUDE.md): no listener is hung on any node the BUILDER makes. Every control declares
// a data-act (PINNED_ACT) for the delegate render.ts installs ONCE on the stable #pinned-notes host, and
// the fold states are keyed by note id / session id in the state the caller holds, so a rebuild on the
// next push paints the same open folds. The one listener set this module knows is armUnpin's, hung on a
// GESTURE (the arming click) and taken down by the disarm, never by a render.
import { utDetailHint, applyUtHint, UT_HINT_CLASS } from "./user-todo-hint";

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
// A row is one line, and the sheet cuts a longer text with an ellipsis; a text past this many characters
// (or one with a line break) is carried IN FULL inside the row's fold, so nothing a session wrote is out
// of reach. An approximation of the cut (the sheet cuts by width, which the builder cannot see): a phone
// shows about fifty characters, a desktop column well over a hundred, so a text this long may be cut
// somewhere and a shorter one shows whole on any surface the strip has.
export const PINNED_LINE_CHARS = 72;

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

/** What the row's fold holds: the detail, and, first, the full text when the one-line row may cut it
 *  (PINNED_LINE_CHARS, or a line break, which the one-line row shows as a space). "" means no fold. */
export function pinnedFoldText(n: PinnedNote): string {
  const detail = (n.detail || "").trim();
  const cut = n.text.length > PINNED_LINE_CHARS || /\n/.test(n.text);
  if (!cut) return detail;
  return detail ? n.text + "\n\n" + detail : n.text;
}

function make(doc: PinnedDoc, tag: string, cls: string): HTMLElement {
  const e = doc.createElement(tag);
  e.className = cls;
  return e;
}

function noteItem(doc: PinnedDoc, sid: string, n: PinnedNote, state: PinnedFoldState, link: PinnedLinkers): HTMLElement {
  const item = make(doc, "div", "pn-item");
  item.dataset.nid = n.id;
  const line = make(doc, "div", "pn-line");
  const txt = make(doc, "span", "pn-text");
  txt.textContent = n.text;
  link.line(txt);   // paths and PR numbers link inside the one-line text
  const open = state.openDetails.has(n.id);
  const fold = pinnedFoldText(n);
  const hint = utDetailHint(fold, open);
  if (hint) {
    txt.classList.add("pn-has-detail");
    txt.dataset.act = PINNED_ACT.toggle; txt.dataset.nid = n.id;
    txt.title = hint.title;
  }
  line.appendChild(txt);
  if (hint) {
    // the hint is a BUTTON beside the text, not inside it: a keyboard reaches the fold through it
    // (Enter / Space are a button's own click), and the ellipsis on a long text cannot swallow it
    const more = make(doc, "button", UT_HINT_CLASS);
    more.setAttribute("type", "button");
    more.dataset.act = PINNED_ACT.toggle; more.dataset.nid = n.id;
    more.setAttribute("aria-expanded", open ? "true" : "false");
    applyUtHint(more, hint);
    line.appendChild(more);
  }
  const unpin = make(doc, "button", "pn-unpin");
  unpin.setAttribute("type", "button");
  unpin.dataset.act = PINNED_ACT.unpin; unpin.dataset.nid = n.id; unpin.dataset.sid = sid;
  unpin.textContent = PINNED_UNPIN_LABEL;
  unpin.title = "take this note down (click twice)";
  line.appendChild(unpin);
  item.appendChild(line);
  if (hint) {
    const d = make(doc, "div", "pn-detail" + (open ? " open" : ""));
    d.textContent = fold;
    link.detail(d);
    item.appendChild(d);
  }
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
