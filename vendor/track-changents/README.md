# Vendored track-changents

This directory holds a pinned copy of the MIT-licensed track-changents core, the code that reads
and writes the `.trackchanges/` sidecar format romp's file comments and tracked changes live in
(see `plans/file-review.md`, Vendoring, and `docs/adr/0002`). romp imports the node modules from
here (the host script `tools/file-comments-host.mjs`), bundles the browser modules from here, and
`install.sh` links the CLIs, the guard hook, and the skill from here into `~/.claude/`, so nothing
in the loop depends on a track-changents install.

## Pin

- Upstream commit: `320cd25fda6fe218481fbf08fa5cfb4670404c96` (2026-09-03).
- Files: every file below is the upstream file at that commit, byte for byte, with the patches
  under `patches/` applied in order (none yet).

```
package.json  engine.js  display.js  protocol.js  store-io.mjs  LICENSE
cli/cli-args.mjs  cli/track-comment.mjs  cli/track-config.mjs  cli/track-edit.mjs  cli/track-reply.mjs
hooks/track-guard.mjs  hooks/track-hooks.test.mjs
skill/SKILL.md
obsidian/src/track-cm.js  obsidian/src/track-logic.js  obsidian/src/track-rollup.js
```

Not vendored: upstream's tests other than the guard's, its README, its installer, the Obsidian
plugin's other modules (`track-snapshot.js` is taken up by Slice 5 of the plan, which is its only
consumer), and the VS Code host.

## Patches

One file per edit under `patches/`, applied at vendoring time and listed here with the reason.
Patches that fix an upstream defect are offered back to the author; patches that are romp's own
are marked so.

(none yet)

## Re-vendoring

Check out the upstream commit, copy the files listed above over this directory, re-apply the
patches in order, and update the pin. The drift test (`tools/vendor-drift.test.mjs`) fails when a
vendored file differs from pin-plus-patches, and when a track-changents checkout is present on the
machine at an older commit than the pin.
