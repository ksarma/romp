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
obsidian/src/track-cm.js  obsidian/src/track-logic.js  obsidian/src/track-rollup.js  obsidian/src/track-snapshot.js
```

Not vendored: upstream's tests other than the guard's, its README, its installer, the Obsidian
plugin's other modules, and the VS Code host.

`obsidian/src/track-snapshot.js` is vendored pristine as a CITATION, not as code romp runs: it is
the source of `ui/webview/track-decorations.ts`, a derived module romp maintains (the plan, Slice 5),
which adapts its inline-overlay decorations block (lines 442-790 at the pin) to the romp editor. That
module's header names the source, the pin, and every departure. Nothing bundles or imports the
vendored file itself; it is here so the derivation can be diffed against exactly what it derives from,
and so a re-vendoring shows what upstream changed in the block.

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
| `0005-skill-decisions-only-message.patch` | yes | The skill says a `[obsidian-diff]` message may carry only the reviewer's accept and reject decisions on earlier changes, with no comment and no thread id to reply into, so an agent does not look for one. |
| `0006-skill-plain-track-edit-no-comment-link.patch` | no (romp-only) | The skill tells the agent to make every edit with plain `track-edit`, never `track-edit --thread <id>`, and to answer a comment in words with `track-reply --thread <id>`: an edit linked to a comment is shown inside the comment rather than as its own change, which the reviewer found confusing (decision 42 in `plans/file-review.md`). Other hosts keep the fold, so this stays romp's. |
| `0007-skill-no-bash-writes-commit-the-folder.patch` | yes | The skill says a tracked file is never written through Bash either (no `cp` or `mv` over it, no `tee`, no `>` or `>>` redirection, no `sed -i` or `perl -i`, no python or node write), that every write goes through `track-edit`, and that `track-config`'s exit code is checked as a step of its own, never in a compound command with the write (its 0 means ON, so `&&` runs the write on the tracked file: the dry-run finding behind decision 47 in `plans/file-review.md`); and it asks the agent to include the `.trackchanges/` folder in a commit of its work when the project has one and does not ignore it (decision 48). |
| `0008-store-lock-one-writer-per-sidecar.patch` | not yet (offerable; held by the standing word of 2026-09-11 to open nothing new upstream) | `store-io.mjs` gains `withStoreLock(storePath, fn)`, one lock per sidecar (`<sidecar>.lock` holding `pid ts` and, from a pid namespace other than the initial one, a second line `ns <inode>` naming it; taken with O_EXCL, retried for up to 2 s, released in `finally`; a dead writer's lock is broken, its pid judged only by a reader in the pid namespace that stamped it, and so is a lock whose stamp is more than 15 s from the reader's clock, behind or ahead; an entry at `.trackchanges`'s name that is not a directory is refused at once, held false, naming it), and `track-edit`, `track-comment` and `track-reply` take it around their load-to-rename, so a writer arriving mid-write waits for the other's rename instead of erasing it (one write in five was lost at a 4 to 20 ms stagger, measured 2026-09-09); a lock not obtained prints one plain line and exits 1 with nothing written. Their `fail()` throws to the entry point instead of exiting on the spot, so the lock is released on a failure. On disk the lock leaves three things under `.trackchanges/`, and nothing else: the lock, for the length of a write; while a stale lock's break runs, a second transient name beside it, `<sidecar>.lock.break`, the claim the breakers serialize on so that one of them removes the dead lock and none removes the fresh lock that replaces it (the breaker removes its claim when the break ends; a dead breaker's claim is removed by the next waiter under the lock's own dead-or-stale test); and one line, `made-dir`, appended to another writer's lock or claim. That line is the one thing the lock writes into a file it did not create: the lock makes the `.trackchanges/` folder when a first write finds none, and the maker removes it again at release when nothing else landed in it, so a refused first write leaves no trace; a maker that finds other writers' locks or claims in the folder appends the line to each of them instead, and their holders (or, for a holder that dies, the breaker of its lock) take the folder away at their own release, the last one out removing it. romp's host takes the same lock (`tools/file-comments-host.mjs`, `underStoreLock`; decision 49 in `plans/file-review.md`). |

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
