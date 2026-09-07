# file_comments fixtures

Synthetic inputs for `tools/file-comments-host.test.mjs` (the `notes-api` demo world; no real
session data). The test copies these into a scratch directory and builds the `.trackchanges/`
layout there at run time: no `.trackchanges/` directory is committed under `tests/fixtures/`,
because the vendored guard hook treats one as a project root and would then deny raw edits to
these files in any session that has the tooling installed.

- `report.md`: the commented file. It carries a unique passage (`cut p95 latency by 40%`), a line
  repeated four times whose 24-character surroundings differ (`retry on timeout`, so the engine
  places the selected one by context), and a sentence repeated twice with identical surroundings
  (`Ship it.`, the tie the host refuses as `anchor-ambiguous`).
- `index.md`: a note whose whole-line `[[docs/report]]` link makes `docs/report.md` inherit
  tracking when `index.md` is tracked.
- `sidecar-v4.json`: a sidecar from a newer format version; every verb refuses it unchanged.
- `sidecar-corrupt.txt`: a truncated sidecar; every verb refuses it unchanged.
