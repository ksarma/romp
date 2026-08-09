# Cards & status: encode attention, not plumbing

Status: PROPOSED, NOT COMMITTED (the user 2026-08-09: write it up as a potential project;
explicitly not ready to green-light). Nothing here is scheduled. The decisions menu below was
reviewed once by the user in conversation; the recommendations are the assistant's, not rulings.
One piece of groundwork already shipped independently: PR #33 made the status-pip input an
honest four-way partition (working / awaiting / ready / state-unknown) so a blank no longer
means anything — the recoloring proposed in Decision 3 builds on that, not on excavation.

## The three problems (the user, 2026-08-09)

1. **"Blocked" is one bucket holding two opposite things.** Some cards are blocked on a
   quick decision — seconds of the user's time, and answering it unblocks parallel work
   sitting idle. Others are blocked because the model's part is DONE and an extended review
   task now sits with the user — minutes to hours, wanting to be scheduled, not popped.
   Qualitatively different; represented identically today.
2. **Session pips encode turn plumbing, not attention.** The dot's yellow/green answers
   "is the turn open?" — so a session waiting on an in-turn subagent shows yellow while one
   waiting on a backgrounded task shows green: the same human situation, two colors, keyed
   on mechanics the user shouldn't have to know. (A third failure — sessions rendering NO
   pip despite known state — was a plain bug, fixed in PR #33.)
3. **Completed is a landfill.** Every finished card piles up until manually checkboxed away,
   so the column carries no signal. Manual dismissal at landfill scale is the problem, not
   the answer.

All three reduce to one principle, which is already the repo's philosophy: the board should
spend the user's attention, not drain it. A card's representation should answer "what does
this cost me and when?" — never "what is the harness doing internally?"

## Decisions menu

Five decisions, severable. Recommendations marked; none is a commitment.

### D1 — How ask-vs-review gets classified

| Option | Pros | Cons |
|---|---|---|
| **A. Judge-derived** — one more field on the blocked-on-you verdict, read from the ask the judge already holds | No new protocol; covers existing sessions; a misfile self-corrects on the next verdict from fresh evidence (the cards-move rule) | Heuristic — a one-line question hiding a deep decision misfiles as "quick" |
| **B. Session self-declaration** — a session-prompt line in the person-voice register (like the path-mention nudge): ask decisions in one line; when handing over review work, say what and roughly how long | Precision at the source; makes asks better-written independent of card logic | Only new sessions comply; agents drift from prompt guidance, so A is needed as fallback regardless |
| **C. Judge effort estimate** (seconds/minutes/hours) instead of two buckets | Desk could sort by size | Estimates will be visibly wrong, corroding trust in the surface; two buckets already capture the behavioral split (interrupt vs schedule) |

**Recommended: A + B together; skip C** unless two buckets prove insufficient in practice.

### D2 — Where the split lives on the board

| Option | Pros | Cons |
|---|---|---|
| **A. One "Needs you" column, two groups** — Asks pinned on top (question rendered inline, answerable inline where possible); "On your desk" below, styled as an inbox | One place to look; no board restructure; mobile-safe | Busy days make the column tall; two temperaments share one region |
| **B. Two columns** | Cleanest separation; column counts become meaningful | Board widens (real cost on the phone); empty-column states; one more region competing for the glance |
| **C. Asks leave the board** — surfaced as an inline answer-prompt + push; the board carries only Desk | Matches asks' transient nature: answer and gone | Biggest build; needs a fallback surface for dismissed asks anyway, degrading to A-plus-inline |

**Recommended: A now**, with inline answer buttons on ask cards; C's inline-prompt behavior is
a natural later graduation if A holds up.

### D3 — Pip semantics

| Option | Pros | Cons |
|---|---|---|
| **A. Attention legend** — red/amber = needs you (shades for ask vs desk); yellow = IN MOTION (open turn OR background delegation, merged on purpose); green = idle, nothing needed; grey = dead/unknown | The dot answers the only glance question; kills the yellow/green plumbing confusion at the root; one legend across tabs, fleet, timeline | Hides turn-open vs background-wait (occasionally wanted — demote to hover/click detail); retrains muscle memory |
| **B. Color = attention + subtle animation = open turn** | Both dimensions on one glyph | Animation is an attention tax on a surface whose point is calm; accessibility caveats |
| **C. Keep current colors, add a separate needs-you badge** | Nothing retrains | Two glyphs to parse per session; the reported confusion remains |

**Recommended: A.** Post-PR-#33 this is a recoloring of an already-honest partition. Turn
mechanics move one level deeper (hover title / detail view), per progressive disclosure.

### D4 — Completed decay (event-based only; never a timer)

| Option | Pros | Cons |
|---|---|---|
| **A. Feed-open marks shown completed cards "seen"; seen cards collapse on the NEXT build** (never under the cursor — the cards-move rule) | Simple, honest event; no scroll bookkeeping | A phone glance counts as seen; multi-device forces a choice (seen-anywhere vs per-browser) |
| **B. Viewport-seen** (card actually scrolled into view) | Closest to "actually saw it" | IntersectionObserver bookkeeping; per-device state; saw ≠ read anyway |
| **C. One-click "sweep"** (collapse everything seen/older) | Zero surprise; trivially event-based | Manual again — the landfill returns if never clicked (though one click beats forty checkboxes) |
| **D. Goal-scoped rollup, no seen-tracking** — completed cards always group under their goal as one `goal — N done ✓` line; a closed goal collapses fully; goal-less cards get an "other ✓" bucket | No seen semantics at all; matches how outcomes are actually thought about; counts preserved; pure event (verdicts + goal closes) | A long-lived goal still accumulates until it closes |

**Recommended: D as the backbone, A layered on** (feed-open collapses card bodies into the
rollup lines), C's sweep as escape hatch. Multi-device: seen-anywhere-is-seen — it is one
human; honesty beats per-screen state.

### D5 — What pushes

| Option | Pros | Cons |
|---|---|---|
| **A. Asks push immediately; desk items badge only** | Pushes stay rare and meaningful — the false-interrupt rule enforced by construction | Desk items can rot silently (badge count mitigates) |
| **B. Both push, styled differently** | Nothing missed | Push fatigue kills the channel for both |
| **C. Asks push; a desk item pushes only at a meaningful event** — e.g. it is the LAST thing between a goal and done ("everything else finished; only your review remains") | That moment genuinely is push-worthy | More machinery; not even definable until D4's goal grouping exists |

**Recommended: A now; C later** once goal rollups exist to define "last thing standing."

## Phases (each one PR-sized, independently shippable, reversible)

1. **The split, visible** — D1-A judge field + D1-B prompt line + D2-A grouped column with
   inline-answerable asks.
2. **Completed stops being a landfill** — D4-D goal rollups + D4-A seen-collapse + sweep.
3. **Pip recoloring** — D3-A, deliberately last so the new meanings land on an already-calmer
   board rather than amid other motion.
4. **Desk-item push nicety** — D5-C, only if phases 1–2 prove out.

Dependencies: 4 needs 2; everything else severable. À la carte is fine.

## Design tripwires (from the repo's standing rules — restated so this plan can't drift)

- Every state that latches (seen, ask-vs-desk verdict) latches until a DECIDING event; no
  per-build re-derivation from flapping inputs, no grace periods, no age thresholds.
- A card may move only on new information; collapses happen on the NEXT build after the
  user's own gesture, never mid-read.
- Injected prompt copy stays in the person's voice: no card/board/column/desk nouns in
  anything a session reads.
- The judge's new field is filed from evidence, with the arm-time/moot-retire guards every
  other card-moving writer follows.
- Any example content in tests/fixtures uses the neutral demo domain (a `notes-api` project
  with `web`/`api`/`tests` sessions) — never real session or goal names.

## Explicitly out of scope

- The blocked/API-error red family, compacting teal, and dead-lane treatments (taxonomy for
  FAILURE states is untouched — this project is about the attention split of healthy states).
- The tab bar's plain-tab-means-ready convention and timeline dead lanes beyond the D3
  recoloring (flagged in PR #33's report as adjacent questions; decide there if D3 proceeds).
- Any change to what the judge considers "blocked" at all — only how a blocked-on-you verdict
  is subdivided and rendered.
