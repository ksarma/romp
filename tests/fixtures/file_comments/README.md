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
- `figures.md`: a note with embedded figures, for the region comments of
  `tools/file-comments-host-regions.test.mjs`: two embeds of `figs/latency.png` (so two comments
  name one distinct src), one of `figs/errors.png`, a web URL, and `../../shared/banner.png`, a
  path above the project root that the host must refuse. The figures themselves are tiny PNGs the
  test generates from bytes at run time; no image file is committed here.
- `tiny-png.mjs`: that generator (`tinyPng(r, g, b)`, a valid 2x2 RGBA PNG whose bytes follow
  from the color, so a second color is "the figure was regenerated") and the `sha256` the tests
  compare the host's hashes against. Not a fixture file itself; imported by the node tests.
- `sidecar-v4.json`: a sidecar from a newer format version; every verb refuses it unchanged.
- `sidecar-corrupt.txt`: a truncated sidecar; every verb refuses it unchanged.
