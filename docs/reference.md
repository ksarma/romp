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
| `romp keyswap [<name>] [--refresh] [--cycle <session,…>\|--cycle-all]` | Which API key the sessions bill, by fingerprint, and whether the kernel reads what your shell reads. With `ROMP_CREDENTIAL_COMMAND` set, `<name>` selects a declared credential and `--refresh` makes the kernel re-run the command; after a rotation, `--cycle` or `--cycle-all` reconnects the quiet running sessions so their new processes pick up the new credential, with no manager restart. Where the key lives in a file, `<name>` (upstream's rewrite of `service.env`) is refused: this fork does not write API keys to files. See [Switching which API key the sessions bill](#switching-which-api-key-the-sessions-bill-romp-keyswap) |
| `romp help` | The same list, from the terminal |

**Update notices.** Romp watches for new tagged releases and, on a checkout that tracks
`main`, for new commits, and offers each one once as a banner with an Update button. The gear's
**Updates and update notices** control (under *Updates & debug*) decides what happens: *Check and
ask* shows the banner, *Install automatically* converges on its own at the next quiet moment, and
*Off* stops both the checks and the banners, so a machine whose owner merges to `main` all day
hears nothing about it and keeps running what it has until they restart Romp themselves. The
reload prompt that reads "A newer romp build is available" is separate and stays on in every
mode: it means the page you are looking at runs older code than the kernel, and a reload fixes it.

**User todos.** A session can flag a decision or an input it needs from you and keep working
meanwhile. Each open request is listed under *Waiting on you* on the card at the bottom of that
session's transcript, with Reply and Dismiss, and a session that resumes after a restart or a
compaction is handed its open requests back so it can withdraw the ones that no longer apply. The
feature is off by default. The gear's **User todos** checkbox (under *Sessions*) turns it on for
one machine at a time: each kernel keeps its own copy, and the choice does not spread to other
attached machines. While it is off, sessions on that machine are not offered the tools that flag
or withdraw a request, nothing is listed, and nothing is handed back on resume. Requests flagged
earlier stay stored and reappear when you turn it back on; the kernel's log says how many are
waiting. Every filing, answer, dismissal and withdrawal is also appended to `user-todos-log.jsonl`
beside the store under Romp's state directory, one line per event and never rewritten, so the list
can be rebuilt if the store is ever lost. The **Waiting on you** pane (bottom bar, off by default)
collects every open request across all sessions and attached machines into one list with the same
Reply and Dismiss; because the switch is per machine, the pane says when it is off on this one and
still lists the other machines' requests.

These are for scripting and for agents rather than daily use:

| Command | What it does |
|---|---|
| `romp url` | Print only the tokened dashboard URL, for piping |
| `romp sessions [--json]` | The fleet with each session's state, identity colours, directory and backend |
| `romp mail …` | The postal service from the shell (below) |
| `romp send <session> [--tag <label>] <text>` | Hand a session a message, on either backend. Anything a script, cron job, or launcher composes SHOULD carry a tag (one word, letters/digits/dashes, up to 24 chars): the chat then renders it as machine-sent under that label instead of as the user's typed words. Raw POST /send callers pass it as the JSON `tag` field (`{name, text, tag}` — a malformed tag fails the whole send, loudly); `--tag` is the CLI's equivalent. Both resolve to the `<!-- romp-tag: <label> -->` marker in the delivered text |
| `romp new --model <id> <name>` | Model for the SDK session: a family alias such as `fable` (follows the family's newest release) or a full id such as `claude-fable-5` (a pin); re-asserted if `<name>` already runs |
| `romp new --effort <level> <name>` | Reasoning effort for the SDK session (`high`, `ultracode`, ...); re-asserted if `<name>` already runs |
| `romp new --env NAME=VALUE <name>` | A per-session env var for the SDK session, repeatable; a re-run against a running `<name>` replaces the whole set — vars not re-named are dropped |
| `romp new --no-env <name>` | Clear a running SDK session's per-session env (declares the empty set) |
| `romp new --in <tag> <name>` | Put the new SDK or Codex session in `<tag>`, so its tab lands in that group (repeatable; a name that does not exist yet creates the tag). Applies to `<name>` if it already runs. The kernel echoes `tags` (the session's tags) and, per `--in`, the stored name it landed as (`tagsApplied`, beside `tagsRequested`): a name the store trimmed or clamped prints as "applied as"; a missing echo, or a tag the kernel refused, prints a warning |
| `romp new --no-inherit <name>` | Run inside a romp session, `romp new` sends that session's stable id (`ROMP_SID`) as the new session's `parent` (marked `parentAuto`), and the kernel copies the parent's tags onto the child; inside a comment thread, the parent is the session the thread belongs to. This flag withholds the parent, so the new session starts outside them. A kernel that never ran the calling session creates the session untagged and echoes `parentIgnored`, which the CLI reports in one line. Raw POST /new callers pass `parent` (a live name or a known sid; an unknown one is a 400 unless `parentAuto` is set) and `tags` (a list of names); opening a name that already runs never inherits |
| `romp tag [<name>] [--add <session>…] [--remove <session>…] [--color <hex>] [--rename <new>] [--delete] [--host <kernel>]` | Session tags. Bare, it lists them; with a name, it merges one tag (created on first use). A tagged session leaves the untagged view, and its tab sits in that tag's section of the strip. `--host` edits an attached kernel's tag |
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
and credentials stay in the manager's environment or the `apiKeyHelper`, never
in a file (see [API keys on disk: the file mode](#api-keys-on-disk-the-file-mode) and
[Installing without keys on disk](#installing-without-keys-on-disk)).

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
are all meant to bill a key that arrives through `apiKeyHelper` — so
`ANTHROPIC_API_KEY` is never in the manager's environment — the
landed-on-the-other-auth warning would fire on every init, permanently.
Declaring the intent fixes it: set
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

Run `romp-service install` again after changing one, and on Linux restart the
manager after it (`systemctl --user restart romp-manager`): the install
rewrites the unit and reloads systemd but leaves a running manager as it is,
while on macOS it reloads the job, which restarts it. The service unit bakes in
whatever is set at install time, so a renumbered port that only lives in your
shell leaves the supervised manager on the old one, and the two collide.

### API keys on disk: the file mode

`~/.config/romp/service.env` holds non-secret settings only
(`ROMP_EXPECTED_AUTH`, for example); API keys never go in it. The format is
plain `KEY=VALUE` lines:

    ROMP_EXPECTED_AUTH=key

Unlike the port settings, it is not baked in at install: it is read each time
the manager starts (the systemd unit through `EnvironmentFile=-`; the macOS
login agent's launcher by parsing it line by line, never sourcing it, so a
malformed line is skipped rather than executed). Change a value by editing the
file and restarting the manager (`systemctl --user restart romp-manager`; on
macOS `launchctl kickstart -k gui/$(id -u)/com.romp.manager`); a missing file
is a no-op.

With no `ROMP_CREDENTIAL_COMMAND` line (see [Installing without keys on
disk](#installing-without-keys-on-disk)) the kernel is in **file mode**,
upstream's behaviour unchanged: keys reach the manager through its
environment. The manager inherits the environment of whatever starts it, so a
shell startup file that loads keys from a secrets manager into the environment
covers anything the kernel or its judges call directly, and nothing is written
to disk. The sessions' own key reaches Claude Code through its `apiKeyHelper`
setting, never through the service file.

The login service does not run that startup file, so the manager it starts
never sees the variables your shell exports. `romp up` in a terminal starts the
manager from your shell; the login service (launchd on macOS, `systemd --user`
on Linux) starts it directly from the unit that `romp-service install` writes,
with no shell in between. A terminal that has `ANTHROPIC_API_KEY` therefore
does nothing for the sessions the kernel spawns. On a machine where Claude
authenticates through an OAuth login the gap is invisible, because the
credentials live in a file any process can read; on an API-key-only machine,
SDK sessions come up unauthenticated while `claude` in your terminal works
fine. [Installing without keys on disk](#installing-without-keys-on-disk)
closes the gap with a command the kernel runs itself, so the service needs no
shell and no environment of its own. Routing `ExecStart` through a login shell
to load the variables is the older workaround: the variables it loads freeze
until a manager restart. `romp-service status` reports which shape the unit
has; in command mode the kernel also says so at boot.

Keep `service.env` key-free even where your installation has no rule against
credentials in files. The file still works as the unit's `EnvironmentFile` for
a key, and where an installation keeps an `ANTHROPIC_API_KEY=` line there the
kernel reads it fresh at every session launch, so a change there needs no
restart. But a key in a file is a copy of the credential that outlives its
rotation: the file keeps the old value after the key is replaced, and anything
that can read the file has the key. This fork's tooling never writes that line
(see [Switching which API key the sessions
bill](#switching-which-api-key-the-sessions-bill-romp-keyswap)).

### Installing without keys on disk

For installations that forbid a credential in any file, the kernel has a
second key source, **command mode**: a command it runs, whose output it hands
to each process it starts. One line in `service.env` (or an `Environment=` line
in the unit) selects it; with the line absent nothing about file mode changes.

    ROMP_CREDENTIAL_COMMAND=my-credentials "$1"
    ROMP_CREDENTIAL_NAMES=hp,lp
    ROMP_CREDENTIAL_SELECTOR_FILE=~/.config/romp/credential-selector
    ROMP_CREDENTIAL_TIMEOUT_S=15

- `ROMP_CREDENTIAL_COMMAND` is a shell command line, and setting it is the
  whole switch. The kernel decides the mode once, when it starts, never
  mid-life, so its sessions, judges and catalog fetch never straddle two key
  sources. A line added to `service.env` reaches the kernel at its next start
  (`romp refresh`); removing the line takes a manager restart (see [Two things
  still need a restart](#two-things-still-need-a-restart)). The kernel runs the
  command as `/bin/sh -c <command> sh <selector>`, so the selector file's
  token is `$1`: `my-cmd "$1"` forwards it, a bare `my-cmd` never sees it. The
  command prints `NAME=VALUE` lines (an `export NAME=VALUE` line is accepted
  here, so a command that already prints shell assignments works as it is;
  `service.env` itself keeps the plain form the launchers and systemd read);
  blank and `#` lines are skipped, the last assignment of a name wins, one
  layer of matching quotes is stripped, an empty value unsets the name, lines
  are split on newlines only, and a value carrying a NUL is dropped as a bad
  line:

      ANTHROPIC_API_KEY=placeholder-work-key
      ANTHROPIC_LP_API_KEY=placeholder-direct-call-key
      MY_SERVICE_TOKEN=placeholder-role-value

  `ANTHROPIC_API_KEY` (optional) is the sessions' key, injected into a session
  whose Billing pick is the key; without it the sessions authenticate through
  Claude Code's `apiKeyHelper`, as before. `ANTHROPIC_LP_API_KEY` is the key for
  the kernel's own direct calls (the model catalog fetch). Any other name is a
  variable for the sessions and their tool shells. Names starting with `ROMP_`
  are dropped, with one problem line naming them, and so are the names Claude
  Code reads as its own authentication or endpoint (`ANTHROPIC_AUTH_TOKEN`,
  `CLAUDE_CODE_OAUTH_TOKEN`, `ANTHROPIC_BASE_URL`, `ANTHROPIC_CUSTOM_HEADERS`):
  a set carrying one would re-route or re-bill every session behind the one
  door the mode keeps for the key. A legitimate `ANTHROPIC_BASE_URL` (a proxy
  every session should use) belongs in the manager's environment or in
  `service.env` as a plain setting, which every kernel and session inherits,
  or in Claude Code's own settings; the command's output is not the place for
  it. A proxy secret in `ANTHROPIC_CUSTOM_HEADERS` is not carried by the
  command either: a proxy that needs one authenticates through Claude Code's
  settings, not through this set.
- `ROMP_CREDENTIAL_SELECTOR_FILE` holds one token, passed as `$1`: a name such
  as `hp`, made of letters, digits, `.`, `_` and `-`, up to 64 characters. The
  default is `~/.config/romp/credential-selector`. `romp keyswap <name>` writes
  it. An installation may point it at a file its `apiKeyHelper` already reads,
  so one switch moves both; a hand edit of that file is picked up at the next
  launch or call, with no refresh (the file's own identity is part of the
  cache).
- `ROMP_CREDENTIAL_NAMES` is the comma-separated list of names an operator may
  select. A name outside it is refused before anything runs and is never
  echoed. The selector is shown by name (in `romp keyswap`, `romp-service
  status`, the log and `/api-health`) only when this list declares it; an
  undeclared token is shown as `(undeclared, N chars)`, since it could be
  anything, a pasted secret included. With the list unset the kernel still
  passes the token as `$1`, but `romp keyswap <name>` refuses to write one.
- `ROMP_CREDENTIAL_TIMEOUT_S` bounds one run, in seconds (default 15; a value
  that is not a number between 0 and 300 is refused with one problem line, and
  the default holds). On the deadline the command's whole process group is
  killed. The deadline is on the command itself: a command that exits with a
  complete set but leaves a child holding its output (a daemon it forked)
  succeeds, and the leftover is killed.

The values never land in the kernel's environment, a log line, a card or the
API-health document; the only rendered form is a fingerprint (`sha256:` and 12
hex digits).

The command runs when its result is needed and the cached set is stale, and
staleness is an event, not a timer: `romp keyswap --refresh`, a `--cycle`, an
authentication failure in a judge call or on a session, or an edit of the
selector file. A failed run keeps the previous set and logs one problem line
per distinct failure reason, with counts and exit codes only (`exited 3 after
0.4s, stderr 87 bytes`), never the command's output. A failure is not cached
the way a success is: the next launch or call runs the command again (one run
per caller; callers that overlap share one run), so a store that was briefly
unreachable is back in use without an operator action. With no previous set,
sessions launch with nothing injected (the `apiKeyHelper` or the login bills),
and a launch is never refused for it.

After a rotation (a new value behind the selected name, or a new selector),
each consumer picks the new set up at its own next step, with no manager
restart:

- Sessions at their next connect (`romp keyswap --cycle-all` reconnects the
  quiet ones now; a running process keeps what it started with until then)
- Judges per call: the set minus `ANTHROPIC_API_KEY`, which is re-added only
  for a key-billed call
- The model catalog per fetch, through `ANTHROPIC_LP_API_KEY`
- A session's tool shells at that session's next reconnect (they inherit the
  CLI's environment)

#### Two things still need a restart

Which restart depends on where the kernel finds the value. Adding the
`ROMP_CREDENTIAL_COMMAND` line to `service.env` changes the mode at the next
kernel start: `romp refresh` is enough, because the kernel reads `service.env`
itself. Removing the line under the installed service needs a manager restart,
`systemctl --user restart romp-manager` on Linux and `launchctl kickstart -k
gui/$(id -u)/com.romp.manager` on macOS: the service loaded `service.env` into
the manager's environment when the manager started, every kernel inherits that
environment, and `romp refresh` restarts kernels only, so a new kernel still
carries the variable and stays in command mode. The restart re-reads
`service.env`, so remove the line first. A line in the unit's own
`Environment=`, in a drop-in, or in the profile a shell-wrapped `ExecStart`
sources (Linux), or in the plist's `EnvironmentVariables` (macOS), is
different: a manager restart re-applies it, so it has to be removed where it
is and the service definition reloaded before the restart. On Linux that is
`systemctl --user daemon-reload` after editing a unit or a drop-in, then the
restart. On macOS `launchctl kickstart -k` restarts the job as launchd loaded
it and does not re-read the plist, so the job is reloaded instead: `launchctl
bootout gui/$(id -u)/com.romp.manager`, then `launchctl bootstrap gui/$(id -u)
~/Library/LaunchAgents/com.romp.manager.plist`. `romp-service install` does
the same on macOS, since it rewrites the plist and reloads the job; on Linux
it rewrites the unit and reloads systemd but leaves a running manager as it
is, so the restart still follows. The other `ROMP_CREDENTIAL_*`
values are read live, the environment first, with the same consequence: a
line the manager's environment already carries is shadowed by that copy until
the manager restarts, while a line the environment does not carry (one added
since the manager started) is read from the file at once. When `romp keyswap`
finds the kernel in command mode under a shell that reads no line, it cannot
tell which place still carries it, so its `MISMATCH` lists each with its
remedy: `service.env` as the manager loaded it; the unit, a drop-in, or the
profile a shell-wrapped `ExecStart` sources; another `service.env`, when the
installer carried a non-default `ROMP_SERVICE_ENV_FILE` into the unit or plist
and this shell reads a different file (run `romp keyswap` with the same
variable, or check the unit); a `service.env` line removed since the kernel
started; and the shell that ran `romp up`. The same other-file cause is named
under a kernel in file mode when the file this shell reads carries the line,
since `romp refresh` reaches only the file the kernel reads.

The kernel checks the configuration once at boot and logs one line per
finding, names and fingerprints only. When the first run succeeds the line is
`key source: command (selector hp) — the set is sha256:… (3 names: …); the
sessions' key is sha256:…`. It logs a problem line for each of the following:

- The command failed, with the consequence: the previous set stands, or
  nothing is injected until a run succeeds.
- A credential-shaped line (`ANTHROPIC_API_KEY`, any `*_API_KEY`, any
  `*_TOKEN` with a value) in `service.env`, the unit, a drop-in or the plist.
  Command mode ignores it; remove it and rotate the credential.
- An `ANTHROPIC_API_KEY` in the manager's own environment, ignored the same
  way.
- An `ExecStart` routed through a shell.
- `ROMP_EXPECTED_AUTH=login` while the command prints a key.
- `ROMP_*` names, or the CLI's own authentication and endpoint names, that the
  command printed.
- `ROMP_CREDENTIAL_TIMEOUT_S` outside its range.

An authentication failure invalidates the set once per credential: a second
refusal while the set (and the helper's output) is unchanged does not re-run
the command, so a revoked credential does not turn every judge call into a
run; `romp keyswap --refresh` re-arms it.

In file mode the same check says nothing new, except a credential in the unit
under a declared `ROMP_EXPECTED_AUTH`. `GET /api-health` carries the same facts
as `keySource` (see [The API-health signal](#the-api-health-signal)), and
`romp-service status` prints the mode and the selector, whether `ExecStart`
runs the manager directly or through a shell, and the credential-shaped names
it finds in the unit or in `service.env`.

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
reason). The macOS launchd path is unchanged: there is no cgroup kill there,
and the tmux server keeps its launchd lineage.

### Switching which API key the sessions bill (`romp keyswap`)

    romp keyswap                       # which credential the kernel holds, by fingerprint, and whether your shell agrees
    romp keyswap <name>                # command mode: select a declared credential (writes the selector file)
    romp keyswap --refresh             # make the kernel re-run its credential command now
    romp keyswap --cycle-all           # after a rotation: reconnect every quiet session
    romp keyswap --cycle web,api       # …or only these

A running CLI keeps the credential its process started with, so after a
rotation the sessions need a new process. `--cycle-all` (or `--cycle
<session,…>`) reconnects each quiet session: the conversation resumes with its
history intact, and the manager never restarts, so no session loses an open
turn. The reconnect is the same mechanism a reasoning-effort or billing switch
uses.

**In command mode** (`ROMP_CREDENTIAL_COMMAND` set) a bare `romp keyswap` runs
your credential command in your shell and asks the kernel what its own run
yields:

    $ romp keyswap
    key source  command (ROMP_CREDENTIAL_COMMAND is set): the kernel runs it and injects the set it prints
    selector    hp             ~/.config/romp/credential-selector
    candidates  hp <- selected, lp
    set         sha256:5e5e5e5e5e5e — 3 names: ANTHROPIC_API_KEY, ANTHROPIC_LP_API_KEY, MY_SERVICE_TOKEN
    live key    sha256:1a2b3c1a2b3c   (this shell's run of the command: its ANTHROPIC_API_KEY line)
    kernel      reads sha256:1a2b3c1a2b3c (its own run); 3 live session(s) on it

    rotate:     romp keyswap <name>  writes the selector (one of: hp, lp) and re-runs the command; then
                romp keyswap --cycle-all  so quiet sessions reconnect. A new value behind the same
                name: romp keyswap --cycle-all  alone (it re-runs the command first).

    $ romp keyswap lp
    selector    hp -> lp
    live key    sha256:9f8e7d9f8e7d   (was sha256:1a2b3c1a2b3c)
    set         sha256:4d4d4d4d4d4d   (was sha256:5e5e5e5e5e5e)
    kernel      reads sha256:9f8e7d9f8e7d (its own run, re-run now: was sha256:1a2b3c1a2b3c); 0 live session(s) on it
                3 live session(s) still on sha256:1a2b3c1a2b3c

    $ romp keyswap --cycle-all
    …
      web            reconnecting now — history kept (from sha256:1a2b3c1a2b3c)
      api            already on this key — nothing to do
      tests          skipped: a turn, subagents or background tasks are in flight …
                re-run --cycle tests once quiet; sessions already on this key read "current"

Where the set carries no `ANTHROPIC_API_KEY`, the live key is your shell's run
of Claude Code's `apiKeyHelper` (named in `$CLAUDE_CONFIG_DIR/settings.json`,
the one user-level settings file; a `settings.local.json` is a project-level
file, and project and managed settings are not consulted), and the kernel
fingerprints the same helper. The helper
runs the way a session's CLI runs it: with the set's other variables in its
environment and no `ROMP_SID`. With no key in the set and no helper
configured, the sessions bill the machine login; the report says so as a
state, not a failure, and a cycle then covers the set's other variables.

Each session is stamped at launch with the fingerprint it launched under, and
a cycle compares that stamp with the current one, so a second run reads
`current` for every session already moved, and a rotation behind the same
name costs one reconnect per session.

`romp keyswap <name>` writes the selector file, re-runs the command in your
shell and confirms the fingerprint moved; an undeclared name exits 2 before
anything runs. A switch that moves nothing is undone and exits 1 with
`nothing switched`: the command ignores `$1`, both names resolve to one
credential, or the command fails for the new name, and the selector goes back
to what it was. A switch that moved asks the kernel to re-run too and reports
the kernel's view. `--refresh` asks the kernel to re-run without switching;
the kernel line then carries the fingerprint before and after.

`MISMATCH` means the kernel and your shell disagree, and the line says on
what. On the mode: `ROMP_CREDENTIAL_COMMAND` is set on one side only, and a
running kernel keeps the mode it started in. When your shell has the line and
the kernel does not, the line says what reaches the kernel: `romp refresh`,
when the line was added to `service.env` (the kernel reads the file at its
start); nothing, when the line is set in your shell's environment only, until
it is in `service.env`. When the kernel is in command mode and your shell
reads no line, the kernel's answer cannot say where the kernel got the line,
so the report lists the places, each with its remedy:

- `service.env` as the manager loaded it at its start, which every kernel
  inherits: a manager restart, which re-reads the file
- the unit's own `Environment=`, a drop-in, or the profile a shell-wrapped
  `ExecStart` sources (Linux), or the plist's `EnvironmentVariables` (macOS):
  a manager restart re-applies these, so remove the line there, reload the
  definition, then restart (the commands are under [Two things still need a
  restart](#two-things-still-need-a-restart))
- another `service.env`, when the kernel's environment names a different file
  through `ROMP_SERVICE_ENV_FILE`: run `romp keyswap` with the same variable
- `service.env`, edited since the kernel read it at its start: `romp refresh`
- the shell that ran `romp up`, which exported the line: start it again from a
  shell without the line

On the fingerprint: the kernel's last run used
another selector (`--refresh` re-runs it), or the two environments differ (the
service environment and your shell hold different `ROMP_CREDENTIAL_*` values,
different selector files, or a different `CLAUDE_CONFIG_DIR`; the
`apiKeyHelper` the kernel fingerprints is the one its own settings name). A
cycle stops on a mismatch before any reconnect, and a shell whose own run
failed cycles nothing.

**In file mode** (no `ROMP_CREDENTIAL_COMMAND`) upstream's `romp keyswap
<name>` rewrites the `ANTHROPIC_API_KEY=` line of `service.env` from a sibling
file (`service.env.<name>`). This fork refuses the rewrite: it does not write
API keys to files, so the named swap exits 2 with that message, reads and
writes nothing, and has no flag that lets it through. The bare command reports
the key the kernel holds (as a fingerprint), the file it reads, and `MISMATCH`
when the kernel is not reading this file's key; a cycle reads and compares the
same way first and stops on a mismatch. Rotate the key at its source, then run
`--cycle-all` for the key-billed sessions. In file mode the kernel hands a
session billed through the `apiKeyHelper` no key, so such a session reads as
the login and the cycle skips it: a rotated helper key reaches those sessions
through `romp refresh --quiet` (every process is new), or through `--cycle-all`
in command mode, where the kernel fingerprints the helper and converges on it.
The cycle report prints one hint line to that effect when it skips a login
row in file mode.

Per session the cycle reports one of:

* `reconnecting now — history kept (from sha256:…)`: reconnecting, with the
  fingerprint its process launched on.
* `already on this key — nothing to do`.
* `skipped: bills the machine login, not the key`: its CLI reported the login,
  so a reconnect would cost a turn for nothing (in file mode a session billed
  through the `apiKeyHelper` reads this way too; see above).
* `not running — its next launch reads the new key`.
* `skipped: a turn, subagents or background tasks are in flight`: a reconnect
  would kill that work. The re-run hint names the skipped sessions; re-run
  `--cycle` with those names once they are quiet.

`romp refresh --quiet` is the alternative that restarts every kernel once the
sessions are quiet: every session's CLI is a new process. The manager itself
keeps running, so a `ROMP_CREDENTIAL_COMMAND` line added to `service.env` is
applied by that restart, while a line removed from it still needs a manager
restart, because the manager's environment carries what it loaded at its
start: `systemctl --user restart romp-manager`, or on macOS `launchctl
kickstart -k gui/$(id -u)/com.romp.manager`. A line in the unit's own
`Environment=` or in the plist's `EnvironmentVariables` is re-applied by that
restart: remove it where it is, reload the definition, then restart (the
commands per platform are under [Two things still need a
restart](#two-things-still-need-a-restart)).

No key value is ever printed, logged, or sent over a socket. The command's
output, the Log panel entry when the kernel's credential changes, and the
kernel's answer to the CLI all render only the first 12 hex digits of its
sha256.

Remote kernels are cycled from their own machine. `ROMP_SERVICE_ENV_FILE`
overrides the path of the env file the kernel reads. A kernel started before
this feature has no `/keycycle` route and says so; take the update once with
`romp refresh` (or `romp refresh --quiet`).

The kernel also guards the rule at start. If the env file carries a
credential-shaped line (`ANTHROPIC_API_KEY`, any `*_API_KEY`, any `*_TOKEN`
with a value) while `ROMP_EXPECTED_AUTH` declares the machine's auth (`key`,
the `apiKeyHelper` design in [API keys on disk: the file
mode](#api-keys-on-disk-the-file-mode), or `login`), it logs one problem line
naming the file and the variable name, never the value. For `ANTHROPIC_API_KEY`
the line says what would happen to billing: that key would be injected at
launch and take over from the declared auth. For any other credential-shaped
name it says only that a credential in the file contradicts the declared auth
model. With no declaration nothing is said; that is upstream's ordinary
file-key installation.

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
under another family's clean traffic. The auth label is a salted digest: the
same key or login gives the same label within one install, and nothing about
the key itself is in it. The salt lives at `STATE/api-health-salt`, minted once
at 0600; an empty file switches to unsalted digests. `key:helper`, `key:env`
and `key:managed` name sources whose material the kernel never holds.

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
  outside the signal; `null` when the kernel could not enumerate them);
  `sidechainExcluded` (a constant `true`: subagent traffic is
  outside the signal on both sides of the ratio). A reader that sees `inTurn >
  0` and a `lastEventAt` minutes old should treat the signal as unknown rather
  than healthy.
- `cliScope`: `on`, the kernel's boot verdict on per-session transient scopes
  (see "What survives a restart"); `fallbacks`, CLI launches since boot on which
  the scope wrapper's pre-flight scope failed and it ran the CLI directly, which
  it reports with a `romp-cli-scope: fallback: …` stderr line. Each is also a
  problem line in the kernel log, in exactly this form: `cli scope: session
  <name> (<sid8>) started its CLI outside a scope — <line>`, where `<sid8>` is
  the first 8 characters of the session id and `<line>` is the wrapper's whole
  stderr line, its `romp-cli-scope: fallback:` prefix included. The wrapper's
  other message, `romp-cli-scope: refused: …` (`ROMP_CLI_REAL` unset, exit 127),
  starts no CLI and is not counted: it is a launch failure, reported on the
  session's error card. `lastFallbackAt`, epoch seconds of the newest fallback,
  `null` when there was none. `on: true` with `fallbacks > 0` means the verdict
  stopped holding after boot: those sessions' work is in the service cgroup, and
  a service restart kills it.
- `config`: the constants in force (see "Derived state").
- `keySource`: the key source the kernel decided at boot, plus what is live
  now: `mode` (`file` or `command`), `selector`, `sessionKeyPath` (`injected`,
  `helper` or `login`: how a session launched now gets its key), `expectedAuth`,
  `helperConfigured`, `execStartShell` (`true` when the unit starts the manager
  through a shell; `null` when no unit was found), `credentialNamesFound`
  (`serviceEnv`, `unit`, `environment`: credential-shaped names, never values),
  `lastRun` (command mode: `ok`, `at`, `reason`, `exitCode`, `durationS`,
  `stale` (a failed run standing on the previous set), `failures`
  (consecutive) and `lastOkAt`; else `null`),
  `fingerprint` and `fingerprintKind` (`key` or `helper`) of the credential a
  session launched now would bill, `setFingerprint` and `names` of the
  command's set, and `sessionsByFingerprint` (live sessions per launch
  fingerprint; `""` counts sessions launched with no credential the kernel
  fingerprinted). See [Installing without keys on
  disk](#installing-without-keys-on-disk).
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

Earlier builds appended one row per transition to `STATE/api-health.jsonl`. A
kernel that boots without a state file seeds one from that ledger's last 64 KB,
once, and leaves the ledger alone; once the state file exists the ledger is
never read again and can be deleted.

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
