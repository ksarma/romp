// The chat's client-side PENDING SEND (render.ts registerOptimistic / reconcileOptimistic): a composer
// send shows its bubble the instant Enter is pressed and re-asserts it on every push until the kernel's
// payload accounts for the message. The DECISIONS live here, pure, so send-pending.test.ts executes
// them (the repo's extract-for-execution idiom); render.ts owns the DOM and the per-session maps.
//
// An entry has NO LIFETIME. It used to expire after 20 s ("a real send always echoes within this"), and
// the 2026-09-06 audit watched the case that assumption misses: the kernel's own echo was pruned early,
// nothing showed a message the CLI still held for 30 s, and the client's bubble gave up at 20 s — the
// send looked lost, then reappeared higher up. An entry now ends on EVENTS only:
//   - a LANDED user atom carrying the text (growth past `base`, so a resend or a short message that
//     substrings history never retires itself),
//   - the kernel's NEVER-DELIVERED verdict on it (its dropped-echo bubble takes over, with the
//     copy-to-composer and dismiss actions),
//   - the user's ✕ (render.ts's qx delegate drops the entry).
// A kernel PROVISIONAL (its echo atom, its queued bubble) only SUPPRESSES ours for the push it is visible
// on — the durable record is the kernel's (a persisted echo, the dropped marking, the fed-text guard in
// prune_live), but if it blinks, ours steps straight back in. Nothing here reads a clock.

export type PendingSend = {
  text: string;        // the sent body, byte for byte — what the kernel echoes and the transcript lands
  body: string;        // `text` minus its image paths, whitespace-collapsed: an image send lands with the
                       //   paths rewritten to "[Image #N]" and stripped, so `text` itself can never match
  ts: number;          // press time (ms) — the bubble's identity in the events array, never a lifetime
  base: number;        // landed atoms carrying the text at send time (-1 until the first reconcile)
  imgPaths?: string[]; // dragged images → the bubble's thumbnails, and the image-aware landing match
  lost?: string;       // an event after the press that makes non-delivery LIKELY ("connection": the
                       //   socket dropped) — the bubble says "not confirmed" instead of "sending…"
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
  return { text, body: pendingBody(text, imgPaths), ts: now, base: -1, imgPaths };
}

/** A LANDED user atom carrying this send: a user event whose uuid is not the kernel's echo prefix and
 *  whose md includes the text — or, for an image send, whose md includes the body and which carries
 *  images (the CLI rewrote the paths to "[Image #N]"; the kernel strips the placeholders and renders
 *  the pictures, so the paths are gone from the text). */
export function landedIn(e: TailEvent, p: PendingSend): boolean {
  if (e.kind !== "user" || typeof e.md !== "string" || isKernelEchoUuid(e.uuid)) return false;
  if (e.md.includes(p.text)) return true;
  if (p.imgPaths && p.imgPaths.length && Array.isArray(e.images) && e.images.length > 0) {
    return collapse(e.md).includes(p.body);
  }
  return false;
}

/** The kernel's own PROVISIONAL copy of the send: its queued bubble or its unlanded echo atom. */
export function provisionalIn(e: TailEvent, p: PendingSend): boolean {
  if (e.kind === "queued" && Array.isArray(e.texts)) return e.texts.some((x) => typeof x.md === "string" && x.md.includes(p.text));
  return e.kind === "user" && isKernelEchoUuid(e.uuid) && typeof e.md === "string" && e.md.includes(p.text);
}

/** The kernel's verdict that the send was LOST: its echo, flagged never-delivered (the CLI died holding
 *  it, or the session moved past it). That bubble carries the text and the resend/dismiss actions. */
export function lostIn(e: TailEvent, p: PendingSend): boolean {
  return e.kind === "user" && !!e.undelivered && typeof e.md === "string" && e.md.includes(p.text);
}

export type Reconciled = {
  keep: PendingSend[];                        // still pending after this push
  inject: PendingSend[];                      // …and not covered by a kernel provisional → show ours
  landed: { p: PendingSend; idx: number }[];  // retired by a landing; idx = the landed event's index
  lost: PendingSend[];                        // retired by the kernel's never-delivered verdict
};

/** One push's decision for a session's pending sends, read off the KERNEL's events (the caller has
 *  already stripped its own injections). `scan` bounds the tail read — the kernel's version of a send
 *  (its atom, its provisional) always lands at or near the tail. */
export function reconcilePending(events: TailEvent[], list: PendingSend[], scan: number = 30): Reconciled {
  const from = Math.max(0, events.length - scan);
  const where = (pred: (e: TailEvent) => boolean): number[] => {
    const out: number[] = [];
    for (let i = from; i < events.length; i++) if (pred(events[i])) out.push(i);
    return out;
  };
  // First reconcile after the send: whatever matching atoms the tail ALREADY holds are background — an
  // older identical message, a bubble this text substrings — not this send. Only growth past this
  // count is a landing (the user 2026-08-09, who watched resends vanish in the call that created them).
  for (const p of list) if (p.base < 0) p.base = where((e) => landedIn(e, p)).length;
  const r: Reconciled = { keep: [], inject: [], landed: [], lost: [] };
  for (const p of list) {
    const li = where((e) => landedIn(e, p));
    if (li.length > p.base) { r.landed.push({ p, idx: li[li.length - 1] }); continue; }
    if (where((e) => lostIn(e, p)).length) { r.lost.push(p); continue; }
    r.keep.push(p);
    if (!where((e) => provisionalIn(e, p)).length) r.inject.push(p);
  }
  return r;
}

/** Where the pending bubble SAT when its message landed higher up: the uuid of the last kernel event
 *  after `landedIdx` (the bubble rode the tail, under that event). null when the landed atom is itself
 *  the tail — the swap happened in place and no cue is owed. The client's own injections and the
 *  kernel's echo atoms are skipped: neither is a stable place to hang a note. */
export function cueAnchor(events: TailEvent[], landedIdx: number): string | null {
  for (let j = events.length - 1; j > landedIdx; j--) {
    const u = events[j].uuid;
    if (!u || isOptimisticUuid(u) || isKernelEchoUuid(u)) continue;
    return u;
  }
  return null;
}
