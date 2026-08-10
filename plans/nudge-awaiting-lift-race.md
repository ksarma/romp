# The nudge stands down while a returned dispatch's report is in flight

Status: PROPOSED, NOT COMMITTED (the user 2026-08-10: queue it as a potential project, like
`cards-attention-rethink.md`; revisit later). Nothing here is scheduled. The diagnosis is
verified against a live incident; the fix below is designed but unbuilt.

## The incident (verified, 2026-08-10)

A session fixed a CI failure, ended its turn with "watching CI" and a background wait task
still out. The judges did everything right:

- **00:12:24** — the closer stamped the goal *awaiting* ("the re-run of CI; will confirm once
  it goes green"). That stamp is what suppresses status nudges (`_goal_awaiting_stamp`).
- **00:14:10** — CI finished, the background task returned, and `_lift_spent_awaiting`
  retired the stamp. Correct: that is the designed lift event.
- **00:14:20, the very next nudge tick** — the auto-nudge fired a status ask on the goal.
  The stamp (the only gate holding it) was gone, the goal read "working" again, the closer
  had settled the last *ended* turn, and the session looked idle. But the returned task had
  already re-woken the session: the wake-up turn carrying "CI is green" was in flight at that
  moment, with no observable transcript records yet, so every idle gate passed.
- **00:14:35** — the closer read the post-ask turn and filed done.

The user saw the session report "CI is green" and then, seconds later, be asked where the CI
fix stands. An earlier ask that morning had the same signature (nudge fired; the closer ruled
done three minutes later from a reply restating what the transcript already contained).

## Root cause

The awaiting-lift is treated as "the wait is over — resume stall-watching," when what it
actually means is "**new information is seconds away**." A dispatched background task
returning *guarantees* an imminent wake-up turn (the harness re-invokes the session with the
task notification), so a nudge in the same tick as a lift always asks for what that turn is
about to say. The 2026-07-24 guard (`_nudge_fire_list` yields when a judge verdict postdates
the nudge's evidence) doesn't cover it: no verdict exists yet — the newer information is an
unjudged in-flight turn. This is the CLAUDE.md cards-move rule breached one layer down: the
nudge moved on an inference (goal back to working + session reads idle), not on new
information (a turn that *ended* with the goal still unresolved).

## The fix (designed, not built — pick the derived check, not a latch)

The first-sketch fix — latch the goal nudge-suppressed at lift time until the next turn ends
— has three traps, worked through on 2026-08-10:

1. **The wake-up isn't guaranteed after all.** A kernel/session restart between the task
   returning and the turn starting loses the notification; a turn-end-keyed latch then holds
   forever, producing the inverse bug: a stalled card that can never be nudged again (the
   same deadlock family as the romp-injected-turn arm gate and the stale `working`
   state-record gate).
2. **Ordering trap.** The lift scan races the wake-up turn. If the turn ends *before* the
   lift is written, "a turn ended after the lift" never becomes true — deadlock by another
   door. The lift-write is the wrong event to key on.
3. **Scope creep.** Only the spent-dispatch lift predicts a wake-up. The 6h-backstop lift
   exists precisely to wake a session asleep behind a stale stamp — suppressing nudges after
   *that* lift would defeat its purpose.

**The shape that avoids all three:** a stateless derived check in `_auto_nudge_session`'s
gates — *suppress a goal's nudge while a completed dispatch of the goal's own postdates the
newest genuine ended turn.* Both facts are already in the transcript (`_scan_bg_tasks` pairs
launches to results; the parse knows turn ends), so it self-releases the moment any genuine
turn ends after the return, regardless of lift-scan timing, and it never touches goals whose
awaits weren't dispatch-backed. Bound it with the existing 6h awaiting backstop for the
lost-notification case (the one place a timer is the honest tool). Accepted cost: when the
wake-up turn ends but ignores the goal, the nudge fires one turn-end later than today — a
slightly late nudge is much cheaper than a false one (Philosophy: every false interrupt is a
broken flow state).

## Test sketch

Reproduce the incident shape in `tests/`: a goal with an awaiting stamp whose own dispatched
task has a completed record newer than the last ended turn → `_auto_nudge_session` must not
fire; add an ended turn after the return → fires (if still working); backstop expiry → fires.
The incident sequence above is the fixture template — rebuilt synthetically (invented
session names and ids per the privacy rules).

## Related

- `cards-attention-rethink.md` — the "blocked/needs-you" minting themes there share this
  incident's lesson: asks must come from events that carry new information.
- Memory: the diagnosis was first recorded in the maintainer's session memory on 2026-08-10.
