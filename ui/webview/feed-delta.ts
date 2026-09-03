// Apply one kernel {type:"feedDelta"} frame onto the last full {type:"feed"} frame held for a host,
// producing a NEW full frame — the base is never mutated (the pane's hover-freeze queue and the merge
// tripwire hold references to earlier frames). The kernel sends deltas only to a socket that announced
// it can take them (the shim's ?caps=feedDelta) and only once that socket holds a full frame; the delta
// carries the cards that changed (by itemId), the itemIds that left, the same for ledgers (by sid),
// and — when any of them changed — EVERY other top-level field, whole, under `top`. federation.ts
// applies it per host and re-emits the merge, so everything downstream keeps seeing whole `feed` frames.
export interface FeedDelta {
  type: "feedDelta";
  now?: number; buildId?: number;
  asks?: any[]; removeAsks?: string[];
  ledgers?: any[]; removeLedgers?: string[];
  top?: Record<string, unknown>;
}

/** The keyed fields a delta upserts into, and their id field. Mirrors the kernel's _FEED_KEYED. */
export const FEED_KEYED: ReadonlyArray<readonly [string, string]> = [["asks", "itemId"], ["ledgers", "sid"]];

export function applyFeedDelta(base: any, d: FeedDelta): any {
  const out: any = d.top
    ? { ...d.top }                                   // top present ⇒ it IS the complete set of non-keyed fields
    : Object.fromEntries(Object.entries(base || {}).filter(([k]) => k !== "asks" && k !== "ledgers"));
  out.type = "feed";
  if (typeof d.now === "number") out.now = d.now;
  if (d.buildId !== undefined) out.buildId = d.buildId;
  out.asks = upsertById(Array.isArray(base?.asks) ? base.asks : [], d.asks || [], d.removeAsks || [], "itemId");
  if (Array.isArray(d.ledgers)) {
    // present ⇒ the client holds a ledgers list after this (the Outline pane's "the build ran" gate reads the key)
    out.ledgers = upsertById(Array.isArray(base?.ledgers) ? base.ledgers : [], d.ledgers, d.removeLedgers || [], "sid");
  } else if (Array.isArray(base?.ledgers)) {
    out.ledgers = base.ledgers;
  }
  return out;
}

/** Replace in place by id (order preserved), drop the removed, append the new. */
export function upsertById(prev: any[], ups: any[], gone: string[], key: string): any[] {
  const drop = new Set(gone);
  const byId = new Map<string, any>(ups.map((u) => [String(u[key]), u]));
  const out: any[] = [];
  for (const p of prev) {
    const id = String(p[key]);
    if (drop.has(id)) continue;
    const u = byId.get(id);
    if (u !== undefined) { out.push(u); byId.delete(id); } else out.push(p);
  }
  for (const u of byId.values()) out.push(u);
  return out;
}
