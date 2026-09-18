# hooks/ — Claude Code hooks

Shell hooks that romp registers with Claude Code (see `install.sh`). They are
the event-driven glue between a running session and the rest of romp — each
fires on a Claude Code lifecycle event for romp sessions, which a hook that acts
only for them identifies by `ROMP_SID` (the id the kernel's SDK backend gives
every session it launches); none of them poll. None records a session's state:
the SDK backend writes the `states/<sid>.jsonl` rows itself.

| Hook | Event | What it does |
|---|---|---|
| `romp-wake.sh` | turn end / prompt / compaction end | Wakes the kernel — the judges and the parked-op drain — when an event creates new work for them (event-based over time heuristics, by design). |
| `romp-postal-ensure.sh` | SessionStart | Makes sure the postal bus is running (async, singleton). |
| `romp-postal-context.sh` | SessionStart | Gives a romp session a compact pointer to the postal skill (not the full skill body). |
| `romp-postal-drain.sh` | Stop | Delivers queued peer mail at turn end, so mail never interleaves with a working turn. |
| `romp-postal-revive.sh` | SessionStart | On revival with unread mail (a parked handoff), makes the session act on that mail. |
| `romp-usertodo-context.sh` | SessionStart | On resume/compact, re-hands a session its open user todos as passive context, so it withdraws the moot ones after its working memory is wiped. Silent while the user-todos switch is off (the gear's User todos checkbox; off by default). |
| `romp-track-bash-guard.mjs` | PreToolUse on `Bash` | Refuses a shell command that would write a tracked file (cp, mv, install and tee targets, `>` and `>>` redirections, `sed -i` and `perl -i` files, a path a python or node one-liner opens for writing; a glob, a brace list or a symlink read as the shell and the kernel would), resolved against the session's cwd and judged by the project's `.trackchanges/config.json`, and points the session at track-edit. A read passes; a command it cannot read through (eval, xargs, a script held in a variable) passes; a write whose target the shell fills in (a variable, a substitution, a glob or brace list it cannot expand) is refused when the session's directory sits in a project that tracks a file the rule could refuse, or when a copy's landing folder is one a tracked file could land in (since 2026-09-18, after a `cp` built from variables landed raw beside a refused literal one; bounded by the round-1 review the same day and corrected by round 2: a target whose only expansions are `$$`, or `$RANDOM` and `$SECONDS` where the shell running it keeps them read-only (bash and zsh; not inside a script handed to `sh`, and `$BASHPID` nowhere, since zsh lets a command assign it), at an absolute path outside every project in play is allowed, the project its own prefix sits in asked first; a leading `$HOME/` is read as `~/` is, a directory is judged under its real path and its name, and the environment's root override counts only for a directory under it; a `$(date)` in a log's name is still refused, and of the environment the hook reads `HOME`, `TRACKCHANGES_ROOT` and `ROMP_SID`, never a variable the command names, and only HOME's value can appear in a refusal, as a path resolved through it); it does nothing in a session romp did not start. Closes the write path the vendored guard below never sees (`plans/file-review.md`, decision 47). Tests: `tools/romp-track-bash-guard.test.mjs` (the grammar and the process) and `tools/romp-track-bash-guard-shapes.test.mjs` (the shapes the review found misread). |

Beside these, `install.sh` links the agent-side tooling for file comments and
tracked changes into `~/.claude/hooks/`: the `track-edit`, `track-comment`,
`track-reply` and `track-config` commands, and `track-guard.mjs`, registered as
a PreToolUse hook on `Write|Edit|MultiEdit` that refuses a raw write to a
tracked file and does nothing in a session romp did not start (romp's own
`romp-track-bash-guard.mjs` above does the same for a write made through the
Bash tool). Their source is
not this directory but `vendor/track-changents/`, a pinned copy of
track-changents; fixes to it are patches under `vendor/track-changents/patches/`,
offered back to its author (see the README there).

Disable the postal hooks with `~/.claude/romp-postal-off`. Shell tests:
`tests/*.bats` (`romp-wake-hook.bats`, `romp-postal-context.bats`, …) — keep
them GNU/BSD-portable, CI runs on Linux.
