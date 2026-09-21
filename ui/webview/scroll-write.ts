// Instrumenting every programmatic scroll write of the chat transcript (T262, the user 2026-09-08: the view
// "jumps up slightly on my scroll in many, many sessions", on a page whose bundle state is unknown). A recording
// alone cannot say WHICH writer moved the view; the laptop's client-diag journal can, once every write to
// #content.scrollTop rides one helper that files a breadcrumb — {surface:"chat", what:"scrollwrite",
// data:{sid, writer, before, after, delta, stick, gesture:false}} — and every scroll the writes do not explain
// files a "scrollgesture" marker, so the recording's timestamps line up against the journal.
//
// Cheap by construction: no stack traces, one row per write that actually moved the view, a per-session
// per-minute cap for each row kind (a following tail writes the bottom on every append; a wheel scroll fires
// dozens of gesture events a second), with one "capped" row at the cap so a silence in the journal is never
// mistaken for a quiet pane. The minute is the wall clock's minute bucket — a bound on volume, not a timer
// that decides behaviour. Pure and DOM-free so node --test executes it.

export const SCROLL_DIAG_CAP_PER_MINUTE = 40;

/** The cap a page actually runs with: the default, or the positive integer in localStorage under
 *  "romp:scrollDiagCap" (T262j, the user 2026-09-08: a capture on their laptop hit the 40/min gesture cap within
 *  seconds of trackpad scrolling, and every unwritten move for the rest of the minute went unrecorded; a laptop
 *  capturing sets the key, everyone else keeps the default). Anything that is not a positive integer → the default. */
export const SCROLL_DIAG_CAP_KEY = "romp:scrollDiagCap";
export function readScrollDiagCap(getItem: (key: string) => string | null): number {
  let raw: string | null = null;
  try { raw = getItem(SCROLL_DIAG_CAP_KEY); } catch { raw = null; }
  const n = raw == null ? NaN : Number(raw);
  return Number.isInteger(n) && n > 0 ? n : SCROLL_DIAG_CAP_PER_MINUTE;
}

/** One kind of row's budget for one session within the current minute: "send" while under the cap, "cap"
 *  exactly once at the cap (the caller files a capped row), "drop" past it until the minute rolls. */
export class ScrollDiagBudget {
  private counts = new Map<string, { minute: number; n: number }>();
  constructor(private cap = SCROLL_DIAG_CAP_PER_MINUTE) {}
  take(sid: string, kind: string, nowMs: number): "send" | "cap" | "drop" {
    const minute = Math.floor(nowMs / 60000);
    const key = sid + " " + kind;
    let e = this.counts.get(key);
    if (!e || e.minute !== minute) { e = { minute, n: 0 }; this.counts.set(key, e); }
    e.n += 1;
    if (e.n <= this.cap) return "send";
    return e.n === this.cap + 1 ? "cap" : "drop";
  }
}

/** Is this #content scroll event the echo of the last programmatic write (its own scroll event, within a
 *  pixel of the value written), or a gesture nobody's code asked for? */
export function classifyScroll(scrollTop: number, lastWriteAfter: number | null): "write-echo" | "gesture" {
  return lastWriteAfter != null && Math.abs(scrollTop - lastWriteAfter) <= 1 ? "write-echo" : "gesture";
}

/** One childList mutation of a tail container, reduced to what the row needs: the classes of the nodes removed at
 *  the END, the classes of the nodes added at the end, and whether a removed node came back in the same task. */
export interface TailMutation { removed: Array<{ cls: string }>; added: Array<{ cls: string }>; atEnd: boolean; }
export function summarizeTailMutations(records: TailMutation[]): { removedTail: string[]; addedTail: string[]; reAdded: boolean } | null {
  const removedTail: Array<{ cls: string }> = [], addedTail: Array<{ cls: string }> = [];
  for (const r of records) {
    if (!r.atEnd) continue;
    removedTail.push(...r.removed); addedTail.push(...r.added);
  }
  if (!removedTail.length) return null;
  const reAdded = removedTail.some((n) => addedTail.indexOf(n) >= 0);
  return { removedTail: removedTail.map((n) => String(n.cls || "").slice(0, 40)), addedTail: addedTail.map((n) => String(n.cls || "").slice(0, 40)), reAdded };
}

/** The breadcrumb for a tail element leaving the DOM (T262j, the user 2026-09-08): the remaining snap is a clamp
 *  against a transcript momentarily shorter WITHIN a frame — a tail node removed, a layout forced, the node back
 *  before the frame ends — which no ResizeObserver can see. `shBefore` = the last scroll height the pane recorded,
 *  `shAfter` = the height once the mutations settled; `reAdded` = the same node came back in the same task. */
export function tailMutRow(sid: string, m: { removedTail: string[]; addedTail: string[]; reAdded: boolean }, shBefore: number, shAfter: number, st: number, ch: number, where: "view" | "live-ask") {
  const clip = (a: string[]) => a.slice(0, 4).map((c) => String(c).slice(0, 40));
  return { sid, where, removed: clip(m.removedTail), added: clip(m.addedTail), reAdded: m.reAdded, shBefore, shAfter, st, ch };
}

/** The breadcrumb for one re-size of a view's virtualization spacers (T262j): a top spacer re-estimate paired with
 *  a bottom one leaves scrollHeight unchanged yet moves everything under the top spacer, and Chrome's scroll
 *  anchoring then moves the reader by the same amount with no pane write. `top`/`bot` = [before, after] heights.
 *  `sh`/`ch` are the scroller's heights read a frame later for the view shown in that frame; a row whose view was
 *  switched away before the frame has none (null, never another view's figures) and carries `view: "inactive"` (PR E
 *  review round 1b). A row with no marker and numbers is the shown view's. */
export function spacerRow(sid: string, topBefore: number, topAfter: number, botBefore: number, botAfter: number, sh: number | null = 0, ch: number | null = 0, view?: "inactive") {
  return { sid, top: [topBefore, topAfter], bot: [botBefore, botAfter], dTop: topAfter - topBefore, dBot: botAfter - botBefore, sh, ch, ...(view ? { view } : {}) };
}

/** The breadcrumb for one height change of the transcript's TAIL outside the append path (T262f, the user
 *  2026-09-08): the active view's element or the live-ask host grew or shrank, by `dh` px, with `last` naming the
 *  tail element (its class list, or "live-ask"). Chrome moves a bottom reader down itself when the tail grows and
 *  clamps them back when it shrinks — both unwritten, so the scroll rows alone cannot say WHICH element flapped;
 *  this row, filed beside them, names it. `stick` = the view's recorded follow mode at the change. */
export function tailChangeRow(sid: string, dh: number, last: string, stick: boolean, sh = 0, ch = 0) {
  return { sid, dh, last: String(last || "").slice(0, 60), stick, sh, ch };
}

/** The class list of the tail element of a view: its last child that carries a unit when `isUnit` is given (the pane's data-unit,
 *  render.ts unitOfNode: a hover's rail band, drawn as the thread's last child with no unit, is not the tail), else, and for a view with
 *  no unit-carrying child at all, its last child that is not a virtualization spacer: the rule before the predicate (PR E, the
 *  maintainer's round 2 ruling), kept for callers that pass none and standing in whole, as a second pass, where the predicate finds
 *  nothing (the maintainer's round 3 ruling C: the empty transcript's placeholder and the deferred build's loading hint are a view's only
 *  child and carry no unit, and the row whose purpose is naming what changed height named nothing there; a per-child OR would instead
 *  name a band beside units). DOM-free: the caller says what a unit is. */
export function tailLabel<T extends { className?: string }>(children: ArrayLike<T>, isUnit?: (c: T) => boolean): string {
  if (isUnit) for (let i = children.length - 1; i >= 0; i--) if (isUnit(children[i])) return String(children[i]?.className || "");
  for (let i = children.length - 1; i >= 0; i--) {
    const c = String(children[i]?.className || "");
    if (c.indexOf("tx-spacer") < 0) return c;
  }
  return "";
}

/** The breadcrumb for one height change of a unit that is NOT the tail (T262n, the user's 2026-09-08 laptop capture:
 *  one unwritten move in eleven minutes, a 24 px shrink of the transcript with the reader at the bottom, and no row
 *  named what shrank). The view rail's row says the transcript changed height and names the TAIL; when a unit above
 *  the tail changes height in place, that row still names the tail. This one names the unit: `cls` its class list,
 *  `fromTail` how many units above the tail it sits (1 = the unit just above it), `stick` the view's recorded follow
 *  mode and `atBottom` the measured bottom at the read. A row only: nothing is written or decided from it. */
export function unitChangeRow(sid: string, dh: number, cls: string, fromTail: number, stick: boolean, atBottom: boolean, sh = 0, ch = 0) {
  return { sid, dh, cls: String(cls || "").slice(0, 60), fromTail, stick, atBottom, sh, ch };
}

export interface UnitHeights<T> { get(t: T): number | undefined; set(t: T, h: number): unknown; }

/** Boxes of the scroller OUTSIDE the thread (the T262n follow-up): #content's direct children that are not a
 *  thread and not the live-ask host (which has its own rows): the host-offline foot, #sub-head, the build
 *  placeholders. The laptop capture's one unwritten move had no tailchange row, so its 24 px came from one of
 *  these, on a remote-host tab, where the foot is the one such box. A box has no place in the thread, so its
 *  unit row carries fromTail BOX_FROM_TAIL and names the box by id (#host-offline-foot) else by class. */
export const BOX_FROM_TAIL = -1;
export function boxLabel(box: { id?: string; className?: string }): string {
  return box.id ? "#" + box.id : String(box.className || "");
}
/** Fold one ResizeObserver callback over the scroller's boxes into the in-place changes to file: the first
 *  observation is the baseline (the pane records it when the box appears), an unchanged height files nothing. */
export function boxChanges<T extends { id?: string; className?: string }>(entries: Array<{ target: T; height: number }>,
                                                                        heights: UnitHeights<T>): Array<{ target: T; dh: number; cls: string }> {
  const out: Array<{ target: T; dh: number; cls: string }> = [];
  for (const e of entries) {
    const prev = heights.get(e.target);
    heights.set(e.target, e.height);
    if (prev === undefined || e.height === prev) continue;
    out.push({ target: e.target, dh: e.height - prev, cls: boxLabel(e.target) });
  }
  return out;
}
/** Fold one ResizeObserver callback over a view's units into the non-tail changes to file. `entries` are the
 *  observed units with their new heights, `children` the view's children in order, `heights` the last height seen
 *  per unit (a WeakMap in the pane). The first observation of a unit is its baseline and files nothing (observe()
 *  reports once on attach); an unchanged height files nothing; a virtualization spacer never files (its spacer rows
 *  say what it did); the TAIL unit never files here, because the view rail's row already carries its change; a unit
 *  no longer in the window files nothing. The tail is the last child with a unit index when `unitOf` is given (the
 *  trim's rule, render.ts unitOfNode: a hover's rail band, the thread's last child with no unit, is neither the tail
 *  nor a unit, and the real tail unit keeps its exemption; PR E, the maintainer's round 2 ruling), else the last child
 *  that is not a spacer (the rule before, kept for callers that pass no `unitOf`). A view with NO unit-carrying child
 *  (the empty transcript's placeholder, the deferred build's loading hint: each a view's only child, observed like
 *  every added element) has no tail and files nothing, as the spacer rule did, and a child that carries no unit (a
 *  foreign child: the hover's band) files nothing either (the maintainer's round 3 ruling A: the unit-aware scan left
 *  the tail at -1 and read children[-1], which the pane's `unitOf` threw on, and filed a band below the tail at a
 *  negative distance). `fromTail` counts UNITS when `unitOf` can say which unit a child belongs to (the pane's
 *  data-unit: a day divider is a child of its own carrying the unit it opens, so counting children would read one
 *  turn plus a divider as two turns), and is never negative: the units are in order and the tail is the last of them
 *  (0 for a divider of the tail's own unit); it falls back to child distance where no unit index exists. */
export function unitChanges<T extends { className?: string }>(entries: Array<{ target: T; height: number }>, children: ArrayLike<T>,
                                                                heights: UnitHeights<T>, unitOf?: (t: T) => number | undefined): Array<{ target: T; dh: number; cls: string; fromTail: number }> {
  const hasUnit = (c: T): boolean => { const u = unitOf!(c); return typeof u === "number" && !Number.isNaN(u); };
  let tail = -1;
  for (let i = children.length - 1; i >= 0; i--) if (unitOf ? hasUnit(children[i]) : String(children[i]?.className || "").indexOf("tx-spacer") < 0) { tail = i; break; }
  const out: Array<{ target: T; dh: number; cls: string; fromTail: number }> = [];
  for (const e of entries) {
    const prev = heights.get(e.target);
    heights.set(e.target, e.height);
    if (prev === undefined || e.height === prev) continue;
    const cls = String(e.target?.className || "");
    if (cls.indexOf("tx-spacer") >= 0) continue;
    let idx = -1;
    for (let i = 0; i < children.length; i++) if (children[i] === e.target) { idx = i; break; }
    if (idx < 0 || tail < 0 || idx === tail) continue;   // tail < 0: no unit-carrying child (the placeholder, the loading hint): nothing to measure a distance from, nothing filed
    if (unitOf && !hasUnit(e.target)) continue;          // a foreign child below the tail (a hover's band): neither a unit nor the tail, never a negative distance
    const ut = unitOf ? unitOf(children[tail]) : undefined, uu = unitOf ? unitOf(e.target) : undefined;
    const byUnit = typeof ut === "number" && typeof uu === "number" && !Number.isNaN(ut) && !Number.isNaN(uu);
    out.push({ target: e.target, dh: e.height - prev, cls, fromTail: byUnit ? ut - uu : tail - idx });
  }
  return out;
}

/** The breadcrumb for one write that moved the view. `sh`/`ch` = #content's scrollHeight/clientHeight after the
 *  write (T262e, the user 2026-09-08: their laptop's rows showed the view moving UP by the same 95 px on two
 *  sessions with no write between the rows — an UNWRITTEN move, which the rows could not classify: a browser
 *  CLAMP after the transcript's tail shrank (scrollHeight drops, the new top equals scrollHeight − clientHeight)
 *  reads exactly like the browser's scroll anchoring absorbing a layout change above the viewport (scrollHeight
 *  unchanged). With both numbers on every row the next log tells them apart in one pass.) */
export function scrollWriteRow(sid: string, writer: string, before: number, after: number, stick: boolean, sh = 0, ch = 0) {
  return { sid, writer, before, after, delta: after - before, stick, gesture: false as const, sh, ch };
}
