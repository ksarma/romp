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
| `romp keyswap [<name>] [--cycle <session,…>\|--cycle-all]` | Switch the API key source without restarting the manager: selects a 1Password reference or a legacy key from `service.env.<name>`, and `--cycle` reconnects running sessions onto it. Bare, it reports the configured source and candidates without fetching secrets. See [Switching which API key the sessions bill](#switching-which-api-key-the-sessions-bill-romp-keyswap) |
| `romp help` | The same list, from the terminal |

These are for scripting and for agents rather than daily use:

| Command | What it does |
|---|---|
| `romp url` | Print only the tokened dashboard URL, for piping |
| `romp sessions [--json]` | The fleet with each session's state, identity colours, directory and backend |
| `romp api-health` | The API-health signal as JSON (see [The API-health signal](#the-api-health-signal)): per-credential, per-model-family retry and give-up rates over rolling windows, with a derived state |
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
per-session files and the session registry under `~/.local/state/romp/`. For
runtime API keys, configure a 1Password reference in the service environment
instead; see [Service environment and credentials](#service-environment-and-credentials).

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

Typing `/model X` or `/effort X` into the chat composer, or sending one with
`romp send`, is the same setting change as a pick from the statusline's model
and effort dropdowns: the kernel takes it through its own setters, so what it
remembers (the value a reconnect relaunches with, the defaults new sessions
start from) follows the switch. A typed `/fast on|off` goes through the same
setters and matches a pick from the fast badge the next section describes, a
separate toggle rather than one of the two dropdowns. A bare `/model` (the
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
or the configured API key source — per session. That source can be a 1Password
reference resolved at runtime or a legacy `ANTHROPIC_API_KEY`.

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
existed. tmux sessions are not covered by the picker: their CLI lives in the
tmux server's environment, which the kernel does not control. What Romp does
do there, when a 1Password reference is configured, is keep the manager's
startup `ANTHROPIC_API_KEY` out of the server's globals, so a terminal
session falls to Claude Code's own auth (login or `apiKeyHelper`) rather than
billing a key nobody chose; see [API keys from 1Password at
runtime](#api-keys-from-1password-at-runtime).

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

The declaration is also checked against `service.env` once, when the kernel
starts. Under `ROMP_EXPECTED_AUTH=login`, a file that selects an API key
source (an `ANTHROPIC_API_KEY=` line with a value, or a `ROMP_API_KEY_REF=`
line) is a contradiction: that source is injected at launch for every session
without an explicit Billing pick, so those sessions bill the key. One problem
line in the Log panel says so before anything launches, naming the file and
the variable but never a value; fix whichever side is wrong. Under `key`, a
key source in the file agrees with the declaration and nothing is said. With
no declaration, or once a Billing pick has made it inert, nothing is said
either. The per-init check above still confirms each landing.

The usage rail reflects a mixed machine: the window bars (5 hours / 7 days /
Fable 5) are drawn once, aggregated across every connected host's login as the
worst reading per window, and an `API` cell beside them carries the
key-billed dollars (5-hour burn and month-to-date, numbers only). Hovering
breaks both down per host — one column per host, side by side — and a host
can show its login's windows and its key's spend together. Only turns whose
session billed the key count toward the API numbers — a login turn's computed
cost is dollars nobody pays.

The token count beside the dollars is every kind together: fresh input,
output, cache writes, and cache reads. Cache reads are most of it — every API
call within a turn (one per tool step) re-reads the whole context from the
cache, so a long session's single turn can read tens of millions of tokens at
a tenth of the input price. The hover splits each window's count by kind, so
the size of the number carries its explanation.

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

### Service environment and credentials

The manager runs as a login service (launchd on macOS, systemd --user on
Linux), so it does not receive variables exported by your shell rc. Configure
the service in `~/.config/romp/service.env` using plain `KEY=VALUE` lines and
owner-only permissions (`chmod 600`). The service reads this file at manager
startup; API key source settings are also read live before use. Other changes
need a manager restart. `ROMP_SERVICE_ENV_FILE` overrides the file's path.
Supervised services use this file as their API key source. An empty or missing
source cannot fall back to credentials inherited from an earlier manager
start, including after a kernel refresh or crash restart. Foreground managers
can use an environment source when no service-file source governs them.

#### API keys from 1Password at runtime

To keep API key values out of Romp's configuration files, set a
[1Password secret reference](https://www.1password.dev/cli/secret-references):

    ROMP_API_KEY_REF=op://vault/item/field

`ROMP_API_KEY_REF` takes priority over a legacy `ANTHROPIC_API_KEY` in the
selected configuration. An empty or invalid reference is an error, not a
request to use the legacy key. Remove competing plaintext assignments when
migrating; `romp keyswap` does this automatically when selecting a profile.

Romp runs [`op read --no-newline`](https://www.1password.dev/cli/reference/commands/read)
for each Claude SDK session launch or reconnect, each API-key-billed judge
call, and each direct model-catalog refresh. A paginated catalog refresh uses
that credential for all its pages. An explicit `romp keyswap --cycle` resolves
the key once per request to check which quiet sessions need a reconnect. When
a retrieval fails, the judges do not retry it on every call: the failure holds
for the rest of that judging pass and is retried when the next pass begins or
the source changes, so an unreachable `op` costs one timeout per pass. Romp
captures the value in memory and passes it to that operation. It does not write the resolved key
to disk or cache it for later operations. A running Claude process retains
the key it received at launch until it reconnects; this is not retrieval
before every message in an existing session.

The `op` executable must be on the **service's PATH**, and 1Password access
must work for the OS user running the service. The service installer records
PATH at install time; run `romp-service install` again after changing it.
An interactive terminal sign-in does not by itself establish that a headless
login service can read the same secret: a service has no desktop app to
unlock. The supported unattended route is a
[1Password service account](https://developer.1password.com/docs/service-accounts/):
put its token in `service.env` beside the reference,

    OP_SERVICE_ACCOUNT_TOKEN=ops_...
    ROMP_API_KEY_REF=op://vault/item/field

and give the account read access to that one vault, and nothing else. When a
reference is configured, Romp takes `op`'s own credential names
(`OP_SERVICE_ACCOUNT_TOKEN`, `OP_SESSION_*`, `OP_CONNECT_*`, `OP_ACCOUNT`) out
of its environment as its first act at startup, says which names it claimed in
the kernel log, and hands them to the `op read` subprocess alone: no Claude
session, judge call, or tmux launch inherits them, so an agent running `env`
sees neither the API key nor the credential. The `op read` subprocess itself
gets a minimal environment, not a copy of the kernel's: `PATH`, `HOME`, `USER`,
`LOGNAME`, `TMPDIR`, `LANG`, `LC_*`, `TERM`, the `XDG_*` names (op finds
`~/.config/op` and the desktop app's socket through `HOME` and `XDG_*`), and
the claimed `OP_*` names. Nothing of Romp's (the serve token, a startup
`ANTHROPIC_API_KEY`, the reference variable) reaches it.

The tmux server needs the same care, because every pane inherits the
**server's** globals, not the launching client's. Whenever Romp becomes the
op consumer — at kernel start, or later when `romp keyswap` selects a
reference on a box that started without one, with no manager restart — it
unsets the `OP_*` names **and** the manager's startup `ANTHROPIC_API_KEY`
from the tmux server's global environment; the manager starts the server
without them, and `romp new -t` scrubs them again before the pane exists
(reading the reference from its own environment or from `service.env`'s
line). A terminal session on a reference-governed box therefore never bills
the key the manager started with: with no `ANTHROPIC_API_KEY` in its
environment it falls to Claude Code's own auth (login or `apiKeyHelper`).
Panes that already existed when the reference was selected keep the
environment they launched with; end or relaunch them. A box with no reference
configured is untouched: static-key panes rely on inheriting the key, and an
`apiKeyHelper` box's sessions need `op`'s environment.

This keeps the token out of every agent's shell by default; it is
inheritance hygiene, not isolation. The file stays readable to the same OS
user (keep it `chmod 600`), and a same-user process can read the manager's
original environment, which is why the account must see only the one vault.
Like the rest of `service.env`, the token line loads when the manager starts;
changing it needs a manager restart, where the reference itself is read live.
Do not put the token in a per-session environment (`romp new --env`), which
is copied into per-session files.

A supervised manager (the systemd or launchd service) reads its key source
from `service.env` **only**. A key that reaches the manager some other way, a
systemd drop-in `Environment=` or a launchd plist entry, is ignored and said
so once in the kernel log with its fingerprint; sessions without an explicit
Billing pick then launch on the login. Move such a key into `service.env`, or
replace it with a reference.

For a foreground manager, the same reference can be supplied in its
environment:

    ROMP_API_KEY_REF=op://vault/item/field romp up

The Billing picker, status displays, and `romp keyswap` listing and selection
inspect the configured source without running `op`. A configured reference
therefore means "API key available to try", not "1Password access verified".
If a selected provider cannot resolve the key, the operation fails with a
credential error. It does not use an ambient key, a previous resolved key,
or a Claude login as a fallback. Choosing **Login** explicitly still uses
Claude Code's supported login flow and does not resolve the API key source.

To migrate an existing service:

1. Put the API key in 1Password and obtain its field's secret reference.
2. Replace `ANTHROPIC_API_KEY=...` in `service.env` with
   `ROMP_API_KEY_REF=op://vault/item/field`. Replace any sibling profiles used
   by `romp keyswap` in the same way, and remove obsolete plaintext copies.
3. Refresh the kernel once to load this version of Romp. Future source edits
   take effect without restarting the manager: the next session launch or
   judge call reads the reference, and that first read also scrubs the tmux
   server of `op`'s names and the retired `ANTHROPIC_API_KEY`.
4. Reconnect existing key-billed SDK sessions with `romp keyswap --cycle-all`
   when they are quiet. Newly launched sessions and subsequent judge/model
   requests use the configured source immediately. Terminal (tmux) sessions
   launched before the migration still carry the plaintext key they started
   with; end and relaunch them.

Once a reference has been selected from `service.env`, Romp remembers it on
disk in the sibling file `service.env.source` (the word `op`, mode 600, never
a reference or a key), so the memory survives kernel restarts: deleting the
reference line and restarting does not make sessions fall to the login.
Selecting a static key — `romp keyswap <static profile>`, or writing an
`ANTHROPIC_API_KEY=` line — removes the marker, so an intentional switch is
not an error. `romp keyswap` does not list the marker as a profile.

Removing or emptying an explicit service-file key source cannot revive the
key inherited when the kernel started. After removing a selected provider,
API-key operations fail until a valid source is selected; choose **Login**
explicitly to use that mode. Removing a static `ANTHROPIC_API_KEY=` line
while the kernel runs is different: the file stays authoritative and
sessions without an explicit Billing pick launch on the login, and the
kernel log says so once, with the removed key's fingerprint and the file's
path. Removing a source does not revoke a credential already held by a
running Claude process; reconnect or end those sessions too. Rotate a
previously exposed key with its issuer as appropriate.

#### Existing API keys and Claude login

1Password is optional for general use. Without a runtime provider selected,
Romp continues to support legacy `ANTHROPIC_API_KEY` configuration, including
in `service.env`, and the existing Claude Code login. A foreground manager
can also use its inherited API key when no service-file source governs it.
For login, authenticate through Claude Code's supported CLI login flow and
select **Login** in Billing; no extracted OAuth token is needed.

Plaintext keys remain supported for compatibility, but do not meet policies
that require secrets to be fetched from 1Password at runtime. File permissions
do not change that distinction.

### Switching which API key the sessions bill (`romp keyswap`)

The key a session bills rides its launch environment, and Romp checks the
API key source in `service.env` **at every session launch**.
So changing keys — moving to another organisation's key, rotating a leaked
one, switching between a high-priority and a batch key — costs no manager
restart, and no session loses an open turn.

Keep one file per profile beside `service.env`, each with a single
`ROMP_API_KEY_REF=op://vault/item/field` assignment, `chmod 600`:

    ~/.config/romp/service.env.highprio
    ~/.config/romp/service.env.lowprio

Then:

    romp keyswap                       # configured source and candidate profiles
    romp keyswap lowprio               # select the source from service.env.lowprio
    romp keyswap lowprio --cycle-all   # …and move the running sessions onto it too
    romp keyswap lowprio --cycle web,api

Legacy profiles containing a single `ANTHROPIC_API_KEY=` assignment also
work. `romp keyswap <name>` writes the selected assignment and removes the
competing key-source assignment, keeping all unrelated lines as they were
(line endings come out as LF). A temp file and rename make the update atomic,
and the mode stays `600` (a looser one is tightened). A symlinked `service.env`
is written through: the target changes, the link stays. A profile without a
usable source is rejected. Listing or selecting a reference never retrieves
its key; an explicit `--cycle` check asks the kernel to resolve it.

After the rewrite:

* **new sessions, and any session you revive, bill the new key immediately** —
  nothing else to do;
* **already-running sessions keep the key their process started with**, because
  the key is handed over at launch. `--cycle-all` (or `--cycle <session,…>`)
  reconnects them so they re-present the new one. A reconnect resumes the same
  conversation with its history intact — the same mechanism a reasoning-effort
  or billing switch uses — and only for a session that is quiet right now. Sessions billing the machine login are
  skipped, dormant ones are reported as needing nothing, a session already
  launched on the current resolved key reads `current`, and a session with a turn,
  subagents or background tasks in flight is skipped and named — a reconnect
  would kill that work — so re-run `--cycle` for those sessions once they are
  quiet;
* **the judges and direct model-catalog refreshes** pick the new source up on
  their next call, with no cycling at all;
* **terminal (tmux) sessions** are not cycled. A swap from a static key to a
  reference removes the old `ANTHROPIC_API_KEY` from the tmux server's
  globals at the kernel's next key read and at the next `romp new -t`, so new
  panes fall to Claude Code's own auth; panes already open keep what they
  launched with — end and relaunch them.

No key value is printed or sent in Romp's status/control responses. Legacy
keys are identified by the first 12 hex of their sha256, such as
`sha256:1a2b3c4d5e6f`. Provider status uses a fingerprint of the reference,
without resolving it; this cannot verify the secret value or detect a rotation
behind an unchanged reference. An explicit `--cycle` resolves the current key
for each quiet session and reconnects it if that key differs from its launch
key, including when the reference itself is unchanged. A session already
using that key reads `current` and stays connected. A reconnect resolves the
source again at the actual launch, so it does not reuse a key cached by the
cycle check.

**One restart, once:** a running kernel needs to load this version to support
runtime providers. Take the update with `romp refresh` — or `romp refresh
--quiet`, which waits for sessions to finish their turns first — and later
source swaps need no manager restart. `romp keyswap --cycle-all` reports when
it encounters a kernel too old to support cycling.

Remote kernels each have their own `service.env` and their own key: run
`romp keyswap` on that machine.

`ROMP_SERVICE_ENV_FILE` overrides the path of the file. The installer bakes
the path it resolved into the unit and, when that is not the default, exports
it to the service as well, so the kernel's live read and the installer name
one file; a service installed before that carries only the default. `romp
keyswap` compares the running kernel's source identity with the file's and
says `MISMATCH` when they differ — the check to make after a swap.

### What survives a restart

A kernel restart ends every session's CLI. On `romp refresh`, the manager's
restart-all or a service stop, the kernel receives SIGTERM and drains: it
closes each CLI, and a CLI still running when the drain's bound expires gets
SIGTERM, then SIGKILL. A crash respawn has no drain: the kernel died without
running one, its CLIs are orphaned, and the next kernel's boot reaper
terminates them (see below). The CLI's harness background tasks do not all end
with it. Its timers and monitors live inside the CLI process and end when it
does. A background shell is a separate process the CLI started, and a CLI
killed by SIGKILL runs no cleanup, so its shells are re-parented and may keep
running. The session resumes with its history and is told what was cut: its
in-flight turn, if it had one, and each background task, with a request to
check whether each is still running before relaunching it. A kernel restart has
never touched work a session deliberately detached: tmux servers, `setsid`
children and other processes that outlive their shell.

A service restart (`systemctl --user restart romp-manager`, or the machine's
own service management) kills everything in the service's cgroup, so on Linux
under systemd Romp runs each session's CLI, and the default tmux server the
manager starts, in a transient systemd scope of its own, outside that cgroup
(`systemctl --user list-units 'romp-session-*' 'romp-tmux-*'` lists them). A
session's tmux servers, `setsid` children and other detached work live in the
session's scope, and a service restart leaves them alive as a kernel restart
does; before 2026-09-05 they were in the service's cgroup and died with it. The
CLI itself still ends: the kernel receives the service's SIGTERM and runs the
same drain. A scoped CLI outlives a service restart only when the drain does not
reach it: a kernel killed before its drain finishes (SIGKILL at the service's
stop timeout), or a CLI the drain could not find. The reaper handles that case:
at the next kernel boot, an SDK-driven CLI holding one of the kernel's sessions
whose parent is not a live romp kernel is treated as orphaned and terminated.
Under `systemd --user` an orphan re-parents to the user manager, not to pid 1,
so a ppid check alone would miss it and did, before 2026-09-05.

One-time caveat when this lands: the first service restart after it still
empties the current cgroup, tmux servers included, because the running manager
and its tmux server predate the change and are still inside the service's
cgroup. The guarantee holds from the following restart on.

`ROMP_CLI_SCOPE=0` in the service environment turns the scopes off, for
session CLIs and the tmux server alike. A manager run outside the service
(`romp up`) scopes nothing unless `ROMP_CLI_SCOPE=1` is set, which turns both
on. The kernel logs which it chose at start (`cli scope: on` or `off`, with the
reason); when the scopes were wanted on Linux and the box cannot provide them
(no `systemd-run`, or a user manager that refuses to start one), that verdict
also appears in the dashboard's error center, since every session then runs
inside the service cgroup. The macOS launchd path is unchanged: there is no cgroup kill there,
and the tmux server keeps its launchd lineage.

#### Per-session memory limits (opt-in)

A session's scope can carry a memory limit, so a runaway process is killed
inside its own session before a machine-wide OOM killer has to pick a victim. On
2026-09-06 a session's shell expanded a glob over a large `/tmp`, grew past 30
GB, and the machine's userspace OOM killer (earlyoom) killed the largest process
it saw at that instant: the romp kernel, which ended every session. No limit is
set by default; the size is the user's choice, per machine. The kernel reads
each of the variables below once at its start and hands it to the session's
scope wrapper, so, like the other service variables, a change takes effect at
the next manager restart. Four variables in the service environment
(`~/.config/romp/service.env`) opt in:

- `ROMP_CLI_SCOPE_MEMORY_MAX`: the hard limit (systemd `MemoryMax=`). Above it,
  the cgroup's OOM killer sends SIGKILL to the largest process in the scope and
  to nothing else (the wrapper's `OOMPolicy=continue`, below, confines the
  kill). When that is a tool's process, as in the incident, the session sees a
  failed tool call: the Bash tool reports the command killed (exit status 137),
  and the scope keeps running with the CLI in it. When the CLI is itself the
  largest process, it is the one killed, and the session is cut as after any CLI
  death. The kernel and the other sessions are untouched either way.
- `ROMP_CLI_SCOPE_MEMORY_HIGH`: the soft limit (`MemoryHigh=`). Above it, the
  scope is throttled and its memory reclaimed; the limit itself kills nothing.
  A throttled scope does raise memory pressure, and on a machine where
  `systemd-oomd` is set to act on the user manager's pressure (`systemctl show
  user@$(id -u).service -p ManagedOOMMemoryPressure` prints `kill`) it can kill
  the whole scope, `OOMPolicy=continue` notwithstanding; check that setting
  before relying on the soft limit alone.
- `ROMP_CLI_SCOPE_MEMORY_SWAP_MAX`: the swap limit (`MemorySwapMax=`). Without
  it, a scope at `MemoryMax` pushes pages to swap instead of being killed, until
  the machine's swap is used up, and the swapping slows every other process. On
  a machine with swap, set this too.
- `ROMP_CLI_SCOPE_OOM_SCORE_ADJ`: an integer from -1000 to 1000, written to the
  `oom_score_adj` of the process that becomes the CLI, before the CLI starts, on
  every path that starts one: a launch that falls back to a direct run, outside
  a scope, still carries it, since the write needs no scope. The CLI and
  everything it spawns inherit it; the kernel keeps its own. Linux's OOM killer
  and earlyoom rank processes by a score this value is added to, so a session
  with a raised value is chosen before the kernel when the whole machine runs
  out of memory. Raising the value needs no privilege. Lowering it below the
  user manager's own `oom_score_adj` needs privilege and is refused (see the
  note on `OOMScoreAdjust=` at the end of this section).

Sizes are an integer with an optional `K`, `M`, `G` or `T` suffix (powers of
1024, as systemd reads them) or `infinity`. The rule is narrower than systemd's
own size syntax: systemd takes `50%` (a share of the machine's memory), `1.5G`,
`16 G`, `16P` and `1G 512M` for `MemoryMax=`, and the rule refuses them all as
not a size, along with a lowercase suffix (`16g`). Each is dropped before it
reaches systemd, with the problem line described below; write `16G`. The
adjustment takes no leading zero: Linux reads `0400` as octal. A value that
fails its rule is dropped and reported, and the session still starts in its
scope with the other limits. The kernel checks the rules once at its start: a
value it refuses is a problem line (a kernel log entry that the dashboard's
error center also shows) naming the variable and the rule, and the wrapper
receives that variable empty, so the value is applied nowhere. The probe at the
kernel's start, described below, catches a value that passes the rule but that
systemd refuses (a size past its range; `OOMPolicy=` on a scope before systemd
253) and reports it the same way, quoting systemd.
The wrapper checks the same rule on every launch and reports a value it refuses
on stderr as `romp-cli-scope: ignored: …`, which the kernel logs as a problem
naming the session and counts in `/api-health` (`cliScope.limitsIgnored`, see
[The API-health signal](#the-api-health-signal)); on a launch the kernel drove,
an `ignored:` line naming a rule means the value reached the wrapper some other
way.

The rules are syntax, and two kinds of value that pass them can still be refused
by the machine: a memory property this systemd does not take on a scope
(`OOMPolicy=` on scopes needs systemd 253), and an adjustment the process cannot
write, because it is below the user manager's own `oom_score_adj` or because
`/proc/self/oom_score_adj` cannot be opened for writing (a read-only `/proc` in
a hardened container). Without a check at the kernel's start, each would be
refused again on every launch, one `ignored:` line and one problem each, while
the kernel's boot line said the value was in force. So with the scopes on, the
kernel runs the wrapper's own steps once at its start: it starts a probe scope
carrying the memory properties, and has a throwaway child write the adjustment
to its own `oom_score_adj`. A refusal there is a problem line at the kernel's
start and reaches the wrapper as an empty variable, so no launch repeats it. The
adjustment's problem line quotes the shell and says which step failed: it names
the floor only when the file opened and the write was refused; otherwise it says
the file could not be opened, and why. The wrapper's `ignored:` line makes the
same distinction. A probe that does not answer (the user bus away at that
moment) settles nothing. The kernel says so in its log (a plain line, not a
problem), hands the values down as read, and lists them in its boot line as set
but not settled, naming the check; the values whose checks did answer keep their
own verdict in the same line, so an unanswered check for one value never makes
another unknown. Whether the values apply is then known from the wrapper's
report on each launch. The wrapper keeps the same guard on every launch. Its
pre-flight scope carries the properties. If that fails, it retries bare; if the
bare scope starts, it tries once more with the properties, and only that second
failure drops them, for that launch, with one `ignored:` line quoting the
failure that decided. (A bare failure is the fallback described above.) The CLI
then starts in its scope without the memory limits; the adjustment is still
written. On a launch the kernel drove, an `ignored:` line quoting a systemd
rejection means the machine changed under the running kernel.

Whenever a memory limit is set, the wrapper also sets `OOMPolicy=continue` on
the scope. A scope's default is `stop`: when Linux's OOM killer kills one
process in it, systemd stops the whole scope, which ends the CLI and every tmux
server and `setsid` job in it. With `continue`, only the killed process is gone.
systemd logs each kill to the user journal as `<unit>: A process of this unit
has been killed by the OOM killer` (`journalctl --user --since today | grep
'romp-session-'`).

The limits need the memory controller delegated to the systemd user manager;
stock systemd delegates it (`systemctl show user@$(id -u).service -p
DelegateControllers` lists `memory`). Without it, systemd accepts the
properties, reports them from `systemctl --user show`, and applies nothing; the
cases are an administrator's drop-in on `user@.service`, the legacy cgroup
hierarchy, a kernel booted with the controller off, and a container whose cgroup
subtree lacks it. The kernel checks for this at its start, inside the probe
scope above: the scope's cgroup has a `memory.max` file when, and only when, the
controller is there. A missing one is a problem line at the kernel's start. A
probe that exits non-zero or does not answer (its scope fails to start, it does
not finish, its command is killed or exits without a marker) is tried once more;
one that exits 0 without printing a marker is not. When no try gives a verdict,
that is a problem line too: it says what each try did (one try, or two) and
quotes systemd's refusal, the exit status, or what was printed; and the check is
left unsettled.
Whether the memory limits apply is then unknown until the next kernel start. To
check a live session, run from a shell inside it: `cat /sys/fs/cgroup$(cut -d:
-f3 /proc/self/cgroup)/memory.max` prints the limit in bytes, `max` when none
applies, and fails when the controller is not there.

A suggested starting point for a shared 64 GB machine:
`ROMP_CLI_SCOPE_MEMORY_MAX=16G`, `ROMP_CLI_SCOPE_MEMORY_HIGH=12G`,
`ROMP_CLI_SCOPE_MEMORY_SWAP_MAX=0`, `ROMP_CLI_SCOPE_OOM_SCORE_ADJ=500`. One
session can still take a quarter of the machine, more than any ordinary tool
call needs; the kernel (a few GB), the other sessions and the system keep the
rest. A session is throttled once it passes 12 GB and killed when it reaches 16
GB, without swapping first. An adjustment of 500 adds 500 points to each
session's OOM score, on a scale where 1000 points is the whole of the machine's
memory, so the machine-wide killers also choose a runaway session before the
kernel.

The limits cover what runs in the session's scope: the CLI, its tool shells,
their `setsid` children, and a private tmux server started directly from a tool
shell (`tmux -L <name>`). Two kinds of work are outside it. Work a session hands
to the server the manager started (`tmux new-session` on the default socket)
runs in that server's scope (`romp-tmux-*`), not the session's. And anything a
session starts as a transient unit of its own (`systemd-run --user --scope …`,
or a `systemd-run --user` service) is a sibling of the session's scope under the
user manager, outside its memory limits: a tmux server detached that way is
outside them, whereas the same server started with a plain `tmux -L` is inside.
A `--scope` job started that way still inherits the session's raised
`oom_score_adj` (`systemd-run` runs the command in place); a transient service
does not (the user manager spawns it, not the session).

`OOMScoreAdjust=` on the manager unit cannot separate the kernel from the
sessions, which is why the adjustment is a raised score on the session tree. A
user unit's `OOMScoreAdjust=` cannot go below the user manager's own
`oom_score_adj`: 100 on a typical machine, where the romp manager and the kernel
sit at 200, so a drop-in asking for -500 lands at 100. It can bring the manager
and the kernel down to that floor and no lower, and, with no session-side
adjustment set, the sessions follow, because the kernel spawns them and they
inherit its value: lowering the kernel's score lowers every session's by the
same amount. The raise on the session side separates the tiers: the wrapper
writes it in the session's own process, after the kernel has spawned it, so the
kernel keeps its own. None of this subsection applies on the launchd path.

## The API-health signal

`GET /api-health` returns one JSON document describing how the API is treating
the sessions this kernel runs. It is computed from frames the kernel already
parses: the per-attempt retry frame, each successful response, and the settle
of a turn the CLI gave up on. The route takes the serve token, like every read
that is more than a bare counter; `romp api-health` prints the document. The
kernel takes no action on it: a consumer reads the signal and applies its own
policy (move traffic to another key, hold a batch).

Events are bucketed by **auth-source label** and **model family**
(`"<auth>|<family>"`, for example `key:0123456789ab|fable`), because rate
limits are per model family per account: pooled, one family's storm disappears
under another family's clean traffic. The auth label is a salted digest of the
credential's identity: for a key the kernel injected, the fingerprint recorded
at the session's launch (the same 12 hex the kernel log and `romp keyswap`
print; the key itself is never read for this, so a 1Password-sourced key is not
retrieved per session start); for a login, the account digest the usage bars
stamp. The same key or login gives the same label within one install, and
nothing about the key itself is in it. The salt lives at
`STATE/api-health-salt`, minted once at 0600; an empty file makes the label
that fingerprint or account digest itself, so a bucket can be matched to the
log. `key:helper`, `key:env` and `key:managed` name sources whose material the
kernel never holds.

### Top-level fields

- `schema`: `1`, incremented on any incompatible change.
- `asOf`: wall-clock epoch seconds at which this response was computed from the
  event ring. Every window and every state is computed at read time, so `asOf`
  is the response time. A clock step moves it; a reader that wants a freshness
  check a clock step cannot fake uses `seq`.
- `bootId`, `bootAt`, `uptimeS`: the kernel process identity, the same id
  `/version` and `X-Romp-Boot` carry. A changed `bootId` means a restart, and
  the windows restarted with it.
- `complete`: true once the longest window (900 s) fits inside the uptime.
- `seq`: count of ring events (attempts, successful responses and give-ups)
  ingested since boot. Monotonic within a boot: two reads with the same `seq`
  saw no traffic in between.
- `lastEventAt`: the newest event of any kind in the ring, across every bucket.
- `coverage`: `sdkSessionsLive` (SDK-backed sessions the backend holds that have
  not ended); `inTurn` (of those, sessions with a turn in flight: working or
  retrying); `retrying` (sessions inside a retry storm right now, the cheapest
  direct thrash indicator, independent of the ratio thresholds);
  `tmuxSessionsUncovered` (tmux-backed sessions, which have no SDK stream and are
  outside the signal; `null` when the kernel could not enumerate them; Codex-backed
  sessions carry no Anthropic API traffic, are outside the signal too, and are
  counted in neither field);
  `sidechainExcluded` (a constant `true`: subagent traffic is
  outside the signal on both sides of the ratio). A reader that sees `inTurn >
  0` and a `lastEventAt` minutes old should treat the signal as unknown rather
  than healthy.
- `cliScope`: the per-session scopes (see "What survives a restart" and
  "Per-session memory limits").
  - `on`, true when the kernel chose at boot to run CLIs in scopes.
  - `fallbacks`, CLI launches since boot on which the scope wrapper's pre-flight
    scope failed, so it ran the CLI directly and reported `romp-cli-scope:
    fallback: …` on stderr. Each is also a problem line in the kernel log, in
    exactly this form: `cli scope: session <name> (<sid8>) started its CLI
    outside a scope — <line>`, where `<sid8>` is the first 8 characters of the
    session id and `<line>` is the wrapper's whole stderr line, its
    `romp-cli-scope: fallback:` prefix included. The wrapper's refusal,
    `romp-cli-scope: refused: …` (`ROMP_CLI_REAL` unset, exit status 127), is
    not counted: no CLI starts, and the failure is reported on the session's
    error card. `lastFallbackAt`, epoch seconds of the newest fallback; `null`
    when there was none. `on: true` with `fallbacks > 0` means scopes were on at
    boot and some launches ran without one: those sessions' work is in the
    service cgroup, and a service restart kills it.
  - The limits: `memoryMax`, `memoryHigh`, `memorySwapMax` (the size strings)
    and `oomScoreAdj` (an integer), each `null` when its variable is unset, when
    its value was rejected, or when the scopes are off (no scope starts, so no
    limit applies).
  - `rejected`, the names of the variables whose values were refused, by their
    rule or by this machine at the kernel's start (memory properties systemd
    rejected; an adjustment the process could not write), each also a problem
    line at the kernel's start.
  - `memoryControllerDelegated`, the kernel's start-time check of whether a
    probe scope carrying the memory properties had a `memory.max` file in its
    cgroup: `true`, `false` (systemd holds the sizes above and applies nothing;
    also a problem line), or `null` when no memory limit is set, the scopes are
    off, or the check could not be settled. A `null` beside a memory limit shown,
    with `on: true`, is that last case: a check at the kernel's start did not
    answer, and `unsettled` says which.
  - `unsettled`, the names of the kernel's start-time checks that were due and
    settled nothing: `memoryLimits` (the probe scope carrying the memory
    properties did not answer, or failed both with and without them),
    `memoryController` (the check inside it gave no marker), `oomScoreAdj` (the
    throwaway child's write did not answer). Empty when every due check
    answered, and when none was due (the scopes off, no limit set). A value
    listed above whose check is named here is set and handed to the wrapper as
    read, and whether it applies is not known at the kernel's start; the other
    fields cannot show this (`oomScoreAdj` present, `rejected` empty and
    `memoryControllerDelegated` `true` read the same whether the adjustment's
    check answered or not). Each named check is also a line in the boot log
    saying why.
  - `limitsIgnored`, wrapper `romp-cli-scope: ignored: …` lines since boot (each
    also a problem line, `cli scope: session <name> (<sid8>) started its CLI
    without a per-session limit — <line>`). It counts lines, not launches: one
    launch writes one line for each value the wrapper refuses, one for the
    memory properties together when systemd rejects them, and one for an
    adjustment it could not write. `on: true` with a limit set and
    `limitsIgnored > 0` means a value the kernel accepted at its start was
    refused at a launch: the machine changed under the running kernel, or the
    value reached the wrapper outside the kernel's hand-off (see "Per-session
    memory limits").
- `config`: the constants in force (see "Derived state").
- `overall`: `state`, the most severe state among buckets that are not
  `unknown` (`thrashing > degraded > recovering > healthy`; `unknown` when every
  bucket is), and `worstBucket`, the bucket that set it. There are no pooled
  windows: summing 429 rates across auth sources mixes unrelated quotas.
- `buckets`: keyed `"<auth>|<family>"`.
- `transitions`: the last 50 state transitions across every bucket, newest
  last, each `{t, bucket, auth, family, from, to, why, evidence}`.
- `rate429Basis`: the constant `"attempts"` (see "Windows").

### Windows

Each bucket carries three windows (`60`, `300`, `900` seconds, ending at
`asOf`), each with:

- `requests`: attempts with a status, `ok + rateLimited + overloaded +
  serverErrors + otherErrors`. `noStatus` (a connection-level failure) and
  `gaveUp` sit outside the sum: a give-up is already inside one of the status
  counters, since the exhausting attempt emits no retry frame and the settle is
  the only place it can be counted.
- `rate429` = `rateLimited / requests`, `rate5xx` = `(overloaded +
  serverErrors) / requests`; both `null` at zero requests.
- `retries`, `sessionsRetrying`, `turnsRetrying`: attempts, distinct sessions
  and distinct turns with at least one retry in the window.
- `complete`: false while the window is longer than the kernel's uptime.

`rate429` is an attempt share, not a request share: one stuck turn contributes
up to `max_retries` attempts. The payload says so (`"rate429Basis":
"attempts"`); read `sessionsRetrying` and `turnsRetrying` beside it to tell one
stuck session from a saturated key. A high `rate429` with `gaveUp` at zero is
traffic being slowed, not blocked; a consumer whose action is expensive should
require `gaveUp` or `turnsRetrying` over its own span, not `state` alone.

The signal covers each session's main thread only. A subagent's retries never
reach the kernel (the CLI folds them into a progress frame the SDK drops), so
its responses are not counted either; counting one side would dilute every
rate during a storm. `coverage.sidechainExcluded` is `true` to say so.
tmux-backed sessions and the judges' own calls have no SDK stream and are
outside the signal.

Retries carry no model field, so they are attributed to the session's
last-learned family: attempts between a mid-storm model fallback and its first
successful reply file under the previous family. Successful responses use their
own model and are exact.

### Per-bucket state fields

- `state`: `unknown`, `healthy`, `thrashing`, `degraded` or `recovering` (see
  "Derived state").
- `stateSince`: epoch seconds of the read that recorded the transition into the
  current state. Every transition is stamped with the time of the read that
  found it (`transitions[].t`), and `stateSince` is that stamp for the newest
  one, so `asOf - stateSince` is how long the state has held as observed. For
  `unknown` it is the read that found no qualifying window, or the boot time
  after a restart.
- `evidence`: `{window, rate429, rate5xx, n}`, the window that decided the
  newest transition, its two rates and its `requests`, recorded at that
  transition and kept with the state; they are the numbers the transition's
  `why` carries. When the state is `unknown`, `window` and the rates are `null`
  and `n` is `requests` over 900 s at read time.
- `why`: the newest transition's reason in words, the same string as its row.
- `transitions`: this bucket's own last 50 transitions, newest last, in the
  same row shape as the top-level list. It is kept per bucket, not filtered
  from the top-level list, so a neighbour that churns through fifty
  transitions does not push this bucket's history out of view.
- `lastError`: the newest attempt or give-up that was not a success, from
  memory only (lost at restart): `at`; `status` (the HTTP status, or `null`);
  `category` (the CLI's error category string, for example `rate_limit`,
  `overloaded` or `server_error`; `null` when the frame carried none); `class`
  (the counter it landed in); `kind` (`retry` or `gaveup`). There is no text
  field, by design: the wire carries none today, and the transcript's 429 text
  names the organisation and the model.

### Derived state

`state` is computed at read time as a pure function of the bucket's event ring,
the last persisted `(state, stateSince)` and `asOf`. It has no other inputs and
no thread of its own.

- `unknown`: no window of the bucket has `requests >= minRequests` (10). Any
  state moves to `unknown` when that is so; it is also the state after boot and
  the state of a bucket whose traffic has stopped. `stateSince` is the read
  that found it so. From `unknown`, the first read with a qualifying window
  classifies afresh: an enter condition gives `thrashing` or `degraded`,
  otherwise `healthy`. `unknown` keeps no memory of the state before it; a
  consumer that wants to join an incident across an `unknown` gap reads
  `transitions`.
- `healthy`: the default once there is evidence.
- `thrashing`: the 429 share is high. The actionable state: a consumer can move
  traffic to another key or organisation.
- `degraded`: the server-side error share (`overloaded` plus `serverErrors`) is
  high while the 429 share is not. A provider-side problem another key may not
  fix, so a separate state.
- `recovering`: the exit condition has been met, but the hold time has not
  passed.

The transitions follow, with the constants that `config` echoes. A rule reads a
window only when that window has `requests >= minRequests`:

- Enter `thrashing`: `rate429(300 s) >= enter429` (0.20), or `rate429(900 s) >=
  enter429Slow` (0.15), or `rate429(60 s) >= enter429Fast` (0.50) with
  `requests(60 s) >= fastMinRequests` (20). From `healthy`, `recovering` and
  `unknown`, and from `degraded` at once: `thrashing` takes precedence over
  `degraded` whenever the 429 condition holds, on entry and afterwards.
- Enter `degraded`: the same conditions on `rate5xx` (`enter5xx` 0.20,
  `enter5xxSlow` 0.15, `enter5xxFast` 0.50) while the 429 condition does not
  hold, from `healthy`, `recovering` and `unknown`. There is no direct
  `thrashing -> degraded`: leaving `thrashing` goes through `recovering`, and
  `recovering -> degraded` fires in the same read when the 5xx condition holds
  (two rows with one `t`).
- `thrashing -> recovering`: `rate429(300 s) <= exit429` (0.10) and
  `rate429(900 s) <= exit429`, both windows qualifying, held at every instant of
  the last `holdS` (120 s). `degraded -> recovering`: the same on `rate5xx` with
  `exit5xx` (0.10).
- `recovering -> healthy`: both exit conditions (429 and 5xx) held throughout
  the last `holdS`, and `asOf - stateSince >= holdS`. Both are required because
  the persisted state is `(state, stateSince)` alone and nothing says which
  state `recovering` came from. A bucket with one rate between its exit and
  enter thresholds stays `recovering`, which is the accurate label.
- `recovering -> thrashing | degraded`: the enter condition again, immediately.

Enter and exit thresholds differ, exits need a hold on two windows, and every
decision needs a minimum sample, so a bucket near a cap does not flap. A
reading between exit and enter (0.10 to 0.15 on the 900 s window) holds the
state however long it lasts, and traffic too thin to qualify the 300 s window
cannot satisfy an exit, so it holds the state too; the windows beside the state
show what the traffic is doing.

"Held throughout the last `holdS`" is decided exactly, without sampling. A
window's counts change only at breakpoints, the instant an event's timestamp
enters the window and the instant it leaves, so the exit condition is
evaluated at `asOf - holdS`, at `asOf` and at each breakpoint between. Evaluating the 900 s window
at `asOf - holdS` needs events back to `asOf - 1020`, so `config.retentionS`
is 1020 and the ring keeps nothing older. A read that finds a transition stamps
it with `t = asOf`, appends it to `transitions`, rewrites the state file and
logs one line in the kernel log (`api-health: <bucket> <from> -> <to> — <why>`).
A reader polling every few seconds observes every transition within one poll of
its breakpoint; a sparser reader observes the state at its read times and the
transitions those reads find, and nothing in between: a state entered and left
between two reads is not recorded, and `recovering -> healthy` needs a read at
least `holdS` after the read that entered `recovering`. Nothing derives while
nobody reads.

### Persistence and restart

A read that observes a transition rewrites `STATE/api-health.json`, whole and
atomically (a temp in the same directory, then a rename). The file holds each
bucket's `state`, `stateSince`, `why` and `evidence` and the `transitions`
tail, so it stays bounded however many transitions pass; per-request events
are never written. The event ring itself is in memory only, so a restart
empties the windows: `seq` restarts at 0, `bootId` changes, `complete` stays
false until each window fits inside the new uptime, and every bucket the state
file knows comes back `unknown` with `stateSince` at the boot time. For each
bucket whose persisted state was not already `unknown` the reload files
`<state> -> unknown` at boot, so the transitions list is continuous across the
restart, and the first read with enough evidence records `unknown -> <state>`
after it. The pre-restart state is not carried over: an empty ring is no
evidence. A state file, or an entry in it, that cannot be read is skipped and
logged, and never keeps the SDK backend from starting.

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
