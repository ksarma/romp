# plans/ — design documents

Three kinds of document live here, and **each file's status header says which it is**:

- **Shipped design history** (most files): the work landed, and the doc records the
  *why* — the incident that motivated a mechanism, the alternatives weighed, what the
  plan got wrong and how scrutiny corrected it — context that the final code and its
  tests no longer show. Don't treat file paths or line references inside them as
  current; they describe the repo as it was when the work landed.
- **Proposed queue entries** (status `PROPOSED, NOT COMMITTED`): potential projects the
  user has deliberately parked to revisit — nothing in them is scheduled, and nothing
  should be built from them unbidden. Currently: `cards-attention-rethink.md` and
  `nudge-awaiting-lift-race.md` (which the user has since ruled are one project — a
  wait-taxonomy — to be re-planned together when revived), and `boot-visibility-card.md`
  (parked 2026-08-15 as a long-term consideration; its notes on the boot reconcile's
  existing recovery behavior are current as of filing).
- **A plan built and awaiting its acceptance walk** (status `BUILT`): `file-review.md`, file
  comments and tracked changes in the file viewer, approved 2026-09-06 and built as six stacked
  fork PRs by 2026-09-07; it moves to shipped design history once the user completes the
  end-to-end walk its decision 29 names.

Living architecture references (the event model, the read side) live in `docs/`
instead — see `docs/architecture.md`.
