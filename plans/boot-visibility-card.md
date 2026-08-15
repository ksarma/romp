# A boot visibility card: what the restart did to your sessions

**Status: PROPOSED, NOT COMMITTED** — parked by the user (2026-08-15) as a long-term
consideration. Nothing here is scheduled; do not build unbidden. Filed after a reboot question
surfaced that the recovery behavior already exists but is invisible — the investigation notes
below are the valuable part, recorded so a revival doesn't re-derive them.

## What already happens at a kernel cold start (verified 2026-08-15, `main` post-#71)

The boot reconcile (`kernel/sdk_backend.py` `_boot_reconcile`) is event-keyed on each
session's recorded state tail, never on timers:

- **Mid-turn casualties auto-resume.** A session whose state tail is `working` had its turn
  CUT by the kernel death (a user interrupt writes `idle`, a finished turn `waiting` — only a
  kill leaves `working`). It is resumed at boot — staggered, so a big batch doesn't make the
  restart look hung (the user 2026-07-20) — with a visible continuation nudge ahead of its
  restored queue (the 2026-07-05 stranded-mid-turn incident is why).
- **Queued sessions auto-resume** so their persisted, undelivered messages deliver.
- **Idle-but-alive sessions never read as dead.** The boot death-pass (`_death_boot_pass`,
  kernel.py) explicitly skips registry entries with `alive: true` — "the resume contract owns
  it" — so they present as ready and resume lazily on first touch.
- **Only tmux-backend sessions genuinely die**: stamped `by: "boot"` in `gone/<sid>.json` at
  the next kernel start, shown dead, revived per-session by hand.
- Sessions already dead BEFORE the restart keep their older stamps and stay down.

So the user's original ask ("after a reboot, revive what the restart killed but not what was
already dead") is the shipped behavior for SDK sessions — better than an offer, since cut
work resumes itself. What is MISSING is visibility: the reconcile acts silently, and the user
has no way to see what it did or to notice the tmux casualties without hunting.

## The proposed card

After a kernel cold start where the reconcile did anything, the feed shows ONE notice card
(the `clearNotices` pattern — kernel-built, riding the feed payload):

> The restart resumed **N** cut sessions, **M** idle sessions are ready, **K** died — Revive · Dismiss

- Glanceable one-liner by default; the session names one click deeper (progressive
  disclosure). "Revive" appears only when K > 0 and posts the existing per-sid `reviveSession`
  op (federation-routed for free); Dismiss records per-sid so the card never flaps back.
- Retirement is event-based: revived/dismissed sids drop the card via the payload, never a
  timeout.
- The offer set derives from records, restart-proof: `gone/` stamps with `by == "boot"`, not
  yet dismissed, still dead — no time-window heuristics (every element is a recorded event).
- Federation: the sid list needs `prefixInbound` coverage (an `OBJ_SID`-style key) so a
  remote kernel's casualties route their revives home.

## Why parked

The dominant backend (SDK) already recovers itself; the card's actionable half serves only
tmux-backend casualties, which the user may never have. The visibility half is genuinely
nice — the reconcile earns trust by being seen — but is not worth a build until the silent
behavior actually causes a moment of doubt. If that moment comes, this doc plus
`_boot_reconcile`'s docstring are the full context.
