// Comment threads (the user 2026-08-13): highlight a passage in the chat, comment on it, and a side
// conversation opens right there — an anchored highlight + popover, powered kernel-side by a fork of
// the session cut at the anchored message. This module is the PURE half (node-testable, no DOM):
// thread types, the whitespace-tolerant exact-text matcher that re-finds a highlight inside a
// re-rendered turn, and the small derivations the popover renders from. All DOM wiring lives in
// render.ts (source-pinned by comments.test.ts, the repo convention).
import type { PickHeld } from "./pick-held";
import { hostOf } from "./host-prefix";

export type CommentMsg = { who: "you" | "agent"; text: string; t: number };

export type CommentThread = {
  /** the thread's mail is off (T356): a comment thread neither sends nor receives peer mail until broken out */
  mailOff?: boolean;
  /** why, when it is off: "thread" (not yet broken out), "isolation" (the lane's mailbox toggle), "unreadable" (its record cannot be read) */
  mailOffWhy?: string;
  /** messages waiting in its postal box (they land when it is broken out) */
  heldMail?: number;
  tid: string;
  name?: string;              // the thread's editable name (<session>-comment-<N> by default)
  color?: string;             // the comment's identity color — picked distinct from its parent's
  anchorUuid: string;
  exact: string;
  status: "open" | "resolved" | "promoting" | "promoted" | "merging" | "merged";   // merging/merged: folded back into the parent (the user 2026-08-23)
  createdT: number;
  state: string;              // the thread session's live state ("working"/"waiting"/…, "" when dormant)
  error?: string;             // the thread CLI's launch error, when it could not start
  unread: boolean;            // a FINISHED agent reply newer than the read watermark — yellow (kernel truth, T237)
  replyOwed?: boolean;        // a reply is still owed (no exchange yet / user's message newest / turn in progress / a send held) — the green wash (kernel truth, T237; absent on an older kernel)
  queued?: number;            // sends the backend holds or has fed for this thread, not yet in the transcript (T237)
  lastUuid?: string;          // the newest record shown/held — "did the transcript move?" without the projection caps (T237)
  unreachable?: boolean | null;   // a broken thread (missing transcript / lost cut): the kernel owes nothing and says so (T237)
  sinceEpoch?: number;        // ms epoch the thread's current state began — the popover chip's timer
  mode?: string;              // the thread's permission mode — the popover statusline's Auto badge
  fast?: string;              // fast-mode state ("on"/"off"/"cooldown"; "" = unknown → no badge)
  modelColor?: number[];      // the chat statusline's rank tints, so metaColor paints the popover
  effortColor?: number[];     //   badges exactly as the chat's (the 2026-08-25 color rider)
  promotedName: string;       // the board session it became, when status === "promoted"
  relayedT?: number;          // when the discussion was last sent back to the session (T145) — 0/absent = never
  model?: string;             // the thread's live/chosen model (the popover's switchable chip)
  effort?: string;            // the thread's effort level (ditto): the value the thread RUNS while a pick is held
  effortPending?: boolean;    // an effort reload is pending on the thread (the popover's effort badge shows the loader dots, as the chat's does)
  fastPending?: boolean;      // a fast pick's reload is pending on the thread (the badge's dim pulse; review round 7, 2026-09-10)
  modePending?: boolean;      // a mode pick's reload, or the landing's live switch, is pending on the thread (ditto)
  pickHeld?: PickHeld | null; // a settings pick held for the thread's live work (the badges' held mark and tip, the menus' marks; review round 6, 2026-09-10)
  msgs: CommentMsg[];
  events?: unknown[];         // the CHAT's own ChatEvents from the branch point on (render parity)
};

export type CommentsFrame = { type: "comments"; id: string; threads: CommentThread[] };

/** Threads grouped by the turn they anchor to — what the mark/badge pass walks per rendered view. */
export function threadsByAnchor(threads: CommentThread[]): Map<string, CommentThread[]> {
  const by = new Map<string, CommentThread[]>();
  for (const th of threads) {
    const list = by.get(th.anchorUuid);
    if (list) list.push(th); else by.set(th.anchorUuid, [th]);
  }
  return by;
}

/** Which thread a click on a comment mark opens, given the mark CHAIN under the pointer — the clicked
 *  mark first, then each enclosing mark outward. Marks nest when two threads anchor to the same passage
 *  (the user 2026-09-10, who commented on one selection twice within seconds): ensureCommentMark re-finds
 *  the identical range for the second thread and wraps its <mark> inside the first's, and the store's
 *  order makes the EARLIER thread the outer one. The delegate hands the click to the innermost mark, so
 *  the outer thread's needs-you ring could never be opened from its own ring: its unread never cleared
 *  and the reply-ready chip stayed lit. The rule: the innermost UNREAD mark when any is (the ring under
 *  the pointer belongs to it; two rings, the newest is the one under the finger), else the innermost,
 *  as before. Null for an empty chain. */
export function pickMarkToOpen(chain: { tid: string; unread: boolean }[]): string | null {
  if (!chain.length) return null;
  const ring = chain.find((m) => m.unread);
  return (ring || chain[0]).tid;
}

/** The thread session is mid-turn — the popover shows its thinking dots. */
export function threadBusy(state: string): boolean {
  return state === "working" || state === "retrying" || state === "compacting";
}

/** The thread session is stuck on an interactive prompt the popover can't answer — say so, and point
 *  at Break out (a full session can). */
// A reply is OWED the moment the user's message is the thread's newest with no agent reply landed
// since (the user 2026-08-24, second report: the mark flashed green on create, dropped to YELLOW
// while the thread CLI was still booting — its live state read idle, a flapping boot-time proxy —
// then went green again once generation started). The in-flight color keys on the EXCHANGE's own
// events: user message in → green until the reply message lands, however the worker session's state
// wobbles on the way. The find-the-event rule, applied to a color.
export function replyOwed(th: CommentThread): boolean {
  const last = th.msgs.length ? th.msgs[th.msgs.length - 1] : null;
  return !!last && last.who === "you";
}
// THE EXCHANGE LATCH (T102, the user 2026-08-26 — replacing the push-count settle): the busy pulse
// is exchange-scoped. It LATCHES at the user's SEND gesture (client-side, optimistic — before any
// kernel round-trip; thread-open must never be the start trigger) and CLEARS only on the
// REPLY-ARRIVED event for that send: the agent's reply RECORD landing in the thread's projected
// msgs — concretely, th.msgs holding MORE who==="agent" entries than it held at the send. Counts of
// the exchange's own records: never wall clocks (cross-host transcripts skew) and never push counts
// (the banned proxy — the old two-quiet-pushes settle counter killed the create-window green
// while the fork booted, and any stall in its 0→1→2 stepping parked green forever with no event to
// clear it). agentCount is that reply-arrived detector's datum; render.ts holds the per-send base.
// Since T237 the KERNEL ships replyOwed (read from the thread's transcript with the event model's own
// turn-end), and the latch covers only the pre-round-trip instant against such a kernel; the
// agentCount clear stays the contract for an older kernel that ships no bit.
export function agentCount(th: CommentThread): number {
  return (th.msgs || []).filter((m) => m.who === "agent").length;
}
export function threadStuck(state: string): boolean {
  return state === "permission" || state === "picker";
}

// ── exact-text re-anchoring ────────────────────────────────────────────────────────────────────
// A highlight is stored as the selected text (`exact`); every re-render must re-find it inside the
// anchor turn's rendered text. Rendered whitespace is not byte-stable (markdown collapses runs,
// wraps lines), so both sides are matched through a whitespace-NORMALIZED view with an index map
// back into the raw string. First occurrence wins — same-turn duplicate phrases anchor to their
// first appearance, a known and acceptable simplification.

/** Collapse whitespace runs to single spaces; `map[i]` = raw index of normalized char i. */
function normalize(raw: string): { norm: string; map: number[] } {
  let norm = "";
  const map: number[] = [];
  let inWs = false;
  for (let i = 0; i < raw.length; i++) {
    const c = raw[i];
    if (/\s/.test(c)) {
      inWs = true;
      continue;
    }
    if (inWs && norm.length) {
      norm += " ";
      map.push(i);              // the space stands for the run; anchor it at the run's end
    }
    inWs = false;
    norm += c;
    map.push(i);
  }
  return { norm, map };
}

/** Find `exact` inside `hay`, whitespace-tolerantly. Returns raw [start, end) in `hay`, or null. */
export function findExact(hay: string, exact: string): { start: number; end: number } | null {
  const target = normalize(exact).norm;
  if (!target) return null;
  const { norm, map } = normalize(hay);
  const at = norm.indexOf(target);
  if (at < 0) return null;
  return { start: map[at], end: map[at + target.length - 1] + 1 };
}

/** findExact with a LONGEST-PREFIX fallback (the user 2026-08-13, who wanted the comment visible
 *  in context every time): a selection that spanned several messages anchors to its FIRST turn,
 *  whose rendered text holds only the selection's head — the full exact-match fails and the thread
 *  fell back to the tiny badge alone. Binary-search the longest word-prefix that still matches, so
 *  the portion that lives in the anchored turn highlights. A too-short remnant (under 3 words and
 *  under 12 characters) stays null — highlighting a stray "The" would mark the wrong thing. */
export function findAnchorRange(hay: string, exact: string):
    { start: number; end: number; partial: boolean } | null {
  const full = findExact(hay, exact);
  if (full) return { ...full, partial: false };
  const words = exact.trim().split(/\s+/);
  let lo = 1, hi = words.length - 1, best: { start: number; end: number; k: number } | null = null;
  while (lo <= hi) {
    const k = (lo + hi) >> 1;
    const r = findExact(hay, words.slice(0, k).join(" "));
    if (r) { best = { ...r, k }; lo = k + 1; } else hi = k - 1;
  }
  if (!best) return null;
  const matched = words.slice(0, best.k).join(" ");
  if (best.k < 3 && matched.length < 12) return null;
  return { start: best.start, end: best.end, partial: true };
}

/** A text node the mark pass must leave alone (T349, the user 2026-09-11: a comment on a table's row broke the table):
 *  the whitespace text between a table's cells and rows sits directly under TABLE / THEAD / TBODY / TFOOT / TR, and an
 *  inline <mark> placed there gets its own anonymous table cell, so the columns shift. Those nodes carry no visible
 *  text; skipping them lets the mark ride the row cell by cell while the table's boxes stay. `parentTag` is the text
 *  node's parent element's tagName (upper-case in an HTML document). */
export function markSkipsParent(parentTag: string | null | undefined): boolean {
  return /^(TABLE|THEAD|TBODY|TFOOT|TR)$/.test(parentTag || "");
}

/** Split a global [start, end) character range over consecutive text-node lengths into per-node
 *  slices — what the DOM pass wraps in <mark> elements. */
export function sliceRanges(nodeLens: number[], start: number, end: number):
    { idx: number; s: number; e: number }[] {
  const out: { idx: number; s: number; e: number }[] = [];
  let off = 0;
  for (let i = 0; i < nodeLens.length && off < end; i++) {
    const len = nodeLens[i];
    const s = Math.max(start, off);
    const e = Math.min(end, off + len);
    if (e > s) out.push({ idx: i, s: s - off, e: e - off });
    off += len;
  }
  return out;
}

/** Optimistic pending sends, reconciled against the kernel's frame (the registerOptimistic pattern):
 *  each landed 'you' message spends AT MOST ONE pending row with its text — a count-based match, so
 *  sending the same words twice keeps the second bubble until its own message lands. Returns the
 *  still-pending remainder to render after the server messages. */
export function prunePending(pending: { text: string; t: number }[], msgs: CommentMsg[]):
    { text: string; t: number }[] {
  const counts = new Map<string, number>();
  for (const m of msgs) {
    if (m.who !== "you") continue;
    const k = normalize(m.text).norm;
    counts.set(k, (counts.get(k) || 0) + 1);
  }
  return pending.filter((p) => {
    const k = normalize(p.text).norm;
    const c = counts.get(k) || 0;
    if (c > 0) {
      counts.set(k, c - 1);
      return false;
    }
    return true;
  });
}

/** A comment create as the client holds it from the send gesture until the kernel answers it: the
 *  anchor, the words, the dialog's picks, the gesture's own id and how many times a transient refusal
 *  has had it re-posted. The kernel answers a repeat of a create it completed with the same thread's
 *  ack (a lost ack, a lag-parked copy that landed before the client's re-post reached it), and it tells
 *  a repeat from a fresh comment by this id: two gestures in the same words on the same passage are
 *  two comments, and a memo keyed on the words alone answered the second with the first thread and
 *  wrote its name nowhere (review, 2026-09-09). */
export type CommentCreate = { sid: string; uuid: string; exact: string; text: string; name: string;
  model: string; effort: string; fast: string; color: string; createId: string; tries: number };

/** One id per send gesture: the moment and a random tail, in the same shape as a provisional tab's id.
 *  Random, not a counter: a reloaded viewer starts its counters over, and the kernel's memo outlives it. */
export function mintCreateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2);
}

/** The create a send gesture holds: stamped with a fresh id, picks defaulted to "" (the kernel's
 *  default-comment settings, then the parent's), the retry count at zero. */
export function newCommentCreate(anchor: { sid: string; uuid: string; exact: string; model?: string; effort?: string;
                                           fast?: string; color?: string },
                                 text: string, name: string): CommentCreate {
  return { sid: anchor.sid, uuid: anchor.uuid, exact: anchor.exact, text, name, model: anchor.model || "",
           effort: anchor.effort || "", fast: anchor.fast || "", color: anchor.color || "",
           createId: mintCreateId(), tries: 0 };
}

/** A create dialog's draft keys in echo mode: the PASSAGE's, not the message's. Keyed by the message, one passage's
 *  unsent or refused words opened in a comment on another passage of it. The uuid comes first and holds no newline.
 *  A main-mode dialog keeps main's keys, the message's ("new:" and "newname:" + its uuid), which hold no newline. */
export const createDraftKey = (a: { uuid: string; exact: string }): string => "new:" + a.uuid + "\n" + a.exact;
export const createNameKey = (a: { uuid: string; exact: string }): string => "newname:" + a.uuid + "\n" + a.exact;

/** An echo-mode dialog opening on a passage whose own draft is empty, words and typed name both, takes main's draft of
 *  the message ("new:" + uuid, "newname:" + uuid) and moves it, the words and the typed name together, so words typed
 *  while the host was in main mode are not lost when it reaches echo mode. A passage with words or a typed name of its
 *  own takes nothing, and main's draft waits whole in the dialog's note (render.ts paintHeldNotes): a comment's typed
 *  name travels with its words, so one never rides another comment's words. The other direction is no move: a
 *  main-mode dialog shows the passage's echo-mode draft in its note, and only the person's Bring it back puts it in
 *  main's keys, since main's handling deletes and prunes main's keys as main does. Returns what it moved (null when it
 *  moved nothing), which render.ts records when main's retry gave up on the message's comment (noteMainBrought). */
export function carryMainDraft(drafts: Map<string, string>, a: { uuid: string; exact: string }): { text: string; name: string } | null {
  const own = [createDraftKey(a), createNameKey(a)], main = ["new:" + a.uuid, "newname:" + a.uuid];
  if (own.some((k) => drafts.get(k)) || !main.some((k) => drafts.get(k))) return null;
  const carried = { text: drafts.get(main[0]) || "", name: drafts.get(main[1]) || "" };
  for (let i = 0; i < 2; i++) {
    const moved = drafts.get(main[i]);
    if (moved) drafts.set(own[i], moved);
    drafts.delete(main[i]);
  }
  return carried;
}

/** The kernel's comments frame sends each thread's passage cut to its first 500 characters (kernel.py, the frame's
 *  `"exact": str(th.get("exact") or "")[:500]`), so an echo-mode synthetic thread holding the whole selection is
 *  compared with a real one on that same cut, counted in code points as Python counts them. */
export const FRAME_EXACT_CUT = 500;
export const frameExact = (exact: string): string => Array.from(exact).slice(0, FRAME_EXACT_CUT).join("");

/** The capability a kernel announces (its caps frame, in reply to a page's ready; KERNEL_WS_CAPS in kernel.py) when
 *  every commentCreated and commentCreateFailed it sends carries the createId of the create it answers. */
export const CREATE_ID_ECHO_CAP = "commentCreateId";

/** What a caps frame says of a host's create answers: whether its list names the echo. */
export const capsAnnounceEcho = (caps: unknown): boolean => Array.isArray(caps) && caps.includes(CREATE_ID_ECHO_CAP);

/** What a kernel answer (commentCreated, commentCreateFailed) says of its host: a createId key (a string, even "")
 *  comes only from a kernel with the echo, and none only from one without it. null for federation's own answer to a
 *  create it could not deliver (relayDrop), which comes from this page and says nothing of the host's kernel. */
export function answerEchoEvidence(m: { id?: unknown; uuid?: unknown; createId?: unknown; relayDrop?: unknown }): boolean | null {
  return m.relayDrop === true ? null : typeof m.createId === "string";
}

/** A create dialog's mode, taken when it opens: echo mode when its session's host's latest evidence is the echo (its
 *  latest connection's connect push, whose marker render.ts noteConnectPush reads, or the last caps frame or answer that
 *  host sent: capsAnnounceEcho, answerEchoEvidence), main mode otherwise, a host that has shown none of them included.
 *  The evidence is kept per host name for the page's life. */
export const hostEchoMode = (evidence: ReadonlyMap<string, boolean>, sid: string): boolean => evidence.get(hostOf(sid)) === true;

/** Where a kernel answer (commentCreated, commentCreateFailed) goes: to the echo-mode code when its createId names a
 *  create this page minted in echo mode (`minted`, kept for the page's life, so a late answer to one it settled, gave
 *  up on or handed back goes there too), and to main's code otherwise: the key absent, "", or an id this page did not
 *  mint in echo mode (a main-mode create's own, or another page's), so main's code sees the answers main saw. */
export const echoAnswer = (m: { id?: unknown; uuid?: unknown; createId?: unknown }, minted: ReadonlySet<string>): m is { createId: string } =>
  typeof m.createId === "string" && minted.has(m.createId);

/** The echo-mode create an answer settles: the one its createId names among those held, and none otherwise. */
export function heldCreateFor(holds: ReadonlyMap<string, CommentCreate>, m: { id?: unknown; uuid?: unknown; createId?: unknown }): CommentCreate | null {
  return typeof m.createId === "string" ? holds.get(m.createId) || null : null;
}

/** A passage named in a notice or a note: on one line, cut to 72 characters (as fork PR 915 does for the file
 *  viewer's comments), in quote marks. */
export function passageLabel(exact: string): string {
  const t = exact.replace(/\s+/g, " ").trim();
  return "“" + (t.length > 72 ? t.slice(0, 71) + "…" : t) + "”";
}

/** The toast for a refused comment whose passage has no unsent echo-mode dialog open to take its words back: they wait
 *  in the note a create dialog shows on any passage of that message, so it says how to open one: a selection's context
 *  menu, opened with a right-click, offers Comment (render.ts showSelectionMenu); selecting alone shows no Comment. An
 *  existing comment opens its thread, which shows no note. */
export function refusedCreateToast(exact: string): string {
  return "Your comment on " + passageLabel(exact) + " was not saved. Its words are kept: select text anywhere in that message, right-click it and choose Comment to see them.";
}

/** The toast for an echo-mode comment the page handed back when its kernel came back as a build without the echo
 *  (render.ts handBackEchoCreates): its dialog closed, and its words wait in the note a create dialog shows on any
 *  passage of that message, reached as the refused comment's toast says. */
export function handedBackToast(exact: string): string {
  return "Your comment on " + passageLabel(exact) + " may or may not have been saved, because the kernel restarted as an older version. Its words are kept: select text anywhere in that message, right-click it and choose Comment to see them.";
}

/** The toast for a comment the page gave up on that the kernel saved after all, when the words handed back to its
 *  passage's box have been changed there since: the box keeps them, and its thread is on the page. */
export function savedAfterAllToast(exact: string): string {
  return "Your comment on " + passageLabel(exact) + " was saved after all. What you typed in its box since is still there.";
}

/** The commentCreate frame for a held create: the send and every re-post of it build the same one, so
 *  the kernel sees one id for one gesture. */
export function commentCreateFrame(c: CommentCreate): { type: "commentCreate"; id: string; uuid: string; exact: string;
    text: string; name: string; model: string; effort: string; fast: string; color: string; createId: string } {
  return { type: "commentCreate", id: c.sid, uuid: c.uuid, exact: c.exact, text: c.text, name: c.name,
           model: c.model, effort: c.effort, fast: c.fast, color: c.color, createId: c.createId };
}
