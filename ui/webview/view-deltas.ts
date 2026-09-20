// The TypeScript receiver for the kernel's _DELTA_SLOTS (2026-09-16): a full frame seeds a slot's base, a
// {type:"delta", slot} patch reassembles onto it, and a patch that cannot apply asks the sending kernel for the
// whole slot (needSlot) and yields nothing. Two consumers, each with one instance per socket: VS Code's panels and
// passive status pipe (vscode-extension/src/extension.ts; they have no shim), and federation.ts for every REMOTE
// socket it dials (Conn.viewDeltas, 2026-09-18: the relay dial carries the page's delta=1, so a remote kernel serves
// its timeline bars as patches, and the kernel's inline shim reassembles only its own LOCAL socket's frames).
// One instance belongs to one socket. Consumers continue receiving complete frames.
// A collection this table cannot key seeds no base (2026-09-19), the kernel's own rule for the shape (_delta_split:
// unkeyable means the whole frame, never zero entries). Produced by a kernel from a750f860d (2026-09-03, the slot
// protocol) to T278c (328e46c26, 2026-09-09; upstream kernels in that window, and fork main from its 2026-09-05 fold
// until it folded T278c), whose bars frame keys judging as a FLAT list (bykeys:sid,t,judge,t1) and ships its own key
// list (_keys); a kernel before the slot protocol sends the same flat list in whole frames and no patch; and a future
// collection keyed by another table takes the same road. The same refusal for a dictlist lane whose NAME carries the
// separator (2026-09-19): the kernel refuses to patch such a payload (_delta_split raises, and its slot goes whole on every
// push), so this side seeds no base over one, since a lane "a<SEP>b" holding item "c" and a lane "a" holding item "b<SEP>c"
// spell one key and a patch would merge them. The rule is the producer's, mirrored here because this receiver meets
// FOREIGN kernels; the kernel's inline shim decoder (kernel.py, the BEGIN VIEW DELTA DECODER block) does not mirror it and
// meets only the kernel that rendered it, which never patches such a payload (the ledger entry
// upstream/2026-09-19-shim-decoder-seeds-a-separator-lane.md records that gap). Seeded, the first judging patch assembled to the patched
// entries alone, per lane and in the old entry shape, and a lane's marks collapsed between full frames; unseeded,
// every patch from it recovers (needSlot) and the slot crosses whole per change, the pre-delta cost, rendered from the
// flat list (federation.ts judgingToWire). Its feed frame keys asks as this table does and seeds as any other. The
// refusal is the one silent shape whose repair never repairs (a bad base or a malformed patch files nothing either,
// but the whole frame they earn seeds). At the seed it tells nothing apart, though: a remote that never patches (one
// before the slot protocol) and one that will send the same whole frame, which renders either way, so nothing is
// said there. The event that costs is the PATCH that finds no base because the slot's whole frame was refused, and
// that is where the OPTIONAL second callback hears of it, per such patch, with the collection and shape the table
// could not key; federation.ts says it once per distinct row (a hostconn row and a console line, keyed on the reason
// and the remote's build). A patch on a slot never seeded, or whose revision misses the held base, is the receiver's
// own resync and says nothing. The extension's pipe has no diagnostics road and passes none.
type Slot = "feed" | "bars";
type Frame = Record<string, any>;
type Collection = { order: string[]; items: Map<string, any> };
type Base = { rev: number; msg: Frame; maps: Map<string, Collection> };
export const VIEW_DELTA_KINDS: Record<Slot, Record<string, string>> = {
  feed: { asks: "byid:itemId" },
  bars: { turns: "dictlist:id", judging: "dictlist:k", messages: "byid" },
};
const KINDS = VIEW_DELTA_KINDS; // pinned to the kernel-produced fixture and the rendered browser table
const SEP = "\u001f";
const object = (v: any): v is Frame => !!v && typeof v === "object" && !Array.isArray(v);
const slotOf = (s: any): Slot | null => s === "feed" || s === "bars" ? s : null;
class Unkeyable extends Error {}   // a present collection whose container the kind cannot key: the frame seeds nothing

function split(value: any, kind: string): Collection {
  if (kind !== "byid" && !kind.startsWith("byid:") && !kind.startsWith("dictlist:")) {
    throw new Error("unsupported view collection kind: " + kind);
  }
  // A list where the kind says dictlist, or an object where it says a list, is a wire keyed by another table (the
  // header's pre-T278c judging); an absent collection is left as before (the kernel keys nothing for it either and
  // sends such a frame whole, so a base seeded over it is never patched). A dictlist lane whose name carries the
  // separator is refused below, in the lane walk: the kernel refuses to patch such a payload (_delta_split), and seeded
  // here its items' keys could not be told apart from another lane's. The reasons stay short: federation.ts puts one
  // behind the slot and before the remote's build tag in a row the kernel cuts at 64 characters (CLIENT_DIAG_STR_MAX).
  if (value !== undefined && value !== null && (kind.startsWith("dictlist:") ? !object(value) : !Array.isArray(value))) {
    throw new Unkeyable(kind + " is " + (Array.isArray(value) ? "a list" : "not a list"));
  }
  const order: string[] = [], items = new Map<string, any>();
  const field = kind === "byid" ? "id" : kind.slice(kind.indexOf(":") + 1);
  function put(value: any, prefix: string, bare = false) {
    const id = object(value) ? value[field] : null;
    let key = bare ? prefix : id === null || id === undefined || id === "" ? null : prefix + String(id);
    if (key === null || items.has(key)) {
      let n = order.length;
      do { key = prefix + "#" + n++; } while (items.has(key));
    }
    items.set(key, value); order.push(key);
  }
  if (kind.startsWith("dictlist:")) {
    if (object(value)) for (const [lane, list] of Object.entries(value)) {
      if (lane.includes(SEP)) throw new Unkeyable(kind + " lane has separator");   // the kernel's twin refusal (_delta_split)
      const prefix = lane + SEP;
      if (!Array.isArray(list) || !list.length) put(list, prefix, true);
      else for (const item of list) put(item, prefix);
    }
  } else if (Array.isArray(value)) for (const item of value) put(item, "");
  return { order, items };
}

function assemble(collection: Collection, kind: string, previous: any): any {
  if (!kind.startsWith("dictlist:")) return collection.order.map((key) => collection.items.get(key));
  const lanes = new Map<string, any>();
  for (const key of collection.order) {
    const cut = key.indexOf(SEP), lane = cut < 0 ? key : key.slice(0, cut);
    const suffix = cut < 0 ? "" : key.slice(cut + 1);
    if (!suffix) lanes.set(lane, collection.items.get(key));
    else {
      if (!lanes.has(lane)) lanes.set(lane, []);
      const list = lanes.get(lane);
      if (!Array.isArray(list)) throw new Error("a lane cannot hold both scalar and item entries");
      list.push(collection.items.get(key));
    }
  }
  // Preserve the browser shim's unchanged-lane identity contract, including an explicit reorder.
  for (const [lane, list] of lanes) {
    const old = Object.prototype.hasOwnProperty.call(previous || {}, lane) ? previous[lane] : undefined;
    if (Array.isArray(list) && Array.isArray(old) && list.length === old.length && list.every((v, i) => v === old[i])) {
      lanes.set(lane, old);
    }
  }
  return Object.fromEntries(lanes);
}

function stringKeys(value: any): string[] {
  if (!Array.isArray(value) || !value.every((v) => typeof v === "string")) throw new Error("invalid key list");
  return value;
}

export class ViewDeltas {
  private bases = new Map<Slot, Base>();
  // a slot whose last whole frame this table refused as a base, and why (collection, kind and container, no frame
  // content): read by the patch that then finds no base, cleared by a whole frame that seeds
  private refused = new Map<Slot, string>();
  /** `needSlot` asks the sending kernel for a slot whole; `unkeyed`, optional, hears of a patch that found no base
   *  because the slot's whole frame was refused as one (the slot, and the table's reason), per such patch and never at
   *  the refusal itself: only a patch tells that the remote patches at all. */
  constructor(private needSlot: (slot: string) => void, private unkeyed?: (slot: string, why: string) => void) {}

  private recover(slot: string): null {
    const known = slotOf(slot);
    if (known) this.bases.delete(known);
    // Like the browser shim, retry on the next inapplicable delta (2026-09-16). The kernel
    // coalesces requests; a lost/refused first request must not freeze this socket forever.
    this.needSlot(slot);
    return null;
  }

  receive(msg: any): any {
    const full = slotOf(msg?.type);
    if (full) {
      const maps = new Map<string, Collection>();
      for (const [name, kind] of Object.entries(KINDS[full])) {
        try {
          maps.set(name, split(msg[name], kind));
        } catch (e) {
          if (!(e instanceof Unkeyable)) throw e;
          // the header's rule: no base for a frame this table cannot key, so the next patch recovers (needSlot) and
          // that kernel serves the slot whole again; the frame itself continues whole, as every full frame does. The
          // refusal is remembered, by collection and shape, for the patch that finds no base below; nothing is said
          // here, where a remote that never patches and one that will are the same frame. Per FRAME, not per remote:
          // a whole frame this table cannot key drops a base a previous one seeded (bases.delete), and the next whole
          // frame that keys seeds again and ends the refusal (refused.delete below); nothing about the remote's build
          // is remembered, only its last whole frame's shape
          this.bases.delete(full);
          this.refused.set(full, name + " " + (e as Error).message);
          return msg;
        }
      }
      this.bases.set(full, { rev: 0, msg, maps });
      this.refused.delete(full);   // a whole frame this table keys ends the refusal: the slot has a base again
      return msg;
    }
    if (msg?.type !== "delta") return msg;
    const slot = slotOf(msg.slot);
    // The kernel and installed extension can differ (2026-09-16). A newer slot still renders
    // through its whole frames even when this receiver cannot decode its patches.
    if (!slot) return typeof msg.slot === "string" && msg.slot ? this.recover(msg.slot) : null;
    const base = this.bases.get(slot);
    if (!base) {
      // No base to apply onto. A patch before any whole frame on this socket is the receiver's own resync; one after a
      // whole frame this table REFUSED is the standing cost the header describes, and this is the one moment it is
      // attributable (that remote patches, and this side keys none of its whole frames), so the listener hears of it
      // here, per patch; the resync is the same either way.
      const why = this.refused.get(slot);
      if (why) this.unkeyed?.(slot, why);
      return this.recover(slot);
    }
    if (base.rev !== msg.base) return this.recover(slot);
    try {
      if (!Number.isSafeInteger(msg.base) || msg.base < 0 || !Number.isSafeInteger(msg.rev) || msg.rev !== msg.base + 1 || !object(msg.coll)) {
        throw new Error("invalid delta revision or collections");
      }
      const kinds = KINDS[slot], next = { ...base.msg }, maps = new Map(base.maps);
      if (msg.rest !== undefined) {
        if (!object(msg.rest) || (msg.rest.type !== undefined && msg.rest.type !== slot)) throw new Error("invalid remainder");
        if (msg.restAll) for (const key of Object.keys(next)) {
          if (!Object.prototype.hasOwnProperty.call(kinds, key) && !Object.prototype.hasOwnProperty.call(msg.rest, key)) delete next[key];
        }
        for (const [key, value] of Object.entries(msg.rest)) {
          if (Object.prototype.hasOwnProperty.call(kinds, key)) throw new Error("collection in remainder");
          Object.defineProperty(next, key, { value, writable: true, enumerable: true, configurable: true });
        }
      }
      if (next.type !== slot) throw new Error("missing frame type");
      for (const [name, change] of Object.entries(msg.coll)) {
        if (!Object.prototype.hasOwnProperty.call(kinds, name) || !object(change)) throw new Error("invalid collection");
        const old = maps.get(name)!;
        const items = new Map(old.items);
        let order = old.order.slice();
        if (change.del !== undefined) for (const key of stringKeys(change.del)) items.delete(key);
        if (change.set !== undefined) {
          if (!object(change.set)) throw new Error("invalid set");
          for (const [key, value] of Object.entries(change.set)) {
            if (!items.has(key)) order.push(key);
            items.set(key, value);
          }
        }
        order = change.order !== undefined ? stringKeys(change.order).slice() : order.filter((key) => items.has(key));
        if (order.length !== items.size || new Set(order).size !== order.length || order.some((key) => !items.has(key))) {
          throw new Error("incomplete collection order");
        }
        const collection = { order, items };
        maps.set(name, collection);
        next[name] = assemble(collection, kinds[name], base.msg[name]);
      }
      this.bases.set(slot, { rev: msg.rev, msg: next, maps });
      return next;
    } catch {
      // A malformed patch never partially advances the held maps or reaches a consumer.
      return this.recover(slot);
    }
  }
}
