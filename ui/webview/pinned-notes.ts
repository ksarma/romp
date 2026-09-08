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
// Progressive disclosure (ui/CLAUDE.md): one compact row per note in pin order (newest last), the
// detail folded behind a click on the row's text (the user-todo row's hint vocabulary); at most
// PINNED_VISIBLE rows showing, the NEWEST, since the kernel's own bound drops the oldest first, and
// the older rows behind one "+N more" fold that sits where they live, above the visible rows. An empty
// list renders nothing (null), so the strip takes no space.
//
// Click safety (ui/CLAUDE.md): no listener is hung on any node built here. Every control declares a
// data-act (PINNED_ACT) for the delegate render.ts installs ONCE on the stable #pinned-notes host, and
// the fold states are keyed by note id / session id in the state the caller holds, so a rebuild on the
// next push paints the same open folds.
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
  link.line(txt);   // paths and PR numbers link before the hint joins the span (the hint carries neither)
  const open = state.openDetails.has(n.id);
  const hint = utDetailHint(n.detail, open);
  if (hint) {
    txt.classList.add("pn-has-detail");
    txt.dataset.act = PINNED_ACT.toggle; txt.dataset.nid = n.id;
    txt.title = hint.title;
    const more = make(doc, "span", UT_HINT_CLASS); applyUtHint(more, hint); txt.appendChild(more);
  }
  line.appendChild(txt);
  const unpin = make(doc, "button", "pn-unpin");
  unpin.setAttribute("type", "button");
  unpin.dataset.act = PINNED_ACT.unpin; unpin.dataset.nid = n.id; unpin.dataset.sid = sid;
  unpin.textContent = PINNED_UNPIN_LABEL;
  unpin.title = "take this note down (click twice)";
  line.appendChild(unpin);
  item.appendChild(line);
  if (hint) {
    const d = make(doc, "div", "pn-detail" + (open ? " open" : ""));
    d.textContent = n.detail || "";
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
