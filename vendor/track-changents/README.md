# Vendored track-changents

This directory holds a pinned copy of the MIT-licensed track-changents core, the code that reads
and writes the `.trackchanges/` sidecar format romp's file comments and tracked changes live in
(see `plans/file-review.md`, Vendoring, and `docs/adr/0002`). romp imports the node modules from
here (the host script `tools/file-comments-host.mjs`), bundles the browser modules from here, and
`install.sh` links the CLIs, the guard hook, and the skill from here into `~/.claude/`, so nothing
in the loop depends on a track-changents install.

## Pin

- Upstream commit: `320cd25fda6fe218481fbf08fa5cfb4670404c96` (2026-09-03).
- `PIN.json` holds the sha256 of every vendored file as it was at that commit, before any patch.
- Every file below is the upstream file at that commit with the patches under `patches/` applied
  in order. Nothing else is edited in place: a change to a vendored file is a new patch.

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

One file per edit under `patches/`, numbered in the order they apply. Each starts with a header
comment giving the reason, the files it touches, and whether it is offered back to the author or
is romp's own. `tools/vendor-drift.test.mjs` checks the headers, the order, and that the series
reproduces both the pin (reversed) and the vendored files (forward).

| Patch | Offered back | What it does |
|---|---|---|
| `0001-a1-revive-into-live-store.patch` | yes | A reply (`track-reply`) or an edit (`track-edit --thread`) into a comment the live sidecar lacks revived it from the `.superseded` park by saving a fresh store with an empty change list over the sidecar, erasing every pending change and every other comment (survey item A1). Adds `reviveThreadInto` to `store-io.mjs` and makes both CLIs revive into the live store. |
| `0002-non-text-refusal.patch` | yes | `track-edit` refuses a file that is not text (an image, PDF or other binary by name; NUL bytes or invalid UTF-8 by content) with a clear message and no write, instead of rewriting it from a lossy decode. The guard passes such a file through to the raw tools rather than steering the agent to `track-edit`. Adds `isNonTextPath` and `hasNulBytes` to `store-io.mjs`; the guard test gains the cases. |
| `0003-skill-several-comments-another-look-stale-text.patch` | yes | The skill says a message may list several comments on one file, tells the agent how to ask for another look, and describes what `track-edit` does with stale text (it usually detaches the displaced changes and proceeds; it refuses only a change that is seconds old). |
| `0004-romp-guard-exits-without-romp-sid.patch` | no (romp-only) | The guard exits 0 at once when `ROMP_SID` is absent from its environment, as the first statement of its `if (invokedDirectly)` block, before stdin is read, so a guard registered machine-wide is inert in every session romp did not launch. `evaluate()` and its unit tests are unchanged; two process-level cases are appended to the guard test. |

Behaviour tests for the offered-back patches, run as an agent would run the CLIs, live in
`tools/vendor-patches.test.mjs`; each case fails against the pristine upstream files.

## Re-vendoring

1. Check out the new upstream commit and copy the files listed above over this directory.
2. Recompute `PIN.json` from those pristine files, exactly as they are at that commit, and update
   the commit in it and here. Where a checkout is present the drift test reads that commit's own
   blobs and compares them with the hashes, so a pin minted from a dirty working tree is caught.
3. Re-apply `patches/*.patch` in order (`git apply --directory=vendor/track-changents` from the
   repo root, or `git apply` from this directory). A patch upstream has since taken can be
   deleted; renumber the rest.
4. Run `node --test tools/vendor-drift.test.mjs tools/vendor-patches.test.mjs
   vendor/track-changents/hooks/*.test.mjs`.

The drift test fails when a vendored file differs from pin-plus-patches, when a patch no longer
applies, and, where a track-changents checkout is present on the machine
(`$TRACKCHANGENTS_CHECKOUT`, else `~/code/track-changents`), when that checkout is behind the
pin or when `PIN.json`'s hashes are not the pinned commit's own blobs (the commit was bumped
without re-hashing, or the pin was minted from a working tree that was not exactly that commit).
