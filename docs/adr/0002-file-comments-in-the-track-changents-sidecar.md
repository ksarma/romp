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
