# hooks/ — Claude Code hooks

Shell hooks that romp registers with Claude Code (see `install.sh`). They are
the event-driven glue between a running session and the rest of romp — each
fires on a Claude Code lifecycle event; none of them poll.

| Hook | Event | What it does |
|---|---|---|
| `romp-wake.sh` | turn end / prompt / compaction end | Wakes the kernel — the judges and the parked-op drain — when an event creates new work for them (event-based over time heuristics, by design). |
| `romp-summarize.sh` | turn events | The announcer: writes a short live phrase to the `@claude-summary` tmux var that status lines and dashboards render. Display-only. |
| `tmux-status.sh` | status events | The passive status pipe serving both backends: membership, `working`/idle state, `@romp-session-id` re-anchoring after `/clear` forks. Never spawns or toasts. |
| `romp-postal-ensure.sh` | SessionStart | Makes sure the postal bus is running (async, singleton). |
| `romp-postal-context.sh` | SessionStart | Gives a romp session a compact pointer to the postal skill (not the full skill body). |
| `romp-postal-drain.sh` | Stop | Delivers queued peer mail at turn end, so mail never interleaves with a working turn. |
| `romp-postal-revive.sh` | SessionStart | On revival with unread mail (a parked handoff), makes the session act on that mail. |
| `romp-usertodo-context.sh` | SessionStart | On resume/compact, re-hands a session its open user todos as passive context, so it withdraws the moot ones after its working memory is wiped. Silent while the user-todos switch is off (the gear's User todos checkbox; off by default). |
| `romp-track-bash-guard.mjs` | PreToolUse on `Bash` | Refuses a shell command that would write a tracked file (cp, mv, install and tee targets, `>` and `>>` redirections, `sed -i` and `perl -i` files, a path a python or node one-liner opens for writing), resolved against the session's cwd and judged by the project's `.trackchanges/config.json`, and points the session at track-edit. A read passes; a command it cannot read through passes; it does nothing in a session romp did not start. Closes the write path the vendored guard below never sees (`plans/file-review.md`, decision 47). Tests: `tools/romp-track-bash-guard.test.mjs`. |

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
`tests/*.bats` (`romp-wake-hook.bats`, `tmux-status-hook.bats`,
`romp-postal-context.bats`, …) — keep them GNU/BSD-portable, CI runs on Linux.
