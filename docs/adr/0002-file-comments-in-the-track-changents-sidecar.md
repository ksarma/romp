# File comments and changes live in the track-changents sidecar, plus a romp-only comments log

Status: accepted (2026-09-06), with Slice 1 of `plans/file-review.md`

A file comment or a session's tracked change is stored in the format the track-changents tools
already read and write: one JSON sidecar per file under the project's `.trackchanges/` folder,
version 3, byte for byte, with one optional additive field for image and PDF regions. Beside it,
romp keeps an append-only comments log of its own that records what was sent to a session, what
was accepted or rejected, when tracking was toggled, and the person's direct edits. We chose this
over a storage format romp designs itself because the agent side of the loop (the CLIs a session
runs, the guard hook that keeps it from writing tracked files raw, and the skill that tells it
what to do) exists and works today in that format, and because two other editors read the same
files; a second implementation of a cross-tool contract is where shared files get corrupted. The
cost is that romp cannot add fields to the sidecar freely, so anything the sidecar forgets, and
it forgets every accepted or rejected change and deletes itself when a file has nothing pending,
must live in the second file.

## Considered options

- **A romp-owned schema.** Rejected: it means rewriting the agent-side tooling and losing the
  other editors for no capability the user named. The user said compatibility was chosen because
  it seemed easier for everyone and would not be defended if it were a bad design; it is the cheap
  path and stays cheap now that the code is vendored under romp's control.
- **Extending the sidecar with romp fields instead of a second file.** Rejected: the format's own
  rule permits additive fields, but a log grows without bound and would be rewritten on every
  save by every host that writes the whole object back; an append-only file with one writer is
  the right shape for a record.

## Consequences

- The vendored copy of track-changents in this repo is the code that reads and writes the
  sidecar; romp's fixes to it are offered back to its author rather than forked silently.
- The comments log is outside the contract: the other editors never read it, and romp's panel is
  its only reader. What is unsent is derived from it on the owning kernel, so no comment state
  lives in a browser.
- A later change to the storage format is a change to files sitting in users' projects, and to
  three editors at once; it should come with a version bump under the format's own gating rule.
- Under that rule the sidecar now carries three additive fields on a comment, `target` (a region),
  `anchorAt` (the offset at which a passage comment's anchor was located; the anchors follow-on,
  2026-09-07) and `changeIds` (the changes the comment is about, by id, the person's own pick; the
  about follow-on, 2026-09-10); all are romp-only, ignored by older readers, and written back
  whole by the other editors. romp never writes the format's own `suggestionId`, the key the other
  editors set on a comment their change answers, and reads one it finds as the change that answered
  the comment.
- Since 2026-09-11 one transient file sits beside a sidecar, or beside `config.json`, for the length
  of a write: `<name>.lock`, holding the writer's pid and a timestamp (and, from a pid namespace
  other than the initial one, a second line naming that namespace). The vendored CLIs and romp's
  host take it around their load-to-rename, so a writer arriving mid-write waits for the other's
  rename instead of erasing its write (vendor patch 0008; decision 49 in `plans/file-review.md`).
  It is broken when its writer is dead or it is older than fifteen seconds, or its stamp is that far
  ahead of the reader's clock, and it is removed when the write ends. The pid is judged only by a
  reader in the pid namespace that stamped it (pids are per namespace); any other lock is judged by
  its stamp's age alone. Breaking it leaves a second transient name while the break runs,
  `<name>.lock.break`: the claim its waiters serialize on, so that one of them removes the dead lock
  and none removes the fresh lock that replaces it. The breaker removes its claim when the break
  ends; a claim whose breaker died is removed by the next waiter, under the same dead-or-stale test
  as the lock. The lock also makes the `.trackchanges/` folder when a first write finds none, and
  removes it again when nothing else landed in it. A maker whose release finds only other writers'
  locks or claims in the folder appends one line, `made-dir`, to each of them: their holders (or,
  should a holder die, the breaker of its lock) take the folder away at their own release. That
  line is the one thing the lock writes into a file it did not create. Both names are outside the
  format (neither ends in `.json`, so no host reads them as a sidecar), and the two names and the
  line are everything the lock leaves under `.trackchanges/`.
- A romp-only field is read defensively wherever it is read: the sidecar is JSON anyone can edit,
  and a field of the wrong shape must claim nothing rather than fail the panel.
