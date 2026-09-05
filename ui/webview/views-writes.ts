// A page's VIEWS WRITES in flight, and what the kernel's answer to one of them means (the user
// 2026-09-05, who lost a batch of tag renames and assignments): every write of the views blob —
// a targeted tag edit (`tagEdit`) or a whole-blob lens/order write (`setTimelineViews`) — carries
// a writeId, and the kernel answers it on the same socket with {tagEditAck|viewsAck, writeId, ok,
// views, error?, refused?}. The optimistic copy a gesture showed clears on that ACK — an event —
// never on a count of frames: a frame that does not echo the edit says nothing about it (it may
// predate the write, or the kernel may have refused it), and the three-frame yield this replaces
// dropped good edits and kept refused ones alike. Pure, shared by render.ts (the tab strip) and
// mirrored by hand in ui/romp-timeline-view.js (which cannot import TS).
import type { SessionViews } from "./session-views";

/** one targeted tag edit — the kernel applies it through its /tag merge, which reads the store first
 *  and so is never judged stale against this page's own earlier writes. Every op but create addresses
 *  the tag by its stored id (`tid`): a name is what a refused rename would have changed, so a
 *  follow-up addressed by name could land on whichever OTHER tag already had it. The message nests
 *  this under `edit`, so no top-level `name` can read as a session address to the federation router. */
export interface TagEditOp {
  op: "create" | "rename" | "recolor" | "addMember" | "removeMember" | "delete";
  /** the tag's stored id — every op but create */
  tid?: string;
  /** create only: the typed name, or none for the kernel's default ("tag N", minted unique there) */
  name?: string;
  newName?: string;
  color?: string;
  sid?: string;
  sids?: string[];
}

export interface ViewsAck {
  type?: string;
  writeId?: unknown;
  ok?: boolean;
  views?: SessionViews | null;
  /** the store's write sequence after this write — the blob's own `seq`, repeated for the poster */
  seq?: number | null;
  error?: string;
  /** the whole-blob path: each tag the stale-writer guard kept the store's copy of, with its reason */
  refused?: { tid?: string; name?: string; reason?: string }[];
  /** a targeted edit: the tag it touched — a create's caller learns the kernel-minted id and name here */
  tid?: string;
  name?: string;
}

/** the blob's write sequence, or null for a blob from a kernel that does not stamp one */
export function seqOf(v: SessionViews | null | undefined): number | null {
  const s = v && (v as any).seq;
  return typeof s === "number" && Number.isFinite(s) ? s : null;
}

/** Whether an incoming blob may replace the held one: yes when its seq is at least the held seq, or
 *  when either side carries no seq (a kernel from before the stamp, or nothing held yet). The order
 *  the socket delivered them in decides nothing — the pusher builds frames from a warmed cache that
 *  can predate a write whose ack already arrived, and federation re-emits stored blobs; the seq is
 *  the store's own order, so an older blob is ignored wherever it turns up. */
export function adoptViews(held: SessionViews | null | undefined, incoming: SessionViews | null | undefined): boolean {
  if (!incoming) return false;
  const h = seqOf(held), i = seqOf(incoming);
  return h === null || i === null || i >= h;
}

export interface AckOutcome {
  /** the writes still in flight after this ack */
  inflight: string[];
  /** drop the optimistic copy now: every write is settled (ok), or this one was refused (revert) */
  clearPending: boolean;
  /** a refusal's one-line reason for the user, else null */
  refusal: string | null;
}

/** a write id: the ms stamp plus a per-page counter, so two same-ms gestures never share one */
export function mintWriteId(seq: number): string {
  return "w" + Date.now().toString(36) + "-" + seq.toString(36);
}

/** What one ack means for the page. ok → this write is settled; the copy clears once NOTHING is in
 *  flight (a later gesture may still be pending). Refused → everything is dropped at once: the
 *  store's blob (the ack carries it) is what stands, and the reason surfaces. An ack for a write
 *  this page never made (a previous load's) still counts as information: with nothing of ours in
 *  flight, the returned blob is the base and no copy stays pinned. */
export function ackOutcome(inflight: readonly string[], m: ViewsAck): AckOutcome {
  const rest = inflight.filter((id) => id !== m.writeId);
  if (m.ok === false) {
    const names = (m.refused || []).map((r) => r && r.name).filter((n): n is string => !!n);
    const why = m.error || (m.refused || []).map((r) => r && r.reason).filter(Boolean).join("; ") || "refused";
    return { inflight: [], clearPending: true, refusal: names.length ? names.join(", ") + ": " + why : why };
  }
  return { inflight: rest, clearPending: rest.length === 0, refusal: null };
}
