// Skeleton tabs (2026-09-07): the client half of the reconnect diet. When a pane redials after its socket
// died (a laptop lid, a long freeze, a network change), the kernel used to serve the fresh socket as a client
// that holds nothing: seventeen full `session` frames, ~9 MB, for ONE tab on screen. Now a redial declares
// itself (`reconnect=1`), the kernel sends the tab strip with a `skeleton` list (every background tab it
// is withholding, cheapest first), the ACTIVE tab in full, and a ~400 B `status` frame per withheld tab. This
// module owns the client's copy of that set — which tabs are resting, what the kernel last said about each,
// and which one to fetch next in idle — as a pure, DOM-free state machine (the prebuild.ts / tab-meta.ts
// pattern: executable in node, so the policy is pinned by skeleton-tabs.test.ts while render.ts only wires it).
// A redial declares itself only once the kernel's caps frame has answered the bundle's ready; before that, with
// the ready still queued for the open, or after a socket that died before its caps frame came back, the shim dials
// as a fresh page and the kernel sends everything whole (2026-09-10).
//
// The page HELD every session before the outage, and render.ts deliberately keeps those `sessions` entries
// (the eventual full then takes upsert's append path, so the DOM and the reader's scroll survive). What a
// skeleton id must never do is DISPLAY that stale copy as current — so render.ts asks this set before every
// active-tab display path (`liveSession`) and before drawing a tab (`renderKind`).
import { hostOf } from "./host-prefix";   // the start gate reads a want's host: a tab on another kernel is served over its relay socket, not this chain's (gateOnStrip)

export interface SkeletonState {
  ids: Set<string>;            // the tabs this page holds no CURRENT copy of (the kernel is withholding them)
  order: string[];             // the kernel's list order — ascending transcript size, the prefetch order
  status: Map<string, any>;    // the last kernel-sent status per skeleton id (the chip reads ONLY this)
  loaded: Set<string>;         // ids whose full `session` frame arrived on THIS socket (see applyTabOrderSkeleton)
  // The idle prefetch's START GATE (stage 0 of the reconnect design, 2026-09-18). Closed for every new socket (the boot dial, and
  // each redial: onSocketUp) and opened by ONE of three events: the first full frame applied for the tab the strip shows as
  // active (gateOnFrame: the pane's active tab, or the tab it awaits after a reload, the kernel's one full under the diet); a
  // strip from the local kernel that lists no such LOCAL tab (gateOnStrip: the stored tab ended while the page was away, a
  // fresh profile with none, or a stored tab on another host, whose full comes over that host's relay socket and is not this
  // chain's to wait for; the kernel's list is the event that says no full is coming for one from this kernel); or a tab shown
  // as active whose full already applied on this socket (gateOnShow: a tap onto a whole tab before the diet's one full lands).
  // nextPrefetch is null while it is closed; the click road (a tap on a skeleton asks at once, render.ts showActive) is never
  // gated. The gate reads no layout: it runs on every layout, ordering the chain behind the active tab's first full (on the
  // desktop that costs the redial's first background ask that one full's latency and nothing else). Before this the chain armed
  // from the strip's first paint, which the kernel sends before it builds anything, so the first background full could leave
  // ahead of the visible tab's, and on a phone link the visible session waited behind a tab nobody was looking at.
  gate: boolean;
  // THE RETURN HOLD (the owner's decision, 2026-09-19): on the phone a redial reloads the VISIBLE tab alone, and the other chat
  // tabs reload only when tapped (the click road, which no gate touches), for the socket's life. A return from the background
  // redials with reconnect=1 and the kernel re-skeletons every other tab; before this the chain then re-downloaded them all, about
  // 16 to 22 MB on the owner's board, for tabs nobody asked for (by the design's per-full figures, 37 fulls at 0.44 to 0.58 MB each;
  // no return's chain has been measured). Set by onSocketUp when the pane's shell is the phone layout (the arm's layout read, at
  // render.ts's wsup arm, the redial's frame); while it stands gateOnFrame and gateOnShow open nothing and nextPrefetch issues no
  // ask; gateOnStrip opens under it (pass 4b, the author's label, 2026-09-20, taking the reviewer's round-3 addendum's extra7-1: its evidence, a local strip with no local want, does not
  // recur, and a refusal recorded nowhere left the gate closed after the flip back to the desktop, the lift arming nothing), which
  // costs no ask while the hold stands and is what the lift arms over. The boot dial sends no wsup, so a cold open's chain is
  // untouched; the desktop passes false and keeps its chain.
  // RE-DECIDED ON THE LAYOUT WORD (review round 3, 2026-09-19, extra8-1): the shell re-tells its panes word on every media-query flip
  // with the layout in it (kernel panesMsg `mob`), and its link word to the iframes outside the pane frames with the same term (a split
  // chat column hears the link word alone; review round 4, kernel-3), and onLayoutWord below sets the hold from that word and the
  // redial record, so a flip to the desktop inside the socket's life lifts the hold (the grid gets its chain) and a flip to the phone
  // after a redial sets it; before this the layout was sampled once at the wsup arm and the hold outlived it in both directions.
  returnHold: boolean;
  redialed: boolean;   // a wsup has arrived on this page (onSocketUp ran): the hold's precondition, since a cold open's chain is never held
}

export function newSkeletonState(): SkeletonState {
  return { ids: new Set(), order: [], status: new Map(), loaded: new Set(), gate: false, returnHold: false, redialed: false };
}

/** A full `session` frame applied (render.ts upsert). Opens the gate when `id` is one of `wants`, the tab the strip shows as
 *  active (render.ts passes the active tab and the tab awaited after a reload, read before the frame's own adoption moved
 *  them). Returns whether it opened NOW, so a caller can arm the chain on the event; an open gate stays open. */
export function gateOnFrame(st: SkeletonState, id: string, wants: ReadonlyArray<string | null | undefined>): boolean {
  if (st.gate || st.returnHold || !id) return false;
  if (!wants.some((w) => w === id)) return false;
  st.gate = true;
  return true;
}

/** The local kernel's strip landed (render.ts applyTabOrder, localStrip). When it lists no LOCAL tab the pane shows or awaits as
 *  active (`want` null; an id the strip does not carry: an ended session; or a want on another host, `host:uuid`, whose full is
 *  served over that host's relay socket and is not this chain's to wait for) no full is coming for one from this kernel, so the
 *  gate opens here and the chain loads the tabs in the kernel's order. A strip that does list a local want leaves the gate to
 *  the frame. Reads no return hold (pass 4b, the author's label, taking the reviewer's round-3 addendum's extra7-1): an open gate under the hold issues no ask, nextPrefetch's hold term
 *  below, and the lift's second read of the gate arms the chain on the flip back. Returns whether it opened NOW. */
export function gateOnStrip(st: SkeletonState, order: readonly string[], want: string | null | undefined): boolean {
  if (st.gate) return false;
  if (want && !hostOf(want) && order.includes(want)) return false;
  st.gate = true;
  return true;
}

/** A tab shown as active (render.ts setActive, silentActivate) whose full already applied on THIS socket (`st.loaded`): the
 *  visible tab has its frame, so the chain may start. A tap onto a tab served whole ahead of the diet's one full (a
 *  transcript-less session is never a skeleton) would otherwise leave the gate to that full's re-post. Never keyed on the
 *  session map, which after a redial holds stale copies of every tab. Returns whether it opened NOW. */
export function gateOnShow(st: SkeletonState, id: string): boolean {
  if (st.gate || st.returnHold || !st.loaded.has(id)) return false;
  st.gate = true;
  return true;
}

/** A tabOrder frame landed. An ARRAY is the kernel's authoritative set → REPLACE (a second reconnect while
 *  skeletons are outstanding re-lists tabs that had loaded — they are stale again, the honest state; once a set
 *  has existed the kernel attaches the key on EVERY strip, an empty list after it empties). NOT an array (an
 *  older kernel, which never sends the key) → KEEP what we hold, pruned to the ids still on the strip. Status entries for ids no longer held are dropped. Returns whether anything
 *  changed, so the caller can key a repaint / re-show on it.
 *
 *  One exception to "array = authoritative": an id whose FULL frame already arrived on this socket is never
 *  re-adopted from an array. The kernel releases a sid the moment it sends its full and enqueues both under
 *  one lock, so a tabOrder that still names X can only be AHEAD of X's full on the wire, never behind it — a
 *  list naming X after X's full is therefore a stale relay, not new information. The federation merge is
 *  exactly such a relay: it keeps a per-host copy of the list and re-attaches it to every merged strip, and
 *  a merge can re-present a copy taken ahead of the full that released the last id (review find 2026-09-08:
 *  the kernel does send an empty list once the set empties, so the copy is eventually told; the filter is
 *  about ORDER, not about a missing key). Without this filter the last skeleton on the strip re-skeletoned on every push, asked for its full, loaded,
 *  and re-skeletoned again — a flap the user's eye follows forever. `onSocketUp` clears the record: a new
 *  socket's list IS new information about every tab. */
export function applyTabOrderSkeleton(st: SkeletonState, skeleton: unknown, order: readonly string[]): boolean {
  const before = st.ids;
  const beforeOrder = st.order;
  let next: string[];
  const keep = new Set(order);   // the strip is the authority on what exists: an id it does not list is gone
  if (Array.isArray(skeleton)) {
    const seen = new Set<string>();
    next = [];
    for (const id of skeleton) {
      // …so a listed skeleton the order lacks (a session that ended before it loaded) is never adopted — the idle
      // prefetch would otherwise ask the kernel for a session it can no longer send (review find 2026-09-07)
      if (typeof id === "string" && id && keep.has(id) && !seen.has(id) && !st.loaded.has(id)) { seen.add(id); next.push(id); }
    }
  } else {
    next = beforeOrder.filter((id) => keep.has(id) && before.has(id));
  }
  st.ids = new Set(next);
  st.order = next;
  for (const id of Array.from(st.status.keys())) if (!st.ids.has(id)) st.status.delete(id);
  if (before.size !== st.ids.size) return true;
  for (let i = 0; i < next.length; i++) if (beforeOrder[i] !== next[i]) return true;
  for (const id of next) if (!before.has(id)) return true;
  return false;
}

/** A {type:"status"} frame. For a skeleton id the status is STORED for the chip and the caller schedules one
 *  strip repaint; for any other id the caller runs today's path (apply to the session, or the no-base repair —
 *  which for a skeleton id would ask for the full and defeat the whole set within a cycle). */
export function onStatus(st: SkeletonState, id: string, status: unknown): "skeleton" | "not-skeleton" {
  if (!st.ids.has(id)) return "not-skeleton";
  st.status.set(id, status);
  return "skeleton";
}

/** A {type:"status"} frame for an id the set does not list (yet) and the page holds NO session for. The kernel sends a
 *  status frame for a sid it holds as a skeleton and for no other (_send_chat_or_status), so such a frame is a skeleton
 *  tab's whose strip this page has not applied: the pane shim's dispatch FIFO carries a newer whole-state frame (a
 *  second tabOrder) to the END of the burst, so the statuses that arrived between two strips are delivered ahead of
 *  the strip that names their set (a later chat column's open sends two: the pusher cycle its handshake woke and the
 *  ready arm's connect push). Held for that strip: applyTabOrderSkeleton keeps the entry when the array lists the id
 *  and drops it when it does not, and the chip reads it only for a skeleton id. Never the no-base ask, which asked for
 *  every withheld tab's full and loaded the whole board into a column opened as a view of one session (2026-09-11). */
export function holdStatus(st: SkeletonState, id: string, status: unknown): void {
  st.status.set(id, status);
}

/** A full `session` frame landed (upsert): the id is loaded, its skeleton entry and stored status go.
 *  Returns whether it WAS held — a just-loaded skeleton that is the active tab must re-show its view, not
 *  append to the hidden one. Also records the id as loaded on this socket (see applyTabOrderSkeleton). */
export function onFull(st: SkeletonState, id: string): boolean {
  st.loaded.add(id);
  const held = st.ids.delete(id);
  if (!held) return false;
  st.order = st.order.filter((x) => x !== id);
  st.status.delete(id);
  return true;
}

/** The tab left the strip (a close, the kernel's omission, a host drop): nothing to load any more. */
export function onDismiss(st: SkeletonState, id: string): void {
  // its view and session left the page with the tab, so it is no longer LOADED here: a later re-listing (a host
  // re-attach, a relay redial) names it a skeleton again and the pane asks for its frame — the way the unfocused
  // pane gets the session the user was on back (T357); before, a once-loaded id could never be a skeleton again on
  // the same socket, so the re-listed tab sat with an "opening…" loader and no ask
  st.loaded.delete(id);
  if (!st.ids.delete(id)) return;
  st.order = st.order.filter((x) => x !== id);
  st.status.delete(id);
}

/** A new socket opened: every earlier full was delivered on a socket that is gone, so the next list the
 *  kernel sends may legitimately re-list those tabs (they are stale after the outage). `phone`: the pane's shell is the
 *  phone layout (render.ts reads it at the wsup arm), so the redial holds the chain for the socket's life (returnHold). */
export function onSocketUp(st: SkeletonState, phone?: boolean): void {
  st.loaded.clear();
  st.gate = false;   // …and the chain waits again for the active tab's first frame on the new socket (stage 0): a redial re-skeletons every other tab, and the visible one's full comes first
  st.returnHold = phone === true;   // …and on the phone it does not run again on this socket: the other tabs reload when tapped (the owner's decision, 2026-09-19)
  st.redialed = true;   // the hold's precondition for a later layout word (onLayoutWord)
}

/** The shell's LAYOUT word (kernel panesMsg `mob`, re-told on every media-query flip; render.ts's panes handler passes it for a pane frame
 *  and its link handler for a split chat column, which hears the link word alone: review round 4, kernel-3): the hold is
 *  re-decided from it and the redial record, so it never outlives the layout (review round 3, 2026-09-19, extra8-1). `phone` true after
 *  a redial holds (a flip to the phone inside the socket's life: the other tabs reload when tapped, as a phone redial's do); false lifts
 *  (a flip to the desktop: the grid gets its chain back). Before any redial nothing is held whatever the word (a cold open's chain is
 *  never held). Returns whether a STANDING hold was lifted now, so the caller can open the gate for the shown tab and arm the chain (or arm
 *  it over a gate already open, which gateOnShow refuses to re-open: render.ts reads `gate` beside it, review round 4, verdict 1). */
export function onLayoutWord(st: SkeletonState, phone: boolean): boolean {
  const was = st.returnHold;
  st.returnHold = st.redialed && phone;
  return was && !st.returnHold;
}

/** The one skeleton to fetch in this idle callback, or null. Null while the page is hidden (bytes and work
 *  nobody sees — the very regime this exists to spare), while ANY skeleton id is already in flight (one at a
 *  time: a 1 MB full ahead of the active tab's 2 KB tail on a slow link delays that tail; one bounds it), and
 *  when nothing is left. Otherwise the first id of the kernel's order still held, not the active tab (its own
 *  click path asks), and in the current view (a view-hidden tab loads on click instead). Null too while the start gate is
 *  closed (`st.gate`, stage 0): the visible tab's first frame has not applied on this socket and the strip lists it, and while the
 *  return hold stands (`st.returnHold`, the owner's decision of 2026-09-19, re-decided on the shell's layout word since round 3). */
export function nextPrefetch(st: SkeletonState, activeId: string | null, inFlight: ReadonlySet<string>,
                             hidden: boolean, inView: (id: string) => boolean): string | null {
  if (hidden || !st.gate || st.returnHold) return null;   // …and while the return hold stands (review round 3, extra8-1: a hold set on a layout word after the gate opened must stop the chain too; before this only the openers read the hold, so a flip to the phone mid-socket held nothing; and, since gateOnStrip reads no hold (pass 4b, the author's label, the reviewer's round-3 addendum's extra7-1), the one term that keeps an open gate silent under it)
  for (const id of st.ids) if (inFlight.has(id)) return null;
  for (const id of st.order) {
    if (!st.ids.has(id) || id === activeId) continue;
    if (inView(id)) return id;
  }
  return null;
}

/** How the strip draws a tab. A skeleton id draws as a skeleton even when a (stale) session entry exists —
 *  that entry is kept for the eventual append, never used to paint. A placeholder is "the kernel is building
 *  this, it is coming" (swirl); a skeleton is "resting, loads on your click" (honest dot, muted label). */
export function renderKind(st: SkeletonState, id: string, hasSession: boolean): "skeleton" | "placeholder" | "loaded" {
  if (st.ids.has(id)) return "skeleton";
  return hasSession ? "loaded" : "placeholder";
}
