// The chat's client-side PENDING SEND (render.ts registerOptimistic / reconcileOptimistic): a composer
// send shows its bubble the instant Enter is pressed and re-asserts it on every push until the kernel's
// payload accounts for the message. The DECISIONS live here, pure, so send-pending.test.ts executes
// them (the repo's extract-for-execution idiom); render.ts owns the DOM and the per-session maps.
//
// An entry has NO LIFETIME. It used to expire after 20 s ("a real send always echoes within this"), and
// the 2026-09-06 audit watched the case that assumption misses: the kernel's own echo was pruned early,
// nothing showed a message the CLI still held for 30 s, and the client's bubble gave up at 20 s — the
// send looked lost, then reappeared higher up. An entry now ends on EVENTS only:
//   - a LANDED user atom carrying the text, placed AFTER the send's anchor (below), that no earlier
//     pending send with the same text has already claimed,
//   - the kernel's NEVER-DELIVERED verdict on it, placed after the same anchor (its dropped-echo bubble
//     takes over, with the copy-to-composer and dismiss actions),
//   - the user's ✕ (render.ts's qx delegate drops the entry).
// A kernel PROVISIONAL (its echo atom, its queued bubble) only SUPPRESSES ours for the push it is visible
// on — the durable record is the kernel's (a persisted echo, the dropped marking, the fed-text guard in
// prune_live), but if it blinks, ours steps straight back in. Nothing here reads a clock.
//
// THE ANCHOR (2026-09-06 review): every decision is read from the events AFTER the send, never from a
// count of tail events. At the first reconcile after the press the entry records the uuid of the last
// stable kernel event (`at.after`) and the uuids of the user events that ALREADY carried the text
// (`at.seen`: an older identical message, an old echo, an undismissed never-delivered bubble). A
// landing, a verdict or a provisional counts for this send only when it sits after the anchor and is
// not in `seen`. The old form read the last 30 events and assumed the landing was near the tail — but an
// absorbed atom is placed at its SEND time, so after a gap in pushes (a sleep, a reconnect, a turn with
// many thinking and tool events) it sat far above the tail and, with the lifetime gone, the bubble never
// ended. When the anchor itself has left the resident window (the transcript grew past the wire tail),
// everything resident is after it, so the scan starts at the head.

export type SendBase = {
  after: string | null;   // uuid of the last stable kernel event at the press; null → nothing to anchor on, scan from the head
  seen: string[];         // uuids of the user events carrying the text at the press: background, never this send
  queued: number;         // copies of the text the kernel's queued bubble(s) already listed at the press
};

export type PendingSend = {
  text: string;        // the sent body, byte for byte — what the kernel echoes and the transcript lands
  body: string;        // `text` minus its image paths, whitespace-collapsed: an image send lands with the
                       //   paths rewritten to "[Image #N]" and stripped, so `text` itself can never match
  ts: number;          // press time (ms) — the bubble's identity in the events array, never a lifetime
  at?: SendBase;       // the send's place in the events (stamped by the first reconcile after the press)
  imgPaths?: string[]; // dragged images → the bubble's thumbnails, and the image-aware landing match
  lost?: string;       // an event after the press that makes non-delivery LIKELY ("connection": the
                       //   socket dropped) — the bubble says "not confirmed" instead of "sending…"
  received?: boolean;  // the kernel has shown its OWN copy of this send (an echo atom or a queued bubble
                       //   that appeared after the press): the send reached it, so a connection drop
                       //   before or after cannot have lost it — `lost` is cleared and never set again
};

/** The slice of a chat event the decisions read (render.ts's ChatEvent is a superset). */
export type TailEvent = {
  kind: string;
  md?: string;
  uuid?: string;
  absorbed?: boolean;
  undelivered?: boolean;
  images?: unknown[];
  texts?: { md?: string }[];
};

export const OPT_PREFIX = "optimistic:";
export const isOptimisticUuid = (u?: string): boolean => !!u && u.startsWith(OPT_PREFIX);
export const isKernelEchoUuid = (u?: string): boolean => !!u && u.startsWith("echo:");
const collapse = (s: string): string => s.replace(/\s+/g, " ").trim();

/** `text` with its shipped image paths removed (quoted or bare, however the composer joined them). */
export function pendingBody(text: string, imgPaths?: string[]): string {
  let t = text;
  for (const p of imgPaths || []) t = t.split('"' + p + '"').join(" ").split(p).join(" ");
  return collapse(t);
}

export function newPending(text: string, imgPaths?: string[], now: number = Date.now()): PendingSend {
  return { text, body: pendingBody(text, imgPaths), ts: now, imgPaths };
}

/** EXACT text match, trimmed: the composer trims what it sends and the kernel strips what it lands
 *  (`" ".join(blocks).strip()`; a follow-up's body after `_split_followup`), so the two agree byte for
 *  byte apart from edge whitespace. Never a substring test — "test" is not "test the continue button",
 *  and a landing of the longer message must not retire the shorter send (2026-09-06 review). */
const sameText = (md: string, text: string): boolean => md.trim() === text.trim();

/** A LANDED user atom carrying this send: a user event whose uuid is not the kernel's echo prefix and
 *  whose md IS the text — or, for an image send, whose md is the body and which carries images (the
 *  CLI rewrote the paths to "[Image #N]"; the kernel strips the placeholders and renders the pictures,
 *  so the paths are gone from the text; a quoted path may leave its quotes behind, so those are set
 *  aside on both sides). */
export function landedIn(e: TailEvent, p: PendingSend): boolean {
  if (e.kind !== "user" || typeof e.md !== "string" || isKernelEchoUuid(e.uuid)) return false;
  if (sameText(e.md, p.text)) return true;
  if (p.imgPaths && p.imgPaths.length && Array.isArray(e.images) && e.images.length > 0) {
    const noq = (s: string) => collapse(s.replace(/"/g, ""));
    return noq(e.md) === noq(p.body);
  }
  return false;
}

/** How many copies of the send's text a kernel queued bubble lists. */
function queuedCopies(e: TailEvent, p: PendingSend): number {
  if (e.kind !== "queued" || !Array.isArray(e.texts)) return 0;
  let n = 0;
  for (const x of e.texts) if (typeof x.md === "string" && sameText(x.md, p.text)) n++;
  return n;
}

/** The kernel's own PROVISIONAL copy of the send: its queued bubble or its unlanded echo atom. A
 *  never-delivered echo is a VERDICT, not a provisional (lostIn), and never suppresses a bubble. */
export function provisionalIn(e: TailEvent, p: PendingSend): boolean {
  if (e.kind === "queued") return queuedCopies(e, p) > 0;
  return e.kind === "user" && isKernelEchoUuid(e.uuid) && !e.undelivered && typeof e.md === "string" && sameText(e.md, p.text);
}

/** The kernel's verdict that the send was LOST: its echo, flagged never-delivered (the CLI died holding
 *  it, or the session moved past it). That bubble carries the text and the resend/dismiss actions. */
export function lostIn(e: TailEvent, p: PendingSend): boolean {
  return e.kind === "user" && !!e.undelivered && typeof e.md === "string" && sameText(e.md, p.text);
}

/** A kernel event a pending send can be anchored to: it has a uuid the kernel will keep. The client's own
 *  injections and the kernel's echo atoms are excluded — an echo is replaced by the landed atom (a new
 *  uuid) the moment its text lands, so it is not a stable place. */
const stableUuid = (e: TailEvent): boolean => !!e.uuid && !isOptimisticUuid(e.uuid) && !isKernelEchoUuid(e.uuid);

/** Where this send sits among the kernel's events, read once at the first reconcile after the press. */
export function stampBase(events: TailEvent[], p: PendingSend): SendBase {
  let after: string | null = null;
  for (let i = events.length - 1; i >= 0; i--) if (stableUuid(events[i])) { after = events[i].uuid!; break; }
  const seen: string[] = [];
  let queued = 0;
  for (const e of events) {
    if (e.kind === "queued") { queued += queuedCopies(e, p); continue; }
    if (e.kind !== "user" || !e.uuid || isOptimisticUuid(e.uuid)) continue;
    if (landedIn(e, p) || lostIn(e, p) || provisionalIn(e, p)) seen.push(e.uuid);
  }
  return { after, seen, queued };
}

/** The first index AFTER the send's anchor — or 0 when there is no anchor, or when the anchor has left the
 *  resident window (then everything resident is later than the send). */
export function scanFrom(events: TailEvent[], at: SendBase): number {
  if (at.after === null) return 0;
  for (let i = events.length - 1; i >= 0; i--) if (events[i].uuid === at.after) return i + 1;
  return 0;
}

export type Reconciled = {
  keep: PendingSend[];                        // still pending after this push
  inject: PendingSend[];                      // …and not covered by a kernel provisional → show ours
  landed: { p: PendingSend; idx: number }[];  // retired by a landing; idx = the landed event's index
  lost: PendingSend[];                        // retired by the kernel's never-delivered verdict
};

/** One push's decision for a session's pending sends, read off the KERNEL's events (the caller has
 *  already stripped its own injections). Entries are read in registration order, and ONE landing retires
 *  ONE entry: the k-th landing after the anchor retires the k-th pending send with that text, and a
 *  landing an earlier entry took is background (`seen`) for every later entry with the same text — two
 *  identical sends in flight used to both retire on the first landing (2026-09-06 review). */
export function reconcilePending(events: TailEvent[], list: PendingSend[]): Reconciled {
  // First reconcile after the send: whatever the events ALREADY hold for this text is background — an
  // older identical message, an old echo, an undismissed never-delivered bubble — not this send. Only
  // what appears after the anchor, beyond that set, is this send's (the user 2026-08-09, who watched
  // resends vanish in the call that created them; the 2026-09-06 review, which watched a resend of a
  // never-delivered message retired as lost by the old verdict).
  for (const p of list) if (!p.at) p.at = stampBase(events, p);
  const r: Reconciled = { keep: [], inject: [], landed: [], lost: [] };
  const claimed = new Set<number>();          // landing indices taken by an earlier entry THIS push
  for (const p of list) {
    const at = p.at!;
    const from = scanFrom(events, at);
    let landedIdx = -1, lostIdx = -1, provisional = false, copies = 0;
    for (let i = from; i < events.length; i++) {
      const e = events[i];
      if (e.uuid && at.seen.includes(e.uuid)) continue;
      if (e.kind === "queued") { const n = queuedCopies(e, p); copies += n; if (n) provisional = true; continue; }
      if (landedIdx < 0 && !claimed.has(i) && landedIn(e, p)) { landedIdx = i; continue; }
      if (lostIdx < 0 && lostIn(e, p)) { lostIdx = i; continue; }
      if (provisionalIn(e, p)) {
        provisional = true;
        p.received = true;                    // an echo the kernel minted for THIS send: it has the text
      }
    }
    if (copies > at.queued) p.received = true;  // the kernel's queue lists a copy it did not list at the press
    if (p.received) p.lost = undefined;         // the drop is older news than the kernel's own copy
    if (landedIdx >= 0) {
      claimed.add(landedIdx);
      const u = events[landedIdx].uuid;
      // this landing is spoken for: background for every later pending send with the same text, on this
      // push and every push after (the retired entry's claim would otherwise leave with it)
      if (u) for (const q of list) if (q !== p && q.at && q.text === p.text && !q.at.seen.includes(u)) q.at.seen.push(u);
      r.landed.push({ p, idx: landedIdx });
      continue;
    }
    if (lostIdx >= 0) { r.lost.push(p); continue; }
    r.keep.push(p);
    if (!provisional) r.inject.push(p);
  }
  return r;
}

/** Where the pending bubble SAT when its message landed higher up: the uuid of the last RENDERED kernel
 *  event after `landedIdx` (the bubble rode the tail, under that event). null when the landed atom is
 *  itself the tail — the swap happened in place and no cue is owed. The client's own injections and the
 *  kernel's echo atoms are skipped: neither is a stable place to hang a note. `rendered` says which
 *  events the chat draws in its current mode — compact mode (the default) hides thinking, and a cue
 *  anchored to a hidden event is never drawn and can never be dismissed (2026-09-06 review). */
export function cueAnchor(events: TailEvent[], landedIdx: number, rendered: (e: TailEvent) => boolean = () => true): string | null {
  for (let j = events.length - 1; j > landedIdx; j--) {
    const e = events[j];
    if (!stableUuid(e) || !rendered(e)) continue;
    return e.uuid!;
  }
  return null;
}

/** The bare group's one-line header, from its bubbles' OWN states: the lost ones (the connection dropped
 *  after the press and nothing has confirmed them) read "not confirmed", the rest "sending…". A group
 *  used to read "N not confirmed" when ANY bubble was lost, and kept that label for the survivors after
 *  a ✕ (2026-09-06 review). */
export type BareLabelPart = { text: string; lost: boolean };
export function bareGroupLabel(nLost: number, nSending: number): { parts: BareLabelPart[]; title: string } {
  const parts: BareLabelPart[] = [];
  if (nLost > 0) parts.push({ text: nLost === 1 ? "not confirmed" : `${nLost} not confirmed`, lost: true });
  if (nSending > 0) parts.push({ text: nSending === 1 ? "sending…" : `sending ${nSending}…`, lost: false });
  const lostTitle = "The connection dropped after " + (nLost === 1 ? "this was" : "these were")
    + " sent, and romp has not confirmed the session has " + (nLost === 1 ? "it" : "them") + ". ✕ moves "
    + (nLost === 1 ? "it" : "one") + " back to the composer to send again.";
  const sendingTitle = "on its way to the session — cancellable until the session takes it";
  const title = nLost > 0 && nSending > 0 ? lostTitle + " The rest: " + sendingTitle + "."
    : nLost > 0 ? lostTitle : sendingTitle;
  return { parts, title };
}
