// The "worked …" footer's rule, pure (2026-09-06): which reply carries the footer, and how long it says.
//
// A reply's footer depends on LATER events — the turn has to be complete (a genuine human prompt landed
// after it) or the session idle — which made it the one thing on a rendered turn that a later event could
// change without the kernel naming that turn in a chatTail. The chat's tail path re-renders exactly the
// events the kernel names as changed (render.ts syncViewInner), so the footer is patched by unit from this
// plan instead of a trailing window re-rendered on every tail.
export interface WorkedEvent { kind: string; human?: boolean }
export type Epoch<E> = (ev: E) => number | null;

/** Seconds the session worked on the prompt that reply `i` answers, or null when `i` carries no footer:
 *  a prompt itself; a reply that is not its turn's last (a later reply exists before the next genuine
 *  prompt); the final turn while the session is still working (the live spinner owns it); no clock on
 *  either end. The elapsed runs from the IMMEDIATE trigger — the most recent user-role line of ANY author
 *  (a nudge or a postal push that prompted the work, not the older human prompt: the user 2026-06-22, who
 *  saw "worked 23m" on a two-minute-old nudge) — to the reply's own stamp. Injected user lines (a postal
 *  push, /command stdout) belong to the same turn: the scan for the turn's end skips them. */
export function turnWorkedSecs<E extends WorkedEvent>(events: readonly E[], i: number, working: boolean, epoch: Epoch<E>): number | null {
  const ev = events[i];
  if (ev.kind === "user") return null;
  let completed = false;
  for (let j = i + 1; j < events.length; j++) {
    const e = events[j];
    if (e.kind !== "user") return null;
    if (e.human) { completed = true; break; }
  }
  if (!completed && working) return null;
  const end = epoch(ev);
  if (end == null) return null;
  let start: number | null = null;
  for (let j = i; j >= 0; j--) { const e = events[j]; if (e.kind === "user") { start = epoch(e); break; } }
  if (start == null) return null;
  const secs = end - start;
  return secs > 0 ? secs : null;
}

/** The footers to reconcile after a tail re-rendered events [from, len): the last reply of the current turn
 *  and of the one before it, when that reply sits BEFORE `from` (a reply at or past `from` was just rendered
 *  with its footer) and inside the rendered window (at or past `winStart`). `secs` null means the reply
 *  carries no footer now (the session went back to work on the same turn — a nudge, say — and the footer it
 *  wore while idle comes off). Only a turn's LAST reply can carry one, so the walk visits one reply per
 *  turn; two turns cover both events that complete a turn: a prompt landing (the previous turn's reply)
 *  and the session going idle (the current turn's reply). */
export function workedFooterPlan<E extends WorkedEvent>(events: readonly E[], from: number, winStart: number, working: boolean, epoch: Epoch<E>): Array<{ unit: number; secs: number | null }> {
  const out: Array<{ unit: number; secs: number | null }> = [];
  let prompts = 0, replySeen = false;
  for (let j = events.length - 1; j >= winStart && prompts < 2; j--) {
    const ev = events[j];
    if (ev.kind === "user") { if (ev.human) { prompts++; replySeen = false; } continue; }
    if (replySeen) continue;      // not the turn's last reply: never a footer
    replySeen = true;
    if (j < from) out.push({ unit: j, secs: turnWorkedSecs(events, j, working, epoch) });
  }
  return out;
}
