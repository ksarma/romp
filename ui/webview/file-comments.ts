// File comments and tracked changes — the viewer's Comments panel (plans/file-review.md, Slices 1 to 5).
//
// The person who directs the sessions reads their output as files, and until now a comment on a file
// left romp: GitHub, a chat quote that scrolled away, or a note typed into the file itself. This panel
// keeps a comment WITH the file, in the track-changents sidecar the agent's own CLIs read and write
// (`.trackchanges/` beside the project's root; docs/adr/0002), and hands everything unsent to the
// session in ONE message — so a morning's reading costs one interruption, not one per remark.
//
// Shape (the plan's Shape of the feature):
//   • The action-row entry is the glance ("Comments · 2 · 5 changes"); the panel is one click; a card
//     expands on click, keyed by comment id in a set that survives every re-render.
//   • A session's pending changes (Slice 2) are cards too: one per change, grouped by the paragraph it
//     falls in, with Accept, Reject, Comment on this change (the about follow-on, 2026-09-10: a comment of the person's
//     naming the change by its stored id, changeIds, its own card in the list) and Reveal; no comment is drawn inside a
//     change's card, and the two are linked by tags ("about N changes" on the comment, "N comments" on the change). Past
//     three groups the rest fold behind one row. The changes are also marked inline in both views — insertions
//     tinted, deletions struck at their point (Rendered places it through the index map since the inline-display
//     follow-on, 2026-09-07; a deletion the map cannot place is card-only) — through anchor-map's change painters
//     (contract D4); a click on a mark opens its card, and Show changes inline in the panel's head turns every mark
//     off in both views. Accept and Reject fence on the sidecar's mtime; Reject, which rewrites the file, also
//     fences on the file's mtime and then reloads the view, since the bytes changed under it.
//   • A region on an image (Slice 3) or on a PDF page (Slice 4) is a comment too: the overlays file-comments-regions.ts
//     puts over the media body's picture, over every figure in rendered markdown, and over each page the PDF chunk
//     draws (one per page, the region's `page` from the canvas's data-page; a far page with nothing to paint takes its
//     overlay as it nears the reader, pageWatch, since making one lays out the whole page column) take a drag and paint
//     each region comment as a rectangle placed by percentages, dashed once the image's bytes changed under it (the
//     host's hash against the stored one). The card shows the region cut from the picture and offers Re-place, which
//     retargets the comment to the next region drawn. Desktop only; a coarse pointer reads and comments on the whole file.
//     A PDF's pages are read from the chunk's shells (pdfPages): a page with no shell is one the regenerated document
//     no longer has (pageGone: stale, Re-place on any page); a shell with no canvas is a page pdf.js could not draw
//     (pageUnrendered: the card says so and reaches the page's own notice, and claims nothing about the file). A
//     region's crop is cut and kept as its page draws (cutCrop, from the region pass on every draw's repaint), the card
//     open or not, so a card keeps its picture after the chunk evicts the page's bitmap, and a card expanded once the
//     page has scrolled away shows it too; a page with no bitmap and nothing kept (pageUndrawn: the chunk draws pages as
//     they near the reader, and nothing here can ask for one) has, in the crop's place, a line that says so and scrolls
//     the page in, which draws it and brings the crop.
//     A figure in rendered markdown is wrapped by its overlay only while the panel is open or the figure has a
//     rectangle to show (paintRegions): closed, with nothing to show, the author's own layout of the page stands.
//   • Edit over pending changes (Slice 5): the viewer's editor carries the changes as marks of its own, so while it is
//     up the paint pass stands down and the poll's file reload does too (a row in the head says the bytes moved). Save
//     goes through this panel (`save`: the text, the records as the editor remapped them, the decisions taken in it),
//     fenced on the sidecar the records came from (the status at Edit, or the last landed save's reply when the editor stayed
//     up past it) and on the file the editor loaded; a refused save keeps the buffer.
//     The change cards stay up meanwhile, but a decision from one is refused in place (DECIDE_IN_EDITOR): it would move
//     the sidecar the editor's records came from, and the buffer could then never be saved. When a decision lands from
//     elsewhere anyway (another browser, a session's CLI) the head says so from the status that shows it, before Save
//     can refuse (CHANGES_MOVED_UNDER_EDIT); so does an Edit clicked before the first status answered, whose editor carries
//     no marks for the changes that status then shows (CHANGES_UNREAD_UNDER_EDIT) — Save refuses rather than write an empty
//     list over them. Reveal and the card links, which switch to Raw and scroll the read view, are not offered while the
//     editor holds the body, and the cards group over the text the offsets index, not the buffer typing moves (editText).
//   • The kernel does the disk work on the OWNING kernel (the `fileComments` op runs a node host
//     script over the vendored track-changents store); this module renders JSON and never holds a
//     sidecar it writes back. Both ops carry `sid`, so federation routes a remote session's file to
//     the kernel that owns the disk with no new relay code.
//   • Change awareness by POLLING (2.5 s while the panel is open and the tab visible): HEAD /file on
//     the file, the sidecar the kernel named, and the project's config.json, comparing X-Romp-Mtime-Ns
//     as STRINGS — and on every figure a text file's region comments name, against the poll's own last
//     reading (a regenerated figure moves none of the three; tick). The Files pane has no filesystem
//     watcher; the poll stands in for that event, and the person's own writes never fire it because every
//     verb reply re-baselines it. Replies land in the
//     order their asks were issued (applyStatus): the kernel runs each ask concurrently and answers when
//     it finishes, and a status that read the disk before a write — asked before it, or asked while it was
//     in flight — must not put the panel back a step once the write's reply is showing.
//   • The panel's controls hang off the viewer's body row, which also holds the FILE's rendered markup; an
//     activation is routed only when the panel made the element (own / owns), never for a data-act the
//     file's author wrote.
//   • What is unsent is derived from the comments log on the owning kernel, never from browser state
//     (decision 10): the `status` reply carries it, the button's count is that number.
//   • Every write sits behind the one file-editing consent, shared with Save (decision 5).
// The pure half (view model, message preview, poll verdicts) is file-comments-model.ts; the
// selection→anchor mapping and the highlight painters are anchor-map.ts (contract C4).
//
// This module imports only TYPES from file-view.ts and is registered there (registerFileViewAction
// in file-view.ts), so the two never form a runtime import cycle.
import type { FileViewAction, FileViewActionCtx, FileViewIdentity, TrackedEdit, CloseAsk } from "./file-view";
import { delegate, flash, pressHold, type ActionHandler, type PressHold } from "./actions";   // pressHold: the arrivals line's change in place waits out a press (the arrivals follow-on, 2026-09-09)
import { fileUrl } from "./preview";
import { kernelUrl } from "./media";
import { hostOf, bareId } from "./host-prefix";
import { loadSettings, saveSettings, onExternalSettingsChange, type CommentsFilter } from "./settings";   // Show changes inline and the filter: the shared, persisted webview settings (the inline-display and filter follow-ons, 2026-09-07)
import { mapRawSelection, mapRenderedSelection, makeAnchor, locateComment, paintRaw, paintRendered, rawOffsetToLine } from "./anchor-map";
import { paintChangesRaw, paintChangesRendered, unpaintChanges } from "./anchor-map";   // the change painters (contract D4)
import type { MapRefusal, SourceRange, Located, ChangePaint } from "./anchor-map";
import {
  type Status, type Hunk, type Card, type CardTurn, type ChangeCard, type ChangeGroup, type SendParts, type Target, actionLabel, cardModel, changeCards, changeGroups,
  foldGroups, moreChangesLabel, authorIdOf, GROUP_LIMIT, DETACHED_GROUP_KEY, sendParts, sendCounts, unsentCount, cardCounts, filterOffered, detachedChanges,
  commentsAbout, aboutOptionLabel, aboutTagWords, refStateWords, changeRef, answeredComments, resolveAnsweredLabel, resolveAnsweredAsk, resolvedWords,
  logRowText, pollBaseline, pollTargets, headVerdict, mtimeMoved, editBlockedReason, lineStartOffset, folderOf,
  regionTarget, regionState, figureTargets, figuresMoved, figureBaseline, figureFenceHash, type PollBaseline, type FigureBaseline, type HeadVerdict,
  pendingRecords, authorIdByLabel, saveArgs, sameRecords, MOVED_UNDER_EDIT, type EditDecisions,   // editing over pending changes (Slice 5)
  todoChoices, todoChoiceLabel, TODO_OPENED_FROM, type TodoChoice,   // the todo a send answers (the todo-file follow-on, 2026-09-07)
  statusEntries, arrivalWords, acceptOptionLabel, YOU, type Entry,   // the arrivals notice (the arrivals follow-on, 2026-09-09)
  partitionPending,   // the Send's accept takes the seen pending changes only (decision 41, 2026-09-09)
  noteTooLong, trimNote,   // the Send confirm's note box (the user's ruling, 2026-09-09); trimNote: the note as the kernel reads it
  savedWhereWords,   // the saved line: a save never moves the view, the line says where the card is (decision 43, 2026-09-09)
} from "./file-comments-model";
import { RegionLayer, cropThumb, isCoarsePointer, isCanvas, type Pictured, type RegionMark } from "./file-comments-regions";   // the overlays (Slice 3, contract E5; Slice 4's pages)
import { regionDesc, isRegion, type Region } from "./region-geometry";
import { layoutCards, CARD_GAP, type LayoutItem, type PlacedItem } from "./card-layout";   // the margin layout's pure half (the 2026-09-07 follow-on)

const POLL_MS = 2500;
const MOVED = new Set(["store-moved", "file-moved", "config-moved"]);
/** Whether a scroller stands at its end (within the pixel a fractional scrollTop can fall short of the integer heights). */
const atEnd = (el: HTMLElement): boolean => el.scrollTop + el.clientHeight >= el.scrollHeight - 1;
/** The comment a `comment` reply added, read off the reply's store (the host names no id in the reply): the one comment
 *  the status before the write did not hold — the write's fence (storeMtimeNs) admits no other write between the two.
 *  After a moved fence's re-read and retry the baseline `had` predates the retry's, so another client's comments may be
 *  new too; then the one whose body is the note, and null when that does not name exactly one — nothing to scroll to,
 *  and nothing in doubt about the save itself. */
function savedCommentId(had: Set<string>, r: Status, note: string): string | null {
  const fresh = r.store ? r.store.comments.filter((c) => !had.has(c.id)) : [];
  if (fresh.length === 1) return fresh[0].id;
  const mine = fresh.filter((c) => c.body === note);
  return mine.length === 1 ? mine[0].id : null;
}
// The verbs that rewrite the FILE, not only the sidecar (reject applies the engine's reverse edits): they
// fence on the file's mtime as the panel last saw it, so a `track-edit` landing mid-round refuses `file-moved`
// instead of reverting over it, and after one succeeds the panel reloads the view — the bytes changed under
// it, and the poll will never notice, since every reply re-baselines it (the plan's own rule).
const FILE_VERBS = new Set(["reject", "reject-all"]);
/** The verbs that write ABOUT a figure — a region's comment, a re-place — and so carry `fence.figureHash` when the status
 *  holds a hash for it (figureFenceHash); the host answers `figure-changed` when the bytes are no longer those. */
const FIGURE_VERBS = new Set(["comment", "retarget"]);
const FIGURE_CHANGED = "figure-changed";
// The verbs that carry no id: they decide whatever is pending when the host runs them. A moved fence on one is not
// retried (mutateOnce) — the plan's fence rule retries by stable change or comment id, and a retry here would decide
// the changes that landed since the click, which the person has not seen. The list is re-read and the choice is theirs again.
const BULK_VERBS = new Set(["accept-all", "reject-all"]);
// The verbs that decide changes BY ID (accept and reject, `{ids}`). The plan's fence rule retries these by stable id,
// and the id IS stable — the change under it is not: a same-author track-edit landing inside or beside a pending
// change is coalesced INTO it (engine.coalesceOps keeps the earlier op's id and grows its texts), so after a moved
// fence the clicked id can name a larger change than the card showed, and a retry would accept, or revert, text the
// person never saw. mutate therefore keeps each change as its card showed it (seen), and mutateOnce decides nothing
// when a change still pending under that id reads differently now (changedSince): the row under the card says so and
// the list, re-read, is theirs again — the BULK_VERBS rule, for an id whose content moved. An id that is GONE is left
// to the host, which refuses it `no-change` by name (the review2 suite pins that path). The seen set the Send's accept
// reads (decision 41) keeps the same texts per seen change (seenTexts), and a status that grows one makes it unseen again.
const DECIDE_VERBS = new Set(["accept", "reject"]);
/** A change as its card showed it when Accept or Reject was clicked: the texts, which the id does not fix. */
export type SeenChange = { id: string; kind: string; oldText: string; newText: string };
/** The changes a by-id decision names (`args.ids`), as the status they were clicked over describes them. */
export function seenChanges(s: Status | null, args: Record<string, unknown>): SeenChange[] {
  const ids = Array.isArray(args.ids) ? args.ids.map(String) : [];
  const out: SeenChange[] = [];
  for (const h of (s && s.hunks) || []) if (ids.includes(String(h.id))) out.push({ id: String(h.id), kind: h.kind, oldText: h.oldText, newText: h.newText });
  return out;
}
/** The seen changes still pending under their id that no longer read as they did — grown by a track-edit coalesced
 *  into them. A change whose id is gone is not listed: the host's `no-change` refusal names it. */
export function changedSince(seen: SeenChange[], hunks: Hunk[]): SeenChange[] {
  return seen.filter((c) => {
    const h = hunks.find((x) => String(x.id) === c.id);
    return !!h && (h.kind !== c.kind || h.oldText !== c.oldText || h.newText !== c.newText);
  });
}
/** The row under the card when a decision stood down (changedSince): in the person's words, and what to do next. */
export function changedRowText(n: number): string {
  return "Nothing decided: the session edited " + (n === 1 ? "this change" : "these changes") + " after you clicked, and "
    + (n === 1 ? "it now reads" : "they now read") + " differently. Look it over and try again.";
}
// The verbs that decide changes, and what a click on one gets while the editor is up (Slice 5). The editor carries the
// sidecar's records as marks and Save writes them back remapped, fenced on the sidecar they came from (editSeed); a
// card's accept or reject meanwhile would drop a record from that sidecar (and, for reject, rewrite the file) while the
// editor still holds it, so every later Save could only refuse `store-moved`, and the typed text would sit in a buffer
// nothing can land, with Reload and Cancel, which both discard it, the only offers. The decision belongs in the editor
// then: its click accepts, its modifier-click rejects, and Save carries both. A tap or a keyboard decides nothing in the
// editor (the editor chunk's marks, departure 6), so the words also name the route that needs no mouse: Save or Cancel,
// then these buttons, which are live again once the editor is closed — and on a device whose primary pointer is coarse (a
// phone, a tablet: isCoarsePointer) that route LEADS, since telling a finger to click and Alt-click names gestures the
// editor ignores from it (DECIDE_IN_EDITOR_TOUCH; the mouse gesture is still named, as one, for a tablet with a trackpad).
// The cards keep real buttons rather than disabled ones so the reason reaches touch and keyboard users (the Edit button's
// idiom, file-view.ts), and the foot says it once without a click — as a caption, or as the row a click gets, never both
// at once (renderChangesFoot).
const DECIDES = new Set(["accept", "reject", "accept-all", "reject-all"]);
export const DECIDE_IN_EDITOR = "While you edit, decide in the editor: click a change to accept it, Alt-click (Cmd-click on a Mac, Ctrl-click elsewhere) to reject it. "
  + "Save writes the decisions with your text. To use Accept and Reject instead, Save or Cancel first: they work again once the editor is closed.";
export const DECIDE_IN_EDITOR_TOUCH = "While you edit, a tap on a change decides nothing: the changes stay pending. "
  + "To accept or reject them, Save or Cancel first: Accept and Reject work again once the editor is closed. "
  + "With a mouse, a click on a change accepts it and Alt-click (Cmd-click on a Mac, Ctrl-click elsewhere) rejects it; Save then writes the decisions with your text.";
const DECIDE_TEXTS = new Set([DECIDE_IN_EDITOR, DECIDE_IN_EDITOR_TOUCH]);
/** Why Edit is refused while a decision this panel sent is still out (mutate holds it at the send and lifts it when the
 *  reply or the refusal lands: holdEdit). The other side of DECIDES: a decision drops a record from the sidecar (a reject
 *  rewrites the file too), and an editor opened while the request is out takes the records as they stood at the click and
 *  is fenced on that sidecar, so its every Save could only refuse `store-moved` — the typed text in a buffer nothing can
 *  land, told only once the reply shows it (CHANGES_MOVED_UNDER_EDIT). Keyed on the request's life, never on a clock; the
 *  viewer refuses in words, in place (its editBlocked idiom), so the reason reaches touch and keyboard users. */
export const DECISION_IN_FLIGHT = "A change in this file is being accepted or rejected right now. Edit opens as soon as that lands.";
/** The decide-in-editor words for this device, read at each use rather than once: the primary pointer can change (a tablet
 *  docks to a keyboard and trackpad), and a row set under one is retired by text under the other (DECIDE_TEXTS). */
function decideInEditor(): string { return isCoarsePointer() ? DECIDE_IN_EDITOR_TOUCH : DECIDE_IN_EDITOR; }
/** What the editor's records are fenced on: the sidecar of the status they came from — at Edit (trackedEdit.begin) or, once
 *  a save landed and the editor stayed up, that save's reply, which the host wrote them back to (saveThroughComments). Null
 *  when nothing is pending: an editor with no marks has nothing to fence on, and Save then follows the status (routesSave). */
type EditSeed = { records: unknown[]; storeMtimeNs: string; configMtimeNs: string };
function seedOf(s: Status): EditSeed | null {
  if (!(s.hunks || []).length) return null;
  return { records: pendingRecords(s.store), storeMtimeNs: s.storeMtimeNs ?? "", configMtimeNs: s.configMtimeNs ?? "" };
}
/** The host's `logWarning` on a reply — its account of a comments-log append that failed, or a sidecar it could not read
 *  back after writing — as text; "" when the reply carries none. */
function warningOf(r: unknown): string {
  const w = (r as { logWarning?: unknown }).logWarning;
  return typeof w === "string" && w ? w : "";
}
// The head's row when the sidecar's pending changes stop being the ones the editor carries while it is up (Slice 5): a
// decision landed since Edit — another browser's card, a session's CLI, or a card's own click that was still in flight
// when Edit began (the gate above reads editing() at the click, and the editor can open during the round trip) — and
// the file's bytes did not move (a reject moves them, and MOVED_UNDER_EDIT is that row). Said at once, from the status
// that shows it (noteChangesMovedUnderEdit, in applyStatus), not at Save: Save can only refuse then, since its fence is
// the sidecar the records came from and the retry stands down when the records changed, and the editor cannot take the
// new list (its handle is read-only), so the row names what is left — copy, Cancel, Edit again. One row per edit
// (changesMovedUnderEdit latches it, so a dismissed row does not return with every later status); retired when the edit
// ends (paintAll).
export const CHANGES_MOVED_UNDER_EDIT = "Pending changes in this file were accepted or rejected after you opened the editor, which still shows them as pending. "
  + "Save will refuse; copy anything you typed, then Cancel and Edit again.";
// The head's row when a status shows pending changes the editor does not carry and the file did not move: Edit was clicked
// before the first status answered (the sidecar is read by a node process on the owning kernel, the file's bytes by a plain
// GET, and the Edit button waits on the bytes only), so begin() had nothing to hand the editor, and the status lands while
// it is up. The editor shows the text with no marks; its Save would write an empty record list back over the sidecar and
// drop every change with no decision logged, and the trace would call it a plain edit. So Save refuses on the same condition
// (saveThroughComments), whether or not the panel is open, and the row says what is left, as CHANGES_MOVED_UNDER_EDIT does:
// copy, Cancel, Edit again — the second Edit carries the changes in. One row per edit (changesUnreadUnderEdit); retired
// when the edit ends (paintAll). Edit is not refused while the status is out: the ask has no bound a plain file should
// wait on (STATUS_DEADLINE_MS on a kernel from before this feature), and a plain file's Edit works as it always did.
export const CHANGES_UNREAD_UNDER_EDIT = "This file has pending changes that were read only after you opened the editor, so it does not show them. "
  + "Save will refuse; copy anything you typed, then Cancel and Edit again.";
// How long a `status` ask may stay unanswered before the panel says so. A kernel that has the op answers
// within its own bound: the host script is cut off at 10 s (contract C2, _FILE_COMMENTS_TIMEOUT) and the
// refusal is sent then, so an ask still open past that plus the relay was never received by a kernel with
// the handler — a kernel from before this feature matches no `type` and sends nothing, not even a warn, and
// federation's drop notice covers only an UNREACHABLE host, not a reachable one that has no answer. There is
// no event to key on because the older kernel emits none; the timer speaks only when the answer never comes
// (feed.ts's redistill watch is the same shape, and ui/CLAUDE.md wants every wait to have a backstop).
// `status` only: a mutating verb that is failed here could have landed on disk, and the kept note would
// invite a duplicate — those keep waiting for the kernel's own answer.
const STATUS_DEADLINE_MS = 15000;
// One send answers a todo (decision 28): a todo naming several files is answered by the FIRST send, and
// later sends for its other files show no checkbox. A viewer is built per open, so the memory of which
// todos THIS page has sent for lives at module level — a second file opened from the same todo, a Reload
// (which re-opens with the same todoId), or the Reply modal's other link all find it. The todo-file follow-on
// made the kernel list the open todos naming the file on every status, and stop once the todo is settled — so
// for a LISTED todo this set covers the moment between the send and the next status only: a status ISSUED after
// the send's reply landed that still lists the todo is the kernel's word that the todo is open (CLAUDE.md, the
// authoritative source) — a parked send stamps only when it drains, not when it is accepted, and a recalled or
// lost answer reopens the todo (kernel _reopen_user_todo) — and applyStatus releases the memory for it, so the
// confirm offers it again as Waiting on you shows it. Before that release a todo the kernel had reopened stayed
// hidden from every confirm on the page until a reload (the review, 2026-09-07). The release is keyed on the
// request counter, not the clock: `answeredAt` holds reqSeq as it stood at the latch, and a status whose reqId
// is past it was issued after the reply (markOverlapped has already flagged every status still out at that
// moment, so an earlier ask that lands later is dropped or, when its clocks prove it newer, applied WITHOUT
// releasing: it may have read the store before the stamp). What the set keeps for good is the todo the file
// was opened from whose `file` is another file: no status of this viewer lists it, and decision 28 wants later
// sends to show no box for it. Another device or document has no view of this set; the kernel's own settled
// check (plan: the reply warns, nothing is stamped) stays the backstop there.
const answeredTodos = new Set<string>();
const answeredAt = new Map<string, number>();

// ── image embeds: the source text behind a rendered <img> ─────────────────────────────────────────
// A figure in a markdown file is commented on through its embed line (the plan's Images and PDFs): in
// Rendered view a click on the picture offers Comment, and the anchor is the embed's source text. The
// mapping walk records no positions for an image (it renders no text), so the embed is found here from
// the picture's own destination (pictureDest: the authored spelling the viewer kept beside a src it
// rewrote through /file, else `src` itself): every embed form the source can hold, in order, fenced code
// skipped, matched against the attribute marked emitted (which percent-encodes the destination).
export type ImageEmbed = { start: number; end: number; dest: string };
const LABEL = "(?:\\\\.|[^\\[\\]\\\\])*";
const IMG_INLINE = new RegExp("!\\[(" + LABEL + ")\\]\\([ \\t]*(?:<([^<>\\n]*)>|([^\\s()]*(?:\\([^\\s()]*\\)[^\\s()]*)*))(?:[ \\t]+(?:\"[^\"]*\"|'[^']*'|\\([^()]*\\)))?[ \\t]*\\)", "g");
const IMG_FULL_REF = new RegExp("!\\[(" + LABEL + ")\\]\\[(" + LABEL + ")\\]", "g");
const IMG_SHORT_REF = new RegExp("!\\[(" + LABEL + ")\\](?![\\[(])", "g");
const IMG_HTML = /<img\b[^>]*?\bsrc[ \t]*=[ \t]*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))[^>]*>/gi;
const REF_DEF = /^ {0,3}\[((?:\\.|[^\[\]\\])+)\]:[ \t]*<?([^\s>]+)>?/gm;
const normLabel = (s: string): string => s.trim().replace(/\s+/g, " ").toLowerCase();
/** Offsets of the source's fenced code blocks, [start, end): an embed written inside one renders as text. */
function fencedRanges(src: string): Array<[number, number]> {
  const out: Array<[number, number]> = [];
  let open: { ch: string; n: number; at: number } | null = null;
  let at = 0;
  for (const line of src.split("\n")) {
    const m = /^ {0,3}(`{3,}|~{3,})/.exec(line);
    if (m) {
      if (!open) open = { ch: m[1][0], n: m[1].length, at };
      else if (m[1][0] === open.ch && m[1].length >= open.n && /^\s*$/.test(line.slice(m[0].length))) { out.push([open.at, at + line.length]); open = null; }
    }
    at += line.length + 1;
  }
  if (open) out.push([open.at, src.length]);
  return out;
}
/** Every image embed in the source, in order: `![alt](dest "title")`, `![alt][ref]` and `![ref]` resolved
 *  through `[ref]: dest` definitions, and a raw `<img src>` tag. Fenced code is skipped. */
export function imageEmbeds(src: string): ImageEmbed[] {
  const fences = fencedRanges(src);
  const inFence = (i: number): boolean => fences.some(([a, b]) => i >= a && i < b);
  const defs = new Map<string, string>();
  let m: RegExpExecArray | null;
  REF_DEF.lastIndex = 0;
  while ((m = REF_DEF.exec(src))) if (!inFence(m.index)) defs.set(normLabel(m[1]), m[2]);
  const out: ImageEmbed[] = [];
  const push = (start: number, len: number, dest: string | undefined): void => {
    if (dest !== undefined && !inFence(start)) out.push({ start, end: start + len, dest });
  };
  for (const re of [IMG_INLINE, IMG_FULL_REF, IMG_SHORT_REF, IMG_HTML]) re.lastIndex = 0;
  while ((m = IMG_INLINE.exec(src))) push(m.index, m[0].length, m[2] ?? m[3] ?? "");
  while ((m = IMG_FULL_REF.exec(src))) push(m.index, m[0].length, defs.get(normLabel(m[2] || m[1])));
  while ((m = IMG_SHORT_REF.exec(src))) push(m.index, m[0].length, defs.get(normLabel(m[1])));
  while ((m = IMG_HTML.exec(src))) push(m.index, m[0].length, m[1] ?? m[2] ?? m[3] ?? "");
  out.sort((a, b) => a.start - b.start);
  return out.filter((e, i) => !i || e.start >= out[i - 1].end);   // a shortcut form inside a longer one: the longer wins
}
/** Whether a source destination is the `src` marked emitted for it (marked percent-encodes; either side may be encoded). */
export function sameDest(dest: string, src: string): boolean {
  if (dest === src) return true;
  try { if (encodeURI(dest).replace(/%25/g, "%") === src) return true; } catch { /* a lone surrogate */ }
  try { return decodeURI(dest) === decodeURI(src); } catch { return false; }
}
/** A path with `.` and `..` folded, a leading slash kept, repeated slashes collapsed — for comparing two spellings, never for reading. */
export function normPath(p: string): string {
  const abs = p.startsWith("/");
  const out: string[] = [];
  for (const seg of p.split("/")) {
    if (!seg || seg === ".") continue;
    if (seg === "..") { if (out.length && out[out.length - 1] !== "..") out.pop(); else if (!abs) out.push(".."); continue; }
    out.push(seg);
  }
  return (abs ? "/" : "") + out.join("/");
}
const decoded = (s: string): string => { try { return decodeURIComponent(s); } catch { return s; } };
// An embed's dest is decoded with decodeURI, as the viewer decodes it before it loads the picture (file-view.ts
// rewriteFigureSrcs), the poll before it HEADs the figure (file-comments-model.ts figurePath) and the host before it
// hashes it: the three readers of a destination must name one file. decodeURIComponent, which stood here first, also
// decodes the escapes of RESERVED characters, so `a%26b.png` became `a&b.png` on this side and stayed `a%26b.png` on
// the viewer's — and a figure written with such an escape never matched its embed once rewritten through /file (the
// drag refused, the embed-line frame unpainted, the picture click's offer a whole-file comment). fileUrlPath keeps
// decodeURIComponent: fileUrl built its `path` with encodeURIComponent, and that is the exact inverse there.
const decodedDest = (s: string): string => { try { return decodeURI(s); } catch { return s; } };
/** Where an embed's `dest`, as written, points relative to the markdown file at `filePath` (absolute dest: itself). */
export function embedPath(filePath: string, dest: string): string {
  const d = decodedDest(dest);
  if (d.startsWith("/")) return normPath(d);
  return normPath(filePath.slice(0, filePath.lastIndexOf("/") + 1) + d);
}
/** The `path` a /file (or /remote/<host>/file) URL names, decoded; null for any other URL. */
export function fileUrlPath(src: string): string | null {
  const q = src.indexOf("?");
  if (q < 0 || !/(^|\/)file$/.test(src.slice(0, q))) return null;
  for (const kv of src.slice(q + 1).split("&")) if (kv.startsWith("path=")) return decoded(kv.slice(5));
  return null;
}
/** Whether a rendered picture's `src` is the embed's `dest`: as marked emitted it (either side percent-encoded),
 *  or as the viewer rewrote it through /file against the file's directory so the figure loads from the kernel
 *  (contract E4) — the two spellings name one path. */
export function srcIsEmbed(src: string, dest: string, filePath: string | null | undefined): boolean {
  if (sameDest(dest, src)) return true;
  const p = fileUrlPath(src);
  return p !== null && typeof filePath === "string" && normPath(p) === embedPath(filePath, dest);
}
const imgsIn = (root: Element): HTMLElement[] => Array.from(root.querySelectorAll("img")) as HTMLElement[];
/** The destination a rendered picture was written with: the authored attribute the viewer keeps as `data-fv-src` when it
 *  rewrites `src` through /file (file-view.ts rewriteFigureSrcs), else `src` itself — a picture the viewer left as written.
 *  Null for a picture with neither. */
export function pictureDest(img: Element): string | null {
  const kept = img.getAttribute("data-fv-src");
  return kept !== null ? kept : img.getAttribute("src");
}
/** Whether a rendered picture came from an embed written as `dest`: srcIsEmbed over the picture's own spelling. With the
 *  authored spelling in hand this is sameDest, so `./fig.png` and `fig.png` — two embeds of ONE file — stay two
 *  destinations, each with its own picture; the /file-path comparison serves only a rewritten picture that carries no
 *  authored spelling. The ONE test every reader of the picture↔embed pairing uses (embedFor, imgForRange, the region
 *  painter's fallbacks), so they cannot disagree about which picture an embed made. */
export function pictureIsEmbed(img: Element, dest: string, filePath?: string | null): boolean {
  const s = pictureDest(img);
  return s !== null && srcIsEmbed(s, dest, filePath);
}
/** The embed the picture at `img` came from, given every embed and every picture: the embeds written as the picture's
 *  destination, and among them, by order — the k-th picture of that destination is its k-th embed. */
function embedOf(img: HTMLElement, imgs: HTMLElement[], all: ImageEmbed[], filePath?: string | null): ImageEmbed | null {
  if (pictureDest(img) === null) return null;
  const hits = all.filter((e) => pictureIsEmbed(img, e.dest, filePath));
  if (hits.length === 1) return hits[0];
  if (!hits.length) return null;
  const k = imgs.filter((i) => pictureIsEmbed(i, hits[0].dest, filePath)).indexOf(img);
  return k >= 0 && k < hits.length ? hits[k] : null;
}
/** The embed a rendered picture came from: by destination, and among twins by order. Null when the source holds none.
 *  `filePath` lets a src the viewer rewrote through /file match its embed (srcIsEmbed) when the picture carries no
 *  authored spelling (pictureDest). Before the rewrite, the hits were found by path (two spellings of one file matched
 *  either picture) while the twins were counted by the rewritten `src` (which the two spellings made different): a
 *  region drawn on the second figure was anchored to the first's embed line, and imgForRange, counting the other way
 *  round, painted the second embed's rectangle on the first figure (the 2026-09-06 review). Both now pair through
 *  embedOf, and imgForRange is embedFor's inverse by construction. */
export function embedFor(img: Element, root: Element, src: string, filePath?: string | null): ImageEmbed | null {
  return embedOf(img as HTMLElement, imgsIn(root), imageEmbeds(src), filePath);
}
/** The rendered picture for an embed's exact source range — the inverse, for painting: the picture whose embedFor is
 *  that embed. Null when no picture came from it (the range is not an embed's, or the source holds more embeds of the
 *  destination than the view holds pictures). */
export function imgForRange(root: Element, src: string, range: SourceRange, filePath?: string | null): HTMLElement | null {
  const all = imageEmbeds(src);
  const e = all.find((x) => x.start === range.start && x.end === range.end);
  if (!e) return null;
  const imgs = imgsIn(root);
  return imgs.find((i) => embedOf(i, imgs, all, filePath) === e) || null;
}
// A framed picture wears the mark classes itself (an <img> has no text to wrap) plus an inline outline, because the
// sheets' ring is an inset shadow the picture covers. `fc-img` tells unpaint to strip, not unwrap. Being inline, the
// outline outranks every plain sheet rule, the print block's `outline: none` on the marks included, so the block has to
// strip a framed picture with `!important` (`.fileview-body img.fc-img`, styles.css and feed.css): without that a
// comment on a figure printed as an amber ring around the picture while the comment itself was hidden with the aside
// (Slice 3 review, round 2; file-view-print-marks-browser.test.ts measures it).
function styleFrame(img: HTMLElement): void {
  const presel = img.classList.contains("fc-presel");
  const dashed = !presel && img.classList.contains("fc-hl-context");
  img.style.outline = "2px " + (dashed ? "dashed" : "solid") + " " + (presel ? "var(--accent)" : "var(--warn)");
  img.style.outlineOffset = "2px";
}
function frameImage(img: HTMLElement, cls: string, data?: Record<string, string>): void {
  img.classList.add("fc-img", ...cls.split(" ").filter(Boolean));
  if (data) for (const k of Object.keys(data)) img.dataset[k] = data[k];
  styleFrame(img);
}
function unframeImage(img: HTMLElement, marks: string[]): void {
  img.classList.remove(...marks);
  if (img.classList.contains("fc-hl") || img.classList.contains("fc-presel")) { styleFrame(img); return; }
  img.classList.remove("fc-img", "fc-hl-context");
  img.style.outline = ""; img.style.outlineOffset = "";
  delete img.dataset.act; delete img.dataset.id;
}
/** Whether a selection end (`node`, `offset`) lies inside the mark `x`, or at one of its edges (Panel.dragClick). A drag
 *  that ends at the mark's boundary may be reported by the engine not as a point inside the mark but as one in the mark's
 *  parent, at the mark's index (its start) or the next (its end), or at the end of the text node before the mark or the
 *  start of the one after it: the same caret, another node. Any other node is outside the mark. */
function endInside(x: Element, node: Node, offset: number): boolean {
  if (x.contains(node)) return true;
  const p = x.parentNode;
  if (!p) return false;
  if (node === p) { const i = Array.prototype.indexOf.call(p.childNodes, x); return offset === i || offset === i + 1; }
  if (node.nodeType === 3) {
    if (node === x.previousSibling) return offset === (node as Text).length;
    if (node === x.nextSibling) return offset === 0;
  }
  return false;
}

function el(tag: string, cls?: string, text?: string): HTMLElement {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}
function btn(label: string, act: string, cls = "fileview-btn"): HTMLButtonElement {
  const b = el("button", cls, label) as HTMLButtonElement;
  b.type = "button";
  b.dataset.act = act;
  return b;
}
/** A comment id inside a selector's quoted attribute value. The ids are sidecar data — a session's tools mint them, a hand
 *  can write them — and nothing on the read path constrains their grammar, so a `"` or `\` in one made querySelector throw,
 *  and on the render path (placeComposer) that stopped every section after the cards from refreshing while the reply was
 *  open; inside the margin pass (placeCards ownMarks), which every render runs, it left every card without a top and the
 *  failure surfaced nowhere (both found in the 2026-09-07 reviews). CSS.escape where the platform has it (every browser
 *  the panel runs in); for a stand-in without it, the two characters a quoted value cannot hold raw. */
function cssId(s: string): string {
  return typeof CSS !== "undefined" && typeof CSS.escape === "function" ? CSS.escape(s) : s.replace(/["\\]/g, "\\$&");
}
const clock = (t: number | string): string => {
  const d = new Date(t);
  if (isNaN(d.getTime())) return "";
  const today = new Date();
  const sameDay = d.getFullYear() === today.getFullYear() && d.getMonth() === today.getMonth() && d.getDate() === today.getDate();
  const hm = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  return sameDay ? hm : d.toLocaleDateString([], { month: "short", day: "numeric" }) + " " + hm;
};
// a pane the shell has hidden gives its iframe a ZERO viewport (document.hidden stays false there) — the
// Sessions pane's gate, reused: skip the tick while hidden, catch up once on the first visible moment
const paneHidden = (): boolean => document.hidden || window.innerWidth === 0 || window.innerHeight === 0;

// `overlapped`: a status ask still unanswered when a write's reply landed (markOverlapped) — its host run may
// have read the disk before that write, whatever its place in line
type Pending = { verb: string; ok: (m: Record<string, unknown>) => void; fail: (e: { code: string; error: string }) => void; deadline?: ReturnType<typeof setTimeout>; overlapped?: boolean };
/** A status reply as the panel applies it: the kernel's fields plus the reqId of the ask it answers, and
 *  whether that ask overlapped a write (see Pending). */
type Reply = Status & { reqId: number; overlapped?: boolean };

// ── which of two status replies read the disk later ────────────────────────────────────────────────
// Mtimes are decimal nanosecond strings (~1.7e18 exceeds JS's safe integers, so they never become numbers):
// digit strings order by length, then by text. A value beats null (a sidecar or config that now exists is a
// later reading than one that says it does not); anything that is not digits is no clock and claims nothing.
function laterNs(a: string | null | undefined, b: string | null | undefined): boolean {
  if (!a) return false;
  if (!b) return true;
  if (!/^\d+$/.test(a) || !/^\d+$/.test(b)) return false;
  return a.length !== b.length ? a.length > b.length : a > b;
}
/** Did `a` read a LATER disk than `b`? True when any of the file, the sidecar or the config moved forward. */
export function newerStatus(a: Status, b: Status): boolean {
  return laterNs(a.fileMtimeNs, b.fileMtimeNs) || laterNs(a.storeMtimeNs, b.storeMtimeNs) || laterNs(a.configMtimeNs, b.configMtimeNs);
}
/** Did `a` PROVABLY read a later disk than `b` — the question for a SUSPECT reply (applyStatus)? newerStatus lets a
 *  value beat null, which is right for a sidecar or config seen for the first time; but a suspect reply's value
 *  against an applied null is as likely a reading from BEFORE the deletion that emptied it: a decision that pruned the
 *  sidecar (the host's pruneIfClean, after an accept-all or a last accept or reject with no comments left), or one of
 *  the vendored CLIs deleting it. The clocks cannot tell the two apart, so a clock `b` does not hold claims nothing
 *  here; the file's clock (never null) and any clock both readings hold decide. A reading dropped this way is not
 *  lost: absent → present is a transition the poll sees and re-reads. Applied, it would put the decided changes
 *  back as cards with live buttons over a sidecar the host has deleted. */
export function provablyNewer(a: Status, b: Status): boolean {
  const held: Status = { ...a };
  if (b.storeMtimeNs === null || b.storeMtimeNs === undefined) held.storeMtimeNs = null;
  if (b.configMtimeNs === null || b.configMtimeNs === undefined) held.configMtimeNs = null;
  return newerStatus(held, b);
}

// ── a path the panel prints inline ─────────────────────────────────────────────────────────────────
// Chromium breaks a line at neither a slash nor anywhere inside an unbroken token, and a flex item's automatic
// minimum size is that token, so a path wider than the aside's 340px (about 55 characters) pushed .fc-panel
// into a horizontal scrollbar: the folder button of the tracking choice, the folder-off confirm, and any error
// row naming a path. The path is appended as text with a <wbr> after every `/` — a break where a reader would
// put one, and no change to textContent — with `overflow-wrap: anywhere` behind it for a single component
// wider than the aside (it also lets the item's minimum size shrink below the token).
/** The path split after every `/`: "/a/b/c.md" → ["/", "a/", "b/", "c.md"]. */
export function pathSegments(path: string): string[] {
  return path.match(/[^/]*\/|[^/]+$/g) || [];
}
function appendPath(node: HTMLElement, path: string): void {
  pathSegments(path).forEach((seg, i) => {
    if (i) node.appendChild(document.createElement("wbr"));
    node.appendChild(document.createTextNode(seg));
  });
  node.style.overflowWrap = "anywhere";
}
/** A .fileview-btn is `flex: 0 0 auto`, one line, right for "Reload" and wrong for a label carrying a path:
 *  this one may shrink to its row and wrap inside, its lines starting at the left like the text around it. */
function shrinkable(b: HTMLElement): void {
  b.style.flex = "0 1 auto"; b.style.minWidth = "0"; b.style.textAlign = "left";
}
// A passage comment's `range` indexes `text` — the source the selection was made over, or the reload the
// passage was followed into (retargetComposer) — so the anchor is always built over the text the offsets
// belong to, never over whatever sits at those offsets now. `text` travels with every non-null range.
// `tied` is set when the pair is stale because the current text holds the passage intact in more than one
// place its anchor cannot tell apart (followPassage): the pair is kept, nothing is painted, the chip says
// so, and Save sends the anchor with NO offset, since the range's start indexes other text and would settle
// the tie by coincidence; the host refuses a tie it cannot settle (anchor-ambiguous) and the note stays.
// `elsewhere` is set when the pair is stale because the edit reached the passage and its text is now intact
// only at a copy the edit never touched (followPassage): the pair is kept, nothing is painted, the chip says
// so, and Save is refused here — the host, given one hit, would place the note on that other copy.
/** The changes a comment being written is ABOUT (the about follow-on, 2026-09-10): the pending changes whose marks the
 *  selection overlaps (overlapping), or the change whose card's Comment on this change opened the box. `on` is the box's
 *  option, checked when the box opens; unchecked, the save is a plain passage comment. `only` when no passage can carry the
 *  comment (a deletion, whose text is not in the file; a detached change): the box offers the comment about the change
 *  alone, says so in one line, and the save carries the ids with no anchor. */
type About = { ids: string[]; on: boolean; only: boolean };
type Composer =
  | { kind: "comment"; range: SourceRange | null; quote: string | null; text?: string; tied?: boolean; elsewhere?: boolean; about?: About; refusal: (MapRefusal & { selText: string }) | null }
  // `resolved`: whether the comment was already resolved when the reply began — the slot's row tells a comment resolved
  // since the reply began from one whose Resolved fold the person closed (replyAway)
  | { kind: "reply"; commentId: string; ref: string; resolved: boolean }
  // a region drawn on a picture (Slice 3): `img` is the picture (re-found after a repaint), `src` and `range` the
  // embed's dest and source range for a figure in rendered markdown (null for a standalone image), `text` the
  // source the range indexes; `refusal` when the figure's embed line could not be found (nothing to anchor to);
  // `page` the 1-based page when the picture is a PDF page's canvas (Slice 4), null otherwise
  | { kind: "region"; img: Pictured; region: Region; page: number | null; src: string | null; range: SourceRange | null; text?: string; tied?: boolean; elsewhere?: boolean; refusal: string | null }
  // Re-place: the next region drawn on the comment's picture becomes its target (retarget, E3); no words. `page`
  // is the comment's current page for a PDF region (the new place may be on any page)
  | { kind: "replace"; commentId: string; ref: string; src: string | null; page: number | null };
/** Why a region on a figure cannot be saved: the anchor is the embed line, and the source holds none for this picture. */
const EMBED_NOT_FOUND = "the line that embeds this image was not found in the source, so a region on it cannot be saved";
/** The passage composer's refusal for the same figure — the picture click's Comment offer builds it (startImageComment), and
 *  Switch to Raw on a refused region turns the region composer into it: a Raw selection of the embed line places the note. */
const EMBED_NOT_FOUND_SELECT = "The line that embeds this image was not found in the source; select it in the Raw view.";
/** The composer's tag titles once the file changed under a pending passage and it now recurs where the anchor cannot tell
 *  the copies apart (`tied`): the person picks the copy again; Save meanwhile carries no offset and the host refuses a tie. */
const PASSAGE_TIED = "The file changed and this passage now occurs in it more than once with the same surroundings, so the copy you selected cannot be told apart; Save asks the file's machine to place it, and refuses if the copies still tie. Select the passage again to pick the copy.";
const EMBED_TIED = "The file changed and the line embedding this figure now occurs in it more than once with the same surroundings, so the one you drew on cannot be told apart; Save asks the file's machine to place it, and refuses if the copies still tie. Draw the region again to pick the figure.";
/** The composer's tag titles once the file changed where the pending passage was, and its text is now intact only at a copy
 *  the edit never touched (`elsewhere`): the person picks the passage again; Save meanwhile is refused here (saveComposer). */
const PASSAGE_ELSEWHERE = "The file changed where you selected this passage, and its text now occurs only elsewhere in the file, at a copy you did not select; Save is refused rather than put the note there. Select the passage again.";
const EMBED_ELSEWHERE = "The file changed where you drew this region, and the line embedding this figure now occurs only elsewhere in the file, at a copy you did not draw on; Save is refused rather than put the note there. Draw the region again.";
/** Save's refusal rows for an `elsewhere` pair: the note stays, and the person selects or draws again. */
const PASSAGE_ELSEWHERE_SAVE = "Nothing saved: the file changed where you selected this passage, and its text now occurs only elsewhere in the file. Select the passage again.";
const EMBED_ELSEWHERE_SAVE = "Nothing saved: the file changed where you drew this region, and the line embedding this figure now occurs only elsewhere in the file. Draw the region again.";
/** The card's words for a highlight on a copy the panel cannot vouch for (copyUnsure): the tag's title, and a line on the
 *  open card, since a tag's title never reaches touch. */
function copyUnsureWords(c: Card): string {
  return "This passage occurs in the file more than once with the same surroundings, and "
    + (c.anchorAt === null
      ? "the comment stores no position to tell the copies apart, so the first copy is highlighted"
      : "the position stored with the comment names none of the copies as the file is now, so the copy nearest that position is highlighted")
    + " — not a confirmed one.";
}
/** The highlight's own title for that copy: the hover's shorter form of the same words, on the same branch as
 *  copyUnsureWords, so the mark and the card never disagree about whether a position is stored (the review,
 *  2026-09-08: the title claimed a stored position on a comment `track-comment` wrote, whose card said it stores none). */
function unsureMarkTitle(c: Card): string {
  return "Open the comment; this passage recurs, and "
    + (c.anchorAt === null
      ? "the comment stores no position to tell the copies apart, so this is the first copy"
      : "this copy is the nearest to the comment's stored position")
    + ", not a confirmed one";
}
/** Where a passage composer's pair — `range` into `oldText` — stands once the view shows `newText` (retargetComposer).
 *  The two texts' common prefix and suffix bound the span the edit changed: a passage wholly before that span keeps its
 *  offsets and one wholly after it moves by the span's growth, both exact — the same characters, however many copies of
 *  the passage the text holds, so a paragraph the session inserts above a recurring passage moves the note with ITS
 *  copy. Only a passage the span reaches is re-found through its anchor (the engine's 24 characters of context, built
 *  over the text the offsets index): `moved` when the quote sits intact at one best hit that lies where the edit put
 *  its text; `elsewhere` when that one hit lies wholly outside the span the edit's text occupies now — text the edit
 *  never touched, at the offsets it had before, so another copy of the passage and never the one the edit reached (the
 *  review, 2026-09-07: a session rewrote the selected copy of a sentence that recurs, the anchor re-found the other
 *  copy, and the note followed it there with no tag); `tied` when it sits intact at several the anchor cannot tell
 *  apart — the engine's earliest and latest tied hits (hint 0, hint length) differ — a choice the old offset must not
 *  make, since nearest-to-an-offset-into-other-text picks by coincidence (the re-find did exactly that until
 *  2026-09-07: an insertion above longer than half the gap between two copies moved the note to the other copy, and
 *  the host, now settling a hinted tie, saved it there); `gone` when the quote is intact nowhere. */
export type Followed = { state: "moved"; range: SourceRange } | { state: "tied" } | { state: "gone" } | { state: "elsewhere" };
export function followPassage(oldText: string, range: SourceRange, newText: string): Followed {
  const oldLen = oldText.length, newLen = newText.length, min = Math.min(oldLen, newLen);
  let p = 0;
  while (p < min && oldText.charCodeAt(p) === newText.charCodeAt(p)) p++;
  let s = 0;
  while (s < min - p && oldText.charCodeAt(oldLen - 1 - s) === newText.charCodeAt(newLen - 1 - s)) s++;
  if (range.end <= p) return { state: "moved", range: { start: range.start, end: range.end } };
  if (range.start >= oldLen - s) { const d = newLen - oldLen; return { state: "moved", range: { start: range.start + d, end: range.end + d } }; }
  const anchor = makeAnchor(oldText, range);
  const first = locateComment(newText, anchor, 0);
  if (first.state !== "located" || !first.range) return { state: "gone" };
  const last = locateComment(newText, anchor, newLen);
  if (last.state === "located" && last.range && last.range.start === first.range.start) {
    // one best hit: the passage only where the edit's text now sits, [p, newLen - s); wholly outside it is untouched text
    if (first.range.end <= p || first.range.start >= newLen - s) return { state: "elsewhere" };
    return { state: "moved", range: first.range };
  }
  return { state: "tied" };
}
/** Why the head of the card holding a reply does not fold it: the head's title, and on a coarse pointer the line under the head
 *  (holdHead, heldNote) — one sentence for both, so the pointer and the touch read the same words. */
const HOLD_WORDS = "The card stays open while its reply is written; Save or Cancel the reply first";
/** The row under a control whose write the file-editing consent refused (mutate; resolveAnswered and reopenAnswered ask once for
 *  their run and put the one row under the header action). */
const CONSENT_REFUSED = "Nothing written: comments need file editing on.";
// ── the composer's box (the follow-on of 2026-09-07: a comment is often several lines) ──────────────
/** The box starts at this many rows (the sheets' min-height says the same in em) and grows with its content to the cap,
 *  COMPOSER_MAX_ROWS rows, then scrolls. The cap is autosizeComposer's alone, not a max-height in the sheets: the person
 *  may also drag the box's handle (resize: vertical), past the cap too, and a sheet clamp would take the drag with it. */
export const COMPOSER_ROWS = 3;
export const COMPOSER_MAX_ROWS = 12;
/** The Send confirm's note box grows to this many rows, then scrolls (the user's ruling, 2026-09-09: about eight). */
export const SEND_NOTE_ROWS = 8;
/** Which modifier the save chord uses: Cmd on macOS, Ctrl elsewhere — the editor's modifier rule (the IS_MAC of its
 *  marks module, the same test; that module stays in the lazy chunk, so the test is repeated here rather than imported),
 *  detected once. Only the HINT reads it: either modifier saves on every platform. */
const IS_MAC = typeof navigator !== "undefined" && /Mac|iP(?:hone|ad|od)/.test(navigator.platform || "");
export type ComposerKey = "save" | "cancel" | null;
/** What a keydown in the box means, pure: Escape cancels; Enter with Cmd or Ctrl saves — the chat composer's chord,
 *  either modifier everywhere, so Ctrl+Enter on a Mac saves too; a plain or Shift+Enter is the browser's own newline
 *  (null: not ours); a key pressed while an IME is composing is the IME's. */
export function composerKeyAction(e: { key: string; metaKey?: boolean; ctrlKey?: boolean; isComposing?: boolean }): ComposerKey {
  if (e.isComposing) return null;
  if (e.key === "Escape") return "cancel";
  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) return "save";
  return null;
}
/** The chord the hint under the box names, in the platform's words. */
export function saveChord(mac: boolean): string { return (mac ? "Cmd" : "Ctrl") + "+Enter"; }
/** The hint on a coarse pointer (a phone, a tablet): a soft keyboard has no modifier to hold, so a chord would name a
 *  key the device lacks, and the person who pressed Return for the old one-line box's save got a newline and no word on
 *  what saves now. The hint names the button beside it instead — the chat composer's rule for its own placeholder
 *  (render.ts composerRestingPlaceholder drops the key chart on a coarse pointer), and decideInEditor's for a tap. */
export const COMPOSER_HINT_TOUCH = "Enter adds a line; tap Save when done";
/** The hint under the box, in the device's words: the platform's chord with a keyboard, COMPOSER_HINT_TOUCH on a coarse
 *  pointer. `touch` defaults to the device's answer (isCoarsePointer), read at each call — the hint is built per render,
 *  and the primary pointer can change (a tablet docks to a keyboard and trackpad), as decideInEditor reads it too; a
 *  test passes it. */
export function composerHint(mac: boolean, touch: boolean = isCoarsePointer()): string {
  return touch ? COMPOSER_HINT_TOUCH : saveChord(mac) + " saves; Enter adds a line";
}
/** Size the box to its content: height auto, then the scroll height — capped at COMPOSER_MAX_ROWS rows of the box's
 *  computed line-height plus its padding (rowCap), past which the box scrolls — plus the border (box-sizing: border-box).
 *  The sheet's min-height floors it at COMPOSER_ROWS. The cap is here and not a max-height in the sheet because the
 *  person's resize drag and this function write the same inline height: a sheet clamp capped the drag too, so a drag at
 *  the cap could not make the box taller yet read as a drag (Panel.autosize), and the box froze at the cap for the rest
 *  of the comment (the 2026-09-07 review). Returns the inline height as the box holds it after the write — read back,
 *  not the string written: Chromium serializes a written 199.82399999999998px as 199.824px, and Panel.autosize tells a
 *  drag from this function's own last write by comparing the inline height to this return — or null when the box has no
 *  layout to measure (hidden, or a document with no renderer), in which case the inline height it had is put back.
 *
 *  The measurement leaves the page's scroll where it found it. `height: auto` collapses a grown box to its rows for the
 *  read, and the layout that read forces is up to nine rows shorter: a scrolled ancestor near its bottom — the panel's
 *  aside, which is short on the phone and in a short pane — is clamped in it, and putting the height back does not put
 *  the scroll back (with cards below the box the browser's anchoring over-corrects the other way instead). Every keystroke
 *  in a grown box jumped the panel toward its top, the Save row and the cards the person had scrolled to leaving the
 *  viewport. So the scrolled ancestors' positions are read first and written back last, on both paths. */
export function autosizeComposer(ta: HTMLTextAreaElement, maxRows = COMPOSER_MAX_ROWS): string | null {
  const prev = ta.style.height;
  const held = scrolledAncestors(ta);
  ta.style.height = "auto";
  const sh = ta.scrollHeight;
  if (!(sh > 0)) { ta.style.height = prev; restoreScroll(held); return null; }
  const border = Math.max(0, (ta.offsetHeight || 0) - (ta.clientHeight || 0));
  ta.style.height = Math.min(sh, rowCap(ta, maxRows)) + border + "px";
  restoreScroll(held);
  return ta.style.height;
}
/** The scroll height of a box at the cap: COMPOSER_MAX_ROWS rows of its computed line-height plus its vertical padding
 *  (scrollHeight counts the padding, not the border). Infinity — no cap — where the row height cannot be read: a document
 *  with no computed style (the panel tests' stand-in), or a box no sheet reaches, which has no floor either. */
function rowCap(ta: HTMLTextAreaElement, maxRows = COMPOSER_MAX_ROWS): number {
  const win = typeof window !== "undefined" ? window : null;
  if (!win || typeof win.getComputedStyle !== "function") return Infinity;
  const cs = win.getComputedStyle(ta);
  const lh = parseFloat(cs.lineHeight);
  if (!(lh > 0)) return Infinity;
  return maxRows * lh + (parseFloat(cs.paddingTop) || 0) + (parseFloat(cs.paddingBottom) || 0);
}
/** The ancestors scrolled down from their top, with how far: the only ones a shorter layout can clamp. */
function scrolledAncestors(el: Element): Array<[Element, number]> {
  const out: Array<[Element, number]> = [];
  for (let p = el.parentElement; p; p = p.parentElement) if (p.scrollTop > 0) out.push([p, p.scrollTop]);
  return out;
}
function restoreScroll(held: Array<[Element, number]>): void {
  for (const [p, top] of held) if (p.scrollTop !== top) p.scrollTop = top;
}
/** The PDF page an element is (Slice 4): the chunk stamps `data-page` (1-based) on each page's canvas and on the page's
 *  shell (div.fileview-pdf-page), and ONLY those two carry a page — an <img> never does, whatever its markup says. The
 *  sanitizer keeps a rendered figure's data-* attributes (owns() relies on that for data-act), so a raw
 *  `<img src="figure.png" data-page="2">` a session wrote into markdown reached here as page 2 of a PDF: the composer
 *  named a page, regionTarget dropped the embed's src for kind "pdf", and the host refused the comment for the missing
 *  src (a region on an embedded figure needs it). Null for anything else, and for a carrier without a positive integer. */
export function pageOf(el: Element | null | undefined): number | null {
  if (!el) return null;
  const cl = el.classList;
  const shell = !!cl && typeof cl.contains === "function" && cl.contains("fileview-pdf-page");
  if (!isCanvas(el) && !shell) return null;
  const raw = (el as HTMLElement).dataset ? (el as HTMLElement).dataset.page : undefined;
  const n = raw === undefined || raw === null ? NaN : Number(raw);
  return Number.isInteger(n) && n >= 1 ? n : null;
}
/** The scroller a PDF page's shell lives in — the nearest ancestor that scrolls vertically (the viewer's body, overflow
 *  auto), stopping under the document's body and root — or null for the viewport when none does. The page watch's root
 *  (watchPages): pdf-chunk.ts's scrollRootFor, for the same reason and with the same stopping rule, but the chunk's exports
 *  stay out of the main bundles (its contract is the window global), so the walk is repeated here. */
function scrollerOf(el: Element | null): Element | null {
  const win = typeof window !== "undefined" ? window : null;
  if (!win || typeof win.getComputedStyle !== "function") return null;
  for (let p = el ? el.parentElement : null; p && p !== document.body && p !== document.documentElement; p = p.parentElement) {
    const s = win.getComputedStyle(p);
    if (/^(auto|scroll|overlay)$/.test(s.overflowY || s.overflow || "")) return p;
  }
  return null;
}
type Err = { text: string; reload: boolean; warn?: boolean };
/** A focused control by what it IS (focusKey / refocus): its action and the id, key or slot naming its subject, plus,
 *  for one in the cards list, the card it sat on and that card's place — where the keyboard goes when the control
 *  comes back disabled or not at all. */
type FocusKey = { act: string; id?: string; key?: string; slot?: string; card?: string; at?: number };

// ── why a region's staleness is unknown ─────────────────────────────────────────────────────────────
// The host puts a reason beside every hash it could not take (fileHashFor / embeddedHashesFor in the host script:
// `fileHashReason` for a media file, `embeddedHashReasons[src]` for a figure a text file's comments name), because the
// kernel keeps the host's stderr only when a call fails — the reason reaches the panel in the reply or not at all. The
// Status type (file-comments-model.ts) names the hashes; the reasons are read off the same reply here, where the card
// is the one thing that shows them: the tag's title collapsed, a sentence in the open card (a title never reaches touch,
// the caption idiom of renderSend). Unknown also has causes the host cannot explain, each named in its own words: a
// comment saved without a hash, a host from before region comments (no hash field at all). Never a bare "unknown": a
// deleted figure, one moved outside the project and one past the hash cap are three different things for the person to
// do (CLAUDE.md: surface the error, never degrade silently).
// A text file's reply carries a third kind of reason, per COMMENT rather than per src (`derivedSrcReasons`, the host's
// derivedSrcsFor): the contract's own shape for an embedded figure is the embed line's anchor plus `{kind, region, hash}`
// with no `src` (the plan's contract; another writer can leave it), and the host reads such a comment by its passage —
// one that embeds exactly one figure gives the reply's copy of the comment that src, so the panel never sees the gap;
// one that cannot tell (two figures on it, none, the passage gone) is left src-less and the cause filed under the
// comment's id. That cause is the answer for such a comment, and a text-file reply never carries `fileHash` — so before
// it was read here, the card blamed a kernel that had answered correctly (the "may predate region comments" sentence
// below, meant for a reply with no hash field at all) and sent the person to restart it (the 2026-09-06 review).
type HashReasons = {
  fileHashReason?: string | null; embeddedHashReasons?: Record<string, string | null> | null;
  /** a text file: per comment id, why a src-less region's passage could not tell which figure it is on */
  derivedSrcReasons?: Record<string, string | null> | null;
};
const unknownGeneric = (noun: string): string => "Whether the " + noun + " changed since this region was drawn could not be checked.";
/** The host's reason as the card shows it: capitalized, ending in a period (the host writes lowercase fragments). */
const asSentence = (s: string): string => { const t = s.trim(); return t.charAt(0).toUpperCase() + t.slice(1) + (/[.!?]$/.test(t) ? "" : "."); };
/** Whether a reply is a TEXT file's: the host puts `embeddedHashes` (an object, empty or not) on every text-file reply and
 *  `fileHash` on every media reply; a kernel from before region comments sends neither. */
const textFileReply = (r: Status & HashReasons): boolean => r.fileHash === undefined && !!r.embeddedHashes && typeof r.embeddedHashes === "object";
/** Why a region comment's staleness cannot be told (regionState "unknown"): the host's own reason when it sent one —
 *  for this comment (derivedSrcReasons), else for its figure or file (embeddedHashReasons / fileHashReason) — else the
 *  panel-side cause it can see, else the generic sentence. `commentId` keys the per-comment reason; without it only the
 *  per-src and per-file reasons are read. */
export function unknownReason(target: Target, s: Status | null, commentId?: string): string {
  const noun = target.kind === "pdf" ? "PDF" : "image";   // the file the region is on: the image, or the PDF whose page it is on
  if (typeof target.hash !== "string" || !target.hash) return "This region was saved without the " + noun + "'s hash, so a later change to the " + noun + " cannot be detected.";
  if (!s) return unknownGeneric(noun);
  const r = s as Status & HashReasons;
  const src = typeof target.src === "string" && target.src ? target.src : null;
  const derived = commentId !== undefined && r.derivedSrcReasons && typeof r.derivedSrcReasons === "object" ? r.derivedSrcReasons[commentId] : undefined;
  if (typeof derived === "string" && derived.trim()) return asSentence(derived);
  const reason = src ? (r.embeddedHashReasons && typeof r.embeddedHashReasons === "object" ? r.embeddedHashReasons[src] : undefined) : r.fileHashReason;
  if (typeof reason === "string" && reason.trim()) return asSentence(reason);
  const current = src ? (r.embeddedHashes && typeof r.embeddedHashes === "object" ? r.embeddedHashes[src] : undefined) : r.fileHash;
  if (current === undefined) {
    // a src-less region on a TEXT file with no reason filed for it: the comment names no figure (no src, and no passage
    // the host could read one from — a region left with no embed line, or a host that does not read passages). The
    // kernel answered; the "predate" sentence would send the person to restart a kernel that is current.
    if (!src && textFileReply(r)) return "This region does not name the figure it is on, so there is no figure to check for changes since the region was drawn.";
    return "The file's machine sent no hash for this " + noun + ", so whether it changed since this region was drawn could not be checked. Its kernel may predate region comments: update and restart it.";
  }
  return unknownGeneric(noun);
}
/** A region the sidecar holds MALFORMED (isRegion fails: a coordinate missing, a string, a null — a hand edit, or a foreign
 *  writer of the romp-only `target`): the card says so in words. It paints no rectangle and crops no thumbnail — a missing
 *  `h` placed a rectangle with `height: NaN%` (a declaration the browser drops: a bar with the author's chip, as if it were
 *  the region) and appended a 0×0 canvas (the 2026-09-06 review) — so the mark on the picture and the card's reference
 *  ("the region at 0.10, 0.20, 0.30, ?") never disagree. The recourse follows (regionRecourse). */
const UNREADABLE_REGION = "The region's coordinates could not be read from the comments file, so it is not drawn on the picture.";
/** The stale card's own words: the tag's title collapsed, a sentence on the open card. `noun`: the image, or the PDF
 *  (mediaNoun), whose pages the regions are on. */
const staleRegion = (noun: string): string => "The " + noun + " changed after this region was drawn, so it may no longer mark the right place.";
/** A PDF region whose page the document shown no longer has (pageGone, Slice 4): stale whatever the hashes say, and the
 *  card says which page went. */
const pageGoneRegion = (page: number | undefined): string => "The PDF changed after this region was drawn and no longer has page " + page + ".";

// ── the wire: ONE window listener for the module, dispatching to the live panel by reqId ───────────
// A reply is matched by reqId only — a REMOTE kernel's reply comes back with its sid host-prefixed
// (federation's prefixInbound), so sid equality would fail there. The one `warn` that means an
// outstanding request will never be answered is federation's drop notice (dropWarn: "<host> is
// unreachable (its kernel isn't answering) — “<type>” was not delivered"), and only when it names one
// of THIS module's ops: the kernel sends `warn` on the same socket for unrelated refusals — a rejected
// rename, a todo notice — with no reqId, and failing a request on those reported a comment that had
// succeeded on disk as failed, with the kept note inviting a duplicate. The shim's own drop event
// (romp:wsdown) fails everything outstanding, as before.
let live: Panel | null = null;
let listening = false;
const DROPPED_OPS = ["fileComments", "fileCommentsSend"];
/** The warn's text when it is federation's drop of one of this module's requests, else null. */
export function droppedRequestText(text: unknown): string | null {
  const t = typeof text === "string" ? text : "";
  return DROPPED_OPS.some((op) => t.includes("“" + op + "” was not delivered")) ? t : null;
}
function ensureListener(): void {
  if (listening) return;
  listening = true;
  window.addEventListener("message", (e: MessageEvent) => {
    const m = e.data;
    if (!m || !live) return;
    if (m.type === "fileCommentsResult" || m.type === "fileCommentsSent") live.settle(m, true);
    else if (m.type === "fileCommentsFailed" || m.type === "fileCommentsSendFailed") live.settle(m, false);
    else if (m.type === "warn") live.failAll(droppedRequestText(m.text));
  });
  window.addEventListener("romp:wsdown", () => { if (live) live.failAll("the connection dropped; try again once it returns"); });
  // Show changes inline is one preference for every viewer (settings.ts): a flip in another pane or tab — the
  // `storage` event, or the gear's same-document signal — repaints this one's marks so its header and its body
  // agree. Installed once here, with the message listener, and routed to the live panel: a listener per panel
  // would outlive the panels (onExternalSettingsChange has no remove).
  onExternalSettingsChange((s) => { if (live && live.inline !== s.changesInline) { live.inline = s.changesInline; live.paintAll(); } });
  // the filter (All · Comments · Changes) is kept the same way and reaches the live panel the same way: its own call, since the
  // toggle's line above is pinned word for word (file-comments-inline-toggle.test.ts) and a pick that changes nothing repaints nothing
  onExternalSettingsChange((s) => { if (live && live.filter !== s.commentsFilter) { live.filter = s.commentsFilter; live.paintAll(); } });
}
/** The save chord, claimed at the WINDOW in the capture phase while the live panel's box is the key's target: the first
 *  listener a keydown meets, by the DOM's phase order, not by who registered first. In the combined shell, palette-main.ts
 *  runs every bound chord from a capture listener on this pane's document, wired when the pane loaded (so ahead of
 *  anything the panel hangs on the document), and a chord with a real modifier dispatches while typing (keybindings.ts
 *  dispatchable). Ctrl+Enter and Cmd+Enter are bindable there and conflict with no shell command, so a shell command the
 *  person bound to one stopped the event before boxKey and ran instead: nothing saved, the hint under the box false. The
 *  chord typed in the box is the box's, as a bare Enter is (the shell refuses to bind that): the claim stops the event
 *  short of every other listener and hands it to boxKey, which saves. Nothing else is claimed: an Escape, a plain Enter,
 *  a composing IME's Enter and a key anywhere but the box pass untouched.
 *
 *  ONE listener for the module, added when it loads and keyed on `live` — not one per panel, added when the panel is
 *  built (the 2026-09-07 review). The chat pane runs its history keys, chat.navBack and chat.navForward, from a
 *  window-capture listener of its own (render.ts, added when that module loads, reading the same overrides store as the
 *  shell's dispatcher), and a rebind of either to Ctrl+Enter or Meta+Enter reached it: listeners on one target in one
 *  phase run in the order they were added, and stopPropagation stops none of them, so a claim added when the panel was
 *  built ran after the chat's listener had navigated — the comment saved and the session switched under the viewer.
 *  Only an earlier listener can stop a same-target one, and only with stopImmediatePropagation. This module is a static
 *  dependency of render.ts (file-view.ts imports fileCommentsAction from here; render.ts imports panelMark), so its body
 *  runs before render.ts's and this listener is added before the chat's; the feed's window listeners leave every Ctrl and
 *  Meta chord alone, and the shell's dispatcher sits on the document, behind the window in the capture phase whatever the
 *  order. A panel adds and removes nothing: dispose clears `live`, and a chord in what was its box passes on as before.
 *  The guard is for an import with no window at all (a node test of the pure helpers), where there is no keyboard. */
function claimSaveChord(ev: KeyboardEvent): void {
  const p = live;
  if (!p || composerKeyAction(ev) !== "save") return;
  if (ev.target === p.input) { ev.stopImmediatePropagation(); p.boxKey(ev); }
  else if (ev.target === p.noteBox) { ev.stopImmediatePropagation(); p.noteKey(ev); }   // the Send confirm's note box: the same chord sends (noteKey)
}
if (typeof window !== "undefined") window.addEventListener("keydown", claimSaveChord, true);

// The controls that are not <button>s — a card's head, its passage link, a Log row, a painted highlight —
// and so take Enter and Space here, through the same root the clicks use: a collapsed card is otherwise a
// dead end for the keyboard (ui/CLAUDE.md, never dead-end a compact view).
const KEY_ACTS = new Set(["fccard", "fcgoto", "fcopen", "fcchange", "fclogrow", "fcaboutfirst"]);
/** The filter's options in the header's order (the filter follow-on, 2026-09-07), and the keys that move along them: the
 *  arrows step to the next or previous option and choose it, wrapping at the ends; Home and End go to the first and last. */
const FILTERS: CommentsFilter[] = ["all", "comments", "changes"];
const FILTER_KEYS = new Set(["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home", "End"]);
/** The keys that are no gesture (gesture): Tab moves the keyboard, and a modifier pressed alone begins a chord — neither
 *  scrolls, edits or presses anything, and the key or the click that follows is the gesture. Counted as gestures, they ended
 *  the saved line before the keyboard could reach it: a Tab from the Send button removed the line the focus was moving to, and
 *  a Shift held for Shift+Tab, or a Ctrl for a Ctrl+click on the line, did the same, so no keyboard could ever press it (the
 *  review, 2026-09-09; measured in Chromium and Firefox). The arrivals line is reached the same way. */
const NAV_KEYS = new Set(["Tab", "Shift", "Control", "Alt", "AltGraph", "Meta"]);

/** Where a Rendered-view refusal's passage sits in the source, for the switch to Raw. The selection
 *  came from the REFUSED block, so the search starts at that block: a copy of the same words earlier in
 *  the file (prose saying "p95" above a table cell "p95") must not win. The text searched for is the
 *  mapper's own source slice when it has one (`rawRange`, found over the normalized text, so it carries
 *  the source's tabs and CRLFs where the DOM's selection string has spaces and LFs), else the trimmed
 *  selection; the mapper's slice stands when neither search hits. Null when the mapper saw no
 *  occurrence at all (the button then only scrolls to the block). */
export function rawTarget(src: string, r: MapRefusal & { selText: string }): SourceRange | null {
  if (!r.rawHasQuote) return null;
  const rr = r.rawRange && r.rawRange.start >= 0 && r.rawRange.end > r.rawRange.start && r.rawRange.end <= src.length ? r.rawRange : null;
  const q = rr ? src.slice(rr.start, rr.end) : r.selText.trim();
  if (!q) return rr;
  const from = typeof r.blockStartOffset === "number" ? Math.max(0, r.blockStartOffset) : 0;
  let i = src.indexOf(q, from);
  if (i < 0) i = src.indexOf(q);
  return i >= 0 ? { start: i, end: i + q.length } : rr;
}

let reqSeq = 0;

// ── the landing cue (the inline-display follow-on's review, 2026-09-07) ─────────────────────────────
// Reveal switches to Raw and centres the change's row. With Show changes inline off — or a batch the Raw painter refused
// (D4) — that row wears no mark of ours, so the person landed among a screen of identical rows with nothing saying which
// one held the change: the line number and the "marks are off" clause were in the button's title, which a finger never
// sees (ui/CLAUDE.md: never dead-end a compact view). So a Reveal that lands where the view shows no mark for its subject
// cues the LANDING ROW (landOn): the `.fv-cl` the scroll centred wears `fc-landing`, the accent wash and a 2px accent bar
// at its left edge — the focus-cue colour (ui/CLAUDE.md), never a status colour, and never a change mark's dress (the
// tint, the struck wash): the marks are off by the person's choice, and a row cue is not a change mark, so the toggle's
// contract (no change mark in either view) holds. The dress rides inline, as a framed picture's outline does (styleFrame):
// the row is the viewer's element, and the sheets dress no landing. The cue is transient by EVENT, never by clock: it
// leaves on the next paint pass (a status landed, the body re-rendered, the marks flipped — each new information the row
// may no longer fit), on the next Reveal (one landing at a time), and with the panel; a card opening or any other
// re-render of the aside alone leaves it standing, and so does scrolling away — the row is where the change is until the
// text moves. When the view DOES mark the subject there (the marks on: Raw paints every change; a comment's highlight),
// the mark is the cue and the row wears none.
const LANDING_BG = "var(--accent-wash)";
const LANDING_BAR = "inset 2px 0 0 var(--accent)";

// ── the panel's marks, for listeners that never see a panel ─────────────────────────────────────────
// Every element a panel paints into the file's body — a highlight, a change mark, a picture frame, a rectangle, and
// the overlay the rectangles sit on — is registered here beside the panel's own `marks` (owns), so a document-level
// listener that knows nothing of panels can tell a panel's activation from the file's markup. The chat pane's link
// handler (render.ts) is that listener: it opens every absolute `a[href]` in a new tab at the CAPTURE phase, before the
// delegate root and before the overlay swallows the click after a press it handed on, so a rectangle on a LINKED figure
// (`[![alt](fig.png)](url)`, which mdBlock renders as <a><img></a>) opened the tab there instead of its card — twice with
// the panel open, once for the click the layer handed on and once for the browser's own — while the feed and Files
// panes, which have no such handler, opened the card (the 2026-09-06 review). A registry, not a class name: the
// sanitizer keeps `class` and `data-*` on the file's own markup, so neither proves the panel made an element (owns).
const PANEL_MARKS = new WeakSet<Element>();
/** Whether `t`, or an element above it, is a mark some panel painted: a rectangle's chip counts through its rectangle,
 *  a press on the overlay through the overlay. False for the file's own markup, whatever it wears. */
export function panelMark(t: Element | null): boolean {
  for (let x: Element | null = t; x; x = x.parentElement) if (PANEL_MARKS.has(x)) return true;
  return false;
}

class Panel {
  status: Status | null = null;
  statusRefusal: { code: string; error: string } | null = null;   // why there is no status, when the kernel refused one
  root: HTMLElement | null = null;          // the aside, built on first open
  marks = new WeakSet<Element>();           // the highlights and picture frames THIS panel painted into the body (owns)
  open = false;
  pending = new Map<number, Pending>();
  appliedReq = 0;                           // the reqId of the newest ask whose reply is showing (applyStatus)
  openCards = new Set<string>();            // keyed expand state: survives every re-render (ui/CLAUDE.md); a change card's key is "chg:" + its id
  openLog = new Set<string>();              // expanded Log rows, keyed by entry (ts|kind) — the same rule
  logOpen = false;
  moreChangesOpen = false;                  // the "… N more changes" fold past GROUP_LIMIT groups — the same rule
  rejectAllConfirm = false;                 // the Reject all confirm row is showing (pane-local, like the folder-off confirm)
  paintedChanges = new Set<string>();       // the change ids whose marks the current view shows; the rest get Reveal
  landing: HTMLElement | null = null;       // the Raw row the last Reveal cued, when the view showed no mark of ours there (landOn)
  // Show changes inline (the inline-display follow-on, 2026-09-07): whether the read view marks the session's changes
  // in the text — insertions tinted, deletions struck — in both views. Off, the file reads as it is and every change
  // is its card alone (no "not shown" tag: nothing is shown by choice). The shared settings store keeps it across
  // opens and pages (settings.ts changesInline, ON by default); comment highlights are not governed by it.
  inline = loadSettings().changesInline;
  // Which cards the list shows and which marks the text wears (the filter follow-on, 2026-09-07): "all", "comments" or
  // "changes", from the shared settings (settings.ts commentsFilter, "all" by default), chosen in the header (All · Comments ·
  // Changes). The inline toggle applies on top: "changes" with the marks off shows the change cards and no mark. The control
  // is offered only while the file has a card to filter (filterOffered), and the choice governs nothing until then (activeFilter).
  filter: CommentsFilter = loadSettings().commentsFilter;
  // The comment saved while the filter showed the changes alone (noteHiddenSave): its card and mark are hidden by that
  // choice, so the list says so where the card would be (hiddenSavedRow) until the card shows or the person dismisses it.
  hiddenSaved: string | null = null;
  busyVerb = new Map<string, string>();     // slot → the verb in flight, so a card's Accept/Reject relabels itself (ui/CLAUDE.md)
  seen = new Map<string, SeenChange[]>();   // slot → the changes a by-id decision was clicked on, as the card showed them (DECIDE_VERBS)
  imageTarget: { range: SourceRange | null } | null = null;   // the picture the float's Comment is about, when it is one
  /** Where the float's subject sat on screen when the button was offered (the rect showFloat placed it beside) and, when the
   *  subject is a picture, the picture itself; a passage is re-read from the live selection. hideFloatOnScroll compares the
   *  subject's rect now against it; cleared with the float (hideFloat), so no element of a swapped-out render is held. */
  floatAt: { top: number; right: number; img: HTMLElement | null } | null = null;
  regionLayers = new Map<Pictured, RegionLayer>();            // the overlays, one per picture in view — an <img>, or a PDF page's canvas (Slice 3/4; paintRegions)
  regionMarks = new Map<Pictured, RegionMark[]>();            // the rectangles the last region pass filed per picture: what a layer made late (onPageNear) paints
  pageWatch: IntersectionObserver | null = null;              // the panel's watch on PDF page shells with no overlay yet (watchPages → onPageNear)
  pageWatched = new Map<HTMLElement, HTMLCanvasElement>();    // the shells it watches, and their canvases
  // what each overlay last painted (its marks, the pending region, the re-place cue), so a pass that brings it nothing
  // new leaves its rectangles standing — the layer updates them in place (RegionLayer.paint), and this spares the pass
  // itself: openPanel's own paint, a status that moved nothing (CLAUDE.md: a move on no new information)
  paintedKey = new WeakMap<RegionLayer, string>();
  cropWait = new WeakSet<HTMLImageElement>();                 // pictures whose load will re-render the cards for their thumbnails
  // a PDF region's crop, kept from the last time its page was drawn (cutCrop: on every draw's repaint for every region on
  // the page, the card open or not, and on an open card's render): the chunk keeps only the bitmaps near the reader (a far
  // page's canvas is 0×0), and a card must not lose its picture because its page scrolled away, nor lack one because it
  // was closed while the page was on screen. Keyed by what the crop was cut from, so a re-place or a regenerated file
  // drops it (cropKey)
  crops = new Map<string, { key: string; crop: HTMLCanvasElement }>();
  figureBase: FigureBaseline = {};                            // the poll's last reading of each figure a region comment names (tick)
  resolvedOpen = false;
  trackChoice = false;                      // the on-toggle's scope row (file / folder) is showing
  trackStop = false;                        // the folder-off confirm is showing
  composer: Composer | null = null;
  errors = new Map<string, Err>();          // per slot: the row sits under the control that asked
  busy = new Set<string>();
  sendConfirm = false;
  sending = false;
  sendOpts = { todo: true, track: true, accept: true };   // all checked by default (decision 8); `accept` is the Slice 2 checkbox
  sentNote: string | null = null;
  // the last send's acknowledgment, kept while the saved line displaces it at the panel's foot (landSaved, in the margin
  // layout, where the line takes its position): what comes back there when the line ends (restoreSent) — at a gesture, at
  // the settled re-read that finds the card in view, at the panel's close — so the foot never shows neither. The review,
  // 2026-09-09, round 2: a reply's landing read its card, taller with the composer's box in it, as below the track's box,
  // and the composer's close re-laid the card whole in view; the pass's re-read ended the line, and the acknowledgment
  // was gone with it, with no gesture of the person's. Set with the acknowledgment (doSend) and cleared with it when the
  // next confirm opens (fcsend): a line standing then comes down on nothing, since the next send's acknowledgment replaces it.
  sentAck: string | null = null;
  // the todo the send answers when SEVERAL are offered (todoOpts' radio group; the todo-file follow-on, 2026-09-07): the id
  // picked, "" for none, null while nothing was picked — the first candidate then, and again when the pick left the list (a
  // todo settled from elsewhere, or answered by the send before). With one candidate the checkbox (sendOpts.todo) decides.
  // The two agree on "none": the change handler writes a declined answer to both (the box unchecked is the "" pick, a
  // "none" pick unchecks the box), because the next status can swap one control for the other — a todo filed or settled
  // elsewhere changes the count — and a decline held in one slot alone came back as the other's default (the 2026-09-07
  // review). An answer written to either puts the other back to its default (checked; null, the first offered).
  todoPick: string | null = null;
  openTodoText = new Set<string>();         // confirm todo rows unfolded to the todo's whole text, keyed by todo id — the same rule (openLog)
  // the Send confirm's note (the user's ruling, 2026-09-09: the grey preview of the message was a system message tied to the
  // send and not worth showing, so a box for the person's own words took its place). `sendNote` is the words as typed, kept
  // across every re-render while the confirm is open (a status landing, a poll) and cleared by a successful send or by
  // closing the confirm on purpose (Cancel); a refused send keeps them. `noteBox` is one persistent textarea, moved into
  // each fresh confirm the way the composer's box is (render restores its focus and scroll): a rebuilt box would drop the
  // caret and the keyboard mid-word. The note goes in the request as `note`, trimmed, first in the message after its header
  // (buildSendMessage is the kernel's twin); over SEND_NOTE_MAX characters the send is refused here, before any request.
  sendNote = "";
  noteRefusal: Err | null = null;             // the send slot's row that refused the note over the bound, while it stands (syncNoteRefusal)
  noteBox = el("textarea", "fc-input fc-send-note") as HTMLTextAreaElement;
  noteSizedTo: string | null = null;         // the inline height autosizeNote last set: any other was dragged there, and stands (the composer's sizedTo rule)
  colors: Map<string, FileViewIdentity> | null = null;
  wanted: { key: FocusKey; at: Element } | null = null;   // a focused control a render rebuilt DISABLED or hidden, and where the keyboard went meanwhile (refocus): kept while it is in the list and the keyboard stays there
  located = new Map<string, Located & { painted: boolean }>();
  /** The comments whose highlight sits on a copy the panel cannot vouch for (copyUnsure): the anchor ties and the stored
   *  position names none of the tied copies, so the copy painted is the engine's guess. Rebuilt with `located` each paint. */
  unsureCopies = new Set<string>();
  base: PollBaseline | null = null;
  // editing over pending changes (Slice 5): what the editor's records came from — the status at Edit, or the last landed
  // save's reply once the editor stayed up past it — as the records and the sidecar/config fence the save fences on (a
  // change a session records mid-edit moves the sidecar, and a fence from the poll's later status would let the save write
  // over it); null when nothing rode in (EditSeed). `lastSaveNs` is the fileMtimeNs of a save reply this panel applied as
  // its status itself, so onSaved skips the re-read it does for saveFile.
  editSeed: EditSeed | null = null;
  lastSaveNs: string | null = null;
  // Which editor: begin() counts one per Edit, and saveThroughComments captures the count at the send, so a reply that finds
  // a LATER editor up (Cancel confirmed during Saving, then Edit again before the ack) leaves that editor's seed and text
  // alone — they are its own, from the status as it stood — and says the file moved under it instead.
  editGen = 0;
  // decisions this panel sent whose reply has not landed (holdEdit): while any is out, the viewer refuses Edit
  decisionsOut = 0;
  // the file's bytes moved under an edit (noteMovedUnderEdit) and the view has not re-read them yet: the first paint after
  // the edit ends re-reads (paintAll). A latch of its own, not the head row's presence: the row's ✕ dismisses the words,
  // and the re-read must still happen, or Cancel would leave the pre-rewrite bytes showing for good (the poll's baseline
  // already moved on to the new mtime when the status landed, so no later tick would notice). The same latch keeps the row
  // to once per edit: every later status reads later than the editor's frozen mtime, and a dismissed row must not return
  // with each of them (the shape the two latches below have)
  movedUnderEdit = false;
  // the sidecar's pending changes stopped being the editor's (noteChangesMovedUnderEdit): the row was set once for this
  // edit; a later status re-sets nothing, and the edit's end clears both (paintAll)
  changesMovedUnderEdit = false;
  // the sidecar shows pending changes the editor never carried (noteChangesUnreadUnderEdit): the same latch shape
  changesUnreadUnderEdit = false;
  // the text the status's offsets index while the editor is up: the file as the editor loaded it (begin), or the content of
  // the last landed save (saveThroughComments), whose reply's hunks index that. text() answers the BUFFER then, which typing
  // moves under the offsets — grouping the cards over it retitled them with every keystroke's render (indexedText). Null
  // outside an edit: the view's text is the one.
  editText: string | null = null;
  decideRows = new Set<string>();           // the slots whose row says to decide in the editor (refuseDecision): retired when the edit ends
  stopped = new Set<string>();              // poll targets a 413/415 retired
  timer: ReturnType<typeof setInterval> | null = null;
  polling = false;
  tickSkipped = false;
  // the reload the panel asked for (syncBytes: a status whose file mtime is not the view's) is out: the body shows
  // the bytes from before, with no marks over them, until the fetch lands. The wait wears the loader at the head of
  // the cards (the "bytes" busy slot, ui/CLAUDE.md), ending on the paint that shows the status's text (paintAll →
  // bytesLanded). The seam reports no failed fetch — the viewer shows its own error in the body and fires no
  // onRendered — so the loader has the same backstop a status ask has: after STATUS_DEADLINE_MS it yields to a row
  // with Reload (bytesLate). `reloadFor` is the file mtime the last ask was for: one ask per mtime, so a second
  // status carrying the same mtime while that fetch is out (the moved-fence retry: the refresh's status, then the
  // retry's reply) asks nothing.
  bytesWait: ReturnType<typeof setTimeout> | null = null;
  reloadFor: string | null = null;
  // ── the margin layout (the build's reading, not a ruling, of the user's 2026-09-07 ask after walking the loop: that
  // comments might move with the window when possible, each trying to stay centered near its place in the text; the
  // build put each card level with its passage instead, and the plan's margin-layout note under Slice 2 records both,
  // with the user's word still to come). Beside the body the aside is laid out as a document editor's margin:
  // the head and the composer stay put at the top, Accept all · Reject all, Send and the Log at the bottom, and between
  // them the cards section is a TRACK whose scroll is locked to the body's — the body's scrollTop is mirrored onto the
  // track on its scroll event and the reverse on the track's (syncFrom guards the echo) — with every card absolutely
  // positioned at its mark's height (placeCards, card-layout.ts). `margin` is whether that layout is on: off in the
  // narrow fold (the sheet's container query stacks the aside under the body: the list layout as before, read off the
  // row's computed flex-direction) and in edit mode (the editor's own marks; no read view to sit beside).
  margin = false;
  placed = new Map<string, PlacedItem>();    // the last pass's placement by card key, in placement order (centerOn and cardsInOrder read it)
  cardsEnd = 0;                               // the last pass's bottom edge of the last card plus the gap: the track content the last card's end needs (followBody)
  bodyPad = 0;                                // the end padding the pass gave the body, in px (padBody): the footer's height plus the last card's overhang
  contentWatched = new Set<Element>();        // the body's element children the size observer holds (watchContent: the content's box, which grows when the body's does not)
  layoutFrame: number | null = null;          // the pass scheduled for the next frame (scheduleLayout: one per frame, however many events ask)
  syncFrom: "body" | "track" | null = null;   // the scroller whose write onto the other is still to echo (mirrorScroll)
  sizer: ResizeObserver | null = null;        // the body, the row and the track (the aside's width and height reach it as the track's): a size change re-runs the pass
  cardSizer: ResizeObserver | null = null;    // the cards of the current render: one growing (a crop, a box inside it) pushes the cards below
  expandIntent: { key: string; wasOpen: boolean } | null = null;   // a card head clicked, as seen before the delegate toggles it (installLayout → afterRender)
  // the focus (the focus follow-on, 2026-09-08): the card the person last acted on — a mark clicked, a card opened by its
  // head, a reference followed, a Show more, a save, a Reveal — which the pass anchors the layout on (card-layout.ts): level with its
  // mark whatever stands above it, the cards above moved up by the least that clears it. Before it, a tall change card above
  // a comment pushed the comment's card a viewport below its highlight, and the click on the highlight scrolled the
  // highlight to the body's top edge with the card still out of sight. Cleared when the list no longer holds the card
  // (placeCards), by a pass in the list layout (the same: a mark or a head clicked there writes one, and the list has no
  // pass to spend it on — the 2026-09-08 review), when the layout ends (layoutOff: the fold, edit mode, the panel's close)
  // and with the panel (dispose). A LOOSE card written here — a whole-file comment's card opened by its head or by its Show
  // more, the card a whole-file comment's save landed in — is spent by the pass as no change: it has no mark to be laid
  // level with, and the rule takes a focus with no mark as none (card-layout.ts), so the pass would have laid the whole
  // margin by the push-down rule again — the clicked card to the track's start, out of the box with nothing scrolling after
  // it, and the card the person was reviewing pushed under the tall card again, off its mark (the verification review,
  // 2026-09-09: the reach rule lays a loose card the chain cannot fit above the focus BELOW it, where a head click reaches
  // it). The pass keeps the focus it laid the cards on last (laidOn) instead: a gesture on a card the rule cannot place
  // moves nothing, as a head click on a loose card never did.
  focusCard: string | null = null;
  laidOn: string | null = null;               // the focus the last margin pass laid the cards on (placeCards): what a loose focus falls back to
  // Show more (the same follow-on): the cards whose long parts — a change's old and new text, a long comment, a long run of
  // turns — show whole in the margin layout, where the sheet otherwise folds each to about eight lines (clipCards); keyed
  // like openCards, so the choice survives a re-render
  openBodies = new Set<string>();
  // ── the arrivals notice (the arrivals follow-on, 2026-09-09; file-comments-model.ts statusEntries, arrivalWords). The
  // user sent comments, the session answered with eleven changes and seven replies while they kept commenting, and nothing
  // in the panel said so until the next Send accepted the changes by default. `seenKeys` is the set of entry keys the
  // person has seen — a change, a comment, a reply (statusEntries) — null until the panel's first render with a status
  // seeds it with everything then in the status. That status is the probe's, asked at mount with the panel closed, and
  // the open's own re-ask (openPanel → refresh) lands after that render, so the first status to land while the panel is
  // OPEN is all seen as well (`seenOpen`, noteArrivals): a file opened fresh has no arrivals — the person is looking at
  // all of it — whatever the session added between the probe and the open (the review, 2026-09-09: a panel first opened
  // minutes after the probe named everything since as arrivals). Every status landing after that (noteArrivals) adds
  // the person's own writes to the set (YOU) and files every other author's entry not in the set as an ARRIVAL, kept in
  // `arrivals` until seen. Seen is event-based (gesture): a
  // gesture of the person's — a pointer press, a key, a wheel, a touch move in the body row, a save, a send — marks the
  // arrivals whose cards are then in the track's box (entryShown) seen; the ones it scrolled into view are seen by the
  // gesture that follows. Never a timer. While any arrival stands the head shows one line naming them (renderHead), a
  // button whose click shows the first of them (goToArrival); the line's own press marks nothing seen, so the line stands
  // through the click that asked to see the first arrival. The arrival cards and their marks wear data-new (renderCard, renderChangeCard,
  // markNew) until seen; `newKeys` is the set of card keys the current render marks. The set lives with the panel, so a
  // Raw/Rendered switch, a reload, a close and reopen of the aside keep it; a new file is a new panel.
  lit = new Set<string>();                    // the change ids whose marks a comment's tag lit under the pointer (lightChanges)
  // the header action's confirm row is showing (decision 46). Set by the action's click, cleared by Resolve or Cancel — and by
  // the events that take the question away: the status whose count falls to zero (the comments resolved from their own
  // cards, settleResolveAnsweredConfirm) and the panel's close. Left set, it came back re-counted when the count rose again,
  // one click from resolving with no gesture behind it (the same shape the Reject-all confirm had at Edit, begin())
  resolveAnsweredConfirm = false;
  resolvingAnswered = false;                  // the resolves are out, one after the other (resolveAnswered)
  consentHeld = false;                        // a run of writes asked the file-editing consent once and holds it (consentForRun); mutate asks nothing meanwhile
  reopenAll: string[] | null = null;          // the comments the last Resolve answered resolved, offered back as Reopen all until the next gesture
  seenKeys: Set<string> | null = null;
  // the texts of every SEEN pending change, by its entry key, as they read when it was marked seen (the seeds above, a
  // gesture, the person's own write: recordSeen, recordPending). The key is the change's id, and the id is stable while the
  // change under it is not (DECIDE_VERBS' comment): a same-author track-edit landing inside or beside a pending change is
  // coalesced into it and grows its texts under the same id, so a status can bring a seen id with text nobody has looked
  // at. A status whose pending change reads differently from this record takes the change out of the seen set and files
  // it as an arrival again (noteArrivals, grownSince): the dot, the line under the header and the Send's unseen count name
  // it, and the next gesture with its card on screen sees it anew — the person's own changes are theirs whatever they
  // read. Before this the Send accepted a change grown under a seen id and the confirm counted it among the seen (the
  // review, 2026-09-09, round 2); the decisions' own guard (changedSince) caught growth after the press alone. Detached
  // changes and comments have no texts here; a seen change with no record (one seen while detached and re-attached since)
  // is recorded as it stands, not filed anew.
  seenTexts = new Map<string, SeenChange>();
  seenOpen = false;                           // whether a status has landed while the panel was open: until one has, the next to land is a newly opened panel's first, all seen (noteArrivals)
  arrivals = new Map<string, Entry>();
  newKeys = new Set<string>();
  // the card a save landed in while it stands out of view, and which side of the box it is on (landSaved; decision 43): the
  // acknowledgment's position at the panel's foot says so in the margin layout, a line under the header in the list layout
  // (savedLine, renderHead says why) until the person's next gesture or the card coming into view. Latched, not read at
  // each render: a render swaps in a fresh list whose height the pass has not written yet, so the track's scroll reads 0
  // until the pass, and a side read then would say the card is in view when it is not (CLAUDE.md: a transient state holds
  // until the deciding event, never re-derived per build). The side is re-read where the geometry is settled — the end of a
  // pass, a scroll, a render in the list layout, the composer's close there (reflectLines, landClosed) — and the line ends
  // there or at a gesture (gesture).
  savedOut: { key: string; side: "above" | "below" } | null = null;
  // the seen set the Send confirm's accept option and count row were last written from (renderSend, syncAcceptOption), null
  // with no confirm up: the send accepts by it (pendingSplit), so what goes is what the confirm said when the person pressed
  // Send. The press itself is a gesture, and its pointerdown or key marks the card the last wheel scrolled in seen — before
  // this the send read the live set after that mark, and accepted a change while the box still read disabled and unchecked
  // with "nothing is accepted until you look" (the review, 2026-09-09: the hold keeps the option's words through a press, so
  // the person could not have read the change in). The card is seen all the same, for the next confirm.
  confirmSeen: Set<string> | null = null;
  sendPress = false;                          // the send's own press is under way (doSend; gesture reads it for the key that sends): its gesture leaves the confirm as the person read it (syncAcceptOption)
  hold: PressHold | null = null;              // the body row's press: the arrivals line's change in place waits for the release (the constructor installs it)
  // persistent section wrappers: render() swaps each section's CHILDREN, never the aside's own children —
  // replaceChildren on the aside would remove and re-insert the composer box, and a removed element
  // loses focus, so a poll-triggered re-render would drop the input's focus mid-word
  sections = { head: el("div", "fc-sec-head"), cards: el("div", "fc-sec-cards"), send: el("div", "fc-sec-send"), log: el("div", "fc-sec-log") };
  // persistent composer parts, for the same reason
  composerBox = el("div", "fc-composer");   // in the panel's slot, or inside the card a reply answers (placeComposer)
  composerRef = el("div", "fc-composer-ref");
  input = el("textarea", "fc-input") as HTMLTextAreaElement;   // several lines (the 2026-09-07 follow-on): Enter is a newline, the chord saves
  // the inline height autosize last set: an inline height that is not this one was dragged there by the person (the
  // sheet's resize: vertical), and their height stands until the composer closes (closeComposer)
  sizedTo: string | null = null;
  composerActs = el("div", "fc-actions");
  composerErr = el("div");
  float = el("button", "fileview-btn fc-float", "Comment") as HTMLButtonElement;
  catchUp = () => { if (this.tickSkipped) void this.tick(); };
  hideFloatOnDown = (ev: Event) => { if (ev.target !== this.float) this.hideFloat(); };
  /** The float goes, and with it what it was about: the picture (imageTarget) and the place it was offered at (floatAt). */
  hideFloat(): void { this.float.hidden = true; this.imageTarget = null; this.floatAt = null; }
  /** The body scrolled, or a figure in it landed its bytes: when the passage (or picture) the float sat beside has moved
   *  from under it, the float goes, as it goes on a press elsewhere (plans/markdown-viewer.md Slice 2: it used to stay
   *  fixed in place while the selection scrolled off the body). The margin lock's own write of the body's scrollTop (a
   *  wheel over the cards, mirrored onto the body) fires the same event and hides it too: the passage has moved then as
   *  well. One body scroll moves nothing on screen: when content above the viewport grows (an unsized figure landing its
   *  bytes), Chromium's scroll anchoring grows scrollTop by the same amount so the reader's text stays put, and fires a
   *  scroll event for that write (the Slice 2 review, round 2: the float vanished from beside a selection that had moved
   *  under a pixel, and the reader had to select the passage again). So the event is the trigger and the subject's rect
   *  the test: the float stays while the passage sits within a pixel of where the button was offered beside it (scrollTop
   *  is whole pixels and the growth above fractional, so anchoring leaves a sub-pixel drift), and goes once it has moved
   *  a pixel or more, or is gone. The same figure landing INSIDE the viewport, above the passage, moves the passage down
   *  by its height with no scroll at all (anchoring adjusts for growth above its anchor node alone), so the listener runs
   *  on a figure's `load` as well, heard on the body in the capture phase since load does not bubble (the Slice 2 review,
   *  round 3: the button stood some 300px above the passage it was offered beside, and a click on it commented on text
   *  the reader could not see under it). The rect is read after the browser's layout for the event, the anchoring
   *  adjustment included, so the one comparison tells the two figures apart. The selection itself stands either way,
   *  and the next mouseup over it offers the button again. */
  hideFloatOnScroll = () => {
    if (this.float.hidden) return;
    const was = this.floatAt, now = this.floatSubjectRect();
    if (was && now && Math.abs(now.top - was.top) < 1 && Math.abs(now.right - was.right) < 1) return;   // anchoring held the passage under the button
    this.hideFloat();
  };
  // Esc cancels a Re-place. Every other composer kind focuses the input, whose own keydown catches Esc; a re-place hides
  // the input (it takes a drag, not words), so nothing in the box holds focus and the key fell through to the viewer's
  // document-level Escape, which closed the WHOLE viewer — the panel, the open card and the pending re-place with it, when
  // the person meant only to think again. Caught at the document in the capture phase, ahead of the viewer's handler,
  // wherever the focus sits (the re-rendered Re-place button, or the body); only while a re-place is pending.
  escapeReplace = (ev: KeyboardEvent) => {
    if (ev.key !== "Escape" || !this.composer || this.composer.kind !== "replace") return;
    ev.preventDefault(); ev.stopPropagation();
    this.closeComposer();
  };
  /** A key in the box. A plain Enter is the browser's own newline; the chord saves (composerKeyAction); Escape cancels.
   *  An Escape under a composing IME is the IME's (composerKeyAction: null, and its default cancels the composition), but
   *  it is still not the viewer's: the document-level Escape (file-view.ts onKey) reads no isComposing and closes the whole
   *  viewer — the panel and the typed comment with it — or peels edit mode. So EVERY Escape stops at the box. */
  boxKey = (e: KeyboardEvent) => {
    if (e.key === "Escape") e.stopPropagation();
    const act = composerKeyAction(e);
    if (act === "save") { e.preventDefault(); void this.saveComposer(); }
    else if (act === "cancel") { e.preventDefault(); e.stopPropagation(); this.closeComposer(); }   // never the viewer's Escape
  };
  /** A key in the Send confirm's note box: the composer's gesture (composerKeyAction), a plain Enter the textarea's own
   *  newline, the chord the send. Escape stops at the box, as in the composer's (boxKey): the viewer's document-level
   *  Escape would close the whole viewer over a note half typed; it closes nothing here, the words stay. */
  noteKey = (e: KeyboardEvent) => {
    if (e.key === "Escape") e.stopPropagation();
    if (composerKeyAction(e) === "save") { e.preventDefault(); void this.doSend(); }
  };

  constructor(readonly ctx: FileViewActionCtx, readonly button: HTMLButtonElement, readonly unit: HTMLElement) {
    ensureListener();
    live = this;
    this.input.rows = COMPOSER_ROWS;
    this.input.placeholder = "Your comment";
    this.input.setAttribute("aria-label", "Comment text");
    this.input.addEventListener("keydown", this.boxKey);   // Escape here; the save chord arrives through the window's claim (claimSaveChord); a plain Enter is left to the textarea
    this.input.addEventListener("input", () => this.autosize());
    this.noteBox.rows = COMPOSER_ROWS;                 // the Send confirm's note: three rows, grown to about eight (SEND_NOTE_ROWS), then scrolling
    this.noteBox.setAttribute("aria-label", "A note for the session");
    this.noteBox.addEventListener("keydown", this.noteKey);
    this.noteBox.addEventListener("input", () => { this.sendNote = this.noteBox.value; this.autosizeNote(); this.syncSendGo(); this.syncNoteRefusal(true); });
    (this.float as HTMLButtonElement).type = "button";
    this.float.hidden = true;
    this.float.title = "Comment on the selected passage";
    // keep the selection alive across the click: a mousedown elsewhere would collapse it before the click lands
    for (const ev of ["mousedown", "touchstart"]) this.float.addEventListener(ev, (e) => e.preventDefault());
    const act = () => {
      flash(this.float);
      const picture = this.imageTarget;
      const sel = window.getSelection();
      this.hideFloat();
      if (picture) this.startImageComment(picture.range);
      else if (sel && !sel.isCollapsed) this.startComment(sel);
    };
    this.float.addEventListener("click", act);
    // a tap: the touchstart above is cancelled, and a cancelled touch synthesizes no mouse events and no
    // click (Touch Events, "mouse events"), so on a phone the button acted on nothing. The tap acts here, on
    // the lift, while the selection is still live; cancelling the touchend too stops any click a browser
    // would still synthesize from acting a second time.
    this.float.addEventListener("touchend", (e) => { e.preventDefault(); act(); });
    document.body.appendChild(this.float);
    for (const ev of ["mousedown", "touchstart"]) document.addEventListener(ev, this.hideFloatOnDown, true);   // a press anywhere else hides it, mouse or finger
    document.addEventListener("keydown", this.escapeReplace, true);   // Esc during a re-place: see escapeReplace
    // with the float's other listeners, for every layout (installLayout runs for every layout too, but its scroll listeners
    // feed mirrorScroll, which acts in the margin layout alone): this open's body. The same listener hears a figure's load,
    // in the capture phase (load does not bubble): a picture landing inside the viewport above the passage moves it with
    // no scroll event (hideFloatOnScroll's comment)
    ctx.body().addEventListener("load", this.hideFloatOnScroll, true);
    ctx.body().addEventListener("scroll", this.hideFloatOnScroll, { passive: true });
    ctx.onSelection((sel) => this.onSelection(sel));
    // a PAINT (new nodes): the whole pass over the body. A REFLOW (the same nodes at a new width or text size, a pane drag's
    // every frame): the marks stand around the same characters, so only what was MEASURED from the text is redone, the
    // cards' places (scheduleLayout, one pass per frame) and the float, which sat by a passage that has moved. Until
    // 2026-09-09 a reflow ran paintAll too, unwrapping and re-wrapping every highlight and change mark and rebuilding the
    // aside, once per frame of a drag: 1.1 s a frame at 3,000 lines with 200 comments and 200 changes (bench
    // tools/viewer-resize-bench.ts), and the whole dashboard stalled for the drag on a bigger file.
    ctx.onRendered((why) => { this.hideFloat(); this.retargetComposer(); if (why === "reflow") this.scheduleLayout(); else this.paintAll(); });
    ctx.onSaved((info) => {
      if (this.base) this.base.file = info.mtimeNs;   // the poll must not re-fetch the person's own save
      if (this.lastSaveNs === info.mtimeNs) { this.lastSaveNs = null; return; }   // a save through this panel: its reply IS the status (Slice 5)
      if (this.status) void this.refresh();            // the Log gained the edit entry before the reply
    });
    ctx.onClose(() => this.dispose());
    ctx.guardClose(() => this.draftAsk());             // a typed, unsaved comment is asked about before the viewer moves on
    ctx.guardClose(() => this.noteAsk());              // …and the words typed in the Send confirm's box, a note not yet sent
    ctx.setTrackedEdit(this.trackedEdit());            // the editor's half of editing over pending changes (Slice 5)
    // every control the panel ever renders hangs off ONE stable root (ui/CLAUDE.md, click-safe): the
    // viewer's body row, which also holds the painted highlights — so a highlight click routes here too.
    // The same row holds the FILE's rendered markdown, and the sanitizer keeps data-* attributes (DOMPurify's
    // ALLOW_DATA_ATTR default), so a file's author can write `<span data-act="fcsendgo">` or a
    // `data-act="fctrackstop"` into prose the session produced: a click there must not send the comments
    // or turn the guard off for a folder. `own` routes an activation only when the panel MADE the element —
    // a control in its aside, or a highlight it painted (owns) — never the file's own markup.
    const row = ctx.body().parentElement || ctx.body();
    delegate(row, {
      ...this.own({
        fctrack: () => { void this.onTrackClick(); },
        fctrackfile: () => { this.trackChoice = false; void this.mutate("set-tracked", { on: true, scope: "file" }, "track"); },
        fctrackfolder: () => { this.trackChoice = false; void this.mutate("set-tracked", { on: true, scope: "folder" }, "track"); },
        fctrackcancel: () => { this.trackChoice = false; this.trackStop = false; this.render(); },
        fctrackstop: () => { this.trackStop = false; void this.mutate("set-tracked", { on: false, scope: "folder" }, "track"); },
        fcinline: () => this.toggleInline(),
        fcfilter: (x) => this.setFilter(x.dataset.key as CommentsFilter),   // All · Comments · Changes (the filter follow-on)
        fcfile: () => this.startFileComment(),
        fcsave: () => { void this.saveComposer(); },
        fccancel: () => this.closeComposer(),
        fcraw: () => this.switchToRaw(),
        // a card whose reply is being written stays open: its box stands in the card (placeComposer), and a fold would take the
        // box and the words with it; Save or Cancel frees the head again
        fccard: (x) => { const id = x.dataset.id!; if (!this.openCards.has(id)) this.openCards.add(id); else if (!this.hostsReply(id)) this.openCards.delete(id); this.render(); },
        fcgoto: (x, ev) => { ev.stopPropagation(); this.goTo(x.dataset.id!); },
        fcreveal: (x, ev) => { ev.stopPropagation(); this.reveal(x.dataset.id!); },
        fcreply: (x, ev) => { ev.stopPropagation(); this.startReply(x.dataset.id!); },
        fcresolve: (x, ev) => { ev.stopPropagation(); void this.mutate("resolve", { commentId: x.dataset.id!, on: x.dataset.on === "1" }, "card:" + x.dataset.id!); },
        fcresolved: () => { this.resolvedOpen = !this.resolvedOpen; this.render(); },
        // Resolve answered (decision 46): the header action asks in one line, resolves the person's answered comments one
        // request each, and offers them back as Reopen all in the acknowledgment's position until the next gesture
        fcresolveanswered: () => { this.resolveAnsweredConfirm = true; this.render(); },
        fcresolveansweredcancel: () => { this.resolveAnsweredConfirm = false; this.render(); },
        fcresolveanswereddo: () => { void this.resolveAnswered(); },
        fcreopenall: () => { void this.reopenAnswered(); },
        // the changes (Slice 2): a decision per card, both at once in the footer, a comment about the change (the about follow-on), the fold
        fcaccept: (x, ev) => { ev.stopPropagation(); void this.mutate("accept", { ids: [x.dataset.id!] }, "change:" + x.dataset.id!); },
        fcreject: (x, ev) => { ev.stopPropagation(); void this.mutate("reject", { ids: [x.dataset.id!] }, "change:" + x.dataset.id!); },
        fcacceptall: () => { this.rejectAllConfirm = false; void this.mutate("accept-all", {}, "changes"); },
        fcrejectall: () => {   // Reject all rewrites the file: one pane-local confirm — unless the editor is up, when the answer is where to decide (DECIDES)
          if (this.ctx.editing()) { this.refuseDecision("changes"); return; }
          this.rejectAllConfirm = !this.rejectAllConfirm; this.render();
        },
        fcrejectallgo: () => { this.rejectAllConfirm = false; void this.mutate("reject-all", {}, "changes"); },
        fcrejectallcancel: () => { this.rejectAllConfirm = false; this.render(); },
        fcchangecomment: (x, ev) => { ev.stopPropagation(); this.startChangeComment(x.dataset.id!); },   // Comment on this change (the about follow-on)
        fcaboutfirst: (x, ev) => { ev.stopPropagation(); this.showAbout(x.dataset.id!); },   // the change card's "N comments" tag: the first comment about the change into view
        fcmore: () => { this.moreChangesOpen = !this.moreChangesOpen; this.render(); },
        // Show more / Show less on a card the margin layout folded (clipCards): more makes the card the focus and centers its
        // mark, as opening a card by its head does (afterRender); less is a fold and moves nothing. On a loose card the pass
        // keeps the focus it had and centerOn has no mark to scroll to: the card shows its text whole where it stands
        fcclip: (x) => {
          const key = x.dataset.id!;
          if (this.openBodies.has(key)) this.openBodies.delete(key);
          else { this.openBodies.add(key); this.focusCard = key; this.expandIntent = { key, wasOpen: false }; }
          this.render();
        },
        // an inline change mark opens its card, and only that: like fcopen below, it cancels the click. A mark inside the
        // author's link (a deletion point placed at the start of a link's label, a substitution's point and tint over it,
        // an insertion's tint) stands inside the <a>, which mdBlock gives target=_blank, so the click that opened the card
        // also opened a tab to the author's URL, the session's URL, on a file under review; painted over a URL the viewer
        // linked (file-view-links.ts) it stands inside that anchor too, and the anchor's own open followed the card's on
        // every click and Enter (the 2026-09-07 review, both finds). Cancelling the click ends the anchor's activation;
        // the chat pane's link handler stands aside for a panel mark on the word that the delegate cancels. The click
        // that ends a drag-selection inside the mark opens nothing (dragClick): the float the mouseup offered stands
        // and the composer opens on the selection, a comment inside the change's own text.
        fcchange: (x, ev) => { ev.preventDefault(); if (this.dragClick(ev)) return; this.openPanel(); this.showCard("chg:" + x.dataset.id!); },
        fcsend: () => { if (this.statusRefusal) return; this.sendConfirm = true; this.sentNote = null; this.sentAck = null; this.render(); },   // renderSend disables the button and says why; the guard holds if a click lands anyway
        fcsavedgo: () => { const out = this.savedOut; this.savedOut = null; if (out) this.scrollCard(out.key); this.reflect(); },   // the saved line (savedLine; decision 43): the card into view as the focus, and the line is over
        fcsendcancel: () => { this.sendConfirm = false; this.sendNote = ""; this.noteBox.value = ""; this.render(); },   // closed on purpose: the note goes with it
        fcsendgo: () => { void this.doSend(); },
        fctodotext: (x) => { const id = x.dataset.id!; if (this.openTodoText.has(id)) this.openTodoText.delete(id); else this.openTodoText.add(id); this.render(); },   // a confirm todo row's fold (todoOpts)
        fclog: () => { this.logOpen = !this.logOpen; this.render(); },
        fclogrow: (x) => { const k = x.dataset.key!; if (this.openLog.has(k)) this.openLog.delete(k); else this.openLog.add(k); this.render(); },
        // Reload re-reads under the row that offered it: the slot wears the loader for the wait (refresh)
        fcreload: (x) => { const slot = x.dataset.slot || "head"; this.errors.delete(slot); this.stopped.clear(); void this.refresh(slot); this.ctx.reload(); },
        fcerrx: (x) => { this.errors.delete(x.dataset.slot || ""); this.render(); },
        fchiddenx: () => { this.hiddenSaved = null; this.render(); },   // the line for a comment saved under Changes (hiddenSavedRow): read, dismissed
        fcarrivals: () => this.goToArrival(),          // the arrivals line (the arrivals follow-on, 2026-09-09): the first arrival's card into view, as the focus
        // a mark in the file's own markup — a rectangle on a figure, a framed picture — is the panel's control, and its
        // click is the card's opening, not the activation of whatever the author wrapped the figure in: a linked figure
        // (`[![p95](figs/p95.png)](url)`, which mdBlock gives target=_blank) opened a new tab on every click, Enter and
        // handed-on press on a rectangle inside it, since the overlay and its rectangles stand inside the <a>
        // (the 2026-09-06 review). Cancelling the click ends the anchor's activation; the card opens as before — unless
        // the click ends a drag-selection inside the highlight (dragClick), as for a change mark above.
        fcopen: (x, ev) => { ev.preventDefault(); if (this.dragClick(ev)) return; this.openPanel(); this.showCard(this.cardKey(x.dataset.id!)); },
        fcreplace: (x, ev) => { ev.stopPropagation(); this.startReplace(x.dataset.id!); },   // a region comment's Re-place (Slice 3)
      }),
    });
    row.addEventListener("change", (ev) => {
      const t = ev.target as HTMLInputElement | null;
      const k = t ? t.dataset.opt : undefined;
      if (!t || !this.owns(t)) return;                 // a control the file's markup carries flips nothing
      if (k === "todopick") this.todoPick = t.value;   // the radio group: the todo's id, or "" for none (todoOpts)
      else if (k === "todo" || k === "track" || k === "accept") this.sendOpts[k] = t.checked;
      else if (k === "about") { const c = this.composer; if (c && c.kind === "comment" && c.about) c.about.on = t.checked; return; }   // the composer's about option: unchecked, a plain passage comment (the about follow-on)
      else return;
      // the answer-a-todo verdict has two controls — the box when one todo is offered, the radio group when several — and
      // the next status can swap one for the other (a todo filed or settled elsewhere changes the count; applyStatus keeps
      // the confirm open), so a verdict recorded in either is written to both: the box unchecked is the "" pick and a
      // "none" pick unchecks the box; a todo picked or the box checked is an answer in both, the other slot back to its
      // default. Before, a declined answer held in one slot came back as the other's default and the send stamped a todo
      // the person had declined (the 2026-09-07 review; todoPick's comment).
      if (k === "todopick") this.sendOpts.todo = t.value !== "";
      else if (k === "todo") this.todoPick = t.checked ? null : "";
      this.render();                                   // the list's counts and the preview follow the boxes (refocus keeps the box focused)
    });
    // a click on a rendered picture offers Comment on its embed line (the plan's Images and PDFs) — the same
    // stable root, a plain tag check rather than a data-act: the markdown's own <img> carries none
    row.addEventListener("click", (ev) => {
      const t = ev.target as HTMLElement | null;
      if (t && typeof t.tagName === "string" && t.tagName.toUpperCase() === "IMG") this.onImageClick(t);
    });
    // Enter or Space on a focused non-button control (KEY_ACTS) is its click, so it lands on the same root —
    // for the panel's own elements only, as with the clicks
    row.addEventListener("keydown", (ev) => {
      if (ev.key !== "Enter" && ev.key !== " ") return;
      const t = ev.target as HTMLElement | null;
      if (!t || typeof t.tagName !== "string" || t.tagName.toUpperCase() === "BUTTON" || t.tagName.toUpperCase() === "INPUT" || typeof t.closest !== "function") return;
      const x = t.closest("[data-act]") as HTMLElement | null;
      if (!x || !KEY_ACTS.has(x.dataset.act || "") || !this.owns(x)) return;
      ev.preventDefault();
      x.click();
    });
    // the filter's buttons are one group (a small radiogroup): an arrow on one of them moves to the next or previous option and
    // chooses it, wrapping at the ends (Home and End: the first and the last) — for the panel's own buttons only, as above
    row.addEventListener("keydown", (ev) => {
      if (!FILTER_KEYS.has(ev.key)) return;
      const t = ev.target as HTMLElement | null;
      if (!t || !t.dataset || t.dataset.act !== "fcfilter" || !this.owns(t)) return;
      const i = FILTERS.indexOf(t.dataset.key as CommentsFilter);
      if (i < 0) return;
      ev.preventDefault();
      const next = ev.key === "Home" ? FILTERS[0] : ev.key === "End" ? FILTERS[FILTERS.length - 1]
        : FILTERS[(i + (ev.key === "ArrowRight" || ev.key === "ArrowDown" ? 1 : FILTERS.length - 1)) % FILTERS.length];
      this.setFilter(next);
      (this.root?.querySelector('[data-act="fcfilter"][data-key="' + next + '"]') as HTMLElement | null)?.focus({ preventScroll: true });
    });
    this.button.addEventListener("click", () => { flash(this.button); if (this.open) this.closePanel(); else this.openPanel(); });
    this.installLayout(row);                           // the margin layout's scroll lock and its re-layout events
    // the person's gestures (the arrivals follow-on, 2026-09-09; gesture): a pointer press or a key anywhere in the body
    // row — the file's text, a mark, the aside and its composer — and the two events that begin a scroll of theirs, a wheel
    // and a touch move. Not the scroll event: the lock's writes and a card's centering fire it with no gesture behind
    // them, and a wheel fires BEFORE the scroll it starts, so what a wheel marks seen is what was on screen
    // before it, and what it scrolled in is seen by the gesture after. A scrollbar drag is a pointer press on the scroller;
    // arrow and page keys are keys. In the capture phase, so a listener that stops the event lower down cannot hide it.
    // The hold is installed FIRST: its own pointerdown listener is capture on the same row, and same-target same-phase
    // listeners run in registration order, so a hold installed after the gesture would still read as not held when the
    // gesture's pointerdown ran reflectSeen, and the line came off in the middle of the press it exists to wait out (the
    // review, 2026-09-09: measured in Chromium and Firefox, the pressed card moved up by the line's height under the pointer).
    this.hold = pressHold(row);                        // the arrivals line's and the saved line's changes in place wait out a press on the row (reflect)
    for (const ev of ["pointerdown", "keydown"]) row.addEventListener(ev, (e) => this.gesture(e), true);
    for (const ev of ["wheel", "touchmove"]) row.addEventListener(ev, (e) => this.gesture(e), { capture: true, passive: true });
  }

  // ── provenance: which activations are the panel's ──────────────────────────────────────────────
  /** Whether the panel made `x`: a control inside its aside (none before the first open), or a highlight or
   *  picture frame it painted into the body (marks). Anything else under the delegate root is the file's own
   *  markup, whatever data-act it carries — the sanitizer keeps data-* attributes, and a class name proves
   *  nothing either. */
  owns(x: Element): boolean {
    return (this.root !== null && this.root.contains(x)) || this.marks.has(x);
  }
  /** Remember an element this panel painted into the body — for owns, and for the document's listeners (panelMark). */
  private mark(x: Element): void { this.marks.add(x); PANEL_MARKS.add(x); }
  /** Whether a click on a body mark is the end of a drag that selected text inside THAT mark, and not a tap. A drag begun
   *  and ended inside one mark fires a click on the mark, the common ancestor of the press and the release, and the mark is
   *  a control (fcchange, fcopen): the click opened the card, showCard's centerOn scrolled the mark to the body's centre,
   *  and that scroll hid the Comment float the same mouseup had just offered beside the selection (hideFloatOnScroll), so a
   *  comment inside a tracked change could be left only by replying to the change (the user, 2026-09-09, who wanted one
   *  on the change's own words). The event is the click's own state, read against the control the click landed on (the
   *  target's nearest data-act: the element the delegate routed here, resolved the same way): a click arriving with a
   *  non-collapsed selection whose anchor and focus both lie inside that mark is a drag's, and the handler does nothing —
   *  the float stands, and the composer opens on the selection as for any passage. The mark, not the body: a press
   *  collapses a standing selection only through text the press can select, so a selection left standing elsewhere in
   *  the body (a passage read, copied, or offered a comment and left) survives a press on a deletion's struck label
   *  (user-select: none), on a region's rectangle (the overlay cancels its pointerdown), on a mark inside an author's
   *  link (draggable) or on a framed picture, and a guard that read any body selection as the drag's left every such
   *  control dead until the reader clicked plain text (the 2026-09-09 review of this fix). A drag that leaves the mark
   *  fires its click on the common ancestor, never on the mark, and no selection end can lie inside a point mark or a
   *  rectangle, so those clicks open the card whatever stands selected. An engine may report a drag's end at the mark's
   *  edge as a point in the mark's parent, or in the neighbouring text, rather than in the mark (endInside takes both as
   *  the mark's). A click with no pointer behind it, `detail` 0 — Enter or Space through the row's keydown (x.click()),
   *  assistive technology, the overlay's hand-on — is never a drag's, whatever selection stands, so the keyboard opens
   *  the card unaffected. The click stood down acts on nothing and shows nothing: the press pulse the delegate put on the
   *  mark before the handler ran (actions.ts flash) comes off in the same task, before a frame paints it, as the tab
   *  list's once() takes it off a swallowed repeat (render.ts). */
  private dragClick(ev: Event): boolean {
    if ((ev as MouseEvent).detail === 0) return false;
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || !sel.anchorNode || !sel.focusNode) return false;
    const at = ev.target as Element | null;
    const x = at && typeof at.closest === "function" ? at.closest("[data-act]") : null;
    if (!x || !endInside(x, sel.anchorNode, sel.anchorOffset) || !endInside(x, sel.focusNode, sel.focusOffset)) return false;
    x.classList.remove("romp-acted");
    return true;
  }
  /** The handlers, each routed only for an element the panel owns. The delegate helper has already flashed
   *  the element by then (a cosmetic pulse); nothing else happens for the file's markup. */
  private own(acts: Record<string, ActionHandler>): Record<string, ActionHandler> {
    const out: Record<string, ActionHandler> = {};
    for (const k of Object.keys(acts)) out[k] = (x, ev) => { if (this.owns(x)) acts[k](x, ev); };
    return out;
  }

  // ── the wire ───────────────────────────────────────────────────────────────────────────────────
  request(verb: string, args?: Record<string, unknown>, fence?: Record<string, string>): Promise<Reply> {
    const reqId = ++reqSeq;
    const { ctx } = this;
    const msg: Record<string, unknown> = { type: "fileComments", reqId, sid: ctx.sid || undefined, path: ctx.path, verb };
    if (args) msg.args = args;
    if (fence) msg.fence = fence;
    return new Promise<Reply>((ok, fail) => {
      // the reply carries the ask's own reqId (the client's, not the echo) so applyStatus can order it, and
      // whether the ask overlapped a write (set on the pending record by markOverlapped, read when it settles)
      const p: Pending = { verb, ok: (m) => ok({ ...m, reqId, overlapped: p.overlapped === true } as unknown as Reply), fail };
      if (verb === "status") p.deadline = setTimeout(() => this.expire(reqId), STATUS_DEADLINE_MS);   // STATUS_DEADLINE_MS: why, and why status only
      this.pending.set(reqId, p);
      ctx.post(msg);
    });
  }
  /** A status ask past its deadline: failed under `no-answer`, naming the machine whose kernel it went to. */
  private expire(reqId: number): void {
    const p = this.pending.get(reqId);
    if (!p) return;
    this.pending.delete(reqId);
    const machine = hostOf(this.ctx.sid || "") || "this machine";
    p.fail({ code: "no-answer", error: "No answer from the kernel on " + machine + " after " + STATUS_DEADLINE_MS / 1000
      + " s. It may predate file comments: update and restart it, then Reload to ask again." });
  }
  /** The kernel's reply carries two optional texts on a SENT message: `warning` (nothing stamped:
   *  the todo switch is off, or the todo was already settled) and `logWarning` (the comments log
   *  append failed, so the Log and the unsent count will not reflect this send). Both are shown; a
   *  send whose record is missing must never look fully done (CLAUDE.md, fail loudly). */
  requestSend(msg: Record<string, unknown>): Promise<{ queued: boolean; warning?: string; todoStamped: boolean }> {
    const reqId = ++reqSeq;
    const str = (v: unknown) => (typeof v === "string" && v ? v : undefined);
    return new Promise((ok, fail) => {
      // a SENT reply's `warning` is exclusively the nothing-stamped text (contract C2), so its absence is the stamp
      this.pending.set(reqId, { verb: "send", ok: (m) => ok({ queued: m.queued === true, warning: [str(m.warning), str(m.logWarning)].filter(Boolean).join(" ") || undefined,
        todoStamped: !str(m.warning) }), fail });
      this.ctx.post({ ...msg, type: "fileCommentsSend", reqId });
    });
  }
  settle(m: Record<string, unknown>, ok: boolean): void {
    const p = this.pending.get(Number(m.reqId));
    if (!p) return;                                    // an older open's reply, or a stale one — lands nowhere
    this.pending.delete(Number(m.reqId));
    if (p.deadline) clearTimeout(p.deadline);
    if (ok) p.ok(m);
    else p.fail({ code: String(m.code || "failed"), error: String(m.error || "the request failed") });
  }
  /** Fail everything outstanding with `text`; null (a warn that was not a drop of ours) leaves it all in flight. */
  failAll(text: string | null): void {
    if (text === null || !this.pending.size) return;
    const ps = [...this.pending.values()]; this.pending.clear();
    for (const p of ps) { if (p.deadline) clearTimeout(p.deadline); p.fail({ code: "unreachable", error: text }); }
  }

  // ── status ─────────────────────────────────────────────────────────────────────────────────────
  /** The first ask, at mount: mounted hidden, revealed when the kernel answers (the GitHub link's
   *  idiom). A `no-node` refusal keeps the action away for good — the gear's row says why. A kernel that
   *  never answers (one from before this feature, reached through federation for a remote session's file,
   *  or the VS Code extension's local one) is named after STATUS_DEADLINE_MS, the way any other refusal
   *  is: the action appears with the reason as its title and in the panel's head row. */
  probe(): void {
    this.request("status").then((s) => this.applyStatus(s), (e: { code: string; error: string }) => {
      if (e.code === "no-node") return;
      this.statusRefusal = e;
      this.unit.hidden = false;
      this.button.title = "Comments: " + e.error;
      this.errors.set("head", { text: e.error, reload: false });
    });
  }
  /** Replies land in the order their asks were ISSUED, not the order they arrive. The kernel runs each ask
   *  concurrently and answers as each finishes, so a `status` the poll asked (or onSaved, or Reload, or a
   *  send's refresh) can be answered after a later comment or toggle whose reply already carried the
   *  post-write state — and applying it as it came put the panel back a step (the new card gone, Send's count
   *  down) until the next tick saw the store moved against that regressed baseline and re-read it: a card
   *  move on no new information (CLAUDE.md). Two asks are suspect: one OLDER than the applied reply, and one
   *  issued after a write's ask but still unanswered when that write's reply landed (`overlapped`,
   *  markOverlapped) — the kernel runs the two concurrently and the host reads the sidecar without a lock,
   *  so the later ask's run can read the disk before the write and answer after it, and its reqId
   *  alone would have let it land. Either is dropped, unless its own clocks PROVE it read a NEWER disk than what
   *  is showing (its run started late and saw a write the applied reply predates): then it IS new information
   *  and lands. A sidecar the two readings disagree on EXISTING is no proof either way (provablyNewer): a suspect
   *  reply holding a sidecar mtime while the applied reply holds none may have read the disk before the write that
   *  pruned it — an accept-all with no comments deletes the sidecar — and applying it brought the decided changes
   *  back as cards with live Accept and Reject; the reverse, a suspect that saw a deletion the applied reply predates,
   *  reads as older. Both are the poll's to settle: present ↔ absent is a transition it sees. Returns whether it
   *  was applied. */
  applyStatus(s: Reply): boolean {
    const suspect = s.reqId < this.appliedReq || s.overlapped === true;
    if (this.status && suspect && !provablyNewer(s, this.status)) return false;
    this.appliedReq = Math.max(this.appliedReq, s.reqId);
    this.status = s;
    this.noteArrivals(s);                              // the entries this status brings that the person has not seen (the arrivals follow-on)
    this.settleResolveAnsweredConfirm();               // a confirm whose count this status took to zero is over, not parked (the field's comment)
    this.releaseAnswered(s);                           // a todo this status lists, asked after a send stamped it, is open again (answeredTodos)
    this.statusRefusal = null;
    this.errors.delete("head");                        // a status refusal's row (probe, refresh) is answered by a status
    this.base = pollBaseline(s);
    this.figureBase = figureBaseline(s, this.ctx.path, this.figureBase);   // the figures' baseline from the same reply (Slice 3)
    this.unit.hidden = false;
    this.button.textContent = actionLabel(s);
    this.button.title = s.store ? "Comments and changes kept beside this file" : "Comment on this file, or track a session's changes to it";
    // Edit is not refused for pending changes any more (Slice 5): they ride into the editor as marks (trackedEdit.begin),
    // and the viewer raises the Slice 2 wording itself when its editor bundle cannot carry them
    this.noteChangesMovedUnderEdit();                  // every status lands here: the one place that can see the editor's records leave the sidecar
    this.noteChangesUnreadUnderEdit();                 // …or show changes the editor never carried (Edit before the first status)
    this.syncBytes(s);                                 // the view shows the text these hunks index, or is asked to (stands down while the editor holds the body)
    this.paintAll();                                   // repaints the highlights and renders the panel
    return true;
  }
  /** The Resolve answered confirm (decision 46) is over once the status it was asked over leaves nothing for it to do: the
   *  comments resolved from their own cards, or by another client, take the header action away (renderHead offers it at N > 0
   *  alone), and a confirm parked behind an absent action came back re-counted when the count rose again, one click from
   *  resolving with no gesture behind it (the field's comment). The status that takes the count to zero ends it. */
  private settleResolveAnsweredConfirm(): void {
    if (this.resolveAnsweredConfirm && !answeredComments(this.cards()).length) this.resolveAnsweredConfirm = false;
  }
  /** The page's memory of the todos its sends stamped (answeredTodos) ends for every todo `s` lists whose latch
   *  predates the ask: the status was issued after the send's reply landed, and the kernel stamps — or parks — before
   *  it replies, so a todo it still lists is open (a parked send, stamped at its drain; a recalled answer, reopened).
   *  A status issued before the reply (its reqId at or under the latch's) releases nothing: it may have read the
   *  store before the stamp. Only an APPLIED status releases — a dropped one is not what the confirm is built from. */
  private releaseAnswered(s: Reply): void {
    if (!Array.isArray(s.todos)) return;
    for (const t of s.todos) {
      const id = t && typeof t === "object" ? t.id : undefined;
      if (typeof id !== "string" || !id) continue;
      const at = answeredAt.get(id);
      if (at !== undefined && at < s.reqId) { answeredTodos.delete(id); answeredAt.delete(id); }
    }
  }
  /** Bring the view's bytes to the text a status describes: its hunks and anchors are offsets into the file the
   *  host read, so when the file mtime the status carries is not the view's, the view is asked to re-fetch and the
   *  cards wear the loader until a paint shows that text (awaitBytes). Every status lands through applyStatus, so
   *  every way the two can diverge is this one rule: a reject's reply (the host rewrote the file); the fresh status
   *  a moved fence asked for, when a track-edit landed under the click and moved the sidecar AND the file (the
   *  refusal named only the sidecar, so a reload keyed on `file-moved` alone left the old bytes up with no marks on
   *  them — the review's finding); an accept's reply whose file mtime moved since the poll last looked; the poll's
   *  own re-read. Nothing else re-fetches: every reply re-baselines the poll to the mtime it carries, so the poll
   *  never sees a move a status already reported. A view with no text yet (its first fetch out) is left alone, and so
   *  is a view whose body the editor holds (Slice 5): its buffer is the text and the viewer's reload() stands down, so
   *  a fetch asked here would never start and the loader it armed could only run out; the head says the bytes moved
   *  instead (noteMovedUnderEdit, at each status's call site), and the edit's end re-reads them (paintAll). */
  private syncBytes(s: Status): void {
    if (this.ctx.editing()) return;
    const vm = this.ctx.mtimeNs();
    if (!vm || !s.fileMtimeNs || vm === s.fileMtimeNs) return;
    this.askReload(s.fileMtimeNs);
    this.awaitBytes(s);
  }
  /** One re-fetch per file mtime (`reloadFor`): the poll and the status that follows it both know the same mtime, and
   *  a status landing while the fetch it asked for is still out must not ask twice. Null asks unconditionally. */
  private askReload(mtimeNs: string | null): void {
    if (mtimeNs !== null && this.reloadFor === mtimeNs) return;
    this.reloadFor = mtimeNs;
    this.ctx.reload();
  }
  /** Re-ask status. While the ask is out and no status has ever landed, the cards section shows the romp
   *  loader (ui/CLAUDE.md: a wait wears the loader, never a line claiming a read); a refusal leaves the
   *  head's row with Reload, the one way back in — nothing re-asks on its own while status is null.
   *  `slot`: the row whose Reload asked. Over a showing status the cards stay up, so that wait would show
   *  nowhere (the row is gone, the click's pulse goes with its rebuilt button, and the ask may run to
   *  STATUS_DEADLINE_MS) — the slot wears the loader instead, where the row was. The poll's and onSaved's own
   *  re-reads pass no slot: nobody is waiting on those, and a swirl in the head per change the session
   *  makes would only pull the eye. */
  async refresh(slot?: string): Promise<boolean> {
    const mark = slot && this.status ? slot : null;   // with no status the cards' own loader is the wait
    this.busy.add("status"); if (mark) this.busy.add(mark); this.render();
    try { return this.applyStatus(await this.request("status")); }
    catch (err) {
      const e = err as { code: string; error: string };
      this.statusRefusal = e;
      this.errors.set("head", { text: e.error, reload: true });
      return false;
    } finally { this.busy.delete("status"); if (mark) this.busy.delete(mark); this.render(); }
  }
  /** A write's reply just landed: every status ask still out was issued before it and may have read the disk
   *  before the write (applyStatus). The flag rides the pending record, so a failed or expired ask needs no
   *  cleanup. */
  private markOverlapped(): void {
    for (const p of this.pending.values()) if (p.verb === "status") p.overlapped = true;
  }
  /** A mutating verb needs a status behind it: the fence comes from there, and `""` for an unknown sidecar
   *  would claim it must not exist, so the host would refuse `store-moved` — a reason that is not the reason
   *  (a corrupt sidecar, say). Re-ask first, since the person may have fixed the file since the last answer;
   *  when the answer is still a refusal, refuse here, under the control that asked, with the host's own text.
   *  The caller (mutate) holds the slot busy for the whole call, loader included. */
  private async requireStatus(slot: string): Promise<boolean> {
    if (this.status) return true;
    try { this.applyStatus(await this.request("status")); return true; }
    catch (err) {
      const e = err as { code: string; error: string };
      this.statusRefusal = e;
      this.errors.set(slot, { text: "Nothing written: " + e.error, reload: false });
      return false;
    }
  }

  // ── open / close ───────────────────────────────────────────────────────────────────────────────
  openPanel(): void {
    if (this.open) return;
    this.open = true;
    if (!this.root) {
      this.root = el("div", "fc-panel");
      // the list layout's scroll (the viewer makes this root the aside, .fileview-aside, whose box scrolls the cards): the
      // saved line follows the card's side against the box as the margin layout's does at mirrorScroll, and ends with the
      // card coming into it — a touch drag begun on the line itself scrolls without a gesture the line ends at, and a
      // scrollbar drag is a press outside the row (the review, 2026-09-09: the words stood stale until the next gesture). A
      // scroll marks nothing seen (the constructor's comment). The margin layout's root does not scroll; its track does.
      this.root.addEventListener("scroll", () => { if (this.savedOut && !this.margin) this.reflect(); }, { passive: true });
    }
    this.ctx.aside(this.root);
    this.button.classList.add("on"); this.button.setAttribute("aria-pressed", "true");
    if (!this.colors) void this.loadColors();
    this.paintRegions();                               // arm the overlays' drag (they paint while closed, but draw only open)
    this.render();
    void this.refresh();
    this.startPoll();
  }
  closePanel(): void {
    if (!this.open) return;
    this.open = false;
    this.ctx.aside(null);
    this.button.classList.remove("on"); this.button.setAttribute("aria-pressed", "false");
    this.hideFloat();
    this.resolveAnsweredConfirm = false;               // a question this panel asked, and the person closed the panel on it (the field's comment)
    // A pending Re-place is a gesture of the OPEN panel: its instruction and Cancel are the composer box, and the drag it
    // waits for is disarmed with the panel. Left pending, the closed panel's picture kept the cue (the dashed accent
    // outline inviting a drag) over an overlay that took none, with nothing on screen saying why, and escapeReplace kept
    // swallowing the document's Escape — the viewer's own close — for a re-place nothing showed (the 2026-09-06 review).
    // Closing ends it, as Esc does: the comment keeps its place. A region composer holding a typed note stays: the words
    // are the person's, and its pending rectangle is a mark like any other.
    if (this.composer && this.composer.kind === "replace") this.closeComposer();
    this.paintRegions();                               // disarm: a closed panel leaves the pictures to the browser
    if (this.margin) this.layoutOff();                 // the body's end padding and the placement go with the aside (a reopen's first pass brings them back)
    this.savedOut = null;                              // the line saying where a saved card stands (savedLine) was for this panel's view: a reopen shows the list afresh
    this.restoreSent(null);                            // …with the acknowledgment the line displaced back at the foot (sentAck)
    this.clearLanding();                               // the Reveal that cued a row was this panel's gesture; the cards it led from are gone
    this.hiddenSaved = null;                           // the line about a save this panel showed nothing for was read with the panel open (hiddenSavedRow)
    this.stopPoll();
  }
  /** The viewer's close ask (ctx.guardClose): a composer holding typed words is a note the person has not saved, and a
   *  close or a replace-open (a link followed inside the file, a Files-pane row, the shell's relay) used to drop it with
   *  the panel, silently (the 2026-09-07 review). The panel names what is at stake; the VIEWER puts the ask, the way it
   *  puts the editor's own (file-view.ts askDiscard: a confirm on the web, the notice bar in the VS Code webview, where
   *  window.confirm shows nothing and answers false; the round-2 review). A re-place takes a drag, not words, and an
   *  empty input has nothing to lose: null lets the close go. */
  draftAsk(): CloseAsk | null {
    const c = this.composer;
    if (!c || c.kind === "replace" || !this.input.value.trim()) return null;
    const p = this.ctx.path, name = p.slice(p.lastIndexOf("/") + 1);
    return { question: "Discard the unsaved comment on " + name + "?", kept: "This file stays open: the comment typed on " + name + " is not saved. Save it, or clear the box, then try again." };
  }
  /** The second close ask: words typed in the Send confirm's box are a note the person has not sent, and a close or a
   *  replace-open dropped them with the panel, silently — the one gap decision 40 recorded (the arrivals follow-on's review,
   *  2026-09-09; closed in its consolidation). An ask of its own beside the composer's rather than that one widened: each
   *  names the one thing it would drop, and the viewer runs every ask in turn (file-view.ts closeGuard), so a person holding
   *  both is asked about both. The emptiness is the kernel's (trimNote): words its strip would take to nothing are not sent
   *  (doSend) and not asked about. Cancel and a send that went clear the field, so neither leaves an ask; a send out or
   *  refused keeps the words and the ask with them. */
  noteAsk(): CloseAsk | null {
    if (!trimNote(this.sendNote)) return null;
    const p = this.ctx.path, name = p.slice(p.lastIndexOf("/") + 1);
    return { question: "Discard the unsent note on " + name + "?", kept: "This file stays open: the note typed under Send on " + name + " is not sent. Send it, or Cancel it, then try again." };
  }
  dispose(): void {
    this.clearLanding();
    this.stopPoll();
    if (this.margin) this.layoutOff();
    this.focusCard = null;
    for (const l of this.regionLayers.values()) l.dispose();
    this.regionLayers.clear();
    this.pageWatch?.disconnect(); this.pageWatch = null; this.pageWatched.clear();   // the shells it held go with the viewer
    this.crops.clear();
    if (this.bytesWait) { clearTimeout(this.bytesWait); this.bytesWait = null; }
    this.sizer?.disconnect(); this.cardSizer?.disconnect(); this.contentWatched.clear();   // the margin layout's observers and its pending frame go with the viewer
    if (this.layoutFrame !== null && typeof cancelAnimationFrame === "function") cancelAnimationFrame(this.layoutFrame);
    this.layoutFrame = null;
    window.removeEventListener("resize", this.onWindowResize);
    this.float.remove();
    for (const ev of ["mousedown", "touchstart"]) document.removeEventListener(ev, this.hideFloatOnDown, true);
    this.ctx.body().removeEventListener("load", this.hideFloatOnScroll, true);
    this.ctx.body().removeEventListener("scroll", this.hideFloatOnScroll);
    document.removeEventListener("keydown", this.escapeReplace, true);
    this.failAll("the file viewer closed");
    if (live === this) live = null;   // …and the window's save-chord claim (claimSaveChord reads `live`) is no longer this box's
  }

  // ── the session color map: one GET /sessions per panel open, authorId → name + colour ──────────
  // /sessions lists the LOCAL kernel's sessions; a remote session's authors get the neutral chip (there
  // is no /remote/<host>/sessions route today).
  async loadColors(): Promise<void> {
    this.colors = new Map();
    if (this.ctx.sid && hostOf(this.ctx.sid)) return;
    try {
      const rows = await (await fetch(kernelUrl("/sessions"), { cache: "no-store" })).json();
      if (Array.isArray(rows)) {
        for (const r of rows) {
          if (r && typeof r.id === "string" && typeof r.name === "string") {
            this.colors.set(r.id, { name: r.name, color: typeof r.bg === "string" && typeof r.fg === "string" ? { bg: r.bg, fg: r.fg } : null });
          }
        }
      }
    } catch { /* the chips fall back to their labels */ }
    // the change marks and the region rectangles carry the author's colour too (paintChanges, paintRegions): repaint
    // when any are up — a rectangle painted before this answer wears the sheet's fallback until then — else just the chips
    const s = this.status;
    if (s && ((s.hunks || []).length || this.cards().some((c) => c.target))) this.paintAll(); else this.render();
  }
  sessionName(): string {
    const id = this.ctx.identity();
    if (id && id.name) return id.name;
    const c = this.ctx.sid && this.colors ? this.colors.get(bareId(this.ctx.sid)) : null;
    return c ? c.name : "the session";
  }

  // ── the poll ───────────────────────────────────────────────────────────────────────────────────
  startPoll(): void {
    if (this.timer) return;
    this.timer = setInterval(() => { void this.tick(); }, POLL_MS);
    document.addEventListener("visibilitychange", this.catchUp);
    window.addEventListener("resize", this.catchUp);
  }
  stopPoll(): void {
    if (this.timer) { clearInterval(this.timer); this.timer = null; }
    document.removeEventListener("visibilitychange", this.catchUp);
    window.removeEventListener("resize", this.catchUp);
  }
  async tick(): Promise<void> {
    if (!this.open || !this.status || !this.base || this.polling) return;
    if (paneHidden()) { this.tickSkipped = true; return; }
    this.tickSkipped = false;
    this.polling = true;
    try {
      const t = pollTargets(this.status, this.ctx.path);
      const base = this.base;
      const checks: Array<[keyof PollBaseline, string]> = [["file", t.file]];
      if (t.store) checks.push(["store", t.store]);
      if (t.config) checks.push(["config", t.config]);
      // `fileNow`: the file's own mtime when the bytes the VIEW shows moved; an embedded figure moving is `figureMoved` (below)
      let fileNow: string | null = null, moved = false;
      for (const [key, target] of checks) {
        const v = await this.head(target);
        if (!v) continue;
        if (mtimeMoved(base[key], v.value)) { moved = true; if (key === "file") fileNow = v.value; }
      }
      // the figures (Slice 3): a region comment on a figure embedded in a text file goes stale when the FIGURE's bytes
      // change, and a session that regenerates one touches none of the three targets above — so they are HEADed too.
      // Each is compared with its baseline (figuresMoved): the mtime the status reply read beside the figure's hash
      // (embeddedMtimes, seeded in applyStatus through figureBaseline), else the poll's own last reading of it — a first
      // reading with neither is an observation, never a move. A move re-asks status, whose embeddedHashes flip the
      // comment to stale by hash, and reloads the view so the new picture shows: the kernel serves /file with
      // Cache-Control: no-cache, so the re-rendered <img> revalidates instead of reusing the old bytes.
      const figs = figureTargets(this.status, this.ctx.path);
      const seen: FigureBaseline = {};
      for (const target of figs) {
        const v = await this.head(target);
        if (v) seen[target] = v.value;
      }
      const fm = figuresMoved(this.figureBase, figs, seen);
      this.figureBase = fm.next;
      const figureMoved = fm.moved.length > 0;
      if (figureMoved) moved = true;
      if (moved) {
        // the bytes changed under the view: repaint them — asked here, not left to the status, so a refused status
        // (a corrupt sidecar, say) still gets the file re-read; the status that follows knows the same mtime and asks nothing.
        // A figure that moved re-fetches the view too, so the new picture shows — unconditionally: the file's own mtime
        // is unchanged, so no status will ask for it (syncBytes keys on the file's mtime alone). Never over an editor's
        // buffer (Slice 5): the viewer's reload() stands down then, so nothing is asked and `reloadFor` is left as it was;
        // the head says the bytes moved instead (noteMovedUnderEdit, below), and the edit's end re-reads them (paintAll)
        if (!this.ctx.editing()) {
          if (fileNow !== null) this.askReload(fileNow);
          else if (figureMoved) this.askReload(null);
        }
        await this.refresh();                        // fresh sidecar, log, and a new baseline
        this.noteMovedUnderEdit();                   // reload() stands down in edit mode: the head says the bytes moved (Slice 5)
      }
    } finally { this.polling = false; }
  }
  /** One HEAD of the poll: the target's mtime verdict, or null when it says nothing this tick — a network blip (the next
   *  tick tries again), an unknown answer, or a 413/415, which retires the target (`stopped`) under the poll's row. */
  private async head(target: string): Promise<{ kind: "value"; value: string } | null> {
    if (this.stopped.has(target)) return null;
    let r: Response;
    try { r = await fetch(fileUrl(target, this.ctx.sid), { method: "HEAD", cache: "no-store" }); }
    catch { return null; }                           // a network blip: the next tick tries again
    const v: HeadVerdict = headVerdict(r.status, r.headers.get("X-Romp-Mtime-Ns"));
    if (v.kind === "stop") {
      this.stopped.add(target);
      // "checking … for changes", the guide's own words for this loop — never "watching": the row sits under
      // the Track changes toggle, and a tracked file whose refresh stopped is still tracked
      this.errors.set("poll", { text: "Stopped checking " + target + " for changes: the kernel answered " + v.status
        + (v.status === 413 ? " (too large to serve)" : " (not a type it serves)") + ". Reload to try again.", reload: true });
      this.render();
      return null;
    }
    return v.kind === "value" ? v : null;
  }

  // ── verbs ──────────────────────────────────────────────────────────────────────────────────────
  /** A mutating verb: consent first (decision 5), then the request with the fence from the current
   *  status; an `editing-off` refusal re-offers the consent and retries once; a moved fence re-issues
   *  status and retries once by the same args — except for the id-less accept-all and reject-all
   *  (BULK_VERBS), which re-issue status and stop, saying nothing was decided; a second refusal shows
   *  verbatim, with Reload when the store, file, or config moved. Resolves the fresh status, or null
   *  when nothing was written. */
  /** The file-editing consent is asked per write below — unless a run of writes holds it (consentHeld: resolveAnswered and
   *  reopenAnswered asked once for the run, consentForRun), when this write asks nothing again: the real ask reads the kernel's
   *  flag per call and confirms whenever it is off, and a decline latches nothing, so N writes in a row asked N times and left
   *  N identical rows (the review, 2026-09-10). */
  async mutate(verb: string, args: Record<string, unknown>, slot: string): Promise<Status | null> {
    // a decision while the editor is up is refused before anything is asked of the kernel (DECIDES: why, and where it goes)
    if (DECIDES.has(verb) && this.ctx.editing()) { this.refuseDecision(slot); return null; }
    // one write in flight per control: a second Enter or click during the round trip is not a second
    // write (the host mints a fresh id per `comment`, so a repeat would land twice); Save disables and
    // relabels itself meanwhile (renderComposer), the slot's loader shows for every other control
    if (this.busy.has(slot)) return null;
    this.busy.add(slot); this.busyVerb.set(slot, verb); this.errors.delete(slot); this.render();
    // a decision holds Edit from here until it settles — the consent's read, the status re-ask, the send, a moved fence's
    // re-read and retry included (DECISION_IN_FLIGHT: why); the gate above and mutateOnce's are the same trap's other side
    const decides = DECIDES.has(verb);
    if (decides) this.holdEdit(1);
    try {
      if (!(await this.requireStatus(slot))) return null;
      // the changes as the card showed them: with a status held, requireStatus asked nothing, so this is the status the
      // card was rendered from. Every attempt (mutateOnce) is checked against it, the retry after a moved fence included.
      if (DECIDE_VERBS.has(verb)) this.seen.set(slot, seenChanges(this.status, args));
      if (!this.consentHeld) {                         // a run holding the consent asked it once already (consentForRun); every other write asks, per click
        if (!(await this.ctx.ensureEditingAllowed())) { this.errors.set(slot, { text: CONSENT_REFUSED, reload: false }); return null; }
      }
      return await this.mutateOnce(verb, args, slot, false);
    } finally { if (decides) this.holdEdit(-1); this.busy.delete(slot); this.busyVerb.delete(slot); this.seen.delete(slot); this.render(); }
  }
  /** Edit is refused while a decision this panel sent is out (DECISION_IN_FLIGHT): the viewer hears the reason when the
   *  first goes out and null when the last settles — one transition each way, however many are out at once (two cards
   *  clicked in a row, the Send's accept beside a card's). A status reply never touches it (Slice 5: pending changes
   *  ride into the editor; file-comments-changes.test.ts pins that applyStatus stays out of it). */
  private holdEdit(delta: 1 | -1): void {
    const was = this.decisionsOut;
    this.decisionsOut = Math.max(0, was + delta);
    if ((was === 0) !== (this.decisionsOut === 0)) this.ctx.setEditBlocked(this.decisionsOut ? DECISION_IN_FLIGHT : null);
  }
  private async mutateOnce(verb: string, args: Record<string, unknown>, slot: string, retried: boolean): Promise<Status | null> {
    // the gate again, at the send: the editor can open during mutate's awaits (the consent's read, a status re-ask, a
    // moved fence's refresh before the retry), and a decision sent then would move the sidecar under the records it just took
    if (DECIDES.has(verb) && this.ctx.editing()) { this.refuseDecision(slot); return null; }
    const s = this.status;
    // a by-id decision stands only over the change the card showed (DECIDE_VERBS): one still pending under the clicked
    // id that reads differently now — grown by a track-edit coalesced into it, seen by the refresh a moved fence ran or
    // by a status that landed while the consent was up — is not decided. The card shows the new reading; the row says
    // the choice is theirs again. Not a refusal to surface: the host would have said ok.
    const seen = this.seen.get(slot);
    const grown = seen && s ? changedSince(seen, s.hunks || []) : [];
    if (grown.length) { this.errors.set(slot, { text: changedRowText(grown.length), reload: false }); return null; }
    const fence: Record<string, string> = { storeMtimeNs: s && s.storeMtimeNs !== null ? s.storeMtimeNs : "", configMtimeNs: s && s.configMtimeNs !== null ? s.configMtimeNs : "" };
    if (FILE_VERBS.has(verb)) fence.fileMtimeNs = s ? s.fileMtimeNs : "";   // reject rewrites the file: the file's mtime as last seen (FILE_VERBS)
    // a write ABOUT a figure — `comment` with a target, `retarget` — is fenced on the figure's bytes too: the hash the
    // status holds for it (figureFenceHash), which the host compares with the bytes it stamps and refuses `figure-changed`
    // when they differ. Without it a figure regenerated between the drag and the save was stamped with the NEW bytes' hash,
    // which every reply then equalled, so a rectangle drawn on the old picture read as current on the new one — the one
    // write the hash exists to catch (the Slice 3 review, 2026-09-06; the host's fence stood unarmed until the panel sent this)
    const fh = FIGURE_VERBS.has(verb) && args.target ? figureFenceHash(s, args.target as Target) : null;
    if (fh) fence.figureHash = fh;
    try {
      const r = await this.request(verb, args, fence);
      this.markOverlapped();                           // the status asks still out may have read the disk before this write
      // a reject's reply carries the mtime of the file the host rewrote: applyStatus (syncBytes) re-fetches the bytes
      // and holds the loader until they paint — the poll will not, the reply just re-baselined it
      this.applyStatus(r);
      this.noteMovedUnderEdit();                       // a reject from a card while the editor is up is refused before this (DECIDES); a reply's clocks can still say a session moved the file (Slice 5): syncBytes stood down
      return r;
    } catch (err) {
      const e = err as { code: string; error: string };
      if (!retried && e.code === "editing-off") {
        if (await this.ctx.ensureEditingAllowed(e.error)) return this.mutateOnce(verb, args, slot, true);
      } else if (MOVED.has(e.code) && BULK_VERBS.has(verb)) {
        // no id says what the person chose: the whole pending set did, and it moved. Fresh status (and the file's bytes
        // when the file moved) so the list shows the current changes, and the row under the control says nothing was
        // decided — the choice is theirs to make again over what they can now see. A retry would decide changes that
        // were not on screen at the click (BULK_VERBS).
        await this.refreshAfterMoved(e.code);
        this.errors.set(slot, { text: "Nothing decided: " + e.error + ". The list of changes was re-read; look it over and try again.", reload: false });
        return null;
      } else if (!retried && MOVED.has(e.code)) {
        await this.refreshAfterMoved(e.code);
        return this.mutateOnce(verb, args, slot, true);
      } else if (e.code === FIGURE_CHANGED) {
        // the figure's bytes changed under the drawing: the one refusal the hash fence exists for, and never retried — a
        // retry would stamp the new bytes with a rectangle drawn on the old ones. It is the event the poll acts on when it
        // sees a figure move, arrived through the refusal instead (and for a figure only resolved comments name, the poll
        // is not watching), so the panel does what the poll does: re-read the comments (the hashes flip the cards stale)
        // and the view (the new picture shows; first, as the poll does — the re-read waits on the kernel, the view need not),
        // through the one reload path and unconditionally: the file's own mtime is unchanged, so the status that follows
        // will not ask (syncBytes keys on the file's mtime alone). The refusal then shows under the control with Reload,
        // the note kept.
        this.askReload(null);
        await this.refresh();
      }
      this.errors.set(slot, { text: e.error, reload: MOVED.has(e.code) || e.code === FIGURE_CHANGED });
      return null;
    }
  }
  /** A decision asked for while the editor is up (a card's Accept or Reject, the foot's Accept all or Reject all): the row
   *  under the control that asked says where to decide instead (DECIDE_IN_EDITOR). Nothing is asked of the kernel. */
  private refuseDecision(slot: string): void {
    this.errors.set(slot, { text: decideInEditor(), reload: false });
    this.decideRows.add(slot);
    this.render();
  }

  // ── editing over pending changes (plans/file-review.md, Slice 5) ─────────────────────────────
  /** The viewer's seam object: what rides into the editor at Edit, where Save goes, and the save itself. */
  private trackedEdit(): TrackedEdit {
    return {
      begin: () => {
        this.editGen++;                                // a new editor: a save reply from an earlier one leaves this one's seed alone (saveThroughComments)
        const s = this.status;
        const hunks = s ? s.hunks || [] : [];
        // begin() runs at the click, before the viewer flips into edit mode (editing() still answers false here), so this
        // render leaves the cards in read mode; the viewer fires the seam's onRendered once as the editor takes the body
        // (enterEdit), and that paint gives the cards their edit-mode state: decisions answered in place, no Reveal or link
        // into a read view that is gone (paintAll's editing branch renders the cards and paints nothing).
        // A new edit, new latches (the records are the sidecar's own again, or none rode in); the Reject-all confirm is
        // a question the person walked away from by clicking Edit — left set, it came back re-counted when the editor
        // closed, one click from rewriting the file with no gesture behind it; and the cards group over the text the
        // status's offsets index, which text() stops answering once the editor holds the buffer (editText).
        this.changesMovedUnderEdit = false;
        this.changesUnreadUnderEdit = false;
        this.rejectAllConfirm = false;
        this.editText = this.ctx.text();
        // No status yet (the first ask is still out, or was refused) reads as nothing pending: the editor mounts plain, and
        // a status that then shows changes raises the head's row and refuses Save (CHANGES_UNREAD_UNDER_EDIT: why Edit is
        // not refused instead).
        if (!s || !hunks.length) { this.editSeed = null; this.render(); return null; }
        const seed = seedOf(s)!;                       // changes are pending: never null here
        const records = seed.records;
        this.editSeed = seed;
        this.render();
        return {
          records,
          // the mark's colour is the author's session colour from the Slice 1 map, as on the panel's own marks; neutral when
          // the label maps to no session here (a remote kernel's author, a session the list no longer holds)
          authorColor: (author) => { const aid = authorIdByLabel(s.store, author); const c = aid && this.colors ? this.colors.get(aid) : null; return c && c.color ? c.color.bg : null; },
          refusal: editBlockedReason(hunks) || "",
        };
      },
      // Read at Save. While records rode into the editor (editSeed), Save goes through the host whatever the poll's latest
      // status says: the save is fenced on the sidecar those records came from, and a sidecar pruned meanwhile (a decision
      // from another browser, a session's CLI) must meet that fence and refuse `store-moved` — never re-route to saveFile,
      // which would land the text with the editor's accepts and rejects dropped and no store fence at all. With nothing
      // in the editor, the status as it stands decides: the file is tracked or has a sidecar.
      routesSave: () => { if (this.editSeed) return true; const s = this.status; return !!s && (!!s.trackedBy || !!s.store); },
      save: (content, records, decided) => this.saveThroughComments(content, records, decided),
    };
  }
  /** The editor's Save through the host: `save` with the text, the records as the editor holds them and its decisions,
   *  fenced on the sidecar the records came from (editSeed; the latest status when none rode in), the config, and the
   *  file as the viewer loaded it. One retry, as every mutating verb gets (mutateOnce), when the sidecar or config moved
   *  but the records the editor carries are still the sidecar's own — a reply a session wrote mid-edit, a toggle from
   *  another browser; never for a moved file (the editor's text is from the old bytes) or a sidecar whose records
   *  changed. The reply is applied as the status (it is one), so onSaved has nothing left to re-read — and it re-seeds the
   *  fence, since the editor may stay up past a landed save (the viewer keeps it over keystrokes typed during the round trip,
   *  or a decision clicked then) and its next Save must meet the sidecar THIS save wrote, not the poll's latest: a decision
   *  landed elsewhere between two saves would pass that fence and be written back as pending. The host's `logWarning`
   *  (the comments log did not take the edit) rides the resolved value for the viewer's note bar and is said in the head. */
  async saveThroughComments(content: string, records: unknown[], decided: EditDecisions): Promise<{ mtimeNs: string; logged: boolean; logWarning?: string }> {
    const seed = this.editSeed;
    const gen = this.editGen;                          // the editor this save came from (begin() counts them): see `mine` below
    // The editor carries no records and the sidecar holds pending changes the file's clock does not account for: the status
    // landed after Edit (noteChangesUnreadUnderEdit's row). The list the editor would write back is empty, and the host
    // takes it as the sidecar's new contents — every change dropped, none decided, a plain-edit trace. Refused before
    // anything is asked, in the row's words: the viewer's Save bar carries them whether or not the panel is open. A file
    // that moved as well is left to the host's file fence (file-moved, with Reload — what MOVED_UNDER_EDIT promised).
    const now = this.status;
    if (!seed && now && (now.hunks || []).length && !laterNs(now.fileMtimeNs, this.ctx.mtimeNs())) throw { code: "changes-unread", error: CHANGES_UNREAD_UNDER_EDIT };
    const fenceOf = (s: Status | null): Record<string, string> => ({
      storeMtimeNs: s && s.storeMtimeNs !== null ? s.storeMtimeNs : "", configMtimeNs: s && s.configMtimeNs !== null ? s.configMtimeNs : "",
    });
    let fence: Record<string, string> = { ...(seed ? { storeMtimeNs: seed.storeMtimeNs, configMtimeNs: seed.configMtimeNs } : fenceOf(this.status)), fileMtimeNs: this.ctx.mtimeNs() };
    const args = saveArgs(content, records, decided);
    for (let attempt = 0; ; attempt++) {
      try {
        const r = await this.request("save", args, fence);
        this.markOverlapped();                         // the status asks still out may have read the disk before this write
        // Whose save this is. The editor that sent it may be gone (Cancel confirmed during Saving) and a LATER one up over the
        // bytes and records from before it (Edit again, before this ack): that editor's begin() seeded editSeed and editText
        // from the status as it stood, and re-seeding them from this reply fenced its next Save on a sidecar it never saw,
        // grouped the cards over text it does not show, and left the records this save decided riding in it as pending with
        // nothing said — the seed then matched the reply (the review's late-ack finding, panel half). So the re-seed is for
        // the editor that saved; for a later one the reply is applied as the status alone. The person hears of it from the
        // viewer, which resolves this same promise: its bar says the earlier save landed under the reopened editor, with
        // Reload, and its exit re-reads the saved bytes (SAVE_LANDED_UNDER_NEW_EDITOR) — so the panel raises no row of its
        // own here, and does not latch a second exit re-read (the moved-file latch would: one message, one read). No editor
        // at all (the edit ended, no new Edit) counts as the same editor: the first paint after the edit clears the fields
        // (paintAll).
        const mine = gen === this.editGen;
        if (mine) {
          // the reply's sidecar is the one the editor's records now came from (the host wrote them back and read them again):
          // the next Save, should the editor stay up, is fenced on it, and noteChangesMovedUnderEdit compares against it —
          // nothing pending, no seed, as at begin(); the first paint after the edit ends clears it either way (paintAll)
          this.editSeed = seedOf(r);
          this.changesMovedUnderEdit = false;          // a new seed, a new latch (a latched row would have refused this save)
          this.changesUnreadUnderEdit = false;
          this.editText = content;                     // the reply's offsets index the text this save wrote (indexedText)
          this.retargetComposer();                     // a passage composer follows its passage into that text, as after a reload
        }
        this.lastSaveNs = r.fileMtimeNs;
        // the bytes the reply describes are the viewer's business at a save's ack: an editor still up holds them as its
        // buffer, and a viewer whose editor is gone re-reads them itself (SAVE_LANDED_UNDER_NEW_EDITOR, the exit's re-read)
        // — so the reply's mtime is the one already asked for, and syncBytes asks no second fetch (askReload's rule)
        this.reloadFor = r.fileMtimeNs;
        // the save landed, but the Log this panel shows lacks the entry the edit owed (or the host could not read the sidecar
        // back): said in the head, in the host's words, where the Log lives — silence there would read as "nothing happened"
        // (CLAUDE.md, never degrade silently). A clean save retires an earlier row; the ✕ dismisses it.
        const logWarning = warningOf(r);
        if (logWarning) this.errors.set("save", { text: logWarning, reload: false, warn: true }); else this.errors.delete("save");
        if (!this.applyStatus(r)) this.render();
        return { mtimeNs: r.fileMtimeNs, logged: (r as { logged?: unknown }).logged === true, ...(logWarning ? { logWarning } : {}) };
      } catch (err) {
        const e = err as { code: string; error: string };
        if (attempt === 0 && (e.code === "store-moved" || e.code === "config-moved")) {
          await this.refresh();
          this.noteMovedUnderEdit();                   // the re-read can show the file moved too: the head says so, as the poll's would
          const s = this.status;
          if (s && sameRecords(seed ? seed.records : [], pendingRecords(s.store))) {
            fence = { ...fenceOf(s), fileMtimeNs: this.ctx.mtimeNs() };
            if (seed && gen === this.editGen) this.editSeed = { ...seed, storeMtimeNs: fence.storeMtimeNs, configMtimeNs: fence.configMtimeNs };   // the saving editor's seed follows; a later editor's is its own
            continue;
          }
        }
        throw e;
      }
    }
  }
  /** The file's bytes moved under an edit (the poll saw it; a verb's reply read a later file): the viewer's reload() stands
   *  down in edit mode, so the head says so. Save will refuse on its file fence; the first paint after the edit ends
   *  re-reads the bytes (paintAll, on the movedUnderEdit latch — the row's ✕ removes the words, not the re-read). Keyed
   *  on the clocks: the status read a later file than the one the editor loaded. Once per edit, as the sibling rows are
   *  (noteChangesMovedUnderEdit, noteChangesUnreadUnderEdit): the editor's mtime is frozen while it is up, so every later
   *  status keeps reading later than it — a comment's or a resolve's reply, a poll that saw only the sidecar move — and
   *  each would otherwise re-raise the row the person dismissed with its ✕ on nothing new about the file. A second
   *  rewrite changes none of the words either (Save refuses, Cancel shows the file as it is now), so the latch, not the
   *  clock's value, decides; the edit's end resets it (paintAll). */
  private noteMovedUnderEdit(): void {
    if (this.movedUnderEdit) return;                   // said once per edit: the row is up or was dismissed, and the re-read is owed either way
    const s = this.status;
    if (!this.ctx.editing() || !s || !laterNs(s.fileMtimeNs, this.ctx.mtimeNs())) return;
    this.movedUnderEdit = true;
    this.errors.set("edit", { text: MOVED_UNDER_EDIT, reload: false });
    this.render();
  }
  /** The sidecar's pending changes are no longer the ones that rode into the editor (a decision landed since Edit) and the
   *  file did not move: the head says so (CHANGES_MOVED_UNDER_EDIT), once per edit, in the render the status gets
   *  (applyStatus calls this before paintAll). Keyed on the records, not the sidecar's clock: a comment or reply moves the
   *  clock and leaves the records, and Save's own retry covers that. A file that moved as well has MOVED_UNDER_EDIT for its
   *  row (noteMovedUnderEdit), which says the same about Save and adds what Cancel shows; this one yields to it. */
  private noteChangesMovedUnderEdit(): void {
    const seed = this.editSeed; const s = this.status;
    if (!seed || !s || !this.ctx.editing() || this.changesMovedUnderEdit) return;
    if (laterNs(s.fileMtimeNs, this.ctx.mtimeNs())) return;   // the bytes moved too: that row (noteMovedUnderEdit) is the one to show
    if (sameRecords(seed.records, pendingRecords(s.store))) return;
    this.changesMovedUnderEdit = true;
    this.errors.set("edit", { text: CHANGES_MOVED_UNDER_EDIT, reload: false });
  }
  /** A status shows pending changes while the editor carries none and the file did not move: Edit was clicked before the
   *  first status answered (begin had nothing to hand the editor), and the sidecar's changes have been read only now. The
   *  head says so at once (CHANGES_UNREAD_UNDER_EDIT), once per edit, in the render the status gets; Save refuses on the
   *  same condition (saveThroughComments). A file that moved as well has MOVED_UNDER_EDIT for its row and the host's file
   *  fence for its refusal; this one yields to it, as the moved-records row does. */
  private noteChangesUnreadUnderEdit(): void {
    const s = this.status;
    if (this.editSeed || !s || !this.ctx.editing() || this.changesUnreadUnderEdit) return;
    if (!(s.hunks || []).length || laterNs(s.fileMtimeNs, this.ctx.mtimeNs())) return;
    this.changesUnreadUnderEdit = true;
    this.errors.set("edit", { text: CHANGES_UNREAD_UNDER_EDIT, reload: false });
  }

  /** After a moved fence: the fresh status, whose file mtime tells applyStatus (syncBytes) whether the file moved
   *  too and the bytes need re-fetching — a `store-moved` from a track-edit moved both, and the code names only the
   *  sidecar. When no status lands (refused, or dropped as suspect) and the FILE is what moved, the bytes are
   *  re-fetched anyway: the refusal is the one evidence there is, and the old text with no marks is worse than a
   *  fetch nothing awaits. */
  private async refreshAfterMoved(code: string): Promise<void> {
    const landed = await this.refresh();
    if (!landed && code === "file-moved") this.askReload(null);
  }

  // ── the bytes a status describes but the view does not show yet: the wait for the reload ───────
  /** A status whose file mtime is not the view's just applied and the view was asked to re-fetch (syncBytes): hold
   *  the "bytes" slot busy (the loader at the head of the cards) until a paint shows the status's text, or the
   *  deadline. Nothing to wait for when the view already shows it (the stand-in's synchronous reload). */
  private awaitBytes(r: Status): void {
    if (this.textCurrent(r)) return;
    if (this.bytesWait) clearTimeout(this.bytesWait);
    this.busy.add("bytes"); this.errors.delete("bytes");
    this.bytesWait = setTimeout(() => this.bytesLate(), STATUS_DEADLINE_MS);
    this.render();
  }
  /** The paint that shows the status's text (paintAll, from the seam's onRendered): the wait is over. */
  private bytesLanded(): void {
    if (!this.bytesWait) return;
    clearTimeout(this.bytesWait); this.bytesWait = null;
    this.busy.delete("bytes");
  }
  /** The deadline: the fetch neither landed nor told the seam it failed. The loader yields to a row, and its Reload
   *  re-fetches the bytes and re-asks status (fcreload) — the loader never traps the person (ui/CLAUDE.md). */
  private bytesLate(): void {
    this.bytesWait = null;
    if (!this.busy.has("bytes")) return;
    this.busy.delete("bytes");
    this.errors.set("bytes", { text: "The file's new contents have not arrived after " + STATUS_DEADLINE_MS / 1000
      + " s; the view still shows the earlier text, with no change marked on it. Reload to read the file again.", reload: true });
    this.render();
  }

  // ── Track changes ──────────────────────────────────────────────────────────────────────────────
  /** With no status behind it (refused, or never answered) the toggle showed "off" on nothing: re-ask under
   *  this control the way every other mutating control does (requireStatus: a second refusal is the row under
   *  the toggle, "Nothing written: …"), with the slot's loader for the wait. On an answer, act on what the
   *  click meant — turning tracking ON, since off is what showed: an untracked file gets the scope row; one
   *  that turns out tracked now reads so, which was the ask, and a second click stops it as usual. Never a
   *  click that only pulses (ui/CLAUDE.md: the result follows the acknowledgement). */
  async onTrackClick(): Promise<void> {
    let s = this.status;
    if (!s) {
      if (this.busy.has("track")) return;
      this.busy.add("track"); this.errors.delete("track"); this.render();
      try { if (!(await this.requireStatus("track"))) return; }
      finally { this.busy.delete("track"); this.render(); }
      s = this.status;
      if (!s) return;
      if (!s.trackedBy) { this.trackChoice = true; this.trackStop = false; this.render(); }
      return;
    }
    if (!s.trackedBy) { this.trackChoice = !this.trackChoice; this.trackStop = false; this.render(); return; }
    if (s.trackedBy.kind === "folder") { this.trackStop = !this.trackStop; this.trackChoice = false; this.render(); return; }
    // a file entry turns off directly; an inherited one is refused by the kernel naming the parent — the row shows it
    void this.mutate("set-tracked", { on: false, scope: "file" }, "track");
  }

  // ── commenting ─────────────────────────────────────────────────────────────────────────────────
  onSelection(sel: Selection): void {
    if (!this.open || this.ctx.mode() === "media" || !sel.rangeCount) return;
    // the seam fires for any selection inside the viewer's box, the aside included: a passage is text of the
    // FILE, so a selection in a card, the Log or the message preview offers nothing (it would only be refused)
    const body = this.ctx.body();
    if (!body.contains(sel.anchorNode) || !body.contains(sel.focusNode)) return;
    const rect = sel.getRangeAt(sel.rangeCount - 1).getBoundingClientRect();
    if (!rect.width && !rect.height) return;
    this.imageTarget = null;                           // a text selection replaces a picture as the float's subject
    this.showFloat(rect);
  }
  private showFloat(rect: { right: number; top: number }, img: HTMLElement | null = null): void {
    const x = Math.min(Math.max(8, rect.right + 6), window.innerWidth - 90);
    const y = Math.min(Math.max(8, rect.top - 30), window.innerHeight - 34);
    this.float.style.left = x + "px"; this.float.style.top = y + "px";
    this.float.hidden = false;
    this.floatAt = { top: rect.top, right: rect.right, img };
  }
  /** The float's subject as it sits on screen now: the picture's box, or the live selection's last range (null once the
   *  selection is gone or collapsed, or the picture has left the document); what hideFloatOnScroll compares with floatAt. */
  private floatSubjectRect(): { top: number; right: number } | null {
    const at = this.floatAt;
    if (!at) return null;
    if (at.img) return at.img.isConnected ? at.img.getBoundingClientRect() : null;
    const sel = window.getSelection();
    if (!sel || !sel.rangeCount) return null;
    const r = sel.getRangeAt(sel.rangeCount - 1).getBoundingClientRect();
    return r.width || r.height ? r : null;
  }
  /** A click on a rendered picture (the plan's Images and PDFs): with the panel open, the float offers
   *  Comment beside it; the anchor will be the embed's source text. A picture the source holds no embed
   *  for (an `src` the sanitizer rewrote, say) still gets the offer, and the composer then says why it
   *  cannot be placed — the offer must not silently do nothing. */
  onImageClick(img: HTMLElement): void {
    if (!this.open || this.ctx.mode() !== "rendered") return;
    const root = this.contentRoot(); const src = this.ctx.text();
    if (!root || src === null || !root.contains(img)) return;
    const e = embedFor(img, root, src, this.ctx.path);
    this.imageTarget = { range: e ? { start: e.start, end: e.end } : null };
    this.showFloat(img.getBoundingClientRect(), img);
  }
  startImageComment(range: SourceRange | null): void {
    const src = this.ctx.text();
    if (src === null) return;
    const was = this.composer;
    this.openPanel();
    this.composer = range
      ? { kind: "comment", range, quote: src.slice(range.start, range.end), text: src, refusal: null }
      : { kind: "comment", range: null, quote: null, refusal: { ok: false, rawHasQuote: false, selText: "", reason: EMBED_NOT_FOUND_SELECT } };
    this.errors.delete("composer");
    this.repaintPresel();
    this.renderFrom(was);
    this.input.focus();
  }
  private contentRoot(): Element | null {
    const mode = this.ctx.mode();
    if (mode === "media") return null;
    return this.ctx.body().querySelector(mode === "rendered" ? ".fileview-md" : "code.hljs");
  }
  startComment(sel: Selection): void {
    const src = this.ctx.text(); const root = this.contentRoot();
    if (src === null || !root) return;
    const selText = sel.toString();
    const res = this.ctx.mode() === "rendered" ? mapRenderedSelection(sel, root, src) : mapRawSelection(sel, root, src);
    const was = this.composer;
    this.openPanel();
    // a selection over a deletion's struck label alone (the about follow-on, section 3): the label is not text of the
    // file, so no passage can carry the comment; the box offers a comment about that change, by id alone (deletionUnder)
    const del = !res.ok || res.range.end <= res.range.start ? this.deletionUnder(sel) : null;
    if (del !== null) this.composer = { kind: "comment", range: null, quote: null, refusal: null, about: { ids: [del], on: true, only: true } };
    else if (res.ok) {
      // a selection wholly or partly inside pending changes' marks (overlapping): an ordinary passage comment, with the
      // option to name those changes checked; unchecked it is a passage comment like any other (the about follow-on)
      const ids = this.overlapping(res.range);
      this.composer = { kind: "comment", range: res.range, quote: res.quote, text: src, refusal: null, ...(ids.length ? { about: { ids, on: true, only: false } } : {}) };
    }
    else this.composer = { kind: "comment", range: null, quote: null, refusal: { ...res, selText } };
    this.errors.delete("composer");
    this.repaintPresel();
    this.renderFrom(was);
    this.input.focus();
  }
  startFileComment(): void {
    const was = this.composer;
    this.composer = { kind: "comment", range: null, quote: null, refusal: null };
    this.errors.delete("composer");
    this.repaintPresel();
    this.renderFrom(was);
    this.input.focus();
  }
  /** Reply on a comment: the box opens INSIDE the card it answers — below the comment's turns, above its buttons
   *  (placeComposer) — so the answer is written where the question is read (the user, 2026-09-07, after walking the
   *  loop); the card opens for it and stays open while the reply is written (renderCard, the fccard handler). */
  startReply(id: string): void {
    const card = this.cards().find((c) => c.id === id);
    if (!card) return;
    this.openCards.add(this.cardKey(id));
    this.composer = { kind: "reply", commentId: id, ref: card.ref, resolved: card.resolved };
    this.errors.delete("composer");
    this.repaintPresel();
    this.render();
    this.showComposer();                               // the card's foot, where the box now stands, into view when it is not
    this.input.focus();
  }
  /** The key of the card the reply being written stands in, latched into the keyed expand state. startReply latches the key
   *  at click time, but a comment's card can change key under an open reply: its change accepted or rejected (the person's
   *  Accept on the same card, the Send's accept, a decision elsewhere) moves it from the change card ("chg:…") to its own
   *  card (cardKey), which the list then showed open only by derivation from the composer — so the first render after the
   *  composer closed, or changed kind, folded it with no gesture and no new information (CLAUDE.md), taking the Reply the
   *  keyboard had just been handed to. Latched at every render, the card stays open by key once the box has left it. */
  private latchReplyCard(): void {
    const r = this.replyTo();
    if (r !== null) this.openCards.add(this.cardKey(r));
  }
  /** The comment whose reply is being written, when the composer is one. */
  private replyTo(): string | null { return this.composer && this.composer.kind === "reply" ? this.composer.commentId : null; }
  /** The head of the card holding the reply being written. The fccard handler folds every card but this one (a fold would
   *  take the box and the words with it), so a press here changes nothing — and a live, expanded button that answers a
   *  press with nothing leaves the person guessing and tells assistive tech the card will collapse (ui/CLAUDE.md, the
   *  click rule). The head says so instead: aria-disabled for the reader, a title for the pointer; it stays a Tab stop, so
   *  the keyboard still reaches the card and the words in it. Save or Cancel frees it. On a coarse pointer the same words
   *  stand under the head as a line (heldNote): a title never reaches touch, and a tap on the head that folds nothing and
   *  says nothing is the pattern this panel's other captions exist to avoid (renderSend, renderChangesFoot; the Re-place
   *  button's presence turns on the pointer the same way). A fine pointer reads the title, and the line stays off: the
   *  card keeps its compact form (ui/CLAUDE.md). */
  private holdHead(head: HTMLElement): void {
    head.setAttribute("aria-disabled", "true");
    head.title = HOLD_WORDS;
  }
  /** The line under a held head on a coarse pointer (holdHead); null on a fine one, where the title reaches. */
  private heldNote(): HTMLElement | null {
    return isCoarsePointer() ? el("div", "fc-note fc-held", HOLD_WORDS + ".") : null;
  }
  /** Whether the card with this expand key holds the reply being written: the comment's own card (cardKey; until the about
   *  follow-on, 2026-09-10, the change card hosting the comment could be that card). */
  private hostsReply(key: string): boolean { const r = this.replyTo(); return r !== null && this.cardKey(r) === key; }
  /** Comment on this change (the about follow-on, 2026-09-10; before it, Reply, which wrote a comment bound to the change
   *  by the format's own field): the composer opens in the panel's slot anchored over the change's span in the current
   *  text, as a selection of it would open it, with the about option checked for the change (changeIds [id] on save;
   *  the message says "about your change …"). A change with no span in the text (a deletion, whose text is not in the
   *  file; a detached change) takes the comment by id alone, laid at the change's mark while it is pending (markTop).
   *  The span is cut from the text the change's offsets index (indexedText): the status's text, which while the editor is
   *  up is the file as the editor loaded it, never the buffer — the buffer moves under the offsets with every unsaved
   *  keystroke, and a span cut from it quoted and anchored other words (the review, 2026-09-10). And only while the view's
   *  text IS that text (spanCarried): over other bytes the card offers no Comment on this change for a spanned change
   *  (renderChangeCard), since the span would name the wrong words and a comment by id alone would lose the passage the
   *  change has; a deletion's is by id whatever the view shows. */
  startChangeComment(id: string): void {
    const c = this.changeView().cards.find((x) => x.id === id);
    if (!c) return;
    const s = this.status;
    const spanned = !c.detached && c.curTo > c.curFrom;
    if (spanned && !this.spanCarried(c)) return;       // the card offers no button in this state (renderChangeCard); a click that reached here anyway writes nothing
    this.openCards.add(c.key);
    if (spanned) {
      const src = this.indexedText()!;                 // non-null: spanCarried
      const off = s!.bom ? 1 : 0;                       // the host's offsets run one ahead of the view's on a BOM file (viewAt)
      const range = { start: Math.max(0, c.curFrom - off), end: Math.max(0, c.curTo - off) };
      this.composer = { kind: "comment", range, quote: src.slice(range.start, range.end), text: src, refusal: null, about: { ids: [id], on: true, only: false } };
    } else {
      this.composer = { kind: "comment", range: null, quote: null, refusal: null, about: { ids: [id], on: true, only: true } };
    }
    this.errors.delete("composer");
    this.repaintPresel();
    this.render();                                     // the change card opens for it: the cards too, whatever `was` (renderFrom renders the composer alone otherwise)
    this.input.focus();
  }
  /** Whether the view carries a spanned change's text where its offsets say (startChangeComment, renderChangeCard): a text to
   *  cut the span from (indexedText: the view's, or the file as the editor loaded it), the status's — not the bytes of a
   *  reject's reply before its reload lands, or of the poll's reload before its status (textCurrent; renderChangeCard's
   *  inFlux, which withholds an unpainted insertion's Reveal on the same ground) — and a view that shows text at all (not
   *  the picture of a media file). A deletion has no span to carry and never asks. */
  private spanCarried(c: ChangeCard): boolean {
    const s = this.status;
    return !!s && this.textCurrent(s) && this.indexedText() !== null && this.ctx.mode() !== "media";
  }
  /** The pending changes whose marks a selection's range overlaps (the about follow-on): an insertion's or a
   *  substitution's span sharing any character with the range, a deletion's point strictly inside it (a selection that
   *  ends at the point does not reach across the removed text). In text order. The hunks index the status's text, so
   *  nothing while the view shows other bytes (textCurrent); on a BOM file the view's offsets run one behind the host's. */
  private overlapping(range: SourceRange): string[] {
    const s = this.status;
    if (!s || !this.textCurrent(s)) return [];
    const off = s.bom ? 1 : 0;
    const start = range.start + off, end = range.end + off;
    const out: string[] = [];
    for (const h of [...(s.hunks || [])].sort((a, b) => a.curFrom - b.curFrom || (a.ts || 0) - (b.ts || 0))) {
      const hit = h.curFrom === h.curTo ? start < h.curFrom && h.curFrom < end : h.curFrom < end && h.curTo > start;
      if (hit) out.push(String(h.id));
    }
    return out;
  }
  /** The one deletion mark of the panel's a selection intersects, by change id, or null: the struck label is generated
   *  text under user-select none, so a selection over it alone holds no text of the file (the mapping refuses or maps an
   *  empty range), and the change it marks is what the person selected. Several marks, or none, is nothing to claim.
   *  Nor is a selection that HOLDS text of the file (its string, which generated text never enters): the mapping refused
   *  it for a reason of its own — it reaches outside the file text, it touches a table in Rendered — and that refusal,
   *  with its Switch to Raw, is the answer; a deletion mark under such a selection is not what the person selected, and
   *  a comment about it in the refusal's place answered a selected passage with a change (the review, 2026-09-10). */
  private deletionUnder(sel: Selection): string | null {
    if (!sel.rangeCount) return null;
    if (sel.toString().trim() !== "") return null;
    const marks = Array.from(this.ctx.body().querySelectorAll('.fc-del[data-act="fcchange"]')).filter((m) => this.marks.has(m)) as HTMLElement[];
    const hit = new Set<string>();
    for (let i = 0; i < sel.rangeCount; i++) {
      const r = sel.getRangeAt(i);
      if (typeof r.intersectsNode !== "function") return null;
      for (const m of marks) if (m.dataset.id && r.intersectsNode(m)) hit.add(m.dataset.id);
    }
    return hit.size === 1 ? Array.from(hit)[0] : null;
  }
  /** The change card's "N comments" tag (the about follow-on): the first open comment about the change into view as the
   *  focus, All chosen first when Changes hides the comment cards (the row that shows them). */
  private showAbout(changeId: string): void {
    const first = commentsAbout(this.cards(), changeId)[0];
    if (!first) return;
    if (this.activeFilter() === "changes") this.setFilter("all");
    this.showCard(first.id);
  }
  /** Light or unlight the marks of the changes a comment's tag names (the about follow-on): the class the sheets ring,
   *  on every mark the panel painted for those ids; `lit` remembers them so a render (which rebuilds the tag under the
   *  pointer, and with it the leave event) can unlight them first. */
  private lightChanges(ids: string[], on: boolean): void {
    for (const id of ids) {
      for (const m of this.ownMarks("fcchange", id)) m.classList.toggle("fc-lit", on);
      if (on) this.lit.add(id); else this.lit.delete(id);
    }
  }
  closeComposer(): void {
    const was = this.composer;
    const held = this.composerBox.contains(document.activeElement);   // the keyboard is in the box (the textarea, Save, Cancel)
    this.composer = null;
    this.input.value = "";
    this.input.style.height = ""; this.sizedTo = null;   // the next comment starts at COMPOSER_ROWS, autosized again
    this.errors.delete("composer");
    this.repaintPresel();
    this.renderFrom(was);                              // …which puts the box back in the panel's slot (placeComposer); after a reply, the cards too
    // a reply's box leaves its card hidden, and a hidden box drops the keyboard to the body: it goes back to the Reply that
    // opened the box instead, so a person on the keyboard keeps their place on the card (Escape, Cancel and a save alike)
    if (was && was.kind === "reply" && held) (this.root?.querySelector('[data-act="fcreply"][data-id="' + cssId(was.commentId) + '"]') as HTMLElement | null)?.focus({ preventScroll: true });
    if (was && was.kind === "reply" && held) this.focusAway(was);   // …or, with no Reply rendered for the comment, to the row that brings its card back
  }
  /** The box after the composer changed from `was`: the composer alone, unless a reply was closed or replaced by another
   *  kind (Cancel, a save, Comment on this file, a selection's or a picture's Comment, a region drawn) — then the cards
   *  too, at once: the head of the card that held the reply is free again (holdHead), and the cards say so before the
   *  next status, not after it. Before this, the kind changes rendered the composer alone, and the head kept its
   *  aria-disabled and its title while a click on it already folded the card. */
  private renderFrom(was: Composer | null): void {
    if (was && was.kind === "reply") this.render(); else this.renderComposer();
  }
  /** The keyboard when a reply's box closed under it and the list shows no card for the comment — the box stood in the
   *  slot (placeComposer), so no Reply of that comment is rendered for closeComposer to hand it to, and a hidden box
   *  drops it to the body. It goes to the row that brings the card back — the Resolved fold, the "… N more changes" row
   *  (replyAway names it) — and with no such row (the comment gone from the sidecar, a status not yet in) to the nearest
   *  control below the slot (focusNear: the first card's head, the changes foot, Send, Comment on this file), so a person
   *  on the keyboard keeps a place in the panel. Nothing while the Reply is rendered: closeComposer put the keyboard on it. */
  private focusAway(was: { commentId: string; resolved: boolean }): void {
    const root = this.root;
    if (!root || root.querySelector('[data-act="fcreply"][data-id="' + cssId(was.commentId) + '"]')) return;
    const back = this.replyAway(was).back;
    const row = back ? root.querySelector('[data-act="' + back + '"]') as HTMLElement | null : null;
    if (row) row.focus({ preventScroll: true });
    else this.focusNear({ act: "fcreply", id: was.commentId, at: 0 });
  }
  /** The mapping refused in Rendered: switch to Raw, and when the selected text occurs in the source,
   *  target that passage — the one in the refused block, not an earlier copy of the same words
   *  (rawTarget) — so the presel mark shows it; otherwise scroll to the block's first line and leave the
   *  note waiting for a Raw selection. */
  switchToRaw(): void {
    let c = this.composer;
    if (c && c.kind === "region" && c.refusal) {
      // a region on a figure the source holds no embed for: nothing to anchor a region to, but a passage on the embed's
      // line can still carry the note. The composer becomes the one the picture click's offer builds for the same
      // figure (startImageComment), awaiting a Raw selection; the typed note stays in the input, the pending rectangle
      // leaves the overlay. The refusal's own sentence used to send the person to Cancel — the one exit that drops the note.
      c = this.composer = { kind: "comment", range: null, quote: null, refusal: { ok: false, rawHasQuote: false, selText: "", reason: EMBED_NOT_FOUND_SELECT } };
      this.errors.delete("composer");
      this.repaintPresel();
    }
    if (!c || c.kind !== "comment" || !c.refusal) return;
    this.ctx.setMode("raw");
    const src = this.ctx.text();
    if (src === null) return;
    const r = c.refusal;
    const range = rawTarget(src, r);
    if (range) {
      c.range = range; c.quote = src.slice(range.start, range.end); c.text = src; c.refusal = null;
      this.errors.delete("composer");                  // an Enter pressed under the refusal is answered now
      this.ctx.scrollToOffset(range.start);
      this.repaintPresel();
      this.renderComposer();
      this.input.focus();
      return;
    }
    if (typeof r.blockStartLine === "number") this.ctx.scrollToOffset(lineStartOffset(src, r.blockStartLine));
    this.renderComposer();
  }
  async saveComposer(): Promise<void> {
    const c = this.composer;
    const note = this.input.value.trim();              // the blank ends go, the line breaks inside stay; all blank saves nothing
    if (!c || c.kind === "replace" || !note) return;   // a re-place takes a drag, not words
    if (c.kind === "region" && c.refusal) {
      this.errors.set("composer", { text: "Nothing saved: " + c.refusal + ".", reload: false });
      this.renderComposer();
      return;
    }
    if (c.kind === "comment" && c.refusal) {
      // nothing to save TO: the selection could not be placed, and a save here would silently become a
      // whole-file comment — the passage the person selected lost, and the session told "on this file"
      this.errors.set("composer", { text: "Nothing saved: select the passage in the Raw view first (Switch to Raw), or Cancel and use Comment on this file for a note on the whole file.", reload: false });
      this.renderComposer();
      return;
    }
    if ((c.kind === "comment" || c.kind === "region") && c.elsewhere) {
      // the edit reached the passage and its text is now intact only at a copy the edit never touched (followPassage):
      // the host, handed the anchor, would find that one hit and place the note there — its exact-hint check runs on a
      // tie alone — so the refusal is made here, the note stays, and the person selects or draws again
      this.errors.set("composer", { text: c.kind === "region" ? EMBED_ELSEWHERE_SAVE : PASSAGE_ELSEWHERE_SAVE, reload: false });
      this.renderComposer();
      return;
    }
    // the comment ids before the write, for the two readers of the reply: the store's for savedCommentId (the scroll to the
    // saved card), the model's cards' for noteHiddenSave (the line for a card the filter hides) — the same ids, cardModel
    // building one card per store comment
    const had = new Set((this.status && this.status.store ? this.status.store.comments : []).map((x) => x.id));   // the comments before the write (savedCommentId)
    const before = new Set(this.cards().map((x) => x.id));   // the comments before the save, so the saved one can be told apart (noteHiddenSave)
    // the save is a gesture of the person's (the arrivals follow-on): the arrival cards on screen are seen
    this.gesture();
    let r: Status | null;
    if (c.kind === "reply") r = await this.mutate("reply", { commentId: c.commentId, note }, "composer");
    else if (c.kind === "region") {
      // the target in fractions of the natural size (E1), the host stamping the hash; a figure in rendered markdown
      // also carries the embed line's anchor, built over the text its range indexes as for a passage comment
      const args: Record<string, unknown> = { note, target: regionTarget(c.region, c.src, c.page) };
      if (c.range && c.text !== undefined) { args.anchor = makeAnchor(c.text, c.range); args.hintOffset = c.range.start; }
      if (c.tied) delete args.hintOffset;                // a tied pair (retargetComposer): the start indexes other text; the passage path below says why
      r = await this.mutate("comment", args, "composer");
    } else {
      const args: Record<string, unknown> = { note };
      // the anchor is built over the text the range indexes (the selection's own, or the reload the passage
      // was re-found in), never over whatever sits at those offsets now; the host re-reads the file and
      // relocates by this anchor and hint, or refuses — a note aimed at one passage never lands on another
      const src = c.text === undefined ? null : c.text;
      if (c.range && src !== null) { args.anchor = makeAnchor(src, c.range); args.hintOffset = c.range.start; }
      // a tied pair (retargetComposer): the start indexes other text, and the host would settle the tie by it — nearest
      // wins, by coincidence — and save the note on a copy the person never selected. With no offset it refuses a tie
      // still standing (anchor-ambiguous), the note stays, and the passage is selected again.
      if (c.tied) delete args.hintOffset;
      // the changes the comment is about (the about follow-on): the option checked, or the change alone with no passage
      if (c.about && c.about.on) args.changeIds = c.about.ids;
      r = await this.mutate("comment", args, "composer");
    }
    const hid = r !== null && c.kind !== "reply" && this.noteHiddenSave(before, note);
    const lined = r !== null && this.landSaved(c, had, r, note);   // the saved card the focus for the layout, and the line when it is out of view — before the composer closes (landSaved says why); no line for a card the filter hides (hid: its own line says where it is)
    if (r) this.closeComposer();                       // a refusal keeps the note where it was typed
    if (hid || (lined && c.kind !== "reply")) this.render();   // the cards were rendered with the reply before the saved comment was known (hid: once more, with its line); a comment's close re-renders the composer alone (renderFrom), so the saved line needs this render — a reply's close rendered the panel whole
    if (r && !lined && !hid && !this.margin) this.landClosed(c, had, r, note);   // the list layout: the box's close lifted the cards, and a card whole in view a moment ago may stand above the box now (landClosed)
  }
  /** After a comment is saved (not a reply): while the filter shows the changes alone, the fresh card and its mark are
   *  hidden (renderCards, paintAll), and a save that shows nothing reads as a save that failed — the person may write the
   *  comment again. The saved comment's id is kept (hiddenSaved) and the list says so where the card would be
   *  (hiddenSavedRow); the kept choice is not changed for it, as it is not for a reply's box (replyAway). The fresh
   *  comment is the one the list did not hold before the save — with several landed at once (another client's, a
   *  session's), the one with the person's words. Every comment is its own card (the about follow-on, 2026-09-10), a
   *  comment about a change too, so under Changes every save is hidden. Returns whether the line is due. */
  private noteHiddenSave(before: Set<string>, note: string): boolean {
    const fresh = this.cards().filter((x) => !before.has(x.id));
    const mine = fresh.find((x) => x.author === "you" && x.body === note) || fresh[fresh.length - 1] || null;
    if (!mine || this.activeFilter() !== "changes") return false;
    this.hiddenSaved = mine.id;
    return true;
  }
  /** The card a save landed in: made the focus for the layout, so the pass lays it level with its mark wherever that is,
   *  and when it stands out of view once the save's status has landed, named in the line at the panel's foot (savedLine).
   *  Nothing scrolls (decision 43, 2026-09-09: the user prefers the view left where it is after a save, a scroll being
   *  disruptive, and accepts that the card may then have to be looked for — the line is the answer to that). Before it,
   *  the save scrolled the text to the card (the 2026-09-07 review: a whole-file comment's card, loose at the top of the
   *  track, appeared nowhere with the text scrolled down, and the save read as having done nothing) and then stood down
   *  when a gesture of the person's came between Save and the reply (the arrivals follow-on: a reply's landing had pulled
   *  the text back from the passage they had scrolled on to). BEFORE the composer closes: the reply's render placed the
   *  cards with the composer's box above the track, and the pass that follows the close (the track's observer) re-places
   *  them with the header as it is then, at the same places on screen — the focus set now is the one that pass lays on.
   *  `had`: the comment ids before the write (savedCommentId names the new one off the reply). A comment saved while the
   *  filter shows the changes alone has no card in the list and no mark in the text (renderCards, paintAll): no focus and
   *  no line here — the line noteHiddenSave raises (hiddenSavedRow) says where the card is. The side is read once here and
   *  again at the end of every pass and at every scroll while the line stands (reflectLines), where the geometry is
   *  settled: the composer's close re-lays the cards — a reply's box leaves its card, which the pass measured with the box
   *  in it, and a comment's slot leaves the track's box, which grows by it — and can bring the card into the box, and the
   *  line ends with that (the acknowledgment it displaced comes back: restoreSent).
   *  Returns whether the line was raised: a comment's save renders it then (saveComposer), the composer's close
   *  re-rendering the composer alone. */
  private landSaved(c: Composer, had: Set<string>, r: Status, note: string): boolean {
    const saved = c.kind === "reply" ? c.commentId : savedCommentId(had, r, note);
    if (saved === null) return false;
    const key = this.cardKey(saved);
    if (this.margin) this.focusOn(key);
    const side = this.cardWhere(key);
    if (side === null) return false;                   // whole in view, or no card to point at
    this.savedOut = { key, side };
    // the margin layout: the position is the line's while it stands (renderSend), and an earlier send's acknowledgment gives
    // way to it — kept (sentAck) to come back in its place when the line ends (restoreSent; the field's comment has the case
    // that lost it). The list layout's line stands under the header (savedLineHead), and the acknowledgment keeps its place
    // at the foot: cleared there too, it went for no reason of position, and only when the card landed out of view (the
    // review, 2026-09-09)
    if (this.margin) this.sentNote = null;
    return true;
  }
  /** Which side of the box the person can see a card stands on — "above" when the card's top is above the box's top,
   *  "below" when it is not whole in the box otherwise (its top in the box and its end past it, or the whole card past
   *  it) — or null for a card whole in the box, and for one not rendered or not placed (the filter hides it, a fold holds
   *  it): nothing to point at. In the margin layout the placement's top and height against the track's scroll and box (the
   *  pass has just placed the fresh cards: render runs it before landSaved); in the list layout the card's box against the
   *  aside's and the window's. */
  private cardWhere(key: string): "above" | "below" | null {
    if (this.margin) {
      const p = this.placed.get(key);
      if (!p) return null;
      const track = this.sections.cards, at = track.scrollTop;
      if (p.top < at) return "above";
      return p.top + p.height <= at + track.clientHeight ? null : "below";
    }
    const card = this.root?.querySelector('.fc-card[data-id="' + cssId(key) + '"]');
    if (!card || !this.root) return null;
    const r = card.getBoundingClientRect(), box = this.root.getBoundingClientRect();
    if (r.height <= 0) return null;
    if (r.top < box.top) return "above";
    return r.bottom <= Math.min(box.bottom, window.innerHeight) ? null : "below";
  }
  /** The list layout, after the composer closed (saveComposer): landSaved read the side with the box still in the aside's
   *  flow above the cards (placeComposer's slot), and the close lifts every card by the box's height — a card whole in view
   *  at the landing can stand above the aside's box now, with no line and nothing to re-read it (every re-read is gated on
   *  the line standing). The side is read once more here, at the settled geometry, and the line raised the way landSaved
   *  raises it (the review, 2026-09-09). An engine with scroll anchoring keeps the card where it was on screen and reads
   *  null here; one without (WebKit before its 27, the phone) reads the card above. The margin layout needs none of this: its
   *  close grows the track's box, and the pass at its end re-reads (placeCards). */
  private landClosed(c: Composer, had: Set<string>, r: Status, note: string): void {
    const saved = c.kind === "reply" ? c.commentId : savedCommentId(had, r, note);
    if (saved === null) return;
    const key = this.cardKey(saved);
    const side = this.cardWhere(key);
    if (side === null) return;
    this.savedOut = { key, side };                     // the list layout's line: the acknowledgment keeps its place (landSaved)
    this.render();                                     // the line into the panel (renderHead)
  }

  // ── the arrivals (the arrivals follow-on, 2026-09-09; the fields' comment says the rule) ───────────
  /** A status landed: the entries in it that the person has not seen and did not write are arrivals (arrivalsAmong's
   *  rule, kept here as a map so an arrival's order and its entry survive); the person's own writes join the seen set
   *  outright; an arrival the status no longer holds (a change decided, a comment gone) is no arrival. An arrival still
   *  standing takes the status's entry for it, in its place in the order: a change keeps its key when the sidecar's rebase
   *  detaches it (store.detached) or re-attaches it as a hunk, and the entry's `pending` says which it is now: the line
   *  under the header counts it as a change either way, and the texts check below reads a pending one alone (the review,
   *  2026-09-09; before decision 41 the accept option's own arrivals count read this flag, and that count went to the seen
   *  split, partitionPending). A SEEN pending change whose texts are not the ones the person saw (seenTexts, grownSince: a
   *  same-author track-edit coalesced into it under the same id) is unseen again — out of the set, filed as an arrival
   *  like a new change, unless it is the person's own — and a seen pending change with no record yet (seen while detached,
   *  re-attached since) is recorded as it stands. Nothing until the first render seeded the set (render), and the first
   *  status to land while the panel is open is all seen too (seenOpen): a newly opened panel's first status is never an
   *  arrival. */
  private noteArrivals(s: Status): void {
    const seen = this.seenKeys;
    if (seen === null) return;
    const entries = statusEntries(s);
    // the first status to land while the panel is open is the newly opened panel's first (the fields' comment): the render
    // seeded the set from the probe's status, asked with the panel closed, and everything this one adds is seen as well. One
    // landing while closed — the open's re-ask answered after a close — is nobody's first: the reopen's own is
    if (!this.seenOpen && this.open) this.recordPending(s);   // …with its pending changes' texts (seenTexts), for the seed below
    if (!this.seenOpen) {
      if (!this.open) return;
      this.seenOpen = true;
      for (const e of entries) seen.add(e.key);
      return;
    }
    const now = new Set(entries.map((e) => e.key));
    for (const k of Array.from(this.arrivals.keys())) if (!now.has(k)) this.arrivals.delete(k);
    for (const k of Array.from(this.seenTexts.keys())) if (!now.has(k)) this.seenTexts.delete(k);   // a change gone from the status (decided, or its record pruned) has no texts to hold
    for (const e of entries) {
      if (seen.has(e.key)) {
        // a seen pending change reads as the person saw it: seen still (recorded now if it has no record yet); one that reads
        // differently is text they have not seen — out of the set, and the rule below files it as any other entry
        if (!e.pending || !this.grownSince(e.key, s)) { if (e.pending) this.recordSeen(e.key, s); continue; }
        seen.delete(e.key); this.seenTexts.delete(e.key);
      }
      if (this.arrivals.has(e.key)) { this.arrivals.set(e.key, e); continue; }   // refreshed in place: a Map's set on a key it holds keeps the order
      if (e.author === YOU) this.recordSeen(e.key, s);   // the person's own write: its texts are seen text (seenTexts)
      if (e.author === YOU) seen.add(e.key);
      else this.arrivals.set(e.key, e);
    }
  }
  /** The texts of a seen pending change, kept with its key (seenTexts; the field's comment): the status's hunk under that
   *  key, as it reads now. Nothing for a key that names no pending change of `s` — a comment, a reply, a detached change. */
  private recordSeen(key: string, s: Status | null = this.status): void {
    if (!key.startsWith("chg:")) return;
    for (const c of seenChanges(s, { ids: [key.slice(4)] })) this.seenTexts.set(key, c);
  }
  /** Every pending change of `s` recorded as seen text (the seeds: the render's, the first open status's). */
  private recordPending(s: Status): void {
    for (const h of s.hunks || []) this.recordSeen("chg:" + String(h.id), s);
  }
  /** Whether a seen pending change reads differently now from the texts the person saw (seenTexts): the same comparison the
   *  decisions stand down on (changedSince). A change with no record is not grown: there is nothing to compare it with. */
  private grownSince(key: string, s: Status): boolean {
    const rec = this.seenTexts.get(key);
    return !!rec && changedSince([rec], s.hunks || []).length > 0;
  }
  /** The card an entry shows on: a change's own; a comment's or a reply's the comment's own card (cardKey, as the list
   *  shows it; until the about follow-on, 2026-09-10, a comment bound to a pending change showed on the change's card). */
  private arrivalCard(e: Entry): string {
    return e.subject.startsWith("chg:") ? e.subject : this.cardKey(e.subject);
  }
  /** A gesture of the person's (the constructor's listeners; saveComposer; doSend): while arrivals stand, every arrival
   *  whose card is on screen now is seen; and the saved line (savedLine) is over. A press or a key on the arrivals line
   *  itself marks nothing: its click shows the first arrival, and the line must survive the click for the glance it was
   *  clicked for. A press or a key on the saved line itself ends nothing, for the same reason: its click shows the card. A
   *  Tab or a modifier pressed alone is no gesture at all (NAV_KEYS): it is how the keyboard reaches either line. */
  gesture(ev?: Event): void {
    if (!this.open) return;
    const t = ev ? (ev.target as Element | null) : null;
    const kb = ev && ev.type === "keydown" ? (ev as KeyboardEvent) : null;
    if (kb && NAV_KEYS.has(kb.key)) return;             // a Tab or a modifier alone moves the keyboard and presses nothing (NAV_KEYS)
    // a press, a key or a touch on a control — never a wheel, which scrolls and presses nothing: a wheel over the saved line is
    // the scroll the line says it goes with (the review, 2026-09-09). A touch move is kept: a jittery tap on the line moves
    // too, and its click reads the latch (fcsavedgo).
    const on = (act: string): boolean => !!t && typeof t.closest === "function" && !!t.closest('[data-act="' + act + '"]') && (!ev || ev.type !== "wheel");
    const over = this.savedOut !== null && !on("fcsavedgo");   // the saved line is over at a gesture — not at a press on the line itself, whose click shows the card
    if (over) this.savedOut = null;
    // the Reopen all offer (decision 46) ends the same way: at a gesture, a press on the offer itself excepted (its click is what
    // it is for); the confirm's own buttons are the gesture that makes the offer, and the offer is set after their click
    const undo = this.reopenAll !== null && !on("fcreopenall");
    if (undo) this.reopenAll = null;
    // the key that sends is the send's own press (the fields' comment, sendPress): Enter or Space on the confirm's Send, the
    // chord in its note box (noteKey). It marks what is on screen seen like any gesture, and the confirm's option and count
    // row stay as the person read them (syncAcceptOption): the send that follows accepts what they say, and redraws the panel.
    // A pointer press needs none of this: the hold parks the change until the release, after the click (reflect).
    const press = !!kb && ((on("fcsendgo") && (kb.key === "Enter" || kb.key === " ")) || (t === this.noteBox && composerKeyAction(kb) === "save"));
    const keys = new Set<string>();
    if (this.arrivals.size && !on("fcarrivals")) {
      for (const [k, e] of Array.from(this.arrivals)) {
        if (!this.entryShown(e)) continue;
        keys.add(this.arrivalCard(e)); this.seenKeys?.add(k); this.recordSeen(k); this.arrivals.delete(k);
      }
    }
    const was = this.sendPress;
    if (press) this.sendPress = true;
    try {
      if (keys.size) this.reflectSeen(keys);
      else if (over || undo) this.reflect();
    } finally { this.sendPress = was; }
  }
  /** Whether an entry's card is on screen: in the margin layout, its placed top inside the track's box (the head, where
   *  the dot is, is what the person sees of a card cut by the box's bottom); in the list layout, the card's top inside the
   *  aside's box and the window's. A card not rendered — hidden by the filter, behind a fold — is not on screen. */
  private entryShown(e: Entry): boolean {
    const key = this.arrivalCard(e);
    const card = this.sections.cards.querySelector('.fc-card[data-id="' + cssId(key) + '"]');
    if (!card) return false;
    if (this.margin) {
      const p = this.placed.get(key);
      if (!p) return false;
      const track = this.sections.cards, at = track.scrollTop;
      return p.top >= at && p.top < at + track.clientHeight;
    }
    if (!this.root) return false;
    const r = card.getBoundingClientRect(), box = this.root.getBoundingClientRect();
    return r.height > 0 && r.top >= box.top && r.top < Math.min(box.bottom, window.innerHeight);
  }
  /** Arrivals just seen, reflected without a render: the dots come off their cards and marks in place (an attribute
   *  changes no layout, so a press under way keeps its target), and the lines follow (reflect). The next render reads the
   *  same state. */
  private reflectSeen(cards: Set<string>): void {
    for (const key of cards) {
      if (this.newKeys.has(key)) {
        const still = Array.from(this.arrivals.values()).some((e) => this.arrivalCard(e) === key);   // another arrival on the same card keeps its dot
        if (still) continue;
        this.newKeys.delete(key);
      }
      const card = this.sections.cards.querySelector('.fc-card[data-id="' + cssId(key) + '"]') as HTMLElement | null;
      if (card) delete card.dataset.new;
      const [act, id] = key.startsWith("chg:") ? ["fcchange", key.slice(4)] : ["fcopen", key];
      for (const m of this.ownMarks(act, id)) delete m.dataset.new;
    }
    this.reflect();
  }
  /** The lines that follow state between renders, rewritten in place (reflectLines) — through the row's press hold
   *  (pressHold): a line removed during a press moves what stands under the pointer (the list under the arrivals line; in
   *  the margin layout the Send button above the saved line, the Send section standing at the panel's foot), and the click
   *  would land on another control or none. A run deferred under a press replaces the one parked before it, so every
   *  caller defers the same whole run. */
  private reflect(): void {
    if (this.hold) void this.hold.defer(() => this.reflectLines()); else this.reflectLines();
  }
  /** The arrivals line under the header (rewritten, or removed with the last arrival); the Send confirm's accept option
   *  and count row, when it is up (renderSend's words and state, syncAcceptOption: a change this gesture marked seen is one
   *  the send now accepts, and a box that was disabled with nothing seen comes on); and the saved line (savedLine: the
   *  card's side now, or removed — the key with it — once the card is whole in view, gone from the list, or the person has
   *  moved on; the acknowledgment it displaced comes back in its place, restoreSent). */
  private reflectLines(): void {
    const b = this.root?.querySelector('[data-act="fcarrivals"]') as HTMLElement | null;
    if (b) { if (!this.arrivals.size) b.remove(); else b.textContent = this.arrivalText(); }
    const cb = this.root?.querySelector('input[data-opt="accept"]') as HTMLInputElement | null;
    if (cb && this.status) this.syncAcceptOption(cb, this.status);
    // the Reopen all offer ended at a gesture (decision 46): its line leaves in place, and the sent acknowledgment it stood in
    // for comes back where it was (the render puts the same back)
    const offer = this.root?.querySelector(".fc-reopen") as HTMLElement | null;
    if (offer && this.reopenAll === null) {
      if (this.sentNote) offer.parentNode?.insertBefore(el("div", "fc-note fc-sent", this.sentNote), offer);
      // the offer's button may hold the keyboard (Tab reaches it, and a wheel is the one gesture that ends the offer while it
      // does): removed under it, the focus would fall to the body and the next Tab start the page over (removeLine's rule)
      const held = offer.contains(document.activeElement);
      offer.remove();
      if (held) this.focusNear({ act: "fcreopenall" });
    }
    const line = this.root?.querySelector('[data-act="fcsavedgo"]') as HTMLElement | null;
    if (this.savedOut) {
      const side = this.cardWhere(this.savedOut.key);
      if (side === null) this.savedOut = null; else this.savedOut.side = side;
    }
    if (!this.savedOut) this.restoreSent(line);         // the line is over: the acknowledgment it displaced is back, where the line stood
    if (!this.savedOut) { if (line) this.removeLine(line); }
    else if (line) line.textContent = savedWhereWords(this.savedOut.side);
  }
  /** The saved line out of the panel (reflectLines). A line that holds the keyboard — reached by Tab and pressed with Enter,
   *  the keyboard's way to it (NAV_KEYS) — would take it to the body with the node (the browser's focus-fixup rule), and the
   *  next Tab would start the page over; it goes to the card the line pointed at (the button carries the card's key), or to
   *  the nearest control the panel offers (focusNear) — the review, 2026-09-09. */
  private removeLine(line: HTMLElement): void {
    const held = document.activeElement === line;
    line.remove();
    if (held) this.focusNear({ act: "fcsavedgo", card: line.dataset.id });
  }
  /** The saved line is over, and the acknowledgment it displaced at the foot (landSaved, the margin layout: sentNote
   *  cleared, sentAck kept) is back: in the field, for the next render (renderSend), and in place before the line when the
   *  line stands in the Send section (reflectLines ends it there with no render), so the foot shows the one or the other
   *  and never neither. Nothing when the acknowledgment shows already (the list layout's line never displaced it) or when
   *  none stands (fcsend cleared both: the confirm is up, and the next send's acknowledgment replaces it). `line` is null at
   *  the panel's close (closePanel): the field alone. */
  private restoreSent(line: HTMLElement | null): void {
    if (this.sentNote !== null || this.sentAck === null) return;
    this.sentNote = this.sentAck;
    if (line && line.parentNode && this.sections.send.contains(line)) line.parentNode.insertBefore(el("div", "fc-note fc-sent", this.sentNote), line);
  }
  /** The marks in the body of every card the render marks new (newKeys) wear the attribute too: after each paint pass the
   *  marks are fresh (paintAll unwraps and repaints them), and render runs after every pass. */
  private markNew(): void {
    for (const key of this.newKeys) {
      const [act, id] = key.startsWith("chg:") ? ["fcchange", key.slice(4)] : ["fcopen", key];
      for (const m of this.ownMarks(act, id)) m.dataset.new = "1";
    }
  }
  /** The arrivals line's click: the first arrival's card into view, opened, as the focus (showCard: the focus rule lays it
   *  level with its mark and centers the mark). The first in the list's own order among the arrivals the list shows; when
   *  the list shows none of them — the filter hides their kind — the filter goes to All, the way the All button takes it,
   *  and the first arrival is shown; a resolved comment's fold opens for a reply on it. */
  private goToArrival(): void {
    const keys = new Set(Array.from(this.arrivals.values(), (e) => this.arrivalCard(e)));
    if (!keys.size) return;
    let first = this.cardsInOrder().map((c) => c.dataset.id || "").find((k) => keys.has(k)) || null;
    if (first === null) {
      if (this.activeFilter() !== "all") this.setFilter("all");
      const e = this.arrivals.values().next().value as Entry;
      first = this.arrivalCard(e);
      const c = this.cards().find((x) => x.id === first);
      if (c && c.resolved) this.resolvedOpen = true;
    }
    this.showCard(first);
  }

  // ── highlights ─────────────────────────────────────────────────────────────────────────────────
  // the card model of the status showing, built once per status: it is a pure function of the status, which applyStatus
  // replaces whole and nothing mutates, so the status's identity is the key (cardsOf). Before the memo every reader rebuilt it
  // over the whole store, and gesture() reads it once per arrival (arrivalCard → cardKey) on every press, key, wheel and touch
  // move, so with hundreds of unseen replies one wheel tick held the page for tens of milliseconds rebuilding one model (the
  // review, 2026-09-09; file-comments-arrivals-review2.test.ts counts the builds through the store)
  private cardsOf: Status | null = null;
  private cardsMemo: Card[] = [];
  cards(): Card[] {
    if (!this.status) return [];
    if (this.cardsOf !== this.status) { this.cardsOf = this.status; this.cardsMemo = cardModel(this.status.store, this.status.hunks || [], this.status.log || [], this.status.decided); }
    return this.cardsMemo;
  }
  /** The change cards, their paragraph groups over the current text, and the fold (GROUP_LIMIT). */
  changeView(): { cards: ChangeCard[]; groups: ChangeGroup[]; shown: ChangeGroup[]; hidden: ChangeGroup[]; hiddenChanges: number } {
    const s = this.status;
    const cards = s ? changeCards(s.store, s.hunks || [], s.log || [], s.decided) : [];
    const groups = changeGroups(cards, this.ctx.mode() === "media" ? null : this.indexedText());
    return { cards, groups, ...foldGroups(groups, this.moreChangesOpen) };
  }
  /** The card a comment id opens: its own. Every comment is its own card since the about follow-on (2026-09-10);
   *  before it a comment bound to a pending change was drawn inside the change's card, and this answered "chg:" + the
   *  change's id for it while the filter showed change cards. The callers stay on this one function so the key of a
   *  comment's card is decided in one place. */
  cardKey(commentId: string): string {
    return commentId;
  }
  /** The filter the list and the marks obey: the kept choice while the file has a card to filter, else "all" — with
   *  nothing in the list the control is not offered (renderHead), and a kept "changes" must not turn the empty state
   *  into a line about changes. */
  activeFilter(): CommentsFilter {
    return filterOffered(this.status) ? this.filter : "all";
  }
  /** One of All · Comments · Changes chosen: the preference goes to the shared store (saveSettings) and the body is repainted
   *  at once from the status already here — the marks the filter hides come off, the cards follow — with no request. The
   *  option already chosen changes nothing (the delegate's flash has acknowledged the click). */
  private setFilter(f: CommentsFilter): void {
    if (f === this.filter || !FILTERS.includes(f)) return;
    this.filter = f;
    saveSettings({ commentsFilter: f });
    this.paintAll();
  }
  /** Expand and scroll to a card by key — a change card inside the fold unfolds it first. */
  showCard(key: string): void {
    if (key.startsWith("chg:")) {
      const v = this.changeView();
      if (v.hidden.some((g) => g.changes.some((c) => c.key === key))) this.moreChangesOpen = true;
    }
    this.openCards.add(key);
    this.focusCard = key;                               // the focus: the render's pass lays the card level with its mark (card-layout.ts); a loose card leaves the pass's focus as it was (laidOn), and scrollCard shows it where it stands
    this.render();
    this.scrollCard(key);
  }
  /** Whether the view's text is the text the status's offsets index: the hunks are offsets into the file the
   *  host read, and after a reject (or a session write the poll has seen but the status has not) the two
   *  differ until the reload lands — painting changes over the other text would mark the wrong passages.
   *  An empty viewer mtime (the fetch not landed) claims nothing. */
  private textCurrent(s: Status): boolean {
    const vm = this.ctx.mtimeNs();
    return !vm || !s.fileMtimeNs || vm === s.fileMtimeNs;
  }
  /** The text the status's offsets and a composer's range index: the view's, or while the editor is up — when text()
   *  answers the buffer, which every keystroke moves under the offsets — the file as the editor loaded it or as the last
   *  landed save wrote it (editText). The group titles and the composer's passage-changed tag read this, never the buffer. */
  private indexedText(): string | null {
    return this.ctx.editing() && this.editText !== null ? this.editText : this.ctx.text();
  }
  /** Show changes inline, flipped: the preference goes to the shared store (saveSettings; every other viewer reads
   *  it on its next paint or through the settings signal) and the body is repainted at once from the status already
   *  here — no status ask, the hunks have not changed — which also re-renders the header's button. */
  private toggleInline(): void {
    this.inline = !this.inline;
    saveSettings({ changesInline: this.inline });
    this.paintAll();
  }
  /** Paint every open comment's anchor over the current view: located → the ring; quote gone but its
   *  context found → the text-changed ring; neither → card only, marked detached. Detached is a
   *  rendering state, never a stored flag. Then the changes (D4/D5): insertions and substitutions tinted
   *  over the new text, deletions struck at their point in both views (Rendered through the index map; a
   *  deletion the map cannot place is card-only), each mark carrying the change's id and the author's session
   *  colour — or none of them, with Show changes inline off. The composer's pending target is painted last. */
  paintAll(): void {
    if (this.ctx.editing()) { this.render(); return; }   // the editor shows the marks over its own buffer (Slice 5); the cards still render
    this.clearLanding();                               // a paint pass over the read view is new information about its rows: the last Reveal's cue goes with it (landOn)
    this.editSeed = null;                              // no editor is up: nothing rode into one (routesSave reads the status again)
    // the rows that said to decide in the editor are about an editor that is gone: retired with it (a row another
    // refusal has since replaced in the same slot is left alone)
    for (const slot of this.decideRows) if (DECIDE_TEXTS.has(this.errors.get(slot)?.text ?? "")) this.errors.delete(slot);
    this.decideRows.clear();
    this.editText = null;                              // the read view is back: the cards group over its text again (indexedText)
    // the edit ended over bytes that moved under it (Cancel — a Save would have refused): re-read them, whether or not
    // the head's row was dismissed with its ✕ meanwhile (movedUnderEdit: the latch, not the row, keys the re-read)
    if (this.movedUnderEdit) { this.movedUnderEdit = false; this.errors.delete("edit"); this.ctx.reload(); }
    // the row that said the editor's changes left the sidecar is about an editor that is gone: retired with it, and the
    // latch with it (nothing to re-read: the status that set the row is the one showing, and this paint marks its changes)
    if (this.changesMovedUnderEdit) { this.changesMovedUnderEdit = false; if (this.errors.get("edit")?.text === CHANGES_MOVED_UNDER_EDIT) this.errors.delete("edit"); }
    if (this.changesUnreadUnderEdit) { this.changesUnreadUnderEdit = false; if (this.errors.get("edit")?.text === CHANGES_UNREAD_UNDER_EDIT) this.errors.delete("edit"); }
    this.located = new Map();
    this.unsureCopies = new Set();
    this.paintedChanges = new Set();
    // a mark of ours holding the keyboard (Enter on it opened the panel, whose colour fetch and status reply both
    // repaint) is unwrapped below, and a removed element drops the focus to the body; refocus() mends only the
    // aside's controls, so the mark's own successor takes it back once painted (refocusMark)
    const held = this.heldMark();
    unpaintChanges(this.ctx.body());                   // before each repaint (D5): the marks are unwrapped, never stacked
    this.unpaint(".fc-hl, .fc-presel");                // a status refresh repaints the SAME body: never wrap twice
    const src = this.ctx.text(); const root = this.contentRoot();
    if (this.status && this.textCurrent(this.status)) this.bytesLanded();   // the view shows the status's text: a reject's reload has landed
    if (src === null || !root) { this.paintRegions(); this.render(); return; }   // a media body: the overlay is its only paint (paintRegions keeps its own focus)
    const rendered = this.ctx.mode() === "rendered";
    // the comment highlights — unless the filter shows the changes alone (activeFilter), when the text wears the change
    // marks only; the cards the filter hides are not rendered, so nothing reads `located` for them
    for (const card of this.activeFilter() === "changes" ? [] : this.cards()) {
      if (card.resolved || !card.anchor) continue;
      // the stored position is the engine's tie-break (nearest wins), so a comment on text that recurs with the same
      // surroundings past the anchor's context is painted on the copy that was chosen — in the VIEW's coordinates
      // (viewAt: the host's text keeps a BOM the fetch strips, so its offsets run one ahead on such a file)
      const at = this.viewAt(card);
      const loc = locateComment(src, card.anchor, at);
      // ...and where the anchor ties and the position names none of the tied copies, the copy painted is the engine's
      // guess: painted in the dashed cue and said on the card (copyUnsure), never shown as the copy that was chosen
      const unsure = loc.state === "located" && !!loc.range && this.copyUnsure(src, card, at, loc.range.start);
      if (unsure) this.unsureCopies.add(card.id);
      let painted = false;
      if (loc.state !== "detached" && loc.range) {
        const cls = "fc-hl" + (loc.state === "context" ? " fc-hl-context" : "");
        const out = rendered ? paintRendered(root, src, loc.range, cls, { act: "fcopen", id: card.id })
          : paintRaw(root, src, loc.range, cls, { act: "fcopen", id: card.id });
        painted = !!out && out.length > 0;
        // a highlight is a control (it opens the card): reachable by Tab, activated by Enter (KEY_ACTS), and
        // remembered as the panel's own (owns) — the one kind of control it puts among the file's markup; a guessed copy
        // wears the dashed cue as well (the sheet's mark for a passage not confirmed at its place) and says so
        const title = unsure ? unsureMarkTitle(card) : "Open the comment on this passage";
        for (const m of out || []) { if (unsure) m.classList.add("fc-hl-context"); (m as HTMLElement).tabIndex = 0; m.setAttribute("role", "button"); (m as HTMLElement).title = title; this.mark(m); }
        if (!painted && rendered && !card.target) {    // an embed line renders no text: the frame goes on its picture — unless the comment is a region, whose rectangle (paintRegions) is the mark
          const img = imgForRange(root, src, loc.range, this.ctx.path);
          if (img) { frameImage(img, unsure ? cls + " fc-hl-context" : cls, { act: "fcopen", id: card.id }); this.mark(img); painted = true; }
        }
      }
      this.located.set(card.id, { ...loc, painted });
    }
    this.paintChanges(root, src, rendered);
    this.paintPresel(root, src, rendered);
    this.paintRegions();
    if (held) this.refocusMark(held);
    this.render();
  }
  // The marks in the BODY are controls too (KEY_ACTS: a highlight, a change mark, a rectangle), and every paint pass
  // rebuilds them — so a status landing while the keyboard was on one left it on the body, the way Enter on a card's
  // head once did in the aside (render's refocus mends the aside alone). The focused mark is re-found by what it IS —
  // the action, the id of its subject, and its place among the subject's marks — never by its node. paintAll and
  // paintRegions each mend the marks they rebuild (heldMark before the pass, refocusMark after it).
  /** A card's stored position (`anchorAt`, the host's offset into the text IT read) in the view's coordinates. The host
   *  reads the file with its BOM kept and the fetch hands the viewer the text with it stripped, so on a BOM-prefixed
   *  file every stored position is the view's plus one; the status says which (`bom`, the host's own word on its text:
   *  the panel has no other authoritative source for it, since the viewer never sees the byte). Compared unmapped, a
   *  position naming the chosen copy missed it by one on every such file, and the copy was painted as a guess (the
   *  review, 2026-09-08). undefined without a position; 0 is a position. */
  private viewAt(card: Card): number | undefined {
    if (card.anchorAt === null) return undefined;
    return this.status && this.status.bom ? card.anchorAt - 1 : card.anchorAt;
  }
  /** Whether the copy the engine found a comment at (`at`, the pick with the stored position as the hint) is a guess:
   *  the anchor has more than one best hit in the text — its earliest and latest (hint 0, hint length) differ, the
   *  host's own test for a tie — and the stored position (`stored`, in the view's coordinates: viewAt) names none of
   *  them. The pick is then nearest-wins from a position nothing vouches for, or the earliest with no position at all:
   *  the host keeps a position that names no copy when the recorded changes carry it to none or to several, and every
   *  position when the file changed unrecorded (refreshAnchorAts), and an edit inside the chosen copy's context leaves
   *  the other copies whole to outscore it (the review, 2026-09-07: the highlight sat on a copy the person never
   *  commented, painted as located). A position that names a tied copy is the choice recorded; one best hit is the
   *  anchor's own answer and needs none. */
  private copyUnsure(src: string, card: Card, stored: number | undefined, at: number): boolean {
    if (!card.anchor || stored === at) return false;
    const first = locateComment(src, card.anchor, 0);
    if (first.state !== "located" || !first.range) return false;
    const last = locateComment(src, card.anchor, src.length);
    return last.state === "located" && !!last.range && last.range.start !== first.range.start;
  }
  /** OUR marks (owns) for one subject, in document order: a comment's highlight may span several rows, and a
   *  substitution paints a deletion point and then its new text, all with the same action and id. */
  private ownMarks(act: string, id: string): HTMLElement[] {
    return Array.from(this.ctx.body().querySelectorAll('[data-act="' + act + '"][data-id="' + cssId(id) + '"]')).filter((m) => this.marks.has(m)) as HTMLElement[];
  }
  /** The mark of ours that holds the keyboard, by what it is — its action, its id, and its place among the subject's
   *  marks — and the element, so a repaint can tell whether it was unwrapped. Null when the focus is anywhere else. */
  private heldMark(): { act: string; id: string; k: number; at: Element } | null {
    const a = document.activeElement as HTMLElement | null;
    if (!a || !this.marks.has(a) || !a.dataset || !a.dataset.act || !a.dataset.id) return null;
    return { act: a.dataset.act, id: a.dataset.id, k: this.ownMarks(a.dataset.act, a.dataset.id).indexOf(a), at: a };
  }
  /** After a repaint: the held mark left the body, so its successor — our mark for the same subject at the same
   *  place — takes the focus, without scrolling. A mark that stayed (nothing repainted it) keeps it; a subject the
   *  repaint no longer paints (the change was decided, the comment resolved) leaves the focus where the browser put it. */
  private refocusMark(held: { act: string; id: string; k: number; at: Element }): void {
    if (this.ctx.body().contains(held.at)) return;
    const next = this.ownMarks(held.act, held.id);
    if (next.length) next[Math.min(Math.max(held.k, 0), next.length - 1)].focus({ preventScroll: true });
  }
  /** The change marks, after the comment highlights (D5): stylesFor hands each mark the author's session colour
   *  from the Slice 1 colour map as `--fc-author` (nothing when unknown: the sheet's neutral). Every painted
   *  element is a control (it opens the card) and the panel's own (owns), like a comment highlight. */
  private paintChanges(root: Element, src: string, rendered: boolean): void {
    const s = this.status;
    if (!this.inline) return;                          // Show changes inline is off: no mark in either view, the cards say everything
    if (this.activeFilter() === "comments") return;    // the filter shows the comments alone: no change mark, the setting above untouched
    if (!s || !(s.hunks || []).length || !this.textCurrent(s)) return;
    const store = s.store;
    // newText rides along so the painters verify that each change's new text sits at its offsets before painting the
    // batch: the hunks index the string the HOST read, and the viewer's text can differ from it — a BOM the fetch
    // stripped puts every mark one character off. Refused, the changes stay card-only, each with Reveal (D4).
    // `label`: the chip beside a Raw mark reads the session's CURRENT name from the colour map, as the card's chip does
    // (chip) — the sidecar's `author` is the name at write time, and after a rename the mark and the card must name the
    // session alike. An author with no live match keeps the sidecar's label (the painter's own fallback, chipLabel).
    const changes: ChangePaint[] = (s.hunks || []).map((h) => {
      const aid = authorIdOf(store, h.id);
      const col = aid && this.colors ? this.colors.get(aid) : null;
      return { id: h.id, kind: h.kind, curFrom: h.curFrom, curTo: h.curTo, oldText: h.oldText, newText: h.newText, author: h.author, label: col ? col.name : undefined };
    });
    const stylesFor = (c: ChangePaint): Record<string, string> => {
      const aid = authorIdOf(store, c.id);
      const col = aid && this.colors ? this.colors.get(aid) : null;
      return col && col.color ? { "--fc-author": col.color.bg } : {};
    };
    let marks: Element[];
    if (rendered) {
      // the Rendered painter reports ids, not elements, so the marks are told from the file's own markup by what the
      // paint ADDED: a `data-act="fcchange"` the file's author wrote survives the sanitizer, and swept in it would pass
      // owns() and act as a control (the delegate root's rule above)
      const before = new Set(Array.from(root.querySelectorAll('[data-act="fcchange"]')));
      const r = paintChangesRendered(root, src, changes, stylesFor);
      for (const id of r.painted) this.paintedChanges.add(id);
      marks = Array.from(root.querySelectorAll('[data-act="fcchange"]')).filter((m) => !before.has(m));
    } else {
      marks = paintChangesRaw(root, src, changes, stylesFor);
      for (const m of marks) { const id = (m as HTMLElement).dataset.id; if (id) this.paintedChanges.add(id); }
    }
    for (const m of marks) { (m as HTMLElement).tabIndex = 0; m.setAttribute("role", "button"); (m as HTMLElement).title = "Open this change"; this.mark(m); }
  }
  private paintPresel(root: Element, src: string, rendered: boolean): void {
    const c = this.composer;
    if (!c || c.kind !== "comment" || !c.range || c.text !== src) return;   // the range indexes c.text; over other bytes it would paint the wrong span
    if (!rendered) { paintRaw(root, src, c.range, "fc-presel"); return; }
    const out = paintRendered(root, src, c.range, "fc-presel");
    if (!out || !out.length) { const img = imgForRange(root, src, c.range, this.ctx.path); if (img) frameImage(img, "fc-presel"); }
  }
  /** Unwrap painted marks: the text nodes go back in place and the parent is normalized. A framed
   *  picture is stripped of its marks instead — unwrapping an <img> would remove the picture. */
  private unpaint(selector: string): void {
    const marks = selector.split(",").map((s) => s.trim().replace(/^\./, ""));
    for (const n of Array.from(this.ctx.body().querySelectorAll(selector))) {
      if (n.classList.contains("fc-img")) { unframeImage(n as HTMLElement, marks); continue; }
      const p = n.parentNode; if (!p) continue;
      while (n.firstChild) p.insertBefore(n.firstChild, n);
      p.removeChild(n); p.normalize();
    }
  }
  private repaintPresel(): void {
    this.unpaint(".fc-presel");
    const src = this.ctx.text(); const root = this.contentRoot();
    if (src !== null && root) this.paintPresel(root, src, this.ctx.mode() === "rendered");
    this.paintRegions();                               // the composer's pending region and the re-place cue live on the overlays
  }
  /** The body was repainted, possibly over NEW text (the poll saw the file move and reloaded it; Reload;
   *  a refresh; a save through the editor): a pending passage follows its passage into that text
   *  (followPassage), so the presel, the chip and the hint move with it — a note typed while the session
   *  inserts a paragraph above still lands where it was aimed, on the copy that was selected even where
   *  the passage recurs, since an edit that does not reach the passage moves its offsets exactly. Not
   *  followed, the selection-time pair is kept, nothing is painted, and the chip says which: the passage
   *  changed or went (Save hands the host that anchor and offset to rule on — it relocates, or refuses
   *  and the note stays), or it now recurs where the anchor cannot tell the copies apart (`tied`: Save
   *  sends the anchor with no offset, so the host refuses a tie rather than settle it by an offset into
   *  other text; selecting the passage again pins the copy), or the edit reached it and its text is now
   *  intact only at a copy the edit never touched (`elsewhere`: Save is refused here, since the host
   *  would place that one hit; selecting the passage again pins the copy). Text that is the pair's own
   *  again — a repaint, a reverted edit — is exact, so a tie or an elsewhere noted meanwhile is dropped. */
  private retargetComposer(): void {
    const c = this.composer; const src = this.indexedText();
    if (!c || (c.kind !== "comment" && c.kind !== "region") || !c.range || c.text === undefined || src === null) return;
    c.elsewhere = false;
    if (src === c.text) { c.tied = false; return; }
    const f = followPassage(c.text, c.range, src);
    if (f.state === "moved") { c.range = f.range; c.text = src; c.tied = false; }
    else c.tied = f.state === "tied";
    c.elsewhere = f.state === "elsewhere";
  }
  // ── region comments (Slice 3): the overlays ─────────────────────────────────────────────────────
  /** The pictures that take an overlay in the current view: the media body's <img>, or each page's canvas while the
   *  PDF chunk renders the pages (the seam's pdfPages; a PDF shown as the browser's frame takes none), or every figure
   *  in rendered markdown; none in Raw, where the embed line is the mark. */
  private regionImages(): Pictured[] {
    const mode = this.ctx.mode();
    if (mode === "media") {
      const pages = this.ctx.pdfPages();
      if (pages.length) return pages.map((pg) => pg.querySelector("canvas.fileview-pdf-canvas")).filter((c): c is HTMLCanvasElement => isCanvas(c));
      const m = this.ctx.mediaElement();
      return m && typeof m.tagName === "string" && m.tagName.toUpperCase() === "IMG" ? [m as HTMLImageElement] : [];
    }
    if (mode === "rendered") { const root = this.contentRoot(); return root ? (imgsIn(root) as HTMLImageElement[]) : []; }
    return [];
  }
  /** The picture a region comment is on, in the current view: the media body's for a standalone image, the canvas of
   *  its page for a PDF region; for an embedded figure the picture its anchor's embed line renders (exact), else the
   *  one whose src is the target's (the anchor detached, the figure still there). Null when the view shows none. */
  private regionImageFor(c: Card): Pictured | null {
    if (!c.target) return null;
    const imgs = this.regionImages();
    if (!imgs.length) return null;
    if (this.ctx.mode() === "media") {
      if (c.target.kind === "pdf") { const page = c.target.page; return imgs.find((i) => pageOf(i) === page) || null; }
      return isCanvas(imgs[0]) ? null : imgs[0];
    }
    const root = this.contentRoot(); const src = this.ctx.text();
    const loc = this.located.get(c.id);
    if (root && src !== null && loc && loc.range) {
      const img = imgForRange(root, src, loc.range, this.ctx.path);
      if (img) return img as HTMLImageElement;
    }
    const dest = c.target.src;
    if (dest) {
      const hit = imgs.find((i) => pictureIsEmbed(i, dest, this.ctx.path));
      if (hit) return hit;
    }
    return null;
  }
  /** The shell of a PDF region's page in the document shown (the chunk's `div.fileview-pdf-page`, by its data-page):
   *  null when the pages are mounted and none is the comment's; undefined while no page is mounted (the frame fallback,
   *  the loader), when nothing can be told about the pages. The SHELLS are the page set, never the canvases: the chunk
   *  builds a shell for every page of the CURRENT document, drawn or not, and takes the canvas out of a page pdf.js
   *  could not draw (pdf-chunk.ts fail()) — a page that exists and has no picture, which is not a page the document lost. */
  private pageShellFor(c: Card): HTMLElement | null | undefined {
    if (!c.target || c.target.kind !== "pdf" || this.ctx.mode() !== "media") return undefined;
    const shells = this.ctx.pdfPages();
    if (!shells.length) return undefined;
    const page = c.target.page;
    return shells.find((s) => pageOf(s) === page) || null;
  }
  /** Whether a PDF region's page is no longer in the document shown: the pages are mounted and none of them is the
   *  comment's. A regenerated PDF with fewer pages leaves such a comment with no rectangle to paint and no page to crop —
   *  but not without a remedy: a PDF re-place may land on any page (onRegionDrawn), so the card still offers Re-place,
   *  and says which page went. False while no page is mounted. */
  private pageGone(c: Card): boolean { return this.pageShellFor(c) === null; }
  /** Whether a PDF region's page is mounted but has no picture: pdf.js could not draw it, and the chunk removed its
   *  canvas and put its notice in the shell. The file is unchanged as far as the page can tell (the hashes say the
   *  rest), so the card names the state — not rendered — and never calls the page gone or the PDF changed; there is no
   *  rectangle, no fresh crop, and no Re-place (the comment's place is not in question, only the picture). */
  private pageUnrendered(c: Card): boolean {
    const shell = this.pageShellFor(c);
    return !!shell && !isCanvas(shell.querySelector("canvas.fileview-pdf-canvas"));
  }
  /** Whether a PDF region's page is mounted with its canvas but no bitmap: the chunk draws a page as it nears the reader
   *  (one scroller height away) and gives a far page's bitmap back, so a page outside that window is a 0×0 canvas —
   *  before its first draw, and after an eviction. Such a card has no fresh crop to cut (cropFor), and the chunk's only
   *  API is render(): nothing here can ask for the page. A page drawn at any time since the document was shown (or since
   *  the file last changed) has left its regions' crops kept (cutCrop), the card open or not, so this state reaches the
   *  crop's slot only for a page not drawn in that time. What the card can do then is say so where the crop would be and
   *  reach the page (cropWaitNote); the scroll draws it, and the draw's repaint (the seam's onRendered) brings the crop. */
  private pageUndrawn(c: Card): boolean {
    const shell = this.pageShellFor(c);
    if (!shell) return false;
    const canvas = shell.querySelector("canvas.fileview-pdf-canvas");
    return isCanvas(canvas) && !(canvas.width > 0 && canvas.height > 0);
  }
  /** The author chip a rectangle wears: the label, and the session's colours as `--fc-author` / `--fc-author-fg`
   *  when the colour map knows the author (the sheet's fallback otherwise, and for `you`). */
  private chipFor(author: string, authorId: string | null): { label: string; style?: Record<string, string> } {
    if (author === "you") return { label: "you" };
    const c = authorId && this.colors ? this.colors.get(authorId) : null;
    if (!c) return { label: author || "unknown" };
    return c.color ? { label: c.name, style: { "--fc-author": c.color.bg, "--fc-author-fg": c.color.fg } } : { label: c.name };
  }
  /** The overlays: one layer per picture in view (built once per picture — a far PDF page's with nothing to paint once
   *  its shell nears the reader, watchPages — and dropped when the picture leaves), each
   *  repainted with the rectangles of the open region comments on it — placed by percentages, dashed when the
   *  image's bytes changed under them and marked unknown when that cannot be told (regionState), the author's chip
   *  and colour — plus the composer's pending region and the re-place cue. Each region on a page with its bitmap in
   *  also has its crop cut and kept here (cutCrop), whatever its card's state, so the picture outlives the bitmap. The
   *  drag is armed only while the panel
   *  is open and the pointer is fine (E5: a coarse pointer reads, and the whole-file comment stands in); the
   *  rectangles show whenever the highlights do. A painted rectangle is the comment's mark (located, painted): the
   *  card's reference links to it and offers no Reveal. A pending region whose picture was repainted is re-found
   *  (the media body's one picture; a PDF page by its number, since a reload hands back new canvases; a figure by its
   *  embed's src). A layer is repainted only when what it would show changed (paintedKey), and its rectangles are
   *  updated in place (RegionLayer.paint): opening the panel, a status that moved nothing, a presel repaint elsewhere
   *  and — with a PDF, where this pass runs on every page draw, redraw and width change (the chunk's onPage) — a page
   *  drawing in leave every rectangle standing, with the click pulse and keyboard focus on one. A rectangle that did
   *  go (its layer dropped, its mark moved to another picture) is re-found for the keyboard by what it is (refocusMark). */
  private paintRegions(): void {
    const held = this.heldMark();                      // a rectangle holding the keyboard: re-found after the pass (refocusMark)
    const imgs = this.regionImages();
    const cur = new Set<Pictured>(imgs);                  // a set: the pass runs per page draw, over thousands of pages
    for (const [img, layer] of this.regionLayers) if (!cur.has(img)) { layer.dispose(); this.regionLayers.delete(img); }
    if (!imgs.length) { this.regionMarks = new Map(); this.watchPages([], cur); return; }
    const s = this.status;
    const c = this.composer;
    if (c && c.kind === "region" && !imgs.includes(c.img)) {
      const again = this.ctx.mode() === "media" ? (c.page ? imgs.find((i) => pageOf(i) === c.page) : imgs[0]) : this.composerImage(c, imgs);
      if (again) c.img = again;
    }
    const per = new Map<Pictured, RegionMark[]>();
    const hideRegions = this.activeFilter() === "changes";
    for (const card of this.cards()) {
      // a malformed region (isRegion) paints nothing: the card says so (UNREADABLE_REGION), and Re-place redraws it
      if (!card.target || (card.target.kind !== "image" && card.target.kind !== "pdf") || !isRegion(card.target.region)) continue;
      const img = this.regionImageFor(card);
      if (!img) continue;
      // a drawn page: the crop of every region on it is cut and kept NOW (cutCrop), the card open or closed, resolved or
      // not — this pass runs on every draw's repaint (the seam's onRendered, from the chunk's onPage), so a card expanded
      // after the page has scrolled away, or opened for the first time then, shows its picture rather than the wait line;
      // the line is left for a page not drawn since the document was shown (pageUndrawn), which nothing here can ask for.
      // Only under a key: with no file hash nothing would be kept, and the cut would be wasted
      if (isCanvas(img) && this.cropKey(card)) this.cutCrop(img, card);
      if (card.resolved) continue;
      if (hideRegions) continue;                       // a rectangle is a comment's mark: none while the filter shows the changes alone (the crop above is kept for when they return)
      const chip = this.chipFor(card.author, card.authorId);
      (per.get(img) || per.set(img, []).get(img)!).push({ id: card.id, region: card.target.region, label: chip.label, state: regionState(card.target, s), style: chip.style });
      const loc = this.located.get(card.id);
      this.located.set(card.id, loc ? { ...loc, painted: true } : { state: "located", painted: true });
    }
    this.regionMarks = per;
    const active = this.open && !isCoarsePointer();
    const target = c && c.kind === "replace" ? this.replaceTarget(c.commentId) : null;   // the picture a re-place must be drawn on — once: the lookup walks the pictures, and so does this loop
    // A PDF's pages: a layer is made NOW for a page with a bitmap (near the reader: the chunk draws only the pages within a
    // scroller height of it), for a page with a rectangle to place (a region comment, the composer's pending region, the
    // re-place cue), and for every page when nothing can say which pages are near (no IntersectionObserver: the chunk
    // draws every page then, too). The rest — the empty overlays of far pages, which only a drag would use — are made as
    // their shells near the reader (watchPages, onPageNear). Making a layer appends the overlay to the page's shell and
    // measures it, a forced layout of the whole page column each time, so one per page in one pass is quadratic in the
    // count: 3 s with the pane unresponsive at 2,000 pages and ~20 s at the chunk's 5,000 cap, on the panel's first pass over a long
    // document (the review, 2026-09-06). The chunk's page cap bounds its own shells, not the panel's layers.
    const lazy = typeof IntersectionObserver !== "undefined";
    const later: HTMLCanvasElement[] = [];
    const rendered = this.ctx.mode() === "rendered";
    for (const img of imgs) {
      const marks = per.get(img) || [];
      const pending = c && c.kind === "region" && c.img === img && !c.refusal ? c.region : null;
      const replacing = target === img;
      // A figure in rendered markdown takes a layer only while the panel is open, or when there is something to put on it —
      // its rectangles, the pending region, the re-place cue. The wrapper is a layout of its own (the sheet's inline-block
      // around a block picture) standing in the AUTHOR's flow: wrapped on every paint, a right-floated README logo stopped
      // floating and a width="100%" plot shrank to its natural width, with the panel closed and no comment anywhere near
      // them (the 2026-09-06 review). Closed, a figure with nothing to show stays as the browser laid it out, and a layer
      // with nothing left to show comes down (closePanel's pass puts the picture back). The media body's one picture keeps
      // its layer as before: it is the file, in a box built for it, and its rectangles show whenever a text file's
      // highlights would (the probe's status paints both).
      const wanted = !rendered || this.open || marks.length > 0 || pending !== null || replacing;
      let layer = this.regionLayers.get(img);
      if (!wanted) { if (layer) { layer.dispose(); this.regionLayers.delete(img); } continue; }
      if (!layer) {
        if (lazy && isCanvas(img) && !(img.width > 0 && img.height > 0) && !per.has(img) && !(c && c.kind === "region" && c.img === img) && target !== img) { later.push(img); continue; }
        layer = this.layerFor(img);
      }
      this.paintLayer(img, layer, active, target);
    }
    this.watchPages(later, cur);
    if (held) this.refocusMark(held);
  }
  /** The overlay for a picture, made once and kept (regionLayers): a page's canvas already sits in the chunk's positioned
   *  wrapper (div.fileview-pdf-page), so the layer anchors there; an <img> is wrapped in a span of the layer's own. The
   *  overlay is the panel's own mark too (panelMark): the browser's own click after a press the layer handed on lands there. */
  private layerFor(img: Pictured): RegionLayer {
    // onClick is a PLAIN picture's click; a framed picture's (an embed-line comment's highlight, data-act="fcopen")
    // the layer hands to the picture itself (handOn), so the delegate's fcopen and the row's IMG listener hear it as
    // they did before the overlay stood over it
    const layer = new RegionLayer(img, {
      onDraw: (i, r) => this.onRegionDrawn(i, r), onClick: (i) => this.onImageClick(i),
      onPress: () => { this.float.hidden = true; this.imageTarget = null; },   // what hideFloatOnDown does for a mousedown the overlay cancels
    }, isCanvas(img) ? img.parentElement : null);
    this.regionLayers.set(img, layer);
    this.mark(layer.overlay);                          // the browser's own click after a handed-on press lands here (panelMark)
    return layer;
  }
  /** Arm one layer as the pass arms them all, and paint it: the rectangles the last pass filed for its picture
   *  (regionMarks), the composer's pending region when it was drawn there, and the re-place cue when the picture is the
   *  comment's own (`target`). A layer is repainted only when what it would show changed (paintedKey): opening the
   *  panel, a status that moved nothing, a presel repaint elsewhere leave its rectangles standing. The rectangles are
   *  the panel's own controls (owns, and the registry the document's listeners read: mark). */
  private paintLayer(img: Pictured, layer: RegionLayer, active: boolean, target: Pictured | null): void {
    layer.setActive(active);
    const c = this.composer; const per = this.regionMarks;
    const pending = c && c.kind === "region" && c.img === img && !c.refusal ? c.region : null;
    const replacing = target === img;
    const key = JSON.stringify([per.get(img) || [], pending, replacing]);
    if (this.paintedKey.get(layer) === key) return;    // nothing new for this picture: its rectangles stand (paintedKey)
    this.paintedKey.set(layer, key);
    for (const r of layer.paint(per.get(img) || [], pending, replacing)) this.mark(r);
  }
  /** Watch the shells of the pages that took no overlay this pass (pageWatch), so each takes one as it nears the reader
   *  (onPageNear) — one scroller height ahead, the chunk's own margin for the draws, so the overlay is under a page before
   *  its bitmap lands, and under the loader the chunk puts over a pending page (which lets the pointer through to it).
   *  Shells whose canvases left the view (a reload's new canvases, the frame back) or took an overlay meanwhile leave the
   *  watch. The root is the scroller the pages live in (scrollerOf), not the viewport: a rootMargin expands only the
   *  root's box, and the body's clip would make a viewport-rooted margin inert (pdf-chunk.ts found the same for the draws). */
  private watchPages(later: HTMLCanvasElement[], cur: Set<Pictured>): void {
    for (const [shell, canvas] of this.pageWatched) {
      if (cur.has(canvas) && !this.regionLayers.has(canvas)) continue;
      this.pageWatch?.unobserve(shell); this.pageWatched.delete(shell);
    }
    if (!later.length) return;
    if (!this.pageWatch) this.pageWatch = new IntersectionObserver((es) => this.onPageNear(es), { root: scrollerOf(later[0].parentElement), rootMargin: "100% 0px" });
    for (const canvas of later) {
      const shell = canvas.parentElement;
      if (!shell || this.pageWatched.has(shell)) continue;
      this.pageWatched.set(shell, canvas);
      this.pageWatch.observe(shell);
    }
  }
  /** The picture a region composer's figure is now, after a repaint of rendered markdown: the one its embed line renders
   *  — the range retargetComposer has re-found in the current text, through imgForRange, the way a saved region's picture
   *  is found (regionImageFor) — else the first picture of its src (the passage not re-found: the "passage changed" state,
   *  where Save hands the drag-time anchor to the host). By src alone, two embeds of ONE destination — a figure shown
   *  twice — put the pending rectangle and the composer's thumbnail on the FIRST twin while `range` still named the second
   *  and Save anchored the region there: the preview stood on one picture and the saved rectangle landed on another (the
   *  2026-09-06 review). Both directions of the pairing count twins by order (embedOf); this one now does too. A pair
   *  marked `tied` or `elsewhere` (retargetComposer) names NO picture: the chip says the figure drawn on cannot be told
   *  apart, or that its embed line is now only elsewhere, and a rectangle on the first twin of the src would claim the
   *  opposite (the review, 2026-09-07); the composer keeps the picture it was drawn on for its thumbnail. */
  private composerImage(c: Extract<Composer, { kind: "region" }>, imgs: Pictured[]): Pictured | undefined {
    if (c.tied || c.elsewhere) return undefined;
    const root = this.contentRoot(); const src = this.ctx.text();
    if (root && src !== null && c.range && c.text === src) {
      const img = imgForRange(root, src, c.range, this.ctx.path) as Pictured | null;
      if (img && imgs.includes(img)) return img;
    }
    return c.src ? imgs.find((i) => pictureIsEmbed(i, c.src!, this.ctx.path)) : undefined;
  }
  /** A watched shell neared the reader: its page's overlay is made and painted now, armed as the others are, and the
   *  shell leaves the watch. A shell whose canvas is no longer in the viewer's body (the pages went while the entry was in
   *  flight) makes none. The first overlay in view re-renders the aside: the empty state names the drag and the cards
   *  offer Re-place only while some overlay takes one (drawsRegions), which until now none did. */
  private onPageNear(entries: IntersectionObserverEntry[]): void {
    const c = this.composer;
    const replacing = c && c.kind === "replace" ? this.replaceTarget(c.commentId) : null;
    const active = this.open && !isCoarsePointer();
    const none = this.regionLayers.size === 0;
    for (const e of entries) {
      if (!e.isIntersecting) continue;
      const shell = e.target as HTMLElement;
      const canvas = this.pageWatched.get(shell);
      this.pageWatch?.unobserve(shell); this.pageWatched.delete(shell);
      if (!canvas || this.regionLayers.has(canvas) || !this.ctx.body().contains(canvas)) continue;
      this.paintLayer(canvas, this.layerFor(canvas), active, replacing);
    }
    if (none && this.regionLayers.size) this.render();
  }
  /** Whether any overlay in view takes a drag (the panel open, a fine pointer): the empty state names the gesture
   *  and the cards offer Re-place only then. */
  private drawsRegions(): boolean {
    for (const l of this.regionLayers.values()) if (l.active) return true;
    return false;
  }
  /** A region drawn on a picture (the overlay's onDraw). In re-place mode it is the comment's new place: `retarget`
   *  when drawn on the comment's own picture, refused under the card otherwise (the anchor stays on that figure's
   *  embed line, so another figure would make the two disagree). Otherwise the composer opens on the region; a
   *  figure in rendered markdown also needs the embed line's anchor (E1), found from the picture the way the picture
   *  click finds it, and a figure the source holds no embed for is refused with the reason, the note kept. */
  onRegionDrawn(img: Pictured, region: Region): void {
    const c = this.composer;
    const page = pageOf(img);                          // a PDF page's canvas names its page; an <img> has none, whatever its markup carries
    if (c && c.kind === "replace") {
      // the drag's answer — the loader for the retarget's round trip, a refusal — is the card's own slot (card:<id>), which
      // renderCard builds only in the OPEN card. startReplace opens it, but nothing kept it so: collapsed since (a click
      // on its head while scrolling the panel), the drag gave no acknowledgement and a refusal showed nowhere while the
      // composer still asked for the drag (the 2026-09-06 review; ui/CLAUDE.md: always acknowledge). The drag is a gesture
      // about this comment, so its card opens for the answer, and is scrolled to.
      const key = this.cardKey(c.commentId);
      this.openCards.add(key);
      const own = this.replaceTarget(c.commentId);
      // a PDF region may be re-placed on any page (the page rides in the new target); a figure's must stay on its own picture
      if (page === null && own !== img) {
        this.errors.set("card:" + c.commentId, { text: own ? "Draw the new place on the figure this comment is on, not on another one." : "The figure this comment is on is not shown here.", reload: false });
        this.render();
        this.scrollCard(key);
        return;
      }
      this.composer = null;
      void this.mutate("retarget", { commentId: c.commentId, target: regionTarget(region, c.src, page) }, "card:" + c.commentId);
      this.repaintPresel();
      this.renderComposer();
      this.scrollCard(key);
      return;
    }
    const was = this.composer;
    this.openPanel();
    let src: string | null = null, range: SourceRange | null = null, text: string | undefined, refusal: string | null = null;
    if (this.ctx.mode() === "rendered") {
      const root = this.contentRoot(); const t = this.ctx.text();
      const e = root && t !== null ? embedFor(img, root, t, this.ctx.path) : null;
      if (e) { src = e.dest; range = { start: e.start, end: e.end }; text = t as string; }
      else refusal = EMBED_NOT_FOUND;
    }
    this.composer = { kind: "region", img, region, page, src, range, text, refusal };
    this.errors.delete("composer");
    this.repaintPresel();
    this.renderFrom(was);
    this.input.focus();
  }
  /** Re-place (a region card's button): the next region drawn on the comment's picture replaces its target (E3);
   *  the composer box carries the instruction, and Cancel keeps the region where it is. */
  startReplace(id: string): void {
    const card = this.cards().find((c) => c.id === id);
    if (!card || !card.target) return;
    this.openCards.add(this.cardKey(id));
    this.composer = { kind: "replace", commentId: id, ref: card.ref, src: card.target.src || null, page: card.target.kind === "pdf" ? card.target.page ?? null : null };
    this.errors.delete("composer"); this.errors.delete("card:" + id);
    this.repaintPresel();
    this.render();
  }
  /** The picture a re-place must be drawn on: the comment's own, when the view shows it. */
  private replaceTarget(commentId: string): Pictured | null {
    const card = this.cards().find((c) => c.id === commentId);
    return card ? this.regionImageFor(card) : null;
  }
  /** The word for the file a region sits on, in the tags and titles: the image, or the PDF (whose pages the regions are on). */
  private mediaNoun(): string { return this.ctx.media() === "pdf" ? "PDF" : "image"; }
  /** What a kept PDF crop was cut from: the page, the region, the target's hash and the file's hash as the status has
   *  it — a re-place or a regenerated file changes the key, and the kept crop is not shown for it. Null for an image
   *  region (its picture is always in view) and while the file's hash is unknown: nothing then says the bytes shown
   *  are the bytes the crop was cut from, so none is kept or shown. */
  private cropKey(c: Card): string | null {
    const t = c.target; const s = this.status;
    if (!t || t.kind !== "pdf" || !s || !s.fileHash) return null;
    return t.page + "|" + JSON.stringify(t.region) + "|" + (t.hash || "") + "|" + s.fileHash;
  }
  /** The region's thumbnail cut from its picture (cropThumb) and, for a PDF page whose bytes the status names (cropKey),
   *  kept under its key (crops) — the one cut for both the render of an open card (cropFor) and the region pass over a
   *  drawn page (paintRegions), so a crop kept with the card closed is the crop the open card would have cut. Null when
   *  the picture has no bitmap to cut from (a 0×0 canvas, a picture still loading); nothing kept is dropped for it. */
  private cutCrop(img: Pictured, c: Card): HTMLCanvasElement | null {
    const fresh = cropThumb(img, c.target!.region);
    if (fresh) { const key = this.cropKey(c); if (key) this.crops.set(c.id, { key, crop: fresh }); }
    return fresh;
  }
  /** The card's thumbnail: cut from the picture in view (a page's from its canvas) and, for a PDF page, kept (cutCrop) —
   *  the chunk gives a far page's bitmap back (a 0×0 canvas) and takes a failed page's canvas away, and the card then shows
   *  the crop from the last draw of the same bytes rather than none, kept while the card was open or while it was closed
   *  (the region pass keeps every drawn page's crops). No picture and nothing kept: no thumbnail — the card's crop slot
   *  then says the page is not drawn and reaches it (pageUndrawn, cropWaitNote); the scroll draws the page, and the crop
   *  comes with that draw's repaint. A picture still loading re-renders the cards once, on its load. */
  private cropFor(img: Pictured | null, c: Card): HTMLCanvasElement | null {
    if (!c.target || !isRegion(c.target.region)) return null;   // a malformed region crops nothing (UNREADABLE_REGION): its NaN made a 0×0 canvas
    const fresh = img ? this.cutCrop(img, c) : null;
    if (fresh) return fresh;
    const kept = this.crops.get(c.id); const key = this.cropKey(c);
    if (kept && key && kept.key === key) return kept.crop;
    if (img && !isCanvas(img) && img.complete === false && !this.cropWait.has(img)) {
      this.cropWait.add(img);
      img.addEventListener("load", () => { this.cropWait.delete(img); this.render(); }, { once: true });
    }
    return null;
  }
  /** What an open card shows in its crop's place while its PDF page has no bitmap (pageUndrawn): one line naming the
   *  page and the remedy, itself the control that scrolls the page in (fcgoto: the rectangle sits on the undrawn page's
   *  overlay, placed by percentages of the page's box, so goTo reaches it). The chunk draws the page once it is near,
   *  and the draw's repaint replaces this line with the crop. A Tab stop, Enter through KEY_ACTS, like the reference. */
  private cropWaitNote(c: Card): HTMLElement {
    const page = c.target!.page;
    const n = el("div", "fc-note fc-link fc-crop-wait", "Page " + page + " is not drawn yet. Go to the page to see this region.");
    n.dataset.act = "fcgoto"; n.dataset.id = c.id;
    n.title = "Go to page " + page + "; the picture of this region appears here once the page is drawn";
    n.tabIndex = 0; n.setAttribute("role", "button");
    return n;
  }
  /** Scroll to a card's mark — the panel's OWN (owns): the file's markup may carry the same attributes earlier in the
   *  document, and a body-wide first match would scroll to that. A region comment's mark is its rectangle (.fc-region,
   *  painted by paintRegions). No mark of ours in the view: Reveal. */
  goTo(key: string): void {
    if (this.margin && this.focusOn(key) && this.centerOn(key)) return;   // the margin layout: the card the focus, level with its mark; the mark to the body's center, the card beside it (the lock brings the track)
    const sel = key.startsWith("chg:") ? '[data-act="fcchange"][data-id="' + cssId(key.slice(4)) + '"]' : '.fc-hl[data-id="' + cssId(key) + '"], .fc-region[data-id="' + cssId(key) + '"]';
    const mark = Array.from(this.ctx.body().querySelectorAll(sel)).find((m) => this.marks.has(m));
    if (mark) { mark.scrollIntoView({ block: "center" }); return; }
    this.reveal(key);
  }
  /** Reveal: switch to Raw and scroll to the passage — a comment's located range, or a change's start — for
   *  a comment or change the view does not show (a Rendered deletion the map refused, any change with Show changes
   *  inline off), so the compact card never dead-ends. In the margin layout the card is made the focus first
   *  (revealInRaw), so the switch's own pass lays it level with its Raw mark before the scroll centers the row, and the
   *  card is then brought whole into the track's box where the row's centering left its end past it (settleRevealed).
   *  Where Raw shows no mark of ours for the subject either, the row the scroll centred is cued (landOn), so the landing
   *  is not a guess among identical rows. */
  reveal(key: string): void {
    if (key.startsWith("chg:")) {
      const c = this.changeView().cards.find((x) => x.key === key);
      if (!c || c.detached) return;                    // a detached change's offset points into a text that has moved on
      this.revealInRaw(key);
      this.ctx.scrollToOffset(c.curFrom);
      this.landOn(c.curFrom, "fcchange", c.id);
      this.settleRevealed(key);
      return;
    }
    const card = this.cards().find((c) => c.id === key);
    if (card && card.target) {                         // a region: the picture it is on, when the view shows it
      const img = this.regionImageFor(card);
      if (img) { img.scrollIntoView({ block: "center" }); return; }
      const shell = this.pageShellFor(card);           // a PDF page pdf.js could not draw: its shell holds the chunk's notice
      if (shell) { shell.scrollIntoView({ block: "center" }); return; }
    }
    const loc = this.located.get(key);
    if (!loc || !loc.range) return;
    this.revealInRaw(key);
    this.ctx.scrollToOffset(loc.range.start);
    this.landOn(loc.range.start, "fcopen", key);
    this.settleRevealed(key);
  }
  /** After a Reveal's switch and scroll: the revealed card whole in the track's box, where the pass laid it level with
   *  its Raw mark (the review of the merge audit's fixes, 2026-09-09). scrollToOffset centers the ROW, and a card taller
   *  than the room under the body's center — half the body's height less the footer's and the gap — landed level with its
   *  head in the box but its end, its run of turns and its Reply and Resolve row, past the track's bottom, while the same
   *  card reached by a click on its mark (showCard: focusOn, then centerOn) landed whole: centerOn's fallback scrolls the
   *  least that shows the card's end, as far as keeps the mark's top in view, a card taller than the track having its head
   *  cut by the excess (its docstring has the two regimes). So the row's centering is followed by that scroll, the landing
   *  a mark click gives; the row's own centering stands where the pass did not lay the card on a mark (laidOn: Show
   *  changes inline off, when Raw paints no mark and landOn cues the row), since centerOn has no mark to scroll to there. */
  private settleRevealed(key: string): void {
    if (this.margin && this.laidOn === key) this.centerOn(key);
  }
  /** A Reveal's switch to Raw, with the card made the focus FIRST when the margin layout is up (the merge audit,
   *  2026-09-09). setMode re-renders the body synchronously and its onRendered pass lays the margin (paintAll, render,
   *  placeCards), so a focus written before the call has that pass lay the revealed card level with its Raw mark, and
   *  scrollToOffset then centers a row whose card is already beside it. Before, reveal() set no focus: the pass laid the
   *  margin on the focus it had — the tall change card the person had unfolded — and the card whose Reveal was clicked
   *  was pushed under it, wholly outside the track's box while its passage sat mid-body; goTo and scrollCard make their
   *  card the focus before they scroll, and Reveal did not. focusOn before the switch would not do: a card Reveal is
   *  offered for is loose in the view where it is offered (no mark to be laid level with), and the pass spends a loose
   *  focus (placeCards: laidOn). A switch that paints nothing (a file with no Rendered view is Raw already; the seam's
   *  setMode returns) ran no pass, so one runs here where the switch ran none, and only there: every pass ends by writing
   *  a new placement (placeCards: `placed`), so the placement of before still standing after the switch says no pass ran.
   *  With Show changes inline off Raw paints no mark either, and the switch's pass falls to the focus it had; a pass after
   *  it would measure the same body and cards and lay them where it did. The pass ran here whenever the last pass had not
   *  laid the cards on this card, which after the switch is every change card's Reveal with the marks off — the whole
   *  margin measured and written twice for one click (the review of the audit's fixes, round 2, 2026-09-09). */
  private revealInRaw(key: string): void {
    if (this.margin) this.focusCard = key;            // the focus: the switch's pass lays the card level with its Raw mark (card-layout.ts)
    const placed = this.placed;                       // the last pass's placement: the switch's pass, where it runs, writes a new one
    this.ctx.setMode("raw");
    if (this.margin && this.placed === placed) this.placeCards(false);   // the switch ran no pass: this is the one
  }
  /** The landing cue, after a Reveal's switch and scroll (the note above LANDING_BG): the Raw row holding `offset` —
   *  the SAME row the viewer's scrollToOffset centred, by the same count of line ends before the offset, clamped to the
   *  last row, so the cue and the scroll never disagree — wears the cue when the Raw body shows no mark of ours for the
   *  subject (`act` + `id`: the change's marks, or the comment's highlight). setMode re-renders the body synchronously
   *  and its onRendered pass has painted by now (paintAll), so what the body shows is what the person sees. One landing
   *  at a time: the last cue is cleared first, whether or not a new one is painted. */
  private landOn(offset: number, act: string, id: string): void {
    this.clearLanding();
    if (this.ownMarks(act, id).length) return;         // the view marks the subject itself: that mark is the cue
    const src = this.ctx.text();
    const code = this.ctx.body().querySelector("code.hljs");
    if (src === null || !code) return;                 // no Raw rows to cue (a media body; the editor's)
    const rows = code.querySelectorAll(".fv-cl");
    if (!rows.length) return;
    const row = rows[Math.min(rawOffsetToLine(src, offset), rows.length - 1)] as HTMLElement;
    row.classList.add("fc-landing");
    row.style.background = LANDING_BG; row.style.boxShadow = LANDING_BAR;
    this.landing = row;
  }
  /** The cue comes off its row — on a paint pass, the next Reveal, the panel closing: each an event, never a timer. */
  private clearLanding(): void {
    const row = this.landing;
    this.landing = null;
    if (!row) return;
    row.classList.remove("fc-landing");
    row.style.background = ""; row.style.boxShadow = "";
  }
  /** The card into view: in the margin layout it is made the focus first, so the pass lays it level with its mark before
   *  the scroll reads where it stands. Every caller sets the focus on its own path too (showCard; goTo; the saved line's
   *  click reaches a card landSaved made the focus when the save landed), and the setter stays HERE all the same: when the
   *  save itself scrolled here (before decision 43) it was the one caller with no setter before it, and a reply saved on
   *  an open card that was not the focus — the change mark above it clicked since the card was opened, the card pushed
   *  under the tall change card — was scrolled to where the push-down rule left it, its mark brought into view with the
   *  card a viewport below, the defect the focus follow-on fixed (the verification review, 2026-09-09). */
  scrollCard(id: string): void {
    if (this.margin && this.focusOn(id) && (this.centerOn(id) || this.showLoose(id))) return;   // the margin layout: the card the focus, level with its mark, its mark to the center; a loose card into the track's box, the body along with it
    this.root?.querySelector('.fc-card[data-id="' + cssId(id) + '"]')?.scrollIntoView({ block: "nearest" });
  }

  // ── the margin layout (the 2026-09-07 follow-on; card-layout.ts is the pure half) ─────────────────
  /** Wire what the layout listens to, once per panel: the two scrollers' events (the lock); a picture loading in the
   *  body (`load` does not bubble, so a capture listener on the body hears every figure's); the window's resize; the
   *  sizes of the body, the row and the track (the aside joins at its first build, the body's content at each pass —
   *  watchContent — and the cards at each render); and a click on a card's head — heard here, under the delegate root
   *  and so BEFORE the delegate toggles the card, so that the render's pass anchors the layout on the card that just
   *  opened (focusCard) and afterRender knows to center its mark. Never on scroll: the lock is the scroll's whole
   *  effect, and the pass moves nothing a scroll changes. */
  private installLayout(row: HTMLElement): void {
    const body = this.ctx.body(), track = this.sections.cards;
    body.addEventListener("scroll", () => this.mirrorScroll("body"));
    track.addEventListener("scroll", () => this.mirrorScroll("track"));
    body.addEventListener("load", () => this.scheduleLayout(), true);
    track.addEventListener("click", (ev) => {
      const t = ev.target as HTMLElement | null;
      const x = t && typeof t.closest === "function" ? (t.closest("[data-act]") as HTMLElement | null) : null;   // what the delegate resolves
      if (x && x.dataset.act === "fccard" && x.dataset.id) {
        const wasOpen = this.openCards.has(x.dataset.id);
        this.expandIntent = { key: x.dataset.id, wasOpen };
        if (!wasOpen) this.focusCard = x.dataset.id;    // a card opened by its head is the focus (focusCard); a fold is a dismissal and moves nothing; a loose card opened leaves the pass's focus as it was (laidOn)
      }
    });
    window.addEventListener("resize", this.onWindowResize);
    if (typeof ResizeObserver !== "undefined") {
      this.sizer = new ResizeObserver(() => this.scheduleLayout());
      this.sizer.observe(body); this.sizer.observe(row); this.sizer.observe(track);
      this.cardSizer = new ResizeObserver(() => this.scheduleLayout());
    }
  }
  onWindowResize = (): void => this.scheduleLayout();
  /** Whether the aside is laid out as a margin now: beside the body — the row's computed flex-direction is the
   *  sheet's own verdict on the fold, `column` being the narrow column, where the aside stands under the body and
   *  the cards are the list — and in read mode. A document with no computed style (a stand-in) is the list. */
  private marginMode(): boolean {
    if (this.ctx.editing() || typeof getComputedStyle !== "function") return false;
    const row = this.ctx.body().parentElement;
    return !!row && getComputedStyle(row).flexDirection !== "column";
  }
  /** One pass per frame, however many events ask for it (a figure's load, a resize, a card's growth). */
  private scheduleLayout(): void {
    if (this.layoutFrame !== null || !this.open) return;
    if (typeof requestAnimationFrame !== "function") { this.placeCards(false); return; }
    this.layoutFrame = requestAnimationFrame(() => { this.layoutFrame = null; this.placeCards(false); });
  }
  /** After every render: the pass, then the centering a head click asked for — in that order, so the expanded card's
   *  new height has pushed the cards below it before anything scrolls (no jump after the expand). Only a card the
   *  click OPENED is centered: a fold is a dismissal, and the text should not move for it. */
  private afterRender(): void {
    this.placeCards(true);
    const intent = this.expandIntent; this.expandIntent = null;
    if (intent && this.margin && !intent.wasOpen && this.openCards.has(intent.key)) this.centerOn(intent.key);
    if (this.savedOut && !this.margin) this.reflect();   // the list layout: the saved line follows the cards as this render laid them (reflectLines); only a render moves them there, and the margin pass re-reads at its own end
  }
  /** The margin pass: card-layout.ts decides, this measures and applies. The mode first — a change toggles the
   *  sheet's `fc-margin`, and the margin layout ending OUTSIDE a render re-renders, since the rows stand in the
   *  footer and must return to the list (layoutOff). In the margin layout: the list's ROWS — the foot (Accept all ·
   *  Reject all), a loader, a refusal, a fold, the empty note — leave the track for the footer, above Send
   *  (moveRows); each card's desired top is its mark's top in the body's content less the header's height (the track
   *  begins that far below the body's top, so a card level with its mark sits that much higher in the track's
   *  content: a mark under the header itself is clamped, and level once the text has scrolled by the header's
   *  height); the cards are placed (layoutCards) and their tops written, a pushed card carrying the leader's length;
   *  the cards' DOM order is made the placement's (so the Tab order runs down the margin, top to bottom: a head is a
   *  Tab stop, focusing one scrolls the track and the body with it, and an order by time scrolled the text up and
   *  down with every Tab); the body's content is padded at its end by the footer's height plus the last card's overhang
   *  (padBody), so the body itself can scroll every mark's card into the track's box; the list is made as tall as
   *  puts the track's farthest position at the body's (one range: the body's content less the body's box plus the
   *  track's), or as the last card, whichever is more; and the track is brought to the body's position. `fromRender`:
   *  the sections were just rebuilt, so the rows are in the list again and the cards are new (the card observer takes
   *  them, as it does the cards the list layout held when the margin layout comes on outside a render). */
  placeCards(fromRender: boolean): void {
    const root = this.root;
    if (!root || !this.open) return;
    const margin = this.marginMode();
    const flipped = margin !== this.margin;
    if (flipped) root.classList.toggle("fc-margin", margin);
    if (!margin) {
      // the list layout has no focus: a mark or a head clicked in it writes one (showCard, installLayout), and a pass here
      // spends nothing on it — but the flip to the margin layout would have, laying the whole margin on a card no gesture
      // named THERE and centering nothing (a resize is not a click), the cards above it moved from their marks (the
      // 2026-09-08 review). The focus is a click's, made in the margin layout.
      this.focusCard = null;
      if (flipped) { this.layoutOff(); if (!fromRender) this.render(); }
      return;
    }
    if (flipped) { this.margin = true; this.placed = new Map(); this.cardsEnd = 0; }
    const watch = fromRender || flipped;               // new cards (a render), or cards the list layout held (the layout just came on): the card observer takes them
    const body = this.ctx.body(), track = this.sections.cards;
    const list = Array.from(track.childNodes).find((n) => n.nodeType === 1) as HTMLElement | undefined;
    if (!list) return;
    this.watchContent(body);
    const kids = (): HTMLElement[] => Array.from(list.childNodes).filter((n) => n.nodeType === 1) as HTMLElement[];
    this.moveRows(kids());
    this.clipCards(kids());                            // which parts the fold cut, and the Show more rows: before the heights are read
    const bodyRect = body.getBoundingClientRect(), trackRect = track.getBoundingClientRect();
    const offset = trackRect.top - bodyRect.top;
    const scroll = body.scrollTop;
    const items: LayoutItem[] = [];
    const nodes = new Map<string, HTMLElement>();
    const laid: HTMLElement[] = [];                    // the items' nodes in the DOM's order, as the pass found them
    if (watch) this.cardSizer?.disconnect();
    let n = 0;
    for (const child of kids()) {
      if (child.hidden || child.classList.contains("fc-group")) continue;   // the paragraph titles: the sheet hides them here, the card's place says the paragraph
      const isCard = child.classList.contains("fc-card") && !!child.dataset.id;
      const key = isCard ? child.dataset.id! : "#" + n++;
      const mark = isCard ? this.markTop(key) : null;
      items.push({ key, desired: mark === null ? null : mark - bodyRect.top + scroll - offset, height: child.getBoundingClientRect().height });
      nodes.set(key, child); laid.push(child);
      if (isCard && watch) this.cardSizer?.observe(child);
    }
    if (this.focusCard !== null && !nodes.has(this.focusCard)) this.focusCard = null;   // the card is gone from the list (a status, the filter, a fold): no focus
    // a loose card as the focus (a whole-file comment's card opened by its head or its Show more, a save landing in one): no
    // mark to lay it level with, and given to the rule it would have unmade the layout — the rule takes a focus with no mark
    // as none — so the pass keeps the focus it laid the cards on last, while the list holds that card (the focusCard field)
    const fit = this.focusCard === null ? null : items.find((it) => it.key === this.focusCard) || null;
    if (fit && fit.desired === null) this.focusCard = this.laidOn !== null && nodes.has(this.laidOn) ? this.laidOn : null;
    this.laidOn = this.focusCard;
    const out = layoutCards(items, CARD_GAP, this.focusCard);
    for (const p of out.placed) {
      const node = nodes.get(p.key)!;
      node.style.top = p.top + "px";
      if (p.pushed >= 1) { node.dataset.pushed = "1"; node.style.setProperty("--fc-push", Math.min(p.pushed, p.top) + "px"); }
      else { delete node.dataset.pushed; node.style.removeProperty("--fc-push"); }
      // a card the focus moved up past its mark (card-layout.ts): a leader DOWN from its end to the mark's height
      const pull = p.desired === null ? 0 : p.desired - (p.top + p.height);
      if (pull >= 1) { node.dataset.pulled = "1"; node.style.setProperty("--fc-pull", pull + "px"); }
      else { delete node.dataset.pulled; node.style.removeProperty("--fc-pull"); }
    }
    const order = out.placed.map((p) => nodes.get(p.key)!);
    if (order.some((node, i) => node !== laid[i])) this.moving(order, () => { for (const node of order) list.appendChild(node); });
    // the body's end padding: the footer's height (the part of the body's box the track's box does not reach), plus how
    // far the last card hangs past the content's end. The content's height is the body's scroll height less the padding
    // it holds — known only while the body scrolls at all (scrollHeight floors at the box); a body that does not scroll
    // is padded by the footer alone, and its track goes on past it for the rest (followBody). That padding is KEPT only
    // where it lengthens the body. A box's padding comes out of its content box, and content sized to the box by a
    // `min-height: 100%` — the standalone picture's box (.fileview-imgbox, which centers the picture in itself), the Raw
    // view's — shrinks by the padding instead of scrolling: the body gained no range, and the picture rose by half the
    // footer at every open of the panel and fell back at the close, on no new information about it (the 2026-09-07
    // review, round 3). So the padding is written, then measured: where it bought the body no range it is taken back the
    // same pass (the content box is whole again before the frame paints, so no observer sees a change). A picture nearly
    // the box's height is the band where it does buy range — its own box outgrows the padded content box — and there it
    // stays, as the padding that lets the body reach a card at the picture's foot.
    const footer = Math.max(0, bodyRect.bottom - trackRect.bottom);
    const scrolls = body.scrollHeight > body.clientHeight;
    const content = scrolls ? body.scrollHeight - this.bodyPad : null;
    const hang = content === null ? 0 : Math.max(0, out.bottom + CARD_GAP + offset - content);
    this.padBody(body, Math.ceil(footer + hang));
    if (!scrolls && body.scrollHeight <= body.clientHeight) this.padBody(body, 0);   // bought no range: taken back
    list.style.height = Math.max(body.scrollHeight - body.clientHeight + track.clientHeight, out.bottom + CARD_GAP) + "px";
    this.placed = new Map(out.placed.map((p) => [p.key, p]));
    this.cardsEnd = out.bottom + CARD_GAP;
    this.syncTrack();
    if (this.savedOut) this.reflect();                 // the saved line follows the placement (reflectLines): the composer's close re-lays the cards, and the card may be in the box now
  }
  /** The margin layout ends (the fold, edit mode, the panel closing): the sheet's class, the body's end padding, the
   *  placement, the card observer, and what the pass wrote on the list and the cards go. The rows stand in the footer
   *  until the render that follows rebuilds the list. The list's inline height and the cards' tops and leaders are
   *  cleared HERE and not left to that render (the merge audit, 2026-09-09): the render rebuilds the list as a rule, but
   *  while a reply's box stands in a card it grafts around the box and keeps the live list and that card (swapCards), so
   *  the height the pass gave the list — the body's range, a screen and more past the cards — stayed on it in the list
   *  layout, and the aside scrolled through empty space under the cards until the box left the card or the columns came
   *  back; the kept card kept its top and its leader as well (no effect under the list's static positioning, but the
   *  next margin pass is the one to write them). */
  private layoutOff(): void {
    this.margin = false;
    this.root?.classList.remove("fc-margin");
    this.padBody(this.ctx.body(), 0);
    this.placed = new Map(); this.cardsEnd = 0;
    this.focusCard = null;                              // the focus is the margin layout's; the list has none
    this.laidOn = null;                                 // and so is the pass's memory of it
    this.cardSizer?.disconnect();
    const list = Array.from(this.sections.cards.childNodes).find((n) => n.nodeType === 1) as HTMLElement | undefined;
    if (!list) return;
    list.style.height = "";
    for (const node of Array.from(list.childNodes).filter((n) => n.nodeType === 1) as HTMLElement[]) {
      node.style.top = ""; delete node.dataset.pushed; delete node.dataset.pulled;
      node.style.removeProperty("--fc-push"); node.style.removeProperty("--fc-pull");
    }
  }
  /** The body's end padding, written only when it changes (an integer, so the rounding of scrollHeight cannot make the
   *  next pass read a different content height and write again). The track's box ends a footer's height above the
   *  body's — Accept all · Reject all, Send and the Log stand under it — so a mark in the text's last lines had its card
   *  under the footer with the body at its end, where no scroll reached it, and a card hanging below the content's end
   *  could be scrolled to only on the track, which the next pass pulled back (the 2026-09-07 review). The padding lets
   *  the body scroll that much further, so the two scrollers keep one range and the body reaches every card's end. */
  private padBody(body: HTMLElement, px: number): void {
    if (px === this.bodyPad) return;
    this.bodyPad = px;
    body.style.paddingBottom = px ? px + "px" : "";
  }
  /** In the margin layout the track holds cards alone. Every ROW the list held — the foot (Accept all · Reject all), a
   *  wait's loader, a refusal's row, the "… N more changes" and Resolved folds, the empty note — stands in the footer
   *  above Send: the foot first (so the footer begins with the changes' buttons; the sheet's rule stands on the section's
   *  top edge, so the footer begins under a rule whichever row comes first), then the other rows in the list's order. The
   *  track's scroll is the body's, so a row placed loose at the top of the track was out of view for a reader anywhere but the top of the text: the reload's loader and its
   *  deadline row with Reload among them, and the fold that says why a painted change has no card beside it (the
   *  2026-09-07 review; ui/CLAUDE.md: the loader first, an error where it can be acted on, no dead end). `kids`: the
   *  list's element children. */
  private moveRows(kids: HTMLElement[]): void {
    const rows = kids.filter((k) => !k.classList.contains("fc-card") && !k.classList.contains("fc-group"));
    if (!rows.length) return;
    const send = this.sections.send;
    const foot = rows.find((k) => k.classList.contains("fc-foot")) || null;
    const box = (Array.from(send.childNodes).filter((k) => k.nodeType === 1) as HTMLElement[]).find((k) => k.classList.contains("fc-send")) || null;
    this.moving(rows, () => {
      if (foot) this.sections.send.insertBefore(foot, this.sections.send.firstChild);
      for (const r of rows) if (r !== foot) send.insertBefore(r, box);
    });
  }
  /** The fold of a tall card (the focus follow-on, 2026-09-08). In the margin layout each long part of a card — a change's
   *  old and new text (`.fc-diff`), a comment's body, a run of turns — wears `fc-clip`, and the sheet caps it at about eight
   *  of its lines with a fade (`.fc-margin .fc-card:not(.fc-more) .fc-clip`); this reads which parts the cap cut (a part whose
   *  content is taller than its box), marks them for the fade (`data-clipped`) and shows the card's Show more row, rendered
   *  hidden, so a card with nothing cut offers no toggle. A card in `openBodies` wears `fc-more`: no cap, no fade, and the
   *  row reads Show less. Run before the cards' heights are measured, since the row is part of the height. The list layout
   *  runs no pass and caps nothing: the rows stay hidden there. A run of turns is cut at its START, not its end (keepEnd).
   *  The parts are every `.fc-clip` UNDER the card, not the card's own children alone: before the about follow-on
   *  (2026-09-10) a change card's hosted comments carried a body and a run of turns of their own, capped by the same
   *  sheet rule, and the card's one row lifted them with the change's text; a pass that skipped them would have left a run capped with no
   *  fade and, where the change's own text is short, no Show more at all — a compact view with no way in (the
   *  verification review, 2026-09-09; file-comments-focus-verify.test.ts drives both). */
  private clipCards(kids: HTMLElement[]): void {
    for (const card of kids) {
      if (!card.classList.contains("fc-card") || !card.dataset.id) continue;
      const row = card.querySelector(".fc-clip-row") as HTMLElement | null;
      if (!row) continue;                              // a closed card: no parts
      const open = this.openBodies.has(card.dataset.id);
      let cut = false;
      for (const part of Array.from(card.querySelectorAll(".fc-clip")) as HTMLElement[]) {   // every part under the card
        const over = !open && part.scrollHeight > part.clientHeight + 1;
        if (over) { part.dataset.clipped = "1"; cut = true; } else delete part.dataset.clipped;
        if (part.classList.contains("fc-replies")) this.keepEnd(part, over);
      }
      row.hidden = !(open || cut);
    }
  }
  /** A folded run of turns shows its END. The turns stand in `ts` order (renderTurns), so the newest — the session's latest
   *  answer, the turn the person re-engages for, the one a reply box under the run answers — is the LAST row, and a cap that
   *  kept the first eight lines showed the oldest turns and hid it behind Show more (the 2026-09-08 review). The cut part is
   *  scrolled to its end (an `overflow: hidden` box scrolls by script, and a fresh render's box starts at 0, so every pass
   *  writes it); the sheets put its fade at its FIRST lines, where the cut is (`.fc-replies.fc-clip[data-clipped]`, against
   *  the last-lines fade of every other cut part). A part not cut stands at its start. */
  private keepEnd(part: HTMLElement, cut: boolean): void {
    if (cut) part.scrollTop = part.scrollHeight;
    else if (part.scrollTop) part.scrollTop = 0;
  }
  /** The Show more / Show less row at an open card's foot (clipCards): a button through the delegate root (fcclip, with the
   *  delegate's flash), hidden until the pass finds a part cut. */
  private clipRow(key: string): HTMLElement {
    const row = el("div", "fc-clip-row");
    const open = this.openBodies.has(key);
    const b = btn(open ? "Show less" : "Show more", "fcclip");
    b.dataset.id = key;
    b.title = open ? "Fold the long text back to a few lines" : "Show the whole text";
    b.setAttribute("aria-expanded", open ? "true" : "false");
    row.appendChild(b);
    row.hidden = true;
    return row;
  }
  /** Make `key` the focus (focusCard): the pass anchors the layout on it from now on, and runs at once when the focus
   *  changed, so the scroll that follows (centerOn) reads the card where it now stands, level with its mark. False for a key
   *  the list shows no card for (a fold hides it; a card not rendered), which changes nothing. True for a loose card, whose
   *  pass keeps the focus it had (laidOn) and moves nothing: the caller's showLoose then scrolls to the card where it stands. */
  private focusOn(key: string): boolean {
    if (!this.sections.cards.querySelector('.fc-card[data-id="' + cssId(key) + '"]')) return false;
    if (this.focusCard !== key) { this.focusCard = key; this.placeCards(false); }
    return true;
  }
  /** Move nodes with `move`, and give the keyboard back to the control it was on when the move detached it: a node
   *  taken out of the document — an insertBefore or appendChild of a node already in it takes it out first — loses its
   *  focus to the body (the browser's focus-fixup rule), and render's refocus ran BEFORE this pass, on the fresh Accept
   *  all or Reject all in the list; moved to the footer, it had lost the keyboard again (the 2026-09-07 review). */
  private moving(nodes: HTMLElement[], move: () => void): void {
    const held = document.activeElement as HTMLElement | null;
    const kept = held && nodes.some((k) => k.contains(held)) ? held : null;
    move();
    if (kept) kept.focus({ preventScroll: true });
  }
  /** The body's content — the rendered markdown's box, the Raw view's, a picture, the pages' host — joins the size
   *  observer each pass, as the body's children stand then (a mode switch or a re-fetch replaces them). The body is a
   *  flex-sized scroller: its own box does not change when its CONTENT grows, so a reflow inside it — a <details>
   *  opened, an embed sized late — moved every mark below the change while the cards kept their tops until some
   *  unrelated event re-ran the pass (the 2026-09-07 review). The content's box does change. */
  private watchContent(body: HTMLElement): void {
    if (!this.sizer) return;
    const now = Array.from(body.childNodes).filter((k) => k.nodeType === 1) as Element[];
    for (const k of this.contentWatched) if (!now.includes(k)) { this.sizer.unobserve(k); this.contentWatched.delete(k); }
    for (const k of now) if (!this.contentWatched.has(k)) { this.sizer.observe(k); this.contentWatched.add(k); }
  }
  /** The track's cards in the order they are read: the DOM's, which the pass sorts into placement order — or, in the
   *  margin layout between a render and its pass, the last pass's order, since the fresh list stands in the model's
   *  order until placeCards re-sorts it, and a place kept by index (focusKey, focusNear) must name the same card before
   *  the rebuild and after. Cards the last pass did not place (new ones) follow, in the DOM's order. */
  private cardsInOrder(): HTMLElement[] {
    const all = Array.from(this.sections.cards.querySelectorAll(".fc-card")) as HTMLElement[];
    if (!this.margin || !this.placed.size) return all;
    const rank = new Map<string, number>();
    for (const k of this.placed.keys()) rank.set(k, rank.size);
    const at = (c: HTMLElement): number => { const r = rank.get(c.dataset.id || ""); return r === undefined ? rank.size + all.indexOf(c) : r; };
    return all.slice().sort((a, b) => at(a) - at(b));
  }
  /** The top of a card's mark in the viewport: the highest of its highlight rows, its framed figure, its region
   *  rectangle or its change marks — whichever the view paints; null when it paints none, or the mark has no box
   *  yet (a figure not loaded, a page not drawn): the loose group, until the load or the draw re-runs the pass. */
  private markTop(key: string): number | null {
    const [act, id] = key.startsWith("chg:") ? ["fcchange", key.slice(4)] : ["fcopen", key];
    let top = this.topOfMarks(act, id);
    if (top === null && !key.startsWith("chg:")) {
      // a comment with no mark of its own (no passage, no region) about a pending change (the about follow-on: a deletion's,
      // whose text is not in the file): laid at that change's mark, the first pending one it names
      const card = this.cards().find((c) => c.id === key);
      if (card && !card.anchor && !card.target) {
        for (const r of card.refs) { if (r.state !== "pending") continue; top = this.topOfMarks("fcchange", r.id); if (top !== null) break; }
      }
    }
    return top;
  }
  private topOfMarks(act: string, id: string): number | null {
    let top: number | null = null;
    for (const m of this.ownMarks(act, id)) {
      const r = m.getBoundingClientRect();
      if (r.width === 0 && r.height === 0) continue;
      if (top === null || r.top < top) top = r.top;
    }
    return top;
  }
  /** The lock: the scroller that moved writes its scrollTop onto the other, and the other's echo — the scroll
   *  event a write raises, on the next frame — is let through without a write back. `syncFrom` names the echo's
   *  source; a write that changed nothing raises no echo, so it is cleared at once then (writeScroll). An event
   *  attributed to the wrong scroller costs one write and no more: a genuine event taken for the echo is let through
   *  unmirrored, an echo taken for genuine writes the older position back once — and every write copies an absolute
   *  scrollTop, so the next genuine event puts both scrollers at the same position again. */
  private mirrorScroll(from: "body" | "track"): void {
    if (!this.margin || !this.open) return;
    if (this.syncFrom !== null && this.syncFrom !== from) { this.syncFrom = null; return; }
    this.syncFrom = null;
    if (from === "body") this.followBody();
    else this.writeScroll(this.ctx.body(), this.sections.cards.scrollTop, "track");
    if (this.savedOut) this.reflect();                 // the saved line follows the card's side against the box as the two scrollers now stand, and ends with the card coming into it (reflectLines)
  }
  private writeScroll(dst: HTMLElement, want: number, from: "body" | "track"): void {
    const before = dst.scrollTop;
    if (before === want) return;
    this.syncFrom = from;
    dst.scrollTop = want;
    if (dst.scrollTop === before) this.syncFrom = null;   // clamped to where it was: no echo will come
  }
  /** The track to the body's position at once (the pass, centerOn), not on the body's event a frame later. */
  private syncTrack(): void {
    if (this.margin) this.followBody();
  }
  /** The body's position onto the track — except past the body's end. The body's end padding (padBody) gives the two
   *  scrollers one range wherever the body scrolls at all; where it does not (a short file, a picture sized to the
   *  box) the track's content still reaches the last card's end, and a card under the footer's band or hanging past
   *  the content shows only when the track scrolls on alone (a wheel over the cards; centerOn). With the body at its
   *  end the track is left where it stands, as far as the last card's end — beyond that it shows nothing, and is
   *  brought back to it; before this, a pass or a status reply pulled the track back to the body and hid the card's
   *  end the person had just scrolled to (the 2026-09-07 review). Below the end the track follows the body as
   *  always, so the next scroll up puts every card level again. */
  private followBody(): void {
    const body = this.ctx.body(), track = this.sections.cards;
    const at = body.scrollTop;
    let want = at;
    if (track.scrollTop > at && atEnd(body)) want = Math.min(track.scrollTop, Math.max(at, this.cardsEnd - track.clientHeight));
    this.writeScroll(track, want, "body");
  }
  /** Scroll the body so the card's mark sits at the vertical center and the card, level with it, lands beside it. The
   *  card IS level because every caller makes it the focus first (focusOn, showCard: the pass anchors the layout on it,
   *  card-layout.ts). Before the focus follow-on (2026-09-08) a card pushed down by a tall card above it was brought in
   *  only as far as kept the mark's top in view, which put the mark at the body's top edge with the card still a
   *  viewport below (the defect the user hit). That fallback stays where the centered scroll would leave the focused
   *  card's end past the track's box: the body scrolls the least that shows the card's end, as far as keeps the mark's
   *  top in view. A card that fits the track lands whole, its head under the track's top; a card taller than the track
   *  has its head cut by the excess; and one taller than the track by more than the header less the gap meets the cap —
   *  the mark's top a gap under the body's top, the head cut by the header less the gap and the end still past the box,
   *  since no scroll shows both ends of such a card (the verification review, 2026-09-09: Show more on a long text is the
   *  usual way there, and the keyboard stays on its Show less at the foot, as the plan records; the plan's focus paragraph
   *  and file-comments-margin-fixes.test.ts pin this cap). Where the body cannot scroll that far (its end, in a body the
   *  padding could not lengthen: padBody) the track goes on alone, as far as the card's end (followBody keeps it there).
   *  False for a card the pass did not place beside a mark (loose: showLoose, for a caller that scrolls to it; a head
   *  click on a loose card moves nothing, afterRender).
   *  Coordinates: `p.top` and `p.height` are the TRACK's content (placeCards wrote the card's top as its mark's top in
   *  the body's content less the header's height), and the lock keeps the track's scrollTop the body's; so the scroll
   *  that shows the card's bottom is the card's bottom plus the gap less the track's box, with no header term. One
   *  added on top scrolled the header's height too far, and an opened card that fit the track landed with its head
   *  — the fold control, the reference link — under the panel's header (the 2026-09-07 review). */
  private centerOn(key: string): boolean {
    const p = this.placed.get(key);
    if (!p || p.desired === null) return false;
    const body = this.ctx.body(), track = this.sections.cards;
    const offset = track.getBoundingClientRect().top - body.getBoundingClientRect().top;
    const markY = p.desired + offset;                  // the mark's top in the body's content
    const view = body.clientHeight;
    let want = markY - view / 2;
    const showCard = p.top + p.height + CARD_GAP - track.clientHeight;   // the least scroll that shows the card's bottom (track content: no header term)
    if (showCard > want) want = Math.min(showCard, markY - CARD_GAP);
    this.scrollBoth(want);
    return true;
  }
  /** A loose card (no mark: the group at the top of the track) into the track's box, by the least scroll that shows it
   *  whole — what scrollIntoView's `nearest` scrolls the track by — written onto the body AND the track at once, as
   *  centerOn writes them. scrollIntoView moved the track alone, and the lock carries a track scroll onto the body only
   *  on the track's scroll EVENT: the browser delivers one per element per frame, so the render's own write onto the
   *  track (the echo the lock lets through unmirrored) and the scroll to the card arrived as one event, the body never
   *  followed, and the frame's pass brought the track back to the body — the card the save had scrolled to was out of
   *  view again (the 2026-09-07 review, in a real engine). False for a card with a mark (centerOn's) or one the pass did
   *  not place (the list layout; a card not yet rendered): the caller scrolls it into view as a list item. */
  private showLoose(key: string): boolean {
    const p = this.placed.get(key);
    if (!p || p.desired !== null) return false;
    const track = this.sections.cards;
    const at = track.scrollTop, box = track.clientHeight;
    let want = at;
    if (p.top - CARD_GAP < at) want = p.top - CARD_GAP;
    else if (p.top + p.height + CARD_GAP > at + box) want = p.top + p.height + CARD_GAP - box;
    this.scrollBoth(want);
    return true;
  }
  /** The composer's box into view where it stands (startReply; render, after a move while the person was typing). In the
   *  margin layout a reply's box stands in its card in the track (placeComposer), whose scroll is the body's: a
   *  scrollIntoView moved the track alone, the lock let the event through as the pass's echo, and the frame's pass brought
   *  the track back to the body (showLoose says the same of a card), so the least scroll that shows the box whole is
   *  written onto both scrollers (scrollBoth), as a loose card is shown. The box is read where the pass has just placed
   *  its card — render runs this after afterRender — and the pass never moves the box itself: it is a descendant of its
   *  card, not a child of the list, so the sheet's absolute positioning and moveRows leave it, and the card's observer
   *  covers its growth. In the slot above the track, or in the list layout, scrollIntoView's nearest as before. */
  private showComposer(): void {
    const box = this.composerBox, track = this.sections.cards;
    if (!this.margin || !track.contains(box)) { box.scrollIntoView({ block: "nearest" }); return; }
    const r = box.getBoundingClientRect(), top = r.top - track.getBoundingClientRect().top + track.scrollTop;
    const at = track.scrollTop, view = track.clientHeight;
    let want = at;
    if (top - CARD_GAP < at) want = top - CARD_GAP;
    else if (top + r.height + CARD_GAP > at + view) want = top + r.height + CARD_GAP - view;
    this.scrollBoth(want);
  }
  /** Both scrollers to `want`, a position in the one range the two share: the body as far as it can go, and the track to
   *  the body's position — or on alone, as far past the body's end as `want` and no further than the last card's end,
   *  where the body's padding could not lengthen it (padBody; followBody keeps it there). */
  private scrollBoth(want: number): void {
    const body = this.ctx.body(), track = this.sections.cards;
    want = Math.max(0, want);
    body.scrollTop = Math.min(want, body.scrollHeight - body.clientHeight);
    const at = body.scrollTop;                         // where the body could go
    this.writeScroll(track, want > at ? Math.min(want, Math.max(at, this.cardsEnd - track.clientHeight)) : at, "body");
  }
  /** The absolute path the kernel acts on, as far as the panel can know it. The kernel resolves the viewer's
   *  path (`~`, a relative chat or todo token against the session's cwd, then realpath) and builds the sent
   *  message from THAT, so the preview and the folder label must name it too (contract C3: identical text).
   *  No reply carries the resolved path itself; the store's own `path` is the file relative to the project
   *  root, written by the host from the resolved path (store-io's relPathFor, corrected on every load), so
   *  root + path IS it whenever a sidecar exists — and a preview needs unsent comments, so one does. With no
   *  sidecar, an absolute viewer path is the kernel's up to a symlink; a relative one names nothing, and the
   *  caller then says less rather than something wrong. */
  filePath(): string | null {
    const s = this.status;
    const rel = s && s.store ? s.store.path : null;
    if (s && s.root && typeof rel === "string" && rel && !rel.startsWith("/")) return s.root.replace(/\/$/, "") + "/" + rel;
    return this.ctx.path.startsWith("/") ? this.ctx.path : null;
  }

  // ── Send to session ────────────────────────────────────────────────────────────────────────────
  /** Fixed sequence (the plan's UX, D5): the message is built from the CURRENT status FIRST (a bound
   *  comment's desc needs the change's old and new text, which an accept removes), then set-tracked when
   *  asked, then the accept of the seen pending changes by id when the box is checked (decision 41: never an accept-all,
   *  and the ids are the ones the confirm showed, pendingSplit), then fileCommentsSend with `tracked` set to the
   *  post-toggle verdict and `accepted` = what the log says is unsent plus the N the accept's reply lists as decided;
   *  a refusal at any step aborts before the send. The comments are already on disk, so a refusal loses nothing. */
  /** Resolve answered (decision 46): the person's open comments the session has answered, read off the cards at the press
   *  (answeredComments: the status is the one source, and nothing is kept between the button and the click), resolved
   *  through the host's resolve op one request each, in the cards' order; a refusal stands under that comment's card as
   *  the card's own Resolve's would (mutate's row) and the rest go on. The ones resolved are offered back as Reopen all
   *  in the acknowledgment's position until the person's next gesture (reopenAll; gesture ends it).
   *  The file-editing consent is asked ONCE for the run (consentForRun), before the first request: asked per write, as
   *  mutate asks it, a decline was asked again for every comment and left one identical row per comment at the list's foot
   *  (the review, 2026-09-10); declined, the one row stands under the header action (the answered slot) and nothing goes. */
  async resolveAnswered(): Promise<void> {
    if (this.resolvingAnswered) return;
    const ids = answeredComments(this.cards()).map((c) => c.id);
    this.resolveAnsweredConfirm = false;
    if (!ids.length) { this.render(); return; }
    this.resolvingAnswered = true; this.reopenAll = null; this.render();
    const done: string[] = [];
    try {
      if (!(await this.consentForRun())) return;
      for (const id of ids) {
        const r = await this.mutate("resolve", { commentId: id, on: true }, "card:" + id);
        if (r) done.push(id);
      }
    } finally {
      this.consentHeld = false;
      this.resolvingAnswered = false;
      this.reopenAll = done.length ? done : null;
      this.render();
    }
  }
  /** Reopen all: the same comments back, one request each, the offer taken; the consent once, as for the resolve. */
  async reopenAnswered(): Promise<void> {
    const ids = this.reopenAll;
    this.reopenAll = null;
    this.render();
    if (!ids || !ids.length) return;
    try {
      if (!(await this.consentForRun())) return;
      for (const id of ids) await this.mutate("resolve", { commentId: id, on: false }, "card:" + id);
    } finally { this.consentHeld = false; }
  }
  /** The file-editing consent for a run of writes (resolveAnswered, reopenAnswered): one ask, held for the run (consentHeld,
   *  which the caller clears when its run ends); declined, mutate's words in the answered slot, under the header action that
   *  asked (renderHead), and false. */
  private async consentForRun(): Promise<boolean> {
    this.errors.delete("answered");
    if (await this.ctx.ensureEditingAllowed()) { this.consentHeld = true; return true; }
    this.errors.set("answered", { text: CONSENT_REFUSED, reload: false });
    this.render();
    return false;
  }
  async doSend(): Promise<void> {
    const s = this.status;
    if (!s || this.statusRefusal || this.sending || !this.ctx.sid) return;   // statusRefusal: renderSend says why
    // the note (the fields' comment): trimmed as the kernel reads it (trimNote: NEL or an ASCII separator alone is no note here
    // as there, so the wire never carries words the kernel would strip to nothing and drop without a word), refused over the
    // bound before any request goes; with nothing unsent it is the whole message, and without it there is nothing to send
    // (renderSend keeps the confirm's Send off then)
    const note = trimNote(this.sendNote);
    const long = noteTooLong(note);
    if (long) { this.errors.set("send", { text: long, reload: false }); this.render(); return; }
    if (!unsentCount(s.unsent) && !note) return;
    const parts: SendParts = sendParts(s);
    let tracked = !!s.trackedBy;
    // the keyboard in the note box as the send begins: the render below takes the confirm down for the wait (renderSend), and
    // the box with it, and a box out of the document drops the keyboard to the body. A refusal brings the box back with its
    // words (the confirm stands: sendConfirm) and the keyboard goes back into it (the finally), so the chord sends again —
    // before, the next Cmd/Ctrl+Enter reached the body and sent nothing (the review, 2026-09-09). A send that went closes the
    // confirm, and there is no box to put it back in
    const noting = document.activeElement === this.noteBox;
    // a send is a gesture, and the send's own (sendPress): a card on screen at the press is seen for the next confirm, and
    // this confirm's option and count row stay as the person read them (syncAcceptOption), since the split below is theirs
    this.sendPress = true;
    this.gesture();                                    // a send is a gesture of the person's (the arrivals follow-on)
    this.sendPress = false;
    // the changes the send accepts on the way (decision 41): the pending changes the person has SEEN, by id through the
    // same accept the card's button uses, never an accept-all — an unseen change stays pending for the next look. The seen
    // ones as the confirm SHOWED them (pendingSplit over confirmSeen): what the option and the count row said at the press
    // is what goes, and a card the press itself marked seen waits for the next send (the fields' comment has the case).
    // None while the editor is up, whose marks they are (DECIDES; renderSend shows no box for them then), and none with
    // the box unchecked; the counts then carry only the log's own decisions. Once the accept answers, the N it decided
    const acceptIds = this.sendOpts.accept ? this.pendingSplit(s).seen.map((h) => String(h.id)) : [];
    let accepted = 0;
    this.sending = true; this.errors.delete("send"); this.render();
    try {
      if (this.sendOpts.track && !s.trackedBy) {
        const r = await this.mutate("set-tracked", { on: true, scope: "file" }, "send");
        if (!r) return;
        tracked = !!r.trackedBy;
        // the accept below takes its baseline from the status it finds (mutate: seenChanges over this.status), and set-tracked
        // has just applied a fresh one — so a seen change grown between the press and that reply (a track-edit coalesced into
        // it: the same id, more text) would read as unchanged and be accepted unread. With no track box the accept goes first,
        // on the press's fence, and a moved store has mutateOnce stand down on the same growth; this path stands down the same
        // way, against the status the confirm was read from (the review, 2026-09-09): the row says so, and nothing is sent
        const grown = changedSince(seenChanges(s, { ids: acceptIds }), r.hunks || []);
        if (grown.length) { this.errors.set("send", { text: changedRowText(grown.length), reload: false }); return; }
      }
      if (acceptIds.length) {
        const a = await this.mutate("accept", { ids: acceptIds }, "send");
        if (!a) return;                                // a refused accept sends nothing: the message would claim decisions never made
        // A is what the accept DECIDED, read off its reply — never the count the confirm was built from: a change gone
        // between the two is the host's to refuse by name, one grown is mutateOnce's to stand down on (and the track path's
        // check above), and the message and the log's send entry
        // must state the same accepts as the accept entry beside it (CLAUDE.md, the authoritative source). A reply
        // that does not say sends nothing: the decisions are in the log already, and the next Send carries them.
        const decided = (a as unknown as { accepted?: unknown }).accepted;
        if (!Array.isArray(decided)) {
          this.errors.set("send", { text: "Nothing sent: the reply to the accept did not list what it accepted, so the message could not state the count. The decisions are recorded; Send again to carry them.", reload: false });
          return;
        }
        accepted = decided.length;
      }
      const counts = sendCounts(parts, acceptIds.length > 0, accepted);
      // the todo this send answers (chosenTodoId): the one the confirm offered — the file was opened from it, or the
      // status lists it as naming this file — as the checkbox or the radio group left it; one id, or none
      const todoId = this.chosenTodoId(s);
      const msg: Record<string, unknown> = {
        sid: this.ctx.sid, path: this.ctx.path, tracked, comments: parts.comments,
        accepted: counts.accepted, rejected: counts.rejected, watermark: parts.watermark,
      };
      if (todoId) msg.todoId = todoId;
      if (note) msg.note = note;
      const reply = await this.sendOnce(msg, false);
      this.markOverlapped();                           // the send appended to the comments log: a status out meanwhile may predate it
      // the latch is the STAMP, not the attempt: a send the kernel warned it could not mark (user todos off,
      // the todo already settled) leaves the checkbox, so the todo is answerable from here once the switch
      // is back on; the settled case re-warns on a later send, honestly, until the kernel says which it was
      if (todoId && reply.todoStamped) answeredTodos.add(todoId);
      if (todoId && reply.todoStamped) answeredAt.set(todoId, reqSeq);   // …as of this request: a status issued after this point that lists the todo releases it (applyStatus)
      const who = this.sessionName();
      const base = reply.queued ? "Queued for " + who : "Sent to " + who + " at " + clock(Date.now());
      this.sentNote = base;                            // an accept resolves no comment (decision 42), so nothing leaves the visible list on a send and the line has no tail
      this.sentAck = base;                             // kept for the saved line's end, when the line has displaced it (the field's comment; restoreSent)
      if (reply.warning) this.errors.set("send", { text: reply.warning, reload: false, warn: true });
      this.sendConfirm = false;
      this.sendNote = ""; this.noteBox.value = "";     // sent: the words went with the message; a refusal (the catch) keeps them
      await this.refresh();
    } catch (err) {
      this.errors.set("send", { text: (err as { error: string }).error, reload: false });
    } finally {
      this.sending = false; this.render();
      if (noting && this.sendConfirm && this.root && this.root.contains(this.noteBox)) this.noteBox.focus({ preventScroll: true });   // refused: the box is back, and the keyboard with it
    }
  }

  /** The send itself, with the one retry every editing-off refusal gets (mutateOnce's branch): the kernel
   *  refuses a send while file editing is off, because the send's log entry is a disk write and a send the
   *  log cannot record would be offered again (kernel: _file_comments_send_op). The refusal's text carries
   *  the phrase the consent helper matches, so the panel re-offers the consent naming the machine and, on
   *  yes, sends once more; a no, or a second refusal, is the caller's error row. */
  private async sendOnce(msg: Record<string, unknown>, retried: boolean): Promise<{ queued: boolean; warning?: string; todoStamped: boolean }> {
    try { return await this.requestSend(msg); }
    catch (err) {
      const e = err as { code: string; error: string };
      if (!retried && e.code === "editing-off" && await this.ctx.ensureEditingAllowed(e.error)) return this.sendOnce(msg, true);
      throw err;
    }
  }

  // ── render ─────────────────────────────────────────────────────────────────────────────────────
  render(): void {
    if (!this.root || !this.open) return;
    const s = this.status;
    const { head, cards, send, log } = this.sections;
    if (!this.root.contains(head)) this.root.replaceChildren(head, this.composerBox, cards, send, log);   // built once per open; a reply's box leaves the slot for its card (placeComposer)
    const keep = this.focusKey();                      // the control holding focus, by identity: the rebuild detaches it
    // a control an earlier render rebuilt disabled is wanted back only while the keyboard is still where that render put it
    const want = this.wanted && document.activeElement === this.wanted.at ? this.wanted.key : null;
    this.wanted = null;
    // the box holding the keyboard: a reply's box stands in its card, and when the fresh list shows no card for it, or shows
    // its comment in another card, the rebuild below moves it — to the slot, or into that card (placeComposer) — and a moved
    // node drops its focus to the body, so the keyboard is put back afterwards, and the words' scroll offset with it (a
    // moved textarea scrolls back to its first line). `home` is the node the box stands in before the rebuild, for the
    // scroll below: swapCards keeps that node whenever the box stays, so a different node afterwards is a move
    const home = this.composerBox.parentElement;
    const typing = document.activeElement === this.input;
    const scroll = this.input.scrollTop;
    const noting = document.activeElement === this.noteBox;   // the Send confirm's note box, rebuilt around like the composer's
    const noteScroll = this.noteBox.scrollTop;
    this.latchReplyCard();                             // the reply's card stays open by key, whatever key the status gave it
    if (this.lit.size) this.lightChanges(Array.from(this.lit), false);   // the tag under the pointer is rebuilt below, and its leave never fires: unlight first
    // the arrivals (the arrivals follow-on): the first render with a status seeds the seen set with all of it — the person
    // is looking at the whole file, and nothing in it arrived while they were; the renders after mark the arrival cards
    // (newKeys → renderCard, renderChangeCard) and their marks in the body (markNew)
    const seeding = this.seenKeys === null && !!s;
    if (this.seenKeys === null && s) this.seenKeys = new Set(statusEntries(s).map((e) => e.key));
    if (seeding && s) this.recordPending(s);           // …and the texts of its pending changes, which a later status is read against (seenTexts)
    this.newKeys = new Set(Array.from(this.arrivals.values(), (e) => this.arrivalCard(e)));
    this.markNew();
    head.replaceChildren(this.renderHead(s));
    this.swapCards(this.renderCards(s));               // around the reply's box, when it stands in a card the fresh list keeps
    this.renderComposer();                             // after the cards: the box stands in a card of the fresh list, or in the slot (placeComposer)
    send.replaceChildren(this.renderSend(s));
    log.replaceChildren(this.renderLog(s));
    if (typing && document.activeElement !== this.input) this.input.focus({ preventScroll: true });
    if (this.input.scrollTop !== scroll) this.input.scrollTop = scroll;
    if (noting && document.activeElement !== this.noteBox) this.noteBox.focus({ preventScroll: true });
    if (this.noteBox.scrollTop !== noteScroll) this.noteBox.scrollTop = noteScroll;
    // the box moved while the person was typing in it: its card left the list and it went to the slot, above the cards and
    // off-screen when the list is long; or the card came back and it returned. (Until the about follow-on, 2026-09-10, it
    // could also go from one card to another: a comment bound to a change under the reply moved onto the change's card and
    // back to its own when the change was accepted; every comment is its own card now, so a card-to-card move has no
    // cause left, and the check below still covers one.) Each of those puts the box in a node other than `home`, and a
    // rebuild that keeps its card keeps that
    // node (swapCards), so the one check covers them; the box is brought into view, the slot's row saying why with it, and a
    // keyboard elsewhere leaves the view where the person put it. After the margin pass (afterRender): in the margin layout
    // a card the fresh list built has no top until the pass places it, so a scroll before the pass went to a place the
    // card would not stand, and the track's scroll is the body's (showComposer)
    const moved = typing && this.composerBox.parentElement !== home;
    if (keep) this.refocus(keep, want, false);
    this.afterRender();                                // the margin layout: place the fresh cards beside their marks, then any centering the click asked for
    // a control the pass SHOWS — the Show more row, rendered hidden and unhidden by clipCards — took no focus before it
    // (focus() on an element not rendered is a no-op), so the keyboard is put back once more; a no-op when the first
    // refocus landed it (the 2026-09-08 review: Enter on Show more left the keyboard on the body, and so did any re-render
    // while the keyboard was on the toggle)
    if (keep) this.refocus(keep, want, true);
    if (moved) this.showComposer();
  }
  /** The cards section takes the fresh list. While the reply's box stands in a card of the LIVE list and the fresh list has
   *  that card too, the nodes between the section and the box — the list and the card — stay in the document and take
   *  their fresh counterparts' children instead (graft): a textarea that
   *  leaves the document, even to come straight back, loses its undo history, its scroll offset, an IME composition in
   *  flight and (until render puts it back) the keyboard; only the value, the caret and the height survive a detach. The
   *  box leaves a card when the fresh list shows no card for its comment (placeComposer moves it to the slot). Until the
   *  about follow-on (2026-09-10) it also left when the list showed the comment in ANOTHER card, a passage comment the
   *  session answered with a bound track-edit moving onto the change's card and a hosted comment whose change was accepted
   *  moving to its own; every comment is its own card now, and the graft still covers a move if one arose. A move costs the detach:
   *  the chain from the section to the box changes depth, so no node of it can stand in for a counterpart, and a node
   *  cannot change parents without leaving the document — the engines' state-preserving move (moveBefore) keeps the focus
   *  and the scroll offset, both of which render restores anyway, and drops the undo history all the same (Chromium 151
   *  and Firefox 153, measured 2026-09-07). placeComposer stands the box in the card the fresh list shows, and render
   *  brings it into view there while the person is typing. */
  private swapCards(fresh: HTMLElement): void {
    const cards = this.sections.cards, box = this.composerBox;
    if (!cards.contains(box) || !this.graft(cards, [fresh], box)) cards.replaceChildren(fresh);
  }
  /** Give `live` the children `fresh` would have, with `keep` (a descendant of `live`) never leaving the document. At each
   *  level the live child on the way to `keep` stands in for its counterpart among the fresh children — the element with
   *  the same tag and data-id — wearing the counterpart's class and action, and takes the counterpart's children the same
   *  way; at `keep`'s own parent the fresh children go around `keep`, those from the `.fc-actions` on after it (where
   *  placeComposer stands the box: before the card's buttons). False, and nothing changed, when a level has no
   *  counterpart — the card is gone from the fresh list, or the comment stands in another card there (swapCards). */
  private graft(live: HTMLElement, fresh: Node[], keep: HTMLElement): boolean {
    const chain: HTMLElement[] = [];                   // the live nodes between `live` and `keep`, top down
    for (let n = keep.parentElement; n && n !== live; n = n.parentElement) chain.unshift(n);
    const twins: HTMLElement[] = [];                   // their fresh counterparts, level by level
    let among = fresh;
    for (const n of chain) {
      const t = among.find((f): f is HTMLElement => f.nodeType === 1 && (f as HTMLElement).tagName === n.tagName && (f as HTMLElement).dataset.id === n.dataset.id);
      if (!t) return false;
      twins.push(t); among = Array.from(t.childNodes);
    }
    let parent = live, kids = fresh;
    for (let i = 0; i <= chain.length; i++) {
      const kept = i < chain.length ? chain[i] : keep, twin = i < chain.length ? twins[i] : null;
      // where the kept node stands among the fresh children: its twin's place, or, for the box, before the card's buttons
      const acts = kids.findIndex((k) => k.nodeType === 1 && (k as HTMLElement).classList.contains("fc-actions"));
      const at = twin ? kids.indexOf(twin) : acts < 0 ? kids.length : acts;
      for (const k of Array.from(parent.childNodes)) if (k !== kept) parent.removeChild(k);
      kids.forEach((k, j) => { if (k !== twin) { if (j < at) parent.insertBefore(k, kept); else parent.appendChild(k); } });
      if (!twin) break;
      // the class (open, detached) and the action (a collapsed card is the control) are what a card's own node changes
      // between renders; its id attributes are what matched it, and the rest is constant per id
      kept.className = twin.className;
      if (twin.dataset.act === undefined) delete kept.dataset.act; else kept.dataset.act = twin.dataset.act;
      parent = kept; kids = Array.from(twin.childNodes);
    }
    return true;
  }
  // Every section's children are rebuilt per render, and a removed element loses its focus to the body — so
  // Enter on a card's head opened the card and left the keyboard nowhere: the second Enter did nothing (or
  // fell through to the chat's composer), and the person had to Tab back in after every toggle. The composer's
  // input persists for the same reason (the sections comment); the rebuilt controls are re-found instead, by
  // what they ARE — the action plus the id, key or slot that names its subject — never by their node, the way
  // render.ts refocuses the active tab after `#tabs` is rebuilt.
  // A control rebuilt DISABLED — Accept, Reject, Accept all and Reject all relabel and disable for their round trip
  // (ui/CLAUDE.md) — cannot take the focus back, and the card it sat on may be gone when the reply lands. The keyboard
  // then goes to the nearest place in the panel (focusNear: its card's head, the head of the card now at its place in
  // the list, the changes foot, Send, the head row's Comment button), and the control is remembered (wanted) and
  // re-found the moment a render shows it enabled again — so a refusal that keeps the card puts the keyboard back on
  // the button it left, and a decision that removes the card leaves it on the next card, never on the body.
  private focusKey(): FocusKey | null {
    const a = document.activeElement as HTMLElement | null;
    if (!a || !this.root || !this.root.contains(a) || !a.dataset) return null;
    const k: FocusKey | null = a.dataset.act ? { act: a.dataset.act, id: a.dataset.id, key: a.dataset.key, slot: a.dataset.slot }
      // a confirm checkbox, re-found by its option; a radio of the todo group by its option AND its value (the todo id, "" for none)
      : a.dataset.opt ? { act: "opt", key: a.dataset.opt, id: a.dataset.opt === "todopick" ? (a as HTMLInputElement).value : undefined } : null;
    if (!k) return null;
    const cards = this.sections.cards;
    if (typeof a.closest === "function") {
      // where in the list it sat: its card and that card's place; for the foot (Accept all, Reject all, the confirm),
      // the change card before it — the comment cards follow the foot, and Accept all's keyboard belongs with the changes.
      // The foot follows the change cards in the list, and stands in the footer in the margin layout (placeCards): the
      // last change card is the place before it either way — its index in the order the cards are read (cardsInOrder),
      // which in the margin layout is the placement's, not the list's
      const all = this.cardsInOrder();
      const card = a.closest(".fc-card"), foot = a.closest(".fc-foot");
      if (card && cards.contains(card)) { k.card = (card as HTMLElement).dataset.id; k.at = all.indexOf(card as HTMLElement); }
      else if (foot) { const changes = all.filter((c) => c.classList.contains("fc-change")); k.at = changes.length ? all.indexOf(changes[changes.length - 1]) : 0; }
    }
    return k;
  }
  /** The first FOCUSABLE control with `k`'s identity, disabled or not: a collapsed card carries the head's act and id
   *  too, but no tabindex. */
  private findControl(k: FocusKey): HTMLElement | null {
    if (!this.root) return null;
    // the panel's own option names, never a sidecar's text; a todo radio is told by its value, compared, never in a selector
    if (k.act === "opt") {
      const all = Array.from(this.root.querySelectorAll('[data-opt="' + k.key + '"]')) as HTMLElement[];
      return (k.id === undefined ? all[0] : all.find((n) => (n as HTMLInputElement).value === k.id)) || null;
    }
    for (const n of Array.from(this.root.querySelectorAll("[data-act]")) as HTMLElement[]) {
      const d = n.dataset;
      if (d.act === k.act && d.id === k.id && d.key === k.key && d.slot === k.slot && (n.tabIndex >= 0 || n.tagName.toUpperCase() === "BUTTON")) return n;
    }
    return null;
  }
  /** `settled`: whether the margin pass has run on the fresh list. render calls this before the pass (so a place kept by
   *  index, k.at, names the card it named before the rebuild: cardsInOrder) and again after it, for a control the pass
   *  shows — the Show more row (clipRow renders it hidden; clipCards unhides it) — which focus() cannot land on until then.
   *  A control found and enabled that takes no focus is therefore left for the second call before the pass, and treated
   *  as gone after it (the list layout, where the row stays hidden: the keyboard goes to the nearest place, not the body).
   *  A wanted control of the LIST — a card's Show less hidden by the fold to the list layout, a busy Accept or Reject — is
   *  remembered again for as long as it is in the list and the keyboard stays where this put it, whether the keyboard went
   *  to the nearest place or to k's own control: render drops the memory at its start, so a memory this re-armed only on
   *  the way to focusNear lasted one render — the toggle was forgotten on the first status or repaint while the columns
   *  stayed narrow, and the render after they came back left the keyboard on the card's head, where Enter folds the card,
   *  not the text; a busy Reject was forgotten the same way when a repaint landed during its round trip, and the refusal
   *  left the keyboard on the head (the verification review, 2026-09-09). The composer's controls keep the one render: its
   *  Save comes back enabled either with a refusal, in the render after the busy one, or in the render before a save closes
   *  the box (mutate's last render, then closeComposer), and a memory that reached that render took the keyboard into the
   *  closing box, and out of it to Reply, where the head had it (file-comments-reply-review2.test.ts pins the head). */
  private refocus(k: FocusKey, want: FocusKey | null, settled: boolean): void {
    if (!this.root || this.root.contains(document.activeElement)) return;   // still focused (the input; the call before the pass landed it): nothing to mend
    const enabled = (n: HTMLElement | null): HTMLElement | null => (n && !(n as HTMLButtonElement).disabled ? n : null);
    // focus a control and say whether it took: an element not rendered (a hidden row's button) ignores focus()
    const take = (n: HTMLElement): boolean => { n.focus({ preventScroll: true }); return document.activeElement === n; };
    const wf = want ? this.findControl(want) : null;   // the wanted control as the list has it: disabled or hidden still, or back
    const w = enabled(wf);
    if (w && (take(w) || !settled)) return;             // the button that was busy is back: the keyboard returns to it — after the pass, if it is not shown yet
    const n = this.findControl(k);
    if (enabled(n) && (take(n!) || !settled)) {
      // k's control took the keyboard while the wanted one, of the list, is still to come back: remembered at the place the
      // keyboard now holds
      if (wf && document.activeElement === n && !this.composerBox.contains(wf)) this.wanted = { key: want!, at: n! };
      return;
    }
    // disabled, gone, or not shown once the pass has run. A control of the cards list (the change cards, the foot): the
    // nearest place, remembering the control still to come back to — this one, or the wanted one. Elsewhere (the head row's
    // confirms), a control the rebuild removed lets the focus fall to the body, quietly: there is no place of its own to
    // stand in for it.
    if (typeof k.at !== "number") return;
    const pending = n ? k : wf ? want : null;
    const at = this.focusNear(k);
    if (at && pending) this.wanted = { key: pending, at };
  }
  /** Focus the nearest enabled control to where `k` sat — its card's head, the head of the card now at its place, a
   *  button of the changes foot, Send, Comment on this file — and return it; null when the panel offers none. */
  private focusNear(k: FocusKey): HTMLElement | null {
    if (!this.root) return null;
    const cards = this.sections.cards;
    const head = (c: Element | null | undefined): HTMLElement | null => (c ? (c.querySelector(".fc-card-head") as HTMLElement | null) : null);
    const picks: Array<HTMLElement | null> = [];
    if (k.card) picks.push(head(cards.querySelector('.fc-card[data-id="' + cssId(k.card) + '"]')));   // a comment id may hold a quote (cssId)
    if (typeof k.at === "number") { const all = this.cardsInOrder(); picks.push(head(all[Math.min(k.at, all.length - 1)])); }
    picks.push(...(Array.from(this.root.querySelectorAll(".fc-foot button")) as HTMLElement[]));   // in the list, or in the margin layout's footer
    picks.push(this.root.querySelector('[data-act="fcsend"]') as HTMLElement | null, this.root.querySelector('[data-act="fcfile"]') as HTMLElement | null);
    for (const n of picks) {
      if (n && !(n as HTMLButtonElement).disabled) { n.focus({ preventScroll: true }); return n; }
    }
    return null;
  }
  private errRow(slot: string): HTMLElement | null {
    const e = this.errors.get(slot);
    if (!e) return null;
    const row = el("div", "fileview-err fc-err" + (e.warn ? " fc-err-warn" : ""));
    row.dataset.slot = slot;
    const text = el("span", undefined, e.text);
    text.style.overflowWrap = "anywhere";              // the host names paths in its refusals; the poll names its target
    row.appendChild(text);
    if (e.reload) { const b = btn("Reload", "fcreload"); b.dataset.slot = slot; b.title = "Read the file and its comments again"; row.appendChild(b); }
    const x = btn("✕", "fcerrx", "fileview-btn fc-x"); x.dataset.slot = slot; x.setAttribute("aria-label", "Dismiss"); row.appendChild(x);
    return row;
  }
  private loader(slot: string): HTMLElement | null {
    if (!this.busy.has(slot)) return null;
    const w = el("div", "fileview-load fc-load");
    w.innerHTML = '<img src="/media/romp-swirl-glyph.svg" alt=""><span>romp</span>'
      + '<i class="fileview-dot"></i><i class="fileview-dot"></i><i class="fileview-dot"></i>';
    w.dataset.slot = slot;                             // so a render can tell which slots already show (strayRows)
    return w;
  }
  /** The rows and loaders of slots whose control the list no longer shows: a by-id Accept or Reject refused after the
   *  refresh removed its card (mutateOnce retries by id, and a change a track-edit coalesced away, or another client
   *  decided, is refused `no-change`), the foot's after a refresh left nothing pending, a comment card inside a closed
   *  fold. Rendered where the section was, so a clicked decision is never silent (CLAUDE.md, fail loudly; the plan:
   *  a second refusal is surfaced verbatim) and the row's ✕ can clear it. `list` is the section built so far. */
  private strayRows(list: HTMLElement, prefixes: string[]): HTMLElement[] {
    const shown = new Set(Array.from(list.querySelectorAll("[data-slot]")).map((n) => (n as HTMLElement).dataset.slot));
    const stray = (slot: string) => prefixes.some((p) => slot === p || slot.startsWith(p)) && !shown.has(slot);
    const out: HTMLElement[] = [];
    for (const slot of this.busy) if (stray(slot)) { const w = this.loader(slot); if (w) { out.push(w); shown.add(slot); } }
    for (const slot of this.errors.keys()) if (stray(slot)) { const r = this.errRow(slot); if (r) { out.push(r); shown.add(slot); } }
    return out;
  }
  private chip(author: string, authorId: string | null): HTMLElement {
    if (author === "you") return el("span", "fc-chip fc-chip-you", "you");
    const c = authorId && this.colors ? this.colors.get(authorId) : null;
    const chip = el("span", "fc-chip", c ? c.name : author || "unknown");
    if (c && c.color) { chip.style.background = c.color.bg; chip.style.color = c.color.fg; }
    return chip;
  }
  private renderHead(s: Status | null): HTMLElement {
    const head = el("div", "fc-head");
    const row = el("div", "fc-row");
    const t = btn("Track changes", "fctrack", "fileview-btn fc-toggle");
    const tb = s?.trackedBy || null;
    t.dataset.on = tb ? "1" : "0";
    t.setAttribute("aria-pressed", tb ? "true" : "false");
    t.textContent = "Track changes" + (tb ? (tb.kind === "folder" ? " · folder" : tb.kind === "inherited" ? " · inherited" : " · on") : "");
    t.title = tb ? (tb.kind === "inherited" ? "Tracked through " + tb.entry + "; turn it off there" : "Tracked by the entry " + tb.entry + "; click to stop")
      : "Record this session's edits to the file as changes you accept or reject";
    row.appendChild(t);
    // Show changes inline, beside Track changes, only while the file has changes to show (progressive disclosure: a
    // control over marks that do not exist is noise) and the read view is up (the editor draws every change itself)
    if (s && (s.hunks || []).length && !this.ctx.editing()) {
      const i = btn("Show changes inline", "fcinline", "fileview-btn fc-toggle");
      i.dataset.on = this.inline ? "1" : "0";
      i.setAttribute("aria-pressed", this.inline ? "true" : "false");
      // under Comments the read view paints no change mark whatever the setting (paintChanges), so the title says the filter
      // hides them and that the setting governs All and Changes — an ON toggle over a body with no marks must not claim marks
      // in the text (the review, 2026-09-07). The button stays: its setting is shared with the other views and other panels
      const withheld = this.activeFilter() === "comments";
      i.title = withheld
        ? (this.inline ? "Comments above hides the change marks with the change cards; under All or Changes the session's changes are marked in the text. Click to read the file without the marks there too"
          : "The marks are off, and Comments above hides them with the change cards; click to mark the session's changes in the text under All or Changes")
        : this.inline ? "The session's changes are marked in the text, insertions tinted and deletions struck; click to read the file without the marks"
        : "The marks are off and the file reads as it is; click to mark the session's changes in the text";
      row.appendChild(i);
    }
    row.appendChild(btn("Comment on this file", "fcfile"));
    // Resolve answered (decision 46): while the session has answered open comments of the person's, one action in the head
    // row resolves them all; at zero it is not offered (progressive disclosure), since there is nothing for it to do
    const answered = s ? answeredComments(this.cards()) : [];
    if (answered.length || this.resolvingAnswered) {
      const ra = btn(this.resolvingAnswered ? "Resolving…" : resolveAnsweredLabel(answered.length), "fcresolveanswered");
      ra.disabled = this.resolvingAnswered;             // posts-and-waits: disabled and relabeled for the round trips (ui/CLAUDE.md)
      ra.title = "Resolve the " + answered.length + " comment" + (answered.length === 1 ? "" : "s") + " of yours the session has answered; a comment stays open until you resolve it";
      row.appendChild(ra);
    }
    head.appendChild(row);
    // the filter (the filter follow-on, 2026-09-07): All · Comments N · Changes M, one group of the toggles' buttons on its own
    // row under them, the chosen one filled — offered once the file has a card to filter (filterOffered), and never before:
    // a control over an empty list is noise. Its counts are the action-row label's (cardCounts), so the glance and the
    // control agree. The buttons take the arrow keys as one group (the constructor's keydown).
    let filterRow: HTMLElement | null = null;          // the row the toggles' answers stand above (underToggles): the filter's, when offered; else the first of the head's other rows, set below
    if (filterOffered(s)) {
      const seg = el("div", "fc-row fc-filter");
      seg.setAttribute("role", "group"); seg.setAttribute("aria-label", "Show");
      const n = cardCounts(s);
      // a detached change is neither pending nor counted (cardCounts), and the Changes list shows its card in the detached
      // group: the option carries the action-row label's own detached clause ("Changes 0 · 1 detached"), so the count and
      // the list it opens agree and a file holding detached changes alone does not read as one with nothing to show
      const d = s && s.store ? detachedChanges(s.store).length : 0;
      // the marks half of each title is the read view's (paintAll): the editor (Slice 5) draws every change itself, from the
      // records it took at Edit, and no comment highlight, so while it is up the titles say what the list does and that the
      // editor's marks stay — the row is offered there all the same, since finding a comment among the change cards is
      // what the filter is for (Show changes inline, which governs marks alone, is not)
      const editing = this.ctx.editing();
      const commentsTitle = "Show only the comments, including comments on changes; " + (editing ? "the editor keeps every change marked in its text" : "the change marks in the text are hidden with the change cards");
      const changesTitle = "Show only the changes, each with the comments made on it" + (editing ? "" : "; the comment highlights in the text are hidden with the comment cards")
        + (d ? "; the " + (d === 1 ? "detached change is" : d + " detached changes are") + " listed too, in a group of " + (d === 1 ? "its" : "their") + " own" : "");
      const options: Array<[CommentsFilter, string, string]> = [
        ["all", "All", "Show every comment and change"],
        ["comments", "Comments " + n.comments, commentsTitle],
        ["changes", "Changes " + n.changes, changesTitle],
      ];
      for (const [key, label, title] of options) {
        const b = btn(key === "changes" && d ? label + " · " + d + " detached" : label, "fcfilter", "fileview-btn fc-toggle");
        b.dataset.key = key;
        b.dataset.on = this.filter === key ? "1" : "0";
        b.setAttribute("aria-pressed", this.filter === key ? "true" : "false");
        b.title = title;
        seg.appendChild(b);
      }
      head.appendChild(seg);
      filterRow = seg;
    }
    // a row answering a click on the toggles' row — the Track scope choice, the Stop confirm, the track slot's loader and
    // refusal — stands directly under that row, above the filter's, the way the foot's Reject-all confirm and Send's stand
    // under their buttons (the plan: an error row under the control that asked); the filter's row is under the toggles
    // again once the question is answered. The other head rows (the status refusal, the poll's, the editor's, the save's)
    // are about the file and the panel as a whole and keep their place below the filter's row.
    const underToggles = (n: HTMLElement): void => { head.insertBefore(n, filterRow); };
    if (this.trackChoice && s) {
      const pick = el("div", "fc-row fc-choice");
      pick.appendChild(el("span", "fc-note", "Track:"));
      pick.appendChild(btn("This file", "fctrackfile"));
      // the folder of the path the kernel acts on (filePath); when the panel cannot name it, the label says
      // "Its folder" and no more — the host computes the entry from the real path either way
      const abs = this.filePath();
      const f = btn(abs ? "Its folder " : "Its folder", "fctrackfolder");
      if (abs) { appendPath(f, folderOf(abs)); shrinkable(f); }
      f.title = "Everything under the folder, files not written yet included";
      pick.appendChild(f);
      pick.appendChild(btn("Cancel", "fctrackcancel"));
      underToggles(pick);
    }
    if (this.resolveAnsweredConfirm && s && answered.length) {
      // the confirm, under the toggles' row like the Track choice: one plain line, Resolve, Cancel
      const ask = el("div", "fc-row fc-choice");
      ask.appendChild(el("span", "fc-note", resolveAnsweredAsk(answered.length)));
      ask.appendChild(btn("Resolve", "fcresolveanswereddo"));
      ask.appendChild(btn("Cancel", "fcresolveansweredcancel"));
      underToggles(ask);
    }
    if (this.trackStop && s?.trackedBy) {
      const stop = el("div", "fc-row fc-choice");
      const ask = el("span", "fc-note", "Stop tracking everything under ");
      appendPath(ask, s.trackedBy.entry); ask.appendChild(document.createTextNode("?"));
      stop.appendChild(ask);
      stop.appendChild(btn("Stop", "fctrackstop"));
      stop.appendChild(btn("Cancel", "fctrackcancel"));
      underToggles(stop);
    }
    for (const n of [this.loader("track"), this.errRow("track"), this.errRow("head"), this.errRow("poll"), this.errRow("edit")]) if (n) head.appendChild(n);
    // the track slot's loader and refusal, built with the head's rows above: moved under the toggle that asked, like its confirms
    // (the head's own children with the slot — the row's ✕ and Reload carry it too, and stay in their row). With no filter row
    // (a file with nothing to filter, or no status) the move's anchor is the first of the head's other rows instead: an
    // insertBefore with no anchor appends, and appended after the status refusal's row the answer to the Track click stood
    // below a row about the file (the review, 2026-09-07). The answered slot's row (Resolve answered's or Reopen all's consent
    // refusal, consentForRun) is an answer to the action row's button too, and stands where its confirm stood.
    if (!filterRow) filterRow = (Array.from(head.childNodes) as HTMLElement[]).find((n) => n.nodeType === 1 && ["head", "poll", "edit"].includes(n.dataset.slot || "")) || null;
    for (const n of Array.from(head.childNodes)) if (n.nodeType === 1 && (n as HTMLElement).dataset.slot === "track") underToggles(n as HTMLElement);
    const ar = this.errRow("answered"); if (ar) underToggles(ar);
    const sv = this.errRow("save"); if (sv) head.appendChild(sv);   // a landed save's logWarning (saveThroughComments): the Log below lacks the entry
    // a Reload from the head's or the poll's row: the slot wears the loader where the row was, until the answer (refresh)
    for (const n of [this.loader("head"), this.loader("poll")]) if (n) head.appendChild(n);
    if (s && s.agentTooling === "absent") {
      head.appendChild(el("div", "fc-warn", "The session cannot reply to comments yet: the track-changents tooling is not linked into ~/.claude on the file's machine. Run romp's install.sh there."));
    }
    // the arrivals line (the arrivals follow-on, 2026-09-09): one line under the header while a session's changes, comments
    // or replies stand unseen, a button that shows the first of them (goToArrival); the words are the model's (arrivalWords)
    if (this.arrivals.size) head.appendChild(this.arrivalLine());
    // the saved line (savedLine; decision 43) in the list layout: under the header, where the person who just saved is looking
    // (the composer stands in the slot under it, placeComposer). The Send section is the scroller's foot there, below the very
    // card the line says is below, so a line in it was never on screen when it was needed (the review, 2026-09-09). The margin
    // layout's Send section is pinned at the panel's foot, and the line keeps the acknowledgment's position there (renderSend).
    const saved = this.savedLineHead();
    if (saved) head.appendChild(saved);
    return head;
  }
  /** The arrivals line, built from the arrivals as they stand; reflectSeen rewrites it in place between renders. */
  private arrivalLine(): HTMLElement {
    const b = btn(this.arrivalText(), "fcarrivals", "fc-sec fc-arrivals");
    b.title = "Show the first of them";
    return b;
  }
  private arrivalText(): string {
    return arrivalWords(Array.from(this.arrivals.values()), (author, authorId) => {
      const c = authorId && this.colors ? this.colors.get(authorId) : null;
      return c ? c.name : author || "unknown";   // the chip's own rule (chip): the session's current name, else the sidecar's label
    });
  }
  /** The box follows its content (autosizeComposer) on every input — unless the person dragged the handle, when their
   *  height stands until the composer closes; a box with no layout to measure keeps the height it had. An inline
   *  height that is not the one autosize last set was dragged there (the sheet's resize: vertical writes it, and
   *  fires no input); sizedTo holds that write as the box serialized it, so the comparison is string to string of one
   *  origin. Before the first keystroke autosize has set none — the box opens with no inline height, and
   *  closeComposer clears the height with sizedTo — so an inline height while sizedTo is null is a drag too: the
   *  first guard is that case, which the second cannot see (the 2026-09-07 review: a box dragged taller before a
   *  word was typed snapped back to its content on the first keystroke). */
  private autosize(): void {
    const ta = this.input;
    if (this.sizedTo === null && ta.style.height) return;                    // dragged before the first keystroke
    if (this.sizedTo !== null && ta.style.height !== this.sizedTo) return;   // dragged since
    const h = autosizeComposer(ta);
    if (h !== null) this.sizedTo = h;
  }
  /** The Send confirm's note box follows its content the same way, to SEND_NOTE_ROWS (the user's ruling, 2026-09-09: about
   *  eight rows, then scrolling), with the same two guards: the box wears .fc-input's resize handle, and a height the person
   *  dragged stands until the confirm closes with nothing kept (renderSend clears it with noteSizedTo, as closeComposer does
   *  the composer's). Before the guards, every keystroke snapped a dragged box back to its rows (the review, 2026-09-09). */
  private autosizeNote(): void {
    const ta = this.noteBox;
    if (this.noteSizedTo === null && ta.style.height) return;                    // dragged before the first keystroke
    if (this.noteSizedTo !== null && ta.style.height !== this.noteSizedTo) return;   // dragged since
    const h = autosizeComposer(ta, SEND_NOTE_ROWS);
    if (h !== null) this.noteSizedTo = h;
  }
  private renderComposer(): void {
    const c = this.composer;
    const box = this.composerBox;
    box.hidden = !c;
    const inCard = this.placeComposer();               // a reply's box into its card; every other box, and a closed one, into the slot
    if (!c) { this.input.hidden = false; return; }   // a re-place hid it; the next note needs it
    const ref = this.composerRef;
    ref.replaceChildren();
    ref.hidden = inCard;                               // in the card the comment itself is the reference: no row repeats it (ui/CLAUDE.md, the compact form)
    this.input.hidden = c.kind === "replace";          // a re-place takes a drag on the picture, not words
    this.input.placeholder = c.kind === "reply" ? "Your reply" : "Your comment";
    this.input.setAttribute("aria-label", c.kind === "reply" ? "Reply text" : "Comment text");
    if (c.kind === "reply") {
      if (!inCard) {
        // the list shows no card for the comment, so the box stands in the slot: the row names the comment and says why,
        // and the words stay in the box — a reply is never dropped because its card left the list
        ref.appendChild(el("span", "fc-note", "Reply on " + c.ref));
        const away = this.replyAway(c);
        ref.appendChild(el("span", "fc-note" + (away.gone ? " fc-refused" : ""), away.text));
      }
    }
    else if (c.kind === "replace") {
      // a PDF region whose page the document no longer has (pageGone): no page wears the re-place cue, so the note says so
      const card = c.page ? this.cards().find((x) => x.id === c.commentId) : undefined;
      const gone = !!card && this.pageGone(card);
      ref.appendChild(el("span", "fc-note", "Drag the comment's new place on " + (c.page ? "a page" : "the image") + " (now " + c.ref + (gone ? ", a page the PDF no longer has" : "") + "). Cancel keeps it where it is."));
    }
    else if (c.kind === "region") {
      if (c.refusal) {
        // no embed line, so no region — but a passage on that line can carry the note, and the switch keeps it (switchToRaw)
        // where Cancel drops it (closeComposer clears the input): the sentence points at the switch, never at Cancel
        ref.appendChild(el("span", "fc-note fc-refused", c.refusal[0].toUpperCase() + c.refusal.slice(1) + ". Select its line in the Raw view instead; the note stays."));
        const sw = btn("Switch to Raw", "fcraw");
        sw.title = "Raw view; select the line that embeds this image there";
        ref.appendChild(sw);
      } else {
        ref.appendChild(el("span", "fc-note", "On " + regionDesc(c.region, c.page)));
        const crop = cropThumb(c.img, c.region);
        if (crop) ref.appendChild(crop);
        if (c.range && c.text !== undefined && c.text !== this.indexedText()) {   // the file changed and the embed line was not followed into it (retargetComposer)
          const t = el("span", "fc-tag", c.tied ? "passage recurs" : "passage changed");
          t.title = c.tied ? EMBED_TIED : c.elsewhere ? EMBED_ELSEWHERE : "The file changed and the line embedding this figure was not found in it; Save asks the file's machine to place it, and refuses if it cannot";
          ref.appendChild(t);
        }
      }
    }
    else if (c.refusal) {
      ref.appendChild(el("span", "fc-note fc-refused", c.refusal.reason));
      const sw = btn("Switch to Raw", "fcraw");
      sw.title = c.refusal.rawHasQuote ? "Raw view, with this passage selected" : "Raw view, scrolled to the block; select the passage there";
      ref.appendChild(sw);
    } else if (c.quote) {
      const q = el("span", "fc-quote", c.quote.replace(/\s+/g, " ").trim());
      q.title = c.quote;
      ref.appendChild(el("span", "fc-note", "On "));
      ref.appendChild(q);
      if (c.range && c.text !== undefined && c.text !== this.indexedText()) {   // the file changed and the passage was not followed into it (retargetComposer)
        const t = el("span", "fc-tag", c.tied ? "passage recurs" : "passage changed");
        t.title = c.tied ? PASSAGE_TIED : c.elsewhere ? PASSAGE_ELSEWHERE : "The file changed and this passage was not found in it; Save asks the file's machine to place it, and refuses if it cannot";
        ref.appendChild(t);
      }
      if (c.about && !c.about.only) ref.appendChild(this.aboutOption(c.about));   // the changes the selection overlaps (the about follow-on)
    } else if (c.about && c.about.only) {
      // a comment about a change with no passage to carry it (the about follow-on): the change's words, and one line saying
      // where the card is laid and why (a deletion's text is not in the file; a detached change's no longer is)
      const ch = this.changeView().cards.find((x) => x.id === c.about!.ids[0]);
      ref.appendChild(el("span", "fc-note", "About the change "));
      const q = el("span", "fc-quote", ch ? ch.ref : c.about.ids[0]);
      if (ch) q.title = ch.kind === "ins" ? "Added: " + ch.newText : ch.kind === "del" ? "Removed: " + ch.oldText : ch.oldText + " → " + ch.newText;
      ref.appendChild(q);
      ref.appendChild(el("span", "fc-note", ch && ch.detached ? "The file no longer holds the change's text, so the comment stands with the change's card."
        : "The removed text is not in the file, so the comment is laid at the change's point."));
    } else ref.appendChild(el("span", "fc-note", "On this file"));
    const acts = this.composerActs;
    const saving = this.busy.has("composer");
    const save = btn(saving ? "Saving…" : "Save", "fcsave");
    save.disabled = saving;                            // posts-and-waits: disabled and relabeled for the round trip (ui/CLAUDE.md)
    this.input.readOnly = saving;                      // what is typed during the round trip would be lost with the note that lands
    // a refused mapping has nothing to save to — Raw or Cancel; Save would silently write a whole-file comment; a
    // refused region likewise, and a re-place saves nothing (the drawn region is the action)
    const noSave = c.kind === "replace" || ((c.kind === "comment" || c.kind === "region") && !!c.refusal);
    // the hint names the chord in the platform's words and sits at the row's left (fc-hint), the buttons at its right
    const hint = el("span", "fc-note fc-hint", composerHint(IS_MAC));
    acts.replaceChildren(...(noSave ? [] : [hint, save]), btn("Cancel", "fccancel"));
    const err = this.composerErr;
    err.replaceChildren(...[this.loader("composer"), this.errRow("composer")].filter((n): n is HTMLElement => !!n));
    if (!box.contains(this.input)) box.replaceChildren(ref, this.input, acts, err);   // built once; the input keeps its focus across renders
  }
  /** The composer's option for the changes a selection overlaps (the about follow-on, 2026-09-10): a checkbox in the
   *  reference row, checked as the box opens (About.on), "about this change" or "about N changes" (aboutOptionLabel), its
   *  title the changes' words; unchecked, Save writes a plain passage comment. The row's change listener keeps About.on. */
  private aboutOption(a: About): HTMLElement {
    const l = el("label", "fc-opt fc-about-opt");
    const cb = el("input") as HTMLInputElement;
    cb.type = "checkbox"; cb.checked = a.on; cb.dataset.opt = "about";
    l.appendChild(cb); l.appendChild(el("span", undefined, aboutOptionLabel(a.ids.length)));
    const cards = this.changeView().cards;
    l.title = a.ids.map((id) => { const ch = cards.find((x) => x.id === id); return ch ? ch.ref : id; }).join("\n");
    return l;
  }
  /** Where the box stands. A reply's box goes INSIDE the card the list shows for its comment — below the turns and above
   *  the buttons; every other kind's box, a closed one, and a reply whose card the list does not show (the comment
   *  resolved into the closed fold, gone from the sidecar, hidden by the Changes filter, a status not yet in) stand in the
   *  panel's own slot between the head and the cards, the reply's row saying why (replyAway). One box, moved between the two: the
   *  words, the caret and the height ride with the node. Moved only when it is not already where it belongs — moving a
   *  focused node, even onto its own place, drops the keyboard to the body, and a rebuilt list makes it move only when the
   *  list stops showing its card or shows its comment in another card: otherwise the card it stands in is kept around it
   *  (swapCards). Returns whether the box is in a card. */
  private placeComposer(): boolean {
    const box = this.composerBox, root = this.root;
    if (!root || !root.contains(this.sections.cards)) return false;   // the sections are the root's children from its first render
    const r = this.replyTo();
    const id = r === null ? null : cssId(r);           // escaped for the selector: a sidecar id may hold a quote (cssId)
    const host = id === null ? null : this.sections.cards.querySelector('.fc-card[data-id="' + id + '"]') as HTMLElement | null;
    const before = (parent: HTMLElement, next: HTMLElement | null): void => {
      const kids = Array.from(parent.childNodes);
      const at = kids.indexOf(box), want = next ? kids.indexOf(next) : kids.length;
      if (at < 0 || at !== want - 1) parent.insertBefore(box, next);
    };
    if (host) {
      before(host, (Array.from(host.childNodes) as HTMLElement[]).find((n) => n.nodeType === 1 && n.classList.contains("fc-actions")) || null);
      box.classList.add("fc-composer-in");
      return true;
    }
    before(root, this.sections.cards);
    box.classList.remove("fc-composer-in");
    return false;
  }
  /** Why the list shows no card for the reply's comment, for the slot's row: the cause, and where a fold hides the card, the
   *  row that brings it back (ui/CLAUDE.md: a compact view never dead-ends) — named in the text, and by its action in
   *  `back`, for the keyboard when the box closes (focusAway). The comment gone from the sidecar (`gone`: the row wears
   *  the refusal's colour); its card hidden while Changes is chosen above (every comment is its own card, the about
   *  follow-on, 2026-09-10, so the filter is the one row besides the fold that can hide one); the comment resolved since the
   *  reply began, or resolved before it and its Resolved fold closed since; else the one case left, a status not yet in. */
  private replyAway(c: { commentId: string; resolved: boolean }): { text: string; gone: boolean; back: "fcresolved" | "fcfilter" | null } {
    const found = this.cards().find((x) => x.id === c.commentId);
    if (!found) return { text: "The comment is gone from the file's comments.", gone: true, back: null };
    // the filter shows the changes alone: the card is behind All or Comments above (the row that brings it back is the
    // group's first button, All)
    if (this.activeFilter() === "changes") return { gone: false, back: "fcfilter", text: "The comment's card is hidden while Changes is chosen above (All or Comments shows it); the reply still goes to it." };
    if (found.resolved) return { gone: false, back: "fcresolved", text: c.resolved ? "The comment's card is under “Resolved” below; the reply still goes to it." : "The comment was resolved meanwhile, so its card is under “Resolved” below; the reply still goes to it." };
    return { gone: false, back: null, text: "The comment's card is not in the list; the reply still goes to it." };   // its own card, open, and not shown: a status not yet in
  }
  /** The line under Changes for the comment just saved there (noteHiddenSave): its card and its mark are hidden by the
   *  choice above, and the line names the options that show them, as the Changes empty state does — the card itself is
   *  not shown, since the filter's own words exclude it. Rendered while the list still hides the card; once it shows
   *  (another pick) or the comment is gone from the file's comments, the line is over and the id with it: a later return
   *  to Changes must not bring it back, the card having been seen. The ✕ ends it early (fchiddenx). In the margin layout
   *  the row is one the list held and stands in the footer above Send with the foot, the folds and the empty note
   *  (moveRows): a row at the top of a track locked to the body's scroll is out of view for a reader anywhere but the
   *  top of the text, and this line exists to be seen after a save made wherever the reader was. */
  private hiddenSavedRow(filter: CommentsFilter): HTMLElement | null {
    const id = this.hiddenSaved;
    if (id === null) return null;
    const card = this.cards().find((c) => c.id === id);
    if (!card || filter !== "changes") { this.hiddenSaved = null; return null; }
    const mark = card.target ? "rectangle" : card.anchor ? "highlight" : null;   // a whole-file comment has no mark in the file
    // .fc-note (0.86em) goes on the words alone, never on the row: a .fileview-btn (0.82em) under it would compound to
    // 0.705em, smaller than every other panel button and than the ✕ of an err row the same list can show a line below
    // (ui/CLAUDE.md, font sizes: nested em compounds; prefer flat contexts) — the Track scope and Reject all confirms put
    // the class on their span the same way
    const row = el("div", "fc-row fc-saved-hidden");
    row.dataset.id = card.id;
    row.appendChild(el("span", "fc-note", "Your comment is saved; its card" + (mark ? " and " + mark + " are" : " is")
      + " hidden while Changes is chosen above (All or Comments shows " + (mark ? "them" : "it") + ")."));
    const x = btn("✕", "fchiddenx", "fileview-btn fc-x"); x.setAttribute("aria-label", "Dismiss"); row.appendChild(x);
    return row;
  }
  private renderCards(s: Status | null): HTMLElement {
    const list = el("div", "fc-cards");
    // the filter (activeFilter): "all" is the whole list, the change cards then every comment's own card (the about
    // follow-on, 2026-09-10: no comment is drawn inside a change card any more; a comment about a change is its own card,
    // the two cross-linked by their tags); "comments" shows the comment cards and no change card; "changes" the change
    // cards alone. The keyed expand state is untouched by the choice: a card opened under one filter is open under the
    // next that shows it.
    const filter = this.activeFilter();
    const cards = filter === "changes" ? [] : this.cards();
    const view = filter === "comments" ? { cards: [], groups: [], shown: [], hidden: [], hiddenChanges: 0 } : this.changeView();
    if (!s) {
      // a wait wears the romp loader while a status ask is out (refresh); once the kernel refused, say what
      // follows — the reason and Reload are the head's row. Never a line claiming a read nothing is making.
      const w = this.loader("status");
      if (w) list.appendChild(w);
      else if (this.statusRefusal) list.appendChild(el("div", "fc-empty", "The comments could not be read, so none can be shown or written."));
      return list;
    }
    // a reject's reload is out: the body shows the bytes it changed, unmarked, until the fetch lands (awaitBytes)
    for (const n of [this.loader("bytes"), this.errRow("bytes")]) if (n) list.appendChild(n);
    const saved = this.hiddenSavedRow(filter);          // a comment saved under Changes: the line for its hidden card, where the card would be
    if (saved) list.appendChild(saved);
    if (!cards.length && !view.cards.length && filter === "changes") {
      // the changes alone, and none: the line says where the comments are (ui/CLAUDE.md, never dead-end a compact view)
      list.appendChild(el("div", "fc-empty", "No changes are pending. All or Comments above shows the comments."));
      for (const n of this.strayRows(list, ["change:", "changes", "card:"])) list.appendChild(n);
      return list;
    }
    if (!cards.length && !view.cards.length) {
      // the gesture is named wherever an overlay in view takes it (drawsRegions): the media body's picture, or a figure in
      // rendered markdown — the panel's guidance is the one place the drag is discoverable from; the overlay's own label
      // reaches assistive tech alone, and the crosshair names nothing
      const draws = this.drawsRegions();
      list.appendChild(el("div", "fc-empty", this.ctx.mode() === "media"
        ? (draws ? "No comments yet. Drag a rectangle on " + (this.ctx.media() === "pdf" ? "a page" : "the image") + ", or comment on this file." : "No comments yet. Comment on this file to leave one.")
        : draws ? "No comments yet. Select a passage and press Comment, drag a rectangle on a figure, or comment on this file."
        : "No comments yet. Select a passage and press Comment, or comment on this file."));
      for (const n of this.strayRows(list, ["change:", "changes", "card:"])) list.appendChild(n);   // a refusal whose card is gone still shows
      return list;
    }
    // the session's pending changes first: grouped by paragraph, the first GROUP_LIMIT groups shown, the rest
    // behind one row (moreChangesOpen), then Accept all · Reject all — the plan's Slice 2 surface. The detached
    // changes (kept in the sidecar, not pending) follow in their own group and count toward no decision.
    const pending = view.cards.filter((c) => !c.detached).length;
    if (view.cards.length) {
      for (const g of view.shown) {
        if (g.title) {
          const gh = el("div", "fc-note fc-group", g.title);
          gh.title = g.key === DETACHED_GROUP_KEY ? "The file no longer holds these changes' text; their record stays with the file's comments, and nothing here decides them"
            : "The paragraph these changes fall in";
          list.appendChild(gh);
        }
        for (const c of g.changes) list.appendChild(this.renderChangeCard(c));
      }
      if (view.hiddenChanges) {
        const more = btn(moreChangesLabel(view.hiddenChanges), "fcmore", "fc-sec");
        more.title = "Show every change"; more.setAttribute("aria-expanded", "false");
        list.appendChild(more);
      } else if (this.moreChangesOpen && view.groups.length > GROUP_LIMIT) {
        const fewer = btn("▾ Fewer changes", "fcmore", "fc-sec");
        fewer.setAttribute("aria-expanded", "true");
        list.appendChild(fewer);
      }
      if (pending) list.appendChild(this.renderChangesFoot(pending));
    }
    // a decision's row or loader whose card (or the foot) the fresh status no longer shows: where the changes were
    for (const n of this.strayRows(list, ["change:", "changes"])) list.appendChild(n);
    const open = cards.filter((c) => !c.resolved), done = cards.filter((c) => c.resolved);
    for (const c of open) list.appendChild(this.renderCard(c));
    if (done.length) {
      const fold = btn((this.resolvedOpen ? "▾ " : "▸ ") + "Resolved (" + done.length + ")", "fcresolved", "fc-sec");
      list.appendChild(fold);
      if (this.resolvedOpen) for (const c of done) list.appendChild(this.renderCard(c));
    }
    for (const n of this.strayRows(list, ["card:"])) list.appendChild(n);
    return list;
  }
  /** What the person can do about a region the card reports on (stale, unreadable), in the card's own words: Re-place
   *  when THIS card offers it; otherwise resolve, and where Re-place is — the tag's title used to say "Re-place it" to a
   *  phone that never gets the button (a coarse pointer draws nothing) and to a view that shows no picture (Raw, an SVG's
   *  Source), so the line names the way there instead of a control that is not on the card. A PDF region with no picture
   *  is on a page the viewer has not drawn — pdf.js could not (pageUnrendered), or the PDF shows as the browser's frame —
   *  and no other view draws it, so the line names the page rather than a view. */
  private regionRecourse(picture: Pictured | null, offered: boolean): string {
    if (offered) return "Re-place it where it belongs now, or resolve it.";
    if (!picture) return this.ctx.media() === "pdf" ? "Resolve it; re-placing it needs its page drawn in the viewer." : "Resolve it, or re-place it from the view that shows the image.";
    return "Resolve it, or re-place it from a computer: drawing a region needs a mouse.";
  }
  private renderCard(c: Card): HTMLElement {
    const isOpen = this.openCards.has(c.id) || this.replyTo() === c.id;   // open while its reply is written: the box stands in it (placeComposer)
    const loc = this.located.get(c.id);
    const picture = c.target ? this.regionImageFor(c) : null;   // the picture the region is on, in this view; null when it shows none
    const card = el("div", "fc-card" + (isOpen ? " open" : "") + (loc && loc.state === "detached" ? " fc-card-detached" : "") + (this.openBodies.has(c.id) ? " fc-more" : ""));   // fc-more: its long parts shown whole (clipCards)
    card.dataset.id = c.id;
    card.dataset.cue = "comment";                      // the left edge's colour: --accent for a comment (a region is one) — the sheets' [data-cue] rules
    if (this.newKeys.has(c.id)) card.dataset.new = "1";   // a comment or a reply of the session's the person has not seen (the arrivals follow-on): the head's dot
    // the expand/collapse target: the whole card while collapsed, the HEAD alone once open — the open body
    // is text to select and copy (the sheet gives it cursor: text), and a click there must not fold the card
    // away from under the selection. The head is a Tab stop and takes Enter/Space (KEY_ACTS).
    if (!isOpen) card.dataset.act = "fccard";
    const head = el("div", "fc-card-head");
    head.dataset.id = c.id; head.dataset.act = "fccard";
    head.tabIndex = 0; head.setAttribute("role", "button"); head.setAttribute("aria-expanded", isOpen ? "true" : "false");
    if (this.replyTo() === c.id) this.holdHead(head);
    // the kind cue (the filter follow-on, 2026-09-07): what the card is, in a word before the author's chip, so a comment
    // and a change read apart at a glance in a long list; the title says what kind of comment
    const kind = el("span", "fc-kind", c.kind === "region" ? "Region" : "Comment");
    kind.title = c.kind === "region" ? "A comment on a region of the picture" : c.kind === "file" && c.refs.length ? "A comment about a change"
      : c.kind === "file" ? "A comment on the file as a whole" : "A comment on a passage";
    head.appendChild(kind);
    head.appendChild(this.chip(c.author, c.authorId));
    const ref = el("span", "fc-ref", c.kind === "passage" ? "“" + c.ref + "”" : c.ref);
    ref.title = c.kind === "passage" ? c.anchor?.quote || c.ref : c.ref;
    // the link and Reveal scroll the read view or switch it to Raw; while the editor holds the body there is neither
    // (the viewer's setMode and scrollToOffset are no-ops then), so neither control is offered (Slice 5)
    const editing = this.ctx.editing();
    // a PDF region whose page is mounted but did not render (pageUnrendered) has no rectangle to reach, so its reference
    // reaches the page instead, where the chunk's notice says why (reveal): the compact card must not dead-end
    const unrendered = this.pageUnrendered(c);
    if ((c.anchor || c.target) && loc && loc.painted && !editing) {
      ref.dataset.act = "fcgoto"; ref.dataset.id = c.id; ref.classList.add("fc-link"); ref.title = c.target ? "Scroll to the region" : "Scroll to the passage";
      ref.tabIndex = 0; ref.setAttribute("role", "button");
    } else if (unrendered) {
      ref.dataset.act = "fcgoto"; ref.dataset.id = c.id; ref.classList.add("fc-link"); ref.title = "Scroll to the page; its notice says why it did not render";
      ref.tabIndex = 0; ref.setAttribute("role", "button");
    }
    head.appendChild(ref);
    // a region (Slice 3): whether the image still has the bytes it was drawn on (E2) — dashed on the picture, a tag here.
    // A PDF region whose page the document no longer has (Slice 4; pageGone) is stale whatever the hashes say: the
    // page it was drawn on is not there to be current on. A page pdf.js could not draw is NOT gone (the shell is
    // there): the hashes alone say whether the file changed, and a tag of its own says the page did not render
    const gone = this.pageGone(c);
    const regionSt = c.target ? regionState(c.target, this.status) : "current";
    // A RESOLVED region has no staleness left to report: the plan and the guide end "stale" at resolve or re-place, the
    // picture paints no rectangle for it (paintRegions), and the card offers no Re-place — so the stale tag, whose title
    // names that button, and the unknown tag and note would point at nothing; a page the PDF lost is no different. Its
    // card wears "resolved" alone (the 2026-09-06 review, which found a resolved region wearing both).
    const shownSt = c.resolved ? "current" : regionSt;
    const shownGone = gone && !c.resolved;
    // Re-place is the way out of a stale or unreadable region, and the card offers it only with a pointer that can draw
    // and a picture in view (below) — the comment's own, or for a PDF region whose page the document no longer has
    // (pageGone) ANY page: a PDF re-place may land on another page (onRegionDrawn), and the stale tag names Re-place as
    // the remedy, so the card must offer it there too rather than leave Resolve as the only way out. The words about
    // either state name what THIS card offers (regionRecourse), so a phone is never told to press a button it does not have
    const replaceOffered = (!!picture || gone) && !c.resolved && this.drawsRegions();
    const recourse = this.regionRecourse(picture, replaceOffered);
    // the stale words, the tag's title and the open card's note alike: which page the PDF lost, when that is what makes
    // the region stale (the page is not there to be current on, whatever the hashes say); else the file's own change
    const staleWords = shownGone
      ? pageGoneRegion(c.target!.page) + " " + (replaceOffered ? "Re-place it on a page it has, or resolve it." : "Resolve it, or re-place it on a page it has from a computer: drawing a region needs a mouse.")
      : staleRegion(this.mediaNoun()) + " " + recourse;
    if (shownGone || shownSt === "stale") { const t = el("span", "fc-tag fc-tag-stale", "stale"); t.title = staleWords; head.appendChild(t); }
    else if (shownSt === "unknown" && c.target) { const t = el("span", "fc-tag", "unknown"); t.title = unknownReason(c.target, this.status, c.id); head.appendChild(t); }
    if (unrendered) {
      const t = el("span", "fc-tag", "not rendered");
      t.title = "Page " + c.target!.page + " did not render, so this region is not shown; the PDF still has that page, and its notice says why";
      head.appendChild(t);
    }
    // a region the sidecar holds malformed (isRegion): no rectangle, no crop, and the card says so — the reference already
    // prints "?" in each slot it cannot read (regionDesc), and this names why the picture shows nothing for it
    const unreadable = !!c.target && !c.resolved && !isRegion(c.target.region);
    if (unreadable) { const t = el("span", "fc-tag", "unreadable"); t.title = UNREADABLE_REGION + " " + recourse; head.appendChild(t); }
    // a region whose picture this view does not show, with no passage to reveal in its place: a standalone image's region
    // seen in the SVG Source view (the XML). No seam call returns to the picture from here (setMode is the markdown
    // pair only), so the tag names the way back rather than leaving the card a dead end (ui/CLAUDE.md)
    if (c.target && !c.anchor && !picture && this.ctx.mode() !== "media") {
      const t = el("span", "fc-tag", "not shown");
      t.title = this.ctx.media() === "svg" ? "The Source view shows the XML, not the image; press Source again to see the region on it" : "This view does not show the image the region is on";
      head.appendChild(t);
    }
    if (loc && loc.state === "context") head.appendChild(el("span", "fc-tag", "text changed"));
    // a highlight on a copy the panel cannot vouch for (copyUnsure): the composer's chip for a pending passage in the same
    // state wears the same words, and the title says which copy is painted and why it is a guess
    if (this.unsureCopies.has(c.id)) { const t = el("span", "fc-tag", "passage recurs"); t.title = copyUnsureWords(c); head.appendChild(t); }
    if (loc && loc.state === "detached") head.appendChild(el("span", "fc-tag", "detached"));
    // the changes the comment names (refs; the about follow-on, 2026-09-10): one tag per source — "about N changes" for the
    // person's own pick, "answered by a change" for a legacy binding — its title the changes' words and states, and the
    // pointer over it lights the pending changes' marks in the text (lightChanges), so the comment and its changes read
    // together without a click; the change card's own tag counts the comments about it (renderChangeCard)
    const refNotes: string[] = [];                     // the about tag's words, for the open card (a title never reaches touch)
    for (const source of ["about", "answered"] as const) {
      const refs = c.refs.filter((r) => r.source === source);
      if (!refs.length) continue;
      const t = el("span", "fc-tag fc-about", aboutTagWords(refs.length, source));
      t.dataset.refs = refs.map((r) => r.id).join(" ");
      t.title = (source === "about" ? "This comment is about: " : "The session answered this comment with: ")
        + refs.map((r) => (r.kind === null ? "a change the file no longer records" : changeRef({ kind: r.kind, oldText: r.oldText, newText: r.newText })) + " (" + refStateWords(r.state) + ")").join("; ");
      if (source === "about") refNotes.push(t.title);   // the same words stand in the open card (below), where a title never reaches; an answered comment's open card shows the answering revision as a turn already (renderTurns)
      const pending = refs.filter((r) => r.state === "pending").map((r) => r.id);
      if (pending.length) {
        t.addEventListener("pointerenter", () => this.lightChanges(pending, true));
        t.addEventListener("pointerleave", () => this.lightChanges(pending, false));
      }
      head.appendChild(t);
    }
    // the decision, when every change the comment names was decided alike (cardModel): the person's own pick (about) is the
    // changes the comment is ABOUT, one or several (CONTEXT.md's vocabulary; before the about follow-on a comment named one
    // change, by the format's field, and the title said "on"); a legacy binding keeps the words it had
    if (c.decision) {
      const d = el("span", "fc-tag", c.decision);
      const about = c.refs.filter((r) => r.source === "about");
      d.title = "You " + c.decision + (about.length > 1 ? " the " + about.length + " changes this comment is about" : about.length ? " the change this comment is about" : " the change this comment is on");
      head.appendChild(d);
    }
    if (c.resolved) head.appendChild(el("span", "fc-tag", "resolved"));
    if (c.replies.length && !isOpen) head.appendChild(el("span", "fc-tag fc-count", String(c.replies.length)));
    head.appendChild(el("span", "fc-time", clock(c.ts)));
    card.appendChild(head);
    if (!isOpen) { card.appendChild(el("div", "fc-preview", c.body.replace(/\s+/g, " ").trim())); return card; }
    const held = this.replyTo() === c.id ? this.heldNote() : null;   // why the held head does not fold, in words, where the title cannot reach
    if (held) card.appendChild(held);
    const crop = c.target ? this.cropFor(picture, c) : null;   // the region cut from the picture (E5), or a page's kept crop
    if (crop) card.appendChild(crop);
    else if (c.target && this.pageUndrawn(c)) card.appendChild(this.cropWaitNote(c));   // no bitmap to cut: the slot says so and reaches the page
    card.appendChild(el("div", "fc-body fc-clip", c.body));   // a long body folds in the margin layout (clipCards)
    // the open card says in words what the region tags say — why the staleness is unknown (unknownReason), that the image
    // changed, that the region could not be read — each with its way out: the tags' titles never reach touch, where the
    // Re-place the stale title used to name is absent too (a coarse pointer draws nothing), so a phone saw a one-word tag
    // and no way to learn that resolving ends it (the 2026-09-06 review; ui/CLAUDE.md: never dead-end a compact view)
    if (this.unsureCopies.has(c.id)) card.appendChild(el("div", "fc-note", copyUnsureWords(c)));   // the tag's words, in reach of touch
    if (shownGone || shownSt === "stale") card.appendChild(el("div", "fc-note", staleWords));
    else if (shownSt === "unknown" && c.target) card.appendChild(el("div", "fc-note", unknownReason(c.target, this.status, c.id)));
    if (unreadable) card.appendChild(el("div", "fc-note", UNREADABLE_REGION + " " + recourse));
    // the changes the comment is about, in words (the about tag's title, which never reaches touch, and the pointer's lighting
    // of the marks, which a keyboard has no way to): on a phone the compact tag read "about 2 changes" and nothing said which
    // two or where (the review, 2026-09-10; ui/CLAUDE.md: never dead-end a compact view). A legacy comment a change answered
    // has no line: the answering revision stands among its turns below, old and new text (renderTurns)
    for (const words of refNotes) card.appendChild(el("div", "fc-note fc-about-note", words));
    if (c.replies.length) card.appendChild(this.renderTurns(c.replies));
    const acts = el("div", "fc-actions");
    const reply = btn("Reply", "fcreply"); reply.dataset.id = c.id; acts.appendChild(reply);
    const res = btn(c.resolved ? "Reopen" : "Resolve", "fcresolve"); res.dataset.id = c.id; res.dataset.on = c.resolved ? "0" : "1"; acts.appendChild(res);
    if (replaceOffered) {                              // Re-place: a pointer that can draw, and the picture in view — or any page, for a PDF region whose page went (replaceOffered)
      const rp = btn("Re-place", "fcreplace"); rp.dataset.id = c.id;
      rp.title = gone ? "The PDF no longer has this page: draw the region again on a page it has"
        : regionSt === "stale" ? "The " + this.mediaNoun() + " changed: draw the region again where it belongs now" : "Draw the region again; the comment keeps its words and its replies";
      acts.appendChild(rp);
    }
    const src = this.ctx.text();
    if (!editing) {
      if (c.anchor && loc && loc.range && !loc.painted) {
        const rv = btn("Reveal", "fcreveal"); rv.dataset.id = c.id;
        rv.title = "Show the passage in the Raw view" + (src !== null ? " (line " + (rawOffsetToLine(src, loc.range.start) + 1) + ")" : "");
        acts.appendChild(rv);
      }
    }
    card.appendChild(this.clipRow(c.id));               // Show more, when the pass finds a part cut (clipCards)
    card.appendChild(acts);
    for (const n of [this.loader("card:" + c.id), this.errRow("card:" + c.id)]) if (n) card.appendChild(n);
    return card;
  }
  /** The turns under a comment, in `ts` order: words as before; a revision (the session's answering
   *  track-edit, recorded as a reply with old and new text) as the same row with the texts instead of a body. */
  private renderTurns(turns: CardTurn[]): HTMLElement {
    const rs = el("div", "fc-replies fc-clip");         // a long run of turns folds in the margin layout (clipCards)
    for (const r of turns) {
      const row = el("div", "fc-reply" + (r.author === "you" ? " fc-reply-you" : ""));
      const meta = el("div", "fc-meta");
      meta.appendChild(this.chip(r.author, r.authorId));
      if (r.kind === "rev") { const t = el("span", "fc-tag", "revised"); t.title = "The session revised the text in answer"; meta.appendChild(t); }
      meta.appendChild(el("span", "fc-time", clock(r.ts)));
      row.appendChild(meta);
      row.appendChild(r.kind === "msg" ? el("div", "fc-body", r.body) : this.diffBody(r.oldText, r.newText));
      rs.appendChild(row);
    }
    return rs;
  }
  /** Old and new text as a body: the old struck (<del>), the new marked (<ins>) — the browser's own dress for
   *  both, so the sheets need no rule for it; either side may be empty (a pure insertion or deletion). */
  private diffBody(oldText: string, newText: string): HTMLElement {
    const b = el("div", "fc-body fc-diff");
    if (oldText) b.appendChild(el("del", "fc-old", oldText));
    if (oldText && newText) b.appendChild(document.createTextNode(" → "));
    if (newText) b.appendChild(el("ins", "fc-new", newText));
    if (!oldText && !newText) b.appendChild(el("span", "fc-note", "(no text)"));
    return b;
  }
  // ── the change cards (Slice 2) ─────────────────────────────────────────────────────────────────
  /** One card per pending change. Collapsed: the author's chip, the one-line reference (a link to its mark
   *  when the view shows one), the "N comments" tag counting the open comments about the change (a control: its click
   *  shows the first, showAbout), and the buttons — Accept and Reject are the card's reason to exist, so they never hide
   *  behind the expand. Open: the old and new text. No comment is drawn inside the card (the about follow-on, 2026-09-10:
   *  every comment is its own card, and a comment about this change wears the "about" tag); Comment on this change opens
   *  the composer over the change's span (startChangeComment) — offered for a spanned change only while the view carries
   *  its text (spanCarried: not while the bytes are in flux, since a comment then would name the wrong words or lose the
   *  passage; a deletion's is by id and stands whatever the view shows). Reveal on a deletion (a point in both views,
   *  which a scroll can miss) and on any change whose mark the view does not show — a refused block, or Show changes
   *  inline off — so the compact card never dead-ends. While the
   *  editor is up (Slice 5) the editor's own marks show every change, deletions included, and the read view Reveal
   *  and the link would scroll is gone, so neither is offered; Accept and Reject stay, and answer with where to
   *  decide (DECIDES).
   *  A DETACHED change (the load-time rebase could not place it; the sidecar keeps it, not pending) wears the
   *  comment cards' detached dress and a tag saying so, and offers no Accept, Reject, Comment on this change or Reveal:
   *  the host decides pending changes only and refuses each of those `no-change`, and the change's last offset points
   *  into a text that no longer holds it. Its texts are one click down, as ever. */
  private renderChangeCard(c: ChangeCard): HTMLElement {
    const isOpen = this.openCards.has(c.key);
    const editing = this.ctx.editing();
    const painted = this.paintedChanges.has(c.id);
    // the view's bytes are not the status's — a reject's reply landed and its reload has not, or the poll's reload landed
    // and its status has not — so nothing was painted, and nothing is known yet about what the view will show once the
    // two agree. Neither the "not shown" tag nor a Reveal is claimed on that: a tag and a button that appear for one
    // fetch and vanish with it would move on no new information (CLAUDE.md). A deletion's Reveal is constant and stays.
    const s = this.status;
    const inFlux = !!s && !this.textCurrent(s);
    const slot = "change:" + c.id;
    const card = el("div", "fc-card fc-change" + (isOpen ? " open" : "") + (c.detached ? " fc-card-detached" : "") + (this.openBodies.has(c.key) ? " fc-more" : ""));   // fc-more: its long parts shown whole (clipCards)
    card.dataset.id = c.key; card.dataset.change = c.id; card.dataset.kind = c.kind;
    card.dataset.cue = "change";                       // the left edge's colour: --text-muted for a change — the sheets' [data-cue] rules
    if (this.newKeys.has(c.key)) card.dataset.new = "1";   // a change the person has not seen (the arrivals follow-on)
    if (!isOpen) card.dataset.act = "fccard";
    const head = el("div", "fc-card-head");
    head.dataset.id = c.key; head.dataset.act = "fccard";
    head.tabIndex = 0; head.setAttribute("role", "button"); head.setAttribute("aria-expanded", isOpen ? "true" : "false");
    const kind = el("span", "fc-kind", "Change");      // the kind cue, as a comment card wears it (renderCard); no decision is offered on a detached change
    kind.title = c.detached ? "A change the session made to the file, whose text the file no longer holds; nothing here accepts or rejects it" : "A change the session made to the file, for you to accept or reject";
    head.appendChild(kind);
    head.appendChild(this.chip(c.author, c.authorId));
    const ref = el("span", "fc-ref", c.ref);
    ref.title = c.kind === "ins" ? "Added: " + c.newText : c.kind === "del" ? "Removed: " + c.oldText : c.oldText + " → " + c.newText;
    if (painted && !editing) {
      ref.dataset.act = "fcgoto"; ref.dataset.id = c.key; ref.classList.add("fc-link"); ref.title = "Scroll to the change";
      ref.tabIndex = 0; ref.setAttribute("role", "button");
    }
    head.appendChild(ref);
    const src = this.ctx.text();
    if (c.detached) {
      const t = el("span", "fc-tag", "detached");
      t.title = "The file no longer holds this text, so the change cannot be accepted or rejected; its record stays with the file's comments";
      head.appendChild(t);
    } else if (!painted && this.inline && !editing && !inFlux && src !== null && this.ctx.mode() !== "media") {
      // with the marks off (inline) the view shows no change by choice, and the tag would claim a failing that is none
      const t = el("span", "fc-tag", "not shown");
      t.title = "This view does not show the change; Reveal opens it in Raw";
      head.appendChild(t);
    }
    if (c.comments) {   // the open comments about this change (the about follow-on): a control, its click showing the first of them
      const t = el("span", "fc-tag fc-count fc-about-count", c.comments + (c.comments === 1 ? " comment" : " comments"));
      t.dataset.act = "fcaboutfirst"; t.dataset.id = c.id; t.tabIndex = 0; t.setAttribute("role", "button");
      t.title = c.comments === 1 ? "Show the comment about this change" : "Show the first of the comments about this change";
      head.appendChild(t);
    }
    head.appendChild(el("span", "fc-time", clock(c.ts)));
    card.appendChild(head);
    if (isOpen) {
      const diff = this.diffBody(c.oldText, c.newText);
      diff.classList.add("fc-clip");                   // a replaced paragraph's old and new text: the tall part the margin layout folds (clipCards)
      card.appendChild(diff);
      card.appendChild(this.clipRow(c.key));           // Show more, when the pass finds a part cut
    }
    if (!c.detached) {
      const acts = el("div", "fc-actions");
      const busy = this.busy.has(slot); const verb = this.busyVerb.get(slot);
      const decide = editing ? decideInEditor() : "";
      const ok = btn(busy && verb === "accept" ? "Accepting…" : "Accept", "fcaccept"); ok.dataset.id = c.id; ok.disabled = busy;
      ok.title = editing ? decide : "Keep the text as it is and drop the change";
      const no = btn(busy && verb === "reject" ? "Rejecting…" : "Reject", "fcreject"); no.dataset.id = c.id; no.disabled = busy;
      no.title = editing ? decide : "Put the old text back in the file";
      if (editing) { ok.classList.add("fileview-btn-blocked"); no.classList.add("fileview-btn-blocked"); }   // real buttons, dimmed: the click answers in place (DECIDES)
      acts.appendChild(ok); acts.appendChild(no);
      // Comment on this change (the about follow-on; before: Reply, a comment bound by the format's own field): for a spanned
      // change only while the view carries its text (spanCarried) — in flux, the composer over the span would quote other
      // bytes and one by id alone would lose the passage the change has; it comes back with the bytes, as Reveal does below
      if (c.curTo === c.curFrom || this.spanCarried(c)) {
        const re = btn("Comment on this change", "fcchangecomment"); re.dataset.id = c.id;
        re.title = "Leave a comment about this change; the message to the session names the change and its text";
        acts.appendChild(re);
      }
      if (!editing) {   // Reveal switches to Raw and scrolls the read view: neither exists while the editor holds the body, which shows the change itself
        if (c.kind === "del" || !painted) {
          const rv = btn("Reveal", "fcreveal"); rv.dataset.id = c.key;
          const line = src !== null && !inFlux ? " (line " + (rawOffsetToLine(src, c.curFrom) + 1) + ")" : "";
          // with Show changes inline off, Raw paints no mark either (paintChanges), so the title promises the place and not
          // a mark — the guide's "opens the Raw view at the change" — and the click cues the row it lands on (landOn), which
          // is what reaches a finger; on, Raw shows every change, a deletion as its point
          rv.title = this.inline ? "Show the change in the Raw view" + line
            : "Open the Raw view at the change" + line + "; the marks are off, so the change is not marked there";
          if (c.kind === "del" || !inFlux) acts.appendChild(rv);   // inFlux: an unpainted insertion's Reveal waits for the bytes
        }
      }
      card.appendChild(acts);
    }
    for (const n of [this.loader(slot), this.errRow(slot)]) if (n) card.appendChild(n);
    return card;
  }
  /** Accept all · Reject all, while any change is pending. Reject all rewrites the file, so it asks once,
   *  pane-locally (the folder-off confirm's idiom), naming the count. While the editor is up (Slice 5) both stay as
   *  real buttons that answer in place (DECIDES), and a caption under them says where to decide without a click, the
   *  way a disabled Send says why (renderSend): a tooltip never reaches touch. A click's row (refuseDecision) says the
   *  same sentence under the same buttons, so the caption stands down while that row shows: the words once, as the row
   *  with its ✕ or as the caption, never stacked; the ✕ hands back to the caption. */
  private renderChangesFoot(n: number): HTMLElement {
    const foot = el("div", "fc-foot");
    const row = el("div", "fc-actions");
    const editing = this.ctx.editing();
    const decide = editing ? decideInEditor() : "";
    const busy = this.busy.has("changes"); const verb = this.busyVerb.get("changes");
    const all = btn(busy && verb === "accept-all" ? "Accepting…" : "Accept all", "fcacceptall"); all.disabled = busy;
    all.title = editing ? decide : "Keep the text as it is and drop every change";
    const none = btn(busy && verb === "reject-all" ? "Rejecting…" : "Reject all", "fcrejectall"); none.disabled = busy;
    none.title = editing ? decide : "Put the old text back for every change";
    none.setAttribute("aria-expanded", this.rejectAllConfirm && !editing ? "true" : "false");
    if (editing) { all.classList.add("fileview-btn-blocked"); none.classList.add("fileview-btn-blocked"); }
    row.appendChild(all); row.appendChild(none);
    foot.appendChild(row);
    if (editing && !DECIDE_TEXTS.has(this.errors.get("changes")?.text ?? "")) foot.appendChild(el("div", "fc-note fc-decide-edit", decide));
    if (this.rejectAllConfirm && !editing) {
      const ask = el("div", "fc-row fc-choice");
      ask.appendChild(el("span", "fc-note", "Put the old text back for " + (n === 1 ? "the change" : "all " + n + " changes") + "?"));
      ask.appendChild(btn("Reject all", "fcrejectallgo"));
      ask.appendChild(btn("Cancel", "fcrejectallcancel"));
      foot.appendChild(ask);
    }
    for (const x of [this.loader("changes"), this.errRow("changes")]) if (x) foot.appendChild(x);
    return foot;
  }
  private renderSend(s: Status | null): HTMLElement {
    const box = el("div", "fc-send");
    this.syncNoteRefusal();                            // the bound refusal's row goes with the words it named (Cancel, a send)
    const n = s ? unsentCount(s.unsent) : 0;
    const b = btn(this.sending ? "Sending…" : "Send to session" + (n ? " (" + n + ")" : ""), "fcsend");
    // a status refusal (refresh, requireStatus) leaves the LAST status showing so the cards stay readable, but
    // what is unsent was derived from a disk the kernel can no longer read for us: a file deleted or moved
    // since, a sidecar gone corrupt. A send built from that would go out and be recorded (or re-recorded)
    // against a state that may no longer hold — the duplicate-send leg of the review's finding — so Send
    // stands down until a fresh status lands (applyStatus clears the refusal; Reload in the head asks).
    const stale = !!this.statusRefusal;
    // with nothing unsent the button still opens the confirm: a note of the person's own is a message by itself (the
    // owner's ruling, 2026-09-09), and the confirm's Send stays off until one is typed
    b.disabled = !s || this.sending || !this.ctx.sid || stale;
    b.title = !this.ctx.sid ? "No session owns this file; open it from a session's link or todo to send"
      : stale ? "The comments could not be re-read; Reload above, then send"
      : !n ? "Nothing unsent: every comment, reply, and decision has gone; a note of your own still goes" : "Hand everything unsent to the session as one message";
    box.appendChild(b);
    // why Send is off, VISIBLE (the GitHub link's caption idiom): a tooltip never reaches touch, and a
    // disabled button takes no focus. Nothing-unsent is captioned only once there are comments to have sent, and not
    // while the confirm is up: its own first line says the same thing, and the same words are shown once, never stacked
    // (renderChangesFoot's rule; the review, 2026-09-09). Send stays ON with nothing unsent (the note), so the caption says
    // a note still goes, as the button's title does: the title alone said it, and a title never reaches touch (the review's
    // consolidation, 2026-09-09).
    if (!this.ctx.sid) box.appendChild(el("div", "fc-note", "No session owns this file; open it from a session's link or todo to send."));
    else if (stale && s && n) box.appendChild(el("div", "fc-note", "The comments could not be re-read, so nothing can be sent until Reload above succeeds."));
    else if (s && !n && !this.sending && !this.sendConfirm && this.cards().length) box.appendChild(el("div", "fc-note", "Nothing unsent: every comment, reply, and decision has gone; a note of your own still goes."));
    // the box closed with nothing kept — Cancel, or a send that took the words — starts the next confirm at its three rows:
    // the inline height autosizeNote wrote, or a drag did, goes with the words on the render that follows the clear, the way
    // closeComposer clears the composer's; a refused send keeps the words and the height with them (the confirm stands
    // through it: sendConfirm stays true while the send is out and after the refusal). The review, 2026-09-09: an empty
    // box reopened at the eight rows the last note had grown it to.
    if (!this.sendConfirm && !this.sendNote && (this.noteBox.style.height || this.noteSizedTo !== null)) { this.noteBox.style.height = ""; this.noteSizedTo = null; }
    // the seen set this render's confirm shows, the send's own (pendingSplit reads it; the fields' comment): fresh at every
    // render of the confirm, rewritten in place with the option after a gesture (syncAcceptOption), none with no confirm up
    this.confirmSeen = this.sendConfirm && s && !this.sending ? new Set(this.seenKeys || []) : null;
    if (this.sendConfirm && s && !this.sending) {
      const parts = sendParts(s);
      // the changes the checkbox may accept on the way: the SEEN pending changes (decision 41; pendingSplit), none while
      // the editor is up (doSend counts the same way) — the changes are the editor's then, and a decision from here would
      // strand its buffer (DECIDES); so no box, no count
      const split = this.pendingSplit(s);
      // the same A and R the send will carry (doSend): the log's unsent decisions plus the seen pending changes the
      // checkbox accepts on the way — so the list shows the sent text (countsRow writes the row, here and in place)
      const counts = sendCounts(parts, this.sendOpts.accept, split.seen.length);
      const cf = el("div", "fc-confirm");
      const who = this.sessionName();
      cf.appendChild(el("div", "fc-note", (n ? "This goes to " : "Nothing is unsent; a note goes to ") + who + ":"));
      const ul = el("ul", "fc-list");
      for (const c of parts.comments) {
        const li = el("li");
        li.appendChild(el("span", "fc-list-desc", c.desc + ": "));
        li.appendChild(el("span", undefined, c.body.replace(/\s+/g, " ").trim()));
        ul.appendChild(li);
      }
      this.countsRow(ul, counts);
      cf.appendChild(ul);
      const opts = el("div", "fc-opts");
      this.todoOpts(opts, s);                          // answer a todo: the checkbox, or the radio group when several name this file
      if (!s.trackedBy) opts.appendChild(this.opt("track", "turn on tracking so the session's edits come back as changes"));
      // the accept option names the seen pending changes it accepts and the unseen ones it leaves (decision 41, 2026-09-09:
      // the user's Send had accepted eleven they had not seen; the arrivals follow-on named them, this leaves them pending).
      // Its words and its state — unchecked and disabled with nothing seen — are syncAcceptOption's, the same the in-place
      // update after a gesture writes (reflectSeen), so a change seen while the confirm is up moves to the seen side either way
      if (split.seen.length + split.unseen.length) opts.appendChild(this.acceptOption(s));
      if (opts.childNodes.length) cf.appendChild(opts);
      // the note box (the fields' comment): the person's own words, the first paragraph of the message after its header;
      // the placeholder names the session, or asks plainly when the panel cannot name one
      this.noteBox.placeholder = who === "the session" ? "Anything to add?" : "Anything to add for " + who + "?";
      if (this.noteBox.value !== this.sendNote) this.noteBox.value = this.sendNote;
      cf.appendChild(this.noteBox);
      const acts = el("div", "fc-actions");
      acts.appendChild(btn("Send", "fcsendgo", "fileview-btn fc-primary"));
      this.syncSendGo(acts.querySelector('[data-act="fcsendgo"]') as HTMLButtonElement);   // off with nothing unsent and no note: nothing to send
      acts.appendChild(btn("Cancel", "fcsendcancel"));
      cf.appendChild(acts);
      box.appendChild(cf);
    }
    const saved = this.savedLine();                    // the card a save landed in, out of view: which side it is on (decision 43), in the acknowledgment's position — the margin layout's; the list layout's stands under the header (renderHead, savedLineHead)
    if (saved) box.appendChild(saved);
    // the Reopen all offer (decision 46) stands in the acknowledgment's position, in its dress, until the next gesture; the
    // sent acknowledgment it stands in for comes back when it ends (reflectLines, or this render)
    if (this.reopenAll !== null) box.appendChild(this.reopenLine(this.reopenAll.length));
    else if (this.sentNote) box.appendChild(el("div", "fc-note fc-sent", this.sentNote));
    for (const x of [this.loader("send"), this.errRow("send")]) if (x) box.appendChild(x);
    return box;
  }
  /** The Reopen all offer's line (decision 46; renderSend): the acknowledgment's words ("Resolved N comments") and the offer
   *  as a text button beside them, in the sent acknowledgment's dress — .fc-note and .fc-sent on the row, as on the
   *  acknowledgment, so the Send section's tiers count it as the acknowledgment and not as growth (the sheets'
   *  `:not(.fc-note)`), and its size on the words and the button alone: the row's own is set back to the section's, since a
   *  .fc-note inside a .fc-note compounds (ui/CLAUDE.md, font sizes; the review, 2026-09-10: the offer rendered at 0.74 of the
   *  acknowledgment beside it). The button wears no class of the saved line's (.fc-saved is that line's own dress, one in the
   *  panel: feed-css-saved-line-head-dress.test.ts), and the sheets have no rule for it, so its text-button shape is inline,
   *  the todo option's idiom; .fc-link gives it the panel's link hover. In the margin layout the Send section scrolls inside
   *  itself while its confirm is up, and a line after the confirm stood past the section's box (the saved line's case,
   *  savedButton, measured 2026-09-09; the offer's, 2026-09-10): it sticks to the section's bottom edge there, as that line
   *  does. The list layout's Send section is the scroller's foot, below every card; the offer stands there all the same
   *  (the plan: the acknowledgment's position). */
  private reopenLine(n: number): HTMLElement {
    const line = el("div", "fc-note fc-sent fc-reopen");
    line.style.fontSize = "inherit";                   // the class is the tier's and the colour's; the size is the children's
    line.appendChild(el("span", "fc-note fc-sent", resolvedWords(n)));
    const b = btn("Reopen all", "fcreopenall", "fc-note fc-sent fc-link");
    b.title = "Reopen the " + (n === 1 ? "comment" : n + " comments") + " just resolved";
    b.style.background = "none"; b.style.border = "0"; b.style.padding = "0"; b.style.marginLeft = "6px";   // beside the words, a word's gap
    b.style.fontFamily = "inherit"; b.style.fontWeight = "inherit"; b.style.lineHeight = "inherit";
    line.appendChild(b);
    if (this.margin) { line.style.position = "sticky"; line.style.bottom = "0"; line.style.background = "var(--bg)"; }
    return line;
  }
  /** The line for the card a save landed in out of view (savedOut; decision 43): "Saved · the card is above" or "below"
   *  (savedWhereWords), a button whose click scrolls the card into view as the focus (fcsavedgo: scrollCard). Rendered
   *  from the latched side (the field's comment says why not from the geometry here) and followed in place between
   *  renders (reflectLines); over — and the key with it — once the card is whole in view or gone from the list, and at
   *  the person's next gesture (gesture). In the acknowledgment's dress and .fc-note as the acknowledgment is, so the Send section
   *  does not count it as growth (the sheets' tiers), as a text button (.fc-saved). This is the margin layout's, in the Send
   *  section pinned at the panel's foot (renderSend); the list layout's stands under the header (savedLineHead, renderHead
   *  says why) — one button either way (savedButton), one in the panel at a time. */
  private savedLine(): HTMLElement | null {
    return this.margin ? this.savedButton() : null;
  }
  /** The list layout's saved line, under the header (renderHead): the Send section is the scroller's foot there, below the
   *  very card the line says is below, so a line in it was never on screen when it was needed (the review, 2026-09-09). */
  private savedLineHead(): HTMLElement | null {
    return this.margin ? null : this.savedButton();
  }
  /** The line's button (savedLine, savedLineHead): the latched side's words, in the acknowledgment's dress. */
  private savedButton(): HTMLElement | null {
    if (!this.savedOut) return null;
    const b = btn(savedWhereWords(this.savedOut.side), "fcsavedgo", "fc-note fc-sent fc-saved");
    b.title = "Show the card";
    b.dataset.id = this.savedOut.key;                  // the card it points at: where the keyboard goes when the line leaves under it (removeLine)
    // the margin layout's Send section scrolls inside itself while the confirm is up (the sheets' grown tier), and the line,
    // after the confirm in it, stood past the section's box — with the confirm up at a 500px viewer the line was never on
    // screen, and every way to scroll it in, a wheel or a scrollbar press, is a gesture that ends it (the review, 2026-09-09;
    // measured in Chromium and Firefox). So it sticks to the section's bottom edge over the rows that scroll, the way the
    // arrivals line sticks to the head's (the sheets' .fc-arrivals rule), and stands in its own place once the section is
    // scrolled to it; the sheet's `background: none` on .fc-saved would show the confirm through it. Inline, the todo
    // option's idiom: the sheets have no rule for the line's place.
    if (this.margin) { b.style.position = "sticky"; b.style.bottom = "0"; b.style.background = "var(--bg)"; }
    return b;
  }
  /** The confirm's Send: off with nothing unsent and no note (as the kernel reads it, trimNote: words its strip would take to
   *  nothing are none), on as soon as either stands. `go` is the button renderSend just
   *  built; without it, the one in the panel, followed in place as the person types (the box's input): a render would rebuild
   *  the confirm around the box. */
  private syncSendGo(go?: HTMLButtonElement): void {
    const b = go || (this.root?.querySelector('[data-act="fcsendgo"]') as HTMLButtonElement | null);
    if (!b) return;
    const n = this.status ? unsentCount(this.status.unsent) : 0;
    b.disabled = !n && !trimNote(this.sendNote);
    b.title = b.disabled ? "Nothing is unsent; type a note to send one" : "Send";
  }
  /** The bound refusal's row (doSend: a note over SEND_NOTE_MAX is refused before any request, in the send slot) is about the
   *  words in the box and lives with them: it stands while the note is over the bound (the count it names may lag the typing;
   *  the next Send names it afresh), and goes once the note is not — shortened under the bound, or gone with Cancel or a send —
   *  where it stood under the Send button after Cancel and under an EMPTY box on the next confirm until its ✕ (the review,
   *  2026-09-09). The row is known by its words, the bound text for the note in the box when it was rendered (noteRefusal); a
   *  kernel's refusal in the same slot is not it and stands as before. `inPlace`: from the box's input, where a render would
   *  rebuild the confirm around the box (syncSendGo), the row's own node is removed. */
  private syncNoteRefusal(inPlace = false): void {
    const row = this.errors.get("send") || null, over = noteTooLong(this.sendNote);
    if (row && over && row.text === over) { this.noteRefusal = row; return; }
    if (!this.noteRefusal || over) return;
    if (row === this.noteRefusal) {
      this.errors.delete("send");
      if (inPlace) (this.root?.querySelector('.fc-err[data-slot="send"]') as HTMLElement | null)?.remove();
    }
    this.noteRefusal = null;
  }
  private opt(key: "todo" | "track" | "accept", label: string): HTMLElement {
    const l = el("label", "fc-opt");
    const cb = el("input") as HTMLInputElement;
    cb.type = "checkbox"; cb.checked = this.sendOpts[key]; cb.dataset.opt = key;
    l.appendChild(cb); l.appendChild(el("span", undefined, label));
    return l;
  }
  /** The pending changes a send may accept, split into the ones the person has seen and the ones they have not (decision
   *  41; partitionPending over the seen set): none of either while the editor is up, whose marks they are (DECIDES). Over
   *  the seen set AS THE CONFIRM SHOWS IT while one is up (confirmSeen, written with the option and the count row), so the
   *  accept the send carries is the one they named when the person pressed Send (the fields' comment has the case a live
   *  read got wrong); over the live set otherwise. */
  private pendingSplit(s: Status): { seen: Hunk[]; unseen: Hunk[] } {
    if (this.ctx.editing()) return { seen: [], unseen: [] };
    return partitionPending(s.hunks || [], this.confirmSeen || this.seenKeys);
  }
  /** The confirm's accept option: the box and its words (acceptOptionLabel), in the state syncAcceptOption gives them. */
  private acceptOption(s: Status): HTMLElement {
    const l = this.opt("accept", "");
    this.syncAcceptOption(l.querySelector("input") as HTMLInputElement, s);
    return l;
  }
  /** The accept option's words and state from the seen split (decision 41): "accept the N pending changes you have seen",
   *  the unseen count after it; with
   *  nothing seen the box is unchecked and disabled, since there is nothing it may accept — the person's own choice
   *  (sendOpts.accept, decision 8's default) is kept for when a look brings a change to the seen side. Called by the render
   *  (acceptOption) and in place after a gesture marked arrivals seen (reflectSeen), so both write the same thing — the
   *  confirm's count row with it (countsRow), and the seen set they were written from (confirmSeen: what the send accepts).
   *  Not for the send's own press (sendPress): the option stays as the person read it, and the send takes that. */
  private syncAcceptOption(cb: HTMLInputElement, s: Status): void {
    if (this.sendPress) return;
    this.confirmSeen = new Set(this.seenKeys || []);
    const split = this.pendingSplit(s);
    const label = cb.parentElement ? cb.parentElement.querySelector("span") : null;
    if (label) label.textContent = acceptOptionLabel(split.seen.length, split.unseen.length);
    cb.disabled = split.seen.length === 0;
    cb.checked = split.seen.length > 0 && this.sendOpts.accept;
    const ul = cb.closest(".fc-confirm")?.querySelector(".fc-list") as HTMLElement | null;   // in place: the confirm's list (the render writes the row itself, before the option is in the confirm)
    if (ul) this.countsRow(ul, sendCounts(sendParts(s), this.sendOpts.accept, split.seen.length));
  }
  /** The confirm's count row, "A accepted, R rejected" (D5): the log's unsent decisions plus the seen pending changes the
   *  checked box accepts on the way (sendCounts, the caller's), the same A and R the send will carry (doSend), so the list
   *  shows the sent text; no row with nothing to state. Written by the render and rewritten in place with the option after a gesture
   *  (syncAcceptOption): before, a look that brought a change to the seen side changed the option's words and left the row
   *  as rendered, so the confirm read "accept the 3 pending changes you have seen" over "2 accepted, 0 rejected" and
   *  sent three (the review, 2026-09-09). */
  private countsRow(ul: HTMLElement, counts: { accepted: number; rejected: number }): void {
    let li = ul.querySelector("li.fc-counts") as HTMLElement | null;
    if (!counts.accepted && !counts.rejected) { if (li) li.remove(); return; }
    if (!li) { li = el("li", "fc-counts"); ul.appendChild(li); }
    li.textContent = counts.accepted + " accepted, " + counts.rejected + " rejected";
  }
  /** The confirm's answer-a-todo control (the todo-file follow-on, 2026-09-07). The candidates are todoChoices': the todo
   *  the file was opened from and every open todo of the session that names this file (the status's `todos`), minus those
   *  a send from this page has answered. ONE candidate: the checkbox, checked by default (decision 8), labelled with the
   *  todo's own text when the kernel listed it (decision 36's generic wording otherwise, since the viewer never receives the
   *  opened-from todo's words). SEVERAL: one radio group — Answer: the first selected, the others, then none — so one send
   *  answers one todo (decision 28). NONE: no control. The label is one line: cut to a line's worth, the whole text on hover
   *  (an inline clip; the sheets have no rule for this control, the Slice 2 idiom) — and one click away, in full: a row
   *  whose todo has words carries a fold (fctodotext, keyed by todo id in openTodoText so a re-render keeps it open) that
   *  shows the whole text under the row, wrapped. The hover never reaches touch, and at the aside's width two todos that
   *  begin alike clip to the same words, so the label alone could not say which todo the send would stamp (the 2026-09-07
   *  review; ui/CLAUDE.md: never dead-end a compact view). */
  private todoOpts(opts: HTMLElement, s: Status): void {
    const cands = this.todoCandidates(s);
    if (!cands.length) return;
    // opt()'s row with the label clipped to ONE line (the text is already cut to a line's worth by todoChoiceLabel; the
    // clip is inline since the sheets have no rule for this control, the Slice 2 idiom) and the whole text on hover. With
    // words to show (title), the label shares its line with the fold's glyph (the Log rows' and the preview's ▸/▾, in
    // the preview's dress) and the whole text stands under the line while the fold is open: the input's value is the
    // todo's id (a radio's by construction; the checkbox's is set for this), which keys the fold. A label without words
    // (none; the opened-from todo the status never listed) has nothing underneath, so it is the row.
    const optRow = (input: HTMLInputElement, text: string, title: string | null): HTMLElement => {
      const l = el("label", "fc-opt");
      const t = el("span", undefined, text);
      t.style.minWidth = "0"; t.style.overflow = "hidden"; t.style.textOverflow = "ellipsis"; t.style.whiteSpace = "nowrap";
      if (title) l.title = title;
      l.appendChild(input); l.appendChild(t);
      if (!title) return l;
      const id = input.value;
      const open = this.openTodoText.has(id);
      const row = el("div", "fc-todo-opt");
      row.style.display = "flex"; row.style.flexDirection = "column"; row.style.gap = "3px"; row.style.minWidth = "0";
      const line = el("div");
      line.style.display = "flex"; line.style.alignItems = "center"; line.style.gap = "6px"; line.style.minWidth = "0";
      l.style.flex = "0 1 auto"; l.style.minWidth = "0";   // the label shrinks (its span clips) so the glyph stays on the line
      const fold = btn(open ? "▾" : "▸", "fctodotext", "fc-sec");
      fold.dataset.id = id;
      fold.style.flex = "0 0 auto"; fold.style.padding = "2px 6px";   // a wider target than the glyph alone (a finger)
      fold.title = open ? "Hide the whole todo" : "Show the whole todo";
      fold.setAttribute("aria-label", fold.title); fold.setAttribute("aria-expanded", open ? "true" : "false");
      line.appendChild(l); line.appendChild(fold);
      row.appendChild(line);
      if (open) {
        row.appendChild(el("div", "fc-body fc-todo-text", title));   // the card body's dress: the todo's own lines, wrapped
      }
      return row;
    };
    if (cands.length === 1) {
      const c = cands[0];
      const cb = el("input") as HTMLInputElement;
      cb.value = c.id;   // the todo the box answers: keys its fold (optRow)
      cb.type = "checkbox"; cb.checked = this.sendOpts.todo; cb.dataset.opt = "todo";
      opts.appendChild(optRow(cb, c.text === null ? "answer " + TODO_OPENED_FROM : "answer the todo: " + todoChoiceLabel(c), c.text));
      return;
    }
    const pick = this.chosenTodoId(s) || "";
    const g = el("div", "fc-opts fc-todo-pick");
    g.setAttribute("role", "radiogroup"); g.setAttribute("aria-label", "Answer a todo with this send");
    g.appendChild(el("span", "fc-note", "Answer:"));
    for (const c of [...cands.map((x) => ({ id: x.id, label: todoChoiceLabel(x), title: x.text })), { id: "", label: "none", title: null }]) {
      const r = el("input") as HTMLInputElement;
      r.type = "radio"; r.name = "fc-todo"; r.value = c.id; r.checked = c.id === pick; r.dataset.opt = "todopick";
      g.appendChild(optRow(r, c.label, c.title));
    }
    opts.appendChild(g);
  }
  private todoCandidates(s: Status): TodoChoice[] { return todoChoices(this.ctx.todoId, s, (id) => answeredTodos.has(id)); }
  /** The todo the next send answers, or null: for one candidate the checkbox's verdict; for several the radio's — the pick
   *  while it is still offered, none when none was picked, else the first (nothing picked yet, or the pick left the list).
   *  The two verdicts agree on none (the change handler writes a decline to both), so a count that changed between the
   *  choice and the send — the box unchecked, then a second todo listed; none picked, then one todo left — still answers
   *  nothing; a pick that left the list falls to the first offered, as a fresh confirm would. */
  chosenTodoId(s: Status): string | null {
    const cands = this.todoCandidates(s);
    if (!cands.length) return null;
    if (cands.length === 1) return this.sendOpts.todo ? cands[0].id : null;
    if (this.todoPick === "") return null;
    if (this.todoPick && cands.some((c) => c.id === this.todoPick)) return this.todoPick;
    return cands[0].id;
  }
  private renderLog(s: Status | null): HTMLElement {
    const box = el("div", "fc-log");
    const rows = s?.log || [];
    box.appendChild(btn((this.logOpen ? "▾ " : "▸ ") + "Log" + (rows.length ? " (" + rows.length + (s?.logTruncated ? "+" : "") + ")" : ""), "fclog", "fc-sec"));
    if (!this.logOpen) return box;
    if (!rows.length) { box.appendChild(el("div", "fc-empty", "Nothing yet: sends, decisions, tracking changes, and direct edits land here.")); return box; }
    const nameOf = (sid: string): string | null => {
      if (this.ctx.sid && bareId(this.ctx.sid) === sid) return this.sessionName();
      const c = this.colors ? this.colors.get(sid) : null;
      return c ? c.name : null;
    };
    // one row per entry is the glance; what the entry holds underneath — the bodies a send carried, the diff of
    // a direct edit — is one click down, keyed so a poll re-render keeps it open (ui/CLAUDE.md: never dead-end)
    for (const e of [...rows].reverse()) {
      const key = String(e.ts) + "|" + String(e.kind);
      const detail = this.logDetail(e);
      const isOpen = !!detail && this.openLog.has(key);
      const row = el("div", "fc-log-row");
      row.appendChild(el("span", "fc-time", clock(e.ts)));
      row.appendChild(el("span", undefined, logRowText(e, nameOf)));
      if (detail) {
        // the row becomes a control; the fold glyph joins its text span, so the row stays time + text (the
        // sheets size it as exactly that) and a re-render keeps it open through openLog
        row.classList.toggle("open", isOpen);
        row.dataset.act = "fclogrow"; row.dataset.key = key;
        row.setAttribute("role", "button"); row.style.cursor = "pointer";
        row.tabIndex = 0; row.setAttribute("aria-expanded", isOpen ? "true" : "false");   // a Tab stop; Enter/Space through KEY_ACTS
        row.title = isOpen ? "Hide" : e.kind === "send" ? "Show what was sent" : e.kind === "edit" ? "Show the edit" : "Show the changes";
        (row.childNodes[1] as HTMLElement).textContent = (isOpen ? "▾ " : "▸ ") + logRowText(e, nameOf);
      }
      box.appendChild(row);
      if (detail && isOpen) box.appendChild(detail);
    }
    if (s?.logTruncated) box.appendChild(el("div", "fc-note", "Showing the last " + rows.length + " entries."));
    return box;
  }
  /** What a Log row has underneath, or null when the line IS the whole entry (a tracking toggle). A send
   *  entry holds the comments as they went — each with what it referred to, in the confirm's own list dress;
   *  an edit entry holds the kernel's diff of the direct edit; an accept or reject entry holds the changes it
   *  decided, old and new text, which the sidecar has since forgotten. */
  private logDetail(e: { kind: string; [k: string]: unknown }): HTMLElement | null {
    if ((e.kind === "accept" || e.kind === "reject") && Array.isArray(e.changes) && e.changes.length) {
      const box = el("div", "fc-log-detail");
      const ul = el("ul", "fc-list");
      for (const ch of e.changes as Array<Record<string, unknown>>) {
        if (!ch || typeof ch !== "object") continue;
        const li = el("li");
        const oldText = typeof ch.oldText === "string" ? ch.oldText : "", newText = typeof ch.newText === "string" ? ch.newText : "";
        li.appendChild(this.diffBody(oldText, newText));
        ul.appendChild(li);
      }
      box.appendChild(ul);
      return box;
    }
    const noted = e.kind === "send" && typeof e.note === "string" && e.note !== "";
    if (e.kind === "send" && ((Array.isArray(e.comments) && e.comments.length) || noted)) {
      const box = el("div", "fc-log-detail");
      if (noted) box.appendChild(el("div", "fc-body fc-log-note", e.note as string));   // the person's own words, as the message carried them first
      const ul = el("ul", "fc-list");
      for (const c of (Array.isArray(e.comments) ? e.comments : []) as Array<Record<string, unknown>>) {
        if (!c || typeof c !== "object") continue;
        const li = el("li");
        li.appendChild(el("span", "fc-list-desc", String(c.desc ?? "on this file") + ": "));
        li.appendChild(el("span", undefined, String(c.body ?? "")));
        ul.appendChild(li);
      }
      if (ul.childNodes.length) box.appendChild(ul);
      return box;
    }
    if (e.kind === "edit") {
      const f = (e.summary && typeof e.summary === "object" ? e.summary : e) as Record<string, unknown>;
      if (typeof f.diff !== "string" || !f.diff) return null;
      const box = el("div", "fc-log-detail");
      box.appendChild(el("pre", "fc-msg", f.diff));
      if (f.truncated === true) box.appendChild(el("div", "fc-note", "The diff was cut short; the file holds the rest."));
      return box;
    }
    return null;
  }
}

// ── the registry entry ─────────────────────────────────────────────────────────────────────────────
// Mounted hidden; the first `status` answer reveals it with the glance label (a `no-node` refusal never
// does — the gear's File comments row names the machine and the reason). Registered by file-view.ts.
export const fileCommentsAction: FileViewAction = {
  id: "file-comments",
  mount(ctx) {
    const unit = el("span", "fileview-fc");
    unit.hidden = true;
    const b = el("button", "fileview-btn", "Comments") as HTMLButtonElement;
    b.type = "button";
    b.setAttribute("aria-pressed", "false");
    unit.appendChild(b);
    new Panel(ctx, b, unit).probe();
    return unit;
  },
};
