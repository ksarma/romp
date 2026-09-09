// A settings pick HELD for the session's live work: the words the chat line, its hover and the badge tips
// use. Pure and string-only, like billing-label.ts, so every case runs as a test (pick-held.test.ts) and the
// surfaces cannot drift; the callers own their chrome.
//
// The kernel holds a pick (effort, permission mode into bypass, fast mode's first opt-in, billing, env) while
// the session runs subagents, Workflow runs or background tasks, since the reload that applies it would kill
// them, and it arms the reload only at a turn's settle that finds none left (SdkSession._arm_reconnect_if_quiet,
// 2026-09-09). The status carries ONE marker for every held kind, `pickHeld` ({surfaces, subagents, tasks}
// from SdkSession.snapshot), and every surface reads it: the badges show the value the session RUNS with a
// small pending mark, the chat says what waits and on what. Both counts at zero means the work has finished
// and the pick waits for a turn to finish: the one in flight (the one the CLI starts to deliver the last
// result) when `inflight` is true, else the session's next; the copy names which instead of "waiting on 0
// subagents" (review round 2; the turn phase since review round 3, 2026-09-09: the kernel sends `inflight`
// from SdkSession._pick_held, and a payload without it keeps the "this turn" copy).

export interface PickHeld { surfaces: string[]; subagents: number; tasks: number; inflight?: boolean }

// Which turn's end applies the pick once the work is done: the open one, or the session's next when none is.
function turnPhrase(h: PickHeld): string {
  return h.inflight === false ? "the next turn" : "this turn";
}

// The kind names in the user's words; a surface this build does not know is named as the kernel sent it.
const KIND_NAMES: Record<string, string> = {
  effort: "effort", mode: "permission mode", fast: "fast mode", auth: "billing", env: "environment",
};

export function pickKindName(kind: string): string {
  return KIND_NAMES[kind] ?? kind;
}

export function workPhrase(n: number, m: number): string {
  return `${n} subagent${n === 1 ? "" : "s"} and ${m} background task${m === 1 ? "" : "s"}`;
}

// "The effort pick" / "The effort and billing picks" / "The pending change" for a hold naming no surface.
export function pickHeldSubject(h: PickHeld): { text: string; plural: boolean } {
  const names = (h.surfaces || []).map(pickKindName);
  if (names.length === 0) return { text: "The pending change", plural: false };
  if (names.length === 1) return { text: `The ${names[0]} pick`, plural: false };
  return { text: `The ${names.slice(0, -1).join(", ")} and ${names[names.length - 1]} picks`, plural: true };
}

// The chat line's visible text, keyed on the state: work still running names the counts; none left says
// the pick applies when the turn finishes.
export function pickHeldLine(h: PickHeld): string {
  const { text, plural } = pickHeldSubject(h);
  if (h.subagents + h.tasks > 0) return `${text} ${plural ? "are" : "is"} waiting on ${workPhrase(h.subagents, h.tasks)}`;
  return `${text} ${plural ? "apply" : "applies"} when ${turnPhrase(h)} finishes`;
}

// The chat line's hover: the why, not the counts (those are in the line itself).
export function pickHeldTitle(h: PickHeld): string {
  if (h.subagents + h.tasks > 0) {
    return "the session reloads to apply the change when they finish; reloading now would cut them off";
  }
  if (h.inflight === false) {
    return "the background work has finished and no turn is open; the session reloads to apply the change "
      + "when the session's next turn ends";
  }
  return "the background work has finished; the session reloads to apply the change when the turn that "
    + "delivers the last result ends";
}

// A badge's tip while its kind is held: the label is what the session runs now, and this says what waits.
export function badgeHeldTip(kind: string, h: PickHeld): string {
  const name = pickKindName(kind);
  const what = `${/^[aeiou]/i.test(name) ? "an" : "a"} ${name} pick`;
  const when = h.subagents + h.tasks > 0
    ? `is waiting on ${workPhrase(h.subagents, h.tasks)}`
    : `applies when ${turnPhrase(h)} finishes`;
  return `${what} ${when}; the badge shows what the session runs now`;
}
