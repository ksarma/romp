# plans/ — design documents

Two kinds of document live here, and **each file's status header says which it is**:

- **Shipped design history** (most files): the work landed, and the doc records the
  *why* — the incident that motivated a mechanism, the alternatives weighed, what the
  plan got wrong and how scrutiny corrected it — context that the final code and its
  tests no longer show. Don't treat file paths or line references inside them as
  current; they describe the repo as it was when the work landed.
- **Proposed queue entries** (status `PROPOSED, NOT COMMITTED`): potential projects the
  user has deliberately parked to revisit — nothing in them is scheduled, and nothing
  should be built from them unbidden. Currently: `cards-attention-rethink.md` and
  `nudge-awaiting-lift-race.md` (which the user has since ruled are one project — a
  wait-taxonomy — to be re-planned together when revived), and `file-browser.md`
  (commissioned 2026-08-14; awaiting the user's build call and its open questions).

Living architecture references (the event model, the read side) live in `docs/`
instead — see `docs/architecture.md`.
