# Reference

This page lists every command and knob. It is here for driving Romp from the
terminal, for scripting against it, and for debugging: you do not need any of it
for ordinary use, where the user interface covers everything. Everything here
runs on the machine that hosts the kernel.

## The `romp` command

Run `romp` on its own and it opens the dashboard, which is all most days need.
Every other command is a bare word after it, and a session's name is always an
argument rather than the command itself, so the two can never collide: `romp new
update` starts a session called "update".

| Command | What it does |
|---|---|
| `romp` | Open the dashboard in your browser, printing the tokened link too |
| `romp new <name>` | Start a session, run by the kernel and watched from the dashboard |
| `romp new -d <dir> <name>` | Start it in `<dir>` instead of the current folder |
| `romp new -t <name>` | Start it as a terminal (tmux) session and attach; add `--detach` to leave it running |
| `romp resume` | Resume a past conversation, chosen from a full-screen picker |
| `romp status` | Manager and kernel status |
| `romp refresh` | Restart the postal bus and every kernel immediately, picking up new code (cut turns resume with their history) |
| `romp update [host…]` | Push this machine's committed Romp to attached remotes and restart them |
| `romp up` | Run the kernel manager in the foreground; rare, since the login service runs it |
| `romp version` | Version report across the moving parts |
| `romp keyswap [<name>] [--cycle <session,…>\|--cycle-all]` | Switch which API key the sessions bill, with no restart: rewrites only the `ANTHROPIC_API_KEY=` line of `service.env` from `service.env.<name>`, and `--cycle` moves running sessions onto it. Bare, it reports the live key and the candidates. See [Switching which API key the sessions bill](#switching-which-api-key-the-sessions-bill-romp-keyswap) |
| `romp help` | The same list, from the terminal |

These are for scripting and for agents rather than daily use:

| Command | What it does |
|---|---|
| `romp url` | Print only the tokened dashboard URL, for piping |
| `romp sessions [--json]` | The fleet with each session's state, identity colours, directory and backend |
| `romp mail …` | The postal service from the shell (below) |
| `romp send <session> [--tag <label>] <text>` | Hand a session a message, on either backend. Anything a script, cron job, or launcher composes SHOULD carry a tag (one word, letters/digits/dashes, up to 24 chars): the chat then renders it as machine-sent under that label instead of as the user's typed words. Raw POST /send callers pass it as the JSON `tag` field (`{name, text, tag}` — a malformed tag fails the whole send, loudly); `--tag` is the CLI's equivalent. Both resolve to the `<!-- romp-tag: <label> -->` marker in the delivered text |
| `romp new --env NAME=VALUE <name>` | A per-session env var for the SDK session, repeatable; a re-run against a running `<name>` replaces the whole set — vars not re-named are dropped |
| `romp new --no-env <name>` | Clear a running SDK session's per-session env (declares the empty set) |
| `romp interrupt <session>` | Interrupt whatever turn a session is taking |
| `romp compact <session> [--wait] [--timeout <s>]` | Compact a session's context in place (Claude's `/compact`: summarize the history, keep the session's name, id, mailbox, and watches) — the alternative to ending and recreating a long-lived session, and the external hand a session needs since it cannot `/compact` itself mid-turn. Quiet session → compacts now; open turn → queued, fires alone the moment the turn ends (the same safe path the chat's compact button uses). `--wait` blocks until the compaction has started and cleared, polling the kernel's own `compacting` signal on the `/sessions` rows (also the field to point a `romp watch` predicate at for scripted recycling); exits 1 honestly on timeout. A remote session's compaction is requested on its own kernel — `--wait` can't follow it from here and says so |
| `romp end <session>` | End a session |
| `romp move <session> <dir>` | Move an SDK session's working directory to `<dir>` (the folder must already exist); the conversation, name, mail and history stay with the session. Quiet session → moves now; open turn → queued, fires when the turn ends. See [Moving a session to another folder](#moving-a-session-to-another-folder) |
| `romp checkin <host>` / `romp checkout <host>` | Publish this machine to an attached hub, or withdraw it |
| `romp default-dir [PATH]` | The default working directory for new sessions; no argument prints it, `""` clears it |
| `romp debug [on\|off\|status]` | Judge debug mode, where rejection rows carry the full input and reply |
| `romp resume <id> [--name <n>] [--detach]` | Resume one exact conversation by UUID |
| `romp refresh --quiet` | Refresh at the next quiet window instead — waits for sessions to finish their turns (15-min backstop) |

`--env` gives one session its own environment, so two sessions in the same
directory can run with different toggles (a `FEATURE_FLAG=1`, a `CLAUDE_CODE_*`
switch) without editing the directory's `.claude/settings*.json`, which reaches
every session there and outlives them all. Re-running `romp new --env` against
a running session declares its full per-session env: any var you don't name
again is dropped, and `romp new --no-env <name>` declares the empty set — it
clears them all. Keep real secrets out of it: each value is copied into
per-session files and the session registry under `~/.local/state/romp/`. Keys
and credentials stay in `service.env` or the `apiKeyHelper`.

Two things to know before building on `romp sessions --json`. **`waiting` means
at rest**, the ordinary state of a session that has finished its turn, so
matching it as an alert badges the whole idle fleet as needing you; the states
that want a person are `permission` and `picker` (a live prompt) and `blocked`.
(`romp sessions` emits the RAW backend states — the dashboard's chip states,
`needsInput`/`awaitingBg`, never appear here.) And
**`id` is the durable key**, not `lastSid`: everything Romp files per session is
keyed by `id`, while `lastSid` is the live transcript's id and forks on
`/clear`.

That key opens the per-session records under `~/.local/state/romp/`. The
per-turn one-liners live in `captions/<id>.jsonl`, one JSON record a line, with
the text under `caption`. A record's own `id` field is not the session's: it
identifies the turn within it. There is no `summaries/` directory; an older
layout had one, and reading it fails silently, since a missing directory just
yields nothing rather than an error.

### Moving a session to another folder

A session's working directory can change after it starts, so when a subproject
moves to its own repository, the session working on it can follow. Right-click
the session's tab and choose **Move to folder…**, or run `romp move <session>
<dir>`. The folder must already exist. Terminal (tmux) sessions cannot be
moved; start a new one in the folder instead.

What moves with the session:

- The conversation. Claude Code moves the transcript, with the tool-results,
  subagent and workflow files beside it, into the new folder's project
  directory under `~/.claude/projects/`; Romp moves the session's earlier
  transcripts (its `/clear` episodes and resume forks) the same way, so history
  and search keep working.
- The session's name, colour, mailbox, goals, cards and captions, all keyed by
  the session id rather than the folder.
- What the agent sees. Claude Code tells the model where it now is and loads
  the new folder's `CLAUDE.md`; from the next turn on, permission rules, hooks,
  skills and project MCP servers come from the new folder.

What does not move, because Claude Code keys it by folder rather than by
session: the old project's auto-memory (`~/.claude/projects/<old
folder>/memory/`), the old folder's entry in `~/.claude.json` (its allowed
tools, MCP approvals and trust), and the old repository's
`.claude/settings.local.json`. A comment thread opened on the session also
keeps its own folder. What Claude Code keys by session id (its debug log, task
store and file-history checkpoints) needs no move.

A move never interrupts a turn: on a session mid-turn it is queued as a chip in
the chat and fires the moment the turn ends, like a queued `/compact`. If Claude
Code reports a turn Romp could not see (one it started itself), the chip waits
for that turn to end too; the chip can be cancelled like any queued item. A
closed session is revived first, in its old folder, then moved. Only one move
per session is in flight at a time; a second request while one is pending is
refused. Every refusal (a folder that does not exist, a path that is a file, a
move already pending) is reported where you asked. If Claude Code's reply to
the move is lost, Romp settles the outcome by where the transcript is, the same
check it runs after a restart that interrupted a move; a move it cannot settle
is reported and left for the next kernel start, with nothing changed.

The move is Claude Code's own relocation (the `set_cwd` control behind the
interactive `/cd`), with Romp moving its own records alongside. It fires Claude
Code's `CwdChanged` hook, not `SessionStart`; Romp registers no `CwdChanged`
hook, so nothing on Romp's side re-runs.

## The Romp Postal Service

How sessions message each other, from either side. Inside a session it is an MCP
server, so an agent calls the tools below directly; from a terminal the same
mailbox is behind `romp mail`. See
[Inter-agent communication](guide.md#inter-agent-communication-the-romp-postal-service)
for what it is for.

### Mail from the terminal

```bash
romp mail send [--kind delegate|coordinate|question] <name> "<text>"
romp mail inbox                  # read your messages, and clear them
romp mail peek                   # read them without clearing
romp mail agents                 # who is live, their branch and working-note
romp mail working "<note>"       # publish what this session is working on
romp mail sent                   # your sent messages, and whether each was read
romp mail recall <to> [id]       # unsend a message the recipient has not read
romp mail remote                 # connect this remote machine to your laptop's bus
```

### Mail inside a session (MCP tools)

| Tool | What it does |
|---|---|
| `send_message(to, body, kind)` | Message a live session by name; `kind` declares delegate / coordinate / question |
| `check_inbox()` | Read messages sent to you (also delivered at the end of each turn) |
| `list_agents()` | The live sessions, each with its branch and working-note |
| `set_working(text)` | Publish what you hold so peers steer clear |
| `check_sent()` | Whether your sent messages were read yet |
| `recall_message(to, id?)` | Unsend a message the recipient hasn't read |

### Claude Code 2.1.224 or newer

Mail to a terminal (tmux) session delivers through Claude Code's per-session
inbox socket, which the CLI added in 2.1.224: delivery is instant and never
touches a half-typed draft. An older Claude Code still works — delivery falls
back to typing the mail into the pane, which is slower and waits for a free
prompt — and `romp` says so at launch, with the upgrade being one
`claude update` away.

## Configuration

### Folder click, in your terminal or editor

The chat statusline shows the session's working directory; clicking it opens
that folder. The default is the OS opener (`open` / `xdg-open`). To open it
elsewhere, set a command via the env var `ROMP_OPEN_FOLDER` or the first
non-comment line of `~/.config/romp/open-folder`; `{dir}` is replaced with
the clicked path (omitted, the path is appended). The command runs on the
kernel's machine.

```bash
# ~/.config/romp/open-folder: pick one line
open -a Ghostty {dir}               # macOS: a new Ghostty window there
ghostty --working-directory={dir}   # Linux: Ghostty
code {dir}                          # VS Code instead
```

### Model and effort, from the statusline or a typed command

Typing `/model X`, `/effort X`, or `/fast on|off` into the chat composer, or
sending one with `romp send`, is the same setting change as a pick from the
statusline's model and effort dropdowns: the kernel takes it through its own
setters, so what it remembers (the value a reconnect relaunches with, the
defaults new sessions start from) follows the switch. A bare `/model` (the
CLI's own picker), a value the kernel cannot vouch for (a typo), or a longer
message that merely opens with the command goes to the CLI verbatim, and the
chat shows the CLI's own reply.

The two backends apply the change differently. An SDK session switches model
live but reloads to apply a new effort: the chat shows "Reloading session…"
and the effort badge shows switching-dots until the reload completes, and a
session that is mid-turn reloads when the turn ends. A terminal (tmux) session
gets the CLI's own command typed into its pane. `/model` there asks for a
confirmation, which the kernel accepts on your behalf so the pane is never
left waiting on a keystroke the dashboard cannot send; `/effort` and `/fast`
apply in place.

### Fast mode, from the chat statusline

The statusline's badges — permission mode, model, effort — are each a small
dropdown. A fourth appears when the session reports Claude Code's fast-mode
state (an Opus-only research preview, billed at a premium): it reads **Fast**
in orange while fast mode is on, **Slow** while it's off, and **Cooldown**
while fast requests are rate-limited. Picking On or Off sends the CLI's own
`/fast` command; the badge never appears on a session that cannot run fast
mode. Turning it on while the session is on a non-Opus model makes the CLI
switch to a fast-capable one, which the chat shows as the command's own
confirmation. If the CLI refuses the toggle (for example, the account has
extra usage turned off), a toast says why and the pick reverts to off —
the control never silently disappears.

### Per-session billing (login vs API key)

An SDK session can bill either the machine's Claude login (subscription usage)
or the `ANTHROPIC_API_KEY` the manager's environment carries — per session.

The new-session picker's **Billing** row states the case whenever the backend
toggle says SDK: segmented buttons when the selected host offers both choices,
and with only one real choice, the same spot simply writes out which applies —
`Login (name@example.com)` or `API key` — so what a session will bill is never
a mystery. A live session additionally wears a statusline badge for
*switching*, beside mode/model/effort, and that control keeps the stricter
rule: it exists only when both choices are real (a one-option selector is
noise). Switching reconnects the session to apply (the key rides the launch
environment), with the same switching-dots the effort badge wears.

The login is named by its account (the email the credential store records);
the key option is labelled plainly `API key` — no fragment of the key, not
even a last-4 tail, ever reaches a browser or a screen. A new session
defaults to the last pick made anywhere, and before any pick to the key when
one is configured — exactly what an ambient key did before the selector
existed. tmux sessions are not covered: their CLI lives in the tmux server's
environment, which the kernel does not control.

Each chat tab's hover tooltip carries the same fact as a `Billing` row —
`API key`, or `Login (name@example.com)` — whenever the session's backend
reports it, one-auth machines included; only tmux sessions, whose billing romp
cannot know, show no row. When the CLI's own report disagrees with what the
session was launched for — a key found through `apiKeyHelper`, say — the row
carries both: `Login (CLI reports API key)`.

Failures are loud rather than silent: a session that lands on the other auth
than it was launched for (say, a key found through `apiKeyHelper`) is flagged
in the Log panel, and a dead credential — "Not logged in", an invalid or
expired key — blocks the session's card with the fix named, and is never
auto-retried.

One side of that check can be the box's *design*: on a machine whose sessions
are all meant to bill a key that arrives through `apiKeyHelper` — so it never
appears in `service.env` — the landed-on-the-other-auth warning would fire on
every init, permanently. Declaring the intent fixes it: set
`ROMP_EXPECTED_AUTH=key` (or `login`) in `service.env`, and a session landing
on the declared side is quiet while one landing on the other side is flagged,
naming the declaration. The check inverts rather than disappearing; unset (or
any other value), it compares against what the session was launched with, as
before. One explicit gear **Billing** pick supersedes the declaration from then
on: the remembered pick becomes the box's expectation and the env var goes
inert (it described the unpicked design), so re-seeded spawns are judged
against your pick, never against stale doctrine.

The usage rail reflects a mixed machine: the window bars (5 hours / 7 days /
Fable 5) are drawn once, aggregated across every connected host's login as the
worst reading per window, and an `API` cell beside them carries the
key-billed dollars (5-hour burn and month-to-date, numbers only). Hovering
breaks both down per host — one column per host, side by side — and a host
can show its login's windows and its key's spend together. Only turns whose
session billed the key count toward the API numbers — a login turn's computed
cost is dollars nobody pays.

### Self-scheduled work wakes an idle session

A session's own scheduled work (a recurring Monitor, a cron firing, a
background task's completion notice) arrives as a queued notification even
while the session is idle. The Claude Code CLI usually delivers it on its
own, starting the turn within a fraction of a second; but a session can fall
into a stuck state where the CLI only queues, nothing ever starts the turn
that reads the queue, and the backlog waits silently until your next message.
Romp watches for that: once a queued notification has sat undelivered for a
minute (well past the CLI's own delivery window) with no turn running, one
driven turn delivers every text that has waited out that minute, verbatim and
with no words of Romp's own, and logs one kernel-log line per wake; a newer
arrival waits out its own minute rather than delaying the rest. A
notification that arrives mid-turn is delivered once the turn settles, and
one whose delivery a kernel restart interrupted is re-driven on the next
boot rather than dropped. Notifications
the CLI delivers itself in either state (a background agent finishing) are
left to it, and sessions that are mid-turn, compacting, blocked on an API
error, retry-paused, or that you interrupted or ended are left alone. On the
first run after an upgrade, a session holding a genuinely old queued backlog
may get one catch-up turn delivering it; that is this feature doing its job
once.

### Install-time switches

For `./install.sh`:

- `ROMP_NO_SERVICE=1` skips the login service.
- `ROMP_NO_EXT=1` skips the VS Code / Cursor extension.
- `ROMP_NO_SDK=1` skips the SDK backend's venv (tmux sessions still work).

For the one-line installer (`bootstrap.sh`), which passes all of the above
through to `install.sh`:

- `ROMP_DIR=<path>` where to clone; default `~/romp`.
- `ROMP_REF=<tag|branch>` install a specific ref; default is the newest `v*`
  release tag, falling back to `main` when none is published.
- `ROMP_NO_PATH=1` leaves your shell rc alone.

### Ports

- `ROMP_KERNEL_PORT=<port>` moves the kernel and its dashboard off the default
  `29855`. `ROMP_SERVE_PORT` is a second name for the same port, the one the
  manager and the supervised service use. Set either and the other follows; set
  both to different values and the kernel refuses to start rather than picking
  one for you.
- `ROMP_POSTAL_PORT=<port>` moves the postal bus off the default `25302`.

Set these if something else on the machine already holds the default. Both have
to agree across everything that talks to the kernel, so export them where the
whole environment sees them rather than for one command.

Run `romp-service install` again after changing one. The service unit bakes in
whatever is set at install time, so a renumbered port that only lives in your
shell leaves the supervised manager on the old one, and the two collide.

### Service environment (secrets)

The manager runs as a login service (launchd on macOS, systemd --user on
Linux), so it never sees variables your shell rc exports — a terminal having
`ANTHROPIC_API_KEY` does nothing for the sessions the kernel spawns. On a
machine where Claude authenticates through an OAuth login this gap is
invisible (the credentials live in a file any process can read); on an
API-key-only machine it means SDK sessions come up unauthenticated while
`claude` in your terminal works fine.

Env like that goes in `~/.config/romp/service.env` — plain `KEY=VALUE` lines,
`chmod 600`:

    ANTHROPIC_API_KEY=sk-ant-...

Unlike the ports above it is NOT baked at install: it is read each time the
manager starts (the systemd unit via `EnvironmentFile=-`, the macOS login
agent's launcher by parsing it — line by line, never sourced, so a malformed
line is skipped rather than executed). Rotate a value by editing the file and
restarting the manager (`romp-service install`); a missing file is a no-op.

`ANTHROPIC_API_KEY` is the one exception to that last sentence — it needs no
restart at all. See below.

### Switching which API key the sessions bill (`romp keyswap`)

The key a session bills rides its launch environment, and romp reads the
`ANTHROPIC_API_KEY=` line of `service.env` **fresh at every session launch**.
So changing keys — moving to another organisation's key, rotating a leaked
one, switching between a high-priority and a batch key — costs no manager
restart, and no session loses an open turn.

Keep one file per key beside `service.env`, each a single `ANTHROPIC_API_KEY=`
line, `chmod 600`:

    ~/.config/romp/service.env.highprio
    ~/.config/romp/service.env.lowprio

Then:

    romp keyswap                       # which key is live, and what you can swap to
    romp keyswap lowprio               # rewrite the key line from service.env.lowprio
    romp keyswap lowprio --cycle-all   # …and move the running sessions onto it too
    romp keyswap lowprio --cycle web,api

`romp keyswap <name>` rewrites **only** the `ANTHROPIC_API_KEY=` line, in
place, keeping every other line of the file as it was (line endings come out
as LF) — a temp file and a rename, so no reader ever sees the file
half-written, and the mode stays `600` (a looser one is tightened). A
symlinked `service.env` is written through: the target changes, the link
stays. It refuses a source file with no key line rather
than writing an empty key, which the CLI would read as "API-key mode, no key".

After the rewrite:

* **new sessions, and any session you revive, bill the new key immediately** —
  nothing else to do;
* **already-running sessions keep the key their process started with**, because
  the key is handed over at launch. `--cycle-all` (or `--cycle <session,…>`)
  reconnects them so they re-present the new one. A reconnect resumes the same
  conversation with its history intact — the same mechanism a reasoning-effort
  or billing switch uses — and only for a session that is quiet right now. Sessions billing the machine login are
  skipped, dormant ones are reported as needing nothing, a session already
  launched on the live key reads `current`, and a session with a turn,
  subagents or background tasks in flight is skipped and named — a reconnect
  would kill that work — so you re-run the same `--cycle` once it is quiet,
  until every session reads `current`;
* **the judges and the model catalog** pick the new key up on their next call,
  with no cycling at all.

No key value is ever printed, logged, or sent over a socket. The only rendered
form is the first 12 hex of its sha256 — `sha256:1a2b3c4d5e6f` — which appears
in the command's output, in the Log panel when the key changes, and in the
kernel's own answer to `--cycle`. Comparing those tells you the swap landed
without either side showing the key.

**One restart, once:** a kernel that is already running when this feature is
installed neither reads the file live nor knows the `--cycle` route, so it is
still on the key it booted with. Take the update a single time with `romp
refresh` — or `romp refresh --quiet`, which waits for the sessions to finish
their turns first — and every swap after that is restart-free. `romp keyswap
--cycle-all` says so plainly if it meets an older kernel.

Remote kernels each have their own `service.env` and their own key: run
`romp keyswap` on that machine.

`ROMP_SERVICE_ENV_FILE` overrides the path of the file. The installer bakes
the path it resolved into the unit and, when that is not the default, exports
it to the service as well, so the kernel's live read and the installer name
one file; a service installed before that carries only the default. `romp
keyswap` asks the running kernel which key it reads and says `MISMATCH` when
that is not the file's — the check to make after a swap.

## Where things live

State is written under `${XDG_STATE_HOME:-~/.local/state}/romp/`. Transcripts
are read in place from where Claude Code writes them (`~/.claude/projects/`)
and never copied.

## Switches

Effective immediately, no restart.

`touch` to **disable**, `rm` to re-enable:

- `~/.claude/romp-postal-off`: the postal service

`touch` to **enable**, `rm` to turn back off:

- `~/.claude/romp-summarize-on`: the live tmux activity phrase. Off by default,
  because it spends tokens on every turn and the SDK backend reports what a
  session is doing without it.
