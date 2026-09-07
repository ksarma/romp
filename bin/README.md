# bin/ — the command surface

`bin/` is the stable **entry-point surface**: every runnable romp command lives
here (put it on `$PATH`: `export PATH="$PATH:<repo>/bin"`). The Python
*implementations* live in the logical source folders — `kernel/`, `postal/`,
`cli/` — and the corresponding bin entries are **symlinks** to them, so external
consumers (launchd/systemd, tmux glue, hooks, the MCP config, remote kernels)
keep stable paths while the code stays navigable by component. `ls -l bin` is
the live map of that indirection.

Only the shell/Node launch glue is a real file here — it *is* the command, with
no separate implementation to point at.

## Real files (launch chain + shell commands)

`romp-service` (login agent) → `romp-node-launch` → `romp-manager` →
`romp-serve` → `kernel/kernel.py`.

| File | Lang | What it is |
|---|---|---|
| `romp` | Bash | The launcher/dispatcher: start/resume/attach sessions, `-d`/`-f`/`-j` terminal views, `--on/--refresh/--status`, `--mail`, `update`, `--version`. Also provisions the tmux server glue when using the tmux backend. |
| `romp-service` | Bash | Installs/removes the launchd (macOS) / systemd-user (Linux) login agent, and stops/starts it (`stop`/`start`: the supervisor halves of `romp down` / `romp up`; `stop` exits 3 when none is installed and 4 when one is installed but not running). Run by `install.sh`. |
| `romp-node-launch` | POSIX sh | Runs the manager under a romp-owned copy of node (`romp-node`) so macOS TCC permissions can be granted to romp alone. |
| `romp-manager` | Node | The kernel **supervisor**: spawns kernels via `romp-serve`, respawns on crash, `up/ensure/restart-all/status/down`. Reached via `romp up` / `romp refresh` / `romp status`, and by `romp down`, which probes it after the service stop and stops one still answering through `down`. `ensure` holds while a `romp down` marker exists; `up` clears it. |
| `romp-serve` | Bash | The manager→kernel seam: maps the manager's spawn contract onto the kernel's env, picks the python, then `exec`s the kernel (PID preserved for the supervisor; the kernel self-builds stale UI bundles). |
| `romp-cli-scope` | POSIX sh | Linux + systemd only: the kernel spawns each session's `claude` CLI through it, and it `exec`s `systemd-run --user --scope` in place, so the CLI (and every tool shell, `setsid` child and tmux server it later starts) runs in a transient scope of its own instead of the manager service's cgroup, which a service restart empties. PID, parent and argv preserved. `ROMP_CLI_SCOPE=0`, or no `ROMP_SID` (a probe, not a session), runs the CLI directly. So does a failed pre-flight scope, with one stderr line saying why, which the kernel logs as a problem at once and counts (`/api-health` `cliScope.fallbacks`). Opt-in per-session limits: `ROMP_CLI_SCOPE_MEMORY_MAX` / `_MEMORY_HIGH` / `_MEMORY_SWAP_MAX` become `-p MemoryMax=` / `MemoryHigh=` / `MemorySwapMax=` on the scope (with `OOMPolicy=continue`, so one OOM kill takes one process, not the scope), and `ROMP_CLI_SCOPE_OOM_SCORE_ADJ` is written to the wrapper's own `oom_score_adj` before the exec; a value it refuses, a property systemd rejects, or an adjustment that parses but Linux will not let it write, is skipped with one `romp-cli-scope: ignored:` stderr line each, logged and counted by the kernel (`cliScope.limitsIgnored`, lines not launches), and the CLI still starts in its scope; the kernel runs the same steps once at its start, so a refusal by the machine lands in `cliScope.rejected` instead of repeating per launch. |
| `romp-sdk-setup` | Bash | Provisions the Agent SDK venv for the SDK backend. Run by `install.sh`. |

## Symlinks → `kernel/` (the always-on core)

| Command | Source | What it is |
|---|---|---|
| `romp-kernel` | `kernel/kernel.py` | **The** kernel: parses transcripts into the event tree, runs the judges, serves chat/feed/fleet/timeline over HTTP+WebSocket on `127.0.0.1:29855`. Spawned by `romp-serve`. |
| `romp-event-model` | `kernel/event_model.py` | Layer 1: transcript → event tree (atoms/segments/turns). Loaded by the kernel and the judges. |
| `romp-judge` | `kernel/judge.py` | Layer 2: the judge engine + all judge prompts (captioner, archiver, planner, …). `docs/judges.md`. |
| `romp-askparse` | `kernel/askparse.py` | Parses the AskUserQuestion picker out of a captured tmux pane (tmux backend only; SDK sessions get the picker natively). |
| `romp_sdk_backend.py` | `kernel/sdk_backend.py` | The **SDK session backend** (current default): drives sessions via the Claude Agent SDK. |
| _(no bin entry)_ | `kernel/keysource.py` | The live source of the manager's API key where an installation keeps one in `service.env`: its `ANTHROPIC_API_KEY=` line, re-read at every session launch (file mode). Shared by the kernel and `romp keyswap`'s report, so the two cannot disagree about the path or the parse. This fork writes no key line (the named swap is refused in file mode). |
| _(no bin entry)_ | `kernel/envsource.py` | The second key source, for installations that keep credentials out of files: with `ROMP_CREDENTIAL_COMMAND` set the kernel runs that command (the selector file's token as `$1`) and hands the `NAME=VALUE` set it prints to each session CLI, judge call and catalog fetch, never to its own environment or a file. Value-free everywhere but one accessor; fingerprints are the only rendered form. `romp keyswap` and `romp-service status` read the same module's configuration. |
| `romp_session_backend.py` | `kernel/session_backend.py` | The `SessionBackend` ABC — the one seam both backends (SDK, tmux) implement. |
| `romp_colormap.py` | `kernel/colormap.py` | The recency colormaps, single source of truth shared with the web bundles. |
| `romp_palette.py` | `kernel/palette.py` | The session-identity color palettes. |

## Symlinks → `postal/`

| Command | Source | What it is |
|---|---|---|
| `romp-postal-service` | `postal/postal_service.py` | Inter-session mail: MCP server + CLI (`romp mail`). `romp-postal` is a symlink alias. |

## Symlinks → `cli/` (terminal tools)

| Command | Source | What it is |
|---|---|---|
| `romp-update` | `cli/update.py` | Pushes this machine's committed romp to attached remote kernels and restarts them (`romp update [host]`). |
| `romp-version` | `cli/version.py` | Version report across the moving parts (`romp version`). |
| `romp-keyswap` | `cli/keyswap.py` | Reports which API key the sessions bill (fingerprints only) and whether the kernel reads what the shell reads; with `ROMP_CREDENTIAL_COMMAND` set, `romp keyswap <name>` selects a declared credential by writing the selector file and `--refresh` makes the kernel re-run the command; after a rotation, `--cycle-all` reconnects quiet running sessions so their new processes pick the new credential up, with no manager restart. Where the key lives in a file, upstream's named swap (a rewrite of `service.env`) is refused: this fork does not write API keys to files. |
| `romp-idle-dots` | `cli/idle_dots.py` | tmux backend only: heals stranded `working` state / fades idle tab dots by inspecting tmux panes. Fired from `hooks/tmux-status.sh`. |

## tmux backend only (real files)

Still wired, only meaningful for tmux sessions. If the tmux backend is ever
dropped, these (plus `romp-askparse`, `romp-idle-dots`, and the tmux glue in
`romp` + dotfiles `tmux.conf`) go with it.

| File | Lang | What it is |
|---|---|---|
| `romp-interrupt-reset` | Bash | tmux Ctrl-C/Esc bind: resets a stuck `working` state (Claude fires no interrupt hook). |
| `romp-mail-clear` | Bash | Clears the postal badge in the tmux status bar on session switch. |
